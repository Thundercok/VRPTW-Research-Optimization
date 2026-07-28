import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export const TOUR_STORAGE_KEY = 'vrptw_onboarding_complete';
export const TOUR_START_EVENT = 'vrptw:start-tour';

/** Fired by Settings (and anything else) to replay the tour on demand. */
export function startOnboardingTour() {
  localStorage.setItem(TOUR_STORAGE_KEY, 'false');
  window.dispatchEvent(new CustomEvent(TOUR_START_EVENT));
}

const ICONS = {
  compass: (
    <>
      <circle cx="12" cy="12" r="9" />
      <polygon points="15.5 8.5 10.5 10.5 8.5 15.5 13.5 13.5 15.5 8.5" />
    </>
  ),
  layers: (
    <>
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </>
  ),
  database: (
    <>
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5" />
      <path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3" />
    </>
  ),
  spark: (
    <>
      <polygon points="13 2 4 14 11 14 10 22 20 10 13 10 13 2" />
    </>
  ),
  table: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <line x1="9" y1="10" x2="9" y2="20" />
    </>
  ),
  brain: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
    </>
  ),
  truck: (
    <>
      <rect x="1" y="5" width="14" height="12" />
      <polygon points="15 9 19 9 22 12 22 17 15 17 15 9" />
      <circle cx="5.5" cy="19" r="2" />
      <circle cx="18.5" cy="19" r="2" />
    </>
  ),
  chart: (
    <>
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </>
  ),
  gear: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6h.09A1.65 1.65 0 0 0 10 3.09V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </>
  ),
  flag: (
    <>
      <path d="M4 22V4c4-2 8 2 12 0v10c-4 2-8-2-12 0" />
      <line x1="4" y1="22" x2="4" y2="15" />
    </>
  ),
};

/**
 * Step targets are resolved lazily, after `tab` has been applied — several of
 * them (#dataset-select, #run-model) only exist while the dispatch view is
 * mounted, so the tour drives navigation rather than assuming it.
 */
const STEPS = [
  { key: 'welcome', icon: 'compass', target: null, tab: 'dispatch', hero: true },
  { key: 'zones', icon: 'layers', target: '.saas-nav', tab: 'dispatch', placement: 'right' },
  { key: 'dataset', icon: 'database', target: '#dataset-select', tab: 'dispatch' },
  { key: 'fleetSize', icon: 'truck', target: '.fleet-toggles', tab: 'dispatch' },
  { key: 'run', icon: 'spark', target: '#run-model', tab: 'dispatch' },
  { key: 'manifest', icon: 'table', target: '#btn-toggle-drawer', tab: 'dispatch' },
  { key: 'playground', icon: 'brain', target: '#btn-toggle-playground', tab: 'dispatch' },
  { key: 'fleet', icon: 'truck', target: '[data-tour="nav-fleet"]', tab: 'fleet', placement: 'right' },
  { key: 'analytics', icon: 'chart', target: '[data-tour="nav-analytics"]', tab: 'analytics', placement: 'right' },
  { key: 'settings', icon: 'gear', target: '[data-tour="nav-settings"]', tab: 'settings', placement: 'right' },
  { key: 'finish', icon: 'flag', target: null, tab: 'dispatch', hero: true },
];

const CARD_W = 384;
const CARD_H_EST = 226;
const PAD = 10;
const GAP = 18;

function computeCardPos(rect, placement) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  if (!rect) {
    return { top: Math.round(vh / 2 - CARD_H_EST / 2), left: Math.round(vw / 2 - CARD_W / 2), arrow: null };
  }

  const clampLeft = (l) => Math.max(16, Math.min(l, vw - CARD_W - 16));
  const clampTop = (tp) => Math.max(16, Math.min(tp, vh - CARD_H_EST - 16));

  // Prefer the requested side, then fall back to whichever edge has room.
  const fitsRight = rect.right + GAP + CARD_W < vw - 16;
  const fitsBelow = rect.bottom + GAP + CARD_H_EST < vh - 16;
  const fitsAbove = rect.top - GAP - CARD_H_EST > 16;

  if ((placement === 'right' && fitsRight) || (!placement && !fitsBelow && !fitsAbove && fitsRight)) {
    return {
      top: clampTop(rect.top + rect.height / 2 - CARD_H_EST / 2),
      left: rect.right + GAP,
      arrow: 'left',
    };
  }
  if (fitsBelow) {
    return { top: rect.bottom + GAP, left: clampLeft(rect.left - 12), arrow: 'top' };
  }
  if (fitsAbove) {
    return { top: rect.top - GAP - CARD_H_EST, left: clampLeft(rect.left - 12), arrow: 'bottom' };
  }
  if (fitsRight) {
    return { top: clampTop(rect.top), left: rect.right + GAP, arrow: 'left' };
  }
  return { top: clampTop(rect.top), left: clampLeft(rect.left - CARD_W - GAP), arrow: 'right' };
}

