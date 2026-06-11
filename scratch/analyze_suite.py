import os
import pandas as pd
import numpy as np
from scipy.stats import wilcoxon

# BKS table from config
BKS = {
    "C101": {"nv": 10, "td": 828.94}, "C102": {"nv": 10, "td": 828.94}, "C103": {"nv": 10, "td": 828.06},
    "C104": {"nv": 10, "td": 824.78}, "C105": {"nv": 10, "td": 828.94}, "C106": {"nv": 10, "td": 828.94},
    "C107": {"nv": 10, "td": 828.94}, "C108": {"nv": 10, "td": 828.94}, "C109": {"nv": 10, "td": 828.94},
    "C201": {"nv": 3, "td": 591.56}, "C202": {"nv": 3, "td": 591.56}, "C203": {"nv": 3, "td": 591.17},
    "C204": {"nv": 3, "td": 590.60}, "C205": {"nv": 3, "td": 588.88}, "C206": {"nv": 3, "td": 588.49},
    "C207": {"nv": 3, "td": 588.29}, "C208": {"nv": 3, "td": 588.32},
    "R101": {"nv": 19, "td": 1650.80}, "R102": {"nv": 17, "td": 1486.12}, "R103": {"nv": 13, "td": 1292.68},
    "R104": {"nv": 9, "td": 1007.31}, "R105": {"nv": 14, "td": 1377.11}, "R106": {"nv": 12, "td": 1252.03},
    "R107": {"nv": 10, "td": 1104.66}, "R108": {"nv": 9, "td": 960.88}, "R109": {"nv": 11, "td": 1194.73},
    "R110": {"nv": 10, "td": 1118.84}, "R111": {"nv": 10, "td": 1096.72}, "R112": {"nv": 9, "td": 982.14},
    "R201": {"nv": 4, "td": 1252.37}, "R202": {"nv": 3, "td": 1191.70}, "R203": {"nv": 3, "td": 939.50},
    "R204": {"nv": 2, "td": 825.52}, "R205": {"nv": 3, "td": 994.43}, "R206": {"nv": 3, "td": 906.14},
    "R207": {"nv": 2, "td": 890.61}, "R208": {"nv": 2, "td": 726.82}, "R209": {"nv": 3, "td": 909.16},
    "R210": {"nv": 3, "td": 939.37}, "R211": {"nv": 2, "td": 885.71},
    "RC101": {"nv": 14, "td": 1696.94}, "RC102": {"nv": 12, "td": 1554.75}, "RC103": {"nv": 11, "td": 1261.67},
    "RC104": {"nv": 10, "td": 1135.48}, "RC105": {"nv": 13, "td": 1629.44}, "RC106": {"nv": 11, "td": 1424.73},
    "RC107": {"nv": 11, "td": 1230.48}, "RC108": {"nv": 10, "td": 1139.82},
    "RC201": {"nv": 4, "td": 1406.94}, "RC202": {"nv": 3, "td": 1365.65}, "RC203": {"nv": 3, "td": 1049.62},
    "RC204": {"nv": 3, "td": 798.46}, "RC205": {"nv": 4, "td": 1297.65}, "RC206": {"nv": 3, "td": 1146.32},
    "RC207": {"nv": 3, "td": 1061.14}, "RC208": {"nv": 3, "td": 828.14},
    "c1_2_1": {"nv": 20, "td": 2704.57}, "c2_2_1": {"nv": 6, "td": 1931.44},
    "r1_2_1": {"nv": 20, "td": 4784.11}, "r2_2_1": {"nv": 4, "td": 4483.16},
    "rc1_2_1": {"nv": 18, "td": 3602.80}, "rc2_2_1": {"nv": 6, "td": 3099.53},
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
suite_dir = os.path.join(ROOT, "results", "ultimate-publication-suite")
shards = ["solomon_clustered", "solomon_short_horizon", "solomon_wide_horizon", "gehring_homberger_200"]

dfs = []
for shard in shards:
    filepath = os.path.join(suite_dir, shard, "benchmark_clean.csv")
    if os.path.exists(filepath):
        dfs.append(pd.read_csv(filepath))

df = pd.concat(dfs, ignore_index=True)
df["Algorithm"] = df["Algorithm"].str.strip()

# Check instances completed by all 5 algorithms
algo_counts = df.groupby("Instance")["Algorithm"].nunique()
valid_instances = algo_counts[algo_counts == 5].index.tolist()
print(f"Total instances completed by all 5 algorithms: {len(valid_instances)} / 62")

# Filter data to valid instances
df = df[df["Instance"].isin(valid_instances)]

# Pivot
nv_df = df.pivot(index="Instance", columns="Algorithm", values="NV_mean")
td_df = df.pivot(index="Instance", columns="Algorithm", values="TD_mean")
dataset_map = df.drop_duplicates("Instance").set_index("Instance")["Dataset"]

# Compute gaps to BKS
nv_gaps = {}
td_gaps = {}
for inst in valid_instances:
    if inst in BKS:
        nv_gaps[inst] = {algo: nv_df.loc[inst, algo] - BKS[inst]["nv"] for algo in nv_df.columns}
        td_gaps[inst] = {algo: (td_df.loc[inst, algo] - BKS[inst]["td"]) / BKS[inst]["td"] * 100 for algo in td_df.columns}

nv_gap_df = pd.DataFrame.from_dict(nv_gaps, orient='index')
td_gap_df = pd.DataFrame.from_dict(td_gaps, orient='index')

print("\n=== VEHICLE COUNT (NV) DIFF TO BKS BY GROUP ===")
groups = ["C1", "C2", "R1", "R2", "RC1", "RC2"]
for g in groups:
    insts_g = dataset_map[dataset_map == g].index
    print(f"\nGroup {g} (N={len(insts_g)}):")
    for algo in ["OR-Tools", "ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
        avg_nv_diff = nv_gap_df.loc[insts_g, algo].mean()
        print(f"  {algo:<15}: {avg_nv_diff:+.3f} vehicles")

print("\n=== TOTAL DISTANCE (TD) GAP TO BKS (%) BY GROUP ===")
for g in groups:
    insts_g = dataset_map[dataset_map == g].index
    print(f"\nGroup {g} (N={len(insts_g)}):")
    for algo in ["OR-Tools", "ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
        avg_td_gap = td_gap_df.loc[insts_g, algo].mean()
        print(f"  {algo:<15}: {avg_td_gap:+.3f}%")

print("\n=== WILCOXON SIGNED-RANK TESTS (N=62) ===")

def run_test(x, y, name_x, name_y, metric):
    try:
        diff = x - y
        if np.all(diff == 0):
            print(f"{metric} {name_x} vs {name_y}: Identical solutions (p-value N/A)")
            return
        stat, p = wilcoxon(x, y)
        print(f"{metric} {name_x} vs {name_y}: p-value = {p:.4e} (stat={stat:.1f})")
    except Exception as exc:
        print(f"{metric} {name_x} vs {name_y}: Error running test ({exc})")

# 1. Hybrid-DDQN vs ALNS-Base
run_test(nv_df["Hybrid-DDQN"], nv_df["ALNS-Base"], "Hybrid-DDQN", "ALNS-Base", "NV")
run_test(td_df["Hybrid-DDQN"], td_df["ALNS-Base"], "Hybrid-DDQN", "ALNS-Base", "TD")

# 2. Hybrid-DDQN vs Hybrid-Rule (Ablation: RL vs Rule)
run_test(nv_df["Hybrid-DDQN"], nv_df["Hybrid-Rule"], "Hybrid-DDQN", "Hybrid-Rule", "NV")
run_test(td_df["Hybrid-DDQN"], td_df["Hybrid-Rule"], "Hybrid-DDQN", "Hybrid-Rule", "TD")

# 3. Hybrid-DDQN vs OR-Tools (Vehicle count superiority)
run_test(nv_df["Hybrid-DDQN"], nv_df["OR-Tools"], "Hybrid-DDQN", "OR-Tools", "NV")
run_test(td_df["Hybrid-DDQN"], td_df["OR-Tools"], "Hybrid-DDQN", "OR-Tools", "TD")
