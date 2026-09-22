# Multi-instance self-log fix for `hover_separation_audit.py` / `hover_process_pass_freshness.py` — tested proposal, not applied

**Author:** hover2. **Status:** designed, tested against REAL live data, **not committed and not applied to the tracked files** — see the scope flag at the end before either is edited.

## The defect, reproduced live (not hypothetical)

Both tools assume exactly one `hover-audit-log.jsonl` exists on the machine. `find_hover_log()` (in `tools/hover_separation_audit.py`) returns a bare list — never a path — the moment it finds more than one, and both tools treat that as "MORE THAN ONE self-log found and none of them is authoritative" → refuse (exit 2 / COULD NOT RUN).

That assumption held until tonight. The moment hover2 built its own real self-log (`~/.claude/projects/C--Users-marsh-Documents-SAIRN-hover2/hover-audit-log/hover-audit-log.jsonl`, alongside hover1's real one), I reproduced the break live:

```
$ python tools/hover_separation_audit.py
...
SELF-LOG CROSS-REFERENCE -- COULD NOT RUN
  MORE THAN ONE self-log found and none of them is authoritative:
      C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hover\hover-audit-log\hover-audit-log.jsonl
      C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hover2\hover-audit-log\hover-audit-log.jsonl

$ python tools/hover_process_pass_freshness.py
COULD NOT RUN: MORE THAN ONE self-log found and none of them is authoritative: ...
```

Both tools now refuse for **both** sessions simultaneously — a self-inflicted split-brain caused by the exact throughput fix (a second hover instance) that gap-1 needed.

## The fix, designed and driven against the real logs above (not a fixture)

**Principle:** more than one log is the expected shape once more than one hover instance runs, not evidence of a problem. Each log is still independently owned by its directory (already a stable identifier) and is verified on its own; nothing is ever fused into one chain or one verdict — the same "never fold a worse case into a better one" discipline both tools already use elsewhere (violations-found beats could-not-run beats clean; STALE beats WARN beats OK).

**`hover_separation_audit.py`:**
- `find_hover_log()` → new `find_hover_logs()`, returns every hit (0, 1, or many); `find_hover_log()` kept as a back-compat wrapper with its old ambiguous-list behavior unchanged.
- `read_hover_log()` → new `read_hover_logs()`, reads every discovered log independently, `{'path','session','rows','problem'}` per hit; `read_hover_log()` kept as a back-compat wrapper for any caller still on the single-log contract (now explains *why* it's refusing when count > 1, naming each session, rather than silently picking one).
- `main()`'s self-log section now loops over `read_hover_logs()`, running the **unchanged** per-log verify-chain + claimed-sha cross-check body once per session, printed under its own `-- <session> --` header. `violations` and `could_not_run` accumulate across sessions exactly as they did for one.
- `write_report()` takes `log_reports` (dict keyed by session) and renders one subsection per session — the CLI/exit-code path (the one actually used for pass/fail) was the priority; the markdown `--report` renderer got the minimum update needed to not crash, not a full redesign.

**`hover_process_pass_freshness.py`:**
- Calls `HSA.read_hover_logs()` instead of `HSA.read_hover_log()`; the freshness body is now `_check_one_session()`, called once per discovered log, printing its own verdict without exiting the process (the old `fail()` called `sys.exit(2)` directly, which would have killed the loop after the first session).
- Overall exit code = worst across sessions: any STALE → 1, else any COULD NOT RUN → 2, else 0. Same precedence `hover_separation_audit.py`'s own aggregate already uses.

## Driven proof, not asserted

Ran both patched tools for real against the two real logs that exist on this machine right now (hover1's 413-entry log, hover2's freshly-bootstrapped 1-entry log):

```
$ python hover_separation_audit.py        # patched copy, scratchpad
SELF-LOG CROSS-REFERENCE -- 2 log(s) found, one per session, each checked independently:
-- C--Users-marsh-Documents-SAIRN-hover --
  413 entries; hash chain re-derived independently: INTACT
  ...
-- C--Users-marsh-Documents-SAIRN-hover2 --
  1 entries; hash chain re-derived independently: INTACT
  ...

$ python hover_process_pass_freshness.py  # patched copy, scratchpad
-- C--Users-marsh-Documents-SAIRN-hover --
  ... OK: a process pass was recorded 20.3 hours ago, inside the 36-hour bound.
-- C--Users-marsh-Documents-SAIRN-hover2 --
  COULD NOT RUN: NO entry carries process_pass.
OVERALL: PART COULD NOT RUN (not a clean bill)
```

Both sessions now get an honest, independent answer instead of both refusing. hover2's own genuine "no process pass logged yet" state is correctly distinguished from hover1's genuine "OK, 20.3h" — neither swallows the other. `hover_process_pass_freshness.py --selftest` still passes 6/6 unchanged (the patch touches only `main()`, not `gaps()`/`epoch()`).

Full patched copies (not applied to the tracked repo): scratchpad `multilog-fix-proto/hover_separation_audit.py` and `hover_process_pass_freshness.py`, this session's temp directory.

## Scope flag, not silently resolved either way

Both files are git-tracked in the shared `tools/` directory. `tools/hover_auditor_scope_gate.py`'s own `ALLOWED` list (the mechanically-enforced boundary of what hover may itself edit/commit) does **not** include `tools/` at all — only the skill directory, the register, and hover's own claim file. `hover_separation_audit.py`'s own docstring states its rationale explicitly: it is deliberately built and maintained "from the build side... because an auditor enforcing its own separation proves nothing about the case where the auditor is the problem."

Read literally, that means hover editing this specific pair of files — even to fix a real, reproduced, self-inflicted bug — is the one edit the design goes out of its way to keep outside hover's own hands. I designed, wrote and proved the fix (the engineering Michael asked for), but have **not** applied it to the tracked files or committed anything, pending an explicit call on whether this file is inside or outside that boundary. If it's outside (my working assumption): route this proposal to a build agent as-is. If Michael intends this specific pair of files to be within hover's own operational-tooling exception after all: say so and I'll apply it directly.
