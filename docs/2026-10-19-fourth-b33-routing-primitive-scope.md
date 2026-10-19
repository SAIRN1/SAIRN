# Routing primitive — phase 1 scope

**fourth / b33, 2026-10-19. Scope only. No app code is written by this document.**

**READ §1 BEFORE §2.** The archaeology that was supposed to precede this
document was run and read this batch, and it changed the answer. The question
was *"does routing code already exist anywhere."* It does. It is not on `main`,
its client half **is** on `main`, and that half is calling a server action that
has never existed there. That is the fact this scope is built on, and it also
makes this document's first phase a **repair**, not a greenfield build.

Every figure below names the command that produced it. Re-derive rather than
quote.

---

## 1. WHAT THE ARCHAEOLOGY FOUND

### 1.1 A complete, working route optimiser exists — on an abandoned branch

`git log --oneline -S"optimizeRoute" --all` surfaces **35169ea2**, *"Add
maps-optimize and maps-static actions to SAIRN Data Bridge for StoneDesk Field
Map"*, 2026-06-18. It adds 105 lines to `api/bridge.js`:

* a POST `?action=maps-optimize` taking `{ addresses: string[] }`;
* a call to Google's **Route Matrix** (`routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix`)
  with `travelMode: 'DRIVE'`, keyed server-side so `GOOGLE_MAPS_API_KEY` never
  reaches the browser;
* a **nearest-neighbour ordering** over the real drive-time matrix, starting
  from stop 0, with an explicit unreachable-pair fallback;
* a `savedMinutes` figure computed as *as-given order total minus optimised
  total*, floored at 0;
* and a sibling `?action=maps-static` that fetches the preview image
  server-side and returns it as a data URL, so the key never appears in a URL
  the browser could copy.

Its own comment explains why it does **not** use Google's
`optimizeWaypointOrder`: that feature is gated behind a manual Support
enablement request, and a nearest-neighbour ordering over real drive times does
not depend on a flag that might not be turned on. That is a judgment worth
keeping.

### 1.2 It is not on `main`, and never has been

```
git merge-base --is-ancestor 35169ea2 HEAD   # -> non-zero: NOT an ancestor
git branch -a --contains 35169ea2            # -> remotes/origin/claude/lucid-ptolemy-b73vu0
```

`main`'s `api/bridge.js` was built fresh on 2026-07-31 (`df84b213`) and its own
header says so — *"no api/bridge.js was ever committed"* at the time the
callers already assumed one existed. `grep -i "maps|optimize|GOOGLE_MAPS"
api/bridge.js` at HEAD returns **nothing**. The archive tree preserved 167
files from that branch (`39af4f5e`) but **not** `api/bridge.js`:
`grep -rln "maps-optimize" archive/` returns nothing.

So the implementation survives **only** in a commit on a branch nobody builds
from.

### 1.3 The client half IS on `main`, and it is calling into the void

| | |
|---|---|
| `stonedesk.html:12547` | `var FM_API = 'https://sairn.vercel.app/api/bridge';` |
| `stonedesk.html:12927` | `fmRunOptimize()` POSTs `?action=maps-optimize` |
| `stonedesk.html:12814` | `fmRenderMap()` POSTs `?action=maps-static` |

Neither call sends an `Authorization` header. On `main`, `api/bridge.js`
dispatches **any** POST that is not `proxy_get` to `handlePush`, which requires
a licence — so both calls land on the push handler and are refused.

**Live-verified this batch**, not inferred, via `tools/sairn_http.py` against
`https://sairn.vercel.app/api/bridge`:

```
maps-optimize  ->  HTTP 401 Unauthorized
maps-static    ->  HTTP 401 Unauthorized
GET /api/bridge -> HTTP 405 Method Not Allowed  (NO_READ_SIDE, by design)
```

### 1.4 The error message blames the wrong thing

`fmRunOptimize`'s catch arm says:

> *"Could not optimize route -- check the Maps API key is configured."*

