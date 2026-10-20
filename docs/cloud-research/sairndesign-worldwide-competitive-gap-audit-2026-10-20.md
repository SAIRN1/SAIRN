# Worldwide competitive-gap audit — SAIRNDESIGN

**fourth / b39, 2026-10-20.** Third in the primary-sources-only set, after
sairnlaw (b37) and sairncode (b38). A `sairndesign-competitive-gap-audit-2026-10-05.md`
already exists and is **competitor-facing**; this is the regulatory lens and
does not refresh it.

**TWO INSTRUMENTS READ IN FULL TEXT, ONE REPORTED UNREAD.** Where a rule number
appears below, its text was fetched through eCFR's documented renderer API.
**The eCFR web pages 302 to `unblock.federalregister.gov`, a bot wall, and that
was not routed around.**

---

## 0. THE RESULT

> **SAIRNdesign specifies physical products into occupied buildings and carries
> no compliance field of any kind on the record that does it.**

`sdn_specitems`' write (`sairndesign.html:2042`) stores:

    {project_id, item, vendor, sku, cost, retail, status,
     lead_time_weeks, one_of_a_kind, notes, created_at, reserved, reserved_for}

**Thirteen fields. Commercial, every one.** `grep -ci` over the whole file:

| | hits |
|---|---|
| `TB 117` / `TB117` | **0** |
| `formaldehyde` | **0** |
| `TSCA` | **0** |
| `flame` / `flammab` | **0** |
| `ASTM` / `E84` | **0** |
| `Prop 65` / `Proposition 65` | **0** |
| `accessib` | **0** |
| `ADA` | 3 — **and all three are inside the word "UNREADABLE"**. Stated because an alternation count is worthless without reading the hits |

**That is not a market gap. It is the one record in the app a regulator would
ask to see, with nowhere to put the answer.**

---

## 1. THE TWO INSTRUMENTS, READ IN FULL

### 1.1 16 CFR Part 1640 — upholstered furniture flammability

**Read in full (8,741 chars of text).** Authority: **sec. 2101 of Pub. L.
116-260** and **15 U.S.C. 1193**; source **86 FR 18443**, 9 April 2021.

* **§ 1640.2(a) — effective 25 June 2021.** **§ 1640.2(b) — the labelling
  requirement in § 1640.4 has been compulsory since 25 June 2022.**
* **§ 1640.5(a) — ALL upholstered furniture must comply with the California
  standard, Technical Bulletin TB 117-2013.** A state test method made the
  national requirement by incorporation.
* **§ 1640.4(b) — every subject product's certification label must bear the
  statement** *"Complies with U.S. CPSC requirements for upholstered furniture
  flammability"*.
* **§ 1640.5(b) — PREEMPTION.** No State or political subdivision may establish
  or continue a different flammability requirement. **(c)** preserves state law
  on *health* risks not aimed at fire.
* **§ 1640.3(e) — the scope is wide and catches what designers actually spec:**
  seating furniture intended for indoor use, movable *or stationary*, with an
  upholstered seat, back or arm, made or sold with a cushion or pillow
  (attached or detached) **or able to be stuffed or filled** — including
  concealed filling. **It expressly INCLUDES furniture intended for use by a
  child** and excludes bedding products and furniture used exclusively for
  physical fitness.

**One effective date, one compliance date, one named test bulletin, one
required label string.** This is the most precisely specifiable obligation in
any audit in this series.

### 1.2 40 CFR Part 770 — TSCA Title VI, composite wood formaldehyde

**Read targeted, from the full 135,826-char text.** Source **81 FR 89724**,
12 December 2016, as amended at **83 FR 5347** and **84 FR 43524**.

**§ 770.10 emission standards:**

| product | limit |
|---|---|
| hardwood plywood, veneer or composite core | **0.05 ppm** |
| particleboard | **0.09 ppm** |
| medium-density fibreboard | **0.11 ppm** |
| thin medium-density fibreboard | **0.13 ppm** |

**§ 770.45 Labeling, and this is the paragraph that reaches a designer:**
panels or bundles *"imported, sold, supplied, or offered for sale in the United
States"* must be labelled with **the panel producer's name, the lot number, the
EPA TSCA Title VI TPC number, and a statement that the products are TSCA Title
VI certified.** Where a panel is not individually labelled, the producer,
importer, distributor, **fabricator or retailer** must have a method sufficient
to identify the supplier and link the label information to the products — **and
*"This information must be made available to potential customers upon
request."*** **§ 770.45(c)** requires fabricators of finished goods containing
composite wood to **label every finished good they produce**. Only panels made
under **§ 770.17** may be labelled no-added-formaldehyde, and only **§ 770.18**
ultra-low-emitting.

**"Available to potential customers upon request" is the hook.** A designer's
client can ask, and the chain runs back through the designer's spec record —
which has no field for it.

---

## 2. WHAT SAIRNDESIGN IS

18 registered resources (`api/_resources/sairndesign.js`, bracket-matched
parse), 20 panels: `clients`, `spec`, `proposals`, `vendors`, `moodboards`,
`pos`, `invoicing`, `team`, `time`, `schedule`, `clientportal`, `samples`,
`contracts`, `referrals`, `discounts`, `reports`, `settings`, `security`, plus
`dashboard` and `ai`.

