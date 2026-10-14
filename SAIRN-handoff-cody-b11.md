# Handoff — cody, batch b11, 2026-10-14

**ALL SIX ITEMS DONE. ON `origin/main` at `1e45208b`, 0 ahead / 0 behind.**
Nothing below is half-finished. Every open thing is open because it belongs to
somebody else, because it is named here as the next batch's work, or because it
is a third state that is neither colour.

**Nothing was overridden. `SAIRN_SEED_GATE` was NEVER used — not the blanket
form and not the scoped `SAIRN_GATE_EXEMPT`. No hook was added or restored,
`.claude/settings.json` was never committed, NO `api/`, `sql/` OR `tools/` FILE
WAS EDITED, `CLAUDE.md` was not touched, and no auditor clone was entered.**

**THE HEADLINE: all eight dispatched suites are GREEN, and every single failure
was a STALE EXPECTATION IN `tests/` — not one defect in any subject.** A retyped
stub signature, a retired blanket override, a worktree→clone banner, a
`git log -2` POSITION, a mode-dependent consumption rule, three hand-written
posture rows, an absolute-emptiness arm named "left behind", and four
pre-`exposed` pin fixtures. The subjects in `api/` and `tools/` were correct as
written in all eight cases.

**THE SECOND FINDING IS ABOUT THIS FILE'S PREDECESSOR AND IT MATTERS MORE.**
b10 recorded `app_session_isolation`'s drift in the SINGULAR — "its own recorded
posture row is 7 days stale". Driving all 18 apps found **THREE** drifted rows.
The suite compared with one `assert.ok` per app, so the FIRST mismatch aborted
the loop and the rest were never compared. **A drift detector that stops at the
first drift under-reports by design, and the under-report is invisible because
the output looks complete.** Fixed: every row is measured and printed with its
gated/total count, then one assertion carries all the mismatches.

---

## 1. Committed and pushed

| | |
|---|---|
| HEAD / `origin/main` | **`1e45208b`** — identical, `0 ahead / 0 behind` |
| my b11 commits, **each tested as an ancestor of `origin/main`** | `a35a89e0` items 1–2 · `076fb102` item 3 · `0241b1b0` item 4 · `241acc05` the role-gate pins · `e253d410` the register · `cc618f18` the gate-demanded regeneration · `1e45208b` the gate's ledger rows — **ANCESTOR, all seven** |
| push | **LANDED without `--force`.** Two gate refusals, both repaired at cause — §7 |
| claim | `tests` — **released after this handoff, the report and the digest** |
| register | `entries` 76 → **69**, `recovered` 22 → **31**, `not_red` 5 → **4** |
| committer identity on every b11 commit | **`fx <fx@example.invalid>`**, author AND committer — §5 |

**THE FOUR `fix(tests)` MESSAGES WERE REWRITTEN TO CARRY A
`no-defect-record:` TRAILER AND THAT IS SAID OUT LOUD.** The register-feed gate
correctly asked why four commits closing failures feed no defect record. The
honest answer is that every repair is to a **test fixture that drifted while its
subject stayed correct**, so a register record would have been a fabricated one.
Each commit carries its own sentence rather than one copied five times, applied
by `git rebase --exec`. **No published history was rewritten — none of the four
had ever landed.**

---

## 2. Per item — all six done

| item | state |
|---|---|
| `run_all_tests_floor_probe.py` stub takes the fourth parameter | **DONE, FAILING-FIRST.** COULD-NOT-RUN → **exit 0, 26 checks**; 3 mutants driven, 3 caught — §3 |
| `refspec_and_override_probe.py` scoped-form refusal · `run_all_tests_pinned_probe.py` clone anchor | **DONE.** 0 failures · ALL 27 ASSERTIONS PASS — §3 |
| `run_cron_liveness` SHA/content anchor · `run_graduated_exemption` MODE · `app_session_isolation` posture row | **DONE, and the third item was THREE rows, not one** — §4 |
| `run_committer_identity_probe.py` hermetic | **DONE. 19 PASS, and NO identity was unset or changed** — §5 |
| methodology · `missing_checker` 2 arms · `role_gate` 4 pin arms | **DONE.** Both green; the 2 were a CASCADE, the 4 were a stale pin shape — §6 |
| push without force, confirm landed | **LANDED** — §1, §7 |

