# SAIRNfreedom — pre-build research baseline

**Status:** research only. Nothing built. No spec, no schema, no app file.

**BUILD SPEC:** `docs/superpowers/specs/2026-08-30-sairnfreedom-phased-build-spec.md`
turns everything below into a phased, dependency-ordered plan with the officer
model as the permissions basis. This file stays canonical for the **research and
the binding decisions**; that file is canonical for **what gets built in what
order**. When they disagree about a fact, this one wins.

**THIS IS THE CANONICAL SAIRNfreedom RESEARCH DOCUMENT.** Merged 2026-08-30
(CC) from two independent parallel research passes that ran the same three
pre-build gates without knowing about each other. Where they disagreed on a
fact, the disagreement was resolved against codes.ohio.gov rather than by
picking a document — see *Reconciliation record* at the end, which names every
difference and how it was settled.

Two detailed research reports are kept as **appendices** rather than inlined,
because they are source-of-record with full citation lists and inlining them
would bury the decisions above them:

- `docs/2026-08-30-sairnfreedom-competitive-and-patent-scan.md`
- `docs/2026-08-30-sairnfreedom-service-hour-reporting-research.md`

Their findings are summarised in this file. A third file,
`docs/2026-08-30-sairnfreedom-orc-2915-verification.md`, was fully absorbed
here and deleted; its content is in git history at `e04e6c9`.

---

## BINDING DECISIONS — read before designing anything

Decided by Michael 2026-08-30, on the evidence in this document. These are
settled, not options.

### 1. Bottle fill level is determined AUTOMATICALLY. No slider, ever.

**The system determines the level from the image itself. There is no user
pointing, marking, tapping, dragging or positioning step anywhere in the UI.**

This is a patent-avoidance constraint, not a UX preference. US11961032B2
claim 1 is active to **2034-01-21** and reads on a method where volume is
determined "as a function of the position of the position indicator" that the
user places by "contacting the digital image at a position ... corresponding
to an amount of beverage remaining." Full verbatim claim in the patent scan
below.

**Therefore, prohibited in the fill-level flow:**
- a slider, handle, or draggable marker over a bottle image
- tap-to-set-the-fill-line on a photo
- any control whose *position* is an input to the volume calculation
- any "confirm the level we guessed by adjusting it" step — an adjustable
  guess is still a user-positioned indicator

**Required instead:** the level comes out of image analysis. If confidence is
low, the acceptable behaviours are to **re-shoot**, **flag for manual
re-count**, or **accept a typed volume** — none of which is a position on an
image.

### 3. Phase 2's passive sensor is DEFERRED — do not plan around it

Superseded 2026-08-30. This section previously read "was not scanned; it needs
its own patent pass before it is built." **It has since been scanned, and both
routes closed** — see *Phase 2 passive sensor* below.

