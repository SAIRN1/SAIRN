# SAIRNlaw court e-filing — Ohio-first scope

**Recorded 2026-08-23.** Every claim below was checked against a primary
source before any code was written. Sources are listed at the bottom with the
exact rule numbers, not paraphrased.

---

## 1. The finding that determines the scope

**There is no way to transmit a filing into an Ohio court from this
application, and there will not be one that a coding session can build.**

Three separate facts, each verified:

1. **Ohio has no statewide trial-court e-filing system.** E-filing is adopted
   county by county under **Ohio Civ.R. 5(E)**, which permits a court to
   provide for electronic filing *by local rule*, and **Ohio Sup.R. 27**,
   which requires any local rule involving information technology to be
   submitted to the Supreme Court's technology standards committee for
   approval. There is no single system, no single rule set, and no single
   endpoint.

2. **Counties run different vendors.** Confirmed in use across Ohio counties:
   Tyler Technologies (Odyssey / Enterprise Justice — Lucas County), Henschen
   (`efile.henschen.com` — Fayette, Butler area courts), and county-built
   systems (Franklin County's own e-Filing System, live since 2011). A client
   that "files in Ohio" would need a separate integration per county.

3. **The vendor route is a contract, not an API key.** Tyler's Odyssey File &
   Serve exposes filing through the **OASIS LegalXML Electronic Court Filing
   (ECF) 4.01** standard, and integration is via becoming a certified
   **Electronic Filing Service Provider (EFSP)** — a partner relationship
   arranged through Tyler (`efminfo@tylertech.com`), per court, per
   jurisdiction. ECF 4.01 is a real open standard and the schemas are public;
   the *authorisation to submit* is not.

   Even the **Supreme Court of Ohio**, which does have a single unified
   system, offers a **web portal only** — attorneys authenticate with their
   Attorney Registration number. No API is published.

**Therefore this build does not claim to file anything.** A feature that
looked like it filed and did not would be the worst possible failure in this
app: a lawyer believing a deadline was met when nothing was transmitted.

## 2. What was built instead

**E-Filing Readiness Check** — a pre-flight validator that mechanically
inspects the actual PDF a lawyer is about to file and checks it against the
real published rules of the court they are filing in, before they upload it
to that court's own portal by hand.

This is the same discipline as the rest of the module:

- The **deadline engine** refuses to compute rather than estimate past its
  holiday-calendar coverage.
- The **citator** resolves citations against CourtListener rather than
  trusting the model.
- The **LeMAJ decomposition** requires a verbatim span checked against the
  user's own text.
- Here: **the file asserts, the code checks** — and every rule the code
  cannot mechanically verify says so explicitly rather than reporting a pass.

### The three-state result, and why not two

Every rule returns `PASS`, `FAIL`, or **`CANNOT VERIFY`**. The third state is
the important one. Margins, line spacing and "fifteen pages *exclusive of the
table of contents and the certificate of service*" cannot be determined from
PDF bytes without rendering and semantic analysis. Reporting those as passes
because nothing objected would be exactly the false-confidence failure this
app exists to avoid. They are named, with the rule that governs them, and
handed back to the filer to check by eye.

## 3. Rules encoded, with citations

### Supreme Court of Ohio

| Rule | Requirement |
|---|---|
| S.Ct.Prac.R. 3.09(B)(1)(b) | Text at least **12-point**, in Times New Roman, Cambria, Calibri, Arial Standard, or Palatino Linotype |
| S.Ct.Prac.R. 3.09(B)(1)(c) | A substantially equivalent substitute typeface is allowed if none is available, with **no more than 80 characters per line** |
| S.Ct.Prac.R. 3.09(B)(1)(d) | Italic type only for case citations and emphasis |
| S.Ct.Prac.R. 3.09(B)(2)(a) | **8½ × 11 inches**, white, 20–22 lb, single-sided |
| S.Ct.Prac.R. 3.09(B)(2)(c) | **Margins at least one inch**; left margin justified |
| S.Ct.Prac.R. 3.09(B)(3) | Double-spaced; footnotes and quotations may be single-spaced but must still be 12-point |
| S.Ct.Prac.R. 7.01(B)(1) | Memorandum in support of jurisdiction: **≤ 15 numbered pages**, exclusive of table of contents and certificate of service |
| S.Ct.Prac.R. 7.01(B)(2) | **No page limit** in a postconviction death-penalty case |
| S.Ct.Prac.R. 7.08(C) | Appellee/cross-appellant combined memorandum: **≤ 30 numbered pages**; appellant/cross-appellee: ≤ 15 |
| S.Ct.Prac.R. 16.02 / 16.03 | First and second merit briefs: **≤ 50 numbered pages** (except certain death-penalty appeals of right) |
| S.Ct.Prac.R. 16.05 | Fourth brief: **≤ 20 numbered pages** |
| S.Ct.Prac.R. 3.02 | Signature: a scanned original signature, **or** `/s "John T. Smith"` |
| e-Filing Portal | Deadline **11:59:59 p.m. local observed time in Columbus, Ohio**; anything submitted after **5:00:00 p.m.** is not reviewed by the Clerk until the next business day |
| e-Filing Portal | **Cannot be e-filed:** affidavits of disqualification, and the record of a lower court or agency |

### Franklin County Court of Common Pleas, General Division

From the **Ninth Amended Civil eFiling Administrative Order**, which states on
its face that it is adopted consistent with Ohio Sup.R. 27, Civ.R. 5(E),
Civ.R. 2 and Crim.R. 12(B).

| Section | Requirement |
|---|---|
| Size of Filing (A) | **≤ 5 MB per submission**; no combination of PDFs in one transmission may exceed **25 MB** |
| Font Style and Size (B) | **Double-spaced**, Times New Roman or Arial, **at least 12-point** |
| Signatures (C)(1) | Conformed signature `/s/(name)`, followed by name, **Supreme Court ID Number**, "Attorney for (party)", firm, address, telephone, e-mail, fax |
| Format | **PDF**, except **proposed orders**, which must be Microsoft Word 2007+ (`.docx`) and must reference the specific motions they apply to |
| Confirmation | Submissions after **11:59 p.m. Friday**, or after 11:59 p.m. on a business day before a court holiday, are **deemed filed the following business day** |
| Confirmation | This does not alter **Civ.R. 6**: a deadline falling on a Saturday, Sunday or legal holiday runs to the end of the next day that is none of those |

## 4. What this deliberately does NOT do

- **It does not file anything, or transmit anything to any court.** The panel
  says so on screen, not only here.
- It does not check margins, line spacing, or which pages are "exclusive of
  the table of contents" — it reports those as `CANNOT VERIFY` with the rule
  cited.
- It covers **two** courts. Ohio has 88 counties. Any court not listed is
  absent rather than approximated — the same rule the international coverage
  panel now follows after Canada was found advertised-but-unavailable.
- It does not tell the filer their filing is *accepted*. Only the Clerk's own
  review does that; Franklin County's order describes a real **Clerk Review**
  step that can reject a compliant-looking submission.

## 5. If e-filing transmission is ever pursued for real

It is a business step first: become a certified EFSP for the specific
county's electronic filing manager, or contract with an existing EFSP that
already is. Only then is there anything to build, and what gets built is an
ECF 4.01 / NIEM message exchange, not a REST call. Budget it as a
per-jurisdiction integration, not one feature.

---

## Sources

- Ohio Civ.R. 5(E) — filing by electronic means, permitted by local rule
- Ohio Sup.R. 27 — local rules involving information technology
- Rules of Practice of the Supreme Court of Ohio (eff. March 1, 2020) —
  S.Ct.Prac.R. 3.02, 3.09, 7.01, 7.08, 16.02, 16.03, 16.05
  https://www.supremecourt.ohio.gov/
- Supreme Court of Ohio E-Filing —
  https://www.supremecourt.ohio.gov/opinions-cases/office/e-filing/
- Franklin County Common Pleas, General Division, Ninth Amended Civil eFiling
  Administrative Order —
  https://www.fccourts.org/DocumentCenter/View/1148/Civil---Ninth-Amended-Administrative-E-Filing-Order
- OASIS LegalXML Electronic Court Filing Version 4.01 (OASIS Standard,
  7 June 2013) — https://www.oasis-open.org/standard/ecfv4-01/
- Tyler Technologies, third-party EFSP partnering —
  https://odysseyfileandservecloud.zendesk.com/hc/en-us/articles/30437719387021
