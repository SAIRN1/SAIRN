# The EUR-Lex route, fixed — and the EU limbs the last three audits could not cite

**fourth / ted, batch b40, 2026-10-20.** b37, b38 and b39 each reported the
same failure and each said no EU instrument could be cited. **This closes it,
and then uses it.**

---

## 1. THE ROUTE

**WHAT FAILED, three batches running.** `eur-lex.europa.eu` HTML pages returned
an **empty body** to every attempt: b37 on the AMLR summary page, b38 on the AI
Act across **three** URL forms (`/eli/reg/2024/1689/oj/eng`,
`/legal-content/EN/TXT/HTML/?uri=OJ:L_202401689`,
`/legal-content/EN/TXT/?uri=CELEX:32024R1689`), b39 again.

**WHAT WORKS — and it is the OFFICIAL MACHINE ROUTE, not a workaround.** The EU
Publications Office exposes CELLAR with HTTP content negotiation on a CELEX
identifier:

    GET http://publications.europa.eu/resource/celex/<CELEX>
    Accept: application/xhtml+xml
    Accept-Language: eng

| CELEX | instrument | result |
|---|---|---|
| `32024R1689` | AI Act | **HTTP 200, 1,257,134 bytes** → `.../cellar/dc8116a1-3fe6-11ef-865a-01aa75ed71a1.0006.03/DOC_1` |
| `32024R1624` | AMLR | **HTTP 200, 1,165,026 bytes** → `.../cellar/868bf3cf-2dd4-11ef-a61b-01aa75ed71a1.0006.03/DOC_1` |

**NO BOT WALL IS INVOLVED AND NONE IS CIRCUMVENTED.** The 303 to a Cellar
resource is the documented behaviour of the identifier service. **This is the
EU equivalent of the eCFR renderer API** that b38 and b39 used after eCFR's web
pages 302'd to a bot wall — and in both cases the rule was the same: *stop at
the wall, find the published machine interface.*

Re-runnable: `scratchpad/b40/eu_fetch.py`.

---

## 2. AI ACT — Regulation (EU) 2024/1689, read from source

### 2.1 Article 113 — and the headline is that IT IS ALREADY IN APPLICATION

> *"It shall apply from 2 August 2026. However: (a) Chapters I and II shall
> apply from 2 February 2025; (b) Chapter III Section 4, Chapter V, Chapter VII
> and Chapter XII and Article 78 shall apply from 2 August 2025, with the
> exception of Article 101; (c) Article 6(1) and the corresponding obligations
> in this Regulation shall apply from 2 August 2027."*

Done at Brussels, **13 June 2024**.

**TODAY IS 2026-10-20, SO THE GENERAL APPLICATION DATE IS ELEVEN WEEKS PAST.**
Three audits treated the AI Act as a future cliff. **It is not a cliff; it is in
force.** Only `Article 6(1)` — the Annex I safety-component limb — is still
ahead, at **2 August 2027**.

### 2.2 Article 6 — the classification rule

* **6(1)**: high-risk where the system is a safety component of, or is itself, a
  product covered by the Union harmonisation legislation in **Annex I** *and*
  that product must undergo **third-party conformity assessment**.
* **6(2)**: *"In addition to the high-risk AI systems referred to in paragraph
  1, AI systems referred to in Annex III shall be considered to be high-risk."*
* **6(3)**: a derogation — an Annex III system is **not** high-risk where it
  *"does not pose a significant risk of harm to the health, safety or
  fundamental rights of natural persons, including by not materially
  influencing the outcome of decision making"*, and one qualifying condition is
  that it *"is intended to perform a narrow procedural task."*

### 2.3 Annex III point 5 — verbatim structure

> **5. Access to and enjoyment of essential private services and essential
> public services and benefits:**
> **(a)** AI systems intended to be used **by public authorities or on behalf of
> public authorities** to evaluate eligibility of natural persons for essential
> public assistance benefits and services, **including healthcare services**, as
> well as to grant, reduce, revoke or reclaim them;
> **(b)** creditworthiness or credit scoring, except fraud detection;
> **(c)** **risk assessment and pricing in relation to natural persons in the
> case of life and health insurance**;
> **(d)** emergency call triage and dispatch, *"as well as of emergency
> healthcare patient triage systems."*

### 2.4 THE ANSWER FOR SAIRNCODE, AND IT IS A NEGATIVE ONE

**SAIRNcode's AI coding path is NOT Annex III high-risk, and the reason is the
actor rather than the subject matter:**

* **5(a) is "by public authorities or on behalf of public authorities."** A
  dental or medical practice coding its own claims is neither.
* **5(c) is the INSURER's side** — risk assessment and pricing for life and
  health insurance. A provider assigning a CPT/ICD code is not pricing
  insurance.
* **5(d)** is emergency triage. Not this.
* **6(1)** needs an Annex I product under third-party conformity assessment.
  Not this, and in any case not until **2 August 2027**.

