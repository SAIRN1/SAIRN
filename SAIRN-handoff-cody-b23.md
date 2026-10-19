# Handoff — cody, batch b23, 2026-10-19

**Written BEFORE the report**, at a point where **nothing is half-finished**:
all four items are closed with driven evidence, every repair is ablated in both
legs, the Tier A obligation is recorded, and the only things not yet committed
are this file and the two artefacts that follow it.

**NOTHING IS PUSHED YET.** The committed/pushed table in §1 is a PRE-PUSH state
and must not be read as a landed one. §6 is the push.

**THE HEADLINE: THE SHAPE fourth ROUTED AS HIGH WAS WORSE THAN ROUTED, AND SO
WAS MY OWN MEASUREMENT OF IT.** fourth b28 found two ways `bld_bids` could lose
its pending tracking with the suite green (N1, N4). Driving it found **two
more** (N5, N6) — so the resource could lose tracking **end to end**: enrolment,
both write sites, and the retry gate, at 25 passed / 0 failed. And then the
ablation **harness I wrote to measure it** reported six false ACCEPTEDs,
because its count regex read the number out of my own new assertion messages —
which quote the phrase *"at 25 passed, 0 failed"* as evidence. **The measuring
tool had the defect it was measuring, one layer out.**

---

## 1. Committed state — PRE-PUSH

| | |
|---|---|
| commits | the claim commit `chore(claims): cody claims platform` is on `origin/main`. The work is **staged and not yet committed** as this file is written |
| claim | `platform`, taken **BEFORE any work**, with a FILES list declared. **STILL HELD** — §5 |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, in any form |
| boundaries | **NO `api/`, `sql/` or `tools/` file written.** `api/_lib` was **COPIED** into a temp tree by one ablation and never written. Ten tools were **RUN** (§4). No hook restored. `.claude/settings.json` never committed. No auditor clone entered |
| Tier A | obligation **RECORDED** on `dnt_rollup`, assigned to **fourth**. `tier_a_review_gate.py` refused the push until it was, correctly — §2 item 4 |
| Stripe | **NO Stripe work of any kind.** SAIRNcash is HELD and was not touched |
| committer | `fx <fx@example.invalid>`, this clone's local config, unchanged |

**Files staged — eight, three of them new tools:**

```
tests/sairnbuild_server_wins.js                 +235/-16  items 1 and 2
tests/sairndental_amount_construction.js         +41/-4   item 4, MONEY
tests/sairndental_rollup_panel.js                +55/-9   item 4, TIER A PHI
docs/b23-logs/ablate_bld_server_wins.py         +184      the items 1-2 ablation
docs/b23-logs/ablate_sweep_fixes.py             +224      the item 4 ablation, both legs
docs/b23-logs/green_but_worthless_sweep.py      +182      the item 4 scanner
docs/2026-10-19-cody-b23-green-but-worthless-sweep.md  +220  the triage
docs/tier-a-reviews.json                         +25      the recorded obligation
```

---

## 2. Item by item

### ITEM 1 — `bld_bids` could lose its pending tracking END TO END with the suite green

Routed by **fourth b28 check 4** as HIGH and deliberately not fixed there,
because `tests/` is mine and *"a reviewer who fixes what he reviews is the
self-signed review this ledger exists to prevent"*. **Reproduced before
repairing, never taken on trust.**

**THE CONCEPTS, stated before the code was written — two assertions, two
properties:**

> `bld_bids` is **enrolled in pending tracking by executable code**, and both
> of its write sites really call mark and clear — not merely that those
> spellings occur somewhere in a 400KB file.

> the retry's per-key gate actually **READS** the tracking map in executable
> code, so a key that is not enrolled is skipped — not merely that the
> spelling `BLD_PENDING_TRACKED[key]` appears in the body.

**MEASURED, pre-repair, `docs/b23-logs/ablate_bld_server_wins.py`:**

```
N1  declaration replaced by a LINE COMMENT carrying it ..... ACCEPTED 25/0
N4  retry GUARD broken, BLOCK COMMENT carries a satisfying .. ACCEPTED 25/0
N5  a real bldPendingMark call site deleted, a COMMENT
    carrying both spellings left behind ..................... ACCEPTED 25/0   <- NEW
N6  retry GUARD broken, a STRING LITERAL carries one ........ ACCEPTED 25/0   <- NEW
N2  declaration DELETED (control) ........................... REFUSED
N3  declaration flipped to false (control) .................. REFUSED
```

