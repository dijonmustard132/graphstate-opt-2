"""Run every heuristic at several work budgets.   usage: python3 run_budget_sweep.py <split> <seeds> [b1,b2,...]
Default budgets are for n<=12 classes; the planted n=30 class uses its own (larger) list."""
import csv, random, sys, time
from lc_tools import *
from generators import from_str
from methods import METHODS
split = sys.argv[1]; SEEDS = int(sys.argv[2])
small = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [500, 1000, 2000, 4000, 10000]
BUDGETS = {"default": small, "PLANT": [20000, 50000, 100000, 300000]}
rows = [r for r in csv.DictReader(open("../data/manifest.csv")) if r["split"] == split]
out = open(f"../results/sweep_{split}.csv", "w", newline=""); w = csv.writer(out)
w.writerow(["id", "class", "orbit_id", "method", "budget", "seed", "found", "mer"])
t0 = time.time()
for k, r in enumerate(rows):
    g = from_str(int(r["n"]), r["graph"])
    for b in BUDGETS.get(r["class"], BUDGETS["default"]):
        for name, fn in METHODS.items():
            for s in range(SEEDS):
                found = fn(g, b, random.Random(1000 * s + int(r["seed"]) % 997 + k))
                w.writerow([r["id"], r["class"], r["orbit_id"], name, b, s, found, r["mer"]])
    out.flush()
    if k % 10 == 0: print(f"{split}: {k+1}/{len(rows)} instances, {time.time()-t0:.0f}s", flush=True)
print(split, "done", f"{time.time()-t0:.0f}s")
