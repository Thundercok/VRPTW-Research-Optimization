export function createInitialState() {
  const savedEmail = localStorage.getItem('vrptw_email') || '';
  return {
    token: localStorage.getItem('vrptw_token') || '',
    email: savedEmail,
    role: localStorage.getItem('vrptw_role') || 'operator',
    resetToken: '',
    mustChangePassword: localStorage.getItem('vrptw_must_change_password') === 'true',
    registerOtpApprovedEmail: '',
    registerOtpVerified: false,
    registerOtpExpiresAt: 0,
    mode: 'sample',
    vehicles: 4,
    capacity: 120,
    customers: [],
    suggest: [],
    selectedSuggest: null,
    analysisVersion: '',
    analysisVersions: [],
    analysisInstance: 'ALL',
    analysisData: null,
    lastResult: null,
    activeTab: 'overview',
    unlocked: Boolean(localStorage.getItem('vrptw_token'))
  };
}
