# Five follow-ups — and the sharpest finding is a correction to my own tool

**2026-09-15 (CC).** Direct follow-ups from the seven-item sweep
(`docs/2026-09-15-seven-item-sweep.md`) plus item 79.

---

## 1. Why the untraced count grows while the ratio improves

**Root cause, measured:** `traced()` has two citing sources, and **243 of 248
citations come from one of them** — an open-work index row naming a test file.
`GUARD_TESTS` supplies 5. So the traced figure moves with **how diligently the
index is written**, not with how well tested the repo is.

Meanwhile **120 of the 213 untraced files are `*.test.js` sitting beside the
module they test**. That is the strongest subject binding this repo has — the
filename names its subject — and `traced()` cannot see it, because a SUBJECT is
not a REQUIREMENT.

### The fix is NOT to widen the definition, and that is the whole point

Counting `foo.test.js` beside `foo.js` as traced would move **55 files** into
the traced column overnight with **not one more requirement written down
anywhere**. That is the same measure-gaming the section was rewritten to stop.
So instead:

- **The absolute count is now the headline** and the ratio is below it, with the
  divergence stated in the document itself. A ratio improves when traced work is
  added; only the count falls when the gap actually closes.
- **The citation concentration is reported** — one source carrying 243 of 248 is
  a single point of failure for the number, and nothing said so before.
- **The untraced are split into two kinds** because they need different fixes:
  **55 bound to a subject but tied to no requirement** (an auditor can see WHAT
  it covers, not WHY that coverage is required) and **158 with no binding at
  all**.

**What is NOT done:** the count itself has not been reduced. 213 test files
still state no requirement, and closing that is 213 judgements about what each
one is for — not something to bulk-generate, which would produce 213 rows saying
nothing.

---

## 2. Compromise procedures for the five most exposed identities

`supabase-service-role`, `sairn_backup_reader`, `anthropic-api`,
`session-signing`, `sairncash-firebase-admin` — the set where neither rotation
nor scope was doing anything. Each now carries a **`compromise` field** in
`tools/nhi_register.py`, rendered into `docs/NHI-REGISTER.md`, with four parts:
**revoke** (where and how), **blast while compromised**, **what breaks during**,
and **the human decision this does not make**.

**The sharpest one is `session-signing`, and it is sharp because the containment
IS the disruption.** One secret signs every app's employee sessions with no
overlap window, so rotating logs everyone out of everything at once, mid-shift,
including whoever is handling the incident. **That dilemma is exactly why it
needs deciding in advance rather than during** — and the procedure says the
build that would remove it (an overlap window) rather than pretending a
procedure solves it.

**DRAFTED, NOT REHEARSED, AND NOT VERIFIED**, on every one of them. The blast
and what-breaks halves are derived from the register and the repo; **the console
steps are not verified, because no clone holds these credentials or that
access.** A runbook nobody has walked through is a draft.

**And a procedure is a THIRD control that fixes neither of the first two.** It
tells you what to do after. The five are still in the broad-and-unrotated list
for exactly that reason, and both the tool and the register say so.

`rotation_blast_radius.py` is now `.3`. **The TRIGGER column went 0 → 5, which
is the direction that needs scrutiny**, so the code says why: the figure
improved because procedures were **written**, not because the test was loosened,
and a fixture proves an empty or thin field still does not count.

---

## 3. The 83 untested claims — and the tool was wrong about five of them

**TIER, by the question this platform tiers on: the worst consequence of the
tool being WRONG.**

| artefact | claims | state | tier |
|---|---|---|---|
| `sc_tier_a_write_gate_live_probe.py` | 7 | **nothing** | **A** — writes and DELETES on the production demo tenant |
| `guard_ablation.py` | 18 | **nothing** | **A** — removes a security gate from a tracked file |
| `sabotage.py` | 11 | self-test, **unwired** | **A** — plants a defect in a tracked file |
| `line_endings.py` | 13 | self-test, **unwired** | **A** — rewrites the bytes of tracked files |
| `nhi_register.py` | 9 | self-test, **unwired** | **A** — writes a governance document, and refuses |
| `accepted_risk_expiry_audit.py` | 16 | self-test, **unwired** | B — report only |
| `ai_action_approval_audit.py` | 9 | self-test, **unwired** | B — report only |

### The correction: unverified and unwired are different states

**`first_article_inspection.py` reported all seven as having NO SUITE AT ALL.
That was wrong about five.** They carry working `--selftest` entry points, **48
arms between them**, that `run_all_tests.py` never invokes — it discovers
`tests/**` and `*.test.js`, and a self-test lives inside the tool.

**This is the third time this tool mistook its own blind spot for a fact about
somebody else's work** (after the hardcoded arm helper and the top-anchored
docstring regex). It now reports UNWIRED as its own state, and the corrected
figure is **2 artefacts with nothing, 25 claims** — not 7 and 83.

### What was done

- **`tests/run_selftest_sweep_probe.py`** — discovers every `tools/*.py` that
  declares a self-test flag and RUNS it. Six found, all green. **A control in a
  drawer is not a control.** It captures `git status --porcelain` before and
  after and fails on any difference, which is what makes it safe to run tools
  that plant defects and rewrite bytes.
  - **It enrolled `first_article_inspection.py` on its first run**, because that
    file's source contains the string `--self-check` inside a regex it uses to
    detect *other* tools' self-tests. The detector now requires the flag to be
    compared against `argv`.
