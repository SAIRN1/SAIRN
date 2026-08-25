# Massachusetts — deadline-seed source-availability gate

**Run 2026-08-25. Verdict: PASS, with one structural finding that must be
settled before any row is written.**

The gate exists because Kentucky did not have one: confirm the primary sources
are readable and permitted BEFORE investing in a jurisdiction. Massachusetts
clears the availability bar that blocked Kentucky and gated Arizona. It raises a
different problem those two did not — a **county-scoped holiday list** — and
that is a schema question, not a source question.

---

## 1. Are the primary sources published free and in full? — YES

The complete Massachusetts Rules of Civil Procedure are published by the
**Trial Court Law Libraries, Massachusetts Court System**, on `mass.gov`.
Index page states `DATE PUBLISHED: July 1, 1974`, `LAST UPDATED: March 5, 2025`.

**No Westlaw, Lexis or Thomson Reuters redirect anywhere in the path.** That is
the decisive difference from Kentucky (`kycourts.gov` → `govt.westlaw.com`, no
free base text at all) and from Arizona (`azcourts.gov` → `azrules.westgroup.com`
→ `govt.westlaw.com` for the *maintained* text). Massachusetts publishes the
maintained text itself.

Rules read verbatim during this gate: **6, 12, 33, 34, 36** — all reachable,
all complete.

## 2. Access method — mass.gov 403s every automated fetch

`curl` with a real browser User-Agent, and `WebFetch`, both return **HTTP 403**
on every `mass.gov` URL tried, including `/doc/.../download` PDF links:

```
https://www.mass.gov/rules-of-civil-procedure/civil-procedure-rule-6-time   403
https://www.mass.gov/law-library/massachusetts-rules-of-civil-procedure     403
https://www.mass.gov/doc/amendments-to-rules-5-and-6-.../download           403
```

A real browser succeeds — **Playwright/Chromium returned HTTP 200 and the full
text on every one of them.** This is an access-method problem, not an
availability or permission problem, and it is **the same shape as North
Carolina**, whose `nccourts.gov/holiday-schedule` is JS-rendered and 403s to
plain fetches; NC passed its gate and was seeded on that basis.

The statute site is unaffected: `malegislature.gov` returns **200** to plain
`curl`.

**Consequence for the seed:** every Massachusetts source read must go through a
real browser. Do not conclude a page is missing from a 403.

## 3. Per-rule currency — REAL, like Virginia, unlike New Jersey

Every rule page prints its own `EFFECTIVE DATE` and an `UPDATES` amendment
history. Confirmed by direct read:

| Rule | Effective date printed | Subject |
|---|---|---|
| 6  | `12/01/2023` | Time (amended Nov 2 2023; earlier amendment eff. 2021-09-01, 488 Mass. 1401) |
| 12 | `07/01/2008` | Defenses and objections — the answer period |
| 33 | `08/01/2009` | Interrogatories to parties |
| 34 | `08/01/2016` | Producing documents |
| 36 | `07/01/1974` | Requests for admission |

So `effective_from` is real per row, as in Virginia — **not** the blanket
`1969-09-08` New Jersey and North Carolina both carry and disclose.

## 4. THE STRUCTURAL FINDING — legal holidays are COUNTY-SCOPED

Mass. R. Civ. P. 6(a) makes an **express cross-reference**, which resolves the
bundled "which holidays actually count" question in its own text — the same
good shape as Washington's CR 6(a) → RCW 1.16.050, and the opposite of Texas,
Arizona and Kentucky, which name no statute:

> As used in this rule and in Rule 77(c), "legal holiday" includes those days
> specified in **Mass. G.L. c. 4, § 7** and any other day appointed as a holiday
> by the President or the Congress of the United States or designated by the
> laws of the Commonwealth.

**G.L. c. 4, § 7, Clause Eighteenth**, read verbatim on `malegislature.gov`:

> "Legal holiday" shall include January first, June nineteenth, July fourth,
> November eleventh, and Christmas Day, **or the day following when any of said
> days occurs on Sunday**, and the third Monday in January, the third Monday in
> February, the third Monday in April, the last Monday in May, the first Monday
> in September, the second Monday in October, and Thanksgiving Day.

and then, in the same clause:

> "Legal holiday" shall also include, **with respect to Suffolk county only**,
> Evacuation Day, on March seventeenth, and Bunker Hill Day, on June
> seventeenth, or the day following when said days occur on Sunday

**Two legal holidays exist in one county and nowhere else in the
Commonwealth.** `holidayFor()` keys a calendar by **jurisdiction + year only**,
so one `ma` calendar cannot express this. It is a geographic split *within* a
state — related to, but not the same as, West Virginia's split, which is by
**body of rules** (civil 6(a)(6) vs appellate 39(a)) rather than by place.

### Which way to encode it, and why

| Encode | Suffolk County result | Everywhere else | Direction |
|---|---|---|---|
| Statewide list only (no Evacuation/Bunker Hill) | deadline computes **EARLY** on those two days | correct | **safe** |
| Suffolk list for all `ma` | correct in Suffolk | every other county rolls **LATE** | **dangerous** |