and `fmRenderMap`'s says *"Map unavailable -- check GOOGLE_MAPS_API_KEY is
set."* **Neither is true.** The key is irrelevant: the request never reaches
code that reads it, because the action does not exist on this deployment. A
person acting on that message would go and check a Vercel environment variable
that is not the problem. This is the "silent failure wearing a diagnosis"
shape — worse than a bare failure, because it sends the reader somewhere else.

### 1.5 A latent second-order hazard in the same fall-through

`handlePush` upserts `{ license_hash, data }` into `bridge_data`. Today the two
maps calls carry no `Authorization` header, so they 401 before touching it.
**If a future change gave those calls the licence header the rest of the app
already holds, the fall-through would accept them as a push and upsert
`data: { addresses: [...] }` over that shop's stored row** — silently, with a
`200 ok`. The defect is not in the maps calls; it is that an unknown `?action=`
falls through to a *write* rather than being refused. That is worth closing
whatever happens to routing.

### 1.6 What else exists, and what does not

Searched at HEAD over all tracked files, and read:

* `route_order`, `stop_order`, `visit_order`, `waypoint`, `distance_matrix`,
  `dispatch_board` — **zero** real hits. Only this batch's and b32's own
  prose, plus the archived `sairntrade.html`.
* **Real geo primitives DO exist**, and one is production-grade:
  `sairngrounds.html:2793` `gcdHaversineM()` — great-circle distance on the
  WGS84 mean radius, with a per-fix `accuracy_m` discipline (the error band is
  *added*, never averaged; a combined band over 25 m yields no distance at
  all). `sairnsenior.html:3207` captures `lat`/`lng` for EVV clock-in/out and
  leaves them **null** rather than faked when permission is refused.
  `sairnlegacy` shares a live vehicle position (`leg_processions`, Tier A on
  confidentiality).
* **The archived `sairntrade.html`** has an `optimizeRoute()` that is a
  **Claude prompt with six hardcoded Westlake OH addresses in the user
  message** — a demo, not an algorithm. It is named here so nobody later
  mistakes it for prior art.

**Conclusion for item 3's question:** routing code exists, it is good, it is
unreachable, and its client half is live and broken.

---

## 2. SCOPE — PHASE 1

### 2.1 Shape: one shared module, not a per-app copy

A module under `api/_lib/`, called by `api/sd-data.js`'s existing
resource/action dispatch — **not** a new top-level endpoint, and **not**
`api/bridge.js`. Three reasons, all from `api/bridge.js`'s own header:

1. `api/bridge.js` is explicitly **StoneDesk-only** and its header warns that
   it is *not* the cross-app data path other apps mean.
2. `api/sd-data.js` is the real shared path — licence-scoped, session-gated,
   already read by ten apps.
3. `api/bridge.js` has no read side at all and answers 405 to GET.

Putting a cross-app primitive on `bridge.js` would repeat the naming collision
that file was annotated about.

### 2.2 Schema

Two tables. Names are app-neutral because the module is.

```sql
-- One planned run of stops for one assignee on one date.
create table rt_routes (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null,              -- 'stonedesk' | 'sairnroofing' | ...
  assignee_id   text not null,              -- the app's OWN employee/crew id; not re-keyed here
  route_date    date not null,
  status        text not null default 'planned',   -- planned | active | closed
  optimized_at  timestamptz,                -- NULL = never optimised; not 0, not now()
  saved_seconds integer,                    -- NULL = not computed. NEVER 0-as-unknown.
  source        text not null,              -- 'manual' | 'drive-matrix' | 'manual-after-optimize'
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, app_id, assignee_id, route_date)
);

-- One stop on that run. The ADDRESS is the input; the ORDER is the output.
create table rt_stops (
  id            uuid primary key default gen_random_uuid(),
  route_id      uuid not null references rt_routes(id) on delete cascade,
  license_hash  text not null,
  seq           integer not null,           -- 1-based position in the CURRENT order
  job_ref       text,                       -- the app's own job id, free-form, nullable
  address       text not null,
  lat           double precision,           -- NULL when not geocoded. Never 0,0.
  lng           double precision,
  accuracy_m    double precision,           -- carried if the point came from a device fix
  status        text not null default 'pending',   -- pending | done | skipped
  locked        boolean not null default false,    -- true = optimiser must not move it
  created_at    timestamptz not null default now(),
  unique (route_id, seq)
);
```

