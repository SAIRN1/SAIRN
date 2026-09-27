# SAIRNvet food-animal sourcing — four drugs, eight rows, and the cattle figure on the swine row

**2026-09-27, CC.** Continuing the formulary citation pass. Coverage moves from
**7 of 485 rows to 15**. Every citation below was retrieved from DailyMed and
quoted verbatim into the row's own `reference` field; nothing was recalled.

**One defect came back three times in four drugs: the swine row carried the
cattle route, the cattle dose, or both.** That is the species-copy class the app
already warns about — and the app's own detector is blind to half of it, for a
reason worth recording.

---

## 1. Why these eight rows and not eight others

The 470 uncited rows are not equal. Two populations carry consequences a
companion-animal dosing error does not:

- **Food-animal rows** — a wrong dose, route or withdrawal puts drug residue in
  meat or milk. The harm lands on somebody who never saw the app.
- **Controlled substances** — 33 uncited, and a separate pass.

69 uncited rows carried `withdrawalStatus: "verify_required"` with
`withdrawalMeat: null` and `withdrawalMilk: null`. **The labels have those
numbers.** These four drugs — tulathromycin, florfenicol, ceftiofur,
oxytetracycline — are the injectable antimicrobials most used in cattle and
swine, and each has a current FDA-approved label on DailyMed.

---

## 2. What the labels said, and what the rows said

### Tulathromycin — the route was swapped between species

DRAXXIN, NADA 141-244. Cattle: *"Inject **subcutaneously** as a single dose in
the neck at a dosage of 2.5 mg/kg."* Swine: *"Inject **intramuscularly** as a
single dose in the neck at a dosage of 2.5 mg/kg."*

**Both rows read route `SC/IM`** — which offers each species the other one's
route. The dose, 2.5 mg/kg, is correct and identical in both.

Withdrawal: **18 days** cattle, **5 days** swine. Not the same number; a row
carrying one for both would be wrong by 13 days.

### Florfenicol — the dose is tied to the route, and the swine row had the cattle figure

NUFLOR / NUFLOR-S, NADA 141-063.

- Cattle BRD/foot rot: **20 mg/kg IM**, second dose 48 h later.
- Cattle BRD control at high risk: **40 mg/kg SC, once**.
- Swine: **15 mg/kg IM**, second dose 48 h later, neck musculature only.
- Withdrawal: **28 days after IM, 38 days after SC** in cattle. **11 days** in
  swine.

**Both rows read `"20-40mg/kg"`, route `"IM/SC"`.**

On the cattle row that is **not a range**. 20 is the IM figure and 40 is the SC
figure, and reading them as interchangeable permits **40 mg/kg IM** (double the
labelled IM dose) or **20 mg/kg SC** (half the labelled SC dose) — and either
way the withdrawal the reader applies is the wrong one of 28 and 38 days.

On the swine row it is simply the cattle figure: the swine label is 15 mg/kg, so
the stored range ran from **33% to 167% above it**, and SC is not a labelled
swine route.

### Ceftiofur — the swine row had the cattle dose, and this one UNDER-doses

EXCENEL RTU EZ, NADA 141-288, revised July 2022.

- Cattle: **1.1–2.2 mg CE/kg**, IM or SC, daily × 3 days.
- Swine: **3–5 mg CE/kg**, IM, daily × 3 days.
- Withdrawal: cattle **4 days**, **no milk discard required**. Swine **4 days at
  an injection-site volume of 5 mL or less, 6 days above 5 mL up to 15 mL**.

**Both rows read `"1-2.2mg/kg SID"`, route `"IM/SC"`** — the cattle figure on
both, and the cattle low bound was itself 1 where the label minimum is 1.1.

**The direction is recorded because it is the opposite of the florfenicol one.**
The stored swine figure is roughly a third to two thirds of the labelled dose:
an **under**-dose, which is a treatment-failure and resistance risk rather than a
residue one. Two errors of the same shape with opposite consequences, and a
write-up that called them both "wrong dose" would lose that.

### Oxytetracycline — a single long-acting dose and a daily dose are not one range

LIQUAMYCIN LA-200, NADA 113-232.

- Cattle: **9 mg/lb (≈20 mg/kg) as a SINGLE long-acting dose** IM or SC; **or
  3–5 mg/lb/day (≈6.6–11 mg/kg/day)** IV, SC or IM, up to 4 consecutive days.
  The label adds: *"Intramuscular administration is not recommended according to
  Beef Quality Assurance Guidelines."*
- Swine: the same two regimens, **intramuscular only**, neck region.
- Withdrawal: **28 days** meat, **96 hours** milk.
- *"Rapid intravenous administration may result in animal collapse."*

