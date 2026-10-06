# SAIRNlegacy competitive-gap audit — 2026-10-05 (CC). **PART 1: the internal half. PART 2, the vendor-claim axis, is at the bottom of this file.**

**PART 1 WAS DELIBERATELY HALF-FINISHED AND SAID SO. PART 2 CLOSES IT, AND IT KILLED ONE OF PART 1's OWN CLAIMS — see the correction at the head of Part 2.** Every
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
`leg_merch_catalog` (~~`:1948`, `:1988`, `:2590`~~ → **re-derived at HEAD
2026-10-06: `:2017` the reader, `:2057` the seed, `:2659` the write**), carrying
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

## 6. ~~THE EXTERNAL HALF — NOT DONE.~~ **DONE 2026-10-05, SAME DAY — see PART 2 below.** The question list it was scoped from, kept

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

---
---

# PART 2 — THE VENDOR-CLAIM AXIS, 2026-10-05 (CC)

**Sourced to vendor and regulator material, with every URL listed at the end.
Where a claim is a VENDOR'S OWN MARKETING it is labelled as such and not as a
verified capability — a feature page is evidence of what is SOLD, which is the
right evidence for a competitive gap and the wrong evidence for whether it
works.**

---

## 0. THE CORRECTION THAT MATTERS: PART 1'S BREADTH THESIS IS WRONG

Part 1 §1 said SAIRNlegacy spans "four businesses that are **usually sold
separately**" and called that breadth "the competitive thesis". **That is false,
and it was the single most load-bearing claim in Part 1.**

Cemetery + crematory + funeral home on **one** platform is a named, established
product category with multiple vendors selling exactly it:

* **PlotBox** — markets itself verbatim as *"Cemetery, Crematory, and Funeral
  Home Software"*, one central platform, and includes **trust fund management**
  in that same sentence.
* **byondpro (OpusXenta)** — *"a comprehensive cemetery, crematory, and funeral
  home management solution … purpose-built for the death care industry."*
* **Cemetery Workstation** — *"an all-in-one platform to handle all aspects of
  cemetery and crematory operations."*
* **Halcyon (Batesville)** — Cemetery Management, Cremation Management,
  **preneed case management**, multi-location, and an AI Copilot.

**SO THE BREADTH IS PARITY, NOT ADVANTAGE, and one of SAIRNlegacy's four
"bundled" businesses is arguably BEHIND rather than ahead:** PlotBox and
byondpro lead with **mapping and plot/record digitisation**, and SAIRNlegacy's
cemetery surface is `leg_plots` and `leg_monuments` with no mapping anywhere in
Part 1's read.

**WHAT IS LEFT OF THE THESIS, narrowed to what the evidence supports:** the
*livery/fleet* line (`leg_vehicles`, `leg_processions`, `leg_dispatches`,
`leg_maintenance`) and the *events* line (`leg_caterers`, `leg_florists`,
`leg_liveryvendors`) did **not** appear in any competitor's advertised feature
list that this pass read. That is a narrower and possibly real differentiator,
and it is **unverified in the negative** — absence from four vendors' marketing
pages is not absence from their products.

**This is why Part 1 refused to write a competitor column it had not
researched.** Had it guessed, it would have guessed *in favour of the platform*,
and the breadth claim would have gone into a deck.

---

## 1. F1 IS CONFIRMED AS DISQUALIFYING, and the Rule's own words are sharper than Part 1 had them

Part 1 inferred that "every established vendor sells Funeral-Rule paperwork as a
headline feature". **Sourced, that inference holds, and the mechanism is more
specific than the claim:**

> *"The Funeral Rule requires a written GPL on request, itemized casket and
> outer-burial-container price lists, and a written statement of goods and
> services for every arrangement. Software that generates these on demand with
> current prices, current package math, and the required disclosures keeps you
> out of FTC enforcement actions."*

And from the FTC's own compliance guidance, which **corrects a nuance Part 1 got
slightly wrong**:

* The **GPL** is *"the keystone of the Funeral Rule"* and must carry identifying
  information, **itemized** prices, and specific disclosures.
* The **CPL** must be shown *"when someone asks or when you talk about caskets,
  alternative containers, or their prices, **and before you show the items or
  pictures of the items**."*
* The **OBCPL** carries the same trigger for grave liners and vaults.

