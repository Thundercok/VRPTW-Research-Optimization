export class FleetController {
  constructor(app) {
    this.app = app;
    this.storageKey = 'vrptw_fleet_config';
  }

  init() {
    // Load from localStorage or create defaults based on current state.vehicles
    const loaded = localStorage.getItem(this.storageKey);
    if (loaded) {
      try {
        this.app.state.fleet = JSON.parse(loaded);
      } catch (e) {
        console.warn('[FleetController] Failed to parse saved fleet, resetting:', e);
        this.app.state.fleet = null;
      }
    }

    if (!this.app.state.fleet || !Array.isArray(this.app.state.fleet)) {
      this.app.state.fleet = [];
    }

    this.syncFleetSize(Number(this.app.state.vehicles));

    // Listen to header vehicles slider adjustments
    const vehiclesSlider = document.getElementById('vehicles-slider');
    if (vehiclesSlider) {
      const handleInput = (e) => {
        this.syncFleetSize(Number(e.target.value));
      };
      vehiclesSlider.addEventListener('change', handleInput);
      vehiclesSlider.addEventListener('input', handleInput);
    }
  }

  syncFleetSize(size) {
    const fleet = this.app.state.fleet;
    const currentCapacity = Number(this.app.state.capacity) || 120;

    if (fleet.length < size) {
      // Expand fleet
      for (let i = fleet.length; i < size; i++) {
        fleet.push({
          id: i,
          driver: `Driver #${i + 1}`,
          capacity: currentCapacity,
          speed: 1.0,
          shiftStart: '08:00',
          shiftEnd: '17:00',
          breakStart: '12:00',
          breakDuration: 30,
          skills: 'None',
          status: 'Active',
        });
      }
    } else if (fleet.length > size) {
      // Shrink fleet
      fleet.splice(size);
    }

    this.app.state.fleet = fleet;
    this.save();
    this.render();
  }

  save() {
    localStorage.setItem(this.storageKey, JSON.stringify(this.app.state.fleet));
  }

  render() {
    const container = document.getElementById('view-fleet');
    if (!container || container.classList.contains('hidden')) return;

    const activeVehicles = this.app.state.fleet.filter((v) => v.status === 'Active');
    const totalCapacity = activeVehicles.reduce((sum, v) => sum + Number(v.capacity), 0);
    const avgSpeed =
      activeVehicles.length > 0
        ? (activeVehicles.reduce((sum, v) => sum + Number(v.speed), 0) / activeVehicles.length).toFixed(2)
        : '0.00';
    const maintenanceCount = this.app.state.fleet.filter((v) => v.status === 'Maintenance').length;

    let html = `
      <div class="fleet-view-container">
        <div class="fleet-view-header">
          <div>
            <h2>Fleet Operations & Shift Schedules</h2>
            <p class="section-desc">Define individual vehicle capacities, operating speeds, driver names, and shift constraint rules. These parameters govern route eligibility, travel times, and vehicle capacity checks.</p>
          </div>
          <div class="fleet-actions-row">
            <button id="btn-fleet-add" class="btn-primary">+ Add Vehicle</button>
            <button id="btn-fleet-reset" class="btn-secondary">Reset to Defaults</button>
          </div>
        </div>

        <!-- Fleet KPI Row -->
        <section class="kpi-row" style="margin-top: 16px; border: 1px solid var(--border); border-radius: var(--r); background: var(--bg-surface); grid-template-columns: repeat(4, 1fr);">
          <div class="kpi-card" style="border-right: 1px solid var(--border);">
            <div class="kpi-title">Active Fleet Size</div>
            <div class="kpi-value">${activeVehicles.length} / ${this.app.state.fleet.length}</div>
            <div class="kpi-sub">Vehicles ready for dispatch</div>
          </div>
          <div class="kpi-card" style="border-right: 1px solid var(--border);">
            <div class="kpi-title">Total Active Capacity</div>
            <div class="kpi-value">${totalCapacity}</div>
            <div class="kpi-sub">Sum of active vehicle loads</div>
          </div>
          <div class="kpi-card" style="border-right: 1px solid var(--border);">
            <div class="kpi-title">Average Speed Multiplier</div>
            <div class="kpi-value">${avgSpeed}x</div>
            <div class="kpi-sub">Efficiency across active drivers</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-title">Fleet Status Check</div>
            <div class="kpi-value ${activeVehicles.length > 0 ? 'highlight-emerald' : 'text-danger'}" style="font-weight: 700;">
              ${activeVehicles.length > 0 ? 'READY' : 'NO VEHICLES'}
            </div>
            <div class="kpi-sub">${maintenanceCount} vehicle${maintenanceCount !== 1 ? 's' : ''} in maintenance</div>
          </div>
        </section>

        <div class="saas-card" style="margin-top: 16px; overflow: auto; flex: 1; border: 1px solid var(--border); border-radius: var(--r);">
          <table class="saas-table fleet-config-table" style="width: 100%; border-collapse: collapse;">
            <thead>
              <tr>
                <th style="width: 60px;">ID</th>
                <th>Driver Name</th>
                <th style="width: 110px;">Capacity</th>
                <th style="width: 90px;">Speed</th>
                <th style="width: 110px;">Shift Start</th>
                <th style="width: 110px;">Shift End</th>
                <th style="width: 110px;">Break Start</th>
                <th style="width: 90px;">Break</th>
                <th style="width: 130px;">Driver Skills</th>
                <th style="width: 120px;">Status</th>
                <th style="width: 70px; text-align: center;">Actions</th>
              </tr>
            </thead>
            <tbody>
    `;

    this.app.state.fleet.forEach((veh, index) => {
      let statusColor = 'var(--text-main)';
      if (veh.status === 'Active') statusColor = 'var(--success)';
      else if (veh.status === 'Maintenance') statusColor = 'var(--orange)';
      else if (veh.status === 'Inactive') statusColor = 'var(--danger)';

      html += `
        <tr data-index="${index}">
          <td><strong class="font-mono">#${veh.id + 1}</strong></td>
          <td>
            <input type="text" class="table-inline-input fleet-input" data-field="driver" value="${this.app.escapeHtml(veh.driver)}" placeholder="Driver Name" />
          </td>
          <td>
            <input type="number" class="table-inline-input fleet-input num" data-field="capacity" value="${veh.capacity}" min="1" max="10000" />
          </td>
          <td>
            <input type="number" class="table-inline-input fleet-input num" data-field="speed" value="${veh.speed}" step="0.1" min="0.5" max="3.0" />
          </td>
          <td>
            <input type="time" class="table-inline-input fleet-input" data-field="shiftStart" value="${veh.shiftStart}" />
          </td>
          <td>
            <input type="time" class="table-inline-input fleet-input" data-field="shiftEnd" value="${veh.shiftEnd}" />
          </td>
          <td>
            <input type="time" class="table-inline-input fleet-input" data-field="breakStart" value="${veh.breakStart}" />
          </td>
          <td>
            <input type="number" class="table-inline-input fleet-input num" data-field="breakDuration" value="${veh.breakDuration}" min="0" max="120" />
          </td>
          <td>
            <select class="table-inline-input fleet-input" data-field="skills" style="font-weight: 500;">
              <option value="None" ${veh.skills === 'None' ? 'selected' : ''}>None (Standard)</option>
              <option value="Refrigerated" ${veh.skills === 'Refrigerated' ? 'selected' : ''}>Refrigerated</option>
              <option value="Hazmat" ${veh.skills === 'Hazmat' ? 'selected' : ''}>Hazmat</option>
            </select>
          </td>
          <td>
            <select class="table-inline-input fleet-input" data-field="status" style="color: ${statusColor}; font-weight: 600;">
              <option value="Active" style="color: var(--success); font-weight: 600;" ${veh.status === 'Active' ? 'selected' : ''}>Active</option>
              <option value="Maintenance" style="color: var(--orange); font-weight: 600;" ${veh.status === 'Maintenance' ? 'selected' : ''}>Maintenance</option>
              <option value="Inactive" style="color: var(--danger); font-weight: 600;" ${veh.status === 'Inactive' ? 'selected' : ''}>Inactive</option>
            </select>
          </td>
          <td style="text-align: center;">
            <button class="btn-text btn-danger btn-fleet-delete" data-index="${index}" title="Delete vehicle">✕</button>
          </td>
        </tr>
      `;
    });

    if (this.app.state.fleet.length === 0) {
      html += `
        <tr>
          <td colspan="10" class="text-center text-muted" style="padding: 32px;">
            No vehicles in fleet. Click "+ Add Vehicle" to register a driver.
          </td>
        </tr>
      `;
    }

    html += `
            </tbody>
          </table>
        </div>
      </div>
    `;

    container.innerHTML = html;

    // Bind dynamic events inside the table
    const inputs = container.querySelectorAll('.fleet-input');
    inputs.forEach((input) => {
      input.addEventListener('change', (e) => {
        const tr = e.target.closest('tr');
        const index = Number(tr.dataset.index);
        const field = e.target.dataset.field;
        let val = e.target.value;

        if (field === 'capacity') {
          val = Math.max(1, Number(val) || 120);
        } else if (field === 'speed') {
          val = Math.max(0.1, Number(val) || 1.0);
        } else if (field === 'breakDuration') {
          val = Math.max(0, Number(val) || 0);
        }

        // Inline validation for shift hours and break times
        const veh = this.app.state.fleet[index];
        const updatedVeh = { ...veh, [field]: val };

        if (field === 'shiftStart' || field === 'shiftEnd') {
          const start = updatedVeh.shiftStart;
          const end = updatedVeh.shiftEnd;
          if (start && end && start >= end) {
            this.app.toast(
              'Invalid Shift Window',
              `Shift end (${end}) must be after shift start (${start}) for Driver #${index + 1}.`,
              'error'
            );
            e.target.classList.add('input-error');
            e.target.value = veh[field]; // revert input value
            return;
          }
        }

        if (field === 'breakStart' || field === 'shiftStart' || field === 'shiftEnd') {
          const brk = updatedVeh.breakStart;
          const start = updatedVeh.shiftStart;
          const end = updatedVeh.shiftEnd;
          if (brk && start && end && (brk < start || brk > end)) {
            this.app.toast(
              'Invalid Break Time',
              `Lunch break (${brk}) must fall within shift hours (${start} - ${end}) for Driver #${index + 1}.`,
              'error'
            );
            e.target.classList.add('input-error');
            e.target.value = veh[field]; // revert input value
            return;
          }
        }

        this.app.state.fleet[index][field] = val;
        this.save();

        // Sync back to main slider if capacity was edited
        if (field === 'capacity') {
          const maxCap = Math.max(...this.app.state.fleet.map((v) => v.capacity));
          this.app.state.capacity = maxCap;
          const mainCapSlider = document.getElementById('capacity-slider');
          if (mainCapSlider) {
            mainCapSlider.value = String(maxCap);
            const mainCapVal = document.getElementById('capacity-value');
            if (mainCapVal) mainCapVal.textContent = String(maxCap);
          }
        }

        // Re-render to dynamically update KPIs and color styling
        this.render();
      });
    });

    // Bind Add button
    const btnAdd = container.querySelector('#btn-fleet-add');
    btnAdd?.addEventListener('click', () => {
      const nextId = this.app.state.fleet.length;
      const currentCapacity = Number(this.app.state.capacity) || 120;
      this.app.state.fleet.push({
        id: nextId,
        driver: `Driver #${nextId + 1}`,
        capacity: currentCapacity,
        speed: 1.0,
        shiftStart: '08:00',
        shiftEnd: '17:00',
        breakStart: '12:00',
        breakDuration: 30,
        skills: 'None',
        status: 'Active',
      });
      this.save();

      const size = this.app.state.fleet.length;
      this.app.state.vehicles = size;
      const mainVehSlider = document.getElementById('vehicles-slider');
      if (mainVehSlider) {
        mainVehSlider.value = String(size);
        const mainVehVal = document.getElementById('vehicles-value');
        if (mainVehVal) mainVehVal.textContent = String(size);
      }

      this.render();
    });

    // Bind Reset button
    const btnReset = container.querySelector('#btn-fleet-reset');
    btnReset?.addEventListener('click', () => {
      if (confirm('Reset fleet configuration to standard defaults?')) {
        this.app.state.fleet = null;
        this.init();
        this.render();
        this.app.toast('Fleet Reset', 'Fleet has been reset to defaults.', 'ok');
      }
    });

    // Bind Delete buttons
    const deleteBtns = container.querySelectorAll('.btn-fleet-delete');
    deleteBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const index = Number(e.target.dataset.index);
        this.app.state.fleet.splice(index, 1);
        // Re-index remaining
        this.app.state.fleet.forEach((v, idx) => (v.id = idx));
        this.save();

        const size = this.app.state.fleet.length;
        this.app.state.vehicles = size;
        const mainVehSlider = document.getElementById('vehicles-slider');
        if (mainVehSlider) {
          mainVehSlider.value = String(size);
          const mainVehVal = document.getElementById('vehicles-value');
          if (mainVehVal) mainVehVal.textContent = String(size);
        }

        this.render();
      });
    });
  }
}
