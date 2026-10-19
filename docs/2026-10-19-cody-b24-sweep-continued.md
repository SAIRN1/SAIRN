# b24 — the sweep continued, and a scope for the B6-class check nobody owns

**cody, b24, 2026-10-19.** Four items. Items 1, 2 and 4 write new logic and
each carries its one-line concept **above** the code it produced. Item 3 is a
**scope only** — no code — because that is what was asked for and because the
cheap version of it is worth more than a fast version.

---

## 0. Methodology, since it is item 5

**Every item below that writes new logic states its concept in one line before
the code exists, and the concept is in the file it governs rather than only
here.** That is not a formality on this platform: b23 found six arms across
three suites that had been written correctly and then made inert by the app
moving, and in every case the arm's *purpose* was recoverable only from prose
that the arm itself did not check. Writing the property down first is what
makes the later ablation a question with an answer.

**And every repair is ablated in BOTH legs.** `--before` drives the identical
mutations against the suites taken out of git. b23 shipped an ablation whose
closing claim had measured nothing and was wrong by two; `docs/b24-logs/`
carries both legs from the first run.

---

## 1. ITEM 1 — `is_default` per row. Michael's decision, and arm E's reason is now true

### The concept, stated before the code

> **The server says which location is the implicit default — `is_default` on
> every row and `default_location_id` on the response — and the client reads
> that answer instead of carrying its own copy of the sentinel string, so the
> constant is defined in exactly one module and no UI can drift from it.**

### What was wrong, and why it had survived an arm written about it

`api/_lib/location-scope.js` added `isDefaultLocation()` with its reason in the
code: *"sairnroofing.html asks this question inline twice, and a UI that
hardcodes the sentinel is the next place the constant drifts."* Measured in
cody b22: **both sites still hardcoded it and could not stop.** That module is
CommonJS; the app is a single HTML file with no loader and no build step. There
was no path from the UI to the function. **Arm E passed from the day it was
written and proved the function WORKS, not that anything USES it.**

b23 routed two options. **Michael chose the second: serve the answer.**

### What changed

| file | change |
|---|---|
| `api/_lib/roofing-locations.js` | re-exports `isDefaultLocation` alongside `DEFAULT_LOCATION_ID`, the pattern that file already uses |
| `api/sd-data.js` | the `rf_locations` read branch stamps `is_default` per row **with that function**, so the sentinel is evaluated by the module that owns it |
| `sairnroofing.html` | `rfDefaultLocId` captured **off the response**; `rfIsDefaultLoc(id)` added; both call sites read it |
| `api/_lib/location-scope.test.js` | **new arm F** |
| `tests/sairnroofing_default_location_from_server.js` | **new suite, 15 arms** |

**`default_location_id` STAYS ON THE RESPONSE and a per-row flag alone would
have been wrong.** The sentinel may legitimately have **no row of its own** —
that is the normal case, since a shop that never opened a second branch has
every job on the implicit default and an **empty registry**. A row-only answer
cannot classify a job attributed to a default that is not in the list.

### NULL MEANS NOT ASKED YET, AND IT IS NOT FALSE

Before the first successful read this file has no server answer, and guessing
either way is wrong in a different direction. `rfIsDefaultLoc()` returns
**null**, and each call site states what it does with an unknown:

- **the select** compares `!== true`, so an unknown **keeps the explicit id
  selected** rather than collapsing the job to Main — showing Main for an id we
  could not classify would tell a foreman the job is on the default branch when
  it may not be. The save path is unaffected: it sends `location_id` only when
  the user actually picked one.
- **`rfLocationName`** compares `=== true`, so an unknown falls through to the
  row name or the raw id and **never prints "Main" for something it could not
  classify** — which is already what it did for an id the registry has never
  heard of.

**A truthiness test would have produced the same answer for the select by
accident rather than by decision**, and arm D1 of the new suite asserts the
explicit `!== true` for exactly that reason.

### Arm F — the arm that would have caught the gap

> **The sentinel is defined in exactly one module and NO app file's EXECUTABLE
> code spells it — so arm E's own reason is a property this suite verifies
> rather than a sentence it carries.**

