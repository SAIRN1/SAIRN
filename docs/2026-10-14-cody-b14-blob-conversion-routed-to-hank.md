# Ten unconverted stored-blob sites — ROUTED TO HANK, not fixed here

**Written 2026-10-14 by cody, batch b14. Measured against `7a1d3382`.**

**NOTHING UNDER `api/` WAS EDITED TO PRODUCE THIS DOCUMENT, and nothing under
`api/` is edited by it.** Every one of the 58 unconverted sites lives in
`api/`, which is hank's. `docs/blob-conversion-coverage.json` is therefore
**left at `unconverted: 58`, `converted: 34`** — the ratchet is NOT re-pinned
here, because re-pinning without a conversion is the one use the tool's own
note forbids: *"Lower it by converting a site and re-pinning with `--repin`,
never to make a run pass."*

**THIS IS THE ROUTING DECISION THE b13 HANDOFF LEFT OPEN.** b13 §4 item 4
recorded that whoever took the ten *"must either hold an `api/` claim or route
the ten conversions to hank with the failing-first command per site."* Michael
decided: **`api/` is hank's, so the ten are routed.** That is the whole
deliverable for this half of the item — the conversions themselves are not
cody's to make.

---

## Why these ten, so the selection is not a judgement

**They are the FIRST TEN in `python tools/blob_conversion_coverage.py --list
RAW` order, as that tool printed them at `7a1d3382`.** No cherry-picking, no
"easiest first", no skipping a hard one. The order is the tool's own, and
re-running the command reproduces the same ten as long as no site above them is
converted first.

**Two of the ten are NOT single-table sites and that changes the work** — see
sites 6 and 7 below. They are generic dispatchers over a table map, so one edit
covers three resources and two resources respectively. Counted as two sites
because the tool counts two `data:` expressions; named here as five resources
so nobody discovers that after starting.

---

## What the conversion is, in this codebase's own terms

From `tools/blob_conversion_coverage.py`'s header, not paraphrased from
memory: a **site** is a `data:` property in an object that *also* carries
`license_hash`. `storedBlob(...)` strips `NEVER_STORED` — `license_hash`,
`app_id`, `p_license_hash` — on every branch, and strips the branch's own
**column keys**, which is what stops a payload copy of a mapped column
shadowing the real one when a read spreads the blob last.

**THE TOOL CANNOT CHOOSE THE COLUMN KEYS AND NEITHER CAN THIS DOCUMENT.**
Which payload fields are real columns is a fact about each table. `sd_slabs`
and every `mech_` record keep `id` INSIDE `data` on purpose, because their
reads return `x.data` whole. So each row below names **the paired READ** and
the converter must derive the key list from that read. A key list copied from
the row beside it is the second-copy defect, and this file does not supply one.

---

## The ten, each with its paired read and its own failing-first command

Line numbers are **as of `7a1d3382`** and will move. The **branch opener text**
in each row is the anchor to grep; if the opener no longer matches, re-derive
the site from `--list RAW` rather than trusting the number.

