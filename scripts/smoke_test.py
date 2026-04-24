"""Quick smoke test: run ALNS and DDQN-ALNS on RC101 with reduced iterations."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vrptw_clean import Config, load_datasets, default_data_path, run_instance


def main() -> None:
    cfg = Config(
        alns_iterations=200,
        hybrid_iterations=200,
        n_runs=1,
        early_stop_patience=100,
        polish_iterations=50,
        polish_patience=30,
    )
    datasets = load_datasets(default_data_path())
    inst = datasets["rc1"][0]
    print(f"Instance {inst.name} n={inst.n} capacity={inst.capacity}")

    print("=== ALNS ===")
    r1 = run_instance(inst, "ALNS", cfg, seed=42)
    print(
        f"nv={r1['nv']} cost={r1['cost']:.2f} gap={r1['td_gap']:+.2f}% time={r1['time']:.1f}s"
    )

    print("=== DDQN-ALNS (PLATEAU-HYBRID) ===")
    r2 = run_instance(inst, "PLATEAU-HYBRID", cfg, seed=42)
    print(
        f"nv={r2['nv']} cost={r2['cost']:.2f} gap={r2['td_gap']:+.2f}% time={r2['time']:.1f}s"
    )


if __name__ == "__main__":
    main()
