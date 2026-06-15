import pandas as pd
import glob
import os

files = [
    "results/multiscale-publication-suite/solomon_100/benchmark_clean.csv",
    "results/multiscale-publication-suite/homberger_200/benchmark_clean.csv",
    "results/multiscale-publication-suite/homberger_400/benchmark_clean.csv"
]

print("Loading completed benchmark results...")
dfs = []
for f in files:
    if os.path.exists(f):
        df = pd.read_csv(f)
        # Extract scale from filename
        scale = f.split("/")[-2]
        df["Scale"] = scale
        dfs.append(df)

if not dfs:
    print("No result files found!")
    exit(1)

merged = pd.concat(dfs, ignore_index=True)

# Define the order we want to display the algorithms
algo_order = [
    "OR-Tools", "ALNS-Base", "GNN-ALNS-Base",
    "Hybrid-Fixed", "GNN-Hybrid-Fixed",
    "Hybrid-Rule", "GNN-Hybrid-Rule",
    "Hybrid-DDQN", "GNN-Hybrid-DDQN",
    "DQN"
]

# Standardize Algorithm names
merged["Algorithm"] = merged["Algorithm"].replace({
    "ALNS-Base": "ALNS-Base",
    "Hybrid-DDQN": "Hybrid-DDQN",
    "GNN-Hybrid-DDQN": "GNN-Hybrid-DDQN",
    "DQN": "DQN",
    "OR-Tools": "OR-Tools"
})

# Filter out rows where Algorithm is not in our list
merged = merged[merged["Algorithm"].isin(algo_order)]

print("\n--- COMPILING SUMMARY TABLE ---")

# Group by Scale, Instance, Algorithm and calculate averages
summary = merged.groupby(["Scale", "Instance", "Algorithm"]).agg({
    "NV_mean": "mean",
    "TD_mean": "mean",
    "Time_s": "mean"
}).reset_index()

# Pivot the table to show algorithm columns or print directly grouped by instance
print("| Scale | Instance | Algorithm | Avg NV | Avg TD | Avg Time (s) |")
print("| :--- | :--- | :--- | :--- | :--- | :--- |")
for _, row in summary.sort_values(by=["Scale", "Instance", "Algorithm"]).iterrows():
    print(f"| {row['Scale']} | {row['Instance']} | {row['Algorithm']} | {row['NV_mean']:.2f} | {row['TD_mean']:.2f} | {row['Time_s']:.1f}s |")
