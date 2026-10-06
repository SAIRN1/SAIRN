# Routed to cc — 2026-10-06 (fourth)

**Two findings in `tests/sairnbiz_vendor_ytd_derivation.js`. Neither is fixed
here and `sairnbiz.html` was not touched.** That file and that suite are both
in cc's active claim (claimed 2026-10-06, `FILES:` includes
`tests/sairnbiz_vendor_ytd_derivation.js`), and the dispatch that sent me here
named the same boundary. Declared per PR §4.3 rather than reworded past.

---

## 1. The suite is red on a STALE ANCHOR, not on the arm the red register names

`docs/known-red-suites.json` records this suite as failing the arm *"the
disclosure names only vendors the residual could carry OVER $600, and says the
count is undecided rather than reporting a number."* **That is no longer what
happens.** At HEAD the suite dies before that arm, at module scope.

Driven in this clone, 2026-10-06:

```
node tests/sairnbiz_vendor_ytd_derivation.js
```

exit code, on its own line:

```
1
```

Full output — seven arms pass, then it throws:

```
sairnbiz vendor YTD derivation
  ok   paid bills accumulate per vendor; Open/Overdue/Held count nothing
  ok   YTD means THIS year -- last year's paid bill counts nothing
  ok   a bill created-as-Paid has no paidDate and falls back to the bill date
  ok   vendor names join trimmed and case-folded
  ok   a string amount is COERCED, not concatenated -- the quiet wrong number
  ok   the fabricated stored field is read by NOTHING in the vendors panel: no display site reads x.ytd any more
  ok   CONTROL: removing the year filter is caught by the last-year fixture
node:assert:152
  throw new AssertionError(obj);
  ^

AssertionError [ERR_ASSERTION]: sbVendorPaidUndatedPriorYear not found -- anchor moved
    at Object.<anonymous> (C:\Users\marsh\Documents\SAIRN-fourth\tests\sairnbiz_vendor_ytd_derivation.js:140:8)
    at Module._compile (node:internal/modules/cjs/loader:1854:14)
    at Object..js (node:internal/modules/cjs/loader:1985:10)
    at Module.load (node:internal/modules/cjs/loader:1577:32)
    at Module._load (node:internal/modules/cjs/loader:1379:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47 {
  generatedMessage: false,
  code: 'ERR_ASSERTION',
  actual: -1,
  expected: -1,
  operator: 'notStrictEqual',
  diff: 'simple'
}
```

**The cause, derived at HEAD.** `tests/sairnbiz_vendor_ytd_derivation.js:138`
anchors on

```js
const START2 = 'function sbVendorPaidUndatedPriorYear(){';
```

and `sairnbiz.html` no longer has that name. It has, at `sairnbiz.html:4176`:

```js
function sbVendorPaidUndatedOtherYear(){
```

with its one caller at `sairnbiz.html:4223` (`var undAll=sbVendorPaidUndatedOtherYear();`).
Count of `sbVendorPaidUndatedPriorYear` in `sairnbiz.html` at HEAD: **0**.

That rename is the shape your own status row describes — *"the prior-year
function that also catches future-dated bills"* — so the app change looks
right and the SUITE is what did not move with it. The one-line repoint:

```js
const START2 = 'function sbVendorPaidUndatedOtherYear(){';
```

and the two assertion messages at `:140` and `:141` name the old identifier in
their text, so those strings want the new name too or the next failure reads
as being about a function that does not exist.

**Not applied here**, because a rename is the author's call: if `PriorYear`
was deliberately kept as an alias the right fix is in the app, not the test,
and I cannot tell those apart from outside your claim.

**`docs/known-red-suites.json` has been corrected** to say the entry is red on
a stale anchor rather than on the $600 band arm — that was my own record and
it was wrong about the cause. The entry still stands and is still owned by
`cc`: it is red, so deleting it would swallow the next real failure.

---

## 2. A SEPARATE finding, in the same file: a span 30 bytes short under an ABSENCE assertion

This came out of the 2026-10-06 span sweep (`d8392f80`), which measured 24
function-body spans against each function's true balanced closing brace.
`tests/sairnbiz_vendor_ytd_derivation.js:100`:

```js
const panel = src.slice(src.indexOf('function rVends()'),
                        src.indexOf('}', src.indexOf('$(\'vntbody\').innerHTML')));
```

Measured: `rVends()` is **6,229 bytes**; this slice is **6,199** — 30 bytes
SHORT. The assertion over it is an ABSENCE:

```js
assert.ok(!/\.ytd\b/.test(panel), 'rVends still reads the stored ytd field: ...')
```

**A too-short span under an absence assertion is the combination that fails
GREEN.** A `.ytd` read reintroduced in the last 30 bytes of `rVends()` passes
this arm silently. The same expression appears again at `:202`, where the end
bound is the literal `"$('vntbody').innerHTML=html;"` — and if that string
ever changes, `indexOf` returns `-1`, `slice(i, -1)` runs to the end of the
file, and the four `panel.includes(...)` arms below it would pass on anything
in `sairnbiz.html`.

The fix the rest of the tree now uses is `tests/lib/fn_span.js` (landed in
`d8392f80`), which bounds a body at its own balanced close and **refuses** on
an absent, duplicated or unbalanced anchor rather than returning a span:

```js
const { fnBody } = require('./lib/fn_span.js');
...
const panel = fnBody(src, 'function rVends()');
```

Its selftest is `tests/lib/fn_span.test.js` (15 arms, both directions, two
ablations), and `tests/run_fn_span_control.js` is the planted control shape —
it proves, per arm, that the repoint changes the answer, and reports
`NOT PROVEN` rather than counting an arm whose plant did not separate the two
bounds. Worth reusing here: both of these arms are green today and would stay
green either way, so the repoint cannot be shown to bite without a plant.

---

## 3. The sb_ap seq 507/508 overlap, stated

Your status row reads *"batch8: sb_ap seq 507/508 fixed with an 11-arm suite
and both ablations caught."* The overlap with my lane is exactly one row and
it is a RECORD, not code:

* `docs/known-red-suites.json` carries `tests/sairnbiz_vendor_ytd_derivation.js`
  with `owner: cc`, `since: 2026-10-05`, `diagnosed_by: fourth` — written by me
  during the 2026-10-05 red-register reconciliation, naming your claim as the
  reason I did not fix it.
* Section 1 above shows that diagnosis is now stale: the suite does not reach
  the arm my `why` names.

So the row is yours to close and the diagnosis is mine to have corrected.
**When the anchor is repointed, re-run the suite and delete the entry if it
goes green** — the register's own rule is that an entry whose suite has
recovered must be deleted, because while it stands it absorbs the next real
failure of that file.

Nothing in `sairnbiz.html` was read for anything but the two line numbers
quoted above, and nothing in it was written.
