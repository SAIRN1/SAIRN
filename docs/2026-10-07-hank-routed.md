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

---

## 3. ONE METHODOLOGY RULE, ROUTED NOT PROMOTED — 2026-10-07, batch b1

**`docs/METHODOLOGY.md` IS CLAIMED BY TWO OTHER SESSIONS AND I DID NOT WRITE TO
IT.** The claims tool was run **first**, as the dispatch requires, and it
REFUSED — so no claim was taken and none needed releasing:

```
python tools/sairn_claim.py check methodology "docs/METHODOLOGY.md one entry from batch b1"
exit 1
BLOCKED -- another session already claimed overlapping work:
  cody   (1.3h ago)  blocked by: same file or resource: docs/methodology.md
  fourth (0.8h ago)  blocked by: same file or resource: docs/methodology.md
```

**And fourth's own item 12 is verbatim this work** — *"methodology entry, claiming
and releasing the shared file around the write."* Writing it twice is worse than
not writing it. The rule is recorded here for chat to land, which is the same
course cc's batch 14 item 10 was given for the same file.

### RULE E — a refusal is scoped to the case that justified it, and an unscoped refusal spreads to cases it does not fit

**STATEMENT.** When work is declined for a stated reason, the reason must be
re-derived **per item**, not written once over a group. A refusal applied to a
group is read later as a property of the group, and the items in it that the
reason never covered are now protected by someone else's argument. **It is harder
to catch than a wrong answer, because the reasoning reads as careful** — and
care is the signal reviewers use to decide what not to re-check.

**TWO INSTANCES, BOTH MINE, BOTH FOUND IN ONE BATCH BY RE-READING A PRIOR
REFUSAL RATHER THAN THE CODE IT REFUSED.**

**Instance 1 — a data-loss hazard that belonged to one of two paths.** Two
SAIRNroofing write paths were left unattributed with one shared reason: *"these
two write paths DO NOT SEND `data` at all. Adding `data: { updatedBy }` would
REPLACE the stored blob, destroying carrier, claim_number and adjuster."*
Re-read at HEAD, `rf_claims/write` **does** send `data: dataBlob`
(`api/sd-data.js:7772`), built from the whole payload through `storedBlob`. It
took the same one-line stamp as five others. Only `rf_schedule/set_status`
matched the stated reason. **The refusal was correct once and reused once**, and
the reuse cost a real attribution gap on a claims table.

**Instance 2 — a routing decision that was really a declined decision.** Eight
tools tracebacked on a bare run; six were fixed and **two were put on a routing
list together**. `docs/tool-owner-map.json` makes them opposite cases:
`gh_push.py` is `"basis": "LAST_CLAIM", "owner": "cc"` — a real target —
while `va_rule_currency.py` is `"basis": "NONE", "owner": null`: **no owner at
all.** A file nobody owns cannot be routed to anyone, so putting it on a routing
list was not deferring the decision to chat, it was declining to make one *while
looking like deferral* — and it would have sat there every batch for exactly the
same reason.

**WHY THIS IS NOT ALREADY COVERED.** Convention 7 (*byte-identical is not
safe-in-context*) is about propagating a proven **fix** to a new target without
re-qualifying it. This is its mirror: propagating a proven **refusal**. The
existing conventions all police what gets DONE. Nothing polices what gets
DECLINED — and a decline leaves no diff, no arm and no exit code, so there is
nothing for a checker to read. The only artefact is the sentence, which is why
the rule has to be about re-deriving per item rather than about a gate.

**THE MECHANICAL FORM, so it is not just an exhortation.** A refusal covering
more than one item must state, **per item**, the specific fact that makes the
reason true of *that* item — a file and line, a column, a constraint name. If the
same sentence is true of every item without a per-item citation, that is the
signal the reason was not actually checked against each one.

