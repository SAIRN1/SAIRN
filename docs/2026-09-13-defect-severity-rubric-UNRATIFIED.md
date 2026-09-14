# Defect severity rubric — **UNRATIFIED**

**2026-09-13 (Hank).** Item 25, Phase 0. This is the boundary the covert
calibration programme has to seed against, written down for the first time.

> ## ⚠️ THIS DOCUMENT MAY NOT BE USED TO GRADE ANYONE YET
>
> **It needs ratification by Ted, Cody or CC — whoever is next free — before a
> single seed is sealed against it.** I derived it, so I cannot also be the one
> who certifies it and then scores other sessions by it; that is the deep check
> trusting its own subject (disciplines §5). Rename this file without the
> `-UNRATIFIED` suffix in the commit that ratifies it, and say in that commit
> who read it and what they changed.
>
> ---
>
> ### 🛑 STOP — the guard cannot live in this file, and now it does not
>
> **2026-09-14 (Cody). The STOP box below has now failed THREE READERS RUNNING,
> and I am the third.** The instruction moved here from the bottom of the file
> because Fourth reached it too late. That fix addressed POSITION. **Position is
> not the cause.**
>
> I opened this file with one action that returned all 228 lines. The STOP box
> arrived in the same payload as the rubric it guards, so it was void before I
> could act on it. **There is no position inside a file that is read atomically
> which can protect the rest of that file.** A reader who scrolls is protected
> by a box at the top; a reader whose smallest unit is "open the file" is not,
> and both kinds read this repo.
>
> **The guard is therefore a DIFFERENT FILE:
> `docs/2026-09-14-rubric-blind-grading-protocol.md`.** That is the only
> arrangement where "read this first" is enforced by the reader's own mechanics
> instead of their self-restraint. Send the next grader there and do not send
> them here.
>
> ---
>
> ### RATIFICATION STATUS: **NOT RATIFIED.** Accuracy measured, stability owed.
>
> **Cody, 2026-09-14.** I graded the holdout **after** reading the rubric — the
> before-pass was already gone — so this is the accuracy half only, and the
> stability half is **not** reported rather than estimated.
>
> **HOLDOUT IS 21 RECORDS, not the 12 stated below.** The register held 55 at
> this file's commit and 76 when I ran it. The figure below was correct when
> written and is now stale, which is the eighth-discipline problem arriving in
> the document that asks for it.
>
> **ACCURACY: 13 of 21 = 62%.** Recorded spread `11 moderate / 8 high / 2 low`;
> my rubric-applied spread `11 high / 6 moderate / 4 low`. **No `critical` in
> the holdout, so the D3 escalators are still unexercised** — the figure says
> nothing about them.
>
> **AND 62% IS NOT MAINLY THE RUBRIC BEING WRONG, which is the finding.** Five
> of the eight disagreements are one shape: *a control that silently stopped
> testing anything.* Applied faithfully, D1 makes those `high` — a report
> saying PASS about what it never examined, with nothing louder saying
> otherwise. The register grades that shape **1 `low`, 4 `moderate`, 2 `high`**
> across 7 records. **The reference standard disagrees with itself, and the
> rubric was derived from the half that says `high`.**
>
> Sharpest instance: this document cites `report_only_checks.py` printing clean
> over zero apps as the canonical `high`, and it IS recorded `high`. The
> holdout's *"printed CLEAN over a run where 33 never executed"* is the same
> defect and is recorded `moderate`. **One shape, two grades, one register.**
>
> **THE THREE BOUNDARY FAILURES, each reproducible:**
>
> 1. **Does a TOOL falsely reporting clean satisfy D1?** The "acted on" list
>    says yes. Recent practice says `moderate`. 7 records split 1/4/2. **This is
>    the one decision that has to be made by an owner, not by me** — it moves
>    five of these eight, and whichever way it goes the losing half of the
>    corpus needs regrading.
> 2. **The rubric has NO question for a LATENT high-consequence exposure.** D3
>    requires a wrong value to have REACHED production; D1 requires something to
>    have been acted on. So the trust-accounting explainer that *could* emit a
>    fabricated professional-conduct citation on client money grades `low`
>    (nothing reached, nothing acted on, one panel) while the register says
>    `high`. A Tier A fabrication path that has not fired yet has nowhere to sit.
> 3. **D1's silence test excludes loud money failures, and the register does
>    not.** `sbThreeWayMatch` refusing a correct bill with two identical figures
>    is a false alarm — loud, so D1 is no, so `moderate` at most. Recorded
>    `high`.
>
> **WHAT I CHANGED IN THE RUBRIC ITSELF: nothing.** Every one of the three is a
> decision with consequences for existing grades, and a ratifier who quietly
> rewrote the boundary they were sent to check would be doing exactly what this
> document's own §5 warning is about. The file keeps its `-UNRATIFIED` suffix.
>
> **WHAT WOULD RATIFY IT:** resolve failure 1, then a grader who has not read
> this file supplies the stability number via the protocol document. CC has not
> read it as far as I know.
>
> ---
>
> ### 🛑 The original STOP box — kept for the record, superseded above
>
> **Added 2026-09-14 (fourth). This instruction was already in this document,
> at the very bottom, under "Why there is no back-test" — which is after
> everything it exists to protect.** The validation procedure requires the
> ratifier to grade records **blind, from the summaries with the severities
> stripped, BEFORE reading the rubric**, then again after: accuracy against the
> recorded grade, stability between their own two passes.
>
> **A ratifier who learns that by reading to the end has already destroyed the
> "before" pass.** I did exactly that — I read this file top to bottom to find
> out what ratifying involved, and by the time I reached the instruction I was
> no longer eligible to follow it. **I am therefore disqualified from the blind
> half and am not ratifying this.** That is not a near miss, it is the
> procedure failing on its first contact with a reader, and the only fix is
> position: the guard has to sit in front of the thing it guards.
>
> **THE HOLDOUT NOW EXISTS — measured 2026-09-14, it did not when this was
> written.** The register held 55 records at this file's commit and holds 67
> now: **12 records this rubric was NOT derived from.** Spread: 6 `high`,
> 4 `moderate`, 2 `low`. **No `critical`, so the D3 escalators are NOT
> exercised by this holdout** and the accuracy figure will say nothing about
> them — publish it with that denominator named, per disciplines §2/§3.
>
> Generate the blind packet without reading grades. **Run from the repo root.**
> The SHA is this file's own adding commit, resolved at run time rather than
> pasted, because four sessions rebase constantly and a pasted SHA names a
> commit that stops existing. **No temp file, deliberately** — the first draft
> of this block wrote to `/tmp` and it does not work here: Git Bash's `/tmp` is
> a virtual path Windows Python cannot open, so the snippet died on its own
> output. Verified working 2026-09-14, printing 12 rows.
>
> ```bash
> python - <<'PY'
> import json, io, subprocess
> RC = subprocess.check_output(['git', 'log', '--diff-filter=A', '-1', '--format=%H', '--',
>     'docs/2026-09-13-defect-severity-rubric-UNRATIFIED.md']).decode().strip()
> pick = lambda d: d['records'] if isinstance(d, dict) and 'records' in d else d
> old = pick(json.loads(subprocess.check_output(
>     ['git', 'show', '%s:docs/defect-density-register.json' % RC]).decode('utf-8')))
> new = pick(json.load(io.open('docs/defect-density-register.json', encoding='utf-8')))
> k = lambda x: (x.get('subject'), x.get('summary', '')[:60])
> seen = set(map(k, old))
> for i, x in enumerate([r for r in new if k(r) not in seen], 1):
>     print('%2d. %s\n' % (i, x.get('summary')))   # severity deliberately NOT printed
> PY
> ```
>
> **If it prints 0 rows, STOP — that is a broken differ, not an empty holdout.**
> The register only grows, so an empty result means the key stopped matching,
> which reads exactly like "nothing new to grade."
>
> **One honest wrinkle, stated rather than smoothed over.** The line below says
> the rubric was derived from **54** records; the register held **55** at this
> file's commit. The differ excludes everything present at the commit, so if
> that 55th record was added after the reading it is being wrongly excluded
> from the holdout. **The error therefore runs one way only — the holdout is a
> floor, never contaminated.** 12 is the number to publish; the true figure may
> be 13.
>
> Grade those 12 blind and record the grades **before** reading on. Records
> added after 2026-09-14 are a second, larger holdout for the month-later
> question this document already asks for.

