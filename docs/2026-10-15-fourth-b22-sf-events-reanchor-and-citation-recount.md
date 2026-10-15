# METHODOLOGY — the `sf_events` re-anchor, and the citation total re-counted from source

**fourth / b22, 2026-10-15.** Item 5 of the batch. Two halves: re-anchor the
rotted citation in the `sf_events` row of `docs/CRITICALITY-TIERS.md`, and
**re-count the stale-citation total from source rather than from the b21
document.** Both halves produced a correction to the instruction that sent me,
and both corrections are measurements.

---

## 1. THE INSTRUCTION SAID THE SEVENTH ANCHOR. MEASURED, IT IS THE SIXTH.

The `sf_events` cell carries its anchors as **quoted strings, not line
numbers** — fourth b20 converted them after all seven line citations in that one
cell had rotted. The cell states its own acceptance rule: *"every quoted anchor
in this cell must resolve EXACTLY ONCE in `sairnfreedom.html`"*.

**Enumerated from the cell's own backticked spans rather than by hand**
(`scratchpad/sf_events_allspans_b22.py`, log `…_b22.log`) — hand-numbering a
22-span table cell is how an off-by-one becomes a confident edit to the wrong
anchor:

| # | anchor | count in `sairnfreedom.html` |
|---:|---|---:|
| 1 | `function eventRefusals(e){` | 1 |
| 2 | `function sfSessionRefusals(c, excludeId){` | 1 |
| 3 | `function sfScheduleEvent(){` | 1 |
| 4 | `(r.alcohol?'<span class="tag warn">Alcohol</span>':'--')` | 1 |
| 5 | `alcohol:e.alcohol, id:e.id, removable:true` | 1 |
| **6** | `if(ev && ev.sessionId) st(K_SESSIONS, getSessions().filter(` | **0 — ROTTED** |
| 7 | `if(getEvents().some(function(e){ return e.sessionId===s.id; })) return;` | 1 |

**Anchor 7 resolves exactly once and needed nothing. Anchor 6 is the one that
had gone to zero.** The edit was applied to 6.

**WHAT MOVED THE CODE.** hank b12's F6 rewrote `sfDeleteEvent()`
(`sairnfreedom.html:5222-5254`). The old line chose its toast on the pointer
being **truthy** and never on whether the filter removed anything, so a stale
pointer announced a removal that did not happen. The new shape counts:

```js
var removedSessions = 0;
if (ev && ev.sessionId) {
  var before = getSessions();
  var after = before.filter(function(s){ return s.id!==ev.sessionId; });
  removedSessions = before.length - after.length;
  st(K_SESSIONS, after);
}
```

**The row's integrity argument is unchanged and is now better evidenced.** The
delete still matches on the stored id alone — which is the whole basis for
`sf_events` being Tier A on INTEGRITY — and it can now distinguish *a pointer
that resolved* from *a pointer that resolved to nothing*. That third outcome was
the invisible one.

**THE NEW ANCHORS, both verified to resolve exactly once BEFORE the write:**
`var after = before.filter(function(s){ return s.id!==ev.sessionId; });` for the
stored-id match, and `removedSessions = before.length - after.length;` for the
count. **So the cell now carries EIGHT anchors, not seven** — stated in the cell
itself, because a count that is quietly wrong is how this register drifts.

**HOW THE EDIT WAS MADE, because the row is one 4,292-character table line.**
Not a split on `|`. `scratchpad/reanchor_sf_events_b22.py` locates the single
row by its `| \`sf_events\` |` prefix, refuses unless the substring to replace
occurs **exactly once**, refuses if the replacement text contains a pipe,
asserts the **pipe count on that line is identical before and after** (7 → 7),
and verifies both new anchors resolve exactly once in the app before writing
anything. `docs/CRITICALITY-TIERS.md` is 487 KB and over the standing-document
read ceiling, so it was never opened wholesale.

**After the write:** all **8** anchors resolve exactly once, and
`python tools/criticality_tier_check.py` reports **PROBLEMS:0** with
`RESOURCE_ROWS:391`, `TIER_A:275`, `ROWS_MIGRATED_TWO_AXIS:391 of 391`.

### One thing I found and did NOT fix, because it is not an anchor

