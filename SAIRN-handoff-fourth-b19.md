# HANDOFF — fourth / ted, batch b19, 2026-10-14

**Written BEFORE the report**, at a point where nothing is half-finished: items
1–6 are committed and pushed, `HEAD == origin/main`, the working tree carries
only the b19 manifest's own final `--set 6` edit, no rebase or stash is in
progress, and the b19 claim is still held on purpose.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you
intend to quote** — including out of this file. That is not boilerplate: see
§3.3, where a third re-derivation of my own b18 documents found a citation that
had been wrong in a way no offset-shift would have caught.

**The two things worth reading first:** (1) **both of my overdue Tier A
obligations are discharged** — 397h and 339h — and one of them produced the
sharpest finding of the batch: *two* of cody's five self-flagged claims have
**correct code and false reasoning**, with the real protection living in a
*neighbouring* arm the author credited to the arm under discussion; (2) **the
`sd_photos` premise is measured and my own b18 ordering was backwards** — the
size failure is the live, total defect and the provenance gap is latent behind
it for every real photograph.

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\b0f8683c-3365-4d5b-82ea-094a13bdff7e\scratchpad\`
New this batch: `tier_a_list_b19.log`, `verdict_b19_queue16.txt`,
`discharge_queue16_b19.log`, `verdict_b19_hover2.txt`,
`discharge_hover2_b19.log`, `hover_lint_drive1.log`,
`hover_lint_selftest.log`, `hover_lint_failclosed.log`,
`hover_lint_noargs.log`, `reseat_reviewed_b19.log`,
`reseat_reviewed_b19.json`, `reseat_parsed_b19.json`, `dangling_34_b19.txt`,
`pull_b19.log`, `pull_loop_b19.log`, `push_loop_b19.log`,
`statusline_payload.json`.
*(This is the same session as b18, so b18's logs are in the same directory.)*

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `a96efce0` | `git rev-parse --short HEAD` |
| `origin/main` | `a96efce0` | `git rev-parse --short origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | **one modified file**: `docs/batch-manifest-fourth-b19.json`, carrying item 6's own evidence. Committed with this handoff | `git status --porcelain` |
| the b19 work commit | `f9677da4`, rebased to land as part of `e46ccfcd..a96efce0` | `git log origin/main --oneline -3` |
| push forced? | **NO** | `e46ccfcd..a96efce0`, **first attempt, no rejection**; `grep -ci force` over the push log → **0** |
| `SAIRN_SEED_GATE=off` | **not used, any form** | — |
| `SAIRN_GATE_EXEMPT=seed` | **not used either.** *(Noted because `CLAUDE.md`'s push protocol changed under me mid-batch: the scoped exemption is now the correct first reach and the blanket flag is documented as the wrong one. I used neither.)* | — |
| `.claude/settings.json` | **not edited, not committed** | not in the commit's file list |
| hooks | **untouched** — not added, not removed, not restored | by instruction |
| files written outside `docs/` | **0** (plus my three root deliverables) | by instruction |
| files written under `.claude/skills/sairn-hover-auditor/` | **0 — and the auditor clone was never entered** | §3.2 |
| all five b19 `docs/` files on `origin/main` | **5 of 5** | `git cat-file -e origin/main:<path>` per file |
| b19 manifest | **6 of 6 `done`**, close pending the three uploads | `batch_manifest.py --check --agent fourth --batch b19` |
| context at this handoff | **42% of 1000k** | `tools/sairn_status_line.py` fed this session's transcript |

**`a96efce0` IS THE STATE AT FINALISATION OF THIS HANDOFF** — this file, the
report, the digest, the b19 close and the claim release all land after it.

---

## 1. ITEM BY ITEM

| # | item | state | exact next step |
|---|---|---|---|
| 1 | discharge the 397h obligation (cody, `dnt_ar`/`dnt_revenue`) | **DONE — DISCHARGED, exit 0.** 7 findings | **cody: 4 arms. cc: 3 `tools/` fixes. hank: 1. Shared: the `sf_events` anchors** (§3.1) |
| 2 | discharge the 339h obligation (hover2, `leg_insurance`/`mech_checks`) by a real drive | **DONE — DISCHARGED, exit 0, four drives with exit codes 0/0/2/0** | **hover2: F1, two lines. And the five unreviewed sibling tools in `c78b545b`** (§3.2) |
| 3 | re-derive every line number in the two b18 documents | **DONE — 71 checked, 70 unmoved, 1 moved, 0 not found** | nothing; the mover is now anchored on quoted text (§3.3) |
| 4 | classify the 34 dangling REVIEWED shas; route the tool work | **DONE — all 34 listed individually, 7 classes, 4 asks routed with a priority order** | **cc: ask 1 first, then ask 4 — it is the only preventive one** (§3.4) |
| 5 | measure the `sd_photos` premise from source only | **DONE — and it reverses my own b18 ordering** | **hank: 4 items, size first. cody: 1 failing-first arm** (§3.5) |
| 6 | push without force, confirm landed | **DONE — `e46ccfcd..a96efce0`, 0/0** | nothing |
| — | this handoff, before the report | **DONE** | — |

---

## 2. CLAIMS, LOCKS AND HOLDS

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b19, published on `origin/main`; **release last**, after the report and digest are up | `sairn_claim.py list` |
| **Tier A obligations assigned to me** | **2, BOTH INSIDE THE 24h DEADLINE** | **(a) 4h** — `hank` `2026-10-14T13:50:42Z`, 21 `leg_*` resources + `rf_settings`, 5 files incl. `api/_lib/leg-roles.js` and `api/sd-data.js`. **(b) 1h** — `cc` `2026-10-14T17:20:09Z`, `quotes`, `sd_comms`. **Neither is overdue; (a) has ~20h left** | `--list` |
| obligations discharged this batch | **2** | 397h and 339h, both as the **assigned owner**, neither by `--takeover` | `--list` before/after: 19 → 18 open (one new arrived) |
| session locks held | **1 of 14 on disk** | `fourth.lock`, `claude_pid 53204`, `started 2026-10-13T05:36:03` — **re-read this batch, not quoted.** Eight batches old | `cat ~/SAIRN-SESSION-LOCKS/fourth.lock` |
| locks removed by me | **0** | `rm` is denied and I did **not** route around it | — |
| `git stash` | **0** | | `git stash list` |
| worktrees besides main | **4** | **none mine** — other sessions' temp gate trees under `AppData\Local\Temp` | `git worktree list` |
| status registry row | `working` | set at batch start; set to `idle` at release | `sairn_status.py set` |

**THE THING THAT CHANGED SHAPE THIS BATCH:** b18 handed over *two overdue
obligations, both mine*. **Both are discharged.** What replaces them is two
**fresh** ones, and that is a different state — there is no overdue Tier A work
assigned to `fourth` for the first time in at least three batches.

**hank's 4h `leg_*` obligation was left deliberately, per the b19 instruction
("two discharges in this batch, not three ... unless it nears its 24h
deadline"). It did not near it — it is 4h old.** It is **b20's item 1**, and it
is the larger of the two: 21 resources across five files including
`api/sd-data.js`. **cc's 1h obligation arrived mid-batch and is b20's item 2.**

---

## 3. WHAT IS OPEN, AND WHY

### 3.1 The 397h discharge — correct code, false reasoning, twice

`docs/2026-10-14-fourth-b19-tier-a-queue16-discharge.md`. **A STATE review:
`f88105a88287` dangles. A WEAK re-seat candidate exists (`bb840eeccb3c`,
FILE-SET SUBSET) and was READ for arm A3's pre-change text but NOT written** —
containment is not equality, and the tool splits those across two flags for
that reason.

**Claims 1 and 5 hold. Claim 3's arithmetic holds and its safety claim does
not. Claims 2 and 4 do not hold as stated.** The pattern across the two that
failed is the finding:

> **In both cases the code is defensible while the stated reasoning is false,
> and in both the real protection lives in a NEIGHBOURING arm that the author
> credited to the arm under discussion.**

* **Claim 2, measured false in both halves.** `3b ⟹ 3c` unconditionally, so 3c
  is a strict *weakening* and not a complement. And on a registry shrunk to two
  rows **both pass** — `3b True, 3c True` — while what actually dies is `3a` and
  `3c0`, the floor arms added in the same edit. **cody asked for exactly this
  test** (*"test that reasoning, it is the whole justification"*) and it does
  not survive. The `len(unrequested) < 5` floor that tolerated four unnamed
  resources under a label saying *"every"* **was** genuinely fixed.
* **Claim 3.** The arithmetic is right. The arm has **no guard of its own** — it
  rejects only an unparseable version and accepts `.0` and `.1`, where the
  demanded set is empty and the assertion is trivially true; the neighbouring
  `int(rev) >= 2` arm is what saves the suite. **Cheapest defeat, one token:
  `CRITERIA_VERSION = '2026-10-14.2'`** — a restarted counter stamping a 4th
  revision, both arms green. Also the explanation check is a **substring test
  over the whole file**, so *"requires adding the explanation"* is false — it
  requires adding the string.
* **Claim 4, both directions.** Too permissive: membership is tested on a
  **module-blind tail name**, so `ast.walk` reads as a file-tree population in
  21 tools **including the checker's own self-verdict**, while its real
  `git ls-files` enumerator is in no family at all. The criterion compares
  accessor **names and never arguments**, and a fixture **pins
  `tracked('*.py')` vs `tracked('*.js')` as agreeing** — real code of that shape
  exists in two tools, so the literal defect shape is declared CLEAN. Too
  strict: the tool prints a **live false positive at HEAD** on
  `tools/purge_evidence_gate.py`, from a door that cannot exist and from
  treating a strict **superset** as disagreement — a shape **none of its 21
  fixtures decides**.
* **Claim 5 is TRUE.** Five candidate second paths between a hall event and its
  minted session, all disproved: `fromEvent` is a write-only boolean with
  **zero readers**, the session row carries neither title nor kind, positions
  are not stable, nothing derives one id prefix from the other, and no naming
  convention is stored. **A stranded session WOULD still count toward the
  three-in-seven statutory limit**, so the B→A promotion rests on a correct code
  fact. **Two adjacent defects found: `sfDeleteEvent` reports *"Event and its
  bingo session removed"* on a STALE pointer that matched nothing — affirmative
  false success — and `sfDeleteSession` never clears the event's pointer while
  the UI offers Remove on every row.**

**EXACT NEXT STEPS:** **cody** — make the older-commit arm non-skippable; fix
the 3c comment or make it a real complement; have the version arm assert its own
floor; three fixtures for the scope checker (the `POPULATION_CALLS`-vs-`FAMILIES`
one-liner first — it would have caught the orphaned `ls_files`). **cc** (owner of
`tools/`) — the `ast.walk` tail-name collision, the missing-flag door, the
printed-detail formatting. **hank** — verify `sfDeleteEvent`'s delete and
refuse-or-warn in `sfDeleteSession`. **Shared** — all six `sf_events` register
anchors have rotted.

### 3.2 The 339h discharge — a real drive, and the bound is the five tools nobody reviewed

`docs/2026-10-14-fourth-b19-hover2-citation-linter-discharge.md`. **Both
recorded shas RESOLVE (`82b69588a125`, `c78b545b`), so unlike my other two
discharges this week this one is a real DIFF review.**

**FOUR DRIVES, real exit codes:** `--lint` on the exact resource name → **0**;
`--selftest` → **0, 33 ok 0 failed**; `--lint --file <nonexistent>` → **2
`COULD NOT RUN: FileNotFoundError`**, so fail-closed is verified **in
execution**; no args → **0**. **The linter's own sha256 is `c226563783a8e56e`
before and after all four**, and `git status` showed only my own untracked
manifest throughout.

**NO FINDING AGAINST THE PREMISE.** Auditor tooling only; **`grep -n '\bgit\b'`
returns zero matches**, so there is no git-subcommand question at all; every
write construct is inside `selftest()` and all three go to `%TEMP%`; no network
of any kind; the two resource names appear **nine times, every one a fixture
literal, a test argument or a test name**, exactly as the obligation asserts.

**ONE FINDING, F1, hover2's, lowest severity:** `--selftest` **leaks** a temp
directory and the `draft.txt` inside it on every run — the `finally:` removes
only the `mkstemp` fixture. Two lines of `shutil.rmtree(..., ignore_errors=True)`.

**THE REAL BOUND, AND IT IS b18's LESSON APPLIED TO MY OWN WORK RATHER THAN
FOUND IN SOMEBODY ELSE'S:** `c78b545b` synced **six** tools and this review
opened **one**. **The other five are not reviewed and are not blessed by this
verdict**, and that is said in the verdict string itself so the register
carries it. **EXACT NEXT STEP: somebody names the other five and decides whether
they need their own obligation** — that is a routing decision, not a review.

**And a credit, because a review that only lists findings is not a review:**
this tool already names a **third state** (`UNVERIFIED-CROSS-LOG`, never folded
into pass or fail), **fails closed with exit 2**, and **counts a skipped
regression as a FAILURE** on the stated ground that an undriven regression
proves nothing. Those are three of the conventions this review would otherwise
have existed to enforce.

### 3.3 The citation re-derivation — and why a count would have missed it

**71 citations checked against HEAD after the pull: 70 UNMOVED, 1 MOVED, 0 NOT
FOUND.**

**The mover is the interesting one.** `api/_lib/sen-evv-clock.js:120-131` was
cited for *"a literal array"* — and at HEAD that range holds **the tail of a
refusal message**, not the array. The real construct is the array at `:79` and
the `field.replace` loop at `:129-140`. **An offset-shift would not have caught
this**, because the cited range was not merely displaced — it had never pointed
at what the sentence said. It is now anchored on `const CLOCK_FIELDS = [...]`
and on `stamps[field.replace('_at', '_received_at')] = serverNowISO;`, so the
next drift is visible rather than silent.

**Two bare `:N` continuations were confirmed as pointing at the file TWO
paragraphs back rather than the nearest one** (`:20-24` → the census SQL,
`:740` → the compliance seed). Both were right — **and both are exactly what a
mechanical re-offset would have broken.**

**THE STANDING LESSON, now three batches old and re-earned each time: re-derive
by content, never by arithmetic.**

### 3.4 cc — the dangling-sha census, and the number b18 did not mention

`docs/2026-10-14-fourth-b19-dangling-sha-census.md`. **All 34 listed
individually** with classification, re-seat target, author→reviewer and
resources. **The b18 figure reproduces exactly** (252 records, 107 with a sha,
66 reachable → 34 of 88 reviewed), which matters because b18 was *quoting* the
tool and this is an independent derivation.

**THE FRAMING FINDING:** `REFUSED: NO_SHA_AT_ALL` → **145 further reviewed
records, every one of them `reviewed`**. **That is not a dangling sha** — those
records never claimed one. **179 reviews are unre-derivable from the register
and only 34 of them are a defect; the rest are history.** Any fix aimed at the
34 leaves 80% of the population untouched, and "34 dangling" read alone
overstates what a re-seat buys.

**Three things a count would not have shown:** b18's own 418h obligation is
**in this list** (`NO_OBJECT_IN_CLONE` — which is *why* that discharge had to be
a state review); **the newest entry is three hours old**, so this is live and
not a backlog; and **six of the 34 name `docs/CRITICALITY-TIERS.md` as their
only file**, so their exact-set matches come back AMBIGUOUS because the file set
is not discriminating.

**`SHA_WRONG_WHEN_WRITTEN` (2 records) is the only class that implies a
WRITE-TIME defect** — a rebase cannot cause it. **Both were authored by
`fourth`**, which is why it is said out loud rather than routed quietly.

**EXACT NEXT STEP, cc, with a priority because four equal asks are no
priority:** **ask 1 first** — separate `NO_SHA_AT_ALL` from the dangling
population in every output, so a `REFUSED: 172` stops reading as 172 defects.
**Then ask 4** — stamp the sha in the same commit that writes the record; it is
**the only preventive one**, and the three-hour-old entry says the current path
can produce an already-absent sha. Then ask 2 (give
`SHA_WRONG_WHEN_WRITTEN` its own exit path), then ask 3 (the window constant —
**an exact file-set match outside the window is better evidence than a subset
match inside it, and today the first is refused while the second is offered**).

**I re-seated NOTHING.** One strong-basis record exists and it is **open**, not
one of the 34; the 10 weak ones need two flags on purpose.

### 3.5 hank — the `sd_photos` premise, and my own b18 ordering was backwards

`docs/2026-10-14-fourth-b19-sd-photos-premise.md`. **SOURCE ONLY — no SQL, no
endpoint, no browser.**

```
cap on data::text                         65,536   sql/stonedesk_data_schema.sql:343
client accepts                        10,485,760   stonedesk.html:25988
what lands in `data`     the whole base64 data URL, unmodified, no downscale
                                                   stonedesk.html:25999
==> binary bytes that fit                 ~48,909   (65536 − 23 prefix − ~300 JSON) × 3/4
```

**Every real photograph fails.** A phone photo is 2–5 MB against a ~48.9 KB
ceiling. And the rejection is **misreported**: a Postgres CHECK violation
arrives as 400, and `api/sd-data.js:14263` folds 400 in with 404 and answers
**`503 NOT_PROVISIONED` — "tables are not set up yet"** — pointing the reader at
a migration they have already run. **`grep` finds twelve such branches**, so it
is a pattern. And the only client report is **`console.warn`**: `sdDataFailed`
has no other body — **no toast, no banner** — while the photo sits in the panel
with its `🧠 Done` badge.

**VERDICT: THE SIZE FAILURE IS THE URGENT HALF.** The provenance gap (b18's
T17) is **live only for rows that land**, which today is the near-empty set of
sub-48 KB images. **So fixing size alone converts a latent provenance gap into a
live one at full volume on the same day — T17 must land with or before the size
fix.** That sequencing is the actionable output, and **it is the opposite of
what my own b18 §7.6.1 ordering implied.** b18 named the right conclusion as a
possibility in its last sentence and then ordered the document the other way
round; **that is the error worth recording — a conditional stated honestly and
then not resolved leaves the reader acting on the ordering.**

**EXACT NEXT STEPS, hank, in order:** (1) decide where the image lives — I
recommend **client-side downscale** as the smallest change that makes the backup
real, with separating the blob from the row named as the direction of travel;
**raising the cap is a design call, not a constant bump**, since 65,536 is a
house convention correct on a dozen sibling tables. (2) **Stop the 400→503
misattribution** — worth doing independently and immediately. (3) Make the
failure visible to a human. (4) Then T17. **cody:** one failing-first arm — an
oversized `sd_photos` write must not answer `503 NOT_PROVISIONED`.

### 3.6 Still open from earlier batches

* **cc:** `tools/batch_manifest.py:386` (still worked around with
  `PYTHONIOENCODING=utf-8` on **every** call this batch); the four census asks
  (§3.4); the three `tools/` fixes from §3.1; `tools/fixture_lock_check.py`
  (b13); the by-design validator (b12) and **four rulings still at
  `DECIDE_OR_NOT_PROMOTED`**; a lock reaper with a stated threshold; the
  `rm`-deny decision; `--read-the-line` on `citation_line_drift_check.py`
  (**which §3.1's F7 is the cheapest customer for**); the corrupted register
  twin on `7bc26782e533`; the b18 session-start surface for any obligation over
  48h (**A3 fail-closed and A6 third-state are its load-bearing arms**); and
  **step 4a missing from the operator runbook** in `docs/NHI-REGISTER.md:69`.
* **cody:** the four b19 arms (§3.1); T17/T18 and the four b18 arms (N1–N4),
  **all failing-first**; the oversized-row arm (§3.5); the two SAIRNcash
  entitlement arms (b16, **ARM B first**); fixture rows 26–50 with row 39 first;
  b14's T7–T10 and T14; T16 (b17).
* **hank:** the four `sd_photos` items (§3.5); F1 and N1–N4 from b18 plus
  §7.6's five implementation points; the `sfDeleteEvent` verification (§3.1);
  the three role matrices, **SAIRNlegacy first**; the two b17 conditions; the
  four removal paths with `sv_scribe_consent` first. **NOBODY DELETES
  `api/ai-notice.js`.**
* **hover2:** F1, the `--selftest` temp-directory leak (§3.2).
* **MICHAEL:** **not asked this batch, by decision.** Option B
  (management-only) stands until a practitioner answers **H8**. The two
  `[DRAFT — LAWYER]` strings.
* **counsel:** three questions. **A funeral director:** five. **A vet
  practice:** two. **A home-care practitioner:** one (H8).
* **fourth (me):** **b20 item 1** — hank's `2026-10-14T13:50:42Z` obligation,
  21 `leg_*` resources + `rf_settings`, 5 files; **b20 item 2** — cc's
  `2026-10-14T17:20:09Z`, `quotes`/`sd_comms`. **Neither is overdue yet and
  item 1 has ~20h left.** Also: naming the five unreviewed sibling tools from
  `c78b545b` (§3.2), and fixture row 11, whose code is cc's.

---

## 4. THE THING THE NEXT SESSION MUST DO FIRST

**Write the manifest. Then run `tier_a_review_gate.py --list` and read the rows
owned by `fourth` BEFORE anything else** — there are two, both fresh, and the
older has roughly twenty hours left. **Discharging them inside the deadline is
the first time this role would have met the clock rather than cleared a
backlog**, and that is worth preserving: a queue that is current is a different
object from one that is being drained.

**And the b19 lesson, which generalises beyond Tier A:** when an author flags
their own work and says *"check this reasoning, it is the whole
justification"* — **check the reasoning separately from the outcome.** Two of
cody's five claims had code worth keeping and a justification that was false,
and in both the protection they described lived in the arm *next door*. **A
correct arm kept for a false reason is an arm nobody can maintain**, because the
next editor reads the comment, not the measurement.

---

## 5. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. Commit this handoff together with the manifest's item-6 edit, and push.
2. `PYTHONIOENCODING=utf-8 python tools/drive_upload_verify.py --agent fourth
   --batch b19` — **will report findings**, because the report and digest do not
   exist yet. Expected; the handoff is written first by instruction.
3. The report and digest, then the same upload-and-verify, then a **Drive-side
   API read** — the mount proves the bytes are in the sync set, not that Google
   acknowledged them.
4. `PYTHONIOENCODING=utf-8 python tools/batch_manifest.py --close --agent
   fourth --batch b19` — **after** all three are up, because closing is
   *defined* as all three verified.
5. **Release the b19 claim last**, and set the status row to `idle`.

**Nothing is partial.** Every open item above is another session's, or mine and
named as mine with its b20 slot, or a measurement with its command stated.
