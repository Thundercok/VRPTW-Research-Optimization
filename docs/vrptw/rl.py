from __future__ import annotations
import random
import math
import numpy as np
from collections import deque
from typing import List, Dict, Tuple, Optional, Deque
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from .core import Plan
from .config import Config, MODES
from .operators import N_D, N_R, N_ACTIONS

DEVICE = torch.device("cpu")

class PrioritizedReplayBuffer:
    """
    Proportional PER (Schaul et al., 2016).
    alpha=0.6: prioritization strength.
    beta anneals 0.4→1.0 over training to correct IS bias.
    """
    def __init__(self, capacity: int, alpha: float = 0.6,
                 beta_start: float = 0.4, beta_end: float = 1.0):
        self.capacity:      int            = capacity
        self.alpha:         np.ndarray     = np.ones((N_D, N_R), dtype=np.float64) * alpha
        self.beta:          float          = beta_start
        self.beta_end:      float          = beta_end   
        self.beta_inc:      float          = (beta_end - beta_start) / 200_000
        self.buf:           List           = []
        self.pos:           int = 0
        self.priorities: np.ndarray = np.zeros(capacity, dtype=np.float32)
        self.max_pri   = 1.0

    def push(self, *transition) -> None:
        if len(self.buf) < self.capacity:
            self.buf.append(transition)
        else:
            self.buf[self.pos] = transition
        self.priorities[self.pos] = self.max_pri
        self.pos = (self.pos + 1) % self.capacity

    def sample(self, batch_size: int):
        n     = len(self.buf)
        probs = self.priorities[:n] ** self.alpha
        probs /= probs.sum()
        idxs  = np.random.choice(n, batch_size, p=probs, replace=False)
        ws    = (n * probs[idxs]) ** -self.beta
        ws   /= ws.max()
        self.beta = float(min(self.beta_end, self.beta + self.beta_inc))        
        s, a, r, ns, d = zip(*[self.buf[i] for i in idxs])
        return (
            np.array(s,  np.float32), np.array(a,  np.int64),
            np.array(r,  np.float32), np.array(ns, np.float32),
            np.array(d,  np.float32),
        ), idxs, torch.tensor(ws, dtype=torch.float32).to(DEVICE)

    def update_priorities(self, idxs, td_errors: np.ndarray) -> None:
        for i, err in zip(idxs, td_errors):
            p = float(abs(err)) + 1e-6
            self.priorities[i] = p
            self.max_pri = max(self.max_pri, p)

    def __len__(self) -> int:
        return len(self.buf)


