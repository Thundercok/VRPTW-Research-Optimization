'use strict';

const SAMPLE_DATA_URL = '../logs/results-v8/nexus_demo.json';

const state = {
  data: null,
  sourceLabel: 'No file loaded yet.',
  activeKey: null,
  selectedRouteIndex: 0,
};

const elements = {
  fileInput: document.getElementById('file-input'),
  loadSample: document.getElementById('load-sample'),
  dataStatus: document.getElementById('data-status'),
  algoSwitcher: document.getElementById('algo-switcher'),
  metaGrid: document.getElementById('meta-grid'),
  schemaList: document.getElementById('schema-list'),
  overviewGrid: document.getElementById('overview-grid'),
  learningNotes: document.getElementById('learning-notes'),
  routeSummary: document.getElementById('route-summary'),
  routeList: document.getElementById('route-list'),
  detailSummary: document.getElementById('detail-summary'),
  routeDetail: document.getElementById('route-detail'),
};

const solutionRegistry = [
  { key: 'rl_alns', label: 'DDQN-ALNS' },
  { key: 'alns', label: 'ALNS' },
];

const schemaKeys = [
  'meta',
  'nodes',
  'alns',
  'rl_alns',
  'summary',
  'transfer',
  'op_matrix',
];

elements.fileInput.addEventListener('change', handleFileSelection);
elements.loadSample.addEventListener('click', loadSampleData);

render();

function handleFileSelection(event) {
  const [file] = event.target.files ?? [];
  if (!file) {
    return;
  }

  readFileAsText(file)
    .then(text => {
      const parsed = JSON.parse(text);
      loadData(parsed, `Loaded from ${file.name}`);
    })
    .catch(error => {
      renderError(error instanceof Error ? error.message : 'Could not load the selected file.');
    })
    .finally(() => {
      elements.fileInput.value = '';
    });
}

async function loadSampleData() {
  try {
    const response = await fetch(SAMPLE_DATA_URL);
    if (!response.ok) {
      throw new Error(`Sample request failed with status ${response.status}.`);
    }
    const parsed = await response.json();
    loadData(parsed, `Loaded sample data from ${SAMPLE_DATA_URL}`);
  } catch (error) {
    renderError(
      error instanceof Error
        ? `${error.message} If you opened the HTML directly from disk, sample fetch may be blocked.`
        : 'Could not fetch sample data.'
    );
  }
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(new Error('The file could not be read.'));
    reader.readAsText(file);
  });
}

function loadData(parsed, sourceLabel) {
  validateData(parsed);

  state.data = parsed;
  state.sourceLabel = sourceLabel;
  state.activeKey = pickDefaultSolution(parsed);
  state.selectedRouteIndex = 0;

  render();
}

function validateData(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('The JSON root must be an object.');
  }

  if (!Array.isArray(data.nodes) || data.nodes.length < 2) {
    throw new Error('Expected a nodes array with at least depot + 1 customer.');
  }

  if (!data.alns && !data.rl_alns) {
    throw new Error('Expected at least one solution block: alns or rl_alns.');
  }
}

function pickDefaultSolution(data) {
  const firstAvailable = solutionRegistry.find(item => Boolean(data[item.key]));
  return firstAvailable ? firstAvailable.key : null;
}

function getActiveSolution() {
  if (!state.data || !state.activeKey) {
    return null;
  }
  return state.data[state.activeKey] ?? null;
}

function render() {
  renderStatus();
  renderSolutionSwitcher();
  renderMeta();
  renderSchemaChecklist();
  renderOverview();
  renderLearningNotes();
  renderRouteList();
  renderRouteDetail();
}

function renderStatus() {
  if (!state.data) {
    elements.dataStatus.className = 'status';
    elements.dataStatus.textContent = state.sourceLabel;
    return;
  }

  const meta = state.data.meta ?? {};
  const activeSolution = getActiveSolution();
  const routeCount = activeSolution?.routes?.length ?? 0;
  elements.dataStatus.className = 'status success';
  elements.dataStatus.textContent =
    `${state.sourceLabel}. Instance ${meta.instance ?? 'unknown'} contains ${meta.n_customers ?? 'unknown'} customers and ${routeCount} routes in the active solution.`;
}

function renderError(message) {
  elements.dataStatus.className = 'status error';
  elements.dataStatus.textContent = message;
}

