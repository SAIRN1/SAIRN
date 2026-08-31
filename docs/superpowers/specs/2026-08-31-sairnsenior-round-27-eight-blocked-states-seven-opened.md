# SAIRNsenior — round 27: seven of the eight "blocked" states opened, and none of them were blocked

2026-08-31. **Research only.** Forty-first document in the series.

> **CORRECTED THE SAME DAY BY ROUND 28.** This document says four times that
> **Idaho is "the only genuine failure of the eight."** That is wrong. Idaho
> opened on the same two angles as the other seven — a moved host
> (`/rules/current/16/…` now 302s to `/current-rules/`) and a client-rendered
> list that `curl` cannot see. **The real figure is eight of eight, and zero of
> the eight were ever blocked.** See
> `2026-08-31-sairnsenior-round-28-idaho-was-not-blocked-either.md`.
> The Idaho 404 that produced the "outage" label had been carried forward
> untested for twenty-plus rounds — which is the same error this document is
> about, committed one more time.

Round 26 corrected round 25 by finding a stale tab. **This round finds the
larger version of the same mistake.** Every one of the eight diagnosed states
carried a diagnosis about a *transport* — "LexisNexis-gated", "publisher SPA",
"soft-200", "canvas PDF, no text layer". **Seven of the eight opened on the
first or second attempt once a different tool was used.** Not a different URL —
a different *tool*.

| State | Round 25/26 diagnosis | What actually happened |
|---|---|---|
| **Utah** | publisher SPA; its own API serves the app | **Browser renders the full rule.** Read in one navigation. |
| **Kansas** | index is chrome only; PDF path soft-200s | **`sos.ks.gov` moved to `rules.ks.gov`.** The soft-200 was a redirect to the new host. |
| **Connecticut** | soft-200 on two publishers | **eRegs portal works.** My section-number format was wrong, not the site. |
| **Alabama** | LexisNexis-gated | **Not gated at all.** Full admin code, full-text search, open. |
| **Mississippi** | LexisNexis-gated | **Not gated at all.** SOS admin-code portal serves a 1,187-page authenticated PDF. |
| **Alaska** | index server-side, content client-side, no route | **Documented AJAX endpoint** found in the site's own `statutes.js`. |
| **Arizona** | canvas PDF, no text layer — **"genuinely blocked"** | **The file has a perfect text layer.** The *viewer* rendered to canvas. `curl` + local extraction reads all 343 pages. |
| **Idaho** | state-declared outage | **Unchanged.** `adminrules.idaho.gov` still 404s. The one that stayed shut. |

> **Round 26 said Arizona "remains unresolved" and that the stale-tab fix "does
> not apply" to it. Both true, and both beside the point** — the fix that applied
> was to stop reading the PDF *through a browser* and download it instead. It
> took one `curl` with a browser User-Agent and `pypdf`.

---

## 1. The method finding, which matters more than any single state

**Every blocked-state diagnosis in rounds 21–26 was produced by one tool, and
named as a property of the publisher.** Three tools were needed and each opened
states the others could not:

| Tool | What it opens | What it cannot do |
|---|---|---|
| **`curl`** | static HTML, PDFs, AJAX endpoints | renders no JavaScript — every SPA looks like an empty shell or a soft-200 |
| **Chrome** | SPAs (Utah, Kansas, Alabama, Mississippi, Connecticut) | cannot read a canvas-rendered PDF viewer; caps extraction around 50 KB |
| **`curl` → local PDF text extraction** | large PDFs and canvas-viewer PDFs (Arizona, Mississippi) | nothing here it failed at |

> **"The site is blocked" was never observed. What was observed was "this tool
> returned nothing."** Those are different claims and they were written down as
> the same one, eight times.

Two smaller corrections from the same root:

- **A browser User-Agent changed Arizona from 403 to 200** on the identical URL.
  A 403 is not "the host refuses" until a plain UA has been tried.
- **`rules.sd.gov/DisplayRule.aspx` 302s to a Microsoft sign-in**, which I nearly
  logged as "South Dakota is behind auth". **The site is fully public** — that one
  path is the administrator console. Opening the root in a browser showed it
  immediately. *The stale-tab rule, applied in reverse: check in the browser
  before concluding from `curl`.*

