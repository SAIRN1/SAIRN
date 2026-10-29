# SAIRN handoff — hank b65 — 2026-10-29

**Subject:** VT, RI, WY and DC seeds, and the S2 detector.

**Result:**
- RI and WY are SEEDED and LIVE.
- VT is NOT seeded: the URL supplied is not the rules.
- DC and S2 were NOT STARTED, because the context budget ran out.

This handoff was written before the report.

## 1. Vermont — NOT SEEDED: the supplied source is the wrong document
- `https://www.vtcourts.gov/media/595` → `AR-2014_VRCP.pdf`. That is the Advisory Committee's **2014 Annual Report**:
  5 pages of committee business, with no rule text.
- It was recorded in `docs/sairnlaw-vermont-deadline-seed-blockers.md` (b65 section). Nothing was guessed.
- **Needs:** the vtcourts.gov URL of the current compiled V.R.C.P., or of the 2018 promulgated Rule 6 order.

## 2. Rhode Island — SEEDED and LIVE (`8b405671d`)
- **Rule 6 was never the blocker.** It names no holiday statute. The calendar is the **early-side reading of § 25-1-1**
  recorded in the blocker doc, seeded on Michael's b65 direction.
- **Encoded:**
  - every named day (4 May, Victory Day, Columbus Day, Juneteenth…);
  - the general Sunday→Monday shift;
  - Thanksgiving (appointed by the President and by Congress, which the incorporation clause reaches);
  - election day in 2026 and 2030.
- **Omitted, each EARLY:** the employee-only Monday after a Saturday holiday, 2028 election day, and appointed days.
- **Engine:** `ri_rcp_6a` is the federal count. `ri_rcp_6d` is **+1 day, for mail OR electronic service**, added to
  the period.
- **Seed:** 8 rows. Interrogatories and production are **40 days**.
- **Live:** before, `NOT_PROVISIONED`. After:
  - interrogatories 2026-09-24 → **2026-11-04** (election day rolls);
  - by email 2026-09-23 → **2026-11-04**;
  - answer 2026-07-21 → **2026-08-11** (Victory Day).

## 3. Wyoming — SEEDED and LIVE
- **Gate:** `docs/sairnlaw-wyoming-deadline-seed-gate.md`. Sources: wyocourts.gov W.R.C.P. eff. 9-21-26, and wyoleg.gov
  W.S. 8-4-101.
- **Holidays:** the "legal holiday" definition includes governor-, chief-justice- and LOCAL-official days, which are
  omitted (EARLY). The shift is Sunday-only. There is no Juneteenth and no Columbus Day.
- **Engine:** `wy_rcp_6a` (federal count) and `wy_rcp_6d` (mail or delivery to the clerk, +3, added to the period).
- **Seed:** 6 rows. **The 6(c)(2) motion response is NOT seeded**, because it ends at the EARLIER of two dates.
- **Live:** before, `NOT_PROVISIONED`. After: by mail 2026-05-20 → **2026-06-22**, answer 2026-06-13 →
  **2026-07-03** (no Saturday shift).
- **Shared with RI:**
  - Drift 0 (479/479 rules, 176/176 holidays).
  - `deadline-rhodeisland-wyoming.test.js` 29/0; 3 mutants red.
  - All deadline suites green.

## 4. DC and S2 — NOT STARTED
- They were not done because the context window reached ~67% after RI and WY. The 85% wrap-up has to fit the
  handoff and the pushes.
- **DC:** use the ND/SD/WY pattern. The sources are D.C. Super. Ct. R. Civ. P. 6 and D.C. Code § 28-2701.
- **S2:** a server-shaped read-await-write detector. A planted server-side case must be its first fixture.

## 5. push_retry — one more defect found by use, FIXED (`c67b69105`)
- **The defect:** a LANDED fast retry's BYPASS-LOG row was left uncommitted (by b63's design). The next `--loop` then
  started dirty and its rebase refused (exit 3).
- **The fix:** each attempt now folds an **append-only** BYPASS-LOG change into a gate-bookkeeping commit before
  rebasing.
- **Tests:** selftest 63/0. An always-true mutant of the append-only check is red. There is a register record.
- **Live:** "bypass rows: committed the BYPASS-LOG row" was printed on the next run.
- **Still open (C1b):** concurrent agents append to `docs/BYPASS-LOG.jsonl`, so rebases CONFLICT on it. That happened
  twice in b65, and each time it was union-resolved by hand: rows 124→125→126, both sides kept.
  - **Recommended fix:** `docs/BYPASS-LOG.jsonl merge=union` in `.gitattributes`. That is a shared file, so it is
    Michael's or cc's call. Not done here.
- **The b65 docs push:**
  - The loop landed on attempt 4.
  - FAST RETRY fired twice.
  - The full gate ran once, because incoming commits touched our manifest. That is correct.

## 6. CLAIMS HELD
`sairnlaw`. It is released after this push lands.

## 7. OPEN
| # | open | owner | next step |
|---|---|---|---|
| J5 | VT | Michael | the correct vtcourts.gov URL for the compiled V.R.C.P. |
| J6 | DC | hank (next) | the ND pattern |
| S2 | the server-side stale-snapshot detector | hank (next) | build it, with a planted server-side fixture first |
| C1b | BYPASS-LOG rebase conflicts | Michael / cc | `merge=union` in `.gitattributes` |
| J4 | lawyer's questions | Michael / counsel | the AK/ND/SD/RI readings (RI § 25-1-1 is the largest) |
| A1, T1, P1, R1, G1 | carried | as before | unchanged |

## 8. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\58897a7d-eff3-428b-8fec-18274a858ae9.jsonl
