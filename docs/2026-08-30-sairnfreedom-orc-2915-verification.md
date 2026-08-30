# SAIRNfreedom — Ohio Rev. Code Chapter 2915 verification

**Read 2026-08-30 from codes.ohio.gov, the Revised Code itself.** Not a
summary site, not a gaming-vendor blog, not a law-firm explainer.

**This is a FRESH BASELINE, not a diff.** The prior research (chat memory,
`/areas/sairnveterans.md`, read 2026-08-29) does not exist as a file on any
clone, so there was no prior state on disk to compare against. Everything below
was read today. Where it disagrees with the prior note, the disagreement is
recorded rather than silently overwritten — the prior note got the substance
right and the citations wrong in ways that would have produced a wrong data
model.

**Scope of this read:** 2915.01, 2915.09, 2915.10, 2915.101. Not yet read:
2915.02–2915.08, 2915.091–2915.093, 2915.11–2915.13, and the Attorney General's
charitable-gaming rules in the Ohio Administrative Code, which are a separate
body of requirements and are **not** covered by anything here.

---

## Confirmed from the prior note

| Claim | Status |
|---|---|
| 2915.01 effective 2025-09-30 | **Confirmed** — "Effective: September 30, 2025", Latest Legislation House Bill 96, 136th General Assembly |
| Division (GG)(11) makes canteen costs an allowable bingo expense | **Confirmed, verbatim** (below) |
| Bingo session = 5 continuous hours, plus 2-hour instant/electronic windows either side | **Confirmed** — 2915.01(S) |
| gross receipts → gross profit → net profit chain | **Confirmed** — 2915.01(T), (EE), (FF) |

**2915.01(GG)(11), verbatim:**

> "Expenses for maintaining and operating a charitable organization's
> facilities, including, but not limited to, a post home, club house, lounge,
> tavern, or canteen and any grounds attached to the post home, club house,
> lounge, tavern, or canteen"

**The definitional chain, verbatim:**

- **(T) "Gross receipts"** — "all money or assets, including admission fees,
  that a person receives from bingo without deduction of prizes or expenses"
- **(EE) "Gross profit"** — "gross receipts minus amount expended for prize
  awards"
- **(FF) "Net profit"** — "gross profit minus expenses"

---

## CORRECTION 1 — the charitable-purpose category list is ORGANIZATION-TYPE SPECIFIC, and this is the single most important finding for the data model

The prior note said net profit must go to *"specific charitable-purpose
categories only (division V) — scholarships, flag donations, disaster relief,
youth activities, patriotism promotion, etc."*

Those words are real and they are in the statute. **They are in division
(V)(2), which is the VETERAN'S ORGANIZATION limb only.** A fraternal
organization is governed by **(V)(3)**, which is an entirely different test with
none of those categories in it.

**(V)(2) — veteran's organizations** (VFW, American Legion posts and their
auxiliaries). Net profit must be:

> "used by the post, chapter, or organization for the charitable purposes set
> forth in division (B)(12) of section 5739.02 of the Revised Code, is used for
> awarding scholarships to or for attendance at an institution mentioned in
> division (B)(12) of section 5739.02 of the Revised Code, is donated to a
> governmental agency, or is used for nonprofit youth activities, the purchase
> of United States or Ohio flags that are donated to schools, youth groups, or
> other bona fide nonprofit organizations, promotion of patriotism, or disaster
> relief"

Note (V)(2) also carries a **75%-veteran membership test** and a
no-private-inurement condition, and it **cross-references ORC 5739.02(B)(12)**,
a sales-tax section not yet read. The full category list is therefore *not yet
fully enumerated* — 5739.02(B)(12) has to be read before the tag list is
complete.

**(V)(3) — fraternal organizations** (Elks, Moose, Eagles). Net profit used:

> "exclusively for religious, charitable, scientific, literary, or educational
> purposes, or for the prevention of cruelty to children or animals, if
> contributions for such use would qualify as a deductible charitable
> contribution under subsection 170 of the Internal Revenue Code"

