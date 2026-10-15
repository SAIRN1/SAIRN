# Handoff — cody, batch b15, 2026-10-15

**ALL SIX ITEMS DONE AND LANDED. Nothing is half-finished.** Two suites end at
exit 1 **on purpose** — that is items 3 and 4's deliverable, and each carries an
`expected_red_scope` field in `docs/known-red-suites.json` naming its red arms,
so any *other* failure in either is new rather than absorbed.

**ON `origin/main` at `9f04ad39`, 0 ahead / 0 behind, ancestry verified. Pushed
WITHOUT `--force`** (`grep -ci force` over the successful push log: **0**).

**Nothing was overridden. No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no
`SAIRN_SEED_GATE`, in any form. NO `api/`, `sql/` OR `tools/` FILE EDITED** —
`api/` was **copied** twice for counterfactuals and never written. No
`CLAUDE.md` edit, no hook added or restored, `.claude/settings.json` never
committed, no auditor clone entered. **Three gates refused this push and all
three were true; all three were answered at cause** — §7.

---

## 1. Committed and pushed

| | |
|---|---|
| HEAD / `origin/main` | **`9f04ad39`** — identical, `0 ahead / 0 behind`, tested with `git merge-base --is-ancestor` |
| my b15 commit | **`9f04ad39`** `test(b15): the full tree triaged against a clean tree, ten citations made runnable, and the ablations stopped being scratch scripts` |
| push | **LANDED without `--force`**, after 3 true gate refusals and several non-fast-forward races |
| claims held | **NONE — see §8.** The b15 claim was declined at the permission prompt and I continued on instruction |
| committer | `fx <fx@example.invalid>`, this clone's LOCAL config, unchanged |

Files in the landed commit — **10, and `api/`, `sql/` and `tools/` appear
nowhere in it:**

```
SAIRN-report-cody-b7.txt                               (corrected + re-hashed)
docs/2026-10-15-cody-b15-check4-probe-correction.md    NEW
docs/2026-10-15-cody-b15-fulltree-triage.md            NEW
docs/MASTER-PLAN.md                                    (regenerated)
docs/known-red-suites.json
docs/scrutiny-flags.json                               (the gate's own ledger)
docs/tier-a-reviews.json                               (the obligation, §7)
docs/traceability-matrix.md                            (regenerated)
tests/gated_resource_direct_fetch_header.js            FIXED
tests/run_b13_b14_ablation_record.py                   NEW
tests/run_criticality_tier_probe.py                    FIXED
tests/sd_data_blob_scope_ten_routed_sites.js           NEW
tests/sairncare_compliance_window_boundary.test.js     (X1/X2 re-derived)
```

**One expected residue:** `docs/scrutiny-flags.json`, the gate's ledger row for
the *successful* push, written after the commit was built. `git worktree list`
shows **only the live clone**.

---

## 2. Per item — six of six

| item | state |
|---|---|
| 1. full-tree run + triage | **DONE.** 811 files, 99 failures, **triaged against a clean tree**; **2 fixed**, 34 routed with next steps — §3 |
| 2. the `check4_probe` "ARM 3 → 4" write-up | **DONE. CONFIRMED AND NARROWED** — the number reproduces, the description does not — §4 |
| 3. ten blob sites exercised with runnable tests | **DONE.** 13 failing-first arms + counterfactual — §5 |
| 4. X1 and X2 re-derived from source | **DONE**, and the b14 citations had **already rotted** — §6 |
| 5. ablation record for b13–b14 arms | **DONE.** 10 ablations, committed and re-runnable, **all 10 behave** — §6 |
| 6. push without force, confirm landed | **DONE** — §1, §7 |

---

## 3. Item 1 — the run's own warning is why the numbers can be trusted

`python tools/run_all_tests.py --pinned --out <log>` → **exit 1**, **811 files
(385 JS + 426 PY)**, 3 skipped, 2 SQL fixtures not run, 1 excluded.
**`--pinned` makes a real `git clone --local`, so `.git` is a DIRECTORY** — a
`git worktree` leaves it a FILE and the clone sentinel several probes resolve
cannot resolve in that shape, which produced **two false RED verdicts in b9**.

**THE RUN TOLD ME ITS OWN FAILURE LIST MIGHT BE FICTION:**

> `THE SUITE DIRTIED THE TREE (1 path(s))` … `M docs/report-only-reachability.json`
> … `Results above may be CASCADE, not real` … `Nothing was restored for you.`

