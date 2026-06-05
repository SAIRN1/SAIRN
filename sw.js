// SAIRN Service Worker — offline capability
const CACHE_NAME = 'sairn-v1';
const URLS_TO_CACHE = [
  '/',
  '/fabricor',
  '/sairnlearn',
  '/sairnlaw',
  '/sairnhealth',
  '/sairnhope',
  '/sairnfriend',
  '/careteam'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(URLS_TO_CACHE);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      if (response) return response;
      return fetch(event.request).catch(function() {
        return new Response('You appear to be offline. Please reconnect to use SAIRN.', {
          headers: {'Content-Type': 'text/plain'}
        });
      });
    })
  );
});
