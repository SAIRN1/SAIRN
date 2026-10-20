# SAIRNcode compliance artefacts — B1, B3, B4

**fourth / ted, batch b39, 2026-10-20.** b38's audit found that SAIRNcode
already implements the substance of the US AI-transparency regime and **cites
none of the five rules that govern it**. These are the artefacts.

**THE CRITERION WAS READ FROM THE REGULATION'S OWN XML, NOT FROM A SUMMARY.**
b38's own "what it did not do" said *"a field list built from a summary of a
field list is the staleness class this platform keeps paying for"* — so this
batch pulled `https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-45?section=170.315`
(248,888 bytes), flattened it, and extracted the `(b)(11)` subtree verbatim.
Working files: `scratchpad/b39/dsi_plain.txt`, `b11_full.txt`.

**eCFR's WEB pages 302 to `unblock.federalregister.gov`, a bot wall. That was
NOT routed around.** The renderer API is eCFR's documented machine interface
and is the intended route; `.../versioner/v1/full/...xml` answered **406 Not
Acceptable** and is reported rather than worked around.

---

## 0. READING IT ITSELF CHANGED TWO THINGS, AND ONE WAS NEARLY A WRONG ARTEFACT

**THERE IS AN EXPIRED PREDECESSOR CRITERION THAT ALSO SAYS "Source attributes",
AND MY FIRST EXTRACTION LANDED ON IT.** `§ 170.315(a)(9)(v)` carries a *"Source
attributes"* heading with **FOUR** items for evidence-based CDS — and its own
`(a)(9)(vi)` reads:

> *"Expiration of criterion. The adoption of this criterion for purposes of the
> ONC Health IT Certification Program expires on January 1, 2025."*

**A four-attribute artefact built against a criterion that expired is exactly
the failure this batch was told to avoid**, and a grep for the heading finds
the dead one first. The live criterion is `(b)(11)`.

**AND THE REAL COUNTS:** `(iv)(A)` is **13** items — b38's summary-derived
figure was right and is now confirmed from source. `(iv)(B)` is **9 headings
carrying 31 leaf items**, which b38 could only call *"a longer list."*

| | | leaves |
|---|---|---|
| (B)(1) | Details and output of the intervention | 4 |
| (B)(2) | Purpose of the intervention | 4 |
| (B)(3) | Cautioned out-of-scope use | 2 |
| (B)(4) | Development details and input features | 4 |
| (B)(5) | Process used to ensure fairness | 2 |
| (B)(6) | External validation process | 4 |
| (B)(7) | Quantitative measures of performance | 5 |
| (B)(8) | Ongoing maintenance of implementation and use | 4 |
| (B)(9) | Update and continued validation / fairness schedule | 2 |
| | **total** | **31** |

---

## 1. B1 — THE PREDICTIVE DSI SOURCE-ATTRIBUTE RECORD

**WHAT THIS IS AND IS NOT.** `(b)(11)(iv)` says the attributes *"must be
supported"* — i.e. the record must exist and be reachable, not that every
answer must be impressive. **So the value of this artefact is that it says NOT
ESTABLISHED where nothing has been established.** An attribute filled in with
something aspirational is worse than one that admits the gap: it converts a
missing control into a false claim, which is the one thing `(b)(11)` cannot
tolerate.

**SCOPE: SAIRNcode's AI code-suggestion path**, the one at
`sairncode.html:842`.

### (B)(1) Details and output

| | |
|---|---|
| (i) developer name and contact | SAIRN Technologies. **Contact: NOT SET — a real address is needed before this is publishable.** |
| (ii) funding source of the technical implementation | Internal to SAIRN Technologies. No external or vendor funding. |
| (iii) value produced as output | A **CPT / HCPCS / ICD-10 code suggestion** for a described procedure or diagnosis, each carrying the exact supporting phrase from the clinical note, plus a **conflict verdict** (NCCI/CCI procedure-to-procedure edit, ICD-10-CM Excludes1/Excludes2 pairing, required modifier). |
| (iv) output type | **A RECOMMENDATION, and a CLASSIFICATION.** The code suggestion informs; the conflict check classifies a pair as conflicting or not. It is **not** an evaluation or an analysis, and it does not replace the coder. |

