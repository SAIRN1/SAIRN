# SAIRNdesign competitive-gap audit — 2026-10-05 (CC). **Both halves, in one pass.**

**Second of the three apps that had no competitive-gap doc of any kind**
(`docs/2026-09-29-competitive-gap-doc-inventory.md`: `sairndesign`,
`sairnlegacy`, `sairnscape`). SAIRNlegacy's was written earlier today.

**WHY THIS ONE CARRIES BOTH HALVES AT ONCE, unlike SAIRNlegacy's Part 1.** That
document deliberately shipped its internal half alone, and then its own Part 2
**killed its single most load-bearing claim** — the breadth thesis — because the
guess an internal-only read invites is a guess *in favour of the platform*. The
lesson was cheap there and is applied here: the competitor column goes in the
same pass or the document is not written.

Every internal figure is measured at `sairndesign.html` at HEAD today. Every
competitor claim is **vendor marketing or a review-site feature tag** and is
labelled as such — evidence of what is *sold*, which is the right evidence for a
gap and the wrong evidence for whether it works. Sources at the end.

---

## 1. What SAIRNdesign is, measured

**20 panels:**

```
ai        clientportal  clients   contracts  dashboard  discounts  invoicing
moodboards  pos         proposals  referrals  reports    samples    schedule
security  settings      spec       team       time       vendors
```

**30 `sdn_*` collections.** `docs/CRITICALITY-TIERS.md` carries **18** register
rows for them, **10 rated Tier A**.

The shape is a **studio operations platform**: client → proposal → contract →
purchase order → invoice, with moodboards, a sample library, a spec list, time
tracking, a client portal and a referral ledger around it. The app describes
itself in its own AI system prompt (`:1888`, `:1919`) as *"a studio operations
assistant for an interior design business (trade markup, client proposals…)"* —
so **trade markup is the app's own stated centre of gravity**, which is the right
instinct for this category.

---

## 2. THE FINDING: `tax` APPEARS ZERO TIMES, AND THAT IS CONTROLLED

| Term | Occurrences in `sairndesign.html` |
|---|---|
| `tax` — **any case, any context, the whole file** | **0** |
| `sales tax` / `tax_rate` / `taxable` | **0** |
| `resale certificate` | **0** |
| `freight` | **0** |
| `procurement` | **0** |
| `expedit`(ing) | **0** |
| `sidemark` | **0** |
| `to the trade` | **0** |
| `cost plus` | **0** |
| `retainer` | **0** |
| `markup` | 21 |
| `trade discount` | 13 |
| `purchase order` | 7 |
| `receiv`(ing) | 13 |
| `tracking` | 8 |

**THE ZERO IS CONTROLLED, WHICH IS WHAT MAKES IT A FINDING RATHER THAN A WORD
COUNT.** It is not a platform convention to leave tax out: `sairnbiz.html` has
**6** occurrences of sales-tax vocabulary and `stonedesk.html` has **8**. So two
sibling apps on the same platform model it and this one does not.

**WHY IT MATTERS SPECIFICALLY HERE, and it is the defining mechanic of the
trade:** an interior designer **buys at trade cost and resells to the client**.
That makes the studio a reseller, which means (a) sales tax is charged to the
client on the resold goods, and (b) the studio presents a **resale certificate**
to the vendor so it is not taxed twice. A platform that runs
proposal → PO → invoice for resold goods and has **no tax concept at all** cannot
produce a correct client invoice for merchandise in any US state that taxes it.

**AND THE PO RECORD CONFIRMS IT RATHER THAN THE COUNT INFERRING IT.** Read at
`:2935`:

```js
var rec={id:newId('PO'),po_number:'PO-'+…,project_id:pjId,vendor:vendor,
  item_ids:…,total_cost:items.reduce(… s+(Number(x.cost)||0) …),
  status:'Draft',created_at:sdnLocalToday()};
```

Eight fields. `total_cost` is **a sum of item costs and nothing else** — no
freight, no tax, no ship-to, no sidemark, no expected or actual receiving date.

---

## 3. THE COMPETITOR COLUMN — and procurement is the category's spine, not a feature

| | SAIRNdesign at HEAD | What the category sells |
|---|---|---|
| Trade markup | **Yes** — 21 mentions, its own KPI (`Avg Markup`, `:310`, `:400`), the app's stated centre | **Yes**, and *item-level* with configurable markup **before client view** (Studio Designer) |
| Purchase orders | **Yes**, 8 fields | **Yes** — plus expediting, **receiving**, and **freight tracking** (Studio Designer) |
| Freight | **0** | **Advertised by name** |
| Sales tax / resale | **0** | Implicit in every accounting-integrated tier; QuickBooks sync is a headline on DesignFiles |
| Moodboards / boards | **Yes** | **Yes** — design boards, product clipping (Houzz Pro / Ivy), client collaboration |
| Client portal | **Yes** | **Yes** |
| Time tracking | **Yes** | Yes |
| Payment processing | a `pos` panel | **A PRICED, ADVERTISED DIFFERENTIATOR** — Studio Designer 3.25% + 60¢ card, 0.5% ACH capped at $25; DesignFiles 2.9% + 30¢ *"Stripe at cost"* and ~0.8% ACH |

**SO THE GAP IS NOT BREADTH AND IT IS NOT MARKUP — IT IS THE MIDDLE OF THE
PROCUREMENT CHAIN.** Studio Designer's advertised spine is *vendor records,
purchase orders, expediting, receiving, freight tracking, item-level trade
pricing*. SAIRNdesign has the two ends — PO and markup — and **none of the three
middle steps**, and the absent one with a name a buyer will ask about is
**freight**, because freight on a $12,000 sofa is not a rounding error and it is
billed to the client.

