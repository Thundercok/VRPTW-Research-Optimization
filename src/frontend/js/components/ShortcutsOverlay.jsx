import React, { useEffect } from 'react';
import { useAppContext } from '../context/AppContext.jsx';
import { SHORTCUTS } from '../shortcuts.js';

export const SHORTCUTS_EVENT = 'vrptw:toggle-shortcuts';

export function openShortcutsOverlay() {
  window.dispatchEvent(new CustomEvent(SHORTCUTS_EVENT, { detail: { open: true } }));
}

export default function ShortcutsOverlay({ open, onClose }) {
  const { t } = useAppContext();

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="shortcuts-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="shortcuts-panel" onClick={(e) => e.stopPropagation()}>
        <div className="shortcuts-head">
          <h3>{t('setShortcuts')}</h3>
          <button className="tour-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <p className="card-desc">{t('setShortcutsDesc')}</p>
        <ul className="shortcuts-list">
          {SHORTCUTS.map((s) => (
            <li key={s.id}>
              <span className="shortcut-desc">{t(s.labelKey)}</span>
              <span className="shortcut-keys">
                {s.keys.map((k) => (
                  <kbd key={k}>{k}</kbd>
                ))}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
