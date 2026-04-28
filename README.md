# VRPTW Research Optimization
> A VRPTW (Vehicle Routing Problem with Time Windows) research and demo system that compares ALNS vs DDQN-ALNS in a web app.

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

> **Pick ONE of the two install paths below (uv OR pip).** Don't run both - they
> create different virtual envs. After installing, always run commands inside the
> activated venv (or via `uv run`).

```bash
# 1) Clone
git clone https://github.com/Thundercok/VRPTW-Research-Optimization.git
cd VRPTW-Research-Optimization

# 2) Copy env template (demo mode works without any keys)
cp .env.example .env       # Windows PowerShell: copy .env.example .env
```

**Option A - uv (recommended, ~30 s install):**

```bash
uv venv .venv --python 3.12
uv pip install -r requirements.txt
uv run python main.py            # uv auto-uses .venv; no activate needed
```

**Option B - plain venv + pip:**

```bash
python -m venv venv
# Activate the venv:
#   Windows PowerShell:  .\venv\Scripts\Activate.ps1
#   Windows cmd:         venv\Scripts\activate.bat
#   Linux / macOS:       source venv/bin/activate
pip install -r requirements.txt
python main.py
```

**Optional - fetch Solomon benchmark files** so you can load `rc101`, `rc205`, etc.:

```bash
python scripts/fetch_solomon.py    # downloads RC1+RC2 into data/solomon/
```

Skip this if you only want the demo - the app ships with a built-in **`demo`**
instance (12 customers around HCMC) that loads instantly. The mirror sites for
Solomon files are flaky; if `fetch_solomon.py` fails just retry later or
download manually from <https://www.sintef.no/projectweb/top/vrptw/>.

Open <http://127.0.0.1:8000/> in a browser. The startup log should print
something like:

```text
[INFO] vrptw.backend: Firebase Admin disabled - demo bypass ON. ...
[INFO] services.solver_service: Torch device: GPU (NVIDIA ..., CUDA 12.6, 2.x.y+cu126)
[INFO] services.solver_service: DDQN transfer weights loaded from .../model/rl_alns_transfer.safetensors
```

That confirms three things at once: backend is up, GPU/CPU was picked correctly,
and the **trained DDQN policy** is loaded from `model/rl_alns_transfer.safetensors`.

### Optional: enable auth + Firestore persistence
1. Create a Firebase project and download a service-account JSON.
2. Drop it under `secrets/firebase-adminsdk.json` (the folder is gitignored).
3. Uncomment `FIREBASE_SERVICE_ACCOUNT_PATH` in `.env` and restart `python main.py`.

## Usage
1. Open `http://127.0.0.1:8000/` for the landing page, or `http://127.0.0.1:8000/app.html`
   to jump straight into the demo. Hit the floating **?** button or
   <kbd>Shift</kbd>+<kbd>?</kbd> for an in-app tour.
2. (Optional) Log in - skipped automatically when running in demo mode.
3. Choose mode:
   - `Sample`: loads a Solomon instance. Default is the built-in `demo` mini sample
     (12 customers, no extra download). Type any other name (e.g. `rc101`) once
     you have run `scripts/fetch_solomon.py`.
   - `Real Data`: upload/import your own customers (CSV/Excel) or click map points.
4. Ensure one depot (`demand = 0`) and at least one customer with capacity + time windows.
5. Click **Run Model** to compare DDQN-ALNS vs ALNS side-by-side.

Useful endpoints:
- `GET /api/health` - `{status, firebase_enabled, demo_auth_bypass, demo_mode, torch, model}`.
  The `model` field tells you whether the trained DDQN weights were found and loaded.
- `GET /api/config` - public observability config the SPA loads on boot.
- `GET /api/solomon?name=demo` - built-in mini benchmark (no files required).

### Sample input file
A ready-to-import customer file lives at:
- `docs/samples/customers_sample.csv` (open in any text editor)
- `docs/samples/customers_sample.xlsx` (formatted Excel workbook)

Both contain the same 13 stops (1 depot + 12 customers around HCMC) with
`name, address, lat, lng, demand, ready, due, service` columns. In the demo,
switch to **Real Data** mode and drag-drop the file into the import area.

### Verifying the trained model is in use
Three quick checks:

1. **Startup log** prints `DDQN transfer weights loaded from .../rl_alns_transfer.safetensors`.
2. `GET /api/health` returns `"model": {"available": true, "loaded_once": true, "loaded_path": "..."}` after the first run.
3. Run `python scripts/smoke_model_loaded.py` - this loads the safetensors and
   compares against a zeroed Q-network on the same seed. The Q-net norm must
   differ (~12 vs 0).

### GPU acceleration (optional)
The DDQN policy auto-uses CUDA when a CUDA-enabled PyTorch wheel is installed.
The default `requirements.txt` ships the CPU-only build to keep the install
small. To switch to a GPU build:

```bash
# Auto-detect CUDA via nvidia-smi and reinstall torch
python scripts/install_torch_gpu.py

# Or force a specific build (cu118 / cu121 / cu124 / cu126)
python scripts/install_torch_gpu.py --cuda 124
```

Restart `python main.py` afterwards. The startup log will print
`Torch device: GPU (NVIDIA ..., CUDA 12.x, 2.x.y+cu1xx)` and the demo's
**Loading panel** shows `Compute: GPU - <model>` while a job is running. For
the small Q-network used here the speed-up is typically modest (a few percent),
but it does keep tensors off the CPU bus when batching.

## Production hardening
The backend is preconfigured with safe defaults that you can tighten via
environment variables (see `.env.example` for the full list):

| Concern        | Variable(s)                                | Default       |
|----------------|--------------------------------------------|---------------|
| Auth bypass    | `DEMO_AUTH_BYPASS`                         | `true` (demo) |
| CORS origins   | `CORS_ALLOW_ORIGINS`                       | `*`           |
| Rate limits    | `RATE_LIMIT_*` (slowapi, in-memory)        | sensible defaults |
| Backend errors | `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`  | disabled      |
| Frontend errors| `SENTRY_FRONTEND_DSN`                      | disabled      |
| Analytics      | `PLAUSIBLE_DOMAIN` _or_ `POSTHOG_PUBLIC_KEY` | disabled    |

Set `DEMO_AUTH_BYPASS=false` and provide Firebase credentials before exposing
the API to the public internet.

## Data Formats
- **Input sample (committed):** `docs/samples/customers_sample.csv` / `customers_sample.xlsx`
- **Legacy import example:** `logs/customers_import_test.csv`
- **Benchmark summary:** `logs/benchmark_clean.csv`
- **Transfer benchmark:** `logs/benchmark_transfer.csv`
- **Run log:** `logs/hybrid-rl-alns-for-vrptw.log`
- **Dashboard payload:** `logs/nexus_demo.json`

## Contributing
1. Fork the repository.
2. Create a feature branch.
3. Add tests or smoke checks for your change.
4. Open a Pull Request with a clear summary and test steps.