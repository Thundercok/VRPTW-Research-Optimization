import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../context/AppContext.jsx';
import { firebaseService } from '../firebaseService.js';

export default function AuthView({ onClose }) {
  const { state, updateState, toast, setStatus, request, loginAsGuest, t } = useAppContext();

  // Local view state: 'login' | 'register' | 'forgot' | 'reset'
  const [view, setView] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('screen') || sessionStorage.getItem('vrptw_auth_screen') || 'login';
  });

  // Backend mode settings fetched from /health
  const [backendMode, setBackendMode] = useState({
    firebase_enabled: null,
    demo_mode: null,
    torch: null
  });

  // Login inputs
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginEmailError, setLoginEmailError] = useState(false);
  const [loginPasswordError, setLoginPasswordError] = useState(false);

  // Register inputs
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerOtp, setRegisterOtp] = useState('');
  const [registerEmailError, setRegisterEmailError] = useState(false);
  const [registerPasswordError, setRegisterPasswordError] = useState(false);
  const [registerOtpError, setRegisterOtpError] = useState(false);

  // Register OTP state
  const [registerOtpApprovedEmail, setRegisterOtpApprovedEmail] = useState('');
  const [registerOtpVerified, setRegisterOtpVerified] = useState(false);
  const [registerOtpExpiresAt, setRegisterOtpExpiresAt] = useState(0);
  const [otpCountdownText, setOtpCountdownText] = useState('');
  const [otpCountdownTone, setOtpCountdownTone] = useState('');
  const [isSendingRegisterOtp, setIsSendingRegisterOtp] = useState(false);

  // Forgot password inputs
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotEmailError, setForgotEmailError] = useState(false);

  // Reset password inputs
  const [resetPassword, setResetPassword] = useState('');
  const [resetPasswordConfirm, setResetPasswordConfirm] = useState('');
  const [resetPasswordError, setResetPasswordError] = useState(false);
  const [resetPasswordConfirmError, setResetPasswordConfirmError] = useState(false);

  // Timers refs
  const otpCountdownTimer = useRef(null);
  const otpVerifyDebounceTimer = useRef(null);

  // Theme & Password Visibility states
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('vrptw_theme') || localStorage.getItem('vrptw_landing_theme_v2') || 'dark';
  });

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('vrptw_theme', nextTheme);
    localStorage.setItem('vrptw_landing_theme_v2', nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  const [showPassword, setShowPassword] = useState(false);

  // Auto-fill test credentials helper
  const handleAutoFill = () => {
    if (localAuthDisabled) {
      handleGuestLogin();
      return;
    }
    setLoginEmail('test@vrptw.local');
    setLoginPassword('testpass123');
    setLoginEmailError(false);
    setLoginPasswordError(false);
    toast('Credentials Filled', 'Ready to sign in.', 'ok');
  };

  // Probe backend mode on mount
  useEffect(() => {
    async function probe() {
      try {
        const response = await fetch(`${window.location.origin}/health`, { method: 'GET' });
        if (!response.ok) {
          const apiBaseRes = await fetch(`${state.apiBase || 'http://localhost:8000'}/health`, { method: 'GET' });
          if (!apiBaseRes.ok) throw new Error();
          const data = await apiBaseRes.json();
          setBackendMode({
            firebase_enabled: 'firebase_enabled' in data ? Boolean(data.firebase_enabled) : true,
            demo_mode: 'demo_mode' in data ? Boolean(data.demo_mode) : false,
            torch: data.torch || null
          });
          return;
        }
        const data = await response.json();
        setBackendMode({
          firebase_enabled: 'firebase_enabled' in data ? Boolean(data.firebase_enabled) : true,
          demo_mode: 'demo_mode' in data ? Boolean(data.demo_mode) : false,
          torch: data.torch || null
        });
      } catch (e) {
        setBackendMode({
          firebase_enabled: null,
          demo_mode: null,
          torch: null
        });
      }
    }
    probe();
  }, []);

  // Sync URL query params with active view state
  useEffect(() => {
    const url = new URL(window.location.href);
    if (view === 'register' || view === 'forgot') {
      url.searchParams.set('screen', view);
      url.searchParams.delete('token');
    } else if (view === 'reset') {
      url.searchParams.set('screen', 'reset');
      if (state.resetToken) {
        url.searchParams.set('token', state.resetToken);
      }
    } else {
      url.searchParams.delete('screen');
      url.searchParams.delete('token');
    }
    sessionStorage.setItem('vrptw_auth_screen', view);
    window.history.replaceState({}, '', `${url.pathname}${url.search}`);
  }, [view, state.resetToken]);

  // Handle auto redirect if unlocked (only when on standalone auth page)
  useEffect(() => {
    if (state.unlocked && window.location.pathname.includes('auth.html')) {
      window.location.replace('app.html');
    }
  }, [state.unlocked]);

  // Clean error styles when switching views
  const changeView = (newView) => {
    setLoginEmailError(false);
    setLoginPasswordError(false);
    setRegisterEmailError(false);
    setRegisterPasswordError(false);
    setRegisterOtpError(false);
    setForgotEmailError(false);
    setResetPasswordError(false);
    setResetPasswordConfirmError(false);
    setView(newView);
  };

  const isValidEmail = (emailVal) => {
    return /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(emailVal);
  };

  // Helper to parse backend error responses
  const parseApiError = (err) => {
    const msg = String(err?.message || err || '').trim();
    if (!msg) return 'An error occurred';
    try {
      const parsed = JSON.parse(msg);
      return parsed.detail || parsed.message || msg;
    } catch {
      return msg;
    }
  };

  // OTP Validation countdown timer
  const startRegisterOtpCountdown = (expiresAt) => {
    if (otpCountdownTimer.current) clearInterval(otpCountdownTimer.current);

    const tick = () => {
      const remainMs = expiresAt - Date.now();
      if (remainMs <= 0) {
        clearInterval(otpCountdownTimer.current);
        setRegisterOtpApprovedEmail('');
        setRegisterOtpVerified(false);
        setRegisterOtpExpiresAt(0);
        setOtpCountdownText('OTP expired. Please click Send OTP again.');
        setOtpCountdownTone('expired');
        return;
      }
      const remainSec = Math.ceil(remainMs / 1000);
      const minutes = Math.floor(remainSec / 60);
      const seconds = remainSec % 60;
      setOtpCountdownText(`OTP valid for ${minutes}:${String(seconds).padStart(2, '0')}.`);
      setOtpCountdownTone('active');
    };

    tick();
    otpCountdownTimer.current = setInterval(tick, 1000);
  };

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (otpCountdownTimer.current) clearInterval(otpCountdownTimer.current);
      if (otpVerifyDebounceTimer.current) clearTimeout(otpVerifyDebounceTimer.current);
    };
  }, []);

  // Request Registration OTP
  const handleRequestOtp = async () => {
    if (isSendingRegisterOtp) return;
    const email = registerEmail.trim().toLowerCase();

    setRegisterEmailError(false);
    setRegisterOtpError(false);

    if (!email || !isValidEmail(email)) {
      setRegisterEmailError(true);
      setOtpCountdownText('Invalid email format.');
      setOtpCountdownTone('expired');
      toast('Invalid Email', 'Please enter a valid email.', 'error');
      return;
    }

    try {
      setIsSendingRegisterOtp(true);
      setOtpCountdownText('Sending OTP...');
      setOtpCountdownTone('active');

      const res = await request('/auth/register/request-otp', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });

      const expires = Date.now() + 10 * 60 * 1000;
      setRegisterOtpApprovedEmail(email);
      setRegisterOtpVerified(false);
      setRegisterOtpExpiresAt(expires);

      startRegisterOtpCountdown(expires);
      toast('OTP Sent', `Check your email for the code.`, 'ok');
      setStatus('Send OTP success. Please enter the 6-digit OTP.', 'ok');
    } catch (error) {
      setRegisterOtpApprovedEmail('');
      setRegisterOtpVerified(false);
      setRegisterOtpExpiresAt(0);
      setOtpCountdownText('Failed to send OTP.');
      setOtpCountdownTone('expired');
      setRegisterEmailError(true);
      toast('Failed to Send OTP', parseApiError(error), 'error');
    } finally {
      setIsSendingRegisterOtp(false);
    }
  };

  // Verify Registration OTP Real-time
  const verifyRegisterOtpApi = async (email, otp) => {
    try {
      await request('/auth/register/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ email, otp }),
      });
      setRegisterOtpVerified(true);
      setOtpCountdownText('OTP verified successfully.');
      setOtpCountdownTone('active');
      toast('OTP Verified', 'Ready to register.', 'ok');
    } catch (error) {
      setRegisterOtpVerified(false);
      setRegisterOtpError(true);
      setOtpCountdownText('Incorrect OTP.');
      setOtpCountdownTone('expired');
    }
  };

  const handleOtpInput = (e) => {
    const val = e.target.value.trim();
    setRegisterOtp(val);
    setRegisterOtpError(false);
    setRegisterOtpVerified(false);

    if (otpVerifyDebounceTimer.current) clearTimeout(otpVerifyDebounceTimer.current);

    const email = registerEmail.trim().toLowerCase();
    const isReady = registerOtpApprovedEmail === email && registerOtpExpiresAt > Date.now() && /^\d{6}$/.test(val);
    if (!isReady) return;

    otpVerifyDebounceTimer.current = setTimeout(() => {
      verifyRegisterOtpApi(email, val);
    }, 220);
  };

  // Perform Account Registration
  const handleRegister = async (e) => {
    e.preventDefault();
    const email = registerEmail.trim().toLowerCase();
    const password = registerPassword.trim();
    const otp = registerOtp.trim();

    if (!email || !password || !otp) return;

    try {
      await request('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, otp }),
      });

      toast('Registration Successful', 'Account created.', 'ok');
      setLoginEmail(email);
      setRegisterEmail('');
      setRegisterPassword('');
      setRegisterOtp('');
      setRegisterOtpApprovedEmail('');
      setRegisterOtpVerified(false);
      setRegisterOtpExpiresAt(0);
      changeView('login');
    } catch (error) {
      toast('Registration Failed', parseApiError(error), 'error');
    }
  };

  // Perform Email/Password Log In
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginEmailError(false);
    setLoginPasswordError(false);

    const email = loginEmail.trim().toLowerCase();
    const password = loginPassword.trim();

    if (!email) {
      setLoginEmailError(true);
      toast('Missing Field', 'Please enter your email.', 'error');
      return;
    }
    if (!password) {
      setLoginPasswordError(true);
      toast('Missing Field', 'Please enter your password.', 'error');
      return;
    }

    try {
      const firebaseUser = await firebaseService.loginUser(email, password);
      const token = await firebaseUser.getIdToken();
      updateState({
        token,
        email: firebaseUser.email,
        role: firebaseUser.email.includes('admin') ? 'admin' : 'operator',
        unlocked: true
      });
      toast('Login Successful', 'Authenticated via Firebase.', 'ok');
    } catch (err) {
      setLoginPasswordError(true);
      toast('Login Failed', err.message || 'Invalid credentials.', 'error');
    }
  };

  // Perform Guest Login
  const handleGuestLogin = () => {
    loginAsGuest();
  };

  // Forgot password
  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setForgotEmailError(false);
    const email = forgotEmail.trim().toLowerCase();
    if (!email || !isValidEmail(email)) {
      setForgotEmailError(true);
      toast('Invalid Email', 'Please enter a valid email address.', 'error');
      return;
    }
    try {
      // Endpoint to trigger Firebase or custom password reset email
      await request('/auth/forgot-password/request', {
        method: 'POST',
        body: JSON.stringify({ email })
      });
      toast('Reset Link Sent', 'Check your email for the password reset instructions.', 'ok');
      changeView('login');
    } catch (err) {
      setForgotEmailError(true);
      toast('Request Failed', parseApiError(err), 'error');
    }
  };

  // Reset password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    setResetPasswordError(false);
    setResetPasswordConfirmError(false);
    if (!resetPassword) {
      setResetPasswordError(true);
      return;
    }
    if (resetPassword !== resetPasswordConfirm) {
      setResetPasswordConfirmError(true);
      toast('Mismatch', 'Passwords do not match.', 'error');
      return;
    }
    try {
      await request('/auth/forgot-password/reset', {
        method: 'POST',
        body: JSON.stringify({
          token: state.resetToken,
          password: resetPassword
        })
      });
      toast('Password Updated', 'Your password has been successfully reset.', 'ok');
      changeView('login');
    } catch (err) {
      toast('Update Failed', parseApiError(err), 'error');
    }
  };

  // UI status and toggles derived from probed backend mode
  const isGuestModeActive = backendMode.demo_mode === true || backendMode.demo_mode === null;
  const localAuthDisabled = backendMode.firebase_enabled === false && backendMode.demo_mode === true;

  const getGuestHint = () => {
    if (backendMode.demo_mode === true) {
      return 'Local demo mode is active. Real email/password login needs Firebase credentials.';
    } else if (backendMode.demo_mode === null) {
      return 'Backend reachability unknown - guest mode kept available as fallback.';
    } else if (backendMode.firebase_enabled === true) {
      return 'Production auth is enabled. Guest access is disabled by the operator.';
    }
    return '';
  };

  const isRegisterEnabled = Boolean(
    registerOtpApprovedEmail &&
    registerOtpApprovedEmail === registerEmail.trim().toLowerCase() &&
    registerOtpVerified &&
    registerOtpExpiresAt > Date.now()
  );

  const isModal = !window.location.pathname.includes('auth.html');

  const cardContent = (
    <div className={`auth-card ${isModal ? 'modal-popup' : ''}`}>
      {/* Close button for Modal Popup */}
      {isModal && onClose && (
        <button
          className="auth-close-btn"
          onClick={onClose}
          title="Close Login"
          type="button"
          aria-label="Close Login"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
      {/* Theme Toggle Button */}
      <button
        className="auth-theme-toggle"
        onClick={toggleTheme}
        title="Toggle Theme"
        type="button"
        aria-label="Toggle Theme"
      >
        {theme === 'dark' ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        )}
      </button>
      <p className="tag">NAMI</p>

      <div className="auth-headline">
        <h1 id="auth-title">{t('authTitle')}</h1>
        <div className="auth-icons" aria-hidden="true">
          <span>🚚</span>
          <span>📍</span>
          <span>🗺️</span>
        </div>
      </div>

      {/* Route illustration */}
      <div className="auth-visual" aria-hidden="true">
        <svg viewBox="0 0 420 100" role="img" focusable="false">
          <defs>
            <linearGradient id="routeGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#93c5fd" />
              <stop offset="100%" stopColor="#2563eb" />
            </linearGradient>
            <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          {/* Route path */}
          <path
            className="route-path"
            d="M24 72 C90 18, 170 92, 250 44 S360 52, 396 26"
            fill="none"
            stroke="url(#routeGrad)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray="6 8"
            filter="url(#neonGlow)"
          />
          {/* Depot */}
          <circle className="route-node route-node-1" cx="24" cy="72" r="6" fill="#2563eb" />
          {/* Waypoints */}
          <circle className="route-node route-node-2" cx="250" cy="44" r="5" fill="#60a5fa" />
          <circle className="route-node route-node-3" cx="396" cy="26" r="6" fill="#2563eb" />
          {/* Truck */}
          <g className="route-truck" transform="translate(138 52)">
            <rect x="0" y="8" width="62" height="20" rx="5" fill="#1d4ed8" />
            <rect x="40" y="2" width="18" height="14" rx="3" fill="#2563eb" />
            <rect x="43" y="4" width="12" height="8" rx="2" fill="#bfdbfe" opacity="0.6" />
            <circle cx="14" cy="30" r="5" fill="#1e3a8a" />
            <circle cx="46" cy="30" r="5" fill="#1e3a8a" />
          </g>
        </svg>
      </div>

      <div className="auth-views">
        {/* LOGIN VIEW */}
        {view === 'login' && (
          <div id="auth-view-login" className="auth-form auth-view active">
            <div className="form-group">
              <label htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                placeholder="you@company.com"
                autoComplete="email"
                value={loginEmail}
                onChange={(e) => {
                  setLoginEmail(e.target.value);
                  setLoginEmailError(false);
                }}
                className={loginEmailError ? 'input-error' : ''}
                disabled={localAuthDisabled}
              />
            </div>

            <div className="form-group">
              <label htmlFor="login-password">Password</label>
              <div className="password-input-wrapper">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter password"
                  autoComplete="current-password"
                  value={loginPassword}
                  onChange={(e) => {
                    setLoginPassword(e.target.value);
                    setLoginPasswordError(false);
                  }}
                  className={loginPasswordError ? 'input-error' : ''}
                  disabled={localAuthDisabled}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <button
              id="btn-login"
              className="btn"
              type="button"
              onClick={localAuthDisabled ? handleGuestLogin : handleLogin}
            >
              {localAuthDisabled
                ? (state.lang === 'vn' ? 'Vào Demo' : 'Continue Demo')
                : t('loginButton')}
            </button>

            {localAuthDisabled && (
              <p id="auth-hint" className="hint auth-hint" style={{ display: 'block' }}>
                {state.lang === 'vn'
                  ? 'Đăng nhập bằng email đang tắt vì Firebase chưa được cấu hình trên máy này. Dùng Demo để chạy solver.'
                  : 'Email login is disabled because Firebase is not configured on this machine. Use Demo to run the solver.'}
              </p>
            )}

            {!localAuthDisabled && (
              <div className="auth-links">
                <button
                  id="link-forgot-password"
                  className="link-btn"
                  type="button"
                  onClick={() => changeView('forgot')}
                >
                  {t('forgotPassword')}
                </button>
                <button
                  id="btn-open-register"
                  className="btn ghost"
                  type="button"
                  onClick={() => changeView('register')}
                >
                  {t('openRegister')}
                </button>
              </div>
            )}

            {isGuestModeActive && (
              <div id="guest-block" className="auth-guest">
                <div className="auth-divider">
                  <span>or</span>
                </div>
                <button
                  id="btn-guest-login"
                  className="btn ghost guest-btn"
                  type="button"
                  onClick={handleGuestLogin}
                >
                  {t('guestLogin')}
                </button>
                <p id="guest-hint" className="hint auth-hint">
                  {getGuestHint() || t('guestHint')}
                </p>
              </div>
            )}

            {/* Local Emulator Test Credentials */}
            <div
              className="auth-creds clickable"
              onClick={handleAutoFill}
              style={{
                marginTop: '16px',
                padding: '12px',
                background: 'rgba(245, 158, 11, 0.08)',
                border: '1px dashed rgba(245, 158, 11, 0.3)',
                borderRadius: '8px',
                fontSize: '12px',
                textAlign: 'left',
                lineHeight: '1.5',
                cursor: 'pointer',
                transition: 'background 0.2s ease, border-color 0.2s ease'
              }}
            >
              <div style={{ fontWeight: '600', color: 'var(--gold)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>🔑</span> Click to Auto-fill Local Credentials:
              </div>
              <div style={{ fontFamily: 'monospace', opacity: 0.9 }}>
                Email: <strong style={{ color: 'var(--text-main)' }}>test@vrptw.local</strong><br />
                Pass: <strong style={{ color: 'var(--text-main)' }}>testpass123</strong>
              </div>
            </div>
          </div>
        )}

        {/* REGISTER VIEW */}
        {view === 'register' && (
          <div id="auth-view-register" className="auth-form auth-view active">
            <div className="form-group">
              <label htmlFor="register-email">Email</label>
              <input
                id="register-email"
                type="email"
                placeholder="you@company.com"
                autoComplete="email"
                value={registerEmail}
                onChange={(e) => {
                  const emailVal = e.target.value;
                  setRegisterEmail(emailVal);
                  setRegisterEmailError(false);
                  if (emailVal.trim().toLowerCase() !== registerOtpApprovedEmail) {
                    setRegisterOtpApprovedEmail('');
                    setRegisterOtpVerified(false);
                    setRegisterOtpExpiresAt(0);
                    setOtpCountdownText('Click Send OTP to receive a verification code.');
                    setOtpCountdownTone('');
                  }
                }}
                className={registerEmailError ? 'input-error' : ''}
              />
            </div>

            <div className="form-group">
              <label htmlFor="register-password">Password</label>
              <div className="password-input-wrapper">
                <input
                  id="register-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Choose a password"
                  autoComplete="new-password"
                  value={registerPassword}
                  onChange={(e) => {
                    setRegisterPassword(e.target.value);
                    setRegisterPasswordError(false);
                  }}
                  className={registerPasswordError ? 'input-error' : ''}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label>One-time code</label>
              <div className="otp-row">
                <input
                  id="register-otp"
                  className={`otp-input ${registerOtpError ? 'input-error' : ''}`}
                  type="text"
                  inputMode="numeric"
                  placeholder="6-digit OTP"
                  maxLength={6}
                  autoComplete="one-time-code"
                  value={registerOtp}
                  onChange={handleOtpInput}
                />
                <button
                  id="btn-request-otp"
                  className="btn ghost otp-send-btn"
                  type="button"
                  onClick={handleRequestOtp}
                  disabled={isSendingRegisterOtp}
                >
                  {t('requestOtp')}
                </button>
              </div>
            </div>
            <p
              id="register-otp-countdown"
              className={`otp-countdown ${otpCountdownTone}`}
            >
              {otpCountdownText || 'Click Send OTP to receive a verification code.'}
            </p>

            <div className="inline-row auth-actions">
              <button
                id="btn-register"
                className="btn"
                type="button"
                onClick={handleRegister}
                disabled={!isRegisterEnabled}
              >
                {t('registerButton')}
              </button>
              <button
                id="btn-back-login-from-register"
                className="btn ghost"
                type="button"
                onClick={() => changeView('login')}
              >
                {t('backToLogin')}
              </button>
            </div>
          </div>
        )}

        {/* FORGOT PASSWORD VIEW */}
        {view === 'forgot' && (
          <div id="auth-view-forgot" className="auth-form auth-view active">
            <div className="form-group">
              <label htmlFor="forgot-email">Email</label>
              <input
                id="forgot-email"
                type="email"
                placeholder="you@company.com"
                autoComplete="email"
                value={forgotEmail}
                onChange={(e) => {
                  setForgotEmail(e.target.value);
                  setForgotEmailError(false);
                }}
                className={forgotEmailError ? 'input-error' : ''}
              />
            </div>
            <p className="hint">We'll send a reset link to this address.</p>

            <div className="inline-row auth-actions">
              <button
                id="btn-forgot-password"
                className="btn"
                type="button"
                onClick={handleForgotPassword}
              >
                {t('forgotButton')}
              </button>
              <button
                id="btn-back-login-from-forgot"
                className="btn ghost"
                type="button"
                onClick={() => changeView('login')}
              >
                {t('backToLogin')}
              </button>
            </div>
          </div>
        )}

        {/* RESET PASSWORD VIEW */}
        {view === 'reset' && (
          <div id="auth-view-reset" className="auth-form auth-view active">
            <div className="form-group">
              <label htmlFor="reset-password">New password</label>
              <div className="password-input-wrapper">
                <input
                  id="reset-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter new password"
                  autoComplete="new-password"
                  value={resetPassword}
                  onChange={(e) => {
                    setResetPassword(e.target.value);
                    setResetPasswordError(false);
                  }}
                  className={resetPasswordError ? 'input-error' : ''}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="reset-password-confirm">Confirm password</label>
              <div className="password-input-wrapper">
                <input
                  id="reset-password-confirm"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Re-enter new password"
                  autoComplete="new-password"
                  value={resetPasswordConfirm}
                  onChange={(e) => {
                    setResetPasswordConfirm(e.target.value);
                    setResetPasswordConfirmError(false);
                  }}
                  className={resetPasswordConfirmError ? 'input-error' : ''}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div className="inline-row auth-actions">
              <button
                id="btn-reset-password"
                className="btn"
                type="button"
                onClick={handleResetPassword}
              >
                {t('resetButton')}
              </button>
              <button
                id="btn-back-login-from-reset"
                className="btn ghost"
                type="button"
                onClick={() => changeView('login')}
              >
                {t('backToLogin')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  if (isModal) {
    return cardContent;
  }

  return (
    <section id="auth-screen" className="auth-screen">
      {/* Ambient Backdrop Glows */}
      <div className="auth-blob blob-1" aria-hidden="true"></div>
      <div className="auth-blob blob-2" aria-hidden="true"></div>
      {cardContent}
    </section>
  );
}
