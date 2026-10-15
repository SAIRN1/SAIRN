# hank — latest (b13, 2026-10-15)

**LANDED.** HEAD == origin/main `58e67efa` when the handoff was written, 0/0,
clean, **NOT forced**. Claim taken as the batch's FIRST action. Three gate
refusals (register-feed, derived-docs, tier-a), three satisfied, **zero
overridden**. Six merges, every one `pull --no-rebase`. Live probe:
**verified=5 fail=0 couldnot=3**, the three named.

## What changed

* **T16 as Michael decided, replacing hank's own N1 refusal.** The 409 closed
  the silent EVV overwrite and left no route for the caregiver who made the
  mistake. Now the original stays on the row and the submission is **appended**
  (old value, new value, actor from the verified session, reason, server
  timestamp), **pending** — and `effectiveClock()` ignores a pending entry, so
  payroll does not move on an unverified self-assertion. New scheduler-only
  `approve_clock_correction`, declared in the resource registry in the same
  edit. An entry with **no status is approved**, so live corrected visits are
  not silently reverted. RED 18/8 → GREEN 27/0.
* **T18** — `mappable` accepted any non-empty `applies_to_positions` while the
  leg beside it validated `audience`. Unmatchable is **UNDECIDED** with the
  token named; a false is **withheld** while a token is unread. RED 9/8 →
  GREEN 17/0.
* **T17** was already closed by b12's N2. Necessity proven by **ablation** (N2a
  red, three controls green). No new code.
* **N4** — the coverage claim now names the real `tests/` suite. cody's probe:
  **exit 0, 8/8**, was exit 1 with 3 findings.
* **F4/F5 (fourth's b20)** — the `leg_aftercare` key was delimiter-ambiguous
  and `merge-duplicates` made a collision silently overwrite a different case's
  check-in. Two forms now, so **every existing id survives byte for byte**; not
  hashed, because a hash collision merges two records. F5: the device adopts
  the id the server stored. RED 7/1/6 → GREEN 14/0.
* **The 11 UNPROVEN apps → 0.** Nine were the check's own fault: a table name
  it derived when `api/_lib/auth.js` says a derivation is wrong for five apps,
  and one detection method over one representation. 17 clean, 0 refused, 0
  unmeasurable.

## Open

1. **T16's approval route has no UI.** API-only; `pending_entries` is rendered
   by nothing, so a submission is invisible to a scheduler. → hank b14.
2. **The approver may be the submitter** in a one-person agency, marked
   `self_approved` not refused. Chosen from precedent, not a rule. → Michael.
3. **Tier A obligation open**, assigned to **fourth**: `alf_staff`,
   `leg_aftercare`, `leg_cases`, `sen_visits`, one question each.
4. **A misspelt role in a picker is still invisible** to the role-picker check
   — measured by sabotage, printed every run, **not closed**.
5. **Five apps' clean verdict is ARRAY-ONLY** — weaker than "the picker was
   checked", and labelled as such on each line.
6. **`api/sd-data-leg-session-gate.test.js` is red and is NOT mine** —
   identical exit 1 at the pre-b13 HEAD.
7. **Four SQL files unrun**, all Michael's: the census (PART 0 first), the two
   MAR-grant blocks, b10 block 5, and `sql/2026-10-14-michael-run-order.sql`
   — the last is the lag the role-picker check cannot see.

## Routed

* **cody** — your b14 `tests/run_b14_leg_aftercare_probe.py` is fourth's routed
  F4 arm. **My fix has landed**; `api/leg-aftercare-key-unambiguous.test.js`
  F4a drives the exact colliding pair. Write yours as a regression guard, and
  **do not build a second copy of the derivation**.
* **cc** — six `api/` suites need wiring into the gate driver (b12's three plus
  b13's three; the role-picker one exits **3 by design**, so treat 3 as
  could-not-run). Plus `fmea_draft --save` for four files.
* **fourth** — the Tier A discharge above.

CONTEXT 39% of 1000k used, measured from this session's own transcript
(cache_read 390,226 + 850), not from `/context`.

Chain tip: `58e67efa` (origin/main at handoff time).
