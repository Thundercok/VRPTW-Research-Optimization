from __future__ import annotations

import numpy as np

from .core import Inst, Plan, _check_route
from .heuristics import _best_insert_position, _route_cost_list, _route_load


def _two_opt_best(route: list[int], inst: Inst) -> list[int]:
    if len(route) < 4:
        return route[:]
    best, best_cost = route[:], _route_cost_list(route, inst)
    for i in range(len(route) - 2):
        for j in range(i + 2, len(route)):
            cand = route[:i] + list(reversed(route[i : j + 1])) + route[j + 1 :]
            if not _check_route(cand, inst):
                continue
            cc = _route_cost_list(cand, inst)
            if cc + 1e-9 < best_cost:
                best, best_cost = cand, cc
    return best


def _best_relocate(plan: Plan, nv_ceiling: int | None = None):
    inst = plan.inst
    best_delta, best_move = -1e-9, None
    for si, source_route in enumerate(plan.routes):
        sc = _route_cost_list(source_route, inst)
        for sp, node in enumerate(source_route):
            sn = source_route[:sp] + source_route[sp + 1 :]
            if sn and not _check_route(sn, inst):
                continue
            snc = _route_cost_list(sn, inst)
            for di, dest_route in enumerate(plan.routes):
                if di == si:
                    continue
                dc = _route_cost_list(dest_route, inst)
                for ip in range(len(dest_route) + 1):
                    dn = dest_route[:ip] + [node] + dest_route[ip:]
                    if not _check_route(dn, inst):
                        continue
                    new_nv = plan.nv - (1 if not sn else 0)
                    if nv_ceiling is not None and new_nv > nv_ceiling:
                        continue
                    delta = snc + _route_cost_list(dn, inst) - sc - dc
                    if new_nv < plan.nv:
                        delta -= 1000.0
                    if delta < best_delta:
                        best_delta, best_move = delta, (si, sp, di, ip)
    return best_move


def _apply_relocate(plan: Plan, move: tuple[int, int, int, int]) -> Plan:
    si, sp, di, ip = move
    routes = [r[:] for r in plan.routes]
    node = routes[si].pop(sp)
    if si < di and len(routes[si]) == 0:
        di -= 1
    routes = [r for r in routes if r]
    routes[di].insert(ip, node)
    return Plan(routes, plan.inst, plan.algo)


def _best_swap(plan: Plan):
    inst = plan.inst
    best_delta, best_move = -1e-9, None
    for si, sr in enumerate(plan.routes):
        sc = _route_cost_list(sr, inst)
        for di in range(si + 1, len(plan.routes)):
            dr = plan.routes[di]
            dc = _route_cost_list(dr, inst)
            for sp, sn in enumerate(sr):
                for dp, dn in enumerate(dr):
                    if sn == dn:
                        continue
                    srn, drn = sr[:], dr[:]
                    srn[sp], drn[dp] = dn, sn
                    if not _check_route(srn, inst) or not _check_route(drn, inst):
                        continue
                    delta = _route_cost_list(srn, inst) + _route_cost_list(drn, inst) - sc - dc
                    if delta < best_delta:
                        best_delta, best_move = delta, (si, sp, di, dp)
    return best_move


def _apply_swap(plan: Plan, move: tuple[int, int, int, int]) -> Plan:
    si, sp, di, dp = move
    routes = [r[:] for r in plan.routes]
    routes[si][sp], routes[di][dp] = routes[di][dp], routes[si][sp]
    return Plan(routes, plan.inst, plan.algo)


