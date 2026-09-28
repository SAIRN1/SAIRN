# SAIRNcode against CodaMetrix and Nym Health — the scoped build list

**2026-09-28 (Cody). SCOPING ONLY. Nothing here is built, and nothing here should
be built from this document alone — items 3 and 6 need a decision that is not an
engineering decision.**

Scoped against the two cloud-research audits on PR branch `claude/wizardly-ride-wtun13`:

- `docs/cloud-research/sairncode-external-competitive-gap-audit-2026-09-26.md` (`130f8408`)
- `docs/cloud-research/sairncode-autonomous-coding-wide-lens-supplement-2026-09-26.md` (`1adefca0`)

**Every "already built" below was MEASURED in `sairncode.html` at
`origin/main` today, not taken from the audits.** The audits describe the market;
they do not describe this app's current state, and two of their framings turn out
to be wrong about it in SAIRNcode's favour.

---

## 0. The correction that changes the whole list

**The audits treat explainability as SAIRNcode's differentiator-under-threat and
could not determine whether Nym's evidence linkage reaches span granularity. That
question is still open about Nym — but it is SETTLED about SAIRNcode, and the
answer moves the gap.**

Measured in `sairncode.html`:

| Capability | State | Where |
|---|---|---|
| Verbatim quoted span per suggested code | **BUILT** | `suggestCodesFromNote()`; the phrase is required from the model |
| The span is INDEPENDENTLY verified against the pasted note | **BUILT** | client re-checks presence, case/whitespace-normalised, and flags any citation it cannot verify rather than trusting the claim |
| The citation + reasoning + rule are a STORED record, not screen-only | **BUILT** | Coded Items queue, `:855` note — *"suggestCodesFromNote() was already doing the hard part; it just threw the result away"* |
| Confidence derived from mechanical signals only | **BUILT** | `scDeriveCodedItemConfidence()` — missing citation, unverifiable citation, missing supporting rule. **Never a percentage asked of the model** |
| Human review recorded with who and when | **BUILT** | `reviewed_by` written on the item |
| GP / GN / GO plan-of-care modifier logic | **BUILT** | `:8529`, including the OT/SLP redirect — the audit's "GP-modifier gap" is closed |
| Denial reconciliation with no probability score | **BUILT** this week | `api/_lib/sc-denial-reconcile.js` |

**So the gap is not explainability and not the GP modifier.** SAIRNcode's
explainability is span-level *and independently checked*, which is a stronger
claim than any vendor in either audit makes — none of them describes verifying its
own model's citation.

**The gap is AUTONOMY.** Measured: `autonomous` appears **0 times** in
`sairncode.html`, `routing` **0 times**, `audit trail` **0 times**. There is a
review queue and there is a derived confidence, and **nothing connects them**.
CodaMetrix's product *is* that connection — confidence-based routing to a human
below a tunable threshold — and Nym's is the same with a more aggressive default.

---

## 1. The scoped list, in dependency order

