# Item 66 — IBNR: how many defects are in there that nobody has found?

**2026-09-14 (Hank).** Scoping. **No reserve figure is produced, and the reason
is a missing field rather than a missing method.**

---

## 1. What IBNR needs, and what the register has

Incurred-But-Not-Reported estimation works off a **lag distribution**: for
claims already reported, how long did each take to surface. Fit the tail, apply
it to the exposure, and you have a reserve for what has been incurred and not
yet reported.

Applied to defects the lag is **injection date → discovery date**.

**The register records the discovery date and not the injection date.** Item 77
added `injection_phase` — `requirement` / `design` / `coding` / `config` — which
is **when in the lifecycle**, not **when in time**. It is the right field and it
is not this one. So there is no lag to fit, and any reserve produced from what
is here would be a number with no distribution under it.

## 2. What the data DOES support, measured

Discovery per day since the register opened, against commit volume. **Claim
churn is 49% of all commits**, so the substantive column is the honest
denominator and both are shown rather than the flattering one.

| Date | defects | commits | substantive | per 100 substantive |
|---|---|---|---|---|
| 2026-09-09 | 2 | 56 | 28 | 7.1 |
| 2026-09-10 | 21 | 270 | 142 | 14.8 |
| 2026-09-11 | 10 | 90 | 43 | 23.3 |
| 2026-09-12 | 6 | 100 | 54 | 11.1 |
| 2026-09-13 | 18 | 244 | 134 | 13.4 |
| 2026-09-14 | 10 | 184 | 84 | 11.9 |

**Six days, ~490 substantive commits, and the normalised find rate is flat
within noise — 7 to 23, no downward trend.**

### The one conclusion this licenses

**Discovery is not saturating.** A depleting defect population produces a
falling find rate per unit of work; this does not fall. On this evidence the
platform is still on the flat part of the discovery curve, nowhere near the
knee — which means **the undiscovered reserve is large relative to the 67 found
so far.**

That is a direction, not a size. It is worth having: it says the honest answer
to *"are we nearly done finding these"* is **no**, and it says it from data
rather than from mood.

### What it does NOT license

- **No number.** A flat rate bounds nothing above.
- **The rate tracks EFFORT as much as population.** Four sessions worked this
  week; more looking finds more. Flat-under-rising-effort would mean depletion,
  flat-under-flat-effort would mean a deep reserve, and **effort is not
  recorded**, so the two cannot be told apart. Commit count is a proxy for
  activity and a poor one for *attention*.
- **Six points is not a trend.** The 23.3 on 09-11 and the 7.1 on 09-09 are one
  quiet day and one partial day, not a signal.
- **The register only holds what was FOUND.** Its `monitoring` column is 0 for
  exactly this reason, and the same selection effect caps everything above.

## 3. What would make a real IBNR possible

**One field: `injection_commit`.** The commit that introduced the defect, on the
record that fixes it.

It is cheap **at record time and only then** — the person fixing a defect has
just read the code and usually knows, or can find it with one `git log -S`. It
is **not honestly backfillable**: reconstructing 67 injection points by blame
would produce a lag distribution built from guesses, which is worse than no
distribution, and it is the same trap the register already refuses for
`detection_method` and `found_by_tool`.

With it, `discovery_lag = fix_date − injection_date` is a real distribution, and
the standard chain-ladder applies to it.

**A second field would sharpen it and is a bigger ask:** exposure — how much
attention a file has actually received. Nothing records that today, and inventing
a proxy from commit counts is the thing §2 above already refuses to do.

## 4. Recommendation

**Add `injection_commit` to `--add` as OPTIONAL with a required reason when
omitted** — the same shape as `--rule not-citable`, which exists precisely so a
record can say *"no honest answer"* instead of carrying a fabricated one. Making
it mandatory would produce guesses; making it silently optional would leave it
empty, which is what happened to `detection_method` before item 2/24.

Then IBNR is re-scoped when the field has real coverage. **Not before**, and this
document is the record of why the number is absent rather than late.

## 5. What this scoping does NOT claim

- **Nothing was built and no field was added.** The recommendation in §4 is a
  recommendation.
- **The 67 records span 2026-09-09 to 2026-09-14 only.** The register is
  deliberately not backfilled, so this is six days of one platform's history and
  says nothing about the years of code those defects live in.
- **"Flat" is eyeballed across six points**, not tested. No trend statistic is
  offered because six points would not support one.
