# Iowa — deadline-seed source-availability gate

**Run 2026-08-27. Verdict: GATED — DO NOT SEED. Sources are official and free,
but TWO things block, and both fail LATE. (1) Iowa's weekend rollover is SPLIT
BY WHAT KIND OF DEADLINE IT IS: the general rule rolls only Sunday, and the
Saturday-and-holidays rule is scoped to commencement, filings and appeals —
while Iowa's answer and discovery deadlines are expressly SERVICE deadlines.
(2) The publisher's dated URLs are INERT: every snapshot date from 01-01-2024
to 07-01-2026 returns the identical file, stamped July 2023.**

Iowa (~3.2M), the largest state with neither a seed nor a gate document after
Utah. Rules of court are the **Iowa Rules of Civil Procedure**, chapter 1 of the
Iowa Court Rules, prescribed by the Iowa Supreme Court.

---

## 1. Sources — authority PASSES, access PASSES, CURRENCY DOES NOT

```
legis.iowa.gov/docs/ACO/CourtRulesChapter/1.pdf   200, 6,767,921 B, 130pp, real text
legis.iowa.gov/docs/code/4.1.pdf                  200, 60,725 B, real text
```

Both free, both on a bare `curl`, both real text PDFs rather than scans. The
publisher chain is stated outright on `legis.iowa.gov/law/courtRules`:

> Iowa Court Rules — Rules of procedure … **as prescribed by the Iowa Supreme
> Court and published by the Legislative Service Agency (Official Version - PDF
> format).**

So the Legislative Service Agency is the official publisher of the court's own
rules, and `legis.iowa.gov` is the right place to read them. **The statute is
current on its face** — `4.1.pdf` carries `Code 2026` internally.

### TRAP — THE DATED URL IS INERT, AND IT LOOKS AUTHORITATIVE

The chapter is served under a date-stamped path,
`CourtRulesChapter/01-01-2026.1.pdf`, which reads exactly like a version
selector. **It is not one.** Every date probed returns a byte-identical file:

| requested snapshot | result |
|---|---|
| `01-01-2024.1.pdf` | 200, **6,767,921 B** |
| `01-01-2025.1.pdf` | 200, **6,767,921 B** |
| `07-01-2025.1.pdf` | 200, **6,767,921 B** |
| `01-01-2026.1.pdf` | 200, **6,767,921 B** |
| **`07-01-2026.1.pdf`** (a future date) | 200, **6,767,921 B** |
| `1.pdf` (undated) | 200, **6,767,921 B** |

**A future date returns content, and every date returns the same bytes.** The
date in the path carries no information at all. Reading `01-01-2026` as evidence
of 2026 currency is the mistake this section exists to prevent.

**What the file actually says about itself:** every one of its 61 page footers
is stamped **`July 2023`**, and the newest amendment anywhere in it is 2023 —
the `[Report …]` lines span 2000–2023 with exactly one rule carrying a 2023
effective date.

**Two readings, and this gate cannot choose between them:** either chapter 1
genuinely has not been amended since July 2023 and the stamp is honest, or the
published snapshot is stale. `iowacourts.gov` 404s on both rules paths tried, so
no independent cross-check was obtained. **This is the currency blocker, and it
is unresolved — not resolved-in-favour.**

Compare the two traps found the same day in Utah: a hostname reading `legacy`
that was in fact current, and a 200 carrying an error-page body. **Iowa's is the
third shape: a URL that encodes a date it does not honour.**

## 2. THE STRUCTURAL FINDING — the rules contain NO counting mechanics at all

**Iowa R. Civ. P. 1.1801, "Computing time; holidays"**, verbatim and complete —
this is the whole rule:

> In computing time under these rules, the provisions of **Iowa Code section
> 4.1, subsection 34, shall govern.**
> [Report 1943; amendment 1967; November 9, 2001, effective February 15, 2002]

**One sentence, and it is a pointer.** Measured on the flattened 130-page
chapter: `first day` **0 hits**, `legal holiday` **0 hits**, `Sunday` **0 hits**.
The three `Saturday` hits are a juror's religious observance (Rule 1.916) and
table-of-contents entries. There is no first-day/last-day rule, no rollover
clause and no holiday list anywhere in the Iowa Rules of Civil Procedure.

Every mechanic therefore lives in **Iowa Code § 4.1(34)**, and the whole
weekend-coverage question has to be answered there. This is Connecticut's shape
inverted: Connecticut's Practice Book had counting but no holiday basis; Iowa's
rules have neither, by design, and delegate both.

## 3. THE BLOCKER — § 4.1(34) IS TWO RULES, AND WHICH ONE APPLIES DEPENDS ON WHAT YOU ARE FILING

