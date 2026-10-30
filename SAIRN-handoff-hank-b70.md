# SAIRN handoff — hank b70 — 2026-10-30

**Subject:** b70 items 1 to 5.
- VT from the official page.
- DC Probate seed.
- M5 PARTIAL render.
- H1y across the other apps hank owns.
- Primary-source URLs.

This handoff was written before the report. Every SHA below is the LANDED one. HEAD was fast-forwarded to `8e481cea7` before any work.

## 1. VT (J5) — BLOCKED. The exact missing source is named (`b777c4637`)
- **Measured:** the official sitemap, https://www.vermontjudiciary.org/sitemap.xml (9 pages), lists **17,442 URLs, and none is V.R.C.P. text**. Site search returns 404.
- **The rules page defers current text to LexisNexis:** https://www.vermontjudiciary.org/attorneys/rules
- **The promulgated list covers two years:** https://www.vermontjudiciary.org/attorneys/rules/promulgated
- **MISSING SOURCE**, either of:
  - an official copy of V.R.C.P. 6/12/33/34/36/59 that carries a current-through date;
  - the promulgation orders for any amendment to them between **2018-01-01 and 2022-10**.
- Lexis was not used, by instruction. The detail is in `docs/sairnlaw-vermont-deadline-seed-blockers.md` §b70.

## 2. DC (J6) — Probate Division: gate PASS and engine standard LANDED (`ac060bedf`); the seed is PARKED until it is loaded
- **Gate:** `docs/2026-10-30-hank-b70-dc-probate-deadline-seed-gate.md`.
  - It is self-named rather than `docs/sairnlaw-*`, because `docs/` is fourth's and only a self-named path is in hank's scope.
  - **Every source is cited with its full URL and sha256** (methodology item 5).
- **The primary source for all 5 rows:** https://www.dccourts.gov/sites/default/files/superior-rules/Superior-Court-Rules-of-the-Probate-Division-EFFECTIVE-8-22-2022.pdf
  - sha256 `cd045c1e…a44b9`, retrieved 2026-10-30.
- **Current-through:**
  - The rules index, https://www.dccourts.gov/superior-court/rules, reads "Last Updated : 02/13/2026".
  - The official Rules and Promulgation Orders list, https://www.dccourts.gov/superior-court/superior-court-resources/superior-court-orders?search=&order_type=Rules+and+Promulgation+Orders, has 66 orders through 26-04 (2026-09). None amends the Probate Division rules after 2022.
- **Observed holiday days:** D.C. Code § 28-2701, https://code.dccouncil.gov/us/dc/council/code/sections/28-2701
- **What landed:**
  - `dc_probate_r_128a` (Rule 128(a), the federal text);
  - `JURISDICTION_COVERAGE.dc`, incomplete and EARLY: no Emancipation Day, no Inauguration Day, no court-observed days;
  - the `dc` / `probate` labels;
  - 16 per-state suites updated to pin `dc`.