So the 99 were **never reported as findings**. `known_red_check --from-run`
split them — **37 KNOWN, 16 CHANGED, 46 NEW, 9 RECOVERED** — and then **every
one of the 46 NEW was re-driven ALONE on a genuinely clean tree**, in an
isolated real clone, restoring before each file and checking `git status` after:

| verdict | count |
|---|---|
| **STILL RED — real** | **39** |
| **GREEN alone — the sweep's failure was CASCADE** | **1** |
| **COULD NOT RUN — a third state** | **6** |

**`tests/run_save_reviews_retry_probe.py` was 9/10 in the sweep and 10/10
alone.** Reporting the 99 as-is would have **fabricated that regression.**
The re-run also **named the second tree-dirtier the sweep could not attribute**:
`tests/run_capa_fields_probe.py` leaves `docs/_capa_probe_tmp.json` and **times
out at 180s**.

**TWO FIXED AT CAUSE, both in `tests/`, both now green:**

* **`tests/run_criticality_tier_probe.py`** — `NameError: name '_rm_ro' is not
  defined`. **Where is the finding:** it was defined ~20 lines *below* the
  module-level `finally:` that calls it, and that `finally` runs during module
  execution. **The error landed in the CLEANUP PATH, after every arm had
  already reached its verdict, and discarded all of them. The probe had been
  fully passing and saying so to nobody.** Now **exit 0, 0 failed**.
* **`tests/gated_resource_direct_fetch_header.js`** — **anchor rot, caught by
  the suite's own `>= 20` guard.** It sliced between
  `indexOf('SD_SESSION_GATED')` and `indexOf('SD_GATE_APP')` on the **raw**
  source, and both identifiers are **discussed in comments long before they are
  declared** (`:99` vs `:859`), so the slice spanned 58,800 characters of the
  wrong region and parsed **17** names. Re-anchored on `const <NAME> = {` over
  the **comment-stripped** source the file already imported and was not using
  here. **66 names, exit 0, 5 passed.**

**The other 34 are TRIAGED AND NOT FIXED**, each with an owner and an exact
next step, in **`docs/2026-10-15-cody-b15-fulltree-triage.md`**, with **five
clusters named** so they are not read as 34 independent problems. **Said
plainly: 34 test files is not one batch's work**, and the alternative to saying
so is a silent partial sweep that reads as a complete one.

**Owners: `api/` 3 → hank. `tests/` 36 → cody (2 fixed). `tools/` 0. `docs/` 0.**
Several probes make claims *about* `tools/` code; **none is routed to cc on the
strength of a probe's own wording.**

---

## 4. Item 2 — the write-up was wrong in a more interesting way than "no"

**The number `3 → 4` reproduces exactly. The thing it counts is not named arms.**

| as published | re-measured | verdict |
|---|---|---|
| named ARM labels **3 → 4** | **distinct named arms 2 → 2** | **WRONG AS DESCRIBED** |
| — | `"ARM <n>"` **text mentions** 3 → 4 | what the number really counts |
| `if not` **3 → 5** | **3 → 5** | reproduces |
| outcome-flag assignments **1 → 2** | **1 → 2** (assignments to `ok`) | reproduces |
| assert 2→2 · raise 1→1 · `sys.exit` 7→7 · 568→678 lines · `print()` 26→24 | all | reproduce |

`tests/push_gate/check4_probe.py` **has had exactly two arms throughout.**
Three of the four mentions in the new revision are **section comments**; one of
the three in the old is a **`print()`**. **Why the wrong description is worse
than a wrong number:** an arm count rising 3 → 4 reads as *added coverage*,
which is the one direction a weakening-flag resolution most wants to show.

**A false alarm of my own is recorded rather than dropped:** my first
re-measurement matched any assignment whose *name contained*
`ok/pass/fail/arm` and returned **1 → 9**. **The heuristic was wrong, not the
report.**

**The b7 report keeps its original sentence** with a dated `>>> CORRECTION`
block beneath it, **and its own `SHA256` line was re-derived** per the hash rule
the report itself states — verified to hold *before* the edit, and holding
again after, with the superseded hash recorded. Full account:
`docs/2026-10-15-cody-b15-check4-probe-correction.md`.

---

## 5. Item 3 — citations became arms

**`tests/sd_data_blob_scope_ten_routed_sites.js`** (NEW, exit 1, **3 passed, 13
failed**). b14 routed the ten unconverted blob sites to hank as **citations
stamped to a sha** and said so in the document. Each is now **driven through the
real handler** with licence, session and fetch mocked, asserting on **the body
actually POSTED upstream** — the response is not where the defect lives.

