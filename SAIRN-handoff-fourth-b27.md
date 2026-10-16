# HANDOFF — fourth / ted, batch b27 (RESUMED), 2026-10-16

**READ THIS FILE ONLY.** It is the whole state.

**b27 WAS DISPATCHED ON 2026-10-15 AND DIED HAVING LANDED NOTHING.** Its
manifest was opened, item 1's test work was done and ablated, and then the
session ended with **both test files UNCOMMITTED in the working tree** and
`docs/batch-manifest-fourth-b27.json` **UNTRACKED**. This session resumed from
that, and the first thing it found is in §1 and is about b27 itself.

**FOUR THINGS BEFORE ANYTHING ELSE:**

1. **A MANIFEST EVIDENCE STRING CITED A FILE THAT WAS NEVER WRITTEN.** b27's
   item 1 evidence says *"the verdict body lives in
   `docs/2026-10-15-fourth-b27-findings.md`"*. **That file does not exist — not
   at HEAD, not on origin, not on disk.** §1
2. **MY OWN PREDECESSOR'S REPAIR OPENED A HOLE, AND ONLY A SECOND ABLATION
   FOUND IT.** The retry could be changed from `'write'` to `'read'` and the
   suite stayed at **25 passed, 0 failed**. §2
3. **THE TIER A DISCHARGE WRITE IS BLOCKED FOR THE SECOND CONSECUTIVE BATCH**,
   by a different session each time, on the same single shared file. §3
4. **THE 26 UNRESOLVED CENSUS LINES ARE 0, AND b26's STATED REASON WAS RIGHT
   FOR 3 OF THE 26.** Three separate mechanisms were each independently enough
   to hide a one-line `const` — and one of the three fixes also removed an
   **OVER-report**. §4

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**Working files (this session's scratchpad):**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\ed5b1771-4b30-429a-98d0-aa98a2a7e664\scratchpad\`
`b27r_bld_ablation2.py` + `_repaired.log` + `_fixed.log`,
`b27r_probe_fixed.log`, `b27r_branch_census.py`, `b27r_census.log`,
`b27r_census_ablate.log`, `b27r_census_why.log`, `b27r_census_why2.log`,
`b27r_why_inherited.py`, `b27r_census_why_AS_OF_b27_R1toR4.log`.
**b27's own first-session files are under `990beb38…`** (`b27_bld_ablation.py`,
`branch_census_b27.py`, `b27_census*.log`) and are a DIFFERENT directory.

---

## 1. WHAT b27 ACTUALLY LEFT BEHIND, AND WHY THE MANIFEST READ WRONG

| | | command |
|---|---|---|
| `docs/batch-manifest-fourth-b27.json` | **UNTRACKED** | `git status --porcelain` |
| `tests/sairnbuild_server_wins.js` | **MODIFIED, uncommitted** | same |
| `tests/run_sairnbuild_server_wins_sabotage_probe.py` | **MODIFIED, uncommitted** | same |
| `docs/2026-10-15-fourth-b27-findings.md` | **DOES NOT EXIST** | `ls`, and not on origin |
| `HEAD` vs `origin/main` on arrival | **6 BEHIND, 0 ahead** | `git rev-list --left-right --count origin/main...HEAD` |

**THE FINDING: b27's item-1 evidence string names a findings document that was
never written, and nothing could tell that from one that was.** The manifest
validated — `batch_manifest.py` checks that `done` carries a re-runnable
pointer and that `blocked` carries a reason, and it does not and cannot check
that a cited path resolves. The string was true about intent at the moment it
was typed and false by the time the session ended. **This is the first
cross-session case of the staleness convention applying to a batch manifest
rather than to a standing document.**

**FOR cc, AS A ROUTED ITEM:** `batch_manifest.py --check` should resolve every
`docs/…`, `tests/…`, `api/…`, `tools/…` or `sql/…` path that appears in an
evidence string and report **COULD NOT RESOLVE** per path — not fail the
manifest, because a scratchpad path is legitimate and a file may land in the
same commit, but **say so**, because a pointer nobody follows is not evidence.
That is one `re.findall` and one `os.path.isfile`, and it would have caught
this the moment b27 was read.

---

## 2. ITEM 1's TEST WORK — AND THE HOLE THE REPAIR OPENED

