# Handoff — cody, batch b24, 2026-10-19

**Written BEFORE the report**, at a point where **nothing is half-finished**:
all four items are closed, every repair is ablated in **both** legs, the diff
shape is checked, and the only things not yet committed are this file and the
two artefacts that follow it.

**NOTHING IS PUSHED YET.** §1 is a **PRE-PUSH** state and must not be read as a
landed one. §6 is the push.

**THE HEADLINE: MICHAEL'S DECISION MADE AN ARM'S STATED REASON TRUE FOR THE
FIRST TIME, AND A SECOND ARM TURNED OUT TO HAVE BEEN UNABLE TO FAIL AT ALL.**
`isDefaultLocation()` was added to the shared module *for* two
`sairnroofing.html` sites and they could not reach it; arm E passed for weeks
proving the function **works**, not that anything **uses** it. And the trust-
ledger ordering I routed from b23 was not merely an unstripped comparison — the
only place it was recorded is a **report-only** probe whose stated contract is
`exit 0 by design`, so it **computed** the fact and **printed** it, and a false
value failed nothing. Its own closing sentence names the edit to watch. Nothing
watched it.

---

## 1. Committed state — PRE-PUSH

| | |
|---|---|
| commits | the claim commit `chore(claims): cody claims platform` is on `origin/main`. The work is **staged and not yet committed** as this file is written |
| claim | `platform`, taken **BEFORE any work**, with a FILES list declared. **STILL HELD** — §5 |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, in any form, and no call to `tools/gate_skip.py` |
| boundaries | **`api/_lib/roofing-locations.js` and `api/sd-data.js` ARE NORMALLY HANK'S AND I TOOK THEM ON MICHAEL'S EXPLICIT DECISION**, declared in the claim string rather than assumed. hank holds **no** active claim. **NO `sql/` file touched. NO `tools/` file touched** — fourth holds `sairn_push_gate_hook.py`, `gate_skip.py`, `tooling_inventory.py`, `wcag_contrast_check.py` and `sairndental.html`, **none of which is in my set** |
| `api/sd-data.js` | **+11 / −1.** One stamping expression plus its comment. Diff shape checked before committing, per Verification Discipline 4 |
| Stripe | **NO Stripe work of any kind.** SAIRNcash is HELD and was not touched |
| committer | `fx <fx@example.invalid>`, this clone's local config, unchanged |

**Files staged — fourteen:**

```
api/_lib/roofing-locations.js                +18      re-exports isDefaultLocation
api/sd-data.js                               +11/-1   is_default stamped per row
api/_lib/location-scope.test.js              +61      NEW arm F
sairnroofing.html                            +56/-2   rfIsDefaultLoc + both call sites
tests/sairnroofing_default_location_from_server.js  +226  NEW suite, 15 arms
tests/sairnlaw_trust_clearance.js            +51      NEW ordering arm (11 total)
tests/sairnlaw_trust_clearance_review_probe.js  +37/-4  its computation repaired
tests/sairnfreedom_server_backup.js          +51/-4   b23 routed
tests/sairnbiz_undated_payee_notes.js        +36/-2   b23 routed
tests/sd_data_blob_scope_ten_routed_sites.js +17/-1   b23 routed
tests/sairncode_pt_gp_modifier.js            +40/-5   the one real new finding
docs/b24-logs/ablate_b24_repairs.py          +279     both legs from the first run
docs/b23-logs/green_but_worthless_sweep.py   +152/-4  the subject classifier
docs/2026-10-19-cody-b24-sweep-continued.md  +355     the full account
```

---

## 2. Item by item

### ITEM 1 — `is_default` per row. Michael's decision

**THE CONCEPT, stated before the code and carried in all three files:**

> The server says which location is the implicit default — `is_default` on
> every row and `default_location_id` on the response — and the client reads
> that answer instead of carrying its own copy of the sentinel string, so the
> constant is defined in exactly one module and no UI can drift from it.

**`default_location_id` STAYS ON THE RESPONSE and a per-row flag alone would
have been wrong.** The sentinel may legitimately have **no row of its own** —
the normal case, because a shop that never opened a second branch has every job
on the implicit default and an **empty registry**. A row-only answer cannot
classify a job attributed to a default that is not in the list.

