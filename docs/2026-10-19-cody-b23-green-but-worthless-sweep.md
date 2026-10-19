# The green-but-worthless sweep — 16 candidates, 6 confirmed, 2 repaired, 4 routed

**cody, b23, 2026-10-19.** Item 4 of this batch. The shape is an assertion
whose subject is the **text of an application file** and whose test is a
substring, regex or **ordering** comparison over that text **without removing
comments** — so any prose containing the spelling satisfies it, including a
comment explaining that the code *used to* do the thing being asserted.

**TWO NUMBERS, NEVER ONE** (cross-domain item 2). The scanner reports
**candidates**; reading reports **confirmed**; only **ablation** reports a
**hole**. Each stage below is given with its own figure and its own method.

---

## 0. The register this sweep exists because of

Every entry was found by **ablation**, never by reading the assertion:

| batch | what was satisfied instead of the property |
|---|---|
| b17 | `key==='bld_bids'` — by a **comment inside the function under test**, saying the code *"used to read"* exactly that |
| b27 (fourth) | a fourth argument — by a **block** comment, after a repair that stripped only `//` lines; and by a **falsy literal** |
| b27-resume | the verb `'write'` — invisible once string literals were collapsed, so the retry could be changed to `'read'` and the arm stayed green |
| b28 (fourth) | `BLD_PENDING_TRACKED['bld_bids'] = true;` by a **line** comment (N1) and the retry guard by a **block** comment (N4). Routed **HIGH**, unfixed until b23 |
| b22 (cody) | P5 by **hank's explanatory comment**; B6 by a **constant's `note` field** — two files, one batch, one day after the convention about this shape was written |
| **b23** | **and two more, found while repairing b28's: N5** a real `bldPendingMark` call site deleted with a comment carrying the literal, **N6** the retry guard carried by a **string literal**. Both ACCEPTED at 25/0 |

**Writing the convention down did not stop it. The ablation did.** That is the
whole argument for this sweep being a tool rather than a resolution to be
careful.

---

## 1. The scanner — 617 scanned, 102 candidates, 16 attributable to cody

`docs/b23-logs/green_but_worthless_sweep.py`, re-runnable, exit 1 while any
candidate stands in scope.

```
test files scanned                                    617
read an app source AND assert on its text,
  with NO comment stripping anywhere                  102
...of those, attributable to cody                      16
```

**Ownership is derived from COMMIT SUBJECTS, not from an `OWNER` header** — 26
of 617 test files carry one, and every commit in this repo is authored by the
same git identity, so the session is only recoverable from what the commit said
about itself.

**THE 102 IS NOT A DEFECT COUNT AND THE 16 IS NOT EITHER.** The scanner cannot
tell a real hole from an assertion whose subject **genuinely is** the file's
prose — a user-visible toast, a disclosure requirement, a panel note — and
several of those are in this repo and are **correct as written**.

---

## 2. Triage by reading — 6 confirmed, 10 refuted

**REFUTED (10 of 16). The scanner matched variable NAMES that look like source
and hold runtime values:**

| file | why it is not the shape |
|---|---|
| `sairncode_pt_gp_modifier.js` | asserts on `b[0].rule` / `b[0].detail` — **runtime findings**, not file text |
| `bld_draws_role_arms.test.js` | `threw.message`, `ALLOWED.indexOf(r)` — runtime |
| `sairnbuild_server_backup.js` | `c.BLD_SYNCED.indexOf(...)` — a **runtime array lifted through `vm`** |
| `sf_operator_payee_review_probe.js` | `HTML.indexOf(anchor, i+1) === -1` — an **anchor UNIQUENESS guard**, which is the *stronger* shape, not a weaker one |
| `stonedesk_pricing_backtest.js` | only the slicer uses `indexOf`; the arms are on runtime values |
| `confidentiality_flagger_asymmetry_review_probe.py`, `run_register_freshness_probe.py`, `run_claim_activity_probe.py`, `run_export_coverage_probe.py`, `run_sairn_status_probe.py` | no source-text assertion; matched on a read + an unrelated expression |

