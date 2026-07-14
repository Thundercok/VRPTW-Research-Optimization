import os
import pandas as pd
import numpy as np

shards = {
    "C1": "results/clean_v3/solomon_clustered/benchmark_clean.csv",
    "C2": "results/clean_v3/solomon_clustered/benchmark_clean.csv",
    "R1": "results/clean_v3/solomon_short_horizon/benchmark_clean.csv",
    "RC1": "results/clean_v3/solomon_short_horizon/benchmark_clean.csv",
    "R2": "results/clean_v3/solomon_wide_horizon/benchmark_clean.csv",
    "RC2": "results/clean_v3/solomon_wide_horizon/benchmark_clean.csv",
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

# Load and combine all results
dfs = []
for fam, path in shards.items():
    if os.path.exists(path):
        df = pd.read_csv(path)
        df["Family"] = df["Instance"].apply(get_family)
        df = df[df["Family"] == fam]
        dfs.append(df)

if not dfs:
    print("No clean_v3 data found.")
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

# Sort by Family and Algorithm
order = ["OR-Tools", "ALNS-Base", "Hybrid-DDQN"]
grouped["Algorithm"] = pd.Categorical(grouped["Algorithm"], categories=order, ordered=True)
grouped = grouped.sort_values(by=["Family", "Algorithm"]).dropna(subset=["Algorithm"])

# Print LaTeX code
print("=== LATEX TABLE FOR THESIS.TEX ===")
print(r"\begin{table}[!htbp]")
print(r"\centering")
print(r"\caption{So sánh tổng hợp hiệu năng trung bình trên toàn bộ 6 lớp dữ liệu Solomon (clean\_v3)}")
print(r"\label{tab:solomon_results}")
print(r"\resizebox{\textwidth}{!}{%")
print(r"\begin{tabular}{llrrrr}")
print(r"\toprule")
print(r"\textbf{Lớp dữ liệu} & \textbf{Thuật toán} & \textbf{NV\_mean} & \textbf{TD\_mean} & \textbf{Gap\%} & \textbf{Thời gian (s)} \\")
print(r"\midrule")

current_family = None
for _, row in grouped.iterrows():
    fam = row["Family"]
    algo = row["Algorithm"]
    nv = f"{row['NV_mean']:.2f}"
    td = f"{row['TD_mean']:.2f}"
    gap = f"{row['Gap%']:.2f}\\%"
    if row['Gap%'] >= 0:
        gap = "+" + gap
    t = f"{row['Time_s']:.1f}"
    
    if algo == "Hybrid-DDQN":
        algo_str = r"\textbf{Hybrid-DDQN (Đề xuất)}"
        nv = r"\textbf{" + nv + "}"
        td = r"\textbf{" + td + "}"
        gap = r"\textbf{" + gap + "}"
        t = r"\textbf{" + t + "}"
    else:
        algo_str = algo

    if fam != current_family:
        if current_family is not None:
            print(r"\midrule")
        print(f"\\multirow{{3}}{{*}}{{{fam}}} & {algo_str} & {nv} & {td} & {gap} & {t} \\\\")
        current_family = fam
    else:
        print(f" & {algo_str} & {nv} & {td} & {gap} & {t} \\\\")

print(r"\bottomrule")
print(r"\end{tabular}}")
print(r"\end{table}")
