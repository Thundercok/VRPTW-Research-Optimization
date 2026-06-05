import pandas as pd
import numpy as np
from scipy.stats import wilcoxon

# Load the two result files
sol_df = pd.read_csv("results/overnight_run/solomon/benchmark_checkpoint.csv")
rc_df = pd.read_csv("results/overnight_run/solomon_rc/benchmark_clean.csv")

# Combine them
df = pd.concat([sol_df, rc_df], ignore_index=True)

# Standardize algorithm names just in case
df["Algorithm"] = df["Algorithm"].str.strip()

# Find instances with all 5 algorithms completed
algo_counts = df.groupby("Instance")["Algorithm"].nunique()
valid_instances = algo_counts[algo_counts == 5].index.tolist()
print(f"Total instances completed by all 5 algorithms: {len(valid_instances)} / 56")

# Filter data to valid instances
df = df[df["Instance"].isin(valid_instances)]

# Pivot to align algorithms side by side for each instance
nv_df = df.pivot(index="Instance", columns="Algorithm", values="NV_mean")
td_df = df.pivot(index="Instance", columns="Algorithm", values="TD_mean")
dataset_map = df.drop_duplicates("Instance").set_index("Instance")["Dataset"]

# Summary stats by dataset group
print("\n=== VEHICLE COUNT (NV) AVERAGES BY GROUP ===")
groups = ["C1", "C2", "R1", "R2", "RC1", "RC2"]
for g in groups:
    insts_g = dataset_map[dataset_map == g].index
    print(f"\nGroup {g} (N={len(insts_g)}):")
    for algo in ["OR-Tools", "ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
        avg_nv = nv_df.loc[insts_g, algo].mean()
        print(f"  {algo:<15}: {avg_nv:.2f}")

print("\n=== TOTAL DISTANCE (TD) AVERAGES BY GROUP ===")
for g in groups:
    insts_g = dataset_map[dataset_map == g].index
    print(f"\nGroup {g} (N={len(insts_g)}):")
    for algo in ["OR-Tools", "ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
        avg_td = td_df.loc[insts_g, algo].mean()
        print(f"  {algo:<15}: {avg_td:.2f}")

# Overall Wilcoxon Signed-Rank Tests across all 55 instances
print("\n=== WILCOXON SIGNED-RANK TESTS (N=55) ===")

def run_test(x, y, name_x, name_y, metric):
    try:
        # Wilcoxon requires differences to be non-zero to run, or handles them.
        # If all differences are zero, p-value is undefined.
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