**Encode the statewide list and disclose the Suffolk gap**, exactly as Virginia
discloses its § 1-210(F) gap and for the identical reason: the omission can only
ever report a date EARLIER than the true deadline, never later. A `JURISDICTION_
COVERAGE` entry already exists for this purpose and Massachusetts should get one.

**Flag this prominently rather than burying it: Suffolk County is Boston**, the
largest legal market in the Commonwealth. This is not a rare edge case — it is
the most-used venue in the state, and the disclosure text must say so plainly.

### A second, smaller gap in the same sentence

Rule 6(a)'s "**any other day appointed as a holiday by the President or the
Congress of the United States or designated by the laws of the Commonwealth**"
is open-ended and ad hoc, so it is not knowable in advance. Same shape as Va.
Code § 1-210(F), same direction (EARLY), same treatment — fold into the same
coverage disclosure rather than refusing.

### The weekend shift is ONE-WAY, and that is unusual here

Clause Eighteenth shifts a holiday **only when it falls on Sunday** ("or the day
following when any of said days occurs on Sunday"). It says **nothing about
Saturday**. Virginia and West Virginia both shift *both* ways (Saturday → the
preceding Friday). A generator carried across from either would invent a Friday
holiday Massachusetts does not have — and that error runs **LATE**. Do not carry
the shift function across; write it from this clause.

## 5. Banked substantive findings — read verbatim, reusable whether or not MA is seeded next

- **Rule 6(a) short-period exclusion is "less than 7 days"** — matching New
  Jersey, North Carolina, Washington and West Virginia's appellate rule, and
  *not* Arizona's eleven. Read, not inferred.
- **Rule 6(d) adds THREE days for MAIL *and* for ELECTRONIC service**, verbatim:
  "served upon the party by mail, by e-mail pursuant to Rule 5(b)(1), or
  otherwise electronically, including through the Electronic Filing Service
  Provider pursuant to Rule 7(b) of the Massachusetts Rules of Electronic
  Filing, three (3) days shall be added to the prescribed period." **This is the
  opposite of FRCP 6(d)**, which stopped extending for electronic service in
  2016, and it matches Kentucky's eFiling Rules 13(6). A standard copied from
  the federal shape would be wrong here.
- **"Shall be added to the prescribed period"** — period-lengthening, one
  rollover at the end (`add_to_period_then_roll`), like NJ/NC/WA/NY/VA, **not**
  the federal after-expiry order.
- **Rule 12(a)(1): the answer period is TWENTY days** — shorter than every state
  seeded so far except Washington's 20 (federal 21, VA 21, NC/WV/GA 30, NJ 35).
- **Rule 12(a)(2) is a real re-trigger, not an extension**: on denial of a Rule
  12 motion the responsive pleading is due "within **10 days** after notice of
  the court's action"; on a granted motion for a more definite statement,
  "within 10 days after the service of the more definite statement." Note it
  runs from **notice of the court's action**, not from entry — different from
  Virginia's R. 3:8(b), which runs from entry. Same two-limb shape New Jersey's
  R. 4:6-1(b) has.
- **Rule 36(a): 30 days, and silence ADMITS** — "The matter is admitted unless,
  within 30 days after service of the request..." with a defendant floor
  ("unless the court shortens the time, a defendant shall not be required to
  serve..."), i.e. the same `resolve_periods` later-of shape as Ohio, Georgia,
  NJ, NC, WA and VA. The defendant floor's day count still needs reading.
- **Rule 33 and Rule 34 both show 30- and 45-day counts** in their text; each
  needs its own verbatim read before seeding — not inferred from the pair.

## 6. What is NOT yet done

This is a **gate**, not a seed. Not yet done, and required before any row:

- Verbatim read of Rule 33's and Rule 34's full periods, including which count
  attaches to which limb and the defendant floor in Rule 36.
- Whether a **court holiday schedule** exists separately from the statute (the
  NC lesson: a rule keying on *courthouse closure* makes the statute the wrong
  source). Rule 6(a) here cross-references the statute expressly, so the statute
  is very likely correct — but Rule 77(c), which the same sentence names, has
  not been read.
- The Rule 12(a)(2) re-trigger's interaction with `applyRetrigger`.
- A decision on the Suffolk County disclosure text.

## 7. Verdict

**PASS.** Sources are free, complete, official, permitted, and carry real
per-rule currency. Access requires a real browser, which is a known and already-
solved condition on this platform. The county-scoped holiday list is a genuine
structural finding but has a safe, already-established resolution (encode
statewide, disclose the Suffolk gap in the EARLY direction), so it is a design
decision to record — not a blocker.

Compare: **Kentucky** failed the gate on source availability *and* on a holiday
basis that fails LATE. **Arizona** failed on an unprovable-completeness
reconstruction. **Massachusetts fails neither.**
