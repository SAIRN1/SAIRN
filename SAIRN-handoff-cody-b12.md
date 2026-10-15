# Handoff — cody, batch b12, 2026-10-14

**ALL SIX ITEMS DONE. ON `origin/main` at `37c649fc`, 0 ahead / 0 behind.**
Nothing below is half-finished. One expected residue:
`docs/scrutiny-flags.json`, the gate's own ledger rows from the final push,
committed with the deliverables.

**Nothing was overridden. No `SAIRN_SEED_GATE` and no `SAIRN_GATE_EXEMPT`, in
any form. No hook added or restored, `.claude/settings.json` never committed,
NO `api/`, `sql/`, `tools/` OR `CLAUDE.md` FILE EDITED, no auditor clone
entered, no `--force` at any point.**

**THE HEADLINE: not one of the six suites I was sent at had a defect in its
subject. Five had STALE ANCHORS OR STALE EXPECTATIONS IN `tests/`, and one
needed a finding written down rather than fixed.** Two hardcoded tripwire names,
two ANCHOR-0 mutations, a hardcoded two-site list, a per-file guard rule, three
standing "EXPECTED RED" footers and three unconditional registration arms.

**THE SECOND FINDING IS THE ONE WORTH CARRYING FORWARD: three of my own new or
tightened arms went red on their first run, and every one of those reds was the
arm's defect, not the subject's.** A comment matched as code, a range *string*
read as a revision walk, a LOCAL sha treated as needing a remote-existence
guard, and a `file:line` citation computed against a comment-stripped copy. Each
was found by reading the subject after the arm accused it — which is the
direction a tightened arm is supposed to fail in, and the reason none of them
reached a routing document.

---

## 1. Committed and pushed

| | |
|---|---|
| HEAD / `origin/main` | **`37c649fc`** — identical, `0 ahead / 0 behind` |
| my b12 commits, **each tested as an ancestor of `origin/main`** | `44fad1f9` item 1 · `7b8f00c0` item 2 · `f0c85a0c` item 3 · `3a5d4640` item 4 · `f8baf814` item 5 · `11ee9668` the symmetric E1 · `22ad7800` + `37c649fc` the gate-demanded regenerations — **ANCESTOR, all eight** |
| push | **LANDED without `--force`.** Four gate refusals, all repaired at cause — §7 |
| claim | `tests` — **released after this handoff, the report, the digest and `SAIRN-latest-cody.md`** |
| register | `entries` 69 → **64**, `recovered` 31 → **37**, `not_red` 4 (one row resolved in place) |
| committer identity | `fx <fx@example.invalid>`, author and committer, from this clone's LOCAL config — unchanged |

---

## 2. Per item — all six done

| item | state |
|---|---|
| tripwire list DERIVED + GRD replacement coverage; counterfactual decided | **DONE.** exit 0; 5 of 5 mutants caught; counterfactual **RETIRED**, re-base ruled out by measurement — §3 |
| blob-coverage S2 re-aimed, register row, citation row, arm 6 tightened, coverage re-pinned | **DONE.** 7 passed · 13/13 arms · 64 → 58 with the tool — §4 |
| T16, T17, T18, N1–N4 failing-first, ablation proven | **DONE.** exit 1 with **4 findings**, ablation **3 of 3**, all ROUTED to hank — §5 |
| SAIRNcash entitlement arms, ARM B first | **DONE.** Both were **ANCHOR-0**, not coverage gaps. 12/12 arms — §6 |
| methodology: measure the population; 56 decode sites; stale rows and footers | **DONE.** 56 → 0 measured both ways; **four** stale footers found where two were named — §4, §6 |
| push without force, confirm landed | **LANDED** — §1, §7 |

---

## 3. Item 1 — the list is derived, and the counterfactual is retired

`python tests/run_cross_tenant_dispatchers_sabotage_probe.py`: **exit 0**, 15
filter mutations all landing in the branch their label names with no foreign arm
red, **0 tripwires derived**.

