export function createInitialState() {
  const savedEmail = localStorage.getItem('vrptw_email') || '';
  const unlocked = Boolean(localStorage.getItem('vrptw_token'));

  // Pre-seed a realistic driver fleet simulation if not already configured
  const savedFleet = localStorage.getItem('vrptw_fleet_config');
  let fleet = [];
  if (savedFleet) {
    try {
      fleet = JSON.parse(savedFleet);
    } catch (e) {
      console.warn('Failed to parse saved fleet:', e);
    }
  }

  if (fleet.length === 0) {
    const seedDrivers = [
      { name: 'Nguyễn Minh Tuấn', speed: 1.05, shiftStart: '06:00', shiftEnd: '15:00', breakStart: '10:30', breakDuration: 30, skills: 'None', status: 'Active' },
      { name: 'Phạm Hoàng Nam', speed: 0.98, shiftStart: '08:00', shiftEnd: '17:00', breakStart: '12:00', breakDuration: 45, skills: 'Refrigerated', status: 'Active' },
      { name: 'Lê Văn Hùng', speed: 0.90, shiftStart: '07:30', shiftEnd: '16:30', breakStart: '11:30', breakDuration: 40, skills: 'Hazmat', status: 'In Transit' },
      { name: 'Trần Quốc Bảo', speed: 1.02, shiftStart: '08:00', shiftEnd: '17:00', breakStart: '12:00', breakDuration: 30, skills: 'Express', status: 'Active' },
      { name: 'Vũ Đức Duy', speed: 0.95, shiftStart: '06:30', shiftEnd: '15:30', breakStart: '11:00', breakDuration: 30, skills: 'Refrigerated', status: 'On Break' },
      { name: 'Đặng Minh Triết', speed: 1.10, shiftStart: '08:30', shiftEnd: '17:30', breakStart: '12:30', breakDuration: 30, skills: 'Express', status: 'Active' },
      { name: 'Hoàng Văn Phong', speed: 0.88, shiftStart: '09:00', shiftEnd: '18:00', breakStart: '13:00', breakDuration: 60, skills: 'Hazmat', status: 'Active' }
    ];
    for (let i = 0; i < 7; i++) {
      const d = seedDrivers[i];
      fleet.push({
        id: i,
        driver: d.name,
        capacity: 120,
        speed: d.speed,
        shiftStart: d.shiftStart,
        shiftEnd: d.shiftEnd,
        breakStart: d.breakStart,
        breakDuration: d.breakDuration,
        skills: d.skills,
        status: d.status
      });
    }
    localStorage.setItem('vrptw_fleet_config', JSON.stringify(fleet));
  }

  return {
    lang: localStorage.getItem('vrptw_demo_lang') === 'vn' ? 'vn' : 'en',
    token: localStorage.getItem('vrptw_token') || '',
    email: savedEmail,
    role: localStorage.getItem('vrptw_role') || 'operator',
    resetToken: '',
    mustChangePassword: localStorage.getItem('vrptw_must_change_password') === 'true',
    registerOtpApprovedEmail: '',
    registerOtpVerified: false,
    registerOtpExpiresAt: 0,
    mode: 'sample',
    vehicles: fleet.length || 7,
    capacity: 120,
    customers: [],
    solomonDatasets: [],
    selectedDataset: 'demo',
    suggest: [],
    selectedSuggest: null,
    analysisVersion: '',
    analysisVersions: [],
    analysisInstance: 'ALL',
    analysisData: null,
    analysisActivity: null,
    adminFeedback: [],
    lastResult: null,
    activeTab: 'dispatch',
    unlocked,
    showLoginModal: !unlocked,
    fleet,
  };
}
