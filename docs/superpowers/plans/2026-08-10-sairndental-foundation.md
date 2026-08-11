# SAIRNdental Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up SAIRNdental as a real, deployed, git-tracked app —
license gate, trial gate, brand identity, the core data model every
other feature depends on (patients/providers/operatories/procedure
types/coverage rules), and the mandatory photo-capture scaffold
requirement (insurance-card capture) — per
`docs/superpowers/specs/2026-08-10-sairndental-design.md`.

**Explicitly deferred to separate follow-up plans, not this one:** the
real availability/conflict-detection engine + public booking page, the
fee-schedule checkout-balance engine, automated email reminders, and
the denial/AR/revenue bridge from SAIRNcode. Each of those needs this
foundation to exist first (real patient/provider/procedure-type
records to compute against) — building them before the data model
exists would mean redoing them once real records are in place, same
reasoning as SAIRNcash's foundation-then-feature split.

## Global Constraints

- License-key + `api/sd-data.js` resource-route auth pattern (standard
  SAIRN B2B convention) — not Stripe/Firebase (spec §0).
- `dnt_procedure_types` is entirely practice-entered — never a
  bundled/hardcoded CDT code list (spec §3, real ADA-copyright
  constraint, not a style choice).
- Every new `sd-data.js` resource name gets its own prefix-collision
  check against the existing resource list before being added — same
  discipline every prior app's onboarding into that file has followed.
- `vercel.json` must be updated in the SAME commit as `sairndental.html`
  is created — SAIRNcash's foundation shipped a 404 the first time
  because this was missed; do not repeat that.
- `python tools/checkblocks.py sairndental.html` /
  `div_balance_check.py` / `duplicate_global_check.py` /
  `key_collision_check.py` clean after every change.
- Push Protocol: full local checks before push, real live-verify after.

---

### Task 1: SQL schema + license seed

**Files:** Create `sql/sairndental_data_schema.sql`,
`sql/sairndental_license_seed.sql`

- [ ] **Step 1: Write the schema**

Real tables for every resource in spec §2, following the exact
generic jsonb-blob pattern (`license_hash`, `app_id`, `<resource>_id`,
`data jsonb`, `created_at`, `updated_at`, 64KB size check, unique
`(license_hash, <resource>_id)`) every prior app's schema file already
uses — see `sql/sairnlegacy_data_schema.sql` as the direct template.
12 tables: `dnt_patients`, `dnt_providers`, `dnt_operatories`,
`dnt_provider_hours`, `dnt_procedure_types`, `dnt_coverage_rules`,
`dnt_appointments`, `dnt_charges`, `dnt_payments`, `dnt_denial`,
`dnt_ar`, `dnt_revenue`. Id-column names via the same mechanical
singularization rule `sairnlegacy_data_schema.sql` documents:
`patient_id`, `provider_id`, `operatory_id`, `provider_hour_id`,
`procedure_type_id`, `coverage_rule_id`, `appointment_id`,
`charge_id`, `payment_id`, `denial_id`, `ar_id`, `revenue_id`.

- [ ] **Step 2: Write the license seed**

