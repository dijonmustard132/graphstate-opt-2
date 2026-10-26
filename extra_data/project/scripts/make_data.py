import random, csv, hashlib, sys, time
from lc_tools import *
from generators import *
MASTER = 2026
rng = random.Random(MASTER)
CAP = 800_000
rows_out = []; seen_orbits = {}; log = []

def orbit_id(minrep): return hashlib.md5(repr(minrep).encode()).hexdigest()[:10]

def add_instance(cls, gen, g, scan, oid, seed):
    rows_out.append({"id": f"{cls}-{len(rows_out):04d}", "class": cls, "generator": gen, "n": len(g), "edges": edges(g),
        "mer": scan['mer'], "label_source": "enumeration", "orbit_id": oid, "orbit_size": scan['size'], "seed": seed,
        "split": "", "graph": to_str(g)})

def process(cls, gen, g, seed, use_original, nstarts):
    scan = orbit_scan(g, random.Random(seed), k=nstarts, cap=CAP)
    if not scan['complete']:
        log.append(f"SKIP {cls}/{gen}: orbit exceeds cap"); return
    if scan['mer'] == 0:
        log.append(f"SKIP {cls}/{gen}: no edges"); return
    oid = orbit_id(scan['minrep'])
    if oid in seen_orbits:
        log.append(f"MERGE {cls}/{gen}: same orbit as {seen_orbits[oid]}"); return
    seen_orbits[oid] = f"{cls}/{gen}"
    starts = [g] if use_original else scan['starts'][:nstarts]
    for st in starts: add_instance(cls, gen, st, scan, oid, seed)

t0 = time.time()
for n in (10, 11, 12):                       # 1 ER graphs, including sparse and dense regimes
    for p in (0.1, 0.2, 0.3, 0.5, 0.8, 0.9):
        for i in range(6):
            seed = rng.randrange(10**9); g = er(n, p, random.Random(seed))
            process("ER", f"ER(n={n},p={p})", g, seed, True, 1)
print("ER done", len(rows_out), f"{time.time()-t0:.0f}s", flush=True)
for n in (10, 11, 12):                       # 2 bounded degree d<=5, Havel-Hakimi
    for i in range(8):
        seed = rng.randrange(10**9); g = bounded_degree(n, 5, random.Random(seed))
        process("BD", f"BD(n={n},dlim=5)", g, seed, True, 1)
print("BD done", len(rows_out), f"{time.time()-t0:.0f}s", flush=True)
res_bases = [(f"path P{n}", path(n)) for n in (8, 9, 10, 11, 12)] + [(f"ring C{n}", cycle(n)) for n in (8, 9, 10, 11, 12)] + \
            [("ladder 2x4", grid(2, 4)), ("ladder 2x5", grid(2, 5)), ("ladder 2x6", grid(2, 6)), ("grid 3x3", grid(3, 3)), ("grid 3x4", grid(3, 4))]
for name, g in res_bases:                    # 3 MBQC resource states: scrambled orbit members
    process("RES", name, g, rng.randrange(10**9), False, 3)
print("RES done", len(rows_out), f"{time.time()-t0:.0f}s", flush=True)
for n in (9, 10, 11, 12):                    # 4 random trees
    for i in range(6):
        seed = rng.randrange(10**9); g = rand_tree(n, random.Random(seed))
        process("TREE", f"random tree n={n}", g, seed, False, 2)
print("TREE done", len(rows_out), f"{time.time()-t0:.0f}s", flush=True)
ghz = [("complete K8", complete(8)), ("complete K10", complete(10)), ("complete K12", complete(12)), ("star S10", star(10)),
       ("K_{4,4}", kbip(4, 4)), ("K_{5,5}", kbip(5, 5)), ("K_{6,6}", kbip(6, 6)), ("K_{3,7}", kbip(3, 7)), ("K_{4,8}", kbip(4, 8)),
       ("wheel W8", wheel(8)), ("wheel W10", wheel(10)), ("wheel W12", wheel(12))]
for name, g in ghz:                          # 5 GHZ-type
    process("GHZ", name, g, rng.randrange(10**9), False, 4)
print("GHZ done", len(rows_out), f"{time.time()-t0:.0f}s", flush=True)
process("REP", "RGS m=2", rgs(2), rng.randrange(10**9), False, 3)     # 6 repeater-like
process("REP", "RGS m=3", rgs(3), rng.randrange(10**9), False, 3)
for c in (5, 6):
    for p in (0.7, 0.8, 0.9):
        for i in range(2):
            seed = rng.randrange(10**9); g = dense_core_leaves(c, p, random.Random(seed))
            process("REP", f"dense core c={c},p={p} + leaves", g, seed, False, 2)
print("REP done", len(rows_out), f"{time.time()-t0:.0f}s", flush=True)
for i in range(10):                          # 7 planted trees, certified MER = n-1
    seed = rng.randrange(10**9); r = random.Random(seed)
    g = scramble(rand_tree(30, r), 300, r); assert connected(g)
    rows_out.append({"id": f"PLANT-{len(rows_out):04d}", "class": "PLANT", "generator": "scrambled random tree n=30 (10n steps)",
        "n": 30, "edges": edges(g), "mer": 29, "label_source": "planted", "orbit_id": f"planted-{i:02d}", "orbit_size": "",
        "seed": seed, "split": "", "graph": to_str(g)})

srng = random.Random(MASTER + 1)             # split by orbit within each class: 40% test / 20% val / 40% train
by_class = {}
for r in rows_out: by_class.setdefault(r['class'], {}).setdefault(r['orbit_id'], []).append(r)
for cls, orbs in by_class.items():
    ids = sorted(orbs); srng.shuffle(ids); k = len(ids)
    n_test = max(1, round(0.4 * k)); n_val = round(0.2 * k) if k >= 3 else 0
    for j, oid in enumerate(ids):
        sp = "test" if j < n_test else ("val" if j < n_test + n_val else "train")
        for r in orbs[oid]: r['split'] = sp
cols = ["id", "class", "generator", "n", "edges", "mer", "label_source", "orbit_id", "orbit_size", "seed", "split", "graph"]
with open("../data/manifest.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows_out)
open("../data/generation_log.txt", "w").write("\n".join(log) + "\n")
print("total instances:", len(rows_out), f"time {time.time()-t0:.0f}s")
for l in log: print(l)
