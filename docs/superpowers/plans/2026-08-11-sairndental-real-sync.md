# SAIRNdental Real Read/Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `sairndental.html` a real read path from the server —
today it has zero, so any data written from a different device (most
critically, self-scheduled bookings from `sairndental-book.html`) is
permanently invisible to staff — per
`docs/superpowers/specs/2026-08-11-sairndental-real-sync-design.md`.

**Architecture:** A new `dntMergeById()` pure array-merge helper and a new
`dntSyncFromServer()` function that loops over every real resource, reads
each from the server via the existing `sdnData('read', resource)` path,
merges server data into local storage by ID, and re-renders every panel.
Called once from `init()`; a new manual Refresh button on Pending Requests
re-runs the same full sweep. Reuses `sairngrounds.html`'s already-proven
`grdSyncFromServer()` pattern (`sairngrounds.html:1452-1509`), adapted for
this app's actual resource set and its lazy, nav-triggered render
convention (`nav()`, `sairndental.html:569-587` — unlike SAIRNgrounds,
`init()` here only renders the Dashboard panel up front; other panels
render when navigated to).

**Tech Stack:** No new dependencies — reuses the existing `sdnData()` /
`ld()` / `st()` helpers already in `sairndental.html`.

## Real correction to the approved spec, found while writing this plan

The spec's §2 resource table listed 13 resources including `dnt_denial`,
`dnt_ar`, `dnt_revenue`. **Checked the actual file and none of the three
has any client-side accessor or render function anywhere in
`sairndental.html`** — no `denial()`/`ar()`/`revenue()` function, no
`rDenial()`/`rAr()`/`rRevenue()` panel. This matches the original
top-level app design spec's own roadmap: the SAIRNcode denial/A/R/revenue
bridge is explicitly listed as a **separate, not-yet-built** follow-up
feature area, distinct from this fix. Syncing data into local storage
keys nothing reads yet would be inert, speculative code with no UI to
verify it against — real over-engineering, not a defect fix. **These
three resources are excluded from this plan's sweep.** When the
denial/A/R/revenue bridge is eventually built, real sync for it belongs
in that feature's own plan, alongside the panels that will actually
display it — not wired in blind now.

Also corrected: the spec's table assumed `dnt_provider_hours`'s local
storage key was `dnt_provider_hours_list` — the actual key, confirmed by
reading `providerHours()` (`sairndental.html:612`), is `dnt_hours_list`.

## Global Constraints

- **Real resource sweep is 10 resources, not 13** (corrected above):
  `dnt_patients`, `dnt_providers`, `dnt_operatories`,
  `dnt_provider_hours`, `dnt_procedure_types`, `dnt_coverage_rules`,
  `dnt_appointments`, `dnt_charges`, `dnt_payments`, `dnt_settings`.
- `dnt_settings` uses single-object replace, not array-merge-by-ID (spec
  §0) — it's the one resource stored locally as an object
  (`dnt_settings_obj`), not a list.
- Sync triggers: once from `init()`, plus a manual Refresh button on
  Pending Requests only — no `setInterval`, no periodic polling anywhere
  (spec §0, §6).
- The Refresh button re-runs the *full* sweep, not an appointments-only
  sync (spec §0) — `rPending()` needs patients/providers/procedure_types
  synced too to resolve names.
- A resource that fails to read (unprovisioned, network error) is
  skipped; the sweep continues through the rest — never let one failure
  abort the whole sweep (spec §1).
- `removePatient()`/`removeProcedureType()` stay local-only (no behavior
  change) — only their toast text changes (spec §4, exact wording below).
- `python tools/checkblocks.py sairndental.html` / `div_balance_check.py`
  / `duplicate_global_check.py` clean after every change. Push Protocol:
  full local checks before push, real live-verify after.

---

### Task 1: `dntMergeById()` pure helper

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: nothing (pure function).
- Produces: `dntMergeById(local, serverArr)` — Task 2's
  `dntSyncFromServer()` calls this exact function for every list-shaped
  resource (all except `dnt_settings`).

- [ ] **Step 1: Add the helper**

Insert immediately before `function init(){` (currently
`sairndental.html:1169`):

