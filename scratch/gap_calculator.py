import pandas as pd
from vrptw.config import BKS

# Load the two result files
sol_df = pd.read_csv("results/overnight_run/solomon/benchmark_checkpoint.csv")
rc_df = pd.read_csv("results/overnight_run/solomon_rc/benchmark_clean.csv")

# Combine them
df = pd.concat([sol_df, rc_df], ignore_index=True)
df["Algorithm"] = df["Algorithm"].str.strip()

# Find instances completed by all 5 algorithms
valid_instances = df.groupby("Instance")["Algorithm"].nunique()[lambda x: x == 5].index.tolist()
df = df[df["Instance"].isin(valid_instances)].copy()

# Add BKS columns
df["BKS_NV"] = df["Instance"].map(lambda x: BKS[x]["nv"])
df["BKS_TD"] = df["Instance"].map(lambda x: BKS[x]["td"])

# Calculate gaps (in %)
df["NV_Gap"] = (df["NV_mean"] - df["BKS_NV"]) / df["BKS_NV"] * 100
df["TD_Gap"] = (df["TD_mean"] - df["BKS_TD"]) / df["BKS_TD"] * 100

groups = ["C1", "C2", "R1", "R2", "RC1", "RC2"]
algorithms = ["OR-Tools", "ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]

print("=== DETAILED GAP ANALYSIS (MEAN OF PER-INSTANCE GAPS) ===")
for g in groups:
    print(f"\nGroup {g} (N={len(df[df['Dataset'] == g]['Instance'].unique())}):")
    # Reference BKS values
    sub_bks = df[(df["Dataset"] == g) & (df["Algorithm"] == "Hybrid-DDQN")]
    print(f"  BKS Reference - Avg NV: {sub_bks['BKS_NV'].mean():.2f}, Avg TD: {sub_bks['BKS_TD'].mean():.2f}")
    for algo in algorithms:
        sub = df[(df["Dataset"] == g) & (df["Algorithm"] == algo)]
        avg_nv = sub["NV_mean"].mean()
        avg_td = sub["TD_mean"].mean()
        mean_nv_gap = sub["NV_Gap"].mean()
        mean_td_gap = sub["TD_Gap"].mean()
        print(f"  {algo:<15} | Avg NV: {avg_nv:.2f} (Gap: {mean_nv_gap:+.2f}%) | Avg TD: {avg_td:.2f} (Gap: {mean_td_gap:+.2f}%)")
