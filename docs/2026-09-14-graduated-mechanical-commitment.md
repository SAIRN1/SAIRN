# Item 101 — graduated mechanical commitment: is there a settling phase, or only a switch?

**2026-09-14 (Fourth).** Asked: does a genuine *settling / re-confirm* phase belong
between "looks ready" and "fully committed" at SAIRN's hard-commit points — not
just a two-step make-before-break?

**Answer: yes at one of them, and it was missing. Fixed in this pass. No at the
other two, and the reasons differ.**

---

## 1. What the docking sequence actually contributes

The NASA/IDSS docking sequence is three phases, not two:

| Phase | What happens | Reversible? |
|---|---|---|
| **Soft capture** | Contact, capture latches engage | Yes — release and back off |
| **Attenuation** | Relative motion is DAMPED, alignment re-measured and corrected | **Yes, and this is the point** |
| **Hard capture** | Structural latches close, seal compresses | No, except a deliberate undocking |

**The middle phase is the whole contribution, and it is easy to read as padding.**
It exists because *the conditions at first contact are transient*. Committing at
the instant of contact latches in whatever misalignment happened to exist then.
Attenuation waits for the transient to decay **and re-measures**, with the
option to abort still open.

**Two properties make it a settling phase rather than a delay:**

1. **It re-measures the WORLD**, not the plan. A timer that re-checks nothing is
   a deadline.
2. **Abort is still cheap.** Once hard capture closes, abort costs a full
   undocking. The re-check has to happen while backing out is still free.

A two-step make-before-break has neither: it proves the new thing exists before
releasing the old one, which is a different property (continuity) and says
nothing about whether the world moved in between.

---

## 2. SAIRN's hard-commit points, one at a time

### 2a. Item 19 — the witnessing lock (`api/sv-witness.js`) — **the gap was real**

Two phases, and they map cleanly:

- **soft capture** — `action: 'request'` mints a token bound to a
  `content_hash`, TTL 10 minutes;
- **hard capture** — `requireWitness()` verifies the token, marks it spent with
  a compare-and-set, and the row is written to `sv_controlled`.

**Everything `requireWitness()` re-checked was a fact about the TOKEN.** That it
exists, is unspent, is unexpired, covers *this* payload, and carries the
countersignature the policy demands. **Not one is a fact about the world**, and
the world had up to `TOKEN_TTL_MS` to move.

**The TTL is not an attenuation phase. It is a deadline, and a deadline
re-verifies nothing.**

**The reachable case, and this file already named the hazard 300 lines above the
place it did not check it.** `activeCaller()` carries the comment: *"a witness
signature from a revoked account is worse than no signature: it carries a name
that no longer means anything."* It was called on `policy`, `set_policy`,
`request` and `countersign` — **and never on the spend path.** So a vet could
confirm a controlled-substance entry, be deactivated (struck off, dismissed,
licence pulled — precisely when deactivation is urgent), and the write would
still land attributed to them within the next ten minutes.

On `sv_controlled`, which `tools/removal_path_check.py --burn-down` ranks **Tier
A with no removal path** and `api/_resources/sairnvet.js` calls *"the
controlled-substance register (DEA-relevant)"*. A correction there is a SECOND
row and the wrong one stands forever.

**FIXED IN THIS PASS.** `requireWitness()` now re-reads the attester —
`witness_employee_id`, and `countersign_employee_id` when two-person is on —
against `active=eq.true` before spending the token. Three properties, each
deliberate:

- **It checks the ATTESTER, not the current caller.** It is the confirmer's
  standing the record claims, not the saver's.
- **It refuses BEFORE the spend.** Burning the token on a refusal the operator
  cannot act on would force a re-confirmation for something that is not their
  fault — and abort must stay cheap, which is property 2 above.
- **A failed lookup is `WITNESS_CHECK_FAILED` (503), not "still active".**
  Could-not-tell on an irreversible write is a refusal, the same as every other
  could-not-tell in that function.

Five arms, sabotage-verified in both halves: emptying the witness list takes 3
red, dropping the countersigner line takes the fourth. A fifth is the paired
positive — an active attester still proceeds, so the step is not a blanket
refusal.

### 2b. Deploy commits — **no, and the reason is that the third phase exists already**

`git push` → Vercel build → production. The tempting reading is that push is
hard capture with nothing before it. It is not:

- **Soft capture** is the push gate: full Check 0 and every `sairn-guardian-v2`
  check, which refuse before anything reaches the remote.
- **Attenuation** is `tools/deploy_verify_notify.py` — it waits ~60s and hashes
  the live site against `HEAD`, which is a genuine *re-measurement of the world
  after the transient*, exactly the right shape.
- **Hard capture** is production serving the new bytes.

**The gap here is not a missing phase, it is that abort is not cheap.** By the
time the mismatch is detected the deploy has happened; the remedy is roll
forward. Adding a re-confirm *before* the push would re-measure a world that has
not moved yet, which is the phase doing nothing.

**Recorded rather than acted on:** the useful change at this commit point is
making abort cheaper (a tested rollback path), not inserting a fourth phase.
That is a different item and it is not claimed here.

### 2c. Migrations run by hand in the SQL editor — **no, because there is no soft capture to settle from**

`sql/*.sql` pasted into the Supabase editor is a single irreversible step with
**no soft-capture phase at all**. The editor reports success for the statements
it ran, so a partial apply is indistinguishable from a full one — the failure
`sairn-guardian-v2` records twice on 2026-08-26.

**A settling phase cannot be added to a commit point that has only one phase.**
What that one needs is the per-statement confirm query the guardian already
mandates — evidence *after*, because there is no *before* to re-check. Naming it
here so item 101 is not read as covering it.

---

## 3. The generalisation, stated narrowly on purpose

**Where a commit point has a soft phase, ask what it re-checks at the hard
phase — and expect the answer to be "the token, not the world."** That is the
shape found here, and it is a natural one to write: the token is the thing in
your hand at the moment of the write, and the preconditions are somewhere else.

**Do not generalise this into "add a settling phase everywhere."** Two of the
three commit points examined do not want one, for different reasons, and a
phase that re-measures nothing is a delay that teaches people to wait.

## 4. What this does NOT claim

- **The other ~14 append-only Class A resources** in
  `docs/2026-09-13-irreversible-write-witnessing-scoping.md` have no lock at all
  and so no settling question yet. They are a separately-sized piece.
- **No live verification.** `api/sv-witness.js` is exercised against a fake REST
  layer, which is right for a decision function; that the deactivated-witness
  case behaves this way against a real database has not been observed here and
  is not claimed. `SUPABASE_URL` is unset in this clone.
- **The 10-minute TTL was not re-derived.** It is unchanged, and whether ten
  minutes is the right window is a separate question from whether anything is
  re-checked inside it.
- **Nothing here says the lock makes a record correct.** `api/sv-witness.js`
  says it first and better: a witness attests that somebody looked, not that
  they were right.
