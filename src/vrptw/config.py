from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# BKS table
# ---------------------------------------------------------------------------
BKS: Dict[str, Dict[str, float]] = {
    "C101": {"nv": 10, "td": 828.94},
    "C102": {"nv": 10, "td": 828.94},
    "C103": {"nv": 10, "td": 828.06},
    "C104": {"nv": 10, "td": 824.78},
    "C105": {"nv": 10, "td": 828.94},
    "C106": {"nv": 10, "td": 828.94},
    "C107": {"nv": 10, "td": 828.94},
    "C108": {"nv": 10, "td": 828.94},
    "C109": {"nv": 10, "td": 828.94},
    # C2
    "C201": {"nv": 3, "td": 591.56},
    "C202": {"nv": 3, "td": 591.56},
    "C203": {"nv": 3, "td": 591.17},
    "C204": {"nv": 3, "td": 590.60},
    "C205": {"nv": 3, "td": 588.88},
    "C206": {"nv": 3, "td": 588.49},
    "C207": {"nv": 3, "td": 588.29},
    "C208": {"nv": 3, "td": 588.32},
    # R1
    "R101": {"nv": 19, "td": 1650.80},
    "R102": {"nv": 17, "td": 1486.12},
    "R103": {"nv": 13, "td": 1292.68},
    "R104": {"nv": 9, "td": 1007.31},
    "R105": {"nv": 14, "td": 1377.11},
    "R106": {"nv": 12, "td": 1252.03},
    "R107": {"nv": 10, "td": 1104.66},
    "R108": {"nv": 9, "td": 960.88},
    "R109": {"nv": 11, "td": 1194.73},
    "R110": {"nv": 10, "td": 1118.84},
    "R111": {"nv": 10, "td": 1096.72},
    "R112": {"nv": 9, "td": 982.14},
    "R201": {"nv": 4, "td": 1252.37},
    "R202": {"nv": 3, "td": 1191.70},
    "R203": {"nv": 3, "td": 939.50},
    "R204": {"nv": 2, "td": 825.52},
    "R205": {"nv": 3, "td": 994.43},
    "R206": {"nv": 3, "td": 906.14},
    "R207": {"nv": 2, "td": 890.61},
    "R208": {"nv": 2, "td": 726.82},
    "R209": {"nv": 3, "td": 909.16},
    "R210": {"nv": 3, "td": 939.37},
    "R211": {"nv": 2, "td": 885.71},
    "RC101": {"nv": 14, "td": 1696.94},
    "RC102": {"nv": 12, "td": 1554.75},
    "RC103": {"nv": 11, "td": 1261.67},
    "RC104": {"nv": 10, "td": 1135.48},
    "RC105": {"nv": 13, "td": 1629.44},
    "RC106": {"nv": 11, "td": 1424.73},
    "RC107": {"nv": 11, "td": 1230.48},
    "RC108": {"nv": 10, "td": 1139.82},
    "RC201": {"nv": 4, "td": 1406.94},
    "RC202": {"nv": 3, "td": 1365.65},
    "RC203": {"nv": 3, "td": 1049.62},
    "RC204": {"nv": 3, "td": 798.46},
    "RC205": {"nv": 4, "td": 1297.65},
    "RC206": {"nv": 3, "td": 1146.32},
    "RC207": {"nv": 3, "td": 1061.14},
    "RC208": {"nv": 3, "td": 828.14},
}

ALGO_ORTOOLS = "OR-Tools"
ALGO_ALNS_BASE = "ALNS-Base"
ALGO_HYBRID_FIXED = "Hybrid-Fixed"
ALGO_HYBRID_RULE = "Hybrid-Rule"
ALGO_HYBRID_DDQN = "Hybrid-DDQN"
ALGO_HYBRID_DDQN_TRANSFER = "Hybrid-DDQN-Transfer"
ALGO_HYBRID_DDQN_TRANSFER_RC2 = "Hybrid-DDQN-Transfer-RC2"
ALGO_HYBRID_DDQN_TRANSFER_DR = "Hybrid-DDQN-Transfer-DR"

