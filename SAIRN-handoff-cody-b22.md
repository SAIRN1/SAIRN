# Handoff — cody, batch b22, 2026-10-17

**Written BEFORE the report**, at a point where **everything is committed except
this file and the two artefacts that follow it**. Nothing is half-edited: the
index row is built WHOLE with its pipe count asserted either side, the shards
are regenerated and `--check`ed CLEAN, the re-aimed suite and the new suite both
drive end to end, and every gate below was **re-run after the rebase** because
24 commits from the other clones landed underneath this work.

**THE HEADLINE: TWO ARMS IN TWO DIFFERENT FILES WERE SATISFIED BY SOMETHING
OTHER THAN THE THING THEY WERE CHECKING, AND BOTH WERE FOUND BY ABLATION IN THIS
ONE BATCH.** In `tests/sd_data_not_provisioned_misclass.js`, arm P5 passed on
hank's *explanatory comment* naming `notProvisioned()` after the call itself was
reverted. In `tests/sairnfreedom_tax_entity_facts.js` — my own new file, written
hours later — arm B6 passed on a *constant's `note` field* after the disclosure
it was checking had been deleted. **Same mechanism, two files, one batch, one
day after convention 36 was written about exactly this.** Neither was findable by
reading; both fell out of removing one layer and asking which arm went red.

**AND THE SECOND HEADLINE IS THAT MY OWN CLAIM'S PREMISE WAS FALSE.** I claimed
a *"shared multi-location multi-brand data model scoping doc"* on the strength of
open-work row **356**, which says item 4 is **NOT STARTED**. It landed
**2026-09-16** and **row 355 — one row below the one I read — says so.** The
design is the 65-line comment header of `api/_lib/location-scope.js` and it is
better than a fresh pass would have been.

---

## 1. Committed state

| | |
|---|---|
| commits | **`c2f8c94f`** → rebased to **`949decefe`** `feat(sairnfreedom): the canteen's exempt entity is CONFIGURABLE…` plus the earlier claim commit |
| claim | `platform`, taken **BEFORE any work**, published to `origin/main`. **STILL HELD as this file is written** — §5 |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, in any form |
| boundaries | **NO `api/`, `sql/` or `tools/` file edited.** Twelve tools were **RUN** (§4). No hook restored. `.claude/settings.json` never committed. No auditor clone entered |
| HOLD honoured | **`api/sd-data.js:14445`, `:2851` and `:14316` are HANK's and were READ ONLY.** No `api/` file is in the diff; the suite **COPIES** `api/` for its ablation and never writes it, asserted by `git status --porcelain` before and after |
| Stripe | **NO Stripe work of any kind.** No object created, no Vercel environment read, no dashboard opened. SAIRNcash is HELD and was not touched |
| rebase | **24 commits** from the other clones landed under this work. **Rebased cleanly, then every gate re-run** — the rebase is a segment boundary, not a formality |
| committer | `fx <fx@example.invalid>`, this clone's local config, unchanged |

**Files in the work commit — ten, and two of them are generated:**

```
sairnfreedom.html                                   +144/-1   the field, the reporter, the limbs
tests/sairnfreedom_tax_entity_facts.js              +249      NEW, 26 arms, exit 0
tests/sd_data_not_provisioned_misclass.js           +203/-77  re-aimed: A1/B1 -> regression, C1 new red
docs/known-red-suites.json                          +8/-6     scope rewritten, tail CORRECTED
docs/2026-09-17-sairnfreedom-tips-tax-treatment.md  +163      §12.6a/b closed, §13 + §13.5
docs/2026-10-17-cody-b22-multi-location-brand-data-model.md  +379  NEW, the scoping doc
docs/SAIRN-OPEN-WORK-INDEX.md                       +1        ONE row, built WHOLE
docs/open-work/ACTIVE.md, platform.md               generated, regenerated
docs/tier-a-reviews.json                            +5/-2     cc's orphaned anchor sha reseated
```

---

## 2. Item by item

### ITEM 1 — the exempt entity is configuration, and `both` is why one field was not enough

`TAX_ENTITIES` carries **c19 / c7 / both**. The research for it was already
done and recorded; what was missing is that **nothing in the app or the document
could represent the answer**. Pub. 3386 says a veterans' organisation running a
bar, restaurant or canteen for members *"may be recognized as tax exempt under
IRC 501(c)(7)"* and that such clubs *"are often operated in conjunction with IRC
501(c)(4) veterans' organizations"*.

