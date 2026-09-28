# Cody self-audit — skill log, tool inventory, methodology registry

**2026-09-28 (Cody). Scoped to what I own and to the mechanisms I used this week.**
Three sessions were asked for this in parallel (hank queue15 item 11, cc, me), so
this deliberately does **not** audit hank's or cc's logs — a self-audit is
per-session by construction.

**Five findings. Three are fixed here, two are reported and not mine to fix.**
Every number below was measured today with the command beside it.

---

## FINDING 1 — the methodology registry's own staleness mechanism had never been fed

    python tools/verification_plan_staleness_check.py

**Before:** `COULD NOT TELL (exit 2). 10 item line(s) and NOT ONE verify marker,
so nothing above was measured and "drift found 0" is the absence of a
measurement, not the absence of drift.`

The tool was built for exactly this document, correctly refuses to report a pass,
and **had sat at exit 2 since it was written** because no item in the plan carries
a `<!-- verify: ... -->` marker. That is the platform's own rule — *a recording
tool nobody feeds reports a vacuous number forever* — applied to the tool that
enforces the rule.

**Fixed, partially and honestly:** three markers added, for the only three items
whose state I can verify from the repo today. **Eight items remain UNVERIFIABLE
and the tool prints them as a third state** rather than counting them clean. I did
not mass-mark: a marker on an item whose state I have not checked is worse than no
marker, because it converts an unknown into an assertion.

**And it immediately found two real drifts:**

| Plan line | Says | Reality |
|---|---|---|
| `:41` Item 54 (heartbeat/watchdog) | "claimed by Fourth, in progress" | no active claim names it |
| `:42` Item 77 (injection-phase field) | "claimed by Hank, in progress" | no active claim names it |

**Not fixed by me** — whether those items are done, dropped or need re-dispatching
is a question for Fourth and Hank. Reported so the plan stops asserting in-flight
work that is not in flight.

---

## FINDING 2 — that same tool read 0 claims from 6 files and reported drift anyway

**This is the serious one.** `claims()` treated a claim file as a single record and
looked for `subject` at the top level. The real shape is
`{session, claims: [...], refusals: [...]}`, so it parsed **nothing**, returned an
empty map, and then **every** `claim=` marker resolved to *"no ACTIVE claim of
that name exists"* and was reported `STALE-INFLIGHT`.

    before:  measured against 6838 commit(s) and   0 claim record(s)
    after:   measured against 6838 commit(s) and 543 claim record(s)

**It had read its source successfully** — the directory existed, so the tool
returned `True` for "measured" — **and produced verdicts from nothing.** That is
rule 1.11 with the arrow reversed: not *could-not-run folded into passed*, but
**could-not-parse folded into FOUND**. A false-finding generator is the shape that
gets a check switched off.

**Fixed:** both file shapes are read, released claims are excluded from `active`,
and **a directory of files that yields zero records now returns `measured=False`**
so every `claim=` marker becomes COULD NOT TELL instead of a fabricated finding.

**The two drifts in Finding 1 survived the fix**, which is what makes them real
rather than artefacts of this bug.

---

## FINDING 3 — the control that should have caught Finding 2 passed, and still would have

`tests/run_verification_plan_staleness_probe.py` ARM 5 asserted only that
`STALE-INFLIGHT` **fires** for a claim name nobody holds. **A detector stuck on
"fire" satisfies that perfectly — and one was.** Verified rather than asserted:
the control exits **0** against the pre-fix tool.

