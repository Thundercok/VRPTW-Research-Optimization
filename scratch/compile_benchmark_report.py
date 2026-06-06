import pandas as pd
import numpy as np

solomon_shards = {
    "solomon_clustered": "results/ultimate-publication-suite/solomon_clustered/benchmark_clean.csv",
    "solomon_short_horizon": "results/ultimate-publication-suite/solomon_short_horizon/benchmark_clean.csv",
    "solomon_wide_horizon": "results/ultimate-publication-suite/solomon_wide_horizon/benchmark_clean.csv",
}

gh_shards = {
    "gehring_homberger_200": "results/ultimate-publication-suite/gehring_homberger_200/benchmark_clean.csv"
}

def analyze_shards(shards_dict, title, include_ortools=False):
    dfs = []
    for shard_name, path in shards_dict.items():
        try:
            shard_df = pd.read_csv(path)
            shard_df["Shard"] = shard_name
            dfs.append(shard_df)
        except Exception as e:
            print(f"Error loading {shard_name}: {e}")
    if not dfs:
        print(f"No data for {title}")
        return None
    df = pd.concat(dfs, ignore_index=True)
    df["Algorithm"] = df["Algorithm"].str.strip()

    algos = ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]
    if include_ortools:
        algos.append("OR-Tools")
        
    df = df[df["Algorithm"].isin(algos)]

    pivot_nv_diff = df.pivot_table(index="Shard", columns="Algorithm", values="NV_diff", aggfunc="mean")
    pivot_gap = df.pivot_table(index="Shard", columns="Algorithm", values="Gap%", aggfunc="mean")
    pivot_time = df.pivot_table(index="Shard", columns="Algorithm", values="Time_s", aggfunc="mean")

    print("\n" + "="*80)
    print(f" {title.upper()} - AVERAGE VEHICLE COUNT DIFF vs BKS (NV_diff)")
    print("="*80)
    print(pivot_nv_diff.round(3).to_string())

    print("\n" + "="*80)
    print(f" {title.upper()} - AVERAGE DISTANCE GAP % vs BKS (Gap%)")
    print("="*80)
    print(pivot_gap.round(3).to_string())

    print("\n" + "="*80)
    print(f" {title.upper()} - AVERAGE SOLVE TIME IN SECONDS (Time_s)")
    print("="*80)
    print(pivot_time.round(1).to_string())

    print("\n" + "="*80)
    print(f" {title.upper()} - SUMMARY STATS OVERALL")
    print("="*80)
    summary = []
    for algo in algos:
        algo_df = df[df["Algorithm"] == algo]
        summary.append({
            "Algorithm": algo,
            "NV_mean": algo_df["NV_mean"].mean(),
            "NV_diff_mean": algo_df["NV_diff"].mean(),
            "Gap%_mean": algo_df["Gap%"].mean(),
            "Time_s_mean": algo_df["Time_s"].mean()
        })
    summary_df = pd.DataFrame(summary).set_index("Algorithm")
    print(summary_df.round(3).to_string())
    return df

print("Compiling Solomon Shards...")
solomon_df = analyze_shards(solomon_shards, "Solomon (56 Instances)", include_ortools=True)

print("\nCompiling Gehring & Homberger 200 Shards...")
gh_df = analyze_shards(gh_shards, "Gehring & Homberger 200 (6 Instances)", include_ortools=True)

# Wilcoxon Signed-Rank Tests for Solomon
if solomon_df is not None:
    print("\n" + "="*80)
    print("WILCOXON SIGNED-RANK STATISTICAL TESTS - SOLOMON (N=56)")
    print("="*80)
    from scipy.stats import wilcoxon
    
    # Pivot the data for tests
    nv_df = solomon_df.pivot(index="Instance", columns="Algorithm", values="NV_mean")
    td_df = solomon_df.pivot(index="Instance", columns="Algorithm", values="TD_mean")

    def test_pair(df_pivot, name_a, name_b, label):
        diff = df_pivot[name_a] - df_pivot[name_b]
        if np.all(diff == 0):
            print(f"  {label} {name_a} vs {name_b}: Identical solutions (p-value N/A)")
        else:
            stat, p = wilcoxon(df_pivot[name_a], df_pivot[name_b])
            print(f"  {label} {name_a} vs {name_b}: p-value = {p:.4e} (stat={stat:.1f})")

    test_pair(nv_df, "Hybrid-DDQN", "ALNS-Base", "NV")
    test_pair(td_df, "Hybrid-DDQN", "ALNS-Base", "TD")

    test_pair(nv_df, "Hybrid-DDQN", "Hybrid-Rule", "NV")
    test_pair(td_df, "Hybrid-DDQN", "Hybrid-Rule", "TD")

    test_pair(nv_df, "Hybrid-DDQN", "Hybrid-Fixed", "NV")
    test_pair(td_df, "Hybrid-DDQN", "Hybrid-Fixed", "TD")


