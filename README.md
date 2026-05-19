# VRPTW Research Optimization

> A research platform comparing **ALNS**, **Hybrid-Fixed**, **Hybrid-Rule**, and **DDQN-ALNS** solvers on the Solomon VRPTW benchmark — with a web-based dispatch portal for live demos.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org)
[![Numba](https://img.shields.io/badge/Numba-00A3E0?style=for-the-badge&logo=numba&logoColor=white)](https://numba.pydata.org)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Project Structure](#2-project-structure)
3. [Installation](#3-installation)
4. [Quick Smoke Test](#4-quick-smoke-test)
5. [Running the Full Benchmark](#5-running-the-full-benchmark)
6. [Transfer Learning & Domain Randomization](#6-transfer-learning--domain-randomization)
7. [Web App (Dispatch Portal)](#7-web-app-dispatch-portal)
8. [Configuration Reference](#8-configuration-reference)
9. [Algorithm Overview](#9-algorithm-overview)
10. [Outputs & Artifacts](#10-outputs--artifacts)
11. [GPU Acceleration](#11-gpu-acceleration)
12. [Contributing](#12-contributing)

---

## 1. Project Overview

This project benchmarks a family of **Adaptive Large Neighbourhood Search (ALNS)** solvers — progressively augmented with Deep Reinforcement Learning (DDQN) controllers — against the classic Solomon RC1/RC2 benchmark instances.

| Algorithm | Description |
|-----------|-------------|
| `ALNS-Base` | Pure ALNS with Thompson-bandit operator selection |
| `Hybrid-Fixed` | ALNS + rule-triggered route-reduction mode |
| `Hybrid-Rule` | ALNS + full heuristic mode-switching policy |
| `Hybrid-DDQN` | ALNS + online-trained DDQN plateau & operator controllers |
| `Hybrid-DDQN-Transfer` | Hybrid-DDQN with weights pre-trained on RC1, tested on RC2 |
| `Hybrid-DDQN-Transfer-RC2` | Within-RC2 transfer (train on first 4, test on last 4) |
| `Hybrid-DDQN-Transfer-DR` | Domain-randomization pre-training, then frozen inference |
| `OR-Tools` | Google OR-Tools CP-SAT baseline |

---

## 2. Project Structure

```
VRPTW-Research-Optimization/
├── docs/                         # Research solver (standalone Python package)
│   ├── vrptw/                    # ← the vrptw package (run everything from here)
│   │   ├── __init__.py           # Public API exports
│   │   ├── __main__.py           # Entry point: python3 -m vrptw
│   │   ├── config.py             # Config dataclass, BKS table, algo labels
│   │   ├── core.py               # Inst, Plan, Numba-JIT cost/feasibility
│   │   ├── generators.py         # SyntheticVRPTWGenerator, load_datasets
│   │   ├── heuristics.py         # Greedy construction, insertion utilities
│   │   ├── operators.py          # 8 destroy + 5 repair operators, DESTROY/REPAIR lists
│   │   ├── local_search.py       # 2-opt, relocate, swap, cross-exchange, route-compact
│   │   ├── pool.py               # RoutePool, MILP/greedy set-partitioning recombination
│   │   ├── rl.py                 # QNet, ThompsonBandit, DDQN controllers, LAC, EliteArchive
│   │   ├── solvers.py            # ALNSSolver, HybridFixedSolver, HybridRuleSolver, HybridDDQNSolver
│   │   └── benchmark.py          # run_instance, run_benchmark, smoke_test, train_transfer_model
│   ├── data/
│   │   └── Solomon/              # 56 Solomon .txt files (rc101–rc208, r1xx, c1xx, etc.) ✓ already present
│   ├── logs/                     # Benchmark CSVs, run logs
│   ├── model/                    # Saved safetensors weights
│   └── scripts/                  # Utility scripts (fetch, GPU install, etc.)
├── src/
│   ├── backend/                  # FastAPI app, auth, job orchestration
│   └── frontend/                 # Web UI (HTML/CSS/JS)
├── main.py                       # Web app entry point
├── requirements.txt
└── pyproject.toml
```

---

## 3. Installation

### Prerequisites

- **Python 3.12** (3.11 works; 3.13+ not yet supported by Numba/PyTorch)
- Recommended: [`uv`](https://docs.astral.sh/uv/) for fast installs

### Option A — uv (recommended, ~30 s)

```bash
git clone https://github.com/Thundercok/VRPTW-Research-Optimization.git
cd VRPTW-Research-Optimization

uv venv .venv --python 3.12
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell

uv pip install -r requirements.txt
```

### Option B — plain pip

```bash
git clone https://github.com/Thundercok/VRPTW-Research-Optimization.git
cd VRPTW-Research-Optimization

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

> **Note:** The Solomon data files (`rc101.txt` … `rc208.txt`) are **already committed** under `docs/data/Solomon/` — no download needed for the benchmark.

---

## 4. Quick Smoke Test

Runs all 4 main solvers on a small synthetic 25-customer instance. Completes in **< 10 seconds**. Use this to verify the environment is set up correctly.

```bash
cd docs
python3 -m vrptw
```

Expected output:

```
Launching VRPTW Application...
ALNS-Base                nv=  4 cost=   580.0 BKS TD N/A NV N/A (0.4s)
Hybrid-Fixed             nv=  3 cost=   648.0 BKS TD N/A NV N/A (1.5s)
Hybrid-Rule              nv=  3 cost=   648.0 BKS TD N/A NV N/A (0.7s)
Hybrid-DDQN              nv=  3 cost=   641.5 BKS TD N/A NV N/A (1.3s)
```

`BKS TD N/A` is expected — synthetic instances have no Best-Known Solution entry.

---

## 5. Running the Full Benchmark

The full benchmark runs all algorithms across **RC1 + RC2** Solomon instances (8 each) with multiple seeds. On a modern laptop it takes **~2–4 hours** for a 3-run pass of all 7 algorithms.

### Step 1 — Write a benchmark script

Create a file, e.g. `docs/run_benchmark.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))   # ensure vrptw package is on path

from vrptw import (
    Config, load_datasets,
    run_benchmark, print_summary_table,
    ALGO_ALNS_BASE, ALGO_HYBRID_FIXED, ALGO_HYBRID_RULE,
    ALGO_HYBRID_DDQN,
)

# ── Config ────────────────────────────────────────────────────────────────────
cfg = Config(
    data_path  = "./data/Solomon",   # path to the Solomon .txt files
    output_dir = "./logs",           # where results CSV and checkpoint are saved
    n_runs     = 3,                  # runs per (instance, algorithm) pair
    alns_iterations   = 1200,        # main search iterations
    hybrid_iterations = 1200,
    max_wall_hours    = 9.5,         # hard stop after this many hours
)

# ── Load instances ─────────────────────────────────────────────────────────────
datasets  = load_datasets(cfg.data_path)
rc1_insts = datasets["rc1"]   # RC101 – RC108
rc2_insts = datasets["rc2"]   # RC201 – RC208
all_insts  = rc1_insts + rc2_insts

# ── Choose algorithms ──────────────────────────────────────────────────────────
algorithms = [
    ALGO_ALNS_BASE,
    ALGO_HYBRID_FIXED,
    ALGO_HYBRID_RULE,
    ALGO_HYBRID_DDQN,
]

# ── Run ────────────────────────────────────────────────────────────────────────
df = run_benchmark(
    instances    = all_insts,
    algorithms   = algorithms,
    cfg          = cfg,
    result_path  = "./logs/benchmark_clean.csv",
    checkpoint_path = "./logs/benchmark_checkpoint.csv",   # auto-resumes on restart
)

print_summary_table(df)
```

### Step 2 — Run it

```bash
cd docs
python3 run_benchmark.py
```

### Checkpointing & resuming

The benchmark saves a checkpoint CSV every 4 instances. If it crashes or you stop it, **just re-run the same script** — completed `(instance, algorithm)` pairs are skipped automatically.

```bash
# Resume from where you left off (no extra flags needed)
python3 run_benchmark.py
```

### Running a subset (fast test)

```python
# Just RC101 and RC201, 1 run, short iterations
cfg = Config(
    data_path         = "./data/Solomon",
    output_dir        = "./logs",
    n_runs            = 1,
    alns_iterations   = 300,
    hybrid_iterations = 300,
    early_stop_patience = 80,
)
all_insts = datasets["rc1"][:1] + datasets["rc2"][:1]
```

### Running only one algorithm

```python
from vrptw import ALGO_HYBRID_DDQN
algorithms = [ALGO_HYBRID_DDQN]
```

### Running a single instance manually

```python
from vrptw import Config, load_datasets, run_instance, ALGO_HYBRID_DDQN

cfg      = Config(data_path="./data/Solomon")
datasets = load_datasets(cfg.data_path)
inst     = datasets["rc1"][0]   # RC101

result, plan = run_instance(inst, ALGO_HYBRID_DDQN, cfg, seed=42)
print(f"NV={result['nv']}  cost={result['cost']:.1f}  gap={result['td_gap']:+.2f}%")
```

### Benchmark output files

| File | Description |
|------|-------------|
| `logs/benchmark_clean.csv` | Final aggregated results (one row per instance/algo) |
| `logs/benchmark_checkpoint.csv` | Live checkpoint — updated every 4 instances |

---

## 6. Transfer Learning & Domain Randomization

Pre-train a DDQN policy, then apply it **frozen** to unseen instances for better out-of-the-box performance.

### Train on RC1, test on RC2 (Transfer)

```python
from vrptw import (
    Config, load_datasets,
    train_transfer_model, load_transfer_model,
    run_benchmark,
    ALGO_HYBRID_DDQN_TRANSFER,
)

cfg      = Config(data_path="./data/Solomon", output_dir="./logs", transfer_epochs=1)
datasets = load_datasets(cfg.data_path)

# Step 1: train on RC1 (saves logs/rl_alns_transfer_rc1_v15.safetensors)
weights = train_transfer_model(datasets["rc1"], cfg, seed=42, label="RC1")

# Step 2: benchmark on RC2 with those frozen weights
df = run_benchmark(
    instances        = datasets["rc2"],
    algorithms       = [ALGO_HYBRID_DDQN_TRANSFER],
    cfg              = cfg,
    transfer_weights = weights,
)
```

### Within-RC2 transfer

```python
from vrptw import train_transfer_model_within_rc2, ALGO_HYBRID_DDQN_TRANSFER_RC2

weights = train_transfer_model_within_rc2(datasets["rc2"], cfg, seed=42)
df = run_benchmark(
    instances        = datasets["rc2"][cfg.rc2_transfer_split:],
    algorithms       = [ALGO_HYBRID_DDQN_TRANSFER_RC2],
    cfg              = cfg,
    transfer_weights = weights,
)
```

### Domain randomization pre-training

```python
from vrptw import train_domain_randomization, ALGO_HYBRID_DDQN_TRANSFER_DR

# Trains on randomly generated synthetic instances (3-phase curriculum)
weights = train_domain_randomization(cfg, seed=42)

# Then test frozen on all Solomon instances
df = run_benchmark(
    instances        = datasets["rc1"] + datasets["rc2"],
    algorithms       = [ALGO_HYBRID_DDQN_TRANSFER_DR],
    cfg              = cfg,
    transfer_weights = weights,
)
```

### Load previously saved weights

```python
from vrptw import load_transfer_model

weights = load_transfer_model(cfg, label="rc1")   # loads rl_alns_transfer_rc1_v15.safetensors
```

---

## 7. Web App (Dispatch Portal)

The web app provides an interactive UI for loading Solomon instances or custom CSV data, running solvers, and viewing routes on a map.

### Start the server

```bash
# From the repo root
cp .env.example .env       # first time only
python main.py
```

Then open **http://127.0.0.1:8000** in your browser.

### Demo mode (no auth required)

By default `DEMO_AUTH_BYPASS=true` in `.env` — you can use the app immediately without Firebase credentials.

### Useful API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Shows Firebase status, Torch device, model loaded state |
| `GET /api/config` | Public config the SPA reads on boot |
| `GET /api/solomon?name=rc101` | Load a Solomon instance by name |
| `POST /api/solve` | Submit a solve job (JSON body) |

### Optional: enable Firebase auth + Firestore

1. Create a Firebase project and download a service-account JSON.
2. Place it at `firebase-adminsdk.json` (already gitignored).
3. Set `DEMO_AUTH_BYPASS=false` and `FIREBASE_SERVICE_ACCOUNT_PATH=firebase-adminsdk.json` in `.env`.
4. Restart `python main.py`.

---

## 8. Configuration Reference

All options are fields of the `Config` dataclass in `docs/vrptw/config.py`. The most important ones:

```python
from vrptw import Config

cfg = Config(
    # ── Data paths ──────────────────────────────────────────────────────────
    data_path  = "./data/Solomon",   # directory containing rc101.txt, etc.
    output_dir = "./logs",           # where CSVs and weights are saved

    # ── Search budget ────────────────────────────────────────────────────────
    alns_iterations     = 1200,      # main ALNS iterations
    hybrid_iterations   = 1200,      # Hybrid solver iterations
    early_stop_patience = 250,       # stop if no improvement for N iterations
    polish_iterations   = 80,        # post-search polish phase iterations
    n_runs              = 3,         # runs per (instance, algo) combination
    max_wall_hours      = 9.5,       # hard wall-clock limit for run_benchmark

    # ── Simulated annealing ──────────────────────────────────────────────────
    temp_control = 0.05,
    temp_decay   = 0.99975,

    # ── DDQN controllers ─────────────────────────────────────────────────────
    ctrl_lr    = 3e-4,               # plateau controller learning rate
    op_lr      = 3e-4,               # operator controller learning rate
    lac_enabled = True,              # Learned Acceptance Criterion on/off

    # ── Transfer learning ────────────────────────────────────────────────────
    transfer_epochs    = 1,          # epochs to train transfer model
    transfer_shuffle   = True,
    rc2_transfer_split = 4,          # first N RC2 instances used for training

    # ── OR-Tools ─────────────────────────────────────────────────────────────
    ortools_time_limit = 60.0,       # seconds

    # ── Route pool / set-partitioning ────────────────────────────────────────
    route_pool_limit   = 480,
    sp_time_limit      = 4.0,
)
```

---

## 9. Algorithm Overview

```
python3 -m vrptw.benchmark       # imports but doesn't run anything — safe to use as a module check
```

All solvers share the same `solve(seed, init)` interface and return `(Plan, history)`.

### Solver hierarchy

```
HybridDDQNSolver          (DDQN plateau + operator + LAC controllers)
    └── HybridFixedSolver   (fixed mode-switching rules, no RL)
    └── HybridRuleSolver    (heuristic mode-switching rules, no RL)
ALNSSolver                (pure ALNS, no hybrid modes)
```

### Key modules

| Module | Responsibility |
|--------|---------------|
| `core.py` | `Inst` (problem data), `Plan` (solution), Numba-JIT cost + feasibility |
| `operators.py` | 8 destroy ops (random, worst, shaw, route-segment, TW-urgent, route-eliminate, proximity-eliminate, cross-route-shaw) + 5 repair ops (greedy, regret-2, regret-3, TW-greedy, FTS-greedy) |
| `local_search.py` | 2-opt, relocate, swap, cross-exchange (granular), route-compact |
| `pool.py` | Route pool with MILP (scipy) or greedy set-partitioning recombination |
| `rl.py` | DDQN with Prioritized Experience Replay, Thompson bandit, Learned Acceptance Criterion, Elite Archive |
| `benchmark.py` | Parallel runner (`ProcessPoolExecutor` + spawn), checkpointing, transfer training |

---

## 10. Outputs & Artifacts

### Benchmark CSV columns

| Column | Description |
|--------|-------------|
| `Dataset` | RC1 or RC2 |
| `Instance` | e.g. RC101 |
| `Algorithm` | Canonical algorithm label |
| `NV_mean` | Mean number of vehicles across runs |
| `NV_std` | Std dev of NV |
| `NV_diff` | Mean NV minus BKS NV (negative = fewer vehicles than BKS) |
| `TD_mean` | Mean total distance |
| `TD_std` | Std dev of total distance |
| `Gap%` | `(TD_mean - BKS_TD) / BKS_TD × 100` |
| `OnTime` | On-time delivery rate (%) |
| `Time_s` | Mean wall time per run (seconds) |
| `NV_inflated` | Flag: NV > BKS_NV, making Gap% comparison misleading |

### Print the summary table from a saved CSV

```python
import pandas as pd
from vrptw import print_summary_table

df = pd.read_csv("./logs/benchmark_clean.csv")
print_summary_table(df)
```

---

## 11. GPU Acceleration

The DDQN policy uses PyTorch. The default `requirements.txt` installs CPU-only PyTorch to keep the install small. To use a GPU:

```bash
# Auto-detect CUDA version via nvidia-smi
python docs/scripts/install_torch_gpu.py

# Or force a specific CUDA version (cu118 / cu121 / cu124 / cu126)
python docs/scripts/install_torch_gpu.py --cuda 124
```

Restart afterwards. The startup log will confirm: `Torch device: GPU (NVIDIA ..., CUDA 12.x)`.

> **Note:** The DDQN Q-network is small — GPU speedup for the solver is modest. The bigger win is if you run many parallel benchmark workers.

---

## 12. Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feat/my-feature`).
3. Add tests or a smoke script for your change.
4. Open a Pull Request with a clear summary and test steps.

---

## Best-Known Solutions (BKS Reference)

The BKS values hard-coded in `config.py` are from the [SINTEF TOP benchmark](https://www.sintef.no/projectweb/top/vrptw/):

| Instance | BKS NV | BKS TD |
|----------|--------|--------|
| RC101 | 14 | 1696.94 |
| RC102 | 12 | 1554.75 |
| RC103 | 11 | 1261.67 |
| RC104 | 10 | 1135.48 |
| RC105 | 13 | 1629.44 |
| RC106 | 11 | 1424.73 |
| RC107 | 11 | 1230.48 |
| RC108 | 10 | 1139.82 |
| RC201 |  4 | 1406.94 |
| RC202 |  3 | 1365.64 |
| RC203 |  3 | 1049.62 |
| RC204 |  3 |  798.46 |
| RC205 |  4 | 1297.65 |
| RC206 |  3 | 1146.32 |
| RC207 |  3 | 1061.14 |
| RC208 |  3 |  828.14 |
