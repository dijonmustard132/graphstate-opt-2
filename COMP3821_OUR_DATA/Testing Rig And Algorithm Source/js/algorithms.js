import { randInt, fastHash } from './graph.js';

// 1. EDM-SA (Literature Baseline: Sharma et al. 2026)
export function alg_edm_sa(inGraph, budget, rng) {
  const graph = inGraph.clone();
  let y = graph.numEdges(), yBest = y;
  const initialTemp = 100.0;
  let temp = initialTemp;
  let transitionCutoff = 1;
  let evals = 0;
  const kMax = Math.max(50, Math.floor(budget / inGraph.n));

  for (let k = 0; k < kMax; k++) {
    evals += inGraph.n;
    const n = graph.n;
    const degs = new Float64Array(n), clust = new Float64Array(n);
    let sumM = 0;
    for (let v = 0; v < n; v++) {
      degs[v] = graph.degree(v); clust[v] = graph.clustering(v);
      sumM += degs[v] * clust[v];
    }
    const metric = new Float64Array(n);
    for (let v = 0; v < n; v++) metric[v] = sumM !== 0 ? (degs[v] * clust[v]) / sumM : 0;

    const uniqueSet = new Set();
    for (let v = 0; v < n; v++) uniqueSet.add(Math.round(metric[v] * 1e8) / 1e8);
    const uniqueElements = Array.from(uniqueSet).sort((a, b) => a - b);

    const cutoffArg = Math.ceil((transitionCutoff / kMax) * uniqueElements.length);
    const chosenArg = cutoffArg < uniqueElements.length ? randInt(rng, cutoffArg, uniqueElements.length) : uniqueElements.length - 1;
    const targetVal = uniqueElements[chosenArg];

    let vertices = [];
    for (let v = 0; v < n; v++) {
      if (metric[v] > 0 && Math.abs((Math.round(metric[v] * 1e8) / 1e8) - targetVal) < 1e-7) vertices.push(v);
    }
    if (vertices.length === 0) {
      let maxC = -1;
      for (let v = 0; v < n; v++) if (clust[v] > maxC) maxC = clust[v];
      for (let v = 0; v < n; v++) if (Math.abs(clust[v] - maxC) < 1e-7) vertices.push(v);
    }
    const xNew = vertices.length > 0 ? vertices[randInt(rng, 0, vertices.length)] : randInt(rng, 0, n);

    const dE = graph.deltaE(xNew);
    const yNew = y + dE;
    if (yNew - y <= 0 || rng() < Math.exp(-(yNew - y) / Math.max(temp, 1e-6))) {
      y = yNew;
      graph.localComplement(xNew);
    }
    if (y < yBest) yBest = y;
    temp = initialTemp * Math.LN2 / Math.log(k + 2);
    transitionCutoff = k + 1;
    if (evals >= budget) break;
  }
  return { bestEdges: yBest, evals };
}

// 2. Exact-Geom-SA (Ablation Baseline: No pivots)
export function alg_exact_geom(inGraph, budget, rng) {
  const g = inGraph.clone();
  let cur = g.numEdges(), best = cur, evals = 0;
  let T = 2.0, alpha = 0.999;
  while (evals < budget) {
    T = Math.max(0.001, T * alpha);
    const moves = [];
    for (let v = 0; v < g.n; v++) {
      if (g.degree(v) < 2) continue;
      evals++;
      moves.push({ v, dE: g.deltaE(v) });
      if (evals >= budget) break;
    }
    if (moves.length === 0) break;
    const minD = Math.min(...moves.map(m => m.dE));
    const weights = moves.map(m => Math.exp(-(m.dE - minD) / Math.max(T, 0.01)));
    const totalW = weights.reduce((a, b) => a + b, 0);
    let r = rng() * totalW, chosen = moves[moves.length - 1];
    for (let i = 0; i < moves.length; i++) {
      r -= weights[i];
      if (r <= 0) { chosen = moves[i]; break; }
    }
    if (chosen.dE <= 0 || rng() < Math.exp(-chosen.dE / Math.max(T, 1e-4))) {
      g.localComplement(chosen.v);
      cur += chosen.dE;
      if (cur < best) best = cur;
    }
  }
  return { bestEdges: best, evals };
}

