# HANDOFF — fourth / ted, batch b20, 2026-10-14

**Written BEFORE the report**, at a point where nothing is half-finished: items
1–6 are committed and pushed, `HEAD == origin/main`, the working tree carries
only the b20 manifest's own final `--set 6` edit, no rebase or stash is in
progress, and the b20 claim is still held on purpose.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote** — including out of this file.

**THREE THINGS WORTH READING FIRST:**

1. **Both of my Tier A obligations were discharged INSIDE the 24h deadline** —
   at 7h and 3h. The four before them were 418h, 397h, 339h and 339h. **This is
   the first batch where this role met the clock instead of draining a
   backlog.**
2. **cc's own change silently turned a probe RED** —
   `tests/run_drive_upload_verify_probe.py` is 34/35, exit 1, at HEAD, because
   an arm greps a sentence fragment the reworded message no longer contains.
   **Measured twice, once by me directly.** Every claim cc made is *true*; the
   findings are all in what was not claimed.
3. **All SEVEN line citations in the `sf_events` register row were wrong**, and
   they are now quoted-text anchors, each verified to resolve **exactly once**.
   **The eighth cross-domain convention has now surfaced live in four
   consecutive documents**, twice in ones I wrote.

**AND THE EIGHT-BATCH-OLD STALE LOCK IS REAPED.** `fourth.lock` had carried a
dead `CLAUDE_PID 53204` since `2026-10-13T05:36:03`; it now belongs to this
session.

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\b0f8683c-3365-4d5b-82ea-094a13bdff7e\scratchpad\`
New this batch: `tier_a_list_b20.log`, `lock_status_before_b20.log`,
`lock_guard_b20.log`, `verdict_b20_leg.txt`, `discharge_leg_b20.log`,
`verdict_b20_cc.txt`, `discharge_cc_b20.log`, `dupv_probe_b20.log`,
`pull_b20.log`, `pull_loop_b20.log`, `push_loop_b20.log`.
*(Same session as b18 and b19, so their logs are in the same directory.)*

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `924085fb` | `git rev-parse --short HEAD` |
| `origin/main` | `924085fb` | `git rev-parse --short origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| **chain tip (full)** | `924085fb54e57c38b590e960f31eb8cc9aa3e1bf` | `git rev-parse HEAD` |
| working tree | **one modified file**: `docs/batch-manifest-fourth-b20.json`, carrying item 6's own evidence. Committed with this handoff | `git status --porcelain` |
| the b20 work commit | `093d091e`, rebased to land inside `1b2e346a..924085fb` | `git log origin/main --oneline -3` |
| push forced? | **NO** | `1b2e346a..924085fb`, **first attempt, no rejection**; `grep -ci force` over the push log → **0** |
| `SAIRN_SEED_GATE=off` | **not used, any form** | — |
| `SAIRN_GATE_EXEMPT=seed` | **not used either** | — |
| `.claude/settings.json` | **not edited, not committed** | not in the commit's file list |
| hooks | **untouched** — not added, not removed, not restored | by instruction |
| files written outside `docs/` | **0** (plus my root deliverables) | by instruction |
| files written under `.claude/skills/sairn-hover-auditor/` | **0 — and neither auditor clone was entered** | §3.4 |
| all six b20 `docs/` paths on `origin/main` | **6 of 6** | `git cat-file -e origin/main:<path>` per file |
| b20 manifest | **6 of 6 `done`**, close pending the three uploads | `batch_manifest.py --check --agent fourth --batch b20` |
| **context at this handoff** | **58% of 1000k** | `tools/sairn_status_line.py` fed this session's transcript |

**`924085fb` IS THE STATE AT FINALISATION OF THIS HANDOFF** — this file, the
report, the digest, `SAIRN-latest-fourth.md`, the b20 close and the claim
release all land after it.

---

## 1. ITEM BY ITEM

