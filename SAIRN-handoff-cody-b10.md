# Handoff — cody, batch b10, 2026-10-14

**ALL SIX ITEMS DONE. ON `origin/main` at `e730b906`, 0 ahead / 0 behind, tree
clean.** Nothing below is half-finished. Every open thing is open because it
belongs to somebody else, because it is a decision rather than a code change, or
because it is named here as the next batch's work.

**Nothing was overridden. `SAIRN_SEED_GATE` was NEVER used, no hook was restored
or re-added, `.claude/settings.json` was never committed, NO `api/` FILE AND NO
`sql/` FILE WAS EDITED, and no auditor clone was entered.**

**THE HEADLINE: the never-driven backlog is CLOSED. `diagnosed` blank went
13 → 0.** Every suite in `docs/known-red-suites.json` has now been driven and
what happened is written down.

---

## 1. Committed and pushed

| | |
|---|---|
| HEAD / `origin/main` | **`e730b906`** — identical, `0 ahead / 0 behind`, `git status` clean |
| my b10 commits, each tested as an ancestor of `origin/main` | `fcd8b188` items 1–5 and the register · `0028a088` the two regenerated derived docs + the gate's own scrutiny rows · `e730b906` the merge — **ANCESTOR, all** |
| push | **LANDED without `--force`.** Two gate refusals, both repaired at cause — §7 |
| claim | `tests` — **released after this handoff, the report and the digest** |
| register | `entries` 84 → **76**, `recovered` 14 → **22**, **undriven 13 → 0** |

**THREE COMMITS WERE COLLAPSED INTO ONE AND THAT IS SAID OUT LOUD.**
`86f6b0ca`, `c5ca2812` and `acac88b8` were committed separately; the
register-feed gate then correctly refused the push, and its escape trailer is
read from **the commit's own body**, so the only honest routes were to rewrite
that message or to write a defect record for a non-defect. They were
re-committed as one with the trailer. **No published history was rewritten —
none of the three had ever landed.**

---

## 2. Per item — all six done

| item | state |
|---|---|
| `test-op-audit.js` stub takes 2 args | **DONE, and FAILING-FIRST.** 15 failed → 0 failed, exit 0, 29 passed — §3 |
| `reservation_lock` `active` reply | **DONE.** ALL 59 ASSERTIONS PASS, exit 0 — §4 |
| `server_backup` 35 → 36 | **DONE, and the decision was made from evidence BEFORE the number moved** — §5 |
| `run_tool_selftest_probe.py` exit 3 | **DONE.** Measured exit 3, `129 passed, 0 failed, 1 could-not-run` — §6 |
| fixture rows 39, 46, 40 | **DONE, each sized to what the file actually lacked** — §8 |
| worktree-sentinel check + the 13 undriven | **DONE. 17-arm guard, exit 0; all 13 driven; undriven 13 → 0** — §9, §10 |
| push without force, confirm landed | **LANDED** — §1, §7 |

---

## 3. The op-audit stub — 14 arms were one defect, and it was not in `api/`

`node tests/sairncare/test-op-audit.js`: **exit 0, 29 passed, 0 failed** (was 12
passed / 14 failed).

**FAILING-FIRST, and the red was captured before anything was touched:** arms
S1/S2/S3 were added and run first, giving **14 passed / 15 failed**, with S1
reporting the exact message `bad app scope: undefined`.

The stub demanded **three** arguments. `api/sd-data.js:1938` calls
`verifySessionToken` with **two**, deliberately, because the
`credentialStillActive` pre-gate runs *above* per-resource app scoping and its
own comment says so. **THE STUB WAS THE STALE HALF AND `api/` IS CORRECT AS
WRITTEN.**

It now allows an **absent** `expectedApp` and **still refuses a wrong one**:

* **S2 is the control** that stops *"tolerate two arguments"* being satisfied by
  **deleting** the app-scope check — which would have retired a real
  cross-tenant assertion.
