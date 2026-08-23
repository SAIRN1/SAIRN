# SAIRNcare — Handoff, 2026-08-23 (Resend alert delivery; PA Ch. 2600 + MI/PA billing-code seeding)

Written at a natural stopping point, both assigned items closed out. Every
claim below was checked against `git`, the live deployment, or the production
runtime log during this session — not carried forward from the previous
handoff and not recalled from memory.

**Naming:** this file uses the `APP-YYYY-MM-DD-subject-handoff.md` convention
adopted 2026-08-23. It is deliberately **not** `SAIRNCARE-SESSION3-HANDOFF.md`
— the counter scheme was retired today after two different real
`SAIRNLAW-SESSION6-HANDOFF.md` files existed at once and a fresh session read
the wrong one. Older handoffs keep their existing names; both patterns on disk
is expected, not drift. Find the latest by **date**, not by highest N.

---

## 0. The headline, because it inverts the previous handoff's open item #1

The previous handoff recorded the alert-email failure as *"Michael action item,
not a code fix — check the Resend vars were saved to the Production environment
and that a redeploy happened after."*

**That diagnosis was wrong, and the truth was two separate problems stacked on
top of each other.** Both are now identified; the first is fixed, the second is
not and cannot be fixed from code.

1. **A code-side variable-name mismatch (FIXED, live-verified).** The cron read
   `RESEND_FROM_ADDRESS`. That variable **has never existed in this Vercel
   project.** The sender address has been configured as **`RESEND_FROM_EMAIL`**
   since 65 days ago, alongside `RESEND_API_KEY`, both on Production and
   Preview. Nothing in the repo referenced it — it was an orphan. Nothing ever
   needed to be set in Vercel.

2. **The Resend sending domain is not verified (STILL OPEN, Michael only).**
   With the name fixed, the sweep now reaches Resend and Resend **rejects it**:

   ```
   13:01:24 GET /api/alf-alerts 200 [error/serverless]
   alf-alerts: Resend send FAILED for license_hash 6dd308f1…09c3dd (1 late)
   -- Resend returned 403 {"statusCode":403,"message":"The sairn.com domain is
   not verified. Please, add and verify your domain on
   https://resend.com/domains","name":"validation_error"}
   ```

   **SAIRNcare alert emails still do not deliver.** The fix moved the failure
   from "never attempted" to "attempted and refused by the provider", which is
   real progress and a real remaining outage.

**The second problem was invisible until this session, and would have stayed
invisible.** See section 3.

---

## 1. Verified current state

- **`origin/main` HEAD at time of writing:** `78d0514d7725a8ec1b21282a302c68fbf51717ae`
  (moves constantly — several other sessions are pushing concurrently; re-derive it).
- **All three commits from this session confirmed present on `origin/main`**
  via `git merge-base --is-ancestor <sha> origin/main`, not from a clean push
  exit code.
- **Working tree in `Documents\SAIRN-cody`: CLEAN.** `git status --short`
  returns nothing.
- **Tests: 348 passing, 0 failing, across 18 suites** in `tests/sairncare/`
  (was 327 at the end of the previous session; +21 this session).
- **`sairncare.html`:** 1 script block, `node --check` clean; div balance
  735/735; 301 ids; 106 inline handlers, 0 undefined; 0 `console.log`;
  0 `api.anthropic.com`; 0 `service_role`.
- **Live production deployment confirmed to contain both fixes** — checked by
  ancestry against the commit the `sairn.vercel.app` alias actually serves,
  and by grepping that commit's blob for `RESEND_FROM_EMAIL` (5 hits) and
  `Resend send FAILED` (1 hit).
- **`https://sairn.vercel.app/sairncare` returns 200** and contains all three
  UI strings added this session (`states routable`, `Codes on file for`,
  `Not evaluated by this app`).

### Known pre-existing, NOT introduced this session
`sairncare.html` has 2 duplicate element ids (`sc-census`, `sc-staff`). They
sit in mutually exclusive branches of one template string, so only one renders
at a time. Confirmed pre-existing by re-checking against the stashed tree.
Not touched — out of scope for these two items.

---

## 2. Commits this session, in order

