# SAIRNsenior — round 19: Nebraska, and five registries in one check

2026-08-30. **Research only.** Twenty-sixth document in the series.

Nebraska has a **dedicated In-Home Personal Services Act** for the non-medical
segment, and it requires the **most registry checks of any state in the survey** —
five, in a single subsection.

**Reclassification check run on every Nebraska text read: zero hits.** Per the
new standing practice, that check now runs as each state is read rather than in a
sweep at the end.

---

## 1. Nebraska — the non-medical segment has its own act

**Neb. Rev. Stat. §§ 71-6501 to 71-6504** — *terms defined; in-home personal
services **worker**; qualifications; in-home personal services **agency**; duties;
applicability.* Separately, **§§ 71-6601 to 71-6608.02** cover **home health
aides**, and **§ 71-417** defines *home health agency*.

**A sixth answer to the unlicensed-segment question:** Nebraska neither leaves it
alone (LA), registers it (FL), makes it disclose (AZ), sets a training-hour floor
(AR), nor licenses it as a facility (NV/OH/CO). It **sets statutory
qualifications for the worker and duties on the agency**, directly in the code.

### § 71-6502 — worker qualifications, and five registries

> "An in-home personal services worker: (1) Shall be **at least eighteen** years
> of age; (2) Shall have **good moral character**; (3) Shall **not have been
> convicted of a crime** … the penalty for which is imprisonment for a period of
> **more than one year** and which crime is **rationally related to the person's
> fitness or capacity** to act as an in-home personal services worker; (4) Shall
> have **no adverse findings on**:
> - the **Adult Protective Services Central Registry**,
> - the central registry created in **§ 28-718** *(child abuse and neglect)*,
> - the **Medication Aide Registry**,
> - the **Nurse Aide Registry**, and
> - the central registry maintained by the **sex offender registration and
>   community notification division of the Nebraska State Patrol** (§ 29-4004);
>
> (5) Shall be **able to speak and understand the English language *or the
> language of the person for whom he or she is providing* in-home personal
> services**; and (6) Shall have **training sufficient to provide the requisite
> level of in-home personal services offered**."

*(Laws 2007 LB236 § 40; Laws 2014 LB853 § 49.)*

**Three things worth carrying:**

1. **Five registries in one axis-C check.** Every other state in the survey checks
   one, occasionally two. **A `registry_checked` boolean is hopeless here** — this
   is five separate lookups against five separate authorities, each needing its own
   date and outcome.
2. **The language requirement is client-matched.** *"…or the language of the
   person for whom he or she is providing"* — so language is **a
   per-assignment qualification**, not a worker attribute. Same family as
   Louisiana's per-client competency, arriving through a plain-English
   qualification clause. (§ 71-6603 goes further for home health aides: the
   language must be understood by **the patient *and* the supervising staff
   member**.)
3. **Axis A is delegated to the agency in one clause** — *"training sufficient to
   provide the requisite level of … services offered"*. **No hours, no topics, no
   approved-programme list.** Nebraska joins South Carolina in delegating axis A
   while specifying axis B and C precisely — the same delegation-as-a-shape
   pattern.

The conviction test is also unusual: not an enumerated barred list, and not
pure agency discretion, but a **statutory two-part test** — over one year's
imprisonment **and** *rationally related to fitness for this work*. **A third
axis-B shape**, distinct from Colorado's agency-judgment and South Carolina's
enumerate-then-delegate.

### § 71-6503 — agency duties, including a conditional driving check

> "An in-home personal services agency shall **employ or contract with only
> persons who meet the requirements of section 71-6502** … shall perform or cause
> to be performed a **criminal history record information check** on each worker
> **and a check of his or her driving record** as maintained by the Department of
> Motor Vehicles **or by any other state which has issued an operator's license**
> to the worker, **when driving is a service provided by the … worker**, and shall
> **maintain documentation of such checks … for inspection at its place of
> business**."

> **A driving-record check conditioned on the service being provided** — the same
> per-assignment shape as Nevada's transport-liability insurance, but on a
> *background check* rather than a document. And it reaches **out-of-state
> licences**, which a single-state DMV lookup would miss.
>
> Note also **"employ or contract with"**: Nebraska expressly contemplates
> contracted workers. Which is why the reclassification check matters —

### Reclassification check — Nebraska is clean

