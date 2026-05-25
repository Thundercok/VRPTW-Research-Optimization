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
from typing import Any, NamedTuple

from fastapi import HTTPException
from models.schemas import JobRequest

_ROOT = Path(__file__).resolve().parents[3]
for candidate in (_ROOT / "src", _ROOT):
    if candidate.exists():
        sys.path.insert(0, str(candidate))

logger = logging.getLogger(__name__)


class SolverRuntime(NamedTuple):
    torch: Any
    config: Any
    alns_solver: Any
    plateau_hybrid_solver: Any
    build_inst: Any
    plan_to_payload: Any


_RUNTIME: SolverRuntime | None = None
_RUNTIME_IMPORT_ERROR: str | None = None
_WEB_CONFIG: Any | None = None


def _load_solver_runtime() -> SolverRuntime:
    """Import the heavy research stack only when a solve actually runs."""
    global _RUNTIME, _RUNTIME_IMPORT_ERROR
    if _RUNTIME is not None:
        return _RUNTIME
    if _RUNTIME_IMPORT_ERROR is not None:
        raise RuntimeError(_RUNTIME_IMPORT_ERROR)

    try:
        import torch
        from services.research_adapter import build_inst, plan_to_payload

        from vrptw import ALNSSolver, Config, PlateauHybridSolver
    except ImportError as exc:
        _RUNTIME_IMPORT_ERROR = str(exc)
        raise RuntimeError(_RUNTIME_IMPORT_ERROR) from exc

    _RUNTIME = SolverRuntime(
        torch=torch,
        config=Config,
        alns_solver=ALNSSolver,
        plateau_hybrid_solver=PlateauHybridSolver,
        build_inst=build_inst,
        plan_to_payload=plan_to_payload,
    )
    return _RUNTIME


def _get_web_config() -> Any:
    global _WEB_CONFIG
    if _WEB_CONFIG is None:
        runtime = _load_solver_runtime()
        _WEB_CONFIG = runtime.config(
            alns_iterations=500,
            hybrid_iterations=500,
            early_stop_patience=200,
            polish_iterations=100,
            polish_patience=60,
            n_runs=1,
        )
    return _WEB_CONFIG


class _LazyWebConfig:
    def __getattr__(self, name: str) -> Any:
        return getattr(_get_web_config(), name)


WEB_CONFIG = _LazyWebConfig()


def device_summary() -> dict[str, Any]:
    """Inspect the active torch device. Used for /api/health and startup logs."""
    try:
        import torch
    except ImportError:
        return {
            "torch_version": "not-installed",
            "cuda_available": False,
            "cuda_built": None,
            "device": "cpu",
        }
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

_DEFAULT_TRANSFER_PATH = _ROOT / "model" / "rl_alns_transfer.safetensors"
_DR_TRANSFER_PATH = _ROOT / "rl_alns_dr_v15.safetensors"
_DOCS_DR_TRANSFER_PATH = _ROOT / "docs" / "rl_alns_dr_v15.safetensors"
_DOCS_TRANSFER_PATH = _ROOT / "docs" / "model" / "rl_alns_transfer.safetensors"
_LEGACY_TRANSFER_PATH = _ROOT / "logs" / "results-v9.5" / "rl_alns_transfer.safetensors"

_WEIGHTS_LOADED_ONCE = False
_WEIGHTS_PATH_USED: str | None = None


def _resolve_transfer_path() -> Path | None:
    """Return the path that ``_load_transfer_weights`` will try, or None if missing."""
    path_env = os.environ.get("VRPTW_TRANSFER_WEIGHTS")
    if path_env:
        candidate = Path(path_env)
        return candidate if candidate.exists() else None
    for candidate in (
        _DEFAULT_TRANSFER_PATH,
        _DR_TRANSFER_PATH,
        _DOCS_DR_TRANSFER_PATH,
        _DOCS_TRANSFER_PATH,
        _LEGACY_TRANSFER_PATH,
    ):
        if candidate.exists():
            return candidate
    return None