| SHA | What |
|---|---|
| `e0b74b4` | **Resend env-var name fix** — `RESEND_FROM_ADDRESS` → `RESEND_FROM_EMAIL`; the `EMAIL_NOT_CONFIGURED` message now names *which* variable is missing; 2 regression tests |
| `7aedb05` | **PA Ch. 2600 (PCH) compliance seeding + MI/PA HCBS billing codes**, plus the payer-engine changes those forced; 17 new tests |
| `1aec336` | **Silent-failure fix** — a Resend *rejection* on the cron path was invisible; now `console.error`'d with the provider's reason; 1 new test |

Files touched across the three: `api/alf-alerts.js`,
`api/_lib/payer-routing.js`, `api/_lib/compliance-rules.js`, `sairncare.html`,
`sql/sairncare_compliance_seed.json`, `sql/sairncare_payer_rules_seed.json`,
and four suites under `tests/sairncare/`.

---

## 3. What was CORRECTED, not just added

### 3.1 The previous handoff's item #1 diagnosis was wrong
Covered in section 0. Recording the shape of the error because it will recur:
the symptom (`503 EMAIL_NOT_CONFIGURED`) genuinely *looks* like a missing
secret, and the guard that produced it listed **both** variables
unconditionally. That message is what sent the previous session looking for an
absent `RESEND_API_KEY` that was present and correct the entire time. The guard
now names only the variable actually missing.

**The check that settled it took one command:** `vercel env ls production`,
which prints variable names and environments without printing values. It should
have been the first thing run, not the last.

### 3.2 A 200 from the alert cron did NOT mean an email was sent
This is the most important finding of the session and it was nearly missed.

After the name fix, the 12:00 UTC firing returned **200** where 10:00 and 11:00
had returned **503**. That is genuine proof the env gate cleared — and it is
*not* proof anything was delivered. `sendResendEmail`'s failure reason went into
the handler's JSON response body, and **a cron's response body goes nowhere**:
Vercel records the status code and discards the body. A Resend 403 on every
message produced a byte-identical 200 to a sweep that delivered perfectly.

An alerting system reporting success while notifying nobody is precisely the
silent-failure pattern this platform is supposed to refuse — and it was sitting
*inside the feature whose entire job is to notice when something did not
happen*. Fixed in `1aec336`; the 13:01 log line quoted in section 0 is the
first output it ever produced, and it immediately exposed the domain problem.

Had this not been added, this handoff would have said "Resend fixed, verified
200" and the alerts still would never have arrived.

### 3.3 Three PA "unverified" figures were WRONG, not merely unconfirmed
The previous seed's `unverified_notes` parked four PCH figures from a working
summary as unchecked. Reading 55 Pa. Code Ch. 2600 directly showed three of them
were affirmatively false:

- **"no numeric ratio"** — false. § 2600.57 carries the *same* service-hour
  figures as the ALR chapter: 1 hr/day per mobile resident, 2 hrs/day per
  resident with mobility needs, 75% during waking hours. Treating PCH as having
  nothing measurable would have let a home under-staff with the app silent.
- **"1 awake staff for 16+ residents"** — wrong in both halves, and *stricter*
  than recorded, not looser. § 2600.58(a): at 16 or more residents **all**
  on-duty direct care staff must be awake. The one-awake-staff figure is
  § 2600.58(b) and triggers on the **mobility-needs count below 16**, a
  different test as well as a different number.
- **"12 hrs/yr general + 6 hrs/yr dementia"** — the 12 is right; the 6 applies
  **only** to staff working in a secured dementia care unit (§ 2600.236).
  Chapter 2600 has **no all-staff dementia-training mandate at all** — there is
  no § 2600.69 counterpart to the ALR chapter's 4+2. Verified by reading the
  whole staffing subchapter §§ 2600.51–2600.68, not inferred from absence.

The fourth ("no RN or dietitian required") is **still not encoded** — see 4.3.

### 3.4 `PA-LICENSURE-2026` claimed a reach it did not have
It declared `available_under: ['pch','alr']` while every figure, phrase and
citation inside it came from Chapter 2800. Not a wrong fact — a correct fact
with too wide a claimed scope, which is the harder kind to catch. Chapter 2600's
unit is a **secured dementia care unit** (dementia only; written request to the
personal care home regional office); Chapter 2800's is a **special care unit**
(also covers neurobehavioral rehabilitation after brain injury; application to
the Department). Both carry the same 60-day lead time and the same four
triggering events, which is exactly what made the substitution look harmless.
Now scoped to `alr`, with a pointer to the PCH rule.

