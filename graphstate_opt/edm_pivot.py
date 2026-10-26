"""Pivot-based simulated annealing for edge minimisation."""

import numpy as np
import networkx as nx
from itertools import combinations


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
    existing_edges = sum(graph.has_edge(u, v) for u, v in combinations(neighbors, 2))
    return len(neighbors) * (len(neighbors) - 1) // 2 - 2 * existing_edges


def _pivot_edge_delta(graph: nx.Graph, u, v) -> int:
    neighbors_u = set(graph.neighbors(u)) - {v}
    neighbors_v = set(graph.neighbors(v)) - {u}
    only_u = neighbors_u - neighbors_v
    only_v = neighbors_v - neighbors_u
    common = neighbors_u & neighbors_v
    groups = ((only_u, only_v), (only_u, common), (only_v, common))
    toggled_pairs = sum(len(left) * len(right) for left, right in groups)
    existing_toggled_edges = sum(
        graph.has_edge(first, second)
        for left, right in groups
        for first in left
        for second in right
    )
    return toggled_pairs - 2 * existing_toggled_edges


def pivot_graph(graph: nx.Graph, u, v) -> nx.Graph:
    """Return the graph obtained by pivoting on edge ``(u, v)``.

    A pivot is the composition of local complementations at ``u``, ``v``,
    and ``u``. The input graph is not modified.
    """
    if graph.is_directed() or graph.is_multigraph():
        raise TypeError("Pivoting requires a simple, undirected graph")
    if u == v or not graph.has_edge(u, v):
        raise ValueError("Pivoting requires an existing edge between distinct nodes")

    return _pivot_inplace(graph.copy(), u, v)


def _edm_sa(
    in_graph: nx.Graph,
    k_max: int,
    initial_temp: float,
    random_state=None,
    pivot_probability: float = 1.0,
):
    if in_graph.is_directed() or in_graph.is_multigraph():
        raise TypeError("Pivoting requires a simple, undirected graph")
    if k_max < 0:
        raise ValueError("k_max must be non-negative")
    if initial_temp <= 0:
        raise ValueError("initial_temp must be positive")
    if not 0.0 <= pivot_probability <= 1.0:
        raise ValueError("pivot_probability must be between 0 and 1")

    rng = np.random.default_rng(random_state)
    graph = in_graph.copy()
    current_edges = graph.number_of_edges()
    best_graph = graph.copy()
    best_edges = current_edges
    current_moves = []
    best_moves = []
    best_edge_history = [best_edges]
    nodes = list(graph.nodes())

    for iteration in range(k_max):
        if not nodes or graph.number_of_edges() == 0:
            break

        vertex = nodes[int(rng.integers(len(nodes)))]
        neighbors = list(graph.neighbors(vertex))
        while not neighbors and graph.number_of_edges() > 0:
            vertex = nodes[int(rng.integers(len(nodes)))]
            neighbors = list(graph.neighbors(vertex))

        use_pivot = rng.random() < pivot_probability
        if not use_pivot and len(neighbors) < 2:
            if pivot_probability > 0 and neighbors:
                use_pivot = True
            else:
                best_edge_history.append(best_edges)
                continue

        if use_pivot:
            edge = (vertex, neighbors[int(rng.integers(len(neighbors)))])
            energy_change = _pivot_edge_delta(graph, *edge)
            move = ("pivot", *edge)
        else:
            energy_change = _lc_edge_delta(graph, vertex)
            move = ("lc", vertex)

        temperature = initial_temp * np.log(2) / np.log(iteration + 2)
        if energy_change <= 0 or rng.random() < np.exp(-energy_change / temperature):
            if use_pivot:
                _pivot_inplace(graph, *edge)
            else:
                _toggle_neighborhood(graph, vertex)
            current_edges += energy_change
            current_moves.append(move)

            if current_edges < best_edges:
                best_graph = graph.copy()
                best_edges = current_edges
                best_moves = current_moves.copy()

        best_edge_history.append(best_edges)

    return best_graph, best_edge_history, best_moves


def edm_pivot_sa(
    in_graph: nx.Graph,
    k_max: int,
    initial_temp: float,
    random_state=None,
):
    """Approximate a minimum-edge representative using pivot moves only.

    Each iteration chooses an existing edge uniformly and proposes a pivot on
    it. A simulated-annealing acceptance rule allows occasional uphill moves.

    Returns
    -------
    best_graph : nx.Graph
        Lowest-edge graph encountered.
    best_edge_history : list[int]
        Best edge count after each completed iteration, including the initial
        graph's edge count.
    best_pivots : list[tuple]
        Pivot edges that transform the input graph into ``best_graph``.
    """
    best_graph, history, moves = _edm_sa(
        in_graph, k_max, initial_temp, random_state
    )
    return best_graph, history, [(u, v) for _, u, v in moves]


def edm_lc_pivot_sa(
    in_graph: nx.Graph,
    k_max: int,
    initial_temp: float,
    random_state=None,
    pivot_probability: float = 0.5,
):
    """Anneal over both local-complementation and pivot moves.

    Returns the best graph, best edge-count history, and the move sequence
    (``("lc", vertex)`` or ``("pivot", u, v)``) that produced it.
    """
    return _edm_sa(
        in_graph, k_max, initial_temp, random_state, pivot_probability
    )