---

## 2. Four distinct regulatory archetypes on the aide-qualification axis

This is the substantive payoff. The states that opened do not vary in degree —
they vary in **kind**, and a product with one qualification model cannot
represent all four.

### Archetype A — state credential, state test, state registry (Kansas)

**K.A.R. 28-51-113, -115, -116.** The most prescriptive found so far, and the
only one with a genuine *stacking* structure:

- Base: **Kansas-certified nurse aide in good standing on the public registry**,
  plus a **20-hour** department-approved home health aide course.
- Then a **state test**: 30 multiple-choice questions, **22 to pass**, **three
  attempts per year**, and **failure within one year forces retaking the entire
  course**.
- **Prescreen at an eighth-grade reading level** before enrolling.
- **Trainee window: one 90-day period only**, never renewed.
- **A lapsed-credential fast path (28-51-115):** an **inactive LPN or RN licensed
  within 24 months**, a licensed mental health technician, or someone trained in
  an accredited nursing/MHT program within 24 months **skips the CNA-plus-20-hour
  requirement entirely and goes straight to the state test**. Fail it once and
  they must take the 20-hour course after all.
- Accommodations are allowed, but **no oral or interpreted test** — reading and
  writing are declared an essential job task. A **bilingual dictionary** and one
  extra hour are allowed for limited English proficiency, which is explicitly
  **not** treated as a disability.

### Archetype B — state curriculum with named deemed-equivalent routes (Connecticut)

**R.C.S.A. § 19-13-D83.** A **75-hour** commissioner-adopted training program
with a 13-element curriculum, competency evaluated by an **RN with 2 years'
nursing experience, 1 of it in home health** — and then **six separate ways to
be deemed to have already completed it**:

1. Employed as an aide before 1 January 1993 (grandfather).
2. Completed the state-sponsored nurse assistant program before 1993.
3. Completed a nurse aide program under § 19-13-D8t — **still owes the competency
   evaluation**.
4. Completed **≥75 hours** of fundamental nursing skills in an approved PN or RN
   program — still owes the competency evaluation.
5. **Out-of-state aide** with documentation meeting the same curriculum — still
   owes the competency evaluation.
6. Any deemed person gets **10 hours of agency orientation** before touching a
   patient.

Plus a **lapse rule**: **24 consecutive months** without paid nursing or
nursing-related work voids it and forces a new competency evaluation.
An aide rated "unsatisfactory" in **more than one** subject area has not passed;
in exactly one, they may not perform that task without direct nurse supervision
until retrained and re-evaluated.

### Archetype C — federal credential plus criminal-history gate (Alaska)

**7 AAC 12.519.** No state curriculum or state test. Instead four conditions:

- **Nurse aide certified by the Board of Nursing** (AS 08.68.331–.336);
- **absent from the registry** as having committed abuse, neglect, or
  misappropriation;
- a **valid criminal history check** (AS 47.05.300–.390), **with a variance
  mechanism at 7 AAC 10.935** — the only explicit second-chance door found so far;
- **agency competency evaluation** across 13 named skill areas before any patient
  contact.

Then **12 hours of in-service per calendar year**, an RN or therapist supervisory
visit **every two weeks**, and **direct observation of in-home performance at
least every three months**.

### Archetype D — fully delegated, outcome-based (Arizona, Mississippi)

**A.A.C. R9-10-1206** prescribes **no hours, no test, no registry**. The
administrator must define required qualifications, skills and knowledge **from
the job description and the acuity of the patients served**, then **verify and
document** them before the person provides services. Everything else is a
personnel-record and TB-clearance requirement. Supervision carries the load: an
RN or therapist **assigns tasks in writing**, verifies competency, and meets the
patient **every two weeks** — or **every 60 days** where only aide services are
furnished.

**Mississippi (15 Miss. Admin. Code Pt. 16, R. 46.29.2)** is the same archetype
by a different route: an aide needs **"previous work experience as a nurses aide
or home health aide and/or" a special program**, and the *agency* must build a
department-approved training program for "unqualified" aides — with **duration
and subject matter deferred to Medicare requirements** rather than stated.
**12 hours of continuing education per year.** No state test, no state home
health aide registry.

