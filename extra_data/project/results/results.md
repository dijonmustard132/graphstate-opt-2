# Benchmark results

This is the central team-facing result summary. Detailed values are retained in the companion CSV files.

## Reading the metrics

- **Mean found/MER**: result divided by a known optimum; closer to `1.0000` is better.
- **Edge excess**: mean `found edges - known optimum`.
- **Relative excess**: mean percentage above the known optimum.
- For arbitrary graphs without exact labels, compare mean and best edge counts, not approximation ratios.

## Planted larger graphs

LC-scrambled random trees with certified optimum `n-1`: 40 graphs, 20 seeds, and 1000 iterations.

| n | Author SA-LC excess | Mixed SA LC+pivot excess | Author found/MER | Mixed found/MER |
|---:|---:|---:|---:|---:|
| 13 | 0.656 edges / 5.47% | 0.000 / 0.00% | 1.0547 | 1.0000 |
| 16 | 1.356 edges / 9.04% | 0.000 / 0.00% | 1.0904 | 1.0000 |
| 20 | 1.881 edges / 9.90% | 0.000 / 0.00% | 1.0990 | 1.0000 |
| 30 | 3.519 edges / 12.13% | 0.031 / 0.11% | 1.1213 | 1.0011 |
| 40 | 4.206 edges / 10.79% | 0.081 / 0.21% | 1.1079 | 1.0021 |

Detailed table: [large_comparison.csv](large_comparison.csv).

## Arbitrary graphs

Thirty-two connected Erdős–Rényi graphs at `n=13, 16, 20, 30` and densities `0.15, 0.35, 0.55, 0.75`, with 20 seeds each. Exact optima are unknown unless an ILP solve completes; lower mean and best edge counts indicate stronger heuristic performance.

The dense cases generally favour mixed LC+pivot SA. Full graph-by-density values are in [arbitrary_comparison.csv](arbitrary_comparison.csv).

Sparse and dense `n=13` SA+ILP spot checks found the same ILP edge counts:

| Graph | Author SA+ILP | Mixed-SA+ILP |
|---|---:|---:|
| ER-13-p15 | 14 edges | 14 edges |
| ER-13-p75 | 19 edges | 19 edges |

## Existing custom dataset

The custom 307-graph experiment and tabu sweep show:

- Mixed LC+pivot SA: exact-hit 99%, mean found/MER `1.000` on the test split.
- Tabu LC+pivot: exact-hit 99%, mean found/MER `1.000` on the test split.
- Author SA-LC: exact-hit 94%, mean found/MER `1.015` on the test split.
- Tabu LC+pivot substantially outperforms plain Tabu LC on resource states and planted cases.

A partial 32-graph, 20-seed closeness rerun gave:

| Method | Mean edge excess | Mean relative excess |
|---|---:|---:|
| Author SA-LC | 0.424 | 3.72% |
| Mixed SA LC+pivot | 0.025 | 0.14% |
| Tabu LC | 0.005 | 0.03% |
| Tabu LC+pivot | 0.000 | 0.00% |

Detailed partial run: [comprehensive_comparison.csv](comprehensive_comparison.csv). This is not a complete rerun of every custom graph.

## Reproduce

```bash
python3 extra_data/project/scripts/run_benchmarks.py
python3 extra_data/project/scripts/run_benchmarks.py --quick
```

See the [team benchmark guide](../../../BENCHMARKS.md) for Colab, custom options, and result interpretation.

## Limitations

- ILP runtime and solver availability affect SA+ILP conclusions.
- Planted tree labels are exact by connectivity and LC-orbit structure.
- Arbitrary graph findings are heuristic unless independently solved or enumerated.
- Tabu comparisons require equal budgets and seeds for the strongest claim.
