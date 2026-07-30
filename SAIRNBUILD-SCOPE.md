# SAIRNbuild — Scope

**Decisions FINALIZED 2026-07-30.** The four open items in §6 are resolved and
folded into the body below. §6 is retained as a decision record rather than
deleted, so the reasoning survives.

| # | Decision |
|---|---|
| 1 | Supabase table prefix: **`bld_*`** |
| 2 | Licence prefix: **`BLD-`**, with one real `license_keys` row provisioned *before* the gate is written |
| 3 | Build order: **Dashboard → Job Board → Job Costing → Change Orders**, then the rest |
| 4 | **Bids & Proposals deferred out of v1** — v1 is 16 panels, not 17 |

**Status: scope only. No code exists.** `sairnbuild.html` has never existed in
this repo's history — confirmed via `git ls-tree -r origin/main -- '*.html'`,
which returns exactly four files (`stonedesk.html`, `sairnbiz.html`,
`sairncode.html`, `sairnvet.html`). `/sairnbuild` 404s live. `vercel.json` has
no build step or route for it.

Two things about SAIRNbuild *do* already exist and were verified, not assumed:

- `sairn-guardian-v2`'s App File Map assigns it `sairnbuild.html`, colour
  `#F59E0B` (amber), app_id `sairnbuild`.
- `api/claude.js`'s `KNOWN_APP_IDS` already allowlists `'sairnbuild'`, so the
  AI proxy will accept its calls on day one with no server change.

**Standing caution carried forward:** `SAIRN-SESSION66-HANDOFF.md` documented,
and `SAIRN-SESSION68` reconfirmed, that an earlier session's handoff falsely
claimed "SAIRNbuild v2.0 built+deployed+recoloured to Amber." Nothing was ever
built. Treat any pre-existing claim of SAIRNbuild progress as false unless
re-verified against the repo.

---

## 1. Target trade + primary persona

**Trade:** residential and light-commercial **general contracting / remodelling**
— the firm that runs the whole job and subcontracts the trades, as distinct
from StoneDesk (a single fabrication shop) or SAIRNscape (landscaping).

**Why this trade fits the platform:** it is the natural *buyer* of StoneDesk's
output. A GC who orders countertops from Pinnacle Stone & Design is the other
side of that transaction, which makes the eventual cross-app story real rather
than contrived.

**Primary persona — the owner-operator GC.** Runs 4-12 concurrent jobs, 2-6 of
their own crew, 8-20 subs on rotation. Lives in a truck. Their actual daily
pain, in priority order:

1. **Where is every job, right now** — which are blocked, on whom.
2. **Am I making money on this job** — committed cost vs budget, before the job
   ends rather than after.
3. **Change orders** — the single largest source of unpaid work in the trade.
   Verbal "sure, we can do that" becomes unbilled labour.
4. **Sub coordination** — who is on site which day, and is their insurance
   current.
5. **Draw requests / progress billing** — the cashflow mechanism GCs actually
   live on, and the thing generic invoicing tools get wrong.

**Deliberately out of scope:** takeoff/estimating from plans (a different,
CAD-shaped product), payroll and HR (that is SAIRNbiz's job — SAIRNbuild should
consume it, not duplicate it), and accounting ledgers (SAIRNacc).

**Secondary persona:** the office admin/bookkeeper who chases lien waivers,
COIs and draw paperwork. Panels they own are marked below.

---

## 2. Panel list

Sidebar grouping mirrors the existing apps' convention (grouped sections, one
panel per real job-to-be-done). Nav ids are the `sbNav(id)` /
`panel-<id>` pairs.

### Overview
| Panel | id | Purpose |
|---|---|---|
| Dashboard | `dashboard` | Every active job with stage, blocked flag, and margin-at-risk in one view. |
| AI Assistant | `ai` | Claude via `/api/claude` with `app_id:'sairnbuild'` — scope questions, contract language, code lookups. |