**N5 AND N6 ARE MINE AND THEY ARE THE REASON REPRODUCING MATTERED.** fourth
named two; the shape had four. **N2 and N3 refusing is what made the hole
invisible** — the arm caught the careless mutations and missed every plausible
one, which reads as a working arm from every angle except an ablation.

**THE REPAIR IS TWO THINGS, AND THE SECOND IS THE ONE PEOPLE SKIP.** (a) Two
views of the source, `code()` (comments gone) and `struct()` (comments gone and
every string collapsed to `''`), with **every assertion stating which it uses
and which mutation that closes** — neither alone is enough, because a mutation
hiding code in a string satisfies `code()` and fails `struct()`, and one
changing a verb satisfies `struct()` and fails `code()`. (b) **Scope is always
a bounded window, never the whole file.** `html.indexOf(...)` over 400KB answers
*"does this text occur anywhere"*, which is a question no property of this app
depends on — and it is also unsafe to strip, because a naive comment stripper
over a whole app blanks URLs inside strings and regex literals.

**The two call sites are now counted INSIDE `saveBid()` and
`bldReassignBid()`** rather than across the file, which is strictly stronger
than the count it replaces: a whole-file count of 2 is satisfied by any two
occurrences anywhere, including — as N5 measured — one real call and one
comment.

### ITEM 2 — `bld_draws` had no arm, and the generalisation that fixed one defect created the gap

Routed by **fourth b28 check 2**, *"same shape as b26's `law_bankstatements`
finding."*

**THE CONCEPT, stated before the arm was written:**

> `bld_draws` is a **member** of `BLD_SESSION_REQUIRED` with a **truthy value in
> the real declaration**, so the one shared call-site expression
> `!!BLD_SESSION_REQUIRED[key]` sends an employee session for a draw write —
> the identical property `bld_bids` already had an arm for, asserted over
> comment-stripped source so no comment can supply it.

**WHY IT DID NOT EXIST IS THE PART WORTH KEEPING.** `bld_bids`' session
requirement used to be spelled `key==='bld_bids'` inline. When `bld_draws`
joined, that was correctly replaced by a **map read at three call sites** — and
the arm guarding it was updated to follow the map, **but only ever for the
member it was originally written about.** So the suite guarded one of two
members of a set whose entire purpose is to be extended.

**MEASURED, pre-repair:**

```
D1  bld_draws: true -> false ........................ ACCEPTED 25/0
D3  bld_draws DROPPED from the map .................. ACCEPTED 25/0
D4  real entry removed, a COMMENT carries it ........ ACCEPTED 25/0
D2  bld_bids: true -> false (CONTROL) ............... REFUSED
```

**D2 refusing is what makes D1 a finding rather than a broken copy:** the same
mutation on the other member of the same object was caught.

**SO THE ARM ITERATES THE SET rather than naming `bld_draws` a second time.**
That is the generalisable form: **when a condition becomes a set, the arm must
iterate the set.** An arm naming one member is not a weaker guard — it is a
guard that silently stops covering every member added after it. A third
resource joining the map is covered **on the day it is added**, which is the
only version of this arm that cannot recreate the gap it closes. It also
carries a **precondition** that the map parses as a set of at least two
members, and a check that the call sites **index** the map rather than
hardcoding a member — an arm over a set is worthless if some site still names
one.

### ITEM 3 — arm Z re-ablated, still CAUGHT, no regression

`python docs/b19-logs/ablate_arm_z.py`:

```
BASELINE  EXIT=0   16 passed, 0 failed   arm Z ok:1 FAIL:0
ABLATED   EXIT=1   15 passed, 1 failed   arm Z ok:0 FAIL:1
CAUGHT.
```

**The control ran first and passed**, so the ABLATED leg is attributable.
Figures identical to the b19 post-fix leg. **Arm Z still fires.**

### ITEM 4 — the sweep: 617 scanned, 102 candidates, 16 mine, 6 confirmed, 2 repaired, 4 routed

Full triage in `docs/2026-10-19-cody-b23-green-but-worthless-sweep.md`. Three
numbers at three stages, by three methods, never one number:

```
scanner (docs/b23-logs/green_but_worthless_sweep.py)   617 scanned, 102 candidates, 16 mine
reading                                                 6 confirmed, 10 refuted
ablation (docs/b23-logs/ablate_sweep_fixes.py)          2 repaired, 7/7 mutations refused
```

