# SAIRN handoff — cody b40 (2026-10-21)

Five items. **Item 1 done, item 2 NOT DONE** (the permission layer denied it), item 3
stated, **item 4 closed as already wired** (Michael's decision), item 5 landed.
Nothing is half-finished.

## State
- `origin/main` = **`4868435442bcfbcae91476ed20ebab35e7a09ab5`**, read with
  `git ls-remote`; it equals HEAD. The only b40 repo change is
  `docs/2026-10-21-cody-b40-routed-to-hank.md`. No code changed.
- Pushed with no `--force` and no skip.
- Claim `sairnlegacy` (b40): **release after this commit.**

## Items
| # | item | state |
|---|---|---|
| 1 | Edit/Write deny for both hover clones (8 entries) | **DONE before b40.** All 8 are present in `.claude/settings.local.json`; that was the b34 item 4 run. **Verified:** an Edit into `SAIRN-hover/CLAUDE.md` and into `SAIRN-hover2/CLAUDE.md` is refused: *"File is in a directory that is denied by your permission settings."* The probe used an old-string that does not exist, so it could not write. **Write was not probed:** it has the same entry shape, but a probe that succeeded would create a file in the auditor's clone. |
| 2 | hank's Bash deny (`Bash(*SAIRN-hover*)` and 4 more; 13 total with the 8) | **NOT DONE.** The harness denied my Bash call, as it did in b34. I did not retry, and did not edit the file another way. |
| 3 | concept for F2/F3 | **A per-home setting may only WIDEN from the narrowest default, and nothing outside the owner's own stored choice can widen it.** No code was written: item 4 was already built. |
| 4 | wire F2/F3 | **ALREADY WIRED (b29).** `api/sd-data.js:~17080–17118` reads `sairnlegacy_settings` and calls `decide()` with all 5 arguments. b22 23/0, b29 21/0, leg-overlap 36/0, declinability 31/0. The missing piece, **an owner WRITE path**, is routed to hank on Michael's decision: `docs/2026-10-21-cody-b40-routed-to-hank.md`. |
| 5 | push, confirm | **LANDED** |

## Item 2 — Michael, two steps
**The shared script must be made case-sensitive first.** `C:\Users\marsh\fix-deny.ps1`
line 14 uses `-notcontains`, which ignores case. It would skip `Bash(*sairn-hover*)`
as a duplicate of `Bash(*SAIRN-hover*)`, leaving 12 of hank's 13. So:
1. In `C:\Users\marsh\fix-deny.ps1` line 14, change `-notcontains` to `-cnotcontains`.
2. In this window, type:

       ! powershell -ExecutionPolicy Bypass -File C:\Users\marsh\fix-deny.ps1 -Path "C:\Users\marsh\Documents\SAIRN-cody\.claude\settings.local.json" -Entries "Bash(*SAIRN-hover*)","Bash(*sairn-hover2*)","Bash(*sairn-hover/*)","Bash(*sairn-hover\*)","Bash(*sairn-hover*)"

   Expect `Done: ... now has 13 deny entries.` Then restart the window for it to apply.

**A side effect to know about:** `Bash(*sairn-hover*)` also denies any command that
names `.claude/skills/sairn-hover-auditor/`, such as a mirror diff of that skill.
Hank's clone already lives with this.

## Open
- hank: the F2/F3 owner write path (routed b40).
- Carried: cc (Tier A b31–b37); fourth (defects 7 and 8, active b49 claim).