def _align_action_head(state: dict[str, Any], target_module: Any) -> tuple[dict[str, Any], int]:
    """Pad the action-head row dimension when the checkpoint was trained with
    fewer modes than the current code defines.

    Returns ``(new_state, padded_rows)``. ``padded_rows == 0`` means no padding
    was needed. We assume the missing modes are appended *after* the trained
    ones (which matches the project history where ``route_reduce`` was added as
    the last mode). The new rows are seeded with the mean of the trained rows
    so they do not dominate or get systematically ignored at argmax time.
    """
    runtime = _load_solver_runtime()
    torch = runtime.torch
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


def _load_transfer_weights(solver: Any) -> bool:
    """Hot-load the trained DDQN policy. Logs the outcome on first call."""
    global _WEIGHTS_LOADED_ONCE, _WEIGHTS_PATH_USED

    runtime = _load_solver_runtime()
    torch = runtime.torch
    config = _get_web_config()
    path = _resolve_transfer_path()
    if path is None:
        if not _WEIGHTS_LOADED_ONCE:
            _WEIGHTS_LOADED_ONCE = True
            logger.warning(
                "DDQN transfer weights NOT FOUND. Searched %s, %s, %s, %s, and %s. The DDQN "
                "policy will run on randomly-initialised weights (epsilon = "
                "%.3f). Set VRPTW_TRANSFER_WEIGHTS or restore "
                "model/rl_alns_transfer.safetensors.",
                _DEFAULT_TRANSFER_PATH,
                _DR_TRANSFER_PATH,
                _DOCS_DR_TRANSFER_PATH,
                _DOCS_TRANSFER_PATH,
                _LEGACY_TRANSFER_PATH,
                float(config.ctrl_eps_end),
            )
        return False

    try:
        from safetensors.torch import load_file

        state = load_file(str(path))
        if any(key.startswith(("plateau.", "operator.", "lac.", "reward_norm.", "ucb.")) for key in state):
            solver.load_weights(state)
            if not _WEIGHTS_LOADED_ONCE:
                _WEIGHTS_LOADED_ONCE = True
                _WEIGHTS_PATH_USED = str(path)
                logger.info("DDQN solver weights loaded from %s (%d tensors).", path, len(state))
            return True

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
    runtime = _load_solver_runtime()
    config = _get_web_config()
    inst = runtime.build_inst(payload.customers, capacity=payload.fleet.capacity, name="DDQN-ALNS")
    solver = runtime.plateau_hybrid_solver(inst, config)
    _load_transfer_weights(solver)
    solver.ctrl.eps = config.ctrl_eps_end
    start = time.time()
    plan, _ = solver.solve(seed=config.seed)
    elapsed = time.time() - start

    if plan.nv > payload.fleet.vehicles:
        raise ValueError(
            f"Infeasible configuration: requires {plan.nv} vehicles but only {payload.fleet.vehicles} provided"
        )

    return runtime.plan_to_payload(plan, payload.customers, elapsed)


def _run_alns(payload: JobRequest) -> dict[str, Any]:
    runtime = _load_solver_runtime()
    config = _get_web_config()
    inst = runtime.build_inst(payload.customers, capacity=payload.fleet.capacity, name="ALNS")
    solver = runtime.alns_solver(inst, config)
    start = time.time()
    plan, _ = solver.solve(seed=config.seed)
    elapsed = time.time() - start

    if plan.nv > payload.fleet.vehicles:
        raise ValueError(
            f"Infeasible configuration: requires {plan.nv} vehicles but only {payload.fleet.vehicles} provided"
        )

    return runtime.plan_to_payload(plan, payload.customers, elapsed)


