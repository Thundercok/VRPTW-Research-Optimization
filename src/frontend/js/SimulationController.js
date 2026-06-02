export class SimulationController {
  constructor(app) {
    this.app = app;
    this.isPlaying = false;
    this.t_sim = 0;
    this.speed = 2; // default to 2x
    this.maxTime = 240; // baseline default
    this.lastTickTime = 0;
    this.animationFrameId = null;

    // UI elements
    this.btnPlay = null;
    this.slider = null;
    this.timeDisplay = null;
    this.speedSelect = null;
    this.vehicleList = null;
    this.controlPanel = null;

    // Dispatch incident controls
    this.incidents = new Map(); // vehicleId -> { type: 'breakdown' | 'traffic', triggerTime: number }
    this.delayOffsets = new Map(); // vehicleId -> number (accumulated permanent delay in minutes)
    this.alerts = []; // array of { time: string, type: string, message: string }
    this.lastVehicleStates = new Map(); // vehicleId -> string (status_stopIndex transition state indicator)
  }

  init() {
    this.btnPlay = document.getElementById('btn-sim-play');
    this.slider = document.getElementById('sim-slider');
    this.timeDisplay = document.getElementById('sim-time-display');
    this.speedSelect = document.getElementById('sim-speed');
    this.vehicleList = document.getElementById('sim-vehicle-panel');
    this.controlPanel = document.getElementById('sim-control-panel');

    this.wireEvents();
  }

  wireEvents() {
    this.btnPlay?.addEventListener('click', () => this.togglePlay());
    this.slider?.addEventListener('input', (e) => this.scrub(Number(e.target.value)));
    this.speedSelect?.addEventListener('change', (e) => {
      this.speed = Number(e.target.value) || 10;
    });

    // Sync radio buttons to update simulation layers immediately
    const mapToggles = document.querySelectorAll('input[name="map_view"]');
    mapToggles.forEach(radio => {
      radio.addEventListener('change', () => {
        this.updateFrame();
      });
    });

    // Toggle driver app companion
    const btnToggleApp = document.getElementById('btn-toggle-driver-app');
    const appEmulator = document.getElementById('driver-app-emulator');
    btnToggleApp?.addEventListener('click', () => {
      appEmulator?.classList.toggle('hidden');
      const isHidden = appEmulator?.classList.contains('hidden');
      btnToggleApp.style.background = isHidden ? 'var(--primary)' : 'var(--success)';
      this.updateDriverAppScreen();
    });

    // Select driver
    const driverSelect = document.getElementById('driver-app-select');
    driverSelect?.addEventListener('change', () => {
      this.updateDriverAppScreen();
    });
  }

  start(maxTime) {
    this.maxTime = Math.max(1, maxTime || 240);
    this.t_sim = 0;
    this.isPlaying = false;

    this.incidents.clear();
    this.delayOffsets.clear();
    this.alerts = [];
    this.lastVehicleStates.clear();

    this.addAlert('info', 'Simulation started. Dispatch center monitoring online.');
    
    if (this.slider) {
      this.slider.max = String(this.maxTime);
      this.slider.value = '0';
    }
    
    this.updatePlayButton();
    this.updateTimeDisplay();
    this.showPanels(true);
    
    this.stopLoop();
    this.updateFrame();
  }

  showPanels(visible) {
    const btnToggle = document.getElementById('btn-toggle-driver-app');
    const driverApp = document.getElementById('driver-app-emulator');
    if (visible) {
      this.controlPanel?.classList.remove('hidden');
      this.vehicleList?.classList.remove('hidden');
      btnToggle?.classList.remove('hidden');
      this.updateDriverAppSelect();
    } else {
      this.controlPanel?.classList.add('hidden');
      this.vehicleList?.classList.add('hidden');
      btnToggle?.classList.add('hidden');
      driverApp?.classList.add('hidden');
      this.stopLoop();
    }
  }

  togglePlay() {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  }

  play() {
    if (this.t_sim >= this.maxTime) {
      this.t_sim = 0; // wrap around
      this.lastVehicleStates.clear();
      this.alerts = [];
      this.addAlert('info', 'Simulation restarted.');
    }
    this.isPlaying = true;
    this.lastTickTime = performance.now();
    this.updatePlayButton();
    this.startLoop();
  }

  pause() {
    this.isPlaying = false;
    this.updatePlayButton();
    this.stopLoop();
  }

  scrub(value) {
    this.t_sim = Math.min(this.maxTime, Math.max(0, value));
    this.updateTimeDisplay();
    this.updateFrame();
  }

  startLoop() {
    const loop = (timestamp) => {
      if (!this.isPlaying) return;
      
      const elapsedSec = (timestamp - this.lastTickTime) / 1000;
      this.lastTickTime = timestamp;

      // Update simulation time
      this.t_sim += elapsedSec * this.speed;

      if (this.t_sim >= this.maxTime) {
        this.t_sim = this.maxTime;
        this.pause();
      }

      if (this.slider) {
        this.slider.value = String(Math.round(this.t_sim));
      }
      this.updateTimeDisplay();
      this.updateFrame();

      this.animationFrameId = requestAnimationFrame(loop);
    };

    this.stopLoop();
    this.lastTickTime = performance.now();
    this.animationFrameId = requestAnimationFrame(loop);
  }

  stopLoop() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  updateTimeDisplay() {
    if (!this.timeDisplay) return;
    const minutes = Math.floor(this.t_sim);
    const secs = Math.floor((this.t_sim % 1) * 60);
    this.timeDisplay.textContent = `Time: ${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}m`;
  }

  updatePlayButton() {
    if (!this.btnPlay) return;
    this.btnPlay.textContent = this.isPlaying ? '⏸ Pause' : '▶ Play';
  }

  // Intercept the geospatial vehicle position during update checks
  getIncidentState(vehicleId, t_sim, route, roadData) {
    const offset = this.delayOffsets.get(vehicleId) || 0;
    const activeIncident = this.incidents.get(vehicleId);

    // Calculate effective time progression
    let t_eff = t_sim - offset;

    if (activeIncident) {
      const triggerTime = activeIncident.triggerTime;
      
      if (t_sim >= triggerTime) {
        if (activeIncident.type === 'breakdown') {
          // Freeze marker coordinates at breakdown trigger point
          const freezeTime = Math.max(0, triggerTime - offset);
          const state = this.app.mapController.getVehicleStateAtTimeDirect(route, freezeTime, roadData);
          const elapsed = Math.round(t_sim - triggerTime);
          return {
            ...state,
            status: 'Breakdown',
            detail: `⚠️ Breakdown! Delayed by ${elapsed}m. Technician active.`,
            lat: state.lat,
            lng: state.lng
          };
        } else if (activeIncident.type === 'traffic') {
          // Progress time since traffic onset at 33% rate (inducing travel time delay)
          const elapsed = t_sim - triggerTime;
          const elapsedEff = elapsed * 0.33;
          t_eff = triggerTime - offset + elapsedEff;
          
          const state = this.app.mapController.getVehicleStateAtTimeDirect(route, t_eff, roadData);
          const delayMinutes = Math.round(elapsed - elapsedEff);
          return {
            ...state,
            status: 'Traffic Jam',
            detail: `🛑 Congestion! Delayed: +${delayMinutes}m. Speed: 12 km/h.`,
            lat: state.lat,
            lng: state.lng
          };
        }
      }
    }

    if (offset > 0) {
      const state = this.app.mapController.getVehicleStateAtTimeDirect(route, t_eff, roadData);
      return {
        ...state,
        detail: `${state.detail} (Delayed: +${Math.round(offset)}m)`
      };
    }

    return null; // let normal map coordinate interpolation proceed
  }

  toggleIncident(vehicleId, type) {
    vehicleId = Number(vehicleId);
    const active = this.incidents.get(vehicleId);
    const driverName = this.getDriverName(vehicleId);

    if (active) {
      if (active.type === type) {
        this.clearIncident(vehicleId);
      } else {
        this.clearIncident(vehicleId);
        this.incidents.set(vehicleId, { type, triggerTime: this.t_sim });
        this.addAlert(type === 'breakdown' ? 'error' : 'warn', 
          `Disruption Alert: ${driverName} reported active ${type === 'breakdown' ? 'engine breakdown' : 'severe traffic jam'}.`
        );
        this.app.toast('Incident Triggered', `${driverName} reports active ${type}.`, 'warn');
      }
    } else {
      this.incidents.set(vehicleId, { type, triggerTime: this.t_sim });
      this.addAlert(type === 'breakdown' ? 'error' : 'warn', 
        `Disruption Alert: ${driverName} reported active ${type === 'breakdown' ? 'engine breakdown' : 'severe traffic jam'}.`
      );
      this.app.toast('Incident Triggered', `${driverName} reports active ${type}.`, 'warn');
    }

    this.updateFrame();
  }

  clearIncident(vehicleId) {
    vehicleId = Number(vehicleId);
    const active = this.incidents.get(vehicleId);
    if (!active) return;

    const driverName = this.getDriverName(vehicleId);
    const elapsed = this.t_sim - active.triggerTime;
    let delayAdded = 0;

    if (active.type === 'breakdown') {
      delayAdded = elapsed;
    } else if (active.type === 'traffic') {
      delayAdded = elapsed * 0.67; // 33% progress means 67% loss rate
    }

    const currentOffset = this.delayOffsets.get(vehicleId) || 0;
    this.delayOffsets.set(vehicleId, currentOffset + delayAdded);
    this.incidents.delete(vehicleId);

    this.addAlert('success', `Resolved: ${driverName} disruption cleared. Route delay committed: +${Math.round(currentOffset + delayAdded)}m.`);
    this.app.toast('Incident Resolved', `${driverName} reports path clear.`, 'ok');
    this.updateFrame();
  }

  addAlert(type, message) {
    const minutes = Math.floor(this.t_sim);
    const secs = Math.floor((this.t_sim % 1) * 60);
    const timeStr = `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    this.alerts.unshift({
      time: timeStr,
      type, // 'info' | 'warn' | 'error' | 'success'
      message
    });

    if (this.alerts.length > 30) {
      this.alerts.pop();
    }
  }

  getRouteForVehicle(vehicleId) {
    const result = this.app.state.lastResult;
    if (!result) return null;
    const mapModeElement = document.querySelector('input[name="map_view"]:checked');
    const activeAlgo = mapModeElement ? mapModeElement.value : 'ddqn';
    const algoResult = result[activeAlgo];
    if (!algoResult || !algoResult.routes) return null;
    return algoResult.routes.find(r => r.vehicle_id === Number(vehicleId));
  }

  getDriverName(vehicleId) {
    const fleetVehicle = this.app.state.fleet?.[vehicleId];
    return fleetVehicle ? fleetVehicle.driver : `Vehicle #${vehicleId}`;
  }

  updateFrame() {
    const result = this.app.state.lastResult;
    if (!result) return;

    // Determine current view (e.g. ddqn, alns, ortools, etc.)
    const mapModeElement = document.querySelector('input[name="map_view"]:checked');
    const activeAlgo = mapModeElement ? mapModeElement.value : 'ddqn';
    const algoResult = result[activeAlgo];

    if (!algoResult || !algoResult.routes) return;

    // Run transition checks and auto-log alerts
    this.checkStateTransitions(algoResult);

    // Update vehicle markers positions on Map
    this.app.mapController.updateSimulation(this.t_sim, algoResult, activeAlgo);

    // Update status panel in the UI
    this.updateStatusPanel(algoResult, activeAlgo);

    // Update companion app view
    this.updateDriverAppScreen();

    // Update Gantt chart cursor and active algorithm selection
    if (this.app.ganttController) {
      if (this.app.ganttController.activeAlgo !== activeAlgo) {
        this.app.ganttController.render(result, activeAlgo);
      }
      this.app.ganttController.setSimTime(this.t_sim);
    }
  }

  checkStateTransitions(algoResult) {
    algoResult.routes.forEach(route => {
      const vehicleId = route.vehicle_id;
      const driverName = this.getDriverName(vehicleId);

      // Get current location/status state (respecting active breakdown freeze if present)
      const roadKey = `${this.app.mapController.activeAlgo || 'ddqn'}_${vehicleId}`;
      const roadData = this.app.mapController.roadRoutes.get(roadKey);
      const state = this.getIncidentState(vehicleId, this.t_sim, route, roadData) || 
                    this.app.mapController.getVehicleStateAtTimeDirect(route, this.t_sim, roadData);

      const activeKey = `${state.status}_${state.stopIndex}`;
      const lastState = this.lastVehicleStates.get(vehicleId);

      if (lastState && lastState !== activeKey) {
        const lastStatus = lastState.split('_')[0];
        const lastStopIndex = Number(lastState.split('_')[1]);

        if (lastStatus === 'Traveling' && (state.status === 'Servicing' || state.status === 'Waiting')) {
          // Arrived at Customer Stop
          const stopIdx = state.stopIndex - 1;
          const customerId = route.stops[stopIdx];
          const customer = this.app.state.customers.find(c => c.id === customerId);
          
          const offset = this.delayOffsets.get(vehicleId) || 0;
          const activeIncident = this.incidents.get(vehicleId);
          let activeDelay = offset;
          if (activeIncident && this.t_sim >= activeIncident.triggerTime) {
            if (activeIncident.type === 'breakdown') activeDelay += (this.t_sim - activeIncident.triggerTime);
            else if (activeIncident.type === 'traffic') activeDelay += (this.t_sim - activeIncident.triggerTime) * 0.67;
          }

          const step = route.schedule[stopIdx];
          if (customer && step) {
            const actualArrival = step.arrival + activeDelay;
            const isLate = actualArrival > customer.due;
            if (isLate) {
              this.addAlert('error', `🛑 Late Delivery: ${driverName} reached customer ${customer.name} LATE at ${this.formatTimeStr(actualArrival)} (Due by: ${this.formatTimeStr(customer.due)}).`);
            } else {
              this.addAlert('success', `✓ Arrived: ${driverName} reached customer ${customer.name} on time.`);
            }

            // Check skill mismatch
            const fleetVehicle = this.app.state.fleet?.[vehicleId];
            const driverSkills = fleetVehicle ? (fleetVehicle.skills || 'None') : 'None';
            if (customer.skill && customer.skill !== 'None') {
              if (driverSkills === 'None' || !driverSkills.includes(customer.skill)) {
                this.addAlert('warn', `⚠️ Skill Mismatch: ${driverName} started service at customer ${customer.name} without required skill "${customer.skill}".`);
              }
            }
          }
        } else if (lastStatus === 'Servicing' && (state.status === 'Traveling' || state.status === 'Returning')) {
          // Service Completed
          const stopIdx = lastStopIndex - 1;
          const customerId = route.stops[stopIdx];
          const customer = this.app.state.customers.find(c => c.id === customerId);
          if (customer) {
            this.addAlert('info', `📦 Delivery Proof: ${driverName} completed packages verification signature at "${customer.name}".`);
          }
        } else if (state.status === 'Returning' && lastStatus !== 'Returning') {
          this.addAlert('info', `↩ Dispatch Update: ${driverName} completed all drops, returning to depot.`);
        }
      }

      this.lastVehicleStates.set(vehicleId, activeKey);
    });
  }

  updateStatusPanel(algoResult, algoName) {
    if (!this.vehicleList) return;
    
    this.activeSubTab = this.activeSubTab || 'vehicles';

    const colors = {
      ddqn: '#10b981',
      alns: '#3b82f6',
      ortools: '#ef4444',
      hybrid_fixed: '#f59e0b',
      hybrid_ddqn: '#8b5cf6',
      hybrid_ddqn_transfer_rc1: '#06b6d4',
      hybrid_ddqn_transfer_dr: '#6366f1',
      hybrid: '#10b981'
    };
    const color = colors[algoName] || '#3b82f6';
    
    let html = `
      <div class="sim-panel-tabs" style="display: flex; gap: 4px; background: rgba(230, 235, 245, 0.9); padding: 4px; border-radius: var(--r); margin-bottom: 12px; border: 1px solid var(--border);">
        <button class="btn-sim-tab" data-tab="vehicles" style="flex: 1; border: none; padding: 6px 10px; font-size: 11px; font-weight: 600; border-radius: 4px; cursor: pointer; transition: all 0.2s; background: ${this.activeSubTab === 'vehicles' ? '#ffffff' : 'transparent'}; color: ${this.activeSubTab === 'vehicles' ? 'var(--text-main)' : 'var(--text-muted)'}; box-shadow: ${this.activeSubTab === 'vehicles' ? 'var(--shadow-sm)' : 'none'};">Drivers</button>
        <button class="btn-sim-tab" data-tab="alerts" style="flex: 1; border: none; padding: 6px 10px; font-size: 11px; font-weight: 600; border-radius: 4px; cursor: pointer; transition: all 0.2s; background: ${this.activeSubTab === 'alerts' ? '#ffffff' : 'transparent'}; color: ${this.activeSubTab === 'alerts' ? 'var(--text-main)' : 'var(--text-muted)'}; box-shadow: ${this.activeSubTab === 'alerts' ? 'var(--shadow-sm)' : 'none'};">Alerts</button>
        <button class="btn-sim-tab" data-tab="pod" style="flex: 1; border: none; padding: 6px 10px; font-size: 11px; font-weight: 600; border-radius: 4px; cursor: pointer; transition: all 0.2s; background: ${this.activeSubTab === 'pod' ? '#ffffff' : 'transparent'}; color: ${this.activeSubTab === 'pod' ? 'var(--text-main)' : 'var(--text-muted)'}; box-shadow: ${this.activeSubTab === 'pod' ? 'var(--shadow-sm)' : 'none'};">POD Logs</button>
      </div>
    `;

    if (this.activeSubTab === 'vehicles') {
      const routeCapacity = Number(this.app.state.lastRunFleet?.capacity ?? this.app.state.capacity);

      algoResult.routes.forEach((route) => {
        const fleetVehicle = this.app.state.fleet?.[route.vehicle_id];
        const driverName = fleetVehicle ? fleetVehicle.driver : `Vehicle #${route.vehicle_id}`;
        const vehCap = fleetVehicle ? Number(fleetVehicle.capacity) : routeCapacity;
        const driverSkills = fleetVehicle ? (fleetVehicle.skills || 'None') : 'None';

        const roadKey = `${algoName}_${route.vehicle_id}`;
        const roadData = this.app.mapController.roadRoutes.get(roadKey);
        const state = this.getIncidentState(route.vehicle_id, this.t_sim, route, roadData) || 
                      this.app.mapController.getVehicleStateAtTimeDirect(route, this.t_sim, roadData);

        const stopsDone = route.stops.filter((stopId, idx) => {
          const step = route.schedule[idx];
          const offset = this.delayOffsets.get(route.vehicle_id) || 0;
          
          const activeIncident = this.incidents.get(route.vehicle_id);
          let activeDelay = offset;
          if (activeIncident && this.t_sim >= activeIncident.triggerTime) {
            if (activeIncident.type === 'breakdown') activeDelay += (this.t_sim - activeIncident.triggerTime);
            else if (activeIncident.type === 'traffic') activeDelay += (this.t_sim - activeIncident.triggerTime) * 0.67;
          }
          
          return step && this.t_sim >= (step.departure + activeDelay);
        }).length;
        
        const totalStops = route.stops.length;
        const percent = totalStops > 0 ? Math.round((stopsDone / totalStops) * 100) : 100;
        const loadPercent = vehCap > 0 ? Math.round((route.load / vehCap) * 100) : 0;
        
        // Dynamic Telemetry Math
        const fuelLevel = Math.max(0, Math.round(100 - (stopsDone / totalStops) * 45));
        const co2Value = (stopsDone * 2.8).toFixed(1);

        const mismatches = [];
        route.stops.forEach((stopId) => {
          const customer = this.app.state.customers.find(c => c.id === stopId);
          if (customer && customer.skill && customer.skill !== 'None') {
            if (driverSkills === 'None' || !driverSkills.includes(customer.skill)) {
              mismatches.push(customer.skill);
            }
          }
        });
        
        // Incident indicators check
        const activeIncident = this.incidents.get(route.vehicle_id);
        const isBreakdown = activeIncident?.type === 'breakdown';
        const isTraffic = activeIncident?.type === 'traffic';
        const cardClass = isBreakdown ? 'has-breakdown' : (isTraffic ? 'has-traffic' : '');

        let statusClass = 'sim-status-parked';
        if (state.status === 'Traveling') statusClass = 'sim-status-traveling';
        if (state.status === 'Waiting') statusClass = 'sim-status-waiting';
        if (state.status === 'Servicing') statusClass = 'sim-status-servicing';
        if (state.status === 'Returning') statusClass = 'sim-status-returning';
        if (state.status === 'Breakdown') statusClass = 'sim-status-parked'; // use red styling override via cardClass
        if (state.status === 'Traffic Jam') statusClass = 'sim-status-waiting';

        html += `
          <div class="sim-vehicle-card ${cardClass} btn-focus-vehicle" data-vehicle-id="${route.vehicle_id}">
            <div class="sim-card-header">
              <span class="sim-veh-id" style="border-left: 3px solid ${color}; padding-left: 8px;">${driverName}</span>
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="focus-lbl" style="font-size: 9px; font-weight: 600; color: var(--text-muted); background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px;">🔍 Focus</span>
                <span class="sim-badge ${statusClass}">${state.status}</span>
              </div>
            </div>
            <div class="sim-card-body">
              <p class="sim-detail-text" style="font-size: 11px; margin-bottom: 8px; color: var(--text-muted); line-height: 1.4;">${state.detail}</p>
              ${mismatches.length > 0 
                ? `<div style="background: rgba(239, 68, 68, 0.1); color: var(--danger); font-size: 10px; margin-bottom: 8px; padding: 4px 8px; border-radius: 4px; display: flex; align-items: center; gap: 4px; border: 1px solid rgba(239, 68, 68, 0.2); font-weight: 600;">
                     ⚠️ Skill Gap: Needs ${[...new Set(mismatches)].join(', ')}
                   </div>`
                : ''
              }

              <!-- Telemetry indicators row -->
              <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-bottom: 6px; margin-top: 4px; border-top: 1px solid rgba(0,0,0,0.04); padding-top: 4px;">
                <span>🔋 Fuel: <strong>${fuelLevel}%</strong></span>
                <span>🌱 CO2: <strong>${co2Value} kg</strong></span>
              </div>

              <div class="sim-stat-row" style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-bottom: 4px;">
                <span>Stops: ${stopsDone}/${totalStops}</span>
                <span>Load: ${route.load}/${vehCap} (${loadPercent}%)</span>
              </div>
              <div class="sim-progress-bar" style="background: rgba(0,0,0,0.06); height: 4px; border-radius: 2px; overflow: hidden; margin-bottom: 6px;">
                <div class="sim-progress-fill" style="width: ${percent}%; background-color: ${color}; height: 100%;"></div>
              </div>

              <!-- Interactive disruption buttons -->
              <div class="sim-card-actions" style="display: flex; gap: 4px; margin-top: 8px; border-top: 1px dashed var(--border); padding-top: 8px;">
                <button class="btn-sim-incident btn-trigger-breakdown" data-vehicle-id="${route.vehicle_id}" style="flex: 1; font-size: 9px; padding: 4px 6px; background: ${isBreakdown ? '#ef4444' : 'rgba(239, 68, 68, 0.08)'}; color: ${isBreakdown ? '#ffffff' : '#ef4444'}; border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 4px; cursor: pointer; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 3px;">
                  ⚠️ ${isBreakdown ? 'Clear incident' : 'Breakdown'}
                </button>
                <button class="btn-sim-incident btn-trigger-traffic" data-vehicle-id="${route.vehicle_id}" style="flex: 1; font-size: 9px; padding: 4px 6px; background: ${isTraffic ? '#f59e0b' : 'rgba(245, 158, 11, 0.08)'}; color: ${isTraffic ? '#ffffff' : '#f59e0b'}; border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 4px; cursor: pointer; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 3px;">
                  🚦 ${isTraffic ? 'Clear congestion' : 'Traffic Jam'}
                </button>
              </div>
            </div>
          </div>
        `;
      });
    } else if (this.activeSubTab === 'alerts') {
      // Alerts log
      let alertsHtml = `<div class="sim-alerts-container">`;
      if (this.alerts.length === 0) {
        alertsHtml += `
          <div class="text-center text-muted" style="padding: 24px 16px; font-size: 11px; background: rgba(255,255,255,0.9); border-radius: var(--r); border: 1px solid var(--border);">
            No dispatcher alerts logged yet. Run simulation to stream live updates.
          </div>
        `;
      } else {
        this.alerts.forEach(alert => {
          alertsHtml += `
            <div class="sim-alert-item ${alert.type}">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="sim-alert-time">${alert.time}</span>
                <span style="font-weight: 700; text-transform: uppercase; font-size: 8px;">${alert.type}</span>
              </div>
              <div style="font-size: 11.5px; color: var(--text-main); font-weight: 500;">
                ${alert.message}
              </div>
            </div>
          `;
        });
      }
      alertsHtml += `</div>`;
      html += alertsHtml;
    } else {
      // POD Sub-Tab
      const completedStops = [];
      algoResult.routes.forEach((route) => {
        const fleetVehicle = this.app.state.fleet?.[route.vehicle_id];
        const driverName = fleetVehicle ? fleetVehicle.driver : `Vehicle #${route.vehicle_id}`;
        
        route.schedule.forEach((step, idx) => {
          if (step.customer_id === 0) return; // skip depot
          
          const offset = this.delayOffsets.get(route.vehicle_id) || 0;
          const activeIncident = this.incidents.get(route.vehicle_id);
          let activeDelay = offset;
          if (activeIncident && this.t_sim >= activeIncident.triggerTime) {
            if (activeIncident.type === 'breakdown') activeDelay += (this.t_sim - activeIncident.triggerTime);
            else if (activeIncident.type === 'traffic') activeDelay += (this.t_sim - activeIncident.triggerTime) * 0.67;
          }

          const actArrival = step.arrival + activeDelay;
          const actDeparture = step.departure + activeDelay;

          if (this.t_sim >= actDeparture) {
            completedStops.push({
              driverName,
              stopId: step.customer_id,
              name: step.name || `Stop #${step.customer_id}`,
              timeStr: this.formatTimeStr(actDeparture),
              status: 'Completed',
              due: actArrival <= Number(this.app.state.customers[step.customer_id]?.due || 1000) ? 'On Time' : 'Delayed'
            });
          } else if (this.t_sim >= actArrival) {
            completedStops.push({
              driverName,
              stopId: step.customer_id,
              name: step.name || `Stop #${step.customer_id}`,
              timeStr: this.formatTimeStr(this.t_sim),
              status: 'Arriving / Servicing',
              due: 'Active'
            });
          }
        });
      });

      completedStops.sort((a, b) => b.stopId - a.stopId);

      if (completedStops.length === 0) {
        html += `
          <div class="text-center text-muted" style="padding: 24px 16px; font-size: 11px; background: rgba(255,255,255,0.9); border-radius: var(--r); border: 1px solid var(--border);">
            No deliveries completed yet. Run the simulation to view Proof of Delivery (POD) logs.
          </div>
        `;
      } else {
        completedStops.forEach(stop => {
          const isDone = stop.status === 'Completed';
          const badgeClass = isDone ? 'status-ready' : 'status-warn';
          const alertColor = stop.due === 'On Time' ? 'var(--success)' : 'var(--orange)';
          
          html += `
            <div class="sim-vehicle-card" style="font-size: 11px; margin-bottom: 8px; border-left: 3px solid ${isDone ? 'var(--success)' : 'var(--orange)'};">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <strong style="color: var(--text-main); font-size: 11px;">Stop #${stop.stopId}: ${this.app.escapeHtml(stop.name)}</strong>
                <span class="status-pill ${badgeClass}" style="font-size: 9px; padding: 2px 6px;">${isDone ? 'Done' : 'Active'}</span>
              </div>
              <div style="color: var(--text-muted); margin-bottom: 6px;">
                Driver: <strong>${stop.driverName}</strong>
              </div>
              ${isDone ? `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border);">
                  <span style="color: ${alertColor}; font-weight: 600; font-size: 10px;">✓ ${stop.due} (${stop.timeStr})</span>
                  <button class="btn-text btn-pod-view" data-stop-id="${stop.stopId}" data-driver="${stop.driverName}" data-time="${stop.timeStr}" data-due="${stop.due}" data-name="${stop.name}" style="font-size: 10px; font-weight: 700; color: var(--primary); text-decoration: underline; padding: 0; background: none; border: none; cursor: pointer;">View POD &rarr;</button>
                </div>
              ` : `
                <div style="color: var(--primary); font-weight: 600; font-style: italic; font-size: 10px; margin-top: 4px;">
                  ⏳ Drop-off/Service in progress...
                </div>
              `}
            </div>
          `;
        });
      }
    }

    this.vehicleList.innerHTML = html;

    // Bind focus click events to driver cards
    const focusCards = this.vehicleList.querySelectorAll('.btn-focus-vehicle');
    focusCards.forEach(card => {
      card.addEventListener('click', (e) => {
        // Prevent clicks on action buttons inside the card from focusing on Leaflet
        if (e.target.closest('.btn-sim-incident')) return;
        
        const vehId = card.dataset.vehicleId;
        this.app.mapController.focusOnVehicle(vehId);
      });
    });

    // Bind tab switching events
    const tabButtons = this.vehicleList.querySelectorAll('.btn-sim-tab');
    tabButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.activeSubTab = e.target.dataset.tab;
        this.updateFrame();
      });
    });

    // Bind incident triggers
    this.vehicleList.querySelectorAll('.btn-trigger-breakdown').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleIncident(btn.dataset.vehicleId, 'breakdown');
      });
    });

    this.vehicleList.querySelectorAll('.btn-trigger-traffic').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleIncident(btn.dataset.vehicleId, 'traffic');
      });
    });

    // Bind POD modal trigger clicks
    const podButtons = this.vehicleList.querySelectorAll('.btn-pod-view');
    podButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const data = e.target.dataset;
        this.showPodModal({
          stopId: Number(data.stopId),
          driverName: data.driver,
          timeStr: data.time,
          due: data.due,
          name: data.name
        });
      });
    });
  }

  formatTimeStr(minutes) {
    const shiftStart = '08:00';
    const [h, m] = shiftStart.split(':').map(Number);
    const totalMin = h * 60 + m + minutes;
    const rawH = Math.floor(totalMin / 60) % 24;
    const endM = Math.floor(totalMin % 60);
    const period = rawH >= 12 ? 'PM' : 'AM';
    const endH = rawH % 12 === 0 ? 12 : rawH % 12;
    return `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')} ${period}`;
  }

  showPodModal(stop) {
    const existing = document.getElementById('pod-proof-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'pod-proof-modal';
    modal.className = 'modal-overlay';
    modal.style.zIndex = '9999';
    modal.style.display = 'flex';
    modal.style.alignItems = 'center';
    modal.style.justifyContent = 'center';

    const customer = this.app.state.customers[stop.stopId] || {};
    
    const signatureSvg = `
      <svg viewBox="0 0 200 60" style="width: 100%; height: 60px; stroke: #1e3a8a; stroke-width: 2.5; fill: none; stroke-linecap: round; stroke-linejoin: round;">
        <path d="M 15 32 C 35 18, 50 42, 65 22 C 80 12, 85 38, 100 28 C 115 18, 120 48, 135 32 C 150 18, 165 38, 185 28" />
        <path d="M 40 25 L 160 25" style="stroke: rgba(0,0,0,0.1); stroke-width: 1;" />
      </svg>
    `;

    modal.innerHTML = `
      <div class="modal-card" style="width: 380px; max-width: 90%; background: #ffffff; border-radius: var(--r); padding: 20px; border: 1px solid var(--border); box-shadow: var(--shadow-lg); color: var(--text-main);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; border-bottom: 1px solid var(--border); padding-bottom: 10px;">
          <h3 style="margin: 0; font-size: 14px; color: var(--primary);">Proof of Delivery (POD)</h3>
          <button id="btn-close-pod" style="background: none; border: none; font-size: 20px; cursor: pointer; color: var(--text-muted); padding: 0; line-height: 1;">&times;</button>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 10px; font-size: 12px; text-align: left;">
          <div>
            <span style="color: var(--text-muted); font-size: 11px;">Stop Destination</span>
            <div style="font-weight: 700; margin-top: 2px;">#${stop.stopId} - ${this.app.escapeHtml(stop.name)}</div>
            <div style="color: var(--text-muted); font-size: 11px; margin-top: 2px;">${this.app.escapeHtml(customer.address || 'Delivered Destination')}</div>
          </div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <div>
              <span style="color: var(--text-muted); font-size: 11px;">Assigned Driver</span>
              <div style="font-weight: 600; color: var(--primary);">${stop.driverName}</div>
            </div>
            <div>
              <span style="color: var(--text-muted); font-size: 11px;">Delivery Status</span>
              <div style="font-weight: 600; color: ${stop.due === 'On Time' ? 'var(--success)' : 'var(--orange)'};">${stop.due} (${stop.timeStr})</div>
            </div>
          </div>
 
          <div class="signature-pad-container">
            <span style="font-size: 9px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Customer Signature Verification</span>
            <div class="signature-pad-box">
              ${signatureSvg}
            </div>
          </div>
 
          <div style="margin-top: 4px; border: 1px solid var(--border); border-radius: var(--r); overflow: hidden; background: #222; position: relative; height: 130px; display: flex; align-items: center; justify-content: center;">
            <div style="position: absolute; top: 6px; left: 6px; background: var(--success); color: white; padding: 2px 6px; font-size: 8px; font-weight: 700; border-radius: 2px; letter-spacing: 0.5px;">
              AI TIMESTAMP CONFIRMED
            </div>
            <div style="color: rgba(255,255,255,0.8); font-size: 10px; text-align: center;">
              <svg viewBox="0 0 24 24" style="width: 32px; height: 32px; fill: none; stroke: currentColor; stroke-width: 1.5; margin: 0 auto 6px; opacity: 0.7;">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
              </svg>
              Doorstep Package Photo (Ref: POD-ID-${stop.stopId})
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('#btn-close-pod').addEventListener('click', () => {
      modal.remove();
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });
  }

  updateDriverAppSelect() {
    const select = document.getElementById('driver-app-select');
    if (!select) return;
    
    select.innerHTML = '<option value="" style="color: #000;">Select Driver...</option>';
    
    const result = this.app.state.lastResult;
    if (!result) return;
    const mapModeElement = document.querySelector('input[name="map_view"]:checked');
    const activeAlgo = mapModeElement ? mapModeElement.value : 'ddqn';
    const algoResult = result[activeAlgo];
    if (!algoResult || !algoResult.routes) return;
    
    algoResult.routes.forEach((route) => {
      const fleetVehicle = this.app.state.fleet?.[route.vehicle_id];
      const driverName = fleetVehicle ? fleetVehicle.driver : `Vehicle #${route.vehicle_id}`;
      const opt = document.createElement('option');
      opt.value = route.vehicle_id;
      opt.textContent = driverName;
      opt.style.color = '#000';
      select.appendChild(opt);
    });
  }

  updateDriverAppScreen() {
    const container = document.getElementById('driver-app-content');
    const select = document.getElementById('driver-app-select');
    if (!container || !select) return;
    
    const selectedVehId = select.value;
    if (selectedVehId === '') {
      container.innerHTML = `
        <div style="text-align: center; margin-top: 100px; padding: 0 16px;">
            <div style="font-size: 32px; margin-bottom: 12px; animation: bounce 2s infinite;">🚚</div>
            <h4 style="margin: 0 0 6px; font-size: 13px; color: #27272a; font-weight: 700;">Driver Companion Emulator</h4>
            <p style="margin: 0; font-size: 10.5px; color: #71717a; line-height: 1.45;">Select an active driver above to simulate mobile deliveries, log signatures, and track live routes.</p>
        </div>
      `;
      return;
    }
    
    const result = this.app.state.lastResult;
    if (!result) return;
    const mapModeElement = document.querySelector('input[name="map_view"]:checked');
    const activeAlgo = mapModeElement ? mapModeElement.value : 'ddqn';
    const algoResult = result[activeAlgo];
    if (!algoResult || !algoResult.routes) return;
    
    const route = algoResult.routes.find(r => r.vehicle_id === Number(selectedVehId));
    if (!route) {
      container.innerHTML = `<div style="text-align: center; padding: 20px; font-size: 11px; color: #71717a;">No active route found for this driver.</div>`;
      return;
    }

    const fleetVehicle = this.app.state.fleet?.[route.vehicle_id];
    const driverSkills = fleetVehicle ? (fleetVehicle.skills || 'None') : 'None';
    
    let html = `
      <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--border); box-shadow: var(--shadow-sm); margin-bottom: 8px;">
        <span style="font-size: 10.5px; color: var(--text-muted); font-weight: 500;">Route Cargo: <strong>${route.load} units</strong></span>
        <span style="font-size: 9px; background: rgba(59,130,246,0.1); color: var(--primary); padding: 2px 6px; border-radius: 4px; font-weight: 700;">Skills: ${driverSkills}</span>
      </div>
      <div style="font-size: 11px; font-weight: 700; color: #27272a; margin-top: 6px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.03em;">Manifest Queue:</div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
    `;

    route.stops.forEach((stopId, idx) => {
      const step = route.schedule[idx];
      const customer = this.app.state.customers.find(c => c.id === stopId);
      if (!customer || !step) return;

      const offset = this.delayOffsets.get(route.vehicle_id) || 0;
      const activeIncident = this.incidents.get(route.vehicle_id);
      let activeDelay = offset;
      if (activeIncident && this.t_sim >= activeIncident.triggerTime) {
        if (activeIncident.type === 'breakdown') activeDelay += (this.t_sim - activeIncident.triggerTime);
        else if (activeIncident.type === 'traffic') activeDelay += (this.t_sim - activeIncident.triggerTime) * 0.67;
      }

      const arrTime = step.arrival + activeDelay;
      const depTime = step.departure + activeDelay;

      const isCompleted = this.t_sim >= depTime;
      const isServicing = this.t_sim >= arrTime && this.t_sim < depTime;
      const isNext = this.t_sim < arrTime && (idx === 0 || (route.schedule[idx-1] && this.t_sim >= (route.schedule[idx-1].departure + activeDelay)));

      let bg = '#ffffff';
      let border = 'var(--border)';
      let statusText = 'Pending';
      let statusColor = '#71717a';

      if (isCompleted) {
        bg = 'rgba(16,185,129,0.05)';
        border = 'rgba(16,185,129,0.2)';
        statusText = 'Delivered';
        statusColor = 'var(--success)';
      } else if (isServicing) {
        bg = 'rgba(245,158,11,0.05)';
        border = 'rgba(245,158,11,0.3)';
        statusText = 'Active / Servicing';
        statusColor = 'var(--orange)';
      } else if (isNext) {
        bg = 'rgba(59,130,246,0.05)';
        border = 'rgba(59,130,246,0.3)';
        statusText = 'En Route / Next';
        statusColor = 'var(--primary)';
      }

      html += `
        <div class="driver-app-card" style="background: ${bg}; border-color: ${border};">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="color: #18181b; font-size: 11px;">Stop #${stopId} - ${this.app.escapeHtml(customer.name)}</strong>
            <span style="font-size: 9px; font-weight: 700; color: ${statusColor}; text-transform: uppercase;">${statusText}</span>
          </div>
          <div style="font-size: 10px; color: #71717a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            📍 ${this.app.escapeHtml(customer.address || 'Delivered Destination')}
          </div>
          
          <div style="font-size: 9px; color: #a1a1aa; margin-top: 2px; display: flex; justify-content: space-between;">
            <span>Window: ${this.formatTimeStr(customer.ready)} - ${this.formatTimeStr(customer.due)}</span>
            <span>ETA: ${this.formatTimeStr(arrTime)}</span>
          </div>

          ${isServicing ? `
            <div style="display: flex; gap: 6px; margin-top: 8px;">
              <button class="btn-app-action btn-complete-stop" data-stop-id="${stopId}" style="flex: 2; background: var(--success); color: white; border: none; padding: 6px; border-radius: 6px; font-size: 9px; font-weight: 700; cursor: pointer; text-align: center; box-shadow: var(--shadow-sm);">✓ Complete Delivery</button>
              <button class="btn-app-action btn-fail-stop" data-stop-id="${stopId}" style="flex: 1; background: var(--danger); color: white; border: none; padding: 6px; border-radius: 6px; font-size: 9px; font-weight: 700; cursor: pointer; text-align: center; box-shadow: var(--shadow-sm);">✕ Fail</button>
            </div>
          ` : ''}

          ${isNext ? `
            <div style="margin-top: 6px;">
              <button class="btn-app-action btn-arrive-stop" data-stop-id="${stopId}" data-arrival-time="${arrTime}" style="width: 100%; background: var(--primary); color: white; border: none; padding: 6px; border-radius: 6px; font-size: 9px; font-weight: 700; cursor: pointer; text-align: center; box-shadow: var(--shadow-sm);">⚡ Arrive at Destination</button>
            </div>
          ` : ''}
        </div>
      `;
    });

    html += `</div>`;
    container.innerHTML = html;

    // Bind inner actions
    container.querySelectorAll('.btn-arrive-stop').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const targetTime = Number(btn.dataset.arrivalTime);
        this.t_sim = targetTime;
        if (this.slider) this.slider.value = String(this.t_sim);
        this.updateTimeDisplay();
        this.updateFrame();
        this.app.toast('Driver Status Update', `Driver arrived at Stop #${btn.dataset.stopId}`, 'info');
      });
    });

    container.querySelectorAll('.btn-complete-stop').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const stopId = Number(btn.dataset.stopId);
        const fleetVehicle = this.app.state.fleet?.[selectedVehId];
        const driverName = fleetVehicle ? fleetVehicle.driver : `Driver #${Number(selectedVehId) + 1}`;
        
        const targetRoute = algoResult.routes.find(r => r.vehicle_id === Number(selectedVehId));
        const stopIdx = targetRoute.stops.indexOf(stopId);
        const step = targetRoute.schedule[stopIdx];
        
        const offset = this.delayOffsets.get(Number(selectedVehId)) || 0;
        const activeIncident = this.incidents.get(Number(selectedVehId));
        let activeDelay = offset;
        if (activeIncident && this.t_sim >= activeIncident.triggerTime) {
          if (activeIncident.type === 'breakdown') activeDelay += (this.t_sim - activeIncident.triggerTime);
          else if (activeIncident.type === 'traffic') activeDelay += (this.t_sim - activeIncident.triggerTime) * 0.67;
        }

        const compTime = step ? step.departure + activeDelay : this.t_sim;
        const arrTime = step ? step.arrival + activeDelay : this.t_sim;

        this.showPodModal({
          stopId: stopId,
          driverName: driverName,
          timeStr: this.formatTimeStr(compTime),
          due: arrTime <= Number(this.app.state.customers[stopId]?.due || 1000) ? 'On Time' : 'Delayed',
          name: this.app.state.customers[stopId]?.name || `Stop #${stopId}`
        });

        if (step) {
          this.t_sim = compTime;
          if (this.slider) this.slider.value = String(this.t_sim);
          this.updateTimeDisplay();
          this.updateFrame();
        }
      });
    });

    container.querySelectorAll('.btn-fail-stop').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const stopId = btn.dataset.stopId;
        this.app.toast('Delivery Failed', `Stop #${stopId} marked as FAILED. Reason: Customer not home.`, 'error');
        this.addAlert('error', `❌ Delivery Failed: Stop #${stopId} marked as FAILED by ${this.getDriverName(selectedVehId)}.`);
        this.t_sim += 15;
        if (this.slider) this.slider.value = String(this.t_sim);
        this.updateTimeDisplay();
        this.updateFrame();
      });
    });
  }
}
