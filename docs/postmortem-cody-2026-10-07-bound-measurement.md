# Blameless postmortem — I set a timeout from the size of the wrong file

**2026-10-07 (Cody).** One incident. **Blameless means the finding is about the
system, not the session**, so this ends in a system-level fix inside an existing
check rather than in a resolution to be more careful.

---

## WHAT HAPPENED

`tools/metamorphic_check.py` carried `PER_RUN_TIMEOUT = 120`, a number nobody
had measured. On 2026-10-06 I replaced it with **40**, derived honestly:

```
timed the six CHECKERS against the biggest real target, under load
  literal_drift_check.py   stonedesk.html (2.76MB)   18.24s   <- "the worst"
  nav_panel_check.py       stonedesk.html            14.35s
  the other four                                    <3.2s
  -> 2 x 18.24 = 36.5, rounded up to 40
```

The bound then **fired on three runs out of three**, every one EXIT 2, with the
same two timeouts each time:

```
run 1  355s  EXIT 2     duplicate_global_check.py  stonedesk.html, relation
run 2  506s  EXIT 2       `duplicate`: timed out after 40s
run 3  476s  EXIT 2     literal_drift_check.py     same relation, same
```

## WHY — AND IT IS NOT A TUNING ERROR

**A metamorphic check never runs a checker on the file.** It runs it on the file
**and on each TRANSFORM of the file**, and `t_duplicate` returns
`lf + '\n' + lf`. The artifact the bound actually has to cover is **5.51MB**,
and I measured the **2.76MB** one.

Re-measured on the duplicated input, same machine:

| checker | 5.51MB (the real subject) | 2.76MB (what I timed) |
|---|---|---|
| `duplicate_global_check.py` | **71.54s** | 0.82s |
| `literal_drift_check.py` | 43.64s | 18.24s |
| `nav_panel_check.py` | 19.89s | 14.35s |
| `div_balance_check.py` | 8.33s | 0.30s |
| `key_collision_check.py` | 7.52s | 3.18s |
| `panel_nesting_check.py` | 0.77s | 0.60s |

`duplicate_global_check` goes **0.82s → 71.54s on a 2× input — 87×**,
superlinear in duplicate ids. **The figure I measured could not have predicted
the figure the bound had to cover, in principle and not just in fact.**

Corrected bound: **145s** (2 × 71.54 = 143.1). Confirming run: **EXIT 0, 352s,
zero timeouts**.

**IT IS HIGHER THAN THE 120 I REPLACED.** My tightening broke a working tool.
And the old 120 was not a 2× bound either — it was simply above 71.54 by luck,
so the file had been one `stonedesk.html` growth spurt away from this all along.

## WHY THE EXISTING CONTROLS DID NOT FIRE

- **The 2× rule itself is right and I followed it.** It says multiply a
  measurement; it does not say which artifact to measure, because until now
  nobody had been bitten by measuring the wrong one.
- **The tool's output never showed the subject.** Three runs printed the
  relation names, the comparison counts and the timeout message — and **not one
  byte about how large the thing being bounded was.** The only size available to
  anybody setting the bound was the one on disk, which is the wrong one.
- **The timeout message named the bound but not the subject.**
  *"timed out after 40s"* tells you the number you already know and withholds
  the number you need.
- **No arm covers it and none plausibly could.** A fixture-sized metamorphic run
  finishes in milliseconds under any bound; the defect only exists at the real
  file's scale, which is the ninth discipline exactly — the costly artifact
  earns the exhaustive verification, and this one got the cheap one.

## CONTRIBUTING CONDITIONS, NOT CAUSES

- **The transform is invisible at the call site.** `run(tool_path, target)` took
  a path. Nothing in the signature, the name or the docstring said that `target`
  is usually a derived artifact several times the size of the file it came from.
- **`duplicate` is the only superlinear relation**, so five of six relations
  would have made the 40s bound look fine. The one that mattered was a minority
  case.
- **I had the right instinct and applied it to the wrong noun.** The commit that
  set 40 says *"measured on this machine while a full 249-suite run was loading
  it -- deliberately the loaded case, because a bound calibrated on an idle box
  is the one that fires under load."* That reasoning is sound. It is about the
  machine, and the variable that mattered was the input.

## THE SYSTEM-LEVEL FIX — INSIDE `tools/metamorphic_check.py`, NOT A NEW TOOL

**The fix is not a bigger number. A number is what went wrong.** What was
missing is that nothing ever reported the size of the artifact the bound applies
to. It does now, in the tool being tuned, on every run:

```python
def run(tool_path, target, relation=None):
    note_subject(relation, target)        # records the largest artifact seen
```

```
  bound subject : PER_RUN_TIMEOUT=145s applies to a LARGEST artifact of
                  5.25MB, produced by relation 'duplicate' -- NOT to the
                  stonedesk.html on disk. Measure THIS when changing the bound.
```

and the timeout message now carries the subject too:

```
timed out after 145s on a 5.25MB artifact from relation 'duplicate'
  -- the bound applies to THIS, not to the file on disk
```

**Printed on CLEAN runs as well as timeouts, and that is the whole point.** The
person who edits `PER_RUN_TIMEOUT` is almost always reading a successful run —
which is exactly when the misleading number is on screen and the correct one is
not.

### Why a report and not a refusal

A refusal would need a ratio threshold, which is a second guessed number sitting
on top of the first — and **a bound that refuses its own subject is how a
checker gets switched off**, which this repo has recorded more than once. The
cheapest thing that would have prevented this incident is *the right number
being visible at the moment of the decision*, and that is what was built.

### What it does not do

- **It does not stop anyone setting a bad bound.** It removes the excuse, not
  the possibility.
- **It does not generalise.** Every other tool in `tools/` with a hardcoded
  timeout still reports nothing about its subject. A sweep for that shape is
  **not done and is not claimed** — it is named in the routed doc as open.

## THE RULE, ROUTED AND NOT SELF-PROMOTED

> **A bound measured against the tool's INPUT is not a bound on the tool's
> SUBJECT. Measure what the bounded call actually receives.**

**Next free convention number is 20** — counted, not quoted: `grep -c "^## [0-9]*\."
docs/2026-09-13-cross-domain-disciplines.md` → **19** at HEAD `fa560504`.

**NOT WRITTEN BY ME.** `docs/METHODOLOGY.md` and
`docs/2026-09-13-cross-domain-disciplines.md` are both in **fourth's** live
batch-12 declared file set, re-checked at this HEAD. **Promoting a convention
out of my own defect is the detector-blessing-its-own-fix shape that convention
11 refuses**, so it is routed with its evidence in
`docs/2026-10-07-cody-routed.md` §3 and adoption is somebody else's call.

**And a lesson from the last routing, applied here:** METHODOLOGY.md's own queue
records two of my previous routings as **NOT RECEIVED**, because they named a
document that was not on `main`. The full rule text is therefore **inline in the
routed doc**, which is pushed, rather than referenced.

## WHAT THIS POSTMORTEM DOES NOT CLAIM

- **That 145s is correct beyond this machine and this tree.** One run at 145s
  returned EXIT 0 with zero timeouts. One run is one run, and the worst case is
  superlinear in a file that is still growing — so this number has a shorter
  life than most and the constant's own comment says so.
- **That the subject line would have caught it.** It would have shown me
  5.51MB while I was looking at 2.76MB. **Whether I would have noticed is not
  something a postmortem gets to assert about its own author.** What is true is
  that the number was not available and now is.