### Item 1 — Route on the confidence that already exists · **S** · no new judgement
`scDeriveCodedItemConfidence()` computes a band and nothing acts on it. Add a
configured threshold and a routing decision per coded item: below it, the item
waits for a human (which is today's behaviour for everything); at or above it, the
item is marked auto-accepted **with the signals that made it so**.

**Why this is small:** the confidence, the queue, the stored citation and the
`reviewed_by` field all exist. This is the edge between them.

**Why it is the first item:** every figure a buyer asks for in this category —
automation rate, review volume, accuracy on the auto-accepted subset — is
uncomputable until an item knows which side of a line it fell on.

**The refusal it must carry:** an item whose citation could not be verified must
never be auto-accepted whatever the band says. That is not a threshold question.

### Item 2 — Publish the automation rate as a MEASURED fraction with its denominator · **S**
Once item 1 exists: auto-accepted / total coded, per specialty and per month,
with the denominator printed beside it.

**The whole competitive claim in this category is a percentage**, and every
percentage in both audits is vendor-published: CodaMetrix "above 96% on average"
while its own customer UMass Memorial reports **86%**; Fathom 95.5%; Nym "50–70%
with zero human touch, varying by specialty". **The spread between a vendor figure
and its own customer's figure is the finding**, and SAIRNcode can report a number
that is its customer's by construction because it is computed from that
customer's own queue.

**The refusal it must carry:** no automation rate before there is a month of real
routed items. A rate over four items is not a rate — and the academic lens in the
supplement is exactly this point, published accuracy for AI coding swinging 34%
to 99% on task design alone.

### Item 3 — Decide the DEFAULT threshold · **DECISION, NOT A BUILD** · Michael
Item 1 needs a default. The default is a clinical-risk and liability decision, not
a tuning parameter: it is the line above which no human reads a code that goes to
a payer under the practice's NPI.

**Scoped, not chosen.** Three defensible defaults with different exposure, and the
honest recommendation is the most conservative until item 2 has data:

1. **Nothing auto-accepts** (threshold above the top band). Ships item 1's
   machinery and changes no behaviour, so item 2 can measure what *would* have
   been auto-accepted before anything is.
2. Auto-accept only items with a verified citation **and** a matched rule **and**
   no modifier finding.
3. A tunable number the practice sets.

**Option 1 is the recommendation** and it is a real option, not a hedge: it makes
the automation rate measurable *counterfactually* before a single claim is routed,
which is the only way to choose 2 or 3 on evidence rather than on nerve.

### Item 4 — Name the auto-accepted subset in the audit export · **XS**
Whatever an auto-accepted item is, an auditor must be able to select them. One
field and one filter.

**Why it is separate from item 1:** it is the item that makes items 1–3 defensible
after the fact, and it is the one that gets forgotten because nothing on screen
needs it.

### Item 5 — A head-to-head accuracy figure SAIRNcode can actually stand behind · **M**
Both audits say no independently-run head-to-head against SAIRNcode exists or was
attempted, and the supplement's §4 says the one genuine RCT found **no significant
accuracy gain** from AI assistance at all.

**Scoped as measurement, not marketing:** on the auto-accepted subset only, the
rate at which a later human edit changes the code. That is a real,
customer-specific, falsifiable number, and it is the number every vendor figure in
these audits is not.

**Do not build this before item 2.** It shares item 2's denominator problem and
adds a second one: a later edit is not proof the original was wrong.

### Item 6 — CPT licensing for customer-uploaded code sets · **BLOCKED, LEGAL** · not engineering
The supplement's §3 raises this and says plainly it is **unresolved
industry-wide** — no vendor in the research, CodaMetrix and Nym included, offers a
public answer.

**Nothing to build and nothing to claim.** It needs a legal read against
SAIRNcode's actual data-handling architecture. Named here so it is not discovered
during a sale.

---

## 2. What is deliberately NOT on the list

- **Anything called "autonomous coding".** SAIRNcode does not do it today and
  items 1–4 do not make it do it; they make the *question* measurable. Adopting
  the category's language before the measurement exists is the fabricated-KPI
  shape with a market-facing label.
- **A denial-probability score.** Both audits independently strengthen the case
  for continuing to refuse: real competitors ship the percentage, none discloses
  its calibration, and the closest analogue — payer-side AI denial decisions — is
  under a ProPublica investigation, two live federal suits, a GAO warning, and a
  state-AG settlement that found a health-AI vendor's self-reported accuracy
  *"likely inaccurate"*. **This is now the best-evidenced engineering decision in
  the app and should be said to buyers in those terms.**
- **Explainability work.** It is built and stronger than the category's, per §0.
  The only open question is about *Nym*, not about SAIRNcode, and it is answered by
  a direct read of Nym's product — research, not build.
- **The GP modifier.** Already built, including the OT/SLP redirect the audit did
  not know about.

---

## 3. Two things a reader must not take from this document

1. **It does not establish that items 1–5 are worth doing.** It establishes that
   they are the *shape* of the gap and that they are small in the order given.
   Whether SAIRNcode should compete in the autonomy category at all is item 3's
   question one level up, and it is Michael's.
2. **Every competitor figure here is from the audits, which are almost entirely
   WebSearch snippets rather than direct page reads** — both documents say so in
   their own §0.1. No figure about CodaMetrix, Nym, Fathom or AKASA in this
   document was independently verified by me, and none should be quoted to a buyer
   without one.
