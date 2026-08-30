---
name: sairn-perf-profiler
description: Diagnose a SAIRN performance problem from measured evidence, not from reading code — slow endpoints, slow Postgres/PostgREST queries, oversized payloads, cold Vercel functions, and the 2MB single-file app ceiling. Trigger when something is "slow", when a page or endpoint times out, before and after any optimisation, and whenever a speed claim is about to be made. Distinct from the frontend `performance` and `core-web-vitals` skills, which cover browser delivery — this covers the server and data layer, where most SAIRN slowness actually lives. Never states a timing it did not measure.
allowed-tools: Read Grep Glob Bash
---

# SAIRN Performance Profiler

**The rule that outranks every technique here: no invented numbers.** Not a
latency, not a percentage improvement, not a row count. A performance report is
a set of claims, and on this platform a claim without evidence is the defect —
same standard as a rule without a citation.

Most SAIRN slowness is **server or payload**, not rendering. Start here, not in
the browser.

---

## 1. Establish a reproducible baseline BEFORE changing anything

Without a baseline there is no improvement, only a feeling.

    for i in 1 2 3 4 5; do
      curl -s -o /dev/null -w "%{time_total} %{size_download} %{http_code}\n" \
        -X POST "https://sairn.vercel.app/api/sd-data" \
        -H "Authorization: Bearer <KEY>" -H "Content-Type: application/json" \
        -d '{"action":"read","resource":"<resource>"}'
    done

Record **all five**, not the best. Note whether the first is an outlier — that
is a cold start, and a cold start is a different problem from a slow query.

**Same conditions on the re-test.** Same licence, same resource, same row count,
same time of day. A re-test under different conditions is a new baseline, not a
comparison.

## 2. Grade the evidence, and say which grade you have

| Grade | Meaning |
|---|---|
| **A — measured** | You ran it and have the numbers |
| **B — instrumented** | A log or `EXPLAIN` from the real system |
| **C — inferred** | Read from code; plausible; **not** a finding |

**Never report C as A.** "This N+1 loop is probably the cause" is grade C until
a measurement says so. Write the grade next to each claim.

## 3. Payload before compute — the most common real cause here

**Incident:** SAIRNroofing's claims read branch was shipping the **full 1.5 MB
signature blob on every claim open**, when nothing on that screen rendered it.
Found and fixed before push; the fix was to strip it unless `include_signature`
is passed, with `has_signature` flagged either way.

Check first: `%{size_download}`. Then look at the `select=` list in the handler.
PostgREST returns exactly what is asked for — an unbounded `select=*` on a table
with a `jsonb` blob or a base64 image is the whole problem, and no amount of
query tuning fixes it.

**Ask: does the caller render every field it receives?**

## 4. Read the actual PostgREST query the handler builds

Slowness attributed to "the database" is usually the URL. In `api/sd-data.js`,
find the `rest(...)` call and read it literally:

- Is there a `license_hash=eq.` filter? An unfiltered read crosses tenants and
  scans everything.
- Is there an index for the columns being filtered? Check the schema file —
  e.g. `idx_rfcon_license`, `idx_rfcon_state` on `(license_hash, state)`.
- Is there a `limit`? An append-only evidence table grows forever.
- Is there an `order` on an unindexed column?

## 5. Append-only tables grow without bound — plan the read, not the write

Several SAIRN tables are append-only by design (`rf_claim_agreements`,
`dnt_credentials`, audit logs). Correct for evidence integrity, and it means a
read that was instant at 10 rows is not at 10,000.

**Check:** does the read ask for all history when it renders only current state?
The evaluate/compute branches derive current state from full history on every
call — fine at present volume, and it is a **known** scaling shape rather than a
surprise. Measure before assuming it is the problem, and measure before assuming
it is not.

## 6. Vercel cold starts are a distinct diagnosis

Every SAIRN endpoint is a stateless serverless function. A slow first request and
fast subsequent ones is a cold start, not a slow query, and query tuning will not
move it. Distinguish them by running the loop in §1 and looking at request 1 vs
2–5 rather than the average.

## 7. The 2 MB single-file ceiling is a real performance surface

`stonedesk.html` is ~2.23 MB in one file, parsed on every load. This is why
`sairn-software-architect` sets a size ceiling and why dead code matters:
`api/bridge.js`'s `pull` had **zero callers across all 13 apps**, and
`stonedesk.html` carries **29 `SEED` constants** and **56 fallback sites**.

Deleting dead code is a measurable parse-time win, and unlike most optimisations
it has no downside. Measure with real byte counts, not impressions.

## 8. Never touch production to profile without explicit authorisation

Read-only measurement against production is fine. **`EXPLAIN ANALYZE` on a large
table, adding an index, changing a config, or running a load test is not** —
those need a named decision, and this platform's rule is that a
cleanup/migration is not done when the command exits, it is done when the
destination is queried back.

State clearly which of your measurements were read-only.

## 9. The smallest change that the evidence supports

One change at a time, then re-measure under the same conditions. Two
simultaneous changes mean neither is attributable — and one of them may have
made things worse while the other hid it.

## 10. Report format

    ## Performance finding
    Symptom      : <what was observed, by whom, where>
    Baseline     : <5 real numbers, same conditions, grade A>
    Cause        : <claim>  [grade A/B/C]
    Evidence     : <the command run and its real output>
    Change       : <smallest change supporting the evidence>
    Re-test      : <5 numbers, SAME conditions>
    Delta        : <measured; omit entirely if not re-measured>
    Not measured : <what remains unverified, and why>

**`Delta` is omitted, never estimated.** "Should be about 40% faster" is the
sentence this skill exists to prevent.

**`Not measured` is mandatory.** A profile that does not say what it could not
reach reads as complete coverage — the same false-confidence failure that let a
green 84/84 suite hide a broken storage layer.

---

## What this skill does not cover

Browser rendering, LCP/INP/CLS, image and font delivery, caching headers. Those
are `performance` and `core-web-vitals`. If the measurement in §1 shows the
server responding fast and the page still feeling slow, **switch skills** —
staying here will produce a confident answer about the wrong layer.
