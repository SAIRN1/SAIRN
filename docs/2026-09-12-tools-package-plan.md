# The tools package — inventory, structure, and what genericisation actually costs

**Written 2026-09-12 (Fourth).** Michael's decision, same day: the package ships
**fully genericised**, because a tool still wired to this repo's paths and
licence-key shape will not run on anyone else's codebase — a functional blocker
for the college course and for selling it, not a documentation nicety.

This is the **inventory and structure** half, which is common to either path and
is done. The genericisation is scoped at the end with a real size, because it is
larger than the documentation and should not be started inside another night's
work.

---

## What is actually here

Derived from `docs/TOOLING-INVENTORY.md` (generated 2026-09-12, `--check`able)
plus a coupling measure taken per file: how many times the executable code —
comments stripped — names something only this platform has (`api/_resources`,
`license_hash`, `license_keys`, `supabase`, an app name, a `PINNACLE` key,
`.claude/`).

`tools/` holds **99 files**. Most of them are not product:

| Excluded | Why |
|---|---|
| 11 `gen_*_calendar.py` / `gen_*_seed.py` | SAIRNlaw jurisdiction data generators. Product content, not a tool. |
| the claim system, push-gate hook, load-state gate, app map | infrastructure for four concurrent clones against one repo. Sellable as a *pattern*, not as code. |
| live probes against SAIRN endpoints | need our licence keys and our deployment. |
| libraries and one-off scripts | support, not product. |

**What is left is the package: 48 tools, ~13,100 lines, 404 coupling
references.** That last number is the genericisation job, and it is the honest
headline.

---

## The structure: seven suites, not fifty scripts

Fifty loose checkers is not a product — nobody knows what to run or in what
order. Each suite below is a **defect class**, with its own runner, its own
worked incident, and its own statement of what it cannot see.

| # | Suite | Tools | LOC | Coupling | What it is for |
|---:|---|---:|---:|---:|---|
| 1 | **Silent failure** | 8 | 2,893 | 88 | a write that fails and tells nobody; a read whose failure is indistinguishable from empty |
| 2 | **Claim honesty** | 8 | 2,068 | 67 | a number nothing computes; a button that does nothing; a feature no user can reach |
| 3 | **Suite integrity** | 4 | 1,092 | 10 | tests that pass for the wrong reason, and checkers that answer differently run to run |
| 4 | **Schema drift** | 7 | 1,851 | 94 | code naming a column the database does not have, and migrations declared but never applied |
| 5 | **Source hygiene** | 10 | 1,385 | 37 | the mechanical layer: parse errors, duplicate globals, control bytes, unbalanced markup |
| 6 | **Governance registers** | 7 | 2,018 | 68 | defect density, traceability, criticality tiers, SOUP — with checkers that keep them honest |
| 7 | **The harness** | 4 | 1,764 | 40 | the registry runner and the gate pattern that make the other six *run* instead of exist |

**Suite 7 is the one that makes it a product rather than a toolbox.** Every
suite above it is a collection of scripts until something invokes them
automatically and reports in one voice. The single most transferable lesson in
this whole package is the one its own inventory records: *a tool that exists is
not a mechanism; a tool that runs is.* Of the 99 files here, **43 are invoked by
nothing at all**, and that was only discovered by generating the inventory.

**Suite 3 is the one nobody else sells.** Checking that your *tests* are honest
— that a control really breaks the thing it claims to break, that an assertion
is not matching a comment about the code, that a checker gives the same answer
twice — is the differentiator. It is also the suite with the lowest coupling
(10 refs across 1,092 lines), so it is the cheapest to ship first.

---

## The four kinds of coupling, and the four different fixes

404 references is not one job. Sorted by what removing it actually requires:

**(a) Hardcoded repo paths — the majority, and the cheap half.**
`api/_resources/*.js`, `sql/`, `db/schema_snapshot.json`, `docs/CRITICALITY-TIERS.md`,
`*.html` at the repo root. Fix: one `toolkit.config.json` naming where each kind
of thing lives, with today's SAIRN values shipped as the worked example. Mostly
mechanical; the risk is the tools that resolve paths *differently* in two places,
which this repo has already been bitten by twice.

**(b) App-shape assumptions — the real work.**
The checkers assume a single-file HTML app with inline `<script>` blocks, a
`license_hash`-scoped row model, and an `app_id`. A React/Vue/Django codebase has
none of that. Fix: a small **adapter interface** — *give me the source units, the
storage-write call sites, the entry points* — with the SAIRN single-file adapter
as the reference implementation. This is where a package that "runs on someone
else's code" is won or lost, and it cannot be done by find-and-replace.

**(c) Platform assumptions — Supabase/PostgREST and Vercel.**
Concentrated in suite 4 and the deploy watcher. Fix: a backend module with one
implementation shipped (Postgres via any connection) and the PostgREST specifics
behind it. Suite 4 has the highest coupling density in the package (94 refs in
1,851 lines) and should be scoped as its own piece.

**(d) House documents — the register formats.**
Suite 6's checkers validate documents whose *shape* is ours. Fix: ship the
templates as part of the product. This is the least work and arguably the most
valuable thing in the box — the registers are the part a college course can
teach directly.

---

## What I would ship first, if it ships in pieces

1. **Suite 3 + suite 5** — lowest coupling (47 refs / 2,477 lines), immediately
   useful on any JavaScript codebase, and suite 3 is the differentiator.
2. **Suite 7** — the harness, which turns the rest into something that runs.
3. **Suite 6** — the registers and their checkers; mostly templates.
4. **Suites 1 and 2** — the highest-value defect classes and the ones needing
   the adapter (b). Do them after the adapter exists, not before.
5. **Suite 4** — last, because it needs the backend module (c) and a live
   database to prove anything against.

---

## Size, honestly

**The documentation half is done or nearly so.** Every tool in this package
already carries a docstring naming the incident that produced it, what it
catches, and what it cannot see — that standard has been enforced per-commit for
weeks. Assembling it into per-suite guides is real work but it is *writing*, not
design.

**The genericisation half is not a tidy-up.** 404 coupling references across
13,100 lines, and the adapter interface (b) is a design problem that has to be
got right once and then implemented per tool. My estimate, and it is an estimate:

| Piece | Size |
|---|---|
| `toolkit.config.json` + path indirection (a) | 1 session |
| Adapter interface design + SAIRN reference implementation (b) | 1–2 sessions, and it should be **reviewed before anything is built on it** |
| Suites 3, 5, 7 ported onto the config + adapter | 1–2 sessions |
| Suites 1, 2 ported | 2 sessions |
| Suite 6 templates + checkers | 1 session |
| Suite 4 backend module (c) + port | 2 sessions |
| Per-suite guides, install, worked examples | 1–2 sessions |

**Roughly 9–12 focused sessions**, with the adapter design as a gate the rest
depends on.

**Two things I would want decided before starting the build**, not during it:

- **Does the package need to run on a codebase that is not JavaScript?** If yes,
  the adapter interface is materially bigger and suites 1, 2 and 5 change shape.
  If no — JS/HTML only — the estimate above holds.
- **Does it ship as one installable package or as seven?** Seven suites that can
  be bought and adopted separately is a different structure from one toolkit,
  and it changes the harness in suite 7.

**One risk worth naming up front.** Every one of these tools earned its keep by
catching a real incident *in this codebase*. Genericising strips exactly the
specificity that makes them accurate — the false-positive rate on somebody
else's code is **unknown**, and this package's own standard says a checker that
false-alarms early gets switched off before it is ever trusted. The honest
mitigation is to run each ported suite against two or three real outside
codebases before shipping, and to publish the measured false-positive rate per
checker rather than a claim that it works.
