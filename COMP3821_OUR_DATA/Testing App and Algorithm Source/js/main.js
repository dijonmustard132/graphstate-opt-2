import { mulberry32 } from './graph.js';
import { GRAPH_GENERATORS, SUITE_REGISTRY } from './generators.js';
import { ALL_ALGOS } from './algorithms.js';
import { 
  renderScalingChart, 
  setChartXScale, 
  setChartYMode, 
  applyManualYBounds, 
  populateFamilyFilter 
} from './chart.js';

let suiteLog = [];

export function populateSelects() {
  const suiteSel = document.getElementById("suiteSelect");
  suiteSel.innerHTML = "";
  Object.keys(SUITE_REGISTRY).forEach(k => {
    const opt = document.createElement("option");
    opt.value = k;
    opt.innerText = SUITE_REGISTRY[k].name;
    suiteSel.appendChild(opt);
  });
  suiteSel.value = "final_report_75";

  const genSel = document.getElementById("customGenSelect");
  genSel.innerHTML = "";
  Object.keys(GRAPH_GENERATORS).forEach(k => {
    const opt = document.createElement("option");
    opt.value = k;
    opt.innerText = GRAPH_GENERATORS[k].name;
    genSel.appendChild(opt);
  });
}

export function renderAlgoToggles() {
  const container = document.getElementById("algoToggles");
  container.innerHTML = "";
  ALL_ALGOS.forEach(a => {
    const label = document.createElement("label");
    label.className = "algo-pill";
    label.innerHTML = `
      <input type="checkbox" id="chk_${a.id}" ${a.defaultChecked ? 'checked' : ''}>
      <span>${a.name}</span>
    `;
    container.appendChild(label);
  });
}

export function onSuiteChange() {
  const k = document.getElementById("suiteSelect").value;
  document.getElementById("customControls").style.display = (k === "custom_instance") ? "flex" : "none";
}

// Parses comma-separated seeds AND range syntax like '1-20'
export function parseSeeds() {
  const raw = document.getElementById("seedInput").value;
  const seeds = [];
  raw.split(",").forEach(part => {
    const s = part.trim();
    if (s.includes("-")) {
      const [start, end] = s.split("-").map(n => parseInt(n.trim(), 10));
      if (!isNaN(start) && !isNaN(end)) {
        for (let i = start; i <= end; i++) seeds.push(i);
      }
    } else {
      const n = parseInt(s, 10);
      if (!isNaN(n)) seeds.push(n);
    }
  });
  return seeds.length > 0 ? seeds : [42];
}

export function randomizeSeed() {
  const s1 = Math.floor(Math.random() * 100000);
  const s2 = Math.floor(Math.random() * 100000);
  const s3 = Math.floor(Math.random() * 100000);
  document.getElementById("seedInput").value = `${s1}, ${s2}, ${s3}`;
}

export function getActiveAlgos() {
  return ALL_ALGOS.filter(a => {
    const el = document.getElementById(`chk_${a.id}`);
    return el && el.checked;
  });
}

export function parseBudgets() {
  const raw = document.getElementById("budgetInput").value;
  const parts = raw.split(",").map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n) && n > 0);
  return parts.length > 0 ? parts : [20000];
}

