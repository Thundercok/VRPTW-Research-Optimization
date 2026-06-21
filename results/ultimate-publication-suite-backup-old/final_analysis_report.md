# Ultimate Publication Suite - Final Analysis Report
Generated on: 2026-06-13 20:27:20

## Solomon Instances Summary (N = 56)
| Subgroup | Metric | OR-Tools | ALNS-Base | Hybrid-Fixed | Hybrid-Rule | Hybrid-DDQN |
|---|---|---|---|---|---|---|
| C1 | NV | 10.00 | 10.00 | 10.00 | 10.00 | 10.00 |
| C2 | NV | 3.00 | 3.00 | 3.00 | 3.00 | 3.00 |
| R1 | NV | 14.25 | 12.48 | 12.25 | 12.25 | 12.25 |
| R2 | NV | 5.45 | 3.01 | 2.83 | 2.82 | 2.82 |
| RC1 | NV | 14.12 | 12.04 | 11.80 | 11.75 | 11.75 |
| RC2 | NV | 6.38 | 3.38 | 3.25 | 3.25 | 3.25 |
| C1 | TD | 840.25 | 828.38 | 828.38 | 828.38 | 828.38 |
| C2 | TD | 593.73 | 594.82 | 590.11 | 589.86 | 589.86 |
| R1 | TD | 1230.80 | 1204.84 | 1204.09 | 1200.43 | 1200.23 |
| R2 | TD | 911.66 | 939.82 | 954.35 | 952.40 | 951.95 |
| RC1 | TD | 1459.11 | 1373.89 | 1366.33 | 1368.17 | 1367.43 |
| RC2 | TD | 1038.93 | 1114.34 | 1136.80 | 1133.99 | 1132.57 |
| C1 | Time | 15.18 | 27.21 | 35.91 | 29.53 | 47.63 |
| C2 | Time | 15.00 | 11.56 | 19.21 | 17.88 | 26.12 |
| R1 | Time | 15.17 | 36.45 | 63.07 | 62.89 | 73.39 |
| R2 | Time | 15.15 | 11.77 | 53.74 | 40.54 | 46.49 |
| RC1 | Time | 15.05 | 37.36 | 57.96 | 42.78 | 49.65 |
| RC2 | Time | 15.01 | 18.31 | 37.91 | 31.45 | 36.24 |

### Solomon Wilcoxon Hypothesis Testing
| Test Comparison | Metric | p-value |
|---|---|---|
| Hybrid-DDQN vs ALNS-Base | NV | 2.8110e-03 |
| Hybrid-DDQN vs ALNS-Base | TD | 1.5112e-02 |
| Hybrid-DDQN vs Hybrid-Rule | NV | Identical |
| Hybrid-DDQN vs Hybrid-Rule | TD | 1.3163e-04 |
| Hybrid-DDQN vs OR-Tools | NV | 4.0497e-08 |
| Hybrid-DDQN vs OR-Tools | TD | 4.4811e-01 |


## Homberger 200 Summary (Complete: 60)
| Subgroup | Metric | OR-Tools | ALNS-Base | Hybrid-Fixed | Hybrid-Rule | Hybrid-DDQN |
|---|---|---|---|---|---|---|
| C1 | NV | 20.40 | 19.10 | 18.98 | 18.90 | 18.90 |
| C2 | NV | 8.00 | 6.00 | 6.00 | 6.00 | 6.00 |
| R1 | NV | 20.70 | 18.30 | 18.20 | 18.20 | 18.20 |
| R2 | NV | 9.00 | 4.16 | 4.10 | 4.10 | 4.10 |
| RC1 | NV | 19.50 | 18.70 | 18.20 | 18.10 | 18.02 |
| RC2 | NV | 8.50 | 4.56 | 4.50 | 4.50 | 4.50 |
| C1 | TD | 2855.48 | 2848.43 | 2746.23 | 2740.60 | 2735.88 |
| C2 | TD | 1947.23 | 1885.23 | 1840.84 | 1836.54 | 1834.55 |
| R1 | TD | 3918.77 | 3971.15 | 3813.13 | 3745.70 | 3720.03 |
| R2 | TD | 2831.79 | 3065.35 | 2972.80 | 2964.86 | 2951.52 |
| RC1 | TD | 3528.11 | 3478.03 | 3492.66 | 3455.49 | 3438.08 |
| RC2 | TD | 2485.60 | 2659.12 | 2580.55 | 2559.31 | 2548.61 |
| C1 | Time | 15.66 | 25.45 | 42.08 | 42.59 | 51.69 |
| C2 | Time | 15.23 | 17.25 | 36.75 | 35.92 | 38.63 |
| R1 | Time | 15.30 | 31.84 | 48.28 | 47.29 | 51.47 |
| R2 | Time | 15.31 | 10.19 | 39.83 | 39.73 | 43.81 |
| RC1 | Time | 15.63 | 34.45 | 52.22 | 51.63 | 45.59 |
| RC2 | Time | 15.31 | 20.13 | 51.92 | 43.87 | 42.58 |