**RED FIRST:** exit 1, two tripwire arms, both *"a session gate arrived on this
branch and the arm STAYED GREEN"*.

**THE TWO NAMES WERE HARDCODED AND THAT WAS THE DEFECT.** `grd_boq_rates` and
`grd_rounds` stopped being `app: null` **deliberately** —
`api/sd-data-cross-tenant-dispatchers.test.js:647-654` sends a real
`sairngrounds` session and its comment at `:633-646` states the trade in its own
words. The section was asserting a property the suite no longer has, by design.

**THE ARMS ARE NOT DELETED.** `derive_tripwires()` reads every `app: null` unit
out of the suite text and drives a real tripwire for each — today **zero**, and
the count is PRINTED so that is a disclosure rather than a silent clean line.
What makes an empty list honest is **REPLACEMENT COVERAGE**, which is a FAILURE
when it does not hold: `tests/sd_data_grd_session_gate.js` must exist, must name
every `grd_*` member the suite traded away (**derived from the unit**, so a
seventh resource needs gate coverage too) and must assert a real 401
`NO_SESSION`. Measured: all 6 covered, refusal present, control name absent.

**CONTROL, 5 OF 5 CAUGHT** — gate suite missing; dropping one traded resource
(named in the failure); no 401 `NO_SESSION`; a gate suite containing an
**INVENTED** `grd_` name, which must make the arm declare its own name test
non-evidence. **And M1 ends at exit 2 COULD NOT RUN**, *"the baseline is not
green (14 failing)"*. **The expectation was changed to what the mutant PROVES,
which is stronger than what it was written to prove: the trade cannot be
undone**, so replacement coverage is the only thing that can hold the property.

### The pre-fix counterfactual is RETIRED, and re-base was ruled out by measurement

Three candidate pre-repair copies of `tests/app_session_isolation.js` were
driven against current source:

| candidate | result |
|---|---|
| `79854387^` the anchor the control used | 33 ok, exit 1 |
| `4f757c3f^` the `!== 401` repair's parent | 33 ok, exit 1 |
| `2efe796f^` the LATEST pre-repair boundary, nine days closer | 33 ok, exit 1 |

**All three fail at the same arm and it is NOT the predicate:**
`sairngrounds: measured SOME, recorded NONE`. That gate landed 2026-10-07 in
`6a2690be` and **no historical copy can know it**, because the posture map is a
hand-written record of the world when it was written. A later pre-repair commit
is still before 2026-10-07.

**THE PREMISE WAS WRONG, WHICH IS THE FINDING.** A suite carrying a hand-written
record of its subject cannot be replayed against a later subject; it was always
going to break on the first gate that landed afterwards. **The cost is named, not
written off:** the same-reason mutations are no longer *shown* to have been
invisible to the old `!== 401` predicate, and the file header says so at the top.
`counterfactual_retired()` is not a stub — it asserts the retirement reason still
holds (18 literal posture rows, no derivation) and exits **3 COULD NOT TELL**
naming the premise if the table ever becomes derived. `old_form_is_blind()` is
kept as **dead code on purpose**: it is the only written account of how to replay
correctly. **CONTROL, 3 OF 3.** Measured: exit 0, **ALL 13 ARMS PASS**.

---

## 4. Item 2 — and the dispatched figure did not reproduce

`python tests/run_blob_coverage_scope_sabotage.py`: **exit 0, 7 passed, NO
FINDINGS** (was exit 1 with 2 live `data:` sites outside the universe).

**MEASURED BEFORE CLAIMING: the universe is 179 non-test `api/**/*.js` files, 0
outside, and both named sites are IN SCOPE.** cc widened `api_files()`.
**129 is not the new universe — it is the size of the OLD GAP**, confirmed by
restoring the flat walk in the control, which leaves exactly 129 files outside
with 20 non-`storedBlob` `data:` writes among them.

