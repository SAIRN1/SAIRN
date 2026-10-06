# CC inventory — batch 10, 2026-10-06

Seven items. **Five landed, one partly landed with the shortfall measured, one
refused on a live claim and routed.** Every figure below carries the command,
the commit and the date; every exit code was read from a status file written by
`tools/capture_exit.py`, never from a harness notification.

Baseline for everything here: **`411f29ce`**, `origin/main...HEAD` = `0 0`,
fetched 2026-10-06.

---

## 0. Premise log — the brief against HEAD, item by item

Written first, because **two premises were wrong and one item was already
half-built by somebody else.**

| # | premise in the brief | at HEAD |
|---|---|---|
| — | *"discharge the most overdue review obligation before new work"* | **LISTED, NOT DISCHARGED — CODY HOLDS THAT EXACT WORK.** 25 eligible, oldest 230h. See §1 |
| 1 | `checker_selftest_check.py`'s third-state reason is false; one line | **HELD, and one line was not enough** — the cause had to be carried out of a bare `except`. See §2 |
| 2 | *"whatever writes SHAs must capture AFTER the rebase"* | **PARTLY WRONG AS A DESIGN, AND THE MECHANISM ALREADY EXISTED.** There is no capture-after-push moment; `.githooks/post-rewrite` has had git's own old→new map since 2026-09-24 and its SCOPE was one file. See §3 |
| 3 | 7 of 14 importers defer the import; move all 7 to module level | **PREMISE INCOMPLETE AND THE FIX IS MOSTLY STRUCTURAL.** "Module level" is not "at import": 6 already-eager probes still run 11–156 lines first. Measured before/after — **1 of 6 improved measurably.** See §4 |
| 4 | `SAIRN-ACTIVE-WORK-cc.md`'s 19 orphans — justify or fix | **MY REASON DOES NOT HOLD UP, AND NEITHER DOES "REWRITE THEM". It is 26, not 19, and 7 of the extra are mine from today.** See §5 |
| 5 | clean up the 2 locked temp dirs | **DONE, and the lock was transient.** See §6 |
| 6 | one methodology rule | **DONE** — §8, routed because the file is hank's |
| 7 | handoff | `docs/handoff-cc-2026-10-06b.md` |

---

## 1. Review obligations — 25 eligible, LISTED, and the most overdue NOT taken

**Listed first, as instructed.** `docs/tier-a-reviews.json` at `411f29ce`:
**235 records, 203 reviewed, 32 open.** Of the 32, **7 were authored by `cc`**
and are therefore not eligible — the whole point of the ledger is that a change
is reviewed by a session other than the one that wrote it. **25 are eligible to
me.** Oldest five, by `opened_at`:

| age | opened_at | author | resources |
|---|---|---|---|
| **230h** | `2026-09-27T01:22:40Z` | hank | `mech_insurance_policies`, `mech_site_assets`, `sc_anesthesia…` |
| 229h | `2026-09-27T02:06:03Z` | cody | `mech_credentials`, `mech_site_assets`, `sc_claims`, `sc_drg…` |
| 228h | `2026-09-27T02:31:54Z` | hank | `alf_compliance_rules`, `alf_staff`, `alf_staff_credentials` |
| 227h | `2026-09-27T03:42:29Z` | hank | `alf_staff`, `sen_visits` |
| 207h | `2026-09-28T00:16:59Z` | fourth | `alf_clients`, `alf_facility`, `alf_family_contacts`, `alf_mar…` |

**I DID NOT DISCHARGE ANY OF THEM, AND THE REASON IS A LIVE CLAIM RATHER THAN A
PREFERENCE.** `cody` holds `docs/tier-a-reviews.json` under a claim taken at
`2026-10-06T14:53:05Z` — inside the 4h window, re-checked at 17:03Z — whose task
text is **`"queue18: Tier A discharges most-overdue-first with adversarial
controls"`**. That is not an overlapping subject; it is the instruction I was
given, verbatim, already in flight.

