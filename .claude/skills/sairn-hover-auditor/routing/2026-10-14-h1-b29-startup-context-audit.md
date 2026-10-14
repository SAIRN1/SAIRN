# H1 b29 -- startup-context measurement, read-only, docs list

Written because this session began near 50% of its context window used
before any work happened. Everything below is measured by command, not
estimated. No setting was changed by this item; the one real settings
finding (see §5) is routed to cc, sole owner of `.claude/settings.json`
and `~/.claude/settings.json`.

## 1. What loads at session start, each item with its size

| item | size | source command |
|---|---|---|
| user-level `~/.claude/CLAUDE.md` | 1,345 B | `wc -c ~/.claude/CLAUDE.md` |
| project `CLAUDE.md` (identical in all 6 clones, git-tracked) | 20,006 B | `wc -c CLAUDE.md` in each clone |
| user-level `~/.claude/settings.json` (shared, one file, read by every clone) | 11,123 B | `wc -c ~/.claude/settings.json` |
| project `.claude/settings.json` (per clone, all 6 currently identical) | 6,517 B | `wc -c .claude/settings.json` in each clone |
| user-level skills directory (`~/.claude/skills/`) | 610,087 B, 62 entries | `du -sb ~/.claude/skills` |
| per-clone project skills (`.claude/skills/`, git-tracked, NOT identical across clones) | 3.36-3.81 MB, see §3 | `du -sb .claude/skills` per clone |
| auto-memory (`MEMORY.md` + individual files, per clone, NOT git-tracked) | 6.4 KB-56.4 KB, see §2 | `du -sb` the project's `memory/` dir |
| this role's own handoff read (manual, via Drive search, not an automatic start-of-session load) | ~8 KB per batch | measured per-batch, not part of fixed startup cost |

The single largest FIXED per-session cost that is not a build agent's own
accumulated memory is the per-clone skills directory (§3), and within
that, `.claude/skills/sairn-hover-auditor/` specifically (this role's own
skill, 2.9-3.4 MB depending on clone, 85-89% of the whole skills
directory in every clone measured).

## 2. Memory files, per clone, each item is a real file with a real byte count

```
cc:      56,399 B total, 22 files -- CMD: du -sb .../SAIRN-cc/memory
cody:    28,618 B total, 14 files -- CMD: du -sb .../SAIRN-cody/memory
fourth:   6,407 B total,  4 files -- CMD: du -sb .../SAIRN-fourth/memory
hank:    20,070 B total,  7 files -- CMD: du -sb .../SAIRN-hank/memory
hover:   15,897 B total,  5 files -- CMD: du -sb .../SAIRN-hover/memory
hover2:  15,241 B total,  6 files -- CMD: du -sb .../SAIRN-hover2/memory
```

**What can be trimmed, named by file, not by guess:**
- `cc`: four files named `batch15-progress.md` (2,420 B), `batch16-progress.md`
  (1,870 B), `batch17-progress.md` (4,020 B) and `batchW-b4-progress.md`
  (3,733 B) -- 12,043 B together, ~21% of cc's whole memory directory.
  These are per-batch progress notes, which is exactly the category this
  role's own memory-system instructions name as excluded ("ephemeral
  task details: in-progress work, temporary state") -- not this role's
  file to delete, flagged for cc as an observation, not a routed action.
- `hank`: one file, `hank-b1-progress.md`, 10,632 B -- 53% of hank's
  entire memory directory on its own, same category as above.
- `cody` and `fourth` carry no file matching `*progress*` or `*batchNN*`
  -- the two leanest directories by both file count and total size, and
  that correlation is not a coincidence worth ignoring.

This is an observation about another clone's own memory hygiene, not a
finding this role fixes or deletes -- the same boundary CLAUDE.md states
for build-agent access to this clone applies in reverse.

## 3. Per-clone `.claude/skills/` size, and where the spread comes from

```
cc:      3,434,339 B  (__pycache__: 68,113 B)
cody:    3,366,480 B  (__pycache__: 0 B)
fourth:  3,362,124 B  (__pycache__: 0 B)
hank:    3,397,608 B  (__pycache__: 31,128 B)
hover:   3,561,572 B  (__pycache__: 199,556 B)
hover2:  3,813,392 B  (__pycache__: 450,017 B)
```
CMD per clone: `du -sb .claude/skills` and
`find .claude/skills -iname __pycache__ -exec du -sb {} + `

**Spread: 451,268 B (13.4%) between the largest (hover2) and smallest
(fourth).** The `sairn-hover-auditor` skill directory alone accounts for
85-89% of every clone's total (2,918,449 B in cody/fourth up to
3,369,717 B in hover2), and the SAME directory's `__pycache__` subtrees
account for the entire inter-clone spread above the shared baseline --
compiled bytecode cache from locally-run `.py` tool files, not content
that differs by design. **What can be trimmed:** the `__pycache__`
directories under `.claude/skills/sairn-hover-auditor/` and
`tools-hover2/` in the hover and hover2 clones specifically -- 199,556 B
and 450,017 B respectively, neither one git-tracked content, both purely
local build artifacts of having run Python tools in that tree.

## 4. Settings.json, per clone -- confirms no startup-load asymmetry here

All 6 project-level `.claude/settings.json` files are byte-identical:
6,517 B, `"hooks": {}` present (0 matcher entries) in every clone. CMD:
`wc -c .claude/settings.json` + `grep -c '"matcher"' .claude/settings.json`
per clone. This independently corroborates item 4 of this batch (cc b8's
hook removal landed uniformly, not just in the clone cc happened to
touch) and means none of the six clones carries a startup-time hook cost
the others do not.

## 5. One real settings finding, routed to cc (sole owner)

Not a defect -- a correction to this batch's own dispatch, which named
the git -C allow rule as missing when it is not. **Verified present**:
`~/.claude/settings.json` lines 102-108 carry four spellings of
`Bash(git -C .../SAIRN-*)` under `permissions.allow`, lines 196-222 carry
the matching `-C`-prefixed mirror of every existing deny rule (so the
new allow cannot walk past a force-push/reset-hard/clean-f deny the
non--C forms already block), and lines 228-233 list
`permissions.additionalDirectories` for all six clones. The file's own
`_gitc_note` (line 261) documents the two-cause design (command pattern
+ directory) and states plainly what was NOT measured: whether the
harness treats a mid-argument `*` in these patterns as a true glob.
**Routed to cc, the sole owner of this file**: if that glob-matching
question has since been tested for real (a `git -C` command that should
have been denied and wasn't, or allowed and prompted anyway), record the
result next to the note that already discloses it as unmeasured.

No change made to any settings file by this item.