export async function runSuite() {
  const suiteKey = document.getElementById("suiteSelect").value;
  const budgets = parseBudgets();
  const seeds = parseSeeds();
  const activeAlgos = getActiveAlgos();

  if (activeAlgos.length === 0) {
    alert("Select at least one algorithm!");
    return;
  }

  const runBtn = document.getElementById("runBtn");
  const pBox = document.getElementById("pBox");
  const pFill = document.getElementById("pFill");
  const status = document.getElementById("statusText");

  runBtn.disabled = true;
  document.getElementById("exportCsvBtn").disabled = true;
  document.getElementById("exportJsonBtn").disabled = true;
  pBox.style.display = "block";
  pFill.style.width = "0%";

  const instances = SUITE_REGISTRY[suiteKey].build(seeds[0]);
  suiteLog = [];

  document.getElementById("scalingCard").style.display = "none";
  document.getElementById("chartCard").style.display = "none";
  document.getElementById("leaderboardCard").style.display = "none";
  document.getElementById("familyCard").style.display = "none";
  document.getElementById("detailsCard").style.display = "none";
  document.getElementById("detailsBody").innerHTML = "";

  const headerRow = document.getElementById("detailsHeaderRow");
  headerRow.innerHTML = `
    <th>Instance</th><th>Family</th><th>n</th><th>Target</th><th>Start</th><th>Budget</th><th>Seed</th>
    ${activeAlgos.map(a => `<th>${a.name}</th>`).join("")}
  `;

  const totalTasks = seeds.length * budgets.length * instances.length * activeAlgos.length;
  let doneTasks = 0;

  const stats = {};
  const familyStats = {};
  const budgetStats = {};

  budgets.forEach(b => {
    budgetStats[b] = {};
    activeAlgos.forEach(a => budgetStats[b][a.id] = { totalEdges: 0, count: 0 });
  });

  activeAlgos.forEach(a => {
    stats[a.id] = {
      name: a.name, totalEdges: 0, startEdges: 0,
      gaps: [], optimalHits: 0, wins: 0, totalTime: 0, runs: 0
    };
  });

  for (let sIdx = 0; sIdx < seeds.length; sIdx++) {
    const currentSeed = seeds[sIdx];

    for (let bIdx = 0; bIdx < budgets.length; bIdx++) {
      const budget = budgets[bIdx];

      for (let instIdx = 0; instIdx < instances.length; instIdx++) {
        const inst = instances[instIdx];
        const startEdges = inst.graph.numEdges();
        const instRow = {
          instance: inst.name, family: inst.family, n: inst.graph.n,
          target: inst.groundTruth, start: startEdges, budget: budget, seed: currentSeed, results: {}
        };

        if (!familyStats[inst.family]) familyStats[inst.family] = {};

        let bestScoreThisRun = Infinity;
        const runOutputs = [];

        for (let aIdx = 0; aIdx < activeAlgos.length; aIdx++) {
          const a = activeAlgos[aIdx];
          status.innerText = `Running Seed ${sIdx + 1}/${seeds.length} · Budget @${budget.toLocaleString()} · [${instIdx + 1}/${instances.length}] ${inst.name} (${a.name})...`;

          await new Promise(r => setTimeout(r, 0));

          const algoHash = a.id.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
          const searchRng = mulberry32(currentSeed + bIdx * 54321 + instIdx * 10007 + algoHash * 137);
          
          const t0 = performance.now();
          const res = a.fn(inst.graph, budget, searchRng);
          const elapsed = performance.now() - t0;

          runOutputs.push({ id: a.id, edges: res.bestEdges, time: elapsed });
          if (res.bestEdges < bestScoreThisRun) bestScoreThisRun = res.bestEdges;

          const s = stats[a.id];
          s.totalEdges += res.bestEdges;
          s.startEdges += startEdges;
          s.totalTime += elapsed;
          s.runs++;

          if (inst.groundTruth !== null) {
            const gap = res.bestEdges - inst.groundTruth;
            s.gaps.push(gap);
            if (gap === 0) s.optimalHits++;
          }

          if (!familyStats[inst.family][a.id]) familyStats[inst.family][a.id] = { edges: 0, count: 0 };
          familyStats[inst.family][a.id].edges += res.bestEdges;
          familyStats[inst.family][a.id].count++;

          budgetStats[budget][a.id].totalEdges += res.bestEdges;
          budgetStats[budget][a.id].count++;

          instRow.results[a.id] = { edges: res.bestEdges, time: elapsed.toFixed(1) };
          doneTasks++;
          pFill.style.width = `${Math.round((doneTasks / totalTasks) * 100)}%`;
        }

        runOutputs.forEach(out => {
          if (out.edges === bestScoreThisRun) stats[out.id].wins++;
        });

        suiteLog.push(instRow);
        appendDetailRow(inst, startEdges, budget, currentSeed, activeAlgos, runOutputs, bestScoreThisRun);
      }
    }
  }

  document.getElementById("scalingCard").style.display = "block";
  document.getElementById("leaderboardCard").style.display = "block";
  document.getElementById("familyCard").style.display = "block";
  document.getElementById("chartCard").style.display = "block";
  document.getElementById("detailsCard").style.display = "block";

  // Populate dynamic topology filter with families found in the run
  populateFamilyFilter(suiteLog);

  renderBudgetMatrix(budgetStats, activeAlgos, budgets);
  renderScalingChart(suiteLog, activeAlgos, budgets); // Passes suiteLog for live topology filtering
  renderLeaderboard(stats, activeAlgos, instances.length * budgets.length * seeds.length);
  renderFamilyBreakdown(familyStats, activeAlgos);

  status.innerHTML = `Completed: <b>${instances.length}</b> instances across <b>${budgets.length}</b> budgets and <b>${seeds.length}</b> seeds (<b>${instances.length * budgets.length * seeds.length}</b> trials/algorithm).`;
  runBtn.disabled = false;
  document.getElementById("exportCsvBtn").disabled = false;
  document.getElementById("exportJsonBtn").disabled = false;
}

