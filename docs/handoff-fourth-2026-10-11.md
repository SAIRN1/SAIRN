# HANDOFF -- fourth / ted, batch b4 (18) RESUME, 2026-10-11

**Written BEFORE the report and the digest, on purpose.** A handoff written after
the report is a summary of a summary; this one is written while the work is still
in front of me, and the report is derived from it rather than the other way
round.

---

## 0. STATE AT PICKUP, reported before anything was touched

| | |
|---|---|
| HEAD at pickup | `03bad219` *chore(claims): fourth releases fourth* |
| working tree | **clean except ONE untracked path** -- `sql/restore_demo_pins_2026-09-29.sql`, 10,307 bytes, dated 2026-10-05 |
| relative to remote | **behind 45** |
| batch-18 handoff | **EXISTS** -- `f25e2f82`, plus the report and digest at `b35ce277` and the correction at `09eabbec`. **Batch 18 was CLOSED, not interrupted.** |

**The untracked file was NOT discarded and NOT committed.** It is not mine, it
has sat in this clone for **eight batches now** (seven at b4 close), nothing
tracked references it, and the resume brief said *if dirty, commit or stash --
don't discard*. Committing somebody else's unreviewed SQL that writes credential
rows would pull it under the push gate's recoverability guard (PR §3.4) without
anybody having read it for that; stashing it hides it from the next session's
`git status`, which is the only thing that has surfaced it at all. **So it is
carried, visibly, for the eighth time, and it is question 1 below.**

**The resume premise was checked rather than assumed.** The brief listed five
batch-18 items under *"if unfinished."* Batch 18's committed digest says all five
are DONE. **Neither statement was taken as evidence** -- each was re-derived from
the repo, and two of the five moved. See §2.

---

## 1. WHAT LANDED, three commits, each pushed and each verified against the ref

| commit | what |
|---|---|
| `71fdeb34` | **items 2 and 3** -- convention **33** assigned and promoted; the two "unlocatable" queue16 conventions recounted; promotion rows **31**, **32**, **33** |
| `f2082d03` | **items 4 and 5** -- every carryover re-derived, `tools/jscomments.py` ownership taken, `SEQ b4-E` written |
| *(this handoff)* | **item 7** |

**Every push was verified with `git ls-remote origin refs/heads/main` compared to
`git rev-parse HEAD`, not with the push message.** That matters this run: **two
pushes were refused before they landed** and neither refusal was a gate finding.
The first printed *"the outgoing range `aefaffdd..61b55a41` could not be read"*
-- the remote had moved and the range named a commit this clone had not fetched.
The second was a hard ref race: *"cannot lock ref: is at `9d671d94` but expected
`f52256c3`"*, another session pushing between my fetch and my push. **Both were
fixed by fetch + rebase + retry and neither was overridden.** `SAIRN_SEED_GATE`
was **not** used at any point.

---

## 2. THE FIVE CARRYOVERS, AND THE TWO THAT MOVED

Full detail in `docs/2026-10-07-fourth-routed.md` **`SEQ b4-E`** (line 2177).

| carryover | verdict | moved? |
|---|---|---|
| the remaining 43 SEQ 17-A findings | **CLOSED as a re-check** -- arithmetic re-derived from the rows (36+7=43, 17+6=23) and **3 of 23 sites read out of source**, all three agreeing | no |
| `tools/jscomments.py` `strip_js` | **CODE was closed; OWNERSHIP WAS NOT** | **YES -- half the item was genuinely open** |
| the external-claims release statement | **CLOSED and re-measured live** -- 24 worktrees are now **2** | no, the release held |
| skill-path scoping | **CLOSED, nothing disabled** | **YES -- two figures drifted +6 each** |
| the external-files inventory | **OUT OF SCOPE** | **hover2 holds it. FLAGGED BACK, NOT DONE** |

