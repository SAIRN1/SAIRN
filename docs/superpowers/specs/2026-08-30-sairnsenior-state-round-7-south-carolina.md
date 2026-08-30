# SAIRNsenior — state round 7: South Carolina, and a citation that stopped existing

2026-08-30. **Research only.** Ninth document in the series.

Also records: the Colorado scheduling prohibition promoted to a build constraint
in two documents, what registering the Indiana API key actually requires, and
Oklahoma and Louisiana still unresolved.

---

## 1. South Carolina — and R.61-77 does not exist any more

Round 6 recorded *"DHEC R.61-77 was not located"* and treated it as a routing
failure. **It was not a routing failure. The regulation was renumbered, and the
department that issued it was abolished.**

**2023 Act No. 60 (S.399) abolished the South Carolina Department of Health and
Environmental Control effective 2024-07-01**, creating the Department of Public
Health and the Department of Environmental Services. The regulations followed:

> "**60–77. Standards for Licensing Home Health Agencies.** (Statutory Authority:
> S.C. Code § 44–69–10 et seq.) … **Transferred from 61–75 and amended by
> SCSR 49–5 Doc. No. 5352, eff May 23, 2025.**"

**So the current citation is R.60-77**, in **Chapter 60 — Department of Public
Health**, effective **2025-05-23**. Anything citing 61-77 (or 61-75) is naming a
regulation that has moved, and any secondary source still using the old number
predates May 2025.

> **Two lessons, and the second is the general one.** First, `Chapter 61.pdf`
> 404s on the publisher's own server while `Chapter 60.pdf` returns 1.99 MB —
> the 404 *was* the answer, and I read it as a broken route for a full round.
> Second: **a citation is a claim with a date on it.** The same failure shape as
> the Tennessee and Missouri wrong-guess citations, inverted — there the URL
> resolved to the wrong document, here the right document refused to resolve
> under a number that had lapsed.

### Axis A — delegated to the agency, in writing

§ 501(B): *"The Agency shall define in writing the responsibilities,
qualifications, and competencies of Staff for all positions."* The agency must
then ensure staff are properly licensed or credentialed for their assigned
duties, *"Trained as necessary to perform the duties for which they are
responsible in an effective manner"*, capable of rendering care, and capable of
following applicable regulations.

**Section 500 is titled "Staff and Training" and contains four rules — General,
Administrator, Clinical Manager, Health Status. There is no home health aide
training rule and no hour figure anywhere in it.** South Carolina joins Colorado
in **delegating the standard to the agency and requiring it be written down** —
but where Colorado delegates *axis B* (the barred-offence judgment) and specifies
axis A in detail, **South Carolina does the exact reverse.** The same delegation
device, applied to opposite axes, in two states.

§ 501(C) requires current records for every staff member: name, address and
telephone; **date of hire and date of initial patient contact** as separate
fields; past employment, experience and education; professional licensure or
credentials; and a **job description signed by the staff member**.

### Axis B — enumerated, with an open-ended tail

§ 501(A): *"Before being employed or contracted as a Staff member, all Direct
Care Staff shall undergo a criminal background check pursuant to S.C. Code
Section 44–7–2910."* Staff **and volunteers** must not have a prior conviction or
nolo contendere plea to:

- unlawful conduct toward a child (S.C. Code § 63-45-70);
- abuse, neglect or exploitation of a vulnerable adult (§ 43-35-10 et seq.);
- **"or any similar criminal offense."**

**That trailing clause is a third axis-B shape.** Ohio, Texas, Virginia and
Florida enumerate exhaustively; Colorado delegates the whole judgment to the
agency; **South Carolina enumerates and then delegates the edge.** A
`barred_offences[]` list can hold the first two items and cannot hold the third,
which is the one that actually requires a human decision — and note it binds
**volunteers**, who are outside most other states' wording.

### Axis D — a health assessment with a lookback, and it is portable

§ 504: every staff member with patient contact must have a **documented Health
Assessment within twelve (12) months prior to initial patient contact**,
including tuberculin skin testing per § 1702 (which also requires a TB risk
assessment). And:

> "If a Staff member is working at multiple Home Health Agencies or facilities
> operated by **the same Licensee**, copies of the documented Health Assessment
> shall be accessible **at each location**."

**A twelve-month lookback anchored to first patient contact — not to hire — and a
document that must be replicated across sites under one licensee.** Neither is
expressible as a boolean or a single date on a worker record.

### Administrator and clinical manager

§ 502: a **full-time** Administrator who is a physician or other Authorized
Healthcare Provider, a Registered Nurse, or has *"training and experience in
health service administration and at least one (1) year of supervisory
administrative experience in home health care or a related healthcare program"* —
near-identical wording to Tennessee's and Texas's administrator tests. A written
designation of who acts in the Administrator's absence is required, by position
title and name.

§ 503: a designated **Clinical Manager** — physician, other Authorized Healthcare
Provider, or RN — supervising professional clinical activities per the treatment
plan.

### Records and reporting, worth carrying

