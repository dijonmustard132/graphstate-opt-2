#!/usr/bin/env python3
"""Compare algorithms by the lowest edge count found, without rating exact hits."""

import argparse
import csv
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

from lc_tools import *
from generators import from_str
from methods import METHODS, LowestEdgeReporter

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "data" / "manifest.csv"
RESULTS = PROJECT / "results"


def run_comparison(split="test", seeds=20, budget=None, progress_interval=10.0):
    rows = [row for row in csv.DictReader(DATA.open()) if row["split"] == split]
    raw_path = RESULTS / f"lowest_edges_{split}.csv"
    summary_path = RESULTS / f"lowest_edges_{split}.md"
    RESULTS.mkdir(parents=True, exist_ok=True)

    reporter = LowestEdgeReporter(progress_interval)
    output = raw_path.open("w", newline="")
    writer = csv.writer(output)
    writer.writerow(["id", "class", "orbit_id", "method", "seed", "found_edges", "known_mer"])

    per_instance = defaultdict(list)
    started = time.monotonic()
    try:
        for graph_index, row in enumerate(rows, 1):
            graph = from_str(int(row["n"]), row["graph"])
            graph_budget = budget if budget is not None else (
                300000 if row["class"] == "PLANT" else 10000
            )
            known_mer = int(row["mer"])

            for method, function in METHODS.items():
                for seed in range(seeds):
                    rng = random.Random(
                        1000 * seed + int(row["seed"])
                        % 997 + graph_index - 1
                    )
                    on_best = lambda best, m=method, g=row["id"]: reporter.update(m, g, best)
                    found = function(graph, graph_budget, rng, on_best=on_best)
                    reporter.update(method, row["id"], found)
                    writer.writerow([
                        row["id"], row["class"], row["orbit_id"], method,
                        seed, found, known_mer,
                    ])
                    per_instance[(row["class"], method)].append(found)
                    per_instance[("ALL", method)].append(found / known_mer)
            output.flush()

            if graph_index % 10 == 0:
                elapsed = time.monotonic() - started
                print(f"[{elapsed:.0f}s] Compared {graph_index}/{len(rows)} graphs", flush=True)
    finally:
        reporter.close()
        output.close()

    lines = [
        f"# Lowest-edge comparison: {split} split",
        "",
        f"{len(rows)} graphs; {seeds} seeds per graph; budget selected per graph class.",
        "Exact-hit counts are not used. Results are ranked by mean edge count and mean distance above the known MER.",
        "",
        "| Method | Mean edge count | Mean found/MER | Mean edge excess |",
        "|---|---:|---:|---:|",
    ]

    classes = sorted({row["class"] for row in rows})
    raw = list(csv.DictReader(raw_path.open()))
    for method in METHODS:
        method_rows = [row for row in raw if row["method"] == method]
        mean_edges = sum(int(row["found_edges"]) for row in method_rows) / len(method_rows)
        mean_ratio = sum(
            int(row["found_edges"]) / int(row["known_mer"])
            for row in method_rows
        ) / len(method_rows)
        mean_excess = sum(
            int(row["found_edges"]) - int(row["known_mer"])
            for row in method_rows
        ) / len(method_rows)
        lines.append(
            f"| {method} | {mean_edges:.3f} | {mean_ratio:.4f} | {mean_excess:.3f} |"
        )

    lines += [
        "",
        "## By graph class",
        "",
        "| Method | " + " | ".join(classes) + " |",
        "|---|" + "---|" * len(classes),
    ]
    for method in METHODS:
        cells = []
        for graph_class in classes:
            values = [
                int(row["found_edges"])
                for row in raw
                if row["method"] == method and row["class"] == graph_class
            ]
            mean_edges = sum(values) / len(values) if values else 0
            cells.append(f"{mean_edges:.3f}")
        lines.append(f"| {method} | " + " | ".join(cells) + " |")

    summary_path.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nLowest-edge raw results: {raw_path}")
    print(f"Lowest-edge summary: {summary_path}")
    return raw_path, summary_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", nargs="?", default="test", choices=("train", "val", "test"))
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--budget", type=int, default=None)
    parser.add_argument("--progress-interval", type=float, default=10.0)
    args = parser.parse_args()
    if args.seeds < 1 or args.progress_interval <= 0:
        parser.error("seeds must be positive and progress-interval must be greater than zero")
    run_comparison(args.split, args.seeds, args.budget, args.progress_interval)


if __name__ == "__main__":
    main()
