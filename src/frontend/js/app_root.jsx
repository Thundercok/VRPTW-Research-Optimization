import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { AppContextProvider, useAppContext } from './context/AppContext.jsx';
import AppLayout from './components/AppLayout.jsx';
import LiveDispatchView from './components/LiveDispatchView.jsx';
import FleetConfigView from './components/FleetConfigView.jsx';
import ModelAnalyticsView from './components/ModelAnalyticsView.jsx';
import SettingsView from './components/SettingsView.jsx';
import LoadingOverlay from './components/LoadingOverlay.jsx';
import ToastContainer from './components/ToastContainer.jsx';
import AuthView from './components/AuthView.jsx';

function AppContent() {
  const { state, isLoadingUser } = useAppContext();

  if (isLoadingUser) {
    return (
      <div style={{
        display: 'flex',
        height: '100vh',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0f172a',
        color: '#f8fafc',
        fontFamily: 'sans-serif'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div className="spinner" style={{
            border: '4px solid rgba(255,255,255,0.1)',
            borderTop: '4px solid #3b82f6',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }}></div>
          <style>{`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}</style>
          <div>Loading NAMI Ops Dashboard...</div>
        </div>
      </div>
    );
  }

  return (
    <AppLayout>
      {state.activeTab === 'dispatch' && <LiveDispatchView />}
      {state.activeTab === 'fleet' && <FleetConfigView />}
      {state.activeTab === 'analytics' && <ModelAnalyticsView />}
      {state.activeTab === 'settings' && <SettingsView />}
      <LoadingOverlay />
      <ToastContainer />

      {/* Auth Modal Popup Overlay */}
      {state.showLoginModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          animation: 'fadeIn 0.3s ease-out',
          overflow: 'auto',
          padding: '20px'
        }}>
          <style>{`
            @keyframes fadeIn {
              from { opacity: 0; }
              to { opacity: 1; }
            }
          `}</style>
          <AuthView onClose={() => updateState({ showLoginModal: false })} />
        </div>
      )}
    </AppLayout>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <AppContextProvider>
    <AppContent />
  </AppContextProvider>
);