**THE TRIGGER IS THE PART THAT MAKES THIS A SOFTWARE PROBLEM AND NOT A PRINTING
PROBLEM.** The CPL is not a document you file once — it must be *presented before
the merchandise is shown*. SAIRNlegacy shows caskets and urns out of
`leg_merch_catalog` with no price-list object attached to that moment, so the app
**cannot implement the trigger even if a home has a CPL on paper**. Part 1 said
"the product does not model it, so it cannot help." The sourced version is
worse: **the product's merchandise panel is the exact screen the Rule attaches an
obligation to.**

**F1's severity is therefore raised from "a salesperson can disqualify it in one
question" to "the app has a screen where a regulated disclosure is required and
does not know it."** The tier does not move — nothing here changes the stored
record's criticality — but the competitive and regulatory reading does.

---

## 2. F3 ANSWERED: preneed is TABLE STAKES as case management, SPECIALIST as trust administration

Part 1 called this "the single highest-value question" and declined to answer it.
**Answered, and it splits in two — which is why it looked ambiguous:**

| Layer | Market position | Evidence |
|---|---|---|
| Preneed **case** management | **TABLE STAKES.** It is a *filterable category* on GetApp and Capterra — i.e. buyers shop on it — and Halcyon lists "preneed case management" as a standard feature | vendor listings + Halcyon's own page |
| Preneed **trust administration / recordkeeping** | **A SPECIALIST PRODUCT.** FSI Trust Solutions exists to do exactly this, as a service with its own tooling; PlotBox includes "trust fund management" on-platform | FSI Trust Solutions; PlotBox |

**SO THE PRODUCT DECISION PART 1 REFUSED TO MAKE NOW HAS A SHAPE:**
SAIRNlegacy has `leg_preneed` with 35 mentions and a panel, so it is already in
the **table-stakes** layer. Its zero occurrences of `irrevocable`, `revocable`
and `surety` mean it is **not** in the specialist layer — and that is a defensible
place to stand, because a specialist layer with a dedicated competitor and
state-by-state trust law is not a thing to half-build.

**WHAT IS NOT DEFENSIBLE, and this is the actual finding:** revocable versus
irrevocable is not a *trust-administration* feature. **It is a field on the
contract** — it decides whether the family can get their money back and whether
the funds count against Medicaid eligibility. A platform can be out of the trust
business entirely and still have to record which kind of contract it is.
**Recording it is table stakes; administering it is not, and Part 1 conflated
them.**

---

## 3. PRICING — the axis Part 1 did not touch at all

| Vendor | Published price | Unit |
|---|---|---|
| **Gather** | **$49/month**, *"no per-user fees and no hidden costs"* | per firm |
| **Passare** | from **$100/month** flat, but pricing is **not published** — custom quote by firm size and locations | per firm |
| **CRaKN** | not published, custom by firm size and features; free trial | — |
| Category range | roughly **$50–$200/month**, some with a one-time purchase option | per firm |

**THE UNIT IS THE FINDING, not the number.** The category prices **per firm, not
per seat and not per case** — Gather advertises the absence of per-user fees as a
selling point, and Osiris is positioned on *"affordable, unlimited-user"* for
independents.

**That is a direct constraint on SAIRNlegacy's licence model.** This platform's
apps are licence-key-per-tenant, which is per-firm and therefore *aligned* — but
it also means **the ceiling is low and known**: a death-care platform competing
on breadth is competing for a $50–$200/month seat, and 27 panels do not change
that. A feature decision that assumes headroom above $200 is assuming something
the published prices do not support.

**NOT CLAIMED:** nothing here is a quote for a multi-location group or a cemetery
with mapping, where PlotBox and Halcyon sit and where pricing is uniformly
unpublished. The $50–$200 band is the independent-firm band.

---

## 4. CHAIN OF CUSTODY — still the best candidate, and still unverified as a differentiator

Part 1 named this as where SAIRNlegacy is most likely AHEAD and said research
should start there. **It did, and it came back inconclusive, which is a result
and is recorded as one.** None of the vendor material this pass read advertises a
first-class identification-and-custody log as a named feature; Halcyon lists
"Cremation Management" and "Document Management" without decomposing either.

**SO THE HONEST STATUS IS UNKNOWN, NOT FAVOURABLE.** Absence from a feature list
is not absence from a product, and "Cremation Management" is exactly the kind of
label that could contain a custody log. **Settling this needs a demo or a
customer, not another search** — and it is the one place where a search returning
nothing is genuinely uninformative rather than mildly reassuring.

---

