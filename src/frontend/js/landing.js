/**
 * NAMI Landing Page — Clean Module
 * Extracted from monolithic inline script. Zero canvas diorama, zero ScrollTrigger.
 */
'use strict';

// ===================================================================
// Storage Keys
// ===================================================================
const STORAGE_THEME = 'vrptw_landing_theme_v2';
const STORAGE_LANG = 'vrptw_landing_lang';

// ===================================================================
// Localization Dictionary
// ===================================================================
const i18n = {
  en: {
    'brand.sub': 'Research Optimization',
    'nav.demo': 'Showcase',
    'nav.features': 'Features',
    'nav.results': 'Benchmarks',
    'nav.getstarted': 'Setup',
    'cta.demo': 'Open Planner',

    'hero.badge': 'Solomon Benchmark Optimizer',
    'hero.title.nami': 'NAMI',
    'hero.title.desc': 'Plateau-Aware Deep RL Routing Engine',
    'hero.subtitle': 'Combining Deep Reinforcement Learning with Adaptive Large Neighborhood Search to solve Vehicle Routing Problems with Time Windows in milliseconds.',
    'hero.cta.start': 'Launch Solver',
    'hero.cta.demo': 'Explore Demo',

    'showcase.eyebrow': 'How It Works',
    'showcase.title': 'From chaos to optimal dispatch in 4 acts',

    'act1.badge': '01',
    'act1.title': "What's the fastest way to deliver to 100 addresses?",
    'act1.desc': 'A single vehicle on a simple route is easy. But scaling delivery operations exposes exponential complexity.',

    'act2.badge': '02',
    'act2.title': 'A single route quickly shatters.',
    'act2.desc': 'Every address introduces narrow time windows, load capacity limits, service times, and vehicle constraints. Classical heuristics easily stagnate in sub-optimal local basins.',

    'act3.badge': '03',
    'act3.title': "NAMI's neural controller takes over.",
    'act3.desc': 'A Double Deep Q-Network (DDQN) agent analyzes the search trajectory in real-time, intelligently selecting destroy-and-repair ALNS operators to break stagnation patterns.',

    'act4.badge': '04',
    'act4.title': 'Optimal dispatch. Delivered.',
    'act4.desc': 'Feasible, balanced paths are generated in milliseconds. Dispatchers receive clean, conflict-free delivery plans verified against all Solomon criteria.',

    'stats.eyebrow': 'Performance Snapshot',
    'stats.saved': 'Distance Saved',
    'stats.ontime': 'On-Time Rate',
    'stats.compute': 'Compute Time',
    'stats.fleet': 'Active Fleets',

    'features.eyebrow': 'Engine Architecture',
    'features.title': 'Engineered for Hard Constraints',
    'features.f1.title': 'DDQN Operator Selection',
    'features.f1.body': 'A Double DQN agent observes the search trajectory and learns which destroy operators (Random, Worst, Cluster) to fire when search basins stagnate.',
    'features.f2.title': 'Time-Window Feasibility',
    'features.f2.body': 'Supports strict time windows (ready time, due date, service duration) with dynamic early-arrival waiting and late-arrival filtering.',
    'features.f3.title': 'Solomon Benchmarks',
    'features.f3.body': 'Built-in, one-click loading of Solomon benchmark instances (C, R, RC families) for rapid performance verification.',
    'features.f5.title': 'Zero-Shot Transfer',
    'features.f5.body': 'The trained plateau-aware RL policy transfers directly across different Solomon families (e.g. trained on RC1, evaluated on RC2) without retraining.',

    'results.eyebrow': 'Scientific Validation',
    'results.title': 'Solomon Benchmark Results',
    'table.th.family': 'Instance Family',
    'table.th.bks': 'Best Known Cost (BKS)',
    'table.th.nami': 'NAMI Hybrid Cost',
    'table.th.alns': 'ALNS Baseline Cost',
    'table.th.namigap': 'NAMI Gap vs BKS (%)',
    'table.th.alnsgap': 'ALNS Gap vs BKS (%)',
    'results.footnote': '* Zero-shot generalization transfer: The model was trained exclusively on RC1 instances and evaluated directly on RC2.',
    'results.citation.title': 'Plateau-Aware Deep RL for Combinatorial Search',
    'results.citation.body': 'Our thesis work analyzes DQN-guided escape operators under severe local stagnation states, outperforming traditional static ALNS variants in 7 of 8 benchmark scenarios.',

    'getstarted.eyebrow': 'Developer Quickstart',
    'getstarted.title': 'Run the engine locally in 60s',

    'footer.blurb': 'Deep reinforcement learning and search heuristics paired together for robust combinatorial optimization.',
    'footer.col.system': 'System',
    'footer.col.academic': 'Academic',
    'footer.link.solver': 'Open Solver',
    'footer.link.demo': 'Showcase',
    'footer.link.benchmarks': 'Benchmarks',
    'footer.link.codebase': 'Codebase',
    'footer.link.feedback': 'Feedback Form',
    'footer.link.dispatcher': 'Dispatcher Login',
    'footer.footnote': 'Designed for computational speed and absolute operational clarity.'
  },
  vn: {
    'brand.sub': 'Tối ưu hóa Nghiên cứu',
    'nav.demo': 'Trình diễn',
    'nav.features': 'Tính năng',
    'nav.results': 'Benchmarks',
    'nav.getstarted': 'Cài đặt',
    'cta.demo': 'Mở Planner',

    'hero.badge': 'Trình Tối Ưu Hóa Solomon Benchmark',
    'hero.title.nami': 'NAMI',
    'hero.title.desc': 'Engine Định Tuyến Học Tăng Cường Sâu Plateau-Aware',
    'hero.subtitle': 'Kết hợp Học tăng cường sâu với Thuật toán tìm kiếm lân cận lớn thích ứng để giải quyết bài toán định tuyến xe có khung thời gian trong mili giây.',
    'hero.cta.start': 'Mở Trình Giải',
    'hero.cta.demo': 'Khám Phá Demo',

    'showcase.eyebrow': 'Cách Hoạt Động',
    'showcase.title': 'Từ hỗn loạn đến điều phối tối ưu qua 4 bước',

    'act1.badge': '01',
    'act1.title': 'Đâu là cách nhanh nhất để giao tới 100 địa chỉ?',
    'act1.desc': 'Một phương tiện trên một lộ trình đơn giản thì dễ dàng. Nhưng việc mở rộng hoạt động giao hàng sẽ tạo ra độ phức tạp theo cấp số nhân.',

    'act2.badge': '02',
    'act2.title': 'Lộ trình nhanh chóng bị phá vỡ.',
    'act2.desc': 'Mỗi địa chỉ đi kèm với các khung giờ nghiêm ngặt, giới hạn tải trọng, thời gian phục vụ và các ràng buộc xe. Các heuristic cổ điển rất dễ mắc kẹt ở cực trị địa phương kém tối ưu.',

    'act3.badge': '03',
    'act3.title': 'Bộ điều khiển nơ-ron NAMI tiếp quản.',
    'act3.desc': 'Agent Double Deep Q-Network (DDQN) phân tích quỹ đạo tìm kiếm theo thời gian thực, lựa chọn thông minh các toán tử destroy-and-repair ALNS để phá vỡ các điểm nghẽn chững lại.',

    'act4.badge': '04',
    'act4.title': 'Điều phối tối ưu. Đã hoàn thành.',
    'act4.desc': 'Các lộ trình khả thi, cân bằng được tạo ra trong vài mili giây. Người điều phối nhận được kế hoạch giao hàng rõ ràng, không có xung đột, được xác thực theo tất cả các tiêu chí Solomon.',

    'stats.eyebrow': 'Hiệu Suất',
    'stats.saved': 'Quãng Đường Tiết Kiệm',
    'stats.ontime': 'Tỷ Lệ Đúng Giờ',
    'stats.compute': 'Thời Gian Tính Toán',
    'stats.fleet': 'Đội Xe Hoạt Động',

    'features.eyebrow': 'Kiến trúc Engine',
    'features.title': 'Thiết kế cho Ràng buộc Khó',
    'features.f1.title': 'Chọn toán tử bằng DDQN',
    'features.f1.body': 'Agent Double DQN quan sát quỹ đạo tìm kiếm và học cách kích hoạt các toán tử destroy phù hợp (Random, Worst, Cluster) khi không gian tìm kiếm bị chững lại.',
    'features.f2.title': 'Độ khả thi Khung giờ',
    'features.f2.body': 'Hỗ trợ khung giờ nghiêm ngặt (ready time, due date, service duration) kèm tự động chờ nếu đến sớm và lọc nếu đến muộn.',
    'features.f3.title': 'Benchmark Solomon',
    'features.f3.body': 'Tích hợp sẵn các bộ benchmark Solomon (họ C, R, RC) để tải nhanh chỉ với một click giúp kiểm chứng thuật toán.',
    'features.f5.title': 'Zero-Shot Transfer',
    'features.f5.body': 'Policy RL nhận diện plateau sau khi huấn luyện có thể chuyển giao trực tiếp sang các họ Solomon khác (ví dụ: huấn luyện trên RC1, chạy thử trên RC2) mà không cần train lại.',

    'results.eyebrow': 'Xác thực Khoa học',
    'results.title': 'Kết quả Benchmark Solomon',
    'table.th.family': 'Họ Solomon Instance',
    'table.th.bks': 'Chi Phí Tốt Nhất (BKS)',
    'table.th.nami': 'Chi Phí NAMI Hybrid',
    'table.th.alns': 'Chi Phí ALNS Baseline',
    'table.th.namigap': 'NAMI Gap so với BKS (%)',
    'table.th.alnsgap': 'ALNS Gap so với BKS (%)',
    'results.footnote': '* Chuyển giao tổng quát hóa Zero-shot: Mô hình được huấn luyện duy nhất trên các instance họ RC1 và được đánh giá trực tiếp trên họ RC2.',
    'results.citation.title': 'Học Tăng Cường Sâu Plateau-Aware cho Bài Toán Tìm Kiếm Tổ Hợp',
    'results.citation.body': 'Nghiên cứu luận văn của chúng tôi phân tích các toán tử thoát khỏi cực trị cục bộ do DQN hướng dẫn dưới các trạng thái chững lại nghiêm trọng, vượt trội hơn các biến thể ALNS tĩnh truyền thống trong 7 trên 8 kịch bản thử nghiệm.',

    'getstarted.eyebrow': 'Khởi động nhanh cho Dev',
    'getstarted.title': 'Chạy cục bộ engine trong 60 giây',

    'footer.blurb': 'Sự kết hợp giữa học tăng cường sâu và thuật toán tìm kiếm cục bộ giúp giải quyết các bài toán tối ưu tổ hợp phức tạp một cách mạnh mẽ.',
    'footer.col.system': 'Hệ Thống',
    'footer.col.academic': 'Học Thuật',
    'footer.link.solver': 'Mở Trình Giải',
    'footer.link.demo': 'Demo Trực Quan',
    'footer.link.benchmarks': 'Điểm Chuẩn (Benchmarks)',
    'footer.link.codebase': 'Kho Mã Nguồn',
    'footer.link.feedback': 'Biểu Mẫu Góp Ý',
    'footer.link.dispatcher': 'Đăng Nhập Điều Phối',
    'footer.footnote': 'Thiết kế cho tốc độ tính toán cao và độ trực quan vận hành tuyệt đối.'
  }
};

