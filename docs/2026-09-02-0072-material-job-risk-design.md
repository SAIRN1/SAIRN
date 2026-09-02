# [0072] Material-correlated job risk — design

**Date:** 2026-09-02 · **Session:** CC · **Status:** scope. Data model first, arithmetic second.

## The data gap is real, and it is bigger than one field

Read from the files, not assumed:

| Record | Fields today | Lead time? |
|---|---|---|
| slab (`sdSlabs`) | `id, material, colorName, status, usableSqft, vendor, photo_base64, addedAt` | none |
| job (`sdJobs`) | `id, customer, jobNum, material, templateDate, targetDate, stage, sqft, installer, address, volume, notes, reservedSlabId, createdAt, installedAt, intakeId` | none |
| `VENDORS` (in-file constant) | vendor `name`, `logo`, `products[{sku, name, price, cat}]` | none |

So there is **no supplier lead time anywhere**, and there are two further absences
that the risk arithmetic needs and that nobody has noticed because nothing has
tried to compute this before:

1. **No order date on a slab.** `addedAt` is when it was entered into inventory.
   Without an `orderedAt` there is no way to *derive* a real lead time from what
   actually happened — only to record what a supplier claims.
2. **No stage durations.** A job carries a current `stage` and nothing about how
   long stages take. `templateDate` and `installedAt` bound the whole job, not
   its parts.

## The rule this design is built around

**Nothing is assumed. Every input is measured or declared, and if it is neither,
it is reported as unknown and the job is not scored.**

That is not caution for its own sake. A projected completion date built on an
invented 14-day lead time is worse than no date: it is a number a shop would
schedule a customer against. The compliance gate settled the same question a day
ago — three states, never two, and untracked is never a green tick. This is the
same shape.

So: **no example lead times are shipped.** The table arrives empty. Until a shop
enters a quoted lead time or the system observes a real one, every job needing
procurement of that material is `risk: "unknown"` with a named reason.

## Data model

### `sd_supplier_lead_times` — new table

Keyed `(license_hash, supplier, material)`. Both halves of the pair matter:
the same supplier is faster on quartz they stock than on quartzite they import,
and the same material is faster from a local distributor than an importer.

| column | meaning |
|---|---|
| `quoted_days` | what the supplier says. Declared by the shop. Nullable. |
| `observed_total_days`, `observed_n` | running sum and count of REAL receipts, so an average is derivable without keeping every event |
| `observed_min_days`, `observed_max_days` | spread, because an average of 10 and 40 is not a 25-day lead time in any useful sense |
| `last_observed_at` | how stale the observation is |

`quoted` and `observed` are stored separately and never merged in storage. The
engine prefers observed when `observed_n >= 3`, and says which it used.

### `orderedAt` on the slab record

One nullable field. When a slab is received with an `orderedAt` set, the system
folds `(addedAt - orderedAt)` into the observed columns above. This is the only
way a lead time becomes *measured* rather than *claimed*, and it costs one date
picker on the intake form.

### Stage durations — derived, never tabled

Computed from completed jobs on this licence: for each stage, the median observed
duration across jobs that have passed through it. Below three completed jobs the
production estimate is unknown, and the job is not scored. No default stage
durations are shipped, for the same reason as lead times.

## The arithmetic, once real data exists

For a job with a `targetDate`:

```
slab_ready_on  = in stock (reserved, or a matching in-stock slab
                 with enough sqft)            -> today
               = otherwise                    -> today + lead_days(supplier, material)
               = lead time unknown            -> UNKNOWN, stop, risk = "unknown"

production_days = sum of median durations for the stages REMAINING
                  after the job's current stage
                = fewer than 3 completed jobs -> UNKNOWN, stop

projected_completion = slab_ready_on + production_days
slack_days           = targetDate - projected_completion

risk = "unknown"  if either input is unknown
     = "at_risk"  if slack_days < 0
     = "tight"    if 0 <= slack_days <= 3
     = "ok"       otherwise
```

`slack_days` is reported alongside the flag, because "at risk by 1 day" and "at
risk by 3 weeks" are different problems and a boolean hides that.

## What this deliberately does not do

- No ship of default lead times, default stage durations, or a "typical" fallback.
- No blending of quoted and observed into one number.
- No score for a job with no `targetDate` — there is no commitment to miss.
- No supplier scoring or ranking. That is a different feature and inviting it
  here would mean shipping judgements about vendors from three data points.