**10 OF 16 WERE FALSE POSITIVES and the tool is left matching rather than
narrowed** — the scanner flags variable *names* that look like source and hold
runtime values (`b[0].rule`, a `vm`-lifted array, an anchor **uniqueness**
guard, which is the *stronger* shape). Narrowing clears the known instances and
fails silently on the next phrasing; in a detector a false negative is invisible
where a false positive is loud and gets read.

**THE TWO REPAIRED, each concept-first:**

> **MONEY** — `tests/sairndental_amount_construction.js`: *both writers parse
> the amount and RETURN on an unreadable one in executable code, before any
> record id is minted — with the ordering measured over comment-stripped
> source.*
>
> **The ordering arm was the worst of the four.**
> `src.indexOf('dntBadAmount') < src.indexOf('newId(')` is satisfied by any
> comment naming `dntBadAmount` above the real `newId(` call while the real
> refusal sits below it — and `addChargeEntry`'s **first line is such a
> comment**. The arm was reading a comment's position.

> **TIER A PHI** — `tests/sairndental_rollup_panel.js`: *the panel div, its
> sidebar button and `nav()`'s dispatch to `rRollup` all exist as LIVE markup
> and LIVE code, and `rRollup()` READS `dnt_rollup` through a real `sdnData`
> call.*
>
> **This file is the worst possible place for a whole-file substring, and the
> reason is its own history:** the arm exists because the row tracking this
> panel recorded *"`dnt_rollup` appears 0 times in every `.html` file"*, so the
> file's PROSE about `dnt_rollup` is now extensive — this suite's own name is
> in it. `html.indexOf('dnt_rollup') !== -1` would stay green **if every real
> call were deleted and one comment survived**.

**ABLATED BOTH LEGS, SAME SESSION:**

```
PRE-REPAIR  (suites from git, --before)   5 ACCEPTED, 2 REFUSED
                                          ACCEPTED: A1, R1, R2, R3, R4
                                          REFUSED : A2, A3 -- controls, already caught
POST-REPAIR (suites on disk)              0 ACCEPTED, 7 REFUSED
```

---

## 3. THREE DEFECTS IN MY OWN MEASUREMENT, FOUND AND RECORDED RATHER THAN QUIETLY FIXED

**This is the most reusable part of the batch.** Every one is in a tool written
*to honour* a discipline and breaking it.

**(a) THE ABLATION HARNESS HAD THE DEFECT IT WAS MEASURING.** Its summary parse
was `(\d+) passed, (\d+) failed`, unanchored. My new assertion **messages**
quote *"at 25 passed, 0 failed"* as evidence of the old hole — so on every run
where one of those arms went red, the harness read the count out of the failure
text and reported **ACCEPTED for a mutation the suite had just REFUSED by
name**. Six false ACCEPTEDs in one run. Anchored to the suite's own summary
line now, and **the verdict is the exit code plus a NAMED red arm**, never the
parsed count alone.

**(b) A CLOSING CLAIM THAT HAD MEASURED NOTHING.** `ablate_sweep_fixes.py` ended
with *"EVERY ONE OF THESE WAS ACCEPTED BEFORE THE REPAIR."* I had not driven
the pre-repair leg. Driving it said **five of seven**. The script now carries a
`--before` mode that takes the suites out of git, so the sentence is a
differential and not a claim.

**(c) TWO ABLATIONS THAT CHANGED TWO THINGS.** R3 and R4 commented the element
out **and** renamed the live one, and both came back REFUSED pre-repair — by the
census arm catching the **rename**, not by anything noticing the comment. **A
mutation that changes two things cannot attribute a refusal to either**, which
is cross-domain item 12's own rule, broken inside the ablation written to honour
it. Single-layer now; ACCEPTED pre-repair, REFUSED after.

**AND ONE CONTROL EARNED ITS PLACE OUT LOUD:** `ablate_sweep_fixes.py`'s first
run failed its **control**, because the amount suite also `require()`s
`api/_lib/safe-number.js` and the temp tree had no `api/`. Without the control
running first, every "REFUSED" below it would have been a copy that could not
run — which is a green ablation report for a suite that never executed.

---

## 4. Verification — exit codes from `echo "EXIT=$?"` on its own line, never a pipeline