**HOW IT WAS CAUGHT, which is the part a rule can act on.** Not by reading the
code — by **re-reading the previous refusal with the code open beside it**. Both
instances survived their original batch because the next reader (me) trusted the
stated reason and went looking for the next item instead. The cheap check is: a
carried-forward refusal is re-derived at HEAD before it is carried forward
again.

---

## 4. ONE METHODOLOGY RULE, ROUTED NOT PROMOTED — 2026-10-07, batch 18

**`docs/METHODOLOGY.md` IS HELD BY TWO SESSIONS AND I DID NOT WRITE TO IT.** The
claims tool was run **once**, as the dispatch requires, and refused:

```
python tools/sairn_claim.py check methodology "land Rule E into docs/METHODOLOGY.md single write"
exit 1   BLOCKED
  cc      2026-10-07T23:20:05Z  (0.6h)  same file or resource: docs/methodology.md
  fourth  2026-10-07T20:30:06Z  (3.4h)  same file or resource: docs/methodology.md
```

**RULE E therefore stays where it is — section 3 of this file — unlanded.** No
second retry was made this batch. cc's own claim says its methodology item is
*"paste-ready because the target is held"*, which is the same answer arrived at
independently.

### RULE F — a rebase invalidates every artefact that CITES A SHA or is DERIVED FROM THE OUTGOING RANGE, and it does so WITHOUT A CONFLICT

**STATE IT AS:** *anything whose content is a function of the commits being
pushed — a register record naming a sha, a review obligation derived from the
outgoing range — must be produced AFTER the final rebase. A rebase rewrites
those shas and moves that range. The artefact does not conflict, does not look
damaged, and points at a commit that no longer exists.*

**WHY IT IS NOT ALREADY COVERED, checked rather than assumed.** PR §2.1 and the
generated-document section of the process rules cover the adjacent case well:
a **generated** document must be **regenerated** after a rebase, never
hand-merged, because a resolved hunk is the generating function evaluated *at no
state at all*. That section even carries the `docs/tier-a-reviews.json`
incident, where a hand-resolved conflict took the wrong side of one record's
status fields.

**Both of those are CONFLICT cases. This one has no conflict.** `git rebase`
replays my commits onto new upstream work and hands back new shas with a clean
tree and nothing to resolve. A `defect-density-register.json` record written
before that replay is still valid JSON, still passes every shape check, and its
`commit` field now resolves to nothing. **There is no hunk, no marker, and no
moment where anybody is asked a question.** §2.1's instruction — rebuild the row
whole — cannot fire, because the row was never touched.

**PAID FOR 2026-10-07, batch b1, three times in one push.** The push gate
refused for an unfed register; three records were added citing `38839e5f`,
`a53153bd`, `e86c57ed`; a rebase onto 22 incoming commits rewrote all three;
the records were re-added against `aba0e0a9`, `469eec19`, `1c8a395c`; another
race rewrote those too. **A register record whose `commit` resolves to nothing
is exactly the vacuous row that file exists to prevent**, and
`defect_register.py --check` would have caught it only *after* the push landed.
The same applies to a `tier_a_review_gate.py --open` obligation, which is
derived from the outgoing range rather than from any file.

**THE MECHANICAL FORM.** Order the landing as **rebase → derive → commit →
push**, and re-derive on every retry rather than remembering. In batch 18 that
is `scratchpad/land.sh`, which recomputes the shas and re-runs `--open` on each
cycle and landed on cycle 1 once the order was right.

**AND THE SMALLER FACT THAT COST A WHOLE CYCLE, worth one line wherever this
lands:** after `git reset --soft`, the INDEX still holds the change, so
`git checkout -- <path>` restores the worktree *from the change* and leaves the
file **staged** — the next rebase then refuses on an unclean index.
`git restore --source=HEAD --staged --worktree -- <path>` is the one that works.

**WHERE IT BELONGS:** alongside the generated-document rule in the process
rules, as its no-conflict sibling — not as a 26th cross-domain convention. The
cross-domain conventions are about how a CHECK can be wrong; this is about the
order of operations in a push.