---

## 3. Item 1 and 2 — three stand-ins, all three retyped from something real

`python -u tests/run_all_tests_floor_probe.py`: **exit 0, 26 checks, 0 failing**
(was exit 1, a traceback at arm 2).

**RED CAPTURED BEFORE ANYTHING WAS TOUCHED:** `TypeError: fake_run() takes from
2 to 3 positional arguments but 4 were given`, raised from
`tools/run_all_tests.py:1278`. So this suite was **COULD NOT RUN, not red** —
the floor arms could not be judged at all.

`fake_run(js, py, quiet=True)` was a **THIRD retyped copy** of `_run`'s
signature, beside the one the file's own header already records dying on
`ValueError` when a third return value appeared. `_run` gained a fourth
PARAMETER, `excluded`, and `_main_body` passes it **positionally**. **There was a
SECOND retyped stub in `patched_result`** — fixing only the first would have
moved the crash to arm 8 rather than removing it.

Both are `*a, **k` now, and **a new arm 0 binds them against
`inspect.signature(R._run)`** for every real call shape, pinning the call-site
count so a third shape cannot be swallowed by `**k`. A seam failure is **exit 2
COULD NOT RUN with the reason named, and the floor arms do not run** — "the stub
no longer fits the function" is not evidence about the floor in either
direction.

**CONTROL: three mutants driven, all three caught** — the retyped signature
restored, a shape the real `_run` cannot take, and a third call site appearing.

`python -u tests/push_gate/refspec_and_override_probe.py`: **exit 0, 0
failures.** The arm asserted the BLANKET `SAIRN_SEED_GATE=off` override was
ALLOWED; it was retired on purpose on 2026-10-13
(`tools/sairn_push_gate_hook.py:1377-1392`). It now asserts the refusal, with
the text **DERIVED from `tools/gate_skip.py` BLANKET_REFUSAL — 15 lines matched
— rather than retyped**, and the refused attempt logged as `ALL` with
`not honoured`. **TWO CONTROL ARMS stop "any refusal counts":** the
un-overridden and quoted-mention refusals must NOT carry the blanket text, which
is exactly what deleting the refusal branch would produce, since the gate refuses
that fixture anyway.

`python -u tests/run_all_tests_pinned_probe.py`: **exit 0, ALL 27 PINNED/OUT
ASSERTIONS PASS.** The hardcoded `throwaway worktree` anchor is now read out of
the runner's own source and **fails CLOSED on not finding it** — an empty anchor
is `'' in body`, true for any body including an empty one, which is the exact
truncation arm 5 exists to catch.

---

## 4. Item 3 — a position, a retired contract, and three posture rows

`python -u tests/run_cron_liveness_probe.py`: **exit 0, 59 passed, 0 failed.**
The arm read `git log -2` and took `_prev[-1]` — a **RELATIVE POSITION**. On
2026-09-23 `c3f2b2a0` (actions/checkout v4→v7 across all five workflows) touched
the file and slid the window by one, so the arm read the commit that **ADDED**
the step and reported that the pre-change version contained it. Anchored on
CONTENT now; **content and not a pinned sha because this repo rebases** — the
sha found is PRINTED as evidence (`5d0f4459`, step added in `a9394d8e`).
Controls: the next revision must ADD the step, and HEAD must still carry it.

`python -u tests/run_graduated_exemption_probe.py`: **exit 0, ALL ARMS PASS.**
Consumption follows `MODE` by design since 2026-10-07 — one Bash `git push` runs
the hook TWICE over ONE store file, and the PreToolUse half was eating the token,
making the scoped exemption **ungrantable**. **Both modes are driven through the
DERIVED default**, and that pair is the control: `consume` hardcoded False fails
the prepush arms, hardcoded True fails the pretooluse arms.

`node tests/app_session_isolation.js`: **exit 0, ALL 66 ASSERTIONS PASS**,
`node --check` clean. **THREE rows, each corrected against a LANDED commit:**