```
EXIT=0  node tests/sairnbuild_server_wins.js              26 passed, 0 failed (was 25)
EXIT=0  node tests/sairndental_amount_construction.js     10 assertions pass
EXIT=0  node tests/sairndental_rollup_panel.js            18 assertions pass
EXIT=0  node tests/bld_draws_role_arms.test.js            regression, untouched
EXIT=0  node tests/sd_data_blob_scope_ten_routed_sites.js regression, 16 passed
EXIT=0  python tests/run_sairnbuild_server_wins_sabotage_probe.py   the negative control
EXIT=0  node --check on all three changed suites
EXIT=0  python -m py_compile on all three new scripts
EXIT=0  python docs/b19-logs/ablate_arm_z.py              item 3, CAUGHT
EXIT=0  python docs/b23-logs/ablate_bld_server_wins.py    16 REFUSED, 0 ACCEPTED
EXIT=0  python docs/b23-logs/ablate_sweep_fixes.py        7 REFUSED, 0 ACCEPTED
EXIT=1  python docs/b23-logs/ablate_sweep_fixes.py --before   5 ACCEPTED -- EXPECTED
EXIT=1  python docs/b23-logs/green_but_worthless_sweep.py 16 candidates in scope
EXIT=0  python tools/md_table_check.py
EXIT=0  python tools/open_work_shard.py --check
EXIT=0  python tools/tier_a_review_gate.py                AFTER recording the obligation
EXIT=0  python tools/known_red_check.py --from-run <b22 fixture>
```

**THE ITEMS 1-2 ABLATION CARRIES M1-M7 AS REGRESSION ARMS**, re-driven because
b23 replaced the previously-repaired arm's two inline strippers with the shared
`code()` and `struct()`. **All seven still REFUSED.** A consolidation that
quietly loosened a working control would be invisible without them, and
replacing a proven control on the strength of "it looks equivalent" is not
acceptable here.

**THE LIVE TREE WAS NEVER WRITTEN BY ANY ABLATION**, and that is asserted rather
than intended: `git status --porcelain` captured before and after each run and
diffed. Every mutation ran in a `tempfile.mkdtemp()` tree removed in a
`finally`.

**THE TWO EXIT-1s ARE BOTH EXPECTED AND BOTH SAY SO IN THEIR OWN OUTPUT.**
`--before` is a pre-repair leg that must find holes; the sweep exits 1 while any
candidate stands in scope, which is what keeps the four routed ones visible.

---

## 5. Claims held

**`platform`, taken BEFORE any work with a FILES list declared, STILL HELD as
this file is written**, because the push in §6 has not happened and **a claim
released before the work lands is a claim that was never true.** Released with
the report; the report records the release.

**Nothing was inherited:** b22's claim was released at the end of b22.

**ONE OVERLAP WAS REPORTED AND READ RATHER THAN DISMISSED:** `sairn_claim.py
check` said *CLEAR ON WORDS — AND THE FILE OVERLAP COULD NOT BE PROVEN EITHER
WAY*, naming cc's claim on `tools/index_duplicate_check.py`,
`tools/status_board_bridge_check.py` and `docs/TOOLING-INVENTORY.md`. **None of
those is in my FILES list and I wrote no `tools/` file**, so the unknown is
resolved by the boundary rather than by the matcher.

---

## 6. Open — every item, why, and the exact next step

### 6.1 → FOURTH. The Tier A obligation on `dnt_rollup`, recorded this batch

**Assigned to fourth by the gate, not first-come.** It names what to try to
break rather than asking for a diff read: construct a mutation that leaves the
panel **unreachable** with all 18 arms green; check whether stripping HTML
comments whole-file broke any arm that *meant* to read commented markup; and
confirm the census arm's new direction is intended — it now compares three sets
derived from `markup` rather than `html`, so a panel that is live but
commented-out in the sidebar reports a **mismatch** where it previously reported
identical.

**NOT CLAIMED: that the panel is reachable in a RENDERED browser.** No live
render was done. This is source-level only, and fourth's own b29 claim is a
sairndental LIVE render pass — **that is the check this cannot substitute for.**

### 6.2 → HANK. `api/sd-data.js`, unchanged from b22 and NOT re-sent

C1 in `tests/sd_data_not_provisioned_misclass.js` is still red on purpose: route
the `alf_op_audits` **existence SELECT** through
`notProvisioned(res, existingR, <the same message>)`, one guard earlier than
A1's fix. `notProvisionedDecide()` needs no change. Re-derive the line number.
`:14316` is still named and not driven.