function renderSolutionSwitcher() {
  if (!state.data) {
    elements.algoSwitcher.innerHTML = '';
    return;
  }

  const buttons = solutionRegistry
    .filter(item => state.data[item.key])
    .map(item => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `toggle-button${state.activeKey === item.key ? ' active' : ''}`;
      button.textContent = item.label;
      button.addEventListener('click', () => {
        state.activeKey = item.key;
        state.selectedRouteIndex = 0;
        render();
      });
      return button;
    });

  elements.algoSwitcher.replaceChildren(...buttons);
}

function renderMeta() {
  if (!state.data) {
    elements.metaGrid.innerHTML = '';
    return;
  }

  const meta = state.data.meta ?? {};
  const rows = [
    ['Instance', meta.instance ?? 'Unknown'],
    ['Dataset', meta.dataset ?? 'Unknown'],
    ['Customers', formatNumber(meta.n_customers)],
    ['Capacity', formatNumber(meta.capacity)],
    ['Horizon', formatNumber(meta.horizon)],
    ['Version', meta.version ?? 'Unknown'],
  ];

  elements.metaGrid.innerHTML = rows
    .map(([label, value]) => {
      return `<div class="meta-row"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(String(value))}</dd></div>`;
    })
    .join('');
}

function renderSchemaChecklist() {
  if (!state.data) {
    elements.schemaList.innerHTML = '';
    return;
  }

  elements.schemaList.innerHTML = schemaKeys
    .map(key => {
      const present = Boolean(state.data[key]);
      return `
        <li class="schema-item">
          <strong>${escapeHtml(key)}</strong>
          <span class="badge ${present ? 'present' : 'missing'}">${present ? 'present' : 'missing'}</span>
        </li>`;
    })
    .join('');
}

function renderOverview() {
  if (!state.data) {
    elements.overviewGrid.innerHTML = '';
    return;
  }

  const activeSolution = getActiveSolution();
  if (!activeSolution) {
    elements.overviewGrid.innerHTML = '';
    return;
  }

  const metrics = buildOverviewMetrics(state.data, activeSolution);

  elements.overviewGrid.innerHTML = metrics
    .map(metric => {
      return `
        <article class="metric-card">
          <p class="metric-label">${escapeHtml(metric.label)}</p>
          <p class="metric-value ${metric.toneClass ?? ''}">${escapeHtml(metric.value)}</p>
          <p class="metric-subtext">${escapeHtml(metric.subtext)}</p>
        </article>`;
    })
    .join('');
}

function buildOverviewMetrics(data, solution) {
  const nodeLookup = buildNodeLookup(data.nodes);
  const routeStats = (solution.routes ?? []).map(route => summarizeRoute(route, nodeLookup));
  const totalDemand = routeStats.reduce((sum, route) => sum + route.totalDemand, 0);
  const totalStops = routeStats.reduce((sum, route) => sum + route.stopCount, 0);
  const avgStops = routeStats.length ? totalStops / routeStats.length : 0;
  const maxLoadPct = routeStats.length ? Math.max(...routeStats.map(route => route.loadPct)) : 0;

  return [
    {
      label: 'Vehicles',
      value: formatNumber(solution.nv ?? routeStats.length),
      subtext: 'How many vehicles the selected solution uses.',
    },
    {
      label: 'Total distance',
      value: formatNumber(solution.td),
      subtext: 'Distance is one of the main objective values in this prototype.',
    },
    {
      label: 'Gap vs BKS',
      value: formatSignedPercent(solution.gap_pct),
      toneClass: solution.gap_pct <= 0 ? 'text-good' : 'text-warn',
      subtext: 'Research-oriented metric that compares this solution with the benchmark reference.',
    },
    {
      label: 'Avg stops / route',
      value: formatNumber(avgStops, 1),
      subtext: `Computed from ${formatNumber(totalStops)} assigned customers across the active routes.`,
    },
    {
      label: 'Total assigned demand',
      value: formatNumber(totalDemand, 1),
      subtext: 'Useful for checking whether route demand roughly matches the customer set.',
    },
    {
      label: 'Peak load ratio',
      value: `${formatNumber(maxLoadPct, 1)}%`,
      toneClass: maxLoadPct >= 90 ? 'text-warn' : 'text-good',
      subtext: 'Highest capacity utilization among the routes in the active solution.',
    },
  ];
}

