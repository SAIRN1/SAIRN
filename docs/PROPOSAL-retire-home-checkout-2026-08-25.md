# Proposal: retire the `C:\Users\marsh\` checkout

**Status: PROPOSAL. Nothing has been run.** Needs Michael's approval, and one
decision (Step 4) that is a judgment call, not a technical one.

Written 2026-08-25 by the Cody session, after the skills audit traced three
separate problems to this one root cause.

---

## What this actually is

`C:\Users\marsh\` — the Windows home directory — **is a git working tree of
`SAIRN1/SAIRN`**, checked out on `main`, **33 commits behind** `origin/main`.
It is not a stray folder inside the home directory. It *is* the home
directory.

Measured, not assumed:

| | |
|---|---|
| Tracked files | **451** (the whole repo: `stonedesk.html`, every app HTML, `api/`, `sql/`, `docs/`, `tests/`, `tools/`) |
| Untracked entries `git status` reports | **477** — i.e. the entire home directory: `Documents\` (all four real clones), `Downloads\`, `Desktop\`, `AppData\`, `.claude\`, `.agents\` |
| Unpushed commits | **0** — nothing would be lost by removing it |
| Locally modified tracked files | 2 — `.claude/settings.json`, `CLAUDE.md` |
| `.git` size | 18 MB |
| Orphaned artifacts if `.git` is removed | 428 files, ~11.0 MB (tracked, excluding `.claude/`) |

`git status` there also throws permission errors on nine Windows junctions
(`Application Data/`, `Cookies/`, `Recent/`, …), which is a good sign that
nobody intended this.

## Why it is worth spending time on

**1. `git clean -xfd` run there deletes the home directory's untracked
content — including all four working clones.** Every file in `Documents\`,
`Downloads\` and `Desktop\` is untracked-and-not-ignored inside this tree.
This is the single largest reversible-by-nobody risk on the machine. It is not
hypothetical: `git clean -xdn` was already used tonight, deliberately scoped to
one path, while diagnosing the skill store.

**2. It is the root cause of the skill-store exposure.** `~/.claude/skills/`
*is* this checkout's tracked `.claude/skills/` directory — the user-level skill
store and the checkout are literally the same path. It tracks 20 `SKILL.md`
files at a 33-commit-old revision. A `git restore` or `git checkout .` there
overwrites the 21 symlinks with stale skills. The canonical store was moved to
`C:\SAIRN\skills\sairn\` specifically to survive that; the symlinks themselves
cannot be protected while this checkout exists.

**3. It is already causing wrong behaviour, today.** `C:\Users\marsh\CLAUDE.md`
is loaded as project instructions for every session whose working directory is
under the home directory — which is all of them. It is 33 commits stale and
still says *"run full Check 0 + all 26 sairn-guardian-v2 checks"*. The repo says
30. **This session read the stale one.** The same staleness applies to every
other tracked file there: a spot-check of 8 found 5 behind current `main`,
including `sql/sairnlaw_employee_auth_schema.sql` and `sairndental-book.html`.

## Proposed end state

- `C:\Users\marsh\` is an ordinary home directory. No `.git`, no repo files.
- Real work continues in the four clones under `Documents\`, unchanged.
- `~/.claude/` survives intact: live `settings.json`, the 21 skill symlinks,
  `output-styles/silent.md`, `agents/panel-auditor.md`.
- Canonical skills stay at `C:\SAIRN\skills\sairn\` — already outside every
  working tree, unaffected by this.
- `~/.agents/skills/` (17 skills, 11 of them symlinked into `~/.claude/skills/`)
  stops being inside a working tree as a side effect. It has no repo copy of
  its own; `docs/skill-backups/` is its only backup.

## Steps, in order

Each step verifies before the next. Nothing here is irreversible until Step 5,
and Step 5 is recoverable from Step 1's backup.

**Step 0 — confirm nothing is waiting to be saved.**
```bash
cd /c/Users/marsh
git rev-list --count origin/main..HEAD     # must print 0
git stash list                             # must be empty
```
If either is non-empty, **stop** and salvage first.

**Step 1 — back up the two things that are genuinely local.**
```bash
cp -r /c/Users/marsh/.claude "/c/SAIRN/backup-2026-08-25/dot-claude"
cp /c/Users/marsh/CLAUDE.md  "/c/SAIRN/backup-2026-08-25/home-CLAUDE.md"
```
`.claude/` holds live settings **and** the 21 symlinks. `cp -r` will
dereference the symlinks into real copies — that is fine for a backup, but do
not restore it blindly; rebuild the symlinks with Step 6 instead.

**Step 2 — record exactly what will be deleted, so it can be checked after.**
```bash
cd /c/Users/marsh
git ls-files > /c/SAIRN/backup-2026-08-25/tracked-files.txt   # expect 451
```

**Step 3 — confirm nothing tracked there is unique.** Everything must exist in
`origin/main`, so deleting the home copies loses nothing:
```bash
cd /c/Users/marsh/Documents/SAIRN-cody && git fetch origin
while read f; do
  git cat-file -e "origin/main:$f" 2>/dev/null || echo "ONLY IN HOME: $f"
