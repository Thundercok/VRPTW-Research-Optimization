"""
solver_service.py
-----------------
ALNS side  : 3 destroy ops (random, worst, Shaw) + 2 repair ops
             (greedy, regret-2), adaptive weights, SA acceptance,
             Or-opt inter-route local search post-processing.
DDQN side  : nearest-neighbour + 2-opt (fast greedy baseline).

Operators mirror those in vrptw.py / the paper:
  _shaw_removal   → op_shaw
  _regret2_insert → op_regret_2
  _or_opt         → _best_relocate (single-customer inter-route)
"""
from __future__ import annotations
import math, random, time
from typing import Any
from models.schemas import JobRequest, Point
from services.distance_service import distance_km


def _build_dist(points, matrix):
    n = len(points)
    if matrix and len(matrix) == n and all(len(r) == n for r in matrix):
        return matrix
    return [
        [distance_km((points[i].lat, points[i].lng), (points[j].lat, points[j].lng))
         for j in range(n)]
        for i in range(n)
    ]


class _Sol:
    __slots__ = ("routes", "dist", "demands", "capacity", "_cost")

    def __init__(self, routes, dist, demands, capacity):
        self.routes = [r[:] for r in routes]
        self.dist, self.demands, self.capacity = dist, demands, capacity
        self._cost = None

    def cost(self):
        if self._cost is None:
            total = 0.0
            for r in self.routes:
                if not r: continue
                total += self.dist[0][r[0]]
                for k in range(len(r) - 1): total += self.dist[r[k]][r[k+1]]
                total += self.dist[r[-1]][0]
            self._cost = total
        return self._cost

    def copy(self):
        s = _Sol.__new__(_Sol)
        s.routes = [r[:] for r in self.routes]
        s.dist, s.demands, s.capacity, s._cost = self.dist, self.demands, self.capacity, self._cost
        return s

    def route_load(self, route):
        return sum(self.demands[c] for c in route)


# ── DDQN side ──────────────────────────────────────────────────────────────

def _nearest_neighbour(n, dist, demands, vehicles, capacity):
    unvisited = set(range(1, n))
    routes = []
    while unvisited and len(routes) < vehicles:
        route, load, cur = [], 0, 0
        while unvisited:
            best_c, best_d = None, float("inf")
            for c in unvisited:
                if load + demands[c] <= capacity and dist[cur][c] < best_d:
                    best_d, best_c = dist[cur][c], c
            if best_c is None: break
            route.append(best_c); load += demands[best_c]; unvisited.discard(best_c); cur = best_c
        if route: routes.append(route)
    for c in sorted(unvisited): routes.append([c])
    return routes


def _two_opt(route, dist):
    best, n = route[:], len(route)
    if n < 3: return best
    improved = True
    while improved:
        improved = False
        for i in range(n):
            for j in range(i + 2, n):
                pi = best[i-1] if i > 0 else 0
                nj = best[j+1] if j+1 < n else 0
                if dist[pi][best[j]] + dist[best[i]][nj] < dist[pi][best[i]] + dist[best[j]][nj] - 1e-9:
                    best[i:j+1] = best[i:j+1][::-1]; improved = True
    return best


# ── Destroy operators ──────────────────────────────────────────────────────

def _random_removal(sol, k, rng):
    all_c = [c for r in sol.routes for c in r]
    if not all_c: return [r[:] for r in sol.routes], []
    removed = rng.sample(all_c, min(k, len(all_c)))
    rs = set(removed)
    return [r for r in [[c for c in r if c not in rs] for r in sol.routes] if r], removed


def _worst_removal(sol, k):
    savings = []
    for route in sol.routes:
        for ci, c in enumerate(route):
            prev = route[ci-1] if ci > 0 else 0
            nxt  = route[ci+1] if ci+1 < len(route) else 0
            savings.append((sol.dist[prev][c] + sol.dist[c][nxt] - sol.dist[prev][nxt], c))
    savings.sort(reverse=True)
    removed = [c for _, c in savings[:k]]
    rs = set(removed)
    return [r for r in [[c for c in r if c not in rs] for r in sol.routes] if r], removed