function renderLearningNotes() {
  if (!state.data) {
    elements.learningNotes.innerHTML = '';
    return;
  }

  const activeSolution = getActiveSolution();
  const notes = buildLearningNotes(state.data, activeSolution);

  elements.learningNotes.innerHTML = notes
    .map(note => `<div class="note">${escapeHtml(note)}</div>`)
    .join('');
}

function buildLearningNotes(data, solution) {
  const meta = data.meta ?? {};
  const routeCount = solution?.routes?.length ?? 0;
  const hasSummary = Array.isArray(data.summary) && data.summary.length > 0;
  const hasTransfer = Array.isArray(data.transfer) && data.transfer.length > 0;

  return [
    `This prototype reads a single JSON object, stores it in one global state object, then re-renders the screen when the active solution changes.`,
    `The current active solution is ${solutionLabel(state.activeKey)} with ${routeCount} routes for instance ${meta.instance ?? 'unknown'}.`,
    `Keys like summary and transfer are still present in the data contract (${hasSummary ? 'yes' : 'no'} summary, ${hasTransfer ? 'yes' : 'no'} transfer), but we are not visualizing them yet because this rebuild is starting from the operational core.`,
  ];
}

function renderRouteList() {
  if (!state.data) {
    elements.routeSummary.textContent = 'No routes';
    elements.routeList.className = 'route-list empty';
    elements.routeList.textContent = 'Load data to inspect routes.';
    return;
  }

  const solution = getActiveSolution();
  const routes = solution?.routes ?? [];
  const nodeLookup = buildNodeLookup(state.data.nodes);
  const routeStats = routes.map(route => summarizeRoute(route, nodeLookup));

  elements.routeSummary.textContent = `${routeStats.length} routes`;

  if (!routeStats.length) {
    elements.routeList.className = 'route-list empty';
    elements.routeList.textContent = 'This solution does not include route details.';
    return;
  }

  const cards = routeStats.map((route, index) => {
    const card = document.createElement('article');
    card.className = `route-card${index === state.selectedRouteIndex ? ' active' : ''}`;

    const latenessText = route.tightStops > 0
      ? `${route.tightStops} tight TW stops`
      : 'No tight TW stops';

    card.innerHTML = `
      <div class="route-header">
        <h3 class="route-title">Vehicle ${escapeHtml(String(route.vehicleId))}</h3>
        <span class="pill">${escapeHtml(latenessText)}</span>
      </div>
      <div class="route-kpis">
        <div class="route-kpi">
          <p class="route-kpi-label">Stops</p>
          <p class="route-kpi-value">${escapeHtml(String(route.stopCount))}</p>
        </div>
        <div class="route-kpi">
          <p class="route-kpi-label">Demand</p>
          <p class="route-kpi-value">${escapeHtml(formatNumber(route.totalDemand, 1))}</p>
        </div>
        <div class="route-kpi">
          <p class="route-kpi-label">Load</p>
          <p class="route-kpi-value">${escapeHtml(formatNumber(route.loadPct, 1))}%</p>
        </div>
      </div>
      <p class="route-path">${escapeHtml(route.preview)}</p>
    `;

    card.addEventListener('click', () => {
      state.selectedRouteIndex = index;
      renderRouteList();
    });

    return card;
  });

  elements.routeList.className = 'route-list';
  elements.routeList.replaceChildren(...cards);
}