def _cross_exchange(plan: Plan, nv_ceiling: int | None = None) -> Plan | None:
    inst = plan.inst
    if nv_ceiling is not None and plan.nv > nv_ceiling:
        return None
    max_dist = max(inst.max_dist, 1.0)
    granular_radius = max(10.0, 0.18 * max_dist)
    best_delta = -1e-9
    best_routes: list[list[int]] | None = None

    def interval_overlap(a0, a1, b0, b1):
        return min(a1, b1) >= max(a0, b0)

    def route_meta(route):
        coords = inst.coords[np.array(route, dtype=np.int64)]
        return (coords.mean(axis=0), float(np.min(inst.ready_times[route])), float(np.max(inst.due_times[route])))

    def seg_meta(seg):
        coords = inst.coords[np.array(seg, dtype=np.int64)]
        return (coords.mean(axis=0), float(np.min(inst.ready_times[seg])), float(np.max(inst.due_times[seg])))

    route_info = [route_meta(r) if r else None for r in plan.routes]

    for i in range(len(plan.routes)):
        for j in range(i + 1, len(plan.routes)):
            r1, r2 = plan.routes[i], plan.routes[j]
            if not r1 or not r2:
                continue
            info1, info2 = route_info[i], route_info[j]
            if info1 is None or info2 is None:
                continue
            c1, r1_ready, r1_due = info1
            c2, r2_ready, r2_due = info2
            if float(np.linalg.norm(c1 - c2)) > 0.55 * max_dist and not interval_overlap(
                r1_ready, r1_due, r2_ready, r2_due
            ):
                continue
            old_pair = _route_cost_list(r1, inst) + _route_cost_list(r2, inst)
            lc1 = (1, 2, 3) if len(r1) >= 12 else (1, 2)
            lc2 = (1, 2, 3) if len(r2) >= 12 else (1, 2)
            for len1 in lc1:
                if len(r1) < len1:
                    continue
                for len2 in lc2:
                    if len(r2) < len2:
                        continue
                    for p1 in range(len(r1) - len1 + 1):
                        seg1 = r1[p1 : p1 + len1]
                        s1c, s1r, s1d = seg_meta(seg1)
                        for p2 in range(len(r2) - len2 + 1):
                            seg2 = r2[p2 : p2 + len2]
                            s2c, s2r, s2d = seg_meta(seg2)
                            if float(np.linalg.norm(s1c - s2c)) > granular_radius and not interval_overlap(
                                s1r, s1d, s2r, s2d
                            ):
                                continue
                            nr1 = r1[:p1] + seg2 + r1[p1 + len1 :]
                            nr2 = r2[:p2] + seg1 + r2[p2 + len2 :]
                            if not _check_route(nr1, inst) or not _check_route(nr2, inst):
                                continue
                            delta = _route_cost_list(nr1, inst) + _route_cost_list(nr2, inst) - old_pair
                            if delta < best_delta:
                                routes = [r[:] for r in plan.routes]
                                routes[i], routes[j] = nr1, nr2
                                best_routes = routes
                                best_delta = delta
    return Plan(best_routes, inst, plan.algo) if best_routes is not None else None


def _try_route_compact(plan: Plan, nv_ceiling: int | None = None) -> Plan | None:
    if len(plan.routes) <= 1:
        return None
    inst = plan.inst
    ranked = sorted(
        range(len(plan.routes)),
        key=lambda i: (len(plan.routes[i]), _route_load(plan.routes[i], inst), _route_cost_list(plan.routes[i], inst)),
    )
    for ridx in ranked:
        source = plan.routes[ridx]
        others = [r[:] for i, r in enumerate(plan.routes) if i != ridx]
        ok = True
        for node in sorted(source, key=lambda n: (inst.due_times[n] - inst.ready_times[n], -inst.demands[n])):
            best_c, best_r, best_p = float("inf"), None, None
            for oi, route in enumerate(others):
                delta, pos = _best_insert_position(node, route, inst)
                if pos is not None and delta < best_c:
                    best_c, best_r, best_p = delta, oi, pos
            if best_r is None:
                ok = False
                break
            others[best_r].insert(best_p, node)
        if not ok:
            continue
        cand = Plan([r for r in others if r], inst, plan.algo)
        if not cand.feasible:
            continue
        if nv_ceiling is not None and cand.nv > nv_ceiling:
            continue
        if cand.dominates(plan) or (cand.nv == plan.nv and cand.cost + 1e-9 < plan.cost):
            return cand
    return None


