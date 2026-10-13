# H1 -> cc: exact push-gate refusal text, generator refuses on empty hooks

Written 2026-10-13, batch b18 (H1/hover). Per Michael's decision (relayed
in this batch's dispatch): this is cc's to fix, not Michael's decision and
not this role's to work around. cc has it queued (re-clear hooks, commit
`hooks: {}` so HEAD matches, make the external-files check warn instead
of block). This doc exists so cc has the exact repro and exact text
rather than a paraphrase.

## Repro command

From the repo root, with `.claude/settings.json`'s hooks object empty
(this clone's standing, intentional state):

    python tools/tooling_inventory.py

Exit code: **2**.

The same failure also fires inside the push gate itself
(`.githooks/pre-push -> tools/sairn_push_gate_hook.py --pre-push`), which
calls this same generator and treats its exit 2 as a hard block -- this
was hit for real on two separate pushes this session (batch b17, HEAD
`26cd486e` and `73d69ddf5455`), both refused identically.

## Exact text (captured 2026-10-13, this batch, via the repro command
above, no flags)

```
NOTE: no report_only_checks.py hook entry found in C:\Users\marsh\Documents\SAIRN-hover\.claude\settings.json, so the sweep budget below is a FALLBACK.
NOTE: no report_only_checks.py hook entry found in C:\Users\marsh\Documents\SAIRN-hover\.claude\settings.json, so the sweep budget below is a FALLBACK.
NOTE: no report_only_checks.py hook entry found in C:\Users\marsh\Documents\SAIRN-hover\.claude\settings.json, so the sweep budget below is a FALLBACK.
CLOSING ERROR -- docs\TOOLING-INVENTORY.md derives from 7 source(s):
  tools on disk                      335   git ls-files tools/
  hook entries                         0   .claude\settings.json  <<< EMPTY
  push-gate invocations               13   tools\sairn_push_gate_hook.py
  report-only registry                76   report_only_checks.REGISTRY
  tools invoked by tests/            232   tests/**/*.py, *.js
  recorded NOT-promoted decisions     86   report_only_checks.NOT_PROMOTED
  numbered gate checks                17   tools\sairn_push_gate_hook.py

REFUSED: 1 derivation source(s) contributed NOTHING, so this
document would have been written from less than it claims:
  hook entries -- read from .claude\settings.json

A zero here is a BROKEN READER or a MOVED SOURCE, not an empty
repo -- and the two are indistinguishable downstream, which is
why this refuses instead of writing a thinner document that
would pass its own --check every time.
REFUSING to generate -- the traverse did not close: docs\TOOLING-INVENTORY.md: 1 empty source(s): hook entries
```

The push-gate's own surrounding wrapper (as seen at `git push`, b17
batch, same exit-2 condition) additionally prints:

```
Exit 1 and exit 2 are different problems and the fix differs. 1 means
regenerate. 2 means the generator's HAND-WRITTEN half has drifted -- a
tool this push adds with no entry describing it -- and it refuses rather
than emitting a blank cell. A refusal also FREEZES every unrelated
correction behind it, which is why it blocks here instead of waiting.

This check refuses only what THIS push broke. A document left stale by
somebody else is reported above and does not block you.
Override by putting SAIRN_SEED_GATE=off at the FRONT of the push command itself (SAIRN_SEED_GATE=off git push ...), not in a separate export. Say so out loud if you do.

(blocked by .githooks/pre-push -> tools/sairn_push_gate_hook.py --pre-push)
```

## What this role did NOT do

`SAIRN_SEED_GATE=off` was not used, on either of the two b17 refusals or
this batch's check. This role does not push through this gate and does
not need a decision from Michael on it -- Michael's decision is already
made (relayed this batch): the fix is cc's, structured as (1) re-clear
hooks, (2) commit `hooks: {}` so HEAD matches the intentionally-empty
state, (3) make `external_file_index_check` warn rather than block for
handoff names (a separate, adjacent item on cc's own queue, not this
gate's hooks-source problem, named here only because cc's claim text
groups both).

## Status at time of writing

Checked `origin/main` before writing this: cc's active claim (`.claude/
claims/cc.json`, taken ~1.8h before this batch started, subject `cc`,
task text includes "hooks disarmed and COMMITTED in this clone per
Michael... external_file_index_check warn-not-block for handoff names")
covers exactly this fix. `git fetch origin` + `git log main..origin/main`
at the start of this batch showed only hank's two commits
(`618cbd9f`, `f442989b`) -- cc's fix had NOT landed yet. Per this batch's
own instruction, the push was skipped rather than retried against a gate
still known to refuse the same way.
