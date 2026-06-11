import React from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export default function FleetConfigView() {
  const { state, updateState, toast } = useAppContext();

  const fleet = state.fleet || [];
  const activeVehicles = fleet.filter((v) => v.status === 'Active');
  const totalCapacity = activeVehicles.reduce((sum, v) => sum + Number(v.capacity), 0);
  const avgSpeed =
    activeVehicles.length > 0
      ? (activeVehicles.reduce((sum, v) => sum + Number(v.speed), 0) / activeVehicles.length).toFixed(2)
      : '0.00';
  const maintenanceCount = fleet.filter((v) => v.status === 'Maintenance').length;

  const saveFleet = (newFleet) => {
    localStorage.setItem('vrptw_fleet_config', JSON.stringify(newFleet));
    updateState({ fleet: newFleet });
  };

  const handleFieldChange = (index, field, val) => {
    const updatedFleet = [...fleet];
    const originalValue = updatedFleet[index][field];

    if (field === 'capacity') {
      val = Math.max(1, Number(val) || 120);
    } else if (field === 'speed') {
      val = Math.max(0.1, Number(val) || 1.0);
    } else if (field === 'breakDuration') {
      val = Math.max(0, Number(val) || 0);
    }

    const updatedVehicle = { ...updatedFleet[index], [field]: val };

    // Validation checks
    if (field === 'shiftStart' || field === 'shiftEnd') {
      const { shiftStart, shiftEnd } = updatedVehicle;
      if (shiftStart && shiftEnd && shiftStart >= shiftEnd) {
        toast(
          'Invalid Shift Window',
          `Shift end (${shiftEnd}) must be after shift start (${shiftStart}) for Driver #${index + 1}.`,
          'error'
        );
        return;
      }
    }

    if (field === 'breakStart' || field === 'shiftStart' || field === 'shiftEnd') {
      const { breakStart, shiftStart, shiftEnd } = updatedVehicle;
      if (breakStart && shiftStart && shiftEnd && (breakStart < shiftStart || breakStart > shiftEnd)) {
        toast(
          'Invalid Break Time',
          `Lunch break (${breakStart}) must fall within shift hours (${shiftStart} - ${shiftEnd}) for Driver #${index + 1}.`,
          'error'
        );
        return;
      }
    }

    updatedFleet[index] = updatedVehicle;
    saveFleet(updatedFleet);

    // Sync capacity back to header configuration if edited
    if (field === 'capacity') {
      const maxCap = Math.max(...updatedFleet.map((v) => v.capacity));
      updateState({ capacity: maxCap });
    }
  };

  const handleAddVehicle = () => {
    const nextId = fleet.length;
    const currentCapacity = Number(state.capacity) || 120;
    const newFleet = [
      ...fleet,
      {
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
      },
    ];
    saveFleet(newFleet);
    updateState({ vehicles: newFleet.length });
  };

  const handleResetDefaults = () => {
    if (window.confirm('Reset fleet configuration to standard defaults?')) {
      const defaultFleet = [];
      const count = Number(state.vehicles) || 4;
      const cap = Number(state.capacity) || 120;
      for (let i = 0; i < count; i++) {
        defaultFleet.push({
          id: i,
          driver: `Driver #${i + 1}`,
          capacity: cap,
          speed: 1.0,
          shiftStart: '08:00',
          shiftEnd: '17:00',
          breakStart: '12:00',
          breakDuration: 30,
          skills: 'None',
          status: 'Active',
        });
      }
      saveFleet(defaultFleet);
      toast('Fleet Reset', 'Fleet has been reset to defaults.', 'ok');
    }
  };

  const handleDeleteVehicle = (index) => {
    const updatedFleet = [...fleet];
    updatedFleet.splice(index, 1);
    // Re-index remaining vehicles
    updatedFleet.forEach((v, idx) => (v.id = idx));
    saveFleet(updatedFleet);
    updateState({ vehicles: updatedFleet.length });
  };

  return (
    <div className="fleet-view-container">
      <div className="fleet-view-header">
        <div>
          <h2>Fleet Operations & Shift Schedules</h2>
          <p className="section-desc">
            Define individual vehicle capacities, operating speeds, driver names, and shift constraint rules.
            These parameters govern route eligibility, travel times, and vehicle capacity checks.
          </p>
        </div>
        <div className="fleet-actions-row">
          <button className="btn-primary" onClick={handleAddVehicle}>
            + Add Vehicle
          </button>
          <button className="btn-secondary" onClick={handleResetDefaults}>
            Reset to Defaults
          </button>
        </div>
      </div>

      {/* Fleet KPI Row */}
      <section
        className="kpi-row"
        style={{
          marginTop: '16px',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r)',
          background: 'var(--bg-surface)',
          gridTemplateColumns: 'repeat(4, 1fr)',
        }}
      >
        <div className="kpi-card" style={{ borderRight: '1px solid var(--border)' }}>
          <div className="kpi-title">Active Fleet Size</div>
          <div className="kpi-value">
            {activeVehicles.length} / {fleet.length}
          </div>
          <div className="kpi-sub">Vehicles ready for dispatch</div>
        </div>
        <div className="kpi-card" style={{ borderRight: '1px solid var(--border)' }}>
          <div className="kpi-title">Total Active Capacity</div>
          <div className="kpi-value">{totalCapacity}</div>
          <div className="kpi-sub">Sum of active vehicle loads</div>
        </div>
        <div className="kpi-card" style={{ borderRight: '1px solid var(--border)' }}>
          <div className="kpi-title">Average Speed Multiplier</div>
          <div className="kpi-value">{avgSpeed}x</div>
          <div className="kpi-sub">Efficiency across active drivers</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-title">Fleet Status Check</div>
          <div
            className={`kpi-value ${
              activeVehicles.length > 0 ? 'highlight-emerald' : 'text-danger'
            }`}
            style={{ fontWeight: 700 }}
          >
            {activeVehicles.length > 0 ? 'READY' : 'NO VEHICLES'}
          </div>
          <div className="kpi-sub">
            {maintenanceCount} vehicle{maintenanceCount !== 1 ? 's' : ''} in maintenance
          </div>
        </div>
      </section>

      <div
        className="saas-card"
        style={{
          marginTop: '16px',
          overflow: 'auto',
          flex: 1,
          border: '1px solid var(--border)',
          borderRadius: 'var(--r)',
        }}
      >
        <table className="saas-table fleet-config-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ width: '60px' }}>ID</th>
              <th>Driver Name</th>
              <th style={{ width: '110px' }}>Capacity</th>
              <th style={{ width: '90px' }}>Speed</th>
              <th style={{ width: '110px' }}>Shift Start</th>
              <th style={{ width: '110px' }}>Shift End</th>
              <th style={{ width: '110px' }}>Break Start</th>
              <th style={{ width: '90px' }}>Break</th>
              <th style={{ width: '130px' }}>Driver Skills</th>
              <th style={{ width: '120px' }}>Status</th>
              <th style={{ width: '70px', textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {fleet.map((veh, index) => {
              let statusColor = 'var(--text-main)';
              if (veh.status === 'Active') statusColor = 'var(--success)';
              else if (veh.status === 'Maintenance') statusColor = 'var(--orange)';
              else if (veh.status === 'Inactive') statusColor = 'var(--danger)';

              return (
                <tr key={index}>
                  <td>
                    <strong className="font-mono">#{veh.id + 1}</strong>
                  </td>
                  <td>
                    <input
                      type="text"
                      className="table-inline-input fleet-input"
                      value={veh.driver}
                      onChange={(e) => handleFieldChange(index, 'driver', e.target.value)}
                      placeholder="Driver Name"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      className="table-inline-input fleet-input num"
                      value={veh.capacity}
                      onChange={(e) => handleFieldChange(index, 'capacity', e.target.value)}
                      min="1"
                      max="10000"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      className="table-inline-input fleet-input num"
                      value={veh.speed}
                      onChange={(e) => handleFieldChange(index, 'speed', e.target.value)}
                      step="0.1"
                      min="0.5"
                      max="3.0"
                    />
                  </td>
                  <td>
                    <input
                      type="time"
                      className="table-inline-input fleet-input"
                      value={veh.shiftStart}
                      onChange={(e) => handleFieldChange(index, 'shiftStart', e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type="time"
                      className="table-inline-input fleet-input"
                      value={veh.shiftEnd}
                      onChange={(e) => handleFieldChange(index, 'shiftEnd', e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type="time"
                      className="table-inline-input fleet-input"
                      value={veh.breakStart}
                      onChange={(e) => handleFieldChange(index, 'breakStart', e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      className="table-inline-input fleet-input num"
                      value={veh.breakDuration}
                      onChange={(e) => handleFieldChange(index, 'breakDuration', e.target.value)}
                      min="0"
                      max="120"
                    />
                  </td>
                  <td>
                    <select
                      className="table-inline-input fleet-input"
                      value={veh.skills}
                      onChange={(e) => handleFieldChange(index, 'skills', e.target.value)}
                      style={{ fontWeight: 500 }}
                    >
                      <option value="None">None (Standard)</option>
                      <option value="Refrigerated">Refrigerated</option>
                      <option value="Hazmat">Hazmat</option>
                    </select>
                  </td>
                  <td>
                    <select
                      className="table-inline-input fleet-input"
                      value={veh.status}
                      onChange={(e) => handleFieldChange(index, 'status', e.target.value)}
                      style={{ color: statusColor, fontWeight: 600 }}
                    >
                      <option value="Active" style={{ color: 'var(--success)', fontWeight: 600 }}>
                        Active
                      </option>
                      <option value="Maintenance" style={{ color: 'var(--orange)', fontWeight: 600 }}>
                        Maintenance
                      </option>
                      <option value="Inactive" style={{ color: 'var(--danger)', fontWeight: 600 }}>
                        Inactive
                      </option>
                    </select>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      className="btn-text btn-danger btn-fleet-delete"
                      onClick={() => handleDeleteVehicle(index)}
                      title="Delete vehicle"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              );
            })}
            {fleet.length === 0 && (
              <tr>
                <td colSpan="11" className="text-center text-muted" style={{ padding: '32px' }}>
                  No vehicles in fleet. Click "+ Add Vehicle" to register a driver.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
