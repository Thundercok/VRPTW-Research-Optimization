export class MapController {
    constructor(app) {
        this.app = app;
        this.map = null;
        this.ddqnMap = null;
        this.alnsMap = null;
        this.vehicleAnimations = [];
        this.ddqnVehicles = new Map();
        this.alnsVehicles = new Map();
        this.roadRoutes = new Map();
        this.routeLayers = {};
        this.vehicleLayers = {};
        this.vehiclesMap = {};
    }

    init() {
        this.map = L.map('map-container', {
            zoomControl: false
        }).setView([10.73193, 106.69934], 13);

        this.ddqnMap = this.map;
        this.alnsMap = this.map;

        L.control.zoom({ position: 'bottomright' }).addTo(this.map);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            attribution: '&copy; CARTO'
        }).addTo(this.map);

        this.canvasRenderer = L.canvas({ padding: 0.5 });
        this.markerLayer = L.layerGroup().addTo(this.map);

        // Keep legacy layers defined for backwards compatibility
        this.ddqnRouteLayer = L.layerGroup();
        this.alnsRouteLayer = L.layerGroup();
        this.alnsDiffLayer = L.layerGroup();
        this.ddqnVehicleLayer = L.layerGroup();
        this.alnsVehicleLayer = L.layerGroup();

        // Switch listeners are dynamically updated in App.js when solver runs, 
        // but we setup standard ones here as a fallback.
        this.currentView = 'ddqn';
    }

    getRouteLayer(algoName) {
        if (!this.routeLayers) this.routeLayers = {};
        if (!this.routeLayers[algoName]) {
            this.routeLayers[algoName] = L.layerGroup();
        }
        return this.routeLayers[algoName];
    }

    getVehicleLayer(algoName) {
        if (!this.vehicleLayers) this.vehicleLayers = {};
        if (!this.vehicleLayers[algoName]) {
            this.vehicleLayers[algoName] = L.layerGroup();
        }
        return this.vehicleLayers[algoName];
    }

    getVehiclesMap(algoName) {
        if (!this.vehiclesMap) this.vehiclesMap = {};
        if (!this.vehiclesMap[algoName]) {
            this.vehiclesMap[algoName] = new Map();
        }
        return this.vehiclesMap[algoName];
    }

    switchView(view) {
        this.currentView = view;
        
        // Remove all route and vehicle layers
        if (this.routeLayers) {
            for (const key in this.routeLayers) {
                this.map.removeLayer(this.routeLayers[key]);
            }
        }
        if (this.vehicleLayers) {
            for (const key in this.vehicleLayers) {
                this.map.removeLayer(this.vehicleLayers[key]);
            }
        }
        
        this.map.removeLayer(this.ddqnRouteLayer);
        this.map.removeLayer(this.ddqnVehicleLayer);
        this.map.removeLayer(this.alnsRouteLayer);
        this.map.removeLayer(this.alnsVehicleLayer);
        this.map.removeLayer(this.alnsDiffLayer);

        // Add active layers
        const routeLayer = this.getRouteLayer(view);
        const vehicleLayer = this.getVehicleLayer(view);
        routeLayer.addTo(this.map);
        vehicleLayer.addTo(this.map);

        if (view === 'alns' && this.alnsDiffLayer) {
            this.map.addLayer(this.alnsDiffLayer);
        }

        if (this.app.simulationController) {
            this.app.simulationController.updateFrame();
        }
    }

    invalidate() {
        if (this.map) this.map.invalidateSize();
    }

    clearRoutes() {
        this.stopVehicleAnimations();
        if (this.routeLayers) {
            for (const key in this.routeLayers) {
                this.routeLayers[key].clearLayers();
            }
        }
        if (this.vehicleLayers) {
            for (const key in this.vehicleLayers) {
                this.vehicleLayers[key].clearLayers();
            }
        }
        this.alnsDiffLayer?.clearLayers();
        this.vehiclesMap = {};
        
        this.ddqnRouteLayer?.clearLayers();
        this.alnsRouteLayer?.clearLayers();
        this.ddqnVehicleLayer?.clearLayers();
        this.alnsVehicleLayer?.clearLayers();
        this.ddqnVehicles.clear();
        this.alnsVehicles.clear();
        
        this.roadRoutes.clear();
    }

    renderMarkers() {
        this.markerLayer.clearLayers();
        const bounds = [];
        this.app.state.customers.forEach(c => {
            const p = [c.lat, c.lng];
            bounds.push(p);
            L.circleMarker(p, {
                renderer: this.canvasRenderer,
                radius: c.isDepot ? 6 : 4,
                color: c.isDepot ? '#2563eb' : '#64748b',
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

    // ── Route rendering (straight-line fallback, replaced by OSRM when ready) ──

    renderAlgoRoutes(algo, algoNameOrIsDdqn, color, capacity) {
        const algoName = (typeof algoNameOrIsDdqn === 'boolean')
            ? (algoNameOrIsDdqn ? 'ddqn' : 'alns')
            : algoNameOrIsDdqn;
        const layerGroup = this.getRouteLayer(algoName);
        (algo.routes || []).forEach((route, routeIndex) => {
            if (!route.path || route.path.length < 2) return;
            const popupContent = this._buildRoutePopup(route, capacity, routeIndex);
            const routeColor = this.colorForRoute(routeIndex, route, color);
            L.polyline(route.path.map((p) => [p[0], p[1]]), {
                renderer: this.canvasRenderer,
                color: routeColor,
                weight: 4,
                opacity: 0.9
            }).bindPopup(popupContent).addTo(layerGroup);
        });
    }

    _buildRoutePopup(route, capacity, routeIndex) {
        const fleetVehicle = this.app.state.fleet?.[route.vehicle_id];
        const driverName = fleetVehicle ? fleetVehicle.driver : `Vehicle ${route.vehicle_id}`;
        const vehCap = fleetVehicle ? fleetVehicle.capacity : capacity;
        const load = Number(route.load ?? 0);
        const cap = Number(vehCap);
        const loadLine = Number.isFinite(load) && Number.isFinite(cap) && cap > 0
            ? `<br/>Load: ${load} / ${cap}` : '';
        const badge = this.buildLoadBadge(load, cap);
        const ratioText = Number.isFinite(badge.ratio) ? `${(badge.ratio * 100).toFixed(1)}%` : 'N/A';
        return `
            <div class="route-popup">
                <strong>${driverName}</strong>
                ${loadLine}
                <br/>Distance: ${Number(route.distance_km || 0).toFixed(2)} km
                <br/>Utilization: ${ratioText}
                <br/><span class="route-load-pill ${badge.tone}">${badge.label}</span>
            </div>
        `;
    }

    // ── OSRM road geometry fetching ──────────────────────────────────────

    async fetchRoadGeometries(result) {
        this.roadRoutes.clear();
        const jobs = [];
        for (const prefix in result) {
            const algo = result[prefix];
            if (!algo || !algo.routes) continue;
            for (const route of algo.routes) {
                if (!route.path || route.path.length < 2) continue;
                jobs.push({ route, prefix });
            }
        }
        // Fetch sequentially with small delays to be polite to OSRM
        for (const job of jobs) {
            await this._fetchSingleRoute(job.route, job.prefix);
            await new Promise(r => setTimeout(r, 80));
        }
        // Re-render polylines with road geometry
        this._rerenderWithRoads(result);
    }

    async _fetchSingleRoute(route, prefix) {
        const waypoints = route.path; // [[lat,lng], ...]
        if (waypoints.length < 2) return;
        const coords = waypoints.map(w => `${w[1]},${w[0]}`).join(';');
        const url = `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`;
        try {
            const resp = await fetch(url);
            if (!resp.ok) return;
            const data = await resp.json();
            if (data.code !== 'Ok' || !data.routes?.length) return;

            const geo = data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]); // [lng,lat]→[lat,lng]
            // Cumulative distances along the geometry
            const cumDist = [0];
            for (let i = 1; i < geo.length; i++) {
                cumDist.push(cumDist[i - 1] + this._approxDist(geo[i - 1], geo[i]));
            }
            // Find geometry indices closest to each original waypoint
            const legBounds = [0];
            for (let wi = 1; wi < waypoints.length; wi++) {
                let bestIdx = legBounds[legBounds.length - 1];
                let bestD = Infinity;
                for (let gi = bestIdx; gi < geo.length; gi++) {
                    const d = this._approxDist(geo[gi], waypoints[wi]);
                    if (d < bestD) { bestD = d; bestIdx = gi; }
                    if (d > bestD * 4 && gi > bestIdx + 10) break;
                }
                legBounds.push(bestIdx);
            }
            const key = `${prefix}_${route.vehicle_id}`;
            this.roadRoutes.set(key, { geometry: geo, cumDist, legBounds });
        } catch (e) {
            console.warn(`OSRM failed for ${prefix} v${route.vehicle_id}:`, e);
        }
    }

    _rerenderWithRoads(result) {
        const cap = Number(this.app.state.lastRunFleet?.capacity ?? this.app.state.capacity);
        
        const colors = {
            ddqn: '#0b8a65',
            alns: '#2563eb',
            ortools: '#e11d48',
            hybrid_fixed: '#d97706',
            hybrid_ddqn: '#7c3aed',
            hybrid_ddqn_transfer_rc1: '#0284c7',
            hybrid_ddqn_transfer_dr: '#4f46e5',
            hybrid: '#0b8a65'
        };

        const rerender = (algo, algoName, baseColor, capacity) => {
            if (!algo?.routes) return;
            const layerGroup = this.getRouteLayer(algoName);
            layerGroup.clearLayers();
            const prefix = algoName;
            algo.routes.forEach((route, routeIndex) => {
                if (!route.path || route.path.length < 2) return;
                const popup = this._buildRoutePopup(route, capacity, routeIndex);
                const color = this.colorForRoute(routeIndex, route, baseColor || '#6b7280');
                const key = `${prefix}_${route.vehicle_id}`;
                const road = this.roadRoutes.get(key);
                const coords = road ? road.geometry : route.path.map(p => [p[0], p[1]]);
                L.polyline(coords, {
                    color, weight: 4, opacity: 0.9, lineJoin: 'round', lineCap: 'round'
                }).bindPopup(popup).addTo(layerGroup);
            });
        };

        for (const algoName in result) {
            const baseColor = colors[algoName] || '#6b7280';
            rerender(result[algoName], algoName, baseColor, cap);
        }

        if (result.ddqn && result.alns) {
            this.alnsDiffLayer.clearLayers();
            this.renderAlnsOnlySegments(result.ddqn, result.alns);
        }
    }

    _approxDist(a, b) {
        const R = 6371;
        const lat1 = a[0] * Math.PI / 180, lat2 = b[0] * Math.PI / 180;
        const dLat = lat2 - lat1, dLng = (b[1] - a[1]) * Math.PI / 180;
        const x = dLng * Math.cos((lat1 + lat2) / 2);
        return Math.sqrt(x * x + dLat * dLat) * R;
    }

    // ── Interpolate position along road geometry for a given leg + fraction ──

    _interpolateRoad(roadData, legIndex, frac) {
        if (!roadData || legIndex + 1 >= roadData.legBounds.length) return null;
        const si = roadData.legBounds[legIndex];
        const ei = roadData.legBounds[legIndex + 1];
        if (si >= ei) return null;
        const sd = roadData.cumDist[si];
        const ed = roadData.cumDist[ei];
        const target = sd + frac * (ed - sd);
        for (let i = si; i < ei; i++) {
            if (roadData.cumDist[i + 1] >= target) {
                const segS = roadData.cumDist[i], segE = roadData.cumDist[i + 1];
                const f = segE > segS ? (target - segS) / (segE - segS) : 0;
                return {
                    lat: roadData.geometry[i][0] + f * (roadData.geometry[i + 1][0] - roadData.geometry[i][0]),
                    lng: roadData.geometry[i][1] + f * (roadData.geometry[i + 1][1] - roadData.geometry[i][1])
                };
            }
        }
        return { lat: roadData.geometry[ei][0], lng: roadData.geometry[ei][1] };
    }

    // ── Vehicle simulation ──────────────────────────────────────────────

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
            '#0ea5e9', '#2563eb', '#10b981', '#f59e0b',
            '#ec4899', '#8b5cf6', '#f43f5e', '#14b8a6',
        ];
        if (routeIndex < palette.length) return palette[routeIndex];
        const hue = (routeIndex * 137.508) % 360;
        return `hsl(${hue},72%,44%)`;
    }

    renderVehicleMarkers(algo, isDdqn, color) {
        const result = this.app.state.lastResult;
        if (result) this.initSimulation(result);
    }

    initSimulation(result) {
        if (this.routeLayers) {
            for (const key in this.routeLayers) {
                this.routeLayers[key].clearLayers();
            }
        }
        if (this.vehicleLayers) {
            for (const key in this.vehicleLayers) {
                this.vehicleLayers[key].clearLayers();
            }
        }
        this.ddqnVehicleLayer?.clearLayers();
        this.alnsVehicleLayer?.clearLayers();
        this.ddqnVehicles.clear();
        this.alnsVehicles.clear();
        this.vehiclesMap = {};

        const colors = {
            ddqn: '#0b8a65',
            alns: '#2563eb',
            ortools: '#e11d48',
            hybrid_fixed: '#d97706',
            hybrid_ddqn: '#7c3aed',
            hybrid_ddqn_transfer_rc1: '#0284c7',
            hybrid_ddqn_transfer_dr: '#4f46e5',
            hybrid: '#0b8a65'
        };

        const setupVehicles = (algo, algoName, baseColor) => {
            if (!algo?.routes) return;
            const layer = this.getVehicleLayer(algoName);
            layer.clearLayers();
            const vehicleMap = this.getVehiclesMap(algoName);

            algo.routes.forEach((route, idx) => {
                if (!route.path || route.path.length === 0) return;
                const color = this.colorForRoute(idx, route, baseColor);
                const start = route.path[0];
                const marker = L.marker([start[0], start[1]], {
                    icon: this.buildVehicleIcon(color)
                });
                const fleetVehicle = this.app.state.fleet?.[route.vehicle_id];
                const driverName = fleetVehicle ? fleetVehicle.driver : `Vehicle #${route.vehicle_id}`;
                marker.bindPopup(driverName);
                marker.addTo(layer);
                vehicleMap.set(route.vehicle_id, marker);
            });
        };

        for (const algoName in result) {
            const baseColor = colors[algoName] || '#6b7280';
            setupVehicles(result[algoName], algoName, baseColor);

            if (algoName === 'ddqn') {
                const map = this.getVehiclesMap('ddqn');
                map.forEach((marker, id) => {
                    this.ddqnVehicles.set(id, marker);
                    marker.addTo(this.ddqnVehicleLayer);
                });
            } else if (algoName === 'alns') {
                const map = this.getVehiclesMap('alns');
                map.forEach((marker, id) => {
                    this.alnsVehicles.set(id, marker);
                    marker.addTo(this.alnsVehicleLayer);
                });
            }
        }
    }

    updateSimulation(t_sim, algoResult, isDdqnOrAlgoName) {
        const algoName = (typeof isDdqnOrAlgoName === 'boolean') 
            ? (isDdqnOrAlgoName ? 'ddqn' : 'alns') 
            : isDdqnOrAlgoName;
        const vehicleMap = this.getVehiclesMap(algoName);
        const prefix = algoName;
        if (!algoResult?.routes) return;

        const layerGroup = this.getRouteLayer(algoName);
        layerGroup.clearLayers();
        const capacity = Number(this.app.state.lastRunFleet?.capacity ?? this.app.state.capacity);
        
        const colors = {
            ddqn: '#0b8a65',
            alns: '#2563eb',
            ortools: '#e11d48',
            hybrid_fixed: '#d97706',
            hybrid_ddqn: '#7c3aed',
            hybrid_ddqn_transfer_rc1: '#0284c7',
            hybrid_ddqn_transfer_dr: '#4f46e5',
            hybrid: '#0b8a65'
        };
        const baseColor = colors[algoName] || '#6b7280';

        algoResult.routes.forEach((route, routeIndex) => {
            const marker = vehicleMap.get(route.vehicle_id);
            if (!marker) return;
            const roadKey = `${prefix}_${route.vehicle_id}`;
            const roadData = this.roadRoutes.get(roadKey);
            const state = this.getVehicleStateAtTime(route, t_sim, roadData);
            marker.setLatLng([state.lat, state.lng]);

            const fleetVehicle = this.app.state.fleet?.[route.vehicle_id];
            const driverName = fleetVehicle ? fleetVehicle.driver : `Vehicle #${route.vehicle_id}`;

            marker.bindPopup(`
                <div style="font-family: Inter, sans-serif; min-width: 160px; padding: 4px 0;">
                    <div style="font-weight: 700; font-size: 13px; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 6px;">
                        🚚 ${driverName}
                    </div>
                    <div style="font-size: 11px; font-weight: 600; color: #3b82f6; text-transform: uppercase; letter-spacing: 0.05em;">
                        ${state.status}
                    </div>
                    <div style="font-size: 11px; color: #475569; margin-top: 2px; line-height: 1.4;">
                        ${state.detail}
                    </div>
                </div>
            `);

            const color = this.colorForRoute(routeIndex, route, baseColor);
            const popup = this._buildRoutePopup(route, capacity, routeIndex);
            const coords = roadData ? roadData.geometry : route.path.map(p => [p[0], p[1]]);

            let splitIdx = 0;
            if (roadData) {
                const legIndex = state.legIndex ?? 0;
                const frac = state.frac ?? 0;
                const si = roadData.legBounds[legIndex] ?? 0;
                const ei = roadData.legBounds[legIndex + 1] ?? coords.length - 1;
                splitIdx = Math.min(coords.length - 1, si + Math.round(frac * (ei - si)));
            } else {
                splitIdx = Math.min(coords.length - 1, state.stopIndex ?? 0);
            }

            const completedCoords = coords.slice(0, splitIdx + 1);
            completedCoords.push([state.lat, state.lng]);
            const upcomingCoords = [[state.lat, state.lng]].concat(coords.slice(splitIdx + 1));

            if (completedCoords.length >= 2) {
                L.polyline(completedCoords, {
                    color, weight: 4.5, opacity: 0.95, lineJoin: 'round', lineCap: 'round'
                }).bindPopup(popup).addTo(layerGroup);
            }
            if (upcomingCoords.length >= 2) {
                L.polyline(upcomingCoords, {
                    color, weight: 3, opacity: 0.25, dashArray: '6, 6', lineJoin: 'round', lineCap: 'round'
                }).bindPopup(popup).addTo(layerGroup);
            }
        });
    }

    getVehicleStateAtTime(route, t_sim, roadData = null) {
        if (!route.path || route.path.length === 0) {
            return { lat: 0, lng: 0, status: 'Completed', detail: 'No route path', legIndex: 0, frac: 0, stopIndex: 0 };
        }
        if (!route.schedule || route.schedule.length === 0) {
            const start = route.path[0];
            return { lat: start[0], lng: start[1], status: 'Completed', detail: 'Parked at Depot (no schedule)', legIndex: 0, frac: 0, stopIndex: 0 };
        }

        const path = route.path;
        const schedule = route.schedule;
        const numStops = route.stops ? route.stops.length : 0;

        let t_last = 0;
        let coord_last = path[0];

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
                // Try road geometry first
                const roadPos = this._interpolateRoad(roadData, i, frac);
                if (roadPos) {
                    return { ...roadPos, status: 'Traveling', detail: `En route to "${step.name}". ETA ${Math.ceil(t_arrival - t_sim)}m.`, legIndex: i, frac: frac, stopIndex: i };
                }
                // Straight-line fallback
                const lat = coord_last[0] + frac * (coord_curr[0] - coord_last[0]);
                const lng = coord_last[1] + frac * (coord_curr[1] - coord_last[1]);
                return { lat, lng, status: 'Traveling', detail: `Traveling to "${step.name}". Arriving in ${Math.ceil(t_arrival - t_sim)}m.`, legIndex: i, frac: frac, stopIndex: i };
            }

            if (t_sim >= t_arrival && t_sim < t_service_start) {
                return { lat: coord_curr[0], lng: coord_curr[1], status: 'Waiting', detail: `Waiting at "${step.name}" (window opens in ${Math.ceil(t_service_start - t_sim)}m).`, legIndex: i, frac: 1.0, stopIndex: i + 1 };
            }

            if (t_sim >= t_service_start && t_sim < t_departure) {
                return { lat: coord_curr[0], lng: coord_curr[1], status: 'Servicing', detail: `Servicing "${step.name}". Remaining: ${Math.ceil(t_departure - t_sim)}m.`, legIndex: i, frac: 1.0, stopIndex: i + 1 };
            }

            t_last = t_departure;
            coord_last = coord_curr;
        }

        // Return to depot
        const stepDepot = schedule[numStops];
        const coord_depot = path[numStops + 1] || path[0];
        if (stepDepot && coord_depot) {
            const t_travel_start = t_last;
            const t_arrival = stepDepot.arrival;
            if (t_sim >= t_travel_start && t_sim < t_arrival) {
                const dur = t_arrival - t_travel_start;
                const frac = dur > 0 ? (t_sim - t_travel_start) / dur : 1;
                const roadPos = this._interpolateRoad(roadData, numStops, frac);
                if (roadPos) {
                    return { ...roadPos, status: 'Returning', detail: `Returning to Depot. ETA ${Math.ceil(t_arrival - t_sim)}m.`, legIndex: numStops, frac: frac, stopIndex: numStops };
                }
                const lat = coord_last[0] + frac * (coord_depot[0] - coord_last[0]);
                const lng = coord_last[1] + frac * (coord_depot[1] - coord_last[1]);
                return { lat, lng, status: 'Returning', detail: `Returning to Depot. Arriving in ${Math.ceil(t_arrival - t_sim)}m.`, legIndex: numStops, frac: frac, stopIndex: numStops };
            }
            t_last = t_arrival;
        }

        const endCoord = coord_depot || coord_last;
        return { lat: endCoord[0], lng: endCoord[1], status: 'Completed', detail: 'All tasks completed. Parked at Depot.', legIndex: numStops, frac: 1.0, stopIndex: numStops + 1 };
    }

    stopVehicleAnimations() { /* simulation handles ticks */ }

    buildDepotIcon() {
        return L.divIcon({
            className: 'map-marker-wrap',
            iconSize: [72, 84], iconAnchor: [36, 72], popupAnchor: [0, -42],
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
            iconSize: [28, 36], iconAnchor: [14, 33], popupAnchor: [0, -20],
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
            iconSize: [56, 56], iconAnchor: [28, 28], popupAnchor: [0, -18],
            html: `<div class="map-icon-3d vehicle" style="--icon-main:${color};--icon-dark:#0f3d33;--icon-shadow:rgba(15,61,51,0.35)"><span class="map-icon-glyph">🚚</span></div>`
        });
    }

    // ── Diff segments (ALNS-only edges) ──────────────────────────────────

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
        L.polyline(path, { color: '#ff5a5f', weight: 10, opacity: 0.22, lineCap: 'round' }).addTo(layerGroup);
        L.polyline(path, { color: '#d7191c', weight: 5, opacity: 0.92, dashArray: '8 5', lineCap: 'round' })
            .bindPopup(`ALNS-only segment • Route ${routeIndex + 1}`).addTo(layerGroup);
    }

    renderAlnsOnlySegments(ddqn, alns) {
        const ddqnSegments = this.collectSegmentSet(ddqn);
        let highlightedSegments = 0;
        (alns.routes || []).forEach((route, routeIndex) => {
            if (!route.path || route.path.length < 2) return;
            let streak = [];
            for (let i = 0; i < route.path.length - 1; i++) {
                const a = route.path[i], b = route.path[i + 1];
                if (!ddqnSegments.has(this.segmentKey(a, b))) {
                    if (streak.length === 0) streak.push([a[0], a[1]]);
                    streak.push([b[0], b[1]]);
                    highlightedSegments += 1;
                    continue;
                }
                if (streak.length > 1) { this.drawDiffSegment(streak, this.alnsDiffLayer, routeIndex); streak = []; }
            }
            if (streak.length > 1) this.drawDiffSegment(streak, this.alnsDiffLayer, routeIndex);
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

    focusOnVehicle(vehicleId) {
        const marker = this.currentView === 'ddqn' ? this.ddqnVehicles.get(Number(vehicleId)) : this.alnsVehicles.get(Number(vehicleId));
        if (marker) {
            this.map.setView(marker.getLatLng(), 15, { animate: true });
            marker.openPopup();
        } else {
            const key = `${this.currentView}_${vehicleId}`;
            const road = this.roadRoutes.get(key);
            if (road && road.geometry.length > 0) {
                this.map.fitBounds(L.polyline(road.geometry).getBounds(), { padding: [50, 50] });
            }
        }
    }
}