> **A worked example of why the archetype matters.** A single "aide qualified:
> yes/no" field is correct in Kansas and meaningless in Arizona. Kansas needs
> *registry ID, course completion date, test date, attempt count, 90-day trainee
> clock*. Arizona needs *which job description, which acuity, who verified,
> when*. Connecticut needs *which of six deeming routes, plus a 24-month
> inactivity clock*. Alaska needs *registry status, criminal-history variance,
> 13 competencies*. **These are four different data models, not four
> configurations of one.**

---

## 3. Two states where the entry gate is not a qualification at all

### Alabama — the state says in its own rule that it does not license

> **"There is no licensure requirement for home health agencies in Alabama."**
> — Ala. Admin. Code r. **410-2-4-.07**(1)(b)

**Confirmed structurally, not just quoted.** The full chapter list for Agency 420
(Department of Public Health) was read: it licenses hospitals, nursing
facilities, assisted living, hospices, birthing centers, ESRD centers and more —
**and contains no home health chapter.** A full-text search for the phrase "home
health agency" across the entire Alabama Administrative Code returns **18 hits,
none of them a licensure chapter**: SHPDA certificate-of-need rules (agency 410),
Medicaid provider rules (560-X-12, -36, -44, -57), and a workers' compensation
fee rule (480-5-5-.30).

**Entry is gated by Certificate of Need instead, and the gate is numeric:**

- Need is computed **per county**, three years forward, from a weighted
  persons-served methodology split **75 % age 65+, 25 % under 65**.
- **APNS ≥ 100 → need for exactly one additional provider. APNS ≤ 99 → none.**
- **At most one application approved per county per cycle.**
- A newly approved provider gets **18 months** before anyone else may apply for
  that county.
- **Favourable consideration** for agencies meeting the statewide average of
  charity care plus self-pay, floor **1 %**.
- An intervenor opposing someone else's CON **may not cite its own utilization
  data** unless it has already filed its SHPDA survey.

> **This is a market-entry regime wearing the file name of a licensure regime.**
> It is the most distinctive state structure found in twenty-seven rounds.

### South Dakota — no home health article exists in the rules either

Round 26 established that **SDCL 34-12 licenses institutions and omits home
health**, and that **ch. 34-3A "Home Health Services" is county-and-municipal
finance**. The remaining open question was the administrative rules.

**The full ARSD article list has now been read.** Article 44 (Health) runs
44:02 through 44:90 and includes assisted living centers (44:70), nursing
facilities (44:73), **nurse aide (44:74)**, hospitals (44:75), adult foster care
(44:77), inpatient hospice (44:79), residential hospice (44:80), community living
homes (44:82). **There is no home health agency article.**

**44:04 "Medical Facilities" was checked directly and is a historical shell** —
every chapter in it is marked *Transferred* or *Repealed*, the bulk moved to
44:73 in October 2015.

**Honest limit:** this is a read of the ARSD article index plus one article, and
of SDCL Title 34's chapter list. **It is strong evidence, not proof**, that South
Dakota does not license home health agencies. A full-text SDCL search has not
been run.

---

## 4. Utah, read in full

**Utah Admin. Code R432-700** (effective 07/06/2023, continuation noticed
08/06/2026) — the whole rule, 28 sections. On the qualification axis:

- **Certified Nursing Aide:** at least **18**, **certificate of completion within
  six months of hire**, **CPR certified**.
- **Personal Care Aide:** **18**, written instructions from a supervisor, first
  aid training, demonstrated competency, and **a minimum of six hours in-service
  per calendar year, prorated in year one**. A PCA may remind and open containers
  but not administer.
- **Administrator:** **at least one year of managerial or supervisory
  experience** — no degree requirement, unlike Connecticut's D81, which requires a
  baccalaureate in nursing plus two years, or a related-field baccalaureate with
  health-services concentration.
- **RN supervisory visits:** initial assessment; **every two weeks** for skilled
  clients; **every three months** for long-term maintenance; and any time the
  condition may have changed.
- **Plan of care reviewed at intervals not exceeding 60 days.**
- Unlicensed staff may administer medication **only by delegation** under
  R156-31B-701, with documented supervision, evaluation and training.