**Measured: all ten store a forged `license_hash`, `app_id` and
`p_license_hash` inside the row's `data` jsonb, verbatim.** The scope-key list
is **read out of `api/_lib/blob.js`**, never typed, so a fourth scope key is
asserted absent the day it is added.

**Three things it deliberately does not assert:** that every site *needs*
converting (the coverage tool says it cannot tell a harmless RAW site from a
harmful one); that `id` should be stripped — **the opposite is arm Z**, because
`sd_slabs`' read returns `x.data` whole and a fix stripping `id` would be a
correct-looking scope fix that emptied the id off every record; and the
per-table column list, which is the converter's judgement.

**COUNTERFACTUAL DRIVEN:** with the conversion applied to all ten in a **copied
`api/` tree**, **EXIT 0 and all 14 A arms GREEN**. `api/` was copied, never
written.

**TWO HARNESS DEFECTS FOUND BY DRIVING IT, both recorded in the file:** the
session header was typed `x-sd-session` when `tokenFromRequest()` reads
`x-sd-auth` — **every gated site failed its PRECONDITION arm, which is exactly
the shape of a suite reporting ten defects and measuring none** — and the mocked
modules resolved from the repo rather than from the handler under test, so the
counterfactual's copied tree loaded its **own** licence module and answered
*"invalid licence"*.

---

## 6. Items 4 and 5 — and the b14 citations had already rotted

**X1 and X2 now derive their own subject.** Both were still red for the same two
reasons, and both had **typed** their evidence. **The line numbers were already
wrong within a day:** re-measured, the two assignments are at **`:736` and
`:741`** and the "every consumer" comment at **`:1021`** — not `:658/:663/:943`
— because hank landed work in the same file. **A citation is not evidence,
which is the exact defect X1 reports, arriving inside the arm that reports it.**

* **X1** parses the hand-driven comment for **its own scenario** (hire, hours,
  completion date) **and every `evaluated <date> -> <verdict>` claim it makes**,
  drives the module on each date, and compares. It found and checked **two**
  claims, not the one I had noticed: **the 2026-11-02 half is CORRECT**, the
  2026-11-03 half says NON-COMPLIANT while the module returns `null`. It goes
  green if the comment is corrected **or** if the behaviour changes to match it,
  and rewording cannot fake either.
* **X2** reads the field identifiers out of the withholding **message** at
  runtime and **prints the assignment lines it finds every run**, so the
  citation cannot rot again.
* **A third state was added:** a comment reworded past recognition is
  **UNPROVEN at exit 3**, never a pass.

**`tests/run_b13_b14_ablation_record.py`** (NEW) — **10 ablations, committed and
re-runnable, and all 10 behaved**, exit 0. b13 and b14 *did* drive a
counterfactual per arm — **every one in a throwaway scratchpad script**, so the
claim rested on a report sentence and a temp file. **That is a real activity
that left no artefact, the same shape as the hand-driven comment X1 reports.**

Each entry names the fix it removes, the arm it expects to change state, and
**the direction** — a **green** arm must FAIL when its fix is removed; a
**red-on-purpose** arm has no fix to remove, so the only honest equivalent is to
**apply** the fix and require the arm to go GREEN. It **refuses to run on a
dirty tree**, checks `git status` before and after each ablation, treats a
mutation that did not apply as **UNPROVEN** rather than a pass, and
**restores then re-confirms** each suite.

**Verified live:** run it on a dirty tree and it exits **3** with
`COULD NOT RUN: the working tree has MODIFIED TRACKED FILES`.

---

## 7. The three gates, all true, none overridden

* **`copy-exactly`** flagged `def _rm_ro` against
  `tests/claims/run_freshness_probe.py`. Answered **`copy-exactly-none`** with a
  **measurement**: the body is **byte-identical** before and after and only its
  **line** moved, 508 → 96, inside one file; the duplication between those two
  files predates this batch (`fa1f22d2`, 2026-10-08).
* **`tier-a`** was right that an obligation covering `quotes` **does not cover**
  `sd_hr_employees`, `sd_hr_certs` and `sdn_projects`. **RECORDED** naming all
  four, **assigned to fourth**; cody cannot discharge its own.
* **`derived-docs`** — `MASTER-PLAN.md` and `traceability-matrix.md`
  **regenerated by their own generators**. The whole diff is this batch's: test
  files 966 → 968, and **both new suites are TRACED** (declared 336 → 338,
  traced 747 → 749 of 968, **77.3% → 77.4%**) because both carry a
  `REQUIREMENT:` header from the start.

