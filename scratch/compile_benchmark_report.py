import pandas as pd

df = pd.read_csv("docs/logs/benchmark_clean.csv")

# We want to display the results in a beautiful table format.
# Let's filter for each algorithm and display it grouped by instance or family.
# Wait, let's create a table with:
# Instance | ALNS-Base NV (TD) | Hybrid-Fixed NV (TD) | Hybrid-Rule NV (TD) | Hybrid-DDQN NV (TD) | OR-Tools NV (TD)

pivot_df = df.pivot(index=["Dataset", "Instance"], columns="Algorithm", values=["NV_mean", "TD_mean", "Gap%"])

output_file = "/Users/thundercock2/.gemini/antigravity/brain/a2f667cd-3d6f-4d5b-87ad-a5f864490fc1/full_benchmark_results.md"

with open(output_file, "w") as f:
    f.write("# Full 56-Instance Solomon Benchmark Results\n\n")
    f.write("Below is the detailed instance-by-instance breakdown of the full 56-instance benchmark results loaded from `docs/logs/benchmark_clean.csv`.\n\n")
    
    # We can create a markdown table
    f.write("| Instance | Dataset | ALNS-Base NV (TD) | Hybrid-Fixed NV (TD) | Hybrid-Rule NV (TD) | Hybrid-DDQN NV (TD) | OR-Tools NV (TD) |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
    
    for idx, row in pivot_df.iterrows():
        dataset, instance = idx
        
        # ALNS-Base
        alns_nv = row[("NV_mean", "ALNS-Base")]
        alns_td = row[("TD_mean", "ALNS-Base")]
        alns_str = f"{alns_nv:.1f} ({alns_td:.1f})" if not pd.isna(alns_nv) else "N/A"
        
        # Hybrid-Fixed
        fixed_nv = row[("NV_mean", "Hybrid-Fixed")]
        fixed_td = row[("TD_mean", "Hybrid-Fixed")]
        fixed_str = f"{fixed_nv:.1f} ({fixed_td:.1f})" if not pd.isna(fixed_nv) else "N/A"
        
        # Hybrid-Rule
        rule_nv = row[("NV_mean", "Hybrid-Rule")]
        rule_td = row[("TD_mean", "Hybrid-Rule")]
        rule_str = f"{rule_nv:.1f} ({rule_td:.1f})" if not pd.isna(rule_nv) else "N/A"
        
        # Hybrid-DDQN
        ddqn_nv = row[("NV_mean", "Hybrid-DDQN")]
        ddqn_td = row[("TD_mean", "Hybrid-DDQN")]
        ddqn_str = f"{ddqn_nv:.1f} ({ddqn_td:.1f})" if not pd.isna(ddqn_nv) else "N/A"
        
        # OR-Tools
        ort_nv = row[("NV_mean", "OR-Tools")]
        ort_td = row[("TD_mean", "OR-Tools")]
        ort_str = f"{ort_nv:.1f} ({ort_td:.1f})" if not pd.isna(ort_nv) else "N/A"
        
        f.write(f"| **{instance}** | {dataset} | {alns_str} | {fixed_str} | {rule_str} | {ddqn_str} | {ort_str} |\n")

print("Generated full benchmark results report successfully!")