* **S3 anchors** the two-argument call site, so this section cannot go on
  measuring a contract the handler no longer has.

---

## 4. The reservation-lock fixture — the pre-gate broke it two ways at once

`node tests/sairnlegacy_reservation_lock.js`: **exit 0, ALL 59 ASSERTIONS
PASS.**

The same pre-gate (a) **consumed the first `replies` entry**, shifting every
later reply by one so the `active` lookup itself read `undefined` → 403; and
(b) would have been **counted in `out.calls`**, breaking every
`calls.length === N` arm — the arms that prove the lock is **one** atomic
conditional write rather than a read-then-write. **Only the first symptom was
visible, which is why the 403 was confusing.**

It is now **answered out of band** in the harness: no reply consumed, no call
recorded, counted in `out.activeLookups`. So the fixture's accounting is exactly
what its author wrote, **and a pre-gate that moves again does not need twelve
edits.**

**TWO MORE STALE SPOTS FELL OUT, both the same shape.** A `leg_bookings`
double-booking guard (`api/sd-data.js:14967`) refuses **400
BOOKING_WINDOW_REQUIRED before any upstream call** without a facility and a
window. The control arm and the 36-resource loop both sent bare `{ id }`, so the
control asserted a call that never happened and the loop measured **35/36 where
the one that "failed" had not been tested** — a precondition failure wearing the
costume of a property failure. Both now satisfy the precondition and the shared
property is measured on **all 36 equally**, rather than `leg_bookings` being
exempted from it.

---

## 5. The 36th resource — decided from evidence, then the number moved

`node tests/sairnfreedom_server_backup.js`: **exit 0, 17 passed, 0 failed.**

The arm's own message said *"if that is deliberate, change this number in the
same commit"*. **IT IS DELIBERATE**, and from `git log` rather than
recollection: `e3446a48`, 2026-09-29, *"sf_trustee_audits reached the server for
the first time — and the registry's own reconciliation had been one short for
weeks"*.

`sairnfreedom.html` has 43 `K_x` bindings and that one was on **none** of the
lists — not `SF_SYNCED`, not the registry, not the schema, not `SF_RESOURCES`,
**and not the deliberate-exclusion list either**. It carries the **ORC 2915
controls attestation** — who attested to the post's financial controls and the
fidelity bond covering the people who handle gaming receipts — and it lived in
one browser's cache.

**The count stays HARDCODED on purpose.** Deriving it from
`REG.resources.length` would make it unfalsifiable, and what it exists to catch
is a resource being **removed**, taking every per-resource assertion in the file
with it.

**ONE CHANGE CLEARED THREE ROWS** — §10.

---

## 6. The third state reaches an exit code

`python -u tests/run_tool_selftest_probe.py`: **exit 3**, and it prints
`129 passed, 0 failed, 1 could-not-run`.

**THIS FILE QUOTED PR §1.11 AT ITSELF AND THEN BROKE IT.** Its output separated
COULD NOT RUN from FAILING with care; its return was
`1 if (fails or cnr or shrunk or unparsed) else 0`, so **a could-not-run alone
produced exit 1** — at the only place a runner reads.

Both halves of `docs/2026-10-13-cody-b6-methodology-unproven.md` §3 are now
implemented: the exit code carries the state **and** the summary line states the
count beside pass and fail. **Precedence is deliberate** — a real failure
outranks a could-not-run, and SHRUNK and UNPARSED stay failures because a
vanished selftest and an unreadable file are losses of coverage, not intermittent
conditions.

**THE REGISTER ROW STAYS IN `entries`, because exit 3 is neither colour.** It
clears when `ooda_phases.py`'s stale `<10 records have an injection date`
self-test is fixed against 249 real records — **cc's**.

---

## 7. Two gate refusals, both repaired at cause, nothing overridden

