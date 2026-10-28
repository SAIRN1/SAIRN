# fourth b62: root causes (2026-10-28)

All four findings were measured in this clone at `07e05929b`. Each section gives the cause, the evidence, and who owns the fix.

## 1. Orphan scrutiny rows (not fixed here: the write site is cc's and cc holds an active `platform` claim)

### Scale, measured

`docs/scrutiny-flags.json` holds 1,594 rows keyed to 704 commits. **1,053 rows (66%) key commits that are not on `origin/main`:**

| state | keys | rows |
|---|---|---|
| on `origin/main` | 276 | 541 |
| exists locally, not an ancestor (rebased away) | 97 | 262 |
| no such object in this clone (rebased in another clone) | 331 | 791 |

All 97 of the locally present orphan keys have a landed twin with the same subject. That is the rebase signature. The class is platform-wide; it is not just b61's 10 rows.

### Mechanism

1. `tools/sairn_push_gate_hook.py` (around line 2250, inside the scrutiny block) calls `exit_status_attributable.scrutiny_record(repo, <commit>, flags)` for every commit in the outgoing range. It does this during **pre-push**, before the remote has accepted anything, and writes straight into the tracked ledger.
2. If the push loses a race or a later gate refuses it, `tools/push_retry.py` `fold_scrutiny()` commits those rows into a bookkeeping commit. The rebase then rewrites every commit, and the next attempt writes a fresh set of rows for the new shas.
3. Nothing removes the old rows:
   - `fold_scrutiny()` runs `scrutiny_append_only()`, which forbids dropping a row.
   - The `scrutiny_record` docstring says *"`.githooks/post-rewrite` plus `tools/doc_sha_reseat.py` exist for exactly that"*. That is not true. `post-rewrite` re-seats only the defect register and the `REWRITE` documents in `doc_sha_reseat.py` (the open-work index, `CRITICALITY-TIERS.md` and `known-red-suites.json`). The scrutiny ledger is in none of its three lists, and its JSON `"sha"` values are not the backticked form that tool's `TOKEN` matches.

### Proposed fix at the write site (for cc, or for fourth on a go-ahead)

1. The gate writes rows to an **untracked pending store**, `.git/sairn-scrutiny-pending.json`, never to the tracked ledger.
2. At the start of every pre-push, and in `push_retry` before each attempt:
   - **promote** a pending row into `docs/scrutiny-flags.json` only when `git merge-base --is-ancestor <sha> origin/main` succeeds, which means the commit landed;
   - **drop** it when the sha is no longer reachable from any local ref;
   - otherwise **keep** it pending.
3. `post-rewrite` drops pending rows whose sha is an old sha in git's rewrite map.

**Effect:** the tracked ledger only ever contains landed commits, so the append-only rule is never broken, because an orphan never enters the ledger. **Cost:** a landed push's rows reach the tracked ledger one push later.

**The existing 1,053 rows need a separate cleanup decision.** The ledger is append-only, so the cleanup would be an annotation, not a deletion: the 97 local twins can be paired by subject, and the 331 missing objects cannot be resolved from this clone.

## 2. The pre-existing probe failures

### `tests/install_git_hooks_check_probe.py`: 1 arm. Owner: **cc** (`tools/install_git_hooks.py`)

**Cause.** The hook-fire test in `tools/install_git_hooks.py` points `core.hooksPath` at the real `.githooks` for the **whole** throwaway repo. The throwaway `git commit` therefore runs `.githooks/prepare-commit-msg`, which correctly fails closed: `tools/staged_conflict_marker_check.py is MISSING`. The commit is refused, `--check` reports COULD NOT TELL, and the arm fails.

**Reproduced here:**
- commit with the hooks in place: exit 1, with that message;
- the same commit with an empty hooksPath: exit 0.

**Fix.** Make the throwaway commit under `-c core.hooksPath=<empty dir>`, and set the real hooksPath only for the `push --dry-run`. Using `--no-verify` would not work, because it does not skip `prepare-commit-msg`.

