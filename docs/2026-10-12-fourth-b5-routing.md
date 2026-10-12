# Routing only -- fourth, batch b5, 2026-10-12

Measured at HEAD `327e9e80`. **NOTHING IN THIS DOCUMENT WAS FIXED.** Every table is
a routing table: owner, exact `file:line`, one row per item. Where an owner
could not be derived from a record it says `UNOWNED`, which is an answer --
not a blank and not a guess.

## 1. The 36 open SEQ 17-A findings (brief item 6)

Carried from `docs/2026-10-07-fourth-routed.md:1698`, where the 17 sites and
their per-site magnitudes were recorded. The arithmetic was re-derived by a
parser this batch rather than read off the summary: the REAL table sums to
**36 across 17 sites** and the WITHDRAWN table to **7 across 6**, 36+7 = 43
and 17+6 = 23, matching the summary block at `:1673-1679`.

**WHY THERE ARE 36 ROWS AND ONLY 17 DISTINCT LINES, stated rather than left
to be noticed.** A magnitude of 14 at one site means batch 17 counted 14
findings there -- 14 keys flowing through ONE derived set -- and it never
recorded a separate line per key. So the site line is the exact location of
every finding at that site, and the `#k of n` column is the ordinal within
the site, not a second position. Splitting them further would mean inventing
line numbers batch 17 did not measure.

