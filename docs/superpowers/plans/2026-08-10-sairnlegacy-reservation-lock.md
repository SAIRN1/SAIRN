# SAIRNlegacy Reservation Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the real two-grieving-families reservation race
(`SAIRN-BACKLOG.md`) by making `leg_merch_units`' `Available -> Reserved`
transition a real atomic server-side check-and-set, per
`docs/superpowers/specs/2026-08-10-sairnlegacy-reservation-lock-design.md`.

**No schema migration required** — the fix is entirely in
`api/sd-data.js` (server) and `sairnlegacy.html` (client).

## Global Constraints

- Only the `Available -> Reserved` transition is gated. `releaseUnit()`
  and `markUnitSold()` are untouched. (Spec §2)
- No change to `sdnData()` or its other ~40 call sites in this file —
  `confirmReserve()` makes its own direct fetch for this one write.
  (Spec §4)
- `node --check api/sd-data.js` must pass after every change.
- `python tools/checkblocks.py sairnlegacy.html` / `div_balance_check.py`
  must stay clean after every change.
- Push Protocol: full Guardian-relevant checks before push, real
  live-verify (not assumed from a clean push) after.

---

### Task 1: `api/sd-data.js` — atomic reservation branch

**Files:** Modify `api/sd-data.js:1653-1669`
(`if (LEG_RESOURCES[resource] && action === 'write')`)

- [ ] **Step 1: Write the implementation**

Insert immediately after the existing `payload.id` validation
(`api/sd-data.js:1655-1658`), before the generic upsert `fetch`:

```js
      // Reservation-lock hard gate (2026-08-10): the one transition on this
      // resource that can't be a blind merge -- two staff on two devices,
      // each holding a stale local copy showing 'Available', could otherwise
      // both pass their own client-side check and both upsert 'Reserved' for
      // different cases, silently overwriting each other (real risk: the
      // same physical casket/urn promised to two grieving families). Every
      // OTHER transition on this resource (release, mark Sold, catalog/unit
      // creation) keeps the existing blind-upsert semantics below -- this is
      // a narrow, resource+transition-specific gate. See
      // docs/superpowers/specs/2026-08-10-sairnlegacy-reservation-lock-design.md
      if (resource === 'leg_merch_units' && payload.status === 'Reserved') {
        const r = await fetch(rest(
          'leg_merch_units?license_hash=eq.' + enc(licHash) +
          '&merch_unit_id=eq.' + enc(String(payload.id)) +
          '&data->>status=eq.Available'
        ), {
          method: 'PATCH',
          headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
          body: JSON.stringify({ data: payload, updated_at: nowISO() })
        });
        if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlegacy data tables are not set up yet — run sql/sairnlegacy_data_schema.sql in Supabase first.' } }); return; }
        const rows = await r.json();
        if (!r.ok) return upstream(res, rows);
        if (!Array.isArray(rows) || rows.length === 0) {
          res.status(409).json({ error: { code: 'ALREADY_RESERVED', message: 'This unit could not be reserved -- it may have already been reserved or sold by someone else, or it has not finished syncing to the server yet.' } });
          return;
        }
        res.status(200).json({ ok: true, data: rows[0].data });
        return;
      }
```

- [ ] **Step 2: Syntax-check**

Run: `node --check api/sd-data.js`
Expected: no output, exit 0.

- [ ] **Step 3: Direct curl verification against the live endpoint**

Using the real demo license `LEG-PINNACLE-2026` (confirmed live and
provisioned with an empty `leg_merch_units` table this session):

```bash
# seed one Available unit directly
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer LEG-PINNACLE-2026' \
  -d '{"action":"write","resource":"leg_merch_units","payload":{"id":"MU-TEST-1","merch_id":"MC-TEST","unit_serial":"TEST-001","status":"Available"}}'

# first reservation -- expect 200 + updated row
curl -s -w '\nHTTP:%{http_code}\n' -X POST https://sairn.vercel.app/api/sd-data \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer LEG-PINNACLE-2026' \
  -d '{"action":"write","resource":"leg_merch_units","payload":{"id":"MU-TEST-1","merch_id":"MC-TEST","unit_serial":"TEST-001","status":"Reserved","reserved_for_case_id":"CS-A"}}'

# second reservation of the SAME unit -- expect 409 ALREADY_RESERVED
curl -s -w '\nHTTP:%{http_code}\n' -X POST https://sairn.vercel.app/api/sd-data \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer LEG-PINNACLE-2026' \
  -d '{"action":"write","resource":"leg_merch_units","payload":{"id":"MU-TEST-1","merch_id":"MC-TEST","unit_serial":"TEST-001","status":"Reserved","reserved_for_case_id":"CS-B"}}'
```