// ===================================================================
// Language
// ===================================================================
function getStoredLang() {
  const v = localStorage.getItem(STORAGE_LANG);
  if (v === 'en' || v === 'vn') return v;
  const navLang = (navigator.language || '').toLowerCase();
  if (navLang.startsWith('vi')) return 'vn';
  return 'en';
}

function applyLang(lang) {
  const dict = i18n[lang] || i18n.en;
  document.documentElement.lang = lang === 'vn' ? 'vi' : 'en';
  document.querySelectorAll('[data-i18n]').forEach((node) => {
    const key = node.getAttribute('data-i18n');
    if (dict[key]) node.textContent = dict[key];
  });
  const label = document.getElementById('lang-label');
  if (label) label.textContent = lang === 'vn' ? 'VN' : 'EN';
  localStorage.setItem(STORAGE_LANG, lang);
}

// ===================================================================
// Theme
// ===================================================================
function getStoredTheme() {
  const v = localStorage.getItem(STORAGE_THEME);
  if (v === 'light' || v === 'dark') return v;
  return 'dark';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(STORAGE_THEME, theme);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', theme === 'dark' ? '#070913' : '#f6f9fc');
  const sunIcon = document.querySelector('.sun-icon');
  const moonIcon = document.querySelector('.moon-icon');
  if (sunIcon && moonIcon) {
    sunIcon.style.display = theme === 'dark' ? 'none' : 'block';
    moonIcon.style.display = theme === 'dark' ? 'block' : 'none';
  }
}

