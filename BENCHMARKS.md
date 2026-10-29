# Team benchmark guide

This is the central guide for reproducing and comparing all graph-state edge-minimisation experiments.

## Quick setup

```bash
python3 -m pip install -e .
python3 -m pip install networkx cvxpy scipy
```

Python 3.10+ is recommended. Colab users can clone the repository and install it with:

```python
!git clone https://github.com/dijonmustard132/graphstate-opt-2.git
%cd graphstate-opt-2
!pip install -q -e .
!pip install -q networkx cvxpy scipy
```

## One-command runner

For the recommended 20-seed planted and arbitrary benchmarks, run:

```bash
python3 extra_data/project/scripts/run_benchmarks.py
```

Useful options:

```bash
# Quick development run; skip ILP checks
python3 extra_data/project/scripts/run_benchmarks.py --quick

# Custom graph counts, iteration count, and seed count
python3 extra_data/project/scripts/run_benchmarks.py \
  --large-graphs 8 \
  --arbitrary-graphs 2 \
  --iterations 1000 \
  --seeds 20

# Run only one benchmark family
python3 extra_data/project/scripts/run_benchmarks.py --only large
python3 extra_data/project/scripts/run_benchmarks.py --only arbitrary
python3 extra_data/project/scripts/run_benchmarks.py --only lowest-edge

# Explicitly exclude expensive ILP spot checkspython3 extra_data/project/scripts/run_benchmarks.py --no-ilp
```

## Algorithms compared

| Method | Move set | Behaviour |
|---|---|---|
| Author SA-LC | Local complementation | Baseline simulated annealing |
| Repo SA LC+pivot | Local complementation + pivot | Mixed current SA baseline |
| Tabu LC | Local complementation | Tabu list avoids recently selected moves |
| Tabu LC+pivot | Local complementation + pivot | Strongest tabu variant in the existing custom benchmarks |
| Author SA+ILP | Author SA preprocessing + ILP | Exact-optimisation comparator |

## Datasets and reports

- `extra_data/project/data/manifest.csv`: 307 custom graphs with exact or certified MER labels.
- `extra_data/project/data/large_manifest.csv`: LC-scrambled planted trees with certified optimum `n-1`.
- `extra_data/project/data/arbitrary_manifest.csv`: connected Erdős–Rényi graphs; exact MER values are not assumed.
- `extra_data/project/results/results.md`: consolidated team-facing benchmark summary.
- `extra_data/project/results/*.csv`: machine-readable detailed results.

## Lowest-edge comparison

This benchmark compares algorithms without using exact-hit counts:

```bash
python3 extra_data/project/scripts/run_lowest_edge_comparison.py test --seeds 20
```

It prints the lowest edge count found every 10 seconds and writes `lowest_edges_test.csv` plus `lowest_edges_test.md` to `extra_data/project/results/`. Change `10.0` with `--progress-interval` if another reporting interval is required.

```bash
python3 extra_data/project/scripts/run_benchmarks.py --only lowest-edge --seeds 20
```

## Existing custom benchmark

```bash
cd extra_data/project/scripts
python3 run_experiments.py test 20
python3 run_experiments.py val 20
python3 run_experiments.py train 20
python3 aggregate.py
```

## Reading the results

For graphs with a known optimum, report:

- `found/MER`: mean result divided by the known optimum. Prefer values close to `1.0000`.
- `edge excess`: mean `found edges - optimum`.
- `relative excess`: mean percentage above the optimum.
- runtime and seed count.

For arbitrary graphs without an exact optimum, report mean edge count, best edge count, runtime, and paired differences. Never call these approximation ratios.

For reproducible comparisons, keep graph count, iteration budget, seed list, and method settings identical. Seed the random states explicitly and analyse paired graph-level differences rather than mixing unrelated graph classes.

## Colab result download

```python
from google.colab import files
files.download("extra_data/project/results/results.md")
files.download("extra_data/project/results/large_comparison.csv")
files.download("extra_data/project/results/arbitrary_comparison.csv")
```