**Four schema decisions that are the point, not decoration:**

* **`saved_seconds` is nullable and NULL means not computed.** The archived
  implementation floored it at `Math.max(0, ...)`, which makes "we could not
  tell" and "we saved nothing" the same value on screen. They are different
  facts and the column must keep them different.
* **`optimized_at` NULL means never optimised.** A route that has only ever
  been hand-ordered must be able to say so; `source` says which.
* **`lat`/`lng` nullable, never `0,0`.** Null Island is a real failure mode and
  `sairnsenior.html:3202` already has the right instinct — *"geolocation
  permission is disclosed (lat/lng left null), never faked."*
* **`locked`** exists because a real day has fixed appointments. An optimiser
  that reorders a 9 AM commitment is worse than no optimiser.

**Grants.** `grant select, insert, update, delete on rt_routes, rt_stops to
service_role;` — **no `truncate`, no `references`, no `trigger`.** Read
`sairn-grant-sweep` before writing the line; do not copy it from here.

**Tier.** Both rows go into `docs/CRITICALITY-TIERS.md` **before** the code
lands, not after. `rt_stops` carries a customer address joined to a named
assignee and a date — that is a location record about identifiable people, the
same class that took `grd_cart_orders` and `leg_processions` to **A** on
confidentiality. Expect **A on confidentiality**; argue integrity separately.

### 2.3 API surface

Four actions on `api/sd-data.js`, resource `routes`:

| action | body | returns | notes |
|---|---|---|---|
| `read` | `{ app_id, assignee_id, route_date }` | the route and its stops in `seq` order | 404 → empty route, not an error |
| `upsert` | `{ app_id, assignee_id, route_date, stops: [{job_ref, address, lat?, lng?, locked?}] }` | the stored route | replaces the stop set; `seq` is assigned in the order given |
| `reorder` | `{ route_id, seq: [stop_id, ...] }` | the stored route | **manual** reorder; sets `source='manual'`, leaves `optimized_at` alone |
| `optimize` | `{ route_id }` | `{ order, saved_seconds \| null, basis }` | the only action that costs money |

**`optimize` must answer three things explicitly and never fold them together:**

* `basis: 'drive-matrix'` — a real Route Matrix answer was used.
* `basis: 'unavailable'` — the matrix could not be reached, no key is
  configured, or a pair is unreachable. **The stored order does not change**,
  `saved_seconds` stays NULL, and the response says which of those it was.
  This is the rule from `CLAUDE.md`: *could not run* is a third state and is
  never folded into a pass.
* It **never returns a reordering it did not compute.** No fallback to the
  as-given order presented as an optimisation.

`locked` stops hold their `seq`; the optimiser orders only the unlocked ones
into the remaining slots. `status='done'` stops are never moved — StoneDesk's
`fmRunOptimize` already does exactly this (`notDone` / `done` split at
`stonedesk.html:12920-12923`) and that behaviour is being *preserved*, not
invented.

**Auth:** licence + session, same gate as every other `sd-data.js` resource.
Not licence-only. An address list joined to a named employee is not shop
metadata.

### 2.4 The one app to wire in first: **StoneDesk**

Not because it is the biggest. Because **its client half already exists, is
already written against this exact call shape, and is currently broken.**

* `fmRunOptimize()` already builds `addrs` from not-done stops, already
  consumes `{ order, savedMinutes }`, already persists into `sdFieldOrder`,
  already re-renders, already splits done/not-done, and already has a
  silent-reoptimise path (`fmAutoReoptimize`).