cody's measurement was right and is restated in
`docs/2026-10-16-fourth-b27-findings.md` §2. The short form: the suite asserted
the literal `key==='bld_bids'` appears in `bldRetryPending`, that literal is
gone from `sairnbuild.html`, and **both surviving occurrences are comments** —
one of them *inside* `bldRetryPending`, explaining the removal. **The assertion
was satisfied by the comment documenting the removal of the thing it asserted,
and the sabotage arm guarding it was ANCHOR-0 at the same time.**

### 2.1 b27's repair closed five mutations and opened a sixth

`<scratch>/b27r_bld_ablation2.py`, ten mutations against a **COPY** of
`sairnbuild.html`, the live tree never written, exit codes from
`subprocess.returncode`:

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

**The repair collapses every string literal to `''` before matching. That is
exactly what closes M5 and M7, and it is exactly what blinds the assertion to
WHICH string the first argument was.** A retry changed to `'read'` drains the
pending queue with a call that fetches rows and saves nothing, so every
stranded record stays stranded while the retry reports success — and the arm
whose entire subject is the retry's **write** stayed green.

**FIXED WITH TWO COPIES AND TWO ASSERTIONS, NEITHER SUFFICIENT ALONE:**
**(A)** comments stripped **and** strings collapsed — proves the call is real
executable code (M5, M7). **(B)** comments stripped **only** — proves the verb
is `'write'` and the cell is `[key]` (M6, M9). A mutation hiding the call in a
string satisfies (B) and fails (A); a mutation changing the verb satisfies (A)
and fails (B).

**RE-ABLATED: 10 of 10 REFUSED, every refusal on the NAMED arm** — the harness
reads the red arm's own line out of stdout, so a mutation refused by some other
arm is not credited to this one. Baseline still 25/0 exit 0.
`<scratch>/b27r_bld_ablation2_fixed.log`.

### 2.2 Probe side — arm 15, and why 6/14/15 are all three present

b27's session added **arm 14** (plant `false`). This session added **arm 15**
(plant `'read'`), because nothing planted the verb mutation and the new
assertion would otherwise rest on something nobody had made fail in that
direction.

`python tests/run_sairnbuild_server_wins_sabotage_probe.py` →
**ALL 19 ARMS PASS, 15 mutations, exit 0**, worktree copy byte-identical again,
suite green again, and its own last arm reports **it left nothing newly dirty**
(2 files were already modified before it started and are not its doing).

**6** proves the flag argument must exist, **14** proves it must not be falsy,
**15** proves the call retried is the write. **No one of the three implies
either of the others**, which is why none was replaced by the next.

---

## 3. THE TIER A DISCHARGE WRITE — BLOCKED TWICE, BY DIFFERENT SESSIONS, ON ONE FILE

| | |
|---|---|
| record | `cody 2026-10-15T15:12:47Z`, resource **`bld_bids`** (Tier A) |
| blocked on | `docs/tier-a-reviews.json` |
| in b27 | **cc** held it from `2026-10-15T16:55:20Z` — three minutes before the first attempt |
| in b27 resume | **hank** holds it from `2026-10-16T11:17:27Z` — one minute before this attempt. `CLAUDE_PID 26072` **RUNNING**, confirmed at 11:17 and again at 11:43 |
| state | **NOT STARTED. Flagged back, not reworded.** |

Per the standing rule the blocked item **stops and waits for a go-ahead**
rather than proceeding under a disclosure. My claim string declares the
exclusion in those words and the task was **not** reworded to slip the matcher.

**THE REVIEW WORK IS COMPLETE AND ABLATED** — §2 is it, and the verdict body is
in `docs/2026-10-16-fourth-b27-findings.md` §2, which **exists**, unlike its
predecessor. **Only the write into `docs/tier-a-reviews.json` is outstanding,
and it is one command once hank releases.** Read the runway from
`tier_a_review_gate.py --list`, not from this line.

**THIS IS A STRUCTURAL PROBLEM AND IS WORTH FIXING RATHER THAN RE-SUFFERING.**
`docs/tier-a-reviews.json` is a **single shared document** every Tier A
discharge by any of four agents must write whole, so a review by X of a record
raised by Y is routinely blocked by Z holding the file for an unrelated row.
**Two consecutive batches lost the same item to it.** **FOR MICHAEL / cc:** it
wants precisely the treatment b26 §3.3 demanded for closed periods — one
**append-only** record per discharge (a JSONL, or a per-agent shard, with the
read unioning them) rather than one document every writer must take whole. That
makes this class of block structurally impossible instead of a thing each batch
re-discovers.