### Homberger 200 Wilcoxon Hypothesis Testing
| Test Comparison | Metric | p-value |
|---|---|---|
| Hybrid-DDQN vs ALNS-Base | NV | 5.2067e-04 |
| Hybrid-DDQN vs ALNS-Base | TD | 1.3742e-07 |
| Hybrid-DDQN vs Hybrid-Rule | NV | 3.1731e-01 |
| Hybrid-DDQN vs Hybrid-Rule | TD | 2.0779e-07 |
| Hybrid-DDQN vs OR-Tools | NV | 1.6829e-11 |
| Hybrid-DDQN vs OR-Tools | TD | 9.6267e-03 |


## Homberger 400 Summary (Complete: 24)
| Subgroup | Metric | OR-Tools | ALNS-Base | Hybrid-Fixed | Hybrid-Rule | Hybrid-DDQN |
|---|---|---|---|---|---|---|
| C1 | NV | 48.25 | 37.83 | 37.25 | 37.25 | 37.25 |
| C2 | NV | 30.50 | 12.17 | 12.00 | 12.00 | 12.00 |
| R1 | NV | 45.25 | 37.00 | 37.00 | 37.00 | 37.00 |
| R2 | NV | 27.25 | 8.25 | 8.00 | 8.00 | 8.00 |
| RC1 | NV | 44.00 | 37.25 | 36.42 | 36.25 | 36.25 |
| RC2 | NV | 26.75 | 10.09 | 9.75 | 9.75 | 9.50 |
| C1 | TD | 10651.61 | 8318.05 | 7567.55 | 7425.75 | 7324.67 |
| C2 | TD | 7669.79 | 4214.86 | 3991.82 | 3964.81 | 3937.76 |
| R1 | TD | 11787.84 | 10319.04 | 9645.84 | 9525.16 | 9390.81 |
| R2 | TD | 9907.61 | 7421.34 | 7270.68 | 7167.19 | 7139.41 |
| RC1 | TD | 10290.73 | 9006.77 | 8837.10 | 8696.34 | 8627.71 |
| RC2 | TD | 7854.81 | 5706.12 | 5451.56 | 5413.83 | 5520.25 |
| C1 | Time | 15.20 | 130.03 | 197.78 | 315.22 | 304.55 |
| C2 | Time | 15.22 | 79.45 | 206.43 | 224.35 | 312.12 |
| R1 | Time | 15.08 | 153.00 | 218.65 | 238.95 | 257.15 |
| R2 | Time | 15.03 | 58.07 | 177.47 | 171.53 | 174.78 |
| RC1 | Time | 15.00 | 135.62 | 174.38 | 160.83 | 146.30 |
| RC2 | Time | 15.03 | 84.60 | 185.05 | 158.50 | 136.97 |

