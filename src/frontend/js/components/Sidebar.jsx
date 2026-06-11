import React from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export default function Sidebar() {
  const { state, updateState, logout, t } = useAppContext();

  const handleTabClick = (e, tab) => {
    e.preventDefault();
    updateState({ activeTab: tab });
  };

  return (
    <aside className="saas-sidebar">
      <div className="brand">
        <div className="brand-logo">N</div>
        <span className="brand-text">NAMI OPS</span>
      </div>

      <nav className="saas-nav">
        <p className="nav-label">Planning</p>
        <a 
          href="#" 
          className={`nav-item ${state.activeTab === 'dispatch' ? 'active' : ''}`}
          onClick={(e) => handleTabClick(e, 'dispatch')}
        >
          Live Dispatch
        </a>
        <a 
          href="#" 
          className={`nav-item ${state.activeTab === 'fleet' ? 'active' : ''}`}
          onClick={(e) => handleTabClick(e, 'fleet')}
        >
          Fleet Config
        </a>

        <p className="nav-label" style={{ marginTop: '24px' }}>Intelligence</p>
        <a 
          href="#" 
          className={`nav-item ${state.activeTab === 'analytics' ? 'active' : ''}`}
          onClick={(e) => handleTabClick(e, 'analytics')}
        >
          Model Analytics
        </a>
        <a 
          href="#" 
          className={`nav-item ${state.activeTab === 'settings' ? 'active' : ''}`}
          onClick={(e) => handleTabClick(e, 'settings')}
        >
          Settings
        </a>
      </nav>

      <div className="sidebar-footer">
        <a 
          href="index.html" 
          className="nav-item" 
          style={{ color: 'var(--text-muted)', marginBottom: '12px', fontSize: '12px' }}
        >
          &larr; Back to Home
        </a>
        <div className="user-badge" id="user-email">
          {state.email || 'guest@nami.local'}
        </div>
        <button id="btn-logout" className="btn-text" onClick={logout}>
          {t('logoutButton')}
        </button>
      </div>
    </aside>
  );
}