### (B)(2) Purpose

| | |
|---|---|
| (i) intended use | Assist a **qualified human coder** in selecting and checking codes against current CMS/AMA guidance. |
| (ii) intended patient populations | None. **The intervention operates on a clinical note and a code set, not on a patient cohort** — there is no patient-level model and no population was selected for or against. |
| (iii) intended users | Certified/qualified medical coders and billing staff inside a licensed practice. **Not patients, not clinicians at the point of care.** |
| (iv) intended decision-making role | **INFORMS.** Never augments-to-autonomy and never replaces: every suggestion enters a human-review queue, and `sairncode.html:842` refuses to pass a suggestion whose citation it cannot verify. |

### (B)(3) Cautioned out-of-scope use

| | |
|---|---|
| (i) tasks, situations or populations cautioned against | **Do not use it to decide a payment amount.** The app itself already refuses this for CY2026 (`:2968`): Medicare runs **two** PFS conversion factors under SSA 1848(d)(20) and the app will not state an amount when QP status is unknown. **Do not use it for a date of service in a prior code year** — see B2 below, nothing is date-qualified. **Do not use it as the sole basis for a risk-adjustment submission** — see B3. |
| (ii) known risks, inappropriate settings, limitations | **Known limitation, measured:** no code set is date-qualified (`grep -ci "effective date"` → **0**), so a code valid for a 2026 DOS may not have existed for the DOS actually billed. **Known risk:** under **31 U.S.C. 3729(b)(1)** *"knowing"* includes **reckless disregard** and *"require[s] no proof of specific intent to defraud"* — so accepting a suggestion without reading the citation is itself the exposure, and the citation is the defence. |

### (B)(4) Development details and input features

| | |
|---|---|
| (i) exclusion/inclusion criteria influencing the training data | **NOT APPLICABLE AND THAT IS A DESIGN PROPERTY, NOT A GAP.** There is no training set: the intervention is a general-purpose model instructed to answer **only from live web search**, never from parametric memory. Its prompts say so in terms — *"do not answer from memory alone, your training data may be stale for this year's code changes"* (`:12430`) — and the response contract requires a `source_snippet` that is *"the EXACT text from a search result -- character-for-character from the search result, not a paraphrase"*, with `no_match:true` rather than a guess. |
| (ii) **use of (A)(5)–(13) variables as input features** | **NONE. MEASURED, NOT ASSERTED.** `grep -ci` over `sairncode.html`: `ethnic` **0**, `sexual orientation` **0**, `gender identity` **0**, `social determinant`/`SDOH` **0**, `health status assessment` **0**; `race` returns **2 hits and both are the word "traceable"/"traced"**. `dob` appears **9** times and **only in the eligibility form** (patient and dependent date of birth for a coverage check), never as an input to a code suggestion. |
| (iii) demographic representativeness per (A)(5)–(13) | **NOT APPLICABLE** — no demographic variable is an input feature, per (ii). |
| (iv) relevance of training data to the deployed setting | **NOT APPLICABLE** — see (i). The equivalent question for this design is *how current is the search corpus*, and that is answered per-call by the `source_snippet` the response is required to carry. |

### (B)(5) Process used to ensure fairness

| | |
|---|---|
| (i) approach taken to ensure the output is fair | **NOT ESTABLISHED. No fairness assessment has been conducted.** What exists instead is a **structural** argument that is worth stating and is not a substitute: no protected-class variable is an input feature (B4(ii)), and every suggestion must be traceable to a quoted phrase in the note. |
| (ii) approaches to manage, reduce or eliminate bias | **NOT ESTABLISHED.** The citation-verification step bounds *fabrication*, not *bias*, and the two are different failures. |

### (B)(6) External validation process

**NOT ESTABLISHED, all four leaves.** No external data source, no clinical
setting, no third party, no process. **This is the largest single gap in the
record and it is the one a certification body would open with.**

### (B)(7) Quantitative measures of performance

**NOT ESTABLISHED, all five leaves** — no validity or fairness figure on
same-source test data, none on external data, and no outcome evaluation.

