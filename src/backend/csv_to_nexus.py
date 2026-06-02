""""
csv_to_nexus.py  —  v2
Run after each Kaggle/vast.ai session.

Usage:
    python csv_to_nexus.py \
        --main  logs/results-v17/benchmark_main_v17.csv \
        --dr    logs/results-v17/benchmark_dr_v17.csv \
        --out   logs/results-v17/nexus_demo.json \
        --version v17

Frontend contract (App.js buildSummaryPairMap):
    row.algo === 'ALNS'      → pair.alns
    row.algo === 'DDQN-ALNS' → pair.ddqn

CSV algo → nexus label:
    ALNS-Base               → "ALNS"
    Hybrid-DDQN             → "DDQN-ALNS"
    *Transfer*              → transfer[] array
    everything else         → summary[] (not paired, visible in scatter)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import UTC, datetime
from typing import Any

BKS: dict[str, dict[str, float]] = {
    "C101": {"nv": 10, "td": 828.94},
    "C102": {"nv": 10, "td": 828.94},
    "C103": {"nv": 10, "td": 828.06},
    "C104": {"nv": 10, "td": 824.78},
    "C105": {"nv": 10, "td": 828.94},
    "C106": {"nv": 10, "td": 828.94},
    "C107": {"nv": 10, "td": 828.94},
    "C108": {"nv": 10, "td": 828.94},
    "C109": {"nv": 10, "td": 828.94},
    "C201": {"nv": 3, "td": 591.56},
    "C202": {"nv": 3, "td": 591.56},
    "C203": {"nv": 3, "td": 591.17},
    "C204": {"nv": 3, "td": 590.6},
    "C205": {"nv": 3, "td": 588.88},
    "C206": {"nv": 3, "td": 588.49},
    "C207": {"nv": 3, "td": 588.29},
    "C208": {"nv": 3, "td": 588.32},
    "R101": {"nv": 19, "td": 1650.8},
    "R102": {"nv": 17, "td": 1486.12},
    "R103": {"nv": 13, "td": 1292.68},
    "R104": {"nv": 9, "td": 1007.31},
    "R105": {"nv": 14, "td": 1377.11},
    "R106": {"nv": 12, "td": 1252.03},
    "R107": {"nv": 10, "td": 1104.66},
    "R108": {"nv": 9, "td": 960.88},
    "R109": {"nv": 11, "td": 1194.73},
    "R110": {"nv": 10, "td": 1118.84},
    "R111": {"nv": 10, "td": 1096.72},
    "R112": {"nv": 9, "td": 982.14},
    "R201": {"nv": 4, "td": 1252.37},
    "R202": {"nv": 3, "td": 1191.7},
    "R203": {"nv": 3, "td": 939.5},
    "R204": {"nv": 2, "td": 825.52},
    "R205": {"nv": 3, "td": 994.43},
    "R206": {"nv": 3, "td": 906.14},
    "R207": {"nv": 2, "td": 890.61},
    "R208": {"nv": 2, "td": 726.82},
    "R209": {"nv": 3, "td": 909.16},
    "R210": {"nv": 3, "td": 939.37},
    "R211": {"nv": 2, "td": 885.71},
    "RC101": {"nv": 14, "td": 1696.94},
    "RC102": {"nv": 12, "td": 1554.75},
    "RC103": {"nv": 11, "td": 1261.67},
    "RC104": {"nv": 10, "td": 1135.48},
    "RC105": {"nv": 13, "td": 1629.44},
    "RC106": {"nv": 11, "td": 1424.73},
    "RC107": {"nv": 11, "td": 1230.48},
    "RC108": {"nv": 10, "td": 1139.82},
    "RC201": {"nv": 4, "td": 1406.94},
    "RC202": {"nv": 3, "td": 1365.65},
    "RC203": {"nv": 3, "td": 1049.62},
    "RC204": {"nv": 3, "td": 798.46},
    "RC205": {"nv": 4, "td": 1297.65},
    "RC206": {"nv": 3, "td": 1146.32},
    "RC207": {"nv": 3, "td": 1061.14},
    "RC208": {"nv": 3, "td": 828.14},
}


def _map_algo(csv_algo: str) -> tuple[str, bool]:
    a = csv_algo.strip()
    if a == "ALNS-Base":
        return "ALNS", False
    if a == "Hybrid-DDQN":
        return "DDQN-ALNS", False
    if "Transfer" in a or "transfer" in a:
        return a, True
    return a, False


def _f(v: str) -> float | None:
    try:
        x = float(v)
        return None if math.isnan(x) else round(x, 4)
    except (ValueError, TypeError):
        return None


def _raws(s: str) -> list[float]:
    try:
        return [float(x) for x in s.split(";") if x.strip()]
    except (ValueError, TypeError):
        return []


def _rawi(s: str) -> list[int]:
    try:
        return [int(x) for x in s.split(";") if x.strip()]
    except (ValueError, TypeError):
        return []


def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _summary_row(r: dict, label: str) -> dict[str, Any]:
    return {
        "algo": label,
        "instance": r["Instance"],
        "dataset": r["Dataset"],
        "gap_pct": _f(r.get("Gap%", "")),
        "time_s": _f(r.get("Time_s", "")),
        "td_cv": _f(r.get("TD_cv", "")),
        "nv": _f(r.get("NV_mean", "")),
        "nv_std": _f(r.get("NV_std", "")),
        "nv_diff": _f(r.get("NV_diff", "")),
        "td": _f(r.get("TD_mean", "")),
        "td_std": _f(r.get("TD_std", "")),
        "nv_cv": _f(r.get("NV_cv", "")),
        "on_time": _f(r.get("OnTime", "")),
        "nv_inflated": r.get("NV_inflated", "False").strip().lower() == "true",
        "raw_costs": _raws(r.get("raw_costs", "")),
        "raw_nv": _rawi(r.get("raw_nv", "")),
    }


def _transfer_row(r: dict) -> dict[str, Any]:
    return {
        "instance": r["Instance"],
        "dataset": r["Dataset"],
        "algo": r["Algorithm"],
        "gap_pct": _f(r.get("Gap%", "")),
        "nv": _f(r.get("NV_mean", "")),
        "td": _f(r.get("TD_mean", "")),
        "time_s": _f(r.get("Time_s", "")),
        "nv_diff": _f(r.get("NV_diff", "")),
        "nv_inflated": r.get("NV_inflated", "False").strip().lower() == "true",
    }


def build_nexus(rows: list[dict], version: str) -> dict[str, Any]:
    summary, transfer = [], []
    for r in rows:
        label, is_tr = _map_algo(r.get("Algorithm", ""))
        (transfer if is_tr else summary).append(_transfer_row(r) if is_tr else _summary_row(r, label))

    alns_instances = [r["instance"] for r in summary if r["algo"] == "ALNS"]
    meta_instance = "RC101" if "RC101" in alns_instances else (alns_instances[0] if alns_instances else "")
    datasets = sorted(set(r["dataset"] for r in summary))

    return {
        "version": version,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "transfer": transfer,
        # Empty convergence — frontend shows "No convergence data" gracefully
        "alns": {"history": []},
        "rl_alns": {"history": []},
        # Empty policy — frontend shows "No policy matrix" gracefully
        "op_matrix": [],
        "destroy_ops": ["Random", "Worst", "Shaw", "RoutePortion", "TWUrgent", "RouteElim", "ProxElim", "CrossShaw"],
        "repair_ops": ["Greedy", "Regret2", "Regret3", "TWGreedy", "FTSGreedy"],
        "meta": {
            "instance": meta_instance,
            "dataset": datasets[0] if datasets else "Unknown",
            "n_customers": 100,
            "capacity": 200,
            "horizon": 230,
            "version": version,
        },
        "bks": BKS,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--main", required=True)
    p.add_argument("--dr", default=None)
    p.add_argument("--out", required=True)
    p.add_argument("--version", default="v17")
    args = p.parse_args()

    rows = load_csv(args.main)
    print(f"Loaded {len(rows)} rows  ← {args.main}")
    if args.dr and os.path.exists(args.dr):
        dr = load_csv(args.dr)
        rows += dr
        print(f"Loaded {len(dr)} rows  ← {args.dr}")
    elif args.dr:
        print(f"[WARN] --dr not found: {args.dr}")

    nexus = build_nexus(rows, args.version)

    counts: dict[str, int] = {}
    for r in nexus["summary"]:
        counts[r["algo"]] = counts.get(r["algo"], 0) + 1
    paired = min(counts.get("ALNS", 0), counts.get("DDQN-ALNS", 0))
    print(f"\nSummary rows   : {len(nexus['summary'])}")
    print(f"Transfer rows  : {len(nexus['transfer'])}")
    print(f"Algo breakdown : {counts}")
    print(f"Paired instances (leaderboard): {paired}")

    if not counts.get("ALNS"):
        print("[WARN] No ALNS rows — leaderboard empty")
    if not counts.get("DDQN-ALNS"):
        print("[WARN] No DDQN-ALNS rows — leaderboard empty")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(nexus, fh, indent=2)
    print(f"\nWritten → {args.out}")


if __name__ == "__main__":
    main()
