# The povidone-iodine rows, read against the source itself — severity HIGH

**2026-09-29 (Cody). NO DOSE STRING WAS CHANGED.** This is a read and a verdict.
The edit is a clinical-content decision for whoever can own it.

## The source, retrieved

Mickelson MA, Mans C, Colopy SA. *Principles of Wound Management and Wound
Healing in the Exotic Pets.* Vet Clin North Am Exot Anim Pract. 2016
Jan;19(1):33–53. PMID 26611923 — read as
[PMC4663678](https://pmc.ncbi.nlm.nih.gov/articles/PMC4663678/).

**Section: DECONTAMINATION (LAVAGE).** Verbatim:

> "If antiseptic solutions are chosen, 0.05% chlorhexidine and **0.5 or 1%**
> povidone-iodine would be considered appropriate."

Two properties of that sentence, both checked against the article rather than
against the row that cites it:

1. **It gives povidone-iodine as a RANGE, not a figure** — `0.5 or 1%`.
2. **It is stated GENERALLY. It does not restrict the recommendation to exotic
   species.** The *article* is about exotic pets; the *sentence* is about
   concentrations.

## The four rows, as they stand

| species row | current dose string | reference attached |
|---|---|---|
| dog | `Dilute 1:10 for lavage` | none |
| cat | `Dilute 1:10 for lavage` | none |
| horse | `Dilute 1:10 for lavage` | none |
| other/exotic/zoo | `Dilute to 1% for lavage (1:10 from 10% stock) — generally safe across species at this dilution` | Mickelson 2016, quoted above |

## Is "Dilute to 1%" supported? NO — not as written

**The source supports `0.5–1%`. The row states `1%`.** A single figure at the top
of a two-value range is not what the evidence printed beside it says, and the row
gives the reader no way to see the difference. The honest string is the range:
*"dilute to 0.5–1% for lavage"*.

Three further things the read settles:

- **The `1:10 from 10% stock` parenthesis is arithmetically right and
  clinically conditional.** 1:10 of a 10% stock is 1%. It is *not* 1% from any
  other stock strength, and the row states the assumption — which is an
  improvement on the three unsourced rows that state only the ratio.
- **The exotic-only scoping is NOT supported by the sentence.** The quoted claim
  carries no species restriction, and the row's own text says *"generally safe
  across species at this dilution"* while the citation sits on that row alone.
  The dog, cat and horse rows show `⚠ No source recorded` against the same drug.
- **Chlorhexidine is the sharper case.** All four chlorhexidine rows read
  `0.05% flush or wipe` — byte-identical to the source's figure — and only the
  exotic row carries the citation. There is no clinical difference between the
  rows at all; the only difference is which one was annotated.

## SEVERITY: HIGH

Not because a patient is likely harmed by 1% rather than 0.5% — both are inside
the source's range. **It is HIGH because the app's one remaining green
"sourced" tick is on a row whose figure is narrower than its own quoted
evidence, on a dosing screen, after a change whose entire purpose was to stop the
app claiming more than it could show.** The failure mode is the one the change was
made to remove, in the place the change put its strongest claim.

## ONE-LINE VERDICT FOR CHAT

**Make all four povidone rows read `dilute to 0.5–1% for lavage (1:10 from 10%
stock)` and move the Mickelson citation onto all four povidone and all four
chlorhexidine rows — the source says a range and says it of no particular
species, and the app currently says a point and says it of one.**

## What this does not decide

Whether 0.5% or 1% is the better *practice* default, and whether a range on a
dosing line is clearer than a point. Both are clinical-judgement calls for a
veterinarian. This document establishes only what the cited source does and does
not support, which is the part that can be checked.
