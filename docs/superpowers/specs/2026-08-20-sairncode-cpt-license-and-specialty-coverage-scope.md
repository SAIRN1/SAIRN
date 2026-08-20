# SAIRNcode — Pre-SAIRNcare gap check: scope, not a build

**Status:** scope for review, per Michael's explicit instruction. No code
written. This checks two claims before trusting them and scopes what's
actually missing — the same discipline as the SAIRNcare scope-conflict find.

---

## Claim 1 — "the CPT/ICD-10/CDT BYO-license grounded lookup was never built." Verified TRUE.

Checked rather than assumed:

- `grep -niE "cpt.*license|licensed.*cpt|byo.*cpt|optum|cdt.*license"
  sairncode.html` → **zero matches**.
- `api/sc-credentials.js`'s `ALLOWED_SERVICES` → **`{ stedi: true }` only**.
  No CPT/CDT vendor is a registerable credential.
- What *does* exist: the "2026 Code Awareness Lookup" (item 4, Encoder
  panel) — real, live, **web-search-grounded**, not license-grounded. It
  checks live search results, not an authoritative connected data source.
  This is not a smaller version of the missing feature; it's the honest
  fallback the missing feature was always meant to sit in front of (already
  stated in the Phase 2 doc's Phase 3 section — that intent was never
  executed).

Correct to flag. This is Phase 3 from the original BYO-credential plan,
scoped in that plan, never built, never re-confirmed since.

---

## Real vendor landscape, verified live this session (not from training data)

Same discipline as Phase 1's Stedi research — checked directly, not recalled.

| Source | Real access path (verified) | License needed |
|---|---|---|
| **ICD-10-CM** | **NLM Clinical Table Search Service** — free, public, no license, no API key. Base URL `https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search`. Confirmed 2026 dataset, 74,719 records. | **None — public domain.** |
| **CPT** | AMA runs a real **CPT Developer Program**, including a **"CPT Zip API"** delivery option, with a 12-month renewable developer license. Commercial use is royalty-based per product/user type. | **Real AMA license required**, developer program exists. |
| **CDT** | ADA sells the CDT dataset via **app/print/manual products**; commercial/API licensing is **negotiated directly** with the ADA, no confirmed self-serve developer API found. | **Real ADA license required, no confirmed programmatic path.** |

This changes the shape of the build materially from the original one-size
sketch:

- **ICD-10-CM needs no BYO credential at all.** A direct, free, public API
  integration is buildable **today**, independent of anything else in this
  scope. Recommend building this piece regardless of what happens with
  CPT/CDT — it's real, free, zero-risk, and immediately upgrades every
  ICD-10 answer in the app from web-search-grounded to authoritative-source-
  grounded.
- **CPT has a real, concrete BYO path**: the practice's own AMA CPT
  Developer Program credential, added as a second `ALLOWED_SERVICES` entry
  in `api/sc-credentials.js` (same encrypted-storage pattern already proven
  for Stedi — no new crypto). A new `api/sc-cpt-lookup.js` calls the CPT Zip
  API / developer endpoints with the practice's own key, same shape as
  `api/sc-eligibility.js`.
- **CDT has no verified self-serve API to BYO against.** Building a
  `cdt: true` credential slot today would be guessing at an integration
  shape nobody has confirmed exists. Recommend the **upload path** instead
  for CDT specifically: the practice exports/uploads their own licensed CDT
  data (they already hold the right to use it clinically) into
  `sc_encoder`-shaped rows scoped to their `license_hash`. Revisit a real
  CDT API path if the ADA ever publishes one.

### Architecture, settled now (cheap), not deferred

Per `sairn-software-architect`'s standing rule — settle the data-model shape
before building, since changing it later is expensive:

- `sc_credentials` gains `cpt: true` (no schema change — jsonb, same table).
- A new `sc_icd10_cache` is **not needed** — NLM's API is fast and free
  enough to call live per lookup, same as the existing web-search fallback;
  caching would be premature.