function setupControls() {
  const langBtn = document.getElementById('lang-toggle');
  const themeBtn = document.getElementById('theme-toggle');

  let currentLang = getStoredLang();
  let currentTheme = getStoredTheme();

  applyLang(currentLang);
  applyTheme(currentTheme);

  langBtn?.addEventListener('click', () => {
    currentLang = currentLang === 'en' ? 'vn' : 'en';
    applyLang(currentLang);
  });

  themeBtn?.addEventListener('click', (e) => {
    const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
    if (document.startViewTransition) {
      const x = e.clientX;
      const y = e.clientY;
      document.documentElement.style.setProperty('--vt-x', `${x}px`);
      document.documentElement.style.setProperty('--vt-y', `${y}px`);
      document.startViewTransition(() => {
        currentTheme = nextTheme;
        applyTheme(currentTheme);
      });
    } else {
      currentTheme = nextTheme;
      applyTheme(currentTheme);
    }
  });
}

// ===================================================================
// Mobile Menu
// ===================================================================
function setupMobileMenu() {
  const btn = document.getElementById('mobile-menu-btn');
  const menu = document.getElementById('mobile-menu');
  if (!btn || !menu) return;

  btn.addEventListener('click', () => {
    const isOpen = menu.classList.toggle('open');
    menu.hidden = !isOpen;
    btn.setAttribute('aria-expanded', String(isOpen));
    btn.classList.toggle('active');
  });

  menu.querySelectorAll('a').forEach((a) => {
    a.addEventListener('click', () => {
      menu.classList.remove('open');
      menu.hidden = true;
      btn.setAttribute('aria-expanded', 'false');
      btn.classList.remove('active');
    });
  });
}