- **`tests/run_guard_ablation_probe.py`** — Tier A, 30 arms. Drives the gate
  regex in both directions, proves the real subject contains **duplicate gate
  lines** (the tool's own documented reason for ablating by line number rather
  than by textual replace), verifies each derived line index really is the gate,
  and asserts the tree is untouched. **It does not run the ablation** — that
  builds a worktree and executes every suite — and says so.

**STILL OPEN:** `sc_tier_a_write_gate_live_probe.py` has no suite and its
subject is a production write path; an offline suite can only cover its argument
handling. **Three Tier A artefacts (`sabotage`, `line_endings`, `nhi_register`)
now RUN but only via their own self-tests, which are not independent of their
subjects** — disciplines section 5. That is better than a drawer and worse than
an outside probe, and it is not closed.

---

## 4. AR-1's trigger: both halves, and only one of them is fixable here

**The register said MECHANICAL and named `api/_lib/stripe-config.js`.** True
about the module, false about the platform: nothing consumes the signal. It goes
to a log, and it is **log-only by design** — the client message deliberately
names no variable — so there is nothing for a checker in this repo to read.
**That is correct behaviour, not a gap to close.**

**The half that WAS fixable, and it was worse than the reported problem:** the
module had **no suite at all**. The branch producing AR-1's trigger could have
been edited away with the only consequence being that an accepted risk's trigger
quietly stopped existing — while the register still said it was monitored.

- **`api/_lib/stripe-config.test.js`**, 19 assertions, added to **`GUARD_TESTS`**
  so it can block a push. The load-bearing arm is the four-cell control: of
  (test key, live key) × (production, preview) **exactly one must warn**, because
  AR-1's trigger reads the ABSENCE of that warning and a banner that fires
  everywhere has no absence.
- **AR-1 rewritten** to state the two halves it really has: GUARDED/MECHANICAL
  for the producer, **NOT WATCHED** for whether a live key has actually been
  installed — which needs a live environment read and is Michael's call.
- **`tools/accepted_risk_trigger_check.py`** — the mechanical half of item 53's
  checker, split out as its own promotable tool exactly as that tool's
  NOT_PROMOTED entry said it should be. It imports `weakness_combination`'s
  functions rather than re-implementing them, so the two cannot disagree about
  what the register says.

**One rule was widened, deliberately:** a mechanism is watched when a runner
names **the suite that guards it**, not only when a runner names the module.
Requiring the module itself would report a genuinely guarded mechanism as
unwatched. Four fixtures hold that in both directions, and the tool says plainly
that **a suite is not a consumer** — this answers "is anything holding this
mechanism", not "does anything read its signal".

---

## 5. Item 79 — the reviewer judges first, then sees the score

**`tools/blind_review.py`.** The mitigation is an ORDERING, not a warning:
telling people not to anchor does not work, withholding the number until their
judgment is recorded does.

- **`--start N`** writes a worksheet of **evidence only** — subject, summary,
  files, commit, layer — with the recorded severity removed, and seals the
  answers in a file the worksheet never names.
- **`--submit`** takes the reviewer's severities, **then** reveals.

**Every judgment must carry a DEFEATER: what would have to be true for that
severity to be WRONG.** Free text, refused below a substance floor. Without it
the reviewer has not judged, and the reveal re-anchors them for the next item
anyway — which is the friction half the item asks for, included because an
accept with no engagement makes the ordering worthless.

### The first real round: 3 of 6 agree

| | your severity | recorded |
|---|---|---|
| R01 stamp failure loses the save, 3 apps | high | high |
| R02 tripwire died in a snapshot re-capture | moderate | **low** |
| R03 43 writes, no timeout, "Point captured" announced anyway | **high** | moderate |
| R04 fail-open in the blocking push gate | high | high |
| R05 report_only_checks reported clean after scanning zero apps | high | high |
| R06 sabotage detector over-counted, 19 was really 8 | **low** | moderate |

**R03 is the disagreement worth reading.** A write that never reached the server
was announced to the user as captured — the silent-failure-showing-false-success
class this platform calls its worst — recorded as `moderate`.

**A disagreement is not an error.** The recorded severity is not ground truth
and neither is the reviewer's. What the round produces is an agreement rate
measured under a **blind** ordering, which is the only kind that means anything.

### What one round does NOT measure

**Nothing about automation bias.** The experiment is this number against the
same reviewers under a **score-first** ordering, and **that second arm does not
exist**. Until it does, 3-of-6 is a blind agreement rate and not an effect size.

### The ceiling, printed on every round

**Nothing stops a reviewer opening the sealed file.** What is mechanical: the
worksheet is scanned for every withheld value and the round is REFUSED if one
appears; the sealed file lives at a path the worksheet never names and is
gitignored; a submission modified before the round started is refused. What is
not: the reading order itself. The control is that breaking it is a deliberate
act with a name rather than the default.

**The first fixture run refused its own worksheet**, because the preamble names
the whole vocabulary and therefore contains every possible answer. Naming the
LIST is not the anchor; naming which one APPLIES is. The scan runs on the body,
and a fixture proves an answer inside a record's own evidence is still caught.

---

## What this does NOT claim

- **No live credential, console or environment was touched.** Every compromise
  procedure is drafted from the register and the repo.
- **No claim-to-arm mapping was performed.** The tier table above is about
  consequence-if-wrong, not about coverage adequacy.
- **The blind round was judged by one reviewer, in one ordering, on six
  records.** It demonstrates the flow and produces one number; it is not a study.
- **Three Tier A artefacts are covered only by their own self-tests**, which are
  not independent of their subjects. Item 3 is not closed.