**NULL MEANS NOT ASKED YET AND IT IS NOT FALSE.** Before the first successful
read there is no server answer, and guessing either way is wrong in a different
direction. Each call site states what it does with an unknown: the **select**
compares `!== true` so an unknown keeps the explicit id rather than collapsing
the job to Main; **`rfLocationName`** compares `=== true` so an unknown falls
through to the row name or raw id and never prints "Main" for something it could
not classify. **A truthiness test would have given the select the same answer by
accident rather than by decision**, and arm D1 asserts the explicit form for
exactly that reason.

**ARM F IS THE ARM THAT WOULD HAVE CAUGHT THE GAP**, and it is
**comment-stripped** or it would fail on the note explaining its own fix — both
app files now quote `id==='LOC-DEFAULT'` to record what was removed. It also
asserts each named app file **exists** (a missing file is COULD NOT CHECK, not
clean) and that it examined as many files as it listed, so it cannot pass by
having examined nothing.

### ITEM 2 — the trust-ledger ordering, and a probe that could not fail

**THE CONCEPT:**

> `lawSetClearance()` performs the local write and the re-render in EXECUTABLE
> code BEFORE its `await`, and a suite that CAN FAIL asserts it — measured on
> comment-stripped source with both anchors required present.

**IT WAS WORSE THAN I ROUTED IT, IN TWO WAYS.** (1) The probe is
**report-only** — `exit 0 by design` is its stated contract — so a false value
failed nothing, and its own closing sentence says *"What WOULD break it is
moving `rTrust()` after the await, which is the edit to watch."* (2) **An absent
anchor read as in-order**: `indexOf` returns `-1` and `-1 < <any real
position>` is **true**, so deleting the write entirely reported the ordering as
holding.

**THE PROBE KEEPS ITS CONTRACT** and its computation is repaired — comments
stripped, all three anchors required, `null` printed as **COULD NOT TELL**. The
guard that can go red is a **new arm in `tests/sairnlaw_trust_clearance.js`**,
which exits 1 on failure.

### ITEM 3 — a SCOPE for the B6-class check. No code, by instruction

**THE CLASS:** an arm satisfied by executable **DATA** that carries prose. b22's
arm B6 asserted a substring against rendered output; an ablation deleted the
disclosure it existed to check and **B6 stayed green**, because a constant's
`note` field independently contained the same words and the renderer printed it
too. **No comment stripper reaches this** — the satisfying text is a string
literal in a constant, real executable data by every syntactic test.

**THE CONCEPT OF A CHECK:**

> For each arm that asserts a literal substring against output the suite
> PRODUCED by running the subject, ask how many distinct string literals in the
> subject's own source could contribute that substring. Two or more and the arm
> is **AMBIGUOUS**: it cannot attribute the presence of that text to the thing
> it is checking.

Four steps, cheap form first: find the arms (subjects the suite **produced**,
the opposite population to b23's file-derived sweep, so the two together cover
both halves); collect every string literal in the subject module; count how many
contain the asserted substring — **one** is attributable, **two or more** is
AMBIGUOUS, **zero** is a third state meaning the substring is assembled at
runtime; and **report, never fail**, because ambiguity is not a defect.

**On b22's B6 the cheapest possible implementation is a hit:** *"TWO EMPLOYERS"*
occurs in the constant's `note` **and** in the `unknowns.push(...)` argument —
two sources, one arm, flagged.

**WHAT IT CANNOT DO, named now:** a substring assembled by concatenation has no
single literal and reads as zero sources; it cannot tell a **required**
duplication from an accidental one — only per-arm ablation settles that, so the
static check is **triage** and the ablation is the **verdict**; and in a
single-file app the literal population is the whole file, which lowers
precision.

**NOT BUILT, and §4 is the argument rather than a preference:** the hard half is
finding the arms, and b24 measured that difficulty on the *easier* population at
**one real finding in four flagged**. A B6 detector with worse precision than
that produces a work-list nobody reads twice. **Routed for an owner.**

### ITEM 4 — the sweep continued: b23's four routed candidates all repaired, plus one new real finding

All four of b23's routed candidates are repaired, each with its concept in the
file. **Two assertions in each of two files were deliberately LEFT on raw
source** — `/IS saved on this device/`, `/localStorage write FAILED/`, *"NOT ON
THE VENDOR LIST"*, *"FUTURE year already marked Paid"* are about **the message a
user reads**, so their subject genuinely **is** the prose. **Same file, opposite
correct treatment**, and that distinction is why this is triage and not a
sweep-and-fix.

