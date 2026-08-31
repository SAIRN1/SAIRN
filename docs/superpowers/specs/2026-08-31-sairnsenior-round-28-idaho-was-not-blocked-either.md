# SAIRNsenior — round 28: Idaho was not blocked either, and one state can hold two archetypes

2026-08-31. **Research only.** Forty-second document in the series.

**Round 27's headline was "seven of eight opened; Idaho is the only genuine
failure." That is now wrong. It is eight of eight.** Idaho opened on the same
two angles that opened the other seven — a moved host and a client-rendered
list — and then produced the most precise publisher-defect finding of the
series.

**Round 27's "Idaho is the one real failure" line is superseded by this
document.** The correction is recorded at the top of that file.

---

## 1. Idaho — the outage is over and the paths moved

`adminrules.idaho.gov` returns **200 and 271 KB**. It is a **rebuilt WordPress
site** (assets dated 2025). The "state-declared outage" recorded in rounds 5–27
is either finished or was never the whole story; **either way it was never
re-tested until now, and the note was carried forward on trust for twenty-plus
rounds.**

Two familiar shapes, both already seen this session:

- **`/rules/current/16/index.html` 302s to `/current-rules/`** — the old deep
  paths are gone. *Same shape as Kansas's `sos.ks.gov` → `rules.ks.gov`.*
  The old chapter PDF path `/rules/current/16/160307.pdf` **still 404s, and that
  404 was the entire basis for "Idaho is blocked."**
- **The rules list is client-rendered.** `curl` sees a WordPress page with 57
  links, none of them a rule. **Chrome sees all 44 agencies and every chapter.**
  *Same shape as Utah, Alabama, Mississippi, Connecticut.*

## 2. IDAPA 16 has no home health chapter — but the statute still requires a licence

**Department of Health and Welfare, current rules: 21 chapters.** Read in full
from the site. Vital statistics, reportable diseases, food code, radiation,
Medicaid eligibility and plan benefits, **certified family homes (16.03.19)**,
**DDA / residential habilitation / adult residential care (16.03.21)**,
**residential assisted living (16.03.22)**, **criminal history and background
checks (16.05.06)**, child welfare and daycare.

**There is no home health agency chapter. The historic 16.03.07 is gone.**

**And yet the statute is live and mandatory:**

> **"After January 1, 1993, no private or public agency or organization may
> advertise, operate, manage, conduct, open, maintain, or hold itself out to the
> public to be a home health agency unless licensed by the department of health
> and welfare."** — Idaho Code **§ 39-2403**

§ 39-2401 gives the board authority to "adopt rules, regulations and standards
for the licensing of an agency"; **§ 39-2405** obliges it to adopt and enforce
standards "with the advice of the advisory board of home health providers."
**Those rules are not in the current administrative code.**

**§ 39-2403 also carries a deeming route**, which is how the gap is bridged in
practice:

> "The department **may grant licenses without conducting a licensure survey to
> medicare certified agencies or agencies currently accredited by an accrediting
> body recognized by the health care financing administration**…"

> **Idaho's shape: a mandatory licence whose substantive standards are absent
> from the published rules, with entry effectively running through Medicare
> certification or private accreditation.** It is the same deemed-status pattern
> recorded for Arizona (A.R.S. 36-425.01) in round 6, but here it is not a
> shortcut alongside state standards — **there are no published state standards
> for it to run alongside.**

**§ 39-2411 exempts thirteen categories**, several of which are exactly where a
consumer product sits: **a family member**; an organization providing only meal
service; **a licensed professional who independently provides services in the
home**; **an employee or volunteer providing non-professional services only**;
in-home assessments that do not lead to ongoing care; case management without
direct delivery; a Medicare-certified hospice; and **"a state authorized personal
assistance agency or personal assistant as defined in chapter 56, title 39."**

## 3. Two publisher index defects, and each nearly produced a false finding

This is the transferable part.

**Defect 1 — Chapter 24's own page and PDF show no sections.**
`/statutesrules/idstat/Title39/T39CH24/` renders the heading "CHAPTER 24 HOME
HEALTH AGENCIES" and **an empty section list**. The chapter PDF is **325
characters of letterhead**. From either artefact the obvious conclusion is *"the
chapter is empty or repealed."*

**It is neither.** Requesting sections directly returns **§§ 39-2401 through
39-2411**, all with full text and unrepealed history notes.