**AND THAT CONCLUSION IS LOAD-BEARING IN THE OTHER DIRECTION, so it is stated
as a boundary rather than a clearance:** the moment SAIRNcode were sold to, or
operated on behalf of, **a payer or a public authority** making eligibility or
pricing determinations, **5(a) or 5(c) would engage and the full high-risk
regime would follow.** That is a *commercial* line, not a technical one, and it
is exactly the kind of thing a vertical sale crosses without anybody filing a
code change.

**b38's B1 artefact is therefore right for the wrong-shaped reason.** It was
built against `45 CFR 170.315(b)(11)`, a US certification criterion. **It is
also, almost item for item, what AI Act Article 11 / Annex IV technical
documentation would ask for if 5(a) or 5(c) ever engaged** — intended purpose,
intended users, foreseeable misuse, training-data provenance, validation,
performance metrics, post-market monitoring. **One artefact, two regimes.**
Worth knowing before anybody treats B1 as US-only paperwork.

---

## 3. AMLR — Regulation (EU) 2024/1624, read from source

### 3.1 Article 90 — the dates, now sourced rather than asserted

> *"It shall apply from 10 July 2027, except in relation to obliged entities
> referred to in Article 3, points (3)(n) and (o), to which it shall apply from
> 10 July 2029."*

Done at Brussels, **31 May 2024**.

**b37 stated exactly these dates from a search snippet and b38/b39 then refused
to cite them. They were right. Now they are sourced** — which is the difference
between a figure that survives a reviewer and one that does not.

### 3.2 The privilege carve-out, and the clause nobody quoted

**[b41: the text quoted below is RECITAL (143). The OPERATIVE provisions are now located and read — Articles 21(2), 24(4) and 70(2)–(3). See §6. The inference clause IS in the operative text, at Art. 70(2)(c) and Art. 21(2)(c).]**

> *"Notaries, lawyers, other independent legal professionals, auditors,
> external accountants and tax advisors should not be obliged to transmit to the
> FIU or to a self-regulatory body any information received from, or obtained in
> relation to, one of their clients in the course of ascertaining the legal
> position of that client, or in performing the task of defending or
> representing that client in, or concerning, judicial proceedings, including
> providing advice on instituting or avoiding such proceedings, **whether such
> information is received or obtained before, during or after such
> proceedings**."*

**And the exception to the exception, which is the part that matters to a
product:**

> *"…except where the legal professional is taking part in money laundering or
> terrorist financing, the legal advice is provided for the purposes of money
> laundering or terrorist financing, or where the legal professional knows that
> the client is seeking legal advice for the purposes of money laundering or
> terrorist financing. **Such knowledge and purpose can be inferred from
> objective factual circumstances.**"*

**THAT LAST SENTENCE IS THE ONE WITH PRODUCT CONSEQUENCES AND NO AUDIT HAD IT.**
The carve-out is **not self-certifying**: knowledge can be *inferred from
objective factual circumstances*, and a practice-management system is where
those circumstances are recorded. b38's sairnlaw audit flagged AML as a company
decision because *"a product that prompts a lawyer to report is prompting a
privilege determination."* **This sharpens it in both directions** — the
determination is not purely the lawyer's subjective call, and the record the
software keeps is itself part of the objective circumstances. **It makes the
decision harder to defer, not easier.**

**Carve-out scope also extends further than b38 implied:** *before, during or
after* proceedings, explicitly.

---

## 4. WHAT THIS CHANGES IN THE THREE AUDITS

| audit | what it said | what the source says |
|---|---|---|
| **b37 sairnlaw** | AMLR applies 10 July 2027 (from a snippet); AML is a company decision because reporting means a privilege determination | **Dates confirmed from Article 90.** The privilege reasoning **holds and gets harder**: knowledge *"can be inferred from objective factual circumstances"*, and the carve-out covers before/during/after proceedings |
| **b38 sairncode** | *"No AI Act article, annex point or date is asserted anywhere"* | **Now asserted and sourced: SAIRNcode is NOT Annex III high-risk**, on the actor test, and the AI Act is **already in application** since 2 August 2026 |
| **b39 sairndesign** | *"No EU instrument is cited anywhere"* — CPR, GPSR, REACH all unread | **The ROUTE is fixed; those three instruments are still UNREAD.** §5 |

---

## 5. WHAT THIS DID NOT DO

* **Only TWO instruments were fetched.** The **Construction Products
  Regulation**, the **General Product Safety Regulation** and **REACH** —
  b39's sairndesign B5 — are **still unread.** The route now exists and they
  are one CELEX identifier each; **the work was not done in this batch** and
  that is a budget fact, not a finding.
* **Both documents were read by TARGETED EXTRACTION, not whole.** The AI Act
  flattens to 585,353 characters and the AMLR to 424,875; I read Article 113,
  Article 6, Annex III point 5, Article 90 and the privilege recitals. **The
  surrounding obligations — Articles 8 to 15, Annex IV, the AMLR's customer
  due-diligence chapter — were NOT read.**