The cell also carries the bare prose spans `` `eventRefusals()` ``,
`` `liquorServiceCheck()` `` and `` `sc_auth` ``, each of which counts **0** in
`sairnfreedom.html` — not because the functions are missing (`eventRefusals` and
`liquorServiceCheck` both exist, at `:4582` and in the refusal path) but because
the register writes them with empty parentheses and the source writes them with
arguments. **They are prose references, not anchors, and the cell's rule is
scoped to anchors.** Named here so the next reader does not count them as six
more rotted citations. **If the anchor-rot check cc is building treats every
backticked span as an anchor, these three are its first three false positives**
— routed to cc with that example.

---

## 2. THE CITATION TOTAL, RE-COUNTED FROM SOURCE — AND b21'S FIGURES DO NOT REPRODUCE

`scratchpad/citation_staleness_b22.py`, log `citation_staleness_b22.log`.
Predicate printed with the result rather than described:

    ([A-Za-z0-9_./-]*):(\d{1,5})   not followed by a digit or a dot

| | **b22, measured now** | b21, as written |
|---|---:|---:|
| TOTAL line citations | **571** | 551 |
| EXPLICIT — path has a known extension **and resolves to a real file** | **198** | 196 |
| path-shaped but the file does not exist in the repo | **0** | — |
| **BARE `:NNNN`** — UNASSESSABLE, never folded into a total | **373** | 355 |
| EXPLICIT + unresolved + BARE | **571** (adds up) | — |
| **PROVABLY STALE** (line beyond EOF) | **0 of 198** | 0 of 196 |
| LIKELY STALE (lands on a blank or pure-comment line) | **39 of 198 (20%)** | 37 of 196 (19%) |

### THE DELTA IS ENTIRELY PREDICATE, AND THAT IS PROVED RATHER THAN ASSUMED

`docs/CRITICALITY-TIERS.md` has **not changed since b21's measurement**:
`git diff --stat 7a5e6a11 HEAD -- docs/CRITICALITY-TIERS.md` is **empty**, and
the same script run against `git show HEAD:docs/CRITICALITY-TIERS.md` and
against the working tree gives **571 / 198 / 373 on both** — so my own
re-anchor edit added **zero** citations too.

**The file is byte-identical and the numbers are different. Therefore b21's
551 / 196 / 355 were not re-derivable, and the difference is the predicate, not
the register.** That is the eighth cross-domain discipline landing on my own
work: a figure quoted without the predicate that produced it stops being a
measurement the moment anybody re-measures.

**CARRY THESE, NOT b21's**, and carry them with the predicate attached. The
standing conclusion is unchanged and is the one that matters: **0 provably
stale, and 373 of 571 — 65% — cannot be mechanically checked at all** because
the citation names a line and not a file. That is a form problem, not a
staleness problem, and converting a cell to quoted-string anchors (which is what
`sf_events` already is) is the fix that removes the whole class.

---

## 3. THE hover2 b36 ROUTING, RE-DERIVED — AND THE RULE IS NOW MECHANICAL

**Added after the batch's six items, on hover2's routing.** `SAIRN-digest-H2-b36.txt`
listed `docs/CRITICALITY-TIERS.md:358` under EVIDENCE-path as *"still unfixed,
re-grepped"*, and `SAIRN-handoff-H2-b36.md` item 4 queued it as open. **Both are
timing artefacts and hover2 said so itself**, in the same handoff: *"fourth's
b22 appears to have landed new commits as this batch wrapped up … not confirmed
whether the actual fix landed with it."* It had. **Re-derived from source rather
than taken from either document:**

| | anchors | findings |
|---|---:|---:|
| the row at `7a5e6a11` — what hover2 re-grepped | 7 | **1 — ROTTED, anchor 6 of 7** |
| the row at HEAD — after the b22 re-anchor | 8 | **0** |

(`scratchpad/sf_anchor_counterfactual_b22.log`, both rows run against the same
live `sairnfreedom.html`.)

**AND IT SETTLES THE ORDINAL INDEPENDENTLY.** hover2 called it *"the 7th"*; the
b22 instruction called it *"the seventh"*; the program says **6 of 7**, twice,
by two different enumerations. Three descriptions, one anchor, and the only one
that is reproducible is the one a program produced.

### The cell's code facts, re-read at HEAD rather than assumed

Re-anchoring proves the quoted text exists. It does not prove the cell's
argument, so the argument was re-read:

* `eventRefusals()` runs `liquorServiceCheck()` on **both ends** of an alcohol
  event, and the OAC 4301:1-1-49(B)(3) consumption-as-well-as-sale reasoning is
  in the source comment, not just in the register.
* The gaming interlock really is **the Phase 3 function itself** —
  `out = out.concat(sfSessionRefusals({…}, null))`, with the source's own
  comment *"Not a re-implementation — the Phase 3 function itself."*
* `sfScheduleEvent()` **returns before any write** when refusals fire, and on a
  gaming success pushes a real row into `K_SESSIONS` with the same id it then
  stores on the event as `sessionId`.
* **The stored `alcohol` has exactly the two readers the cell names** — the
  table tag and the combined list. The other `b.alcohol` determinations in that
  file (`:5335-5376`) are **`sf_rentals`**, driven from the `hr-` hall-rental
  form, not from an event row. Checked because if they had been event readers
  the cell's tier argument would turn on `alcohol` rather than on `sessionId`.
* **The cell contains no line-number citation**, which is what it claims about
  itself: the only `:NNNN`-shaped token in it is `4301:1`, from the OAC
  regulation number. *(Worth noting for §2: regulation numbers are counted as
  BARE citations by that predicate, so the 373 is an upper bound on real bare
  code citations.)*

### THE FAILING-FIRST CHECK — `tools/sf_events_anchor_check.py`

**The cell stated its own acceptance rule in prose and nothing drove it, so it
went quiet for a day.** hank b12's F6 moved the text for a correct reason, the
anchor fell to zero, and the register kept asserting it until a human re-read
the cell. That is the eighth cross-domain discipline exactly: *nothing announces
the day a check stops testing anything.*

* **Criteria locked against synthetic fixtures first, 10/10 arms**, and the
  check refuses to judge real data if the lock breaks.
* **The failing-first arm is the real pre-b22 anchor text** —
  `if(ev && ev.sessionId) st(K_SESSIONS, getSessions().filter(` — which must
  come back ROTTED. If that arm ever passes, the tool has stopped working.
* **Both failure directions**: zero matches is ROTTED, more than one is
  AMBIGUOUS. A unique-match rule needs both arms, not one.
* **Entity escaping is driven in both directions** — an `&amp;`-escaped anchor
  must match the raw app text, and the unescape must not invent a match for
  text that is absent.
* **The false-positive class is an explicit arm**: a prose span with empty
  parentheses is ignored, not reported. `eventRefusals()`,
  `liquorServiceCheck()` and `sc_auth` all count 0 in the app, and a tool that
  treated every backticked span as an anchor would open with three false
  findings on this one cell.
* **No anchors at all is a FINDING, not a pass** — otherwise the check passes by
  measuring nothing, which is the shape this register keeps paying for.
* **It fails CLOSED**: a missing app file, a missing register, zero sf_events
  rows or more than one is **exit 2 COULD NOT RUN**, never exit 0.
* **It prints what it cannot tell you, every run**: a resolving anchor proves
  the text is there and unique; it does not prove the cell's claim *about* that
  text. No string match establishes *"removes the linked session by stored id
  only."*

**Live run: exit 0, 8 of 8 anchors resolve exactly once**
(`scratchpad/sf_anchor_check_b22.log`). The cell now **names the check inside
its own rule sentence**, so the rule and its enforcer cannot drift apart
silently.

**THIS IS NOT cc's ROUTED ANCHOR-ROT TOOL AND MUST NOT BE MISTAKEN FOR IT.**
That one is general over the whole register — the b20 spec, 8 requirements and
10 arms, including reporting bare `:NNNN` citations as UNASSESSABLE rather than
folding them into a total. This is one cell and one app file. **When the general
tool lands, delete this one rather than maintaining both**; the file says so in
its own header so that deletion is the expected end state and not a judgement
call later.

---

### THE ONE CLAUSE I AM ADDING TO THE CONVENTION

b21 proposed: print the command **and** the raw count. Driven twice more this
batch, it needs one more clause — **when a predicate names an identifier, say
which identifier.** hank's 400→503 count of 98 was anchored on a response
variable literally named `r`; 99 of the 157 real branches use that name and 58
do not, so a predicate that reads like a *shape* was actually a *name*, and its
output reported a sample as a population. Full account:
`docs/2026-10-15-fourth-b22-not-provisioned-helper-review.md` §1.