### Jobs
| Panel | id | Purpose |
|---|---|---|
| Job Board | `jobs` | The core record: address, client, contract value, stage, target dates. |
| Schedule | `schedule` | Who (crew or sub) is on which job on which day; the coordination view. |
| Change Orders | `changeorders` | Capture scope changes at the moment they happen, price them, get them accepted. |
| Daily Logs | `dailylogs` | Per-job site notes, weather, headcount, photos — the record that wins disputes. |
| Punch List | `punchlist` | Close-out defects per job, assigned to a sub, open until signed off. |
| Inspections | `inspections` | Permit and inspection milestones with pass/fail and re-inspection dates. |

### Money
| Panel | id | Purpose |
|---|---|---|
| Job Costing | `jobcost` | Budget vs committed vs actual per cost code, per job. The margin-truth panel. |
| Draw Requests | `draws` | Progress billing: % complete per line, retainage, what has been requested vs received. |
| Purchase Orders | `po` | Material and sub POs issued against a job and a cost code. |
| ~~Bids & Proposals~~ | ~~`bids`~~ | **DEFERRED out of v1.** A genuinely separate workflow from running active jobs; keeps v1 tight around the core job-costing loop. Revisit as a v2 increment. |

### Subs & Vendors
| Panel | id | Purpose |
|---|---|---|
| Subcontractors | `subs` | Sub roster with trade, rate basis, and current COI / W-9 / licence expiry. |
| Compliance | `compliance` | The expiry board: every insurance certificate and licence with days-until-expiry. |
| Suppliers | `suppliers` | Material vendors, terms, and spend-to-date by supplier. |

### Company
| Panel | id | Purpose |
|---|---|---|
| Company Profile | `company` | Business identity, licence numbers, insurance — synced to the platform. |
| Reports | `reports` | Job P&L, WIP schedule, change-order log, compliance expiry, sub spend. |
| Settings | `settings` | PINs/roles, cost-code list, default retainage %, markup defaults. |

**16 panels in v1** (17 listed, Bids deferred). Comparable to SAIRNbiz's 20.
Anything beyond this list is a later increment, not v1.

**Build order (decided):** `dashboard` → `jobs` → `jobcost` → `changeorders`
first. Those four are the persona's top-ranked pains and together exercise the
whole stack end to end — a `bld_*` table, the `/api/sd-data` read+write
branches, the licence gate, and a computed-not-hardcoded KPI. Only once that
loop is proven live do the remaining 12 get built; each is then additive against
a pattern that already works, rather than 16 panels all half-wired at once.

---

## 3. Data model

### Tenancy convention — follows the existing split exactly

The existing convention in `api/sd-data.js` is **not** uniform, and the
inconsistency is deliberate. Verified in code before writing this:

- `business_profiles` → keyed by **`license_hash`** + `app_id`
- `ai_memories` → keyed by **`license_hash`** + `app_id`
- `sd_slabs` → keyed by **`license_hash`**
- `employees` → keyed by **`customer_email`** (decision D1b)

The rule that explains it: **data owned by one app is keyed by
`license_hash`; data deliberately shared *across* apps is keyed by
`customer_email`**, because a customer may hold separate licences per app and
still be one tenant. `employees` is customer-email-keyed precisely so SAIRNbiz
can write it and StoneDesk can read it.

SAIRNbuild follows the same rule:

| Table | Tenancy key | Owner | Why |
|---|---|---|---|
| `business_profiles` | `license_hash` + `app_id='sairnbuild'` | SAIRNbuild | Reuses the existing shared table, no new table needed. |
| `ai_memories` | `license_hash` + `app_id='sairnbuild'` | SAIRNbuild | Same. |
| `bld_jobs` | `license_hash` | SAIRNbuild | App-owned. |
| `bld_change_orders` | `license_hash` | SAIRNbuild | App-owned. |
| `bld_costs` | `license_hash` | SAIRNbuild | App-owned. |
| `bld_draws` | `license_hash` | SAIRNbuild | App-owned. |
| `bld_subs` | `license_hash` | SAIRNbuild | App-owned. |
| `bld_daily_logs` | `license_hash` | SAIRNbuild | App-owned. |
| `employees` | `customer_email` | **SAIRNbiz (read-only here)** | Cross-app. SAIRNbuild reads its own crew from the roster SAIRNbiz already maintains — it must NOT write it. |

