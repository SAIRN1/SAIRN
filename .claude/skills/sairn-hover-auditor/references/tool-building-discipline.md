# This role's own tool-building discipline

Written H1 batch Q item 9, after building three new tools in the same
sitting (`hover_completeness_probe.py`, `hover_threshold_cluster.py`,
`hover_hidden_state.py`) and finding a real, hand-verified false positive
in every single one of them on its own first real run. Three for three is
not a coincidence worth ignoring — it is the actual base rate for a
freshly-written text/regex-shaped scanner pointed at real source for the
first time, and this file exists so the next tool this role builds starts
from that measured rate rather than from optimism.

## The rule: every new checking tool is sabotage-tested two ways, not one

A detector that is only tested against a bad state planted directly into
its input (a hand-written fixture string, a crafted JSON blob) proves it
can recognise that SHAPE of badness. It does not prove the detector still
catches the same badness when it arrives the way a real defect actually
arrives — mid-transition, with everything else in flight around it. Both
are required before a new tool's first real run is trusted:

1. **Planted directly.** The bad state is constructed by hand and handed
   straight to the function under test — `hover_completeness_probe.py`'s
   `_selftest()` writing a fixture `api/_resources/fakeapp.js` with a known
   gap resource already in place. Fast, cheap, and exactly what every
   selftest in this toolset already does.
2. **Reached via the real transition.** The bad state is produced by the
   same KIND of event that creates it for real — right after a rebase
   completes, a claim releases, a retry fires, a resource is added to a
   live file that already had an older register entry. `hover_completeness_probe.py`'s
   second fixture appends a new resource to an already-written file and
   reruns, rather than constructing the end state directly — the same
   distinction `sabotage_benchmark/` already draws for this role's
   detection tools, now written down as a rule for every NEW tool rather
   than left as something only the benchmark remembers.

A tool that passes (1) but has never been run through (2) has only proven
it can read a fixture, not that it survives contact with how the bug
actually gets created. Where real continuous transitions are impractical
to simulate in a selftest (most of this role's tools), the SECOND check is:
hand-verify the tool's first real run against real source, line by line,
before trusting any of its output — which is what caught all three bugs
below, none of which any fixture had been written to catch because nobody
knew yet they existed.

## Base rate, measured this batch: 3 real tools, 3 real first-run bugs

- `hover_completeness_probe.py`: matched a quoted string inside a `//`
  comment (`sdnData('write','law_deadlines')`) as if it were a real
  resource literal. A text-shaped scanner cannot distinguish code from a
  comment describing code unless it strips comments first.
- `hover_threshold_cluster.py`: matched its OWN selftest fixture text
  (a string the test writes to a temp file) as a real, already-tripped
  threshold in its own source. A text-shaped scanner run against "every
  .py file in the repo" will find itself, and its own test fixtures read
  exactly like real code.
- `hover_hidden_state.py`: 'status' alone matched on 110/110 of every
  resource it could locate a handler for — a near-universal lifecycle
  field, not a signal. The tool was technically correct (every one of
  those resources really does branch on a field called `status`) and
  useless until the near-100%-hit-rate was noticed and filtered.

None of these three bugs share a root cause. They share only that they
were found by reading the tool's own real first-run output rather than
trusting a clean selftest, which is the actual, adoptable lesson: **a new
tool's first run against real data is itself a test of the tool, not yet
a report about the subject.**

## Operational near-miss this same batch, folded in because it is the same class of lesson

Calling `hover_log.py --add` without first setting `HOVER_LOG_PATH_OVERRIDE`
silently started a SECOND, disconnected genesis chain at
`.claude/skills/sairn-hover-auditor/tools/hover-audit-log.jsonl` (seq=1)
instead of appending to the real 1113-entry chain this role's identity
lives in. Caught immediately (`git status` showed the stray file
untracked), deleted before anything else was appended to it, and the real
append redone with the override set explicitly. **Every future `--add` call
this role makes sets `HOVER_LOG_PATH_OVERRIDE` explicitly — never relies on
the tool's own default.** This is not a new checking tool's bug; it is the
same underlying lesson (an untested default silently does the wrong thing
the first time it is actually exercised) applied to this role's own
infrastructure rather than to a subject it audits.

## Resuming work: the chain log is ground truth, not the claim file

Added H1 batch R item 8. Batch Q opened on an instruction framed as
"you compacted mid-batch, resume" -- and `.claude/claims/hover.json`
showed NOTHING active since 2026-09-30, over a week stale, which read on
its own like there was nothing to resume. The chain log said otherwise:
seq1109-1113 showed five real, timestamped items from the same batch
already landed. **The claim file and the chain log are two different
persistence mechanisms answering two different questions** -- the claim
file is a cross-session file-lock (`sairn_claim.py`'s whole purpose is
telling OTHER sessions not to touch the same files right now), and it is
entirely normal for it to go unwritten or expire while this role's own
real work continues, because nothing about resuming mid-batch requires a
file-lock to still be held. The chain log is this role's own append-only
record of what it actually did, and it is the one that answers "is there
unfinished work to resume." **On every future resume, check the chain log
first and do not treat a stale or empty claim file as evidence against
resuming** -- it answers a different question and was never built to
answer this one.

A related, harder-edged version of the same "verify the artifact, not just
the log entry describing it" discipline surfaced one batch later (batch R
item 6): eleven chain-log entries across two days cited running
`hover_cross_resource_gate_check.py` as this role's own committed tool,
and the file has never existed in this repository's history at all --
caught only because this batch tried to actually re-run it rather than
trusting the citation. The chain log is ground truth about WHAT THIS ROLE
INTENDED AND BELIEVED it did; it is not, by itself, proof that a cited
artifact still exists to be re-verified. Trust it over the claim file for
"is there unfinished work" -- and still check that a cited tool is
actually present before building a re-sweep on top of it.

