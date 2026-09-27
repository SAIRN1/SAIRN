# How review coverage could reach Tier B/C rows — scoping, not a build

**Scoped 2026-09-26 (Fourth). Methodology item 8 of the queue. Nothing is built
here and nothing should be built from here without the decision in §6 being
made first.**

`tools/tiering_recheck.py` (methodology item 26 phase 2) reported its headline as
a blind spot rather than a result: **Tier A rows 266, reviewed 245 (93.2%). Tier
B/C 124 rows, reviewed 0 (0.0%).** The peer-review gate opens an obligation when
**Tier A code changes**, so a row left at B is never reviewed and no review can
ever surprise anybody about it. Under-tiering is the error the mechanism cannot
see, and it is the direction that leaves a real record under-protected.

This document scopes how that could change. Every number in it is measured in
§1, and the measurement is the thing that killed the obvious option.

---

## 1. Measured first, because the obvious option fails on the numbers

All figures 2026-09-26, commands in §7.

| | Tier A | Tier B/C |
|---|---|---|
| Rows in `docs/CRITICALITY-TIERS.md` | 266 | 124 |
| Ever reviewed | 245 (93.2%) | **0 (0.0%)** |
| **Named in a changed CODE line in the last 14 days** | **252 (95%)** | **33 (27%)** |
| Rows with NO code change in 14 days | 14 | **91** |

Review throughput, from `docs/tier-a-reviews.json`: **173 records across 11 days
— a median of 13 obligations per day — and 156 of 173 discharged (90%).** The
practice works. It is not the bottleneck.

**THE DECISIVE ROW IS THE THIRD ONE.** Tier A coverage is 93% because Tier A code
changes constantly — 95% of those rows appeared in a changed line inside two
weeks. The event-triggered gate fires so often on A that coverage accumulates as
a side effect.

**B/C rows do not change at that rate. 91 of 124 did not change at all.** So:

> **Widening the gate's trigger from "Tier A" to "any tier" would reach 33 of
> 124 rows in two weeks and would never reach the other 91.** It cannot close
> this gap, because the gap is mostly made of rows that do not change.

That is worth stating plainly because "just extend the gate to B/C" is the answer
everybody reaches for first, including me. It is a 27% answer costing roughly
+2.4 obligations/day (+18% review load), and it leaves 73% permanently invisible
while looking like a fix.

**THERE ARE TWO BLIND SPOTS HERE, NOT ONE**, and conflating them is why the first
answer looks adequate:

1. **Tier** — the gate only asks about A.
2. **Change** — the gate only fires on a diff, at ANY tier. 14 Tier A rows also
   went unchanged for two weeks; a row nobody edits is invisible to an
   event-triggered mechanism regardless of its tier.

Fixing (1) alone leaves (2). Anything that closes (2) has to be triggered by
**time**, not by an edit.

---

## 2. What the precedent actually says

**Cited at the level of the MECHANISM. No standard or primary source was fetched
in this pass** — the same disclosure convention the competitive audits in this
repo use. Each is named so somebody can go and read it before building; none
should be quoted as authority on this evidence.

### 2.1 Acceptance sampling with switching rules — ANSI/ASQ Z1.4, MIL-STD-1916

The relevant idea is not "inspect a sample". It is that **the sample size is
derived from the lot size and an accepted risk, and the RESULT changes the next
inspection**: normal inspection tightens when defects are found and relaxes when a
run is clean. A fixed 10% sample forever is not this pattern; it is a ritual.

**Maps to:** sample B/C rows per app, and when a sampled row turns out to be
under-tiered, **tighten that app** — raise its sampling rate until a clean run.
The platform already has the signal this would switch on: 74 of its defect
records carry `detection_method: independent-review`.

### 2.2 Rotational controls testing — financial-statement audit practice

An audit does not test every control every year. It tests a risk-ranked subset
and **rotates so that every control in scope is tested within a stated cycle**,
with the highest-risk ones excluded from rotation and tested every period.

