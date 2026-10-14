# AI wording package — for counsel — `[DRAFT — LAWYER]` throughout — 2026-10-14

**WHAT THIS IS.** Four pieces of customer-facing wording, in plain language,
plus exactly where each one appears in the software. **Every line of wording
below is a draft written by the engineering side and is not to be used until
counsel has reviewed or replaced it.** The mechanism is built and tested
separately; this document is only the words and their placement.

**The requirement it answers:** Anthropic's usage policy, **effective
2026-11-12**, which is the one date in this document.

**WHAT IS NOT HERE, DELIBERATELY:** no names, no email addresses, no phone
numbers, no firm details. The technical specification lives in
`docs/2026-10-14-ai-safeguards-spec.md`; this is the readable half.

---

## 1. THE FOUR PIECES, AND WHO SEES EACH ONE

| | piece | who sees it | how often |
|---|---|---|---|
| **A** | the AI notice | **every employee** who uses an app | **once**, at their first login |
| **B** | the owner acceptance clause | **the business owner** who signs for the account | **once**, at signature |
| **C** | the document footer | **anyone who receives a document** from the business | on every document that leaves the business |
| **D** | the assistant label | **anyone using a chat or assistant screen** | always on screen, not a popup |

**The design rule behind the table, decided by the business owner:
simple, and no repeated popups.** A, B and D are each shown once or shown
permanently; nothing nags.

---

## 2. A — THE AI NOTICE, shown once per employee

`[DRAFT — LAWYER]`

> **This app uses AI to help with some work.**
>
> AI suggestions can be wrong, incomplete or out of date. They are suggestions,
> not decisions.
>
> **A person is responsible for anything that is sent out, filed, or acted on.**
> Check AI output before you use it, the same way you would check a draft from
> a colleague.
>
> [ I understand ]

**WHERE IT APPEARS.** On the login screen, the first time a person signs in
after this is switched on. One button. **It is a notice that is acknowledged,
not a consent that can be withdrawn** — which is why the button says
*I understand* rather than *I agree*.

**WHAT IS STORED, so counsel can see exactly what the record is:** the version
of the notice the person acknowledged, and the date and time. It is stored
against that person's own login record, so the business can answer "who was
told, and when" without a separate list.

**IT IS NOT SHOWN AGAIN** unless the wording changes. If counsel revises this
text, the version changes and every employee sees it once more — once, not
repeatedly.

**TWO THINGS COUNSEL MAY WANT TO WEIGH:**

* *"A person is responsible"* — whether that sentence should name **the
  business** rather than the individual employee, and whether it should appear
  in the employee notice at all or only in the owner's agreement.
* Whether a jurisdiction requires the notice to say **which kinds of work** the
  AI assists with, rather than "some work".

---

## 3. B — THE OWNER ACCEPTANCE, once per account, in the service agreement

`[DRAFT — LAWYER]`

> **AI-assisted features.**
>
> The software includes features that use artificial intelligence to generate
> suggestions, drafts and summaries. AI output can be wrong. **The business
> remains responsible for reviewing AI output before it is relied on, sent to a
> customer or client, filed with any authority, or used to make a decision
> about a person.**
>
> The business is responsible for telling its own staff that the software uses
> AI, and for making sure the people who review AI output are competent to do
> so. The software shows each employee an AI notice at first login and keeps a
> record of that acknowledgement; **that record does not transfer
> responsibility for review to the software provider.**
>
> Where the software marks an output as high-risk and asks for a review before
> the output becomes a document or a decision, the business is responsible for
> ensuring that review is carried out by a person qualified to carry it out.

**WHERE IT APPEARS.** In the service agreement, accepted once when the account
is set up. **It is not a button inside the app and it does not gate anything:**
if the clause has not been accepted, the software still works. That is a
deliberate engineering decision — a business locked out of its own software
over paperwork is a worse outcome than an unsigned clause, and the gap is
visible to the provider either way.

**WHAT IS STORED:** that the clause was accepted, which version, when, and by
whom.

**THREE THINGS COUNSEL MAY WANT TO WEIGH:**

* Whether this belongs in the **main agreement**, an **annex**, or the
  **acceptable-use terms** — and whether existing customers need to accept it
  again or are covered by an amendment notice.
