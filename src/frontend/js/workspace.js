/**
 * Workspace-level side effects shared by Settings and the global shortcuts.
 *
 * Everything here is deliberately free of React so the same action can be
 * triggered from a settings button, a hotkey, or the console.
 */

export const STORAGE_KEYS = {
  apiBase: 'vrptw_api_base',
  appTheme: 'vrptw_theme',
  landingTheme: 'vrptw_landing_theme_v2',
  mapTheme: 'vrptw_map_theme',
  lang: 'vrptw_demo_lang',
  sidebarCollapsed: 'vrptw_sidebar_collapsed',
  fleet: 'vrptw_fleet_config',
  onboarding: 'vrptw_onboarding_complete',
};

/** Keys the "reset preferences" action clears — session/auth keys are kept. */
const PREFERENCE_KEYS = [
  STORAGE_KEYS.apiBase,
  STORAGE_KEYS.appTheme,
  STORAGE_KEYS.landingTheme,
  STORAGE_KEYS.mapTheme,
  STORAGE_KEYS.lang,
  STORAGE_KEYS.sidebarCollapsed,
  STORAGE_KEYS.onboarding,
];

/** Applies the light/dark choice to the document and both storage keys. */
export function applyAppTheme(theme) {
  const value = theme === 'dark' ? 'dark' : 'light';
  localStorage.setItem(STORAGE_KEYS.appTheme, value);
  // The landing page reads its own key; keeping them in step means the marketing
  // site and the console do not flip themes as you move between them.
  localStorage.setItem(STORAGE_KEYS.landingTheme, value);
  document.documentElement.setAttribute('data-theme', value);
  return value;
}

/**
 * Applies the basemap style. Returns true when a live map was retiled, false
 * when only the preference was stored (dispatch view not mounted).
 */
export function applyMapTheme(theme) {
  const value = theme === 'carto-dark' ? 'carto-dark' : 'carto-light';
  localStorage.setItem(STORAGE_KEYS.mapTheme, value);
  const controller = window.app?.mapController;
  if (controller?.setTileTheme) {
    controller.setTileTheme(value);
    return true;
  }
  return false;
}

/**
 * Normalises what the user typed into an API base the fetch layer can use.
 * Returns null when the input cannot be understood.
 */
export function normalizeApiBase(raw) {
  const value = String(raw || '').trim();
  if (!value) return '';
  if (value.startsWith('/')) return value.replace(/\/+$/, '') || '/';

  let url;
  try {
    url = new URL(/^https?:\/\//i.test(value) ? value : `http://${value}`);
  } catch {
    return null;
  }
  const path = url.pathname.replace(/\/+$/, '');
  // A bare origin means the caller gave us the host only; the routers live
  // under /api, so append it rather than silently 404ing every request.
  return `${url.origin}${path || '/api'}`;
}

export function currentApiBase() {
  return localStorage.getItem(STORAGE_KEYS.apiBase) || '/api';
}

/** Downloads the whole workspace — data plus preferences — as one JSON file. */
export function exportWorkspace(state) {
  const payload = {
    exportedAt: new Date().toISOString(),
    schema: 'nami-workspace/1',
    mode: state?.mode ?? null,
    dataset: state?.selectedDataset ?? null,
    fleetSummary: { vehicles: state?.vehicles ?? null, capacity: state?.capacity ?? null },
    customers: state?.customers ?? [],
    fleet: state?.fleet ?? [],
    preferences: {
      language: localStorage.getItem(STORAGE_KEYS.lang) || 'en',
      appTheme: localStorage.getItem(STORAGE_KEYS.appTheme) || 'light',
      mapTheme: localStorage.getItem(STORAGE_KEYS.mapTheme) || 'carto-light',
      apiBase: localStorage.getItem(STORAGE_KEYS.apiBase) || null,
    },
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
  link.download = `nami-workspace-${stamp}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoking synchronously can cancel the download in some browsers.
  setTimeout(() => URL.revokeObjectURL(url), 2000);

  return { customers: payload.customers.length, fleet: payload.fleet.length };
}

/** Clears preferences only, leaving the signed-in session and data intact. */
export function resetPreferences() {
  PREFERENCE_KEYS.forEach((key) => localStorage.removeItem(key));
  applyAppTheme('light');
}
