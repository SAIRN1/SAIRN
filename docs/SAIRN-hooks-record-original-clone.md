# Original clone (`C:\Users\marsh\Documents\SAIRN`) -- hooks record, 2026-10-14

Written by cc, batch b9, **before** clearing anything in that clone. This is a
record, not an action: the clone's `hooks` block is copied verbatim below so
the exact pre-clear state is recoverable, independent of the working copy.

## Why this exists

`SAIRN-handoff-cc-b8.md` listed this clone as having 3 Claude Code hook
events (`PostToolUse`, `PreToolUse`, `PreCompact`) plus a locally modified
`.claude/settings.json`, and said clearing those 3 hooks was Michael's
decision to make, not cc's. b9 decided it. This file is the copy made first,
per that instruction, before any edit landed in the clone.

## What was actually found, 2026-10-14 (read-only, before any change)

`git -C C:\Users\marsh\Documents\SAIRN status --porcelain` and
`git rev-list --left-right --count origin/main...HEAD` show a state larger
than the b8 handoff's framing:

- **HEAD is `26db189`, and `origin/main...HEAD` is `7810  1`** -- this clone
  is **7,810 commits behind** `origin/main` and carries **1 commit origin/main
  does not have**, not a small, recent divergence like hank/cody/fourth's.
- The 1 local-only commit (`26db189`, "fix: sairnbiz.html -- re-run
  voice-input attach on every nav(), correct the spec doc", 2026-08-18) is
  **already content-equivalent to an upstream commit**, `6c1cb4d0`, same
  subject line, already on `origin/main`. Checked by title match in
  `git log --oneline origin/main -- sairnbiz.html`; the full patch was not
  diffed byte-for-byte before writing this record.
- **Two tracked files carry local uncommitted modifications**:
  `.claude/settings.json` (permissions-section changes only -- the `hooks`
  block itself is byte-identical to HEAD, confirmed by `git diff` showing no
  hunk inside `hooks`) and `SAIRN-ACTIVE-WORK.md` (1 line changed).
- **Untracked files are present**, including build artifacts
  (`__pycache__/`, `deployment.log`, several ad-hoc `.py` scripts at repo
  root) and one file whose name alone is worth flagging rather than reading:
  `.claude/MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQK.txt`, 218 bytes. That name is
  PEM/base64-shaped (`MIG...` is the start of a DER-encoded key dumped as
  base64). **Not opened, not read, not touched** -- naming it here so it is
  not lost, and so whoever owns that clone can decide what it is and whether
  it belongs anywhere, including whether it should be deleted rather than
  left untracked beside a repo.

None of this was visible from the b8 handoff, which measured only the
`hooks` event count and the fact of a locally modified settings.json -- both
true, but the modification turned out to be in `permissions`, not `hooks`,
and the clone's age is the more load-bearing fact for what `pull --rebase`
would actually do here.

## The hooks block, copied verbatim before clearing

```json
{
  "PostToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "command",
          "command": "python C:/Users/marsh/tools/html_script_check.py",
          "timeout": 30
        }
      ]
    },
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "python C:/Users/marsh/tools/deploy_verify_notify.py",
          "if": "Bash(git push*)",
          "timeout": 90,
          "statusMessage": "Verifying live deploy...",
          "async": true,
          "asyncRewake": true
        }
      ]
    }
  ],
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "python C:/Users/marsh/tools/git_push_master_guard.py",
          "timeout": 10
        }
      ]
    },
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "command",
          "command": "python C:/Users/marsh/tools/redaction_check.py",
          "timeout": 10
        }
      ]
    }
  ],
  "PreCompact": [
    {
      "matcher": "auto",
      "hooks": [
        {
          "type": "command",
          "command": "echo '{\"hookSpecificOutput\":{\"hookEventName\":\"PreCompact\",\"additionalContext\":\"PreCompact fired: if a StoneDesk handoff is overdue (see sairn-session-handoff skill), write SAIRN-SESSION-N-HANDOFF.md now -- self-contained, independently re-verified -- before this compaction erases working context.\"},\"suppressOutput\":true}'",
          "timeout": 5
        }
      ]
    }
  ]
}
```

## The full settings.json, as found (working copy, before any edit)

```json
{
 "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Edit(C:/Users/marsh/Documents/SAIRN/**)",
      "Write(C:/Users/marsh/Documents/SAIRN/**)",
      "Write(C:/Users/marsh/.claude/projects/C--Users-marsh/memory/**)",
      "Bash(node --check:*)",
      "Bash(git status)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git fetch:*)",
      "Bash(curl -s https://raw.githubusercontent.com/SAIRN1/*)",
      "Bash(wc -c:*)",
      "Bash(wc -l:*)"
    ],
    "deny": [
      "Bash(rm -rf /*)",
      "Bash(git push --force*)",
      "Bash(git push*master*)"
    ],
    "ask": [
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git push:*)",
      "Bash(npx vercel:*)"
    ]
  },
  "model": "sonnet",
  "env": {
    "DISABLE_AUTOUPDATER": "1"
  },
  "hooks": { ...copied above... },
  "outputStyle": "silent",
  "enabledPlugins": {
    "superpowers@claude-plugins-official": true
  }
}
```

(The `hooks` value is elided here only to avoid duplicating the block twice
in one file; it is byte-identical to the copy above.)

## What b9 did and did not do as a result

- **Cleared**: `hooks` set to `{}` in the clone's working copy of
  `.claude/settings.json`, uncommitted, matching the pattern already live in
  `SAIRN-cc`/`SAIRN-hank`/`SAIRN-cody`/`SAIRN-fourth`. The pre-existing
  `permissions` local modification was left exactly as found -- not mine to
  resolve, and not what was asked.
- **Not committed.** Per house rule, `.claude/settings.json` is never
  committed by an agent session; it stays a local, uncommitted change in that
  clone, same as the permissions edit already sitting there.
- **`pull --rebase` was NOT run in this clone.** The 7,810-commit divergence,
  the one local commit, and the untracked file above are each individually
  survivable, but together they are a materially different operation from
  "pull the hook removal" -- flagged to Michael rather than guessed at. See
  the b9 report/digest for the exact question.
