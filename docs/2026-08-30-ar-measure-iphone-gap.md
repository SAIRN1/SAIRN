# AR Measure on iPhone — settled

**Question:** does StoneDesk's AR square-footage measurement work on iPhone, and
if not, what would it take? It affects a live pricing decision, so this is
written to be definitive rather than balanced.

**Answer: it does not work on iPhone, it never has, and it is not fixable in
SAIRN's code.** It also does **not** fail silently — verified in the
implementation, not inferred.

---

## 1. The platform fact, settled against the machine-readable source

**iOS Safari has never supported WebXR.** Not the AR module — the entry point
itself. `navigator.xr` does not exist.

From MDN's `browser-compat-data` (`api/XRSystem.json`), which is what MDN's
tables render from **and what WebKit's own feature-status page now redirects to,
having been retired**:

    XRSystem             safari: false    safari_ios: "mirror"  → false
    isSessionSupported   safari: false    safari_ios: "mirror"  → false

`caniuse` agrees independently: iOS Safari **3.2 through 26.6, every version, not
supported**. Apple's developer forums state `immersive-ar` is "not in a testable
state" even on visionOS.

### The conflicting source, adjudicated rather than reported

One search result (`multiwaresolutions.com`, a low-authority blog) claims
*"Safari 18 enables inline AR sessions backed by ARKit on iPhone and iPad,
allowing camera passthrough and hit-testing without a native app."*

**That is wrong.** If iOS Safari exposed hit-testing through WebXR, `caniuse`
would show partial support rather than ❌ across every version, and
`browser-compat-data` would not carry `false`. The claim most likely conflates
visionOS Safari — which *does* support `immersive-vr` — with iOS. No conflict
remains; the machine-readable data is authoritative and two independent sources
agree with it.

## 2. The premise correction — it does not fail silently

The concern was that the feature "may silently fail for the majority of real
customers." **It does not.** `stonedesk.html`'s `attachARMeasure`:

    var supported = await checkARSupport();
    if (!supported) return;   // no button at all

`checkARSupport()` short-circuits on `!navigator.xr` before touching
`isSessionSupported`. On iPhone the button is **never created**. Manual typing
and voice dictation fill the same `#viz-est-sqft` field and are untouched.

**Checked across the whole platform, not just StoneDesk.** Five apps ship a real
implementation — `stonedesk`, `sairnbuild`, `sairndesign`, `sairngrounds`,
`sairnscape` — and **all five carry the same `if (!supported) return` guard**.
`sairnlegacy` only mentions WebXR in a comment about another app; it has no
implementation.

**So the real problem is different, and for a pricing decision it is arguably
worse than a crash:** the feature is *invisible* on iPhone. No error, no
degraded mode, no support ticket — and therefore nothing in any log or metric
would ever reveal that a majority of customers never saw it. A crash gets
reported. This does not.

*(The 51%+ iPhone share figure is Michael's; not independently verified here.
The conclusion does not depend on the exact number — any large iPhone share
produces the same answer.)*

## 3. The options, scoped

### AR Quick Look / USDZ — **cannot do this. Rule it out.**

This is the obvious-sounding answer and it is wrong, so it is listed first.

Verified against Apple's own AR Quick Look documentation: it is a **display-only
viewer** for USDZ/Reality models. It supports custom banners, a call-to-action
button and Apple Pay checkout. It provides **no** measurement API, **no**
hit-testing, and **no** mechanism to return coordinate or spatial data to the
JavaScript that launched it.

It can put a countertop *model* in a room. It cannot measure one. Not a path.

### 8th Wall — the platform shut down five months ago

Niantic **wound down the hosted 8th Wall platform, access ending 2026-02-28**,
and released the core as open source under MIT. Commercial licences had been
**$700/project/month** (reduced from $3,000).

What survives is a **free, MIT-licensed, unmaintained** world-tracking/SLAM
binary — Niantic is no longer developing it. So this is not "integrate a
vendor"; it is "adopt an abandoned dependency for a measurement feature whose
accuracy is a pricing input." That is a different and much worse proposition.

*(Same shape as the SAIRNfreedom Phase 2 sensor finding: the integrate option's
viability, not the technology, is what decides it.)*

### Reference-object photo measurement — no AR required, works everywhere

Photograph the surface with a known-size object in frame (a tape measure, a
credit card), scale from pixel ratio. Runs in any browser on any phone, uses the
camera capture path StoneDesk **already has** (SAIRN MULTI-MODAL INPUT sits
directly below the AR module in the same file). Less precise than AR hit-testing
and honest about it.

### Native wrapper — real but large

ARKit is reachable only from a native app. `sairn-app-builder` covers the
wrap/sign/notarise pipeline. This is a product decision, not a feature fix.

### The non-AR fallback already ships

Manual entry and voice dictation into `#viz-est-sqft` are live today on every
device. iPhone users are not blocked from producing an estimate — they are
blocked from producing it *by pointing a camera*.

## 4. Recommendation

**Do not price AR measurement as a headline capability.** It is
Android-and-ARCore-only, and will remain so until Apple ships WebXR — a decision
entirely outside SAIRN's control, with no announced timeline.

If it stays in the product, describe it as an **Android bonus**, not a feature
of the product. If a camera-based measurement path is genuinely needed on
iPhone, the reference-object approach is the only one that is buildable now,
free, and uses infrastructure already in the file.

**What a third-party tester with an iPhone can and cannot tell you:** they
cannot test this feature at all. They will see no AR button and nothing will
appear broken. **That absence is the expected result, not a failed test** — and
without this document they would very reasonably report "the AR button is
missing" as a bug.

## 5. What was not checked

- Whether Android hit-test accuracy is good enough for quoting. Nothing here
  measures the feature's *quality* on the platform where it does run.
- Whether the open-source 8th Wall binary actually works in current iOS Safari;
  ruled out on maintenance grounds before testing.
- Any announced Apple timeline for WebXR. Absence of evidence in the sources
  read, not evidence of absence.

## Sources

- [MDN browser-compat-data — `api/XRSystem.json`](https://raw.githubusercontent.com/mdn/browser-compat-data/main/api/XRSystem.json)
- [caniuse — WebXR Device API](https://caniuse.com/webxr)
- [Apple — AR Quick Look](https://developer.apple.com/augmented-reality/quick-look/)
- [Road to VR — 8th Wall goes open source as hosted services go offline](https://roadtovr.com/niantic-webar-platform-8th-wall-open-source/)
- [Apple Developer Forums — immersive-ar on visionOS](https://developer.apple.com/forums/thread/743655)
