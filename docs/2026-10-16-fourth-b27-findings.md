# fourth b27 (resume) — two guards that were not guarding, and a lower bound three rules deep

**2026-10-16. Batch b27, resumed.** b27 was dispatched on 2026-10-15, opened its
manifest, got item 1's test work done and ablated, and then died before
committing anything. Nothing it did had landed: the two test files were sitting
UNCOMMITTED in the working tree and `docs/batch-manifest-fourth-b27.json` was
UNTRACKED. `docs/2026-10-15-fourth-b27-findings.md` — which that manifest's own
evidence string says holds the Tier A verdict body — **does not exist, at HEAD
or anywhere**. That is the first finding of this batch and it is about b27
itself: a manifest evidence string naming a file that was never written reads
exactly like one naming a file that was.

**EVERY FIGURE BELOW NAMES THE COMMAND THAT PRODUCED IT.**

---

## 1. THE TIER A DISCHARGE WRITE IS STILL BLOCKED, AND IT IS NOW THE SECOND BATCH IN A ROW

| | |
|---|---|
| record | `cody 2026-10-15T15:12:47Z`, resource **`bld_bids`** (Tier A) |
| blocked on | `docs/tier-a-reviews.json` |
| b27 (2026-10-15) | **cc** claimed it at `2026-10-15T16:55:20Z`, three minutes before fourth's first attempt |
| b27 resume (2026-10-16) | **hank** claimed it at `2026-10-16T11:17:27Z`, one minute before fourth's attempt. `CLAUDE_PID 26072` running, confirmed live at 11:17 and again at 11:43 |
| state | **NOT STARTED. Flagged back, not reworded.** |

Per the standing rule the blocked item stops and waits for a go-ahead rather
than proceeding under a disclosure. **The review WORK is complete** — §2 and §3
are it, and they are ablated — **and only the write into
`docs/tier-a-reviews.json` is outstanding.** The exact next step is one command
once hank releases.

**THE PATTERN IS WORTH NAMING RATHER THAN RE-SUFFERING:**
`docs/tier-a-reviews.json` is a single shared file that every Tier A discharge
by any of the four build agents must write, and a review by agent X of a record
raised by agent Y is routinely blocked by agent Z holding the file for an
unrelated row. Two consecutive batches lost the same item to it. **FOR
MICHAEL / cc:** that file wants the same treatment §3.3 of the b26 handoff
demanded for closed periods — one append-only record per discharge rather than
one document every writer must take whole. A per-agent shard or an append-only
JSONL would make this class of block structurally impossible rather than a
thing each batch re-discovers.

---

## 2. ITEM 1 — THE bld_bids SUITE REPAIR, AND MY OWN REPAIR OPENED A HOLE

cody's measurement was right: `tests/sairnbuild_server_wins.js` asserted that
the literal `key==='bld_bids'` appears in `bldRetryPending`, that literal is
gone from `sairnbuild.html`, and **both remaining occurrences are comments** —
one of them inside `bldRetryPending` explaining the removal. The assertion was
satisfied by the comment documenting the removal of the thing it asserted, and
the sabotage arm guarding it was ANCHOR-0 at the same time.

### 2.1 The first repair moved the hole. Measured, 5 mutations

b27's first session repaired it to strip `//` comments and require **some**
fourth argument at the `bldData()` call site. Five mutations against a **COPY**
of `sairnbuild.html` (`<scratch>/b27_bld_ablation.py`):

```
M1  fourth argument DELETED .................... exit 1  REFUSED
M2  fourth argument -> `false` ................. exit 0  ACCEPTED  <- same defect
M3  fourth argument -> `0` ..................... exit 0  ACCEPTED  <- same defect
M4  the DECLARATION deleted, call sites kept ... exit 0  ACCEPTED
M5  real call broken, a BLOCK comment carries
    a satisfying one ........................... exit 0  ACCEPTED  <- a COMMENT again
```

So cody's own check (1) — *can the new regex be satisfied by a future comment or
string literal the way its predecessor was* — **answers YES: by a BLOCK
comment**, because the stripper only removed `//` lines. And a **falsy** fourth
argument is arm 6's own defect wearing an argument: the branch in
`api/sd-data.js` refuses a session-required write whose flag is `false` exactly
as it refuses one with no flag.

