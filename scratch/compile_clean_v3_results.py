import os
import pandas as pd

shards = {
    "Solomon Clustered (C1/C2)": "results/clean_v3/solomon_clustered/benchmark_clean.csv",
    "Solomon Short-Horizon (R1/RC1)": "results/clean_v3/solomon_short_horizon/benchmark_clean.csv",
    "Solomon Wide-Horizon (R2/RC2)": "results/clean_v3/solomon_wide_horizon/benchmark_clean.csv",
}

print("# COMPILING NEW SWEEP RESULTS (clean_v3)")
print("This table summarizes the completed Solomon shards under clean_v3 (runs = 2, iterations = 600).\n")

for name, path in shards.items():
    if not os.path.exists(path):
        print(f"### {name}: Missing results file ({path})\n")
        continue
        
    print(f"### {name}")
    df = pd.read_csv(path)
    
    # We want to group by Dataset (or family) and Algorithm, and calculate the mean of metrics
    # Let's map instances to their respective family (C1, C2, R1, R2, RC1, RC2)
    def get_family(inst):
        inst = inst.upper()
        if inst.startswith("C1"): return "C1"
        if inst.startswith("C2"): return "C2"
        if inst.startswith("RC1"): return "RC1"
        if inst.startswith("RC2"): return "RC2"
        if inst.startswith("R1"): return "R1"
        if inst.startswith("R2"): return "R2"
        return "Unknown"
        
    df["Family"] = df["Instance"].apply(get_family)
    
    # Clean Gap% column
    if "Gap%" in df.columns:
        df["Gap%"] = df["Gap%"].astype(str).str.replace("%", "").str.replace("+", "").astype(float)
        
    # Group by Family and Algorithm
    grouped = df.groupby(["Family", "Algorithm"]).agg({
        "NV_mean": "mean",
        "TD_mean": "mean",
        "Gap%": "mean",
        "Time_s": "mean"
    }).reset_index()
    
    # Sort
    order = ["OR-Tools", "ALNS-Base", "Hybrid-DDQN"]
    grouped["Algorithm"] = pd.Categorical(grouped["Algorithm"], categories=order, ordered=True)
    grouped = grouped.sort_values(by=["Family", "Algorithm"])
    
    print("| Family | Algorithm | Mean NV | Mean TD | Mean Gap% vs BKS | Mean Time |")
    print("| :--- | :--- | :---: | :---: | :---: | :---: |")
    for _, row in grouped.iterrows():
        print(f"| {row['Family']} | {row['Algorithm']} | {row['NV_mean']:.2f} | {row['TD_mean']:.2f} | {row['Gap%']:.2f}% | {row['Time_s']:.1f}s |")
    print("\n")
