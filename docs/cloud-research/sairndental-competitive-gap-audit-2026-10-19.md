# Worldwide competitive-gap audit — SAIRNDENTAL

**fourth / b36, 2026-10-19.**

**THE BATCH ASKED FOR THE FIRST OF sairnlaw, sairncode, sairndesign, sairnbiz
WITH NO CURRENT AUDIT. ALL FOUR HAVE ONE.** Measured before choosing:

| vertical | audits on file | newest |
|---|---|---|
| sairnlaw | 2 | 2026-09-26 |
| sairncode | 2 | 2026-09-26 |
| sairnbiz | 1 | 2026-09-26 |
| sairndesign | 1 | **2026-10-05** |

None is older than four weeks, so none is stale. **Three apps have ZERO
audits** — `sairndental`, `sairnmechanical`, `sairnroofing`. SAIRNdental was
taken because it has no audit at all and was already open for this batch's
accessibility pass, so the code recon is first-hand rather than inherited.

**THIS IS NOT A BUILD RECOMMENDATION.** §6 says what would have to be true.

**THE HEADLINE IS UNUSUAL FOR THIS SERIES AND IT IS WHY THIS ONE WAS WORTH
RUNNING:** the previous four audits each found a market gap SAIRN had no
capability to fill. **This one is the reverse.** The gap the 2026 dental market
most loudly names is the one SAIRNdental is already closest to filling — and
the single missing piece is **a commercial clearinghouse relationship, which is
a company decision, not a build.** §5.

---

## 1. THE MARKET — AND WHY THE SHARE FIGURES ARE REPORTED AS A RANGE

**There is no authoritative public market-share dataset for dental practice
management software.** One of the sources consulted says so outright, which is
more useful than the numbers around it: *"there is no reliable public data on
dental practice management software market share from the ADA, Capterra, or
market research firms."* Every figure below is therefore a **vendor-adjacent
estimate**, reported as a range and never reconciled into a single number.

| vendor | reported revenue share | reported installed base |
|---|---|---|
| Henry Schein One (Dentrix / Dentrix Ascend) | **18–22%** | **35,000+** practices on Dentrix; **48,000+** across Dentrix + Ascend (March 2026) |
| Patterson (Eaglesoft) | **12–15%** | not separately reported |
| Open Dental | **4–6%** | not separately reported |

**Read that honestly: the three named incumbents are a minority of a
fragmented market by revenue share, and the leader's own installed base is the
only hard-ish number available.** Curve Dental and Denticon are consistently
named as the cloud-native challengers and **no practice count was found for
either** — stated because an absent figure is not a small one.

---

## 2. THE REGULATORY SURFACE — SETTLED, FEDERAL, AND ALREADY BUILT FOR

**The live obligation is the No Surprises Act Good Faith Estimate**, and it
applies to dentistry. The requirement, as reported across several compliance
sources:

* A written GFE for **uninsured and self-pay** patients. **Self-pay is not a
  synonym for uninsured** — an *insured* patient who chooses not to submit a
  claim triggers the same obligation.
* **The clock runs from SCHEDULING, not from the visit:** 1 business day when
  the appointment is ≥3 business days out; 3 business days when it is ≥10 days
  out or simply requested.
* The estimate must be **itemised** and carry service and diagnosis codes plus
  each provider's **name, NPI and TIN**.
* **Retained for at least 6 years** and produced on request.
* **Penalties up to $10,000 per violation**, CMS-investigated.

**This is the most buildable regulatory shape this series has encountered** —
federal, single-regime, settled, with a specified record. It is the opposite of
childcare's 50-state ratio matrix or pest control's per-state applicator
licence table, **both of which failed on having no matrix owner.**

**And SAIRNdental already has `dnt_gfe` as a registered resource with its own
panel.** This audit did not have to propose it.

---

## 3. PLATFORM FIT — MEASURED FROM THE REGISTRY, NOT ESTIMATED

    node -e "console.log(require('./api/_resources/sairndental.js').resources.join(' '))"

**25 registered resources**, and the ones that matter here:

| the market's named pain | SAIRNdental resource | state |
|---|---|---|
| Good Faith Estimates | `dnt_gfe` | **built**, own panel |
| denials & appeals | `dnt_denial` | **built**, own panel |
| provider credentialing / licence expiry | `dnt_credentials`, `dnt_cred_rules` | **built**, own panel, Tier A |
| coverage / benefit rules | `dnt_coverage_rules` | **built** |
| A/R and recall | `dnt_ar`, `dnt_recall_outreach` | **built** |
| treatment plans | `dnt_txplans` | **built** |
| **real-time eligibility verification** | **— none —** | **ABSENT** |

**`icap` (Insurance Capture) is a PHOTO capture panel, not an eligibility
check.** It records what the card says; it does not ask the payer anything.
That distinction is the whole of §5 and it is stated here so nobody reads the
panel list and concludes the capability exists.

---

## 4. WHERE THE MARKET SAYS THE GAP IS — AND IT IS AN INTEGRATION GAP

The 2026 buyer literature is unusually consistent, and it does **not** ask for
another PMS. It asks for three things to stop living in three tools:

> *"eligibility verification sits upstream, while denial management, appeals,
> credentialing and A/R recovery sit downstream"* — practices are described as
> struggling with workflows that do not connect these functions.

And the quantified claim, repeated across vendor sources and therefore reported
as vendor-sourced rather than independent:

* manual verification **10–15 minutes per patient** vs **under 60 seconds**
  automated;
* denial rates **8–12% manual** vs **3–6% automated**;
* manual eligibility **~$10.60 per transaction** vs **~$0.30** electronic.

