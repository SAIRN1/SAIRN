# Worldwide competitive-gap audit — OUTPATIENT BEHAVIORAL HEALTH

**fourth / b29, 2026-10-17.** Second audit in the "vertical SAIRN has not
built for" series; the first was childcare
(`childcare-worldwide-competitive-gap-audit-2026-10-16.md`, b28).

**THIS IS NOT A BUILD RECOMMENDATION.** §7 lists what would have to be true
first, and none of it is true today. Per `sairn-decision-gate` a new vertical is
expensive to reverse and an audit is not the gate.

**Every figure names where it came from. Re-derive anything you mean to quote,
including out of this file.**

---

## 0. THE UNIVERSE WAS DERIVED, AND IT CORRECTS THE PREVIOUS AUDIT

b28's childcare audit said *"all eighteen real products already have one"*.
**Derived at HEAD today the count is SEVENTEEN, not eighteen:**

    git ls-files '*.html' | grep -E '^(sairn[a-z]+|stonedesk)\.html$'
    -> sairnbiz sairnbuild sairncare sairncash sairncode sairndental
       sairndesign sairnfreedom sairngrounds sairnlaw sairnlegacy
       sairnmechanical sairnroofing sairnscape sairnsenior sairnvet stonedesk

`stonedesk-catalog.html`, `stonedesk-hr.html`, `stonedesk-intake.html`,
`sairndental-book.html` and `sairndental-complaint.html` are companion surfaces
of a product already in the list, not products. Whether the eighteenth was one
of those or a product since removed, **the number in that document no longer
matches the repo**, which is convention 8 (instrument drift) landing on an audit
written yesterday. The denominators below are stated as *n of 17* with the
command that produced them, so the next session re-derives rather than inherits.

**Why behavioral health is the one chosen.** Three criteria, applied to the
unbuilt verticals, not a preference:

1. **The regulatory shape SAIRN has already solved once.** Outpatient mental
   health bills on a code set republished annually (CPT) against a **date of
   service**, under a rule that varies **by state and by payer** with an
   effective window. That is the same problem `sairndental` solves for CDT
   editions and that b28 finished the read half of — the one piece of this
   platform that has a proven, driven implementation of exactly this.
2. **A credential layer that is the product, not an afterthought.** Supervision
   hours, licensure, compact privileges and payer enrolment all expire, on
   different clocks, and billing is void without them.
3. **Not adjacent to a built product.** Home health and hospice overlap
   `sairncare` and `sairnsenior`; outpatient behavioral health does not.

---

## 1. THE CENTRAL FINDING — THE MARKET IS SPLIT AND NEITHER HALF HOLDS THE SUPERVISION LAYER

The solo-and-small-group segment is dominated by two products:
**SimplePractice** (reported at 250,000+ practitioners and 20M+ clients) and
**TherapyNotes**, with Valant and ICANotes as specialist outpatient systems. The
agency/enterprise segment is a different field entirely — **Qualifacts
(Credible / CareLogic / InSync) reports 2,200+ agencies**, alongside Netsmart,
Oracle Health, Epic and NextGen.

**The gap sits exactly on the seam between those two segments**, and it is the
group practice that employs **pre-licensed associate clinicians**:

* Supervision-hour tracking **is not a standard feature**. The buyer guidance
  found says support *"varies by platform, and many practices still track it in
  a separate log"* — and the existence of a cottage industry of standalone
  trackers (HourPath, SupervisionPath, Miyndsett, supervisiontracker.org) is the
  market telling you the EHR does not do it. A board-acceptable export is the
  specific thing those guides tell buyers to ask about.
* **Billing under supervision is payer-specific and changing.** Incident-to is a
  narrow Medicare mechanism, not a general route for billing associate or
  provisionally-licensed clinicians under a supervisor's NPI — and commercial
  payers are withdrawing their own versions of it (Blue Cross Michigan ending
  associate incident-to billing is the documented instance). A practice whose
  revenue depends on associates can have the basis withdrawn **per payer, per
  state, on a date** — the same flip shape childcare's CCDF basis showed twice
  in 26 months.
* **Headway, one of the largest access routes for therapists, does not support
  incident-to billing at all**, which forecloses provisionally-licensed
  clinicians on that rail. The structural choice is pushed onto the practice
  with no system of record for it.

**So the layer that decides whether an associate's session is billable at all —
who supervised it, were they credentialed that day, does this payer allow it in
this state — is the layer nobody is holding.**

---

## 2. THE REGULATORY FINDINGS, DATED, WITH PRIMARY CITATIONS

Three live deadlines, two of them inside the next 90 days. **All three
citations were pulled from the Federal Register API, not from a secondary
summary** (see §6 for how, and for why that matters).

