# SAIRNsenior — round 29: Connecticut's other half, and the worker-class split is not a Kansas quirk

2026-08-31. **Research only.** Forty-third document in the series.

Round 28 found that **the archetype attaches to the worker class, not the
state**, on a single instance (Kansas). This round reads Connecticut's unread
regime and then tests the finding against the other 41 states.

**Result: the split is real and recurs, but the *discriminator* is different in
every state that has one.** Three confirmed this round, three different axes.
And the corpus-wide pass produced something more useful than the split analysis
itself — **a defensible list of 14 states where a second worker class has
plausibly never been looked at.**

---

## 1. Connecticut D66–D79 — the aide standard is duplicated, the administrator standard is not

Round 27 read only D80–D92 (homemaker-home health aide agencies). D66–D79
(home health *care* agencies — the skilled regime) is now read.

**On the aide axis the two regimes are the same rule, restated.** D69(d)(2)(A)–(S)
reproduces D83(b)(1)–(19) nearly verbatim: the same **75-hour** curriculum with
the same thirteen elements, the same competency evaluator (**RN with 2 years'
nursing experience, 1 in home health**), the same "unsatisfactory in more than
one area = fail", the same **24-month inactivity rule**, the same **10 hours of
orientation** for anyone deemed equivalent, and the same six deeming routes
including out-of-state reciprocity.

**Two real differences:**

- **Trainer eligibility is stricter in the skilled regime.** D83 bars an agency
  from training if it has been out of compliance with **OBRA** requirements in
  the preceding 24 months. **D69 adds "and/or one or more condition of
  participation of title 42, part 484 of the code of federal regulations"** — the
  federal Medicare CoPs.
- **Supervision is heavier.** D69 requires an RN **accessible by phone and
  available to make a home visit at all times, including nights, weekends and
  holidays**, whenever aides are on assignment; a **60-day RN assessment
  conducted in the home while the aide is providing services**; and, for any task
  delegated beyond the listed duties, a clinical-record entry showing the primary
  care nurse **assessed the aide's competence and determined the task could be
  delegated safely**.

**Where Connecticut does split is the administrator class, and it splits by
agency type.**

| | Skilled agency (**D67**) | Homemaker-aide agency (**D81**) |
|---|---|---|
| Administrator | **Master's** in nursing (+ licence) or public health/administration with health-services concentration, **+1 yr** supervisory; **or baccalaureate** in nursing or administration **+2 yrs**; or a **licensed physician +1 yr** | **Baccalaureate** in nursing (+ licence) **+2 yrs**, or baccalaureate in social work/home economics/administration or related human-services field with health-services concentration |
| Grandfather | two routes — and **one of them sunsets**: the 1979 route was void after **1 Jan 1986** unless the person also met one of routes (1)–(5) | — |
| Supervisor of clinical services | RN with **master's +1 yr** home-health clinical, **or baccalaureate +3 yrs** (1 in home health), **or** diploma/associate **+3 yrs in the past 5** *plus* ANA community-health certification **or** 6 credits in community-health nursing theory or health-care management | — |

> **A sunsetting grandfather clause is worth flagging on its own.** Connecticut's
> aide grandfather (pre-1993 employment) is permanent; its 1979 administrator
> grandfather expired in 1986. **"Grandfathered" is not one state of the world —
> it has an expiry date in some rules and not others**, and a data model that
> stores a boolean loses that.

**Numeric staffing thresholds, which no other state has stated this densely:**

- **1 full-time supervisor of clinical services per ≤15 FTE professional direct
  service staff** (D68(e)(1)); that supervisor **may also be the administrator at
  ≤6 FTE** professional direct service staff.
- Therapy: a **full-time supervisor once direct therapy staff reaches 5 FTE**,
  span capped at **15 FTE**; **≥1 registered PT/OT per 6 or fewer assistants**;
  the assistant must **confer with the PT/OT every 30 days**.
- Social work: same **5 FTE / 15 FTE** supervisor rule; **≥1 qualified social
  worker per 6 or fewer assistants**.
- Aides: **1 full-time RN per ≤15 FTE aides on duty**; the aide-program
  supervisor becomes a **dedicated full-time role at 25 or more aides**.
- Absences of the administrator or the supervisor of clinical services **longer
  than one month must be reported to the commissioner**; the administrator's
  appointment within **3 days** and departure within **48 hours**.

*Compare Mississippi (round 27), which keys the same idea to **patient census**
— supervising nurse may also be administrator to 25 patients, may carry a load
to 50, must be full-time supervisory above 50. **Connecticut keys it to staff
count, Mississippi to client count.** Same constraint, incompatible units.*