# ---------------------------------------------------------------------------
# QNet
# ---------------------------------------------------------------------------
class QNet(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int):
        super().__init__()
        hid2      = max(hidden_dim // 2, 32)
        self.trunk= nn.Sequential(
            nn.Linear(state_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.ReLU(),
        )
        self.value_head = nn.Sequential(nn.Linear(hidden_dim, hid2), nn.ReLU(), nn.Linear(hid2, 1))
        self.adv_head   = nn.Sequential(nn.Linear(hidden_dim, hid2), nn.ReLU(), nn.Linear(hid2, action_dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.trunk(x)
        v = self.value_head(h)
        a = self.adv_head(h)
        return v + a - a.mean(dim=1, keepdim=True)


# ---------------------------------------------------------------------------
# Thompson bandit
# ---------------------------------------------------------------------------
class ThompsonBandit:
    def __init__(self, n_d: int, n_r: int):
        self.alpha = np.ones((n_d, n_r), dtype=np.float64)
        self.beta  = np.ones((n_d, n_r), dtype=np.float64)

    def mean(self) -> np.ndarray:
        return self.alpha / (self.alpha + self.beta)

    def select(self, prior: Optional[np.ndarray] = None,
               prior_strength: float = 0.0) -> Tuple[int, int]:
        samples = np.random.beta(self.alpha, self.beta)
        if prior is not None:
            p       = np.asarray(prior, dtype=np.float64)
            p      /= max(p.sum(), 1e-9)
            samples = samples + prior_strength * p
        idx = np.unravel_index(int(samples.argmax()), samples.shape)
        return int(idx[0]), int(idx[1])

    def update(self, di: int, ri: int, score: float, sigma1: int) -> None:
        success           = float(np.clip(score / max(sigma1, 1), 0.0, 1.0))
        self.alpha[di, ri]+= success
        self.beta[di, ri] += 1.0 - success

    def decay(self, rate: float = 0.95) -> None:
        np.multiply(self.alpha - 1.0, rate, out=self.alpha)
        np.add(self.alpha, 1.0, out=self.alpha)
        np.multiply(self.beta - 1.0, rate, out=self.beta)
        np.add(self.beta, 1.0, out=self.beta)

    def clone(self) -> "ThompsonBandit":
        b       = ThompsonBandit(self.alpha.shape[0], self.alpha.shape[1])
        b.alpha = self.alpha.copy()
        b.beta  = self.beta.copy()
        return b


# ---------------------------------------------------------------------------
# Elite archive
# ---------------------------------------------------------------------------
class EliteArchive:
    def __init__(self, k: int = 5):
        self.k = k
        self._plans: Dict[str, List[Plan]] = {}

    def update(self, plan: Plan) -> None:
        if not plan.feasible:
            return
        key    = plan.inst.name
        bucket = self._plans.setdefault(key, [])
        bucket.append(plan.copy())
        bucket.sort(key=lambda p: (p.nv, p.cost))
        self._plans[key] = bucket[:self.k]

    def best(self, inst_name: str) -> Optional[Plan]:
        bucket = self._plans.get(inst_name, [])
        return bucket[0].copy() if bucket else None

    def summary(self) -> str:
        lines = []
        for name, bucket in sorted(self._plans.items()):
            p       = bucket[0]
            td_gap, _ = p.gap()
            gap_str = f"{td_gap:+.2f}%" if td_gap is not None else "--"
            lines.append(f"  {name}: nv={p.nv} cost={p.cost:.1f} gap={gap_str}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# DDQN controllers  (now using PrioritizedReplayBuffer)
# ---------------------------------------------------------------------------
class PlateauController:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.q   = QNet(cfg.ctrl_state_dim, len(MODES), cfg.ctrl_hidden).to(DEVICE)
        self.q_t = QNet(cfg.ctrl_state_dim, len(MODES), cfg.ctrl_hidden).to(DEVICE)
        self.q_t.load_state_dict(self.q.state_dict())
        self.opt = optim.Adam(self.q.parameters(), lr=cfg.ctrl_lr)
        self.buf = PrioritizedReplayBuffer(cfg.ctrl_buffer)
        self.eps = cfg.ctrl_eps_start
        self.step= 0

    def reset(self) -> None:
        self.eps = self.cfg.ctrl_eps_start

    def act(self, state: np.ndarray) -> int:
        if random.random() < self.eps:
            return random.randrange(len(MODES))
        with torch.no_grad():
            return int(self.q(torch.tensor(state).unsqueeze(0).to(DEVICE))[0].argmax().item())

    def observe(self, s, a, r, ns, done=0.0):
        self.buf.push(s, a, r, ns, done)

    def train_step(self) -> None:
        self.step += 1
        if len(self.buf) < self.cfg.ctrl_batch:
            return
        (s, a, r, ns, d), idxs, is_w = self.buf.sample(self.cfg.ctrl_batch)
        s  = torch.tensor(s).to(DEVICE)
        a  = torch.tensor(a, dtype=torch.long).to(DEVICE)
        r  = torch.tensor(r).to(DEVICE)
        ns = torch.tensor(ns).to(DEVICE)
        d  = torch.tensor(d).to(DEVICE)
        qp = self.q(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            best_a = self.q(ns).argmax(1).unsqueeze(1)
            qn     = self.q_t(ns).gather(1, best_a).squeeze(1)
            target = r + self.cfg.ctrl_gamma * qn * (1 - d)
        td_errors = (qp - target).detach().cpu().numpy()
        self.buf.update_priorities(idxs, td_errors)
        loss = (is_w * F.smooth_l1_loss(qp, target, reduction="none")).mean()
        self.opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), 1.0)
        self.opt.step()
        if self.step % self.cfg.ctrl_target_freq == 0:
            self.q_t.load_state_dict(self.q.state_dict())
        self.eps = max(self.cfg.ctrl_eps_end, self.eps * self.cfg.ctrl_eps_decay)


class OperatorController:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.q   = QNet(cfg.op_state_dim, N_ACTIONS, cfg.op_hidden).to(DEVICE)
        self.q_t = QNet(cfg.op_state_dim, N_ACTIONS, cfg.op_hidden).to(DEVICE)
        self.q_t.load_state_dict(self.q.state_dict())
        self.opt = optim.Adam(self.q.parameters(), lr=cfg.op_lr)
        self.buf = PrioritizedReplayBuffer(cfg.op_buffer)
        self.eps = cfg.op_eps_start
        self.step= 0

    def reset(self) -> None:
        self.eps = self.cfg.op_eps_start

    def _prior(self, dw: np.ndarray, rw: np.ndarray) -> np.ndarray:
        dw = np.asarray(dw, np.float32); dw /= max(dw.sum(), 1e-9)
        rw = np.asarray(rw, np.float32); rw /= max(rw.sum(), 1e-9)
        return np.outer(dw, rw)

    def _sample_prior(self, prior: np.ndarray, bandit: ThompsonBandit) -> int:
        probs  = prior.reshape(-1) * bandit.mean().reshape(-1)
        probs /= max(probs.sum(), 1e-9)
        return int(np.random.choice(N_ACTIONS, p=probs))

    def act(self, state, dw, rw, bandit, frozen=False) -> Tuple[int, int, int]:
        prior = self._prior(dw, rw)
        if not frozen and len(self.buf) < self.cfg.op_warmup:
            di, ri = bandit.select(prior=prior, prior_strength=self.cfg.bandit_prior_strength)
            action = di * N_R + ri
        elif not frozen and random.random() < self.eps:
            action = self._sample_prior(prior, bandit)
            di, ri = divmod(action, N_R)
        else:
            with torch.no_grad():
                q = self.q(torch.tensor(state).unsqueeze(0).to(DEVICE))[0].cpu().numpy()
            q      = (q + self.cfg.op_prior_strength * np.log(prior.reshape(-1) + 1e-8)
                        + self.cfg.op_bandit_strength * bandit.mean().reshape(-1))
            action = int(q.argmax())
            di, ri = divmod(action, N_R)
        return int(action), int(di), int(ri)

    def observe(self, s, a, r, ns, done=0.0):
        self.buf.push(s, a, r, ns, done)

    def train_step(self) -> None:
        self.step += 1
        if len(self.buf) < self.cfg.op_batch:
            return
        (s, a, r, ns, d), idxs, is_w = self.buf.sample(self.cfg.op_batch)
        s  = torch.tensor(s).to(DEVICE)
        a  = torch.tensor(a, dtype=torch.long).to(DEVICE)
        r  = torch.tensor(r).to(DEVICE)
        ns = torch.tensor(ns).to(DEVICE)
        d  = torch.tensor(d).to(DEVICE)
        qp = self.q(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            best_a = self.q(ns).argmax(1).unsqueeze(1)
            qn     = self.q_t(ns).gather(1, best_a).squeeze(1)
            target = r + self.cfg.op_gamma * qn * (1 - d)
        td_errors = (qp - target).detach().cpu().numpy()
        self.buf.update_priorities(idxs, td_errors)
        loss = (is_w * F.smooth_l1_loss(qp, target, reduction="none")).mean()
        self.opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), 1.0)
        self.opt.step()
        if self.step % self.cfg.op_target_freq == 0:
            self.q_t.load_state_dict(self.q.state_dict())
        self.eps = max(self.cfg.op_eps_end, self.eps * self.cfg.op_eps_decay)


# ---------------------------------------------------------------------------
# Learned Acceptance Criterion
# ---------------------------------------------------------------------------
class LearnedAcceptanceCriterion:
    def __init__(self, cfg: Config):
        self.cfg  = cfg
        self.net  = nn.Sequential(
            nn.Linear(cfg.lac_state_dim, cfg.lac_hidden), nn.ReLU(),
            nn.Linear(cfg.lac_hidden, cfg.lac_hidden // 2), nn.ReLU(),
            nn.Linear(cfg.lac_hidden // 2, 1), nn.Sigmoid(),
        ).to(DEVICE)
        self.opt  = optim.Adam(self.net.parameters(), lr=cfg.lac_lr)
        self.step = 0
        self._pending:   deque = deque()
        self._train_buf: deque = deque(maxlen=cfg.lac_buf_size)

    def features(self, cost_delta, cur_cost, temp, temp_init, no_imp, patience,
                 nv_diff, progress, tw_tight_frac, fleet_fill, avg_slack_val) -> np.ndarray:
        metro = math.exp(-max(cost_delta, 0.0) / max(temp, 1e-6))
        return np.array([
            cost_delta / max(abs(cur_cost), 1.0),
            temp / max(temp_init, 1e-6),
            no_imp / max(patience, 1),
            float(np.clip(nv_diff, -2, 2)),
            progress, tw_tight_frac, fleet_fill, avg_slack_val, metro,
        ], dtype=np.float32)

    def decide(self, feats: np.ndarray, cur_best_cost: float) -> Tuple[bool, float]:
        self.step += 1
        self._pending.append((feats.copy(), cur_best_cost, self.step))
        metro_p = float(feats[-1])
        if self.step < self.cfg.lac_warmup:
            return random.random() < metro_p, metro_p
        with torch.no_grad():
            p = float(self.net(torch.tensor(feats).unsqueeze(0).to(DEVICE))[0, 0])
        return random.random() < p, p

    def observe(self, current_best_cost: float) -> None:
        cutoff = self.step - self.cfg.lac_horizon
        while self._pending and self._pending[0][2] <= cutoff:
            feats, best_at_t, _ = self._pending.popleft()
            label = 1.0 if current_best_cost < best_at_t - 1e-6 else 0.0
            self._train_buf.append((feats, label))
        if self.step % self.cfg.lac_train_freq == 0 and len(self._train_buf) >= 64:
            self._train()

    def _train(self) -> None:
        batch = random.sample(self._train_buf, min(64, len(self._train_buf)))
        feats, labels = zip(*batch)
        x = torch.tensor(np.array(feats), dtype=torch.float32).to(DEVICE)
        y = torch.tensor(labels, dtype=torch.float32).to(DEVICE)
        pos_weight = torch.tensor(
            [max((y == 0).sum().item(), 1) / max((y == 1).sum().item(), 1)],
            dtype=torch.float32,
        ).to(DEVICE)
        pred = self.net(x).squeeze(1)
        loss = F.binary_cross_entropy(pred, y, weight=pos_weight.expand_as(y))
        self.opt.zero_grad(); loss.backward(); self.opt.step()

    def state_dict(self) -> Dict:
        return {f"lac.{k}": v.clone().cpu() for k, v in self.net.state_dict().items()}

    def load_state_dict(self, weights: Dict) -> None:
        sd      = self.net.state_dict()
        updates = {}
        for k, v in weights.items():
            bare = k[4:] if k.startswith("lac.") else k
            if bare in sd and tuple(v.shape) == tuple(sd[bare].shape):
                updates[bare] = v.to(DEVICE)
        sd.update(updates)
        self.net.load_state_dict(sd)