**THE FILE'S MERGE POLICY IS WHY THIS IS A REAL COLLISION AND NOT A PAPER ONE.**
`merge_policy` is `union-by-identity` on `(author_session, opened_at)`, and
`tools/sairn_rebase_resolve.py` **REFUSES** a merge when both sides changed the
same record differently. Two sessions each discharging most-overdue-first do not
pick different records — they pick the same one. The append-only design absorbs
us working on *different* obligations and refuses, correctly, when we work on
the same one.

**Declared in the claim rather than reworded past the matcher (PR §4.3).** The
230h obligation is named here so it is routable, not quietly skipped.

---

## 2. `checker_selftest_check.py` — a true third state with a FALSE reason

**THE DEFECT.** `registry_tools()` returned a bare `None` from **two** different
`except` arms, so `main()` could only print a disjunction it had no way to
evaluate: *"COULD NOT READ `tools/report_only_checks.py`, or its REGISTRY is
empty."*

**DRIVEN, AND NEITHER DISJUNCT WAS TRUE.** Fault: one entry appended to
`REGISTRY` missing only its `evidence` field. The validator raised
`RegistryIncomplete` naming the entry and the field. The file read fine; the
registry held 76 entries.

**THE EXIT CODE WAS NEVER WRONG.** Exit 2 is correct and PR §1.11 was satisfied.
What was wrong is that the message sent the reader to the two places the answer
was not, while the real diagnosis — which named the tool AND the missing field —
was discarded by the bare `except`.

**THREE ARMS, DRIVEN AGAINST A STUBBED REGISTRY, exit codes from
`capture_exit.py --read`:**

| arm | fault | exit | message |
|---|---|---|---|
| A | `RegistryIncomplete` raised at import | **2** | `COULD NOT READ the report-only registry. THE REAL CAUSE, as raised: RegistryIncomplete: … missing: evidence` |
| B | `REGISTRY = []`, genuinely empty | **2** | `THE REGISTRY READ FINE AND IS GENUINELY EMPTY — 0 entries carrying a 'tool' key` |
| C | module absent entirely | **2** | `… THE REAL CAUSE: ModuleNotFoundError: No module named 'report_only_checks'` |

**AND THE CONTROL IS WHAT MAKES THAT MEAN ANYTHING.** The same two faults driven
against the **pre-fix** code (`git show HEAD:…`) produced **byte-identical**
output — verified with `diff`, 0 lines of difference. One message, two causes.

**I REINTRODUCED THE DEFECT ONE LINE LOWER AND THE DRIVE CAUGHT IT.** My first
message appended *"the file was NOT found to be unreadable and the registry was
NOT found to be empty"* — true of arm A and **false of arm C**, where the module
genuinely is absent. Deleted, and the deletion is commented in place so the next
author does not re-add the reassurance. The exception line already separates the
cases; no claim beyond it is asserted.

**Regression:** `tests/run_checker_selftest_probe.py` **23 passed, 0 failed,
EXIT 0**, unchanged before and after, and the clean-path output is byte-identical
to the pre-fix run.

---

## 3. The root cause of the orphaned citations — and the mechanism already existed

**WHAT THE BRIEF ASKED FOR CANNOT BE BUILT AS STATED.** *"Capture the SHA after
`sairn_claim.py`'s rebase-before-push"* presumes a post-push moment to capture
in. Git has no post-push hook, and the SHA is not final until the push succeeds
— so there is no point at which a writer could have captured the right value.

**WHAT DOES EXIST, AND HAS SINCE 2026-09-24:** `.githooks/post-rewrite` fires
once after a rebase or an `--amend` with git's own `<old> <new>` map on stdin and
hands it to `defect_register.py --post-rewrite`. That is **strictly better than
capturing at write time** — it does not need the writer to predict anything.

**THE GAP WAS THE FILE LIST, NOT THE MECHANISM. Measured at `411f29ce`:**

