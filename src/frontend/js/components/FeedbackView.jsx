import React, { useState, useEffect } from 'react';
import { useAppContext } from '../context/AppContext.jsx';

const I18N = {
  en: {
    'lang-button': 'VN',
    'feedback-badge': 'Anonymous channel',
    'feedback-title': 'Share anonymous feedback',
    'feedback-lead':
      'Send a private suggestion, bug report, or product idea. Admins can review entries later and use them to shape the roadmap.',
    'feedback-point-1': 'No login required.',
    'feedback-point-2': 'Messages are stored anonymously.',
    'feedback-point-3': 'Admins can review feedback in the demo app.',
    'feedback-category-label': 'Category',
    'feedback-message-label': 'Message',
    'feedback-rating-label': 'Rating',
    'feedback-contact-label': 'Contact (optional)',
    'feedback-submit': 'Send Feedback',
    'feedback-home-link': 'Home',
    'feedback-status': 'Ready to receive your feedback.',
  },
  vn: {
    'lang-button': 'EN',
    'feedback-badge': 'Kênh ẩn danh',
    'feedback-title': 'Gửi góp ý ẩn danh',
    'feedback-lead':
      'Gửi đề xuất riêng, báo lỗi hoặc ý tưởng sản phẩm. Admin sẽ xem được các phản hồi sau đó để phát triển roadmap.',
    'feedback-point-1': 'Không cần đăng nhập.',
    'feedback-point-2': 'Nội dung được lưu ẩn danh.',
    'feedback-point-3': 'Admin có thể xem feedback trong app demo.',
    'feedback-category-label': 'Danh mục',
    'feedback-message-label': 'Nội dung',
    'feedback-rating-label': 'Đánh giá',
    'feedback-contact-label': 'Liên hệ (không bắt buộc)',
    'feedback-submit': 'Gửi phản hồi',
    'feedback-home-link': 'Trang chủ',
    'feedback-status': 'Sẵn sàng nhận phản hồi của bạn.',
  },
};

