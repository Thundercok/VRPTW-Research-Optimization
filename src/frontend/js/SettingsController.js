import { toggleDemoLang } from './demoLang.js';

export class SettingsController {
  constructor(app) {
    this.app = app;
  }

  init() {
    // Read or apply any initial preferences
    const apiBase = localStorage.getItem('vrptw_api_base');
    if (apiBase) {
      console.info('[SettingsController] Custom API base URL active:', apiBase);
    }
  }

  render() {
    const container = document.getElementById('view-settings');
    if (!container || container.classList.contains('hidden')) return;

    const apiBase = localStorage.getItem('vrptw_api_base') || '';

    let html = `
      <div class="settings-view-container">
        <div class="settings-view-header">
          <h2>System Settings & Workspace Preferences</h2>
          <p class="section-desc">Adjust local API endpoints, toggle language, review Firebase platform connectivity, and customize map styles.</p>
        </div>

        <div class="settings-grid">
          <div class="saas-card settings-card">
            <h3>API & Execution Environment</h3>
            <p class="card-desc">Set backend server address to direct solver operations.</p>
            <div class="settings-form-group" style="margin-top: 12px;">
              <label for="settings-api-url">Backend API Endpoint</label>
              <input type="text" id="settings-api-url" class="saas-input" value="${apiBase}" placeholder="Default: Same Host / Proxy (e.g., http://127.0.0.1:8000)" />
              <p class="field-hint">Specify alternative host if running python backend separately from Vite.</p>
            </div>
            <button id="btn-save-api-settings" class="btn-primary" style="margin-top: 16px;">Save API Configuration</button>
          </div>

          <div class="saas-card settings-card">
            <h3>Interface & Localization</h3>
            <p class="card-desc">Manage language preferences and mapping providers.</p>
            <div class="settings-form-group" style="margin-top: 12px;">
              <label>Current Language</label>
              <div style="display: flex; gap: 8px; margin-top: 6px;">
                <button id="btn-settings-lang-en" class="btn-secondary ${this.app.lang === 'en' ? 'active-btn' : ''}">English (EN)</button>
                <button id="btn-settings-lang-vn" class="btn-secondary ${this.app.lang === 'vn' ? 'active-btn' : ''}">Tiếng Việt (VN)</button>
              </div>
            </div>

            <div class="settings-form-group" style="margin-top: 16px;">
              <label for="settings-map-theme">Map Visual Style</label>
              <select id="settings-map-theme" class="saas-select" style="margin-top: 6px;">
                <option value="carto-light" selected>CartoDB Positron (Light)</option>
                <option value="carto-dark">CartoDB Dark Matter</option>
              </select>
            </div>
          </div>

          <div class="saas-card settings-card">
            <h3>Firebase Connection & Session</h3>
            <p class="card-desc">Review your current operator session state.</p>
            <div style="margin-top: 12px; display: flex; flex-direction: column; gap: 10px;">
              <div class="settings-info-row">
                <span>Firebase Persistence:</span>
                <strong style="color: ${this.app.state.token ? 'var(--success)' : 'var(--text-muted)'}">
                  ${this.app.state.token ? 'Active Session' : 'Guest Mode (Local Only)'}
                </strong>
              </div>
              <div class="settings-info-row">
                <span>Operator Account:</span>
                <span class="font-mono">${this.app.escapeHtml(this.app.state.email || 'guest@nami.local')}</span>
              </div>
              <div class="settings-info-row">
                <span>System Mode:</span>
                <span class="status-pill status-ready" style="text-transform: uppercase; font-size: 10px; padding: 2px 6px;">${this.app.state.mode} DATA</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    container.innerHTML = html;

    // Bind event handlers
    const btnSaveApi = container.querySelector('#btn-save-api-settings');
    btnSaveApi?.addEventListener('click', () => {
      const urlVal = document.getElementById('settings-api-url').value.trim();
      if (urlVal) {
        localStorage.setItem('vrptw_api_base', urlVal);
      } else {
        localStorage.removeItem('vrptw_api_base');
      }
      this.app.toast('Settings Saved', 'API endpoint updated. Please reload to apply.', 'ok');
    });

    const btnEn = container.querySelector('#btn-settings-lang-en');
    btnEn?.addEventListener('click', () => {
      if (this.app.lang !== 'en') {
        const nextLang = toggleDemoLang();
        this.app.lang = nextLang;
        this.app.applyLanguage(nextLang);
        this.render();
      }
    });

    const btnVn = container.querySelector('#btn-settings-lang-vn');
    btnVn?.addEventListener('click', () => {
      if (this.app.lang !== 'vn') {
        const nextLang = toggleDemoLang();
        this.app.lang = nextLang;
        this.app.applyLanguage(nextLang);
        this.render();
      }
    });

    const themeSelect = container.querySelector('#settings-map-theme');
    const savedTheme = localStorage.getItem('vrptw_map_theme') || 'carto-light';
    if (themeSelect) {
      themeSelect.value = savedTheme;
      themeSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        localStorage.setItem('vrptw_map_theme', val);
        this.app.toast('Style Selected', 'Map visual style updated. Please refresh to render tiles.', 'ok');
      });
    }
  }
}