**Iowa Code § 4.1(34), "Time — legal holidays"**, verbatim:

> In computing time, the first day shall be excluded and the last included,
> **unless the last falls on Sunday**, in which case the time prescribed shall
> be extended so as to include the whole of the following Monday. **However,
> when** by the provisions of a statute or rule prescribed under authority of a
> statute, the last day for **the commencement of an action or proceedings, the
> filing of a pleading or motion in a pending action or proceedings, or the
> perfecting or filing of an appeal** from the decision or award of a court,
> board, commission, or official falls on **a Saturday, a Sunday, a day on which
> the office of the clerk of the district court is closed in whole or in part
> pursuant to the authority of the supreme court**, the first day of January,
> the third Monday in January, **the twelfth day of February**, the third Monday
> in February, the last Monday in May, the fourth day of July, the first Monday
> in September, the eleventh day of November, the fourth Thursday in November,
> the twenty-fifth day of December, **and the following Monday when any of the
> foregoing named legal holidays fall on a Sunday**, and any day appointed or
> recommended by the governor of Iowa or the president of the United States as a
> day of fasting or thanksgiving, the time shall be extended to include **the
> next day which the office of the clerk of the court … is open to receive the
> filing**.

**Sentence one rolls ONLY SUNDAY.** Saturday is not mentioned. On its own that
is the Louisiana failure exactly.

**Sentence two rolls Saturday, Sunday, clerk-closure days and eleven named
holidays — but ONLY for three kinds of deadline:** commencement of an action,
**the FILING of a pleading or motion** in a pending action, and appeals.

### Why that scoping is the blocker and not a footnote

**Iowa's own deadlines are written as SERVICE deadlines, expressly.**

- **Rule 1.303(1)**: *"the defendant … shall **serve**, and within a reasonable
  time thereafter file, a motion or answer **within 20 days** after the service
  of the original notice and petition."* The twenty-day clock runs on
  **serving**; filing merely has to follow "within a reasonable time".
- **Rule 1.509**: *"**Answers shall not be filed**; however, they shall be
  **served** upon all adverse parties within 30 days after the interrogatories
  are served."* This one forecloses the question — the rule says outright that
  the document is not filed at all.
- **Rule 1.512(1)**: *"shall **serve** a written response within 30 days after
  the service of the request."*

A deadline to **serve** an answer is not the commencement of an action, is not
the **filing** of a pleading or motion, and is not an appeal. **On the words,
sentence two does not reach Iowa's answer deadline or any of its discovery
deadlines** — which would leave them under sentence one, rolling on Sunday only.

**THE DIRECTION OF ERROR IS LATE.** If this engine rolls a Saturday-landing
answer deadline forward to Monday and sentence one in fact governs, the reported
date is **two days after** the real one. That loses a filing. Rolling only
Sunday when sentence two does govern would be **EARLY** — safe — but the engine
cannot pick per rule today.

**A court would very likely read the statute purposively** and apply sentence
two to a served answer; the twenty-day period is prescribed "by … rule
prescribed under authority of a statute", and treating served and filed papers
differently for weekend purposes would be odd. **That is a legal judgment, not
an arithmetic one, and this gate does not make it.**

### It also breaks the engine change already queued for Louisiana

The open-work index already carries a prioritised engine change: **a
per-JURISDICTION weekend-rollover flag**, raised because `isWeekend()` rolls both
days unconditionally and Louisiana is the first state where that is
affirmatively wrong. **A per-jurisdiction flag is not enough for Iowa.** Iowa
needs the rollover to differ **per RULE** within one jurisdiction — filings roll
Saturday, served papers may not. Whoever builds that flag should read this
section first, because the data shape chosen there decides whether Iowa is
seedable at all.

## 4. The holiday list — derivable, with one day nobody else has

Sentence two names its own days, so Iowa is **derive, not ingest**, like Utah:
1 January; third Monday in January; **12 February**; third Monday in February;
last Monday in May; 4 July; first Monday in September; 11 November; fourth
Thursday in November; 25 December; plus governor's or president's fasting-or-
thanksgiving days.

- **12 FEBRUARY — LINCOLN'S BIRTHDAY — IS A SEPARATE LEGAL HOLIDAY**, listed
  alongside the third Monday in February. No seeded jurisdiction has it. It is a
  **fixed date that usually lands on a weekday**, so missing it is a real
  one-day error (EARLY, safe, but real).
- **The observation shift is SUNDAY-ONLY**: *"the following Monday when any of
  the foregoing named legal holidays fall on a Sunday."* **There is no
  Saturday→Friday limb**, unlike Utah's both-ways shift — and none is needed
  inside sentence two, because Saturday is independently a roll-off day there.
  **But under sentence one it matters a great deal**, which is the §3 problem
  again.