**`both` IS THE SHAPE THAT MATTERED.** It is where *"whose employee received
this tip"* has **two** answers, and that answer decides **which return** the
employer-side figures land on. A design storing one entity collapses two
employers into one silently.

**THE DEFAULT IS `''`, NOT `'c19'`,** and that is the load-bearing decision: an
unset structure reads **UNKNOWN**, because a defaulted (c)(19) is a silent
assumption of precisely the thing the field exists to stop assuming.

**AND THE §45B FLOOR IS NO LONGER A CONSTANT**, which closes §12.6b's
precondition in code rather than leaving it as a warning. `SEC45B_LIMBS` carries
**both** limbs of §45B(b)(2) — `$5.15` frozen at *"in effect on January 1,
2007"* for food and beverage, the **current** federal minimum (`$7.25` today) for
beauty service — each with the Form 8846 sentence it came from and a `frozen`
boolean. `taxEntityFacts()` returns `limb` and `floor` **together**, so the
figure cannot be read without the population it applies to.

**NOTHING COMPUTES A CREDIT AND §7.3 IS UNCHANGED.** Read that as the boundary,
not as caution: reaching §45B requires the post to first be in the UBIT state it
is trying to stay out of.

### ITEM 2 — the reporter was DORMANT CODE, and my own Guardian pass found it

**§13.3 of the tips document is true and was not sufficient.**
`taxEntityFacts()` was driven in all four states, every arm green, and
`grep -n "taxEntityFacts" sairnfreedom.html` returned **the definition, a
mention inside its own comment, and nothing else.**

**A configurable structure whose effects are invisible is the assumption it
exists to remove, one step later** — the post answers the question, nothing it
can see changes, and the next session reads a field with no evidence anybody
uses it.

**RESOLVED BY WIRING, AND THE CHOICE WAS REAL.** Deleting it would have made
§12.6b's *"it is no longer only a warning"* **false in the same commit that
wrote it**. So `sfRenderTaxFacts()` paints it into Post Profile from
`sfRenderPost()`, **the unknowns as prominently as the determinations**, and the
unset state renders the unknown as the *whole* output — **never a blank box,
because a blank box reads as "no issue here"**.

### ITEM 3 — the not-provisioned suite's subject was FIXED, so the suite said so

**hank landed BOTH routed call sites and ten more.** Measured by the suite on
every run, never quoted: **318 guards / 88 via `notProvisioned()` / 67 raw 503
→ 319 / 99 / 57.** Eleven guards converted where two were routed.

**WHAT WENT RED WHEN THE FIX LANDED WAS THE RIGHT THING.** Arm P5 existed to
assert *"the branch does NOT already route through `notProvisioned()`, so A1 is
measuring the shipped answer"* — and it failed the moment the fix landed,
**telling the suite its subject had changed instead of letting A1 go green and
read as a defect that never existed.**

**A2 IS AN ABLATION NOW, NOT A COUNTERFACTUAL, AND IT IS STRICTLY STRONGER.**
It **reverts** hank's call site in a COPY of `api/` and requires **A1 AND P5 to
come back RED**. The old form proved the fix *would* work; this one proves **A1
can still fail**, which is the only thing that makes a green A1 evidence.

**AND IT IMMEDIATELY CAUGHT A DEFECT IN THE RE-AIM ITSELF.** The first inverted
P5 read `OPA_BRANCH.indexOf("notProvisioned(") >= 0`; with the call reverted,
**A1 went RED and P5 STAYED GREEN**, because the branch still contains the words
`notProvisioned()` inside hank's own explanatory **comment**. P5 now strips line
comments and requires an invocation **with arguments**.

**A3 MOVED FROM THE CHILD TO THE PARENT**, because in the ablated copy it passes
**vacuously**: a raw 503 answers 503 for every input including a real 404. An
arm that cannot distinguish the fixed case from the reverted one is not an arm.

**C1 IS THE NEW RED ARM AND IT CLOSES A GAP b19's OWN ROUTING NAMED.** b19 said
in terms: *"The existing-row read two guards earlier has the same shape and is
not driven here… Named rather than asserted."* hank converted the UPSERT guard
and left that one; measured, the branch now holds **exactly one** raw 503 and it
is that guard. **The injected code is 42703 and not 23514 on purpose and that is
not a softening**: a CHECK violation fires on a WRITE, this guard sits on a
SELECT, so the plausible 400 here is an UNDEFINED COLUMN.

