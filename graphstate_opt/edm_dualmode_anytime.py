"""
DualMode-Anytime: High-performance anytime heuristic for MER.
Combines 2-tier downhill short-circuiting, candidate-pruned pivots,
a 4-slot FIFO ring tabu buffer, and dual-mode softmax plateau exploration.
"""

import numpy as np
import networkx as nx
from itertools import combinations
from typing import Tuple, List, Optional


def _toggle_neighborhood(graph: nx.Graph, vertex) -> nx.Graph:
    neighbors = list(graph.neighbors(vertex))
    for index, first in enumerate(neighbors):
        for second in neighbors[index + 1:]:
            if graph.has_edge(first, second):
                graph.remove_edge(first, second)
            else:
                graph.add_edge(first, second)
    return graph


def _pivot_inplace(graph: nx.Graph, u, v) -> nx.Graph:
    for vertex in (u, v, u):
        _toggle_neighborhood(graph, vertex)
    return graph


def _lc_edge_delta(graph: nx.Graph, vertex) -> int:
    neighbors = list(graph.neighbors(vertex))
    d = len(neighbors)
    if d < 2:
        return 0
    existing_edges = sum(graph.has_edge(u, v) for u, v in combinations(neighbors, 2))
    return d * (d - 1) // 2 - 2 * existing_edges


def _pivot_edge_delta(graph: nx.Graph, u, v) -> int:
    neighbors_u = set(graph.neighbors(u)) - {v}
    neighbors_v = set(graph.neighbors(v)) - {u}
    only_u = neighbors_u - neighbors_v
    only_v = neighbors_v - neighbors_u
    common = neighbors_u & neighbors_v
    groups = ((only_u, only_v), (only_u, common), (only_v, common))
    toggled_pairs = sum(len(left) * len(right) for left, right in groups)
    existing_toggled = sum(
        graph.has_edge(first, second)
        for left, right in groups
        for first in left
        for second in right
    )
    return toggled_pairs - 2 * existing_toggled


def edm_dualmode_anytime(
    in_graph: nx.Graph,
    budget: int = 20000,
    random_state: Optional[int] = None,
) -> Tuple[nx.Graph, List[int], List[Tuple]]:
    """
    Find Minimum Edge Representative (MER) using DualMode-Anytime.

    Parameters
    ----------
    in_graph : nx.Graph
        Input simple undirected graph.
    budget : int
        Maximum standardized evaluation budget.
    random_state : int, optional
        Seed for the random number generator.

    Returns
    -------
    best_graph : nx.Graph
        Lowest-edge representative graph state found.
    history : list of int
        Best edge count history.
    best_moves : list of tuple
        Sequence of ('lc', v) or ('pivot', u, v) moves applied.
    """
    if in_graph.is_directed() or in_graph.is_multigraph():
        raise TypeError("Graph must be simple and undirected.")

    rng = np.random.default_rng(random_state)
    graph = in_graph.copy()
    nodes = list(graph.nodes())
    node_to_idx = {node: i for i, node in enumerate(nodes)}
    n = len(nodes)

    cur_edges = graph.number_of_edges()
    best_edges = cur_edges
    best_graph = graph.copy()
    history = [best_edges]
    moves_applied = []

    # Adaptive cooling schedule
    est_step_cost = max(n, n + int(0.25 * cur_edges))
    est_iters = max(15, budget // est_step_cost)
    t0, t_min = 2.0, 0.005
    alpha = (t_min / t0) ** (1.0 / est_iters)
    temp = t0

    stagnant = 0
    tabu = [-1, -1, -1, -1]
    tabu_ptr = 0
    evals = 0

    while evals < budget:
        if cur_edges <= n - 1:  # Theoretical tree floor reached
            break

        temp = max(t_min, temp * alpha)

        # Dynamic reheat on plateau
        if stagnant >= 5:
            temp = min(2.5, temp * 2.2)
            stagnant = 1

        single_deltas = {}
        best_single = None
        min_single_delta = float('inf')
        second_single = None
        second_single_delta = float('inf')

        # --- Phase 1: Single LC Scan ---
        for node in nodes:
            deg = graph.degree(node)
            if deg < 2:
                single_deltas[node] = 999
                continue

            node_idx = node_to_idx[node]
            if stagnant < 2 and node_idx in tabu:
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

        # Short-Circuit 1: Immediate Downhill Descent
        if best_single and (best_single[2] <= -2 or (best_single[2] == -1 and stagnant == 0)):
            v = best_single[1]
            _toggle_neighborhood(graph, v)
            tabu[tabu_ptr % 4] = node_to_idx[v]
            tabu_ptr += 1
            cur_edges += best_single[2]
            moves_applied.append(('lc', v))
            if cur_edges < best_edges:
                best_edges = cur_edges
                best_graph = graph.copy()
                stagnant = 0
            history.append(best_edges)
            continue

        # --- Phase 2: Pruned Pivot Scan ---
        best_pivot = None
        min_pivot_delta = float('inf')
        second_pivot = None
        second_pivot_delta = float('inf')

        should_check_pivots = (min_single_delta >= 0) or (min_single_delta == -1 and stagnant >= 1) or (stagnant >= 2)

        if should_check_pivots and evals < budget:
            prune_cutoff = max(2, min_single_delta + 3) if min_single_delta <= 0 else (min_single_delta + 2)

            broken = False
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

                # Short-Circuit 2: Immediate early break on strong downhill pivot
                if d_p <= -2 and stagnant == 0:
                    broken = True
                    break

                if evals >= budget:
                    broken = True
                    break

        # --- Phase 3: Candidate Pool Selection ---
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

        if (pool[0][2] if pool[0][0] == 'lc' else pool[0][3]) < 0:
            chosen = pool[0]
        else:
            candidates = pool[:3]
            min_d = candidates[0][2] if candidates[0][0] == 'lc' else candidates[0][3]
            deltas = np.array([c[2] if c[0] == 'lc' else c[3] for c in candidates], dtype=float)
            weights = np.exp(-(deltas - min_d) / max(temp, 0.05))
            probs = weights / np.sum(weights)
            chosen = candidates[int(rng.choice(len(candidates), p=probs))]

        move_dE = chosen[2] if chosen[0] == 'lc' else chosen[3]

        # --- Phase 4: Annealing Acceptance ---
        if move_dE <= 0 or rng.random() < np.exp(-move_dE / max(temp, 1e-4)):
            if chosen[0] == 'lc':
                v = chosen[1]
                _toggle_neighborhood(graph, v)
                tabu[tabu_ptr % 4] = node_to_idx[v]
                tabu_ptr += 1
                moves_applied.append(('lc', v))
            else:
                u, v = chosen[1], chosen[2]
                _pivot_inplace(graph, u, v)
                tabu[tabu_ptr % 4] = node_to_idx[u]
                tabu[(tabu_ptr + 1) % 4] = node_to_idx[v]
                tabu_ptr += 2
                moves_applied.append(('pivot', u, v))

            cur_edges += move_dE
            if cur_edges < best_edges:
                best_edges = cur_edges
                best_graph = graph.copy()
                stagnant = 0
            else:
                stagnant += 1
        else:
            stagnant += 1

        history.append(best_edges)

    return best_graph, history, moves_applied