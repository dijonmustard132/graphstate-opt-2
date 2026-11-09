#!/usr/bin/env python3
"""Run individual DualMode-Hybrid feature ablations.

Results are reported relative to the original method using the same graphs
and random seeds.
"""

import argparse
import csv
import math
import random
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generators import from_edges, grid, rand_tree  # noqa: E402
from lc_tools import OPS, connected, delta, edges, edge_list, lc, pivot, pivot_delta, scramble  # noqa: E402


FEATURES = (("pivot moves", "pivots"), ("pivot pruning", "pruning"),
            ("tabu memory", "tabu"), ("softmax plateau", "softmax"))
METHODS = {"Original": {}}
for name, option in FEATURES:
    METHODS[f"- {name}"] = {option: False}
FAMILIES = ("planted-tree", "erdos-renyi", "grid", "complete-bipartite")


def make_graphs(graphs_per_family):
    """Return varied deterministic n=40 graphs; only certified families have targets."""
    graphs = []
    for index in range(graphs_per_family):
        seed = 20261108 + index
        tree_rng = random.Random(seed + 1000)
        tree = scramble(rand_tree(40, tree_rng), 800, tree_rng)
        graphs.append(("planted-tree", index, tree, 39))

        er_rng = random.Random(seed + 2000)
        while True:
            er = from_edges(40, [(u, v) for u in range(40) for v in range(u + 1, 40)
                                 if er_rng.random() < 0.15])
            if connected(er):
                break
        graphs.append(("erdos-renyi", index, er, None))
        grid_rng = random.Random(seed + 3000)
        graphs.append(("grid", index, scramble(grid(5, 8), 800, grid_rng), None))
        bipartite = from_edges(40, [(u, 20 + v) for u in range(20) for v in range(20)])
        bipartite_rng = random.Random(seed + 4000)
        graphs.append(("complete-bipartite", index,
                       scramble(bipartite, 800, bipartite_rng), 39))
    return graphs


def choose_softmax(candidates, temperature, rng):
    scores = [-change / max(temperature, 1e-9) for change, _ in candidates]
    largest = max(scores)
    weights = [math.exp(score - largest) for score in scores]
    return rng.choices(candidates, weights=weights, k=1)[0]


def dualmode(rows, budget, rng, *, pivots=True, pruning=True, tabu=True, softmax=True):
    """Run the report's DualMode-Hybrid control flow and return its best edge count."""
    rows = list(rows)
    OPS[0] = 0
    best = edges(rows)
    recent = deque(maxlen=4)
    while OPS[0] < budget:
        current = edges(rows)
        lc_moves = []
        for vertex in range(len(rows)):
            if rows[vertex].bit_count() < 2:
                continue
            change = delta(rows, vertex)
            move = ("lc", vertex)
            if not tabu or move not in recent or current + change < best:
                lc_moves.append((change, move))
        if not lc_moves:
            break

        downhill = [item for item in lc_moves if item[0] <= -2]
        if downhill:
            change, move = min(downhill)
        else:
            candidates = list(lc_moves)
            if pivots:
                best_lc = min(change for change, _ in lc_moves)
                for u, v in edge_list(rows):
                    if pruning:
                        endpoint_changes = [change for change, move in lc_moves
                                            if move[1] in (u, v)]
                        if not endpoint_changes or min(endpoint_changes) > best_lc + 2:
                            continue
                    move = ("pivot", u, v)
                    if not tabu or move not in recent:
                        candidates.append((pivot_delta(rows, u, v), move))
            if softmax:
                change, move = choose_softmax(candidates, 4.0, rng)
            else:
                change, move = min(candidates)

        rows = lc(rows, move[1]) if move[0] == "lc" else pivot(rows, move[1], move[2])
        if tabu:
            recent.append(move)
        best = min(best, edges(rows))
    return best


def run(graphs, budget, seeds):
    results = []
    total = len(graphs) * len(METHODS) * len(seeds)
    completed = 0
    for family, index, graph, optimum in graphs:
        for method_name, options in METHODS.items():
            for seed in seeds:
                started = time.perf_counter()
                found = dualmode(graph, budget, random.Random(seed), **options)
                runtime = time.perf_counter() - started
                results.append({
                    "family": family, "graph_index": index, "input_edges": edges(graph),
                    "certified_mer": "" if optimum is None else optimum,
                    "method": method_name, "seed": seed, "budget": budget,
                    "found_edges": found,
                    "edge_excess": "" if optimum is None else found - optimum,
                    "runtime_seconds": runtime,
                })
                completed += 1
        print(f"Completed {family} graph {index} ({completed}/{total} runs)", flush=True)
    return results


def mean(values):
    return sum(values) / len(values) if values else None


def format_metric(value, decimals=3):
    """Format a metric, using N/A when no certified target exists."""
    return "N/A" if value is None else f"{value:.{decimals}f}"


def write_outputs(results, output_dir, budget, seeds, graphs_per_family):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "ablation_study.csv"
    fields = ["family", "graph_index", "input_edges", "certified_mer", "method",
              "seed", "budget", "found_edges", "edge_excess", "runtime_seconds"]
    with csv_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    grouped = defaultdict(list)
    for result in results:
        grouped[(result["family"], result["method"])].append(result)
    lines = [
        "# DualMode-Hybrid ablation study", "",
        f"Four graph families, {graphs_per_family} graph(s) per family, "
        f"{len(seeds)} newly generated shared seeds, and an equal budget of {budget} OPS.", "",
        "Values are percentage differences from Original within the same graph family; negative is better.", "",
    ]
    for title, metric in (("Change in final edge count relative to Original", "found_edges"),
                          ("Change in runtime relative to Original", "runtime_seconds")):
        lines.extend([f"## {title}", "",
                      "| Feature removed | Planted tree | Erdős–Rényi | Grid | Bipartite |",
                      "|---|---:|---:|---:|---:|"])
        for name, _ in FEATURES:
            values = []
            for family in FAMILIES:
                baseline = mean([row[metric] for row in grouped[(family, "Original")]])
                variant = mean([row[metric] for row in grouped[(family, f"- {name}")]])
                values.append(f"{100 * (variant / baseline - 1):+.2f}%")
            lines.append(f"| {name.capitalize()} | " + " | ".join(values) + " |")
        lines.append("")
    lines += ["", "## Reading the ablation", "",
              "Each variant removes only the feature named in its row, using the same graphs "
              "and seeds as Original. Percentages compare family-wide mean edge counts "
              "and runtimes; negative values mean fewer edges or lower runtime."]
    md_path = output_dir / "ablation_study.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graphs-per-family", type=int, default=5)
    parser.add_argument("--budget", type=int, default=20000)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--seed-random-state", type=int, default=20261109,
                        help="Random state used to generate the reproducible seed list")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    if min(args.graphs_per_family, args.budget, args.seeds) < 1:
        parser.error("graphs-per-family, budget, and seeds must be positive")
    seed_rng = random.Random(args.seed_random_state)
    seeds = seed_rng.sample(range(1, 10_000_000), args.seeds)
    results = run(make_graphs(args.graphs_per_family), args.budget, seeds)
    write_outputs(results, args.output_dir, args.budget, seeds, args.graphs_per_family)


if __name__ == "__main__":
    main()