def _best_or_opt(plan: Plan, nv_ceiling: int | None = None):
    inst = plan.inst
    best_delta, best_move = -1e-9, None
    for si, source_route in enumerate(plan.routes):
        sc = _route_cost_list(source_route, inst)
        for L in (2, 3):
            for sp in range(len(source_route) - L + 1):
                seg = source_route[sp : sp + L]
                sn = source_route[:sp] + source_route[sp + L :]
                if sn and not _check_route(sn, inst):
                    continue
                snc = _route_cost_list(sn, inst) if sn else 0.0
                for di, dest_route in enumerate(plan.routes):
                    if di == si:
                        continue
                    dc = _route_cost_list(dest_route, inst)
                    for ip in range(len(dest_route) + 1):
                        # Try original segment order
                        dn = dest_route[:ip] + seg + dest_route[ip:]
                        if _check_route(dn, inst):
                            new_nv = plan.nv - (1 if not sn else 0)
                            if nv_ceiling is None or new_nv <= nv_ceiling:
                                delta = snc + _route_cost_list(dn, inst) - sc - dc
                                if new_nv < plan.nv:
                                    delta -= 1000.0
                                if delta < best_delta:
                                    best_delta, best_move = delta, (si, sp, L, di, ip, False)

                        # Try reversed segment order
                        dn_rev = dest_route[:ip] + list(reversed(seg)) + dest_route[ip:]
                        if _check_route(dn_rev, inst):
                            new_nv = plan.nv - (1 if not sn else 0)
                            if nv_ceiling is None or new_nv <= nv_ceiling:
                                delta = snc + _route_cost_list(dn_rev, inst) - sc - dc
                                if new_nv < plan.nv:
                                    delta -= 1000.0
                                if delta < best_delta:
                                    best_delta, best_move = delta, (si, sp, L, di, ip, True)
    return best_move


def _apply_or_opt(plan: Plan, move: tuple[int, int, int, int, int, bool]) -> Plan:
    si, sp, L, di, ip, is_reversed = move
    routes = [r[:] for r in plan.routes]
    seg = routes[si][sp : sp + L]
    del routes[si][sp : sp + L]
    if si < di and len(routes[si]) == 0:
        di -= 1
    routes = [r for r in routes if r]
    if is_reversed:
        seg = list(reversed(seg))
    routes[di] = routes[di][:ip] + seg + routes[di][ip:]
    return Plan(routes, plan.inst, plan.algo)


def _try_route_merge(plan: Plan) -> Plan | None:
    """
    Route Consolidation Move.

    Attempts to merge any two capacity-compatible routes into a single feasible
    route via EDF-ordered best-insertion. Unlike _try_route_compact (which
    scatters customers across many routes), this produces ONE longer route —
    exactly the route type MILP needs to assemble an NV-1 partition.

    Checks at most the 4 shortest routes for O(k * n^2) tractability.
    Returns the best merged plan (nv-1), or None if no merge is feasible.
    """
    inst = plan.inst
    if len(plan.routes) <= 1:
        return None

    ranked = sorted(range(len(plan.routes)), key=lambda i: len(plan.routes[i]))
    check_idxs = ranked[: min(4, len(ranked))]
    best_merged: Plan | None = None

    for pos_i, i in enumerate(check_idxs):
        r1 = plan.routes[i]
        load1 = sum(inst.demands[n] for n in r1)
        for j in check_idxs[pos_i + 1 :]:
            r2 = plan.routes[j]
            if load1 + sum(inst.demands[n] for n in r2) > inst.capacity:
                continue  # capacity gate

            # EDF ordering minimises downstream TW violations
            combined = sorted(list(r1) + list(r2), key=lambda n: inst.due_times[n])
            merged_route: list[int] = []
            ok = True
            for node in combined:
                _, pos = _best_insert_position(node, merged_route, inst)
                if pos is None:
                    ok = False
                    break
                merged_route.insert(pos, node)
            if not ok or not _check_route(merged_route, inst):
                continue

            surviving = [r[:] for k, r in enumerate(plan.routes) if k != i and k != j]
            surviving.append(merged_route)
            cand = Plan(surviving, inst, plan.algo)
            if not cand.feasible:
                continue
            if best_merged is None or cand.dominates(best_merged) or cand.nv < best_merged.nv:
                best_merged = cand

    return best_merged


