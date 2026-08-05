# SAIRNgrounds — Scope

**Phase 1 scope, decided 2026-08-05.** Confirmed this session: SAIRNgrounds
and SAIRNscape are two distinct products (not one app under two names — see
`SAIRN-SESSION*-HANDOFF.md` investigation same day). No prior SAIRNgrounds
build exists anywhere — verified against full git history (all branches, all
remotes) and the local filesystem, zero hits. This is a ground-up build, not
a recovery. This doc covers **Phase 1 only**; later phases are listed at the
bottom as known future scope, not built here.

| # | Decision |
|---|---|
| 1 | Supabase table prefix: **`grd_*`** — no collision with any existing app prefix (`sd_`/`bld_`/`sb_`). |
| 2 | Licence prefix: **`GRD-`** — not yet provisioned; provisioning is Michael's step (service-role/Supabase dashboard access), same as every prior app. |
| 3 | `api/claude.js` `KNOWN_APP_IDS` does **not** yet include `'sairngrounds'` — verified by direct read. This is a required, small server change before the AI proxy will accept this app's calls (unlike SAIRNbuild, which didn't need one). |
| 4 | `app_id`: `sairngrounds`. Colour: not yet assigned in `sairn-guardian-v2`'s App File Map — needs adding alongside the file map entry. |

---

## 1. Target persona + trade

**Trade:** golf courses, HOAs, and commercial/large-property landscaping —
distinct from SAIRNscape (general residential/small-commercial landscapers).
The defining differentiator is scale and specialization: acreage-level
turf/irrigation management and, specifically, golf course operations.

**Primary persona — the golf course superintendent / grounds manager.**
Runs a crew across 100+ acres, manages irrigation across dozens of zones,
answers to a green committee or HOA board on budget and course conditions.
Daily pain, in priority order:
1. **Is today a go/no-go day for the crew** — weather-driven, course-wide.
2. **Where is every job/task across the property**, not per-customer the way
   a small landscaper thinks about it — per-hole, per-zone, per-area.
3. **Quoting/estimating for HOA and commercial contract work** — the
   business-development side that funds the operation.
4. **Irrigation zone status** — deferred to a later phase (§ Future scope)
   but the reason the Weather Command Engine matters this early: irrigation
   decisions are weather-driven.

**Deliberately out of scope for Phase 1:** the Golf Course Module's full
hole-by-hole GPS mapping (course-plotting-by-walking), ponds/lakes/creeks,
irrigation zone control, Crew Training Academy, Invasive Species Management,
Property Ecosystem Health Report, DreamClose™. Listed in full under
**Future scope** below so they aren't forgotten, not built here.

---

## 2. Phase 1 panel list

Mirrors the convention every other app follows: a business-operation spine
first, proven before breadth. Reuses StoneDesk/SAIRNbuild's verified spine
shape (directory → intake → quote) rather than inventing a new one.

| Panel | id | Purpose | Status |
|---|---|---|---|
| Dashboard | `dashboard` | Every active job/property with status, weather go/no-go banner (reads the Weather Command Engine below). | Not built |
| AI Assistant | `ai` | Claude via `/api/claude`, `app_id:'sairngrounds'` — scope questions, treatment/product lookups. | Not built |
| Property Directory | `properties` | The core record: golf course / HOA / commercial property, contact, acreage, contract status — this app's equivalent of a customer directory, named for what this persona actually manages (a *property*, not a household customer). | Not built |
| Job Intake | `intake` | New job/work-order capture against a property: scope requested, target date, site notes. | Not built |
| Quoting / Estimating | `quotes` | Line-item quote builder for HOA/commercial contract work, Low/Mid/High presentation — same proven shape as StoneDesk's Quote Builder, adapted to acreage/contract line items instead of slab sqft. | Not built |
| Golf Course Module | `golfcourse` | **Phase 1's defining differentiator, scoped narrow for this phase:** per-hole/per-zone status list (name, acreage, last-serviced date, condition note) as a real, computed-from-data view. GPS walk-mapping and moving-green tracking are explicitly **deferred** (see Future scope) — this phase ships the data model and a manually-entered status board, not the AR/GPS capture tool. | Not built |
| Weather Command Engine | *(topbar, not a panel — cross-cutting)* | **Confirmed portable, real, working reference implementation exists:** `stonedesk.html:14153-14198`, `sairnLoadWeather()`, exec-role-gated topbar element (`#sairn-weather-bar`, `#sairn-wx-icon/temp/desc/status`), Open-Meteo API (`api.open-meteo.com`, free, no key), geolocation-based, go/no-go threshold logic already built (`temp>32 && temp<100 && wind<25 && not-rain/snow/storm`). This is a direct port, not a new build — more relevant here than anywhere else in the platform, since course-wide crew go/no-go is this persona's #1 daily question (§1). | Confirmed available, not yet ported |