- **Build** is blocked by an active patent thicket (Nectar's 8+ family to
  2036, BarVision's spouts) plus a hardware business this platform has no
  part of.
- **Integrate** is blocked because neither vendor exposes an API, and the one
  confirmed operating is **$250–$300/month on a 1-year contract** — roughly
  ten times what a volunteer-run post is likely to pay for the whole product.

Phase 1's automatic photo determination carries the inventory feature.
Reopen only on real customer demand or a vendor with an actual API.

**RESIDUAL RISK ON THIS DECISION — added 2026-08-30 from the second scan. The
decision stands; this is the reasoning behind it, not a reopening.**

Two facts the first scan did not have, both of which argue the same way:

- **There is a PENDING continuation in the same family: US20240320601A1
  (application 18/586,707)**, filed 2024-02-26, published 2024-09-26. Claims
  1–21 are cancelled and claim 22 is the first independent claim — and claim 22
  *also* requires "contacting the graphical user interface at a position." A
  pending application means **claims can still be amended** while this product
  is being built.
- **Partender's own specification already discloses the automatic approach:**
  "the computer can also identify and calculate the liquid level in each bottle
  simply via photographing, video recording, or panning over the bottle(s)
  being measured."

So automatic determination is the right build path — it avoids every *granted*
claim, all of which require a user-positioned indicator — but it is **not a
clean room.** The automatic method sits on top of disclosure inside a live
family with an amendable pending continuation.

**What follows, and it does not change what gets built:** before this feature
appears in **sales material, a demo to a real post, or any external claim**,
get a real freedom-to-operate opinion from counsel. Both passes were keyword
screens by non-lawyers. Neither is clearance, and both say so.

Worth weighing when that bill arrives: this feature guards **none** of the
three things the competitive scan identifies as the actual moat (see *The
competitive gap*, corrected below). It is a demo feature, not a defensive one,
and its FTO cost should be judged on that basis.

### 2. Banner is ANIMATED app-wide, static on onboarding (2026-08-30)

Supersedes the earlier static-everywhere call. One animated flag banner,
consistently, on the dashboard and every page; **onboarding is the exception and
stays static.** The earlier rejection was of a *bad implementation* — turbulence
filters that read as water or TV static — not of the idea. It gets built
properly as real work this time, and reviewed against `sairn-visual-review` on a
rendered page before it is called done. No literal flag reproduction: diagonal
red/white/blue stripe with a small star cluster. Full reasoning in the build
spec §1d.

### 3. Scope of this document

Everything verified here is the **gaming** half. Liquor licensing is
unexamined — see *Still not verified*. Do not read compliance coverage into
the canteen side.

**Provenance, stated because it matters for how much this is trusted:** the
body of this document originated in a chat session's own memory system
(`/areas/sairnveterans.md`), not on any clone's filesystem — which is why a
repo search for it found nothing. It is written here so Hank, CC and Ted can
read it without someone pasting it, which was the whole reason for the file.

**Superseded 2026-08-30 by the merge — corrected rather than deleted, because
the original wording is what a reader would otherwise trust.** This paragraph
used to say the competitive sections were "recorded as received and have not
been independently re-verified", and that the statutory section "carries two
corrections". Both are now out of date:

- The **competitive** section HAS been independently verified — eleven products
  against primary sources — and was **rewritten**, because the original
  four-pillar framing did not survive it. See *The competitive gap*.
- The statutory section carries **five** corrections, not two, plus the
  §2915.09 operational limits.

The **canteen/financial evidence** section is still recorded as received and
remains un-re-verified. That part of the original caveat stands.

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

## The competitive gap — REWRITTEN 2026-08-30, the original framing does not survive

The baseline said: *"No competitor found combines membership + regulated bar +
regulated gaming + legally-required fund segregation. That intersection is the
opening."* **That is partially refuted.** Full scan in
`docs/2026-08-30-sairnfreedom-competitive-and-patent-scan.md`; eleven products
verified against primary sources.

**Arrow International, headquartered in Cleveland, Ohio, already markets three
of the four pillars in one shipping product.** Verbatim from their page:

> "Arrow's Tab King® is an industry-leading point-of-sale solution for clubs,
> social quarters, and charities. Designed to simplify operations and boost
> efficiency, Tab King puts every part of your business at your fingertips
> **from food and beverage to gaming, membership, time tracking, and
> reporting**."
> — equipment.arrowinternational.com/electronic-pull-tabs, 9900 Clinton Road,
> Cleveland, OH 44144

55 years in charitable gaming. Acquired Tab Wizard in December 2021,
consolidating the pull-tab + F&B POS category. Tab King USA partnered with the
**Northeast Moose Association** in 2019 on a fraternal lodge management system
including membership-card swipe for good standing.

### THE MOAT, RESTATED

**It is not the four-pillar combination.** Three of those four are combined and
selling, by a vendor in the target state with the distribution channel this
product would need anyway.

**The defensible ground is the three things no verified competitor touches:**

1. **ORC Ch. 2915 charitable-purpose disbursement tagging.** No vendor makes any
   claim about it, and it is the hardest to copy because it requires reading the
   statute correctly — see CORRECTION 3 below, where the category list turns out
   to be per organization type. A competitor bolting this on would very likely
   get exactly that wrong.
2. **District/state read-only rollup across independently-governed posts.** Only
   ClubExpress has anything adjacent, and its multi-tier chapters model is a
   general org hierarchy, not a cross-tenant regulatory rollup.
3. **Hall rental.** Only ALPost has it, inside an American-Legion-specific
   website builder with no accounting, no POS and no gaming.

**Fund segregation alone is thin and must not be relied on as the moat.** Nobody
claims it today, but it is a chart-of-accounts decision plus a reporting
template, not a hard engineering problem. If Arrow decides Ohio segregation is
worth two sprints, the four-pillar framing is fully refuted.

### Corrections to the named leads

- **TidyHQ — HOLDS.** Feature list verified: CRM, Memberships, Events, Finances,
  Communications, Tasks & Governance, Meetings, Shop, Web Pages, Documents.
  Confirmed absent: POS, bar, canteen, liquor inventory, gaming, bingo,
  charitable gaming, fund accounting, fund segregation. One caveat: "TidyAI" is
  *"AI consulting and workshops for sporting organisations"* — a services
  offering, **not** an AI assistant over org data. The "300+ clubs, 32 countries"
  figure was not found on the features page and is unverified.
- **Member Muster — APPEARS DEFUNCT.** `membermuster.com` is a parked ParkLogic
  page offering the domain; `membermuster.us` returns DNS NXDOMAIN. No feature
  claim about it is verifiable.
- **GUST — NOT FOUND.** No product by that name was locatable. The nearest real
  product is Cannabis Club Systems, whose "SmartBud AI" is verified as *product
  recommendation*, not marketing generation. **The AI-on-own-data validation
  cited in the baseline is therefore weakly supported**, and the AI marketing
  assistant should be justified on its own merits rather than on this precedent.
- **Partender — MISCHARACTERISED.** It is **not** photo-based estimation.
  Verbatim: *"Just tap where the liquor level is on the bottle and swipe to the
  next bottle."* Manual tap-on-image. This is the same finding that produced
  Binding Decision 1, reached independently.

### Others worth knowing

- **M.A.P.S. Online / EO Software** (thepostsoftware.com) — a **licensed VFW
  National vendor**, VFW-specific since 1991: ledger, check writer, bank
  reconciliation, Post Trustees' Quarterly Report, 990 summary, membership
  rosters and dues posting. Notably *"Even Bingo funds are accounted for with
  transaction codes"* — the closest thing to segregation found anywhere, and it
  is **tracking within one ledger, not segregation.** No canteen POS, no bingo
  operations.
- **ClubExpress** — decisive quote from its own Money tab: *"ClubExpress is not
  a full accounting system for your club or association."*
- **Buz Club Software** — membership + F&B POS + real accounting, but targets
  golf/yacht/city/racquet clubs, **no** fraternal or veterans mention, **no**
  gaming.

**Single most important open competitive question:** whether Tab King does real
dues billing and fraternal governance, or only card-swipe good-standing. Arrow
publishes no pricing and no feature matrix. **Request a demo before locking any
strategic conclusion.**

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
- **Phase 2: DEFERRED 2026-08-30 — not "after Phase 1", but indefinitely.**
  This originally read "passive, always-on proximity/depth sensor (inspired by
  Spill-O-Not) for zero-touch tracking, only after Phase 1 is validated with
  real posts." Both the build and integrate routes were scanned and both
  closed — see *Binding decision 3* and *Phase 2 passive sensor*. Kept in
  place rather than deleted so the original plan and its reason for dying stay
  together.
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
| ~~Charitable purpose enumerates scholarships, flags, patriotism, disaster relief, youth activities~~ | **PARTLY WRONG AS STATED — see CORRECTION 3** | those words are in **§2915.01(V)(2)**, the veteran's limb ONLY, not division (V) generally |
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

