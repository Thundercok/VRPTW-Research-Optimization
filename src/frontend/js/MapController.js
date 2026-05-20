export class MapController {
    constructor(app) {
        this.app = app;
        this.map = null;
        this.ddqnMap = null;
        this.alnsMap = null;
        this.vehicleAnimations = [];
        this.ddqnVehicles = new Map();
        this.alnsVehicles = new Map();
    }

    init() {
        this.map = L.map('map-container', {
            zoomControl: false // Hide default ugly zoom controls
        }).setView([10.73193, 106.69934], 13);

        this.ddqnMap = this.map;
        this.alnsMap = this.map;

        // Add sleek bottom-right zoom control
        L.control.zoom({ position: 'bottomright' }).addTo(this.map);

        // PREMIUM CARTOGRAPHY: CartoDB Light (No street noise, high contrast)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            attribution: '&copy; CARTO'
        }).addTo(this.map);

        this.canvasRenderer = L.canvas({ padding: 0.5 });
        this.markerLayer = L.layerGroup().addTo(this.map);
        
        // Create layers
        this.ddqnRouteLayer = L.layerGroup();
        this.alnsRouteLayer = L.layerGroup();
        this.alnsDiffLayer = L.layerGroup();
        this.ddqnVehicleLayer = L.layerGroup();
        this.alnsVehicleLayer = L.layerGroup();

        // Default to showing DDQN layers
        this.ddqnRouteLayer.addTo(this.map);
        this.ddqnVehicleLayer.addTo(this.map);

        // Track active view
        this.currentView = 'ddqn';

        // Bind radio buttons change events
        const radios = document.querySelectorAll('input[name="map_view"]');
        radios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.switchView(e.target.value);
            });
        });
    }

    switchView(view) {
        this.currentView = view;
        if (view === 'ddqn') {
            this.map.addLayer(this.ddqnRouteLayer);
            this.map.addLayer(this.ddqnVehicleLayer);
            this.map.removeLayer(this.alnsRouteLayer);
            this.map.removeLayer(this.alnsVehicleLayer);
            this.map.removeLayer(this.alnsDiffLayer);
        } else {
            this.map.addLayer(this.alnsRouteLayer);
            this.map.addLayer(this.alnsVehicleLayer);
            this.map.addLayer(this.alnsDiffLayer);
            this.map.removeLayer(this.ddqnRouteLayer);
            this.map.removeLayer(this.ddqnVehicleLayer);
        }
    }

    invalidate() {
        if (this.map) {
            this.map.invalidateSize();
        }
    }

    clearRoutes() {
        this.stopVehicleAnimations();
        this.ddqnRouteLayer?.clearLayers();
        this.alnsRouteLayer?.clearLayers();
        this.alnsDiffLayer?.clearLayers();
        this.ddqnVehicleLayer?.clearLayers();
        this.alnsVehicleLayer?.clearLayers();
        this.ddqnVehicles.clear();
        this.alnsVehicles.clear();
    }

    renderMarkers() {
        this.markerLayer.clearLayers();
        const bounds = [];

        this.app.state.customers.forEach(c => {
            const p = [c.lat, c.lng];
            bounds.push(p);

            // PRO MARKERS: Inner dot with a semi-transparent stroke
            L.circleMarker(p, {
                renderer: this.canvasRenderer,
                radius: c.isDepot ? 6 : 4,
                color: c.isDepot ? '#2563eb' : '#64748b', // Blue border for depot, slate for stops
                weight: c.isDepot ? 3 : 2,
                fillColor: '#ffffff',
                fillOpacity: 1
            }).bindPopup(`
        <div style="font-family: Inter, sans-serif;">
          <strong style="font-size: 14px; color: #0f172a;">${c.name}</strong>
          <div style="color: #64748b; font-size: 12px; margin-top: 4px;">Demand: ${c.demand} units</div>
        </div>
      `).addTo(this.markerLayer);
        });

        if (bounds.length > 0) this.map.fitBounds(bounds, { padding: [40, 40] });
    }

    renderAlgoRoutes(algo, isDdqn, color, capacity) {
        const layerGroup = isDdqn ? this.ddqnRouteLayer : this.alnsRouteLayer;
        (algo.routes || []).forEach((route, routeIndex) => {
            if (!route.path || route.path.length < 2) return;
            const load = Number(route.load ?? 0);
            const cap = Number(capacity);
            const loadLine = Number.isFinite(load) && Number.isFinite(cap) && cap > 0
                ? `<br/>Load: ${load} / ${cap}`
                : '';

            const badge = this.buildLoadBadge(load, cap);
            const ratioText = Number.isFinite(badge.ratio) ? `${(badge.ratio * 100).toFixed(1)}%` : 'N/A';
            const popupContent = `
                <div class="route-popup">
                    <strong>Vehicle ${route.vehicle_id}</strong>
                    ${loadLine}
                    <br/>Distance: ${Number(route.distance_km || 0).toFixed(2)} km
                    <br/>Utilization: ${ratioText}
                    <br/><span class="route-load-pill ${badge.tone}">${badge.label}</span>
                </div>
            `;
            const routeColor = this.colorForRoute(routeIndex, route, color);
            L.polyline(route.path.map((p) => [p[0], p[1]]), {
                renderer: this.canvasRenderer,
                color: routeColor,
                weight: 4,
                opacity: 0.9
            }).bindPopup(popupContent).addTo(layerGroup);
        });
    }

    buildLoadBadge(load, cap) {
        if (!Number.isFinite(load) || !Number.isFinite(cap) || cap <= 0) {
            return { ratio: NaN, label: 'No load info', tone: 'neutral' };
        }
        const ratio = load / cap;
        if (ratio > 0.95) return { ratio, label: 'Critical load', tone: 'critical' };
        if (ratio >= 0.80) return { ratio, label: 'Near full', tone: 'near' };
        return { ratio, label: 'Safe load', tone: 'safe' };
    }

    colorForRoute(routeIndex, route, fallback) {
        const palette = [
            '#0ea5e9', // Sky blue
            '#2563eb', // Indigo
            '#10b981', // Emerald
            '#f59e0b', // Amber
            '#ec4899', // Pink
            '#8b5cf6', // Violet
            '#f43f5e', // Rose
            '#14b8a6', // Teal
        ];
        if (routeIndex < palette.length) return palette[routeIndex];
        const hue = (routeIndex * 137.508) % 360;
        return `hsl(${hue},72%,44%)`;
    }

    renderVehicleMarkers(algo, isDdqn, color) {
        // Compatibility wrapper for original App.js paintResult calls.
        // We now delegate initialization to initSimulation.
        const result = this.app.state.lastResult;
        if (result) {
            this.initSimulation(result);
        }
    }

    initSimulation(result) {
        this.ddqnVehicleLayer.clearLayers();
        this.alnsVehicleLayer.clearLayers();
        this.ddqnVehicles.clear();
        this.alnsVehicles.clear();

        if (result.ddqn && result.ddqn.routes) {
            result.ddqn.routes.forEach((route, idx) => {
                if (!route.path || route.path.length === 0) return;
                const color = this.colorForRoute(idx, route, '#10b981');
                const start = route.path[0];
                const marker = L.marker([start[0], start[1]], {
                    icon: this.buildVehicleIcon(color)
                });
                marker.bindPopup(`Vehicle #${route.vehicle_id}`);
                marker.addTo(this.ddqnVehicleLayer);
                this.ddqnVehicles.set(route.vehicle_id, marker);
            });
        }

        if (result.alns && result.alns.routes) {
            result.alns.routes.forEach((route, idx) => {
                if (!route.path || route.path.length === 0) return;
                const color = this.colorForRoute(idx, route, '#3b82f6');
                const start = route.path[0];
                const marker = L.marker([start[0], start[1]], {
                    icon: this.buildVehicleIcon(color)
                });
                marker.bindPopup(`Vehicle #${route.vehicle_id}`);
                marker.addTo(this.alnsVehicleLayer);
                this.alnsVehicles.set(route.vehicle_id, marker);
            });
        }
    }

    updateSimulation(t_sim, algoResult, isDdqn) {
        const vehicleMap = isDdqn ? this.ddqnVehicles : this.alnsVehicles;
        if (!algoResult || !algoResult.routes) return;

        algoResult.routes.forEach((route) => {
            const marker = vehicleMap.get(route.vehicle_id);
            if (!marker) return;

            const state = this.getVehicleStateAtTime(route, t_sim);
            marker.setLatLng([state.lat, state.lng]);
            marker.bindPopup(`
                <div style="font-family: Inter, sans-serif; min-width: 160px; padding: 4px 0;">
                    <div style="font-weight: 700; font-size: 13px; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 6px;">
                        🚚 Vehicle #${route.vehicle_id}
                    </div>
                    <div style="font-size: 11px; font-weight: 600; color: #3b82f6; text-transform: uppercase; letter-spacing: 0.05em;">
                        ${state.status}
                    </div>
                    <div style="font-size: 11px; color: #475569; margin-top: 2px; line-height: 1.4;">
                        ${state.detail}
                    </div>
                </div>
            `);
        });
    }

    getVehicleStateAtTime(route, t_sim) {
        if (!route.path || route.path.length === 0) {
            return { lat: 0, lng: 0, status: 'Completed', detail: 'No route path' };
        }
        if (!route.schedule || route.schedule.length === 0) {
            const start = route.path[0];
            return { lat: start[0], lng: start[1], status: 'Completed', detail: 'Parked at Depot (no schedule)' };
        }

        const path = route.path;
        const schedule = route.schedule;
        const numStops = route.stops ? route.stops.length : 0;
        
        let t_last = 0;
        let coord_last = path[0];

        // Loop through each stop in the schedule
        for (let i = 0; i < numStops; i++) {
            const step = schedule[i];
            const coord_curr = path[i + 1];
            if (!step || !coord_curr) continue;

            const t_travel_start = t_last;
            const t_arrival = step.arrival;
            const t_service_start = step.service_start;
            const t_departure = step.departure;

            if (t_sim >= t_travel_start && t_sim < t_arrival) {
                const dur = t_arrival - t_travel_start;
                const frac = dur > 0 ? (t_sim - t_travel_start) / dur : 1;
                const lat = coord_last[0] + frac * (coord_curr[0] - coord_last[0]);
                const lng = coord_last[1] + frac * (coord_curr[1] - coord_last[1]);
                return {
                    lat,
                    lng,
                    status: 'Traveling',
                    detail: `Traveling to "${step.name}". Arriving in ${Math.ceil(t_arrival - t_sim)}m.`
                };
            }

            if (t_sim >= t_arrival && t_sim < t_service_start) {
                return {
                    lat: coord_curr[0],
                    lng: coord_curr[1],
                    status: 'Waiting',
                    detail: `Waiting at "${step.name}" (window opens in ${Math.ceil(t_service_start - t_sim)}m).`
                };
            }

            if (t_sim >= t_service_start && t_sim < t_departure) {
                return {
                    lat: coord_curr[0],
                    lng: coord_curr[1],
                    status: 'Servicing',
                    detail: `Servicing "${step.name}". Remaining: ${Math.ceil(t_departure - t_sim)}m.`
                };
            }

            t_last = t_departure;
            coord_last = coord_curr;
        }

        // Return to depot step
        const stepDepot = schedule[numStops];
        const coord_depot = path[numStops + 1] || path[0];
        if (stepDepot && coord_depot) {
            const t_travel_start = t_last;
            const t_arrival = stepDepot.arrival;

            if (t_sim >= t_travel_start && t_sim < t_arrival) {
                const dur = t_arrival - t_travel_start;
                const frac = dur > 0 ? (t_sim - t_travel_start) / dur : 1;
                const lat = coord_last[0] + frac * (coord_depot[0] - coord_last[0]);
                const lng = coord_last[1] + frac * (coord_depot[1] - coord_last[1]);
                return {
                    lat,
                    lng,
                    status: 'Returning',
                    detail: `Returning to Depot. Arriving in ${Math.ceil(t_arrival - t_sim)}m.`
                };
            }
            t_last = t_arrival;
        }

        // Completed
        const endCoord = coord_depot || coord_last;
        return {
            lat: endCoord[0],
            lng: endCoord[1],
            status: 'Completed',
            detail: 'All tasks completed. Parked at Depot.'
        };
    }

    stopVehicleAnimations() {
        // Compatibility wrapper: do nothing as simulation handles ticks
    }

    buildDepotIcon() {
        return L.divIcon({
            className: 'map-marker-wrap',
            iconSize: [72, 84],
            iconAnchor: [36, 72],
            popupAnchor: [0, -42],
            html: `<div class="map-icon-3d depot" style="--icon-main:#0ea5e9;--icon-dark:#0c4a6e;--icon-shadow:rgba(14,165,233,0.36)"><span class="map-icon-glyph">🏭</span></div>`
        });
    }

    buildCustomerIcon(ready, due) {
        const urgency = (Number(due) || 1000) - (Number(ready) || 0);
        const isUrgent = urgency < 20;
        const mainColor = isUrgent ? '#ef4444' : '#7c3aed';
        const darkColor = isUrgent ? '#991b1b' : '#5b21b6';
        const shadowColor = isUrgent ? 'rgba(239,68,68,0.35)' : 'rgba(124,58,237,0.35)';
        const br = isUrgent ? '4px' : '50%';

        return L.divIcon({
            className: 'map-marker-wrap',
            iconSize: [28, 36],
            iconAnchor: [14, 33],
            popupAnchor: [0, -20],
            html: `
                <div class="map-icon-3d customer" style="--icon-main:${mainColor};--icon-dark:${darkColor};--icon-shadow:${shadowColor}; border-radius: ${br};">
                    <svg class="map-icon-avatar" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <ellipse class="avatar-hair-back" cx="12" cy="9" rx="6.4" ry="5.7"></ellipse>
                        <circle class="avatar-bun" cx="13.6" cy="4.7" r="2.25"></circle>
                        <path class="avatar-hair-front" d="M6.2 9.3c0-3.4 2.5-5.9 5.8-5.9 2.8 0 5.2 1.9 5.8 4.6-.8-.4-1.7-.7-2.8-.7-2.5 0-4.7 1.4-5.9 3.5l-2.9-1.5z"></path>
                        <circle class="avatar-face" cx="12" cy="10.3" r="4.3"></circle>
                        <path class="avatar-shirt" d="M5.1 20.1c.2-3.8 2.8-6.4 6.9-6.4s6.7 2.6 6.9 6.4H5.1z"></path>
                        <circle class="avatar-eye" cx="10.4" cy="10" r="0.5"></circle>
                        <circle class="avatar-eye" cx="13.6" cy="10" r="0.5"></circle>
                        <path class="avatar-mouth" d="M10.1 12.3c.5.4 1.1.6 1.9.6s1.4-.2 1.9-.6"></path>
                    </svg>
                </div>`
        });
    }

    buildVehicleIcon(color = '#0b8a65') {
        return L.divIcon({
            className: 'map-marker-wrap',
            iconSize: [56, 56],
            iconAnchor: [28, 28],
            popupAnchor: [0, -18],
            html: `<div class="map-icon-3d vehicle" style="--icon-main:${color};--icon-dark:#0f3d33;--icon-shadow:rgba(15,61,51,0.35)"><span class="map-icon-glyph">🚚</span></div>`
        });
    }

    segmentKey(a, b) {
        const ka = `${Number(a[0]).toFixed(5)},${Number(a[1]).toFixed(5)}`;
        const kb = `${Number(b[0]).toFixed(5)},${Number(b[1]).toFixed(5)}`;
        return ka < kb ? `${ka}|${kb}` : `${kb}|${ka}`;
    }

    collectSegmentSet(algo) {
        const set = new Set();
        (algo.routes || []).forEach((route) => {
            if (!route.path || route.path.length < 2) return;
            for (let i = 0; i < route.path.length - 1; i++) {
                set.add(this.segmentKey(route.path[i], route.path[i + 1]));
            }
        });
        return set;
    }

    drawDiffSegment(path, layerGroup, routeIndex) {
        L.polyline(path, {
            color: '#ff5a5f',
            weight: 10,
            opacity: 0.22,
            lineCap: 'round'
        }).addTo(layerGroup);

        L.polyline(path, {
            color: '#d7191c',
            weight: 5,
            opacity: 0.92,
            dashArray: '8 5',
            lineCap: 'round'
        }).bindPopup(`ALNS-only segment • Route ${routeIndex + 1}`).addTo(layerGroup);
    }

    renderAlnsOnlySegments(ddqn, alns) {
        const ddqnSegments = this.collectSegmentSet(ddqn);
        let highlightedSegments = 0;

        (alns.routes || []).forEach((route, routeIndex) => {
            if (!route.path || route.path.length < 2) return;

            let streak = [];
            for (let i = 0; i < route.path.length - 1; i++) {
                const a = route.path[i];
                const b = route.path[i + 1];
                const key = this.segmentKey(a, b);
                const isUnique = !ddqnSegments.has(key);

                if (isUnique) {
                    if (streak.length === 0) streak.push([a[0], a[1]]);
                    streak.push([b[0], b[1]]);
                    highlightedSegments += 1;
                    continue;
                }

                if (streak.length > 1) {
                    this.drawDiffSegment(streak, this.alnsDiffLayer, routeIndex);
                    streak = [];
                }
            }

            if (streak.length > 1) {
                this.drawDiffSegment(streak, this.alnsDiffLayer, routeIndex);
            }
        });

        if (highlightedSegments > 0) {
            this.app.setStatus(`Highlighted ${highlightedSegments} ALNS segments that do not appear in DDQN.`, 'ok');
        }

        return highlightedSegments;
    }

    updateVehicle(id, lat, lng, status) {
        if (!this.map) return;

        const color = status === 'danger' ? '#ef4444' : '#10b981';

        if (!this.ddqnVehicles.has(id)) {
            const m1 = L.circleMarker([lat, lng], { color, radius: 6, fillOpacity: 1 }).addTo(this.ddqnVehicleLayer);
            this.ddqnVehicles.set(id, m1);
        } else {
            this.ddqnVehicles.get(id).setLatLng([lat, lng]).setStyle({ color });
        }

        if (!this.alnsVehicles.has(id)) {
            const m2 = L.circleMarker([lat, lng], { color, radius: 6, fillOpacity: 1 }).addTo(this.alnsVehicleLayer);
            this.alnsVehicles.set(id, m2);
        } else {
            this.alnsVehicles.get(id).setLatLng([lat, lng]).setStyle({ color });
        }
    }
}