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

---

## 4. THE SHA EXTRACTOR — the old sweep was wrong in BOTH directions, not just one

**Corrected 2026-10-07.** The dispatch premise was that my 8-hex sweeps
**over-report ABSENT**. They did. They also **under-reported ORPHANED**, which
is the half nobody had noticed and the half that matters.

| | old extractor | fixed extractor |
|---|---|---|
| pattern | `\b[0-9a-f]{8}\b` — exactly 8, counted as a sha | hex RUN, length 8–40 measured against the whole run, with four rejection rules |
| distinct tokens | 87 | **111** |
| ON-REF | 66 | **73** |
| **ORPHANED** | 6 | **17** |
| ABSENT | 15 | 21 |
| rejected as not-a-sha | 0 | **10**, by reason |

**Why ABSENT rose rather than fell, and it is not a regression.** Ten
false positives were rejected — but the old `{8}` pattern also *missed* every
12- and 40-character form, so the fixed run sees many more real shas in all
three states. Netted out: **10 non-shas removed from ABSENT, and 11 genuine
orphans found that the old pattern was structurally blind to.** The old sweep
was not merely noisy; it was quiet about the state that needs action.

**The ten rejected, by reason, printed by the tool itself:**

    all digits -- a number, not a hex id   8   000000000000 1234567890123 40318627
                                               4111111111111111 50000000000001 55889165
    date shape YYYYMMDD                    2   20260318 20260825

**The rules, each with its own selftest arm:** minimum length 8; all-digit
strings rejected; `YYYYMMDD` date shapes rejected by name even though rule 2
subsumes them, so the arm can say *why*; full 8-4-4-4-12 UUIDs masked out of the
text **before** matching, so a scratchpad session id contributes nothing rather
than contributing its first block; and length measured against the whole hex
**run**, because `\b` does not separate `4111111111111111`.

**12 selftest arms: 8 false-positive shapes, 4 paired positives, 1 anti-vacuity
arm.** The paired positives (an 8-char prefix, a 40-char sha, a 12-char prefix,
an uppercase prefix) exist because *reject everything* is the easy wrong fix
here, and the anti-vacuity arm proves a **bare** 8-char hex token is still kept
— so the UUID arms are not passing because the length rule rejected them.

**Three identical runs:** `PROGRAM_EXIT=0` each, and all three outputs
**byte-identical**. First run clean.

**WHAT IT STILL CANNOT DO, stated rather than discovered later.** It cannot tell
an 8-char mixed-hex token that is *not* a sha — an md5 prefix, a colour code
without `#` — from one that is. Two such tokens remain in the ABSENT column:
`4975e2e9` and `c430231c`, which are **scratchpad session UUIDs quoted as bare
8-char tokens** in the batch-12 caveat paragraph that named them as false
positives. The UUID mask catches them in a path; it cannot catch them in prose.
**The report naming three states is the fix, not a cleverer regex.**

**Where the durable version belongs:** this is my scratchpad sweep, which is the
tool that produced the wrong figures and therefore the tool the dispatch asked
me to fix. The platform's durable sha reader is `tools/doc_sha_reseat.py`, which
is **cc's**, so the rules above are routed rather than copied in.

---

## 5. THE 83 — a CENSUS, and it is 31 of 83

**Measured 2026-10-07 at `a7b6b58c`.** The 83 is re-extracted from the pinned
run log itself rather than quoted — `^  FAIL\s+(?:py|node)\s+(\S+)` over
`pinned2_stdout.txt` returns **83 rows**, which is the number that log's own
summary line states.

**A row counts as individually verified when its register `environment` stamp
carries a real SHA** — meaning somebody ran it alone and recorded which commit.
That is a stricter test than "I ran it": it requires the commit to be written
down.

| | |
|---|---|
| the 83, re-extracted | **83** |
| register rows with a SHA-stamped individual run | **32** |
| **of those, inside the 83** | **31** |
| still unverified of the 83 | **52** |

### The one verified row that is NOT in the 83, and it confirms a diagnosis

`tests/push_gate/check9_probe.py` is SHA-stamped and individually run — and it
is **not** one of the 83. The pinned run reported it **SKIPPED**, not FAIL. That
is exactly consistent with this batch's diagnosis of it: check 9 declines to
judge a docs-only outgoing range, so it emits nothing. **The row is red when
driven directly and skipped in a suite run**, which is the environment
dependence the stamp exists to record.

### What 31 of 83 does NOT mean

* **It is not 31 confirmed failures.** Of the 31, **four exit 2** — a
  could-not-run, not a failure — and **one now exits 0**
  (`run_primitive_obsession_probe`, fixed under convention 18 and RECOVERED).
* **The 52 are not presumed red.** They are *unmeasured individually*. The
  pinned run is not a census for the reason this platform already recorded: two
  probes in that very run gave opposite verdicts depending only on whether they
  ran in the clone or in a linked worktree.
* **Eight of the 31 carried no `exit_code` field until this batch**, only an
  environment stamp. Backfilled from the runs recorded in their own `why`
  text — which is why the field exists rather than being inferable from prose.

---

## 10. CONVENTION 18 — 2 of 8 fixed, and the second fix corrected my own diagnosis

**`tests/run_write_path_scan_probe.py` fixed 2026-10-07, verified alone,
ablated.** That makes **2 of the 8** suites in the convention-18 family fixed —
`run_primitive_obsession_probe` in batch 12 and this one — with **6 open and
carrying artifacts**.

### The violation, and why it was not visible before

    _loosened = dict(_shipped['counts'])
    _loosened[_worst] += 5          # ONLY the worst app

That arm's stated subject is *"a count that FELL is not a regression"* — a
property of the **ratchet**. Loosening one app silently made its outcome depend
on **every other app matching its baseline** — a property of the
**repository**. Two assertions, one arm, and it was failing for the second one.

Every app is loosened now, so the arm asserts only its own subject.

### And it corrected a diagnosis I wrote in batch 12

I had recorded *"a baselined count FELL"*. **Measured at `a7b6b58c`: the shipped
baseline records 25 sites and the tree measures 25 — the TOTAL AGREES — and the
shipped-baseline arm fails anyway.** One app **rose** while another **fell**.

A fall alone could not fail a ratchet that tolerates falls, which is the half I
had backwards. **The redistribution is invisible to a total**, and catching it
is the whole reason the ratchet is per-app — so this row is evidence *for* the
tool's design rather than against it.

### Verification

| | |
|---|---|
| failing arms | **2 → 1** |
| runs | **two**, both `PROGRAM_EXIT=1`, both naming the same single arm |
| ablation | the ratchet made intolerant of a fall → **the fixed arm FAILS**; subject restored **byte-identical** |

**The one remaining failure is the genuine live-tree arm** (*"the shipped
baseline PASSES today"*), which is correct behaviour and stays.

**STILL NOT CLEARED:** which app rose and which fell is not named.
`tools/write_path_fault_scan.py` exposes `apps(argv)` and `scan(path)` rather
than a per-app counter, so the comparison needs the ratchet's own code path — and
re-implementing it is how a wrong denominator gets built.
