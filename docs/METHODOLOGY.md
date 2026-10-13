# METHODOLOGY — a pointer, deliberately, not a second home for the conventions

**Created 2026-10-06 (Fourth). It is three paragraphs on purpose.**

Two sessions were routing work to this filename — cc for three methodology
conventions, cody for one plus three more
(`docs/2026-10-06-cody-routed.md`: *"`docs/METHODOLOGY.md` | **fourth** |
ITEM 15 — three conventions + three more"*) — and the file did not exist. So
either it gets created, or every such routing silently drops.

**The standing conventions live in ONE file and it is not this one:**

> ### `docs/2026-09-13-cross-domain-disciplines.md`

**COUNT THE `## <n>.` HEADINGS IN THAT FILE rather than trusting any number
written anywhere, including here.** That is the file's own instruction and
`CLAUDE.md` repeats it, because the count has been wrong in three places at
once before and was wrong again on 2026-09-25 when two sessions each added an
eleventh within the hour.

## Why this file is a pointer and not a document

A second home for a convention is a second thing to drift, which is item 8 of
the file it would be competing with — *nothing announces the day a check stops
testing anything* — applied to prose. Two files each holding "the conventions"
produce exactly the failure this platform keeps paying for: a reader finds one,
acts on it, and the correction is in the other.

So the rule for this file is narrow and is the whole content:

* **A convention goes in `docs/2026-09-13-cross-domain-disciplines.md`**, as a
  numbered section, with the real incident that paid for it and a *"where it
  does not transfer"* paragraph. Nowhere else.
* **A dated inventory may STATE a lesson and route it**, which is what cody did
  for the captured-exit-code rule rather than promoting it from a dated file —
  *"a lesson in a dated file is the eighth convention waiting to happen."*
* **This file records what is ROUTED HERE AND NOT YET PROMOTED**, so a handover
  is visible rather than lost. That is the only list it carries.

## Routed here and not yet promoted

| Routed by | What | State at 2026-10-06 |
|---|---|---|
| cody, `2026-10-06-cody-queue16-inventory.md` §8 | a green claim must cite an exit code captured by whatever WAITED on the tool | **PROMOTED** as convention **15** |
| cody, `2026-10-06-cody-routed.md` | *"three conventions + three more"* for this file | **NOT RECEIVED.** Only the §8 one above is written down anywhere I can read. The other items in that document are registrations and an OWNER-line proposal, not conventions. Asked back rather than guessed at |
| cc, claim text 2026-10-06 | *"item 15's three methodology conventions … are routed to fourth for METHODOLOGY.md"* | **NOT RECEIVED.** `docs/2026-10-06-cc-batch-9-inventory.md` is named in cc's claim but is not on `main` at the time of writing, so the three conventions are not readable. Nothing invented in their place |
| cody, `2026-10-06-cody-routed.md` | **283 of 296 `tools/*.py` carry no `# OWNER:` line** (13 do). Routed as a proposal, with the note that the generator which would enforce it is fourth's | **QUEUED, NOT STARTED — and re-counted rather than quoted.** At HEAD 2026-10-06: **298** `tools/*.py`, of which **15** carry a `# OWNER:` line in their first six lines and 2 more mention `OWNER:` further down. So 283 is now 283 again by coincidence of a moving numerator and denominator, and the figure to act on is **15 of 298**. **AND THE CHECKER ALREADY EXISTS**: `tools/tool_owner_header_check.py` is on `main`. The open work is the 283 headers, not the gate — which changes the shape of the proposal and is why it was re-counted instead of accepted |
| hank, `docs/2026-10-06-inventory-hank-batch9.md` | **A FIXTURE TIDIER THAN PRODUCTION TESTS A SYSTEM THAT DOES NOT EXIST.** A checker's fixtures must carry the shape the real code carries -- including the parts that look like noise -- and a fixture no real code matches is deleted, not kept beside a true one. **Paid for three times by ONE tool in two days, `tools/gate_parity_check.py`, and twice it blinded the tool to the very defect it was built from:** (1) its pre-fix fixture declared the role set INSIDE the gated branch, where no handler in `api/sd-data.js` declares one -- the real handler declares it in the shared prelude -- so the arm PASSED while the ablation against the actual pre-fix file flagged three groups and `alf_family_contacts` was not one of them; (2) its write-path fixture answered a bare `{ ok: true }`, where every real write on this platform carries `Prefer: return=representation` and answers `{ ok: true, data: rows[0].data }` -- so the tool compared writes against reads after its own docstring said it would not, and the first live run reported 36 groups that were mostly the design; (3) a source-anchor arm cut its block on a string that exists only in a COMMENT, which the same arm strips two lines earlier, so the block ran to end-of-file. **THE DETECTOR IS CHEAP AND IS THE WHOLE CONVENTION: run the checker against the REAL PRE-FIX FILE, not only against fixtures.** All three survived a green fixture set and none survived one ablation. Related to but not the same as convention **12** (ablation over chaos): 12 is about removing a layer from clean code to measure what it alone catches; this is about the FIXTURE being unrepresentative, which 12 cannot see because an ablation of a wrong fixture is still wrong | **ROUTED 2026-10-06, NOT PROMOTED BY ME.** The standing conventions live in `docs/2026-09-13-cross-domain-disciplines.md` -- **count the `## <n>.` headings rather than trusting any number written down**; it is 15 at HEAD `264d8c3f`. Promotion is a judgement for whoever owns that file, and self-promoting a convention out of my own defects is the detector-blessing-its-own-fix shape convention **11** refuses |
| hank, `docs/2026-10-06-inventory-hank-batch10.md` | **A GENERATOR THAT REFUSES LOUDLY ON ONE FAILURE MODE MUST REFUSE AT LEAST AS LOUDLY ON ITS MIRROR.** Where a check has an obvious opposite &mdash; missing vs duplicate, absent vs present, under vs over &mdash; the loud side teaches everybody that the mechanism is watching, and the silent side is then trusted by exactly the people the loud side trained. **PAID FOR BY `tools/tooling_inventory.py`, measured by driving it:** a MISSING `PURPOSES` entry exits **2** with *REFUSING to generate* and names the tool; a DUPLICATE key exits **0**, silently, because Python keeps the last of two identical dict keys and discards the first and the generator never looks. **The duplicate is the worse half:** a missing entry announces itself at the next push, while a discarded entry is a cell somebody WROTE, believing it landed, that is invisible in the rendered document AND in the generated source. It happened on 2026-10-06 and the author could not have found out. **THE GENERATOR'S OWN JUSTIFICATION ARGUES FOR IT** &mdash; it refuses a missing entry because *&ldquo;a blank cell is how the last inventory went stale&rdquo;*, and a blank cell is at least VISIBLE. **THE TEST IS CHEAP AND IT IS THE CONVENTION: for every loud refusal, name the opposite condition out loud and drive it.** If the opposite is silent, that is a finding, not a gap in coverage. Not the same as convention **8** (nothing announces the day a check stops testing anything): 8 is about a check going stale over TIME, this is about a check that was never symmetric on the day it was written | **ROUTED 2026-10-06, NOT PROMOTED BY ME, and the artifact is runnable:** `tests/run_purposes_duplicate_key_probe.py` drives the real generator in a scratch tree, proves both halves (`missing -> exit 2 REFUSING`, `duplicate -> exit 0 silent`), and exits 0 the moment the fix lands, so it is the acceptance test as well as the evidence. The standing conventions live in `docs/2026-09-13-cross-domain-disciplines.md`, which is **fourth's** &mdash; count the `## <n>.` headings rather than trusting a number; 15 at HEAD `c586d0e3`. Promoting a convention derived from my own near-miss is the detector-blessing-its-own-fix shape convention **11** refuses |

| fourth, `docs/handoff-fourth-2026-10-07.md` batch-16 rows 4 and 5b, 2026-10-07 | **A PROGRESS METRIC WHOSE NUMERATOR IS COUNTED OUT OF A DEFECT REGISTER MOVES BACKWARD ON SUCCESS, and the number alone cannot say which direction was good.** The census of individually-verified red suites is defined as *register rows carrying a SHA-stamped individual run that are inside the 83-item pinned FAIL list*. This batch drove ten suites alone and stamped them: **40 -> 50 of 83.** Then one arm fix cleared four suites, and the register's own rule -- *an entry whose suite has gone GREEN must be deleted, because while it stands it swallows the next real failure of that file* -- required deleting those four rows. **The census read 46 of 83 ten minutes after it read 50, and the four rows that left it are the only four in the whole population that are VERIFIED GREEN rather than verified red.** A reader taking the number as progress sees a 4-point regression caused by the best outcome available. **This is not a bug in the register and not a bug in the census; it is a metric whose denominator is a fixed historical list and whose numerator is a LIVE table that shrinks when work succeeds.** It is adjacent to convention 14 (state n of N before using a sample as evidence) and to convention 22 (a window is a measurement), but neither covers it: the sample here is complete and the window is the whole list -- what moves is MEMBERSHIP, and it moves in the direction that looks like failure. **The cheap fix, stated as a proposal and not applied:** a metric built on a mutable register records RECOVERED as its own third state rather than as an absence, so verified-green and never-measured are not the same cell -- which is the same absence-versus-unknown distinction `known-red-suites.json` already enforces one level down in its `environment` stamps, and the same third-state discipline as conventions 17 and 24 | **PROMOTED 2026-10-07 (batch 17), BY INSTRUCTION, AND IMPLEMENTED RATHER THAN WRITTEN DOWN.** It was routed and not self-promoted when found -- promoting a convention out of my own measurement artefact is the detector-blessing-its-own-fix shape convention **11** refuses. Chat then asked for the census to report THREE counts, and a count cannot be derived from rows that have been deleted, so the promotion is a STRUCTURE and not a sentence: `docs/known-red-suites.json` now carries a top-level **`recovered`** list beside `entries`, plus a `_what_recovered_is` that states the rule -- `entries` means KNOWN RED, `recovered` means VERIFIED GREEN at a named commit, and a suite in NEITHER is UNMEASURED. `tools/known_red_check.py` reads only `entries`, verified by reading it, so the key is additive and changes no verdict it prints. **The census now reads GREEN 5 / RED 51 / UNMEASURED 27 = 83, and the figure that only ever goes UP is the 56 individually verified.** A `recovered` row is not an allow-list entry: it records exit 0 on one commit, and a regression turns it back into an `entries` row. **Still open and named rather than closed with it:** the 18 unbaselined primitive-obsession occurrences across five apps are untouched -- that row fixed a probe, not a tree |
| fourth, `docs/handoff-fourth-2026-10-07.md` batch-17 rows 6, 7 and 9, and `docs/2026-10-07-fourth-routed.md` SEQ 17-A and 17-C, 2026-10-07 | **CONVENTION 25's TRIGGER SHOULD COUNT FALSE-POSITIVE CLASSES AGAINST A SOURCE CONSTRUCT ACROSS EVERY CHECKER, NOT WITHIN ONE CHECKER.** As landed, 25 says: at three distinct false-positive CLASSES from ONE checker, stop patching and review the design. That shape is right and its scope is too narrow, and this batch measured why. **ONE COMMENT BLOCK -- `sairnsenior.html:5768-5780`, which exists solely to record that `sen_settings` must never be written locally and therefore has to quote `st('sen_settings')` to say so -- produced THREE DIFFERENT WRONG ANSWERS FROM THREE DIFFERENT CHECKERS:** (1) `tests/phi_cache_scoped_to_user.js` arm 5a counted it as two WRITES and demanded a purge rule for a cache that does not exist, holding four register rows shut and leaving a PHI purge guard's seven mutations unplanted; (2) the SEQ 17-A sweep found **47** more derived sets that shrink when comments are stripped, including two that are **100% phantom** -- `tools/stale_row_sweep.py:240` set 29 -> 0 and `tests/sairnvet_seed_never_syncs.js:98` set 1 -> 0, asserting entirely about prose; (3) `tools/citation_line_drift_check.py` proposes repointing the `sen_settings` citations AT LINE 5774 OF THAT SAME BLOCK -- offering, as the write site, the line that says there is no write site. **Under 25 as written, each tool has ONE class and none reaches the trigger, so the design review never fires.** Counted the other way -- per SOURCE CONSTRUCT, across checkers -- the trigger was met and the answer is already on disk: `tests/lib/strip_comments.js` exists because THREE private comment-strippers were each wrong in a different direction, and its header is the artefact of this rule being followed before it was named. **The fix is one line per checker and the same control arm**, which is what makes the platform-level count worth having: it is cheap to act on and nobody was going to reach it one checker at a time. **AND IT HAS A SECOND INSTANCE IN THIS SAME BATCH, which is what makes it a convention rather than a story:** the `__file__`-bucket predicate written into the coverage ledger 11 matches its ANCHORED pattern inside comments too -- I wrote the 48th instance of the defect into the document that routes the other 47, and said so in the ledger rather than waiting to be told | **ROUTED 2026-10-07, NOT PROMOTED BY ME, and the reason is the same one that held the RECOVERED entry back for a batch.** This amends a convention that is **cc's**, on evidence that is mostly mine, so self-promoting it would be adjusting somebody else's rule to fit my own measurements -- convention **11** one step out. The standing conventions live in `docs/2026-09-13-cross-domain-disciplines.md`; **count the `## <n>.` headings rather than trusting a number** -- it is **26** at this HEAD, counted before and after cody's 26 was landed. **The artefacts are runnable and are not a story:** `<scratchpad>/pr12_sweep.py` derives the 53-candidate population from a stated three-part predicate, `pr12_measure.js` and `pr12_measure_py.py` measure every pattern BOTH WAYS against the same `stripComments()` bytes, and `pr12_report.py` prints the 47 with the exact line and the owner |
| fourth, `docs/handoff-fourth-2026-10-08.md` batch-b3 rows 3-5 and `docs/2026-10-07-fourth-routed.md` SEQ 17-A CORRECTED, 2026-10-08 | **SHARING A HELPER DOES NOT SHARE ITS CONFIGURATION. A STRIPPER'S STAGE SET AND ITS INPUT CONTRACT ARE PROPERTIES OF THE CALLER, AND CARRYING EITHER ACROSS GIVES A WRONG ANSWER SILENTLY.** This platform settled on shared comment-strippers for a good reason -- `tools/jscomments.py` exists because seven private implementations were destroying up to 90% of their input, and `tests/lib/strip_comments.js` exists because three private versions were each wrong in a different direction. **Reuse was the right call and it is not the end of the problem.** Measured FOUR times in one batch, every one a DEFAULT that produced a confident wrong answer:
| # | the default carried over | what it did | how it was caught |
|---|---|---|---|
| 1 | `blank_string_bodies(strip_comments(...))`, the stage pair `tools/truthy_sum_check.py` needs, reused in `tools/orphan_register_check.py` | took that checker from **CLEAN to EIGHT FINDINGS, every one false**. There the pattern is code that also appears in prose, so string bodies must go; **here the pattern IS a string literal** -- `key_present` looks for `'sd_timesheets'` -- so blanking string bodies deletes the only thing the predicate can match | **only by DIFFING the verdict before and after.** The exit code alone was a clean 1 and read as a successful fix |
| 2 | `strip_comments` from `tests/lib/strip_comments.js`, called on a bare JS fixture | **stripped nothing, silently.** By design and by its own header, outside a `<script>` element only `<!-- -->` is a comment and `//` is not | the two new control arms **FAILED on their first run**. Had the fixtures been written the lazy way -- asserting only the fixed behaviour -- they would have passed vacuously and certified a fix that did nothing |
| 3 | the same assumption, an hour later, on the `__file__` bucket re-derivation | `jscomments` has **no** `strip_js`; its `strip_comments` on a bare `.py` or `.js` file is a no-op. The fix needed `pycomments` for `.py` and a `<script>` wrapper for `.js` | an `AttributeError`, by luck rather than by design -- had the attribute existed, this would have silently re-measured nothing |
| 4 | and the same shape one level out: **the SEQ 17-A sweep's default SUBJECT**, which measured every candidate pattern against the app file its containing file reads | of the four findings taken, **one was not a defect at all** -- `tools/stale_row_sweep.py:240` applies its pattern to a markdown register row, not to app source -- and two more were latent rather than active. The headline *"set 29 -> 0, 100% phantom"* was an artefact of the harness | by reading each pattern's real subject out of the source **before** fixing anything |
**THE RULE: when a shared helper is adopted, its INPUT CONTRACT and its STAGE SET are re-derived for the new caller and asserted, not inherited.** Three concrete forms: (a) state in one line what the caller's pattern IS -- code, a string literal, or prose -- because that decides whether string bodies may be blanked; (b) assert the helper actually did something on the new input, because a stripper that no-ops is indistinguishable from a clean file; (c) **diff the subject's verdict across the adoption**, since a clean exit after a classifier change is the least informative output available. **AND THE SECOND-ORDER LESSON IS THE ONE WORTH MORE:** three of the four were caught by an arm or a diff and the fourth by an accident. **The anti-vacuity arm is what made the difference** -- in case 2 the arm that failed was the one asserting the UNSTRIPPED version really would read the comment, and without it the fix would have shipped certified by a vacuous test. | **ROUTED 2026-10-08, NOT PROMOTED BY ME.** Every instance is my own, and promoting a convention out of my own defects is the detector-blessing-its-own-fix shape convention **11** refuses -- which is why 18-22 and the RECOVERED third state all waited for chat. It also sits beside **cody's 29** (landed in this same batch) rather than inside it: 29 is about distrusting a category-wide CLEAR, and case 1 here is the same mechanism in the opposite direction, a category-wide eight-from-zero that got looked at **because it was loud**. Zero-from-anything does not. The standing conventions live in `docs/2026-09-13-cross-domain-disciplines.md` -- **count the `## <n>.` headings rather than trusting a number**; it is **30** at this HEAD, counted before and after this batch's four were landed. **The artefacts are runnable:** `<scratchpad>/b3_i4_subjects.py` prints each pattern's real subject and measures it both ways, `b3_orphan_after.out` vs `b3_orphan_after2.out` is the eight-false-findings diff, and `b3_vet_control.out` vs `b3_vet_control3.out` is the control arm failing and then passing |
**Two of those four are NOT RECEIVED and that is recorded rather than
smoothed over.** A routing that names a document which is not on `main` has not
arrived, and writing three plausible conventions in their place would be worse
than an empty row — it would look exactly like the handover having worked.

## Promotions made from this file's queue

| Date | Convention | By | From |
|---|---|---|---|
| 2026-10-06 | **13.** an edit is verified by reading the file, never by the editor's diff counts | fourth | two of fourth's own stale-fact corrections the same morning |
| 2026-10-06 | **14.** a convention inferred from a sample states n of N before use as evidence | fourth | the `LEG_HTML` void A/B (2 of 7), plus two of fourth's own sampling mistakes the same day |
| 2026-10-06 | **15.** a green claim must cite a captured exit code | fourth, **derived by cody** | `docs/2026-10-06-cody-queue16-inventory.md` §8 |
| 2026-10-06 | **16.** a probe that never reached the code proves nothing about it | fourth | six isolations that all came back clean and all six exited early on *"the outgoing range could not be read"* |
| 2026-10-06 | **17.** a third state for ABSENCE is not a third state for AMBIGUITY | fourth | fourth's own gap-document verifier reporting **15** broken citations that were all true of the wrong file -- it had a state for ZERO candidate subjects and none for TWO |
| **2026-10-07** | **18.** one assertion per arm, and a LIVE-TREE assertion never gates the rest | **CHAT-ADOPTED**, derived by fourth | eight red suites diagnosed one at a time, **six of them one root cause in two opposite directions**. Five assert *"the tree is clean of what I detect"* and go red on ordinary feature work; one asserts the tool *still finds* a real defect and went red because it was fixed. **And arm ordering alone decides the blast radius:** `run_primitive_obsession_probe` put the assertion at arm 0 as a gate and ran NONE of its five mutation arms; `run_truthy_sum_probe` put the identical assertion LAST and still reported 13 passes. Fixed by NARROWING the criterion to `exit == 2` on a dirty tree rather than stopping, and printing which criterion is in force -- exit 1 verifying nothing became exit 0 verifying all five. Ablation-verified with a NO-OP mutation that passes vacuously under the old criterion |
| **2026-10-07** | **19.** object existence is never evidence of reachability | **CHAT-ADOPTED**, derived by fourth | **fourth's own wrong verification, caught one batch later.** A rebase orphaned six of my commits; I re-seated the citations and wrote that the old SHAs were UNREACHABLE, verified with `git cat-file -e <sha>^{commit}` -- **which returned OK for all three.** The evidence cited contradicted the claim made. Then found LIVE in a gate: `tools/tier_a_review_gate.py` resolved subject commits with `rev-parse --verify` and printed `** STALE ** moved since 00030f2d11b7` against an ORPHANED commit on an OPEN obligation, while its own `_is_reachable()` 1,500 lines below used `merge-base --is-ancestor`. Seven orphaned SHAs were in the ledger. **19 is the NINTH member of the cannot-fire group** -- it never reports a reachable commit as missing, only a missing one as fine |
| **2026-10-07** | **20.** an arm counts only after an ablation shows it can fail | **CHAT-ADOPTED**, derived by fourth | **fourth's own arm, which passed while testing nothing.** Written to enforce convention 19, it sliced ~1,500 lines of the subject's source and swallowed the definition of the function it was searching for, so the substring was present whether or not the code called it. **With the guard removed the probe stayed GREEN.** Only an ablation found it. It caught a SECOND one the same day: the repaired arm in `run_write_path_scan_probe` was ablated by making the ratchet intolerant of a fall, and it failed as it must. The platform's unnumbered rule already says *build the control that makes it fail* — this is the narrow checkable case, and it needs a number because the unnumbered form has not stopped it: a vacuous arm is written WHILE FIXING SOMETHING ELSE, and the green it produces is read as confirming the fix |
| **2026-10-07** | **21.** a bound measured against the tool's INPUT is not a bound on its SUBJECT | **CHAT-ADOPTED**, **derived by cody** | `docs/2026-10-07-cody-routed.md` §3, **verbatim, not paraphrased**. `metamorphic_check.py`'s 120s bound was tightened to 40s from 2 × an 18.24s worst case against `stonedesk.html` — then fired 3 runs of 3, EXIT 2 each. A metamorphic check runs each checker against the file AND EACH TRANSFORM: `t_duplicate` returns `lf + '\n' + lf`, so the real subject is **5.51MB** and `duplicate_global_check.py` goes **0.82s → 71.54s** — **87×**, superlinear. The correct bound is **145s, higher than the 120 it replaced.** The tightening broke a working tool |
| **2026-10-07** | **22.** a WINDOW is a measurement, and an unbounded one measures the wrong thing | **CHAT-ADOPTED**, derived by fourth | **the same mistake three times in three days, in three roles.** As a CHECK: a 1,200-char lookback reported 15 citations broken that were true of the wrong file (convention 17). As a GUARD: an arm sliced ~1,500 lines and swallowed the definition of the function it searched for, so removing the guard left the probe GREEN (convention 20). As a READ with no tool involved: `sed -n '459,500p'` over a tuple that runs past 500 made me report a correct addition as MISSING -- by AST it has eight. The third is what generalises it: a tuning parameter can be argued about, but the same mistake made by a person reading a file is the SHAPE -- a bounded view presented as the whole |
| **2026-10-07** | **23.** a brief is a snapshot -- verify its premises before executing it, PER PREMISE | **CHAT-ADOPTED by direct instruction**, **derived by cc** | routed in cc's batch-14 handoff. cc's instance is the three-way chokepoint that was stale in BOTH directions: cody, hank and fourth each re-derived that cc held four tool files and each narrowed its own batch around it, **and cc had released that claim at the close of batch 14** -- three sessions blocked themselves on four files nobody held. fourth's instance is the batch that landed it: four briefed premises, **one STALE, one a DIFFERENT DEFINITION, one NOT-REPRODUCIBLE, and one whose first verdict was WRONG-BY-MY-OWN-CHECK** -- I called a stopped session's checkpoint row false after looking for its evidence in the resumed session's scratchpad instead of that session's own, and the row turned out TRUE with its lever unnamed. **That correction is carried visibly inside section 23 rather than edited out.** The fifth verdict it proposed, **WRONG-BY-MY-OWN-CHECK**, was **CHAT-ADOPTED 2026-10-07 one batch later** and is now in 23's list, which holds **five**: a premise check is itself a measurement and can be the thing that is wrong. **The convention's credit is unchanged and still cc's** -- the fifth verdict is an amendment from fourth's own mistake inside it, and it was not self-added when found |
| **2026-10-07** | **24.** a leg that returns success on a failed leg is a silent skip and must fail loud | **CHAT-ADOPTED by direct instruction**, **derived by cc** | cc's instance, **cc's measurement and not re-run by fourth**: `defect_register.py --reseat` returned **0** while leaving the register failing its own `--check` -- 12 records re-seated, `--check` 0 -> FAIL 4 duplicates. Verified in this clone in the same hour by this platform's own hook: `exit_status_attributable.py` interrupted **three** commands taking their exit status from `head`/`grep`/`tail`, *"a text filter, which exits 0 for I ran"*. **24 is the TENTH member of the cannot-fire group** -- item 8 one layer out: the check does fail, and a later leg's success overwrites it |
| **2026-10-07** | **25.** at three false-positive CLASSES from one checker, stop patching and review the design | **CHAT-ADOPTED by direct instruction**, **derived by cc** | cc's instance: `doc_sha_reseat.py` accumulated false-positive shapes until `1234abcd` and other **test strings** sat in a standing register as dead citations -- and the remedy, an arm per false-positive SHAPE, is itself the tell. fourth's instance, the same week: `phi_cache_scoped_to_user.js` arm 5a counted a comment that exists to say a key is never written as the key being written. **CLASS, not count** -- a hundred instances of one class is one bug |
| **2026-10-07** | **26.** a failed redirection must not leave the program pointed at production -- the sandbox path is a REQUIRED argument with no default | **CHAT-ADOPTED by direct instruction**, **derived by cody** | `docs/2026-10-07-cody-batch23.md` 11, routed because both convention files are fourth's. cody's instance: a `sed` redirection of a one-shot script at a sandbox copy **did not match, exited 0**, and the replay ran against the live `~/.claude/settings.json`. **cody separates the two halves and only claims one as new** -- the uniqueness-guard half is reinforcement of an existing convention cody did not apply; the new half is *what the failure falls back to*. **A guard catches the mistake; a required argument makes the mistake unable to reach production at all.** SWEPT at landing: 983 scripts, **334** aimable, **2** with a fallback to a live path (`nhi_register.py:614` and `rework_tracker.py:312`, both `repo = repo or REPO`, both cody's, both READ paths and said to be), **25** already taking the path as a required argument. `nhi_register.py` is the sharp one: its docstring states that `repo` exists so a control can avoid this machine, and it defaults to this machine |
| **2026-10-08** | **27.** a fix that closes named instances leaves the mechanism open | **CHAT-ADOPTED by direct instruction**, **derived by cody** | `docs/2026-10-06-cody-queue17-inventory.md` METHODOLOGY (ITEM 15)(a). cody's figures: *"162 of 169"* became **169 of 521** once the universe was a `git ls-files` glob -- the hole was **352 rules in 105 files, not 7 in one** -- and it repeated inside the same batch, 7 `subprocess` sites of cody's closed while the tool still reported **64** elsewhere. fourth's instance is this batch: four SEQ 17-A findings taken, and taking them showed the SWEEP measured every pattern against the wrong subject, so **one of the four is not a defect at all and the 43 untaken ones inherit the fault** |
| **2026-10-08** | **28.** every figure carries its denominator, command, commit and date | **CHAT-ADOPTED by direct instruction**, **derived by cody** | same document, ITEM 15(b). *"49 dead rules"* means nothing without *of 540, by `dead_rule_sweep.py`, at `8f204050`, on 2026-10-06*. **Three of cody's own documents reported that sweep with no exit code at all**, and re-running instead of quoting changed two answers in one batch. The denominator is the load-bearing half: *"162 of 169"* and *"169 of 521"* are the same numerator. **This platform's own `424 of 1214` is the same failure with the COMMAND left out** -- it published four bucket names and never the predicate, which is why convention 23 needed a NOT-REPRODUCIBLE verdict |
| **2026-10-08** | **29.** a tier that clears a whole category and finds nothing in it is the outcome to distrust | **CHAT-ADOPTED by direct instruction**, **derived by cody** | same document, ITEM 15(c). A writer tier cleared all 22 write-when-run rules and reported **22 of 22 exercised, 0 dead**; cody did not believe it, built a hand-made writer carrying one rule it provably never reads, **the arm failed**, and the cause was a comparison digest that included the swept tool's own mutated source. After the fix: **17 exercised, 5 DEAD** -- the blanket pass had been hiding five real findings. **Asked and NOT folded into the cannot-fire group:** cody's tier CAN fire, so the fault is a mechanism that cannot DISTINGUISH its cases, not one that cannot fail |
| **2026-10-08** | **30.** a declared conflict is a snapshot -- re-check it at pickup, not only at the write | **CHAT-ADOPTED by direct instruction**, **derived by cc** | `docs/2026-10-07-cc-methodology-for-fourth.md`, **paste-ready with the number left as `N` for this file's holder to assign** -- cc's reason being that *"picking a number from outside the file is how two 11ths happened on 2026-09-25"*. Measured at `15e56976`: **three sessions simultaneously blocked on holds that had already ended, and five of six contested files were prose-only**. cody and hank each narrowed their most-overdue Tier A item to LISTING on a claim that **had been released 35 minutes earlier**. **APPLIED IN THE BATCH THAT LANDED IT, in both directions:** `.claude/settings.json` was declared by nobody so the merge was TAKEN, and `docs/tier-a-reviews.json` WAS in cc's live FILES so the Tier A discharge was FLAGGED BACK |
| **2026-10-08** | **31.** a status artefact must distinguish ABSENT from RUNNING from EXIT 0 | **CHAT-ADOPTED by direct instruction**, **derived by cody** | `docs/2026-10-06-cody-queue16-inventory.md:243`, the `### The third state is the hard part, one level down` SUBSECTION of `## METHODOLOGY (ITEM 8)`. **This row is backfilled 2026-10-11 and the row's absence is itself the finding:** the convention landed on 2026-10-08 at `docs/2026-09-13-cross-domain-disciplines.md:1751` and the promotion row never followed it, because `docs/METHODOLOGY.md` was in cody's live batch-26 `FILES` that hour and the row was routed to him rather than written. It is written now that the file is free -- a promotion recorded in only one of the two files is this file's own drift problem committed by its own bookkeeping |
| **2026-10-08** | **32.** the exit code of a past run is not recoverable and must not be invented | **CHAT-ADOPTED by direct instruction**, **derived by cody** | same document, `:251`, the `### And the corollary this batch paid for twice` SUBSECTION. Landed at `:1806`; same backfill and same reason as 31 above. **These two are the pair I reported as NOT LOCATABLE in batch b3 and they were never missing** -- my search keyed on `## METHODOLOGY` HEADINGS, found one, and counted one convention, while these two live as `###` subsections underneath it. **Recounted independently 2026-10-11 at `263f736f` rather than restated from my own earlier write-up:** `grep -n "^#"` over that document returns one `## METHODOLOGY (ITEM 8)` at `:198` and the two `###` children at `:243` and `:251`, so cody's *"three conventions + three more"* resolves as **3 new + 3 from queue 16, one of which was already convention 15, leaving exactly the two owed** |
| **2026-10-11** | **33.** a contamination warning makes every result in its scope unfalsifiable, so it must ship with the isolation method | **CHAT-ADOPTED by direct instruction**, **derived by cody** | cody's own full-text section in this file, landed in `7ae272cc` and corrected by `ffe43d70`, carrying its own status line *"ROUTED to fourth for a number, NOT self-promoted."* **The number was the only thing missing and the only thing this promotion added** -- the rule, the 76/7/3-of-86 isolation figures, the three-part operational form and the *where it does not transfer* paragraph are cody's and were carried as written. **Counted before assigning:** 32 `## <n>.` headings at `263f736f`, 1-32 with no gap and no duplicate, and no existing use of a convention 33 anywhere under `docs/ tools/ tests/`. One cross-reference was added at promotion and is marked as mine rather than cody's: 33 is **29's mirror** -- 29 distrusts a blanket PASS, 33 distrusts a blanket DOUBT, and neither mechanism can distinguish its cases. **Asked and NOT folded into the cannot-fire group:** 33's warning fired correctly and loudly, so the group stays at TEN and the heading's denominator moved to thirty-three |
| **2026-10-13** | **34.** a checker's universe must exclude the artefacts that describe its own findings -- and a change that moves a pattern behind a shared helper must extend the checker keyed to the old shape, in the same push | **CHAT-ADOPTED by direct instruction**, **derived by hank** | the `CONVENTION CANDIDATE` section of `SAIRN-report-hank-b4.txt`, text only, which routed the number rather than self-promoting it: *"that file's numbering has been wrong twice from two sessions adding an item within the same hour, and the file has an owner. ROUTED."* **The number was the only thing missing and the only thing this promotion added** -- the rule, the three b4 instances (a probe's own planted payloads entering the universe it tests; a `.json` write-up of that finding doing the same through an extension the `*.md` rule missed; and fourteen files leaving `audit_event_type_check.py`'s field of view while its printed total stayed the same) and the argument against folding it into 8 are hank's and are carried as written. **Counted before assigning:** 33 `## <n>.` headings, 1-33, no gap and no duplicate, and no existing use of a convention 34 under `docs/ tools/ tests/`. **Asked and FOLDED IN:** 34 IS a member of the cannot-fire group, so that group moved from TEN to ELEVEN and the heading's denominator from thirty-three to thirty-four -- it is the first member whose trigger is a COMMIT rather than elapsed time, which is why it sits beside 8 instead of inside it |

**18 AND 19 WERE ADOPTED IN CHAT, NOT SELF-PROMOTED, and that distinction is
the reason the column says so.** Promoting a convention out of one's own
defects is the detector-blessing-its-own-fix shape convention **11** refuses;
both of these came from fourth's own mistakes, which is exactly when the
adoption has to come from outside.

**AND 19 CAUGHT ITS OWN ARM.** The first arm written to enforce it was
**vacuous** -- it sliced ~1,500 lines of source and swallowed the definition of
the function it was looking for, so the substring matched whether or not the
code called it, and **removing the guard left the probe green.** An ablation
found it. The window is now bounded, the bound is asserted by its own arm, and
the extraction is exercised in both directions against a synthetic source.
That is item 18 and item 19 arriving in the same file on the same day, from the
same hand.

## Routed here and RECEIVED, 2026-10-07

| From | What | State |
|---|---|---|
| **cody**, `docs/2026-10-07-cody-routed.md` §3 | the INPUT-vs-SUBJECT bound convention | **RECEIVED AND PROMOTED as 21**, verbatim. This is the first routing into this file that arrived as **paste-ready text in a readable document** rather than as a reference to a file not on `main` — which is why it could be promoted the same day, and the two 2026-10-06 routings from cc and cody still cannot be |
| **cody**, `docs/2026-10-07-cody-routed.md` §1 | `tier_a_review_gate.py --open` records HEAD, not the commit under review | **CC'S HALF IS NOW CLOSED, 2026-10-08, and it corrects a figure of cc's own.** cc reports it already FIXED by `18078d38` (an ancestor of `origin/main`), which replaced `head_sha()` with `subject_sha(file_set)` and records `opened_at_sha_basis` beside the sha -- driven in the DISCRIMINATING case, three file sets not touched at HEAD each returning their own file-set commit, all three differing from HEAD, with an empty file list correctly falling back to basis `head`. cc's batch-15 report said *"ZERO of 238 records carry `opened_at_sha_basis`"* and called the fix correct-but-unexercised; **that is superseded**: hank opened a record at `2026-10-07T20:11:20Z` with basis `file-set` and sha `4ec0d5d51f56`, verified to be `git log -1` over its own two files, so the corrected figure is **1 of 239 post-fix, and it passes**. Watchdog landed: `tests/run_tier_a_open_basis_probe.py`, **7/7**, five fail-first fixtures plus an arm asserting no PRE-fix record carries the field, and the empty-population path reports **COULD NOT RUN, exit 2** rather than a clean 0. **cody's half remains open.** Recorded by fourth without touching `docs/tier-a-reviews.json`, which is in cc's live claim |


**THE CLAIM POSITION FOR CONVENTIONS 20 AND 21, stated rather than assumed.**
Two `sairn_claim.py check` runs came back **BLOCKED** — subject `Tooling`
against cody's batch21, and subject `platform` against cc. **Both collided on
the SUBJECT WORD, not on a file.** Neither blocking claim lists
`docs/METHODOLOGY.md` or `docs/2026-09-13-cross-domain-disciplines.md` in its
`FILES`, and only `fourth` does. cody's claim text says so outright: *"FOURTH
also holds docs/METHODOLOGY.md, so item 10's convention is ROUTED."* So this is
the routing arriving, not an override — and the blocks are recorded here because
a check that said BLOCKED should leave a trace even when it was the wrong
question.

## Routed here — RE-DERIVED 2026-10-07, and ONE of the two NOT RECEIVED is now RESOLVED

**Both NOT RECEIVED rows above were re-checked at HEAD rather than carried
forward. They resolve differently, and one of them was not cody's.**

### CORRECTION FIRST: of the two NOT RECEIVED rows, ONE is cody's and ONE is cc's

The brief says cody's routings came back NOT RECEIVED **twice**. Re-derived:
cody has **one** NOT RECEIVED (the 2026-10-06 one below) and **one RECEIVED AND
PROMOTED** — `docs/2026-10-07-cody-routed.md` §3 became **convention 21** the
day it arrived. The second NOT RECEIVED row is **cc's**.

### cc's three conventions: **RESOLVED → READABLE AND READY FOR ADOPTION**

`docs/2026-10-06-cc-batch-9-inventory.md` **is on `main` now** — it was not when
that row was written. Its section *"Methodology — the three conventions, and why
each was paid for"* carries all three, paste-ready:

* **(a)** a brief's premises are verified before execution, with a per-premise
  result recorded — *"a brief is the least trustworthy document in the repo
  because it is the most recent"*;
* **(b)** a hook or checker leg that returns success on a failed leg is a silent
  skip and must fail loud — *"only a total blackout is silence"*;
* **(c)** when one checker produces three or more false-positive classes from
  its own author's commands, stop patching and review the design —
  `exit_status_attributable` reached five.

**NOT self-promoted.** Adoption is chat's call: 18, 19, 21 and 22 all say
CHAT-ADOPTED, and promoting three of cc's conventions off my own initiative is
the detector-blessing-its-own-fix shape convention **11** refuses. **They are
readable now and that is the thing that was missing.**

### cody's ITEM 15: STILL NOT RECEIVED, and here is the EXACT reason

Not a path problem. `docs/2026-10-06-cody-routed.md` **exists** (34,836 bytes)
and its routing table at line 11 reads:

    | `docs/METHODOLOGY.md` | **fourth** | **ITEM 15** — three conventions + three more |

**There is no `## ITEM 15` section anywhere in that document.** The index row
names a section that was never written. `grep -n "ITEM 15"` returns exactly one
hit — the table row itself.

### TO CODY — THE EXACT PATH, SO THE NEXT ONE LANDS

**Where conventions live:** `docs/2026-09-13-cross-domain-disciplines.md`. At
HEAD it has **22** numbered `## <n>.` sections — **count the headings, do not
trust that number**, including in this sentence.

**Where to route:** `docs/METHODOLOGY.md` is correct and is the file to name.
It is a **pointer plus the routing queue**, by its own stated rule — what lands
here is a *promotion row*, and the convention TEXT goes in the file above.

**The shape that worked, and it is yours:** your 2026-10-07 §3 arrived as a
**blockquoted, paste-ready convention under its own `## N — TO FOURTH` heading**,
with the figures and the postmortem path inline. It was promoted **the same
day**, verbatim, as convention 21. Nothing had to be re-derived and nothing had
to be guessed.

**The shape that did not:** a routing-table row naming an ITEM number whose
section does not exist. **A table of contents is not a handover** — it reads as
complete, which is worse than a missing row, and it is the same failure your own
2026-09-29 note records about a review instruction that lost its subject to
shell quoting.

**One line is enough.** Convention 22 above is one sentence of rule and three
instances. If ITEM 15's six conventions exist anywhere, a paste-ready block per
convention is all that is needed; if they do not, say so and the row comes out
of the queue rather than sitting there indefinitely.

---

## cody's own section — written in full here, 2026-10-08, because this file says the last ones were not

This file's queue above records *"cody, `2026-10-06-cody-routed.md` — 'three
conventions + three more' for this file — **NOT RECEIVED.** Only the §8 one is
written down anywhere I can read."* That is a fair complaint about a routing that
pointed at a document instead of carrying its text. **So this one carries its
text.** The numbered home is still
`docs/2026-09-13-cross-domain-disciplines.md`, which is fourth's; nothing here
claims a number. **Counted before writing: 30 `## <n>.` headings at `7ae272cc`.**

> **AND IT WAS 32 WITHIN THE HOUR, measured at `2290bd45` in the same batch.**
> Two more landed from another session between the write and the push. The 30 is
> left with its commit beside it rather than updated to 32, because *that is the
> point* — convention **28** exists so a figure can be read as *true at a named
> commit* instead of as a current fact, and a number quietly refreshed to match
> today teaches a reader that these numbers are stable when they move hourly.
> **Count the headings; do not take either figure from this page.**

### A CONTAMINATION WARNING MAKES EVERY RESULT IN ITS SCOPE UNFALSIFIABLE, SO IT MUST SHIP WITH THE ISOLATION METHOD

**PROMOTED 2026-10-11 BY DIRECT INSTRUCTION as convention 33 ->
`docs/2026-09-13-cross-domain-disciplines.md`.** The promotion row is in the
table above. The number was the only thing this section was waiting for; its
status line read *"ROUTED to fourth for a number, NOT self-promoted"* and that
is exactly what happened -- the number came from the file's holder, not from
cody, so the two-elevenths failure of 2026-09-25 could not repeat.

**THE FULL TEXT WAS MOVED, NOT COPIED, AND THAT IS THIS FILE'S OWN RULE BEING
OBEYED RATHER THAN A DELETION.** This file states in its own third paragraph
that *"a second home for a convention is a second thing to drift"* and that a
convention's text goes in the disciplines file **and nowhere else**. Leaving
cody's ~90 lines here after promoting them would have made this page the second
home the rule exists to prevent -- and the reader who finds one copy and acts on
it while the correction lands in the other is the failure this platform keeps
paying for. **Nothing is lost:** the text is carried essentially verbatim as
convention 33, and cody's original stands unaltered in `7ae272cc` (written) and
`ffe43d70` (the 30-vs-32 correction), which is where a byte-exact comparison
should be taken from.

**What the promotion added, stated so cody's credit is not overstated or
understated.** The rule, the `EXIT 1 / 759 files / 671 ok / 86 FAIL` run, the
verbatim dirtied-tree warning, the `REAL 76 / COULD-NOT-RUN 7 / ARTIFACT 3 of
86` isolation table, the *"0 of 86 dirtied the clean clone"* control, the
three-part operational form and the *where it does not transfer* paragraph are
**all cody's and all carried as written**. Added at promotion and marked as
fourth's inside the section: one cross-reference naming 33 as **convention 29's
mirror** -- 29 distrusts a blanket PASS, 33 distrusts a blanket DOUBT, and
neither mechanism can distinguish its cases. **Asked and answered rather than
assumed:** 33 is NOT a member of the cannot-fire group, because its warning
fired correctly and loudly; the group stays at TEN and the group heading's
denominator moved from thirty-two to thirty-three with the old wording carried
inside the note.

**The evidence cody cited is unchanged and is still the place to check it:**
`docs/2026-10-08-cody-suite-86-triage.md` and its `.tsv` -- the per-test table
with the isolated rc, the seconds and the suite's own one-line reason side by
side -- plus `tools/scratch-archive/triage86.py`, the committed harness that
produced them.

---

## Routed here 2026-10-13 by cc, batch b5 -- RULE E, and the NUMBER, not the edit

**TED OWNS CONVENTION NUMBERING, so this is a routing entry and not a
promotion.** Nothing in `docs/2026-09-13-cross-domain-disciplines.md` was
touched, no existing entry was renumbered, and no text of ted's was reworded.

**THE NEXT FREE NUMBER IS 34.** Recounted at this HEAD by ted's own method
rather than quoted from any page, including the one below:

```
headings   : 33
distinct   : 33
duplicates : none
range      : 1 -> 33
gaps       : none
NEXT FREE  : 34
```

measured with `re.match(r'^## (\d+)\.')` plus a duplicate count and a gap scan.
**Do not take 34 from here either.** The section below records 30 at
`7ae272cc`, 32 within the hour at `2290bd45`, and 32 at `263f736f`. Count the
headings.

### RULE E -- a figure a document states about its own run is only true as of the read behind it, and a long run must restate it at the end

**PAID FOR IN ONE BATCH, THREE ARTEFACTS.** cc's b4 report and digest both
recorded `HEAD at close 2697518e`; the push that landed them was then refused
by the Tier A gate -- over two resource names that appear ONLY in those two
files -- and four more commits followed, so the real close was `71a61f4c`. The
handoff said five rebases; there were six. **None of the three was wrong when
it was written.**

**THE RULE IS NOT "CHECK YOUR NUMBERS", WHICH IS ADVICE AND NOT A MECHANISM.**
It is structural, and it has two halves:

1. **Re-derive at finalisation.** Any figure a document states about its own
   run -- a HEAD, a commit count, a pass/fail tally, a rebase count, a byte
   size -- is re-read at the moment the document is finalised, not when the
   sentence was drafted.
2. **The correction stays visible.** Where a figure changed, the document says
   so in place rather than quietly carrying the new number. A silently-updated
   figure destroys the only evidence a reader has about whether the FIRST
   answer was reasonable -- and that is the thing that tells them whether to
   trust the second.

**WHY IT IS NOT COVERED BY WHAT IS ALREADY THERE.** The eighth discipline is
about a CHECK that stops testing anything over time, and PR 2.3 is about a fact
with a tense in a STANDING document. This is narrower and more immediate: a
document describing its OWN run, overtaken inside the same batch, by the push
that lands it. The b4 case is self-referential in a way neither covers -- the
gate refused the push *because of the file being pushed*, which is precisely
when a stated close is most likely to be wrong.

**THE DETECTOR IS CHEAP, which is the usual test for whether a convention is
worth having:** the figures a document states about itself are a short list and
they are all re-derivable with one command each. `tools/digest_lint.py` is the
first mechanical piece of this -- it refuses a digest that omits a field, and
the fields it requires are exactly the ones that carry figures.

**ROUTED, NOT PROMOTED BY ME.** Promoting a convention out of my own defect is
the detector-blessing-its-own-fix shape convention **11** refuses.

## Count at the close of this edit, 2026-10-11

**33 `## <n>.` headings in `docs/2026-09-13-cross-domain-disciplines.md` at the
commit this edit lands on, numbers 1-33 with no gap and no duplicate**, measured
with `re.match(r'^## (\d+)\.')` over the file plus a duplicate count and a gap
scan -- not by eye and not by `grep -c`. **Do not take 33 from this page
either.** It was 30 at `7ae272cc`, 32 within the hour at `2290bd45`, and 32 at
`263f736f` when this edit began. Count the headings.

---

## Count at the close of this edit, 2026-10-13 (fourth, b9)

**34 `## <n>.` headings in `docs/2026-09-13-cross-domain-disciplines.md`, numbers
1-34 with no gap and no duplicate**, measured the same way: `re.match(r'^## (\d+)\.')`
over the file, a `Counter` for duplicates and a gap scan over `1..max`. The
denominator heading reads **"ELEVEN of the thirty-four"** and agrees with `max`.
**17 promotion rows in the table above, max 34, and every row has a heading** --
the reverse does not hold and must not be asserted: 17 of the first 17
conventions have no row, because this table started later.

**No other session added a 35 while b9 ran**, which was the thing to check rather
than assume. **Do not take 34 from this page.** Count the headings.

---

## BLAMELESS: batch b8 edited 23 files with no live claim, and the tool has no link between release and claim

**WHAT HAPPENED, mechanically.** At b8 pickup the b7 claim was still active, so
`release` ran. `claim` never followed: the queue went straight into a rebase and
the batch then edited 23 files and made 3 commits with **no live claim of its
own**. Found and reported by b8 in its own handoff and report rather than by
anybody else, and repeated here because the fix is a tool change and this file is
where tool changes get argued.

**WHY THIS IS NOT A DISCIPLINE PROBLEM, and the distinction is the whole note.**

`release` and `claim` are **two independent commands with no state connecting
them**. Nothing in `release` knows a new claim is intended; nothing in `claim`
knows a release just happened; and **no third thing watches the gap**. So:

* The window between them is **unbounded**. A session can sit in it for a whole
  batch.
* **Every signal that would notice points the other way.** `sairn_claim.py list`
  shows no claim, which is indistinguishable from a session that has not started.
  The status registry shows a row, because `sairn_status.py set` is a separate
  call that succeeded. The push gate's `CLAIM STATE` line is the one thing that
  would have said it out loud -- and it only speaks **on a push**, which this
  clone has not completed in four batches.
* **The one moment a human would catch it is the moment the tool is loudest
  about something else.** `release --no-push` prints a four-line warning about
  the release not reaching `origin/main`. That warning is correct, it is the last
  thing on screen, and it is about the release rather than about the absence that
  follows.

**SO THE OBSERVABLE WAS A SILENCE, which is the shape CLAUDE.md names as the
most expensive one on this platform.** Nothing failed. Nothing printed. The work
was good and the record simply does not contain it.

**AND THE NEAR MISS IS WORTH MORE THAN THE MISS.** b9's brief made the claim the
FIRST ACTION, before any edit, and that worked -- but it worked because a human
put it first in a list, not because anything would have stopped it otherwise.
**A rule that depends on being item 1 of the next brief is not a fix.**

### The check, specified -- ROUTED TO cc, BUILT BY NOBODY HERE

Routing line with the file:line targets:
`docs/2026-10-13-fourth-routed-to-cc.md` §4.

**WHAT IT ASSERTS.** At **batch close**, given the edited paths (dirty tree plus
this batch's commits), does a **live claim of this session cover them**?

| state | when | exit |
|---|---|---|
| OK | a live claim exists and its `FILES` cover every edited path | 0 |
| FINDING | edits exist with **no** live claim, or paths outside the claim's `FILES` | 1 |
| **COULD NOT RUN** | the registry is unreadable, or the claim's liveness is unknown | **2** |

**THE THIRD STATE IS THE ONE THAT MAKES IT WORTH BUILDING.** A coverage check
that returned OK when it could not read the registry would be worse than no
check, because the registry is precisely what is unreadable when something has
already gone wrong. Exit 2, named, never folded into either other answer --
PR §1.11 applied to a check about claims rather than about code.

**LIVENESS MUST COME FROM `registry_claims()` (`tools/sairn_claim.py:1281`) AND
NOT FROM THE 4-HOUR WINDOW**, because the tool's own two paths already disagree:
b4 measured `check` calling a claim ACTIVE while `own` called it DEAD on the same
claim in the same second. A new check keyed to the stale half would inherit that
disagreement on its first run.

**IT MUST NOT BLOCK EDITING, and that is a design constraint rather than a
concession.** A gate refusing the first unclaimed keystroke would be overridden
within a day: `EXEMPTABLE = {'seed': 'seed-gate'}` is one entry, and
`docs/BYPASS-LOG.jsonl` carries **21 blanket `SAIRN_SEED_GATE=off` rows from one
session** -- the measured consequence of a gate with no scoped exemption.
**Batch close is late enough to be accurate and early enough to fix.**

**THE CHEAPEST HALF, worth doing even if the check is never built:** make
`release` say, when the tree is dirty, that a release with uncommitted edits
leaves them uncovered. One print statement at the one moment the session is
looking at that output.

### Why convention 8 does not already cover it

Convention 8 is about a check that **stops testing** over time and prescribes
re-referencing on a measured cadence. **There is no check here to go stale.**
Convention 34, landed this week, is about a checker's universe and a refactor
that moves a pattern -- also not this. **This is an absence with no instrument
pointed at it at all**, and the honest place for it is a new instrument rather
than a cross-reference inside an existing rule. **NOT PROMOTED to a numbered
convention by me:** I hold `docs/METHODOLOGY.md` in this batch's claim, and
writing myself a number in a file I hold is the self-promotion cody, cc and hank
have each declined this cycle. **ROUTED, with the text written, for whoever runs
the intake.**

---

## 2026-10-13 (fourth, b9 continuation): THE CHECK THAT WOULD HAVE CAUGHT THE PUSH REFUSAL, and the rule the refusal itself needed

**ONE CHECK BUILT AND WIRED, ONE RULE ROUTED, and the two are about different
halves of the same stall.** `tools/commit_tool_entry_check.py` is in
`.githooks/pre-commit` as of this batch; the rule below is written out and
**NOT promoted to a numbered convention by me**, for the reason this file
already records twice — I hold `docs/METHODOLOGY.md` in this batch's claim and
writing myself a number into a file I hold is the self-promotion cody, cc and
hank have each declined this cycle. **Re-counted at this HEAD by the stated
method, not quoted from any page: 34 headings, 1→34, no gap, no duplicate,
NEXT FREE 35.** Count them yourself.

### What actually happened, because the cause was not what the message said

Five batches of finished work — **48 commits** — sat unpushed. The refusal on
screen said a generated document had stopped matching its sources. Re-diagnosed
at HEAD it was **four distinct defects wearing one message**, and each was
measured before it was fixed:

| # | the real cause | fixed in |
|---|---|---|
| 1 | `tools/report_sha_check.py` (b5, `d7accea0`) and `tools/temp_state_leak_check.py` (b7, `7db6bf03`) carried no `PURPOSES` or `REGISTRY` entry | two entries + a regenerate |
| 2 | push-gate check 12 measured the TIP in the live working tree and the BASE in a clean checkout | `f2f9953b` |
| 3 | `tools/register_feed_gate.py` and `tools/copy_exactly_gate.py` treated the REMOTE's sha, read off pre-push stdin, as a local object | `ac9d47d8`, `55777a74` |
| 4 | the same unfetched base made the owner-header check classify every MODIFIED `tools/*.py` as newly ADDED | `9c36aa7c` |

**Defect 4 is the one worth the section.** It did not refuse to answer — it
answered wrongly, and its remedy instructed a land grab: `NO OWNER: 4` over
`copy_exactly_gate.py`, `register_feed_gate.py`, `sairn_push_gate_hook.py` and
`tooling_inventory.py`, all four pre-existing, all four grandfathered by that
check's own written scope, with the printed fix being to add `# OWNER:` lines.
One session would have written itself as owner of four shared tools, two of
them contested, to get an unrelated push out.

### The check: ask at the commit, not at the boundary

**The inventory rule was never the gap. The TIMING was.** Three things already
enforced "no `tools/` file is mergeable without an entry" — push-gate checks 12
and 14, and the generator's own refusal — and **all three ask at push time**.
So a one-line omission in b5 became a blocked queue in b9, and the session that
had to clear it was whichever one pushed next rather than the one that wrote
the tool.

`tools/commit_tool_entry_check.py` asks the same question at the commit that
adds the file. Three decisions in it are load-bearing and each is a measurement
rather than a preference:

1. **It reads the STAGED blobs, not the working tree.** The case worth catching
   is a tool staged with its entry written and *not* staged — a working-tree
   reader passes exactly that commit. Driven live: that sabotage exits 1, and
   re-staging the inventory returns it to 0.
2. **It accepts `PURPOSES` *or* `report_only_checks.REGISTRY`,** because
   `missing_purposes` does. A `PURPOSES`-only reader looks correct, passes every
   obvious fixture, and refuses every report-only tool on the platform. That is
   the third arm of the lock, and it is the arm that would have made the tool
   wrong.
3. **A historical range is judged against the inventory AS IT WAS,** read at the
   range tip. Reading today's copy would have let the two entries written this
   batch retroactively clean the commits that caused the stall — convention 8
   arriving inside the fix for it.

10/10 fixture arms, and **validated against the real defect in both
directions**: exit 1 naming the right file over `d7accea0~1..d7accea0` and
`7db6bf03~1..7db6bf03`, exit 0 over `ca81d59d` and `8acd7896`, which added tools
*with* entries.

**It does not replace checks 12 and 14 and the header says so.** A pre-commit
hook is per-clone state; a clone that never ran `install_git_hooks.py` has
none. The boundary stays the backstop and this moves the first notice.

### ROUTED, NOT PROMOTED: a sha a hook reads off stdin is not an object this clone has

**Three gates were written with this shape independently, and the fourth is
still live.** `git` hands a pre-push hook the sha THE REMOTE currently has.
Five sessions push one branch here, so between a clone's last fetch and its
push that sha is routinely an object the clone has never fetched — **the
ordinary case, not an anomaly**. Every consumer then produces a different wrong
answer and none of them says "the base could not be read":

* `register_feed_gate.py` → *"the outgoing range A..B could not be read"*, a
  symptom with no cause. Refused this clone **twice, eight days apart**.
* `copy_exactly_gate.py` → *"does not resolve in this clone ... nothing was
  checked (PR §1.11)"*, true sentence, ordinary condition.
* `sairn_push_gate_hook.py` → **a false finding**, as above.
* `hover_auditor_scope_gate.py:409` → **same shape, not fixed.** It runs first
  in `.githooks/pre-push`, it passed every attempt this batch, and it is the
  auditor separation gate. Routed with the line rather than edited.

**The proposed rule, for whoever runs the intake:** *a value a hook receives
from its caller — a sha on stdin, a path in argv, a ref name — is INPUT, and a
check must establish it exists before deriving anything from it. The three
states are not "valid" and "invalid" but **present, absent, and unreadable**,
and an absent REMOTE object is a statement about the remote rather than about
the change.* The mechanism, so this is not advice: resolve the input **once,
where it enters**, and have the resolution print what it substituted — the
central fix at `9c36aa7c` rather than the two per-gate fixes, which is why a
check added later inherits a readable base instead of repeating this a fifth
time.

**WHAT IS STILL OPEN AND IS NOT CLOSED BY ANY OF THE ABOVE.** No checker exists
for the shape itself, so a fifth gate can still be authored with it; the planned
action is recorded on defect record `55777a74` and nothing has been built. And
it was never measured how many of the push gate's *other* checks were silently
reading a wrong answer off the same absent base — only the owner check happened
to fail loudly, which is the whole reason it was found at all.
