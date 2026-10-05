# Register corrections — batch 4, derived at HEAD, text only

**2026-10-05 (hank).** Items 1, 2, 8, 9. **Nothing applied.**

**`docs/CRITICALITY-TIERS.md` IS cc's UNDER A LIVE CLAIM** — tested
mechanically, not assumed:

    python tools/sairn_claim.py check platform "... FILES: docs/CRITICALITY-TIERS.md"
    BLOCKED -- another session already claimed overlapping work:
      session : cc    claimed : 2026-10-05T11:12:09Z (0.6h ago)
      blocked by: same declared FILES: docs/CRITICALITY-TIERS.md

cc is working *"the match.cost register cell from hank's delivered text"* — my
previous batch's delivery, which they applied at `4dfc4753`. **The brief says
fix items 1 and 2 now; the claim system says the file is open in another
session.** I am not editing it. Everything below is paste-ready, and the only
thing standing between it and the register is one claim release.

---

## 0. Premise log (item 11 methodology)

| Item | Premise at HEAD |
|---|---|
| 1 `sdn_vendors` PII | **HELD** — cell still says "no PII"; code still writes `contact_name/phone/email` |
| 2 `sb_perf` | **HELD** — both citations still wrong, still invisible to the tool |
| 3 drift checker | **HELD** — and narrower than stated: the anchor was a *closing backtick*, so ranges were blind too |
| 4 registry tail | **HELD** — filed with 7 arms; and the boundary is **not reproducible** |
| 5 `push_retry` | **HELD**, both halves |
| 6 sweep re-run | **ALREADY CLOSED** — ran anyway; it found the instability |
| 7 #745 | **READ** — 5 resources, 8 line corrections, one of which is **wrong at HEAD** |
| 8 twelve logs | **ALL HELD** — 24 of 24 pairs still citing the old line |
| 9 rows 82/845 | **ALREADY DELIVERED** — see §5 |
| 10 elapsed | **18 apps**, derived |

---

## 1. Item 1 — `sdn_vendors` (#772), row `:343`

**Premise held. Ten days, now eleven.** The cell asserts absolutely:

> *"No elevated confidentiality class — **no PII**, PHI, privileged
> communication, or financial-account detail on this row. Classified by the
> stated B rule rather than individually read."*

`sairndesign.html:2613-2614` writes
`{name, category, contact_name, phone, email, …}`, and the seed at
`:1607-1611` carries five real examples
(`contact_name:'Jamie Rourke', phone:'(800) 555-0100'`). `10855b55`
(2026-09-25) said so in its own commit body.

### Paste-ready — confidentiality cell

> A trade vendor's record **including a named individual's direct work contact
> detail** — `contact_name`, `phone`, `email`. The `sd_customers` /
> `properties` class: commercially sensitive, not an elevated one

### Paste-ready — evidence cell

> **INDIVIDUALLY READ 2026-10-05 (hank), CORRECTING A CLAUSE THAT WAS FALSE
> WHEN WRITTEN AND WAS CONTRADICTED IN WRITING ELEVEN DAYS AGO.** The cell said
> *"no PII … classified by the stated B rule rather than individually read"* —
> an absolute claim and an admission it was never checked, in one sentence.
> READ OUT OF THE APP: `saveVendor()` at `sairndesign.html:2613-2614` writes
> `{name, category, contact_name, phone, email, lead_time_typical_weeks,
> rating, notes, created_at}`; the seed at `:1607-1611` carries five real
> contacts. **`10855b55` (2026-09-25) already recorded it**: *"sdn_vendors …
> is the row that actually carries named individuals' phone and …"*.
> **TIER UNCHANGED AT B, and that is the finding rather than a formality:** a
> work phone and a work email for a person acting in a business capacity is the
> `properties` / `sd_customers` class, already settled at B on commercial
> sensitivity. The false clause goes; the tier it was attached to was right for
> a different reason than the one given.

**The counter-argument, stated because it is not silly:** a reader who holds
that a named individual's phone and email is an elevated class regardless of
business capacity would re-tier this A. That is not the reading this register
has applied 37 times, so I did not apply it — but the call is mine and it is
arguable.

---

## 2. Item 2 — `sb_perf` (row `:198`), and the tool still cannot see it

**Both citations are wrong at HEAD, and both are in the form the checker was
blind to.** Re-derived by searching for the claim, never by offsetting the old
number:

| Cited | Row's claim | At HEAD | Verdict |
|---|---|---|---|
| `sairnbiz.html:448` | *"rows are `{emp, type, due, rev, score, raise, pip, status}`"* | `<button class="btn bo" onclick="closeHireModal()">Cancel</button>` | **WRONG** |
| `:4714` | *"exported with those headers at `:4714`"* | `$('tr-cert').textContent=…` — the training KPI tiles | **WRONG** |

Derived replacements:

    rows are {emp,type,due,rev,score,raise,pip,status}
        LIVE WRITE  sairnbiz.html:2480   p.push({emp:emp,type:$('rvtype').value,
                                           due:$('rvdue').value,rev:…,score:…
        SEED        sairnbiz.html:2171-2175   identical shape, inside
                                           st('sb_perf',[ at :2170

    exported with those headers
        sairnbiz.html:5143   else if(type==='performance'){rows=[['Employee',
                               'Type','Due','Reviewer','Score','Raise','PIP',
                               'Status']];ld('sb_perf',[])…

`:5143` matches the sentence exactly — that header list is literally
`Employee, Type, Due, Reviewer, Score, Raise, PIP, Status`, and it reads
`sb_perf`.

### Paste-ready, row `:198`

> `sairnbiz.html:448` → `sairnbiz.html:2480`
> `exported with those headers at `:4714`` → `exported with those headers at `:5143``

and append:

> **CITATIONS RE-DERIVED 2026-10-05 (hank).** Both line numbers had drifted and
> **neither was visible to `citation_line_drift_check.py` before 2026-10-05** —
> it read only the bare `` `:NNN` `` form. `:448` had become the hire modal's
> Cancel button and `:4714` the training KPI tiles. Both CLAIMS were true; only
> the numbers had moved. **Tier untouched:** A on confidentiality for the `pip`
> flag, as re-tiered 2026-09-25.

---

## 3. Item 7 — hover log #745, read directly, and one of its corrections is wrong

Read read-only from
`~/.claude/projects/C--Users-marsh-Documents-SAIRN-hover/hover-audit-log/hover-audit-log.jsonl`
(833 entries). **Nothing in the hover clone was written or opened for writing.**

Entry 745, 2026-09-30, `target: hank`, severity low:
*"ROUTED PACKAGE, TEXT ONLY, NOTHING EDITED. Part A — 22 rows hand-read this
round: 8 real corrections found, 14 confirmed already-correct."*

**The five resources, re-derived at HEAD:**

| Resource | Row | Repoint | At HEAD |
|---|---|---|---|
| `bld_comm_log` | `:210` | `:6752`→`:6811` | ✅ `// Deliberately homeowner-facing only: cost, margin, committed spend, and` |
| `sb_vends` | `:201` | `:3745`→`:3832` | ❌ **WRONG — see below** |
| `sc_anesthesia_base_units` | `:264` | `:5016`→`:5049` | ✅ `note.textContent = 'Base units filled from your reference table (source: '…` |
| `sf_events` | `:358` | `:4343`→`:4999`, `:4367`→`:5023` | ✅ both: the `K_SESSIONS` filter and the Sessions-panel event-link filter |
| `sd_comms` | `:163` | `:10539`→`:10582`, `:10575`→`:10618`, `:10606`→`:10649` | ✅ all three are `var d=commsEnsureIds();` |

### `sb_vends` — the auditor's correction is wrong at HEAD, and it also missed one

The log proposes `:3745`→`:3832`, quoting *"but nothing displays it any more"*.
**That text is at `:4088`, not `:3832`.** `:3832` is a different comment
(`// explicit that no money moved; the ledger has to say the same thing`).

**And the row carries a SECOND citation the log does not mention**, because it
is the named form the checker was blind to: the cell says
*"`sbVendorPaidYTD()` at `sairnbiz.html:3873`"*. At HEAD
`function sbVendorPaidYTD(){` is at **`:4129`**.

    sb_vends reg:201
      :3745                  -> :4088    the "nothing displays it any more" comment
      sairnbiz.html:3873     -> :4129    function sbVendorPaidYTD(){

**That second one is the point of item 3.** A hand-read by the auditor and a
mechanical sweep both missed it — the auditor because it was not in the series
being read, the tool because it could not see the form at all.

**Part B of #745 is NOT re-derived here and I am not applying it.** It refers
to *"the 59 mechanically-resolved rows across 41 resources from the prior
round's item 4, and the earlier queue's original-46 corrections … delivered in
chat and not re-pasted here."* Those are not in the log entry and not in this
repo. **Unavailable, named, not guessed.**

---

## 4. Item 8 — twelve log entries, 24 pairs, all verified at HEAD

**Every one holds.** For all 18 rows: the register row has not moved
(`row-matches=True`), the old citation is still there, the new one is not, and
the target line's content matches the auditor's description.

| # | Resource | Row | Repoint(s) — verified at HEAD |
|---|---|---|---|
| 788 | `sd_crm` | `:175` | `:30664`→`:31357` `var _crmReadFailed=false;` · `:30764`→`:31440` the Pipeline-KPI sum · `:30816`→`:31492` `val:parseFloat(…'crm-val'…)` |
| 789 | `sb_train` | `:200` | `:1976`→`:2162` seed row · `:2128`→`:2238` `function checkAttentionItems() {` · `:4507`→`:4766` `function saveCertRenewal(){` |
| 795 | `sv_boarding` | `:574` | `:8579`→`:8832` `function addBoarding(){` |
| 796 | `sd_sms_log` | `:164` | `:32789`→`:32859` |
| 796 | `sd_email_threats` | `:165` | `:38217`→`:38287` |
| 802 | `sf_vehicle_service` | `:379` | `:6140`→`:6936` `odometer:Number($('vh-odo')…)` · `:6220`→`:6966` `if(odo) veh.odometer=odo;` · `:6222`→`:7024` the "at or past their service odometer" render |
| 803 | `sf_district_imports` | `:353` | `:6416`→`:7162` `K_IMPORTS='sf_district_imports'` · `:6747`→`:7493` `st(K_IMPORTS, imports);` · `:7455`→`:7456` `function sfImportReports(){` · `:7516`→`:7517` `function sfClearImports(){` |
| 809 | `sb_bud` | `:190` | `:3748`→`:2182` `st('sb_bud',[` |
| 810 | `sb_exps` | `:191` | `:3469`→`:2656` `function saveExp(){` |
| 816 | `sen_authorizations` | `:553` | `:4929`→`:5069` `async function saveAuthorization(){` |
| 817 | `sc_providers` | `:282` | `:2953`→`:2968` the "QP status is not cosmetic" note |
| 823 | `sb_hire` | `:192` | `:2349`→`:2178` seed row |
| 824 | `sdn_referrals` | `:335` | `:3493`→`:3519` `async function saveReferral(){` |

**#796 is a defect, not just drift, and it is still open.** The log records that
`sd_email_threats` derives risk by a naive `lower.includes('critical')` /
`('high')` / `('medium')` substring match **with no negation handling**, so an
AI response containing *"not a high risk"* stores **High**. That is a live
mis-rating on an A/A row. **Out of scope here** — it is `stonedesk.html`
behaviour, not a citation — and it is the one item in this batch I would put
ahead of every repoint.

---

## 5. Item 9 — rows 82 and 845 were already delivered

**Confirmed, not re-done.** Delivered in the previous batch:

* **Text:** `docs/2026-10-05-register-corrections-hank.md` §6, committed in
  `b9f5807e`'s batch — both rows written out paste-ready, row 82 as a
  retraction of my own false claim, row 845 as a closure.
* **cc flagged:** the shared status registry carried
  *"FOR CC: index rows 82 (mine, retract) and 845 (stale) paste-ready in
  docs/2026-10-05-register-corrections-hank.md sec 6 — you hold
  SAIRN-OPEN-WORK-INDEX.md, not editing it"*.

**Neither has been applied yet** — `docs/SAIRN-OPEN-WORK-INDEX.md` is in cc's
live claim. Nothing further for me to deliver; the text exists and the holder
has been told twice. Re-flagged once more this batch rather than duplicated.

---

## 6. What I will not claim

* **Nothing in §1–§4 is applied.** cc holds the register.
* **I did not read the prose of the other ~150 drifted rows** the expanded
  sweep now surfaces (177 DRIFTED across 444 citations). On the evidence of
  `sb_perf`, `sc_encoder` and `grd_irr_zones`, a substantial fraction will be
  deliberate render/read citations that must NOT be repointed.
* **#745 Part B is unavailable to me** — 59 rows plus an "original-46" set that
  exist only in a chat transcript. Not inferred.
* **I did not verify the `sd_email_threats` mis-rating myself** — I am
  repeating the auditor's re-confirmation and flagging it, not claiming an
  independent read.
* **I read the hover log; I did not audit it.** The entries are the auditor's
  record of its own work, and the hash chain was not verified by me.
