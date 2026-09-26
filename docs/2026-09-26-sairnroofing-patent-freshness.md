# SAIRNroofing patent freshness check — 2026-09-26

**Re-verified against current records because the 2026-08-24 and 2026-08-26
screens are a month old and one of their load-bearing claims has since been
undone by the USPTO Director.**

**This is not a clearance and cannot become one.** No opinion here is a legal
opinion. It is a status check on patents the repo already reasons about, plus
one it does not.

**There is no `patents.md` in this repo.** The dispatch names one; the actual
patent material lives in
`docs/superpowers/specs/2026-08-24-sairnroofing-v1-scope.md` §1 (the families
and the design-around) and
`docs/superpowers/specs/2026-08-26-ip-screen-roofing-delta-and-deadline-engine.md`
(the delta screen). Both are annotated to point here rather than rewritten.

---

## 1. Headline

| | | |
|---|---|---|
| **Xactware US 9,501,700** | the patent the design-around is built against | **CONFIRMED ACTIVE to 2032-07-16. The repo was right; nothing changes.** |
| **EagleView US 9,135,737** | **NOT TRACKED ANYWHERE IN THIS REPO** | **The 2024 PTAB invalidation was VACATED by the USPTO Director on 2026-09-24 — two days ago.** |
| **EagleView/Pictometry 9,183,538 and 10,648,800** | §1.2 says PTAB held both "obvious and invalid (July 2024), affirmed on appeal" | Both read **Active** on the public record today. §1.2's framing is no longer safe to rely on — see §4 for why that is not the same as saying it is wrong. |

**The direction of the change is the point.** §1.2 of the 08-24 scope calls
EagleView *"the aggressive enforcer, but weakening"*. On the evidence below
that framing is at best unsupported and at worst backwards, and it is exactly
the kind of sentence that justifies relaxing caution.

---

## 2. Xactware/Verisk — US 9,501,700 — CONFIRMED, no change

Read from the patent's own public record:

> **Status: "Active, expires 2032-07-16"** · Assignee **Xactware Solutions
> Inc** · priority and filing **2012-02-15** · granted **2016-11-22** ·
> adjusted expiration **2032-07-16**

`2026-08-24-sairnroofing-v1-scope.md` §1.1 is headed *"Family A —
Xactware/Verisk, US 9,501,700, active to 2032"*. **That is correct and
re-verified.** The eight-element claim-1 analysis in that section is untouched
by anything in this check, and so is the design-around built against it:
a single inference producing a quantities schedule, with no per-point roof-line
filter, no scan/rotate/scan, and no manipulable geometric model.

**Nothing in this document is a reason to revisit the SAIRNroofing v1 design.**

---

## 3. EagleView US 9,135,737 — the untracked one, and it was just reinstated

> **US 9,135,737** — *"Concurrent display systems and methods for aerial roof
> estimation"* · Assignee **EagleView Technologies Inc** · priority
> **2008-10-31** · granted **2015-09-15** · anticipated expiration
> **2029-05-15** · status **Active**
>
> Post-grant history on the record: **IPR2016-00592** (Final Written Decision),
> **IPR2017-00363** (not instituted), **IPR2022-00734** (Final Written
> Decision) — and **Fed. Cir. 24-2330**.

**USPTO Director John Squires vacated the 2024 PTAB decision that had found
claims of this patent invalid. Decision dated 2026-09-24.** Trade coverage
describes it as throwing out "a two-year-old Patent Trial and Appeal Board
decision that found claims in an EagleView Technologies patent on measuring
roofs to be invalid", with the claims now treated as patentable again.

**This patent appears nowhere in either repo screen.** §1.2 names 9,183,538 and
10,648,800 and nothing else, so a reader working from the repo would not know
this patent exists, let alone that its invalidation was undone this week.

**IT RUNS TO 2029, WHICH IS INSIDE ANY PLANNING HORIZON SAIRNroofing HAS.**

---

## 4. The two the repo DOES name — and the honest limit on what this check proves

`2026-08-24` §1.2 states PTAB held **9,183,538** and **10,648,800** *"obvious
and invalid (July 2024), affirmed on appeal"*. Today:

| patent | assignee on the record | status shown | anticipated expiry |
|---|---|---|---|
| US 9,183,538 | Pictometry International Corp | Active | 2033-02-16 |
| US 10,648,800 | Pictometry International Corp | Active | 2029-05-22 |

**A PUBLIC "ACTIVE" STATUS IS NOT PROOF THE CLAIMS SURVIVED, AND THIS DOCUMENT
DOES NOT CLAIM IT IS.** That field is automated and tracks maintenance-fee and
term events; a PTAB cancellation is not reflected in it until a certificate
issues, which can lag by a long way and does not happen at all while an appeal
is pending. So the correct reading is the narrow one:

- the repo's sentence is **not corroborated** by the public record, and
- neither source settles claim-level validity.

**What follows from that is a stop, not a reversal.** §1.2's conclusion —
"weakening" — was built on those two invalidations. One sibling patent's
invalidation has now been vacated by the Director. That is enough to retire the
framing as a basis for decisions, and not enough to assert the opposite. Anyone
who needs the real answer needs PTAB and Federal Circuit dockets read by
counsel, which is what the 08-26 screen's own opening sentence already says.

---

## 5. What changes, and what does not

**Does not change:**
- The v1 design-around. It is built against 9,501,700's claim 1, which is
  confirmed active and unchanged.
- The 08-26 screen's deadline-engine conclusions (§2). Those are SAIRNlaw
  patents, a different subject, untouched here.
- Anything about whether to build. Nothing here is a clearance.

**Does change:**
- **EagleView's family is not "weakening" on this evidence** and the repo
  should stop saying so.
- **9,135,737 joins the tracked set** and runs to 2029.
- The 08-24 §1.2 sentence now carries a pointer here.

---

## 6. Evidence grade, stated because it decides how this may be used

**Every patent status above was read from that patent's own public record
page** — status line, assignee, priority, grant and expiry — which is a direct
read, not a search snippet. Those are the strongest claims here.

**The Director's vacatur is NOT a direct read.** The Law360 article is
paywalled; what was retrievable is the headline, the patent number
(**9,135,737**) and the decision date (**2026-09-24**), plus a second
independent summary of the same action. **The order itself was not opened.**
Before this is relied on for anything but "go and look", the Director Review
order should be read from the PTAB record.

**Two PDFs could not be read at all** in this pass — that is recorded because
a failed fetch is a failure, not an absence.

---

## 7. Recommended next action, and it is one line

**Have counsel pull the PTAB and Federal Circuit records for 9,135,737
(IPR2022-00734, Fed. Cir. 24-2330), 9,183,538 and 10,648,800.** The repo now
has three EagleView patents whose claim-level status it cannot establish from
public sources, one of which changed two days ago. That is a question for the
same counsel engagement the 08-26 screen already says this needs, not a
research task.