| # | item | state | exact next step |
|---|---|---|---|
| 1 | close b19; Drive-API-read both files; reap the stale lock | **DONE — nothing was missing, so nothing was rewritten. Lock reaped** | nothing (§2 records the new lock owner) |
| 2 | discharge hank's `2026-10-14T13:50:42Z` (21 `leg_*` + `rf_settings`) | **DONE — exit 0, at 7h, INSIDE the deadline. All four attack points survive; 5 findings** | **hank: F1–F5, F4 first. cody: 2 arms. Michael: run-order blocks 5 and 6** (§3.1) |
| 3 | discharge cc's `2026-10-14T17:20:09Z` (`quotes`, `sd_comms`) | **DONE — exit 0, at 3h. A real diff review; 6 findings** | **cc: F3 FIRST — a red arm in the suite** (§3.2) |
| 4 | name the owner of each of the five siblings and route each | **DONE — all five are hover2's, derived from provenance** | **hover2: four `# OWNER:` lines, then decide per file** (§3.4) |
| 5 | re-anchor the six rotted `sf_events` anchors; spec the rot check | **DONE — it was SEVEN, not six. 7 anchors, 7 unique, 0 line citations** | **cc: build the check; A2/A4/A10 are the load-bearing arms** (§3.5) |
| 6 | push without force, confirm landed | **DONE — `1b2e346a..924085fb`, 0/0, first attempt** | nothing |
| — | this handoff, before the report | **DONE** | — |

---

## 2. CLAIMS, LOCKS AND HOLDS

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b20, published on `origin/main`; **release last**, after all four uploads | `sairn_claim.py list` |
| **Tier A obligations assigned to me** | **2** | see below — **one is overdue by OBLIGATION age and fresh by ASSIGNMENT age, and the distinction matters** | `--list` |
| obligations discharged this batch | **2** | both as the **assigned owner**, neither by `--takeover`. Register went 19 → 17 open | `--list` before/after |
| **session lock** | **1, and it is MINE and LIVE now** | was `CLAUDE_PID 53204`, `started 2026-10-13T05:36:03`, state **`DEAD`**, held eight batches. **`session_lock_check.py guard` → exit 0**, now `CLAUDE_PID 3444`, `started 2026-10-14T16:46:22`, state **`SELF`** | `python tools/session_lock_check.py status` |
| locks removed by me | **0** | **the reap was a reclaim, not an `rm`** — `guard` is the tool's own designed verb for a lock whose owner process is gone, and I did not route around the `rm` deny | `lock_guard_b20.log` |
| `git stash` | **0** | | `git stash list` |
| worktrees besides main | **4** | **none mine** — other sessions' temp gate trees | `git worktree list` |
| status registry row | `working` | set at batch start; `idle` at release | `sairn_status.py set` |

### The two obligations that are mine, and why the second number differs

| | obligation | age | **assignment** age | why it matters |
|---|---|---:|---:|---|
| **b21 item 1** | `hank` **`2026-10-13T09:03:35Z`**, 11 resources, **one file: `SAIRN-addendum-hank-b5.txt`** | **39h — OVERDUE on the 24h clock** | **2h** — `owner_assigned_at 2026-10-14T17:58:19Z` | **It was reassigned to me mid-batch**, off a previous owner. **The 24h deadline runs on the obligation; the 48h takeover window runs on the assignment.** So it is overdue and *not* takeover-eligible, and nobody else can lift it from me yet |
| **b21 item 2** | `hank` **`2026-10-14T17:56:56Z`**, **33 resources**, 5 files incl. `api/_lib/sv-roles.js` and `api/sd-data.js` | **6h** | 6h | hank b11: **three Tier A surfaces, each needing a different thing reviewed hardest** — the first is `alf_family_contacts` losing its inherited read roles for a named, time-limited, audited grant |

**ITEM 1 IS THE SMALLER JOB AND THE OLDER CLOCK: it is DOCUMENT ONLY — no code
in the push.** Its own text says so: the gate flagged it because
`SAIRN-addendum-hank-b5.txt` **mentions** `bld_draws`, `sf_events` and
`sf_products` in prose, *"recorded rather than argued away"*. **Do it first
anyway** — it is overdue, and a prose-only obligation is an hour's review, not
a day's.

**AND ITS SHA IS THE ONE STRONG-BASIS RE-SEAT MY b19 CENSUS FOUND:**
`f0e81b92459c -> 8a572a6ead25` **[EXACT FILE SET]**. **Re-seating it is now
MY call rather than a stranger's, because I own the record** — and it is still
cc's tool. **Decide it deliberately; do not let it ride along.**

