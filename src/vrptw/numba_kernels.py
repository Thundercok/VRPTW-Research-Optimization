"""
JIT-compiled Numba kernels for VRPTW local-search hot paths.

Every function is decorated with ``@njit(cache=True)`` and operates
exclusively on NumPy arrays and scalars (no Python objects).
"""

from __future__ import annotations

import numpy as np
from numba import njit

from .core import _route_cost, _route_ok

# ──────────────────────────────────────────────────────────────────────
# 1.  2-opt (intra-route)
# ──────────────────────────────────────────────────────────────────────


@njit(cache=True)
def _two_opt_best_numba(
    route_arr: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
):
    """Return (best_route, improved) after trying every 2-opt reversal."""
    n = len(route_arr)
    if n < 4:
        return route_arr.copy(), False

    best_cost = _route_cost(route_arr, dist)
    best_arr = route_arr.copy()
    improved = False
    cand = np.empty(n, dtype=np.int64)

    for i in range(n - 2):
        for j in range(i + 2, n):
            # Build candidate: prefix | reversed segment | suffix
            idx = 0
            for k in range(0, i):
                cand[idx] = route_arr[k]
                idx += 1
            for k in range(j, i - 1, -1):
                cand[idx] = route_arr[k]
                idx += 1
            for k in range(j + 1, n):
                cand[idx] = route_arr[k]
                idx += 1

            if not _route_ok(cand, demands, capacity, ready, due, service, dist):
                continue
            cc = _route_cost(cand, dist)
            if cc + 1e-9 < best_cost:
                best_cost = cc
                for k in range(n):
                    best_arr[k] = cand[k]
                improved = True

    return best_arr, improved


# ──────────────────────────────────────────────────────────────────────
# 2.  Intra-route Or-Opt  (segment lengths 1, 2, 3)
# ──────────────────────────────────────────────────────────────────────


@njit(cache=True)
def _or_opt_intra_numba(
    route_arr: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
):
    """Return (best_route, improved) after trying all intra-route or-opt moves."""
    n = len(route_arr)
    best_cost = _route_cost(route_arr, dist)
    best_arr = route_arr.copy()
    improved = False

    remainder = np.empty(n, dtype=np.int64)
    cand = np.empty(n, dtype=np.int64)
    seg = np.empty(3, dtype=np.int64)

    for L in range(1, 4):  # segment lengths 1, 2, 3
        if n < L + 2:
            continue
        for sp in range(n - L + 1):
            # Extract segment
            for k in range(L):
                seg[k] = route_arr[sp + k]

            # Build remainder (route without segment)
            rn = 0
            for k in range(n):
                if k < sp or k >= sp + L:
                    remainder[rn] = route_arr[k]
                    rn += 1
            # rn == n - L

            for ip in range(rn + 1):
                for rev in range(2):  # 0 = forward, 1 = reversed
                    # Build candidate: remainder[:ip] + seg + remainder[ip:]
                    ci = 0
                    for k in range(ip):
                        cand[ci] = remainder[k]
                        ci += 1
                    if rev == 0:
                        for k in range(L):
                            cand[ci] = seg[k]
                            ci += 1
                    else:
                        for k in range(L - 1, -1, -1):
                            cand[ci] = seg[k]
                            ci += 1
                    for k in range(ip, rn):
                        cand[ci] = remainder[k]
                        ci += 1

                    # Skip identity move (element-by-element comparison)
                    is_identity = True
                    for k in range(n):
                        if cand[k] != route_arr[k]:
                            is_identity = False
                            break
                    if is_identity:
                        continue

                    if not _route_ok(cand, demands, capacity, ready, due, service, dist):
                        continue
                    cc = _route_cost(cand, dist)
                    if cc + 1e-9 < best_cost:
                        best_cost = cc
                        for k in range(n):
                            best_arr[k] = cand[k]
                        improved = True

    return best_arr, improved


# ──────────────────────────────────────────────────────────────────────
# 3.  Combined intra-route optimise  (alternates 2-opt ↔ or-opt)
# ──────────────────────────────────────────────────────────────────────


@njit(cache=True)
def _intra_route_optimize_numba(
    route_arr: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
    max_passes: int,
):
    """Alternate 2-opt and or-opt passes until convergence or *max_passes*."""
    best = route_arr.copy()
    for _pass in range(max_passes):
        changed = False

        arr2, imp2 = _two_opt_best_numba(best, dist, demands, capacity, ready, due, service)
        if imp2:
            best = arr2
            changed = True

        arr3, imp3 = _or_opt_intra_numba(best, dist, demands, capacity, ready, due, service)
        if imp3:
            best = arr3
            changed = True

        if not changed:
            break

    return best


