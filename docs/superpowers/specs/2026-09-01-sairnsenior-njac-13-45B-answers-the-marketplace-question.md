# SAIRNsenior — N.J.A.C. 13:45B read; the round 32 §5a marketplace question is answered

**Date:** 2026-09-01
**Closes:** round 32 §5a, and the 2026-08-31 "stopped at the terms-of-use dialog"
blocker.

---

## 0. The terms-of-use dialog was not necessary

The previous session stopped because N.J.A.C. 13:45B on New Jersey's own OAL
site sits behind a LexisNexis "I Agree" click. **That click was never needed.**
The full rule text is published verbatim by Cornell LII and the statutes by
onecle, neither of which gates on an agreement. Michael authorised accepting the
terms; **the terms were not accepted, because a route existed that did not
require it.**

The four sources are persisted under `docs/sources/sairnsenior/NJ/` with sha256
of the original bytes, per the round 29 convention. **Every quotation below was
checked against the stored text, not against a fetch summary.**

## 1. The question

> Does placement by a registered Health Care Service Firm satisfy "employed by"
> under N.J.S.A. 45:11-24.6 / 24.7?

## 2. The answer: **no — and the question contains the wrong assumption**

Placement is not an alternative to employment. **Employment is the precondition
for placement.** The rule states it directly:

> **N.J.A.C. 13:45B-14.7(b)** — "A health care service firm shall only refer or
> place actively certified homemaker-home health aides that are employed by the
> agency."

A firm cannot place an aide *in order to* create the employment relationship;
it may only place aides it **already employs**. And 14.7(a) closes the other
door — an agency that is not licensed as a health care service firm "shall not
place certified homemaker-home health aides" at all.

The statutes agree, from two directions:

> **N.J.S.A. 45:11-24.6** — biennial recertification issues "only upon receiving
> documented proof from a home health agency or health care service firm that
> the homemaker-home health aide is currently employed and regularly supervised
> by a registered professional nurse."

> **N.J.S.A. 45:11-24.7** — the certificate itself must carry the legend:
> "Valid only if certified homemaker-home health aide is employed by a home
> health agency or health care service firm and is performing delegated nursing
> regimen or nursing tasks delegated through the authority of a duly licensed
> registered professional nurse."

**24.7 is the sharpest fact in this file.** The credential is not merely
*restricted* outside an employment relationship — it is **stamped on its face as
invalid**. A CHHA working through a referral marketplace is not a CHHA who is
bending a rule; they are, on the document's own text, uncertified for that work.

## 3. The one genuine opening, and the test it comes with

The definition of the firm is where the platform question actually lives:

> **N.J.A.C. 13:45B-13.2** — "'Health care service firm' means any person who
> operates a firm that employs individuals **directly or indirectly** for the
> purpose of assigning the employed individuals to provide health care, personal
> care, or companion services either directly in the home or at a care-giving
> facility, **and** who, in addition to paying wages or salaries to the employed
> individuals while on assignment, pays or is required to pay Federal social
> security taxes and State and Federal unemployment insurance; carries or is
> required to carry worker's compensation insurance; **and sustains
> responsibility for the action of the employed individuals** while they render
> health care services."

"Directly or **indirectly**" is real and is the only text in the chapter that a
platform model could stand on. But it is immediately followed by a four-part
conjunctive test the firm itself must satisfy:

1. pays wages or salaries **while on assignment**;
2. pays (or is required to pay) federal social security tax and state + federal
   unemployment insurance;
3. carries (or is required to carry) workers' compensation insurance;
4. **sustains responsibility for the action of the workers** while they render
   care.

This is a substantive employer test, not a labelling exercise. **A marketplace
that routes a client's payment to a 1099 worker and disclaims liability for that
worker's conduct fails all four** — most decisively #4, which is precisely the
risk-transfer a marketplace model exists to achieve. "Indirectly" plausibly
reaches a PEO, an employer-of-record arrangement, or a staffing subsidiary. It
does not reach a matching platform.

## 4. What this changes for the schema

Confirms and sharpens the round 32 finding rather than overturning it. New
Jersey does not merely agency-lock the credential — it locks it to an
**employment** relationship with a specific licensed entity type, and pins the
credential's *validity* to that relationship continuing (24.6 recertification,
24.7 certificate legend).

Two axes are re-confirmed as inexpressible in a single-worker-credential schema:

- **agency type** — 14.7(a): only an entity licensed as a health care service
  firm may place at all.
- **RN delegation** — 24.7 requires, *in addition* to employment, that tasks be
  delegated through a licensed RN's authority. 14.7(c)–(e) build this out: only
  delegated tasks, competence demonstrated to the supervisor, every delegated
  task documented in the patient record. **Employment alone is not sufficient
  even when it is genuine.**

A third is added: **credential validity is conditional and revocable by
employment status**, not a durable attribute of the worker. A schema that stores
"CHHA: yes" is wrong in New Jersey the moment the aide leaves the firm.

## 5. What remains for counsel — narrowed, not eliminated

The original question is answered by the rule. **The residual question is
different and much narrower:**

> Can a technology platform qualify as a health care service firm that employs
> CHHAs "indirectly" under N.J.A.C. 13:45B-13.2 — specifically, can it satisfy
> the requirement that it "sustains responsibility for the action of the
> employed individuals while they render health care services" — and if so, in
> what corporate form?

That is a structuring question for a New Jersey health care regulatory attorney,
not a rule-reading question. **It is worth asking only if the answer changes a
product decision**; if SAIRNsenior is not going to become an employer of record
or contract with one, the rule text already forecloses the model in New Jersey
and no opinion is needed.

## 6. What was not checked

- **Whether New Jersey enforces this against platforms in practice.** This is a
  read of the rules as written. No enforcement actions, advisory opinions, or
  Division guidance were searched.
- **N.J.A.C. 13:45B subchapters other than 13 and 14**, beyond the definitions
  and placement rules quoted. Chapter 45B is "PERSONNEL SERVICES" and covers
  employment agencies generally; a separate subchapter may govern referral-only
  models under a different licence class. **Not read — a real gap, and the
  most likely place a contrary answer would hide.**
- **13:45B-13.8** (uncertified/unlicensed individuals providing home-based
  services) surfaced in search and was **not** read. It governs the adjacent
  case — a firm placing *uncertified* workers with written notice to the
  client — which may be the actually-viable New Jersey model and is not covered
  by anything above.

## Sources

All four persisted with sha256 under `docs/sources/sairnsenior/NJ/`.

- [N.J.A.C. 13:45B-14.7 — Homemaker-home health aides and agencies](https://www.law.cornell.edu/regulations/new-jersey/N-J-A-C-13-45B-14-7)
- [N.J.A.C. 13:45B-13.2 — Definitions](https://www.law.cornell.edu/regulations/new-jersey/N-J-A-C-13-45B-13-2)
- [N.J.S.A. 45:11-24.6 — Conditions for issuance of biennial recertification](https://law.onecle.com/new-jersey/title-45/45-11-24.6.html)
- [N.J.S.A. 45:11-24.7 — Required language on certificate](https://law.onecle.com/new-jersey/title-45/45-11-24.7.html)
