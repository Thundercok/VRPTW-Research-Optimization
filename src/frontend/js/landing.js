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

    'hero.badge': 'v3.2 · Hybrid-DDQN · Solomon + Homberger',
    'hero.title.nami': 'NAMI',
    'hero.title.desc': 'Plateau-Aware Deep RL Routing Engine',
    'hero.subtitle': 'Combining Deep Reinforcement Learning with Adaptive Large Neighborhood Search to solve Vehicle Routing Problems with Time Windows in milliseconds.',
    'hero.cta.start': 'Open Dispatch Portal',
    'hero.cta.code': 'View Codebase →',

    'ticker.epoch': 'Epoch:',
    'ticker.cost': 'Cost:',
    'ticker.plateau': 'Plateau Level:',

    'pipeline.eyebrow': 'Algorithm · 4 Stages',
    'pipeline.title': 'Plateau-Aware Escape Pipeline',
    'pipeline.s1.title': 'Constructive Decoder',
    'pipeline.s1.body': 'Initial solution generated via greedy route construction and DDQN-guided insertion heuristic initialization.',
    'pipeline.s2.title': 'Stagnation Detection',
    'pipeline.s2.body': 'Tracks the search trajectory in real time, detecting local minima plateaus when improvement patience thresholds are violated.',
    'pipeline.s3.title': 'DDQN Guided Repair',
    'pipeline.s3.body': 'Double Deep Q-Network selects optimal combinations of destroy and repair operators to successfully break search basin stagnation.',
    'pipeline.s4.title': 'Optima Convergence',
    'pipeline.s4.body': 'Performs local search optimization and Set Partitioning formulation to recombine elite routes into the final feasible route plan.',

    'stats.instances': 'Solomon + Homberger instances tested',
    'stats.seeds': 'independent seeds (cold-starts)',
    'stats.wilcoxon': 'in 5 of 6 scale comparisons',
    'stats.overhead': 'compute overhead vs ALNS-Base',

    'features.eyebrow': 'Engine Architecture',
    'features.title': 'Engineered for Hard Constraints',
    'features.f1.title': 'DDQN Plateau Controller',
    'features.f1.bullet1': 'Prioritized Experience Replay (PER) with beta-annealing',
    'features.f1.bullet2': 'Welford reward normalization for stable training',
    'features.f1.bullet3': 'Dynamically shifts search mode upon stagnation',
    'features.f2.title': 'Adaptive Search Engine',
    'features.f2.bullet1': '8 destroy and 5 insertion operators',
    'features.f2.bullet2': 'Thompson-bandit operator selection policy',
    'features.f2.bullet3': 'Granular local search heuristics',
    'features.f3.title': 'Learned Acceptance Criterion (LAC)',
    'features.f3.bullet1': 'Neural network solution acceptance classifier',
    'features.f3.bullet2': 'Replaces traditional simulated annealing schedule',
    'features.f3.bullet3': 'Adapts to current trajectory characteristics',
    'features.f5.title': 'Set-Partitioning MILP Recombinator',
    'features.f5.bullet1': 'Sub-route extraction during search trajectory',
    'features.f5.bullet2': 'Global recombination via mixed-integer equations',
    'features.f5.bullet3': 'Guarantees optimal layout of elite sub-routes',

    'results.eyebrow': 'Scientific Validation',
    'results.title': 'Solomon & Homberger Benchmark Results',
    'table.th.instance': 'Instance / Family',
    'table.th.scale': 'Scale',
    'table.th.bks': 'BKS (NV / TD)',
    'table.th.nami': 'NAMI Hybrid (NV / TD)',
    'table.th.alns': 'ALNS Baseline (NV / TD)',
    'table.th.wilcoxon': 'Wilcoxon p-value',
    'table.group.100': '100-Customer Instances (Solomon Benchmarks)',
    'table.group.200': '200-Customer Instances (Gehring-Homberger Benchmarks)',
    'table.group.400': '400-Customer Instances (Gehring-Homberger Benchmarks)',
    'table.summary': 'Summary: NAMI Hybrid-DDQN matches BKS vehicle floors at 100/200 scale and achieves statistically significant (p < 0.05) vehicle reductions at 400 scale.',
    'results.footnote.dagger': '† Travel Distance (TD) comparisons are excluded when vehicle counts (NV) are not matched, as extra vehicle capacity artificially distorts travel distance.',
    'results.footnote.coldstart': 'Note: Standalone solver results are generated under strict independent cold-start conditions starting from build_greedy in a cleared directory, without multi-stage warm-starts.',
    'results.footnote.wilcoxon': '* Statistically significant difference between NAMI Hybrid and ALNS Baseline (Wilcoxon signed-rank test p < 0.05).',
    'results.citation.title': 'Plateau-Aware Deep RL for Combinatorial Search',
    'results.citation.body': 'Our thesis work analyzes DQN-guided escape operators under severe local stagnation states, outperforming traditional static ALNS variants in 7 of 8 benchmark scenarios.',

    'getstarted.eyebrow': 'Developer Quickstart',
    'getstarted.title': 'Run the engine locally',
    'cli.explorer': 'EXPLORER'
  },
  vn: {
    'brand.sub': 'Tối ưu hóa Nghiên cứu',
    'nav.demo': 'Trình diễn',
    'nav.features': 'Tính năng',
    'nav.results': 'Benchmarks',
    'nav.getstarted': 'Cài đặt',
    'cta.demo': 'Mở Planner',

    'hero.badge': 'v3.2 · Hybrid-DDQN · Solomon + Homberger',
    'hero.title.nami': 'NAMI',
    'hero.title.desc': 'Engine Định Tuyến Học Tăng Cường Sâu Plateau-Aware',
    'hero.subtitle': 'Kết hợp Học tăng cường sâu với Thuật toán tìm kiếm lân cận lớn thích ứng để giải quyết bài toán định tuyến xe có khung thời gian trong mili giây.',
    'hero.cta.start': 'Mở Cổng Điều Phối',
    'hero.cta.code': 'Xem Kho Mã Nguồn →',

    'ticker.epoch': 'Kỷ nguyên:',
    'ticker.cost': 'Chi phí:',
    'ticker.plateau': 'Mức độ chững:',

    'pipeline.eyebrow': 'Thuật toán · 4 Giai đoạn',
    'pipeline.title': 'Quỹ đạo Vượt cực trị của NAMI',
    'pipeline.s1.title': 'Bộ Giải Mã Constructive',
    'pipeline.s1.body': 'Khởi tạo phương án ban đầu bằng thuật toán chèn tham lam và chèn điểm theo định hướng của mạng nơ-ron DDQN.',
    'pipeline.s2.title': 'Nhận Diện Điểm Chững',
    'pipeline.s2.body': 'Theo dõi quỹ đạo tìm kiếm thời gian thực, phát hiện các điểm chững cực trị địa phương khi vượt quá ngưỡng kiên nhẫn.',
    'pipeline.s3.title': 'Sửa Lỗi Hướng Dẫn bằng DDQN',
    'pipeline.s3.body': 'Mạng Q-learning sâu kép chọn cặp toán tử destroy-and-repair tối ưu để phá vỡ các điểm chững của quỹ đạo tìm kiếm.',
    'pipeline.s4.title': 'Hội Tụ Cực Trị',
    'pipeline.s4.body': 'Tối ưu hóa tìm kiếm cục bộ và lập công thức Set Partitioning để tái tổ hợp các tuyến đường tốt nhất thành kế hoạch lộ trình khả thi.',

    'stats.instances': 'Bộ dữ liệu Solomon & Homberger được thử nghiệm',
    'stats.seeds': 'Các hạt giống độc lập (khởi động lạnh)',
    'stats.wilcoxon': 'Trong 5 trên 6 phép so sánh quy mô',
    'stats.overhead': 'Phụ phí tính toán so với ALNS-Base',

    'features.eyebrow': 'Kiến trúc Engine',
    'features.title': 'Thiết kế cho Ràng buộc Khó',
    'features.f1.title': 'Bộ điều khiển chững DDQN',
    'features.f1.bullet1': 'Prioritized Experience Replay (PER) với beta-annealing',
    'features.f1.bullet2': 'Chuẩn hóa phần thưởng Welford để tối ưu hóa đào tạo',
    'features.f1.bullet3': 'Tự động chuyển đổi chế độ tìm kiếm khi bị chững',
    'features.f2.title': 'Engine Tìm kiếm Thích ứng',
    'features.f2.bullet1': '8 toán tử hủy (destroy) và 5 toán tử chèn (insert)',
    'features.f2.bullet2': 'Chính sách lựa chọn toán tử dựa trên Thompson-bandit',
    'features.f2.bullet3': 'Các thuật toán tìm kiếm cục bộ chi tiết',
    'features.f3.title': 'Tiêu chuẩn Chấp nhận Học máy (LAC)',
    'features.f3.bullet1': 'Mạng nơ-ron phân loại chấp nhận phương án',
    'features.f3.bullet2': 'Thay thế lược đồ luyện kim mô phỏng truyền thống',
    'features.f3.bullet3': 'Thích ứng với đặc tính quỹ đạo tìm kiếm hiện tại',
    'features.f5.title': 'Tái tổ hợp Tuyến đường Set-Partitioning MILP',
    'features.f5.bullet1': 'Trích xuất tuyến đường con trong suốt quỹ đạo tìm kiếm',
    'features.f5.bullet2': 'Tái tổ hợp toàn cục qua quy hoạch nguyên hỗn hợp',
    'features.f5.bullet3': 'Đảm bảo cấu trúc tối ưu của các tuyến đường con tốt nhất',

    'results.eyebrow': 'Xác thực Khoa học',
    'results.title': 'Kết quả Benchmark Solomon & Homberger',
    'table.th.instance': 'Bộ dữ liệu / Họ',
    'table.th.scale': 'Quy mô',
    'table.th.bks': 'BKS (Số xe / TD)',
    'table.th.nami': 'NAMI Hybrid (Số xe / TD)',
    'table.th.alns': 'ALNS Baseline (Số xe / TD)',
    'table.th.wilcoxon': 'Giá trị p Wilcoxon',
    'table.group.100': 'Bộ dữ liệu 100 khách hàng (Solomon Benchmarks)',
    'table.group.200': 'Bộ dữ liệu 200 khách hàng (Gehring-Homberger Benchmarks)',
    'table.group.400': 'Bộ dữ liệu 400 khách hàng (Gehring-Homberger Benchmarks)',
    'table.summary': 'Tóm tắt: NAMI Hybrid-DDQN đạt số lượng xe tối thiểu của BKS ở quy mô 100/200 và giúp giảm số xe có ý nghĩa thống kê (p < 0.05) ở quy mô 400.',
    'results.footnote.dagger': '† Phép so sánh quãng đường (TD) bị loại trừ khi số lượng xe (NV) không khớp nhau, vì việc thừa năng lực vận tải sẽ bóp méo nhân tạo quãng đường di chuyển.',
    'results.footnote.coldstart': 'Lưu ý: Kết quả trình giải độc lập được tạo ra dưới điều kiện khởi động lạnh độc lập nghiêm ngặt từ build_greedy trong thư mục trống.',
    'results.footnote.wilcoxon': '* Sự khác biệt có ý nghĩa thống kê giữa NAMI Hybrid và ALNS Baseline (kiểm định Wilcoxon signed-rank p < 0.05).',
    'results.citation.title': 'Học Tăng Cường Sâu Plateau-Aware cho Bài Toán Tìm Kiếm Tổ Hợp',
    'results.citation.body': 'Nghiên cứu luận văn của chúng tôi phân tích các toán tử thoát khỏi cực trị cục bộ do DQN hướng dẫn dưới các trạng thái chững lại nghiêm trọng, vượt trội hơn các biến thể ALNS tĩnh truyền thống trong 7 trên 8 kịch bản thử nghiệm.',

    'getstarted.eyebrow': 'Khởi động nhanh cho Dev',
    'getstarted.title': 'Chạy cục bộ engine',
    'cli.explorer': 'THƯ MỤC'
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

  const tickerEpochEl = document.getElementById('ticker-epoch');
  const tickerCostEl = document.getElementById('ticker-cost');
  const tickerPlateauBar = document.getElementById('ticker-plateau-bar');
  const tickerPlateauVal = document.getElementById('ticker-plateau-val');

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

  let plateauLevel = 0;

  function triggerPlateauFlash() {
    if (!tickerPlateauBar) return;
    tickerPlateauBar.classList.add('flash');
    setTimeout(() => {
      tickerPlateauBar.classList.remove('flash');
    }, 400);
  }



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

    // 1. Draw coordinate axes bounding box & corners labels
    ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.05)';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    const c00 = isoProject(0, 0, cw, ch);
    const c10 = isoProject(1, 0, cw, ch);
    const c11 = isoProject(1, 1, cw, ch);
    const c01 = isoProject(0, 1, cw, ch);
    ctx.moveTo(c00.x, c00.y);
    ctx.lineTo(c10.x, c10.y);
    ctx.lineTo(c11.x, c11.y);
    ctx.lineTo(c01.x, c01.y);
    ctx.closePath();
    ctx.stroke();

    ctx.fillStyle = isDark ? 'rgba(255, 255, 255, 0.28)' : 'rgba(0, 0, 0, 0.35)';
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.fillText('(0, 100)', c00.x - 42, c00.y);
    ctx.fillText('(100, 100)', c10.x + 8, c10.y);
    ctx.fillText('(100, 0)', c11.x + 8, c11.y + 8);
    ctx.fillText('(0, 0)', c01.x - 32, c01.y + 8);

    // 2. Draw cluster bounding circles/ellipses
    ctx.strokeStyle = isDark ? 'rgba(122, 115, 255, 0.03)' : 'rgba(99, 91, 255, 0.06)';
    ctx.lineWidth = 0.7;
    ctx.setLineDash([2, 4]);
    clusters.forEach((c, idx) => {
      const center = isoProject(c.cx, c.cy, cw, ch);
      ctx.beginPath();
      ctx.ellipse(center.x, center.y, 45, 22, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = isDark ? 'rgba(255, 255, 255, 0.14)' : 'rgba(0, 0, 0, 0.18)';
      ctx.font = '7px "JetBrains Mono", monospace';
      ctx.fillText(`CLUSTER_0${idx + 1}`, center.x - 20, center.y - 10);
    });
    ctx.setLineDash([]);

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

        plateauLevel = 0;
        triggerPlateauFlash();

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

    // Stagnation Plateau logic
    if (frameCount % 4 === 0) {
      plateauLevel += 0.5;
      if (plateauLevel > 100) {
        plateauLevel = 0;
        triggerPlateauFlash();
      }
    }

    if (tickerEpochEl) tickerEpochEl.textContent = epoch;
    if (tickerCostEl) tickerCostEl.textContent = currentCost.toFixed(1);
    if (tickerPlateauBar) tickerPlateauBar.style.width = `${plateauLevel}%`;
    if (tickerPlateauVal) tickerPlateauVal.textContent = `${Math.round(plateauLevel)}%`;

    requestAnimationFrame(draw);
  }

  resize();
  draw();
  window.addEventListener('resize', resize);
}
