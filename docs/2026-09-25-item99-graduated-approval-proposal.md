# Item 99, the half still open — does the most consequential change get a different APPROVAL, or just more review?

**2026-09-25 (Cody).** A scoping pass on the question
`docs/2026-09-15-item99-graduated-consent-for-irreversible-changes.md` left
open. That document answered *"is consent attached to the change?"* and
recorded that `tools/tier_a_review_gate.py` closed it hours later. This one
asks the question underneath it:

> **Does the platform's most consequential change type get a genuinely
> different approval PROCESS, or the same process with more review bolted on?**

**Measured answer: the same process. No change on this platform — none, of any
tier — requires consent before it lands.** That is not a criticism of the
review culture, which the numbers below show is strong. It is a statement about
where the gate sits in the sequence, and it is the one structural property
Bitcoin Core's consensus model has that SAIRN does not.

Everything below is measured against the repo at `d10494dd`. Re-derive rather
than quote: every figure here is a snapshot and this document says so in §7.

---

## 1. What the approval sequence actually is, for every change

For a Tier A change and for a typo, the sequence is identical:

```
write  ->  push  ->  (gate: is an OBLIGATION recorded?)  ->  LANDED  ->  review, later, maybe
```

`tools/tier_a_review_gate.py` is genuinely good and it is not what is missing.
It refuses a push that changes Tier A code with **no obligation recorded**, it
refuses a record whose reviewer is its own author, and it assigns rather than
leaving first-come. It closed property **(a)** — consent discoverable from the
change — exactly as item 99 §5.1 says.

**But it gates the RECORDING, not the APPROVAL.** The obligation is a promise
that somebody will look. The code is already on `origin/main` when the promise
is made, serving customers, while the promise is outstanding.

Bitcoin Core's consensus rule is the opposite shape: the change **does not
land** until ACKs exist. The bar is set by blast radius and the artifact waits.

---

## 2. The review culture is strong, and that matters for what follows

This is not a document arguing for more rigour. Measured from
`docs/tier-a-reviews.json`:

| | |
|---|---|
| obligations recorded | **157** |
| discharged | **143** (91%) |
| open | **14** |
| discharge latency | min 0.3h, **median 8.2h**, p90 55.3h, max 67.4h |
| open obligation age | median 19.8h, max 44.1h, **4 of 14 over 24h** |

A 91% discharge rate at a median of eight hours, across five sessions, is a
working ledger. **Any proposal that makes this worse is a bad trade**, and that
constraint shapes §5 more than anything else here.

---

## 3. Property (b) is still open, and it is now the blocker rather than a nicety

