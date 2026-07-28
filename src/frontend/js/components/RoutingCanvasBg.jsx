import React, { useEffect, useRef } from 'react';

export default function RoutingCanvasBg() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let w, h;
    let animationId;

    function resize() {
      w = canvas.width = canvas.offsetWidth * Math.min(devicePixelRatio, 2);
      h = canvas.height = canvas.offsetHeight * Math.min(devicePixelRatio, 2);
      ctx.resetTransform();
      ctx.scale(Math.min(devicePixelRatio, 2), Math.min(devicePixelRatio, 2));
    }

    const allNodes = [];
    allNodes.push({ x: 0.5, y: 0.5, type: 'depot', r: 4.5, label: 'DEPOT' });

    function seedRandom(i) {
      const x = Math.sin(i * 12345.678) * 10000;
      return x - Math.floor(x);
    }

    const clusters = [
      { cx: 0.2, cy: 0.25 },
      { cx: 0.8, cy: 0.22 },
      { cx: 0.22, cy: 0.75 },
      { cx: 0.78, cy: 0.72 },
      { cx: 0.5, cy: 0.48 },
    ];

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
        label: `C-${100 + i}`,
      });
    }

    function isoProject(x, y, cw, ch) {
      const cx = cw / 2;
      const cy = ch * 0.52;
      const scale = Math.max(cw, ch) * 1.1;
      const px = (x - 0.5) * scale;
      const py = (y - 0.5) * scale;
      const isoX = cx + (px - py) * 0.95;
      const isoY = cy + (px + py) * 0.46;
      return { x: isoX, y: isoY };
    }

    const clusterNodes = [[], [], [], [], []];
    for (let idx = 1; idx < allNodes.length; idx++) {
      const cIdx = (idx - 1) % 5;
      clusterNodes[cIdx].push(idx);
    }

    clusters.forEach((c, cIdx) => {
      clusterNodes[cIdx].sort((a, b) => {
        const angleA = Math.atan2(allNodes[a].y - c.cy, allNodes[a].x - c.cx);
        const angleB = Math.atan2(allNodes[b].y - c.cy, allNodes[b].x - c.cx);
        return angleA - angleB;
      });
    });

    const vehicles = [
      { id: 1, route: [0, ...clusterNodes[0].slice(0, 6), 0], speed: 0.0065, progress: 0, segment: 0, color: '#00d4ff', trail: [], rerouteActive: false, rerouteTime: 0, reroutePos: null },
      { id: 2, route: [0, ...clusterNodes[1].slice(0, 6), 0], speed: 0.0075, progress: 0.15, segment: 0, color: '#a855f7', trail: [], rerouteActive: false, rerouteTime: 0, reroutePos: null },
      { id: 3, route: [0, ...clusterNodes[2], 0], speed: 0.0055, progress: 0.3, segment: 0, color: '#ec4899', trail: [], rerouteActive: false, rerouteTime: 0, reroutePos: null },
      { id: 4, route: [0, ...clusterNodes[3], 0], speed: 0.007, progress: 0.45, segment: 0, color: '#f59e0b', trail: [], rerouteActive: false, rerouteTime: 0, reroutePos: null },
      { id: 5, route: [0, ...clusterNodes[4], 0], speed: 0.005, progress: 0.6, segment: 0, color: '#10b981', trail: [], rerouteActive: false, rerouteTime: 0, reroutePos: null },
      { id: 6, route: [0, ...clusterNodes[0].slice(6), 0], speed: 0.008, progress: 0.05, segment: 0, color: '#22c55e', trail: [], rerouteActive: false, rerouteTime: 0, reroutePos: null },
      { id: 7, route: [0, ...clusterNodes[1].slice(6), 0], speed: 0.006, progress: 0.25, segment: 0, color: '#0ea5e9', trail: [], rerouteActive: false, rerouteTime: 0, reroutePos: null },
    ];

    function catmullRom(p0, p1, p2, p3, t) {
      const t2 = t * t;
      const t3 = t2 * t;
      const x = 0.5 * (2 * p1.x + (-p0.x + p2.x) * t + (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 + (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3);
      const y = 0.5 * (2 * p1.y + (-p0.y + p2.y) * t + (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 + (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3);
      return { x, y };
    }

    function getWaypoint(route, idx) {
      const len = route.length;
      const i = (idx + len) % len;
      return allNodes[route[i]];
    }

    const costParticles = [];

    function draw() {
      const cw = canvas.offsetWidth;
      const ch = canvas.offsetHeight;
      if (cw === 0 || ch === 0) {
        animationId = requestAnimationFrame(draw);
        return;
      }

      ctx.clearRect(0, 0, cw, ch);
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

      const vehColors = {
        '#00d4ff': isDark ? '#38bdf8' : '#0284c7',
        '#a855f7': isDark ? '#7dd3fc' : '#0369a1',
        '#ec4899': isDark ? '#fb923c' : '#ea580c',
        '#f59e0b': isDark ? '#fbbf24' : '#d97706',
        '#10b981': isDark ? '#60a5fa' : '#3b82f6',
        '#22c55e': isDark ? '#34d399' : '#059669',
        '#0ea5e9': isDark ? '#a78bfa' : '#7c3aed',
      };

      const colors = {
        grid: isDark ? 'rgba(56, 189, 248, 0.05)' : 'rgba(2, 132, 199, 0.05)',
        depot: isDark ? '#38bdf8' : '#0284c7',
        depotGlow: isDark ? 'rgba(56, 189, 248, 0.14)' : 'rgba(2, 132, 199, 0.14)',
        clientStroke: isDark ? 'rgba(148, 163, 184, 0.7)' : 'rgba(71, 85, 105, 0.55)',
        clientFill: isDark ? 'rgba(56, 189, 248, 0.06)' : 'rgba(2, 132, 199, 0.05)',
        nodeCore: isDark ? '#020617' : '#ffffff',
      };

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

      ctx.strokeStyle = isDark ? 'rgba(122, 115, 255, 0.03)' : 'rgba(99, 91, 255, 0.06)';
      ctx.lineWidth = 0.7;
      ctx.setLineDash([2, 4]);
      clusters.forEach((c, idx) => {
        const center = isoProject(c.cx, c.cy, cw, ch);
        ctx.beginPath();
        ctx.ellipse(center.x, center.y, 45, 22, 0, 0, Math.PI * 2);
        ctx.stroke();
      });
      ctx.setLineDash([]);

      vehicles.forEach((veh) => {
        const drawColor = vehColors[veh.color] || veh.color;
        let rgbaColor = 'rgba(122, 115, 255, 0.08)';
        if (drawColor.startsWith('#')) {
          const r = parseInt(drawColor.slice(1, 3), 16);
          const g = parseInt(drawColor.slice(3, 5), 16);
          const b = parseInt(drawColor.slice(5, 7), 16);
          rgbaColor = `rgba(${r}, ${g}, ${b}, ${isDark ? 0.06 : 0.11})`;
        }

        ctx.strokeStyle = rgbaColor;
        ctx.lineWidth = 0.85;
        ctx.setLineDash([2, 4]);
        ctx.beginPath();
        const rLen = veh.route.length;
        for (let s = 0; s < rLen - 1; s++) {
          const w0 = getWaypoint(veh.route, s - 1);
          const w1 = getWaypoint(veh.route, s);
          const w2 = getWaypoint(veh.route, s + 1);
          const w3 = getWaypoint(veh.route, s + 2);
          for (let step = 0; step <= 20; step++) {
            const t = step / 20;
            const normPos = catmullRom(w0, w1, w2, w3, t);
            const pos = isoProject(normPos.x, normPos.y, cw, ch);
            if (s === 0 && step === 0) ctx.moveTo(pos.x, pos.y);
            else ctx.lineTo(pos.x, pos.y);
          }
        }
        ctx.stroke();
        ctx.setLineDash([]);
      });
      ctx.globalAlpha = 1.0;

      vehicles.forEach((veh) => {
        veh.progress += veh.speed;
        if (veh.progress >= 1.0) {
          veh.progress = 0;
          veh.segment = (veh.segment + 1) % veh.route.length;
        }

        const w0 = getWaypoint(veh.route, veh.segment - 1);
        const w1 = getWaypoint(veh.route, veh.segment);
        const w2 = getWaypoint(veh.route, veh.segment + 1);
        const w3 = getWaypoint(veh.route, veh.segment + 2);

        const normPos = catmullRom(w0, w1, w2, w3, veh.progress);
        const pos = isoProject(normPos.x, normPos.y, cw, ch);

        veh.trail.push({ x: pos.x, y: pos.y });
        if (veh.trail.length > 24) veh.trail.shift();

        const drawColor = vehColors[veh.color] || veh.color;
        const trailLen = veh.trail.length;
        if (trailLen > 1) {
          for (let k = 1; k < trailLen; k++) {
            const ratio = k / trailLen;
            ctx.beginPath();
            ctx.moveTo(veh.trail[k - 1].x, veh.trail[k - 1].y);
            ctx.lineTo(veh.trail[k].x, veh.trail[k].y);
            ctx.strokeStyle = drawColor;
            ctx.lineWidth = ratio * 2.8 + 0.5;
            ctx.globalAlpha = Math.pow(ratio, 2.5) * 0.95;
            ctx.stroke();
          }
          ctx.globalAlpha = 1.0;
        }

        ctx.lineWidth = 0.7;
        allNodes.forEach((node) => {
          if (node.type === 'depot') return;
          const nodePos = isoProject(node.x, node.y, cw, ch);
          const dx = pos.x - nodePos.x;
          const dy = pos.y - nodePos.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 160) {
            const alpha = (1.0 - dist / 160) * (isDark ? 0.32 : 0.42);
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

        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = drawColor;
        ctx.shadowBlur = 10;
        ctx.shadowColor = `rgba(${ringRgb}, 0.5)`;
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 4, 0, Math.PI * 2);
        ctx.strokeStyle = isDark ? '#151a18' : '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        if (Math.random() < 0.0018) {
          veh.rerouteActive = true;
          veh.rerouteTime = 0;
          veh.reroutePos = { x: pos.x, y: pos.y };
          const reduction = Math.random() * 4.5 + 0.5;
          costParticles.push({
            x: pos.x,
            y: pos.y - 12,
            text: `-${reduction.toFixed(1)}`,
            alpha: 1.0,
          });
        }

        if (veh.rerouteActive) {
          veh.rerouteTime++;
          const progress = veh.rerouteTime / 35;
          if (progress >= 1.0) {
            veh.rerouteActive = false;
          } else {
            const alpha = 1.0 - progress;
            ctx.beginPath();
            ctx.arc(veh.reroutePos.x, veh.reroutePos.y, progress * 32, 0, Math.PI * 2);
            ctx.strokeStyle = isDark ? `rgba(255, 94, 0, ${alpha})` : `rgba(234, 88, 12, ${alpha})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(veh.reroutePos.x, veh.reroutePos.y, progress * 16, 0, Math.PI * 2);
            ctx.strokeStyle = isDark ? `rgba(122, 115, 255, ${alpha * 0.8})` : `rgba(99, 91, 255, ${alpha * 0.85})`;
            ctx.lineWidth = 1.2;
            ctx.stroke();
          }
        }
      });

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
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, node.type === 'depot' ? 3.5 : 1.8, 0, Math.PI * 2);
        ctx.fillStyle = colors.nodeCore;
        ctx.fill();
      });

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

      animationId = requestAnimationFrame(draw);
    }

    window.addEventListener('resize', resize);
    resize();
    draw();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
        opacity: 0.8
      }}
    />
  );
}
