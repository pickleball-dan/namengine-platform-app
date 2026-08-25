// NamEngine Service Worker — minimal, cache-first for offline shell
const CACHE = 'namengine-v1';
const PRECACHE = ['/'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Only handle GET requests; let everything else pass through
  if (event.request.method !== 'GET') return;
  // Let API and admin routes always go to network
  if (event.request.url.includes('/api/') || event.request.url.includes('/dev/')) return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
