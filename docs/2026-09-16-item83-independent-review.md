# Item 83, independent review — 96 arms cover two entry points and never enter the third

**2026-09-16.** Independent adversarial review of Cody's item-83 witnessing-lock
suites, by a fresh-context reviewer with no knowledge of the work. Commissioned
by Michael; the reviewer was not the author and not the session that
commissioned it.

Subject: `api/sv-witness.js` (502 lines), the server-side witnessing lock for
irreversible writes on SAIRNvet — controlled-substance, DEA-relevant.

Controls reviewed: `tests/failsafe/witness_atomicity.js`,
`tests/failsafe/witness_recovery.js`, `tests/failsafe/witness_countersign.js`,
plus `api/sv-witness.test.js`, `tests/sv_witness_probe.py` and
`tests/countersign_coverage_probe.py`.

---

## Method, and why the baseline is not the evidence

**Baseline: 96 arms, all green.** That is the least interesting fact in this
document. The question a control review has to answer is not *do the tests
pass* — it is **if the behaviour an arm names were broken, would that arm
actually go red.**

So the reviewer built an independent sabotage driver — **32 mutations, wider
than either existing probe** — running in a detached `git worktree` seeded from
the working tree, with `count(anchor) != 1` reported as **COULD-NOT-PLANT** and
never folded into pass or miss.

**Zero COULD-NOT-PLANT rows: every one of the 32 genuinely applied.** That
matters as much as the result — a sabotage that silently does not apply reports
the expected answer for the wrong reason, and this platform has measured that
failure across most of its controls.

**25 caught. 7 survived all 96 arms.**

---

## 1. CONFIRMED, and it is the one that matters: the half that MINTS the token is driven by nothing

`grep` across the whole repository finds **nothing anywhere** driving
`action: 'request'`, `'set_policy'` or `'policy'`. Four mutations inside those
handlers survived every arm in all four suites:

| file:line | sabotage | result |
|---|---|---|
| `api/sv-witness.js:242` | `if (!svAuth.isPrescriber(caller))` → `if (false)` | all green |
| `api/sv-witness.js:267` | `token_hash: hashToken(tok)` → `String(tok)` | all green |
| `api/sv-witness.js:268` | `contentHash(resource, body.payload)` → `contentHash(resource, {})` | all green |
| `api/sv-witness.js:214` | `set_policy` owner gate → `if (!caller)` | all green |

What ships undetected, concretely:

* **A receptionist or tech mints a witness token** for a controlled-substance
  entry and the row records `witness_role: 'receptionist'`.
  `api/sv-witness.test.js:146-158` — *"only a licensed veterinarian may
  witness"* — tests `svAuth.isPrescriber` **as a pure function** and asserts the
  tier is imported. It never asserts the handler calls it. **It tests the
  helper, not the call site.**
* **The tokens table holds plaintext, spendable signatures** on a DEA-relevant
  register — and the lock breaks outright, because mint would store plaintext
  while `requireWitness` looks up a sha256. Nothing goes red. The two controls
  that look like they cover this both read somewhere else:
  `api/sv-witness.test.js:120` reads the *body* of `hashToken()`, and `:447`
  reads `sql/sairnvet_witness_schema.sql`. **Neither reads the call site.**
* **The token is bound to nothing at mint time.** Every content-binding arm in
  every suite *fabricates the token row itself* with a correct `content_hash`,
  so the binding is proven on the CHECK side and never on the MINT side. This
  is precisely the hole `api/sv-witness.js:42-45` names in its own header: *"A
  token bound to the event can be spent on a different record."*
* **Any signed-in employee turns `require_two_person` off**, after which
  `requireWitness` stops demanding a countersignature at all.

**This is structurally the identical finding `bba0c82a` made about
`countersign`, one entry point over.** `c35af12d` closed `countersign`;
`request` was never scoped — and the suites' own honest-scope headers do not
name it as out of scope either, so a reader has no way to tell the gap is
there.

## 2. CONFIRMED: `active=eq.true` can be deleted and nothing goes red

`api/sv-witness.js:181`. Dropping `&active=eq.true` from the employee lookup
left all four suites green.

**A struck-off, dismissed or deactivated vet with a live session — up to 12
hours — can `request` and `countersign` controlled-substance entries.** That is
the exact hazard `api/sv-witness.js:172-175` names in words.

`witness_countersign.js:55-57` *discloses* that it cannot test this — it
"proves the lock refuses when the lookup comes back EMPTY, not that the filter
is spelled correctly." **The same file demonstrates the remedy 430 lines
later:** `:490-498` source-anchors `SAME_PERSON` precisely because "deletion is
invisible everywhere else." The technique was in hand and was not applied to
the one guard the file admits it cannot reach behaviourally.

