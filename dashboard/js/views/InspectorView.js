export class InspectorView {
    constructor(store) {
        this.store = store;

        // Lưu lại cái index đang chọn (Thay vì để global như cũ)
        this.localState = {
            selectedRouteIndex: 0
        };

        // DOM Elements của Tab 3
        this.elements = {
            metaGrid: document.getElementById('meta-grid'),
            routeSummary: document.getElementById('route-summary'),
            routeList: document.getElementById('route-list'),
            detailSummary: document.getElementById('detail-summary'),
            routeDetail: document.getElementById('route-detail'),
        };

        // Dặn class này: "Ê, khi nào Store có data mới thì chạy hàm render() nha!"
        this.store.subscribe((state) => {
            this.localState.selectedRouteIndex = 0; // Reset lại route đang chọn
            this.render(state);
        });
    }

    render(state) {
        if (!state.data) return;

        this.renderMeta(state.data);
        this.renderRouteList(state.data, state.activeKey);
        this.renderRouteDetail(state.data, state.activeKey);
    }

    // --- MẤY HÀM NÀY LÀ TỪ CODE CŨ CỦA BẠN ĐƯA SANG ---
    renderMeta(data) {
        const meta = data.meta ?? {};
        const rows = [
            ['Instance', meta.instance ?? 'Unknown'],
            ['Dataset', meta.dataset ?? 'Unknown'],
            ['Customers', this.formatNumber(meta.n_customers)],
            ['Capacity', this.formatNumber(meta.capacity)],
            ['Horizon', this.formatNumber(meta.horizon)],
        ];

        this.elements.metaGrid.innerHTML = rows
            .map(([label, value]) => `<div class="meta-row"><dt>${this.escapeHtml(label)}</dt><dd>${this.escapeHtml(String(value))}</dd></div>`)
            .join('');
    }

    renderRouteList(data, activeKey) {
        const solution = data[activeKey];
        const routes = solution?.routes ?? [];
        const nodeLookup = this.buildNodeLookup(data.nodes);
        const routeStats = routes.map(route => this.summarizeRoute(route, nodeLookup, data.meta.capacity));

        this.elements.routeSummary.textContent = `${routeStats.length} routes`;

        if (!routeStats.length) {
            this.elements.routeList.className = 'route-list empty';
            this.elements.routeList.textContent = 'No routes available.';
            return;
        }

        const cards = routeStats.map((route, index) => {
            const card = document.createElement('article');
            card.className = `route-card${index === this.localState.selectedRouteIndex ? ' active' : ''}`;

            const latenessText = route.tightStops > 0 ? `${route.tightStops} tight TW stops` : 'No tight TW stops';

            card.innerHTML = `
        <div class="route-header">
          <h3 class="route-title">Vehicle ${this.escapeHtml(String(route.vehicleId))}</h3>
          <span class="pill">${this.escapeHtml(latenessText)}</span>
        </div>
        <div class="route-kpis">
          <div class="route-kpi"><p class="route-kpi-label">Stops</p><p class="route-kpi-value">${route.stopCount}</p></div>
          <div class="route-kpi"><p class="route-kpi-label">Demand</p><p class="route-kpi-value">${this.formatNumber(route.totalDemand, 1)}</p></div>
          <div class="route-kpi"><p class="route-kpi-label">Load</p><p class="route-kpi-value">${this.formatNumber(route.loadPct, 1)}%</p></div>
        </div>
        <p class="route-path">${this.escapeHtml(route.preview)}</p>
      `;

            card.addEventListener('click', () => {
                this.localState.selectedRouteIndex = index;
                // Re-render khi bấm chọn xe khác
                this.renderRouteList(data, activeKey);
                this.renderRouteDetail(data, activeKey);
            });

            return card;
        });

        this.elements.routeList.className = 'route-list';
        this.elements.routeList.replaceChildren(...cards);
    }

    renderRouteDetail(data, activeKey) {
        const solution = data[activeKey];
        const routes = solution?.routes ?? [];
        const route = routes[this.localState.selectedRouteIndex];

        if (!route) {
            this.elements.detailSummary.textContent = 'No selection';
            this.elements.routeDetail.innerHTML = 'Select a route to inspect its stops.';
            return;
        }

        const nodeLookup = this.buildNodeLookup(data.nodes);
        const routeSummary = this.summarizeRoute(route, nodeLookup, data.meta.capacity);

        this.elements.detailSummary.textContent = `Vehicle ${routeSummary.vehicleId}`;

        // Vẽ chi tiết bảng các node xe đi qua
        const stopRows = (route.nodes ?? []).map((nodeId, index) => {
            const node = nodeLookup.get(nodeId);
            if (!node) return `<tr><td colspan="5">Node missing</td></tr>`;
            const twWidth = Number(node.due ?? 0) - Number(node.ready ?? 0);
            const toneClass = twWidth < 30 ? 'text-warn' : 'text-good';

            return `
        <tr>
          <td class="stop-seq">${index + 1}</td>
          <td><strong>${node.id}</strong><div class="stop-meta">x=${node.x}, y=${node.y}</div></td>
          <td>${this.formatNumber(node.demand, 1)}</td>
          <td><span class="${toneClass}">[${node.ready}, ${node.due}]</span><div class="stop-meta">width ${twWidth}</div></td>
          <td>${node.svc}</td>
        </tr>`;
        }).join('');

        this.elements.routeDetail.innerHTML = `
      <table class="stop-table">
        <thead><tr><th>Seq</th><th>Stop</th><th>Demand</th><th>Time window</th><th>Service</th></tr></thead>
        <tbody>${stopRows}</tbody>
      </table>
    `;
    }

    // --- CÁC HÀM TIỆN ÍCH ---
    buildNodeLookup(nodes) { return new Map((nodes ?? []).map(n => [n.id, n])); }

    summarizeRoute(route, nodeLookup, capacity) {
        const nodes = Array.isArray(route.nodes) ? route.nodes : [];
        const stats = nodes.reduce((acc, nodeId) => {
            const node = nodeLookup.get(nodeId);
            if (node) {
                acc.totalDemand += Number(node.demand ?? 0);
                if ((Number(node.due ?? 0) - Number(node.ready ?? 0)) < 30) acc.tightStops += 1;
            }
            return acc;
        }, { totalDemand: 0, tightStops: 0 });

        const cap = Number(capacity ?? 0);
        const previewNodes = nodes.slice(0, 5).join(' -> ');
        return {
            vehicleId: route.id ?? '?', stopCount: nodes.length, totalDemand: stats.totalDemand, tightStops: stats.tightStops,
            loadPct: cap > 0 ? (stats.totalDemand / cap) * 100 : 0, preview: `0 -> ${previewNodes} -> ... -> 0`,
        };
    }

    formatNumber(val, d = 0) { return Number.isFinite(Number(val)) ? Number(val).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }) : 'N/A'; }
    escapeHtml(val) { return String(val).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }
}