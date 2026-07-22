import os
import pandas as pd
from scipy.stats import wilcoxon

shards_solomon = {
    "C1/C2": "results/clean_v4/solomon_clustered/benchmark_clean.csv",
    "R1/RC1": "results/clean_v4/solomon_short_horizon/benchmark_clean.csv",
    "R2/RC2": "results/clean_v4/solomon_wide_horizon/benchmark_clean.csv",
}

shards_gh200 = {
    "C1": "results/clean_v4/gehring_homberger_200/c1/benchmark_clean.csv",
    "C2": "results/clean_v4/gehring_homberger_200/c2/benchmark_clean.csv",
    "R1": "results/clean_v4/gehring_homberger_200/r1/benchmark_clean.csv",
    "R2": "results/clean_v4/gehring_homberger_200/r2/benchmark_clean.csv",
    "RC1": "results/clean_v4/gehring_homberger_200/rc1/benchmark_clean.csv",
    "RC2": "results/clean_v4/gehring_homberger_200/rc2/benchmark_clean.csv",
}

shards_larger = {
    "GH-400": "results/clean_v4/gehring_homberger_400/benchmark_clean.csv",
    "GH-600": "results/clean_v4/gehring_homberger_600/benchmark_clean.csv",
}

def get_family(inst):
    inst = inst.upper()
    if inst.startswith("C1_2"): return "C1"
    if inst.startswith("C2_2"): return "C2"
    if inst.startswith("R1_2"): return "R1"
    if inst.startswith("R2_2"): return "R2"
    if inst.startswith("RC1_2"): return "RC1"
    if inst.startswith("RC2_2"): return "RC2"
    if inst.startswith("C1"): return "C1"
    if inst.startswith("C2"): return "C2"
    if inst.startswith("RC1"): return "RC1"
    if inst.startswith("RC2"): return "RC2"
    if inst.startswith("R1"): return "R1"
    if inst.startswith("R2"): return "R2"
    return "Unknown"

def clean_df(df):
    if "Gap%" in df.columns:
        df["Gap%"] = df["Gap%"].astype(str).str.replace("%", "").str.replace("+", "").astype(float)
    return df

def compile_section(name, paths_dict):
    print(f"\n=======================================================")
    print(f"  {name} RESULTS SUMMARY")
    print(f"=======================================================")
    dfs = []
    for k, p in paths_dict.items():
        if os.path.exists(p):
            dfs.append(pd.read_csv(p))
    if not dfs:
        print(f"No results found for {name}.\n")
        return None
    
    df = pd.concat(dfs, ignore_index=True)
    df = clean_df(df)
    df["Family"] = df["Instance"].apply(get_family)
    
    grouped = df.groupby(["Family", "Algorithm"]).agg({
        "NV_mean": "mean",
        "TD_mean": "mean",
        "Gap%": "mean",
        "Time_s": "mean"
    }).reset_index()
    
    order = ["OR-Tools", "ALNS-Base", "Hybrid-DDQN"]
    grouped["Algorithm"] = pd.Categorical(grouped["Algorithm"], categories=order, ordered=True)
    grouped = grouped.sort_values(by=["Family", "Algorithm"])
    
    print("| Family | Algorithm | Mean NV | Mean TD | Mean Gap% vs BKS | Mean Time |")
    print("| :--- | :--- | :---: | :---: | :---: | :---: |")
    for _, row in grouped.iterrows():
        print(f"| {row['Family']} | {row['Algorithm']} | {row['NV_mean']:.2f} | {row['TD_mean']:.2f} | {row['Gap%']:.2f}% | {row['Time_s']:.1f}s |")
    
    # Run Wilcoxon Signed-Rank Test if both ALNS-Base and Hybrid-DDQN are present
    alns = df[df["Algorithm"] == "ALNS-Base"].sort_values("Instance")
    ddqn = df[df["Algorithm"] == "Hybrid-DDQN"].sort_values("Instance")
    merged = pd.merge(alns, ddqn, on="Instance", suffixes=("_alns", "_ddqn"))
    if len(merged) > 1:
        print(f"\nAligned Instances: {len(merged)}")
        nv_alns, nv_ddqn = merged["NV_mean_alns"].values, merged["NV_mean_ddqn"].values
        td_alns, td_ddqn = merged["TD_mean_alns"].values, merged["TD_mean_ddqn"].values
        
        try:
            _, p_nv = wilcoxon(nv_alns, nv_ddqn, alternative="greater")
            print(f"NV Wilcoxon p-value (ALNS-Base > Hybrid-DDQN): {p_nv:.6g}")
        except Exception as e:
            print("Failed to run Wilcoxon on NV:", e)
            
        try:
            _, p_td = wilcoxon(td_alns, td_ddqn, alternative="greater")
            print(f"TD Wilcoxon p-value (ALNS-Base > Hybrid-DDQN): {p_td:.6g}")
        except Exception as e:
            print("Failed to run Wilcoxon on TD:", e)
            
        # Matched NV subset
        matched = merged[merged["NV_mean_alns"] == merged["NV_mean_ddqn"]]
        print(f"Matched NV Subset: {len(matched)} / {len(merged)}")
        if len(matched) > 1:
            td_alns_m, td_ddqn_m = matched["TD_mean_alns"].values, matched["TD_mean_ddqn"].values
            try:
                _, p_td_m = wilcoxon(td_alns_m, td_ddqn_m, alternative="greater")
                print(f"Matched-NV TD Wilcoxon p-value (ALNS-Base > Hybrid-DDQN): {p_td_m:.6g}")
            except Exception as e:
                print("Failed to run Wilcoxon on Matched-NV TD:", e)
    return df

print("# COMPILING SWEEP RESULTS FOR clean_v4\n")
df_sol = compile_section("SOLOMON 100", shards_solomon)
df_gh200 = compile_section("GEHRING & HOMBERGER 200", shards_gh200)

for name, path in shards_larger.items():
    if os.path.exists(path):
        print(f"\n=======================================================")
        print(f"  {name} RESULTS SUMMARY")
        print(f"=======================================================")
        df = pd.read_csv(path)
        df = clean_df(df)
        df["Family"] = df["Instance"].apply(get_family)
        grouped = df.groupby(["Family", "Algorithm"]).agg({
            "NV_mean": "mean",
            "TD_mean": "mean",
            "Gap%": "mean",
            "Time_s": "mean"
        }).reset_index()
        order = ["OR-Tools", "ALNS-Base", "Hybrid-DDQN"]
        grouped["Algorithm"] = pd.Categorical(grouped["Algorithm"], categories=order, ordered=True)
        grouped = grouped.sort_values(by=["Family", "Algorithm"])
        print("| Family | Algorithm | Mean NV | Mean TD | Mean Gap% vs BKS | Mean Time |")
        print("| :--- | :--- | :---: | :---: | :---: | :---: |")
        for _, row in grouped.iterrows():
            print(f"| {row['Family']} | {row['Algorithm']} | {row['NV_mean']:.2f} | {row['TD_mean']:.2f} | {row['Gap%']:.2f}% | {row['Time_s']:.1f}s |")