**The one that was half-open.** `jscomments.py` had `strip_js`, `strip_auto`,
`WrongLanguage` and `_refuse_python`, and its probe exits **0** with arms L1-L15
green -- but the item also said *take ownership* and there was no `# OWNER:`
line. `tool_owner_header_check.py` went **exit 1 "NO OWNER: 1" -> exit 0 "OWNER:
fourth"**, grandfathered backlog 265 -> 264. Ownership was **derived** from
`SAIRN-OPEN-WORK-INDEX.md:818`, `git log --follow` (three commits) and the live
claim record, and the derivation is written into the file header so the next
reader can re-check it instead of taking it.

**The one that drifted.** `git ls-files .claude/skills` is **198**, not the 192
`SEQ b4-B` recorded three days ago, and the hover-auditor subtree is **165**, not
159. Same six files, and they are the auditor's. The conclusion is **stronger**:
**165 of 198 tracked files -- 83% --** are the subtree a build agent must not
touch.

---

## 3. WHAT IS ROUTED TO WHOM, with the exact lines

**`tools/session_lock_check.py` -> ITS OWNER. Unchanged from b4 and still open.**

```
tools/session_lock_check.py:128   lock_path()    -- the only place a lock FILENAME is
                                                    formed; no session name in it
tools/session_lock_check.py:349   lock_payload() -- the only lock WRITE site
tools/session_lock_check.py:357   'task': task   -- "" in 14 of 14 live lock files
```

**Eight orphan locks, every holder DEAD, ZERO released.** `b12wt2`, `repo`,
`tree`, `wt-tools` and four `sairn_idem_*`. Holder `claude_pid`s put to
`Get-Process` one at a time: **78192, 39448, 58388, 61668, 82012, 73300 all
DEAD**; **64304 (this session) the only live one.** Two carry hank's old 82012
(`tree`, `sairn_idem_uw3ebld2`); **six are unattributable because the format has
no holder field.** **Any `--prune-dead` must REFUSE on an unattributable record,
not clear it** -- clearing it is PR §1.11 wearing a cleanup.

**`tools/sairn_claim.py` -> ITS OWNER. Two items, both cheap, and the tool's own
output proves the first fix already exists.**

1. **The matcher has no sense of negation.** Attempt 2 of my claim said *"the
   external-files item is REMOVED from scope; hover2 holds it"* and was **BLOCKED
   on `external-files`** -- the honest disclosure is punished and the silent
   omission is rewarded. **The fix is already half-built:** attempt 4 printed
   *"LEXICAL ONLY -- shared phrase: `digest sairn`; the declared file sets are
   DISJOINT"* and did **not** block. That `FILES` layer works; attempts 2 and 3
   were decided before it ran. This is cc's open item 8.
2. **`COMMON_PHRASE_SESSIONS = 3` is derived from the LIVE claim corpus**
   (`common_phrases()` / `_all_claim_tasks()`), so with one active claim per
   session, ordinary process vocabulary can block two careful sessions before
   three of them ever carry it. Attempt 3 was **BLOCKED on `"digest handoff"`** --
   two words every batch on this platform contains.

**Nothing was overridden.** There is no `--force` on `sairn_claim.py claim`
(`--help` shows only `--no-push` and `--no-fetch`), and that is the correct
design. The finding is that the block fired on the wrong evidence.

**`SAIRN-ACTIVE-WORK-fourth.md` -> ME, inbound from cc's batch W item 13.** Over
the 400,000-byte ceiling and still over it. `tooling_inventory.py
--standing-doc-sizes` **exits 1** with **7** documents over -- pre-existing,
unchanged by this batch, and one of the seven is mine.

**The external-files inventory -> THE COORDINATING SESSION.** `hover2`'s live
batch Z declares it. I removed the work rather than rewording the claim (PR
§4.3), so **nothing of mine touched it this run.** Note from b4 that still
stands: there are **two** efforts at that gate -- cc's
`tools/external_file_index_check.py` and the hover-side check landed as
`ab1b3cc2`. Which is canonical is still unanswered.

---

