# Item 47 — First Article Inspection on the three tools the gate demanded

**2026-09-16 (Fourth).** Report only, never gated, per the item's own terms.

**Subjects:** `tools/assurance_case.py` (item 5), `tools/risk_event_tree.py`
(item 84) and `tools/dora_metrics.py` — all three built the previous round and
first committed on 2026-09-16, which is the FAI requirement date.

**Machine-readable record:** `docs/first-article-inspections.json`.
**Gate:** `python tools/first_article_check.py`.

---

## The gate demanded this, which is the point of having built it

`tools/first_article_check.py` was built on 2026-09-15 with `required_from`
set to **2026-09-16** — deliberately one day out, because 22 tools had been
committed that day by four parallel sessions and none of them could have
followed a rule that did not exist yet.

The next thing committed after that date was **my own work**, and the gate
reported three findings against it. That is the pre-deployment half item 63
flagged as missing, biting on the session that built it, on its first
opportunity. Nothing about it needed persuading.

## Result

| | claims | arms before | **unverified at start** | unverified now |
|---|---|---|---|---|
| `assurance_case.py` | 10 | 39 | **2** | 0 |
| `risk_event_tree.py` | 7 | 29 | **2** | 0 |
| `dora_metrics.py` | 9 | 36 | **2** | 0 |

Six unverified claims, and they are **the same two claims on all three tools**.

## The same two gaps, three times — which is the finding

**1. "Exit 2 when it could not run."** Every one of the three states an exit-2
COULD-NOT-RUN contract in its header, and not one of them had an arm for it.
All three had arms for exit 0 and exit 1.

This is not a coincidence, it is a **habit**: the interesting exits are the ones
that carry a verdict, and the exit that carries *no* verdict is the one nobody
writes a test for. It is also the most consequential of the three, because
folding a could-not-run into a finding is precisely **PR §1.11** — and all three
tools cite that discipline in their own headers while failing to verify their
own compliance with it.

**2. "REPORT ONLY."** All three say it. None of them checked it, despite it
being mechanically checkable three separate ways: absent from the report-only
runner `REGISTRY`, present in `NOT_PROMOTED` as a deliberate decision, and not
invoked by the push gate. A sentence in a header is not a constraint.

All six arms were added and all six pass.

## What FAI could NOT settle

Five claims across the three are `cannot-test`, and separating them from the six
above is the judgement an arm-by-arm view cannot make:

- **Three SCOPE disclaimers on the assurance case** — not a claim that Tier A
  data is safe, that the evidence is sufficient, or that this is a certification
  artefact. No arm can show a document is not being read as the thing it
  disclaims.
- **The event tree's independence caveat** — the figures are a FLOOR, not an
  estimate. Stated in the header and in every run's output; no arm can show a
  reader did not treat the floor as the answer.
- **DORA's "not that a Vercel deployment succeeded"** — a claim about what the
  data source can see. A commit that failed to build counts as a deployment
  here. Confirming otherwise needs the Vercel deployment API, which is outside
  this tool by design and is the same repository-is-not-the-deployment limit the
  assurance case draws as its undeveloped goal **G10**.

## What this inspection does NOT claim

- **An arm existing is not an arm being right.** FAI checks coverage, not
  correctness.
- **Three artefacts.** The uninspected count is printed by
  `first_article_check.py` on every run; it is deliberately not written here,
  because a count in prose goes stale the first week.
- **The mapping was made by reading.** Word-overlap scoring of prose claims
  against prose arm labels returned 38% with five false positives out of five on
  this platform, and the extractor in `--worksheet` is labelled a worksheet for
  that reason.
