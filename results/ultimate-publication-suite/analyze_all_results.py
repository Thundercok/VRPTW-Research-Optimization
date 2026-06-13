import os
import pandas as pd
import numpy as np
from scipy.stats import wilcoxon

def load_and_standardize(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        df = pd.read_csv(file_path)
        df["Algorithm"] = df["Algorithm"].str.strip()
        df["Instance"] = df["Instance"].str.strip()
        # Clean up any potential whitespace in string columns
        for col in ["Dataset", "Instance", "Algorithm"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def analyze_dataset_group(df, group_name, algos):
    if df is None or len(df) == 0:
        return None, None, 0
    
    # Check completeness
    algo_counts = df.groupby("Instance")["Algorithm"].nunique()
    valid_instances = algo_counts[algo_counts == len(algos)].index.tolist()
    total_instances = df["Instance"].nunique()
    
    print(f"\n==========================================================================")
    print(f" ANALYZING GROUP: {group_name} ({len(valid_instances)} / {total_instances} complete instances)")
    print(f"==========================================================================")
    
    df_valid = df[df["Instance"].isin(valid_instances)]
    if len(df_valid) == 0:
        print("No complete instances available for this group yet.")
        return None, None, 0
        
    nv_df = df_valid.pivot(index="Instance", columns="Algorithm", values="NV_mean")
    td_df = df_valid.pivot(index="Instance", columns="Algorithm", values="TD_mean")
    time_df = df_valid.pivot(index="Instance", columns="Algorithm", values="Time_s")
    
    # Subgroup breakdown
    subgroups = sorted(df_valid["Dataset"].unique())
    print("\n--- VEHICLE COUNT (NV) MEAN ---")
    subgroup_summary = []
    for sg in subgroups:
        insts_sg = df_valid[df_valid["Dataset"] == sg]["Instance"].unique()
        print(f"\nSubgroup {sg} (N={len(insts_sg)}):")
        sg_row = {"Subgroup": sg, "Metric": "NV"}
        for algo in algos:
            val = nv_df.loc[insts_sg, algo].mean()
            print(f"  {algo:<15}: {val:.2f}")
            sg_row[algo] = val
        subgroup_summary.append(sg_row)
            
    print("\n--- TOTAL DISTANCE (TD) MEAN ---")
    for sg in subgroups:
        insts_sg = df_valid[df_valid["Dataset"] == sg]["Instance"].unique()
        print(f"\nSubgroup {sg} (N={len(insts_sg)}):")
        sg_row = {"Subgroup": sg, "Metric": "TD"}
        for algo in algos:
            val = td_df.loc[insts_sg, algo].mean()
            print(f"  {algo:<15}: {val:.2f}")
            sg_row[algo] = val
        subgroup_summary.append(sg_row)
        
    print("\n--- RUNTIME (SECONDS) MEAN ---")
    for sg in subgroups:
        insts_sg = df_valid[df_valid["Dataset"] == sg]["Instance"].unique()
        print(f"\nSubgroup {sg} (N={len(insts_sg)}):")
        sg_row = {"Subgroup": sg, "Metric": "Time"}
        for algo in algos:
            val = time_df.loc[insts_sg, algo].mean()
            print(f"  {algo:<15}: {val:.1f}s")
            sg_row[algo] = val
        subgroup_summary.append(sg_row)

    # Wilcoxon Signed-Rank Tests
    print("\n--- WILCOXON SIGNED-RANK TESTS (Overall) ---")
    
    def run_test(x, y, name_x, name_y, metric):
        diff = x - y
        if np.all(diff == 0):
            print(f"  {metric:<4} {name_x} vs {name_y}: Identical solutions (p-value N/A)")
            return "Identical"
        try:
            stat, p = wilcoxon(x, y)
            print(f"  {metric:<4} {name_x} vs {name_y}: p-value = {p:.4e} (stat={stat:.1f})")
            return f"{p:.4e}"
        except Exception as exc:
            print(f"  {metric:<4} {name_x} vs {name_y}: Error ({exc})")
            return f"Error ({exc})"

    test_results = {}
    for comp in [("Hybrid-DDQN", "ALNS-Base"), ("Hybrid-DDQN", "Hybrid-Rule"), ("Hybrid-DDQN", "OR-Tools")]:
        x_alg, y_alg = comp
        test_results[f"NV_{x_alg}_vs_{y_alg}"] = run_test(nv_df[x_alg], nv_df[y_alg], x_alg, y_alg, "NV")
        test_results[f"TD_{x_alg}_vs_{y_alg}"] = run_test(td_df[x_alg], td_df[y_alg], x_alg, y_alg, "TD")
        
    return subgroup_summary, test_results, len(valid_instances)

def main():
    base_dir = "results/ultimate-publication-suite"
    
    # 1. Solomon Shards
    solomon_shards = [
        os.path.join(base_dir, "solomon_clustered/benchmark_clean.csv"),
        os.path.join(base_dir, "solomon_short_horizon/benchmark_clean.csv"),
        os.path.join(base_dir, "solomon_wide_horizon/benchmark_clean.csv"),
    ]
    sol_dfs = [load_and_standardize(f) for f in solomon_shards if os.path.exists(f)]
    sol_df = pd.concat(sol_dfs, ignore_index=True) if sol_dfs else None
    
    # 2. Homberger Shards
    homberger_info = [
        ("Homberger 200", os.path.join(base_dir, "gehring_homberger_200/benchmark_clean.csv")),
        ("Homberger 400", os.path.join(base_dir, "gehring_homberger_400/benchmark_clean.csv")),
        ("Homberger 600", os.path.join(base_dir, "gehring_homberger_600/benchmark_clean.csv")),
        ("Homberger 800", os.path.join(base_dir, "gehring_homberger_800/benchmark_clean.csv")),
        ("Homberger 1000", os.path.join(base_dir, "gehring_homberger_1000/benchmark_clean.csv")),
    ]
    
    algos = ["OR-Tools", "ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]
    
    report_markdown = []
    report_markdown.append("# Ultimate Publication Suite - Final Analysis Report")
    report_markdown.append(f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Analyze Solomon
    if sol_df is not None:
        sg_summary, tests, n_complete = analyze_dataset_group(sol_df, "Solomon (56 Instances)", algos)
        
        if sg_summary is not None:
            report_markdown.append("## Solomon Instances Summary (N = 56)")
            report_markdown.append("| Subgroup | Metric | OR-Tools | ALNS-Base | Hybrid-Fixed | Hybrid-Rule | Hybrid-DDQN |")
            report_markdown.append("|---|---|---|---|---|---|---|")
            for row in sg_summary:
                report_markdown.append(f"| {row['Subgroup']} | {row['Metric']} | {row['OR-Tools']:.2f} | {row['ALNS-Base']:.2f} | {row['Hybrid-Fixed']:.2f} | {row['Hybrid-Rule']:.2f} | {row['Hybrid-DDQN']:.2f} |")
            
            report_markdown.append("\n### Solomon Wilcoxon Hypothesis Testing")
            report_markdown.append("| Test Comparison | Metric | p-value |")
            report_markdown.append("|---|---|---|")
            for key, pval in tests.items():
                metric, comp = key.split("_", 1)
                comp_pretty = comp.replace("_vs_", " vs ")
                report_markdown.append(f"| {comp_pretty} | {metric} | {pval} |")
            report_markdown.append("\n")
        else:
            report_markdown.append("## Solomon Summary")
            report_markdown.append("*Benchmark results are currently incomplete or pending.*\n")

    # Analyze Homberger Shards
    for name, path in homberger_info:
        h_df = load_and_standardize(path)
        if h_df is not None and len(h_df) > 0:
            sg_summary, tests, n_complete = analyze_dataset_group(h_df, name, algos)
            
            if sg_summary is not None:
                report_markdown.append(f"## {name} Summary (Complete: {n_complete})")
                report_markdown.append("| Subgroup | Metric | OR-Tools | ALNS-Base | Hybrid-Fixed | Hybrid-Rule | Hybrid-DDQN |")
                report_markdown.append("|---|---|---|---|---|---|---|")
                for row in sg_summary:
                    report_markdown.append(f"| {row['Subgroup']} | {row['Metric']} | {row['OR-Tools']:.2f} | {row['ALNS-Base']:.2f} | {row['Hybrid-Fixed']:.2f} | {row['Hybrid-Rule']:.2f} | {row['Hybrid-DDQN']:.2f} |")
                
                report_markdown.append(f"\n### {name} Wilcoxon Hypothesis Testing")
                report_markdown.append("| Test Comparison | Metric | p-value |")
                report_markdown.append("|---|---|---|")
                for key, pval in tests.items():
                    metric, comp = key.split("_", 1)
                    comp_pretty = comp.replace("_vs_", " vs ")
                    report_markdown.append(f"| {comp_pretty} | {metric} | {pval} |")
                report_markdown.append("\n")
            else:
                report_markdown.append(f"## {name} Summary")
                report_markdown.append(f"*Benchmark results are currently incomplete or pending.*\n")
        else:
            print(f"\nShard '{name}' is not complete or not found yet.")
            report_markdown.append(f"## {name} Summary")
            report_markdown.append(f"*Benchmark results are currently pending for this shard.*\n")

    # Write report to markdown file
    report_path = os.path.join(base_dir, "final_analysis_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(report_markdown))
    print(f"\nReport successfully saved to: {report_path}")

if __name__ == "__main__":
    main()
