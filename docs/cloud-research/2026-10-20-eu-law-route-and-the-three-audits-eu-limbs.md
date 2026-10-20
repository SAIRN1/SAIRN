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