| # | file:line | #k of n | subject | app | owner | route to | why the hazard reaches it |
|---|---|---|---|---|---|---|---|
| 1 | `tests/licence_rekey_isolation.js:400` | 1 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | subject is `expr`, accumulated at :388-393 from `src.slice(at).split("\n")` over an app file; a commented-out key enters `keys` then `foreign`, which is an assertion about cross-app key leakage |
| 2 | `tests/licence_rekey_isolation.js:400` | 2 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 3 | `tests/licence_rekey_isolation.js:400` | 3 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 4 | `tests/licence_rekey_isolation.js:400` | 4 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 5 | `tests/licence_rekey_isolation.js:400` | 5 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 6 | `tests/licence_rekey_isolation.js:400` | 6 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 7 | `tests/licence_rekey_isolation.js:400` | 7 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 8 | `tests/licence_rekey_isolation.js:400` | 8 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 9 | `tests/licence_rekey_isolation.js:400` | 9 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 10 | `tests/licence_rekey_isolation.js:400` | 10 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 11 | `tests/licence_rekey_isolation.js:400` | 11 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 12 | `tests/licence_rekey_isolation.js:400` | 12 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 13 | `tests/licence_rekey_isolation.js:400` | 13 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 14 | `tests/licence_rekey_isolation.js:400` | 14 of 14 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #1 |
| 15 | `tests/sairnbiz_incidents_kpi.js:264` | 1 of 1 | APP-SLICE | SAIRNbiz | cody | cody -- the SAIRNbiz owner by the b6 directory rule | subject is `m[1]` from `/var SB_SYNCED\s*=\s*\[([^\]]*)\]/.exec(html)` at :262 -- the SB_SYNCED array body in the app |
| 16 | `tests/sairnbiz_server_backup.js:191` | 1 of 1 | APP-SLICE | SAIRNbiz | cody | cody -- the SAIRNbiz owner by the b6 directory rule | subject is `clientList = slice(html, "var SB_SYNCED=['sb_invs'", "];")` at :190 |
| 17 | `tests/sairncode_gates.js:301` | 1 of 1 | api/sd-data.js SLICE | SAIRNcode | cody | cody -- the SAIRNcode owner by the b6 directory rule | subject is `m[1]` from SC_TIER_A_WRITE_ROLES_BY_RESOURCE in api/sd-data.js at :297-299 -- source code, so the hazard is real, but NOT an app file, so batch 17 measured its magnitude against a file this site never reads |
| 18 | `tests/sairnlegacy_processions_isolation.js:72` | 1 of 1 | APP-SLICE | SAIRNlegacy | cody | cody -- the SAIRNlegacy owner by the b6 directory rule | subject is `mapBlock = API.slice(mapStart, API.indexOf("};", mapStart))` at :71 |
| 19 | `tests/sairnlegacy_session_gate_review_probe.js:202` | 1 of 1 | APP-SLICE | SAIRNlegacy | cody | cody -- the SAIRNlegacy owner by the b6 directory rule | subject is `m` from `html.match(/var (DATA_API\|AUTH_API\|PROXY)\s*=\s*'([^']+)'/g)` at :201; a commented-out endpoint constant becomes a live endpoint in `consts`. TAKE THIS ONE FIRST: its own comment records that its first spelling was vacuous in the reassuring direction |
| 20 | `tests/sairnlegacy_write_failure_voice.js:197` | 1 of 1 | APP-SLICE | SAIRNlegacy | cody | cody -- the SAIRNlegacy owner by the b6 directory rule | subject is `m[1]` from `sites`, derived from SRC (the app) |
| 21 | `tests/seed_never_syncs_platform.js:105` | 1 of 2 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | subject is `b.body` from `bodyOf(src, m.index)` at :103, where `src` is every root .html read at :99 |
| 22 | `tests/seed_never_syncs_platform.js:105` | 2 of 2 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #21 |
| 23 | `tests/seed_never_syncs_platform.js:147` | 1 of 5 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | subject is `m[2]` from the *_SYNCED array body in `app.src` at :145 |
| 24 | `tests/seed_never_syncs_platform.js:147` | 2 of 5 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #23 |
| 25 | `tests/seed_never_syncs_platform.js:147` | 3 of 5 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #23 |
| 26 | `tests/seed_never_syncs_platform.js:147` | 4 of 5 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #23 |
| 27 | `tests/seed_never_syncs_platform.js:147` | 5 of 5 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #23 |
| 28 | `tests/seed_never_syncs_platform.js:250` | 1 of 1 | APP-WHOLE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | subject is `app.src` itself -- the whole unstripped app file. The ONLY whole-app subject of the 23, so the one site where batch 17 measured the right thing |
| 29 | `tests/seed_never_syncs_platform.js:274` | 1 of 2 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | subject is `b.body` again. TAKE THIS ONE EARLY: the comment at :263-269 records that this site already lost a round to a regex that silently matched nothing |
| 30 | `tests/seed_never_syncs_platform.js:274` | 2 of 2 | APP-SLICE | PLATFORM (all apps) | cody | cody -- the PLATFORM (all apps) owner by the b6 directory rule | same site, same subject as #29 |
| 31 | `tests/sen_hydrate_comparator_review_probe.js:209` | 1 of 1 | TEST-FILE SOURCE | SAIRNsenior | cody | cody -- the SAIRNsenior owner by the b6 directory rule | subject is `names[0]` from `SUBJECT.match(...)`, SUBJECT being tests/sairnsenior_hydrate_delegation_review_probe.js read at :20-21. JS source with comments, so real; not an app, so the magnitude was wrong |
| 32 | `tests/sen_hydrate_comparator_review_probe.js:210` | 1 of 1 | TEST-FILE SOURCE | SAIRNsenior | cody | cody -- the SAIRNsenior owner by the b6 directory rule | same subject, second block |
| 33 | `tests/stonedesk_server_backup.js:47` | 1 of 1 | api SLICE | StoneDesk | cody | cody -- the StoneDesk owner by the b6 directory rule | subject is `body = api.slice(at, api.indexOf("};", at))` at :45 |
| 34 | `tests/stonedesk_server_backup.js:55` | 1 of 1 | api SLICE | StoneDesk | cody | cody -- the StoneDesk owner by the b6 directory rule | same `body` |
| 35 | `tools/citation_drift_hook.py:411` | 1 of 1 | ITS OWN .py SOURCE | PLATFORM tooling | cc | cc -- the PLATFORM tooling owner by the b6 directory rule | subject is `lines = io_read_lines(REPO/me)` at :406 -- the hook reads ITSELF to derive a self-test fixture. A comment-borne identifier can be chosen as the anchor, which makes the fixture weaker rather than wrong. REAL but low-consequence, and said so |
| 36 | `tools/citation_drift_hook.py:416` | 1 of 1 | ITS OWN .py SOURCE | PLATFORM tooling | cc | cc -- the PLATFORM tooling owner by the b6 directory rule | same `lines`, second pass |