---

## 3. WHAT IS OPEN, AND WHY

### 3.1 hank — the leg role matrix survives, and five findings sit beside it

`docs/2026-10-14-fourth-b20-leg-role-matrix-discharge.md`. **A STATE review:
`0442c8e0c95d` dangles and no candidate was offered.**

**ALL FOUR ATTACK POINTS SURVIVE, and the measurement is the part that counts:**

```
spec parsed from my b15 document   36 resources  {REGULATED 9, MONEY 15, OPERATIONS 12}
code loaded by require()           36 resources, same three counts
set difference, both directions    SPEC-ONLY: none   CODE-ONLY: none
bands                              36 compared, 0 mismatches
per-role cells (8 x 36)            288 checked, 0 grant diffs
```

**THE DISCLOSURE THAT BOUNDS IT, AND IT IS AT THE TOP OF THE VERDICT RATHER
THAN IN A CAVEAT: the spec hank was transcribing is MINE.** I can establish the
transcription is faithful; **I cannot be the independent reviewer of whether the
spec puts the right resource in the right band.** That half is routed to counsel
(C1, C2) and a funeral director (F1–F5) and **five of those eight are still
unanswered.**

**A METHODOLOGY WARNING WORTH MORE THAN THE RESULT:** the first parse pass
reported **two false mismatches on two money resources** because the spec reader
ran one line past the OPERATIONS list. **An unbounded parse produces exactly the
finding a careless reviewer would have filed.** When a measurement produces a
finding, measure the measurement first.

**THE FIVE FINDINGS, F4 FIRST:**

* **F4 — the `leg_aftercare` key is DELIMITER-AMBIGUOUS.** `checkin_type` is
  normalised; `case_id` gets a `trim()` only; and `-` is **both the joiner and
  the normaliser's output**. So `('CS-7','1 Week')` and `('CS-7-1','Week')` both
  derive `AC-CS-7-1-WEEK`, and the upsert's `merge-duplicates` **silently
  overwrites a different case's check-in and returns 200.** **Not reachable
  through the shipped UI** (fixed three-type plan, three-segment generated ids)
  — **reachable by any licence-key holder posting directly**, and by any future
  free-text type, **which is precisely the assumption the code's own comment
  rests on.** **And no arm covers it: the colliding pair would PASS the
  cross-check, because both copies agree on the wrong answer.**
* **F5 — the canonicalisation leaves a local duplicate on the device it was
  built to protect.** The transport discards the rewritten id and marks the
  **client's** id as synced, so the un-upgraded device keeps the random id, the
  next hydrate fails to match, and **one check-in becomes two local rows** —
  the duplicate-grief symptom the fix exists to prevent. **One line in the
  caller.**
* **F2 — the 15 money panels fail soft into local-only for a `staff` login.**
  No hard lockout; writes commit locally *before* the server is asked, with no
  rollback, and a 403 is indistinguishable from "sync unavailable". The toast
  is correct. **COULD NOT TELL whether a `staff` employee's role can be edited
  in place** — if not, the only route off `staff` is delete-and-recreate.
* **F3 — three stale citations for one anchor, one stamped "RE-DERIVED".** The
  clergy literal is at `sairnlegacy.html:4841`, cited as 4839 (twice, one with
  the freshness stamp) and 4820. **This is §3.5's subject arriving in hank's
  file.**
* **F1 — a no-op `{ livery: NO }` override** on `leg_deathrecords` that
  advertises an exception the band already enforces.

**AND THE THING THAT OUTRANKS ALL FIVE, which is Michael's and not hank's:**
the run-order file says in its own words that *"SAIRNlegacy's five new task
roles are rejected… nobody can be given a role other than
owner/director/staff"* and that blocks 1, 3, 5 and 6 are *"the thing currently
FAILING rather than a preparation for something later."* **So the 36-resource
matrix this review verified as faithful is TODAY a gate nobody can populate,
and the only role anybody can hold is the deprecated one** — the exact opposite
of the deprecation's intent. **EXACT NEXT STEP: ask Michael whether blocks 5 and
6 have been run. Nothing in the repo records a run; that is UNVERIFIED and needs
a human, not a file.**