**`sdn_specitems` is the spine.** Everything downstream — proposals, purchase
orders, invoices, the client portal — is a view of what was specified.

---

## 3. THE GAP — THREE FINDINGS

### 3.1 **THE SPEC RECORD HAS NOWHERE TO PUT A CERTIFICATION, AND IT IS THE RECORD THAT NEEDS ONE**

A designer who specifies a sofa is specifying an article inside § 1640.3(e)'s
definition. The obligation to label sits on the manufacturer or importer — **but
the designer is the party who chose it, documented it, and will be asked about
it**, and the only field available is free-text `notes`.

**Same for millwork and casegoods under § 770.45:** the information must be
*available to potential customers upon request* and there is no field holding
the producer name, lot number or TPC number the request would be answered with.

**What makes this a finding rather than a wish:** the app already carries
`vendor` and `sku` per item, so **the join to a certification is one field
away**. It is not a data-model problem; it is a missing column.

### 3.2 **NO ACCESSIBILITY DIMENSION AT ALL, ON AN APP THAT STORES ROOM DIMENSIONS**

`sdn_roomdims` is a registered resource and `accessib` returns **0**. An
interior layout in a place of public accommodation is governed by the **2010
ADA Standards for Accessible Design**, and clearances are dimensional — exactly
the data `sdn_roomdims` holds.

**REPORTED HONESTLY: I did not fetch the ADA Standards this batch**, so no
clearance figure is quoted anywhere in this document and none should be taken
from it. The finding is the **absence of the dimension**, which is measured; its
*content* is not sourced here and is named in §5 as unread.

### 3.3 **THE PRODUCT CLAIM IS COMMERCIAL AND THE LIABILITY IS PHYSICAL**

Every one of the thirteen `sdn_specitems` fields is about money, time or
inventory: cost, retail, lead time, reserved. **The app models the designer's
business perfectly and the specified object not at all.** A fire, a
formaldehyde complaint or an accessibility action is answered from records this
app does not keep, which means a professional using it is complete on billing
and empty on the questions that carry real exposure.

---

## 4. WHAT WOULD HAVE TO BE BUILT

| | thing | size | blocker |
|---|---|---|---|
| **B1** | **A compliance block on `sdn_specitems`** — for upholstered seating: TB 117-2013 label sighted (y/n/not-applicable) + evidence; for composite wood: producer name, lot number, TPC number. **Three states, never two: compliant / not compliant / not established.** | **small — one field group on an existing record** | **none** |
| **B2** | **A per-item applicability test** so the block only appears where the rule bites — § 1640.3(e)'s scope is precise enough to encode, including its child-furniture inclusion and its bedding/fitness exclusions | **small** | none |
| **B3** | **A client-portal answer** to the § 770.45 *"available upon request"* duty, reading B1 | **small**, the portal exists | none |
| **B4** | **An accessibility dimension on `sdn_roomdims`** | **medium** | the ADA Standards were **not read** here; read them first |
| **B5** | **Non-US**: the EU Construction Products Regulation, the General Product Safety Regulation, REACH | **large** | **EUR-Lex is unfetchable by this route — §5** |

**B1–B3 have no blocker and together they are one field group, one predicate
and one portal panel.** That is the second audit in a row whose lead
recommendation is unblocked, after four that were not.

---

## 5. WHAT COULD NOT BE READ — REPORTED, NOT PARAPHRASED

1. **THE EU LIMB IS STILL UNSOURCEABLE AND THIS IS NOW THE THIRD BATCH RUNNING.**
   b37 (AMLR), b38 (AI Act, three URL forms) and this batch all hit EUR-Lex
   pages that return an **empty body**. **No EU instrument is cited anywhere in
   this document** — not the Construction Products Regulation, not the General
   Product Safety Regulation, not REACH. **A worldwide audit that cannot read
   EU law is a US audit with a wider title, and saying so is the only honest
   handling.** Fixing the route is worth more than the next audit.
2. **The 2010 ADA Standards for Accessible Design — NOT FETCHED.** §3.2's
   finding is the measured *absence* of an accessibility dimension, not a claim
   about any clearance. **Do not take a dimension from this document.**
3. **40 CFR 770 was read TARGETED, not whole** — §770.10's limits and §770.45's
   labelling text verbatim, out of 135,826 characters. The quarterly-testing,
   third-party-certifier and import-certification subparts were **not read**,
   and B1 should not be built as if they were.
4. **Interior-design licensure was not audited at all.** Title acts and
   practice acts differ per US state and per country; that is the
   per-jurisdiction matrix problem that killed b28 and b30, and it is named
   rather than half-done.
5. **No competitor product was driven and no market size is quoted** — the same
   deliberate hole as b37 and b38, with the same cost: **this audit cannot say
   whether anyone already ships B1–B5.**
6. **Nothing was driven in the app.** §0's field list is a source read of one
   write site; `sairndesign.html` is in **0** of this batch's commits.