## 3. CONFIRMED: the coverage cross-check is a floor, and its comment says otherwise

`witness_countersign.js:477-489` asserts `listed >= 6`. The reviewer added a
seventh mutation to `countersign_coverage_probe.py` with **no matching section
in the suite** — the arm stayed **green** and the suite exited 0.

The comment at `:475-476` says adding a mutation without an arm "is VISIBLE
instead of silently uncovered." **That is false as written.** The probe can grow
indefinitely and this arm will never notice. Fix: `assert.strictEqual(listed,
6)`, deliberately bumped, or a per-mutation name cross-walk instead of a count.

## 4. CONFIRMED: an arm names a guard it cannot distinguish

`api/sv-witness.test.js:181-186`, *"NO TOKEN refuses with WITNESS_REQUIRED"*.
Deleting the guard at `api/sv-witness.js:361` (`if (!token)` → `if (false)`)
left all four suites green: the empty token falls through to the row lookup, no
row returns, and `:381-383` produces the **same** code and the **same** 403.

Operational risk is low — the behaviour survives — but it is a green arm
sitting over a deleted guard.

## 5–6. Minor

* `witness_recovery.js:200-203` — the "row was never edited" assertion
  normalises `spent_at` on both sides, so a spend landing on the row is
  invisible to it. Redundant rather than wrong: covered two lines above by
  `world.applied.length === 0`. Its stated claim is broader than what it checks.
* `witness_atomicity.js:83-86` — `hashedRow()` is dead code, defined and never
  called. Cosmetic, but a dead helper among live fixtures reads as coverage.
* `witness_atomicity.js:93-99` sets a module-level `TRANSITION_CALLS` in arm 1
  that arm 2 consumes. If arm 1 fails, arm 2 silently degrades to a single
  interruption point. Loud enough via arm 1's own red, but a hidden coupling.

---

## What was checked and found SOUND

Recorded because *"I checked this and it holds"* is a result, and an unchecked
claim must not be mistaken for a sound one.

1. **Atomicity is real, not a happy path plus an error path.**
   `witness_atomicity.js:109-122` interrupts at every *measured* call index and
   asserts proceed ⟹ spent. It bites: swallowing the throw turns ATOM+RECOV
   red; returning null before the spend turns ATOM+RECOV+UNIT red.
2. The **"spend landed, answer didn't"** case measures the spend's call index
   rather than hard-coding it, and carries its own did-the-fixture-apply guard.
3. **The race is a real interleaving**, `Promise.all` against a modelled
   compare-and-set — not an assertion about one. Dropping `&spent_at=is.null`
   turns three suites red.
4. **`db7f5f59`'s "move the clock, not another offset" is true.**
   `failsafekit.js:221-229` replaces `Date.now` and *awaits* inside
   try/finally. Independently confirmed by `TOKEN_TTL_MS = 0` and a wrong-unit
   mutation, each caught.
5. **The boundary arms really freeze the clock** and assert the *mechanism* —
   including that the real function **identity** is restored afterwards, not
   its value, which would pass by luck.
6. **`c35af12d`'s claim that the countersign half is now caught: TRUE.** All six
   probe mutations plus four the reviewer invented independently are caught by
   `witness_countersign.js` and by no other suite.
7. **`bba0c82a`'s "a mutation control whose header said it never touched the
   clone" is now honest.** Both probes use `git worktree add --detach`, copy in,
   restore in `finally`, prune. Concurrent probes cannot clobber each other.
8. **Sabotage cannot silently fail to apply** — `count(anchor) != 1` is a third
   state in both probes, and the coverage probe fails closed.
9. **The suites drive the real thing** — all three `require()` the real module
   and use the real `contentHash`/`TOKEN_TTL_MS`. No reimplemented logic.
10. **No vacuous "expect no findings" arms** anywhere in the three suites.

**Net: these are genuinely well-built suites** — among the better controls on
this platform; sections A/C/C2 of atomicity and B2 of recovery are exemplary.
**The gap is not craft, it is scope.** 96 arms cover `requireWitness` and
`countersign` thoroughly and do not enter `request` at all.

## Not reached

`sql/sairnvet_witness_schema.sql` and
`docs/2026-09-13-irreversible-write-witnessing-scoping.md` were not reviewed
against the code; the `api/sd-data.js` call-site anchor at
`api/sv-witness.test.js:408` was not sabotaged; nothing was verified against the
live deployment.

## Routing

**Not fixed here, and deliberately.** These are Cody's suites and Cody's
subject; a reviewer who fixes what it found stops being a reviewer, and the
second pair of eyes is the whole value. Findings 1 and 2 are the priority — both
are live authorisation gaps on a controlled-substance path, not test debt.
