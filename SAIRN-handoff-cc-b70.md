# SAIRN handoff: cc, batch b70, 2026-10-29

**All six items are closed.** One is closed as "genuinely missing" and
flagged, which is item 3. Landed at `25aff5d0` (see the digest for the final
tip). No `--force`, no override, no skip.

| | |
|---|---|
| Claims | `platform` (b70), released with this handoff. |
| Context | see the digest's CONTEXT line (measured). |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\52164776-0b08-422d-94e1-7a56daf3eaaa.jsonl` |

## 1. The Tier A obligations cody flagged in b62: discharged

Read-only agents ran the reviews, and cc spot-checked the key citations.

**cody b58: mech WRITE_UNCONFIRMED. SOUND-WITH-GAPS (low).**
- The code is in `10e914b1` + `4a8920f5`. The recorded sha `9e37119c` is not
  in this clone.
- Can a real save return `[]`? No:
  - every path is a merge-duplicates upsert with return=representation, or a
    POST where a duplicate is a 409;
  - there is no PATCH, no ignore-duplicates and no trigger.
- Tests: 11 suites and probes, all exit 0.
- Ablation: removing the guard per resource failed that resource's arms.
- **Gaps routed to cody:** the MECH_RECORDS request shape is unasserted; the
  test's ablation temp file in `api/` is not gitignored.

**cody b61: sairnfreedom `sf_server_confirmed`. SOUND-WITH-GAPS (low).**
- The code is in `7ae231b4`. The recorded sha `01a24fad` is in no ref.
- Confirmation runs only after the failure guard (`:2048` →
  `:2057/:2058`). The set is keyed by resource + id and wiped on a licence
  switch.
- Tests: 7 suites, all exit 0. 3/3 script blocks pass `node --check`.
- **Gaps routed to cody:**
  - entries never expire;
  - a legacy device with no `SF_LIC_FP` skips the wipe;
  - D4c is regex-only, and three ablations survive it.

**Still open, not cody's:** hover b92 (`test_965`) waits on hover landing
the file.

## 2. The O7 push script: regenerated

The script cody meant is **cody's scratchpad `push_once.sh`**
(05129111…/scratchpad, 2026-10-28 17:31), not a tracked tool.

**Confirmed in its source:** derived docs are regenerated only inside
`if grep -q "whole-tree re-check not green"`, the pure-base-skip path. Two
consequences:
- in gate mode the full gate ran on stale docs, which is cody's b62 double
  refusal;
- `TOOLING-INVENTORY` was never regenerated at all.

**The regenerated block** is in `docs/2026-10-29-cc-b70-o7-push-script.md`:
- regenerate all three documents unconditionally after the rebase and
  BEFORE the skip decision;
- trade-off, stated there: a derived-docs commit may force a full gate,
  which is the safe direction.

**cody's file was not edited.** A scratchpad belongs to its session.

**`tools/push_retry.py` already does this**, at lines 1312 and 1391, with
hank b64's separate derived-docs commit. The recommendation is that cody
retire the script for it.

## 3. Live-block fixtures for the three new rules: GENUINELY MISSING (flagged)

`docs/2026-09-03-demo-credentials.md`, `tools/audit_licence.py`
`KNOWN_AUDIT_KEYS` and `sql/` were checked.

**StoneDesk.**
- `SD-AUDIT-2026` has **only an owner** credential (`sairn-demo-owner`).
- `sd_crm.read` needs owner, admin, sales and install. `exec_context.read`
  needs the same four.
- The older admin seeds were disposable (`stonedesk_verify_admin_seed.sql`)
  or on other licences.

**SAIRNdental.**
- There is **no dental audit licence**. `KNOWN_AUDIT_KEYS` has none, and the
  only dental credential is the `DNT-PINNACLE-2026` demo owner.
- `dnt_rollup.read` needs owner, frontdesk and provider.
- The 2026-08-27 tiering verification credentials were cleaned up after use.

**What the fixtures need:**
- admin, sales and install credentials on `SD-AUDIT-2026`;
- a dental audit licence with owner, frontdesk and provider credentials.

That means credential SQL, which needs the recoverability guard (CLAUDE.md
§3.4) and Michael's run. The fixture rows themselves can be generated from
`seed()` the way `sen_branches` was in b64, once the employee ids exist.

**Nothing was written to the database.**

## 4. CRLF cross-check of hank's, cody's and fourth's tools

An AST scan covered 256 `.py` files owned by hank, cody or fourth (60 with
an OWNER line, 196 derived). It looked for text-mode appends with no
`newline=`, and for `os.open` with `O_APPEND` but no `O_BINARY`, skipping
selftest and fixture functions.

**Result: 4 hits, none a log writer.** All are temp fixtures inside test
probes:
- `tests/claims/run_push_verify_probe.py:478/602/705` (cody);
- `tests/seam_check/run_delegation_probe.py:105` (fourth).

**Nothing to route.** No cross-owned file was touched.

## 5. Cause tags

`docs/recurring-bug-classes-2.md` **C4: a remedy gated on an unrelated
condition** (construction → automation script → the fix sits inside a
different decision's branch).
- Its occurrences are `push_retry.py` (2026-10-05) and cody's
  `push_once.sh` (b62, O7).
- The section carries this batch's tag table. O7 is the one fix; the rest
  were reviews and checks with no code change, and the section says so.
- The file is declared as cc's assigned b70 path.

## 6. OPEN

| Item | Owner | Next |
|---|---|---|
| Apply the O7 block, or move to `push_retry.py` | cody | per `docs/2026-10-29-cc-b70-o7-push-script.md` |
| b58/b61 test gaps | cody | as routed |
| Credentials for the three live blocks | Michael | `SD-AUDIT-2026` admin/sales/install; a dental audit licence with owner/frontdesk/provider |
| hover b92 obligation | cc | after hover lands `test_965` |
