# SAIRNbuild — Scope

**Decisions FINALIZED 2026-07-30, panel scope EXPANDED same day (§2).** The
four open items originally in §6 were resolved and folded into the body; §6
is retained as a decision record. §2's original 16-panel v1 list is likewise
superseded by a 36-panel expansion, kept below as its own decision record
rather than deleted.

| # | Decision |
|---|---|
| 1 | Supabase table prefix: **`bld_*`** |
| 2 | Licence prefix: **`BLD-`**, with one real `license_keys` row provisioned *before* the gate is written — **done**, see §6. |
| 3 | Build order: **Dashboard → Job Board → Job Costing → Change Orders** shipped first, live; sequencing for the remaining 32 panels is a separate, not-yet-made decision. |
| 4 | ~~Bids & Proposals deferred out of v1~~ — **reinstated 2026-07-30**, see §2. |

**Status: 4 of 36 scoped panels built and live** (`dashboard`, `jobs`,
`jobcost`, `changeorders` — `sairnbuild.html` exists, is routed at
`/sairnbuild`, and is wired into `vercel.json`). This corrects the
"scope only, no code exists" status this section originally carried — that
was true when first written and has not been true since the build-order
panels shipped; left uncorrected it would misdirect a future session into
re-verifying something already settled.

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

## 2. Panel list — EXPANDED 2026-07-30

**Superseded the original 16-panel v1.** Standing product decision: a
general-contractor/builder platform manages far more surface area than four
job-costing panels — comparable in scope to StoneDesk (a single-shop
fabricator, 61 panels), not a small add-on comparable to SAIRNbiz (20). This
section replaces §2 as it stood; the original 16-panel table is preserved
below as a decision record rather than deleted.

**Honesty note on the count, stated up front rather than left implicit:** this
pass produced **36 panels** — every real GC job-to-be-done named in the
request, plus proven patterns cross-referenced from StoneDesk/SAIRNbiz/SAIRNvet
— not a padded list built to hit a round number. StoneDesk's 61 is the result
of many real build sessions surfacing genuine additional need over time, not
an upfront design target. This doc does not manufacture 25 more panels to
match that number artificially; it grows the same way StoneDesk did, from
here, as real sessions surface real additional need. If Michael wants more
panels seeded now rather than grown organically, that is his call to make
explicitly, not something to assume from "comparable in scope."

Sidebar grouping mirrors the existing apps' convention (grouped sections, one
panel per real job-to-be-done). Nav ids are the `sbNav(id)` /
`panel-<id>` pairs. Four panels already built and live keep their existing ids
unchanged (`dashboard`, `jobs`, `jobcost`, `changeorders`).

### Overview (2)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Dashboard | `dashboard` | Every active job with stage, blocked flag, and margin-at-risk in one view. | **Built, live** |
| AI Assistant | `ai` | Claude via `/api/claude` with `app_id:'sairnbuild'` — scope questions, contract language, code lookups. | New |

### Sales & Bidding (1)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Bids & Proposals | `bids` | **Reinstated — reverses the original v1 deferral.** The rationale for cutting it ("keeps v1 tight") no longer applies once v1 itself is being redefined at StoneDesk scale; a GC managing 4-12 concurrent jobs needs a real pipeline feeding Job Board, the same way StoneDesk's Quote Builder/AI Instant Quote feed its own job flow. Line-item cost estimation lives inside this panel rather than as a separate Estimating panel — §1's boundary against CAD/takeoff-based estimating stays exactly as decided; this is proposal pricing, not a takeoff tool. | New |

### Jobs (10)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Job Board | `jobs` | The core record: address, client, contract value, stage, target dates. | **Built, live** |
| Project Timeline | `timeline` | Multi-week critical-path/Gantt-style view across all jobs — distinct from the day-to-day crew Schedule below: this panel answers "when does each phase happen," Schedule answers "who's where today." | New |
| Schedule | `schedule` | Who (crew or sub) is on which job on which day; the coordination view. | New |
| Daily Logs | `dailylogs` | Per-job site notes, weather, headcount, photos — the record that wins disputes. | New |
| Field Photo Analysis | `fieldphoto` | **Core feature, not an afterthought — per the standing photo→Claude→structured-output product rule (`sairn-app-scaffold`).** A rep or PM photographs a site condition (unexpected framing issue, damage, a scope question), Claude reads it and suggests cost/scope impact, optionally spawning a Change Order or RFI directly from the result. Same 3-stage pattern as StoneDesk's Field Sketch Quote (camera-capture input, multimodal proxy call through `sairn.vercel.app/api/claude`, app-specific output) — output shape here is cost/scope suggestions, not a priced quote. | New |
| Change Orders | `changeorders` | Capture scope changes at the moment they happen, price them, get them accepted. | **Built, live** |
| Punch List | `punchlist` | Close-out defects per job, assigned to a sub, open until signed off. | New |
| RFIs | `rfis` | Request-for-information log: question to architect/engineer/owner, date sent, response, days outstanding — the paper trail that protects against delay-claim disputes. | New |
| Submittals | `submittals` | Material and shop-drawing approval tracking: submitted, under review, approved/rejected, resubmit — distinct from Purchase Orders (this is approval status, not a commitment to buy). | New |
| Selections | `selections` | Client-chosen finishes (paint, fixtures, flooring, appliances) per job: option, chosen date, lead time, ordered flag — a residential-remodel-specific pain with no equivalent in StoneDesk/SAIRNbiz/SAIRNvet, added because it's real, not because it was cross-referenced. | New |
| Inspections | `inspections` | Permit and inspection milestones with pass/fail and re-inspection dates. | New |