Derived from all 54 records in `docs/defect-density-register.json` as of
2026-09-13. Nothing here is invented: every rule below is a reading of grades
this platform already assigned, and every place the reading fails is named.

---

## The rubric

Three questions, asked in this order. **Stop at the first one that answers.**

### D3 — Escalators. Any one of these and it is `critical`.

1. **A wrong or invented value reached PRODUCTION and touched a Tier A
   resource** — money, or regulated/protected data, as `docs/CRITICALITY-TIERS.md`
   defines Tier A.
2. **Fabricated data was presented as real.**
3. **A BLOCKING control was disabled or bypassed wholesale** — the mechanism,
   not one of its checks.

Both existing `critical` records satisfy these and nothing else does:

| Record | Which escalator |
|---|---|
| Lazy demo seeding wrote invented drug balances and invented vet names to the LIVE server, on the controlled-substance panel | 1 and 2 — Tier A regulated data, and the values were invented |
| The push gate disabled NINE of its ten checks when one unrelated tool was absent | 3 — and it is the **push gate**, which blocks |

**"Blocking" is load-bearing in escalator 3.** `report_only_checks.py` reporting
a clean platform after scanning zero apps is the same *shape* — a control saying
nothing was wrong about work it never looked at — and it is graded `high`, not
`critical`, because it refuses nothing. That distinction is the difference
between the two records and it has to stay explicit, or every reporting bug
becomes a `critical`.

### D1 — Did the wrong answer get acted on, **silently**?

**Both halves are required.**

- **Acted on:** a gate allowed something it should have refused; a record was
  lost, overwritten or written wrong; a report said `PASS`/`CLEAN`/`OK` about
  something it had not examined; a person was told an action succeeded when it
  had not.
