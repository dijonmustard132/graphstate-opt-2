import csv, statistics as st, collections
METH = ["SA (LC)", "SA (LC+pivot)", "ILS (LC)", "ILS (LC+pivot)", "Tabu (LC)", "Tabu commit (LC)", "Tabu (LC+pivot)", "Tabu (pivot only)"]
SMALL = [500, 1000, 2000, 4000, 10000]; PL = [20000, 50000, 100000, 300000]
def load(splits):
    d = collections.defaultdict(list)       # (method, budget, class, instance) -> [(ratio, exact)]
    for sp in splits:
        for r in csv.DictReader(open(f"../results/sweep_{sp}.csv")):
            f, m = int(r['found']), int(r['mer'])
            d[(r['method'], int(r['budget']), r['class'], r['id'])].append((f / m, f == m))
    return {k: (st.mean(x[0] for x in v), st.mean(x[1] for x in v)) for k, v in d.items()}
def cell(inst, m, b, classes):
    v = [x for k, x in inst.items() if k[0] == m and k[1] == b and k[2] in classes]
    return f"{st.mean(x[0] for x in v):.3f} ({100*st.mean(x[1] for x in v):.0f}%)", len(v)
def tab(inst, title, classes, budgets):
    n = cell(inst, METH[0], budgets[0], classes)[1]
    L = [f"**{title}** ({n} instances)", "", "| Method | " + " | ".join(f"{b:,}" for b in budgets) + " |", "|---|" + "---|" * len(budgets)]
    for m in METH: L.append(f"| {m} | " + " | ".join(cell(inst, m, b, classes)[0] for b in budgets) + " |")
    return "\n".join(L)
def er_density_table():
    meta = {r["id"]: r for r in csv.DictReader(open("../data/manifest.csv"))}
    runs = collections.defaultdict(list)
    for r in csv.DictReader(open("../results/sweep_test.csv")):
        if r["class"] != "ER" or int(r["budget"]) != 2000 or r["method"] not in METH[:2]: continue
        p = float(meta[r["id"]]["generator"].split("p=")[1].rstrip(")"))
        band = "Sparse (p<=0.2)" if p <= 0.2 else ("Dense (p>=0.8)" if p >= 0.8 else "Mid (p=0.3/0.5)")
        found, mer = int(r["found"]), int(r["mer"])
        runs[(band, r["method"], r["id"])].append((found / mer, found == mer))
    by_group = collections.defaultdict(list)
    for (band, method, _), values in runs.items():
        by_group[(band, method)].append((st.mean(x[0] for x in values), st.mean(x[1] for x in values)))
    lines = ["**Table F. TEST, ER density breakdown at 2,000 OPS**", "",
             "| Density | Instances | SA (LC) mean ratio (exact hit) | SA (LC+pivot) mean ratio (exact hit) |",
             "|---|---:|---:|---:|"]
    for band in ("Sparse (p<=0.2)", "Mid (p=0.3/0.5)", "Dense (p>=0.8)"):
        lc = by_group[(band, METH[0])]
        mixed = by_group[(band, METH[1])]
        fmt = lambda values: f"{st.mean(x[0] for x in values):.3f} ({100*st.mean(x[1] for x in values):.0f}%)"
        lines.append(f"| {band} | {len(lc)} | {fmt(lc)} | {fmt(mixed)} |")
    return "\n".join(lines)
SIX = {"ER", "BD", "RES", "TREE", "GHZ", "REP"}
sel = load(["train", "val"]); test = load(["test"])
parts = [tab(sel, "Table A. Budget sweep on train+val (use this to CHOOSE budgets), six classes pooled, n<=12", SIX, SMALL), "",
         tab(sel, "Table B. Same, ER random only (the hardest class)", {"ER"}, SMALL), "",
         tab(sel, "Table C. Same, resource states only", {"RES"}, SMALL), "",
         tab(test, "Table D. Budget sweep on TEST (report this), six classes pooled", SIX, SMALL), "",
         tab(test, "Table E. TEST, ER random only", {"ER"}, SMALL), "",
         er_density_table(), "",
         tab(load(["train", "val", "test"]), "Table G. Planted n=30 trees (budget in work units), all splits pooled", {"PLANT"}, PL)]
open("../results/budget_sweep.md", "w").write("\n".join(parts) + "\n"); print("\n".join(parts))