ALGO_ORDER = [
    ALGO_ORTOOLS,
    ALGO_ALNS_BASE,
    ALGO_HYBRID_FIXED,
    ALGO_HYBRID_RULE,
    ALGO_HYBRID_DDQN,
    ALGO_HYBRID_DDQN_TRANSFER,
    ALGO_HYBRID_DDQN_TRANSFER_RC2,
    ALGO_HYBRID_DDQN_TRANSFER_DR,
]

LEGACY_ALGO_LABELS = {
    "ALNS": ALGO_ALNS_BASE,
    "ALNS-Base": ALGO_ALNS_BASE,
    "ALNS+": ALGO_HYBRID_FIXED,
    "ALNS-FAIR": ALGO_HYBRID_FIXED,
    "Hybrid-Fixed": ALGO_HYBRID_FIXED,
    "ALNS++": ALGO_HYBRID_RULE,
    "SCHED-ALNS": ALGO_HYBRID_RULE,
    "Hybrid-Rule": ALGO_HYBRID_RULE,
    "DDQN-ALNS": ALGO_HYBRID_DDQN,
    "PLATEAU-HYBRID": ALGO_HYBRID_DDQN,
    "Hybrid-DDQN": ALGO_HYBRID_DDQN,
    "DDQN-ALNS*": ALGO_HYBRID_DDQN_TRANSFER,
    "DDQN-ALNS★": ALGO_HYBRID_DDQN_TRANSFER,
    "Hybrid-DDQN-Transfer": ALGO_HYBRID_DDQN_TRANSFER,
    "Hybrid-DDQN-Transfer-RC2": ALGO_HYBRID_DDQN_TRANSFER_RC2,
    "Hybrid-DDQN-Transfer-DR": ALGO_HYBRID_DDQN_TRANSFER_DR,
}


def canonical_algo_label(label: str) -> str:
    if label in LEGACY_ALGO_LABELS:
        return LEGACY_ALGO_LABELS[label]
    normalized = label.lower().replace("_", "-")
    for k, v in LEGACY_ALGO_LABELS.items():
        if k.lower().replace("_", "-") == normalized:
            return v
    for val in ALGO_ORDER:
        if val.lower().replace("_", "-") == normalized:
            return val
    return label


def normalize_algorithm_frame(df: pd.DataFrame) -> pd.DataFrame:
    if "Algorithm" not in df.columns:
        return df
    out = df.copy()
    out["Algorithm"] = out["Algorithm"].map(canonical_algo_label)
    extra = [a for a in out["Algorithm"].dropna().unique() if a not in ALGO_ORDER]
    out["Algorithm"] = pd.Categorical(out["Algorithm"], categories=ALGO_ORDER + extra, ordered=True)
    sort_cols = [c for c in ("Dataset", "Instance", "Algorithm") if c in out.columns]
    if sort_cols:
        out = out.sort_values(sort_cols).reset_index(drop=True)
    return out


def default_data_path() -> str:
    candidates = [
        "./data/Solomon",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "Solomon"),
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "data", "Solomon"
        ),
        "/workspace/data/Solomon",
        "/root/data/Solomon",
        "/kaggle/input/vrptw-benchmark-datasets/data/Solomon",
        "/kaggle/input/datasets/senju14/vrptw-benchmark-datasets/data/Solomon",
        "/content/vrptw-benchmark/data/Solomon",
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return candidates[0]


def default_output_dir() -> str:
    for d in ("/workspace", "/root", "/kaggle/working", "/content"):
        if os.path.exists(d):
            return d
    return os.getcwd()


