import React, { useState, useEffect } from 'react';
import { useAppContext } from '../context/AppContext.jsx';

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

export default function FeedbackAdminView() {
  const { state, setLang, request, toast } = useAppContext();
  const lang = state.lang === 'vn' ? 'vn' : 'en';
  const dict = I18N[lang];

  const [items, setItems] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusText, setStatusText] = useState(dict.loading);

  const loadFeedback = async (currentLang) => {
    const currentDict = I18N[currentLang] || I18N.en;
    setStatusText(currentDict.loading);

    try {
      // Endpoint is /admin/feedback
      const data = await request('/admin/feedback', { method: 'GET' });
      const feedbackItems = Array.isArray(data?.items) ? data.items : [];
      setItems(feedbackItems);
      setStatusText(currentDict.ready);
    } catch (error) {
      if (error?.message?.includes('HTTP 401') || error?.message?.includes('HTTP 403')) {
        setStatusText(currentDict.unauthorized);
        setItems([]);
      } else {
        setStatusText(error?.message || 'Failed to load feedback.');
        toast('Load Failed', error?.message || 'Could not fetch anonymous feedback.', 'error');
      }
    }
  };

  useEffect(() => {
    loadFeedback(lang);
    document.documentElement.lang = lang === 'vn' ? 'vi' : 'en';
  }, [lang]);

  const handleToggleLang = () => {
    setLang(lang === 'vn' ? 'en' : 'vn');
  };

  const handleRefresh = () => {
    loadFeedback(lang);
  };

  return (
    <>
      <a className="back-to-landing" href="app.html" title="Back to demo">&larr; Demo</a>
      <button
        id="lang-toggle"
        className="lang-fab"
        type="button"
        onClick={handleToggleLang}
        title={lang === 'vn' ? 'Chuyen sang tieng Anh' : 'Switch to Vietnamese'}
        aria-label={lang === 'vn' ? 'Chuyen sang tieng Anh' : 'Switch language'}
      >
        {dict['lang-toggle']}
      </button>

      <main className="feedback-screen auth-screen">
        <section className="auth-card feedback-card">
          <div className="feedback-copy">
            <p className="tag" id="feedback-admin-tag">{dict['feedback-admin-tag']}</p>
            <p className="feedback-badge" id="feedback-admin-badge">{dict['feedback-admin-badge']}</p>
            <h1 id="feedback-admin-title">{dict['feedback-admin-title']}</h1>
            <p id="feedback-admin-lead" className="feedback-lead">
              {dict['feedback-admin-lead']}
            </p>
          </div>

          <div className="feedback-actions">
            <button
              id="feedback-admin-refresh"
              className="btn ghost"
              type="button"
              onClick={handleRefresh}
            >
              {dict['feedback-admin-refresh']}
            </button>
            <span id="feedback-admin-count" className="status">
              {dict.countLabel(items.length)}
            </span>
          </div>

          <div className="table-wrap feedback-inbox-table">
            <table>
              <thead>
                <tr>
                  <th id="feedback-col-when">{dict['feedback-col-when']}</th>
                  <th id="feedback-col-category">{dict['feedback-col-category']}</th>
                  <th id="feedback-col-message">{dict['feedback-col-message']}</th>
                  <th id="feedback-col-rating">{dict['feedback-col-rating']}</th>
                  <th id="feedback-col-contact">{dict['feedback-col-contact']}</th>
                </tr>
              </thead>
              <tbody id="feedback-admin-rows">
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                      {dict.empty}
                    </td>
                  </tr>
                ) : (
                  items.map((item, index) => {
                    const whenStr = item?.created_at
                      ? new Date(Number(item.created_at) * 1000).toLocaleString()
                      : '-';
                    const ratingStr = item?.rating ? String(item.rating) : '-';
                    return (
                      <tr key={item?.id || index}>
                        <td>{whenStr}</td>
                        <td>{item?.category || '-'}</td>
                        <td>{item?.message || '-'}</td>
                        <td>{ratingStr}</td>
                        <td>{item?.contact || '-'}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <p id="feedback-admin-status" className="status">{statusText}</p>
        </section>
      </main>
    </>
  );
}
