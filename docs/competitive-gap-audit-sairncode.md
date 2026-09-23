# Worldwide competitive-gap audit — SAIRNcode

**Status: research supplied by Michael 2026-09-23 from real findings. Every
"current state" verdict below was re-derived against `sairncode.html` at HEAD
by Cody before being written down. Several supplied items turned out to be
already built, and one turned out to have been considered and DECLINED in the
code with a stated reason — those are recorded as corrections in §6 rather
than shipped as gaps. One item supplied as "since built" is NOT built, and is
promoted to a real gap in §4.**

---

## 0. What this document closes, and the search that preceded it

This is the fifth audit of its kind and SAIRNcode is the app that never had
one. Four exist —
`2026-08-26` (roofing/dental/senior), `2026-08-27` (mechanical), `2026-09-02`
(StoneDesk), `2026-09-03` (build/vet/biz/grounds/cash) — and **`sairncode`
appears zero times across all four**, counted rather than assumed.

Earlier on 2026-09-23 this research was dispatched as "genuine chat-session
work, never committed", and a search for it came back empty across six
avenues: `docs/` and `docs/superpowers/specs/` by filename and by content,
`git log --all --diff-filter=A` on every branch, all four sibling clones
tracked and untracked, `docs/MASTER-PLAN.md` (which names `sairncode` only in
generated count tables and does not contain the word "research"), and a
competitor-vocabulary sweep over every tracked doc naming SAIRNcode. It was
reported as **unconfirmable rather than not-done**, and deliberately not
written up from nothing.

The research was real. It was not in the repository. **This file is the
artefact that absence needed** — the same correction the 2026-09-03 audit
records for its own five apps, where the same thing happened three times.

---

## 1. What SAIRNcode actually is, measured

Read from `api/_resources/sairncode.js` and the panel ids in the app, not from
a description:

- **28 registered resources.** `sc_claims`, `sc_prebill`, `sc_hcc`, `sc_drg`,
  `sc_rac`, `sc_denial`, `sc_denial_events`, `sc_ar`, `sc_revenue`,
  `sc_compliance`, `sc_fraud`, `sc_query`, `sc_telehealth`, `sc_anesthesia`,
  `sc_anesthesia_base_units`, `sc_auth`, `sc_auth_requests`, `sc_providers`,
  `sc_encoder`, `sc_scrubrules`, `sc_eligibility`, `sc_settings`,
  `sc_specialty_checks`, `sc_specialty_checklists`, `sc_coded_items`,
  `sc_credential_scope`, `sc_pctc`, `sc_dme`.
- **38 panels**, of which **fifteen are specialty surfaces**: `transport`,
  `ed`, `cos`, `pt`, `eye`, `uc`, `esrd`, `onc`, `mh`, `chiro`, `dermwound`,
  `maternity`, `drugadmin`, `modrouting`, `pctc`.
- **21 of the 28 resources are Tier A** on at least one axis
  (`docs/CRITICALITY-TIERS.md`), which is the highest proportion of any app on
  the platform.

---

## 2. Small-business tier — US

| # | Item | Current state, re-derived at HEAD | Verdict |
|---|---|---|---|
| A1 | **Fully autonomous coding with confidence-scoring and exception-only review** — the real 2026 category (CodaMetrix, Nym Health) | **`autonomous` appears ZERO times in `sairncode.html`.** `confidence` appears 20 times, but as per-suggestion confidence, not as a route-to-auto-post threshold. There is no exception queue and no auto-post path | **REAL GAP.** The largest one here, and it is a product decision before it is a build |
| A2 | **Real-time payer-eligibility-informed suggestions** | **HALF BUILT.** `panel-eligibility` exists and describes itself as *"Real-time patient coverage verification (270/271) through your own clearinghouse"*, and `sc_eligibility` stores `{patient, payer, status, plan, encounter_ref, service_types, checked_for, date}`. What does NOT exist is the feedback edge: nothing reads an eligibility result back into a coding suggestion | **PARTIAL GAP — the join, not the data** |
| A3 | **Pre-submission denial-probability scoring** | **CONSIDERED AND DECLINED IN THE CODE, with a measured reason.** See §6.1. `scPreSubmissionRisk()` produces COUNTS, never a predicted percentage | **NOT A GAP — a recorded decision** |
| A4 | **AI-drafted, evidence-backed appeal letters with mandatory human review** | **BUILT.** Appeal-letter drafting landed 2026-08-20 (Phase 3 item 6); the prompt carries hard rules and the output is gated on human review | **BUILT** |
| A5 | **Explainability / citation trail as its own buyer criterion** | **BUILT, and it is the app's strongest differentiator.** 29 `citation`/`explainab` occurrences; `sc_coded_items` stores `{code, code_type, encounter_ref, provider_id, provider_name, quote, quote_verified, reasoning, source_rule, reviewed_by, reviewed_at, created_by}` — a VERBATIM CLINICAL QUOTE plus the rule that justified the code, which is the artefact a coding review actually reads | **BUILT — lead with this** |