**ALL 17 FILES COME BACK `UNOWNED`, and the test was mechanical:** no
`# OWNER:` / `// OWNER:` header in the first 4KB, no live claim declaring the
path in its `FILES` list, and absent from both run tables (they are GREEN
suites, so a failure table could not name them). The `app` column is derived
from the path token or, for the two platform-wide suites, from the fact that
they read every root `.html`. **An owner derived from an app is a routing
hint and not an owner**; the standing fix is the `# OWNER:` backlog --
`tools/tool_owner_header_check.py` reports 264 `tools/*.py` with no header,
and these 17 are the same gap one directory over.

## 2. The 6 standing documents over the 400,000-byte ceiling that are NOT mine (brief item 7)

`python tools/tooling_inventory.py --standing-doc-sizes` -> **EXIT 1**, 6
documents over, measured at HEAD `327e9e80`. It was SEVEN at the start of this
batch; `SAIRN-ACTIVE-WORK-fourth.md` was the seventh and is now 369,849
bytes (brief item 5). **None of the remaining six is mine and none was
touched.**

| document | bytes | over by | owner | owner basis | note for the owner |
|---|---:|---:|---|---|---|
| `docs/SAIRN-OPEN-WORK-INDEX.md` | 2,380,170 | 1,980,170 | SHARED -- no single owner | four sessions append to it | cc's batch W item 13 already carries the split: *"SAIRN-OPEN-WORK-INDEX.md split into a short current index plus an archive"*. Not re-routed here; confirmed still outstanding and still over. |
| `SAIRN-ACTIVE-WORK-cc.md` | 1,095,644 | 695,644 | cc | the filename names the session | same split this batch just did on mine, and the active half will not fit in one file: mine needed TWO archive parts. Expect the same. |
| `SAIRN-ACTIVE-WORK-hank.md` | 945,301 | 545,301 | hank | the filename names the session | as above. |
| `SAIRN-ACTIVE-WORK-cody.md` | 782,848 | 382,848 | cody | the filename names the session | as above. |
| `docs/CRITICALITY-TIERS.md` | 485,668 | 85,668 | cody (contested) | cody declared it in a claim FILES list; the claim tool's own header records cody and hank claiming it 6 seconds apart | the register is a table, so a split must not cut a row -- rebuild rows whole (PR 2.1). |
| `SAIRN-ACTIVE-WORK.md` | 404,183 | 4,183 | SHARED -- superseded | the pre-2026-08-24 shared log, replaced by the four per-session files | nothing appends to it any more, so this one is an ARCHIVE question rather than a split: it is 4,183 bytes over and has been inert since the split. |

## 3. The 39 private comment-strippers NOT consolidated this batch (brief item 4, the remainder)

A whole-tree inventory found **44 private comment-strip sites across 23
files** -- not the eight batch b4 named, which was a count of distinct
IMPLEMENTATIONS among a smaller scanned set. **5 of the 44 were replaced** in
`tests/faults/grd_write_faults.js` (the named eighth at `:385` plus four more
in the same file that the inventory found); `grep` reports 0 left there.

**The other 39 are routed and NOT edited, for a reason that is about
correctness and not caution.** Swapping a `//`-only strip for the shared
library changes what text remains, so it can flip an absence assertion in
EITHER direction; each file therefore needs its own before/after run of its
own suite. These 22 files are other sessions' and none is in my claim's
`FILES` list. Doing 22 unverified edits across other sessions' suites to
close a tidiness item is how a consolidation breaks a platform.

**The consolidation target for JS is `tests/lib/strip_comments.js`** --
`stripComments(html)` for a whole app file, `stripJs(src)` for a bare JS
fragment. `tools/jscomments.py` is the PYTHON half of the same
consolidation and cannot be required from node; the brief's wording names it
and this is the note that the JS callers need its counterpart instead.