**The sweep re-run: 102 → 95 candidates, cody's 16 → 10.**

**THE CLASSIFIER IS AN HONEST PARTIAL AND ITS FIRST VERSION WAS USELESS.**
Collecting every subject in a file and taking the strongest reported **83
FILE-DERIVED / 12 UNTRACED / 0 RUNTIME over 95** — almost everything — because
nearly every one of these files reads an app into `html` and then calls
`html.indexOf(sig)` **inside a `grab()` helper**. An `indexOf` in a slicing
helper is **extraction, not a claim**. Scoping to statements that actually
assert gave **64 / 31 / 0**.

**STILL ONLY A PARTIAL, MEASURED ON MY OWN FOUR: one of four was real.** The
residual cause is named — **window bleed**, an extraction next to an assertion
getting classified as one. **1 of 4 is better than b23's 6 of 16 and it is not
good.** Left matching rather than narrowed, for the recorded reason.

**THE ONE REAL FINDING, repaired:** `tests/sairncode_pt_gp_modifier.js` —
*the `pt-gp` input exists as LIVE MARKUP and `runPtCheck` reads it in LIVE
CODE*. **Two strips, not one:** HTML comments whole-file (the delimiters are
unambiguous), JS comments only **inside `runPtCheck`'s own body** (a whole-file
JS strip blanks URLs in strings and regex literals). A third arm reports **COULD
NOT LOCATE** rather than letting an unfound subject read as a pass.

---

## 3. THE ABLATION HARNESS HAD A SILENT CLOBBER — THE THIRD SUCH DEFECT IN TWO BATCHES

`api/_lib` is copied wholesale because these suites `require()` modules out of
it. **The first version wrote the suite FIRST and then copied `api/_lib` OVER
it**, so for any suite that lives *inside* `api/_lib` the `--before` leg
silently drove the **disk** copy and reported a pre-repair measurement it had
never taken.

**MEASURED, NOT SUSPECTED:** L1 came back **REFUSED** in the PRE leg **with arm
F named — and arm F does not exist at HEAD.** That impossibility is the only
reason it was caught.

The library now goes down first, the suite on top, and **the written file is
read back and compared**, returning NOT DRIVEN on a mismatch. **An assertion
rather than a careful ordering, because this is the third time:** b23's harness
parsed its count out of its own assertion messages, b23's closing claim had
measured nothing, and now this. **Each was in a tool written to honour a
discipline and breaking it.**

---

## 4. Verification — exit codes from `echo "EXIT=$?"` on its own line, never a pipeline

```
EXIT=0  node api/_lib/location-scope.test.js                 8 arms (was 7)
EXIT=0  node api/_lib/roofing-locations.test.js              17, untouched
EXIT=0  node api/_lib/roofing-locations-endpoint.test.js     29, untouched
EXIT=0  node api/_lib/roofing-consolidation.test.js          17, untouched
EXIT=0  node api/_lib/dnt-location.test.js                   12, untouched
EXIT=0  node api/_lib/dnt-rollup.test.js                     30, untouched
EXIT=0  node tests/sairnroofing_default_location_from_server.js   15 arms, NEW
EXIT=0  node tests/sairnlaw_trust_clearance.js               11 (was 10)
EXIT=0  node tests/sairnlaw_trust_clearance_review_probe.js  report-only, 0 by design
EXIT=0  node tests/sairnfreedom_server_backup.js             17
EXIT=0  node tests/sairnbiz_undated_payee_notes.js           11
EXIT=0  node tests/sd_data_blob_scope_ten_routed_sites.js    16
EXIT=0  node tests/sairncode_pt_gp_modifier.js               48
EXIT=0  node tests/sairnbuild_server_wins.js                 26, b23 regression
EXIT=0  node tests/sairndental_rollup_panel.js               18, b23 regression
EXIT=0  node tests/sairndental_amount_construction.js        10, b23 regression
EXIT=0  node --check api/_lib/roofing-locations.js, api/sd-data.js,
                     api/_lib/location-scope.test.js and all six changed suites
EXIT=0  Check 0a, sairnroofing.html      2/2 blocks, PARSER-based extraction
EXIT=0  python -m py_compile on both b24/b23 scripts
EXIT=0  python docs/b24-logs/ablate_b24_repairs.py        12 as expected, 0 NOT
EXIT=1  python docs/b24-logs/ablate_b24_repairs.py --before   5 ACCEPTED, EXPECTED
EXIT=1  python docs/b23-logs/green_but_worthless_sweep.py  10 in scope, EXPECTED
EXIT=0  python tools/nav_panel_check.py sairnroofing.html
EXIT=0  python tools/div_balance_check.py sairnroofing.html
EXIT=0  python tools/sairn_reachability_check.py sairnroofing.html
EXIT=0  python tools/sairn_strict_args_check.py sairnroofing.html
EXIT=0  python tools/sairn_dead_button_audit.py sairnroofing.html
EXIT=0  python tools/md_table_check.py
EXIT=0  python tools/open_work_shard.py --check
EXIT=0  python tools/tier_a_review_gate.py
        grep -c service_role sairnroofing.html  ->  0
```