| document | hexish tokens | ON-MAIN | ORPHAN | ABSENT | re-seated by the hook? |
|---|---|---|---|---|---|
| `docs/defect-density-register.json` | 564 | 546 | 5 | 13 | **yes** |
| `docs/SAIRN-OPEN-WORK-INDEX.md` | 404 | 337 | 14 | 53 | **no** |
| `docs/traceability-matrix.md` | 114 | 93 | 6 | 15 | no |
| `SAIRN-ACTIVE-WORK-cc.md` | 280 | 245 | 25 | 10 | no |

The register stayed healthy; the prose beside it rotted. **One file covered, and
it is the covered one that is clean.**

**TIGHTER FIGURE FOR THE INDEX, and the two must not be mixed up.** The table
above counts **bare** hex words, which over-counts: 404 candidates against 367
when backticks are required, and the 37 extra are decimal figures, 12-hex
register record ids and one illustrative literal (`1234abcd`). On the tight
count the index is **321 ON-MAIN / 8 ORPHAN / 38 ABSENT = 46 dead of 367
(12.5%), across 37 rows.** 46 is the number to quote.

### What landed: `tools/doc_sha_reseat.py`, wired into the hook that already has the map

**ONLY A TOKEN THAT IS A PREFIX OF AN `old` SHA GIT ITSELF NAMED IS
SUBSTITUTED.** No subject matching, no patch-id, no heuristic. The prefix
comparison runs in **one direction only** — the document's token must be a prefix
of the map's `old`, never the reverse — copied deliberately from
`defect_register.cmd_post_rewrite`, so a 7-character token cannot match a
different commit's abbreviation. A rewrite that did not move the commit
substitutes nothing.

**BACKTICKS ARE REQUIRED, AND THAT IS A MEASUREMENT.** The bare-word form has a
9% false-candidate rate on a 900-line standing document. A repair tool with that
rate is not one anybody should wire to a hook.

**THREE FILE CLASSES, and the second one only exists because the drive found it:**

* **REWRITE** — `SAIRN-OPEN-WORK-INDEX.md`, `CRITICALITY-TIERS.md`,
  `known-red-suites.json`. Rewritten in the working tree, **never staged, never
  committed** — the identical contract `defect_register.py --post-rewrite` has
  carried since 2026-09-24. Unless another session holds the file under a live
  claim, in which case it is **PROPOSED** and not touched: the hazard there is a
  write race, and no mechanical substitution is worth one.
* **GENERATED** — `traceability-matrix.md`, `TOOLING-INVENTORY.md`,
  `MASTER-PLAN.md`. **Never patched.** The first version of the list had the
  traceability matrix in REWRITE, and the end-to-end drive re-seated two real
  citations in it *correctly* before the obvious question surfaced: that file is
  generated by `tools/traceability_matrix.py` **from the open-work index**, which
  is where those same SHAs come from. The repair would have been discarded by the
  next generation while reading, in the meantime, as a fix that had been applied.
  Membership is taken from `invocation_path_scan.GENERATED_DOCS`, not from my own
  guess at which files look generated.
* **REPORT-ONLY** — `SAIRN-ACTIVE-WORK-*.md`. Never rewritten; listed by name on
  every run so a stale pointer in a log is visible without being erased.

**DRIVEN END TO END, through the hook itself**, with a one-pair map on stdin
(`c8b5e5b1…` → `HEAD`), exit from `capture_exit.py`:

```
hook EXIT 0
  defect register: re-seated 1 record(s) from git's own rewrite map.
  PROPOSED for docs/SAIRN-OPEN-WORK-INDEX.md -- NOT WRITTEN because another
    session holds it under a LIVE CLAIM
  GENERATED, so NOT PATCHED -- docs/traceability-matrix.md ... REGENERATE it
  REPORT-ONLY, never rewritten: SAIRN-ACTIVE-WORK-{cc,cody,fourth,hank}.md
```

