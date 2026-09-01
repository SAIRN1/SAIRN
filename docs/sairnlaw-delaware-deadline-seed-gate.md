# Delaware — deadline-seed source-availability gate

**Verdict: PASS. Ready to seed, with three disclosures and one judgment call
that is not mine.** Gated 2026-09-01 (Hank). No rows are seeded by this
document; it is the gate that precedes the seed, in the same shape as every
other state's gate doc in this directory.

**Why Delaware over the eight other never-gated states** (Alaska, Maine,
Montana, North Dakota, Rhode Island, South Dakota, Vermont, Wyoming): it is by
some distance the most commercially significant of them for a B2B legal
customer, and its sources turned out to be the cleanest read of any state gated
so far. That is a judgment about value, stated so it can be disagreed with.

---

## 1. Sources — PASS, and the easiest retrieval yet

| What | Where | Result |
|---|---|---|
| Superior Court Civil Rules | `courts.delaware.gov/forms/download.aspx?id=173418` | **200**, 973,277 bytes, 118 pages, all rules in one authenticated PDF |
| Legal holidays statute, 1 Del. C. ch. 5 | `delcode.delaware.gov/title1/c005/index.html` | **200**, full text of §§ 501-502, marked "Authenticated PDF" available beside it |

**Both returned 200 to a plain browser-header request on the first attempt.**
No 403, no click-through, no login, no CAPTCHA. That is worth recording because
it is the exception: courts.nh.gov, cms.gov's manual downloads and the CMS
coverage database all needed a full browser header set within the last two days,
and Colorado and Tennessee are gated out entirely behind terms acceptance.

**The rules PDF carries per-rule amendment history**, e.g. Rule 6: "Amended,
effective May 11, 1950; Jan. 1, 1965; May 31, 1965; Oct. 15, 1980; Jan. 1, 1991;
Sept. 4, 2014." That is the Hawaii/Idaho/Nebraska/New Mexico position and the
opposite of New Hampshire's, where no effective date is published anywhere and
every one had to come from a 2013 adoption order.

---

## 2. The computation standard — `de_super_ct_civ_r_6a`

Super. Ct. Civ. R. 6(a), verbatim:

> In computing any period of time prescribed or allowed by these Rules, by order
> of court, or by statute, the day of the act, event or default after which the
> designated period of time begins to run shall not be included. The last day of
> the period so computed shall be included, **unless it is a Saturday or Sunday,
> or other legal holiday, or other day on which the office of the Prothonotary
> is closed**, in which event the period shall run until the end of the next day
> on which the office of the Prothonotary is open. **When the period of time
> prescribed or allowed is less than 11 days**, intermediate Saturdays, Sundays,
> and other legal holidays shall be excluded in the computation. As used in this
> rule, "legal holidays" shall be those days **provided by statute or appointed
> by the Governor or the Chief Justice** of the State of Delaware.

**THE RULE NAMES BOTH WEEKEND DAYS ITSELF, so the engine default is correct and
no `weekend_days` declaration is needed.** Checked deliberately, because this
gate was run the same day the per-jurisdiction weekend flag shipped and the
temptation to find a second user for it is exactly how a flag gets misapplied.
Delaware is not one: Rule 6(a) says "a Saturday or Sunday" in its own words and
does not defer the weekend question to the holiday statute the way
La. C.C.P. art. 5059(A) does.

**`short_period_exclusion_days: 11`**, which joins Alabama and Wisconsin. It
matters here and is not decorative: **Rule 59(b)'s new-trial period is 10 days**,
so it falls under the threshold and excludes intermediate weekends and holidays,
where a 3-day-style federal reading would not.

### DISCLOSURE 1 — the Prothonotary-closed limb is not modelled

Rule 6(a) rolls off "**or other day on which the office of the Prothonotary is
closed**", and rolls forward to "the next day on which the office of the
Prothonotary is **open**". This engine has no field for a given county office's
closures and cannot acquire one from a statute.

**Direction: SAFE.** Omitting a closure day returns the earlier, unrolled date;
filing early is safe. This is the identical limb Indiana T.R. 6(A) carries
("days on which the office is closed"), already documented as not modelled in
`indiana_tr_6a`'s own entry, and the same treatment applies. It must be
disclosed in `JURISDICTION_COVERAGE.de`, not left implicit.

### DISCLOSURE 2 — the proclamation limb

"legal holidays" includes days "**appointed by the Governor or the Chief
Justice**". That is open-ended and underivable, the same shape as Idaho Code
§ 73-108 and HRS § 8-1's presidential/gubernatorial limbs. Disclose; do not
attempt to enumerate.