// ===================================================================
// Scroll Spy
// ===================================================================
function setupScrollSpy() {
  const navLinks = Array.from(document.querySelectorAll('.nav-links a'));
  const sections = navLinks
    .map((link) => {
      const id = link.getAttribute('href') || '';
      if (!id.startsWith('#')) return null;
      const target = document.querySelector(id);
      return target ? { link, target } : null;
    })
    .filter(Boolean);

  if (!sections.length || !('IntersectionObserver' in window)) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const match = sections.find((s) => s.target === entry.target);
        if (!match) return;
        navLinks.forEach((l) => l.classList.remove('active'));
        match.link.classList.add('active');
      });
    },
    { rootMargin: '-40% 0px -50% 0px', threshold: 0 }
  );

  sections.forEach(({ target }) => observer.observe(target));
}

// ===================================================================
// Navbar Scroll Effect
// ===================================================================
function setupNavbarScroll() {
  const nav = document.querySelector('.site-nav');
  if (!nav) return;
  window.addEventListener(
    'scroll',
    () => { nav.classList.toggle('is-scrolled', window.scrollY > 20); },
    { passive: true }
  );
}

// ===================================================================
// CLI Tabs + Copy
// ===================================================================
function setupCLITabs() {
  const tabs = document.querySelectorAll('.cli-tab-btn');
  const panes = document.querySelectorAll('.cli-pane');

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const targetId = tab.getAttribute('data-target');
      tabs.forEach((t) => t.classList.remove('active'));
      panes.forEach((p) => p.classList.remove('active'));
      tab.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  function showTooltip(btn) {
    const tooltip = btn.querySelector('.copy-success-tooltip');
    const btnText = btn.querySelector('.btn-copy-text');
    if (tooltip) {
      tooltip.classList.add('show');
      if (btnText) btnText.textContent = 'Copied!';
      setTimeout(() => {
        tooltip.classList.remove('show');
        if (btnText) btnText.textContent = 'Copy';
      }, 1500);
    }
  }

  function fallbackCopyText(text, btn) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      showTooltip(btn);
    } catch (err) {
      console.error('Fallback copy failed', err);
    }
    document.body.removeChild(textArea);
  }

  document.querySelectorAll('.btn-copy-code').forEach((btn) => {
    btn.addEventListener('click', () => {
      const pane = btn.closest('.cli-pane');
      const codeBlock = pane?.querySelector('.cli-code-block');
      if (!codeBlock) return;

      const commands = Array.from(codeBlock.querySelectorAll('.cli-command'))
        .map((el) => el.textContent.trim())
        .join('\n');

      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(commands).then(() => showTooltip(btn)).catch(() => fallbackCopyText(commands, btn));
      } else {
        fallbackCopyText(commands, btn);
      }
    });
  });
}

// ===================================================================
// Scroll Reveal (IntersectionObserver)
// ===================================================================
function setupScrollReveal() {
  const revealEls = document.querySelectorAll('.reveal');
  if (!revealEls.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    },
    { rootMargin: '0px 0px -60px 0px', threshold: 0.1 }
  );

  revealEls.forEach((el) => observer.observe(el));
}

// ===================================================================
// Animated Stat Counters
// ===================================================================
function setupCounters() {
  const counters = document.querySelectorAll('[data-count-to]');
  if (!counters.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        observer.unobserve(el);

        const target = parseFloat(el.getAttribute('data-count-to'));
        const suffix = el.getAttribute('data-count-suffix') || '';
        const prefix = el.getAttribute('data-count-prefix') || '';
        const decimals = (el.getAttribute('data-count-decimals') || '0') | 0;
        const duration = 1600;
        const start = performance.now();

        function tick(now) {
          const elapsed = now - start;
          const progress = Math.min(elapsed / duration, 1);
          // Ease out cubic
          const eased = 1 - Math.pow(1 - progress, 3);
          const current = target * eased;
          el.textContent = prefix + current.toFixed(decimals) + suffix;
          if (progress < 1) requestAnimationFrame(tick);
        }

        requestAnimationFrame(tick);
      });
    },
    { threshold: 0.3 }
  );

  counters.forEach((el) => observer.observe(el));
}