- CDT upload data reuses `sc_encoder`'s existing shape (`code/type/desc/
  bundling`) rather than inventing a parallel table — `type` already
  supports an open string, just add `'CDT'` as a valid value.
- The existing "2026 Code Awareness Lookup" UI is the right integration
  point for all three: try the connected authoritative source (CPT
  developer key, or ICD-10 via NLM, or CDT via uploaded reference) **first**,
  fall back to the current web-search grounding only when no authoritative
  source is connected/matched — exactly the tiered pattern already proven by
  the Prebill scrub tool (local rule table first, web search fallback).

---

## Claim 2 — specialty coverage. Partially true, and the real finding is more specific than "coverage is missing."

### What's actually there — checked, not assumed

- `grep -ci` across the 9 named specialties + ophthalmology in
  `sairncode.html`: **zero real hits** for behavioral health, orthopedics,
  podiatry, cardiology, oncology, interventional radiology, DME,
  ophthalmology. (An "ASA" hit turned out to be a false-positive substring
  inside `scHasAiConsent` — checked directly, not trusted.)
- The app's own "Specialty" nav group contains exactly **two** panels:
  Telehealth and Anesthesia. Every other specialty gets the same generic
  system prompt and the same generic CRUD panels as every other kind of
  claim.
- `SAIRNCODE_SYSTEM_PROMPT` itself names **zero** specialties — it is one
  prompt for the entire platform.

### The Anesthesia panel: real math, real gap underneath it

Worth naming precisely rather than lumping in with "specialty coverage
missing" generally, since it's a different, more specific finding:

- The **time-unit formula is correct**: `timeUnits = minutes / 15`,
  `totalUnits = base + timeUnits` — that is the real, standard ASA
  convention, correctly implemented.
- **Base Units is a free-text number the coder types in** — there is no
  real ASA Relative Value Guide base-unit reference table behind it, no
  physical-status modifier (P1–P6) capture, and no payer conversion-factor
  ($/unit) output. The math is honest; the reference data behind one of its
  two inputs doesn't exist yet. This is a real, scoped, buildable gap — not
  a rebuild, an addition (a small reference table + two form fields), same
  shape as the Scrub Rules Reference's own real/verified/sourced discipline.

### Behavioral health and DME — two real, live probes run this session (not assumed)

Sent real questions through the live, authenticated `api/sc-ai.js`
(production, real session) to get real evidence rather than guessing at
what the AI would say:

1. **Behavioral health** — asked for the exact time thresholds
   distinguishing psychotherapy add-on codes 90833/90836/90838 and whether
   they vary by payer. Got back specific, **correct** thresholds (16 / 38 /
   53 minutes — the real, long-stable AMA figures) plus an accurate,
   appropriately-hedged breakdown of real Medicare-vs-Medicaid variance.
2. **DME** — asked about Medicare's KX modifier documentation requirements
   for power wheelchairs and whether the LCD changed recently. Got back a
   response that led with an explicit **"I need to be transparent about my
   limitations"** section, correctly refused to claim current post-2024 LCD
   specifics, and pointed to CMS directly — exactly the disclosure standard
   the app's own system prompt asks for.

**Neither probe found a fabrication.** Both suggest the general-knowledge
answer quality and hedging discipline hold up reasonably well even on
specialty-specific questions, on this small sample.

### What this means for the real gap — and the honest limit of this scoping pass

Two real probes are evidence, not a certification. **I am not a certified
medical coder, and neither is a live-tested but unverified answer to two
questions.** Concluding "behavioral health coverage is fine" from this would
repeat exactly the mistake this whole audit arc has been correcting — a
plausible-sounding, ungrounded claim standing in for real expert
verification (the same root cause as the original AAPC 65% score).

**The real, structural gap this scoping pass did confirm** is not "the AI
gives wrong specialty answers" — it's that **SAIRNcode has zero
specialty-aware structure anywhere in the app**: no specialty-scoped denial-
pattern tracking (the real `sc_denial_events` from item 3 has no specialty
field), no specialty-specific modifier/bundling checklists (Scrub Rules
Reference is specialty-agnostic), no specialty-specific documentation
checklists in the prior-auth draft tool. That is a real, nameable,
buildable gap — a structural one, not a knowledge one — and it does not
require inventing a coverage verdict to act on.

### Recommendation: build the mechanism, not the verdict

Per the Premortem run on this exact question earlier this session ("what
did the review method itself structurally miss") — the honest answer here
is that **no one on this team is positioned to personally certify clinical
coding coverage**, and manufacturing that certification would be the single
highest-risk fabrication this entire audit arc has fought. The buildable,
honest piece is a **self-service spot-check harness**:

- A small panel (or a mode on the existing AI Assistant) where a real coder
  submits a real specialty question, records **their own** pass/fail
  judgment against the answer, and that verdict is stored — real coverage
  data, produced by a real credentialed person, not guessed by either the AI
  or by me.
- Ship it with the 9-specialty list already named (behavioral health,
  orthopedics, podiatry, anesthesia, cardiology, oncology, interventional
  radiology, DME, ophthalmology) as starter categories, empty until a real
  coder populates it — same "empty by default, real-source-required"
  discipline as the Scrub Rules Reference.
- This turns "is coverage adequate" from an unanswerable question for this
  session into a real, growing, evidence-backed answer over time.

---

## Claim 3 — dashboard KPIs are static. Verified TRUE, no nuance.

- 96 `kpi-card` instances across the file. **Zero** have an `onclick`.
  **Zero** have `cursor:pointer` in the CSS. Checked mechanically, not
  sampled.
- `renderDashboard()` (and every sibling panel's own KPI renderer) computes
  real numbers from real localStorage-backed data — the numbers themselves
  are honest, they're simply not interactive.

### Scope: click-to-drill-down, SAIRNcode only (per instruction)

- Add a real click handler to each dashboard `.kpi-card` that navigates to
  the source panel and applies a real filter matching that KPI's own
  computation — e.g. "Denial Rate" drills into the Denial panel filtered to
  `status==='Denied'`, matching `renderDashboard()`'s own denominator
  exactly (not a re-derived, possibly-inconsistent filter).
- Reuse each panel's existing search/filter input rather than inventing a
  second filtering mechanism — set the value and call the panel's own
  `filterTable()`/render function.
- Real requirement, not cosmetic: the drill-down's row count must match the
  KPI number it came from, verified by a real click-through, not assumed
  from the code.

---

## Decision-gate pass (`sairn-decision-gate`)

**Bid/No-Bid** on "build CPT BYO + ICD-10 free-API + specialty harness +
KPI drill-down now": real opportunity (this is the literal, missing piece
of the original audit's own stated goal), real qualification gap closes
itself once scoped (ICD-10 needs zero new infra, CPT needs one new
credential type reusing existing crypto, KPI drill-down is pure client
work) — **passes cleanly**, unlike Phase 2c. No infra Michael doesn't
already have.

**Premortem** — "six months from now, SAIRNcode claimed real specialty
coverage and a customer's coder found it wrong." Prevented by NOT shipping
a verdict, only the mechanism to produce one honestly (above). "Six months
from now, the CDT credential slot sat there and nobody could ever configure
it because no real API exists" — prevented by choosing upload for CDT
specifically instead of guessing at an unconfirmed API shape.

**NIST AI RMF** — Measure: the two live probes are a real first Measure
signal, correctly scoped as insufficient for a coverage claim on their own.
Manage: the spot-check harness *is* the ongoing Measure/Manage mechanism —
recommend building it as infrastructure, not a one-time report.

---

## Recommended build order, once confirmed

1. **ICD-10-CM via NLM** — free, no credential, zero new risk. Ships
   first, upgrades every existing ICD-10 answer immediately.
2. **CPT BYO via AMA Developer Program credential** — new
   `ALLOWED_SERVICES.cpt`, new `api/sc-cpt-lookup.js`, same shape as
   Phase 1's Stedi integration.
3. **CDT via upload**, reusing `sc_encoder`.
4. **Anesthesia base-unit reference table** + physical-status modifier
   capture — small, scoped, same discipline as Scrub Rules Reference.
5. **Specialty spot-check harness** — the mechanism, not a verdict.
6. **Dashboard KPI drill-down** — independent of the above, can ship any
   time, SAIRNcode only per instruction.

No code written yet. Report back scope, per instruction — awaiting
confirmation before building any of the above.
