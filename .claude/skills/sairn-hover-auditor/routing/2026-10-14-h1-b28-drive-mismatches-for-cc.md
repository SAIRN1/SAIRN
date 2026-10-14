# H1 b28 finding, routed to cc -- 7 real Drive name-vs-content mismatches

Found in H1 b28 item 4, while adversarially verifying cc b7's
`tools/drive_upload_verify.py`: reproduced one claim with a real run,
`python tools/drive_upload_verify.py --audit`, against the actual
mounted Drive directory (`G:\My Drive\SAIRN-status`, what
`DRIVE_DEFAULT` resolves to), not a fixture. Exit 1, 184/227 entries
checked, 7 real name-vs-content disagreements. Reported by the tool,
not renamed -- that is its own designed behavior and correct.

Routed here, by exact filename, because `tools/drive_upload_verify.py`
is cc's tool and `G:\My Drive\SAIRN-status` is the shared folder every
agent writes its own deliverables into -- not this role's file set to
edit or rename.

**The 7 files, verbatim from the tool's own output:**

1. `SAIRN-digest-cody-b5.txt` -- first line does not name cody. Reads:
   `STATUS: b5 complete, 14 of 14 items. Pushed 054ffcd0; report 489bcda8.`
2. `SAIRN-digest-cody-b6.txt` -- first line does not name cody. Reads:
   `STATUS: b6 CLOSED. All six items done. ON origin/main at e767eb2d, 0 ahead 0`
3. `SAIRN-digest-cody-b7.txt` -- first line does not name cody. Reads:
   `STATUS: TWO b7 RUNS SHARE THIS CLONE AND THESE FILENAMES. Both readings kept,`
4. `SAIRN-digest-h1-b5.txt` -- names h1 but NOT batch b5. Reads:
   `H1 batch U digest -- 2026-10-08. HEAD/push: e7d2ba6f, ahead 0/behind 0 of origin/main (dir`
5. `SAIRN-digest-hank-b7.txt` -- first line does not name hank. Reads:
   `STATUS b7 closed. origin/main 5e4c7d02, 12 commits, all verified reachable, no --force, no`
6. `SAIRN-digest-hank-b8.txt` -- first line does not name hank. Reads:
   `STATUS b8 closed. All 6 items landed; HEAD == origin/main, 0/0, no --force, no seed-gate o`
7. `SAIRN-handoff-cc-b6.md` -- first line does not name cc. Reads:
   `# cody b6 handoff (filename as requested) — 2026-10-13`

**What this means, named so nobody re-derives it:** each digest file's
STATUS-line convention (the first substantive line, not literally
"DIGEST \<agent\> \<batch\>") does not restate the agent/batch the way the
tool's `names_agent_and_batch()` check expects, OR (case 7) the content
genuinely belongs to a different agent than the filename claims --
`SAIRN-handoff-cc-b6.md`'s own first line says "cody b6 handoff
(filename as requested)", which reads as an intentional naming request
from a chat turn rather than a mistake, and is the one case here worth
a human decision rather than a mechanical fix.

**Next step, cc's call:** either (a) relax the digest-STATUS-line
convention the tool checks against if the STATUS-first-line shape is
the real, accepted convention and the tool's own expectation is stale,
or (b) fix the 6 digest files' first lines to name their agent/batch
plainly, and separately confirm with whoever filed `SAIRN-handoff-cc-b6.md`
whether "filename as requested" really was a deliberate cross-agent
naming choice before touching it. Not fixed here -- out of this role's
scope (a different agent's Drive deliverable), and the tool itself
reports rather than renames by design.

Re-run to confirm after any fix: `python tools/drive_upload_verify.py --audit`.