**SAIRNdental already holds three of the four pieces in one app.** Denials,
credentialing and coverage rules are not separate purchases here — they are
registered resources in a single codebase with a single auth model. That is
precisely the integration the buyer guides describe practices failing to get.

**This is the first time in this series that the platform's existing shape
matches the market's named complaint.**

---

## 5. THE ONE MISSING PIECE IS A CONTRACT, NOT A FEATURE — AND THAT IS THE BLOCKER

Real-time eligibility is an **X12 270/271 EDI** transaction. A practice cannot
ask a payer directly at scale; it goes through a **clearinghouse**. The named
dental clearinghouses are **DentalXChange, Vyne Dental, Change Healthcare,
Tesia, NEA, QSI and NextGen**; DentalXChange is reported as connecting **600+
dental payers** with direct EDI links to the **top 50 carriers by claim
volume**. Vyne publishes eligibility APIs (ClearCoverage, Onederful, Standard).

**Reported integration economics**, vendor-sourced and unverified:

* third-party integration **$40K–60K** up front, **$20K–40K/year** recurring;
* per-transaction **$0.15–$0.51** depending on vendor and whether it is an
  eligibility request or a claim;
* contract terms vary from **month-to-month with 60-day termination** to
  30-day pilots.

**THE BLOCKER IS A COMPANY DECISION AND IT IS NAMED AS ONE.** To ship
eligibility, SAIRN must **enter a commercial relationship with a clearinghouse**
— sign a contract, carry a recurring cost, and accept per-transaction billing
that scales with customer usage. **No amount of building substitutes for it.**

**This is the same CLASS of blocker as trucking's** *"SAIRN has never sold an
administered service"* — a standing company capability, not a product gap. It
is **narrower**: a vendor contract and a line item, not a staffed service
with liability. But it is the same kind of decision and it belongs to Michael.

**What is NOT blocked:** everything downstream of eligibility is already built.
If the clearinghouse question is answered yes, the integration is one
server-side module against a documented EDI API — the shape
`api/_lib/mech-credentials.js` and `api/_lib/roofing-crew-capacity.js` already
establish on this platform.

---

## 6. WHAT WOULD HAVE TO BE TRUE

1. **SAIRN decides whether it will carry a clearinghouse contract and a
   per-transaction cost that scales with usage.** §5. Michael's, and nothing
   proceeds without it.
2. **One real practice administrator is interviewed** and confirms that
   eligibility-plus-denials-plus-credentialing in one tool is worth switching
   PMS for. **Nothing in the public material establishes switching intent** —
   it establishes complaint, which is not the same thing, and a PMS migration
   is among the most disruptive purchases a practice makes.
3. **A driven trial on Dentrix Ascend, Curve or Denticon** to replace
   vendor-authored claims about what they do not do with observed behaviour.
   **None was provisioned for this audit.**
4. **The GFE implementation is checked against the real rule**, not against
   this document: itemised, service **and** diagnosis codes, provider name +
   NPI + TIN, the scheduling-clock timing, and 6-year retention. `dnt_gfe`
   exists; **whether it satisfies all five was not verified here.**
5. **A criticality-tier pass on `dnt_gfe` and `dnt_denial`.** A GFE is the
   document a $10,000-per-violation penalty attaches to. Not assessed here.

---

## 7. WHAT THIS AUDIT DID NOT DO

* **No competitor account was provisioned and no product was driven.** Every
  claim in §1 and §4 rests on secondary sources, **many of them published by
  vendors selling into this exact gap** — including several whose own product
  is an eligibility tool. That conflict is named rather than averaged away.
* **No dentist, office manager or billing coordinator was interviewed.**
* **No primary regulation was read.** The GFE requirements in §2 are reported
  from compliance-firm summaries, not from the Federal Register. **This is
  weaker sourcing than the pest-control and trucking audits, which pulled
  primary citations through the Federal Register API**, and the difference is
  stated rather than hidden.
* **The market-share figures are not reconciled** and one source explicitly
  says no authoritative dataset exists.
* **SAIRNdental's own GFE, denials and credentialing panels were NOT audited
  for correctness** — their existence was read from the registry. Existing and
  being right are different claims.

---

## 8. WHERE THIS LEAVES THE SERIES

Five audits now. The blockers, in order of appearance:

| vertical | blocker | kind |
|---|---|---|
| childcare | no owner for a 50-state matrix | company |
| behavioral health | no owner for a 50-state matrix | company |
| trucking | never sold an administered service | company |
| pest control | no routing primitive **+ market already served** | **build** + market |
| **dental** | **no clearinghouse relationship** | **company** |

**Four of five blockers are company decisions.** The routing primitive was the
one buildable item and b34/b35 built it — four consumers wired, still awaiting
one handler branch.

**Dental is the strongest candidate the series has produced**, because the
regulatory surface is federal and settled, the integration the market asks for
is three-quarters built, and the blocker is a **vendor contract** rather than a
standing staffed capability. **It is still a no until §6.1 is answered.**

---

*Sources (all secondary): medixdental.com (which states no authoritative
market-share dataset exists), pabau.com, siotek.net, ariadental.ai,
elementera.com, aimadefor.com, marketresearchfuture.com,
futuremarketinsights.com; dentalcompliance.com, ddslawyers.com,
mdclarity.com, lsimedbilling.com, medprecisionbilling.com, cartgaze.com,
314e.com, americanbillingassociation.com; needletailai.com, avized.com,
vynedental.com, zuub.com, opendental.com, withassured.com, getaron.ai,
dentalrobot.ai, teero.com, api.dental, staffingly.com, grandviewresearch.com.
**No primary regulatory citation was pulled for this audit** — see §7.*
