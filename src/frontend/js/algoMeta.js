/**
 * Single source of truth for algorithm display metadata.
 *
 * The label and colour tables used to be copy-pasted into MapController,
 * GanttController and App.js. Adding a solver meant editing three places and
 * discovering the miss only when a dropdown rendered a raw key like
 * `hybrid_ddqn_transfer_dr`.
 */

export const ALGO_LABELS = {
  ddqn: 'Hybrid DDQN (Transfer)',
  alns: 'ALNS Base',
  ortools: 'OR-Tools',
  hybrid_fixed: 'Hybrid Fixed',
  hybrid_ddqn: 'Hybrid DDQN (Random)',
  hybrid_ddqn_transfer_rc1: 'Hybrid DDQN (RC1)',
  hybrid_ddqn_transfer_dr: 'Hybrid DDQN (DR)',
  hybrid: 'Hybrid DDQN',
};

export const ALGO_COLORS = {
  ddqn: '#0b8a65',
  alns: '#2563eb',
  ortools: '#e11d48',
  hybrid_fixed: '#d97706',
  hybrid_ddqn: '#7c3aed',
  hybrid_ddqn_transfer_rc1: '#0284c7',
  hybrid_ddqn_transfer_dr: '#4f46e5',
  hybrid: '#0b8a65',
};

/** Overlay every comparison card measures against. */
export const BASELINE_ALGO = 'alns';

/** Overlay preferred on a fresh result set, when the backend returned it. */
export const PREFERRED_ALGO = 'ddqn';

export function algoLabel(key) {
  return ALGO_LABELS[key] || key;
}

export function algoColor(key) {
  return ALGO_COLORS[key] || '#6b7280';
}

/**
 * Overlay keys a result set can offer, in a stable order: the preferred
 * overlay first, the baseline second, everything else in backend order.
 * `Object.keys` order alone would let a solver failure silently reshuffle the
 * dropdown between two runs of the same instance.
 */
export function overlayKeysFor(result) {
  if (!result) return [];
  const keys = Object.keys(result).filter((k) => result[k] && Array.isArray(result[k].routes));
  const head = [PREFERRED_ALGO, BASELINE_ALGO].filter((k) => keys.includes(k));
  return [...head, ...keys.filter((k) => !head.includes(k))];
}

/** Overlay to select for a result set, keeping the operator's pick when it survived the re-solve. */
export function resolveActiveOverlay(result, current) {
  const keys = overlayKeysFor(result);
  if (!keys.length) return PREFERRED_ALGO;
  if (current && keys.includes(current)) return current;
  return keys[0];
}
