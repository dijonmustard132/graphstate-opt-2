# Graph-state benchmark project

This folder contains the reproducible custom datasets, benchmark runners, and machine-readable results.

Start with the central [team benchmark guide](../../../BENCHMARKS.md).

## Directory layout

- `scripts/`: dataset generation, benchmark runners, and aggregation
- `data/`: custom graph manifests
- `results/`: consolidated reports and detailed CSV output

## Standard commands

```bash
# Central comparison runner
python3 scripts/run_benchmarks.py

# Existing custom 307-graph experiment
cd scripts
python3 run_experiments.py test 20
python3 aggregate.py
```

Run the central guide's commands from the repository root, not from this folder.
