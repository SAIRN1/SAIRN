# SAIRN handoff — hank b58 — 2026-10-28

**Subject:** the idleCompaction check, the callers' 502 run in a sandbox on the deployed code, the ALF audit owner
recovery SQL, the SC-PINNACLE-2026 trial and the legacy Stedi row, and the sandbox method applied to every other open
fail-open/closed item. This handoff was written before the report. Nothing is half-finished.

**Methodology concept:** *ship the provenance, not the bytes.* A deployed-sha check is only as strong as the proof that
the bytes run are the bytes deployed. So the sandbox fetches the exact-sha tarball itself and hashes the whole api/
tree against the git blobs. The network then goes to deny-all before any driver runs. No file passes through the
model, so a 1.4 MB file costs the same as a 5 KB one. A green run is not trusted until a local mutation of the same
guard turns that arm red.

## 1. PUSHED STATE — NOT FORCED
- The commit holds: the two SQL files, the three b58 documents, and the chain-log entry appended to
  `SAIRN-ACTIVE-WORK-hank.md`. Re-derive the tip from `git log origin/main` after the push.
- No app code changed this batch.
- **Untracked files I did not create** are present in the clone root and were left uncommitted: `conflict_excerpt.txt`,
  `full_conflict.txt`, `resolve_conflict.py`, `schema_snapshot_raw.json`, `dir`, and `.claude/settings.json*.bak`. The
  owner should claim or remove them.

## 2. CLAIMS HELD
- `sql` (commit 6660a0b6e). It is released after the push, in the same batch.

## 3. THE ITEMS
1. **idleCompaction — RESTORED.**
   - The key was **absent** from `C:\Users\marsh\.claude\settings.json`.
   - Added `"idleCompaction": false` at the top level. Every other key is byte-equal as parsed JSON; checked with
     json.load before writing.
   - Backup: `settings.json.bak-hank-b58`.
   - This is a standing first-action check every batch.
2. **The callers' 502 — CLOSED.**
   - Run in sandbox `sbx_kbNaQRph30Od3GYOQRNAYm2vMXLA`, deny-all, on prod `dpl_4D9LaKrr79HfojJQ9tVqEuen9qxL` @ `098de0716`.
     The 191-file api manifest matched inside the sandbox.
   - bridge.js push and the sd-data pre-gate, **16/16**:
     - unreadable or non-list 2xx → 502 ACTIVE_CHECK_UNREADABLE;
     - 500/503/403 → 502 ACTIVE_CHECK_FAILED;
     - zero writes or data reads on any refusal;
     - controls: active → 200, inactive → 403, 404 → proceeds.
   - Mutation control: 10 of 10 refusal arms red.
   - The api/ diff to the current prod sha `131d2f8e2` is 0 lines, so this result holds there too.
   - **One deviation, stated:** sd-data.js did not go through a subagent. The in-sandbox fetch made that unnecessary,
     and the verification is stronger: the whole api/ tree was hash-matched, not a chosen file list.
3. **`sql/alf-audit-owner-recovery.sql`.**
   - What it does: re-keys and unlocks `audit-owner` to a PIN that Michael generates and holds. It is an upsert, so
     nothing is deleted. It carries the PR 3.4 recoverability guard, a check that the placeholders were replaced, and
     the license-hash literal check.
   - **Why:** today the only usable owner PIN lives in this session's temp scratchpad, the same single point of
     failure as zz-audit-owner.
   - The live state today is healthy. Measured read-only:
     - audit-owner: active and unlocked;
     - zz-audit-owner: active.
   - Rehearsed against a temp-table copy: a locked audit-owner came out re-keyed and unlocked, the other 4 rows were
     untouched, and prod was untouched.
   - `employee_auth_guard_check` OK.
   - **Where the current audit-owner PIN lives:** the b51 scratchpad, in `alf_owner_pin.txt` under
     `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517\scratchpad\b51\`.
     The location only, not the value.
4. **`sql/sc-pinnacle-2026-trial-extend.sql`. MEASURED: the trial is not in the database.**
   - `license_keys` has no `trial_ends_at` column.
   - SC-PINNACLE-2026 is active, plan demo, with no subscription.
   - The expired-trial screen is `sairncode.html` checkTrialGate() (around line 3481). It counts 30 days from
     `localStorage['sc_trial_start']` in that browser, and it hides the app after sign-in.
   - So the file says no SQL can extend it, and gives the browser unblock step:
     `localStorage.setItem('sc_trial_start', String(Date.now()))`.
   - PART 2 is a guarded server-side exemption. It is a no-op today and was rehearsed live as a no-op.
   - **The legacy Stedi row is owned by SC-PINNACLE-2026 itself:** credential `default`, service `stedi`,
     ciphertext length 90, written 2026-08-23. `legacy_rows` = 1 and v2 = 0, re-measured today.
5. **The sandbox method on every other open fail-open/closed item:**
   - **W6** derive_charges, sandbox `sbx_paOfp1QNnJTQw5OFe3poAPyIS462` @ `131d2f8e2`: **9/9**. All four reads × unreadable
     or 500 → 502 READ_FAILED, with 0 writes. Mutation red.
   - **W2** claude.js + license.js, neither stubbed, sandbox `sbx_vEPUUZAlz4rbtwLa0ZI761IroOVN`: **9/9**. In the unset,
     observe and enforce modes, an unreadable or non-list licence → 502 LICENCE_UNREADABLE, with 0 Anthropic calls.
     Mutation red.
   - **The b51..b55 suites at the deployed sha:** 11/0, 9/0, 12/0, 6/0, 13/0.
   - With this, W1–W6, C1 and the callers have all been run on deployed code.

Evidence: `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517\scratchpad\b58\sandbox_evidence.txt`.
The drivers are `driver_callers.js`, `driver_w6.js` and `driver_w2.js` in the same folder.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| A1 | ALF audit owner PIN held only in a temp scratchpad | Michael | run `sql/alf-audit-owner-recovery.sql` with your own generated PIN, log in once, and record WHERE it lives in `docs/2026-09-29-alf-audit-licence-unusable.md` |
| S1 | Stedi backfill blocked by the client-side trial screen | Michael | browser step in the header of `sql/sc-pinnacle-2026-trial-extend.sql`, then re-save the Stedi key, then PART 3 should show legacy_rows = 0, then clear SD_AUTH_SECRET_PREVIOUS |
| S2 | durable exemption: demo licences skip checkTrialGate | Michael decides | if yes: a one-function change in `sairncode.html` (skip when the licence plan is demo), with a test |
| U1 | untracked files in the clone root, not mine | their owner | claim or remove them |
| T1 | an informal review of 45ba1d9f7, da19dd707, cf13093c8 | cc | unchanged |
| RS | pre-existing red api/ suites | owners | unchanged |

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