Real demo license, same pattern as every other
`sql/*_license_seed.sql`: key `DNT-PINNACLE-2026` (matches this
platform's existing "Try X-PINNACLE-2026" gate-hint convention),
`app_id:'sairndental'`, `plan:'demo'`.

- [ ] **Step 3: Flag to the user**

Neither file is run as part of this plan's execution — both require
Supabase SQL editor access I don't have. Surface explicitly once
written, same as every other migration this session.

---

### Task 2: `api/sd-data.js` — register the 12 resources

**Files:** Modify `api/sd-data.js` (RESOURCES allowlist, error message
resource list, and a new `DNT_RESOURCES` generic read/write block —
same shape as `LEG_RESOURCES`/`SDN_RESOURCES`)

- [ ] **Step 1: Add to `RESOURCES` and the 400 error message's resource list**

Check first that none of the 12 new names collide with any existing
resource string in the file (`key_collision_check.py` after, but a
manual `grep -n "dnt_"` before writing anything is the actual
prevention step — this file's own header documents this exact
collision class happening before).

- [ ] **Step 2: Add the generic `DNT_RESOURCES` read/write block**

Directly mirrors `LEG_RESOURCES`'s block (`api/sd-data.js:1631-1669`)
— same blind-upsert semantics for all 12 (no atomic-gate requirement
identified for any of them at this stage; if the availability-engine
follow-up plan finds a real double-booking race analogous to
SAIRNlegacy's reservation lock, that gets its own narrow atomic fix
then, not preemptively guessed at here).

- [ ] **Step 3: `api/claude.js` — add `'sairndental'` to `KNOWN_APP_IDS`**

For §1's insurance-card capture call and any future AI use — same
one-line addition pattern as SAIRNcash's.

- [ ] **Step 4: Syntax-check**

```
node --check api/sd-data.js
node --check api/claude.js
```

- [ ] **Step 5: Commit**

```
git add api/sd-data.js api/claude.js
git commit -m "feat: api/sd-data.js -- register SAIRNdental's 12 resources; api/claude.js -- add sairndental app_id

..."
```

---

### Task 3: `sairndental.html` — app shell, license/trial gate, brand identity

**Files:** Create `sairndental.html`

- [ ] **Step 1: Write the base shell**

Following this platform's standard structure (see `sairnlegacy.html`'s
gate/PIN/trial-gate section as the direct template — `VALID=['DNT-',
'DEMO-','SAIRN-']` prefix array, `checkTrialGate()` ported verbatim
with the `TRIAL_KEY='dnt_trial_start'` substitution, license-key gate
calling `check_license`-equivalent against `api/sd-data.js`). Brand
color `#0EA5E9` throughout (spec §0). Nav sidebar with 4 top-level
sections stubbed: Patients, Scheduling, Billing (checkout balance +
denial/A/R/revenue), Insurance Capture — panels for Scheduling/Billing
beyond basic data entry are built in the follow-up plans, not here.

- [ ] **Step 2: `sd-data.js`-style generic sync helper**

`sdnData(action, resource, payload)` — identical shape to every other
app's copy of this function (`sairnlegacy.html:1261` as reference),
own copy for `sairndental.html`, not shared/imported.

- [ ] **Step 3: `vercel.json` wiring — same commit, not a follow-up**

Add `sairndental` to `buildCommand`'s `cp` list and a
`{"src":"/sairndental$","dest":"/sairndental.html"}` route entry.

- [ ] **Step 4: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
python tools/key_collision_check.py sairndental.html
node -e "JSON.parse(require('fs').readFileSync('vercel.json','utf8')); console.log('VALID_JSON')"
```

- [ ] **Step 5: Commit**

```
git add sairndental.html vercel.json
git commit -m "feat: SAIRNdental -- app shell, license/trial gate, vercel.json wiring

..."
```

---

### Task 4: Core data panels — patients, providers, operatories, procedure types, coverage rules

**Files:** Modify `sairndental.html`

- [ ] **Step 1: Patients panel**

CRUD for `dnt_patients` (spec §2 shape). Insurance fields present but
populated either manually or via Task 5's capture flow — this panel
doesn't depend on Task 5, Task 5 depends on this panel's data shape
existing first.

- [ ] **Step 2: Providers + Operatories panels**

CRUD for `dnt_providers`/`dnt_operatories`. Minimal — name + role for
providers, name for operatories. Real scheduling logic (provider
hours → availability) is the availability-engine follow-up plan's
job, not this one's — this task only needs providers/operatories to
exist as real records other resources can reference by id.

- [ ] **Step 3: Provider Hours panel**

CRUD for `dnt_provider_hours` (day-of-week + start/end time per
provider) — the real data the availability-engine follow-up plan
will consume. Entering it now, computing availability from it later.

- [ ] **Step 4: Procedure Types + Coverage Rules panels**

CRUD for `dnt_procedure_types` (practice-entered CDT code + fee + 
default length — spec §3's licensing constraint applies here: no
placeholder/seed data implying a real bundled code list, seed with
2-3 clearly-labeled example rows the practice is expected to replace)
and `dnt_coverage_rules` (payer + procedure type + coverage %).

- [ ] **Step 5: Syntax-check + commit**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
```