# ──────────────────────────────────────────────────────────────────────
# 4.  Inter-route single-node swap evaluation
# ──────────────────────────────────────────────────────────────────────


@njit(cache=True)
def _swap_evaluate_numba(
    r1: np.ndarray,
    r2: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
):
    """
    Evaluate every single-node swap between *r1* and *r2*.

    Returns ``(best_delta, sp, dp)`` where *sp*/*dp* are positions in
    *r1*/*r2* respectively.  If no improving swap exists the sentinel
    ``(-1e-9, -1, -1)`` is returned.
    """
    n1 = len(r1)
    n2 = len(r2)
    c1 = _route_cost(r1, dist)
    c2 = _route_cost(r2, dist)
    old_cost = c1 + c2

    best_delta = -1e-9
    best_sp = -1
    best_dp = -1

    # Working copies
    t1 = r1.copy()
    t2 = r2.copy()

    for sp in range(n1):
        for dp in range(n2):
            if r1[sp] == r2[dp]:
                continue

            # Swap in-place
            t1[sp] = r2[dp]
            t2[dp] = r1[sp]

            if _route_ok(t1, demands, capacity, ready, due, service, dist) and _route_ok(
                t2, demands, capacity, ready, due, service, dist
            ):
                new_cost = _route_cost(t1, dist) + _route_cost(t2, dist)
                delta = new_cost - old_cost
                if delta < best_delta:
                    best_delta = delta
                    best_sp = sp
                    best_dp = dp

            # Undo swap
            t1[sp] = r1[sp]
            t2[dp] = r2[dp]

    return best_delta, best_sp, best_dp


# ──────────────────────────────────────────────────────────────────────
# 5.  Best segment insertion into a route
# ──────────────────────────────────────────────────────────────────────


@njit(cache=True)
def _best_segment_insert_numba(
    seg: np.ndarray,
    route: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
):
    """
    Find the best position to insert *seg* into *route*.

    Both forward and reversed orientations are tried.  Capacity is
    checked first for an early exit.

    Returns ``(best_delta, best_pos, rev_int)`` or ``(1e18, -1, 0)``
    if no feasible insertion exists.
    """
    seg_len = len(seg)
    rn = len(route)
    new_len = rn + seg_len

    # ── Capacity early-exit ──
    seg_load = 0.0
    for k in range(seg_len):
        seg_load += demands[seg[k]]
    route_load = 0.0
    for k in range(rn):
        route_load += demands[route[k]]
    if seg_load + route_load > capacity:
        return 1e18, -1, 0

    old_cost = _route_cost(route, dist)

    best_delta = 1e18
    best_pos = -1
    best_rev = 0

    cand = np.empty(new_len, dtype=np.int64)
    seg_rev = np.empty(seg_len, dtype=np.int64)
    for k in range(seg_len):
        seg_rev[k] = seg[seg_len - 1 - k]

    for rev in range(2):  # 0 = forward, 1 = reversed
        s = seg if rev == 0 else seg_rev
        for pos in range(rn + 1):
            ci = 0
            for k in range(pos):
                cand[ci] = route[k]
                ci += 1
            for k in range(seg_len):
                cand[ci] = s[k]
                ci += 1
            for k in range(pos, rn):
                cand[ci] = route[k]
                ci += 1

            if not _route_ok(cand, demands, capacity, ready, due, service, dist):
                continue
            new_cost = _route_cost(cand, dist)
            delta = new_cost - old_cost
            if delta < best_delta:
                best_delta = delta
                best_pos = pos
                best_rev = rev

    if best_pos == -1:
        return 1e18, -1, 0
    return best_delta, best_pos, best_rev


# ──────────────────────────────────────────────────────────────────────
# 6.  Cross-exchange segment swap between two routes
# ──────────────────────────────────────────────────────────────────────