---

## 3. Small-business tier — Germany (DRG/OPS), directional

| # | Item | Current state | Verdict |
|---|---|---|---|
| B1 | **Hybrid-DRG (§115f SGB V, in force 1 Jan 2026)** blends inpatient and outpatient; most software is not built for it | **`Hybrid-DRG`, `115f` and `SGB` each appear ZERO times.** The four `OPS` hits are unrelated English words, not the German procedure classification | **UNBUILT, and correctly so — see §5** |
| B2 | Real-time AI suggestions drawn from the whole patient record validate the longitudinal approach | Directional confirmation of an architecture SAIRNcode already has in `sc_coded_items` | **VALIDATION, not a gap** |
| B3 | Honest vendor pattern: flagging complex cases for human review | Matches what A4 and A5 already do | **VALIDATION, not a gap** |

---

## 4. Specialty coverage — supplied as "since built", and ONE of them is not

Michael's research supplied these as design rationale rather than open work.
**Fourteen of fifteen check out. One does not, and it is a real gap.**

| Specialty | Supplied facts | Re-derived |
|---|---|---|
| **Critical care transport** (`panel-transport`) | two billing streams — HCPCS A-codes for transport, CPT 99466/67/85/86 for the accompanying physician; specialty gating; bundling risk; air ambulance under No Surprises Act IDR, ground not | **BUILT.** `99466` ×4; `No Surprises`/`IDR` ×5 |
| **Emergency Department** (`panel-ed`) | 99281-85 by MDM only, never time; 99291/92 time-based; cannot bill same-day with ED E/M by the same provider; **CY2023 99292 rule (104 min) stricter than CPT (75 min)**; paediatric ED 99293-96; a real 2026 HHS-OIG audit found $15M+ improper payments from wrong site-of-service | **BUILT.** `99291` ×7, `99292` ×15, `104` ×12, `OIG`/`site-of-service` ×3 |
| **Cosmetic / Reconstructive** (`panel-cos`) | same CPT is cosmetic (self-pay) or reconstructive (insurance) by documented medical necessity; separate direct-pay workflow; modifiers 59/51/76 | **BUILT** |
| **Physical Therapy** (`panel-pt`) | 8-Minute Rule aggregating all timed minutes first; KX threshold $2,480 for 2026 tracked cumulatively; **GP modifier required on every Medicare claim**; MPPR 100%/50%; 2026 RTM codes 98979/84/85 | **BUILT EXCEPT ONE.** 8-minute ×6, `2480` ×3, `KX` ×88, MPPR ×7, RTM 98979/98984/98985 all present. **`GP` as a whole word appears ZERO times.** The panel's own tooltip lists *"8-minute rule, KX threshold, CQ modifier, MPPR, 2026 RTM codes"* — **CQ, not GP.** They are different modifiers: CQ flags services furnished by a PTA, GP certifies the service is under an outpatient physical-therapy plan of care and is required on every Medicare therapy claim. **REAL GAP** |
| **Optometry / Ophthalmology** (`panel-eye`) | routine-vs-medical decides insurer, code family and payout; dual-billing split (medical exam + 92015 refraction); co-management modifiers -54/-55 | **BUILT.** `92015` ×6 |
| **Urgent Care** (`panel-uc`) | not its own code family; modifier 25 ties E/M + procedure + diagnostics; S9083/S9088 flat fee vs Medicare's standard E/M; true ED codes legally restricted to hospital-based EDs | **BUILT.** `S9083`/`S9088` ×7 |
| **Dialysis / ESRD** (`panel-esrd`) | Medicare's monthly bundled/capitated model | **BUILT** |
| **Oncology / infusion** (`panel-onc`) | J-codes plus JW/JZ waste modifiers | **BUILT.** `JW`/`JZ` ×60 |
| **Mental Health / Counseling** (`panel-mh`) — supplied as the richest specialty | LPC/LMFT/LMHC Medicare-eligible only since Jan 2024, flat 75% fee schedule, barred from 90792 and E&M add-ons; psychotherapy notes carry stricter HIPAA status (45 CFR §164.501); telehealth same CPT, only modifier/POS changes the rate (~$42/session swing); NCCI Ch. XI (Jan 2026) sets four same-day bundling rules | **BUILT.** `90792` ×2, `45 CFR` ×1, `NCCI` ×8 |
| **Provider-specialty-to-billable-code validation** | confirmed five times independently; core architecture | **BUILT AND IS THE ARCHITECTURE.** `specialty` ×112, backed by `sc_specialty_checks`, `sc_specialty_checklists` and `sc_credential_scope` |