// 3. Pivot-SA (Ablation Baseline: Full unpruned pivots)
export function alg_pivot(inGraph, budget, rng) {
  const g = inGraph.clone();
  let cur = g.numEdges(), best = cur, evals = 0;
  let T = 2.0, alpha = 0.998;
  while (evals < budget) {
    T = Math.max(0.001, T * alpha);
    const candidates = [];
    for (let v = 0; v < g.n; v++) {
      if (g.degree(v) >= 2) {
        evals++;
        candidates.push({ type: 'lc', u: v, dE: g.deltaE(v) });
      }
    }
    for (let u = 0; u < g.n; u++) {
      for (let v = u + 1; v < g.n; v++) {
        if (g.hasEdge(u, v) && g.degree(u) >= 2 && g.degree(v) >= 2) {
          evals += 3;
          candidates.push({ type: 'pivot', u, v, dE: g.pivotDelta(u, v) });
          if (evals >= budget) break;
        }
      }
      if (evals >= budget) break;
    }
    if (candidates.length === 0) break;
    candidates.sort((a, b) => a.dE - b.dE);
    const chosen = candidates[0];
    if (chosen.dE <= 0 || rng() < Math.exp(-chosen.dE / Math.max(T, 1e-4))) {
      if (chosen.type === 'lc') g.localComplement(chosen.u);
      else g.pivot(chosen.u, chosen.v);
      cur += chosen.dE;
      if (cur < best) best = cur;
    }
  }
  return { bestEdges: best, evals };
}

// 4. DualMode-Anytime / Apex Ultra (Flagship Anytime Heuristic)
export function alg_custom_5_2(inGraph, budget, rng) {
  const g = inGraph.clone();
  let cur = g.numEdges(), best = cur, evals = 0;

  const estStepCost = Math.max(g.n, g.n + Math.floor(0.25 * cur));
  const estIters = Math.max(15, Math.floor(budget / estStepCost));
  const T0 = 2.0, Tmin = 0.005;
  const alpha = Math.pow(Tmin / T0, 1.0 / estIters);
  let T = T0;

  let stagnant = 0;
  const tabu = [-1, -1, -1, -1];
  let tabuPtr = 0;
  const singleDeltas = new Int32Array(g.n);

  while (evals < budget) {
    if (cur <= g.n - 1) break;
    T = Math.max(Tmin, T * alpha);

    if (stagnant >= 5) {
      T = Math.min(2.5, T * 2.2);
      stagnant = 1;
    }

    let bestSingle = null, minSingleDelta = Infinity;
    let secondSingle = null, secondSingleDelta = Infinity;

    for (let v = 0; v < g.n; v++) {
      if (g.degree(v) < 2) { singleDeltas[v] = 999; continue; }
      if (stagnant < 2 && (v === tabu[0] || v === tabu[1] || v === tabu[2] || v === tabu[3])) {
        singleDeltas[v] = 999; continue;
      }
      evals++;
      const dE = g.deltaE(v);
      singleDeltas[v] = dE;

      if (dE < minSingleDelta) {
        secondSingle = bestSingle;
        secondSingleDelta = minSingleDelta;
        minSingleDelta = dE;
        bestSingle = { type: 'lc', u: v, dE };
      } else if (dE < secondSingleDelta) {
        secondSingleDelta = dE;
        secondSingle = { type: 'lc', u: v, dE };
      }
      if (evals >= budget) break;
    }

    // Short-Circuit 1: Immediate Downhill Descent
    if (bestSingle && (bestSingle.dE <= -2 || (bestSingle.dE === -1 && stagnant === 0))) {
      g.localComplement(bestSingle.u);
      tabu[tabuPtr % 4] = bestSingle.u; tabuPtr++;
      cur += bestSingle.dE;
      if (cur < best) { best = cur; stagnant = 0; }
      continue;
    }

    let bestPivot = null, minPivotDelta = Infinity;
    let secondPivot = null, secondPivotDelta = Infinity;
    const shouldCheckPivots = (minSingleDelta >= 0) || (minSingleDelta === -1 && stagnant >= 1) || (stagnant >= 2);

    if (shouldCheckPivots && evals < budget) {
      const pruneCutoff = minSingleDelta <= 0 ? Math.max(2, minSingleDelta + 3) : (minSingleDelta + 2);

      pivotLoop:
      for (let u = 0; u < g.n; u++) {
        if (g.degree(u) < 2) continue;
        for (let v = u + 1; v < g.n; v++) {
          if (g.hasEdge(u, v) && g.degree(v) >= 2) {
            if (stagnant < 2 && singleDeltas[u] > pruneCutoff && singleDeltas[v] > pruneCutoff) continue;

            evals += 3;
            const d = g.pivotDelta(u, v);

            if (d < minPivotDelta) {
              secondPivot = bestPivot;
              secondPivotDelta = minPivotDelta;
              minPivotDelta = d;
              bestPivot = { type: 'pivot', u, v, dE: d };
            } else if (d < secondPivotDelta) {
              secondPivotDelta = d;
              secondPivot = { type: 'pivot', u, v, dE: d };
            }

            // Short-Circuit 2: Immediate early break on strong downhill pivot
            if (d <= -2 && stagnant === 0) break pivotLoop;
            if (evals >= budget) break pivotLoop;
          }
        }
      }
    }

    const pool = [];
    if (bestSingle) pool.push(bestSingle);
    if (bestPivot) pool.push(bestPivot);
    if (secondSingle && secondSingle.dE <= minSingleDelta + 1) pool.push(secondSingle);
    if (secondPivot && secondPivot.dE <= minPivotDelta + 1) pool.push(secondPivot);

    if (pool.length === 0) break;
    pool.sort((a, b) => a.dE - b.dE);

    let chosen;
    if (pool[0].dE < 0) {
      chosen = pool[0];
    } else {
      const candidates = pool.slice(0, 3);
      const minD = candidates[0].dE;
      const weights = candidates.map(m => Math.exp(-(m.dE - minD) / Math.max(T, 0.05)));
      const sumW = weights.reduce((a, b) => a + b, 0);
      let r = rng() * sumW;
      chosen = candidates[0];
      for (let i = 0; i < candidates.length; i++) {
        r -= weights[i];
        if (r <= 0) { chosen = candidates[i]; break; }
      }
    }

    if (chosen.dE <= 0 || rng() < Math.exp(-chosen.dE / Math.max(T, 1e-4))) {
      if (chosen.type === 'lc') {
        g.localComplement(chosen.u);
        tabu[tabuPtr % 4] = chosen.u; tabuPtr++;
      } else {
        g.pivot(chosen.u, chosen.v);
        tabu[tabuPtr % 4] = chosen.u;
        tabu[(tabuPtr + 1) % 4] = chosen.v;
        tabuPtr += 2;
      }
      cur += chosen.dE;
      if (cur < best) { best = cur; stagnant = 0; }
      else { stagnant++; }
    } else {
      stagnant++;
    }
  }

  return { bestEdges: best, evals };
}

