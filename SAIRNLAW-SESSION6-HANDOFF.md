# SAIRNlaw — Session 6 Handoff

**Written 2026-08-23, at ~97% context, mid-verification.** Everything below was
re-checked against the real repo and the live site immediately before writing —
none of it is recalled from earlier in the session.

Read this before touching the mock trial module.

---

## 1. The goal

**LeMAJ argument decomposition for the mock trial / AI-judge module.**

Decompose the user's free-text position into **discrete legal data points**
before anything critiques it, then attack each point individually rather than
the paragraph as a whole. A holistic critique lets the adversary answer the
easiest reading of an argument; forcing it apart first means every element gets
attacked, including the ones the lawyer glossed over.

**The guardrail that makes it safe, and the reason it is not just a prompt:**
every data point must carry a **verbatim span copied from what the user
actually wrote**, and that span is checked **mechanically** against the original
text before the point is used. A decomposition step that paraphrases can quietly
invent a claim the lawyer never made and then attack it — reporting a weakness
in an argument that does not exist, which is worse than not decomposing at all.
Same show-your-work discipline as the citator and the Wex parser: **the model
asserts, the code checks.**

Citations raised in the critique are grounded through the **real** citator
`verify` action (built earlier this session), never invented. The hard rules
from the rest of the module still apply: **no win-probability number, ever**,
and no standalone verdict.

---

## 2. Current state — what is pushed vs. what is not

**Everything is pushed. The working tree is clean. There is no uncommitted
work.** Verified three ways immediately before writing this:

```
git status --porcelain            -> (empty)
git diff --stat origin/main HEAD  -> (empty)
git log --oneline -3
  afe7b7b Merge branch 'main'
  a667e06 feat: SAIRNlaw mock trial -- LeMAJ argument decomposition into legal data points
```

**The mtRun rewiring IS pushed** — this was the specific thing worth confirming,
because it was applied in two failed attempts before it succeeded. Confirmed
present in the pushed commit and on the live deploy:

```
git show HEAD:sairnlaw.html | grep -c "mtDecompose(pos).then"   -> 1
git show HEAD:sairnlaw.html | grep -c "attacked separately"     -> 2
curl -s https://sairn.vercel.app/sairnlaw | grep -c "mtDecompose(pos).then\|mtAnchorPoints"  -> 3
```

### Shipped this session (all live)

| commit | what |
|---|---|
| `e0dcbdc` | Badge honesty patch — stopped asserting a citation check that never ran |
| `41eb491` | **`verify` action on the citator** — real citation→CourtListener resolution, cache-first, batched |
| `ed14e1b` | Citation footnote describes the states actually present |
| `a667e06` | **LeMAJ decomposition** — this handoff's subject |

### In scratchpad only — NOT in the repo, and deliberately so

These are throwaway build/test scripts, not product code. Nothing depends on
them; they are listed so nobody hunts for them:

```
scratchpad/build_lemaj.py      first (failed) splice attempt — superseded
scratchpad/lemaj_block.js      the JS block that was spliced in — now IN sairnlaw.html
scratchpad/rewire_mtrun.py     the mtRun rewiring script — already applied
scratchpad/test_lemaj.js       anchor-guard isolation test — see §4
scratchpad/verify_mocktrial.py browser round-trip harness (reusable)
scratchpad/verify_lemaj.py     NOT CREATED — the run was cut off before it was written
```

---

## 3. The `rep()` bug — what it was, and whether the fix is what shipped

**What happened.** `scratchpad/rewire_mtrun.py` defines
`rep(old, new, label)`. The fourth edit passed what looked like three arguments
but was actually four, because two adjacent Python string literals were
separated by a comma instead of being concatenated:

```python
rep("...adversarial critique, not a prediction</div>' +",
    "...adversarial critique, not a prediction' +",      # <- literal 1
    "      (anchored.length ? ...) + '</div>' +",        # <- literal 2, became arg 3
    'label per-point critique')                          # <- became arg 4
TypeError: rep() takes 3 positional arguments but 4 were given
```

**Why it did no damage.** The script writes the file only at the very end, after
all four edits. The exception fired on edit 4, so **nothing was written** — the
first three successful edits were discarded with it. The failure was atomic.
This is worth knowing because the console output showed three `ok:` lines before
the traceback, which reads like a partial write. It was not.

**The fix** was to join the two literals with `+ nl +` so they form one string.

**Confirmation the fixed version is what shipped:** after the fix the script ran
clean (all four `ok:` lines, then `mtRun rewired`), `node --check` passed on the
extracted script block, and `git status` is now empty with `origin/main` matching
`HEAD`. The live deploy carries the wiring (greps above). **Yes — the syntax-clean
version is the one that got pushed.**