**THE ABLATION, BOTH LEGS, SAME SESSION:**

```
PRE-REPAIR    3 as expected, 5 UNEXPECTED, 4 not driven
              ACCEPTED (the real holes): L1, T1, T3, S1, S2
              REFUSED (controls, already caught): T2, T4
              GREEN (control, correct): L2
              NOT DRIVEN (suite is new at HEAD): L3, L4, L5, L6
POST-REPAIR   12 as expected, 0 UNEXPECTED, 0 not driven
```

**L3–L6 CANNOT HAVE A PRE-REPAIR LEG AND THAT IS STATED RATHER THAN SCORED.**
The suite did not exist at HEAD, so for item 1's client behaviour the honest
comparison is *"no suite existed"* — a weaker statement than *"the mutation was
accepted"*, and it is not dressed up as the stronger one.

**T2 AND T4 WERE ALREADY CAUGHT** by the two-device arms, so they are
**controls** here, not repairs. Their refusing in **both** legs is what makes T1
and T3 attributable to the new arm.

**L2 IS A CONTROL THAT MUST STAY GREEN IN BOTH LEGS:** a comment mentioning the
sentinel is not a client copy of it, and an arm that flagged the note
documenting its own repair is a defect this repo has paid for.

**THE LIVE TREE WAS NEVER WRITTEN BY ANY ABLATION**, asserted rather than
intended: `git status --porcelain` captured before and after and diffed. Every
mutation ran in a `tempfile.mkdtemp()` tree removed in a `finally`.

---

## 5. Claims held

**`platform`, taken BEFORE any work with a FILES list declared, STILL HELD as
this file is written**, because the push in §6 has not happened and **a claim
released before the work lands is a claim that was never true.** Released with
the report; the report records the release.

**THE api/ BOUNDARY IS DECLARED, NOT ASSUMED.**
`api/_lib/roofing-locations.js` and `api/sd-data.js` are normally hank's; I took
them on **Michael's explicit decision** this batch, said so in the claim string,
and confirmed hank holds no active claim. `sairn_claim.py check` reported
*CLEAR ON WORDS — AND THE FILE OVERLAP COULD NOT BE PROVEN EITHER WAY* against
fourth's claim, and the unknown is resolved **by the boundary**: fourth holds
four `tools/` files and `sairndental.html`, none of which is in my set, and I
wrote no `tools/` file.

**Nothing was inherited:** b23's claim was released at the end of b23.

---

## 6. Open — every item, why, and the exact next step

### 6.1 → AN OWNER FOR THE B6-CLASS CHECK. Routed to chat, scoped in §2 ITEM 3

Full scope in §3 of `docs/2026-10-19-cody-b24-sweep-continued.md`. **The cheap
form is a hit on b22's own B6 arm**, which is the strongest argument for it
being worth building. **The precondition is the arm-finding half**, and b24's
measured 1-of-4 precision on the easier population is the reason not to rush it.
**Do not build it without a precision number on a real sample.**

### 6.2 → WHOEVER TAKES THE NEXT SWEEP BATCH. 85 candidates, not mine

`green_but_worthless_sweep.py --all` reports **95**; **10** are cody's. The
other **85 are not mine, not read, and not counted as clean.** The FILE-DERIVED
ones are the routable work-list and the tool prints them. **Read the §4 caveat
first: window bleed makes the FILE-DERIVED class roughly 1-in-4 real on the one
sample that has been checked.**

### 6.3 → NOBODY, FOR THE SIX UNTRACED ROWS IN cody's SCOPE