## CORRECTION 3 — the charitable-purpose category list is PER ORGANIZATION TYPE, and this is the single most important finding for the data model

**This corrects a row in this document's own confirmation table above, which
marked the veteran's category list as the general meaning of division (V).**

Verified against codes.ohio.gov on 2026-08-30, and **confirmed three times by
two independent research passes** — twice via the section page and once via the
authenticated PDF (`codes.ohio.gov/assets/laws/revised-code/authenticated/29/
2915/2915.01/9-30-2025/2915.01-9-30-2025.pdf`). All three reads agree.

Division (V) has four limbs and **veteran's organizations and fraternal
organizations get different ones.**

**§2915.01(V)(2) — veteran's organizations** (VFW, American Legion posts and
their auxiliaries). This is where the familiar list actually lives. Net profit
must be:

> "used by the post, chapter, or organization for the charitable purposes set
> forth in division (B)(12) of section 5739.02 of the Revised Code, is used for
> awarding scholarships to or for attendance at an institution mentioned in
> division (B)(12) of section 5739.02 of the Revised Code, is donated to a
> governmental agency, or is used for nonprofit youth activities, the purchase
> of United States or Ohio flags that are donated to schools, youth groups, or
> other bona fide nonprofit organizations, promotion of patriotism, or disaster
> relief"

(V)(2) also carries a **75%-veteran membership test** and a no-private-inurement
condition.

**§2915.01(V)(3) — fraternal organizations** (Elks, Moose, Eagles), quoted in
full:

> "A fraternal organization that has been in continuous existence in this state
> for fifteen years and that uses the net profit exclusively for religious,
> charitable, scientific, literary, or educational purposes, or for the
> prevention of cruelty to children or animals, if contributions for such use
> would qualify as a deductible charitable contribution under subsection 170 of
> the Internal Revenue Code"

**(V)(3) contains none of those words** — no scholarships, no flags, no
patriotism, no disaster relief, no youth activities. Explicitly re-checked
against primary source for this reconciliation.

And it carries a **hard fifteen-years-continuous-existence-in-Ohio
precondition**. A fraternal lodge younger than that does not qualify under this
limb at all. That is a gating fact, not a category.

### Why this matters more than it looks

**The disbursement tag list is not one list.** A VFW post and an Elks lodge, in
the same product, in the same state, tag the same dollar against different
legally-enumerated sets. A single shared `charitable_purpose` enum would be
wrong for one of them — and wrong in the direction that produces a
clean-looking licence renewal report backed by the wrong statute.

This is the SAIRNroofing multi-state lesson recurring on a different axis:
**"Ohio-only" removed the state variable and did not remove the variation.**
Here the axis is organization type, inside a single state.

Same shape as `rf_contingency_rules`: the category set belongs in **a row with
a citation, keyed by organization type**, never a hardcoded array.

**The cross-reference is now closed too.** §5739.02(B)(12), pulled verbatim
during the service-hour research, adds: *relief of poverty; improvement of
health through the alleviation of illness, disease, or injury; operation of an
organization exclusively for the provision of professional, laundry, printing,
and purchasing services to hospitals or charitable institutions; operation of a
home for the aged; operation of a noncommercial educational radio or television
broadcasting station; operation of a nonprofit animal adoption service or county
humane society; promotion of education by an institution of learning…; operation
of a parent-teacher association, booster group, or similar organization…;
operation of a community or area center in which presentations in music,
dramatics, the arts, and related fields are made…; the production of
performances in music, dramatics, and the arts; or the promotion of education by
an organization engaged in carrying on research in, or the dissemination of,
scientific and technological knowledge.*

## CORRECTION 4 — division (V) does not govern instant bingo at all

The opening words of (V), verbatim:

> "'Charitable purpose' means that the net profit of bingo, **other than instant
> bingo or electronic instant bingo**, is used by, or is given, donated, or
> otherwise transferred to, any of the following:"

So the purpose-tagged regime in (V) and the **tiered percentage regime in
§2915.101** (below) are not alternative readings of one rule — they are two
regimes split by game type, and **a post running both traditional and instant
bingo is subject to both simultaneously, on different money.**

