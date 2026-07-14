import pandas as pd
df = pd.read_csv("results/clean_v3/solomon_wide_horizon/benchmark_clean.csv")
rc2_df = df[df['Instance'].str.startswith('RC2')]
print("=== All RC2 Results in solomon_wide_horizon ===")
print(rc2_df[['Instance', 'Algorithm', 'NV_mean', 'TD_mean', 'Gap%']].to_string(index=False))
