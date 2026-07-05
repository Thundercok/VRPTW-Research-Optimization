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
        <h2>{state.lang === 'vn' ? 'Cài Đặt Hệ Thống & Tùy Chọn Workspace' : 'System Settings & Workspace Preferences'}</h2>
        <p className="section-desc">
          {state.lang === 'vn' 
            ? 'Điều chỉnh API endpoint, thay đổi ngôn ngữ giao diện, kiểm tra trạng thái kết nối Firebase và tùy biến style bản đồ.' 
            : 'Adjust local API endpoints, toggle language, review Firebase platform connectivity, and customize map styles.'}
        </p>
      </div>

      <div className="settings-grid">
        <div className="saas-card settings-card">
          <h3>{state.lang === 'vn' ? 'API & Môi Trường Thực Thi' : 'API & Execution Environment'}</h3>
          <p className="card-desc">
            {state.lang === 'vn' ? 'Cấu hình địa chỉ server backend để thực thi các tác vụ tính toán tối ưu.' : 'Set backend server address to direct solver operations.'}
          </p>
          <div className="settings-form-group" style={{ marginTop: '12px' }}>
            <label htmlFor="settings-api-url">{state.lang === 'vn' ? 'Địa chỉ Backend API Endpoint' : 'Backend API Endpoint'}</label>
            <input 
              type="text" 
              id="settings-api-url" 
              className="saas-input" 
              value={apiUrl} 
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="Default: Same Host / Proxy (e.g., http://127.0.0.1:8000)" 
            />
            <p className="field-hint">
              {state.lang === 'vn' 
                ? 'Chỉ định host thay thế nếu bạn đang chạy python backend ở một server/cổng khác.' 
                : 'Specify alternative host if running python backend separately from Vite.'}
            </p>
          </div>
          <button className="btn-primary" style={{ marginTop: '16px' }} onClick={saveApiBase}>
            {state.lang === 'vn' ? 'Lưu Cấu Hình API' : 'Save API Configuration'}
          </button>
        </div>

        <div className="saas-card settings-card">
          <h3>{state.lang === 'vn' ? 'Giao Diện & Bản Địa Hóa' : 'Interface & Localization'}</h3>
          <p className="card-desc">{state.lang === 'vn' ? 'Quản lý tùy chọn ngôn ngữ hiển thị và nhà cung cấp bản đồ.' : 'Manage language preferences and mapping providers.'}</p>
          <div className="settings-form-group" style={{ marginTop: '12px' }}>
            <label>{state.lang === 'vn' ? 'Ngôn Ngữ Hiện Tại' : 'Current Language'}</label>
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
            <label htmlFor="settings-app-theme">{state.lang === 'vn' ? 'Chế Độ Giao Diện Dashboard' : 'Application Theme Mode'}</label>
            <select 
              id="settings-app-theme" 
              className="saas-select" 
              style={{ marginTop: '6px' }}
              value={appTheme}
              onChange={handleAppThemeChange}
            >
              <option value="dark">{state.lang === 'vn' ? 'Giao diện Tối (Premium Glassmorphic)' : 'Dark Theme (Premium Glassmorphic)'}</option>
              <option value="light">{state.lang === 'vn' ? 'Giao diện Sáng (Default Slate)' : 'Light Theme (Default Slate)'}</option>
            </select>
          </div>

          <div className="settings-form-group" style={{ marginTop: '16px' }}>
            <label htmlFor="settings-map-theme">{state.lang === 'vn' ? 'Phong Cách Bản Đồ' : 'Map Visual Style'}</label>
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
          <h3>{state.lang === 'vn' ? 'Kết Nối Firebase & Trạng Thái Phiên' : 'Firebase Connection & Session'}</h3>
          <p className="card-desc">{state.lang === 'vn' ? 'Xem trạng thái phiên làm việc của điều phối viên hiện tại.' : 'Review your current operator session state.'}</p>
          <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div className="settings-info-row">
              <span>{state.lang === 'vn' ? 'Phiên Firebase:' : 'Firebase Persistence:'}</span>
              <strong style={{ color: state.token ? 'var(--success)' : 'var(--text-muted)' }}>
                {state.token 
                  ? (state.lang === 'vn' ? 'Đã đăng nhập Firebase' : 'Active Session') 
                  : (state.lang === 'vn' ? 'Chế độ Khách (Chỉ lưu cục bộ)' : 'Guest Mode (Local Only)')}
              </strong>
            </div>
            <div className="settings-info-row">
              <span>{state.lang === 'vn' ? 'Tài Khoản Operator:' : 'Operator Account:'}</span>
              <span className="font-mono">{state.email || 'guest@nami.local'}</span>
            </div>
            <div className="settings-info-row">
              <span>{state.lang === 'vn' ? 'Chế Độ Dữ Liệu:' : 'System Mode:'}</span>
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
