# SAIRN handoff — hank b64 — 2026-10-29

**Subject:**
- J1 continued: SD, VT, RI.
- The `sd-sub-data.js:71` UTC-day fix, and the scanner's `.js` coverage.
- C1a: the push_retry fold moved into its own commit (Michael chose this in b64 over pinning the exemption to
  patch-ids).

This handoff was written before the report. Nothing is half-finished.

## 1. South Dakota — SEEDED and LIVE (the ND pattern, exactly)
- **Gate:** `docs/sairnlaw-southdakota-deadline-seed-gate.md`. SD's civil rules are statutes (SDCL 15-6), read verbatim
  from sdlegislature.gov.
- **Engine (`bc04f91c9`):**
  - `sd_rcp_6a`: the Ohio mechanism with **ELEVEN** ("less than eleven days"). It is the first seeded state at 11.
  - `sd_rcp_6e`: mail only, added to the period.
  - `JURISDICTION_COVERAGE.sd`, direction early.
- **The holiday referent is express** (§ 1-5-1). Both weekend shifts apply to five days, Juneteenth included.
  Native Americans' Day is also a holiday.
- **The under-11-vs-mail ordering is unstated, so it is AVOIDED:** no row with a base count under 11 carries mail days.
- **Seed (`3494815d1`):** 8 rows. The dispatch said 12. The text supports 8 without guessing a limb.
  - SD suite 28/0; 4 mutants red.
  - 45/45 deadline and sub-data suites green.
- **Live:**
  - Before: `NOT_PROVISIONED`.
  - After:
    - interrogatories by mail 2026-09-12 → **2026-10-15**;
    - new trial 2026-06-05 → **2026-06-22** (10 < 11, so weekends and Juneteenth are skipped);
    - appeal 2026-05-20 → **2026-06-22**.
  - All match the hand derivation. Drift 0: 465/465 rules, 164/164 holidays.

## 2. Vermont — BLOCKED ON SOURCE (not gated)
- **Record:** `docs/sairnlaw-vermont-deadline-seed-blockers.md`.
- vtcourts.gov hosts individual promulgation orders but no compiled current V.R.C.P. The obvious rule URLs all return
  404, and only a summary list of the 2018 changes and a 2017 RECOMMENDED draft are reachable.
- This is the Kentucky shape.
- **Needs** the promulgated 2018 Rule 6 order and each period rule, or Michael's acceptance of the official West/Lexis
  compilation as the source.

## 3. Rhode Island — still NOT SEEDED; the search is recorded in the blocker doc
- **Item 4 asked to source the referent and seed.** No official referent was found:
  - courts.ri.gov holiday pages: 404;
  - admin.ri.gov/holidays: **403** (possibly a bot block, so a human may get through);
  - hr.ri.gov and ri.gov: 404;
  - two searches: third-party calendars only.
- **Also found:** 2026 bill H 7781 carries § 25-1-1 text, and its status is unconfirmed.
- **Not seeded:** seeding on a guessed list is the late-direction risk the gate exists for.
- See the b64 section in `docs/sairnlaw-rhodeisland-deadline-seed-blockers.md`.

## 4. sd-sub-data.js:71 — FIXED (`ca1cf0fca`)
- **The fix:** `localTodayISO()` (America/New_York) replaces the UTC day at line 71 and at both callers, including the
  409 assignment block.
- **Why that zone:** there is no per-licence time zone server-side. America/New_York is the easternmost zone of the 50
  states, so it can never call a still-valid document expired in them.
- **Stated limit:** PR/USVI could read 'valid' for up to 1 hour after their own midnight.
- **Test:** `api/b64-sub-compliance-local-day.test.js` 9/0, run against the SHIPPED functions.
  - A control arm shows the UTC day blocked a COI on its last valid evening.
  - 2 revert mutants are red.

## 5. The scanner reads .js now (`48a3e5d79`)
- **What changed in `tools/sairn_stale_snapshot_scan.py`:**
  - A `.js/.mjs/.cjs` file is read as one script block.
  - Named files that yield no script are listed as NOT read.
  - A run that scans nothing exits 2.
- **Re-run over api/:**
  - **191 files scanned** (previously 0 were actually read).
  - 5 UTC derivations remain, all judged intentional in b63: the demo-day bucket, the retrieved_at stamp, and the
    render-usage month pair.
  - **sd-sub-data.js is gone from the list.**
- **"Clean" means no unjudged hit. It does not mean zero.** The tool itself says "do not drive it to zero".
- **Still a limit:** the read-await-write arm targets the client store shape. It did not catch a planted server-side
  case, so its zero on api/ is not evidence.

## 6. C1a — the fold goes into its own commit (`2a49d1e17`)
- **The change:**
  - Regenerated documents go in a `chore(derived-docs <tip>)` commit, amended in place when it is HEAD.
  - `authored_commits()` drops that commit and the gate-bookkeeping commit from the patch-id and file sets.
- **Tests:** selftest 60/0. A "keep the regen commit" mutant is red.
- **LIVE, on this batch's own push:**
  - attempt 1 was a `generated` refusal, so it folded;
  - attempt 2 lost the race;
  - attempt 3 printed **"FAST RETRY, gate not re-run: … these 5 patch-id(s)"**, after two regenerate folds, and
    PUSHED.
  - b63 pushes 3 and 4 had fallen to the full gate in exactly this situation, so this is the fix working.
- **Seen, minor:** a gate-bookkeeping commit created between attempts means a second derived-docs commit is made
  rather than amended. That is harmless, because both are excluded.

## 7. CLAIMS HELD
`sairnlaw` and `tools`. Both are released after this push lands.

## 8. OPEN
| # | open | owner | next step |
|---|---|---|---|
| J2 | RI | Michael / counsel | the RI Judiciary's annual holiday/closure notice (a human may get past the admin.ri.gov 403), or a decision on the § 25-1-1 readings |
| J5 | VT | Michael | the 2018 promulgated Rule 6 order and period rules, or acceptance of the official compilation |
| J3 | WY, DC | hank (next) | the ND/SD pattern |
| J4 | lawyer's questions | Michael / counsel | AK MLK (b); AK/ND/SD mail days on notice-of-entry or distribution rows; ND Juneteenth; the SD under-11 ordering |
| S2 | the stale-snapshot arm is blind to server code | tool owner | a server-shaped read-await-write detector, with a planted control |
| A1, T1, P1, R1, G1 | carried | as before | unchanged |

## 9. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\58897a7d-eff3-428b-8fec-18274a858ae9.jsonl
