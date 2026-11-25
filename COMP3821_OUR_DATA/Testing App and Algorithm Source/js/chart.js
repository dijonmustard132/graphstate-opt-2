let chartInstance = null;
let chartCachedData = null;
export let currentXScaleMode = 'linear';
export let currentYScaleMode = 'auto';

const CHART_COLOR_PALETTE = [
  '#10b981', '#38bdf8', '#8b5cf6', '#f59e0b', '#f43f5e',
  '#06b6d4', '#a855f7', '#fb923c', '#e2e8f0', '#94a3b8'
];

export function populateFamilyFilter(suiteLog) {
  const filterSel = document.getElementById('chartFamilyFilter');
  if (!filterSel || !suiteLog || suiteLog.length === 0) return;

  const currentVal = filterSel.value;
  const uniqueFamilies = Array.from(new Set(suiteLog.map(r => r.family))).sort();

  filterSel.innerHTML = '<option value="ALL">All Topologies (Aggregate)</option>';
  uniqueFamilies.forEach(fam => {
    const opt = document.createElement('option');
    opt.value = fam;
    opt.innerText = fam;
    filterSel.appendChild(opt);
  });

  if (uniqueFamilies.includes(currentVal)) {
    filterSel.value = currentVal;
  }
}

export function renderScalingChart(dataSource = null, activeAlgos = null, budgets = null) {
  if (dataSource && activeAlgos && budgets) {
    chartCachedData = { dataSource, activeAlgos, budgets };
  }
  if (!chartCachedData) return;

  const canvas = document.getElementById('scalingChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const { dataSource: data, activeAlgos: algos, budgets: rawBudgets } = chartCachedData;
  const sortedBudgets = [...rawBudgets].map(Number).sort((a, b) => a - b);
  const selectedFamily = document.getElementById('chartFamilyFilter')?.value || 'ALL';

  // Calculate averages per budget and algorithm (filtered by topology)
  let globalMin = Infinity, globalMax = -Infinity;

  const datasets = algos.map((algo, idx) => {
    const color = CHART_COLOR_PALETTE[idx % CHART_COLOR_PALETTE.length];
    
    const dataPoints = sortedBudgets.map(b => {
      let avg = null;

      if (Array.isArray(data)) {
        // High-precision filter directly from suiteLog rows
        let total = 0, count = 0;
        for (let i = 0; i < data.length; i++) {
          const row = data[i];
          if (row.budget === b && (selectedFamily === 'ALL' || row.family === selectedFamily)) {
            const res = row.results ? row.results[algo.id] : null;
            if (res && res.edges !== undefined) {
              total += res.edges;
              count++;
            }
          }
        }
        avg = count > 0 ? (total / count) : null;
      } else if (data[b] && data[b][algo.id]) {
        // Fallback for budgetStats object
        const entry = data[b][algo.id];
        avg = entry.count > 0 ? (entry.totalEdges / entry.count) : null;
      }

      if (avg !== null) {
        if (avg < globalMin) globalMin = avg;
        if (avg > globalMax) globalMax = avg;
      }
      return currentXScaleMode === 'linear' ? { x: b, y: avg } : avg;
    });

    return {
      label: algo.name,
      data: dataPoints,
      borderColor: color,
      backgroundColor: color + '18',
      borderWidth: idx === 0 ? 3.0 : 2.0,
      tension: 0.35,
      pointRadius: 4,
      pointHoverRadius: 7,
      pointBackgroundColor: color,
      pointBorderColor: '#070709',
      pointBorderWidth: 1.5
    };
  });

  if (!isFinite(globalMin)) return;

  // Zoom Modes
  let yMin = null, yMax = null;
  const manualMin = parseFloat(document.getElementById('manualYMin').value);
  const manualMax = parseFloat(document.getElementById('manualYMax').value);

  if (!isNaN(manualMin) || !isNaN(manualMax)) {
    yMin = !isNaN(manualMin) ? manualMin : undefined;
    yMax = !isNaN(manualMax) ? manualMax : undefined;
  } else if (currentYScaleMode === 'tight') {
    const span = Math.max(0.5, globalMax - globalMin);
    yMin = Math.max(0, parseFloat((globalMin - span * 0.05).toFixed(1)));
    yMax = parseFloat((globalMax + span * 0.05).toFixed(1));
  } else if (currentYScaleMode === 'zero') {
    yMin = 0;
    yMax = Math.ceil(globalMax * 1.08);
  } else {
    const span = Math.max(1, globalMax - globalMin);
    yMin = Math.max(0, Math.floor(globalMin - span * 0.12));
    yMax = Math.ceil(globalMax + span * 0.12);
  }

  const xScaleConfig = currentXScaleMode === 'linear' ? {
    type: 'linear',
    grid: { color: 'rgba(255, 255, 255, 0.04)', drawBorder: false },
    ticks: {
      color: '#8a8a93',
      font: { family: "'JetBrains Mono', monospace", size: 11 },
      callback: (val) => val >= 1000 ? (val / 1000) + 'k' : val
    },
    title: { display: true, text: 'Compute Budget (Evaluations — Linear Spatial Scale)', color: '#54545d', font: { size: 11 } }
  } : {
    type: 'category',
    labels: sortedBudgets.map(b => `@${b.toLocaleString()} Evals`),
    grid: { color: 'rgba(255, 255, 255, 0.04)', drawBorder: false },
    ticks: { color: '#8a8a93', font: { family: "'JetBrains Mono', monospace", size: 11 } },
    title: { display: true, text: 'Compute Budget (Equidistant Tiers)', color: '#54545d', font: { size: 11 } }
  };

  if (chartInstance) chartInstance.destroy();

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 250 },
      interaction: { mode: 'nearest', intersect: false },
      plugins: {
        legend: {
          position: 'top', align: 'end',
          labels: { color: '#8a8a93', font: { size: 11, weight: 500 }, boxWidth: 12, boxHeight: 4, padding: 14 }
        },
        tooltip: {
          backgroundColor: 'rgba(10, 10, 14, 0.94)', titleColor: '#ffffff', bodyColor: '#e2e8f0',
          borderColor: 'rgba(255, 255, 255, 0.12)', borderWidth: 1, padding: 10,
          callbacks: {
            title: (items) => {
              const bVal = currentXScaleMode === 'linear' ? Number(items[0].parsed.x).toLocaleString() : sortedBudgets[items[0].dataIndex]?.toLocaleString();
              return `Budget: ${bVal} evals (${selectedFamily === 'ALL' ? 'All Topologies' : selectedFamily})`;
            },
            label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)} edges`
          }
        }
      },
      scales: {
        x: xScaleConfig,
        y: {
          min: yMin, max: yMax,
          grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
          ticks: { color: '#8a8a93', callback: (v) => v.toFixed(1) + ' e' },
          title: { display: true, text: selectedFamily === 'ALL' ? 'Average Final Edges' : `Average Final Edges (${selectedFamily})`, color: '#54545d', font: { size: 11 } }
        }
      }
    }
  });
}

export function setChartXScale(mode) {
  currentXScaleMode = mode;
  document.getElementById('btnScaleRegular').style.background = mode === 'regular' ? 'rgba(255,255,255,0.12)' : 'transparent';
  document.getElementById('btnScaleRegular').style.color = mode === 'regular' ? '#fff' : '#8a8a93';
  document.getElementById('btnScaleLinear').style.background = mode === 'linear' ? 'rgba(255,255,255,0.12)' : 'transparent';
  document.getElementById('btnScaleLinear').style.color = mode === 'linear' ? '#fff' : '#8a8a93';
  renderScalingChart();
}

export function setChartYMode(mode) {
  currentYScaleMode = mode;
  document.getElementById('manualYMin').value = '';
  document.getElementById('manualYMax').value = '';
  ['btnYAuto', 'btnYTight', 'btnYZero'].forEach(id => {
    document.getElementById(id).style.background = 'transparent';
    document.getElementById(id).style.color = '#8a8a93';
  });
  const activeBtn = mode === 'auto' ? 'btnYAuto' : mode === 'tight' ? 'btnYTight' : 'btnYZero';
  document.getElementById(activeBtn).style.background = 'rgba(255,255,255,0.12)';
  document.getElementById(activeBtn).style.color = '#fff';
  renderScalingChart();
}

export function applyManualYBounds() {
  currentYScaleMode = 'manual';
  ['btnYAuto', 'btnYTight', 'btnYZero'].forEach(id => {
    document.getElementById(id).style.background = 'transparent';
    document.getElementById(id).style.color = '#8a8a93';
  });
  renderScalingChart();
}