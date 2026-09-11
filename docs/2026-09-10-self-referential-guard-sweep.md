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

## What the first half did not cover — now done, below

**Checkers in `tools/`, not tests.** Several derive their subject from the thing
they check — `criticality_tier_check.py` reads the apps from
`api/_resources/*.js`, `traceability_matrix.py` reads its rows from sources,
`preauth_oracle_check.py` walks `api/`. The same question applies to each, and
the answer is usually different: deleting an `api/` handler is not itself a
defect, while deleting a resource from a registry is. **That is a second sweep
with a different judgement in every case.**

---

# Part two — the `tools/` checkers (2026-09-10)

## The answer, stated before the detail: three real holes, and the biggest was the test runner itself

The first half found the platform had almost solved this problem already. The
second half did not come out the same way, and the reason is structural rather
than anything about who wrote what: **a test suite's subject is a registry
somebody curated, and a checker's subject is usually the filesystem.** A
curated list has a number attached to it that a person chose. A directory walk
has whatever is there, and "whatever is there" cannot be zero-checked by
comparing it to itself.

## The judgement that had to be made once per checker

The question is never "is the subject derived?" — it is **"if this subject list
went empty or short, would that be a defect, and would anyone find out?"** Three
different answers turned up:

| If the subject list shrinks… | …is it a defect? | Example |
|---|---|---|
| the risk leaves with the subject | **no** | an `api/` handler is deleted — there is no endpoint left to leak |
| the risk stays, the guard leaves | **yes** | a test file is deleted — the code it guarded is still shipping |
| nobody chose it at all | **always** | `git` failed, the tool ran from the wrong directory, a glob stopped matching |

The third row is the one this half of the sweep is really about, and it is
invisible in every case: an empty subject list produces a report that is
**byte-identical to a clean one**.

## What was examined

| Checker | Subject derived from | Verdict |
|---|---|---|
| `tools/run_all_tests.py` | `os.walk('tests')` + `api/*.test.js` | ❌ → **fixed** — see below |
| `tools/report_only_checks.py` | `git ls-files '*.html'` | ❌ → **fixed** — see below |
| `tools/preauth_oracle_check.py` | `os.walk('api')` | ⚠ → **two gaps closed** |
| `tools/write_without_readback_check.py` | `*.html` in the **current directory** | ⚠ → **coverage now disclosed** |
| `tools/criticality_tier_check.py` | `api/_resources/*.js` | ✅ safe — the rollup pins the counts |
| `tools/traceability_matrix.py` | `tests/`, `api/`, registries | ✅ safe — `--check` diffs against the committed doc |
| `tools/sairn_strict_args_check.py` | `glob('*.html')`, cwd-relative | ✅ prints `in 0 file(s)` |
| `tools/sairn_seam_check.py` | `glob('api/*.js')`, cwd-relative | ✅ prints `0 clean, 0 not-forwarded, 0 could-not-tell` |
| `tools/sairn_stale_snapshot_scan.py` | `glob('*.html')`, cwd-relative | ✅ three zeros on one line — thin, but visible |

**The cwd-relative class was measured, not reasoned about.** All four were run
from `docs/` and their real output read. Three disclose a zero somewhere;
`write_without_readback_check.py` was the only one that printed an empty table,
`none`, `none`, and exit 0 with no count anywhere.

---

## 1. The test runner did not know how many tests there should be

`discover()` walks `tests/` and `api/`, counts what it finds, and reported
`ALL N TEST FILES PASS` for whatever N turned out to be. **Delete twenty test
files and it prints a true sentence about a suite that just lost twenty
guards.** This is the largest derived-subject guard on the platform and it
pinned nothing.

`MIN_TEST_FILES` is the pin. Two things about it are worth more than the pin
itself:

**It is a floor at runtime and an equality at commit time**, because the two
ends want opposite things. A floor never false-alarms on a clone mid-addition,
so nobody learns to route around it; an equality, enforced by
`tests/run_all_tests_floor_probe.py`, leaves no dead zone between the pin and
reality. Growth is reported as housekeeping with the new number to write;
shrinkage is the defect.

**The first version of the pin was wrong in both of the ways this document is
about, and neither was visible in its diff:**

