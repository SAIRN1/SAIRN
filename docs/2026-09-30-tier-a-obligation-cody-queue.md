# Tier A review obligation — cody, 2026-09-30 queue (ledger held by hank)

**This is a review obligation that belongs in `docs/tier-a-reviews.json` and could
not be recorded there.** `docs/tier-a-reviews.json` is claimed by **hank**
(claimed 2026-09-30T13:26:35Z), and the claim tool refused twice, forty minutes
apart, with:

> `DO NOT start this. Flag it back to the coordinating chat session and let it
> decide who runs it.`

It is written here so the obligation exists in a file somebody can read, and so
the next session to hold the ledger can move it across verbatim. **A document is
weaker than a ledger row** — a row is queued and chased, this is read once — and
that weakness is the reason it is recorded rather than dropped.

**Assign to:** any session other than cody. **Resources named:** `rf_cert_rules`,
`rf_contingency_rules`, `stonedesk_quote_history`.

---

## The names are strings, not branches

**No code serving any of the three was changed.** They appear on changed lines
for these reasons and no others:

| resource | where it appears | what it is |
|---|---|---|
| `rf_cert_rules` | `tools/bare_run_writers.py` | one of five declared output paths, `sql/rf_cert_rules_load_gate_generated.sql` |
| `rf_contingency_rules` | `tools/bare_run_writers.py` | the fifth declared output path, added because the sweep caught it missing |
| `stonedesk_quote_history` | `tests/quote_builder_delete_does_not_resurrect.js` | the storage key inside a line lifted verbatim from `stonedesk.html` so the test does not re-type it |

This is PR §1.2 — grep cannot tell code from text that describes code — and the
correct response is to record the obligation rather than argue with the gate.

## What changed

- `tools/bare_run_writers.py` — NEW. The 20 tools whose bare run is supposed to
  write, each with the path it writes and why.
- `tools/bare_run_write_check.py` — reads that list, reports its entries as
  `INTENDED` rather than omitting them, and fails when a declared writer writes a
  path it did not declare.
- `tools/tool_owner_header_check.py` — NEW, plus its probe and the push-gate
  wiring: a newly ADDED `tools/*.py` must carry `# OWNER: <session>`.
- `tools/condition_coverage.py` — mutates a detached worktree instead of
  `api/_lib/ledger.js`; `--report` added and refuses a source path.
- `tools/nhi_register.py` — bare run is report-only; the sibling scan is bounded.
- `tools/schema_provisioning_check.py` — a session-gated 403 now says so.
- Twenty generators — one `OWNER-INTENDED BARE-RUN WRITER` header comment each.
- Three StoneDesk suites re-anchored; one generated-doc regeneration.

## What to attack

**(a) THE ALLOWLIST IS A HAND-WRITTEN LIST OF PATHS AND IT WAS ALREADY WRONG.** I
declared four output paths for `sairn_build_load_gates.py` and it writes five. The
sweep's undeclared-path check caught it on the first real run, which is the arm
working — but the same class can recur on any entry whose generator gains an
output, and the only thing standing behind each entry's REASON is my judgement.
Read the reasons, not the paths; the paths are machine-checked and the reasons are
not.

**(b) `master_plan.py`, `traceability_matrix.py` AND `tooling_inventory.py` ARE
STILL BARE-RUN WRITERS BY DESIGN, AND THAT IS A DECISION.** I was told not to
change the push gate's `fix: python tools/master_plan.py` lines and I did not.
The consequence is that three tools the gate itself invokes will rewrite
documents if anybody runs them to see what they do. The allowlist makes that
visible rather than safe. If the right answer is `--write` on all three plus the
gate's fix lines updated in the same change, this is where to say so.

**(c) THE OWNER GATE GRANDFATHERS 282 TOOLS AND I CHOSE THAT.** A gate refusing
every push touching any tool would be switched off within the hour, so it applies
only to files a push ADDS. The 282 still have no owner, the count is printed on
every run, and nothing forces it down. Argue for a deadline or a per-push
decrement if you think the printed count is not enough.

**(d) `condition_coverage.py` NOW NEEDS A WORKTREE TO RUN AT ALL.** A clone where
`git worktree add` fails gets exit 2 COULD NOT RUN instead of a measurement. That
is the fail-closed direction and it is also a new way for the tool to be
unavailable. I did not test it against a clone with worktrees disabled.

**(e) THE SIBLING-SCAN CAP IS 32 AND I PICKED THE NUMBER.** Seven working copies
exist today. 32 leaves room for worktrees beside them and is far below the 1865
that caused the timeout, but nothing measured where the real boundary is, and a
clone parent that legitimately holds 33 repositories now gets a refusal.

**(f) THE OWNER FIELD IS SELF-ASSERTED.** `# OWNER: cody` is checked against the
session list and against nothing else. A tool whose header names a session that
did not write it passes.
