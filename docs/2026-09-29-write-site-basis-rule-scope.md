# "Only reading a resource's reads tells you what it controls" — the rule, measured

**2026-09-29 (Hank).** Item 16 of queue23. **SCOPE ONLY — nothing built.** The
candidate rule was **run read-only over the current table** and the numbers below
are measured, not estimated.

---

## The rule

> **`criticality_tier_check.py` FAILS a row whose integrity or confidentiality
> basis cites only WRITE sites.**

It comes from a measured failure. `msb_sale_hours` sat at Tier B for seven weeks
on a cell that said *"nothing here computes against a statutory window or refuses
a sale outside one."* The cell cited `:4483` and `:4903` — **both correct on the
day, and both write sites.** The two READ sites are `msbIsAlcoholSaleAllowedNow()`
and a checkout path that **refuses an alcohol sale**. From the write side a
control input is indistinguishable from a display configuration.

---

## Measured over the current 391 rows

| Population | Rows |
|---|---|
| Rows with a two-axis header | **391** |
| **No citation at all** | **209** |
| Cites **both** read and write sides | 81 |
| Cites **read** side only | 19 |
| **Cites WRITE side only — the rule would fail these** | **82** |

**82 hits, of which 45 are Tier A.**

### The first thing the measurement says, and it is not about the 82

**209 of 391 rows cite no line at all.** That is **53% of the table outside this
rule entirely** — including `alf_incidents`, `alf_billing`, `bld_costs`,
`alf_compliance_rules` and 197 more, many of them Tier A.

**A rule that fires on 82 rows while 209 are exempt for having less evidence is
backwards.** It would put pressure on exactly the cells that already did the most
work — the ones that bothered to cite a line — and none on the cells that cite
nothing. **That is the single strongest argument against building it as stated**,
and it only appeared because the rule was run before it was recommended.

---

## The false-positive shapes, from reading the hits

### 1. The classifier cannot see past the first clause — the dominant shape

`msb_sales` is a hit. Its cell:

> *"`:4649` writes `{cart_type, items, total, payment, age_verified, employee,
> timestamp, voided}`. **MONEY on its face** — `total` and `payment`."*

**That cell is correct and complete.** The resource's integrity risk *is* on its
face: a sale total that is wrong is wrong. **There is no read to cite** — the
harm does not depend on a consumer. Requiring one would force a citation that
does not exist, and the honest response would be to invent one.

**Any row whose harm is intrinsic to the stored value falls here**, which is most
money rows. That is a large fraction of the 82.

### 2. Rows where the read is described but not cited

`rf_settings` is a hit, and its cell is one of the strongest in the table:

> *"THIS ROW WAS FILED AS A PREFERENCE AND IS A DECISION RULE ON INSURANCE
> CLAIMS."*

A decision rule is **by definition** about what reads it. The cell makes the
read-side argument in words and attaches its line number to the write. **The rule
as stated fails a row that did the analysis correctly and put the colon in the
wrong place** — a formatting test wearing a methodology test's clothes.

### 3. Vocabulary, not substance

My classifier reads words near each citation. `sb_bud` is a hit because its
read-side argument lives in a clause my regex did not match. **A real
implementation inherits this**, and it is the direction that matters: it
**over**-fires, and an over-firing gate in a 391-row table is one somebody
switches off.

### 4. The one the rule genuinely catches

`sdn_samples` and `sf_service_hours` are hits and both are rows where the write
was read and the consumers were not. **That is the `msb_sale_hours` shape and it
is real.** The rule works — it is just surrounded by three false-positive classes
that outnumber it.

---

## What it would take to build it properly

1. **A structured citation**, not a bare `:NNNN` — `write:4483`, `read:4643`.
   The cell already knows which it means; the format throws it away. **This is
   the whole fix**, and it is a table-format change across 391 rows, not a
   checker change.
2. **An explicit `intrinsic` marker** for §1 — a row declaring that its harm does
   not depend on a consumer, which is a real and common claim that the current
   format cannot express.
3. **Then** the checker is trivial: fail a row with write citations, no read
   citation, and no `intrinsic` marker.

Steps 1 and 2 are the work. Step 3 is twenty lines.

---

## Recommendation: **DO NOT BUILD THE RULE. Build the smallest thing that earns it.**

The rule as stated would fire on 82 rows, of which I would expect **fewer than a
quarter to be real** — while 209 rows with no citation at all sail past. It would
be switched off inside a week, and it would take the real finding with it.

**Build instead, in this order:**

**(a) A `NO CITATION` report — today, report-only, ten lines.** 209 rows assert a
basis and cite nothing. That is a bigger, cleaner, unambiguous population, it
needs no format change, and it has **no false-positive shape at all**: either a
row cites a line or it does not.

**(b) The `write:` / `read:` citation prefix, on NEW and EDITED rows only.** No
migration of 391 rows. Today's six edits would have carried it. When the prefixed
population is large enough to mean something, the rule from item 16 becomes
twenty lines with no classifier and no false positives.

**(c) Only then, the rule.**

**What this costs by not building it now:** the `msb_sale_hours` shape stays
undetectable by machine until (b) has run for a while. **That is acceptable
because the human version of the check now exists** — it is written into
`msb_sale_hours`' own cell, into `sv_wildliferehab`'s, and into the open-work
index row, in the same words each time:

> **Reading a resource's WRITES tells you what it CONTAINS; only reading its
> READS tells you what it CONTROLS.**

A sentence in three cells a reviewer will hit is worth more this month than a gate
firing on 82 rows where 60 of them are right.
