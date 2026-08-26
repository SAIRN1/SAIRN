SAIRN TECHNOLOGIES LLC
[Letterhead — company address / contact placeholder]

**AMENDMENT NO. 1 TO THE DATA PROCESSING ADDENDUM**
Effective Date: [DATE] · Amends the SAIRN Data Processing Addendum dated [DATE]

---

## Plain-Language Summary

- This amendment adds **SAIRNdental** and **SAIRNsenior** to the parts of the DPA that already cover SAIRNcare and SAIRNvet.
- Nothing else in the DPA changes. Every other section stays exactly as it is.
- The effect is that patient and client health data in SAIRNdental and SAIRNsenior is treated as health data under the DPA, and the same Business Associate Agreement requirement applies before any of it goes in.
- This amendment **does not** create a BAA and is not a substitute for one. The BAA is still a separate document that has to be signed.

---

## 1. Purpose

This Amendment No. 1 ("Amendment") amends the SAIRN Data Processing Addendum ("DPA") between Customer ("Controller") and SAIRN Technologies LLC ("Processor," "SAIRN"). Capitalized terms not defined here have the meaning given in the DPA.

The DPA's health-data provisions currently name SAIRNcare and SAIRNvet only.

SAIRNdental processes patient records, appointments, treatment and procedure records, charges, payments, and clinical photographs. SAIRNsenior processes home-care client records, caregiver assignments, scheduled visits with electronic visit verification, and billing claims. Both therefore require the same framework. This Amendment adds SAIRNdental and SAIRNsenior to those provisions and makes no other change.

## 2. Amendment to Section 3 (Categories of Data Processed)

The second bullet of DPA Section 3 is deleted in its entirety and replaced with the following:

> For SAIRNcare, SAIRNvet, SAIRNdental, and SAIRNsenior: patient, animal health-related, dental patient, or home-care client health records — see Section 9 for the additional HIPAA framework that applies.

## 3. Amendment to Section 9 (Healthcare Data — HIPAA Addendum Trigger)

DPA Section 9 is deleted in its entirety and replaced with the following:

> **9. Healthcare Data — HIPAA Addendum Trigger**
>
> SAIRNcare, SAIRNvet, SAIRNdental, and SAIRNsenior may involve protected health information (PHI) or animal-health-equivalent records.
>
> Before onboarding a HIPAA-covered-entity workflow into SAIRNcare, SAIRNvet, SAIRNdental, or SAIRNsenior, Customer and SAIRN must execute a separate Business Associate Agreement (BAA). SAIRN must also have an executed BAA with Anthropic covering any PHI processed through AI features before offering these Apps to covered entities. Contact SAIRN before beginning this workflow.

## 4. No Other Changes

Except as expressly amended above, the DPA remains in full force and effect and is unchanged. This Amendment forms part of the DPA. In the event of a conflict between this Amendment and the DPA, this Amendment controls as to the sections it amends.

For the avoidance of doubt, this Amendment does not constitute, create, or substitute for a Business Associate Agreement. The requirement in Section 9 as amended remains a separate condition to be satisfied by a separate executed instrument.

## 5. Contact

SAIRN Technologies LLC — michael@sairn.com — Westlake, Ohio

---

**Signature**

By signing below, the parties agree to this Amendment No. 1 to the Data Processing Addendum.

Customer Signature: _______________________________     Date: ____________

Printed Name: _______________________________

Business Name: _______________________________

For SAIRN Technologies LLC:  _______________________________     Date: ____________

Michael L. Dibert, Owner

---

This document was prepared as a template by SAIRN Technologies LLC. It is not legal advice. SAIRN Technologies LLC recommends having any binding agreement reviewed by a licensed attorney in your jurisdiction before execution.

---

<!--
DRAFTING NOTES — NOT PART OF THE AMENDMENT. Remove before sending.

Drafted 2026-08-26 against the real SAIRN-Data-Processing-Addendum.docx
(2026-08-07, 14 sections), read in full. Conventions per
.claude/skills/sairn-contract-drafter/SKILL.md.

Signature block uses "Business Name", matching the MASTER documents, not the
"Company/Entity Name" the per-app agreements use. That difference is real in
the source material and is preserved deliberately -- this amends a master
document, so it follows master-document convention.

Replacement text quoted in full rather than described, so the amended section
can be read without holding the original alongside it. The Anthropic-BAA
sentence is carried through UNCHANGED from the original section 9 -- it is not
this amendment's business to alter it, and altering it silently would be the
worst possible edit to make while that BAA is being pursued separately.

SCOPE WIDENED 2026-08-26, deliberately and on instruction. This file was first
drafted for SAIRNdental alone and named accordingly; SAIRNsenior was then added
in the SAME amendment rather than a later one, so there is never a window in
which one health app is covered and the other is not, and so it costs one
signature instead of two. File renamed via git mv rather than re-created, so
the history of the narrower draft survives.

SAIRNsenior belongs here on the same evidence as SAIRNdental: it is a home-care
application whose own source carries a section headed "SAIRNSENIOR: sen_clients
HIPAA MINIMUM-NECESSARY PRIVACY GATE" (api/sd-data.js:2004). The code has
treated that data as PHI since 2026-08-20; only the paperwork lagged.

COMPANION AMENDMENTS, both required for this to be complete:
  docs/legal/SAIRN-ToS-Amendment-No1-Health-Apps-DRAFT-2026-08-26.md
  docs/legal/SAIRN-AUP-Revision-No1-Health-Apps-DRAFT-2026-08-26.md
ToS section 9 and AUP section 5 carry the same two-app limitation in their
headings as well as their text, and both plain-language summaries name the two
apps too. Amending the DPA alone would leave the other two silent.

The DPA's own Plain-Language Summary needed NO change -- checked rather than
assumed. It never names the healthcare apps; only sections 3 and 9 do.

TEMPLATE ONLY. Attorney review required before execution.
-->
