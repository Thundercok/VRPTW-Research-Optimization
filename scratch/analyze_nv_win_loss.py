import os
import pandas as pd
import numpy as np

ROOT = "/Users/thundercock2/Documents/Github/VRPTW-Research-Optimization/VRPTW-Research-Optimization"
OUTPUT_BASE = os.path.join(ROOT, "results", "ultimate-publication-suite")
SHARDS = ["solomon_clustered", "solomon_short_horizon", "solomon_wide_horizon", "gehring_homberger_200"]

def main():
    print("=== PER-SEED NV WIN/TIE/LOSS BREAKDOWN (N=310 OBSERVATIONS) ===")
    
    dfs = []
    for s in SHARDS:
        clean_path = os.path.join(OUTPUT_BASE, s, "benchmark_clean.csv")
        if os.path.exists(clean_path):
            dfs.append(pd.read_csv(clean_path))
            
    if not dfs:
        print("Error: ultimate-publication-suite files not found!")
        return
        
    df = pd.concat(dfs, ignore_index=True)
    
    # Pair ALNS-Base vs Hybrid-DDQN
    alns = df[df["Algorithm"] == "ALNS-Base"].sort_values("Instance")
    ddqn = df[df["Algorithm"] == "Hybrid-DDQN"].sort_values("Instance")
    
    common = sorted(list(set(alns["Instance"]) & set(ddqn["Instance"])))
    print(f"Common instances found: {len(common)}")
    
    wins = 0    # Hybrid-DDQN NV < ALNS-Base NV
    ties = 0    # Hybrid-DDQN NV == ALNS-Base NV
    losses = 0  # Hybrid-DDQN NV > ALNS-Base NV
    
    win_instances = []
    loss_instances = []
    
    total_pairs = 0
    
    for inst in common:
        ra = alns[alns["Instance"] == inst].iloc[0]
        rb = ddqn[ddqn["Instance"] == inst].iloc[0]
        
        raw_a = [float(x) for x in str(ra["raw_nv"]).split(";")]
        raw_b = [float(x) for x in str(rb["raw_nv"]).split(";")]
        
        n_pairs = min(len(raw_a), len(raw_b))
        for i in range(n_pairs):
            nv_a = raw_a[i]
            nv_b = raw_b[i]
            total_pairs += 1
            
            if nv_b < nv_a:
                wins += 1
                win_instances.append((inst, i+1, nv_a, nv_b))
            elif nv_b == nv_a:
                ties += 1
            else:
                losses += 1
                loss_instances.append((inst, i+1, nv_a, nv_b))
                
    print(f"\nTotal paired seed comparisons: {total_pairs}")
    print(f"  • Hybrid-DDQN WINS (NV_ddqn < NV_alns): {wins} ({wins/total_pairs*100:.1f}%)")
    print(f"  • Hybrid-DDQN TIES (NV_ddqn == NV_alns): {ties} ({ties/total_pairs*100:.1f}%)")
    print(f"  • Hybrid-DDQN LOSSES (NV_ddqn > NV_alns): {losses} ({losses/total_pairs*100:.1f}%)")
    
    if wins > 0:
        print("\nSample Wins (Hybrid-DDQN reduced NV by 1+ vehicle):")
        for w in win_instances[:10]:
            print(f"  - {w[0]} (run {w[1]}): ALNS={int(w[2])} vs Hybrid={int(w[3])}")
            
    if losses > 0:
        print("\nSample Losses:")
        for l in loss_instances[:10]:
            print(f"  - {l[0]} (run {l[1]}): ALNS={int(l[2])} vs Hybrid={int(l[3])}")
    else:
        print("\n✅ Hybrid-DDQN HAD ZERO LOSSES ACROSS ALL 310 SEED-PAIRS!")

if __name__ == "__main__":
    main()
