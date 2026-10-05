# SAIRNlegacy competitive-gap audit — 2026-10-05 (CC), **PART 1 OF 2: the internal half**

**THIS DOCUMENT IS DELIBERATELY HALF-FINISHED AND SAYS SO IN ITS TITLE.** Every
other app's competitive-gap audit in `docs/cloud-research/` carries two halves:
what we have, derived from the code, and what competitors have, derived from
external research. **The internal half below is complete and every figure in it
was measured at HEAD today.** The external half is **not done**, is not
estimated, and is scoped at the end as a named question list rather than left as
an impression.

A competitive-gap document with a fabricated competitor column would be worse
than no document, because the next reader would price a decision off it.

---

## Why SAIRNlegacy was picked first of the three uncovered apps

`docs/2026-09-29-competitive-gap-doc-inventory.md` found **three apps with no
competitive-gap doc of any kind** — `sairndesign`, `sairnlegacy`, `sairnscape`.
Not thin coverage: nothing, on `main` or any branch, dedicated or shared. The
pick is measured, not a preference:

| | `sairnlegacy` | `sairndesign` | `sairnscape` |
|---|---|---|---|
| File size | **319,748 B** | 269,114 B | 258,355 B |
| Lines | **4,949** | 4,291 | 4,260 |
| Panels (`id="panel-…"`) | **27** | 20 | 0 found by that pattern |
| Register rows | **36** | 18 | 9 |
| …of those rated **Tier A** | **20** | 10 | **1** |

**It is the largest, the most built-out, and it holds twice the Tier A data of
the next one.** And one reason outranks all of those:

**IT IS THE ONLY ONE OF THE THREE WITH A FEDERAL RULE THAT PRESCRIBES THE
PRODUCT'S OWN PAPERWORK.** The FTC Funeral Rule (16 CFR Part 453) does not merely
regulate the business — it mandates specific disclosure documents, mandates that
they be *offered* at specific moments, and mandates itemisation. That turns *"is
a competitor beating us"* from an impression into a **checkable list**, which is
the only kind of competitive finding this platform has ever been able to defend.
`sairnscape` (landscaping, 1 Tier A row) has no comparable axis.

---

## 1. What SAIRNlegacy actually is, measured

**27 panels**, which is a wider surface than the apps that already have audits:

```
aftercare   ai          cases       caterer     cemetery    certs       clergy
cremation   dashboard   dispatch    docs        fleet       florist     invoicing
keepsakes   livery      memorial    merch       monument    obituary    permits
pets        preneed     procession  scheduling  security    tribute
```

**46 `leg_*` collections** are read or written by the app. It is not a funeral-home
app — it is a **death-care operations platform** spanning four businesses that are
usually sold separately: funeral home (cases, GPL, invoicing, certs, permits),
**cemetery** (plots, monuments), **crematory** (cremations, custody log), and
**livery/fleet** (vehicles, processions, dispatch, maintenance). It also carries a
**pet** line (`leg_petcases`) and an events/catering line (`leg_caterers`,
`leg_floristorders`, `leg_liveryvendors`).

**That breadth is the competitive thesis and it is also the risk** — the same
one-platform-vs-four-vendors argument that `sairnmechanical`'s audit makes for
trades, and it has never been tested here against what the incumbents bundle.

---

## 2. The Funeral Rule axis — measured, and the first real finding

Vocabulary counts, run against `sairnlegacy.html` at HEAD. **A zero here is not
proof of absence of the capability — it is proof the app does not use the rule's
own words**, which for a mandated-disclosure product is itself the finding,
because the rule's words are what an inspector and a customer both look for.

| Term | Occurrences |
|---|---|
| `GPL` | **35** |
| `General Price List` | **6** |
| `Statement of Funeral Goods` | **3** |
| `Funeral Rule` | **2** |
| `16 CFR` | **0** |
| `casket price list` / `CPL` | **0** |
| `OBCPL` | **0** |
| `outer burial` / `burial container` | 1 / 1 |
| `declinable` / `non-declinable` | **0** / **0** |
| `basic services fee` | **0** |
| `cash advance` | **0** |
| `telephone price` / `written price` | **0** / **0** |

