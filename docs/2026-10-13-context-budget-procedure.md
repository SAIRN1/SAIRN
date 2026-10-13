# The context-budget procedure for a batch session

**Written 2026-10-13 (hank b7) because b6 ended at 98% context.** Not a theory
of context. A procedure, followed by the batch that wrote it, with the numbers
it was measured against.

**This is the HOW-MUCH-TO-READ half. `sairn-context-budget` is the
HOW-TO-NOT-LIE half** — a truncated read is indistinguishable from a complete
one, and a count quoted from a truncated read becomes a confident wrong claim.
Read that skill before quoting any figure out of anything large. This file is
only about not running out of room in the first place, which is a different
failure: it does not produce a wrong answer, it produces a session that cannot
finish and hands off mid-edit.

---

## Why 98% is a defect and not just a number

At 98% the handoff and the report — the two artefacts the next session actually
needs — are written in the smallest remaining space, last, under the most
pressure, about the most material. That is the wrong order for everything. The
batch brief for b7 makes it structural rather than advisory: **the handoff is
written BEFORE the report, at a point where nothing is half-finished.**

The failure is not "the session stopped". It is that the one thing nobody else
can reconstruct — what was in flight and why — is produced when there is least
room to produce it.

---

## The procedure

### 1. Read the two documents you were given. Not their neighbours.

A fresh session's first instinct is orientation: the primer, the process rules,
the handoff, the active-work files, the open-work index. **That instinct costs
more than the work.** Measured on this repo, 2026-10-08:
`SAIRN-ACTIVE-WORK-*.md` total 3.8 MB ≈ 1.03 M tokens, and
`docs/SAIRN-OPEN-WORK-INDEX.md` alone is 2.38 MB ≈ 640 k tokens. Either one
read whole exceeds or consumes the window.

So: read exactly what the brief names, then `grep` for anything else. In b7 the
brief named two files, and every other document was reached by `grep -n` plus a
window of twenty lines. **Nothing was read whole that was over ~40 KB.**

### 2. Size before you open.

One `wc -c` on everything you expect to need, in one call, before the first
`Read`. It costs one line of output and it decides your whole approach:

    wc -c sql/audit_checkpoint_schema.sql api/audit-checkpoint.js api/sf-auth.js …

Under ~40 KB: read it whole, once. Over: `grep -n` for the symbol, then read a
window. Over ~400 KB: never read it, and say so out loud — the number and the
command that produced it, so the next reader does not have to re-measure.

### 3. One read per file. Target the symbol, not the region.

`grep -n "SCHEMA_PERMITTED\|ALL_AUDIT_TABLES"` then one `Read` with `offset`
and `limit` beats three exploratory reads of the same file. Cap reads at ~150
lines. A second read of the same region is a sign the first one was aimed badly,
not that the file is hard.

**A line range that stops inside a structure gives a wrong answer with no
warning** — on 2026-10-07 a 42-line window over a Python tuple read four entries
of eight and concluded a required entry was missing. Widen until you can see the
structure close, or stop reading text and measure the thing: `node -e`,
`ast.literal_eval`, `len()`.

### 4. Measure with a program instead of reading.

The cheapest read is the one that returns a number. Counting the `sf_` keys in a
1,200-line gate table cost twelve lines of output via a parser; reading the
table would have cost thousands and would have been less reliable, because the
block carries more comment than code. In b7 this was the difference between
discovering "27 of 36" and believing a comment that said 36.

**And it is not only cheaper, it is a different kind of evidence.** A comment is
a claim. `node -e 'console.log(Object.keys(X).length)'` is a measurement.

### 5. Push the noisy work to a subagent, and ask for a verdict.

A subagent spends its own window and returns only what you asked for. Dispatch
when the answer requires sweeping a file you must not pay for — in b7, nine
resources' read and write sites inside a very large single-file app. That audit
cost 82 k tokens of the subagent's context and about 2 k of mine.

Three rules, each paid for:

* **Ask for a verdict line, not a report.** "GATING THESE NINE IS CLIENT-SAFE"
  or "NOT SAFE: <what> at <line> because <why>".
* **Require citations and forbid guessing.** `file:line` for every claim, and
  COULD NOT TELL as an allowed answer. A subagent that cannot say "I could not
  tell" will invent.
* **Do not take it at face value.** The b7 subagent reported that none of the
  nine was in `SD_GATE_APP`; that was re-measured locally with a parser before
  the edit was written. It was right — and the re-measurement cost six lines.

**Check the agent actually has the tools.** A `suite-driver` dispatch in b7
returned eight CANNOT RUNs because its allowlist has no Bash. It reported that
honestly rather than inventing exit codes, which is the correct behaviour and
still a wasted round trip. Match the agent type to the verbs the task needs.

### 6. Test output goes to a file. Read the tail.

    node api/x.test.js > "$SCRATCH/x.log" 2>&1; echo "exit=$?"; tail -2 "$SCRATCH/x.log"

Then `grep -E "^  FAIL" -A 3` only if it failed. A suite that prints 400 passing
arm names costs more to read than the change it is checking. **The exit code
comes from the program's own output**, never from "it looked fine".

### 7. Write the handoff when nothing is half-finished — not when the room runs out.

The trigger is a STATE, not a percentage: every code change committed, every
suite run with its exit code recorded, no file mid-edit. That state occurs
naturally at the end of each numbered item. Write the handoff at the LAST such
point you can reach, and treat "I have one item left and plenty of room" as the
moment to write it rather than the moment to postpone it.

**Then write the report.** The report is derived from the handoff plus the log
files; the handoff is derived from the repository. That order means the
expensive-to-reconstruct artefact is produced first, and the one that can be
rebuilt from committed state is produced last.

### 8. Re-derive every number right before writing it.

Counts drift toward the flattering one when remembered. Pass counts, arm counts,
pair counts, sha — all of them come from the tool that records them, re-run at
write time. This is cheap precisely because of step 6: the log files are still
on disk, and `tail -2` is the whole cost.

---

## What this is not

**Not a licence to skip the startup checklist.** The claim check, the status
registry and the handoff read still happen — they are small by design, and the
registry is one command. What is skipped is the UNFOCUSED read: four
active-work files, an open-work index, a primer you already have in context.

**Not a reason to leave work undone.** If an item genuinely needs a large read,
take it, say what it cost, and hand off earlier. Running out of room with the
work finished is a scheduling problem. Running out of room with an item silently
dropped is a reporting failure, and no budget justifies it.

---

## Measured on the batch that wrote it

b7 ran six items — one idempotent SQL block plus code and four new test arms, a
red suite split into four arms, three stale SQL CHECK constraints, a demo
credential with a double round trip, nine resources gated with two ablations,
and this file. Every file over 40 KB was reached by `grep` and a window; one
subagent carried the only large-file sweep; every suite's output went to a log
and only its tail was read. The context figure for b7 is on the last line of
`SAIRN-digest-hank-b7.txt`, measured rather than estimated, beside the proxy
used to measure it.