### `tests/run_staging_discipline_probe.py`: 2 arms. Owner: **cody**

**Cause.** Section A of the probe assumes `tools/push_retry.py` contains **zero** breadth-staging calls. cody b31 (`c79d4e59b`, 2026-10-20) added `git('add', '-A')` at `push_retry.py:674`, inside the selftest's throwaway repo. The scanner is correct to count it; it is a real call. The probe's fixture assumption went stale.

**Fix, either of:**
- stage by name there: `git('add', '--', SCRUTINY_FILE)`;
- or pin section A to a revision of `push_retry.py` from before `c79d4e59b`.

Note that `tools/push_retry.py` is also in fourth's `assigned_overrides`, so fourth could take this if it is routed here. It was left alone because the dispatch limits fixes to docs/.html.

## 3. Reseat collision `f9a4e5a0` / `5bb0950a`: RESOLVED in b62

**Cause.** Two register records are identical in every field apart from `commit`. `f9a4e5a0032b` is not an object at all; it is a pre-rebase citation, added in `69ca56e48`/`5e4c7d023` (b7). hover2's b20 ruling had already named it.

**Why it stayed open for 15 days.** `defect_register.py --supersede f9a4e5a0032b --by 5bb0950a51b6` refuses with "2 records match the survivor sha". hover2's own ruling record is also keyed at `5bb0950a51b6`, and the command's `find()` matches on sha alone, so more characters cannot disambiguate it.

**Applied.** I set `superseded_by: 5bb0950a51b6` on the stale record. I used the register's own `reseat_base()` and `superseded_survivor()`, and picked the single survivor whose content is identical, which is the condition `--supersede` checks.
- `--reseat` now reports "nothing is outstanding: 5 record(s) are SUPERSEDED".
- `--check` reports OK, 760 records.
- Nothing was deleted.

**Tool gap, for the register tool's owner (cc):** `--supersede` should fall back to the content-identical record when the survivor sha hosts more than one record.

## 4. Why `push_timeout_guard` has never been driven by a real `timeout … git push`

**What denies it.** The denier is **Claude Code's auto-mode permission classifier**, not a static rule and not a SAIRN hook:
- `~/.claude/settings.json` has `permissions.defaultMode: "auto"`.
- No deny rule in the three settings files matches `timeout N git push`. They deny only `--force`, `-f`, `--delete`, `--mirror`, `*master*`, `reset --hard`, clean and checkout.
- b61's denied command was a compound scratch script: `git init`, a bare remote, a hook, then `timeout 60 git push`. The classifier judges the whole command text. It denied a similar scratch-repo command again in b62 (`rm -rf` plus `git config` in the scratchpad).

**Minimum permission that would let a later batch verify it.** One exact allow rule in `.claude/settings.local.json` for one fixed, tracked driver. A driver mode inside fourth's own file is the narrowest:

    "Bash(python tools/push_timeout_guard.py --live-drive)"

That mode (not built) would:
1. create a temp repo and a temp **bare** remote, with no network and never `origin`;
2. point its hooksPath at a one-line hook that runs `push_timeout_guard.py --pre-push`;
3. run `timeout 60 git push` through `subprocess`;
4. pass only if the push is refused **and** the bare remote's ref is unchanged;
5. run a control arm, the same push without `timeout`, which must succeed.

Two conditions apply:
- **Run it with `run_in_background`.** The Bash tool's own timeout is a second killer, and the guard cannot see it; this is already a named blind spot.
- **Nothing broader is needed, and nothing broader should be granted.** A wildcard such as `Bash(timeout *)` would allow exactly the hazard the guard exists to stop.

### Found while checking this (for Michael)

`.claude/settings.local.json` still **allows** `timeout 540 python tools/push_retry.py --loop --attempts 4/5/6` and `timeout 600 … --attempts 6`. push_retry pushes, so these are the forbidden shape. The b61 guard now refuses them at pre-push (it finds the `timeout` ancestor), so they no longer kill a gate. They should still be removed so nobody reaches for them. I did not edit them, because a permission file is Michael's.