* Whether "competent to do so" is the right standard, or whether the regulated
  settings below need something stronger (a named licensed person).
* Whether the clause should say anything about **the AI provider**, or stay
  silent on who supplies the model.

---

## 4. C — THE DOCUMENT FOOTER, on anything that leaves the business

`[DRAFT — LAWYER]` — two forms, and **both are needed**:

> **AI-assisted. Reviewed by [name].**

> **AI-assisted. Not reviewed.**

**WHERE IT APPEARS.** At the foot of documents that go outside the business:
PDFs, printed documents, emailed quotes, invoices and letters, and documents
shown to customers or clients in a portal. **It does not appear on internal
screens.**

**WHY THERE ARE TWO FORMS AND WHY THE SECOND ONE MATTERS.** If nothing was
reviewed, the footer says so rather than disappearing. **A document with no
footer and a document nobody reviewed must not look the same** — otherwise the
footer's absence becomes the most common state and stops meaning anything.

**THE NAME.** It is the person who pressed **Reviewed** on that output, taken
from the record the software keeps. If counsel prefers a role to a person
(*"Reviewed by a licensed veterinarian"*), that is a wording change, not a
mechanism change.

**TWO THINGS COUNSEL MAY WANT TO WEIGH:**

* Whether naming an individual employee on a customer-facing document is
  appropriate in each setting, or whether it should be the business's name.
* Whether *"AI-assisted"* is the right phrase where AI produced only a small
  part of a long document — and whether a threshold is needed.

---

## 5. D — THE ASSISTANT LABEL, always on screen

`[DRAFT — LAWYER]`

> **AI assistant. Answers can be wrong.**

**WHERE IT APPEARS.** A single line on every chat or assistant screen, visible
the whole time it is in use. **It cannot be dismissed**, because a dismissible
label is a popup with extra steps.

---

## 6. WHERE THE "REVIEWED" STEP APPEARS — the five high-risk kinds of output

The software asks for a one-click **Reviewed** before an AI output becomes a
document or a decision, and **only** in these five categories:

| | category | the kind of business |
|---|---|---|
| 1 | **legal documents** — drafts, citations, estate documents | law practice, estate and funeral services |
| 2 | **medication or clinical suggestions** | assisted living, veterinary practice, dental practice, senior services |
| 3 | **hiring, pay or discipline** | any business using the HR features |
| 4 | **claim outcomes** | insurance-claim work |
| 5 | **investment or tax** | bookkeeping, accounting and financial features |

**It deliberately does NOT appear on** chat replies, searches, summaries,
internal drafting help, greetings, cost estimates or scheduling suggestions.
**A review button on everything is a review button nobody reads**, and that is
the failure mode worth naming to counsel: asking for too many confirmations
produces less review, not more.

**WHO PRESSED IT IS RECORDED** — the person, the output, and the time.

---

## 7. WHAT WE ARE ASKING COUNSEL TO DO

1. **Rewrite or approve the four pieces of wording** in §§2–5. They are drafts
   by engineers and are marked as such everywhere they appear.
2. **Say where B belongs** — main agreement, annex, or acceptable-use terms —
   and whether existing customers must re-accept.
3. **Say whether the employee notice carries the responsibility sentence**, or
   whether that belongs only in the owner's agreement.
4. **Say whether the footer names a person or the business.**
5. **Flag anything missing** for the regulated settings in §6 — in particular
   clinical, trust-account and personal-injury work, where a professional-
   conduct rule may require more than a notice.

**WHAT HAPPENS WHEN THE WORDING COMES BACK.** The notice carries a version
number. New wording means a new version, and every employee acknowledges it
once more — once each, not repeatedly. **Nothing has to be rebuilt to change
the words**, which is why the mechanism is being finished before the wording is
settled.

---

## 8. PLAIN STATEMENT OF WHAT THIS DOCUMENT IS NOT

* **It is not legal advice and it is not a compliance claim.** Whether this
  satisfies any policy, regulation or professional rule is counsel's reading,
  not an engineering result.
* **It is not final wording.** Every quoted block is `[DRAFT — LAWYER]`.
* **It contains no contact details** for anyone, by instruction.
* **It does not describe the data model, the database columns or the tests.**
  Those are in `docs/2026-10-14-ai-safeguards-spec.md`, which is written for
  engineers and is not the document to hand to counsel.
