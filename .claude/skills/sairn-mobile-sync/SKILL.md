---
name: sairn-mobile-sync
description: Implementation pattern for syncing data captured on a phone/tablet in the field (signatures, photos, slab scans, POS entries) back to the office view of a SAIRN app, and vice versa. Trigger whenever the user wants "mobile sync," "phone to office," "field to shop," "real-time" or "live" updates between two devices, a signature-capture pad, a bridge/relay endpoint between sessions, or is building POS/slab/intake features that need to appear on another device without a manual refresh. Extracted from sairn-software-architect because this is a reusable technical pattern used identically across apps, not an architecture judgment call — the judgment call (whether a feature needs cross-device sync at all) still belongs in sairn-software-architect; this skill is what to do once that call is made. Companion to sairn-app-builder (native wrapper/push is a different problem — see the ceiling section below before reaching for this skill).
---

# SAIRN Mobile Sync — phone-to-office (and back), honestly

## The ceiling: this is polling, not push — say so up front

SAIRN apps are hosted single-file HTML with a serverless backend (`sairn.vercel.app/api/*`), running in a plain mobile browser (not a native wrapper in the common case — see `sairn-app-builder` if one exists for this app). That combination **cannot** hold a persistent WebSocket or receive OS-level push notifications reliably, especially on iOS Safari, which suspends background tabs aggressively. Do not design or describe this as "real-time" — it's **near-real-time via polling**, typically a few seconds to tens of seconds of lag depending on the existing interval. That's a perfectly good, honest architecture for this use case (a shop office doesn't need sub-second updates from a field tech). State the real lag to whoever's asking for the feature before building, not after they notice it.

If someone actually needs true push (e.g. an urgent alert that must arrive instantly), that requires a native wrapper with real push entitlements — that's `sairn-app-builder`'s Tauri/Electron territory, a different, bigger commitment. Don't quietly try to fake push with aggressive short-interval polling; say plainly which one is being built.

## The 4-part pattern

1. **Local write is immediate and optimistic, and it fires the bridge POST right away — don't wait for a poll cycle to originate an update.** The device that captured the data (phone in the field) writes to its own local state (`localStorage`) first, so the UI updates instantly and works offline, *then* immediately POSTs the same event to the bridge endpoint. If the POST fails (offline, flaky signal), queue it and retry — the local write already happened, so nothing is lost from the originating device's point of view.

2. **The bridge stores the event with `timestamp` and `source_device`, never just the raw payload.** Every consumer needs to know *when* something happened and *where it came from* to merge correctly and to avoid reprocessing its own echo (see point 4 below). The bridge is a thin store-and-list endpoint — it does not need business logic, just append-and-return-since(timestamp).

3. **The office device polls using whatever `setInterval` loop already exists in that app — don't add a second, competing timer.** Nearly every SAIRN app already has some periodic refresh (KPI updates, nav-triggered re-renders). Hook the bridge check into that existing cadence rather than starting a new interval at a different frequency; two independent timers racing to update the same DOM is how you get flicker and duplicate renders (see the `renderX()`-shadowing class of bug documented in StoneDesk's orphan-reference audit — two render paths for one panel is always a bug, sync-originated or not). When new events come back, **merge into the existing real data model** — compare timestamps, don't blind-overwrite a field the office might have just edited locally.