**REFUSAL 1 — the register-feed gate:** *"this push closes a defect and does not
feed the register."* Correct to ask. **The answer was the `no-defect-record:`
trailer, not a register record**, and the reason is the finding: every repair in
that commit is to a **test fixture that drifted while `api/` stayed correct**.
Both `api/` guards landed *after* the fixtures that now fail against them, and
the 36th resource is a deliberate addition. **A register record would have been
a fabricated one.** The trailer says so in 30+ characters, which is what the
gate requires and what stops the field meaning nothing.

**REFUSAL 2 — the generated-document gate:** `docs/MASTER-PLAN.md` and
`docs/traceability-matrix.md` stopped matching their sources, because the push
adds a test file and changes register rows both documents count. Regenerated
with the two commands the gate itself printed — both exit 0, both *"every leg
closed"*. **That is the one declared exception to b10's `tests/`-only scope: a
generator the gate demanded, not an authored `docs/` edit.**

Then one `fetch first` race. **No conflicts and no `--force` at any point.**

---

## 8. Item 4 — three criteria locks, each sized to what the file lacked

**ROW 39 `tests/push_gate/missing_checker_probe.py` — the fail-closed rule's own
probe, and it had no lock.** Its verdict lived in three inline conditions per
arm. They are now one named predicate, `deny_for()`, locked by **7 synthetic
cases** before any real gate runs — **and the arms were rewired through it, so
the lock is load-bearing rather than decorative.** The arm that matters is
**L2: a refusal for an UNRELATED reason is NOT a deny** — without it, *"any
refusal counts"* satisfies every arm in sections B–D.

**THE LOCK CAUGHT ME WRITING A FIXTURE THAT COULD NOT FAIL**, which is the
cheapest possible proof it is load-bearing: L4 expected the phrase `seam` while
the victim path is `.../sairn_seam_check.py`, so **the path itself satisfied the
phrase test**. L4 now uses a phrase that cannot appear incidentally and **L4b
pins the lesson** — a phrase that is a substring of the victim path cannot
discriminate. The separator bug the header records (backslashes vs forward
slashes once failing *every* arm at once, which inside a mutation harness reads
as every mutation biting) is locked as **L6** instead of left in a comment. A
failed lock is **exit 2 and the real gate is not run**.
**Measured: lock 7/7, then 38 PASS with 2 failures** — *"a push of a sql file
whose table the snapshot has is allowed"* and *"the throwaway worktree is
removed"*. Both are in the real-gate sections, **pre-existing, not touched**, and
§11 names them as open. It needs ~10 minutes to run.

**ROW 46 `tests/run_role_gate_negative_coverage_probe.py` — the docstring states
both halves and nothing locked the thing that reads them.** Every arm decides
through `num()`, which takes the first digit token off the first line starting
with a key — a text parse against a tool's prose, and the one point where the
probe can silently answer about the wrong number (`UNCOVERED: none (12 gates)`
would read **12**). **Six cases now lock it both ways; L3 is the one that
matters** — a line with no count must return `None` rather than a digit from
elsewhere on it, and L4 pins that an absent key is `None` and never `0`.
**Measured: lock 6/6**; the 4 remaining failures are the pin-file arms already
diagnosed in b9 and are unchanged.

**ROW 40 `tests/role_gate_loop_rule_probe.py` — ALREADY locked in both
directions, and saying so matters.** Its P-arms and N-arms are exactly the pair
the routing document asks for. **Two things were missing and neither is the
pair:** no version stamp, and an **unguarded seam** — `run()` reaches straight
into `rg.file_driven(src, ROLES)`, so a rename or a changed return shape kills it
mid-arms with a traceback that looks exactly like *"the rule broke"*. It now
checks the seam against a minimal fixture whose answer is known by hand and
**exits 2 COULD NOT RUN with the reason named**.
**Measured: exit 0, seam reachable, 11/11.**

---

## 9. Item 5a — the worktree-sentinel guard, and it is a correction to my own work

