SAIRN TECHNOLOGIES LLC
[Letterhead — company address / contact placeholder]

**SAIRNROOFING SERVICE AGREEMENT**
Effective Date: [DATE]

---

## 1. Relationship to Platform Terms

This SAIRNroofing Service Agreement ("Agreement") supplements the SAIRN Platform Terms of Service, Data Processing Addendum, and Acceptable Use Policy (together, the "Platform Terms"), which apply in full to your use of SAIRNroofing. This Agreement adds terms specific to SAIRNroofing, SAIRN's roofing contractor management application. In the event of a direct conflict, this Agreement controls for SAIRNroofing-specific matters.

## 2. Subscription and Licensed Companies

SAIRNroofing is licensed on a monthly, auto-renewing subscription basis, per roofing company, with employee seats and branch locations as set out in your order form or account dashboard. A subscription covers one company license unless upgraded to a multi-location or multi-seat plan.

## 3. AI-Assisted Features and Measurement Output

SAIRNroofing uses AI (Claude, via Anthropic) to produce a **quantities schedule** from photographs you capture — squares, ridge, hip, valley, eave and rake linear footage, penetrations, pitch class, stories, and a waste factor.

This output is a decision-support estimate, not a survey. You are responsible for reviewing and correcting the quantities before they are used in an estimate, proposal, or material order, and for confirming them at the property where the job requires it.

SAIRNroofing does **not** perform aerial measurement, does not generate a geometric or three-dimensional roof model, and does not produce a facet or slope diagram. It produces a reviewable list of quantities. Any description of SAIRNroofing as roof-measurement or roof-modeling software would misstate the product.

## 4. No Insurance Advice from SAIRN; SAIRN Does Not Adjust Claims

SAIRN is a software provider. SAIRN is not an insurance adjuster, not a public adjuster, not an insurance producer, and does not provide insurance advice.

Several states restrict a roofing contractor from acting as a public adjuster on property that contractor is servicing — including Texas (Tex. Ins. Code § 4102.163) and Florida (Fla. Stat. § 626.854). SAIRNroofing's supplement worksheet and slope damage assessment are built to stay on the correct side of that line by construction: each performs an arithmetic comparison against figures **you** recorded and a reference **you** configured. Neither states what an adjuster should have included, and neither states that a roof should be repaired or replaced.

You remain solely responsible for all communication with carriers and adjusters, for any supplement you file, for compliance with the licensing and public-adjuster rules of every state in which you operate, and for confirming that your use of these features is permitted there.

## 5. Claim, Job, and Homeowner Data

Business data you enter into SAIRNroofing — job records, customer contact details, property addresses, photographs of customer property, claim records, adjuster contacts, signed contingency agreements, proposals and invoices — is Customer Data under the Data Processing Addendum. You own it. SAIRNroofing processes this data to provide the service per the DPA.

Photographs of a customer's property and a homeowner's captured signature are personal data of a third party. You are responsible for obtaining any consent or notice your jurisdiction requires before capturing and storing them.

**Evidence records are append-only.** Claim photographs, signed contingency agreements, and issued proposals cannot be edited or deleted through the application, by design, so the record of what was captured and signed remains intact. Corrections are made by adding a superseding record, not by altering the original.

## 6. Damage Assessment Thresholds Are Yours

SAIRNroofing ships no default damage threshold. The threshold against which slope evidence is assessed — and the source you cite for it — is entered by you, and every assessment result displays both. Where no threshold has been configured, the application refuses to assess rather than applying an industry convention on your behalf.

The assessment reports whether the evidence you recorded meets the threshold you configured. It is not a carrier decision, not a prediction of one, and does not determine coverage.

## 7. Service Availability

SAIRN uses commercially reasonable efforts to keep SAIRNroofing available. Standard pricing tiers do not include a guaranteed uptime SLA. Any SLA commitment must be set out in a separate written addendum.

## 8. Payment Terms

Subscription fees are billed monthly via credit card auto-billing. You may cancel at any time; cancellation takes effect at the end of the current billing period, with 30 days' notice requested where practical, per the Platform Terms.

## 9. Limitation of Liability

SAIRN's total liability arising out of or related to this Agreement is limited to the fees you paid SAIRN for SAIRNroofing in the three (3) months preceding the event giving rise to the claim, consistent with the Platform Terms.

## 10. Governing Law

This Agreement is governed by the laws of the State of Ohio, consistent with the Platform Terms.

---

**Signature**

By signing below, the parties agree to be bound by this Agreement.

Customer Signature: _______________________________     Date: ____________

Printed Name: _______________________________

Company/Entity Name: _______________________________

For SAIRN Technologies LLC:  _______________________________     Date: ____________

Michael L. Dibert, Owner

---

This document was prepared as a template by SAIRN Technologies LLC. It is not legal advice. SAIRN Technologies LLC recommends having any binding agreement reviewed by a licensed attorney in your jurisdiction before execution.

---

## Plain-Language Summary

- SAIRNroofing is licensed per roofing company, billed monthly, and auto-renews.
- You own your company's job, claim, and customer data.
- SAIRNroofing's AI (Claude) turns your photos into a **list of quantities** you review — it does not measure roofs from the air, does not build a 3D model, and does not draw a roof diagram.
- SAIRN is a software provider, **not an insurance adjuster**. The supplement worksheet and damage assessment do arithmetic against numbers you entered and a threshold you set — they never argue a claim for you, and you stay responsible for everything you send a carrier.
- The damage threshold is yours. We ship no default, and the app refuses to assess rather than guessing one.
- Claim photos and signed agreements are permanent records — corrections are added, not overwritten.
- We aim for high uptime but don't guarantee a specific SLA at standard pricing tiers.
- If something goes wrong, our liability is capped at fees you paid in the prior 3 months.
- The general SAIRN Platform Terms of Service, DPA, and AUP also apply — this agreement adds SAIRNroofing-specific terms.

---

<!--
DRAFTING NOTES — NOT PART OF THE AGREEMENT. Remove before sending to anyone.

Drafted 2026-08-26 against the 2026-08-17 per-app generation (SAIRNlaw /
SAIRNdesign / SAIRNlegacy), NOT the superseded 2026-08-07 StoneDesk agreement.
Conventions per .claude/skills/sairn-contract-drafter/SKILL.md.

Sections 1, 7, 8, 9, 10, the signature block and the disclaimer are copied
VERBATIM from the real documents. Do not reword them.

Section 4 is the professional-liability firewall, modelled on SAIRNlaw's
"No Legal Advice from SAIRN; No Attorney-Client Relationship". Roofing needs
one because the public-adjuster statutes are real and name contractors
specifically.

Sections 3, 5 and 6 were written from the code, not from memory:
api/_resources/sairnroofing.js, the rf_* handlers in api/sd-data.js, the
headers of api/_lib/roofing-supplement.js and roofing-damage-assessment.js,
and docs/superpowers/specs/2026-08-24-sairnroofing-v1-scope.md.

NOT CLOSED BY THIS DOCUMENT — see the accompanying gap report:
  * DPA §6 promises deletion on request; service_role holds no DELETE on the
    rf_* tables, so deletion needs owner-level database work. Section 5's
    append-only paragraph describes the behaviour honestly but does not
    reconcile the DPA commitment.
  * Pricing tiers are undecided; §2 points at the order form, as the real
    agreements do.
  * US 8,983,806 (Accurence) — the app is clear of claim 1 by one element.
    §3's "no facet or slope diagram" sentence is load-bearing for that and
    must not be softened.
  * Trademark screen for the SAIRN mark is still outstanding, platform-wide.

TEMPLATE ONLY. Attorney review required before execution.
-->
