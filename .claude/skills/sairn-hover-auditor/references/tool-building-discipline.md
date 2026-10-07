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
