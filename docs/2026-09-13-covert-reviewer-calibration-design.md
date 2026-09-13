# Covert reviewer calibration — boundary-case seeding, design only

**2026-09-13 (Hank).** Item 25, scoped to a design and stopped there. Nothing is
seeded, no reviewer has been tested, and no tool is built.

Unblocked by item 2/24 landing. Item 2/24 asked *"were these reviews
independent"* and its detection-rate half is blocked because the input was never
captured. **This is a different question with a different failure mode**, and it
is worth saying up front so the two are not merged later: item 2/24 measures
whether a defect was FOUND. This measures whether a defect that was found was
GRADED correctly — and whether the same reviewer grades it the same way twice.

Disciplines applied: **§1 blind lock**, **§2 two numbers**, **§3 named
uncertainty table**, **§5 the deep check runs with its subject not trusted**.
Each is cited where it changes the design rather than listed at the end.

---

## 1. The blocking finding: there is no severity rubric to sit at the edge of

The brief is to seed defects *"deliberately at the edge between two severity
tiers."* **That edge has never been drawn.** Three severity vocabularies exist
on this platform and none of them defines a boundary:

| Where | Scale | What defines the boundaries |
|---|---|---|
| `docs/defect-density-register.json` (54 records) | `critical` / `high` / `moderate` / `low` | **Nothing.** `tools/defect_register.py:47` is a tuple, and line 222 validates membership in it. That is the entire specification |
| `.claude/skills/sairn-adversarial-reviewer/SKILL.md` | `CRITICAL` / `WARNING` / `NOTE` | One sentence each, plus a promotion rule: a finding flagged by 2+ personas moves up one level |
| `docs/CRITICALITY-TIERS.md` | `A` / `B` / `C` | Well defined — but it tiers **resources**, not defects, and it is a different axis |

So a reviewer running the adversarial skill emits `WARNING`; the register wants
`high` or `moderate`; **nothing anywhere says which**, and the promotion rule
means the same defect can come out one level apart depending on how many
personas happened to flag it. `CRITICALITY-TIERS.md` opens by insisting on *"one
scheme, not two"* with the SOUP register — which is true of those two and makes
this the third.

**A boundary case cannot be authored against a boundary that does not exist.**
The rubric is therefore the first deliverable, ahead of any seed.

---

## 2. I tried to derive the boundary from the 54 records. It does not derive.

Reported as a **negative result**, because a locator that fails is evidence and
suppressing it would leave the next session to repeat it.

Two crude signals were scored over every record's summary, with the criteria
locked against four fixtures before the register was opened (§1):

- **O — outcome-changing:** something acted on the wrong answer (a gate allowed
  a push, a record was lost, a checker printed `PASS`), rather than the error
  being confined to a report whose verdict was unchanged.
- **S — wide reach:** every run, every app, platform-wide — rather than one call
  site or one probe arm.

| Severity | O=T S=T | O=T S=F | O=F S=T | O=F S=F | n |
|---|---|---|---|---|---|
| critical | 0 | 1 | 0 | 1 | 2 |
| **high** | 3 | 8 | 5 | **9** | 25 |
| **moderate** | 2 | 4 | 6 | **11** | 23 |
| low | 0 | 2 | 0 | 2 | 4 |

**The proxy does not separate high from moderate**, and the way it fails is the
useful part: **9 of 25 `high` records carry neither signal**, including *"A
dropped socket produced NO toast at all"*, *"A hung server backup was completely
silent"*, and *"43 server writes with no timeout on any path."* Those are
textbook outcome-changing silent failures; my regex simply did not contain the
words they happened to use. The locator mostly located its own blind spots.

**What that rules out:** deriving the rubric mechanically from the existing
labels. **What it does not rule out:** the boundary being real — 48 of 54
records sit in the two crowded tiers, and both tiers contain the same shapes (a
checker that miscounts; a write path with no timeout). The separation is a
judgement nobody has written down, which is exactly the condition calibration
exists for.

**This locator is not a classifier and must never be reported as one.** It has
no accuracy figure attached and will not be given one; a keyword count dressed
as an accuracy number is the fabrication this platform has already paid for.