**Defect 2 — the Title 39 index labels Chapter 56 "[REPEALED]" and does not link
it.** But `§§ 39-5601–39-5605, 39-5608, 39-5609` all render as live **"PERSONAL
ASSISTANCE SERVICES"**, with history notes ending in ordinary amendments
(**2010** for § 39-5601) **and no repeal entry**.

> **A control was run before either conclusion was recorded.** `SECT39-2499` and
> `SECT39-5610` return **HTTP 404**, so the section endpoint is not a soft-200
> that echoes the chapter for any input. **The 200s are real.**
>
> **Honest limit:** this establishes that the index and the section pages
> disagree and that the section pages carry no repeal note. It does not
> absolutely exclude the site serving stale section text. **The index defect is
> certain; "Chapter 56 is live" is strong inference, not proof.**

**Both defects point the same way: on this publisher, the chapter index is
unreliable and the section endpoint is the ground truth.** Round 25 already paid
for the inverse mistake — eleven South Dakota endpoint forms debugged against a
chapter that was the wrong citation. **Here the citation was right and the index
was wrong.** The rule that covers both: **confirm a chapter is empty by asking
for its sections, not by reading its table of contents.**

## 4. Idaho's non-medical tier was hiding behind the "[REPEALED]" label

**Idaho Code ch. 56, tit. 39 — Personal Assistance Services**, the chapter the
index says does not exist, is where Idaho's qualification axis for non-skilled
in-home work actually lives:

**§ 39-5604, Health and background checks — mandatory:**

> "The director **shall require** providers to obtain health tests or screens,
> **criminal background and nurse's aide registry checks**, and licenses and/or
> certifications necessary to protect the health, person and property of the
> participant for any personal assistant acting as an employee, agent, or
> contractor of a provider."

**§ 39-5605, Training of personal assistants — discretionary:**

> "The director **may** require a personal assistant to successfully complete a
> training program established by the rules **before beginning to provide**
> personal assistance services. **Those providing personal assistance services
> when the rule is established will be given a reasonable period of time to
> obtain the required training.** The director **may establish different training
> requirements for different services provided and for personal assistants
> serving participants with intensive needs.**"

> **Screening is compulsory; training is optional and, if imposed, arrives with a
> statutory grandfather period and may vary by service type and client acuity.**
> That is a fifth shape: **mandatory vetting, discretionary competence.** No
> other state read so far separates the two this cleanly.

## 5. Kansas — the same state holds two archetypes at once

Round 27 called Kansas **Archetype A** (state credential, state test, state
registry) on the strength of K.A.R. 28-51-113/-115/-116. **That is true only of
home health aides.** Reading the supportive-care tier changes the claim.

**K.A.R. 28-51-117, Supportive care services** (effective 20 May 2022) imposes
**no state credential, no registry, no state test and no prescribed hours.** The
licensee writes the scope-of-practice policy, and:

- **competency demonstrated before the worker operates without the manager
  present, and re-evaluated annually**, across ten named areas — including
  "communicating with clients with a hearing deficit, dementia, or other special
  needs";
- **on-site supervision at least every three months**, including a client
  satisfaction assessment;
- **written assignments prepared by a manager from the plan of care, reviewed
  every three months.**

> **Kansas is Archetype A for aides and Archetype D for supportive care workers,
> in the same article of the same code.** The round-27 framing — four archetypes,
> four data models — survives, but the unit is wrong: **the archetype attaches to
> the worker class, not to the state.** A state-level `qualification_model` field
> would already be wrong for Kansas.

### The single most product-relevant rule found in twenty-eight rounds

**28-51-117(g) is a task-permission matrix with per-task client-condition
preconditions** — sixteen categories, each with an explicit boundary:

| Task | Permitted | Boundary |
|---|---|---|
| **Medication** | inquire, verbally prompt, hand over, open the container | **only** from a day/time-marked reminder container pre-selected by client, family, nurse or pharmacist; **never administration**; must report immediately if doses are missed or mistimed |
| **Skin care** | assist | **only if skin unbroken and no active chronic skin problem**; no medication; **no wound care or dressing changes** |
| **Ambulation** | assist | client can balance and bear weight **and** a qualified health professional has found them independent with an assistive device |
| **Bathing** | assist | wounds needing bandage changes → **must be a home-health-licensed agency** |
| **Dressing** | ordinary clothing, **over-the-counter** support stockings | **not** elastic bandage wraps or prescription antiembolic/pressure stockings |
| **Exercise** | normal bodily movement as tolerated; may encourage | **not** exercise prescribed by a PT/OT |
| **Feeding** | assist | client chews, swallows and sits upright unaided; **no syringe, tube or IV**; high choking/aspiration risk → home-health-licensed agency |
| **Mouth care** | denture care, basic oral hygiene | unconscious, swallowing difficulty, aspiration risk or recent oral surgery → home-health-licensed agency |
| **Nail care** | soak, push back cuticles **without utensils**, file | **trimming only** if the agency declared home health services on its application or renewal |
| **Positioning** | simple alignment | client can signal the need; **not** if skin care is required with it |
| **Shaving** | electric or safety razor only | — |
| **Toileting** | bedpans, urinals, commodes, incontinence pads, empty catheter bags and ostomy bags | **no** catheter insertion/removal or external catheter care; **no** suppositories or enemas |
| **Transfers** | if client can stand, pivot and assist; may help a family member transfer | **not** if the client cannot assist; equipment only with full training and step-by-step direction; **lift devices require demonstrated competency** |
| **Respiratory care** | — | **skilled service; prohibited outright** |
| **Oxygen** | temporarily remove/replace cannula or mask to shave or wash the face; set flow when changing tanks | flow-setting **only** with specific training and demonstrated competency |

> **This is not a qualification rule at all — it is an authorisation rule keyed to
> the client's condition at the moment of the task.** "Is this worker qualified?"
> cannot express it. "May this worker do this task, for this client, today?" can.
> Nail *trimming* turning on a box ticked on the agency's licence renewal is the
> sharpest example: **the same worker, same client, same clippers, is permitted or
> not depending on an administrative election made months earlier.**

---

## 6. Where the eight stand now

| State | Status |
|---|---|
| Utah, Kansas, Connecticut, Alabama, Mississippi, Alaska, Arizona | **CLOSED on the qualification axis** (round 27) |
| **Idaho** | **OPEN AND READ** — IDAPA 16 chapter list; Idaho Code §§ 39-2401 – 39-2411 and §§ 39-5601 – 39-5609 |
| *(Indiana)* | **STILL ON HOLD** — credential decision, untouched |

**Eight of eight opened. Zero of the eight were blocked.** Every diagnosis in
rounds 21–26 described a tool's output and named it a property of a publisher.

## 7. Tier 2 — still open

| Item | Status |
|---|---|
| Idaho IDAPA **16.05.06** Criminal History and Background Checks | **ROUTE OPEN, NOT READ** — the rules implementing § 39-5604's mandatory screening. |
| Idaho IDAPA **16.03.26** Medicaid Plan Benefits | **ROUTE OPEN, NOT READ** — the likely home of any § 39-5605 training rule, and the test of whether the director ever exercised the discretion. |
| Idaho **§§ 39-5606, 39-5607** | **404 on the section endpoint** — repealed or never enacted; not chased. |
| Idaho ch. 24 — whether any home health rule exists outside IDAPA 16 | **NOT ESTABLISHED.** The absence from the current chapter list is strong, not conclusive. |
| Kansas **28-51-118** HCBS, **-100** definitions, **-112**, **-114** | **ROUTE OPEN, NOT READ.** |
| Connecticut **D66–D79** (skilled home health *care* agencies) | **ROUTE OPEN, NOT READ.** |
| Alaska **7 AAC 10.935** (criminal-history variance) | **NOT READ.** |
| Arizona R9-10-1201–1205, 1207–1209 | **ROUTE OPEN, NOT READ.** |
| Mississippi ch. 46 subch. 6–14; ch. 54 registry scoping | **CACHED / PARTIALLY READ.** |
| South Dakota full-text SDCL search | **NOT RUN.** |

## 8. Method notes

- **Re-test a state-declared outage before carrying it into another round.**
  Idaho's was carried for twenty-plus rounds on a single 404 and was over.
- **A chapter's table of contents is not evidence that the chapter is empty.**
  Ask the section endpoint. Idaho's Chapter 24 renders zero sections and has
  eleven; its Chapter 56 is labelled "[REPEALED]" and is not.
- **Run the negative control before believing a positive.** `SECT39-2499` → 404
  is what makes `SECT39-2401` → 200 mean something. A soft-200 would have
  produced eleven confident fabrications.
- **The archetype attaches to the worker class, not the state.** Kansas proves a
  single state can be maximally prescriptive for one worker class and fully
  delegated for another, in one article.
- **Look for the task-permission rule, not only the credential rule.** K.A.R.
  28-51-117(g) and Idaho § 39-5605's per-service differentiation are both saying
  the same thing: **what a worker may do is a function of the task and the
  client's condition, not of a credential held once.**