**Prefix DECIDED: `bld_*`.** SAIRNbiz's *localStorage* keys are already `sb_*`
(`sb_emps`, `sb_invs`, `sb_jobs`, …), so an `sb_*` Supabase table would read as
SAIRNbiz's even though SAIRNbiz owns no Supabase tables of its own. `bld_*`
removes the ambiguity outright and keeps one prefix per app.

Applies to **localStorage keys too**, not just Supabase tables — `bld_jobs`,
`bld_costs`, `bld_seeded`. Using one prefix on the server and another on the
client is exactly the kind of split that produced the `sd_remnant` /
`sd_remnants` confusion in StoneDesk (two keys, one letter apart, two modules).

### Key fields per table

Every app-owned table follows the existing shape — `license_hash`,
`updated_at`, and a `data` JSONB blob — rather than wide columns. That is what
`sd_slabs` and `business_profiles` already do, and the `employees` incident this
session (9 of 13 assumed columns did not exist) is the argument for it: a JSONB
payload cannot drift out of sync with the client's assumed schema.

```
bld_jobs        job_id, license_hash, updated_at, data{
                  address, client_name, client_email, client_phone,
                  contract_value, stage, start_date, target_end, actual_end,
                  permit_no, cost_codes[], retainage_pct, notes }

bld_change_orders co_id, license_hash, job_id, updated_at, data{
                  description, amount, labour_hrs, status
                  (draft|sent|accepted|rejected), requested_by,
                  sent_at, accepted_at, signature }

bld_costs       cost_id, license_hash, job_id, updated_at, data{
                  cost_code, kind (labour|material|sub|other),
                  budget, committed, actual, vendor_or_sub, po_ref, date }

bld_draws       draw_id, license_hash, job_id, updated_at, data{
                  draw_no, period_end, lines[{cost_code, pct_complete,
                  amount}], retainage_held, requested_at, received_at,
                  amount_received }

bld_subs        sub_id, license_hash, updated_at, data{
                  company, trade, contact, phone, email, rate_basis,
                  rate, w9_on_file, coi_expiry, licence_no,
                  licence_expiry, notes }

bld_daily_logs  log_id, license_hash, job_id, updated_at, data{
                  log_date, weather, crew_count, subs_on_site[],
                  work_performed, delays, photos[], author }
```

**Unique constraints — verify, do not assume.** The `employees` work this
session found the live table already had a `(customer_email, employee_id)`
composite that the client was not using, and `syncEmps()` failed for weeks
naming the wrong conflict target. Every table above needs an explicit
`UNIQUE (license_hash, <entity>_id)` created and then **probe-verified** the
same way (`on_conflict=` returns `42P10` when the constraint is missing) before
any client code relies on it.

---

## 4. Shared infrastructure — reuse vs new

### Reused unchanged (no server work)
| Component | Note |
|---|---|
| `api/_lib/license.js` | Untouched. Header says "single source of truth — do NOT fork this." Validates against `license_keys` by raw `key`; returns `license_hash`, `customer_email`, `active`, `trial_ends_at`, `stripe_subscription_id`. |
| `api/claude.js` | Untouched. `'sairnbuild'` is **already** in `KNOWN_APP_IDS` — verified. |
| Pattern 13 entitlement gate | The `402 TRIAL_EXPIRED` / paid-bypass logic already in `sd-data.js` applies as-is. |
| `business_profiles`, `ai_memories` | Existing tables, already `app_id`-scoped. |
| `employees` (read) | Existing read branch. SAIRNbuild reads crew from SAIRNbiz's roster. |

### Extended (server work, small)
| Component | Change |
|---|---|
| `api/sd-data.js` `RESOURCES` | Add `jobs`, `change_orders`, `costs`, `draws`, `subs`, `daily_logs`. Each gets a read + write branch following the **existing** `profile`/`slabs` pattern verbatim — service-role key server-side, `Prefer: resolution=merge-duplicates`, `upstream()` on failure. Do **not** invent a new endpoint. |
| `employees` write gate | Already gated to `app_id==='sairnbiz'`. Confirm SAIRNbuild receives `405 READ_ONLY` — that is the correct, intended behaviour, not a bug to fix. |
| `vercel.json` | Add `sairnbuild.html` to `buildCommand` and a `/sairnbuild$` route. Currently absent. |