def local_search(
    plan: Plan,
    max_passes: int = 1,
    nv_ceiling: int | None = None,
    max_ls_moves: int = 5,
    pool=None,  # RoutePool | None — seeds pool with every improvement
) -> Plan:
    """
    pool: when provided, each improvement along the LS trajectory is added to
          the route pool, generating diverse intermediate routes for MILP.
          Also triggers _try_route_merge at the end to seed merged-route types.
    """
    best = plan.copy()
    for _ in range(max_passes):
        improved = False
        routes = []
        for route in best.routes:
            nr = _two_opt_best(route, best.inst)
            routes.append(nr)
            if nr != route:
                improved = True
        best = Plan(routes, best.inst, best.algo)

        moves = 0
        while moves < max_ls_moves:
            move = _best_relocate(best, nv_ceiling=nv_ceiling)
            if move is not None:
                cand = _apply_relocate(best, move)
                if cand.feasible and (cand.dominates(best) or (cand.nv == best.nv and cand.cost + 1e-9 < best.cost)):
                    best, improved = cand, True
                    if pool is not None:
                        pool.add_plan(best)
                    moves += 1
                    continue
            move = _best_swap(best)
            if move is not None:
                cand = _apply_swap(best, move)
                if cand.feasible and cand.cost + 1e-9 < best.cost:
                    best, improved = cand, True
                    if pool is not None:
                        pool.add_plan(best)
                    moves += 1
                    continue
            move = _best_or_opt(best, nv_ceiling=nv_ceiling)
            if move is not None:
                cand = _apply_or_opt(best, move)
                if cand.feasible and (cand.dominates(best) or (cand.nv == best.nv and cand.cost + 1e-9 < best.cost)):
                    best, improved = cand, True
                    if pool is not None:
                        pool.add_plan(best)
                    moves += 1
                    continue
            cross = _cross_exchange(best, nv_ceiling=nv_ceiling)
            if cross is not None:
                best, improved = cross, True
                if pool is not None:
                    pool.add_plan(best)
                moves += 1
                continue
            compact = _try_route_compact(best, nv_ceiling=nv_ceiling)
            if compact is not None:
                best, improved = compact, True
                if pool is not None:
                    pool.add_plan(best)
                moves += 1
                continue
            break

        if not improved:
            break

    # Pool-seeding bonus: generate merged-route type not produced by normal LS
    if pool is not None:
        merged = _try_route_merge(best)
        if merged is not None:
            pool.add_plan(merged)

    return best