§ 601: every Incident documented with review, investigation, evaluation and
corrective action, **retained six (6) years after the patient is last
discharged**, readily available and stored for the first year after discharge;
incidents reported to the patient's representative or emergency contact *"at the
earliest practicable hour."*

---

## 2. The Colorado scheduling prohibition — now flagged where it will be seen

Promoted per instruction, because it is a feature-gating requirement rather than
a data field:

- **`2026-08-30-…-round-6-az-co-placement-sc.md`** now opens with a
  **⛔ BUILD CONSTRAINT** section before any other content, stating that a
  Colorado-registered placement agency must not be given scheduling,
  training-delivery or assignment-direction features **at all**; that the gate is
  **account-level, keyed on registration category, decided before UI is
  exposed**; that hidden-but-enableable is the same exposure; and that "Colorado"
  is therefore not a single configuration.
- **`2026-08-30-…-pathways-model.md`** — the document that defines the standard
  shape — now carries the same warning **above** the five-axis table, so anyone
  reading the model first cannot miss it.

The distinction recorded in both: every other registration-category instance
changes *which requirements apply*; **only this one changes what the software is
allowed to do.**

---

## 3. Indiana — what the API key actually costs

`api.iga.in.gov` returns `"x-api-key not found"` and points to
`docs.api.iga.in.gov`, which is a JavaScript single-page app (473 bytes of shell)
and renders nothing to a fetch.

**Obtaining the key requires registering an account with the Indiana General
Assembly, and creating accounts is not something I do — that one needs Michael.**
It is a small task and the access is real: the API is public, documented, and
returns Indiana Code as JSON, which would make IC 16-27 (home health agencies and
personal services agencies) and IAC Title 410 straightforward.

**Once a key exists**, pass it as the `x-api-key` header; the endpoint shape
already confirmed working is
`https://api.iga.in.gov/{year}/code/title/{n}/article/{n}`.

---

## 4. Oklahoma and Louisiana — still unresolved

**Oklahoma.** `rules.ok.gov` 403s the chapter path, the title path and a direct
document path. `oklahoma.gov` and `sos.ok.gov` document paths 404. `oscn.net`
hosts an Oklahoma document index and responds, but it is the courts network and
the administrative-code database was not reachable through the entry point tried.
**No route found; four hosts tried.**

**Louisiana.** `ldh.la.gov` loads but is programme information, not rule text.
`doa.la.gov` — the Office of the State Register, which publishes the LAC —
returns 200 at its root and **404 on every LAC path guessed** (`/doa/osr/lac`,
`/pages/osr/lac.aspx`, `/osr/lac/lac.htm`, and two `/media/<slug>/48v1.pdf`
forms). The `/media/` paths use opaque slugs, so guessing cannot work; the index
page that carries them was not found. `legis.la.gov` serves statutes and its
LawSearch page loads, so **the statutory side of Louisiana is reachable** — R.S.
40:2009.31 et seq. was identified but not fetched.

**Both recorded as open with the routes tried, not as pending intentions.**

---

## 5. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| SC R.60-77 Sections 900, 1200, 1700, 1800 | **NOT READ** | Only definitions, licensure, staffing and part of reporting were mined from a 787-page chapter. § 1702 (TB risk assessment) was seen only by cross-reference from § 504. |
| Whether SC sets aide qualifications anywhere outside R.60-77 | **NOT ESTABLISHED** | § 501(B) delegates to the agency; whether Medicare CoPs or another regulation supply a floor was not checked. |
| SC Code § 44-7-2910 (the background-check mechanism) | **NOT READ** | Cross-referenced by § 501(A). |
| Indiana IC 16-27 / IAC 410 | **BLOCKED ON AN ACCOUNT** | Not a technical obstacle. |
| Oklahoma OAC 310:661 | **NO ROUTE — four hosts tried** | Listed above. |
| Louisiana LAC Title 48 | **NO ROUTE — five paths tried** | Statutes reachable; regulations not. |
| AZ AAC R9-10 | **CLOSED** | Round 5 ledger. |
| CO Chapter 26 Parts 4, 6, § 5.12; Chapter 2 Part 2.3.6 | **NOT READ** | Carried. |
| TN background-check duty outside 0720-27 | **NOT ESTABLISHED** | Carried. |
| The remaining ~26 states | **NOT ATTEMPTED** | Twenty-five states on at least one axis is not coverage. |

## 6. Method notes

- **A 404 on a chapter number can be a fact about the law, not the server.**
  South Carolina cost a full round because `Chapter 61.pdf` 404ing was read as a
  broken route when it was the correct answer — the chapter had been renumbered
  after its department was abolished. **Before concluding a publisher is
  awkward, check whether the citation still exists.**
- **Delegation is a device states apply to different axes.** Colorado delegates
  the barred-offence judgment and specifies training in detail; South Carolina
  specifies barred offences and delegates the qualifications. Recognising
  delegation as a *shape* rather than as a property of one axis is what makes
  both storable.
- **"Similar offense" and "the agency determines" are the same instruction** —
  a documented human decision — reached from opposite directions. Both need a
  place to record reasoning, not a flag.
