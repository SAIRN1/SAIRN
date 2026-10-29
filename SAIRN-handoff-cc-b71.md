# SAIRN handoff: cc, batch b71, 2026-10-29

**Five of six items are closed.** Item 2 (`ctxmeter.py`) was not found, and
Michael chose to skip it. Landed at `04db9347` (see the digest for the final
tip). No `--force`, no override, no skip.

| | |
|---|---|
| Claims | none taken. The only repo edits were the watchdog header, the inventory and the bug-classes file; the worktree removal was in `Documents/SAIRN`. |
| Context | see the digest's CONTEXT line (measured). |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\52164776-0b08-422d-94e1-7a56daf3eaaa.jsonl` |

## 4 (first). Re-verified before touching shared config

Hook presence is **4/4** at blob `22b205e8`, and the install regression
test is **37/37**.

## 1. The shop-foreman watchdog is now LIVE on a schedule

**It was not live before:** it was built in b67, run by hand in b68, and
operated by hank at batch start from b69.

**What now runs it:** Windows Task Scheduler task **`SAIRN-watchdog`**, every
**15 minutes**. It runs `~/SAIRN-SESSION-LOCKS/watchdog-run.cmd`, which is:

    python tools/sairn_watchdog.py --repo "G:\My Drive\SAIRN-status"

**What it reads and writes:**
- the shared status registry, plus each build agent's **latest Drive
  handoff** and digest. With no git on the Drive, a handoff's landing time
  comes from its file mtime;
- it writes `~/SAIRN-SESSION-LOCKS/watchdog-findings.json` **only**, and
  never messages, pauses or touches an agent.

**What it flags** (unchanged): overlapping file claims, a claim that
contradicts the agent's last handoff, a registry row behind the handoff, and
a NEXT step that does not match the registry.

**First scheduled run (12:54:26Z):** one finding, **hank REGISTRY-BEHIND**
(row "b65: VT/RI/WY/DC seeds…" against `SAIRN-handoff-hank-b66.md`). No
could-not-check.

**Reading the task's status.** "Last Result: 1" is the watchdog's own
**findings** exit code, not a failure. Liveness is the file's
`generated_utc`.

**Limit:** the task runs only while the user is logged on, because the Drive
mount must be present.

Recorded in the tool header and its TOOLING-INVENTORY entry.

## 2. `ctxmeter.py` false-floor bug: NOT FOUND, skipped by Michael

**Where I looked, and found no file of that name:**
- the four builder clones;
- `Documents/SAIRN`;
- `~/.claude`;
- the Claude scratchpads;
- `G:\My Drive\SAIRN-status`;
- a 4-deep search of the home directory.

The hover clone was searched by filename only.

I asked which file was meant. Michael answered **"Skip it this batch."**

## 3. Stray `.git` entries cleaned up

**What they were.** The only nested `.git` entries on the machine are three
Claude Code agent **worktree link files** under
`Documents/SAIRN/.claude/worktrees/`, all still registered in `git worktree
list`.

**Removed, on Michael's choice:**
- `sairn-precommit-lessons-and-tools` (clean);
- `stonedesk-chamfered-corners` (only `tools/__pycache__` untracked, so
  `--force`).

Both used `git worktree remove`, and both branches are kept.

**KEPT:** `agent-ad8f80cc19dee3bb4`. It holds an **uncommitted
`api/claude.js` change**, and removing it would destroy that edit.

## 5. Cause tags

`docs/recurring-bug-classes-2.md` **C5: a check with no operator, or a
workspace with no reaper** (operations → scheduling / workspace hygiene).
- The tag table covers both fixes.
- `ctxmeter.py` is stated as not found and skipped.

## 6. OPEN

| Item | Owner | Next |
|---|---|---|
| `ctxmeter.py`: which file? | Michael | name the path when it is next in scope |
| The `agent-ad8f80cc…` worktree's uncommitted `api/claude.js` | Michael | keep, commit or discard |
| hank's registry row is behind its handoff (b65 vs b66) | hank | `sairn_status.py set` |
| The b70 items (O7, b58/b61 gaps, live-block credentials) | cody / Michael | unchanged |