`confidentiality_flagger_asymmetry_review_probe.py`,
`run_register_freshness_probe.py`, `run_claim_activity_probe.py`,
`run_export_coverage_probe.py`, `run_sairn_status_probe.py`,
`bld_draws_role_arms.test.js`. **UNTRACED means this tool could not tell** — b23
read them and refuted them, and **that reading is not upgraded to a
measurement here.**

### 6.4 → HANK. Unchanged from b22/b23 and NOT re-sent

C1 in `tests/sd_data_not_provisioned_misclass.js` is still red on purpose: route
the `alf_op_audits` **existence SELECT** through
`notProvisioned(res, existingR, <the same message>)`, one guard earlier than
A1's fix. `notProvisionedDecide()` needs no change. Re-derive the line number.
`:14316` is still named and not driven.

**AND A COURTESY NOTE, because I crossed your boundary:** `api/sd-data.js` is
**+11 / −1** — one stamping expression in the `rf_locations` read branch plus
its comment — and `api/_lib/roofing-locations.js` gained one re-export. Both on
Michael's decision, both declared in the claim string. Nothing else in `api/`
was touched.

### 6.5 → FOURTH. The b23 Tier A obligation on `dnt_rollup` is still open

Assigned to you by the gate in b23. It names what to try to break rather than
asking for a diff read, and it is **not** a substitute for your own b29/b30 live
render pass.

### 6.6 → CC. Carried from b22, unchanged

Open-work **row 449** records *"`dnt_rollup` appears 0 times in every `.html`
file"*, which is **false** — `sairndental.html:2543` is a real
`sdnData('read','dnt_rollup',{})` call. **Row 356**'s item-4 sentence still says
the shared multi-location architecture is NOT STARTED where **row 355**
contradicts it.

### 6.7 → MICHAEL. Nothing is blocked on you

The `isDefaultLocation()` decision you gave this batch is **implemented and
ablated**. SAIRNcash stays **HELD**.

### 6.8 → NOT TOUCHED IN b24, named so it is not mistaken for done

**NO LIVE RENDER.** Every repair in this batch is source-level. Nothing
establishes that the roofing location select or the trust ledger behaves
correctly in a real browser against a real Supabase — and the `is_default`
change is a **live response-shape change**, so it is the one item here that most
deserves a real request against the deployed endpoint. **Named as UNVERIFIED in
the report rather than folded into the pass.**

The b17/b18 carry-overs are exactly as b19–b23 left them: `tooling_inventory
--hooked` failing open on an empty hook set; the two claims probes' retyped-task
fixtures; `sairnbuild.html`'s bare `catch(e){}` in `st()`; six named
`recurrence_open` register records; `run_capa_fields_probe.py`'s 200–420s
per-arm 2.46MB register rewrite; b16's three deterministic ablation arms. **The
151/57 sibling `NOT_PROVISIONED` guards are still NOT converted — a decision,
not a backlog.** The expensive known-red-`tail` census is still unmeasured.
`irs.gov/instructions/i8846` is still unread.

---

## 7. Scratch and transcript

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\9fe1b8da-047e-4787-9e87-9983dd2e2635.jsonl`
— **3,846,722 bytes, 2,048 lines.** This session also carries b22 and b23; b24
begins at the turn whose first item is the `isDefaultLocation()` decision.
**Context at this line: 56.7% of 1000k (567,369 tokens, max usage sum over the
transcript), measured rather than estimated.**

**Scratch:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\9fe1b8da-047e-4787-9e87-9983dd2e2635\scratchpad\`
— `b24_before.log`, `b24_after.log`, `b24pre.txt`, `b24post.txt`, the
`rf_*.js` Check-0a block extracts, and b23's `ablate_bld.py` / `sweep_*.log`
still in place.

**No worktree was created this batch.** Every ablation used
`tempfile.mkdtemp()` directories removed in a `finally`.
`C:/Users/marsh/AppData/Local/Temp/gate-probe3-17976` is registered against this
clone, is **not mine**, and was left alone. The 109 files / 247 MB that `rm` has
refused across b14–b16 are still at the b16 path, listed in
`SAIRN-handoff-cody-b16.md` §6. **Nothing in the repo or on the Drive depends on
any of them.**

---

*Written before the report, at a point where everything above is done and only
this file and the two artefacts that follow it are uncommitted.*
