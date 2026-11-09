import { Graph, randInt, mulberry32 } from './graph.js';

export function scrambleGraph(g, numSteps, rng) {
  let applied = 0, attempts = 0;
  while (applied < numSteps && attempts < numSteps * 10) {
    attempts++;
    const v = randInt(rng, 0, g.n);
    if (g.degree(v) >= 2) {
      g.localComplement(v);
      applied++;
    }
  }
}

export function ensureConnected(g, rng) {
  const visited = new Uint8Array(g.n);
  const queue = [0];
  visited[0] = 1;
  let head = 0;
  while (head < queue.length) {
    const u = queue[head++];
    for (let v = 0; v < g.n; v++) {
      if (g.hasEdge(u, v) && !visited[v]) {
        visited[v] = 1;
        queue.push(v);
      }
    }
  }
  for (let i = 0; i < g.n; i++) {
    if (!visited[i]) {
      const target = queue[randInt(rng, 0, queue.length)];
      g.addEdge(i, target);
      visited[i] = 1;
      queue.push(i);
    }
  }
}

export const GRAPH_GENERATORS = {
  "report_tree/planted_scrambled": {
    name: "Planted Scrambled Tree",
    generate: (n, p, rng) => {
      const g = new Graph(n);
      for (let i = 1; i < n; i++) g.addEdge(i, randInt(rng, 0, i));
      scrambleGraph(g, 3 * n, rng);
      return { graph: g, groundTruth: n - 1, family: "Planted Tree" };
    }
  },
  "report_bipartite/complete_asymmetric": {
    name: "Complete Bipartite K(a, b)",
    generate: (n, splitA, rng) => {
      const a = Math.max(1, Math.min(n - 1, Math.floor(splitA || n / 2)));
      const b = n - a;
      const g = new Graph(n);
      for (let i = 0; i < a; i++) {
        for (let j = a; j < n; j++) g.addEdge(i, j);
      }
      return { graph: g, groundTruth: a + b - 1, family: "Bipartite Complete" };
    }
  },
  "report_bipartite/defective": {
    name: "Defective Bipartite K(a, b) \\ M",
    generate: (n, config, rng) => {
      const a = config.a || 6;
      const b = n - a;
      const removeCount = config.m || 1;
      const g = new Graph(n);
      for (let i = 0; i < a; i++) {
        for (let j = a; j < n; j++) g.addEdge(i, j);
      }
      let removed = 0;
      for (let i = 0; i < a && removed < removeCount; i++) {
        const j = a + (i % b);
        if (g.hasEdge(i, j)) {
          g.adj[i][j] = 0;
          g.adj[j][i] = 0;
          removed++;
        }
      }
      return { graph: g, groundTruth: n - 1, family: "Bipartite Defective" };
    }
  },
  "report_canonical/cabello_orbit": {
    name: "Cabello Canonical Orbit (n=8)",
    generate: (n, orbitId, rng) => {
      const g = new Graph(8);
      let targetMER = 7;
      if (orbitId === 1) {
        for (let i = 1; i < 8; i++) g.addEdge(0, i);
        targetMER = 7;
      } else if (orbitId === 45) {
        const edges = [[0,1],[1,2],[2,3],[3,4],[4,5],[2,6],[3,7]];
        edges.forEach(([u, v]) => g.addEdge(u, v));
        targetMER = 7;
      } else if (orbitId === 119) {
        const edges = [[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,0],[0,7],[3,7]];
        edges.forEach(([u, v]) => g.addEdge(u, v));
        targetMER = 8;
      } else if (orbitId === 146) {
        const edges = [
          [0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,7],[7,0],
          [0,4],[1,5],[2,6],[3,7]
        ];
        edges.forEach(([u, v]) => g.addEdge(u, v));
        targetMER = 9;
      }
      scrambleGraph(g, 24, rng);
      return { graph: g, groundTruth: targetMER, family: "Cabello Orbit" };
    }
  },
  "report_hardware/grid_2d": {
    name: "Scrambled 2D MBQC Grid",
    generate: (L, p, rng) => {
      const n = L * L;
      const g = new Graph(n);
      for (let r = 0; r < L; r++) {
        for (let c = 0; c < L; c++) {
          const v = r * L + c;
          if (c + 1 < L) g.addEdge(v, v + 1);
          if (r + 1 < L) g.addEdge(v, v + L);
        }
      }
      scrambleGraph(g, 3 * n, rng);
      return { graph: g, groundTruth: null, family: "Grid MBQC" };
    }
  },
  "report_hardware/heavy_hex": {
    name: "Scrambled Heavy-Hex Hardware Lattice",
    generate: (n, p, rng) => {
      const g = new Graph(n);
      for (let i = 0; i < n - 1; i++) g.addEdge(i, i + 1);
      const step = Math.floor(n / 6);
      for (let i = 0; i < n - step; i += step) {
        if (!g.hasEdge(i, i + step)) g.addEdge(i, i + step);
      }
      scrambleGraph(g, 3 * n, rng);
      return { graph: g, groundTruth: null, family: "Heavy-Hex" };
    }
  },
  "report_hardware/modular_qpu": {
    name: "Scrambled Modular QPU",
    generate: (n, numModules, rng) => {
      const g = new Graph(n);
      const modules = numModules || 3;
      const modSize = Math.floor(n / modules);
      for (let m = 0; m < modules; m++) {
        const start = m * modSize;
        const end = (m === modules - 1) ? n : start + modSize;
        for (let i = start; i < end; i++) {
          for (let j = i + 1; j < end; j++) {
            if (rng() < 0.75) g.addEdge(i, j);
          }
        }
      }
      for (let m = 0; m < modules; m++) {
        const u = m * modSize + randInt(rng, 0, modSize);
        const nextMod = (m + 1) % modules;
        const v = nextMod * modSize + randInt(rng, 0, modSize);
        g.addEdge(u, v);
      }
      ensureConnected(g, rng);
      scrambleGraph(g, 3 * n, rng);
      return { graph: g, groundTruth: null, family: "Modular QPU" };
    }
  },
  "report_complex/erdos_renyi": {
    name: "Erdős–Rényi G(n, p)",
    generate: (n, p, rng) => {
      const g = new Graph(n);
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          if (rng() < p) g.addEdge(i, j);
        }
      }
      ensureConnected(g, rng);
      return { graph: g, groundTruth: null, family: "Erdős–Rényi" };
    }
  },
  "report_complex/scale_free": {
    name: "Barabási–Albert Scale-Free",
    generate: (n, mAttach, rng) => {
      const m = Math.max(2, Math.floor(mAttach || 2));
      const g = new Graph(n);
      for (let i = 0; i <= m; i++) {
        for (let j = i + 1; j <= m; j++) g.addEdge(i, j);
      }
      for (let i = m + 1; i < n; i++) {
        const targets = new Set();
        let totalDeg = 0;
        for (let node = 0; node < i; node++) totalDeg += g.degree(node);
        while (targets.size < m) {
          let r = rng() * totalDeg, acc = 0;
          for (let node = 0; node < i; node++) {
            acc += g.degree(node);
            if (acc >= r) { targets.add(node); break; }
          }
        }
        targets.forEach(t => g.addEdge(i, t));
      }
      return { graph: g, groundTruth: null, family: "Scale-Free" };
    }
  },
  "report_complex/small_world": {
    name: "Watts–Strogatz Small-World",
    generate: (n, beta, rng) => {
      const k = 4;
      const g = new Graph(n);
      for (let i = 0; i < n; i++) {
        for (let j = 1; j <= k / 2; j++) g.addEdge(i, (i + j) % n);
      }
      for (let i = 0; i < n; i++) {
        for (let j = 1; j <= k / 2; j++) {
          if (rng() < beta) {
            const target = (i + j) % n;
            g.adj[i][target] = 0; g.adj[target][i] = 0;
            const newTarget = randInt(rng, 0, n);
            if (newTarget !== i) g.addEdge(i, newTarget);
          }
        }
      }
      ensureConnected(g, rng);
      return { graph: g, groundTruth: null, family: "Small-World" };
    }
  }
};

