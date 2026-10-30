# SAIRN handoff — hank b71 — 2026-10-30

**Subject:** b71 items 1 to 5.
- The Stop hook, plus source URL + sha256 citations.
- VT on the official rules pages.
- DC load and the M5 live check.
- #1734 and #1817.
- StoneDesk H1y.

This handoff was written before the report. Every SHA below has LANDED, except the VT doc commit `97ce52a20`, which lands with this push. HEAD was fast-forwarded to `9cd38e85d` before any work.

## 1. Methodology
- **Stop hook: ARMED, verified explicitly.**
  - `.claude/settings.local.json` → `Stop` → `python "C:/Users/marsh/Documents/SAIRN-hank/.git/sairn-hooks/sairn_done_line.py" --stop-hook`.
  - **The armed copy is byte-identical to `tools/sairn_done_line.py`** (`cmp` after `tr -d '\r'`).
  - **Selftest: 20 arms, 0 failed** (criteria 2026-10-29.cody-b66.1).
  - **b70's record in `.git/sairn-done-line`** shows `refusals: 0`.
- **Sources:** every source used this batch is cited with its URL and sha256: the VT doc §b71 and the DC gate §1 and §8.

## 2. VT (J5) — STILL NOT FOUND on the Judiciary's own rules pages (`97ce52a20`)
- **Pages read directly**, with sha256 of the bytes as served (the pages are dynamic): https://www.vermontjudiciary.org/attorneys/rules, /attorneys/rules/promulgated and /attorneys/rules/proposed.
- **What they hold:** links to LexisNexis, Proposed Amendments and the two-year promulgated list. There is no V.R.C.P. text and no current-through date. Seven other rules paths return 404.
- **WHAT WOULD UNBLOCK IT**, either of:
  1. a Judiciary-issued copy of V.R.C.P. 6/12/33/34/36/59 that states a current-through date (from the Court Administrator's Office or the Civil Rules Advisory Committee);
  2. the 2018-01-01 to 2022-10 promulgation orders for those rules, plus a statement that there are no others.

## 3. DC (J6) and M5 live
- **DC: PASS, loaded and live.**
  - **Load:** `python tools/load_deadline_seed.py dc` on LAW-PINNACLE-2026, signed in as sairn-demo-owner (role: owner). Result: "All 6 calendars and 5 rules loaded."
  - **Drift:** `tools/sairn_load_state_check.py --app sairnlaw` reports 0. Rules and holidays are both MISSING 0, STALE 0, EXTRA 0.
  - **Live compute** on https://sairn.vercel.app/api/legal-deadlines: **7 of 7 dates match the hand derivation.**
  - **Control:** dc / civil-litigation still refuses with NOT_PROVISIONED.
  - **Seed push:** `769ddce10` carries the seed, the calendar and `api/_lib/deadline-dc.test.js` (21/21). The gate doc §8 records the load.
- **M5 live: NOT CONFIRMED (a fail to confirm, not a pass).**
  - The live `law_trust_reconcile` read on LAW-PINNACLE-2026, as owner, returns `PARTIAL` with 1 leg compared.
  - The reason is that the licence has **no bank statement on file**, so the bank leg (where M5 lives) is never compared and `stale_deposits_in_transit` is not emitted.
  - **To exercise M5 live, the licence needs two new rows:** a bank statement, and a trust deposit dated more than 30 days before it with `cleared: false`.
  - **I did not write trust-ledger rows to the canonical licence without your go-ahead.** The offline render of the real panel (`ca9790795`, 4/4) stands.

## 4. #1734 and #1817, reported by commit and blob
- **#1734 (the 3 raw `o.id` sinks): ALREADY FIXED, by `af2db16b3` (hank b69 H1x).**
  - **The blob proof**, counted with a literal fixed-string scan:

    | commit | blob | raw sinks | `JA(o.id)` sinks |
    |---|---|---|---|
    | `cce3c0eb6`, H1's check | `b6e9d79d98baeeeb6a881b8f91eb4bfef62175b4` | 3 | 0 |
    | `af2db16b3` | `35df42f52f2f1bc64ecfae26d29720cfc011d4ef` | 0 | 3 |
    | `9cd38e85d` (HEAD at start) | `ad195137b155276d7c57172fc18a038d296ab951` | 0 | 3 |

  - **Where they are:** `advanceKeepsakeOrder`, `markFloristDelivered` and `advanceCatererOrder`.
  - **Why H1 still listed them:** H1 #1810 checked `cce3c0eb6`, the blob before the fix.
  - **Still open on #1734:** the SERVER half. The leg write branch checks no id format. That is defence in depth and is not done.
- **#1817 (NY time-zone expiry day): FIXED as a claim, behaviour kept (`149c90b97`, register `5184f89a9`).**
  - The `api/sd-sub-data.js` comment and the claim in `ca1cf0fca` were backwards: Eastern rolls over FIRST, so a western shop's document expires 1–6 h early.
  - The comment now states that window and why it was kept: it is the safe direction for a compliance gate, and there is no per-licence time zone.
  - `api/b71-sub-expiry-eastern-day.test.js` passes 4/4. It covers the West-early window, the Eastern-valid case and a UTC control.

## 5. StoneDesk H1y — the claim was RELEASED, so the fix is applied and live (`eed68c6a7`, register `d76644332`)
- `sdDrawingsLoad` and `sdDrawingsDelete` now JS-escape before `escHtml`, the same form sairnbiz uses.
- **Tests:** `api/b70-inline-handler-args.test.js` now covers stonedesk and passes 25/25, with arm X.
- **Suites:** all stonedesk suites match base. `stonedesk_exec_msgs_gate.js` fails at base too.
- **Live on sairn.vercel.app/stonedesk.html: PRESENT.**

## 6. Cause tags
`docs/recurring-bug-classes.md`, batch 71: (1) #1817's wrong invariant; (2) StoneDesk H1y.

## 7. CLAIMS HELD
`sairnlaw`, `sairnlegacy` and `stonedesk`. All three are released after this push.

## 8. OPEN — exact next steps
| # | item | owner | next step |
|---|---|---|---|
| M5L | live M5 render | Michael | say yes to writing a test bank statement plus a >30-day uncleared deposit on LAW-PINNACLE-2026, or name a scratch licence. Then hank reads the reconcile (expect PARTIAL with `stale_deposits_in_transit`) and opens Trust Accounting live |
| 1734S | server-side id format check on leg writes | hank / Michael | decide whether to add one. Existing ids are newId-shaped, so a format rule must accept every one already stored |
| J5 | Vermont | Michael | either of the two sources in section 2 |
| J6C | DC civil Rules 6/12/33/34/36/59 | hank | the same gate as Probate; dccourts.gov is reachable |
| 1817T | per-licence time zone | Michael | product decision: only that removes the West-early window |
| carried | SDP, LGP, J4, J2, A1, P1, R1, G1, S5, S7, T1, M5r, RL1, LE1, HK1, H1z | as in b70 §7 | unchanged |