| # | site at `7a1d3382` | branch / table | the paired READ that decides the column keys |
|---|---|---|---|
| 1 | `api/_lib/sd-store.js:203` | `writeMemory()` → `ai_memories` | `readMemories()` at `:175` — returns `flat(x.data, { created_at: x.created_at })`. **`shop_id` IS a column on the write (stamped from `business_profiles`) and the read does NOT re-merge it**, so a payload `shop_id` is stored in the blob and silently contradicts the row's own column rather than being overwritten by it |
| 2 | `api/sd-data.js:2326` | `profile/write` → `business_profiles` | `:2312` — read returns `flat(row.data, { shop_id: row.shop_id })` |
| 3 | `api/sd-data.js:3663` | `slabs/write` → `sd_slabs` | `:3646` — **this read returns `x.data` WHOLE, so `id` stays inside `data` on purpose.** Do not strip it |
| 4 | `api/sd-data.js:3718` | `locations/write`, opener at `:3687` → `sd_locations` | the `locations/read` fetch at `:3680` — returns `x.data` whole; `location_id` is the column and `payload.id` is its source |
| 5 | `api/sd-data.js:3755` | `remnants/write` → `sd_remnants` | `:3737`; `remnant_id` is the column |
| 6 | `api/sd-data.js:4116` | **GENERIC — `SD_LINEAGE` dispatcher**: `sd_blocks` (`block_id`), `sd_bundles` (`bundle_id`), `sd_slab_history` (`event_id`) | `:4100` — read does `Object.assign({ id: x[cfg.idCol] }, x.data)`, **blob spread LAST, so a payload `id` shadows the real column.** `cfg.idCol` is the key to strip |
| 7 | `api/sd-data.js:4175` | **GENERIC — `SD_HR` dispatcher**: `sd_hr_employees` (`employee_key`), `sd_hr_certs` (`cert_key`) | `:4156` — same `Object.assign({ id: ... }, x.data)` shape. **PERSON DATA: employees and training records. Re-qualify the tier before converting** |
| 8 | `api/sd-data.js:4913` | `properties/write` → `grd_properties` | `:4900` — read returns `x.data`; `property_id` is the column |
| 9 | `api/sd-data.js:4934` | `jobs/write` → `grd_jobs` | `:4921`; **TWO columns — `job_id` and `property_id`** |
| 10 | `api/sd-data.js:4955` | `quotes/write` → `grd_quotes` | `:4942`; **TWO columns — `quote_id` and `property_id`** |

### The failing-first command, per site

Two measurements per site, deliberately of different shapes — one over the
source text, one over the tool's count — because a single method that goes
quiet is indistinguishable from a conversion that worked.

**(a) The source-text check, anchored on the branch opener, not the line
number.** For site 8:

```sh
grep -n "resource === 'properties' && action === 'write'" api/sd-data.js
sed -n '<hit>,<hit+8>p' api/sd-data.js | grep -c "data: payload"
#   BEFORE the conversion -> 1      <- this is the RED, and it must be captured
#   AFTER  the conversion -> 0
```

Sites 6 and 7 have no `resource === '...'` opener — they are dispatchers.
Anchor those two on `const SD_LINEAGE = {` and `const SD_HR = {` and widen the
window to the write.

**(b) The tool's own count, which is the structurally independent half.**

```sh
python tools/blob_conversion_coverage.py --list RAW        # BEFORE: the site is listed
python tools/blob_conversion_coverage.py --list CONVERTED  # BEFORE: it is NOT
# ...convert...
python tools/blob_conversion_coverage.py --list RAW        # AFTER:  gone
python tools/blob_conversion_coverage.py --list CONVERTED  # AFTER:  present
```

**`unconverted` must fall by exactly one per `data:` expression converted** —
so **58 → 48** when all ten are done, NOT 58 → 53 and not 58 → 44. Sites 6 and
7 are one expression each despite covering five resources; a drop of more than
ten means something other than these ten moved and the figure is not
attributable.

### The re-pin, which is hank's to run and only after the conversions

```sh
python tools/blob_conversion_coverage.py --repin
```

**Never by hand**, and never ahead of the conversion. `docs/blob-conversion-coverage.json`
stays untouched until then; this document does not pre-adjust it.

---

## What is NOT claimed here

* **Not that all ten NEED converting.** The tool says it *"cannot tell a
  harmless RAW site from a harmful one"*, and this document does not overrule
  that. Site 3 is flagged precisely because its read returns the blob whole.
* **Not that the ten were tested.** No `api/` file was run, edited or
  exercised for this routing. The branch/table/read triples above were read out
  of the source at `7a1d3382` and are citations, not test results.
* **Not that the line numbers will hold.** They are stamped to a sha for that
  reason, and each row carries text to re-derive from.

**Owner: hank** (`api/`). **Routed by: cody**, batch b14, holding the `tests`
claim and declaring `api/` read-only.