Expected: first reservation 200 with `data.reserved_for_case_id ===
"CS-A"`; second 409 with `error.code === "ALREADY_RESERVED"`. Read back
via `{"action":"read","resource":"leg_merch_units"}` and confirm the row
still shows `reserved_for_case_id:"CS-A"` — CS-B's write must not have
landed at all.

- [ ] **Step 4: Commit**

```
git add api/sd-data.js
git commit -m "fix: api/sd-data.js -- atomic check-and-set for leg_merch_units reservation

..."
```

---

### Task 2: `sairnlegacy.html` — honest rejection message

**Files:** Modify `sairnlegacy.html:1891-1906` (`confirmReserve()`)

- [ ] **Step 1: Write the implementation**

Replace the `st('leg_merch_units',list); ... var syncResult=await
sdnData(...)` tail of `confirmReserve()` with a direct fetch so the real
status/error code is visible to this call site only:

```js
async function confirmReserve(){
  var caseId=$('rvcase').value;
  if(!caseId){$('reserve-err').textContent='Select a case';return;}
  var list=merchUnits();
  var u=list.find(function(x){return x.id===mcReserveUnit;});
  if(!u){$('reserve-err').textContent='Unit not found';return;}
  if(u.status!=='Available'){$('reserve-err').textContent='This unit was just reserved by someone else -- pick a different unit';closeReserveModal();rMerch();return;}
  u.status='Reserved';u.reserved_for_case_id=caseId;u.reserved_at=legLocalToday();
  st('leg_merch_units',list);
  closeReserveModal();rMerch();
  var lic=legLicenseKey();
  if(!lic){toast('Reserved on this device only -- server sync not yet enabled for this app',5500);return;}
  try{
    var r=await fetch(DATA_API,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+lic},
      body:JSON.stringify({action:'write',resource:'leg_merch_units',app_id:APP_ID,payload:u})});
    var d=await r.json().catch(function(){return null;});
    if(r.status===409&&d&&d.error&&d.error.code==='ALREADY_RESERVED'){
      // Server rejected it -- someone else's reservation actually won. Roll
      // the local optimistic write back and tell staff the truth.
      u.status='Available';u.reserved_for_case_id='';u.reserved_at='';
      st('leg_merch_units',list);rMerch();
      toast(d.error.message,6000);
      return;
    }
    toast((r.ok&&d&&d.ok)?'Unit reserved for '+caseLabel(caseId):'Reserved on this device only -- server sync not yet enabled for this app',(r.ok&&d&&d.ok)?3500:5500);
  }catch(e){
    toast('Reserved on this device only -- server sync not yet enabled for this app',5500);
  }
}
```

Note: on the 409 path, the local optimistic `Reserved` write is rolled
back to `Available` — the earlier `st('leg_merch_units',list)` call
already made it locally visible before the network round-trip
completed (needed so `rMerch()` reflects the attempt immediately); this
correction keeps local state honest once the server's real answer comes
back, rather than leaving a phantom local `Reserved` that the server
never actually holds.

- [ ] **Step 2: Syntax-check**

```
python tools/checkblocks.py sairnlegacy.html
python tools/div_balance_check.py sairnlegacy.html
```
Expected: 0 failed blocks, `RESULT:PASS`.

- [ ] **Step 3: Live interaction test**

Through the real UI (`sairn.vercel.app/sairnlegacy`, `LEG-PINNACLE-2026`
demo key): add a catalog item and a unit, reserve it — confirm success
toast. Open a second reservation attempt on the same unit from a second
tab/injected session (or replay via `javascript_tool` against a second
tab sharing the same license) — confirm the honest rejection message
and that the panel shows the unit still reserved for the *first* case,
not flipped to the second.

- [ ] **Step 4: Commit**

```
git add sairnlegacy.html
git commit -m "fix: SAIRNlegacy -- confirmReserve() surfaces the real 409 rejection

..."
```

---

### Task 3: Push, live-verify, close the backlog entry

- [ ] **Step 1:** Full local re-check (`checkblocks.py`,
  `div_balance_check.py` on `sairnlegacy.html`; `node --check` on
  `api/sd-data.js`).
- [ ] **Step 2:** Push both commits.
- [ ] **Step 3:** Re-run Task 1 Step 3's curl sequence against the now-
  live endpoint (confirms the deployed function, not just local code).
- [ ] **Step 4:** Live UI test (Task 2 Step 3) against the deployed app.
- [ ] **Step 5:** Update `SAIRN-BACKLOG.md` — move this entry to a
  "Resolved" note (or remove it) with the real fix description and
  verification date, and correct the "same scope-class as SAIRNbuild"
  language now proven wrong (this fix required no schema migration and
  no multi-session build).
