# Routed by hank — 2026-10-07, batch b1

Everything here is **routed, not done**. Each entry names the file, the line, the
owner the owner map gives, and a command that reproduces it.

---

## 1. ROUTED TO CC: `tools/gh_push.py:182` tracebacks on a bare run

**THE LAST OF THE EIGHT.** Eight of 315 scripts under `tools/` raised
`IndexError: list index out of range` on a bare run where 67 others refuse in
words. Six were fixed at `47d69604`; `tools/va_rule_currency.py` is fixed in this
batch; **this one is owned by somebody else and is not touched.**

**OWNER, from the mechanism rather than from inference.**
`docs/tool-owner-map.json` records:

```json
"gh_push.py": { "also_claimed_by": [], "basis": "LAST_CLAIM",
                "last_claim": "812857c0", "owner": "cc" }
```

That is a real routing target, which is why this is a routing and not a
judgement call. (Contrast `va_rule_currency.py`, whose entry is
`"basis": "NONE", "owner": null` — **no owner at all.** A file nobody owns
cannot be routed to anyone, so leaving it on a routing list was not deferring
the decision, it was declining to make one. It was taken under this batch's
claim and the move is stated in the probe's own header.)

**REPRODUCING COMMAND, one line:**

```
python tools/gh_push.py
```

```
Traceback (most recent call last):
  File "...\tools\gh_push.py", line 240, in <module>
    main()
  File "...\tools\gh_push.py", line 182, in main
    commit_message = sys.argv[1]
IndexError: list index out of range
```

**EXACT LINE AND CHANGE.** `tools/gh_push.py:182` is
`commit_message = sys.argv[1]`. The fix is the same shape the other seven now
carry — a `len(sys.argv) <= 1` guard that writes `COULD NOT RUN:` plus a
`usage:` line to stderr and exits **2**.

**WHY EXIT 2 AND NOT 1, which is the whole point.** On this platform exit 1
means FINDINGS and exit 2 means COULD NOT RUN. An uncaught `IndexError` exits 1.
So a tool that tracebacks on a missing argument is indistinguishable, to anything
reading an exit code, from a tool that ran and found something — the third-state
collapse **PR §1.11** names, arriving through a missing `len(sys.argv)` check.

**AND IT IS WORSE HERE THAN IN THE OTHER SEVEN.** `gh_push.py` PUSHES. The other
seven are read-only measurement helpers whose bare run wastes a reader's time. A
sweep that reads exit 1 from this one as "ran, had findings" is misreading a tool
that **did not push**, and the thing it did not do is the thing somebody is
relying on.

**NOT ADDED TO `tests/run_tool_usage_refusal_probe.py`.** Adding an arm for a
file I am not fixing would make that probe red on arrival for cc, and a probe
that fails for a reason outside its owner's change is how a red bar stops being
read. The arm belongs in the same commit as the fix.

**A REGRESSION ARM FOR IT IS ONE LINE** once the fix lands: append
`'gh_push.py'` to `SUBJECTS` in `tests/run_tool_usage_refusal_probe.py` and
remove it from `NOT_MINE`. Driving it bare is safe — the guard returns before
any git call — but **confirm that before running the arm**, because the point of
the arm is that the tool refuses rather than acts.

---

## 2. RETRACTION — the auditor-namespace crash was routed to FOURTH and should not have been. **CHAT HOLDS IT.**

**WITHDRAWN:** `docs/2026-10-06-hank-routed-to-fourth.md` **§9**, which routed
`tools/hover_separation_ci.py`'s crash to fourth. The section is marked retracted
in place; its text and evidence are left intact rather than deleted.

**THE FINDING IS NOT WITHDRAWN AND WAS RE-DERIVED AT HEAD `2dff2da7` TODAY:**

```
python tools/hover_separation_ci.py
AttributeError: module 'hover_separation_audit' has no attribute 'AUDITOR_SCOPE'
exit 1          (tools/hover_separation_ci.py:97)
```

`git status` captured before and after: no change from this run.

**WHY THE ROUTING WAS WRONG.** These two files are the **detect** half of the
build/audit boundary. `CLAUDE.md` says a build agent must not reach into that
boundary's machinery, *"including to arm those gates; that is the same boundary
problem running the other way."* **Fourth is a build agent.** Handing a build
agent the repair of the detector that constrains build agents recreates the exact
separation the gate exists to hold — and it does so while looking like ordinary
routing, which is what made it easy to write.

**THE MISTAKE HAS A SHAPE WORTH NAMING.** I reasoned about **tool ownership**
(who may edit this file) when the governing question was **role separation** (who
may be *asked* to). `docs/tool-owner-map.json` has no column for the second, I did
not go looking for one, and an owner lookup that returns an answer feels like a
completed check. A routing decision needs BOTH questions asked, and only one of
them has a tool.

**AND A SECOND REASON THAT STANDS ALONE.** §9's own conclusion is that the fix is
not a blind substitution: the old name was a flat tuple, the new API is a constant
**plus a predicate**, and comparing against only the SHARED half *"would make the
equality check pass while silently dropping what the predicate covers — a green
that means less than the red it replaced."* Choosing which comparison is intended
is a decision about what the boundary **means**. That is chat's.

**NO NEW AGENT IS NAMED.** Nothing in the hover auditor namespace was touched,
read for this purpose, or routed by me.
