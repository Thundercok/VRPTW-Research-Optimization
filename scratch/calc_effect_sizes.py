import os
import pandas as pd
import numpy as np
from scipy.stats import wilcoxon, norm

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

algo_counts = df.groupby("Instance")["Algorithm"].nunique()
valid_instances = algo_counts[algo_counts == 5].index.tolist()
df = df[df["Instance"].isin(valid_instances)]

# Separate into Solomon only vs Overall
solomon_instances = [inst for inst in valid_instances if not "_" in inst]
gh_instances = [inst for inst in valid_instances if "_" in inst]

print(f"Solomon instances: {len(solomon_instances)}")
print(f"GH instances: {len(gh_instances)}")
print(f"Overall instances: {len(valid_instances)}")
print()

def run_detailed_test(x, y, name_x, name_y, metric, subset_name):
    diff = x - y
    non_zero = diff[diff != 0]
    n_total = len(x)
    n_nonzero = len(non_zero)
    
    if n_nonzero == 0:
        print(f"[{subset_name}] {metric} {name_x} vs {name_y}: Identical (diff is all zeros)")
        return
        
    stat, p = wilcoxon(x, y)
    p_clamped = max(p, 1e-15)
    z = norm.ppf(1 - p_clamped / 2)
    
    # Effect size r = Z / sqrt(N)
    r_total = z / np.sqrt(n_total)
    
    print(f"[{subset_name}] {metric} {name_x} vs {name_y}:")
    print(f"  p-value     = {p:.4e}")
    print(f"  W-statistic = {stat:.1f}")
    print(f"  Z-score     = {z:.4f}")
    print(f"  Effect r (N={n_total})  = {r_total:.4f}")
    print()

for name, subset in [("Solomon (N=55)", solomon_instances), ("Overall (N=62)", valid_instances)]:
    nv_sub = df[df["Instance"].isin(subset)].pivot(index="Instance", columns="Algorithm", values="NV_mean")
    td_sub = df[df["Instance"].isin(subset)].pivot(index="Instance", columns="Algorithm", values="TD_mean")
    
    run_detailed_test(nv_sub["Hybrid-DDQN"], nv_sub["ALNS-Base"], "Hybrid-DDQN", "ALNS-Base", "NV", name)
    run_detailed_test(td_sub["Hybrid-DDQN"], td_sub["ALNS-Base"], "Hybrid-DDQN", "ALNS-Base", "TD", name)
    run_detailed_test(td_sub["Hybrid-DDQN"], td_sub["Hybrid-Rule"], "Hybrid-DDQN", "Hybrid-Rule", "TD", name)
    run_detailed_test(nv_sub["Hybrid-DDQN"], nv_sub["OR-Tools"], "Hybrid-DDQN", "OR-Tools", "NV", name)
    run_detailed_test(td_sub["Hybrid-DDQN"], td_sub["OR-Tools"], "Hybrid-DDQN", "OR-Tools", "TD", name)
    # Also run DDQN vs H-Fixed for TD
    run_detailed_test(td_sub["Hybrid-DDQN"], td_sub["Hybrid-Fixed"], "Hybrid-DDQN", "Hybrid-Fixed", "TD", name)