### ITEM 4 — the register row had a SECOND defect, older than this batch, in the field the tool actually compares

`run_all_tests.py` builds a FAIL line's tail from **`out[-1]` — the suite's LAST
PRINTED LINE**. `known_red_check.py` classifies a row by comparing that,
digit-normalised, against the row's own `tail`. **This row's tail has been an
ARM LIST since b19** and this suite's last line is its closing expected-red
paragraph. **They never matched.**

**MEASURED, NOT REASONED:** a fixture log carrying the real FAIL line reported
**`CHANGED (1)`** before the fix and **`KNOWN (1)`** after.

**A ROW REGISTERED WITH A TAIL THE RUNNER CANNOT PRODUCE IS WORSE THAN AN ABSENT
ROW.** Absent reads NEW and gets looked at. CHANGED reads as *"a second defect
is hiding inside an entry that says this file is expected to fail"* — and the
**entry** is the thing that is wrong.

### ITEM 5 — the scoping doc, and the design that already existed

`docs/2026-10-17-cody-b22-multi-location-brand-data-model.md`. **No
implementation, by decision.** §3 of that doc is the argument.

**Re-derived at HEAD rather than quoted, and three figures had moved:**
`dnt-rollup` **27 → 30** arms; the `'LOC-DEFAULT'` literal at **40** sites while
the JS constant is defined in exactly **one** module; `brandId`/`brand_id`
**0** times in all **22** `*.html` files. **112 arms green across the six
location suites.**

**THREE ROLL-UP SHAPES NOW, NOT TWO**, and the third is named nowhere including
in the module comment: `sairnfreedom.html`'s `buildDistrictReport()` buckets per
**ENTITY across an INSTALL boundary by signed JSON**, where the other two cross a
`group by`. **It exists because a district does not own its posts' rows** — so
*the roll-up shape is a function of who owns the rows*, not of how many axes
there are.

### ITEM 6 — cc's Tier A anchor sha, reseated. ITEM 7 — this file. ITEM 8 — the push, §6

---

## 3. The two arms that were satisfied by the wrong string

**This is one finding in two files and it is the reusable part of the batch.**

| file | arm | what satisfied it instead | found by |
|---|---|---|---|
| `tests/sd_data_not_provisioned_misclass.js` | P5 | hank's **comment** naming `notProvisioned()`, after the call was reverted | A2's inverted ablation |
| `tests/sairnfreedom_tax_entity_facts.js` | B6 | `TAX_ENTITIES.both.note`, which independently contains *"TWO EMPLOYERS ARE POSSIBLE"*, after the two-employer **unknown** was deleted | L1 of the five-layer ablation |

**Both arms were GREEN on the real tree and both were worthless.** Neither was
visible by reading the assertion, because in each case the assertion is true —
of a different string than the one the arm exists to check. **The thing that
separated them is identical in both: remove the layer, see whether the named arm
goes red.** Not "does the suite still pass", which would have cleared both.

**THE FIX SHAPE IS ALSO THE SAME: assert on the STRUCTURE the thing lives in,
not on the rendered or concatenated text.** P5 strips comments and requires an
invocation **with arguments**. B6 asserts on the `unknowns` **list**, requires it
to reach the rendered unknowns block, and **B6b requires the two single-entity
shapes NOT to carry it** — so a disclosure pushed unconditionally fails too.

**AND IT RECURRED ONE BATCH AFTER CONVENTION 36 WAS WRITTEN ABOUT IT.** Writing
the convention down did not stop it; the ablation did. That is the argument for
cross-domain item 12 being a standing practice rather than a documented one.

---

## 4. Verification — exit codes from `echo "EXIT=$?"` on its own line, never a pipeline

**Every line below was re-run AFTER the rebase.**

