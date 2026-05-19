from __future__ import annotations
import random
import math
import time
from collections import deque
from typing import List, Dict, Tuple, Optional, Deque
import numpy as np
import torch
from .config import Config, MODES, BKS, ALGO_ALNS_BASE, ALGO_HYBRID_FIXED, ALGO_HYBRID_RULE, ALGO_HYBRID_DDQN, MODE_DEFAULT, MODE_INTENSIFY, MODE_DIVERSIFY, MODE_TW_RESCUE, MODE_POOL_RECOMBINE, MODE_ROUTE_REDUCE, ALGO_ORTOOLS
from .core import Inst, Plan, _avg_slack, _plan_spread, _fleet_fill
from .heuristics import build_greedy
from .operators import DESTROY, REPAIR, accept, accept_with_nv_ceiling, destroy_size, N_D, N_R
from .local_search import local_search, _iterative_route_elimination
from .pool import RoutePool, recombine_with_route_pool
from .rl import PrioritizedReplayBuffer, ThompsonBandit, EliteArchive, PlateauController, OperatorController, LearnedAcceptanceCriterion, DEVICE

try:
    from ortools.constraint_solver import routing_enums_pb2, pywrapcp as _pywrapcp
    ORTOOLS_OK = True
except Exception:
    ORTOOLS_OK = False