| app | was | now | commit |
|---|---|---|---|
| `sairngrounds` | NONE / NOT DOCUMENTED | **SOME, 21 of 30** | `6a2690be` 2026-10-07 |
| `sairnscape` | SOME ("2 of 12") | **ALL, 12 of 12** | `0442646c`, `d99b47f9`, `5776ef19` |
| `sairnfreedom` | SOME ("16 of 36") | **ALL, 36 of 36** | `46d74678` 2026-10-13 |

**THE NINE STILL-UNGATED `sairngrounds` RESOURCES ARE NAMED IN THE ROW AND WERE
DRIVEN, NOT INFERRED.** They are exactly the `msb_*` set — **`msb_licenses` is
Tier A and is one of them.** Every `grd_*` refuses; every `msb_*` does not.
**SOME is the measurement, not an all-clear.**

**`sairnscape`'s OLD ROW IS THE WORST SHAPE A ROW HERE CAN TAKE.** It did not say
"not decided" — it said the other ten stayed licence-only **DELIBERATELY**. A
reader sweeping for licence-only resources would have skipped the app on the
strength of a positive claim that the gap was a decision.

---

## 5. Item 4 — the arm was asking the wrong question, and no identity was touched

`python -u tests/run_committer_identity_probe.py`: **exit 0, 19 PASS.**

**RED FIRST:** section F's `and no local override was left behind`, detail
`fx@example.invalid`. b10 routed this to **Michael as a DECISION. It was not
one.** The arm is named "left behind" — a BEFORE/AFTER property of the run — and
it tested `--local --get user.email == ''`, which is a property of whoever's
clone it is. **Both repairs the failure invited were wrong:** unsetting a
committer identity is not a test's call, and dropping the arm would retire the
only check that the probe cleans up after itself. It now asserts the LOCAL layer
is **byte-identical before and after**, named separately from the merged read —
because the merged read would stay equal if a probe wrote a local override
identical to the inherited value, **which is the shape that hid for three days
in 2026-09**.

**HERMETIC NOW.** git MERGES system, global and local, so every git command and
tool invocation against the throwaway clone runs with `GIT_CONFIG_GLOBAL` and
`GIT_CONFIG_SYSTEM` pointed at an empty file. Without it, an operator whose
GLOBAL identity happened to be a known throwaway would see section B — *"an
ordinary identity is CLEAN"* — refuse. **Section A is deliberately NOT
isolated**: its job is to report what this clone really commits as.

**NEW CONTROL, BOTH DIRECTIONS (section B0):** a hostile GLOBAL config carrying a
known throwaway identity **DOES** reach the checker and is refused — so the
fixture is not inert — **and** under the isolation the same clone is CLEAN. That
pair fails if `isolated_env()` is deleted, which matters because the symptom of
missing isolation is a verdict that depends on whose machine it is, and **that is
invisible from one green run.**

**ASKED FOR AND MEASURED: every b11 commit carries `fx <fx@example.invalid>` as
BOTH author and committer.** It comes from this clone's **LOCAL** config;
`--global` is `Michael Dibert <mikied68@gmail.com>`. `committer_identity_check.py`
reports this clone CLEAN, so `fx@example.invalid` is **not** on the derived
throwaway-identity list. **Nothing was changed.**

---

## 6. Item 5 — the 2 were a cascade, the 4 were a stale pin shape

`python tests/push_gate/missing_checker_probe.py`: **exit 0, 40 PASS**, criteria
lock 7/7 first. **~25 minutes — it runs the full gate eleven times.**

**THE TWO b10 FAILURES WERE WORKTREE-RESIDUE CASCADE, NOT DEFECTS, AND NOTHING
WAS EDITED.** b10's own cleanup note records the cause: two leftover gate
worktrees and one gate base worktree were still registered when it ran, and
`git worktree remove --force` cannot finish against that, so the cleanup arm
fails and the section-F control after it inherits a dirty registry. **EVIDENCE,
NOT A GUESS:** `git worktree list` read immediately BEFORE this run showed only
the live clone; during the run it showed exactly one addition
(`gate-missing-19808`); the cleanup arm then PASSED and the list is back to one.
**STANDING RULE FOR THE NEXT SESSION: read `git worktree list` before driving
this suite.**

