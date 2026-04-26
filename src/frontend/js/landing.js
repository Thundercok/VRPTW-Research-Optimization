/* VRPTW Research Optimization - landing page interactions
   - Theme toggle (light/dark) with localStorage persistence
   - i18n EN/VN with localStorage persistence
   - Smooth scroll-spy for active nav highlighting
   - Mobile menu toggle
*/
(function () {
  'use strict';

  const STORAGE_THEME = 'vrptw_landing_theme';
  const STORAGE_LANG = 'vrptw_landing_lang';

  const i18n = {
    en: {
      'brand.sub': 'Research Optimization',
      'nav.about': 'About',
      'nav.features': 'Features',
      'nav.algorithm': 'Algorithm',
      'nav.results': 'Results',
      'nav.tech': 'Tech Stack',
      'nav.getstarted': 'Get Started',
      'cta.demo': 'Open Demo',

      'hero.badge': 'Open-source research',
      'hero.title.line1': 'A Plateau-Aware',
      'hero.title.line2': 'Deep RL Controller',
      'hero.title.line3': 'for VRPTW',
      'hero.lead':
        'DDQN-ALNS hybrid solver that learns when to escape local optima. Compare it side-by-side with classic ALNS on Solomon RC1/RC2 benchmarks - directly in your browser.',
      'hero.cta.try': 'Try Live Demo',
      'hero.cta.github': 'View on GitHub',
      'hero.stat1.value': '2.6%',
      'hero.stat1.label': 'Avg. gap vs. best-known',
      'hero.stat2.value': '~10s',
      'hero.stat2.label': 'Median runtime per instance',
      'hero.stat3.value': 'RC1 -> RC2',
      'hero.stat3.label': 'Zero-shot transfer',

      'about.eyebrow': 'About the project',
      'about.title': 'Why this project exists',
      'about.lead':
        'Vehicle routing with time windows is hard: the search space is combinatorial, real fleets must respect customer service intervals, and pure heuristics often plateau. We combine reinforcement learning with adaptive large neighborhood search to learn smarter restarts - then ship it as a transparent web demo so anyone can poke at it.',
      'about.card1.title': 'Reproducible research',
      'about.card1.body':
        'Single Python file (vrptw_clean.py) holds the entire solver. Pre-trained weights ship in the repo; benchmark CSVs are committed for full traceability.',
      'about.card2.title': 'Real solver in the demo',
      'about.card2.body':
        'The web app runs the same PlateauHybridSolver and ALNS baseline - no mock. Side-by-side routes, runtimes, and load-balancing metrics.',
      'about.card3.title': 'Operator-friendly UX',
      'about.card3.body':
        'Import customers from CSV/Excel, drop pins on a Leaflet map, edit time windows inline, run the model, export results.',

      'features.eyebrow': 'Features',
      'features.title': 'What you can do today',
      'features.f1.title': 'DDQN-ALNS hybrid',
      'features.f1.body':
        'A Double DQN agent learns which destroy operator to fire when the search plateaus, while ALNS handles the repair step.',
      'features.f2.title': 'Solomon benchmarks',
      'features.f2.body':
        'RC1 and RC2 instances load with one click. Capacity, fleet size, and time windows auto-populate.',
      'features.f3.title': 'Real-data import',
      'features.f3.body':
        'Upload CSV/XLSX with lat, lng, demand, ready, due, service. Or geocode addresses and pin on the map.',
      'features.f4.title': 'Side-by-side compare',
      'features.f4.body':
        'DDQN-ALNS vs. plain ALNS run in parallel. Watch route maps, runtime, total distance, and load balance.',
      'features.f5.title': 'Zero-shot transfer',
      'features.f5.body':
        'Train on RC1, evaluate on RC2 without retraining. The plateau-aware reward generalizes across instance families.',
      'features.f6.title': 'Guest mode demo',
      'features.f6.body':
        'No Firebase keys? No problem. The backend boots in demo mode and the front-end exposes a one-click guest login.',

      'algorithm.eyebrow': 'Algorithm',
      'algorithm.title': 'Plateau-aware reinforcement learning',
      'algorithm.body1':
        'The controller observes the search trajectory: best-so-far, current-cost, and a plateau counter. When stagnation is detected, the DDQN policy chooses an aggressive destroy operator; otherwise it sticks with safer moves. Repair is delegated to a Numba-accelerated ALNS routine.',
      'algorithm.body2':
        'Reward is shaped to reward both immediate cost reduction and long-term escape behaviour, which is what the paper calls "plateau-aware" credit assignment.',
      'algorithm.list1.k': 'Action space:',
      'algorithm.list1.v': '5 destroy operators (random, worst, related, route, cluster)',
      'algorithm.list2.k': 'State:',
      'algorithm.list2.v': 'normalized gap, plateau counter, capacity utilisation, time-window slack',
      'algorithm.list3.k': 'Network:',
      'algorithm.list3.v': '2-layer MLP, target net synced every 200 steps',
      'algorithm.list4.k': 'Repair:',
      'algorithm.list4.v': 'regret-2 insertion with TW feasibility check',

      'results.eyebrow': 'Results',
      'results.title': 'Benchmark snapshot',
      'results.r1': 'Avg. total-distance gap on RC1',
      'results.r2': 'Zero-shot gap on RC2',
      'results.r3': 'Median runtime per 100-customer instance',
      'results.r4': 'Runtime vs. naive ALNS at equal quality',
      'results.note':
        'See logs/benchmark_clean.csv and logs/benchmark_transfer.csv in the repository for the raw numbers.',

      'tech.eyebrow': 'Tech stack',
      'tech.title': 'Built with proven open-source tools',

      'getstarted.eyebrow': 'Get started',
      'getstarted.title': 'Run it locally in under 2 minutes',
      'getstarted.s1.title': 'Clone & enter',
      'getstarted.s1.body': 'Pull the repo, then move into the project root.',
      'getstarted.s2.title': 'Install with uv or pip',
      'getstarted.s2.body': 'uv venv with Python 3.12, then install requirements.',
      'getstarted.s3.title': 'Optional - fetch Solomon',
      'getstarted.s3.body': 'Run scripts/fetch_solomon.py to download RC1+RC2 benchmark instances.',
      'getstarted.s4.title': 'Launch',
      'getstarted.s4.body': 'python main.py boots FastAPI on 127.0.0.1:8000. The demo loads in your browser.',

      'footer.col.product': 'Product',
      'footer.col.research': 'Research',
      'footer.col.contact': 'Contact',
      'footer.blurb':
        'DDQN-ALNS hybrid solver for the Vehicle Routing Problem with Time Windows. Open-source research project.',
      'footer.paper': 'Paper draft',
      'footer.benchmarks': 'Benchmarks',
      'footer.copyright': '© 2026 VRPTW Research Optimization. Released under the MIT License.'
    },
    vn: {
      'brand.sub': 'Nghiên cứu tối ưu hóa',
      'nav.about': 'Giới thiệu',
      'nav.features': 'Tính năng',
      'nav.algorithm': 'Thuật toán',
      'nav.results': 'Kết quả',
      'nav.tech': 'Công nghệ',
      'nav.getstarted': 'Bắt đầu',
      'cta.demo': 'Vào Demo',

      'hero.badge': 'Dự án nghiên cứu mã nguồn mở',
      'hero.title.line1': 'Bộ điều khiển',
      'hero.title.line2': 'Deep RL nhận diện plateau',
      'hero.title.line3': 'cho bài toán VRPTW',
      'hero.lead':
        'Solver lai DDQN-ALNS biết khi nào cần thoát khỏi cực trị địa phương. So sánh trực tiếp với ALNS truyền thống trên bộ benchmark Solomon RC1/RC2 - ngay trên trình duyệt của bạn.',
      'hero.cta.try': 'Thử Demo',
      'hero.cta.github': 'Xem trên GitHub',
      'hero.stat1.value': '2.6%',
      'hero.stat1.label': 'Khoảng cách trung bình so với best-known',
      'hero.stat2.value': '~10 giây',
      'hero.stat2.label': 'Thời gian chạy trung vị mỗi instance',
      'hero.stat3.value': 'RC1 -> RC2',
      'hero.stat3.label': 'Zero-shot transfer',

      'about.eyebrow': 'Giới thiệu dự án',
      'about.title': 'Tại sao dự án tồn tại',
      'about.lead':
        'VRPTW khó vì không gian tìm kiếm tổ hợp khổng lồ, đội xe thực tế phải tôn trọng khung giờ phục vụ và heuristic thuần thường mắc kẹt ở cực trị. Chúng tôi kết hợp học tăng cường với ALNS để học cách tái khởi tạo thông minh hơn - sau đó đóng gói thành một web demo minh bạch để bất kỳ ai cũng có thể thử nghiệm.',
      'about.card1.title': 'Nghiên cứu có thể tái lập',
      'about.card1.body':
        'Toàn bộ solver nằm gọn trong một file Python (vrptw_clean.py). Trọng số đã train, log benchmark đều được commit để tiện kiểm chứng.',
      'about.card2.title': 'Solver thật trong demo',
      'about.card2.body':
        'Web app chạy đúng PlateauHybridSolver và ALNS baseline - không mock. So sánh tuyến, runtime, mức cân bằng tải song song.',
      'about.card3.title': 'UX thân thiện với người vận hành',
      'about.card3.body':
        'Import khách hàng từ CSV/Excel, thả pin trên bản đồ Leaflet, sửa khung giờ inline, chạy mô hình, xuất kết quả.',

      'features.eyebrow': 'Tính năng',
      'features.title': 'Hôm nay bạn có thể làm gì',
      'features.f1.title': 'Hybrid DDQN-ALNS',
      'features.f1.body':
        'Agent Double DQN học cách chọn destroy operator phù hợp khi quá trình tìm kiếm chững lại; ALNS đảm nhiệm bước repair.',
      'features.f2.title': 'Benchmark Solomon',
      'features.f2.body':
        'Tải RC1, RC2 chỉ với một click. Tự điền sức chứa, số xe và khung giờ.',
      'features.f3.title': 'Nhập dữ liệu thật',
      'features.f3.body':
        'Upload CSV/XLSX kèm lat, lng, demand, ready, due, service. Hoặc geocode địa chỉ và thả pin.',
      'features.f4.title': 'So sánh song song',
      'features.f4.body':
        'DDQN-ALNS và ALNS thuần chạy song song. Quan sát bản đồ tuyến, runtime, tổng quãng đường, độ cân bằng tải.',
      'features.f5.title': 'Zero-shot transfer',
      'features.f5.body':
        'Train trên RC1, chạy thẳng RC2 mà không cần train lại. Hàm thưởng plateau-aware giúp model tổng quát hóa giữa các họ instance.',
      'features.f6.title': 'Demo chế độ khách',
      'features.f6.body':
        'Không có Firebase key cũng không sao. Backend chạy demo mode, frontend có nút "Continue as Guest" một click là vào.',

      'algorithm.eyebrow': 'Thuật toán',
      'algorithm.title': 'Học tăng cường nhận diện plateau',
      'algorithm.body1':
        'Bộ điều khiển quan sát quỹ đạo tìm kiếm: best-so-far, chi phí hiện tại và bộ đếm plateau. Khi phát hiện chững lại, policy DDQN chọn destroy mạnh; ngược lại giữ những bước an toàn. Bước repair giao cho ALNS được tăng tốc bằng Numba.',
      'algorithm.body2':
        'Hàm thưởng được thiết kế để khuyến khích cả việc giảm chi phí tức thời lẫn hành vi thoát cực trị dài hạn - đó là cái mà bài báo gọi là gán tín chỉ "plateau-aware".',
      'algorithm.list1.k': 'Action space:',
      'algorithm.list1.v': '5 toán tử destroy (random, worst, related, route, cluster)',
      'algorithm.list2.k': 'State:',
      'algorithm.list2.v': 'gap chuẩn hóa, bộ đếm plateau, tỉ lệ tải, slack khung giờ',
      'algorithm.list3.k': 'Mạng:',
      'algorithm.list3.v': 'MLP 2 lớp, target net đồng bộ mỗi 200 bước',
      'algorithm.list4.k': 'Repair:',
      'algorithm.list4.v': 'regret-2 insertion kèm kiểm tra feasibility khung giờ',

      'results.eyebrow': 'Kết quả',
      'results.title': 'Bức tranh benchmark',
      'results.r1': 'Gap tổng quãng đường trung bình trên RC1',
      'results.r2': 'Gap zero-shot trên RC2',
      'results.r3': 'Runtime trung vị cho instance 100 khách',
      'results.r4': 'Runtime so với ALNS cơ bản ở cùng chất lượng',
      'results.note':
        'Số liệu thô có trong logs/benchmark_clean.csv và logs/benchmark_transfer.csv của repo.',

      'tech.eyebrow': 'Công nghệ',
      'tech.title': 'Xây dựng trên các công cụ mã nguồn mở đã được kiểm chứng',

      'getstarted.eyebrow': 'Bắt đầu',
      'getstarted.title': 'Chạy local trong dưới 2 phút',
      'getstarted.s1.title': 'Clone & vào dự án',
      'getstarted.s1.body': 'Clone repo, sau đó cd vào thư mục gốc.',
      'getstarted.s2.title': 'Cài đặt với uv hoặc pip',
      'getstarted.s2.body': 'uv venv với Python 3.12, sau đó cài requirements.',
      'getstarted.s3.title': 'Tùy chọn - tải Solomon',
      'getstarted.s3.body': 'Chạy scripts/fetch_solomon.py để tải RC1+RC2.',
      'getstarted.s4.title': 'Khởi động',
      'getstarted.s4.body': 'python main.py bật FastAPI tại 127.0.0.1:8000. Demo mở ngay trong trình duyệt.',

      'footer.col.product': 'Sản phẩm',
      'footer.col.research': 'Nghiên cứu',
      'footer.col.contact': 'Liên hệ',
      'footer.blurb':
        'Solver lai DDQN-ALNS cho bài toán Định tuyến phương tiện có khung giờ. Dự án nghiên cứu mã nguồn mở.',
      'footer.paper': 'Bản nháp paper',
      'footer.benchmarks': 'Benchmarks',
      'footer.copyright': '© 2026 VRPTW Research Optimization. Phát hành theo giấy phép MIT.'
    }
  };

  function getStoredLang() {
    const v = localStorage.getItem(STORAGE_LANG);
    if (v === 'en' || v === 'vn') return v;
    const navLang = (navigator.language || '').toLowerCase();
    if (navLang.startsWith('vi')) return 'vn';
    return 'en';
  }

  function getStoredTheme() {
    const v = localStorage.getItem(STORAGE_THEME);
    if (v === 'light' || v === 'dark') return v;
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
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

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_THEME, theme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#0b1220' : '#ffffff');
  }

  function setupToggles() {
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

    themeBtn?.addEventListener('click', () => {
      currentTheme = currentTheme === 'light' ? 'dark' : 'light';
      applyTheme(currentTheme);
    });
  }

  function setupMobileMenu() {
    const btn = document.getElementById('mobile-menu-btn');
    const menu = document.getElementById('mobile-menu');
    if (!btn || !menu) return;
    btn.addEventListener('click', () => {
      const isOpen = menu.classList.toggle('open');
      menu.hidden = !isOpen;
    });
    menu.querySelectorAll('a').forEach((a) =>
      a.addEventListener('click', () => {
        menu.classList.remove('open');
        menu.hidden = true;
      })
    );
  }

  function setupScrollSpy() {
    const navLinks = Array.from(document.querySelectorAll('.topnav a'));
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

  document.addEventListener('DOMContentLoaded', () => {
    setupToggles();
    setupMobileMenu();
    setupScrollSpy();
  });
})();