* **THE AMLR PRIVILEGE TEXT IS A RECITAL, NOT AN ARTICLE**, and the
  distinction matters: a recital is interpretive, and the operative provision
  it explains was not located. **Do not build a reporting flow on §3.2 without
  finding the article.**
* **No consolidated-version check.** Both were read at the CELEX identifier's
  current Cellar representation; neither was checked for amendment since
  publication.
* **No legal review.** The Annex III conclusion in §2.4 is a reading of the
  text against a product description. It is the kind of conclusion a lawyer
  should confirm before it appears in anything customer-facing.
* **No competitor or market work.** Unchanged from all three audits.

---

## 6. b41 — THE AMLR PRIVILEGE CARVE-OUT, OPERATIVE TEXT

**fourth / b41, 2026-10-20.** b40 quoted the privilege language from a recital
and said the operative article had not been located. **It is three articles,
not one, and they do not say the same thing.** Same CELEX route, `32024R1624`,
HTTP 200, 1,165,026 bytes; each article below read in full.

### 6.1 The three operative carve-outs

| article | the duty it lifts | carve-out wording | "before, during or after" | exceptions (a)–(c) |
|---|---|---|---|---|
| **Art. 70(2)** | **Art. 69(1)** — report suspicions to the FIU, and answer FIU requests | *"in the course of ascertaining the legal position of that client, or performing their task of defending or representing that client in, or concerning, judicial proceedings, including providing advice on instituting or avoiding such proceedings"* | **YES** | **YES** |
| **Art. 24(4)** | **Art. 24** — report discrepancies with the central beneficial-ownership register | same wording | **YES** | **NO — a different limit:** the duty applies again when they *"provide legal advice in any of the situations covered by Article 21(2), second subparagraph"* |
| **Art. 21(2)** | **Art. 21(1)** — refrain from or terminate a relationship where CDD cannot be completed, and consider reporting | *"to the extent that those persons ascertain the legal position of their client, or perform the task of defending or representing that client …"* | **NO** — the phrase is absent | **YES** |

**The exceptions, verbatim from Art. 70(2) (Art. 21(2) is identical):** the
carve-out does not apply when the professional *"(a) take[s] part in money
laundering, its predicate offences or terrorist financing; (b) provide[s] legal
advice for the purposes of money laundering, its predicate offences or
terrorist financing; or (c) know[s] that the client is seeking legal advice for
the purposes of money laundering, its predicate offences or terrorist
financing; **knowledge or purpose may be inferred from objective factual
circumstances.**"*

**So b40's headline survives the move from recital to article, in the
operative text, twice.** The inference clause is law at Art. 70(2)(c) and Art.
21(2)(c), not just a recital's gloss.

### 6.2 What the operative text adds that the recital did not

1. **Art. 70(3) — Member States may narrow it.** *"Where justified on the
   basis of the higher risks … associated with certain types of transactions,
   Member States may decide that the exemption … does not apply to those types
   of transactions and, as appropriate, impose additional reporting
   obligations."* **The carve-out is a Union floor that each Member State can
   lower per transaction type, with notification to the Commission.** A product
   that encodes "privileged → no report" as a single EU-wide rule will be
   wrong in any Member State that has used 70(3), and this read does not say
   which have.
2. **The carve-out is per DUTY, not per client.** The same matter can be
   exempt from FIU reporting (70(2)) and still owe a beneficial-ownership
   discrepancy report (24(4)) if the advice falls into Art. 21(2)'s second
   subparagraph. A single "privileged" flag on a matter cannot answer both.
3. **Art. 21(2) does NOT carry "before, during or after".** For the
   terminate-or-refrain duty, the text is the narrower *"to the extent that
   those persons ascertain … or perform …"*. Whether that difference is
   deliberate is a question for counsel; the texts differ and this document
   says so rather than harmonising them.
4. **Art. 70(1)** lets Member States route reports from Art. 3(3)(a)–(b)
   entities through a self-regulatory body, which must forward them *"promptly
   and unfiltered"*. The reporting channel is national.

### 6.3 What this means for sairnlaw, stated as a boundary

b38's AML company decision stands, and the operative text makes the shape of a
compliant feature clearer: **three duties, three carve-outs, one shared
exception list with an objective-inference test, and a Member-State override
on the most important one.** A product feature would need, per matter, the
**basis** for each carve-out claimed (which of "ascertaining the legal
position" / "defending or representing … in proceedings" applies), and **must
not** record a privilege determination as settled when Art. 70(2)(c) makes it
rebuttable on objective facts the same system holds.

### 6.4 Not read

* **Articles 3(3) (who is an obliged entity among legal professionals) and
  73 (tipping-off)** were not read this batch.
* **No Member State's 70(3) decisions** — they are notified to the
  Commission and this read did not look for them.
* **No consolidated-version check.** No legal review.