### New, client-side only
| Component | Note |
|---|---|
| `sairnbuild.html` | Single-file app, amber `#F59E0B`, per the reference architecture. |
| `sbldData()` helper | The `sdData()`-equivalent: `POST /api/sd-data` with `Authorization: Bearer <license_key>`, returns `null` on any failure. **Copy the shape, not the identity logic** — and take the lesson from this session directly: define **one** resolver (`sbldLicenseKey()`) used everywhere, never inline the key lookup at each call site. StoneDesk had that logic copy-pasted in six places across three spellings before it was consolidated. |
| Licence gate | Prefix allowlist **must include `'BLD-'`** (decided), with an inline comment that the list is a format check and **not** auth. See §4a — the row must exist and be verified *before* this is written. |

### 4a. Licence provisioning — MUST happen before the gate is written

**Prefix DECIDED: `BLD-`.** Consistent with the existing convention
(`SD-` StoneDesk, `SB-` SAIRNbiz) and unambiguous against `bld_*` tables.

**Order of operations, deliberately in this sequence** so the SAIRNbiz
`SD-`/allowlist mismatch cannot repeat:

1. **Provision the row first.** One row in `public.license_keys`:

   | Column | Value | Consumed by |
   |---|---|---|
   | `key` | `BLD-PINNACLE-2026` | `license.js` looks up by raw `key` |
   | `status` | `active` | compared `.trim().toLowerCase()` |
   | `customer_email` | `demo@pinnaclestone.example` *(or the tenant email of record)* | tenant identity; scopes the `employees` read |
   | `app_id` | `sairnbuild` | read, not gated on by `sd-data` |
   | `plan` | as appropriate | Pattern 13 `plan_tier` |
   | `trial_ends_at` | future date, or `null` | `null` is treated as not-expired |
   | `stripe_subscription_id` | optional | set → bypasses the trial gate entirely |

2. **Verify it validates, before writing any client code.** `anon` cannot read
   or insert `license_keys` (both return `42501` — confirmed by probe, service
   role only by design), so verification goes through the deployed endpoint,
   whose error codes are an exact oracle:

   ```
   curl -s -X POST https://sairn.vercel.app/api/sd-data \
     -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer BLD-PINNACLE-2026' \
     -d '{"action":"read","resource":"profile","payload":{}}'
   ```

   `401 INVALID_LICENSE` → row absent · `403 LICENSE_INACTIVE` → status not
   active · `402 TRIAL_EXPIRED` → trial past and no Stripe sub · **`200` → good,
   proceed.** Confirmed as of 2026-07-30 that `BLD-PINNACLE-2026` and
   `BLD-INDUSTRIES-2026` both currently return `401` — the row does **not** yet
   exist and still needs creating.

3. **Only then** add `'BLD-'` to the client allowlist, and re-verify the key is
   accepted through the real UI gate — not just server-side. SAIRNbiz's gate
   silently returned early without setting `sb_lic`, which made an
   authentication failure look like a frozen-tab problem for several rounds.

**Provisioning is not something I can do** — it requires the service-role key or
Supabase dashboard access. This step is Michael's.

### Explicitly NOT built
Direct client-side Supabase calls. The anon/publishable key is locked out of
every table by design; StoneDesk already abandoned that approach and SAIRNbiz's
`syncEmps()` was broken for weeks because of it. All data access goes through
`/api/sd-data`. No `supabase-js` CDN script in this app.

---

## 5. Demo data plan

**Convention:** the platform seeds one recognisable fictional operator per app —
`Pinnacle Stone & Design` (StoneDesk, SAIRNbiz), `Pinnacle Animal Hospital`
(SAIRNvet), `Pinnacle Medical Billing LLC` (SAIRNcode). SAIRNbuild follows with
**`Pinnacle Industries LLC`** — a Westlake, OH general contractor.

**The story that makes the demo coherent:** Pinnacle Industries is the GC;
Pinnacle Stone & Design is its countertop supplier. One seeded job's material
PO points at Pinnacle Stone, which is the cross-app narrative made concrete.