**Comment-stripped, or it would fail on the note explaining its own fix.** Both
app files now carry a comment quoting `id==='LOC-DEFAULT'` to record what was
removed; an assertion counting raw occurrences would flag the documentation of
its own repair, a defect this repo has paid for by name. Arm F also **asserts
each named app file exists** — a missing file is COULD NOT CHECK and must not
read as clean — and asserts it examined as many files as it listed, so it
cannot pass by having examined nothing.

---

## 2. ITEM 2 — the trust-ledger ordering arm, and the probe that could not fail

### The concept, stated before the code

> **`lawSetClearance()` performs the local write and the re-render in
> EXECUTABLE code BEFORE its `await`, and a suite that CAN FAIL asserts it —
> measured on comment-stripped source with both anchors required present.**

### It was worse than routed, in a way worth recording

b23 routed this as "the same ordering shape as the money arm." It is, **and
there were two further problems:**

1. **The file is report-only. `exit 0 by design` is its stated contract.** So
   it **computed** the ordering and **printed** it, and a false value failed
   nothing. The review's own closing sentence says *"What WOULD break it is
   moving `rTrust()` after the await, which is the edit to watch"* — **and
   nothing watched it.**
2. **An absent anchor read as in-order.** `indexOf` returns `-1`, and
   `-1 < <any real position>` is **true**, so deleting the write entirely
   reported the ordering as holding.

### What changed

- **The probe keeps its contract** and its computation is repaired: comments
  stripped, all three anchors required, and `null` printed as **COULD NOT
  TELL** rather than as `false`.
- **The guard that can go red is a new arm in
  `tests/sairnlaw_trust_clearance.js`** (now 11 arms), which exits 1 on
  failure. It requires each anchor before comparing positions, and each
  assertion says what the app would do wrong if it failed.

### Why the order is the control, not a nicety

`lawMarkOutstanding` goes straight to `lawSetClearance(id, null, true)` **with
no prompt**, so the "a prompt blocks a second click" argument does not cover
that path. It holds anyway for a stronger reason: `st()` and `rTrust()` both
run **synchronously before the await**, JavaScript dispatches the second click
only after the first handler yields, and by then the re-render has **removed
the Outstanding button** because the row is now `cleared===false`. **The
control the second press would need is gone before the second press can be
delivered.**

---

## 3. ITEM 3 — a SCOPE for the B6-class check. No code

### The class, precisely

**An arm satisfied by executable DATA that carries prose.** In b22, arm B6
asserted `rendered.indexOf('TWO EMPLOYERS') >= 0`. An ablation deleted the
two-employer **unknown** the arm existed to check — and B6 **stayed green**,
because `TAX_ENTITIES.both.note` independently contains *"TWO EMPLOYERS ARE
POSSIBLE"* and the renderer prints that note too.

**IT IS NOT THE COMMENT CLASS AND NO COMMENT STRIPPER REACHES IT.** The text
that satisfied the arm is a **string literal in a constant** — real executable
data by every syntactic test. b23's sweep is blind to it **by construction**,
and said so.

### The concept of a check for it

> **For each arm that asserts a literal substring against output the suite
> PRODUCED by running the subject, ask how many distinct string literals in
> the subject's own source could contribute that substring. Two or more and
> the arm is AMBIGUOUS: it cannot attribute the presence of that text to the
> thing it is checking.**

### What it would look like, in the cheap form first

1. **Find the arms.** An assertion whose subject is a value the suite
   **produced** — the return of a render/compute function, or an element's
   `innerHTML` after a call — rather than text read off a file. That is the
   opposite population to b23's sweep, which deliberately looked at
   file-derived subjects, and the two together cover both halves.
2. **Collect the candidate sources.** Every string literal in the subject
   module's own source — constants, message tables, template fragments.
3. **Count.** How many of them contain the asserted substring? **One** is
   attributable. **Two or more is AMBIGUOUS** and goes on a work-list. **Zero**
   is a third state: the substring is assembled at runtime and this check
   cannot speak to it.
4. **Report, never fail.** Ambiguity is **not** a defect — two sources may both
   be required, and an arm asserting a user-visible phrase that appears in
   both a constant and a heading is correct as written.