And a hard precondition: the organization must have been **"in continuous
existence in this state for fifteen years."** A fraternal lodge younger than
that does not qualify under this limb at all. That is a gating fact, not a
category.

### Why this matters more than it looks

**The disbursement tag list is not one list.** A VFW post and an Elks lodge, in
the same product, in the same state, tag the same dollar against different
legally-enumerated category sets. Building one shared enum would be wrong for
one of them, and wrong in the direction that produces a clean-looking state
licence renewal report backed by the wrong statute.

This is the SAIRNroofing multi-state lesson recurring on a different axis:
"Ohio-only" removes the *state* variable and does not remove the variation.
Here the axis is **organization type**, and it is inside a single state.

Same shape as `rf_contingency_rules`: the category set belongs in a **row with
a citation**, keyed by organization type, not in a hardcoded array.

---

## CORRECTION 2 — two different net-profit regimes, split by game type

Division (V) opens: *"'Charitable purpose' means that the net profit of bingo,
**other than instant bingo or electronic instant bingo**, is used by..."*

So (V) does **not** govern instant bingo. Instant-bingo net profit is governed
by **2915.101** (effective 2021-09-30), which imposes percentage formulas
rather than a purpose list:

- First $250,000 (or adjusted amount) per **calendar year**: at least **25%**
  to qualified organizations; up to 75% retained for expenses.
- Above $250,000: at least **50%** to qualified organizations; **5%** permitted
  for the organization's own charitable purposes or community action; 45%
  retained for expenses.
- Veteran's, fraternal and sporting organizations are treated **more favourably
  than other charities**, which must distribute 100%.

The prior note collapsed these into one regime. They are two, and a post
running both traditional bingo and instant bingo is subject to both
simultaneously on different money.

---

## CORRECTION 3 — the fund-segregation requirement is real, but it is 2915.10(C), not GG(11), and the relationship runs the other way

The prior note framed GG(11) as *"legally linking the bar and the bingo
operation's books"* and treated the segregation requirement as flowing from
that linkage. That has it backwards, and the real provision is stronger and
more specific than the summary.

**2915.10(C), verbatim:**

> "The gross profit from each bingo session or game described in division
> (O)(1) or (2) of section 2915.01 of the Revised Code shall be deposited into
> a checking account devoted exclusively to the bingo session or game."

All bingo expenses and net-profit distributions must be made **"only by checks
or electronic fund transfers drawn on the bingo session or game account."**

Three things follow that the app has to model exactly:

1. **It is GROSS PROFIT that must be deposited** — gross receipts *minus prize
   awards* — not gross receipts. Depositing the wrong figure is a records
   violation even when the arithmetic later reconciles.
2. **An exclusive account, and payment only from it.** No cash disbursement
   path. That constrains the nightly canteen close-out design directly.
3. **GG(11) then permits canteen operating costs to be paid OUT of that
   segregated account as an allowable bingo expense.** So the correct mental
   model is: mandatory segregation on the way in, permitted and enumerated
   linkage on the way out. That is exactly why every canteen expense charged to
   bingo needs an auditable tag — not because the books are merged, but because
   they are legally separated and one specific class of expense is allowed to
   cross.

---

## NEW — requirements not in the prior note at all

### 2915.10(A) is a schema specification, and it names the canteen explicitly

Records to be kept **at least 3 years**:

| Div | Requirement |
|---|---|
| (A)(1) | Itemized gross receipts and profits **by game type** |
| (A)(2) | Itemized expenses with **payee names** and receipts |
| (A)(3) | Prize lists with winner name, address and **SSN for prizes $600+** |
| (A)(4) | Net profit recipients with names/addresses and itemized expenditure |
| (A)(5) | **Participant count per session** |
| (A)(6) | **Food and beverage sales receipts** |
| (A)(7) | **Food and beverage expenses**, with payee names and receipts |

(A)(6) and (A)(7) are the canteen↔bingo linkage as a *records* obligation, and
they are the strongest single justification for building the canteen and the
gaming module as one product rather than two.

