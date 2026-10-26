"""Planted n=30 trees (certified MER = 29) at low budgets, all splits pooled (10 instances).   usage: python3 run_planted_sweep.py [seeds]"""
import csv, random, sys, statistics as st, collections
from lc_tools import *
from generators import from_str
from methods import METHODS
SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
BUD = [1000, 2000, 5000, 10000, 20000]
rows = [r for r in csv.DictReader(open("../data/manifest.csv")) if r["class"] == "PLANT"]
res = collections.defaultdict(list)
for k, r in enumerate(rows):
    g = from_str(int(r["n"]), r["graph"]); mer = int(r["mer"])
    for b in BUD:
        for name, fn in METHODS.items():
            for s in range(SEEDS):
                f = fn(g, b, random.Random(1000 * s + int(r["seed"]) % 997 + k)); res[(name, b)].append((f / mer, f == mer))
lines = ["| Method | " + " | ".join(f"{b:,}" for b in BUD) + " |", "|---|" + "---|" * len(BUD)]
for name in METHODS:
    lines.append(f"| {name} | " + " | ".join(f"{st.mean(x[0] for x in res[(name,b)]):.3f} ({100*st.mean(x[1] for x in res[(name,b)]):.0f}%)" for b in BUD) + " |")
txt = f"**Planted n=30 trees, low budgets** ({len(rows)} instances x {SEEDS} seeds; mean found/MER and exact-hit share)\n\n" + "\n".join(lines)
open("../results/planted_low_budget.md", "w").write(txt + "\n"); print(txt)
