# SAIRN handoff: cc, batch b66, 2026-10-28

**Three dispatches were worked as one batch.** The work is a builder-into-auditor
deny hook with a shared block log, a recurring presence check, and the
done-line wrapper.

| | |
|---|---|
| Landed | `a2bdf5ea` (hook + presence), `a367bd0c` (done-line + Stop + log reconcile), `8c15c569` (writer matches H1 byte-for-byte). See the digest for the final tip. No `--force`, no override, no skip. |
| Claims | `platform` (b66), released with this handoff. |
| Context | see the digest's CONTEXT line (measured). |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\52164776-0b08-422d-94e1-7a56daf3eaaa.jsonl` |

## 1. The deny hook: `tools/builder_auditor_deny_hook.py`

**What it is.** A PreToolUse hook for Edit, Write, MultiEdit, NotebookEdit,
Bash, PowerShell and Monitor.
- It runs from a copy in `<clone>/.git/sairn-hooks/`, in cc, cody, fourth and
  hank.
- It is wired in each clone's `settings.local.json`.
- Hover clones are not wired.

**What counts as an auditor path:**
- the path manifest's `auditor_paths`, read at run time, over a built-in
  floor;
- `hover<N>` claim files;
- `H<N>` deliverables;
- the `SAIRN-hover<N>` clones.

**What each call is checked for:**
- **Paths** are checked both as written and after realpath.
- **Bash** gets:
  - a text pass, raw and compacted;
  - tokens resolved through `cd`, `pushd` and `git -C`;
  - git pathspecs, including ancestors and globs (dirty-gated);
  - `git apply` and `git am` patch targets;
  - any **untracked** script reached as an argument, by pipe, or by
    `-c exec(open())`.

**How it behaves.**
- It fails closed on an unreadable payload.
- An allowed call produces no output.
- Selftest: **74 arms**. Each layer was ablated, and its own arms fail without
  it.

**Baseline replay.** 5,256 real builder calls from the four transcripts were
replayed through the hook. 73 would have been refused:
- 9 were Edit or Write into hover clones, all real reach-ins or past probes;
- 60 were Bash commands naming auditor paths, which are refused by spec;
- 4 were my own uncommitted selftest.

The replay drove four narrowings before landing: index-only git, dirty-gated
ancestors, read-only globs, and Monitor called with only a task_id.

**Live, in this session**, with nothing changed (`git status` empty):
- a `git checkout` on an auditor path was refused;
- a `python -c` naming one was refused;
- a direct Edit on SKILL.md was refused.

H1's b99 also drove its own hook from the hover side, including a subagent
case.

**A false positive the armed hook surfaced on its first day.** The first
version also scanned *modified tracked* scripts, so it refused cc running
`tools/tooling_inventory.py`, which names the auditor paths. That is a routine
builder step. Now only untracked scripts are scanned; `is_tracked()` says why.

## 2. The shared block log, reconciled with H1's live writer

- Both hooks now append to `~/SAIRN-SESSION-LOCKS/deny-blocks.log`.
- I read H1's `block_log()` from source
  (`hover_builder_path_deny.py`:803). Both sides now match on:
  - **five tab-separated columns**: ts, agent[/subagent type], path, tool,
    reason;
  - the same UTC format;
  - the same tab and newline sanitising;
  - the **same 400-character field cap**;
  - one `os.write` under `O_APPEND`.
- Measured on the live file: **20 rows, all five columns**, sorted by time;
  13 are the auditor's and the rest are cc's.
- A fresh live refusal (22:52:32Z) wrote a correct row.
- The earlier JSON-lines rows were migrated in, and that format is retired.
  The old `builder-auditor-blocks.jsonl` files are left in place, because rm
  is denied.
- The Drive mirror `G:\My Drive\SAIRN-status\deny-blocks.log` is a **byte**
  copy: 2,946 = 2,946 bytes.
  - The first version copied in text mode and dropped H1's CRs.
  - The selftest arm for this was ablated and fails without the fix.

**ROUTED TO H1 (not touched; audit layer).** H1's `block_log()` calls
`os.open` without `os.O_BINARY`, so on Windows every auditor row ends **CRLF**
and builder rows end LF. Readers must strip `\r`. The fix is
`| getattr(os, 'O_BINARY', 0)`.

## 3. Recurring presence check: `tools/builder_hook_presence.py`

**When it runs.** It is a SessionStart hook in every builder clone. Each clone
checks **all four**.

**What it checks:**
- blob sha of each copy against the newest builder origin/main;
- the exact PreToolUse, SessionStart and Stop wiring;
- no `disableAllHooks`;
- a readable manifest.

**`--install`.**
- It refuses an unlanded copy.
- **A refresh leaves `settings.local.json` untouched.** That was verified
  byte-identical on all four clones when I refreshed today's copies myself.
  The settings files are deny-protected for agents. Michael ran the two
  installs that wrote the wiring.

**Now:** 4 of 4 OK, at hook blob `6663acbd`.

**Selftest:** 14 arms.

## 4. Done-line wrapper: `tools/sairn_done_line.py`

**`--batch b<n>`** prints `done b<n> <id>` only when all of these hold:
- the handoff, report and digest are on origin/main byte for byte, after a
  fetch;
- the handoff landed no later than the report;
- `digest_lint` passes;
- `drive_upload_verify` uploads and verifies all three.

**The id is read from Drive for desktop's `metadata_sqlite_db`.** It joins
items through `stable_parents` to the SAIRN-status folder. It waits for a real
cloud id rather than a `local-` placeholder. I checked it against the API's id
for cc b65, and the two agree.

**`--stop-hook`** (wired as Stop) refuses any final text other than the
recorded line. After 3 refusals it lets the turn end, so it cannot loop.

**Selftest:** 16 arms.

CLAUDE.md's done-line bullet now names the tool.

## 5. Tier A: hover b96 ITEM 4

This is the same `test_965` record cc appended in b65
(`opened_at` 2026-10-28T21:14:26Z, sha `fe012756`, on origin/main).
- It was **not appended twice.**
- H1 b99's "BLOCKED-ON:cc" for it is stale.
- The next step is hover's: land the test file.

## 6. OPEN

| Item | Owner | Next |
|---|---|---|
| CRLF rows in the shared log | H1 | Add `O_BINARY` in `block_log()`. |
| The "anything else hover owns" triad (`hover_auditor_scope_gate.py`, `hover_separation_*`, `hover_routing_gap_*`) is NOT in the deny scope: shared, and cc owns the gate | Michael | Decide whether builders should be blocked from them. |
| Hook limits, stated in the header | -- | A committed tool opening an auditor path; a path built from shell variables; an import from an untracked script. |
| Review the hover b92 obligation | cc | After hover lands test_965. |
| cody b57 `mech_backup` obligation | cc | Unreviewed, from b65. |