**Product consequence:** `game_type` must be on the disbursement record. The
rule a disbursement has to satisfy is determined by the game that produced the
money.

## CORRECTION 5 — the fund-segregation requirement is §2915.10(C), and the relationship runs opposite to the thesis below

This document's profit-chain section concludes that "the bar's books are not
merely adjacent to the bingo books; they are an input to them." That is correct
about (FF)/(GG)(11) — and it is only half the picture, because **§2915.10 was
not read in the first pass.**

**§2915.10(C), verbatim:**

> "The gross profit from each bingo session or game described in division (O)(1)
> or (2) of section 2915.01 of the Revised Code shall be deposited into a
> checking account devoted exclusively to the bingo session or game."

All bingo expenses and net-profit distributions must be made **"only by checks
or electronic fund transfers drawn on the bingo session or game account."**

Three things follow that the app must model exactly:

1. **It is GROSS PROFIT that gets deposited** — receipts *minus prize awards* —
   not gross receipts. Depositing the wrong figure is a records violation even
   when the arithmetic reconciles later.
2. **An exclusive account, and payment only from it.** No cash disbursement
   path. This constrains the nightly canteen close-out design directly.
3. **(GG)(11) then permits canteen operating cost to be paid OUT of that
   segregated account** as an allowable expense. So the correct model is
   **mandatory segregation inbound, enumerated permission for one class of
   expense to cross outbound** — which is exactly why every canteen cost charged
   to bingo needs an auditable tag. Not because the books are merged, but
   because they are legally separated and one specific class is allowed across.

### §2915.10(A) is a schema specification, and it names the canteen

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

- **(B)** Records kept at the principal/headquarters location; **the Attorney
  General must be notified of that location** — so "where the records live" is a
  stored field, not an operational detail.
- **(D)** Annual inventory of bingo supplies, **due by November 1**.
- **(H)** Attorney General and law enforcement may inspect accounts and records.

**(A)(6) and (A)(7) are the canteen↔bingo linkage as a *records obligation*, and
they are the strongest single justification for building the canteen and gaming
modules as one product rather than two.**

**PII WARNING — decide before the table exists.** (A)(3) requires storing winner
**Social Security numbers** for prizes of $600 or more. That is regulated PII
inside a gaming record and needs an explicit encryption, access-role and
retention decision **up front**, not retrofitted. Flagged here so it cannot be
discovered late.

## Additional §2915.09 limits the calendar must ENFORCE

Beyond the 2 a.m.–10 a.m. blackout already recorded above:

- **(C)(4)** No more than **three bingo sessions in any seven-day period**
  (exceptions for volunteer firefighter and rescue organizations).
- **(C)(5)** Maximum prize payout **$6,000 per session**.
- **(C)(7)** Under-18s may not work as bingo game operators.
- **(C)(8)** Persons with felony or gambling convictions may not be operators.
- **(D)(1)** No *"commission, wage, salary, reward, tip, donation, gratuity, or
  other form of compensation"* to bingo game operators.

These are **constraints the booking calendar must refuse to violate**, not
fields it reports after the fact — the same fail-closed posture the SAIRNroofing
rescission engine uses.

**(D)(1) interacts with canteen staffing:** a post that pays a bartender who
also runs the bingo game has a problem the software should be able to see.

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

> **⚠ READ CORRECTION 5 BEFORE MODELLING THIS.** The paragraph above is
> correct about (FF)/(GG)(11) and is **only half the picture** — §2915.10(C)
> requires gross profit to be deposited into an account devoted **exclusively**
> to bingo, with all payments made only from it. The right model is therefore
> **mandatory segregation inbound, with one enumerated expense class permitted
> to cross outbound** — not merged books. Correction 5 appears ~80 lines
> *above* this section and says "the thesis below", so this pointer exists
> because a reader arriving here first would otherwise take the paragraph above
> as the final word.

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

## A third segregation requirement — the Attorney General, not the Revised Code

Surfaced by the competitive scan, absent from both statutory passes. The Ohio
AG states that organizations must maintain **"a separate checking account for
their electronic instant bingo proceeds"**, must file **quarterly reports due
February 28 / May 31 / August 31 / November 30**, and that **"Manufacturers and
distributors of electronic instant bingo systems must obtain an endorsement from
the attorney general's office."**
— charitable.ohioago.gov/Charitable-Bingo/Electronic-Instant-Bingo

That is a **third** segregation requirement, on a **different money type**, with
deadlines nothing in Chapter 2915 itself supplies. It confirms that the AG /
Ohio Administrative Code layer flagged below as unread is load-bearing rather
than a formality.

**Strategic note:** the endorsement requirement is a regulatory moat around
*gaming system distribution* that Arrow already sits inside and this product
does not. Another reason the differentiation should rest on the compliance and
reporting layer rather than anything touching system distribution.

---

# National service-hour reporting — item 8, researched before schema

Full report with citations:
`docs/2026-08-30-sairnfreedom-service-hour-reporting-research.md`. Item 8 was
flagged as the one part of the scope not researched to the standard of the rest,
and therefore the likeliest source of invented compliance fields. Summary:

## The headline: two taxonomies, not one

