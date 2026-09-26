# SAIRNvet exotic dosing — what the formulary actually rests on

**2026-09-26 (cc).** Two questions were asked: whether SAIRNvet's exotic-patients
panel had been through the fabrication-hardening pass, and whether the
exotic-species dosing figures had any external reference behind them.

The first premise is **false** and is corrected below. The second found a real
defect that is larger than exotics and is fixed here.

---

## 1. The exotic-patients PANEL was already hardened — measured, not assumed

`exotic-patients` is one of eight `SV_SPECIES_GROUPS` entries rendered by
`svRenderSpeciesPanel()`. It is a species-filtered view of the real roster:
every KPI is computed from a field that exists on a patient record (Active
Patients, New This Month, Avg Visits/Yr, Chart Completion), and the empty state
is a sentence rather than a blank box.

**Measured over the whole file:** `class="kpi-value"` cells containing a literal
with no JS interpolation — **0**. There is no hardcoded KPI anywhere in
`sairnvet.html`. The 2026-08-30 and 2026-09-01 sweeps did this panel; the
comment above `SV_SPECIES_GROUPS` records which invented figures were dropped
rather than re-fabricated ($156K, $1,640, $198K, $89K, $76K, $52K, $18K, and
`zoo-patients`' Revenue YTD $64K).

**So the panel is not the unhardened surface. The formulary is.**

---

## 2. The unhardened surface: a green tick that meant nothing

The Drug Database screen rendered, per row:

```js
var status = d.needsReview ? '⚠ Needs Review' : '✓ Verified';
```

`needsReview:false` is **the absence of a flag**. The screen read it as **the
presence of a verification**. Measured:

| | count |
|---|---|
| rows in `VET_DRUGS` | 485 |
| rows displaying **✓ Verified** | **284** |
| rows carrying any source field | **0** — the schema had none |
| controlled substances displaying ✓ Verified | 20 |

There was no `reference` field on any row, no citation anywhere in the file, and
therefore nothing that could have been checked. A clinician reading a mg/kg
figure was told it had been verified, with no way to ask against what.

**And the same claim was in nine other places**, the worst being the system
prompt of the AI Dosing Calculator:

> you may ONLY use the **verified database record** and calculation provided
> below as your source of truth for the numeric dose

That puts the word in the model's mouth and therefore in front of the vet.

### The exotic half specifically

73 of the 485 rows are exotic/zoo/avian/reptile species. **68 carry
`needsReview:true`** and refuse a numeric dose — that half was already honest,
and one entry is exemplary: Amoxicillin / *exotic (unspecified)* stores
`"Consult species-specific formulary"` with a flag naming Carpenter's Exotic
Animal Formulary and saying not to extrapolate from the dog/cat dose.

**Five exotic rows displayed ✓ Verified.** Those are the five this audit went
looking for a source for.

**One thing the structured fields hide, and it matters:** `doseMin`/`doseMax`
are null on almost every exotic row — honest, because nothing machine-readable
should be multiplied by a weight. But the human-readable `dose` string still
carries a specific range (`"0.5-1mg/kg slow IV"`, `"25-35mg/kg BID"`,
`"2-5mg/kg"`). **The clinician reads the string.** So "no numeric dose" in the
data model is not the same as "no number on the screen", and roughly 50 exotic
rows put a number in front of a reader while the machine fields say there isn't
one.

---

## 3. What was verified, and what was not

Every citation below was **retrieved and quoted**, not recalled. Anything that
could not be retrieved is recorded as unverified rather than assumed correct.

### VERIFIED — 3 rows

**Chlorhexidine 0.05% and povidone-iodine lavage, exotic species**

> "If antiseptic solutions are chosen, 0.05% chlorhexidine and 0.5 or 1%
> povidone-iodine would be considered appropriate."

Mickelson MA, Mans C, Colopy SA. *Principles of Wound Management and Wound
Healing in the Exotic Pets.* Vet Clin North Am Exot Anim Pract. 2016
Jan;19(1):33–53. doi:10.1016/j.cvex.2015.08.002. PMID 26611923.

- `Chlorhexidine Solution` / *other/exotic/zoo species* stored **0.05%** — matches.
- `Betadine (Povidone-Iodine)` / *other/exotic/zoo species* stored
  **"Dilute 1:10 for lavage"**. **A ratio is not a dose without its starting
  strength.** 1:10 is 1% only if the bottle is the usual 10% stock, and the
  string never said so. Rewritten to **"Dilute to 1% for lavage (1:10 from 10%
  stock)"**, which is what the source actually supports.

