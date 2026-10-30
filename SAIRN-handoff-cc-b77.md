# SAIRN handoff: cc, batch b77, 2026-10-30

**Context window (item 2).**
- Declared: **1,000,000** for session `a046cdf7`, in `.git/sairn-context-window`.
- Measured now: CONTEXT 25.4% of 1,000,000 -- 254,022 tokens, measured.
- Why it changed: the earlier 200,000 declaration was wrong. A prompt of
  222,768 tokens was observed, which is more than 200,000, so
  `context_verify` refused that declaration. 1,000,000 is the only published
  window size the measured prompt fits.

**Claim:** `api`, held by cc b77. It is released at the end of this batch.

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\a046cdf7-9eaf-4291-b1ac-b9b8bb34da67.jsonl`

## 1. Done

**Item 1: the b76 sairngrounds.html change is reverted and routed to fourth.**
- The `grdData` line is restored. `git diff db0bc67a~1 -- sairngrounds.html`
  is empty, and all 5 script blocks pass `node --check`.
- `sairngrounds.html` is removed from `assigned_overrides.cc`.
- The server-side deleted-row fix (`api/sd-data.js`, `preSession.app`)
  stays. It is the platform half. Its regression suite still passes 43/0.
- The routed note is in `docs/2026-10-30-cc-b77-routed.md`, and the
  status-registry note for fourth is appended and confirmed.

**Item 3 (N-3): body.app_id sweep.** There are 10 grep hits. Two are real
reads.
- **`shared_knowledge` (sairnlegacy staff permission): FIXED.**
  - It was gated on `body.app_id === 'sairnlegacy'`, so a staff member
    without access omitted `app_id` and got 200 on read and write.
  - It is now keyed on `lic.app_id`, with the body kept as an OR.
  - The new suite `api/b77-legacy-shared-knowledge-app-id.test.js` was RED on
    4 arms before the fix (exit 1) and passes 18/0 after.
  - Regressions all pass: b76 43/0, b38 1196/0, session-gate 22, active-credential 13.
  - `tests/app_session_isolation.js`, `tests/sairnlegacy_write_failure_voice.js` and
    `tests/sairnlaw_hydrate.js` exit 0, both with and without the fix.
  - Defect-register record added. Cause tag: C7 recurrence in
    `docs/recurring-bug-classes-2.md`.
- **`memApp` (memory): safe, unchanged.** The branch gate verifies the token
  against `memApp`, so a mismatch is refused 403.
- The other 8 hits are comments.

**Item 4: cody b65's 3 LOW findings stay open, routed to cody.** In
`docs/2026-10-30-cc-b77-routed.md`, each finding gives its exact fix and why
cc does not hold its file:
1. `sairnfreedom.html` licence case. The file is cody's override, and the
   same block is in 12 of fourth's `*.html`.
2. Grounds GPS race. This is app logic in `sairngrounds.html`, which is not
   cc's.
3. The stonedesk S4c test arm. It lives in `tests/`, which is cody's.

**Item 5: every manifest edit was diffed before it was written.**
- The new content was built in scratch and diffed against
  `git show HEAD:docs/sairn-path-manifest.json`.
- Exactly 5 changed lines were expected: b77 note added, b76 note amended,
  sairngrounds removed, b77 suite added. 5 were measured, and only then was the
  file copied into place.
- The precedent sha in the note was first written as `5160452b` and corrected
  to `106ae3e2` before writing. `106ae3e2` is the commit that actually added
  the b76 suite entry.
- Precedents cited: **106ae3e2** for the b76 test-file entry, **1b8ac96f** for
  the b38 test override.

**Hover b92 `test_965`:** still dropped, no action.

## 2. Open

| # | Item | Owner | Next step |
|---|---|---|---|
| G-1 | Add `app_id: APP_ID` to `grdData`; decide whether grounds rows written under `stonedesk` need migrating | fourth | `docs/2026-10-30-cc-b77-routed.md` |
| K-1..K-3 | The three LOW findings from the b65 review | cody | same doc |
| N-2 | Review of the b76 fix (Tier A) | cody | unchanged |
| N-5 | `payload.app_id` and other request-field-conditioned branches not swept | cc | `grep -n "payload.app_id" api/sd-data.js`, then read each branch |
| F-1, L-1, C-3..C-5 | carried over | see b74 and b75 | unchanged |

## 3. Addendum at push time

- **sairngrounds.html had to stay declared until its own revert landed.**
  Removing the declaration in the same push as the revert made the revert
  FOREIGN to cc, and the path-scope gate refused it.
  - The revert landed with the declaration kept, at `d689dc59` on origin.
  - This push then removes it. The manifest diff against HEAD was 3 lines,
    measured before writing: note amended, entry removed.
- **Generated docs regenerated with their own tools:** `docs/MASTER-PLAN.md`
  and `docs/traceability-matrix.md`.
- **Defect register:** the b77 record re-seats by subject. `defect_register.py
  --check` reports OK for 807 records.