**National reporting categories and Ohio charitable-gaming categories are NOT
alignable.** National reports measure *what the post did and gave, including its
own program costs.* Chapter 2915 measures *where gaming net profit went.*

The American Legion's Consolidated Post Report carries ~15 explicit "cost to
post for X" fields — `#28` wake/funeral/memorial services, `#104`
administrative costs, `#111` ALR operations, `#116` NEF operations. All are
legitimate CPR line items. **None is a permitted destination under (V)(2).**
Tagging both from one picklist would silently assert compliance the statute does
not support.

**Hours have no place in Chapter 2915 at all.** Volunteer hours are central to
all four national reports and appear nowhere in the charitable-purpose test,
which is about net-profit dollars. **Hours are single-tagged; dollars are
double-tagged.**

## No shared period boundary exists

| Org | Fiscal year | Deadline | Cadence |
|---|---|---|---|
| American Legion | Jun 1 – May 31 | **Jul 1** | annual (CPR, 126 numbered items) |
| VFW | Jul 1 – Jun 30 | **Jun 30** | rolling entry, annual cutoff |
| Elks (national) | Apr 1 – Mar 31 | **before Apr 30** | annual (CLMS2Web) |
| **Elks (Ohio overlay)** | per event | **10th of following month** | **monthly, required of all Ohio lodges** |
| Moose | May 1 – Apr 30 | Feb 15 / May 15 / Aug 15 / Nov 15 | quarterly |
| Eagles | **UNVERIFIED** | — | password wall |

**Reporting periods must be per-organization configuration, never constants.**
Hardcoding any one of these is wrong for three others.

## Unit rules that constrain column types

- **`hours` must be DECIMAL.** VFW mandates `.08` for five minutes. An integer
  column silently truncates to zero.
- **`hours` are cumulative person-hours** — stated identically by VFW (5 comrades
  × 2 hrs = 10) and Ohio Elks (2 Elks × 6 hrs = 12). Store the product; store
  headcount separately.
- **`miles` are round trip × people in the vehicle**, same rule in both sources.
- **Money is two columns, never one** — cash vs non-cash/in-kind. Both Elks and
  the CPR separate them.
- **Elks uniquely splits member/non-member on both hours and miles.** It cannot
  be reconstructed from a blended total, so it must be captured at entry or it
  is lost permanently. It collapses harmlessly to one number for the other four.
- **`counts_toward_national_service` flag.** VFW and Moose both carry explicit
  exclusions — post-benefit work, member-only activities, fundraiser hours, and
  **"working on bingo night"**. Without the flag, totals inflate and the VFW
  Department chairman, who is the sole approving authority, rejects the report.

## Must NOT be hardcoded — verified reasons, not caution

- **Eagles: everything.** foe.com returns a literal password prompt. No form, no
  deadline, no units, no categories. **Build nothing by analogy.**
- **Moose categories.** Two *official* Moose sources — the fillable form and the
  2023 handbook — contradict each other **today** on their own category list.
  This is the strongest single argument against hardcoding any enum in this
  feature.
- **Elks CLMS2 program codes** and **VFW sub-categories** are login-gated. One
  example Elks value was visible (`1001- Youth Scholarship`); one example is not
  a list.
- **CPR item numbers 1–126 as database keys.** They are scoped to a form year
  (2025-26 artwork `#71IA1125`, 2024-25 `71IA1024`). Key on a stable internal
  concept and map item numbers per year.
- **Auto-submit / API integration.** All four are manual member portals; no
  public API found for any. Design for CSV export and human re-entry, and **do
  not promise submission.**

## A collision worth remembering

The Ohio Elks Charity Records Booklet lists **"Bingo"** and **"Charity Poker
Night"** as *reportable charitable activities*. VFW guidance lists *"working on
bingo night"* as explicitly **not** community service. Chapter 2915 treats the
same evening as a *revenue source* for both. **Three different meanings, one
event** — and the software has to hold all three without letting any of them
contaminate the others.

---

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
category as Partender" — **must not be built as a Partender-style slider.**

**DECIDED 2026-08-30: build automatic determination from the start.** No
human-positioned indicator anywhere in the UI. See *Binding decisions* at the
top of this document for the full constraint and the list of specifically
prohibited controls. The alternative — build the slider and take counsel on
US11961032B2 first — was considered and rejected.

Phase 2's passive sensor is a different technology. It was unscanned when this
section was written; it **has since been scanned and DEFERRED** — see the
section immediately below and *Binding decision 3*.

---

# Phase 2 passive sensor — FIRST PASS ONLY

Run 2026-08-30 at Michael's request: an initial read on whether this is worth
real research time, **not** a scan to the standard of the Phase 1 work above.
One claim was read in full. Treat every conclusion here as provisional.

## The on-bottle space is occupied, commercially and by patent

- **Nectar Inc** — **US10078003B2**, priority 2014-06-04, granted 2018-09-18,
  status **"Active — Reinstated, expires 2036-03-22"**, and a family of **8+
  related patents** (US11012764, US10324075, US10670444, US10267667,
  US10591345, US11016072 …) with, per the family listing, "varying claim
  scopes". Modality is **ultrasonic**: the device transmits a pulse and times
  the bounce off the remaining liquid.
- **BarVision LLC** — patented wireless "Smart Spouts" with an onboard IMU,
  processor and radio. Shipping product, not just filings.
