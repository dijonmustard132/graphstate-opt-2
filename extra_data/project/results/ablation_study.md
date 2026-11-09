# DualMode-Hybrid ablation study

Four graph families, 5 graph(s) per family, 100 newly generated shared seeds, and an equal budget of 20000 OPS.

Values are percentage differences from Original within the same graph family; negative is better.

## Change in final edge count relative to Original

| Feature removed | Planted tree | Erdős–Rényi | Grid | Bipartite |
|---|---:|---:|---:|---:|
| Pivot moves | +4.13% | +0.00% | -2.02% | +0.00% |
| Pivot pruning | -4.63% | +0.04% | +6.47% | +0.00% |
| Tabu memory | +4.05% | -0.01% | +4.29% | +0.00% |
| Softmax plateau | +9.76% | -0.11% | -1.01% | +0.00% |

## Change in runtime relative to Original

| Feature removed | Planted tree | Erdős–Rényi | Grid | Bipartite |
|---|---:|---:|---:|---:|
| Pivot moves | -42.10% | -64.94% | -55.47% | -94.65% |
| Pivot pruning | -46.40% | -63.67% | -55.27% | -0.85% |
| Tabu memory | -5.03% | +1.84% | -1.37% | -1.92% |
| Softmax plateau | -13.68% | +10.00% | -12.66% | -6.49% |

## Reading the ablation

Each variant removes only the feature named in its row, using the same graphs and seeds as Original. Percentages compare family-wide mean edge counts and runtimes; negative values mean fewer edges or lower runtime.