That session then fixed it three ways and re-ran: all five REFUSED.

### 2.2 AND THAT REPAIR OPENED ONE OF ITS OWN. Measured, 10 mutations

**This is the finding this batch adds.** The repair collapses every string
literal to `''` before matching, which is what closes M5 — and it is also what
blinds the assertion to **which** string the first argument was.
`<scratch>/b27r_bld_ablation2.py`, ten mutations, M1–M5 again plus five aimed at
the shape of the **repair** rather than its predecessor:

```
BASELINE ........................................ exit 0  25 passed, 0 failed
M1  fourth argument DELETED ..................... exit 1  REFUSED
M2  fourth argument -> `false` .................. exit 1  REFUSED
M3  fourth argument -> `0` ...................... exit 1  REFUSED
M4  DECLARATION deleted, call sites kept ........ exit 1  REFUSED
M5  real call broken, BLOCK comment satisfies ... exit 1  REFUSED
M6  'write' -> 'read' at the retry call site .... exit 0  ACCEPTED, 25/0  <-- THE HOLE
M7  real call broken, STRING LITERAL satisfies .. exit 1  REFUSED
M8  declaration flips bld_bids: true -> false ... exit 1  REFUSED
M9  reads the map but the WRONG CELL ............ exit 1  REFUSED
M10 fourth argument is the OBJECT, not the cell .. exit 1  REFUSED
```

**M6: the retry could be changed to READ instead of WRITE and the arm whose
whole subject is the retry's write stayed green at 25 passed, 0 failed.** A
retry that reads drains the pending queue with a call that fetches rows and
saves nothing, so every stranded record stays stranded while the retry reports
success. That is the same class as the comment that started this, one layer
further in.

**THE FIX IS TWO COPIES AND TWO ASSERTIONS, AND NEITHER ALONE IS ENOUGH:**

* **(A)** comments stripped **AND** strings collapsed — proves the call is real
  **executable** code, because no comment or string survives to carry it
  (M5, M7);
* **(B)** comments stripped **ONLY** — proves the verb is `'write'` and the cell
  is `[key]`, which (A) cannot see once the strings are gone (M6, M9).

A mutation hiding the call in a string satisfies (B) and fails (A); a mutation
changing the verb satisfies (A) and fails (B).

**RE-ABLATED AFTER THE FIX: 10 of 10 REFUSED, baseline still 25/0 exit 0, and
every refusal is on the NAMED arm** — the harness reads the red arm's own line
out of stdout rather than crediting an exit code to whatever it was testing.
`<scratch>/b27r_bld_ablation2_fixed.log`.

### 2.3 Probe side — arms 14 and 15, and why all three of 6/14/15 stay

The first b27 session added **arm 14** (plant the `false` form). This batch adds
**arm 15** (plant `'read'`), because nothing planted the verb mutation and the
new assertion would otherwise rest on something nobody had made fail in that
direction.

`python tests/run_sairnbuild_server_wins_sabotage_probe.py` →
**ALL 19 ARMS PASS, 15 mutations, exit 0**, and its own last arm reports it left
nothing newly dirty (2 files were already modified before it started and are
not its doing). `<scratch>/b27r_probe_fixed.log`.

Arms 6, 14 and 15 are all three present on purpose: **6** proves the flag
argument must exist, **14** proves it must not be falsy, **15** proves the call
being retried is the write — and no one of the three implies either of the
others.

---

## 3. ITEM 2 — THE 26 UNRESOLVED LINES ARE 0, AND THE REASON WAS NOT INTER-PROCEDURAL

b26 reported **26 identifiers UNRESOLVED** and named the reason: `origin()` is
intra-procedural, so a function parameter has no `const <name> =` to find. b27's
first session built **R4** — resolve a parameter by unioning its call sites,
unsafe-wins — with 5 fixtures, and the population fell **26 → 20**.

**AND THEN IT STOPPED, WITH NINETEEN OF THE TWENTY IN CLASS C AND R4 HAVING
TOUCHED NONE OF THEM.** A bucket of 20 nobody can take apart is the same lower
bound R3 was built to kill, one level further in. So this batch built `--why`:
it names, **per line**, the identifier that stalled the walk and the reason, and
it **cross-checks its own answers against `origin()`** — a divergence prints
`MIRROR DIVERGED` and is exit 2, never a quiet re-classification.

