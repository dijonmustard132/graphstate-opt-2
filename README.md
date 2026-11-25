# Heuristic Search for Minimum-Edge Graph States (`graphstate-opt-2`)

**COMP3821/9801 (Extended Algorithm Design and Analysis) — Group 34 (Term 3, 2026)**  
*Budgeted optimisation over local-complementation orbits*

**Group members:** Adam Burges, Dexuan Lin, Jack Petersen, Nicholas Mulquiney

**Project mentor:** Ryan Ong

---

## Overview

This repository contains the browser-based benchmarking rig, archived experimental results, orbit-verification script, and upstream baseline comparator for our study comparing five simulated-annealing and local-search heuristics for finding sparse (minimum-edge) locally equivalent graph states under finite evaluation budgets:

- **`EDM-SA`** — Reimplementation of Sharma et al.’s single-LC simulated annealing baseline (`Mv = Cv * dv` scoring, logarithmic cooling)
- **`Exact-Geom-SA`** — Exact single-LC scoring (`Δv`) with softmax proposal and geometric cooling
- **`Pivot-SA`** — Exact LC + unpruned edge-pivot scoring with greedy `min-Δ` proposal and geometric cooling
- **`DualMode-Anytime`** — Exact LC scoring, 4-vertex tabu list, LC/pivot short-circuits, pruned pivots, adaptive budget-matched cooling, and stagnation reheating
- **`DualMode-Deep`** — Exact LC + permissive pivot scoring, 2-step LC tunnel, 64-slot FNV-1a state-hash cycle filter, and 3-LC kick from incumbent with slower geometric cooling

---

## Repository Structure

```text
.
├── COMP3821_OUR_DATA/
│   ├── Report Results/
│   │   ├── REPORT_RESULTS_RUN.json       # Primary benchmark results used in the report
│   │   └── OLD_RESULTS_ARCHIVED.json     # The benchmark results before we updated our known minimum edge calculation for Cabello graphs
│   └── Testing App and Algorithm Source/ # Browser benchmarking rig
│       ├── css/
│       │   └── styles.css
│       ├── js/
│       │   ├── algorithms.js             # Implementations of all 5 search heuristics
│       │   ├── chart.js                  # Results plotting in the GUI
│       │   ├── generators.js             # 75-instance benchmark suite & target labels
│       │   ├── graph.js                  # Adjacency representation, LC & pivot moves
│       │   └── main.js                   # Rig UI & benchmark runner logic
│       └── index.html                    # Entry point for the browser GUI
├── edm_sa.py                             # Sharma et al. upstream Python EDM-SA comparator
├── target_audit.py                       # Exhaustive BFS orbit verifier for small target-labelled graphs
└── README.md