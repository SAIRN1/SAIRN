# HANDOFF — fourth / ted, batch b49, 2026-10-21

**READ THIS FILE ONLY.** It is the whole state. **Everything is landed. No
force, no gate skip.** All 37 dental, roofing, senior and sairnbiz suites exit 0
on the landed tree. Wrapped at a safe point at **~45% real context**.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Scratchpad:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- `add_defect49.py` holds the register records;
- the `mut_*.html` files are the mutation copies.

## 1. STATE (origin/main, rebased SHAs)

| item | sha | result |
|---|---|---|
| 1 dental reds | `95e31d3b7` | ledger_export 8/8, mc 3/3, rollup 18/18 |
| 2 b47 geocode arms | `c04a3baaa` (b47) | already landed. cc b36's gap was the **Z8 display** tests: `dd3c45f6e`, 19 arms, 6/6 mutants |
| 3 cody defect 7 (roofing) | `5e38373c6` | RED 3/10 → GREEN 10/10, 3/3 mutants, fault probe 0 |
| 3 cody defect 8 (senior) | `02cec2f84` | RED 5/15 → GREEN 15/15, 6/6 mutants |
| + senior reds (Michael's follow-up) | `11cc6e33d` | negative_hours 22/22, referral 11/11 |
| 4 overrides review | `a1052d124` | details below |
| bookkeeping | `a1052d124`, `598f0a09d`, `c58242795`, `7d13b7b39` | register, Tier A, docs, re-seats |

## 2. CONCEPTS (one per fix, stated before code)

- **Dental ledger export:** a vm suite extracts every function the export
  calls. `dntChargeCode()` was missing.
- **Dental rollup:** the `panel-*` id prefix is the panel namespace, so the
  announcer was renamed `nav-announce`.
- **Roofing:** a read that failed, or a table that is not set up, is said on
  screen and never rendered as "none".
- **Senior defect 8:**
  - a refusal withdraws the row and names the reason;
  - no answer, or a table that is not set up, keeps the row on the device and says which;
  - a claim keeps its pricing and authorisation message when its save fails;
  - with no contract in force, the claim message says it is unknown whether authorisation is required.
- **Senior suites:** both extract `senEffClock()`. The claim sandbox also
  carries `senLastErr`, because this batch's `generateClaim` clears it before
  writing.

## 3. OVERRIDES REVIEW (fourth now holds 15)

- **Removed:** `api/route-map.js` and `api/b46-route-geocode.test.js`. cc
  reviewed the geocode work and found it SOUND.
- **Kept, waiting on cody's review (none found):** 5 sairnbiz test files.
- **Kept, waiting on a review of the b48 work:** 4 dental `api/` entries.
- **Added for this batch:** 6 `tests/` files.

## 4. OPEN

1. **Tier A, owed by cc:**
   - `sen_payer_contracts`, `sen_authorizations`, 4 `rf_*` resources, `employees`/`sb_payruns`, `sen_claims`/`sen_clients`/`sen_visits`;
   - plus Z8 display (`dbac30771`).
2. **Platform notes, not fixed:**
   - `tests/app_session_isolation.js` is red at HEAD ("routes: recorded NOTHING").
   - `tests/sairndental_write_failure_probe.py` probe 2 does not bite. It was also exit 1 before this batch.
3. **Not swept:** the same `(x.ok&&x.data)||{}` idiom elsewhere in `sairnroofing.html`, and other sairnsenior saves that still use the one-line failure message.
4. **Landing note:** the push gate's own scrutiny rows make the tree dirty, which blocks `pull --rebase`. Commit them before each pull.

## 5. CLAIMS

`fourth`: released at wrap. No SQL.