`python -u tests/run_role_gate_negative_coverage_probe.py`: **exit 0, 0 failed**
(was 4 failed). **RED FIRST: all four arms at `exit=2`,** every one
*"COULD NOT TELL — the pin carries neither `exposed` nor an integer
`not_driven` … NOTHING WAS COMPARED on that leg."*

**A STALE FIXTURE, AND THE TOOL IS RIGHT.** b9 read it as "the tool exiting 2 on
the fixture's constructed pin" — the symptom. The cause: all four constructed
pins were `{'uncovered': N}`, the **pre-change shape**.
`tools/role_gate_negative_coverage.py:763` ratchets on
`exposed = uncovered + not_driven`, because deleting the only suite that drives a
resource moves it `uncovered → not_driven`: **`uncovered` FALLS, the old rule
printed "IMPROVED — re-pin", and the ratchet could be walked down by deleting
tests.** **NOTHING IN `tools/` WAS EDITED.**

**THREE LEGS DRIVEN, not just the repaired one:** the modern pin; the LEGACY pin
which must still compare by DERIVING the sum **and disclose that it derived it**;
and the `uncovered`-ONLY pin, **whose exit 2 is now asserted as the CORRECT
answer rather than erased by the repair — the failure is a test now.**
**NEW CONTROL:** `uncovered` falling while the SUM HOLDS must be "no worse" and
must NOT be IMPROVED, because that is precisely what deleting a driving suite
looks like.

### Two `not_red` predictions driven rather than left standing

Both said *"it will recover by itself when the baseline does"*, both baselines
have since gone green, and **nothing had tested either claim**.

* **`tests/app_session_isolation_probe.py` — the block IS cleared by this
  batch's fix to its baseline. ALL 13 ARMS PASS, 8 mutations, every one
  refused.** And **the first drive found a real stale anchor**, which is the whole
  value of running it: mutation 7 reported **ANCHOR-3**, exit 1. Its anchor was
  the bare 403/FORBIDDEN block — unique when written, now **three** occurrences in
  `api/sd-data.js`: the `SD_SESSION_GATED` gate at `:2106` that the mutation
  names, plus two ROLE gates that landed later and are not the session boundary
  at all (`sairnsenior` MANAGEMENT_ROLES `:6777`, `sairnbuild` BLD_DRAW_ROLES
  `:13983`). `replace(o, n, 1)` would have planted in whichever came first.
  **NOT a coverage gap — the arm was never running.** The anchor now carries
  `if (!gateSession) {`, measured unique. **It stays in `not_red` at exit 3:**
  what remains is the pre-fix COUNTERFACTUAL being unreachable, which is neither
  colour.
* **`tests/run_cross_tenant_dispatchers_sabotage_probe.py` — block cleared, and
  it is RED, so PROMOTED to `entries`.** Exit 1: 15 filter mutations all hold, 2
  gate tripwires fail. **DIAGNOSED AND NOT FIXED** — §8 item 1.

---

## 7. Two gate refusals, both repaired at cause, nothing overridden

**REFUSAL 1 — the register-feed gate**, on all four `fix(tests)` commits. The
answer was the `no-defect-record:` trailer, **not** a register record, and the
reason is the finding: every repair is to a test fixture that drifted while its
subject stayed correct. §1 records the rewrite.

**REFUSAL 2 — the generated-document gate:** `docs/TOOLING-INVENTORY.md` stopped
matching its sources. Regenerated with **the one command the gate itself
printed** — `python tools/tooling_inventory.py`, exit 0, every leg closed, 644
lines. **ONE CELL CHANGED and it is correct:** `gate_skip.py`'s control column
gains `refspec_and_override_probe.py`, because that probe now imports
`gate_skip` to derive the refusal text. **That is the one declared exception to
b11's `tests/`-only scope: a generator the gate refused without.**

