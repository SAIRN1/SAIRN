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
   § 501(b) the **preceding Friday, 3 July 2026, is a legal holiday**.
   **That is a fifth answer to the 3 July 2026 question** this platform has now
   produced four times: Idaho and Nebraska carry it via Saturday-shift clauses
   inside the sections their rules cite; Hawaii omits it because § 8-2 fell
   outside the reference; New Hampshire omits it because RSA 288:2 is a
   Sunday-only rule with no Saturday limb; **Delaware carries it because
   § 501(b) has an explicit Saturday limb and Rule 6(a) reaches the whole
   statute.** Five jurisdictions, four reasons, one date.

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

## 5. What was NOT determined, and must be before seeding

- **Rule 34 was not located in the extracted text** under the heading searched
  for, so the production-of-documents period is unread. It is almost certainly
  30 days and parallel to Rule 33, and **"almost certainly" is not a citation**.
- **Rule 33's "except that a defendant …" clause was truncated** in the extract
  read here. It is very likely the federal-style carve-out giving a defendant a
  longer period when interrogatories are served early, and that clause changes a
  seeded row from a flat 30 to a `later_of`. **It must be read in full before a
  Rule 33 row is written**, because guessing it flat reports EARLY for a
  defendant and guessing it a floor reports LATE for a plaintiff.
- **The statute fixing the date of the General Election was not read.** Needed
  to date § 501(a)(12) and (a)(13) for 2026.
- **Whether the Court of Chancery has its own computation rule** was not
  checked. Delaware's commercial value is largely Chancery, and Chancery Rule 6
  is a separate rule set from Superior Court Rule 6. A seed labelled `de` that
  silently means "Superior Court only" would be a coverage claim nobody made —
  the domain/label must say which court.

---

## 6. Verdict

**PASS — seed it, with the four disclosures above written into
`JURISDICTION_COVERAGE.de` before any row is loaded**, and with §5's four open
items closed first. Nothing here is a blocker of the Louisiana or Colorado kind:
every unresolved item is either a short additional read or an omission that runs
EARLY.
