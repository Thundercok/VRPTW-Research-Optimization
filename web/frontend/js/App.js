import { firebaseService } from './firebaseService.js';
import { API_BASE, SAMPLE_SOLONON_RC } from './constants.js';
import { createInitialState } from './createInitialState.js';

export class App {
  constructor() {
    this.state = createInitialState();
    this.tableInputDraft = { name: '', address: '', demand: '0', lat: null, lng: null };
    this.tableInputRefs = {};

    this.el = this.bindElements();
    this.maps = null;
    this.vehicleAnimations = [];
    this.loadingAnim = {
      active: false,
      rafId: 0,
      progress: 0,
      stage: 0,
      stageStartedAt: 0,
      lastTickAt: 0
    };
    this.registerOtpCountdownTimer = 0;
    this.registerSuccessCountdownTimer = 0;
    this.registerOtpVerifyDebounceTimer = 0;
    this.isSendingRegisterOtp = false;
    this.isSendingForgotPasswordLink = false;
    this.isSubmittingPasswordChange = false;
    this.registerOtpRequestedEmail = ''; // Track which email OTP was sent to
    this.wireAuthEvents();
    this.routeAuthScreenFromURL();

    if (this.state.unlocked && this.state.email) {
      if (this.state.mustChangePassword) {
        this.showAuthView('reset');
        this.toast('Password Change Required', 'Set a new password before accessing the app.', 'error');
      } else {
        this.enterApp();
        this.initFirebase(this.state.email);
        this.toast('Auto Login', 'Previous session restored.', 'ok');
      }
    } else {
      this.leaveApp();
    }
  }

  bindElements() {
    return {
      authViews: Array.from(document.querySelectorAll('.auth-view')),
      viewLogin: document.getElementById('auth-view-login'),
      viewRegister: document.getElementById('auth-view-register'),
      viewForgot: document.getElementById('auth-view-forgot'),
      viewReset: document.getElementById('auth-view-reset'),
      loginEmail: document.getElementById('login-email'),
      loginPassword: document.getElementById('login-password'),
      registerEmail: document.getElementById('register-email'),
      registerPassword: document.getElementById('register-password'),
      registerOtp: document.getElementById('register-otp'),
      registerOtpCountdown: document.getElementById('register-otp-countdown'),
      forgotEmail: document.getElementById('forgot-email'),
      resetPassword: document.getElementById('reset-password'),
      resetPasswordConfirm: document.getElementById('reset-password-confirm'),
      linkForgotPassword: document.getElementById('link-forgot-password'),
      btnOpenRegister: document.getElementById('btn-open-register'),
      btnBackLoginFromRegister: document.getElementById('btn-back-login-from-register'),
      btnBackLoginFromForgot: document.getElementById('btn-back-login-from-forgot'),
      btnBackLoginFromReset: document.getElementById('btn-back-login-from-reset'),
      authHint: document.getElementById('auth-hint'),
      btnRequestOtp: document.getElementById('btn-request-otp'),
      btnRegister: document.getElementById('btn-register'),
      btnLogin: document.getElementById('btn-login'),
      btnForgotPassword: document.getElementById('btn-forgot-password'),
      btnResetPassword: document.getElementById('btn-reset-password'),
      btnLogout: document.getElementById('btn-logout'),
      adminPanel: document.getElementById('admin-panel'),
      adminRefresh: document.getElementById('admin-refresh'),
      adminUserRows: document.getElementById('admin-user-rows'),
      userEmail: document.getElementById('user-email'),
      authScreen: document.getElementById('auth-screen'),
      appShell: document.getElementById('app-shell'),
      tabButtons: Array.from(document.querySelectorAll('.tab-btn')),
      tabPanels: Array.from(document.querySelectorAll('.tab-panel')),
      tabbarIndicator: document.querySelector('.tabbar-indicator'),
      pickExcel: document.getElementById('pick-excel'),
      excelInput: document.getElementById('excel-input'),
      dropzone: document.getElementById('dropzone'),
      modeToggle: document.getElementById('mode-toggle'),
      vehicles: document.getElementById('vehicles-slider'),
      vehiclesValue: document.getElementById('vehicles-value'),
      capacity: document.getElementById('capacity-slider'),
      capacityValue: document.getElementById('capacity-value'),
      addressInput: document.getElementById('address-input'),
      addAddress: document.getElementById('add-address'),
      suggestList: document.getElementById('address-suggest'),
      pasteBox: document.getElementById('paste-box'),
      parsePaste: document.getElementById('parse-paste'),
      loadSample: document.getElementById('load-sample'),
      runModel: document.getElementById('run-model'),
      customerRows: document.getElementById('customer-rows'),
      tableEmpty: document.getElementById('table-empty'),
      tableSkeleton: document.getElementById('table-skeleton'),
      mapEmptyDdqn: document.getElementById('map-empty-ddqn'),
      mapEmptyAlns: document.getElementById('map-empty-alns'),
      metricRuntimeCard: document.getElementById('metric-runtime-card'),
      metricRuntimeDdqn: document.getElementById('metric-runtime-ddqn'),
      metricRuntimeAlns: document.getElementById('metric-runtime-alns'),
      metricRuntimeDelta: document.getElementById('metric-runtime-delta'),
      metricRuntimeBarDdqn: document.getElementById('metric-runtime-bar-ddqn'),
      metricRuntimeBarAlns: document.getElementById('metric-runtime-bar-alns'),
      metricDistanceCard: document.getElementById('metric-distance-card'),
      metricDistanceDdqn: document.getElementById('metric-distance-ddqn'),
      metricDistanceAlns: document.getElementById('metric-distance-alns'),
      metricDistanceDelta: document.getElementById('metric-distance-delta'),
      metricDistanceBarDdqn: document.getElementById('metric-distance-bar-ddqn'),
      metricDistanceBarAlns: document.getElementById('metric-distance-bar-alns'),
      metricVehiclesCard: document.getElementById('metric-vehicles-card'),
      metricVehiclesDdqn: document.getElementById('metric-vehicles-ddqn'),
      metricVehiclesAlns: document.getElementById('metric-vehicles-alns'),
      metricVehiclesDelta: document.getElementById('metric-vehicles-delta'),
      metricVehiclesBarDdqn: document.getElementById('metric-vehicles-bar-ddqn'),
      metricVehiclesBarAlns: document.getElementById('metric-vehicles-bar-alns'),
      connectionPill: document.getElementById('connection-pill'),
      loading: document.getElementById('loading'),
      loadingCard: document.getElementById('loading-card'),
      loadingTitle: document.getElementById('loading-title'),
      loadingPhase: document.getElementById('loading-phase'),
      loadingPercent: document.getElementById('loading-percent'),
      loadingTrackFill: document.getElementById('loading-track-fill'),
      loadingTruck: document.getElementById('loading-truck'),
      toastRoot: document.getElementById('toast-root'),
      status: document.getElementById('status')
    };
  }

