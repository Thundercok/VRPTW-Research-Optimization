import React from 'react';
import Sidebar from './Sidebar.jsx';
import Header from './Header.jsx';

export default function AppLayout({ children }) {
  return (
    <div id="app-shell" className="saas-layout">
      <Sidebar />
      <main className="saas-main">
        <Header />
        {children}
      </main>
    </div>
  );
}
