import { App } from './App.js';

// --- Inside your js/main.js ---

// 1. Safe Auth Listeners (Only run if the user is on auth.html)
const loginBtn = document.getElementById('btn-login');
if (loginBtn) {
  loginBtn.addEventListener('click', async () => {
    // Your existing login logic
    // IMPORTANT: You no longer need to manually toggle .hidden classes
    // to show the dashboard. The window.location redirect in auth.html handles it.
  });
}

// 2. Safe Dashboard Listeners (Only run if the user is on app.html)
const runModelBtn = document.getElementById('run-model');
if (runModelBtn) {
  runModelBtn.addEventListener('click', () => {
    // Your existing model execution logic
  });
}

const logoutBtn = document.getElementById('btn-logout');
if (logoutBtn) {
  logoutBtn.addEventListener('click', () => {
    firebaseAuth()
      .signOut()
      .then(() => {
        // The auth guard in app.html will automatically catch this
        // and kick them back to auth.html.
      });
  });
}

function wireHelpModal() {
  const button = document.getElementById('help-button');
  const modal = document.getElementById('help-modal');
  const closeBtn = document.getElementById('help-modal-close');
  if (!button || !modal) return;

  const open = () => {
    modal.classList.remove('hidden');
    if (typeof window.vrptwTrack === 'function') window.vrptwTrack('help_open', {});
  };
  const close = () => modal.classList.add('hidden');

  button.addEventListener('click', open);
  closeBtn?.addEventListener('click', close);
  modal.addEventListener('click', (event) => {
    if (event.target === modal) close();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
      close();
    }
    if (event.shiftKey && event.key === '?') {
      event.preventDefault();
      modal.classList.contains('hidden') ? open() : close();
    }
  });

  if (!sessionStorage.getItem('vrptw.help_seen')) {
    sessionStorage.setItem('vrptw.help_seen', '1');
    setTimeout(open, 600);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new App();
  wireHelpModal();
});