4. **Never fork a second data store for the same shared concept.** The synced data lives in the exact same `localStorage` key / same in-memory array / same schema the rest of that panel already uses — not a parallel `_synced` copy that a different render function reads. This is the single most common way this pattern goes wrong in practice: someone builds the sync path against a fresh, convenient data shape instead of plugging into the real one, and now the app has two competing sources of truth for one concept. (StoneDesk has several standing examples of exactly this mistake, pre-dating this skill, where two renderers/two storage keys grew up around one feature — customers, comms, and remnant each had this; see git history around the "canonical renderer" fixes. This skill exists so mobile-sync work doesn't add a new instance of the same bug.)

## Standard bridge event shape

Every event through the bridge — either direction — uses the same envelope:

```js
{
  app_id: "stonedesk",           // which app; bridge may serve multiple
  event_type: "signature_captured", // app-defined string, e.g. "slab_scanned", "pos_sale"
  source_device: deviceId,       // stable per-device id (see below) — lets a device ignore its own echo
  timestamp: new Date().toISOString(),
  payload: { /* event-specific data */ }
}
```

`source_device` should be a UUID generated once and cached in that device's own `localStorage` (`sd_device_id` or equivalent app-prefixed key) — not derived from anything identifying (no fingerprinting). When polling, a device filters out events where `source_device === myDeviceId` before merging, so it never re-applies its own write.

Minimal bridge contract (server side, e.g. a Vercel function alongside the existing `api/*` endpoints):
- `POST /api/bridge` — append one event (body = the envelope above).
- `GET /api/bridge?app_id=X&since=<timestamp>` — return events newer than `since`, so pollers only fetch deltas, not the whole log every cycle.

Keep this endpoint dumb (store + filter-by-timestamp only). Business logic (what a `pos_sale` event actually does to inventory) belongs in the app's own merge handler, not the bridge.

## Working signature-capture canvas snippet

Vanilla JS, touch + mouse, no library. Produces a PNG data URL ready to drop straight into the bridge payload.

```html
<canvas id="sig-pad" width="600" height="200" style="border:1px solid var(--border);touch-action:none;background:#fff;border-radius:8px"></canvas>
<div style="display:flex;gap:8px;margin-top:8px">
  <button class="q-btn" onclick="sigClear()">Clear</button>
  <button class="q-btn primary" onclick="sigSaveAndSync()">Save Signature</button>
</div>
<script>
(function(){
  var canvas = document.getElementById('sig-pad');
  var ctx = canvas.getContext('2d');
  ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.strokeStyle = '#111';
  var drawing = false, last = null;

  function pos(e){
    var r = canvas.getBoundingClientRect();
    var p = e.touches ? e.touches[0] : e;
    return { x: (p.clientX - r.left) * (canvas.width / r.width),
             y: (p.clientY - r.top) * (canvas.height / r.height) };
  }
  function start(e){ e.preventDefault(); drawing = true; last = pos(e); }
  function move(e){
    if (!drawing) return; e.preventDefault();
    var p = pos(e);
    ctx.beginPath(); ctx.moveTo(last.x, last.y); ctx.lineTo(p.x, p.y); ctx.stroke();
    last = p;
  }
  function end(){ drawing = false; last = null; }

  canvas.addEventListener('mousedown', start); canvas.addEventListener('mousemove', move);
  window.addEventListener('mouseup', end);
  canvas.addEventListener('touchstart', start, {passive:false});
  canvas.addEventListener('touchmove', move, {passive:false});
  canvas.addEventListener('touchend', end);

  window.sigClear = function(){ ctx.clearRect(0, 0, canvas.width, canvas.height); };

  window.sigSaveAndSync = function(){
    var dataUrl = canvas.toDataURL('image/png');
    // 1. local write, immediate — plug into THIS app's real data model, not a new one
    var jobId = getCurrentJobId(); // app-specific
    saveSignatureLocally(jobId, dataUrl); // app-specific, writes the real localStorage key

    // 2. immediate bridge POST — don't wait for a poll cycle
    fetch('/api/bridge', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        app_id: 'stonedesk',
        event_type: 'signature_captured',
        source_device: getDeviceId(), // app-specific, cached UUID
        timestamp: new Date().toISOString(),
        payload: { jobId: jobId, signature: dataUrl }
      })
    }).catch(function(){ queueForRetry('signature_captured', jobId, dataUrl); }); // app-specific offline queue

    showToast('Signature saved.');
  };
})();
</script>
```

`getCurrentJobId`, `saveSignatureLocally`, `getDeviceId`, `queueForRetry` are deliberately left as app-specific stubs — wire them to whatever real job/customer data model and device-id convention that app already has. Don't invent a new signature-specific store; a signature is a field on the existing job/customer record.

## What NOT to do

- **Don't call this "real-time"** to a stakeholder — it's polling-based near-real-time. Say the actual lag.
- **Don't build a second timer.** Hook into the app's existing `setInterval`/nav-triggered refresh.
- **Don't fork a data store.** Same `localStorage` key, same schema, same renderer the rest of the panel already uses — this is the #1 way this pattern turns into a bug.
- **Don't skip `source_device` filtering.** Without it, a device will poll back its own just-sent event and can double-apply or flicker.
- **Don't put business logic in the bridge.** It stores and filters-by-timestamp; the app decides what an event *means*.
- **Don't reach for this skill when real push is actually required** — that's a native-wrapper problem (`sairn-app-builder`), not a polling-interval tuning problem.
