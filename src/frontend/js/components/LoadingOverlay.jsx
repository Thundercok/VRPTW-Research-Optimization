import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export default function LoadingOverlay() {
  const { loadingState, cancelJob, t } = useAppContext();
  const [isMinimized, setIsMinimized] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);
  const consoleEndRef = useRef(null);

  // Keep track of active elapsed time counter
  useEffect(() => {
    if (loadingState.active) {
      setElapsed(0);
      const start = Date.now();
      timerRef.current = setInterval(() => {
        setElapsed(Math.round((Date.now() - start) / 1000));
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [loadingState.active]);

  // Auto-scroll console terminal to bottom on new logs
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [loadingState.logs]);

  if (!loadingState.active) return null;

  if (isMinimized) {
    return (
      <div 
        id="loading-launcher" 
        className="loading-launcher"
        onClick={() => setIsMinimized(false)}
        style={{ cursor: 'pointer' }}
      >
        <span className="loading-launcher-text">{t('loadingLauncher')}...</span>
      </div>
    );
  }

  return (
    <div id="loading" className="loading-overlay">
      <div id="loading-card" className="loading-card">
        <div className="loading-card-header">
          <h2 id="loading-title" className="loading-title">{t('loadingTitle')}</h2>
          <div className="loading-card-actions">
            <button 
              id="loading-minimize" 
              className="loading-action-btn" 
              title="Minimize"
              onClick={() => setIsMinimized(true)}
            >
              ─
            </button>
            <button 
              id="loading-cancel" 
              className="loading-action-btn loading-cancel-btn" 
              title="Cancel"
              onClick={cancelJob}
            >
              ✕
            </button>
          </div>
        </div>
        <p id="loading-subtitle" className="loading-subtitle">{t('loadingSubtitle')}</p>
        <p id="loading-phase" className="loading-phase">{loadingState.backend}</p>
        
        <div className="loading-track">
          <div className="loading-road-lines"></div>
          <div 
            id="loading-track-fill" 
            className="loading-track-fill" 
            style={{ width: `${loadingState.progress}%` }}
          ></div>
          <div 
            id="loading-truck" 
            className="loading-truck" 
            style={{ left: `calc(${loadingState.progress}% - 30px)` }}
          >
            <svg className="truck-svg" viewBox="0 0 120 60" width="60" height="30">
              <g className="truck-body">
                {/* Cabin */}
                <path d="M80,20 L95,20 L105,35 L105,50 L80,50 Z" fill="var(--primary)" />
                {/* Cabin Window */}
                <path d="M83,23 L93,23 L99,32 L83,32 Z" fill="#ffffff" opacity="0.8" />
                {/* Cargo Container */}
                <rect x="15" y="10" width="63" height="40" rx="3" fill="var(--text-main)" />
                {/* Connection pin */}
                <rect x="76" y="42" width="6" height="8" fill="#475569" />
              </g>
              {/* Exhaust Smoke Puffs */}
              <g className="exhaust">
                <rect x="10" y="44" width="6" height="4" fill="#64748b" />
                <circle className="smoke smoke-1" cx="4" cy="42" r="3" fill="#cbd5e1" opacity="0" />
                <circle className="smoke smoke-2" cx="0" cy="40" r="4" fill="#cbd5e1" opacity="0" />
                <circle className="smoke smoke-3" cx="-4" cy="38" r="5" fill="#cbd5e1" opacity="0" />
              </g>
              {/* Front/Back Wheels */}
              <g className="wheel wheel-back">
                <circle cx="32" cy="50" r="9" fill="#1e293b" />
                <circle cx="32" cy="50" r="4" fill="#e2e8f0" />
                <line x1="25" y1="50" x2="39" y2="50" stroke="#64748b" stroke-width="1.5" />
                <line x1="32" y1="43" x2="32" y2="57" stroke="#64748b" stroke-width="1.5" />
              </g>
              <g className="wheel wheel-front">
                <circle cx="90" cy="50" r="9" fill="#1e293b" />
                <circle cx="90" cy="50" r="4" fill="#e2e8f0" />
                <line x1="83" y1="50" x2="97" y2="50" stroke="#64748b" stroke-width="1.5" />
                <line x1="90" y1="43" x2="90" y2="57" stroke="#64748b" stroke-width="1.5" />
              </g>
            </svg>
          </div>
        </div>
        <div id="loading-percent" className="loading-percent">{Math.round(loadingState.progress)}%</div>

        {/* Real-time Console Log Terminal */}
        <div className="loading-console-wrapper">
          <div class="loading-console-header">
            <span>Live Solver Feed</span>
            <span class="loading-console-dot"></span>
          </div>
          <div id="loading-console" className="loading-console">
            {loadingState.logs.length === 0 ? (
              <div className="loading-console-line placeholder">Connecting to optimizer...</div>
            ) : (
              loadingState.logs.map((log, index) => (
                <div key={index} className="loading-console-line">{log}</div>
              ))
            )}
            <div ref={consoleEndRef} />
          </div>
        </div>

        <div className="loading-stats">
          <div>
            <span className="loading-stat-label">{t('loadingElapsed')}</span
            ><span id="loading-elapsed" className="loading-stat-value">{elapsed}s</span>
          </div>
          <div>
            <span className="loading-stat-label">{t('loadingBackend')}</span
            ><span id="loading-backend" className="loading-stat-value">{loadingState.backend}</span>
          </div>
          <div>
            <span className="loading-stat-label">{t('loadingCompute')}</span>
            <span id="loading-device" className="loading-stat-value">{loadingState.device}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