- **The clerk-closure limb is ADDITIONAL to the named list, not a replacement
  for it** — Minnesota's 6.01(a)(4) shape, **not** Wisconsin's. Omitting it can
  only report EARLY. **"Closed in whole or IN PART"** is unusually broad and is
  not derivable from any list.
- **The roll TARGET is defined by openness**, not by not-a-holiday: *"the next
  day which the office of the clerk … is open to receive the filing."* With the
  named list plus weekends that is computable in the ordinary case, but the
  closure schedule is the true artifact.

## 5. The service extension — +3, and it reaches E-MAIL

**Rule 1.443(2)**, verbatim:

> When by the rules in this chapter a party has the right or is required to do
> some act within a prescribed period after the service of a notice or other
> paper upon the party and the notice or paper is served upon the party **by
> mail, e-mail, or facsimile transmission, three days shall be added** to the
> prescribed period. Such additional time **shall not be applicable where a
> court has prescribed the method of service of notice and the number of days to
> be given or where the deadline runs from entry or filing of a judgment, order
> or decree.**

**Three days, and the method list INCLUDES E-MAIL** — most seeded jurisdictions
exclude electronic service from the extension, so an allowlist copied from a
neighbour would under-count here. Straightforward `applies_when`, with **no
exclusivity condition** — so Iowa does **not** hit the problem that held Utah's
mail row.

**Two carve-outs, and the second is mechanical rather than discretionary:** the
extension does not apply where the deadline **runs from entry or filing of a
judgment, order or decree**. That is knowable from the trigger, so it must be
encoded as an absence on those rows rather than as a runtime condition. The
first carve-out (a court has prescribed the method and the day count) is a
court-order override the engine cannot see.

## 6. What else is seedable once the blockers clear

- **Rule 1.303(1)** — **20 days** to serve a motion or answer after service of
  the **original notice and petition**. The shortest answer period of any
  jurisdiction gated so far, and Iowa-specific terminology worth naming
  precisely in the trigger.
- **Rule 1.303(4)** — service by publication: on or before the date fixed in the
  published notice, *"which date shall not be less than 20 days after the date
  of last publication."* A **floor on a party-chosen date** — the
  `designated_period` shape already built for Ohio and Indiana.
- **Rule 1.509** — 30 days (interrogatories). **Rule 1.512(1)** — 30 days
  (production).
- **Rule 1.510** — requests for admission, and it carries **a chained defendant
  floor**: *"unless the court shortens the time, a defendant shall not be
  required to serve answers or objections before the expiration of **60 days
  after service of the original notice** upon defendant."* That is a
  later-of-two-periods with **different counts per limb** — precisely the
  `resolve_periods` shape built after Georgia's fifteen-day error. Iowa would be
  its second real user.
- **Rule 1.444** — pleading over: further pleading within **ten days** after the
  clerk mails or delivers notice of the order or ruling.

## 7. What was NOT determined

- **Whether § 4.1(34) sentence two reaches a SERVED answer or discovery
  response.** The blocker. Legal judgment, late-direction.
- **Whether chapter 1 has been amended since July 2023.** The currency blocker.
  `iowacourts.gov` 404s were not chased to a working path.
- **Iowa Code § 1C.1** (state holidays) was fetched but **not read**, and
  nothing in § 4.1(34) points at it — sentence two carries its own list. Worth
  a look only to see whether it conflicts.
- Rules 1.302 and 1.305–1.315 (original notice and how service completes), so
  what date a caller supplies for the Rule 1.303 trigger is not yet sourced.
- Appellate rules (a separate chapter) were not opened.

## 8. Verdict

**GATED. Do not seed.** Nothing here is an access or authority problem — the
Legislative Service Agency publishes the Supreme Court's rules free, officially,
and on a bare `curl`, and the statute is current on its face.

**Two blockers, both LATE-direction:**

1. **The rollover scope split in § 4.1(34).** Sentence one rolls Sunday only;
   sentence two rolls Saturday and the holidays but is scoped to commencement,
   **filings** and appeals — and Iowa's answer and discovery deadlines are
   written as **service** deadlines, one of them saying outright that the
   document "shall not be filed". Guessing wrong rolls a Saturday deadline two
   days late. **This also means the queued per-jurisdiction weekend-rollover
   flag will not cover Iowa; it needs per-rule.**
2. **Currency cannot be established from the publisher's own artifacts**, because
   the dated URLs are inert and the file stamps July 2023.

Resolve (1) before writing a single row — it is the kind of question that
decides whether the jurisdiction is modellable at all, not a disclosure. (2) is
a smaller problem and probably answerable with one working `iowacourts.gov`
path or a Supreme Court rule-order feed.
