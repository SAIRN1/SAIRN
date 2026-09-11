# Self-referential guards — the platform sweep, and what it did NOT find

**Written 2026-09-10 (Fourth).** Commissioned after the fault probe for the two
newest suites caught them disabling themselves: their by-name section iterated
`REG.resources` and filtered by tier, so **removing a resource from the registry
also removed its own assertion**. The arm that dropped a Tier A money resource
from registry, client and schema together reported *green* — not because the
suite tolerated the defect, but because the test for it had stopped existing.

The question the sweep asks: **how many other guards on this platform derive
their subject from the thing they guard, and can therefore be disarmed by the
defect they exist to catch?**

---

## The answer, stated before the detail: almost none

**Thirteen derived-subject suites were examined. Twelve already pin a count.
One does not and is benign. The hole was in the two newest files, and it was
mine.**

That is the result as it came out. It would have been easy to write this up as
a platform-wide problem — the shape is real and genuinely dangerous — but the
measurement says the platform had already solved it everywhere except in code
written today.

---

## Why deriving the subject is usually RIGHT

This sweep is not an argument for hardcoded lists. `tests/sairnvet_seed_never_syncs.js`
says so in its own header, and it is correct: a hardcoded list of seeded getters
*"would pass forever while the app grew a fortieth"*.

The two approaches are blind in opposite directions:

| | catches an ADDITION | catches a REMOVAL |
|---|---|---|
| **Derived** subject list | ✅ the new item is tested automatically | ❌ the item's assertion leaves with it |
| **Hardcoded** subject list | ❌ the new item is never tested | ✅ the missing item fails loudly |

**So the fix is not to stop deriving. It is to derive AND pin the count** — then
an addition is tested automatically and a removal fails on the pin. That is what
twelve of the thirteen already do.

---

## What was examined

| Suite | Subject derived from | Count pinned? |
|---|---|---|
| `tests/sairnbiz_server_backup.js` | `registry.resources` | ✅ |
| `tests/sairnbuild_server_backup.js` | `BLD_SYNCED`, sliced from the app | ✅ `=== 30` |
| `tests/sairnlaw_billing_codes.js` | `LAW_BILLING_CODES`, sliced from the app | ✅ |
| `tests/stonedesk_server_backup.js` | `handlerMap()` from the handler | ✅ `=== 21` |
| `tests/sairnvet_seed_never_syncs.js` | seeded getters, parsed from the app | ✅ `>= 39` |
| `tests/seed_never_syncs_platform.js` | per-app key lists | ✅ |
| `tests/st_reports_failure.js` | `APPS` — a literal IN the test, not derived | n/a |
| `api/sd-data-sairnlaw-resources.test.js` | `registry.resources` | ✅ |
| `api/_lib/dental-bi.test.js` | `bi.DATASETS` | ✅ |
| `api/_lib/ledger.test.js` | `L.ACCOUNTS` | ✅ |
| `api/_lib/anon-rate-limit.test.js` | `reg.RESOURCE_NAMES` | ❌ — **and benign, see below** |
| `tests/sairnfreedom_server_backup.js` | `REG.resources` | ❌ → **fixed today** |
| `tests/sairndesign_server_backup.js` | `REG.resources` | ❌ → **fixed today** |
| `tests/sairngrounds_server_backup.js` | `REG.resources` | ❌ → **fixed today** |

### The one that stays unpinned, and why that is correct

`api/_lib/anon-rate-limit.test.js` iterates `reg.RESOURCE_NAMES` to assert the
429 rate-limit message names none of them. If the registry were empty the loop
would assert nothing — but **an empty registry is not the defect this test
guards**, and the leak it is looking for can only exist if names exist. Pinning
a count here would be ceremony, not coverage.

That distinction is the one a mechanical checker cannot make, which is why this
sweep is a document and not a tool.

---

## What was fixed

The three newest suites now pin their registry counts — 35, 18 and 30 — with the
number stated as deliberate and requiring a hand edit. **That edit is the
point:** it makes a removal visible in a diff instead of silently shrinking the
test surface.

The by-name sections were already repaired in `1ef35a62` by reading Tier A from
`docs/CRITICALITY-TIERS.md` — an independent source — rather than from the
registry they are checking. The count pin is a second, cheaper layer that would
have caught the same thing.

---

## ⚠ The detector over-reported, and that is the reusable lesson

The first pass looked for `.length >= N` and reported **six** unpinned suites.
Four were false: this repo writes the same assertion as
`assert.strictEqual(x.length, 30)`, which that pattern does not match, and one
subject (`st_reports_failure.js`'s `APPS`) is a literal in the test rather than
a derived list at all.

Reading the four before reporting them is what turned a fabricated
platform-wide finding into an accurate negative result. **Every candidate here
was opened and read; none was reported on the strength of a grep.** That is the
same blind-zero class `sairn-portfolio-triage` documents, hit twice in one day
by the same session — once on the master plan's test counts, once here.

---

## What this does not cover

**Checkers in `tools/`, not tests.** Several derive their subject from the thing
they check — `criticality_tier_check.py` reads the apps from
`api/_resources/*.js`, `traceability_matrix.py` reads its rows from sources,
`preauth_oracle_check.py` walks `api/`. The same question applies to each, and
the answer is usually different: deleting an `api/` handler is not itself a
defect, while deleting a resource from a registry is. **That is a second sweep
with a different judgement in every case, and it is not done here.**