### Money (7)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Job Costing | `jobcost` | Budget vs committed vs actual per cost code, per job. The margin-truth panel. | **Built, live** |
| Draw Requests | `draws` | Progress billing: % complete per line, retainage, what has been requested vs received. | New |
| Lien Waivers | `lienwaivers` | Conditional/unconditional waivers tied to each draw — the paperwork that travels with money, kept separate from Draws itself the same way StoneDesk keeps Invoices and AR/Financial as separate panels rather than one combined view. | New |
| Purchase Orders | `po` | Material and sub POs issued against a job and a cost code. | New |
| Deliveries | `deliveries` | Fulfillment tracking against issued POs — expected date, received, short/damaged flag. POs are the commitment; this is whether it showed up. | New |
| Timesheet | `timesheet` | Crew clock-in/out per job, feeding Job Costing's labour cost-code lines directly. Reuses the pattern StoneDesk and SAIRNbiz both already run as a Timesheet panel. | New |
| Check Register | `checkregister` | Reconciles written checks (sub/vendor payments) against the bank register — direct reuse of a real, working StoneDesk feature (`#sb-check-register`, `stonedesk.html` line ~2488), not reinvented. | New |

### Subs & Vendors (4)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Subcontractors | `subs` | Sub roster with trade, rate basis, and current COI / W-9 / licence expiry. | New |
| Compliance | `compliance` | The expiry board: every insurance certificate and licence with days-until-expiry. | New |
| Suppliers | `suppliers` | Material vendors, terms, and spend-to-date by supplier. | New |
| Equipment | `equipment` | Owned and rented equipment per job: utilization, maintenance due, rental cost accrual. | New |

### Safety (1)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Safety & Incidents | `safety` | Incident log (date, job, description, OSHA-reportable flag, corrective action) and toolbox-talk tracking. A GC carries this liability directly; StoneDesk's own Safety panel (`panel-safety`) is the closest direct precedent. | New |

### Client (2)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Client Portal | `clientportal` | Shared view for the homeowner/client: job status, photos, approved change orders, selections status. Communication log lives here rather than as a separate panel, folding in what would otherwise be a duplicate of this. | New |
| Warranty | `warranty` | Post-completion callback tracking: claim, job reference, trade responsible, status, cost. Direct reuse of StoneDesk's proven Warranty panel shape. | New |

### Documents (1)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Documents | `documents` | Plans, specs, and permit file library per job — the one place drawings live, referenced by RFIs/Submittals/Inspections rather than each keeping its own copy. | New |

### Growth (2)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Reviews | `reviews` | Post-job client reviews/testimonials — direct reuse of StoneDesk's proven Reviews panel (`panel-reviews`), genuinely relevant here since referral/repeat business is a real residential-remodel revenue channel. | New |
| Referrals | `referrals` | Referral-source tracking — direct reuse of StoneDesk's proven Referral panel (`panel-referral`). | New |

### Company (6)
| Panel | id | Purpose | Status |
|---|---|---|---|
| Company Profile | `company` | Business identity, licence numbers, insurance — synced to the platform. | New |
| Reports | `reports` | Job P&L, WIP schedule, change-order log, compliance expiry, sub spend. | New |
| Settings | `settings` | PINs/roles, cost-code list, default retainage %, markup defaults. | New |
| Market Intelligence | `market` | Material cost trend and mortgage-rate signals (lumber, concrete, steel; financing-rate context for clients) — direct reuse of StoneDesk's proven Market Intelligence panel (`panel-market`). | New |
| Material Price Intelligence | `priceintel` | Vendor price comparison and trend tracking for volatile material costs — direct reuse of StoneDesk's proven Price Intelligence panel (`panel-priceintel`), genuinely relevant given real material-cost volatility in construction right now. | New |
| Integrations | `integrations` | Third-party connections (accounting, e-signature). Direct reuse of StoneDesk's proven Integrations panel (`panel-integrations`). | New |

