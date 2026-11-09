#!/usr/bin/env python3
"""
Ultra Mega Super Benchmark Suite - Python Web Dashboard & Testing Engine
COMP3821/9801: Extended Algorithm Design and Analysis (UNSW Sydney)

Run with:
    python3 benchmark_dashboard.py
"""

import os
import sys
import json
import time
import webbrowser
import threading
import numpy as np
import networkx as nx
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Ensure local package import
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from graphstate_opt.edm_sa import edm_sa
from graphstate_opt.edm_pivot import edm_pivot_sa, edm_lc_pivot_sa
from graphstate_opt.edm_dualmode_anytime import edm_dualmode_anytime
from graphstate_opt.edm_dualmode_deep import edm_dualmode_deep


# =====================================================================
# 1. PROCEDURAL GRAPH GENERATORS & SUITES
# =====================================================================

def _toggle_neighborhood(G: nx.Graph, v):
    nb = list(G.neighbors(v))
    for i in range(len(nb)):
        for j in range(i + 1, len(nb)):
            u, w = nb[i], nb[j]
            if G.has_edge(u, w):
                G.remove_edge(u, w)
            else:
                G.add_edge(u, w)

def scramble_graph(G: nx.Graph, steps: int, rng):
    nodes = list(G.nodes())
    applied = 0
    attempts = 0
    while applied < steps and attempts < steps * 10:
        attempts += 1
        v = nodes[int(rng.integers(len(nodes)))]
        if G.degree(v) >= 2:
            _toggle_neighborhood(G, v)
            applied += 1

def ensure_connected(G: nx.Graph, rng):
    if nx.is_connected(G):
        return
    components = list(nx.connected_components(G))
    for i in range(1, len(components)):
        u = int(rng.choice(list(components[0])))
        v = int(rng.choice(list(components[i])))
        G.add_edge(u, v)