| file | sites | lines | shape |
|---|---:|---|---|
| `api/_lib/courtlistener-rate-limit.test.js` | 2 | :224, :266 | line-// |
| `api/_lib/deadline-endpoint-inputs.test.js` | 1 | :38 | block-/* + line-// |
| `api/_lib/deadline-jurisdiction-labels.test.js` | 1 | :61 | block-/* + line-// |
| `api/_lib/dental-gfe.test.js` | 5 | :159, :174, :183, :223, :233 | line-// |
| `api/_lib/mech-assets.test.js` | 1 | :99 | line-// |
| `api/alf-append-only-read-order.test.js` | 1 | :192 | line-// per line |
| `api/greeting.test.js` | 1 | :96 | block-/* + line-// |
| `api/sairndental/public-book-guardian.test.js` | 3 | :131, :152, :171 | line-// |
| `api/sairnvet-transcribe.test.js` | 1 | :152 | block-/* quoted in a comment |
| `tests/faults/alf_rule_read_faults.js` | 3 | :262, :271, :284 | line-// |
| `tests/faults/sd_write_faults.js` | 2 | :269, :316 | line-// |
| `tests/intake_form_public_surface.js` | 1 | :171 | line-// |
| `tests/intake_link_no_credential.js` | 1 | :142 | line-// |
| `tests/intake_no_false_success.js` | 1 | :350 | line-// |
| `tests/ld_reports_unreadable.js` | 1 | :188 | line-// |
| `tests/roofing_claim_gate_single_source.js` | 5 | :135, :171, :186, :212, :330 | line-// |
| `tests/sairndesign_po_procurement.js` | 1 | :190 | html-comment |
| `tests/sb_sync_badge_honesty.js` | 1 | :164 | line-// |
| `tests/sd_timesheet_pay_est.js` | 4 | :128, :139, :157, :191 | line-// |
| `tests/st_reports_failure.js` | 1 | :191 | line-// |
| `tests/stonedesk_admin_storage_kpi.js` | 1 | :76 | block-/* |
| `tests/sv_storage_guard.js` | 1 | :355 | line-// |

**39 sites across 22 files.** 5 replaced + 39 routed = 44 found.

## 4. Routed from brief item 3 -- the cascade mechanism, and what is NOT established

`tests/phi_cache_scoped_to_user.js` is **72 passed / 0 failed alone, exit 0**,
re-measured three times this batch, and hank's 2026-10-08 table records it as
`63 passed, 1 failed` in the whole-tree run. The precondition that converts
that into `SKIPPED` rather than `FAIL` is in my own file and is done (item 3).
What is ROUTED is the mechanism underneath it:

| finding | file:line | owner | what to do |
|---|---|---|---|
| the atexit restore net calls `git checkout --` and never reads the return code, so with `core.bare = true` set by an earlier probe the restore SILENTLY DOES NOTHING | `tests/seam_check/run_delegation_probe.py:76` | cody (NAMED OVERRIDE in the b6 brief) | check the return code and fail loud; a restore that cannot verify itself is the third state, not a pass |
| the same in the context manager's `finally` | `tests/seam_check/run_delegation_probe.py:113` | cody | as above |
| the SENTINEL is removed whether or not the checkout landed, so the one layer that was meant to leave evidence of a failed restore CLEARS ITSELF | `tests/seam_check/run_delegation_probe.py:80` and `:119` | cody | remove the sentinel only after the restore verifies |
| a probe leaves `core.bare = true` behind, which is what disarms every `git`-based restore and every `git status` watch-list on the platform | `tests/push_gate/check8_probe.py:209` | **cody** (NAMED OVERRIDE) | this is where the behaviour is recorded. Stop leaving it set, or set it back in a `finally` that verifies |
| the DETECTOR for that state reports and nothing REFUSES on it -- and with this clone's hooks off by instruction it does not even run at session start | `tools/clone_health_check.py:209-211` | **cc** (NAMED OVERRIDE) | split out of the row above on 2026-10-13: ONE row naming two files with two different owners is a routing line neither of them can act on |

**MEASURED THIS BATCH, not theorised.** Driving 23 suites one at a time left
`api/sd-data.js` missing `, warn_days: gateWarn` and
`api/_lib/subcontractor-compliance.js` in a state that FAILS `node --check`
(`SyntaxError: Identifier 'today' has already been declared`), with the
sentinel absent. Both were restored from HEAD and both now pass
`node --check`. `core.bare` was `true` and was set back to `false`.

**AND THE HYPOTHESIS THAT LOOKED BEST WAS REFUTED.** Removing
`, warn_days: gateWarn` from `api/sd-data.js` exactly as
`run_delegation_probe.py:241` removes it, then driving
`phi_cache_scoped_to_user.js`, gives **72 passed / 0 failed** -- the file was
restored byte-identical afterwards and re-run. So that plant is NOT what
turns phi_cache red, the particular mutator is **NOT ESTABLISHED**, and it is
not named. An invented cause ends the investigation.

## 5. Session locks -- both groups, 0 released (brief item 9)

Release required BOTH tests, per the brief: the holder pid verified DEAD *and*
the lock ATTRIBUTABLE. **0 of 14 met both, so 0 were released.**

| lock | holder pid | pid state | attributable? | verdict |
|---|---|---|---|---|
| `cc.lock` | 53560 | LIVE | yes -- filename is a session name | LEAVE (live) |
| `cody.lock` | 2204 | LIVE | yes | LEAVE (live) |
| `fourth.lock` | 61696 | LIVE | yes -- this session | LEAVE (live) |
| `hank.lock` | 48956 | LIVE | yes | LEAVE (live) |
| `hover.lock` | 30428 | LIVE | yes | LEAVE (live) |
| `hover2.lock` | 83452 | LIVE | yes | LEAVE (live) |
| `b12wt2.lock` | 78192 | DEAD | NO | LEAVE |
| `repo.lock` | 39448 | DEAD | NO | LEAVE |
| `tree.lock` | 82012 | DEAD | NO | LEAVE |
| `wt-tools.lock` | 73300 | DEAD | NO | LEAVE |
| `sairn_idem_o66nnvth.lock` | 58388 | DEAD | NO | LEAVE |
| `sairn_idem_q5p4bqkx.lock` | 58388 | DEAD | NO | LEAVE |
| `sairn_idem_rhbjx2yx.lock` | 61668 | DEAD | NO | LEAVE |
| `sairn_idem_uw3ebld2.lock` | 82012 | DEAD | NO | LEAVE |

**Each dead pid was put to `Get-Process` ONE AT A TIME**: 78192, 39448, 58388,
61668, 82012, 73300 all DEAD. Attribution failed for all eight because the
`task` field is `""` in 14 of 14 locks and the status registry's pid->session
map holds none of those pids -- it currently reads cc 26312, cody 2204,
fourth 61696, hank 48956, hover 30428, hover2 71364.

**THIS CORRECTS batch b4's OWN CLAIM.** b4 reported that two of the eight
(`tree`, `sairn_idem_uw3ebld2`) were *"hank's by his old claude_pid 82012"*.
No current record ties 82012 to hank -- hank is 48956 now -- so that
attribution was an inference carried from a previous session's memory, not a
record, and under the brief's AND condition it does not qualify. The honest
count is **0 attributable, not 2**.

The standing fix is unchanged and still routed: `tools/session_lock_check.py`
`:128` `lock_path()` forms the only lock FILENAME and nothing in it carries a
session name; `:349` `lock_payload()` is the only WRITE site; `:357`
`'task': task` is the field that is empty in 14 of 14.

## 6. The worktree (brief item 8) -- removed, and why that discarded nothing

| worktree | head | reachable from origin/main | dirt | action |
|---|---|---|---|---|
| `cc-review-0a_4251m` | `f65e734d` | **YES** | 2,373 paths, **all of them `D` (staged deletions)**, 0 stashes, 0 added, 0 modified | **unlocked and removed** |
| `defreg-probe-59076` | `fdce1b4b` | **NO** | 1 path | **LEFT, hash reported** |
| `gate12-19124-5` | `549a372a` | **NO** | clean | **LEFT, hash reported** |

`cc-review-0a_4251m` met the brief's condition: `git merge-base
--is-ancestor f65e734d origin/main` succeeds, so every commit on it is
reachable. The 2,373 dirty paths were ALL staged deletions of files that
exist at that reachable commit, which is why `--force` was used and why it
discarded nothing recoverable -- there was no added or modified path and no
stash. It had been held 493.6 hours with an AMBIGUOUS claim attribution.

**The other two are NOT mine by intent but ARE mine by provenance**: driving
the 23 candidate suites for item 2 created them minutes earlier. Their heads
are probe commits that are not on `origin/main`, so removing the worktrees
would orphan commits, and the brief's own rule for the unreachable case is to
leave them and report the hashes. Reported: `fdce1b4b`, `549a372a`.


---

# ADDED BY BATCH b6, 2026-10-13 -- fourth

The owner column above was rewritten this batch: every row that said `UNOWNED`
now names a session. **The basis is a DIRECTORY RULE given in the b6 brief, not
a record** -- `api/` to hank, `tests/` to cody, `tools/` to cc, `docs/` to
fourth, plus six named overrides. That is a weaker basis than a file's own
`# OWNER:` line and a stronger one than nothing, and the `owner basis` column
says which it is so the two are never confused. 40 rows rewritten, 0 left
unowned, and the pipe count per row was compared before and after.

## 7. The 14 session locks, with PID and age (b6 item 9)

Release required BOTH tests again -- the holder pid verified DEAD *and* the lock
ATTRIBUTABLE -- and b6 narrows it further: release only what is attributable to
**me**. **0 locks were released.** Age is the lock FILE's mtime, measured now;
the `lock says` column is the raw `claude_start` value the lock carries, which
is a Windows FILETIME tick count and not a date, and is printed as-is rather
than converted, because converting a field whose units are a guess is how a
wrong number gets a date next to it.

| lock | holder pid | pid state | file age (h) | lock says | attributable to | verdict |
|---|---:|---|---:|---|---|---|
| `b12wt2.lock` | 78192 | DEAD | 120.6 | 134357762159212705 | NONE | LEAVE -- dead but UNATTRIBUTABLE |
| `cc.lock` | 53560 | LIVE | 1.6 | 134362418688496853 | cc | LEAVE -- holder is LIVE |
| `cody.lock` | 2204 | LIVE | 1.6 | 134362418402795108 | cody | LEAVE -- holder is LIVE |
| `fourth.lock` | 61696 | LIVE | 1.5 | 134362418976255147 | fourth | LEAVE -- holder is LIVE |
| `hank.lock` | 48956 | LIVE | 1.6 | 134362418846177203 | hank | LEAVE -- holder is LIVE |
| `hover.lock` | 30428 | LIVE | 1.4 | 134362411605322071 | hover | LEAVE -- holder is LIVE |
| `hover2.lock` | 83452 | LIVE | 1.4 | 134362419152238394 | hover2 | LEAVE -- holder is LIVE |
| `repo.lock` | 39448 | DEAD | 147.5 | 134357133510386951 | NONE | LEAVE -- dead but UNATTRIBUTABLE |
| `sairn_idem_o66nnvth.lock` | 58388 | DEAD | 299.0 | 134351763382256557 | NONE | LEAVE -- dead but UNATTRIBUTABLE |
| `sairn_idem_q5p4bqkx.lock` | 58388 | DEAD | 299.2 | 134351763382256557 | NONE | LEAVE -- dead but UNATTRIBUTABLE |
| `sairn_idem_rhbjx2yx.lock` | 61668 | DEAD | 306.9 | 134350675984514778 | NONE | LEAVE -- dead but UNATTRIBUTABLE |
| `sairn_idem_uw3ebld2.lock` | 82012 | DEAD | 114.0 | 134358654468810777 | NONE | LEAVE -- dead but UNATTRIBUTABLE |
| `tree.lock` | 82012 | DEAD | 114.5 | 134358654468810777 | NONE | LEAVE -- dead but UNATTRIBUTABLE |
| `wt-tools.lock` | 73300 | DEAD | 116.4 | 134357847177782898 | NONE | LEAVE -- dead but UNATTRIBUTABLE |

**0 RELEASED, 14 LEFT: 6 holders are LIVE (all six sessions are running) and 8
are DEAD AND UNATTRIBUTABLE.** Not one of the eight is attributable to me, so
not one qualifies under the brief's rule. Every dead pid was put to
`Get-Process` one at a time: 78192, 39448, 58388 (twice), 61668, 82012 (twice),
73300.

**WHY NONE OF THE EIGHT CAN BE ATTRIBUTED, measured rather than asserted.** The
registry's pid->session map holds `{26312: cc, 2204: cody, 61696: fourth,
48956: hank, 30428: hover, 71364: hover2}` -- the six LIVE sessions and nobody
else. A dead pid is by definition absent from it, so the map can never attribute
a dead lock, and the lock files themselves carry no session field. **That is the
structural reason, and it is why this is the third batch reporting 0 releases:
the information needed to release them was never written down at lock time.**
Routed, unchanged, to cc per the b6 directory rule: `tools/session_lock_check.py:128`
`lock_path()` forms the only lock FILENAME and nothing in it carries a session
name; `:349` `lock_payload()` is the only WRITE site; `:357` `'task': task` is
the field that is empty in 14 of 14.

`fourth.lock` is LIVE and is this session's own. It is released at report close.

## 8. Claim visibility -- b5's own sentence is half wrong (b6 item 8)

b5 reported its claim as invisible, quoting the tool: *"committed locally and is
therefore INVISIBLE to every other clone -- treat this as NOT CLAIMED."*
**MEASURED, and it is true of one path and false of the other.**

| path | where it lives | who reads it | needs a push? | carried my unpushed claim? |
|---|---|---|---|---|
| GIT RECORD (authoritative) | `.claude/claims/<session>.json`, TRACKED | every clone, after `git fetch` | **YES** | **NO** |
| STATUS REGISTRY (advisory) | `~/SAIRN-SESSION-LOCKS/status/<session>.json`, OUTSIDE EVERY CLONE | every session ON THIS MACHINE, with no fetch | **no** | **YES -- 1 claim, 11 files** |

`tools/sairn_claim.py` already publishes active claims to the registry
(`publish_claims`, around `:1547`) and already reads other sessions' from it
(`registry_claims`, `:1281`). So an unpushed claim is invisible to a clone on
ANOTHER machine and perfectly visible to the five other sessions on this one.
Verified by calling `sairn_status.read_claims(exclude='cody')` and finding my own
active claim in the result.

**THE DEFECT IS THE MESSAGE, NOT THE MECHANISM, and the message is what a
session acts on.** b5 read it, believed it was unclaimed, and said so in its own
report and handoff. ROUTED TO **cc** (`tools/` by the b6 directory rule), three
exact lines:

| line | what it prints | why it is wrong here |
|---|---|---|
| `tools/sairn_claim.py:1966` | *"therefore INVISIBLE to every other clone -- treat this as NOT CLAIMED."* | the registry row was already written; it is invisible OFF this machine only |
| `tools/sairn_claim.py:1921` | *"--no-push: committed locally only. Other clones cannot see this until you push it."* | same, and `--no-push` is the flag a session uses precisely when it cannot push |
| `tools/sairn_claim.py:2414` | *"--no-push: nothing published. Other clones still cannot see it."* | **"nothing published" is the flatly wrong half** -- `publish_claims` ran |

Suggested wording, so the fix is not left as "be clearer": *"not on
origin/main, so clones on another machine cannot see it; PUBLISHED to the
machine-local registry, so the other sessions here can. Re-check with
`sairn_claim.py list`."*

## 9. The phi_cache mutator -- 8 candidates eliminated one at a time (b6 item 2)

**NOT FOUND, and the hypothesis is now substantially weaker rather than
unproven.** The candidate set was derived, not guessed: 95 suites name one of
phi_cache's seven subjects AND contain a write primitive; of those, 7 put a
write within 3 lines of a subject; 2 of those 7 name a temp or worktree path in
the same window and were descoped BY NAME. The 5 survivors were driven ALONE,
then the 3 descoped-or-adjacent ones were driven too -- 8 in all, one at a time,
each logged as it ran.

| # | candidate | subject moved? | core.bare after | phi_cache after |
|---|---|---|---|---|
| 1 | `tests/run_alf_scope_mutation_probe.py` | none | false | exit 0, 72/0 |
| 2 | `tests/run_cross_tenant_dispatchers_sabotage_probe.py` | none | false | exit 0, 72/0 |
| 3 | `tests/run_role_gate_negative_coverage_probe.py` | none | false | exit 0, 72/0 |
| 4 | `tests/write_readback_shape_probe.py` | none | false | exit 0, 72/0 |
| 5 | `tools/mutation_anchor_check.py` | none | false | exit 0, 72/0 |
| 6 | `tests/seam_check/run_delegation_probe.py` | none | false | exit 0, 72/0 |
| 7 | `tests/seam_check/run_delegation_residue_control.py` | none | false | exit 0, 72/0 |
| 8 | `tests/run_tier_a_review_gate_probe.py` | none | false | exit 0, 72/0 |

The seven subject digests were identical at the start and the end of both
rounds, so no candidate moved one even transiently that the harness missed.

**AND CANDIDATE 6 IS THE INFORMATIVE ONE.** b5 measured
`run_delegation_probe.py` leaving `api/sd-data.js` and
`api/_lib/subcontractor-compliance.js` sabotaged. Driven here with
`core.bare = false` throughout, it restored both perfectly. **That confirms b5's
chain rather than contradicting it**: the restore works when `git` works and
fails silently when `core.bare` is true. It also means the residue it leaves is
the `, warn_days: gateWarn` plant, which b5 ABLATED with no effect on
phi_cache -- so even the one suite that can dirty a subject does not explain the
red.

**WHAT IS LEFT, stated as the open question it is.** hank's `63 passed, 1 failed`
was produced under a tree state that none of the 8 can create. The next
occurrence will IDENTIFY ITSELF: b5's precondition makes phi_cache print
`SKIPPED:` and name the dirty subject instead of failing, so the question is now
self-reporting and does not need another bisect.

## 10. Stripper consolidation -- counts (b6 items 1 and 12)

| | sites | files |
|---|---:|---:|
| found by the b5 whole-tree inventory | 44 | 23 |
| replaced in b5 (`tests/faults/grd_write_faults.js`) | 5 | 1 |
| **replaced in b6** | **10** | **5** |
| remaining, re-counted at this HEAD | **29** | **17** |

The b6 ten are the first ten rows of the table in section 3, taken in order:
`api/_lib/courtlistener-rate-limit.test.js` (2),
`api/_lib/deadline-endpoint-inputs.test.js` (1),
`api/_lib/deadline-jurisdiction-labels.test.js` (1),
`api/_lib/dental-gfe.test.js` (5), `api/_lib/mech-assets.test.js` (1).

**ALL TEN ROUTE THROUGH `stripJs` FROM `tests/lib/strip_comments.js`**, which is
the JS half of the same consolidation `tools/jscomments.py` is the Python half
of. Every subject at these ten sites is a bare `.js` file, which is why it is
`stripJs` and not `stripComments`; using one for the other is the defect that
library's own header records three times.

Each suite was driven before and after. `api/_lib/mech-assets.test.js` went
**62 passed -> 61 passed, 1 FAILED** on the first attempt and the message was
`stripJs is not defined` -- the require had not been added to that one file.
**That is a real result and it is kept here rather than quietly fixed**: the
before/after discipline is what caught it, within one run, and a consolidation
done without it would have left a suite red and a session believing 10 sites
were clean. After the require landed: 62/62, exit 0.

