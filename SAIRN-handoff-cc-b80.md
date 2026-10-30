# SAIRN handoff: cc, batch b80, 2026-10-30

**Context:** CONTEXT 31.9% of 1,000,000 -- 318,621 tokens, measured. The declared window is 1,000,000.

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\a046cdf7-9eaf-4291-b1ac-b9b8bb34da67.jsonl`

**Claims:** none.

## 1. Item 1: C-3 closed

`ctxmeter.py` is the chat's own context-measurement tool. It is not a repo
file, so no clone was ever going to contain it. The search is dropped, and cc
owes no fix.

## 2. Item 2: cody b68 record (2026-10-30T09:00:48Z, invoices/sd_invoices) re-seated, widened and reviewed

**Re-seat.** I ran `--reseat-shas --only 2026-10-30T09:00:48Z`, first as a
dry run, then with `--write`. It moved the anchor `8aa4d7d6` →
`5745a824` on the basis EXACT FILE SET.

**The record's file list was wrong.** It named only
`tests/stonedesk_save_reentry.js`, so the file-set match anchored the record
on the S4c test commit. The change the record's text describes is two other
commits:
- `e22c9cd0`: the 13 licence guards;
- `51d9b401`: sairngrounds `gcdMarkShotEnd`.

I widened the record with `--amend 5745a824 --add-files <the 15 files of
those commits> --body-file <why> --apply`. The amendment is attributed to
cc.

**Review.** Done by a subagent, verified here.
- The verdict is in `docs/2026-10-30-cc-b80-review-cody-b68.md`:
  **SOUND-WITH-GAPS (MEDIUM)**. Discharged.
- Tests: `tests/licence_guard_legacy_device.js` 78/0, exit 0;
  `tests/sairngrounds_save_reentry.js` 48/0, exit 0.
- Ablations: each fix line, removed in a scratch copy, turns its arms RED.
- Read and write forms match in all 13 apps.

**Findings:**
- **F1 MEDIUM** (cody): `sairngrounds.html` ~:3098-3117. `gcdMarkShotEnd`
  reads `round` BEFORE the up-to-8s GPS await and saves it after. An End
  round or Arrive pressed during that wait is overwritten by the stale copy,
  locally and on the server (`grd_rounds`, Tier A). I verified this by
  reading the code. Before `51d9b401` the function crashed instead.
  - Cause tag: stale-snapshot-across-await.
  - Fix: re-read `gcdActiveRound()` after the await, or hold Arrive/End
    while `gcdShotEnding`.
- **F2 LOW** (cody): `sairnfreedom.html` ~:2936-2951. That gate does not
  upper-case the key and keeps a case-sensitive fingerprint. Offline, the
  stored key is removed but the fingerprint stays, so retyping the same
  licence in a different case can still offer the "DIFFERENT licence" wipe.
- **F3 LOW, latent** (Michael): `license_keys_key_key` is `UNIQUE(key)`,
  which is case-sensitive. All keys are upper-case only by convention. The
  read-only proof is `sql/b80_license_keys_case_duplicate_verify.sql`; it is
  NOT RUN and returns counts only, no key material. A unique index on
  `upper(key)` is recommended in the verdict and was not written.

## 3. Item 3: register state after item 2

`--list` shows **3 open, all unresolved, none owned by cc**:
- **hover b92 `test_965`:** UNOWNED, audit track only, overdue 50h.
- **cody 2026-10-29T20:17:23Z (`sf_trustee_audits`):** assigned to fourth,
  overdue 27h. It is COULD-NOT-TELL: its sha `0f8c36e1` does not resolve.
- **fourth 2026-10-29T21:38:43Z (law_trusttx, leg_cremations):** assigned to
  hank, overdue 26h.

`--validate` reports 323 records, OK.

## 4. Item 4: `docs/tier-a-reviews.json` was diffed at every write

Each tool write was snapshotted first, then diffed against the snapshot and
against HEAD:
- **re-seat:** 7 lines vs HEAD;
- **amend:** 51 lines vs the post-re-seat state, 56 vs HEAD;
- **discharge:** 8 lines vs the pre-discharge state.

A parsed record-level comparison against HEAD shows **exactly one record
changed** (cody 2026-10-30T09:00:48Z), with none added or removed.

There were no manifest edits; the line-delta is 0.

## 5. Item 5

Hook presence is re-checked after this batch's commits land. The literal
output is in the report.

## 6. Open

| # | Item | Owner |
|---|---|---|
| B80-F1 | grounds round overwritten across the GPS await | cody |
| B80-F2 | sairnfreedom case-sensitive fingerprint | cody |
| B80-F3 | run `sql/b80_license_keys_case_duplicate_verify.sql`; decide on a unique index on `upper(key)` | Michael |
| L-1, C-4, C-5 | as b79 §3 | Michael |
