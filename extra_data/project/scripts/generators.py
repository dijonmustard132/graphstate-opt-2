import itertools, random
def from_edges(n, es):
    rows = [0] * n
    for a, b in es: rows[a] |= 1 << b; rows[b] |= 1 << a
    return rows
def to_str(rows):
    return ";".join(f"{u}-{v}" for u in range(len(rows)) for v in range(u + 1, len(rows)) if (rows[u] >> v) & 1)
def from_str(n, s):
    return from_edges(n, [tuple(map(int, t.split("-"))) for t in s.split(";") if t])
def path(n): return from_edges(n, [(i, i + 1) for i in range(n - 1)])
def cycle(n): return from_edges(n, [(i, (i + 1) % n) for i in range(n)])
def star(n): return from_edges(n, [(0, i) for i in range(1, n)])
def complete(n): return from_edges(n, list(itertools.combinations(range(n), 2)))
def kbip(a, b): return from_edges(a + b, [(i, a + j) for i in range(a) for j in range(b)])
def wheel(n): return from_edges(n, [(0, i) for i in range(1, n)] + [(i, i % (n - 1) + 1) for i in range(1, n)])
def grid(r, c):
    es = []
    for i in range(r):
        for j in range(c):
            if j + 1 < c: es.append((i * c + j, i * c + j + 1))
            if i + 1 < r: es.append((i * c + j, (i + 1) * c + j))
    return from_edges(r * c, es)
def rgs(m):   # repeater graph state: complete core on 2m vertices, one leaf on each core vertex
    k = 2 * m
    return from_edges(2 * k, list(itertools.combinations(range(k), 2)) + [(i, k + i) for i in range(k)])
def dense_core_leaves(c, p, rng):   # random dense core + one leaf per core vertex (generalised-repeater-like)
    es = [(i, j) for i in range(c) for j in range(i + 1, c) if rng.random() < p] + [(i, c + i) for i in range(c)]
    return from_edges(2 * c, es)
def er(n, p, rng):
    return from_edges(n, [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p])
def rand_tree(n, rng):
    return from_edges(n, [(i, rng.randrange(i)) for i in range(1, n)])
def havel_hakimi(deg):
    d = list(deg); n = len(d); es = []
    while True:
        order = sorted(range(n), key=lambda i: -d[i])
        v = order[0]
        if d[v] == 0: return es
        if d[v] > n - 1: return None
        d[v], k = 0, d[v]
        for u in order[1:k + 1]:
            if d[u] == 0: return None
            d[u] -= 1; es.append((v, u))
def bounded_degree(n, dlim, rng, tries=10000):
    """sample n positive integers <= dlim as a degree sequence, build with Havel-Hakimi, keep if connected (as in the paper's description)"""
    from lc_tools import connected
    for _ in range(tries):
        deg = [rng.randint(1, dlim) for _ in range(n)]
        if sum(deg) % 2: continue
        es = havel_hakimi(deg)
        if es is None: continue
        g = from_edges(n, es)
        if connected(g): return g
    raise RuntimeError("no bounded-degree graph found")