## 5. What Part 2 changes about Part 1, in one table

| Part 1 said | Part 2 finds |
|---|---|
| Breadth across four businesses is the competitive thesis | **WRONG.** Cemetery+crematory+funeral is a named category with at least four vendors. Breadth is parity; cemetery MAPPING may put us behind |
| F1: an incumbent could disqualify us in one question | **CONFIRMED AND WORSE.** The CPL has a *presentation trigger* attached to the merchandise screen the app already has |
| F3: preneed trust administration — is it table stakes? | **ANSWERED, and the question was mis-framed.** Case management is table stakes; trust administration is specialist; **revocable/irrevocable is a contract field, not a trust feature** |
| Pricing: not touched | **$49–$200/month, PER FIRM.** The unit constrains the roadmap more than the number |
| Custody may be where we are ahead | **STILL UNKNOWN.** No vendor advertises it; that is not evidence either way |

---

## 6. Sources

* [FTC — Complying With the Funeral Rule (2020)](https://www.ftc.gov/system/files/documents/plain-language/565a-complying-with-funeral-rule_2020_march_508.pdf)
* [FTC — Funeral Rule price list essentials](https://www.ftc.gov/system/files/documents/plain-language/funeral_rule_price_list_essentials.pdf)
* [FTC — Funeral Industry Practices Rule (legal library)](https://www.ftc.gov/legal-library/browse/rules/funeral-industry-practices-rule)
* [PlotBox — Cemetery, Crematory, and Funeral Home Software](https://plotbox.com/)
* [Halcyon — Funeral Home Management Software](https://www.halcyondcms.com/funeral-software/)
* [Capterra — Funeral Home Software 2026](https://www.capterra.com/funeral-home-software/)
* [Capterra — Passare pricing](https://www.capterra.com/p/164764/Passare/)
* [GetApp — funeral home software with pre-need management](https://www.getapp.com/retail-consumer-services-software/funeral-home/f/pre-need-management/)
* [FSI Trust Solutions](https://fsitrust.com/)
* [Parting Pro — Best Funeral Home Software (2026)](https://partingpro.com/blog/what-is-the-best-software-for-funeral-homes)
* [funeral.com — Funeral Home Price Lists Explained: GPL, Cash Advances](https://funeral.com/blogs/the-journal/funeral-home-price-lists-explained-gpl-cash-advances-and-how-to-compare-quotes-ftc-funeral-rule)

**BLIND SPOTS: 6.** (1) **No vendor was contacted, trialled or demoed.** Every
competitor claim is read off marketing, listing-site summaries or review-site
feature tags, which describe what is SOLD and not what works. (2) **Feature-list
absence is not product absence** — §4's custody finding and §0's livery
differentiator both rest on absence from marketing pages, which is the weakest
form of evidence in this document and is labelled as such in both places. (3)
**Pricing is the independent-firm band only**; PlotBox, Halcyon and the
multi-location/cemetery-mapping tier are uniformly unpublished and are not
represented. (4) **No search was run in the negative** — I did not search for
"funeral software that lacks a CPL", so F1's "every established vendor sells it"
rests on two sources rather than a surveyed denominator. (5) **The FTC material
is current-as-read-today and the Funeral Rule has been under review** — a 2022
Federal Register notice appeared in the results and was not read, so a rule
change could move F1 and F2 in either direction. (6) **Part 1's internal half was
not re-run** — its code citations are as of this morning and are not re-derived
here.

---

## Re-derived at HEAD, 2026-10-06 (Fourth) — F1 AND F2 ARE BOTH CLOSED, and F1 was already closed when Part 2 called it "CONFIRMED AND WORSE"

**Re-derive before acting on any finding here.** This document was written on
2026-10-05 and two of its findings had already moved or moved the next day.
Both are now closed and both corrections are measured against the app at HEAD.

### F1 — closed the same day this document was written

Part 1 said the CPL and OBCPL *"are not modelled as price lists at all"* and
Part 2 raised the severity to *"the app has a screen where a regulated
disclosure is required and does not know it."* **At HEAD the app knows.**
Counted in `sairnlegacy.html` today:

| marker | Part 1 recorded | at HEAD |
|---|---|---|
| `CPL` | 0 | **6** |
| `OBCPL` | 0 | **3** |
| `casket price list` | 0 | **3** |
| `outer burial` | 0 | **12** |
| `16 CFR` | — | **2** |

And it is not prose. `openItemPriceList('casket')` and `('obc')` are two
buttons **on the Merchandise panel** at `sairnlegacy.html:433` — which is the
trigger Part 2 identified as the hard part — with the reasoning written beside
them at `:435`: *"16 CFR 453.2(b)(2) and (b)(3) require the CPL and the OBCPL
to be offered for inspection BEFORE caskets or containers are shown, and this
is the screen where they are shown."* `IPL_KINDS` at ~~`:3352`~~ **`:3446` (re-derived 2026-10-06; the declinability
work of the same day moved it, and the line this document cited is now inside
`legComposeStatement`)** maps each list to
its categories and its rule sentence, **a vault is counted as an outer burial
container and an urn as neither**, an empty list refuses to print as a
document, and a missing price prints `PRICE NOT ON FILE` rather than `$0`.

**So Part 2's own headline cell is stale about F1.** The table in §5 says
"CONFIRMED AND WORSE"; the correct reading at HEAD is *confirmed as the right
finding, and already built*. The analysis stays — the presentation trigger is
exactly why the buttons are on the merchandise screen and not under Documents.

### F2 — closed 2026-10-06, and the inference it was unsure about was right

Part 1 marked F2 **NOT DRIVEN**: *"I did not read the invoicing panel's
line-item structure closely enough to say what it *does* model."*

**Driven now, and the inference held.** `sairnlegacy.html`'s `saveInvoice()`
built `line_items` as `[{label, amount}]` from the CHECKED boxes only. An
unchecked box left no trace, so a family offered embalming who declined it
produced a byte-identical record to a family never offered it. `declinable`
measured **0** at HEAD before this change.

What landed:

* **Three states per line, not two** — `Selected` / `Declined` / `Not offered`,
  with **Not offered pre-checked**, so a director who has not reached a line
  does not have it read as a decline.
* **`declined_items` stored beside `line_items`** on the invoice record.
  `leg_invoices` keeps a `data jsonb` blob
  (`sql/sairnlegacy_data_schema.sql:208`), so this needed **no server change** —
  `api/sd-data.js` is hank's under an active claim and was not touched.
* **One non-declinable charge, and the app never guesses which.** 16 CFR
  453.2(b)(4)(iii)(C) permits exactly one — the basic services fee. The home
  ticks it in General Price List Rates; nothing is pre-ticked, and the seed
  list is deliberately unmarked even though it opens with *"Basic Services of
  Funeral Director and Staff"*, because matching that string would be a legal
  determination made by a substring. Zero marked is **disclosed**; two marked
  **refuses**; declining the marked one **refuses** and names it.
* **A Statement of Funeral Goods and Services Selected** (16 CFR 453.2(b)(5))
  per invoice, itemising selected items, listing declined items as declined,
  and — for an invoice saved before declines were kept — saying
  **"Not recorded… It is NOT a statement that nothing was declined"** rather
  than rendering an empty declined list. That third answer is the same fold F2
  names, one layer out.
* **A price that is absent is never 0.** A selected line with no price refuses,
  the total reports *"not computable"* rather than a figure, and the WRITER
  refuses too — the first draft mapped it to `amount: 0`, which would have put
  the refused value into the stored record while the screen looked correct.

**It still asserts nothing about compliance.** Whether a list was offered to a
family before the merchandise was shown is an act in a room; the statement says
so in its own footer.

**Driven by `tests/sairnlegacy_declinability.js` — 31 arms, 0 failed**,
extracting the composer from the app file by its own balanced braces
(`tests/lib/fn_span.js`) rather than a byte window, with a control proving the
declined and never-offered cases produce DIFFERENT stored records and an
ablation proving the writer's refusal is not a no-op.

### What is left of this document's findings

| Finding | At HEAD 2026-10-06 |
|---|---|
| **F1** CPL / OBCPL not modelled | **CLOSED** 2026-10-05 (CC) — buttons on the merchandise panel, with the trigger reasoning |
| **F2** `declinable` zero; declined ≡ never-offered | **CLOSED** 2026-10-06 (Fourth) — three states, `declined_items`, the Statement, 31 arms |
| **F3** preneed depth | Answered by Part 2 as a scoping question, not a code gap. Unchanged |
| Chain of custody as a differentiator | **STILL UNKNOWN**, as Part 2 says. No vendor advertises it; that is not evidence either way |
| Cemetery MAPPING may put us behind | **NOT RE-DERIVED HERE.** Outside this pass and not claimed as checked |