def _load_weights_for_solver(solver: Any, algo: str) -> None:
    import os

    from safetensors.torch import load_file


    label = "rc1" if "rc1" in algo else "dr"
    candidates = []
    output_dir = _ROOT / "logs"

    if label == "dr":
        candidates = [
            _DR_TRANSFER_PATH,
            _DOCS_DR_TRANSFER_PATH,
            output_dir / "rl_alns_dr_v15.safetensors",
            output_dir / "rl_alns_dr_v15.pt",
            _ROOT / "rl_alns_dr_v15.safetensors",
        ]
    else:
        candidates = [
            _DEFAULT_TRANSFER_PATH,
            _DOCS_TRANSFER_PATH,
            _LEGACY_TRANSFER_PATH,
        ]

    for cand in candidates:
        path_str = str(cand)
        if os.path.exists(path_str):
            try:
                state = load_file(path_str)
                if hasattr(solver, "load_weights"):
                    solver.load_weights(state)
                else:
                    aligned_q, _ = _align_action_head(state, solver.ctrl.q)
                    aligned_qt, _ = _align_action_head(state, solver.ctrl.q_t)
                    solver.ctrl.q.load_state_dict(aligned_q, strict=True)
                    solver.ctrl.q_t.load_state_dict(aligned_qt, strict=True)
                logger.info("Loaded transfer weights for %s from %s", algo, path_str)
                return
            except Exception as e:
                logger.error("Failed loading weight candidate %s for %s: %s", path_str, algo, e)


def _run_algo_generic(payload: JobRequest, algo: str) -> dict[str, Any]:
    runtime = _load_solver_runtime()
    config = _get_web_config()
    import vrptw

    inst = runtime.build_inst(payload.customers, capacity=payload.fleet.capacity, name=algo)

    if algo == "ortools":
        plan, elapsed = vrptw.run_ortools(inst, config)
        if plan is None:
            raise ValueError("OR-Tools failed to find a feasible solution")
        return runtime.plan_to_payload(plan, payload.customers, elapsed)

    elif algo == "alns_base":
        solver = vrptw.ALNSSolver(inst, config)
        start = time.time()
        plan, _ = solver.solve(seed=config.seed)
        elapsed = time.time() - start
        return runtime.plan_to_payload(plan, payload.customers, elapsed)

    elif algo == "hybrid_fixed":
        solver = vrptw.HybridFixedSolver(inst, config)
        start = time.time()
        plan, _ = solver.solve(seed=config.seed)
        elapsed = time.time() - start
        return runtime.plan_to_payload(plan, payload.customers, elapsed)

    elif algo == "hybrid_ddqn":
        solver = vrptw.HybridDDQNSolver(inst, config)
        start = time.time()
        plan, _ = solver.solve(seed=config.seed)
        elapsed = time.time() - start
        return runtime.plan_to_payload(plan, payload.customers, elapsed)

    elif algo == "hybrid_ddqn_transfer_rc1":
        solver = vrptw.HybridDDQNSolver(inst, config)
        _load_weights_for_solver(solver, algo)
        start = time.time()
        plan, _ = solver.solve(seed=config.seed)
        elapsed = time.time() - start
        return runtime.plan_to_payload(plan, payload.customers, elapsed)

    elif algo == "hybrid_ddqn_transfer_dr":
        solver = vrptw.HybridDDQNSolver(inst, config)
        _load_weights_for_solver(solver, algo)
        start = time.time()
        plan, _ = solver.solve(seed=config.seed)
        elapsed = time.time() - start
        return runtime.plan_to_payload(plan, payload.customers, elapsed)

    else:
        raise ValueError(f"Unknown algorithm specified: {algo}")


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


async def solve_model(payload: JobRequest, matrix: list[list[float]] | None = None) -> dict[str, Any]:
    try:
        runtime = _load_solver_runtime()
        _get_web_config()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Solver is unavailable because a runtime dependency is not installed: {exc}",
        ) from exc
    _validate(payload)
    _log_device_once()
    runtime.torch.set_num_threads(max(1, (os.cpu_count() or 4) // 2))

    loop = asyncio.get_running_loop()
    algos = ["ddqn", "alns", "ortools", "hybrid_fixed", "hybrid_ddqn", "hybrid_ddqn_transfer_rc1", "hybrid_ddqn_transfer_dr"]

    tasks = {}
    for algo in algos:
        if algo == "ddqn":
            tasks[algo] = loop.run_in_executor(None, _run_ddqn_alns, payload)
        elif algo == "alns":
            tasks[algo] = loop.run_in_executor(None, _run_alns, payload)
        else:
            tasks[algo] = loop.run_in_executor(None, _run_algo_generic, payload, algo)

    results = {}
    for algo, task in tasks.items():
        try:
            results[algo] = await task
        except Exception as e:
            logger.error("Failed running algorithm pipeline %s: %s", algo, e)

    return results