### 3.2 cc — every claim true, and the change broke its own control

`docs/2026-10-14-fourth-b20-cc-quotes-comms-discharge.md`. **A REAL DIFF
REVIEW — `3b1dc5fe3174` RESOLVES.**

**F3 IS THE FINDING AND IT IS cc's FIRST JOB:**

```
CMD python tests/run_drive_upload_verify_probe.py          ->  EXIT 1
      FAIL WRONG-AGENT: ... wanted (1, True)  got (1, False)
      drive_upload_verify probe: 34/35 arm(s) pass
CMD git show --stat --oneline d1308719   ->  1 file changed, 38 insertions(+), 2 deletions(-)
CMD git log --oneline -1 -- tests/run_drive_upload_verify_probe.py
      9603441d  (the tool's CREATION commit -- untouched by d1308719)
```

The arm asserts the substring `does not name cc`; the reworded message says
*"WRONG AGENT -- the first line names cody, not cc."* **`tools/run_all_tests.py`
walks `tests/` recursively, so this is a red arm in the discoverable suite.**
**The commit's own subject is "the dangerous case was buried" — it unburied the
case in the message and buried a failing control in the suite.**

**EXACT NEXT STEP, cc: re-run the probe and point the arm at the stable TOKEN
`WRONG AGENT` rather than a sentence fragment**, so the next rewording does not
break it. **A message a test greps is an interface.**

**The other five, in order of value:** **F5** — `shared_diff`'s discriminator
is **one prefix on one directory**, so the false-finding class it was built to
kill is still live in `push-retries/`, `gate-skips/`, `gate-exemptions/` and
`batch-cleanup/` (**measured: `push-retries/` holds per-agent files from several
sessions minutes apart today**), and the external probe **never redirects
`SAIRN_LOCKS_DIR`, so the control watches the real registry**. **F6** — the
subject's **own** status row is unconditionally dropped, and it is named after
its writer exactly like the lock file the tool exists for. **F2** — "36/36
fixtures intact" is true **because no fixture was added**; delete the new branch
and 36/36 still passes. **F4** — the agent roster is hardcoded and
cross-checked only against a second hardcoded table, so an **unrostered**
author's genuine mis-file now gets the reassuring "convention gap" label.
**F1** — "separately" is true of the label and not of the presentation: both
classes land in one list in alphabetical order, and the audit's summary sentence
is now literally wrong for the files it counts.

**Also named, not traced:** the probe printed `COULD NOT RUN: the criteria lock
failed.` **before** the FAIL. **A criteria-lock failure and a red arm are
different states and should not share a run.**

### 3.3 Michael — one decision, and it is not a new one

**Nothing new is asked of Michael this batch.** Option B (management-only)
**stands until a practitioner answers H8**, per the standing decision, and
Michael was **not** asked.

**What is waiting:** whether **run-order blocks 5 and 6 have been run** (§3.1) —
which is a question about work already routed, not a new decision. **And H8
itself**, which remains with a home-care practitioner.

### 3.4 hover2 — four `# OWNER:` lines, and a naming collision to settle

`docs/2026-10-14-fourth-b20-c78b545b-sibling-routing.md`. **This closes the
bound my own b19 verdict placed on itself** — it said five siblings were
unreviewed and only named them collectively.

**ALL FIVE ARE hover2's, derived from evidence:** no `.py` file carries an
`# OWNER:` line, and **every commit under `tools-hover2/` is scoped
`hover2`/`hover2-tools` while every commit under `tools/` is scoped `hover`.**

**THE TRAP, and it is why the method is stated:** all four basenames exist in
**both** auditor trees and the copies are **not mirrors** —
`hover_cold_scan_pool.py` is **1738 lines in H1's tree against 716 in H2's**.
**Routing by basename would have sent work to the wrong owner.** *(Compared
after `tr -d '\r'`.)*

**A CORRECTION TO MY OWN b19 WORDING:** the commit touched **six paths — five
`.py` and one `.jsonl`** — so the five siblings are **four tools and one data
file**, and *"synced six tools"* was wrong in the same way a check count that
includes a skip is wrong.

