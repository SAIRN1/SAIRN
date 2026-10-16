# Handoff — cody, batch b19, 2026-10-16

**Written BEFORE the report.** Every item below is either landed, or open with
the reason it is open and the exact next step. **Nothing is half-edited.**

**THE SESSION DID NOT START WHERE THE PROMPT ASSUMED, AND THAT IS THE FIRST
THING TO READ.** The dispatch said *"read your own newest handoff and resume
exactly where it says."* The newest handoff on the Drive is
**`SAIRN-handoff-cody-b17.md`** — **there is no b18 handoff, report or digest**,
and `SAIRN-latest-cody.md` was still publishing b17's digest with b18 named only
as the live claim. **b18 had done most of its work and been cut off before
writing anything:** three b18 commits sat unpushed on `main` for 20 hours, with
**two files still uncommitted in the working tree**, and the b18 claim was still
`active`. So b19 began by finishing b18 rather than by starting item 1 — and one
of the two uncommitted files **did not work**, which is §1.

---

## 1. The b18 tail, finished rather than committed as found

`docs/test-file-floor.json` and `tests/run_dead_rule_sweep_probe.py` were
modified and uncommitted. **Measured before touching either:**
`python tests/run_dead_rule_sweep_probe.py` → **EXIT=2**, dying immediately
after printing section I's header.

**THE FLOOR PIN IS HONEST AND WAS RE-VERIFIED, NOT TAKEN ON TRUST.** 808 → 824,
from b18's triaged full-tree run at `c011a287`
(`RAN: 395 JS + 429 PY = 824 files`). `discover()` on the live tree returns
**395 JS + 430 PY = 825** — exactly one more than the run saw, and the one is
`tests/run_window_anchor_ratchet_probe.py`, which b18 added after the run
started. The pin is what the **triaged run measured**; a floor is `count >= pin`
so 824 is the conservative direction.

**AND IT COLLIDED WITH ANOTHER CLONE'S RAISE IN A REBASE.** Another clone had
pushed 808 → **811** from its own run. `824 > 811`, the ratchet only rises, and
824 is the number a triaged run measured — so 824 stands and `previous` now
reads 811, which is what the pin actually replaced. **Resolved by the ratchet's
own rule, not by preference**, and recorded in the file.

**A SEPARATE FINDING IN THAT FILE, worth more than the number:** the 811 version
arrived with `lowered_from_813_why` **absent** — not deleted by a person,
**dropped by `raise_floor()`**, which rewrites the file from its own fixed key
set. So every hand-written key here survives only until the next full-tree run.
Restored, and the hazard is now written into the file as
`the_generator_drops_keys_it_does_not_know`.

### The probe: b18's change left it at exit 2, and would have read the wrong number if it had not

`tools/dead_rule_sweep.py` refuses to run outside
`tools/git_config_isolation.py`. b18 wrapped the two **subprocess** call sites.

* **THE SWEEP IS DRIVEN THREE WAYS AND ONLY TWO HAVE CALL SITES.** Section I
  calls `D.make_sandbox()` **in-process** — `import dead_rule_sweep as D` — so
  `require_isolation()` fired inside the interpreter, where there is no call
  site to wrap. **Fixed by re-execing the WHOLE PROBE under the real wrapper
  once, at the top.**
* **AND THE WRAPPED CALLS SUBSTITUTED ONE QUANTITY FOR ANOTHER UNDER THE SAME
  NAME.** The wrapper's exit code is its verdict on `.git/config` and
  `.git/worktrees` — 0 UNCHANGED, 1 CHANGED, 2 COULD NOT SNAPSHOT — and it says
  so in its own output: *"THIS IS A FINDING ABOUT THE COMMAND, whatever the
  command itself returned"*. `run()` wrapped and returned `r.returncode`, so
  every arm reading `rc` was reading *did git admin state change* where it meant
  *what did the sweep exit*. F9a's `rc in (0, 1)` passes on either. The re-exec
  recovers the inner code through `--rc-file`; a wrapper verdict of 1 is its own
  exit-1 failure with a named reason; a missing rc-file is exit 2.