```
EXIT=0  node tests/sairnfreedom_tax_entity_facts.js        26 arms, 0 failed
EXIT=1  node tests/sd_data_not_provisioned_misclass.js     15 passed, 1 failed -- C1 ON PURPOSE
EXIT=0  Check 0a, sairnfreedom.html                        2/2 blocks, PARSER-based extraction
EXIT=0  node --check tests/sairnfreedom_tax_entity_facts.js
EXIT=0  node --check tests/sd_data_not_provisioned_misclass.js
EXIT=0  python tools/open_work_shard.py --check            CLEAN, 814 rows byte for byte
EXIT=0  python tools/tier_a_review_gate.py                 obligation OPEN and covering
EXIT=0  python tools/md_table_check.py                     0 malformed, 0 uncheckable
EXIT=0  python tools/known_red_check.py --from-run <fix>   KNOWN (1), was CHANGED (1)
EXIT=0  python tests/run_known_red_probe.py                0 failures
EXIT=0  python tools/sairn_app_map_check.py                17 files, 17 rows
EXIT=0  python tools/nav_panel_check.py sairnfreedom.html
EXIT=0  python tools/div_balance_check.py sairnfreedom.html
EXIT=0  python tools/sairn_reachability_check.py sairnfreedom.html   clean
EXIT=0  python tools/sairn_strict_args_check.py sairnfreedom.html
EXIT=0  python tools/sairn_dead_button_audit.py sairnfreedom.html    A/B/C1/C2/D1/E all 0
EXIT=1  python tools/index_duplicate_check.py              3 pairs -- PRE-EXISTING
EXIT=1  python tools/tooling_inventory.py --standing-doc-sizes   8 docs -- PRE-EXISTING
```

**THE ABLATION, 5 OF 5 CAUGHT BY A NAMED ARM, per arm and not per exit code:**

```
L1  the two-employer disclosure                    -> B6
L2  the UNSET branch's "not defaulted" sentence    -> A3
L3  the limb travelling with the floor             -> C[c19], C[c7], C[both], D2
L4  the two limbs' floors made equal               -> P2, P3
L5  the frozen/unfrozen distinction collapsed      -> P2, P3
```

**Driven on a COPY of `sairnfreedom.html` in a temp directory.
`git status --porcelain` identical before and after — the live tree was never
written, and that is asserted rather than intended.**

**STRUCTURE MEASURED BOTH WAYS:** `docs/SAIRN-OPEN-WORK-INDEX.md` **851 → 852**
table rows and **1,006 → 1,007** lines; the new row is **8 pipes**, like every
other, and **ONE physical line**; line 355 and the row that followed it are
**byte-identical** afterwards, asserted in the inserter.

**AND THE 114-LINE CHURN IN `docs/open-work/ACTIVE.md` WAS PROVEN TO BE A
REFLOW, NOT SWEPT-IN WORK.** Normalising the `platform.md:NN` citations and the
counts leaves **0 lines only-removed and exactly 1 only-added — mine.** One
inserted line renumbers every subsequent citation; the diff shape was checked
before committing rather than explained afterwards.

**THE TWO EXIT-1s ARE PRE-EXISTING AND MEASURED.** `index_duplicate_check` names
the same three pairs b21 measured — SAIRNgrounds 144/145, Tooling 255/257,
Platform 295/299 — and `docs/SAIRN-OPEN-WORK-INDEX.md` was not modified at HEAD
by anybody else this batch, so the result is unchanged by construction.
`--standing-doc-sizes` names **eight** documents over the ceiling, up from the
seven `CLAUDE.md` records.

**AND ONE OF THOSE EIGHT IS A GENERATED SHARD, WHICH IS WORTH SOMEBODY'S
ATTENTION:** `docs/open-work/platform.md` is **844,983 bytes**. The shards exist
to make a 2.4MB index readable by app, and **the platform shard has itself grown
past the ceiling the sharding was meant to solve.** Not mine to fix; named so it
is not discovered again.

**THE DERIVED-DOCS GATE REFUSED THE FIRST PUSH AND IT WAS RIGHT.** The new suite
is a test file, so `docs/traceability-matrix.md` and `docs/MASTER-PLAN.md` no
longer matched their sources. Both regenerated with their own generators — **run,
not edited; `tools/` is cc's.** The measured delta: **990 → 991** test files on
disk, **219 → 220** traced to no stated requirement, 77.9% → 77.8%.

