# HANDOFF — fourth / ted, batch b62, 2026-10-28

**READ THIS FILE ONLY.** It is the whole state.
- **Landed:** items 3 and 5, through `a3efe3dab`, with no force and no gate skip.
- **Root-caused, not fixed:** item 1, because the write site is cc's and cc holds a live `platform` claim. **Decision needed.**
- **Root-caused, owners named:** item 2. Item 4 is documented.
- Wrapped at 21.8% real context.

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\b6e28c25-eaee-4611-aeb3-d94f0198d47f.jsonl`
**Full detail:** `docs/2026-10-28-fourth-b62-root-causes.md`, one section per item.
**Scratchpad:** `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\b6e28c25-eaee-4611-aeb3-d94f0198d47f\scratchpad\`
- `supersede62.py`: the register write.
- `git-config-before-b61-identity.txt`: the identity backup.

## 1. STATE

| item | sha | state |
|---|---|---|
| 1 orphan scrutiny rows | none | **ROOT-CAUSED; fix designed, NOT applied.** It needs a go-ahead (section 2) |
| 2 install_git_hooks_check (1 arm) | none | root cause reproduced; owner **cc** (`tools/install_git_hooks.py`) |
| 2 staging_discipline (2 arms) | none | root cause found; owner **cody** (the stale probe fixture) |
| 3 reseat collision f9a4e5a0/5bb0950a | `40698b8ef` | **RESOLVED.** `--reseat` reports nothing outstanding; `--check` OK, 761 records |
| 4 timeout guard, never driven live | `1c10fa015` (doc §4) | the denier is identified, and the minimum permission is written as one exact allow rule |
| 5 claim-state recheck on every push | `d7e8f5d9a`, `a3efe3dab` | **live**: it ran on this batch's own landing push ("4 commit(s), 7 watched path(s) … no overlap") |

Earlier the same day, the b61 addendum (post-restart) landed as `0f93cad83`. It unset the `fx` local identity; commits now carry Michael Dibert.

## 2. DECISION NEEDED: item 1

**The fix is at the write site, and it is not mine.**
- The rows are written by `tools/sairn_push_gate_hook.py` (around line 2250) through `exit_status_attributable.scrutiny_record`.
- Both files are cc's (`tools/`), and `push_retry.fold_scrutiny` is involved too.
- cc held an active `platform` claim the whole batch: b66, the PreToolUse deny hook and its presence check.
- The memory rule is: on an overlap, flag back and wait.

**Measured:** 1,053 of the 1,594 ledger rows (66%) key commits that are not on origin/main. This is platform-wide, not 10 a batch.

**Mechanism:**
1. The gate writes during pre-push, before the remote has accepted anything.
2. The retry loop commits those rows.
3. The rebase rewrites the commits.
4. The append-only rule forbids removing the old rows.

The `scrutiny_record` docstring claims `post-rewrite` and `doc_sha_reseat` repair this ledger. They do not; it is in neither tool's document set.

**Proposed fix:**
- The gate writes to an untracked `.git/sairn-scrutiny-pending.json`.
- Each pre-push and each retry **promotes** a pending row only once its sha is an ancestor of origin/main, drops it once the sha is unreachable, and otherwise keeps it pending.
- `post-rewrite` drops the old shas.

**Recommendation:** route this to cc after b66 closes. Alternatively, give fourth a go-ahead naming cc's claim id, and I would declare the three paths in `assigned_overrides`, as I did in b61. The 1,053 existing rows are a separate decision: an annotation, not a deletion.

## 3. DETAIL

### Item 3: the register

- **The phantom.** `f9a4e5a0032b` is not an object. Its record is identical in every field apart from `commit` to the record at `5bb0950a51b6`.
- **Why `--supersede` refused for 15 days.** hover2's b20 ruling record is **also** keyed at `5bb0950a51b6`, and the tool's `find()` matches on sha alone.
- **The fix.** I applied `superseded_by` through the register's own `reseat_base()` and `superseded_survivor()`, choosing the one survivor whose content is identical. Nothing was deleted.
- **For cc (the tool's owner):** `--supersede` should fall back to the content-identical record when the survivor sha hosts more than one record.

### Item 2: the two probes

**install_git_hooks_check (cc).**
- **Cause:** the hook-fire test points `core.hooksPath` at the real `.githooks` for the whole throwaway repo. `prepare-commit-msg` then correctly refuses, saying `staged_conflict_marker_check.py is MISSING`, so the throwaway commit fails.
- **Reproduced:** exit 1 with the hooks, exit 0 with an empty hooksPath.
- **Fix:** make the throwaway commit under an empty hooksPath, and set the real one only for the `push --dry-run`. `--no-verify` would not skip `prepare-commit-msg`.

**staging_discipline (cody).**
- **Cause:** the probe assumes `push_retry.py` has zero breadth-staging calls. cody b31 (`c79d4e59b`) added `git('add', '-A')` at `push_retry.py:674`, inside the selftest's temp repo. The scanner is right.
- **Fix:** stage by name there, or pin the fixture revision.
- `push_retry.py` is in fourth's overrides, so fourth can take it if it is routed here.

### Item 4: why the timeout guard cannot be driven live

**The denier is Claude Code's auto-mode classifier** (`defaultMode: "auto"`). It is not a deny rule and not a SAIRN hook: no deny rule matches `timeout N git push`.

**Minimum permission:** one allow rule, `Bash(python tools/push_timeout_guard.py --live-drive)`, for a mode that is not yet built. It would use a temp bare remote and never origin. It would pass only if the push is refused **and** the remote ref is unchanged, and it has a no-timeout control. It must run with `run_in_background`. Never grant `Bash(timeout *)`.

**For Michael:** `.claude/settings.local.json` still **allows** `timeout 540/600 python tools/push_retry.py --loop`. That is the forbidden shape. The b61 guard now refuses it, but the allow rule should go. I did not edit it: a permission file is yours.

### Item 5: `tools/claim_state_recheck.py` (`# OWNER: fourth`)