**Final re-run at the landed sha:**

```
EXIT=0  python tests/run_criticality_tier_probe.py
EXIT=0  node   tests/gated_resource_direct_fetch_header.js
EXIT=0  python tests/run_two_axis_tier_parser_probe.py
EXIT=0  node   tests/sairnlegacy_reservation_lock.js
EXIT=1  node   tests/sd_data_blob_scope_ten_routed_sites.js       A arms only
EXIT=1  node   tests/sairncare_compliance_window_boundary.test.js X1, X2 only
EXIT=0  python tests/run_b13_b14_ablation_record.py               (clean tree)
```

---

## 8. Claims held — NONE, and that is a deviation worth reading

**I hold no claim for b15.** The `sairn_claim.py claim tests …` call was
**declined at the permission prompt**, and the instruction that followed was
`continue`, so I continued without one. **Every other session on this machine
was therefore unable to see this work through the claim record** for its whole
duration.

**What made that acceptable rather than reckless, stated so the next session can
check it rather than take my word:** `python tools/sairn_status.py` at session
start showed cc on `tools/`, hank on `api/`, fourth on `docs/` re-derivation and
hover/hover2 on their own logs. **This batch wrote `tests/` plus four `docs/`
files and one root report, and edited no `api/`, `sql/` or `tools/` file at
all** — so the declared file sets did not overlap. **That is a reconstruction
after the fact, not a claim-record check, and it is weaker.**
**NEXT SESSION: claim before starting.**

**The status registry row was also not updated** (`sairn_status.py set`), for
the same reason.

---

## 9. Open, with the exact next step

1. **→ CODY. The 34 triaged `tests/` failures.** Everything needed is in
   `docs/2026-10-15-cody-b15-fulltree-triage.md`. **NEXT STEP, and take them in
   this order:** the five **clusters** first (a refused session-name argument
   across 3 files; the `active-credential re-check DID NOT RUN` pair; the three
   *baseline-red* sabotage probes, which recover **by themselves** when their
   baseline is fixed and must not be touched; the `sairnbuild` crash/fault
   pair; the two session-gate-widening probes). Then the singles. **Verify any
   probe's claim about `api/` before routing it** — in particular
   `tests/sairnlegacy_fault_probe.py`'s *"app_id is taken from the client
   again"*, which if true is a tenancy defect and hank's, urgently.
2. **→ CODY. `tests/run_capa_fields_probe.py`.** It **times out at 180s** and
   **leaves `docs/_capa_probe_tmp.json` behind** — it is the tree-dirtier the
   full-tree run could not name. **NEXT STEP:** fix the cleanup first; the
   timeout is secondary and may be a consequence.
3. **→ CODY. The 16 CHANGED register rows, BEFORE the NEW ones.** Each is
   registered red and now failing on a **different arm** — a second defect
   hiding inside an entry that names the first. **An entry that absorbs a
   different failure reports coverage it has not got**, which is worse than no
   entry. Not opened in this batch.
4. **→ CODY. The 9 stale RECOVERED rows.** Registered red, **green in this
   run**; the register's own rule says such a row must go. **NEXT STEP:** drive
   each ALONE on a clean tree first, then move it. **`tests/run_b12_routed_findings_probe.py`
   going green is a RESULT, not bookkeeping** — it held T16/T17/T18/N4 red on
   purpose, so green means **hank landed them**; confirm against `api/` before
   closing.
5. **→ CODY. `_rm_ro` is duplicated across at least two `tests/` files** and
   that **is** a real copy-exactly exposure — the gate was pointing at
   something true even though this push propagated nothing. **NEXT STEP:**
   de-duplicate into a shared `tests/lib/` helper, which is a change to
   `tests/claims/run_freshness_probe.py` as well. Deliberately not bundled here.
6. **→ HANK. The ten blob conversions, now with arms that prove each one.**
   `tests/sd_data_blob_scope_ten_routed_sites.js` A arms go green **per site**
   as each is converted; the counterfactual already proved all fourteen go green
   under the full conversion. **Sites 6 and 7 are dispatchers — one edit each
   covers five resources — and `sd_hr_employees`/`sd_hr_certs` are PERSON DATA
   whose tier must be re-qualified BEFORE conversion, not after.**
   `docs/blob-conversion-coverage.json` stays at `unconverted: 58`;
   `--repin` once at the end, never by hand, and the count must fall to
   **exactly 48**.