---

## 4. ITEM 2 — 26 UNRESOLVED → 0, AND THE REASON WAS NOT INTER-PROCEDURAL

b26 reported **26 UNRESOLVED** and named the reason: `origin()` is
intra-procedural, so a parameter has no `const <name> =` to find. b27 built
**R4** — resolve a parameter by unioning its call sites, unsafe-wins, 5
fixtures — and the population fell **26 → 20**.

**AND THEN IT STOPPED, WITH 19 OF THE 20 IN CLASS C AND R4 HAVING TOUCHED NONE
OF THEM.** A bucket of 20 nobody can take apart is the same lower bound R3 was
built to kill, one level further in.

So this session built **`--why`**: it names, **per line**, the identifier that
stalled the walk and why, and it **cross-checks its own answers against
`origin()`** — a divergence prints `MIRROR DIVERGED` and is exit 2, never a
quiet re-classification. It named **`resource` on 16 of the 20 lines.**

### `api/sd-data.js:748` is `const resource = body && body.resource;`

One line. The handler runs to `:18867`. `resource` is the **table name**, chosen
by the caller. **THREE SEPARATE MECHANISMS were each independently enough to
make it unreachable:**

| | what it was | what it hid |
|---|---|---|
| **R5** | lookback capped at **400 lines** | `:748` is 14,000 lines above its last reader. **b23's 14-line window and b24's fixed window, a THIRD time, inside the rule built to kill them.** `:13724`'s `famP` is declared at `:13227` — **497 lines up**, just outside the cap |
| **R6** | `body` was in `CALLER_ROOTS` **and** in `NOISE`, and `NOISE` was filtered first | the walk dropped `body` before the root lookup could answer CALLER. `headers` had the same treatment and was invisible because dropping the only name on a RHS falls through to SERVER — **the right answer for the wrong reason** |
| **R7** | `IDENT` matched **JS keywords and property names** | `new Date().toISOString().slice(0,7)` yielded four names, one resolvable. `:6023` was a third state because the walk was tracing grammar |

**R5 also stops an OVER-report:** with R5 off the shadowing fixture flips to
CALLER, so a parameter now shadows the outer binding and R4 is asked **first**.

### R7 fired in BOTH directions, and the second is the finding

R7 closed `:6023`. Spot-checking the newly-resolved lines in the **opposite**
direction then found `:13364`, which interpolates
`enc(String(session.employee_id))`: `url_idents` had its **own** name filter,
did not strip property names, pulled `employee_id` out as a variable, resolved
**that** elsewhere in the file, and reported the branch **CALLER** when its only
caller-facing name is a **SESSION** root.

**EVERY UNDER-REPORT HAD ALREADY GONE TO ZERO, SO THE ONLY DIRECTION LEFT THAT
COULD FIND ANYTHING WAS THE OVER-REPORTING ONE.** A census checked only for
what it missed would have shipped this. Independent confirmation the fix is
right rather than merely different: **the SESSION counts returned to exactly
b26's values (B: 1, C: 2) and nothing else moved.**

### The figures — `CRITERIA_VERSION 2026-10-16.b27r.1`, 26/26 fixtures

| shape | total | write-guarded | GET CALLER | SESSION | UNRESOLVED | SERVER-ONLY | UNCLASSIFIED |
|---|---|---|---|---|---|---|---|
| `A-helper` | 88 | 88 | 0 | 0 | 0 | 0 | 0 |
| `B-inline-503` | 70 | **22** | **35** | 1 | **0** | 10 | 2 |
| `C-200-empty` | 151 | 0 | **34** | 2 | **0** | 115 | 0 |
| `other` | 23 | 1 (`:15150`) | 10 | 0 | **0** | 12 | 0 |

**Against b26: B CALLER 32 → 35, C CALLER 16 → 34, UNRESOLVED 26 → 0.** b23 said
class B was 13/33; b26 withdrew that to 32/9; **it is 35/10**. b23 said *"0 of
the 151 interpolates a caller value"*; b26 withdrew that to 16; **it is 34**.

**THE 22 WRITE-GUARDED BRANCHES DID NOT MOVE** and the list is byte-identical to
b26's — R5/R6/R7 only touch the origin walk; the write/GET split is R1's.

