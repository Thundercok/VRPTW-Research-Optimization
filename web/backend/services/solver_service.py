"""Web solver: delegate to DDQN-ALNS (`PlateauHybridSolver`) and ALNS from the
research code. CPU-bound work runs in a thread to not block the asyncio loop.

Config is tuned for web responsiveness: ~500 iterations cap so a typical
20-customer request finishes within ~10-20s on CPU. For benchmarks use
`vrptw_clean.run_instance` directly.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any

import torch

from models.schemas import JobRequest
from services.research_adapter import build_inst, plan_to_payload

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from vrptw_clean import ALNSSolver, Config, PlateauHybridSolver  # noqa: E402

WEB_CONFIG = Config(
    alns_iterations=500,
    hybrid_iterations=500,
    early_stop_patience=200,
    polish_iterations=100,
    polish_patience=60,
    n_runs=1,
)

_DEFAULT_TRANSFER_PATH = _ROOT / "logs" / "results-v9.5" / "rl_alns_transfer.safetensors"


def _load_transfer_weights(solver: PlateauHybridSolver) -> bool:
    path_env = os.environ.get("VRPTW_TRANSFER_WEIGHTS")
    path = Path(path_env) if path_env else _DEFAULT_TRANSFER_PATH
    if not path.exists():
        return False
    try:
        from safetensors.torch import load_file

        state = load_file(str(path))
        solver.ctrl.q.load_state_dict(state, strict=False)
        solver.ctrl.q_t.load_state_dict(state, strict=False)
        return True
    except Exception:
        return False


def _run_ddqn_alns(payload: JobRequest) -> dict[str, Any]:
    inst = build_inst(payload.customers, capacity=payload.fleet.capacity, name="DDQN-ALNS")
    solver = PlateauHybridSolver(inst, WEB_CONFIG)
    _load_transfer_weights(solver)
    solver.ctrl.eps = WEB_CONFIG.ctrl_eps_end
    start = time.time()
    plan, _ = solver.solve(seed=WEB_CONFIG.seed)
    elapsed = time.time() - start

    if plan.nv > payload.fleet.vehicles:
        raise ValueError(
            f"Infeasible configuration: requires {plan.nv} vehicles but only {payload.fleet.vehicles} provided"
        )

    return plan_to_payload(plan, payload.customers, elapsed)


def _run_alns(payload: JobRequest) -> dict[str, Any]:
    inst = build_inst(payload.customers, capacity=payload.fleet.capacity, name="ALNS")
    solver = ALNSSolver(inst, WEB_CONFIG)
    start = time.time()
    plan, _ = solver.solve(seed=WEB_CONFIG.seed)
    elapsed = time.time() - start

    if plan.nv > payload.fleet.vehicles:
        raise ValueError(
            f"Infeasible configuration: requires {plan.nv} vehicles but only {payload.fleet.vehicles} provided"
        )

    return plan_to_payload(plan, payload.customers, elapsed)


def _validate(payload: JobRequest) -> None:
    points = payload.customers
    if len(points) < 2:
        raise ValueError("Need depot and at least one customer")
    if payload.fleet.vehicles <= 0:
        raise ValueError("Vehicles must be at least 1")
    if payload.fleet.capacity <= 0:
        raise ValueError("Capacity must be at least 1")
    for c in points[1:]:
        if c.demand < 0:
            raise ValueError(f"Customer {c.id} has negative demand")
        if c.demand > payload.fleet.capacity:
            raise ValueError(
                f"Customer demand {c.demand} exceeds vehicle capacity {payload.fleet.capacity} (customer id={c.id})"
            )


async def solve_model(payload: JobRequest) -> dict[str, Any]:
    _validate(payload)
    torch.set_num_threads(max(1, (os.cpu_count() or 4) // 2))

    loop = asyncio.get_running_loop()
    ddqn_task = loop.run_in_executor(None, _run_ddqn_alns, payload)
    alns_task = loop.run_in_executor(None, _run_alns, payload)
    ddqn_result, alns_result = await asyncio.gather(ddqn_task, alns_task)
    return {"ddqn": ddqn_result, "alns": alns_result}