- **PARKED, built and tested 21/21, NOT in the repo:**
  - **Where:** `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\7439551c-4f37-4ff2-81aa-7549f726dd51\scratchpad\dc_parked\`.
  - **The files:** `sairnlaw_deadline_seed_dc.json` (5 rows), `sairnlaw_deadline_calendars_dc.json` (2026–2031) and `deadline-dc.test.js`.
  - **The generator** is at `...\scratchpad\gen_dc.py`. It is run from the repo root and writes both JSON files into `sql/`.
  - **Why parked:** the push gate refuses a seed the live licence does not hold (LAW-PINNACLE-2026: 5 rules and 6 calendars MISSING). The load needs a licence key, an employee and a PIN, and this session has none of them.
  - **The scratchpad is session-local.** If it is gone, regenerate with `gen_dc.py` from the gate doc, or re-derive from the gate doc's §5 table.
- **Rows:**
  - 105(c)(2): response, 14 days after filing;
  - 112(c)(1): inventory, 90 days after appointment;
  - 112(c)(2): conservator inventory, 60 days after appointment;
  - 113(e)(6)(B): formal-audit demand, 20 days after approval;
  - 125(c)(2): reconsideration after final account, 20 days after entry.
- **Not seeded:** 125(c)(1). Its second cut-off would make the date LATE.
- **Not touched:** the DC civil rules (6/12/33/34/36/59). dccourts.gov now returns 200, so they are seedable next.

## 3. M5 — cutoff kept at 30 days. The panel renders correctly OFFLINE; the LIVE check is BLOCKED (`ca9790795`)
- **Offline:** `api/b70-m5-partial-render.test.js` passes 4/4.
  - It drives the real `rTrust()` and `LAW_RECON_STATUS` from sairnlaw.html against the real reconciler.
  - A 91-day-old deposit in transit renders **"Partly reconciled"**, with the bank leg's "NOT RECONCILED ON THIS LEG ALONE … more than 30 days" reason.
  - **Control:** a fresh deposit renders "Reconciled".
- **LIVE with an authenticated session: NOT DONE.**
  - It needs a SAIRNlaw licence key, an employee and a PIN, and none is in this session.
  - It also needs a stale deposit-in-transit row on that licence.
  - `/api/sd-data` answers 401 unauthenticated.

## 4. H1y — FIXED in sairnvet, sairncode and sairnbiz (`1406e46f7`, register `ac342288e`, guard `2d861a268`); stonedesk PARKED
- **Counts:**
  - sairnvet: 62 values now go through `JA()`.
  - sairncode: 32 values now go through `JA()`.
  - sairnbiz: 8 values. They keep the single-quoted form their suites pin, JS-escaped with `.replace(/[\\\u0027]/g,'\\$&')` before `H()`.
- **`api/b70-inline-handler-args.test.js` passes 19/19.** Arm X finds the shape at `8e481cea7` in all three files.
- **Live on sairn.vercel.app:** the fix is PRESENT in all three files.
- **Suites:** all 62 sairnvet/sairnbiz/sairncode/stonedesk suites match base.
  - `stonedesk_exec_msgs_gate.js` fails at base too.
  - My first attempt, a new global JA in sairnbiz/stonedesk, broke 5 suites. It was caught before commit and is cause-tagged as row 2.
- **stonedesk.html, 2 sites (`sdDrawingsLoad` / `sdDrawingsDelete`), PARKED.**
  - **Why:** fourth held an ACTIVE stonedesk claim, and the claim-state recheck refused the push.
  - **The patch:** `...\scratchpad\stonedesk_h1y.patch`. It is the **earlier JSON-quote form, which breaks `tests/stonedesk_saved_drawings.js`**. Apply the single-quote form shown in the sairnbiz commit instead.
  - The rest of StoneDesk already uses `escAttrJs`.

## 5. Cause tags
`docs/recurring-bug-classes.md`, batch 70, has 2 rows: the copied wrong-layer escape, and my test-coupling miss.

## 6. CLAIMS HELD
`sairnlaw` is released after this push.

## 7. OPEN — exact next steps
| # | item | owner | next step |
|---|---|---|---|
| J6L | DC Probate load + seed push | Michael (credentials), then hank | with licence key/employee/PIN: `python tools/load_deadline_seed.py dc --dry-run`, then the real load. Verify a dc/probate compute goes from NOT_PROVISIONED to the gate §6 dates. Copy the 3 parked files into `sql/` and `api/_lib/`, then commit and push |
| J6C | DC civil Rules 6/12/33/34/36/59 | hank | dccourts.gov is now reachable, so run the same gate. Civil Rule 6 PDF: https://www.dccourts.gov/sites/default/files/rules-superior-court/Civil%20Rule%206.%20Computing%20and%20Extending%20Time%20Time%20for%20Motion%20Papers.pdf (Promulgation Order 24-02 amended it) |
| M5L | live authenticated PARTIAL check | Michael (session) | sign in to SAIRNlaw on sairn.vercel.app. On a licence with a deposit in transit dated more than 30 days before the latest statement, open Trust Accounting and confirm "Partly reconciled" plus the stale-deposit sentence |
| J5 | Vermont | Michael | the missing source in section 1 |
| H1y-SD | stonedesk 2 sites | hank, after fourth releases `stonedesk` | the single-quote JS-escape form, as in sairnbiz; then run `tests/stonedesk_saved_drawings.js` |
| H1z | the same shape outside hank's apps | owners | sweep with `api/b70-inline-handler-args.test.js`'s scan |
| carried | SDP, LGP, J4, J2, A1, P1, R1, G1, S5, S7, T1, M5r, RL1, LE1, HK1 | as in b69 §8 | unchanged |
