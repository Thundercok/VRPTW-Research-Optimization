import os
import pandas as pd
import numpy as np
from scipy import stats

ROOT = "/Users/thundercock2/Documents/Github/VRPTW-Research-Optimization/VRPTW-Research-Optimization"
OUTPUT_BASE = os.path.join(ROOT, "results", "ultimate-publication-suite")
SHARDS = {
    1: {"name": "solomon_clustered", "path": "solomon_clustered"},
    2: {"name": "solomon_short_horizon", "path": "solomon_short_horizon"},
    3: {"name": "solomon_wide_horizon", "path": "solomon_wide_horizon"},
    4: {"name": "gehring_homberger_200", "path": "gehring_homberger_200"}
}

def load_data():
    dfs = []
    for sid, shard in SHARDS.items():
        clean_path = os.path.join(OUTPUT_BASE, shard["path"], "benchmark_clean.csv")
        if os.path.exists(clean_path):
            dfs.append(pd.read_csv(clean_path))
    if not dfs:
        raise FileNotFoundError("No benchmark clean files found!")
    df = pd.concat(dfs, ignore_index=True)
    df["Algorithm"] = df["Algorithm"].str.strip()
    return df

def wilcoxon_per_run(df, algo_a, algo_b, metric_col="raw_costs"):
    a_rows = df[df['Algorithm'] == algo_a]
    b_rows = df[df['Algorithm'] == algo_b]
    
    vals_a, vals_b = [], []
    common_instances = set(a_rows['Instance']) & set(b_rows['Instance'])
    
    for inst_name in sorted(common_instances):
        ra = a_rows[a_rows['Instance'] == inst_name]
        rb = b_rows[b_rows['Instance'] == inst_name]
        if ra.empty or rb.empty:
            continue
        
        if metric_col in ra.columns and pd.notna(ra[metric_col].values[0]):
            ac = [float(x) for x in str(ra[metric_col].values[0]).split(';')]
            bc = [float(x) for x in str(rb[metric_col].values[0]).split(';')]
            n = min(len(ac), len(bc))
            vals_a.extend(ac[:n])
            vals_b.extend(bc[:n])
        else:
            # Fallback
            mean_col = "TD_mean" if metric_col == "raw_costs" else "NV_mean"
            vals_a.append(float(ra[mean_col].values[0]))
            vals_b.append(float(rb[mean_col].values[0]))
            
    vals_a = np.array(vals_a)
    vals_b = np.array(vals_b)
    
    diff = vals_a - vals_b
    nonzero = diff[diff != 0]
    if len(nonzero) < 5:
        return {'stat': None, 'p': None, 'n': len(vals_a)}
        
    stat, p = stats.wilcoxon(vals_a, vals_b, alternative='two-sided')
    
    # Calculate effect size r = Z / sqrt(N)
    # For large samples, we can approximate Z
    # But scipy's wilcoxon returns the statistic W. Let's do a direct calculation of Z if needed.
    # W = min(rank_sum_positive, rank_sum_negative)
    # We can use stats.rankdata on absolute differences to compute the exact Z statistic.
    n = len(nonzero)
    ranks = stats.rankdata(np.abs(nonzero))
    w_pos = np.sum(ranks[nonzero > 0])
    w_neg = np.sum(ranks[nonzero < 0])
    w = min(w_pos, w_neg)
    mean_w = n * (n + 1) / 4.0
    var_w = n * (n + 1) * (2 * n + 1) / 24.0
    # Correction for ties if needed, but this is a standard approximation
    z = (w - mean_w) / np.sqrt(var_w)
    r = np.abs(z) / np.sqrt(len(vals_a)) # effect size
    
    return {
        'stat': stat,
        'p': p,
        'n': len(vals_a),
        'effect_r': r,
        'mean_a': vals_a.mean(),
        'mean_b': vals_b.mean()
    }