`python -u tests/worktree_sentinel_guard.py --selftest`: **17 arms, exit 0.**

**In b9 two suites were driven in an isolated worktree, crashed, and were
reported RED. They are GREEN.** Their sentinel is
`os.path.join(REPO, '.git', 'seam-delegation-probe.planting')` and **in a
worktree `.git` is a 64-byte FILE, not a directory**, so the sentinel can never
be created. The rule is now mechanical: **no suite may be classified red or
green from a worktree unless every sentinel it builds RESOLVES**; otherwise the
answer is **exit 2 COULD NOT RUN**, which is neither colour.

**DERIVED, NOT A HAND LIST** — sentinels are read out of each suite's own source
every run, in three spellings, with comments and docstrings stripped because
every file that discusses this defect names `.git` in prose.

**IT INHERITS THROUGH IMPORTS, AND THAT WAS NOT OPTIONAL:** the file that
*motivated* the guard — `run_delegation_residue_control.py` — **builds no
sentinel of its own.** It reaches the probe by `CONTROLS_FOR` and by a built
path handed to `spec_from_file_location`, so a guard that understood only
`import <name>` would have called it CLASSIFIABLE and therefore red — **the
original defect wearing a new hat.** Three routes are read, one level only,
declared.

**The control pair runs both ways on synthetic trees**, and the arm that stops
*"always refuse in a worktree"* from satisfying it is: **a suite with NO
sentinel is CLASSIFIABLE even in a worktree.** Unreadable source is exit 2,
never 0. **Its first self-arm was wrong in a useful way** — it asserted this
file builds no sentinel and failed, because the arms hold fixture source in
string literals; it now asserts the property that actually matters, that the
guard does not block *itself* from a real clone.

**REAL TREE, REPORTED AND NOT ASSERTED: 424 python suites scanned, 17 build a
`.git` sentinel, 0 unclassifiable from this clone. b9 knew about TWO.** The
other fifteen would have been misclassified from a worktree in exactly the same
way.

---

## 10. Item 5b — the 13 undriven suites, driven in the live clone

**Driven in the LIVE clone deliberately**, one at a time, `git status --short`
checked **before and after every single suite**. The one suite that dirtied the
tree (`push_gate/refspec_and_override_probe.py` — `docs/scrutiny-flags.json`
and `docs/BYPASS-LOG.jsonl`) was restored with `git checkout --` before the next
one ran. **Nothing accumulated; HEAD never moved during the sweep.**

Phase A re-confirmed the two `.git`-sentinel suites: **both exit 0**, and the
guard printed `sentinel(s) resolve here (clone checkout)` for each — including
the inherited one for the residue control.

**EIGHT ROWS WENT GREEN and moved to `recovered`:**

| suite | result |
|---|---|
| `tests/sairncare/test-op-audit.js` | 29 passed, 0 failed |
| `tests/sairnlegacy_reservation_lock.js` | ALL 59 ASSERTIONS PASS |
| `tests/sairnfreedom_server_backup.js` | 17 passed, 0 failed |
| `tests/sairnlegacy_fault_probe.py` | ALL 23 ARMS PASS (18 mutations) |
| `tests/sairnfreedom_fault_probe.py` | 0 failed |
| `tests/sairnfreedom_server_backup_probe.py` | ALL 9 ARMS PASS (4 mutations) |
| `tests/claims/run_registry_claim_probe.py` | 0 failure(s) |
| `api/sd-data-cross-tenant-dispatchers.test.js` | 419 passed, 0 failed |

**THREE OF THOSE EIGHT CLEARED WITHOUT BEING TOUCHED — and they were DRIVEN to
confirm it rather than assumed.** The three fault/mutation probes are
baseline-gated on the two fixtures repaired in §4 and §5, so one count change
and one harness change gave them a baseline and **31 mutations then ran**. That
is the difference between a record and a prediction.