### 3.5 The payer engine assumed things that were only true because OH and IN agreed
Researching MI and PA exposed two latent modelling bugs:

- **Every state was assumed to have acuity tiers.** A tierless state fell
  through to `MISSING_TIER` with an empty `available_tiers` list — telling the
  user to supply one of nothing, and blaming them for a data gap. `tier_model`
  must now be **declared**; a rule declaring neither returns `MALFORMED_RULE`
  naming itself, and a tier supplied to a tierless state is refused rather than
  silently ignored.
- **Coverage counted any rule as coverage.** Seeding MI and PA would have
  flipped an honest "2 of 4" into a "4 of 4" meaning the opposite to a biller.
  `hcbsCoverage()` now separates routable from reference-only. The client-side
  duplicate of that computation in `sairncare.html` was updated to match — it
  would otherwise have displayed the false number regardless of the server.

### 3.6 A process error of mine, disclosed
An early `cd /c/Users/marsh` moved the Bash tool's **persistent** working
directory to the home-directory checkout of this same repo. Several later
relative-path verification commands therefore ran against a stale copy: a
`node --check`, a full test run, and a couple of source greps. **No edit or
commit was affected** — every `Edit` used an absolute path, and the home
checkout was never written to (still at `1a9fa99`, untouched). But those checks
were worthless, and were all redone with explicit paths; the numbers in
section 1 are from the redone runs.