def analyze():
    df = load_data()
    
    # Filter for instances completed by all 5 algorithms
    algo_counts = df.dropna(subset=["NV_mean"]).groupby("Instance")["Algorithm"].nunique()
    valid_instances = algo_counts[algo_counts == 5].index.tolist()
    df_valid = df[df["Instance"].isin(valid_instances)].copy()
    
    print(f"Total instances analyzed (N={len(valid_instances)}):")
    
    solomon_instances = [inst for inst in valid_instances if not "_" in inst]
    df_solomon = df_valid[df_valid["Instance"].isin(solomon_instances)].copy()
    
    gh_instances = [inst for inst in valid_instances if "_" in inst]
    df_gh = df_valid[df_valid["Instance"].isin(gh_instances)].copy()
    
    # 1. Wilcoxon signed-rank tests (per-run paired, N=62 instances * 5 runs = 310 observations)
    print("\n=== WILCOXON SIGNED-RANK TESTS (per-run paired, N=62 * 5 = 310 observations) ===")
    for comparison in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "OR-Tools"]:
        # Vehicle Count (NV) Wilcoxon using raw_nv
        res_nv = wilcoxon_per_run(df_valid, "Hybrid-DDQN", comparison, "raw_nv")
        if res_nv['stat'] is not None:
            print(f"NV: Hybrid-DDQN vs {comparison}: p-value = {res_nv['p']:.4e} (W={res_nv['stat']:.1f}, r={res_nv['effect_r']:.3f})")
        else:
            print(f"NV: Hybrid-DDQN vs {comparison}: No significant variance (identical NV values)")
            
        # Travel Distance (TD) Wilcoxon using raw_costs
        res_td = wilcoxon_per_run(df_valid, "Hybrid-DDQN", comparison, "raw_costs")
        if res_td['stat'] is not None:
            print(f"TD: Hybrid-DDQN vs {comparison}: p-value = {res_td['p']:.4e} (W={res_td['stat']:.1f}, r={res_td['effect_r']:.3f})")
        else:
            print(f"TD: Hybrid-DDQN vs {comparison}: No significant variance (identical TD values)")
        print()

    # 2. Table V: Ablation Analysis (overall N=62 instances)
    print("\n=== TABLE V: ABLATION ANALYSIS ===")
    # Averages over all 62 instances (Solomon + GH)
    for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
        sub_df = df_valid[df_valid["Algorithm"] == algo]
        avg_nv_diff = sub_df["NV_diff"].mean()
        avg_gap = sub_df["Gap%"].mean()
        print(f"{algo:<20} NV Diff: {avg_nv_diff:>+.3f} | TD Gap%: {avg_gap:>+.3f}%")

    # 3. Table VI: NV-filtered TD Gap% (Solomon only, N=56)
    print("\n=== TABLE VI: NV-FILTERED TD GAP% (SOLOMON) ===")
    # Algo-specific filtering
    print("Algo-specific:")
    for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
        sub = df_solomon[(df_solomon["Algorithm"] == algo) & (df_solomon["NV_diff"] <= 0)]
        print(f"  {algo}: N={len(sub)}, Avg TD Gap = {sub['Gap%'].mean():.3f}%")
        
    # Fair intersection filtering (instances where all 4 algorithms achieved NV_diff <= 0)
    solomon_nv_diff_pivot = df_solomon.pivot(index="Instance", columns="Algorithm", values="NV_diff")
    conds = [solomon_nv_diff_pivot[algo] <= 0 for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]]
    fair_insts = solomon_nv_diff_pivot[np.logical_and.reduce(conds)].index.tolist()
    print(f"Fair intersection (N={len(fair_insts)}):")
    df_fair = df_solomon[df_solomon["Instance"].isin(fair_insts)]
    fair_overall_gaps = df_fair.groupby("Algorithm")["Gap%"].mean()
    for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
        print(f"  {algo}: Avg TD Gap = {fair_overall_gaps[algo]:.3f}%")

    # 4. Table VII: Solomon Category Breakdown (Fair Intersection)
    print("\n=== TABLE VII: SOLOMON CATEGORY BREAKDOWN (FAIR INTERSECTION) ===")
    def get_cat(inst):
        if inst.startswith("C1") or inst.startswith("C2"):
            return "Clustered"
        elif inst.startswith("R1") or inst.startswith("RC1"):
            return "Short-Horizon"
        elif inst.startswith("R2") or inst.startswith("RC2"):
            return "Wide-Horizon"
        return "Unknown"
    df_fair = df_fair.copy()
    df_fair["Category"] = df_fair["Instance"].apply(get_cat)
    fair_cat_gaps = df_fair.groupby(["Category", "Algorithm"])["Gap%"].mean().unstack()
    for cat in ["Clustered", "Short-Horizon", "Wide-Horizon"]:
        print(f"Category: {cat} (N={len(df_fair[(df_fair['Category'] == cat) & (df_fair['Algorithm'] == 'Hybrid-DDQN')])})")
        for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"]:
            print(f"  {algo}: {fair_cat_gaps.loc[cat, algo]:.3f}%")

    # 5. Table VIII: Gehring-Homberger 200 (6 instances)
    print("\n=== TABLE VIII: GEHRING-HOMBERGER 200 RESULTS ===")
    # Print exactly like Table VII in paper.tex (Instance & BKS & ALNS & H-Fixed & H-Rule & H-DDQN & OR-Tools)
    gh_pivot_nv = df_gh.pivot(index="Instance", columns="Algorithm", values="NV_mean")
    gh_pivot_gap = df_gh.pivot(index="Instance", columns="Algorithm", values="Gap%")
    
    # We need the BKS NV and TD for Gehring-Homberger 200
    gh_bks = {
        "c1_2_1": {"nv": 20, "td": 2704.57},
        "c2_2_1": {"nv": 6, "td": 1931.44},
        "r1_2_1": {"nv": 20, "td": 4795.12},
        "r2_2_1": {"nv": 4, "td": 4483.00},
        "rc1_2_1": {"nv": 18, "td": 3603.00},
        "rc2_2_1": {"nv": 6, "td": 3099.00}
    }
    
    for inst in sorted(gh_bks.keys()):
        bks_nv = gh_bks[inst]["nv"]
        bks_td = gh_bks[inst]["td"]
        
        row_str = f"{inst:<10} BKS: {bks_nv}/{bks_td:.2f}"
        for algo in ["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN", "OR-Tools"]:
            nv = gh_pivot_nv.loc[inst, algo]
            gap = gh_pivot_gap.loc[inst, algo]
            row_str += f" | {algo}: {int(nv)}/{gap:+.2f}%"
        print(row_str)

if __name__ == "__main__":
    analyze()