class ALNSSolver:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst   = inst
        self.cfg    = cfg
        self.bandit = ThompsonBandit(N_D, N_R)

    def solve(self, seed: Optional[int] = None,
              init: Optional[Plan] = None) -> Tuple[Plan, List[float]]:
        if seed is not None:
            random.seed(seed); np.random.seed(seed)
        cfg        = self.cfg
        self.bandit= ThompsonBandit(N_D, N_R)
        cur  = init.copy() if init is not None else build_greedy(self.inst, ALGO_ALNS_BASE)
        best = cur.copy()
        temp = cfg.temp_control * cur.cost / math.log(2)
        history  = [best.cost]
        no_imp   = 0
        for it in range(cfg.alns_iterations):
            di, ri  = self.bandit.select()
            size    = destroy_size(it, cfg.alns_iterations, cfg, self.inst.n)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand    = REPAIR[ri](dest, removed)
            score   = 0
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
        self.inst       = inst
        self.cfg        = cfg
        self.ctrl       = PlateauController(cfg)
        self.op_ctrl    = OperatorController(cfg)
        self.lac        = LearnedAcceptanceCriterion(cfg)
        self.mode_bandits: List[ThompsonBandit] = [ThompsonBandit(N_D, N_R) for _ in MODES]
        self.op_counts: Dict[Tuple[int, int], int] = {}
        self._segment_recombine_used = False
        self._init_nv = 1

    def clone_weights(self) -> Dict:
        weights: Dict[str, torch.Tensor] = {}
        for prefix, sd in (("plateau",  self.ctrl.q.state_dict()),
                            ("operator", self.op_ctrl.q.state_dict())):
            for k, v in sd.items():
                weights[f"{prefix}.{k}"] = v.clone().cpu()
        weights.update(self.lac.state_dict())
        return weights

    def load_weights(self, weights: Dict) -> None:
        plateau_sd  = self.ctrl.q.state_dict()
        operator_sd = self.op_ctrl.q.state_dict()
        p_up: Dict[str, torch.Tensor] = {}
        o_up: Dict[str, torch.Tensor] = {}
        legacy = not any(k.startswith(("plateau.", "operator.")) for k in weights)
        if legacy:
            for k, v in weights.items():
                if k in plateau_sd and tuple(v.shape) == tuple(plateau_sd[k].shape):
                    p_up[k] = v.to(DEVICE)
        else:
            for k, v in weights.items():
                if k.startswith("plateau."):
                    bare = k.split(".", 1)[1]
                    if bare in plateau_sd and tuple(v.shape) == tuple(plateau_sd[bare].shape):
                        p_up[bare] = v.to(DEVICE)
                elif k.startswith("operator."):
                    bare = k.split(".", 1)[1]
                    if bare in operator_sd and tuple(v.shape) == tuple(operator_sd[bare].shape):
                        o_up[bare] = v.to(DEVICE)
        plateau_sd.update(p_up);  operator_sd.update(o_up)
        self.ctrl.q.load_state_dict(plateau_sd)
        self.ctrl.q_t.load_state_dict(plateau_sd)
        self.op_ctrl.q.load_state_dict(operator_sd)
        self.op_ctrl.q_t.load_state_dict(operator_sd)
        lac_weights = {k: v for k, v in weights.items() if k.startswith("lac.")}
        if lac_weights:
            self.lac.load_state_dict(lac_weights)

    def _potential(self, plan: Plan) -> float:
        bks = BKS.get(plan.inst.name)
        if not bks:
            return 0.0
        gap_pct = float(np.clip(
            (plan.cost - bks["td"]) / max(bks["td"], 1.0) * 100.0, -25.0, 25.0
        ))
        return float(-self.cfg.potential_nv_scale * max(plan.nv - bks["nv"], 0)
                     - self.cfg.potential_cost_scale * gap_pct)

    def _state(self, cur, best, no_imp, temp, imp_rate, progress, pool) -> np.ndarray:
        rb, lb = _plan_spread(cur, self.inst)
        t0     = self.cfg.temp_control * max(best.cost, 1.0) / math.log(2)
        pool_fill = min(len(pool._routes) / max(self.cfg.route_pool_limit, 1), 1.0)
        return np.array([
            min(no_imp / max(self.cfg.early_stop_patience, 1), 1.0),
            min((cur.cost - best.cost) / max(best.cost, 1), 1.0),
            min(temp / max(t0, 1e-6), 1.5),
            imp_rate,
            min(cur.nv / max(self._init_nv, 1), 2.0),
            rb, lb, self.inst.tw_tight_frac,
            _avg_slack(cur), _fleet_fill(cur), pool_fill, progress,
        ], dtype=np.float32)

    def _op_state(self, cur, best, mode_idx, it, temp, no_imp, pool, recent_imp) -> np.ndarray:
        rb, lb = _plan_spread(cur, self.inst)
        t0     = self.cfg.temp_control * max(best.cost, 1.0) / math.log(2)
        pool_fill = min(len(pool._routes) / max(self.cfg.route_pool_limit, 1), 1.0)
        return np.array([
            min((cur.cost - best.cost) / max(best.cost, 1), 1.0),
            min(cur.nv / max(self._init_nv, 1), 2.0),
            it / max(self.cfg.hybrid_iterations, 1),
            (it % self.cfg.segment_size) / max(self.cfg.segment_size, 1),
            min(temp / max(t0, 1e-6), 1.5),
            min(no_imp / max(self.cfg.early_stop_patience, 1), 1.0),
            rb, lb, self.inst.tw_tight_frac,
            _avg_slack(cur), _fleet_fill(cur), pool_fill,
            mode_idx / max(len(MODES) - 1, 1),
            float(cur.nv - best.nv) / max(self._init_nv, 1),
            recent_imp,
        ], dtype=np.float32)

    def _segment_reward(self, best_before, best_after, cur_before, cur_after,
                        accepted_moves, action) -> float:
        base = -0.20 - 0.04 * MODES[action].ls_passes
        if MODES[action].use_recombine:
            base -= 0.06
        best_nv_gain   = best_before.nv - best_after.nv
        cur_nv_gain    = cur_before.nv  - cur_after.nv
        best_cost_gain = max((best_before.cost - best_after.cost) / max(best_before.cost, 1) * 100, 0.0)
        cur_cost_gain  = max((cur_before.cost  - cur_after.cost)  / max(cur_before.cost,  1) * 100, 0.0)
        if best_nv_gain > 0:
            base += 8.0 * best_nv_gain + 1.2 * best_cost_gain
        elif cur_nv_gain > 0:
            base += 5.0 * cur_nv_gain  + 0.6 * cur_cost_gain
        else:
            base += 0.35 * best_cost_gain + 0.15 * cur_cost_gain
        if accepted_moves <= max(1, self.cfg.segment_size // 10):
            base -= 0.15
        shaped = self.cfg.ctrl_gamma * self._potential(cur_after) - self._potential(cur_before)
        return float(self.cfg.segment_reward_scale * base + shaped)

    def _iteration_reward(self, cur_before, best_before, cur_after, best_after, accepted) -> float:
        if not accepted:
            base = -0.08
        else:
            base = 0.05
            best_nv_gain   = best_before.nv - best_after.nv
            cur_nv_gain    = cur_before.nv  - cur_after.nv
            best_cost_gain = max((best_before.cost - best_after.cost) / max(best_before.cost, 1) * 100, 0.0)
            cur_cost_gain  = max((cur_before.cost  - cur_after.cost)  / max(cur_before.cost,  1) * 100, 0.0)
            if best_nv_gain > 0:
                base += 3.0 * best_nv_gain + 0.4 * best_cost_gain
            elif cur_nv_gain > 0:
                base += 2.0 * cur_nv_gain  + 0.2 * cur_cost_gain
            else:
                base += 0.12 * best_cost_gain + 0.05 * cur_cost_gain
            if cur_after.nv > cur_before.nv:
                base -= 0.5 * (cur_after.nv - cur_before.nv)
        shaped = self.cfg.op_gamma * self._potential(cur_after) - self._potential(cur_before)
        return float(self.cfg.iteration_reward_scale * base + shaped)

    def _route_reduce_trigger(self, cur: Plan, no_imp: int) -> bool:
        return (no_imp >= self.cfg.plateau_start
                and _fleet_fill(cur) < max(0.52, 0.80 - 0.25 * self.inst.tw_tight_frac))

    def _select_action(self, state_before, cur, best, no_imp, progress, pool, frozen) -> Tuple[int, bool]:
        if no_imp >= max(10, self.cfg.ctrl_start // 2):
            return self.ctrl.act(state_before), (not frozen)
        return MODE_DEFAULT, False

    def _refine_candidate(self, cand, action, pool, cur, best, no_imp, iter_idx) -> Plan:
        del cur
        mode    = MODES[action]
        refined = cand
        # ── LS gate: 20-iteration cadence + only on feasible non-NV-inflating cands ──
        _do_ls  = (mode.ls_passes > 0
                   and iter_idx % 20 == 0
                   and refined.feasible
                   and refined.nv <= best.nv)
        if _do_ls:
            nv_cap  = (best.nv
                       if action in (MODE_INTENSIFY, MODE_TW_RESCUE,
                                     MODE_POOL_RECOMBINE, MODE_ROUTE_REDUCE)
                       else None)
            refined = local_search(refined, max_passes=mode.ls_passes, nv_ceiling=nv_cap)
        if (mode.use_recombine and not self._segment_recombine_used
                and no_imp >= max(self.cfg.ctrl_start, self.cfg.plateau_start // 2)
                and len(pool._routes) >= self.cfg.rl_recombine_min_routes):
            self._segment_recombine_used = True
            nv_cap    = min(best.nv, refined.nv)
            recombined= recombine_with_route_pool(refined, pool, self.cfg, nv_ceiling=nv_cap)
            if recombined.dominates(refined):
                refined = local_search(recombined, max_passes=1, nv_ceiling=recombined.nv)
        return refined

    def _fixed_nv_polish(self, start: Plan, pool: RoutePool,
                         inherited_bandit: Optional[ThompsonBandit] = None) -> Plan:
        cfg       = self.cfg
        target_nv = start.nv
        # Inherit operator statistics from main search instead of cold-starting
        polish_bandit = inherited_bandit.clone() if inherited_bandit is not None \
                        else ThompsonBandit(N_D, N_R)
        cur  = local_search(start, max_passes=cfg.polish_ls_passes, nv_ceiling=target_nv)
        best = cur.copy()
        pool.add_plan(best)
        temp   = cfg.temp_control * best.cost / math.log(2)
        no_imp = 0
        for it in range(cfg.polish_iterations):
            di, ri = polish_bandit.select()
            size   = destroy_size(it, cfg.polish_iterations, cfg, self.inst.n, scale=0.70)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand   = REPAIR[ri](dest, removed)
            cand   = local_search(cand, max_passes=1, nv_ceiling=target_nv)
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
        best = local_search(best, max_passes=cfg.polish_ls_passes, nv_ceiling=best.nv)
        pool.add_plan(best)
        return best

    def solve(self, seed: Optional[int] = None, frozen: bool = False,
              init: Optional[Plan] = None) -> Tuple[Plan, List[float]]:
        if seed is not None:
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        cfg = self.cfg
        self.ctrl.reset(); self.op_ctrl.reset()
        if getattr(self, "use_op_rl", True):
            self.lac = LearnedAcceptanceCriterion(cfg)
        self.mode_bandits = [ThompsonBandit(N_D, N_R) for _ in MODES]
        self.op_counts    = {}
        pool = RoutePool(self.inst, cfg)
        cur  = init.copy() if init is not None else build_greedy(self.inst, self.algo_name)
        best = cur.copy()
        pool.add_plan(cur)
        self._init_nv = cur.nv
        temp = cfg.temp_control * cur.cost / math.log(2)
        all_dw = np.ones((len(MODES), N_D), dtype=np.float32)
        all_rw = np.ones((len(MODES), N_R), dtype=np.float32)
        history: List[float] = [best.cost]
        recent_improvements: Deque[int] = deque(maxlen=cfg.segment_size)
        no_imp     = 0
        n_segments = math.ceil(cfg.hybrid_iterations / cfg.segment_size)

        for seg_idx in range(n_segments):
            progress = seg_idx / max(n_segments, 1)
            imp_rate = sum(recent_improvements) / max(len(recent_improvements), 1)
            self._segment_recombine_used = False
            state_before  = self._state(cur, best, no_imp, temp, imp_rate, progress, pool)
            action, ctrl_active = self._select_action(
                state_before, cur, best, no_imp, progress, pool, frozen)
            mode     = MODES[action]
            dw       = all_dw[action].copy()
            rw       = all_rw[action].copy()
            biased_dw= np.maximum(dw * np.array(mode.destroy_bias, np.float32), 0.1)
            biased_rw= np.maximum(rw * np.array(mode.repair_bias,  np.float32), 0.1)
            mode_bandit = self.mode_bandits[action]
            temp    *= mode.temp_boost
            seg_scores = np.zeros((N_D, N_R))
            seg_counts = np.zeros((N_D, N_R))
            seg_best_pre = best.copy()
            seg_cur_pre  = cur.copy()
            accepted_moves = 0

            for offset in range(cfg.segment_size):
                it = seg_idx * cfg.segment_size + offset
                if it >= cfg.hybrid_iterations:
                    break
                op_state = self._op_state(cur, best, action, it, temp, no_imp, pool, imp_rate)
                if getattr(self, "use_op_rl", True):
                    op_action, di, ri = self.op_ctrl.act(
                        op_state, biased_dw, biased_rw, mode_bandit, frozen=frozen)
                else:
                    di, ri    = mode_bandit.select(
                        prior=self.op_ctrl._prior(biased_dw, biased_rw),
                        prior_strength=self.cfg.bandit_prior_strength,
                    )
                    op_action = di * N_R + ri
                size        = destroy_size(it, cfg.hybrid_iterations, cfg, self.inst.n,
                                           scale=mode.destroy_scale)
                cur_before  = cur.copy()
                best_before = best.copy()
                dest, removed = DESTROY[di](cur.copy(), size)
                cand = REPAIR[ri](dest, removed)
                cand = self._refine_candidate(cand, action, pool, cur, best, no_imp, it)

                allow_nv_increase = (action == MODE_DIVERSIFY)
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
                        t0_init   = cfg.temp_control * max(best.cost, 1.0) / math.log(2)
                        lac_feats = self.lac.features(
                            cost_delta=cand.cost - cur.cost, cur_cost=cur.cost,
                            temp=temp, temp_init=t0_init, no_imp=no_imp,
                            patience=cfg.early_stop_patience, nv_diff=cand.nv - cur.nv,
                            progress=it / max(cfg.hybrid_iterations, 1),
                            tw_tight_frac=self.inst.tw_tight_frac,
                            fleet_fill=_fleet_fill(cur), avg_slack_val=_avg_slack(cur),
                        )
                        accepted, _ = self.lac.decide(lac_feats, best.cost)
                    else:
                        accepted = random.random() < math.exp(
                            -(cand.cost - cur.cost) / max(temp, 1e-6))

                if cfg.lac_enabled and getattr(self, "use_op_rl", True) and not frozen:
                    self.lac.observe(best.cost)

                score    = 0
                improved = False
                if accepted:
                    accepted_moves += 1
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

                key = (di, ri)
                self.op_counts[key] = self.op_counts.get(key, 0) + 1
                recent_improvements.append(1 if improved else 0)
                seg_scores[di, ri] += score
                seg_counts[di, ri] += 1
                mode_bandit.update(di, ri, score, cfg.sigma1)
                cur_after  = cur.copy()
                best_after = best.copy()
                next_imp   = sum(recent_improvements) / max(len(recent_improvements), 1)
                next_state = self._op_state(
                    cur_after, best_after, action, it + 1, temp, no_imp, pool, next_imp)
                done = 1.0 if no_imp >= cfg.early_stop_patience else 0.0
                if not frozen and getattr(self, "use_op_rl", True):
                    self.op_ctrl.observe(
                        op_state, op_action,
                        self._iteration_reward(cur_before, best_before,
                                               cur_after, best_after, accepted),
                        next_state, done,
                    )
                    if (it + 1) % 4 == 0:
                        self.op_ctrl.train_step()
                temp *= cfg.temp_decay * mode.temp_decay_scale
                history.append(best.cost)
                if no_imp >= cfg.early_stop_patience:
                    break

            for mb in self.mode_bandits:
                mb.decay(cfg.bandit_decay)
            for d in range(N_D):
                for r in range(N_R):
                    if seg_counts[d, r] > 0:
                        avg    = seg_scores[d, r] / seg_counts[d, r]
                        dw[d]  = dw[d] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
                        rw[r]  = rw[r] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
            all_dw[action] = np.maximum(dw, 0.1)
            all_rw[action] = np.maximum(rw, 0.1)

            state_after = self._state(
                cur, best, no_imp, temp,
                sum(recent_improvements) / max(len(recent_improvements), 1),
                min((seg_idx + 1) / max(n_segments, 1), 1.0),
                pool,
            )
            if ctrl_active:
                self.ctrl.observe(
                    state_before, action,
                    self._segment_reward(seg_best_pre, best, seg_cur_pre, cur,
                                         accepted_moves, action),
                    state_after, 0.0,
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

        # Pass dominant mode bandit to polish (inherits learned operator stats)
        dominant_mode = int(np.argmax([b.alpha.sum() for b in self.mode_bandits]))
        best = self._fixed_nv_polish(best, pool,
                                     inherited_bandit=self.mode_bandits[dominant_mode])
        history.append(best.cost)

        if cfg.recombine_after_polish:
            recombined = recombine_with_route_pool(best, pool, cfg, nv_ceiling=best.nv)
            if recombined.dominates(best):
                best = local_search(recombined, max_passes=cfg.polish_ls_passes,
                                    nv_ceiling=recombined.nv)
                history.append(best.cost)

        # Post-search NV reduction pass (especially effective on RC2)
        bks = BKS.get(self.inst.name)
        if bks is not None and best.nv > bks["nv"]:
            eliminated = _iterative_route_elimination(best, self.inst)
            if eliminated.dominates(best):
                best = eliminated
                history.append(best.cost)

        best.algo = self.algo_name
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

    def _select_action(self, state_before, cur, best, no_imp, progress, pool, frozen):
        del state_before, best, frozen
        if self._route_reduce_trigger(cur, no_imp):
            return MODE_ROUTE_REDUCE, False
        pool_ready  = len(pool._routes) >= max(self.cfg.rl_recombine_min_routes,
                                               max(12, cur.nv * 2))
        fleet_fill  = _fleet_fill(cur)
        slack       = _avg_slack(cur)
        if (pool_ready and no_imp >= max(10, self.cfg.ctrl_start // 2)
                and fleet_fill >= 0.66 and progress < 0.92):
            return MODE_POOL_RECOMBINE, False
        if (self.inst.tw_tight_frac >= 0.18 and slack < 0.16
                and no_imp >= max(8, self.cfg.ctrl_start // 2)):
            return MODE_TW_RESCUE, False
        if no_imp >= max(12, self.cfg.ctrl_start // 2):
            return (MODE_DIVERSIFY if progress < 0.45 else MODE_INTENSIFY), False
        return MODE_DEFAULT, False

    def solve(self, seed=None, frozen=True, init=None):
        plan, history = super().solve(seed=seed, frozen=True, init=init)
        plan.algo = self.algo_name
        return plan, history


PlateauHybridSolver   = HybridDDQNSolver
ScheduledHybridSolver = HybridRuleSolver
RLALNSSolver          = HybridDDQNSolver


def run_ortools(inst: Inst, cfg: Config) -> Tuple[Optional[Plan], float]:
    if not ORTOOLS_OK:
        print("  [OR-Tools] not installed — skipping")
        return None, 0.0
    from ortools.constraint_solver import routing_enums_pb2, pywrapcp
    scale      = 100
    n_nodes    = inst.n + 1
    n_vehicles = inst.n
    manager    = pywrapcp.RoutingIndexManager(n_nodes, n_vehicles, 0)
    routing    = pywrapcp.RoutingModel(manager)
    dist_mat   = (inst.dist * scale).astype(int)
    serv_int   = (inst.service_times * scale).astype(int)

    def transit_cb(fi, ti):
        fn, tn = manager.IndexToNode(fi), manager.IndexToNode(ti)
        return int(dist_mat[fn, tn]) + int(serv_int[fn])
    transit_idx = routing.RegisterTransitCallback(transit_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)
    demands_int = inst.demands.astype(int)

    def demand_cb(fi):
        return int(demands_int[manager.IndexToNode(fi)])
    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx, 0, [int(inst.capacity)] * n_vehicles, True, "Capacity")
    routing.AddDimension(transit_idx, int(inst.horizon * scale),
                         int(inst.horizon * scale), False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for node in range(1, inst.n + 1):
        idx = manager.NodeToIndex(node)
        time_dim.CumulVar(idx).SetRange(int(inst.ready_times[node] * scale),
                                        int(inst.due_times[node] * scale))
    for v in range(n_vehicles):
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.Start(v)))
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.End(v)))
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = int(cfg.ortools_time_limit)
    params.log_search = False
    t0       = time.time()
    solution = routing.SolveWithParameters(params)
    elapsed  = time.time() - t0
    if not solution:
        print(f"  [OR-Tools] no solution ({elapsed:.1f}s)")
        return None, elapsed
    routes: List[List[int]] = []
    for v in range(n_vehicles):
        route: List[int] = []
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