**AND `sairnfreedom_server_backup_probe.py` IS WHY A LEFT-ALONE exit-2 ROW
MATTERS.** b9 correctly left it exactly as it was, because exit 2 is neither
colour. Had it been recorded red, the cause would have been attributed to the
probe instead of to the stale 35-vs-36 count that actually held it.

**ELEVEN ROWS GOT THEIR FIRST DIAGNOSIS**, each with its exit code, its failing
arm names, its cause and the `file:line` of its exit:

* **REAL DEFECTS — 4 suites, 11 arms.** `run_alf_read_order_sabotage_probe.py`
  (a subject that scores **zero reads found as a pass**, so hoisting a read into
  a local silently empties the arm); `run_blob_coverage_scope_sabotage.py` (a
  coverage figure over a **flat `os.listdir` universe missing 126 files**, with
  2 live write sites outside it); `run_citation_anchor_hop_sabotage.py` (a
  60-line window **crediting a neighbour's access**, and a **comment** on the
  cited line reading as *direct*); `faults/transport_timeout_sweep.js` (three
  apps **reject** on timeout instead of resolving, and **stonedesk has no 15s
  abort at all** — calibrated by **twelve** apps that pass the same arms).
* **STALE EXPECTATIONS — 5.** `refspec_and_override` (the blanket
  `SAIRN_SEED_GATE` override was retired on purpose — **and `CLAUDE.md` §3 is
  stale the same way**, routed); `run_all_tests_pinned` (a hardcoded
  `worktree` anchor after the deliberate worktree→clone switch);
  `run_cron_liveness` (an unrelated commit **slid a `git log -2` window** — the
  eighth discipline exactly); `run_graduated_exemption` (consumption now follows
  `MODE` by design); `app_session_isolation` (**the suite measured correctly**;
  its own recorded posture row is 7 days stale — it is working as a drift
  detector).
* **COULD NOT RUN — 1.** `run_all_tests_floor_probe.py` crashed on a **stale
  stub signature**: the real `_run` gained a fourth parameter and `fake_run` did
  not.
* **ENVIRONMENT PRECONDITION — 1.** `run_committer_identity_probe.py`: this
  clone carries a pre-existing local `user.email` override. **The arm before it
  passed**, which is the evidence the probe did not write it.

**NO TEST FILE WAS EDITED TO MAKE ANY OF THIS PASS.** Nothing in the 13-suite
sweep was touched at all.

---

## 11. Open, with the exact next step

1. **`tests/run_committer_identity_probe.py`** → **Michael. A DECISION, not a
   code change.** This clone's `user.email` is `fx@example.invalid` and
   `user.name` is `fx`. Either that local identity is intentional and the arm
   should assert the expected value instead of emptiness, or the override should
   be removed. **It is not the tests owner's to unset a committer identity.**
2. **`CLAUDE.md` push-protocol §3 still documents `SAIRN_SEED_GATE=off`** as the
   override, and the blanket form was deliberately retired — the hook answers
   *"it no longer works … USE THE SCOPED FORM"*. → **whoever owns `CLAUDE.md`.**
   A standing document that teaches a retired override is worse than silence.
3. **`tests/faults/transport_timeout_sweep.js`'s four findings** → **hank.**
   `sairncare.html`, `sairnscape.html` and `stonedesk.html` reject on timeout
   instead of resolving to the failure value; `stonedesk.html`'s `sdData()` has
   **no 15s abort at all**. Twelve apps pass the same arms, so the arms are
   calibrated.
4. **`tests/run_blob_coverage_scope_sabotage.py`** → **cc** (`tools/`).
   `api_files()` uses `os.listdir` — flat — so 126 files are outside the
   coverage universe and the figure is a floor that does not say so. Two live
   `data:` write sites are in the unscanned region:
   `api/_lib/sd-store.js:166`, `api/sairndental/public-complaint-submit.js:136`.
