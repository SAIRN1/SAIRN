# Multi-slot trigger documents — design for the four cross-appeal rows

**Scoped 2026-09-02 (Hank), on Michael's direction, BEFORE building.** This is a
schema change to live rule data on a legal-deadline product, so the design is
written down and reviewed first. Nothing in this document has been implemented.

Companion to the single-slot discriminator shipped the same day (`567d661`
mechanism, `77236c2` declarations), which covers 45 of the 48 rows whose trigger
names one specific document. These are the other four.

---

## 1. The four rows, and what they actually are

| Row | Mechanism | Limb 1 | Limb 2 |
|---|---|---|---|
| `ny-cplr-5513c-cross-appeal` | `resolve_periods: later_of`, per-limb counts | `service_of_the_adverse_partys_notice_of_appeal` (10 d) | **`service_upon_appellant_of_judgment_with_written_notice_of_entry`** (30 d) |
| `oh-appr-4B1-cross-appeal` | `resolve_periods: later_of` | **`entry_of_final_order`** (30 d) | `filing_of_the_first_notice_of_appeal` (10 d) |
| `tx-trap-261d-cross-appeal-ordinary` | `resolve_periods: later_of` | **`signing_of_the_judgment`** (30 d) | `filing_of_the_first_notice_of_appeal` (14 d) |
| `frap-4b1A-criminal-notice-of-appeal` | `resolve: later_of`, ONE shared count (14 d) | **`entry_of_judgment_or_order_being_appealed`** | `filing_of_government_notice_of_appeal` |

**TWO DIFFERENT MULTI-TRIGGER MECHANISMS ARE IN PLAY AND THE DESIGN MUST COVER
BOTH.** `resolve_periods` gives each limb its own count and compares the
resulting dates; `resolve` shares one count and compares the trigger dates. Only
FRAP 4(b)(1)(A) uses the second.

### The finding that shrinks the problem

**Of the eight limbs, exactly four are terms of art.** Bolded above. The other
four — service of the adverse party's notice of appeal, and the filing of a
notice of appeal (three times) — name an act with one unambiguous date. A party
either filed a notice on a day or did not.

**So this is not "one slot per limb". It is "a slot for the limbs that need
one", and each of these four rows needs exactly ONE.** A design that mandated a
declaration per limb would force four fabricated declarations saying "this is
the date the notice was filed, not the date it was filed", which is noise that
trains a reader to skim.

---

## 2. Schema

A new **optional** row field, used only on multi-trigger rules:

```json
"trigger_documents": {
  "signing_of_the_judgment": {
    "id": "signing_of_the_judgment",
    "label": "the date the trial court SIGNED the judgment",
    "not_the": "the date it was entered on the docket, filed by the clerk, or mailed",
    "authority": "Tex. R. App. P. 26.1(d)",
    "on_unconfirmed": "refuse"
  }
}
```

- **Keyed by the limb's `event` string.** That key is what the caller already
  uses to supply `trigger_dates`, and the API already reports it per row as
  `requires_dates` — so the caller has the vocabulary before it asks.
- **A limb with no entry is unguarded, deliberately**, and that is the normal
  case for four of the eight.
- **The declaration shape is byte-identical to the singular `trigger_document`**
  so one validator serves both and there is no second vocabulary to learn.

### Caller input

```json
"trigger_documents": { "signing_of_the_judgment": "signing_of_the_judgment" }
```

A map from **limb event → the document id the caller affirms** the date supplied
for that limb came from.

**Why a map and not a list of confirmed events.** A bare
`["signing_of_the_judgment"]` can only express *"I confirm"*, never *"I confirm
it is THIS document"* — which throws away the MISMATCH refusal the single-slot
design deliberately has. That refusal is not theoretical here: Ohio's limb runs
from **entry**, Texas's from **signing**, and a caller who has both matters open
can affirm the wrong one. An affirmative wrong answer is worse than silence, and
the map preserves the ability to say so.

### A row carries the singular or the plural, never both

`trigger_document` is for a string trigger; `trigger_documents` is for an object
trigger. The write-time validator rejects a row carrying both, and rejects the
plural on a single-trigger row, so the two cannot drift into overlapping
meanings.

---

## 3. Refusal semantics — all-or-nothing, and why

**If any guarded limb is unconfirmed and declares `refuse`, the whole
computation refuses.** No partial answer, no "computed from the limbs we could
verify".

The reason is the mechanism itself: **`later_of` means an unverified limb can
always be the one that governs.** Computing the other limb and returning it
would be returning a date that is only correct if the unverified limb happens to
lose — which cannot be known without using the unverified date. That is the same
reasoning that put the single-slot guard before the arithmetic rather than
after.

All four rows are appellate, so all four guarded limbs take `refuse`. The
`warn` path is still reachable by the schema and is left available for a future
civil multi-trigger row rather than being designed out.

---

## 4. THE IMPLEMENTATION CONSTRAINT THAT MATTERS MOST

**The multi-slot guard cannot sit where the single-slot guard sits.**

Today `resolveTriggerDocument` runs at `deadline-engine.js:4254`, after the
winning rule is chosen and before any arithmetic — which is correct for a
single-trigger rule, where nothing is computed until then.

For a multi-trigger rule that is **44 lines too late**. `resolveTrigger` is
called at `:4210`, and for a `resolve_periods` spec it dispatches to
`resolvePeriods`, which calls `computeBasePeriod` at `:3992` **for every limb**.
By the time execution reaches `:4254`, every limb's date has already been
computed from dates the caller was never asked to verify.

**So the plural guard must run before the `resolveTrigger` loop**, on each
matching rule, and refuse there. That is the single most important detail in
this document: putting it in the obvious place beside its sibling would produce
a guard that reads correctly, tests green on the refusal code, and still does
the arithmetic it exists to prevent.

---

## 5. Blast radius

- **4 rows, 4 declarations** — one slot each, not eight.
- **1 new row field, 1 new caller input, 1 validator branch, 1 relocated guard.**
- **Zero existing assertions change.** Which is the second finding, below.

### These four rows have NO test coverage at all

Verified 2026-09-02: no file in `api/_lib/*.test.js` references any of the four
rule ids or any of their four trigger spec ids. **All four are LIVE** — each
appears in `rules_status` on `LAW-PINNACLE-2026` with its `requires_dates` pair.

So four appellate cross-appeal rows are answering today with no assertion
anywhere that they answer correctly, and the reason the discriminator work did
not break them is that nothing was testing them. **The build should add
coverage for the rows themselves — the `later_of` arithmetic on both limbs, both
mechanisms — and not only for the new guard.** That is arguably worth doing even
if the multi-slot design is rejected.

---

## 6. What is NOT proposed

- **No migration of the 45 single-slot rows to the plural form.** They are
  correct, tested and live; converting them would be churn with a real chance of
  introducing exactly the kind of defect this week has been spent removing.
- **No per-limb `warn`/`refuse` mixing within one row** in the first pass. The
  schema permits it; no current row needs it, and mixing raises a question
  (does a warned limb still return a date when a refused limb blocks?) that has
  no real instance to reason from.
- **No change to `requires_dates`** in the API response. It already names the
  limbs; the declaration is additive.

---

## 7. Open question for Michael

**Should the FRAP 4(b)(1)(A) criminal row be in scope at all?** It is the only
one of the four using `resolve` rather than `resolve_periods`, the only criminal
row, and its guarded limb — *entry of the judgment or order being appealed* — is
the same term of art already declared on the two civil FRAP rows. Including it
is consistent; excluding it would leave one row of the four unguarded for no
reason I can see. **Recommendation: include it**, and the design above does.
