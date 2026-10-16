# LATEST — fourth / ted — batch b28 — 2026-10-16

**ALL SIX ITEMS DONE, manifest 6/6, opened as the FIRST action of the batch.**
`HEAD == origin/main` at **`3bd460ad`**, 0/0, **NOT forced** (ancestry-proved;
`grep -ci force` → 0 across all four push logs), and **landed verified ON ORIGIN
by reading the files back**. No `SAIRN_SEED_GATE` / `GATE_EXEMPT` /
`SAIRN_SKIP` in any form — **the push was REFUSED FOUR TIMES and every refusal
was read rather than overridden.** `settings.json` untouched, hooks untouched.
**0 files written under `api/ sql/ tests/`**; **`docs/tier-a-reviews.json`
BYTE-UNTOUCHED**; `tools/tier_a_review_gate.py` not edited. Auditor clones not
entered. **CONTEXT 49.1% of 1000k** (491,363 tokens).

---

## The five things

1. **TWO OF SIX DISPATCHED ITEMS RESTED ON A FACTUALLY WRONG PREMISE**, and
   both corrections are stated at the top of the artefact they affected rather
   than applied silently. Item 3's orphaned tbody / unfinished JS / HTML
   corruption **do not exist** — the parser returns **zero findings and zero
   unclosed tags** and all four script blocks pass `node --check`; the
   `grep -c '<tr'` that looked unbalanced was counting `<tr>` inside JS string
   literals. Item 4's *"four existing audit docs"* are **four of twenty**, and
   all eighteen real products already have one.
2. **A WRITE-AND-NEVER-READ ON MONEY (HIGH).** SAIRNdental has stamped
   `cdt_code` and `cdt_version` onto every charge since 2026-09-17 and its own
   comment states the guarantee — **both readers ignored the stamp** and looked
   the code up live from the mutable catalogue row, one of them **nine lines
   below its own comment stating the rule it broke**. Invisible to every
   structural check, because stamp and lookup agree on every row until the day
   the catalogue is edited — the one day the stamp exists for.
3. **THE TIER A LEDGER IS APPEND-ONLY PER-AGENT, AND THE bld_bids DISCHARGE
   LANDED THROUGH IT WHILE hank STILL HELD THE OLD FILE.** Three consecutive
   batches had lost that discharge to a file-level hold.
4. **cody's CHECK (4) IS A HIGH FINDING, DRIVEN.** The unrepaired predecessor
   defect sits **twelve lines above** the arm b27 repaired, and `bld_draws` has
   **no arm at all**.
5. **THE CHILDCARE SUBSIDY BILLING BASIS FLIPPED TWICE IN 26 MONTHS** —
   rescinded by final rule **2026-05-12**, effective **2026-07-13**, now a
   per-state option.

## Why per-agent shards and not one JSONL — the part worth keeping

The ledger **already** declared itself append-only in its own `merge_policy` and
`sairn_rebase_resolve.py` **already** 3-way merged it by identity. **So git was
never the contention.** `sairn_claim.py` decides on the **DECLARED FILE SET**,
so two sessions naming the same path block each other whatever the merge
semantics are — **and one shared JSONL is still one path.**

* Identity `(author_session, opened_at)`, **taken verbatim** from the legacy
  `merge_policy.identity`; `--validate` reports **IDENTITY DRIFT** if they ever
  disagree.
* Union read, last layer wins **FIELD-BY-FIELD** — a discharge line need not
  restate `resources`/`files`/`rules`, and a whole-record replace would erase
  them by omission. **That is a fixture, in the direction that would have been
  wrong.**
* **Migration proved LOSSLESS**, not assumed: 265 → 265, 0 only in legacy, 0
  only in the union, **0 differing**. Idempotent; legacy file **byte-identical**.
* **25 fixtures, both directions**, `--selftest` exit 0; every other mode runs
  them first and exits **2 COULD NOT RUN**.

**TWO DEFECTS IN MY OWN TOOL, FOUND AND FIXED RATHER THAN SHIPPED:** `--read`
first called all 265 migrated records *"superseded"* when every one was a
**byte-identical mirror of itself** — 265 edits reported where there were none,
the fabrication shape inside the tool built to stop one; and `--migrate` would
have written into **hank's** shard when a rebase brought his new record
mid-batch, contradicting the module's own rule, so the cross-author bulk move
now needs `--all-authors` and **names what it declines**.

## Next, shortest first

**cc:** land the **two function bodies** from
`docs/2026-10-16-fourth-b28-tier-a-shards-routed-to-cc.md` — until then the
discharge is **recorded but not seen by the gate**, and that is three batches of
contention still open. Then a **stored-field-vs-reader sweep** per app, which
would have found finding 2 on the day it was introduced. *(`tools/branch_census.py`
now exists — cc landed it during this batch, closing a routed item open for
five.)*

**cody:** check (4) — match over a comment-and-string-stripped copy, require the
**guard** not the substring, **then re-run N1 and N4 and confirm BOTH go RED**;
plus an arm for `bld_draws`.

**hank:** `docs/tier-a-reviews.json` is now a **read-only base layer** — keep
reading it, stop rewriting it once cc lands the change, append to
`docs/tier-a-reviews/hank.jsonl` instead.

**Michael:** the childcare vertical is **explicitly NOT recommended** by §5 of
its own audit, which lists what would have to be true first — a driven trial
account, one real centre director, and an owner for a 50-state rule matrix that
nobody has.

**NO LIVE VERIFICATION.** Nothing ran against a real Supabase. **The shards are
not authoritative and the push gate has never read one.** `sairndental.html` was
**never rendered** and `sairn-visual-review` did not run. The audit **drove no
competitor product** and interviewed nobody.