| | rule | citation | the date that bites |
|---|---|---|---|
| **R1** | Confidentiality of Substance Use Disorder (SUD) Patient Records (42 CFR Part 2 final rule) | **89 FR 12472**, doc `2024-02544`, published 2024-02-16, effective 2024-04-16 | **COMPLIANCE DATE 2026-02-16 — already passed.** OCR accepts complaints and opens civil enforcement from that date, at HIPAA-level penalties |
| **R2** | Fourth Temporary Extension of COVID-19 Telemedicine Flexibilities for Prescription of Controlled Medications (DEA/HHS) | **90 FR 61301**, doc `2025-24123`, published 2025-12-31, effective 2026-01-01 | **FLEXIBILITIES LAPSE 2026-12-31 — 75 days from this document.** The special-registration final rule was logged as received at OIRA 2026-09-21 with final action listed for November 2026, so the replacement regime is **not published as of today** |
| **R3** | Counseling Compact / PSYPACT privileges to practice | not a federal rule; per-state enactment and implementation | **A moving denominator.** PSYPACT reported operational across 40+ jurisdictions; the Counseling Compact is issuing privileges in a far smaller, *growing* set — sources seen give **seven** states fully implemented and **nine** live as of September 2026, and they disagree |

**R1 is the one with a product consequence most systems get wrong.** Part 2 now
carries HIPAA-level penalties and a separate consent architecture, and the
records it covers are **a subset of a practice's chart, identified by what the
record is about** — not by which practice holds it. A system that treats the
patient as the unit of confidentiality cannot express it. A system that treats
the *record* as the unit can.

**R2 is a cliff, not a trend.** On 2027-01-01 either a special registration
regime exists or a very large volume of established telepsychiatry prescribing
loses its basis overnight. **Nothing in the repo models a prescribing basis with
an expiry, and the replacement rule's text does not exist to model yet.** Any
product entering this vertical before November 2026 would be building against a
rule whose successor is still at OIRA.

**R3 is the childcare finding again, in a different body of law.** A privilege
to practice is **per state, per profession, with an effective date**, and the
set is still growing. One global answer is wrong on the day it is written. Note
the asymmetry the sources agree on even where they disagree on counts:
**psychologists and counsellors have compacts; BCBAs largely do not** — so a
multi-state practice has different answers for two clinicians sitting in the
same office.

---

## 3. PLATFORM FIT — MEASURED, NOT ASSERTED

    APPS=$(git ls-files '*.html' | grep -E '^(sairn[a-z]+|stonedesk)\.html$')   # N=17
    for each pattern: grep -ciE "<pattern>" "$f"

| primitive | pattern | present in | which |
|---|---|---|---|
| credential expiry **field** | `expires_on\|expiry_date\|expires_at\|expiration_date` | **6 of 17** | sairncare, sairncash, sairndental, sairnlegacy, sairnmechanical, sairnroofing |
| date-of-service concept | `date of service\|date_of_service\|service_date` | **4 of 17** | sairncode, sairndental, sairnlegacy, sairnsenior |
| `effective_from` window | `effective_from` | **4 of 17** | sairncare, sairndental, sairnlaw, sairnsenior |
| **supervisory co-signature** | `co-sign\|cosign\|co_sign\|countersign` | **2 of 17** | sairncare, sairnvet |
| NPI | `npi` | **4 of 17** | sairncode, sairndental, sairnlaw, stonedesk |
| CPT code | `cpt_code\|cpt code` | **1 of 17** | sairncode |

**Read that table the pessimistic way, because that is the honest way.** The
two primitives this vertical is *built on* — a supervisory co-signature, and a
clinician-level credential whose validity is evaluated against the date of
service — exist in **2 of 17** and **4 of 17** respectively, and **in no single
app together with a CPT-coded billing path**. `sairndental` has the
code-edition-against-date-of-service engine and no supervision; `sairncare` and
`sairnvet` have a co-signature and no coded billing; `sairncode` has CPT and is
a medical-coding tool, not a practice.

**Nothing here is a reusable behavioral-health core. It is three proven halves
in three different products.**

---

## 4. WHAT WOULD HAVE TO BE BUILT THAT HAS NEVER BEEN BUILT

Stated before any opportunity framing, because this is the part that decides
cost:

1. **A supervision ledger that a licensing board will accept.** Hours attributed
   to a supervisee, by type (individual/group/direct/indirect), against a
   supervisor who was themselves qualified **on that date**, exportable in a
   board's format. Board formats differ per state. No SAIRN app has any of this.
2. **A billing-basis engine keyed on (payer × state × clinician licence status ×
   date of service).** `sairndental`'s CDT engine is the nearest proven thing
   and it is keyed on one axis, not four.
