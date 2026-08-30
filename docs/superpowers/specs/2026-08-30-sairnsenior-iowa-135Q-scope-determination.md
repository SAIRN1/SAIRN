# SAIRNsenior — does Iowa's platform-registration law apply to us?

2026-08-30. **Scope determination.** Answers the open question raised in
`2026-08-30-sairnsenior-state-round-13-iowa-platform-registration.md`.

> **This is a documented reading of a statute, not legal advice.** The
> quotations below are primary and verifiable; the conclusion is a reasoned
> application of them to the product as it exists today. Before anything
> customer-facing rests on it — a contract term, a marketing claim, an answer to
> an Iowa prospect — it should be confirmed by counsel. `sairn-decision-gate`'s
> rule about claims made outside the team applies.

---

## The answer

**SAIRNsenior as currently built is OUTSIDE Iowa Code ch. 135Q. It is neither a
"health care employment agency" nor a "health care technology platform", and no
registration is required.**

**Adding an open-shift marketplace where non-employee caregivers bid would put it
inside**, and the $500 annual registration would then be the smallest of the
consequences.

---

## 1. What the statute actually requires

Source: **Iowa Code 2025, ch. 135Q**, `legis.iowa.gov/docs/code/135Q.pdf`.

### § 135Q.1(6) — "Health care technology platform"

> "…includes an individual, a trust, a partnership, a corporation, a limited
> liability partnership or company, or any other business entity that develops
> and operates, offers, or maintains a system or technology that provides an
> **internet-based or application-based marketplace** through which an
> **independent nursing services professional bids on open shifts posted by a
> health care entity** to provide nursing services for the health care entity."

**Three cumulative elements**, all of which must be present:

| # | Element | SAIRNsenior |
|---|---|---|
| 1 | an internet- or application-based **marketplace** | **No.** Single-tenant, agency-facing app. Panels: dashboard, AI, clients, scheduling, billing, caregivers, compliance, reports, security, settings. No cross-agency market. |
| 2 | an **independent** nursing services professional **bids** | **No.** Zero occurrences of "open shift", "bid", "bidding", "marketplace", "independent contractor" or "1099" anywhere in `sairnsenior.html`. |
| 3 | on **open shifts posted by a health care entity** | **No.** The model is roster-and-assign — 65 occurrences of "assign", a `roster`, and the employee list read through the shared `employees` resource. Shifts are **assigned to known staff**, not posted for claiming. |

### § 135Q.1(7) — "Independent nursing services professional"

> "…a person engaged as an **independent contractor through a health care
> technology platform**… An independent nursing services professional shall be
> considered an independent contractor **provided the … professional in the …
> professional's sole discretion bids on open shifts and chooses where, when, and
> how often to work.**"

The role is defined **by the bidding behaviour**, and it only exists *through a
platform*. A scheduled employee assigned by a coordinator is not one.

### § 135Q.1(3) — "Health care employment agency"

> "(a) …an agency that **contracts with a health care entity in this state to
> provide agency workers** for temporary or temporary-to-hire employee
> placements.
> (b) …does not include a health care entity or an affiliate … **when acting as a
> health care employment agency for the sole purpose of providing agency workers
> to the health care entity itself** or to an affiliate…
> (c) …does not include a health care technology platform."

**SAIRNsenior does not provide workers to anyone.** It licenses software. And
even the customer agency is excluded by (b) when it staffs itself.

---

## 2. The trap in this chapter, and it is not the one I expected

**"Nursing services" is not limited to nursing.** § 135Q.1(10):

> "'Nursing services' means those services which may be provided only by or under
> the supervision of a nurse. 'Nursing services' **includes** services performed
> by a registered nurse, a licensed practical nurse, a certified nurse aide, a
> certified medication aide, a **home health aide**, a medication manager, or by
> **noncertified or nonlicensed staff providing personal care as defined in
> section 231C.2**."

*(It excludes practice by an ARNP/APRN under ch. 152 or 152E.)*

> **A personal-care marketplace would be in scope.** The intuitive defence — *"we
> only do non-medical personal care, this is a nursing statute"* — **fails on the
> statute's own words.** Whoever evaluates a future marketplace feature must not
> reach for it.

---

## 3. What "inside" would cost — so the trade-off is visible before it is made

If SAIRNsenior ever ships open-shift bidding by non-employees, § 135Q.3 attaches:

- **§ 135Q.3(1)(a)** — register **annually** with the Department of Inspections,
  Appeals and Licensing; **$500 annual fee**; certificate of registration issued
  on approval.
- **§ 135Q.3(1)(b)** — failing to register **prohibits the platform from
  contracting with any health care entity in Iowa.** Not a fine — a market ban.
- **§ 135Q.3(1)(c)** — a platform allowing bidding on open shifts is an
  **authorized agency for access to the single contact repository** (Iowa's
  background-check system), **and must rerun background checks after two
  consecutive years of inactivity** by a professional. *A dormancy-triggered
  re-check — a scheduling-data-driven compliance job.*
- **§ 135Q.3(2)** — the platform must **verify** that each professional
  (a) supplies documentation demonstrating they meet **all applicable state
  requirements and qualifications of personnel in a health care entity setting**;
  (b) meets all applicable **minimum state licensing and certification**
  requirements; and (c) **maintains professional liability insurance of
  $1,000,000 per occurrence and $3,000,000 aggregate.**
- **§ 135Q.3(3)(a)(1)** — the platform **shall not restrict** a professional's
  employment opportunities by noncompete *(text continues beyond what was read)*.
- Plus, from 481 IAC ch. 55: **immediate** facility notification on a
  dependent-adult-abuse allegation; documentation to the department or entity on
  demand; and **quarterly reporting of every Medicare/Medicaid entity contracted
  with and the average amount charged**, broken down by provider type and worker
  category.

> **§ 135Q.3(2)(a) is the one that would bite hardest.** It makes the platform
> responsible for verifying that each worker meets **"all applicable state
> requirements and qualifications"** — which, across the thirty-three states in
> this survey, is the entire five-axis model plus the behaviour constraints.
> Iowa would make SAIRNsenior the party that has to get that right, per worker,
> as a condition of operating.

---

## 4. What was checked, and what was not

**Checked:** Iowa Code § 135Q.1 definitions (1)–(11) and § 135Q.3(1)–(3)(a)(1),
read from the Legislature's own PDF; 481 IAC ch. 55 (round 13); and
`sairnsenior.html`'s panel set and staffing vocabulary by direct grep.

**Not checked:**

- § 135Q.2 (employment-agency requirements), § 135Q.4 (penalties and
  enforcement), § 135Q.5 (department annual report).
- The remainder of § 135Q.3(3) beyond the noncompete clause.
- Iowa Code § 231C.2's definition of personal care, incorporated by (10).
- **Whether any other state has an equivalent** — this survey found it only
  because a keyword sweep happened to include "home care". **No other state has
  been checked for a platform-registration statute**, and the absence of a
  finding is not evidence of absence.

**A standing condition, not a one-time answer.** The determination is about the
product *as built on 2026-08-30*. It should be re-run against § 135Q.1(6) before
any feature ships that lets a worker who is not the agency's employee choose
shifts.
