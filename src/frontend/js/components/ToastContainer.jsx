import React from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export default function ToastContainer() {
  const { toasts } = useAppContext();
  return (
    <div id="toast-root" className="toast-root">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast ${toast.tone}`} role={toast.tone === 'error' ? 'alert' : 'status'}>
          <div className="toast-title">{toast.title || 'Notice'}</div>
          {toast.message && <div className="toast-message">{toast.message}</div>}
        </div>
      ))}
    </div>
  );
}