  wireAuthEvents() {
    this.el.btnOpenRegister?.addEventListener('click', (event) => {
      event.preventDefault();
      this.showAuthView('register');
    });
    this.el.linkForgotPassword?.addEventListener('click', (event) => {
      event.preventDefault();
      this.showAuthView('forgot');
    });
    this.el.btnBackLoginFromRegister?.addEventListener('click', (event) => {
      event.preventDefault();
      this.showAuthView('login');
    });
    this.el.btnBackLoginFromForgot?.addEventListener('click', (event) => {
      event.preventDefault();
      this.showAuthView('login');
    });
    this.el.btnBackLoginFromReset?.addEventListener('click', (event) => {
      event.preventDefault();
      this.showAuthView('login');
    });
    this.el.btnRequestOtp?.addEventListener('click', (event) => {
      event.preventDefault();
      this.requestRegisterOtp();
    });
    this.el.btnRegister?.addEventListener('click', (event) => {
      event.preventDefault();
      this.register();
    });
    this.el.btnLogin?.addEventListener('click', (event) => {
      event.preventDefault();
      this.login();
    });
    this.el.btnForgotPassword?.addEventListener('click', (event) => {
      event.preventDefault();
      this.requestForgotPasswordOtp();
    });
    this.el.btnResetPassword?.addEventListener('click', (event) => {
      event.preventDefault();
      this.resetForgotPassword();
    });
    this.el.btnLogout?.addEventListener('click', (event) => {
      event.preventDefault();
      this.logout();
    });

    this.el.registerEmail?.addEventListener('input', () => {
      this.clearFieldError(this.el.registerEmail);
      const currentEmail = this.el.registerEmail.value.trim().toLowerCase();
      // Only reset OTP state if email actually changed from the one OTP was sent to
      if (currentEmail !== this.registerOtpRequestedEmail) {
        this.state.registerOtpApprovedEmail = '';
        this.state.registerOtpVerified = false;
        this.state.registerOtpExpiresAt = 0;
        this.stopRegisterOtpCountdown();
        this.updateRegisterOtpCountdownText('Click Send OTP to receive a verification code.');
        this.updateRegisterButtonState();
      }
    });
    this.el.registerPassword?.addEventListener('input', () => this.clearFieldError(this.el.registerPassword));
    this.el.registerOtp?.addEventListener('input', () => {
      this.clearFieldError(this.el.registerOtp);
      this.state.registerOtpVerified = false;
      this.updateRegisterButtonState();
      this.scheduleRealtimeOtpVerification();
    });
    [this.el.registerEmail, this.el.registerPassword, this.el.registerOtp].forEach((field) => {
      field?.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
      });
    });
    this.el.loginEmail?.addEventListener('input', () => this.clearFieldError(this.el.loginEmail));
    this.el.loginPassword?.addEventListener('input', () => this.clearFieldError(this.el.loginPassword));
    this.el.forgotEmail?.addEventListener('input', () => this.clearFieldError(this.el.forgotEmail));
    this.el.resetPassword?.addEventListener('input', () => this.clearFieldError(this.el.resetPassword));
    this.el.resetPasswordConfirm?.addEventListener('input', () => this.clearFieldError(this.el.resetPasswordConfirm));

    this.updateRegisterButtonState();
  }

  routeAuthScreenFromURL() {
    const params = new URLSearchParams(window.location.search);
    const screen = params.get('screen') || sessionStorage.getItem('vrptw_auth_screen');
    if (screen === 'register') {
      this.showAuthView('register');
      return;
    }
    if (screen === 'forgot') {
      this.showAuthView('forgot');
      return;
    }
    if (screen === 'reset') {
      this.state.resetToken = params.get('token') || '';
      this.showAuthView('reset');
      return;
    }
    this.showAuthView('login');
  }

  showAuthView(view) {
    const key = `view${view.charAt(0).toUpperCase()}${view.slice(1)}`;
    const current = this.el[key];
    this.el.authViews.forEach((node) => node.classList.add('hidden'));
    current?.classList.remove('hidden');
    if (view) sessionStorage.setItem('vrptw_auth_screen', view);
    this.syncAuthScreenInUrl(view);
    this.stopRegisterSuccessCountdown();
    this.clearAuthInputErrors();
    // Clear register OTP state when leaving register view
    if (view !== 'register') {
      this.registerOtpRequestedEmail = '';
    }
    if (view === 'register') {
      if (this.state.registerOtpExpiresAt > Date.now()) {
        this.startRegisterOtpCountdown();
      } else {
        this.stopRegisterOtpCountdown();
        this.updateRegisterOtpCountdownText('Click Send OTP to receive a verification code.');
      }
      this.updateRegisterButtonState();
    } else {
      this.stopRegisterOtpCountdown();
    }
  }

  syncAuthScreenInUrl(view) {
    const url = new URL(window.location.href);
    if (view === 'register' || view === 'forgot') {
      url.searchParams.set('screen', view);
      if (view !== 'reset') url.searchParams.delete('token');
    } else if (view === 'reset') {
      url.searchParams.set('screen', 'reset');
      if (this.state.resetToken) url.searchParams.set('token', this.state.resetToken);
    } else {
      url.searchParams.delete('screen');
      url.searchParams.delete('token');
    }
    window.history.replaceState({}, '', `${url.pathname}${url.search}`);
  }

  clearAuthInputErrors() {
    [
      this.el.loginEmail,
      this.el.loginPassword,
      this.el.registerEmail,
      this.el.registerPassword,
      this.el.registerOtp,
      this.el.forgotEmail,
      this.el.resetPassword,
      this.el.resetPasswordConfirm
    ].forEach((field) => this.clearFieldError(field));
  }

  setFieldError(field) {
    if (!field) return;
    field.classList.add('input-error');
  }

  clearFieldError(field) {
    if (!field) return;
    field.classList.remove('input-error');
  }

  updateRegisterButtonState() {
    if (!this.el.btnRegister || !this.el.registerEmail) return;
    const currentEmail = this.el.registerEmail.value.trim().toLowerCase();
    const enabled = Boolean(
      this.state.registerOtpApprovedEmail &&
      this.state.registerOtpApprovedEmail === currentEmail &&
      this.state.registerOtpVerified &&
      this.state.registerOtpExpiresAt > Date.now()
    );

    this.el.btnRegister.hidden = false;
    this.el.btnRegister.classList.remove('hidden');
    this.el.btnRegister.disabled = !enabled;
  }

  stopRegisterOtpCountdown() {
    if (this.registerOtpCountdownTimer) {
      window.clearInterval(this.registerOtpCountdownTimer);
      this.registerOtpCountdownTimer = 0;
    }
  }

  stopRegisterSuccessCountdown() {
    if (this.registerSuccessCountdownTimer) {
      window.clearInterval(this.registerSuccessCountdownTimer);
      this.registerSuccessCountdownTimer = 0;
    }
  }

  stopRegisterOtpVerifyDebounce() {
    if (this.registerOtpVerifyDebounceTimer) {
      window.clearTimeout(this.registerOtpVerifyDebounceTimer);
      this.registerOtpVerifyDebounceTimer = 0;
    }
  }

  scheduleRealtimeOtpVerification() {
    this.stopRegisterOtpVerifyDebounce();

    const email = this.el.registerEmail?.value.trim().toLowerCase() || '';
    const otp = this.el.registerOtp?.value.trim() || '';
    const canVerify =
      this.state.registerOtpApprovedEmail === email &&
      this.state.registerOtpExpiresAt > Date.now() &&
      /^\d{6}$/.test(otp);

    if (!canVerify) return;

    this.registerOtpVerifyDebounceTimer = window.setTimeout(() => {
      this.verifyRegisterOtp({ silent: true });
    }, 220);
  }

  updateRegisterOtpCountdownText(text, tone = '') {
    if (!this.el.registerOtpCountdown) return;
    this.el.registerOtpCountdown.className = `otp-countdown ${tone}`.trim();
    this.el.registerOtpCountdown.textContent = text;
  }

  startRegisterOtpCountdown() {
    this.stopRegisterOtpCountdown();

    const tick = () => {
      const remainMs = this.state.registerOtpExpiresAt - Date.now();
      if (remainMs <= 0) {
        this.stopRegisterOtpCountdown();
        this.state.registerOtpApprovedEmail = '';
        this.state.registerOtpVerified = false;
        this.state.registerOtpExpiresAt = 0;
        this.updateRegisterButtonState();
        this.updateRegisterOtpCountdownText('OTP expired. Please click Send OTP again.', 'expired');
        return;
      }

      const remainSec = Math.ceil(remainMs / 1000);
      const minutes = Math.floor(remainSec / 60);
      const seconds = remainSec % 60;
      this.updateRegisterOtpCountdownText(`OTP valid for ${minutes}:${String(seconds).padStart(2, '0')}.`, 'active');
      this.updateRegisterButtonState();
    };

    tick();
    this.registerOtpCountdownTimer = window.setInterval(tick, 1000);
  }

  parseApiError(error) {
    const raw = String(error?.message || '').trim();
    if (!raw) return 'An error occurred';
    try {
      const parsed = JSON.parse(raw);
      return parsed.detail || parsed.message || raw;
    } catch {
      return raw;
    }
  }

  formatRunError(errorLike) {
    const raw = typeof errorLike === 'string' ? errorLike : this.parseApiError(errorLike);
    const message = String(raw || '').trim();
    if (!message) return 'Run failed unexpectedly.';

    const lower = message.toLowerCase();
    if (lower.includes('infeasible configuration') && lower.includes('vehicles')) {
      return 'Infeasible with current settings: number of vehicles is too low for current demand/capacity. Try increasing Vehicles or Capacity.';
    }
    if (lower.includes('exceeds vehicle capacity')) {
      return 'At least one customer demand exceeds vehicle capacity. Increase Capacity or reduce that customer demand.';
    }
    if (lower.includes('negative demand')) {
      return 'Invalid input: demand cannot be negative.';
    }
    return message;
  }

  isValidEmail(email) {
    return /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(email);
  }

  async requestRegisterOtp() {
    if (this.isSendingRegisterOtp) return;

    // Keep the register view pinned while sending OTP.
    this.showAuthView('register');

    const email = this.el.registerEmail.value.trim().toLowerCase();
    this.clearFieldError(this.el.registerEmail);
    this.clearFieldError(this.el.registerOtp);

    if (!email) {
      this.setFieldError(this.el.registerEmail);
      this.updateRegisterOtpCountdownText('Email is required before sending OTP.', 'expired');
      this.toast('Missing Email', 'Please enter your email first.', 'error');
      return;
    }

    if (!this.isValidEmail(email)) {
      this.setFieldError(this.el.registerEmail);
      this.updateRegisterOtpCountdownText('Invalid email format.', 'expired');
      this.toast('Invalid Email', 'Please enter a valid email before sending OTP.', 'error');
      return;
    }

    try {
      this.isSendingRegisterOtp = true;
      this.el.btnRequestOtp && (this.el.btnRequestOtp.disabled = true);
      this.updateRegisterOtpCountdownText('Sending OTP...', 'active');

      const res = await this.request('/auth/register/request-otp', {
        method: 'POST',
        body: JSON.stringify({ email })
      });

      this.state.registerOtpApprovedEmail = email;
      this.registerOtpRequestedEmail = email; // Track this email for OTP state management
      this.state.registerOtpVerified = false;
      this.state.registerOtpExpiresAt = Date.now() + 10 * 60 * 1000;
      this.stopRegisterOtpVerifyDebounce();
      this.startRegisterOtpCountdown();
      this.updateRegisterButtonState();
      this.el.registerOtp?.focus();
      this.toast('OTP Sent Successfully', `Delivery method: ${res.delivery}. Check your email for the OTP code.`, 'ok');
      this.updateRegisterOtpCountdownText('OTP sent. Enter OTP to verify automatically.', 'active');
      this.setStatus('Send OTP success. Please enter the 6-digit OTP to continue.', 'ok');
      // Pin register view after successful OTP send
      this.showAuthView('register');
    } catch (error) {
      this.state.registerOtpApprovedEmail = '';
      this.registerOtpRequestedEmail = ''; // Clear on error
      this.state.registerOtpVerified = false;
      this.state.registerOtpExpiresAt = 0;
      this.stopRegisterOtpVerifyDebounce();
      this.stopRegisterOtpCountdown();
      this.updateRegisterOtpCountdownText('Failed to send OTP. Please try again.', 'expired');
      this.updateRegisterButtonState();
      this.setFieldError(this.el.registerEmail);
      const reason = this.parseApiError(error);
      this.setStatus(`Send OTP failed: ${reason}`, 'error');
      this.toast('Failed to Send OTP', reason, 'error');
      this.showAuthView('register');
    } finally {
      this.isSendingRegisterOtp = false;
      this.el.btnRequestOtp && (this.el.btnRequestOtp.disabled = false);
    }
  }

  async verifyRegisterOtp(options = {}) {
    const { silent = false } = options;
    try {
      const email = this.el.registerEmail.value.trim().toLowerCase();
      const otp = this.el.registerOtp.value.trim();

      this.clearFieldError(this.el.registerEmail);
      this.clearFieldError(this.el.registerOtp);

      if (!email || !this.isValidEmail(email)) {
        this.setFieldError(this.el.registerEmail);
        throw new Error('Invalid email format');
      }
      if (!otp) {
        this.setFieldError(this.el.registerOtp);
        throw new Error('OTP is required');
      }
      if (!/^\d{6}$/.test(otp)) {
        this.setFieldError(this.el.registerOtp);
        throw new Error('OTP must be exactly 6 digits');
      }
      if (this.state.registerOtpApprovedEmail !== email || this.state.registerOtpExpiresAt <= Date.now()) {
        this.setFieldError(this.el.registerEmail);
        throw new Error('Please send OTP first before verifying');
      }

      await this.request('/auth/register/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ email, otp })
      });

      this.state.registerOtpVerified = true;
      this.updateRegisterButtonState();
      this.updateRegisterOtpCountdownText('OTP verified successfully. You can now click Register.', 'active');
      if (!silent) {
        this.toast('OTP Verified', 'OTP is correct. Register button is now available.', 'ok');
      }
    } catch (error) {
      this.state.registerOtpVerified = false;
      this.updateRegisterButtonState();
      this.setFieldError(this.el.registerOtp);
      this.updateRegisterOtpCountdownText('Incorrect OTP. Please try again.', 'expired');
      if (!silent) {
        this.toast('OTP Verification Failed', this.parseApiError(error), 'error');
      }
    }
  }

  wireWorkspaceEvents() {
    this.setupTabs();
    this.setupExcelImport();
    this.wireEvents();
    this.el.adminRefresh?.addEventListener('click', () => this.loadAdminUsers());
  }

  enterApp() {
    this.state.unlocked = true;
    this.el.authScreen?.classList.add('hidden');
    this.el.appShell?.classList.remove('hidden');

    if (!this.maps) {
      this.maps = this.createMaps();
      this.wireWorkspaceEvents();
      this.renderCustomers();
      this.renderMarkers();
      this.showEmptyStates();
    } else {
      this.maps.ddqnMap.invalidateSize();
      this.maps.alnsMap.invalidateSize();
    }

    this.setStatus('Ready for operations.', 'ok');
    this.updateConnectionPill();
    this.updateSessionInfo();
    this.updateAdminPanel();
    this.activateTab(this.state.activeTab, true);
  }

  leaveApp() {
    this.state.unlocked = false;
    this.el.appShell?.classList.add('hidden');
    this.el.authScreen?.classList.remove('hidden');
    if (this.el.authHint) {
      this.el.authHint.textContent = 'Register once, then log in to receive your token.';
    }
    this.showAuthView('login');
  }

  async initFirebase(email) {
    try {
      const enabled = await firebaseService.init(email);
      if (enabled) {
        await firebaseService.logEvent('login', { source: 'dashboard' });
        this.toast('Firebase Connected', 'Session data persistence is enabled.', 'ok');
      } else {
        this.toast('Firebase Not Configured', 'Fill in js/firebaseConfig.js to enable data persistence.', 'error');
      }
    } catch (error) {
      this.toast('Firebase Error', error.message, 'error');
    }
  }

  setupTabs() {
    this.el.tabButtons.forEach((button) => {
      button.addEventListener('click', () => this.activateTab(button.dataset.tab));
    });
    window.addEventListener('resize', () => this.updateTabIndicator());
    this.activateTab(this.state.activeTab, true);
  }

  setupExcelImport() {
    if (this.el.pickExcel) {
      this.el.pickExcel.addEventListener('click', () => this.el.excelInput?.click());
    }

    if (this.el.excelInput) {
      this.el.excelInput.addEventListener('change', (event) => this.handleExcelFile(event));
    }

    if (this.el.dropzone) {
      this.el.dropzone.addEventListener('click', (event) => {
        if (event.target === this.el.dropzone) this.el.excelInput?.click();
      });
      this.el.dropzone.addEventListener('dragover', (event) => {
        event.preventDefault();
        this.el.dropzone.classList.add('dragover');
      });
      this.el.dropzone.addEventListener('dragleave', () => {
        this.el.dropzone.classList.remove('dragover');
      });
      this.el.dropzone.addEventListener('drop', (event) => {
        event.preventDefault();
        this.el.dropzone.classList.remove('dragover');
        const [file] = event.dataTransfer?.files ?? [];
        if (file) this.handleExcelFile({ target: { files: [file] } });
      });
    }
  }

  createMaps() {
    const ddqnMap = L.map('map-ddqn').setView([10.73193, 106.69934], 13);
    const alnsMap = L.map('map-alns').setView([10.73193, 106.69934], 13);

    const layer = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    [ddqnMap, alnsMap].forEach((m) => {
      L.tileLayer(layer, { maxZoom: 19 }).addTo(m);
    });

    const ddqnMarkerLayer = L.layerGroup().addTo(ddqnMap);
    const alnsMarkerLayer = L.layerGroup().addTo(alnsMap);
    const ddqnRouteLayer = L.layerGroup().addTo(ddqnMap);
    const alnsRouteLayer = L.layerGroup().addTo(alnsMap);
    const alnsDiffLayer = L.layerGroup().addTo(alnsMap);
    const ddqnVehicleLayer = L.layerGroup().addTo(ddqnMap);
    const alnsVehicleLayer = L.layerGroup().addTo(alnsMap);

    let syncing = false;
    const sync = (source, target) => {
      source.on('move', () => {
        if (syncing) return;
        syncing = true;
        target.setView(source.getCenter(), source.getZoom(), { animate: false });
        syncing = false;
      });
    };
    sync(ddqnMap, alnsMap);
    sync(alnsMap, ddqnMap);

    ddqnMap.on('click', (e) => this.addMapPoint(e.latlng));
    alnsMap.on('click', (e) => this.addMapPoint(e.latlng));

    return {
      ddqnMap,
      alnsMap,
      ddqnMarkerLayer,
      alnsMarkerLayer,
      ddqnRouteLayer,
      alnsRouteLayer,
      alnsDiffLayer,
      ddqnVehicleLayer,
      alnsVehicleLayer
    };
  }

  buildDepotIcon() {
    return L.divIcon({
      className: 'map-marker-wrap',
      iconSize: [30, 40],
      iconAnchor: [15, 36],
      popupAnchor: [0, -24],
      html: `
        <div class="map-icon-3d depot" style="--icon-main:#dc2626;--icon-dark:#9f1239;--icon-shadow:rgba(159,18,57,0.4)">
          <span class="map-icon-glyph">🏭</span>
        </div>`
    });
  }

  buildCustomerIcon() {
    return L.divIcon({
      className: 'map-marker-wrap',
      iconSize: [28, 36],
      iconAnchor: [14, 33],
      popupAnchor: [0, -20],
      html: `
        <div class="map-icon-3d customer" style="--icon-main:#7c3aed;--icon-dark:#5b21b6;--icon-shadow:rgba(124,58,237,0.35)">
          <span class="map-icon-glyph">👤</span>
        </div>`
    });
  }

  buildVehicleIcon(color = '#0b8a65') {
    return L.divIcon({
      className: 'map-marker-wrap',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -10],
      html: `
        <div class="map-icon-3d vehicle" style="--icon-main:${color};--icon-dark:#0f3d33;--icon-shadow:rgba(15,61,51,0.35)">
          <span class="map-icon-glyph">🚚</span>
        </div>`
    });
  }

  stopVehicleAnimations() {
    this.vehicleAnimations.forEach((anim) => {
      anim.alive = false;
      if (anim.rafId) cancelAnimationFrame(anim.rafId);
    });
    this.vehicleAnimations = [];
  }

  startVehicleAnimation(marker, path) {
    if (!Array.isArray(path) || path.length < 2) return;

    const anim = {
      alive: true,
      rafId: 0,
      segment: 0,
      t: Math.random() * 0.85,
      speed: 0.012 + Math.random() * 0.006
    };

    const tick = () => {
      if (!anim.alive) return;

      const a = path[anim.segment];
      const b = path[anim.segment + 1] || path[0];
      const lat = a[0] + (b[0] - a[0]) * anim.t;
      const lng = a[1] + (b[1] - a[1]) * anim.t;
      marker.setLatLng([lat, lng]);

      anim.t += anim.speed;
      if (anim.t >= 1) {
        anim.t = 0;
        anim.segment += 1;
        if (anim.segment >= path.length - 1) {
          anim.segment = 0;
        }
      }

      anim.rafId = requestAnimationFrame(tick);
    };

    anim.rafId = requestAnimationFrame(tick);
    this.vehicleAnimations.push(anim);
  }

  wireEvents() {
    this.el.modeToggle.addEventListener('change', () => {
      this.state.mode = this.el.modeToggle.checked ? 'real' : 'sample';
      this.setStatus(`Switched to ${this.state.mode === 'sample' ? 'Solomon RC' : 'Real Data'} mode.`);
    });

    this.el.vehicles.addEventListener('input', () => {
      this.state.vehicles = Number(this.el.vehicles.value);
      this.el.vehiclesValue.textContent = String(this.state.vehicles);
    });

    this.el.capacity.addEventListener('input', () => {
      this.state.capacity = Number(this.el.capacity.value);
      this.el.capacityValue.textContent = String(this.state.capacity);
    });

    this.el.loadSample.addEventListener('click', () => {
      this.state.mode = 'sample';
      this.el.modeToggle.checked = false;
      this.state.customers = SAMPLE_SOLONON_RC.map((c, idx) => ({ ...c, id: idx }));
      this.renderCustomers();
      this.renderMarkers();
      this.setStatus('Loaded Solomon RC sample data.', 'ok');
    });

    this.el.parsePaste?.addEventListener('click', () => this.parsePasteData());
    this.el.runModel.addEventListener('click', () => this.submitJob());
    this.el.addAddress.addEventListener('click', () => this.addSelectedAddress());
    this.el.addressInput.addEventListener('input', () => this.handleAddressInput());
    this.wireTableInlineEditing();
  }

  wireTableInlineEditing() {
    if (!this.el.customerRows) return;
    this.el.customerRows.addEventListener('dblclick', (event) => {
      const cell = event.target.closest('td[data-editable="true"]');
      if (!cell) return;
      this.startCustomerCellEdit(cell);
    });
  }

  startCustomerCellEdit(cell) {
    if (!cell || cell.classList.contains('is-editing')) return;

    const row = cell.closest('tr');
    const customerId = Number(row?.dataset.customerId);
    const field = cell.dataset.field;
    if (!Number.isFinite(customerId) || !field) return;

    const customer = this.state.customers.find((item) => item.id === customerId);
    if (!customer) return;

    const originalValue = field === 'demand' ? String(customer.demand ?? 0) : String(customer[field] ?? '');
    const input = document.createElement('input');
    input.className = 'table-edit-input';
    input.type = field === 'demand' ? 'number' : 'text';
    input.value = originalValue;
    if (field === 'demand') {
      input.min = '0';
      input.step = '1';
    }

    cell.classList.add('is-editing');
    cell.textContent = '';
    cell.appendChild(input);
    input.focus();
    input.select();

    let done = false;
    const commit = async () => {
      if (done) return;
      done = true;
      await this.commitCustomerCellEdit({ customerId, field, rawValue: input.value, originalValue });
    };

    const cancel = () => {
      if (done) return;
      done = true;
      this.renderCustomers();
    };

    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        commit();
        return;
      }
      if (event.key === 'Escape') {
        event.preventDefault();
        cancel();
      }
    });

    input.addEventListener('blur', () => {
      commit();
    });
  }

  async commitCustomerCellEdit({ customerId, field, rawValue, originalValue }) {
    const customer = this.state.customers.find((item) => item.id === customerId);
    if (!customer) {
      this.renderCustomers();
      return;
    }

    const nextValue = String(rawValue ?? '').trim();
    if (nextValue === originalValue) {
      this.renderCustomers();
      return;
    }

    if (field === 'name') {
      if (!nextValue) {
        this.toast('Invalid Name', 'Name cannot be empty.', 'error');
        this.renderCustomers();
        return;
      }
      customer.name = nextValue;
      this.renderCustomers();
      this.renderMarkers();
      this.setStatus('Customer name updated.', 'ok');
      return;
    }

    if (field === 'demand') {
      const demand = Number(nextValue);
      if (!Number.isFinite(demand) || demand < 0) {
        this.toast('Invalid Demand', 'Demand must be a number >= 0.', 'error');
        this.renderCustomers();
        return;
      }
      customer.demand = Math.round(demand);
      this.renderCustomers();
      this.renderMarkers();
      this.setStatus('Customer demand updated.', 'ok');
      return;
    }

    if (field === 'address') {
      if (!nextValue) {
        this.toast('Invalid Address', 'Address cannot be empty.', 'error');
        this.renderCustomers();
        return;
      }

      customer.address = nextValue;
      const geocoded = await this.tryGeocodeFromText(nextValue);
      if (geocoded) {
        customer.lat = geocoded.lat;
        customer.lng = geocoded.lng;
        this.setStatus('Address updated. Coordinates were refreshed automatically.', 'ok');
      } else {
        this.setStatus('Address updated, but geocoding could not refresh coordinates.', 'error');
        this.toast('Geocode Warning', 'Could not find coordinates for this address.', 'error');
      }
      this.renderCustomers();
      this.renderMarkers();
      return;
    }

    this.renderCustomers();
  }

  activateTab(tabName, silent = false) {
    this.state.activeTab = tabName;
    this.el.tabButtons.forEach((button) => button.classList.toggle('active', button.dataset.tab === tabName));
    let targetPanel = null;
    this.el.tabPanels.forEach((panel) => {
      panel.classList.add('active');
      panel.classList.remove('panel-focus');
      if (panel.dataset.panel === tabName) targetPanel = panel;
    });

    if (targetPanel) {
      targetPanel.classList.add('panel-focus');
      if (!silent) {
        targetPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    this.updateTabIndicator();
    if (!silent) {
      this.toast('Tab Changed', `Switched to ${this.tabLabel(tabName)}.`, 'ok');
    }
  }

  updateTabIndicator() {
    if (!this.el.tabbarIndicator) return;
    const activeButton = this.el.tabButtons.find((button) => button.classList.contains('active'));
    if (!activeButton) return;
    const parentRect = activeButton.parentElement?.getBoundingClientRect();
    const rect = activeButton.getBoundingClientRect();
    if (!parentRect) return;
    this.el.tabbarIndicator.style.width = `${rect.width}px`;
    this.el.tabbarIndicator.style.transform = `translateX(${rect.left - parentRect.left}px)`;
  }

  tabLabel(tabName) {
    return ({ overview: 'Overview', maps: 'Split Map', results: 'Results' })[tabName] ?? tabName;
  }

  async request(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (this.state.token) headers.Authorization = `Bearer ${this.state.token}`;
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!response.ok) {
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || data?.message || `HTTP ${response.status}`);
      }
      const body = await response.text();
      throw new Error(body || `HTTP ${response.status}`);
    }
    return response.json();
  }

  async register() {
    try {
      const email = this.el.registerEmail.value.trim().toLowerCase();
      const password = this.el.registerPassword.value.trim();
      const otp = this.el.registerOtp.value.trim();
      this.clearFieldError(this.el.registerEmail);
      this.clearFieldError(this.el.registerPassword);
      this.clearFieldError(this.el.registerOtp);

      if (!email || !this.isValidEmail(email)) {
        this.setFieldError(this.el.registerEmail);
        throw new Error('Invalid email format');
      }
      if (this.state.registerOtpApprovedEmail !== email) {
        this.setFieldError(this.el.registerEmail);
        throw new Error('Please send OTP successfully before registering');
      }
      if (!password) {
        this.setFieldError(this.el.registerPassword);
        throw new Error('Password is required');
      }
      if (!this.state.registerOtpVerified) {
        this.setFieldError(this.el.registerOtp);
        throw new Error('Please verify OTP before registering');
      }
      if (password.length < 6) {
        this.setFieldError(this.el.registerPassword);
        throw new Error('Password must be at least 6 characters');
      }
      if (!otp) {
        this.setFieldError(this.el.registerOtp);
        throw new Error('OTP is required');
      }
      if (!/^\d{6}$/.test(otp)) {
        this.setFieldError(this.el.registerOtp);
        throw new Error('OTP must be exactly 6 digits');
      }

      await this.request('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, otp })
      });
      this.toast('Registration Successful', 'Account created successfully.', 'ok');
      this.el.loginEmail.value = email;
      this.el.registerEmail.value = '';
      this.el.registerPassword.value = '';
      this.el.registerOtp.value = '';
      this.state.registerOtpApprovedEmail = '';
      this.registerOtpRequestedEmail = ''; // Clear on successful registration
      this.state.registerOtpVerified = false;
      this.state.registerOtpExpiresAt = 0;
      this.stopRegisterOtpCountdown();
      this.stopRegisterSuccessCountdown();
      this.updateRegisterOtpCountdownText('Click Send OTP to receive a verification code.');
      this.updateRegisterButtonState();
      this.showAuthView('login');
    } catch (error) {
      const message = this.parseApiError(error);
      if (/otp/i.test(message)) {
        this.setFieldError(this.el.registerOtp);
      } else if (/password/i.test(message)) {
        this.setFieldError(this.el.registerPassword);
      } else if (/email/i.test(message)) {
        this.setFieldError(this.el.registerEmail);
      }
      this.toast('Registration Failed', message, 'error');
    }
  }

  async login() {
    try {
      const email = this.el.loginEmail.value.trim().toLowerCase();
      const password = this.el.loginPassword.value.trim();
      this.clearFieldError(this.el.loginEmail);
      this.clearFieldError(this.el.loginPassword);
      if (!this.isValidEmail(email)) {
        this.setFieldError(this.el.loginEmail);
        throw new Error('Invalid email format');
      }
      if (!password) {
        this.setFieldError(this.el.loginPassword);
        throw new Error('Please enter both email and password');
      }
      const data = await this.request('/auth/token', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      this.state.token = data.access_token;
      this.state.email = email;
      this.state.role = data.role || 'operator';
      this.state.mustChangePassword = Boolean(data.must_change_password);
      localStorage.setItem('vrptw_token', this.state.token);
      localStorage.setItem('vrptw_email', email);
      localStorage.setItem('vrptw_role', this.state.role);
      localStorage.setItem('vrptw_must_change_password', String(this.state.mustChangePassword));

      if (this.state.mustChangePassword) {
        this.state.resetToken = '';
        this.el.resetPassword.value = '';
        this.el.resetPasswordConfirm.value = '';
        this.showAuthView('reset');
        this.toast('Password Change Required', 'Use the temporary password once, then set a new password now.', 'error');
        return;
      }

      this.enterApp();
      await this.initFirebase(email);
      this.updateConnectionPill();
      this.toast('Login Successful', 'Token has been saved in your browser.', 'ok');
    } catch (error) {
      const message = this.parseApiError(error);
      if (/email/i.test(message)) this.setFieldError(this.el.loginEmail);
      if (/password|credential|invalid/i.test(message)) this.setFieldError(this.el.loginPassword);
      this.toast('Login Failed', message, 'error');
      if (this.el.authHint) this.el.authHint.textContent = `Login error: ${message}`;
    }
  }

  async requestForgotPasswordOtp() {
    if (this.isSendingForgotPasswordLink) return;

    try {
      this.isSendingForgotPasswordLink = true;
      this.el.btnForgotPassword && (this.el.btnForgotPassword.disabled = true);

      const email = this.el.forgotEmail.value.trim().toLowerCase();
      this.clearFieldError(this.el.forgotEmail);
      if (!this.isValidEmail(email)) {
        this.setFieldError(this.el.forgotEmail);
        throw new Error('Invalid email format');
      }

      const res = await this.request('/auth/forgot-password/request', {
        method: 'POST',
        body: JSON.stringify({ email })
      });

      this.el.forgotEmail.value = '';
      this.el.loginEmail.value = email;
      this.toast('Temporary Password Sent', `Delivery method: ${res.delivery}. Check your email for the temporary password.`, 'ok');
      this.showAuthView('login');
    } catch (error) {
      const message = this.parseApiError(error);
      this.setFieldError(this.el.forgotEmail);
      this.toast('Failed to Send Reset Link', message, 'error');
    } finally {
      this.isSendingForgotPasswordLink = false;
      this.el.btnForgotPassword && (this.el.btnForgotPassword.disabled = false);
    }
  }

  async resetForgotPassword() {
    if (this.isSubmittingPasswordChange) return;

    try {
      this.isSubmittingPasswordChange = true;
      this.el.btnResetPassword && (this.el.btnResetPassword.disabled = true);

      const password = this.el.resetPassword.value.trim();
      const confirm = this.el.resetPasswordConfirm.value.trim();
      this.clearFieldError(this.el.resetPassword);
      this.clearFieldError(this.el.resetPasswordConfirm);
      if (password.length < 6) {
        this.setFieldError(this.el.resetPassword);
        throw new Error('New password must be at least 6 characters');
      }
      if (password !== confirm) {
        this.setFieldError(this.el.resetPasswordConfirm);
        throw new Error('Password confirmation does not match');
      }

      if (this.state.mustChangePassword) {
        await this.request('/auth/password/change-required', {
          method: 'POST',
          body: JSON.stringify({ new_password: password })
        });

        const loginEmail = this.state.email;
        this.state.mustChangePassword = false;
        this.state.resetToken = '';
        this.state.token = '';
        this.state.email = '';
        this.state.role = 'operator';
        localStorage.removeItem('vrptw_token');
        localStorage.removeItem('vrptw_email');
        localStorage.removeItem('vrptw_role');
        localStorage.removeItem('vrptw_must_change_password');
        this.el.resetPassword.value = '';
        this.el.resetPasswordConfirm.value = '';
        this.el.loginEmail.value = loginEmail;
        this.toast('Password Updated', 'New password saved. Please login again.', 'ok');
        this.showAuthView('login');
      } else {
        const token = this.state.resetToken || new URLSearchParams(window.location.search).get('token') || '';
        if (!token) throw new Error('Missing reset token in URL');

        await this.request('/auth/forgot-password/reset', {
          method: 'POST',
          body: JSON.stringify({ token, new_password: password })
        });

        this.toast('Password Updated', 'You can now log in with your new password.', 'ok');
        this.state.resetToken = '';
        this.el.resetPassword.value = '';
        this.el.resetPasswordConfirm.value = '';
        window.history.replaceState({}, '', window.location.pathname);
        this.showAuthView('login');
      }
    } catch (error) {
      const message = this.parseApiError(error);
      this.toast('Failed to Update Password', message, 'error');
    } finally {
      this.isSubmittingPasswordChange = false;
      this.el.btnResetPassword && (this.el.btnResetPassword.disabled = false);
    }
  }

  async logout() {
    this.state.token = '';
    this.state.email = '';
    this.state.role = 'operator';
    this.state.mustChangePassword = false;
    localStorage.removeItem('vrptw_token');
    localStorage.removeItem('vrptw_email');
    localStorage.removeItem('vrptw_role');
    localStorage.removeItem('vrptw_must_change_password');
    this.updateConnectionPill();
    this.updateSessionInfo();
    this.leaveApp();
    this.toast('Logged Out', 'Session has ended.', 'ok');
    try {
      await firebaseService.logEvent('logout', { source: 'dashboard' });
    } catch {
      // Ignore logging failure on logout.
    }
  }

  updateAdminPanel() {
    const isAdmin = this.state.role === 'admin';
    this.el.adminPanel?.classList.toggle('hidden', !isAdmin);
    if (isAdmin) {
      this.loadAdminUsers();
    }
  }

  async loadAdminUsers() {
    if (this.state.role !== 'admin' || !this.el.adminUserRows) return;
    try {
      const data = await this.request('/admin/users', { method: 'GET' });
      this.el.adminUserRows.innerHTML = '';
      (data.items || []).forEach((item) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${item.email}</td>
          <td>
            <select class="admin-role-select" data-email="${item.email}">
              <option value="admin" ${item.role === 'admin' ? 'selected' : ''}>admin</option>
              <option value="operator" ${item.role === 'operator' ? 'selected' : ''}>operator</option>
              <option value="viewer" ${item.role === 'viewer' ? 'selected' : ''}>viewer</option>
            </select>
          </td>
          <td>${new Date(item.created_at * 1000).toLocaleString()}</td>
          <td><button class="btn ghost" data-action="save-role" data-email="${item.email}" type="button">Save</button></td>
        `;
        this.el.adminUserRows.appendChild(tr);
      });

      this.el.adminUserRows.querySelectorAll('[data-action="save-role"]').forEach((button) => {
        button.addEventListener('click', () => this.saveAdminRole(button.dataset.email));
      });
    } catch (error) {
      this.toast('Failed to Load User List', error.message, 'error');
    }
  }

  async saveAdminRole(email) {
    if (!email || !this.el.adminUserRows) return;
    const select = this.el.adminUserRows.querySelector(`select[data-email="${email}"]`);
    if (!select) return;
    try {
      await this.request(`/admin/users/${encodeURIComponent(email)}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role: select.value })
      });
      this.toast('Role Updated', `${email} -> ${select.value}`, 'ok');
    } catch (error) {
      this.toast('Failed to Update Role', error.message, 'error');
    }
  }

  async handleAddressInput() {
    const q = this.el.addressInput.value.trim();
    this.state.selectedSuggest = null;
    if (q.length < 3) {
      this.state.suggest = [];
      this.renderSuggest();
      return;
    }
    try {
      const data = await this.request(`/geocode?q=${encodeURIComponent(q)}&limit=6`, { method: 'GET' });
      this.state.suggest = data.items || [];
      this.renderSuggest();
    } catch {
      this.state.suggest = [];
      this.renderSuggest();
    }
  }

  renderSuggest() {
    this.el.suggestList.innerHTML = '';
    this.state.suggest.forEach((item) => {
      const li = document.createElement('li');
      li.textContent = item.address;
      li.addEventListener('click', () => {
        this.state.selectedSuggest = item;
        this.el.addressInput.value = item.address;
        this.state.suggest = [];
        this.renderSuggest();
      });
      this.el.suggestList.appendChild(li);
    });
  }

  addSelectedAddress() {
    const selected = this.state.selectedSuggest;
    if (!selected) {
      this.setStatus('Please select an address from the suggestion list.', 'error');
      return;
    }
    this.pushCustomer({
      name: `C-${Date.now().toString().slice(-4)}`,
      address: selected.address,
      lat: selected.lat,
      lng: selected.lng,
      demand: 10
    });
    this.el.addressInput.value = '';
    this.state.selectedSuggest = null;
    this.setStatus('Added a customer from address autocomplete.', 'ok');
    this.toast('Delivery Point Added', selected.address, 'ok');
  }

  async parsePasteData() {
    const text = this.el.pasteBox.value.trim();
    if (!text) {
      this.setStatus('No data available to parse.', 'error');
      return;
    }

    const rows = text.split(/\r?\n/).map((line) => line.split(/\t|,/));
    const newItems = await this.parseRowsToCustomers(rows);

    newItems.forEach((item) => this.pushCustomer(item));
    this.el.pasteBox.value = '';
    this.setStatus(`Added ${newItems.length} customers from pasted Excel data.`, 'ok');
    this.toast('Import Successful', `Loaded ${newItems.length} rows from clipboard.`, 'ok');
  }

  async handleExcelFile(event) {
    const [file] = event.target.files ?? [];
    if (!file) return;
    try {
      if (typeof XLSX === 'undefined') throw new Error('SheetJS is not loaded yet');
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: 'array' });
      const firstSheet = workbook.SheetNames[0];
      const sheet = workbook.Sheets[firstSheet];
      const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });
      const newItems = await this.parseRowsToCustomers(rows);
      newItems.forEach((item) => this.pushCustomer(item));
      this.toast('Excel Imported', `${newItems.length} customers have been loaded.`, 'ok');
      this.setStatus(`Imported ${newItems.length} rows from Excel file.`, 'ok');
    } catch (error) {
      this.toast('Import Failed', error.message, 'error');
      this.setStatus(`Unable to read Excel file: ${error.message}`, 'error');
    } finally {
      if (this.el.excelInput) this.el.excelInput.value = '';
    }
  }

  async parseRowsToCustomers(rows) {
    const newItems = [];
    for (const cols of rows) {
      if (!Array.isArray(cols) || cols.length === 0) continue;
      const [name = '', address = '', latRaw = '', lngRaw = '', demandRaw = '10'] = cols.map((c) => String(c).trim());
      let lat = Number(latRaw);
      let lng = Number(lngRaw);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        if (!address) continue;
        const geo = await this.tryGeocodeFromText(address);
        if (!geo) continue;
        lat = geo.lat;
        lng = geo.lng;
      }
      newItems.push({
        name: name || `Cust-${Date.now().toString().slice(-4)}`,
        address,
        lat,
        lng,
        demand: Number(demandRaw) || 10
      });
    }
    return newItems;
  }

  async tryGeocodeFromText(address) {
    try {
      const geo = await this.request(`/geocode?q=${encodeURIComponent(address)}&limit=1`, { method: 'GET' });
      if (!geo.items || geo.items.length === 0) return null;
      return { lat: Number(geo.items[0].lat), lng: Number(geo.items[0].lng) };
    } catch {
      return null;
    }
  }

  async tryReverseGeocode(lat, lng) {
    try {
      const result = await this.request(`/reverse-geocode?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`, { method: 'GET' });
      const shortAddress = result?.short_address?.trim();
      const fullAddress = result?.address?.trim();
      return shortAddress || fullAddress || '';
    } catch {
      return '';
    }
  }

  async addMapPoint(latlng) {
    const address = (await this.tryReverseGeocode(latlng.lat, latlng.lng)) || `Lat ${latlng.lat.toFixed(5)}, Lng ${latlng.lng.toFixed(5)}`;
    this.pushCustomer({
      name: `Pin-${this.state.customers.length}`,
      address,
      lat: latlng.lat,
      lng: latlng.lng,
      demand: 0
    });
    this.setStatus('Dropped a new delivery pin.', 'ok');
    this.toast('Pin Added', 'Point was added directly on the map.', 'ok');
  }

  focusTableInputField(field) {
    const input = this.tableInputRefs[field];
    if (!input) return;
    input.focus();
    input.select?.();
  }

  formatDraftCoord(value) {
    return Number.isFinite(value) ? Number(value).toFixed(5) : '-';
  }

  updateDraftCoordCells() {
    if (this.tableInputRefs.latCell) this.tableInputRefs.latCell.textContent = this.formatDraftCoord(this.tableInputDraft.lat);
    if (this.tableInputRefs.lngCell) this.tableInputRefs.lngCell.textContent = this.formatDraftCoord(this.tableInputDraft.lng);
  }

  async resolveTableInputAddress() {
    const address = this.tableInputDraft.address.trim();
    if (!address) {
      this.tableInputDraft.lat = null;
      this.tableInputDraft.lng = null;
      this.updateDraftCoordCells();
      return false;
    }
    const geo = await this.tryGeocodeFromText(address);
    if (!geo) {
      this.tableInputDraft.lat = null;
      this.tableInputDraft.lng = null;
      this.updateDraftCoordCells();
      return false;
    }
    this.tableInputDraft.lat = geo.lat;
    this.tableInputDraft.lng = geo.lng;
    this.updateDraftCoordCells();
    return true;
  }

  async handleTableInputEnter(field) {
    if (field === 'name') {
      this.focusTableInputField('address');
      return;
    }
    if (field === 'address') {
      await this.resolveTableInputAddress();
      this.focusTableInputField('demand');
      return;
    }
    if (field === 'demand') {
      await this.submitTableInputRow();
    }
  }

  moveTableInputFocus(field, direction) {
    const order = ['name', 'address', 'demand'];
    const index = order.indexOf(field);
    if (index < 0) return;
    const nextIndex = Math.max(0, Math.min(order.length - 1, index + direction));
    if (nextIndex === index) return;
    this.focusTableInputField(order[nextIndex]);
  }

  resetTableInputDraft() {
    this.tableInputDraft = { name: '', address: '', demand: '0', lat: null, lng: null };
  }

  async submitTableInputRow() {
    const name = this.tableInputDraft.name.trim();
    const address = this.tableInputDraft.address.trim();
    const demandRaw = String(this.tableInputDraft.demand ?? '').trim();

    if (!name && !address && !demandRaw) {
      this.focusTableInputField('name');
      return;
    }

    const demand = Number(demandRaw || '0');
    if (!Number.isFinite(demand) || demand < 0) {
      this.toast('Invalid Demand', 'Demand must be a number >= 0.', 'error');
      this.focusTableInputField('demand');
      return;
    }

    if (!address) {
      this.toast('Missing Address', 'Please enter an address.', 'error');
      this.focusTableInputField('address');
      return;
    }

    if (!Number.isFinite(this.tableInputDraft.lat) || !Number.isFinite(this.tableInputDraft.lng)) {
      const found = await this.resolveTableInputAddress();
      if (!found) {
        this.toast('Geocode Failed', 'Could not resolve this address to coordinates.', 'error');
        this.focusTableInputField('address');
        return;
      }
    }

    this.pushCustomer({
      name: name || `Cust-${this.state.customers.length}`,
      address,
      lat: this.tableInputDraft.lat,
      lng: this.tableInputDraft.lng,
      demand: Math.round(demand),
    });

    this.resetTableInputDraft();
    this.setStatus('Added customer from table input row.', 'ok');
    window.requestAnimationFrame(() => this.focusTableInputField('name'));
  }

  renderTableInputRow() {
    const tr = document.createElement('tr');
    tr.className = 'table-input-row';

    const idCell = document.createElement('td');
    idCell.textContent = '+';
    tr.appendChild(idCell);

    const createInputCell = (field, value, type = 'text') => {
      const td = document.createElement('td');
      const input = document.createElement('input');
      input.className = 'table-inline-input';
      input.type = type;
      input.value = value;
      if (field === 'demand') {
        input.min = '0';
        input.step = '1';
      }
      input.addEventListener('input', () => {
        this.tableInputDraft[field] = input.value;
      });
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          this.handleTableInputEnter(field);
          return;
        }
        if (event.key === 'ArrowRight') {
          event.preventDefault();
          this.moveTableInputFocus(field, 1);
          return;
        }
        if (event.key === 'ArrowLeft') {
          event.preventDefault();
          this.moveTableInputFocus(field, -1);
        }
      });
      if (field === 'address') {
        input.addEventListener('blur', () => {
          this.resolveTableInputAddress();
        });
      }
      td.appendChild(input);
      this.tableInputRefs[field] = input;
      return td;
    };

    tr.appendChild(createInputCell('name', this.tableInputDraft.name));
    tr.appendChild(createInputCell('address', this.tableInputDraft.address));

    const latCell = document.createElement('td');
    latCell.className = 'table-inline-readonly';
    latCell.textContent = this.formatDraftCoord(this.tableInputDraft.lat);
    this.tableInputRefs.latCell = latCell;
    tr.appendChild(latCell);

    const lngCell = document.createElement('td');
    lngCell.className = 'table-inline-readonly';
    lngCell.textContent = this.formatDraftCoord(this.tableInputDraft.lng);
    this.tableInputRefs.lngCell = lngCell;
    tr.appendChild(lngCell);

    tr.appendChild(createInputCell('demand', this.tableInputDraft.demand, 'number'));

    this.el.customerRows.appendChild(tr);
  }

  pushCustomer(item) {
    const id = this.state.customers.length;
    this.state.customers.push({ ...item, id, isDepot: false });
    this.renderCustomers();
    this.renderMarkers();
  }

  renderCustomers() {
    this.tableInputRefs = {};
    this.el.customerRows.innerHTML = '';
    this.state.customers.forEach((c) => {
      const tr = document.createElement('tr');
      tr.dataset.customerId = String(c.id);

      const values = [
        { field: 'id', value: String(c.id), editable: false },
        { field: 'name', value: c.name || '', editable: true },
        { field: 'address', value: c.address || '-', editable: true },
        { field: 'lat', value: Number(c.lat).toFixed(5), editable: false },
        { field: 'lng', value: Number(c.lng).toFixed(5), editable: false },
        { field: 'demand', value: String(c.demand), editable: true },
      ];

      values.forEach(({ field, value, editable }) => {
        const td = document.createElement('td');
        td.dataset.field = field;
        if (editable) {
          td.dataset.editable = 'true';
          td.classList.add('cell-editable');
          td.title = 'Double-click to edit';
        }
        td.textContent = value;
        tr.appendChild(td);
      });

      this.el.customerRows.appendChild(tr);
    });
    this.renderTableInputRow();
    this.showEmptyStates();
  }

  renderMarkers() {
    const { ddqnMarkerLayer, alnsMarkerLayer, ddqnMap, alnsMap } = this.maps;
    ddqnMarkerLayer.clearLayers();
    alnsMarkerLayer.clearLayers();
    const bounds = [];

    const depotIcon = this.buildDepotIcon();
    const customerIcon = this.buildCustomerIcon();

    this.state.customers.forEach((c) => {
      const p = [c.lat, c.lng];
      bounds.push(p);
      const markerIcon = c.isDepot ? depotIcon : customerIcon;
      const popupTitle = c.isDepot ? 'Warehouse / Depot' : 'Customer';
      const popupAddress = c.address ? `<br/>${c.address}` : '';
      const popupContent = `<strong>${popupTitle}</strong><br/>${c.name}${popupAddress}<br/>Demand: ${c.demand}`;
      L.marker(p, { icon: markerIcon }).bindPopup(popupContent).addTo(ddqnMarkerLayer);
      L.marker(p, { icon: markerIcon }).bindPopup(popupContent).addTo(alnsMarkerLayer);
    });

    if (bounds.length > 0) {
      ddqnMap.fitBounds(bounds, { padding: [22, 22] });
      alnsMap.fitBounds(bounds, { padding: [22, 22] });
    }
    this.showEmptyStates();
  }

  async submitJob() {
    try {
      if (!this.state.token) {
        this.toast('Not Logged In', 'Please log in before running the model.', 'error');
        return;
      }
      if (this.state.customers.length < 2) {
        this.setStatus('At least depot and 1 customer are required.', 'error');
        return;
      }

      this.showLoading(true);
      this.setStatus('Running geocoding/matrix and submitting job...');
      this.toast('Processing', 'System is running geocoding and distance matrix.', 'ok');

      const matrixPoints = this.state.customers.map((c) => ({ lat: c.lat, lng: c.lng }));
      await this.request('/matrix', {
        method: 'POST',
        body: JSON.stringify({ points: matrixPoints })
      });

      const payload = {
        mode: this.state.mode,
        fleet: { vehicles: this.state.vehicles, capacity: this.state.capacity },
        customers: this.state.customers
      };
      this.state.lastRunFleet = { ...payload.fleet };

      const submit = await this.request('/jobs', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      await firebaseService.saveJobStart(submit.job_id, {
        mode: this.state.mode,
        fleet: payload.fleet,
        customerCount: this.state.customers.length,
        customers: this.state.customers
      });

      const pollLimitMs = this.estimatePollTimeoutMs(this.state.customers.length);
      await this.pollJob(submit.job_id, pollLimitMs);
    } catch (error) {
      const friendly = this.formatRunError(error);
      this.setStatus(`Submit error: ${friendly}`, 'error');
      this.toast('Submit Failed', friendly, 'error');
      this.hideLoadingImmediate();
    }
  }

  estimatePollTimeoutMs(customerCount) {
    const count = Math.max(0, Number(customerCount) || 0);
    const baseline = 180000;
    const scaled = baseline + count * 3500;
    return Math.min(900000, Math.max(baseline, scaled));
  }

  async pollJob(jobId, timeoutMs = 180000) {
    const startedAt = Date.now();
    while (Date.now() - startedAt < timeoutMs) {
      const data = await this.request(`/jobs/${jobId}`, { method: 'GET' });
      if (data.status === 'queued') {
        this.setLoadingProgress(this.loadingAnim.progress, null, 'Job queued, waiting for worker...', 0.18, 'idle');
      } else if (data.status === 'processing') {
        this.setLoadingProgress(this.loadingAnim.progress, null, 'Backend is processing optimization...', 0.28, 'alns');
      }
      if (data.status === 'done') {
        this.state.lastResult = data.result;
        this.paintResult();
        await firebaseService.saveJobResult(jobId, data.result);
        await this.completeLoading();
        this.setStatus('Received optimization results from backend.', 'ok');
        this.toast('Model Completed', 'Results have been rendered on the dashboard.', 'ok');
        this.showEmptyStates();
        return;
      }
      if (data.status === 'failed') {
        throw new Error(this.formatRunError(data.error || 'Job failed'));
      }
      await new Promise((resolve) => setTimeout(resolve, 1400));
    }
    const seconds = Math.round(timeoutMs / 1000);
    throw new Error(
      `Job timeout after ${seconds}s. Backend may still be running; try increasing Vehicles/Capacity or reducing customer count.`
    );
  }

  paintResult() {
    const result = this.state.lastResult;
    if (!result) return;

    this.stopVehicleAnimations();

    this.maps.ddqnRouteLayer.clearLayers();
    this.maps.alnsRouteLayer.clearLayers();
    this.maps.alnsDiffLayer.clearLayers();
    this.maps.ddqnVehicleLayer.clearLayers();
    this.maps.alnsVehicleLayer.clearLayers();
    const routeCapacity = Number(this.state.lastRunFleet?.capacity ?? this.state.capacity);
    this.renderAlgoRoutes(result.ddqn, this.maps.ddqnRouteLayer, '#0b8a65', routeCapacity);
    this.renderAlgoRoutes(result.alns, this.maps.alnsRouteLayer, '#2563eb', routeCapacity);
    const highlightedCount = this.renderAlnsOnlySegments(result.ddqn, result.alns, this.maps.alnsDiffLayer);
    this.renderVehicleMarkers(result.ddqn, this.maps.ddqnVehicleLayer, '#0b8a65');
    this.renderVehicleMarkers(result.alns, this.maps.alnsVehicleLayer, '#2563eb');

    if (highlightedCount > 0) {
      this.setStatus(`Highlighted ${highlightedCount} ALNS segments that do not appear in DDQN.`, 'ok');
    }

    this.updateCompareMetric({
      card: this.el.metricRuntimeCard,
      ddqnNode: this.el.metricRuntimeDdqn,
      alnsNode: this.el.metricRuntimeAlns,
      deltaNode: this.el.metricRuntimeDelta,
      barDdqn: this.el.metricRuntimeBarDdqn,
      barAlns: this.el.metricRuntimeBarAlns,
      ddqn: result.ddqn.runtime_sec,
      alns: result.alns.runtime_sec,
      unit: 's',
      decimals: 2,
      lowerIsBetter: true
    });

    this.updateCompareMetric({
      card: this.el.metricDistanceCard,
      ddqnNode: this.el.metricDistanceDdqn,
      alnsNode: this.el.metricDistanceAlns,
      deltaNode: this.el.metricDistanceDelta,
      barDdqn: this.el.metricDistanceBarDdqn,
      barAlns: this.el.metricDistanceBarAlns,
      ddqn: result.ddqn.total_distance_km,
      alns: result.alns.total_distance_km,
      unit: 'km',
      decimals: 2,
      lowerIsBetter: true
    });

    this.updateCompareMetric({
      card: this.el.metricVehiclesCard,
      ddqnNode: this.el.metricVehiclesDdqn,
      alnsNode: this.el.metricVehiclesAlns,
      deltaNode: this.el.metricVehiclesDelta,
      barDdqn: this.el.metricVehiclesBarDdqn,
      barAlns: this.el.metricVehiclesBarAlns,
      ddqn: result.ddqn.vehicles_used,
      alns: result.alns.vehicles_used,
      unit: '',
      decimals: 0,
      lowerIsBetter: true
    });

    this.showEmptyStates();
  }

  updateCompareMetric({ card, ddqnNode, alnsNode, deltaNode, barDdqn, barAlns, ddqn, alns, unit, decimals, lowerIsBetter }) {
    const ddqnValue = Number(ddqn);
    const alnsValue = Number(alns);
    const tieThreshold = 1e-9;
    const diff = alnsValue - ddqnValue;
    const absDiff = Math.abs(diff);

    let winner = 'tie';
    if (absDiff > tieThreshold) {
      if (lowerIsBetter) {
        winner = ddqnValue < alnsValue ? 'ddqn' : 'alns';
      } else {
        winner = ddqnValue > alnsValue ? 'ddqn' : 'alns';
      }
    }

    if (ddqnNode) ddqnNode.textContent = this.formatMetricValue(ddqnValue, unit, decimals);
    if (alnsNode) alnsNode.textContent = this.formatMetricValue(alnsValue, unit, decimals);

    if (deltaNode) {
      if (winner === 'tie') {
        deltaNode.textContent = 'Results are tied';
      } else {
        const betterLabel = winner.toUpperCase();
        deltaNode.textContent = `${betterLabel} is better by ${this.formatMetricValue(absDiff, unit, decimals)}`;
      }
    }

    if (card) card.dataset.winner = winner;

    const epsilon = 1e-9;
    if (lowerIsBetter) {
      const min = Math.min(ddqnValue, alnsValue) + epsilon;
      const ddqnScore = min / (ddqnValue + epsilon);
      const alnsScore = min / (alnsValue + epsilon);
      if (barDdqn) barDdqn.style.width = `${30 + ddqnScore * 70}%`;
      if (barAlns) barAlns.style.width = `${30 + alnsScore * 70}%`;
    } else {
      const max = Math.max(ddqnValue, alnsValue) + epsilon;
      const ddqnScore = ddqnValue / max;
      const alnsScore = alnsValue / max;
      if (barDdqn) barDdqn.style.width = `${30 + ddqnScore * 70}%`;
      if (barAlns) barAlns.style.width = `${30 + alnsScore * 70}%`;
    }
  }

  formatMetricValue(value, unit, decimals) {
    const fixed = Number(value).toFixed(decimals);
    return `${fixed}${unit}`;
  }

  buildLoadBadge(load, cap) {
    if (!Number.isFinite(cap) || cap <= 0) {
      return { ratio: null, label: 'N/A', tone: 'low' };
    }
    const ratio = load / cap;
    if (ratio > 0.95) return { ratio, label: 'Critical', tone: 'high' };
    if (ratio >= 0.8) return { ratio, label: 'Near Full', tone: 'medium' };
    return { ratio, label: 'Safe', tone: 'low' };
  }

  renderAlgoRoutes(algo, layerGroup, color, capacity) {
    (algo.routes || []).forEach((route) => {
      if (!route.path || route.path.length < 2) return;
      const load = Number(route.load ?? 0);
      const cap = Number(capacity);
      const loadLine = Number.isFinite(cap) && cap > 0 ? `<br/>Load: ${load}/${cap}` : `<br/>Load: ${load}`;
      const badge = this.buildLoadBadge(load, cap);
      const ratioText = Number.isFinite(badge.ratio) ? `${(badge.ratio * 100).toFixed(1)}%` : 'N/A';
      const popupContent = `
        <div class="route-popup">
          <strong>Vehicle ${route.vehicle_id}</strong>
          ${loadLine}
          <br/>Distance: ${Number(route.distance_km || 0).toFixed(2)} km
          <br/>Utilization: ${ratioText}
          <br/><span class="route-load-pill ${badge.tone}">${badge.label}</span>
        </div>
      `;
      L.polyline(route.path.map((p) => [p[0], p[1]]), {
        color,
        weight: 4,
        opacity: 0.78
      }).bindPopup(popupContent).addTo(layerGroup);
    });
  }

  renderAlnsOnlySegments(ddqn, alns, layerGroup) {
    const ddqnSegments = this.collectSegmentSet(ddqn);
    let highlightedSegments = 0;

    (alns.routes || []).forEach((route, routeIndex) => {
      if (!route.path || route.path.length < 2) return;

      let streak = [];
      for (let i = 0; i < route.path.length - 1; i++) {
        const a = route.path[i];
        const b = route.path[i + 1];
        const key = this.segmentKey(a, b);
        const isUnique = !ddqnSegments.has(key);

        if (isUnique) {
          if (streak.length === 0) streak.push([a[0], a[1]]);
          streak.push([b[0], b[1]]);
          highlightedSegments += 1;
          continue;
        }

        if (streak.length > 1) {
          this.drawDiffSegment(streak, layerGroup, routeIndex);
          streak = [];
        }
      }

      if (streak.length > 1) {
        this.drawDiffSegment(streak, layerGroup, routeIndex);
      }
    });

    return highlightedSegments;
  }

  drawDiffSegment(path, layerGroup, routeIndex) {
    L.polyline(path, {
      color: '#ff5a5f',
      weight: 10,
      opacity: 0.22,
      lineCap: 'round'
    }).addTo(layerGroup);

    L.polyline(path, {
      color: '#d7191c',
      weight: 5,
      opacity: 0.92,
      dashArray: '8 5',
      lineCap: 'round'
    }).bindPopup(`ALNS-only segment • Route ${routeIndex + 1}`).addTo(layerGroup);
  }

  collectSegmentSet(algo) {
    const set = new Set();
    (algo.routes || []).forEach((route) => {
      if (!route.path || route.path.length < 2) return;
      for (let i = 0; i < route.path.length - 1; i++) {
        set.add(this.segmentKey(route.path[i], route.path[i + 1]));
      }
    });
    return set;
  }

  segmentKey(a, b) {
    const ka = `${Number(a[0]).toFixed(5)},${Number(a[1]).toFixed(5)}`;
    const kb = `${Number(b[0]).toFixed(5)},${Number(b[1]).toFixed(5)}`;
    return ka < kb ? `${ka}|${kb}` : `${kb}|${ka}`;
  }

  renderVehicleMarkers(algo, layerGroup, color) {
    (algo.routes || []).forEach((route) => {
      if (!route.path || route.path.length < 2) return;
      const start = route.path[0];
      const marker = L.marker([start[0], start[1]], { icon: this.buildVehicleIcon(color) });
      marker.bindPopup(`Vehicle #${route.vehicle_id}`);
      marker.addTo(layerGroup);
      this.startVehicleAnimation(marker, route.path);
    });
  }

  setStatus(message, tone = '') {
    this.el.status.className = `status ${tone}`.trim();
    this.el.status.textContent = message;
  }

  updateConnectionPill() {
    if (!this.el.connectionPill) return;
    const connected = Boolean(this.state.token);
    this.el.connectionPill.textContent = connected ? 'Connected' : 'Offline';
    this.el.connectionPill.className = connected ? 'pill soft ok' : 'pill soft';
  }

  updateSessionInfo() {
    if (!this.el.userEmail) return;
    this.el.userEmail.textContent = this.state.email || '-';
  }

  showEmptyStates() {
    if (this.el.tableEmpty) {
      this.el.tableEmpty.classList.add('hidden');
      if (this.el.tableSkeleton) this.el.tableSkeleton.classList.add('hidden');
    }
    const hasRoutes = Boolean(this.state.lastResult?.ddqn?.routes?.length || this.state.lastResult?.alns?.routes?.length);
    if (this.el.mapEmptyDdqn) this.el.mapEmptyDdqn.classList.toggle('hidden', hasRoutes);
    if (this.el.mapEmptyAlns) this.el.mapEmptyAlns.classList.toggle('hidden', hasRoutes);
  }

  toast(title, message, tone = '') {
    if (!this.el.toastRoot) return;
    const node = document.createElement('div');
    node.className = `toast ${tone}`.trim();
    node.innerHTML = `
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    `;
    this.el.toastRoot.appendChild(node);
    window.setTimeout(() => {
      node.style.opacity = '0';
      node.style.transform = 'translateY(8px) scale(0.98)';
      window.setTimeout(() => node.remove(), 220);
    }, 2800);
  }

  showLoading(show) {
    if (show) {
      this.startLoadingProgress();
      this.el.loading.classList.remove('hidden');
      return;
    }
    this.hideLoadingImmediate();
  }

  setLoadingProgress(progress, title, phase, speed = 0, algo = 'idle') {
    const value = Math.max(0, Math.min(100, progress));
    const progressText = `${Math.round(value)}%`;
    const normalizedSpeed = Math.max(0, Math.min(1, speed));

    if (this.el.loadingTitle && title) this.el.loadingTitle.textContent = title;
    if (this.el.loadingPhase && phase) this.el.loadingPhase.textContent = phase;
    if (this.el.loadingPercent) this.el.loadingPercent.textContent = progressText;

    if (this.el.loadingCard) {
      this.el.loadingCard.style.setProperty('--truck-speed', normalizedSpeed.toFixed(3));
      this.el.loadingCard.dataset.algo = algo;
      this.el.loadingCard.classList.remove('is-slow', 'is-medium', 'is-fast');
      if (normalizedSpeed > 0.67) this.el.loadingCard.classList.add('is-fast');
      else if (normalizedSpeed > 0.34) this.el.loadingCard.classList.add('is-medium');
      else this.el.loadingCard.classList.add('is-slow');
    }

    if (this.el.loadingTrackFill) {
      this.el.loadingTrackFill.style.setProperty('--loading-progress', `${value}%`);
    }
    if (this.el.loadingTruck) {
      this.el.loadingTruck.style.setProperty('--loading-progress', `${value}%`);
    }
  }

  startLoadingProgress() {
    this.stopLoadingProgress();
    this.loadingAnim.active = true;
    this.loadingAnim.progress = 0;
    this.loadingAnim.stage = 0;
    this.loadingAnim.stageStartedAt = performance.now();
    this.loadingAnim.lastTickAt = this.loadingAnim.stageStartedAt;
    this.setLoadingProgress(0, 'AI is optimizing routes...', 'Collecting route data...', 0.22, 'idle');

    const phases = [
      { label: 'Collecting route data...', until: 28, algo: 'idle', base: 0.032, amp: 0.024 },
      { label: 'Running DDQN...', until: 63, algo: 'ddqn', base: 0.044, amp: 0.038 },
      { label: 'Running ALNS...', until: 97, algo: 'alns', base: 0.039, amp: 0.034 },
      { label: 'Finalizing best routes...', until: 99, algo: 'alns', base: 0.012, amp: 0.01 }
    ];

    const tick = (now) => {
      if (!this.loadingAnim.active) return;

      const stage = phases[this.loadingAnim.stage] || phases[phases.length - 1];
      const delta = Math.max(8, now - this.loadingAnim.lastTickAt);
      const pulse = (Math.sin(now / 220) + 1) / 2;
      const step = (stage.base + stage.amp * pulse) * (delta / 16);

      if (this.loadingAnim.progress < stage.until) {
        this.loadingAnim.progress = Math.min(stage.until, this.loadingAnim.progress + step);
      }

      this.setLoadingProgress(
        this.loadingAnim.progress,
        null,
        stage.label,
        Math.min(1, step / 0.1),
        stage.algo
      );

      if (this.loadingAnim.progress >= stage.until - 0.01 && this.loadingAnim.stage < phases.length - 1) {
        this.loadingAnim.stage += 1;
        this.loadingAnim.stageStartedAt = now;
      }

      this.loadingAnim.lastTickAt = now;
      this.loadingAnim.rafId = requestAnimationFrame(tick);
    };

    this.loadingAnim.rafId = requestAnimationFrame(tick);
  }

  stopLoadingProgress() {
    this.loadingAnim.active = false;
    if (this.loadingAnim.rafId) cancelAnimationFrame(this.loadingAnim.rafId);
    this.loadingAnim.rafId = 0;
  }

  async completeLoading() {
    const start = this.loadingAnim.progress;
    this.stopLoadingProgress();
    const duration = 420;
    const t0 = performance.now();

    await new Promise((resolve) => {
      const step = (now) => {
        const t = Math.min(1, (now - t0) / duration);
        const eased = 1 - Math.pow(1 - t, 3);
        const value = start + (100 - start) * eased;
        const velocity = Math.max(0.22, 1 - t * 0.8);
        this.setLoadingProgress(value, 'Optimization Complete', 'Rendering maps and KPI...', velocity, 'done');
        if (t < 1) {
          requestAnimationFrame(step);
          return;
        }
        resolve();
      };
      requestAnimationFrame(step);
    });

    if (this.el.loadingCard) {
      this.el.loadingCard.classList.add('loading-card-shake');
      await new Promise((resolve) => setTimeout(resolve, 320));
      this.el.loadingCard.classList.remove('loading-card-shake');
    }

    await new Promise((resolve) => setTimeout(resolve, 180));
    this.el.loading.classList.add('hidden');
  }

  hideLoadingImmediate() {
    this.stopLoadingProgress();
    this.setLoadingProgress(0, 'AI is optimizing routes...', 'Collecting route data...', 0, 'idle');
    this.el.loading.classList.add('hidden');
  }
}