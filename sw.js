// Screen Time Dashboard - Service Worker (PWA) v2
const CACHE_NAME = 'screentime-v8';
const PRE_CACHE = ['/', '/manifest.json'];

// CDN domains that use Network-First strategy
const CDN_DOMAINS = ['bootcdn.net'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    // Step 1: Clear ALL old caches to purge any stale CDN resources
    caches.keys().then((keys) => {
      return Promise.all(keys.map((k) => caches.delete(k)));
    }).then(() => {
      // Step 2: Pre-cache only local resources (NOT CDN)
      return caches.open(CACHE_NAME).then((cache) => {
        return cache.addAll(PRE_CACHE);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Check if this is a CDN resource → Network-First
  const isCDN = CDN_DOMAINS.some((domain) => url.hostname.includes(domain));

  if (isCDN) {
    // Network-First: try network, fallback to cache
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, clone);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }

  // Local resources → Cache-First
  if (
    event.request.destination === 'document' ||
    event.request.destination === 'style' ||
    event.request.destination === 'script' ||
    event.request.destination === 'manifest' ||
    url.pathname.endsWith('.ico')
  ) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        const fetchPromise = fetch(event.request).then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, clone);
            });
          }
          return response;
        }).catch(() => cached);
        return cached || fetchPromise;
      })
    );
  } else {
    // Network-first for API calls and other requests
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(event.request);
      })
    );
  }
});
