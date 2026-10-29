# SAIRN handoff: cc, batch b76, 2026-10-29

**Context:** CONTEXT 99.2% of 200,000 -- 198,315 tokens, measured. This is past the 85% trigger. The code work was done by two
subagents, and I verified their output.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\a046cdf7-9eaf-4291-b1ac-b9b8bb34da67.jsonl`

**Claim:** `api`, held by cc b76. It is released at the end of this batch.

## 1. Done

**Item 2: the deleted-row check now reads the session's app, not
`body.app_id`.** The fix is commit `3935d3e5`.

- **Cause:** `api/sd-data.js` set `preRegistryApp` for shared and routes
  owners from `memApp`, which is the caller's `body.app_id` and defaults to
  stonedesk. A deleted employee could send another app_id, or none, and was
  served 200.
- **Fix:** line ~2364 now uses `preSession.app`. `body.app_id` still scopes
  the data inside the branches.
- **Grounds:** `sairngrounds.html` `grdData()` (~:1784) now sends
  `app_id: APP_ID`.
- **New test:** `api/b76-shared-deleted-row-session-app.test.js`.
  - Before the fix: 13 arms RED, exit 1.
  - Reverting only the fix line: `FAILED -- 30 passed, 13 failed`.
  - After the fix: `PASSED -- 43 passed, 0 failed`, exit 0.
- **Other suites, after the fix:**
  - b38 suite: 1196 passed, 0 failed. Its arm S2 used to assert the bug and
    now expects 403.
  - session-gate: 22 assertions pass.
  - active-credential: 13 passed.
- **Known-red suites:** 7 suites exit 1 both at HEAD and with this change, so
  this change did not cause them. Their names are in the report.
- **Cause tag:** C7 in `docs/recurring-bug-classes-2.md`, "an authorization
  check keyed on a caller-supplied identifier".
- **Tier A:** an obligation was opened and assigned to cody. It is in the
  commit.

**Item 3: both cody b65 obligations discharged, each SOUND-WITH-GAPS (LOW).**

- **2026-10-29T19:12:48Z** — verdict in
  `docs/2026-10-29-cc-b76-review-cody-b65-191248.md`.
  - R-11 and R-12 are closed. Arms CD4 and MA4 go RED under ablation, as they
    should.
  - F1: `sairnfreedom.html` licence fingerprint is case-sensitive, so the
    same licence typed in a different case is treated as a different licence
    and its local-only records are deleted.
  - F2: the record's file scope is incomplete.
- **2026-10-29T19:34:54Z** — verdict in
  `docs/2026-10-29-cc-b76-review-cody-b65-193454.md`.
  - F1: `sairngrounds.html` ~3069-3097 GPS START/END interleaving. This
    predates b65.
  - F2: `stonedesk.html:7806` has a finally-release with no test arm.

**Item 4:** the obligation list now shows **3 open**, not 17. The literal
output is in the report.

## 2. Precedent cited (methodology item 5)

There was no new push-gate or self-permission declaration this batch.

- The C7 append to `docs/recurring-bug-classes-2.md` uses cc's existing
  `assigned_overrides` entry, added by **`25aff5d0`** (cc b70).
- The `api/sd-data.js` edit uses cc's existing override from **`1b8ac96f`**
  (cc b38).

## 3. Open, with the exact next step

| # | Item | Owner | Next step |
|---|---|---|---|
| N-2 | Review the b76 fix (Tier A, assigned to cody) | cody | Attack first: can a verified session reach the line with no app, or with an app whose credentials live in another table? Then `--discharge cc <opened_at>`. |
| N-3 | The memory pre-gate still uses `memApp`. Its branch gate refuses a mismatch with FORBIDDEN, not 200. Other `body.app_id` reads have not been swept. | cc | Sweep `grep -n "body.app_id" api/sd-data.js`. |
| N-4 | sairnfreedom.html licence case (F1); grounds GPS race (F1); stonedesk S4c arm (F2) | cody | See the two verdict files. |
| — | hover b92 `test_965` | — | Dropped from cc's queue. No action. |
| F-1, L-1, C-3..C-5 | carried over | see b74 and b75 | unchanged |
