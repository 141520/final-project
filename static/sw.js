/* TarmRoy service worker — minimal, safe defaults
 * - Stale-while-revalidate for static assets
 * - Network-first for HTML (so logged-in pages stay fresh)
 * - Bypass: API endpoints, Supabase, admin
 */
const VERSION = 'pf-v1';
const STATIC_CACHE = `pf-static-${VERSION}`;
const PAGE_CACHE = `pf-page-${VERSION}`;

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => !k.endsWith(VERSION)).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Skip cross-origin (Supabase, Google Fonts CSS — let browser handle)
  if (url.origin !== location.origin) return;

  // Skip admin, auth, search-with-form-post
  if (url.pathname.startsWith('/admin') || url.pathname.startsWith('/logout')) return;

  // Static assets → SWR
  if (url.pathname.startsWith('/static/') || /\.(css|js|svg|png|jpg|jpeg|webp|woff2?)$/i.test(url.pathname)) {
    e.respondWith((async () => {
      const cache = await caches.open(STATIC_CACHE);
      const cached = await cache.match(req);
      const fetchPromise = fetch(req).then(res => {
        if (res && res.status === 200) cache.put(req, res.clone());
        return res;
      }).catch(() => cached);
      return cached || fetchPromise;
    })());
    return;
  }

  // HTML pages → network-first, fallback to cache
  if (req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html')) {
    e.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        const cache = await caches.open(PAGE_CACHE);
        cache.put(req, fresh.clone());
        return fresh;
      } catch (_) {
        const cache = await caches.open(PAGE_CACHE);
        const cached = await cache.match(req);
        return cached || new Response('<h1>Offline</h1><p>กรุณาเชื่อมต่ออินเทอร์เน็ต</p>',
          { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
      }
    })());
  }
});
