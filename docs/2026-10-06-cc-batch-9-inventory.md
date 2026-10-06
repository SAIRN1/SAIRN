# CC inventory — batch 9, 2026-10-06

Sixteen items. **Eleven landed, four routed because the file belongs to another
session, one refused on a boundary.** Everything routed is in
`docs/2026-10-06-cc-routed.md` with the exact edit and the measurement behind it.

---

## 0. Premise log — the brief against HEAD, item by item

Written first, because three of these were wrong and one item was already done.

| # | premise in the brief | at HEAD |
|---|---|---|
| 1 | row 95's count is 10 instances, 6 routed / 4 unrouted | **HELD on the ten, and the row disagrees with itself** — title says six, detail enumerates five then appends a sixth, and a seventh lives in a separate row |
| 2 | the index needs rows for seq 544/545/538, #892, dnt_supplies, metamorphic | **TWO ARE ALREADY CLOSED BY ME** (545 and metamorphic, this batch) and **#892's CLAIM IS FALSE** — see below |
| 3 | `metamorphic_check` exits 1 on `fmea/alf_facility_role_gate_live_probe.py` | **HELD, and the path is wrong** — the file is `tools/alf_facility_role_gate_live_probe.py`; `fmea/` is the metamorphic SUBJECT name, not a directory |
| 4 | `sairnbiz_vendor_ytd_derivation.js` is red, my sb_ap work may resolve it | **HELD, AND MY WORK CAUSED HALF OF IT** — two independent failures, one mine, one older than my work |
| 5 | 12 red suites | **NOT CONFIRMED AS TWELVE.** I fixed four red artefacts and did not enumerate a twelve-member set — see §5 |
| 6 | at least 3 obligations owed to cc | **NINE**, not three |
| 7 | `dnt_supplies` unit_cost × qty is summed into a displayed total | **HELD EXACTLY** — `sairndental.html:6790`, rendered at `:6794` |
| 8 | `hashLicense` has no case normalisation, ~40 call sites | **HELD** |
| 9 | 2 of my drifts, 7 others | **FIVE ARE MINE, TWO ARE NOT** |
| 10 | the push gate has fourth's literal-match false positive | **HELD, and it fails CLOSED where fourth's failed OPEN** |
| 11 | evaluate a tokenized parse, build if every arm survives | **EVERY ARM SURVIVES AND IT IS STILL NOT BETTER** — see §11 |
| 13 | `report_only_checks.py` is cody's | **RELEASED, and cody's claim names it as mine explicitly** |
| 14 | wire `tools/hover_tip_beacon.py --check --max-lag N` | **THE PATH DOES NOT EXIST AND NEITHER DOES THE FLAG** — see §14 |

---

## 1. The Tier A gate stops matching prose comments · `fa2aebf7`

Open-work row 95. `strip_diff_noise()` blanked prose STRING bodies and
deliberately counted COMMENT text, so writing a sentence about a Tier A resource
registered the author as changing code that serves it.

**THE OLD DECISION WAS DEFENSIBLE AND ITS COST RAN ONE WAY**, which is why ten
accumulated: each false demand opens a real obligation costing a reviewer a full
read, and complying is always cheaper than fixing. The old argument — *"a hunk
that discusses sc_claims was edited by somebody thinking about sc_claims"* — is an
argument for REPORTING, not BLOCKING, which is the distinction
`context_only_tier_a()` already draws for hunk context.

Same threshold as the prose rule: three or more whitespace-separated words.
Marker chosen by EXTENSION, and with no path it blanks **nothing** — a wrong guess
makes the gate go quiet, which the docstring already names as the worse failure.
Character walk, not a regex.

**THE TEN, DRIVEN BEFORE AND AFTER: 5 STOP · 2 STILL MATCH · 3 COULD NOT TELL.**
The two survivors are multi-line docstring interiors (no quote, no `#` on the
line) and, for one, bare fixture literals that no string analysis can separate
from a handler. Both named in the docstring rather than left to be rediscovered.

**ONE COMMIT-LEVEL FLIP IN THE WHOLE REGISTER**, `f07d8660` BLOCKED→CLEAN, and it
was hand-verified three independent ways rather than accepted.

**THE PROBE ARM THAT GUARDED THIS WAS A TIME BOMB AND IT WAS NOT ABOUT COMMENTS.**
Its fixture resource was `sorted(_res)[0]` = `alf_activities`, and somebody opened
an obligation covering it on 2026-09-29. `check()` then returns 0 for the CORRECT
reason, so the arm would have gone red for a reason unrelated to its subject. The
fixture resource is now DERIVED as one no open obligation covers, and with no such
resource the arm says COULD NOT RUN rather than passing.

4 behaviour arms + 6 sabotage/ablation arms. Per-arm ablation: invocation position
catches 2 alone, the suppression catches 6, the tightening 2.

## 2. `tests/sairnbiz_vendor_ytd_derivation.js` · exit 1 → 0, 18 passed

