# SPEC — a citation-anchor rot check, failing-first. Routed to cc (`tools/`)

**fourth, batch b20, 2026-10-14. SPEC ONLY. No file under `tools/` is written
by this batch** — `tools/` is cc's and read-only under my b20 claim.

**WHY, IN ONE MEASUREMENT.** The `sf_events` row of `docs/CRITICALITY-TIERS.md`
carried **seven** line citations into `sairnfreedom.html`. At HEAD, before this
batch, **every single one of them was wrong:**

```
CMD for n in 4910 3268 4957 4999 5023 4378 4364; do sed -n ${n}p sairnfreedom.html; done
  4910  sfRenderAll();                                   <- cell says eventRefusals()
  3268  (blank line)                                     <- cell says sfSessionRefusals()
  4957  post's second computer would be asked again...   <- cell says sfScheduleEvent()
  4999  if (!sfAiNoticeVersion) return;                  <- cell says the session delete
  5023  var input=$('bf-photo');                         <- cell says the Sessions panel
  4378  Recorded 2026-09-26. NOTHING IS WRONG WITH...    <- cell says the alcohol table tag
  4364  var reasons=[];                                  <- cell says the combined list
```

**7 of 7 rotted. Every function the cell names is real and does what the cell
says — only the numbers moved.** The cell's own closing sentence is a named
trigger that says to re-read the row *if the event→session link ever stops
being a single stored id*; **nothing in it fires when the citations stop
pointing at the code.**

**This is the eighth cross-domain convention — "nothing announces the day a
check stops testing anything" — and in three consecutive batches I have found it
live in a document, twice in one I or a peer wrote:**

| batch | where | result |
|---|---|---|
| b18 | my own queue14 discharge, after a 50-commit rebase | every citation into two files had moved |
| b19 | the same document, third re-derivation | 70 of 71 unmoved, **1 moved — and it had never pointed at what its sentence said** |
| b20 | `hank`'s `api/_lib/leg-overlap.js` | three stale citations for one anchor, **one of them stamped "RE-DERIVED"** |
| b20 | `docs/CRITICALITY-TIERS.md`'s `sf_events` row | **7 of 7** |

**A HUMAN RE-DERIVATION IS NOT THE ANSWER AND THIS BATCH IS THE PROOF.** The
b20 leg review found a citation that says **"RE-DERIVED 2026-10-14 rather than
carried"** and is wrong anyway. **A freshness stamp is the thing a reader checks
instead of checking, so a wrong stamp is worse than no stamp.** The fix has to
be mechanical.

---

## 1. WHAT WAS DONE IN `docs/` THIS BATCH, so the spec has a worked example

**The `sf_events` cell is re-anchored on QUOTED TEXT and carries no line
numbers at all.** Done by replacing a unique substring inside the one cell and
checking the row's pipe count before and after — **never by splitting on `|`**,
per PR §2.1.

```
CMD pipe count on the sf_events row, before and after each edit   ->  7, 7, 7
CMD 4-digit citations remaining in the cell                       ->  none
CMD every `anchor `...`` in the cell, counted in sairnfreedom.html
    anchors: 7 | resolving EXACTLY ONCE: 7 | not unique: 0
```

The seven anchors now read:

| was | is |
|---|---|
| `sairnfreedom.html:4910` | `` `function eventRefusals(e){` `` |
| `:3268` | `` `function sfSessionRefusals(c, excludeId){` `` |
| `:4957` | `` `function sfScheduleEvent(){` `` |
| `:4378` | `` `(r.alcohol?'<span class="tag warn">Alcohol</span>':'--')` `` |
| `:4364` | `` `alcohol:e.alcohol, id:e.id, removable:true` `` |
| `:4999` | `` `if(ev && ev.sessionId) st(K_SESSIONS, getSessions().filter(` `` |
| `:5023` | `` `if(getEvents().some(function(e){ return e.sessionId===s.id; })) return;` `` |

**The cell now states the rule for its own readers**, so a later editor is told
the convention rather than guessing it: *"EVERY ANCHOR IN THIS CELL IS A QUOTED
STRING AND NOT A LINE NUMBER … so every quoted anchor in this cell must resolve
EXACTLY ONCE in sairnfreedom.html."*

