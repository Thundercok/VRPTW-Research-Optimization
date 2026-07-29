import React from 'react';
import { useAppContext } from '../context/AppContext.jsx';
import { SAMPLE_SOLOMON_RC } from '../constants.js';

export default function Header() {
  const { state, updateState, status, statusTone, submitJob, loadSolomonDataset, backendAvailable, t } = useAppContext();

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
        const seedDrivers = [
          { name: 'Nguyễn Minh Tuấn', speed: 1.05, shiftStart: '06:00', shiftEnd: '15:00', breakStart: '10:30', breakDuration: 30, skills: 'None', status: 'Active' },
          { name: 'Phạm Hoàng Nam', speed: 0.98, shiftStart: '08:00', shiftEnd: '17:00', breakStart: '12:00', breakDuration: 45, skills: 'Refrigerated', status: 'Active' },
          { name: 'Lê Văn Hùng', speed: 0.90, shiftStart: '07:30', shiftEnd: '16:30', breakStart: '11:30', breakDuration: 40, skills: 'Hazmat', status: 'In Transit' },
          { name: 'Trần Quốc Bảo', speed: 1.02, shiftStart: '08:00', shiftEnd: '17:00', breakStart: '12:00', breakDuration: 30, skills: 'Express', status: 'Active' },
          { name: 'Vũ Đức Duy', speed: 0.95, shiftStart: '06:30', shiftEnd: '15:30', breakStart: '11:00', breakDuration: 30, skills: 'Refrigerated', status: 'On Break' },
          { name: 'Đặng Minh Triết', speed: 1.10, shiftStart: '08:30', shiftEnd: '17:30', breakStart: '12:30', breakDuration: 30, skills: 'Express', status: 'Active' },
          { name: 'Hoàng Văn Phong', speed: 0.88, shiftStart: '09:00', shiftEnd: '18:00', breakStart: '13:00', breakDuration: 60, skills: 'Hazmat', status: 'Active' },
          { name: 'Đỗ Tiến Đạt', speed: 1.00, shiftStart: '08:00', shiftEnd: '17:00', breakStart: '12:00', breakDuration: 30, skills: 'None', status: 'Active' },
          { name: 'Bùi Anh Tuấn', speed: 0.97, shiftStart: '07:00', shiftEnd: '16:00', breakStart: '11:30', breakDuration: 30, skills: 'Refrigerated', status: 'Maintenance' },
          { name: 'Phan Văn Khánh', speed: 1.00, shiftStart: '08:00', shiftEnd: '17:00', breakStart: '12:00', breakDuration: 30, skills: 'None', status: 'Active' }
        ];
        for (let i = fleet.length; i < val; i++) {
          const d = seedDrivers[i % seedDrivers.length];
          fleet.push({
            id: i,
            driver: d.name,
            capacity: currentCapacity,
            speed: d.speed,
            shiftStart: d.shiftStart,
            shiftEnd: d.shiftEnd,
            breakStart: d.breakStart,
            breakDuration: d.breakDuration,
            skills: d.skills,
            status: d.status,
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
        return t('headerTitleDefault');
      case 'fleet':
        return t('headerTitleFleet');
      case 'analytics':
        return t('headerTitleAnalytics');
      case 'settings':
        return t('headerTitleSettings');
      default:
        return t('headerTitleDefault');
    }
  };

  const getPageContext = () => {
    switch (state.activeTab) {
      case 'dispatch':
      case 'fleet':
        return t('headerCtxPlanning');
      case 'analytics':
      case 'settings':
        return t('headerCtxIntelligence');
      default:
        return t('headerCtxPlanning');
    }
  };

  return (
    <header className="saas-header">
      <div className="header-left">
        <div className="page-title-group">
          <h1 className="page-title">{getPageTitle()}</h1>
          <span className="page-subtitle">{getPageContext()}</span>
        </div>
        <span className={`status-pill status-ready ${statusTone}`} id="status">
          {status}
        </span>
        {backendAvailable === false && (
          <div className="backend-warning" style={{ fontSize: '11px', color: 'var(--alert)', background: 'var(--alert-wash)', padding: '4px 8px', borderRadius: '4px', fontWeight: 'bold' }}>
            ⚠ Backend Offline
          </div>
        )}
      </div>

      {state.activeTab === 'dispatch' && (
        <div className="header-right">
          {/* Map overlay picker. Lives here, next to the dataset select, rather
              than over the map — MapController/App repopulate its options after
              every solve. No caption: the option text names the overlay. */}
          <select
            id="map-view-select"
            className="saas-select map-overlay-select"
            defaultValue="ddqn"
            aria-label={t('mapOverlay')}
            title={t('mapOverlay')}
          >
            <option value="ddqn">DDQN</option>
            <option value="alns">ALNS Base</option>
          </select>
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
            <option value="custom">{t('headerCustomImport')}</option>
          </select>
          {/* The only manifest trigger in the app — the map pane no longer
              carries a duplicate. Usable on every dataset; the drawer itself
              stays read-only for the bundled demo sets. */}
          <button
            id="btn-toggle-drawer"
            className="btn-secondary btn-sm manifest-btn"
            onClick={() => window.dispatchEvent(new CustomEvent('open-manifest'))}
            title={t('manifestDrawerTitle')}
          >
            <span aria-hidden="true">☰</span>
            {t('manifestBtn')}
          </button>
          <div className="fleet-toggles">
            <label>
              {t('headerVehicles')}:{' '}
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
              {t('headerCapacity')}:{' '}
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
            {t('headerExecute')}
          </button>
        </div>
      )}
    </header>
  );
}