**MY SUITE IS ONE OF THE 220 AND I DID NOT BIND IT, DELIBERATELY.** The only
binding path open to me is the open-work index, and my row there is about
multi-location scoping — **putting the suite's filename into it to move a number
is precisely the measure-gaming that document's own text warns about**
(*"counting it as traced would move 40 files across overnight with not one more
requirement written down anywhere"*). The other path, `GUARD_TESTS`, lives in
`tools/sairn_push_gate_hook.py`, which is **cc's and a push gate** — editing it
is both a boundary crossing and the self-checking class. **So the honest state is
one more file on a 220-deep platform backlog, said rather than quietly
absorbed.** The requirement it covers IS written down — §12.6b and §13.5 of
`docs/2026-09-17-sairnfreedom-tips-tax-treatment.md` — just not anywhere the
matrix reads.

**AND THE PUSH'S CLAIM READ `DEAD`, WHICH IS A LIVENESS ARTEFACT OF THIS RESUME
AND NOT AN UNCLAIMED PUSH.** `tools/sairn_claim.py own` reports
`state: DEAD, because: CLAUDE_PID 22036 no longer exists` — the claim was taken
at `2026-10-17T11:22:11Z` by the session that started b22, and **this session
resumed the same batch under a new pid**. The record still names `platform` and
the same task string. `claim` **refuses** to re-take it (*"carry on under the
claim you already hold, or release it first so the record says one thing"*), and
**rewording the task string to get a fresh claim is the move PR §4.3 forbids** —
so the batch carried on under the held record and it is released with the report.
**Every other clone saw it HELD the whole time**; the DEAD reading is visible only
to its own session.

---

## 5. Claims held

**`platform`, taken BEFORE any work, STILL HELD as this file is written**,
because the push in §6 has not happened and **a claim released before the work
lands is a claim that was never true.** It is released with the report and
digest, and the report records the release.

**Nothing was inherited:** b21's claim was released at the end of b21.

---

## 6. Open — every item, why, and the exact next step

### 6.1 → HANK. `api/sd-data.js`, the append-only existence guard

**C1 is red on purpose and the fix is the same one line as A1, one guard
earlier:** route the `alf_op_audits` **existence SELECT** through
`notProvisioned(res, existingR, <the same message>)`. **`notProvisionedDecide()`
needs no change.** Re-derive the line number; measured, the branch holds exactly
one raw 503 and it is that guard. **C2 is the paired positive** — a genuine 404
on the same guard answers 503 — so C1 is a comparison between two real answers.

**AND THANK YOU FOR A1 AND B1, which is not a courtesy:** the conversion is what
let the suite become a regression guard, and **eleven guards moved where two were
routed.** `:14316` is still named and not driven.

### 6.2 → WHOEVER OWNS OPEN-WORK ROW 356. One clause, not a rewrite

**Row 356's item-4 sentence says the shared multi-location architecture is NOT
STARTED. Row 355, written the next day by the same session, says it is DESIGNED
AND FIRST-MIGRATED.** Both were true when written. **356 is read first and 355's
correction is invisible from it**, and that cost this batch the premise of its
own claim. **One clause pointing at 355 is the whole fix.** I did not edit it —
re-wording another session's row to carry my own answer is the edit this platform
has least tolerance for.

### 6.3 → CC. Row 449's measurement is now false

Row 449 records *"`dnt_rollup` appears 0 times in `sairndental.html` and 0 times
in every `.html` file in the repo — NO PANEL, NO NAV TARGET, NOTHING SENDS IT."*
**That was true then.** Re-derived at HEAD: **`sairndental.html:2543` is
`await sdnData('read','dnt_rollup',{})`** with `dntLastErrText('dnt_rollup')`
beside it at `:2549`. The row's *"NEEDS A DECISION — either a panel or a written
deferral"* **was answered by somebody building the panel.**

**NOT CLAIMED: that the panel is reachable from the nav or complete.** I checked
the call site, not the route. Only that the row's stated measurement no longer
holds, and the amendment is yours.

### 6.4 → WHOEVER OWNS `api/_lib/roofing-locations`. A DECISION, not a fix

`isDefaultLocation()` was added to `location-scope.js` with its reason stated:
*"`sairnroofing.html` asks this question inline twice… a UI that hardcodes the
sentinel is the next place the constant drifts."* **Both sites still hardcode it**
(`sairnroofing.html:3292`, `:3298`) **and they cannot stop** — the module is
CommonJS, the app is a single HTML file with no loader and no build step. **There
is no path from that UI to that function.** Arm E passes and proves the function
works, **not that anything uses it.**

**Either (a) accept the two client literals permanently and say so in a comment
at both sites, or (b) return an `is_default` boolean per row from the locations
endpoint so the client never compares the sentinel. (b) is the one that makes
arm E's stated reason true.** Not taken here: `api/` is hank's this batch.

### 6.5 → NOBODY, FOR THE BRAND AXIS, AND THAT IS THE SCOPING CALL

**The LOCATION half is built and tested. The BRAND/ENTITY half has two
disagreeing implementations (`rf_entities`, `sen_franchise_agreements`) and no
shared anything**, and `location-scope.test.js` arm D **forbids** the shared
module from growing one. **The precondition is a SECOND app that needs an entity
layer, not a session with time** — the same precondition `location-scope.js`
consolidated on, and the reason it is a good module rather than a guess.

**AND DO NOT BUILD location-as-access-boundary.** Recorded decision **2026-08-25
(Michael)** at `api/_lib/roofing-locations.js:20`: *"It deserves a real
multi-location customer to design against rather than a guess now."* **A session
that picks it up has misread it.**

### 6.6 → WHOEVER WANTS THE EXPENSIVE HALF OF ITEM 4's FINDING

**How many of the other 64 known-red rows carry a `tail` the runner cannot
produce is NOT MEASURED, and it is not cheap.** Establishing it needs each
registered suite driven **ALONE** and its `out[-1]` compared to its row — a long
run, and several of those suites **write when run**.

**The arm belongs in `tests/run_known_red_probe.py`**, which already builds its
fixture log FROM these rows and is therefore the one place that could assert the
inverse — that every row's tail is a line some suite really printed — **but it
would have to drive them to know.** Routed rather than estimated.

### 6.7 → SAIRNfreedom, IF A POST EVER REPORTS `both` WITH TIPPED STAFF

**Add an `employerEntity` to the member/officer record — NOT a second scalar on
the post** — because the question is per worker and a post-level field answers it
wrongly for every post that has both. **`taxEntityFacts().unknowns` already says
the app does not record it**, so the gap is disclosed to the post that has it
rather than buried. **Nothing should be built until a real post reports that
shape.**

### 6.8 → NOBODY. SAIRNcash is HELD

**Do not pursue any Stripe item until Michael says go.** Unchanged from b21, and
nothing in this batch touched it.

### 6.9 → THE POST's CPA. One question, one line, unchanged from b21

**Is this post's canteen held under §501(c)(19), a companion §501(c)(7), or
both?** **It is now a FIELD** rather than only a question — `TAX_ENTITIES`, with
`''` meaning UNKNOWN — so the answer has somewhere to land when it arrives.

### 6.10 → WHOEVER OWNS THE THREE DUPLICATE INDEX PAIRS. Pre-existing, not mine

SAIRNgrounds 144/145, Tooling 255/257, Platform 295/299. Measured, not inherited
as a claim. `index_duplicate_check.py` keeps exiting 1 until each pair is merged
or marked.

### 6.11 → NOT TOUCHED IN b22, named so it is not mistaken for done

The b17/b18 carry-overs are exactly as b19–b21 left them: `tooling_inventory
--hooked` failing open on an empty hook set; the two claims probes' retyped-task
fixtures; `sairnbuild.html`'s bare `catch(e){}` in `st()`; six named
`recurrence_open` register records; `run_capa_fields_probe.py`'s 200–420s per-arm
2.46MB register rewrite; b16's three deterministic ablation arms. **And the
151/57 sibling `NOT_PROVISIONED` guards are NOT converted — a decision, not a
backlog** (cross-domain item 7): which of them carry real risk is a per-branch
judgement belonging to whoever owns `api/`. **The population figure moved from
151/67 to 151/57 because hank converted eleven**, and the decision is unchanged.
**`irs.gov/instructions/i8846` is still unread — HTTP 404 at b21 and not
retried.**

---

## 7. Scratch and transcript

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\9fe1b8da-047e-4787-9e87-9983dd2e2635.jsonl`

**Scratch:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\9fe1b8da-047e-4787-9e87-9983dd2e2635\scratchpad\`
— `gen_drive.py`, `taxfacts_drive.js`, `ablate.py`, `add_row.py`,
`fixture_log.txt`, `observed_tail.txt`, `nps.out`, and the commit message.

**No worktree was created this batch.** The ablation used
`tempfile.mkdtemp()` directories, each removed in a `finally`.
`C:/Users/marsh/AppData/Local/Temp/gate-probe3-17976` is registered against this
clone, is **not mine**, and was left alone. The 109 files / 247 MB that `rm` has
refused across b14–b16 are still at the b16 path, listed in
`SAIRN-handoff-cody-b16.md` §6. **Nothing in the repo or on the Drive depends on
any of them.**

---

*Written before the report, at a point where everything above is committed
except this file and the two artefacts that follow it.*
