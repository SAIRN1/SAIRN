# Coverage ledger — what is EXHAUSTED at this depth, and what that does not mean

**fourth (Ted), 2026-10-07.** Two sweeps are recorded here as **exhausted at
the depth they operate at**. That phrase is doing work: it means every item in
a re-derived population was measured by a named command at a named commit, and
it means nothing at all about the depths those commands do not reach. The
limits are stated in each row rather than left for a reader to discover.

---

## 1. GAP-DOCUMENT VERIFICATION — 36 of 36, EXHAUSTED at the arithmetic depth

| | |
|---|---|
| **population** | **36** documents, re-enumerated at HEAD. The dispatch premise said *"5 of 35"*; that was the batch-9 figure, batch 10 checked all 35 at headline level, and the population re-enumerates to **36** |
| **command** | `python <scratchpad>/gapverify2.py $(cat gapdocs.txt)` |
| **commit** | `762b084b` |
| **date** | 2026-10-06 |
| **exit** | **`PROGRAM_EXIT=0`**, read from the program's own invocation |
| **runs** | **three** against that SHA. The first returned the same file-citation and count-claim totals as the last; only the citation column moved, because the two states added between runs move citations |
| **result** | documents NAMED 36 / READ 36 / ABSENT 0 · file citations 321, 4 missing · count claims 47 hold, 17 broke, 173 could-not-check, 4 ambiguous · line citations 6 hold, 5 broke, 21 could-not-check, 1 ambiguous, **15 misattributed by the tool** |

### What EXHAUSTED means here, and what it does not

**Exhausted:** every checkable **count claim** and **line citation** in all 36
documents has been re-derived against the file the document itself names.

**NOT exhausted, and these are not caveats, they are the larger part:**

* **No verdict in any of the 36 documents has been re-derived.** This pass
  checks arithmetic, never argument. A document whose every figure holds can
  still reach a wrong conclusion.
* **173 count claims and 21 line citations name no file at all** and are
  unreachable by any version of this tool. That is roughly **60% of the count
  claims in the corpus** and it is a ceiling, not a tuning problem.
* **The 17 broken count claims are measured, not triaged.** `applicant`
  46 → 0 in `stonedesk.html` and `public catalog` 17 → 0 in `sairnsenior.html`
  are capabilities going the *wrong* way and are the two to read first.
* **The tool cannot see a correction written as strikethrough.** Three
  already-corrected SAIRNdental figures were reported stale by an earlier pass
  for exactly this reason.
* **15 of the 21 citations the tool first called broken were ITS OWN wrong
  denominator** — roofing `rf_*` judged against `sairndental.html` and dental
  `dnt_*`/`cdt_*` against `sairnroofing.html`, in one document covering three
  verticals. That became convention **17**. A future reader should assume the
  same class exists in whatever the tool cannot attribute.

---

## 2. SPAN SWEEP — 34 of 34, EXHAUSTED at the does-it-parse depth

| | |
|---|---|
| **population** | **34** span-taking sites, re-derived. The dispatch premise said *"14 remaining of 38"*; **143** sites match a function-start locator, **110** take no span at all, 143 − 110 = 33, plus one `FIXED_WINDOW` site = **34**. The 38 was an earlier raw candidate count including sites later shown not to take a span. There is no "14 remaining" |
| **command** | `node <scratchpad>/spanparse.js` |
| **commit** | `762b084b` |
| **date** | 2026-10-06 |
| **exit** | **`PROGRAM_EXIT=0`** |
| **judge** | **V8.** Each span is written to a temp file and fed to `node --check`. A span that does not parse as a function expression is not a function body, whatever any brace counter says |
| **result** | `SITES: 34   WALKER SPANS THAT PARSE: 34   SITE SPANS THAT PARSE: 31   COULD NOT EVALUATE: 0` |

### The three real findings

| site | app / source |
|---|---|
| `tests/sairnbiz_vendor_ytd_derivation.js:268` | `sairnbiz.html`, `function rVends()`, bound `marker0` on `$('vntbody').innerHTML=html;` |
| `api/sd-data-leg-session-gate.test.js:211` | `sairnlegacy.html`, `function sdnData(...)`, bound `marker` on `return fetch(DATA_API` |
| `api/_lib/stonedesk-remnant-publishing.test.js:201` | `stonedesk.html`, `window.pcToggleRemnant=async function`, bound `func` on `function pcRenderRequests` |

All 34 **walker** spans (`tests/lib/fn_span.js`) parse, so the shared helper is
clean and the three defects are in what those three suites take for themselves.

### What EXHAUSTED means here, and what it does not

**Exhausted:** every site in the re-derived population has been measured by a
real JavaScript parser, in both the walker and the site-span direction.

**NOT exhausted:**

* **"Parses as a function" is not "is the RIGHT function."** A span can parse
  cleanly and still start or end in the wrong place. Nothing here checks that
  the span is the body the suite intended.
* **The three defects are NOT repointed.** A repoint needs a **planted control
  per site** proving the new span is the right one — per-site work, and the
  next step.
* **The 110 "take no span" sites were classified, not verified.** They were
  excluded by a scanner, and a site wrongly excluded is invisible to this
  measurement entirely.
* **One SHA, one machine.** Measured at `762b084b` only, and a span bound to a
  marker string in a 2MB app file is exactly the kind of thing that moves.

---

## 3. WHY A COVERAGE LEDGER AT ALL, and the figure that is NOT in it

A sweep reported as "36 of 36" or "34 of 34" reads as *done*. Both are, at one
depth, and neither is at the depth a reader cares about: whether the gap
documents are **right**, and whether the spans are **correct**. Writing the
depth beside the ratio is the only thing that keeps the ratio honest, and it is
item **3** of the cross-domain disciplines — publish the denominator and what it
is a denominator *of*.

**The figure deliberately absent from this ledger:** any statement that the
suite as a whole is green or that the tree is clean. The last whole-tree run,
`PROGRAM_EXIT=1` at `762b084b`, reported 83 failing files — and two probes in
it gave **opposite verdicts** depending only on whether they ran in the live
clone or in a linked worktree. Until `tools/run_all_tests.py` carries cody's
isolation fix, **no whole-tree or `--pinned` figure belongs in a coverage
ledger**, which is why neither is here and why every suite this batch was run
individually.