### 4.1 The one real specialty gap

**The GP modifier is absent from the PT panel.** Every other PT fact supplied
is implemented. `\bGP\b` returns nothing in the entire file, and the panel's
own tooltip enumerates CQ where the research says GP.

Why it matters more than one missing string: GP is required on **every**
Medicare outpatient therapy claim, so its absence is not an edge case — it is
a claim-level omission on the whole specialty. It also sits directly beside
the KX threshold logic that IS built, which is the more sophisticated of the
two.

**Not fixed here.** This is an audit; a coding change to a Tier A app is a
separate claim with its own review obligation.

---

## 5. Mid-market tier — the named enterprise bar

CodaMetrix's named customers are **Mass General Brigham, Mayo Clinic, Yale
Medicine and Henry Ford**. The bar that implies:

- high-volume autonomous coding across many specialties at hospital-system
  scale — **§2 A1, the real gap**;
- full longitudinal record integration — partially answered by
  `sc_coded_items`' quote-and-rule trail;
- deep EHR interoperability, **Epic dominant** — not measured here and not
  asserted.

**SAIRNcode's existing panel set already covers real enterprise RCM breadth ON
PAPER** — claims, prebill, HCC, DRG, RAC, denial, AR, revenue — and that is
exactly the sentence to be careful with. Breadth of panel is not depth of
function, and this audit measured the presence of vocabulary and resources,
not the sufficiency of any one workflow at scale. **A direct depth check on
those eight panels is owed before pitching a large hospital system**, and it
is not performed in this document.

### 5.1 Why Germany is correctly unbuilt

§115f took effect 1 January 2026. Building a Hybrid-DRG grouper before the US
autonomous-coding gap in §2 A1 is closed would be answering a smaller market's
newer question while the larger market's defining 2026 category sits open.
Recorded so "not built" is not mistaken for "not considered".

---

## 6. Corrections — items supplied as gaps that are not

The 2026-09-03 audit records four of these for its five apps. SAIRNcode has
one, and it is the most instructive on the platform.

### 6.1 Denial-probability scoring was considered and DECLINED, in writing, in the code

`sairncode.html` carries the decision verbatim above `scPreSubmissionRisk()`:

> **WHAT THIS DELIBERATELY IS NOT: a denial-probability score.** The request
> asked for "denial-probability scoring per claim," and the honest answer
> after checking the real data is that no such number can be computed here.
> Checked live against production with a real admin session before writing any
> of this: `sc_denial_events` had 0 rows, `sc_denial` 0, `sc_ar` 0,
> `sc_prebill` 0, and `sc_claims` held exactly 1 row which is the known
> `CLM-MIGRATION-TEST` residue, not real data. There is no labelled outcome
> set, no base rate, and nothing to calibrate a predicted probability against.

and states the distinction it is built on:

> `"34% chance this claim is denied"` → a **PREDICTION**. Requires a calibrated
> model. We have none. Never produced here.
> `"this payer denied this exact code 3 of your 12 logged denials"` → a
> **COUNT** of events the practice itself recorded. Real, checkable, and
> genuinely useful. This is what gets produced.

**This is the fabricated-KPI discipline applied to a competitive feature.** A
plausible percentage on a claim screen is indistinguishable from a calibrated
one to the buyer, and SAIRNcode refused to produce it rather than shipping a
number with nothing behind it. It gets more useful as real denials are logged,
by construction.

**Sell this as the decision it is.** A competitor's confidence percentage
invites exactly one question — *calibrated against what?* — and SAIRNcode can
answer it.

---

## 7. What this document does NOT establish

- **No depth check was run on the eight enterprise RCM panels.** §5's "on
  paper" is literal: presence of panels and resources, not sufficiency at
  hospital scale.
- **Every "BUILT" verdict is a vocabulary-and-resource measurement.** A code
  appearing in the file means the app knows about it; it does not mean the
  rule around it is correct. The GP finding is what that limit looks like when
  it bites — fourteen specialties passed the same test GP failed, and only a
  reader who knew CQ and GP are different modifiers would have caught it.
- **No competitor product was used or tested.** Every competitor claim is
  Michael's supplied research, recorded as supplied.
- **EHR interoperability was not measured at all**, in either direction.

---

## 8. Decay

Like the four audits before it, this file predicts its own decay. Its state
cells are mostly *"this vocabulary appears N times"*, which can only move when
a feature is genuinely built or removed — the same structural property that
kept the 2026-09-03 audit's 33 cells stable over twelve days while the
2026-08-26 audit's moved. **Re-derive before building anyway**; one
confirmation is not a warranty.
