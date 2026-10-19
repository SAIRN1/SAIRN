# Worldwide competitive-gap audit — STRUCTURAL PEST CONTROL

**fourth / b31, 2026-10-19.** Fourth in the "vertical SAIRN has not built for"
series, after childcare (b28), outpatient behavioral health (b29, **PARKED**)
and small-fleet DOT compliance (b30, recommended against).

**Michael's instruction was to continue the queue. b30's own recommendation was
to stop auditing until two company questions were settled; that was raised and
the instruction was repeated, so this is the audit, done in full.** Whether it
changes either answer is §7.

**THIS IS NOT A BUILD RECOMMENDATION.** §7 says what would have to be true.

---

## 0. WHY THIS ONE — IT WAS PICKED TO TEST WHETHER THE SERIES CAN EVER SAY YES

The first three audits failed on **company capability**, not on market: twice
on *nobody owns a 50-state regulatory matrix*, once on *SAIRN has never sold an
administered service*. Picking a fourth vertical with those same two
dependencies would have been guaranteed to produce a fourth no.

So this one was picked **against** that: structural pest control is a
**field-service trade with recurring routes**, which is the exact shape
StoneDesk, SAIRNroofing, SAIRNgrounds, SAIRNscape and SAIRNmechanical already
serve. If the series can ever produce a yes, it should be here.

**It does not, and the reason is new — which makes this the most informative
of the four.** §3 and §6.

Universe re-derived at HEAD, as in b29/b30:

    git ls-files '*.html' | grep -E '^(sairn[a-z]+|stonedesk)\.html$'   -> 17

---

## 1. THE MARKET — FRAGMENTED, WHICH IS THE GOOD NEWS

**The denominator is contested and is reported as a RANGE rather than picked:**

| source | count | what it counts |
|---|---|---|
| NPMA | **16,565** firms | structural pest management |
| BLS (2026 Q1) | **17,933** establishments | establishments, not firms |
| IBISWorld (2026) | **31,307** businesses | a broader industry definition |

**These are not three estimates of one number — they count three different
things**, and a single figure would be a fabrication. Revenue is similarly
split: NPMA puts **US structural service revenue at $12.654B (2024)** and
**$13.4B (2025)**, while IBISWorld's broader industry is **$29.9B (2026)**.
Only the structural figures are relevant to this audit.

**THE STRUCTURAL FACT THAT MATTERS: 81.4% of firms operate just 1–2
locations.** This is a highly fragmented trade of small operators — the same
customer shape every SAIRN field app already targets, and the opposite of
behavioral health's two-giant split.

**The software field is crowded and already segmented by operator size**, which
is a sign of a mature, well-served market rather than a gap:

* **1–3 technicians:** GorillaDesk, Housecall Pro
* **5–15 trucks:** FieldRoutes, PestPac, Briostack
* **20–500+ technicians:** FieldRoutes, described in the buyer guidance as the
  industry default

**There is no obvious hole in the product map.** Unlike behavioral health,
where supervision-hour tracking had a visible cottage industry proving unmet
demand, nothing surfaced here that the incumbents are documented as not doing.
**That is a finding, not an absence of research**: a crowded field with a
size-segmented product ladder is what a solved problem looks like.

---

## 2. THE REGULATORY SURFACE — SETTLED AT THE TOP, A MATRIX UNDERNEATH

**Primary citations, Federal Register API** (the route b29 established;
`WebFetch` is still blocked by a redirect and `tools/sairn_http.py` still
answers):

| | rule | citation | status |
|---|---|---|---|
| **R1** | *Pesticides; Certification of Pesticide Applicators* — the strengthened federal standard | **82 FR 952**, doc `2016-30332`, published 2017-01-04, **effective 2017-03-06** | in force and OLD |
| **R2** | *…Further Extension to Expiration Date of Certification Plans* | **87 FR 50953**, doc `2022-17823`, published 2022-08-19 | extended state-plan conformance to **2023-11-04** — also passed |

R1 set a **nationwide minimum age**, capped the **recertification interval at
5 years**, required **specialised certification for fumigation and aerial
application**, and raised competency standards. **The federal floor has been
settled for years and the conformance deadline is three years past.** There is
no live federal cliff here — the opposite of b30's trucking audit, where DEA
flexibilities lapse 2026-12-31.

**The live layer is per-state and it is a matrix again. Reported, NOT verified
against any state register:** a core exam plus category exams; licence terms of
**one to three years**; CEU requirements from **4 to 24 per cycle**; and
renewal deadlines that differ per state and per licence class — Tennessee
2026-06-30, Minnesota 2026-03-01, North Carolina 2026-06-30 commercial /
2026-09-30 private, Ohio 2026-01-15. **Four states, four dates, four rules.**

**The per-application record is where the real product obligation sits**, and
it is federal via FIFRA: the label is legally enforceable, so a complete
service record carries date and time, site address and areas treated, target
pest, product name and **EPA registration number**, concentration or rate,
total quantity, method and equipment, the **certified applicator**, the
**re-entry interval** and confirmation the customer was told, and any area not
treated and why. **That is a well-specified, federally-anchored data model** —
and the most buildable thing in this audit.

---

## 3. PLATFORM FIT — AND TWO MEASUREMENT ARTEFACTS CAUGHT BEFORE THEY SHIPPED

    APPS=$(git ls-files '*.html' | grep -E '^(sairn[a-z]+|stonedesk)\.html$')   # N=17
    for each pattern: grep -ciE "<pattern>" "$f"