* **F3's `Popen` IS DIRECT AGAIN, DELIBERATELY.** That arm KILLS the process to
  prove the reap handles a dead owner, and killing a wrapper orphans the sweep
  it launched.
* **NOT `os.environ['SAIRN_GIT_ISOLATION'] = '1'`** — that is the guard switched
  off by the thing it guards, in a file whose section G exists because a control
  doing what it checks for is this probe's own history.
* **NEW ARM G0** asserts `SAIRN_GIT_ISOLATION=1` by name. The refusal banner
  contains the string `DEAD RULE SWEEP`, so **F2 — the paired positive whose job
  is to prove the sweep STARTED — passed on the message saying it would not.**

`EXIT=0`, **84 passed / 0 failed**, wrapper: *"wrapped command exit 0 /
UNCHANGED"*.

---

## 2. The five dispatched items

### ITEM 1 — arm Z's `else`, and the ablation came back RED

`tests/sd_data_blob_scope_ten_routed_sites.js:347` read
`if (d.id !== undefined && s.idMustSurvive) { ok(...) }` with **no `else`**. The
one state the arm exists to catch emitted neither `ok` nor `bad`. **It did not
go red, it disappeared.**

**THE FIX IS SPLITTING THE PREDICATE**, not bolting on an `else`:
`s.idMustSurvive` selects the POPULATION, `d.id !== undefined` is the
ASSERTION. Folding them together is what made a failing assertion
indistinguishable from a site the arm does not cover.

**BOTH LEGS, ONE SESSION.** Driver committed at `docs/b19-logs/ablate_arm_z.py`,
following the b16 precedent:

```
PRE-FIX  BASELINE  EXIT=0  16 passed, 0 failed   arm Z ok:1 FAIL:0
PRE-FIX  ABLATED   EXIT=0  15 passed, 0 failed   arm Z ok:0 FAIL:0  SILENT
POST-FIX BASELINE  EXIT=0  16 passed, 0 failed   arm Z ok:1 FAIL:0
POST-FIX ABLATED   EXIT=1  15 passed, 1 failed   arm Z ok:0 FAIL:1  CAUGHT
```

The pre-fix leg **reproduces fourth's b25 numbers exactly**.

**WHAT IS ABLATED IS THE SUBJECT, NOT THE ARM.** In a COPY of `api/`, the
`sd_slabs` write branch becomes `storedBlob(payload, ['id'])` — the plausible
scope fix the arm was written to catch. Removing the ARM can only reduce the arm
count; it cannot make the arm red. The control refuses the run unless the
unmutated copy is exit 0 **with arm Z present AND passing**. The branch anchor
is bounded by the next branch guard and refuses unless
`storedBlob(payload, [])` occurs **exactly once** inside it.

**THE PRE-FIX LEG IS DELIBERATELY NOT COMMITTED**: it needs a literal copy of
the removed one-condition arm, and in b17 an assertion in this repo was
satisfied by a COMMENT inside the function it tested explaining what the code
*"used to read"*. The numbers are the record; the scratch driver was
`<scratchpad>/armz_before.py`.

### ITEM 2 — the blob-scope row is RECOVERED, and the red was never wrong

**Exit 0, 16 passed / 0 failed**, driven alone in the live clone **twice** — at
the b18 tip and again after rebasing onto 17 commits from the other clones,
because a green on a stale base is the exact defect this row records.

The old row recorded 3 passed / 13 failed in a real `git clone --local` at
`040cbfd9` and **every isolation property it claimed is true.** The premise
under it was false: `git merge-base --is-ancestor 8627f4e4 9f04ad39` → **NO**,
and `... 8627f4e4 040cbfd9` → **NO**. hank's conversion landed at 08:09; the
suite was committed at 08:11 on a parallel branch. **A correct measurement
produced a wrong diagnosis.** The file's own header said *"ALL TEN ARMS ARE RED
UNTIL hank CONVERTS THE SITE"* and was never true of a tree it was run on.