export default function OnboardingTour() {
  const { state, updateState, t } = useAppContext();
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);
  const [rect, setRect] = useState(null);
  const [entered, setEntered] = useState(false);
  const rafRef = useRef(0);

  const current = STEPS[step] || STEPS[0];
  const isLast = step === STEPS.length - 1;

  const open = useCallback(() => {
    setStep(0);
    setVisible(true);
    setEntered(false);
    requestAnimationFrame(() => setEntered(true));
  }, []);

  const finish = useCallback(() => {
    localStorage.setItem(TOUR_STORAGE_KEY, 'true');
    setEntered(false);
    setVisible(false);
    setRect(null);
  }, []);

  // First visit auto-start, plus an explicit replay event from Settings.
  useEffect(() => {
    const onStart = () => open();
    window.addEventListener(TOUR_START_EVENT, onStart);
    if (localStorage.getItem(TOUR_STORAGE_KEY) !== 'true') open();
    return () => window.removeEventListener(TOUR_START_EVENT, onStart);
  }, [open]);

  // Drive navigation so the step's target is actually mounted.
  useEffect(() => {
    if (!visible) return;
    if (current.tab && state.activeTab !== current.tab) {
      updateState({ activeTab: current.tab });
    }
  }, [visible, step]); // eslint-disable-line react-hooks/exhaustive-deps

  // Track the highlighted element. The target may mount a frame or two after
  // the tab switch, so this polls on animation frames while the tour is open.
  useEffect(() => {
    if (!visible) {
      setRect(null);
      return undefined;
    }
    const selector = current.target;
    const tick = () => {
      if (selector) {
        const el = document.querySelector(selector);
        const next = el ? el.getBoundingClientRect() : null;
        setRect((prev) => {
          if (!next) return prev === null ? prev : null;
          if (
            prev &&
            Math.abs(prev.top - next.top) < 0.5 &&
            Math.abs(prev.left - next.left) < 0.5 &&
            Math.abs(prev.width - next.width) < 0.5 &&
            Math.abs(prev.height - next.height) < 0.5
          ) {
            return prev;
          }
          return next;
        });
      } else {
        setRect((prev) => (prev === null ? prev : null));
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [visible, step, current.target]);

  // Keyboard: arrows to move, Esc to leave.
  useEffect(() => {
    if (!visible) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        finish();
      } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        e.preventDefault();
        setStep((s) => (s >= STEPS.length - 1 ? s : s + 1));
        if (isLast) finish();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setStep((s) => Math.max(0, s - 1));
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [visible, isLast, finish]);

  // Never compete with the login modal — a tour over a blocked app is noise.
  if (!visible || state.showLoginModal) return null;

  const pos = computeCardPos(rect, current.placement);
  const hole = rect
    ? {
        top: rect.top - PAD,
        left: rect.left - PAD,
        width: rect.width + PAD * 2,
        height: rect.height + PAD * 2,
      }
    : null;

  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    <div className={`tour-root ${entered ? 'is-in' : ''}`} role="dialog" aria-modal="true" aria-label={t('tourAria')}>
      {/* The scrim is one box whose huge spread shadow fills the rest of the
          screen, so the highlighted control stays perfectly crisp instead of
          sitting under a tinted layer. tour-root itself swallows stray clicks. */}
      <div
        className={`tour-scrim ${hole ? 'has-hole' : 'is-full'}`}
        style={hole ? { top: hole.top, left: hole.left, width: hole.width, height: hole.height } : undefined}
      />
      {hole && (
        <div className="tour-halo" style={{ top: hole.top, left: hole.left, width: hole.width, height: hole.height }} />
      )}

      <div
        className={`tour-card tour-card--${pos.arrow || 'center'} ${current.hero ? 'is-hero' : ''}`}
        style={{ top: pos.top, left: pos.left, width: CARD_W }}
      >
        {pos.arrow && <span className={`tour-arrow tour-arrow--${pos.arrow}`} />}

        <div className="tour-card-head">
          <span className="tour-badge">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {ICONS[current.icon]}
            </svg>
          </span>
          <div className="tour-card-heading">
            <span className="tour-eyebrow">
              {t('tourStepLabel')} {step + 1} / {STEPS.length}
            </span>
            <h3>{t(`tour_${current.key}_title`)}</h3>
          </div>
          <button className="tour-close" onClick={finish} aria-label={t('tourSkip')}>
            ✕
          </button>
        </div>

        <p className="tour-body">{t(`tour_${current.key}_desc`)}</p>

        <div className="tour-progress">
          <span className="tour-progress-fill" style={{ width: `${progress}%` }} />
        </div>

        <div className="tour-foot">
          <div className="tour-dots">
            {STEPS.map((s, i) => (
              <button
                key={s.key}
                type="button"
                className={`tour-dot ${i === step ? 'is-active' : ''} ${i < step ? 'is-done' : ''}`}
                onClick={() => setStep(i)}
                aria-label={`${t('tourStepLabel')} ${i + 1}`}
              />
            ))}
          </div>
          <div className="tour-actions">
            {step > 0 && (
              <button className="tour-btn tour-btn-ghost" onClick={() => setStep(step - 1)}>
                {t('tourBack')}
              </button>
            )}
            <button className="tour-btn tour-btn-ghost" onClick={finish}>
              {t('tourSkip')}
            </button>
            <button className="tour-btn tour-btn-primary" onClick={() => (isLast ? finish() : setStep(step + 1))}>
              {isLast ? t('tourDone') : t('tourNext')}
              {!isLast && <span className="tour-btn-chev">›</span>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
