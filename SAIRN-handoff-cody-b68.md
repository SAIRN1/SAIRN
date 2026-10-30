# SAIRN handoff — cody b68 (2026-10-30)

**Citation discipline (item 5):** findings below are cited by record (`opened_at`), commit SHA or log hash. A line number is given only beside a quoted code anchor, because line numbers drift. R-11 has drifted once already (3104 → 3118), and the SDN sites moved +5 this batch.

## Committed / pushed state
- **Landed through the full gate.** The final SHA is in `SAIRN-report-cody-b68.txt`, measured after this file lands.
- **One rebase stop.** I had left my item-4 index edit uncommitted, and the loop refused to rebase over it. I committed it.
- **Two ledger conflicts** were merged by identity with `tools/sairn_rebase_resolve.py`: the register at 814 records and tier-a at 323. Register commit references were re-seated to the rebased SHAs.
- **Claims:** none held. fourth holds `stonedesk` (b70); my stonedesk change this batch is test-only (`tests/stonedesk_save_reentry.js`).

## 1. Done-line Stop hook (item 1): already in place, enforced by code, nothing to build
- **Built by cc b66** (`a367bd0c2`). My b66 fix `bea263709` closed the no-record gap.
- **Armed in ALL FOUR builder clones.** Each runs `.git/sairn-hooks/sairn_done_line.py --stop-hook` from `.claude/settings.local.json`'s `Stop`. Every armed copy is sha256 `7aa02c754b5b`, criteria `2026-10-29.cody-b66.1`, identical to the tracked file. Selftest 20/0.
- **It has already enforced my last three closes by code.**
  - b65: refused once, then the exact line passed.
  - b66 and b67: passed first time. The state file shows `refusals: 0` for the b67 line `done b67 1kzxmkdJ…`.
  - b67: driven end to end against the live state file (4/4 cases).
- "Same mechanism as hank's": it IS the same file in hank's clone.

## 2. b66 carryover (item 2): closed what was actionable, the rest with reasons
**Closed this batch.** All three were cc b76's verdicts on cody b65's records in `docs/tier-a-reviews.json`, routed to cody:
- **F1 on record `2026-10-29T19:12:48Z`: the case-sensitive licence fingerprint.** Fixed in `aadab627c` across all 13 guards.
  - Before asking, each guard compares the stored previous key to the one entered, trimmed and upper-cased. This follows `api/_lib/license.js`'s upper-case retry.
  - L5/L6 were RED in all 13 first; 78/78 now. licence_rekey_isolation is 70/70.
  - **The loosening was checked read-only:** `license_keys` has 31 keys, all upper-case, and 31 distinct after case-folding. No two licences differ only in case.
- **F1 on record `2026-10-29T19:34:54Z`: gcdMarkShotStart interleave.** Fixed in `569ab9bc4`. The start is snapshotted before the GPS wait and cleared only if unchanged.
  - GS1/GS2 were RED first; 48/0 now.
  - This also closes b66 carryover row 8.
- **F2 on record `2026-10-29T19:34:54Z`: the throwing-reset claim was unguarded.** Arm S4c added in `42b1050e1`. It is green on the shipped code and RED with the `finally` removed (driven, then restored). 18/0.
- **F2 on record `2026-10-29T19:12:48Z`: record hygiene.**
  - The 12-guard code is now covered by the b68 obligation.
  - R-12 (`de3547365`): `--open --range` on that commit says its changed lines name no Tier A resource, so **no obligation is owed by the gate's own rule**.

**b66 carryover table, row by row:**
| b66 row | status now |
|---|---|
| 1 Tier A review of b66 changes (record `2026-10-29T20:17:23Z`) | still OPEN, owner fourth. Its `files` list names only the TTL files, which is cc's F2 point. |
| 2 Tier A reviews of b65 | DONE by cc b76; its findings are closed above |
| 3 SDN write-unconfirmed | hank's (`api/`); row re-verified, see 4 |
| 4 deploy_verify chained push | fixed by fourth `c7d7e74d8`; my b67 verdict (record `2026-10-29T21:30:59Z`) routed the `$(…)` gap to fourth; no fix landed yet (`git log` since 21:30 is empty) |
| 5 exit_status_attributable silent suppressions | cc's; **no commit to that file since my b65 verdict** (record `2026-10-06T06:18:11Z`, `3cf3d5ec3e2c`); still open |
| 6 H2 rows | hover2's; corrected with hashes in b67 |
| 7 "scaffold carries the old guard text" | **CLOSED, the premise was wrong.** `~/.claude/skills/sairn-app-scaffold/SKILL.md` has NO licence-guard text. I wrote that row without checking. New apps copy a sibling's guard, and all 13 are now fixed. |
| 8 gcdMarkShotStart | CLOSED (`569ab9bc4`) |
| 9 standing re-entry checker | NOT DONE. It is a new checker, and the disciplines doc requires criteria locked against synthetic fixtures first (three shapes now: server await, device await, timer reset). That is a batch of its own; this batch went to the four reviewer findings, which were defects. |
| 10 older b64/b65 items | unchanged; see `SAIRN-handoff-cody-b64.md` rows 7-20 |

## 3. R-11 is stable (item 3)
- `sairndental.html:3118` is `dntCredWriting++;` and `:3119` is `try{rCredentials(null);syncResult=await sdnData('write','dnt_credentials',rec);}finally{dntCredWriting--;}`.
- **`git blame` puts both lines at `f4d8c29fa` (cody b65).** Nothing has touched them since. The 3104 → 3118 drift happened before b67 and has not moved again.
- CD4 is green (20/0). The live sairndental page is byte-identical to HEAD.

## 4. B67-SDN-WRITE-UNCONFIRMED is current (item 4); not mine to fix
- **Re-verified at HEAD `112b4120c`, `api/sd-data.js` blob `881804937a60`:** both sites are unchanged. They moved +5 to `:15881` and `:6767` after cc b77 `52b9ca3a3`.
- **The row is now anchored on the code, not the number:**
  - the generic limb's exact statement, which occurs once in the file;
  - the sdn_clients branch head. Its 200 expression occurs 3 times in the file.
- Table pipes in the quoted code are escaped (`&#124;`), and the pipe count was checked.

## 5. Live verification
- All 13 guard apps plus sairnmechanical are served byte-identical to HEAD (sha256 after CR strip). The 13 carry the new same-key check.

## Open, and the exact next step
| # | open item | owner | exact next step |
|---|---|---|---|
| 1 | Tier A review of the b68 changes (13-guard case check, grounds shot-start) | cc | discharge; attack point 1 is already measured (31 keys, no case collisions) |
| 2 | Tier A review of the b66 changes (record `2026-10-29T20:17:23Z`) | fourth | discharge |
| 3 | SDN write-unconfirmed (row `B67-SDN-WRITE-UNCONFIRMED-CODY-2026-10-30`) | hank | the b58 pattern, red-first |
| 4 | deploy_verify `$(…)`/backtick silent skip (record `2026-10-29T21:30:59Z`) | fourth | two red-first arms |
| 5 | exit_status_attributable suppressions (record `2026-10-06T06:18:11Z`) | cc | five red-first arms |
| 6 | Standing re-entry checker | cody | a batch of its own: criteria lock, then the tool |
| 7 | H2 rows (seq 813 hash `ed20a6b9…`, seq 1111 hash `94e2e6b8…`) | hover2 | as each row says |
