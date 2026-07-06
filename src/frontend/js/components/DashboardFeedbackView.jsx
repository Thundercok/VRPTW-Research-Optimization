import React, { useState, useEffect } from 'react';
import { useAppContext } from '../context/AppContext.jsx';

export default function DashboardFeedbackView() {
  const { state, toast, request } = useAppContext();

  // Feedback Form State
  const [feedbackCategory, setFeedbackCategory] = useState('general');
  const [feedbackRating, setFeedbackRating] = useState('');
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [feedbackContact, setFeedbackContact] = useState('');
  const [feedbackStatusText, setFeedbackStatusText] = useState('');

  // Feedback Review List State
  const [feedbackList, setFeedbackList] = useState([]);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [devNotes, setDevNotes] = useState({});

  // Fetch Feedback Inbox list
  const loadFeedback = async () => {
    setFeedbackLoading(true);
    try {
      const res = await request('/admin/feedback');
      setFeedbackList(res.items || []);
    } catch (e) {
      console.warn('Failed to load feedback in Dashboard:', e);
    } finally {
      setFeedbackLoading(false);
    }
  };

  useEffect(() => {
    loadFeedback();
  }, []);

  // Submit Feedback handler
  const submitFeedback = async (e) => {
    e.preventDefault();
    if (!feedbackMessage.trim()) return;

    if (feedbackMessage.trim().length < 3) {
      toast('Validation Error', state.lang === 'vn' ? 'Nội dung phản hồi phải từ 3 ký tự trở lên.' : 'Feedback message must be at least 3 characters.', 'error');
      setFeedbackStatusText(state.lang === 'vn' ? 'Gửi thất bại: Nội dung quá ngắn' : 'Submit failed: Message too short');
      return;
    }

    setFeedbackStatusText(state.lang === 'vn' ? 'Đang gửi...' : 'Sending...');
    try {
      await request('/feedback', {
        method: 'POST',
        body: JSON.stringify({
          page: 'app-dashboard',
          language: state.lang === 'vn' ? 'vn' : 'en',
          category: feedbackCategory,
          message: feedbackMessage.trim(),
          contact: feedbackContact.trim(),
          rating: feedbackRating ? Number(feedbackRating) : null
        })
      });
      setFeedbackMessage('');
      setFeedbackContact('');
      setFeedbackRating('');
      toast('Feedback Sent', 'Thank you for your feedback!', 'ok');
      setFeedbackStatusText(state.lang === 'vn' ? 'Đã gửi feedback. Cảm ơn bạn!' : 'Feedback sent. Thank you!');
      loadFeedback();
    } catch (err) {
      setFeedbackStatusText(state.lang === 'vn' ? 'Gửi thất bại' : 'Submit failed');
      toast('Error', err.message, 'error');
    }
  };

  // Dev Check / Update Reply note handler
  const handleUpdateFeedback = async (id) => {
    const devNote = devNotes[id] || '';
    try {
      await request(`/admin/feedback/${id}`, {
        method: 'POST',
        body: JSON.stringify({
          status: 'checked',
          developer_note: devNote
        })
      });
      toast('Feedback Updated', 'Developer response saved.', 'ok');
      loadFeedback();
    } catch (err) {
      toast('Update Failed', err.message, 'error');
    }
  };

  return (
    <div className="settings-view-container" style={{ padding: '24px' }}>
      <div className="settings-view-header" style={{ marginBottom: '24px' }}>
        <h2>{state.lang === 'vn' ? '💬 Ý Kiến Phản Hồi & Đóng Góp Ý Tưởng' : '💬 Anonymous Feedback & Developer Hub'}</h2>
        <p className="section-desc">
          {state.lang === 'vn' 
            ? 'Gửi ý kiến đóng góp ẩn danh của bạn để cải thiện hệ thống, hoặc duyệt danh sách góp ý để phản hồi của nhà phát triển.' 
            : 'Send private suggestions or bugs, and review operator submissions directly from this developer hub.'}
        </p>
      </div>

      <div className="settings-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '24px', alignItems: 'start' }}>
        {/* Anonymous Feedback Form Card */}
        <div className="saas-card settings-card">
          <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px' }}>
            {state.lang === 'vn' ? '📝 Gửi Góp Ý Mới' : '📝 Submit Feedback'}
          </h3>
          <p className="card-desc" style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            {state.lang === 'vn' ? 'Gửi ý kiến ẩn danh. Đội ngũ phát triển sẽ kiểm tra và cập nhật code.' : 'No login required. Stored anonymously for developer review.'}
          </p>
          <form onSubmit={submitFeedback} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '12px' }}>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>{state.lang === 'vn' ? 'Danh mục' : 'Category'}</label>
                <select 
                  className="saas-select" 
                  value={feedbackCategory} 
                  onChange={(e) => setFeedbackCategory(e.target.value)}
                  style={{ padding: '8px', fontSize: '13px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-soft)' }}
                >
                  <option value="general">{state.lang === 'vn' ? 'Chung' : 'General'}</option>
                  <option value="bug">{state.lang === 'vn' ? 'Lỗi' : 'Bug'}</option>
                  <option value="idea">{state.lang === 'vn' ? 'Ý tưởng' : 'Idea'}</option>
                  <option value="performance">{state.lang === 'vn' ? 'Hiệu năng' : 'Performance'}</option>
                </select>
              </div>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>{state.lang === 'vn' ? 'Đánh giá' : 'Rating'}</label>
                <select 
                  className="saas-select" 
                  value={feedbackRating} 
                  onChange={(e) => setFeedbackRating(e.target.value)}
                  style={{ padding: '8px', fontSize: '13px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-soft)' }}
                >
                  <option value="">{state.lang === 'vn' ? 'Tùy chọn' : 'Optional'}</option>
                  <option value="5">5 ★</option>
                  <option value="4">4 ★</option>
                  <option value="3">3 ★</option>
                  <option value="2">2 ★</option>
                  <option value="1">1 ★</option>
                </select>
              </div>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>{state.lang === 'vn' ? 'Nội dung phản hồi' : 'Feedback Message'}</label>
              <textarea 
                className="saas-textarea" 
                rows="5" 
                placeholder={state.lang === 'vn' ? 'Nhập ý kiến đóng góp của bạn...' : 'Tell us what to improve...'}
                value={feedbackMessage} 
                onChange={(e) => setFeedbackMessage(e.target.value)}
                required
                style={{ resize: 'none', padding: '8px', fontSize: '13px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-soft)' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>{state.lang === 'vn' ? 'Thông tin liên hệ (tùy chọn)' : 'Contact (optional)'}</label>
              <input 
                type="text" 
                className="saas-input" 
                placeholder="email@example.com"
                value={feedbackContact} 
                onChange={(e) => setFeedbackContact(e.target.value)}
                style={{ padding: '8px', fontSize: '13px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-soft)' }}
              />
            </div>

            <button type="submit" className="btn-primary" style={{ marginTop: '8px', padding: '10px', fontSize: '13px', fontWeight: 600 }}>
              {state.lang === 'vn' ? 'Gửi Góp Ý' : 'Send Feedback'}
            </button>
            {feedbackStatusText && <p style={{ fontSize: '12px', color: 'var(--primary)', marginTop: '4px', fontWeight: 600 }}>{feedbackStatusText}</p>}
          </form>
        </div>

        {/* Developer Feedback Review (Inbox) Card */}
        <div className="saas-card settings-card" style={{ maxHeight: 'calc(85vh - 120px)', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '8px', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
              {state.lang === 'vn' ? '📬 Thư Đã Nhận (Dev review)' : '📬 Feedback Inbox (Dev Review)'}
            </h3>
            <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '12px' }} onClick={loadFeedback} disabled={feedbackLoading}>
              🔄 {state.lang === 'vn' ? 'Tải lại' : 'Refresh'}
            </button>
          </div>
          
          {feedbackLoading ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{state.lang === 'vn' ? 'Đang tải phản hồi...' : 'Loading feedback...'}</p>
          ) : feedbackList.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{state.lang === 'vn' ? 'Chưa có phản hồi nào.' : 'No feedback entries yet.'}</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {feedbackList.map((item) => (
                <div key={item.id} style={{ 
                  padding: '14px', 
                  background: 'var(--bg-soft, #f8fafc)', 
                  borderRadius: '10px', 
                  border: '1px solid var(--border)',
                  fontSize: '13px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)' }}>
                    <span>
                      📅 {item.created_at ? new Date(item.created_at * 1000).toLocaleString() : '—'} | 🏷️ {item.category} {item.rating ? `| ⭐ ${item.rating}/5` : ''}
                    </span>
                    <span style={{ 
                      padding: '2px 6px', 
                      borderRadius: '4px', 
                      background: item.status === 'checked' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      color: item.status === 'checked' ? '#10b981' : '#f59e0b',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      fontSize: '10px'
                    }}>
                      {item.status === 'checked' ? (state.lang === 'vn' ? 'Đã duyệt' : 'Done') : (state.lang === 'vn' ? 'Mới' : 'New')}
                    </span>
                  </div>

                  <div style={{ fontWeight: 500, color: 'var(--text-main)', wordBreak: 'break-word' }}>
                    {item.message}
                  </div>

                  {item.contact && (
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      📧 {state.lang === 'vn' ? 'Liên hệ:' : 'Contact:'} <strong>{item.contact}</strong>
                    </div>
                  )}

                  {/* Dev Action/Reply Block */}
                  <div style={{ 
                    marginTop: '6px', 
                    paddingTop: '8px', 
                    borderTop: '1px dashed var(--border)', 
                    display: 'flex', 
                    flexDirection: 'column', 
                    gap: '6px' 
                  }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <input 
                        type="text" 
                        className="saas-input" 
                        placeholder={state.lang === 'vn' ? 'Nhập phản hồi (ví dụ: Đã sửa code, cảm ơn đề xuất!)' : 'Enter dev reply note...'}
                        value={devNotes[item.id] !== undefined ? devNotes[item.id] : (item.developer_note || '')}
                        onChange={(e) => setDevNotes(prev => ({ ...prev, [item.id]: e.target.value }))}
                        style={{ padding: '6px 10px', fontSize: '12px', flex: 1, borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-soft)' }}
                      />
                      <button 
                        className="btn-primary" 
                        onClick={() => handleUpdateFeedback(item.id)}
                        style={{ padding: '6px 12px', fontSize: '12px', fontWeight: 600 }}
                      >
                        ✓ {state.lang === 'vn' ? 'Duyệt & Phản Hồi' : 'Resolve & Reply'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
