/**
 * The single source of truth for global hotkeys.
 *
 * Settings renders this list and useGlobalShortcuts binds it, so the two can
 * never drift — the previous Settings card advertised keys nothing listened for.
 */
const MOD = /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent) ? '⌘' : 'Ctrl';

export const SHORTCUTS = [
  { id: 'help', keys: ['Shift', '?'], labelKey: 'setShortcutsHelp' },
  { id: 'run', keys: [MOD, 'S'], labelKey: 'setShortcutsRun' },
  { id: 'export', keys: [MOD, 'E'], labelKey: 'setShortcutsExport' },
  { id: 'tabs', keys: [MOD, '1 – 4'], labelKey: 'setShortcutsTabs' },
  { id: 'tour', keys: [MOD, '/'], labelKey: 'setShortcutsTour' },
];

const TAB_ORDER = ['dispatch', 'fleet', 'analytics', 'settings'];

/** True when the event came from a field where the key means something else. */
function isTypingTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable;
}

/**
 * @param {object} handlers  { run, exportWorkspace, help, tour, goToTab }
 * @returns {(e: KeyboardEvent) => void}
 */
export function createShortcutHandler(handlers) {
  return function onKeyDown(e) {
    const mod = e.ctrlKey || e.metaKey;

    // Shift+? is the one binding that must not fire mid-sentence.
    if (!mod && e.shiftKey && e.key === '?' && !isTypingTarget(e.target)) {
      e.preventDefault();
      handlers.help?.();
      return;
    }

    if (!mod) return;

    switch (e.key.toLowerCase()) {
      case 's':
        e.preventDefault();
        handlers.run?.();
        break;
      case 'e':
        e.preventDefault();
        handlers.exportWorkspace?.();
        break;
      case '/':
        e.preventDefault();
        handlers.tour?.();
        break;
      case '1':
      case '2':
      case '3':
      case '4':
        e.preventDefault();
        handlers.goToTab?.(TAB_ORDER[Number(e.key) - 1]);
        break;
      default:
        break;
    }
  };
}
