# EVV transmission groundwork — what is knowable now, from primary sources

Research pass, 2026-08-27. **No code written, no app file touched.** Groundwork
only, so that the transmission build can move quickly once two deferred
decisions land.

**Explicitly out of scope, untouched, and not researched:** the trading-partner
agreement per aggregator, and the credential-storage decision (env vars vs a
service-role-only table). Both are Michael's to decide. Authentication appears
below **descriptively only** — what each aggregator's model *is*, never where a
secret should live.

---

## 0. Three corrections to things this session previously asserted

**0.1 — "The wire formats cannot be verified from primary sources." Wrong.**

That claim shaped the earlier recommendation to defer transmission, and it does
not survive contact with the sources. Of nine distinct EVV wire formats
identified, **eight have publicly published specifications** — most of them
published by state Medicaid agencies, which are primary sources by any standard.
Complete field tables with types and lengths, real payload examples, documented
error semantics and sequencing rules are all obtainable today.

The recommendation to build readiness first still stands, but it now stands on
its real reasons — no trading-partner agreement, no credential decision, and the
readiness data model being a prerequisite either way — and **not** on "we cannot
know the format."

**0.2 — The state-to-aggregator list carried from the 2026-08-26 audit was
wrong in at least one verifiable place.**

That list came from a secondary source and was passed to this pass unchecked.
**Indiana is Sandata, not HHAeXchange** — verified against
[in.gov](https://www.in.gov/medicaid/providers/business-transactions/electronic-visit-verification/):
*"The IHCP is using Sandata as the state-sponsored system."* Georgia, Kansas,
Tennessee and Arkansas could not be confirmed as HHAeXchange-aggregator states
either way. Eight states with published HHAeXchange specs were missing from it
entirely (MN, NJ, OK, WV, FL, HI, PA, VA).

**Treat every state-to-aggregator mapping in this document as point-in-time.**
Michigan's own 2023 press release names Alabama as an HHAeXchange state; Alabama
appears on no current list and has no published spec. Even a vendor's own list
churns.

**0.3 — The HHAeXchange/Sandata acquisition date was wrong.**

Reported earlier as September 2024. It closed **2024-10-03**, per
[HHAeXchange's own press release](https://www.hhaexchange.com/press-releases/hhaexchange-acquires-sandata-technologies).

---

## 1. Method and the honesty contract

Every claim below carries one of four labels, and they are used strictly:

- **PRIMARY-VERIFIED** — fetched from a state Medicaid agency, a federal source, or the vendor's own official technical documentation, and read. URL given.
- **VENDOR-DOCUMENTED** — from vendor marketing or support pages, not a state or federal source.
- **SECONDARY** — blog, listicle, comparison, consultancy. *Nothing in this document rests on a secondary source.*
- **NOT VERIFIED** — believed but unconfirmed. Said plainly.

Same contract the readiness engine ships with. "No coverage found" and "gated"
are recorded as findings, not smoothed over.

### A provenance decision, made deliberately

Sandata's altEVV specification PDFs each carry a footer reading *"Proprietary and
Confidential Information of Sandata Technologies, LLC … Unauthorized access,
copying and replication are prohibited."* Copies are also reachable from an
unauthenticated Sandata S3 bucket.

**This document cites only the state-government-published copies** — public
records published deliberately by agencies such as NC DHHS, DC DHCF, AZ AHCCCS,
RI EOHHS, VT DVHA, IL DHS, Maine DHHS, Indiana FSSA, WI DHS, CA DHCS and CO HCPF.
The bucket is not cited and was not needed: every technical claim below is
independently available from a state source. Same conclusions, provenance that
does not depend on a vendor's misconfiguration.

### Tooling limits that shaped coverage

WebSearch budget was exhausted (200/200) before this pass began. Nearly every
general search engine now blocks or degrades automated access — DuckDuckGo,
Mojeek and Brave serve CAPTCHAs, Bing HTML returns no external result links,
Ecosia and Startpage 403 or challenge. **`medicaid.gov` and `cms.gov` return 403
to everything.** Work proceeded by direct URL fetch and a browser session.

**Consequence, stated rather than hidden:** absence of a search hit is not
evidence a document does not exist. Several states were never reached — Missouri,
Oklahoma, Vermont, Rhode Island, Utah, Alaska, California IHSS, Massachusetts,
Maine, Idaho, South Carolina, Alabama, Kansas, Nevada, New Mexico, Oregon eXPRS.
**No claim is made about any of them.**

---

## 2. The federal floor — now PRIMARY-VERIFIED, with a phrasing correction

`api/_lib/sen-evv-readiness.js` currently reports its six-element list as
unverified and discloses that on screen. **That disclosure can now be narrowed.**

The six elements are verified word for word against two independent official
hosts — [uscode.house.gov](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title42-section1396b&num=0&edition=prelim)
and [govinfo.gov](https://www.govinfo.gov/content/pkg/USCODE-2023-title42/html/USCODE-2023-title42-chap7-subchapXIX-sec1396b.htm),
which returned identical text.

> **42 U.S.C. § 1396b(l)(5)(A)** — "The term 'electronic visit verification
> system' means, with respect to personal care services or home health care
> services, a system under which visits conducted as part of such services are
> electronically verified with respect to— (i) the type of service performed;
> (ii) the individual receiving the service; (iii) the date of the service;
> (iv) the location of service delivery; (v) the individual providing the
> service; and (vi) the time the service begins and ends."

All six match the module's wording exactly.

**Citation for a code comment:** `42 U.S.C. § 1396b(l)(5)(A)(i)–(vi)` — SSA
§ 1903(l), added by Pub. L. 114-255, div. B, title XII, § 12006(a), Dec. 13, 2016.
*(The Statutes at Large page is NOT VERIFIED — govinfo's Public Law HTML truncates
before Title XII. Omit it; the citation is complete without it.)*

### The correction the module must absorb

The module says the statute *"requires six data elements to be captured."* **It
does not.** The six are the statutory **definition** of a qualifying EVV system —
things a system "electronically verifie[s]." The operative requirement, at
`§ 1396b(l)(1)`, is that a State *require the use of* such a system, scoped to
services "requiring an in-home visit by a provider." Practically the same effect,
but "data elements" is CMS/vendor vocabulary and should not be attributed to the
statute.

### Also now verified, and useful

- **Compliance dates** (`§ 1396b(l)(1)`): personal care **2020-01-01**, home health **2023-01-01**.
- **Enforcement** is an FMAP reduction, ramping 0.25 → 1 percentage point (2023+ for personal care, 2027+ for home health). CMS actively surveys for it via Form CMS-10680.
- **Good-faith exemption** (`§ 1396b(l)(4)`) is a **one-year** reprieve only, requiring both a good-faith effort *and* unavoidable system delays. Fully expired for personal care; covered only calendar 2023 for home health.
- **A permanent grandfather clause exists** at `§ 1396b(l)(3)` for states that already required EVV as of 2016-12-13 — not previously known to us.
- **There is no EVV rulemaking at all.** A full Federal Register API sweep for `"electronic visit verification"` returns 11 CMS documents, none of them a rule. All operational detail lives in sub-regulatory guidance.

### What stays disclosed

Two things, and the module's disclosure should narrow to exactly these:

1. **CMS's own EVV guidance has not been read** — `medicaid.gov` and `cms.gov` 403 to automated fetch. Since there is no rulemaking, that guidance is where operational detail lives, so this is a real residual gap.
2. **"States may add requirements on top" is an inference from statutory silence.** The statute contains no "at a minimum" language and no preemption clause. The inference is defensible and uncontradicted — but it must be written as *"the statute specifies six verification points and does not preempt additional State requirements,"* never as *"CMS states these are minimums."*

---

## 3. The architectural finding that outranks any single format

**Washington State has no EVV aggregator at all.** EVV data elements ride on the
claim into ProviderOne, the state MMIS. There is nothing to integrate *with*.

**PRIMARY-VERIFIED**, [DSHS ALTSA, EVV System Requirements v4, July 2026](https://www.dshs.wa.gov/sites/default/files/ALTSA/stakeholders/documents/EVV/EVV_Systems_Requirements_for_Home_Care_Agencies_V4.pdf):

> "the Consumer Directed Employer and Home Care Agencies must include EVV data
> elements in claim submissions to ProviderOne. The ProviderOne system aggregates
> EVV data during the claims submission process."

**Why this matters more than any format detail:** a data model that assumes
"every state has an aggregator endpoint to POST to" needs *surgery*, not
configuration, to serve Washington. Designing for submission-as-claim now costs
almost nothing; retrofitting it later means reworking the core abstraction.

The correct abstraction is therefore **"a visit becomes a submitted artifact,"**
where the artifact may be an API call, a file drop, *or a claim line* — not
"a visit is POSTed to an aggregator."

---

## 4. The nine wire formats

Eight of nine have public specifications.

| # | Format family | Transport | Payload | Public spec |
|---|---|---|---|---|
| 1 | **Sandata OpenEVV altEVV** | REST/HTTPS | JSON | Yes — many state agencies |
| 2 | **HHAeXchange Aggregator API** | REST/HTTPS + OAuth2 | JSON | Yes — vendor KB, openly |
| 3 | **HHAeXchange V5 Flat File** | SFTP | CSV, 96 columns | Yes — vendor KB |
| 4 | **HHAeXchange Texas** | HTTPS | **SOAP** | Yes — vendor KB |
| 5 | **Netsmart / Tellus** | SFTP or HTTPS | XML (API); pipe-delimited / 837P (SFTP) | Yes |
| 6 | **CareBridge** | SFTP only | Pipe-delimited CSV | Yes |
| 7 | **Texas TMHP** | SFTP | Pipe-delimited positional, ~115 fields | Yes |
| 8 | **New York eMedNY** | REST | JSON | Yes |
| 9 | **Louisiana LaSRS/SRI** | SFTP | CSV, 5-file bidirectional bridge | Yes |
| 10 | **Washington ProviderOne** | Claim (.DAT or DDE) | EVV fields embedded in the claim | Yes |
| — | **Therap** | REST | JSON (presumed) | **No — NDA-gated** |

*(Ten rows for nine families: HHAeXchange's three interfaces are one vendor but
genuinely three implementations.)*

---

## 5. Sandata — what is knowable

All **PRIMARY-VERIFIED** from state-published copies. Representative source:
[NC DHHS, OpenEVV-altEVV v7.10](https://medicaid.ncdhhs.gov/documents/providers/programs-services/evv/openevv-altevv-v7-10-final/download).

**Transport.** HTTPS REST, JSON, POST. Three endpoint families —
`/interfaces/intake/{clients|employees|visits}/rest/api/v1.1` on `api.sandata.com`
(UAT on `uat-api.sandata.com`). Unauthenticated probes return the documented 401
envelope, confirming the published spec matches the live service. SFTP exists
elsewhere in the OpenEVV family but **not** for third-party visit submission.

**Payload.** JSON array even for a single record, **case-sensitive field names**,
UTC `YYYY-MM-DDTHH:MM:SSZ`. A complete worked example is published.

**Three operational facts that would each have cost real time:**

1. **HTTP 200 does not mean accepted.** The spec is explicit: *"this status code is used for both success AND error conditions… The JSON returned must be used to determine if processing was successful."* You POST, receive a UUID, then poll `GET /status?uuid=`, and the first poll is routinely *"not ready yet. Please try again"* (RI's spec advises a 5-minute wait). Parse per-record `ErrorCode`, never the envelope `status`.
2. **A lower `SequenceID` is silently accepted as historical**, not rejected — so a late or out-of-order submission quietly fails to become current. Equal values *are* rejected. A rejected SequenceID must never be reused.
3. **Hard ordering:** employees and clients must be fully processed *before* visits. Not merely sent — processed.

**Per-state divergence is real, not cosmetic.** Ohio uses different endpoints and
renames roughly nine top-level fields (`ProviderIdentification{}` →
`BusinessEntityID`, `EmployeeOtherID` → `StaffOtherID`, `ClientOtherID` →
`PatientOtherID`, and so on). California adds `JurisdictionID`. Exception IDs,
reason codes and procedure codes are per-state and **not portable**. Field names
have also drifted between base versions (`VisitTasks` → `Tasks`).

**Design consequence:** a per-state field-mapping layer, not one canonical schema.

**Genuinely gated:** credentials; the WADL/Swagger schema (401 live); the complete
numeric error-code catalogue, which Sandata says varies by implementation.

**The real blocker is not technical.** Sandata's vendor certification portal admits
you only once a provider agency in that state has **already named you** as their
alternate EVV vendor. That is a business-development sequence, not an engineering
one, and it is a materially better-defined blocker than "trading-partner
agreement." **Flagged for Michael; not resolved here.**

---

## 6. HHAeXchange — what is knowable

All **PRIMARY-VERIFIED** from
[knowledge.hhaexchange.com/edi/](https://knowledge.hhaexchange.com/edi/Content/Documentation/EDI/EDI.htm),
which is fully public and unauthenticated. Michigan's Medicaid agency links
directly to the spec PDF. **No provenance concern here at all.**

**Three separate products, and which one you build is a state-by-state fact:**

- **REST/JSON Aggregator API** — IL, MI, MN, MS, NJ, OK, WV. OAuth 2.0 client-credentials, 30-minute token the docs tell you to reuse. Max **100 visit records per request**.
- **V5 Flat File over SFTP** — AR, FL, HI, NC, NY, PA, VA. CSV, 96 positional columns, only seven of them required. Deletes are in-band (column BA `Is Deletion`).
- **Texas — SOAP**, an entirely different interface (`SearchVisits`, `GetVisitInfoV2`, `CreateSchedule`, `DeleteVisit`). Verified mechanically: the Texas page contains 29 occurrences of "SOAP" and zero of "JSON".

**Two design constraints that are irreversible once tripped:**

> "Once the visit is confirmed manually, then EVV Clock In/Out is not allowed in
> subsequent requests. Once the EVV Clock In/Out is completed, then a change to
> an EVV Clock In/Out is not allowed in subsequent requests."

And **silent truncation**: over-length strings are cut to max length rather than
rejected. A too-long field does not error — it quietly becomes wrong data.

**131 numbered error codes are published** with element, message and remediation.
Async model: submit → transaction ID → poll `GET /visits/transactions/{id}` for
`Pending`/`Success`/`Failed`.

### The single most useful finding in this pass

**There is a public pre-integration validator at
[edi.hhaexchange.com](https://edi.hhaexchange.com)** — pick state and interface
spec, upload a file, receive pass/fail per validation. *"Data is discarded (not
stored in any HHAeXchange server)."*

**Format conformance can be proven with no credentials, no agreement, and no
customer.** That is the concrete "move fast later" lever this task was asked to
find, and it is available today.

### The acquisition consolidates nothing

Closed 2024-10-03. HHAeXchange's own FAQ: *"Sandata will operate as a standalone
business unit."* Delaware published a **Sandata-branded** spec under a 2026/06
path with zero mention of HHAeXchange; Ohio still runs Sandata; Minnesota lists
Sandata as a third-party vendor integrating *into* HHAeXchange.

| | HHAeXchange | Sandata |
|---|---|---|
| Auth | OAuth 2.0, scope `write:aggregator` | HTTP Basic + separate `Account` header |
| Casing | camelCase | PascalCase |
| Batch | 100 records | 5,000 records |

**Building to one buys nothing toward the other.** Do not plan on convergence.

---

## 7. The rest, and where to start

**Netsmart/Tellus** — SFTP or HTTPS; XML on the API path, pipe-delimited TXT or
837P EDI on SFTP. Public. **CareBridge** — SFTP only, pipe-delimited CSV. Public.
**Therap** — NDA-gated, the one genuine exception.

**Louisiana (LaSRS/SRI)** is a state contractor, not a commercial aggregator, and
LDH publishes the spec itself — including a downloadable field-layout spreadsheet.
[LDH declares it open in those exact words](https://ldh.la.gov/assets/medicaid/EVV/third-party-data-integration-process.pdf):
*"Louisiana's Electronic Visit Verification (EVV) system is defined as an 'open'
system per Centers for Medicare and Medicaid Services (CMS)."* It is a five-file
bidirectional nightly SFTP bridge, and it uniquely demands the **externally-facing
IP address** of the check-in device (`IPIN`/`IPOUT`/`IPEDIT`) — seen nowhere else
in this pass. It also has **no dual-running period**: once a provider goes live on
a third-party system, they lose the ability to enter data in the state system for
those service dates.

### Cheapest places to start, if and when the decisions land

1. **New York eMedNY** — smallest complete REST/JSON implementation, self-service API key.
2. **Louisiana** — complete public SFTP/CSV spec with a downloadable field layout.
3. **Texas TMHP** — the best spec to *learn* from regardless of whether it ships.

### Open-model states confirmed in those terms

Michigan (*"open vendor model"*), Minnesota (publishes a 38-vendor integration
list), Texas (Proprietary System Request + Operational Readiness Review), Colorado
(*"hybrid model"*), California, Wisconsin, Louisiana. **Maryland is NOT VERIFIED** —
its page is JavaScript-injected and the static HTML carries no document links.

---

## 8. What this changes, and what it does not

**Changes:** the format is no longer the unknown. Eight of nine families are
publicly specified; one aggregator offers credential-free conformance testing;
the federal floor is verified statute rather than corroborated secondary
reporting.

**Does not change:** both deferred decisions stand exactly where they were.
Nothing here resolves the trading-partner agreement or the credential-storage
question, and nothing here should be read as pressure on either. The Sandata
finding *sharpens* the first one — the gate is a named provider agency, not
paperwork — which is information for the decision, not the decision.

**Also unchanged:** readiness-first was the right call. The readiness data model
is a prerequisite for every one of the nine formats, and building it first cost
nothing that has to be undone.

### Follow-ups this pass produced

1. **Correct the readiness module's federal-floor disclosure** — move from unverified to cited (`42 U.S.C. § 1396b(l)(5)(A)(i)–(vi)`), fix the "requires six data elements" phrasing, narrow the disclosure to the two residual gaps in §2. **This is a code change to shipped behaviour and is NOT made here** — it needs Michael's go-ahead.
2. **Correct the 2026-08-26 audit's state-to-aggregator list** — Indiana at minimum is wrong.
3. **Design the submission abstraction around "artifact," not "aggregator POST"** — see §3, before any transmission code exists.
4. **Resolve Maryland**, and the ~16 states never reached.
