# SAIRNsenior — state round 8: Oklahoma and Louisiana, both opened

2026-08-30. **Research only.** Tenth document in the series.

Both states were recorded in round 7 as "no route found" after four and five
attempts. **Both opened on the first try once the South Carolina lesson was
applied properly** — stop guessing paths, go find the publisher's own index.

---

## 1. The routes, and why the earlier attempts failed

**Oklahoma.** `rules.ok.gov` 403s everything and remains closed. But Oklahoma's
statutes are on **`oscn.net`**, which round 6 had already fetched and dismissed
as "the courts network". It is — and it also publishes the Oklahoma Statutes.
`index.asp?ftdb=STOKST63&level=1` returns 634 KB of Title 63 (Public Health), and
individual sections come from `DeliverDocument.asp?CiteID=<n>` with the ids in
that index. **The host I had already reached was the answer; I stopped at the
first page because its branding said "courts".**

**Louisiana.** The Office of the State Register publishes the LAC at
`doa.la.gov/doa/osr/louisiana-administrative-code/`. I had guessed `/doa/osr/lac`,
`/pages/osr/lac.aspx` and `/osr/lac/lac.htm` — all 404. **One fetch of the site
root, and a grep of its links for "administrative code", gave the real path.**
Title 48 (Public Health) is published as **two `.docx` files** at opaque
`/media/<slug>/` paths, which is why slug-guessing could never work:

- `48v01.docx` — Title 48:I, Public Health–General (Book 1 of 2), 1.76 MB
- `48v2.docx` — Title 48:I-XXV, Public Health–General (Book 2 of 2), 2.45 MB

**`.docx`, not PDF** — so `pypdf` is the wrong tool. `zipfile` +
`word/document.xml` + tag-strip gives 3.67 M and 3.36 M characters of clean text.
Worth adding to the toolkit alongside the PDF path.

> **The general lesson, stated because it has now cost three rounds:** guessing
> URL paths is guessing. Fetch the publisher's index page and read its links.
> South Carolina, Tennessee, Colorado, Oklahoma and Louisiana were all solved
> that way; every path I invented from memory failed.

---

## 2. Tier 1 — Oklahoma

**63 O.S. § 1-1960 et seq., the Home Care Act** (read from OSCN, cite line
"63 O.S. § 1-1961 (OSCN 2026)").

### Axis A — certification plus registry placement, with a four-month window

§ 1-1961(2) defines **"Certification"** as *"verification of appropriate training
and competence established by the State Commissioner of Health by rules
promulgated pursuant to the Home Care Act **for home health aides and home care
agency administrators**."* Both roles, one mechanism.

§ 1-1962(C)(1) is the operative gate:

> "No employer or contractor … shall employ or contract with any individual as a
> home health aide **for more than four (4) months**, on a full-time, temporary,
> per diem or other basis, unless the individual is a licensed health
> professional **or unless the individual has satisfied the requirements for
> certification and placement on the home health aide registry maintained by the
> State Department of Health.**"

**A third timing shape.** Washington's clock is 120 days from hire with a
pre-service floor; Tennessee's is three months with no floor; **Oklahoma's is
four months and what must be achieved by then is not hours but *presence on a
state registry*.** Combined with Wisconsin — where registry presence is required
from the start — Oklahoma shows the registry axis can carry **a deadline** as
well as a state.

§ 1-1962(C)(2) preserves a 1992–93 grandfathering path, and its residual clause
still binds: *"The home care agency shall maintain responsibility for assurance
of specific competencies of the home health aide and **shall only assign the home
health aide to tasks for which the aide has been determined to be competent**."*
**That is a per-task assignment constraint, not a per-worker credential** — the
same shape as Colorado's adaptive-equipment clause.

### A market-structure rule with no analogue elsewhere in this survey

§ 1-1962(B): **no licensed health care facility, licensed physician, APRN, PA or
state agency employee may refer a client** for personal care services, or for
companion or sitter services under § 1-1972(A), **except to an agency licensed to
provide them.** "Licensed health care facility" is defined broadly for this
purpose — acute care hospitals, LTACs, rehabilitation hospitals, skilled nursing
facilities, **assisted living facilities**, residential care homes, home care
agencies, adult day care centres and hospice agencies.

> This regulates **the referral**, not the provider. Every other state read
> constrains who may *work*; Oklahoma also constrains **who may be sent
> business**. For a product with any referral or partner-network feature, an
> Oklahoma unlicensed provider cannot lawfully receive a referral from most of
> the obvious sources.

### Scope exclusions worth carrying

"Home care agency" excludes (§ 1-1961(5)): individuals contracting with DHS to
provide personal care — **expressly "provided such individuals shall not be
exempt from certification as home health aides"**; intermediary services
organizations (ISOs) contracting with the Oklahoma Health Care Authority for the
**CD-PASS** self-directed waiver; **CD-PASS employer participants** themselves;
and **PACE organizations** (42 C.F.R. § 460.6).

**Note the shape of the first one: exempt from *agency licensure*, not exempt from
*aide certification*.** A single "is this exempt?" flag gets it wrong — the
exemption applies to one axis and not another.

Definitions to carry: **"home health aide"** is *"an individual who provides
personal care to clients in their temporary or permanent place of residence for a
fee"*; **"personal care"** is *"assistance with dressing, bathing, ambulation,
exercise or other personal needs"*; **"skilled care"** requires a trained
respiratory therapist/technician or a state-licensed practitioner.

---

## 3. Tier 1 — Louisiana

**LAC Title 48:I, Chapter 91 — Home Health Agencies** (plus Chapter 92, Direct
Service Worker Registry).

### The clearest unlicensed-segment statement in the survey

From the Chapter 91 "Jurisdiction" definition:

> "…nothing in this Part shall be construed to prohibit the delivery of
> **personal care, homemaker, respite, and other in-home services by a person or
> entity not licensed under this Rule** unless provided with other home health
> services."

**Louisiana does not license non-medical in-home care at all** — unless it is
bundled with home health services, at which point the whole chapter attaches.
Compare Florida (register, don't license), Ohio and Colorado (a separate
non-medical licence category) and Arizona (no licence, but mandatory disclosure).
**Louisiana is the null case**, and the trigger that flips it is *bundling*.

### Axis A — defined by supervision and by a per-visit record

> "**Home Health Aide**—a person qualified to provide direct patient care in the
> home **under the supervision of a RN or physical therapist** to assist the
> patient with ADLs, **in accordance with a written plan of care (POC), and
> requiring a clinical note for each patient visit.**"

**A clinical note per visit is in the definition of the role itself.** That is a
documentation obligation attached to every scheduled visit — squarely a product
requirement, and the second rule in this survey (after Colorado's scheduling
prohibition) that constrains what the software must do rather than what it must
store.

### Axis C — a registry check, placed on the administrator

Among the administrator's enumerated duties: *"assure that agency policies are
enforced, including but not limited to **checking the direct service worker
(DSW)/certified nurse aide (CNA) registry for adverse actions against
non-licensed employees** in accordance with state laws."*

Louisiana runs its own **Direct Service Worker Registry** (Chapter 92), with
§ 9201 definitions, § 9231 Health Care Provider Responsibilities, and a
Subchapter D covering medication administration and noncomplex tasks in home and
community-based settings — including **§ 9245 Training Requirements** and
**§ 9247 Annual Competency Evaluation**. **None of Chapter 92 was read**; the
duty above is quoted from Chapter 91's administrator section.

The administrator's other listed duties are recognisably the axis-E set: ensure
**orientation** of health care personnel providing direct patient care; ensure
**timely annual evaluation**; assure **regularly scheduled appropriate continuing
education for all health professionals and home health aides**; and be on site or
immediately available.

### A premises rule that constrains the business, not the worker

> "The HHA shall be a **separate entity** from any other entity, business, or
> trade. If office space is shared with another healthcare related entity, the
> HHA shall **operate independently, have a clearly defined scope of services**,
> and ensure confidentiality is maintained… **The HHA may not share office space
> with a non-healthcare related entity.**"

Chapter 91's structure, for whoever continues: § 9101 Definitions, § 9102
Governing Body, § 9103 Personnel Qualifications and Responsibilities, § 9105 State
Licensure, § 9115 Agency Operations, § 9118 Branch Offices, § 9119 Personnel
Policies and Records, § 9120 HHA Responsibilities, § 9123 Patient Care Standards,
§ 9129 Clinical Records, § 9131 QAPI.

---

## 4. What this round adds to the model

- **The registry axis can carry a deadline** (OK: four months to reach the
  registry) as well as a requirement.
- **Exemptions are per-axis, not per-entity.** Oklahoma exempts DHS personal-care
  contractors from *agency licensure* while expressly **not** exempting them from
  *aide certification*. A boolean `exempt` is wrong.
- **Some rules regulate the referral, not the provider** (OK § 1-1962(B)). A
  partner or referral feature needs its own licensure check, distinct from the
  worker checks.
- **A second behaviour constraint joins Colorado's:** Louisiana requires **a
  clinical note for every home health aide visit**, written into the definition
  of the role. Colorado forbids a feature; Louisiana compels one.
- **"Not licensed" is a real regulatory state, and it can be conditional.**
  Louisiana leaves non-medical in-home care unlicensed *unless bundled* with home
  health services.

---

## 5. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| OAC 310:661 (Oklahoma's implementing rules) | **STILL NO ROUTE** | `rules.ok.gov` 403s everything. The Home Care Act above is statute; § 1-1963/§ 1-1964 delegate the detail — training hours, competency testing, registry mechanics — to Department rules that were **not** read. |
| OK § 1-1972 (companion/sitter services) | **NOT READ** | Cross-referenced by § 1-1962(B). |
| LA LAC 48:I Chapter 92 (Direct Service Worker Registry) in full | **NOT READ** | Including § 9245 training requirements and § 9247 annual competency evaluation, which are the likely home of Louisiana's axis A detail. |
| LA § 9103 Personnel Qualifications and Responsibilities | **NOT READ** | The section most likely to carry aide qualification specifics. |
| SC R.60-77 §§ 900, 1200, 1700, 1800 | **NOT READ** | Carried from round 7. |
| Indiana | **ON HOLD** | No API key; per instruction, skipped rather than pursued. |
| AZ AAC R9-10 | **CLOSED** | Round 5 ledger. |
| CO Ch. 26 Parts 4, 6, § 5.12 | **NOT READ** | Carried. |
| TN background-check duty outside 0720-27 | **NOT ESTABLISHED** | Carried. |
| The remaining ~24 states | **NOT ATTEMPTED** | Twenty-seven states on at least one axis is not coverage. |

## 6. Method notes

- **Fetch the index; never invent the path.** Five states solved this way; every
  invented path failed. This is now the default move, not a fallback.
- **A host's branding is not its contents.** `oscn.net` says "Oklahoma State
  Courts Network" and publishes the statutes. I had already fetched it in round 6
  and moved on.
- **`.docx` is a live publication format for state regulations.** `zipfile` +
  `word/document.xml` + tag-strip. Louisiana publishes an entire LAC title that
  way, and no PDF tool will touch it.
- **A statute that delegates is only half an answer.** Oklahoma's Home Care Act
  is fully read and still does not give a training-hour figure, because
  §§ 1-1963/1-1964 hand that to Department rules behind a 403. Reading the
  statute told me *what shape* the answer has — certification plus registry — but
  not its content.
