# Cross-app dead-function sweep — 100 zero-reference functions, and ten of them are security layers

**Date:** 2026-08-31 · **Session:** CC · **Tool:** `tools/sairn_dead_function_sweep.py`
**Raw output:** `docs/2026-08-31-dead-function-sweep.txt`

## Why this ran when a reachability sweep already had

`tools/sairn_reachability_probe.py` swept all 16 apps on 2026-08-30 and reported
"one real instance found". That number was correct for the question it asked and
is **not** a statement about the platform. Its source shows why:

```python
targets = [n for n in F if RESTORE.match(n)]
```

`RESTORE` is a name whitelist — `reverify|restore|resume|rehydrate|recheck|
checksession|loadstate|hydrate|refreshsession|validatetrial|checktrial|
checklicen|verifylicen|checkauth|restoresession|bootstrapsession`. Every
function whose name does not match was never examined. That was the right scope
for the SAIRNcash returning-customer gap, and it found `mechRestore` correctly.

The gap was demonstrated, not assumed: working `sairnmechanical.html` by hand on
2026-08-31 turned up **eight** zero-caller functions in the one file the probe
had already flagged — `loadWeather`, `renderRangeBars`, `crSave`, `crPostGL`,
`crUpdate`, `aiFollowUp`, `loadPricing`, `loadLastSync`. None matches `RESTORE`,
so none was ever a candidate.

The signal this tool uses is the one the probe's own header identifies as
needing no entry-point tracing: **a function nothing references anywhere is dead
however the app is entered.** So this tool does not trace reachability at all.

## Result

| App | Functions | Dead |
|---|---:|---:|
| stonedesk.html | 1050 | **88** |
| sairnmechanical.html | 59 | 5 |
| sairnscape.html | 165 | 5 |
| sairnbuild.html | 444 | 1 |
| sairnvet.html | 363 | 1 |
| sairnbiz, sairncare, sairncash, sairncode, sairndental (×3), sairndesign, sairngrounds, sairnlaw, sairnlegacy, sairnroofing, sairnsenior, stonedesk-hr | 2176 | 0 |
| **Total** | **4257** | **100** |

Fourteen of the 100 were hand-verified against the raw file by independent
grep — zero false positives in that sample. The other 86 have not been read
individually and **must be before anything is deleted.**

## The finding that matters: ten security layers are defined and never called

`stonedesk.html` carries a numbered security system, `// LAYER 1` … `// LAYER
30`. Fourteen of those thirty are implemented as a named function. **Ten of the
fourteen are never referenced anywhere in the file:**

| Layer | Function | Status |
|---|---|---|
| 1 — Domain Allowlist Fetch Interceptor | `fetch` patch | alive |
| **2 — XSS Output Sanitizer** | `safeHTML` | **DEAD** |
| **6 — Brute-Force Protection on PIN** | `saTrackLoginAttempt` | **DEAD** |
| 7 — Prompt Injection Detection | `saCleanPrompt` | alive |
| 8 — PII Scrubbing (24 patterns) | `saScrubPII` | alive |
| 9 — Data Exfiltration Monitor | `XMLHttpRequest` patch | alive |
| **16 — Rate Limiting** | `saCheckRateLimit` | **DEAD** |
| **17 — Response Sanitization** | `saSanitizeResponse` | **DEAD** |
| **19 — Request Signing** | `saSignRequest` | **DEAD** |
| **20 — Prompt Injection on Every Claude Call** | `saSecureClaudeCall` | **DEAD** |
| **21 — Anomaly Detection** | `saDetectAnomaly` | **DEAD** |
| **24 — Data Minimization Checker** | `saCheckDataMinimization` | **DEAD** |
| **27 — Right to Delete (one-click wipe)** | `saWipeAllData` | **DEAD** |
| **30 — Security Status Dashboard** | `saShowSecurityStatus` | **DEAD** |