```js
// ── REAL SERVER SYNC (2026-08-11) ────────────────────────────────────
// This app previously had zero 'read' actions anywhere -- every panel
// rendered only from this device's own localStorage, so anything written
// from a different device (critically, a self-scheduled booking from
// sairndental-book.html, which always runs in a different, unauthenticated
// browser) was permanently invisible to staff. Confirmed live before this
// fix: a fresh session showed 0 patients/providers/etc. and "No pending
// requests" despite the server holding real data for all of it. Same
// pattern as sairngrounds.html's grdMergeById()/grdSyncFromServer()
// (2026-08-06 fix for the identical bug there) -- reused deliberately,
// not reinvented. See docs/superpowers/specs/2026-08-11-sairndental-real-sync-design.md.
//
// Known, accepted limitation (same as the sairngrounds precedent): no
// delete-tombstones -- a record removed locally via removePatient()/
// removeProcedureType() can reappear on the next sync, since the server
// still has it and this merge has no way to know it was deliberately
// removed. Disclosed to staff via the updated toast text (Task 4), not
// silently hidden. Real tombstoned deletes are separate, larger,
// deferred work.
function dntMergeById(local, serverArr){
  var merged=local.slice();
  serverArr.forEach(function(sr){
    var idx=merged.findIndex(function(m){return m&&sr&&m.id!=null&&m.id===sr.id;});
    if(idx>=0)merged[idx]=sr;else merged.push(sr);
  });
  return merged;
}
```

- [ ] **Step 2: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

