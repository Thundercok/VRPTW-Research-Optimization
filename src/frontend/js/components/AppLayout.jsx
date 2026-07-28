import React, { useCallback, useEffect, useState } from 'react';
import Sidebar from './Sidebar.jsx';
import Header from './Header.jsx';
import ShortcutsOverlay, { SHORTCUTS_EVENT } from './ShortcutsOverlay.jsx';
import { useAppContext } from '../context/AppContext.jsx';
import { createShortcutHandler } from '../shortcuts.js';
import { exportWorkspace } from '../workspace.js';
import { startOnboardingTour } from './OnboardingTour.jsx';

export default function AppLayout({ children }) {
  const { state, updateState, submitJob, toast } = useAppContext();
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  const handleExport = useCallback(() => {
    const counts = exportWorkspace(state);
    toast('Export Complete', `${counts.customers} stops and ${counts.fleet} vehicles saved to JSON.`, 'ok');
  }, [state, toast]);

  useEffect(() => {
    const handler = createShortcutHandler({
      run: () => submitJob(),
      exportWorkspace: handleExport,
      help: () => setShortcutsOpen((v) => !v),
      tour: () => startOnboardingTour(),
      goToTab: (tab) => updateState({ activeTab: tab }),
    });
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleExport, submitJob, updateState]);

  useEffect(() => {
    const onToggle = (e) => setShortcutsOpen(e.detail?.open ?? true);
    window.addEventListener(SHORTCUTS_EVENT, onToggle);
    return () => window.removeEventListener(SHORTCUTS_EVENT, onToggle);
  }, []);

  return (
    <div id="app-shell" className="saas-layout">
      <Sidebar />
      <main className="saas-main">
        <Header />
        {children}
      </main>
      <ShortcutsOverlay open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
}
