# SAIRN handoff — hank b66 — 2026-10-29

**Subject:**
- VT from the official index;
- DC (J6);
- S2;
- `merge=union` on BYPASS-LOG (C1b);
- J4 stated verbatim;
- the hook-presence re-check.

This handoff was written before the report.

## 1. Hook presence — RE-VERIFIED before touching BYPASS-LOG
`python tools/builder_hook_presence.py` exited 0: cody OK, fourth OK, hank OK. cloud is not on this machine. This ran
before `.gitattributes` and the ledger were touched.

## 2. C1b — `merge=union` on `docs/BYPASS-LOG.jsonl` (`2f2aac896`)
- **Proof before adoption** (`git merge-file`, two appended rows): a plain merge gives exit 1 with 1 conflict marker;
  `--union` gives exit 0, 0 markers and 3 rows.
- **Also added `eol=lf`.** The `.jsonl` file had no rule and warned on every touch.
- **Verified:** `git check-attr` reports `merge: union, eol: lf`.
- **Stated limit:** union is safe ONLY because the file is append-only. An edit to an existing row would be duplicated,
  not merged. `push_retry.append_only()` guards this clone's writes.

## 3. S2 — `tools/server_stale_snapshot_scan.py` (`cf29ca94d`)
- **What it finds:** per async function, a DB read parsed with `.json()`, then an `await` AFTER the parse, then a
  PATCH/PUT/POST with no concurrency guard. The guards it accepts are If-Match, `version=`/`updated_at=eq.`, `rpc/`,
  upsert resolution, and an advisory lock.
- **Selftest 8/8, both directions.**
  - Positive: arrow functions.
  - Negatives: a version guard, rpc, no write, no await after the parse, and a commented-out write.
  - One arm caught a real bug in the first draft: `await r.json()` itself counted as the window.
- **2 mutants red** (the guard check and the await check).
- **Over api/:** 191 files scanned, **41 sites to judge**. They are QUESTIONS, not defects: a site is a lost update only
  if two requests can write the same row. The list is in the scratchpad run, and NONE was triaged this batch.
- Zero files scanned exits 2. It has a PURPOSES entry in the tooling inventory.

## 4. VT — NOT SEEDED (no Rule 6 on the official index)
- `vtcourts.gov/attorneys/rules` has no compiled-rules link. It points to **LexisNexis** for "Vermont Statutes, Court
  Rules and Administrative Code", a script-driven app that cannot be fetched.
- `/attorneys/rules/promulgated` lists only recent orders, none of them a Rule 6 order. `?page=N` returns the same
  page.
- Recorded in the VT blocker doc (b66 section).
- **Unblock:** Michael pastes the Rule 6/12/33/34/36/59 text from Lexis, or supplies the 2017 Rule 6 order URL.

## 5. DC — NOT SEEDED (the official source is unreachable)
- **dccourts.gov returns HTTP 403 to every request:** the site root, the rules pages, and the Rule 6 PDF path.
- **D.C. Code § 28-2701 is reachable** at code.dccouncil.gov. The fetched page returned its annotations, including
  Emancipation Day (April 16) and the Indigenous Peoples' Day amendment.
- No DC gate is possible without the court's rule text. This is the same shape as RI's admin.ri.gov 403: a human
  browser may get through where this fetch did not.

## 6. J4 — the lawyer's questions, VERBATIM
1. **AK, MLK Day.** "Under Alaska Civil Rule 6(a), is Martin Luther King, Jr.'s Birthday a 'legal holiday' for
   computing a court deadline, given that AS 44.12.010(a)(2) lists it 'as provided in (b)' and AS 44.12.010(b) makes it
   a legal holiday 'for employment purposes' for state employees on collective-bargaining terms?"
2. **AK, mailed distribution.** "Does Alaska Civil Rule 6(c) add three days to the Civil Rule 59(b) period, and does
   Appellate Rule 502(c) add three days to the Appellate Rule 204(a)(1) period, when the judgment was distributed by
   non-electronic mail and the period runs 'from the date shown in the clerk's certificate of distribution'?"
3. **ND, 59(c) mail days.** "Does N.D.R.Civ.P. 6(e)(1) add three days to the Rule 59(c)(2) period when notice of entry
   of judgment was served by mail?"
4. **ND, Juneteenth.** "Is June 19 a 'legal holiday' under N.D.R.Civ.P. 6(a)(6), given that N.D.C.C. 1-03-01 does not
   list it and 1-03-01(12) reaches only days 'appointed by the President of the United States or by the governor of
   this state for a public holiday'?"
5. **SD, under-eleven ordering.** "Under SDCL 15-6-6(a) and (e), is the 'less than eleven days' threshold applied to
   the prescribed period before or after the three days added for service by mail?"
6. **SD, notice-of-entry mail days.** "Does SDCL 15-6-6(e) add three days to the SDCL 15-6-59(b) and 15-26A-6 periods
   when written notice of entry was given by mail?"
7. **RI, the holiday list.** "For R.I. Super. R. Civ. P. 6(a), which days are 'legal holidays': (a) does R.I. Gen. Laws
   § 25-1-1 supply the list although it says 'holidays'; (b) is the Monday 'state employees will celebrate' after a
   holiday falling on a Saturday a legal holiday for court deadlines; (c) is general election day a holiday in a year
   with only legislative races; (d) does the clause 'any other days as … the president or the Congress of the United
   States shall appoint as holidays for any purpose' bring in every federal holiday?"

Every one of these is currently encoded on the EARLY side, and each is disclosed in that jurisdiction's
`JURISDICTION_COVERAGE` entry.

## 7. CLAIMS HELD
`sairnlaw`. It is released after this push lands.

## 8. OPEN
| # | open | owner | next step |
|---|---|---|---|
| J5 | VT | Michael | the Lexis text of Rules 6/12/33/34/36/59, or the URL of the 2017 Rule 6 order |
| J6 | DC | Michael | the dccourts.gov Rule 6 text (the site 403s automated fetches) |
| S3 | the 41 S2 sites | owners per file | triage: which writes can race on the same row |
| J4 | the 7 questions above | Michael / counsel | answers flip specific rows or calendars, each named in coverage |
| A1, T1, P1, R1, G1 | carried | as before | unchanged |

## 9. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\58897a7d-eff3-428b-8fec-18274a858ae9.jsonl