S2 asserts the unscanned region is **EMPTY**, derived from the same walk S1 uses.
**S2b keeps the two sites as a REGRESSION PIN** — they must be inside the
universe, so re-narrowing `api_files()` fails and NAMES them. **S2c** is the
control: an invented `api/` path must not be in the scanned set.
**CONTROL, 2 OF 2 CAUGHT.**

`docs/blob-conversion-coverage.json` **re-pinned with the tool, not by hand**:
unconverted **64 → 58**, converted 33 → 34, BUILT 159 → 171. 58 sites still hand
a raw payload to the store and the tool says so every run: a ratchet is not a
pass.

### Arm 6 of the scope-gate probe now guards BETWEEN source and sink

It detected the guard **per file** — anywhere in the text — and its own comment
admitted it would miss a file that guards one path and leaves another unguarded.
It now requires a guard between the binding of the remote sha and its first use
in a revision walk, in the same function, following the sha **one hop by name**.
**Three states:** a binding that RETURNS the sha is printed as COULD NOT TELL,
and **ARM 6c** requires each such file to still carry the weaker per-file guard,
so the tightening cannot be a net loss. Measured: **13/13**, population 3, 4
could-not-tell all with a per-file guard present.

**THE TIGHTENED ARM WENT RED FIRST AND BOTH REDS WERE ITS OWN DEFECTS:** a range
*string* is not a sink (`'%s..%s'` is built at
`hover_auditor_scope_gate.py:426` and `_have_commit` is checked at `:427`); and
only the **remote** sha needs a guard (tracking both flagged the new-branch
branch at `:424`, which walks `lsha` alone). **And comments are stripped** —
`register_feed_gate.py` was reported unguarded because a comment 26 lines below
says *"merge-base(origin/main, tip) is WHAT THIS PUSH ADDS"*.
**CONTROL, 4 OF 4, against synthetic tools — and F2 is the case the old rule
PASSED:** a guard present but AFTER the sink is now reported with both line
numbers.

---

## 5. Item 3 — four findings, all routed, none fixed

`python tests/run_b12_routed_findings_probe.py`: **exit 1, 8 arms, 4 holding,
4 findings.** **RED ON PURPOSE and registered as such.**

| arm | finding |
|---|---|
| **T16** | `api/sd-data.js:7179` — the caregiver branch copies `SEN_VISIT_EVV_FIELDS` straight over `visitData`, so a SECOND write carrying `clock_in_at` **REPLACES the caregiver's recorded time with no trail**. `checkClockEvent()` refuses only the impossible and explicitly **allows and stores a PAST time**. The file's own comment states the rule it breaks. |
| **T17** | `api/sen-auth.js:263` — `setup` upserts with `merge-duplicates`, so it **rewrites an existing employee's role**, gated only on `caller.role !== 'owner'`. `PROVISIONING_ROLES` is `['owner']`, so an owner can demote the last owner and **provisioning becomes unrecoverable from inside the app**. |
| **T18** | `api/_lib/compliance-rules.js` — **DRIVEN**. `mappable` accepts any non-empty `applies_to_positions` without checking its contents against `STAFF_POSITIONS`, while the next leg of the SAME expression validates `audience`. A requirement declaring `['rn']` is counted MAPPED and `matchAudience()` then returns a **DECIDED `applies: false`** for every real position. |
| **N4** | `api/sd-data-cross-tenant-dispatchers.test.js:577` claims the GRD gate is *"held by `api/sd-data-grd-session-gate.test.js`"*, which does not exist. The coverage DOES exist at `tests/sd_data_grd_session_gate.js` — **true in substance, wrong in its citation**. |

**N1, N2 and N3 are why each T arm is an ASYMMETRY and not a missing feature**,
and all three hold: the append-only correction route writes no clock field;
`set_active` in the same file DOES carry the last-admin guard through
`lifecycle.setActive()`; the same `mappable` expression DOES validate `audience`.
Each defect is one branch missing what its neighbour has.