### Homberger 400 Wilcoxon Hypothesis Testing
| Test Comparison | Metric | p-value |
|---|---|---|
| Hybrid-DDQN vs ALNS-Base | NV | 3.2835e-03 |
| Hybrid-DDQN vs ALNS-Base | TD | 6.5565e-06 |
| Hybrid-DDQN vs Hybrid-Rule | NV | 3.1731e-01 |
| Hybrid-DDQN vs Hybrid-Rule | TD | 6.9217e-04 |
| Hybrid-DDQN vs OR-Tools | NV | 1.8001e-05 |
| Hybrid-DDQN vs OR-Tools | TD | 1.1921e-07 |


## Homberger 600 Summary (Complete: 12)
| Subgroup | Metric | OR-Tools | ALNS-Base | Hybrid-Fixed | Hybrid-Rule | Hybrid-DDQN |
|---|---|---|---|---|---|---|
| C1 | NV | 94.00 | 59.66 | 58.50 | 58.50 | 58.50 |
| C2 | NV | 56.50 | 18.84 | 18.16 | 18.00 | 18.00 |
| R1 | NV | 99.00 | 57.00 | 57.00 | 57.00 | 57.00 |
| R2 | NV | 60.00 | 11.50 | 11.00 | 11.00 | 11.00 |
| RC1 | NV | 79.50 | 57.16 | 55.50 | 55.50 | 55.50 |
| RC2 | NV | 47.00 | 15.83 | 15.50 | 15.50 | 15.00 |
| C1 | TD | 29763.18 | 16174.10 | 14885.28 | 14731.23 | 14503.58 |
| C2 | TD | 22409.66 | 8522.74 | 7933.49 | 7859.02 | 7745.58 |
| R1 | TD | 35503.63 | 24322.38 | 22497.12 | 22195.42 | 22091.11 |
| R2 | TD | 29948.08 | 18298.28 | 18250.96 | 17974.93 | 17898.25 |
| RC1 | TD | 27779.00 | 18638.92 | 18903.87 | 18538.52 | 18276.40 |
| RC2 | TD | 23345.55 | 13080.59 | 12497.17 | 12405.74 | 12584.33 |
| C1 | Time | 15.25 | 207.45 | 406.05 | 410.90 | 403.30 |
| C2 | Time | 15.25 | 211.35 | 387.40 | 433.80 | 418.15 |
| R1 | Time | 15.30 | 336.70 | 573.05 | 519.70 | 497.50 |
| R2 | Time | 15.30 | 178.85 | 293.25 | 315.35 | 289.70 |
| RC1 | Time | 15.10 | 334.35 | 340.25 | 226.00 | 204.05 |
| RC2 | Time | 15.05 | 249.20 | 404.10 | 341.80 | 255.30 |

### Homberger 600 Wilcoxon Hypothesis Testing
| Test Comparison | Metric | p-value |
|---|---|---|
| Hybrid-DDQN vs ALNS-Base | NV | 7.8125e-03 |
| Hybrid-DDQN vs ALNS-Base | TD | 2.4414e-03 |
| Hybrid-DDQN vs Hybrid-Rule | NV | 1.0000e+00 |
| Hybrid-DDQN vs Hybrid-Rule | TD | 4.1992e-02 |
| Hybrid-DDQN vs OR-Tools | NV | 4.8828e-04 |
| Hybrid-DDQN vs OR-Tools | TD | 4.8828e-04 |