---

## 4. The anchor-guard isolation test — it PASSED

`scratchpad/test_lemaj.js`, extracted verbatim from `sairnlaw.html`:

```
17 passed, 0 failed
```

It ran to completion **before** the cut-off. What it proves:

- Genuine spans anchor; an **invented** claim (`"the landlord fraudulently
  induced the lease"`, absent from the position) is rejected
- A span **stitched from non-adjacent words** of the real text is rejected
- Normalisation forgives **typography only** — curly vs straight quotes,
  collapsed whitespace, case — and a **negated/altered** span is still rejected
- Unknown point types fall back to `legal_claim` rather than rendering raw
- The JSON parser handles bare arrays, fenced arrays and prose-wrapped arrays,
  and returns `null` (rather than guessing) on non-JSON or on a JSON object
- A **planted failure** confirms an absent span does not anchor

**What was cut off** was the *next* step: `verify_lemaj.py`, a live browser
round-trip. That file was never written and never ran. **The decomposition has
never been exercised end-to-end in a real browser session.**

---

## 5. Exact next step

**Run the live browser verification of the decomposition. Nothing else is
outstanding.**

Write `scratchpad/verify_lemaj.py` modelled on the existing
`scratchpad/verify_mocktrial.py` (which works and was used successfully twice
this session). Reuse its login flow verbatim:

```
license  LAW-TEST-2026
employee hank-verify
PIN      418306
```

Steps: log in → `nav('mocktrial')` → select role `opposing` → fill
`#mt-position` → click `#mt-run-btn` → wait for `#mt-result` to stop showing
"Stress-testing".

**Assert:**

1. `#mt-points` renders and contains `legal data point`
2. `#mt-points .srow` count >= 3 (discrete points extracted)
3. Every point badged `Anchored` or `Not in your text`
4. At least one point **Anchored**
5. **Two** `/api/claude` calls fire (decompose, then critique) — not one
6. The critique header says `attacked separately`
7. **No** probability pattern in either `#mt-points` or `#mt-result`
8. No uncaught page errors

Suggested position (this one reliably produces citations, used successfully
earlier this session):

> We represent a criminal defendant. The prosecution failed to disclose a police
> report showing an alternate suspect, and separately obtained cell-site location
> data covering 7 days without a warrant. We intend to move to suppress the
> location data and to seek dismissal for the non-disclosure. Cite the
> controlling Supreme Court authority.

### Two things to watch for

- **The unanchored path may not trigger naturally.** If every point anchors, the
  "Not in your text" branch is untested live. It is covered by the isolation
  test, but if you want it exercised in the browser you will need to force it
  (e.g. stub `mtDecompose` to return a point with a fabricated span).
- **The no-decomposition fallback** (`dec.ok === false`) is also untested live.
  It should render "**Not decomposed.**" and the critique should address the
  position as a whole — it must **never** silently fall back while implying the
  argument was decomposed.

### Do not re-verify these — already done and confirmed live this session

- Citation `verify` action: Brady (`373 U.S. 83`) and Carpenter (`585 U.S. 296`)
  both resolve with real case names and CourtListener links. Fabricated cites
  (`999 U.S. 12345`, `888 U.S. 777`) return `not_found`. Mixed batch of 4 real +
  1 fake resolved correctly in **one** budget unit.
- Probability guard: 12/12 against real phrasings, plus two full browser
  round-trips with zero predictions in real model output.

---

## Standing context a fresh session needs

- **CourtListener limits are the real constraint on the citator**: 5/min,
  50/hour, 125/day for **all** SAIRNlaw firms through one shared token (the
  limiter runs tighter at 4/45/115 for headroom). This is why `verify` batches
  every citation into one call and checks cache first. Do not make it
  one-call-per-citation.
- **Blockers that are not code and not mine to clear:** `CANLII_API_KEY` is
  still unset (Canada reports unavailable honestly; key is in human review).
  `sql/sairnlaw_wex_intl_schema.sql` **has been run** — Wex and Find Case Law
  both work now.
- **The Aug 20 commitment list is stale and has now misdirected three separate
  scope requests.** All four of its items were already built on 2026-08-21
  (`1779346`, `ff26b05`, `e4fbb91`). See
  `docs/sairnlaw-international-coverage-scope.md` for the international-coverage
  correction, which also records why BAILII and AustLII are permanently excluded
  (their own terms prohibit automated access — no engineering closes that).
- **Not started, flagged for their own scope pass:** jury difficulty/demographic
  modelling was already built in `e4fbb91` with the Batson guardrail enforced in
  code (`juryCheckStrikeReason()`).