@njit(cache=True)
def _cross_exchange_pair_numba(
    r1: np.ndarray,
    r2: np.ndarray,
    max_len1: int,
    max_len2: int,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
    old_pair_cost: float,
):
    """
    Evaluate all segment-swap moves between *r1* and *r2*.

    For each combination of segment lengths and starting positions the
    two candidate routes are built, feasibility-checked, and the cost
    delta is computed.

    Returns ``(delta, p1, len1, p2, len2)`` for the best improving move,
    or ``(-1e-9, -1, -1, -1, -1)`` if none exists.
    """
    n1 = len(r1)
    n2 = len(r2)
    max_cand = n1 + n2  # upper bound on candidate length

    cand1 = np.empty(max_cand, dtype=np.int64)
    cand2 = np.empty(max_cand, dtype=np.int64)

    best_delta = -1e-9
    best_p1 = -1
    best_l1 = -1
    best_p2 = -1
    best_l2 = -1

    for len1 in range(1, max_len1 + 1):
        if n1 < len1:
            continue
        for len2 in range(1, max_len2 + 1):
            if n2 < len2:
                continue
            for p1 in range(n1 - len1 + 1):
                for p2 in range(n2 - len2 + 1):
                    # Build nr1 = r1[:p1] + r2[p2:p2+len2] + r1[p1+len1:]
                    cn1 = 0
                    for k in range(p1):
                        cand1[cn1] = r1[k]
                        cn1 += 1
                    for k in range(p2, p2 + len2):
                        cand1[cn1] = r2[k]
                        cn1 += 1
                    for k in range(p1 + len1, n1):
                        cand1[cn1] = r1[k]
                        cn1 += 1

                    # Build nr2 = r2[:p2] + r1[p1:p1+len1] + r2[p2+len2:]
                    cn2 = 0
                    for k in range(p2):
                        cand2[cn2] = r2[k]
                        cn2 += 1
                    for k in range(p1, p1 + len1):
                        cand2[cn2] = r1[k]
                        cn2 += 1
                    for k in range(p2 + len2, n2):
                        cand2[cn2] = r2[k]
                        cn2 += 1

                    # Skip empty routes
                    if cn1 == 0 or cn2 == 0:
                        continue

                    # Feasibility checks on the variable-length slices
                    c1_slice = cand1[:cn1]
                    c2_slice = cand2[:cn2]

                    if not _route_ok(c1_slice, demands, capacity, ready, due, service, dist):
                        continue
                    if not _route_ok(c2_slice, demands, capacity, ready, due, service, dist):
                        continue

                    new_cost = _route_cost(c1_slice, dist) + _route_cost(c2_slice, dist)
                    delta = new_cost - old_pair_cost
                    if delta < best_delta:
                        best_delta = delta
                        best_p1 = p1
                        best_l1 = len1
                        best_p2 = p2
                        best_l2 = len2

    return best_delta, best_p1, best_l1, best_p2, best_l2


# ──────────────────────────────────────────────────────────────────────
# 7.  Pruned kernels using GNN heatmaps
# ──────────────────────────────────────────────────────────────────────


@njit(cache=True)
def _swap_evaluate_pruned_numba(
    r1: np.ndarray,
    r2: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
    heatmap: np.ndarray,
    pruning_threshold: float,
):
    n1 = len(r1)
    n2 = len(r2)
    c1 = _route_cost(r1, dist)
    c2 = _route_cost(r2, dist)
    old_cost = c1 + c2

    best_delta = -1e-9
    best_sp = -1
    best_dp = -1

    t1 = r1.copy()
    t2 = r2.copy()

    for sp in range(n1):
        prev1 = r1[sp - 1] if sp > 0 else 0
        nxt1 = r1[sp + 1] if sp < n1 - 1 else 0
        u = r1[sp]

        for dp in range(n2):
            v = r2[dp]
            if u == v:
                continue

            prev2 = r2[dp - 1] if dp > 0 else 0
            nxt2 = r2[dp + 1] if dp < n2 - 1 else 0

            # GNN edge probability check
            if (
                heatmap[prev1, v] < pruning_threshold
                or heatmap[v, nxt1] < pruning_threshold
                or heatmap[prev2, u] < pruning_threshold
                or heatmap[u, nxt2] < pruning_threshold
            ):
                continue

            # Swap in-place
            t1[sp] = v
            t2[dp] = u

            if _route_ok(t1, demands, capacity, ready, due, service, dist) and _route_ok(
                t2, demands, capacity, ready, due, service, dist
            ):
                new_cost = _route_cost(t1, dist) + _route_cost(t2, dist)
                delta = new_cost - old_cost
                if delta < best_delta:
                    best_delta = delta
                    best_sp = sp
                    best_dp = dp

            # Undo swap
            t1[sp] = u
            t2[dp] = v

    return best_delta, best_sp, best_dp


