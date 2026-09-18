# Should the circuit breaker move from observe to enforce? — what the real data shows

**2026-09-18 (Fourth).** Asked because the auditor's chaos test confirmed the
breaker fires correctly at threshold 10, and flipping it on a miscalibrated
threshold risks taking a working dependency offline during a real blip.

**Answer: do not flip, and the threshold is not the blocker.** Two things have
to exist before the threshold question is even askable, and neither does.

---

## 1. THE ONLY PRODUCTION BREAKER IS WIRED TO A STORE THAT REFUSES TO ENFORCE

One non-test caller creates a breaker on this platform:

```
api/_lib/ai-rate-limit.js:225        store: RESIL.instanceStore(),
```

and `instanceStore()` in `api/_lib/resilience.js` carries, in its own words:

> ```
> // NAMED, NOT IMPLIED. The one thing this store must never do is let a
> // caller enforce on it -- see the header, and see anon-rate-limit.js for
> // what enforcing on a per-instance counter actually did in production.
> canEnforce: false,
> ```

**So `mode: 'enforce'` on the one breaker that exists in production would be
enforcing on a per-process counter** — which this platform has already done once,
in `anon-rate-limit.js`, and recorded as a real production defect. On a
serverless runtime each instance keeps its own count, so ten failures spread
across ten cold starts is ten counters of one and the breaker never opens; and
when it does open it opens for one instance while the others carry on. It is
not a weaker breaker, it is a different and wrong thing.

The store that CAN enforce is `sharedStore()`, backed by
`sql/sairn_circuit_breaker_schema.sql` and the `sairn_ai_rate_limit_consume`-
style atomic RPC. **Nothing in production wires it.** `grep` finds
`sharedStore(` in `api/_lib/resilience.test.js` and nowhere else.

**And the table it needs is not known to exist.** `sairn_circuit_breaker` is
absent from `db/schema_snapshot.json`, and the capture (2026-09-13 18:39Z)
PREDATES the schema file, so — the same asymmetry as the rate-limit migrations —
the absence proves nothing in either direction. `tools/schema_snapshot_
freshness.py` calls it **undecidable**, which is the honest word.

**Flipping a mode flag today therefore does one of two things: nothing at all,
or it recreates a defect this platform has already paid for.** Neither is a
threshold question.

---

## 2. THERE IS NO SUPABASE FAILURE HISTORY TO CALIBRATE AGAINST

I looked for it in the three places it could be and it is in none of them.

* **The breaker's own table** would hold `failures`, `last_failure_at`,
  `opened_at` per dependency — the exact series a threshold should be fitted to.
  It is unprovisioned or undecidable (§1), so it holds nothing.
* **This clone has no database access**, so no direct query is possible.
* **GitHub Actions history covers 500 runs** (`total_count` 5114). Aggregated:
  CodeQL 242 success / 2 null, hover-separation 244 success, nightly-backup
  **2 runs 2 failures**, cron-liveness 7 success / 3 failure in that window.
  **None of it is a Supabase measurement.** CodeQL and hover-separation never
  touch it; the nightly backup fails at `pg_dump` before any application path
  runs.

### AND THE ONE SERIES THAT LOOKS LIKE DEPENDENCY FAILURE IS THE MONITOR'S OWN BUG

`cron-liveness` failed **seven consecutive runs** — #2 through #8, 2026-09-16
10:18Z to 2026-09-17 12:08Z — and has succeeded on every run since (#9–#15).
A seven-in-a-row outage followed by a clean recovery is exactly the shape
somebody would fit a threshold to.

**It was not an outage.** `f1d733ff`, registered at `db652999` — *"the monitor
that failed six times without asking anything"* — an **empty-secret defect in
the watchdog itself**: the same variable read in two languages in one workflow,
the shell half correct, so a reader who checked one half found a right answer
and stopped.

**Counting those seven as dependency failures is precisely the miscalibration
this question exists to avoid**, and it is the only candidate population
available. A threshold fitted to it would be fitted to a bug in the instrument.

---

## 3. What the chaos test does and does not license

The auditor's test confirmed the breaker **fires correctly at threshold 10** —
that is a statement about the MECHANISM and it is worth having. It is not a
statement about the RATE. Whether ten failures in a window is a dependency being
down or a dependency having a bad second is a question about Supabase's real
behaviour, and nothing here has measured that.

This is the platform's own recorded distinction: a mechanism that works and a
threshold that is right are two different claims, and the second needs a
denominator.

---

## 4. Recommendation

**Do not flip.** In order:

1. **Provision the shared store and wire it.** Run
   `sql/sairn_circuit_breaker_schema.sql`, confirm with a query, and point
   `ai-rate-limit.js` at `sharedStore()`. Until then "enforce" is either inert
   or wrong, and the flag is a decoration.
2. **Let it run in OBSERVE with the shared store for a real window.** That is
   what produces the first genuine failure series this platform has ever had —
   the table records every outcome whether or not it opens. Observe-first is
   this platform's own promotion path, used for push-gate checks 5 and 7.
3. **Then fit the threshold to that series**, and report accuracy and stability
   as two numbers rather than one.

**What would change my answer:** a real `sairn_circuit_breaker` table with a
few weeks of rows in it. Nothing else — not a longer chaos test, and not
another look at the Actions history, which cannot see Supabase at all.

**One thing to fix regardless of the decision:** `recurrence_open` on the
watchdog record names a sweep nobody has run — *any other*
`os.environ.get(name, default)` reading a GitHub secret has the identical
empty-secret defect. That is a live, unswept class in the same workflows this
question is about.
