import networkx as nx

from graphstate_opt.edm_pivot import edm_lc_pivot_sa, edm_pivot_sa, pivot_graph


def test_pivot_is_involutive_and_does_not_mutate_input():
    graph = nx.Graph()
    graph.add_edges_from([("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])
    original_edges = set(graph.edges())

    pivoted = pivot_graph(graph, "a", "b")
    restored = pivot_graph(pivoted, "a", "b")

    assert set(pivoted.edges()) == {("a", "b"), ("a", "d"), ("b", "c")}
    assert set(graph.edges()) == original_edges
    assert set(restored.edges()) == original_edges
    assert set(restored.nodes()) == set(graph.nodes())


def test_optimizer_returns_cleanly_when_no_pivot_is_available():
    graph = nx.empty_graph(4)

    best_graph, history, pivots = edm_pivot_sa(graph, 20, 1.0, random_state=0)

    assert best_graph.number_of_edges() == 0
    assert history == [0]
    assert pivots == []


def test_optimizer_finds_edge_reduction_on_four_cycle():
    graph = nx.cycle_graph(4)

    best_graph, history, pivots = edm_pivot_sa(graph, 1, 1.0, random_state=0)

    assert best_graph.number_of_edges() == 3
    assert history == [4, 3]
    assert len(pivots) == 1
    assert len(pivots[0]) == 2


def test_mixed_optimizer_reports_moves_that_recreate_best_graph():
    graph = nx.cycle_graph(6)

    best_graph, history, moves = edm_lc_pivot_sa(
        graph, 50, 2.0, random_state=4
    )
    recreated = graph.copy()
    for move in moves:
        if move[0] == "lc":
            neighbors = list(recreated.neighbors(move[1]))
            for index, first in enumerate(neighbors):
                for second in neighbors[index + 1:]:
                    if recreated.has_edge(first, second):
                        recreated.remove_edge(first, second)
                    else:
                        recreated.add_edge(first, second)
        else:
            recreated = pivot_graph(recreated, move[1], move[2])

    assert best_graph.number_of_edges() <= graph.number_of_edges()
    assert history[0] == graph.number_of_edges()
    assert set(recreated.edges()) == set(best_graph.edges())