**AND THERE IS A RELEVANT PIECE OF HISTORY THAT BELONGS HERE RATHER THAN BEING
HIDDEN:** this file previously carried **fabricated 82% / 71% confidence
scores** (`sairncode.html:862`, `:4206`), which were removed and replaced with a
**derived** figure. **An absent performance measure is the correct state; a
manufactured one was the previous state.** Recording that is part of what
(B)(7) is for.

### (B)(8) Ongoing maintenance

**NOT ESTABLISHED, all four leaves.** No monitoring cadence for validity or
fairness, and no local-data measurement.

### (B)(9) Update and continued validation schedule

**NOT ESTABLISHED, both leaves.** **Recommended first step and it is small:**
adopt the search-grounding contract as the monitored property — *what fraction
of suggestions are rejected for an unverifiable citation* is already computable
from the human-review queue, needs no new instrumentation, and is a real
performance measure rather than a declared one.

### (v) Access and modification

`(b)(11)(v)(A)` requires a limited set of identified users to reach *complete
and up-to-date plain language descriptions* of these attributes, and `(v)(B)`
that they can **record, change and access** them. **Nothing in SAIRNcode
surfaces this record today** — `grep -ci "source attribute"` → **0**. This
document is the content; a panel that renders it, and lets an owner edit the
NOT ESTABLISHED entries, is the remaining work.

---

## 2. B3 — THE TWO RISK-ADJUSTMENT DATES, AND THE ASYMMETRY

**From `42 CFR 422.310(g)`, read in full in b38:**

| | |
|---|---|
| submission deadlines | **the first Friday in September** and **the first Friday in March** |
| after the final deadline | an organisation **may only correct OVERPAYMENTS. It may not submit new diagnoses.** |
| `422.310(e)` | a **sample of medical records** must be submitted for validation as CMS requires; **RADV findings may be EXTRAPOLATED** and payment remitted |

**THE PRODUCT CONSEQUENCE IS DIRECTIONAL AND IT IS THE WHOLE POINT.** Before
the final deadline, a found **gap** (an unsubmitted HCC) and a found **error**
(a wrongly submitted one) are both actionable. **After it, only the error is**
— and it is *mandatory*, while the gap is worth nothing.

**So an HCC panel that lists both as "findings" is pointing the user at work
that no longer exists in one direction, and burying the work that is now
compulsory.** `grep -ci "RADV"` over `sairncode.html` → **0**; `first Friday`
→ **0**.

**THE SPECIFICATION, as data rather than prose:**

```
RADV_WINDOW = {
  // 42 CFR 422.310(g). COMPUTED, never a table of dates that goes stale --
  // the same decision gfeFederalHolidays() made in sairndental.html.
  firstFridayOf: function(year, month0){ /* month0: 2=March, 8=September */ },
  // Before the March deadline for the prior payment year, BOTH directions are
  // actionable. After it, ONLY overpayment corrections are.
  mode: function(today){ return today <= finalDeadline ? 'BOTH' : 'OVERPAYMENT_ONLY'; }
}
```

**In `OVERPAYMENT_ONLY` mode the panel must say so, and must not render a
found-gap as actionable** — the honest string is *"past the 422.310(g)
deadline: this gap can no longer be submitted. Over-coded diagnoses must still
be corrected."* **Showing the gap greyed and unexplained is the same defect as
the credentialing tiles this batch just fixed.**

---

## 3. B4 — THE 92.210(b) DECISION-SUPPORT-TOOL INVENTORY

**`45 CFR 92.210` has three paragraphs, (a)–(c), and `(b)` is an ONGOING DUTY
TO GO LOOKING** — *"reasonable efforts to identify uses"* of patient care
decision support tools that employ variables measuring race, colour, national
origin, sex, age or disability. **A duty to identify is satisfied by an
inventory, so here is one.**