## Homberger 800 Summary (Complete: 6)
| Subgroup | Metric | OR-Tools | ALNS-Base | Hybrid-Fixed | Hybrid-Rule | Hybrid-DDQN |
|---|---|---|---|---|---|---|
| C1 | NV | 127.00 | 81.33 | 80.00 | 80.00 | 80.00 |
| C2 | NV | 78.00 | 26.33 | 24.33 | 24.00 | 24.00 |
| R1 | NV | 149.00 | 80.00 | 80.00 | 80.00 | 80.00 |
| R2 | NV | 88.00 | 15.33 | 15.00 | 15.00 | 15.00 |
| RC1 | NV | 114.00 | 77.00 | 74.00 | 74.00 | 74.00 |
| RC2 | NV | 76.00 | 22.00 | 21.00 | 21.00 | 21.00 |
| C1 | TD | 54956.49 | 25842.35 | 25365.26 | 25221.97 | 25184.38 |
| C2 | TD | 44499.02 | 13888.84 | 11979.02 | 11705.71 | 11705.71 |
| R1 | TD | 71387.20 | 49030.71 | 41898.97 | 40967.61 | 40967.61 |
| R2 | TD | 56632.65 | 31594.17 | 31074.35 | 31015.14 | 30711.55 |
| RC1 | TD | 54576.87 | 34694.01 | 34605.59 | 34161.24 | 33253.02 |
| RC2 | TD | 45068.58 | 21503.52 | 21068.94 | 20804.86 | 20547.93 |
| C1 | Time | 15.20 | 573.40 | 2868.20 | 712.00 | 502.20 |
| C2 | Time | 15.40 | 333.40 | 2524.30 | 763.80 | 543.30 |
| R1 | Time | 15.30 | 484.30 | 2722.50 | 640.10 | 513.30 |
| R2 | Time | 15.40 | 362.40 | 989.60 | 2139.90 | 543.60 |
| RC1 | Time | 15.90 | 360.30 | 1760.10 | 1384.50 | 495.10 |
| RC2 | Time | 15.30 | 424.80 | 2697.60 | 791.60 | 488.60 |

### Homberger 800 Wilcoxon Hypothesis Testing
| Test Comparison | Metric | p-value |
|---|---|---|
| Hybrid-DDQN vs ALNS-Base | NV | 6.2500e-02 |
| Hybrid-DDQN vs ALNS-Base | TD | 3.1250e-02 |
| Hybrid-DDQN vs Hybrid-Rule | NV | Identical |
| Hybrid-DDQN vs Hybrid-Rule | TD | 1.2500e-01 |
| Hybrid-DDQN vs OR-Tools | NV | 3.1250e-02 |
| Hybrid-DDQN vs OR-Tools | TD | 3.1250e-02 |


## Homberger 1000 Summary
*Benchmark results are currently pending for this shard.*

## LaTeX Publication-Ready Tables
Copy the LaTeX block below directly into your paper document:

