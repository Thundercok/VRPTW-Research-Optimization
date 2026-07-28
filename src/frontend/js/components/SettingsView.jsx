import React, { useState } from 'react';
import { useAppContext } from '../context/AppContext.jsx';
import { startOnboardingTour } from './OnboardingTour.jsx';
import { openShortcutsOverlay } from './ShortcutsOverlay.jsx';
import { SHORTCUTS } from '../shortcuts.js';
import {
  STORAGE_KEYS,
  applyAppTheme,
  applyMapTheme,
  currentApiBase,
  exportWorkspace,
  normalizeApiBase,
  resetPreferences,
} from '../workspace.js';

export default function SettingsView() {
  const { state, setLang, toast, t, updateState } = useAppContext();
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem(STORAGE_KEYS.apiBase) || '');
  const [mapTheme, setMapTheme] = useState(() => localStorage.getItem(STORAGE_KEYS.mapTheme) || 'carto-light');
  const [appTheme, setAppTheme] = useState(
    () => localStorage.getItem(STORAGE_KEYS.appTheme) || localStorage.getItem(STORAGE_KEYS.landingTheme) || 'light'
  );
  const [testing, setTesting] = useState(false);

  /** Writes the API base. Returns the stored value, or null when rejected. */
  const persistApiBase = () => {
    const normalized = normalizeApiBase(apiUrl);
    if (normalized === null) {
      toast('Invalid Endpoint', t('setApiInvalid'), 'error');
      return null;
    }
    if (normalized) {
      localStorage.setItem(STORAGE_KEYS.apiBase, normalized);
    } else {
      localStorage.removeItem(STORAGE_KEYS.apiBase);
    }
    setApiUrl(normalized);
    return normalized;
  };

  const saveApiBase = () => {
    const stored = persistApiBase();
    if (stored === null) return;
    toast(
      'Settings Saved',
      stored ? `Requests will go to ${stored} after a reload.` : 'Reverted to this host. Reload to apply.',
      'ok'
    );
  };

  // API_BASE is resolved once at module load, so the only honest way to apply a
  // new endpoint is a reload — offer it rather than leaving the user guessing.
  const saveApiBaseAndReload = () => {
    if (persistApiBase() === null) return;
    window.location.reload();
  };

  const testConnection = async () => {
    const target = normalizeApiBase(apiUrl);
    if (target === null) {
      toast('Invalid Endpoint', t('setApiInvalid'), 'error');
      return;
    }
    const base = target || currentApiBase();
    setTesting(true);
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 6000);
      const res = await fetch(`${base}/health`, { signal: controller.signal });
      clearTimeout(timer);
      if (res.ok) {
        toast('Connection Successful', `Backend responded at ${base}/health`, 'ok');
      } else {
        toast('Connection Failed', `${base}/health returned HTTP ${res.status}`, 'error');
      }
    } catch (e) {
      const reason = e?.name === 'AbortError' ? 'timed out after 6s' : 'network error';
      toast('Connection Failed', `Cannot reach ${base}/health — ${reason}.`, 'error');
    } finally {
      setTesting(false);
    }
  };

  const handleMapThemeChange = (e) => {
    const val = e.target.value;
    setMapTheme(val);
    const appliedLive = applyMapTheme(val);
    toast(
      'Map Style Updated',
      appliedLive ? 'Basemap swapped on the live map.' : 'Saved — it applies when the dispatch map opens.',
      'ok'
    );
  };

  const handleAppThemeChange = (e) => {
    const val = applyAppTheme(e.target.value);
    setAppTheme(val);
    toast('Theme Updated', `Application theme changed to ${val}.`, 'ok');
  };

  const handleExport = () => {
    const counts = exportWorkspace(state);
    toast('Export Complete', `${counts.customers} stops and ${counts.fleet} vehicles saved to JSON.`, 'ok');
  };

  const handleRestartTour = () => {
    updateState({ activeTab: 'dispatch' });
    startOnboardingTour();
  };

  const handleResetPreferences = () => {
    if (!window.confirm('Reset language, theme, map style and API endpoint to their defaults?')) return;
    resetPreferences();
    setApiUrl('');
    setMapTheme('carto-light');
    setAppTheme('light');
    setLang('en');
    applyMapTheme('carto-light');
    toast('Preferences Reset', 'Workspace data was left untouched.', 'ok');
  };

  const clearAllData = () => {
    if (!window.confirm('Clear all local data? This removes your fleet, preferences and session.')) return;
    localStorage.clear();
    toast('Data Cleared', 'All local data has been removed. Reloading...', 'warn');
    setTimeout(() => window.location.reload(), 900);
  };

  const effectiveBase = localStorage.getItem(STORAGE_KEYS.apiBase) || `${window.location.origin}/api`;

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
              placeholder="http://127.0.0.1:8000/api"
            />
            <p className="field-hint">{t('setApiHint')}</p>
            <p className="field-hint">
              Currently in use: <span className="font-mono">{effectiveBase}</span>
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
            <button className="btn-primary" onClick={saveApiBase}>
              {t('setApiSave')}
            </button>
            <button className="btn-secondary" onClick={saveApiBaseAndReload}>
              {t('setApiReload')}
            </button>
            <button className="btn-secondary" onClick={testConnection} disabled={testing}>
              {testing ? '…' : t('setApiTest')}
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
              <span
                className="status-pill status-ready"
                style={{ textTransform: 'uppercase', fontSize: '10px', padding: '2px 6px' }}
              >
                {state.mode} DATA
              </span>
            </div>
          </div>
        </div>

        <div className="saas-card settings-card">
          <h3>{t('setData')}</h3>
          <p className="card-desc">{t('setDataDesc')}</p>

          <div style={{ marginTop: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button className="btn-secondary" onClick={handleExport}>
              {t('setDataExport')}
            </button>
            <button className="btn-secondary" onClick={handleRestartTour}>
              {t('setDataRestart')}
            </button>
            <button className="btn-secondary" onClick={handleResetPreferences}>
              {t('setResetPrefs')}
            </button>
            <button
              className="btn-secondary"
              style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}
              onClick={clearAllData}
            >
              {t('setDataClear')}
            </button>
          </div>
          <p className="field-hint" style={{ marginTop: '10px' }}>
            {t('setDataExportHint')}
          </p>
        </div>

        <div className="saas-card settings-card">
          <h3>{t('setShortcuts')}</h3>
          <p className="card-desc">{t('setShortcutsDesc')}</p>
          {/* Rendered from the same table the key handler binds, so the list
              cannot advertise a hotkey that does nothing. */}
          <ul className="shortcuts-list">
            {SHORTCUTS.map((s) => (
              <li key={s.id}>
                <span className="shortcut-desc">{t(s.labelKey)}</span>
                <span className="shortcut-keys">
                  {s.keys.map((k) => (
                    <kbd key={k}>{k}</kbd>
                  ))}
                </span>
              </li>
            ))}
          </ul>
          <button className="btn-secondary btn-sm" style={{ marginTop: '14px' }} onClick={openShortcutsOverlay}>
            {t('setShortcutsHelp')}
          </button>
        </div>
      </div>
    </div>
  );
}