**EXTRA SCRUTINY is REPORTED, not a refusal, and the four WEAKENING flags are
answered in the commits they name** — the shapes matched are
`a skip / exemption / allowlist entry ADDED`, caught on posture-row text, on the
word "drift" in a derived-text comment, on an `_exempt_path` assertion and on a
`rmtree(ignore_errors=True)` cleanup. **All four are arms and recorded
measurements; none relaxes anything.** The gate's own note says the WEAKENING
level was 3 of 3 FALSE on its first real diff, and that it is a triage prompt
rather than a finding.

Then two `fetch first` races, both rebased. **No conflicts and no `--force` at
any point.**

---

## 8. Open, with the exact next step

1. **`tests/run_cross_tenant_dispatchers_sabotage_probe.py`** → **cody, next
   batch. DIAGNOSED, NOT FIXED — it is outside b11's dispatched items and is
   recorded rather than done quietly.** The probe **HARDCODES** two `app: null`
   gate tripwires at `:406-416` on `grd_boq_rates` and `grd_rounds`. Those units
   stopped being `app: null` **deliberately**:
   `api/sd-data-cross-tenant-dispatchers.test.js:647-654` now sends a real
   `sairngrounds` session, and the comment at `:633-646` states the trade in its
   own words — the tripwire is given up so the arms test TENANT ISOLATION again,
   with the gate's arrival held by a dedicated suite. **THE REPLACEMENT COVERAGE
   WAS CHECKED RATHER THAN TRUSTED:** `tests/sd_data_grd_session_gate.js` exists
   (added in `6a2690be` with the 21-resource gate) and names both resources — the
   comment guesses its path as `api/`, it is under `tests/`. **NEXT STEP: DERIVE
   the tripwire list from the suite's own `app: null` units so it cannot go stale
   again, AND assert in the same arm that the dedicated gate suite covers GRD.
   DO NOT simply delete the two arms — that drops the coverage instead of
   relocating it.**
2. **`tests/app_session_isolation_probe.py`'s pre-fix counterfactual** → **cody.**
   Exit 3, neither colour. The suite as it stood before `PHASE_2_GATED` existed is
   no longer green against current `api/sd-data.js`, so "BLIND" would mean nothing
   and the harness refuses to print it — correct, and a loss of evidence rather
   than a failure. **Decide whether it can be re-based on a later pre-repair
   commit or should be retired with its finding recorded.** It is a historical
   control and it has done its job once.
3. **`MIN_TEST_FILES` is 370 against 796 discovered** → **cc** (`tools/`).
   `tests/run_all_tests_floor_probe.py` arm 1 prints it as HOUSEKEEPING every
   run: **426 test files could be deleted with the guard silent.** Raise it in
   `tools/run_all_tests.py`. Reported, not fixed — it is deliberately a floor and
   not an equality, so this is a stale pin and not a defect.
4. **`tools/sairn_push_gate_hook.py:988-991` contradicts its own code 390 lines
   below** → **cc** (`tools/`). The comment block says *"THE BLANKET FORM STILL
   WORKS and is deliberately not removed"*; `:1377-1392` refuses it and prints
   the scoped form. **`CLAUDE.md` §3 was the same staleness and SOMEBODY HAS
   ALREADY FIXED MOST OF IT** — it now leads with `SAIRN_GATE_EXEMPT=seed`. But
   its new paragraph still says **"`SAIRN_SEED_GATE=off` still works"**, which the
   code contradicts. → **whoever owns `CLAUDE.md`.** Not the tests owner's, either
   file.
5. **`tests/push_gate/check4_probe.py` and `check7_probe.py`** → **unchanged,
   still `not_red` at exit 3**, blocked by the same failing blind lock. **Not
   examined in b11** and said rather than implied.
6. **The 17 suites that build a `.git` sentinel** → still nobody's, and still the
   point. `python tests/worktree_sentinel_guard.py --report` lists them; it
   re-measured **424 python suites scanned, 17 building a sentinel, 0
   unclassifiable from this clone** during b11.
