# SAIRN handoff — hank b59 — 2026-10-28

**Subject:** the ALF recovery SQL is now run-ready (b58 shipped placeholders), the methodology rule from that failure,
and a check of this clone's git config for the cc-b60 leak shape. This handoff was written before the report. Nothing
is half-finished.

**Methodology concept (standing from b59):** *the file that ships is the file that passed.* After writing any SQL
for handoff, re-read the LITERAL file. After the push, read the committed blob, `git show origin/main:<path>`, and
confirm three things: it has no placeholders, its literals are well-formed, and any credential verifies against
values read back from that blob. Any rehearsal is built mechanically from that literal file. It may only rename the
table and strip begin/commit; it never substitutes values. Recorded in memory as `shipped-file-is-the-file-that-passed`.

## 1. PUSHED STATE — NOT FORCED, LANDED
- `b676e7e79` fix(sql, hank b59), `38d7553cb` register record, `9c6c1c5f5` claim release — all on origin/main and
  authored `mikied68@gmail.com` (see item 3).
- These three b59 documents are in a docs-only commit after this file is written.

## 2. CLAIMS HELD
None. `sql` was claimed (40bd38bc4) and released (9c6c1c5f5).

## 3. THE ITEMS
1. **`sql/alf-audit-owner-recovery.sql` — RUN-READY.**
   - Real values from `hashPin()` were written into the file itself. The 8-digit PIN is held only in
     `C:\Users\marsh\Documents\SAIRN-hank\.git\sairn-alf-audit-owner-pin`, which sits inside `.git` and is never
     committed. It was never printed.
   - Checks on the literal file, then again on the origin blob (sha256 `12f588a7…`, identical):
     - 0 placeholders;
     - the hash is 128 hex characters and the salt 32;
     - the guard values equal the insert values;
     - the PIN verifies against the values read back from the file, and a wrong PIN is rejected.
   - Re-rehearsed on a temp table built mechanically from the literal file:
     - with audit-owner deliberately locked first, it came out re-keyed (salt `f472b006`) and unlocked;
     - the other 4 rows kept the same hash as prod;
     - prod's audit-owner was untouched, its updated_at still 2026-10-22.
   - `employee_auth_guard_check` OK.
   - **Stated risk, also in the file header:** the repo is public. This hash of an 8-digit PIN can be attacked
     offline, past the lockout. That is acceptable only on the synthetic audit licence. Re-key after use. b51's
     file had the same exposure.
   - Prod is unchanged by Michael's aborted run: audit-owner updated_at is still 2026-10-22.
2. **Why the b58 rehearsal and the real run diverged.** This is not quite the "real values tested but not written"
   shape:
   - b58's rehearsal ran on a script-made copy, with dummy hex (`repeat('a',128)`) substituted and the table renamed.
     The SQL that passed was never the SQL that shipped.
   - The "guard check OK" was `employee_auth_guard_check`, a static lint for the recoverability marker. It cannot
     see an unreplaced placeholder.
   - The generator line was run once, only to check output lengths, and its values were discarded.
   - The digest said "rehearsed" without saying "needs an operator substitution step".
   - Recorded in the defect register (b676e7e79, user-report, moderate, three factors, recurrence open: no push-time
     lint yet refuses a placeholder token in `sql/`). The standing rule is in memory.
3. **Git config: the LEAK WAS PRESENT.**
   - `.git/config` carried `user.email=fx@example.invalid` and `user.name=fx`. Those are `copy_exactly_gate.py`
     `_fx_repo`'s fixture identity: it ran from a linked worktree whose exported absolute GIT_DIR overrode `-C`.
     This clone has 10+ linked worktrees under Temp, including my `scratchpad\b51wt`.
   - `core.bare` was already false. GIT_DIR is not set in this shell.
   - **Fixed:** the local user.email and user.name were unset, and the global identity Michael Dibert
     <mikied68@gmail.com> now applies. Verified with `git var GIT_AUTHOR_IDENT` and on every b59 commit.
   - Backup of the old config: `...\scratchpad\b58\git-config-before-b59.txt`.
   - cc's code fix (58801d4c7, which drops GIT_DIR for the fixtures and restores core.bare in finally) is in this
     clone after the pull.
   - **Extent, measured and NOT rewritten:** 148 commits on origin/main since 2026-10-18 whose subject names hank
     carry the fx identity, b58's a93a74cb7 among them. Rewriting would need a force push, so they stay.
   - Also seen and not touched: `SAIRN-cody` has `fx@local` and `SAIRN-fourth` has `fx@example.invalid` in their
     local config. Those clones are their owners'.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| A1 | run the recovery SQL | Michael | run `sql/alf-audit-owner-recovery.sql` as-is; expect the NOTICE "audit-owner re-keyed and unlocked"; take the PIN from `.git\sairn-alf-audit-owner-pin` into your password manager, delete that file, and log in once via `/api/alf-auth` |
| A2 | the public hash exposure | Michael / hank | after A1's verification is done, re-key again with a fresh PIN if the licence stays in use |
| L1 | no push-time lint for `__X__` placeholders in `sql/` | hank, if wanted | add an arm to `tools/employee_auth_guard_check.py` or a sibling gate (not done: tool scope) |
| G1 | the fx identity in the cody and fourth clones' local config | cody, fourth | `git config --local --unset user.email` and `--unset user.name`, then check `git var GIT_AUTHOR_IDENT` |
| S2 | demo licences skipping checkTrialGate (b58) | Michael decides | unchanged |
| U1 | untracked files in the clone root that are not mine | their owner | unchanged |

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