- it said **163 while `discover()` returned 180** — seventeen test files could
  have been deleted in silence, 85% of the twenty-file example its own comment
  used. A floor below the real count is not a cautious floor, it is an
  unmeasured dead zone;
- it was added to `_main_body()` and **not to `_hook_body()`** — the copy that
  runs unattended after every push, in every clone. That is the half that
  mattered. A deletion you made yourself is in your own diff; **a deletion that
  arrives by rebase from another clone is visible to nothing else**, and the
  hook was the only thing positioned to see it.

The second is CLAUDE.md's standing lesson from `sairn_claim_hook.py`, hit again
without being recognised: *a fix verified on the copy a human invokes is not
verified if a second copy runs unattended.* The probe's final arm now asserts
there is exactly one definition of the constant and exactly two comparisons
against it, so a third copy cannot be added with the check in only two of them.

## 2. The report-only sweep reported a clean platform after scanning zero apps

`report_only_checks.py` runs the promoted checkers after every push. Six of its
twenty-one entries run **per app**, over 22 apps — 132 checker runs. The target
list comes from `git ls-files '*.html'`.

When that list came back empty, `for t in targets` simply did not execute.
`findings` stayed `[]`, `unrun` stayed `[]`, and the hook printed nothing —
**the same output as a clean sweep of all 22 apps.** Proved by forcing
`app_files()` to `[]` before fixing it, not argued from reading.

Two ways in, both closed:

- **`git ls-files` failing was read as "no apps."** The return code was never
  checked. Git absent from the hook's PATH, an index locked by one of the four
  clones mid-rebase, a corrupt index — any of them yields empty stdout. It now
  raises, and `run_one()` turns that into an `unrun` line, which is the
  *could not run is not a pass* standard used everywhere else here.
- **Zero targets is now an `unrun` line**, not a silent pass. A **deleted** app
  is deliberately *not* what this guards — removing an app removes the risk
  with it, and it is loud in a diff. What it guards is the list emptying for a
  reason nobody chose.

One thing was **left alone on purpose**: the "not scanned: N non-root .html"
notice prints on the hand run only, because the hook's stdout is a single JSON
payload that a stray line would corrupt. The file claimed the exclusion was
"PRINTED rather than silent"; that claim is now scoped to where it is true.
The exclusion is correct in both copies — `vercel.json` serves root files only
— so the zero-target guard covers the case that is not benign.

## 3. `preauth_oracle_check.py` — two gaps, neither a verdict change

It already audits its **accepted-exemptions** file for entries that matched
nothing, on the stated reasoning that *"an accepted-list nobody audits is how a
suppression outlives the thing it suppressed."* The **declarations** file — the
one recording that a handler is public on purpose — had no equivalent, so a
declaration could outlive its handler in silence. `STALE DECLARATION` now
reports it, mutation-proved by injecting a declaration for a file that does not
exist.

It also printed four counts and never said **how many handlers it looked at**,
so a walk over zero files produced the same all-zeros report as a clean run over
all 63. `HANDLERS_SCANNED` closes that.

Both are report-only and change no verdict, deliberately: deleting a handler is
a legitimate act.

---

## ⚠ What this half did NOT do, said plainly

- **`write_without_readback_check.py`, `sairn_strict_args_check.py`,
  `sairn_stale_snapshot_scan.py` and `sairn_seam_check.py` still default to a
  CWD-relative glob.** Only the coverage disclosure was fixed, not the
  anchoring. Run via `report_only_checks.py` they are safe (it passes
  `cwd=REPO`); run by hand from a subdirectory they scan nothing. Anchoring
  each to a `REPO` constant is a real fix and it is not done here.
- **The remaining ~75 files in `tools/` were not individually read.** The
  candidates were selected by grepping for filesystem discovery, and every
  candidate that grep produced was opened — but a checker that derives its
  subject some other way (parsing a source file, importing a module) would not
  have appeared in that list. The first half of this sweep records what a grep
  alone is worth: it over-reported six suites of which four were false.
- **`tools/defect_register.py --check` fails today with 5 pre-existing
  problems** — two commit SHAs recorded in the register are not in this repo
  after a fetch. Found while verifying this work, unrelated to it, not fixed
  here.
