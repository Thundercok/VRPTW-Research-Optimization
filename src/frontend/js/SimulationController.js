export class SimulationController {
  constructor(app) {
    this.app = app;
    this.isPlaying = false;
    this.t_sim = 0;
    this.speed = 10; // default to 10x
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
  }

  start(maxTime) {
    this.maxTime = Math.max(1, maxTime || 240);
    this.t_sim = 0;
    this.isPlaying = false;
    
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
    if (visible) {
      this.controlPanel?.classList.remove('hidden');
      this.vehicleList?.classList.remove('hidden');
    } else {
      this.controlPanel?.classList.add('hidden');
      this.vehicleList?.classList.add('hidden');
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

  updateFrame() {
    const result = this.app.state.lastResult;
    if (!result) return;

    // Determine current view (DDQN or ALNS)
    const mapModeElement = document.querySelector('input[name="map_view"]:checked');
    const isDdqn = mapModeElement ? (mapModeElement.value === 'ddqn') : true;
    const algoResult = isDdqn ? result.ddqn : result.alns;

    if (!algoResult || !algoResult.routes) return;

    // Update vehicle markers positions on Map
    this.app.mapController.updateSimulation(this.t_sim, algoResult, isDdqn);

    // Update status panel in the UI
    this.updateStatusPanel(algoResult, isDdqn);
  }

  updateStatusPanel(algoResult, isDdqn) {
    if (!this.vehicleList) return;
    
    let html = '';
    const routeCapacity = Number(this.app.state.lastRunFleet?.capacity ?? this.app.state.capacity);

    algoResult.routes.forEach((route) => {
      const state = this.app.mapController.getVehicleStateAtTime(route, this.t_sim);
      const stopsDone = route.stops.filter((stopId, idx) => {
        const step = route.schedule[idx];
        return step && this.t_sim >= step.departure;
      }).length;
      const totalStops = route.stops.length;
      
      const percent = totalStops > 0 ? Math.round((stopsDone / totalStops) * 100) : 100;
      const loadPercent = Math.round((route.load / routeCapacity) * 100);
      
      // Determine status class
      let statusClass = 'sim-status-parked';
      if (state.status === 'Traveling') statusClass = 'sim-status-traveling';
      if (state.status === 'Waiting') statusClass = 'sim-status-waiting';
      if (state.status === 'Servicing') statusClass = 'sim-status-servicing';
      if (state.status === 'Returning') statusClass = 'sim-status-returning';
      
      const color = isDdqn ? '#10b981' : '#3b82f6';

      html += `
        <div class="sim-vehicle-card">
          <div class="sim-card-header">
            <span class="sim-veh-id" style="border-left: 3px solid ${color}; padding-left: 8px;">Vehicle #${route.vehicle_id}</span>
            <span class="sim-badge ${statusClass}">${state.status}</span>
          </div>
          <div class="sim-card-body">
            <p class="sim-detail-text">${state.detail}</p>
            <div class="sim-stat-row">
              <span>Stops: ${stopsDone}/${totalStops}</span>
              <span>Load: ${route.load}/${routeCapacity} (${loadPercent}%)</span>
            </div>
            <div class="sim-progress-bar">
              <div class="sim-progress-fill" style="width: ${percent}%; background-color: ${color};"></div>
            </div>
          </div>
        </div>
      `;
    });

    this.vehicleList.innerHTML = html;
  }
}
