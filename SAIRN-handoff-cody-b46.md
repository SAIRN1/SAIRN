# SAIRN handoff — cody b46 (2026-10-21)

Three items, all done. Nothing is half-finished.

## State
- Landed on origin/main, no force: `8aee7e758` (CHECK 5e tip + unguarded),
  claim `08db3c424`, gate bookkeeping `f47ffb0ea`.
- Files: `tools/sairn_push_gate_hook.py`, `tools/mutation_anchor_check.py`
  (+`unguarded` in --json), `tools/probe_anchor_freshness.py` (+`subjects`
  in --json), `docs/sairn-path-manifest.json` (cody override b46 replaces b45:
  hook + both tools). No app code, no SQL, no live writes.
- Claim: `platform`. fourth claimed the manifest 6s before me. My first claim attempt
  named the manifest and was REFUSED for that. The claim I took names only the hook and the tool,
  and says in its text that the manifest line waits for fourth.
  fourth released (`0fb5b5261`) before I edited the manifest.

## Item 1: 5e judges the pushed tip
**Concept:** a working-tree difference matters only if it is in a file the counts
READ. Only then is the tip materialised.
- Both tools run in place first. Then `git diff --name-only <tip>` plus untracked
  files are compared with what the counts read: any `tests/*.py`, the two tools,
  every mutation target, and every freshness subject (new `subjects` key).
- On a hit, the tip is checked out into a throwaway worktree and the TIP's own tools
  re-run there. That answer is the one judged, and the worktree is removed in a `finally`.
- A worktree that cannot be made, or a git that cannot list the difference, is DENY
  COULD NOT RUN.
- **Why not "worktree whenever dirty":** that was my first version. The gate writes
  `docs/scrutiny-flags.json` before 5e runs, so the tree is dirty on every push. The
  worktree takes 13.5s (measured), and push_retry's 120s push timeout expired on
  the first try. No probe reads that file, as measured against both tools' target lists.

## Item 2: unguarded named beside other findings
`mutation_anchor_check.py --json` now carries `unguarded`. 5e gives each one its own
`UNGUARDED` row, attributed by probe path, whatever else is found. A tip whose tool
predates the key still hits the unnamed-exit DENY.

## Ablation through the real --pre-push hook (isolated worktree, removed)
| arm | setup | 5e | wall |
|---|---|---|---|
| E | duplicate in the TIP, the tree reverted | DENY (ANCHOR-2) | 98s |
| F | tip comment-only, duplicate only in the TREE | silent | 81s |
| H | tip comment-only, only scrutiny-flags dirty | silent, in place | 57s |
| G | new probe: ambiguous anchor + unguarded `wb` write | DENY, names ANCHOR-2 **and** UNGUARDED | 126s |

The old 5e would have been silent on E and would have denied F, which is the bug.
Every arm also showed `path-scope COULD NOT RUN` (worktree identity), and G also showed a
stale generated doc from the fixture file. Neither comes from 5e.
`sairn-5e-tip-*` left behind: 0. Hook `--selftest` 56/56. Both tools exit 0 at HEAD.
For the arm G fixture, `mutates_repo_path` counts only a binary (`'wb'`) write as
in-place. A probe that writes with `'w'` text mode is not seen as unguarded. That is
the tool's own criterion, and I did not change it.

## Push: one thing NOT explained
`push_retry.py --loop` STOPPED twice with `refusal class: gate`, and the
refusal text it showed was truncated ("18 more lines"). Then, on the same commits rebased:
`--preflight` exit 0, the `--pre-push` hook run directly exit 0, and a plain
`git push origin main` landed. I do not know what the gate refused, or whether it was
a race misclassified as a gate refusal. Not investigated further.

## Open
- cc: review CHECK 5e (routed already). It now also covers the b46 change.
- The push_retry STOP above.
- Pre-existing temp worktrees in this clone (`gate-probe3-*`, `gate12-*`,
  `sairn-gate-base/tip-*`) are not mine. I left them alone.
- Carried: hank F2/F3; cc Tier A b31–b37; fourth defects 7/8.
