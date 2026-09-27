# A check whose only trigger cannot fire for what it checks

**Swept 2026-09-26 (CC).** Tool: `tools/invocation_path_scan.py` (report-only,
`--selftest` 7 arms). Run it rather than quoting the numbers below.

---

## Why this sweep exists

`tools/register_freshness_check.py` was written 2026-09-24 to catch a register
citation that no longer points at what it says. Every arm of it was right. It
was registered. **And it never once ran because of an edit to either document
it checks.**

Its only wiring was `report_only_checks.REGISTRY`, and that sweep's hook opens
with:

```python
if payload and not pushes(cmd):
    return 0                      # report_only_checks.hook_main()
```

So the checker ran after a **`git push`**. The two documents it reads —
`docs/CRITICALITY-TIERS.md` and `docs/tier-a-reviews.json` — are changed with
Write and Edit. Editing a citation-bearing document triggered nothing at all,
and a session that edited one and did not push ran it **zero times**.

**This is not PR 1.1 (a check that stopped checking) and not a check that never
worked.** The finding is a wiring fact: the trigger and the subject are in
different worlds, and nothing about either one says so. A check like that
reports a clean result — eventually, somewhere else, attributed to somebody
else's push.

It had already cost something twice. All nine line citations on
`sc_anesthesia_base_units` went 30–45 lines stale **within a day**, found only
because a review obligation happened to send a reader there. And `8d0430c3`
records five drifted cites introduced **by a correction to that same
document** — the edit that breaks a citation is almost always an edit to the
document the citation lives in, which is the one moment nothing was watching.

Closed by `tools/citation_drift_hook.py`, wired PostToolUse Write|Edit.

---

## The structural finding, which is larger than the instance

**All 62 registered report-only checkers run at push time only.** Not after any
Bash command — after a `git push` specifically, and not after one the pre-tool
gate denied. This repo denies pushes routinely.

That is a defensible decision for most of them: they are a push-time report on
a promotion path, and running 62 checkers on every keystroke would be absurd.
It is **not** defensible for a checker whose subject is a document a human
edits and whose finding is cheapest at the moment of the edit. Those are the
candidates below.

---

## The five candidates, each read and decided

The tool derives candidates from each checker's own `catches` text and refuses
to classify them, because whether a document named there is the checker's
**subject** or a **source it reads** is a read, not a regex. Here is the read.

### 1. `index_duplicate_check.py` → `docs/SAIRN-OPEN-WORK-INDEX.md` — **REAL, same shape**

Its own words: *"two rows … describing the same subject — a superseded row that
was never removed, so the file every session reads to choose work gives two
answers and the reader cannot tell which is current."*

The document **is** the subject, and the defect is **introduced by an edit to
it**. This is `register_freshness_check` again, in a file edited more often than
either of that tool's two documents and read by every session at start to
choose work. On the day it was built the index held two such pairs, both left in
place.

**Recommended fix, and it is a decision with a cost, so it is named and not
taken here:** a Write|Edit hook scoped to that one path, the same shape as
`citation_drift_hook.py`. The cost is a third scoped hook script, or a
dispatcher mapping document → checker. Wiring the checker *directly* to
Write|Edit is the wrong answer: it does not self-scope by `file_path`, so it
would run on every edit in the repo and be switched off within a week.

### 2. `defect_register.py` → `docs/defect-density-register.json` — **REAL but narrow**

Its subject is the register, and `--check` catches a record that has stopped
being true. But the register is **written through the tool**, which validates
on `--add` and refused five things a hand-written record got wrong earlier
today, and a post-rebase hook already re-seats shas automatically. The
uncovered case is narrow: somebody hand-editing the JSON. Real, low value,
lower than (1).

### 3. `secrets_inventory.py` → `docs/SECRETS-INVENTORY.md` — **NOT this class**

It catches *"`docs/SECRETS-INVENTORY.md` drifting from the code — a new
environment variable, a removed one, or a guard that moved."* The document goes
wrong when **the code** changes, not when the document is edited. An edit
trigger on the document would fire at the one moment the document is *most*
likely to be right.

This is the **code-authored variant** of the same class, which the tool prints
as a blind spot it cannot see: the correct trigger is an edit to code, and
that fires constantly. Not fixed here, and not dismissed — named as a separate
open question.

