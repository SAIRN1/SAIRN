# SAIRN handoff — cody b42 (2026-10-21)

Three items, all done. **Every probe was refused.** Nothing is half-finished.

## State
- Only the b42 handoff, report and digest changed. No code. No SQL. No claim taken
  (local-config item, no app).
- `.claude/settings.local.json` is gitignored. I did not write to it this batch.

## Item 1: probes. ALL EIGHT REFUSED.
Same eight read-only `test -d` probes as b41, one Bash call each, sent in parallel:
`/c/.../SAIRN-hover`, `/c/.../SAIRN-hover2`, `/c/.../sairn-hover2`,
`/c/.../sairn-hover/`, `/c/.../sairn-hover2/`, `C:\...\sairn-hover\`,
`C:\...\sairn-hover2\`, `/c/.../sairn-hover`.
Each came back `Permission to use Bash with command ... has been denied.`
No marker printed. In b41 all eight ran.

## Item 2: not needed
No probe succeeded, so there was nothing inert to investigate. fix-deny.ps1 not run.

## Item 3: settings.local.json is otherwise unchanged
Read with `json.load` and compared to `.claude/settings.local.json.bak`
(10:46 today, before any deny entries existed):
- deny: 0 -> 13. Exactly the 8 Edit/Write entries + the 5 Bash entries.
  The inert joined `),Bash(` entry from b41 is gone.
- allow: 1007 -> 1007. Nothing added, nothing removed, same order.
- No other keys, in `permissions` or at the top level.

**One formatting difference, not content:** the file was re-serialised.
Indent 2 -> 4 spaces and LF -> CRLF (84,805 -> 92,550 bytes). That is the fix
command rewriting the file, not a stray edit. Claude Code reads it fine: the deny
list is in effect, as item 1 shows.

## Open
- `.claude/settings.local.json.bak` is still untracked in this clone. Michael's
  call whether to keep it. I left it.
- Not verified: other clones' deny lists. If any was built with the b40 `-File`
  command, it has the same inert joined entry. I did not read them.
- Side effect (from b40): `Bash(*sairn-hover*)` also denies any command naming
  `.claude/skills/sairn-hover-auditor/`.
- Carried: hank, the F2/F3 owner write path. cc, Tier A b31–b37. fourth, defects 7 and 8.
