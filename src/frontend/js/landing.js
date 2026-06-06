/* ===================================================================
   NAMI Landing Page Script - Story-Driven Scroll Animations & Utils
   =================================================================== */

/* global gsap, ScrollTrigger */

(function () {
  'use strict';

  const STORAGE_THEME = 'vrptw_landing_theme';
  const STORAGE_LANG = 'vrptw_landing_lang';

  // Localization Dictionary
  const i18n = {
    en: {
      'brand.sub': 'Research Optimization',
      'nav.demo': 'Interactive Demo',
      'nav.features': 'Features',
      'nav.results': 'Benchmarks',
      'nav.getstarted': 'Setup',
      'cta.demo': 'Open Planner',

      'act1.title': "What's the fastest way to deliver to 100 addresses?",
      'act1.desc':
        'A single vehicle on a simple route is easy. But scaling delivery operations exposes exponential complexity.',
      'act2.title': 'A single route quickly shatters.',
      'act2.desc':
        'Every address introduces narrow time windows, load capacity limits, service times, and vehicle constraints. Classical heuristics easily stagnate in sub-optimal local basins.',
      'act3.title': "NAMI's neural controller takes over.",
      'act3.desc':
        'A Double Deep Q-Network (DDQN) agent analyzes the search trajectory in real-time, intelligently selecting destroy-and-repair ALNS operators to break stagnation patterns.',
      'act4.title': 'Optimal dispatch. Delivered.',
      'act4.desc':
        'Feasible, balanced paths are generated in milliseconds. Dispatchers receive clean, conflict-free delivery plans verified against all Solomon criteria.',

      'features.eyebrow': 'Engine Architecture',
      'features.title': 'Engineered for Hard Constraints',
      'features.f1.title': 'DDQN Operator Selection',
      'features.f1.body':
        'A Double DQN agent observes the search trajectory and learns which destroy operators (Random, Worst, Cluster) to fire when search basins stagnate.',
      'features.f2.title': 'Time-Window Feasibility',
      'features.f2.body':
        'Supports strict time windows (ready time, due date, service duration) with dynamic early-arrival waiting and late-arrival filtering.',
      'features.f3.title': 'Solomon Benchmarks',
      'features.f3.body':
        'Built-in, one-click loading of Solomon benchmark instances (C, R, RC families) for rapid performance verification.',
      'features.f5.title': 'Zero-Shot Transfer',
      'features.f5.body':
        'The trained plateau-aware RL policy transfers directly across different Solomon families (e.g. trained on RC1, evaluated on RC2) without retraining.',

      'results.eyebrow': 'Scientific Validation',
      'results.title': 'Solomon Benchmark Results',
      'getstarted.eyebrow': 'Developer Quickstart',
      'getstarted.title': 'Run the engine locally in 60s',
    },
    vn: {
      'brand.sub': 'Tối ưu hóa Nghiên cứu',
      'nav.demo': 'Demo Trực quan',
      'nav.features': 'Tính năng',
      'nav.results': 'Benchmarks',
      'nav.getstarted': 'Cài đặt',
      'cta.demo': 'Mở Planner',

      'act1.title': 'Đâu là cách nhanh nhất để giao tới 100 địa chỉ?',
      'act1.desc':
        'Một phương tiện trên một lộ trình đơn giản thì dễ dàng. Nhưng việc mở rộng hoạt động giao hàng sẽ tạo ra độ phức tạp theo cấp số nhân.',
      'act2.title': 'Lộ trình nhanh chóng bị phá vỡ.',
      'act2.desc':
        'Mỗi địa chỉ đi kèm với các khung giờ nghiêm ngặt, giới hạn tải trọng, thời gian phục vụ và các ràng buộc xe. Các heuristic cổ điển rất dễ mắc kẹt ở cực trị địa phương kém tối ưu.',
      'act3.title': 'Bộ điều khiển nơ-ron NAMI tiếp quản.',
      'act3.desc':
        'Agent Double Deep Q-Network (DDQN) phân tích quỹ đạo tìm kiếm theo thời gian thực, lựa chọn thông minh các toán tử destroy-and-repair ALNS để phá vỡ các điểm nghẽn chững lại.',
      'act4.title': 'Điều phối tối ưu. Đã hoàn thành.',
      'act4.desc':
        'Các lộ trình khả thi, cân bằng được tạo ra trong vài mili giây. Người điều phối nhận được kế hoạch giao hàng rõ ràng, không có xung đột, được xác thực theo tất cả các tiêu chí Solomon.',

      'features.eyebrow': 'Kiến trúc Engine',
      'features.title': 'Thiết kế cho Ràng buộc Khó',
      'features.f1.title': 'Chọn toán tử bằng DDQN',
      'features.f1.body':
        'Agent Double DQN quan sát quỹ đạo tìm kiếm và học cách kích hoạt các toán tử destroy phù hợp (Random, Worst, Cluster) khi không gian tìm kiếm bị chững lại.',
      'features.f2.title': 'Độ khả thi Khung giờ',
      'features.f2.body':
        'Hỗ trợ khung giờ nghiêm ngặt (ready time, due date, service duration) kèm tự động chờ nếu đến sớm và lọc nếu đến muộn.',
      'features.f3.title': 'Benchmark Solomon',
      'features.f3.body':
        'Tích hợp sẵn các bộ benchmark Solomon (họ C, R, RC) để tải nhanh chỉ với một click giúp kiểm chứng thuật toán.',
      'features.f5.title': 'Zero-Shot Transfer',
      'features.f5.body':
        'Policy RL nhận diện plateau sau khi huấn luyện có thể chuyển giao trực tiếp sang các họ Solomon khác (ví dụ: huấn luyện trên RC1, chạy thử trên RC2) mà không cần train lại.',

      'results.eyebrow': 'Xác thực Khoa học',
      'results.title': 'Kết quả Benchmark Solomon',
      'getstarted.eyebrow': 'Khởi động nhanh cho Dev',
      'getstarted.title': 'Chạy cục bộ engine trong 60 giây',
    },
  };

  // Node and Path Coordinates Setup for Canvas
  const DEPOT = { x: 150, y: 300 };

  const CUSTOMER_NODES = [
    // Cluster 1 (Top Right) - Ordered for a beautiful non-overlapping loop path
    { id: 1, x: 450, y: 150, targetColor: '#10b981', cluster: 1 }, // Emerald Route
    { id: 2, x: 500, y: 200, targetColor: '#10b981', cluster: 1 },
    { id: 3, x: 550, y: 250, targetColor: '#10b981', cluster: 1 },
    { id: 4, x: 600, y: 200, targetColor: '#10b981', cluster: 1 },
    { id: 5, x: 650, y: 150, targetColor: '#10b981', cluster: 1 },
    { id: 6, x: 600, y: 100, targetColor: '#10b981', cluster: 1 },
    { id: 7, x: 550, y: 150, targetColor: '#10b981', cluster: 1 },

    // Cluster 2 (Bottom Right) - Ordered for a beautiful non-overlapping loop path
    { id: 8, x: 600, y: 350, targetColor: '#3b82f6', cluster: 2 }, // Blue Route
    { id: 9, x: 650, y: 400, targetColor: '#3b82f6', cluster: 2 },
    { id: 10, x: 700, y: 450, targetColor: '#3b82f6', cluster: 2 },
    { id: 11, x: 650, y: 500, targetColor: '#3b82f6', cluster: 2 },
    { id: 12, x: 550, y: 500, targetColor: '#3b82f6', cluster: 2 },
    { id: 13, x: 600, y: 450, targetColor: '#3b82f6', cluster: 2 },
    { id: 14, x: 500, y: 450, targetColor: '#3b82f6', cluster: 2 },

    // Cluster 3 (Middle Right) - Ordered for a beautiful non-overlapping loop path
    { id: 15, x: 350, y: 300, targetColor: '#6366f1', cluster: 3 }, // Indigo Route
    { id: 16, x: 450, y: 250, targetColor: '#6366f1', cluster: 3 },
    { id: 17, x: 500, y: 300, targetColor: '#6366f1', cluster: 3 },
    { id: 18, x: 500, y: 350, targetColor: '#6366f1', cluster: 3 },
    { id: 19, x: 400, y: 350, targetColor: '#6366f1', cluster: 3 },
    { id: 20, x: 450, y: 300, targetColor: '#6366f1', cluster: 3 },

    // Scattered Random Group (Cluster 4) - Ordered for a beautiful non-overlapping loop path
    { id: 21, x: 200, y: 200, targetColor: '#8b5cf6', cluster: 4 }, // Purple Route
    { id: 22, x: 200, y: 100, targetColor: '#8b5cf6', cluster: 4 },
    { id: 23, x: 300, y: 100, targetColor: '#8b5cf6', cluster: 4 },
    { id: 24, x: 300, y: 150, targetColor: '#8b5cf6', cluster: 4 },
    { id: 25, x: 350, y: 200, targetColor: '#8b5cf6', cluster: 4 },
    { id: 26, x: 300, y: 400, targetColor: '#8b5cf6', cluster: 4 },
    { id: 27, x: 250, y: 500, targetColor: '#8b5cf6', cluster: 4 },
    { id: 28, x: 400, y: 500, targetColor: '#8b5cf6', cluster: 4 },
    { id: 29, x: 450, y: 450, targetColor: '#8b5cf6', cluster: 4 },
    { id: 30, x: 350, y: 450, targetColor: '#8b5cf6', cluster: 4 },
  ];

  // Map route configurations to coordinates
  const ROUTES = [
    {
      color: '#10b981', // Emerald
      nodes: [DEPOT, ...CUSTOMER_NODES.filter((n) => n.cluster === 1), DEPOT],
    },
    {
      color: '#3b82f6', // Blue
      nodes: [DEPOT, ...CUSTOMER_NODES.filter((n) => n.cluster === 2), DEPOT],
    },
    {
      color: '#6366f1', // Indigo
      nodes: [DEPOT, ...CUSTOMER_NODES.filter((n) => n.cluster === 3), DEPOT],
    },
    {
      color: '#8b5cf6', // Purple
      nodes: [DEPOT, ...CUSTOMER_NODES.filter((n) => n.cluster === 4), DEPOT],
    },
  ];

  // Helper: Linear Interpolation between two points
  function lerp(start, end, amt) {
    return (1 - amt) * start + amt * end;
  }

  // Helper: Get coordinate point along a sequence of coordinates at a given progress
  function getPointAtProgress(pathPoints, progress) {
    if (!pathPoints || pathPoints.length === 0) return { x: 0, y: 0 };
    if (progress <= 0) return pathPoints[0];
    if (progress >= 1) return pathPoints[pathPoints.length - 1];

    const totalSegments = pathPoints.length - 1;
    const rawSegment = progress * totalSegments;
    const index = Math.floor(rawSegment);
    const frac = rawSegment - index;

    const start = pathPoints[index];
    const end = pathPoints[index + 1];

    return {
      x: lerp(start.x, end.x, frac),
      y: lerp(start.y, end.y, frac),
    };
  }

  // Helper: Generate structured SVG paths for routes
  function buildPathD(points) {
    return points.reduce((d, p, i) => {
      return d + (i === 0 ? `M ${p.x} ${p.y}` : ` L ${p.x} ${p.y}`);
    }, '');
  }

  // Canvas elements creation
  const svgCanvas = document.getElementById('animation-canvas');
  const routeGroup = document.getElementById('route-paths-group');
  const nodesGroup = document.getElementById('nodes-group');
  const vehiclesGroup = document.getElementById('vehicles-group');

  let nodeElements = [];
  let haloElements = [];
  let routePathElements = [];
  let vehicleElements = [];
  let chaosLinesGroup = null;

  // Initialize Canvas DOM structures
  function initCanvas() {
    if (!svgCanvas) return;

    // Clear groupings
    routeGroup.innerHTML = '';
    nodesGroup.innerHTML = '';
    vehiclesGroup.innerHTML = '';

    nodeElements = [];
    haloElements = [];
    routePathElements = [];
    vehicleElements = [];

    // Create Depot Node
    const depotCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    depotCircle.setAttribute('cx', DEPOT.x);
    depotCircle.setAttribute('cy', DEPOT.y);
    depotCircle.setAttribute('r', 10);
    depotCircle.setAttribute('class', 'node-circle depot');
    nodesGroup.appendChild(depotCircle);

    // Create Customer Nodes (Neutral start state)
    CUSTOMER_NODES.forEach((node) => {
      // Create halo first (behind circle)
      const halo = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      halo.setAttribute('cx', node.x);
      halo.setAttribute('cy', node.y);
      halo.setAttribute('r', 4);
      halo.setAttribute('fill', 'none');
      halo.setAttribute('stroke', '#ef4444');
      halo.setAttribute('stroke-width', '2');
      halo.setAttribute('class', 'node-halo');
      halo.style.opacity = '0';
      nodesGroup.appendChild(halo);
      haloElements.push({ id: node.id, el: halo });

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', node.x);
      circle.setAttribute('cy', node.y);
      circle.setAttribute('r', 5);
      circle.setAttribute('class', 'node-circle customer');
      nodesGroup.appendChild(circle);
      nodeElements.push({ id: node.id, el: circle, originalX: node.x, originalY: node.y });
    });

    // Create Routes
    ROUTES.forEach((route, index) => {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', buildPathD(route.nodes));
      path.setAttribute('class', 'route-line solved');
      path.setAttribute('stroke', route.color);
      path.style.opacity = '0';
      routeGroup.appendChild(path);
      routePathElements.push({ index, el: path, color: route.color });

      // Create vehicle point indicator
      const vehicle = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      vehicle.setAttribute('points', '-6,-4 8,0 -6,4 -3,0');
      vehicle.setAttribute('class', 'vehicle-ptr');
      vehicle.style.opacity = '0';
      vehiclesGroup.appendChild(vehicle);
      vehicleElements.push({ index, el: vehicle, color: route.color });
    });

    // Create a group for chaotic problem state lines
    chaosLinesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    routeGroup.appendChild(chaosLinesGroup);
  }

  // Dynamic SVG Renderer based on progress
  function renderCanvas(act, progress) {
    if (!svgCanvas) return;

    // Theme adaptations
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const neutralNodeColor = isDark ? '#475569' : '#94a3b8';

    if (act === 1) {
      // Act I: Simple linear truck deliveries
      if (chaosLinesGroup) chaosLinesGroup.innerHTML = '';

      // Hide HUD panel
      const hud = document.getElementById('hud-panel');
      if (hud) hud.classList.remove('active');

      // Nodes are bunched up or hidden
      nodeElements.forEach((node) => {
        // Line up nodes along the horizontal axis in a line
        const targetX = lerp(DEPOT.x, 700, (node.id - 1) / CUSTOMER_NODES.length);
        node.el.setAttribute('cx', targetX);
        node.el.setAttribute('cy', DEPOT.y);
        node.el.setAttribute('r', 3);
        node.el.setAttribute('fill', neutralNodeColor);
        node.el.style.opacity = lerp(0.1, 0.4, progress);
      });

      // Clear halos
      haloElements.forEach((h) => (h.el.style.opacity = '0'));

      // Hide optimized routes
      routePathElements.forEach((r) => (r.el.style.opacity = '0'));

      // Run single vehicle along a straight line
      vehicleElements.forEach((v, idx) => {
        if (idx === 0) {
          v.el.style.opacity = '1';
          const pos = getPointAtProgress([DEPOT, { x: 700, y: DEPOT.y }], progress);
          v.el.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);
          v.el.setAttribute('fill', v.color);
        } else {
          v.el.style.opacity = '0';
        }
      });
    } else if (act === 2) {
      // Act II: Explosion into chaos
      const hud = document.getElementById('hud-panel');
      if (hud) hud.classList.remove('active');

      // Nodes explode to original coordinates
      nodeElements.forEach((node) => {
        const startX = lerp(DEPOT.x, 700, (node.id - 1) / CUSTOMER_NODES.length);
        const startY = DEPOT.y;

        const currentX = lerp(startX, node.originalX, progress);
        const currentY = lerp(startY, node.originalY, progress);

        node.el.setAttribute('cx', currentX);
        node.el.setAttribute('cy', currentY);
        node.el.setAttribute('r', lerp(3, 5, progress));
        node.el.setAttribute('fill', '#ef4444'); // Red alert nodes
        node.el.style.opacity = '1';
      });

      // Turn on red halos at half progress
      haloElements.forEach((h) => {
        h.el.setAttribute('cx', CUSTOMER_NODES.find((n) => n.id === h.id).x);
        h.el.setAttribute('cy', CUSTOMER_NODES.find((n) => n.id === h.id).y);
        h.el.style.opacity = progress > 0.5 ? '0.6' : '0';
      });

      // Draw random red chaotic lines crossing
      if (chaosLinesGroup && progress > 0.3) {
        chaosLinesGroup.innerHTML = '';
        for (let i = 0; i < 20; i++) {
          const n1 = CUSTOMER_NODES[Math.floor(lerp(0, CUSTOMER_NODES.length - 1, (i * 0.17) % 1))];
          const n2 = CUSTOMER_NODES[Math.floor(lerp(0, CUSTOMER_NODES.length - 1, (i * 0.37) % 1))];
          if (n1.id !== n2.id) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', n1.x);
            line.setAttribute('y1', n1.y);
            line.setAttribute('x2', n2.x);
            line.setAttribute('y2', n2.y);
            line.setAttribute('stroke', '#ef4444');
            line.setAttribute('stroke-width', '1');
            line.setAttribute('opacity', lerp(0, 0.35, progress));
            chaosLinesGroup.appendChild(line);
          }
        }
      }

      // Truck shakes at depot or center
      vehicleElements.forEach((v, idx) => {
        if (idx === 0) {
          v.el.style.opacity = '1';
          const shakeX = DEPOT.x + Math.sin(Date.now() * 0.05) * 3;
          const shakeY = DEPOT.y + Math.cos(Date.now() * 0.05) * 3;
          v.el.setAttribute('transform', `translate(${shakeX}, ${shakeY}) rotate(${shakeX * 5})`);
          v.el.setAttribute('fill', '#ef4444');
        } else {
          v.el.style.opacity = '0';
        }
      });

      // Hide optimized routes
      routePathElements.forEach((r) => (r.el.style.opacity = '0'));
    } else if (act === 3) {
      // Act III: Optimization (drawing routes, changing node states)
      if (chaosLinesGroup) chaosLinesGroup.innerHTML = '';

      const hud = document.getElementById('hud-panel');
      if (hud) hud.classList.remove('active');

      // Adjust nodes to cluster colors progressively
      nodeElements.forEach((node) => {
        node.el.setAttribute('cx', node.originalX);
        node.el.setAttribute('cy', node.originalY);
        node.el.setAttribute('r', 5.5);

        const targetNode = CUSTOMER_NODES.find((n) => n.id === node.id);
        const nodeColor =
          progress > 0.5 ? targetNode.targetColor : lerpColor('#ef4444', targetNode.targetColor, progress * 2);
        node.el.setAttribute('fill', nodeColor);
      });

      // Halos fade out
      haloElements.forEach((h) => (h.el.style.opacity = lerp(0.6, 0, progress)));

      // Draw optimized routes progressively using stroke dash offsets
      routePathElements.forEach((r) => {
        r.el.style.opacity = progress;
        const totalLength = r.el.getTotalLength() || 1500;
        r.el.setAttribute('stroke-dasharray', totalLength);
        r.el.setAttribute('stroke-dashoffset', totalLength * (1 - progress));
      });

      // Vehicles start tracing routes
      vehicleElements.forEach((v) => {
        v.el.style.opacity = progress > 0.4 ? '1' : '0';
        v.el.setAttribute('fill', v.color);
        const route = ROUTES[v.index];
        const pos = getPointAtProgress(
          route.nodes.map((n) => ({ x: n.x, y: n.y })),
          progress
        );
        v.el.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);
      });
    } else if (act === 4) {
      // Act IV: Completed Dashboard loop
      if (chaosLinesGroup) chaosLinesGroup.innerHTML = '';

      // Fade HUD panel in
      const hud = document.getElementById('hud-panel');
      if (hud) hud.classList.add('active');

      // Nodes locked in color groups
      nodeElements.forEach((node) => {
        node.el.setAttribute('cx', node.originalX);
        node.el.setAttribute('cy', node.originalY);
        node.el.setAttribute('r', 5.5);
        node.el.setAttribute('fill', CUSTOMER_NODES.find((n) => n.id === node.id).targetColor);
      });

      // Halos fully hidden
      haloElements.forEach((h) => (h.el.style.opacity = '0'));

      // Paths fully active
      routePathElements.forEach((r) => {
        r.el.style.opacity = '1';
        r.el.removeAttribute('stroke-dashoffset');
        r.el.removeAttribute('stroke-dasharray');
      });

      // Continuous loop of vehicles tracing routes
      const time = Date.now() * 0.00015;
      vehicleElements.forEach((v) => {
        v.el.style.opacity = '1';
        v.el.setAttribute('fill', v.color);
        const route = ROUTES[v.index];
        const loopProg = (time * (1.2 + v.index * 0.2)) % 1;
        const pos = getPointAtProgress(
          route.nodes.map((n) => ({ x: n.x, y: n.y })),
          loopProg
        );

        // Compute orientation angle for path following
        const nextPos = getPointAtProgress(
          route.nodes.map((n) => ({ x: n.x, y: n.y })),
          (loopProg + 0.01) % 1
        );
        const angle = Math.atan2(nextPos.y - pos.y, nextPos.x - pos.x) * (180 / Math.PI);

        v.el.setAttribute('transform', `translate(${pos.x}, ${pos.y}) rotate(${angle})`);
      });
    }
  }

  // Color blending helper for transitions
  function lerpColor(color1, color2, factor) {
    const clamp = Math.max(0, Math.min(1, factor));
    const c1 = parseHex(color1);
    const c2 = parseHex(color2);

    const r = Math.round(lerp(c1.r, c2.r, clamp));
    const g = Math.round(lerp(c1.g, c2.g, clamp));
    const b = Math.round(lerp(c1.b, c2.b, clamp));

    return `rgb(${r}, ${g}, ${b})`;
  }

  function parseHex(hex) {
    const clean = hex.replace('#', '');
    return {
      r: parseInt(clean.substring(0, 2), 16),
      g: parseInt(clean.substring(2, 4), 16),
      b: parseInt(clean.substring(4, 6), 16),
    };
  }

  // ===================================================================
  // GSAP ScrollTrigger Integration
  // ===================================================================

  function setupScrollAnimations() {
    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
      console.warn('GSAP or ScrollTrigger not loaded. Using fallback animation.');
      setupFallbackAnimation();
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    // Only run scroll timeline on desktop
    if (window.innerWidth < 1024) {
      setupFallbackAnimation();
      return;
    }

    initCanvas();

    // Timeline to scrub animation state
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: '.scroll-track',
        start: 'top top',
        end: 'bottom bottom',
        scrub: 1,
        onUpdate: (self) => {
          const progress = self.progress;

          // Divide timeline into 4 Acts
          let act = 1;
          let actProgress = 0;

          if (progress < 0.25) {
            act = 1;
            actProgress = progress / 0.25;
          } else if (progress < 0.5) {
            act = 2;
            actProgress = (progress - 0.25) / 0.25;
          } else if (progress < 0.75) {
            act = 3;
            actProgress = (progress - 0.5) / 0.25;
          } else {
            act = 4;
            actProgress = (progress - 0.75) / 0.25;
          }

          // Trigger Act Card active toggle
          toggleActiveCard(act);

          // Render canvas updates
          renderCanvas(act, actProgress);
        },
      },
    });
  }

  // Toggle active CSS class for text cards
  function toggleActiveCard(activeAct) {
    for (let act = 1; act <= 4; act++) {
      const card = document.getElementById(`card-act${act}`);
      if (card) {
        if (act === activeAct) {
          card.classList.add('active');
        } else {
          card.classList.remove('active');
        }
      }
    }
  }

  // Fallback animation: continuous loop for mobile/tablets or if GSAP fails
  let fallbackInterval = null;
  function setupFallbackAnimation() {
    if (fallbackInterval) clearInterval(fallbackInterval);

    initCanvas();
    toggleActiveCard(4); // Keep Act IV card active

    fallbackInterval = setInterval(() => {
      renderCanvas(4, 1.0); // Keep rendering loop in Act IV (routes resolved)
    }, 16);
  }

  // ===================================================================
  // Localization Settings
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
      if (dict[key]) {
        // Handle links, headings, paragraphs
        node.textContent = dict[key];
      }
    });

    const label = document.getElementById('lang-label');
    if (label) label.textContent = lang === 'vn' ? 'VN' : 'EN';
    localStorage.setItem(STORAGE_LANG, lang);
  }

  // ===================================================================
  // Theme Switching Settings
  // ===================================================================

  function getStoredTheme() {
    const v = localStorage.getItem(STORAGE_THEME);
    if (v === 'light' || v === 'dark') return v;
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_THEME, theme);

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#080d16' : '#ffffff');

    // Update icons visibility
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    if (sunIcon && moonIcon) {
      if (theme === 'dark') {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
      } else {
        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
      }
    }
  }

  // Setup control listeners
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

    themeBtn?.addEventListener('click', () => {
      currentTheme = currentTheme === 'light' ? 'dark' : 'light';
      applyTheme(currentTheme);
    });
  }

  // Setup Mobile hamburger menu
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

  // Highlight navigation links on scroll (Scrollspy)
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

  // Sticky Navbar shadow on scroll
  function setupNavbarScroll() {
    const nav = document.querySelector('.site-nav');
    if (!nav) return;
    window.addEventListener(
      'scroll',
      () => {
        nav.classList.toggle('is-scrolled', window.scrollY > 20);
      },
      { passive: true }
    );
  }

  // Initial Boot
  document.addEventListener('DOMContentLoaded', () => {
    setupControls();
    setupMobileMenu();
    setupScrollSpy();
    setupNavbarScroll();
    setupScrollAnimations();
  });

  // Handle resizing (re-initialize animations on desktop <-> mobile shifts)
  let resizeTimeout = null;
  window.addEventListener('resize', () => {
    if (resizeTimeout) clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      setupScrollAnimations();
    }, 250);
  });
})();