---

## 3. Where the boundary actually is, read by hand

Reading all 54, two discriminators appear to be carrying the grade:

- **D1 — did anything act on it?** A gate allowed a push it should have refused;
  a saved record was lost; a verdict was printed as `PASS`. Versus: the number in
  a report was wrong **and the verdict was unchanged**.
- **D2 — reach.** Every run / every app, versus one site / one arm.

The clean cases are where D1 and D2 agree. The boundary is where they disagree,
and two records make it visible because they are the *same class of defect*:

| Record | D1 | D2 | Graded |
|---|---|---|---|
| `key_collision_check.py` counted a line of prose as a storage-key write — 93 raw vs 92 comment-stripped — **with the verdict unchanged** | no | no | **moderate** |
| `nav_panel_check` reported `RESULT:PASS` on two apps whose panel system it could not see — 32 containers invisible | **yes** | no | **high** |

Both are *"a checker saw the wrong thing."* They land a tier apart on **D1
alone**. That single question is the high/moderate boundary as this platform has
actually been applying it, and writing it down is Phase 0.

---

## 4. The seeding design

### 4.1 What a boundary seed is

A defect authored so that **D1 and D2 point in opposite directions**, or so that
D1's answer depends on a fact the reviewer has to go and check. Three families:

- **B1 — `high | moderate`.** A miscount that does not change today's verdict,
  but is platform-wide and one ordinary commit away from changing it. (D1 says
  moderate today; D2 and the near future say high.)
- **B2 — `moderate | low`.** A real defect at exactly one call site, on a Tier C
  resource, where nothing downstream reads the wrong value yet.
- **B3 — `critical | high`.** A fail-open in a gate that is currently
  unreachable because a second gate catches the same case first — and becomes
  reachable the day that second gate moves. This family is the sharpest, because
  the platform has already had the real version of it twice.

Each seed carries a **sealed intended grade plus the reasoning that produced
it**, written and committed *before any reviewer sees the seed* (§1). The seal
is the calibration's own blind lock: without it, a disputed grade gets
retrofitted to whatever the reviewer said.

### 4.2 Two numbers, never one (§2)

- **ACCURACY** — the fraction of seeds graded at the sealed grade.
- **STABILITY** — the fraction of seeds graded *the same way* when re-presented
  at least one session later, **whether or not that grade was right**.

They cannot be collapsed. A reviewer who is consistently one tier low has a
rubric problem that is fixable in an afternoon. A reviewer who is right half the
time and differently right on a re-run is not calibrated at all, and a single
"50%" would read identically for both. **And B-family seeds are ambiguous by
construction**, so low accuracy on them is not automatically a reviewer failure
— which is what the next section exists to keep honest.

### 4.3 The named uncertainty table, published before results (§3)

One row per seed, published when the seed is sealed and not after:

| Seed | Family | Sealed grade | The single discriminator it turns on | Why it is genuinely ambiguous |
|---|---|---|---|---|

**A seed whose ambiguity was not declared in advance cannot be counted as a
boundary case afterwards.** Without that rule every miss gets reclassified as
*"well, that one was a boundary case"* and the accuracy number becomes
unfalsifiable — the same shape as a risk scorer grading its own false positives.

And the corollary this repo already applies: **print the denominator.** With
three families and a handful of reviewers the cell counts are tiny. No
percentage goes out without the `n` beside it.

### 4.4 The seeder must prove its seed landed — tonight's lesson, applied before the code exists

This tool is **structurally the same tool as the sabotage controls**, and 21 of
37 of those never verify their own sabotage applied. The failure is
`src.replace(anchor, …)` silently doing nothing when the anchor rots, after
which the probe runs against an unmodified file and reports green forever.

Non-negotiable, from the first commit rather than retrofitted:

1. **Landed proof** — assert the file's bytes changed, and read the seed back
   out of the file rather than trusting the return value of the edit.
2. **Removal proof** — after the exercise, the file is byte-identical to its
   pre-seed state. **Compared after `tr -d '\r'`**: a CRLF-vs-LF difference is
   not drift, and that mistake produced three false alarms in one session on
   2026-09-03.
