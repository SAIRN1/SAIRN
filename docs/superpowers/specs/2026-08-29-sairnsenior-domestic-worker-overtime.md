# SAIRNsenior — state domestic-worker overtime, and the MA/TX sources

2026-08-29. **Research only. No app behaviour changed by this document.**

Closes item 5 of `2026-08-28-narrow-verification-pass-results.md` §7 for six states,
and clears the two dead publishers logged in
`2026-08-29-sairnsenior-state-variation.md` Tier 2. Same two-tier rule as that
document: **Tier 1 is fetched from the issuing government; Tier 2 is not safe to
encode.**

---

## 0. The premise this pass was given was wrong, and that is the finding

The open item was worded: *"State domestic-worker overtime rules, which a federal
FLSA rescission would not displace."* That is the natural assumption — state law
is independent of federal law — and **it does not hold in at least two of the six
states read.**

**Connecticut and Oregon each incorporate the federal definition by reference.**
A DOL rescission of the 2013 companionship rule (RIN 1235-AA51, projected
November 2026) therefore propagates *into* their state law automatically. Quoted
below. Nobody would go looking for that while the note says state rules are
insulated.

So the correct model for SAIRNsenior is **three** categories, not two:

1. **Independent** — state fixes its own threshold in its own words (CA, NY, IL).
2. **Federally coupled** — state coverage turns on an FLSA definition, so it
   moves when the federal rule moves (CT, OR).
3. **Agency-carved-out** — the state has a domestic-worker law, but employees of
   a *licensed home care agency* are outside it (OR), which is precisely the
   worker SAIRNsenior exists to schedule.

---

## Tier 1 — verified from primary source, 2026-08-29

### The overtime thresholds themselves

| State | Threshold | Live-in threshold | Citation |
|---|---|---|---|
| California | 9 hrs/day **or** 45 hrs/week | same section, no separate live-in rule | Lab. Code § 1454 |
| New York | 40 hrs/week | **44 hrs/week** | Lab. Law § 170 |
| Oregon | 40 hrs/week | **44 hrs/week** | ORS 653.547(2)(a) |
| Illinois | 40 hrs/week | none stated | 820 ILCS 105/4a |
| Massachusetts | 40 hrs/week (general OT law; no domestic exemption) | none stated | M.G.L. c. 151 § 1A |
| Nevada | 40 hrs/week **or** 8 hrs/day | **exemptible by written agreement** | NRS 608.018 |

All at **1.5×** the regular/base rate.

**California — Lab. Code § 1454**, verbatim: *"A domestic work employee who is a
personal attendant shall not be employed more than nine hours in any workday or
more than 45 hours in any workweek unless the employee receives one and one-half
times the employee's regular rate of pay…"* Added by Stats. 2013, Ch. 374 (AB
241), effective 2014-01-01.

**California — who counts, § 1451.** "Personal attendant" is defined as a person
employed *"by a private householder **or third-party employer**"* where
supervision/feeding/dressing is **more than 80%** of weekly hours. **So an
agency-employed caregiver is covered in California** — the direct opposite of
Oregon below. Excluded from "domestic work employee": **IHSS participants and
providers**, family members, minors babysitting the employer's children, casual
babysitters, **licensed health facility employees**, regional-center/developmental-
services employees, and exempt child care providers. The 80% test and the IHSS
exclusion are both load-bearing and both easy to miss.

**New York — Lab. Law § 170**, "Hours of labor for domestic workers," verbatim:
*"…shall require any domestic worker to work more than forty hours in a week, or
forty-four hours in a week for domestic workers who reside in the home of their
employer; unless they receive compensation for overtime work at a rate which is
at least one and one-half times the worker's normal wage rate."*

**Illinois — domestic workers are affirmatively written in.** 820 ILCS 105/3(d)
defines "employee" to include *"notwithstanding subdivision (1) of this
subsection (d), one or more domestic workers as defined in Section 10 of the
Domestic Workers' Bill of Rights Act."* The **notwithstanding** clause is the
mechanism: it overrides the fewer-than-four-employees exclusion that would
otherwise remove nearly every household employer. 105/4a sets 40 hours at 1.5×
and **none** of its subsection (2) exemptions reaches domestic service or
companionship.