**That is a 10-of-16 false-positive rate on this scope, and the tool is left
matching rather than narrowed.** Narrowing clears the known instances and fails
silently on the next phrasing; in a detector a false negative is invisible where
a false positive is loud and gets read. Same call `tools/sairn_push_gate_hook.py`
records for its own WEAKENING level.

**CONFIRMED (6 of 16):**

| file | the assertion | what it protects |
|---|---|---|
| `sairndental_amount_construction.js` | §2's substring **and ORDERING** tests over a raw function body | **MONEY** — a charge minted with an amount the app had already refused |
| `sairndental_rollup_panel.js` | 4 wiring arms over raw `html` | **TIER A PHI** panel reachability |
| `sairnfreedom_server_backup.js` | `:178`, `:180`, `:196` code regexes over whole `HTML` | the backup-failure reporter and the derived sync map |
| `sairnlaw_trust_clearance_review_probe.js` | `:255` `f.indexOf("st(...)") < f.indexOf('await sdnData')` | **the same ORDERING shape as the money one** |
| `sairnbiz_undated_payee_notes.js` | `:152` `/Object\.keys\(und\)\.forEach/.test(SRC)` | an unlisted payee staying reachable |
| `sd_data_blob_scope_ten_routed_sites.js` | `:188` `AUTH_SRC.match(/function tokenFromRequest…/)` | a **precondition extraction**, not an assertion — lowest of the six |

---

## 3. Repaired in b23 — the two highest-criticality, each concept-first then ablated

### 3.1 `tests/sairndental_amount_construction.js` — MONEY

**THE CONCEPT:** *both writers parse the amount and RETURN on an unreadable one
in executable code, before any record id is minted — with the ordering measured
over comment-stripped source, so prose mentioning the refusal cannot stand in
for the refusal.*

**The ordering arm was the worst of the four**, and it is worth stating exactly
why: `src.indexOf('dntBadAmount') < src.indexOf('newId(')` is satisfied by
**any comment naming `dntBadAmount` above the real `newId(` call**, while the
real refusal sits below it. `addChargeEntry`'s first line **is** such a comment
— *"REFUSED BEFORE ANYTHING IS BUILT, not coerced"* — so the arm was reading a
comment's position, not the code's.

Repair: one `code()` helper, applied **at the assertion** and not inside
`grab()`, because `grab()`'s other caller feeds `vm.runInContext` and stripping
comments out of code about to be **executed** changes the subject under test
rather than the assertion. Plus a precondition that **both** anchors exist in
executable code before their order is compared — an order comparison between
two `-1`s is `false < false`, which is not an assertion about anything.

### 3.2 `tests/sairndental_rollup_panel.js` — TIER A PHI reachability

**THE CONCEPT:** *the panel div, its sidebar button and `nav()`'s dispatch to
`rRollup` all exist as **live markup and live code**, and `rRollup()` **reads**
`dnt_rollup` through a real `sdnData` call — not that those spellings occur
somewhere in a 440KB file.*

**This file is the worst possible place for a whole-file substring, and the
reason is its own history.** The arm exists because the open-work row tracking
this panel recorded *"`dnt_rollup` appears 0 times in every `.html` file"*. The
file's **prose** about `dnt_rollup` is now extensive — this suite's own name is
in it — so `html.indexOf('dnt_rollup') !== -1` would stay green **if every real
call were deleted and one comment survived**.

Repair: `markup` = the file with **HTML comments** removed, used by the markup
and census arms; `code(slice)` for the two JS arms, each **bounded to one
function body first**. **The HTML strip is whole-file and the JS strip is
not**, deliberately: `<!--`/`-->` is an unambiguous pair in an HTML document,
while `//` occurs inside every URL in every string and inside regex literals,
and a naive whole-app JS stripper is a measured false-finding source here
(Guardian check 27, 58 phantom findings).

### 3.3 Ablated — both legs, same session

`docs/b23-logs/ablate_sweep_fixes.py`, and `--before` drives the identical
mutations against the suites taken out of git:

