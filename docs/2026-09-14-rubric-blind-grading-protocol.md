# Blind-grading protocol for the defect severity rubric

**2026-09-14 (Cody).** Read this file. **Do not open the rubric yet.**

This exists because the instruction it carries has now destroyed its own
precondition **three times running**, and the two previous fixes both addressed
the wrong cause.

## Why this is a separate file

The blind pass requires grading records **before** reading the rubric. That
instruction originally sat at the bottom of the rubric, under *"Why there is no
back-test"* — after everything it protects. Fourth read the file top to bottom
to find out what ratifying involved, reached the instruction too late, and
disqualified themselves.

The fix applied then was **position**: move it into a STOP box at the top. That
protects a reader who scrolls.

**It does not protect a reader whose smallest action is "open the file".** I am
that reader. I opened the rubric with a single call that returned all 228
lines, and the STOP box arrived in the same payload as the rubric it guards. By
the time I could act on it, it was already void. Position cannot fix this,
because there is no position inside a file that is read atomically.

**So the guard has to be a DIFFERENT FILE.** That is the only arrangement where
"read this first" is enforceable by the reader's own mechanics rather than by
their self-restraint. A grader can read this file completely and still be
eligible.

## The protocol

1. **Do not open** `docs/2026-09-13-defect-severity-rubric-UNRATIFIED.md` (or
   its ratified successor) until step 4.
2. Generate the holdout packet. It prints summaries with **severity, layer and
   app stripped** — layer and app are stripped too, because "tooling" beside a
   shared-path summary narrows the grid on its own. Run from the repo root:

   ```bash
   python - <<'PY'
   import json, io, subprocess
   RC = subprocess.check_output(['git', 'log', '--diff-filter=A', '-1', '--format=%H', '--',
       'docs/2026-09-13-defect-severity-rubric-UNRATIFIED.md']).decode().strip()
   pick = lambda d: d['records'] if isinstance(d, dict) and 'records' in d else d
   old = pick(json.loads(subprocess.check_output(
       ['git', 'show', '%s:docs/defect-density-register.json' % RC]).decode('utf-8')))
   new = pick(json.load(io.open('docs/defect-density-register.json', encoding='utf-8')))
   k = lambda x: (x.get('subject'), x.get('summary', '')[:60])
   seen = set(map(k, old))
   for i, x in enumerate([r for r in new if k(r) not in seen], 1):
       print('%2d. %s\n' % (i, x.get('summary')))
   PY
   ```

   **If it prints 0 rows, STOP** — the register only grows, so an empty result
   means the key stopped matching. That is a broken differ, and it reads
   exactly like "nothing new to grade".

3. **Grade every row from the summary alone, on your own judgement, and WRITE
   THE GRADES TO A FILE BEFORE CONTINUING.** Four levels: `critical`, `high`,
   `moderate`, `low`. Committing them to disk first is what makes the pass
   auditable — a grade held in your head is one that can drift toward the
   rubric as you read it.

4. Now read the rubric. Grade the same rows again, applying it.

5. Report **two numbers, never one** (disciplines §2):
   - **ACCURACY** — pass 2 against the recorded severities in the register.
   - **STABILITY** — pass 1 against pass 2, i.e. whether the rubric taught you
     anything or only agreed with what you already thought.

   If stability is low the rubric is not teachable, whatever accuracy says.

## And read this before trusting accuracy

**The reference standard disagrees with itself.** Measured 2026-09-14 on the
21-record holdout: two defect shapes carry more than one grade in the register
itself —

| Shape | n | Spread |
|---|---|---|
| a control/probe that silently stopped testing anything | 7 | 1 `low`, 4 `moderate`, 2 `high` |
| a report claiming coverage it did not have | 5 | 3 `high`, 2 `moderate` |

So a disagreement between your grade and the recorded one may be **the corpus
being inconsistent rather than you being wrong**, and an accuracy figure
computed against it is not a clean measure of the rubric. Name which
disagreements fall on a split shape before quoting the number — that is
convention 3 applied to the reference rather than to the sample.

## What is still owed

Nobody has produced a **stability** number. Mine is unobtainable: I destroyed
my own "before" pass by opening the rubric, which is the third occurrence of
exactly that. **CC has not read the rubric as far as I know and is the
remaining eligible grader.** The accuracy half is recorded in the rubric
itself; stability is the gap.
