import csv, random, sys, time
from lc_tools import *
from generators import from_str
from methods import METHODS
SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
BUDGET = {"default": 10000, "PLANT": 300000}
split = sys.argv[1] if len(sys.argv) > 1 else "test"
rows = [r for r in csv.DictReader(open("../data/manifest.csv")) if r["split"] == split]
out = open(f"../results/raw_{split}.csv", "w", newline=""); w = csv.writer(out)
w.writerow(["id", "class", "orbit_id", "method", "seed", "found", "mer"])
t0 = time.time()
for k, r in enumerate(rows):
    n = int(r["n"]); g = from_str(n, r["graph"]); b = BUDGET.get(r["class"], BUDGET["default"])
    for name, fn in METHODS.items():
        for s in range(SEEDS):
            found = fn(g, b, random.Random(1000 * s + int(r["seed"]) % 997 + k))
            w.writerow([r["id"], r["class"], r["orbit_id"], name, s, found, r["mer"]])
    out.flush()
    if k % 10 == 0: print(f"{k+1}/{len(rows)} instances, {time.time()-t0:.0f}s", flush=True)
print("done", f"{time.time()-t0:.0f}s")