**And the data file is the interesting one:** `c78b545b` added
`hover_self_health_fires.jsonl` to `tools-hover2/`; **it is not tracked at HEAD
and it is gitignored by a `.gitignore` inside that very directory.** **Same
shape as b19's `sd_photos` finding — something the system believes it is backing
up that the storage layer quietly refuses.** **UNVERIFIED: the mechanism.**
`git log --all` on that path returns nothing, so **I will not narrate a deletion
no commit records** — the four facts are measured, the story joining them is
not.

**EXACT NEXT STEPS, hover2:** add `# OWNER: hover2` to the four `.py` files
(**four lines, and the routing question stops needing a document**); decide per
file whether it needs its own obligation, **starting with
`hover_cold_scan_pool.py`** — biggest delta, and the name collision makes it the
one most likely to be read in the wrong tree; declare whether the self-health
log is meant to be in the platform backup; **and jointly with hover, say which
tree is canonical for the four shared basenames.** Until that is settled, any
future routing by basename is a coin flip.

### 3.5 cc — the anchor rot check, and the measurement that justifies it

`docs/2026-10-14-fourth-b20-anchor-rot-check-spec.md`.

**IT WAS SEVEN, NOT SIX.** Every one of the `sf_events` row's citations was
wrong:

```
CMD for n in 4910 3268 4957 4999 5023 4378 4364; do sed -n ${n}p sairnfreedom.html; done
  4910  sfRenderAll();                      <- cell says eventRefusals()
  3268  (blank line)                        <- cell says sfSessionRefusals()
  4957  post's second computer would be...  <- cell says sfScheduleEvent()
  4999  if (!sfAiNoticeVersion) return;     <- cell says the session delete
  5023  var input=$('bf-photo');            <- cell says the Sessions panel
  4378  Recorded 2026-09-26. NOTHING IS...  <- cell says the alcohol table tag
  4364  var reasons=[];                     <- cell says the combined list
```

**7 of 7. Every function the cell names is real and does what the cell says —
only the numbers moved.**

**WHAT WAS DONE, and it is `docs/` only:** the cell now carries **quoted-text
anchors and no line numbers at all**, and states the convention to its own
future readers. **Verified: 7 anchors, all resolving EXACTLY ONCE in
`sairnfreedom.html`, 0 four-digit citations left, and the row's pipe count 7
before and after every edit** — rebuilt by unique-substring replacement, **never
by splitting on `|`** (PR §2.1). **Re-verified after the rebase.**

**EXACTLY ONCE, not at least once:** a non-unique anchor is a citation that will
rot silently later. **That is the stronger guard and it is the one
`sabotage_control_check.py` had to be corrected to recognise.**

**AND A HUMAN RE-DERIVATION IS NOT THE ANSWER — THIS BATCH IS THE PROOF.**
§3.1's F3 found a citation stamped **"RE-DERIVED 2026-10-14"** that is wrong
anyway. **A freshness stamp is what a reader checks instead of checking, so a
wrong stamp is worse than none.**

**EXACT NEXT STEP, cc:** build `tools/citation_anchor_rot_check.py` to the spec
— **8 requirements, 10 failing-first arms.** **A2** (an anchor appearing twice
is a FINDING, not a pass — the only arm that catches the *next* rot), **A4**
(absent target → **exit 2**, never 0), and **A10** (a document with no anchors
prints `0 anchors, 0 line citations` **out loud**) are the three a reviewer
would cut and the three that matter. **A7 pins this batch's row and is checkable
as having been RED before it.**

**UNVERIFIED, and I am not extrapolating:** how many of
`docs/CRITICALITY-TIERS.md`'s **hundreds** of remaining `` `:NNNN` ``
citations are stale. The `sf_events` row was 7 of 7 — **and that row was edited
across several batches, which is the condition that rots citations, so it is not
a sample.** **The check's first run is the measurement.**

### 3.6 Still open from earlier batches