### ITEM 3 — the control arm reads off `failed.length`

Its message said *"so the ten failures above"* and printed it on a run with
**zero** failures above, in the one arm whose job is to make the count above
readable. It now says something different and true when the count is zero.

### ITEM 4 — the b24 F1 re-anchor, and the rot is exit 1 now

`tests/run_b14_leg_aftercare_probe.py` extracted its subject through
`const acKey = ('AC-'...`. hank replaced the derivation; the anchor stopped
matching; the probe exited **3 COULD NOT RUN** — and
`docs/known-red-suites.json` recorded it as `exit_code: 1`,
`expected_red_scope: "ARM 1 ONLY"`. **An exit 3 is neither.** No sweep prints a
FAIL line for it, so the only arm measuring a silent-overwrite defect on a
bereaved family's records was off and the register read as understood.

* **RE-ANCHORED ON A STRUCTURE.** The server half is the **balanced block** of
  the `leg_aftercare` guard, from the `acEsc` helper to the `}` that closes the
  guard — no character budget to outgrow. Both halves now extract their
  **helper** too (`legAcEsc`, `acEsc`), which is why the old one-expression
  anchor could not simply be re-aimed: the extracted expression would throw on
  an undefined identifier. Arm **0e** asserts both blocks came back balanced,
  non-empty and mentioning `const acKey`; node re-parses them; the liveness
  control requires a key to come out.
* **THE ROT OF THIS FILE'S OWN ANCHOR IS EXIT 1, NOT EXIT 3, BY OWNERSHIP.**
  **NEW ARM 3, failing-first in both subjects** — the probe re-runs itself
  against renamed copies through two new injection points: **3a** unmutated
  copies at new paths → exit 0 (so *"it exits 1"* is not satisfied by a probe
  that is red anyway, and the injection points are proved inert); **3b** server
  anchor renamed → exit 1; **3c** no line STARTS with `COULD NOT RUN:` and the
  anchor and file are named; **3d** CLIENT anchor renamed → exit 1 and named;
  **3e** the server anchors still passed in that run, so 3d was surgical.
* **TWO DEFECTS IN CONTROLS, FOUND BY DOING THIS.** (1) The liveness control
  asserted `startswith('AC-')`, which a correct **`ACX-`** key FAILS — the arm
  whose job is to prove the extraction ran would have gone red on the fix.
  (2) Arm 3c first read `'COULD NOT RUN' not in output` and **failed on its own
  subject's prose**: the child's summary explains *"this is not a COULD NOT
  RUN"*. A scanner looking for a verdict inside text that DISCUSSES the verdict
  finds the discussion.

`EXIT=0`, **18 arms, 0 failed.** Row moved to `recovered`.

### ITEM 5 — two misclassifications, observed by fourth and never driven

**NEW: `tests/sd_data_not_provisioned_misclass.js`, exit 1, 12 passed / 2
failed.** A1 and B1 red on purpose, routed in
`docs/2026-10-16-cody-b19-notprovisioned-misclass-routed-to-hank.md`. Line
numbers re-derived at this batch: the guard fourth cited as `:14347` is
**`:14445`**.

| arm | measured |
|---|---|
| **A1** `alf_op_audits`, Tier A, injected 400 + `{"code":"23514"}` | **HTTP 503 `NOT_PROVISIONED`** — a row refused on CONTENT reported as a missing table, operator told to run a migration already applied |
| A0 control, store healthy | HTTP 200 `ok:true` |
| **A2** counterfactual, COPY of `api/`, one call site → `notProvisioned(res, w, …)` | **HTTP 400 `ROW_REFUSED`**, A1 goes green |
| **A3** same copy, genuine 404 | **still 503 `NOT_PROVISIONED`** — the fix does not trade one wrong answer for another |
| **B1** `mech_site_assets`, injected 400 + `{"code":"42703"}` | HTTP 200 `{"ok":true,"data":[],"provisioned":false}` — **byte-identical** to the 404 case |
| B0 / B2 controls | `provisioned:true` with the board / genuine 404 → `provisioned:false` |

