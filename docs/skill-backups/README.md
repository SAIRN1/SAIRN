# docs/skill-backups — ARCHIVE COPY, NOT A LOADED SKILL SET

**Nothing in this directory is loaded by Claude Code.** Active skills live in
`.claude/skills/` (repo, 20 `sairn-*` skills, tracked) and
`~/.claude/skills/` (machine-global). This is a disaster-recovery copy only.
Editing a file here changes nothing.

Created 2026-08-25 by the skills ground-truth audit, which found 29 skills
that existed **only** on this one machine — in no repo, with no backup.
Machine loss meant total loss. That is what this closes.

## What is here

29 skills, 190 files, **3,447,054 bytes**, byte-verified equal to their
global source at creation time.

They are the global skills that are *not* the tracked `sairn-*` set. The
`sairn-*` skills are deliberately **absent** from this directory — they are
already version-controlled in `.claude/skills/` and copying them here would
create a second, silently-diverging copy of exactly the kind this audit
existed to find.

## Read this before restoring — 11 of the 29 were symlinks

`~/.claude/skills/` is not 29 plain directories. **11 entries are symlinks**
into a second skills root, `~/.agents/skills/`:

`claude-api`, `frontend-design`, `grill-me`, `playwright-devops`, `ponytail`,
`ponytail-review`, `self-improving-agent`, `skill-creator`, `skill-vetter`,
`token-budget-advisor`, `ui-ux-pro-max`

Those 11 are stored here as **dereferenced real content**, which is correct
for an archive — a stored symlink pointing at a machine that no longer exists
would back up nothing. But it means a naive `cp -r` restore replaces symlinks
with real directories and **silently detaches them from `~/.agents/skills/`**,
so later updates to that root stop reaching `~/.claude/skills/`.

**To restore faithfully:** put the 11 back under `~/.agents/skills/` and
re-create the symlinks in `~/.claude/skills/`. The other 18 restore directly.

`~/.agents/skills/` holds 17 skills. The 6 not symlinked here —
`brainstorming`, `executing-plans`, `finishing-a-development-branch`,
`systematic-debugging`, `verification-before-completion`, `writing-plans` —
are the Superpowers plugin set, loaded through their own mechanism and
**not** part of this backup.

## Keeping it honest

This is a **snapshot**, not a sync. It goes stale the moment a global skill
is edited, and nothing detects that automatically — the same failure class
this audit found in `sairn-guardian-v2`, where the global copy sat two checks
behind the committed one for a day while every session loaded the stale one.

Re-verify with a real byte comparison rather than trusting this file:

```bash
G=~/.claude/skills; D=docs/skill-backups
for s in $(ls -1 "$D" | grep -v README); do
  gb=$(find -L "$G/$s" -type f -exec cat {} + | wc -c)
  bb=$(find -L "$D/$s" -type f -exec cat {} + | wc -c)
  [ "$gb" = "$bb" ] && echo "OK   $s" || echo "DRIFT $s ($gb vs $bb)"
done
```

`find -L` is required, not optional — plain `find` does not follow the 11
symlinks and reports them as **0 bytes**, which reads exactly like a failed
backup. That is a real false alarm this audit hit before catching the cause.

Tracked in `docs/SAIRN-OPEN-WORK-INDEX.md`.
