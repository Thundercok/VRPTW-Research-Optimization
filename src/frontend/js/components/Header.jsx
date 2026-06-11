import React from 'react';
import { useAppContext } from '../context/AppContext.jsx';
import { SAMPLE_SOLOMON_RC } from '../constants.js';

export default function Header() {
  const { state, updateState, status, statusTone, submitJob, loadSolomonDataset } = useAppContext();

  const handleDatasetChange = (e) => {
    const value = e.target.value;
    if (value === 'custom') {
      updateState({
        mode: 'real',
        customers: [], // wait for CSV upload
        selectedDataset: 'custom',
      });
    } else {
      updateState({
        mode: 'sample',
        selectedDataset: value,
      });
      loadSolomonDataset(value);
    }
  };

  const handleVehiclesChange = (e) => {
    const val = Math.max(1, Number(e.target.value) || 1);
    updateState({ vehicles: val });

    // Synchronize fleet config size
    updateState((prev) => {
      const fleet = [...(prev.fleet || [])];
      const currentCapacity = prev.capacity || 120;
      if (fleet.length < val) {
        for (let i = fleet.length; i < val; i++) {
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
      } else if (fleet.length > val) {
        fleet.splice(val);
      }
      localStorage.setItem('vrptw_fleet_config', JSON.stringify(fleet));
      return { fleet };
    });
  };

  const handleCapacityChange = (e) => {
    const val = Math.max(1, Number(e.target.value) || 1);
    updateState({ capacity: val });

    // Synchronize individual vehicles capacity defaults
    updateState((prev) => {
      const fleet = (prev.fleet || []).map((v) => ({ ...v, capacity: val }));
      localStorage.setItem('vrptw_fleet_config', JSON.stringify(fleet));
      return { fleet };
    });
  };

  const getPageTitle = () => {
    switch (state.activeTab) {
      case 'dispatch':
        return 'Route Optimization';
      case 'fleet':
        return 'Fleet Management';
      case 'analytics':
        return 'Diagnostics';
      case 'settings':
        return 'Preferences';
      default:
        return 'Route Optimization';
    }
  };

  return (
    <header className="saas-header">
      <div className="header-left">
        <h1 className="page-title">{getPageTitle()}</h1>
        <span className={`status-pill status-ready ${statusTone}`} id="status">
          {status}
        </span>
      </div>

      {state.activeTab === 'dispatch' && (
        <div className="header-right">
          <select 
            id="dataset-select" 
            className="saas-select"
            value={state.mode === 'sample' ? (state.selectedDataset || 'demo') : 'custom'}
            onChange={handleDatasetChange}
          >
            {state.solomonDatasets && state.solomonDatasets.length > 0 ? (
              state.solomonDatasets.map((ds) => (
                <option key={ds.name} value={ds.name}>
                  {ds.label || ds.name.toUpperCase()}
                </option>
              ))
            ) : (
              <option value="demo">Solomon RC101 (Demo)</option>
            )}
            <option value="custom">Custom Import...</option>
          </select>
          <div className="fleet-toggles">
            <label>
              Vehicles:{' '}
              <input 
                type="number" 
                id="vehicles-slider" 
                className="saas-input-small"
                value={state.vehicles}
                onChange={handleVehiclesChange}
                min="1"
                max="50"
              />
            </label>
            <label>
              Capacity:{' '}
              <input 
                type="number" 
                id="capacity-slider" 
                className="saas-input-small"
                value={state.capacity}
                onChange={handleCapacityChange}
                min="10"
                max="10000"
              />
            </label>
          </div>
          <button id="run-model" className="btn-primary" onClick={submitJob}>
            Execute Solver
          </button>
        </div>
      )}
    </header>
  );
}