// 5. DualMode-Deep / Apex Deep (High-Budget Offline Specialist)
export function alg_custom_deep(inGraph, budget, rng) {
  let g = inGraph.clone();
  let cur = g.numEdges(), best = cur, evals = 0;
  let bestGraph = g.clone();

  let T = 2.5;
  const alpha = 0.9992;
  let stagnant = 0;

  const stateTabu = new Int32Array(64);
  let tabuIdx = 0;
  stateTabu[0] = fastHash(g);
  tabuIdx = 1;

  const singleDeltas = new Int32Array(g.n);

  while (evals < budget) {
    if (cur <= g.n - 1) break;
    T = Math.max(0.002, T * alpha);

    let bestSingle = null, minSingleDelta = Infinity;
    let secondSingle = null, secondSingleDelta = Infinity;

    for (let v = 0; v < g.n; v++) {
      if (g.degree(v) < 2) { singleDeltas[v] = 999; continue; }
      evals++;
      const dE = g.deltaE(v);
      singleDeltas[v] = dE;

      if (dE < minSingleDelta) {
        secondSingle = bestSingle;
        secondSingleDelta = minSingleDelta;
        minSingleDelta = dE;
        bestSingle = { type: 'lc', u: v, dE };
      } else if (dE < secondSingleDelta) {
        secondSingleDelta = dE;
        secondSingle = { type: 'lc', u: v, dE };
      }
      if (evals >= budget) break;
    }

    let bestPivot = null, minPivotDelta = Infinity;
    let secondPivot = null, secondPivotDelta = Infinity;

    if (evals < budget) {
      const pruneCutoff = minSingleDelta <= 0 ? Math.max(3, minSingleDelta + 4) : (minSingleDelta + 3);

      for (let u = 0; u < g.n; u++) {
        if (g.degree(u) < 2) continue;
        for (let v = u + 1; v < g.n; v++) {
          if (g.hasEdge(u, v) && g.degree(v) >= 2) {
            if (stagnant < 2 && singleDeltas[u] > pruneCutoff && singleDeltas[v] > pruneCutoff) continue;

            evals += 3;
            const d = g.pivotDelta(u, v);

            if (d < minPivotDelta) {
              secondPivot = bestPivot;
              secondPivotDelta = minPivotDelta;
              minPivotDelta = d;
              bestPivot = { type: 'pivot', u, v, dE: d };
            } else if (d < secondPivotDelta) {
              secondPivotDelta = d;
              secondPivot = { type: 'pivot', u, v, dE: d };
            }
            if (evals >= budget) break;
          }
        }
        if (evals >= budget) break;
      }
    }

    // 2-Step Compound Lookahead Tunneling
    let tunnelFound = false;
    if (minSingleDelta >= 0 && minPivotDelta >= 0 && stagnant >= 2 && evals < budget) {
      const tunnelU = bestSingle ? bestSingle.u : -1;
      if (tunnelU !== -1 && singleDeltas[tunnelU] <= 4) {
        g.localComplement(tunnelU);
        const nb = g.neighbors(tunnelU);
        let bestStep2 = -1, minStep2 = Infinity;

        for (let i = 0; i < nb.length; i++) {
          const w = nb[i];
          if (g.degree(w) >= 2) {
            evals++;
            const d2 = g.deltaE(w);
            if (d2 < minStep2) { minStep2 = d2; bestStep2 = w; }
            if (evals >= budget) break;
          }
        }
        g.localComplement(tunnelU);

        if (bestStep2 !== -1 && (singleDeltas[tunnelU] + minStep2) < 0) {
          g.localComplement(tunnelU);
          g.localComplement(bestStep2);
          cur += (singleDeltas[tunnelU] + minStep2);
          stateTabu[tabuIdx % 64] = fastHash(g);
          tabuIdx++;
          if (cur < best) { best = cur; bestGraph = g.clone(); stagnant = 0; }
          tunnelFound = true;
        }
      }
    }
    if (tunnelFound) continue;

    // Basin-Hopping Macro Kick
    if (stagnant >= 8 && evals < budget) {
      g = bestGraph.clone();
      cur = best;
      for (let kick = 0; kick < 3; kick++) {
        const kickV = randInt(rng, 0, g.n);
        if (g.degree(kickV) >= 2) {
          evals++;
          cur += g.deltaE(kickV);
          g.localComplement(kickV);
        }
      }
      T = Math.min(2.5, T * 2.5);
      stagnant = 0;
      continue;
    }

    const pool = [];
    if (bestSingle) pool.push(bestSingle);
    if (bestPivot) pool.push(bestPivot);
    if (secondSingle && secondSingle.dE <= minSingleDelta + 1) pool.push(secondSingle);
    if (secondPivot && secondPivot.dE <= minPivotDelta + 1) pool.push(secondPivot);

    if (pool.length === 0) break;
    pool.sort((a, b) => a.dE - b.dE);

    let chosen = pool[0];
    if (chosen.dE >= 0) {
      const candidates = pool.slice(0, 3);
      const minD = candidates[0].dE;
      const weights = candidates.map(m => Math.exp(-(m.dE - minD) / Math.max(T, 0.05)));
      const sumW = weights.reduce((a, b) => a + b, 0);
      let r = rng() * sumW;
      for (let i = 0; i < candidates.length; i++) {
        r -= weights[i];
        if (r <= 0) { chosen = candidates[i]; break; }
      }
    }

    if (chosen.type === 'lc') g.localComplement(chosen.u);
    else g.pivot(chosen.u, chosen.v);

    const nextHash = fastHash(g);
    let isCyclic = false;
    for (let i = 0; i < 64; i++) {
      if (stateTabu[i] === nextHash) { isCyclic = true; break; }
    }

    if (isCyclic && (cur + chosen.dE >= best) && stagnant < 4) {
      if (chosen.type === 'lc') g.localComplement(chosen.u);
      else g.pivot(chosen.u, chosen.v);
      stagnant++;
      continue;
    }

    if (chosen.dE <= 0 || rng() < Math.exp(-chosen.dE / Math.max(T, 1e-4))) {
      cur += chosen.dE;
      stateTabu[tabuIdx % 64] = nextHash;
      tabuIdx++;
      if (cur < best) { best = cur; bestGraph = g.clone(); stagnant = 0; }
      else { stagnant++; }
    } else {
      if (chosen.type === 'lc') g.localComplement(chosen.u);
      else g.pivot(chosen.u, chosen.v);
      stagnant++;
    }
  }

  return { bestEdges: best, evals };
}

export const ALL_ALGOS = [
  { id: "custom5_2", name: "DualMode-Anytime", fn: alg_custom_5_2, defaultChecked: true },
  { id: "custom_deep", name: "DualMode-Deep", fn: alg_custom_deep, defaultChecked: true },
  { id: "edm_sa", name: "EDM-SA (Sharma et al. Baseline)", fn: alg_edm_sa, defaultChecked: true },
  { id: "exact_geom", name: "Exact-Geom-SA (No Pivots)", fn: alg_exact_geom, defaultChecked: false },
  { id: "pivot", name: "Pivot-SA (Unpruned)", fn: alg_pivot, defaultChecked: false },
];