### F1 — the GPL is a first-class object and the other TWO mandated price lists are not

**VERIFIED BY READING THE CODE, not inferred from the counts.** The General Price
List has its own collection and its own editable rates:
`leg_gplservices` (`sairnlegacy.html:2028` seed, `:2917` reader, `:3301-3302`
rate update and server write). That is a real, correct implementation of the
central Funeral Rule artefact.

**The Casket Price List and the Outer Burial Container Price List are not
modelled as price lists at all.** Caskets and urns exist — in
`leg_merch_catalog` (`:1948`, `:1988`, `:2590`), carrying
`category:'Casket'` and `category:'Urn'` rows — i.e. as **merchandise inventory**,
which is a different object from a disclosure document. 16 CFR 453 treats the
CPL and OBCPL as **separate lists with their own offering requirements**, not as
a filtered view of a catalogue.

**WHY THIS IS A COMPETITIVE FINDING AND NOT ONLY A COMPLIANCE ONE:** every
established vendor in this category sells Funeral-Rule paperwork as a headline
feature, because it is the thing a funeral director is personally liable for. An
app that produces a GPL but cannot produce a CPL is one an incumbent's
salesperson can disqualify in a single question.

**WHAT THIS FINDING DOES NOT CLAIM:** it does not claim the app is non-compliant.
Compliance is a property of what the *home* hands the *customer*, and a home may
produce its CPL outside the software. The claim is narrower and checkable: **the
product does not model it**, so it cannot help.

### F2 — `declinable` appears zero times, and that is the Rule's actual mechanic

The Funeral Rule's substance is not "publish a price list" — it is that a
customer may **decline** individual items and buy only what they want, with only
a small number of non-declinable charges permitted. **Neither word appears
anywhere in the app.** So the itemisation that the rule exists to create has no
representation in the data model, and `leg_invoices` cannot distinguish a
declined item from one never offered.

**NOT DRIVEN:** I did not read the invoicing panel's line-item structure closely
enough to say what it *does* model. This finding is a vocabulary measurement plus
a model-shape inference, and it is marked as such rather than stated as driven.

---

## 3. The preneed axis — the money surface, and the vocabulary is thin

`preneed` appears **35** times and has its own panel and collection
(`leg_preneed`). `trust` appears 9 times, `insurance-funded` once. But:

| Term | Occurrences |
|---|---|
| `irrevocable` | **0** |
| `revocable` | **0** |
| `surety` | **0** |

**Preneed is state-regulated money held for years against a future service, and
the revocable/irrevocable distinction is the central one** — it determines
whether the money can be withdrawn, how it is reported, and, materially for
families, whether the funds count as an asset for Medicaid eligibility.
**Neither word is in the app.**

**STATED AS A GAP IN THE MODEL, NOT AS A DEFECT:** I have not established that
SAIRNlegacy intends to administer preneed trusts rather than merely record that a
preneed contract exists. If the latter, the absence is correct scoping and
should be written down as such. **That is a product decision I am not making
here, and it is the single highest-value question on the list in §6.**

---

## 4. Chain of custody — the strongest thing in the app

`custody` appears **23** times and `leg_custodylog` is a real collection, beside
`leg_cremations` and `leg_deathrecords`. `authorization` appears 12 times.

**This is the axis where SAIRNlegacy is most likely to be AHEAD rather than
behind,** and it is the one worth researching first on the competitor side: a
crematory's identification-and-custody record is the artefact behind the
industry's most serious failure mode, and a platform that keeps it as a
first-class log rather than a PDF attachment is making a real claim.

**Not verified:** whether the custody log is append-only, whether it is
session-gated, and whether entries are server-stamped. `docs/CRITICALITY-TIERS.md`
rates 20 of the 36 `leg_*` rows Tier A; **which** rows and on what basis was not
re-read for this document.

