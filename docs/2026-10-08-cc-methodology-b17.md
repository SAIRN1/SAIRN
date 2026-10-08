# cc — batch 17 (b3) methodology: what I would do differently, with the measurement behind each

**Written 2026-10-08 at HEAD `b0a128bc`.**

**PASTE-READY, NOT APPLIED.** `docs/METHODOLOGY.md` and
`docs/2026-09-13-cross-domain-disciplines.md` are both declared by **fourth**
under a live claim, re-checked at this HEAD. Nothing below is written into
either file by me. Each entry is drafted in the voice those files use so it can
be moved across without rewriting.

Five entries. Every one is a thing I did wrong in *this* batch, with the
command and the number that caught it — not a principle I agree with.

---

## A. A fix that corrects a key's SHAPE must be re-checked for its REFERENT

**Candidate for `docs/2026-09-13-cross-domain-disciplines.md` as a new numbered
convention.** Count the `## <n>.` headings in that file rather than trusting a
number from here.

> **A fix to an identifier can repair its FORM and leave it pointing at the
> wrong thing, and the repaired form makes the second defect harder to see.**
>
> `docs/scrutiny-flags.json` is keyed `(sha, path)`. On 2026-10-06 nine rows
> were found keyed `"main"` — the push gate had handed its prepush `tip`, which
> is a ref *name*. The fix resolved `tip` to a real sha and added a guard
> refusing a non-sha key outright. Both halves are correct and the bug was not
> fixed.
>
> The flags are computed over a diff of the whole push range, `base..tip`, and
> were then recorded under `tip`. On a multi-commit push that credits the **tip
> commit** with every checker edit anywhere in the push and leaves the commit
> that actually made the edit with no row at all. **Measured on a real push:**
> `bf174f30` carried rows naming `tests/run_audit_event_type_probe.py`,
> `tests/run_tool_usage_refusal_probe.py` and
> `tests/sd_data_write_attribution_three_apps.js`. It changes five `docs/`
> files and **none of those three**. The commit that really added the refusal
> probe, `320ddabe`, earlier in the same push, carried no row.
>
> `scrutiny_record`'s own docstring had said *"KEYED BY COMMIT, NOT BY PUSH
> ATTEMPT"* the whole time. It was not true, and the sha-shaped key made it
> read as though it were.
>
> **The check:** after fixing an identifier, ask *what does this now point at,
> and is there a commit/row/file where I can go look at it?* A key is only as
> good as the thing it resolves to. For a ledger keyed to a commit, the
> property to assert is **self-verifiability**: `git show <row.sha> -- <row.path>`
> must produce text, or the row is wrong whatever its shape.

---

## B. Re-run your own green at the HEAD you are reporting from

**Candidate for `docs/METHODOLOGY.md`.**

> **A green you have already reported is not evidence about the HEAD you are
> reporting it from.** It is evidence about the HEAD where it ran.
>
> `python tools/tool_owner_map.py --check` exited **0** at `7b82997b`, the
> commit where I added a field and reported the tool clean. The same command
> exited **1** at `785a8c99`, three of my own commits later. The whole diff was
> one row: `tools/va_rule_currency.py`'s `last_commit` moving from
> `1ae447cf0b5e` to `7b82997b0de7` — because `7b82997b` is where I edited that
> file.
>
> The map was correct and the check was correct. The **field** was wrong, and
> nothing except re-running the identical command at a later HEAD could have
> shown it. Had I only quoted the run that made me happy, a tool I own would
> have shipped a check that goes red on almost every commit, for a benign
> reason.
>
> **The check:** the verification sweep is not a formality at the end of a
> batch. Run every cited green again at final HEAD, each one alone, and compare
> the exit code to what you wrote down earlier. A pair that disagrees is the
> most valuable thing the sweep produces.

---

## C. A new field on a derived document is a new regeneration obligation — count the rows it can move

**Candidate for `docs/METHODOLOGY.md`, and it is the root cause under B.**

> `docs/tool-owner-map.json` is generated and has a `--check` mode asking *is
> this still true?* I added `last_commit` to every row with basis
> `UNRECORDED`. **There are 614 such rows.** So any commit touching any of 614
> files moved a row and made `--check` fail.
>
> I did not add a bug; I added a **maintenance obligation of 614 files wide**,
> and I did it without counting. A check that goes red for a benign reason is a
> check people learn to ignore, which costs more than the field was ever worth.
>
> **What distinguishes the field that stayed from the field that went:**
> `first_commit` — the commit that *introduced* the file — does not move unless
> history is rewritten, and it is the one that answers the question the basis
> poses. The basis is *nobody has recorded an owner*, so the only useful thing
> the row can offer is a routing target, and that is whoever introduced it.
> `last_commit` named the most recent toucher: not a routing target, and
> changing constantly. **Churn with no answer in it.**
>
> **The check:** before adding a field to a generated artifact that has a
> `--check`, ask *how many rows can this field move, and what moves it?* If the
> answer is "ordinary work on any of N files", the field has to earn N.
>
> **And prove the fix with an ablation, not a passing run.** Measured in an
> isolated worktree: fixed tool → `--check` exit 0; then a commit touching an
> `UNRECORDED` file → exit **0**; `last_commit` restored, same commit → exit
> **1**. The mutation counted its anchor before replacing, so the red is the
> field returning rather than a sabotage that silently missed.