**Maps to:** a stated cycle — say every B/C row read once per quarter — with the
cycle length being the promise, rather than a per-change trigger. This is the
option that closes blind spot (2), because a rotation is driven by the calendar.

### 2.3 Scheduled observation of NORMAL operations — LOSA, aviation

The closest precedent in intent. A Line Operations Safety Audit exists because
incident-triggered review is **structurally blind to routine operations**: if you
only look when something goes wrong, you never learn what normal looks like. The
answer was scheduled observation of ordinary flights, not more incident reports.

**Maps to:** exactly this problem. Our gate is incident-triggered where the
"incident" is a diff. 91 rows have no diffs. Reviewing them requires a mechanism
whose trigger is "it is time", and the precedent says that mechanism is worth
having even though nothing is wrong.

### 2.4 Randomised inspection with a stated detection probability — IAEA safeguards

The deterrent comes from the **published probability**, not from coverage. A
declared "any row may be read in any quarter" changes behaviour at write time
even at low sampling rates.

**Maps to:** the honest framing for a low-rate option. If we sample 10%, the claim
is "a 10% chance per quarter", NOT "we review B/C rows" — and the first is a real
statement while the second is the kind of thing this platform's claim documents
keep having to correct.

### 2.5 Risk-ranked ordering — already in this repo

`docs/fmea/` and `tools/fmea_draft.py` already produce per-file risk drafts, and
`tools/tiering_recheck.py` already ranks B/C rows by app using
independent-review defect density: **UNREVIEWED IN A SURPRISING APP, 95 rows
grouped by app worst-first.** Whatever option is chosen, that ranking exists and
should set the order. No new prioritisation machinery is needed.

---

## 3. The options, with costs from §1's measured throughput

Current load is ~13 obligations/day. Each option's cost is expressed against it.

### Option A — widen the gate's trigger to any tier
- **Reaches:** 33 of 124 in 14 days; 91 never.
- **Cost:** ~+2.4/day, +18%.
- **Cannot do:** close the gap. Named first because it is the intuitive answer
  and the numbers say it is a partial one. **Not sufficient alone.**
- **Still worth doing?** Arguably yes, as the cheap half of a pair — it catches a
  B row at the moment somebody is already in the file, which is the cheapest
  possible time to read it.

### Option B — quarterly rotation over all 124 B/C rows (§2.2, §2.3)
- **Reaches:** all 124, within one quarter, by construction.
- **Cost:** 124 rows / ~90 days ≈ **1.4 reviews/day, ~+11%.** Cheaper than
  Option A and complete, because it is not waiting for anything.
- **Cannot do:** react quickly. A row promoted to A mid-quarter waits.
- **Requires:** a scheduler and a durable "last read" date per row. The register
  has no such field today (§5).

### Option C — risk-ranked sample with switching rules (§2.1, §2.4, §2.5)
- **Reaches:** a stated percentage per quarter, ordered by the existing
  surprising-app ranking; tightens on a finding.
- **Cost:** whatever rate is chosen — at 25%/quarter, ~0.35/day.
- **Cannot do:** promise coverage. Must be stated as a probability (§2.4) or it
  becomes the same overstatement pattern corrected in the SAIRNlaw claim today.
- **Best when:** the honest position is that full coverage is not affordable.

### Option D — do nothing, and say so in the tool
- Already half-done: `tiering_recheck.py` prints the blind spot as its headline
  and `--candidates` exits 2 COULD NOT TELL rather than 0 when it has nothing to
  evaluate, so the gap cannot be misread as an all-clear.
- **Cannot do:** find an under-tiered row. **This is the current state, and it is
  a defensible one** — the cost of B/C being wrong is by definition lower than A
  being wrong. It should be chosen deliberately rather than by default.

**Recommendation: B, with A as the cheap companion, and C as the fallback if B's
1.4/day proves unaffordable in practice.** B is the only option that closes blind
spot (2), it is *cheaper* than the intuitive Option A, and its cost is a
calendar-driven trickle rather than a spike. A is worth adding because reading a
row while somebody is already in the file is the cheapest review there is. C only
becomes right if B is tried and the load is real.

---

## 4. What any of these must NOT do

