import os
import pandas as pd
from scipy.stats import wilcoxon

shards = [
    "results/clean_v3/solomon_clustered/benchmark_clean.csv",
    "results/clean_v3/solomon_short_horizon/benchmark_clean.csv",
    "results/clean_v3/solomon_wide_horizon/benchmark_clean.csv",
]

dfs = []
for p in shards:
    if os.path.exists(p):
        dfs.append(pd.read_csv(p))
        
if not dfs:
    print("No clean_v3 Solomon result files found!")
    exit(1)
    
df = pd.concat(dfs, ignore_index=True)

# Separate into ALNS-Base and Hybrid-DDQN
alns = df[df["Algorithm"] == "ALNS-Base"].sort_values("Instance")
ddqn = df[df["Algorithm"] == "Hybrid-DDQN"].sort_values("Instance")

# Merge on Instance to align
merged = pd.merge(alns, ddqn, on="Instance", suffixes=("_alns", "_ddqn"))

print(f"Total instances aligned: {len(merged)}")

# 1. Wilcoxon on NV_mean
nv_alns = merged["NV_mean_alns"].values
nv_ddqn = merged["NV_mean_ddqn"].values

print("\n--- Wilcoxon Signed-Rank Test: Vehicle Count (NV) ---")
print(f"ALNS-Base NV Mean: {nv_alns.mean():.4f}")
print(f"Hybrid-DDQN NV Mean: {nv_ddqn.mean():.4f}")
try:
    stat, pval = wilcoxon(nv_alns, nv_ddqn, alternative="greater")
    print(stat, pval)
    print(f"Wilcoxon p-value (greater, i.e., ALNS-Base > Hybrid-DDQN): {pval:.6g}")
except Exception as e:
    print("Failed to run Wilcoxon on NV:", e)

# 2. Wilcoxon on TD_mean
td_alns = merged["TD_mean_alns"].values
td_ddqn = merged["TD_mean_ddqn"].values

print("\n--- Wilcoxon Signed-Rank Test: Total Distance (TD) - Overall ---")
print(f"ALNS-Base TD Mean: {td_alns.mean():.4f}")
print(f"Hybrid-DDQN TD Mean: {td_ddqn.mean():.4f}")
try:
    stat, pval = wilcoxon(td_alns, td_ddqn, alternative="greater")
    print(f"Wilcoxon p-value (greater, i.e., ALNS-Base > Hybrid-DDQN): {pval:.6g}")
except Exception as e:
    print("Failed to run Wilcoxon on TD:", e)

# 3. Wilcoxon on TD_mean on matched NV subset
matched_nv_df = merged[merged["NV_mean_alns"] == merged["NV_mean_ddqn"]]
print(f"\nMatched NV Subset size: {len(matched_nv_df)} out of {len(merged)}")
if len(matched_nv_df) > 0:
    td_alns_m = matched_nv_df["TD_mean_alns"].values
    td_ddqn_m = matched_nv_df["TD_mean_ddqn"].values
    print(f"ALNS-Base TD Mean (Matched NV): {td_alns_m.mean():.4f}")
    print(f"Hybrid-DDQN TD Mean (Matched NV): {td_ddqn_m.mean():.4f}")
    try:
        stat, pval = wilcoxon(td_alns_m, td_ddqn_m, alternative="greater")
        print(f"Wilcoxon p-value (greater, i.e., ALNS-Base > Hybrid-DDQN): {pval:.6g}")
    except Exception as e:
        print("Failed to run Wilcoxon on Matched NV TD:", e)
else:
    print("No instances with matched NV.")