def _shaw_removal(sol, k, rng):
    """Remove k customers most related to a random seed (distance + demand)."""
    all_c = [c for r in sol.routes for c in r]
    if not all_c: return [r[:] for r in sol.routes], []
    seed = rng.choice(all_c)
    removed, rs = [seed], {seed}
    max_dist = max(sol.dist[i][j] for i in range(len(sol.dist)) for j in range(len(sol.dist))) + 1e-9
    while len(removed) < min(k, len(all_c)):
        best_c, best_score = None, float("inf")
        for c in all_c:
            if c in rs: continue
            score = (0.6 * sol.dist[seed][c] / max_dist +
                     0.4 * abs(sol.demands[seed] - sol.demands[c]) / max(sol.capacity, 1))
            if score < best_score: best_score, best_c = score, c
        if best_c is None: break
        removed.append(best_c); rs.add(best_c)
    return [r for r in [[c for c in r if c not in rs] for r in sol.routes] if r], removed


# ── Repair operators ───────────────────────────────────────────────────────

def _best_insert(c, route, dist):
    best_d, best_p = float("inf"), None
    chain = [0] + route + [0]
    for pos in range(len(route) + 1):
        d = dist[chain[pos]][c] + dist[c][chain[pos+1]] - dist[chain[pos]][chain[pos+1]]
        if d < best_d: best_d, best_p = d, pos
    return best_d, best_p


def _greedy_insert(routes, removed, dist, demands, capacity, vehicles):
    routes = [r[:] for r in routes]
    for c in removed:
        best_d, best_ri, best_p = float("inf"), -1, -1
        for ri, route in enumerate(routes):
            if sum(demands[x] for x in route) + demands[c] > capacity: continue
            d, p = _best_insert(c, route, dist)
            if p is not None and d < best_d: best_d, best_ri, best_p = d, ri, p
        if best_ri >= 0: routes[best_ri].insert(best_p, c)
        elif len(routes) < vehicles: routes.append([c])
        else:
            least = min(range(len(routes)), key=lambda i: sum(demands[x] for x in routes[i]))
            routes[least].append(c)
    return routes


def _regret2_insert(routes, removed, dist, demands, capacity, vehicles):
    """
    Regret-2 insertion — insert the customer whose 2nd-best position is
    most costly relative to its best position first.
    Mirrors op_regret_2 in vrptw.py.
    """
    routes, remaining = [r[:] for r in routes], list(removed)
    while remaining:
        best_regret, chosen_c, chosen_ri, chosen_p = -float("inf"), None, None, None
        for c in remaining:
            opts = sorted(
                (d, ri, p)
                for ri, route in enumerate(routes)
                if sum(demands[x] for x in route) + demands[c] <= capacity
                for d, p in [_best_insert(c, route, dist)]
                if p is not None
            )
            if not opts:
                regret, ri_b, p_b = float("inf"), None, None
            elif len(opts) == 1:
                regret, ri_b, p_b = float("inf"), opts[0][1], opts[0][2]
            else:
                regret, ri_b, p_b = opts[1][0] - opts[0][0], opts[0][1], opts[0][2]
            if regret > best_regret:
                best_regret, chosen_c, chosen_ri, chosen_p = regret, c, ri_b, p_b
        if chosen_c is None: break
        remaining.remove(chosen_c)
        if chosen_ri is not None: routes[chosen_ri].insert(chosen_p, chosen_c)
        elif len(routes) < vehicles: routes.append([chosen_c])
        else:
            least = min(range(len(routes)), key=lambda i: sum(demands[x] for x in routes[i]))
            routes[least].append(chosen_c)
    return routes


# ── Or-opt local search ────────────────────────────────────────────────────

def _or_opt(sol: _Sol, max_moves: int = 10) -> _Sol:
    """Inter-route single-customer relocation. Mirrors _best_relocate in vrptw.py."""
    best, moves = sol.copy(), 0
    while moves < max_moves:
        found = False
        for si, src in enumerate(best.routes):
            if not src: continue
            for sp, c in enumerate(src):
                prev = src[sp-1] if sp > 0 else 0
                nxt  = src[sp+1] if sp+1 < len(src) else 0
                saving = best.dist[prev][c] + best.dist[c][nxt] - best.dist[prev][nxt]
                for di, dst in enumerate(best.routes):
                    if di == si: continue
                    if best.route_load(dst) + best.demands[c] > best.capacity: continue
                    ins_d, ins_p = _best_insert(c, dst, best.dist)
                    if ins_p is None: continue
                    if saving - ins_d > 1e-9:
                        nr = [r[:] for r in best.routes]
                        nr[si] = src[:sp] + src[sp+1:]
                        nr[di] = dst[:ins_p] + [c] + dst[ins_p:]
                        nr = [r for r in nr if r]
                        best = _Sol(nr, best.dist, best.demands, best.capacity)
                        moves += 1; found = True; break
                if found: break
            if found: break
        if not found: break
    return best


