# SAIRNfreedom — pre-build research baseline

**Status:** research only. Nothing built. No spec, no schema, no app file.

**Provenance, stated because it matters for how much this is trusted:** the
body of this document originated in a chat session's own memory system
(`/areas/sairnveterans.md`), not on any clone's filesystem — which is why a
repo search for it found nothing. It is written here so Hank, CC and Ted can
read it without someone pasting it, which was the whole reason for the file.

The competitive and evidence sections below are recorded **as received** and
have not been independently re-verified in this pass. The **Ohio statutory
section has** — see *Statutory re-verification* at the end, which was run
fresh against codes.ohio.gov on 2026-08-30 and carries two corrections.

---

## Scope

Ohio only, for now. **Fraternal/veterans-style clubs only** — VFW, American
Legion, Elks, Moose, Eagles. Explicitly **NOT** country clubs, yacht clubs, or
other private clubs lacking the canteen + gaming combination. That combination
is the product, not the membership.

## Core structural insight

Each post/lodge is its **own independently-governed, independently-licensed
entity** — its own bingo licence, its own liquor licence, its own treasury —
even under a shared national umbrella. Confirmed for both VFW and Moose
International structures.

So "multi-location" here means a **district/state-level rollup view for an
overseeing body**, not one owner running several physical locations as one
operation. That is a materially different data model from every other
multi-location feature on this platform and should not be copied from one.

## The competitive gap

- **TidyHQ** — 300+ service clubs, 32 countries. Serves membership and
  governance (dues, meetings, AGM tooling). **Zero** canteen/bar POS, **zero**
  state gaming/bingo compliance, **zero** fund segregation between canteen and
  bingo.
- **Member Muster** — American Legion-specific; appears membership/dues only.

No competitor found combines membership + regulated bar + regulated gaming +
legally-required fund segregation. That intersection is the opening.

## Evidence base for the canteen/financial pain points

From VFW's **own official training materials**, not inferred:

- The **Quartermaster** is a bonded volunteer officer, *personally* responsible
  for all post funds.
- VFW's own *Quartermaster Financial Playbook* advises posts to begin by simply
  listing income and expenses **in one place** — which is the actual starting
  bar to clear.
- A real Frankfort VFW post **nearly closed** because financial records and
  bills went to a now-deceased member's home with no shared visibility.
- Trustees are **required** to physically inventory canteen liquor regularly to
  check for shortage.

## Canteen bottle inventory — phased

- **Phase 1:** photo-based fill-level estimation. Same category as
  **Partender**, an existing proven competitor — differentiated by tying into
  the post's event calendar and bingo-fund compliance data rather than being a
  standalone stock count.
- **Phase 2:** passive, always-on proximity/depth sensor (inspired by
  Spill-O-Not) for zero-touch tracking. **Only after Phase 1 is validated with
  real posts.**
- **LiDAR ruled out** — impractical for standing-bottle fill-through-glass at
  bar distance.

## Hall rental

UK village-hall rate-sheet pattern: hourly/session rates varying weekday vs
weekend, a discount tier for members/regulars/charities vs the public rate, and
a **separate, larger refundable damage deposit specifically for
alcohol-serving events**.

## Disbursement tracking

Nonprofit **fund accounting** concept — named restricted buckets, not one
pooled total — but deliberately **not** full grants-management software. A
simple log tagged to Ohio's specific allowed charitable-purpose categories, for
state licence renewal reporting.

## AI marketing assistant

Grounded in the post's **own live operational data** — canteen specials,
upcoming bingo, membership trend, events — replacing generic promotion with
informed, timely, targeted content. Pattern validated by Spain's **GUST**
cannabis-club software: different vertical, same AI-on-own-data shape.

## Deferred to a future phase

Building maintenance/facilities tracking; officer election/term/bonding
tracking; Phase 2 passive sensor hardware.

**Volunteer/service-hour reporting was deferred in the original note but has
since been pulled INTO phase 1** at Michael's request.

---

# Statutory re-verification — Ohio Rev. Code Chapter 2915

Run fresh against **codes.ohio.gov** on **2026-08-30**, as an independent
check rather than a diff (there was no prior state on disk to diff against).
Every claim below was confirmed. **Two corrections were found**, both of the
kind that would mislead a later reader rather than break anything today.

## Confirmed, with the division pinned

| Claim | Verified | Where |
|---|---|---|
| Charitable purpose enumerates scholarships, flags, patriotism, disaster relief, youth activities | YES | **§2915.01(V)** |
| Allowable expenses explicitly include canteen/clubhouse operating costs | YES | **§2915.01(GG)(11)** |
| Bingo session = max 5 continuous hours | YES | **§2915.01(S)(1)** |
| Instant bingo for up to 2 hours before **and** 2 hours after that period | YES | **§2915.01(S)(2)** |
| Veteran's organization defined | YES | **§2915.01(J)** |
| Fraternal organization defined | YES | **§2915.01(L)** |

**§2915.01(GG)(11), verbatim** — this is the provision that legally links the
bar's books to the bingo operation's, and it is the load-bearing one for the
whole product thesis:

