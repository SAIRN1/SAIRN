# This role's own tool-building discipline (hover2)

Written batch O item 7, from this role's OWN real friction this session —
not copied from H1's `references/tool-building-discipline.md`, which covers
a different set of lessons (sabotage-testing a freshly-written detector two
ways). This file is about a different failure class: **the recording tool's
own guard rails, and the silent-copy-divergence shape, both found the hard
way by hover2 itself.**

## Rule 1: a logging tool's own input gates are not optional ceremony — read them before fighting them

`hover_log.py --append` refused four times this session before a `--type
finding` entry landed clean:

1. **Inline `--summary` is refused for `type=finding`.** The tool's own
   refusal message names why: a prior incident (seq 273) lost a word to
   shell command substitution before the tool ever saw the text, silently —
   a log entry got committed with content the author never actually wrote.
   `--summary-file` sidesteps the whole class of shell-quoting risk by
   never putting the content on a command line at all. **Applying lesson:**
   write the summary to a scratch file FIRST, every time, for `type=finding`
   — do not try inline `--summary` "just this once" because it is shorter.
2. **`type=finding` requires `--vector` in `T:[ABC]/EX:(L|M|H|NA)/SC:(C|S)`
   form.** Guessing a plausible-looking vector string and letting the regex
   reject it burns a turn; reading `VECTOR_RE` in the tool's own source once
   (`T:[ABC]/EX:(L|M|H|NA)/IM:(L|M|H)/SC:(C|S)`) answers it permanently. A
   self-bug (this role's own tooling, not a platform finding) still needs a
   vector — there is no "not applicable" value; pick the closest honest fit
   (e.g. `T:B/EX:NA/IM:L/SC:C` for a tooling-only, no-exploit defect) rather
   than inventing a new token the regex will reject.
3. **`type=finding` requires `--source <path>[:sha]` or an explicit
   `--source-exempt-reason`.** Named after a real incident (`leg_aftercare`
   — a finding logged against a row already fixed on `origin/main`, with
   nothing catching the staleness before it was committed to a hash-chained
   log). The fix is cheap: pass `--source <file> --repo <path>` and let the
   tool derive the live blob sha itself, or state plainly that the finding
   is about this role's own tooling and there is no platform file to cite.
   Skipping this to "save a step" is exactly the shortcut the gate exists to
   block.
4. **A repeated `target` on the very next entry is refused** unless
   `--same-target-reason` is given. Cheaper fix than justifying the repeat:
   give the next entry its own distinct, descriptive target slug — it also
   makes the log more useful to read later than two entries both filed
   under `self`.

**General form:** when a tool you rely on refuses your call, the refusal
text is usually citing a real past incident by name — read it before
treating the refusal as friction to route around. Three of these four gates
exist because of a documented, specific, earlier failure; none of them is
arbitrary.

## Rule 2: a tool that exists in two places drifts silently, and only a re-hash catches it before it matters

Found FIRST at seq697 (this role's own `hover2_timestamp.py`: the platform
repo's committed copy was stale because the log repo's separately-edited
copy had masked it all batch) and found AGAIN, independently, at batch O
item 6 — this time by a **deliberate re-hash sweep**, not an accident: 3 of
32 tool files that exist in both `tools-hover2/` (the git clone) and the log
repo's own directory had genuinely diverged, in BOTH directions (two files
where the clone was ahead, one where the log-repo copy carried a real,
already-decided edit the clone never received). **This is not a one-time
bug that got fixed once; it is a structural property of keeping two writable
copies of the same tool and editing whichever one happens to be open.**

**Applying lesson:** whenever this role is about to trust a tool's behavior
without having just run it moments ago, sha256 BOTH copies first if both
exist, rather than assuming "I fixed this already" from memory. A clean
`git diff` on one copy proves nothing about the other. The two-copy
arrangement itself is the risk — not fixing it here, because that is a
larger decision than one batch item, but naming it as a standing,
not-yet-eliminated hazard rather than a closed incident.

## Rule 3: fail-closed gates that compute a verdict from two sources must name BOTH sources when they disagree with memory

`tool_provenance_status.py`'s own refusal text ("fail-closed on the read,
PR §1.11: a ledger that is absent or unreadable is a COULD-NOT-READ, printed
by name") is the right shape — and it is why the ledger-path bug (batch O
item 6) was CAUGHT rather than silently reported as "every tool
unvalidated," which would have been read as true and was not. **Applying
lesson when building a new tool that reads from more than one source:**
design the "could not read source X" case to print the exact path it tried,
every time — a vague "no ledger found" is unfalsifiable by the next reader,
while a printed wrong path is falsifiable in one `ls` command, which is
exactly how item 6's bug was confirmed rather than merely suspected.

## Rule 4 (batch P, items 6/9/12) — "where do MY OWN files live" is the single most common first-run bug this role's tools have, and it keeps recurring because the fix was never made reusable

THREE SEPARATE TOOLS got this wrong on first contact with reality, in one
batch: `tool_provenance_status.py` derived both ledger paths relative to
the git clone instead of `~/.claude/projects/<project>/hover-audit-log/`
(item 6). The very next tool built to fix THAT class of bug,
`citation_resolve_check.py`, computed its own `DEFAULT_LOG` the SAME wrong
way — `os.path.join(HERE, 'hover-audit-log.jsonl')` — and crashed
`FileNotFoundError` on its first real `--recheck` run (item 9), fixed in
the same cycle because the crash was loud rather than silently wrong.
`hover2_sha_citation_verify.py`, built in an EARLIER batch, has a related
but distinct version: it resolves its `doc` argument against the process's
current working directory rather than joining it with `--repo`, so it
fails `COULD NOT RUN` unless invoked from exactly the right cwd (item 12).

**Three different symptoms, one root cause: this role's own tools keep
RE-DERIVING "where do my real external files live" from scratch, by hand,
each time, instead of importing one answer.** Item 6 found and fixed the
first instance and wrote it up as a one-off bug fix. Item 9's own tool,
built minutes later by the SAME session that had just fixed item 6, made
the identical mistake — the lesson from item 6 was recorded as a FIX, not
as a REUSABLE FACT, so the next tool never consulted it.

**Applying lesson, concretely:** this role's own `hover-self-log-location`
path logic (both ledgers, the log itself, any future per-instance file)
should live in ONE small shared module (or at minimum one copy-pasted
constant block with a single canonical comment, consistently reused rather
than re-typed) that every new tools-hover2/ script imports or copies
verbatim — not re-derived from "the pattern" by memory each time. Until
that consolidation happens, **every new tool that needs its own external
file path is assumed guilty until its first real run proves otherwise** —
run it for real, against the real path, before trusting any output,
exactly as items 6/9/12 did. The crash-loud failures (9, 12) were caught
fast for free; the silent-wrong one (6, reporting COULD-NOT-RUN rather than
crashing) took a deliberate fail-closed check. A tool whose "could not
find my own data" failure mode is a crash rather than a swallowed
exception is easier to catch by accident — worth preferring on purpose in
any future tool here.

## Base rate, measured this batch: 3 of 3 own-location-dependent tools touched this batch had this exact bug on sight

Not a coincidence worth leaving unnamed, same standard H1's own file sets:
`tool_provenance_status.py` (existing tool, found broken), `citation_resolve_check.py`
(brand new, broke immediately), `hover2_sha_citation_verify.py` (existing
tool, found broken under a cwd this role had never happened to run it from
before). 3 for 3. The measured base rate for "a tools-hover2/ script that
needs to locate a file outside the git clone" on THIS role, as of
2026-10-08, is: assume it is wrong until run.
