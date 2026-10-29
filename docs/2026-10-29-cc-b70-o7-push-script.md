# O7: the push script that skips derived-doc regeneration in gate mode (cc b70, 2026-10-29)

**Routed by** cody b62 (`SAIRN-handoff-cody-b62.md` §1 and O7). **Assigned to
cc** in Michael's b70 dispatch.

## What "the push script" is

It is **not a tracked tool.** It is cody's scratchpad loop:

    C:/Users/marsh/AppData/Local/Temp/claude/C--Users-marsh-Documents-SAIRN-cody/05129111-.../scratchpad/push_once.sh

That is cody's newest copy (2026-10-28 17:31). cc read it and **did not edit
it**: a scratchpad belongs to the session that keeps it.

## The defect, confirmed in its source

After each rebase, the script regenerates `docs/MASTER-PLAN.md` and
`docs/traceability-matrix.md` **only inside**:

    if grep -q "whole-tree re-check not green" "$SP/decide.txt"; then

That is the pure-base-skip decision path. In **gate mode**, any other
`pure_base_skip.py` outcome, nothing is regenerated. So the full gate runs
against derived documents that the rebase just made stale, and it refuses on
`derived-docs`. That is exactly cody's b62 double refusal.

It also never regenerates **`docs/TOOLING-INVENTORY.md`**, the third document
the gate holds.

## The regenerated script (the fix)

Replace the conditional block with an **unconditional** regeneration right
after the rebase and re-seat, and before the skip decision. That way both
paths push current documents:

```bash
  # REGENERATE AFTER EVERY REBASE, BOTH PATHS (cc b70, O7). The pure-base skip
  # is decided on the tree AFTER this, so a skip never ships stale documents
  # and a full gate never refuses on them.
  PYTHONIOENCODING=utf-8 python tools/master_plan.py >/dev/null 2>&1
  PYTHONIOENCODING=utf-8 python tools/traceability_matrix.py >/dev/null 2>&1
  PYTHONIOENCODING=utf-8 python tools/tooling_inventory.py >/dev/null 2>&1
  git add docs/MASTER-PLAN.md docs/traceability-matrix.md docs/TOOLING-INVENTORY.md
  git diff --cached --quiet || git commit -q -m "chore(derived-docs, cody): regenerated after rebase

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  PYTHONIOENCODING=utf-8 python tools/pure_base_skip.py --old-base "$old_base" --gated-patches "$STATE" > "$SP/decide.txt" 2>&1
  d=$?
```

Then delete the old `if grep -q "whole-tree re-check not green" ...; fi`
block.

**Trade-off, stated.** A new derived-docs commit changes the outgoing patch
set. `pure_base_skip.py` may therefore choose the full gate where it would
have skipped. That is the safe direction: a few minutes of gate, never a
stale push.

## The durable alternative, already in the repo

`tools/push_retry.py` already does what O7 asks:
- it calls `_regenerate_and_fold()` after **every** successful rebase
  (line 1312, inside `if behind > 0:`);
- it calls it again on any push refusal that names a generated document
  (line 1391);
- all three documents are in its `GENERATED` list;
- since hank b64 (`2a49d1e1`), regenerated docs go into their own
  `chore(derived-docs …)` commit, which `authored_commits()` excludes from
  the patch-id comparison. A fast retry therefore stays fast.

**Recommendation to cody:** retire `push_once.sh` for `python
tools/push_retry.py`. If you keep the script, apply the block above.

## Cause tag

Logged in `docs/recurring-bug-classes-2.md`, section C4:
**construction → automation script → a remedy gated on an unrelated
condition.** It is the same shape `push_retry.py` itself had until 2026-10-05,
whose own comment calls it "a retry loop whose remedy is gated on an
unrelated condition".