3. **Could-not-tell is a third state.** A seeder that cannot confirm either
   proof says so and fails; it never rounds to "seeded" or to "clean".

### 4.5 Blast radius — structural, not procedural

Seeded defects are deliberately-planted bugs. The containment must be a property
of the mechanism, not a rule someone remembers:

- Seeds exist only in a **throwaway clone or worktree**, never in a session's
  working clone.
- What a reviewer receives is a **review packet — a diff** — not a branch anyone
  can push. There is no ref for a seed to travel on.
- **No seed carries a real credential, a real customer record, or a real SQL
  write.** A seeded fail-open must be in a fixture gate, not in the push gate.
- **`defect_register.py --check` must REFUSE a record carrying `seeded: true`.**
  A seeded defect is not a confirmed defect; ingesting one inflates the density
  and corrupts the very register the rubric was derived from. This is the one
  change to an existing tool that the programme requires, and it should land
  **before** the first seed exists, not alongside it.

### 4.6 The subject does not grade itself (§5)

The rubric in Phase 0 cannot be written by me and then used by me to grade other
sessions — that is the deep check trusting its own subject. Phase 0's output
needs ratification by Michael or by a second session that did not write it,
before any seed is sealed against it.

---

## 5. What this programme cannot measure — written down before anyone quotes it

**It is not capture-recapture and must never be used as such.** Seeded-defect
detection rates are conventionally used to estimate the total defect population:
if reviewers find 6 of 10 seeds, the unseeded findings are scaled by 10/6. That
inference needs the seeds to be **representative** of real defects. **B-family
seeds are deliberately unrepresentative** — they are authored to sit on the
boundary, which is the least typical place a defect can be. Any population
estimate built on them would be wrong in an unknown direction.

The tool must print that in its own output, beside the numbers, in the shape the
FMEA prediction check already uses (`DO NOT QUOTE THIS ALONE`).

Also outside its reach: whether a reviewer would have *found* the defect
unprompted. A review packet hands the defect over. Detection is item 2/24's
question and remains blocked on `detection_method`.

---

## 6. Phases and size

| Phase | What | Size | Gate |
|---|---|---|---|
| **0** | The rubric: D1 and D2 written as one page, plus a crosswalk from the skill's 3-level scale to the register's 4-level one | **S** | **Ratified by someone who did not write it** (§5). Nothing else may start |
| **1** | Seal 9 seeds (3 per family) + publish the uncertainty table | **S** | Table published before any reviewer sees a seed |
| **2** | The seeder: landed proof, removal proof, review-packet mechanism, `seeded:true` refusal in `defect_register.py` | **M** | The `--check` refusal lands first |
| **3** | Scoring: accuracy and stability as two numbers, denominators printed, the not-capture-recapture warning in the output | **S** | — |

Phase 0 is the whole critical path. Phases 1–3 are cheap and mechanical once the
boundary is a written sentence instead of an intuition.

---

## 7. The open decision

**Who is covert to whom.** The reviewers on this platform are the other Claude
sessions and Michael. Seeding unannounced defects into packets reviewed by the
sessions raises nothing. **Michael is a different question and I am not deciding
it.** There is also a second-order effect worth naming: once a covert programme
is known to exist, it changes behaviour on *every* review, not only seeded ones
— a reviewer asking *"is this one of the planted ones"* is reviewing
differently. That effect is real whichever way the decision goes; the choice is
whether it is paid for knowingly.

---

## 8. What this document does NOT claim

- **No rubric is asserted.** §3's two discriminators are a reading of 54
  records, offered as the input to Phase 0, not as the answer.
- **The cross-tab in §2 is a failed locator**, reported so it is not rebuilt. It
  has no accuracy figure and will not be given one.
- **No seed exists**, no reviewer has been tested, and no tool has been written.
- **The 54 records are the whole evidence base**, and the register starts
  2026-09-09 and is deliberately not backfilled — so this reads the platform's
  last four days of judgement, not its history.