def build_suite(suite_key: str, base_seed: int = 42):
    instances = []

    if suite_key == "final_report_75":
        # 1. Planted Scrambled Trees (16 instances: 4x16, 4x32, 4x48, 4x64)
        for n in [16, 32, 48, 64]:
            for i in range(1, 5):
                rng = np.random.default_rng(base_seed + n * 1000 + i * 17)
                G = nx.Graph()
                G.add_nodes_from(range(n))
                for v in range(1, n):
                    G.add_edge(v, int(rng.integers(0, v)))
                scramble_graph(G, 3 * n, rng)
                instances.append({
                    "id": f"Tree-{n}-0{i}", "family": "Planted Tree", "n": n,
                    "graph": G, "groundTruth": n - 1
                })

        # 2. Complete Bipartite K(a, b) Asymmetry (5 instances, n=30)
        splits = [("Bipart-Sym-15", 15), ("Bipart-Asym-10", 10),
                  ("Bipart-Asym-05", 5),  ("Bipart-Asym-03", 3), ("Bipart-Asym-02", 2)]
        for name, a in splits:
            b = 30 - a
            G = nx.complete_bipartite_graph(a, b)
            instances.append({
                "id": name, "family": "Bipartite Complete", "n": 30,
                "graph": G, "groundTruth": 29
            })

        # 3. Defective Bipartite K(a, b) \ M (5 instances, n=12)
        defects = [("Defect-6-6-M1", 6, 1), ("Defect-6-6-M4", 6, 4),
                   ("Defect-4-8-M1", 4, 1), ("Defect-4-8-M3", 4, 3), ("Defect-3-9-M1", 3, 1)]
        for name, a, m in defects:
            b = 12 - a
            G = nx.complete_bipartite_graph(a, b)
            for i in range(m):
                u = i % a
                v = a + (i % b)
                if G.has_edge(u, v):
                    G.remove_edge(u, v)
            instances.append({
                "id": name, "family": "Bipartite Defective", "n": 12,
                "graph": G, "groundTruth": 11
            })

        # 4. Cabello Canonical Orbits (4 instances, n=8)
        cabello_specs = [
            (1, 7, [(0, i) for i in range(1, 8)]),
            (45, 7, [(0,1),(1,2),(2,3),(3,4),(4,5),(2,6),(3,7)]),
            (119, 8, [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,0),(0,7),(3,7)]),
            (146, 9, [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,0),(0,4),(1,5),(2,6),(3,7)])
        ]
        for orb_id, target, edges in cabello_specs:
            rng = np.random.default_rng(base_seed + 4000 + orb_id)
            G = nx.Graph()
            G.add_nodes_from(range(8))
            G.add_edges_from(edges)
            scramble_graph(G, 24, rng)
            instances.append({
                "id": f"Cabello-Orb-{orb_id}", "family": "Cabello Orbit", "n": 8,
                "graph": G, "groundTruth": target
            })

        # 5. Scrambled 2D MBQC Grids (8 instances)
        for L in [4, 5, 6, 7]:
            for i in range(1, 3):
                n = L * L
                rng = np.random.default_rng(base_seed + 5000 + L * 100 + i)
                G = nx.convert_node_labels_to_integers(nx.grid_2d_graph(L, L))
                scramble_graph(G, 3 * n, rng)
                instances.append({
                    "id": f"Grid-{L}x{L}-0{i}", "family": "Grid MBQC", "n": n,
                    "graph": G, "groundTruth": None
                })

        # 6. Scrambled Heavy-Hex Lattices (6 instances: 3x27, 3x45)
        for n in [27, 45]:
            for i in range(1, 4):
                rng = np.random.default_rng(base_seed + 6000 + n * 10 + i)
                G = nx.path_graph(n)
                step = max(3, n // 6)
                for u in range(0, n - step, step):
                    G.add_edge(u, u + step)
                scramble_graph(G, 3 * n, rng)
                instances.append({
                    "id": f"HeavyHex-{n}-0{i}", "family": "Heavy-Hex", "n": n,
                    "graph": G, "groundTruth": None
                })

        # 7. Scrambled Modular QPUs (6 instances: 3x36, 3x60)
        for n, mods in [(36, 3), (60, 4)]:
            mod_sz = n // mods
            for i in range(1, 4):
                rng = np.random.default_rng(base_seed + 7000 + n * 10 + i)
                G = nx.Graph()
                G.add_nodes_from(range(n))
                for m in range(mods):
                    m_nodes = list(range(m * mod_sz, (m + 1) * mod_sz))
                    for u_idx, u in enumerate(m_nodes):
                        for v in m_nodes[u_idx + 1:]:
                            if rng.random() < 0.75:
                                G.add_edge(u, v)
                    next_m_nodes = list(range(((m + 1) % mods) * mod_sz, (((m + 1) % mods) + 1) * mod_sz))
                    G.add_edge(int(rng.choice(m_nodes)), int(rng.choice(next_m_nodes)))
                ensure_connected(G, rng)
                scramble_graph(G, 3 * n, rng)
                instances.append({
                    "id": f"Modular-{n}-0{i}", "family": "Modular QPU", "n": n,
                    "graph": G, "groundTruth": None
                })

        # 8. Erdős–Rényi G(40, p) (15 instances)
        for tag, p in [("Sparse", 0.12), ("Medium", 0.35), ("Dense", 0.75)]:
            for i in range(1, 6):
                rng = np.random.default_rng(base_seed + 8000 + int(p * 1000) + i)
                G = nx.erdos_renyi_graph(40, p, seed=int(base_seed + 8000 + i))
                while not nx.is_connected(G):
                    G = nx.erdos_renyi_graph(40, p, seed=int(rng.integers(1e6)))
                instances.append({
                    "id": f"ER-{tag}-0{i}", "family": "Erdős–Rényi", "n": 40,
                    "graph": G, "groundTruth": None
                })

        # 9. Barabási–Albert Scale-Free (5 instances, n=40, m=2)
        for i in range(1, 6):
            G = nx.barabasi_albert_graph(40, 2, seed=int(base_seed + 9000 + i))
            instances.append({
                "id": f"ScaleFree-BA-0{i}", "family": "Scale-Free", "n": 40,
                "graph": G, "groundTruth": None
            })

        # 10. Watts–Strogatz Small-World (5 instances, n=40, k=4, beta=0.10)
        for i in range(1, 6):
            rng = np.random.default_rng(base_seed + 9500 + i)
            G = nx.watts_strogatz_graph(40, 4, 0.10, seed=int(base_seed + 9500 + i))
            ensure_connected(G, rng)
            instances.append({
                "id": f"SmallWorld-WS-0{i}", "family": "Small-World", "n": 40,
                "graph": G, "groundTruth": None
            })

    elif suite_key == "quick_smoke":
        rng = np.random.default_rng(base_seed)
        G1 = nx.path_graph(16)
        scramble_graph(G1, 48, rng)
        instances.append({"id": "Tree-16 (Planted)", "family": "Planted Tree", "n": 16, "graph": G1, "groundTruth": 15})
        instances.append({"id": "Bipart-Sym-15", "family": "Bipartite Complete", "n": 30, "graph": nx.complete_bipartite_graph(15, 15), "groundTruth": 29})
        G3 = nx.convert_node_labels_to_integers(nx.grid_2d_graph(4, 4))
        scramble_graph(G3, 48, rng)
        instances.append({"id": "Grid-4x4 (MBQC)", "family": "Grid MBQC", "n": 16, "graph": G3, "groundTruth": None})
        G4 = nx.erdos_renyi_graph(30, 0.35, seed=base_seed)
        ensure_connected(G4, rng)
        instances.append({"id": "ER-Medium (n=30)", "family": "Erdős–Rényi", "n": 30, "graph": G4, "groundTruth": None})

    return instances


# =====================================================================
# 2. ALGORITHM REGISTRY & EXECUTION
# =====================================================================

ACTIVE_ALGORITHMS = {
    "DualMode-Anytime": {
        "name": "DualMode-Anytime (Apex Ultra)",
        "fn": lambda G, B, s: edm_dualmode_anytime(G, budget=B, random_state=s)
    },
    "DualMode-Deep": {
        "name": "DualMode-Deep (Apex Deep)",
        "fn": lambda G, B, s: edm_dualmode_deep(G, budget=B, random_state=s)
    },
    "edm_sa": {
        "name": "edm_sa (Sharma et al. Baseline)",
        "fn": lambda G, B, s: edm_sa(G, k_max=max(10, B // G.number_of_nodes()), initial_temp=100.0)
    },
    "edm_pivot_sa": {
        "name": "edm_pivot_sa (Pivot-SA)",
        "fn": lambda G, B, s: edm_pivot_sa(G, k_max=B, initial_temp=100.0, random_state=s)
    },
    "edm_lc_pivot_sa": {
        "name": "edm_lc_pivot_sa (Mixed LC+Pivot)",
        "fn": lambda G, B, s: edm_lc_pivot_sa(G, k_max=B, initial_temp=100.0, random_state=s, pivot_probability=0.5)
    }
}

CACHED_SUITE = {}

def execute_task(suite_key, inst_idx, algo_key, budget, base_seed):
    cache_id = f"{suite_key}_{base_seed}"
    if cache_id not in CACHED_SUITE:
        CACHED_SUITE[cache_id] = build_suite(suite_key, base_seed)

    inst = CACHED_SUITE[cache_id][inst_idx]
    G = inst["graph"]
    start_edges = G.number_of_edges()
    gt = inst["groundTruth"]

    algo = ACTIVE_ALGORITHMS[algo_key]
    seed = int(base_seed + inst_idx * 137 + budget)

    t0 = time.perf_counter()
    res = algo["fn"](G, budget, seed)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    final_G = res[0]
    final_edges = final_G.number_of_edges()

    return {
        "instance": inst["id"],
        "family": inst["family"],
        "n": inst["n"],
        "target": gt,
        "start": start_edges,
        "algo": algo_key,
        "algo_name": algo["name"],
        "budget": budget,
        "edges": final_edges,
        "time_ms": round(elapsed_ms, 2)
    }


# =====================================================================
# 3. EMBEDDED DASHBOARD HTML/JS (RAW STRING TO PREVENT ESCAPING BUGS)
# =====================================================================

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Ultra Mega Super Benchmark Suite - Python Web Edition</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --primary: #2563eb; --primary-hover: #1d4ed8;
      --success: #16a34a; --warning: #ca8a04; --danger: #dc2626;
      --bg: #0f172a; --panel-bg: #1e293b; --border: #334155;
      --text: #f8fafc; --text-muted: #94a3b8;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
      margin: 0; padding: 24px; background: var(--bg); color: var(--text);
    }
    h1 { margin: 0 0 6px 0; font-size: 1.6em; }
    h2 { margin: 0 0 12px 0; font-size: 1.2em; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
    .subtitle { color: var(--text-muted); font-size: 0.9em; margin-bottom: 20px; }
    .card {
      background: var(--panel-bg); border: 1px solid var(--border);
      border-radius: 8px; padding: 18px; margin-bottom: 20px;
    }
    .flex-row { display: flex; gap: 14px; align-items: flex-end; flex-wrap: wrap; }
    .control-group { display: flex; flex-direction: column; gap: 4px; }
    label { font-size: 0.78em; font-weight: 700; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; }
    input, select, button {
      background: #0f172a; border: 1px solid var(--border); color: var(--text);
      padding: 8px 12px; font-size: 0.88em; border-radius: 6px; outline: none;
    }
    input:focus, select:focus { border-color: var(--primary); }
    button {
      background: var(--primary); color: white; border: none; font-weight: 600; cursor: pointer;
      transition: background 0.15s ease;
    }
    button:hover { background: var(--primary-hover); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { background: #475569; }
    .btn-secondary:hover { background: #334155; }
    .btn-success { background: var(--success); }
    .btn-success:hover { background: #15803d; }

    .algo-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
    .algo-pill {
      display: flex; align-items: center; gap: 6px; background: #0f172a; border: 1px solid var(--border);
      padding: 5px 12px; border-radius: 20px; font-size: 0.82em; cursor: pointer; user-select: none;
    }
    .algo-pill input { cursor: pointer; }

    .progress-box { width: 100%; height: 8px; background: #0f172a; border-radius: 4px; overflow: hidden; margin-top: 14px; display: none; }
    .progress-fill { height: 100%; width: 0%; background: var(--primary); transition: width 0.1s ease; }

    .table-responsive { width: 100%; overflow-x: auto; margin-top: 12px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.85em; text-align: left; }
    th, td { border: 1px solid var(--border); padding: 8px 10px; white-space: nowrap; }
    th { background: #0f172a; font-weight: 600; color: #cbd5e1; }
    tr:nth-child(even) { background: rgba(255, 255, 255, 0.02); }
    tr:hover { background: rgba(255, 255, 255, 0.05); }

    .badge { padding: 2px 6px; border-radius: 4px; font-size: 0.75em; font-weight: 700; }
    .badge-opt { background: #14532d; color: #86efac; border: 1px solid #166534; }
    .badge-win { background: #1e3a8a; color: #93c5fd; border: 1px solid #1d4ed8; }
    .best-score { font-weight: bold; color: #4ade80; }
    .rank-1 { color: #facc15; font-weight: bold; }
  </style>
</head>
<body>

  <h1>Ultra Mega Super Benchmark Suite (Python Native Engine)</h1>
  <div class="subtitle">Multi-Budget Combinatorial Gauntlet: Testing Python graphstate_opt MER heuristics live.</div>

  <!-- CONTROL PANEL -->
  <div class="card">
    <div class="flex-row">
      <div class="control-group">
        <label>Benchmark Suite:</label>
        <select id="suiteSelect">
          <option value="final_report_75" selected>★ Final Report Suite (75 Curated Instances)</option>
          <option value="quick_smoke">Quick Smoke Test (4 Instances)</option>
        </select>
      </div>

      <div class="control-group">
        <label>Eval Budgets (comma-separated):</label>
        <input type="text" id="budgetInput" value="100, 1000, 5000, 20000, 100000" style="width:190px;">
      </div>

      <div class="control-group">
        <label>Base Seed:</label>
        <input type="number" id="baseSeed" value="42" style="width:80px;">
      </div>

      <div style="display:flex; gap:8px;">
        <button id="runBtn" onclick="runPythonSuite()">Run Multi-Budget Gauntlet</button>
        <button class="btn-secondary" onclick="randomizeSeed()">Random Seed</button>
        <button class="btn-success" id="exportCsvBtn" onclick="exportCSV()" disabled>Export CSV</button>
        <button class="btn-secondary" id="exportJsonBtn" onclick="exportJSON()" disabled>Export JSON</button>
      </div>
    </div>

    <div style="margin-top: 14px;">
      <label>Active Python Algorithms:</label>
      <div class="algo-container" id="algoToggles"></div>
    </div>

    <div class="progress-box" id="pBox"><div class="progress-fill" id="pFill"></div></div>
    <div id="statusText" style="margin-top:8px; font-size:0.82em; color:var(--text-muted);">Ready. Backend connected to Python graphstate_opt.</div>
  </div>

  <!-- CHART CARD -->
  <div class="card" id="chartCard" style="display:none;">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.25rem;">
      <div>
        <h2 style="margin: 0; font-size: 1.2rem; font-weight: 700; border: none; padding: 0;">Compute Scaling Dynamics</h2>
        <div class="subtitle" style="margin: 0.25rem 0 0; font-size: 0.8rem;">Average Final Edges vs. Compute Budget (Lower is Better)</div>
      </div>
      <div style="display: flex; gap: 10px; align-items: center;">
        <div style="display: inline-flex; background: rgba(255,255,255,0.04); padding: 0.2rem; border-radius: 6px;">
          <button type="button" id="btnScaleRegular" style="background:transparent; border:none; padding:4px 8px; font-size:0.75rem;" onclick="setChartXScale('regular')">Regular</button>
          <button type="button" id="btnScaleLinear" style="background:rgba(255,255,255,0.15); border:none; padding:4px 8px; font-size:0.75rem;" onclick="setChartXScale('linear')">Linear Spatial</button>
        </div>
      </div>
    </div>
    <div style="position: relative; height: 380px; width: 100%;">
      <canvas id="scalingChart"></canvas>
    </div>
  </div>

  <!-- BUDGET MATRIX -->
  <div class="card" id="scalingCard" style="display:none;">
    <h2>Budget Scaling Matrix (Average Final Edges per Budget Tier)</h2>
    <div class="table-responsive">
      <table>
        <thead><tr id="scalingHeaderRow"></tr></thead>
        <tbody id="scalingBody"></tbody>
      </table>
    </div>
  </div>

  <!-- LEADERBOARD -->
  <div class="card" id="leaderboardCard" style="display:none;">
    <h2>Aggregate Leaderboard (Across All Budgets & Instances)</h2>
    <div class="table-responsive">
      <table>
        <thead>
          <tr>
            <th>Rank</th><th>Algorithm</th><th>Avg Final Edges</th><th>Avg Edge Reduction (%)</th>
            <th>Avg Gap (Known Targets)</th><th>Optimal Hits (%)</th><th>Wins / Best</th><th>Avg Time / Run</th><th>Total Time</th>
          </tr>
        </thead>
        <tbody id="leaderboardBody"></tbody>
      </table>
    </div>
  </div>

  <!-- FAMILY BREAKDOWN -->
  <div class="card" id="familyCard" style="display:none;">
    <h2>Performance by Graph Family</h2>
    <div class="table-responsive">
      <table>
        <thead><tr id="familyHeaderRow"></tr></thead>
        <tbody id="familyBody"></tbody>
      </table>
    </div>
  </div>

  <!-- GRANULAR DETAILS -->
  <div class="card" id="detailsCard" style="display:none;">
    <h2>Granular Per-Instance & Per-Budget Results</h2>
    <div class="table-responsive">
      <table>
        <thead><tr id="detailsHeaderRow"></tr></thead>
        <tbody id="detailsBody"></tbody>
      </table>
    </div>
  </div>

<script>
var AVAILABLE_ALGOS = [];
var suiteLog = [];
var chartInstance = null;
var currentXScaleMode = 'linear';
var cachedBudgetStats = null;
var cachedActiveAlgos = null;
var cachedBudgets = null;

async function initUI() {
  try {
    var res = await fetch("/api/init");
    var data = await res.json();
    AVAILABLE_ALGOS = data.algos;

    var container = document.getElementById("algoToggles");
    container.innerHTML = "";
    AVAILABLE_ALGOS.forEach(function(a) {
      var label = document.createElement("label");
      label.className = "algo-pill";
      label.innerHTML = '<input type="checkbox" id="chk_' + a.id + '" ' + (a.default ? 'checked' : '') + '> ' + a.name;
      container.appendChild(label);
    });
  } catch (err) {
    document.getElementById("statusText").innerText = "Failed to connect to backend: " + err;
  }
}

function randomizeSeed() {
  document.getElementById("baseSeed").value = Math.floor(Math.random() * 100000);
}

function getActiveAlgos() {
  return AVAILABLE_ALGOS.filter(function(a) {
    var el = document.getElementById("chk_" + a.id);
    return el && el.checked;
  });
}

function parseBudgets() {
  var raw = document.getElementById("budgetInput").value;
  return raw.split(",").map(function(s) { return parseInt(s.trim(), 10); }).filter(function(n) { return !isNaN(n) && n > 0; });
}

async function runPythonSuite() {
  var suiteKey = document.getElementById("suiteSelect").value;
  var budgets = parseBudgets();
  var baseSeed = parseInt(document.getElementById("baseSeed").value, 10);
  var activeAlgos = getActiveAlgos();

  if (activeAlgos.length === 0) {
    alert("Select at least one algorithm!");
    return;
  }

  var runBtn = document.getElementById("runBtn");
  var pBox = document.getElementById("pBox");
  var pFill = document.getElementById("pFill");
  var status = document.getElementById("statusText");

  runBtn.disabled = true;
  document.getElementById("exportCsvBtn").disabled = true;
  document.getElementById("exportJsonBtn").disabled = true;
  pBox.style.display = "block";
  pFill.style.width = "0%";

  var manRes = await fetch("/api/manifest?suite=" + suiteKey + "&seed=" + baseSeed);
  var manifest = await manRes.json();
  var instances = manifest.instances;

  suiteLog = [];
  document.getElementById("scalingCard").style.display = "none";
  document.getElementById("chartCard").style.display = "none";
  document.getElementById("leaderboardCard").style.display = "none";
  document.getElementById("familyCard").style.display = "none";
  document.getElementById("detailsCard").style.display = "block";
  document.getElementById("detailsBody").innerHTML = "";

  var headerRow = document.getElementById("detailsHeaderRow");
  var headerHtml = "<th>Instance</th><th>Family</th><th>n</th><th>Target MER</th><th>Start</th><th>Budget</th>";
  activeAlgos.forEach(function(a) { headerHtml += "<th>" + a.name + "</th>"; });
  headerRow.innerHTML = headerHtml;

  var totalTasks = budgets.length * instances.length * activeAlgos.length;
  var doneTasks = 0;

  var stats = {};
  var familyStats = {};
  var budgetStats = {};

  budgets.forEach(function(b) {
    budgetStats[b] = {};
    activeAlgos.forEach(function(a) { budgetStats[b][a.id] = { totalEdges: 0, count: 0 }; });
  });

  activeAlgos.forEach(function(a) {
    stats[a.id] = {
      name: a.name, totalEdges: 0, startEdges: 0,
      gaps: [], optimalHits: 0, wins: 0, totalTime: 0, runs: 0
    };
  });

  for (var bIdx = 0; bIdx < budgets.length; bIdx++) {
    var budget = budgets[bIdx];

    for (var instIdx = 0; instIdx < instances.length; instIdx++) {
      var inst = instances[instIdx];
      var instRow = {
        instance: inst.id, family: inst.family, n: inst.n,
        target: inst.groundTruth, start: inst.startEdges, budget: budget, results: {}
      };

      if (!familyStats[inst.family]) familyStats[inst.family] = {};

      var bestScoreThisRun = Infinity;
      var runOutputs = [];

      for (var aIdx = 0; aIdx < activeAlgos.length; aIdx++) {
        var a = activeAlgos[aIdx];
        status.innerText = "[Budget @" + budget + "] [" + (instIdx + 1) + "/" + instances.length + "] Python computing " + inst.id + " with " + a.name + "...";

        var taskRes = await fetch("/api/execute", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            suite: suiteKey, instIdx: instIdx, algo: a.id, budget: budget, seed: baseSeed
          })
        });
        var taskData = await taskRes.json();

        runOutputs.push({ id: a.id, edges: taskData.edges, time: taskData.time_ms });
        if (taskData.edges < bestScoreThisRun) bestScoreThisRun = taskData.edges;

        var s = stats[a.id];
        s.totalEdges += taskData.edges;
        s.startEdges += inst.startEdges;
        s.totalTime += taskData.time_ms;
        s.runs++;

        if (inst.groundTruth !== null) {
          var gap = taskData.edges - inst.groundTruth;
          s.gaps.push(gap);
          if (gap === 0) s.optimalHits++;
        }

        if (!familyStats[inst.family][a.id]) familyStats[inst.family][a.id] = { edges: 0, count: 0 };
        familyStats[inst.family][a.id].edges += taskData.edges;
        familyStats[inst.family][a.id].count++;

        budgetStats[budget][a.id].totalEdges += taskData.edges;
        budgetStats[budget][a.id].count++;

        instRow.results[a.id] = { edges: taskData.edges, time: taskData.time_ms.toFixed(1) };
        doneTasks++;
        pFill.style.width = Math.round((doneTasks / totalTasks) * 100) + "%";
      }

      runOutputs.forEach(function(out) {
        if (out.edges === bestScoreThisRun) stats[out.id].wins++;
      });

      suiteLog.push(instRow);
      appendDetailRow(inst, budget, activeAlgos, runOutputs, bestScoreThisRun);
    }
  }

  document.getElementById("scalingCard").style.display = "block";
  document.getElementById("leaderboardCard").style.display = "block";
  document.getElementById("familyCard").style.display = "block";
  document.getElementById("chartCard").style.display = "block";

  cachedBudgetStats = budgetStats;
  cachedActiveAlgos = activeAlgos;
  cachedBudgets = budgets;

  renderBudgetMatrix(budgetStats, activeAlgos, budgets);
  renderScalingChart(budgetStats, activeAlgos, budgets);
  renderLeaderboard(stats, activeAlgos, instances.length * budgets.length);
  renderFamilyBreakdown(familyStats, activeAlgos);

  status.innerHTML = "Multi-Budget Gauntlet complete. Evaluated <b>" + instances.length + "</b> instances across <b>" + budgets.length + "</b> budget tiers.";
  runBtn.disabled = false;
  document.getElementById("exportCsvBtn").disabled = false;
  document.getElementById("exportJsonBtn").disabled = false;
}

function appendDetailRow(inst, budget, activeAlgos, runOutputs, bestScore) {
  var tbody = document.getElementById("detailsBody");
  var tr = document.createElement("tr");

  var rowHtml = "<td><b>" + inst.id + "</b></td>" +
    "<td><small style='color:var(--text-muted);'>" + inst.family + "</small></td>" +
    "<td>" + inst.n + "</td>" +
    "<td>" + (inst.groundTruth !== null ? inst.groundTruth : "<small style='color:var(--text-muted);'>N/A</small>") + "</td>" +
    "<td>" + inst.startEdges + "</td>" +
    "<td><span class='badge' style='background:#334155; color:#cbd5e1;'>" + budget + "</span></td>";

  activeAlgos.forEach(function(a) {
    var out = runOutputs.find(function(o) { return o.id === a.id; });
    var isBest = (out.edges === bestScore);
    var isOptimal = (inst.groundTruth !== null && out.edges === inst.groundTruth);

    var cellBadge = "";
    if (isOptimal) cellBadge = "<span class='badge badge-opt'>OPT</span>";
    else if (isBest) cellBadge = "<span class='badge badge-win'>BEST</span>";

    rowHtml += "<td class='" + (isBest ? 'best-score' : '') + "'>" +
      out.edges + " " + cellBadge +
      "<br><small style='color:var(--text-muted); font-size:0.75em;'>" + out.time.toFixed(1) + "ms</small></td>";
  });

  tr.innerHTML = rowHtml;
  tbody.appendChild(tr);
}

function renderBudgetMatrix(budgetStats, activeAlgos, budgets) {
  var headerRow = document.getElementById("scalingHeaderRow");
  var hHtml = "<th>Algorithm</th>";
  budgets.forEach(function(b) { hHtml += "<th>@" + b + " Evals</th>"; });
  headerRow.innerHTML = hHtml;

  var tbody = document.getElementById("scalingBody");
  tbody.innerHTML = "";

  var colMins = {};
  budgets.forEach(function(b) {
    var mins = activeAlgos.map(function(a) { return budgetStats[b][a.id].totalEdges / budgetStats[b][a.id].count; });
    colMins[b] = Math.min.apply(null, mins);
  });

  activeAlgos.forEach(function(a) {
    var tr = document.createElement("tr");
    var rowHtml = "<td><b>" + a.name + "</b></td>";
    budgets.forEach(function(b) {
      var avg = budgetStats[b][a.id].totalEdges / budgetStats[b][a.id].count;
      var isColBest = Math.abs(avg - colMins[b]) < 1e-4;
      rowHtml += "<td class='" + (isColBest ? 'best-score' : '') + "'>" + avg.toFixed(1) + (isColBest ? " ★" : "") + "</td>";
    });
    tr.innerHTML = rowHtml;
    tbody.appendChild(tr);
  });
}

function renderLeaderboard(stats, activeAlgos, totalTrials) {
  var tbody = document.getElementById("leaderboardBody");
  tbody.innerHTML = "";

  var list = activeAlgos.map(function(a) { return stats[a.id]; });
  list.sort(function(a, b) { return (a.totalEdges / a.runs) - (b.totalEdges / b.runs); });

  list.forEach(function(s, idx) {
    var tr = document.createElement("tr");
    var avgEdges = (s.totalEdges / s.runs).toFixed(1);
    var pctReduction = (((s.startEdges - s.totalEdges) / s.startEdges) * 100).toFixed(1);
    var avgGap = s.gaps.length > 0 ? (s.gaps.reduce(function(a, b) { return a + b; }, 0) / s.gaps.length).toFixed(2) : "N/A";
    var optPct = s.gaps.length > 0 ? ((s.optimalHits / s.gaps.length) * 100).toFixed(1) + "%" : "N/A";
    var avgTime = (s.totalTime / s.runs).toFixed(1);

    tr.innerHTML = "<td class='" + (idx === 0 ? 'rank-1' : '') + "'><b>#" + (idx + 1) + "</b></td>" +
      "<td><b>" + s.name + "</b></td>" +
      "<td>" + avgEdges + "</td>" +
      "<td style='color:#38bdf8;'>-" + pctReduction + "%</td>" +
      "<td>" + (avgGap === "0.00" ? "<span class='best-score'>0.00</span>" : avgGap) + "</td>" +
      "<td>" + optPct + "</td>" +
      "<td><b>" + s.wins + "</b> / " + totalTrials + "</td>" +
      "<td>" + avgTime + " ms</td>" +
      "<td>" + (s.totalTime / 1000).toFixed(2) + " s</td>";
    tbody.appendChild(tr);
  });
}

function renderFamilyBreakdown(familyStats, activeAlgos) {
  var headerRow = document.getElementById("familyHeaderRow");
  var hHtml = "<th>Graph Family</th>";
  activeAlgos.forEach(function(a) { hHtml += "<th>" + a.name + "</th>"; });
  headerRow.innerHTML = hHtml;

  var tbody = document.getElementById("familyBody");
  tbody.innerHTML = "";

  Object.keys(familyStats).forEach(function(fam) {
    var tr = document.createElement("tr");
    var rowHtml = "<td><b>" + fam + "</b></td>";
    activeAlgos.forEach(function(a) {
      var entry = familyStats[fam][a.id];
      var avg = entry ? (entry.edges / entry.count).toFixed(1) : "-";
      rowHtml += "<td>" + avg + "</td>";
    });
    tr.innerHTML = rowHtml;
    tbody.appendChild(tr);
  });
}

var PALETTE = ['#10b981', '#38bdf8', '#8b5cf6', '#f59e0b', '#f43f5e'];

function renderScalingChart(budgetStats, activeAlgos, budgets) {
  var canvas = document.getElementById('scalingChart');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var sortedBudgets = budgets.slice().sort(function(a, b) { return a - b; });

  var datasets = activeAlgos.map(function(algo, idx) {
    var color = PALETTE[idx % PALETTE.length];
    var data = sortedBudgets.map(function(b) {
      var entry = budgetStats[b][algo.id];
      var avg = entry.totalEdges / entry.count;
      return currentXScaleMode === 'linear' ? { x: b, y: avg } : avg;
    });

    return {
      label: algo.name, data: data, borderColor: color, backgroundColor: color + '20',
      borderWidth: 2, tension: 0.3, pointRadius: 4
    };
  });

  var xScaleConfig = currentXScaleMode === 'linear' ? {
    type: 'linear', ticks: { color: '#8a8a93', callback: function(v) { return v >= 1000 ? (v/1000) + 'k' : v; } }
  } : {
    type: 'category', labels: sortedBudgets.map(function(b) { return "@" + b + " Evals"; }), ticks: { color: '#8a8a93' }
  };

  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: 'line', data: { datasets: datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { x: xScaleConfig, y: { ticks: { color: '#8a8a93' } } },
      plugins: { legend: { labels: { color: '#cbd5e1' } } }
    }
  });
}

function setChartXScale(mode) {
  currentXScaleMode = mode;
  document.getElementById('btnScaleRegular').style.background = mode === 'regular' ? 'rgba(255,255,255,0.15)' : 'transparent';
  document.getElementById('btnScaleLinear').style.background = mode === 'linear' ? 'rgba(255,255,255,0.15)' : 'transparent';
  if (cachedBudgetStats && cachedActiveAlgos && cachedBudgets) {
    renderScalingChart(cachedBudgetStats, cachedActiveAlgos, cachedBudgets);
  }
}

function exportCSV() {
  if (suiteLog.length === 0) return;
  var activeAlgos = getActiveAlgos();
  var NL = String.fromCharCode(10);
  var csv = "Instance,Family,Vertices,StartEdges,TargetMER,Budget," +
            activeAlgos.map(function(a) { return a.name + "_Edges," + a.name + "_TimeMS"; }).join(",") + NL;

  suiteLog.forEach(function(row) {
    var line = '"' + row.instance + '","' + row.family + '",' + row.n + ',' + row.start + ',' + (row.target !== null ? row.target : "") + ',' + row.budget;
    activeAlgos.forEach(function(a) {
      var r = row.results[a.id];
      line += "," + r.edges + "," + r.time;
    });
    csv += line + NL;
  });
  downloadFile(csv, "Python_MER_Benchmark_" + Date.now() + ".csv", "text/csv");
}

function exportJSON() {
  if (suiteLog.length === 0) return;
  downloadFile(JSON.stringify(suiteLog, null, 2), "Python_MER_Benchmark_" + Date.now() + ".json", "application/json");
}

function downloadFile(content, fileName, mimeType) {
  var blob = new Blob([content], { type: mimeType });
  var url = window.URL.createObjectURL(blob);
  var a = document.createElement("a");
  a.href = url; a.download = fileName; a.click();
}

window.addEventListener("DOMContentLoaded", initUI);
</script>
</body>
</html>
"""

# =====================================================================
# 4. LIGHTWEIGHT EMBEDDED PYTHON SERVER
# =====================================================================

class BenchmarkRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif parsed.path == "/api/init":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "algos": [
                    {"id": k, "name": v["name"], "default": (k in ["DualMode-Anytime", "DualMode-Deep", "edm_sa"])}
                    for k, v in ACTIVE_ALGORITHMS.items()
                ]
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        elif parsed.path == "/api/manifest":
            qs = parse_qs(parsed.query)
            suite_key = qs.get("suite", ["final_report_75"])[0]
            seed = int(qs.get("seed", [42])[0])

            cache_id = f"{suite_key}_{seed}"
            if cache_id not in CACHED_SUITE:
                CACHED_SUITE[cache_id] = build_suite(suite_key, seed)

            manifest_list = [
                {
                    "id": inst["id"],
                    "family": inst["family"],
                    "n": inst["n"],
                    "startEdges": inst["graph"].number_of_edges(),
                    "groundTruth": inst["groundTruth"]
                }
                for inst in CACHED_SUITE[cache_id]
            ]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"instances": manifest_list}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/execute":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode("utf-8"))

            res = execute_task(
                suite_key=data["suite"],
                inst_idx=data["instIdx"],
                algo_key=data["algo"],
                budget=data["budget"],
                base_seed=data["seed"]
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return  # Suppress verbose terminal HTTP logging


def run_server(port=8080):
    server = HTTPServer(("127.0.0.1", port), BenchmarkRequestHandler)
    url = f"http://127.0.0.1:{port}"
    print("\n" + "=" * 70)
    print(f"[*] Ultra Mega Benchmark Dashboard running at: {url}")
    print("[*] Connected to Python graphstate_opt algorithms.")
    print("=" * 70)

    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)