**POPULATIONS MEASURED BY THE SUITE ON EVERY RUN, NEVER QUOTED:** 318 guards of
the form `X.status === 404 || X.status === 400` — **88** route through
`notProvisioned()`, **67** answer a raw 503, **151** answer a raw HTTP 200
`provisioned: false`, 12 other. **The 151 independently reproduces the figure
the dispatch named.** Arm P3 refuses unless all three answers are represented;
P4 asserts both subjects are **members**.

**WHAT B1 DOES NOT CLAIM.** The branch's own comment at `:2846-2850` argues that
a registry provisioned before the AIM Act columns existed should be told to
re-run the idempotent migration, **and that argument is correct and is not
disputed.** B1 asserts only that the two states **differ** in the answer.

**AND THE SUITE'S FIRST VERSION HAD THE DEFECT THE METHODOLOGY ITEM IS ABOUT.**
`branchOf()` bounded each branch at the next `if (resource === ` terminator and
**overran by a factor of 130** — 23,575 characters for a 180-line branch — so
the slice contained other branches that **do** call `notProvisioned()`, and arm
**P5, whose entire job is to assert the defect has NOT already been fixed,
reported that it had been.** A precondition arm telling the suite to retire
itself over a defect that is still shipped. Balanced-brace bounded it is 11,146
characters, and **new arm P1b** asserts neither slice names the other branch's
resource.

### The Tier A half of item 5

**OBLIGATION OPENED AND ASSIGNED, not left first-come:** `alf_facility`,
`alf_op_audits`, `leg_aftercare`, `mech_site_assets`, opened
**2026-10-16T12:24:12Z**, **ASSIGNED TO cc**. `alf_facility` is there because
the suite MOCKS its threshold read so the `alf_op_audits` branch reaches its
guard; **no assertion is made about it** and the record says so. Six things a
reviewer should check, hardest first, are on the record. **Reviewer must not be
cody.**

**ON THE FRESH-OBLIGATION QUESTION, measured rather than assumed absent:**
`--list` shows **five** obligations assigned to cody and the **newest was opened
2026-10-06T07:56:17Z, 243h ago**. **Nothing fresh has been opened against this
session since b18.** The five are all past 48h and `--takeover`-able by anybody.

### METHODOLOGY — convention 36

`docs/2026-09-13-cross-domain-disciplines.md` gains **36. A CHECK'S OWN ROT IS
NOT BIASED TOWARD RED — and the exit code it answers with must be chosen by
OWNERSHIP, not by convenience.**

Item 8 says nothing announces the day a check stops testing anything. **36 is
the missing half: when it does stop, it does not announce it by going red.**
Three instances, all measured this batch, and **two of the three read as good
news** — an arm that VANISHES, a probe that EXITS 3 where no sweep prints a FAIL
line, and a precondition arm that REPORTS THE DEFECT ALREADY FIXED.

**THE REMEDY IS AN OWNERSHIP RULE.** An absent tool or an unreadable subject
stays exit 2/3 COULD NOT RUN — **PR §1.11 unchanged, and 36 only ever moves a
verdict from the quieter state to the louder one.** But an anchor that no longer
matches a file that reads perfectly well is a defect in the **check**, and must
be **exit 1 with the anchor named**, plus a **driven** arm that renames the
anchor in a COPY with an unmutated-copy control first.

**A TERMINATOR IS A GUESS ABOUT WHAT COMES NEXT; A BALANCED BRACE IS A PROPERTY
OF THE BRANCH ITSELF.** 35 clause 2 says a fixed line count reaches into the
next construct; a terminator pattern is the same defect **wearing a structural
costume**, and it fails further — a line count overruns by a bounded amount, a
missing terminator overruns until the next match anywhere in the file.

