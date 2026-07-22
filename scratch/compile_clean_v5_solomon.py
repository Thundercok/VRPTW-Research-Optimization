import os
import pandas as pd
from scipy.stats import wilcoxon

shards_solomon = {
    "C1/C2": "results/clean_v5/solomon_clustered/benchmark_clean.csv",
    "R1/RC1": "results/clean_v5/solomon_short_horizon/benchmark_clean.csv",
    "R2/RC2": "results/clean_v5/solomon_wide_horizon/benchmark_clean.csv",
}

def get_family(inst):
    inst = inst.upper()
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

def main():
    print("# COMPILING SWEEP RESULTS FOR clean_v5 (SOLOMON 100)\n")
    
    dfs = []
    for k, p in shards_solomon.items():
        if os.path.exists(p):
            dfs.append(pd.read_csv(p))
            
    if not dfs:
        print("No Solomon results found in clean_v5.")
        return
        
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
         
    # Wilcoxon Tests
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

if __name__ == "__main__":
    main()