> "Expenses for maintaining and operating a charitable organization's
> facilities, including, but not limited to, a post home, club house, lounge,
> tavern, or canteen and any grounds attached to the post home, club house,
> lounge, tavern, or canteen"

**§2915.01(S), verbatim:**

> "A period that includes both of the following: (1) Not to exceed five
> continuous hours for the conduct of one or more games described in division
> (O)(1) of this section, instant bingo, and electronic instant bingo; (2) A
> period for the conduct of instant bingo and electronic instant bingo for not
> more than two hours before and not more than two hours after the period
> described in division (S)(1) of this section."

## CORRECTION 1 — the session limits are a DEFINITION, not a conduct rule

The baseline recorded "bingo session time limits" without a division. The
natural place to look is §2915.09 (*Illegally conducting bingo game*), and
**they are not there.** They live in the **definition** of "bingo session" at
**§2915.01(S)**.

This matters for implementation: the 5+2+2 window is not a rule the software
enforces against a session, it is what the word *session* legally **means**.
Anything the product calls a "session" that runs longer, or sells instant bingo
outside those windows, is not a non-compliant session — it is **not a session
at all** under the statute, and every downstream calculation keyed to
"per session" is then keyed to nothing.

What §2915.09 *does* carry, and is separately relevant: division (C)(6)
prohibits conducting a session "at any time during the eight-hour period
between two a.m. and ten a.m.", with instant bingo sales permitted to begin at
9 a.m. for a 10 a.m. session.

## CORRECTION 2 — "Chapter 2915, effective 2025-09-30" is imprecise

That is the effective date of **§2915.01 only**. Sections in the chapter carry
**different** effective dates — **§2915.09 is effective 2021-09-30**.

Citing a single effective date for the whole chapter would be wrong about most
of it. Any compliance claim this product makes must cite the **section**, with
that section's own effective date, the same discipline SAIRNlaw's deadline
seeds already use per-jurisdiction.

## The profit chain — verified 2026-08-30, all three divisions

| Term | Division | Definition (verbatim) |
|---|---|---|
| Gross receipts | **§2915.01(T)** | "All money or assets, including admission fees, that a person receives from bingo without the deduction of any amounts for prizes paid out or for the expenses of conducting bingo." |
| Gross profit | **§2915.01(EE)** | "Gross receipts minus the amount actually expended for the payment of prize awards." |
| Net profit | **§2915.01(FF)** | "Gross profit minus expenses." |

    gross receipts  − prizes paid   = gross profit
    gross profit    − expenses      = net profit

**This is where the whole product thesis actually closes.** "Expenses" in
(FF) is the enumerated allowable list at (GG) — which includes the canteen at
(GG)(11). So canteen operating cost is deductible in arriving at the net
profit figure that the charitable-distribution rules then bind. The bar's
books are not merely *adjacent* to the bingo books; they are an input to them.

## Net profit distribution — §2915.101, and it is TIERED

Effective **2021-09-30** (not 2025-09-30 — see Correction 2).

For **veteran's / fraternal / sporting** organizations, per calendar year:

| Annual net profit | Must distribute | May retain |
|---|---|---|
| First **$250,000** (or adjusted amount) | **≥ 25%** | ≤ 75% |
| Amount **above $250,000** | **≥ 50%** | 45%, plus 5% for the organization's own charitable purposes |

For other charitable organizations: **100%** of net profit must be
distributed.

Applies to instant bingo and electronic instant bingo without differentiating
between them. Stated on a **calendar year** basis; the section does **not**
set a deadline for completing distributions within that year.

**Product consequence:** this is not one ratio, it is a threshold with two
regimes. The software must track **cumulative annual** net profit against
$250,000 and switch ratio at the crossing — a running total, not a
per-session or per-event calculation. Note "(or adjusted amount)": the
threshold is adjustable, so it must be configuration, never a constant.

## Licence types — OAC 109:1-4-08

Effective **2021-12-23**.

- **Type I** — bingo as defined in §2915.01(O)(1).
- **Type II** — instant bingo / electronic instant bingo **at a bingo
  session**. Requires Type I.
- **Type III** — instant bingo / electronic instant bingo **other than at a
  bingo session**.

Veteran's and fraternal organizations may hold Types I, II (with I), and III.

**Product consequence:** licence type is not a display field, it gates which
activities are lawful for that post. A Type III-only post conducting instant
bingo *at* a session is out of compliance. The type must drive behaviour.

## Still not verified — flagged rather than assumed

- **LIQUOR LICENSING IS ENTIRELY UNEXAMINED.** ORC 4301/4303 and OAC
  4301:1-1-\*. The canteen half of this product has its **own regulator, own
  licence, own record-keeping and own inspection regime**, and none of it is
  covered by anything above. Everything verified in this document is the
  **gaming** half. **Do not build the canteen side assuming compliance is
  covered — it is not.** Deferred by decision, not by oversight; recorded here
  so nobody infers coverage from the depth of the gaming research.
- OAC 109:1-4-08 as read contains **no** record-keeping, reporting or renewal
  obligations. Those almost certainly exist elsewhere in 109:1-4-\* (03 and 05
  surfaced repeatedly alongside it) and were not read. Any renewal-reporting
  feature needs them first.
