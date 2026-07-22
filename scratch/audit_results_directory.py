import os
import pandas as pd

ROOT = "/Users/thundercock2/Documents/Github/VRPTW-Research-Optimization/VRPTW-Research-Optimization"
OUTPUT_BASE = os.path.join(ROOT, "results", "ultimate-publication-suite")

def main():
    print("=== AUDIT OF RESULTS IN ULTIMATE-PUBLICATION-SUITE ===")
    
    total_instances = 0
    total_rows = 0
    
    for sub in sorted(os.listdir(OUTPUT_BASE)):
        sub_dir = os.path.join(OUTPUT_BASE, sub)
        if not os.path.isdir(sub_dir):
            continue
        clean_csv = os.path.join(sub_dir, "benchmark_clean.csv")
        if os.path.exists(clean_csv):
            df = pd.read_csv(clean_csv)
            n_inst = df["Instance"].nunique()
            n_rows = len(df)
            total_instances += n_inst
            total_rows += n_rows
            print(f"  • {sub:25s}: {n_inst:3d} unique instances, {n_rows:3d} total rows")
        else:
            print(f"  • {sub:25s}: No benchmark_clean.csv")
            
    print(f"\nTOTAL UNIQUE INSTANCES ACROSS ALL DIRECTORIES: {total_instances}")

if __name__ == "__main__":
    main()