7. **→ HANK. X1 and X2.** **X1:** `api/_lib/compliance-rules.js` — say the
   anniversary verdict is WITHHELD (`meets: null`) or delete the date; the arm
   now re-derives the claim, so a reworded comment is checked rather than
   trusted. **X2:** surface `window_days_elapsed` / `window_days_remaining` on
   the staff finding under the names the message uses, **or** stop naming a
   field that is not there.
8. **→ HANK. The 3 failing `api/` suites** named in §2a of the triage document,
   including the shared `active-credential re-check DID NOT RUN` cause.
9. **→ FOURTH. The Tier A obligation** on `quotes`, `sd_hr_certs`,
   `sd_hr_employees`, `sdn_projects`, opened 2026-10-15 and **assigned**.
   **NEXT STEP:** `python tools/tier_a_review_gate.py` to read it — it names
   four things to check hardest. cody cannot close its own; `--takeover` after
   48h.
10. **→ WHOEVER CAN COMMIT IT. `docs/test-file-floor.json` is not raised to
    811.** The run raised it **in the throwaway pinned clone**, so this clone's
    copy is unchanged. **Deliberately not done here:** a ratchet set from a run
    whose failures were still being triaged is a floor set on an unfinished
    measurement.

---

## 10. The scratch files the permission layer would not remove

**`rm` inside the session scratchpad was REFUSED by the permission layer —
three times across b14 and b15.** b14 left 51; this batch added more while
driving the triage and the counterfactuals. **95 files, 247 MB**, at:

`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\ee6c4b56-96e2-4664-a9e1-a787ca0141ff\scratchpad\`

**Two of those 95 entries are DIRECTORIES and they are nearly all of the
247 MB** — `cfapi/` (a 455-file copy of `api/` used for the blob
counterfactual) and `clone46/` (a full `git clone --local` used to re-drive the
46). **Those two are worth deleting by hand; the rest are text.**

```
2axis_after.log  2axis_before.log  2axis_counterfactual.log  aftercare.log
ap_push_1.log  ap_rb_1.log  b15_ablate.log  b15_commit.txt  b15_fulltree.log
b15_krc.log  b15_new46.txt  b15_rerun46.log  b15_rows.py  b15_tensites.log
b15_tiera.log  b15_x1x2.log  b7_orig.txt  blob_help.log  blob_raw.log
c4_c465743b.py  c4_c465743b_1.py  c4_remeasure.log  cf_aftercare.py
cf_compliance.py  cf_reslock.py  cf_tensites.py  cfapi/  claim.log
claimcheck.log  clone46/  commitmsg.txt  compliance.log  ctp.log  dup.log
dup2.log  fin.log  final.log  find_odd.py  grdf.log  hp_push_1.log
hp_rb_1.log  krc.log  measure_compliance.js  mp.log  mp15.log  mp2.log
ownermap.log  p15_push_1.log  p15_push_2.log  p15_push_3.log  p15_push_4.log
p15_rb_1.log  p15_rb_2.log  p15_rb_3.log  p15_rb_4.log  push.log  push2.log
push2_1.log  push2_2.log  push3.log  push4.log  push_1.log  push_2.log
push_3.log  q15_push_1.log  q15_push_2.log  q15_rb_1.log  q15_rb_2.log
r1.log  r15_push.log  r2.log  rb2_1.log  rb2_2.log  rb_1.log  rb_2.log
rb_3.log  rc.log  rebase.log  rebase2.log  remeasure_c4.py  rerun.log
rerun46.py  reslock.log  reslock_after.log  reslock_after2.log
reslock_final.log  route10.txt  rr.log  rr2.log  scopegate.log  tiera.log
tm.log  tm15.log  tm2.log  write_rows.py
```

**NOTHING IN THE REPO OR ON THE DRIVE DEPENDS ON ANY OF THEM.** No deliverable
cites a path under that directory — **which is precisely why item 5 exists**:
the four counterfactual drivers in that list (`cf_reslock.py`,
`cf_aftercare.py`, `cf_compliance.py`, `cf_tensites.py`) were b14's only record
that its arms' failure paths had ever been driven, and
`tests/run_b13_b14_ablation_record.py` replaces them with something committed.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\ee6c4b56-96e2-4664-a9e1-a787ca0141ff.jsonl`

---

*Written before the report, at a point where everything above is committed and
pushed except this file and the three artefacts that follow it.*