- **Silently:** nothing louder was already saying the same thing. **A defect
  that announces itself is not this.**

**D1 = yes → `high`** (absent an escalator).

The silence half is not decoration — it is what separates `low` from `high` in
the records, and without it the rubric misgrades two of the four `low`s:

| Record | Acted on? | Silent? | Graded |
|---|---|---|---|
| `defect_register --check` ran its vocabulary validation after a `continue`, so an unresolvable-SHA record stopped having method, layer and severity checked | yes — it printed OK on fields it never checked | **no** — the unresolvable SHA is already reported loudly by the same command | `low` |
| A floor pinned to a post-classification count went red on a correctness improvement | no — it went **red**, wrongly, which is a false alarm and not a silent one | n/a | `low` |
| A mutation control anchored on a line two writers share verbatim, so it probed nothing | no — it reported `ANCHOR-2` rather than claiming green | n/a | `low` |

### D2 — Reach. Only asked when D1 is **no**.

- **WIDE** — every run, every app, every call site of a shared path, or a shared
  tool many things depend on → **`moderate`**.
- **NARROW** — one call site, one probe arm, one panel → **`low`**.

---

## The whole thing as a grid

| | | |
|---|---|---|
| **any D3 escalator** | → | **`critical`** |
| **D1 yes** (acted on, silently) | → | **`high`** |
| **D1 no, D2 wide** | → | **`moderate`** |
| **D1 no, D2 narrow** | → | **`low`** |

**The high/moderate boundary is D1 and D1 alone**, which is what makes it
seedable. The two records that show it are the same class of defect one tier
apart:

| Record | D1 | Graded |
|---|---|---|
| `key_collision_check.py` counted a line of prose as a storage-key write — 93 raw vs 92 comment-stripped — **with the verdict unchanged** | **no** — the number was wrong, the answer was not | `moderate` |
| `nav_panel_check` reported `RESULT:PASS` on two apps whose panel system it could not see — 32 containers invisible | **yes** — the PASS was the only signal | `high` |

---

## The crosswalk to `CRITICAL` / `WARNING` / `NOTE`

`.claude/skills/sairn-adversarial-reviewer/SKILL.md` grades on three levels and
the register wants four. **There is no clean 1:1 map and pretending otherwise is
what a crosswalk is for:**

| Skill | Register | Note |
|---|---|---|
| `CRITICAL` | `critical` **or** `high` | The skill's own definition — *"data loss, security breach, production outage, OR fabricated data presented as real"* — spans both. **A reviewer emitting `CRITICAL` must answer D3 explicitly to place it.** |
| `WARNING` | `moderate`, and `high` when D1 is yes | *"Likely to cause bugs in edge cases"* says nothing about whether anything acted on it |
| `NOTE` | `low` | The one clean correspondence |

### And the promotion rule has to change

The skill promotes a finding one severity level when 2+ personas flag it. **That
moves severity on agreement count, which is evidence about CONFIDENCE and not
about CONSEQUENCE.** Under it, an obvious cosmetic issue three personas all
notice outranks a subtle silent-failure one persona found — which is backwards
on every axis this rubric is built from.

**Recommendation for the ratifier to accept or reject: the promotion rule raises
CONFIDENCE, not SEVERITY.** Severity comes from D3/D1/D2 and from nothing else.
This is the single change in this document that alters existing behaviour, and
it is flagged rather than folded in quietly.

---

## What this rubric cannot do

- **It does not decide anything for Tier B and C resources at the escalator.**
  D3's first escalator names Tier A because that is what the two `critical`
  records are. A production defect on a Tier B resource has never happened here
  at `critical` severity, so the rubric has no evidence for it and does not
  guess.
- **"Wide" and "narrow" are not defined numerically** and deliberately so. The
  records use *"every"*, *"all fifteen"*, *"twelve of fifteen"* on one side and
  *"one call site"* on the other, with nothing in between; inventing a threshold
  would be a number with no evidence under it.
- **D1's silence test needs a judgement about what counts as "louder."** That is
  the residual ambiguity, and it is exactly where the B1 boundary seeds should
  be authored.

## Why there is no back-test, and what would count as one

**A back-test against the 54 records would be circular** — the rubric was read
off those grades, so agreement with them measures nothing but my own
consistency. No clean holdout exists, because I read all 54 before writing this.

> **2026-09-14 (fourth): this instruction is the one that matters most and it
> was positioned last, where a ratifier reaches it only after reading the whole
> rubric — at which point it can no longer be followed.** It is now repeated in
> the STOP box at the top, which is where it has to live. It is left here too
> rather than moved, so a reader who remembers it from the bottom still finds
> it. **The holdout it asks for exists now: 12 records, command in the STOP
> box.**

**What would validate it:** the ratifier grading a set of records blind, from
the summaries alone with the severities stripped, before reading this document —
then again after. Two numbers, per disciplines §2: agreement with the recorded
grade (accuracy) and agreement between their own two passes (stability). If the
second is low the rubric is not teachable, whatever the first says.

Records added **after** today are the real holdout, and they should be graded
with the rubric and the grade recorded, so the question can be asked properly in
a month.