**THE MAP IS READ TWICE BY TWO PROGRAMS AND THAT NEEDED A FIX IN THE HOOK.** Git
hands stdin once; piping it into the first consumer would leave the second
reading an empty stream and reporting, truthfully and uselessly, that no commit
moved. It is captured to a variable and fed to each. **Control: the HEAD version
of the hook under the same map re-seated the register and printed nothing about
the documents** — so the first consumer's behaviour is unchanged and the second
is the whole delta. Both synthetic edits were reverted; `git status` confirms the
register is untouched.

**`docs/recurring-bug-classes.md` was dropped from the set** — it does not exist
at this commit, and a permanent COULD-NOT-READ line on every run trains a reader
to skip the third state.

**Regression:** `tests/run_doc_sha_reseat_probe.py` — **19 arms, 0 failed,
EXIT 0**. It drives all three classes against temp trees, because on the live
clone **every REWRITE target was under another session's claim**, so the real run
exercised only PROPOSE and GENERATED. A tool whose write path has never executed
is not one to wire into a git hook.

**ONE ARM OF MINE WAS WRONG AND THE TOOL WAS RIGHT.** Arm E asserted that a
blinded token rule would report *"Nothing to do"*. What actually happens is
better: the tool's own criteria lock classifies its 12 fixtures first, two fail
under the mutation, and it exits **2 COULD NOT RUN** with *"NOTHING REAL WAS READ
OR WRITTEN"* before any document is opened. The lock is this tool's ablation
detector. The arm now asserts that; asserting the empty result would have been an
arm that passes on the worse of two designs.

**WHAT IT DOES NOT CLAIM:** that a document whose SHAs all resolve is correct. A
citation can point at a real commit and be the wrong one —
`defect_register.is_bookkeeping_only` exists because
`--commit $(git rev-parse HEAD)` cited three bookkeeping commits that resolved
perfectly. This repairs pointers a rewrite BROKE. It cannot see one that was
wrong when written.

---

## 4. The import-time refusal — 6 of 7 moved, and the premise was incomplete

**THE PREMISE: 7 of 14 importers defer the import into a function, so the refusal
arrives mid-run. MOVE ALL 7.** Six moved;
**`tools/dead_rule_sweep.py` is cody's under a live claim** and is routed instead.

**TWO DIFFERENT MOVES, AND CONFLATING THEM WOULD HAVE UNDONE §2.** Three of the
six (`checker_selftest_check`, `invocation_path_scan`,
`flaky_checker_quarantine`) wrap the import to produce a third state or a
labelled fallback. A **bare** module-level import there would replace a named
diagnosis with a traceback — trading a worse message for an earlier one when
both are available at once. Those three got a **guarded** module-level import:
evaluated at import, outcome carried. The other three
(`checker_control_check`, `traceability_matrix`, `run_export_coverage_probe`)
have no third state, so a bare hoist changes *when* and not *what*.

**AND THE `sys.path` INSERT HAD TO MOVE WITH IT** for two of them. The old insert
sat inside the function; hoisting the import alone works when the file runs as a
script (its own directory is `sys.path[0]`) and fails when it is imported as a
module — which `tools/checker_confidence.py` does to
`flaky_checker_quarantine`. Verified: all five tools import cleanly as modules,
**EXIT 0** each.

### MEASURED BEFORE AND AFTER, and the honest answer is 1 of 6

The number item 3 is really about is **how many lines of the program's own output
precede the refusal**. Fault injected in a detached worktree;
`tools/report_only_checks.py` never edited in the live clone and verified
byte-identical to `origin/main` afterwards.