export default function FeedbackView() {
  const { state, setLang, request, toast } = useAppContext();
  const lang = state.lang === 'vn' ? 'vn' : 'en';
  const dict = I18N[lang];

  const [category, setCategory] = useState('general');
  const [message, setMessage] = useState('');
  const [rating, setRating] = useState('');
  const [contact, setContact] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusText, setStatusText] = useState(dict['feedback-status']);

  useEffect(() => {
    setStatusText(dict['feedback-status']);
    document.documentElement.lang = lang === 'vn' ? 'vi' : 'en';
  }, [lang]);

  const handleToggleLang = () => {
    setLang(lang === 'vn' ? 'en' : 'vn');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) {
      setStatusText(lang === 'vn' ? 'Vui lòng nhập nội dung feedback.' : 'Please enter a feedback message.');
      return;
    }

    setIsSubmitting(true);
    setStatusText(lang === 'vn' ? 'Đang gửi...' : 'Sending...');

    const payload = {
      page: 'feedback',
      language: lang,
      category,
      message: message.trim(),
      contact: contact.trim(),
      rating: rating ? Number(rating) : null,
    };

    try {
      await request('/feedback', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setMessage('');
      setContact('');
      setRating('');
      setStatusText(lang === 'vn' ? 'Đã gửi feedback. Cảm ơn bạn!' : 'Feedback sent. Thank you!');
      toast('Feedback Sent', lang === 'vn' ? 'Cảm ơn phản hồi của bạn!' : 'Thank you for your feedback!', 'ok');
    } catch (error) {
      setStatusText(lang === 'vn' ? `Gửi thất bại: ${error.message}` : `Submit failed: ${error.message}`);
      toast('Submit Failed', error.message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <a className="back-to-landing" href="app.html" title="Back to demo">&larr; Demo</a>
      <button
        id="lang-toggle"
        className="lang-fab"
        type="button"
        onClick={handleToggleLang}
        title={lang === 'vn' ? 'Chuyển sang tiếng Anh' : 'Switch to Vietnamese'}
        aria-label={lang === 'vn' ? 'Chuyển sang tiếng Anh' : 'Switch language'}
      >
        {dict['lang-button']}
      </button>

      <main className="feedback-screen auth-screen">
        <section className="auth-card feedback-card">
          <div className="feedback-grid">
            <div className="feedback-copy">
              <p className="tag">PROJECT NAMI</p>
              <p className="feedback-badge" id="feedback-badge">{dict['feedback-badge']}</p>
              <h1 id="feedback-title">{dict['feedback-title']}</h1>
              <p id="feedback-lead" className="feedback-lead">
                {dict['feedback-lead']}
              </p>
              <ul className="feedback-points">
                <li id="feedback-point-1">{dict['feedback-point-1']}</li>
                <li id="feedback-point-2">{dict['feedback-point-2']}</li>
                <li id="feedback-point-3">{dict['feedback-point-3']}</li>
              </ul>
            </div>

            <form id="feedback-form" className="feedback-form" onSubmit={handleSubmit}>
              <label className="feedback-field" htmlFor="feedback-category">
                <span id="feedback-category-label">{dict['feedback-category-label']}</span>
                <select
                  id="feedback-category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  <option value="general">{lang === 'vn' ? 'Chung' : 'General'}</option>
                  <option value="bug">{lang === 'vn' ? 'Lỗi' : 'Bug'}</option>
                  <option value="idea">{lang === 'vn' ? 'Ý tưởng' : 'Idea'}</option>
                  <option value="data">{lang === 'vn' ? 'Dữ liệu / Demo' : 'Data / Demo'}</option>
                  <option value="performance">{lang === 'vn' ? 'Hiệu năng' : 'Performance'}</option>
                </select>
              </label>

              <label className="feedback-field" htmlFor="feedback-message">
                <span id="feedback-message-label">{dict['feedback-message-label']}</span>
                <textarea
                  id="feedback-message"
                  rows="7"
                  placeholder={lang === 'vn' ? 'Nhập nội dung góp ý...' : 'Tell us what to improve...'}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  required
                ></textarea>
              </label>

              <div className="feedback-row">
                <label className="feedback-field" htmlFor="feedback-rating">
                  <span id="feedback-rating-label">{dict['feedback-rating-label']}</span>
                  <select
                    id="feedback-rating"
                    value={rating}
                    onChange={(e) => setRating(e.target.value)}
                  >
                    <option value="">{lang === 'vn' ? 'Tùy chọn' : 'Optional'}</option>
                    <option value="5">{lang === 'vn' ? '5 - Xuất sắc' : '5 - Excellent'}</option>
                    <option value="4">{lang === 'vn' ? '4 - Tốt' : '4 - Good'}</option>
                    <option value="3">{lang === 'vn' ? '3 - Tạm ổn' : '3 - Okay'}</option>
                    <option value="2">{lang === 'vn' ? '2 - Cần cải thiện' : '2 - Needs work'}</option>
                    <option value="1">{lang === 'vn' ? '1 - Kém' : '1 - Poor'}</option>
                  </select>
                </label>

                <label className="feedback-field" htmlFor="feedback-contact">
                  <span id="feedback-contact-label">{dict['feedback-contact-label']}</span>
                  <input
                    id="feedback-contact"
                    type="text"
                    maxLength="120"
                    placeholder={lang === 'vn' ? 'Để lại email hoặc tên nếu muốn liên hệ lại' : 'Leave an email or name if you want follow-up'}
                    value={contact}
                    onChange={(e) => setContact(e.target.value)}
                  />
                </label>
              </div>

              <div className="feedback-actions">
                <button
                  id="feedback-submit"
                  className="btn primary"
                  type="submit"
                  disabled={isSubmitting}
                >
                  {dict['feedback-submit']}
                </button>
                <a className="btn ghost" href="index.html" id="feedback-home-link">
                  {dict['feedback-home-link']}
                </a>
              </div>

              <p id="feedback-status" className="status">{statusText}</p>
            </form>
          </div>
        </section>
      </main>
    </>
  );
}
