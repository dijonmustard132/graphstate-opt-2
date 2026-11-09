"""
DualMode-Deep: High-budget exhaustive optimizer for MER.
Employs steepest-descent ranking, 2-step compound tunneling, 64-state hash
tabu memory, and iterated local search (basin-hopping kicks) for deep plateaus.
"""

import numpy as np
import networkx as nx
from itertools import combinations
from typing import Tuple, List, Optional
from graphstate_opt.edm_dualmode_anytime import (
    _toggle_neighborhood,
    _pivot_inplace,
    _lc_edge_delta,
    _pivot_edge_delta,
)


def _fast_graph_hash(graph: nx.Graph, n: int, nodes: list) -> int:
    """32-bit FNV-1a hash over graph adjacency structure."""
    h = 0x811C9DC5
    for i in range(n):
        u = nodes[i]
        chunk = 0
        for j in range(n):
            v = nodes[j]
            bit = 1 if graph.has_edge(u, v) else 0
            chunk = (chunk << 1) | bit
            if (j & 31) == 31 or j == n - 1:
                h = ((h ^ chunk) * 0x01000193) & 0xFFFFFFFF
                chunk = 0
    return h


def edm_dualmode_deep(
    in_graph: nx.Graph,
    budget: int = 100000,
    random_state: Optional[int] = None,
) -> Tuple[nx.Graph, List[int], List[Tuple]]:
    """
    Find MER using DualMode-Deep for high-budget offline synthesis (B >= 20,000).
    """
    if in_graph.is_directed() or in_graph.is_multigraph():
        raise TypeError("Graph must be simple and undirected.")

    rng = np.random.default_rng(random_state)
    graph = in_graph.copy()
    nodes = list(graph.nodes())
    n = len(nodes)

    cur_edges = graph.number_of_edges()
    best_edges = cur_edges
    best_graph = graph.copy()
    history = [best_edges]
    moves_applied = []

    temp = 2.5
    alpha = 0.9992
    stagnant = 0

    state_tabu = np.zeros(64, dtype=np.int64)
    state_tabu[0] = _fast_graph_hash(graph, n, nodes)
    tabu_idx = 1
    evals = 0

    while evals < budget:
        if cur_edges <= n - 1:
            break

        temp = max(0.002, temp * alpha)

        # --- Phase 1: Exhaustive Steepest Descent ---
        single_deltas = {}
        best_single = None
        min_single_delta = float('inf')
        second_single = None
        second_single_delta = float('inf')

        for node in nodes:
            if graph.degree(node) < 2:
                single_deltas[node] = 999
                continue

            evals += 1
            d_e = _lc_edge_delta(graph, node)
            single_deltas[node] = d_e

            if d_e < min_single_delta:
                second_single = best_single
                second_single_delta = min_single_delta
                min_single_delta = d_e
                best_single = ('lc', node, d_e)
            elif d_e < second_single_delta:
                second_single_delta = d_e
                second_single = ('lc', node, d_e)

            if evals >= budget:
                break

        best_pivot = None
        min_pivot_delta = float('inf')
        second_pivot = None
        second_pivot_delta = float('inf')

        if evals < budget:
            prune_cutoff = max(3, min_single_delta + 4) if min_single_delta <= 0 else (min_single_delta + 3)

            for u, v in graph.edges():
                if graph.degree(u) < 2 or graph.degree(v) < 2:
                    continue
                if stagnant < 2 and single_deltas.get(u, 999) > prune_cutoff and single_deltas.get(v, 999) > prune_cutoff:
                    continue

                evals += 3
                d_p = _pivot_edge_delta(graph, u, v)

                if d_p < min_pivot_delta:
                    second_pivot = best_pivot
                    second_pivot_delta = min_pivot_delta
                    min_pivot_delta = d_p
                    best_pivot = ('pivot', u, v, d_p)
                elif d_p < second_pivot_delta:
                    second_pivot_delta = d_p
                    second_pivot = ('pivot', u, v, d_p)

                if evals >= budget:
                    break

        # --- Phase 2: 2-Step Compound Tunneling ---
        tunnel_found = False
        if min_single_delta >= 0 and min_pivot_delta >= 0 and stagnant >= 2 and evals < budget:
            tunnel_u = best_single[1] if best_single else None
            if tunnel_u is not None and single_deltas.get(tunnel_u, 999) <= 4:
                _toggle_neighborhood(graph, tunnel_u)
                nb = list(graph.neighbors(tunnel_u))
                best_step2 = None
                min_step2 = float('inf')

                for w in nb:
                    if graph.degree(w) >= 2:
                        evals += 1
                        d2 = _lc_edge_delta(graph, w)
                        if d2 < min_step2:
                            min_step2 = d2
                            best_step2 = w
                        if evals >= budget:
                            break

                _toggle_neighborhood(graph, tunnel_u)  # Revert test

                if best_step2 is not None and (single_deltas[tunnel_u] + min_step2) < 0:
                    _toggle_neighborhood(graph, tunnel_u)
                    _toggle_neighborhood(graph, best_step2)
                    cur_edges += single_deltas[tunnel_u] + min_step2
                    moves_applied.extend([('lc', tunnel_u), ('lc', best_step2)])

                    state_tabu[tabu_idx % 64] = _fast_graph_hash(graph, n, nodes)
                    tabu_idx += 1
                    if cur_edges < best_edges:
                        best_edges = cur_edges
                        best_graph = graph.copy()
                        stagnant = 0
                    history.append(best_edges)
                    tunnel_found = True

        if tunnel_found:
            continue

        # --- Phase 3: Basin-Hopping Macro Kick ---
        if stagnant >= 8 and evals < budget:
            graph = best_graph.copy()
            cur_edges = best_edges
            for _ in range(3):
                kick_v = nodes[int(rng.integers(n))]
                if graph.degree(kick_v) >= 2:
                    evals += 1
                    d_k = _lc_edge_delta(graph, kick_v)
                    _toggle_neighborhood(graph, kick_v)
                    cur_edges += d_k
                    moves_applied.append(('lc', kick_v))
            temp = min(2.5, temp * 2.5)
            stagnant = 0
            continue

        # --- Phase 4: State-Tabu Metropolis Selection ---
        pool = []
        if best_single:
            pool.append(best_single)
        if best_pivot:
            pool.append(best_pivot)
        if second_single and second_single[2] <= min_single_delta + 1:
            pool.append(second_single)
        if second_pivot and second_pivot[3] <= min_pivot_delta + 1:
            pool.append(second_pivot)

        if not pool:
            break

        pool.sort(key=lambda m: m[2] if m[0] == 'lc' else m[3])
        chosen = pool[0]

        if (chosen[2] if chosen[0] == 'lc' else chosen[3]) >= 0:
            candidates = pool[:3]
            min_d = candidates[0][2] if candidates[0][0] == 'lc' else candidates[0][3]
            deltas = np.array([c[2] if c[0] == 'lc' else c[3] for c in candidates], dtype=float)
            weights = np.exp(-(deltas - min_d) / max(temp, 0.05))
            probs = weights / np.sum(weights)
            chosen = candidates[int(rng.choice(len(candidates), p=probs))]

        # Speculatively apply move to test state tabu
        if chosen[0] == 'lc':
            _toggle_neighborhood(graph, chosen[1])
        else:
            _pivot_inplace(graph, chosen[1], chosen[2])

        next_hash = _fast_graph_hash(graph, n, nodes)
        is_cyclic = np.any(state_tabu == next_hash)
        move_dE = chosen[2] if chosen[0] == 'lc' else chosen[3]

        if is_cyclic and (cur_edges + move_dE >= best_edges) and stagnant < 4:
            # Revert move
            if chosen[0] == 'lc':
                _toggle_neighborhood(graph, chosen[1])
            else:
                _pivot_inplace(graph, chosen[1], chosen[2])
            stagnant += 1
            continue

        if move_dE <= 0 or rng.random() < np.exp(-move_dE / max(temp, 1e-4)):
            cur_edges += move_dE
            state_tabu[tabu_idx % 64] = next_hash
            tabu_idx += 1
            if chosen[0] == 'lc':
                moves_applied.append(('lc', chosen[1]))
            else:
                moves_applied.append(('pivot', chosen[1], chosen[2]))

            if cur_edges < best_edges:
                best_edges = cur_edges
                best_graph = graph.copy()
                stagnant = 0
            else:
                stagnant += 1
        else:
            # Revert rejected move
            if chosen[0] == 'lc':
                _toggle_neighborhood(graph, chosen[1])
            else:
                _pivot_inplace(graph, chosen[1], chosen[2])
            stagnant += 1

        history.append(best_edges)

    return best_graph, history, moves_applied