# h1 b38 -- the "8 unattributed routing docs" board cell is counting a real limit, not 8 oversights

**Routed to cc** (owner of `tools/sairn_board_publish.py`, whose `routed_for()`
is where this count comes from). **Not committed to docs/ -- that is platform
territory, outside this role's scope**
(`tools/hover_auditor_scope_gate.py` refuses it, same reason the b34
weakening-flags sign-off had to be routed rather than applied directly). This
note records the verification; applying anything, if anything should be
applied, is for a non-hover session.

## What the board counts, and what it means today

`routed_for()` in `tools/sairn_board_publish.py` matches `docs/*.md` against
`-routed(?:-|$)` and separately counts how many of those do **not** also match
`-routed-to-<agent>`. That count is currently **8**, re-derived directly
against the live `docs/` listing with the tool's own two regexes (not copied
from an old board cell):

```
2026-10-07-cc-routed-b15.md
2026-10-07-cc-routed-b16.md
2026-10-07-fourth-routed-pinned-worktree-shared-config.md
2026-10-08-cc-routed-b17.md
2026-10-13-cc-routed-b5.md
2026-10-13-cc-routed-b7.md
2026-10-13-fourth-b10-routed-red-suites.md
2026-10-13-fourth-b11-routed-acknowledgement.md
```

## Each one read in full -- none is a naming oversight

A background agent read all 8 documents in full (not headers/filenames) and
reported, per file, who actually wrote it, who the content is addressed to,
and whether a single `-routed-to-<agent>` rename would be accurate:

| file | recipients found inside the body | would a single rename be accurate? |
|---|---|---|
| `...-cc-routed-b15.md` | michael, cody, fourth, hank | **No** -- genuinely 4-way split |
| `...-cc-routed-b16.md` | cody, fourth, michael | **No** -- cody heaviest but fourth's section is a real, substantial deliverable |
| `...-fourth-routed-pinned-worktree-shared-config.md` | nobody named as owner (routed "for scheduling," the only individual named gets a secondary item) | **No** -- would overstate the one name that does appear |
| `...-cc-routed-b17.md` | mostly nobody (cc's own sweep report); §6 names hank for 2 items, 2 rows explicitly unowned | **No** -- ~80% of the document isn't routed to hank or anyone |
| `...-cc-routed-b5.md` | michael (decision), fourth/ted (owns a section by name), cody, hank, cloud | **No** -- no dominant party |
| `...-cc-routed-b7.md` | mostly cc's own batch-completion report; one unnamed forward-pointer | **No** -- this is closer to a self-report than a routing doc |
| `...-fourth-b10-routed-red-suites.md` | hank (`api/`, 5 rows) and cody (`tests/`, 79 rows) | **No** -- cody has more volume but hank's assignment is real and distinct; a cody-only rename drops it |
| `...-fourth-b11-routed-acknowledgement.md` | fourth auditing whether EARLIER findings were acknowledged -- not itself routing anything new | **Different category entirely.** This measures acknowledgement (`ACK_COMMIT`/`ACK_CLAIM`/`ACK_STATUS`/`ACK_DECIDED`/`MENTION_ONLY`/`UNACK`); the named/unattributed binary doesn't really apply to it |

**The pattern across all 8: they were never missing a `-routed-to-X` suffix by
accident. Seven are genuinely multi-recipient documents that route different
individual findings to different people inside one file, and the eighth is a
different kind of artifact (an acknowledgement audit) that the convention was
never designed to describe.** Forcing a single-recipient rename on any of
them would make the filename **less** accurate than leaving it alone, not
more -- a reader would see `-routed-to-hank` on `...-cc-routed-b17.md` and
reasonably assume the document is about hank, when ~80% of it is cc's own
sweep addressed to no one.

## What this means for the board cell, and the one real option

**This is not 8 things to fix by renaming files.** The board's
`"plus 8 routing doc(s) naming no recipient in the filename, not attributed
here"` line is accurately describing the convention's own coverage limit, the
same way it already correctly describes itself ("BY FILENAME CONVENTION, and
that is said out loud rather than presented as a complete list"). The honest
options, for whoever owns this tool to weigh, are:

1. **Leave it as-is.** The line already discloses the gap rather than hiding
   it -- arguably nothing is actually broken here.
2. If a finer-grained count is wanted, change `routed_for()`'s *definition*
   of "attributed" from a single filename suffix to **any `-routed-to-X`
   substring OR a body match against a short list of routing-section
   headers/phrases** (several of the 8 do say "Routed to: X" or similar
   inline) -- a real code change to `tools/`, not a docs/ rename, and
   therefore cc's call, not this role's.
3. Re-file `...-fourth-b11-routed-acknowledgement.md` out of the `-routed-`
   bucket entirely (rename to something like `...-ack-recheck.md`), since it
   is not a routing document in the sense the other 15 matching files are --
   this is the one of the 8 where a rename would be an accuracy
   *improvement* rather than a forced simplification, but it is still a
   `docs/` edit and still routed here rather than applied.

No action taken on any file. Logged to the hover chain alongside this note.
