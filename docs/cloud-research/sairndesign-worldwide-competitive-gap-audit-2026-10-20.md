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
| **B1** | **[BUILT b41 — §6.1, and the composite-wood fields are the § 770.45(c)(2) finished-good label, not the panel fields named here]** **A compliance block on `sdn_specitems`** — for upholstered seating: TB 117-2013 label sighted (y/n/not-applicable) + evidence; for composite wood: producer name, lot number, TPC number. **Three states, never two: compliant / not compliant / not established.** | **small — one field group on an existing record** | **none** |
| **B2** | **A per-item applicability test** so the block only appears where the rule bites — § 1640.3(e)'s scope is precise enough to encode, including its child-furniture inclusion and its bedding/fitness exclusions | **small** | none |
| **B3** | **A client-portal answer** to the § 770.45 *"available upon request"* duty, reading B1 | **small**, the portal exists | none |
| **B4** | **An accessibility dimension on `sdn_roomdims`** | **medium** | the ADA Standards were **not read** here; read them first |
| **B5** | **Non-US**: the EU Construction Products Regulation, the General Product Safety Regulation, REACH | **large** | ~~EUR-Lex is unfetchable by this route — §5~~ **b41: all three read from source — §6.2** |

**B1–B3 have no blocker and together they are one field group, one predicate
and one portal panel.** That is the second audit in a row whose lead
recommendation is unblocked, after four that were not.

---

## 5. WHAT COULD NOT BE READ — REPORTED, NOT PARAPHRASED

1. **[SUPERSEDED b41 — §6.2 reads all three from source.]** **THE EU LIMB IS STILL UNSOURCEABLE AND THIS IS NOW THE THIRD BATCH RUNNING.**
   b37 (AMLR), b38 (AI Act, three URL forms) and this batch all hit EUR-Lex
   pages that return an **empty body**. **No EU instrument is cited anywhere in
   this document** — not the Construction Products Regulation, not the General
   Product Safety Regulation, not REACH. **A worldwide audit that cannot read
   EU law is a US audit with a wider title, and saying so is the only honest
   handling.** Fixing the route is worth more than the next audit.
2. **[CLOSED b43 — §7.3 reads the 2010 Standards from the DOJ text.]** **The 2010 ADA Standards for Accessible Design — NOT FETCHED.** §3.2's
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

---

## 6. b41 ADDENDUM — B1–B3 BUILT, AND THE EU LIMB READ FROM SOURCE

**fourth / b41, 2026-10-20.** Two things changed: B1–B3 are now in
`sairndesign.html`, and the three EU instruments §5.1 could not reach have
been read through the CELEX route b40 fixed.

### 6.1 B1–B3 — built, driven, and one correction to §4

**THE CORRECTION FIRST, because §4's B1 named the wrong label.** §4 said the
composite-wood block should hold *"producer name, lot number, TPC number"*.
Those are the **§ 770.45(a) panel** fields. A designer specifies **finished
goods** — a cabinet, a table, millwork — and **§ 770.45(c)(2)** gives a
finished good its own label: **the fabricator's name, the month/year
produced, and a statement that the goods are "TSCA Title VI compliant"**. The
panel label sits one step back in the chain, with the fabricator. **The build
records the finished-good label.** Re-read from the 40 CFR 770 text, not
recalled. Two further scope edges came out of the same read and are encoded:

* **§ 770.2(e)(4)** — composite wood made before **1 June 2018** may be sold
  at any time. A vintage piece is out of scope; the app already sells them.
* **§ 1640.2(a)** — Part 1640 applies to furniture *"manufactured, imported,
  or reupholstered on or after"* **25 June 2021**. Reupholstery re-enters scope.

**What is on the record now** (`sairndesign.html`, `saveSpec()` writes `cert`
at **:2062**): thirteen fields, five answering § 1640.3(e)(1)–(3) and
§ 1640.2(a), two answering § 770.3/§ 770.2(e)(4), and per regime a label state
(*not checked / sighted / absent*) plus evidence. **The record is stored in the
existing `data jsonb` column — no schema change, no SQL.**

**B2, the predicate** (`sdnUflScope` **:2111**, `sdnCwScope` **:2117**): any
disqualifying answer → *not applicable*; every qualifying answer → *applies*;
**anything unanswered → undetermined, which renders as NOT ESTABLISHED.** A
blank form never reads as out of scope and never as compliant. *Sighted* with
no evidence (or, for composite wood, no fabricator or production month) is
also not established, and the reason names what is missing.