Item 99 §5.1 left this: the gate records **that** an obligation exists, not
**what kind** of review discharged it. There is still no field for it — the
record's keys are `author_session, commit, files, note, opened_at,
opened_at_sha, owner_assigned_at, owner_note, resources, reviewed_at,
reviewer_owner, reviewer_session, rules, status, verdict, what`. Nothing names
the kind.

**So it was measured out of the prose instead**, by matching the 143 verdicts
for evidence of having run something versus only read:

| verdict contains | count |
|---|---|
| evidence of RUNNING it (drove / ran / reproduced / measured / mutated) | **101** |
| both running and reading language | **30** |
| read-only language only | **3** |
| neither pattern | **9** |

**131 of 143 discharges show the reviewer ran something.** Item 99 §2 called
this *"a tested ACK, invented independently and expressed better"*, and the
number supports that.

**THE REASON THIS MATTERS HERE IS NOT BOOKKEEPING.** §5's rule requires a
**tested** discharge and must be able to refuse a read-only one. A regex over
prose cannot carry a gate — it is the instrument-drift shape
(`docs/2026-09-13-cross-domain-disciplines.md` §8) waiting to happen: the day
somebody writes *"reviewed by reading the diff and I did not run it"*, the
regex sees "run" and passes. **A structured field is a precondition for §5, not
an improvement to it.** That is the one thing in this document that should be
built first and is cheap.

---

## 4. Which changes actually deserve a different process — and it is NOT "Tier A"

Tier A is 257 resources. Requiring pre-landing consent on all of them would
block essentially every push on this platform, and the failure mode is already
recorded in item 99's own §5: *"a gate that is red on arrival gets disabled,
and then the rule is worse off than when it was merely unenforceable."*

The distinguishing property is not tier. It is **whether a later commit undoes
the effect.**

| | a later commit undoes it? | example |
|---|---|---|
| ordinary Tier A code | **yes** — revert and redeploy | the SAIRNscape session gate; a wrong role set |
| **irreversible** | **no** — the effect has already escaped | a `revoke` executed against the live database; a reconciliation a firm relied on to move client money; an auth change that already minted tokens |

A revert does not un-execute SQL, does not un-send a filing, and does not
recall a token. **That, not the tier, is Bitcoin Core's actual criterion** — a
one-line consensus change outranks a thousand-line GUI change because consensus
cannot be rolled back.

**Measured candidate class**, deliberately narrow, over 2026-09-11..today:

| candidate | commits |
|---|---|
| `api/_lib/auth.js` (shared by 82 API files) | 5 |
| `api/_lib/law-trust-reconcile.js` (IOLTA three-way) | 4 |
| `api/_lib/employee-lifecycle.js` | 4 |
| `sql/` containing `grant`/`revoke` | 20 |
| **union, deduplicated** | **30** |

Against **2894 commits** in the same fourteen days: **about 1%.** Over the full
register window (since 2026-09-09) the same union is 36.

That is the right order of magnitude for a rule that makes a push wait. If the
class were 10% it would be a wall.

---

## 5. The proposal — four properties, and each is a different PROCESS, not more review

**Class name: `irreversible`.** Membership is by explicit nomination, never
derived.

**(1) Consent PRECEDES landing.** For a commit in the class, the push is
refused until a **discharged** obligation names it — not merely a recorded one.
This is the single property that makes the approval different in kind rather
than in volume. Everything else on the platform keeps today's
record-then-review sequence, unchanged.

**(2) The discharge must be `tested`.** A read-only ACK cannot discharge an
irreversible-class obligation. Requires §3's structured field to exist first.
This is Bitcoin Core's (b) used as a gate rather than as documentation.

**(3) Two sessions, not one.** Two independent discharges by two different
sessions, neither the author. **The reason is this platform's own
`cross-domain-disciplines` §7:** Ariane 5 lost a vehicle to two identical
redundant units failing identically, because *a second copy is not a second
opinion*. One reviewer of an irreversible change is a single point of judgement
on the one class where there is no second chance.

**(4) A window with a way to still fail** — Bitcoin Core's (c), and the
property item 99 §4 correctly deferred to item 101 for deploys but which has no
analogue for *approval*. After the second discharge, a hold before the push is
accepted, during which any session may NACK and reopen the obligation. Consent
becomes a process with a failure mode rather than a counter reaching two.

### Why this is not red on arrival

**The class starts EMPTY.** Nothing historical is retroactively
non-compliant — the exact objection item 99 §5 raised against its own
`Reviewed-By:` proposal, and the reason that proposal was not built. Each
member is added by a deliberate commit carrying a written reason, the same
convention `run_all_tests.py`'s `CONCURRENCY_SENSITIVE` set already uses:
*"adding to this set is a claim."*

Suggested first three, each because a revert genuinely does not undo it:
`api/_lib/auth.js`, `api/_lib/law-trust-reconcile.js`, and any `sql/` file
containing `grant` or `revoke`. That is 30 commits in fourteen days, ~1%.

### The cost, stated rather than buried

At a **median discharge of 8.2h and a p90 of 55.3h**, property (1) means an
irreversible-class push waits hours and sometimes two days. With property (3)
it waits for two of them. **On a four-session platform that is a real cost and
it is the reason the class must stay tiny** — and the reason properties (3) and
(4) should be considered separately from (1) rather than adopted as a block.

**A cheaper variant worth costing before the full version:** properties (1) and
(2) only, one discharge, no hold window. That is still a different approval
sequence — consent before landing — at roughly half the latency.

---

## 6. What this does NOT claim

- **It does not claim any irreversible change went wrong.** No instance is
  cited because none was found; the argument is structural.
- **It does not claim the review culture is weak.** §2 is evidence of the
  opposite, and is the main constraint on §5.
- **It does not propose more review.** §5 proposes review in a different
  *position* — before landing rather than after — for about 1% of commits.
  Everything else keeps today's process untouched.
- **It is not built.** Property (2) depends on §3's field, which does not
  exist; properties (1), (3) and (4) are a policy decision about how long a
  push may be made to wait, which is **Michael's to make and not a tool's** —
  the same call item 99 §5 reached and `register_feed_gate` respected.
- **The class membership above is a suggestion, not a finding.** Three paths
  and one SQL pattern were measured for volume, not audited for whether each is
  genuinely irreversible.

---

## 7. Decay

Every figure here is a snapshot of 2026-09-25 at `d10494dd`: 157/143/14
obligations, 8.2h median, 131-of-143 tested-shaped verdicts, 30 candidate
commits in fourteen days, 2894 commits total. The ledger moves hourly across
five clones. **Re-derive before quoting any of them** — and in particular
re-derive the 131 of 143, because it is a regex over prose and §3 explains why
that is exactly the kind of number that goes quietly wrong.
