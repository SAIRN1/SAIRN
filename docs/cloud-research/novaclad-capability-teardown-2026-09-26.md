# Novaclad capability teardown vs. StoneDesk's WebXR AR measurement (2026-09-26)

**Research pass, 2026-09-26. No code, no claims, no tier registers touched —
new file only, under `docs/cloud-research/`, on its own branch, same lane as
the SOC2/SAIRNvet/StoneDesk research already in this directory.** This is a
feature-level capability teardown, not a market overview: the question is
what Novaclad's scanning pipeline actually does differently from StoneDesk's
own AR measurement, whether any of the *technique* (not the business) is
genuinely worth adapting, and to say plainly if the honest answer is "no."

---

## 0. Scope, and a correction that has to land before any capability comparison

The StoneDesk external competitive-gap audit
(`docs/cloud-research/stonedesk-external-competitive-gap-audit-2026-09-26.md`,
same branch, three commits back) described Novaclad as having "launched a
free iOS app in September 2026." **A harder, dedicated pass this time found
real reason to doubt that framing, and it belongs here rather than silently
folded in** — this document is new-files-only per its own scope and does not
edit that file, but the correction needs to be visible to anyone reading
both. Section 1 lays out the evidence; the short version: no App Store
listing for Novaclad is findable, the company's own site (as indexed) uses
"coming soon," "early access," and "waitlist" language, and every piece of
coverage saying it "launched" traces to the same September 23 press release.
The more defensible read is an early-access pilot with one signed partner
(the founders' own shop), not a general release. Nothing below assumes
either way beyond what §1 documents.

### 0.1 A network-egress caveat that applies to every section below

As with every research pass run from this environment, outbound `WebFetch`
(full-page retrieval) returned `EGRESS_BLOCKED` for nearly every domain
attempted, including Apple's and W3C's own developer/specification pages —
only raw `github.com` file fetches succeeded in this pass, a first for this
document series (prior passes in this series got zero direct fetches at
all). Every other finding below rests on `WebSearch`'s indexed excerpt of a
page, not an independently opened full read. Confidence flags per claim
reflect this, and are more load-bearing than usual in §2–3 given this
document's technical/citation-heavy content.

---

## 0.2 Internal grounding — exactly what StoneDesk's AR measurement does today

Read directly from the live `stonedesk.html` source (the "SAIRN AR MEASURE"
module), not summarized from memory, because the precision matters for a
teardown like this one:

- **Mechanism: WebXR `hit-test` only.** The module requests an
  `immersive-ar` session with `hit-test` as its only required feature — no
  scene reconstruction, no depth API, no mesh, no LiDAR access of any kind.
  Each frame, `getHitTestResults()` returns where a ray from the camera
  intersects a surface ARCore has already recognized as flat.
- **Capture pattern: exactly 3 taps, 2 edges, one rectangle.** The user taps
  a start corner, a middle corner, and an end point; the two resulting edge
  lengths (Euclidean distance between hit-test poses, converted to feet) are
  multiplied for an area. The module's own header comment states this
  scope explicitly: **"This is NOT room scanning"** — a separate, existing
  manual Room Layout mode (the Drawing Tool) already covers irregular
  shapes, and is untouched by this module. As shipped today, there is no
  capture path for an L/U-shaped edge, a second disconnected section (an
  island), or a seam location via the AR camera specifically.
- **Platform: Android/WebXR-capable browsers only**, by the module's own
  documentation — Safari on iOS does not expose `immersive-ar` WebXR
  sessions to web pages at all, a limitation independently reconfirmed in
  this pass (§2).
- **The differentiator claim, in the code's own words, is integration —
  not measurement technology.** The module's header comment is
  unusually candid about this and worth quoting directly, because it frames
  the entire rest of this teardown: *"The differentiator per the research
  behind this build isn't the AR measurement itself (MeasureSquare, AR
  Ruler, arcsite, and others already do that, no patent blocker either
  way — all built on the same public ARKit/ARCore/WebXR surface) — it's
  that the number lands directly in a real, already-wired
  pricing/inventory/Quote-Builder pipeline instead of staying a standalone
  measurement nobody's business software ever sees."* StoneDesk was not
  built on a claim of measurement-technology superiority, which matters
  directly for how to read a "does Novaclad's tech beat ours" question: the
  honest baseline it should be measured against is integration depth, not
  raw sensing capability — but the question the task asked (is there a
  technique worth adopting) is still worth answering on its own terms,
  below.