- **Must not re-tier automatically.** Cross-domain disciplines item 11: a fixer
  may PROPOSE and may never apply. `tiering_recheck.py` already cannot write
  `docs/CRITICALITY-TIERS.md` and an arm asserts it by bytes and mtime. A
  promotion is not even a cell edit — `SC_TIER_A_SOFT_DELETE_ONLY` and the write
  gates DERIVE from the Tier A list, so an A withdraws a resource's `delete` verb
  and moves its client remove path.
- **Must not report a sampled rate as coverage.** §2.4.
- **Must not let the author review their own row.** `tier_a_review_gate.py`
  already refuses a record whose reviewer is its own author; any extension
  inherits that or it is not independent.
- **Must not fold "not yet read" into "read and fine".** A third state, same as
  UNEXAMINED in `tiering_recheck.py`.

---

## 5. The one structural prerequisite, whichever option is chosen

**`docs/tier-a-reviews.json` records reviews of CHANGES, not reads of ROWS.** Its
records carry `opened_at`, `opened_at_sha`, `files`, `resources`, `what`,
`verdict` — an obligation raised by a diff. Nothing in it answers **"when was
this row last read, irrespective of whether it changed?"**

Options B and C both need that field, and it is a different thing from what
exists: a per-row `last_read_at` with the reviewer and the verdict, decoupled
from any commit. Option A does not need it, which is part of why A is tempting
and insufficient.

**This is the real build in any of these**, and it is a schema decision on an
append-only shared register that four clones merge by union-by-identity. It is
not a side effect of adding a trigger, and it is the first thing to design.

---

## 6. The decision this needs, which is not mine

Three questions, in order:

1. **Is Option D acceptable?** If B/C rows being unreviewed is an accepted cost,
   this document closes and the tool's headline is the whole answer.
2. **If not, is 1.4 reviews/day (Option B) affordable on top of 13?** That is the
   only real cost question. If yes, B. If no, C at a stated rate.
3. **Whichever is chosen, who owns the per-row `last_read_at` schema (§5)?** It
   touches a register four sessions write to.

---

## 7. Re-derive every figure; do not quote them from here

```
python tools/tiering_recheck.py                 # the A vs B/C review coverage
python -c "import json,io; d=json.load(io.open('docs/tier-a-reviews.json',encoding='utf-8')); print(len(d['records']),'records')"
```

The 14-day change rate — the number that decides Option A — is measured by
diffing CODE ONLY. **`docs/` must be excluded**: `docs/CRITICALITY-TIERS.md`
names every tiered row, so any commit touching the register makes all 390 rows
look changed. My first run of this measurement reported 124 of 124 B/C rows
touched, i.e. 100%, which would have made Option A look complete. The exclusion is
the whole measurement:

```
python - <<'PY'
import io, re, subprocess
src = io.open('docs/CRITICALITY-TIERS.md', encoding='utf-8').read()
a, bc = [], []
for line in src.split('\n'):
    m = re.match(r'^\| `([a-z0-9_]+)` \| \*\*([ABC])\*\* \| \*\*([ABC])\*\* \|', line)
    if m: (a if m.group(2) == 'A' else bc).append(m.group(1))
diff = subprocess.run(['git','log','--since=14 days ago','-p','--unified=0','--',
                       'api/','*.html','sql/'], capture_output=True, text=True,
                      encoding='utf-8', errors='replace').stdout
added = '\n'.join(l for l in diff.split('\n')
                  if (l.startswith('+') or l.startswith('-'))
                  and not l.startswith(('+++','---')))
for name, rows in (('Tier A', a), ('Tier B/C', bc)):
    hit = [r for r in rows if re.search(r'\b'+re.escape(r)+r'\b', added)]
    print('%-9s %3d of %3d changed in 14d (%.0f%%)'
          % (name, len(hit), len(rows), 100*len(hit)/len(rows)))
PY
```

**These rates will drift and the conclusion depends on them.** If B/C code ever
starts changing as often as A does, Option A stops being a 27% answer and this
document needs re-running rather than re-reading.