@njit(cache=True)
def _best_segment_insert_pruned_numba(
    seg: np.ndarray,
    route: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
    heatmap: np.ndarray,
    pruning_threshold: float,
):
    seg_len = len(seg)
    rn = len(route)
    new_len = rn + seg_len

    # Capacity early-exit
    seg_load = 0.0
    for k in range(seg_len):
        seg_load += demands[seg[k]]
    route_load = 0.0
    for k in range(rn):
        route_load += demands[route[k]]
    if seg_load + route_load > capacity:
        return 1e18, -1, 0

    old_cost = _route_cost(route, dist)

    best_delta = 1e18
    best_pos = -1
    best_rev = 0

    cand = np.empty(new_len, dtype=np.int64)
    seg_rev = np.empty(seg_len, dtype=np.int64)
    for k in range(seg_len):
        seg_rev[k] = seg[seg_len - 1 - k]

    for rev in range(2):  # 0 = forward, 1 = reversed
        s = seg if rev == 0 else seg_rev
        for pos in range(rn + 1):
            prev = route[pos - 1] if pos > 0 else 0
            nxt = route[pos] if pos < rn else 0

            # GNN edge probability check
            if heatmap[prev, s[0]] < pruning_threshold or heatmap[s[-1], nxt] < pruning_threshold:
                continue

            ci = 0
            for k in range(pos):
                cand[ci] = route[k]
                ci += 1
            for k in range(seg_len):
                cand[ci] = s[k]
                ci += 1
            for k in range(pos, rn):
                cand[ci] = route[k]
                ci += 1

            if not _route_ok(cand, demands, capacity, ready, due, service, dist):
                continue
            new_cost = _route_cost(cand, dist)
            delta = new_cost - old_cost
            if delta < best_delta:
                best_delta = delta
                best_pos = pos
                best_rev = rev

    if best_pos == -1:
        return 1e18, -1, 0
    return best_delta, best_pos, best_rev


@njit(cache=True)
def _cross_exchange_pair_pruned_numba(
    r1: np.ndarray,
    r2: np.ndarray,
    max_len1: int,
    max_len2: int,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
    old_pair_cost: float,
    heatmap: np.ndarray,
    pruning_threshold: float,
):
    n1 = len(r1)
    n2 = len(r2)
    max_cand = n1 + n2

    cand1 = np.empty(max_cand, dtype=np.int64)
    cand2 = np.empty(max_cand, dtype=np.int64)

    best_delta = -1e-9
    best_p1 = -1
    best_l1 = -1
    best_p2 = -1
    best_l2 = -1

    for len1 in range(1, max_len1 + 1):
        if n1 < len1:
            continue
        for len2 in range(1, max_len2 + 1):
            if n2 < len2:
                continue
            for p1 in range(n1 - len1 + 1):
                prev1 = r1[p1 - 1] if p1 > 0 else 0
                nxt1 = r1[p1 + len1] if p1 + len1 < n1 else 0

                for p2 in range(n2 - len2 + 1):
                    prev2 = r2[p2 - 1] if p2 > 0 else 0
                    nxt2 = r2[p2 + len2] if p2 + len2 < n2 else 0

                    # GNN boundary edge checks
                    if (
                        heatmap[prev1, r2[p2]] < pruning_threshold
                        or heatmap[r2[p2 + len2 - 1], nxt1] < pruning_threshold
                        or heatmap[prev2, r1[p1]] < pruning_threshold
                        or heatmap[r1[p1 + len1 - 1], nxt2] < pruning_threshold
                    ):
                        continue

                    # Build nr1 = r1[:p1] + r2[p2:p2+len2] + r1[p1+len1:]
                    cn1 = 0
                    for k in range(p1):
                        cand1[cn1] = r1[k]
                        cn1 += 1
                    for k in range(p2, p2 + len2):
                        cand1[cn1] = r2[k]
                        cn1 += 1
                    for k in range(p1 + len1, n1):
                        cand1[cn1] = r1[k]
                        cn1 += 1

                    # Build nr2 = r2[:p2] + r1[p1:p1+len1] + r2[p2+len2:]
                    cn2 = 0
                    for k in range(p2):
                        cand2[cn2] = r2[k]
                        cn2 += 1
                    for k in range(p1, p1 + len1):
                        cand2[cn2] = r1[k]
                        cn2 += 1
                    for k in range(p2 + len2, n2):
                        cand2[cn2] = r2[k]
                        cn2 += 1

                    if cn1 == 0 or cn2 == 0:
                        continue

                    c1_slice = cand1[:cn1]
                    c2_slice = cand2[:cn2]

                    if not _route_ok(c1_slice, demands, capacity, ready, due, service, dist):
                        continue
                    if not _route_ok(c2_slice, demands, capacity, ready, due, service, dist):
                        continue

                    new_cost = _route_cost(c1_slice, dist) + _route_cost(c2_slice, dist)
                    delta = new_cost - old_pair_cost
                    if delta < best_delta:
                        best_delta = delta
                        best_p1 = p1
                        best_l1 = len1
                        best_p2 = p2
                        best_l2 = len2

    return best_delta, best_p1, best_l1, best_p2, best_l2