Two lessons worth keeping: `cd X && cmd` changes state for every later call in
this shell, and `C:\Users\marsh\` being a checkout of the same repo makes that
mistake silent instead of loud.

### 3.7 The first live verification failed 3 of 29 checks — and that was the DB, not the code
Worth recording because the instinct was to suspect the change. The test licence
`ALF-TEST-2026` held only a **partial** seed: 7 of 16 compliance rules, and
Indiana's payer rules were absent entirely. The full seed is now loaded (16
compliance + 6 payer, all `200`), and the re-run passed all 29.

---

## 4. Open items, prioritized

### 4.1 BLOCKING, Michael only — the Resend sending domain is not verified
**SAIRNcare alert emails do not deliver.** Resend returns
`403 … The sairn.com domain is not verified`. Two options:

- Verify `sairn.com` at <https://resend.com/domains> (DNS records), or
- Change `RESEND_FROM_EMAIL` to a sender on an already-verified domain.

This is **not** a code fix and this session did not attempt one. It affects
every Resend sender on this project, not just SAIRNcare.

**How to confirm it is fixed:** the cron fires hourly at :00 UTC. Check the
production runtime log for `/api/alf-alerts`. The failure line
`alf-alerts: Resend send FAILED … Resend returned 403` disappearing — while
the test facility still has a late dose — is the signal. Do not read a bare
200 as success; that is exactly the trap described in 3.2.

**Current test-facility state, so the signal is interpretable:** licence
`ALF-TEST-2026` (`license_hash` `6dd308f1…09c3dd`), facility "Verification
ALF", `med_window_minutes` 60, `alert_email` set, **1 genuinely late
medication**. So the sweep does reach the send on every firing — the only
variable is whether Resend accepts it.

### 4.2 NOT MINE — `api/sairndental/send-reminder.js` has the identical bug
It reads the same non-existent `RESEND_FROM_ADDRESS` and fails its own
env-completeness guard on every firing, and has done **since it shipped** — it
has never sent a single reminder. **Deliberately not fixed here:** outside the
SAIRNcare/`alf_` scope this session was given. Confirmed real and held for
whoever builds SAIRNdental. It is a one-line change, and note that fixing the
name alone will not make it deliver either until 4.1 is resolved.

### 4.3 PCH "no RN or dietitian required" — still unverified, deliberately
Chapter 2600's staffing subchapter contains no RN or dietitian requirement, but
this app does not encode a negative from an absence in a single chapter.
Asserting "not required" is a compliance claim, and the only honest basis for
one is a positive source saying so. Recorded in the seed's `unverified_notes`.

### 4.4 PA ALR special care unit — two items still unconfirmed
The Ch. 2800 "max 2 residents per living unit" figure and the ALR cognitive
pre-admission screening window remain unverified and unencoded. **The PCH
equivalents ARE now confirmed** (medical evaluation within 60 days prior,
cognitive screening within 72 hours prior, § 2600.231(b)–(c)) — do **not**
carry those across to ALR. That is the same substitution error 3.4 was about.

### 4.5 MI and PA remain reference-only by design, not by omission
Neither state bills assisted living the way OH and IN do, and this is a fact
about the programs rather than a limit of the research:

- **MI** — MI Choice has **no assisted-living per-diem code**. The service is
  Community Living Supports, `H2015`, in **15-minute units of care actually
  delivered**, billed to the **waiver agency** (which submits encounter data to
  MDHHS via CHAMPS), not to the state. Days present determines neither the unit
  count nor the payer.
- **PA** — the OLTL fee schedule contains **no assisted-living line at all**.
  The nearest code is Residential Habilitation `W0102`, an **OBRA-waiver**
  service capped at **8 unrelated residents** in the licensed setting, whose
  unit is a day carrying **at least 8 hours** of service. Most Medicaid ALF
  residents in PA are in Community HealthChoices — capitated managed care, no
  state fee schedule to seed.

**A `T2031`-shaped Michigan rule was the single most damaging thing available
here.** It would have looked exactly like Ohio's and billed a code Michigan does
not use. If a future session is asked to "finish" MI/PA coverage, that request
is based on a false premise — re-read this section before writing anything.

### 4.6 Rules are seeded in the repo AND loaded into ALF-TEST-2026 only
The seed JSONs are the source of truth in-repo. They are **not** automatically
in any database. A real facility licence needs the rules loaded through the
`write` action before compliance or routing answers anything. As of this
session, only `ALF-TEST-2026` has the full set.

### 4.7 Carried forward, re-checked, still open
- `ALF_PHARMACY_SECRET` is set, so `api/alf-pharmacy.js` is live, but no real
  pharmacy integration is connected to it.
- SMS remains genuinely unavailable platform-wide; the UI states this.

---

## 5. Environment gotchas that cost real time

Three carried from the previous handoff and re-confirmed, plus two new.

- **Mixed line endings.** `core.autocrlf=true` here: blobs are LF, worktree is
  CRLF. `api/sd-data.js` has previously been mangled file-wide by `sed -i`.
  **Check the diff *shape* (`git diff --cached --numstat`) before every commit**
  — this session's were 20/4, 46/1, 84/13, etc., all targeted.
- **Python on Windows defaults to cp1252.** Pass `encoding='utf-8'` explicitly.
  (Avoided entirely this session by using Node, which is UTF-8 by default.)
- **A backgrounded Chrome tab suspends painting and network completion.** Check
  `document.visibilityState` before diagnosing an app bug.
- **NEW — the Bash tool's working directory persists across calls**, and
  `cd X && cmd` inside a compound command changes it for everything after.
  Because `C:\Users\marsh\` is *also* a checkout of `SAIRN1/SAIRN`, relative
  paths silently resolve against a stale copy instead of erroring. Use
  `git -C <path>` and absolute paths. See 3.6.
- **NEW — PDF tables extract wrong by default.** The PA OLTL fee schedule PDF
  misaligns by one row under `pdftotext -layout`, putting procedure codes
  against the **wrong service names**. `pdftotext -table` aligns correctly. The
  extraction was cross-checked against known HCPCS semantics (`T1002` RN,
  `T1003` LPN, `GO`/`GP` therapy modifiers, `97537` community reintegration)
  before any code was trusted. Note also that `pdftoppm` is **not installed** on
  this machine, so the `Read` tool cannot render PDF pages as images — text
  extraction is the only route, which is exactly why the alignment check matters.

---

## 6. Credentials (unchanged, re-confirmed working this session)

- **Licence:** `ALF-TEST-2026`
- **Owner:** `cody-verify` / PIN `472913` — real login performed twice this
  session, and a fresh independent token issued for the read-back verification.
- Also present: `cody-nursing`, `cody-med_aide`, `cody-billing`, same PIN.
- Session token header is **`X-SD-Auth`** (not `X-ALF-Token`).
- The `route` action's payload key is **`program`** (e.g. `medicaid_hcbs`),
  not `mechanism`.

---

## 7. Standard verification reminder

Re-derive `origin/main` HEAD (it moves several times an hour — multiple
sessions push concurrently), re-run `tests/sairncare/*.js`, and re-check the
live endpoints before trusting any claim in this document, **including this
one**.

And specifically: **do not treat a 200 from `/api/alf-alerts` as proof an alert
was delivered.** Section 3.2 exists because that inference was available, looked
reasonable, and was false.