**MEMBERSHIP ASKED AND ANSWERED:** 36 is a **TWELFTH member** of the cannot-fire
group, **admitted on (a) and (b) rather than on (c)** — (c) fired and produced a
false clean, which is 35's shape and stays outside the group. Said in the
group's own note, because admitting an item on its strongest instance while
quietly counting its weakest is how that denominator stops meaning anything.
**Counted before assigning: 36 headings, 1-36, no gap, no duplicate, and no
other session added a 36 while b19 ran.**

**AND THE PROMOTION-ROW FIGURE IN `docs/METHODOLOGY.md` WAS WRONG**, corrected
by convention 35 clause 3 rather than silently. The 2026-10-15 block says
*"18 promotion rows in the table above"*:

```
3b5fabb50 -> 23 rows     # the commit that introduced that block
HEAD       -> 23 rows     # before this edit added the 36 row
```

**The subject did not move, so the two numbers are two predicates over the same
bytes and the published one is wrong.** 24 now. The old block is carried
unchanged beneath the new one, including its 18.

---

## 3. Verification at the landed tip — exit codes read from `echo "EXIT=$?"` on its own line, never from a pipeline

```
EXIT=0  node tests/sd_data_blob_scope_ten_routed_sites.js   16 passed, 0 failed
EXIT=0  python tests/run_b14_leg_aftercare_probe.py         18 arms, 0 failed
EXIT=1  node tests/sd_data_not_provisioned_misclass.js      12 passed, 2 failed
                                                            (A1 and B1 ONLY)
EXIT=0  python docs/b19-logs/ablate_arm_z.py                CAUGHT
EXIT=0  python tests/run_dead_rule_sweep_probe.py           84 passed, 0 failed
EXIT=0  python tests/run_known_red_probe.py                 0 failure(s)
EXIT=0  python tools/master_plan.py --check
EXIT=0  python tools/tooling_inventory.py --check
EXIT=0  python tools/traceability_matrix.py --check
EXIT=0  node --check on every changed JS file
```

**All four suites were re-driven AFTER the second rebase**, not only before it.

---

## 4. Claims and overrides

**The claim was taken BEFORE any work and it took three attempts to publish, for
a reason worth knowing.** `sairn_claim.py claim` **cannot push with a dirty
working tree** — `git rebase` refuses outright, so no push is ever attempted and
the tool correctly reports **NOT CLAIMED**. The tree was dirty with b18's two
leftover files, then with `docs/scrutiny-flags.json` rows that the claim
commit's own scrutiny pass had just written. **Each retry is a retry and adds no
second entry**, exactly as the tool says.

* **claim:** `tests` (`cody-1792149459`, taken **2026-10-16T11:17:39Z**)
* **BOTH CODY CLAIMS ARE RELEASED. CORRECTED AFTER THIS FILE WAS FIRST
  WRITTEN, AND THE OLD TEXT IS NOT LEFT STANDING BECAUSE IT WOULD BE A FALSE
  STATEMENT ABOUT LIVE STATE.** This paragraph first said both were *"still
  active and deliberately not released"*, on the reasoning that `release`
  takes a subject rather than an id and would take the live b19 claim with the
  stale b18 one. **That was the wrong call and the premise was also wrong in a
  useful way:** taking both IS the desired outcome, because both are cody's
  and both are finished — and the cost of leaving them is that two stale
  claims on `tests` block every other clone from the directory for four hours
  each, which is the thing the claim system exists to prevent, pointed the
  wrong way. `python tools/sairn_claim.py release tests` released **both**, by
  name, in one commit — b18's `cody-1792078195` and b19's `cody-1792149459` —
  and reported *"pushed and verified on origin/main"*.
  **NO CLAIMS HELD BY CODY AFTER THIS BATCH.**
* **overrides: NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no
  `SAIRN_SEED_GATE`, in any form.
* **boundaries:** no `api/`, `sql/` or `tools/` file edited — `api/` is COPIED
  for every counterfactual and the live tree holds no modification to it. The
  three generators were **RUN, not changed**. No hook restored.
  `.claude/settings.json` never committed. No auditor clone entered.