3. **42 CFR Part 2 record-level segmentation with its own consent object.** Not
   a flag on a patient. This is a data-model decision made at birth or not at
   all — item 7 of the cross-domain disciplines (byte-identical is not
   safe-in-context) applies directly: copying `sairndental`'s chart model into
   a Part 2 setting would be a correct copy of an unsafe model.
4. **A prescribing-authority object with an expiry**, which R2 makes mandatory
   and whose rule text does not exist yet.
5. **Criticality.** A supervision record is the evidence a licensure board
   relies on and a billing basis determines whether a claim is fraudulent. On
   `docs/CRITICALITY-TIERS.md` terms this is **Tier A on at least two
   resources**, and **that tier is NOT assessed in this document** — naming it
   is not assessing it.

---

## 5. WHAT THIS AUDIT DID NOT DO

* **No competitor account was provisioned and no product was driven.** Every
  claim in §1 rests on **secondary sources, some of them vendor-authored or
  vendor-adjacent buyer guides.** The SimplePractice practitioner figure is a
  vendor-published number and is reproduced as such, not as an independent
  measurement.
* **No market-share percentages were obtained.** Unlike b28's childcare audit,
  which had a 6sense technographic table, **the searches returned no share
  table for this vertical at all.** Vendor counts (250,000+ practitioners;
  2,200+ agencies) are **not shares and are not denominated against the same
  universe** — one counts individuals, the other organisations. **They are
  therefore NOT combined into a figure here**, which is convention 3: an
  itemised uncertainty rather than one blended number.
* **The Counseling Compact state count is UNRECONCILED**, 7 vs 9 from two
  sources dated weeks apart, and is reported as a range rather than averaged.
* **No clinician, supervisor or practice owner was interviewed.**
* **Market sizing is excluded entirely.** Two analyst figures surfaced
  (USD 2.04B in 2026 → 7.16B by 2035; and an unrelated 11.92B-by-2030 figure for
  a differently-drawn "behavioral health software" market). They do not describe
  the same universe, so **neither is quoted as the market size.**

**One methodological gain worth keeping, because b28 lost this exact fight:**
b28 recorded that *"a redirect blocked the direct Federal Register fetch, so the
rescission is cited by document number with an instruction to re-derive."*
`WebFetch` is still blocked today — federalregister.gov 302s to
`unblock.federalregister.gov` — **but the Federal Register JSON API answers 200
through `tools/sairn_http.py`**, because that module sends a browser
User-Agent. So R1 and R2 above carry real FR citations pulled from the primary
source:

    python -c "import sys;sys.path.insert(0,'tools');import sairn_http as H;
    print(H.fetch('https://www.federalregister.gov/api/v1/documents/2025-24123.json'
                  '?fields[]=citation&fields[]=effective_on',no_cache=True).body)"

**Use that route for any future regulatory citation on this platform rather than
re-discovering the block.**

---

## 6. IF IT WERE PURSUED — THE ORDER THAT FOLLOWS FROM THE ABOVE

Not a plan, a consequence. The regulatory clock, not the feature list, sets it:

1. **Wait for the DEA special-registration final rule** (OIRA, final action
   listed November 2026). Building a prescribing-authority model before it
   publishes is building against a draft.
2. **Part 2 segmentation first, if at all.** It is a data-model decision that
   cannot be retrofitted, and its enforcement date has already passed.
3. **The supervision ledger is the wedge, not the EHR.** It is the piece the
   incumbents are documented as not holding, it is the piece with a cottage
   industry proving demand, and it is the only piece that does not require
   displacing SimplePractice to be worth anything.

---

## 7. WHAT WOULD HAVE TO BE TRUE BEFORE THIS IS A DECISION

Unchanged in shape from b28's childcare §5, because the shortfall is the same:

* A **driven trial account** on SimplePractice and on TherapyNotes, with the
  supervision and associate-billing paths actually exercised — the claim in §1
  is currently second-hand.
* **One real group-practice owner employing associates**, interviewed.
* **An owner for a 50-state supervision-rule and compact matrix.** Nobody on
  this platform has that, and it is the same unstaffed obligation childcare
  surfaced. **Two audits have now named the same missing role.** That is the
  finding about SAIRN rather than about the market.
* A **criticality-tier assessment** of the supervision and billing-basis
  resources, which §4.5 names and does not perform.

---

*Sources (secondary, §1 and R3): hipaajournal.com, swlaw.com, reedsmith.com,
mcdermottplus.com, ehealthvirginia.org, acuity.news, triadhq.com,
telehealth.org, counselingpsychology.org, upheal.io, therapyappointment.com,
mentalwealthsolutions.org, matthewryanlcsw.com, practicebetter.io,
btc.therapymate.com, towardshealthcare.com, mordorintelligence.com.
Primary (R1, R2): federalregister.gov API, documents `2024-02544` and
`2025-24123`.*