**ABLATION, 3 OF 3:** each T arm re-run against a COPY carrying its own fix goes
GREEN, so each follows the guard it names rather than a constant. The clone is
never written and that is asserted.

**N4's POPULATION IS MEASURED: 314** coverage claims in comment blocks citing an
`api/`, `tests/` or `tools/` path; **N4b fails below 100**. Three false positives
were removed **structurally, not by a name blocklist**: comments only (the first
five hits were fixture payloads inside STRING literals); comment **blocks**, not
lines (the real finding spans two); and create-then-remove / self-disclosed
citations.

**AND T17 FIRST PASSED BECAUSE OF A COMMENT** — the guard regex matched
`lifecycle.` inside *"Both run through api/_lib/employee-lifecycle.js"*. A
**misreported `file:line`** was caught the same way: comment-stripping moved
T16's citation from `:7179` to `:7137`.

**No `docs/` routing file was written, because `docs/` is fourth's.** The
findings live in the commit message, in the arms and in
`docs/known-red-suites.json`.

---

## 6. Items 4 and 5 — anchors, populations and three stale footers

**SAIRNcash, ARM B first.** Both failing arms were **`ANCHOR-0`**, not coverage
gaps — *a stale anchor and a missing arm look identical in a summary line and
have opposite fixes.* **ARM B** (mutation 5): the anchor predated
`customerId: s.customerId` being added to the verify request. **ARM A**
(mutation 3): the branch became multi-line, and **the one-liner spelling still
exists TWICE** (`:863`, `:990`), so a loosened anchor would have planted in the
wrong branch — worse than ANCHOR-0. Both re-anchored, **measured unique**.
Measured: **12/12 arms, 8 mutations, exit 0**, `sairncash.html` byte-identical.
The other three entitlement suites were driven and are green.

**THE 56 DECODE SITES, MEASURED BOTH WAYS.** `tools/subprocess_decode_check.py`
reported **56 sites across 33 `tests/` files and 0 in `tools/`** — reproducing
cc's b9 figure exactly. **By tool: all 56 belong to that one checker.** `--fix`
closed all 56; re-run measured **0, CLEAN**; every modified path is under
`tests/`; all 33 parse. A sample was **driven**, not just compiled.
`run_two_axis_tier_parser_probe` exits 1 — **and did before the change too**,
confirmed by stashing and re-running.

**THREE STANDING `EXPECTED RED` FOOTERS, WHERE TWO WERE NAMED.** Driving every
suite that carries one found **four**: `sd_data_clock_flags_merge`,
`sairncare_office_manager_role` and **`mar_billing_grant`** (a sixth stale
register row the dispatch did not name) were all green and all printing EXPECTED
RED beside their own `0 failed`. The fourth,
`run_alf_scope_mutation_probe.py:220`, is a **per-mutation message inside working
logic** and was left alone — which is why the count is four and the fix is three.
Each footer is **DERIVED** from the run now, keeping the routing history.

**AND THAT FIX EXPOSED ARM E1.** Moving the rows made E1 fail in all three: it
asserted **unconditionally** that the suite IS in `entries` — *"while it is
deliberately red"*. Same defect class, one layer in. **E1 is symmetric now: red
requires a row, GREEN REQUIRES ITS ABSENCE.** In `mar_billing_grant` the fixed
arm **caught its own row on the first run** — *"this suite is GREEN but still has
an `entries` row, which will swallow the next real failure of this file."*

---

## 7. Four gate refusals, all repaired at cause, nothing overridden

1. **Register feed** — one commit lacked a `no-defect-record:` trailer. Added by
   `git rebase --exec`; **no published history rewritten**, it had never landed.
2. **Generated document** — `docs/traceability-matrix.md`. Regenerated with the
   command the gate printed.