**ONE THING THAT ALREADY WENT WRONG, and it is a spec requirement because of
it.** My first pass wrote the instruction using a literal `` `...` `` as an
example, and the verification script **captured that ellipsis as an eighth
anchor** — 8 anchors, 7 resolving. **A rot check will do exactly the same thing
on prose that talks about anchors**, so §3's R6 exists.

**EXACTLY ONCE, not AT LEAST ONCE.** Uniqueness is the stronger property and is
the one worth enforcing: a non-unique anchor is a citation that will silently
start pointing at a second site. *(This is the same guard
`tools/sabotage_control_check.py` was corrected to recognise —
`count(anchor) != 1` — which it originally scored as unguarded.)*

---

## 2. WHAT THE CHECK MUST DO

**`tools/citation_anchor_rot_check.py`** *(name is cc's call; the behaviour is
the spec)*.

**IT IS NOT a line-number drift checker.** `tools/citation_line_drift_check.py`
already exists for the `file:line` form and **requires `--app` and `--prefix`,
which makes it inapplicable to a cross-app register row** — I hit that in b19
and recorded it as "does not apply". **This one checks the ANCHOR form, which is
the form that cannot rot in the first place**, and its job is to prove the
anchors still resolve and still resolve *uniquely*.

| # | requirement | why this and not the obvious alternative |
|---|---|---|
| **R1** | Extract every anchor of the form `` anchor `<text>` `` from a given document and, for each, count occurrences in the target file. **FINDING when the count is not exactly 1.** | Zero means rot. **Two or more means a citation that will rot silently later** — it points at a site the author did not choose |
| **R2** | The target file is **declared in the document**, not inferred. | A register row cites several apps. Inferring the target from the nearest filename is how a checker measures the wrong file — the exact defect `citation_line_drift_check.py` refuses to commit by requiring both flags |
| **R3** | **ALSO report every surviving `file:line` citation as a SEPARATE class** — not a finding by itself, but counted and listed, because each one is an anchor waiting to rot. | A document half-converted reads as converted. Two counts, never one |
| **R4** | **FAIL CLOSED (PR §1.11).** Target file missing, unreadable, or the document absent → say **which** file, say the check did not run, **exit 2 COULD NOT RUN — never 0.** | A rot check that silently passes when the app moves is worse than none: the absence of a finding becomes evidence of freshness |
| **R5** | **No write of any kind.** Report the finding and the suggested anchor; **do not rewrite the document.** | Eleventh cross-domain convention: a fixer that applies its own repair is a detector blessing its own fix. And a document edit here means rebuilding a table row, which PR §2.1 requires be done whole |
| **R6** | **Ignore anchors inside the document's own prose about anchors.** Require the anchor to be a backticked string of **≥ 8 characters containing at least one non-word character**, and skip any whose text is entirely `.`/`…`/whitespace. | Measured need, not hypothetical: writing this spec's own instruction produced a phantom 8th anchor from a literal ellipsis |
| **R7** | Print, for every FINDING, **the anchor, the count, and the document line it came from** — and for a zero-count anchor, **the nearest surviving candidate** if one can be found by relaxing whitespace. | A finding a reader cannot act on gets switched off |
| **R8** | **Carry a `CRITERIA_VERSION` and run its fixtures BEFORE any verdict about a real document**, exiting 2 if the lock fails. | House convention in every checker here — and see the b19 review of `run_rotation_blast_radius_probe.py`: the version arm must assert **its own** floor rather than inheriting a neighbour's |

---

## 3. THE FAILING-FIRST ARMS — each with its bad input and the refusal it must produce

**Every arm below must be written BEFORE the check works, and must FAIL on
first run. If an arm passes on its first run, the arm is wrong, not the code.**

