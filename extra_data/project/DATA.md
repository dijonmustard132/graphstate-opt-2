# Extra test data for LC edge-minimisation (datasheet)

Independent of the authors' repo (arr0w-hs/graph_state_optimization). Nothing here was run against their code or data.
Their released ER / bounded-degree sets (Zenodo) should still be used for head-to-head comparison with EDM-SA/EDM-SAILP.

## What is in `data/manifest.csv` (307 graphs, n = 8-12, plus 10 planted graphs at n = 30)
One row per graph. Columns: `id, class, generator, n, edges (input), mer (exact minimum), label_source, orbit_id, orbit_size, seed, split, graph` (edge list "u-v;u-v;...").

| Class | What it is | How built | Start graph | MER label |
|---|---|---|---|---|
| ER | Erdos-Renyi G(n,p), n=10-12, p in {0.1,0.2,0.3,0.5,0.8,0.9} | 6 per cell | the sampled graph | full orbit enumeration |
| BD | bounded degree (<=5): n positive integers <=5 as degree sequence, Havel-Hakimi, connected only | 8 per n | the generated graph | full orbit enumeration |
| RES | measurement-based-computation resource states: paths P8-P12, rings C8-C12, ladders 2x4-2x6, grids 3x3, 3x4 | orbit of the named graph | 3 uniform random orbit members ("scrambled") | full orbit enumeration |
| TREE | random recursive trees, n=9-12 | 6 per n | 2 uniform random orbit members | enumeration (checked == n-1) |
| GHZ | complete, complete bipartite, wheels (star merged with complete: same orbit) | named graphs | up to 4 orbit members | enumeration (complete checked == n-1) |
| REP | repeater-like: complete core + leaves (RGS m=2,3) and random dense core + leaves | named / sampled | 2-3 orbit members | full orbit enumeration |
| PLANT | random tree n=30 scrambled by 10n random LCs | 10 graphs | the scrambled graph | certified n-1 (connected graphs need >= n-1 edges; LC preserves connectivity) |

Splits are by **orbit** within each class: 40% test / 20% val / 40% train (>= 1 test orbit per class). Scrambled starts from one orbit are correlated, so analyse per orbit.
Orbit ids come from the lexicographically smallest member of the *labelled* orbit; isomorphic relabellings can still land in different orbits.

## Reproduce
```
cd scripts
python3 make_data.py          # ~85 s, deterministic (seeds fixed; regenerated checksum matched)
python3 validate_data.py      # independent checks, exit code 1 on failure
python3 run_experiments.py train 3
python3 run_experiments.py val 3
python3 run_experiments.py test 3
python3 aggregate.py          # writes results/results.md
```
Python 3.10+ (uses int.bit_count). No external packages.

## Validation performed
0 failures: orbits never span splits; no duplicate graphs; stored edge counts match; trees and planted graphs connected with MER = n-1;
complete graphs collapse to n-1; MER <= input edges; 229 of 307 rows (size <= 20,000) re-enumerated from the stored graph with matching MER and orbit size.

## Known limits
- Exact labels come from enumeration, so n <= 12 here. At these sizes most classes are easy: nearly every method reaches the exact minimum on BD, TREE, GHZ and REP. Only ER (and RES for weak methods) separate methods. Use lower budgets or larger certified instances to discriminate.
- PLANT gives certified labels at n=30 but only 10 graphs, and scrambled trees stay sparse (about 2.5n edges).
- Few orbits per class (e.g. 4-6 test orbits for GHZ, RES, REP): per-class numbers are indicative only.
- Operation counts (`OPS`) are my own hardware-independent unit.

## Pivot comparison
An edge pivot on `uv` is implemented as `LC(u), LC(v), LC(u)`. The mixed simulated-annealing baseline samples local-complementation and pivot moves, while the LC-only baseline uses the same budget and acceptance schedule. Run `run_budget_sweep.py` on train/val to choose budgets, then test; the sweep reports quality against `OPS` rather than relying only on wall-clock time. The package API `graphstate_opt.edm_lc_pivot_sa` provides the same mixed move family for NetworkX graphs.

## Variable resources (budget sweeps)
The budget is the number of word-level operations a heuristic may use per graph (`OPS` in `lc_tools.py`). 10,000 saturates most classes; use a sweep instead of one budget.
```
cd scripts
python3 run_budget_sweep.py train 3      # choose budgets on train/val ...
python3 run_budget_sweep.py val 3
python3 run_budget_sweep.py test 3       # ... report on test
python3 run_budget_sweep.py test 3 1000,2000,4000   # custom budget list (n<=12 classes)
python3 aggregate_sweep.py               # writes results/budget_sweep.md
python3 run_planted_sweep.py 3           # n=30 planted trees at low budgets
```
Select budgets from train+val tables, then report the test tables (never pick budgets by looking at test).
