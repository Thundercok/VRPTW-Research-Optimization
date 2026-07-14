import pandas as pd
import numpy as np

# Load Solomon wide horizon results
df = pd.read_csv("results/clean_v3/solomon_wide_horizon/benchmark_clean.csv")

# Filter for RC2 instances
rc2 = df[df["Instance"].str.startswith("RC2")]

# Pivot to compare ALNS-Base and Hybrid-DDQN side-by-side
pivot_nv = rc2.pivot(index="Instance", columns="Algorithm", values="NV_mean")
pivot_td = rc2.pivot(index="Instance", columns="Algorithm", values="TD_mean")

print("=== Solomon RC2: NV comparison ===")
print(pivot_nv)
print("\n=== Solomon RC2: TD comparison ===")
print(pivot_td)

# Filter for instances where NV matches exactly between ALNS-Base and Hybrid-DDQN
matched_instances = []
for inst in pivot_nv.index:
    nv_alns = pivot_nv.loc[inst, "ALNS-Base"]
    nv_hybrid = pivot_nv.loc[inst, "Hybrid-DDQN"]
    if nv_alns == nv_hybrid:
        matched_instances.append(inst)

print(f"\nMatched instances (exact NV match): {matched_instances}")

# Calculate averages over matched instances
alns_matched_td = pivot_td.loc[matched_instances, "ALNS-Base"].mean()
hybrid_matched_td = pivot_td.loc[matched_instances, "Hybrid-DDQN"].mean()
diff_percent = (hybrid_matched_td - alns_matched_td) / alns_matched_td * 100

print(f"ALNS-Base Matched TD Mean: {alns_matched_td:.2f}")
print(f"Hybrid-DDQN Matched TD Mean: {hybrid_matched_td:.2f}")
print(f"Matched TD improvement: {diff_percent:+.2f}%")