| panel / path | is it a decision support tool? | does it use a 92.210 variable? |
|---|---|---|
| AI code suggestion (`:842`) | **yes** | **no** — measured in B4(ii) above: 0 for race, ethnicity, sexual orientation, gender identity, SDOH, health status |
| NCCI / Excludes conflict check (`:4460`) | **yes** | **no** — inputs are code pairs only |
| current-code lookup (`:12430`) | **yes** | **no** — input is a text description |
| `hcc` risk adjustment | **yes** | **NOT ESTABLISHED — and this is the one to check first.** HCC models are age- and sex-weighted by construction. Whether SAIRNcode's panel reads age or sex, or only displays what a payer returned, was **not determined** here |
| `drg` grouping | **yes** | **NOT ESTABLISHED** — DRG grouping is age-sensitive in several MS-DRG pairs |
| `anesthesia`, `pctc`, `modrouting` | arguably | **no** — unit and modifier arithmetic |
| `eligibility` | **no** — a coverage lookup, not a recommendation | collects **date of birth** (`:2694`, `:2709`), which is an *age* variable under (b), but is not a decision support tool |
| `fraud`, `ar`, `revenue`, `prebill`, `encoder`, `query`, `rac`, + 13 specialty panels | not assessed | **NOT ASSESSED** |

**THIS INVENTORY IS INCOMPLETE AND SAYS SO, which is the honest state of a
first pass.** `(b)`'s duty is *ongoing* and *reasonable efforts* — a partial
inventory that names what it has not covered discharges more of that duty than
a complete-looking one that quietly stops at the easy panels.

**EXACT NEXT STEP: `hcc` and `drg`.** Both are age/sex-weighted by
construction, both are named Tier A work elsewhere, and both are the rows where
the answer could be *yes*.

---

## 4. THE FIVE RULES, AND WHERE EACH IS NOW CITED

| rule | artefact | status |
|---|---|---|
| **45 CFR 170.315(b)(11)** | §1 — the full 9-heading / 31-leaf predictive record | **written**, with 15 leaves NOT ESTABLISHED and named |
| **42 CFR 422.310(e),(g)** | §2 — the two dates and the mode switch | **specified**, not yet code |
| **31 U.S.C. 3729(b)(1)** | §1 (B)(3)(ii) — reckless disregard, no intent required | **cited where it bites**, on the out-of-scope caution |
| **45 CFR 92.210(b)** | §3 — the tool inventory | **written and explicitly incomplete** |
| **WHO ICD-11 (WHA72.15)** | — | **NOT ADDRESSED HERE.** b38 called it a timing judgment against WHO's *14 countries collecting or reporting*, and nothing in this batch changes that. Named so its absence is not mistaken for coverage |

---

## 5. WHAT THIS DID NOT DO

* **No code was written.** These are documents, which is what B1 and B4 are;
  **B3 is specified and unimplemented**, and `api/sd-data.js` — where the `sc_*`
  handlers live — is **cody's**.
* **`sairncode.html` was not modified.** It is in **0** of this batch's commits.
* **Nothing was driven.** The grounding and citation-verification behaviour in
  §1 is read from shipped user-facing copy and prompt text, **not** reproduced.
  **That matters most for (B)(7):** I am recording that no performance measure
  exists, which is safe; I am *not* claiming the verifier works.
* **The 92.210 compliance date is still unestablished** — not in the section,
  not in 92.10. b38 said so and it is still true.
* **`hcc` and `drg` were not read** for 92.210 variables. They are the two most
  likely to be a *yes* and they are the exact next step.
* **No legal review.** Four instruments were read in full and one is cited from
  b38's read. What they mean for this product is advice, and this is not it.

---

# ADDENDUM — b40, 2026-10-20: the two panels, and the first measured leaf

## A1. B4's NAMED NEXT STEP POINTED AT THE WRONG PANELS

§3 above said *"EXACT NEXT STEP: `hcc` and `drg`. Both are age/sex-weighted by
construction … both are the rows where the answer could be yes."* **Read now,
and the prediction was wrong in both directions.**

| panel | 92.210 variable? | evidence |
|---|---|---|
| `hcc` | **NO** | `renderHcc()` (`sairncode.html:4497`) reads `{cat, patient, value, status}`. The panel body is a **1,434-char shell** with a four-column table. No age, no sex, no gender, no DOB anywhere in it |
| `drg` | **NO** | same shape, a **1,391-char shell**. Zero matches |
| **`transport`** | **YES — AGE, determinatively** | `<input type="number" id="tr-age" placeholder="Patient age (months)">` (`:1386`) |
| **`esrd`** | **YES — AGE, determinatively** | `<input type="number" id="esrd-age" placeholder="Age at end of month">` (`:1690`), and the panel's own copy: *"The code is fixed by the age at the **end of the month**"* (`:1684`) |

