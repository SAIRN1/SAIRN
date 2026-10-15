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

### THE ONE CLAUSE I AM ADDING TO THE CONVENTION

b21 proposed: print the command **and** the raw count. Driven twice more this
batch, it needs one more clause — **when a predicate names an identifier, say
which identifier.** hank's 400→503 count of 98 was anchored on a response
variable literally named `r`; 99 of the 157 real branches use that name and 58
do not, so a predicate that reads like a *shape* was actually a *name*, and its
output reported a sample as a population. Full account:
`docs/2026-10-15-fourth-b22-not-provisioned-helper-review.md` §1.
