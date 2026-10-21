# SAIRN handoff — hank b38 — 2026-10-21

**Subject:** Bash deny for the two hover clones (item H); item G closed; item C held. No application code
changed. Written before the report, nothing half-finished.

## 1. PUSHED STATE
This batch commits only these three documents. **NOT FORCED.** Re-derive the tip after the push.
`.claude/settings.local.json` (untracked, this clone only) is now **13 deny / 1213 allow** — Michael ran the
writes; the auto-mode classifier refused my own write to it as self-modification, and I did not route around it.

## 2. CLAIMS HELD
None (released at the end of the batch).

## 3. THE ITEMS
1. **G — closed by Michael's decision.** Build agents never write to SAIRN-hover or SAIRN-hover2; the eight
   Edit/Write deny entries are correct as written. Concept: *the deny is the specification, so every expectation
   about a build-agent write into a hover clone is "refused", and the record that said otherwise is corrected, not
   the rule.* Searched `tools/`, `docs/`, `tests/`, `.claude/`: no test or doc expects such a write to succeed —
   the only "must succeed" was the b37 dispatch text, and b37 §4 item G is superseded by this line.
2. **H — Bash deny, not a hook.** Concept: *Bash cannot be write-scoped by pattern, so deny every Bash command
   whose text names a hover clone; reads stay available through Read/Grep.* Hook rejected because hooks are
   disarmed by standing decision (`.claude/settings.json` `_hooks_note`). Entries now in this clone:
   `Bash(*SAIRN-hover*)` and `Bash(*sairn-hover*)` (plus three narrower lowercase entries made redundant).
   **Probe (read-only `ls -d`, never a write):** refused — `/c/.../SAIRN-hover2`, `/c/.../sairn-hover/`,
   `true && ls -d C:/.../SAIRN-hover`, `C:\...\sairn-hover\`. Positive control `ls -d .../SAIRN-cody` ran.
   **Two defects found on the way:** (a) `Bash(*sairn-hover\*)` did not match a backslash path — `\*` reads as a
   literal `*`; (b) `~/fix-deny.ps1` dedups with `-notcontains`, which is case-INsensitive, so it silently skipped
   `Bash(*sairn-hover*)` as a duplicate of the uppercase entry, while Claude Code's matching IS case-sensitive.
   The case-sensitive copy used is `add-deny-cs.ps1` (scratchpad, this session).
   **Residual, by construction:** other casings (`Sairn-Hover`), globs (`SAIRN-h*`), a path built in a variable,
   a script that writes internally, and the PowerShell tool (not in my tool set; untested). This is a guardrail
   against an accidental write, not containment.
3. **C — held, needs Michael's Google Cloud access.** `api/route-map.js` already calls Static Maps with
   `GOOGLE_MAPS_API_KEY`; enabling the Maps Static API on that key's project (and adding it to the key's API
   restrictions if any) is a Cloud Console action. Not attempted.
4. **A — dropped** from my queue per dispatch (Michael runs it on cc, fourth, H1).

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| H2 | Bash deny on cc, cody, fourth | Michael: run `add-deny-cs.ps1` (or fixed `fix-deny.ps1`) with `-Path` = that clone's `settings.local.json`, `-Entries 'Bash(*SAIRN-hover*)','Bash(*sairn-hover*)'`. **NOT on H1/hover/hover2** — it would block the auditor naming its own clone |
| H3 | `~/fix-deny.ps1` case-insensitive dedup | Michael: change `-notcontains` to `-cnotcontains` (file is outside the repo) |
| C | Static Maps on the Maps key | Michael, Cloud Console |
| B | snapshot re-export (b35 G) | Michael, per `SAIRN-handoff-hank-b35.md` §4 |
| D | untracked `conflict_excerpt.txt`, `full_conflict.txt`, `dir`, `resolve_conflict.py`, `schema_snapshot_raw.json`, `.claude/settings.json*.bak` | not mine, not touched |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
