# Compare our dualmode with the published MER's by the author.

import ast
import pandas as pd
import networkx as nx
from graphstate_opt.edm_dualmode_anytime import edm_dualmode_anytime

# Load authors' published Erdős–Rényi benchmarks
df_er = pd.read_csv("data/er_mers.csv")

for idx, row in df_er.head(10).iterrows():
    n = int(row["num_vertices"])
    author_best = int(row["num_edges"])
    edge_list = ast.literal_eval(row["edges"])
    
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from(edge_list)
    
    # Run DualMode-Anytime on their exact graph
    G_our, _, _ = edm_dualmode_anytime(G, budget=20000, random_state=42)
    our_best = G_our.number_of_edges()
    
    diff = author_best - our_best
    status = f"BEAT BY {diff} EDGES!" if diff > 0 else "TIED"
    print(f"Graph #{idx+1} (n={n}): Authors' MER = {author_best} | Our MER = {our_best} -> {status}")