// Clean detail row with Google/Meta style badges and subtle typography (JSON import safe)
export function appendDetailRow(inst, startEdges, budget, seed, activeAlgos, runOutputs, bestScore) {
  const tbody = document.getElementById("detailsBody");
  const tr = document.createElement("tr");

  const vertexCount = inst.n !== undefined ? inst.n : (inst.graph ? inst.graph.n : "?");
  const displayName = inst.name || inst.instance || "—";
  const targetVal = (inst.groundTruth !== null && inst.groundTruth !== undefined && inst.groundTruth !== "")
    ? inst.groundTruth
    : (inst.target !== null && inst.target !== undefined && inst.target !== "" ? inst.target : null);

  let rowHtml = `
    <td><strong>${displayName}</strong></td>
    <td><span class="text-secondary">${inst.family}</span></td>
    <td>${vertexCount}</td>
    <td>${targetVal !== null ? targetVal : "<span class='text-secondary'>—</span>"}</td>
    <td>${startEdges}</td>
    <td><span class="badge badge-neutral">${typeof budget === "number" ? budget.toLocaleString() : budget}</span></td>
    <td><span class="badge badge-subtle">${seed}</span></td>
  `;

  activeAlgos.forEach(a => {
    const out = runOutputs.find(o => o.id === a.id);
    if (!out) {
      rowHtml += `<td><span class="text-secondary">—</span></td>`;
      return;
    }
    const isBest = (out.edges === bestScore);
    const isOptimal = (targetVal !== null && out.edges === Number(targetVal));

    let cellBadge = "";
    if (isOptimal) cellBadge = `<span class="badge badge-opt">OPT</span>`;
    else if (isBest) cellBadge = `<span class="badge badge-win">BEST</span>`;

    rowHtml += `
      <td class="${isBest ? 'best-score' : ''}">
        <div style="display:flex; align-items:center; gap:6px;">
          <span>${out.edges}</span>
          ${cellBadge}
        </div>
        <div class="text-secondary" style="font-size:0.75rem;">${out.time.toFixed(1)}ms</div>
      </td>
    `;
  });

  tr.innerHTML = rowHtml;
  tbody.appendChild(tr);
}

export function renderBudgetMatrix(budgetStats, activeAlgos, budgets) {
  const headerRow = document.getElementById("scalingHeaderRow");
  headerRow.innerHTML = `<th>Algorithm</th>${budgets.map(b => `<th>@${b.toLocaleString()} Evals</th>`).join("")}`;

  const tbody = document.getElementById("scalingBody");
  tbody.innerHTML = "";

  const colMins = {};
  budgets.forEach(b => {
    colMins[b] = Math.min(...activeAlgos.map(a => budgetStats[b][a.id].totalEdges / budgetStats[b][a.id].count));
  });

  activeAlgos.forEach(a => {
    const tr = document.createElement("tr");
    let rowHtml = `<td><strong>${a.name}</strong></td>`;
    budgets.forEach(b => {
      const avg = budgetStats[b][a.id].totalEdges / budgetStats[b][a.id].count;
      const isColBest = Math.abs(avg - colMins[b]) < 1e-4;
      rowHtml += `<td class="${isColBest ? 'best-score' : ''}">${avg.toFixed(1)} ${isColBest ? '<span class="star-pill">★</span>' : ''}</td>`;
    });
    tr.innerHTML = rowHtml;
    tbody.appendChild(tr);
  });
}

export function renderLeaderboard(stats, activeAlgos, totalTrials) {
  const tbody = document.getElementById("leaderboardBody");
  tbody.innerHTML = "";

  const list = activeAlgos.map(a => stats[a.id]);
  list.sort((a, b) => (a.totalEdges / a.runs) - (b.totalEdges / b.runs));

  list.forEach((s, idx) => {
    const tr = document.createElement("tr");
    const avgEdges = (s.totalEdges / s.runs).toFixed(1);
    const pctReduction = (((s.startEdges - s.totalEdges) / s.startEdges) * 100).toFixed(1);
    const avgGap = s.gaps.length > 0 ? (s.gaps.reduce((a, b) => a + b, 0) / s.gaps.length).toFixed(2) : "—";
    const optPct = s.gaps.length > 0 ? `${((s.optimalHits / s.gaps.length) * 100).toFixed(1)}%` : "—";
    const avgTime = (s.totalTime / s.runs).toFixed(1);

    tr.innerHTML = `
      <td class="${idx === 0 ? 'rank-1' : ''}"><strong>#${idx + 1}</strong></td>
      <td><strong>${s.name}</strong></td>
      <td><strong>${avgEdges}</strong></td>
      <td><span class="text-primary font-medium">-${pctReduction}%</span></td>
      <td>${avgGap === "0.00" ? "<span class='best-score'>0.00</span>" : avgGap}</td>
      <td>${optPct}</td>
      <td>${s.wins} <span class="text-secondary">/ ${totalTrials}</span></td>
      <td>${avgTime} ms</td>
      <td>${(s.totalTime / 1000).toFixed(2)} s</td>
    `;
    tbody.appendChild(tr);
  });
}