---

## D. A warning written as a number becomes the thing it is warning about

**Candidate for `docs/2026-09-13-cross-domain-disciplines.md`, as a sharper
instance of the existing "nothing announces the day a check stops testing
anything".**

> `SELF_EXCLUDED` in `tools/cross_tenant_isolation_scope.py` carried this
> comment, written 2026-09-21:
>
> > *"BUT **FIVE** HAND-WRITTEN ENTRIES, ONE PER REVIEW, IS A LIST THAT GROWS
> > BY ONE EVERY TIME SOMEBODY REVIEWS THIS TOOL."*
>
> The warning was right. **The tuple reached eight.** The sentence objecting to
> a list that grows was itself stated as a number that then grew, and sat
> sixteen days being wrong in the file it was warning about.
>
> Two other statements of the same count were also stale: a comment three
> entries above reading *"this tuple **IS** two string literals"* — present
> tense, sitting directly above the third literal it denied the existence of —
> and, the one that cost something, the **NEXT ACTION** in
> `docs/SAIRN-OPEN-WORK-INDEX.md`: *"hank or cody reads `SELF_EXCLUDED` and
> answers one question — is each of the **five** entries removing a FALSE
> CREDIT rather than an inconvenient FINDING?"* That row was dispatching a
> review of **five of eight**, and a reviewer who answered it honestly would
> have reported the item complete with three entries never looked at.
>
> **A stale count in a NEXT ACTION is not a documentation nit. It is a smaller
> job wearing the name of the whole one.**
>
> **The check:** do not bump the number — remove it and point at the thing that
> prints it. All three now point at `len(SELF_EXCLUDED)`, which the tool emits
> on every run (`8 file(s) EXCLUDED as the grader's own subject`). Bumping five
> to eight would have bought about sixteen days, which is exactly how long the
> five lasted.
>
> **And measure the count by parsing, not by reading.** fourth recorded getting
> this wrong first with `sed -n '459,500p'`, which stopped inside the tuple,
> read four entries and concluded an entry was *missing*. `ast.literal_eval` on
> the assignment settled it. A line range that stops inside a structure gives a
> wrong answer with no warning — same family as a truncated read (PR §1.7).

---

## E. A single-item test cannot test a multi-item property, and every arm being green hides that

**Candidate for `docs/METHODOLOGY.md`.**

> `tests/run_scrutiny_flag_probe.py` had six arms (A–F) covering the gate's
> scrutiny check: it fires on a weakening, does not fire on an unrelated push,
> never denies, reaches the ledger, has teeth under a blinded classifier, and
> treats an import failure as a third state. All six passed. All six were
> correct. **Not one of them could express the defect in §A**, because
> `build_repo()` builds a push of exactly **one** commit — so `tip` and *the
> commit that changed the checker* were the same object, and the distinction
> the bug lives in did not exist in the fixture.
>
> The defect was found by reading five parked stashes, not by any arm.
>
> **The check:** when a property is about the relationship *between* items —
> which commit in a push, which row of a batch, which retry of a loop — a
> fixture with one item cannot test it, and a full green bar will say otherwise.
> Ask explicitly: *how many of the thing does my fixture contain, and is the
> property I care about visible at that count?*
>
> Arm G now pushes two commits — the weakening in the first, a docs-only tip in
> the second, hank's exact shape — and asserts the row names the culprit, does
> **not** name the tip, and is self-verifiable. **Ablated** via a
> `SCRUT_PROBE_GATE` lever against the pre-fix gate: 4 of arm G's 9 checks go
> red and the row sha comes back equal to the tip. Arms A–F stay green in both
> directions, which is how I know the fix changed what it meant to change.

---

## F. A process note on this batch itself, which is mine and not paste-ready

Not for anybody else's file — recorded here because it is a real failure of my
own discipline this batch.

**My batch claim expired mid-run and I did not notice for seven commits.** I
found it at item 13, while re-checking who held `docs/METHODOLOGY.md` — not by
checking my own claim. Items 6 through 12 therefore landed **under an expired
claim**, invisible to every other clone as live work. No collision resulted
(every target was re-checked against the live claim list before writing, and all
were declared by nobody), but that is luck plus per-item conflict checks, not
the claim system working.

Claims expire after 4 hours and a batch of this size runs longer than that.
**The per-item checkpoint I already run should also re-check my own claim's age,
not only other sessions' claims.** That is the cheap fix and I did not have it.