## "Missing" means "not found where I looked," never more than that

Added H1 batch S item 14, after batch R's own HIGH-severity finding that
`hover_cross_resource_gate_check.py` was "never committed to this
repository, on any branch, ever" turned out to be WRONG -- the file had
lived in this role's own external working directory since the day it was
built, and batch R's search checked the git-tracked repo and `git log
--all` but never looked in the one place this role's own operational
tooling actually lives. **Before concluding an artifact does not exist,
enumerate every place it plausibly would be — including this role's own
external directory, which is easy to forget precisely because it is
outside the repository the rest of a search naturally centers on — and
say which places were checked, not just the verdict.** "Could not find it
in git" and "does not exist" are different claims; batch R's finding
quietly upgraded the first into the second.

## A register's load-bearing prose is not always in the column with that job

`hover_ai_redaction_field_check.py`'s own first real run flagged
`mech_docs` for not naming the field it redacts -- except it does, in
exhaustive detail, just in the "worst consequence if read by the wrong
person" column rather than "Evidence," which is the column every other
tool in this role's toolset checks. **A register's own authors do not
reliably put the sentence that matters in the same cell every row** --
check the union of a row's free-text columns before concluding a row says
nothing, not whichever one column convention assumes carries the answer.

## An external refactor can silently break a dependent script's API, and nothing finds this by routine

`tools/hover_separation_ci.py` called `hover_separation_audit.AUDITOR_SCOPE`
for an unknown number of days after that attribute was deliberately
removed in favour of a session-parameterized class -- every single
invocation crashed with an `AttributeError`, meaning the server-side
separation check (the one that catches a missing or bypassed local hook)
simply never ran, silently, for as long as nobody happened to invoke the
CI script directly. Nothing in this role's standing sweeps would have
caught it on its own -- it surfaced only because a direct instruction
named the file and asked this role to run it. **Two files with a real
import/call dependency between them are a pair that can drift the moment
either one changes alone**, the same shape `hover_auditor_scope_gate.py`
and `hover_separation_audit.py` already guard against for THEIR OWN
mutual agreement (per-session, across several names, in
`tests/run_hover_separation_probe.py`) -- but that guard only covers the
two files that explicitly maintain it against each other. A THIRD file
consuming either one's API has no such guard unless someone adds one, and
this role does not currently have a standing sweep that asks "does
anything import a name this file used to export."

## Prevention, not just detection: commit before you cite, checked at write time

`hover_citation_guard.py` (batch S item 5) is the standing answer to the
"missing tool" lesson above: before any chain-log entry is written, every
tool/script/path it names must resolve in git on `origin/main`, or the
append is refused. Built narrow on purpose -- a blanket scan of free
prose would refuse this role's own legitimate sabotage-fixture narration
(inventing a fictional tool name to test ANOTHER tool's parser is not a
false citation), so only `--ref` (structured, always checked) and
invocation-shaped `--summary` prose (a path within 60 chars of an EXIT
code or `--selftest`) are checked. **A write-time guard only prevents the
NEXT mistake of this shape; it does not retroactively clean history** --
its own `--recheck-log` mode found 67 citations across 57 pre-existing
entries that do not resolve today, left as a disclosed backlog rather
than edited (the log is append-only) or implied clean.

## The log convention this item also adds: a reversal gets its own entry

A later read that **CONTRADICTS** an earlier clean verdict from this role
is never folded into a routine re-check entry. It gets its own entry, with
`contradicts` pointing at the earlier seq, and the summary states plainly
that this role's own prior verdict was wrong and why — not softened into
"re-confirmed with an update" language. A clean verdict that quietly
becomes not-clean, recorded in a way that reads the same as any other
routine recheck, is a second silent failure riding on top of the one
already being audited: the register would show two checks and no visible
sign that they disagree. `hover_log.py`'s own `contradicts` field already
exists for exactly this; the convention being added here is that it is
**mandatory**, not optional, whenever a reversal of this role's own prior
finding is the thing being logged, and that the entry's salience (how it
reads in `--tail` and in a handoff) is deliberately raised rather than
left to blend in with routine entries.
