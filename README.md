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
│   ├── Testing Rig/          # Browser benchmarking rig (index.html, generators.js, etc.)
│   └── ...                   # JSON results archive for the report
├── edm_sa.py                 # Sharma et al. upstream Python EDM-SA comparator
├── target_audit.py           # Exhaustive BFS orbit verifier for small target-labelled graphs
└── README.md