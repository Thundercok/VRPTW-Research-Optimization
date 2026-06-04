import os
import pandas as pd

paths = [
    "docs/logs/results-v17/benchmark_main_v17.csv",
    "docs/logs/results-v17/benchmark_dr_v17.csv",
    "docs/logs/results-v9.8/results/benchmark_clean.csv",
    "docs/logs/results-v9.7.1/results/benchmark_clean.csv",
    "docs/logs/benchmark_clean.csv",
    "results/ultimate-phase4-verification/benchmark_clean.csv"
]

for p in paths:
    if os.path.exists(p):
        try:
            df = pd.read_csv(p)
            n_unique_inst = df["Instance"].nunique()
            print(f"Path: {p} -> Rows: {len(df)}, Unique instances: {n_unique_inst}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Algorithms: {list(df['Algorithm'].unique()) if 'Algorithm' in df else 'N/A'}")
        except Exception as e:
            print(f"Path: {p} -> Error: {e}")
    else:
        print(f"Path: {p} -> NOT FOUND")
