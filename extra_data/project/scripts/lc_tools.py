"""Bitset graph tools: local complementation (LC), pivots, exact orbit scan, scrambling.
A graph on n vertices is a list of n Python ints; bit j of rows[i] is 1 iff i~j."""
import random
OPS = [0]   # hardware-independent work counter (word-level operations)

def edges(rows): return sum(r.bit_count() for r in rows) // 2

def nbrs(mask):
    out = []
    while mask:
        a = mask & -mask; mask ^= a; out.append(a.bit_length() - 1)
    return out

def delta(rows, v):
    """exact change in edge count of LC at v:  C(d,2) - 2*e(N(v))"""
    nb = rows[v]; d = nb.bit_count()
    if d < 2: return 0
    e2 = 0; m = nb
    while m:
        a = m & -m; m ^= a
        e2 += (rows[a.bit_length() - 1] & nb).bit_count()
    OPS[0] += d
    return d * (d - 1) // 2 - e2

def lc(rows, v):
    nb = rows[v]; r = list(rows); m = nb
    while m:
        a = m & -m; m ^= a
        r[a.bit_length() - 1] ^= nb & ~a
    OPS[0] += nb.bit_count()
    return r

def pivot(rows, u, v):
    """pivot on edge uv = LC at u, v, u"""
    return lc(lc(lc(rows, u), v), u)

def pivot_delta(rows, u, v):
    """exact edge change of a pivot. A=N(u)\\N[v], B=N(v)\\N[u], C=N(u)&N(v): all pairs between different
    classes are toggled; u and v swap neighbourhoods (edge count unchanged by the swap)."""
    nu = rows[u] & ~(1 << v); nv = rows[v] & ~(1 << u)
    A = nu & ~nv; B = nv & ~nu; C = nu & nv
    def e(X, Y):
        s = 0; m = X
        while m:
            a = m & -m; m ^= a
            s += (rows[a.bit_length() - 1] & Y).bit_count()
        return s
    a, b, c = A.bit_count(), B.bit_count(), C.bit_count()
    OPS[0] += 2 * a + b + 1      # e(A,B), e(A,C) iterate over A; e(B,C) over B
    return a * b + a * c + b * c - 2 * (e(A, B) + e(A, C) + e(B, C))

def edge_list(rows):
    OPS[0] += len(rows)
    return [(u, v) for u in range(len(rows)) for v in nbrs(rows[u]) if v > u]

def connected(rows):
    n = len(rows); vis = {0}; st = [0]
    while st:
        x = st.pop()
        for y in nbrs(rows[x]):
            if y not in vis: vis.add(y); st.append(y)
    return len(vis) == n

def scramble(rows, steps, rng):
    """lazy random walk on the LC orbit (uniform stationary distribution; ~5n steps mix edge counts)"""
    r = list(rows); n = len(r)
    for _ in range(steps):
        v = rng.randrange(n)
        if r[v].bit_count() >= 2: r = lc(r, v)
    return r

def orbit_scan(rows, rng, k=4, cap=800_000):
    """Breadth-first enumeration of the whole LC-orbit. Returns exact MER, orbit size, a canonical fingerprint
    (lexicographically smallest member) and k uniform random members (reservoir sample)."""
    s = tuple(rows); seen = {s}; fr = [s]
    best = edges(rows); minrep = s; res = [s]; cnt = 1
    while fr:
        nf = []
        for g in fr:
            for v in range(len(g)):
                h = tuple(lc(list(g), v))
                if h not in seen:
                    seen.add(h); nf.append(h); cnt += 1
                    e = edges(list(h))
                    if e < best: best = e
                    if h < minrep: minrep = h
                    if len(res) < k: res.append(h)
                    else:
                        j = rng.randrange(cnt)
                        if j < k: res[j] = h
        fr = nf
        if len(seen) > cap:
            return dict(complete=False, size=len(seen))
    return dict(complete=True, mer=best, size=len(seen), minrep=minrep, starts=[list(x) for x in res])
