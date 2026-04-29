import { API_BASE } from './constants.js';
import { getDemoLang, setDemoLang, toggleDemoLang } from './demoLang.js';

const I18N = {
  en: {
    'lang-toggle': 'VN',
    'feedback-badge': 'Anonymous channel',
    'feedback-title': 'Share anonymous feedback',
    'feedback-lead': 'Send a private suggestion, bug report, or product idea. Admins can review entries later and use them to shape the roadmap.',
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
    'lang-toggle': 'EN',
    'feedback-badge': 'Kênh ẩn danh',
    'feedback-title': 'Gửi góp ý ẩn danh',
    'feedback-lead': 'Gửi đề xuất riêng, báo lỗi hoặc ý tưởng sản phẩm. Admin sẽ xem được các phản hồi sau đó để phát triển roadmap.',
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

function renderLanguage(lang) {
  const dict = I18N[lang] || I18N.en;
  document.documentElement.lang = lang === 'vn' ? 'vi' : 'en';
  Object.entries(dict).forEach(([id, text]) => {
    const node = document.getElementById(id);
    if (node) node.textContent = text;
  });
  const submit = document.getElementById('feedback-submit');
  if (submit) submit.textContent = dict['feedback-submit'];
  const toggle = document.getElementById('lang-toggle');
  if (toggle) {
    toggle.title = lang === 'vn' ? 'Chuyển sang tiếng Anh' : 'Switch to Vietnamese';
    toggle.setAttribute('aria-label', lang === 'vn' ? 'Chuyển sang tiếng Anh' : 'Switch language');
  }

  const categoryOptions = document.querySelectorAll('#feedback-category option');
  if (categoryOptions.length >= 5) {
    categoryOptions[0].textContent = lang === 'vn' ? 'Chung' : 'General';
    categoryOptions[1].textContent = lang === 'vn' ? 'Lỗi' : 'Bug';
    categoryOptions[2].textContent = lang === 'vn' ? 'Ý tưởng' : 'Idea';
    categoryOptions[3].textContent = lang === 'vn' ? 'Dữ liệu / Demo' : 'Data / Demo';
    categoryOptions[4].textContent = lang === 'vn' ? 'Hiệu năng' : 'Performance';
  }

  const ratingOptions = document.querySelectorAll('#feedback-rating option');
  if (ratingOptions.length >= 6) {
    ratingOptions[0].textContent = lang === 'vn' ? 'Tùy chọn' : 'Optional';
    ratingOptions[1].textContent = lang === 'vn' ? '5 - Xuất sắc' : '5 - Excellent';
    ratingOptions[2].textContent = lang === 'vn' ? '4 - Tốt' : '4 - Good';
    ratingOptions[3].textContent = lang === 'vn' ? '3 - Tạm ổn' : '3 - Okay';
    ratingOptions[4].textContent = lang === 'vn' ? '2 - Cần cải thiện' : '2 - Needs work';
    ratingOptions[5].textContent = lang === 'vn' ? '1 - Kém' : '1 - Poor';
  }
}

async function main() {
  let lang = getDemoLang();
  renderLanguage(lang);

  const toggle = document.getElementById('lang-toggle');
  toggle?.addEventListener('click', () => {
    lang = toggleDemoLang();
    renderLanguage(lang);
  });

  const form = document.getElementById('feedback-form');
  const status = document.getElementById('feedback-status');
  const category = document.getElementById('feedback-category');
  const message = document.getElementById('feedback-message');
  const rating = document.getElementById('feedback-rating');
  const contact = document.getElementById('feedback-contact');
  const submitBtn = document.getElementById('feedback-submit');

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      page: 'feedback',
      language: lang,
      category: String(category?.value || 'general'),
      message: String(message?.value || '').trim(),
      contact: String(contact?.value || '').trim(),
      rating: rating?.value ? Number(rating.value) : null,
    };

    if (!payload.message) {
      if (status) status.textContent = lang === 'vn' ? 'Vui lòng nhập nội dung feedback.' : 'Please enter a feedback message.';
      return;
    }

    if (submitBtn) submitBtn.disabled = true;
    if (status) status.textContent = lang === 'vn' ? 'Đang gửi...' : 'Sending...';

    try {
      const response = await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || `HTTP ${response.status}`);
      }

      message.value = '';
      contact.value = '';
      rating.value = '';
      if (status) status.textContent = lang === 'vn' ? 'Đã gửi feedback. Cảm ơn bạn!' : 'Feedback sent. Thank you!';
    } catch (error) {
      if (status) status.textContent = lang === 'vn' ? `Gửi thất bại: ${error.message}` : `Submit failed: ${error.message}`;
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

setDemoLang(getDemoLang());
main();