# Worldwide competitive-gap audit — SMALL-FLEET DOT / FMCSA COMPLIANCE

**fourth / b30, 2026-10-19.** Third in the "vertical SAIRN has not built for"
series, after childcare (b28) and outpatient behavioral health (b29, now
**PARKED** — see `PARKED-VERTICALS.md`).

**THIS IS NOT A BUILD RECOMMENDATION.** §7 says what would have to be true
first and none of it is true today. Per `sairn-decision-gate` a new vertical is
expensive to reverse and an audit is not the gate.

**Every figure names the command or the citation that produced it. Re-derive
anything you mean to quote, including out of this file.**

---

## 0. WHY THIS ONE, AND WHY IT IS NOT A THIRD COPY OF THE SAME STORY

The first two audits both landed on the same shape — a credential that expires,
a rule that varies by state, a billing basis that moves. **Picking a third
vertical with that shape would have told us nothing new**, so the test applied
here was: does this vertical fail for a *different* reason?

It does. The binding object in trucking compliance is not a per-state rule
matrix — it is **one federal regime, enforced by audit, against a per-driver
file**. That difference is the whole finding, and it cuts both ways: the
regulatory surface is far more tractable than childcare's 50-state CCDF problem
or behavioral health's compact patchwork, **and the thing being sold is a
service relationship rather than software**. §2.

**Universe re-derived at HEAD, as in b29:**

    git ls-files '*.html' | grep -E '^(sairn[a-z]+|stonedesk)\.html$'   -> 17

---

## 1. THE MARKET, AND WHERE THE SMALL CARRIER ACTUALLY SITS

Three bands, and they are not competing for the same customer:

| band | who | what they sell |
|---|---|---|
| **Applicant tracking / onboarding** | **Tenstreet** — reported at **4,200+ client carriers** and **15M+ applications processed** | a recruiting pipeline. Built for carriers with a dedicated onboarding team; the reported hurdle for a small fleet is complexity and price, not capability |
| **Done-for-you compliance** | **Foley** | a **certified third-party administrator** for the FMCSA Clearinghouse — drug and alcohol programme, background screening, MVR monitoring, digital driver files, audit support. **A service with software attached, not the reverse** |
| **Training** | **Luma Brighter Learning** and others | ELDT theory coursework, delivered as modules |

**THE SEGMENT THAT IS UNDERSERVED IS NAMED EXPLICITLY IN THE BUYER GUIDANCE:**
fleets of **1–20 trucks**, which need compliance kept **without an in-house
compliance officer**, at a reported **$30–$150/month**. That is the price band
SAIRN's apps already live in, and it is a long way below what the onboarding
platforms are built to serve.

**AND THAT IS ALSO THE PROBLEM, STATED HERE RATHER THAN IN A FOOTNOTE.** Foley
is the shape of the incumbent that matters: a carrier does not mainly want a
screen that *tracks* a drug-testing programme, it wants somebody to *run* one
and to stand behind it at an audit. **A software-only entrant does not displace
a third-party administrator; it sells to a carrier who has one.** SAIRN has
never sold a service relationship, and nothing in the platform administers
anything on a customer's behalf.

---

## 2. THE REGULATORY SURFACE — ONE FEDERAL REGIME, AND IT IS MOVING

**Two primary citations, pulled from the Federal Register API rather than from
a vendor summary** (the method b29 established; `WebFetch` is still blocked by
a redirect and `tools/sairn_http.py` still works):

| | rule | citation | the date that bites |
|---|---|---|---|
| **R1** | *Restoring Integrity to the Issuance of Non-Domiciled Commercial Driver's Licenses (CDL)* — **interim final rule**, FMCSA | **90 FR 46509**, doc `2025-18869`, published **and effective 2025-09-29** | immediate: sharply limits SDLA authority to issue or renew non-domiciled CLPs and CDLs |
| **R2** | the same, **FINAL RULE**, reaffirming the IFR with minor changes | **91 FR 7044**, doc `2026-02965`, published 2026-02-13, **effective 2026-03-16** | already in force |