```
PRE-REPAIR  (suites from git)  5 ACCEPTED, 2 REFUSED
            ACCEPTED: A1, R1, R2, R3, R4
            REFUSED : A2, A3  -- CONTROLS, already caught
POST-REPAIR (suites on disk)   0 ACCEPTED, 7 REFUSED
```

**THE FIRST VERSION OF THAT SCRIPT CLAIMED ALL SEVEN HAD BEEN ACCEPTED, AND IT
HAD MEASURED NONE OF THEM.** Running the `--before` leg said **five**. The
claim is corrected in the script and the script now carries the leg that
settles it, because a closing sentence about an ablation is exactly the kind of
thing that goes unchecked.

**AND THE FIRST R3/R4 WERE NOT SINGLE-LAYER.** They commented the element out
**and** renamed the live one, and both came back REFUSED pre-repair — by the
census arm catching the **rename**, not by anything noticing the comment. **A
mutation that changes two things cannot attribute a refusal to either**, which
is cross-domain item 12's own rule, broken inside the ablation written to honour
it. Corrected to comment-out only; both are then ACCEPTED pre-repair and
REFUSED after.

---

## 4. NOT repaired in b23 — four confirmed, routed with the exact edit

**Said rather than absorbed.** Each needs its own ablation, and four files'
worth of concept-first repair plus eight ablation legs is not this batch.

### 4.1 `tests/sairnlaw_trust_clearance_review_probe.js:255` — TAKE THIS ONE FIRST

```js
return f.indexOf("st('law_trusttx',list)") < f.indexOf('await sdnData')
    && f.indexOf('rTrust();') < f.indexOf('await sdnData');
```

**It is the SAME ORDERING SHAPE as §3.1 and the money one is now proof that it
bites.** The property is *the local write and the re-render happen before the
await* — i.e. a trust-ledger entry is on screen before the network call. A
comment above `await sdnData` naming `st('law_trusttx',list)` satisfies it with
the real write moved after. **Exact edit:** wrap `f` in a comment stripper and
assert both anchors exist before comparing positions. **Trust money.**

### 4.2 `tests/sairnfreedom_server_backup.js:178, :180, :196`

Three code-shape regexes over the whole `HTML`. **Exact edit:** bound `:180`
and `:196` to `st()`'s own body and strip comments; `:178` can stay whole-file
but should assert the `function` keyword in stripped source. **Leave `:187` and
`:189` alone** — their subject genuinely **is** the user-facing message text.

### 4.3 `tests/sairnbiz_undated_payee_notes.js:152`

`/Object\.keys\(und\)\.forEach/.test(SRC)` over the whole file. **Exact edit:**
assert it inside `rVends`'s body, comment-stripped. **Leave `:155` and `:158`
alone** — *"NOT ON THE VENDOR LIST"* and *"FUTURE year already marked Paid"* are
**panel notes**, and asserting the prose is the point.

### 4.4 `tests/sd_data_blob_scope_ten_routed_sites.js:188` — lowest, and read it before changing it

`AUTH_SRC.match(/function tokenFromRequest\(req\)\s*\{\s*\n\s*const h = …/)` is
a **precondition that EXTRACTS the header name** so the suite cannot type it —
which is the discipline, not a defect. The only hole is that a comment carrying
that shape could supply a **wrong** header name. **Exact edit:** strip comments
from `AUTH_SRC` before the match. **Do not "fix" the extraction itself.**

---

## 5. What this sweep CANNOT see, named because it is not a gap in the method

- **An assertion that strips comments correctly and still checks the wrong
  property.** Nothing textual reaches that.
- **b22's B6 class, entirely.** That arm was satisfied by a **constant's
  `note` field** — real executable data carrying prose. To a text scanner it
  looks like nothing, because it *is* code. Detecting it needs the value flow,
  not the text.
- **The other 86 candidates** (102 minus cody's 16). Not mine, not read, not
  counted as clean — and the scanner will keep reporting them.

**So the honest state is: one re-runnable scanner, six confirmed by reading, two
repaired and ablated both legs, four routed with pasteable edits, and one named
class the tool is blind to.**
