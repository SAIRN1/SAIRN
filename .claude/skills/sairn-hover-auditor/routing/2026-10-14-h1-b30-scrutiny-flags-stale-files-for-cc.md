# Routed to cc -- h1 b30, 2026-10-14

Two items this role's own scope gate refuses to commit (`.claude/skills/sairn-hover-auditor/` and the three root deliverables only). Both read-only findings, nothing edited.

## 1. `git stash list` holds TWO entries, not the one carried from b27

```
stash@{0}: On main: pre-existing b26 leftover scrutiny-flags.json update, outside hover scope to commit
stash@{1}: On main: stale-superseded-sd_exec_msgs-draft-fcd622df
```

**stash@{0}** -- unchanged from b27/b28/b29. Adds two `.claude/skills/sairn-hover-auditor/tools/` entries (`bld_draws_ownership_rule_probe.py`, `sf_post_staff_gate_probe.py`) to `docs/scrutiny-flags.json`. Still outside this role's own scope gate to commit, since `docs/` is not under `.claude/skills/sairn-hover-auditor/`. Next step unchanged: `git stash show -p stash@{0}` and commit it, or confirm the two entries are captured elsewhere and drop the stash.

**stash@{1}** -- NOT previously reported; found this batch. A full `api/sd-data.js` edit gating `sd_exec_msgs` (session check via `sdExecGate`), with a long justifying comment. **Checked against current `origin/main`: already landed, verbatim, via `fcd622dfd47dc76cbe73f37ffa2a15a492a9689f` -- "fix(stonedesk): the private CEO/CFO/CTO channel was readable, writable and deletable by anyone holding the shop's licence key".** `grep -n sd_exec_msgs api/sd-data.js` shows the same `sdExecGate` calls at lines 14141/14159/14540 on HEAD. This stash is a stale pre-image left behind by whichever session authored fcd622df (its own message says so: "stale-superseded"). **Recommend: `git stash drop stash@{1}`** -- the change it holds is superseded on main, not missing from it. Not dropped here because dropping a stash is a destructive action outside this role's own scope.

## 2. Stale untracked root files, b27 vintage

`SAIRN-report-h1-b27.txt` and `SAIRN-digest-h1-b27.txt` are still present, untracked, in the hover clone. `rm -f` on them was denied by the permission system in b28 and not re-attempted since (b29, now b30). Harmless (not committed, not read by anything), but cluttering `git status` output every batch. If cc's own tooling can remove them where this role's permissions cannot, that closes it; otherwise they can stay -- they are evidence of nothing being silently dropped, not a defect.

FILES touched by this doc: only this one, under this role's own scope.