| importer | class | BEFORE | AFTER | |
|---|---|---|---|---|
| `tests/run_export_coverage_probe.py` | bare hoist | **30** | **0** | **the one measurable win** |
| `tools/checker_control_check.py` | bare hoist | 0 | 0 | no change — `promoted()` was already called before any output |
| `tools/traceability_matrix.py` | bare hoist | 0 | 0 | no change, same reason |
| `tools/invocation_path_scan.py` | guarded | 0 | 0 | **improved invisibly to this metric** — see below |
| `tools/checker_selftest_check.py` | guarded | *(refused with the FALSE message)* | 3 | **improved invisibly to this metric** |
| `tools/flaky_checker_quarantine.py` | guarded | 36 | 36 | unchanged **by design** — the labelled fallback is the better behaviour |

**SO THE FIX IS MOSTLY STRUCTURAL RATHER THAN MEASURABLE, AND SAYING OTHERWISE
WOULD BE SIX WINS WHERE THERE IS ONE.** What the three 0→0 moves buy is not
fewer lines: it is that the refusal no longer depends on *call order*. A future
edit that prints before the first call to `promoted()` would have silently
reintroduced the delay; now it cannot.

**TWO IMPROVEMENTS THIS METRIC CANNOT SEE**, which is why it is not the only one
reported: `checker_selftest_check` went from a false reason to the real cause
(§2), and `invocation_path_scan` went from naming only the unreadable input
(`report_only_checks.REGISTRY`, eleven characters) to naming it **with the
raised cause beneath it**. Same defect class as §2, one notch milder — that one
asserted something false, this one asserted too little.

### THE PREMISE WAS INCOMPLETE: "module level" is not "at import"

**SIX PROBES ALREADY HAD MODULE-LEVEL IMPORTS AND STILL RUN 11 TO 156 LINES
FIRST**, because a module-level import placed 184 lines down executes 183 lines
of module body before it:

| probe | own lines before the refusal |
|---|---|
| `tests/run_baseline_readiness_probe.py` | **147** |
| `tests/run_literal_drift_control_probe.py` | 44 |
| `tests/run_optimistic_success_probe.py` | 44 |
| `tests/run_dora_metrics_probe.py` | 21 |
| `tests/run_risk_event_tree_probe.py` | 19 |
| `tests/run_assurance_case_probe.py` | 11 |

So the universal guarantee the brief wants is **not** achievable by moving
imports to module level — it needs them in the **import header**. None of those
six is in my claim and all six fail closed loudly, so they are reported with
their numbers rather than edited. **13 of 13 fail closed under the fault; none
reports a clean run.**

**AND §16 OF THE BATCH-9 INVENTORY HAS ONE STALE COLUMN, corrected here rather
than left to be rediscovered:** its control column was measured at `5553f1e2`
and recorded all 13 importers at exit 0. At `411f29ce` the clean-registry
controls are **not** all 0 — `checker_control_check`, `checker_selftest_check`,
`flaky_checker_quarantine`, `invocation_path_scan`, `run_export_coverage_probe`
and `run_baseline_readiness_probe` exit 1 on a clean registry, for reasons
unrelated to any edit of mine (verified: the HEAD version of each produces
byte-identical output to mine). A control column is only true as of the commit it
was taken at.

---

## 5. `SAIRN-ACTIVE-WORK-cc.md` — the reason does not hold up, and neither does rewriting

**MY REASON THIS MORNING:** *"an append-only log records what was true when each
entry was written; silently repointing history is worse than a stale pointer in
it."*

**THE FIRST HALF IS RIGHT ABOUT PROSE AND WRONG ABOUT POINTERS.** A SHA written
before its push was never true on `main` — it resolved in one clone, mine, and in
no other, from the moment it was written. That is not a preserved past truth; it
is a reference that never resolved for any reader.

**BUT REWRITING THEM IN PLACE IS ALSO WRONG, for a reason I had not identified
until I counted: SIX ARE QUOTED *AS DEAD*.** The 2026-10-06 close-out entry cites
`99774ecc`, `cabb4f7e`, `21a41817`, `641fb936`, `ddbfd281` and `571cab5f`
precisely because they are orphans — they are the evidence. Repointing those
would delete the finding and leave a paragraph about dead SHAs in which every SHA
resolves.