---

## 2. Testing the split across the corpus — method, and its limits first

**What was searched:** the 34 SAIRNsenior write-ups on disk. **The raw state
corpus from earlier rounds does not survive** — it lived in per-session scratch
directories, so this pass reads *what the documents say*, not the underlying
rules.

Two attribution passes were run — one scoping each worker-class term to the
nearest preceding state heading, one to the enclosing paragraph.

> **The two passes disagreed substantially.** Florida scored 3 classes on the
> paragraph pass and 0 on the heading pass; Delaware 1 and 0; Utah 0 and 2. **A
> single run of this would have been reported as a finding and would have been
> wrong.** Only the **union** is used below, and only as a **candidate
> generator.**
>
> **Known false positives in the union.** "Supportive care" attaches to Alaska,
> Idaho, Indiana, Mississippi and South Dakota purely because rounds 27–28
> discuss Kansas's supportive-care tier in paragraphs that name those states.
> **Group C is over-counted. Groups A and B are the trustworthy output**, because
> a *missing* term is much harder to produce by accident than a spurious one.

### A. Nine states with no worker class named anywhere in the write-ups

**Maryland, Minnesota, Montana, New Hampshire, New Jersey, New Mexico, North
Dakota, Vermont, Wyoming.**

These are the thinnest entries in the whole survey. Whatever was read for them
was not on the worker-qualification axis at all.

### B. Five states read only on a skilled class

| State | Only class named |
|---|---|
| Alabama | HHA |
| Kentucky | HHA |
| Maine | HHA |
| **North Carolina** | CNA |
| South Carolina | HHA |

**Fourteen states in total where a second worker class has plausibly never been
examined.** Alabama is excusable — round 27 established it does not license home
health at all. The other thirteen are not.

---

## 3. Three confirmations, three different discriminators

Two states were pulled from the candidate list and read live. Both had a split,
and neither matches Kansas's.

### North Carolina — splits by whether the work is hands-on

**10A NCAC 13J** (Licensing of Home Care Agencies) carries **three tiers in one
subchapter**, and the corpus had recorded only "CNA".

**Tier 1 — in-home caregivers subject to occupational licensing (.1110(a)):**
board rules apply, plus agency-documented competency **demonstrated to a health
care practitioner**; supervision method and frequency set by **agency policy**.

**Tier 2 — in-home caregivers not subject to licensing (.1110(b)–(c)):** may be
assigned **only** activities for which competency has been demonstrated;
supervised by a health care practitioner with a **home visit every 90 days**,
with or without the aide present, **and annually while the aide is providing
care**.

**Tier 3 — companion, sitter and respite personnel (§ .1500):** a separate
section with its own definitions, scope, management and competency rules. The
class is defined by what it is *not*:

> **"Non-Hands-on Care Services"** means basic home management tasks, shopping,
> meal preparation, transportation, companion services, socialization,
> **medication reminders**, and other services that do not require "hands-on
> care" **"and which do not require training or verification of skills by a
> Registered Nurse."**

Everything relaxes at that boundary:

- supervision drops to **client contact every 3 months**, a **home visit every 6
  months**, and **annually with the worker present** — versus 90 days and annual;
- the **agency director** need only be a **high school graduate or GED holder**
  with **one year of experience** in home care/companion/sitter/respite (or be a
  health care practitioner) — the skilled-agency director standard does not apply;
- the supervisor of non-hands-on services **may also be the agency director**.

> **North Carolina draws the line at touching the client.** Kansas draws it
> between two named worker classes. **Same structural consequence, different
> trigger** — and NC's trigger is a property of the task, which is the same thing
> K.A.R. 28-51-117(g) encodes task by task.

### Maryland — splits by the client's condition, with a consent override

**COMAR 10.07.05** (Residential Service Agencies). Maryland was in **group A** —
no worker class recorded anywhere — and it has one of the sharpest rules found.

Two classes are defined: **certified caregivers** — Board-of-Nursing **certified
nursing assistants, certified medication technicians and certified medicine
aides**, who alone may perform **"certified care"** (nursing functions routinely
delegated by an RN) — and everyone else.

**The allocation rule is keyed to the client, not the worker (.10D–E):**

> An agency **may not knowingly provide or refer an uncertified caregiver**
> unless the client **(1)** does not require assistance with activities of daily
> living; **(2)** requires only ADL assistance **and, in the judgment of the
> supervising nurse, there are no predictable adverse health consequences**; or
> **(3) signs a waiver of skilled services form.**
>
> A **certified** caregiver **must** be provided where the client requires one to
> perform ADLs, **or** requires **medication administration**.

