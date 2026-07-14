import os
import pandas as pd
import numpy as np

shards = {
    "C1": "results/clean_v3/gehring_homberger_200/c1/benchmark_clean.csv",
    "C2": "results/clean_v3/gehring_homberger_200/c2/benchmark_clean.csv",
    "R1": "results/clean_v3/gehring_homberger_200/r1/benchmark_clean.csv",
    "R2": "results/clean_v3/gehring_homberger_200/r2/benchmark_clean.csv",
    "RC1": "results/clean_v3/gehring_homberger_200/rc1/benchmark_clean.csv",
    "RC2": "results/clean_v3/gehring_homberger_200/rc2/benchmark_clean.csv",
}

dfs = []
for fam, path in shards.items():
    if os.path.exists(path):
        df = pd.read_csv(path)
        df["Family"] = fam
        dfs.append(df)

if not dfs:
    print("No H200 data found.")
    exit(1)

df_all = pd.concat(dfs, ignore_index=True)

# Clean Gap% column
if "Gap%" in df_all.columns:
    df_all["Gap%"] = df_all["Gap%"].astype(str).str.replace("%", "").str.replace("+", "").astype(float)

# Group by Family and Algorithm
grouped = df_all.groupby(["Family", "Algorithm"]).agg({
    "NV_mean": "mean",
    "TD_mean": "mean",
    "Gap%": "mean",
    "Time_s": "mean"
}).reset_index()

# Sort
order = ["OR-Tools", "ALNS-Base", "Hybrid-DDQN"]
grouped["Algorithm"] = pd.Categorical(grouped["Algorithm"], categories=order, ordered=True)
grouped = grouped.sort_values(by=["Family", "Algorithm"]).dropna(subset=["Algorithm"])

print("# GEHRING & HOMBERGER 200 - SWEEP RESULTS (clean_v3)")
print("| Family | Algorithm | Mean NV | Mean TD | Mean Gap% vs BKS | Mean Time |")
print("| :--- | :--- | :---: | :---: | :---: | :---: |")
for _, row in grouped.iterrows():
    print(f"| {row['Family']} | {row['Algorithm']} | {row['NV_mean']:.2f} | {row['TD_mean']:.2f} | {row['Gap%']:.2f}% | {row['Time_s']:.1f}s |")