**One thing IS known and is not reassuring, from the code's own record**
(`sairnlegacy.html:1528-1548`): until 2026-09-21, **56 of this file's 58
`sdnData()` call sites sent no session token**, and `api/sd-data.js`'s
`LEG_RESOURCES` branches did not require one — so **36 tables, including
`leg_deathrecords` and `leg_custodylog`, were authorised by the licence key
alone**, a bearer credential shipped to the browser. Fixed at the transport
rather than at 56 call sites, and the comment explains why. Recorded here because
a competitive claim about custody rigour has to survive its own history.

---

## 5. One maintainability observation, not a defect

`sairnlegacy.html`'s transport function is named **`sdnData`** — the same name
used by `sairndental.html`, `sairndesign.html` and `sairnlaw.html`. **Checked:
each is its own local function sending its own app's licence key**
(`sairnlegacy.html:1528` reads `legLicenseKey()`), so this is a copied naming
convention and **not** a cross-app transport collision. Recorded because the name
reads like SAIRNdesign's and the next reader will wonder — which is a cost even
when nothing is broken.

---

## 6. THE EXTERNAL HALF — NOT DONE. The question list, scoped.

**No competitor was researched for this document. No vendor name, price, feature
or roadmap claim appears anywhere above, and none should be inferred.** What
follows is the brief, ordered by how much a wrong answer would cost:

1. **Do the incumbents bundle funeral home + cemetery + crematory + livery, or
   sell them separately?** This is the whole breadth thesis in §1. If they bundle,
   27 panels is parity, not an advantage.
2. **Is preneed trust administration table stakes or a separate product?**
   Decides whether §3's zero-occurrence finding is a gap or correct scoping — and
   it is a product decision, not a research finding alone.
3. **Does every serious competitor produce the CPL and OBCPL?** If yes, F1 is a
   disqualifier rather than a to-do.
4. **Who else models custody as a first-class log?** §4 is our best candidate
   strength and it is unverified as a differentiator.
5. **What does the category charge, and per what unit** — per case, per location,
   per seat? Nothing in this document touches pricing.
6. **Is there a regulatory-update obligation?** The Funeral Rule has been under
   FTC review; a vendor who ships rule changes is selling something a static app
   cannot match.

**The method to use is already on disk and should not be reinvented:** the twelve
audits merged onto `main` today (PR #18) are the template, and
`docs/2026-09-29-competitive-gap-doc-inventory.md` explains the
DEDICATED-vs-SHARED counting rule this document should be scored under when it is
finished.

---

## What this document does NOT claim

* **No competitor research.** §6 is a brief, not a finding.
* **No compliance verdict.** §2 and §3 measure what the PRODUCT models, never
  what a funeral home does with it.
* **Vocabulary counts are evidence about words, not capabilities.** A zero means
  the app does not use the rule's term; where I inferred a model shape from one,
  §2's F2 says so explicitly.
* **The Tier A breakdown was not re-read.** 20 of 36 `leg_*` rows are rated A per
  `docs/CRITICALITY-TIERS.md`; which rows, and whether each was individually
  read, is not established here — and two register rows elsewhere were found
  today to carry a withdrawn "not individually read" sentence, so that file's
  rows are not safe to quote without opening them.
* **Nothing was driven against the live app.** No panel was clicked and no
  endpoint was called for this document.

**BLIND SPOTS: 5.** (1) The external half is entirely absent — this is half an
audit and the title says so. (2) Vocabulary counting cannot see a capability
implemented under different words; F1 was confirmed by reading code, F2 was not.
(3) The 27-panel figure counts panel DIVS, not working features — no panel was
checked for whether it functions. (4) Cemetery, livery and pet lines are named in
§1 and not examined at all; any of the three could be a shell. (5) The pick
between the three uncovered apps used size, panel count and Tier A density as
proxies for commercial importance, and a proxy is not the thing — if SAIRNscape
has a buyer waiting and SAIRNlegacy does not, this ordering is wrong and the
measurement would not show it.
