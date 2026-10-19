# Routing phase 1 — what landed, and the one piece that is blocked

**fourth / b34, 2026-10-19.** Follows
`docs/2026-10-19-fourth-b33-routing-primitive-scope.md`, which is the design
this implements, and `docs/cloud-research/2026-10-19-three-recurring-blockers.md`,
which named the four conditions that close Blocker C.

**Read §3 first if you hold `api/sd-data.js`.** One handler branch is the only
thing standing between this and a working endpoint, it is written out in full
and ready to paste, and it is **not applied** because that file is claimed.

---

## 1. WHAT IS DONE

| | file | state |
|---|---|---|
| tier rows, **written before any code** | `docs/CRITICALITY-TIERS.md` | `rt_routes` + `rt_stops`, **A / A**, in a new `### routes` section |
| schema | `sql/rt_routes_schema.sql` | NEW — **not run against Supabase**, see §4 |
| the module | `api/_lib/routes.js` | NEW — four actions' worth of logic, three-state basis |
| its suite | `api/_lib/routes.test.js` | NEW — **56 arms, 56 passing**, including two sabotage controls |
| resource registry | `api/_resources/routes.js` + one line in `index.js` | NEW |
| first consumer | `stonedesk.html` `fmRunOptimize()` | repointed |
| second consumer | `sairngrounds.html` Scheduling panel | NEW — Route order for a crew's day |

**The four closing conditions from the blockers page, scored honestly:**

1. **Tier the two resources before the code — DONE.** And the tier is
   mechanically enforced rather than decorative; see §2.
2. **The shared module lands — DONE as a module, NOT as a reachable endpoint.**
   §3.
3. **Repoint StoneDesk and live-verify against the deployed URL — CLIENT DONE,
   LIVE VERIFICATION NOT POSSIBLE AND NOT CLAIMED.** §4.
4. **A second app proves it is shared — DONE in code, unverified at runtime for
   the same reason as 3.**

**So Blocker C is NOT closed.** It is closer by three conditions out of four,
and the fourth is a live check nobody can run until §3 and §4 are both resolved.

---

## 2. THE TIER IS ENFORCED, NOT JUST WRITTEN — AND FINDING THAT OUT FOUND A GAP

`rt_routes` / `rt_stops` are **Tier A on confidentiality**: `rt_stops` joins a
street address to a named assignee and a date, which is a record of where an
identifiable person was at a known time. Same class that took
`grd_cart_orders` and `leg_processions` from B to A.

The obvious home for a cross-app resource was `api/_resources/shared.js`.
**It would have been invisible there.** `apps_with_registries()` in
`tools/criticality_tier_check.py` skips that file by name:

```python
if app in ('index', 'shared'):
    continue
```

so the completeness arm that caught `sairnsenior/sen_period_closings` cannot
see anything declared in it. **Measured: all seven resources in `shared.js` —
`profile`, `memory`, `employees`, `slabs`, `render_usage`, `shared_knowledge`,
`employee_profile` — have no row in the register, and the checker reports no
finding about any of them.** That is a fail-open skip: CLEAN over seven
resources it was never shown reads exactly like a pass.

**Two of the seven are not obviously B** — `employees` is the cross-app HR
roster and `employee_profile` is a manager-set record about a named person.
No tier is asserted for any of them here; the gap is recorded in the register's
own gaps section as work, not closed.

`api/_resources/routes.js` therefore registers as its own `app`, so the checker
enumerates it. `APPS_WITH_REGISTRIES` now reads **18 for 17 apps**, and that
discrepancy is the point rather than an error.

**Checker, before and after:**

```
before: RESOURCE_ROWS:391  TIER_A:276  PROBLEMS:6
after : RESOURCE_ROWS:393  TIER_A:278  PROBLEMS:4
```

Zero new problems. The two that went away are pre-existing HEADLINE drifts in
the sentence this edit had to move anyway, re-derived from the checker's own
output rather than adjusted by the size of the edit. **The remaining 4 are not
mine** — three are `sairnscape` rollup drift and one is
`sairnsenior/sen_period_closings` having no row.

---

## 3. BLOCKED — THE `api/sd-data.js` HANDLER BRANCH

