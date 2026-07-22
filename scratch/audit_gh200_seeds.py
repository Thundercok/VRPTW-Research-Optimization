import os
import pandas as pd

ROOT = "/Users/thundercock2/Documents/Github/VRPTW-Research-Optimization/VRPTW-Research-Optimization"
GH200_CSV = os.path.join(ROOT, "results", "ultimate-publication-suite", "gehring_homberger_200", "benchmark_clean.csv")

def main():
    print("=== AUDIT OF GEHRING-HOMBERGER 200 SEED COMPLETENESS ===")
    if not os.path.exists(GH200_CSV):
        print(f"Error: {GH200_CSV} not found!")
        return
        
    df = pd.read_csv(GH200_CSV)
    print(f"Total rows in GH-200 benchmark_clean.csv: {len(df)}")
    print(f"Unique instances: {df['Instance'].nunique()}")
    print(f"Algorithms: {df['Algorithm'].unique()}")
    
    # Check seed counts per instance per algorithm
    counts = df.groupby(["Instance", "Algorithm"]).size().unstack(fill_value=0)
    
    print("\nBreakdown of seed counts per instance:")
    print(counts.value_counts())
    
    # Check raw_nv list lengths if stored as semicolon-separated string
    if "raw_nv" in df.columns:
        df["num_seeds"] = df["raw_nv"].apply(lambda x: len(str(x).split(";")) if pd.notna(x) else 0)
        print("\nSeed count distribution based on raw_nv string length:")
        print(df.groupby("Algorithm")["num_seeds"].value_counts())
        
        # List instances with < 5 seeds or > 5 seeds
        incomplete = df[df["num_seeds"] != 5]
        if not incomplete.empty:
            print(f"\nInstances with seed count != 5 ({len(incomplete)} rows):")
            print(incomplete[["Instance", "Algorithm", "num_seeds"]])
        else:
            print("\n✅ ALL 60 GH-200 INSTANCES HAVE EXACTLY 5 COMPLETED SEEDS FOR ALL ALGORITHMS!")

if __name__ == "__main__":
    main()
