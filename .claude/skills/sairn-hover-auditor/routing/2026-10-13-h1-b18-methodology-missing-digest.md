# H1 batch b18 item 5 -- blameless methodology note: b16's missing digest

Written 2026-10-13, batch b18. Blameless, per the platform's own standing
convention (`sairn-adversarial-reviewer`'s cross-domain discipline, and
this file's own Safe Harbor section): this names a process gap, not a
failing of the session that hit it.

## What happened

b16's own report (`SAIRN-report-h1-b16.txt`) was uploaded to Drive at
08:18 UTC with its SHA256 line left as the literal string `PLACEHOLDER`.
`SAIRN-digest-h1-b16.txt` was never written or uploaded at all. b17
(picking up after compaction) found both gaps, named them in its own
report and handoff, and did not retroactively patch the b16 file (AS-FOUND,
not overwritten) or fabricate a backdated digest.

## Root cause

A context-window compaction event landed between the report upload and
the two remaining finalization steps (compute the real hash, write the
digest). Nothing in the batch-close sequence as currently practiced
checks, AFTER the fact, that a report and its digest were BOTH produced
for the same batch number before the session ends -- the sequence is
trusted to run to completion in one pass, and a compaction (or any other
interruption) between steps leaves a partial, undetected gap. This is
not a one-off: it is the same class of gap PR's own standing material
names directly -- "nothing announces the day a check stops testing
anything" applies here one level up, to the REPORTING process itself
rather than to a code checker.

## Proposed mechanical check (not built here -- naming it, not building it)

A small script, run at the START of a new batch (before any audit work,
alongside the existing claim/chain-tip resume check already performed
every batch) that:

1. Lists every `SAIRN-report-h1-b<N>.txt` and `SAIRN-digest-h1-b<N>.txt`
   title present in the Drive status folder (same `search_files` call
   this role already uses at resume time).
2. For every batch number N with a report present, confirms a digest
   with the SAME batch number is also present. A report with no matching
   digest is a **STILL OPEN** finding, named by batch number, not silently
   carried forward.
3. Separately, opens each report found and confirms its SHA256 line is
   NOT the literal string `PLACEHOLDER` and is a syntactically valid
   64-hex-character string -- a report that uploaded successfully but
   never got its hash computed is the other half of this exact gap
   (b16 had both: no digest, AND a placeholder hash).
4. Reports a clear STILL-OPEN / CLEAN verdict for the batch range checked,
   the same three-state discipline (pass / fail / could-not-run) already
   required everywhere else in this role's own method -- never silently
   folding "nobody checked yet" into "clean."

This is deliberately proposed as a resume-time check (run by the NEXT
session, reading Drive) rather than an end-of-batch self-check (run by
the SAME session that might be the one getting compacted) -- a check that
depends on the interrupted session finishing cleanly to run at all would
not have caught this exact incident, since the interruption is precisely
what prevented the finishing steps. A check that survives the interruption
has to live in a DIFFERENT session's resume sequence, the same reasoning
this role's own chain-tip/token verification already follows (verify the
real state, never trust that the prior session's own account of itself
was complete).

## Who builds it

Not this role -- this is tooling that reads this role's OWN Drive
artifacts (reports/digests), which is this role's own operational
tooling per the skill file's stated exception ("the self-log, anything
that records or verifies the hover auditor's own actions"), so it is
this role's to build, not a build agent's. Named here as a proposal
rather than built in this batch because item 5 as dispatched asked for
the methodology note, not the implementation -- flagged as a candidate
for a future batch's own tooling work.