**`sex` and `gender`: ZERO occurrences anywhere in the file.** There is no sex
variable in SAIRNcode at all, and the only 92.210 variable in use is **age**.

**THE USE IS LAWFUL AND THAT IS NOT THE POINT.** A dialysis MCP code and a
paediatric transport code are **fixed by age by the rule being implemented** —
the clearest possible legitimate use, and `92.210(c)`'s mitigation duty has
little to bite on. **But `92.210(b)` is a duty to IDENTIFY, and these two were
not on the inventory.** An inventory that misses the only two panels using a
protected-class variable has failed at its one job.

**CORRECTED ROWS, to be read with §3:**

| panel | DSI? | 92.210 variable | status |
|---|---|---|---|
| `hcc` | yes | **none on the client** | the computation, if any, is server-side in `api/sd-data.js` — **cody's, NOT READ** |
| `drg` | yes | **none on the client** | same |
| `transport` | yes | **AGE (months)**, determinative | disclosed; lawful; **must stay on the inventory** |
| `esrd` | yes | **AGE at end of month**, determinative | disclosed; lawful; **must stay on the inventory** |

**THE SERVER CAVEAT IS LOAD-BEARING, NOT A HEDGE.** *"No 92.210 variable on the
client"* is not *"no 92.210 variable"*. `hcc` and `drg` could read age or sex
server-side and the client would look exactly like this. That half is
unreadable to me by claim and is named as the next step rather than guessed.

---

## A2. (B)(7) GETS ITS FIRST MEASURED LEAF, AND THE DATA ALREADY EXISTS

§1 left all five `(iv)(B)(7)` leaves NOT ESTABLISHED and proposed one cheap
real measure. **The store already carries it.**

`scRouteCodedItems()` (`:7393`) partitions on `review_status`, and
`reviewCodedItem()` (`:7345`) refuses any value other than
`reviewed_accepted` / `reviewed_rejected` — so a decided item is **settled,
whichever way it went**. Four states:

    needs_human_review | auto_assigned | reviewed_accepted | reviewed_rejected

**THE MEASURE, defined so it cannot drift:**

```
HUMAN-REJECTION RATE
  = count(review_status === 'reviewed_rejected')
  / count(review_status === 'reviewed_rejected' || === 'reviewed_accepted')

DECIDED ITEMS ONLY IN THE DENOMINATOR. needs_human_review is NOT a rejection
-- it is an item nobody has looked at, and counting it either way is the
collapse-three-states-into-two defect this platform keeps finding.
auto_assigned is NOT an acceptance either: no human looked at it.
```

**A SECOND, SHARPER FIGURE from the same store**, because the first measures the
coder's disagreement with everything rather than the grounding specifically:

```
CITATION-HELD RATE
  = count(items whose confidence_basis names an unverifiable citation)
  / count(all coded items)
```

`confidence_basis` is a real array built at `:7201-7203`
(`review_status = basis.length ? 'needs_human_review' : 'auto_assigned'`) and
`escalation_reason` already renders it as *"Held for a human coder because:
…"*. **The reasons are already per-item and already structured.**

**WHY IT IS A GENUINE `(B)(7)` LEAF AND NOT A VANITY METRIC:** `(B)(7)(i)` asks
for *validity of the intervention in test data derived from the same source as
the initial training data*. **There is no training data** — §1 (B)(4)(i) — so
the nearest honest analogue is **validity in local data under human
adjudication**, which is also what `(B)(8)(ii)` asks for by name: *"Validity of
intervention in local data."*

**NOT BUILT, AND THE REASON IS SCOPE RATHER THAN DIFFICULTY.**
`sairncode.html` is **DOCS-ONLY in b40's claim** and appears in **0** of b40's
commits. This is the specification; it is two `filter().length` calls over a
store that already exists.

**AND IT MUST SHIP WITH ITS DENOMINATOR VISIBLE.** A rejection rate of *"0%"*
over two decided items is not a performance measure, and `(B)(7)` would be
**worse** for it than for the honest NOT ESTABLISHED it replaces. **Render it as
`N of M decided`, or not at all** — the rule SAIRNdental's denials panel already
follows with *"N of M argued"*.
