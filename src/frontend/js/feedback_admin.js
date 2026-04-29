import { API_BASE } from './constants.js';
import { getDemoLang, toggleDemoLang } from './demoLang.js';

const I18N = {
  en: {
    'lang-toggle': 'VN',
    'feedback-admin-tag': 'ADMIN',
    'feedback-admin-badge': 'Feedback Inbox',
    'feedback-admin-title': 'Anonymous Feedback',
    'feedback-admin-lead': 'Review anonymous feedback submitted from the demo form and refresh as needed.',
    'feedback-admin-refresh': 'Refresh',
    'feedback-col-when': 'When',
    'feedback-col-category': 'Category',
    'feedback-col-message': 'Message',
    'feedback-col-rating': 'Rating',
    'feedback-col-contact': 'Contact',
    countLabel: (count) => `${count} entries`,
    ready: 'Ready.',
    loading: 'Loading feedback...',
    empty: 'No feedback yet.',
    unauthorized: 'Admin access required. Please log in as admin.',
  },
  vn: {
    'lang-toggle': 'EN',
    'feedback-admin-tag': 'QUAN TRI',
    'feedback-admin-badge': 'Hop thu phan hoi',
    'feedback-admin-title': 'Feedback an danh',
    'feedback-admin-lead': 'Xem cac feedback an danh tu demo va lam moi khi can.',
    'feedback-admin-refresh': 'Lam moi',
    'feedback-col-when': 'Thoi gian',
    'feedback-col-category': 'Danh muc',
    'feedback-col-message': 'Noi dung',
    'feedback-col-rating': 'Danh gia',
    'feedback-col-contact': 'Lien he',
    countLabel: (count) => `${count} muc`,
    ready: 'San sang.',
    loading: 'Dang tai feedback...',
    empty: 'Chua co feedback.',
    unauthorized: 'Can quyen admin. Vui long dang nhap bang tai khoan admin.',
  },
};

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderLanguage(lang) {
  const dict = I18N[lang] || I18N.en;
  document.documentElement.lang = lang === 'vn' ? 'vi' : 'en';
  Object.entries(dict).forEach(([id, text]) => {
    if (typeof text !== 'string') return;
    const node = document.getElementById(id);
    if (node) node.textContent = text;
  });

  const toggle = document.getElementById('lang-toggle');
  if (toggle) {
    toggle.title = lang === 'vn' ? 'Chuyen sang tieng Anh' : 'Switch to Vietnamese';
    toggle.setAttribute('aria-label', lang === 'vn' ? 'Chuyen sang tieng Anh' : 'Switch language');
  }
}

function setStatus(message) {
  const status = document.getElementById('feedback-admin-status');
  if (status) status.textContent = message;
}

function setCount(count, lang) {
  const node = document.getElementById('feedback-admin-count');
  if (!node) return;
  const dict = I18N[lang] || I18N.en;
  node.textContent = dict.countLabel(count);
}

function renderRows(items, lang) {
  const tbody = document.getElementById('feedback-admin-rows');
  if (!tbody) return;
  tbody.replaceChildren();

  if (!items.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 5;
    cell.textContent = (I18N[lang] || I18N.en).empty;
    row.appendChild(cell);
    tbody.appendChild(row);
    return;
  }

  items.forEach((item) => {
    const tr = document.createElement('tr');
    const when = item?.created_at ? new Date(Number(item.created_at) * 1000).toLocaleString() : '-';
    const rating = item?.rating ? String(item.rating) : '-';
    tr.innerHTML = `
      <td>${escapeHtml(String(when))}</td>
      <td>${escapeHtml(String(item?.category || '-'))}</td>
      <td>${escapeHtml(String(item?.message || '-'))}</td>
      <td>${escapeHtml(String(rating))}</td>
      <td>${escapeHtml(String(item?.contact || '-'))}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadFeedback(lang) {
  const dict = I18N[lang] || I18N.en;
  setStatus(dict.loading);

  const headers = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('vrptw_token') || '';
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const response = await fetch(`${API_BASE}/admin/feedback`, { method: 'GET', headers });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const message = body?.detail || `HTTP ${response.status}`;
      if (response.status === 401 || response.status === 403) {
        setStatus(dict.unauthorized);
        setCount(0, lang);
        renderRows([], lang);
        return;
      }
      throw new Error(message);
    }

    const data = await response.json();
    const items = Array.isArray(data?.items) ? data.items : [];
    setCount(items.length, lang);
    renderRows(items, lang);
    setStatus(dict.ready);
  } catch (error) {
    setStatus(String(error?.message || error || 'Failed to load feedback.'));
  }
}

function main() {
  let lang = getDemoLang();
  renderLanguage(lang);
  loadFeedback(lang);

  const toggle = document.getElementById('lang-toggle');
  toggle?.addEventListener('click', () => {
    lang = toggleDemoLang();
    renderLanguage(lang);
    loadFeedback(lang);
  });

  const refresh = document.getElementById('feedback-admin-refresh');
  refresh?.addEventListener('click', () => loadFeedback(lang));
}

main();
