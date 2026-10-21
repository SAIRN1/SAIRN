# SAIRN handoff — cody b41 (2026-10-21)

Three items. **Item 1 answered** (root cause found and reproduced). **Item 2 NOT DONE:**
every probe ran, none was refused, and the harness denied my fix. **Item 3:** only
these deliverables changed in the repo. Nothing is half-finished.

## State
- Only the b41 handoff, report and digest changed. No code changed. No SQL.
- `.claude/settings.local.json` is gitignored. Nothing I did changed it (the write was denied).
- No claim was taken: this is a local-config item with no app.

## Item 1: why fix-deny.ps1 said 9, not 13
**None of the five were already present. The five were stored as ONE entry.**
Here is the deny list now, read with `json.load`, entry 8 verbatim:

    'Bash(*SAIRN-hover*),Bash(*sairn-hover2*),Bash(*sairn-hover/*),Bash(*sairn-hover\\*),Bash(*sairn-hover*)'

The b40 handoff told Michael to run `powershell ... -File fix-deny.ps1 ... -Entries "a","b",...`.
**Under `-File`, PowerShell does not turn a comma list into an array.** `$Entries`
arrives as one string with the commas inside it. So the count was 8 + 1 = 9.
Nothing was dropped as a duplicate (the `-cnotcontains` fix from b40 is in place,
line 14). **The b40 command was wrong. That was my error.**
Reproduced with a test script in the scratchpad: `-File` gives `count=1`;
the same list under `-Command "& 'script' -Entries 'a','b',..."` gives `count=5`.

That one entry is **in effect inert.** Its pattern only matches a command that
literally contains the text `),Bash(`.

## Item 2: probes. NO variant is denied.
I ran eight read-only `test -d` probes. **All eight ran and printed their marker.**
None was refused by the permission layer:
`/c/.../SAIRN-hover`, `/c/.../SAIRN-hover2`, `/c/.../sairn-hover2`,
`/c/.../sairn-hover/`, `/c/.../sairn-hover2/`, `C:\...\sairn-hover\`,
`C:\...\sairn-hover2\`, `/c/.../sairn-hover`.
Each probe checks that the directory exists. None lists or reads anything inside it.

**The fix was denied.** I tried to run fix-deny.ps1 in the corrected `-Command` form.
The harness denied that Bash call, the third time this has happened (b34, b40, b41).
I did not retry it and did not try another route.

### Michael: one command, then restart
Run this in the cody window. It is the form tested above. Use `-Command`, not `-File`:

    ! powershell -NoProfile -ExecutionPolicy Bypass -Command "& 'C:\Users\marsh\fix-deny.ps1' -Path 'C:\Users\marsh\Documents\SAIRN-cody\.claude\settings.local.json' -Entries 'Bash(*SAIRN-hover*)','Bash(*sairn-hover2*)','Bash(*sairn-hover/*)','Bash(*sairn-hover\\*)','Bash(*sairn-hover*)'"

Expect `now has 14 deny entries`: the 8 Edit/Write entries, the inert joined one,
and the 5 new ones.
**Optional cleanup** to remove the inert joined entry (the count becomes 13):

    ! python -c "import json;p=r'C:\Users\marsh\Documents\SAIRN-cody\.claude\settings.local.json';d=json.load(open(p,encoding='utf-8-sig'));d['permissions']['deny']=[x for x in d['permissions']['deny'] if '),Bash(' not in x];json.dump(d,open(p,'w',encoding='utf-8'),indent=4);print(len(d['permissions']['deny']))"

**Check the other clones too.** If hank's (or anyone's) deny list was built with the
same `-File` command, it has the same single inert entry. That is not verified:
I did not read any other clone's settings.

## Open
- Michael: the command above, then a restart. Next cody batch: re-run the 8 probes.
  Every probe should be refused.
- Side effect (from b40): `Bash(*sairn-hover*)` will also deny any command that
  names `.claude/skills/sairn-hover-auditor/`.
- Carried: hank, the F2/F3 owner write path. cc, Tier A b31–b37. fourth, defects 7 and 8.