**Massachusetts — by absence, not by inclusion.** M.G.L. c. 151 § 1A requires
1.5× over 40 and enumerates 20 exemptions; **none is domestic service or home
care in a private home.** M.G.L. c. 149 § 190 (Domestic Workers' Bill of Rights)
adds rest-day and record-keeping duties and routes the overtime rate back to
c. 151 § 1A rather than setting its own. **Read the two together — § 190 alone
looks like it has no overtime rule.**

> Flagged, not carried: the c. 151 § 1A exemption list as retrieved includes a
> hospital/nursing-home item. Whether that reaches any home-care employer was
> **summarised, not quoted**, so it sits in Tier 2.

**Nevada — the only state here where the parties can contract out.** NRS
608.018(3)(p) exempts *"a domestic service employee who resides in the household
where he or she works if the domestic service employee and his or her employer
agree in writing to exempt the domestic service employee from the
requirements."* A live-in exemption that depends on a **signed document** is a
record SAIRNsenior would have to store and check, not a rule it can evaluate
from hours alone.

**Nevada — NRS 608.0195 is directly on point for 24-hour shifts** and was found
while checking something else. Employer and employee may agree **in writing** to
exclude a regularly scheduled sleeping period of **up to 8 hours** from paid
hours where adequate facilities are provided; **any interruption for service
counts as work**; and if interruptions drop the sleep period **below 5 hours,
the entire period is compensable**. It applies to residential-facility employees
and **home care workers** specifically. That is a computable payroll rule with a
cliff in it, and it is the sharpest scheduling-to-payroll interaction found in
this pass.

**Washington — no blanket domestic exclusion.** RCW 49.46.010(3)(b) excludes only
*"any individual employed in casual labor in or about a private home, unless
performed in the course of the employer's trade, business, or profession"* —
the trailing clause puts agency-dispatched care back in. Subsection (3)(j)'s
on-call residential exemption now carries an express carve-back: *"this
exemption does not apply to any individual employed by an employer as a domestic
worker as defined under RCW 49.96.010."*

### The federal coupling — the part that changes the model

**Connecticut, C.G.S. § 31-58(e).** "Employee" excludes an individual employed
*"in domestic service in or about a private home, **except any individual in
domestic service employment as defined in the regulations of the federal Fair
Labor Standards Act**."* Coverage is therefore an FLSA-regulation question, not a
Connecticut question. Separately confirmed: § 31-76i, the overtime exceptions
list, runs to sixteen-plus items and **contains no domestic-service exemption** —
so the coverage question is settled entirely at the § 31-58(e) definition, which
is the section a reader looking for "domestic worker overtime" would not open.

**Oregon, ORS 653.547(1)(b)(B).** "Domestic worker" **excludes**:

- *"(ix) Individuals performing companionship services exempt from the provisions
  of the Fair Labor Standards Act of 1938 (29 U.S.C. 201 et seq.)."* — the same
  federal coupling.
- *"(vii) Individuals employed by organizations licensed as required by ORS
  443.015 or 443.315."* — **in-home care agencies.** Oregon's Domestic Workers'
  Protection Act does not reach an agency's employees at all.

Also excluded: parents/spouses of the employer, the employer's children under 26,
students attending school during the day, other children under 14, casual
babysitters, casual labour, independent contractors, house-sitters, and
in-kind-only arrangements. ORS 653.020(2) and (14) separately exempt casual
domestic service and companionship services from the general wage law; ORS
653.553 names §§ 653.547–653.551 the Domestic Workers' Protection Act
(2015 c.457 § 4).

### What to encode

**Do not encode a single "domestic worker OT" flag per state.** The rule needs
three inputs the state statutes actually turn on: whether the worker is
**agency-employed or household-employed**, whether they **live in**, and — for CT
and OR — **what the FLSA companionship regulation currently says**. Two of the
six states cannot be evaluated correctly without the third input, and that input
has a projected change date of **November 2026**.

---

## Tier 2 — reported, not independently checked

**Do not encode anything in this section.**

| Item | Status | Provenance |
|---|---|---|
| MA c. 151 § 1A hospital/nursing-home exemption — does it reach any home-care employer? | **SUMMARISED, NOT QUOTED** | The exemption list came back as a 20-item paraphrase. The verbatim wording was never retrieved. |
| New Jersey overtime / Domestic Workers' Bill of Rights | **NOT FETCHED** | `law.justia.com` returned 403 and no official NJ statute host was tried. |
| Seattle and other municipal domestic-worker ordinances | **NOT ATTEMPTED** | WA has no statewide domestic-worker OT premium; the local layer was out of scope and is a real gap. |
| The other 44 states | **NOT ATTEMPTED** | Stated so six states are not read as coverage. |

---

## The two dead publishers, resolved

Both Tier 2 rows in `2026-08-29-sairnsenior-state-variation.md` are now answered.
**One was diagnosed wrongly by me this morning and is corrected here.**

### Massachusetts — mass.gov blocks the fetcher, not the browser, and malegislature.gov was never blocked

I recorded this morning that mass.gov "returned HTTP 403, not a shell" and
concluded the obstacle was a bot wall rather than the landing shell the prior
pass had described. **Both halves were true and I drew the wrong line between
them.** Driving Chrome directly:

- `mass.gov` in a real browser serves the page fine — **the 403 is specific to
  automated fetch.** `curl` with a browser user-agent also gets 403 (14,061 bytes
  of HTML, not a PDF), so it is a request-fingerprint block, not a UA check.
- The regulation page **is** a landing shell exactly as the prior pass said: it
  carries a title, authority (M.G.L. c. 111 §§ 72F–72L), a date and a **PDF
  download link**, and no regulation text.
- The PDF renders in Chrome's viewer but the viewer is canvas-based — page text
  extraction returns nothing, and the first page is all that could be read by
  screenshot before this stopped being worth the attempts.

**So the prior pass's "landing shell" note was right and my "bot wall" correction
narrowed it wrongly.** Both are real: a shell *and* a fetch block, on the same
page, and neither explains the other.

**The useful part: `malegislature.gov` is a different host and is not blocked at
all.** Every Massachusetts statute in this document came from it on the first
try. **Massachusetts is not a blocked state — mass.gov is a blocked host, and
only the CMRs live there.**

What was learned about the target anyway, from the mass.gov search index and the
PDF's own table of contents (both readable): **105 CMR 155.000** is the Patient
and Resident Abuse Prevention Registry, issued by DPH under M.G.L. c. 111
§§ 72F–72L, and §§ 155.004–155.012 apply to *"all individuals working in or
employed by a facility, home health agency, homemaker agency or hospice
program."* Its § 155.010 is "Responsibilities of the Facility, Home Health
Agency, Homemaker Agency, and Hospice Program" and § 155.016 establishes the
registry for nurse aides, **home health aides and homemakers**. **The substantive
text of those two sections was not read** — that is the remaining MA gap, and it
is now a narrow one.

### Texas — the Appian portal is unusable, and HHSC's own material is the way in

`texreg.sos.state.tx.us` is retired. Its replacement,
`texas-sos.appianportalsgov.com`, **navigates but never reaches document-idle** —
text extraction, element search and screenshot all time out against it, and the
`rule=` URL parameter is silently dropped, so the chapter and subchapter listings
render but no individual rule can be opened without a click the page never
becomes responsive enough to accept. Three attempts, two of them after a reload.
**Recorded as unusable rather than retried further.**

Structure that *was* readable from it, and is worth keeping: **26 TAC ch. 558**,
"Licensing Standards for Home and Community Support Services Agencies," subchapters
A–H, with **Subchapter G "Home Health Aides"** containing a single rule,
**§ 558.701**.

The rule text itself came from **HHSC's own pre-survey training modules** on
`apps.hhs.texas.gov`, which are fetchable:

- **75 hours minimum** — *"A minimum of 75 hours as follows: an appropriate
  number of hours of classroom instruction; and a minimum of 16 hours of clinical
  experience."*
- **At least 16 hours of classroom training before clinical experience** working
  directly with clients.
- **Competency evaluation must be performed by an RN**, with no more than one
  unsatisfactory rating (excluding communication skills and rights of the
  elderly). Cited there to **26 TAC § 558.701(e)–(f)**; aide qualifications cited
  to **§ 558.401(f)** and **§ 558.701(c)**.

> **Provenance label, and it matters:** this is **HHSC restating its own rule in
> a training module**, not the codified text of 26 TAC § 558.701. It is a primary
> *agency* source, one step removed from the regulation. Good enough to plan
> against; **not** good enough to quote to a customer as the rule. Reading
> § 558.701 itself is still open.
>
> Also open: **Personal Assistance Services**. Texas licenses non-medical
> personal-care agencies in the same chapter, and **nothing retrieved states the
> requirements for an unlicensed personal assistant** — which is the larger half
> of SAIRNsenior's Texas market.

## Method notes worth carrying

- **Host-level blocks are not state-level blocks.** `mass.gov` 403s every
  automated fetch; `malegislature.gov` serves the same state's statutes freely.
  Before recording a state as unreachable, try its *other* publisher.
- **When a fetch summariser says a chapter page lacks a section, it usually means
  the page was truncated, not that the text is absent.** `cga.ct.gov` chapter 558
  and `oregonlegislature.gov` ORS 653 both "did not contain" the sections asked
  for; both contained them in full. `curl` + local extraction found each on the
  first try. **For any statute chapter large enough to matter, fetch it whole and
  search it locally.**
- **A JS-rendered portal that never idles defeats every browser tool at once** —
  text, find, and screenshot all inject scripts. There is no partial win to
  salvage; go find the agency's own publication instead.
- The CT and OR findings were both in **definition** sections, not in the
  overtime sections. Searching for the operative rule would have missed both.