**Mississippi adds one scaling threshold nobody else states numerically:** the
supervising nurse may **also be the administrator until the census reaches 25**;
may carry a scheduled patient load until **50**; **above 50 must be full-time
supervisory** (R. 46.23.3).

---

## 5. Where the eight now stand

| State | Status after this round |
|---|---|
| **Utah** | **CLOSED** — R432-700 read in full. |
| **Kansas** | **CLOSED on the qualification axis** — 28-51-113, -115, -116 read in full; article index captured. |
| **Connecticut** | **CLOSED on the qualification axis** — 19-13-D83 read in full; D66–D79 and D80–D92 both identified. |
| **Alabama** | **CLOSED** — no licensure exists; CON methodology read in full. |
| **Mississippi** | **CLOSED on the qualification axis** — ch. 46 subchapters 22, 23, 29, 38 read; full 1,187-page part cached. |
| **Alaska** | **CLOSED on the qualification axis** — 7 AAC 12.500–.590 identified, .516 and .519 read in full. |
| **Arizona** | **OPEN AND READ** — 9 A.A.C. 10 art. 12 (R9-10-1201 – 1209); R9-10-1206 read in full. |
| **Idaho** | **STILL CLOSED** — `adminrules.idaho.gov` 404s. The only genuine failure of the eight. |
| *(Indiana)* | **STILL ON HOLD** — credential decision, untouched. |

**Seven of eight opened. One of eight was real.** That is the same ratio round 26
found on a smaller sample and did not generalise from.

---

## 6. Tier 2 — what is still open

| Item | Status |
|---|---|
| Kansas 28-51-100 definitions, -112 training, -114 instructors, -117/-118 supportive care and HCBS | **ROUTE OPEN, NOT READ** — the non-medical tier is where a consumer product actually lives. |
| Connecticut D66–D79 (home health *care* agencies, the skilled regime) | **ROUTE OPEN, NOT READ** — only the homemaker-aide regime D80–D92 was read. |
| Alaska 7 AAC 12.505–.517, .521–.590 | **ROUTE OPEN, NOT READ** — only .516 and .519. |
| Alaska 7 AAC 10.935 (criminal-history variance) | **NOT READ** — the only second-chance mechanism found; worth reading on its own. |
| Arizona R9-10-1201 – 1205, 1207 – 1209 | **ROUTE OPEN, NOT READ.** |
| Mississippi ch. 46 subchapters 6–14 (classification, licence, application) | **CACHED, NOT READ.** |
| Mississippi ch. 54 nurse-aide registry | **PARTIALLY READ** — and note it defines abuse findings **only in terms of long-term care residents**, so the registry gating home health hiring is scoped to a setting that is not home health. Worth confirming. |
| South Dakota — full-text SDCL search | **NOT RUN** — needed before "South Dakota does not license home health" is stated without qualification. |
| **Idaho** | **CLOSED** — state outage, retried once this round, unchanged. |
| **Indiana** | **ON HOLD.** |

## 7. Method notes

- **Name the tool, not the publisher.** "LexisNexis-gated" was written twice about
  sites that were never gated. The honest form of that note is *"`curl` returned
  a shell; browser not yet tried."*
- **A moved host looks exactly like a broken one.** Kansas's soft-200 was
  `sos.ks.gov` redirecting to `rules.ks.gov`. A browser shows the new URL in the
  tab; `curl -w` shows only the status code unless you ask for the effective URL.
- **A canvas PDF viewer is a viewer problem.** Download the file and extract
  locally. Arizona cost six rounds as "genuinely blocked" and took two commands.
- **Send a browser User-Agent before believing a 403.**
- **Check `curl` findings in the browser too, not only the reverse.** South Dakota
  nearly gained a false "behind Microsoft auth" diagnosis from one admin path.
- **Read the site's own JavaScript.** Alaska's endpoint
  (`aac.asp?media=print&secStart=…&secEnd=…`) was written in plain sight in
  `/scripts/statutes.js`, and it defeats the browser's ~50 KB extraction cap
  as well as the SPA.
- **The 50-state count did not change this round and should not be the headline.**
  Breadth was already complete. **Depth moved: seven states went from "diagnosed,
  unread" to "read on the axis that matters."**
