/* ============================================================
   PetFinder Pro UX — vanilla JS, 0 deps
   - Top loading bar on link nav + form submit
   - Toast API: PF.toast(text, type, opts)
   - Scroll-reveal via IntersectionObserver
   - Scroll-to-top button
   - PWA install prompt + service worker
   - Lazy-load all <img> (native + fallback fade-in)
   ============================================================ */
(function () {
  'use strict';
  const w = window, d = document;
  const PF = w.PF = w.PF || {};

  // ---------- 1. Top progress bar ----------
  const bar = d.createElement('div');
  bar.id = 'pf-progress';
  d.documentElement.appendChild(bar);
  let progT = 0, progRAF;
  function progStart() {
    cancelAnimationFrame(progRAF);
    progT = 0; bar.classList.add('active');
    bar.style.transform = 'scaleX(0.05)';
    setTimeout(progTick, 80);
  }
  function progTick() {
    if (progT >= 0.85) return;
    progT += (0.85 - progT) * 0.06;
    bar.style.transform = `scaleX(${progT})`;
    progRAF = requestAnimationFrame(() => setTimeout(progTick, 100));
  }
  function progDone() {
    cancelAnimationFrame(progRAF);
    bar.style.transform = 'scaleX(1)';
    setTimeout(() => {
      bar.classList.remove('active');
      setTimeout(() => { bar.style.transform = 'scaleX(0)'; }, 350);
    }, 150);
  }
  PF.progress = { start: progStart, done: progDone };

  // Hook navigation: show bar on link clicks (same-origin) & form submits
  d.addEventListener('click', (e) => {
    const a = e.target.closest('a');
    if (!a) return;
    if (a.target === '_blank' || a.hasAttribute('download')) return;
    const url = a.getAttribute('href');
    if (!url || url.startsWith('#') || url.startsWith('javascript:') || url.startsWith('mailto:') || url.startsWith('tel:')) return;
    try {
      const u = new URL(a.href, location.href);
      if (u.origin !== location.origin) return;
      if (u.pathname === location.pathname && u.hash) return;
    } catch (_) { return; }
    progStart();
  }, true);
  d.addEventListener('submit', (e) => {
    if (e.target && e.target.method && e.target.method.toLowerCase() === 'get') return;
    progStart();
  }, true);
  w.addEventListener('pageshow', progDone);

  // ---------- 2. Toast ----------
  let toastWrap = d.getElementById('pf-toasts');
  if (!toastWrap) {
    toastWrap = d.createElement('div');
    toastWrap.id = 'pf-toasts';
    toastWrap.setAttribute('role', 'status');
    toastWrap.setAttribute('aria-live', 'polite');
    d.body.appendChild(toastWrap);
  }
  const ICONS = { success: '✅', error: '⚠️', warning: '⚡', info: 'ℹ️' };
  PF.toast = function (msg, type = 'info', opts = {}) {
    const life = Math.max(2000, opts.life || 5000);
    const t = d.createElement('div');
    t.className = 'pf-toast ' + (type || 'info');
    t.style.setProperty('--life', (life / 1000) + 's');
    t.innerHTML = `<span class="icon">${ICONS[type] || 'ℹ️'}</span>
      <div class="body"></div>
      <button class="close" aria-label="ปิด">×</button>`;
    t.querySelector('.body').textContent = msg;
    const remove = () => {
      t.classList.add('leaving');
      setTimeout(() => t.remove(), 260);
    };
    t.querySelector('.close').addEventListener('click', remove);
    toastWrap.appendChild(t);
    setTimeout(remove, life);
    return t;
  };

  // Promote Django messages → toasts (then hide the original .messages block)
  const djMsgs = d.querySelectorAll('.messages .msg');
  if (djMsgs.length) {
    djMsgs.forEach(el => {
      const cls = el.className.split(' ').find(c => c !== 'msg') || 'info';
      const txt = (el.querySelector('span') || el).textContent.trim();
      PF.toast(txt, cls);
    });
    const wrap = d.querySelector('.messages');
    if (wrap) wrap.remove();
  }

  // ---------- 3. Scroll reveal ----------
  if ('IntersectionObserver' in w) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    const observe = () => d.querySelectorAll('[data-reveal]:not(.in)').forEach(el => io.observe(el));
    observe();
    // Re-observe after pageshow (back/forward cache)
    w.addEventListener('pageshow', observe);
  } else {
    d.querySelectorAll('[data-reveal]').forEach(el => el.classList.add('in'));
  }

  // ---------- 4. Scroll to top ----------
  const totop = d.createElement('button');
  totop.id = 'pf-totop';
  totop.setAttribute('aria-label', 'กลับขึ้นบน');
  totop.innerHTML = '↑';
  d.body.appendChild(totop);
  totop.addEventListener('click', () => w.scrollTo({ top: 0, behavior: 'smooth' }));
  let lastY = 0;
  w.addEventListener('scroll', () => {
    const y = w.scrollY;
    totop.classList.toggle('show', y > 600);
    lastY = y;
  }, { passive: true });

  // ---------- 5. PWA install prompt ----------
  let deferred;
  const installBtn = d.createElement('button');
  installBtn.id = 'pf-install';
  installBtn.innerHTML = '📱 ติดตั้งแอป';
  d.body.appendChild(installBtn);
  w.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferred = e;
    installBtn.classList.add('show');
  });
  installBtn.addEventListener('click', async () => {
    if (!deferred) return;
    installBtn.classList.remove('show');
    deferred.prompt();
    const { outcome } = await deferred.userChoice;
    deferred = null;
    if (outcome === 'accepted') PF.toast('ติดตั้งแอปสำเร็จ! 🎉', 'success');
  });
  w.addEventListener('appinstalled', () => {
    installBtn.classList.remove('show');
    PF.toast('Pet Finder ถูกติดตั้งบนเครื่องคุณแล้ว 🐾', 'success');
  });

  // ---------- 6. Lazy-load all images ----------
  d.querySelectorAll('img:not([loading])').forEach(img => {
    img.loading = 'lazy';
    img.decoding = 'async';
  });

  // ---------- 7. Service worker (best-effort) ----------
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    w.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch(() => {/* ignore */});
    });
  }

  // ---------- 8. Expose helpers ----------
  PF.copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      PF.toast('คัดลอกแล้ว', 'success', { life: 2200 });
    } catch (_) {
      PF.toast('คัดลอกไม่สำเร็จ', 'error');
    }
  };
})();