* **committer:** `fx <fx@example.invalid>`, this clone's local config, unchanged.
* **push:** no `--force`, in any form.

---

## 5. Open — every item, why it is open, and the exact next step

### 5.1 → hank. The two call sites, and the fix is proved

`docs/2026-10-16-cody-b19-notprovisioned-misclass-routed-to-hank.md`.
**NEXT STEP:** replace the raw 503 at `api/sd-data.js:14445` with
`await notProvisioned(res, w, <the same message>)` — A2 and A3 already drive
exactly that change on a copy and both pass. Then decide what distinguishes a
42703 from a 404 at `:2851`; a field beside `provisioned: false` satisfies B1.
**Re-derive both line numbers**; they moved +98 between fourth's measurement and
this one.

**AND A THIRD GUARD NAMED BUT NOT DRIVEN:** `api/sd-data.js:14316`, the
`alf_op_audits` append-only existence check, has the same shape, so a 23xxx
there also renders as *"not set up yet"*.

### 5.2 → cc. The Tier A obligation opened today

`alf_facility`, `alf_op_audits`, `leg_aftercare`, `mech_site_assets`, opened
2026-10-16T12:24:12Z. **NEXT STEP:** `python tools/tier_a_review_gate.py --list`
and read the six checks on the record. **cody cannot discharge its own.**

### 5.3 → ANYBODY. cody's five overdue Tier A obligations

All five are past 48h — the newest is **243h** old — so `--takeover` applies to
any of them. They are **not fresh** and nothing new was opened against cody in
b18 or b19. Measured, not assumed.

### 5.4 → CODY. The 151 and the 67 are NOT converted and that is a decision

The populations are measured on every run of the new suite; **which siblings
carry real risk is a per-branch judgement about what a 400 can mean on that
table and it belongs to whoever owns `api/`.** Converting 218 branches on a
measured count would be exactly the byte-identical-is-not-safe-in-context
mistake (cross-domain item 7).

### 5.5 → CODY. `docs/test-file-floor.json` will lose its explanatory keys

`raise_floor()` rewrites the file from its own fixed key set, so the four
hand-written keys there — including the restored b14 lowering note — vanish on
the next full-tree raise. **NEXT STEP:** either teach `raise_floor()` to carry
unknown keys through, or move the durable half out of the JSON. `tools/` is
cc's, so the first option is a routing and not a cody edit.

### 5.6 → CODY. The b17 and b18 carry-overs NOT touched in b19

Named so they are not mistaken for done: **§6.4** (`tooling_inventory.py
--hooked` fails open on an empty hook set, cc), **§6.5** (the two claims probes'
retyped-task fixtures, cc first then cody), **§6.7** (`sairnbuild.html`'s bare
`catch(e){}` in `st()`), **§6.8** (six named `recurrence_open` register
records), **§6.10** (`run_capa_fields_probe.py` is 200-420s because
`with_register()` rewrites 2.46MB per arm), **§6.11** (b16's three deterministic
ablation arms). **Every one of these is still exactly as b17 left it.**

---

## 6. Scratch, and one thing cleaned up

**`git worktree remove`d:** b18's `wt18` was still registered against this
clone at `c011a287`. Removed and pruned — a stale `.git/worktrees` entry makes
the NEXT `worktree add` refuse, in a directory `git status` never shows.
`C:/Users/marsh/AppData/Local/Temp/gate-probe3-17976` is **not mine** and was
left alone.

**Scratch:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\0f5c2c46-aab3-44b3-997b-47c60e2fbcce\scratchpad\`
— logs, the commit messages, `armz_before.py`, `move_rows.py`, `add_row.py`.

**The 109 files / 247 MB that `rm` has refused across b14–b16 are still at the
b16 path** and are listed in `SAIRN-handoff-cody-b16.md` §6. `cfapi/` and
`clone46/` are nearly all of it. **Nothing in the repo or on the Drive depends
on any of them.**

---

*Written before the report, at a point where everything above is committed
except this file and the three artefacts that follow it.*