**0 UNRESOLVED IS NOT THE THIRD STATE BEING RETIRED.** Three fixtures still
produce it — a name declared nowhere, a function with no call sites, a call with
fewer arguments than the position. The module docstring says so too, because the
next session reads that and not this.

**ABLATION, per RULE per FIXTURE — every one load-bearing:** R1 **1**, R2 **1**,
R3 **11**, R4 **3**, R5 **3**, R6 **2**, R7 **1** fixture(s) change.

**SPOT-CHECKED BOTH WAYS on the real file:** `:14886`/`:18338` CALLER (the
caller chooses the **table name** — the strongest form there is); `:10556`
CALLER, which is what **b26 resolved by hand** as proof the third state earned
its keep, now reached mechanically; `:13724` CALLER via the 497-line
declaration; `:13364` SESSION after the fix; `:6023` SERVER-ONLY; and 4 of the
115 class-C SERVER-ONLY sampled (`sel`, `cols` — a URL prefix and a column-name
literal) and correct. **115 of 151 staying put is the evidence the widened
window did not invent reachability.**

### Routed, not installed — and the b26 routing doc now says so

`tools/` is cc's. Full source inline in
`docs/2026-10-16-fourth-b27-branch-census-routed-to-cc.md`, and
**`docs/2026-10-15-fourth-b26-branch-census-routed-to-cc.md` now carries a
SUPERSEDED banner naming it**, because a reader who opened the older file would
otherwise install a three-rule census that reports a SESSION branch as CALLER.
**`tools/branch_census.py` STILL DOES NOT EXIST**; this is the fifth batch in
which the census has lived only in a scratchpad and a routing doc.

---

## 5. ONE DEFECT IN MY OWN EVIDENCE, DISCLOSED

**The final `--why` run OVERWROTE `b27r_census_why.log`**, which held the
20-line diagnosis the findings doc cites for the `resource` figure. It is **not
quoted from memory**: `<scratch>/b27r_why_inherited.py` reproduces it by running
the same census with **R5/R6/R7 ablated off**, and the counts (16 of 20 lines
stall on `resource`; `NOT-A-PARAM` 16, `NO-DECL-NO-FN` 8, `MIXED-RHS` 7 reasons
over 20 lines) are **counted out of the regenerated log mechanically, not
read**.

---

## 6. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| on arrival | **6 behind, 0 ahead** of `origin/main`; rebased, then pushed the claim | `git rev-list --left-right --count origin/main...HEAD` |
| claim | **HELD**, `CLAUDE_PID 9416`, re-seated after arriving DEAD from the b27 session's pid | `sairn_claim.py own` |
| claim published | **yes, on `origin/main`** — the first attempt said `NOT CLAIMED` because the push was behind, and that refusal is the thing that got read | — |
| status row | `working`, re-stamped this session | `sairn_status.py` |
| `SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` | **none used, any form** | — |
| `.claude/settings.json` | **not edited, not committed** | — |
| hooks | **untouched and never re-added** | — |
| files written under `api/` `sql/` `tools/` | **0** | `git status --porcelain` |
| auditor clones | **not entered** | — |
| `git stash` | one taken to rebase, **popped, 0 remaining** | `git stash list` |
| b27 batch manifest | **6 items: done 4, blocked 1 (§3), open 1 (the push)** | `batch_manifest.py --check --agent fourth --batch b27` |

**The push, its ancestry proof and the landed-on-origin read-back are in §8,
written after they happened.**

---

## 7. WHAT IS OPEN, BY OWNER

### cc — `tools/`

1. **INSTALL THE CENSUS** from
   `docs/2026-10-16-fourth-b27-branch-census-routed-to-cc.md` — seven rules, 26
   fixtures, `--why`, `--ablate`. `REPO` to become a repo-root derivation,
   everything else unchanged. **Five batches, five scratchpads; the b26 routing
   doc is superseded and banner-marked, so install from the b27 one.**
2. **`batch_manifest.py --check` should RESOLVE the paths in evidence strings**
   and report COULD NOT RESOLVE per path. §1 — one `re.findall` and one
   `os.path.isfile`, and it would have caught b27's phantom findings doc.
3. **`docs/tier-a-reviews.json` wants to be append-only.** §3 — two consecutive
   batches lost the same item to one shared document.
