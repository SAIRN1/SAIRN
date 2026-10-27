# SAIRN handoff: cc, batch b59, 2026-10-27

**Items 1, 2, 4, 5 and 6 are closed. Item 3, the root cause, is NOT
established.** Its open step is named below.
- Landed: `69d381cd`, the gate self-integrity check and `logged_exec.py`,
  through `tools/push_retry.py --loop`. The clone reads 0 0 against origin.
- No product code changed, no `--force`, no override.

| | |
|---|---|
| Claims held | none |
| Context | about 81% (see the digest's CONTEXT line) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

## 1. Item 1: `f413c5ea` against H1's b86 spec — EXACT MATCH

**The spec** is H1's tracked patch
`.claude/skills/sairn-hover-auditor/references/pending-patches/b86-allowed-entries-scope-gate-and-audit.patch`
(blob `6a464c6b`), as described in `SAIRN-handoff-H1-b86.md` §1.

**The check:**
- I piped the blob straight into `git apply`, on a throwaway worktree at the
  commit's parent `3e8a5215^`.
- The result is **blob-identical** to the commit for both files:
  - `tools/hover_auditor_scope_gate.py` = `5ab4c392`;
  - `tools/hover_separation_audit.py` = `b9f36af4`.
- The commit touches **only** those two files (+50 / −2). **Nothing extra.**

**A note on method.** A first attempt used a copy I had retyped through the
Write tool. That copy lost two single-space context lines, so its patch hash
differed. I discarded that check and re-ran it on the tracked blob itself.

**This resolves b58's DECISION-NEEDED.** The commit is H1's patch, applied
verbatim.

## 2. Item 2: already on origin

- `f413c5ea` became `3e8a5215` on rebase, and it is on `origin/main`.
- `git log origin/main -- tools/hover_auditor_scope_gate.py` shows it as the
  latest commit to that file.
- **It was pushed in b58, as part of cc's outgoing range, before this
  verification.** I am saying so rather than presenting the push as done in
  b59. H1 can proceed with its b85 patches.

## 3. Item 3: the root cause — NOT established

**The replay.** I replayed cc's own 11:03 command shape in a throwaway
worktree:
- the same commit, `pull --rebase` and `tee | grep "\->"` pipeline;
- `git push --dry-run` to a throwaway ref, so the full pre-push chain ran and
  nothing could land.

**The system killed it for low memory**, during the gate run. I have not
restarted it.

**What it showed before it died:**
- The gate file stayed at **307,268 bytes**.
- **No `cd` or `git` file was created.**

That weakens b58 hypothesis 2, that a hook mis-parsed cc's command. It does
not eliminate it, because the run did not complete.

**The patch-apply command at 11:02–11:04 was not cc's,** and it was never
captured. That is the reason for item 5.
- **Exact next step (Michael):** paste the command line used to apply H1's
  b86 patch in SAIRN-cc at 11:02, including the shell it ran in
  (PowerShell, cmd or bash).
- With that text, a replay in a worktree settles it.

**A second integrity event this batch, now restored.** After the killed
replay, `core.bare` was set to `true` in this clone's shared `.git/config`
(config mtime 12:04:58).
- Every work-tree command failed, with "this operation must be run in a work
  tree".
- I set it back with `git config core.bare false`. Status, gate hash and push
  are all normal again.
- **This is a known class.** `tools/bare_run_write_check.py` already records
  "how core.bare=true reached a live clone".
- Most likely a sandboxed probe in the pre-push chain flipped the shared
  config of a worktree and was killed before it could undo the change. A
  worktree shares its config with the main repo.
- Not root-caused this batch.

## 4. Item 4: the fix — a gate self-integrity check, in `.githooks/pre-push`

**The redirect bug itself was not found** (§3), so there is nothing to fix at
the source yet. The defensive fix landed:
- Before any gate runs, each of `sairn_push_gate_hook.py`,
  `register_feed_gate.py`, `copy_exactly_gate.py` and
  `hover_auditor_scope_gate.py` must be **non-empty and hash-identical to its
  HEAD blob**.
- Otherwise the push is refused, exit 1, with both hashes printed.
- It fails closed when the blob is absent or a hash cannot be computed.

Driven in a throwaway worktree:

| Arm | Result |
|---|---|
| clean | passes, rc 0 |
| gate emptied | REFUSED, rc 1 |
| gate edited | REFUSED, rc 1 |

A real push has since gone through the check: `69d381cd` landed.

## 5. Item 5: the methodology, as a tool — `tools/logged_exec.py`

`python tools/logged_exec.py -- <argv>`:
- **logs** the full argv, cwd and time to `.git/sairn-exec-log.jsonl`
  **before** running;
- **refuses** any shell-operator argument (`>`, `>>`, `2>`, `|`, `&&`, `;`,
  `<`), because it runs **without a shell**;
- **exits 3** if a gate or hook file changed during the run.

Fixtures are 8/8. A `>` argument is refused with rc 2 and no file is
created. **The rule:** every patch-apply or hook-touching command goes
through this wrapper.

## 6. OPEN

| Item | Owner | Next step |
|---|---|---|
| The truncation root cause | Michael, then cc | Provide the 11:02 patch-apply command line. cc replays it in a worktree through `logged_exec.py`. |
| `core.bare=true` recurrence | cc | Find which pre-push-chain probe sets the shared config inside a worktree. Make it set and restore in a `finally`, or use a non-shared repo. Extend `bare_run_write_check.py` to cover it. |
| The replay that was killed | cc, when asked | Re-run `scratchpad\replay59.sh` once memory allows; it is not restarted by default. |
| Carried | hank / fourth / H1 | the b58 SAIRNlegacy findings; the b56/b57 StoneDesk findings; H1's b85 patches |
