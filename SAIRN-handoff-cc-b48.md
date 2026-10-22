# SAIRN handoff: cc, batch b48, 2026-10-22

**Six items: four closed, one partly closed and blocked on Michael (item 3),
and one closed with a deviation (item 2).** No `--force` and no override were
used.

## 1. State

| | |
|---|---|
| Landed | `6d801c8a` (the H1 #1640 fix) and the scrutiny rows, to origin/main at `5d32ba5b`, then these deliverables. The clone reads 0 0 against origin |
| Overrides | **NONE** |
| Context | the CONTEXT line in the digest, measured by `tools/context_verify.py` |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

## 2. Item 1: H1 #1640, CLOSED (`6d801c8a`)

- **The finding** is in H1's self-log
  (`~/.claude/projects/C--Users-marsh-Documents-SAIRN-hover/hover-audit-log/hover-audit-log.jsonl`,
  seq 1640, ref `h1-b73-handoff-blocked-by-own-scope-gate`). The pre-commit
  scope gate refused `SAIRN-handoff-H1-b73.md` and `SAIRN-latest-H1.md`, and
  it was still refusing the b81 digest at H1 b82.
- **The fix, in `tools/hover_auditor_scope_gate.py`:**
  - An entry that begins `^` is now an anchored regex, matched with
    `fullmatch`. Every other entry keeps its old meaning.
  - `AuditorScope.own_deliverables` is derived from the session name:
    `hover` → H1, `hover<N>` → H<N>.
  - It covers `SAIRN-{handoff,report,digest,closure-recheck}-H<n>-b<N>.{md,txt}`
    and `SAIRN-latest-H<n>.md`, at the clone root only.
  - The scope is per instance: hover2 cannot write H1's files.
  - A non-auditor session gets `UNPROVISIONED`, which matches nothing.
  - The quotation is the same SKILL.md exception that `OWN_CLAIM` cites. That
    was #1640's own option 1.
- **`tools/hover_separation_audit.py`** got the duplicate copy in the same
  change. The audit accepts any instance's deliverables.
- **Probe:** `tests/run_hover_separation_probe.py`, declared under cc in
  `assigned_overrides`, gained 6 arms. It passes 154/154.
  - With the fix ablated it gives 151/154, and exactly the three new
    allow-arms go red.
  - The refusal arms cover another instance's file, H11, a non-root path,
    `.bak`, `.mdx`, a build agent's handoff, and a non-auditor session.
- **Other checks:** `hover_separation_ci` exits 0 and its probe has 0
  failures. `hover_separation_audit` gives the same verdict before and after:
  2 pre-existing violations, the same shas.
- **Not yet driven:** a real commit in H1's armed clone. cc cannot reach that
  clone, by design. **Next step:** H1 commits its next handoff without
  `--no-verify` and logs whether it passes, which closes #1640 in its chain.

## 3. Item 2: deny replication to cody and fourth, CLOSED, with a deviation

- **cody already had hank's 13 entries.** The file is unchanged and
  byte-identical to the pre-run backup.
- **fourth had 8**: the Edit/Write forms, without the 5 `Bash(*…hover*)`
  entries. It now has 13, and they are the same set as hank's. Every other
  key and the allow list are identical to before (checked by parsing both
  files).
- **DEVIATION: `fix-deny.ps1` was run first and corrupted both files.** I
  restored both byte-identical from backups, then made the same
  `-cnotcontains` append in Python.
  - Windows PowerShell 5.1 `Get-Content`/`Set-Content` round-trips through
    the ANSI code page.
  - In cody, 1 allow entry changed: `\u2500\u2500` became `--`.
  - In fourth, 4 allow entries changed, and one em dash was written as a raw
    cp1252 0x97 byte, so the file was no longer valid UTF-8.
  - There is no `pwsh` (PowerShell 7) on this machine.
  - **For Michael:** the script is safe only on files that are pure ASCII.
    Otherwise add `-Encoding UTF8` to both cmdlets, or run it under pwsh.
- Backups are in
  `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a\scratchpad\settings.local.json.{cody,fourth}.bak-cc-b48`.
  They were moved out of those clones, where they were untracked.
- **hank's file** is valid UTF-8 with 6 non-ASCII bytes. Whether an earlier
  run altered it cannot be told without its original.

## 4. Item 3: auditor-local deny lists, PARTLY DONE, needs Michael

Read-only check:

- **SAIRN-hover already denies hover2** (4 entries: Edit and Write, in both
  the `//C:/` and `~/` forms). Nothing is needed.
- **SAIRN-hover2 does NOT deny SAIRN-hover.** Its deny list has 16 entries
  (destructive git, and the four build clones), and none of them names
  SAIRN-hover.
- **cc could not write it.** cc's own deny list refuses Write/Edit to both
  auditor clones and any Bash command naming them. CLAUDE.md also says a build
  agent must not reach into an auditor clone. Both are by design.
- The hover2 file is pure ASCII, so `fix-deny.ps1` is safe on it.
- **Next step, Michael**, one command:

      ! powershell -NoProfile -ExecutionPolicy Bypass -Command "& 'C:\Users\marsh\fix-deny.ps1' -Path 'C:\Users\marsh\Documents\SAIRN-hover2\.claude\settings.local.json' -Entries 'Edit(//C:/Users/marsh/Documents/SAIRN-hover/**)','Write(//C:/Users/marsh/Documents/SAIRN-hover/**)','Edit(~/Documents/SAIRN-hover/**)','Write(~/Documents/SAIRN-hover/**)'"

- **Then verify in a fresh window for each auditor.** cc cannot open one.
  - In a new H1 window: a native Write to a probe file in SAIRN-hover should
    succeed, and the same probe in SAIRN-hover2 should be refused.
  - In a new H2 window: the mirror image.

## 5. Item 4: CHECK 5f inside a full `--preflight`, VERIFIED

- The sweep-runner agent came back COULD NOT RUN, because it had no shell
  tool. I ran it directly instead.
- **Setup:** a throwaway worktree outside the clone, with no ancestor
  `node_modules`. One local commit touches only a comment in
  `api/_lib/firebase-admin.js`; that commit was never pushed. There were
  three full runs.

| Arm | Exit | 5f finding | Expectation |
|---|---|---|---|
| A: no `node_modules` | 1 | DENY, 41 `MISSING` lines (scope npm) | PASS |
| B: real copy of the clone's install (the check alone exits 0) | 1 | **none** | PASS |
| C: copy with firebase-admin set to 12.7.0 | 1 | DENY, `DRIFT node_modules/firebase-admin -- locked 13.10.0, installed 12.7.0` | PASS |

- **The other finding** in all three arms was path-scope COULD NOT RUN. A
  worktree has no provisioned `sairn-session`, so that is expected noise and
  not a 5f fault.
- **Teardown:** the worktree and the `wt5f-probe` branch were removed. The
  clone's firebase-admin is 13.10.0, `cmp`-identical to the b46 backup, and
  the dependency check is CLEAN.
- Pre-existing stale worktrees remain in `git worktree list`. They were not
  created here, apart from `scratchpad/wt-abl` from an earlier cc batch. They
  are left as found.

## 6. OPEN

- **Michael:** add the hover2 deny entries (command above), then do the
  fresh-window verification for each auditor.
- **Michael:** decide whether to make `fix-deny.ps1` UTF-8-safe.
- **H1:** confirm #1640 with a real commit in the armed clone.
- **cody:** CHECK 5e `skipped` anchors (carried from b46).
- **hank, cody, fourth:** run `npm ci --ignore-scripts --no-audit --no-fund`
  once per clone (carried from b46).