# ---------------------------------------------------------------------------
# Config — tuned for i7-14700KF (28 cores), n_runs=3
# ---------------------------------------------------------------------------
@dataclass
class Config:
    data_path: str = field(default_factory=default_data_path)
    output_dir: str = field(default_factory=default_output_dir)

    # ── iterations (reduced from 3500; early-stop exits stagnation faster) ─
    alns_iterations: int = 1200
    hybrid_iterations: int = 1200
    early_stop_patience: int = 250
    polish_iterations: int = 80
    polish_patience: int = 40

    destroy_ratio_min: float = 0.10
    destroy_ratio_max: float = 0.40
    temp_control: float = 0.05
    temp_decay: float = 0.99975
    sigma1: int = 33
    sigma2: int = 9
    sigma3: int = 3
    weight_decay: float = 0.10
    segment_size: int = 100
    max_wall_hours: float = 9.5
    n_runs: int = 5
    seed: int = 42

    # ── plateau controller ─────────────────────────────────────────────────
    ctrl_state_dim: int = 12
    ctrl_hidden: int = 128
    ctrl_lr: float = 3e-4
    ctrl_gamma: float = 0.95
    ctrl_buffer: int = 20_000
    ctrl_batch: int = 64
    ctrl_target_freq: int = 100
    ctrl_eps_start: float = 0.40
    ctrl_eps_end: float = 0.02
    ctrl_eps_decay: float = 0.9997
    ctrl_start: int = 24
    plateau_start: int = 72
    ctrl_start_floor: int = 10  # minimum non-improvement threshold floor to trigger plateau controller
    nv_increase_penalty: float = 15.0
    rl_recombine_min_routes: int = 24
    ctrl_tau: float = 0.005  # soft target update rate for PlateauController
    per_beta_steps: int = 50_000  # steps over which beta anneals 0.4 → 1.0
    # ── operator controller ────────────────────────────────────────────────
    op_state_dim: int = 15
    op_hidden: int = 128
    op_lr: float = 3e-4
    op_gamma: float = 0.97
    op_buffer: int = 30_000
    op_batch: int = 64
    op_target_freq: int = 120
    op_eps_start: float = 0.35
    op_eps_end: float = 0.02
    op_eps_decay: float = 0.9996
    op_warmup: int = 256
    op_prior_strength: float = 0.55
    op_bandit_strength: float = 0.20
    op_tau: float = 0.005  # soft target update rate for OperatorController

    bandit_decay: float = 0.95
    bandit_prior_strength: float = 0.18
    potential_nv_scale: float = 15.0
    potential_cost_scale: float = 0.18
    segment_reward_scale: float = 0.30
    iteration_reward_scale: float = 0.45

    # ── route pool / set-partitioning ─────────────────────────────────────
    route_pool_limit: int = 480
    route_pool_max_per_customer: int = 18
    sp_time_limit: float = 4.0
    sp_vehicle_penalty_scale: float = 100.0

    # ── polish ────────────────────────────────────────────────────────────
    polish_ls_passes: int = 2
    recombine_after_main_search: bool = True
    recombine_after_polish: bool = True

    # ── transfer ──────────────────────────────────────────────────────────
    transfer_epochs: int = 1
    transfer_shuffle: bool = True
    rc2_transfer_split: int = 4

    # ── elite archive ─────────────────────────────────────────────────────
    elite_archive_k: int = 5

    # ── OR-Tools ──────────────────────────────────────────────────────────
    ortools_time_limit: float = 60.0

    # ── Learned Acceptance Criterion ──────────────────────────────────────
    lac_enabled: bool = True
    lac_state_dim: int = 9
    lac_hidden: int = 48
    lac_lr: float = 1e-3
    lac_warmup: int = 300
    lac_horizon: int = 80
    lac_train_freq: int = 20
    lac_buf_size: int = 5000
    lac_batch: int = 64  # batch size for training the learned acceptance criterion
    # ── domain randomization ──────────────────────────────────────────────
    domain_randomization_epochs: int = 20
    domain_randomization_batch: int = 15

    def validate(self) -> None:
        """Validate configuration settings to prevent runtime failures during long-running tasks."""
        if self.alns_iterations < 0:
            raise ValueError(f"alns_iterations must be >= 0, got {self.alns_iterations}")
        if self.hybrid_iterations < 0:
            raise ValueError(f"hybrid_iterations must be >= 0, got {self.hybrid_iterations}")
        if self.early_stop_patience <= 0:
            raise ValueError(f"early_stop_patience must be > 0, got {self.early_stop_patience}")
        if not (0.0 <= self.destroy_ratio_min < self.destroy_ratio_max <= 1.0):
            raise ValueError(
                f"Invalid destroy ratios: min={self.destroy_ratio_min}, max={self.destroy_ratio_max}. "
                "Must satisfy 0.0 <= min < max <= 1.0"
            )
        if self.max_wall_hours <= 0.0:
            raise ValueError(f"max_wall_hours must be > 0, got {self.max_wall_hours}")
        if self.n_runs < 1:
            raise ValueError(f"n_runs must be >= 1, got {self.n_runs}")
        if self.ctrl_tau <= 0.0 or self.ctrl_tau >= 1.0:
            raise ValueError(f"ctrl_tau must be > 0 and < 1, got {self.ctrl_tau}")
        if self.op_tau <= 0.0 or self.op_tau >= 1.0:
            raise ValueError(f"op_tau must be > 0 and < 1, got {self.op_tau}")
        if self.per_beta_steps <= 0:
            raise ValueError(f"per_beta_steps must be > 0, got {self.per_beta_steps}")
        if self.lac_batch < 16:
            raise ValueError(f"lac_batch must be >= 16, got {self.lac_batch}")
        if self.ctrl_start_floor < 1:
            raise ValueError(f"ctrl_start_floor must be >= 1, got {self.ctrl_start_floor}")


