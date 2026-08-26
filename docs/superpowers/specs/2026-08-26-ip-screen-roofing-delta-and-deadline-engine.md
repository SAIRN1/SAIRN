# IP quick screen — SAIRNroofing Phase 4-5 delta, and SAIRNlaw's deadline engine

**2026-08-26.** Public-source patent screen. **This is not a clearance and
cannot become one.** No opinion here is a legal opinion; a real patent
attorney is required before launch, unchanged by this document — the same
standing caveat `2026-08-24-sairnroofing-v1-scope.md` §1.4 already carries.

## 0. Correction to the premise this screen was requested under

The request described SAIRNroofing as an app that has **never** had a
patent/trademark screen. That is not accurate, and acting on it would have
duplicated existing work while missing the actual gap.

`docs/superpowers/specs/2026-08-24-sairnroofing-v1-scope.md` carries a real
screen dated 2026-08-24: a full "Patent position" section (`:43`) analysing
Xactware/Verisk **US 9,501,700** element by element and the EagleView/
Pictometry family, the design-around v1 was built to (`:1.3`), an explicit
hard boundary on what would void that analysis, and a trademark finding
recorded honestly as *"inconclusive, not cleared"* (`:100`).

What genuinely has **no** screen is the **Phase 4-5 delta** — everything built
after that spec was written. That is what this document covers. Scope an IP
screen to the delta, not to the app, whenever a prior screen exists.

## 1. SAIRNroofing — the finding that matters

### 1.1 US 8,983,806 B2 — Accurence, Inc., "Method and system for roof analysis"

Filed **2011-12-23**, granted **2015-03-17**, assignee **Accurence, Inc.**
(claims priority to provisional 61/460,964). Nominal 20-year term from filing
puts expiry around **2031-12-23**, subject to PTA and to maintenance fees
having been paid — **maintenance-fee status was NOT verified** and cannot be
from the sources used here. Treat as potentially in force.

Independent claim 1, in full, is a five-element AND:

1. receiving **digital building facet data** for a first building facet
2. receiving **digital inspection data** for that facet
3. determining an **amount of building material required to repair** damage to
   an area of that facet, **including determining a first amount of waste
   building material**
4. determining a **repair indicator** for that facet, based at least in part on
   the facet data and the inspection data
5. **displaying an electronic image** of the set of building facets

**Why this matters more than the patents already screened.** The 2026-08-24
analysis was aimed entirely at the *aerial-imagery / computer-vision* family —
Xactware's eight-element scan-rotate-scan pipeline and EagleView's measurement
patents. The design-around it produced (single LLM inference → quantities
schedule, no manipulable geometric model) defeats six of Xactware's eight
elements and is sound **for that family**.

It does not address Accurence claim 1 at all, and **claim 1 has no
computer-vision, aerial-imagery, or geometric-modelling limitation whatsoever.**
Aerial CAD data appears only in dependent claim 2. Claim 3 defines "building
facet data" broadly enough to include **facet pitch and facet area** — which is
what a quantities schedule is. So the entire basis of the existing design-around
is orthogonal to this patent.

### 1.2 How close is SAIRNroofing, element by element

| element | SAIRNroofing today | reads on it? |
|---|---|---|
| 1. facet data | `squares`, `ridge_lf`, `hip_lf`, pitch class, `stories` (`sairnroofing.html:1958-1961`) — claim 3 expressly includes facet pitch and area | **likely yes** |
| 2. inspection data | Phase 5 per-claim photos tagged by elevation/slope and damage type; claim 4 lists hail-hit frequency, wind damage, material age | **likely yes** |
| 3. material amount incl. **waste** | `waste_factor_pct` is an explicit field (`:1961`), and the supplement worksheet computes expected items `measured_from: squares` (`:1186`, `:1239`) | **likely yes** |
| 4. **repair indicator** | grep finds **no repair-vs-replace determination anywhere** in the app | **no** |
| 5. **display facet image** | no facet diagram or facet-image rendering found | **no** |

**SAIRNroofing is clear of claim 1 — by two elements, not six.** Claim 1 is an
AND, so absent 4 and 5 there is no literal infringement. But that is a far
thinner margin than the existing spec's headline "distance from six of eight
elements on independent grounds," and the margin is **not** load-bearing on the
design-around everyone believes is protecting this app.

### 1.3 The specific risk, stated plainly

The two elements holding the line are the two most obvious next features.

- *"Should this roof be repaired or replaced?"* is a **repair indicator**. It is
  the single most natural product request for a roofing estimator, and adding it
  supplies element 4 directly.
- *A facet/slope diagram* is an obvious UI improvement to a quantities schedule,
  and supplies element 5.

Build either without counsel and the app moves from two elements clear to one.
Build both and claim 1 may read on it in full — with no aerial imagery, no CV,
and no geometric model anywhere near it, which is exactly the safety everyone
currently believes they have.

**Recommended hard boundary, in `sairn-forward-scan` style, written into
`sairnroofing.html` itself the way the Phase 6 exclusions were:**