- Plus a long tail of older dispensing-control art (US8453878B2 spout sensor,
  US20070228068A1 weighing system, WO1994008887A1 control caps).

## The one distinction that looked promising — and how far it actually goes

US10078003B2 claim 1 **requires the sensor to be a container cover** — a bottle
cap engaging the container opening. It cannot read on a sensor mounted
separately and observing bottles at a distance.

So the shelf-side, touches-nothing approach Phase 2 was aimed at sits **outside
that particular claim**. That is a real distinction and it is the right one to
have found.

**But it is one claim out of a family of eight with varying scope.** "Outside
claim 1 of one member" is not "clear of the family", and it is certainly not
clear of BarVision or the older art. Establishing that would be the real
research, and it has not been done.

## The finding that matters more than the patent question

**Phase 2 may be the wrong shape regardless of how the patents come out.**

1. **The category is commercially served.** Nectar and BarVision are funded
   companies shipping hardware. Phase 2 would not be entering an empty market;
   it would be entering an occupied one with a late, unfunded product.
2. **Hardware is a different business.** Manufacturing, unit economics,
   certification, RMA, field support and firmware updates — none of which this
   platform does today, for any app.
3. **The moat was never the measurement.** The research above states Phase 1's
   differentiator explicitly: not the fill-level reading itself, but "tying
   into the post's event calendar and **bingo-fund compliance data**." That
   differentiator does not require owning the sensor. Nothing in ORC 2915,
   §2915.101's tiered distribution, or the licence-type gating is served
   better by SAIRN manufacturing a depth sensor.

**So the question to answer before spending research time is not "is the
sensor patent-clear" — it is "why build the sensor at all."** An integration
with an existing spout/cap vendor would deliver the same compliance-linked
inventory data with no hardware business and no patent exposure, and the
patent thicket found here is an argument *for* that route rather than an
obstacle to route around.

## The integrate-instead check — RUN 2026-08-30. Answer: no route.

The recommendation above was to check whether Nectar or BarVision expose an
API before doing more patent work. Done. **Neither offers one, and the
economics do not fit the customer either.** That closes both paths, not one.

### BarVision — active, no API, priced past the customer

Site live and current (© 2026). Read directly rather than from search
summaries, because the search result *"connects to over 50 of the top POS
systems"* reads like an integration platform and is not one — that is
**outbound** work BarVision does and sells as a feature, not an inbound
surface a third party can build against.

- **"Ways to Connect"**, the only nav item that sounded like a partner route,
  is **a contact form.** Name, phone, email, note. No API, no developer docs,
  no partner programme anywhere on the site.
- **Pricing: "$250 to $300 a month", 1-year contract, billed quarterly**,
  50–80 spouts typical. That is **$3,000–$3,600 a year**.

That price is the finding. This product's customer is a volunteer-run post
whose own VFW Quartermaster training material advises starting by listing
income and expenses **in one place** — the documented pain is that bills went
to a deceased member's house and nobody could see them. A $3,000-a-year
bar-monitoring subscription is not adjacent to that problem; it is an order of
magnitude past it, and likely past SAIRNfreedom's own plausible price point.

BarVision does list "country club, sports arena, airport lounge" as speciality
venues, so fraternal-club-shaped customers are within their aim — they are
simply aiming at the ones with budget.

### Nectar — cannot confirm the liquor business is still operating

`nectar.buzz` turned out to be **an unrelated company** (commercial
beekeeping software) — recorded so nobody else loses time on it. The liquor
Nectar (Palo Alto, founded 2014, Aayush Phumbhra) has patents active to 2036
and press coverage in 2017 and 2019, but **no current operating status could
be confirmed** in this pass. Live patents plus a cold trail is the worst
combination for an integration partner: the IP is enforceable, the company may
not be there to integrate with.

## Recommendation: defer Phase 2 entirely

Both routes are now closed for different reasons, and neither is a
scheduling problem that waiting fixes:

- **Build** — active patent thicket (Nectar's 8+ family to 2036, BarVision's
  spouts), plus a hardware business this platform has no part of.
- **Integrate** — no API exists at either vendor, and the one with confirmed
  current operation is priced at roughly ten times what this customer is
  likely to pay for the whole product.

**Let Phase 1's automatic photo determination carry the inventory feature.**
It is patent-cleared by design (see *Binding decisions*), needs no hardware,
and already delivers the actual differentiator — fill data tied to the event
calendar and the bingo-fund compliance chain. Phase 2 was always
"zero-touch convenience on top of that", and no evidence found here says the
convenience is worth a hardware business or a $3,000/year dependency.

**Reopen only if** a post asks for it specifically and can fund it, or a
vendor with a real API appears. Neither is worth watching for.

This was a first-pass read, not a freedom-to-operate opinion. Not counsel.

## Sources — patents and vendors

