**Table 1. Test split (budget 10,000 work units; planted 300,000; 3 seeds)**

| Method | ER random | Bounded degree | Resource states | Trees | GHZ-type | Repeater-like | Planted n=30 | All (excl. planted) |
|---|---|---|---|---|---|---|---|---|
| SA (LC) | 1.037 (86%) | 1.002 (97%) | 1.006 (93%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.015 (94%) |
| SA (LC+pivot) | 1.001 (98%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (99%) |
| ILS (LC) | 1.000 (99%) | 1.000 (100%) | 1.003 (96%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.001 (99%) |
| ILS (LC+pivot) | 1.003 (95%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.001 (98%) |
| Tabu (LC) | 1.007 (89%) | 1.000 (100%) | 1.039 (67%) | 1.002 (98%) | 1.000 (100%) | 1.000 (100%) | 1.060 (50%) | 1.009 (91%) |
| Tabu commit (LC) | 1.002 (98%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.001 (99%) |
| Tabu (LC+pivot) | 1.001 (98%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (99%) |
| Tabu (pivot only) | 1.407 (28%) | 1.160 (0%) | 1.376 (0%) | 1.404 (0%) | 1.397 (56%) | 1.144 (55%) | 1.319 (0%) | 1.355 (23%) |

Instances per class: ER random 43, Bounded degree 10, Resource states 18, Trees 20, GHZ-type 16, Repeater-like 11, Planted n=30 4. Cells: mean found/MER (share of runs reaching the exact minimum).

**Table 2. Effect of adding pivot moves, test split**

| Comparison (first minus second) | ER random | Bounded degree | Resource states | Trees | GHZ-type | Repeater-like | All (orbits) | 95% CI (all) |
|---|---|---|---|---|---|---|---|---|
| SA: SA (LC+pivot) - SA (LC) | -0.036 | -0.002 | -0.006 | +0.000 | +0.000 | +0.000 | -0.0207 (exact-hit +7.8 pts, 78 orbits) | [-0.0453, -0.0057] |
| ILS: ILS (LC+pivot) - ILS (LC) | +0.003 | +0.000 | -0.003 | +0.000 | +0.000 | +0.000 | +0.0015 (exact-hit -1.9 pts, 78 orbits) | [-0.0004, +0.0043] |
| Tabu: Tabu (LC+pivot) - Tabu (LC) | -0.006 | +0.000 | -0.039 | -0.002 | +0.000 | +0.000 | -0.0067 (exact-hit +7.9 pts, 78 orbits) | [-0.0111, -0.0031] |
| Tabu vs commit: Tabu (LC+pivot) - Tabu commit (LC) | -0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | -0.0002 (exact-hit +0.4 pts, 78 orbits) | [-0.0006, +0.0000] |

Negative = the pivot variant found smaller graphs. Unit of analysis = orbit (seeds and starts averaged within an orbit).

**Table 3. Same comparison pooled over all splits (more orbits; robustness check)**

| Comparison (first minus second) | ER random | Bounded degree | Resource states | Trees | GHZ-type | Repeater-like | All (orbits) | 95% CI (all) |
|---|---|---|---|---|---|---|---|---|
| SA: SA (LC+pivot) - SA (LC) | -0.026 | -0.003 | -0.002 | +0.000 | +0.000 | +0.000 | -0.0148 (exact-hit +6.6 pts, 195 orbits) | [-0.0253, -0.0069] |
| ILS: ILS (LC+pivot) - ILS (LC) | +0.002 | +0.000 | -0.001 | +0.000 | +0.000 | +0.000 | +0.0009 (exact-hit -1.1 pts, 195 orbits) | [-0.0001, +0.0023] |
| Tabu: Tabu (LC+pivot) - Tabu (LC) | -0.006 | -0.003 | -0.018 | -0.001 | +0.005 | -0.006 | -0.0055 (exact-hit +6.7 pts, 195 orbits) | [-0.0080, -0.0033] |
| Tabu vs commit: Tabu (LC+pivot) - Tabu commit (LC) | -0.000 | +0.000 | +0.000 | +0.000 | +0.006 | +0.000 | +0.0000 (exact-hit +0.3 pts, 195 orbits) | [-0.0005, +0.0009] |

Negative = the pivot variant found smaller graphs. Unit of analysis = orbit (seeds and starts averaged within an orbit).

**Table 4. All splits pooled**

| Method | ER random | Bounded degree | Resource states | Trees | GHZ-type | Repeater-like | Planted n=30 | All (excl. planted) |
|---|---|---|---|---|---|---|---|---|
| SA (LC) | 1.026 (89%) | 1.003 (94%) | 1.002 (97%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.001 (97%) | 1.010 (95%) |
| SA (LC+pivot) | 1.001 (99%) | 1.001 (99%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) |
| ILS (LC) | 1.001 (98%) | 1.000 (100%) | 1.001 (99%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (99%) |
| ILS (LC+pivot) | 1.003 (96%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.001 (99%) |
| Tabu (LC) | 1.007 (91%) | 1.003 (96%) | 1.018 (84%) | 1.001 (99%) | 1.001 (99%) | 1.006 (96%) | 1.068 (57%) | 1.006 (93%) |
| Tabu commit (LC) | 1.001 (98%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.000 (99%) |
| Tabu (LC+pivot) | 1.000 (99%) | 1.000 (100%) | 1.000 (100%) | 1.000 (100%) | 1.006 (96%) | 1.000 (100%) | 1.000 (100%) | 1.001 (99%) |
| Tabu (pivot only) | 1.444 (19%) | 1.149 (8%) | 1.355 (0%) | 1.365 (2%) | 1.284 (55%) | 1.142 (43%) | 1.321 (10%) | 1.342 (20%) |

Instances per class: ER random 108, Bounded degree 24, Resource states 45, Trees 48, GHZ-type 44, Repeater-like 28, Planted n=30 10. Cells: mean found/MER (share of runs reaching the exact minimum).
