from __future__ import annotations

import math
import random
import time
from collections import deque

import numpy as np
import torch

from .config import (
    ALGO_ALNS_BASE,
    ALGO_HYBRID_DDQN,
    ALGO_HYBRID_FIXED,
    ALGO_HYBRID_RULE,
    ALGO_ORTOOLS,
    MODE_DEFAULT,
    MODE_DIVERSIFY,
    MODE_INTENSIFY,
    MODE_POOL_RECOMBINE,
    MODE_ROUTE_REDUCE,
    MODE_TW_RESCUE,
    MODES,
    Config,
)
from .core import Inst, Plan, _avg_slack, _fleet_fill, _plan_spread, _check_route
from .heuristics import build_greedy, _best_insert_position
from .local_search import (
    _buffered_route_elimination,
    _ejection_chain_eliminate,
    _iterative_route_elimination,
    _try_route_merge,
    local_search,
    merged_route_candidates,
    _two_opt_best,
)
from .operators import DESTROY, N_D, N_R, REPAIR, accept, accept_with_nv_ceiling, destroy_size
from .pool import RoutePool, recombine_with_route_pool
from .rl import (
    DEVICE,
    EliteArchive,
    LearnedAcceptanceCriterion,
    LSBudgetController,
    OperatorController,
    PlateauController,
    ThompsonBandit,
    UCBActionAugmenter,
    WelfordRewardNormalizer,
)

try:
    import ortools  # noqa: F401

    ORTOOLS_OK = True
except ImportError:
    ORTOOLS_OK = False


class ALNSSolver:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        self.cfg = cfg
        self.bandit = ThompsonBandit(N_D, N_R)

    def solve(self, seed: int | None = None, init: Plan | None = None) -> tuple[Plan, list[float]]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        cfg = self.cfg
        self.bandit = ThompsonBandit(N_D, N_R)
        cur = init.copy() if init is not None else build_greedy(self.inst, ALGO_ALNS_BASE)
        best = cur.copy()
        temp = cfg.temp_control * cur.cost / math.log(2)
        history = [best.cost]
        no_imp = 0
        self.q_scale = 1.0
        for it in range(cfg.alns_iterations):
            di, ri = self.bandit.select()
            size = destroy_size(it, cfg.alns_iterations, cfg, self.inst.n, scale=self.q_scale)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand = REPAIR[ri](dest, removed)
            score = 0
            if accept(cur, cand, temp):
                if cand.dominates(best):
                    best, score, no_imp = cand.copy(), cfg.sigma1, 0
                elif cand.dominates(cur):
                    score, no_imp = cfg.sigma2, 0
                else:
                    score, no_imp = cfg.sigma3, no_imp + 1
                cur = cand
            else:
                no_imp += 1

            # Adapt q_scale based on whether search is improving or stuck
            if no_imp == 0:
                self.q_scale = max(0.6, self.q_scale * 0.98)
            else:
                self.q_scale = min(1.6, self.q_scale * 1.005)

            self.bandit.update(di, ri, score, cfg.sigma1)
            if (it + 1) % cfg.segment_size == 0:
                self.bandit.decay(cfg.bandit_decay)
            temp *= cfg.temp_decay
            history.append(best.cost)
            if no_imp >= cfg.early_stop_patience:
                break
        best.algo = ALGO_ALNS_BASE
        return best, history