**7 Phase-1 surfaces** (5 panels + AI Assistant + Dashboard), plus the
Weather Command Engine as cross-cutting infrastructure rather than an 8th
panel — matching SAIRNbuild's precedent of treating Weather as topbar, not
a panel.

---

## 3. Data model (Phase 1 tables only)

Follows the existing tenancy convention (`license_hash`-keyed, app-owned;
JSONB `data` blob per row rather than wide columns — the `sd_slabs`/
`bld_jobs` pattern, chosen specifically because a JSONB payload cannot drift
out of sync with the client's assumed schema, per the `employees` incident
documented in `SAIRNBUILD-SCOPE.md` §3).

```
grd_properties   property_id, license_hash, updated_at, data{
                   name, type (golf|hoa|commercial), contact_name,
                   contact_email, contact_phone, acreage, address,
                   contract_status, notes }

grd_jobs         job_id, license_hash, property_id, updated_at, data{
                   scope_requested, target_date, status, site_notes }

grd_quotes       quote_id, license_hash, property_id, updated_at, data{
                   line_items[], total_low, total_mid, total_high,
                   status (draft|sent|accepted|rejected), valid_until }

grd_golf_zones   zone_id, license_hash, property_id, updated_at, data{
                   hole_or_zone_name, acreage, last_serviced,
                   condition_note }
```

**Unique constraints:** `UNIQUE (license_hash, <entity>_id)` on every table
above, required and probe-verified before client code depends on it — not
assumed present. Same standing caution as `SAIRNBUILD-SCOPE.md` §3.

---

## 4. Shared infrastructure — reuse vs new

### Reused unchanged
| Component | Note |
|---|---|
| `api/_lib/license.js` | Untouched — single source of truth. |
| Weather Command Engine logic | Ported from `stonedesk.html:14153-14198`, not rebuilt — same Open-Meteo call, same go/no-go thresholds. |
| Pattern 13 entitlement gate | `sd-data.js`'s existing 402/paid-bypass logic applies as-is. |

