"""Generate certified larger LC-orbit graphs and compare SA implementations."""

import argparse
import csv
import random
import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from graphstate_opt.edm_ilp import edm_ilp
from graphstate_opt.edm_sa import edm_sa
from graphstate_opt.edm_sa_ilp import edm_sa_ilp
from graphstate_opt.edm_pivot import edm_lc_pivot_sa


SIZES = (13, 16, 20, 30, 40)
DATA_PATH = ROOT / "data" / "large_manifest.csv"
RESULTS_PATH = ROOT / "results" / "large_comparison.csv"
ILP_RESULTS_PATH = ROOT / "results" / "large_ilp_comparison.csv"
SUMMARY_PATH = ROOT / "results" / "large_comparison.md"


def random_tree(size, rng):
    graph = nx.empty_graph(size)
    graph.add_edges_from((vertex, rng.randrange(vertex)) for vertex in range(1, size))
    return graph


def locally_complement(graph, vertex):
    neighbors = list(graph.neighbors(vertex))
    for index, first in enumerate(neighbors):
        for second in neighbors[index + 1:]:
            if graph.has_edge(first, second):
                graph.remove_edge(first, second)
            else:
                graph.add_edge(first, second)


def generate_dataset(graphs_per_size):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            ["id", "n", "edges", "certified_mer", "seed", "lc_scramble_steps", "graph"]
        )
        for size in SIZES:
            for index in range(graphs_per_size):
                seed = 20261027 + size * 1000 + index
                rng = random.Random(seed)
                graph = random_tree(size, rng)
                scramble_steps = 20 * size
                for _ in range(scramble_steps):
                    locally_complement(graph, rng.randrange(size))
                edge_list = ";".join(
                    f"{u}-{v}" for u, v in sorted(graph.edges())
                )
                writer.writerow(
                    [
                        f"LC-TREE-{size}-{index:03d}",
                        size,
                        graph.number_of_edges(),
                        size - 1,
                        seed,
                        scramble_steps,
                        edge_list,
                    ]
                )
    return list(csv.DictReader(DATA_PATH.open()))


def load_dataset():
    return list(csv.DictReader(DATA_PATH.open()))


def as_networkx(row):
    size = int(row["n"])
    graph = nx.empty_graph(size)
    for edge in row["graph"].split(";"):
        if edge:
            u, v = map(int, edge.split("-"))
            graph.add_edge(u, v)
    return graph


def run_sa_comparison(rows, iterations, seeds):
    output_rows = []
    for graph_index, row in enumerate(rows):
        graph = as_networkx(row)
        optimum = int(row["certified_mer"])
        for run_seed in seeds:
            np.random.seed(run_seed)
            start = time.perf_counter()
            author_graph, _, _ = edm_sa(graph, iterations, 10.0)
            author_seconds = time.perf_counter() - start
            output_rows.append(
                [
                    row["id"],
                    row["n"],
                    row["edges"],
                    optimum,
                    run_seed,
                    "author-SA-LC",
                    author_graph.number_of_edges(),
                    f"{author_seconds:.6f}",
                ]
            )

            start = time.perf_counter()
            mixed_graph, _, _ = edm_lc_pivot_sa(
                graph, iterations, 10.0, random_state=run_seed
            )
            mixed_seconds = time.perf_counter() - start
            output_rows.append(
                [
                    row["id"],
                    row["n"],
                    row["edges"],
                    optimum,
                    run_seed,
                    "repo-SA-LC+pivot",
                    mixed_graph.number_of_edges(),
                    f"{mixed_seconds:.6f}",
                ]
            )
        if (graph_index + 1) % 10 == 0:
            print(f"Compared {graph_index + 1}/{len(rows)} graphs", flush=True)

    with RESULTS_PATH.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "n",
                "input_edges",
                "certified_mer",
                "seed",
                "method",
                "found_edges",
                "runtime_seconds",
            ]
        )
        writer.writerows(output_rows)
    return output_rows