4. Unchanged from b26: `tier_a_review_gate.py --amend`; wire **ONE** anchor-rot
   tool into a gate; R3's 48 citation ranges; and **the convention-numbering
   check routed in `docs/2026-10-12-fourth-b5-routing.md:585-615` is still not
   built** — b25, b26 and now b27 all moved a prose denominator by hand.

### hank — `api/`

Unchanged from the b26 handoff §9 and **re-stated here without re-verification,
which is why it is not restated in detail**: H3 first (the append-only closings
resource and the named refusal of `payroll_closed_periods` at the generic
`sen_settings` path — **until it exists a paid period can be unfrozen by a
billing session with one POST**), then H2, then H1 with the 2×2 re-run
confirming ARM A goes RED; then Q4's `partially_closed`, Q(b)2's EVV basis,
Q(c)'s two purity headers; then b24 F3 and F4. **Read b26's handoff for those,
not this paragraph.**

**AND ONE THING b27 ADDS FOR hank:** the census now says **34 of the 151
class-C branches are caller-reachable**, not b23's 0 and not b26's 16, and
**35 of class B's 46**, not 13 and not 32. The `:13503`/`:17127` pair and the
22-branch list are unchanged.

### cody — `tests/`

1. **Arm Z's `else` branch, then RE-RUN THE ABLATION** — unchanged, HIGH.
2. `known-red-suites.json` blob-scope row → RECOVERED; the control arm's
   hardcoded *"ten failures above"* → read off `failed.length`.
3. **b24 F1** — re-anchor the `leg_aftercare` probe, with an arm that fails when
   the extraction anchor stops matching.
4. A failing-first arm driving a `23514` through one of the 22 and a `42703`
   through one of the 151.
5. **NEW, and it is about your own two files:** `tests/sairnbuild_server_wins.js`
   and `tests/run_sairnbuild_server_wins_sabotage_probe.py` were edited by me
   under a declared claim while yours was expired. **The arm now carries TWO
   assertions and the probe carries arms 6, 14 and 15.** If you re-shape that
   arm, the property to keep is **both** copies: strings collapsed proves it is
   code, strings intact proves it is the `'write'`.

### Michael

**Nothing blocking from b27.** Carried, unchanged, from b26: the one-person-
agency self-approval question; whether any real visit was underpaid before today
is **not establishable from the repo**; and **no agency has a
`payroll_closed_periods` row, so the freeze has never run on real data by
anyone.**

**ONE NEW THING FOR YOU, and it is a process call not a code one:** §3. Two
batches in a row lost the same Tier A item to one shared JSON file, and the fix
is a schema decision somebody has to make.

---

## 8. WHAT b27 RESUME PROVED vs LEFT UNPROVEN

**PROVED, driven or measured:** that b27 landed nothing and that its manifest
cited a file that was never written; that the b27 suite repair closed M1–M5 and
**opened M6**, with the retry readable as `'read'` at 25/0; that the two-copy
fix closes all ten, each on the named arm; that the probe is 19 arms / 15
mutations / exit 0 and leaves nothing dirty; that `resource` stalled 16 of the
20 UNRESOLVED lines; that **three** independent mechanisms hid
`api/sd-data.js:748`; that R7 removed an **over**-report as well as an
under-report, with the SESSION counts returning to b26's exactly; that all
seven census rules are load-bearing by per-fixture ablation; that the 22
write-guarded branches did not move; and that 115 of 151 class-C branches are
still SERVER-ONLY after the window was widened.

**LEFT UNPROVEN, and none of it is recorded as checked:**

* **NO LIVE VERIFICATION.** Nothing ran against a real Supabase. **No production
  row read, no table touched, no deployment fetched.**
* **The Tier A discharge write.** §3 — blocked, not attempted, not partly done.
* **The census is still not a gate** and `tools/branch_census.py` still does not
  exist.
* **`origin()`'s lookback is unbounded but still NEAREST-BACKWARD** — a
  heuristic, not scope analysis. The parameter-shadowing case has a fixture; a
  `let` re-declared in a sibling block does **not**, and nothing claims it does.
* **`KEYWORDS` is a hand-written list of 14 words**, not the JS grammar.
* **`sairnbuild.html` was mutated only in COPIES**, never re-extracted block by
  block and never rendered.
* **Everything in §7 attributed to hank's list is carried from b26 and was NOT
  re-verified this batch.**