Ten-pattern check run against §§ 71-6502, 71-6503, 71-6603 and the full chapter
71 index: **zero hits** for *not independent contractors*, *shall be
considered/deemed an employer*, *deemed/considered employees*, *employer of
record*, *co-employer*, *joint employer*.

**Nebraska does not assign employment status by statute**, and its
*"employ or contract with"* language confirms contractors are contemplated.
**Contrast Rhode Island**, where the same activity would make the agency the
employer for all purposes.

### § 71-6603 — home health aides, six routes

18+, good moral character, the same conviction test, the language requirement
(patient **and** supervisor), and **one of six qualifications**: an approved home
health aide training course meeting § 71-6608.01; graduation from a school of
nursing; employment as a **home health aide II** by a licensed agency before
**1991-09-06**; a nursing-school course including practical clinical experience in
fundamental nursing skills **plus** a competency evaluation under § 71-6608.02; an
approved nurse-aide course under § 71-6039 **plus** a competency evaluation; or
employment as a **home health aide I** before 1991-09-06.

**Two grandfather clauses anchored to a 1991 date**, still operative — the same
dated-rule shape as Ohio's pre/post-2008 split and Louisiana's 2018 administrator
test.

---

## 2. Route ledger — six states still to open

| State | Attempt | Result |
|---|---|---|
| **Nebraska** | `nebraskalegislature.gov/laws/browse-chapters.php?chapter=71` → `statutes.php?statute=<n>` | **WORKS** — chapter index 272 KB, per-section pages clean. |
| Delaware | `delcode.delaware.gov/title16/index.html` | 200, 8.4 KB index reached; **chapter list parsed poorly and the home-care chapter was not identified.** Retry with a different extraction. |
| Hawaii | `capitol.hawaii.gov/hrscurrent/Vol06_Ch0321-0344/HRS0321/` | 200 — an **IIS directory listing** of HRS 321 section files; my link extractor found no `href`s in its markup. The files are there; the parser was wrong. |
| West Virginia | `code.wvlegislature.gov/16-5D/` | 200, but the body is the **whole-code chapter navigation**, not article 5D. Needs the article's own path. |
| North Dakota | `ndlegis.gov/cencode/t23c17-5.html` | **300 Multiple Choices** — *"The document name you requested … could not be found"*, i.e. a wrong filename, with the server offering alternatives. |
| Alaska | `akleg.gov/basis/statutes.asp` | 200 — *"This page is no longer used please use …"*. **A self-declared move**, like South Carolina's renumbering. Follow the pointer. |
| South Dakota | `sdlegislature.gov/Statutes/34-12` | 200, **288 characters** — *"doesn't work properly without JavaScript"*. SPA. |

**Three of these are my parser or my path, not the publisher** (Delaware,
Hawaii, West Virginia), **one is a self-declared move** (Alaska), **one is a
wrong filename the server said so about** (North Dakota), and **one is a genuine
SPA** (South Dakota). Recorded that way so the next pass does not treat them
alike.

---

## 3. Tier 2

| Item | Status |
|---|---|
| Neb. Rev. Stat. §§ 71-6501, 71-6504, 71-6608.01, 71-6608.02, 71-6039, 71-417 | **NOT READ** — definitions, applicability, the training-course standard and the competency-evaluation standard. **§ 71-6608.01 is where any Nebraska hour figure would live.** |
| Nebraska administrative rules (Title 175 NAC) | **NOT ATTEMPTED** |
| Whether Nebraska licenses in-home personal services agencies at all | **NOT ESTABLISHED** — §§ 71-6502/6503 impose duties without, in the text read, a licensure requirement. § 71-6504 (applicability) was not read. |
| DE, HI, WV, ND, AK, SD | **NOT OPENED** — see ledger. |
| AL, MS, UT, CT, KS | **NO ROUTE** — carried. |
| ID | **CLOSED** — state-side outage. |
| IN | **ON HOLD** |

## 4. Method notes

- **The reclassification check now runs per state, as it is read.** Nebraska is
  the first state checked at read time rather than in a retrospective sweep. It
  cost one command.
- **Distinguish six kinds of failure, not one.** This round produced a bad
  filename the server itself flagged, a page that says it moved, an SPA, and
  three cases where my own extractor or path was wrong. Only the SPA is a
  property of the publisher.
- **A statutory qualification can be per-assignment.** Nebraska's language
  requirement and its driving-record condition both depend on **who the worker is
  sent to and what they will do there** — not on the worker alone.