**Scope, stated so this is not over-read.** The remaining 16 layers are
implemented as meta tags, self-installing IIFEs or event listeners. Those are
**not covered** by a reference count and have **not** been assessed — they are
neither cleared nor condemned here. Layer 7 being alive means some
prompt-injection defence does run even though Layer 20's wrapper does not.

Why it is worth its own section rather than a line in a list of 100: this is the
fabrication class pointed at security. The code is present, named, numbered and
commented, so a reader — an auditor, a customer's IT reviewer, or us writing a
proposal — concludes the control exists. It provides no protection. A missing
control and a present-but-unreachable control look identical from the outside
and are identical in effect; only the second one also reads as evidence that the
work was done.

**Nothing here has been changed.** Wiring a sanitizer into a live output path is
not a mechanical edit, and ten of them at once is a design decision about which
controls this product actually claims. That is Michael's call, and
`sairn-decision-gate` applies before any of it is described as implemented.

## UPDATE 2026-08-31 — nine of the ten wired and live-verified

Michael's call: wire them. Nine are wired (`5e03232`) and verified against
`sairn.vercel.app/stonedesk` by behaviour, not by reading the diff. Layer 2 is
deliberately not wired — see below.

| Layer | Verified how | Result |
|---|---|---|
| 6 Brute-Force PIN | 20 failed attempts through `saTrackLoginAttempt` | lockout overlay appeared, `L6-BRUTE` logged, counter reset on success |
| 16 Rate Limiting | primed the limiter's own window, then one **real** proxy call | `REJECTED: SAIRN Security: rate limit exceeded (30 calls/min)` |
| 17 Response Sanitization | asked Claude to **construct** `github_pat_` + 20 chars, so the pattern was absent from the request | caller received `[TOKEN-REMOVED]` — Layer 17's own string, and the only place it exists |
| 19 Request Signing | inspected the real outbound payload | `_ts` and `_origin` present |
| 20 Prompt Injection | real call carrying "Ignore previous instructions…" | outbound body became `[Content removed by SAIRN Security: prompt injection detected]`, `L7-INJECT` logged |
| 21 Anomaly Detection | spy on the real request path | called with `stonedesk:/api/claude`, returned `false` for a single request — correct, not a false alarm |
| 24 Data Minimization | wrote through the real `stRaw()` helper | `Sensitive fields in stored data: ssn, creditCard` logged **and the write still happened** |
| 27 Right to Delete | button present and function reachable | **NOT fired** — see below |
| 30 Security Status | invoked the control | real report with live counts from this session's own events |

**Layer 17's test was designed to exclude a confound and the first attempt
failed it.** Asking Claude to echo an `sk-…` string returned `[KEY-REDACTED]`
— which looks like a pass and is not one: Layer 8 scrubs *outbound* content, so
Claude only ever echoed a redaction that had already happened before the request
left. The valid test makes the model build the token from parts so the pattern
cannot appear in the request. Only then does a redacted response prove the
*response* path did it.

**Layer 27 was not fired, on purpose.** It calls `confirm()` — which blocks the
browser automation channel entirely — and then clears localStorage including the
licence key. Reachability is proven; behaviour is not. That is a gap in this
verification, stated rather than glossed. It is a ten-second manual check.

### Two things found while verifying, neither of them fixed

**`maxLoginAttempts` is 20, not 5.** A five-attempt probe showed no lockout and
looked like a wiring failure; it was the probe's threshold that was wrong. The
layer works at 20. Whether twenty guesses at a numeric PIN before any delay is
the intended policy is a separate decision — the code is doing what it was
configured to do.

