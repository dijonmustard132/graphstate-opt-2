"""Heuristics compared in the experiments. All take (rows, budget, rng) and return the best edge count found.
Budget = work units from lc_tools.OPS (hardware independent)."""
import math, random, threading, time
from collections import deque
from lc_tools import *


class LowestEdgeReporter:
    """Print the lowest edge count found periodically and when the final result is ready."""

    def __init__(self, interval=10.0):
        self.interval = interval
        self._lock = threading.Lock()
        self._best = {}
        self._started = time.monotonic()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._periodic, daemon=True)
        self._thread.start()

    def update(self, method, graph_id, edge_count):
        with self._lock:
            key = (method, graph_id)
            previous = self._best.get(key)
            if previous is None or edge_count < previous:
                self._best[key] = edge_count

    def snapshot(self):
        with self._lock:
            return dict(self._best)

    def _periodic(self):
        while not self._stop.wait(self.interval):
            elapsed = time.monotonic() - self._started
            values = self.snapshot()
            if values:
                print(f"[{elapsed:.0f}s] Lowest edge counts so far:", flush=True)
                for (method, graph_id), edges in sorted(values.items()):
                    print(f"  {method} | {graph_id}: {edges}", flush=True)

    def close(self):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=0.1)

T0, TEND, KICK, TENURE = 4.0, 0.3, 5, 7      # tuned earlier on separate ER training graphs (not re-tuned on this dataset)

def _apply(rows, mv):
    return lc(rows, mv[1]) if mv[0] == 'v' else pivot(rows, mv[1], mv[2])

def sa(rows, budget, rng, mixed=False, on_best=None):
    rows = list(rows); n = len(rows); E = edges(rows); best = E; OPS[0] = 0
    if on_best is not None: on_best(best)
    while OPS[0] < budget:
        T = T0 * (TEND / T0) ** min(OPS[0] / budget, 1)
        if mixed and rng.random() < 0.5:
            u = rng.randrange(n)
            if rows[u] == 0: OPS[0] += 1; continue
            nb = nbrs(rows[u]); OPS[0] += len(nb); v = rng.choice(nb)
            d = pivot_delta(rows, u, v); mv = ('e', u, v)
        else:
            v = rng.randrange(n)
            if rows[v].bit_count() < 2: OPS[0] += 1; continue
            d = delta(rows, v); mv = ('v', v)
        if d <= 0 or rng.random() < math.exp(-d / T):
            rows = _apply(rows, mv); E += d
            if E < best:
                best = E
                if on_best is not None: on_best(best)
    return best

def _moves(rows, mixed):
    mv = [('v', v) for v in range(len(rows)) if rows[v].bit_count() >= 2]
    if mixed: mv += [('e', u, v) for (u, v) in edge_list(rows)]
    return mv
def _score(rows, mv):
    return delta(rows, mv[1]) if mv[0] == 'v' else pivot_delta(rows, mv[1], mv[2])

def ils(rows, budget, rng, mixed=False, on_best=None):
    rows = list(rows); OPS[0] = 0
    def descend(r):
        while OPS[0] < budget:
            sc = [(_score(r, m), m) for m in _moves(r, mixed)]
            if not sc: return r
            mn = min(s for s, _ in sc)
            if mn >= 0: return r
            r = _apply(r, rng.choice([m for s, m in sc if s == mn]))
        return r
    cur = descend(rows); Ecur = edges(cur); best = Ecur
    if on_best is not None: on_best(best)
    while OPS[0] < budget:
        if not _moves(cur, mixed): return best
        r = list(cur)
        for _ in range(KICK):
            ms = _moves(r, mixed)
            if not ms: break
            r = _apply(r, rng.choice(ms))
        r = descend(r); E = edges(r)
        if E < best:
            best = E
            if on_best is not None: on_best(best)
        if E <= Ecur: cur, Ecur = r, E
    return best

def tabu(rows, budget, rng, use_lc=True, use_pivot=False, commit=False, on_best=None):
    """plain tabu on exact edge change over LC and/or pivot moves; commit=True adds the two-move plan (LC only)"""
    rows = list(rows); n = len(rows); E = edges(rows); best = E; OPS[0] = 0; tl = deque(maxlen=TENURE)
    if on_best is not None: on_best(best)
    while OPS[0] < budget:
        c = []
        if use_lc:
            for v in range(n):
                if rows[v].bit_count() < 2: continue
                d = delta(rows, v)
                if ('v', v) in tl and not (E + d < best): continue
                c.append((d, ('v', v), None))
                if commit:
                    g2 = lc(rows, v); bd = None; bu = None
                    for u in nbrs(rows[v]):
                        if g2[u].bit_count() < 2: continue
                        du = delta(g2, u)
                        if bd is None or du < bd: bd, bu = du, u
                    if bd is not None: c.append((d + bd, ('v', v), ('v', bu)))
        if use_pivot:
            for (u, v) in edge_list(rows):
                d = pivot_delta(rows, u, v)
                if ('e', u, v) in tl and not (E + d < best): continue
                c.append((d, ('e', u, v), None))
        if not c:
            has_moves = (
                (use_lc and any(rows[v].bit_count() >= 2 for v in range(n)))
                or (use_pivot and bool(edge_list(rows)))
            )
            if not has_moves: break
            tl.clear(); continue
        mn = min(x[0] for x in c); _, m1, m2 = rng.choice([x for x in c if x[0] == mn])
        rows = _apply(rows, m1); tl.append(m1)
        if m2 is not None: rows = _apply(rows, m2); tl.append(m2)
        E = edges(rows)
        if E < best:
            best = E
            if on_best is not None: on_best(best)
    return best

METHODS = {
    "SA (LC)":               lambda r, b, g, **kw: sa(r, b, g, **kw),
    "SA (LC+pivot)":         lambda r, b, g, **kw: sa(r, b, g, mixed=True, **kw),
    "ILS (LC)":              lambda r, b, g, **kw: ils(r, b, g, **kw),
    "ILS (LC+pivot)":        lambda r, b, g, **kw: ils(r, b, g, mixed=True, **kw),
    "Tabu (LC)":             lambda r, b, g, **kw: tabu(r, b, g, **kw),
    "Tabu commit (LC)":      lambda r, b, g, **kw: tabu(r, b, g, commit=True, **kw),
    "Tabu (LC+pivot)":       lambda r, b, g, **kw: tabu(r, b, g, use_pivot=True, **kw),
    "Tabu (pivot only)":     lambda r, b, g, **kw: tabu(r, b, g, use_lc=False, use_pivot=True, **kw),
}