**THE vendor + SKU JOIN** (`sdnCertForProduct` **:2169**) copies **product
facts only** — the four § 1640.3(e) scope answers, whether it contains
composite wood, the fabricator. **Unit facts never join**: a label sighting,
a production month, a pre-2021/pre-2018 date and evidence belong to the piece
in hand, and copying a sighting from another project's sofa would certify a
label nobody looked at. Both vendor and SKU are required — a SKU alone
collides across vendors.

**B3, the portal answer** (`sdnPortalCompliance` **:3607**): a Client Portal
card reads the record and quotes the **§ 1640.4(b)** statement or the
**§ 770.45(c)(2)** fabricator line where established, says *not established /
not compliant* with the reason where not, and keeps the denominator on screen
— *"1 of 3 item(s) where a rule applies or may apply are established
compliant · 1 outside both rules."* **Evidence notes are internal and are not
shown.**

**DRIVEN in Chromium against the real page: 66/66**, every exit of both
predicates, all four regime states, each missing composite-wood field named
individually, the worst-of-two overall, the modal → `saveSpec` → edit round
trip, the join (case/space-insensitive hit, different-vendor miss, no-SKU miss,
no self-join, unit facts left blank), the portal card, a legacy record with
no `cert` key, and the proposal-approval reservation path, which mutates the
record in place and **keeps** `cert`. **MUTATION CONTROL:** a predicate that
maps *undetermined* to *not applicable* makes the blank-record assertion read
`not_applicable` → **CONTROL_PASS true**. Script:
`scratchpad/b41/drive_design.py`.

**REPRODUCED FIRST:** before the change a seeded spec item had 14 keys and
none for compliance, the modal had 11 inputs, the portal had 4 cards, and
`sdnCertState` was `undefined`.

### 6.2 The EU limb — three instruments, one CELEX each, read from source

Route: `GET http://publications.europa.eu/resource/celex/<CELEX>`, content
negotiation, as in b40. **REACH has no XHTML manifestation** (HTTP 404 for
`application/xhtml+xml` and `text/html`); the **PDF** manifestation answered
200 and was text-extracted (849 pages). **No wall was involved.**

| instrument | CELEX | fetched | in application |
|---|---|---|---|
| **CPR** — Regulation (EU) 2024/3110 | `32024R3110` | 200, 1,030,210 B | **8 January 2026** (Art. 96); Reg. 305/2011 repealed from that date **except listed articles kept to 8 January 2040** (Art. 94) |
| **GPSR** — Regulation (EU) 2023/988 | `32023R0988` | 200, 452,216 B | **13 December 2024** (Art. 52) |
| **REACH** — Regulation (EC) 1907/2006 | `32006R1907` | 200, PDF 1,864,477 B | entry into force **1 June 2007** (Art. 141(1)); Title IV, which holds Art. 33, is **not** in Art. 141(2)'s deferred list — *a reading, stated as one* |

**All three are in application today. None is a future cliff.**

**REACH Article 33(2) is the EU twin of § 770.45's "upon request", and it
names the designer directly.** *"On request by a consumer any supplier of an
article containing a substance meeting the criteria in Article 57 and
identified in accordance with Article 59(1) in a concentration above 0,1 %
weight by weight (w/w) shall provide the consumer with sufficient information,
available to the supplier, to allow safe use of the article including, as a
minimum, the name of that substance … free of charge, within 45 days."*
**Art. 3(33)**: a *supplier of an article* is *"any producer or importer of an
article, distributor or other actor in the supply chain placing an article on
the market"*. **Art. 3(3)**: furniture is an *article*. A designer who resells
is a supplier, and **the 45-day clock runs against a record this app does not
keep** — there is no field for a supplier's SVHC declaration.