function renderRouteDetail() {
  if (!state.data) {
    elements.detailSummary.textContent = 'No selection';
    elements.routeDetail.className = 'route-detail empty';
    elements.routeDetail.textContent = 'Select a route to inspect its stops.';
    return;
  }

  const solution = getActiveSolution();
  const routes = solution?.routes ?? [];
  const route = routes[state.selectedRouteIndex];

  if (!route) {
    elements.detailSummary.textContent = 'No selection';
    elements.routeDetail.className = 'route-detail empty';
    elements.routeDetail.textContent = 'This solution has no route details to inspect.';
    return;
  }

  const nodeLookup = buildNodeLookup(state.data.nodes);
  const routeSummary = summarizeRoute(route, nodeLookup);
  const detail = buildRouteDetail(route, nodeLookup);

  elements.detailSummary.textContent = `Vehicle ${routeSummary.vehicleId}`;
  elements.routeDetail.className = 'route-detail';
  elements.routeDetail.innerHTML = `
    <div class="detail-grid">
      <div class="detail-card">
        <p class="detail-card-label">Distance</p>
        <p class="detail-card-value">${escapeHtml(formatNumber(route.dist, 1))}</p>
      </div>
      <div class="detail-card">
        <p class="detail-card-label">Assigned demand</p>
        <p class="detail-card-value">${escapeHtml(formatNumber(routeSummary.totalDemand, 1))}</p>
      </div>
      <div class="detail-card">
        <p class="detail-card-label">Capacity usage</p>
        <p class="detail-card-value">${escapeHtml(formatNumber(routeSummary.loadPct, 1))}%</p>
      </div>
      <div class="detail-card">
        <p class="detail-card-label">Tight TW stops</p>
        <p class="detail-card-value">${escapeHtml(String(routeSummary.tightStops))}</p>
      </div>
    </div>
    <table class="stop-table">
      <thead>
        <tr>
          <th>Seq</th>
          <th>Stop</th>
          <th>Demand</th>
          <th>Time window</th>
          <th>Service</th>
        </tr>
      </thead>
      <tbody>
        ${detail.stopRows}
      </tbody>
    </table>
  `;
}

function buildRouteDetail(route, nodeLookup) {
  const stopRows = (route.nodes ?? [])
    .map((nodeId, index) => {
      const node = nodeLookup.get(nodeId);
      if (!node) {
        return `
          <tr>
            <td class="stop-seq">${index + 1}</td>
            <td colspan="4">Node ${escapeHtml(String(nodeId))} was referenced by the route but not found in nodes.</td>
          </tr>`;
      }

      const twWidth = Number(node.due ?? 0) - Number(node.ready ?? 0);
      const toneClass = twWidth < 30 ? 'text-warn' : 'text-good';

      return `
        <tr>
          <td class="stop-seq">${index + 1}</td>
          <td>
            <strong>${escapeHtml(String(node.id))}</strong>
            <div class="stop-meta">x=${escapeHtml(formatNumber(node.x, 1))}, y=${escapeHtml(formatNumber(node.y, 1))}</div>
          </td>
          <td>${escapeHtml(formatNumber(node.demand, 1))}</td>
          <td>
            <span class="${toneClass}">[${escapeHtml(formatNumber(node.ready, 1))}, ${escapeHtml(formatNumber(node.due, 1))}]</span>
            <div class="stop-meta">width ${escapeHtml(formatNumber(twWidth, 1))}</div>
          </td>
          <td>${escapeHtml(formatNumber(node.svc, 1))}</td>
        </tr>`;
    })
    .join('');

  return { stopRows };
}

function summarizeRoute(route, nodeLookup) {
  const nodes = Array.isArray(route.nodes) ? route.nodes : [];
  const stats = nodes.reduce(
    (acc, nodeId) => {
      const node = nodeLookup.get(nodeId);
      if (!node) {
        return acc;
      }

      acc.totalDemand += Number(node.demand ?? 0);
      if ((Number(node.due ?? 0) - Number(node.ready ?? 0)) < 30) {
        acc.tightStops += 1;
      }
      return acc;
    },
    { totalDemand: 0, tightStops: 0 }
  );

  const capacity = Number(state.data?.meta?.capacity ?? 0);
  const previewNodes = nodes.slice(0, 7).join(' -> ');
  const suffix = nodes.length > 7 ? ' -> ...' : '';

  return {
    vehicleId: route.id ?? '?',
    stopCount: nodes.length,
    totalDemand: stats.totalDemand,
    tightStops: stats.tightStops,
    loadPct: capacity > 0 ? (stats.totalDemand / capacity) * 100 : 0,
    preview: `0 -> ${previewNodes}${suffix}${nodes.length ? ' -> 0' : '0'}`,
  };
}

function buildNodeLookup(nodes) {
  return new Map((nodes ?? []).map(node => [node.id, node]));
}

function solutionLabel(key) {
  return solutionRegistry.find(item => item.key === key)?.label ?? key ?? 'Unknown';
}

function formatNumber(value, fractionDigits = 0) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return 'N/A';
  }
  return numericValue.toLocaleString(undefined, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

function formatSignedPercent(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return 'N/A';
  }
  const prefix = numericValue > 0 ? '+' : '';
  return `${prefix}${numericValue.toFixed(2)}%`;
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}