## 4. CONVENTION 33 -- WHAT WAS ADDED AND WHAT WAS NOT

**It is cody's convention. The number is the only thing I added**, which is what
its own status line asked for: *"ROUTED to fourth for a number, NOT
self-promoted."*

**Counted before assigning, and the method matters because two elevenths landed
within an hour on 2026-09-25:** **32** `## <n>.` headings at `263f736f`, numbers
1-32, **no gap and no duplicate**, by `re.match(r'^## (\d+)\.')` plus a
`Counter` and a gap scan -- not by eye and not by `grep -c`. `grep -rn` over
`docs/ tools/ tests/` found no existing convention 33. It now sits at
`docs/2026-09-13-cross-domain-disciplines.md:1851` and the file re-counts
**1-33 clean**.

**THE TEXT WAS MOVED, NOT COPIED, and that will look like a deletion in the
diff.** `METHODOLOGY.md`'s own third paragraph says a second home for a
convention is a second thing to drift and that the text belongs in the
disciplines file **and nowhere else**. Leaving cody's ~90 lines in both files
after promoting them builds exactly the second home that rule exists to prevent.
**cody's original stands unaltered in `7ae272cc` and `ffe43d70`**, and
`METHODOLOGY.md` now says so and says where to take a byte-exact comparison
from.

**ONE thing was added at promotion and it is marked as mine inside the section,
not cody's:** 33 is **convention 29's mirror** -- 29 distrusts a blanket PASS,
33 distrusts a blanket DOUBT, and neither mechanism can distinguish its cases.

**The membership question was asked rather than assumed**, as every prior
addition did. **33 is NOT a member of the cannot-fire group:** its warning
*fired*, correctly and loudly, and the suite's statement about its own dirtied
tree was true. The group stays at **TEN**; the heading's denominator moved from
*thirty-two* to *thirty-three* **with the old wording carried inside the note**.

---

## 5. THE QUEUE16 RECOUNT -- THEY WERE NEVER MISSING, and a SECOND defect came out of the recount

**Re-derived from the source document, not restated from my own b3 write-up.**
`docs/2026-10-06-cody-queue16-inventory.md` has **one** `## METHODOLOGY (ITEM 8)`
heading at **:198** and **two `###` children** under it, at **:243** and **:251**.
My b3 search keyed on the `##` unit, found one, and counted one convention.

```
:243  ### The third state is the hard part, one level down   -> convention 31, landed :1751
:251  ### And the corollary this batch paid for twice        -> convention 32, landed :1806
```

So cody's *"three conventions + three more"* resolves as **3 new + 3 from queue
16, one of which was already convention 15, leaving exactly the two owed** -- and
both landed on 2026-10-08, credited to cody.

**THE RECOUNT FOUND SOMETHING THE FIRST PASS DID NOT.** Both **promotion ROWS
were absent** from `METHODOLOGY.md`'s table. The conventions landed on 2026-10-08
and the rows never followed, because `METHODOLOGY.md` was in cody's live
batch-26 `FILES` that hour and the rows were **routed to him instead of
written**. The file is free now, so they are backfilled -- **and the absence is
recorded as the finding it is**: a promotion recorded in only one of the two
files is this file's own drift problem committed by its own bookkeeping.

---

## 6. CLAIMS, LOCKS AND HOLDS AT THIS MOMENT

| | |
|---|---|
| repo claim | `.claude/claims/fourth.json` **ACTIVE**, taken this run on the **4th attempt**, committed and verified on `origin/main`. **To be released at batch close.** |
| session lock | `~/SAIRN-SESSION-LOCKS/fourth.lock` **HELD**. `session_lock_check.py status` -> **exit 0**, `state : SELF`, `CLAUDE_PID 64304`. Mine, live, deliberately kept. |
| status row | **RESTATED at pickup.** It said `fourth idle DEAD batch b4 (18) CLOSED`; set to `working` with this run's real HEAD. |
| worktrees | **2 registrations.** This clone, and `cc-review-0a_4251m` -- **git-LOCKED, detached at `f65e734d`, NOT MINE, NOT REMOVED.** |
| stash | **none.** |
| orphan locks | **8, all holders dead, ZERO released.** See §3. |
| untracked | `sql/restore_demo_pins_2026-09-29.sql` -- **carried, not adopted, eighth batch.** |