### 6.3 → WHOEVER TAKES THE NEXT SWEEP REPAIR. Four confirmed, each with the edit

**TAKE `tests/sairnlaw_trust_clearance_review_probe.js:255` FIRST.** It is the
**same ORDERING shape** as the money arm repaired here, so the money one is now
proof that it bites:

```js
return f.indexOf("st('law_trusttx',list)") < f.indexOf('await sdnData')
    && f.indexOf('rTrust();') < f.indexOf('await sdnData');
```

The property is *the local write and the re-render happen before the await* — a
trust-ledger entry on screen before the network call. **A comment above
`await sdnData` naming `st('law_trusttx',list)` satisfies it with the real write
moved after.** Edit: wrap `f` in a comment stripper and assert both anchors
exist before comparing positions. **Trust money.**

Then: `tests/sairnfreedom_server_backup.js:178/:180/:196` — bound `:180` and
`:196` to `st()`'s own body and strip comments; **leave `:187` and `:189`
alone**, their subject genuinely IS the user-facing message.
`tests/sairnbiz_undated_payee_notes.js:152` — assert inside `rVends`'s body;
**leave `:155` and `:158` alone**, those are panel notes and asserting the prose
is the point. `tests/sd_data_blob_scope_ten_routed_sites.js:188` — lowest;
strip comments from `AUTH_SRC` before the match and **do not "fix" the
extraction itself**, which is the discipline rather than a defect.

### 6.4 → WHOEVER OWNS THE OTHER 86 CANDIDATES

`green_but_worthless_sweep.py --all` reports **102**; **16** are attributable to
cody and the other **86 are not mine, not read, and not counted as clean.** The
tool keeps reporting them and exits 1 while any remain in scope.

### 6.5 → NOBODY YET, AND IT IS A REAL BLIND SPOT, NAMED

**The sweep cannot see b22's B6 class at all.** That arm was satisfied by a
**constant's `note` field** — real executable data carrying prose. To a text
scanner it looks like nothing, because it **is** code. Detecting it needs the
value flow, not the text. **No tool on this platform looks for it**, and the
only thing that has ever found one is an ablation.

### 6.6 → NOT TOUCHED IN b23, named so it is not mistaken for done

The b17/b18 carry-overs are exactly as b19–b22 left them: `tooling_inventory
--hooked` failing open on an empty hook set; the two claims probes'
retyped-task fixtures; `sairnbuild.html`'s bare `catch(e){}` in `st()`; six
named `recurrence_open` register records; `run_capa_fields_probe.py`'s 200–420s
per-arm 2.46MB register rewrite; b16's three deterministic ablation arms. **The
151/57 sibling `NOT_PROVISIONED` guards are still NOT converted — a decision,
not a backlog.** b22's four routed items stand: open-work **row 356**'s stale
item-4 sentence, **row 449**'s now-false `dnt_rollup` measurement (→ CC),
`isDefaultLocation()`'s two unreachable UI sites, and the expensive
known-red-`tail` census. `irs.gov/instructions/i8846` is still unread.

### 6.7 → MICHAEL. Nothing is blocked on you this batch

SAIRNcash stays **HELD**. The one judgement call carried from b22 is unchanged
and small: `isDefaultLocation()` was added for two `sairnroofing.html` sites
that cannot reach it — accept the two client literals with a comment at both, or
return an `is_default` boolean per row.

---

## 7. Scratch and transcript

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\9fe1b8da-047e-4787-9e87-9983dd2e2635.jsonl`
— **2,638,493 bytes, 1,375 lines.** This session also carries b22; b23 begins at
the `CODY b23` turn. **Context at this line: 40.6% of 1000k (406,397 tokens,
max usage sum over the transcript), measured rather than estimated.**

**Scratch:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\9fe1b8da-047e-4787-9e87-9983dd2e2635\scratchpad\`
— `ablate_bld.py` (the working copy of what landed as
`docs/b23-logs/ablate_bld_server_wins.py`), `ablate_before.log`,
`ablate_after.log`, `ablate_after2.log`, `sweep_before.log`, `sweep_after.log`,
`ablate_sweep.log`, and b22's `fixture_log.txt` / `observed_tail.txt`, reused
here to re-verify `known_red_check`.

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
