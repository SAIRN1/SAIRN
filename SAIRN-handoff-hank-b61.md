# SAIRN handoff — hank b61 — 2026-10-28

**Subject:** post-restart reorientation after an emergency machine restart. Reconcile b60, push anything unpushed,
re-read the shipped blobs on origin, and run an fx git-identity sanity check. No code changed this batch.

This handoff was written before the report. Nothing is half-finished.

## 1. RECONCILIATION — the dispatch premise did not hold
- The dispatch said 5 commits were ahead of origin (S2, #1274, L1, bookkeeping, fx-identity). **Measured after
  `git fetch`: 0 ahead, 28 behind.**
- All b60 commits were already on origin/main before the restart: `414d26351` (S2), `cdf71e894` (#1274),
  `995e53c9a` (L1), `bce658193` (bookkeeping), `8c2607420` (b60 docs). The claim releases were on origin too.
- **There is no fx-identity commit.** b60 item 5 was a check, not a commit. `git log --all --grep=fx` finds only
  cody b57 `e31869242` and cc b60 `58801d4c7`, neither of them hank's.
- The Drive handoff `SAIRN-handoff-hank-b60.md` (id `1qds70-gaFXfLDtkdHPPmUGTr21h2eWpJ`) matches the local one. Drive
  has one extra line, "These docs: `8c2607420`, LANDED", which is confirmed.
- **The fetch/rebase/push retry (step 2) was therefore not run.** There was nothing to push. Local main was
  fast-forwarded to `80d753ef1`.

## 2. LITERAL ORIGIN BLOBS (at origin/main `80d753ef1`)
- 19 files were touched by the 5 b60 commits.
  - 12 are byte-identical at origin/main to the b60 tip.
  - 7 have changed since b60. All 7 are shared ledgers or derived docs that other sessions append to: MASTER-PLAN,
    TOOLING-INVENTORY, the defect-density register, the path manifest, tier-a-reviews, the traceability matrix, and
    tooling_inventory.py.
- My b60 entries are still present at origin: the register has `cdf71e894bf3` ×1, and tier-a has `cdf71e894` ×1.
- `tools/sql_placeholder_check.py --ref 80d753ef1 --all`: **exit 0, 310 files read as committed blobs.**
  - No undeclared placeholder.
  - `sql/backup_reader_role.sql:96,98` were reported NOT RUN-READY. Both are declared operator input, as b60 recorded.
- A marker grep over the non-SQL b60 blobs (sc-auth.js, the 2 api tests, the b60 hunks of sd-data.js and
  sairncode.html) found 0 hits.
- One method note: running the tool from an extracted copy fails CLOSED (exit 2), because it resolves git from its own
  location. It was run from the clone with `--ref`, after confirming the clone's tool blob equals origin's.

## 3. FX GIT IDENTITY (this clone)
- There is no local `user.*`. The identity comes from global `~/.gitconfig`: `Michael Dibert <mikied68@gmail.com>`.
- `core.bare=false`. `GIT_DIR`, `GIT_AUTHOR_EMAIL` and `GIT_COMMITTER_EMAIL` are all unset.
- `git var` gives the author and the committer as mikied68.
- `tools/committer_identity_check.py` exited 0 (CLEAN). It found 29 probe identities in tests/, and none is reachable.
- `idleCompaction: false` is still set in `~/.claude/settings.json:302`.

## 4. METHODOLOGY
- No unlabeled exit 1 occurred this batch.
- The two exit-2 results (the placeholder tool run from an extracted copy, and context_verify with an undeclared
  window) both printed their reasons, so neither was ambiguous. No retry was needed.
- **The context window is 1,000,000, as Michael corrected.** It was first declared 200,000 as an assumption, which
  gave a CONTEXT figure overstated by 5x. It was re-declared with `--provision-window 1000000` and re-measured: 10.5%,
  105,243 tokens.
- **The first b61 push was refused twice by a ref-lock race.** Origin moved while the gate ran. Both refusals were
  labelled (`cannot lock ref ... expected <old tip>`), not unlabelled. Per the bounded-retry rule it stopped, and
  Michael authorised one more fetch, rebase and push.

## 4b. THE PUSH RACE, FIXED IN THE TOOL (Michael's third b61 dispatch)
- **The race:**
  - Three bare-`git push` attempts were all refused with `cannot lock ref` after the gate PASSED.
  - origin moved during each gate run. This is the same class as cody's b53–b56 (C1).
- **The fix is in `tools/push_retry.py --loop`.** It is the durable form of cody b56's scratchpad `push_fast.sh`.
  - After a full-gate pass is lost to a race, the next attempt fetches, rebases and re-compares the outgoing
    `git patch-id --stable` set.
  - It skips the gate (`--no-verify`) only if all three hold:
    1. the patch-id set is unchanged;
    2. the incoming commits touch none of our files;
    3. the incoming commits touch none of the gate's inputs (CRITICALITY-TIERS, the gate hook, `.githooks/`).
  - Anything unreadable gets the full gate.
  - Every skip is a `docs/BYPASS-LOG.jsonl` row.
  - The default is 5 attempts.
- **A pre-existing break was also fixed:** `--selftest` was crashing with a TypeError before this batch.
  - The cause: `79c4f10cf` added `timeout=None` to the push call, and the selftest's git stub took no kwargs.
  - It now passes all arms, including 15 new C1 arms.
  - 4 mutants are red: no patch-id compare, no overlap check, a skip armed after a gate refusal, and a skip never armed.
- **`docs/recurring-bug-classes-2.md` C1:**
  - adds the hank b61 occurrence;
  - closes the "skip is in a scratchpad script" item;
  - records the standing pattern: all 4 build agents push via `push_retry.py --loop`.
- **Finding for the identity owner (G1):** `79c4f10cf` landed on origin today authored `fx <fx@example.invalid>`. A probe
  identity is still committing in some clone. This clone is clean, and that commit is not hank's.
- **BLOCKED ON cc: `python tools/push_retry.py --loop` must be added to the shared builder allow-list by cc, who owns
  it, before any agent can use it.**
  - The auto-mode classifier denied hank's run of it, without a reason. The likely cause is the `--no-verify` path.
  - hank did NOT add it to the list.
  - Until it is added, pushes stay on plain `git push` (full gate, racy).
- **Residual, not fixed:** a skipped push does not re-run the whole-tree checks against the new base. The fold step does
  regenerate the derived docs after each rebase. Condition 3 bounds the risk but does not remove it. The real fix is
  gate duration or a merge queue (C1).

## 5. CLAIMS HELD
`tools` (push_retry C1). It is released after the push lands.

## 6. OPEN, AND THE EXACT NEXT STEP (carried from b60, unchanged)
| # | open | owner | next step |
|---|---|---|---|
| T1 | Tier A review of cdf71e894 (#1274) | cc | `tools/tier_a_review_gate.py --discharge hank <opened_at> "<verdict>"` |
| P1 | the SAIRNcode trial gate is client-side only | Michael decides | a server-side trial check in `api/sc-auth.js` if a real paywall is wanted |
| R1 | the readiness presence signal for coordinator/scheduler | Michael, only if wanted | keep it, or suppress it |
| A1 | run sql/alf-audit-owner-recovery.sql (b59) | Michael | unchanged |
| G1 | the fx identity in the cody and fourth clones | cody, fourth | unchanged |
| U1 | untracked files in the clone root that are not mine | owner | unchanged |

## 7. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\58897a7d-eff3-428b-8fec-18274a858ae9.jsonl
