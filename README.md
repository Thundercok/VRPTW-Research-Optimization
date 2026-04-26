# VRPTW Research Optimization
> A VRPTW (Vehicle Routing Problem with Time Windows) research and demo system that compares ALNS vs DDQN-ALNS in a web app.

![Demo](docs/readme-assets/demo.gif)

## About The Project
- **Problem solved:** Helps evaluate and demonstrate VRPTW route optimization with realistic constraints (capacity + time windows).
- **Core features:** Interactive web demo, CSV/Excel import, map-based route visualization, ALNS vs DDQN-ALNS comparison, benchmark analysis artifacts.
- **Tech stack:**  
  ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
  ![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
  ![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
  ![Numba](https://img.shields.io/badge/Numba-00A3E0?style=for-the-badge&logo=numba&logoColor=white)
  ![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white)
  ![Firebase Admin](https://img.shields.io/badge/Firebase%20Admin-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)

## Project Structure
```text
src/
  backend/        # FastAPI API, auth, job orchestration, solver integration
  frontend/       # Static web UI (served by FastAPI)
docs/
  report-draft1.tex
  vrptw_clean.py  # Research solver source of truth
logs/
  benchmark_clean.csv
  benchmark_transfer.csv
  hybrid-rl-alns-for-vrptw.log
  nexus_demo.json
  image/
model/
  rl_alns_transfer.safetensors
```

## Getting Started

### Prerequisites
- Python `>=3.11,<3.13` (the project is pinned to 3.12 - PyTorch + Numba do not yet support 3.14).
- (Recommended) [`uv`](https://docs.astral.sh/uv/) for fast, reproducible installs.

### Quick start (newbie clone)

```bash
# 1) Clone
git clone https://github.com/Thundercok/VRPTW-Research-Optimization.git
cd VRPTW-Research-Optimization

# 2) Copy env template (demo mode works without any keys)
cp .env.example .env       # Windows PowerShell: copy .env.example .env

# 3a) Option A - uv (recommended)
uv venv .venv --python 3.12
uv pip install -r requirements.txt

# 3b) Option B - plain venv + pip
python -m venv venv
# Windows:    venv\Scripts\activate
# Linux/mac:  source venv/bin/activate
pip install -r requirements.txt

# 4) (Optional) Fetch Solomon benchmark data so the "Sample" button works
python scripts/fetch_solomon.py    # downloads RC1+RC2 into data/solomon/

# 5) Run the project (single entry point)
python main.py
```

Open `http://127.0.0.1:8000/` in a browser. The startup log should print
`Firebase Admin disabled - VRPTW demo solver still works at /` when no
credentials are provided. That is expected: the VRPTW demo, Solomon loader,
solver comparison, and analysis endpoints all run in **demo mode** without
Firebase.

### Optional: enable auth + Firestore persistence
1. Create a Firebase project and download a service-account JSON.
2. Drop it under `secrets/firebase-adminsdk.json` (the folder is gitignored).
3. Uncomment `FIREBASE_SERVICE_ACCOUNT_PATH` in `.env` and restart `python main.py`.

## Usage
1. (Optional) Log in - skipped automatically when running in demo mode.
2. Choose mode:
   - `Sample`: loads a Solomon instance (default `rc101`).
   - `Real Data`: upload/import your own customers (CSV/Excel) or click map points.
3. Ensure one depot (`demand = 0`) and at least one customer with capacity + time windows.
4. Click **Run Model** to compare DDQN-ALNS vs ALNS side-by-side.

Health check: `GET http://127.0.0.1:8000/api/health` returns `{ "status": "ok", "firebase_enabled": true|false }`.

## Data Formats
- **Input CSV example:** `logs/customers_import_test.csv`
- **Benchmark summary:** `logs/benchmark_clean.csv`
- **Transfer benchmark:** `logs/benchmark_transfer.csv`
- **Run log:** `logs/hybrid-rl-alns-for-vrptw.log`
- **Dashboard payload:** `logs/nexus_demo.json`

## Contributing
1. Fork the repository.
2. Create a feature branch.
3. Add tests or smoke checks for your change.
4. Open a Pull Request with a clear summary and test steps.