**Weather — cross-cutting, not a panel.** StoneDesk's real Weather Command
Engine (`stonedesk.html` line ~12792, exec-role-gated topbar status, not a
sidebar panel) is more relevant to a GC than to a stone shop — weather delays
are a direct, frequent driver of schedule slip and belong logged against
Daily Logs and visible on Dashboard. Implement the same way StoneDesk does:
a topbar status element, not a 37th panel.

**Deliberately NOT cross-referenced, and why:** StoneDesk's IT Admin panel —
built for a business with its own IT-support surface, a mismatch for this
persona (an owner-operator running 4-12 jobs from a truck). Porting every
StoneDesk panel regardless of fit would be padding, the exact thing the
honesty note above is trying to avoid.

**36 panels total (4 already built/live, 32 new).** Comparable in real
job-to-be-done coverage to StoneDesk's early-to-mid build, not yet at
StoneDesk's full 61 — see the honesty note above for why that gap is left
open rather than filled artificially.

**Build order:** the 4 already-built-and-live panels (`dashboard`, `jobs`,
`jobcost`, `changeorders`) stay exactly as they are — nothing here proposes
reworking shipped, live-verified code. Sequencing the remaining 32 is a
separate decision for the next session, not decided in this pass.

**NOT done in this pass, flagged rather than rushed:** §3's data model needs
a new `bld_*` table (or an extension to an existing one, where the pattern
fits — e.g. Deliveries could live as a status field on `bld_purchase_orders`
rather than its own table) for each new panel above. Speccing 10+ new tables
carefully, the way §3 already does for the original six, is real work that
deserves its own pass rather than being rushed alongside this one.

### Original v1 panel list (superseded, kept as decision record)

| Panel | id | Purpose |
|---|---|---|
| Dashboard | `dashboard` | Every active job with stage, blocked flag, and margin-at-risk in one view. |
| AI Assistant | `ai` | Claude via `/api/claude` with `app_id:'sairnbuild'` — scope questions, contract language, code lookups. |
| Job Board | `jobs` | The core record: address, client, contract value, stage, target dates. |
| Schedule | `schedule` | Who (crew or sub) is on which job on which day; the coordination view. |
| Change Orders | `changeorders` | Capture scope changes at the moment they happen, price them, get them accepted. |
| Daily Logs | `dailylogs` | Per-job site notes, weather, headcount, photos — the record that wins disputes. |
| Punch List | `punchlist` | Close-out defects per job, assigned to a sub, open until signed off. |
| Inspections | `inspections` | Permit and inspection milestones with pass/fail and re-inspection dates. |
| Job Costing | `jobcost` | Budget vs committed vs actual per cost code, per job. The margin-truth panel. |
| Draw Requests | `draws` | Progress billing: % complete per line, retainage, what has been requested vs received. |
| Purchase Orders | `po` | Material and sub POs issued against a job and a cost code. |
| ~~Bids & Proposals~~ | ~~`bids`~~ | Was deferred out of v1 here; reinstated above, 2026-07-30. |
| Subcontractors | `subs` | Sub roster with trade, rate basis, and current COI / W-9 / licence expiry. |
| Compliance | `compliance` | The expiry board: every insurance certificate and licence with days-until-expiry. |
| Suppliers | `suppliers` | Material vendors, terms, and spend-to-date by supplier. |
| Company Profile | `company` | Business identity, licence numbers, insurance — synced to the platform. |
| Reports | `reports` | Job P&L, WIP schedule, change-order log, compliance expiry, sub spend. |
| Settings | `settings` | PINs/roles, cost-code list, default retainage %, markup defaults. |

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

### Licence status — RESOLVED, correcting a stale claim left in this section
**`BLD-PINNACLE-2026` is provisioned and working**, confirmed later the same
day this section was first written: it returns `200` from `/api/sd-data`
(was `401` earlier that day, per `SAIRNBUILD-SESSION2-HANDOFF.md`). The gate
accepts it, PIN passes, and reads resolve to real data. This section
previously said the row "does not exist yet" — that was true at the time it
was written and is not true now; left uncorrected it would have sent a future
session chasing a blocker that's already closed. Nothing about §4a's
provisioning steps needs to be repeated.

## 7. Verification standard for the build

Non-negotiable, inherited from this session's work: Guardian v2 before every
push (`node --check`, div balance, duplicate ids, nav/panel reconciliation);
`sairn_dead_button_audit.py` clean on A/C2/D1; every fix live-verified against
the deployed URL rather than assumed from a clean push; and any unique
constraint probe-verified before client code depends on it.