**`--why` named `resource` as a stalling identifier on 16 OF THE 20 LINES**
(20 occurrences across those 16; `NOT-A-PARAM` 16, `NO-DECL-NO-FN` 8,
`MIXED-RHS` 7 reasons over 20 lines, because a line can stall on more than one
name).

**ONE DISCLOSURE ON THAT EVIDENCE.** The live log of that run was **overwritten**
by the final `--why`. It is not quoted from memory: it is reproduced by
`<scratch>/b27r_why_inherited.py`, which runs the same census with **R5, R6 and
R7 ablated off**, and the figures above are counted out of
`<scratch>/b27r_census_why_AS_OF_b27_R1toR4.log` mechanically rather than read.

### `api/sd-data.js:748` is `const resource = body && body.resource;`

One line. The handler runs to `:18867`. `resource` is the **table name**, chosen
by the caller. **THREE SEPARATE MECHANISMS were each independently enough to
make that unreachable**, and each is now a rule with fixtures both ways:

| | what it was | why it hid a CALLER |
|---|---|---|
| **R5** | the declaration lookback was **400 lines** | `:748` is 14,000 lines above its last reader. b23's 14-line window and b24's fixed window, a **third** time, inside the rule built to kill them. `:13724`'s `famP` is declared at `:13227` — **497 lines up**, just outside the cap |
| **R6** | `body` was in `CALLER_ROOTS` **and** in `NOISE`, and `NOISE` was filtered first | so the walk dropped `body` before the root lookup could answer CALLER. `headers` is in `SERVER_ROOTS` and `NOISE` too and had the same treatment — invisible, because dropping the only name on a right-hand side falls through to "assigned from a literal" → SERVER, which happened to be right for the wrong reason |
| **R7** | the `IDENT` regex matched **JS keywords and property names** | `const month = new Date().toISOString().slice(0, 7)` yielded `new`, `Date`, `toISOString`, `slice`. Only `Date` resolves, so the right-hand side was MIXED and `:6023` was a third state. Nothing about that line is unresolvable — the walk was tracing grammar |

**R5 also prevents an over-report:** with R5 off, the shadowing fixture — a
parameter with an outer declaration of the same name — flips to CALLER. A
parameter shadows the outer binding, so R4 is asked **first**.

### R7 fired in BOTH directions, and the second one is the finding

`R7` was adopted to close `:6023`. Spot-checking the newly-resolved lines in the
**opposite** direction then found `api/sd-data.js:13364`:

```
const ar = await fetch(rest('alf_clients?license_hash=eq.' + enc(licHash)
  + '&assigned_employee_id=eq.' + enc(String(session.employee_id))
  + '&select=client_id'), { headers });
```

`url_idents` had its **own** name filter and did not strip property names, so it
pulled `employee_id` out as if it were a variable, resolved **that** somewhere
else in the file, and reported the branch **CALLER** when its only caller-facing
name is a **SESSION** root. `url_idents` now shares `trace_names` with the rest
of the walk, and the cross-check that caught it is now two fixtures.

**EVERY UNDER-REPORT HAD ALREADY GONE TO ZERO BY THEN, SO THE ONLY DIRECTION
LEFT THAT COULD FIND ANYTHING WAS THE OVER-REPORTING ONE.** A census checked
only for what it missed would have shipped this. The independent confirmation
that the fix is right rather than merely different: the SESSION counts returned
to **exactly** b26's values (B: 1, C: 2) and nothing else moved.

### The figures, `CRITERIA_VERSION 2026-10-16.b27r.1`, 26/26 fixtures

| shape | total | write-guarded | GET CALLER | SESSION | UNRESOLVED | SERVER-ONLY | UNCLASSIFIED |
|---|---|---|---|---|---|---|---|
| `A-helper` | 88 | 88 | 0 | 0 | 0 | 0 | 0 |
| `B-inline-503` | 70 | **22** | **35** | 1 | **0** | 10 | 2 |
| `C-200-empty` | 151 | 0 | **34** | 2 | **0** | 115 | 0 |
| `other` | 23 | 1 (`:15150`) | 10 | 0 | **0** | 12 | 0 |

