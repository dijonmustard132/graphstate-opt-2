#!/usr/bin/env python3
"""Central entry point for the repository's benchmark comparisons."""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[2]


def run(command, cwd=REPO):
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=("large", "arbitrary", "custom", "all"), default="all")
    parser.add_argument("--quick", action="store_true", help="Use smaller graph counts and skip ILP")
    parser.add_argument("--no-ilp", action="store_true", help="Skip ILP spot checks")
    parser.add_argument("--large-graphs", type=int)
    parser.add_argument("--arbitrary-graphs", type=int)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seeds", type=int, default=20)
    args = parser.parse_args()

    large_graphs = args.large_graphs if args.large_graphs is not None else (2 if args.quick else 8)
    arbitrary_graphs = args.arbitrary_graphs if args.arbitrary_graphs is not None else (1 if args.quick else 2)

    if args.only in ("large", "all"):
        command = [
            sys.executable,
            str(PROJECT / "scripts" / "run_large_comparison.py"),
            "--graphs-per-size", str(large_graphs),
            "--iterations", str(args.iterations),
            "--seeds", str(args.seeds),
            "--ilp-count", "0" if args.quick or args.no_ilp else "2",
        ]
        run(command)

    if args.only in ("arbitrary", "all"):
        command = [
            sys.executable,
            str(PROJECT / "scripts" / "run_arbitrary_comparison.py"),
            "--graphs-per-cell", str(arbitrary_graphs),
            "--iterations", str(args.iterations),
            "--seeds", str(args.seeds),
        ]
        run(command)

    if args.only == "custom":
        scripts = PROJECT / "scripts"
        run([sys.executable, "run_experiments.py", "test", str(args.seeds)], cwd=scripts)
        run([sys.executable, "aggregate.py"], cwd=scripts)


if __name__ == "__main__":
    main()
