# Narrow verification pass — results

2026-08-28. **Research and documentation only.** No app behaviour changed by this
document; one code correction it produced is committed alongside and described in
§6.

This closes the follow-up row created on 2026-08-26, which logged five items that
a prior pass could not verify because `cms.gov`, `dol.gov`, `federalregister.gov`,
USPTO and Google Patents all refused automated fetch. **Four of five are now
resolved from primary sources.** The fifth (state-by-state variation) was not
attempted and stays open.

---

## 0. The finding that changes how we should read our own notes

**The blocked-host claim was wrong, and it was wrong in a way that hid a
different problem.**

Tested directly today rather than inferred from a lane's report — two of my own
research lanes contradicted each other on this, so I checked:

| Host | Last night | Today |
|---|---|---|
| `cms.gov` | recorded 403 | **200** |
| `medicaid.gov` root | recorded 403 | **200** |
| `medicaid.gov` EVV guidance path | recorded 403 | **404** |

So `cms.gov` is reachable and the 403 was transient. And `medicaid.gov` is
reachable too — the EVV guidance failure is a **404 on a specific path**, meaning
the page moved or was retired, not that a bot wall exists.

That distinction matters more than it looks. "Blocked" implies wait and retry.
**"Moved" means find the new URL** — a different action, and one nobody would
take while the note says 403. A stale limitation in our own documentation
suppressed the correct next step. It also means the residual-gap wording shipped
in `api/_lib/sen-evv-readiness.js` had the right conclusion for the wrong reason;
see §6.

---

## 1. Federal EVV floor — VERIFIED (carried from 2026-08-27, unchanged)

Already closed in the transmission-groundwork pass and repeated here only so this
document stands alone: the six EVV elements are verified word for word against
**42 U.S.C. § 1396b(l)(5)(A)(i)–(vi)**, and they are the statutory *definition* of
a qualifying EVV system, not a required-field list.

---

## 2. CMS Access Rule "80/20" — IN FORCE, with a pending rescission vehicle

**PRIMARY-VERIFIED.** CMS, *Ensuring Access to Medicaid Services*, final rule,
**89 FR 40542** (2024-05-10), FR doc **2024-08363**, RIN 0938-AU68, docket
CMS-2442-F, **effective 2024-07-09**. Technical correction at 89 FR 53501
(2024-06-27) — editorial only, no substantive change.

### Three corrections to how we had it

**The section is `42 CFR 441.302(k)(3)(i)`.** Our note guessed at 441.302 /
441.311 / 447.203. The first two are right; **447.203 is not** — this rule did
amend it, but for fee-for-service payment-rate transparency, a different subject.
Do not cite 447.203 for the 80/20.

**It is a provider-level test, not a state aggregate:**

> "the State must ensure that **each provider** spends 80 percent of total
> payments the provider receives for services it furnishes … on total
> compensation for direct care workers who furnish those services."

**Habilitation is not subject to the 80% floor.** The floor covers homemaker,
home health aide and personal care only. Habilitation appears solely in the
§ 441.311(e)(2)(i) *reporting* requirement.

Also: the denominator is payments **net of "excluded costs"**, defined
exhaustively at (k)(1)(iii) as required-training, direct-care-worker travel, and
PPE costs.

### Dates — "July 2030" is right but is computed, not quoted

§ 441.302(k)(8) says compliance begins **"6 years after July 9, 2024."** The rule
never prints "2030" — a full-text search of the 2.3 MB document returns zero
occurrences. State it as computed. Reporting begins **4 years after** (2028-07-09,
§ 441.311(f)(2)), with a readiness report one year earlier (2027-07-09).

### Exemptions — more than we listed

Small-provider percentage (k)(4) and hardship (k)(5), both as we had them — **plus
two we omitted**: an **IHS/Tribal exemption** (k)(7), and a carve-out for
self-directed models where **the beneficiary sets the worker's rate** (k)(2)(ii).
Both flexibilities carry strings: annual reporting plus a CMS-approved
improvement plan, waivable only if applied to **fewer than 10 percent** of
providers (k)(6)(iii)).

### Status, and the caveat our notes lacked

**In force and unamended** as of the eCFR's current Title 42 issue date
(2026-08-26). No subsequent rulemaking against Part 441, 447 or 438.72; no
statutory change (P.L. 119-21 does not contain the phrase "direct care worker");
no litigation found.

**But:** CMS proposed rule **CMS-2450 / RIN 0938-AV70** has been **pending OIRA
review since 2026-05-12**, and its Unified Agenda Statement of Need expressly
contemplates *"rescinding or revising provisions finalized in"* the Ensuring
Access final rule. **Whether the 80/20 is among them is NOT VERIFIED** and will
only be knowable when the NPRM publishes.

---

## 3. FLSA companionship exemption — CURRENT LAW VERIFIED, RESCISSION PENDING

**PRIMARY-VERIFIED** from the eCFR versioner API (Title 29 current as of
2026-08-26).

**§ 552.109(a)** is the operative provision and it is unambiguous:

