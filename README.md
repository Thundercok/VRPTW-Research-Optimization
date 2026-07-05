# 🚛 NAMI Routing Engine — Production Demo (v1.0.0-release)

A streamlined, production-ready version of the **NAMI Vehicle Routing Problem with Time Windows (VRPTW) Solver**. This branch contains only the core application files optimized for immediate demonstration and deployment in a Windows environment using VS Code or Docker.

---

## 🚀 Quick Start (Single-Command Docker Deployment)

For the fastest way to get the app running, deploy using Docker. The frontend assets are pre-built inside a multi-stage Docker container and served directly by the FastAPI backend. Firebase emulators are bypassed by default in demo mode.

### Prerequisites
* [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) (ensure WSL 2 backend or Hyper-V is enabled)

### Launching the Application
1. Open PowerShell or CMD in the repository root folder.
2. Spin up the container:
   ```powershell
   docker compose up --build
   ```
3. Once uvicorn logs show it is ready, open your web browser and navigate to:
   👉 **[http://localhost:8000](http://localhost:8000)**

---

## 💻 Local Manual Installation (Windows)

If you prefer to run the development server locally on Windows without Docker, follow these steps.

### Prerequisites
* **Python 3.12**: Download from [python.org](https://www.python.org/downloads/). *(Note: Numba and PyTorch are not yet compatible with Python 3.13).*
* **Node.js 20+**: For building frontend assets. Download from [nodejs.org](https://nodejs.org/).
* Recommended: [`uv`](https://github.com/astral-sh/uv) for fast Python package installation.

### Step 1: Install Python Dependencies
Open PowerShell in the root directory:
```powershell
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\Activate.ps1

# Install requirements (specify Torch CPU index to avoid large CUDA downloads)
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
```

### Step 2: Install and Build Frontend Assets
In the same root directory, compile the React and Vite frontend assets:
```powershell
# Install node packages
npm install

# Build the production bundle into dist/
npm run build
```

### Step 3: Run the Local FastAPI Server
With `.venv` active, start uvicorn:
```powershell
python main.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser. The backend will automatically detect the compiled `dist/` directory and serve it statically.

---

## ⚡ Quick CLI Smoke Test

To verify the JIT-compiled optimization solvers work outside the web interface, run a quick 25-customer local search benchmark on a synthetic dataset.

In PowerShell (with `.venv` active):
```powershell
$env:PYTHONPATH="src"
python -m vrptw smoke-test
```
Expected output (resolves in ~5 seconds):
```text
Running synthetic smoke test (nodes=25, distribution=RC)...
ALNS-Base                nv=  3 cost=   648.0 BKS TD N/A NV N/A (0.3s)
Hybrid-Fixed             nv=  3 cost=   639.2 BKS TD N/A NV N/A (1.4s)
Hybrid-Rule              nv=  3 cost=   641.5 BKS TD N/A NV N/A (0.3s)
Hybrid-DDQN              nv=  3 cost=   639.2 BKS TD N/A NV N/A (0.6s)
```

---

## 🖥️ Using the Demo Interface (Guest Mode)

By default, the demo bypasses Firebase credentials and operates in a fully functional offline mode.

1. Navigate to **[http://localhost:8000](http://localhost:8000)**.
2. Click **Open Solver** or **Dispatcher Login** in the navigation header or footer.
3. Click the yellow **Continue as Guest Operator** button.
4. **Load Solomon Data**: Go to the sidebar, select an instance (e.g. `RC101`), and click **Load Dataset**.
5. **Run Optimization**: Configure your fleet vehicle capacity and click the **Run Solver** button to see JIT local search and deep Q-network heuristics plan routes in real time.

---

## 🛠️ VS Code Integration (Windows)

We have provided native VS Code launch configurations to make debugging easy.

1. Open the repository root directory in VS Code.
2. If prompted, install the recommended **Python** and **Docker** extensions.
3. Press `Ctrl + Shift + D` (or click the Run & Debug icon on the sidebar).
4. Select **Run FastAPI Backend (Dev Mode)** from the dropdown and press `F5`.
5. Breakpoints set inside `src/backend` or `src/vrptw` will trigger normally!

---

## 📁 Optimized Project Structure

The demo branch is structured to minimize noise:
```
VRPTW-Research-Optimization/
├── .vscode/
│   └── launch.json                  # VS Code Windows launch debug targets
├── data/
│   └── Solomon/                     # Standard Solomon text instances (pre-loaded)
├── src/
│   ├── vrptw/                       # JIT solver engine (ALNS, Local Search, DDQN)
│   ├── backend/                     # FastAPI backend REST services
│   └── frontend/                    # Single-page web app React components & assets
├── Dockerfile                       # Multi-stage container deployment file
├── docker-compose.yml               # Production single-service Compose configuration
├── main.py                          # Local backend dev server entry point
├── package.json                     # Node/Vite build configurations
├── pyproject.toml                   # Python package declaration
├── requirements.txt                 # Python PIP dependencies
├── rl_alns_dr_v15.safetensors       # Trained model weights for Hybrid-DDQN solver
└── README.md                        # Setup and demonstration instructions
```

---

## ⚙️ Environment Variables Reference

A `.env.example` file is included in the project root. Copy it to `.env` to override configuration defaults:

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_AUTH_BYPASS` | `true` | When `true`, bypasses Firebase Authentication and signs in as an admin Guest automatically. |
| `CORS_ALLOW_ORIGINS` | `*` | List of client origins permitted to fetch from the backend. |
| `SENTRY_DSN` | *(None)* | DSN string to report runtime server errors to Sentry. |