The commit direction had its paired positive (ARM 6, "an item marked DONE whose
commit DID land is NOT reported"). The claim direction never did.

**Fixed: ARM 5b**, which names a claim that IS actively held and demands silence.
It reads the **live** claim record rather than inventing a fixture, deliberately —
a fixture claim would not have exercised the parser that was broken.

**Ablation-verified**, not assumed: with the old parser restored in a temp copy,
`claims()` returns 0 records and `measured=False`, so ARM 5b finds no live claim
to name and **fails loudly** with *"COULD NOT DRIVE … This is NOT a pass"*. The
ablation script refuses to report if its own patch did not apply.

---

## FINDING 4 — the skill the model loads is BEHIND the skill in the repo

**Reported, not fixed. It is cc's content and possibly staged deliberately.**

    diff <(tr -d '\r' < .claude/skills/sairn-code-scrubber/SKILL.md) \
         <(tr -d '\r' < ~/.claude/skills/sairn-code-scrubber/SKILL.md)

Compared **after `tr -d '\r'`**, because the store is CRLF and the repo is LF and a
bare `diff` reports content-identical files as changed — this repo has four false
alarms on record for exactly that.

**Real divergence, 70 lines:** the repo copy carries `## 27. A cap on a ratio that
turns an OVERRUN into COMPLETION` and the user store does not. `sairn-guardian-v2`
is identical after normalising, so this is not a systematic mirror failure — it is
one skill.

**Why it matters more than a stale document:** `CLAUDE.md` says the repo *mirrors*
the store, so the **store is what a session actually loads**. A bug pattern added
to the repo copy is invisible to every session until the store is updated, and
nothing checks the direction. The scrubber section in question describes a defect
found on 2026-09-27 — **a real, current bug pattern that no session will be warned
about.**

**Named for cc**, whose section it is, rather than copied by me: overwriting
another session's skill file from the wrong direction is how a deliberate staging
step becomes a lost edit.

---

## FINDING 5 — four promoted checkers have no control, and eighteen have never been measured

    python tools/checker_control_check.py       # 64 promoted, 4 NO DECLARED CONTROL, 1 ONE DIRECTION
    python tools/flaky_checker_quarantine.py    # NOT MEASURED AT ALL: 18

**Reported as a standing number, not a finding against anyone.** Both tools already
print these as their own headline, so this is not new information — it is the
confirmation that the number is being read, which is the only thing that stops a
report-only figure from going quiet.

**One of the four is `checker_denominator.py`, which cc is actively building**, so
its missing control is work in flight rather than a gap. I did not check the other
three against their owners' claims and am not asserting anything about them.

**And a note about my own two tools from this week:** both
`assertion_label_shape_check.py` and `entry_point_scope_check.py` have controls
(25 and 21 arms, `CONTROLS_FOR` declared) and **neither is in the report-only
registry**, because `tools/report_only_checks.py` is held under a live `cc` claim.
So `checker_control_check.promoted()` cannot see either pair, and **they are
currently in neither the 64 nor the 4** — they are outside the population
entirely, which is a worse state than being counted as uncontrolled. Both are
tracked in open-work rows with the ready-to-paste entries.

---

## What this audit did NOT do

- **It did not audit the other sessions' skill logs.** Hank and cc were asked for
  the same thing in the same window; three sessions auditing one log would produce
  three partial answers and no owner.
- **It did not mass-mark the methodology plan.** Eight items remain unverifiable
  and are printed as such. Converting an unknown into an assertion to make a
  counter look better is the defect the counter exists to find.
- **It did not touch `tools/report_only_checks.py`, `tools/checker_denominator.py`
  or the `sairn-code-scrubber` user-store copy.** All three belong to live work by
  other sessions, declared rather than worked around (PR 4.3).
- **It did not re-measure the 12 cross-domain disciplines or the skill count.**
  Both are counted at point of use per CLAUDE.md; the disciplines heading count is
  **12** today, which matches what that file's own instruction predicts.

## One scope note on my own claim

`tools/verification_plan_staleness_check.py` and
`tests/run_verification_plan_staleness_probe.py` were **not** in this session's
declared FILES list. They are the methodology registry's own checker and its
control, which is squarely inside the "self-audit … of the methodology registry"
this claim names, and no other session holds either file — checked before editing.
Recorded here rather than left for a reviewer to notice.