### Seed content
- **6 jobs** across stages: 2 in progress, 1 blocked on inspection, 1 in
  close-out/punch, 1 complete, 1 awarded-not-started. Real Westlake/Rocky
  River/Avon Lake addresses matching the existing apps' geography. (Originally
  "1 bidding" — changed, since Bids is deferred out of v1 and a `bidding`
  stage with no panel behind it would be a dead state.)
- **5 subcontractors** with deliberately varied compliance state: 3 current,
  **1 COI expiring in 12 days**, **1 expired** — so the Compliance panel has
  something true to show. An all-green board demonstrates nothing.
- **4 change orders**: 1 accepted, 1 sent, 1 draft, 1 rejected — so every state
  renders.
- **Cost rows** on the two in-progress jobs: one comfortably under budget, one
  **over on labour**, so Job Costing shows a real negative. Per this session's
  StoneDesk/SAIRNbiz work, a negative metric must render in the danger colour
  conditionally — not a static "good" green.
- **2 draw requests**: 1 received, 1 outstanding past 30 days.
- **8 daily logs** on the active jobs, including one weather delay.
- **Crew** read from `employees` (SAIRNbiz's roster) rather than seeded locally —
  proves the cross-app read on day one.

### Hard rules for the seed
1. **Every KPI computed from the seed, never hardcoded.** Guardian Check 0b.
   The `genReport('pl')` fabrication in SAIRNbiz (`$498,000` hardcoded next to a
   real computation) is the failure to avoid.
2. **No button may claim an action it does not perform.** If a feature is not
   built, the label says so honestly — the SAIRNcode "read-only in this demo
   build" and SAIRNbiz `runPayroll()` fixes are the precedent.
3. **Seed only when the storage key is absent**, and guard with a
   `bld_seeded` flag. Note the trap found in StoneDesk's remnant module:
   `JSON.parse(x) || SEED` treats an empty array `[]` as truthy, so a
   legitimately-emptied list silently re-seeds. Check for `null` explicitly.
4. **Two differently-labelled metrics must have genuinely different
   calculations.** SAIRNbiz's "This Month" and "Total Recorded" were the same
   variable under two labels.

---

## 6. Decision record — RESOLVED 2026-07-30

Retained rather than deleted, so the reasoning is auditable later.

| # | Decision | Resolution | Where it lives now |
|---|---|---|---|
| 1 | Supabase table prefix | **`bld_*`** — removes the visual collision with SAIRNbiz's `sb_*` localStorage keys outright; one prefix per app. Extended to cover client-side keys too, so server and client never diverge. | §3 |
| 2 | Licence prefix + provisioned row | **`BLD-`**, row provisioned and endpoint-verified **before** the gate is written. Full column spec and the verification curl are in §4a. | §4a |
| 3 | Build order | **Dashboard → Job Board → Job Costing → Change Orders**, then the remaining 12. Proves the whole stack on the four highest-pain panels before breadth. | §2 |
| 4 | Bids & Proposals | **Deferred out of v1.** v1 is 16 panels. Also changed one seed job from `bidding` to `awarded-not-started`, since a stage with no panel behind it would be a dead state. | §2, §5 |

### Still genuinely open — and blocking
**The `BLD-PINNACLE-2026` row does not exist yet.** Verified 2026-07-30: both
`BLD-PINNACLE-2026` and `BLD-INDUSTRIES-2026` return `401 INVALID_LICENSE`, and
`anon` can neither read nor insert `license_keys` (`42501` on both, service role
only by design). Creating it needs the service-role key or dashboard access, so
it is Michael's step, and it **gates the licence gate** — §4a step 1.

Everything else in this scope can be built without it; only the gate and any
end-to-end sync test are blocked.

## 7. Verification standard for the build

Non-negotiable, inherited from this session's work: Guardian v2 before every
push (`node --check`, div balance, duplicate ids, nav/panel reconciliation);
`sairn_dead_button_audit.py` clean on A/C2/D1; every fix live-verified against
the deployed URL rather than assumed from a clean push; and any unique
constraint probe-verified before client code depends on it.