| primitive | present in |
|---|---|
| on-site signature capture | **15 of 17** |
| recurring service | **10 of 17** |
| credential expiry **field** | **6 of 17** |
| EPA-anything | **1 of 17** — sairnmechanical, and it is **EPA 608 refrigerant certification**, a technician credential, which is a genuine analogue |
| chemical / applicator vocabulary | **2 of 17**, both incidental (a `chemical_handling` option in sairngrounds, a `Chemicals` category in stonedesk) |
| service-site address as a field | **1 of 17** |
| CEU / recertification | **2 of 17**, neither about a trade licence |
| **route / stop ordering** | **0 of 17** |

**TWO ARTEFACTS, BOTH CAUGHT BY READING THE MATCHES INSTEAD OF THE COUNT:**

* **`\broute\b` returned 17 of 17.** Every hit is the same sentence in a shared
  comment — *"classify a single route because 13 of…"* — copied into every app.
  **There is no routing primitive anywhere on this platform; the real count is
  0 of 17.** This is the second consecutive audit where a loose pattern
  returned exactly the universe size, which is what a wrong measurement looks
  like (b30's was `\bhos\b` matching *"those"*).
* **`chemical|applicator|pesticide` returned 3 of 17**, one of which is
  SAIRNvet's *"chemical contraception"*. Unrelated. Corrected to 2, both
  incidental.

**Read plainly: the FIELD-SERVICE half fits and the TRADE half does not.**
Signature capture, recurring service and job records are there. Routing —
the thing every incumbent sells first — **does not exist anywhere on this
platform**, and neither does any chemical, applicator or EPA-registration
model. SAIRN's field apps are *job*-shaped, not *route*-shaped.

---

## 4. WHAT WOULD HAVE TO BE BUILT THAT HAS NEVER BEEN BUILT

1. **Route optimisation and daily dispatch.** 0 of 17. The buyer guidance
   treats route optimisation as the primary purchase reason ("10+ hours
   weekly"), and it is a genuinely hard problem, not a panel.
2. **A chemical application record keyed to EPA registration number**, with
   rate, quantity, method, re-entry interval and customer notification — the
   FIFRA record in §2.
3. **An applicator licence object** with category, state, term and CEU balance,
   evaluated **as of the service date** — the `effective_from` shape
   SAIRNdental proved, applied to a trade licence.
4. **A 50-state renewal and CEU matrix.** Same unstaffed obligation childcare
   and behavioral health both named.
5. **Criticality.** A pesticide application record is the evidence in a state
   enforcement action and a re-entry interval is a human-safety determination.
   **Tier A on at least two resources, and that tier is NOT assessed here.**

---

## 5. WHAT THIS AUDIT DID NOT DO

* **No competitor account was provisioned and no product was driven.** Every
  claim in §1 rests on secondary sources, most of them **vendor or
  vendor-adjacent buyer guides**, several of which are published by the
  products they rank.
* **No market-share percentages were found.** The size-segment ladder in §1 is
  buyer-guide consensus, not measured share.
* **No state regulation was read.** Every per-state figure in §2 is reported
  and unverified; only R1 and R2 are primary.
* **No operator, technician or state regulator was interviewed.**
* **The three company counts and the two revenue figures are NOT reconciled**
  and are reported as a range, because they count different things.

---

## 6. THE FOUR AUDITS SIDE BY SIDE

| | childcare | behavioral health | trucking | **pest control** |
|---|---|---|---|---|
| customer shape | small centres | small practices | small carriers | **small operators, 81.4% at 1–2 locations** |
| regulatory surface | 50-state CCDF, flipped twice | compacts, patchwork | one federal regime | federal floor SETTLED + per-state matrix |
| platform fit | credential expiry | code-edition engine | a file-upload box | **signature + recurring, but NO routing** |
| incumbents | a leader missing compliance | two giants, supervision gap | a service administrator | **a full, size-segmented ladder** |
| why not | no matrix owner | no matrix owner | SAIRN sells no services | **the market is already served, and the core primitive is absent** |

**THE FOURTH AUDIT FAILS FOR A GENUINELY NEW REASON, AND IT IS THE PLAINEST
ONE:** this is not an underserved market. Three audits found a gap and no
capability to fill it; this one found **capability adjacency and no gap**.

---

## 7. WHAT WOULD HAVE TO BE TRUE — AND WHAT THE SERIES HAS NOW ESTABLISHED

**For this vertical:**

1. A routing and dispatch engine exists on this platform, or is costed as a
   first-class build. It is 0 of 17 today and it is what the customer buys
   first.
2. A real small operator is interviewed and names something FieldRoutes,
   PestPac, Briostack and GorillaDesk all fail to do. **Nothing in the public
   material suggests what that would be**, and that is the honest state.
3. The per-state licence matrix has an owner — the same condition, now named by
   **three of four** audits.

**WHAT FOUR AUDITS HAVE ESTABLISHED, which is the useful output:** the blocker
has never once been the market's size or the regulation's difficulty. It has
been, in order: **no owner for a standing regulatory matrix** (childcare,
behavioral health, pest control), **no capacity to sell an administered
service** (trucking), and now **no routing primitive** (pest control). The
first two are company decisions. **The third is the first finding in this
series that is a BUILD gap SAIRN could simply close**, and it would widen every
field app it already ships — not just this vertical.

---

*Sources (secondary): schedulingkit.com, ibisworld.com, thepestcontrolbrief.com,
marketingexterminator.com, pestpac.com, techjockey.com, nerdbot.com,
educba.com, pestpromanager.com, myquoteiq.com, pipelineon.com,
onlinepestcontrolcourses.com, pestcontrolbusinesses.com, vortechpro.com,
kaamcam.com, hmndp.org, ecfr.gov (40 CFR 171), state agriculture departments
(LA, OH). Primary (R1, R2): federalregister.gov API, documents `2016-30332`
and `2022-17823`.*
