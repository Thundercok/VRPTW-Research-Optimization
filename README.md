# VRPTW Optimization using Hybrid RL-ALNS

This repository focuses on solving the **Vehicle Routing Problem with Time Windows (VRPTW)** through a hybrid approach combining **Reinforcement Learning (RL)** and **Adaptive Large Neighborhood Search (ALNS)**.

The project leverages an RL agent to dynamically select the most effective heuristics within the ALNS framework to optimize delivery routes, minimize travel distance, and satisfy strict time constraints.

---

## Project Structure

```text
VRPTW-RESEARCH-OPTIMIZ...
├── demo/
│   ├── assets/
│   ├── data/
│   └── index.html
├── legacy/
│   ├── data/
│   ├── style.css
│   ├── index.html
│   ├── app.js
│   ├── solomon-parser.js
│   └── hybrid-rl-alns-for-vrptw.log
├── logs/
│   ├── results-v5/
│   └── results-v7/
│       ├── models/
│       ├── benchmark_transfer.csv
│       ├── benchmark.csv
│       ├── nexus_demo.json
│       ├── hybrid-rl-alns-for-vrptw-97d929.log
│       ├── hybrid-rl-alns-for-vrptw-a9b129.log
│       └── dashboard.png
├── past-reports/
│   ├── References/
│   ├── 1233.docx
│   ├── NOTE_NCKH_TDTU_VRPTW_2526.docx
│   ├── notebook5cf2826d49.ipynb
│   ├── 11-2025.pdf
│   └── 1233.pdf
├── .gitignore
├── vrptw.ipynb
└── README.md
```

---

## Research Highlights

* **Methodology** : Integrates a learning agent to adaptively choose 'Destroy' and 'Repair' operators based on the current state of the solution.
* **Performance** : Evaluated against standard Solomon Benchmark instances (C, R, and RC types).
* **Components** :
* **Heuristics Engine** : Implementation of multiple neighborhood search operators.
* **RL Agent** : Policy-based/Value-based learning for operator selection.
* **Web Visualization** : Interactive dashboard located in the** **`demo/` directory to analyze routing results.

---

## Getting Started

### Algorithm Execution

The core logic is implemented in Python. To run the research experiments:

1. Open** **`vrptw.ipynb` or the archived notebooks in** **`past-reports/` using Jupyter or Google Colab.
2. Ensure necessary dependencies (NumPy, Pandas, PyTorch/TensorFlow) are installed.

### Visualizing Results

1. Navigate to the** **`demo/` folder.
2. Open** **`index.html` in a web browser to access the visualization engine.
3. Load the JSON-formatted solution data (e.g., from** **`logs/results-v7/nexus_demo.json`) to view vehicle paths.
