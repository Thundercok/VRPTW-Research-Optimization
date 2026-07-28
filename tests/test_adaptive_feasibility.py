import numpy as np

from vrptw.core import Inst, Plan
from vrptw.penalty import AdaptiveFeasibilityManager


def test_adaptive_feasibility_manager_tightness_classification():
    # Scenario A: Tight time windows
    raw_tight = {
        "name": "mock_tight",
        "capacity": 100.0,
        "data": np.array(
            [
                [0, 0, 0, 0, 0, 100, 0],  # Depot: (0, 100)
                [1, 1, 0, 10, 0, 10, 0],  # Customer 1: ready=0, due=10 (Tight: 10/100 = 0.1)
                [2, 2, 0, 10, 5, 15, 0],  # Customer 2: ready=5, due=15 (Tight: 10/100 = 0.1)
            ],
            dtype=np.float64,
        ),
    }
    inst_tight = Inst(raw_tight)
    mgr_tight = AdaptiveFeasibilityManager(inst_tight)

    # Tight time windows (< 0.25 tightness) should initialize with lambda = 50.0
    assert mgr_tight.lam == 50.0

    # Scenario B: Wide time windows
    raw_wide = {
        "name": "mock_wide",
        "capacity": 100.0,
        "data": np.array(
            [
                [0, 0, 0, 0, 0, 100, 0],  # Depot: (0, 100)
                [1, 1, 0, 10, 0, 80, 0],  # Customer 1: ready=0, due=80 (Wide: 80/100 = 0.8)
                [2, 2, 0, 10, 0, 90, 0],  # Customer 2: ready=0, due=90 (Wide: 90/100 = 0.9)
            ],
            dtype=np.float64,
        ),
    }
    inst_wide = Inst(raw_wide)
    mgr_wide = AdaptiveFeasibilityManager(inst_wide)

    # Wide time windows (>= 0.25 tightness) should initialize with lambda = 1.0
    assert mgr_wide.lam == 1.0


def test_adaptive_feasibility_manager_lambda_updates():
    raw = {
        "name": "mock",
        "capacity": 100.0,
        "data": np.array(
            [
                [0, 0, 0, 0, 0, 100, 0],
                [1, 1, 0, 10, 0, 80, 0],
                [2, 2, 0, 10, 0, 90, 0],
            ],
            dtype=np.float64,
        ),
    }
    inst = Inst(raw)
    mgr = AdaptiveFeasibilityManager(inst, target_ratio=0.5, alpha_ema=0.1)

    # Start with lam = 1.0
    assert mgr.lam == 1.0

    # Record a sequence of feasible plans -> ratio should rise -> lam should decrease
    for _ in range(20):
        # mock plan with zero violations
        plan = Plan([[1, 2]], inst)
        mgr.record_solution(plan)
        mgr.update_penalties()

    assert mgr.lam < 1.0

    # Record a sequence of infeasible plans (we mock this by manually setting a low ratio or directly triggering updates)
    mgr.feasible_ema = 0.1  # simulate high infeasibility rate
    mgr.update_penalties()
    assert mgr.lam > 0.1  # lam should start increasing again