**Both rows read `"10-20mg/kg SID"`, route `"IM/IV"`.** The two regimens differ
in **frequency**, not only in size, so flattening them into a once-daily range
invites **20 mg/kg every day**, which is neither. The cattle row also omitted
SC, a labelled route; the swine row included IV, which is **not** labelled for
swine in this product.

---

## 3. What was changed, and what was deliberately not

**Routes corrected to the label** on all eight rows, following the precedent set
by the flunixin cattle row earlier the same day. **Doses corrected** where the
stored figure was the other species' number or below the label minimum.

**Two rows were deliberately left with `doseMin`/`doseMax` NULL** —
florfenicol/cattle and both oxytetracycline rows. The calculator refuses when
either bound is null (`sairnvet.html`, `if(m.needsReview || m.doseMin===null ||
m.doseMax===null)`), which is the outcome wanted: a min/max spanning 20 and 40,
or 10 and 20, would let the calculator **multiply the false range by a body
weight** and print it. A guard that removes a misleading range from the prose
and rebuilds it in the numeric fields has fixed nothing.

**`needsReview` is now false on all eight**, because the suite requires it: a
referenced row that is also flagged shows the amber badge and **hides its own
citation**. Refusal still comes from the null bounds where it should.

**Every withdrawal string names its PRODUCT**, not just its number. A withdrawal
period belongs to a product, not to a drug name, and these rows are generic:
"28 days" beside "Oxytetracycline" reads as a fact about oxytetracycline, and it
is a fact about LIQUAMYCIN LA-200. A short-acting injectable of the same drug
has a different one. Each `reference` also names the products it does **not**
cover — INCREXXA, MACROSYN, AROVYN, VACASAN and RESPIRMYCIN for tulathromycin;
NAXCEL, EXCEDE and SPECTRAMAST for ceftiofur.

---

## 4. The detector that cannot see this

`svCopiedDoseIndex()` already flags a figure repeated across a drug's species
rows — 117 drug names, 309 of 485 rows. It is the right detector and it would
have caught the florfenicol and ceftiofur rows on the dose.

**It cannot see the tulathromycin one at all, and the reason is structural: it
keys on the DOSE STRING.** Tulathromycin's dose is genuinely identical in cattle
and swine; only the route differs. A detector watching for a copied figure is
blind to a copied route by construction, and on a food animal the route is the
food-safety fact — it drives injection-site residue and it is what the
withdrawal period was established for.

That gap is held by a named arm rather than by a new detector. A route-copy
detector would fire on every legitimately shared route in the table and be
switched off within a week, which is the same argument the copy marker itself
records for warning rather than refusing.

---

## 5. The arms, and the ablation

Five arms added to `tests/sairnvet_formulary_source_honesty.js` (34 → 39). Each
was driven red by a single mutation, applied alone, with the file restored
after:

| mutation | result |
|---|---|
| tulathromycin route swap restored (`SC/IM`) | 38 passed, **1 FAILED** |
| florfenicol swine dose back to the cattle figure | 38 passed, **1 FAILED** |
| florfenicol cattle regains numeric bounds | 38 passed, **1 FAILED** |
| ceftiofur swine dose back to the cattle figure | 38 passed, **1 FAILED** |
| oxytetracycline swine route regains IV | 38 passed, **1 FAILED** |
| a withdrawal loses its product name | 38 passed, **1 FAILED** |

**The product-name control found a real row on its first run**, which is the
only reason it is worth having: `Flunixin Meglumine/cattle` carried a bare
`"4 days"` from the earlier pass. Now `"4 days (Banamine, NADA 101-479 —
established for the SLOW IV route only; other flunixin products and any
extra-label route may differ)"`.

---

## 6. What this does NOT claim

- **No dose here is asserted to be clinically correct.** A citation is evidence
  that somebody read a label. Where the stored figure and the label disagreed,
  the label was followed and the disagreement is written into the row's `flag`
  so a veterinarian can overrule it.
- **Extra-label use is legal and is not being called an error.** What was wrong
  is that the rows presented one species' labelled route and dose as the other
  species', with nothing saying so. An intentional extra-label choice is a
  different object from a copy nobody noticed.
- **15 of 485 is a disclosure, not coverage.** 470 rows still record no source.
- **One product per drug.** Each reference covers the specific NADA it names.
  Other approved products of the same drug have different doses, routes and
  withdrawal periods, and the references say so by name.
- **Nothing was checked against a live deployment before the push.** The
  post-push live read is recorded in the commit.