def _try_chain_elimination(plan: Plan, target_idx: int) -> Plan | None:
    """
    Single-target ejection chain.  Processes each customer in the target route;
    for customers that fail direct insertion, attempts a depth-2 chain:
      c → Ri  (displacing d from Ri)  →  d → Rj
    Returns a feasible Plan with nv-1, or None if any customer is unplaceable.
    """
    inst = plan.inst
    target = plan.routes[target_idx]
    routes = [r[:] for i, r in enumerate(plan.routes) if i != target_idx]

    # Tightest TW first — hardest-to-place customers block everything downstream
    for c in sorted(target, key=lambda n: inst.due_times[n] - inst.ready_times[n]):
        # --- Level 1: direct best-insertion ---
        best_delta, best_ri, best_pos = float("inf"), None, None
        for ri, route in enumerate(routes):
            delta, pos = _best_insert_position(c, route, inst)
            if pos is not None and delta < best_delta:
                best_delta, best_ri, best_pos = delta, ri, pos

        if best_ri is not None:
            routes[best_ri].insert(best_pos, c)
            continue

        # --- Level 2: ejection chain  (c ejects d from Ri, d moves to Rj) ---
        best_chain_cost = float("inf")
        best_chain: tuple | None = None  # (ri, eject_pos, d, rj)

        for ri, route in enumerate(routes):
            for eject_pos, d in enumerate(route):
                # Temporary route with d removed
                stripped = route[:eject_pos] + route[eject_pos + 1 :]
                delta_c, pos_c = _best_insert_position(c, stripped, inst)
                if pos_c is None:
                    continue
                # Check if d can land anywhere else
                for rj, other in enumerate(routes):
                    if rj == ri:
                        continue
                    delta_d, pos_d = _best_insert_position(d, other, inst)
                    if pos_d is not None:
                        total = delta_c + delta_d
                        if total < best_chain_cost:
                            best_chain_cost = total
                            best_chain = (ri, eject_pos, d, rj)

        if best_chain is None:
            return None  # c unplaceable even with chain

        ri, eject_pos, d, rj = best_chain
        # Apply: remove d, insert c into Ri, insert d into Rj
        stripped_ri = routes[ri][:eject_pos] + routes[ri][eject_pos + 1 :]
        _, pos_c = _best_insert_position(c, stripped_ri, inst)
        if pos_c is None:
            return None
        routes[ri] = stripped_ri[:pos_c] + [c] + stripped_ri[pos_c:]

        _, pos_d = _best_insert_position(d, routes[rj], inst)
        if pos_d is None:
            return None
        routes[rj].insert(pos_d, d)

    cand = Plan([r for r in routes if r], inst, plan.algo)
    return cand if cand.feasible else None


def _ejection_chain_eliminate(plan: Plan) -> Plan | None:
    """
    Tries to eliminate up to the 4 smallest routes via depth-2 ejection chains.
    Complements _iterative_route_elimination: handles cases where greedy
    insertion fails due to TW blocking but a 2-step chain resolves the conflict.

    Complexity: O(k × n_target × n_routes × route_len × n_routes) per call —
    fast enough for post-search use on 100-customer instances.
    Returns first feasible NV-1 plan found, or None.
    """
    if len(plan.routes) <= 1:
        return None

    ranked = sorted(
        range(len(plan.routes)),
        key=lambda i: (len(plan.routes[i]), sum(plan.inst.demands[n] for n in plan.routes[i])),
    )
    for target_idx in ranked[:4]:
        result = _try_chain_elimination(plan, target_idx)
        if result is not None:
            return result
    return None


def _iterative_route_elimination(
    plan: Plan,
    inst: Inst,
    max_rounds: int = 6,
    pool=None,  # RoutePool | None — seeds pool after each success
) -> Plan:
    best = plan.copy()
    for _ in range(max_rounds):
        if len(best.routes) <= 1:
            break
        sorted_idxs = sorted(
            range(len(best.routes)),
            key=lambda i: (
                len(best.routes[i]),
                _route_load(best.routes[i], inst),
                _route_cost_list(best.routes[i], inst),
            ),
        )
        eliminated = False
        for target_idx in sorted_idxs[:5]:
            target = best.routes[target_idx]
            others = [r[:] for i, r in enumerate(best.routes) if i != target_idx]
            ok = True
            for node in sorted(target, key=lambda n: inst.due_times[n] - inst.ready_times[n]):
                best_d, best_r, best_p = float("inf"), None, None
                for oi, route in enumerate(others):
                    delta, pos = _best_insert_position(node, route, inst)
                    if pos is not None and delta < best_d:
                        best_d, best_r, best_p = delta, oi, pos
                if best_r is None:
                    ok = False
                    break
                others[best_r].insert(best_p, node)
            if not ok:
                continue
            cand = Plan([r for r in others if r], inst, best.algo)
            if not cand.feasible:
                continue
            cand = local_search(cand, max_passes=2, nv_ceiling=cand.nv, pool=pool)
            if cand.feasible:
                if pool is not None:
                    pool.add_plan(cand)
                best = cand
                eliminated = True
                break
        if not eliminated:
            break
    return best