**THE STATUS REGISTRY WAS WRONG IN A NEW DIRECTION and the next session should
not trust it either way.** At pickup it reported **all six sessions `idle
DEAD`**. All six session locks are **live** and were started within four minutes
of each other on 2026-10-11 -- `hover 19:35:16`, `cody 19:35:47`, `cc 19:36:20`,
`hank 19:37:47`, `fourth 19:38:30`, `hover2 19:39:23`. `CLAUDE.md` warns that an
**empty** registry is not evidence nobody is working. **The measured failure here
is the mirror: a POPULATED one is not evidence they are dead.** I wrote my own
row and none of the other five.

---

## 7. WHAT IS NOT DONE, stated plainly

- **The external-files inventory.** `hover2` holds it; removed from scope and
  flagged back. **Not attempted.**
- **The 36 REAL SEQ 17-A findings** across 17 sites. **Open by design** -- the
  b4 pass recorded their real subjects so nobody re-measures against the wrong
  file; nothing was fixed and this run fixed nothing either.
- **The eighth private comment-stripper**, `tests/faults/grd_write_faults.js:385`
  -- its own `/\/\/[^\n]*/g` eats the rest of any line containing `//` inside a
  URL. Routed to the `jscomments.py` consolidation, which I now own. **Open.**
- **`SAIRN-ACTIVE-WORK-fourth.md` over the ceiling.** Inbound to me, untouched.
- **7 standing documents over 400,000 bytes.** `tooling_inventory.py
  --standing-doc-sizes` **exits 1**. Pre-existing and unchanged by this batch.
- **283-ish `tools/*.py` with no `# OWNER:` line.** 264 grandfathered after this
  run's one. Not a gate; a backlog.

---

## 8. QUESTIONS ONLY MICHAEL CAN ANSWER

Three of these are carried from b4 unanswered, and they are repeated rather than
dropped because an unanswered question that stops being asked becomes a decision
nobody made.

1. **`sql/restore_demo_pins_2026-09-29.sql`** has sat untracked in this clone for
   **eight batches** and is not mine. It writes credential rows, so committing it
   pulls it under the push gate's recoverability guard without anybody having
   reviewed it for that. **Commit it, delete it, or keep carrying it?**
2. **`cc-review-0a_4251m`** is a git-LOCKED worktree in this clone with a dead
   holder, left by a `/code-review` run. **I will not remove another agent's
   locked tree. Do you want it cleared?**
3. **Two efforts at the unindexed-external-file gate** -- cc's
   `tools/external_file_index_check.py` and the hover-side check in `ab1b3cc2`.
   **Which is canonical?**
4. **Convention 33's text was MOVED out of `METHODOLOGY.md`, not copied.** That
   is the file's own rule and it is the right call, but it deletes ~90 lines of
   cody's prose from a file he wrote them into on purpose after complaining that
   earlier routings were NOT RECEIVED. **If you would rather the text stay in
   both places, say so and I will restore it** -- with the caveat that the file
   then holds the second home its own third paragraph warns about.
5. **The claim matcher blocked me twice on evidence that was wrong** -- once on a
   resource I was explicitly declining, once on the words `digest handoff`. I
   worked around it by writing a claim about the work rather than the paperwork.
   **Is that the behaviour you want, or should a session in that position stop
   and wait for you instead?** I would rather be told than keep choosing.
6. **~350 files still sit in `C:\Users\marsh\`** that b4 classified as throwaway
   -- ~20MB, none referenced by any tracked file. **Nothing was deleted and
   nothing will be without your word.** Still question 1 of b4.
