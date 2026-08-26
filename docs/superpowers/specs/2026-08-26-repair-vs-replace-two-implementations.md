# Repair-vs-replace: two independent implementations, side by side

**2026-08-26.** Two sessions built this feature the same night without either
knowing the other had. Neither migration has been run, so **nothing is live and
there is no clock on the decision.**

| | Cody — `4d4410f` (on `origin/main`) | CC — local, committed, **not pushed** |
|---|---|---|
| Engine | `api/_lib/roofing-damage-assessment.js` (208 lines) | `api/_lib/roofing-repair.js` (261 lines) |
| Storage | `rf_settings`, keyed rows (`setting_key='damage_threshold'`) | `rf_repair_thresholds`, single-purpose table |
| Verb | `assess_damage` | `assess_repair` |
| Tests | in that commit | 17 engine + 18 endpoint |

Both were read in full before this was written — behaviour, not headers.

---

## Where they independently agree

Worth recording because it was arrived at twice, separately:

- Pure engine, no I/O, no LLM.
- **Three outcomes, third mandatory.** A missing count is never "low damage".
- **Per-slope, never a whole-roof verdict.** Both refuse to emit a roof-level
  yes/no, both for the same stated reason: carriers total slopes.
- **Threshold configured, never hardcoded**, carrying a required `source`, and
  both refuse to assess rather than assume one. Both name Guardian Check 0b's
  fabricated-authority pattern as the reason.
- Management-only write, open read (a foreman must see the number they were
  measured against).
- Per-claim override that reports *as* an override.

---

## Where Cody's is better, and these are real

1. **DENSITY, NOT RAW COUNT — and this is a defect in CC's engine, not a
   preference.** Cody divides: `counted / test_squares`, then compares per
   square, with no rounding ("rounding 7.5 up to 8 would manufacture a total
   slope out of arithmetic"). CC's compares the raw `test_square_hits` against
   the threshold directly, which silently assumes exactly one test square was
   inspected. The convention is *per square*. **A 12-hit count over 3 squares
   is 4/square — CC's engine would call that 12 and meet a threshold of 8.**
   CC's version cannot ship as-is without this fix.

2. **Outcome vocabulary.** Cody: `meets_threshold` / `below_threshold` /
   `insufficient_evidence` — describes the *evidence*. CC: `supports_replacement`
   / `supports_repair` — edges toward entitlement, which is the exact line the
   public-adjuster rules draw. Cody's is the safer wording and cites real
   statutes for why (Tex. Ins. Code 4102.163, Fla. Stat. 626.854).

3. **Refuses rather than partially answers.** Cody returns `ok:false` with
   problems on invalid input. CC returns a result with `reasons`.

4. **`rf_settings` is the better table.** Keyed rows mean this is the last
   settings migration the app needs; CC's is single-purpose. Cody's commit also
   registers it on day one specifically so the provisioning probe can see it —
   the gap that left 41 declared tables unmeasurable.

---

## Where CC's is stricter — the two Michael asked about

**1. The photo-evidence rule. CONFIRMED DIFFERENT — Cody's is not strict.**

Cody computes `evidence_gap` as a *string annotation* and nothing more:

```js
evidence_gap: cited.length ? null : 'No photo cited for this slope -- the count is unsupported by evidence in this app.'
```

The outcome is unchanged. **A slope with 40 hits and zero photos still returns
`meets_threshold`**, with the gap noted beside it. CC's refuses: no photo means
the count is reported but never scored, and if no slope is evidenced the whole
claim is `insufficient_evidence` regardless of the numbers. Michael confirmed
the strict rule explicitly on 2026-08-26.

**Also:** Cody takes `photo_ids` from the payload and only filters blanks —
it never checks the ids exist on that claim. CC reads `rf_claim_photos`
server-side and returns unresolved ids by name. This is the same
caller-cannot-substitute discipline Phase 3c already established for the
measured scope.

**2. Unmatchable / discontinued shingle. BOTH HANDLE IT — OPPOSITELY.**

Cody treats it as a **hard trigger that scores**: `discontinued_material ===
true` returns `meets_threshold` immediately, basis `discontinued_material`,
reason *"a matching spot repair is not purchasable"* — no test square needed.

CC **records it and deliberately refuses to score it**, on the grounds that
whether an unmatchable shingle supports replacing *undamaged* slopes turns on
policy wording and on state matching / line-of-sight rules that were **not
researched and are not cited anywhere in either implementation.**

This is a genuine judgment call, not a bug in either:
- Cody's is more useful and states a defensible physical fact.
- But it converts an unverified coverage question into a threshold-meeting
  outcome — the one place either engine asserts something legal-adjacent
  without a citation, in a feature whose whole design principle is that a
  number needs a traceable source.

**Recommend: keep the trigger, but as its own basis that does not silently read
as a damage threshold being met, and research the matching rules before it goes
in front of a carrier.**

---

## One difference that is NOT a defect

CC computes only from the **stored** claim blob. Cody accepts
`payload.assessment` and falls back to stored. That looked like a gate hole and
is not: the UI is deliberately assess-then-save (`rfDmgBuildPayload()` sends
unsaved form state, and the toast reads *"Assessed. Press Save Evidence to
record the threshold this used."*). It is a live preview by design. The
trade-off is real but minor — Cody's is better UX, CC's has stricter
provenance.

---

## Recommendation

**Keep Cody's as the base.** It is already pushed, its density model is
correct where CC's is wrong, its vocabulary is safer, and `rf_settings` is the
better long-term home. Port three things from CC's:

1. The **strict photo rule** — no photo, no scoring; no evidenced slope,
   `insufficient_evidence`. Michael confirmed this.
2. **Server-side photo-id verification** against `rf_claim_photos`, with
   unresolved ids named.
3. Re-shape the **discontinued-material trigger** so it does not present as a
   met damage threshold, pending the matching-rule research.

CC's engine, table, verb, tests and panel are then deleted rather than merged —
two of anything is what caused this.

**Not affected either way:** the patent position. Either implementation supplies
element 4 of US 8,983,806 B2 claim 1, and element 5 remains the only element
the app does not meet.
