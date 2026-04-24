"""Quick smoke test: Solomon loader + web solver path with TW fields."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "web" / "backend"))


def main() -> int:
    from services.solomon_service import load_solomon_dataset
    from services.research_adapter import build_inst, plan_to_payload
    from models.schemas import Point

    data = load_solomon_dataset("rc101")
    print(f"[solomon] dataset={data['dataset']} fleet={data['fleet']} n={len(data['customers'])}")
    first3 = data["customers"][:3]
    for c in first3:
        print(f"  id={c['id']} demand={c['demand']} ready={c['ready']} due={c['due']} svc={c['service']}")

    subset = data["customers"][:21]
    points = [Point(**c) for c in subset]
    inst = build_inst(points, capacity=int(data["fleet"]["capacity"]), name="SmokeRC101-20")
    print(f"[inst] n={inst.n} capacity={inst.capacity}")

    from vrptw_clean import ALNSSolver, Config

    cfg = Config(max_iter=200, seed=1)
    solver = ALNSSolver(inst, cfg)
    t0 = time.time()
    plan = solver.run()
    rt = time.time() - t0
    payload = plan_to_payload(plan, points, rt)
    print(
        f"[alns] runtime={rt:.2f}s vehicles={payload['vehicles_used']} "
        f"total_km={payload['total_distance_km']:.2f}"
    )
    assert payload["vehicles_used"] >= 1
    assert payload["total_distance_km"] > 0
    print("[ok] smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