**Screening (.10B) is the most detailed found in any state**, and applies equally
to employees, independent contractors and contractual employees: state criminal
history record check or private background check, professional
licence/certification verification, **TB screening**, references, employment
history, I-9, **an in-person interview before the individual is referred to
clients**, and **a skills assessment and demonstration before client referral**.

**Training (.11) sets a floor, not a duration:** instruction and supervised
practice in personal care of the sick or disabled at home, recognising when to
refer to an RN, record keeping, ethics and confidentiality, **CPR**, standard
precautions, and **prevention of abuse and neglect**. Outside providers may
deliver it **only with written approval from the Office of Health Care Quality**.

> **Maryland's discriminator is client acuity, and it is overridable by the
> client's signature.** No credential field can express "this worker may serve
> this client because the client signed a waiver." It is a per-assignment
> authorisation with a consent artefact attached.

### Connecticut — splits by agency type, on the administrator class only

Covered in §1. **The aide standard is identical across both regimes; the
administrator and supervisor standards are not.**

---

## 4. What this does to the data model

Round 28 said the archetype attaches to the worker class. **That was right and
still too simple.** Four discriminators are now confirmed, and a state may use
more than one:

| Discriminator | State | The question it asks |
|---|---|---|
| **Worker class** | Kansas | *Which class is this person in?* |
| **Task** | North Carolina; Kansas 28-51-117(g) | *Is this task hands-on / on the permitted list?* |
| **Client condition** | Maryland | *What does this client need, and did they waive?* |
| **Agency type** | Connecticut | *Which licence does the employer hold?* |

> The lowest common denominator is not a worker attribute at all. It is
> **(worker, task, client, agency, date) → permitted or not**, with the state
> supplying which of those five actually matter. Kansas needs task and class.
> Maryland needs client and a stored consent artefact. North Carolina needs the
> hands-on flag. Connecticut needs agency type — and, for administrators, a
> grandfather route **with an expiry date**.

---

## 5. Tier 2 — what this round opened and did not close

| Item | Status |
|---|---|
| **The 9 group-A states** (MD partly done; MN, MT, NH, NJ, NM, ND, VT, WY) | **NOT READ on the worker axis.** The single largest remaining gap in the survey. |
| **The 4 remaining group-B states** (KY, ME, NC done, SC) | **ONE CLASS READ.** NC proved the payoff; the others are untested. |
| Maryland COMAR 10.07.05 **.12 Services Provided** (incl. the .12D waiver form) | **ROUTE OPEN, NOT READ** — the waiver mechanism is only referenced above. |
| Maryland **nurse referral / nursing-agency** chapters, and COMAR 10.27.11 (delegation of nursing functions) | **ROUTE OPEN, NOT READ** — the delegation rule is what makes "certified care" movable. |
| North Carolina **.1107** In-Home Aide Services, **.1003** Personnel, **10A NCAC 06A / 06X** (block-grant service levels, cross-referenced by .1502(a)) | **ROUTE OPEN, NOT READ** — 06A/06X are where NC's aide *levels* would live. |
| Connecticut **D70, D73–D79** | **ROUTE OPEN, NOT READ.** |
| Kansas 28-51-118 HCBS; Alaska 7 AAC 10.935; Arizona R9-10-1201–1209 (rest); Mississippi ch. 46 subch. 6–14; SD full-text SDCL | **CARRIED FORWARD from rounds 27–28.** |

## 6. Method notes

- **Run the same analysis two ways before believing either.** Two attribution
  passes over the same 34 documents disagreed on roughly a third of states. The
  disagreement is the finding: **a single pass would have been reported as a
  matrix and been wrong.**
- **Absence is a stronger signal than presence in a text heuristic.** A term can
  appear next to a state by accident; it rarely goes missing by accident. Groups
  A and B are usable, group C is not.
- **The candidate list paid out on the first two tries.** North Carolina and
  Maryland were picked off it blind and both had splits the corpus had missed.
  That is two for two, which argues the remaining twelve are worth the same
  treatment — **and argues that the earlier "42 states read on at least one
  axis" figure was measuring breadth of *state* coverage, not of *worker class*
  coverage.**
- **The raw corpus should be persisted.** This analysis was weaker than it needed
  to be because the source documents from rounds 1–26 are gone and only the
  write-ups survive. Future fetches worth keeping should land somewhere durable,
  not in a session scratch directory.