**GPSR — the designer is a distributor, and can become a manufacturer.**
**Art. 3(11)** distributor = anyone in the supply chain other than manufacturer
or importer who makes a product available. **Art. 12(1)**: before making a
product available, verify the manufacturer met **Art. 9(5)** (a type, batch or
serial number visible to consumers), **9(6)** (manufacturer name, postal **and
electronic** address) and **9(7)** (instructions and safety information in the
consumer's language). **`vendor` is not the manufacturer and `sku` is not
necessarily the 9(5) identifier.** **Art. 13(2)–(3)**: whoever *substantially
modifies* a product — a change with a safety impact, not foreseen in the
original risk assessment, not made by the consumer for their own use — **is
deemed the manufacturer** for the affected part. **Reupholstery and custom
alteration, which this app's clients commission, are the case.** **Art.
2(2)(i) excludes antiques** (defined **Art. 3(28)** as items such as
collectors' items or works of art where consumers cannot expect state-of-the-
art safety); **Art. 2(3) includes used and reconditioned products.** *Vintage
is not antique*, and the app's one-of-a-kind flag does not distinguish them.

**CPR — only for what is built in, and the duty is to display.** **Art.
3(1)** construction product = an item placed on the market *"for
incorporation in a permanent manner into construction works"*; **3(3)**
permanent = intended to remain after completion. Movable furniture is out;
flooring, wall finishes and fixed fit-out a designer supplies are in.
**Art. 25(2)**: before making one available the distributor verifies CE
marking, the **declaration of performance and conformity** (or its
availability under Art. 16(2)), and instructions/safety information; **Art.
25(3)**: the distributor *"shall display to customers, in a visible manner,
before they are bound by a sales contract"* the information the Regulation
requires. **That is a pre-contract duty, and the proposal is where this app
binds the client.**

### 6.3 What the EU read adds to §4

| | thing | size | blocker |
|---|---|---|---|
| **B6** | **REACH Art. 33(2)**: per item, the supplier's SVHC declaration (substance name or "none above 0.1 % w/w declared"), plus a request log with the **45-day** due date | small | none |
| **B7** | **GPSR Art. 9(5)–(6)/12(1)**: manufacturer name + postal + electronic address and the product identifier, distinct from `vendor`/`sku`; **an antique / not-antique answer** (Art. 2(2)(i)); a *modified by us* flag that surfaces **Art. 13(2)** | small–medium | none |
| **B8** | **CPR Art. 25(3)**: a *permanently incorporated* flag and a DoPC reference, shown **on the proposal** before the client signs | medium | the proposal flow, not the spec record |

**B6–B8 are not built.** They are specified here, from source, for the next
session.

### 6.4 What was NOT read — stated, not paraphrased

* **Targeted extraction, not whole reads**: CPR 370,061 chars flattened,
  GPSR 187,350, REACH 978,665 (PDF text). Articles quoted above were read in
  full; the rest was not.
* **REACH is the 2006 Official Journal text, NOT the consolidated version.**
  The Candidate List (Art. 59) and Annex XVII restrictions have been amended
  many times since; **nothing here says which substances are listed today**.
* **No consolidated-version check on CPR or GPSR either.**
* **No Member State law** — GPSR Art. 9(7)'s language rule is per Member
  State, and penalties are national.
* **No legal review.** Who is a *distributor* turns on whether the designer
  takes title and resells or only specifies; both business models exist and
  this audit does not decide which a given customer runs.

---

## 7. b43 ADDENDUM — THE UK LIMB, THE ADA STANDARDS, AND B1–B3 PROVEN ON THE RUNNING APP

**fourth / b43, 2026-10-20.** This audit has existed since b39 (US) and b41
(EU, §6). This increment closes **§5.2**, which said the ADA Standards were
not fetched. It adds the **first non-EU, non-US jurisdiction**, and it proves
B1–B3 against the live app with a real server write.

### 7.1 B1–B3 on the running app — a real write, read back, then restored

This is the open item b41 named: *"one real write of `cert` to the real
endpoint, read back"*. It is now closed.
- **How it ran:** the real login at `https://sairn.vercel.app/sairndesign.html`
  on the demo licence (`SDN-PINNACLE-2026`, role `owner`), then the UI path
  `editSpec` → cert form → `saveSpec` on record `SP-1786203933218-222`.
- **Read back from the server, not localStorage:** all 13 `cert` fields
  persisted, and `sdnCertState()` recomputed from the server copy gives
  **compliant**.
- **Restored:** the original record was then written back. A server read
  after that is **byte-identical to the original** (sorted-key JSON compare),
  so the demo tenant ends as it started.
- **Result: 9/9** (`scratchpad/b43/live_design.py`). **The `data jsonb`
  route needs no schema change, as §6.1 claimed — now measured, not argued.**

### 7.2 UK — The Furniture and Furnishings (Fire) (Safety) Regulations 1988

**SI 1988/1324**, fetched as the official XML from
`https://www.legislation.gov.uk/uksi/1988/1324/data.xml` (HTTP 200, 176,963
B). **That is the revised text as legislation.gov.uk holds it.** Regs 10, 12
and 13 appear there as revoked; the date of revision was not checked.

| reg. | what the text says | what it means for this app |
|---|---|---|
| **3** "furniture" | *"furniture of any description which is ordinarily intended for private use in a dwelling"*, and it **includes beds, divans, sofa-beds, cushions, mattresses and pillows** | **Wider than 16 CFR 1640**, whose § 1640.3(e)(3) **excludes** mattresses, foundations and bedding. **The B2 predicate built in b41 is US-only:** answering "bedding/mattress = yes" makes an item n/a, but in the UK that same item is in scope |
| **4** | the Regulations do not apply to goods **manufactured before 1 January 1950**, nor to re-upholstery materials for such furniture | **A third vintage line**, after 1640's **25 June 2021** and 770's **1 June 2018**. One `pre2021` answer cannot carry three jurisdictions' cut-offs |
| **5** | upholstery must pass the **cigarette test** (Sched. 4) | a test result, not a label sighting |
| **8** | permanent covers must pass the **match test** (Sched. 5) | same |
| **11** | furniture covered by Sched. 7 must bear the **permanent labelling** set out there | the UK analogue of § 1640.4(b) |
| **14** | **second-hand furniture** previously supplied to a non-dealer must still satisfy regs 5, 6 and 8(1)–(2), unless reg. 4 excludes it | **a vintage piece made in 1950 or later and resold in the UK is IN scope.** The app's one-of-a-kind / vintage flag is exactly this case |
| **15** | **"no person shall supply"** furniture that fails any requirement | the duty sits on **any** supplier, a reselling designer included |

**This is the sharpest finding in the increment.** The US predicate treats
"vintage" as a way *out* of scope (1640.2(a); 770.2(e)(4)). In the UK,
reg. 14 pulls second-hand furniture back *in*, and only pre-1950 goods are
excluded.

### 7.3 2010 ADA Standards for Accessible Design — §5.2 closed

Source: DOJ PDF `https://www.ada.gov/assets/pdfs/2010-design-standards.pdf`
(HTTP 200, 279 pages, text-extracted). **Every figure below is quoted from
that text.**

| section | requirement |
|---|---|
| **305.3** | clear floor or ground space **30 in min × 48 in min** |
| **304.3.1** | turning space **60 in diameter min** (or a T-shape in a 60 in square, 304.3.2) |
| **403.5.1** | walking-surface clear width **36 in min** (32 in for 24 in max as an exception) |
| **902.2 / 902.3** | dining and work surfaces need a 305 forward-approach space and 306 knee/toe clearance; tops **28 in min, 34 in max** above the floor |
| **226.1** | where dining surfaces are provided, **at least 5 percent** of seating and standing spaces comply with 902; the same for work surfaces used by **other than employees**. Sales and service counters are excepted |

**What the app holds against that.** `sdn_roomdims` stores **`width_ft`,
`length_ft`** — one rectangle per project (`saveRoomDimensions()`). Spec
items carry **no dimension and no height**, and `sdn_projects` carries **no
occupancy type** (fields: `client_id name budget target_install_date status
notes`).

**So none of the ADA checks is computable today, for a precise reason.**
Each needs either a **height on a spec item** (902.3), a **count across the
items in a room** (226.1's 5 percent), or a **layout** (305/403/304), and the
first two need to know whether the project is a **place of public
accommodation** at all. A residential client is outside Title III.

### 7.4 What this adds to §4

| | thing | size | blocker |
|---|---|---|---|
| **B4** *(replaces §4's B4)* | **Project occupancy** (residential / public accommodation / employee-only). Then, on spec items that are dining or work surfaces, **a top height** checked against **902.3 (28–34 in)**, and a **226.1 count**: at least 5 percent compliant, shown as N of M | small–medium | none — **the Standards are now read** |
| **B9** | **Jurisdiction on the project, and a predicate per jurisdiction.** The UK's reg. 3 scope (bedding in), reg. 4 date (1950) and reg. 14 (second-hand in) contradict the US predicate on three answers out of five | medium | which jurisdictions to support is a product decision |
| **B10** | **Layout clearances** (305 / 304 / 403) | large | needs furniture placement, which this app does not model |

**B4's first half and B9's data field are unblocked.** B10 is honestly large.

### 7.5 Not read, or not done

* **UK Schedules 4, 5 and 7 (test methods and label text) were not read**,
  so no label wording is quoted for the UK.
* **No other Commonwealth or Asian jurisdiction**, e.g. Canada's flammability
  regulations or Australia's. The UK is the one non-EU, non-US limb added.
* **ADA Title III scoping beyond 226.1** (e.g. the 2010 Standards' 802/803
  spaces) was not read, and **no state building code** was read.
* **No competitor was driven**, the same deliberate hole as before.
* **No legal review.** Whether a designer is a "supplier" under reg. 15 turns
  on whether they take title, as with the EU distributor question in §6.4.