7. **One `docs/scrutiny-flags.json` residue is expected after the final push.**
   The gate writes a ledger row for every commit it examines, so the commit that
   lands this handoff will itself produce one. b10 left the same residue and
   Michael committed it as `chore(scrutiny ledger)`. **It is a record, not dirt —
   do not `git checkout --` it without reading it.**
8. **Items 3–7 of b10's open list that are NOT mine and were not touched:**
   `tests/faults/transport_timeout_sweep.js` (hank),
   `run_blob_coverage_scope_sabotage.py` (cc),
   `run_citation_anchor_hop_sabotage.py` (cc),
   `run_alf_read_order_sabotage_probe.py` (hank), `ooda_phases.py`'s stale
   self-test (cc). **All still open, all still routed, none re-verified here.**

---

## 9. Methodology — what was actually proved

**EVERY REPAIR IS FAILING-FIRST AND THE RED IS QUOTED, NOT SUMMARISED.** Eight
suites, eight captured reds, each one's exit code and failing arm names written
into `docs/known-red-suites.json` beside the `file:line` that produced the exit.
The before/after logs were in the scratchpad and are **deleted** — the register
is the citation, because a digest pointing at a temp directory is a citation that
expires.

**EVERY REPAIR CARRIES A CONTROL ARM THAT STOPS "DELETE THE CHECK" FROM
SATISFYING IT**, and three of them caught something:

* the floor probe's seam arm was driven against **three mutants** and caught all
  three, including the exact b10 defect restored;
* the identity probe's hostile-global fixture proved **reachable** before the
  isolation was proved to block it — without that, "isolation works" is satisfied
  by an inert fixture;
* the role-gate control is the **gamed shape itself**: `uncovered` falling while
  the sum holds is what deleting a driving suite looks like.

**NO TEST WAS EDITED TO TURN IT GREEN.** Two repairs make the opposite trade:
`run_role_gate_negative_coverage_probe.py` keeps the exit-2 refusal that was
failing it **as a new arm**, and `run_all_tests_floor_probe.py` adds a third
state (exit 2) rather than letting a broken stub report green.

**ONE THING IS DISCLOSED AND NOT MEASURED.** `missing_checker_probe.py` was
driven at `ebbf57c5`, before the last three commits. Those commits touch
`tests/run_role_gate_negative_coverage_probe.py`,
`tests/app_session_isolation_probe.py` and `docs/`, none of which it reads — but
it was **not** re-driven at `1e45208b`, because it costs ~25 minutes. **Stated
rather than folded into the green.**

---

## 10. Cleanup

**Removed:** my own scratch files under
`C:\Users\marsh\AppData\Local\Temp\claude\…\scratchpad\` — the b11 before/after
logs (`b11_floor_before/after`, `b11_refspec_before/after`,
`b11_pinned_before/after`, `b11_cron_before/after`, `b11_grad_before/after`,
`b11_appiso_before/mid/after`, `b11_ident_before/after`, `b11_rg_before/after`,
`b11_mc_before`, `b11_aisp`, `b11_aisp2`, `b11_ctd`, the eight `b11_final_*` and
two `b11_post_rebase_*` logs), the one-shot scripts (`b11_floor_control.py`,
`b11_posture_measure.js`, `b11_posture_counts.js`, `b11_register.py`,
`b11_trailer.sh`) and `krs_backup.json`.

**WORKTREES: `git worktree list` shows ONLY the live clone.** Two were removed
by hand during the batch — `red-suite-worktree-eb9jqf1m`, left by a
`red_suite_register_check.py` run I stopped, and a gate base worktree from the
pinned probe. **That residue is exactly what caused b10's two
`missing_checker_probe` failures (§6), so leaving it would have handed the next
session the same false red.**

**`docs/scrutiny-flags.json` was restored once with `git checkout --`** — the
refspec probe drives the real gate, which appends a ledger row — and its real
rows from the real push attempts are **committed**, in `1e45208b`.

**EVIDENCE IS IN THE REGISTER AND IN THE COMMIT MESSAGES, NOT IN SCRATCH.**

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\ec3355ad-083b-4402-a518-3d4e79072c4c.jsonl`

---

*Written before the report, at a point where everything above is committed and
pushed except this file and the report and digest that follow it.*
