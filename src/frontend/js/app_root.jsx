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
import OnboardingTour from './components/OnboardingTour.jsx';

function AppContent() {
  const { state, isLoadingUser, t } = useAppContext();

  if (isLoadingUser) {
    return (
      <div style={{
        display: 'flex',
        height: '100vh',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--paper)',
        color: 'var(--ink-muted)',
        fontFamily: 'var(--font-sans)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div className="spinner" style={{
            border: '2px solid var(--rule)',
            borderTopColor: 'var(--pine)',
            borderRadius: '50%',
            width: '28px',
            height: '28px',
            animation: 'spin 0.8s linear infinite',
            margin: '0 auto 14px'
          }}></div>
          <style>{`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}</style>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.6875rem',
            fontWeight: 500,
            letterSpacing: '0.12em',
            textTransform: 'uppercase'
          }}>{t('loadingConsole')}</div>
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
      <OnboardingTour />

      {state.showLoginModal && (
        <div id="auth-screen" style={{
          position: 'fixed',
          inset: 0,
          display: 'flex',
          // flex-start + margin:auto on the card, NOT alignItems:center — a
          // centred child taller than the overlay has its top pushed outside
          // the scrollable area and can never be reached.
          alignItems: 'flex-start',
          justifyContent: 'center',
          zIndex: 9999,
          background: 'rgba(21, 26, 24, 0.55)',
          backdropFilter: 'blur(6px)',
          WebkitBackdropFilter: 'blur(6px)',
          animation: 'fadeIn 0.3s ease-out',
          overflowY: 'auto',
          padding: '24px'
        }}>
          <style>{`
            @keyframes fadeIn {
              from { opacity: 0; }
              to { opacity: 1; }
            }
          `}</style>
          <AuthView onClose={() => { window.location.href = 'index.html'; }} />
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