---

## 3. The holiday statute — 1 Del. C. § 501, and it is unlike any seeded so far

> (a) The following days shall be legal holidays in this State: (1) January 1 …
> (2) The third Monday in January, known as Martin Luther King, Jr. Day.
> (3) **Good Friday.** (4) June 19, known as Juneteenth. (5) July 4 … (6) The
> first Monday in September … (7) November 11, known as Veterans Day. (8) The
> fourth Thursday in November … (9) **The Friday following Thanksgiving Day.**
> (10) December 25 … (11) **Saturdays.** (12) **The day of the General Election
> as it biennially occurs**; and (13) **In Sussex County, Return Day, the second
> day after the General Election, after 12:00 Noon.**
>
> (b) If any of the legal holidays fall on Sunday, the Monday following shall be
> a legal holiday. If any of the legal holidays **other than Saturday** fall on
> Saturday, the Friday preceding shall be a legal holiday.
>
> (c) The last Monday in May shall be the legal holiday, known as Memorial Day …

**FOUR THINGS HERE HAVE NO ANALOGUE IN ANY SEEDED STATE.**

1. **SATURDAYS ARE THEMSELVES A STATUTORY LEGAL HOLIDAY** — § 501(a)(11) — and
   **SUNDAY IS NOT IN THE LIST AT ALL.** Sunday appears only in (b), as the day
   a *different* holiday might fall on. This is the exact inverse of Louisiana,
   where Sunday is statewide and Saturday is parish-scoped. **It changes
   nothing for the engine here**, because Rule 6(a) names both days itself, but
   it must be understood before anyone "simplifies" the calendar by deferring
   the weekend question to the statute.

