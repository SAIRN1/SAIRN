# SAIRN handoff — cody b64 (2026-10-29)

## Committed / pushed state
- **LANDED, tip `a5ad5f7c9`, full gate.**
  - The rebase hit conflicts in `docs/defect-density-register.json`, because both sides had appended records. I merged them by identity: my first record by hand, the rest with `tools/sairn_rebase_resolve.py`. `register --check` is OK at 784 records.
  - The gate then blocked on Tier A. I opened one obligation covering the 35 resources the re-entry guards touch; the gate assigned it to **cc**.
- **The manifest** gained the seven app files the item-3 fixes touch: sairncode, sairndental, sairngrounds, sairnlegacy, stonedesk, sairncare and sairnlaw. Michael directed this ("fix each one found").
- **Claim:** sairnmechanical, cody b64. It is released at close.

## 1. The DECISION-NEEDED is resolved, and the row is closed with no code change
- **Michael's decision:** the b33 email-leg removal already covers H1's mirror. The RFC3161 mirror push has been live since 2026-10-07.
- The index row `B63-H1-DRILL-CODY-2026-10-29` is now CLOSED (&#9989;) and its "Blocked by" cell reads "decided 2026-10-29, Michael".
- The shards were regenerated: `open_work_shard --check` is CLEAN, with 823 rows.

## 2. The saveDoc guard can no longer be held open by a fetch that never answers (FIXTURE FIRST)
- **The fixture came first.** `tests/mech_fetch_timeout_fallback.js` drives the real `mechData()` and `mechPushOne()` against a fetch that never settles unless aborted, in three engines.
  - **RED on the old code:** the modern engine passed 2/2 (the control). An engine with no `AbortSignal.timeout` went 0/2, and one with no `AbortController` went 0/2; both HUNG.
- **The fix:**
  - `AbortSignal.timeout` where it exists;
  - otherwise an `AbortController` aborted by a timer at the same 15 s;
  - and `mechData()` races a backstop timer (timeout + 1 s) for an engine with neither.
- **Now 6/6.** The other suites:
  - `transport_timeout_sweep` 81/81 across 15 apps;
  - `mech_backup_not_silent` 23/0;
  - the fault probe and the redaction probe 0 failures;
  - `node --check` clean.

## 3. The re-entry sweep across all apps: 47 real, ALL 47 FIXED, each fixture-first
- **Method.**
  - 507 handlers were scanned and 87 suspects read by hand. The candidates were every handler on onclick, onsubmit or onchange, every `addEventListener` and every `.onclick=` that awaits and writes.
  - **Limit:** handlers wired through `data-action` delegation would not be found.
  - The scanner and its logs are in this session's scratchpad, under `reentry/`.
- **The six highest-impact, committed as `23315f891`.** Each arm drove the real handler, was RED first, then green:
  - sairnlegacy `confirmPayment`: the pre-need `amount_paid` was applied twice.
  - stonedesk `posCompleteSale`: a slab re-reserve and a duplicate invoice.
  - sairngrounds `dcCreateInvoiceAndSchedule`.
  - sairncode `addClaimEntry`.
  - sairnlegacy `saveCremation`.
  - sairndental `respondToComplaint`: a duplicate reply in a patient's thread.
- **The other 41, committed as `a746b20e4`.** None were skipped, and every arm was RED on the unfixed code first.
  - **sairncode:** 24 handlers through one shared helper, `scSaveBusy`/`scHoldWhile`.
  - **The rest:** sairncare 4, sairndental 3, sairnlaw 1, sairngrounds 5, sairnmechanical 2 and stonedesk 2.
  - `tests/lib/save_reentry_harness.js` is the shared driver.
  - **Results:** sairncode 125/0, sairncare 20/0, sairndental 19/0, sairnlaw 5/0, sairngrounds 34/0, sairnmechanical 10/0, stonedesk 16/0.
  - Across the 181 JS tests that read these files, there are no new failures.
- **Found, but outside this shape:**
  - grounds `gcdPlaceOrder` and `gcdMarkShotEnd` wait on the device GPS, not the server. A second press sends a second Pro Shop order.
  - stonedesk `posCompleteSale` without a slab awaits nothing, but a 2.5 s reset window means a second press records a second sale.
  - Several handlers never reset what they read. A press after the wait has finished still creates another record; the guard covers only the wait itself.
- **Tests:** the 148 JS tests that read the edited files show the same 8 reds before and after, all pre-existing from the b59 triage, with no new failure.

## 4. Competitive-gap audit recount
- **Measured** with `git ls-files`: 17 apps (the top-level `*.html` files, excluding sub-pages) against `docs/cloud-research/*`.
- **11 of 17 have a committed WORLDWIDE audit.** The **6** with none are:
  - **sairncare**: only `external`, 09-25;
  - **sairndental**: `competitive-gap-audit-2026-10-19`, not named "worldwide";
  - **sairnfreedom**: external, 09-27;
  - **sairnlegacy**: 10-05;
  - **sairnscape**: 10-05;
  - **stonedesk**: external, 09-26.
- **0 apps have no audit doc at all.** Each of the 6 has an earlier-round doc committed.
- **What a repo count cannot see:** whether worldwide research for those 6 exists only in a session or in Drive. fourth's audits say they are built "from the research on file". fourth's b63 queue named sairnmechanical, then sairnbuild, sairngrounds, sairncash and sairncare; the first four are now committed, and **sairncare is the one still outstanding from that queue.**

## 5. Methodology
- **Fixture first, for items 2 and 3.** Each fixture reproduced the hang or the duplicate, and was RED, before the fix.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | Out-of-shape re-entry: grounds GPS waits, stonedesk 2.5 s POS window, handlers that never reset their inputs | cody: guard or reset each |
| O2 | 6 apps with no committed worldwide audit | fourth's audit queue (sairncare next) |
| O3 | Turn the re-entry sweep scanner into a standing checker | cody |
| O4 | Tier A reviews of the b64 app changes | whoever the gate assigns |