* So phase 1 against StoneDesk is **three edits**, not a feature:
  1. point `fmRunOptimize` at `sd-data.js` resource `routes`, action
     `optimize`, with the licence and session headers the app already holds;
  2. replace both misleading catch messages with what actually happened —
     and have the `basis: 'unavailable'` arm say *which* unavailability;
  3. read `saved_seconds` and render nothing at all when it is NULL, rather
     than "saves ~0 min".
* Candidates ranked by how much they'd need built from zero (measured by
  routing/assignment vocabulary at HEAD): StoneDesk has `fmGetOrderedStops`,
  `sdFieldOrder`, 68 `route` hits and 57 `dispatch` hits; `sairnmechanical` has
  22 `dispatch` and 6 `route`; `sairnscape` 13 `route`, 4 `dispatch`, and its
  dashboard subtitle already reads *"Today's jobs and routes across all
  customers"*; `sairngrounds` 6 `route`, 3 `dispatch`, **plus the only real
  haversine on the platform**; `sairnroofing` has **1** `route` hit and would
  be a build from zero.

**`sairngrounds` is the second app, and for a reason worth writing down:** it
already owns `gcdHaversineM()` and the accuracy-band discipline around it. When
`basis: 'unavailable'` fires, a straight-line ordering is a *legitimate* second
basis — but only if it is labelled `basis: 'great-circle'` and never allowed to
masquerade as drive time. Grounds already has the code and, more importantly,
already has the habit.

### 2.5 Explicitly NOT in phase 1

Said out loud so a later session does not read silence as an omission:

* **No geocoding.** Addresses go to the matrix as strings, as the archived
  implementation did. `lat`/`lng` are carried when an app already has them.
* **No live traffic, no time windows, no multi-day, no capacity constraints.**
* **No crew/tech *assignment*.** Phase 1 orders the stops a human already
  assigned. Deciding *who* goes is a different problem with a different failure
  mode and must not ride along in the same scope.
* **No new map rendering.** `maps-static` is a separate question; see §3.
* **No per-app copy of this module, ever.** That is the whole point.

---

## 3. THE REPAIR THAT IS DUE REGARDLESS

Three items, independent of whether phase 1 is built. **None is claimed done
here; each is a routable open item.**

1. **`api/bridge.js` must refuse an unknown `?action=` rather than falling
   through to `handlePush`.** §1.5. A write is the wrong default for a typo.
2. **StoneDesk's two Field Map error messages must stop blaming
   `GOOGLE_MAPS_API_KEY`.** §1.4. Whatever replaces the call, the message that
   points a reader at the wrong environment variable is a defect today.
3. **`maps-static` has no route forward in this scope and that is a decision,
   not an oversight.** Phase 1 covers ordering. The preview image is a separate
   call with a separate cost and a separate key, and `fmRenderMap` will keep
   failing until someone decides whether a map image is wanted at all. Until
   then it should say *"Route preview is not available in this build"* rather
   than naming a key.

---

## 4. WHAT THIS DOCUMENT DOES NOT ESTABLISH

* **No code was written and none was run.** This is scope.
* **The live 401s prove the deployed endpoint refuses those actions.** They do
  **not** prove `GOOGLE_MAPS_API_KEY` is unset in Vercel — that was not
  checked and is a different question.
* **The archived implementation was read, not tested.** It has never run in
  this clone, and `Math.max(0, ...)` on `savedMinutes` is a defect inherited
  from it that §2.2 corrects rather than copies.
* **The per-app vocabulary counts in §2.4 are a ranking aid, not an audit.**
  `grep -o -i` over words like `route` and `assign` over-matches; they were
  used to order candidates, and the StoneDesk conclusion rests on the three
  named functions, not on the counts.

---

*Related: `docs/cloud-research/2026-10-19-three-recurring-blockers.md`, which
states whether this document closes the routing blocker. It does not fully —
read §3 there.*
