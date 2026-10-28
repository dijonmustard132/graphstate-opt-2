"""Compare LC-SA and LC+pivot-SA on arbitrary connected random graphs."""

import argparse
import csv
import io
import random
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from graphstate_opt.edm_ilp import edm_ilp
from graphstate_opt.edm_pivot import edm_lc_pivot_sa
from graphstate_opt.edm_sa import edm_sa
from graphstate_opt.edm_sa_ilp import edm_sa_ilp


SIZES = (13, 16, 20, 30)
PROBABILITIES = (0.15, 0.35, 0.55, 0.75)
DATA_PATH = ROOT / "data" / "arbitrary_manifest.csv"
RESULTS_PATH = ROOT / "results" / "arbitrary_comparison.csv"
ILP_RESULTS_PATH = ROOT / "results" / "arbitrary_ilp_comparison.csv"
SUMMARY_PATH = ROOT / "results" / "arbitrary_comparison.md"


def connected_random_graph(size, probability, seed):
    rng = random.Random(seed)
    graph_seed = seed
    while True:
        graph = nx.gnp_random_graph(size, probability, seed=graph_seed)
        if nx.is_connected(graph):
            return graph, graph_seed
        graph_seed = rng.randrange(2**32)


def generate_dataset(graphs_per_cell):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["id", "n", "p", "edges", "seed", "graph_seed", "graph"])
        for size in SIZES:
            for probability in PROBABILITIES:
                for index in range(graphs_per_cell):
                    seed = 20261027 + size * 100000 + round(probability * 100) * 100 + index
                    graph, graph_seed = connected_random_graph(size, probability, seed)
                    edge_list = ";".join(
                        f"{u}-{v}" for u, v in sorted(graph.edges())
                    )
                    writer.writerow(
                        [
                            f"ER-{size}-p{round(probability * 100):02d}-{index:02d}",
                            size,
                            probability,
                            graph.number_of_edges(),
                            seed,
                            graph_seed,
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
            graph.add_edge(*map(int, edge.split("-")))
    return graph


def run_sa_comparison(rows, iterations, seeds):
    results = []
    for graph_index, row in enumerate(rows):
        graph = as_networkx(row)
        for run_seed in seeds:
            np.random.seed(run_seed)
            start = time.perf_counter()
            author_graph, _, _ = edm_sa(graph, iterations, 10.0)
            author_seconds = time.perf_counter() - start
            results.append(
                [
                    row["id"],
                    row["n"],
                    row["p"],
                    row["edges"],
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
            results.append(
                [
                    row["id"],
                    row["n"],
                    row["p"],
                    row["edges"],
                    run_seed,
                    "repo-SA-LC+pivot",
                    mixed_graph.number_of_edges(),
                    f"{mixed_seconds:.6f}",
                ]
            )
        if (graph_index + 1) % 8 == 0:
            print(f"Compared {graph_index + 1}/{len(rows)} graphs", flush=True)

    with RESULTS_PATH.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            ["id", "n", "p", "input_edges", "seed", "method", "found_edges", "runtime_seconds"]
        )
        writer.writerows(results)
    return results


def run_ilp_comparison(rows, iterations):
    output_rows = []
    selected = [
        next(
            candidate
            for candidate in rows
            if int(candidate["n"]) == 13 and float(candidate["p"]) == probability
        )
        for probability in (0.15, 0.75)
    ]

    for row in selected:
        graph = as_networkx(row)
        for method, operation in (
            ("author-SA-ILP", lambda: edm_sa_ilp(graph, iterations, 10.0)),
            (
                "repo-SA-LC+pivot-ILP",
                lambda: mixed_sa_then_ilp(graph, iterations),
            ),
        ):
            captured = io.StringIO()
            start = time.perf_counter()
            try:
                with redirect_stdout(captured):
                    result = operation()
                status = (
                    "optimal"
                    if not captured.getvalue().strip()
                    else captured.getvalue().strip()
                )
                output_rows.append(
                    [
                        row["id"],
                        method,
                        row["n"],
                        row["p"],
                        row["edges"],
                        result[3] if method == "author-SA-ILP" else result[1],
                        f"{time.perf_counter() - start:.6f}",
                        result[5] if method == "author-SA-ILP" else result[2],
                        status,
                    ]
                )
            except Exception as error:
                output_rows.append(
                    [
                        row["id"],
                        method,
                        row["n"],
                        row["p"],
                        row["edges"],
                        "",
                        f"{time.perf_counter() - start:.6f}",
                        "",
                        f"error: {type(error).__name__}: {error}",
                    ]
                )

    with ILP_RESULTS_PATH.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "method",
                "n",
                "p",
                "input_edges",
                "found_edges",
                "total_seconds",
                "ilp_seconds",
                "solver_status",
            ]
        )
        writer.writerows(output_rows)
    return output_rows


def mixed_sa_then_ilp(graph, iterations):
    mixed_graph, _, _ = edm_lc_pivot_sa(
        graph, iterations, 10.0, random_state=20261027
    )
    output_graph, edge_count, ilp_seconds = edm_ilp(mixed_graph)
    return output_graph, edge_count, ilp_seconds


def write_summary(rows, ilp_rows, iterations, seeds):
    results = list(csv.DictReader(RESULTS_PATH.open()))
    lines = [
        "# Arbitrary random-graph comparison",
        "",
        f"Connected Erdős–Rényi samples: {len(rows)} graphs; n={', '.join(map(str, SIZES))}; "
        f"p={', '.join(map(str, PROBABILITIES))}; {len(seeds)} seeds per graph; "
        f"{iterations} iterations and initial temperature 10.0.",
        "Unlike the planted-tree test, these inputs are sampled directly as random graphs. "
        "Their exact MERs are unknown except where an ILP solve completes.",
        "",
        "| n | p | Graphs | Method | Mean edges found | Best edges | Mean runtime (s) |",
        "|---:|---:|---:|---|---:|---:|---:|",
    ]
    for size in SIZES:
        for probability in PROBABILITIES:
            subset = [
                result
                for result in results
                if int(result["n"]) == size and float(result["p"]) == probability
            ]
            graph_count = len({result["id"] for result in subset})
            for method in ("author-SA-LC", "repo-SA-LC+pivot"):
                method_rows = [result for result in subset if result["method"] == method]
                found = [int(result["found_edges"]) for result in method_rows]
                runtime = sum(float(result["runtime_seconds"]) for result in method_rows)
                lines.append(
                    f"| {size} | {probability:.2f} | {graph_count} | {method} | "
                    f"{sum(found) / len(found):.2f} | {min(found)} | "
                    f"{runtime / len(method_rows):.4f} |"
                )
    lines += [
        "",
        "## SA-ILP spot check",
        "",
        "The original SA-ILP and mixed-SA-ILP share the same ILP model; this compares "
        "their preprocessing on both a sparse and a dense arbitrary n=13 input. "
        "Solver status is recorded below.",
        "",
        "| Graph | Method | Input edges | Found | Total time (s) | ILP time (s) | Solver status |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for result in ilp_rows:
        lines.append(
            f"| {result[0]} | {result[1]} | {result[4]} | {result[5]} | "
            f"{result[6]} | {result[7]} | {result[8]} |"
        )
    lines += [
        "",
        "## Interpretation limits",
        "",
        "For arbitrary inputs, lower edge count does not prove a better MER without an "
        "exact optimum. The table therefore reports edge counts and runtime rather than "
        "inventing an approximation ratio. The n=13, p=0.50 ILP feasibility probe exceeded "
        "180 seconds and was stopped; denser/harder instances are assessed by the paired "
        "SA results, not by an unavailable exact label.",
        "",
        "Run `python3 extra_data/project/scripts/run_arbitrary_comparison.py` to regenerate "
        "the graphs and results.",
    ]
    SUMMARY_PATH.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graphs-per-cell", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seeds", type=int, default=20)
    args = parser.parse_args()
    if args.graphs_per_cell < 1 or args.iterations < 1 or args.seeds < 1:
        parser.error("graphs-per-cell, iterations, and seeds must be positive")
    rows = generate_dataset(args.graphs_per_cell)
    seeds = [11 + 12 * index for index in range(args.seeds)]
    run_sa_comparison(rows, args.iterations, seeds)
    ilp_rows = run_ilp_comparison(rows, args.iterations)
    write_summary(rows, ilp_rows, args.iterations, seeds)


if __name__ == "__main__":
    main()