- [US11961032B2 — inventory of containers for beverages](https://patents.google.com/patent/US11961032B2/en)
- [US10078003B2 — Nectar sensor device configuration](https://patents.google.com/patent/US10078003B2/en)
- [US8453878B2 — liquid level measuring device (spout)](https://patents.google.com/patent/US8453878B2)
- [US20070228068A1 — alcoholic beverage management and inventory](https://patents.google.com/patent/US20070228068)
- [BarVision — wireless smart spouts](https://barvision.com/)
- [US20190197466A1 — inventory control for liquid containers (ABANDONED)](https://patents.google.com/patent/US20190197466A1/en)
- [US12450865B2 — detecting liquid level inside a container](https://patents.google.com/patent/US12450865B2/en)
- [EP3992847A1 — a bottle analysis system](https://patents.google.com/patent/EP3992847A1/en)

## Sources — statutes and administrative rules

- [ORC §2915.01 — Definitions](https://codes.ohio.gov/ohio-revised-code/section-2915.01)
- [ORC §2915.09 — Illegally conducting bingo game](https://codes.ohio.gov/ohio-revised-code/section-2915.09)
- [ORC §2915.10 — Bingo records retention](https://codes.ohio.gov/ohio-revised-code/section-2915.10)
- [ORC §2915.101 — Distribution of net profit](https://codes.ohio.gov/ohio-revised-code/section-2915.101)
- [ORC §5739.02 — cross-referenced by §2915.01(V)(2)](https://codes.ohio.gov/ohio-revised-code/section-5739.02)
- [OAC 109:1-4-08 — Bingo license types](https://codes.ohio.gov/ohio-administrative-code/rule-109:1-4-08)
- [Ohio AG — Electronic Instant Bingo](https://charitable.ohioago.gov/Charitable-Bingo/Electronic-Instant-Bingo)

---

# Reconciliation record — two parallel passes, merged 2026-08-30

Two sessions ran the same three pre-build gates the same night without knowing
about each other. Both committed. This section records every difference and how
it was settled, because a silent merge would hide the one place the two
documents disagreed **on a fact**.

## The correction count was 2 vs 4, and neither was wrong about arithmetic

They are **different findings, not a disagreement about how many exist.** Merged
total is five, plus the operational limits.

| Finding | Pass A (this file, originally) | Pass B | Resolution |
|---|---|---|---|
| Session limits are a **definition** at §2915.01(S), not a conduct rule at §2915.09 | **FOUND** | missed | **Kept — Pass A only.** The strongest implementation insight in either document: a "session" running long is not a non-compliant session, it is **not a session**, and every per-session calculation is then keyed to nothing |
| Chapter effective date is imprecise; sections differ | FOUND | FOUND | Agreed. Pass B added §2915.10 and §2915.101 both at 2021-09-30 |
| **(V)(2) vs (V)(3) — category list is per org type** | **STATED INCORRECTLY** | **FOUND** | **Pass B correct. See CORRECTION 3.** This is the one real factual disagreement |
| (V) excludes instant bingo by its own opening words | missed | **FOUND** | Added as CORRECTION 4 |
| Segregation is §2915.10(C); §2915.10 unread in Pass A | missed | **FOUND** | Added as CORRECTION 5 |
| §2915.101 tiered distribution, cumulative-annual threshold | **FOUND, in depth** | found, summarised | **Kept — Pass A's version.** More precise, and the running-total product consequence is Pass A's |
| OAC 109:1-4-08 licence Types I/II/III gate lawful activity | **FOUND** | missed | **Kept — Pass A only** |
| §2915.09 (C)(4) 3-sessions/7-days, (C)(5) $6,000 cap, (D)(1) no operator compensation | missed | **FOUND** | Added |
| §2915.09 (C)(6) blackout, with instant sales from 9 a.m. for a 10 a.m. session | **FOUND**, with the 9 a.m. detail | found, without it | **Kept — Pass A's version** |
| §2915.10(A) record schema, SSN PII, Nov 1 inventory, AG notified of records location | missed | **FOUND** | Added |
| §5739.02(B)(12) cross-reference resolved verbatim | missed | **FOUND** | Added |
| AG electronic-instant-bingo account + quarterly reports | missed | **FOUND** | Added |

**The one real factual disagreement**, resolved by going back to primary source
a third time rather than by preferring a document: this file's own confirmation
table listed *"Charitable purpose enumerates scholarships, flags, patriotism,
disaster relief, youth activities"* as **verified at §2915.01(V)**. Those words
are real, but they sit in **(V)(2)**, which applies only to veteran's
organizations. **(V)(3), which governs Elks, Moose and Eagles, contains none of
them.** Re-checked explicitly against codes.ohio.gov for this reconciliation and
confirmed a third time; the row is struck through above rather than deleted, so
the error stays visible.

Had that row survived into a build, it would have produced **one shared
charitable-purpose enum** — the wrong data model for every fraternal lodge in
the product, failing in the direction that yields a clean-looking licence
renewal report backed by the wrong statute.

## The bottle feature: no disagreement, and the decision stands

Both passes independently found that Partender is manual tap-on-image, not
automatic, and both independently identified the granted claims as requiring a
user-positioned indicator. Pass A took it to a decision with Michael and Cody;
Pass B stopped at "needs counsel."

**Pass A's framing is the one that reflects the actual decision** and is
unchanged at the top of this document: automatic determination from the start,
no user-positioned indicator anywhere. Pass B's caution has been folded in as
**the reasoning behind that decision and a residual-risk flag** — the pending
continuation `US20240320601A1` whose claims can still be amended, and
Partender's own specification already disclosing the automatic method. Neither
reopens the decision. Both argue for the same build path and for getting a real
FTO opinion before the feature reaches sales material.

Pass A additionally cleared **US12450865B2** (Nutricia — claim 1 requires scale
markings, which liquor bottles lack) and flagged the surrounding system claims
5, 6, 9, 14 and 15, which Pass B missed entirely. Those are kept above.

## What this cost, and the lesson

Two sessions, roughly two hours each, on the same three gates. The duplication
was not detected until a rebase pulled three unexpected `docs(sairnfreedom)`
commits into an unrelated push.

It was not a total waste — the parallel passes caught each other's errors, and
the (V)(2)/(V)(3) correction only exists because two people read the same
statute independently. But that is a defence of the outcome, not of the process.

**The process lesson is the one already written in `CLAUDE.md`:** read all four
`SAIRN-ACTIVE-WORK-*.md` files before starting, and the split removes the write
collision, not the need to know what another session is touching. Neither pass
logged "starting SAIRNfreedom gates" anywhere another session would see before
both were already deep in the work.

---

## Two research lessons, and a platform-wide audit that came back clean

> **Consolidated 2026-08-30 into
> `docs/superpowers/specs/2026-08-30-research-method-lessons.md`**, together
> with two further lessons from the same night (a mechanical proxy that ranked
> the best document worst, and the EVV no-credential pattern). That file is the
> single findable place; the detail below stays here because each lesson is
> more useful beside the evidence that produced it.

Both lessons come from this document's own mistakes. The audit checking whether
they recur elsewhere was run 2026-08-30 and is a **negative result** — recorded
because a negative result is what makes the lessons worth generalising rather
than treating as one-offs.

### Lesson 1 — confirming words EXIST is not confirming their SCOPE

The (V)(2)/(V)(3) error above. The verification question asked was *"does (V)
enumerate charitable purposes such as scholarships, flags, patriotism?"* and the
answer was a truthful yes with a real quote. A yes/no question gets a yes. It
establishes the words are present; it establishes nothing about which
subdivision holds them or which organisation types they bind — and here the
product covers two families, so that was the whole question.

**Ask instead:** "quote the division letter, and say who it applies to."

### Lesson 2 — price the integrate option BEFORE recommending build

Phase 2 was scoped as a patent question and hours went into the patent
landscape. The patent answer stayed ambiguous. What actually closed the phase
was one hour of reading two vendor websites: neither exposes an API, and the one
confirmed operating charges $250–300/month on a 1-year contract, roughly ten
times what this customer would pay for the entire product.

Also worth keeping: **read the vendor's own site, not the search summary.**
"Connects to over 50 of the top POS systems" reads like an integration platform
and is outbound work BarVision sells as a feature. The only nav item that
sounded like a partner route was a contact form.

### The audit: SAIRNfreedom was the only instance

Every other in-progress SAIRN research doc was checked for the same
build-vs-integrate viability gap. **None has it**, and several handle it better
than this document did:

| Doc | Verdict |
|---|---|
| `2026-08-27-evv-transmission-groundwork.md` | **Better.** Explicitly names the trading-partner agreement and credentials as unresolved gates, marks the Swagger schema "genuinely gated (401 live)", and found a way to progress regardless — format conformance provable "with no credentials, no agreement" |
| `2026-08-26-competitive-gap-audit-roofing-dental-senior.md` | **Clean.** Explicitly "recommends no build", and flags dental credentialing vendors as "mostly without published pricing" rather than assuming |
| `2026-08-27-sairnmechanical-shared-platform-competitive-research.md` | **Clean.** Incumbent pricing throughout ($179/user, $149, $189, $1,500/yr); the operative spec references it at its line 12 rather than restating it |
| `2026-08-21-plumbing-electrical-hvac-worldwide-research.md` | **Clean.** Proportionally dense on both cost and access |

So this is a lesson from one document, not a pattern across the platform.

### Lesson 1 audited too — the SAIRNsenior series, also clean

The scope failure was separately checked against the ten-document SAIRNsenior
state series (2,450 lines), since it is the same shape: statutory requirements
that bind one provider class and not another. **It does not have the failure**,
and is consistently more careful than this document was:

- **Subdivisions pinned**, not sections: `RCW 74.39A.074(1)(b)`,
  `63 O.S. § 1-1962(C)(1)`, `R.60-77 § 501(B)`.
- **Entity scope stated at the point of the claim** — "a long-term care
  worker"; certification "for home health aides *and* home care agency
  administrators. Both roles, one mechanism."
- **Exemption lists enumerated**, i.e. the "who is NOT bound" question asked
  directly — Washington's registered nurses, pre-2012-01-07 hires, family
  members, ≤20 hours, <300 hours/year.
- **Absence recorded as a finding**, not silence: South Carolina "there is no
  home health aide [standard]", plus a register flagging *"Whether SC sets aide
  qualifications anywhere outside R.60-77 — NOT ESTABLISHED"*, which is exactly
  the scope question left open rather than assumed.

**A correction to the audit's own method, worth more than the result.** The
first pass ranked documents by a subdivision-precision ratio (cites carrying a
subdivision ÷ bare cites). It ranked **round 8 worst** — and round 8 is the
best document in the series. The ratio measured *citation density in prose*,
not scope discipline: a document that cites many sections precisely generates
many "bare" matches too. The finding came from reading, not the metric. A
mechanical proxy for a judgement property will rank confident, well-cited work
badly; use it to choose a reading order and never as the verdict.