```latex
% ==========================================================================
% Generated on: 2026-06-13 20:27:20
% ==========================================================================

% ==========================================================================
% LATEX TABLE FOR: Solomon RESULTS
% ==========================================================================
\begin{table}[htbp]
\centering
\caption{Summary of vehicle count (NV), travel distance (TD), and runtime on Solomon.}
\label{tab:results_solomon}
\begin{tabular}{llrrrrr}
\hline
\textbf{Subgroup} & \textbf{Metric} & \textbf{OR-Tools} & \textbf{ALNS-Base} & \textbf{Hybrid-Fixed} & \textbf{Hybrid-Rule} & \textbf{Hybrid-DDQN} \\ \hline
C1 & NV & 10.00 & 10.00 & 10.00 & 10.00 & 10.00 \\
C2 & NV & 3.00 & 3.00 & 3.00 & 3.00 & 3.00 \\
R1 & NV & 14.25 & 12.48 & 12.25 & 12.25 & 12.25 \\
R2 & NV & 5.45 & 3.01 & 2.83 & 2.82 & 2.82 \\
RC1 & NV & 14.12 & 12.04 & 11.80 & 11.75 & 11.75 \\
RC2 & NV & 6.38 & 3.38 & 3.25 & 3.25 & 3.25 \\
C1 & TD & 840.25 & 828.38 & 828.38 & 828.38 & 828.38 \\
C2 & TD & 593.73 & 594.82 & 590.11 & 589.86 & 589.86 \\
R1 & TD & 1230.80 & 1204.84 & 1204.09 & 1200.43 & 1200.23 \\
R2 & TD & 911.66 & 939.82 & 954.35 & 952.40 & 951.95 \\
RC1 & TD & 1459.11 & 1373.89 & 1366.33 & 1368.17 & 1367.43 \\
RC2 & TD & 1038.93 & 1114.34 & 1136.80 & 1133.99 & 1132.57 \\
C1 & Time & 15.18 & 27.21 & 35.91 & 29.53 & 47.63 \\
C2 & Time & 15.00 & 11.56 & 19.21 & 17.88 & 26.12 \\
R1 & Time & 15.17 & 36.45 & 63.07 & 62.89 & 73.39 \\
R2 & Time & 15.15 & 11.77 & 53.74 & 40.54 & 46.49 \\
RC1 & Time & 15.05 & 37.36 & 57.96 & 42.78 & 49.65 \\
RC2 & Time & 15.01 & 18.31 & 37.91 & 31.45 & 36.24 \\
\hline
\end{tabular}
\end{table}

% Wilcoxon Signed-Rank Test p-values for Solomon
\begin{table}[htbp]
\centering
\caption{Wilcoxon signed-rank test p-values comparing Hybrid-DDQN against baselines on Solomon.}
\label{tab:wilcoxon_solomon}
\begin{tabular}{llr}
\hline
\textbf{Comparison} & \textbf{Metric} & \textbf{p-value} \\ \hline
Hybrid-DDQN vs ALNS-Base & NV & $2.81 \times 10^{-3}$ \\
Hybrid-DDQN vs ALNS-Base & TD & $1.51 \times 10^{-2}$ \\
Hybrid-DDQN vs Hybrid-Rule & NV & Identical \\
Hybrid-DDQN vs Hybrid-Rule & TD & $1.32 \times 10^{-4}$ \\
Hybrid-DDQN vs OR-Tools & NV & $4.05 \times 10^{-8}$ \\
Hybrid-DDQN vs OR-Tools & TD & $4.48 \times 10^{-1}$ \\
\hline
\end{tabular}
\end{table}

% ==========================================================================
% LATEX TABLE FOR: Homberger 200 RESULTS
% ==========================================================================
\begin{table}[htbp]
\centering
\caption{Summary of vehicle count (NV), travel distance (TD), and runtime on Homberger 200.}
\label{tab:results_homberger_200}
\begin{tabular}{llrrrrr}
\hline
\textbf{Subgroup} & \textbf{Metric} & \textbf{OR-Tools} & \textbf{ALNS-Base} & \textbf{Hybrid-Fixed} & \textbf{Hybrid-Rule} & \textbf{Hybrid-DDQN} \\ \hline
C1 & NV & 20.40 & 19.10 & 18.98 & 18.90 & 18.90 \\
C2 & NV & 8.00 & 6.00 & 6.00 & 6.00 & 6.00 \\
R1 & NV & 20.70 & 18.30 & 18.20 & 18.20 & 18.20 \\
R2 & NV & 9.00 & 4.16 & 4.10 & 4.10 & 4.10 \\
RC1 & NV & 19.50 & 18.70 & 18.20 & 18.10 & 18.02 \\
RC2 & NV & 8.50 & 4.56 & 4.50 & 4.50 & 4.50 \\
C1 & TD & 2855.48 & 2848.43 & 2746.23 & 2740.60 & 2735.88 \\
C2 & TD & 1947.23 & 1885.23 & 1840.84 & 1836.54 & 1834.55 \\
R1 & TD & 3918.77 & 3971.15 & 3813.13 & 3745.70 & 3720.03 \\
R2 & TD & 2831.79 & 3065.35 & 2972.80 & 2964.86 & 2951.52 \\
RC1 & TD & 3528.11 & 3478.03 & 3492.66 & 3455.49 & 3438.08 \\
RC2 & TD & 2485.60 & 2659.12 & 2580.55 & 2559.31 & 2548.61 \\
C1 & Time & 15.66 & 25.45 & 42.08 & 42.59 & 51.69 \\
C2 & Time & 15.23 & 17.25 & 36.75 & 35.92 & 38.63 \\
R1 & Time & 15.30 & 31.84 & 48.28 & 47.29 & 51.47 \\
R2 & Time & 15.31 & 10.19 & 39.83 & 39.73 & 43.81 \\
RC1 & Time & 15.63 & 34.45 & 52.22 & 51.63 & 45.59 \\
RC2 & Time & 15.31 & 20.13 & 51.92 & 43.87 & 42.58 \\
\hline
\end{tabular}
\end{table}

% Wilcoxon Signed-Rank Test p-values for Homberger 200
\begin{table}[htbp]
\centering
\caption{Wilcoxon signed-rank test p-values comparing Hybrid-DDQN against baselines on Homberger 200.}
\label{tab:wilcoxon_homberger_200}
\begin{tabular}{llr}
\hline
\textbf{Comparison} & \textbf{Metric} & \textbf{p-value} \\ \hline
Hybrid-DDQN vs ALNS-Base & NV & $5.21 \times 10^{-4}$ \\
Hybrid-DDQN vs ALNS-Base & TD & $1.37 \times 10^{-7}$ \\
Hybrid-DDQN vs Hybrid-Rule & NV & $3.17 \times 10^{-1}$ \\
Hybrid-DDQN vs Hybrid-Rule & TD & $2.08 \times 10^{-7}$ \\
Hybrid-DDQN vs OR-Tools & NV & $1.68 \times 10^{-11}$ \\
Hybrid-DDQN vs OR-Tools & TD & $9.63 \times 10^{-3}$ \\
\hline
\end{tabular}
\end{table}

% ==========================================================================
% LATEX TABLE FOR: Homberger 400 RESULTS
% ==========================================================================
\begin{table}[htbp]
\centering
\caption{Summary of vehicle count (NV), travel distance (TD), and runtime on Homberger 400.}
\label{tab:results_homberger_400}
\begin{tabular}{llrrrrr}
\hline
\textbf{Subgroup} & \textbf{Metric} & \textbf{OR-Tools} & \textbf{ALNS-Base} & \textbf{Hybrid-Fixed} & \textbf{Hybrid-Rule} & \textbf{Hybrid-DDQN} \\ \hline
C1 & NV & 48.25 & 37.83 & 37.25 & 37.25 & 37.25 \\
C2 & NV & 30.50 & 12.17 & 12.00 & 12.00 & 12.00 \\
R1 & NV & 45.25 & 37.00 & 37.00 & 37.00 & 37.00 \\
R2 & NV & 27.25 & 8.25 & 8.00 & 8.00 & 8.00 \\
RC1 & NV & 44.00 & 37.25 & 36.42 & 36.25 & 36.25 \\
RC2 & NV & 26.75 & 10.09 & 9.75 & 9.75 & 9.50 \\
C1 & TD & 10651.61 & 8318.05 & 7567.55 & 7425.75 & 7324.67 \\
C2 & TD & 7669.79 & 4214.86 & 3991.82 & 3964.81 & 3937.76 \\
R1 & TD & 11787.84 & 10319.04 & 9645.84 & 9525.16 & 9390.81 \\
R2 & TD & 9907.61 & 7421.34 & 7270.68 & 7167.19 & 7139.41 \\
RC1 & TD & 10290.73 & 9006.77 & 8837.10 & 8696.34 & 8627.71 \\
RC2 & TD & 7854.81 & 5706.12 & 5451.56 & 5413.83 & 5520.25 \\
C1 & Time & 15.20 & 130.03 & 197.78 & 315.22 & 304.55 \\
C2 & Time & 15.22 & 79.45 & 206.43 & 224.35 & 312.12 \\
R1 & Time & 15.08 & 153.00 & 218.65 & 238.95 & 257.15 \\
R2 & Time & 15.03 & 58.07 & 177.47 & 171.53 & 174.78 \\
RC1 & Time & 15.00 & 135.62 & 174.38 & 160.83 & 146.30 \\
RC2 & Time & 15.03 & 84.60 & 185.05 & 158.50 & 136.97 \\
\hline
\end{tabular}
\end{table}

% Wilcoxon Signed-Rank Test p-values for Homberger 400
\begin{table}[htbp]
\centering
\caption{Wilcoxon signed-rank test p-values comparing Hybrid-DDQN against baselines on Homberger 400.}
\label{tab:wilcoxon_homberger_400}
\begin{tabular}{llr}
\hline
\textbf{Comparison} & \textbf{Metric} & \textbf{p-value} \\ \hline
Hybrid-DDQN vs ALNS-Base & NV & $3.28 \times 10^{-3}$ \\
Hybrid-DDQN vs ALNS-Base & TD & $6.56 \times 10^{-6}$ \\
Hybrid-DDQN vs Hybrid-Rule & NV & $3.17 \times 10^{-1}$ \\
Hybrid-DDQN vs Hybrid-Rule & TD & $6.92 \times 10^{-4}$ \\
Hybrid-DDQN vs OR-Tools & NV & $1.80 \times 10^{-5}$ \\
Hybrid-DDQN vs OR-Tools & TD & $1.19 \times 10^{-7}$ \\
\hline
\end{tabular}
\end{table}

% ==========================================================================
% LATEX TABLE FOR: Homberger 600 RESULTS
% ==========================================================================
\begin{table}[htbp]
\centering
\caption{Summary of vehicle count (NV), travel distance (TD), and runtime on Homberger 600.}
\label{tab:results_homberger_600}
\begin{tabular}{llrrrrr}
\hline
\textbf{Subgroup} & \textbf{Metric} & \textbf{OR-Tools} & \textbf{ALNS-Base} & \textbf{Hybrid-Fixed} & \textbf{Hybrid-Rule} & \textbf{Hybrid-DDQN} \\ \hline
C1 & NV & 94.00 & 59.66 & 58.50 & 58.50 & 58.50 \\
C2 & NV & 56.50 & 18.84 & 18.16 & 18.00 & 18.00 \\
R1 & NV & 99.00 & 57.00 & 57.00 & 57.00 & 57.00 \\
R2 & NV & 60.00 & 11.50 & 11.00 & 11.00 & 11.00 \\
RC1 & NV & 79.50 & 57.16 & 55.50 & 55.50 & 55.50 \\
RC2 & NV & 47.00 & 15.83 & 15.50 & 15.50 & 15.00 \\
C1 & TD & 29763.18 & 16174.10 & 14885.28 & 14731.23 & 14503.58 \\
C2 & TD & 22409.66 & 8522.74 & 7933.49 & 7859.02 & 7745.58 \\
R1 & TD & 35503.63 & 24322.38 & 22497.12 & 22195.42 & 22091.11 \\
R2 & TD & 29948.08 & 18298.28 & 18250.96 & 17974.93 & 17898.25 \\
RC1 & TD & 27779.00 & 18638.92 & 18903.87 & 18538.52 & 18276.40 \\
RC2 & TD & 23345.55 & 13080.59 & 12497.17 & 12405.74 & 12584.33 \\
C1 & Time & 15.25 & 207.45 & 406.05 & 410.90 & 403.30 \\
C2 & Time & 15.25 & 211.35 & 387.40 & 433.80 & 418.15 \\
R1 & Time & 15.30 & 336.70 & 573.05 & 519.70 & 497.50 \\
R2 & Time & 15.30 & 178.85 & 293.25 & 315.35 & 289.70 \\
RC1 & Time & 15.10 & 334.35 & 340.25 & 226.00 & 204.05 \\
RC2 & Time & 15.05 & 249.20 & 404.10 & 341.80 & 255.30 \\
\hline
\end{tabular}
\end{table}

% Wilcoxon Signed-Rank Test p-values for Homberger 600
\begin{table}[htbp]
\centering
\caption{Wilcoxon signed-rank test p-values comparing Hybrid-DDQN against baselines on Homberger 600.}
\label{tab:wilcoxon_homberger_600}
\begin{tabular}{llr}
\hline
\textbf{Comparison} & \textbf{Metric} & \textbf{p-value} \\ \hline
Hybrid-DDQN vs ALNS-Base & NV & $7.81 \times 10^{-3}$ \\
Hybrid-DDQN vs ALNS-Base & TD & $2.44 \times 10^{-3}$ \\
Hybrid-DDQN vs Hybrid-Rule & NV & 1.0000e+00 \\
Hybrid-DDQN vs Hybrid-Rule & TD & $4.20 \times 10^{-2}$ \\
Hybrid-DDQN vs OR-Tools & NV & $4.88 \times 10^{-4}$ \\
Hybrid-DDQN vs OR-Tools & TD & $4.88 \times 10^{-4}$ \\
\hline
\end{tabular}
\end{table}

% ==========================================================================
% LATEX TABLE FOR: Homberger 800 RESULTS
% ==========================================================================
\begin{table}[htbp]
\centering
\caption{Summary of vehicle count (NV), travel distance (TD), and runtime on Homberger 800.}
\label{tab:results_homberger_800}
\begin{tabular}{llrrrrr}
\hline
\textbf{Subgroup} & \textbf{Metric} & \textbf{OR-Tools} & \textbf{ALNS-Base} & \textbf{Hybrid-Fixed} & \textbf{Hybrid-Rule} & \textbf{Hybrid-DDQN} \\ \hline
C1 & NV & 127.00 & 81.33 & 80.00 & 80.00 & 80.00 \\
C2 & NV & 78.00 & 26.33 & 24.33 & 24.00 & 24.00 \\
R1 & NV & 149.00 & 80.00 & 80.00 & 80.00 & 80.00 \\
R2 & NV & 88.00 & 15.33 & 15.00 & 15.00 & 15.00 \\
RC1 & NV & 114.00 & 77.00 & 74.00 & 74.00 & 74.00 \\
RC2 & NV & 76.00 & 22.00 & 21.00 & 21.00 & 21.00 \\
C1 & TD & 54956.49 & 25842.35 & 25365.26 & 25221.97 & 25184.38 \\
C2 & TD & 44499.02 & 13888.84 & 11979.02 & 11705.71 & 11705.71 \\
R1 & TD & 71387.20 & 49030.71 & 41898.97 & 40967.61 & 40967.61 \\
R2 & TD & 56632.65 & 31594.17 & 31074.35 & 31015.14 & 30711.55 \\
RC1 & TD & 54576.87 & 34694.01 & 34605.59 & 34161.24 & 33253.02 \\
RC2 & TD & 45068.58 & 21503.52 & 21068.94 & 20804.86 & 20547.93 \\
C1 & Time & 15.20 & 573.40 & 2868.20 & 712.00 & 502.20 \\
C2 & Time & 15.40 & 333.40 & 2524.30 & 763.80 & 543.30 \\
R1 & Time & 15.30 & 484.30 & 2722.50 & 640.10 & 513.30 \\
R2 & Time & 15.40 & 362.40 & 989.60 & 2139.90 & 543.60 \\
RC1 & Time & 15.90 & 360.30 & 1760.10 & 1384.50 & 495.10 \\
RC2 & Time & 15.30 & 424.80 & 2697.60 & 791.60 & 488.60 \\
\hline
\end{tabular}
\end{table}

% Wilcoxon Signed-Rank Test p-values for Homberger 800
\begin{table}[htbp]
\centering
\caption{Wilcoxon signed-rank test p-values comparing Hybrid-DDQN against baselines on Homberger 800.}
\label{tab:wilcoxon_homberger_800}
\begin{tabular}{llr}
\hline
\textbf{Comparison} & \textbf{Metric} & \textbf{p-value} \\ \hline
Hybrid-DDQN vs ALNS-Base & NV & $6.25 \times 10^{-2}$ \\
Hybrid-DDQN vs ALNS-Base & TD & $3.12 \times 10^{-2}$ \\
Hybrid-DDQN vs Hybrid-Rule & NV & Identical \\
Hybrid-DDQN vs Hybrid-Rule & TD & $1.25 \times 10^{-1}$ \\
Hybrid-DDQN vs OR-Tools & NV & $3.12 \times 10^{-2}$ \\
Hybrid-DDQN vs OR-Tools & TD & $3.12 \times 10^{-2}$ \\
\hline
\end{tabular}
\end{table}

```