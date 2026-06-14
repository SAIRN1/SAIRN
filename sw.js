// ================================================================
// SAIRN B2B Service Worker — sw.js (v2)
// Offline-first for field use: cache all app shells
// Michael L. Dibert · SAIRN Technologies · 2026
// ================================================================

const CACHE = 'sairn-b2b-v2';
const B2B_APPS = [
  '/stonedesk.html', '/fabricor.html',
  '/sairntrade.html', '/sairnbuild.html',
  '/sairnscape.html', '/sairnhr.html',
  '/sairnaccounting.html', '/sairnlaw.html',
  '/sairncode.html', '/sairndesign.html'
];

// Cache app shells on install
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => {
      return Promise.allSettled(B2B_APPS.map(url =>
        cache.add(url).catch(err => console.log('Cache miss:', url, err.message))
      ));
    })
  );
  self.skipWaiting();
});

// Clean old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network first for API, cache first for app shells
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Always network for API calls
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({ error: 'offline', message: 'No network. Data will sync when reconnected.' }), {
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );
    return;
  }

  // Cache-first for HTML app shells
  if (url.pathname.endsWith('.html') || url.pathname === '/') {
    e.respondWith(
      caches.match(e.request).then(cached => {
        const networkFetch = fetch(e.request).then(response => {
          if (response.ok) {
            caches.open(CACHE).then(cache => cache.put(e.request, response.clone()));
          }
          return response;
        }).catch(() => cached);
        return cached || networkFetch;
      })
    );
    return;
  }

  // Default: network with cache fallback
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});

// Background sync for offline job saves
self.addEventListener('sync', e => {
  if (e.tag === 'sync-jobs') {
    e.waitUntil(syncOfflineData());
  }
});

async function syncOfflineData() {
  // Get queued actions from IndexedDB (set by apps when offline)
  try {
    const db = await openDB();
    const tx = db.transaction('offline_queue', 'readwrite');
    const store = tx.objectStore('offline_queue');
    const items = await store.getAll();

    for (const item of items) {
      try {
        await fetch(item.url, {
          method: item.method,
          headers: item.headers,
          body: item.body
        });
        await store.delete(item.id);
      } catch (e) {
        console.log('Sync failed for item', item.id, e.message);
      }
    }
  } catch (e) {
    console.log('Background sync error:', e.message);
  }
}

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('sairn_offline', 1);
    req.onupgradeneeded = e => {
      e.target.result.createObjectStore('offline_queue', { keyPath: 'id', autoIncrement: true });
    };
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = () => reject(req.error);
  });
}