> "Third party employers of employees engaged in companionship services within
> the meaning of § 552.6 **may not avail themselves of the minimum wage and
> overtime exemption** provided by section 13(a)(15) of the Act, **even if the
> employee is jointly employed** by the individual or member of the family or
> household using the services."

§ 552.109(c) does the same for **live-in** workers and the overtime exemption. So
**today**: an agency-employed caregiver, live-in included, gets minimum wage and
overtime at 1.5× over 40. The agency cannot claim either exemption, nor claim it
as a joint employer.

Litigation confirmed: vacated in part at the district court, then **reversed and
the rule upheld** — *Home Care Ass'n of America v. Weil*, **799 F.3d 1084 (D.C.
Cir. 2015)**, mandate 2015-10-13, DOL enforcing from 2015-11-12.

### The status our notes flagged as unknown

**DOL has a pending rulemaking to rescind the 2013 rule in its entirety.**
NPRM at **90 FR 28976** (2025-07-02), RIN **1235-AA51**, proposing to *"return to
the 1975 regulations."* It sits at **Final Rule Stage** with a projected
**November 2026** publication. Even the narrower alternative under consideration
would remove exactly § 552.109 and § 552.6(b).

Nothing has changed in the CFR yet — an FR sweep on the Part 552 index returns 16
documents, newest being that NPRM.

**Consequence for SAIRNsenior's payroll logic:** current law is safe to encode
and **must not be hard-coded as permanent**. This wants a dated, configurable
rule, with RIN 1235-AA51 re-checked before any release after October 2026.

**Not covered:** state domestic-worker overtime rules, which would survive a
federal rescission. Still open.

---

## 4. PDGM and OASIS — three corrections, one of them scope-defining

### OASIS-E1 is stale. The current instrument is **OASIS-E2**, effective 2026-04-01

**PRIMARY-VERIFIED** from CMS's own OASIS Data Sets page and **90 FR 55416**.
E2 **removes** items rather than adding them: the COVID-19 vaccination item
(**O0350**) and four SDOH elements (**R0310**, **R0320A**, **R0320B**, **R0330**).

**A trap worth naming:** the CY 2025 final rule describes a "2027 OASIS" that
would have *added* four elements. **That release was cancelled** and replaced by
E2 going the opposite direction. Anything sourced from the CY 2025 rule about a
2027 OASIS expansion is superseded.

Lineage, all primary: OASIS-E 2023-01-01 → OASIS-E1 2025-01-01 → **OASIS-E2
2026-04-01**. No successor exists — a confident negative, not a gap: nothing after
E2 on the CMS page, and a full FR-corpus search for "OASIS-E3" returns nothing.

Note `42 CFR 484.55(c)(8)` deliberately does **not** name a version — it says "the
current version … as specified by the Secretary." **So a product must track the
CMS OASIS Data Sets page, not the CFR, for version changes.**

### OASIS is all-payer for skilled patients since 2025-07-01

Not Medicare-only, which is how we had it. The correct rule is two-level:

- **Provider type decides scope.** Medicare-certified HHA → in scope. Non-medical
  personal-care / private-duty agency → **out of scope entirely**.
- **Service type decides per-patient applicability** within a certified HHA.
  Exempt, quoted verbatim at 90 FR 55421: *"patients under the age of 18;
  patients receiving maternity services; and patients receiving only personal
  care, housekeeping, or chore services."*

A dual-line business running both a certified HHA and a private-duty division has
OASIS obligations on the skilled side only.

### PDGM is current — and 30-day payment does not mean everything is 30-day

Confirmed at **42 CFR 484.205(b)(2)**: periods on or after 2020-01-01 are paid on
a **30-day** basis. Created by FR doc 2018-24145 (83 FR 56406), effective
2019-01-01, applying to periods from 2020-01-01. The CY 2026 rule (90 FR 55342,
effective 2026-01-01) **updates** PDGM and does not supersede it. No CY 2027 final
rule exists; the proposed rule was still in its comment window on 2026-08-31.

**The trap:** certification (`424.22(b)(1)`) and OASIS recertification
(`484.55(d)(1)`, "the last 5 days of every 60 days") remain on **60-day** clocks.
A product modelling one clock will mis-schedule recerts.

Also worth carrying: **NOA, not RAP** — `484.205(j)(1)` requires a Notice of
Admission within **5 calendar days** of start of care, with a **1/30th per day**
payment reduction for late filing that the provider may not bill to the
beneficiary.

---

## 5. EVV patent assignees — both resolved, and one is nearly expired

### US 9,471,749 — "Healthcare verification system and method"

**Assignee at issue: Kinnser Software, Inc. Current assignee: WellSky Home Health
& Hospice Corporation.** PRIMARY-VERIFIED from two independent sources each. The
2018-11-13 event is a **name change**, not a sale.

**That is worth noting for reasons beyond IP:** WellSky is a direct competitor
identified in our own 2026-08-26 competitive audit — vendor-claimed at 4,300+
agencies and 8 of the 10 largest personal-care franchise networks. Filed
2014-03-11, priority 2013-03-14, issued 2016-10-18, **anticipated expiry
2034-11-14**, status "Active – Reinstated."

