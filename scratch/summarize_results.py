import os
import glob
import pandas as pd
import numpy as np

OUTPUT_BASE = "results/clean_v3"

shards = {
    'Solomon Clustered': f"{OUTPUT_BASE}/solomon_clustered/*.csv",
    'Solomon Short-Horizon': f"{OUTPUT_BASE}/solomon_short_horizon/*.csv",
    'Solomon Wide-Horizon': f"{OUTPUT_BASE}/solomon_wide_horizon/*.csv",
    'H200 C1': f"{OUTPUT_BASE}/gehring_homberger_200/c1/*.csv",
    'H200 C2': f"{OUTPUT_BASE}/gehring_homberger_200/c2/*.csv",
    'H200 R1': f"{OUTPUT_BASE}/gehring_homberger_200/r1/*.csv",
    'H200 R2': f"{OUTPUT_BASE}/gehring_homberger_200/r2/*.csv",
    'H200 RC1': f"{OUTPUT_BASE}/gehring_homberger_200/rc1/*.csv",
    'H200 RC2': f"{OUTPUT_BASE}/gehring_homberger_200/rc2/*.csv",
    'H400': f"{OUTPUT_BASE}/gehring_homberger_400/*.csv",
    'H600': f"{OUTPUT_BASE}/gehring_homberger_600/*.csv",
    'H800': f"{OUTPUT_BASE}/gehring_homberger_800/*.csv",
    'H1000': f"{OUTPUT_BASE}/gehring_homberger_1000/*.csv",
}

print("=== SUMMARY OF ALL SWEEP SHARDS ===")
for shard_name, pattern in shards.items():
    files = glob.glob(pattern)
    clean_files = [f for f in files if "clean.csv" in f]
    ckpt_files = [f for f in files if "checkpoint.csv" in f]
    
    file_to_parse = None
    status = "NOT STARTED"
    if clean_files:
        file_to_parse = clean_files[0]
        status = "COMPLETED"
    elif ckpt_files:
        file_to_parse = ckpt_files[0]
        status = "PARTIAL"
        
    if file_to_parse is None:
        print(f"  {shard_name:<25}: NOT STARTED")
        continue
        
    try:
        df = pd.read_csv(file_to_parse)
        if df.empty:
            print(f"  {shard_name:<25}: {status} (Empty)")
            continue
            
        # The CSV has columns: Instance, Algorithm, NV_mean, TD_mean, Gap%, Time_s
        # Let's aggregate by Algorithm and compute mean of these columns across all instances in the shard
        agg = df.groupby('Algorithm').agg({
            'NV_mean': 'mean',
            'TD_mean': 'mean',
            'Gap%': 'mean',
            'Time_s': 'mean'
        }).reset_index()
        
        print(f"\n  {shard_name:<25} ({status}, {df['Instance'].nunique()} instances):")
        for _, row in agg.iterrows():
            print(f"    - {row['Algorithm']:<15}: NV={row['NV_mean']:.2f}, TD={row['TD_mean']:.2f}, TD_Gap={row['Gap%']:.2f}%, Time={row['Time_s']:.1f}s")
            
    except Exception as e:
        print(f"  {shard_name:<25}: {status} (Error parsing: {e})")
print("\n==================================")