**On b22's B6 this is a hit on the cheapest possible implementation:** *"TWO
EMPLOYERS"* occurs in `TAX_ENTITIES.both.note` and in the `unknowns.push(...)`
argument — **two sources, one arm, flagged.**

### What it cannot do, named now rather than discovered later

- **A substring assembled by concatenation** (`'TWO ' + noun + 'S'`) has no
  single literal and will read as zero sources.
- **It cannot tell a required duplication from an accidental one.** Only
  per-arm ablation — delete one candidate source, re-run, see whether the arm
  still passes — settles that, and that is expensive. **The static check is
  triage; the ablation is the verdict.**
- **It needs to know which module produced the value.** In a single-file app
  that is the whole file, which makes the literal population large and the
  precision lower. b24's own experience says that matters: see §4.

### Why it is not built in b24

**Because the honest version needs the arm-finding half to work first, and
b24's experience says that is the hard part.** §4 below is a measurement of
exactly that difficulty on the *easier* population, and it came out at **one
real finding in four flagged**. Shipping a B6 detector with worse precision
than that would produce a work-list nobody reads twice — which is how a
detector becomes decoration. **Routed to chat for an owner.**

---

## 4. ITEM 4 — the sweep continued, and the classifier is an HONEST PARTIAL

### b23's four routed candidates are all repaired

| file | the concept now asserted |
|---|---|
| `tests/sairnlaw_trust_clearance_review_probe.js` + `tests/sairnlaw_trust_clearance.js` | §2 above |
| `tests/sairnfreedom_server_backup.js` | the backup-failure reporter exists and `st()` really delegates to it **inside `st()`'s own body**; `SF_SYNCED_ON` is really derived from `SF_SYNCED` |
| `tests/sairnbiz_undated_payee_notes.js` | `rVends()` really iterates the undated keys **inside its own body** |
| `tests/sd_data_blob_scope_ten_routed_sites.js` | the session header name is extracted from **comment-stripped** handler source |

**TWO ASSERTIONS WERE DELIBERATELY LEFT ON RAW SOURCE IN EACH OF TWO FILES, and
that distinction is the whole point of triage rather than a sweep-and-fix.**
`/IS saved on this device/`, `/localStorage write FAILED/`, *"NOT ON THE VENDOR
LIST"* and *"FUTURE year already marked Paid"* are about **the message a user
reads**. Their subject genuinely **is** the prose, so stripping comments would
be checking the wrong thing. **Same file, opposite correct treatment.**

### The sweep re-run: 102 → 95, cody's 16 → 10

```
test files scanned                                    618
candidates (read an app source, assert on its text,
  no comment stripping anywhere)                       95
...attributable to cody                                10
```

### The classifier, and the measured verdict on it

**The concept:** *a candidate is only interesting when the variable being
substring-tested is DERIVED FROM FILE TEXT, so the sweep traces each
asserted-on identifier back to its assignment and reports FILE-DERIVED,
RUNTIME and UNTRACED as three separate populations — never folding UNTRACED
into either.*

**The first version of it discriminated nothing and that is recorded rather
than quietly fixed.** Collecting every subject in the file and taking the
strongest reported **83 FILE-DERIVED / 12 UNTRACED / 0 RUNTIME over 95** — i.e.
almost everything — because nearly every one of these files reads an app into
`html` and then calls `html.indexOf(sig)` **inside a `grab()` helper**. **An
`indexOf` in a slicing helper is extraction, not a claim.** Scoping subject
collection to statements that actually assert moved it to:

```
FILE-DERIVED   64      read these
UNTRACED       31      THIS TOOL COULD NOT TELL -- still needs a human
RUNTIME         0      a substring test on a runtime value is not this defect
```

**AND IT IS STILL ONLY A PARTIAL, MEASURED ON MY OWN FOUR:** of cody's four
FILE-DERIVED rows, **one was real.**

| row | verdict | why |
|---|---|---|
| `tests/sairncode_pt_gp_modifier.js:333` | **REAL — repaired, §4.1** | `ok(/id="pt-gp"/.test(html))`, raw source |
| `tests/sairnbuild_server_backup.js:112` | false positive | `const a = html.indexOf(startMark)` — extraction, pulled in by **window bleed** |
| `tests/stonedesk_pricing_backtest.js:61` | false positive | same shape |
| `tests/sf_operator_payee_review_probe.js:41` | false positive | an anchor **UNIQUENESS** guard, which is the *stronger* shape |

