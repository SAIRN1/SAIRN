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

**What would validate it:** the ratifier grading a set of records blind, from
the summaries alone with the severities stripped, before reading this document —
then again after. Two numbers, per disciplines §2: agreement with the recorded
grade (accuracy) and agreement between their own two passes (stability). If the
second is low the rubric is not teachable, whatever the first says.

Records added **after** today are the real holdout, and they should be graded
with the rubric and the grade recorded, so the question can be asked properly in
a month.