# ---------------------------------------------------------------------------
# Mode specifications
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModeSpec:
    name: str
    destroy_scale: float
    temp_boost: float
    temp_decay_scale: float
    destroy_bias: Tuple[float, ...]  # length == N_D = 8
    repair_bias: Tuple[float, ...]  # length == N_R = 5
    ls_passes: int
    use_recombine: bool


MODES: Tuple[ModeSpec, ...] = (
    ModeSpec(
        "default", 1.00, 1.00, 1.000, (1.0, 1.0, 1.0, 1.0, 1.0, 0.8, 0.8, 1.0), (1.0, 1.0, 1.0, 1.0, 1.1), 0, False
    ),
    ModeSpec(
        "intensify", 0.70, 0.98, 0.995, (0.5, 1.3, 1.2, 0.5, 1.0, 0.7, 0.8, 0.9), (1.3, 1.2, 0.8, 1.0, 1.3), 1, False
    ),
    ModeSpec(
        "diversify", 1.35, 1.08, 1.002, (1.5, 0.9, 1.3, 1.4, 1.0, 0.7, 1.4, 1.6), (0.9, 1.0, 1.3, 1.0, 0.9), 0, False
    ),
    ModeSpec(
        "tw_rescue", 1.10, 1.05, 1.000, (0.6, 0.9, 1.1, 0.8, 1.8, 0.4, 0.8, 1.0), (0.8, 1.0, 1.2, 1.8, 2.2), 1, False
    ),
    ModeSpec(
        "pool_recombine",
        0.90,
        1.01,
        0.997,
        (0.7, 1.2, 0.9, 1.1, 0.8, 1.8, 1.6, 1.1),
        (0.7, 1.1, 1.5, 0.9, 1.1),
        1,
        True,
    ),
    ModeSpec(
        "route_reduce", 0.95, 1.02, 0.998, (0.6, 1.0, 0.9, 1.7, 0.6, 2.2, 2.4, 1.2), (0.8, 1.2, 1.5, 1.0, 1.4), 1, True
    ),
)

MODE_DEFAULT, MODE_INTENSIFY, MODE_DIVERSIFY = 0, 1, 2
MODE_TW_RESCUE, MODE_POOL_RECOMBINE, MODE_ROUTE_REDUCE = 3, 4, 5
