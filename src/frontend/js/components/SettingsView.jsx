import React, { useState } from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export default function SettingsView() {
  const { state, setLang, toast, t } = useAppContext();
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem('vrptw_api_base') || '');
  const [mapTheme, setMapTheme] = useState(() => localStorage.getItem('vrptw_map_theme') || 'carto-light');
  const [appTheme, setAppTheme] = useState(() => localStorage.getItem('vrptw_theme') || localStorage.getItem('vrptw_landing_theme_v2') || 'dark');

  const saveApiBase = () => {
    if (apiUrl.trim()) {
      localStorage.setItem('vrptw_api_base', apiUrl.trim());
    } else {
      localStorage.removeItem('vrptw_api_base');
    }
    toast('Settings Saved', 'API endpoint updated. Please reload to apply.', 'ok');
  };

  const handleMapThemeChange = (e) => {
    const val = e.target.value;
    setMapTheme(val);
    localStorage.setItem('vrptw_map_theme', val);
    toast('Style Selected', 'Map visual style updated. Please refresh to render tiles.', 'ok');
  };

  const handleAppThemeChange = (e) => {
    const val = e.target.value;
    setAppTheme(val);
    localStorage.setItem('vrptw_theme', val);
    document.documentElement.setAttribute('data-theme', val);
    toast('Theme Updated', `Application theme changed to ${val}.`, 'ok');
  };

  return (
    <div className="settings-view-container">
      <div className="settings-view-header">
        <h2>System Settings & Workspace Preferences</h2>
        <p className="section-desc">Adjust local API endpoints, toggle language, review Firebase platform connectivity, and customize map styles.</p>
      </div>

      <div className="settings-grid">
        <div className="saas-card settings-card">
          <h3>API & Execution Environment</h3>
          <p className="card-desc">Set backend server address to direct solver operations.</p>
          <div className="settings-form-group" style={{ marginTop: '12px' }}>
            <label htmlFor="settings-api-url">Backend API Endpoint</label>
            <input 
              type="text" 
              id="settings-api-url" 
              className="saas-input" 
              value={apiUrl} 
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="Default: Same Host / Proxy (e.g., http://127.0.0.1:8000)" 
            />
            <p className="field-hint">Specify alternative host if running python backend separately from Vite.</p>
          </div>
          <button className="btn-primary" style={{ marginTop: '16px' }} onClick={saveApiBase}>
            Save API Configuration
          </button>
        </div>

        <div className="saas-card settings-card">
          <h3>Interface & Localization</h3>
          <p className="card-desc">Manage language preferences and mapping providers.</p>
          <div className="settings-form-group" style={{ marginTop: '12px' }}>
            <label>Current Language</label>
            <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
              <button 
                className={`btn-secondary ${state.lang === 'en' ? 'active-btn' : ''}`}
                onClick={() => setLang('en')}
              >
                English (EN)
              </button>
              <button 
                className={`btn-secondary ${state.lang === 'vn' ? 'active-btn' : ''}`}
                onClick={() => setLang('vn')}
              >
                Tiếng Việt (VN)
              </button>
            </div>
          </div>

          <div className="settings-form-group" style={{ marginTop: '16px' }}>
            <label htmlFor="settings-app-theme">Application Theme Mode</label>
            <select 
              id="settings-app-theme" 
              className="saas-select" 
              style={{ marginTop: '6px' }}
              value={appTheme}
              onChange={handleAppThemeChange}
            >
              <option value="dark">Dark Theme (Premium Glassmorphic)</option>
              <option value="light">Light Theme (Default Slate)</option>
            </select>
          </div>

          <div className="settings-form-group" style={{ marginTop: '16px' }}>
            <label htmlFor="settings-map-theme">Map Visual Style</label>
            <select 
              id="settings-map-theme" 
              className="saas-select" 
              style={{ marginTop: '6px' }}
              value={mapTheme}
              onChange={handleMapThemeChange}
            >
              <option value="carto-light">CartoDB Positron (Light)</option>
              <option value="carto-dark">CartoDB Dark Matter</option>
            </select>
          </div>
        </div>

        <div className="saas-card settings-card">
          <h3>Firebase Connection & Session</h3>
          <p className="card-desc">Review your current operator session state.</p>
          <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div className="settings-info-row">
              <span>Firebase Persistence:</span>
              <strong style={{ color: state.token ? 'var(--success)' : 'var(--text-muted)' }}>
                {state.token ? 'Active Session' : 'Guest Mode (Local Only)'}
              </strong>
            </div>
            <div className="settings-info-row">
              <span>Operator Account:</span>
              <span className="font-mono">{state.email || 'guest@nami.local'}</span>
            </div>
            <div className="settings-info-row">
              <span>System Mode:</span>
              <span className="status-pill status-ready" style={{ textTransform: 'uppercase', fontSize: '10px', padding: '2px 6px' }}>
                {state.mode} DATA
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
