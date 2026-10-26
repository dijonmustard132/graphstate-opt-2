"""Independent checks on data/manifest.csv. Exit code 1 if anything fails."""
import csv, random, sys, collections
from lc_tools import *
from generators import from_str
rows = list(csv.DictReader(open("../data/manifest.csv"))); bad = []
def fail(r, msg): bad.append(f"{r['id']}: {msg}")
# 1 each orbit lives in exactly one split
sp = collections.defaultdict(set)
for r in rows: sp[(r['class'], r['orbit_id'])].add(r['split'])
for k, v in sp.items():
    if len(v) != 1: bad.append(f"orbit {k} spans splits {v}")
# 2 no duplicate graphs
seen = {}
for r in rows:
    key = (r['n'], r['graph'])
    if key in seen: fail(r, f"duplicate of {seen[key]}")
    seen[key] = r['id']
nchk = 0
for r in rows:
    n = int(r['n']); g = from_str(n, r['graph'])
    if edges(g) != int(r['edges']): fail(r, "edge count mismatch")
    if r['class'] in ("TREE", "PLANT", "GHZ") or r['label_source'] == "planted":
        if not connected(g): fail(r, "not connected")
    if r['class'] in ("TREE", "PLANT") and int(r['mer']) != n - 1: fail(r, f"tree-equivalent class but mer={r['mer']} != n-1")
    if r['class'] == "GHZ" and r['generator'].startswith("complete") and int(r['mer']) != n - 1: fail(r, "complete graph must collapse to n-1 edges")
    if int(r['mer']) > int(r['edges']): fail(r, "mer exceeds input edges")
    # 3 re-derive MER by an independent BFS for orbits of moderate size
    if r['label_source'] == "enumeration" and r['orbit_size'] and int(r['orbit_size']) <= 20000:
        s = orbit_scan(g, random.Random(0), k=1, cap=50000); nchk += 1
        if not s['complete'] or s['mer'] != int(r['mer']) or s['size'] != int(r['orbit_size']): fail(r, "re-enumeration disagrees")
    # 4 scrambled-from-start sanity: planted graphs are connected with >= n-1 edges
    if r['label_source'] == "planted" and int(r['edges']) < n - 1: fail(r, "fewer than n-1 edges")
print(f"checked {len(rows)} instances ({nchk} re-enumerated from the stored graph); failures: {len(bad)}")
for b in bad[:20]: print("  ", b)
sys.exit(1 if bad else 0)
