/* ============================================================
   PetFinder PRO — premium UX behaviors
   - Dark mode (no flash, syncs with OS)
   - Ripple effect (auto-applied to .pf-ripple)
   - Tilt 3D (auto-applied to .pf-tilt)
   - Counter animation (auto-applied to .pf-counter[data-target])
   - Bottom sheet API: PF.openSheet(id)
   - Native share API helper: PF.share(opts) or [data-share-url]
   - Haptic feedback: PF.haptic(ms)
   - Pull-to-refresh
   - Swipe gestures: PF.onSwipe(el, {left, right, up, down})
   ============================================================ */
(function () {
  'use strict';
  const w = window, d = document;
  const PF = w.PF = w.PF || {};

  // ─── Dark mode (no flash: read at parse-time via inline script in base.html) ───
  function applyTheme(t) {
    d.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem('pf-theme', t); } catch (_) {}
    const meta = d.querySelector('meta[name="theme-color"]:not([media])') ||
                 d.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = t === 'dark' ? '#1a1f2e' : '#FCEED5';
  }
  PF.toggleTheme = function () {
    const cur = d.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(cur === 'dark' ? 'light' : 'dark');
    PF.haptic(20);
  };
  PF.setTheme = applyTheme;

  // ─── Ripple effect ───
  d.addEventListener('click', (e) => {
    const t = e.target.closest('.pf-ripple');
    if (!t) return;
    const r = t.getBoundingClientRect();
    const fx = d.createElement('span');
    fx.className = 'pf-ripple-fx';
    const size = Math.max(r.width, r.height);
    fx.style.width = fx.style.height = size + 'px';
    fx.style.left = (e.clientX - r.left) + 'px';
    fx.style.top = (e.clientY - r.top) + 'px';
    t.appendChild(fx);
    setTimeout(() => fx.remove(), 700);
  });

  // ─── Tilt 3D ───
  d.querySelectorAll('.pf-tilt').forEach((el) => {
    el.addEventListener('mousemove', (e) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      el.style.setProperty('--tilt-x', (-y * 8) + 'deg');
      el.style.setProperty('--tilt-y', (x * 12) + 'deg');
    });
    el.addEventListener('mouseleave', () => {
      el.style.setProperty('--tilt-x', '0deg');
      el.style.setProperty('--tilt-y', '0deg');
    });
  });

  // ─── Counter animation ───
  if ('IntersectionObserver' in w) {
    const cIO = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const el = e.target;
        cIO.unobserve(el);
        const target = parseFloat(el.dataset.target || '0');
        const dur = parseInt(el.dataset.dur || '1400', 10);
        const decimals = parseInt(el.dataset.decimals || '0', 10);
        const t0 = performance.now();
        const ease = (x) => 1 - Math.pow(1 - x, 3);
        function tick(now) {
          const p = Math.min(1, (now - t0) / dur);
          const v = target * ease(p);
          el.textContent = v.toLocaleString('th-TH', {
            maximumFractionDigits: decimals, minimumFractionDigits: decimals,
          });
          if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      });
    }, { threshold: 0.4 });
    d.querySelectorAll('.pf-counter[data-target]').forEach(el => cIO.observe(el));
  }

  // ─── Bottom sheet API ───
  PF.openSheet = function (id) {
    const sheet = d.getElementById(id);
    if (!sheet) return;
    let back = d.querySelector('.pf-sheet-back[data-for="' + id + '"]');
    if (!back) {
      back = d.createElement('div');
      back.className = 'pf-sheet-back'; back.dataset.for = id;
      d.body.appendChild(back);
      back.addEventListener('click', () => PF.closeSheet(id));
    }
    requestAnimationFrame(() => {
      back.classList.add('open');
      sheet.classList.add('open');
      sheet.classList.add('pf-sheet'); // ensure styled
    });
  };
  PF.closeSheet = function (id) {
    const sheet = d.getElementById(id);
    const back = d.querySelector('.pf-sheet-back[data-for="' + id + '"]');
    if (sheet) sheet.classList.remove('open');
    if (back) back.classList.remove('open');
  };

  // ─── Native Share API ───
  PF.share = async function (opts = {}) {
    const data = {
      title: opts.title || d.title,
      text: opts.text || '',
      url: opts.url || location.href,
    };
    PF.haptic(15);
    if (navigator.share) {
      try { await navigator.share(data); return true; }
      catch (_) { /* user cancelled */ return false; }
    }
    // Fallback: copy URL
    try {
      await navigator.clipboard.writeText(data.url);
      if (PF.toast) PF.toast('คัดลอกลิงก์แล้ว — แชร์ได้เลย!', 'success', { life: 2500 });
    } catch (_) {
      if (PF.toast) PF.toast('แชร์ไม่สำเร็จ', 'error');
    }
    return false;
  };
  d.addEventListener('click', (e) => {
    const t = e.target.closest('[data-share-url]');
    if (!t) return;
    e.preventDefault();
    PF.share({
      title: t.dataset.shareTitle, text: t.dataset.shareText, url: t.dataset.shareUrl,
    });
  });

  // ─── Haptic feedback ───
  PF.haptic = function (ms) {
    if ('vibrate' in navigator) {
      try { navigator.vibrate(Math.min(ms || 25, 100)); } catch (_) {}
    }
  };

  // ─── Pull-to-refresh (mobile only) ───
  (function ptr() {
    if (!('ontouchstart' in w)) return;
    let startY = 0, pulling = false, threshold = 80;
    const ind = d.createElement('div');
    ind.className = 'pf-ptr'; ind.textContent = '⬇️ ดึงเพื่อรีเฟรช';
    d.body.appendChild(ind);
    d.addEventListener('touchstart', (e) => {
      if (w.scrollY > 0) return;
      startY = e.touches[0].clientY; pulling = true;
    }, { passive: true });
    d.addEventListener('touchmove', (e) => {
      if (!pulling) return;
      const dy = e.touches[0].clientY - startY;
      if (dy <= 0) { ind.classList.remove('show'); return; }
      if (dy > 25) ind.classList.add('show');
      if (dy > threshold) ind.textContent = '🔄 ปล่อยเพื่อโหลด';
    }, { passive: true });
    d.addEventListener('touchend', (e) => {
      if (!pulling) return;
      pulling = false;
      const dy = (e.changedTouches[0].clientY - startY);
      if (dy > threshold) {
        ind.classList.add('spin'); ind.textContent = ' กำลังโหลด...';
        PF.haptic(40);
        setTimeout(() => location.reload(), 250);
      } else {
        ind.classList.remove('show');
      }
    }, { passive: true });
  })();

  // ─── Swipe gestures ───
  PF.onSwipe = function (el, handlers) {
    let sx = 0, sy = 0, t0 = 0;
    el.addEventListener('touchstart', (e) => {
      sx = e.touches[0].clientX; sy = e.touches[0].clientY; t0 = Date.now();
    }, { passive: true });
    el.addEventListener('touchend', (e) => {
      const dx = e.changedTouches[0].clientX - sx;
      const dy = e.changedTouches[0].clientY - sy;
      const dt = Date.now() - t0;
      if (dt > 600) return;
      const ax = Math.abs(dx), ay = Math.abs(dy);
      if (Math.max(ax, ay) < 40) return;
      if (ax > ay) {
        if (dx > 0 && handlers.right) handlers.right();
        if (dx < 0 && handlers.left) handlers.left();
      } else {
        if (dy > 0 && handlers.down) handlers.down();
        if (dy < 0 && handlers.up) handlers.up();
      }
    }, { passive: true });
  };

  // ─── Distance-based sorting (Geolocation + Haversine) ───
  PF.sortByDistance = function (containerSel, cardSel) {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      const lat = pos.coords.latitude, lng = pos.coords.longitude;
      const container = d.querySelector(containerSel);
      if (!container) return;
      const cards = Array.from(container.querySelectorAll(cardSel + '[data-lat][data-lng]'));
      cards.forEach(c => {
        const dlat = parseFloat(c.dataset.lat), dlng = parseFloat(c.dataset.lng);
        const dist = haversine(lat, lng, dlat, dlng);
        c.dataset.distance = dist.toFixed(1);
        const lbl = c.querySelector('.pf-distance');
        if (lbl) lbl.textContent = '📍 ' + dist.toFixed(1) + ' กม.';
      });
      cards.sort((a, b) => parseFloat(a.dataset.distance) - parseFloat(b.dataset.distance))
        .forEach(c => container.appendChild(c));
      if (PF.toast) PF.toast('เรียงตามระยะใกล้สุดแล้ว 📍', 'success');
    }, () => {
      if (PF.toast) PF.toast('ไม่สามารถเข้าถึงตำแหน่งได้', 'error');
    }, { timeout: 8000 });
  };
  function haversine(la1, lo1, la2, lo2) {
    const R = 6371;
    const toRad = (x) => x * Math.PI / 180;
    const dLa = toRad(la2 - la1), dLo = toRad(lo2 - lo1);
    const a = Math.sin(dLa/2)**2 + Math.cos(toRad(la1))*Math.cos(toRad(la2))*Math.sin(dLo/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  }

  // ─── Auto-attach theme toggle button ───
  d.addEventListener('click', (e) => {
    if (e.target.closest('.pf-theme-toggle')) PF.toggleTheme();
  });

  // ─── Listen to OS theme changes when user hasn't picked ───
  if (w.matchMedia) {
    const mq = w.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener && mq.addEventListener('change', (e) => {
      if (!localStorage.getItem('pf-theme')) applyTheme(e.matches ? 'dark' : 'light');
    });
  }
})();
