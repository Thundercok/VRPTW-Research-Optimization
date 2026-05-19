const STORAGE_KEY = 'vrptw_demo_lang';

export function getDemoLang() {
  const value = localStorage.getItem(STORAGE_KEY);
  return value === 'vn' ? 'vn' : 'en';
}

export function setDemoLang(lang) {
  const next = lang === 'vn' ? 'vn' : 'en';
  localStorage.setItem(STORAGE_KEY, next);
  return next;
}

export function toggleDemoLang() {
  return setDemoLang(getDemoLang() === 'en' ? 'vn' : 'en');
}