2. **§ 501(b) IS A SHIFT RULE IN BOTH DIRECTIONS, AND IT IS INSIDE THE
   REFERENCE.** Rule 6(a) reaches "those days **provided by statute**", which is
   the whole of § 501 and not a numbered subsection, so (b) is carried — the
   New Hampshire position (RSA ch. 288, a chapter) rather than the Hawaii one
   (HRS § 8-1, a section, which left § 8-2's shift outside). Sunday-falling
   holidays observe Monday; Saturday-falling holidays observe the preceding
   Friday, **except Saturday itself**, which the drafters had to carve out
   precisely because (a)(11) makes every Saturday a holiday.

   **For 2026 this is not dormant.** Juneteenth, 19 June 2026, is a **Friday** —
   no shift. Independence Day, 4 July 2026, is a **Saturday**, so under
   § 501(b) the **preceding Friday, 3 July 2026, is a legal holiday**, and
   Delaware **carries** it because § 501(b) has an explicit Saturday limb and
   Rule 6(a) reaches the whole statute rather than one section of it.

   > **CORRECTED 2026-09-01, same day, before this doc was relied on.** The
   > first version of this paragraph called that "a fifth answer to the 3 July
   > 2026 question … five jurisdictions, four reasons, one date". **That was
   > wrong, and wrong in the direction that overstates novelty.** It generalised
   > a phrase from the New Hampshire commit, which was comparing one deliberately
   > chosen set of four neighbours (ID, NE, HI, NH), into a platform-wide tally
   > nobody had counted. **Counted 2026-09-01 across every seeded 2026 calendar:
   > 19 of 30 CARRY Friday 3 July** — AL, AR, FL, ID, KS, MD, MN, NE, NV, NJ, NM,
   > NC, OK, OR, SC, UT, VA, WA, WV — **and 11 OMIT it** — CA, GA, HI, IL, MA, MS,
   > MO, NH, NY, TX, WI. **Delaware would be the twentieth carrier, not the
   > fifth answer.**
   >
   > **What is actually worth recording is not the count but that the split is
   > real and is decided per state by statutory mechanics, not by consensus.**
   > Two-thirds of seeded states observe the Friday and a third do not, and the
   > reason differs each time: an explicit shift clause inside the cited section
   > (Idaho, Nebraska), a shift clause inside the cited *chapter* (Delaware,
   > Maryland — whose Judiciary publishes 3 July itself), a shift clause that
   > exists but fell **outside** the reference (Hawaii), and no Saturday limb at
   > all (New Hampshire). **A neighbour's answer is never evidence here**, which
   > was the only durable point the original sentence was reaching for.

3. **THE GENERAL ELECTION DAY IS A HOLIDAY AND 2026 IS AN ELECTION YEAR** —
   § 501(a)(12), "the day of the General Election as it biennially occurs".
   **This is the New Hampshire judgment call again, in the same year.** There,
   RSA 288:1 named a "biennial election" that ch. 652 never defines, dating it
   required RSA 653:7, and the day was **omitted** as the EARLY/safe direction
   with the date named for hand-checking.

   **The same call is available here and the analysis is NOT the same**, because
   Delaware's own statute uses the term "General Election" that its election
   code also uses, so the identification is a shorter reach. **Dating it still
   requires a second title that was NOT read during this gate** (see §5). Until
   it is, the New Hampshire treatment is the honest default: omit, disclose,
   name the candidate date, and say a Delaware deadline landing in the first
   week of November 2026 must be checked by hand.

4. **SUSSEX COUNTY RETURN DAY IS A HALF-DAY, COUNTY-SCOPED HOLIDAY** —
   § 501(a)(13), "the second day after the General Election, **after 12:00
   Noon**". Two features this engine cannot express at once: it is scoped to one
   of three counties, and it begins at noon.

   **Direction: SAFE, and for two independent reasons.** Omitting a
   county-scoped extra holiday reports EARLIER — the Massachusetts Suffolk
   County and Alabama Mardi Gras treatment. And a half-day that begins at noon
   is not a day the whole of which is a holiday, so treating it as a full
   rolling day would be wrong in the LATE direction. Omit and disclose.

   **Contrast South Carolina and Louisiana on the half-holiday question**, which
   this platform has now seen answered three ways: S.C. Rule 6(a) says a half
   holiday "shall be considered as other days and not as a holiday";
   La. C.C.P. art. 5059(C) says "a half-holiday is considered a legal holiday";
   Delaware's statute simply creates one and says nothing about how to count it.

---

## 4. Periods available to seed — all quoted from the PDF read

| Rule | Period | Note |
|---|---|---|
| 12(a) | Answer **20 days** after service of process, complaint and affidavit | Carve-outs named in the rule itself for certiorari, ditch returns, mechanics' liens, Rule 3(c) appeals, and attachment/capias actions — a seeded row must say it does not cover those |
| 12(a) | Answer **20 days** after appearance, where the defendant appears before service | A second, distinct trigger on the same rule |
| 33 | Interrogatory answers/objections **30 days** after service | The rule text continues "except that a defendant …", which was NOT fully read — see §5 |
| 36 | Admissions **30 days** after service | **Self-executing: "The matter is admitted unless, within 30 days …"** — the New Hampshire shape, not the Mississippi/New Mexico/South Carolina `later_of` floor |
| 59(b) | New trial **10 days** after entry of judgment or rendition of the verdict | **Under the 11-day threshold**, so intermediate weekends and holidays are excluded |
| 59(b) | Opposing party's response **10 days** after service of the motion | Also under the threshold |
| 6(e) | **+3 days** when service is by mail | "The additional 3-day period applies only to actions taken by parties and **does not apply to actions taken by the Court**" |

**Rule 6(e) IS NOT AN EXCLUSIVITY RULE.** Checked against the Utah/Florida shape
deliberately: it says "service is by mail", with no "only", "exclusively" or
equivalent. So it needs no `requires_exclusive` and takes the plain federal
shape. It is also **mail-only** — no electronic or consented-means limb — so
`applies_when` is a single method.

---

## 5. The four open items — ALL FOUR CLOSED 2026-09-01, same day

Each was named in the first version of this document as unread. Each has now
been read from the primary source, and two of them changed the answer.

### 5.1 Rule 34 — READ. Same shape as Rule 33, and both are ELECTIONS

> **Rule 34(b).** The party upon whom the request is served shall serve a
> written response **within 30 days after the service of the request, except
> that a defendant may serve a response within 45 days after** service of the
> summons and complaint upon that defendant.

> **Rule 33(a).** The party upon whom the interrogatories have been served shall
> serve a copy of the answers, and objections if any, **within 30 days after the
> service of the interrogatories, except that a defendant may serve answers or
> objections within 45 days after service of the summons and complaint** upon
> that defendant.

**THE WORD IS "MAY", AND ON THIS PLATFORM THAT DECIDES THE SHAPE.** Mississippi,
New Mexico, South Carolina and Hawai'i make Rule 36 a floor because their text
is *"shall not be required to serve ... before the expiration of"* 45 days.
Delaware says a defendant **may** serve within 45 days of a different trigger —
an ELECTION between two limbs with two different triggers, which is Hawai'i's
own 33/34 shape, **not** a `later_of` floor. Nebraska is the warning in the other
direction: its rule says "may" **and** "whichever is longer" in one sentence, so
the comparative governs there and the same word produces a floor. **The word
alone never settles it; the sentence does.**

### 5.2 Rule 36 — READ, and it does NOT carry the carve-out

> **Rule 36(a).** The matter is admitted unless, **within 30 days after service
> of the request**, or within such shorter or longer time as the Court may
> allow, the party to whom the request is directed serves ... a written answer or
> objection ...

**Rules 33 and 34 give a defendant the 45-day election and Rule 36 does not.**
Verified by reading all three, not inferred from the pair. So the admissions row
is a **flat thirty and self-executing** — the New Hampshire shape — and copying
33's election onto it would tell a Delaware defendant a matter is still open
when it has already been admitted.

### 5.3 The General Election date — READ, and it is CONSTITUTIONAL, not statutory

> **Del. Const. art. V, § 1.** The general election shall be held **biennially on
> the Tuesday next after the first Monday in the month of November**, and shall
> be by ballot ...

**THIS INVERTS THE NEW HAMPSHIRE CALL RATHER THAN REPEATING IT.** There,
RSA 288:1 named a *"biennial election"* that ch. 652 never defines, dating it
needed RSA 653:7 which uses a *different term*, and the day was omitted as the
EARLY/safe direction. **Delaware has no definitional gap:** 1 Del. C.
§ 501(a)(12) says *"the day of the General Election as it biennially occurs"* and
the Constitution fixes *"the general election ... biennially"* on a named day.
Same term, constitutional source, one reference.

**For 2026 that is Tuesday 3 November 2026** — the first Monday in November 2026
is Monday the 2nd, verified by weekday, and the Tuesday next after it is the 3rd.
**It should be CARRIED, not omitted**, and the reason is that the identification
is a citation rather than a reading. Sussex Return Day is then **Thursday 5
November 2026**, and stays omitted for the separate reasons in §3.4.

### 5.4 Chancery — READ, and it is a GENUINELY DIFFERENT COMPUTATION

Ct. Ch. R. 6 was downloaded and read (231-page authenticated PDF, HTTP 200,
same clean retrieval as the Superior Court set). **It is not a copy of Superior
Court Rule 6, and the differences are not cosmetic:**

| | Superior Court R. 6(a) | Ct. Ch. R. 6 |
|---|---|---|
| Last-day rollover | off Saturday/Sunday/legal holiday **or any day the Prothonotary's office is closed**, forward to the next day it is **open** | off Saturday/Sunday/legal holiday only, with **Register in Chancery inaccessibility as a SEPARATE additional limb** (6(a)(3)) |
| "Legal holiday" | days "provided by statute **or appointed by the Governor or the Chief Justice**" | "declared a holiday by the **Governor** ... or identified in **1 Del. C. § 501**" — **no Chief Justice limb** |
| Backward periods | not addressed | **6(a)(4) addresses them expressly** — count backward when the period is measured before an event |
| Hours | none | **6(a)(2)**, a full hours unit with its own rollover |
| Short-period exclusion | less than 11 days | less than 11 days — **the one place they agree** |

**THE ROLLOVER DIFFERENCE IS THE DECISIVE ONE and it is the Wisconsin question
in miniature.** Superior Court's closure limb REPLACES the holiday test inside
the same sentence — the shape that made Wisconsin dangerous. Chancery's
inaccessibility limb is ADDITIONAL to an ordinary holiday rollover — the
Minnesota and Utah shape, where omitting it can only report EARLY.

**SCOPING DECISION, MINE, STATED SO IT CAN BE OVERRULED: seed SUPERIOR COURT
ONLY as jurisdiction `de`, and say so in the label, the coverage entry and every
row's note.** Every period in §4 is a Superior Court rule; Chancery has its own
Rules 12, 33, 34 and 36 that were NOT read here. **A `de` seed that silently
spanned both courts would be a coverage claim nobody made** — and it would be
wrong in a specific way, since a Chancery deadline computed on the Prothonotary
closure basis is computed under the wrong rule. Chancery is its own gate, its own
standard (`de_ct_ch_r_6`) and its own seed, and is not started here.

---

## 6. Verdict

**PASS — seed Superior Court, with the disclosures in §2 and §3 written into
`JURISDICTION_COVERAGE.de` before any row is loaded.** All four items formerly
in this section are closed above. Nothing here is a blocker of the Louisiana or
Colorado kind: every remaining omission runs EARLY, and the two items that
changed on a second read — the 33/34 election shape and the election-day date —
both moved toward MORE coverage rather than less.