export function renderFamilyBreakdown(familyStats, activeAlgos) {
  const headerRow = document.getElementById("familyHeaderRow");
  headerRow.innerHTML = `<th>Graph Family</th>${activeAlgos.map(a => `<th>${a.name}</th>`).join("")}`;

  const tbody = document.getElementById("familyBody");
  tbody.innerHTML = "";

  Object.keys(familyStats).forEach(fam => {
    const tr = document.createElement("tr");
    let rowHtml = `<td><strong>${fam}</strong></td>`;
    activeAlgos.forEach(a => {
      const entry = familyStats[fam][a.id];
      const avg = entry ? (entry.edges / entry.count).toFixed(1) : "—";
      rowHtml += `<td>${avg}</td>`;
    });
    tr.innerHTML = rowHtml;
    tbody.appendChild(tr);
  });
}

export function exportCSV() {
  if (suiteLog.length === 0) return;
  const activeAlgos = getActiveAlgos();
  const escapeCsv = (str) => `"${String(str).replace(/"/g, '""')}"`;
  const NL = String.fromCharCode(10);

  let csv = "Instance,Family,Vertices,StartEdges,TargetMER,Budget,Seed," +
            activeAlgos.map(a => `${escapeCsv(a.name)}_Edges,${escapeCsv(a.name)}_TimeMS`).join(",") + NL;

  suiteLog.forEach(row => {
    let line = `${escapeCsv(row.instance)},${escapeCsv(row.family)},${row.n},${row.start},${row.target !== null ? row.target : ""},${row.budget},${row.seed}`;
    activeAlgos.forEach(a => {
      const r = row.results[a.id];
      line += `,${r.edges},${r.time}`;
    });
    csv += line + NL;
  });

  downloadFile(csv, `MER_MultiSeed_${Date.now()}.csv`, "text/csv");
}

export function exportJSON() {
  if (suiteLog.length === 0) return;
  const jsonStr = JSON.stringify(suiteLog, null, 2);
  downloadFile(jsonStr, `MER_MultiBudget_${Date.now()}.json`, "application/json");
}

function downloadFile(content, fileName, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  a.click();
}

function setupSegmentedControl(buttons, onSelect) {
  buttons.forEach(btn => {
    if (!btn) return;
    btn.addEventListener("click", () => {
      buttons.forEach(b => b && b.classList.remove("active"));
      btn.classList.add("active");
      onSelect(btn);
    });
  });
}

// ============================================================================
// JSON IMPORT & DASHBOARD RESTORATION
// ============================================================================

export function handleJSONImport(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      const loadedLog = JSON.parse(e.target.result);
      if (!Array.isArray(loadedLog) || loadedLog.length === 0) {
        alert("Invalid benchmark JSON: Expected a non-empty array of trial objects.");
        return;
      }
      renderImportedSuite(loadedLog);
    } catch (err) {
      alert("Error parsing JSON: " + err.message);
    }
  };
  reader.readAsText(file);
  event.target.value = "";
}