### 4. `dependency_graph.py` → `docs/SPOF-REGISTER.md` — **NOT this class**

Same reasoning as (3), including the sharp arm it carries (*"a row marked
RETIRED while the component is still above the bar"*): the register goes wrong
because the code's chokepoints moved, not because somebody edited the register.

### 5. `dispatch_state.py` → `docs/SAIRN-OPEN-WORK-INDEX.md` — **NOT this class, DIFFERENT gap**

Its subject is the **join** of the open-work index and the live claims, not
either document. Its question is *"what should I work on"* — and the moment
that question is asked is **session start and dispatch**, not a document edit.

It is currently push-triggered, which is the least useful moment of all for it:
by the time you push, you have already done the work. Measured on the run that
motivated it: a five-item queue was dispatched and **four were another
session's live or owned work**, three named verbatim in a claim made six
minutes earlier.

**This is a genuine wiring gap of a different shape — right check, wrong
moment — and it is a candidate for `SessionStart`, where `sairn_claim_hook.py`
and `sairn_status.py` already run.** Not taken here; it is a decision about
what a session is told at start.

---

## What this sweep did not look at

Printed by the tool on every run, repeated here because a limitation in a tool's
output is a limitation nobody reads:

- A checker whose subject is **code** rather than a document is out of scope
  entirely. Write/Edit fires for code too, so the same class exists there and
  this sweep reports every one of them as fine. Findings (3) and (4) are in it.
- Only **registered** checkers are enumerated — the registry, the
  `.claude/settings.json` hooks, the push gate. A check existing as a bare
  script nobody wired is invisible here and is a different finding. Measured
  separately: of 226 tracked Python tools, **5** are referenced by no hook,
  gate, registry, test or other tool (`gen_ma_seed.py`, `gen_mn_seed.py`,
  `gen_mo_seed.py`, `gen_va_seed.py`, `js_code_only_diff.py`) and all five are
  legitimately CLI-only generators.
- It reads **wiring, never behaviour**. A checker wired to Write|Edit that
  returns early for the file it was handed reads as covered.
- The push-gate list comes from name occurrences in `sairn_push_gate_hook.py`,
  so a tool named only in a comment there reads as invoked.

## Found while sweeping, NOT fixed, and not mine to fold in

**`python tools/report_only_checks.py --list` has been crashing.** It raises
`KeyError: 'evidence'` on the first registry entry that lacks that key, and
**four do**: `register_freshness_check.py`, `log_cluster.py`,
`allan_deviation_check.py`, `response_shape_check.py`. Verified against HEAD as
well as the working tree, so it predates this sweep.

That matters more than a broken flag: `--list` is the registry's only
human-readable surface — the thing that prints what each of the 62 checkers
catches, why it matters, and what it found on a real run. It has been unusable
since the second of those four entries was added, and nothing noticed, because
nothing else reads `evidence`.

**Not fixed here, deliberately, and the two candidate fixes are not equivalent.**
Writing evidence text for four checkers I have not run would be fabricating the
one field in that registry that is supposed to be a measurement. Changing the
print to `e.get('evidence')` is a one-line fix and is only correct if it prints
something like `NO EVIDENCE RECORDED` — a third state — rather than an empty
string, which would turn a crash into a blank cell and make an unmeasured
checker indistinguishable from a measured one. That is the same decision
`tooling_inventory.py` already makes when it refuses to emit a blank cell.
Michael's call, separately from this sweep.

## Decisions left open, deliberately

1. Wire `index_duplicate_check.py` at edit time (scoped hook, or a
   document → checker dispatcher). **Recommended.**
2. Move `dispatch_state.py` to `SessionStart`.
3. The code-authored variant: what, if anything, should run when code changes
   that could stale `SECRETS-INVENTORY.md` or `SPOF-REGISTER.md`.

`invocation_path_scan.py` is **deliberately not promoted** into the push sweep,
and the reason is recorded in `report_only_checks.NOT_PROMOTED`: its own subject
is `.claude/settings.json` and `report_only_checks.py`, both edit-authored, so
registering it at push time would make it an instance of its own finding.