- No deadline for annual distribution was found in §2915.101. Absence in the
  section read is not proof of absence in the chapter or the OAC.

---

# Patent scan — photo-based bottle fill level (Phase 1)

Run 2026-08-30, before any build, because a patent problem in this category
invalidates a design path *after* it is built and Partender being an
established competitor is exactly when prior art is most likely to exist.

**This is a preliminary scan, not a freedom-to-operate opinion.** I am not
counsel. Claims were read via published summaries and one verbatim pull;
claim construction, prosecution history, validity and design-around are all
legal questions this does not answer. Treat it as "where to point a lawyer",
not as clearance.

## The finding inverts the obvious plan

**The manual-slider-on-a-bottle-image approach — the natural way to build
Phase 1, and Partender's UX — sits inside an ACTIVE granted claim running to
2034.**

**US11961032B2** — *System and method for taking an inventory of containers
for beverages*. Inventor/assignee **Nikhil Kundra** (individual). Priority
**2012-11-26**, granted **2024-04-16**, status **"Active, expires
2034-01-21"**. Claim 1, verbatim:

> "A method for taking an inventory of containers for beverage comprising the
> steps of: providing a portable computing device having a graphical user
> interface; providing a digital image of a container corresponding to an open
> container at the graphical user interface, the digital image including an
> identification characteristic; providing a position indicator at the
> graphical user interface indicating a level by covering at least a part of
> the digital image; contacting the digital image at a position, relative to
> the identification characteristic, along the digital image of the open
> container corresponding to an amount of beverage remaining in an actual
> container to be inventoried causing the position indicator to indicate at
> the graphical user interface an amount of beverage remaining; and
> determining a volume of remaining beverage in the open container as a
> function of the position of the position indicator along the digital image."

The specification names bars, restaurants and nightclubs as the field of use.

**And the surrounding system is claimed too**, which matters more than claim 1
alone — a design-around on the slider does not clear these:

- **Claim 5** — establishment sections/subsections and container locations
- **Claim 6** — server library of container images with selection
- **Claim 9** — server-side volume aggregation with alert thresholds
- **Claim 14** — image library organised by location, sequential display
- **Claim 15** — capturing container images by camera to build the library

## The automatic approach is the clearer path, not the harder one

**US20190197466A1** — *Inventory control for liquid containers*, E-Commerce
Exchange Solutions Inc, filed 2017-12-27. Status **"Abandoned"**, and **no
granted patent in the family.** It claims automatic image-processing fill
detection — meniscus identification, landmark detection, CNN — and explicitly
removes "dependence on human visual senses". Abandoned means it cannot be
asserted, and as a published application it is **prior art** that may cut
against later claims in the same space.

So the intuition is backwards: the *simpler* Phase 1 (tap the image at the
fill line) is the encumbered one; the *harder* one (determine the level
automatically from the photograph, with no user-positioned indicator) is the
one with the clearer published landscape.

**The distinguishing line in claim 1 is precise and worth designing to:**
volume must not be determined "as a function of the position of the position
indicator." If the level comes from image analysis and the user never
positions an indicator, claim 1 is not read on.

## Checked and NOT a barrier

- **US12450865B2** — Nutricia NV, granted 2025-10-21, active to 2041. CNN
  liquid level from a portable camera — but claim 1 **requires "at least one
  number and a plurality of scale markings"** on the container and a modified
  ResNet. Liquor bottles carry no graduation markings, so claim 1 is not met.
  Field is infant nutrition.
- **EP3992847A1** — *A bottle analysis system*, computer vision, no markers
  needed. European application; scope here is Ohio. Status not pulled. Worth
  a look only if the product ever goes to the EU.

## What this means for the phased plan

Phase 1 as written in the baseline — "photo-based fill-level estimation, same
category as Partender" — **should not be built as a Partender-style slider.**
Either build the automatic determination from the start, or get counsel on
US11961032B2 before writing the UI. Phase 2's passive sensor is a different
technology and was not scanned; it needs its own pass before it is built.

## Sources

- [US11961032B2 — inventory of containers for beverages](https://patents.google.com/patent/US11961032B2/en)
- [US20190197466A1 — inventory control for liquid containers (ABANDONED)](https://patents.google.com/patent/US20190197466A1/en)
- [US12450865B2 — detecting liquid level inside a container](https://patents.google.com/patent/US12450865B2/en)
- [EP3992847A1 — a bottle analysis system](https://patents.google.com/patent/EP3992847A1/en)

## Sources

- [ORC §2915.01 — Definitions](https://codes.ohio.gov/ohio-revised-code/section-2915.01)
- [ORC §2915.09 — Illegally conducting bingo game](https://codes.ohio.gov/ohio-revised-code/section-2915.09)
- [ORC §2915.101 — Distribution of net profit](https://codes.ohio.gov/ohio-revised-code/section-2915.101)
- [OAC 109:1-4-08 — Bingo license types](https://codes.ohio.gov/ohio-administrative-code/rule-109:1-4-08)
