#!/usr/bin/env bash
set -e

OUTPUT_BASE="results/ultimate-publication-suite"
mkdir -p "$OUTPUT_BASE"

echo "=========================================================================="
echo " KICH HOAT DOT BENCHMARK SAN XUAT TONG LUC PHUCO VU CONG BO QUOC TE       "
echo " Cau hinh: 5 Runs | 5000 Main Iters | 1000 Patience | 300 Polish Iters"
echo "=========================================================================="

# Dam bao giu cho may khong roi vao trang thai ngu dong cuc bo khi giai toan dem
if command -v caffeinate &> /dev/null; then
    caffeinate -dism &
    CAFF_PID=$!
    trap 'kill $CAFF_PID 2>/dev/null || true' EXIT
fi

# ── SHARD 1: HO BAI TOAN PHAN CUM DIA LY (C1 SUITE & C2 SUITE) ──
echo "--> Dang thuc thi Shard 1: Clustered Instances (C1 & C2)..."
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Solomon \
  --output-dir "$OUTPUT_BASE/solomon_clustered" \
  --runs 5 \
  --alns-iters 5000 \
  --hybrid-iters 5000 \
  --early-stop 1000 \
  --polish-iters 300 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances C101 C102 C103 C104 C105 C106 C107 C108 C109 C201 C202 C203 C204 C205 C206 C207 C208

# ── SHARD 2: HO BAI TOAN NGAU NHIEN VA HON HOP NGAN (R1 & RC1 SUITE) ──
echo "--> Dang thuc thi Shard 2: Random/Mixed Short-Horizon (R1 & RC1)..."
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Solomon \
  --output-dir "$OUTPUT_BASE/solomon_short_horizon" \
  --runs 5 \
  --alns-iters 5000 \
  --hybrid-iters 5000 \
  --early-stop 1000 \
  --polish-iters 300 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances R101 R102 R103 R104 R105 R106 R107 R108 R109 R110 R111 R112 RC101 RC102 RC103 RC104 RC105 RC106 RC107 RC108

# ── SHARD 3: HO BAI TOAN NGAU NHIEN VA HON HOP DAI KHUNG KHIEP (R2 & RC2 SUITE) ──
echo "--> Dang thuc thi Shard 3: Random/Mixed Wide-Horizon (R2 & RC2)..."
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Solomon \
  --output-dir "$OUTPUT_BASE/solomon_wide_horizon" \
  --runs 5 \
  --alns-iters 5000 \
  --hybrid-iters 5000 \
  --early-stop 1000 \
  --polish-iters 300 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances R201 R202 R203 R204 R205 R206 R207 R208 R209 R210 R211 RC201 RC202 RC203 RC204 RC205 RC206 RC207 RC208

# ── SHARD 4: DAI THANH PHO GEHRING & HOMBERGER 200 KHACH ──
echo "--> Dang thuc thi Shard 4: Gehring & Homberger Large-Scale (200 Customers)..."
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Gehring_Homberger/homberger_200_customer_instances \
  --output-dir "$OUTPUT_BASE/gehring_homberger_200" \
  --runs 5 \
  --alns-iters 600 \
  --hybrid-iters 600 \
  --early-stop 150 \
  --polish-iters 50 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances C1_2_1 C2_2_1 R1_2_1 R2_2_1 RC1_2_1 RC2_2_1

echo "=========================================================================="
echo " TOAN BO SUITE BENCHMARK 56+6 INSTANCES DA HOAN THANH XUAT SAC            "
echo " Du lieu sach da nam an toan tai thu muc: $OUTPUT_BASE                    "
echo "=========================================================================="