- **(B)** Records kept at the principal/headquarters location; the Attorney
  General must be notified of that location.
- **(D)** Annual inventory of bingo supplies, **due by November 1**.
- **(H)** Attorney General and law enforcement may inspect accounts and records.

**Handling note:** (A)(3) requires storing winner **Social Security numbers**
for prizes of $600 or more. That is regulated PII sitting inside a gaming
record, and it needs a deliberate decision about encryption, access role, and
retention **before** the table exists — not after. Flagging it here so it
cannot be discovered late.

### 2915.09 — hard operational limits the event calendar must enforce

Section title: *"Illegally conducting bingo game — rules."* Effective
2021-09-30.

- **(C)(4)** No more than **three bingo sessions in any seven-day period**
  (exceptions for volunteer firefighter and rescue organizations).
- **(C)(5)** Maximum prize payout **$6,000 per session**.
- **(C)(6)** No sessions between **2:00 a.m. and 10:00 a.m.**
- **(C)(7)** Under-18s may not work as bingo game operators.
- **(C)(8)** Persons with felony or gambling convictions may not be operators.
- **(C)(12)** Under-18s may not play under 2915.01(O)(1).
- **(D)(1)** No *"commission, wage, salary, reward, tip, donation, gratuity, or
  other form of compensation"* to bingo game operators.

The three-sessions-per-seven-days rule and the 2 a.m.–10 a.m. blackout are
scheduling constraints, not reporting fields — the booking calendar has to
refuse to create a violating session, the same fail-closed posture the roofing
rescission engine uses.

**(D)(1) interacts with the canteen staffing model**: a post that pays a
bartender who also runs the bingo game has a problem the software should be
able to see.

---

## CORRECTION 4 — the chapter is not uniformly dated

The prior note recorded the chapter as *"effective 2025-09-30."* That is true
of **2915.01 only**. As read today:

| Section | Effective date shown |
|---|---|
| 2915.01 | **2025-09-30** (HB 96, 136th GA) |
| 2915.09 | 2021-09-30 |
| 2915.10 | 2021-09-30 |
| 2915.101 | 2021-09-30 |

Recording one date for a whole chapter is the same class of error as recording
one seed-file version for a whole rule set. **Every rule row this app stores
must carry the effective date of the section it came from, not a chapter-level
date.**

---

## Open items before any compliance code is written

1. **Read ORC 5739.02(B)(12)** — cross-referenced by (V)(2). The veteran's
   category list is incomplete without it.
2. **Read the Ohio Administrative Code charitable-gaming rules** and the
   Attorney General's licensing material. Statute is not the whole obligation;
   the AG administers the licence and the renewal report this app is meant to
   feed.
3. **Read 2915.091 / 2915.092 / 2915.093** — instant bingo conduct and location
   rules, and the veteran's-organization-specific provisions.
4. **Confirm the verbatim text by a second human read** before any of it is
   encoded. Everything above came from a single automated read per section. The
   quotes are reproduced exactly as returned, and statutory text going into a
   compliance engine deserves a second pair of eyes on the page itself.
5. **Liquor permit law is entirely unexamined.** A post canteen operates under
   an Ohio liquor permit class with its own rules; nothing in Chapter 2915
   covers it. Out of scope for this read and it should not be assumed handled.

---

## What this changes about the build

- The charitable-purpose tag list is **per organization type**, stored as cited
  rows, not a shared enum. Veteran's and fraternal posts get different sets.
- The **fraternal 15-year-continuous-existence test** is a licence-eligibility
  precondition and belongs in the post's profile, gating whether (V)(3)
  disbursement tagging even applies.
- **Instant bingo needs its own net-profit engine** with the 25/50/5/45
  percentage tiers and a calendar-year accumulator, separate from the
  purpose-tagged path.
- The **bingo checking account is a first-class entity**, not an attribute. The
  nightly canteen close-out has to know that bingo gross profit lands there and
  that canteen costs charged to bingo must be paid from it.
- The event calendar is a **constraint enforcer**, not a display.