**Against b26: class B CALLER 32 → 35, class C CALLER 16 → 34, UNRESOLVED
26 → 0.** b23 said class B was 13 CALLER / 33 SERVER-ONLY; b26 withdrew that to
32/9; it is **35/10**. b23 said *"0 of the 151 interpolates a caller value"*;
b26 withdrew that to 16; **it is 34.**

**THE 22 WRITE-GUARDED BRANCHES DID NOT MOVE**, and the list is byte-identical
to b26's. R5, R6 and R7 only touch the origin walk; the write/GET split is R1's.
That is the methodology working rather than luck.

**0 UNRESOLVED IS NOT THE THIRD STATE BEING RETIRED.** Three fixtures still
produce it — a name declared nowhere, a function with no call sites, a call with
fewer arguments than the position — so the mechanism can still say it and 0 is a
measured answer rather than a collapsed one. The module docstring says this too,
because the next session will read that and not this.

### Ablation, per RULE per FIXTURE — every one load-bearing

```
WITHOUT R1 span-bounded-at-next-fetch               1 fixture(s) change
WITHOUT R2 guard-binds-to-own-variable              1 fixture(s) change
WITHOUT R3 follow-caller-through-assignments       11 fixture(s) change
WITHOUT R4 resolve-a-parameter-across-call-sites    3 fixture(s) change
WITHOUT R5 scope-bounded-lookback-and-param-shadowing  3 fixture(s) change
WITHOUT R6 a-root-is-never-discarded-as-noise       2 fixture(s) change
WITHOUT R7 a-js-keyword-is-not-an-identifier        1 fixture(s) change
```

### Spot-checked in both directions on the real file

* `:14886`, `:18338` — `rest(resource + '?license_hash=eq.' + enc(licHash)...)`.
  **CALLER correct, and it is the strongest form there is: the caller chooses
  the table name.**
* `:10556` — **CALLER**, which is what b26 resolved **by hand** and reported as
  the proof its third state was earning its keep. The mechanism now agrees
  without the hand.
* `:13724` — `famP` is `const famP = payload || {};` at `:13227`, 497 lines up.
  **CALLER correct**, and only R5 can see it.
* `:13364` — **SESSION**, after the over-report fix above.
* `:6023` — **SERVER-ONLY**, `new Date()`.
* 4 of the 115 class-C SERVER-ONLY sampled: `:2597`/`:3270` trace only `sel`
  (`const sel = 'sd_supplier_lead_times?...' + enc(licHash)`), `:2851`/`:3391`
  only `cols` (a column-name string literal). **SERVER-ONLY correct — the
  widened window did not invent reachability**, and 115 of 151 staying put is
  the evidence that it did not.

### Routed, not installed

`tools/` is cc's. Full source inline in
`docs/2026-10-16-fourth-b27-branch-census-routed-to-cc.md`, and **the b26
routing doc now carries a SUPERSEDED banner naming this one** — because a
reader who opens the older file would otherwise install a three-rule census
that reports a SESSION branch as CALLER. `tools/branch_census.py` **still does
not exist**; this is the fifth batch in which the census has lived only in a
scratchpad and a routing doc.

---

## 4. WHAT THIS BATCH LEFT UNPROVEN

* **NO LIVE VERIFICATION.** Nothing ran against a real Supabase. No production
  row read, no table touched, no deployment fetched.
* **The Tier A discharge write.** §1 — blocked, not attempted.
* **The census is still not a gate.** Nothing runs it on a push, so the
  staleness convention applies to it like everything else.
* **`sairnbuild.html` was mutated only in COPIES** and never re-extracted block
  by block, never rendered.
* **`origin()`'s lookback is now unbounded but still NEAREST-BACKWARD**, which
  is a heuristic and not scope analysis. The shadowing fixture covers the
  parameter case; a `let` re-declared in a sibling block is not covered, and no
  fixture claims it is.
* **`KEYWORDS` is a hand-written list of 14 words**, not the JS grammar. It is
  enough for the one line it was built for and is not a parser.
