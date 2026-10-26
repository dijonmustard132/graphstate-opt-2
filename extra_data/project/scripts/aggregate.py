import csv, random, statistics as st, collections
CLASSES = ["ER", "BD", "RES", "TREE", "GHZ", "REP", "PLANT"]
NAMES = {"ER": "ER random", "BD": "Bounded degree", "RES": "Resource states", "TREE": "Trees", "GHZ": "GHZ-type",
         "REP": "Repeater-like", "PLANT": "Planted n=30"}
METH = ["SA (LC)", "SA (LC+pivot)", "ILS (LC)", "ILS (LC+pivot)", "Tabu (LC)", "Tabu commit (LC)", "Tabu (LC+pivot)", "Tabu (pivot only)"]
def load(splits):
    runs = []
    for sp in splits:
        for r in csv.DictReader(open(f"../results/raw_{sp}.csv")):
            runs.append((r['id'], r['class'], r['orbit_id'], r['method'], int(r['found']), int(r['mer'])))
    return runs
def per_instance(runs):
    d = collections.defaultdict(list)
    for iid, cls, oid, m, f, mer in runs: d[(iid, cls, oid, m)].append((f / mer, f == mer))
    return {k: (st.mean(x[0] for x in v), st.mean(x[1] for x in v)) for k, v in d.items()}
def table(inst, title):
    lines = [f"**{title}**", "", "| Method | " + " | ".join(NAMES[c] for c in CLASSES) + " | All (excl. planted) |", "|---|" + "---|" * (len(CLASSES) + 1)]
    for m in METH:
        cells = []; allr = []; alle = []
        for c in CLASSES:
            v = [x for k, x in inst.items() if k[1] == c and k[3] == m]
            cells.append(f"{st.mean(x[0] for x in v):.3f} ({100*st.mean(x[1] for x in v):.0f}%)")
            if c != "PLANT": allr += [x[0] for x in v]; alle += [x[1] for x in v]
        lines.append(f"| {m} | " + " | ".join(cells) + f" | {st.mean(allr):.3f} ({100*st.mean(alle):.0f}%) |")
    n = {c: len({k[0] for k in inst if k[1] == c}) for c in CLASSES}
    lines += ["", "Instances per class: " + ", ".join(f"{NAMES[c]} {n[c]}" for c in CLASSES) + ". Cells: mean found/MER (share of runs reaching the exact minimum)."]
    return "\n".join(lines)
rr = random.Random(0)
def paired(inst, a, b, cls=None, B=4000):
    orb = collections.defaultdict(list)
    for k, x in inst.items():
        if k[3] != a or (cls and k[1] != cls) or (not cls and k[1] == "PLANT"): continue
        y = inst[(k[0], k[1], k[2], b)]
        orb[(k[1], k[2])].append((x[0] - y[0], x[1] - y[1]))
    d = [st.mean(t[0] for t in v) for v in orb.values()]; e = [st.mean(t[1] for t in v) for v in orb.values()]
    bs = sorted(st.mean(rr.choice(d) for _ in d) for _ in range(B))
    return st.mean(d), bs[int(.025 * B)], bs[int(.975 * B)], 100 * st.mean(e), len(d)
def pivot_table(inst, title):
    pairs = [("SA", "SA (LC+pivot)", "SA (LC)"), ("ILS", "ILS (LC+pivot)", "ILS (LC)"), ("Tabu", "Tabu (LC+pivot)", "Tabu (LC)"), ("Tabu vs commit", "Tabu (LC+pivot)", "Tabu commit (LC)")]
    lines = [f"**{title}**", "", "| Comparison (first minus second) | " + " | ".join(NAMES[c] for c in CLASSES if c != "PLANT") + " | All (orbits) | 95% CI (all) |", "|---|" + "---|" * 8]
    for nm, a, b in pairs:
        cells = []
        for c in CLASSES:
            if c == "PLANT": continue
            m, lo, hi, ex, n = paired(inst, a, b, c); cells.append(f"{m:+.3f}")
        m, lo, hi, ex, n = paired(inst, a, b)
        lines.append(f"| {nm}: {a} - {b} | " + " | ".join(cells) + f" | {m:+.4f} (exact-hit {ex:+.1f} pts, {n} orbits) | [{lo:+.4f}, {hi:+.4f}] |")
    lines += ["", "Negative = the pivot variant found smaller graphs. Unit of analysis = orbit (seeds and starts averaged within an orbit)."]
    return "\n".join(lines)
test = per_instance(load(["test"])); allsp = per_instance(load(["test", "val", "train"]))
test_seeds = len({r["seed"] for r in csv.DictReader(open("../results/raw_test.csv"))})
out = [table(test, f"Table 1. Test split (budget 10,000 work units; planted 300,000; {test_seeds} seeds)"), "",
       pivot_table(test, "Table 2. Effect of adding pivot moves, test split"), "",
       pivot_table(allsp, "Table 3. Same comparison pooled over all splits (more orbits; robustness check)"), "",
       table(allsp, "Table 4. All splits pooled")]
open("../results/results.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
