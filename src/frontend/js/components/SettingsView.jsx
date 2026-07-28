import React, { useState } from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export default function SettingsView() {
  const { state, setLang, toast, t, request } = useAppContext();
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem('vrptw_api_base') || '');
  const [mapTheme, setMapTheme] = useState(() => localStorage.getItem('vrptw_map_theme') || 'carto-light');
  const [appTheme, setAppTheme] = useState(() => localStorage.getItem('vrptw_theme') || localStorage.getItem('vrptw_landing_theme_v2') || 'light');

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

  const testConnection = async () => {
    try {
      const urlToTest = apiUrl.trim() || 'http://127.0.0.1:8000';
      const res = await fetch(`${urlToTest}/health`);
      if (res.ok) {
        toast('Connection Successful', `Backend is reachable at ${urlToTest}`, 'ok');
      } else {
        toast('Connection Failed', `Backend responded with status ${res.status}`, 'error');
      }
    } catch (e) {
      toast('Connection Failed', `Cannot reach backend. Network error.`, 'error');
    }
  };

  const clearAllData = () => {
    if (confirm('Are you sure you want to clear all local data? This will reset your session.')) {
      localStorage.clear();
      toast('Data Cleared', 'All local data has been removed. Reloading...', 'warn');
      setTimeout(() => window.location.reload(), 1000);
    }
  };

  const restartOnboarding = () => {
    localStorage.setItem('vrptw_onboarding_complete', 'false');
    toast('Tour Restarted', 'The onboarding tour will begin immediately.', 'ok');
    // We update local storage, which the onboarding component listens to (in interval).
  };

  const exportData = () => {
    const dataStr = JSON.stringify(state.customers, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'vrptw_customers_export.json';
    link.click();
    URL.revokeObjectURL(url);
    toast('Export Complete', 'Customer data downloaded as JSON.', 'ok');
  };

  return (
    <div className="settings-view-container">
      <div className="settings-view-header">
        <h2>{t('setMainTitle')}</h2>
        <p className="section-desc">{t('setDesc')}</p>
      </div>

      <div className="settings-grid">
        <div className="saas-card settings-card">
          <h3>{t('setApi')}</h3>
          <p className="card-desc">{t('setApiDesc')}</p>
          <div className="settings-form-group" style={{ marginTop: '12px' }}>
            <label htmlFor="settings-api-url">{t('setApiUrl')}</label>
            <input 
              type="text" 
              id="settings-api-url" 
              className="saas-input" 
              value={apiUrl} 
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="Default: Same Host / Proxy (e.g., http://127.0.0.1:8000)" 
            />
            <p className="field-hint">{t('setApiHint')}</p>
          </div>
          <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
            <button className="btn-primary" onClick={saveApiBase}>
              {t('setApiSave')}
            </button>
            <button className="btn-secondary" onClick={testConnection}>
              {t('setApiTest')}
            </button>
          </div>
        </div>

        <div className="saas-card settings-card">
          <h3>{t('setUi')}</h3>
          <p className="card-desc">{t('setUiDesc')}</p>
          <div className="settings-form-group" style={{ marginTop: '12px' }}>
            <label>{t('setUiLang')}</label>
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
            <label htmlFor="settings-app-theme">{t('setUiTheme')}</label>
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
            <label htmlFor="settings-map-theme">{t('setUiMap')}</label>
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
          <h3>{t('setFirebase')}</h3>
          <p className="card-desc">{t('setFirebaseDesc')}</p>
          <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div className="settings-info-row">
              <span>{t('setFbPersist')}</span>
              <strong style={{ color: state.token ? 'var(--success)' : 'var(--text-muted)' }}>
                {state.token ? 'Active Session' : 'Guest Mode (Local Only)'}
              </strong>
            </div>
            <div className="settings-info-row">
              <span>{t('setFbAccount')}</span>
              <span className="font-mono">{state.email || 'guest@nami.local'}</span>
            </div>
            <div className="settings-info-row">
              <span>{t('setFbMode')}</span>
              <span className="status-pill status-ready" style={{ textTransform: 'uppercase', fontSize: '10px', padding: '2px 6px' }}>
                {state.mode} DATA
              </span>
            </div>
          </div>
        </div>

        <div className="saas-card settings-card">
          <h3>{t('setData')}</h3>
          <p className="card-desc">{t('setDataDesc')}</p>
          
          <div style={{ marginTop: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button className="btn-secondary" onClick={exportData}>{t('setDataExport')}</button>
            <button className="btn-secondary" onClick={restartOnboarding}>{t('setDataRestart')}</button>
            <button className="btn-secondary" style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }} onClick={clearAllData}>{t('setDataClear')}</button>
          </div>
        </div>

        <div className="saas-card settings-card">
          <h3>{t('setShortcuts')}</h3>
          <p className="card-desc">{t('setShortcutsDesc')}</p>
          <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Shift + ?</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>Help & Shortcuts</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Ctrl + S</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>Execute Solver</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Ctrl + E</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>Toggle Edit Mode</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