* **cc:** **F3 first** (§3.2), then F5/F6/F2/F4/F1; the anchor rot check (§3.5);
  `tools/batch_manifest.py:386` (**still worked around with
  `PYTHONIOENCODING=utf-8` on every call**); the four b19 census asks
  (**ask 1 then ask 4 — the only preventive one**); the three `tools/` fixes
  from the b19 queue16 review; `--read-the-line` on
  `citation_line_drift_check.py` (**§3.1's F3 is its cheapest customer**);
  `tools/fixture_lock_check.py`; the by-design validator and **four rulings at
  `DECIDE_OR_NOT_PROMOTED`**; a lock reaper with a stated threshold
  (**partly answered: `session_lock_check.py guard` is the verb — what is
  missing is a stated threshold and a sweep, not the mechanism**); the
  `rm`-deny decision; the corrupted register twin on `7bc26782e533`; the
  session-start surface for any obligation over 48h; **step 4a missing from the
  operator runbook** in `docs/NHI-REGISTER.md:69`.
* **cody:** the two b20 arms (§3.1 — the aftercare collision arm, and the
  function-name anchor that degrades to *unproven* at exit 3); the four b19
  arms; T17/T18 and b18's N1–N4, **all failing-first**; the oversized-`sd_photos`
  arm; the two SAIRNcash entitlement arms (**ARM B first**); fixture rows 26–50
  with row 39 first; b14's T7–T10 and T14; T16.
* **hank:** **F4 then F5** (§3.1), then F2/F3/F1; the `sd_photos` **size fix
  first with T17 landing with or before it**; the 400→503 misattribution; the
  `sfDeleteEvent` verification; b18's F1 and N1–N4 — **N1 is untouched by this
  batch's `clock_flags` merge and REMAINS OPEN**; §7.6's five points; the three
  role matrices; the two b17 conditions; the four removal paths with
  `sv_scribe_consent` first. **NOBODY DELETES `api/ai-notice.js`.**
* **hover2:** the four `# OWNER:` lines and the three decisions (§3.4); b19's
  F1, the `--selftest` temp-directory leak.
* **hover + hover2 jointly:** which tree is canonical for the four shared
  basenames (§3.4).
* **MICHAEL:** run-order blocks 5 and 6 (§3.1); the two `[DRAFT — LAWYER]`
  strings. **Option B stands; he was not asked this batch.**
* **counsel:** three questions. **A funeral director:** five — **and five of
  the eight gate the band assignment §3.1 just verified as faithfully
  transcribed.** **A vet practice:** two. **A home-care practitioner:** one
  (H8).
* **fourth (me):** **b21 item 1** — the 39h/2h document-only obligation,
  **plus the deliberate decision on its strong-basis re-seat**; **b21 item 2** —
  hank b11's 33-resource obligation. Also fixture row 11, whose code is cc's.

---

## 4. THE THING THE NEXT SESSION MUST DO FIRST

**Write the manifest. Then `tier_a_review_gate.py --list` and read the rows
owned by `fourth` before anything else** — there are two, and **the older one is
overdue on the 24h clock while being only 2h old on the assignment clock.**
Those are different clocks and the handoff above says which is which. **Take the
document-only one first: it is the overdue one and the smaller job.**

**And the b20 lesson, which is not about Tier A at all:** **cc's change was
correct, well-described, and broke its own control — and nothing in the commit
noticed.** The arm was grepping prose. **Anchor on the thing meant to be stable
— a token, a quoted string, a function name — never on the sentence around
it.** That is the same sentence as §3.5's and the two findings are the same
defect in two materials.

---

## 5. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. Commit this handoff with the manifest's item-6 edit, and push.
2. Upload this handoff to Drive folder
   `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` and verify.
3. The report and digest, plus **`SAIRN-latest-fourth.md`** (digest + open items
   + routed items + a CONTEXT line + the chain tip, under ~60 lines), then
   upload-and-verify, then a **Drive-side API read** — the mount proves the
   bytes are in the sync set, not that Google acknowledged them. **Expect the
   API read to lag by a minute; b19's first read came back empty and was a
   retry, not a missing file.**
4. `batch_manifest.py --close --agent fourth --batch b20` — **after** the
   uploads, because closing is *defined* as verified.
5. **Release the b20 claim last**, and set the status row to `idle`.

**Nothing is partial.** Every open item above is another session's, or mine and
named as mine with its b21 slot, or a measurement with its command stated.