**RESOLUTION: A TABLE APPENDED, NOTHING ABOVE EDITED.** Append-only kept
literally; every dead pointer resolvable in one place; the three classes still
distinguishable, which an in-place rewrite would have destroyed.

**AND IT IS 26, NOT 19.** Not drift — **seven of the extra are mine from today**,
six of them the deliberately-quoted orphans. A figure quoted from a scan taken
before the same session appended to the file is stale by construction.

| class | n | |
|---|---|---|
| **RESOLVED** | **16** | each by a *unique* subject match on `origin/main` — no ambiguity, no judgement |
| **QUOTED-AS-DEAD** | **6** | left exactly as written |
| **UNRESOLVABLE** | **3** | ABSENT — not an object in this clone, so no subject to match. Cannot be resolved from here by any method |
| **NO-SUBJECT-MATCH** | **1** | `74e029a5f373` resolves locally; its subject appears on no commit on `main`. Either it never landed or it landed reworded, and this clone cannot tell which |

**THE SUBJECT MATCH IS THE WEAKER METHOD AND IS USED ONLY BECAUSE THE STRONGER
ONE IS GONE.** These 26 predate the `post-rewrite` wiring; their exact maps
expired with the reflog. §3 is why there will not be a 27th.

---

## 6. The two locked temp directories — cleared, and the lock was transient

**BOTH ARE GONE.**
`…/scratchpad/regwt` refused `rm -rf` this morning with `Device or resource busy`
and `git worktree remove` with `Permission denied`; it deleted cleanly on a
retry once the background process holding it had exited.
`…/Temp/drs-sandbox-5otm8w0w` was already absent — `dead_rule_sweep.py` builds
that sandbox itself, which is also why it is the slow importer.

**Neither is registered as a worktree** (`git worktree list` | grep → no match),
so nothing in git pointed at either. **The method was "wait for the holder to
exit, then retry"**, and the honest note is that the first report should have said
*"held by a live process"* rather than *"genuinely inert"* — a lock with an owner
is a different fact from a lock with none.

---

## 7. Routed, not landed

* **`tools/dead_rule_sweep.py`** — cody's. The one lazy importer I did not move;
  its import at `:488` sits inside a function and the sweep builds a git
  worktree before reaching it, which is why both arms of yesterday's bound
  exceeded **900s** (control `exit 124`). Routed with that measurement.
* **The 37 open-work index rows** — hank's. `docs/2026-10-06-cc-routed.md` §9.
  `tools/doc_sha_reseat.py --post-rewrite` now proposes them automatically on the
  next rewrite.
* **The six late-but-module-level probe imports** — not mine, numbers in §4.
* **`docs/2026-09-13-cross-domain-disciplines.md` item 11 has NO BODY** —
  fourth's. See §9.
* **The methodology rule** — hank holds `docs/METHODOLOGY.md`. §8.

---

## 8. Methodology — one rule, and what paid for it

**A COMMIT SHA IS THE ONE FORM OF EVIDENCE ON THIS PLATFORM THAT A SUCCESSFUL
PUSH IS GUARANTEED TO INVALIDATE. Never write one for a commit that has not been
pushed; cite the artefact instead, and let the rewrite map repair what is already
written.**

**PAID FOR, TWICE OVER, IN MEASURED COUNTS:** 46 dead citations of 367 in
`docs/SAIRN-OPEN-WORK-INDEX.md` (12.5%, 37 rows) and 26 in
`SAIRN-ACTIVE-WORK-cc.md`, of which 5 were mine from a single batch. No clone
can resolve 38 of the index's — they were created and orphaned in another clone
and are not fetchable from anywhere.