---

## 1. Is Novaclad's app actually shipped? A load-bearing correction

Three independent signals point the same direction, none from a single
weak source: a `site:apps.apple.com` search for "Novaclad" returns **zero
results** — no listing exists in Apple's own indexed store as of this pass.
Novaclad's own site, as indexed by search (direct fetch blocked — this was
not independently opened, so treat as one step removed from a primary read),
describes the product (branded **"DIY Shopper"**) as **"FREE... coming soon
to the Apple App Store,"** not live, and carries an `/early-access` page
("Early Access and Exclusivity Awaits") and a `/contact-us` page titled
**"Contact Waitlist, Media and Investors"** — the vocabulary of a
pre-launch company. One indexed snippet describes an "early access pilot"
trading free access for "honest feedback," with paid tiers "eventually"
following. Against this, the original PR Newswire release and every wire
pickup (Yahoo Finance, Webull, Trend Hunter, and several smaller syndication
sites) uniformly say Novaclad "Launches" the app, available at
`novaclad.com/app`, with no caveat — but every one of those is the same
press release, not independent verification, and a company's own launch
press release describing an early-access pilot as a "launch" would not be
unusual marketing practice. **No version history, screenshots, ratings, or
user reviews exist anywhere findable, consistent with a pre-release
product**, not a shipped one with even a handful of early users. This
document treats "there is a generally downloadable Novaclad app today" as
**unconfirmed, and more likely false than the original coverage implied.**

**No patent or published patent application exists under Novaclad's name,
anywhere.** Searches against Google Patents and USPTO, plus the named
founders (Ryan and Audrey Brown) combined with "patent," found nothing —
Novaclad's own materials never use the words "patent" or "patent pending."
This is a confirmed absence, not an inference: there is no IP filing to
teardown.

**No independent trade-press coverage exists beyond the wire syndication.**
Targeted checks against stone-industry trade publications (Stone World,
TISE/Surfaces show coverage, DesignHounds) found nothing. The one non-wire
mention is a **paid "branded content" placement in St. Louis Magazine**
about the founders' shop's retail partnership, which references Novaclad in
passing and does not constitute independent editorial verification of
anything technical.

**The workflow's handling of the exact edge cases this teardown was asked
about — irregular shapes, an island as a separate section, existing
seams — is genuinely, completely undocumented.** Every source, including
Novaclad's own site as indexed, repeats one boilerplate sentence: the
engine "captures a room in three dimensions with the iPhone's LiDAR sensor,
then applies a model trained on how a working shop reads a kitchen to
produce a fabrication-grade takeoff and an itemized price." Nothing
describes whether this is a full-room mesh walkthrough or a simpler guided
capture, and nothing anywhere addresses islands, L/U-shapes, or seams. This
should be read as a real, load-bearing gap in Novaclad's own public
disclosure — not something this research failed to find with enough effort.
Likewise, **no numeric accuracy claim exists anywhere** — the only
accuracy-adjacent language is the unquantified adjective "fabrication-grade"
applied to the takeoff, asserted without a tolerance figure or any
comparison to laser templating.

