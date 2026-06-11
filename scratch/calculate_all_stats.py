import pandas as pd
import numpy as np

# Load and combine result files
sol_df = pd.read_csv("results/overnight_run/solomon/benchmark_checkpoint.csv")
rc_df = pd.read_csv("results/overnight_run/solomon_rc/benchmark_clean.csv")
df = pd.concat([sol_df, rc_df], ignore_index=True)

# Standardize names
df["Algorithm"] = df["Algorithm"].str.strip()
df["Instance"] = df["Instance"].str.strip()

# Only keep instances completed by all 5 algorithms
algo_counts = df.groupby("Instance")["Algorithm"].nunique()
valid_instances = algo_counts[algo_counts == 5].index.tolist()
df = df[df["Instance"].isin(valid_instances)]

# Categorize Solomon families
# C1, C2 -> Clustered (N=17)
# R1, RC1 -> Short Horizon (N=20)
# R2, RC2 -> Wide Horizon (N=18)
def get_category(dataset):
    if dataset in ["C1", "C2"]:
        return "Clustered"
    elif dataset in ["R1", "RC1"]:
        return "Short Horizon"
    elif dataset in ["R2", "RC2"]:
        return "Wide Horizon"
    return "Unknown"

df["Category"] = df["Dataset"].apply(get_category)

# Table 1: NV_diff mean by category and overall
print("=== TABLE I: NV_diff averages ===")
nv_diff_pivot = df.pivot(index="Instance", columns="Algorithm", values="NV_diff")
categories = ["Clustered", "Short Horizon", "Wide Horizon"]
instance_categories = df.drop_duplicates("Instance").set_index("Instance")["Category"]

for cat in categories:
    insts_cat = instance_categories[instance_categories == cat].index
    print(f"\n{cat} (N={len(insts_cat)}):")
    for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN", "OR-Tools"]:
        val = nv_diff_pivot.loc[insts_cat, algo].mean()
        print(f"  {algo:<15}: {val:.4f}")

print("\nOverall Mean:")
for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN", "OR-Tools"]:
    val = nv_diff_pivot[algo].mean()
    print(f"  {algo:<15}: {val:.4f}")


# Table II & III: NV-filtered TD Gap%
print("\n=== TABLE II & III: NV-FILTERED TD GAP% ===")

# Algo-specific filter: each algorithm filtered where its own NV_inflated is False (or NV_diff <= 0)
print("\nAlgo-specific Filtering:")
for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
    algo_df = df[(df["Algorithm"] == algo) & (df["NV_diff"] <= 0)]
    n_insts = len(algo_df)
    avg_gap = algo_df["Gap%"].mean()
    print(f"  {algo:<15}: {avg_gap:.4f}% (N={n_insts})")

# Fair intersection filter: instances where ALL 4 heuristic algorithms have NV_diff <= 0
inflated_counts = df[df["Algorithm"].isin(["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"])].groupby("Instance")["NV_diff"].max()
fair_instances = inflated_counts[inflated_counts <= 0].index.tolist()
print(f"\nFair Intersection Subset (N={len(fair_instances)}):")

# Overall fair intersection mean
print("\nOverall Fair Intersection Mean:")
for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
    algo_fair = df[(df["Algorithm"] == algo) & (df["Instance"].isin(fair_instances))]
    avg_gap = algo_fair["Gap%"].mean()
    print(f"  {algo:<15}: {avg_gap:.4f}%")

# Fair intersection by category
print("\nFair Intersection by Category:")
for cat in categories:
    insts_cat = instance_categories[instance_categories == cat].index
    fair_insts_cat = [i for i in fair_instances if i in insts_cat]
    print(f"\n  {cat} (N={len(fair_insts_cat)}):")
    for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
        algo_fair_cat = df[(df["Algorithm"] == algo) & (df["Instance"].isin(fair_insts_cat))]
        avg_gap = algo_fair_cat["Gap%"].mean()
        print(f"    {algo:<15}: {avg_gap:.4f}%")
