# Four research-method lessons — 2026-08-30

All four were produced in one night, three of them by my own mistakes and one
by borrowing someone else's good idea. They were scattered across four commit
messages and two research documents; this is the single findable place.

**They are the same mistake four times.** Each one substitutes a cheap,
adjacent question for the actual question — and the cheap question returns a
confident answer, which is what makes it dangerous:

| The actual question | The cheap substitute that was asked instead |
|---|---|
| Which subdivision holds this, and whom does it bind? | Do these words appear? |
| Is the alternative available and affordable? | Is the build path patent-clear? |
| Is this document's reasoning scoped carefully? | How dense are its citations? |
| Which *part* of this is blocked? | Is this blocked? |

The substitute is always faster and always answerable. That is the trap.

---

## 1. Confirming words EXIST is not confirming their SCOPE

**Where it happened.** ORC §2915.01(V). I asked a fetch-summariser *"does (V)
enumerate charitable purposes such as scholarships, flags, patriotism?"* and got
a truthful **yes** with a real verbatim quote. Recorded as verified.

The words were real. They sit in **(V)(2)**, which binds *veteran's*
organizations only. **(V)(3)** governs fraternal lodges — Elks, Moose, Eagles —
and contains none of them. SAIRNfreedom targets both families, so the
distinction was the entire question. A parallel session caught it.

**Cost if it had shipped:** one shared charitable-purpose enum, wrong for every
fraternal lodge in the product, failing in the direction that yields a
clean-looking licence renewal report backed by the wrong statute.

**The fix is the phrasing.** A yes/no question gets a yes. Ask instead:

> "Quote the division letter, and say which entity types it applies to."

Generalises past statutes to any hierarchical source — regulations, standards,
API docs, contracts. Presence is not scope.

## 2. Price the integrate option BEFORE recommending build

**Where it happened.** SAIRNfreedom Phase 2's bottle sensor was scoped as a
patent question. Hours went into the patent landscape and the answer stayed
ambiguous — one active family, one abandoned application, unclear ground.

What actually closed the phase was **one hour reading two vendor websites**:
neither exposes an API, and the one confirmed operating charges **$250–300/month
on a 1-year contract** — roughly ten times what the customer would pay for the
whole product. Build was blocked by patents; integrate was blocked by price and
access. Both, for different reasons.

**The fix:** on any build-vs-integrate question, establish the integrate
option's *availability and price first*. It is cheaper to check and more often
decisive.

**With the corollary that cost real time here — read the vendor's own site, not
the search summary.** *"Connects to over 50 of the top POS systems"* reads like
an integration platform. It is outbound work the vendor does and sells as a
feature. The only nav item that sounded like a partner route was a contact form.

## 3. A mechanical proxy for a judgement property ranks good work badly

**Where it happened.** Auditing the ten-document SAIRNsenior series for lesson
1, I ranked the documents by a subdivision-precision ratio — cites carrying a
subdivision ÷ bare cites.

**It ranked round 8 worst. Round 8 is the best document in the series** — I had
already read it and knew that. The ratio measured *citation density in prose*,
not scope discipline: a document that cites many sections precisely also
generates many bare matches. The real finding came from reading.

**The fix:** a mechanical proxy is for choosing a reading order. It is never
the verdict. When a metric disagrees with something you have read, the metric
is the thing under suspicion.

## 4. Separate "can I reach it" from "do I handle it correctly"

**Borrowed, not learned the hard way** — from
`2026-08-27-evv-transmission-groundwork.md`, which found that EVV format
conformance "can be proven with no credentials, no agreement, and no
trading-partner onboarding."

Reaching a service is gated. Handling its documented response correctly is
**not**, and never was. Most "blocked on credentials" threads are only half
blocked.

**Verified to generalise, not assumed.** Of 49 rows in
`docs/SAIRN-OPEN-WORK-INDEX.md` with a non-empty *Blocked by*, only **4** are
blocked on access, and two of those say in their own text that the block is not
an access problem. The one real candidate — SAIRNcash, blocked on
`STRIPE_SECRET_KEY` — now has `api/sairncash/verify.test.js`: **16 assertions
against Stripe's published Checkout Session and Subscription shapes, zero
credentials, all passing.**

What is still gated there: connectivity, the real price id, whether Stripe is
provisioned in Vercel at all. What is no longer waiting: every decision the
handler makes. **If that logic were wrong, the key would not have revealed it
faster — it would have revealed it in production.**

---

## Where these already live

Consolidated here; not deleted from their original homes, because each is more
useful with its own evidence beside it.

- Lessons 1–3, with the full statutory and audit detail:
  `docs/superpowers/specs/2026-08-30-sairnfreedom-research.md`, *Reconciliation
  record*.
- Lesson 4, demonstrated: `api/sairncash/verify.test.js` (commit `20840db`).
- Lessons 1 and 2 also in this session's memory as
  `verify-scope-not-just-presence`, so they survive the session.

## Related

`2026-08-26-parallel-duplicate-build-lesson.md` — the duplicate-work lesson,
which recurred the same night and cost two sessions roughly two hours each on
the same three SAIRNfreedom gates. Different failure, same root: neither
session checked the cheap thing (the remote, the other clone's active-work
file) before doing the expensive thing.