**What it does.**
- It runs in `.githooks/pre-push` once for each commit in the outgoing range.
- It refuses when another session's **active** claim covers a path the commit touches. A claim covers a path when its FILES list names the path or a directory above it, or, for `<app>.html`, when its subject is that app.
- The paths it watches:
  - the hook itself, plus every `tools/*.py` the hook invokes (read from the hook text);
  - everything under `docs/`;
  - every root `*.html`.
- Shared ledgers are exempt.

**Safety.**
- It **fails closed**: exit 2 refuses the push.
- A go-ahead is `SAIRN_CLAIM_GOAHEAD="<claim id>: <who>"`, and it waives only that claim id.
- It is in the hook's self-integrity list.
- It is declared in fourth's `assigned_overrides` and has an inventory entry.

**Tests.**
- Fixtures: 13/13.
- Real-commit control: on the b61 hook commit `d3e1d1fd8`, a still-active cody platform claim produces a refusal.

**Blind spots:**
- claims fresher than the last fetch;
- a claim with no FILES list on a non-app subject;
- commit time. `--staged` exists for a future `pre-commit` wiring, which is cc's file.

### Push

- **Two attempts.**
  - The first was refused by derived-docs (TOOLING-INVENTORY was stale). I regenerated it and added a new commit rather than amending.
  - That refused attempt wrote one scrutiny row, for `d7e8f5d9a`. No rebase followed, so the row keys a landed commit.
- **This batch created 0 orphan rows.**

## 4. OPEN, with the exact next step

1. **Item 1:** a go-ahead, or routing to cc (section 2).
2. **install_git_hooks.py hook-fire commit:** cc, as described above.
3. **staging_discipline fixture:** cody.
4. **`--supersede` ambiguity:** cc.
5. **`--live-drive` mode plus its allow rule:** Michael decides whether to grant it; fourth builds it.
6. **The `timeout … push_retry` allow rules in `.claude/settings.local.json`:** Michael.

## 5. CLAIMS

`fourth` held **platform** (b62 FILES list). It is released at wrap.