Red for **two independent reasons** and only one was mine. (a) The anchor
`sbVendorPaidUndatedPriorYear` — my rename, and the `notStrictEqual(-1)` guard
doing exactly its job. (b) `/spendOf\(x\)<600&&…>=600/` — **not mine, and red
before my work went near it**: the code reads `thr.amount`, which is the correct
shape, so the arm was red while the code was right.

Both re-pointed rather than relaxed, and (b) strengthened in the direction the old
arm had backwards: the literal 600 must now be **absent**. The partition arm goes
from three buckets to four and checks **every pair**.

## 3. `fmea_draft.py` · a metamorphic violation and a horoscope · `fa2aebf7`

(a) `\bCLEAN\b` is case-sensitive and matched the English word `clean` once a
comment was upper-cased. **Culprit named by elimination over all six
alternatives**, not guessed. Rewording the subject file rejected as slipping past
the matcher; `re.I` rejected on a measurement (197 matches across 296 files). The
detector is made blind to full-line comment text. Cost named: 96 files still fire,
**exactly 3** lose their verdict.

(b) Rule 1.7 fired on **44.6%** of 691 files and `run_fmea_probe` arm 3b was RED
ON MAIN — confirmed identical at origin/main. Measured per half: the bare `[:NNN]`
slice was **307 of 308** hits and **every one inspected is a display truncation in
a message**. The slice half caught zero genuine instances. Dropped, named half
widened, **14/691 = 2.0%**, all fourteen hand-checked as real bounds.

Five new local arms assert the relation in BOTH case directions, with a
not-vacuous arm requiring the subject to still contain the word that caused it.

## 4. Nine Tier A obligations discharged — all of them

**ZERO now owed to cc.** Each driven with a control per attack point. The full
verdicts are in the register; the findings worth carrying:

* **hover_routing_gap_check** — a FOURTH and a FIFTH vacuous-sweep state, both
  reachable: a renamed `routable` field, and an unparseable `ts` which makes
  `too_old` false with no trace. The fifth I found **only because my own fixture
  was wrong first**.
* **sairn_claim disclosure rule** — a LIVE FALSE-CLEAR, **wider than the author
  stated**: a marker in the same clause as the `FILES:` list exempts EVERY
  declared path, not just the one named.
* **citation_line_drift_check** — `:2414` is `['sf_lic','sf_jobs','sf_settings'].every(...)`,
  a membership test excluded as a declaration block; and the 40-line window sits
  at the **median** of the nearest-write distribution (min 0, median 44, max 3471),
  the least stable place to put a threshold.
* **schema_provisioning_check** — both enumerations he owed, done: all 17
  registries return non-empty, and all **ten** live uses of the prefix strip are
  the intended mapping, so the feared orphan resolution does not reproduce.
* **sf_trustee_audits** — the key column matches a unique schema column, and 17 of
  17 sf_ resources are gated read+write, so the gate decision was never novel. And
  **the review gate cannot name the subject of a change that introduces a
  resource** — the inverse of row 95, and the more dangerous half.
* **the consent/day-zero/leap-day trio** — all three claims true; the leap-day
  permissive direction quantified at **exactly one day** (93 vs 92); and the
  day-zero branch reaches **every** customer via `DEFAULT_ANNUAL_WINDOW` while the
  existing suite feeds a shape that **cannot reach it**.
* **the reseat gate** — SUPERSET is right, and the real argument is an asymmetry
  neither of us had written: a SUPERSET twin can only be wrong by being too broad
  and still contains the work; a PARTIAL twin is positive evidence that record and
  commit disagree.

**AND FIVE OF MY OWN FIXTURES WERE WRONG BEFORE ANY OF IT REPRODUCED** — an
invented rule object, an object where a string was wanted, the wrong staff field,
a rule whose `null` came from a different cause entirely, and `date` for
`completed_on`. **Every one would have been a confident, specific, false finding
against somebody else's work.** The only reason none reached a verdict is that the
arms require a POSITIVE result rather than a non-empty one, so a vacuous pass
fails.

## 5. Red artefacts fixed — four, and I am not claiming twelve

The brief says twelve red suites. **I did not enumerate a twelve-member set and I
am not going to imply I did.** What I fixed, each confirmed red before and green
after:

| artefact | was | now |
|---|---|---|
| `tests/sairnbiz_vendor_ytd_derivation.js` | exit 1, 2 distinct failures | exit 0, 18 passed |
| `tests/run_fmea_probe.py` | exit 1, arm 3b (red on main) | exit 0, 0 failed |
| `tests/claims/run_fileset_matcher_probe.py` | exit 1, 3 failures | exit 0 |
| `tools/mutation_anchor_check.py` | exit 2 (2 bad anchors, 5 unreadable) | exit 0, 533 checked |
| `tests/run_mutation_anchor_resolver_probe.py` | exit 1 after the above | exit 0 |