- [ ] **Step 3: Node verification (this function has zero DOM dependency, so it's genuinely testable outside the browser even though it lives inline in the HTML file)**

Run this exact command, pasting the function's own source:

```
node -e "
function dntMergeById(local, serverArr){
  var merged=local.slice();
  serverArr.forEach(function(sr){
    var idx=merged.findIndex(function(m){return m&&sr&&m.id!=null&&m.id===sr.id;});
    if(idx>=0)merged[idx]=sr;else merged.push(sr);
  });
  return merged;
}
var assert=require('assert');
// server record overwrites a matching local ID
assert.deepStrictEqual(
  dntMergeById([{id:'A',name:'old'}],[{id:'A',name:'new'}]),
  [{id:'A',name:'new'}]
);
// non-matching server record gets appended
assert.deepStrictEqual(
  dntMergeById([{id:'A',name:'a'}],[{id:'B',name:'b'}]),
  [{id:'A',name:'a'},{id:'B',name:'b'}]
);
// local-only record with no server counterpart survives untouched
assert.deepStrictEqual(
  dntMergeById([{id:'LOCAL-ONLY',name:'x'}],[]),
  [{id:'LOCAL-ONLY',name:'x'}]
);
console.log('all 3 dntMergeById cases passed');
"
```

Expected output: `all 3 dntMergeById cases passed`.

- [ ] **Step 4: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- dntMergeById() pure merge helper (real-sync foundation)"
```

---

### Task 2: `dntSyncFromServer()` + wire into `init()`

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: `dntMergeById()` from Task 1, existing `sdnData(action,
  resource, payload)`, `ld()`, `st()`, `settings()`.
- Produces: `dntSyncFromServer()` — Task 3's Refresh button calls this
  exact function.

- [ ] **Step 1: Add the sweep function**

Insert immediately after Task 1's `dntMergeById()`:

```js
var DNT_SYNC_RESOURCES=[
  ['dnt_patients','dnt_patients_list'],
  ['dnt_providers','dnt_providers_list'],
  ['dnt_operatories','dnt_operatories_list'],
  ['dnt_provider_hours','dnt_hours_list'],
  ['dnt_procedure_types','dnt_procedures_list'],
  ['dnt_coverage_rules','dnt_coverage_list'],
  ['dnt_appointments','dnt_appointments_list'],
  ['dnt_charges','dnt_charges_list'],
  ['dnt_payments','dnt_payments_list']
];
// dnt_denial/dnt_ar/dnt_revenue deliberately excluded -- no client-side
// accessor or render function exists for any of them yet (confirmed by
// reading the file); that's a separate, not-yet-built follow-up feature
// area, not part of this fix. See this plan's "Real correction" section.
async function dntSyncFromServer(){
  var changed=false;
  for(var i=0;i<DNT_SYNC_RESOURCES.length;i++){
    var resource=DNT_SYNC_RESOURCES[i][0], key=DNT_SYNC_RESOURCES[i][1];
    var serverData=await sdnData('read',resource,{});
    if(Array.isArray(serverData)&&serverData.length){
      st(key,dntMergeById(ld(key,[]),serverData));changed=true;
    }
  }
  // dnt_settings: single-object resource, not a list -- take the one
  // 'default' record from the server's array response (still array-
  // shaped like every other resource's read, per api/sd-data.js) and
  // replace the local object directly.
  var settingsData=await sdnData('read','dnt_settings',{});
  if(Array.isArray(settingsData)&&settingsData.length){
    var serverSettings=settingsData.find(function(s){return s&&s.id==='default';})||settingsData[0];
    if(serverSettings){st('dnt_settings_obj',serverSettings);changed=true;}
  }
  if(changed){
    rDash();rPatients();rProviders();rOperatories();rHours();rProcedures();
    rCoverage();rPending();rAppointments();rBilling();
    if($('panel-booking-settings')&&$('panel-booking-settings').classList.contains('on'))rBookingSettings();
  }
}
```

(`rBookingSettings()` is guarded by an `.on`-class check, not called
unconditionally like the others, because it reads directly from `<input>`
DOM elements that only exist/are populated correctly once that panel has
been navigated to at least once — matching this file's existing lazy-nav
convention rather than fighting it.)

- [ ] **Step 2: Call it once from `init()`**

```js
function init(){
  rDash();
  fillDentalSelects();
  dntSyncFromServer();
}
```

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

- [ ] **Step 4: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- dntSyncFromServer() real read/sync sweep, called on init()"
```

---

### Task 3: Manual Refresh button on Pending Requests

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: `dntSyncFromServer()` from Task 2.
- Produces: no new functions — a UI trigger for an existing one.

- [ ] **Step 1: Add the button**

In the Pending Requests panel header (`sairndental.html:395-398`):

```html
        <div class="ph"><div><div class="ptitle">Pending Requests</div><div class="psub">Self-scheduled and other pending appointments &mdash; review and confirm before they're final. New bookings are never auto-confirmed.</div></div></div>
        <div class="card"><div class="ch"><div class="ct">Awaiting Confirmation</div><button class="btn bo bs" onclick="dntRefreshPending()">Refresh</button></div><div class="cb" style="padding:0">
          <table id="pending-table"><thead><tr><th>Patient</th><th>Provider</th><th>Time</th><th>Source</th><th>Photos / Notes</th><th></th></tr></thead><tbody id="pending-tbody"></tbody></table>
        </div></div>
```

- [ ] **Step 2: Add the click handler**

Immediately after `dntSyncFromServer()` (Task 2):

```js
async function dntRefreshPending(){
  var btn=event&&event.target;
  if(btn){btn.disabled=true;btn.textContent='Refreshing...';}
  await dntSyncFromServer();
  if(btn){btn.disabled=false;btn.textContent='Refresh';}
  toast('Refreshed from server');
}
```

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

Expected: clean, no duplicate IDs (this adds no new `id` attributes, only
a button with an `onclick`).

- [ ] **Step 4: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- manual Refresh button on Pending Requests (full sweep, not appointments-only)"
```

---

### Task 4: Local-delete toast disclosure

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new — text-only change to two existing toasts.

- [ ] **Step 1: `removePatient()`**

```js
function removePatient(id){
  // Local-only, matching this platform's real convention for every
  // resource on the generic sd-data.js pattern -- that endpoint has no
  // delete action for ANY app (read/write only), so a fake "sync the
  // deletion" call would either do nothing useful or, worse, blindly
  // overwrite the real synced record's full data with a bare
  // {id,_deleted} payload via the upsert-merge write path, destroying
  // the real fields. Removing here only removes it from this device --
  // and now that real sync exists (2026-08-11), a later sync WILL pull
  // this record right back if the server still has it. Disclosed via
  // the toast below, not silently hidden.
  var list=patients().filter(function(p){return p.id!==id;});
  st('dnt_patients_list',list);rPatients();
  toast('Patient removed on this device -- may reappear if server data syncs again');
}
```

- [ ] **Step 2: `removeProcedureType()`**

```js
function removeProcedureType(id){
  // Local-only -- see removePatient()'s comment for why.
  var list=procedureTypes().filter(function(p){return p.id!==id;});
  st('dnt_procedures_list',list);rProcedures();
  toast('Procedure type removed on this device -- may reappear if server data syncs again');
}
```

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
```

- [ ] **Step 4: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- disclose reappear-on-sync risk in local-delete toasts"
```

---

### Task 5: End-to-end verification, push, live-verify

- [ ] **Step 1:** Full local re-check: `checkblocks.py` /
  `div_balance_check.py` / `duplicate_global_check.py` on
  `sairndental.html`; confirm Task 1's Node verification still passes.
- [ ] **Step 2:** Push to `main`.
- [ ] **Step 3: The actual regression test for this entire fix — genuinely
  live, not simulated.** Using the real `DNT-PINNACLE-2026` demo practice
  (`verify-test-slug`), submit a new booking through the real live
  `sairndental-book.html` (a fresh patient name, so it's unambiguous which
  record is the new one). Then, in a **separate, fresh** browser session
  (cleared localStorage, matching the diagnostic method already used to
  find this bug) log into `sairndental.html` with the same license and PIN.
  Expected: the new booking appears in Pending Requests with the correct
  patient name, provider, and time — not "(unknown patient)", not absent.
- [ ] **Step 4:** With that same session still open, submit a *second* new
  booking through the public page (different patient name). Without
  reloading the staff app, click the new Refresh button on Pending
  Requests. Expected: the second booking appears without a full page
  reload.
- [ ] **Step 5:** Confirm the reappear-after-delete behavior is real, not
  just theoretical: remove one of the test patients created above via
  `removePatient()`, confirm the toast shows the new disclosure text and
  the row disappears, then click Refresh. Expected: the record reappears
  (proving Task 4's disclosure is accurate) — and confirm this is stated
  honestly to whoever reviews this, not treated as a bug to silently patch
  around.
- [ ] **Step 6:** Confirm the Dashboard's counts (`k-patients` etc.)
  reflect real server-synced totals after a fresh login, not just
  whatever existed locally before.
- [ ] **Step 7: Regression check.** Confirm a license/practice with
  genuinely zero server-side data for some resource (e.g. a resource that
  returns an empty array) does not clear out any local seed/demo data for
  that resource, and does not throw — read `dntSyncFromServer()`'s guard
  (`Array.isArray(serverData)&&serverData.length`) and confirm this
  case live if a suitable test license is available; otherwise confirm by
  code inspection that an empty/absent server response is a genuine no-op.
- [ ] **Step 8: `dnt_settings` single-object handling (spec §5's explicit
  test requirement).** Live: use the demo practice's existing Booking
  Settings (already has real `booking_slug:'verify-test-slug'` etc. saved
  server-side), clear localStorage, log in fresh, navigate to Booking
  Settings. Expected: the real saved values populate the form (proving
  the server's one `default` record replaced the local object, not the
  hardcoded empty-string defaults from `settings()`'s fallback). Confirm
  by code inspection (no live case readily available for this specific
  path) that a practice with no settings row at all — `settingsData` is
  `[]` — leaves the local `dnt_settings_obj` untouched rather than being
  overwritten with something broken.
- [ ] **Step 9: Failure-doesn't-abort-the-sweep (spec §5's explicit test
  requirement).** Confirmed by code inspection, not a live simulated
  failure (impractical to engineer a real mid-sweep failure against a
  live endpoint): `sdnData()` (`sairndental.html:492-499`) never throws —
  every failure path (`!r.ok`, network error, no license) resolves to
  `null` via its own internal `.catch()`. `dntSyncFromServer()`'s loop has
  no `try/catch` and no early return on a `null` result — it just skips
  that resource's merge (`if(Array.isArray(serverData)...)` is false for
  `null`) and continues to the next iteration. The loop structurally
  cannot abort partway through; this is a property of the code, not
  something that needs a live failure injected to prove.
- [ ] **Step 10:** Clean up all test patients/appointments created in Steps
  3-5 — **note up front, per the already-logged backlog item, there is no
  delete API anywhere on this platform**, so "cleanup" here means
  reporting the exact record IDs created for manual Supabase-dashboard
  deletion, the same honest limitation already hit and logged during the
  photo-capture feature's own live verification.
- [ ] **Step 11:** Update
  `docs/superpowers/specs/2026-08-11-sairndental-real-sync-design.md`'s
  status line with the real commit SHAs and confirmed-live date.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks 1-5
is written**, per your instruction.
