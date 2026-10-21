# SAIRN handoff — hank b36 — 2026-10-21

**Subject:** the hover deny-list applied to this clone and confirmed; context discipline made durable as a
standing memory rule. No application code changed. Written before the report, nothing half-finished.

## 1. PUSHED STATE
This batch commits only these three documents (re-derive the tip after the push). **NOT FORCED.**
`.claude/settings.local.json` is gitignored (`.gitignore:1`), so the deny fix is local to this clone by design.

## 2. CLAIMS HELD
None.

## 3. THE ITEMS
1. **Deny-list fix — RAN, CONFIRMED.** The command as given (`-File … -Entries "a","b"`) printed only the
   PowerShell banner and wrote nothing: under `-File` the comma list does not arrive as an array. Re-run as
   `powershell -NoProfile -ExecutionPolicy Bypass -Command "& 'C:\Users\marsh\fix-deny.ps1' -Path '…' -Entries 'a','b',…"`
   → `Done: … now has 8 deny entries.` Grep finds all eight at lines 1219–1226 (`Edit`/`Write` × `SAIRN-hover`,
   `SAIRN-hover2` × the `//C:/…` and `~/…` forms); the file still parses (allow 1213, deny 8).
   **Side effect to know:** PowerShell 5.1's `Get-Content`/`Set-Content` re-encode as ANSI, so the one non-ASCII
   allow rule (line ~314, box-drawing chars in an `awk` command) may now read `??`. Harmless, but the same
   `-File` array trap will hit the other clones if the command is pasted as given.
2. **Context discipline — FIXED AS A STANDING RULE.** Concept: *output enters context only as failures and
   counts; anything longer goes to a file that is grepped.* Recorded as memory
   `filter-output-before-it-enters-context` (indexed in MEMORY.md): every gate/suite run filtered to
   `FAIL|passed|failed|exit|Blocked|REFUSED|->`, refusals grepped for their heading, app files over ~1000
   lines read by grep or line range only. **Context now: 79.5%** (measured) — the rule cannot lower what is
   already spent; it governs the next session.
3. **Methodology:** the one new piece of logic is the rule above; its concept is stated there.
4. **Push:** §1.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| A | other clones' deny lists | run the `-Command` form above per clone; the `-File` form silently does nothing |
| B | snapshot re-export (b35 G) | Michael, per `SAIRN-handoff-hank-b35.md` §4 |
| C | Static Maps on the Maps key (b35 D) | Michael |
| D | untracked `conflict_excerpt.txt`, `full_conflict.txt`, `dir` in this clone | not mine, not touched — whoever wrote them |
| E | this session is at 79.5% | next batch should start a fresh session |

## 5. TRANSCRIPT
    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\8dd2a9db-f15f-4fee-9950-08bcb26892c0.jsonl