**Layer 5's session-lock screen is guarded by two hardcoded 4-digit PINs.**
`saUnlock` uses `Object.values(CODES)`, and `CODES` is `{sales, admin}` with
two 4-digit literals sitting in a publicly served file. The front door moved to
per-employee server-side auth (`api/sd-auth.js`); the *lock* screen did not. So
a session that auto-locks after 30 minutes idle can be reopened with a PIN
anyone can read out of the page source. (The literal `['1234','9999']` fallback
in that function does not apply here, because `CODES` is defined — checked
live, not assumed.) Not changed: making the lock screen re-authenticate is real
work and a product decision, not part of wiring dead layers.

## Secondary pattern: superseded parallel implementations

Several dead functions are older implementations of features that **do** work
under a different name — so the feature is fine and the duplicate is litter:

- `vmAnalyze` / `vmPreview` / `sdVeinExport` are dead, but the live Vein Match
  panel calls `sdVeinAnalyze()` and `sdVeinPrint()`. **The feature works.** A
  memory note recording StoneDesk's six AI features as real and live remains
  correct; "every handler defined" was true and is simply a weaker claim than
  "every handler reachable".
- `crSave` / `crPostGL` / `crUpdate` appear dead in **both** stonedesk.html and
  (until today) sairnmechanical.html — the same abandoned Check Register copied
  between apps. The sairnmechanical pair was deleted in `325c5ab`; stonedesk's
  `crSave` even carries a comment saying it is kept as a no-op.
- Sixteen `sd*Export` functions (`sdCRMExport`, `sdSeamExport`, `sdTaxExport`,
  `sdWasteExport`, …) are defined on `window` and never referenced. Whether the
  export buttons call something else or do not exist has **not** been checked
  per panel.

## How the tool was validated, and the two bugs found by validating it

The 2026-08-30 lesson — *"a checker's first draft over-reports, and shipping it
without hand-verifying its own output is how a check gets switched off"* — held
again. Two bugs, both found by checking the tool's output against the raw files
rather than by reading the tool:

**1. A runaway comment delimiter blanked 80.5% of a file.** The JS block-comment
rule was applied to the whole document, so this markup opened a comment:

```html
<input type="file" accept="image/*" capture="environment" ...>
```

`.*?` ran 204,534 characters forward to the first `*/` — inside a regex literal
in a later script — and erased every identifier in between. `sairncare.html`
reported **9 of its 12 functions dead** while `onclick="saveFacility()"` sat in
the markup. sairngrounds reported 19. Both are now clean, and their true
function counts are 206 and 238, not 12 and 83. Fixed by scoping JS comment
stripping to `<script>` regions, plus a guard that warns when stripping removes
more than 25% of a file — the failure was silent and exited 0.

**2. Named function expressions were counted as dead.** `sairnroofing.html` runs
its startup as `(function init(){ ... })()`. `init` appears once, so a reference
count called it dead while it executed on every page load. Fixed by requiring
declaration position; a first pass at that fix then discarded every
`async function` declaration, which was caught because `vmAnalyze` **disappeared
from the findings between two runs with no fix in between** — a finding
vanishing is as suspicious as one appearing.

The tool is validated against a synthetic probe covering 18 shapes: plain dead,
`window.x = function` dead, arrow dead, comment-only mention, called-bare,
called-as-`window.x()`, markup-`onclick`-only, passed-by-reference, alias
export, named IIFE, named callback, async dead, async alive, async IIFE.

## Known limits

- Object-literal methods (`foo: function(){}`) and class methods are not
  collected — neither reported nor cleared.
- Cross-file calls are not considered. These are single-file apps; any that
  stops being one breaks the assumption.
- A name appearing only inside a string counts as a reference.
- The `export-only` list under-reports aliases assigned through `window.x =
  window.y`, and is a prompt to read the file rather than a finding.

## Next

Nothing in the 100 has been deleted. The order that makes sense:

1. Michael's call on the ten security layers — wire, delete, or stop counting
   them as implemented. This is the only item with an outside-facing claim
   attached to it.
2. The `sd*Export` cluster, per panel: does the button call something else, or
   is export simply absent from that panel?
3. The rest of stonedesk's 88, read individually before any deletion.
