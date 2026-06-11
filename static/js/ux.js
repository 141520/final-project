/* ═════════════════════════════════════════════════════════
   UX Layer: top progress + button-loading-on-submit + image fade
   ═════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // ─────────────────────────────────────────────
  // 1. TOP PROGRESS BAR
  // ─────────────────────────────────────────────
  const bar = document.createElement('div');
  bar.id = 'pf-topbar';
  bar.innerHTML = '<div class="bar"></div>';
  document.documentElement.appendChild(bar);
  const fill = bar.firstElementChild;

  let progressTimer = null;

  function start() {
    fill.style.opacity = '1';
    fill.style.width = '0';
    requestAnimationFrame(() => { fill.style.width = '30%'; });
    clearTimeout(progressTimer);
    progressTimer = setTimeout(creep, 400);
  }
  function creep() {
    const cur = parseFloat(fill.style.width) || 0;
    const next = Math.min(cur + (90 - cur) * 0.1, 90);
    fill.style.width = next + '%';
    progressTimer = setTimeout(creep, 400);
  }
  function finish() {
    clearTimeout(progressTimer);
    fill.style.width = '100%';
    setTimeout(() => {
      fill.style.opacity = '0';
      setTimeout(() => { fill.style.width = '0'; }, 300);
    }, 200);
  }

  // Hook navigation — click on internal links + form submit
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (!href || href.startsWith('#') || a.target === '_blank' ||
        a.hasAttribute('download') || href.startsWith('javascript:') ||
        href.startsWith('mailto:') || href.startsWith('tel:')) return;
    // ภายในโดเมนเดียวกันเท่านั้น
    try {
      const url = new URL(href, location.href);
      if (url.origin !== location.origin) return;
    } catch (_) { return; }
    start();
  });

  // Browser back/forward
  window.addEventListener('pageshow', finish);
  window.addEventListener('beforeunload', start);

  // ─────────────────────────────────────────────
  // 2. BUTTON LOADING STATE — auto on form submit
  // ─────────────────────────────────────────────
  document.addEventListener('submit', (e) => {
    const form = e.target;
    if (!form || form.tagName !== 'FORM') return;
    if (form.hasAttribute('data-no-loading')) return;

    const btn = form.querySelector('button[type="submit"], input[type="submit"]');
    if (!btn || btn.disabled) return;

    // เก็บข้อความเดิมไว้ resume ถ้า fail validation
    btn.dataset._originalLabel = btn.innerHTML || btn.value || '';
    btn.classList.add('pf-btn-loading');
    btn.disabled = true;

    // safety: ถ้า 12 วินาทียัง redirect ไม่ไป — ปลดล็อก
    setTimeout(() => {
      btn.classList.remove('pf-btn-loading');
      btn.disabled = false;
    }, 12000);
  }, true);

  // ─────────────────────────────────────────────
  // 3. IMAGE FADE-IN (handle non-lazy too)
  // ─────────────────────────────────────────────
  function markLoaded(img) {
    if (img.complete && img.naturalHeight > 0) {
      img.classList.add('is-loaded');
    } else {
      img.addEventListener('load', () => img.classList.add('is-loaded'), { once: true });
      img.addEventListener('error', () => img.classList.add('is-loaded'), { once: true });
    }
  }
  document.querySelectorAll('img[loading="lazy"]').forEach(markLoaded);

  // Observe ภาพที่ inject เข้า DOM ทีหลัง (htmx, fetch render ฯลฯ)
  if (window.MutationObserver) {
    new MutationObserver((mutations) => {
      mutations.forEach((m) => m.addedNodes.forEach((n) => {
        if (n.nodeType !== 1) return;
        if (n.matches && n.matches('img[loading="lazy"]')) markLoaded(n);
        if (n.querySelectorAll) n.querySelectorAll('img[loading="lazy"]').forEach(markLoaded);
      }));
    }).observe(document.body, { childList: true, subtree: true });
  }

  // ─────────────────────────────────────────────
  // 4. PUBLIC API
  // ─────────────────────────────────────────────
  window.PF = window.PF || {};
  window.PF.progress = { start, finish };
  window.PF.btnLoading = (btn, on) => {
    if (!btn) return;
    btn.classList.toggle('pf-btn-loading', !!on);
    btn.disabled = !!on;
  };
})();
