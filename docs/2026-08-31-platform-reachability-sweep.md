# Platform reachability sweep — can a customer actually reach what shipped?

Guardian 0b asks whether a number has a function behind it. This asks the
opposite: the function is real — **can anyone reach it?**

The class comes from 2026-08-30/31, when three complete, working, AI-backed
StoneDesk features turned out to be unreachable. Nothing was broken. Each
injected its only trigger into `#sairn-intake-actions`, an element existing
solely as an empty `display:none` placeholder.

**Result: 18 of 19 apps clean. All findings are in `stonedesk.html`.**

Tool: `tools/sairn_reachability_check.py`.

---

## What the three detectors look for

| | |
|---|---|
| **R1** | An id exists both as an empty `display:none` placeholder **and** as something the JS creates. `getElementById` returns the stub, so install-once guards refuse to install. |
| **R2** | JS injects a control into a container that is `display:none` in markup. |
| **R3** | A `window.<name> = function` that nothing calls or wires. The shape that hid `openCompare` / `openDocModal` / `openCamera`. |

## Results

**R1 — 2 hits, both intentional and already documented.**
`sairn-lock-overlay` (held pending CC's Layer 5 security work — freeing it
activates a lock whose unlock validates hardcoded PINs) and `sairn-voice-btn`
(held on purpose, because Feature 7 is superseded by `attachVoiceInput()` and
freeing it produces a duplicate mic button). The checker is right that they
collide; the collisions are the fix.

**R2 — zero hits.** The `#sairn-intake-actions` case that motivated the whole
sweep no longer matches, because that panel's injections were the thing already
found. Nothing else on the platform does it.

**R3 — 32 hits, all in StoneDesk, and 30 are definition-only.** For those 30 the
function name appears **exactly once in the entire 2.2 MB file** — the
definition. That is a count, not an inference.

They fall into three groups:

**Group 1 — the `sa*` security helpers (13).** `saWipeAllData`,
`saSecureClaudeCall`, `saSignRequest`, `saTrackLoginAttempt`,
`saCheckRateLimit`, `saDetectAnomaly`, `saSanitizeResponse`,
`saCheckDataMinimization`, `saShowSecurityStatus`, `saDebounce`, and others.
**Handed to CC** — this is inside the already-claimed "stonedesk security layers
wiring" task, and `saWipeAllData` in particular (a data-wipe entry point with no
caller) belongs in that review rather than this one.

**Group 2 — the export/print family (15).** `sdCRMExport`, `sdSeamExport`,
`sdVeinExport`, `sdStoneyardExport`, `sdRemnantExport`, `sdWasteExport`,
`sdTaxExport`, `sdSafetyExport`, `sdReviewsExport`, `sdReferralExport`,
`sdEquipmentExport`, `sdEmployeesExport`, `sdDamageExport`, `sdBulletinExport`,
`sdSintExport`. Each builds a CSV and each has no caller.
**There is no generic export helper in StoneDesk** — zero `exportTableCSV`
calls, unlike SAIRNvet which routes every panel through one. So these are not
superseded by a shared helper; they are simply unwired.

**Group 3 — assorted entry points (2 + 2 ambiguous).** `openFQ`,
`sairnOpenFQ`, `sairnOpenPricing`, `safeHTML`, `crPostGL`.

## Two documented retirements, correctly not counted as defects

`crSave` carries a comment: *"crSave kept as no-op for backwards compat;
crSendToBridge is the real…"* — and its body toasts the user toward the
replacement. `sdTrainingExport` is named in a comment as the **canonical**
export for `panel-training`, so its status needs a read rather than a verdict;
it is reported, not claimed.

`sairnmechanical`'s `doRegister` / `savePins` / `selectAuthTab` were flagged by
an earlier version and are **not** defects: they are deliberate
`function(){}` no-op shims beside a comment explaining roles now come from the
server on login. The checker now skips empty bodies for exactly this reason — a
retired feature is not an unreachable one.

## Two scanner bugs found and fixed, both worth recording

Both were in comment-stripping, and both **deleted real code**, producing
fabricated findings:

1. `//[^\n]*` truncated every line containing an `https://` URL, removing real
   `onclick` handlers.
2. `/\*.*?\*/` matched across `/*` and `*/` sequences living inside JS strings
   and regexes, removing **1.2 MB of a 2.2 MB file**. `sdAIQExport` was reported
   as an orphan while `onclick="sdAIQExport()"` sat inside the deleted region.

**The fix was to stop stripping comments entirely** and search raw source. The
cost is that a function named only in a comment counts as used, so R3
under-reports. That is the safe direction: a missed orphan is a gap, a
fabricated one trains people to ignore the tool — the same standard applied to
the raw-HTML sweep's failed tag-opener check.

That is also why the tool's headline number moved 41 → 35 → 39 → 34 → 32 across
iterations. Only the last is trustworthy, and the earlier ones are recorded here
so nobody cites them.

## Recommendation, not done

The export family is one decision, not fifteen: **wire them to their panels'
existing Export buttons, or delete them.** Which one depends on whether those
panels are supposed to have CSV export at all — a product question. Deleting
~15 working CSV builders because nobody wired a button is the wrong default;
so is leaving them as permanent dead weight.

## Limits

Static. It cannot see a handler attached at runtime from a computed name, nor a
container un-hidden by JS. Clean output means "no unreachable feature of these
three shapes", not "every feature is reachable" — only a browser settles that,
which is what the `sairn-visual-review` DOM assertion is for.