Claim 1, descriptive only: determines the patient's home address and the
caregiver device's geolocation, and enables an electronic-signature screen only
if the device is within a threshold distance. **Flagging only — no infringement
analysis performed or implied.**

### US 11,915,806 — the long HIPAA/EVV title

**Assignee: Therap Services, LLC**, original and current, no reassignment.
PRIMARY-VERIFIED from three sources.

**The fact that changes its weight: it expires 2026-11-27** — about three months
from today. It claims 2006 priority through a long continuation chain, so the
20-year term runs from 2006-11-27. Our earlier note flagged it as the one
directly overlapping any video-based check-in feature; that concern has a short
remaining life.

Claim 1, descriptive only: stores physical attributes of the individual under
care and others, records video, uses face/eye/hair matching to distinguish the
individual from bystanders, blurs bystanders before human viewing, and
auto-populates service-type/recipient/date/location/provider/start-end fields from
the video data. **Flagging only.**

### Sandata telephony call-matching — found, and it appears never to have granted

**US 2006/0281469 A1**, "Employee tracking system with verification", app
11/152,279, filed 2005-06-14. Claim 1 is exactly the call-matching model our notes
described — separate employee-side and client-side data over one telephone call,
cross-matched against a database.

**Assignee attribution is weaker here and is labelled accordingly:** one
aggregator (Unified Patents) names Sandata Technologies; FreePatentsOnline prints
**no** assignee for this document and Google Patents 503'd. Corroboration is
circumstantial — inventor **Gary Stoller** is Sandata's founder and the same
counsel prosecuted Sandata's confirmed **US 7,835,955**. **Grant status: appears
not to have granted** (publication type A, no grant number); abandonment **NOT
VERIFIED**.

### A method correction worth keeping

The lane's first pass used FreePatentsOnline's `AN/"Sandata"` assignee search and
got 12 hits, **five of which are not Sandata's** — they belong to MCI, IVDS and
individual inventors, and the string "Sandata" appears zero times on several of
those pages. The `AN/` field silently degraded to a broader match. **Had that
result set been trusted, we would have attributed MCI's patents to Sandata.**
Assignee attribution is a factual claim about a real company; verify each hit on
its own page rather than trusting a field search.

### Endpoints, for the next pass

Working: **Google Patents via WebFetch** (the only source giving the Legal Events
assignment chain), **FreePatentsOnline via curl** with a browser UA (verbatim
claims, needs retries), and **`api.unifiedpatents.com/patents/{US-NNNNNNN-B2}`** —
clean JSON, no key, no rate limit, the most efficient endpoint found.

Dead or gated: `assignment-api.uspto.gov` (**DNS does not resolve — appears
retired**), both PatentsView hosts, `ped.uspto.gov`, `api.uspto.gov` (401, needs
key), EPO OPS and Espacenet (403), `patents.google.com` via curl (503 bot-block).

---

## 6. The one code correction this pass produced

`api/_lib/sen-evv-readiness.js` ships a `residual_gaps` entry reading, in part,
*"medicaid.gov and cms.gov return 403 to automated fetch."* **That reason is now
false** — both return 200; the EVV guidance page returns 404, i.e. it moved.

The **gap itself may still be real** — unread guidance is unread — but a
disclosure that misstates *why* is worse than one that simply says what is
unknown, because it prescribes the wrong remedy. Corrected in the same commit as
this document to state the accurate position: the guidance has not been read, the
previously-recorded block does not exist, and the current obstacle is a moved URL.

---

## 7. What remains open

1. **State-by-state variation** — licensure, training hours, background checks, wage/sick-leave. Not attempted in this pass. The largest remaining gap in the senior-care research.
2. **Whether CMS-2450 targets the 80/20.** Unknowable until the NPRM publishes. Re-check RIN 0938-AV70 and the FR Part 441 index.
3. **Whether DOL's rescission finalises.** RIN 1235-AA51, projected November 2026.
4. **CMS sub-regulatory EVV guidance** — still unread, but now for a findable reason. The next pass should locate the current URL rather than treat it as blocked.
5. **State domestic-worker overtime rules**, which a federal FLSA rescission would not displace.

## 8. Method notes worth carrying

- **The Federal Register API's `conditions[term]` search is unreliable.** A quoted `"direct care worker"` returned zero results, which is certainly false. **Use the `conditions[cfr][title]` + `conditions[cfr][part]` index instead** — structured metadata, behaves correctly. Every negative finding in §2 rests on that index, not on term search.
- **eCFR's human HTML redirects bots**; its **versioner API** (`/api/versioner/v1/full/{date}/title-NN.xml?part=NNN`) does not. That API is how §2 and §3 were read.
- **federalregister.gov HTML 403s but its JSON API and `/documents/full_text/text/...txt` paths work.**
- **Do not record a host as blocked without re-testing.** Two lanes in this very pass disagreed about `cms.gov`, and the note that resolved it was a direct one-line curl.