**R1/R2 are a WORKFORCE event wearing a licensing rule's clothes.** A carrier
does not get a notice saying "your driver is now ineligible"; it finds out when
a credential fails to renew. The compliance object a product would have to hold
is therefore **eligibility-at-a-date per driver**, re-evaluated on a rule change
— which is the same `effective_from` shape `sairndental` ships for CDT editions
and the one primitive this platform has actually proved.

**Reported, NOT independently verified, and listed separately for that reason**
— every item below comes from secondary compliance-industry sources and **none
of it was confirmed against the CFR or the Federal Register**:

* an **annual Clearinghouse query** for every CDL driver, with a stated
  **January 5** deadline for the prior calendar year;
* **24-hour** employer reporting of positive tests, refusals and SAP
  return-to-duty completions;
* **Clearinghouse-II**: a state must **downgrade a prohibited driver's CDL
  within 60 days** of notification, mandatory for all states since 2024-11-18;
* **English-language-proficiency violations now placing a driver
  out-of-service**;
* civil penalties around **$16,000 per Clearinghouse occurrence**;
* **~12,000 compliance reviews planned for Q1–Q2 2026, a reported 40%
  increase**, with small carriers not exempt.

**If any single one of those is quoted to a customer it must be re-derived
first.** The 40% figure in particular is a vendor-marketing number in every
source seen, and it is the one most likely to be repeated because it is the
most alarming.

---

## 3. PLATFORM FIT — MEASURED, AND IT IS THE WEAKEST OF THE THREE AUDITS

    APPS=$(git ls-files '*.html' | grep -E '^(sairn[a-z]+|stonedesk)\.html$')   # N=17
    for each pattern: grep -ciE "<pattern>" "$f"

| primitive | pattern | present in |
|---|---|---|
| credential expiry **field** | `expires_on\|expiry_date\|expires_at\|expiration_date` | **6 of 17** |
| vehicle identity | `\bvin\b\|odometer\|license_plate` | **2 of 17** (sairnfreedom, sairnlegacy) |
| **CDL / USDOT** | `\bcdl\b\|dot_number\|usdot` | **0 of 17** |
| **hours of service / ELD** | `hours_of_service\|duty_status\|\beld\b` | **0 of 17** |
| **screening (MVR, drug test, Clearinghouse)** | `\bmvr\b\|drug_test\|background_check\|clearinghouse` | **0 of 17** |
| tamper-evident log | `audit_log\|audit_trail\|hash_chain` | **1 of 17** (sairnvet) |

**ONE FALSE POSITIVE WAS FOUND AND REMOVED RATHER THAN REPORTED.** The
screening row first came back **1 of 17** on `sairncode`. Reading the matches
rather than the count: every hit is *"your own **clearinghouse** account"* /
*"Stedi clearinghouse"* — a **healthcare claims clearinghouse**, a homograph of
the FMCSA Drug & Alcohol Clearinghouse and completely unrelated. The row is
**0 of 17**.

**A second artefact, disclosed because it nearly shipped:** loose patterns for
"vehicle/fleet" and "hours of service" both returned **17 of 17**, which is what
a measurement looks like when it is wrong. `\bhos\b` without the boundary was
matching *"those"* and *"hostile"*. Both rows were re-measured with boundaries
before anything was written down. Convention 35 — a predicate has a span as
well as a pattern.

**Read plainly: this vertical shares almost nothing with what SAIRN has
built.** Childcare shared a credential-expiry primitive; behavioral health
shared the code-edition-against-date-of-service engine. **This one shares a
file-upload box.**

---

## 4. WHAT WOULD HAVE TO BE BUILT THAT HAS NEVER BEEN BUILT

1. **A driver qualification file as a first-class object** — a defined document
   set per driver, each with its own expiry and its own regulatory citation,
   evaluated **as of an audit date** rather than as of today.
2. **A Clearinghouse integration**, which is a registered relationship with a
   federal system, not an API key. Foley is a *certified third-party
   administrator*; that certification is the product.