def run_ilp_comparison(rows, count, iterations):
    candidates = [
        row
        for row in rows
        if int(row["n"]) == min(SIZES)
        and int(row["edges"]) > int(row["certified_mer"])
    ][:count]
    output_rows = []
    for row in candidates:
        graph = as_networkx(row)
        optimum = int(row["certified_mer"])

        np.random.seed(20261027)
        result = edm_sa_ilp(graph, iterations, 10.0)
        if round(result[3]) != optimum:
            raise RuntimeError(f"Author SA-ILP missed certified MER for {row['id']}")
        output_rows.append(
            [
                row["id"],
                "author-SA-ILP",
                optimum,
                result[3],
                f"{result[4]:.6f}",
                f"{result[5]:.6f}",
            ]
        )

        start = time.perf_counter()
        mixed_graph, _, _ = edm_lc_pivot_sa(
            graph, iterations, 10.0, random_state=20261027
        )
        ilp_graph, ilp_edges, ilp_seconds = edm_ilp(mixed_graph)
        total_seconds = time.perf_counter() - start
        if round(ilp_edges) != optimum or ilp_graph.number_of_edges() != optimum:
            raise RuntimeError(f"Mixed-SA-ILP missed certified MER for {row['id']}")
        output_rows.append(
            [
                row["id"],
                "repo-SA-LC+pivot-ILP",
                optimum,
                ilp_edges,
                f"{total_seconds:.6f}",
                f"{ilp_seconds:.6f}",
            ]
        )

    with ILP_RESULTS_PATH.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            ["id", "method", "certified_mer", "found_edges", "total_seconds", "ilp_seconds"]
        )
        writer.writerows(output_rows)
    return output_rows


def write_summary(rows, ilp_rows, iterations, seeds):
    results = list(csv.DictReader(RESULTS_PATH.open()))
    lines = [
        "# Larger-graph SA comparison",
        "",
        f"Certified LC-scrambled random-tree instances: {len(rows)} graphs across "
        f"n={', '.join(map(str, SIZES))}; {len(seeds)} seeds per graph; "
        f"{iterations} iterations and initial temperature 10.0.",
        "Each target is n-1: the input is LC-equivalent to a tree, and local "
        "complementation preserves connectivity.",
        "",
        "| n | Graphs | Method | Mean found/MER | Mean edge excess | Mean excess (%) | Mean runtime (s) |",
        "|---:|---:|---|---:|---:|---:|---:|",
    ]
    for size in SIZES:
        subset = [result for result in results if int(result["n"]) == size]
        graph_count = len({result["id"] for result in subset})
        for method in ("author-SA-LC", "repo-SA-LC+pivot"):
            method_rows = [result for result in subset if result["method"] == method]
            ratios = [
                int(result["found_edges"]) / int(result["certified_mer"])
                for result in method_rows
            ]
            mean_ratio = sum(ratios) / len(ratios)
            mean_excess = sum(
                int(result["found_edges"]) - int(result["certified_mer"])
                for result in method_rows
            ) / len(method_rows)
            mean_excess_percent = sum(
                (int(result["found_edges"])
                 - int(result["certified_mer"]))
                / int(result["certified_mer"])
                for result in method_rows
            ) / len(method_rows) * 100
            runtime = sum(float(result["runtime_seconds"]) for result in method_rows)
            lines.append(
                f"| {size} | {graph_count} | {method} | "
                f"{mean_ratio:.4f} | {mean_excess:.3f} | "
                f"{mean_excess_percent:.2f}% | {runtime / len(method_rows):.4f} |"
            )
    lines += [
        "",
        "## SA-ILP spot check",
        "",
        "The original SA-ILP and mixed-SA-ILP use the same ILP implementation; "
        "this compares their different SA preprocessing on selected n=13 cases.",
        "",
        "| Graph | Method | Certified MER | Found | Total time (s) | ILP time (s) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for result in ilp_rows:
        lines.append(
            f"| {result[0]} | {result[1]} | {result[2]} | {float(result[3]):.0f} | "
            f"{result[4]} | {result[5]} |"
        )
    lines += [
        "",
        "Run `python3 extra_data/project/scripts/run_large_comparison.py` to "
        "regenerate the dataset, CSVs, and this summary.",
        "The set is intentionally planted with known optima; it does not measure "
        "performance on arbitrary graphs whose MER is unknown.",
    ]
    SUMMARY_PATH.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graphs-per-size", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--ilp-count", type=int, default=2)
    args = parser.parse_args()
    if (
        args.graphs_per_size < 1
        or args.iterations < 1
        or args.seeds < 1
        or args.ilp_count < 0
    ):
        parser.error("graphs-per-size, iterations, and seeds must be positive; ilp-count cannot be negative")
    rows = generate_dataset(args.graphs_per_size)
    seeds = [11 + 12 * index for index in range(args.seeds)]
    run_sa_comparison(rows, args.iterations, seeds)
    ilp_rows = run_ilp_comparison(rows, args.ilp_count, args.iterations)
    write_summary(rows, ilp_rows, args.iterations, seeds)


if __name__ == "__main__":
    main()