**The residual cause is named: window bleed.** The assertion window is a line
plus up to five continuation lines, so an extraction sitting next to an
assertion gets classified as one. **1 of 4 is better than b23's 6 of 16 and it
is not good**, and the tool is left matching rather than narrowed for the same
reason as before: narrowing clears the known instances and fails silently on
the next phrasing, and in a detector a false negative is invisible where a
false positive is loud and gets read.

**The remaining six in cody's scope are all UNTRACED**, which means *this tool
could not tell* — not that they are clean. b23 read them and refuted them;
that reading stands and is **not** upgraded to a measurement here.

### §4.1 The one real finding, repaired

> **THE CONCEPT: the `pt-gp` input exists as LIVE MARKUP and `runPtCheck` reads
> it in LIVE CODE — so a commented-out input or a commented-out read cannot
> satisfy either, which is exactly the "a rule the form cannot reach reads as
> covered" failure that section is named for.**

**Two strips, not one, and the split is deliberate.** `<!-- -->` is an
unambiguous pair in an HTML document so it is removed across the whole file; a
whole-file JS strip is **not** safe, because `//` occurs inside every URL in
every string and inside regex literals. So the markup arm reads
HTML-comment-stripped source and the code arm is **bounded to `runPtCheck`'s
own body** before its JS comments are removed. A third arm reports **COULD NOT
LOCATE** if that function cannot be found by balanced braces, rather than
letting an unfound subject read as a pass.

### The 85 that are not cody's

`--all` reports **95**; **10** are attributable to cody. **The other 85 are not
mine, not read, and not counted as clean.** Of those, the FILE-DERIVED ones are
the routable work-list and the tool prints them on request.

---

## 5. Ablation — both legs, same session

`docs/b24-logs/ablate_b24_repairs.py`, and `--before` takes the suites out of
git:

```
PRE-REPAIR    3 as expected, 5 UNEXPECTED, 4 not driven
              ACCEPTED (the real holes): L1, T1, T3, S1, S2
              REFUSED (controls, already caught): T2, T4
              GREEN (control, correct): L2
              NOT DRIVEN (suite is new at HEAD): L3, L4, L5, L6
POST-REPAIR   12 as expected, 0 UNEXPECTED, 0 not driven
```

**L3–L6 CANNOT HAVE A PRE-REPAIR LEG AND THAT IS STATED RATHER THAN SCORED.**
`tests/sairnroofing_default_location_from_server.js` did not exist at HEAD, so
for item 1's client behaviour the honest comparison is *"no suite existed"* —
a weaker statement than *"the mutation was accepted"*, and it is not dressed up
as the stronger one.

**T2 AND T4 WERE ALREADY CAUGHT**, by the two-device arms, so they are
**controls** here and not repairs. Their refusing in **both** legs is what makes
T1 and T3 attributable to the new arm rather than to the mutations being
careless ones.

**AND THE ABLATION HARNESS HAD A SILENT CLOBBER, found and recorded — the third
such defect in two batches.** `api/_lib` is copied wholesale because these
suites `require()` modules out of it; the first version wrote the suite **first**
and then copied `api/_lib` **over it**, so for any suite that lives *inside*
`api/_lib` the `--before` leg silently drove the **disk** copy. Measured: L1
came back REFUSED in the PRE leg **with arm F named, and arm F does not exist at
HEAD.** The library now goes down first, the suite on top, and **the written
file is read back and compared** — an assertion rather than a careful ordering,
because this is the third time.

---

## 6. What is NOT done

- **No B6-class check is built.** §3 is a scope, which is what was asked for,
  and §4's measured precision is the argument for not rushing it.
- **The 85 non-cody candidates are unread.**
- **The six UNTRACED rows in cody's scope are not upgraded** from b23's reading
  to a measurement.
- **The classifier's window bleed is not fixed.** Named, measured at 1-of-4 on
  the FILE-DERIVED class, and left matching.
- **No live render.** Every repair here is source-level. Nothing establishes
  that the roofing location select or the trust ledger behaves correctly in a
  real browser against a real Supabase.