# ── ALNS core ──────────────────────────────────────────────────────────────

def _alns(initial, dist, demands, capacity, vehicles, iterations, seed=42):
    rng  = random.Random(seed)
    sol  = _Sol(initial, dist, demands, capacity)
    best = sol.copy()
    temp, cooling = max(sol.cost() * 0.02, 1.0), 0.997
    dw = [1.0, 1.0, 1.0]   # random, worst, shaw
    rw = [1.0, 1.0]         # greedy, regret-2
    REWARD, PENALTY = 1.15, 0.97
    n_c = sum(len(r) for r in sol.routes)

    for _ in range(iterations):
        k = max(1, int(n_c * rng.uniform(0.10, 0.30)))

        dw_t = sum(dw); dr = rng.random() * dw_t; cum = 0.0; d_idx = 0
        for idx, w in enumerate(dw):
            cum += w
            if dr <= cum: d_idx = idx; break

        if d_idx == 0:   nr, removed = _random_removal(sol, k, rng)
        elif d_idx == 1: nr, removed = _worst_removal(sol, k)
        else:            nr, removed = _shaw_removal(sol, k, rng)

        r_idx = 0 if rng.random() * sum(rw) <= rw[0] else 1
        repaired = (_greedy_insert if r_idx == 0 else _regret2_insert)(
            nr, removed, dist, demands, capacity, vehicles)

        cand  = _Sol(repaired, dist, demands, capacity)
        delta = cand.cost() - sol.cost()
        if delta < 0 or rng.random() < math.exp(-delta / max(temp, 1e-9)):
            sol = cand
            if sol.cost() < best.cost():
                best = sol.copy()
                dw[d_idx] = min(5.0, dw[d_idx] * REWARD)
                rw[r_idx] = min(5.0, rw[r_idx] * REWARD)
            else:
                dw[d_idx] = max(0.2, dw[d_idx] * PENALTY)
                rw[r_idx] = max(0.2, rw[r_idx] * PENALTY)
        temp *= cooling

    return _or_opt(best, max_moves=10)


# ── Output formatter ───────────────────────────────────────────────────────

def _to_output(sol, points, runtime):
    routes_out, total_dist = [], 0.0
    for i, route in enumerate(sol.routes):
        if not route: continue
        chain = [0] + route + [0]
        path  = [[points[idx].lat, points[idx].lng] for idx in chain]
        dist  = sum(sol.dist[chain[k]][chain[k+1]] for k in range(len(chain)-1))
        total_dist += dist
        routes_out.append({
            "vehicle_id":  i + 1,
            "distance_km": round(dist, 4),
            "load":        sol.route_load(route),
            "path":        path,
            "stops":       [points[c].id for c in route],
        })
    return {
        "runtime_sec":       round(runtime, 4),
        "total_distance_km": round(total_dist, 4),
        "vehicles_used":     len(routes_out),
        "routes":            routes_out,
    }


# ── Public entry point ─────────────────────────────────────────────────────

async def solve_model(
    payload: JobRequest,
    distance_matrix: list[list[float]] | None = None,
) -> dict[str, Any]:
    points   = payload.customers
    if len(points) < 2:
        raise ValueError("Need depot and at least one customer")

    vehicles, capacity, n = payload.fleet.vehicles, payload.fleet.capacity, len(points)
    dist    = _build_dist(points, distance_matrix)
    demands = [p.demand for p in points]

    for p in points[1:]:
        if p.demand < 0:
            raise ValueError(f"Negative demand on id={p.id}")
        if p.demand > capacity:
            raise ValueError(f"Demand {p.demand} > capacity {capacity} (id={p.id})")

    # DDQN: NN + 2-opt
    t0 = time.perf_counter()
    nn = _nearest_neighbour(n, dist, demands, vehicles, capacity)
    nn = [_two_opt(r, dist) for r in nn]
    if len(nn) > vehicles:
        raise ValueError(f"Infeasible: need {len(nn)} vehicles, only {vehicles} available.")
    ddqn_sol, ddqn_time = _Sol(nn, dist, demands, capacity), time.perf_counter() - t0

    # ALNS: Shaw + Regret-2 + Or-opt
    t1 = time.perf_counter()
    alns_sol  = _alns([r[:] for r in nn], dist, demands, capacity, vehicles,
                      iterations=min(600, max(200, n * 10)))
    alns_time = time.perf_counter() - t1

    return {
        "ddqn": _to_output(ddqn_sol, points, ddqn_time),
        "alns": _to_output(alns_sol, points, alns_time),
    }