**Deslorelin 4.7 mg implant, ferret**

> "Suprelorin® F (4.7 mg) Implant is indicated for the management of adrenal
> gland cortical disease in the male and female domestic ferret." … "The
> recommended dosage is one, 4.7 mg implant per ferret every 12 months."

FDA-approved label, Suprelorin F, NADA 141-325, via DailyMed setid
`aa5776dc-277e-4a5e-885f-6e3f05c8404b`, label updated 2022-01-07. This is the
strongest class of source available to any row in this table: an approved label
for this exact species and indication.

### NOT VERIFIED — flagged, not assumed

**Sevoflurane "2-4% maintenance", `bird` and `exotic (small mammal/reptile)`**

Searched Merck/MSD Veterinary Manual (avian and reptile clinical procedures) and
PubMed Central. The avian anaesthesia literature retrieved confirms sevoflurane
and isoflurane are the agents of choice for maintenance in birds and describes
their properties, but **no source retrieved states a 2–4% maintenance
concentration for birds or for exotic small mammals/reptiles**, and minimum
anaesthetic concentration is reported per species rather than as one range. The
figure may well be a reasonable clinical starting point; **this audit could not
source it, so it is not labelled as sourced.** These two rows now display
**⚠ No source recorded**.

**The other 479 rows** carry no reference either. That is a disclosure, not a
finding about any particular dose — most are companion-animal figures that are
uncontroversial in practice. What changed is that the app no longer claims
otherwise.

---

## 4. What was changed

1. **`reference` field added to `VET_DRUGS`.** Present on 3 rows; absent means
   no source is recorded.
2. **The badge is three-state now**, because two could not express the truth:
   - `⚠ Needs Review` — flagged (unchanged, 201 rows)
   - `✓ Referenced` — cites a source, shown in the tooltip (3 rows)
   - `⚠ No source recorded` — neither, **and deliberately not green** (281 rows)
3. **The AI grounding path stops saying "verified"** in all nine places,
   including the system prompt, which now instructs the model to *tell the user
   plainly* when a figure is unsourced. The grounding context passes the row's
   sourcing through, so a cited row and an uncited one no longer look identical
   to the model.
4. **"Verified calculation" → "Calculated in-app from the stored range".** The
   multiplication is something the app genuinely performed; the mg/kg range it
   multiplied may have no source. The old wording transferred the confidence of
   the arithmetic onto its input.
5. **`tests/sairnvet_formulary_source_honesty.js`, 14 arms**, driven red six
   ways — see below.

**Not changed: no dose figure was edited**, except the povidone-iodine string,
where the change makes the instruction match its own citation. Re-sourcing 479
rows is a veterinary review, not a code change, and pretending otherwise would
be the same defect in the other direction.

---

## 5. The ablation

The wording is the only thing holding the honesty, and wording regrows. Six
mutations, each applied alone with the file restored after:

| mutation | result |
|---|---|
| M1 green `✓ Verified` restored on an unsourced row | 13 passed, **1 FAILED** |
| M2 system prompt calls the record verified again | 13 passed, **1 FAILED** |
| M3 calculator box says "Verified calculation" again | 13 passed, **1 FAILED** |
| M4 dashboard sentence restored | 13 passed, **1 FAILED** |
| M5 a reference loses its retrieval date | 13 passed, **1 FAILED** |
| M6 the grounding stops branching on `m.reference` | **14 passed, 0 failed** ← |

**M6 initially caught nothing, and that is recorded rather than quietly fixed.**
The arm asserted `/m\.reference/` appeared near the grounding assignment.
`m.reference` appears **twice** there — once as the ternary test, once inside
the true branch — so replacing the *test* with `false` left the arm green while
the model stopped being told anything about sourcing. A presence check where a
dependency check was meant. The arm now asserts the branch condition and the
existence of the uncited branch; M6 fails 13/1 with it.

---

## 6. What this does NOT claim

- **No dose here is asserted to be correct.** A citation is evidence that
  somebody looked something up. Three sourced rows out of 485 is a disclosure of
  coverage, not a coverage claim.
- **The unsourced rows are not asserted to be wrong.** "No source recorded" says
  exactly what it says.
- **Carpenter's Exotic Animal Formulary was not consulted.** It is the standard
  reference for this material, it is a book, and nothing in this pass had access
  to it. The app's own Amoxicillin/exotic flag already names it, which is the
  right pointer; sourcing the exotic rows against it is the real remedy and is
  a veterinary task, not a code one.
- **Nothing was checked against a live deployment.** This is a read of
  `sairnvet.html` in this repo.
