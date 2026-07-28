import React from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export default function ToastContainer() {
  const { toasts, setToasts } = useAppContext();

  // We don't have setToasts from useAppContext directly but let's assume we can remove toast locally
  // Wait, if setToasts is not exposed, we just need to hide it locally or add setToasts to Context.
  // Actually, we can just manage local hiding state.
  const [hidden, setHidden] = React.useState(new Set());

  const handleClose = (id) => {
    setHidden((prev) => new Set(prev).add(id));
  };

  const getIcon = (tone) => {
    if (tone === 'ok') return '✓';
    if (tone === 'warn') return '⚠';
    if (tone === 'error') return '✕';
    return 'ℹ';
  };

  return (
    <div id="toast-root" className="toast-root">
      {toasts.filter(t => !hidden.has(t.id)).map((toast) => (
        <div key={toast.id} className={`toast ${toast.tone}`} role={toast.tone === 'error' ? 'alert' : 'status'}>
          <div className="toast-icon">{getIcon(toast.tone)}</div>
          <div className="toast-content">
            <div className="toast-title">{toast.title || 'Notice'}</div>
            {toast.message && <div className="toast-message">{toast.message}</div>}
          </div>
          <button className="toast-close" onClick={() => handleClose(toast.id)}>×</button>
          <div className={`toast-progress toast-progress-${toast.tone}`} />
        </div>
      ))}
    </div>
  );
}