> Do not add a repair-vs-replace indicator, and do not render a facet/slope
> diagram, without a fresh legal check against US 8,983,806 (Accurence). These
> are elements 4 and 5 of that patent's claim 1; the app is currently clear of
> claim 1 only because both are absent. The Xactware/EagleView design-around in
> `2026-08-24-sairnroofing-v1-scope.md` §1.3 does **not** cover this patent — it
> addresses a computer-vision family, and this claim has no CV limitation.

### 1.4 Also surfaced, not yet analysed

- **US 2015/0248730 A1 / WO 2015/131121 A1 — "Insurance adjuster claim scoping."**
  Directly adjacent to Phase 5's claim-scoping and supplement worksheet. Grant
  status and claim scope **not** established here.
- **US 9,262,564 B2 — "Method of estimating damage to a roof"** (State Farm).
  Damage assessment without an on-site estimator. Not analysed.
- **US 11,392,977 B2 and US 2017/0345069 A1 — Accurence.** Same assignee as
  §1.1; "Repair estimate quality assurance automation" is on its face close to
  the supplement worksheet's deterministic line-item comparison. Not analysed.

Four unanalysed references, one of them from the same assignee as the live
finding. This screen is a starting point, not a survey.

## 2. SAIRNlaw deadline engine — materially better position

Scope: `resolve_periods` (`api/_lib/deadline-engine.js:1964`), `terminal_day_rule`,
and everything added since the citator's original screen.

### 2.1 The governing prior art is expired

| patent | assignee | filed | ~term end |
|---|---|---|---|
| US 7,668,863 B2 — *Management of court schedules* (court rules + local rules + individual judge rules, jurisdiction expert) | **CompuLaw, LLC** (now Aderant) | 2002-07-22 | **~2022** — expired |
| US 6,859,806 B1 — *Legal docketing using a customizable rules subset* | Ideapath Inc. | 2000-07-21 | **~2020** — expired |
| US 6,549,894 B1 — *Computerized docketing with automatic due date alert* | — | 1999 | expired |

US 7,668,863 is the closest art to what SAIRNlaw's engine does — rules-based
deadline computation across statutes, local rules and individual judges — and
it is **out of term**. The foundational docketing-and-calendaring art in this
field dates to 1999-2002 and has aged out.

### 2.2 Two further reasons the position is strong

**The rules are law.** `terminal_day_rule` (weekend/holiday rollover) and
`resolve_periods` (`later_of` / `earlier_of` two computed limbs) are direct
applications of FRCP 6 and its state analogues. The rule text is a statute; a
faithful implementation of a statute is not somebody's proprietary method.

**Alice.** Post-*Alice v. CLS Bank*, a claim to computing a date from rules on a
generic computer is squarely in abstract-idea territory. That is why this field's
patents are old: the ones that would issue on this subject matter today largely
would not.

### 2.3 Not a finding, but worth recording

`resolvePeriods` **refuses** rather than guesses when a rule declares
`resolve_periods` with fewer than two limbs, or applies it to a backward-counted
limb (`:1969`, `:1983`), and names which direction the error would run
(`:1996`). Honest-refusal behaviour of that kind is a defensive-publication
candidate if the platform ever wants one — it is the opposite of the fabrication
risk Guardian Check 0b exists for. Recorded as an option, not a recommendation.

## 3. Trademark — unchanged, and it is one question, not two

Nothing here changes `2026-08-24`'s finding: a public-web search for a "SAIRN"
mark returns nothing relevant, which is **not** a clearance. It was not TESS,
EUIPO or WIPO, and a real screen needs **Class 42 (SaaS)** and **Class 9
(downloadable software)**.

This is a **platform-level** question — one "SAIRN" mark across all 13 apps —
not a per-app one. Running it once per app would be waste; running it once,
properly, through counsel, covers everything.

## 4. What this screen did not do

- **No maintenance-fee or assignment check on US 8,983,806.** It may have
  lapsed, or been assigned to a more or less litigious owner. Unknown.
- **No claim-chart-level analysis** of the four references in §1.4.
- **No freedom-to-operate opinion.** Not possible from public search, and not
  possible from a session regardless of sources.
- **No file-wrapper or prosecution-history review**, which routinely narrows
  claims relative to their plain text — element 1 or 3 could well have been
  narrowed during prosecution in a way that increases the margin in §1.2. That
  cuts toward *more* room, not less, and is exactly the kind of thing counsel
  checks and a web search cannot.
- **Google Patents rate-limited and then 503'd** partway through. Later results
  came from FreePatentsOnline and search snippets. Coverage is a screen, not a
  survey, and the §1.4 list is evidence of what remains unexamined.

## 5. Recommendation

1. **SAIRNroofing: do not build a repair-vs-replace indicator or a facet
   diagram** until counsel has looked at US 8,983,806. Everything else in
   Phase 4-5 is unaffected by this finding.
2. Add the §1.3 boundary comment to `sairnroofing.html` alongside the Phase 6
   exclusions, so it cannot quietly disappear.
3. **SAIRNlaw: no blocker found.** Continue building the deadline engine.
4. Take the four §1.4 references and the trademark question to counsel together,
   once, as one package.
