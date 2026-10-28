# SAIRN handoff: cc, batch b60, 2026-10-28

**Items 1, 3 and 4 are closed. Item 2 did NOT reproduce the truncation.** Its
open step is named below. Also found: the root cause of b59's `core.bare=true`
event, and a second leak from the same cause (this clone's commit identity).

- Landed: `58801d4c` (fix), `c99ca905` (register record), `b6f03541` (manifest
  declaration), `6b89b158` (register re-seat). The clone reads 0 0 against
  origin. Every changed blob is identical on `origin/main`.
- No product code changed, no `--force`, no override, no skip.

| | |
|---|---|
| Claims held | none (the `tools` claim is released with this handoff) |
| Context | 21.1% of 1,000,000, measured |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\332ab89b-94aa-4880-931e-d17413636dfc.jsonl` |

## 1. Item 1: the `core.bare` probe. Root cause found; the fix goes beyond a finally

**The finally was not the cause, and on its own it could not have fixed this.**
The probe that writes it is `tools/copy_exactly_gate.py`'s blind-lock fixtures.
They run on every pre-push, and their first line is `git -C <tempdir> init`.

- git exports `GIT_DIR` to a pre-push hook. When the push comes from a linked
  worktree, that path is ABSOLUTE.
- `GIT_DIR` takes priority over `-C`, so the `init` re-initialised the REAL
  repo. It wrote `core.bare=true` and `user.name`/`user.email=fx` into the
  shared `.git/config`.
- Measured in a scratch repo (`scratchpad\gitdir_hyp2.py`). A real
  `push --dry-run` from a worktree flips `core.bare` from false to true.
- **It does not depend on a kill.** The ablation shows `core.bare=true` after a
  run that completed cleanly too. After that the fixtures fail, so **every push
  from a worktree was also refused as COULD NOT RUN.** The b59 low-memory kill
  was incidental.
- A push from the main clone exports a RELATIVE `GIT_DIR`, which resolves
  inside the temp dir. That is why this only ever hit worktrees.
- `tests/push_gate/check8_probe.py` recorded this exact corruption on
  2026-10-06 (`bare = true`, `email = fx@example.invalid`). It fixed itself by
  moving to a clone, without naming the writer.

**The fix:**
- `.githooks/pre-push` unsets `GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
  GIT_COMMON_DIR` before the first gate runs.
- `copy_exactly_gate.run_fixtures` drops the same variables for the fixture
  run.
- It also restores `core.bare` in a `finally` if the value moved. That is the
  net. **A finally does not run on a hard kill** (TerminateProcess or an OOM
  kill), so surviving a kill is the job of the env drop.

**The test, `tests/run_core_bare_kill_probe.py`: 10/10.**
- It runs the real gate under a worktree's `GIT_DIR`.
- It hard-kills the gate at 15, 35, 55 and 75% of the run, and checks each time
  that the gate was still running when killed.
- `core.bare` stayed false every time.
- A teeth arm proves the observable can see the leak.
- **Ablation:** the same probe run against the unfixed gate at HEAD scores
  4/10, with `core.bare=true` on every arm.

**End to end:**
- A real `git push --dry-run` from a worktree of THIS clone ran the full gate
  chain under the cap. Result: rc 0, 102 s, peak 384 MB.
- The shared `.git/config` sha256 was identical before and after.
- The dry-run created no remote ref.

## 2. DECISION NEEDED (Michael): this clone's commit identity is a leak

**The record:**
- cc's commits were authored "Michael Dibert" (global identity) up to
  2026-10-27 11:18.
- From 12:06 they are authored "fx \<fx@example.invalid\>".
- That is the identity `_fx_repo` writes. It arrived with the b59 worktree
  replay at about 12:04.
- b59 restored `core.bare` and missed this.

**I did not change it,** because changing it changes the authorship of every
future commit.

**One conflict to resolve:** `tests/run_committer_identity_probe.py` says
fx@example.invalid was "set deliberately and by no probe". That may be true of
another clone. It is not true of this one.

- **To restore:** `git config --local --unset user.name` and
  `git config --local --unset user.email`.

## 3. Item 2: CMD replay of the 11:02 patch apply. NOT reproduced

**Setup:**
- Run in `git clone --local` at `d48125f9`, with the hooks of that time. It was
  a clone and not a worktree, because a worktree shares config (§1).
- Every run went through `capped_run.py` (2000 MB, 600 s) and then
  `logged_exec.py`, so the argv and the tree delta are on record.

| Run | What it is | Result |
|---|---|---|
| C1 | H1's README sequence in CMD: `git apply --check`, `git apply`, `git add`, `git commit -m "<recorded subject>"` | Reproduces commit `c9c0a5ae` **blob for blob** (5ab4c392 / b9f36af4) and its author. Push gate untouched at 307,268 bytes. No `cd` or `git` files. |
| C2 | The same lines pasted with a leading `> ` (a quoted block) | Creates **empty `cd` and `git` files in the clone root**, which is 2 of the 3 artefacts. No commit, gate untouched. |
| C3 | A bare `> tools\sairn_push_gate_hook.py` line in CMD, with `/` and with `\` | "The syntax of the command is incorrect"; **the file is NOT truncated**. A shape built to match, which did not. |

**Conclusion:**
- The prescribed command does not truncate the gate.
- The quote-prefix paste explains `cd` and `git`, but not the truncation.
- The commit at 11:02:39 proves a correct apply happened before the 11:04
  artefacts, so a quote-prefixed paste would have to be a second paste, after
  the commit.
- **The root cause of the truncation is still not established.**
- **Next step (Michael):** find out whether a second block was pasted into CMD
  at about 11:04 (CMD history is lost once the window closes). If it was,
  paste it into a `.cmd` file and run it through
  `capped_run.py -- python tools/logged_exec.py -- cmd /d /c <file>` in a
  `--local` clone.

## 4. Item 3: the cap, as a tool. `tools/capped_run.py`

`python tools/capped_run.py --mem-mb N --timeout S -- <cmd>`:
- **The cap is set up front**, and `--mem-mb` has no default.
- **On Windows** it runs the command in a Job Object, with a job-wide memory
  limit and KILL_ON_JOB_CLOSE. The runner puts itself in the job first, so
  every child is inside the job from its first instruction.
- **Elsewhere** it uses `RLIMIT_AS`.
- **Exit codes:** 4 when the memory cap is reached, 5 on timeout, and 2 with the
  command NOT run if the cap cannot be applied.
- **Fixtures 5/5**, both directions: 700 MB under a 256 MB cap is refused and
  the runner survives.

**The rule:**
- Every incident replay runs through this tool.
- Every replay runs in a `git clone --local`, not in a linked worktree.

`logged_exec.py` now also records the tree delta (path, status and size). That
is what caught C2's two 0-byte files.

## 5. OPEN

| Item | Owner | Next step |
|---|---|---|
| The truncation root cause | Michael, then cc | Was a second block pasted at about 11:04? Replay it as §3 says. |
| The identity leak in this clone | Michael | Decide whether to unset (§2). |
| Other clones and worktrees | each owner | Any clone that pushed from a worktree before `58801d4c` may carry `core.bare`/fx. Check with `git config --local --list`. |
| `tests/run_copy_exactly_gate_probe.py` | cc / cody | 0/1, "the harness cannot reach the gate the way it assumes". **It fails the same way at HEAD before b60**, so it predates this batch and is not caused by it. |
| Carried | hank / fourth / H1 | the b58 SAIRNlegacy findings; the b56/b57 StoneDesk findings; H1's b85 patches |
