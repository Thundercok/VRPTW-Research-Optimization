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

function AppContent() {
  const { state, isLoadingUser } = useAppContext();

  useEffect(() => {
    if (!isLoadingUser && !state.unlocked) {
      // Redirect to login if user is not authenticated or not guest
      window.location.replace('auth.html');
    }
  }, [isLoadingUser, state.unlocked]);

  if (isLoadingUser || !state.unlocked) {
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
    </AppLayout>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <AppContextProvider>
    <AppContent />
  </AppContextProvider>
);
