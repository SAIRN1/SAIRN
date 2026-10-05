# Routed to cc — two items that can only land in files cc holds

**2026-10-05 (Cody). CONFLICT DECLARED PER PR §4.3.** Both items below belong in
files under cc's **live** claim as of this writing:

| file | cc's claim | what I owe it |
|---|---|---|
| `docs/SAIRN-OPEN-WORK-INDEX.md` | `cc` — sb_ap seq 507/508, pre-commit grep-vs-git fail-open, row 82 re-derive, `exit_status_attributable` false positives | **ITEM 1** — one new row, authored below, paste-ready |
| `tools/exit_status_attributable.py` | same claim, and cc is **mid-fix on that exact file** | **ITEM 7b** — a coverage finding, below |

**Neither file is in my file set and I did not edit either.** The row is
delivered whole rather than described, because PR §2.1's named defect is a row
edited by splitting on `|` and the cheapest way to avoid it is to hand over the
finished line.

---

## ITEM 1 — the row for `metamorphic_check.py`

**PASTE THE THIRD LINE ONLY.** The header and separator are reproduced so the
block is a well-formed table that `md_table_check.py` can read — a bare row with
no header is an `ORPHAN` to that tool and it is right to say so. Seven cells, no
raw pipe, no raw em-dash, entity-escaped the way the surrounding rows are.

```
| App | Item | Status | Owner | Blocked by | Next action | Sz |
|---|---|---|---|---|---|---|
| **Tooling** | **&#128993; `metamorphic_check.py` EXITS 1 on a rewording finding that appears in NO index row &mdash; the tool is cody&rsquo;s and so is the gap** <!-- QUEUE16-ITEM1-CODY-2026-10-05 --> | **MEASURED 2026-10-05 (cody) at HEAD, and the tool is otherwise green: the file-transform family is CLEAN at 0 violated of 90 comparisons, `blind_lock()` is LOCKED at 24 fixture comparisons, and all SIX rules `dead_rule_sweep` called DEAD on 2026-09-29 are now exercised (`--tool metamorphic_check.py`: 6 of 6, 0 dead, CLEAN). The ONE finding is in the REWORDING family: `fmea/alf_facility_role_gate_live_probe.py`, relation `case`, 504 applicable and 1 violated. The verdict MOVED &mdash; `('_d_falsy_from_except', '_d_fixed_window')` gained `_d_checker_without_probe`. PRE-EXISTING, not introduced by the fixture work: `b70b040f` names it as &ldquo;its one existing finding&rdquo;** | cody (the tool); row routed to cc | **The ROW was blocked, not the diagnosis.** `docs/SAIRN-OPEN-WORK-INDEX.md` was under cc&rsquo;s live claim on 2026-10-05, so this line was authored and handed over in `docs/2026-10-05-cody-routed-to-cc.md` rather than inserted | **Reproduce in seconds, not 200: `python tools/metamorphic_check.py --prose` isolates the rewording family and exits 1.** Then decide between the TWO hypotheses, which are opposite findings and must not be merged: **(a)** the `case` rewording is NOT meaning-preserving on this subject, in which case the RELATION is over-broad and the fix is to narrow or declare it, or **(b)** `_d_checker_without_probe` is case-sensitive where it should not be, in which case the FMEA DETECTOR has a real defect and the relation caught it. **Nothing here has been diagnosed; (b) would make this a found defect rather than a tool limit** | S |
```

### What the row is careful NOT to say

- **It does not call the finding benign.** It has not been diagnosed. Only
  confirmed as pre-existing, reproducible, and unlogged.
- **It does not call the tool broken.** Six of its rules went from dead to
  exercised this batch and the file-transform half is clean at 0 of 90.
- **It does not pick between (a) and (b).** Hypothesis (b) means the relation
  found a real FMEA defect, which is the opposite verdict from (a), and the
  distinction is the whole value of the row.

---

## ITEM 7b — `exit_status_attributable.py` does not flag the trailing-echo shape

**Read-only analysis. I did not edit the file.** cc's claim says she is working
on that tool's **false positives**; this is the opposite direction — a **false
negative** — so it is worth having in front of her while the file is open.

### What the tool catches today

It fires on a command whose exit status will be taken from a **text filter or a
later element** of a pipeline or `&&`/`;` chain, and it is right every time it
fired in my session — it warned on nearly every command I ran, including the
ones where I had already redirected correctly.

### The shape it does NOT catch

```
python tools/metamorphic_check.py > /tmp/out 2>&1
echo "EXIT=$?"
```

This is the **prescribed** pattern — the tool's own message recommends it:
*"measure it alone: `<tool> > /tmp/out 2>&1` then read `$?` on its own line."*
And on a **foreground** run it is completely correct: the `EXIT=` line is
printed where I can read it.

**It stops being correct the moment the run is BACKGROUNDED.** The harness then
reports the exit status of the **compound command**, whose last element is the
`echo` — so it reports **0** no matter what the tool did. Measured 2026-10-05:

| run | harness notification | real code, from the captured `EXIT=` line |
|---|---|---|
| `metamorphic_check.py` | completed (exit code 0) | **1** |
| `dead_rule_sweep.py` | completed (exit code 0) | **2** |

**Two not-green tools were one step from entering a standing document as
green.** The `EXIT=` line was in the captured stdout the whole time; what was
wrong was the number that looked authoritative.

### Why this is a gap in the CHECKER and not only in my habit

`exit_status_attributable` reasons about the command **text**, which is the right
place for it. The backgrounding decision is made by the **harness**, after the
text is written, so the same text is safe in one context and misleading in the
other. **That is a second, unguarded source of the exact number the tool exists
to protect.**

### The finding, stated as the smallest change that would have caught it

The tool already parses the command into elements to find the status-bearing
one. **When the LAST element is an `echo` (or any command) whose argument
contains `$?`, the exit status reported by any caller of the whole command is
that element's — not the tool's.** That is flaggable from the text alone, with a
message that does not contradict the advice the tool already gives:

> the `EXIT=$?` line is correct to PRINT, and is NOT the status a caller sees.
> If this run is backgrounded or wrapped, the caller reads the `echo`'s 0. Read
> the `EXIT=` value out of the captured output, or use
> `python tools/capture_exit.py -- <tool> ...`.

**`tools/capture_exit.py` exists as of this batch** and writes the real status to
a file rather than relying on a trailing `echo` — so the message has somewhere
to point. It is registered in `docs/TOOLING-INVENTORY.md`.

**This is a PROPOSAL, not a patch.** Per the eleventh standing convention a
detector may propose a repair and may not apply it, and the file is cc's besides.
If the shape is judged too noisy to flag unconditionally, the narrower version is
to flag it only when the trailing `echo` is the final element of a
**multi-line** command, which is the only form that gets backgrounded.