done < /c/SAIRN/backup-2026-08-25/tracked-files.txt
```
Expect **zero** output apart from `.claude/settings.json` and `CLAUDE.md`,
which are the two known local modifications and are already backed up.
Any other name means **stop** — that file exists nowhere else.

**Step 4 — DECISION FOR MICHAEL, then delete the orphans.** Removing `.git`
alone leaves 428 stale repo files (~11 MB) loose in the home directory. Two
options:

- **(a) Delete them.** Cleanest. They are stale duplicates of files that live
  in four working clones. This is the recommendation.
- **(b) Keep them.** Only if something outside the repo reads a path like
  `C:\Users\marsh\stonedesk.html` — a shortcut, a script, a bookmark. Worth
  ten seconds of thought before choosing (a), because it is the one part of
  this that a backup does not make trivially reversible.

For (a), delete from the recorded list rather than by hand, and **exclude
`.claude/`**:
```bash
cd /c/Users/marsh
grep -v '^\.claude/' /c/SAIRN/backup-2026-08-25/tracked-files.txt \
  | while read f; do rm -f "$f"; done
# then remove the directories left empty (api/, sql/, docs/, tests/, tools/,
# agent/, scripts/, .github/, .semgrep/) — check each is empty first
```
Do **not** use `git clean` for this. `git clean` at this path is the exact
command this proposal exists to make impossible.

**Step 5 — remove the working tree.**
```bash
mv /c/Users/marsh/.git "/c/SAIRN/backup-2026-08-25/home-dot-git"
```
Move, do not delete — 18 MB, and it makes Steps 0–5 fully reversible until
you are satisfied. Delete it after a week of clean sessions.

**Step 6 — verify the skill store still resolves.**
```bash
cd /c/Users/marsh/Documents/SAIRN-cody
bash scripts/verify-skill-store.sh      # expect CLEAN, exit 0
```
If any symlink was collateral damage, rebuild:
```bash
for s in $(ls -1 .claude/skills); do
  rm -rf "/c/Users/marsh/.claude/skills/$s"
  MSYS=winsymlinks:nativestrict ln -s "/c/SAIRN/skills/sairn/$s" "/c/Users/marsh/.claude/skills/$s"
done
```

**Step 7 — confirm the home directory is no longer a working tree.**
```bash
git -C /c/Users/marsh rev-parse --show-toplevel   # expect: not a git repository
git -C /c/Users/marsh/Documents/SAIRN-cody status --short | head
```
The second command must still work normally — the clones are independent and
are not affected by any of this.

**Step 8 — start one fresh Claude Code session and confirm** the stale
`CLAUDE.md` is gone from the loaded context (it should no longer say 26
checks) and that a `sairn-*` skill loads.

## What this does NOT fix

- **`~/.agents/skills/`** stops being inside a working tree, but its 17 skills
  still exist in exactly one place on one machine. `docs/skill-backups/` covers
  11 of them; the 6 Superpowers ones are plugin-managed. Not urgent, not solved.
- **Two real copies of the `sairn-*` skills** (repo + `C:\SAIRN`) still exist by
  design — see `scripts/verify-skill-store.sh` for why, and run it to detect
  drift.
- **The user-level `~/.claude/CLAUDE.md`** is a separate, untracked file and is
  not touched by any of this. Only the repo-artifact `~/CLAUDE.md` goes away.

## Rollback

Before Step 5: nothing has changed that matters. After Step 5:
```bash
mv "/c/SAIRN/backup-2026-08-25/home-dot-git" /c/Users/marsh/.git
cd /c/Users/marsh && git checkout -- .
```
That restores the checkout exactly as it is today, including the 428 files, at
the same 33-commits-behind commit.