export const SUITE_REGISTRY = {
  final_report_75: {
    name: "★ Final Report Suite (Complete 75 Curated Instances)",
    build: (baseSeed) => {
      const list = [];
      const gen = GRAPH_GENERATORS;

      // 1. Planted Scrambled Trees (16 instances: 4x16, 4x32, 4x48, 4x64)
      [16, 32, 48, 64].forEach(n => {
        for (let i = 1; i <= 4; i++) {
          const rng = mulberry32(baseSeed + n * 1000 + i * 17);
          const inst = gen["report_tree/planted_scrambled"].generate(n, 0, rng);
          list.push({ name: `Tree-${n}-0${i}`, ...inst });
        }
      });

      // 2. Complete Bipartite Asymmetry Sweep (5 instances, n=30)
      const splits = [
        { name: "Bipart-Sym-15", a: 15 },
        { name: "Bipart-Asym-10", a: 10 },
        { name: "Bipart-Asym-05", a: 5 },
        { name: "Bipart-Asym-03", a: 3 },
        { name: "Bipart-Asym-02", a: 2 }
      ];
      splits.forEach((s, idx) => {
        const rng = mulberry32(baseSeed + 2000 + idx);
        const inst = gen["report_bipartite/complete_asymmetric"].generate(30, s.a, rng);
        list.push({ name: s.name, ...inst });
      });

      // 3. Defective Bipartite Suite (5 instances, n=12)
      const defects = [
        { name: "Defect-6-6-M1", a: 6, m: 1 },
        { name: "Defect-6-6-M4", a: 6, m: 4 },
        { name: "Defect-4-8-M1", a: 4, m: 1 },
        { name: "Defect-4-8-M3", a: 4, m: 3 },
        { name: "Defect-3-9-M1", a: 3, m: 1 }
      ];
      defects.forEach((d, idx) => {
        const rng = mulberry32(baseSeed + 3000 + idx);
        const inst = gen["report_bipartite/defective"].generate(12, d, rng);
        list.push({ name: d.name, ...inst });
      });

      // 4. Cabello Canonical Orbits (4 instances, n=8)
      [1, 45, 119, 146].forEach(orbId => {
        const rng = mulberry32(baseSeed + 4000 + orbId);
        const inst = gen["report_canonical/cabello_orbit"].generate(8, orbId, rng);
        list.push({ name: `Cabello-Orb-${orbId}`, ...inst });
      });

      // 5. Scrambled 2D MBQC Grids (8 instances)
      [4, 5, 6, 7].forEach(L => {
        for (let i = 1; i <= 2; i++) {
          const rng = mulberry32(baseSeed + 5000 + L * 100 + i);
          const inst = gen["report_hardware/grid_2d"].generate(L, 0, rng);
          list.push({ name: `Grid-${L}x${L}-0${i}`, ...inst });
        }
      });

      // 6. Scrambled Heavy-Hex Lattices (6 instances)
      [27, 45].forEach(n => {
        for (let i = 1; i <= 3; i++) {
          const rng = mulberry32(baseSeed + 6000 + n * 10 + i);
          const inst = gen["report_hardware/heavy_hex"].generate(n, 0, rng);
          list.push({ name: `HeavyHex-${n}-0${i}`, ...inst });
        }
      });

      // 7. Scrambled Modular QPUs (6 instances)
      [{ n: 36, mods: 3 }, { n: 60, mods: 4 }].forEach(cfg => {
        for (let i = 1; i <= 3; i++) {
          const rng = mulberry32(baseSeed + 7000 + cfg.n * 10 + i);
          const inst = gen["report_hardware/modular_qpu"].generate(cfg.n, cfg.mods, rng);
          list.push({ name: `Modular-${cfg.n}-0${i}`, ...inst });
        }
      });

      // 8. Erdős–Rényi Density Sweep (15 instances)
      [{ tag: "Sparse", p: 0.12 }, { tag: "Medium", p: 0.35 }, { tag: "Dense", p: 0.75 }].forEach(cfg => {
        for (let i = 1; i <= 5; i++) {
          const rng = mulberry32(baseSeed + 8000 + Math.floor(cfg.p * 1000) + i);
          const inst = gen["report_complex/erdos_renyi"].generate(40, cfg.p, rng);
          list.push({ name: `ER-${cfg.tag}-0${i}`, ...inst });
        }
      });

      // 9. Barabási–Albert Scale-Free (5 instances)
      for (let i = 1; i <= 5; i++) {
        const rng = mulberry32(baseSeed + 9000 + i);
        const inst = gen["report_complex/scale_free"].generate(40, 2, rng);
        list.push({ name: `ScaleFree-BA-0${i}`, ...inst });
      }

      // 10. Watts–Strogatz Small-World (5 instances)
      for (let i = 1; i <= 5; i++) {
        const rng = mulberry32(baseSeed + 9500 + i);
        const inst = gen["report_complex/small_world"].generate(40, 0.10, rng);
        list.push({ name: `SmallWorld-WS-0${i}`, ...inst });
      }

      return list;
    }
  },

  quick_smoke: {
    name: "Quick Smoke Test (4 Instances)",
    build: (seed) => {
      const rng = mulberry32(seed);
      return [
        { name: "Tree-16 (Planted)", ...GRAPH_GENERATORS["report_tree/planted_scrambled"].generate(16, 0, rng) },
        { name: "Bipart-Sym-15", ...GRAPH_GENERATORS["report_bipartite/complete_asymmetric"].generate(30, 15, rng) },
        { name: "Grid-4x4 (MBQC)", ...GRAPH_GENERATORS["report_hardware/grid_2d"].generate(4, 0, rng) },
        { name: "ER-Medium (n=40)", ...GRAPH_GENERATORS["report_complex/erdos_renyi"].generate(40, 0.35, rng) }
      ];
    }
  },

  custom_instance: {
    name: "Custom Single Instance (Interactive)",
    build: (seed) => {
      const rng = mulberry32(seed);
      const genKey = document.getElementById("customGenSelect").value;
      const n = parseInt(document.getElementById("customN").value, 10);
      const param = parseFloat(document.getElementById("customParam").value);
      const inst = GRAPH_GENERATORS[genKey].generate(n, param, rng);
      return [{ name: `Custom-${GRAPH_GENERATORS[genKey].name}`, ...inst }];
    }
  }
};