3. **MVR monitoring**, which is a per-state data-purchase relationship.
4. **Drug-and-alcohol programme administration** — random-selection pools, SAP
   workflow, 24-hour reporting. This is an operational service with legal
   exposure, and it is the part a carrier is actually buying.
5. **Criticality.** A driver qualification file is the evidence in a federal
   audit and an eligibility determination can put a driver out of work. On
   `docs/CRITICALITY-TIERS.md` terms this is **Tier A on at least two
   resources**, and **that tier is NOT assessed here** — naming it is not
   assessing it.

---

## 5. WHAT THIS AUDIT DID NOT DO

* **No competitor account was provisioned and no product was driven.** Every
  claim in §1 rests on secondary sources, several of them **vendor-authored
  buyer guides for competing products** — a worse source class than b29's,
  which at least had analyst technographics.
* **No market share figures exist in anything seen.** Tenstreet's "4,200+
  carriers" and "15M+ applications" are vendor-published counts against
  different universes and are **NOT combined into a share**. There are roughly
  half a million active US motor carriers; **no denominator from a source worth
  citing was found**, so no percentage appears in this document.
* **No carrier, safety director or third-party administrator was interviewed.**
* **The six reported regulatory items in §2 were NOT verified against primary
  sources.** Only R1 and R2 were.
* **No pricing was verified.** The $30–$150 band is one guide's assertion.

---

## 6. THE HONEST COMPARISON ACROSS THE THREE AUDITS

| | childcare (b28) | behavioral health (b29) | trucking (this) |
|---|---|---|---|
| regulatory surface | 50-state CCDF, flipped twice in 26 months | compacts + per-payer, patchwork | **one federal regime** — the most tractable of the three |
| platform fit | credential expiry shared | code-edition engine shared | **almost nothing shared** |
| what the buyer buys | software | software | **a service relationship** |
| the blocker | no owner for a 50-state matrix | no owner for a 50-state matrix | **SAIRN does not sell services** |
| status | audited, **not decided** | **PARKED** 2026-10-19 | audited, **recommended against**, §7 |

**THE PATTERN ACROSS THREE AUDITS IS NOT ABOUT ANY MARKET.** Two of the three
failed on *the same missing role* — nobody owns a standing regulatory matrix.
The third fails on a *different* missing capability — nobody sells or
administers a service. **A fourth audit of a fourth vertical will not change
either, and that is the finding worth carrying forward.** §7.

---

## 7. WHAT WOULD HAVE TO BE TRUE — AND A RECOMMENDATION ABOUT THE SERIES

**For this vertical specifically**, all four, not any one:

1. SAIRN decides it is willing to sell an **administered service**, with the
   staffing and liability that implies. This is a company decision, not a
   product one.
2. A certified **third-party-administrator** path is costed, or a partnership
   with an existing one is real.
3. One real small-carrier safety director is interviewed and confirms the
   file-keeping pain is worth paying for **separately from** the TPA they
   already use.
4. The six reported items in §2 are verified against primary sources.

**AND A RECOMMENDATION ABOUT THE SERIES ITSELF, which is the more useful
output of this batch:** three audits have now cost real session time and
produced three non-recommendations, each blocked by a *standing company
capability* rather than by anything about the market. **Running a fourth before
either blocker is resolved would be measuring the same wall from a new angle.**
The cheaper next move is to settle the two questions the audits keep surfacing
— *who owns a regulatory matrix* and *will SAIRN ever sell a service* — and
only then ask which vertical fits the answers.

---

*Sources (secondary, §1 and the reported half of §2): foleyservices.com,
embarksafety.com, heavyvehicleinspection.com, getfileflo.com, numeo.ai,
datatruck.io, tenstreet.com, cbinsights.com, lumabrighterlearning.com,
ccjdigital.com, synergysafetygroup.com, idispatchhub.com, inoutlabs.com.
Primary (R1, R2): federalregister.gov API, documents `2025-18869` and
`2026-02965`.*