5. **`tests/run_citation_anchor_hop_sabotage.py`** → **cc** (`tools/`). The
   citation checker is a substring test, so its ANCHORED-VIA rows are
   **UNVERIFIED rather than sound**: a 60-line window credits a neighbour's
   access, and a comment on the cited line reads as *direct*.
6. **`tests/run_alf_read_order_sabotage_probe.py`** → **hank.**
   `api/alf-append-only-read-order.test.js` must treat **zero matches as a third
   state, not a pass**; today hoisting the `alf_mar` read into a local empties
   the arm silently.
7. **`ooda_phases.py`'s `<10 records have an injection date`** against 249 real
   records → **cc.** It is the single item keeping
   `tests/run_tool_selftest_probe.py` at exit 3; when it clears, that suite
   exits 0 and its row should move to `recovered`.
8. **Five stale-expectation repairs in `tests/`** → **cody, next batch.** The
   `refspec_and_override` override arm, `run_all_tests_pinned`'s anchor,
   `run_cron_liveness`'s `git log -2` window (anchor on the SHA or the content,
   not on a relative position), `run_graduated_exemption`'s `MODE`, and
   `app_session_isolation`'s recorded `sairngrounds` posture row (update to SOME
   and cite `6a2690be`).
9. **`tests/run_all_tests_floor_probe.py`'s stub signature** → **cody, next
   batch.** `fake_run(js, py, quiet=True)` must take the fourth parameter the
   real `_run(js, py, quiet, excluded=None)` now has, otherwise the floor arms
   cannot be judged at all. Its standing note while passing arm 1: *"the suite
   GREW: 792 files discovered, MIN_TEST_FILES says 370 … 422 test file(s) could
   be deleted with the guard silent."*
10. **`tests/push_gate/missing_checker_probe.py`'s 2 remaining failures** →
    **cody, next batch.** *"a push of a sql file whose table the snapshot has is
    allowed"* and *"the throwaway worktree is removed"*. Both are in the
    real-gate sections, pre-existing, and untouched by b10's lock. Budget ~10
    minutes for a run.
11. **`tests/run_role_gate_negative_coverage_probe.py`'s 4 pin-file arms** →
    **cody, next batch.** Diagnosed in b9 as the tool exiting 2 on the fixture's
    constructed pin; the lock added in b10 does not address them.
12. **The 17 suites that build a `.git` sentinel** → **nobody yet, and that is
    the point.** `python tests/worktree_sentinel_guard.py --report` lists them.
    Run that guard before classifying any suite from a worktree; it is the
    mechanical form of b9's two false verdicts.

---

## 12. Cleanup

**Removed:** my own scratch files under
`C:\Users\marsh\AppData\Local\Temp\claude\…\scratchpad\` — the b10 logs
(`b10claim`, `oa_before`, `oa_after`, `rl`–`rl3`, `sb`, `ts`, `wsg`–`wsg5`,
`wsg_rep`, `r39`–`r39c`, `r46`, `r40`, `mp`, `tm`, `p1`–`p4`, `undriven`, the
three chained-suite logs and the `b10logs/` directory) and the one-shot scripts
`reg_b10.py`, `m1.txt`, `mb10.txt`, `diag_bk.js`.

**Two leftover gate worktrees from the row-39 runs** (`gate-missing-968`,
`gate-missing-3568`) **and one gate base worktree** were removed and pruned by
hand — the probe's own cleanup arm fails while the gate holds them, which is
open item 10. **`git worktree list` shows only the live clone.**

**EVIDENCE IS IN THE REGISTER, NOT IN SCRATCH.** All 13 drives, the 11 filled
`why` fields and the 8 `recovered` rows are in `docs/known-red-suites.json`,
each naming its exit code, its arm names and the `file:line` that produced the
exit. A digest pointing at a temp directory is a citation that expires.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\6f734872-ad7d-48a6-9ee8-4fe9b8c31a22.jsonl`

---

*Written before the report, at a point where everything above is committed and
pushed except this file and the report and digest that follow it.*