3. **Generated document** — `docs/MASTER-PLAN.md`. Same.
4. **Tier A review** — the gate reads `grd_boq_rates` and `grd_rounds` out of my
   probe, and those **are** Tier A. They appear only as a regression pin and no
   `api/` or `sql/` file was touched — **but "my change is harmless" is exactly
   the judgement the rule takes away from the author**, so the obligation was
   OPENED rather than reasoned away. `tools/tier_a_review_gate.py --open`,
   **assigned to fourth**, with the three things a reviewer should check named in
   the record.

Then a rebase conflict in two **generated** documents and one append-only record.
Resolved the right way for each: **regenerate** `traceability-matrix.md` and
`MASTER-PLAN.md`, take **theirs** for `docs/tier-a-reviews.json` and **re-run
`--open`** so my obligation appends onto the current file rather than being
hand-merged.

---

## 8. Open, with the exact next step

1. **T16 / T17 / T18 → HANK.** `api/sd-data.js:7179` (EVV overwrite with no
   trail), `api/sen-auth.js:263` (last-owner demotion), and
   `api/_lib/compliance-rules.js` (`applies_to_positions` contents unvalidated).
   Each has a RED arm in `tests/run_b12_routed_findings_probe.py` that goes
   green on its own when fixed; `--ablate` shows the fix each one measures. The
   suite stays red with **fewer** findings on a partial fix, which is the
   intended reading.
2. **N4 → HANK.** `api/sd-data-cross-tenant-dispatchers.test.js:577` cites
   `api/sd-data-grd-session-gate.test.js`; the real path is
   `tests/sd_data_grd_session_gate.js`. **A one-line comment correction**, and it
   clears the fourth finding.
3. **The Tier A obligation → FOURTH**, assigned, in `docs/tier-a-reviews.json`.
   48h before anyone may `--takeover`.
4. **The retired counterfactual's REPLACEMENT → CODY.** Do not replay the suite.
   Apply the OLD predicate to the mutant's own refusal — assert `!== 401` accepts
   a 500 and `=== 403 && FORBIDDEN` refuses it — which needs no historical copy
   and no world-state. Smaller and durable.
5. **`tests/run_two_axis_tier_parser_probe.py` is RED and PRE-EXISTING** — one
   arm, *"the NEW six-cell shape parses, raises no row-level problem, and counts
   as migrated"*. **Not touched and not diagnosed in b12**; confirmed red before
   my change. Its register row should be checked against that arm.
6. **`tests/run_scope_gate_unfetched_base_probe.py` carries `# OWNER: cc`** while
   living in `tests/`, which the register's own path rule makes cody's. I
   tightened it as dispatched and left the header alone. **A routing question for
   whoever reconciles the two conventions** — not a code change.
7. **58 unconverted blob sites remain** (`docs/blob-conversion-coverage.json`).
   A ratchet, not a target; the tool refuses to let the number rise.
8. **b11's items that are NOT mine and were not re-verified here:**
   `MIN_TEST_FILES` 370 vs 796 (cc), the
   `tools/sairn_push_gate_hook.py:988-991` comment contradicting its own code
   (cc), `CLAUDE.md`'s *"SAIRN_SEED_GATE=off still works"* line,
   `tests/push_gate/check4_probe.py` and `check7_probe.py` (not_red, exit 3),
   and the 17 `.git`-sentinel suites.

---

## 9. Cleanup

Scratch files under
`C:\Users\marsh\AppData\Local\Temp\claude\…\scratchpad\` are **removed**.
`git worktree list` shows **only the live clone**. Evidence lives in
`docs/known-red-suites.json` and in the commit messages, never in a temp path —
a digest pointing at a temp directory is a citation that expires.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\ec3355ad-083b-4402-a518-3d4e79072c4c.jsonl`

---

*Written before the report, at a point where everything above is committed and
pushed except this file and the three artefacts that follow it.*
