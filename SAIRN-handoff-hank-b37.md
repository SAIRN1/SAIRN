# SAIRN handoff — hank b37 — 2026-10-21

**Subject:** verbatim `-Command` form of the deny-list fix for the other clones; native Write/Edit probe of
this clone's deny list. No application code changed. Written before the report, nothing half-finished.

## 1. PUSHED STATE
This batch commits only these three documents, rebased onto `c71917d62` (re-derive the tip after the push).
**NOT FORCED.** `.claude/settings.local.json` is unchanged this batch (still 8 deny / 1213 allow).

## 2. CLAIMS HELD
None.

## 3. THE ITEMS
1. **Verbatim command** — taken from the b36 transcript tool call, not retyped. Run from this clone's Git Bash;
   the quoting also holds in a PowerShell prompt (no `$` in it). Each clone changes `-Path` only:

       powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& 'C:\Users\marsh\fix-deny.ps1' -Path 'C:\Users\marsh\Documents\SAIRN-hank\.claude\settings.local.json' -Entries 'Edit(//C:/Users/marsh/Documents/SAIRN-hover/**)','Write(//C:/Users/marsh/Documents/SAIRN-hover/**)','Edit(//C:/Users/marsh/Documents/SAIRN-hover2/**)','Write(//C:/Users/marsh/Documents/SAIRN-hover2/**)','Edit(~/Documents/SAIRN-hover/**)','Write(~/Documents/SAIRN-hover/**)','Edit(~/Documents/SAIRN-hover2/**)','Write(~/Documents/SAIRN-hover2/**)'"

   Success prints `Done: <path> now has N deny entries.` — no `Done:` line means it did not run.
2. **Probe — hover2 REFUSED (as required); hover ALSO REFUSED (dispatch said it must succeed).** Native `Write`
   (new file) and `Edit` against `SAIRN-hover2\hank-b37-deny-probe.txt` and `SAIRN-hover\hank-b37-deny-probe.txt`:
   all four returned `File is in a directory that is denied by your permission settings.` Positive control: a
   `Write` to this session's scratchpad succeeded, so the refusal is path-specific, not blanket. `ls` confirms
   no probe file landed in either clone. The only deny source is this clone's `settings.local.json`
   (user `settings.json` lists both clones only at lines 268–269, outside `deny`).
   **Why hover is refused:** the b36 entry list, as dispatched, denies both clones; and CLAUDE.md says a build
   agent must not reach into `SAIRN-hover`. The "must succeed" expectation contradicts both. Not changed —
   Michael's call (item G).
3. **Methodology:** see report item 3.
4. **Push:** docs only, §1.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| A | cc, cody, fourth, H1 deny lists | send §3.1 with `-Path` set to each clone's own `settings.local.json`; then run the same 4-call probe there |
| G | hover expectation mismatch | Michael: if hover must be writable, drop the 4 `SAIRN-hover/**` entries from the list before sending A; else correct the expectation |
| H | deny covers native Edit/Write only — a Bash write (`echo > …`) into either clone is not blocked by these rules | Michael: decide whether a Bash deny or a hook is wanted; not probed by writing, by design |
| B | snapshot re-export (b35 G) | Michael, per `SAIRN-handoff-hank-b35.md` §4 |
| C | Static Maps on the Maps key (b35 D) | Michael |
| D | untracked `conflict_excerpt.txt`, `full_conflict.txt`, `dir`, `resolve_conflict.py`, `schema_snapshot_raw.json`, `.claude/settings.json*.bak` | not mine, not touched |

## 5. TRANSCRIPT
    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\aa095c27-2afe-4239-b582-2bf409c0757f.jsonl