export function renderImportedSuite(loadedLog) {
  suiteLog = loadedLog;

  const algoKeys = Object.keys(suiteLog[0].results);
  const activeAlgos = algoKeys.map(id => {
    const found = ALL_ALGOS.find(a => a.id === id);
    return found ? found : { id: id, name: id };
  });

  const budgets = Array.from(new Set(suiteLog.map(r => r.budget))).sort((a, b) => a - b);

  const stats = {};
  const familyStats = {};
  const budgetStats = {};

  budgets.forEach(b => {
    budgetStats[b] = {};
    activeAlgos.forEach(a => budgetStats[b][a.id] = { totalEdges: 0, count: 0 });
  });

  activeAlgos.forEach(a => {
    stats[a.id] = {
      name: a.name, totalEdges: 0, startEdges: 0,
      gaps: [], optimalHits: 0, wins: 0, totalTime: 0, runs: 0
    };
  });

  document.getElementById("detailsBody").innerHTML = "";
  const headerRow = document.getElementById("detailsHeaderRow");
  headerRow.innerHTML = `
    <th>Instance</th><th>Family</th><th>n</th><th>Target MER</th><th>Start</th><th>Budget</th><th>Seed</th>
    ${activeAlgos.map(a => `<th>${a.name}</th>`).join("")}
  `;

  suiteLog.forEach(row => {
    if (!familyStats[row.family]) familyStats[row.family] = {};

    let bestScoreThisRun = Infinity;
    const runOutputs = [];

    activeAlgos.forEach(a => {
      const res = row.results[a.id];
      if (!res) return;
      const edges = res.edges;
      const time = parseFloat(res.time) || 0;

      runOutputs.push({ id: a.id, edges: edges, time: time });
      if (edges < bestScoreThisRun) bestScoreThisRun = edges;

      const s = stats[a.id];
      s.totalEdges += edges;
      s.startEdges += row.start;
      s.totalTime += time;
      s.runs++;

      if (row.target !== null && row.target !== undefined && row.target !== "") {
        const gap = edges - Number(row.target);
        s.gaps.push(gap);
        if (gap === 0) s.optimalHits++;
      }

      if (!familyStats[row.family][a.id]) familyStats[row.family][a.id] = { edges: 0, count: 0 };
      familyStats[row.family][a.id].edges += edges;
      familyStats[row.family][a.id].count++;

      budgetStats[row.budget][a.id].totalEdges += edges;
      budgetStats[row.budget][a.id].count++;
    });

    runOutputs.forEach(out => {
      if (out.edges === bestScoreThisRun) stats[out.id].wins++;
    });

    appendDetailRow(
      { name: row.instance, family: row.family, n: row.n, groundTruth: row.target },
      row.start,
      row.budget,
      row.seed !== undefined ? row.seed : "-",
      activeAlgos,
      runOutputs,
      bestScoreThisRun
    );
  });

  document.getElementById("scalingCard").style.display = "block";
  document.getElementById("leaderboardCard").style.display = "block";
  document.getElementById("familyCard").style.display = "block";
  document.getElementById("chartCard").style.display = "block";
  document.getElementById("detailsCard").style.display = "block";

  // Re-populate and render dynamic topology filter from imported dataset
  populateFamilyFilter(suiteLog);

  renderBudgetMatrix(budgetStats, activeAlgos, budgets);
  renderScalingChart(suiteLog, activeAlgos, budgets);
  renderLeaderboard(stats, activeAlgos, suiteLog.length);
  renderFamilyBreakdown(familyStats, activeAlgos);

  document.getElementById("exportCsvBtn").disabled = false;
  document.getElementById("exportJsonBtn").disabled = false;

  document.getElementById("statusText").innerHTML = `Successfully loaded <b>${suiteLog.length}</b> trials from JSON.`;
}

// Event Bindings
window.addEventListener("DOMContentLoaded", () => {
  populateSelects();
  renderAlgoToggles();

  document.getElementById("suiteSelect").addEventListener("change", onSuiteChange);
  document.getElementById("runBtn").addEventListener("click", runSuite);
  document.getElementById("randSeedBtn").addEventListener("click", randomizeSeed);
  document.getElementById("exportCsvBtn").addEventListener("click", exportCSV);
  document.getElementById("exportJsonBtn").addEventListener("click", exportJSON);

  document.getElementById("importJsonBtn").addEventListener("click", () => {
    document.getElementById("importJsonInput").click();
  });
  document.getElementById("importJsonInput").addEventListener("change", handleJSONImport);

  // Live Graph Class / Topology Chart Filter
  const familyFilter = document.getElementById("chartFamilyFilter");
  if (familyFilter) {
    familyFilter.addEventListener("change", () => {
      renderScalingChart();
    });
  }

  // Segmented control button state handlers
  const scaleBtns = [document.getElementById("btnScaleRegular"), document.getElementById("btnScaleLinear")];
  setupSegmentedControl(scaleBtns, (btn) => {
    setChartXScale(btn.id === 'btnScaleLinear' ? 'linear' : 'regular');
  });

  const yBtns = [document.getElementById("btnYAuto"), document.getElementById("btnYTight"), document.getElementById("btnYZero")];
  setupSegmentedControl(yBtns, (btn) => {
    if (btn.id === 'btnYAuto') setChartYMode('auto');
    if (btn.id === 'btnYTight') setChartYMode('tight');
    if (btn.id === 'btnYZero') setChartYMode('zero');
  });

  const manualMin = document.getElementById("manualYMin");
  const manualMax = document.getElementById("manualYMax");
  if (manualMin) manualMin.addEventListener("input", applyManualYBounds);
  if (manualMax) manualMax.addEventListener("input", applyManualYBounds);
});