### Required server changes (small, before app is usable)
| Component | Change |
|---|---|
| `api/claude.js` `KNOWN_APP_IDS` | Add `'sairngrounds'` — currently absent, verified by direct read. Without this, every AI Assistant/quote-drafting call in this app will be rejected. |
| `api/sd-data.js` (or equivalent) `RESOURCES` | Add `properties`, `jobs`, `quotes`, `golf_zones` — each a read+write branch following the existing `profile`/`slabs` pattern verbatim, per `SAIRNBUILD-SCOPE.md` §4's precedent. |
| `vercel.json` | Add `sairngrounds.html` to `buildCommand` and a `/sairngrounds$` route — currently absent (confirmed: this is why `sairngrounds.vercel.app/sairngrounds` 404s today, there's nothing deployed). |
| `sairn-guardian-v2` App File Map | Add `sairngrounds.html` entry, colour TBD. |

### New, client-side only
| Component | Note |
|---|---|
| `sairngrounds.html` | Single-file app, per the reference architecture. Auth gate / nav shell / data-layer helper (`grdData()`, `grdLicenseKey()`) built fresh — **correction to Michael's framing:** `sairn-app-scaffold` does **not** actually contain a ready-made auth-gate/nav-shell/data-layer template; it currently covers only the photo→Claude→structured-output pattern (verified by reading the skill directly). The smallest existing full app, `sairnbiz.html` (141KB/1825 lines), is the more useful structural reference for auth/nav/data-layer conventions — `sairnscape.html`'s current shell (marketing page + chat demo, 63KB) is explicitly **not** architecture to copy, per this session's own scoping decision. |
| Licence gate | Prefix allowlist must include `'GRD-'` once §4a-equivalent provisioning is done. |

### Licence provisioning — Michael's step, not mine
Same as every prior app: I cannot provision a `license_keys` row (requires
service-role/Supabase dashboard access). One `GRD-*` row needs creating and
endpoint-verified (`curl` against `/api/sd-data` returning `200`, not `401`)
before the client gate is written against it.

---

## 5. Future scope (explicitly deferred, not forgotten)

- Crew Training Academy
- Invasive Species Management
- Property Ecosystem Health Report
- DreamClose™
- Ponds/lakes/creeks (larger aquatic features)
- Irrigation technology / zone control
- Course-plotting-by-walking (GPS/AR hole-layout mapping, moving greens) —
  shared build with SAIRNscape's AR walk-and-design; build once, decide
  which app gets it first once both have their Phase 1 spine live.

### 5a. Golf Caddie differentiation package — CONFIRMED, Phase 2+, not built now

Approved 2026-08-05 as the app's full player-facing differentiator, layered
on top of the Phase 1 Golf Course Module (`golfcourse`, §2, which is the
*operations* side — manually-entered per-hole/zone status). This package is
the *player-facing* side and is deliberately sequenced after the Phase 1
business-operation spine is live — same "don't attempt the full thing in
one pass" discipline applied everywhere else in this doc.

1. **Base layer:** phone GPS player-position tracking + shot-distance-by-
   position-delta (mark position before a shot, mark again after — distance
   computed from the delta, no separate hardware/sensor needed) + licensed
   course mapping data (Golf Intelligence API or equivalent — vendor/cost
   not yet evaluated) + AI distance-to-pin and shot-tips using that data.
2. **Live course conditions feeding AI tips** — recently-cut greens, moved
   pin positions, wet bunkers — sourced from the *same operational data*
   course staff already enter through the Phase 1 Golf Course Module, not
   a separately maintained feed. This is the direct dependency that makes
   Phase 1's `golfcourse` panel a prerequisite, not just a nice-to-have
   before this package starts.
3. **Weather Command Engine wired into live player advice** — wind,
   incoming storm, heat — not just the course-wide go/no-go banner Phase 1
   ships; this extends the same engine (§2's cross-cutting row) into
   per-shot advice.
4. **On-course revenue:** order food/drinks to the cart based on live GPS
   position, book the next tee time mid-round, contextual pro-shop
   upsells.
5. **Operational value back to the course:** anonymized pace-of-play data
   and usage patterns feeding maintenance/scheduling decisions — closes
   the loop back into the same operations side Phase 1's Golf Course
   Module owns.

**Sequencing dependency, stated explicitly:** items 2 and 5 both assume
Phase 1's `golfcourse` panel is live and holding real data — this package
cannot honestly ship ahead of Phase 1's operations side without either
faking the conditions feed or duplicating data entry, both of which this
project's standing anti-fabrication rule rules out.

---

## 6. Verification standard for the build

Non-negotiable, inherited from every prior app: `node --check` per script
block before any push (project standing rule, never bulk find-replace);
full `sairn-guardian-v2` Check 0 + 26 checks before pushing; live-verify
against the deployed URL after push, never assumed from a clean `git push`
alone. Nothing in this doc is "built" until it passes both.