**ROUTED, NOT FIXED:** `tests/run_tier_a_review_gate_sabotage_probe.py` exits **3
COULD NOT RUN** in a detached worktree — the session identity cannot be carried
in, so nothing is verified. Confirmed identical at origin/main. It needs
`sairn_session_identity.py --provision` in the worktree path, which is a harness
change rather than a suite fix.

## 6–9, 13 — see the commits

* **`sairn_push_gate_hook.py`** refused prose about a push. **The rule was already
  in the file sixty lines down**; the push detection had half of it. Heredoc bodies
  added as spans after the ablation showed the quoted-span layer catching **zero**
  — a layer catching zero is redundant or looking at the wrong thing. Pre-fix rule:
  **10 of 20 arms wrong**.
* **`exit_status_attributable`** — five FP classes, **none found by reading**. A
  tokenised parse agreed on all 23 arms and then refused an unmatched double quote,
  so it is a **cross-check** and not a replacement; every subject arm is decided
  twice by implementations sharing no code.
* **`hashLicense`** — case normalised at LOOKUP, exact-first-and-always, hash
  follows the key that matched. 21 recorded keys, all uppercase. **A looser first
  measurement would have decided it backwards.**
* **hook manifest** — regenerated, all 9 changes named. **Five were mine, not two**:
  `.githooks/pre-commit`, `cron_beat_refusal_check.py`,
  `exit_status_attributable.py`, `report_only_checks.py`, `sairn_push_gate_hook.py`.
  Not mine: `deploy_verify_notify.py` (fourth's blind-deploy sweep) and
  `register_feed_gate.py` (hank's sairncash batch) — both COMMITTED on origin/main
  with their own commit messages, which is why blessing their hashes is different
  from blessing an in-flight edit.
* **E2** — closed at the **INTAKE**, not just the backlog. The five entries got
  `evidence` from a REAL RUN each (PR §2.7), and the registry now **raises at
  import** on an undocumented entry, naming the tool and the missing field. It
  raises rather than warns because a suite tells you after the entry is on main,
  which is how five accumulated. Driven with a planted entry.

## 14 — the one refusal

`tools/hover_tip_beacon.py` does not exist; the file is in the auditor's scope.
There is no `--max-lag` flag — staleness is `STALE_AFTER_ENTRIES = 15`. And wiring
it into the build-side chain is a build agent arming the auditor's gate, which
CLAUDE.md forbids in those words.

**What I could do, I did, read-only:** `--selftest` writes only to a tempfile
scratch dir, so running it touches nothing there — confirmed with `git status` on
that path afterwards. **13 arms, 0 failed**, and it already covers both the FRESH
and STALE cases the request names, plus MISMATCH and two COULD-NOT-RUN states.
Routed to hover.

---

## Methodology — the three conventions, and why each was paid for

Routed to fourth for `docs/METHODOLOGY.md`; stated here because this is the batch
that bought them.

**(a) A brief's premises are verified before execution, with a per-premise result
recorded.** Of eight premises, three were wrong about WHERE or WHETHER and one
item was already done. A brief is the least trustworthy document in the repo
because it is the most recent — and when it is your own prior report it carries
your own blind spots forward at full confidence. The table at the top of this file
is the artefact the convention asks for.

**(b) A hook or checker leg that returns success on a failed leg is a silent skip
and must fail loud.** Three instances this batch. The rule: every leg reports its
own outcome and NAMES what it could not read; only a total blackout is silence.

**(c) When one checker produces three or more false-positive classes from its own
author's commands, stop patching and review the design.**
`exit_status_attributable` reached five, and the fifth revealed the defect was
never in the subject half — the same raw-text split was wrong in the ATTRIBUTION
half for every command carrying a quoted separator. Four patches had each fixed a
symptom. Asking the design question at five produced a better answer than another
patch would have.

---

## BLIND SPOTS — 7

1. **I did not enumerate the twelve red suites.** I fixed four red artefacts I met
   and routed one. A full-tree suite drive is fourth's claimed work this batch and
   I did not duplicate it, so "how many are red" is still unmeasured by me.
2. **Three of row 95's ten are COULD NOT TELL** because `opened_at_sha` is HEAD at
   open time rather than the diff the gate judged. That is a defect in the record
   shape and nothing here fixes it.
3. **The two surviving instances need an `ast`-based line-number map** and I did
   not build it. Named in the docstring, which is the next best thing and not the
   same thing.
4. **`seq 538`'s twelve SDN resources are not verified by me.** I wrote the method
   and declined to write the row.
5. **Nothing I landed was verified against the deployment.** The licence-case
   change in particular is a transport-level behaviour change tested only against
   a stubbed `fetch`; a live drive with a lower-case key is owed.
6. **The import-time registry refusal is a new way to break every importer.** It
   is deliberate and I believe it is right, but the first person it stops will be
   stopped hard, and I have not measured how that feels in a hook.
7. **`dnt_supplies` is re-tiered in a routed document, not in the register**, so
   until hank lands it the resource is still B/B and the Tier A obligation it
   wants cannot even be opened — the gate derives its resource list from the row
   that does not yet say A.