**The business model structurally forecloses adopting Novaclad's technology
directly, independent of everything above.** Novaclad places exactly one
fabricator per metro market through a "Founder-Partner program" (the
founders' own Rock Creek Granite is the flagship partner), offering
"regional exclusivity" and a "personalized dashboard" for incoming leads. No
API, SDK, white-label offering, or any licensing path for an outside
fabricator to use the scanning engine itself was found anywhere. A separate
venture-studio portfolio page names Novaclad the first product of a broader
"Fabrication Cloud" platform with a self-reported (unverified) market-size
figure — investor framing, not a technology disclosure. **Even setting the
shipped-or-not question aside entirely, there is no disclosed mechanism by
which a stone shop, or a platform like StoneDesk building for stone shops,
could adopt Novaclad's own implementation** — the only stated path to
participation is winning exclusive partner status in a market, which by
construction locks out every other shop in that market.

### Sources (§1)

1. PR Newswire — "Novaclad Launches AI-LiDAR Measurement Engine for the
   Building Trades..." —
   http://www.prnewswire.com/news-releases/novaclad-launches-ai-lidar-measurement-engine-for-the-building-trades-starting-with-a-free-app-that-measures-a-kitchen-in-five-minutes-302888372.html
   — accessed 2026-09-26 — primary source; fetch blocked, snippet only.
   Origin of nearly all other coverage.
2. Yahoo Finance (same release) —
   https://finance.yahoo.com/technology/ai/articles/novaclad-launches-ai-lidar-measurement-235800716.html
   — accessed 2026-09-26 — wire pickup, identical text.
3. Trend Hunter (same release) —
   https://www.trendhunter.com/trends/free-app-measures-kitchens — accessed
   2026-09-26 — wire pickup with light editorializing, no new facts.
4. Webull (same release) — https://www.webull.com/news/15630393755517952 —
   accessed 2026-09-26 — wire pickup, identical text.
5. wireuk.org (same release) —
   https://wireuk.org/novaclad-launches-ai-lidar-measurement-engine-for-the-building-trades-starting-with-a-free-app-that-measures-a-kitchen-in-five-minutes/
   — accessed 2026-09-26 — wire pickup, identical text.
6. Middletown Life (same release) —
   https://lifestyle.middletownlifemagazine.com/story/706675/ — accessed
   2026-09-26 — wire pickup, identical text.
7. ACHIEVE Community Health (same release) —
   https://www.achievecommunities.org/novaclad-launches-ai-lidar-measurement-engine-for-the-building-trades-starting-with-a-free-app-that-measures-a-kitchen-in-five-minutes/
   — accessed 2026-09-26 — wire pickup, identical text.
8. Stockhausen.org (same release) —
   https://stockhausen.org/novaclad-launches-ai-lidar-measurement-engine-for-the-building-trades-starting-with-a-free-app-that-measures-a-kitchen-in-five-minutes/
   — accessed 2026-09-26 — wire pickup, identical text.
9. Novaclad — "About Us" — https://www.novaclad.com/about-us — accessed
   2026-09-26 — company site, snippet only, fetch blocked; not read
   verbatim.
10. Novaclad — "App" — https://www.novaclad.com/app — accessed 2026-09-26 —
    snippet only; source of the "DIY Shopper... coming soon" finding, not
    read verbatim.
11. Novaclad — "Early Access" — https://www.novaclad.com/early-access —
    accessed 2026-09-26 — snippet only; supports pre-launch/pilot reading.
12. Novaclad — "Contact Us" — https://www.novaclad.com/contact-us —
    accessed 2026-09-26 — snippet only; supports pre-launch reading.
13. Novaclad — homepage — https://www.novaclad.com/ — accessed 2026-09-26 —
    snippet only.
14. 4Fold Futures — Novaclad portfolio page —
    https://www.4foldfutures.com/investments/nova-clad — accessed
    2026-09-26 — investor-facing page, snippet only; source of the
    "Fabrication Cloud" name and an unverified TAM figure, single-source.
15. St. Louis Magazine — "See how this company is changing the stone
    industry..." — https://www.stlmag.com/branded-content/rock-creek-modern-customer-new-technology/
    — accessed 2026-09-26 — explicitly labeled branded/sponsored content,
    not independent editorial coverage; tangential mention only.
16. Apple App Store search (`site:apps.apple.com Novaclad`, via WebSearch)
    — accessed 2026-09-26 — no listing found; strong but not absolute
    evidence given possible index lag for a brand-new app.
17. Google Patents / USPTO general search for "Novaclad" — accessed
    2026-09-26 — no relevant patent found.
18. Justia Patents — "Ryan H. Brown" —
    https://patents.justia.com/inventor/ryan-h-brown — accessed 2026-09-26
    — appears to be an unrelated individual, no link to Novaclad
    established.

---

## 2. The technical mechanism, precisely

**LiDAR scene reconstruction (ARKit) produces continuous 3D data — a mesh
or a depth image, not single points.** ARKit exposes two distinct, public
capabilities on LiDAR-equipped hardware: `sceneReconstruction`, which
returns `ARMeshAnchor` objects (vertex, face, and normal data, plus a
per-face surface classification like wall/floor/table), and
`sceneDepth`/`smoothedSceneDepth`, a dense per-pixel depth map with a
per-pixel confidence level. Both have been ordinary, publicly documented
parts of the iOS SDK since ARKit 3.5 (2020) and ARKit 4 (extended to iPhone
12 Pro) — available to any developer with a normal Apple Developer Program
membership on qualifying hardware, no special gate or NDA. **On the
evidence found, "Novaclad's technique," whatever it actually is, would be
architecturally a conventional iOS app calling a documented, public Apple
API — not proprietary technology unique to one vendor.** Any competitor
building a native iOS app for iPhone 12 Pro-or-newer could call the
identical APIs; this is the same conclusion StoneDesk's own code comment
already reaches for AR measurement generally (§0.2).

**WebXR `hit-test` has no built-in point limit — the 3-tap cap is
StoneDesk's own product-scope choice, not a technical ceiling.** The spec
itself is a deliberately thin primitive: one ray-cast per call against
whatever surface the platform already understands. Real third-party WebXR
tools already place an arbitrary number of hit-test-sourced points and
connect them into closed polygons with client-side area calculation — so a
polygon-capture upgrade to the *existing* hit-test approach is technically
possible today, without adopting any new WebXR module, and would not by
itself require LiDAR or a native app.

**Two more capable WebXR modules exist, and one is a real bridge toward
LiDAR-like data on the web — with real limits.** **Plane Detection**
already ships in Chrome on Android and returns `XRPlane.polygon`, a
convex-polygon surface boundary generated automatically with no tapping —
but it runs on ARCore's ordinary vision-based plane fitting, not LiDAR, and
being convex-only, it structurally cannot represent a concave notch (a sink
cutout, for instance). **Depth Sensing** is the real bridge: a standardized,
already-shipped (Chrome 90, April 2021, Android/ARCore-backed) API
returning a genuine per-pixel depth buffer, and its own explainer — written
by the engineer who built it — treats Apple's LiDAR-backed depth API as one
of the reference hardware shapes the standard was designed to fit. **In
practice, this bridge does not reach LiDAR-grade data today**: ARCore's
Depth API, which backs Chrome's implementation, computes depth mostly via
motion stereo across successive camera frames rather than a dedicated
time-of-flight sensor, and Safari still does not implement `immersive-ar`
on iOS/iPadOS at all as of September 2026 — so no browser today can reach
real LiDAR-grade depth over WebXR, on either platform, regardless of which
WebXR module is used.

### Sources (§2)

1. Apple Developer Documentation —
   `ARWorldTrackingConfiguration.sceneReconstruction` —
   https://developer.apple.com/documentation/arkit/arworldtrackingconfiguration/scenereconstruction
   — accessed 2026-09-26 — official docs, high confidence; content via
   search-snippet synthesis (fetch returned page title only).
2. Apple Developer Documentation — `ARMeshAnchor` / `ARMeshGeometry` /
   `ARMeshClassification` —
   https://developer.apple.com/documentation/arkit/armeshanchor ,
   https://developer.apple.com/documentation/arkit/armeshgeometry ,
   https://developer.apple.com/documentation/arkit/armeshclassification —
   accessed 2026-09-26 — official docs, high confidence, snippet only.
3. Apple Developer Documentation — `ARFrame.sceneDepth` /
   `ARDepthData.confidenceMap` —
   https://developer.apple.com/documentation/arkit/arframe/scenedepth ,
   https://developer.apple.com/documentation/arkit/ardepthdata/confidencemap
   — accessed 2026-09-26 — official docs, high confidence, snippet only.
4. W3C — WebXR Hit Test Module — https://www.w3.org/TR/webxr-hit-test-1/ —
   accessed 2026-09-26 — official spec, high confidence, snippet only.
5. immersive-web/hit-test — README —
   https://github.com/immersive-web/hit-test/blob/master/README.md —
   accessed 2026-09-26 — official spec repo, directly fetched, high
   confidence.
6. immersive-web/webxr-samples — `hit-test.html` —
   https://github.com/immersive-web/webxr-samples/blob/main/hit-test.html —
   accessed 2026-09-26 — official sample code, directly fetched.
7. Mithun1075/MeasureXR — https://github.com/Mithun1075/MeasureXR —
   accessed 2026-09-26 — third-party project, medium confidence, used only
   as an existence proof that multi-point hit-test polygon capture is
   built today.
8. immersive-web/real-world-geometry — WebXR Plane Detection Module —
   https://immersive-web.github.io/real-world-geometry/plane-detection.html
   — accessed 2026-09-26 — official spec, snippet only.
9. Google ARCore Developers — `ArPlane`/`getPolygon` reference —
   https://developers.google.com/ar/reference/c/group/ar-plane — accessed
   2026-09-26 — official docs, snippet only.
10. W3C — WebXR Depth Sensing Module —
    https://www.w3.org/TR/webxr-depth-sensing-1/ — accessed 2026-09-26 —
    official spec, snippet only.
11. bialpio/webxr-depth-api — explainer.md —
    https://github.com/bialpio/webxr-depth-api/blob/master/explainer.md —
    accessed 2026-09-26 — primary source (written by the feature's
    engineer), directly fetched, high confidence.
12. Chromium blink-dev — "Intent to Ship: WebXR Depth API" —
    https://groups.google.com/a/chromium.org/g/blink-dev/c/v4fneq7tgDA/m/utkwOcjuAwAJ
    — accessed 2026-09-26 — official Chromium mailing list, snippet only.
13. Neowin — "Chrome 90 is here with an AV1 encoder and new augmented
    reality APIs" — https://www.neowin.net/news/chrome-90-is-here-with-an-av1-encoder-and-new-augmented-reality-apis/
    — accessed 2026-09-26 — tech press, corroborates shipping date.
14. Google for Developers — ARCore Depth API developer guide —
    https://developers.google.com/ar/develop/depth — accessed 2026-09-26 —
    official docs, snippet only; confirms motion-stereo, not ToF.
15. immersive-web/raw-camera-access —
    https://github.com/immersive-web/raw-camera-access — accessed
    2026-09-26 — official spec repo; a separate RGB-access module, not
    depth — noted so the two are not conflated.
16. Variant Launch — "The state of WebXR on iOS, and beyond" —
    https://launch.variant3d.com/blog/23-06-state-webxr-on-ios-beyond —
    accessed 2026-09-26 — industry technical blog, moderate confidence.
17. XRDoctors — "WebXR on iOS — What Works in Safari in 2026" —
    https://xrdoctors.pro/blog/webxr-on-ios-what-actually-works — accessed
    2026-09-26 — industry blog, corroborating.
18. Apple Developer Forums — "[WebXR] Support for AR module in VisionOS
    2.x" — https://developer.apple.com/forums/thread/756850 — accessed
    2026-09-26 — Apple's own forum discussion, moderate confidence.

---

## 3. Real accuracy numbers, honestly compared

**LiDAR (Approach A) has real, peer-reviewed accuracy data, and it is
distance- and motion-dependent, not a flat spec.** The most-cited study
(Jeftha et al., *Scientific Reports*, 2021) found iPhone 12 Pro LiDAR
achieving roughly ±1cm absolute accuracy on small objects (>10cm),
degrading to ≈6–8cm at room scale. A 2023 iPad Pro indoor-mapping study
found under 1mm deviation from a best-fit plane in careful, *static*
capture, worsening to about 1cm in *dynamic* (walking) capture, and
specifically recommended a 1–1.5m scan distance — which happens to match
the working distance for scanning a countertop closely. A 2026 cross-model
study reported roughly 2.06cm RMSE point-cloud distance for the iPhone 15.
In a tightly controlled clinical comparison (iPhone 14 Pro scanning apps
against a stationary professional photogrammetry rig), mean surface
deviation was 1.46–1.66mm — a genuinely good result for a phone, though
still roughly an order of magnitude behind dedicated precision scanners.
**Honest summary: sub-centimeter accuracy at close range under good, still
conditions, degrading with distance and motion — no source claims
survey-grade precision, and no source tested this specifically against
stone.**

**No comparable accuracy figure exists anywhere for WebXR hit-test or
ARCore plane detection specifically** — this pass, like the ones before it,
found no rigorous published number for Approach B. What is documented is a
more serious failure mode than reduced accuracy: vision-only tracking and
plane detection are known to lose tracking or fail to find a plane at all
on textureless, glossy, or repetitively-patterned surfaces — a real,
specific risk for a polished stone countertop, and a failure that returns
**no result** rather than a slightly-off one. **LiDAR is not immune to the
same material, either** — general active-optical-scanning literature (not
iPhone-specific, and flagged as a physics-based inference rather than a
documented iPhone-LiDAR-on-stone finding, since no source tested this
combination directly) notes that dark, glossy, specular surfaces cause weak
or bounced-away infrared returns on *any* time-of-flight sensor, producing
dropouts. A very dark, high-gloss slab is plausibly a nontrivial case for
iPhone LiDAR too, just a different (and likely less severe) failure mode
than vision-only tracking's complete loss of plane detection.

**On point-tap versus continuous capture — the part of this comparison
most directly relevant to irregular shapes, islands, and seams**: no source
addressed this exact question for countertops specifically, but the
underlying mechanics support a clear, defensible conclusion. A mesh or
dense depth image contains enough information that edges, corners, and
disconnected regions can in principle be extracted algorithmically — a
real, established (if nontrivial) problem in the point-cloud/computational
-geometry literature. Manual hit-test tapping and even automatic Plane
Detection cannot deliver that without an app building its own segmentation
logic on top: Plane Detection's convex-only polygons structurally cannot
represent a concave notch like a sink cutout, and nothing in ARCore
guarantees that two coplanar-but-physically-separate surfaces (a main
counter run and a kitchen island) get fit as two distinct planes rather
than merged into one. **Irregular-edge and multi-section auto-detection is
possible in principle from continuous 3D data (LiDAR mesh/depth), and not
straightforwardly possible from hit-test or Plane Detection alone without
substantial additional app-side work.** Whether Novaclad's own app actually
does this segmentation work is, per §1, undocumented — so this is a
statement about what the technology *could* support, not evidence Novaclad
*has* built it.

### Sources (§3)

1. Jeftha et al. — "Evaluation of the Apple iPhone 12 Pro LiDAR for an
   Application in Geosciences," *Scientific Reports* (2021) —
   https://www.nature.com/articles/s41598-021-01763-9 (mirror:
   https://pmc.ncbi.nlm.nih.gov/articles/PMC8593014/) — accessed
   2026-09-26 — peer-reviewed, high confidence, snippet only.
2. "Evaluating the accuracy and quality of an iPad Pro's built-in lidar for
   3D indoor mapping," ScienceDirect (2023) —
   https://www.sciencedirect.com/science/article/pii/S2666165923000510 —
   accessed 2026-09-26 — peer-reviewed, high confidence, snippet only.
3. "A comparison of lidar accuracy across iPhone models, with implications
   for reproducibility and cross-study comparison," Taylor & Francis
   (2026) — https://www.tandfonline.com/doi/full/10.1080/2150704X.2026.2720055
   — accessed 2026-09-26 — peer-reviewed, high confidence, snippet only.
4. "Comparative Accuracy of Stationary and Smartphone-Based Photogrammetry
   in Oral and Maxillofacial Surgery: A Clinical Study" —
   https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11594577/ — accessed
   2026-09-26 — peer-reviewed, high confidence, snippet only.
5. "An Empirical Evaluation of Four Off-the-Shelf Proprietary Visual
   -Inertial Odometry Systems" —
   https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9785098/ (also
   arXiv:2207.06780) — accessed 2026-09-26 — peer-reviewed, high
   confidence, snippet only; found ARKit tracking marginally more
   stable/accurate than ARCore under fast motion or poor light.
6. "Plane Detection with ARCore and Unity," DEV Community —
   https://dev.to/whatminjacodes/plane-detection-with-arcore-and-unity-3245
   — accessed 2026-09-26 — developer tutorial, moderate confidence.
7. "Challenges of Indoor SLAM: A multi-modal multi-floor dataset for SLAM
   evaluation" — https://arxiv.org/pdf/2306.08522 — accessed 2026-09-26 —
   academic, moderate-high confidence; general VIO/SLAM literature, not
   ARCore-specific.
8. SCANOLOGY — "How to Scan Dark or Reflective Parts" —
   https://www.3d-scantech.com/how-to-scan-dark-or-reflective-parts/ —
   accessed 2026-09-26 — vendor blog, low-medium confidence; general
   active-scanning physics, not iPhone-specific.
9. INSVISION — "When Black Surfaces Break the Scanner" —
   https://www.insvision3d.com/en/news/industry-articles/when-black-surfaces-break-the-scanner-3d-scanning-reflective-and-dark-parts-without-spray/
   — accessed 2026-09-26 — vendor blog, same caveat as source 8.
10. "EdgeFormer: Local Patch-based Edge Detection Transformer on Point
    Clouds" (arXiv:2604.21387) and "Surface and Edge Detection for
    Primitive Fitting of Point Clouds" (ResearchGate) — accessed
    2026-09-26 — academic, moderate confidence; establishes general
    feasibility/difficulty of algorithmic edge extraction from 3D data, not
    countertop-specific.

---

## 4. Synthesis — is any of this genuinely adoptable?

**No technique should be borrowed from Novaclad specifically — there is
nothing publicly documented to borrow.** Its own workflow, edge-case
handling, and accuracy are all undocumented (§1); it may not even be a
shipped, generally-available app as of this research (§1); it holds no
patent and offers no license, API, or SDK (§1); and the sensing approach it
reportedly uses is, on the evidence in §2, an ordinary application of a
public Apple API that has been available to every iOS developer since 2020 —
the same conclusion StoneDesk's own code already reaches about AR
measurement generally. **A different platform and a different business
model do not, on their own, mean there is a technique worth adopting here,
and in Novaclad's specific case the honest finding is that there plausibly
isn't one to adopt even setting the platform difference aside** — this is
the plain answer the task asked for if the research came back this way, and
it did.

**What is genuinely worth weighing is not "Novaclad's technique" but the
underlying technology category it represents, and that is a real,
architecturally significant tradeoff rather than a free win:**

- **A native iOS app using ARKit's public LiDAR APIs** would, per §2–3,
  provide continuous 3D geometry that can in principle support automatic
  irregular-shape and multi-section detection (islands, L/U-shapes) in a
  way StoneDesk's current hit-test approach structurally cannot, and would
  likely be materially more robust against the surface-tracking failures a
  glossy stone countertop can cause for vision-only plane detection. The
  cost is real and non-trivial: it means shipping and maintaining a native
  app, a real departure from StoneDesk's current no-install, browser-based
  design; it works only on iPhone 12 Pro-or-newer *Pro* models and
  compatible iPads, a materially narrower device set than "any WebXR
  -capable phone" (which currently means Android); and even LiDAR is not
  immune to the same reflective-surface risk that threatens the current
  approach, just less severely. This is a `sairn-software-architect` /
  `sairn-decision-gate` question about whether that cost is worth paying —
  not a conclusion this research draws for the team.
- **A smaller, browser-compatible step exists and does not require going
  native or acquiring new hardware dependencies**: WebXR Plane Detection
  already ships in Chrome on Android today and could replace or augment the
  current exactly-3-tap flow with automatic surface-boundary capture — a
  real, scoped, achievable improvement to the *existing* Android/WebXR
  approach. It remains bounded by real limits: convex-only polygons (no
  sink-cutout notches), no guarantee of correctly separating a counter run
  from an island, and — like every option in this document except a native
  iOS build — no path to iOS at all, since Safari does not implement
  `immersive-ar` in any form.
- **WebXR Depth Sensing is the closest thing to a "LiDAR over the web"
  bridge, and it is real, but it does not currently deliver LiDAR-grade
  results even where it runs.** It ships in Chrome on Android today, but
  the depth data it exposes there is computed from motion stereo across
  camera frames, not a dedicated time-of-flight sensor — meaningfully less
  capable than what ARKit gets from actual LiDAR hardware — and it is not
  implemented on iOS at all. Adopting it would be a genuine capability step
  up from plain hit-test on Android specifically, but should not be
  expected to close the accuracy gap with a native iPhone LiDAR
  implementation, and does nothing for the iOS-availability gap that is
  arguably the more consequential limitation of StoneDesk's current
  approach.

**The honest bottom line**: there is no shortcut here. Closing the real gap
between StoneDesk's current 3-tap rectangle measurement and genuine
irregular-shape/multi-section AR capture, on both platforms, would require
either a native iOS app scoped to LiDAR-equipped Pro hardware (real
capability gain, real architectural cost, real device-coverage narrowing)
or continued investment in the WebXR standards track (Plane Detection now,
Depth Sensing as browsers mature), which stays browser-based and
Android-only and tops out below LiDAR-grade precision even at its best.
Neither path is "adopt what Novaclad did" — Novaclad, on the evidence
gathered here, has not published anything that describes a solved version
of this problem to adopt from.

---

## 5. What this document does not establish or decide

- **No claim in this document should be quoted externally** — to a
  customer, prospect, or in sales/positioning material — without a
  follow-up read from a network that can reach the underlying primary
  sources, including Apple's and W3C's own documentation pages, which this
  pass could not open directly (§0.1).
- **This document does not decide whether StoneDesk should build a native
  iOS AR feature, adopt WebXR Plane Detection or Depth Sensing, or do
  nothing.** That is a `sairn-software-architect` / `sairn-decision-gate`
  question turning on real product-strategy tradeoffs (device coverage,
  maintenance cost of a native app, how much the current 3-tap scope
  actually limits real customers today) this research has no visibility
  into.
- **It does not resolve whether Novaclad's app is actually shipped and
  live** — §1 lays out real evidence pointing toward "probably not
  generally available," but this was not independently confirmed by
  opening Novaclad's own site directly (fetch blocked), and it should be
  re-checked before this document's framing is treated as final. If it
  becomes clearly shipped later, its own edge-case handling and accuracy
  would still need to be re-researched from scratch, since neither is
  documented today.
- **It does not test or measure anything directly** — every accuracy
  figure in §3 comes from third-party studies of ARKit LiDAR generally
  (mostly not countertop- or stone-specific), not from a live comparison
  against StoneDesk's own AR module or against any Novaclad output.

## 6. Decay

Every source above is a search-index snapshot from 2026-09-26. Two things
in this document are unusually likely to change soon and should be
re-checked before being treated as settled: whether Novaclad's app actually
ships generally (§1 — the whole premise of "is there a live competitor
product" could resolve either way within weeks, given the company's own
"coming soon" language), and the state of WebXR Depth Sensing's real-world
maturity and any iOS WebXR movement (§2 — both are active standards-track
areas, not static facts). The peer-reviewed LiDAR accuracy figures in §3
are more stable, but were not tested against stone specifically by any
source found, and that gap is worth closing with a direct measurement
rather than more literature search if this ever becomes a real build
decision.
