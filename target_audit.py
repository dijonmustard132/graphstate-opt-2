"""Verify the nine nontrivial configured targets in the 75-instance suite.

The graph definitions match the final_report_75 suite in
COMP3821_OUR_DATA/Testing Rig/js/generators.js in the Group 34 repository.
They are enumerated before scrambling because every scrambling move is an LC.
The 16 planted trees and five complete bipartite graphs have a direct tree
certificate, so they do not require exhaustive enumeration.

Run with: python target_audit.py
"""

from collections import deque


def orbit_minimum(n, edges):
    """Return the true minimum edge count and size of a labelled LC orbit."""
    edge_bit = [[0] * n for _ in range(n)]
    index = 0
    for u in range(n):
        for v in range(u):
            edge_bit[u][v] = edge_bit[v][u] = 1 << index
            index += 1
    start = 0
    for u, v in edges:
        assert 0 <= u < n and 0 <= v < n and u != v
        start |= edge_bit[u][v]

    # Local complementation XORs the clique on the current neighbour set.
    clique_mask = [0] * (1 << n)
    for subset in range(1, len(clique_mask)):
        lowest_bit = subset & -subset
        u = lowest_bit.bit_length() - 1
        others = subset ^ lowest_bit
        clique_mask[subset] = clique_mask[others]
        for v in range(u + 1, n):
            if others & (1 << v):
                clique_mask[subset] |= edge_bit[u][v]

    queue = deque([start])
    seen = {start}
    minimum = start.bit_count()
    while queue:
        graph = queue.popleft()
        for row in edge_bit:
            neighbours = 0
            for v, bit in enumerate(row):
                if graph & bit:
                    neighbours |= 1 << v
            successor = graph ^ clique_mask[neighbours]
            if successor not in seen:
                seen.add(successor)
                queue.append(successor)
                minimum = min(minimum, successor.bit_count())
    return minimum, len(seen)


def defective_bipartite_edges(a, missing_count, n=12):
    """Recreate the dashboard's matching deletion from K_{a,n-a}."""
    b = n - a
    missing = {(i % a, a + (i % b)) for i in range(missing_count)}
    return [(u, v) for u in range(a) for v in range(a, n) if (u, v) not in missing]


if __name__ == "__main__":
    # Distinct labelled stars and the clique form the orbit of K_4.
    assert orbit_minimum(4, [(0, 1), (0, 2), (0, 3)]) == (3, 5)
    assert orbit_minimum(4, [(u, v) for u in range(4) for v in range(u)]) == (3, 5)
    assert orbit_minimum(4, [(0, 1), (2, 3)]) == (2, 1)

    cabello = [
        ("Cabello-Orb-1", 7, [(0, i) for i in range(1, 8)], (7, 9)),
        ("Cabello-Orb-45", 7,
         [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (2, 6), (3, 7)], (7, 139)),
        ("Cabello-Orb-119", 8,
         [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 0), (0, 7), (3, 7)],
         (9, 2952)),
        ("Cabello-Orb-146", 9,
         [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 0),
          (0, 4), (1, 5), (2, 6), (3, 7)], (12, 3156)),
    ]
    defective = [
        ("Defect-6-6-M1", 6, 1, (11, 268)),
        ("Defect-6-6-M4", 6, 4, (14, 37152)),
        ("Defect-4-8-M1", 4, 1, (11, 244)),
        ("Defect-4-8-M3", 4, 3, (13, 6480)),
        ("Defect-3-9-M1", 3, 1, (11, 214)),
    ]
    cases = [(name, 8, target, edges, expected) for name, target, edges, expected in cabello]
    cases.extend(
        (name, 12, 11, defective_bipartite_edges(a, missing_count), expected)
        for name, a, missing_count, expected in defective
    )
    print("Instance,Configured target,Exact minimum,Labelled orbit size")
    for name, n, target, edges, expected in cases:
        minimum, orbit_size = orbit_minimum(n, edges)
        assert (minimum, orbit_size) == expected, name
        print(f"{name},{target},{minimum},{orbit_size}")
