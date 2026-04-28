"""Web solver: delegate to DDQN-ALNS (`PlateauHybridSolver`) and ALNS from the
research code. CPU-bound work runs in a thread to not block the asyncio loop.

Config is tuned for web responsiveness: ~500 iterations cap so a typical
20-customer request finishes within ~10-20s on CPU. For benchmarks use
`vrptw_clean.run_instance` directly.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import torch
from models.schemas import JobRequest
from services.research_adapter import build_inst, plan_to_payload

_ROOT = Path(__file__).resolve().parents[3]
for candidate in (_ROOT, _ROOT / "docs"):
    if candidate.exists():
        sys.path.insert(0, str(candidate))

from vrptw_clean import ALNSSolver, Config, PlateauHybridSolver  # noqa: E402

logger = logging.getLogger(__name__)


def device_summary() -> dict[str, Any]:
    """Inspect the active torch device. Used for /api/health and startup logs."""
    cuda_available = bool(torch.cuda.is_available())
    info: dict[str, Any] = {
        "torch_version": torch.__version__,
        "cuda_available": cuda_available,
        "cuda_built": torch.version.cuda or None,
        "device": "cuda" if cuda_available else "cpu",
    }
    if cuda_available:
        try:
            info["device_name"] = torch.cuda.get_device_name(0)
            info["device_count"] = torch.cuda.device_count()
        except Exception:
            info["device_name"] = "unknown"
            info["device_count"] = 1
    return info


_DEVICE_LOGGED = False


def _log_device_once() -> None:
    global _DEVICE_LOGGED
    if _DEVICE_LOGGED:
        return
    _DEVICE_LOGGED = True
    info = device_summary()
    if info["cuda_available"]:
        logger.info(
            "Torch device: GPU (%s, CUDA %s, %s)",
            info.get("device_name", "unknown"),
            info.get("cuda_built", "?"),
            info.get("torch_version"),
        )
    else:
        logger.info(
            "Torch device: CPU only (torch %s). For GPU acceleration run "
            "`python scripts/install_torch_gpu.py`.",
            info.get("torch_version"),
        )

WEB_CONFIG = Config(
    alns_iterations=500,
    hybrid_iterations=500,
    early_stop_patience=200,
    polish_iterations=100,
    polish_patience=60,
    n_runs=1,
)

_DEFAULT_TRANSFER_PATH = _ROOT / "model" / "rl_alns_transfer.safetensors"
_LEGACY_TRANSFER_PATH = _ROOT / "logs" / "results-v9.5" / "rl_alns_transfer.safetensors"

_WEIGHTS_LOADED_ONCE = False
_WEIGHTS_PATH_USED: str | None = None


def _resolve_transfer_path() -> Path | None:
    """Return the path that ``_load_transfer_weights`` will try, or None if missing."""
    path_env = os.environ.get("VRPTW_TRANSFER_WEIGHTS")
    if path_env:
        candidate = Path(path_env)
        return candidate if candidate.exists() else None
    if _DEFAULT_TRANSFER_PATH.exists():
        return _DEFAULT_TRANSFER_PATH
    if _LEGACY_TRANSFER_PATH.exists():
        return _LEGACY_TRANSFER_PATH
    return None


def _align_action_head(state: dict[str, torch.Tensor], target_module: torch.nn.Module) -> tuple[dict[str, torch.Tensor], int]:
    """Pad the action-head row dimension when the checkpoint was trained with
    fewer modes than the current code defines.

    Returns ``(new_state, padded_rows)``. ``padded_rows == 0`` means no padding
    was needed. We assume the missing modes are appended *after* the trained
    ones (which matches the project history where ``route_reduce`` was added as
    the last mode). The new rows are seeded with the mean of the trained rows
    so they do not dominate or get systematically ignored at argmax time.
    """
    aligned = dict(state)
    padded = 0
    target_state = target_module.state_dict()

    for key in list(aligned.keys()):
        if key not in target_state:
            continue
        saved = aligned[key]
        target = target_state[key]
        if saved.shape == target.shape:
            continue
        # Only handle the case where the row dimension grew (more output modes).
        if saved.ndim == target.ndim and saved.ndim in (1, 2):
            saved_rows = saved.shape[0]
            target_rows = target.shape[0]
            if 0 < saved_rows < target_rows and saved.shape[1:] == target.shape[1:]:
                extra = target_rows - saved_rows
                if saved.ndim == 2:
                    seed = saved.mean(dim=0, keepdim=True).expand(extra, -1).clone()
                else:
                    seed = saved.mean().expand(extra).clone()
                aligned[key] = torch.cat([saved, seed], dim=0)
                padded = max(padded, extra)
    return aligned, padded


def _load_transfer_weights(solver: PlateauHybridSolver) -> bool:
    """Hot-load the trained DDQN policy. Logs the outcome on first call."""
    global _WEIGHTS_LOADED_ONCE, _WEIGHTS_PATH_USED

    path = _resolve_transfer_path()
    if path is None:
        if not _WEIGHTS_LOADED_ONCE:
            _WEIGHTS_LOADED_ONCE = True
            logger.warning(
                "DDQN transfer weights NOT FOUND. Searched %s and %s. The DDQN "
                "policy will run on randomly-initialised weights (epsilon = "
                "%.3f). Set VRPTW_TRANSFER_WEIGHTS or restore "
                "model/rl_alns_transfer.safetensors.",
                _DEFAULT_TRANSFER_PATH,
                _LEGACY_TRANSFER_PATH,
                float(WEB_CONFIG.ctrl_eps_end),
            )
        return False

    try:
        from safetensors.torch import load_file

        state = load_file(str(path))
        aligned_q, padded_q = _align_action_head(state, solver.ctrl.q)
        aligned_qt, _ = _align_action_head(state, solver.ctrl.q_t)
        # strict=True now that shapes match, so we never silently skip layers.
        solver.ctrl.q.load_state_dict(aligned_q, strict=True)
        solver.ctrl.q_t.load_state_dict(aligned_qt, strict=True)
        if not _WEIGHTS_LOADED_ONCE:
            _WEIGHTS_LOADED_ONCE = True
            _WEIGHTS_PATH_USED = str(path)
            if padded_q > 0:
                logger.warning(
                    "DDQN transfer weights loaded from %s with %d action-head row(s) "
                    "padded (checkpoint trained on %d modes, current code defines %d). "
                    "Trained behaviour is preserved for the original modes; new modes "
                    "start with the mean Q-values.",
                    path,
                    padded_q,
                    len(state.get("net.5.weight", torch.empty(0))),
                    solver.ctrl.q.state_dict()["net.5.weight"].shape[0],
                )
            else:
                logger.info("DDQN transfer weights loaded from %s (%d tensors).", path, len(state))
        return True
    except Exception as exc:
        if not _WEIGHTS_LOADED_ONCE:
            _WEIGHTS_LOADED_ONCE = True
            logger.error("Failed to load DDQN transfer weights from %s: %s", path, exc)
        return False


def transfer_weights_summary() -> dict[str, Any]:
    """Reflection helper used by /api/health and tests."""
    path = _resolve_transfer_path()
    return {
        "available": path is not None,
        "path": str(path) if path else None,
        "loaded_once": _WEIGHTS_LOADED_ONCE,
        "loaded_path": _WEIGHTS_PATH_USED,
    }


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
    _log_device_once()
    torch.set_num_threads(max(1, (os.cpu_count() or 4) // 2))

    loop = asyncio.get_running_loop()
    ddqn_task = loop.run_in_executor(None, _run_ddqn_alns, payload)
    alns_task = loop.run_in_executor(None, _run_alns, payload)
    ddqn_result, alns_result = await asyncio.gather(ddqn_task, alns_task)
    return {"ddqn": ddqn_result, "alns": alns_result}
