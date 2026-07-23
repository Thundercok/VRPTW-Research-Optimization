"""
Capture golden (nv, cost) fingerprints for solver regression testing.

Phase 1 and Phase 2 of the optimisation work are behaviour-preserving: they must
reproduce these fingerprints bit-identically. Phase 3 onward intentionally changes
search trajectories, at which point this file is regenerated and the delta recorded.

Usage:
    python scripts/capture_golden.py                 # write tests/golden/baseline.json
    python scripts/capture_golden.py --out other.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from vrptw.config import Config  # noqa: E402
from vrptw.core import Inst, load_solomon_instance  # noqa: E402
from vrptw.solvers import ALNSSolver, HybridDDQNSolver  # noqa: E402

# Small, fast, and spanning the instance families that behave differently:
# tight-TW (R101/RC207), clustered (C101), and a 200-customer Homberger shard.
GOLDEN_INSTANCES = [
    ("R101", "data/Solomon/r101.txt"),
    ("RC207", "data/Solomon/rc207.txt"),
    ("C101", "data/Solomon/c101.txt"),
    ("r1_2_1", "data/Gehring_Homberger/homberger_200_customer_instances/R1_2_1.TXT"),
]

GOLDEN_SEEDS = [1, 7]
GOLDEN_ITERS = 200


def load_instance(path: str) -> Inst:
    """Parse a Solomon/Homberger formatted instance file."""
    return load_solomon_instance(path)


def _make_cfg() -> Config:
    """Deterministic, short-budget config. Early stop is disabled so the
    iteration count (and therefore the RNG stream) is fixed across runs."""
    return Config(
        alns_iterations=GOLDEN_ITERS,
        hybrid_iterations=GOLDEN_ITERS,
        early_stop_patience=10**9,
        split_enabled=False,
        time_limit=None,
        time_limit_per_customer=0.0,
    )


def capture(repo_root: str = _REPO) -> dict:
    records = []
    for label, rel_path in GOLDEN_INSTANCES:
        path = os.path.join(repo_root, rel_path)
        if not os.path.exists(path):
            print(f"  SKIP {label}: {rel_path} not found")
            continue
        inst = load_instance(path)
        for solver_name, solver_cls in (("Hybrid-DDQN", HybridDDQNSolver), ("ALNS-Base", ALNSSolver)):
            for seed in GOLDEN_SEEDS:
                solver = solver_cls(inst, _make_cfg())
                t0 = time.time()
                best, _ = solver.solve(seed=seed)
                elapsed = time.time() - t0
                records.append(
                    {
                        "instance": label,
                        "solver": solver_name,
                        "seed": seed,
                        "nv": int(best.nv),
                        "cost": float(best.cost),
                        "feasible": bool(best.feasible),
                        "wall_time": round(elapsed, 3),
                    }
                )
                print(
                    f"  {label:8s} {solver_name:12s} seed={seed}  "
                    f"nv={best.nv:3d}  cost={best.cost:11.4f}  {elapsed:7.2f}s"
                )
    return {
        "iters": GOLDEN_ITERS,
        "seeds": GOLDEN_SEEDS,
        "records": records,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(_REPO, "tests", "golden", "baseline.json"))
    args = ap.parse_args()

    print(f"Capturing golden fingerprints ({GOLDEN_ITERS} iterations, seeds {GOLDEN_SEEDS})...")
    payload = capture()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    total = sum(r["wall_time"] for r in payload["records"])
    print(f"\nWrote {len(payload['records'])} records to {args.out} (total solve time {total:.1f}s)")


if __name__ == "__main__":
    main()
