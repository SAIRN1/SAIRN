# Routed to hank — 2026-10-06 (fourth)

**Three findings in files hank holds under an active claim.** Nothing below was
edited. `python tools/sairn_claim.py check` BLOCKS on *"same app: stonedesk"*
and on `sairnsenior.html`, against hank's claim of 2026-10-06 06:55Z
(`FILES:` includes `sairnsenior.html` and `stonedesk.html`). Declared per
PR §4.3 rather than reworded past, and flagged rather than proceeded on.

---

## 1. `tests/stonedesk_server_backup.js:260` — a 200-byte window over a 96-byte function

Found by the 2026-10-06 span sweep (`d8392f80`), which measured 24
function-body spans against each function's own balanced closing brace. This is
one of five that disagreed and one of the four that were real.

```js
const seam = html.slice(html.indexOf('function sdHydrateStore('),
                        html.indexOf('function sdHydrateStore(') + 200);
assert.ok(seam.indexOf('sdWhileSuppressed') !== -1,
  'the store seam does not suppress -- every hydrated row echoes back to the server');
```

Measured at HEAD: `sdHydrateStore(` is **96 bytes** long. The window is **200**.
So **104 bytes of whatever follows the function** are searched for
`sdWhileSuppressed`, and the arm is a POSITIVE assertion — *the span contains
this* — which is the combination that **fails GREEN**. If the suppression
wrapper were removed from `sdHydrateStore` while any neighbouring code
mentioned `sdWhileSuppressed`, this arm would still pass and
`tests/stonedesk_server_backup.js` would report 23/23.

**The one-line repoint.** `tests/lib/fn_span.js` landed in `d8392f80`:

```js
const { fnBody } = require('./lib/fn_span.js');   // with the other requires
...
const seam = fnBody(html, 'function sdHydrateStore(');
```

`fnBody` bounds a body at its own balanced close, skipping strings, comments
and regex literals, and **refuses** — rather than falling back to a bound it
has no basis for — on an absent signature, a signature matching twice, or
braces that never balance. Its selftest is `tests/lib/fn_span.test.js`
(15 arms, both directions, two ablations). Signature uniqueness in
`stonedesk.html` was checked: `function sdHydrateStore(` occurs exactly once.

**I made this edit, then reverted it when `check` blocked.** The suite is
UNCHANGED at HEAD and still exits 0 (23 passed, 0 failed) — the hole is open,
not broken. `tests/run_fn_span_control.js` carries the proof as an arm whose
name says the hole is still open:

```
  ok - tests/stonedesk_server_backup.js -- the hydrate seam suppresses [HOLE STILL OPEN, ROUTED TO hank]
        old bound said true (wrong), new bound says false, real source still true
```

That arm plants `sdWhileSuppressed` **outside** the function after renaming it
inside, and shows the 200-byte window still finds it while the balanced span
does not. So the repoint is proven to change the answer before anyone applies
it.

---

## 2. `docs/2026-09-02-competitive-gap-status-rederived.md` — the SAIRNsenior section's evidence clauses have gone false in letter, while the verdicts hold

I re-derived that file's SAIRNroofing and SAIRNdental sections at HEAD today
and corrected two cells. **I did not touch the SAIRNsenior or StoneDesk
sections** and have not claimed them as checked. What I measured before
stopping:

| Row | Its evidence clause | Counted at HEAD |
|---|---|---|
| Senior **A1** EVV transmission to a state aggregator | *"0 hits on any submission path"* | `aggregator` **18**, `transmission` **3** |
| Senior **A2** telephony fallback | *"Zero occurrences of either"* (as of 08-26) | `telephony` **2** |
| Senior **A4** claims transmission (837) / clearinghouse | *"0 hits"* | `837` **1**, `clearinghouse` **0** |

**The verdicts are still right and the evidence sentences are not.** Every
non-zero hit was read:

* `sairnsenior.html:3978` — the `837` hit is the string `~:5837` inside a
  comment about the authorisation-gap tool. A line number, not a transaction
  set.
* `sairnsenior.html:3001`–`:3002` — the `telephony` hits are comment text
  recording that telephony is the unbuilt half.
* `sairnsenior.html:1245` — **an on-screen disclosure**: *"This records which
  aggregator you are required to submit to. **It does not submit anything.**
  SAIRNsenior has no transmission path to Sandata, HHAeXchange, Tellus or
  CareBridge yet — visits are recorded here and still have to be submitted
  through your aggregator's own portal."*
* `sairnsenior.html:2897` — a second one: *"This is a report. **It submits
  nothing.** SAIRNsenior has no transmission path to any aggregator yet — this
  shows which completed visits carry the data a submission would need, so the
  real cost of closing the gap is visible per visit."*

**That last pair is a STATE CHANGE, not noise.** This platform's own roofing
document draws the distinction explicitly: *"A gap that is disclosed on screen
is not a gap that is closed, and it is not a gap that is hidden either."*
Senior A1 and A4 have moved from **undisclosed-open** to **disclosed-open**,
and the rows do not say so — a reader counting zero hits would also conclude
the app says nothing about it, which is now wrong in the app's favour.

Suggested cell wording, for you to paste or discard:

> **OPEN — VENDOR-BLOCKED, AND NOW DISCLOSED ON SCREEN (re-counted at HEAD
> 2026-10-06).** `aggregator` is 18 hits and `transmission` 3, none of them a
> submission path: the substantive two are disclosures at
> `sairnsenior.html:1245` (*"It does not submit anything"*) and `:2897`
> (*"This is a report. It submits nothing"*), which name all four aggregators
> and tell the user they must still use the portal. Aggregator onboarding is
> still the gate. **The 0-hit evidence this cell was written on is no longer
> the measurement** — and a cell asserting an absence is the one most worth
> re-counting, because absence is what a later commit removes.

---

## 3. The same file's StoneDesk section was not re-derived either

Rows 1–8 of `## StoneDesk` carry 2026-09-02 verdicts, re-derived in part on
2026-09-14 and 2026-09-17. I did not re-derive them today. Two things I
noticed without checking them, offered only as a place to start:

* **Row 4** (*no slab-scanner integration*, **OPEN**) rests on *"3 `slabsmith`
  hits: one comment, two AI system prompts"* — a count, and counts are the
  clause that rots.
* **Row 6** (*no QuickBooks integration*, **HELD OPEN ON PURPOSE**) is
  Michael's call and should not change on a code read. But the file's own
  closing paragraph already flags that `325e1294` built the roofing EXPORT, and
  as of today the roofing CONNECTOR exists too (`api/accounting.js`, 501 on
  every OAuth action, no Intuit application). If row 6 is ever reopened, the
  first question is export-or-connection, and only one of those has a vendor
  dependency.

Nothing in `sairnsenior.html` or `stonedesk.html` was written. Both were read
only for the line numbers quoted above.
