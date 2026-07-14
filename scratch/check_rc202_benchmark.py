import pandas as pd
df = pd.read_csv("results/clean_v3/solomon_wide_horizon/benchmark_clean.csv")
rc202_df = df[df['Instance'] == 'RC202']
print("=== RC202 results from solomon_wide_horizon/benchmark_clean.csv ===")
print(rc202_df.to_string())
