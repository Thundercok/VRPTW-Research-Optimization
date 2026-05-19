import { App } from './App.js';

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
