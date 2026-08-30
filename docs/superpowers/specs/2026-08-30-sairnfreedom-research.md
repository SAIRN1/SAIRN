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

## Not verified in this pass, and flagged rather than assumed

- The **gross receipts → gross profit → net profit** calculation chain. The
  baseline describes it and it is very likely §2915.01 definitions plus
  §2915.101 (net profit distribution), but the arithmetic and its required
  reporting form were **not** read this pass. Verify before any figure is
  computed and shown to a post.
- Whether Ohio Administrative Code **109:1-4-\*** (Attorney General bingo
  rules) adds requirements beyond the Revised Code. Search results repeatedly
  surfaced OAC 109:1-4-03/05/08 alongside these sections. Licence *types* and
  record-keeping detail likely sit there, and a compliance product that reads
  only the ORC will be incomplete.
- **Liquor** licensing (ORC 4301/4303 and OAC 4301:1-1-\*) — entirely
  unexamined. The canteen half of the product has its own regulator and this
  research covers only the gaming half.

## Sources

- [ORC §2915.01 — Definitions](https://codes.ohio.gov/ohio-revised-code/section-2915.01)
- [ORC §2915.09 — Illegally conducting bingo game](https://codes.ohio.gov/ohio-revised-code/section-2915.09)
- [ORC §2915.101 — Distribution of net profit](https://codes.ohio.gov/ohio-revised-code/section-2915.101)
- [OAC 109:1-4-08 — Bingo license types](https://codes.ohio.gov/ohio-administrative-code/rule-109:1-4-08)