**`sidemark` IS THE SHARPEST SINGLE ABSENCE and it is a one-word test.** A
sidemark is how the whole trade routes a shipment to the right project and
client — it goes on every PO and every delivery. Zero occurrences. A designer
evaluating this app will look for that field, not for a feature list.

---

## 4. PRICING — and the unit is MISALIGNED with this platform, which SAIRNlegacy's was not

| Vendor | Published price | Unit |
|---|---|---|
| **Studio Designer** | from ~**$65 / user / month**, Basic; Pro and Team add accounting | **PER USER**, annual contract + onboarding fee |
| **Houzz Pro** | Essential **$99/mo** annual (**$149** month-to-month), single user, **+$60/mo per additional user** | **PER USER** |
| **Ivy (Houzz)** | **$45/mo** | per user |
| **DesignFiles** | **$49/mo** e-Design, **$69/mo** Full Service | per user/firm |

**THIS IS THE OPPOSITE OF THE DEATH-CARE FINDING AND THAT CONTRAST IS THE POINT.**
SAIRNlegacy's category prices **per firm** — Gather advertises *"no per-user
fees"* as a selling point — and this platform's licence-key-per-tenant model
aligned with it. **Interior design prices PER USER and per seat**, with Houzz Pro
charging $60/month for the second seat.

**So the same licence model that fits SAIRNlegacy under-monetises SAIRNdesign by
construction.** A five-person studio pays one tenant licence here and would pay
roughly $325/month at Studio Designer's Basic rate. That is a commercial finding
about the **platform**, not about the app, and nothing in this repo has stated it
before.

**NOT CLAIMED:** no quote was obtained; Studio Designer's Pro/Team rates and
every enterprise tier are unpublished, and the figures above are list prices from
vendor and review-site pages read today.

---

## 5. Ranked, and the two rankings agree here — which is unusual

| # | Finding | Severity | Competitor beating us? |
|---|---|---|---|
| 1 | **No tax concept of any kind**, controlled against two sibling apps that have one. A reseller platform that cannot compute tax on resold goods cannot produce a correct client invoice | **HIGH** | **Yes, implicitly** — every accounting-integrated tier assumes it |
| 2 | **No freight, receiving or expediting** — the three middle steps of the advertised procurement spine | **HIGH** | **Yes, explicitly, by name** |
| 3 | **No `sidemark`** — the trade's universal shipment-routing field | **MODERATE** | **Yes**, and it is the one-word disqualifier |
| 4 | **Per-user pricing norm vs this platform's per-tenant licence** | **MODERATE (commercial)** | N/A — this is our pricing, not their feature |
| 5 | Payment-processing rates are a priced, advertised differentiator and we have an unexamined `pos` panel | **LOW–MOD** | **Unknown** — our rates are not stated anywhere read here |

**Unlike SAIRNlegacy, severity and exposure point the same way**, because every
item above is a thing a prospect meets in the first week of real use rather than
an internal verification gap.

---

## 6. Sources

* [Studio Designer — the best interior design software (vendor comparison)](https://www.studiodesigner.com/blog/the-best-interior-design-software/)
* [mortar.design — Interior Design Software Cost 2026: Real Prices & Payment Fees](https://mortar.design/blog/interior-design-software-cost-2026)
* [DesignFiles — Houzz Pro vs Studio Designer](https://blog.designfiles.co/houzz-pro-vs-studio-designer/)
* [Programa — Best Interior Design Software Guide](https://programa.design/best-interior-design-software-guide)
* [knowlix — Studio Designer Alternative: 9 Tools for Design Firms in 2026](https://knowlix.ai/blog/studio-designer-alternative)
* [agiled.app — 9 Best All-in-One Software for Interior Designers (2026)](https://agiled.app/blog/best-all-in-one-software-for-interior-designers)

---

## What this document does NOT claim

* **No vendor was trialled or demoed.** Every competitor claim is marketing or a
  review-site feature tag.
* **No panel of SAIRNdesign was clicked.** Every internal figure is read out of
  the file; nothing was driven and no record was written.
* **The 20-panel figure counts panel DIVs**, not working features.
* **The Tier A breakdown was not re-read** — 10 of 18 `sdn_*` rows are rated A
  per `docs/CRITICALITY-TIERS.md`, and that file was found today to carry
  withdrawn boilerplate on other rows, so it is not safe to quote without
  opening the rows.
* **`tax` = 0 is a lexical fact.** It is strong because it is controlled against
  two sibling apps and because the PO record was read directly, but a tax
  capability implemented without the word would not appear in it.

**BLIND SPOTS: 5.** (1) The competitor half rests on marketing and
listing-site summaries; **feature-list absence was not used as evidence anywhere
in this document**, which is the one methodological improvement over
SAIRNlegacy's Part 2. (2) No search was run in the negative — I did not look for
a serious competitor that *also* lacks tax or freight, so "the category sells it"
is an inference from four vendors rather than a surveyed denominator. (3)
Pricing is list-price only and every mid/enterprise tier is unpublished. (4) The
invoicing panel's line-item structure was not read, so what `sdn_invoices`
*does* model is unestablished — the tax finding is about the absence of the
concept, not about a specific wrong total. (5) `sairnscape` is still unaudited
and is now the last of the three; nothing here measures whether it should be next
or whether it has a buyer.