**THE SHAPE IS GENERAL AND IS NOT ABOUT SHAs.** A tool wrote a value that was
TRUE WHEN WRITTEN and that the platform's own normal operation then made FALSE —
and nothing announced it, because the document still reads as precise. This is
discipline 8 (instrument drift) with a sharper edge: the drift is not gradual and
not probabilistic, it is **caused by the success path**. The citation does not
rot over months; it dies at the instant the push it was waiting for succeeds.

**THE TEST FOR THE CLASS:** *does the act of completing this work change the
value I just recorded about it?* If yes, record something the completion cannot
touch — a test file, an assertion count, a resource name — or arrange for the
completing step to hand you the correction. `post-rewrite` is that arrangement
for SHAs and it already existed; what was missing was the list of documents it
covered.

**AND A SECOND-ORDER RULE FROM THE SAME MEASUREMENT, because it inverted a
finding once today:** a sweep for dead references **must not be satisfiable by
the local object store of the clone that wrote them**. `git cat-file -e
<sha>^{commit}` answers *does this object exist here*, which is clone-dependent:
my own `ddbfd281` passes it in this clone and fails it in every other one on this
machine. It reported **38**. `git merge-base --is-ancestor <sha> origin/main`
answers the question a reader has, and reports **46**. A check whose verdict
depends on which clone runs it is not a check.

**Routed to hank for `docs/METHODOLOGY.md`** and recorded here because this is
the batch that bought it.

---

## 9. A finding against a standing document, routed to fourth

**`docs/2026-09-13-cross-domain-disciplines.md` ITEM 11 HAS A HEADING AND NO
BODY.** Lines 447 and 448 are adjacent:

```
## 11. Human-gated auto-remediation — a fixer may not approve its own fix
## 12. Ablation over chaos — measure ONE layer's contribution, not the system's luck
```

Everything that follows is item 12's — the SpaceX heatshield framing, the
2026-09-25 first run, the per-arm measurement. **Item 11 is a title.**

**WHY THIS MATTERS MORE THAN A FORMATTING SLIP:** `CLAUDE.md` instructs every
session to COUNT the `## <n>.` headings rather than trust a written figure, and
the count is 15 — so item 11 is *counted* as present on every read. A reader
following the instruction correctly concludes the convention exists and is
documented. **I relied on item 11 for this batch's `doc_sha_reseat.py` design**
(propose-vs-apply by file ownership) and had to reconstruct its content from the
`post-rewrite` hook's own reasoning, because the document that is supposed to
state it does not.

**Reproducing artifact:** `sed -n '447,449p'
docs/2026-09-13-cross-domain-disciplines.md` at `411f29ce`.
**Routed to fourth**, who holds that file. Not fixed by me: writing the body of
somebody else's convention is not a formatting repair.

---

## BLIND SPOTS — 6

1. **I did not discharge a single review obligation.** 25 eligible, oldest 230h,
   and the reason is cody's live claim on the identical work. That is a correct
   refusal and it is still 25 undischarged obligations.
2. **The three 0→0 import moves are unmeasured.** I claim they remove a
   dependency on call order. Nothing in this batch tests that — it would need a
   mutation that prints before the first registry read, and I did not build one.
3. **`tools/doc_sha_reseat.py`'s write path has never executed on a real
   tracking document.** Every REWRITE target was under another session's live
   claim all day, so the live runs exercised PROPOSE and GENERATED only. The
   write path is proven against temp trees in 19 probe arms and nowhere else.
4. **The 16 RESOLVED entries in §5 rest on subject matching**, which is the
   weaker method and which `post-rewrite` exists to avoid. Each match is unique,
   and a unique match on a reworded subject would still be wrong. I did not
   diff the trees to confirm.
5. **The six late-module-level probes are reported, not fixed**, so the
   "universal guarantee" item 3 asked for is **not** achieved — it is 7 of 13
   at zero lines, not 13 of 13.
6. **Nothing here was verified against a deployment.** Every item is a
   build-time tool, a hook or a document; none has a deployed surface to drive,
   so "verified" means its own controls, its own ablation and nothing more.
