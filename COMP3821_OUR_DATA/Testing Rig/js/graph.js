// ============================================================================
// DETERMINISTIC PRNG (Mulberry32)
// ============================================================================
export function mulberry32(a) {
  return function() {
    let t = a += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

export function randInt(rng, min, max) {
  return Math.floor(rng() * (max - min)) + min;
}

// ============================================================================
// FAST GRAPH DATA STRUCTURE & ZERO-ALLOCATION DELTAS
// ============================================================================
export class Graph {
  constructor(n, adj = null) {
    this.n = n;
    this.adj = adj ? adj.map(r => new Uint8Array(r)) : Array.from({ length: n }, () => new Uint8Array(n));
  }

  clone() {
    const g = new Graph(this.n);
    for (let i = 0; i < this.n; i++) g.adj[i].set(this.adj[i]);
    return g;
  }

  addEdge(u, v) {
    if (u !== v) {
      this.adj[u][v] = 1;
      this.adj[v][u] = 1;
    }
  }

  hasEdge(u, v) {
    return this.adj[u][v] === 1;
  }

  numEdges() {
    let c = 0;
    for (let i = 0; i < this.n; i++) {
      const row = this.adj[i];
      for (let j = i + 1; j < this.n; j++) {
        if (row[j]) c++;
      }
    }
    return c;
  }

  degree(v) {
    let d = 0;
    const row = this.adj[v];
    for (let i = 0; i < this.n; i++) d += row[i];
    return d;
  }

  neighbors(v) {
    const nb = [];
    const row = this.adj[v];
    for (let i = 0; i < this.n; i++) {
      if (row[i]) nb.push(i);
    }
    return nb;
  }

  clustering(v) {
    const nb = this.neighbors(v);
    const d = nb.length;
    if (d < 2) return 0.0;
    let internal = 0;
    for (let i = 0; i < d; i++) {
      const row = this.adj[nb[i]];
      for (let j = i + 1; j < d; j++) {
        if (row[nb[j]]) internal++;
      }
    }
    return internal / ((d * (d - 1)) / 2);
  }

  averageClustering() {
    let s = 0;
    for (let i = 0; i < this.n; i++) s += this.clustering(i);
    return s / this.n;
  }

  deltaE(v) {
    Graph.ensureScratch(this.n);
    const rowV = this.adj[v];
    const nb = Graph._scratchNb;
    let d = 0;
    for (let i = 0; i < this.n; i++) {
      if (rowV[i]) nb[d++] = i;
    }
    if (d < 2) return 0;
    let internal = 0;
    for (let i = 0; i < d; i++) {
      const row = this.adj[nb[i]];
      for (let j = i + 1; j < d; j++) {
        if (row[nb[j]]) internal++;
      }
    }
    return ((d * (d - 1)) >> 1) - (2 * internal);
  }

  localComplement(v) {
    Graph.ensureScratch(this.n);
    const rowV = this.adj[v];
    const nb = Graph._scratchNb;
    let d = 0;
    for (let i = 0; i < this.n; i++) {
      if (rowV[i]) nb[d++] = i;
    }
    for (let i = 0; i < d; i++) {
      const u = nb[i];
      const rowU = this.adj[u];
      for (let j = i + 1; j < d; j++) {
        const w = nb[j];
        rowU[w] ^= 1;
        this.adj[w][u] ^= 1;
      }
    }
  }

  pivot(u, v) {
    this.localComplement(u);
    this.localComplement(v);
    this.localComplement(u);
  }

  pivotDelta(u, v) {
    Graph.ensureScratch(this.n);
    const onlyU = Graph._scratchU;
    const onlyV = Graph._scratchV;
    const common = Graph._scratchC;
    let lenU = 0, lenV = 0, lenC = 0;

    const rowU = this.adj[u];
    const rowV = this.adj[v];
    const n = this.n;

    for (let i = 0; i < n; i++) {
      if (i === u || i === v) continue;
      const inU = rowU[i];
      const inV = rowV[i];
      if (inU && inV) common[lenC++] = i;
      else if (inU) onlyU[lenU++] = i;
      else if (inV) onlyV[lenV++] = i;
    }

    const toggledPairs = (lenU * lenV) + (lenU * lenC) + (lenV * lenC);
    let existingToggled = 0;

    for (let i = 0; i < lenU; i++) {
      const row = this.adj[onlyU[i]];
      for (let j = 0; j < lenV; j++) {
        if (row[onlyV[j]]) existingToggled++;
      }
    }
    for (let i = 0; i < lenU; i++) {
      const row = this.adj[onlyU[i]];
      for (let j = 0; j < lenC; j++) {
        if (row[common[j]]) existingToggled++;
      }
    }
    for (let i = 0; i < lenV; i++) {
      const row = this.adj[onlyV[i]];
      for (let j = 0; j < lenC; j++) {
        if (row[common[j]]) existingToggled++;
      }
    }

    return toggledPairs - 2 * existingToggled;
  }

  static ensureScratch(n) {
    if (!Graph._scratchN || Graph._scratchN < n) {
      const cap = Math.max(n * 2, 256);
      Graph._scratchNb = new Int32Array(cap);
      Graph._scratchU = new Int32Array(cap);
      Graph._scratchV = new Int32Array(cap);
      Graph._scratchC = new Int32Array(cap);
      Graph._scratchN = cap;
    }
  }
}

export function fastHash(graph) {
  let h = 0x811c9dc5;
  const n = graph.n;
  for (let i = 0; i < n; i++) {
    const row = graph.adj[i];
    let chunk = 0;
    for (let j = 0; j < n; j++) {
      chunk = (chunk << 1) | row[j];
      if ((j & 31) === 31 || j === n - 1) {
        h = Math.imul(h ^ chunk, 0x01000193);
        chunk = 0;
      }
    }
  }
  return h | 0;
}