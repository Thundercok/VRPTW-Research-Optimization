import os
import pandas as pd

# Define paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ortools_csv = os.path.join(ROOT, "results", "ortools_only_sweep", "benchmark_clean.csv")
suite_dir = os.path.join(ROOT, "results", "ultimate-publication-suite")

if not os.path.exists(ortools_csv):
    raise FileNotFoundError(f"OR-Tools sweep results not found at: {ortools_csv}")

# Load new OR-Tools results
or_df = pd.read_csv(ortools_csv)
or_df = or_df[or_df["Algorithm"] == "OR-Tools"]

shards = ["solomon_clustered", "solomon_short_horizon", "solomon_wide_horizon", "gehring_homberger_200"]

for shard in shards:
    shard_dir = os.path.join(suite_dir, shard)
    for filename in ["benchmark_clean.csv", "benchmark_checkpoint.csv"]:
        filepath = os.path.join(shard_dir, filename)
        if not os.path.exists(filepath):
            continue
        
        df = pd.read_csv(filepath)
        
        # Remove existing OR-Tools rows for clean replacement
        df = df[df["Algorithm"] != "OR-Tools"]
        
        # Find unique instances in this shard file
        instances = df["Instance"].unique()
        
        # Extract new OR-Tools results for these instances
        new_or = or_df[or_df["Instance"].isin(instances)]
        
        # Concatenate and sort
        merged_df = pd.concat([df, new_or], ignore_index=True)
        
        # Keep consistent order: Dataset, Instance, Algorithm
        merged_df["Algorithm"] = pd.Categorical(
            merged_df["Algorithm"], 
            categories=["OR-Tools", "ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"], 
            ordered=True
        )
        merged_df = merged_df.sort_values(by=["Dataset", "Instance", "Algorithm"]).reset_index(drop=True)
        
        # Save back
        merged_df.to_csv(filepath, index=False)
        print(f"Updated {filepath}: total rows={len(merged_df)}, OR-Tools rows={len(new_or)}")
