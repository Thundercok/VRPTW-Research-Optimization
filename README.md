
# VRPTW Optimization using Hybrid RL-ALNS

This repository focuses on solving the **Vehicle Routing Problem with Time Windows (VRPTW)** through a hybrid approach combining **Reinforcement Learning (RL)** and **Adaptive Large Neighborhood Search (ALNS)**.

The project aims to leverage RL to dynamically select the most effective heuristics within the ALNS framework to optimize delivery routes, minimize travel distance, and satisfy strict time constraints.

---

## 🔬 Research Highlights

* **Methodology**: Integrates a learning agent to adaptively choose 'Destroy' and 'Repair' operators based on the current state of the solution.
* **Performance**: Evaluated against standard **Solomon Benchmark** instances (C, R, and RC types).
* **Components**:
  * **Heuristics Engine**: Implementation of multiple neighborhood search operators.
  * **RL Agent**: Policy-based/Value-based learning for operator selection.
  * **Web Visualization**: Interactive dashboard to analyze routing results and vehicle paths.

---

## 📂 Project Overview

- `vrptw.ipynb`: The main research notebook containing algorithm implementation, training, and evaluation.
- `index.html`, `app.js`, `style.css`: The frontend engine for 2D route visualization.
- `data/`: Contains Solomon benchmark datasets.
- `solomon-parser.js`: Utility to parse standard benchmark files into JSON for the visualization tool.
- `past-reports/`: Academic documentation and research logs.

---

## 🚀 Getting Started

### Algorithm Execution

The core logic is implemented in Python. To run the research experiments:

1. Open `vrptw.ipynb` or `notebook5cf2826d49.ipynb` in Jupyter Notebook or Kaggle.
2. Ensure dependencies like `numpy`, `pandas`, and your RL framework are installed.

### Visualizing Results

To see the optimized routes in action:

1. Open `index.html` in any modern web browser.
2. The interface allows you to load JSON-formatted solution data and view the spatio-temporal distribution of the vehicles.

---

## 🎓 Author

**Huy (Thundercok)** Student at **Ton Duc Thang University (TDTU)** Major: Computer Science / IT

---

## ⚠️ Maintenance Note

*The repository is currently undergoing structural cleanup to better separate research scripts from the visualization frontend.*
