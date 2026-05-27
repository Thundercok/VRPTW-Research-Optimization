/* ===================================================================
   GANTT CHART — Driver Schedule Timeline Controller
   =================================================================== */

const ROW_HEIGHT = 38;
const LABEL_WIDTH = 140;
const HEADER_HEIGHT = 28;
const ROW_BAR_HEIGHT = 20;

export class GanttController {
  constructor(app) {
    this.app = app;
    this.panel = null;
    this.canvas = null;
    this.ctx = null;
    this.tooltip = null;
    
    this.isCollapsed = false;
    this.activeAlgo = 'ddqn';
    this.result = null;
    this.simTime = 0;
    this.maxTime = 240;
    this.scaleX = 2.5; // pixels per minute
    
    this.segments = [];
    this.hoveredSegment = null;
  }

  init() {
    // 1. Create the main panel element
    this.panel = document.createElement('div');
    this.panel.className = 'gantt-panel gantt-entering hidden';
    
    this.panel.innerHTML = `
      <div class="gantt-header" id="gantt-header-clickable">
        <div class="gantt-header-left">
          <span class="gantt-header-title">📊 Driver Schedule (Gantt)</span>
          <span class="gantt-header-badge" id="gantt-badge">DDQN</span>
        </div>
        <div class="gantt-header-right">
          <select class="gantt-algo-select" id="gantt-select-algo"></select>
          <button class="gantt-chevron-btn" id="gantt-btn-chevron" title="Expand/Collapse">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="18 15 12 9 6 15"></polyline>
            </svg>
          </button>
        </div>
      </div>
      <div class="gantt-legend">
        <div class="gantt-legend-item">
          <div class="gantt-legend-swatch travel"></div>
          <span>Travel</span>
        </div>
        <div class="gantt-legend-item">
          <div class="gantt-legend-swatch wait"></div>
          <span>Wait</span>
        </div>
        <div class="gantt-legend-item">
          <div class="gantt-legend-swatch service"></div>
          <span>Service</span>
        </div>
      </div>
      <div class="gantt-canvas-wrap" id="gantt-wrap">
        <canvas id="gantt-canvas-el"></canvas>
      </div>
    `;

    // 2. Create the tooltip element at body level to avoid overflow clipping issues
    this.tooltip = document.createElement('div');
    this.tooltip.className = 'gantt-tooltip';
    document.body.appendChild(this.tooltip);

    // 3. Inject panel after `#view-dispatch .workspace-full`
    const workspaceFull = document.querySelector('#view-dispatch .workspace-full');
    if (workspaceFull) {
      workspaceFull.parentNode.insertBefore(this.panel, workspaceFull.nextSibling);
    }

    // 4. Hook elements
    this.canvas = this.panel.querySelector('#gantt-canvas-el');
    this.ctx = this.canvas.getContext('2d');

    // 5. Setup event listeners
    const header = this.panel.querySelector('#gantt-header-clickable');
    header.addEventListener('click', (e) => {
      if (e.target.closest('#gantt-select-algo') || e.target.closest('.gantt-chevron-btn')) {
        return; // handle select or button click separately
      }
      this.toggleCollapse();
    });

    const chevronBtn = this.panel.querySelector('#gantt-btn-chevron');
    chevronBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleCollapse();
    });

    const select = this.panel.querySelector('#gantt-select-algo');
    select.addEventListener('change', (e) => {
      const selectedAlgo = e.target.value;
      const radio = document.querySelector(`input[name="map_view"][value="${selectedAlgo}"]`);
      if (radio) {
        radio.checked = true;
        radio.dispatchEvent(new Event('change'));
      }
    });

    this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    this.canvas.addEventListener('mouseleave', () => this.handleMouseLeave());

    window.addEventListener('resize', () => {
      if (this.result && !this.panel.classList.contains('hidden')) {
        this.resizeAndDraw();
      }
    });

    // Create offscreen patterns for Travel and Wait fills
    this.createFillPatterns();
  }

  createFillPatterns() {
    // 1. Travel stripe pattern (45deg lines)
    this.travelPatternCanvas = document.createElement('canvas');
    this.travelPatternCanvas.width = 10;
    this.travelPatternCanvas.height = 10;
    const tCtx = this.travelPatternCanvas.getContext('2d');
    tCtx.strokeStyle = 'rgba(100, 116, 139, 0.4)';
    tCtx.lineWidth = 1.8;
    tCtx.beginPath();
    tCtx.moveTo(0, 10);
    tCtx.lineTo(10, 0);
    tCtx.stroke();

    // 2. Wait dot pattern
    this.waitPatternCanvas = document.createElement('canvas');
    this.waitPatternCanvas.width = 6;
    this.waitPatternCanvas.height = 6;
    const wCtx = this.waitPatternCanvas.getContext('2d');
    wCtx.fillStyle = '#f59e0b';
    wCtx.beginPath();
    wCtx.arc(3, 3, 1.2, 0, 2 * Math.PI);
    wCtx.fill();
  }

  toggleCollapse() {
    this.isCollapsed = !this.isCollapsed;
    if (this.isCollapsed) {
      this.panel.classList.add('collapsed');
    } else {
      this.panel.classList.remove('collapsed');
      // Redraw since canvas might have been hidden/distorted
      setTimeout(() => this.resizeAndDraw(), 100);
    }
  }

  render(result, activeAlgo) {
    this.result = result;
    this.activeAlgo = activeAlgo || 'ddqn';

    if (!result || Object.keys(result).length === 0) {
      this.panel.classList.add('hidden');
      return;
    }

    this.panel.classList.remove('hidden');
    // Smooth fade in
    setTimeout(() => {
      this.panel.classList.remove('gantt-entering');
    }, 50);

    const algoResult = this.result[this.activeAlgo];
    if (!algoResult || !algoResult.routes) {
      return;
    }

    // Update Dropdown Options
    const select = this.panel.querySelector('#gantt-select-algo');
    const labels = {
      ddqn: 'Hybrid DDQN (Transfer)',
      alns: 'ALNS Base',
      ortools: 'OR-Tools',
      hybrid_fixed: 'Hybrid Fixed',
      hybrid_ddqn: 'Hybrid DDQN (Random)',
      hybrid_ddqn_transfer_rc1: 'Hybrid DDQN (RC1)',
      hybrid_ddqn_transfer_dr: 'Hybrid DDQN (DR)',
      hybrid: 'Hybrid DDQN'
    };

    select.innerHTML = Object.keys(result).map(key => 
      `<option value="${key}" ${key === this.activeAlgo ? 'selected' : ''}>${labels[key] || key}</option>`
    ).join('');

    const badge = this.panel.querySelector('#gantt-badge');
    badge.textContent = (labels[this.activeAlgo] || this.activeAlgo).toUpperCase();

    // Calculate max time duration for scheduling
    let maxTime = 120;
    algoResult.routes.forEach(route => {
      if (route.schedule && route.schedule.length > 0) {
        const lastStep = route.schedule[route.schedule.length - 1];
        if (lastStep && lastStep.arrival > maxTime) {
          maxTime = lastStep.arrival;
        }
      }
    });
    this.maxTime = Math.ceil(maxTime + 30); // 30 min buffer

    this.resizeAndDraw();
  }

  resizeAndDraw() {
    const wrap = this.panel.querySelector('#gantt-wrap');
    if (!wrap) return;
    
    const containerWidth = wrap.clientWidth;
    // Calculate pixels per minute (at least 2.2px/min, stretching to container if shorter)
    this.scaleX = Math.max(2.2, (containerWidth - LABEL_WIDTH - 24) / this.maxTime);

    const algoResult = this.result?.[this.activeAlgo];
    const numVehicles = algoResult ? algoResult.routes.length : 0;
    const totalWidth = LABEL_WIDTH + this.maxTime * this.scaleX;
    const totalHeight = HEADER_HEIGHT + numVehicles * ROW_HEIGHT + 8;

    // Handle high density displays (DPR)
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = totalWidth * dpr;
    this.canvas.height = totalHeight * dpr;
    this.canvas.style.width = `${totalWidth}px`;
    this.canvas.style.height = `${totalHeight}px`;
    
    this.ctx.resetTransform();
    this.ctx.scale(dpr, dpr);

    this.draw();
  }

  draw() {
    const algoResult = this.result?.[this.activeAlgo];
    if (!algoResult || !algoResult.routes) return;

    const width = this.canvas.width / (window.devicePixelRatio || 1);
    const height = this.canvas.height / (window.devicePixelRatio || 1);

    this.ctx.clearRect(0, 0, width, height);

    // 1. Draw Grid lines & X-axis Header
    this.ctx.fillStyle = '#f8fafc'; // light grid header
    this.ctx.fillRect(LABEL_WIDTH, 0, width - LABEL_WIDTH, HEADER_HEIGHT);
    
    // Bottom border of axis header
    this.ctx.strokeStyle = 'var(--border)';
    this.ctx.lineWidth = 1;
    this.ctx.beginPath();
    this.ctx.moveTo(0, HEADER_HEIGHT);
    this.ctx.lineTo(width, HEADER_HEIGHT);
    this.ctx.stroke();

    for (let t = 0; t <= this.maxTime; t += 30) {
      const x = LABEL_WIDTH + t * this.scaleX;

      // Vertical line
      this.ctx.strokeStyle = 'rgba(228, 232, 240, 0.7)';
      this.ctx.lineWidth = 1;
      this.ctx.beginPath();
      this.ctx.moveTo(x, HEADER_HEIGHT);
      this.ctx.lineTo(x, height);
      this.ctx.stroke();

      // Tick labels
      this.ctx.fillStyle = 'var(--text-muted)';
      this.ctx.font = '600 9.5px var(--font-main, sans-serif)';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(this.formatTime(t), x, HEADER_HEIGHT / 2);
    }

    // 2. Draw Lane content & Rows
    this.segments = [];

    algoResult.routes.forEach((route, idx) => {
      const y = HEADER_HEIGHT + idx * ROW_HEIGHT;
      const barY = y + (ROW_HEIGHT - ROW_BAR_HEIGHT) / 2;

      // Row separator
      this.ctx.strokeStyle = 'var(--border)';
      this.ctx.lineWidth = 1;
      this.ctx.beginPath();
      this.ctx.moveTo(0, y + ROW_HEIGHT);
      this.ctx.lineTo(width, y + ROW_HEIGHT);
      this.ctx.stroke();

      // Driver Name Label
      const fleetVehicle = this.app.state.fleet?.[route.vehicle_id] || this.app.state.fleet?.find(v => v.id === route.vehicle_id);
      const driverName = fleetVehicle ? fleetVehicle.driver : `Driver #${route.vehicle_id + 1}`;
      
      this.ctx.fillStyle = '#f8fafc'; // label block background
      this.ctx.fillRect(0, y, LABEL_WIDTH, ROW_HEIGHT);
      
      // Vertical border separating labels and timeline
      this.ctx.strokeStyle = 'var(--border)';
      this.ctx.lineWidth = 1;
      this.ctx.beginPath();
      this.ctx.moveTo(LABEL_WIDTH, y);
      this.ctx.lineTo(LABEL_WIDTH, y + ROW_HEIGHT);
      this.ctx.stroke();

      this.ctx.fillStyle = 'var(--text-main)';
      this.ctx.font = 'bold 11px var(--font-main, sans-serif)';
      this.ctx.textAlign = 'left';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(driverName, 12, y + ROW_HEIGHT / 2);

      // Render Schedule Segments
      if (!route.schedule || route.schedule.length === 0) return;
      
      const routeColor = this.colorForRoute(idx);
      let t_last = 0;

      route.schedule.forEach((step, stepIdx) => {
        const isDepot = step.customer_id === 0;

        // A. Travel Segment: t_last -> step.arrival
        const travelDur = step.arrival - t_last;
        if (travelDur > 0) {
          const x = LABEL_WIDTH + t_last * this.scaleX;
          const w = travelDur * this.scaleX;

          // Fill Travel background translucent route color
          this.ctx.fillStyle = routeColor;
          this.ctx.globalAlpha = 0.12;
          this.ctx.fillRect(x, barY, w, ROW_BAR_HEIGHT);

          // Fill hatch pattern overlay
          this.ctx.globalAlpha = 0.35;
          const travelPattern = this.ctx.createPattern(this.travelPatternCanvas, 'repeat');
          this.ctx.fillStyle = travelPattern;
          this.ctx.fillRect(x, barY, w, ROW_BAR_HEIGHT);
          this.ctx.globalAlpha = 1.0;

          this.segments.push({
            type: 'travel',
            x1: x,
            x2: x + w,
            y1: barY,
            y2: barY + ROW_BAR_HEIGHT,
            driverName,
            data: {
              from: t_last,
              to: step.arrival,
              destination: isDepot ? 'Depot' : (step.name || `Stop #${step.customer_id}`)
            }
          });
        }

        // B. Wait Segment (only if not depot and wait time > 0)
        if (!isDepot && step.service_start > step.arrival) {
          const waitDur = step.service_start - step.arrival;
          const x = LABEL_WIDTH + step.arrival * this.scaleX;
          const w = waitDur * this.scaleX;

          // Light amber background
          this.ctx.fillStyle = '#f59e0b';
          this.ctx.globalAlpha = 0.12;
          this.ctx.fillRect(x, barY, w, ROW_BAR_HEIGHT);

          // Dot pattern overlay
          this.ctx.globalAlpha = 0.55;
          const waitPattern = this.ctx.createPattern(this.waitPatternCanvas, 'repeat');
          this.ctx.fillStyle = waitPattern;
          this.ctx.fillRect(x, barY, w, ROW_BAR_HEIGHT);
          this.ctx.globalAlpha = 1.0;

          this.segments.push({
            type: 'wait',
            x1: x,
            x2: x + w,
            y1: barY,
            y2: barY + ROW_BAR_HEIGHT,
            driverName,
            data: {
              from: step.arrival,
              to: step.service_start,
              waitTime: waitDur,
              stopName: step.name || `Stop #${step.customer_id}`
            }
          });
        }

        // C. Service Segment (only for customer stops)
        if (!isDepot) {
          const x = LABEL_WIDTH + step.service_start * this.scaleX;
          const w = (step.departure - step.service_start) * this.scaleX;

          // Solid block of route color
          this.ctx.fillStyle = routeColor;
          this.ctx.globalAlpha = 0.85;
          this.ctx.fillRect(x, barY, w, ROW_BAR_HEIGHT);
          
          this.ctx.strokeStyle = routeColor;
          this.ctx.lineWidth = 1;
          this.ctx.strokeRect(x, barY, w, ROW_BAR_HEIGHT);
          this.ctx.globalAlpha = 1.0;

          // Draw stop label inside if space fits
          const stopLabel = `#${step.customer_id}`;
          this.ctx.fillStyle = '#ffffff';
          this.ctx.font = 'bold 8.5px var(--font-data, monospace)';
          this.ctx.textAlign = 'center';
          this.ctx.textBaseline = 'middle';
          const textWidth = this.ctx.measureText(stopLabel).width;
          if (textWidth + 6 < w) {
            this.ctx.fillText(stopLabel, x + w / 2, barY + ROW_BAR_HEIGHT / 2);
          }

          this.segments.push({
            type: 'service',
            x1: x,
            x2: x + w,
            y1: barY,
            y2: barY + ROW_BAR_HEIGHT,
            driverName,
            data: {
              customerId: step.customer_id,
              stopName: step.name || `Stop #${step.customer_id}`,
              from: step.service_start,
              to: step.departure,
              duration: step.service_duration
            }
          });
        }

        t_last = step.departure;
      });
    });

    // 3. Draw Vertical Time Cursor (Simulation sync)
    if (this.simTime > 0) {
      const cursorX = LABEL_WIDTH + this.simTime * this.scaleX;
      
      this.ctx.strokeStyle = '#dc2626'; // var(--danger)
      this.ctx.lineWidth = 1.5;
      this.ctx.setLineDash([3, 3]);
      this.ctx.beginPath();
      this.ctx.moveTo(cursorX, 0);
      this.ctx.lineTo(cursorX, height);
      this.ctx.stroke();
      this.ctx.setLineDash([]); // reset

      // Cursor circle anchor
      this.ctx.fillStyle = '#dc2626';
      this.ctx.beginPath();
      this.ctx.arc(cursorX, HEADER_HEIGHT, 4.5, 0, 2 * Math.PI);
      this.ctx.fill();
    }
  }

  setSimTime(t) {
    this.simTime = t;
    if (this.canvas && !this.panel.classList.contains('hidden')) {
      this.draw();
    }
  }

  handleMouseMove(e) {
    if (!this.canvas) return;

    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Find if hovering over a segment
    const hovered = this.segments.find(seg => 
      mx >= seg.x1 && mx <= seg.x2 && my >= seg.y1 && my <= seg.y2
    );

    if (hovered) {
      this.hoveredSegment = hovered;
      
      let html = `<div class="gantt-tooltip-title">${hovered.driverName}</div>`;

      if (hovered.type === 'travel') {
        html += `
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Activity:</span><span class="gantt-tooltip-value">🚚 Traveling</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Heading:</span><span class="gantt-tooltip-value">${hovered.data.destination}</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Depart:</span><span class="gantt-tooltip-value">${this.formatClockTime(hovered.data.from)}</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Arrive:</span><span class="gantt-tooltip-value">${this.formatClockTime(hovered.data.to)}</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Duration:</span><span class="gantt-tooltip-value">${Math.round(hovered.data.to - hovered.data.from)} mins</span></div>
        `;
      } else if (hovered.type === 'wait') {
        html += `
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Activity:</span><span class="gantt-tooltip-value" style="color:#f59e0b">⏳ Waiting</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Location:</span><span class="gantt-tooltip-value">${hovered.data.stopName}</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Arrived:</span><span class="gantt-tooltip-value">${this.formatClockTime(hovered.data.from)}</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Start Work:</span><span class="gantt-tooltip-value">${this.formatClockTime(hovered.data.to)}</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Idle Time:</span><span class="gantt-tooltip-value">${Math.round(hovered.data.waitTime)} mins</span></div>
        `;
      } else if (hovered.type === 'service') {
        html += `
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Activity:</span><span class="gantt-tooltip-value" style="color:var(--success)">🔧 Dropoff/Service</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Customer:</span><span class="gantt-tooltip-value">#${hovered.data.customerId} - ${hovered.data.stopName}</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Start:</span><span class="gantt-tooltip-value">${this.formatClockTime(hovered.data.from)}</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Complete:</span><span class="gantt-tooltip-value">${this.formatClockTime(hovered.data.to)}</span></div>
          <div class="gantt-tooltip-row"><span class="gantt-tooltip-label">Duration:</span><span class="gantt-tooltip-value">${Math.round(hovered.data.duration)} mins</span></div>
        `;
      }

      this.tooltip.innerHTML = html;
      this.tooltip.classList.add('visible');
      
      // Position tooltip near cursor but handle window boundaries
      const tRect = this.tooltip.getBoundingClientRect();
      let left = e.clientX + 14;
      let top = e.clientY + 14;

      if (left + tRect.width > window.innerWidth) {
        left = e.clientX - tRect.width - 10;
      }
      if (top + tRect.height > window.innerHeight) {
        top = e.clientY - tRect.height - 10;
      }

      this.tooltip.style.left = `${left}px`;
      this.tooltip.style.top = `${top}px`;
    } else {
      this.handleMouseLeave();
    }
  }

  handleMouseLeave() {
    this.hoveredSegment = null;
    if (this.tooltip) {
      this.tooltip.classList.remove('visible');
    }
  }

  formatTime(minutes) {
    const totalMin = 8 * 60 + minutes; // starts at 08:00 AM
    const h = Math.floor(totalMin / 60) % 24;
    const m = Math.floor(totalMin % 60);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }

  formatClockTime(minutes) {
    const totalMin = 8 * 60 + minutes;
    const rawH = Math.floor(totalMin / 60) % 24;
    const endM = Math.floor(totalMin % 60);
    const period = rawH >= 12 ? 'PM' : 'AM';
    const endH = rawH % 12 === 0 ? 12 : rawH % 12;
    return `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')} ${period}`;
  }

  colorForRoute(routeIndex) {
    const palette = ['#0ea5e9', '#2563eb', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#f43f5e', '#14b8a6'];
    if (routeIndex < palette.length) return palette[routeIndex];
    const hue = (routeIndex * 137.508) % 360;
    return `hsl(${hue},72%,44%)`;
  }

  destroy() {
    if (this.tooltip) this.tooltip.remove();
    if (this.panel) this.panel.remove();
  }
}
