import os
import shutil
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
combined_dir = os.path.join(ROOT, "data", "combined_sweep")

# Create combined directory
if os.path.exists(combined_dir):
    shutil.rmtree(combined_dir)
os.makedirs(combined_dir)

# 1. Copy Solomon files
solomon_dir = os.path.join(ROOT, "data", "Solomon")
solomon_files = glob.glob(os.path.join(solomon_dir, "*.txt"))
for f in solomon_files:
    shutil.copy(f, combined_dir)

# 2. Copy Gehring & Homberger 200-customer representative files
hg_dir = os.path.join(ROOT, "data", "Gehring_Homberger", "homberger_200_customer_instances")
hg_instances = ["C1_2_1.TXT", "C2_2_1.TXT", "R1_2_1.TXT", "R2_2_1.TXT", "RC1_2_1.TXT", "RC2_2_1.TXT"]
for name in hg_instances:
    src_path = os.path.join(hg_dir, name)
    if os.path.exists(src_path):
        shutil.copy(src_path, combined_dir)
    else:
        print(f"Warning: Could not find H&G file {src_path}")

print(f"Successfully aggregated {len(os.listdir(combined_dir))} files in {combined_dir}")
