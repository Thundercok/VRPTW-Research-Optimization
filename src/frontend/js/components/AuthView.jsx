import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../context/AppContext.jsx';
import { firebaseService } from '../firebaseService.js';
import RoutingCanvasBg from './RoutingCanvasBg.jsx';
import { API_BASE } from '../constants.js';

export default function AuthView({ onClose }) {
  const { state, updateState, toast, setStatus, request, loginAsGuest, t } = useAppContext();

  // Local view state: 'login' | 'register' | 'forgot' | 'reset'
  const [view, setView] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('screen') || sessionStorage.getItem('vrptw_auth_screen') || 'login';
  });

  // Backend mode settings fetched from /api/health
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
    return localStorage.getItem('vrptw_theme') || localStorage.getItem('vrptw_landing_theme_v2') || 'light';
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
      const tryFetch = async (url) => {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 3000);
        try {
          const res = await fetch(url, { method: 'GET', signal: controller.signal });
          clearTimeout(timeout);
          if (!res.ok) return null;
          return await res.json();
        } catch {
          clearTimeout(timeout);
          return null;
        }
      };

      // The backend only ever exposed /api/health; the bare /health this used
      // to probe 404'd in production, so the page always fell through to its
      // "backend unavailable" defaults.
      let data = await tryFetch(`${API_BASE}/health`);
      // Fall back to explicit localhost if the proxy isn't set up
      if (!data) data = await tryFetch('http://127.0.0.1:8000/api/health');

      if (data) {
        setBackendMode({
          firebase_enabled: 'firebase_enabled' in data ? Boolean(data.firebase_enabled) : true,
          demo_mode: 'demo_mode' in data ? Boolean(data.demo_mode) : false,
          torch: data.torch || null
        });
      } else {
        // Backend unavailable — default to guest-friendly mode
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
    <div className={`auth-card-new ${isModal ? 'modal-popup' : ''}`}>


      {/* LEFT PANE */}
      <div className="auth-left-pane">
        <RoutingCanvasBg />
        <div className="auth-left-top" style={{ position: 'relative', zIndex: 1 }}>
          <div className="auth-left-logo">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--pine)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
              <line x1="12" y1="22.08" x2="12" y2="12"></line>
            </svg>
            <div className="auth-left-logo-text">
              <span className="auth-left-logo-title">NAMI Dispatch</span>
              <span className="auth-left-logo-sub">ĐIỀU PHỐI · TỐI ƯU · THEO DÕI</span>
            </div>
          </div>
        </div>
        
        <div className="auth-left-middle" style={{ position: 'relative', zIndex: 1 }}>
          <h2>{t('authLeftHeadline1')}<br/><span className="highlight">{t('authLeftHeadline2')}</span></h2>
        </div>
        
        <div className="auth-left-bottom" style={{ position: 'relative', zIndex: 1 }}>
          <ul className="auth-left-bullets">
            <li>{t('authLeftBullet1')}</li>
            <li>{t('authLeftBullet2')}</li>
            <li>{t('authLeftBullet3')}</li>
          </ul>
        </div>
      </div>

      {/* RIGHT PANE */}
      <div className="auth-right-pane">
        
        {(view === 'login' || view === 'register') && (
          <div className="auth-tabs">
            <button 
              className={`auth-tab-btn ${view === 'login' ? 'active' : ''}`}
              onClick={() => changeView('login')}
            >
              {t('loginTab')}
            </button>
            <button 
              className={`auth-tab-btn ${view === 'register' ? 'active' : ''}`}
              onClick={() => changeView('register')}
            >
              {t('registerTab')}
            </button>
          </div>
        )}

        <div className="auth-headline-right">
          {view === 'login' && (
            <>
              <h2>{t('loginWelcome')}</h2>
              <p>{t('loginSub')}</p>
            </>
          )}
          {view === 'register' && (
             <>
               <h2>{t('registerWelcome')}</h2>
               <p>{t('registerSub')}</p>
             </>
          )}
          {view === 'forgot' && (
             <>
               <h2>{t('forgotWelcome')}</h2>
               <p>{t('forgotSub')}</p>
             </>
          )}
          {view === 'reset' && (
             <>
               <h2>{t('resetWelcome')}</h2>
               <p>{t('resetSub')}</p>
             </>
          )}
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
                ? t('demoButton')
                : t('loginButton')}
            </button>

            {localAuthDisabled && (
              <p id="auth-hint" className="hint auth-hint" style={{ display: 'block' }}>
                {t('demoHint')}
              </p>
            )}

            {!localAuthDisabled && (
              <div className="auth-links-right">
                <button
                  id="link-forgot-password"
                  className="link-btn"
                  type="button"
                  onClick={() => changeView('forgot')}
                >
                  {t('forgotPassword')}
                </button>
              </div>
            )}

            {isGuestModeActive && (
              <div id="guest-block" className="auth-guest">
                <div className="auth-divider">
                  <span>{t('orContinue')}</span>
                </div>
                <button
                  id="btn-guest-login"
                  className="btn-google"
                  type="button"
                  onClick={handleGuestLogin}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                  {t('guestDemoButton')}
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
                marginTop: '8px',
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
              <div style={{ fontWeight: '600', color: 'var(--ink)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                Demo Admin:
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
      
      {/* Close Button for Modal */}
      {isModal && onClose && (
        <button className="auth-close-btn" onClick={onClose} title="Close Login" type="button" aria-label="Close Login">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
        </button>
      )}
      
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
