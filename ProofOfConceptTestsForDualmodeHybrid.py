# Adam - How to Use (Instructions For Mac, Likely To Work On Other Systems):
# 1. Install Repo
# 2. Run "python3 -m venv venv && source venv/bin/activate" (similar to node_modules. This command is likely different on Windows)
# 3. Run "pip install --upgrade pip" (updates pip)
# 4. Run "pip install -e ." (installs Deps for this file and the whole project too)
# 5. Run "python3 ProofOfConceptTestsForDualmodeHybrid.py" (runs this file)
# 6. When you do step 5, don't be surprised if there is a wait for the first time as python may be setting up certain things.

import ast
import math
import os
import random
import time
import networkx as nx
import numpy as np
import pandas as pd

from graphstate_opt.edm_sa import edm_sa

# =====================================================================
# Graph Operations
# =====================================================================


def local_complementation(G, v):
    neighbors = list(G.neighbors(v))
    k = len(neighbors)
    for i in range(k):
        u1 = neighbors[i]
        for j in range(i + 1, k):
            u2 = neighbors[j]
            if G.has_edge(u1, u2):
                G.remove_edge(u1, u2)
            else:
                G.add_edge(u1, u2)


def delta_edges_lc(G, v):
    neighbors = list(G.neighbors(v))
    k = len(neighbors)
    if k < 2:
        return 0
    max_possible = k * (k - 1) // 2
    existing = 0
    for i in range(k):
        for j in range(i + 1, k):
            if G.has_edge(neighbors[i], neighbors[j]):
                existing += 1
    return max_possible - 2 * existing


def pivot(G, u, v):
    local_complementation(G, u)
    local_complementation(G, v)
    local_complementation(G, u)


def delta_edges_pivot(G, u, v):
    """Analytic O(|Nu|*|Nv|) calculation of delta edges under a pivot on (u, v).

    Equivalent to H = G.copy(); pivot(H, u, v); return H.number_of_edges() -
    G.number_of_edges(), but without deep-copying or mutating the graph.
    """
    Nu = set(G.neighbors(u)) - {v}
    Nv = set(G.neighbors(v)) - {u}
    C = Nu & Nv
    A = Nu - C
    B = Nv - C

    def bipartite_delta(S1, S2):
        if not S1 or not S2:
            return 0
        existing = sum(1 for x in S1 for y in S2 if G.has_edge(x, y))
        return len(S1) * len(S2) - 2 * existing

    return bipartite_delta(A, B) + bipartite_delta(A, C) + bipartite_delta(B, C)


# =====================================================================
# Your Algorithm (alg_custom_5_1)
# =====================================================================


