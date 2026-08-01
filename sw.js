// sw.js -- self-destructing kill switch, not a real service worker.
//
// This file was deleted from an earlier deployment at some point in the
// past, but browsers that had already registered it kept running the OLD
// active worker indefinitely -- a service worker's update check re-fetches
// this exact URL periodically, and per spec that check FAILS (and the old
// worker is left running unchanged) whenever the fetch returns a non-2xx
// status, which is exactly what a deleted sw.js does (confirmed live 404,
// 2026-08-01). That's why those browsers could never self-heal: there was
// never a valid new script for them to update to. Restoring this file
// (with different content than whatever was last cached, which is
// automatic since it didn't exist before) gives their next periodic update
// check something to actually succeed against.
//
// Per the Service Worker spec, this update-check fetch is NEVER intercepted
// by the currently-active service worker's own fetch handler -- that
// exclusion exists specifically so a broken/stale SW can always be
// replaced. That's the mechanism this file relies on: it doesn't need the
// affected browser to ever successfully load fresh HTML first (it can't --
// that's the whole problem); it only needs its own bytes to be fetched
// during a routine update check, which happens independently.
//
// Once a browser installs this version: skipWaiting() takes over
// immediately (no waiting for old tabs to close), clients.claim() takes
// control of every open client, then it deletes every Cache Storage entry
// on this origin, unregisters itself, and forces every currently-open
// client to reload. No fetch handler is added at any point, so nothing
// this script ever does intercepts a network request -- once it's in
// control, requests already go straight to the network, which is what
// finally lets stonedesk.html's own inline kill-switch (belt-and-suspenders
// re-check) run for real.
//
// This file is intentionally left in place after the cleanup completes --
// removing it again would just recreate the exact bug it exists to fix for
// any future browser that registers it before it's next updated. If a real
// service worker is ever wanted for this origin, replace the body of this
// file with real logic; don't delete it out from under existing
// registrations again.

self.addEventListener('install', function (event) {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    (async function () {
      await self.clients.claim();

      var cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(function (name) { return caches.delete(name); }));

      await self.registration.unregister();

      var clientList = await self.clients.matchAll({ type: 'window' });
      clientList.forEach(function (client) {
        try { client.navigate(client.url); } catch (e) { /* best-effort */ }
      });
    })()
  );
});