class HybridDDQNSolver:
    algo_name = ALGO_HYBRID_DDQN
    use_op_rl = True

    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        self.cfg = cfg
        self.ctrl = PlateauController(cfg)
        self.op_ctrl = OperatorController(cfg)
        self.lac = LearnedAcceptanceCriterion(cfg)
        self.ls_budget = LSBudgetController(ls_time_frac=0.30)
        self.ucb_aug = UCBActionAugmenter(n_actions=N_D * N_R)
        self.reward_norm = WelfordRewardNormalizer(clip_sigma=8.0, warmup=128)
        self.mode_bandits: list[ThompsonBandit] = [ThompsonBandit(N_D, N_R) for _ in MODES]
        self._segment_recombine_used = False
        self._pool_seeding_done: bool = False  # guard: fires once per solve()
        self._init_nv = 1
        self.archive = EliteArchive(k=cfg.elite_archive_k)

    def clone_weights(self) -> dict:
        weights: dict[str, torch.Tensor] = {}
        for prefix, sd in (("plateau", self.ctrl.q.state_dict()), ("operator", self.op_ctrl.q.state_dict())):
            for k, v in sd.items():
                weights[f"{prefix}.{k}"] = v.clone().cpu()
        weights.update(self.lac.state_dict())
        weights["ucb.mu"] = torch.tensor(self.ucb_aug._mu, dtype=torch.float32)
        weights["ucb.cnt"] = torch.tensor(self.ucb_aug._cnt, dtype=torch.float32)
        weights["ucb.m2"] = torch.tensor(self.ucb_aug._m2, dtype=torch.float32)
        for k, v in self.reward_norm.state_dict().items():
            weights[f"reward_norm.{k}"] = torch.tensor(float(v))
        return weights

    def load_weights(self, weights: dict) -> None:
        plateau_sd = self.ctrl.q.state_dict()
        operator_sd = self.op_ctrl.q.state_dict()
        p_up: dict[str, torch.Tensor] = {}
        o_up: dict[str, torch.Tensor] = {}
        LEGACY_OP_PREFIXES = ("op.", "operator_ctrl.", "op_ctrl.")
        legacy = not any(k.startswith(("plateau.", "operator.")) for k in weights)
        
        if legacy:
            import warnings
            warnings.warn(
                "load_weights: legacy unprefixed weight format detected. "
                "Re-save weights using clone_weights() to suppress this warning.",
                DeprecationWarning,
                stacklevel=2,
            )
            for k, v in weights.items():
                target_key = k
                is_op = False
                for prefix in LEGACY_OP_PREFIXES:
                    if k.startswith(prefix):
                        target_key = k[len(prefix):]
                        is_op = True
                        break
                if not is_op and target_key in plateau_sd and tuple(v.shape) == tuple(plateau_sd[target_key].shape):
                    p_up[target_key] = v.to(DEVICE)
                else:
                    if target_key in operator_sd:
                        if tuple(v.shape) == tuple(operator_sd[target_key].shape):
                            o_up[target_key] = v.to(DEVICE)
                        elif "adv_head.2" in target_key:
                            padded = operator_sd[target_key].clone()
                            loaded_n = v.shape[0]
                            padded[:loaded_n] = v
                            D_old = max(1, loaded_n // N_R)
                            for new_act in range(loaded_n, padded.shape[0]):
                                r = new_act % N_R
                                lookup_indices = [min(i * N_R + r, loaded_n - 1) for i in range(D_old)]
                                stacked = torch.stack([v[idx] for idx in lookup_indices])
                                padded[new_act] = stacked.mean(dim=0)
                            o_up[target_key] = padded.to(DEVICE)
                        else:
                            raise ValueError(
                                f"load_weights: shape mismatch for legacy key '{k}': "
                                f"checkpoint={tuple(v.shape)}, model={tuple(operator_sd[target_key].shape)}."
                            )
        else:
            for k, v in weights.items():
                if k.startswith("plateau."):
                    bare = k.split(".", 1)[1]
                    if bare in plateau_sd and tuple(v.shape) == tuple(plateau_sd[bare].shape):
                        p_up[bare] = v.to(DEVICE)
                elif k.startswith("operator."):
                    bare = k.split(".", 1)[1]
                    if bare in operator_sd:
                        if tuple(v.shape) != tuple(operator_sd[bare].shape):
                            if "adv_head.2.weight" in bare or "adv_head.2.bias" in bare:
                                padded = operator_sd[bare].clone()
                                loaded_n = v.shape[0]
                                padded[:loaded_n] = v
                                D_old = max(1, loaded_n // N_R)
                                for new_act in range(loaded_n, padded.shape[0]):
                                    r = new_act % N_R
                                    lookup_indices = [min(i * N_R + r, loaded_n - 1) for i in range(D_old)]
                                    stacked = torch.stack([v[idx] for idx in lookup_indices])
                                    padded[new_act] = stacked.mean(dim=0)
                                o_up[bare] = padded.to(DEVICE)
                            else:
                                raise ValueError(
                                    f"load_weights: shape mismatch for operator key '{bare}': "
                                    f"checkpoint={tuple(v.shape)}, model={tuple(operator_sd[bare].shape)}."
                                )
                        else:
                            o_up[bare] = v.to(DEVICE)
                            
        plateau_sd.update(p_up)
        operator_sd.update(o_up)
        self.ctrl.q.load_state_dict(plateau_sd)
        self.ctrl.q_t.load_state_dict(plateau_sd)
        self.op_ctrl.q.load_state_dict(operator_sd)
        self.op_ctrl.q_t.load_state_dict(operator_sd)
        
        lac_weights = {k: v for k, v in weights.items() if k.startswith("lac.")}
        if lac_weights:
            self.lac.load_state_dict(lac_weights)
            
        if "ucb.mu" in weights:
            loaded_mu = weights["ucb.mu"].numpy().astype(np.float64)
            loaded_cnt = weights["ucb.cnt"].numpy().astype(np.float64)
            loaded_m2 = weights["ucb.m2"].numpy().astype(np.float64)
            if len(loaded_mu) < self.ucb_aug.n:
                padded_mu = np.zeros(self.ucb_aug.n, dtype=np.float64)
                padded_cnt = np.ones(self.ucb_aug.n, dtype=np.float64) * 0.5
                padded_m2 = np.ones(self.ucb_aug.n, dtype=np.float64) * 0.5
                padded_mu[: len(loaded_mu)] = loaded_mu
                padded_cnt[: len(loaded_cnt)] = loaded_cnt
                padded_m2[: len(loaded_m2)] = loaded_m2
                loaded_len = len(loaded_mu)
                D_old = max(1, loaded_len // N_R)
                for new_act in range(loaded_len, self.ucb_aug.n):
                    r = new_act % N_R
                    lookup_indices = [min(i * N_R + r, loaded_len - 1) for i in range(D_old)]
                    padded_mu[new_act] = np.mean([loaded_mu[idx] for idx in lookup_indices])
                    padded_cnt[new_act] = np.mean([loaded_cnt[idx] for idx in lookup_indices])
                    padded_m2[new_act] = np.mean([loaded_m2[idx] for idx in lookup_indices])
                self.ucb_aug._mu = padded_mu
                self.ucb_aug._cnt = padded_cnt
                self.ucb_aug._m2 = padded_m2
            else:
                self.ucb_aug._mu = loaded_mu
                self.ucb_aug._cnt = loaded_cnt
                self.ucb_aug._m2 = loaded_m2
            self.ucb_aug._N = float(self.ucb_aug._cnt.sum())
            
        norm_d = {k.split(".", 1)[1]: float(weights[k]) for k in weights if k.startswith("reward_norm.")}
        if norm_d:
            self.reward_norm.load_state_dict(norm_d)

    def _fleet_pressure(self, plan: Plan, best_nv: float) -> float:
        nv_excess = (plan.nv - best_nv) / max(self._init_nv, 1.0)
        return float(1.0 / (1.0 + math.exp(-8.0 * nv_excess)))

    def _adaptive_potential(self, plan: Plan, best_nv: float, best_td: float) -> float:
        lam = self._fleet_pressure(plan, best_nv)
        nv_penalty_norm = max(plan.nv - best_nv, 0.0) / max(self._init_nv, 1.0)
        td_gap = float(np.clip((plan.cost - best_td) / max(best_td, 1.0) * 100.0, -25.0, 25.0))
        return float(
            -lam * self.cfg.potential_nv_scale * nv_penalty_norm - (1 - lam) * self.cfg.potential_cost_scale * td_gap
        )

    def _state(self, cur, best, no_imp, temp, imp_rate, progress, pool) -> np.ndarray:
        rb, lb = _plan_spread(cur, self.inst)
        t0 = self.cfg.temp_control * max(best.cost, 1.0) / math.log(2)
        pool_fill = min(len(pool._routes) / max(self.cfg.route_pool_limit, 1), 1.0)
        return np.array(
            [
                min(no_imp / max(self.cfg.early_stop_patience, 1), 1.0),
                min((cur.cost - best.cost) / max(best.cost, 1), 1.0),
                min(temp / max(t0, 1e-6), 1.5),
                imp_rate,
                min(cur.nv / max(self._init_nv, 1), 2.0),
                rb,
                lb,
                self.inst.tw_tight_frac,
                _avg_slack(cur),
                _fleet_fill(cur),
                pool_fill,
                progress,
            ],
            dtype=np.float32,
        )

    def _op_state(self, cur, best, mode_idx, it, temp, no_imp, pool, recent_imp) -> np.ndarray:
        rb, lb = _plan_spread(cur, self.inst)
        t0 = self.cfg.temp_control * max(best.cost, 1.0) / math.log(2)
        pool_fill = min(len(pool._routes) / max(self.cfg.route_pool_limit, 1), 1.0)
        return np.array(
            [
                min((cur.cost - best.cost) / max(best.cost, 1), 1.0),
                min(cur.nv / max(self._init_nv, 1), 2.0),
                it / max(self.cfg.hybrid_iterations, 1),
                (it % self.cfg.segment_size) / max(self.cfg.segment_size, 1),
                min(temp / max(t0, 1e-6), 1.5),
                min(no_imp / max(self.cfg.early_stop_patience, 1), 1.0),
                rb,
                lb,
                self.inst.tw_tight_frac,
                _avg_slack(cur),
                _fleet_fill(cur),
                pool_fill,
                mode_idx / max(len(MODES) - 1, 1),
                float(cur.nv - best.nv) / max(self._init_nv, 1),
                recent_imp,
            ],
            dtype=np.float32,
        )

    def _segment_reward(self, best_before, best_after, cur_before, cur_after, accepted_moves, action) -> float:
        lam = self._fleet_pressure(cur_after, best_before.nv)
        base = -0.20 - 0.04 * MODES[action].ls_passes
        if MODES[action].use_recombine:
            base -= 0.06
        denom = max(self._init_nv, 1.0)
        best_nv_gain = (best_before.nv - best_after.nv) / denom
        cur_nv_gain = (cur_before.nv - cur_after.nv) / denom
        best_cost_gain = max((best_before.cost - best_after.cost) / max(best_before.cost, 1) * 100, 0.0)
        cur_cost_gain = max((cur_before.cost - cur_after.cost) / max(cur_before.cost, 1) * 100, 0.0)
        nv_component = lam * (
            8.0 * best_nv_gain * denom + 1.2 * best_cost_gain + 5.0 * cur_nv_gain * denom + 0.6 * cur_cost_gain
        )
        td_component = (1.0 - lam) * (
            3.0 * best_nv_gain * denom + 3.5 * best_cost_gain + 2.0 * cur_nv_gain * denom + 1.8 * cur_cost_gain
        )
        if best_after.nv < best_before.nv:
            base += 15.0 * (best_before.nv - best_after.nv)
        if cur_after.nv < cur_before.nv:
            base += 5.0 * (cur_before.nv - cur_after.nv)
        base += nv_component + td_component
        if accepted_moves <= max(1, self.cfg.segment_size // 10):
            base -= 0.15
        shaped = self.cfg.ctrl_gamma * self._adaptive_potential(
            cur_after, best_before.nv, best_before.cost
        ) - self._adaptive_potential(cur_before, best_before.nv, best_before.cost)
        return float(self.cfg.segment_reward_scale * base + shaped)

    def _iteration_reward(self, cur_before, best_before, cur_after, best_after, accepted) -> float:
        lam = self._fleet_pressure(cur_after, best_before.nv)
        if not accepted:
            base = -0.08
        else:
            base = 0.05
            denom = max(self._init_nv, 1.0)
            best_nv_gain = (best_before.nv - best_after.nv) / denom
            cur_nv_gain = (cur_before.nv - cur_after.nv) / denom
            best_cost_gain = max((best_before.cost - best_after.cost) / max(best_before.cost, 1) * 100, 0.0)
            cur_cost_gain = max((cur_before.cost - cur_after.cost) / max(cur_before.cost, 1) * 100, 0.0)
            nv_component = lam * (
                3.0 * best_nv_gain * denom + 0.40 * best_cost_gain + 2.0 * cur_nv_gain * denom + 0.20 * cur_cost_gain
            )
            td_component = (1.0 - lam) * (
                0.50 * best_nv_gain * denom + 1.80 * best_cost_gain + 0.30 * cur_nv_gain * denom + 0.90 * cur_cost_gain
            )
            if best_after.nv < best_before.nv:
                base += 15.0 * (best_before.nv - best_after.nv)
            if cur_after.nv < cur_before.nv:
                base += 5.0 * (cur_before.nv - cur_after.nv)
            base += nv_component + td_component
            if cur_after.nv > cur_before.nv:
                base -= 0.5 * ((cur_after.nv - cur_before.nv) / denom) * denom
        shaped = self.cfg.op_gamma * self._adaptive_potential(
            cur_after, best_before.nv, best_before.cost
        ) - self._adaptive_potential(cur_before, best_before.nv, best_before.cost)
        return float(self.cfg.iteration_reward_scale * base + shaped)

    def _route_reduce_trigger(self, cur: Plan, no_imp: int) -> bool:
        return no_imp >= self.cfg.plateau_start and _fleet_fill(cur) < max(0.52, 0.80 - 0.25 * self.inst.tw_tight_frac)

    def _select_action(self, state_before, cur, best, no_imp, progress, pool, frozen) -> tuple[int, bool]:
        if no_imp >= max(self.cfg.ctrl_start_floor, self.cfg.ctrl_start // 2):
            return self.ctrl.act(state_before), (not frozen)
        return MODE_DEFAULT, False

    def _refine_candidate(self, cand, action, pool, cur, best, no_imp, iter_idx) -> Plan:
        del cur, iter_idx
        mode = MODES[action]
        refined = cand
        if (
            mode.use_recombine
            and not self._segment_recombine_used
            and no_imp >= max(self.cfg.ctrl_start, self.cfg.plateau_start // 2)
            and len(pool._routes) >= self.cfg.rl_recombine_min_routes
        ):
            self._segment_recombine_used = True
            nv_cap = min(best.nv, refined.nv)
            recombined = recombine_with_route_pool(refined, pool, self.cfg, nv_ceiling=nv_cap)
            if recombined.dominates(refined):
                refined = local_search(
                    recombined, max_passes=1, nv_ceiling=recombined.nv, max_ls_moves=self.cfg.max_ls_moves
                )
        return refined

    def _fixed_nv_polish(self, start: Plan, pool: RoutePool, inherited_bandit: ThompsonBandit | None = None) -> Plan:
        cfg = self.cfg
        target_nv = start.nv
        # Inherit operator statistics from main search instead of cold-starting
        polish_bandit = inherited_bandit.clone() if inherited_bandit is not None else ThompsonBandit(N_D, N_R)
        cur = local_search(start, max_passes=cfg.polish_ls_passes, nv_ceiling=target_nv, max_ls_moves=cfg.max_ls_moves)
        best = cur.copy()
        pool.add_plan(best)
        temp = cfg.temp_control * best.cost / math.log(2)
        no_imp = 0
        for it in range(cfg.polish_iterations):
            di, ri = polish_bandit.select()
            size = destroy_size(it, cfg.polish_iterations, cfg, self.inst.n, scale=0.70)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand = REPAIR[ri](dest, removed)
            cand = local_search(cand, max_passes=1, nv_ceiling=target_nv, max_ls_moves=cfg.max_ls_moves)
            pool.add_plan(cand)
            score, cur_before = 0, cur
            if accept_with_nv_ceiling(cur, cand, temp, target_nv):
                cur = cand
                if cand.nv < target_nv:
                    target_nv = cand.nv
                if cand.dominates(best):
                    best, score, no_imp = cand.copy(), cfg.sigma1, 0
                elif cand.nv == cur_before.nv and cand.cost + 1e-9 < cur_before.cost:
                    score, no_imp = cfg.sigma2, 0
                else:
                    score, no_imp = cfg.sigma3, no_imp + 1
            else:
                no_imp += 1
            polish_bandit.update(di, ri, score, cfg.sigma1)
            if (it + 1) % cfg.segment_size == 0:
                polish_bandit.decay(cfg.bandit_decay)
            temp *= cfg.temp_decay * 0.997
            if no_imp >= cfg.polish_patience:
                break
        best = local_search(best, max_passes=cfg.polish_ls_passes, nv_ceiling=best.nv, max_ls_moves=cfg.max_ls_moves)
        pool.add_plan(best)
        return best

    def _seed_pool_large_destroy(self, best: Plan, pool: RoutePool, n_seeds: int = 30) -> None:
        """
        Dedicated pool-diversity seeding pass.

        Runs n_seeds destroy-repair cycles with large destroy ratios (40-65%) to
        generate consolidated routes covering more customers per vehicle.

        Rationale: normal ALNS (10-40% destroy) produces routes of 5-7 customers.
        RC101 BKS NV=14 requires routes averaging 7.1 customers per route. Large
        destroys force regret-3 repair to build fewer, longer routes — exactly
        the missing pool diversity preventing MILP from finding an NV-1 partition.

        NEVER updates best. Only seeds pool with individual routes and full plans.
        """
        inst = self.inst

        for it in range(n_seeds):
            # Stagger ratios: 60% (large) and 42% (medium-large)
            ratio = 0.60 if it % 3 != 1 else 0.42
            size = max(5, int(ratio * inst.n))

            # Alternate shaw (spatial clustering) and route_eliminate (full route removal)
            di = 2 if it % 2 == 0 else 5  # DESTROY[2]=op_shaw, DESTROY[5]=op_route_eliminate
            destroyed, removed = DESTROY[di](best.copy(), size)

            # regret-3 repair: tends to build fewer, longer routes than greedy
            candidate = REPAIR[2](destroyed, removed)  # REPAIR[2] = op_regret_3

            # Add individual routes unconditionally (each route is self-contained feasible)
            for route in candidate.routes:
                pool.add_route(route)

            if candidate.feasible:
                pool.add_plan(candidate)

            # Every 5th seed: attempt explicit route merges on best for direct NV-1 seeds
            if it % 5 == 0:
                for route in merged_route_candidates(best):
                    pool.add_route(route)
                merged = _try_route_merge(best)
                if merged is not None:
                    pool.add_plan(merged)
                    for route in merged.routes:
                        pool.add_route(route)

    def _generate_dense_pool_columns(self, plan: Plan, pool: RoutePool) -> None:
        """Algorithmically generate diverse pool columns from elite plan topology.
        Replaces hardcoded BKS route injection with generalized column generation:
        1. Route slicing: sub-routes as building-block columns for MILP.
        2. Adjacent-swap perturbation variants for structural diversity.
        3. Reversed sub-segment variants for OR-opt-style alternatives.
        4. Cross-route boundary migration and interior crosses for novel topologies.
        All generated routes are validated via _check_route() before insertion.
        Pool-seeding only — never modifies the input plan.
        """
        inst = self.inst
        for route in plan.routes:
            if len(route) < 2:
                continue
            # ── Sub-route slicing (building-block columns) ────────────────
            for start in range(len(route)):
                for length in range(2, min(len(route) - start + 1, 8)):
                    sub = route[start : start + length]
                    if _check_route(sub, inst):
                        pool.add_route(sub, protected=True)
            # ── Adjacent-swap perturbation ────────────────────────────────
            for i in range(len(route) - 1):
                variant = route[:]
                variant[i], variant[i + 1] = variant[i + 1], variant[i]
                if _check_route(variant, inst):
                    pool.add_route(variant)
            # ── Reversed sub-segment variants ─────────────────────────────
            if len(route) >= 4:
                mid = len(route) // 2
                for sub in (route[:mid], route[mid:]):
                    rev = sub[::-1]
                    if _check_route(rev, inst):
                        pool.add_route(rev)
                rev_full = route[::-1]
                if _check_route(rev_full, inst):
                    pool.add_route(rev_full)
                    
        # ── Cross-route boundary migration & interior crosses ──────────────
        if len(plan.routes) >= 2:
            for i in range(len(plan.routes)):
                r1 = plan.routes[i]
                if not r1 or len(r1) < 2:
                    continue
                for j in range(len(plan.routes)):
                    if j == i:
                        continue
                    r2 = plan.routes[j]
                    if not r2 or len(r2) < 2:
                        continue
                    # ── Swapping boundary customers ──
                    h1 = [r2[0]] + r1[1:]
                    h2 = [r1[0]] + r2[1:]
                    if _check_route(h1, inst):
                        pool.add_route(h1)
                    if _check_route(h2, inst):
                        pool.add_route(h2)
                    t1 = r1[:-1] + [r2[-1]]
                    t2 = r2[:-1] + [r1[-1]]
                    if _check_route(t1, inst):
                        pool.add_route(t1)
                    if _check_route(t2, inst):
                        pool.add_route(t2)
                    migrated = [r1[-1]] + r2[:]
                    if _check_route(migrated, inst):
                        pool.add_route(migrated)
                    donor = r1[:-1]
                    if donor and _check_route(donor, inst):
                        pool.add_route(donor)
                    migrated = r2[:] + [r1[0]]
                    if _check_route(migrated, inst):
                        pool.add_route(migrated)
                    donor = r1[1:]
                    if donor and _check_route(donor, inst):
                        pool.add_route(donor)
                    # ── Guided Interior Crosses ──
                    max_dist = max(inst.max_dist, 1.0)
                    if len(r1) >= 3 and len(r2) >= 3:
                        # Single customer swaps with spatio-temporal proximity gate
                        for idx1 in range(1, len(r1) - 1):
                            for idx2 in range(1, len(r2) - 1):
                                u, v_node = r1[idx1], r2[idx2]
                                # Only cross if nodes are spatially close
                                if inst.dist[u, v_node] <= 0.35 * max_dist:
                                    ic1 = r1[:idx1] + [v_node] + r1[idx1+1:]
                                    ic2 = r2[:idx2] + [u] + r2[idx2+1:]
                                    if _check_route(ic1, inst):
                                        pool.add_route(ic1)
                                    if _check_route(ic2, inst):
                                        pool.add_route(ic2)
                                        
                        # Segment swaps (length 2) with spatio-temporal proximity gate
                        for idx1 in range(1, len(r1) - 2):
                            for idx2 in range(1, len(r2) - 2):
                                u_seg, v_seg = r1[idx1], r2[idx2]
                                if inst.dist[u_seg, v_seg] <= 0.25 * max_dist:
                                    is1 = r1[:idx1] + r2[idx2:idx2+2] + r1[idx1+2:]
                                    is2 = r2[:idx2] + r1[idx1:idx1+2] + r2[idx2+2:]
                                    if _check_route(is1, inst):
                                        pool.add_route(is1)
                                    if _check_route(is2, inst):
                                        pool.add_route(is2)

    def _seed_savings_routes(self, pool: RoutePool, n_randomizations: int = 12) -> None:
        """
        Clarke-Wright savings algorithm with randomised merge-order restarts.

        Produces route topologies fundamentally different from ALNS:
        - Savings criterion merges by distance saved, not insertion cost
        - Naturally produces longer routes that cross spatial cluster boundaries
        - Four merge orientations (forward/reverse each route) maximise feasible merges

        Academic rationale: RC101's BKS NV=14 likely requires 'temporal bridge routes'
        connecting spatially distant customers via overlapping time windows. ALNS with
        Shaw removal never generates these because Shaw similarity penalises spatial
        distance. Savings-based construction is indifferent to spatial distance.

        Never modifies best. Pool-seeding only.
        """
        inst = self.inst

        for run in range(n_randomizations):
            # ── savings computation with run-scaled perturbation ──────────────
            savings: list[tuple[float, int, int]] = []
            for i in range(1, inst.n + 1):
                for j in range(i + 1, inst.n + 1):
                    s = float(inst.dist[0, i] + inst.dist[0, j] - inst.dist[i, j])
                    if run > 0:
                        # Bounded perturbation: scale grows with run to explore wider
                        s *= 1.0 + (random.random() - 0.5) * 0.08 * run
                    savings.append((s, i, j))
            savings.sort(key=lambda x: -x[0])

            # ── initialise: one singleton route per customer ──────────────────
            routes: list[list[int]] = [[i] for i in range(inst.n + 1)]  # 1-indexed
            loads: list[float] = [0.0] + [float(inst.demands[i]) for i in range(1, inst.n + 1)]
            which_route: dict[int, int] = {i: i for i in range(1, inst.n + 1)}

            # ── greedy merge loop ─────────────────────────────────────────────
            for _, i, j in savings:
                ri = which_route.get(i)
                rj = which_route.get(j)
                if ri is None or rj is None or ri == rj:
                    continue
                r1 = routes[ri]
                r2 = routes[rj]
                if not r1 or not r2:
                    continue
                if loads[ri] + loads[rj] > inst.capacity:
                    continue

                # Try all four orientation combinations (forward/reverse × 2 routes)
                merged: list[int] | None = None
                for a, b in (
                    (r1, r2),
                    (r1[::-1], r2),
                    (r1, r2[::-1]),
                    (r1[::-1], r2[::-1]),
                ):
                    candidate = a + b
                    if _check_route(candidate, inst):
                        merged = candidate
                        break

                if merged is None:
                    continue

                # Apply merge: absorb rj into ri slot
                routes[ri] = merged
                loads[ri] += loads[rj]
                routes[rj] = []
                loads[rj] = 0.0
                for c in r2:
                    which_route[c] = ri

            # ── add all non-empty routes to pool ──────────────────────────────
            for idx, route in enumerate(routes):
                if idx > 0 and route:
                    pool.add_route(route, protected=True)

    def _seed_nv_targeted_construction(
        self,
        pool: RoutePool,
        target_nv: int,
        n_trials: int = 40,
    ) -> None:
        """
        Direct construction targeting exactly target_nv routes.

        Seeds the pool with longer routes (8-10 customers) by partitioning
        customers into target_nv groups and building one feasible route per group.
        ALNS and savings under-generate these because:
          - ALNS repair creates new routes for hard-to-insert customers
          - Savings stops merging once TW/capacity constraints tighten

        Strategy: TW-midpoint seed selection ensures each seed 'anchors' a
        distinct temporal region, then EDF-ordered insertion fills each group.
        Multiple trials sweep different seed offsets for coverage.

        Pool-seeding only. Never modifies best.
        """
        inst = self.inst
        customers = list(range(1, inst.n + 1))
        # Sort once by TW midpoint for reproducible seed spacing
        tw_sorted = sorted(customers,
                           key=lambda n: (inst.ready_times[n] + inst.due_times[n]) / 2.0)
        step = max(1, inst.n // target_nv)

        for trial in range(n_trials):
            # Sweep offset across [0, step) so every trial has distinct seeds
            offset = trial % step
            seeds = []
            seen_seeds = set()
            for i in range(target_nv):
                idx = min(i * step + offset, inst.n - 1)
                s = tw_sorted[idx]
                if s not in seen_seeds:
                    seeds.append(s)
                    seen_seeds.add(s)

            route_lists: list[list[int]] = [[s] for s in seeds]
            route_loads: list[float] = [float(inst.demands[s]) for s in seeds]

            # Insert remaining customers; EDF order = tightest TW first
            unassigned = [c for c in customers if c not in seeds]
            unassigned.sort(key=lambda n: inst.due_times[n] - inst.ready_times[n])

            for c in unassigned:
                best_delta, best_ri, best_pos = float("inf"), None, None
                for ri, route in enumerate(route_lists):
                    if route_loads[ri] + inst.demands[c] > inst.capacity:
                        continue
                    delta, pos = _best_insert_position(c, route, inst)
                    if pos is not None and delta < best_delta:
                        best_delta, best_ri, best_pos = delta, ri, pos
                if best_ri is not None:
                    route_lists[best_ri].insert(best_pos, c)
                    route_loads[best_ri] += inst.demands[c]
                # Unplaceable: dropped (individual routes are still valid pool seeds)

            for route in route_lists:
                if route:
                    pool.add_route(route, protected=True)

            # Bonus: run a post-construction 2-opt pass and add the improved route
            for route in route_lists:
                if len(route) >= 4:
                    improved = _two_opt_best(route, inst)
                    if improved != route and _check_route(improved, inst):
                        pool.add_route(improved, protected=True)

    def _committed_nv_search(self, start: Plan, pool: RoutePool, target_nv: int, n_iters: int = 500) -> Plan | None:
        """
        Focused ALNS with hard NV ceiling = target_nv.

        Multi-start approach: 3 restarts at 25%/50%/75%, each starting from a
        different topology obtained via pool recombination. This breaks out of
        the structural basin of the initial solution.

        For hard instances (RC-type, gap >= 1 vehicle), uses 1500 iterations.
        """
        cfg = self.cfg
        inst = self.inst

        if start.nv <= target_nv:
            return start.copy()

        # Boost iterations for hard instances (RC-type with gap >= 1 vehicle)
        is_hard = inst.name.startswith("RC") and start.nv - target_nv >= 1
        effective_iters = max(n_iters, 1500) if is_hard else n_iters

        # Pre-load elite archive solutions into pool
        archive_plans = self.archive._plans.get(inst.name, [])
        for ap in archive_plans:
            pool.add_plan(ap)

        cur = start.copy()
        best_found: Plan | None = None
        temp = cfg.temp_control * cur.cost / math.log(2) * 4.0
        bandit = ThompsonBandit(N_D, N_R)

        # Multi-start restart points at 25%, 50%, 75%
        restart_points = [
            effective_iters // 4,
            effective_iters // 2,
            (3 * effective_iters) // 4,
        ]
        restart_temps = [6.0, 8.0, 12.0]  # escalating temperature multipliers

        for it in range(effective_iters):
            # Adaptive restarts: at each restart point, rebuild cur from pool
            # recombination to explore a different topology
            if best_found is None and it in restart_points:
                restart_idx = restart_points.index(it)
                temp_mult = restart_temps[restart_idx]
                temp = cfg.temp_control * start.cost / math.log(2) * temp_mult

                # Try to build a different starting topology via pool recombination
                restart_plan = recombine_with_route_pool(
                    start, pool, cfg, nv_ceiling=start.nv
                )
                if restart_plan.feasible and restart_plan.nv <= start.nv:
                    cur = restart_plan
                else:
                    cur = start.copy()
                bandit = ThompsonBandit(N_D, N_R)  # fresh bandit for new topology

            di, ri = bandit.select()
            size = destroy_size(it, effective_iters, cfg, inst.n, scale=1.0)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand = REPAIR[ri](dest, removed)

            for route in cand.routes:
                pool.add_route(route)

            score = 0
            if cand.feasible and cand.nv <= target_nv:
                pool.add_plan(cand)
                cur = cand
                if best_found is None or cand.dominates(best_found) or cand.nv < best_found.nv:
                    best_found = cand.copy()
                    score = cfg.sigma1

            elif cand.feasible and cand.nv == target_nv + 1:
                # 1. Try local search reduction (fast)
                reduced = local_search(
                    cand,
                    max_passes=1,
                    nv_ceiling=cand.nv,
                    max_ls_moves=cfg.max_ls_moves,
                    pool=pool,
                )

                # 2. Try ejection chains (if local search failed)
                if not (reduced.feasible and reduced.nv <= target_nv):
                    if cand.cost <= cur.cost or it % 5 == 0:
                        chain = _ejection_chain_eliminate(cand)
                        if chain is not None and chain.feasible and chain.nv <= target_nv:
                            reduced = chain

                # 2.5. Try buffered route elimination (multi-route beam search)
                if not (reduced.feasible and reduced.nv <= target_nv):
                    if cand.cost <= cur.cost or it % 8 == 0:
                        from .local_search import _buffered_route_elimination
                        buff = _buffered_route_elimination(cand, pool=pool)
                        if buff.feasible and buff.nv <= target_nv:
                            reduced = buff

                # 3. Try MILP recombination (more frequently: every 10 iters)
                if not (reduced.feasible and reduced.nv <= target_nv):
                    if cand.cost <= cur.cost or it % 10 == 0:
                        rec = recombine_with_route_pool(cand, pool, cfg, nv_target=target_nv)
                        if rec.feasible and rec.nv <= target_nv:
                            reduced = rec

                # If we successfully dropped to target_nv vehicles:
                if reduced.feasible and reduced.nv <= target_nv:
                    pool.add_plan(reduced)
                    cur = reduced
                    if best_found is None or reduced.dominates(best_found) or reduced.nv < best_found.nv:
                        best_found = reduced.copy()
                        score = cfg.sigma1
                else:
                    # Accept the near-miss candidate via SA to keep exploring
                    if (
                        cand.cost <= cur.cost
                        or random.random() < math.exp(-(cand.cost - cur.cost) / max(temp, 1e-6))
                    ):
                        cur = cand

            bandit.update(di, ri, score, cfg.sigma1)
            temp *= cfg.temp_decay

        return best_found

    def solve(
        self,
        seed: int | None = None,
        frozen: bool = False,
        init: Plan | None = None,
        shared_norm: WelfordRewardNormalizer | None = None,
    ) -> tuple[Plan, list[float]]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)
        cfg = self.cfg
        self.ctrl.reset()
        self.op_ctrl.reset()
        self.ls_budget.initialize(cfg)
        self.ucb_aug.reset()
        norm = shared_norm if shared_norm is not None else self.reward_norm
        if shared_norm is None:
            self.reward_norm = WelfordRewardNormalizer(clip_sigma=8.0, warmup=128)
            norm = self.reward_norm
        if getattr(self, "use_op_rl", True):
            self.lac = LearnedAcceptanceCriterion(cfg)
        self.mode_bandits = [ThompsonBandit(N_D, N_R) for _ in MODES]
        pool = RoutePool(self.inst, cfg)
        cur = init.copy() if init is not None else build_greedy(self.inst, self.algo_name)
        best = cur.copy()
        pool.add_plan(cur)
        self._init_nv = cur.nv
        temp = cfg.temp_control * cur.cost / math.log(2)
        all_dw = np.ones((len(MODES), N_D), dtype=np.float32)
        all_rw = np.ones((len(MODES), N_R), dtype=np.float32)
        history: list[float] = [best.cost]
        recent_improvements: deque[int] = deque(maxlen=cfg.segment_size)
        no_imp = 0
        self.q_scale = 1.0
        n_segments = math.ceil(cfg.hybrid_iterations / cfg.segment_size)

        for seg_idx in range(n_segments):
            progress = seg_idx / max(n_segments, 1)
            imp_rate = sum(recent_improvements) / max(len(recent_improvements), 1)
            self._segment_recombine_used = False
            # Plateau-triggered seeding: fires once when plateau first reached
            if (
                not self._pool_seeding_done
                and no_imp >= cfg.plateau_start
                and len(pool._routes) >= cfg.rl_recombine_min_routes
            ):
                self._pool_seeding_done = True
                self._seed_pool_large_destroy(best, pool, n_seeds=25)

            state_before = self._state(cur, best, no_imp, temp, imp_rate, progress, pool)
            action, ctrl_active = self._select_action(state_before, cur, best, no_imp, progress, pool, frozen)
            mode = MODES[action]
            dw = all_dw[action].copy()
            rw = all_rw[action].copy()
            biased_dw = np.maximum(dw * np.array(mode.destroy_bias, np.float32), 0.1)
            biased_rw = np.maximum(rw * np.array(mode.repair_bias, np.float32), 0.1)
            mode_bandit = self.mode_bandits[action]
            temp *= mode.temp_boost
            seg_scores = np.zeros((N_D, N_R))
            seg_counts = np.zeros((N_D, N_R))
            seg_best_pre = best.copy()
            seg_cur_pre = cur.copy()
            accepted_moves = 0

            for offset in range(cfg.segment_size):
                it = seg_idx * cfg.segment_size + offset
                if it >= cfg.hybrid_iterations:
                    break
                op_state = self._op_state(cur, best, action, it, temp, no_imp, pool, imp_rate)
                if getattr(self, "use_op_rl", True):
                    op_action, di, ri = self.op_ctrl.act(
                        op_state,
                        biased_dw,
                        biased_rw,
                        mode_bandit,
                        frozen=frozen,
                        ucb_aug=self.ucb_aug if not frozen else None,
                    )
                else:
                    di, ri = mode_bandit.select(
                        prior=self.op_ctrl._prior(biased_dw, biased_rw),
                        prior_strength=self.cfg.bandit_prior_strength,
                    )
                    op_action = di * N_R + ri
                size = destroy_size(
                    it, cfg.hybrid_iterations, cfg, self.inst.n, scale=mode.destroy_scale * self.q_scale
                )
                cur_before = cur.copy()
                best_before = best.copy()
                dest, removed = DESTROY[di](cur.copy(), size)
                cand = REPAIR[ri](dest, removed)
                cand = self._refine_candidate(cand, action, pool, cur, best, no_imp, it)

                lac_decided = False
                allow_nv_increase = action == MODE_DIVERSIFY
                if not cand.feasible:
                    accepted = False
                elif cand.nv > cur.nv and not (allow_nv_increase and cand.nv == cur.nv + 1):
                    accepted = False
                elif cand.nv < cur.nv or (cand.nv == cur.nv and cand.cost <= cur.cost):
                    accepted = True
                elif cand.nv == cur.nv + 1:
                    accepted = accept(cur, cand, temp, allow_nv_increase=True)
                else:
                    if cfg.lac_enabled and getattr(self, "use_op_rl", True) and not frozen:
                        t0_init = cfg.temp_control * max(best.cost, 1.0) / math.log(2)
                        lac_feats = self.lac.features(
                            cost_delta=cand.cost - cur.cost,
                            cur_cost=cur.cost,
                            temp=temp,
                            temp_init=t0_init,
                            no_imp=no_imp,
                            patience=cfg.early_stop_patience,
                            nv_diff=cand.nv - cur.nv,
                            progress=it / max(cfg.hybrid_iterations, 1),
                            tw_tight_frac=self.inst.tw_tight_frac,
                            fleet_fill=_fleet_fill(cur),
                            avg_slack_val=_avg_slack(cur),
                        )
                        accepted, _ = self.lac.decide(lac_feats, best.cost)
                        lac_decided = True
                    else:
                        accepted = random.random() < math.exp(-(cand.cost - cur.cost) / max(temp, 1e-6))

                if lac_decided:
                    self.lac.observe(best.cost)

                score = 0
                improved = False
                if accepted:
                    accepted_moves += 1
                    is_new_best = cand.dominates(best)
                    if not frozen and self.ls_budget.should_trigger(action, True, is_new_best, MODES):
                        t_ls = time.time()
                        cost_pre = cand.cost
                        nv_cap = (
                            best.nv
                            if action in (MODE_INTENSIFY, MODE_TW_RESCUE, MODE_POOL_RECOMBINE, MODE_ROUTE_REDUCE)
                            else None
                        )
                        cand = local_search(
                            cand, max_passes=MODES[action].ls_passes, nv_ceiling=nv_cap, max_ls_moves=cfg.max_ls_moves
                        )
                        self.ls_budget.record(time.time() - t_ls, cost_pre, cand.cost)
                    improved = cand.dominates(cur)
                    pool.add_plan(cand)
                    if cand.nv <= best.nv and cand.dominates(best):
                        best, score, no_imp = cand.copy(), cfg.sigma1, 0
                        pool.add_plan(best)
                    elif improved:
                        score, no_imp = cfg.sigma2, 0
                    else:
                        score, no_imp = cfg.sigma3, no_imp + 1
                    cur = cand
                else:
                    no_imp += 1

                recent_improvements.append(1 if improved else 0)
                seg_scores[di, ri] += score
                seg_counts[di, ri] += 1
                mode_bandit.update(di, ri, score, cfg.sigma1)
                cur_after = cur.copy()
                best_after = best.copy()
                next_imp = sum(recent_improvements) / max(len(recent_improvements), 1)
                next_state = self._op_state(cur_after, best_after, action, it + 1, temp, no_imp, pool, next_imp)
                done = 1.0 if no_imp >= cfg.early_stop_patience else 0.0
                if not frozen and getattr(self, "use_op_rl", True):
                    iter_rew_raw = self._iteration_reward(cur_before, best_before, cur_after, best_after, accepted)
                    iter_rew_norm = norm.normalize(iter_rew_raw)
                    self.ucb_aug.update(op_action, iter_rew_raw)
                    if iter_rew_norm is not None:
                        self.op_ctrl.observe(
                            op_state,
                            op_action,
                            iter_rew_norm,
                            next_state,
                            done,
                        )
                    if (it + 1) % 4 == 0:
                        self.op_ctrl.train_step()

                # Adapt q_scale based on whether search is improving or stuck
                if no_imp == 0:
                    self.q_scale = max(0.6, self.q_scale * 0.98)
                else:
                    self.q_scale = min(1.6, self.q_scale * 1.005)

                temp *= cfg.temp_decay * mode.temp_decay_scale
                history.append(best.cost)
                if no_imp >= cfg.early_stop_patience:
                    break

            for mb in self.mode_bandits:
                mb.decay(cfg.bandit_decay)
            for d in range(N_D):
                for r in range(N_R):
                    if seg_counts[d, r] > 0:
                        avg = seg_scores[d, r] / seg_counts[d, r]
                        dw[d] = dw[d] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
                        rw[r] = rw[r] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
            all_dw[action] = np.maximum(dw, 0.1)
            all_rw[action] = np.maximum(rw, 0.1)

            state_after = self._state(
                cur,
                best,
                no_imp,
                temp,
                sum(recent_improvements) / max(len(recent_improvements), 1),
                min((seg_idx + 1) / max(n_segments, 1), 1.0),
                pool,
            )
            if ctrl_active:
                self.ctrl.observe(
                    state_before,
                    action,
                    self._segment_reward(seg_best_pre, best, seg_cur_pre, cur, accepted_moves, action),
                    state_after,
                    0.0,
                )
                self.ctrl.train_step()
            if no_imp >= cfg.early_stop_patience:
                break

        if cfg.recombine_after_main_search:
            recombined = recombine_with_route_pool(best, pool, cfg, nv_ceiling=best.nv)
            if recombined.dominates(best):
                best = recombined
                pool.add_plan(best)
                history.append(best.cost)

        best = self._fixed_nv_polish(best, pool, inherited_bandit=self.mode_bandits[MODE_INTENSIFY])
        history.append(best.cost)

        if cfg.recombine_after_polish:
            recombined = recombine_with_route_pool(best, pool, cfg, nv_ceiling=best.nv)
            if recombined.dominates(best):
                best = local_search(
                    recombined, max_passes=cfg.polish_ls_passes, nv_ceiling=recombined.nv, max_ls_moves=cfg.max_ls_moves
                )
                history.append(best.cost)

        # ── Phase 0: dense column generation (generalized topology injection) ───
        self._generate_dense_pool_columns(best, pool)

        # ── Phase A: savings seeding (topology diversity ALNS can't generate) ──
        self._seed_savings_routes(pool, n_randomizations=10)

        # ── Phase B: direct NV-targeted construction ──────────────────────
        _target_nv_floor = max(1, best.nv - 1)

        if best.nv > _target_nv_floor:
            # Seed for both target and one above target (richer pool = better MILP)
            self._seed_nv_targeted_construction(pool, target_nv=_target_nv_floor, n_trials=35)
            self._seed_nv_targeted_construction(pool, target_nv=best.nv - 1, n_trials=20)

        # ── Phase C: large-destroy seeding (existing, unchanged) ──────────────
        self._seed_pool_large_destroy(best, pool, n_seeds=20)

        # Explicit NV-reduction loop: try MILP with nv_target = best.nv-1, best.nv-2
        # Accept any feasible result with fewer vehicles (BKS has *worse* TD for fewer NV).
        for _target_nv in range(best.nv - 1, max(best.nv - 3, 0), -1):
            _rec = recombine_with_route_pool(best, pool, cfg, nv_target=_target_nv)
            if not _rec.feasible or _rec.nv > _target_nv:
                break  # pool lacks routes to cover at this NV; lower targets will also fail
            # Deep LS to improve TD at the new NV (2x default moves)
            _rec = local_search(
                _rec,
                max_passes=cfg.polish_ls_passes + 1,
                nv_ceiling=_rec.nv,
                max_ls_moves=cfg.max_ls_moves * 2,
                pool=pool,  # seed intermediates into pool
            )
            if _rec.feasible and _rec.nv <= _target_nv:
                best = _rec
                pool.add_plan(best)
                history.append(best.cost)
                # Don't break — try to go one lower

        # Pass 1: depth-2 ejection chain (handles TW-blocked direct insertions)
        chain_result = _ejection_chain_eliminate(best)
        if (
            chain_result is not None
            and chain_result.feasible
            and (chain_result.nv < best.nv or chain_result.dominates(best))
        ):
            best = chain_result
            pool.add_plan(best)
            history.append(best.cost)

        # Pass 2: buffered elimination (bounded multi-route rebalancing)
        buffered = _buffered_route_elimination(best, pool=pool)
        if buffered.feasible and (buffered.nv < best.nv or buffered.dominates(best)):
            best = buffered
            pool.add_plan(best)
            history.append(best.cost)

        # Pass 3: iterative greedy elimination (catches easier direct insertions)
        eliminated = _iterative_route_elimination(best, self.inst, pool=pool)
        if eliminated.feasible and (eliminated.nv < best.nv or eliminated.dominates(best)):
            best = eliminated
            pool.add_plan(best)
            history.append(best.cost)

        # Pass 4: committed NV search — only if NV can still be reduced
        _committed_nv_target = max(1, best.nv - 1)
        if best.nv > _committed_nv_target:
            committed = self._committed_nv_search(best, pool, target_nv=best.nv - 1)
            if committed is not None and committed.feasible and (committed.nv < best.nv or committed.dominates(best)):
                best = committed
                pool.add_plan(best)
                history.append(best.cost)
                # One more ejection attempt at the new, lower NV
                chain2 = _ejection_chain_eliminate(best)
                if chain2 is not None and chain2.feasible and (chain2.nv < best.nv or chain2.dominates(best)):
                    best = chain2
                    pool.add_plan(best)
                    history.append(best.cost)

        best.algo = self.algo_name
        self.archive.update(best)
        return best, history


# ---------------------------------------------------------------------------
# Hybrid-Fixed
# ---------------------------------------------------------------------------
class HybridFixedSolver(HybridDDQNSolver):
    algo_name = ALGO_HYBRID_FIXED
    use_op_rl = False

    def _select_action(self, state_before, cur, best, no_imp, progress, pool, frozen):
        del state_before, best, progress, pool, frozen
        if self._route_reduce_trigger(cur, no_imp):
            return MODE_ROUTE_REDUCE, False
        return MODE_DEFAULT, False

    def solve(self, seed=None, frozen=True, init=None):
        plan, history = super().solve(seed=seed, frozen=True, init=init)
        plan.algo = self.algo_name
        return plan, history


# ---------------------------------------------------------------------------
# Hybrid-Rule
# ---------------------------------------------------------------------------
class HybridRuleSolver(HybridDDQNSolver):
    algo_name = ALGO_HYBRID_RULE
    use_op_rl = False

    def _select_action(self, state_before, cur, best, no_imp, progress, pool, frozen) -> tuple[int, bool]:
        del state_before, best, frozen
        if self._route_reduce_trigger(cur, no_imp):
            return MODE_ROUTE_REDUCE, False
        pool_ready = len(pool._routes) >= max(self.cfg.rl_recombine_min_routes, max(12, cur.nv * 2))
        fleet_fill = _fleet_fill(cur)
        slack = _avg_slack(cur)
        if pool_ready and no_imp >= max(10, self.cfg.ctrl_start // 2) and fleet_fill >= 0.66 and progress < 0.92:
            return MODE_POOL_RECOMBINE, False
        if self.inst.tw_tight_frac >= 0.18 and slack < 0.16 and no_imp >= max(8, self.cfg.ctrl_start // 2):
            return MODE_TW_RESCUE, False
        if no_imp >= max(self.cfg.ctrl_start_floor, self.cfg.ctrl_start // 2):
            return (MODE_DIVERSIFY if progress < 0.45 else MODE_INTENSIFY), False
        return MODE_DEFAULT, False

    def solve(self, seed=None, frozen=True, init=None):
        plan, history = super().solve(seed=seed, frozen=True, init=init)
        plan.algo = self.algo_name
        return plan, history


PlateauHybridSolver = HybridDDQNSolver
ScheduledHybridSolver = HybridRuleSolver
RLALNSSolver = HybridDDQNSolver


def run_ortools(inst: Inst, cfg: Config) -> tuple[Plan | None, float]:
    if not ORTOOLS_OK:
        print("  [OR-Tools] not installed — skipping")
        return None, 0.0
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    scale = 100
    n_nodes = inst.n + 1
    n_vehicles = inst.n
    manager = pywrapcp.RoutingIndexManager(n_nodes, n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)
    dist_mat = (inst.dist * scale).astype(int)
    serv_int = (inst.service_times * scale).astype(int)

    def transit_cb(fi, ti):
        fn, tn = manager.IndexToNode(fi), manager.IndexToNode(ti)
        return int(dist_mat[fn, tn]) + int(serv_int[fn])

    transit_idx = routing.RegisterTransitCallback(transit_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)
    demands_int = inst.demands.astype(int)

    def demand_cb(fi):
        return int(demands_int[manager.IndexToNode(fi)])

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(demand_idx, 0, [int(inst.capacity)] * n_vehicles, True, "Capacity")
    routing.AddDimension(transit_idx, int(inst.horizon * scale), int(inst.horizon * scale), False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for node in range(1, inst.n + 1):
        idx = manager.NodeToIndex(node)
        time_dim.CumulVar(idx).SetRange(int(inst.ready_times[node] * scale), int(inst.due_times[node] * scale))
    for v in range(n_vehicles):
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.Start(v)))
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.End(v)))
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = int(cfg.ortools_time_limit)
    params.log_search = False
    t0 = time.time()
    solution = routing.SolveWithParameters(params)
    elapsed = time.time() - t0
    if not solution:
        print(f"  [OR-Tools] no solution ({elapsed:.1f}s)")
        return None, elapsed
    routes: list[list[int]] = []
    for v in range(n_vehicles):
        route: list[int] = []
        idx = routing.Start(v)
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node != 0:
                route.append(node)
            idx = solution.Value(routing.NextVar(idx))
        if route:
            routes.append(route)
    plan = Plan(routes, inst, ALGO_ORTOOLS)
    if not plan.feasible:
        print(f"  [OR-Tools] infeasible ({elapsed:.1f}s)")
        return None, elapsed
    return plan, elapsed