**`api/sd-data.js` is claimed by cody on b26** (*"convert the 151/57 sibling
NOT_PROVISIONED guards … to the shipped notProvisioned()/notProvisionedDecide()
pattern"*). `sairn_claim.py check` answers **BLOCKED — same file or resource:
api/sd-data.js**, and the tool's own instruction is *"DO NOT start this. Flag it
back."* It was not touched. `git status` shows no modification to it.

**Until this branch exists, `rt_routes` has no handler and the endpoint cannot
answer** — the registry entry only gets a request past the allowlist.

### The branch, ready to paste

Drop into `api/sd-data.js` alongside the other per-resource branches, inside the
handler where `licHash`, `headers`, `rest`, `enc`, `req` and `res` are in scope.

```js
// ── SHARED ROUTING PRIMITIVE (rt_routes / rt_stops) ────────────────────────
// Module: api/_lib/routes.js. Schema: sql/rt_routes_schema.sql.
// Tier A on confidentiality both rows — docs/CRITICALITY-TIERS.md, `routes`.
// Consumers: stonedesk.html fmRunOptimize(), sairngrounds.html
// grdRouteOptimize(). Neither app owns it.
//
// LICENCE **AND** SESSION on every verb, not licence-only: a licence proves
// the shop, and an address list joined to a named employee is not shop
// metadata.
if (resource === 'rt_routes' || resource === 'rt_stops') {
  const RT = require('./_lib/routes.js');
  const p = payload || {};
  const session = verifySessionToken(tokenFromRequest(req), licHash, p.app_id);
  if (!session) {
    res.status(403).json({ error: { code: 'FORBIDDEN', message: 'A valid employee session is required' } });
    return;
  }
  const keyErr = RT.validateRouteKey(p);
  if (keyErr) { res.status(400).json({ error: { code: 'BAD_REQUEST', message: keyErr } }); return; }

  const routeFilter = 'license_hash=eq.' + enc(licHash)
    + '&app_id=eq.' + enc(p.app_id)
    + '&assignee_id=eq.' + enc(p.assignee_id)
    + '&route_date=eq.' + enc(p.route_date);

  async function loadRoute() {
    const r = await fetch(rest('rt_routes?' + routeFilter + '&select=*&limit=1'), { headers });
    if (r.status === 404 || r.status === 400) return { notProvisioned: true };
    const rows = await r.json();
    if (!r.ok) return { upstream: rows };
    return { row: (Array.isArray(rows) && rows[0]) || null };
  }
  async function loadStops(routeId) {
    const r = await fetch(rest('rt_stops?route_id=eq.' + enc(routeId)
      + '&license_hash=eq.' + enc(licHash) + '&select=*&order=seq.asc'), { headers });
    if (r.status === 404 || r.status === 400) return { notProvisioned: true };
    const rows = await r.json();
    if (!r.ok) return { upstream: rows };
    return { rows: rows || [] };
  }

  if (action === 'read') {
    const got = await loadRoute();
    if (got.notProvisioned) { res.status(200).json({ ok: true, data: null, provisioned: false }); return; }
    if (got.upstream) return upstream(res, got.upstream);
    if (!got.row) { res.status(200).json({ ok: true, data: null, provisioned: true }); return; }
    const st = await loadStops(got.row.id);
    if (st.notProvisioned) { res.status(200).json({ ok: true, data: null, provisioned: false }); return; }
    if (st.upstream) return upstream(res, st.upstream);
    res.status(200).json({ ok: true, data: { route: got.row, stops: st.rows }, provisioned: true });
    return;
  }

  if (action === 'upsert') {
    const stopErr = RT.validateStops(p.stops);
    if (stopErr) { res.status(400).json({ error: { code: 'BAD_REQUEST', message: stopErr } }); return; }
    const rr = await fetch(rest('rt_routes?on_conflict=license_hash,app_id,assignee_id,route_date'), {
      method: 'POST',
      headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
      body: JSON.stringify({
        license_hash: licHash, app_id: p.app_id, assignee_id: p.assignee_id,
        route_date: p.route_date, updated_at: new Date().toISOString()
      })
    });
    const rrows = await rr.json();
    if (!rr.ok) return upstream(res, rrows);
    const routeId = (Array.isArray(rrows) ? rrows[0] : rrows).id;
    // REPLACE the stop set. The delete is bounded by route_id -- it reaches
    // only the stops of one route of one licence. See the grant note in
    // sql/rt_routes_schema.sql for why this is a hard delete and not a flag.
    await fetch(rest('rt_stops?route_id=eq.' + enc(routeId) + '&license_hash=eq.' + enc(licHash)),
      { method: 'DELETE', headers });
    const toInsert = p.stops.map((s, i) => ({
      route_id: routeId, license_hash: licHash, seq: i + 1,
      job_ref: s.job_ref || null, address: s.address,
      lat: s.lat === undefined ? null : s.lat,
      lng: s.lng === undefined ? null : s.lng,
      accuracy_m: s.accuracy_m === undefined ? null : s.accuracy_m,
      status: s.status || 'pending', locked: s.locked === true
    }));
    const si = await fetch(rest('rt_stops'), {
      method: 'POST',
      headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
      body: JSON.stringify(toInsert)
    });
    const srows = await si.json();
    if (!si.ok) return upstream(res, srows);
    res.status(200).json({ ok: true, route_id: routeId, stops: srows });
    return;
  }

  if (action === 'reorder') {
    // MANUAL reorder. Sets source='manual' and deliberately does NOT touch
    // optimized_at or saved_seconds -- a human reordering a route does not
    // invalidate the record that an optimiser once ran, and it does not
    // create a saving either.
    const got = await loadRoute();
    if (got.upstream) return upstream(res, got.upstream);
    if (!got.row) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No route for that app/assignee/date' } }); return; }
    const st = await loadStops(got.row.id);
    if (st.upstream) return upstream(res, st.upstream);
    const ordered = RT.applyOrder(st.rows, (p.seq || []).map(
      (id) => st.rows.findIndex((r) => String(r.id) === String(id))));
    if (!ordered) { res.status(400).json({ error: { code: 'BAD_REQUEST', message: 'seq must list every stop of this route exactly once' } }); return; }
    for (const s of ordered) {
      await fetch(rest('rt_stops?id=eq.' + enc(s.id)), {
        method: 'PATCH', headers, body: JSON.stringify({ seq: s.seq })
      });
    }
    await fetch(rest('rt_routes?id=eq.' + enc(got.row.id)), {
      method: 'PATCH', headers,
      body: JSON.stringify({ source: 'manual', updated_at: new Date().toISOString() })
    });
    res.status(200).json({ ok: true, stops: ordered });
    return;
  }

  if (action === 'optimize') {
    const stopErr = RT.validateStops(p.stops);
    if (stopErr) { res.status(400).json({ error: { code: 'BAD_REQUEST', message: stopErr } }); return; }
    const result = await RT.optimize(p.stops, {});
    // THE THIRD STATE IS RETURNED AS A 200, NOT AN ERROR STATUS, and that is
    // deliberate: "I could not compute an ordering" is a successful answer to
    // the question asked. A 502 here would make the client's catch arm the
    // place this lands, which is exactly where the old maps-optimize call died
    // under a message about the wrong environment variable.
    // NOTHING IS WRITTEN when basis is 'unavailable' -- the stored order must
    // not move.
    if (result.basis !== 'unavailable') {
      const rr = await fetch(rest('rt_routes?on_conflict=license_hash,app_id,assignee_id,route_date'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, app_id: p.app_id, assignee_id: p.assignee_id,
          route_date: p.route_date,
          optimized_at: new Date().toISOString(),
          saved_seconds: result.saved_seconds,   // NULL means NOT COMPUTED
          source: result.basis,
          updated_at: new Date().toISOString()
        })
      });
      const rrows = await rr.json();
      if (!rr.ok) return upstream(res, rrows);
    }
    res.status(200).json(Object.assign({ ok: true }, result));
    return;
  }

  res.status(400).json({ error: { code: 'BAD_REQUEST', message: 'action must be read, upsert, reorder or optimize for ' + resource } });
  return;
}
```

**Also needed, in the same edit:** `'optimize'`, `'upsert'` and `'reorder'` are
verbs beyond `read`/`write`, so they must be declared as `extraActions` —
`api/_resources/index.js` refuses a verb declared for a resource its own module
does not register, and `api/_resources/routes.js` owns both names. The
declaration belongs in `api/_resources/routes.js`:

```js
extraActions: {
  rt_routes: ['upsert', 'reorder', 'optimize'],
},
```

**That line is NOT in the file yet, on purpose.** `api/_resources/index.js`
asserts extra actions at load; declaring verbs with no handler branch would make
the registry assert a capability that answers 400. It goes in with the branch,
not before it.

---

## 4. WHAT IS NOT VERIFIED, AND WHY — STATED RATHER THAN SOFTENED

**The endpoint was probed live and the probe could not answer the question.**
`tools/sairn_http.py` against `https://sairn.vercel.app/api/sd-data`:

```
rt_routes  read, no auth  -> 401 {"error":{"code":"NO_LICENSE", ...}}
rt_stops   read, no auth  -> 401 {"error":{"code":"NO_LICENSE", ...}}
employees  read, no auth  -> 401   (control: a resource that definitely exists)
zzz_not_a_resource        -> 401   (control: one that definitely does not)
```

**Both controls answer identically, which is the finding.** The licence gate
fires ahead of resource dispatch, so an unauthenticated probe cannot
distinguish a registered resource from an unregistered one in either direction.
Going further would mean entering a real licence key, which is not something
this session does.

So: **no live verification of items 3 or 4 is claimed.** What is claimed is
exactly what was checked —

* `node api/_lib/routes.test.js` → **56 passed, 0 failed**
* `python tools/checkblocks.py stonedesk.html` → **131 blocks, 0 failed**
* `python tools/checkblocks.py sairngrounds.html` → **5 blocks, 0 failed**
* `python tools/criticality_tier_check.py` → **PROBLEMS 6 → 4**, rows 391 → 393

**And `sql/rt_routes_schema.sql` HAS NOT BEEN RUN.** Both tables are absent from
Supabase until Michael runs it, so even with §3's branch applied the endpoint
would answer `provisioned: false` rather than data. That is the correct
behaviour and it is still not a working feature.

**THE CLIENT HALVES ARE SAFE TO SHIP BEFORE ANY OF THAT, which is why they
were shipped.** Both consumers handle `basis:'unavailable'` and a null response
as first-class answers that say *the stored order is unchanged* and name the
reason. That path has to exist regardless of whether the endpoint ever answers,
and it is a strict improvement on what StoneDesk did before: a dead call to an
action that never existed on `main`, under a message telling the reader to check
a Maps API key the request never reached.

---

## 5. ONE THING TOUCHED THAT WAS DECLARED NOT MINE, AND THE REASON

The batch instruction placed *"StoneDesk's two wrong Field Map error messages"*
out of scope as `api/`, hank's lane. **Two corrections, offered rather than
assumed:**

1. **Those messages are not in `api/`.** They are in `stonedesk.html` at the
   `.catch` arms of `fmRunOptimize` and `fmRenderMap`.
2. **One of them is inside the function item 3 asked me to repoint.** Changing
   where `fmRunOptimize` sends its request necessarily rewrites its catch arm;
   leaving the old text would have meant a call to the new endpoint failing
   under a message about a Maps API key that is now doubly irrelevant.

**`fmRenderMap` — the `maps-static` one — WAS NOT TOUCHED.** It still names
`GOOGLE_MAPS_API_KEY`, it still calls the dead bridge action, and it is still
somebody's to fix. **And `api/bridge.js`'s unknown-`?action=`-reaches-a-WRITE
hazard was not touched either** — that is the real `api/` item and it remains
routed to hank, unclaimed and unstarted.

---

## 6. EXACT NEXT STEP, PER ITEM

1. **cody (or whoever next holds `api/sd-data.js`):** paste §3's branch and the
   `extraActions` declaration. Nothing else in that file changes.
2. **Michael:** run `sql/rt_routes_schema.sql` in the Supabase SQL editor. Until
   then both resources answer `provisioned: false`.
3. **After 1 and 2:** live-verify against the deployed URL with a real session —
   not a clean `git push`, and not a local run. That is closing condition 3 and
   it is the one still open.
4. **Then:** SAIRNscape, SAIRNroofing and SAIRNmechanical are the remaining
   field apps with a day-of-stops shape. Each is a consumer, not a copy.
5. **Still open and not mine:** `api/bridge.js`'s write-hazard; `fmRenderMap`'s
   message and the `maps-static` decision; the seven untiered `shared.js`
   resources (§2); `sd_field_stops` at B/B against `rt_stops` at A/A.
