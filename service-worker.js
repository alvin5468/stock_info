const CACHE = 'slow-rich-v2';
const STATIC = [
  './',
  './index.html',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  // data_live.js：完全繞過 HTTP cache，直接打網路
  if (e.request.url.includes('data_live.js')) {
    e.respondWith(
      fetch(new Request(e.request.url, {cache: 'no-store'}))
        .catch(() => caches.match(e.request))
    );
    return;
  }
  // 其他靜態資源：cache-first
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