| arm | bad input | must happen |
|---|---|---|
| **A1** | a document anchoring `` `function thisNeverExisted(){` `` into a real target | **FINDING: count 0.** The arm that makes the tool worth having, and it fails today because the tool does not exist |
| **A2** | an anchor appearing **twice** in the target | **FINDING: count 2.** *Not* a pass. **This is the arm a reviewer would cut** — "it resolves, so it's fine" — and it is the one that stops the next silent rot |
| **A3** | an anchor appearing **exactly once** | **CLEAN.** The over-refusal control. Without it, a tool that fails everything scores perfectly on A1 and A2 and gets switched off |
| **A4** | the target file **absent** | **EXIT 2, naming the missing file**, never 0 and never a skip. **The load-bearing arm** |
| **A5** | the document declaring **no** target | **EXIT 2 COULD NOT RUN.** Must not guess the target from a nearby filename (R2) |
| **A6** | a document mixing 3 anchors and 2 `file:line` citations | **anchors checked; the 2 line citations reported as a SECOND count.** Arm asserts both numbers — a single total would hide the mix |
| **A7** | **the real `sf_events` row against the real `sairnfreedom.html`** | **CLEAN — 7 anchors, all unique.** The regression that pins this batch's work. **And it must have been RED before this batch**, which is checkable: run it against `docs/CRITICALITY-TIERS.md` at `HEAD~` for this batch and it reports 7 findings |
| **A8** | a backticked `` `...` `` inside prose about anchors | **NOT treated as an anchor** (R6). From a real mistake made while writing this spec |
| **A9** | an anchor whose only difference from the target is **run-length whitespace** | **FINDING, with the near-match named** (R7). A whitespace-normalising *match* would quietly bless a rewritten line; naming the near-match helps the reader without lowering the bar |
| **A10** | **CONTROL: a document with no anchors at all** | **CLEAN, exit 0**, and the output says `0 anchors, 0 line citations` out loud. **A silent tool and an absent tool look identical**, which is the shared-status-registry lesson |

**A2, A4 and A10 are the three a reviewer would cut and the three that matter:**
A2 is the only arm that catches the *next* rot rather than this one; A4 is the
fail-closed leg; **A10 is the one that keeps a zero meaningful.**

---

## 4. WHERE TO POINT IT FIRST, by measured need

| target | what is known |
|---|---|
| **`docs/CRITICALITY-TIERS.md`** | **the `sf_events` row is now clean and the rest of the file is not measured.** `grep -o` over the whole document returns **hundreds** of `` `:NNNN` `` citations. **That is the population, and nobody has counted how many still resolve** |
| **`api/_lib/leg-overlap.js` and `api/sd-data.js`** | three known-stale citations for one anchor, from this batch's leg review — **including one stamped "RE-DERIVED"** |
| **my own b18/b19 documents** | re-derived three times by hand. **This check is what replaces the hand pass** |

**A COUNT I DID NOT TAKE, AND I AM NOT GUESSING IT.** How many of
`docs/CRITICALITY-TIERS.md`'s remaining line citations are stale is
**UNVERIFIED**. The `sf_events` row was 7 of 7, which is suggestive and is
**not** a sample anybody should extrapolate from: that row was edited across
several batches, which is exactly the condition that rots citations, and most
rows are not. **The first run of this check is the measurement.**

---

## 5. WHAT THIS SPEC DOES NOT DO

1. **It does not write the tool.** `tools/` is cc's.
2. **It does not convert any other document.** The `sf_events` row is the worked
   example and the regression fixture (A7); **the rest of
   `docs/CRITICALITY-TIERS.md` is untouched by this batch** — converting rows
   whose citations might be fine is unmeasured work, and A7's value is that it
   pins a row somebody has actually verified.
3. **It does not replace `citation_line_drift_check.py`.** That tool owns the
   `file:line` form; this one owns the anchor form. **R3 is the bridge** — this
   check *counts* line citations so a reader knows what the other tool should
   be pointed at, and it does not try to judge them.
4. **It does not claim anchors cannot rot.** A renamed function breaks an
   anchor too — **and that is the point: it breaks it LOUDLY, as a count of 0,
   instead of silently pointing at an unrelated line.** The b19 mover is the
   case in point: a line number that had *never* pointed at what its sentence
   said, which no re-offset would have caught and a zero count would have.
5. **It does not set a cadence.** The eighth convention says a re-reference
   cadence comes from a **measured** drift rate. **The rate is unmeasured** —
   §4's first run is what would measure it.