def alg_custom_5_1(in_graph, budget, rng):
    g = in_graph.copy()
    n = g.number_of_nodes()
    cur = g.number_of_edges()
    best = cur
    best_g = g.copy()
    evals = 0

    est_step_cost = max(n, n + int(0.28 * cur))
    est_iters = max(15, budget // est_step_cost)
    T0, Tmin = 2.0, 0.005
    alpha = (Tmin / T0) ** (1.0 / est_iters)
    T = T0

    stagnant = 0
    tabu = [-1, -1, -1, -1]
    tabu_ptr = 0

    while evals < budget:
        if cur <= n - 1:
            break
        T = max(Tmin, T * alpha)

        if stagnant >= 5:
            T = min(2.5, T * 2.0)
            stagnant = 0

        # Level 1: Rapid Single-LC Scan
        best_single = None
        min_single_delta = float("inf")
        second_single = None
        single_deltas = {}

        for v in range(n):
            if g.degree(v) < 2 or (stagnant < 2 and v in tabu):
                single_deltas[v] = 999
                continue

            evals += 1
            dE = delta_edges_lc(g, v)
            single_deltas[v] = dE
            if dE < min_single_delta:
                second_single = best_single
                min_single_delta = dE
                best_single = {"type": "lc", "u": v, "dE": dE}
            if evals >= budget:
                break

        # High-yield immediate greedy step
        if best_single and best_single["dE"] <= -2:
            local_complementation(g, best_single["u"])
            tabu[tabu_ptr % 4] = best_single["u"]
            tabu_ptr += 1
            cur += best_single["dE"]
            if cur < best:
                best = cur
                best_g = g.copy()
                stagnant = 0
            continue

        # Level 2: Pruned Pivot Scan
        best_pivot = None
        min_pivot_delta = float("inf")
        second_pivot = None

        if evals < budget:
            prune_cutoff = (
                max(2, min_single_delta + 3)
                if min_single_delta <= 0
                else (min_single_delta + 2)
            )
            for u in range(n):
                if g.degree(u) < 2:
                    continue
                for v in range(u + 1, n):
                    if g.has_edge(u, v) and g.degree(v) >= 2:
                        if (
                            stagnant < 2
                            and single_deltas.get(u, 999) > prune_cutoff
                            and single_deltas.get(v, 999) > prune_cutoff
                        ):
                            continue
                        evals += 3
                        d = delta_edges_pivot(g, u, v)
                        if d < min_pivot_delta:
                            second_pivot = best_pivot
                            min_pivot_delta = d
                            best_pivot = {
                                "type": "pivot",
                                "u": u,
                                "v": v,
                                "dE": d,
                            }
                        if evals >= budget:
                            break
                if evals >= budget:
                    break

        # Level 3: Dual-Mode Selection
        pool = []
        if best_single:
            pool.append(best_single)
        if best_pivot:
            pool.append(best_pivot)
        if second_single and second_single["dE"] <= min_single_delta + 1:
            pool.append(second_single)
        if second_pivot and second_pivot["dE"] <= min_pivot_delta + 1:
            pool.append(second_pivot)

        if not pool:
            break
        pool.sort(key=lambda m: m["dE"])

        if pool[0]["dE"] < 0:
            chosen = pool[0]
        else:
            candidates = pool[:3]
            min_d = candidates[0]["dE"]
            weights = [
                math.exp(-(m["dE"] - min_d) / max(T, 0.05)) for m in candidates
            ]
            sum_w = sum(weights)
            r = rng.random() * sum_w
            chosen = candidates[0]
            for i, cand in enumerate(candidates):
                r -= weights[i]
                if r <= 0:
                    chosen = cand
                    break

        prob_accept = (
            math.exp(-chosen["dE"] / max(T, 1e-4)) if chosen["dE"] > 0 else 1.0
        )
        if chosen["dE"] <= 0 or rng.random() < prob_accept:
            if chosen["type"] == "lc":
                local_complementation(g, chosen["u"])
                tabu[tabu_ptr % 4] = chosen["u"]
                tabu_ptr += 1
            else:
                pivot(g, chosen["u"], chosen["v"])
                tabu[tabu_ptr % 4] = chosen["u"]
                tabu[(tabu_ptr + 1) % 4] = chosen["v"]
                tabu_ptr += 2
            cur += chosen["dE"]
            if cur < best:
                best = cur
                best_g = g.copy()
                stagnant = 0
            else:
                stagnant += 1
        else:
            stagnant += 1

    return best_g, best, evals


# =====================================================================
# Synthetic Graph Helpers
# =====================================================================


def generate_bounded_degree(n, max_d, seed):
    rng = np.random.default_rng(seed)
    for _ in range(100):
        degrees = rng.integers(1, max_d + 1, size=n)
        if sum(degrees) % 2 != 0:
            idx = int(rng.integers(0, n))
            degrees[idx] += 1 if degrees[idx] < max_d else -1
        try:
            G = nx.havel_hakimi_graph(degrees)
            if nx.is_connected(G):
                return G
        except nx.NetworkXError:
            continue
    # Fallback to random d-regular
    d = min(max_d, n - 1)
    if (n * d) % 2 != 0:
        d -= 1
    return nx.random_regular_graph(d, n, seed=seed)


# =====================================================================
# Main Benchmark Engine
# =====================================================================

MASTER_SEED = 2026
records = []


def run_single_comparison(
    suite_name, config_label, G_input, seed, true_mer=None, budget=1800
):
    init_edges = G_input.number_of_edges()

    # 1. Run Their Algorithm
    t0 = time.perf_counter()
    res_theirs = edm_sa(G_input.copy(), k_max=100, initial_temp=100)
    time_theirs = time.perf_counter() - t0
    g_theirs = res_theirs[0] if isinstance(res_theirs, tuple) else res_theirs
    edges_theirs = g_theirs.number_of_edges()

    # 2. Run Your Algorithm
    algo_rng = random.Random(seed)
    t0 = time.perf_counter()
    _, edges_yours, evals_used = alg_custom_5_1(
        G_input.copy(), budget=budget, rng=algo_rng
    )
    time_yours = time.perf_counter() - t0

    # Determine Winner
    if edges_yours < edges_theirs:
        winner = "Yours"
    elif edges_yours > edges_theirs:
        winner = "Theirs"
    else:
        winner = "Tie"

    rec = {
        "suite": suite_name,
        "config": config_label,
        "nodes": G_input.number_of_nodes(),
        "init_edges": init_edges,
        "theirs_edges": edges_theirs,
        "yours_edges": edges_yours,
        "edge_delta": edges_theirs - edges_yours,
        "time_theirs_s": round(time_theirs, 4),
        "time_yours_s": round(time_yours, 4),
        "winner": winner,
        "true_mer": true_mer,
        "gap_theirs": (edges_theirs - true_mer)
        if true_mer is not None
        else None,
        "gap_yours": (edges_yours - true_mer) if true_mer is not None else None,
        "yours_hit_opt": (edges_yours == true_mer)
        if true_mer is not None
        else None,
    }
    records.append(rec)
    return rec


def main():
    print("=" * 80)
    print("  MEGA GIANT ULTRA MULTI-CONFIGURATION BENCHMARK SUITE (SEEDED)")
    print("=" * 80)
    random.seed(MASTER_SEED)
    np.random.seed(MASTER_SEED)

    # -----------------------------------------------------------------
    # SUITE 1: Known Ground-Truth Exact MER Rediscovery (ER + BD Datasets)
    # -----------------------------------------------------------------
    print("\n[+] SUITE 1: Ground-Truth Scramble Rediscovery (ER & BD MER Datasets)")
    for dataset, csv_file in [
        ("ER-Mers", "data/er_mers.csv"),
        ("BD-Mers", "data/bd_mers.csv"),
    ]:
        if not os.path.exists(csv_file):
            print(f"    Notice: {csv_file} not found, skipping {dataset}.")
            continue
        df = pd.read_csv(csv_file)
        sample_size = min(15, len(df))
        print(
            f"    -> Running {sample_size} scrambled trials against {dataset}..."
        )

        for idx, row in df.head(sample_size).iterrows():
            seed = MASTER_SEED + 1000 + idx
            scramble_rng = random.Random(seed)

            # Build graph
            edges = ast.literal_eval(row["edges"])
            G = nx.Graph()
            G.add_nodes_from(range(row["num_vertices"]))
            G.add_edges_from(edges)
            true_mer = G.number_of_edges()

            # Scramble with 12 random LCs
            G_scrambled = G.copy()
            nodes = list(G_scrambled.nodes())
            for _ in range(12):
                cands = [v for v in nodes if G_scrambled.degree(v) >= 2]
                if cands:
                    local_complementation(
                        G_scrambled, scramble_rng.choice(cands)
                    )

            run_single_comparison(
                suite_name="Ground-Truth",
                config_label=f"{dataset}_n{row['num_vertices']}",
                G_input=G_scrambled,
                seed=seed,
                true_mer=true_mer,
                budget=2000,
            )

    # -----------------------------------------------------------------
    # SUITE 2: Erdős-Rényi Density Matrix (Varying n and edge density p)
    # -----------------------------------------------------------------
    print(
        "\n[+] SUITE 2: Erdős-Rényi Density Grid (n ∈ [10, 14, 18], p ∈ [0.25, 0.50, 0.75])"
    )
    n_values = [10, 14, 18]
    p_values = [0.25, 0.50, 0.75]
    reps_per_cell = 4

    for n in n_values:
        for p in p_values:
            for rep in range(reps_per_cell):
                seed = MASTER_SEED + 2000 + n * 100 + int(p * 100) + rep
                G = nx.erdos_renyi_graph(n, p, seed=seed)
                # Ensure simple connectivity
                if not nx.is_connected(G):
                    comps = list(nx.connected_components(G))
                    comp_rng = random.Random(seed)
                    for c_idx in range(len(comps) - 1):
                        u = comp_rng.choice(list(comps[c_idx]))
                        v = comp_rng.choice(list(comps[c_idx + 1]))
                        G.add_edge(u, v)

                run_single_comparison(
                    suite_name="ER-Grid",
                    config_label=f"ER_n{n}_p{p:.2f}",
                    G_input=G,
                    seed=seed,
                    budget=1800,
                )
    print(
        f"    -> Finished {len(n_values) * len(p_values) * reps_per_cell} ER grid trials."
    )

    # -----------------------------------------------------------------
    # SUITE 3: Hardware Bounded-Degree Topologies (Max Degree 3, 5)
    # -----------------------------------------------------------------
    print(
        "\n[+] SUITE 3: Hardware Bounded-Degree Topologies (d_max ∈ [3, 5], n ∈ [12, 16, 22])"
    )
    bd_configs = [(12, 3), (12, 5), (16, 3), (16, 5), (22, 3), (22, 5)]
    reps_bd = 4

    for n, d_max in bd_configs:
        for rep in range(reps_bd):
            seed = MASTER_SEED + 3000 + n * 10 + d_max + rep
            G = generate_bounded_degree(n, d_max, seed=seed)
            run_single_comparison(
                suite_name="Bounded-Degree",
                config_label=f"BD_n{n}_d{d_max}",
                G_input=G,
                seed=seed,
                budget=2000,
            )
    print(f"    -> Finished {len(bd_configs) * reps_bd} Bounded-Degree trials.")

    # -----------------------------------------------------------------
    # SUITE 4: High-Qubit Scaling Challenge (n ∈ [30, 50, 75])
    # -----------------------------------------------------------------
    print("\n[+] SUITE 4: High-Qubit Scaling Stress Test (n ∈ [30, 50, 75])")
    scaling_nodes = [30, 50, 75]
    reps_scale = 3

    for n in scaling_nodes:
        for rep in range(reps_scale):
            seed = MASTER_SEED + 4000 + n + rep
            G = nx.erdos_renyi_graph(n, p=0.35, seed=seed)
            # Budget scales gracefully with graph size
            scaled_budget = int(1200 + 40 * n)
            run_single_comparison(
                suite_name="High-Qubit-Scaling",
                config_label=f"Scale_n{n}",
                G_input=G,
                seed=seed,
                budget=scaled_budget,
            )
    print(
        f"    -> Finished {len(scaling_nodes) * reps_scale} High-Qubit scaling trials."
    )

    # =================================================================
    # AGGREGATE SUMMARY REPORTS
    # =================================================================
    df_res = pd.DataFrame(records)
    csv_filename = "mega_benchmark_results.csv"
    df_res.to_csv(csv_filename, index=False)
    print(f"\n[✔] Detailed trial logs written to '{csv_filename}'")

    print("\n" + "=" * 80)
    print("                    MEGA BENCHMARK EXECUTIVE SUMMARY")
    print("=" * 80)

    # 1. Overall Win/Tie/Loss
    total_runs = len(df_res)
    yours_wins = (df_res["winner"] == "Yours").sum()
    theirs_wins = (df_res["winner"] == "Theirs").sum()
    ties = (df_res["winner"] == "Tie").sum()

    print(f"\n[OVERALL RECORD across {total_runs} total experiments]")
    print(
        f"  * Your Algorithm Wins : {yours_wins:3d} ({yours_wins / total_runs * 100:.1f}%)"
    )
    print(f"  * Ties                : {ties:3d} ({ties / total_runs * 100:.1f}%)")
    print(
        f"  * Their EDM-SA Wins   : {theirs_wins:3d} ({theirs_wins / total_runs * 100:.1f}%)"
    )

    # 2. Performance by Suite
    print("\n" + "-" * 80)
    print(
        f"{'Suite':<20} | {'Runs':<5} | {'Their Avg':<10} | {'Your Avg':<10} | {'Edge Adv.':<10} | {'Your Win%'}"
    )
    print("-" * 80)
    for suite, grp in df_res.groupby("suite"):
        avg_th = grp["theirs_edges"].mean()
        avg_yr = grp["yours_edges"].mean()
        adv = avg_th - avg_yr
        win_pct = (grp["winner"] == "Yours").mean() * 100
        print(
            f"{suite:<20} | {len(grp):<5} | {avg_th:<10.2f} | {avg_yr:<10.2f} | {adv:<+10.2f} | {win_pct:.1f}%"
        )

    # 3. Ground Truth Exact MER Accuracy
    df_gt = df_res[df_res["true_mer"].notnull()]
    if not df_gt.empty:
        print("\n" + "-" * 80)
        print("GROUND-TRUTH EXACT OPTIMUM (MER) METRICS:")
        print(
            f"  * Your Exact MER Hit Rate: {df_gt['yours_hit_opt'].mean() * 100:.1f}%"
        )
        print(
            f"  * Your Average Distance to MER: +{df_gt['gap_yours'].mean():.2f} edges"
        )
        print(
            f"  * Their Average Distance to MER: +{df_gt['gap_theirs'].mean():.2f} edges"
        )

    # 4. Runtime Summary
    print("\n" + "-" * 80)
    print(
        f"Average Execution Time per Graph -> Theirs: {df_res['time_theirs_s'].mean():.3f}s | Yours: {df_res['time_yours_s'].mean():.3f}s"
    )
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()