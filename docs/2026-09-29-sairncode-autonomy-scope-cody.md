# SAIRNcode autonomy — what is already autonomous, and where the boundary has to sit

**2026-09-29 (Cody). SCOPING AND A CORRECTION. Nothing here is built.**

This is the companion to `docs/2026-09-28-sairncode-autonomous-coding-scope.md`,
and it opens by correcting that document, because the correction changes what the
remaining work is.

---

## 0. THE PREDECESSOR'S CENTRAL MEASUREMENT WAS WRONG, AND THE FEATURE IT CALLED MISSING SHIPPED FIVE WEEKS EARLIER

`docs/2026-09-28-sairncode-autonomous-coding-scope.md` says:

> **The gap is AUTONOMY.** Measured: `autonomous` appears **0 times** in
> `sairncode.html`, `routing` **0 times**, `audit trail` **0 times**. There is a
> review queue and there is a derived confidence, and **nothing connects them**.

Re-measured in `sairncode.html` at `origin/main` today:

| token | that document | today |
|---|---|---|
| `autonomous` | 0 | **0** — correct |
| `routing` | 0 | **20** |
| `audit trail` | 0 | **0** — correct |

And the substantive claim — *"there is a review queue and there is a derived
confidence and nothing connects them"* — **is false, and was false when it was
written.** The connection is three lines inside the confidence function itself:

```js
return {
    confidence: basis.length ? 'low' : 'high',
    confidence_basis: basis,
    review_status: basis.length ? 'needs_human_review' : 'auto_assigned',
    escalation_reason: basis.length
        ? 'Held for a human coder because: ' + basis.join(' ')
        : ''
};
```

…consumed by `scRouteCodedItems()`, which splits the queue in two so that
auto-assigned items stop consuming a coder's attention. Both landed in
**`f9a3b381`, 2026-08-20** — *"SAIRNcode Phase 2 item 3 — exception-based routing
+ two real confidence signals"* — five and a half weeks before the document that
called them missing.

**How a word count produced a wrong answer about built code:** the feature is
spelled `scRouteCodedItems`, `review_status`, `auto_assigned`,
`needs_human_review`. It is not spelled `autonomous`, and the word `routing`
appears twenty times in the comments around it. A vocabulary drawn from a
*competitor audit* was used to measure *this app*, and an absence of the
competitor's words was read as an absence of the capability. That is the same
shape as a stale anchor: the check was real, the subject was not what the check
was looking at.

**So item 1 of the predecessor list — "Route on the confidence that already
exists" — is not small. It is DONE.** It should be struck from that list rather
than re-scoped, and this document is the record of why.

---

## 1. What is therefore actually open

Not the routing edge. **The SCOPE of the autonomy that edge already grants** —
which is a different question and a harder one, because it is not an engineering
decision.

### 1.1 The confidence is BINARY, and "high" means the absence of a red flag

```js
confidence: basis.length ? 'low' : 'high'
```

`basis` is a list of **disqualifying** signals: no cited phrase, a phrase that
did not verify, no source rule, no code value, a conflict with a scrub rule this
practice itself entered, a prior rejection of the same code by a coder, a
credentialing gap, an eligibility concern. Every one is real, mechanical, and
derived from data the practice created — the design is deliberately strong and
the file says so in its own comments, including why a numeric confidence was
removed after the fabricated 82%/71% scores.

**But `high` is not evidence that the code is right. It is the absence of
evidence that it is wrong.** Those are different claims, and the second one is
what currently decides that no human looks at the item.

That is defensible today, because nothing downstream acts on `auto_assigned`
except the queue split. It stops being defensible the moment an auto-assigned
item can reach a claim without a human in between — and reaching a claim is what
"autonomy" means in the category the predecessor document is scoping against.

### 1.2 The one gate that must exist before autonomy widens

**No coded item may reach `sc_claims` on `auto_assigned` alone.** Today it
cannot; there is no path from the coded-items queue to a submitted claim that
skips a person. Any work that creates one has to bring its own gate with it, and
the gate is not a threshold — a binary signal has no threshold to tune.

The shape it needs instead is a **named allow-list of what may ever be
autonomous**, because "everything that has no red flag" is not a scope, it is a
default:

| may be autonomous | must never be | why |
|---|---|---|
| a code the practice's own verified scrub rules and prior coder decisions both support, on an encounter whose eligibility answered clean | anything where `quote_verified !== true` | the citation check is the entire explainability claim; an unverified quote auto-assigned is an auto-assignment on no grounds |
| a repeat of a code a coder has already accepted for the same encounter type | any code the practice has **never** billed before | a first-time code is a coverage and credentialing question, not a coding one |
| — | anything on an encounter with a credentialing or eligibility concern **of any severity** | these already force `low`; they must not become tunable |
| — | anything where an NCCI-style interaction would apply but no local rule exists | absence of a local rule is a gap in the practice's rule table, not a clean interaction check. The file is already explicit that a hardcoded NCCI table would not be safe to ship |

**The last row is the important one and it is the current design's honest
weakness.** `findLocalScrubMatch` reads `sc_scrubrules`, where every row required
a human-entered Source and nothing is ever seeded. That makes a hit *strong*
evidence. It makes a **miss** no evidence at all — and a miss currently
contributes nothing to `basis`, so it reads as clean. A practice with an empty
rule table gets `high` on everything.

That is the zero-item-corpus failure in a product surface: **an empty rule table
and a table with no conflicts produce the same answer**, and the second is the
one the user will read.

### 1.3 What that means for the build

Before any autonomy widens, `scDeriveCodedItemConfidence` needs a third state,
not a second signal: **`cannot_tell`**, separate from `low` and `high`, set when
the practice's rule table is empty or does not cover the code pair being checked.
It routes to a human exactly like `low` does today, so nothing changes
operationally — but the reason is recorded truthfully, and the day someone builds
a threshold, `cannot_tell` is structurally excluded from the autonomous side
rather than counted as clean.

**This is PR §1.11 applied to a customer-facing judgement rather than to a
checker.** Could-not-tell is a third state and is never folded into passed.

---

## 2. What this document does not establish

1. **It does not establish that SAIRNcode should compete on autonomy at all.**
   That is still the predecessor's §3 item and it is still Michael's. Nothing
   here argues for widening autonomy; it argues that *if* it widens, these are
   the boundaries it has to bring with it.
2. **No competitor claim is repeated here.** Every figure about CodaMetrix, Nym,
   Fathom or AKASA in the predecessor document came from WebSearch snippets that
   the source audits themselves flag as not directly read. This document makes no
   competitive claim of any kind.
3. **The correction in §0 is about a document, not about a person's judgement.**
   The predecessor's §0 — that SAIRNcode's explainability is span-level *and
   independently verified*, which is a stronger claim than any vendor in either
   audit makes — was checked today and holds. It is the autonomy measurement that
   was wrong, and it was wrong in the same direction: it understated what this app
   already does.