```
git add sairndental.html
git commit -m "feat: SAIRNdental -- core data panels (patients, providers, operatories, provider hours, procedure types, coverage rules)

..."
```

---

### Task 5: Insurance-card capture (mandatory scaffold requirement)

**Files:** Modify `sairndental.html`

- [ ] **Step 1: Photo capture UI**

`<input type="file" accept="image/*" capture="environment">` on the
Patients panel (per-patient action: "Capture Insurance Card"), preview
`<img>`, base64-encode client-side (`FileReader.readAsDataURL`) — per
`sairn-app-scaffold`'s reference pattern.

- [ ] **Step 2: Claude analysis call**

Through the shared proxy only (`sairn.vercel.app/api/claude`,
`app_id:'sairndental'`, `is_demo:true`), image as a multimodal content
block, system prompt instructing extraction of payer name, member ID,
group number, and plan type, free-text response with targeted
extraction (regex/line-parsing) into the four fields — per the
scaffold skill's own honest note: not a fragile full-JSON contract,
matching StoneDesk's proven real implementation shape.

- [ ] **Step 3: Pre-fill, never auto-save**

Extracted values populate the patient's insurance fields as an
editable draft the front-desk staff reviews and confirms before
saving — same "AI suggests, human confirms" discipline as SAIRNcash's
deduction-category suggestion, not a silent auto-write.

- [ ] **Step 4: Syntax-check + commit**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
```

```
git add sairndental.html
git commit -m "feat: SAIRNdental -- insurance-card capture (mandatory sairn-app-scaffold requirement)

..."
```

---

### Task 6: End-to-end verification, push, live-verify

- [ ] **Step 1:** Full local re-check of every changed file.
- [ ] **Step 2:** Push all commits.
- [ ] **Step 3:** Live-verify `sairn.vercel.app/sairndental` returns 200
  (learned from SAIRNcash: verify this specifically, don't assume from
  a clean push).
- [ ] **Step 4:** Real license-gate + trial-gate test against the live
  deployment (once `sql/sairndental_license_seed.sql` has been run).
- [ ] **Step 5:** Real interaction test of every Task 4 panel — add a
  patient, provider, operatory, provider-hours entry, procedure type,
  coverage rule, confirm each persists and syncs.
- [ ] **Step 6:** Real interaction test of Task 5's capture flow
  against an actual insurance-card photo — confirm extraction is
  reasonable and the pre-fill is genuinely editable, not silently
  auto-saved.
- [ ] **Step 7:** Update
  `docs/superpowers/specs/2026-08-10-sairndental-design.md`'s status
  to "foundation implemented and live-verified," with commit SHAs, and
  note the three deferred feature areas as the next real work.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks 1-6
is written**, per standing project practice and your instruction.

## After this plan: the three deferred follow-up plans

Written and executed separately, only once this foundation is live and
confirmed working (same sequencing as SAIRNcash's foundation → tax-
estimator split):
1. **Availability engine + public booking page** (spec §4) — the
   largest remaining piece; real conflict/double-booking detection
   across provider + operatory dimensions.
2. **Fee-schedule engine + real-time checkout balance** (spec §3).
3. **Automated email reminders** (spec §5) — needs a real email
   provider account provisioned by Michael before this can be built
   against anything real, so likely the last of the three to actually
   go live even if built earlier.
4. **Denial/A/R/Revenue bridge from SAIRNcode** (spec §6) — probably
   the fastest of the four follow-ups given it's largely direct reuse,
   but sequenced last here only because it has no dependency on this
   foundation plan at all and could reasonably be pulled forward if
   that's preferred once foundation work begins.
