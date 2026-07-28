import React, { useState, useEffect } from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export default function Sidebar() {
  const { state, updateState, logout, t } = useAppContext();
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem('vrptw_sidebar_collapsed') === 'true';
  });

  useEffect(() => {
    document.documentElement.style.setProperty('--sidebar-width', collapsed ? '56px' : '220px');
  }, [collapsed]);

  const toggleCollapse = () => {
    const newVal = !collapsed;
    setCollapsed(newVal);
    localStorage.setItem('vrptw_sidebar_collapsed', newVal);
  };

  const handleTabClick = (e, tab) => {
    e.preventDefault();
    updateState({ activeTab: tab });
  };

  return (
    <aside className={`saas-sidebar ${collapsed ? 'collapsed' : ''}`} onDoubleClick={toggleCollapse}>
      <div className="brand">
        <div className="brand-logo">N</div>
        {!collapsed && <span className="brand-text">NAMI OPS</span>}
        <button className="sidebar-collapse-btn" onClick={toggleCollapse} title="Toggle Sidebar">
          {collapsed ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="13 17 18 12 13 7"></polyline><polyline points="6 17 11 12 6 7"></polyline></svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="11 17 6 12 11 7"></polyline><polyline points="18 17 13 12 18 7"></polyline></svg>
          )}
        </button>
      </div>

      <nav className="saas-nav">
        {!collapsed && <p className="nav-label">{t('sbPlanning')}</p>}
        {collapsed && <div style={{ height: '28px' }}></div>}
        <a 
          href="#" 
          className={`nav-item ${state.activeTab === 'dispatch' ? 'active' : ''}`}
          onClick={(e) => handleTabClick(e, 'dispatch')}
          title={t('sbLiveDispatch')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"></polygon><line x1="9" y1="3" x2="9" y2="21"></line><line x1="15" y1="3" x2="15" y2="21"></line></svg>
          {!collapsed && <span>{t('sbLiveDispatch')}</span>}
        </a>
        <a 
          href="#" 
          className={`nav-item ${state.activeTab === 'fleet' ? 'active' : ''}`}
          onClick={(e) => handleTabClick(e, 'fleet')}
          title={t('sbFleetConfig')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>
          {!collapsed && <span>{t('sbFleetConfig')}</span>}
        </a>

        {!collapsed && <p className="nav-label" style={{ marginTop: '24px' }}>{t('sbIntelligence')}</p>}
        {collapsed && <div style={{ height: '38px' }}></div>}
        <a 
          href="#" 
          className={`nav-item ${state.activeTab === 'analytics' ? 'active' : ''}`}
          onClick={(e) => handleTabClick(e, 'analytics')}
          title={t('sbModelAnalytics')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
          {!collapsed && <span>{t('sbModelAnalytics')}</span>}
        </a>
        <a 
          href="#" 
          className={`nav-item ${state.activeTab === 'settings' ? 'active' : ''}`}
          onClick={(e) => handleTabClick(e, 'settings')}
          title={t('sbSettings')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
          {!collapsed && <span>{t('sbSettings')}</span>}
        </a>
      </nav>

      <div className="sidebar-footer">
        <a 
          href="index.html" 
          className={collapsed ? "btn-icon-only" : "btn-back-home"}
          title={t('sbWebsite')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
          {!collapsed && <span>{t('sbWebsite')}</span>}
        </a>
        {state.unlocked && state.role !== 'guest' ? (
          <>
            {!collapsed && (
              <div className="user-badge" id="user-email">
                {state.email}
              </div>
            )}
            <button id="btn-logout" className={collapsed ? "btn-icon-only" : "btn-text"} onClick={logout} title={t('logoutButton')}>
              {collapsed ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
              ) : t('logoutButton')}
            </button>
          </>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
            {!collapsed && state.role === 'guest' && (
              <div className="user-badge" id="user-email" style={{ opacity: 0.7, fontSize: '11px' }}>
                {t('sbGuestDemo')}
              </div>
            )}
            <button
              id="btn-sidebar-login"
              className={collapsed ? "btn btn-icon-only-primary" : "btn"}
              style={collapsed ? {} : {
                width: '100%',
                background: 'var(--primary)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                padding: '8px 12px',
                fontSize: '13px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'background 0.2s'
              }}
              onClick={() => updateState({ showLoginModal: true })}
              title={t('sbSignIn')}
            >
              {collapsed ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg>
              ) : t('sbSignIn')}
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