// ===================================================================
// Bento Card Glow Effect
// ===================================================================
function setupBentoGlow() {
  document.querySelectorAll('.bento-card').forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty('--mouse-x', `${e.clientX - rect.left}px`);
      card.style.setProperty('--mouse-y', `${e.clientY - rect.top}px`);
    });
  });
}

// ===================================================================
// Boot
// ===================================================================
document.addEventListener('DOMContentLoaded', () => {
  setupControls();
  setupMobileMenu();
  setupScrollSpy();
  setupNavbarScroll();
  setupCLITabs();
  setupBentoGlow();
  setupScrollReveal();
  setupCounters();
  setupRoutingCanvas();
});

// ===================================================================
// NAMI Animated Routing Canvas
// ===================================================================
function setupRoutingCanvas() {
  const canvas = document.getElementById('nc');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let w, h;

  // Set high-DPI scaling
  function resize() {
    w = canvas.width = canvas.offsetWidth * Math.min(devicePixelRatio, 2);
    h = canvas.height = canvas.offsetHeight * Math.min(devicePixelRatio, 2);
    ctx.resetTransform();
    ctx.scale(Math.min(devicePixelRatio, 2), Math.min(devicePixelRatio, 2));
  }

  // Clustered Solomon-like node layout (56 nodes: 1 depot + 55 clients)
  const allNodes = [];
  // Depot at center
  allNodes.push({ x: 0.5, y: 0.5, type: 'depot', r: 4.5, label: 'DEPOT' });

  // Deterministic seed helper
  function seedRandom(i) {
    const x = Math.sin(i * 12345.678) * 10000;
    return x - Math.floor(x);
  }

  // Define 5 wide cluster zones covering the entire page background
  const clusters = [
    { cx: 0.20, cy: 0.25 }, // Top Left
    { cx: 0.80, cy: 0.22 }, // Top Right
    { cx: 0.22, cy: 0.75 }, // Bottom Left
    { cx: 0.78, cy: 0.72 }, // Bottom Right
    { cx: 0.50, cy: 0.48 }  // Center Cluster
  ];

  // Distribute 55 clients among clusters to cover the background densely
  for (let i = 0; i < 55; i++) {
    const cIdx = i % clusters.length;
    const c = clusters[cIdx];
    const angle = seedRandom(i * 3) * Math.PI * 2;
    const dist = seedRandom(i * 7) * 0.15 + 0.03;
    allNodes.push({
      x: c.cx + Math.cos(angle) * dist,
      y: c.cy + Math.sin(angle) * dist,
      type: 'client',
      r: 2,
      label: `C-${100 + i}`
    });
  }

  // Isometric projection helper
  function isoProject(x, y, cw, ch) {
    const cx = cw / 2;
    const cy = ch * 0.52; // Centered vertically, leaving navbar space
    
    // Scale uniformly to cover 92% of screen height/width
    const scale = Math.min(cw, ch) * 0.92;
    const px = (x - 0.5) * scale;
    const py = (y - 0.5) * scale;
    
    // Isometric mapping with slightly wider projection angles for widescreen visual
    const isoX = cx + (px - py) * 0.95;
    const isoY = cy + (px + py) * 0.46;
    return { x: isoX, y: isoY };
  }

  // Group and sort node indices by cluster zone (to form neat, local routing loops)
  const clusterNodes = [[], [], [], [], []];
  for (let idx = 1; idx < allNodes.length; idx++) {
    const cIdx = (idx - 1) % 5;
    clusterNodes[cIdx].push(idx);
  }

  // Sort nodes in each cluster clockwise relative to their cluster center
  clusters.forEach((c, cIdx) => {
    clusterNodes[cIdx].sort((a, b) => {
      const angleA = Math.atan2(allNodes[a].y - c.cy, allNodes[a].x - c.cx);
      const angleB = Math.atan2(allNodes[b].y - c.cy, allNodes[b].x - c.cx);
      return angleA - angleB;
    });
  });

  // Define 7 regional vehicle routes by partitioning the sorted clusters
  const vehicles = [
    {
      id: 1,
      route: [0, ...clusterNodes[0].slice(0, 6), 0], // Top Left A
      speed: 0.0065,
      progress: 0,
      segment: 0,
      color: '#00d4ff', // Cyan
      trail: [],
      rerouteActive: false,
      rerouteTime: 0,
      reroutePos: null
    },
    {
      id: 2,
      route: [0, ...clusterNodes[1].slice(0, 6), 0], // Top Right A
      speed: 0.0075,
      progress: 0.15,
      segment: 0,
      color: '#a855f7', // Purple
      trail: [],
      rerouteActive: false,
      rerouteTime: 0,
      reroutePos: null
    },
    {
      id: 3,
      route: [0, ...clusterNodes[2], 0], // Bottom Left
      speed: 0.0055,
      progress: 0.3,
      segment: 0,
      color: '#ec4899', // Pink
      trail: [],
      rerouteActive: false,
      rerouteTime: 0,
      reroutePos: null
    },
    {
      id: 4,
      route: [0, ...clusterNodes[3], 0], // Bottom Right
      speed: 0.007,
      progress: 0.45,
      segment: 0,
      color: '#f59e0b', // Amber/Orange
      trail: [],
      rerouteActive: false,
      rerouteTime: 0,
      reroutePos: null
    },
    {
      id: 5,
      route: [0, ...clusterNodes[4], 0], // Center
      speed: 0.005,
      progress: 0.6,
      segment: 0,
      color: '#10b981', // Emerald
      trail: [],
      rerouteActive: false,
      rerouteTime: 0,
      reroutePos: null
    },
    {
      id: 6,
      route: [0, ...clusterNodes[0].slice(6), 0], // Top Left B
      speed: 0.008,
      progress: 0.05,
      segment: 0,
      color: '#22c55e', // Green
      trail: [],
      rerouteActive: false,
      rerouteTime: 0,
      reroutePos: null
    },
    {
      id: 7,
      route: [0, ...clusterNodes[1].slice(6), 0], // Top Right B
      speed: 0.006,
      progress: 0.25,
      segment: 0,
      color: '#0ea5e9', // Sky Blue
      trail: [],
      rerouteActive: false,
      rerouteTime: 0,
      reroutePos: null
    }
  ];

  // Catmull-Rom spline interpolation
  function catmullRom(p0, p1, p2, p3, t) {
    const t2 = t * t;
    const t3 = t2 * t;
    const x = 0.5 * (
      (2 * p1.x) +
      (-p0.x + p2.x) * t +
      (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 +
      (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3
    );
    const y = 0.5 * (
      (2 * p1.y) +
      (-p0.y + p2.y) * t +
      (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 +
      (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3
    );
    return { x, y };
  }

  function getWaypoint(route, idx) {
    const len = route.length;
    const i = (idx + len) % len;
    return allNodes[route[i]];
  }

  // Telemetry logs
  const logs = [
    'SYSTEM: Cluster-aware VRPTW solver online',
    'GNN: Embedding active nodes for edge weights',
    'DDQN: Evaluating escape operator pool...',
    'ALNS: Base constructive layout initialized'
  ];

  function addLog(text) {
    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0];
    logs.push(`[${timeStr}] ${text}`);
    if (logs.length > 5) logs.shift();
  }

  let frameCount = 0;
  let epoch = 48;
  let currentCost = 1284.2;
  const costParticles = [];



  // Animation frame loop
  function draw() {
    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;
    if (cw === 0 || ch === 0) {
      requestAnimationFrame(draw);
      return;
    }
    
    // Clear canvas transparently to let gradient orbs and page background show through
    ctx.clearRect(0, 0, cw, ch);

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    const vehColors = {
      '#00d4ff': isDark ? '#00d4ff' : '#0284c7', // Cyan
      '#a855f7': isDark ? '#a855f7' : '#7c3aed', // Purple
      '#ec4899': isDark ? '#ec4899' : '#db2777', // Pink
      '#f59e0b': isDark ? '#f59e0b' : '#d97706', // Orange
      '#10b981': isDark ? '#10b981' : '#059669', // Emerald
      '#22c55e': isDark ? '#22c55e' : '#16a34a', // Green
      '#0ea5e9': isDark ? '#0ea5e9' : '#0284c7'  // Sky Blue
    };
    
    // Dynamic theme-based colors configuration (brighter connections, fainter grid)
    const colors = {
      grid: isDark ? 'rgba(122, 115, 255, 0.015)' : 'rgba(99, 91, 255, 0.03)',
      connections: isDark ? 'rgba(122, 115, 255, 0.28)' : 'rgba(99, 91, 255, 0.32)',
      depot: isDark ? '#7a73ff' : '#635bff',
      depotGlow: isDark ? 'rgba(122, 115, 255, 0.12)' : 'rgba(99, 91, 255, 0.18)',
      clientStroke: isDark ? 'rgba(0, 212, 255, 0.65)' : 'rgba(2, 132, 199, 0.75)',
      clientFill: isDark ? 'rgba(0, 212, 255, 0.04)' : 'rgba(2, 132, 199, 0.06)',
      nodeCore: '#ffffff'
    };

    // Draw isometric grid (extremely sparse, minimal perspective references)
    ctx.strokeStyle = colors.grid;
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    for (let i = -2; i <= 4; i++) {
      const p1 = isoProject(i * 0.5, -1, cw, ch);
      const p2 = isoProject(i * 0.5, 2, cw, ch);
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);

      const p3 = isoProject(-1, i * 0.5, cw, ch);
      const p4 = isoProject(2, i * 0.5, cw, ch);
      ctx.moveTo(p3.x, p3.y);
      ctx.lineTo(p4.x, p4.y);
    }
    ctx.stroke();

    // Draw the optimized vehicle route paths (delicate dashed regional sweep loops)
    vehicles.forEach((veh) => {
      const drawColor = vehColors[veh.color] || veh.color;
      
      // Convert hex color to rgba with low opacity for an elegant outline
      let rgbaColor = 'rgba(122, 115, 255, 0.08)';
      if (drawColor.startsWith('#')) {
        const r = parseInt(drawColor.slice(1, 3), 16);
        const g = parseInt(drawColor.slice(3, 5), 16);
        const b = parseInt(drawColor.slice(5, 7), 16);
        rgbaColor = `rgba(${r}, ${g}, ${b}, ${isDark ? 0.06 : 0.11})`;
      }
      
      ctx.strokeStyle = rgbaColor;
      ctx.lineWidth = 0.85;
      ctx.setLineDash([2, 4]); // Dashed line for blueprint aesthetic
      ctx.beginPath();
      
      const rLen = veh.route.length;
      // Draw smooth closed loop using Catmull-Rom interpolation
      for (let s = 0; s < rLen - 1; s++) {
        const w0 = getWaypoint(veh.route, s - 1);
        const w1 = getWaypoint(veh.route, s);
        const w2 = getWaypoint(veh.route, s + 1);
        const w3 = getWaypoint(veh.route, s + 2);
        
        for (let step = 0; step <= 20; step++) {
          const t = step / 20;
          const normPos = catmullRom(w0, w1, w2, w3, t);
          const pos = isoProject(normPos.x, normPos.y, cw, ch);
          if (s === 0 && step === 0) {
            ctx.moveTo(pos.x, pos.y);
          } else {
            ctx.lineTo(pos.x, pos.y);
          }
        }
      }
      ctx.stroke();
      ctx.setLineDash([]); // Reset dash pattern
    });
    ctx.globalAlpha = 1.0;



    // Update & draw vehicles
    vehicles.forEach((veh) => {
      // 1. Move vehicle
      veh.progress += veh.speed;
      if (veh.progress >= 1.0) {
        veh.progress = 0;
        veh.segment = (veh.segment + 1) % veh.route.length;
      }

      // 2. Interpolate path
      const w0 = getWaypoint(veh.route, veh.segment - 1);
      const w1 = getWaypoint(veh.route, veh.segment);
      const w2 = getWaypoint(veh.route, veh.segment + 1);
      const w3 = getWaypoint(veh.route, veh.segment + 2);

      const normPos = catmullRom(w0, w1, w2, w3, veh.progress);
      const pos = isoProject(normPos.x, normPos.y, cw, ch);

      // 3. Track trail
      veh.trail.push({ x: pos.x, y: pos.y });
      if (veh.trail.length > 24) veh.trail.shift();

      const drawColor = vehColors[veh.color] || veh.color;

      // Draw tapered trail (ratio-weighted width + opacity)
      const trailLen = veh.trail.length;
      if (trailLen > 1) {
        for (let k = 1; k < trailLen; k++) {
          const ratio = k / trailLen;
          ctx.beginPath();
          ctx.moveTo(veh.trail[k - 1].x, veh.trail[k - 1].y);
          ctx.lineTo(veh.trail[k].x, veh.trail[k].y);
          
          ctx.strokeStyle = drawColor;
          ctx.lineWidth = ratio * 2.8 + 0.5; // thick to thin
          ctx.globalAlpha = Math.pow(ratio, 2.5) * 0.95; // fast fade towards tail
          ctx.stroke();
        }
        ctx.globalAlpha = 1.0; // reset
      }

      // Draw active ALNS search neighborhood (dynamic proximity scan lines)
      ctx.lineWidth = 0.7;
      allNodes.forEach((node) => {
        if (node.type === 'depot') return;
        const nodePos = isoProject(node.x, node.y, cw, ch);
        const dx = pos.x - nodePos.x;
        const dy = pos.y - nodePos.y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 160) {
          const alpha = (1.0 - dist / 160) * (isDark ? 0.32 : 0.42);
          // Convert hex vehicle color to rgba dynamically
          let scanRgb = '122, 115, 255';
          if (drawColor.startsWith('#')) {
            const r = parseInt(drawColor.slice(1, 3), 16);
            const g = parseInt(drawColor.slice(3, 5), 16);
            const b = parseInt(drawColor.slice(5, 7), 16);
            scanRgb = `${r}, ${g}, ${b}`;
          }
          ctx.strokeStyle = `rgba(${scanRgb}, ${alpha})`;
          ctx.beginPath();
          ctx.moveTo(pos.x, pos.y);
          ctx.lineTo(nodePos.x, nodePos.y);
          ctx.stroke();
        }
      });

      // Draw faint search boundary ring in vehicle color
      let ringRgb = '122, 115, 255';
      if (drawColor.startsWith('#')) {
        const r = parseInt(drawColor.slice(1, 3), 16);
        const g = parseInt(drawColor.slice(3, 5), 16);
        const b = parseInt(drawColor.slice(5, 7), 16);
        ringRgb = `${r}, ${g}, ${b}`;
      }
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 160, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${ringRgb}, ${isDark ? 0.065 : 0.125})`;
      ctx.lineWidth = 0.6;
      ctx.stroke();

      // Draw glowing vehicle head
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.shadowBlur = 12;
      ctx.shadowColor = drawColor;
      ctx.fill();
      ctx.shadowBlur = 0;

      // 4. Stochastic Reroute Event
      if (Math.random() < 0.0018) {
        veh.rerouteActive = true;
        veh.rerouteTime = 0;
        veh.reroutePos = { x: pos.x, y: pos.y };

        const reduction = Math.random() * 4.5 + 0.5;
        currentCost -= reduction;
        if (currentCost < 828.3) currentCost = 1284.2;

        costParticles.push({
          x: pos.x,
          y: pos.y - 12,
          text: `-${reduction.toFixed(1)}`,
          alpha: 1.0
        });

        addLog(`DDQN: Reroute V-${veh.id} -> Cost ${currentCost.toFixed(1)}`);
      }

      // Draw double-ring expanding burst
      if (veh.rerouteActive) {
        veh.rerouteTime++;
        const progress = veh.rerouteTime / 35;
        if (progress >= 1.0) {
          veh.rerouteActive = false;
        } else {
          const alpha = 1.0 - progress;
          // Outer orange burst
          ctx.beginPath();
          ctx.arc(veh.reroutePos.x, veh.reroutePos.y, progress * 32, 0, Math.PI * 2);
          ctx.strokeStyle = isDark ? `rgba(255, 94, 0, ${alpha})` : `rgba(234, 88, 12, ${alpha})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Inner violet burst
          ctx.beginPath();
          ctx.arc(veh.reroutePos.x, veh.reroutePos.y, progress * 16, 0, Math.PI * 2);
          ctx.strokeStyle = isDark ? `rgba(122, 115, 255, ${alpha * 0.8})` : `rgba(99, 91, 255, ${alpha * 0.85})`;
          ctx.lineWidth = 1.2;
          ctx.stroke();
        }
      }
    });

    // Draw nodes
    allNodes.forEach((node) => {
      const pos = isoProject(node.x, node.y, cw, ch);
      
      if (node.type === 'depot') {
        const pulse = Math.sin(Date.now() / 250) * 2.5;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, node.r + pulse, 0, Math.PI * 2);
        ctx.fillStyle = colors.depotGlow;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(pos.x, pos.y, node.r, 0, Math.PI * 2);
        ctx.fillStyle = colors.depot;
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, node.r, 0, Math.PI * 2);
        ctx.fillStyle = colors.clientFill;
        ctx.strokeStyle = colors.clientStroke;
        ctx.lineWidth = 1.2;
        ctx.fill();
        ctx.stroke();
      }

      // Draw white center core
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, node.type === 'depot' ? 3.5 : 1.8, 0, Math.PI * 2);
      ctx.fillStyle = colors.nodeCore;
      ctx.fill();
    });

    // Update & draw cost particle drops
    for (let i = costParticles.length - 1; i >= 0; i--) {
      const p = costParticles[i];
      p.y -= 0.8;
      p.alpha -= 0.025;
      if (p.alpha <= 0) {
        costParticles.splice(i, 1);
      } else {
        ctx.fillStyle = isDark ? `rgba(255, 94, 0, ${p.alpha})` : `rgba(234, 88, 12, ${p.alpha})`;
        ctx.font = 'bold 9px "JetBrains Mono", monospace';
        ctx.fillText(p.text, p.x + 6, p.y);
      }
    }

    // Epoch Live Updater
    frameCount++;
    if (frameCount % 45 === 0) {
      epoch++;
      if (epoch > 600) epoch = 1;
    }

    requestAnimationFrame(draw);
  }

  resize();
  draw();
  window.addEventListener('resize', resize);
}
