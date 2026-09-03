---
name: sairn-contract-drafter
description: How to draft a per-app SAIRN service agreement so it matches the real, executed house convention instead of inventing one. Extracted 2026-08-26 from the four real master documents and the two real per-app agreements on disk, not designed from scratch. Trigger whenever a new SAIRN app needs a customer-facing service agreement, whenever someone asks for "the contract", "the service agreement", "terms for <app>", or before any app is offered to a real prospect. Also read it before AMENDING a master document — several per-app gaps can only be closed in the ToS or DPA, not in the app agreement.
---

# SAIRN Contract Drafter

Extracted the way `sairn-grant-sweep` was: from the real artifacts, after
reading them. Nothing here is invented convention.

**Source material, read 2026-08-26** (all in `C:\Users\marsh\Downloads\`, none
in Google Drive, none tracked in any repo — see *Where the documents live*):

| Document | Date | Sections |
|---|---|---|
| `SAIRN-Platform-Terms-of-Service.docx` | 2026-08-07 | 15 |
| `SAIRN-Data-Processing-Addendum.docx` | 2026-08-07 | 14 |
| `SAIRN-Acceptable-Use-Policy.docx` | 2026-08-07 | 8 |
| `SAIRN-StoneDesk-Service-Agreement.docx` | 2026-08-07 | 8 |
| `SAIRN-SAIRNlaw-Service-Agreement.docx` | **2026-08-17** | **9** |
| `SAIRN-SAIRNdesign-Service-Agreement.docx` | 2026-08-17 | (same generation) |
| `SAIRN-SAIRNlegacy-Service-Agreement.docx` | 2026-08-17 | (same generation) |

Also present and not to be confused with these: `SAIRN-Mutual-NDA.docx`,
`SAIRN-Vendor-Subcontractor-Agreement.docx`.

## 1. Draft against the 2026-08-17 generation, NOT StoneDesk

**The first thing this skill exists to prevent.** StoneDesk's agreement is the
oldest per-app document and is routinely described as "the existing pattern."
It is the *superseded* pattern. Three per-app agreements written ten days later
(SAIRNlaw, SAIRNdesign, SAIRNlegacy) add a structural section StoneDesk does
not have, and that section is the whole point of the newer generation.

**What the Aug 17 generation added: a professional-liability firewall.**
SAIRNlaw §4 is *"No Legal Advice from SAIRN; No Attorney-Client Relationship"* —
an explicit statement that SAIRN is a software provider, not a practitioner of
the regulated profession the app serves, and that the customer's licensed
people retain all professional judgment. StoneDesk has no equivalent because
stone fabrication is not a licensed profession.

**Rule: if the app serves a licensed or regulated trade, it needs that
section.** Roofing (public-adjuster statutes), dentistry (clinical practice,
HIPAA), senior care, veterinary, medical coding — all qualify. Draft the firewall
before anything else; it is the section most likely to matter and the one
StoneDesk cannot teach you.

## 2. The skeleton, in order

Confirmed identical across both generations except where noted.

```
SAIRN TECHNOLOGIES LLC
[Letterhead — company address / contact placeholder]

<APPNAME> SERVICE AGREEMENT
Effective Date: [DATE]

1. Relationship to Platform Terms
2. Subscription and Licensed <unit>        (Locations / Firms / Practices …)
3. AI-Assisted Features  [+ grounding rules, + third-party data disclaimers]
4. <PROFESSIONAL-LIABILITY FIREWALL>       (regulated-trade apps only)
5. <Domain> Data / Data Ownership
6. Service Availability
7. Payment Terms
8. Limitation of Liability
9. Governing Law

Signature block
Standing disclaimer
Plain-Language Summary
```

**Plain-Language Summary position moved between generations** — StoneDesk puts
it immediately after the Effective Date, SAIRNlaw puts it last, after the
disclaimer. Follow SAIRNlaw. Flagging rather than silently picking, because it
is a real inconsistency in the source material.

## 3. Verbatim boilerplate — copy exactly, do not paraphrase

**§1 opener** (substitute app name and the one-line app descriptor):

> This <App> Service Agreement ("Agreement") supplements the SAIRN Platform
> Terms of Service, Data Processing Addendum, and Acceptable Use Policy
> (together, the "Platform Terms"), which apply in full to your use of <App>.
> This Agreement adds terms specific to <App>, SAIRN's <one-line descriptor>
> application. In the event of a direct conflict, this Agreement controls for
> <App>-specific matters.

**§6 Service Availability** — identical in both, substitute the app name:

> SAIRN uses commercially reasonable efforts to keep <App> available. Standard
> pricing tiers do not include a guaranteed uptime SLA. Any SLA commitment must
> be set out in a separate written addendum.

**§7 Payment Terms** — identical in both:

> Subscription fees are billed monthly via credit card auto-billing. You may
> cancel at any time; cancellation takes effect at the end of the current
> billing period, with 30 days' notice requested where practical, per the
> Platform Terms.

**§8 Limitation of Liability** — identical, substitute the app name:

> SAIRN's total liability arising out of or related to this Agreement is
> limited to the fees you paid SAIRN for <App> in the three (3) months
> preceding the event giving rise to the claim, consistent with the Platform
> Terms.

**§9 Governing Law** — identical:

> This Agreement is governed by the laws of the State of Ohio, consistent with
> the Platform Terms.

**Signature block** — note the per-app agreements say *Company/Entity Name*
where the master documents say *Business Name*:

```
Signature
By signing below, the parties agree to be bound by this Agreement.
Customer Signature: _______________________________     Date: ____________
Printed Name: _______________________________
Company/Entity Name: _______________________________
For SAIRN Tech LLC:  _______________________________     Date: ____________
Michael L. Dibert, Founder & CEO
```

**Standing disclaimer** — identical verbatim in all six documents, always last
before (or after) the summary. Never reword:

> This document was prepared as a template by SAIRN Tech LLC. It is not
> legal advice. SAIRN Tech LLC recommends having any binding agreement
> reviewed by a licensed attorney in your jurisdiction before execution.

## 4. Cross-reference discipline — cite, never restate

The master ToS points *forward* to each satellite once, by full name plus
acronym. Each satellite points *back* with "supplements the SAIRN Platform
Terms of Service" plus an explicit precedence clause. The per-app agreement
collapses all three into **"Platform Terms"** in §1 and thereafter cites that
short form.

**Do not restate a master term in an app agreement.** The real documents cite
instead, and the phrasing is consistent — reuse it:

- `"…processes this data to provide the service per the DPA."`
- `"…with 30 days' notice requested where practical, per the Platform Terms."`
- `"…consistent with the Platform Terms."`

A restated term is a term that will silently diverge the first time the master
is amended. That is the same second-copy-with-nothing-forcing-them-to-match
failure `sairn-guardian-v2`'s *Eliminate Duplication at the Source* section
describes, applied to contracts, where the consequence is a contradiction
between two executed documents rather than a bug.

## 5. Write §3 and §5 from the CODE, not from memory

The agreement makes representations about what the product does. Verify each
one before writing it.

1. Read `api/_resources/<app>.js` for the real resource list.
2. Read the handler branches in `api/sd-data.js` for what each actually does.
3. Read the app's scope spec in `docs/superpowers/specs/` for closed decisions
   and deliberate exclusions.

**SAIRNlaw §3 is the model for how specific this should be.** It does not say
"AI-assisted legal research." It names the citation-grounding rule, names
CourtListener as a third-party database operated by the Free Law Project, and
states plainly that SAIRN does not verify its completeness or currency. That
level of specificity is the convention.

**Describe the product's real boundaries, not a generic version of it.** A
representation that overstates capability is a misrepresentation even when it
sounds harmless — e.g. describing SAIRNroofing as "roof measurement software"
when it deliberately produces a quantities schedule and no geometric model,
for a documented patent reason.

## 6. Before drafting: three gaps the app agreement CANNOT close

Check each. Each is closed by amending a *master* document or by executing a
*separate instrument* — writing them into the app agreement does not work and
creates false comfort.

**6.1 DPA §9 names only SAIRNcare and SAIRNvet.** The HIPAA Addendum Trigger,
and the health-data category in DPA §3, are hardcoded to those two apps. Any
new health-adjacent app (SAIRNdental, SAIRNsenior) is **outside the master
DPA's health framework** until the DPA itself is amended. An app agreement
cannot add itself to a section of another document.

**6.2 A BAA is a separate instrument, and there are TWO of them.** DPA §9:

> Before onboarding a HIPAA-covered-entity workflow into SAIRNcare or SAIRNvet,
> Customer and SAIRN must execute a separate Business Associate Agreement
> (BAA). **SAIRN must also have an executed BAA with Anthropic covering any PHI
> processed through AI features before offering these Apps to covered
> entities.**

The upstream one is the easily-missed one. Any app that sends customer data to
`api/claude` and could carry PHI needs a SAIRN↔Anthropic BAA **before it is
offered to a covered entity at all** — that is not a customer-signature
question and no per-app agreement can satisfy it. "HIPAA-trigger language" in
a service agreement is not a BAA.

**6.3 The DPA promises deletion the product may not be able to perform.**
DPA §6 commits to deleting or returning Customer Data on request. Platform-wide,
`service_role` holds **no DELETE** on almost every app table — deliberately, and
correctly, for evidence and audit integrity. Verify per app:

```bash
grep -h "grant .* to service_role" sql/<app>_*.sql
```

Where the grant is `select, insert, update`, deletion requires direct database
work by the owner and cannot be self-served. Either the DPA needs qualifying
language or an operational runbook has to exist. Do not paper over it in the
app agreement.

## 7. Where the documents live — and the risk that creates

**All six are in `C:\Users\marsh\Downloads\` only.** Not in Google Drive
(searched by title, full text, and recent files on 2026-08-26 — Drive holds
only two LLC Operating Agreement drafts). Not tracked in any SAIRN clone; git
history has never contained a `.docx`.

**This is a single-point-of-failure for executed legal instruments living in a
Downloads folder.** Flagged, not fixed — where the canonical legal store should
be is Michael's decision, not something a drafting session should quietly
change. But a session that cannot find these documents will conclude they do
not exist and draft from scratch, which is exactly what nearly happened on
2026-08-26.

## 8. Checklist

- [ ] Drafted against the **Aug 17** generation, not StoneDesk.
- [ ] Professional-liability firewall section present, if the trade is licensed.
- [ ] §1, §6, §7, §8, §9, signature block and disclaimer copied **verbatim**.
- [ ] Every master term **cited**, never restated.
- [ ] §3 and §5 written from the resource registry and handlers, not memory.
- [ ] No representation overstates what the code does.
- [ ] Master-document gaps (§6.1–6.3) checked and reported **separately**, not
      absorbed into the draft.
- [ ] Plain-Language Summary written, last, in the customer's own vocabulary.
- [ ] Marked template-only, attorney review required, disclaimer intact.
