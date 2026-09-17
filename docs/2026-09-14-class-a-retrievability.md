# Item 39c — the nine unassessed Class A resources, answered

**Written 2026-09-14 (Hank).** Closes the denominator Fourth left open in
`docs/2026-09-14-record-retention-and-retrievability.md`: *"Nine of the eleven
Class A resources are UNASSESSED for retrievability, not clean."*

The question is not whether the rows exist. It is whether somebody who is
**asked to produce them** can. Fourth answered it for `sv_audit_log` by hand and
named the method the other nine needed — derive the **backing variable** from
the storage key and ask whether that variable reaches a renderer, rather than
counting references to the key string.

That method was run. **The headline is a negative, and it is reported first
because it is the result:** all nine could be seen on screen and `sv_audit_log` was the only one that could not.

**CORRECTED 2026-09-16 (CC): IT NOW CAN, AND SO THE HEADLINE ABOVE IS NO LONGER THE RESULT.** Hank shipped a Dosing Audit Trail panel with its own Export CSV. **Live-verified rather than read from a commit:** `https://sairn.vercel.app/sairnvet` answers 200 at 818,332 bytes and the DEPLOYED source carries `panel-doseaudit`, "Dosing Audit Trail" and `svExportDoseAudit`. **Eleven of eleven on screen, and eight of eleven as a file.** The original sentence is kept above rather than rewritten, because a document that quietly becomes right reads as though it was never wrong.

But the question splits in two, and the second half is where the finding is.

---

## The answer, both halves

| App | Resource | On screen? | By what | As a **file**? |
|---|---|---|---|---|
| sairndental | `dnt_charges` | yes | `rBilling()` | yes — `exportDataset('charges')` **(added 2026-09-14)** |
| sairndental | `dnt_payments` | yes | `rBilling()` | yes — `exportDataset('payments')` **(added 2026-09-14)** |
| sairndental | `dnt_credentials` | yes | `rCredentials()` | yes — `exportDataset('credentials')` |
| sairndental | `dnt_vendor_orders` | yes | `vShowSpendReport()` | yes — `exportDataset('vendororders')` **(added 2026-09-14)** |
| sairnroofing | `rf_certifications` | yes | `rfRenderCertBoard()`, `panel-certifications` | yes — `'certifications'` |
| sairnroofing | `rf_claim_photos` | yes | `rfLoadClaimPhotos()` | yes — `'claim_photos'` **(added 2026-09-14)** |
| sairnroofing | `rf_proposals` | yes | the job panel's proposal chain | yes — `'proposals'` |
| sairncare | `alf_staff_credentials` | yes | `crRefresh()` → `rCredentials()` | **no** — app has no export machinery |
| sairnmechanical | `mech_credentials` | yes | `mechCredRefresh()` → `mechRenderAccess()` | **no** — app has no export machinery |
| sairnvet | `sv_controlled` | yes | `panel-controlled` | **yes** — `svExportControlled()`, on the panel's own "Export CSV" button **(added 2026-09-16, `ba8843df`)** |
| sairnvet | `sv_audit_log` | **yes** — `panel-doseaudit`, "Dosing Audit Trail" **(added 2026-09-16, Hank)** | `svRenderDoseAudit()` | **yes** — `svExportDoseAudit()` **(same panel)** |

**Eleven of eleven on screen. Nine of eleven as a file** (was eight, and seven before that; `sv_audit_log` closed BOTH halves on 2026-09-16 and `sv_controlled` closed the file half the same day) — three when this was written, and the four gaps below were closed the same day. The remaining **two** are in apps with no export machinery at all.

**`sv_controlled`'s row said "no — app has no export machinery" for most of 2026-09-16, while the export was already in the file.** It is worth recording which way that error ran. `tools/export_coverage_check.py` had two states where there are three: it could find an export REGISTRY or not, and the absence of one was printed as the absence of export MACHINERY. SAIRNvet has never had a registry and by that morning had two real CSV writers on two real buttons, so the tool reported a missing feature that existed, this table copied the tool, and `tests/run_export_coverage_probe.py` section E pinned the copy. **A pin makes an answer stable, not true** — all three artefacts agreed with each other and none of them agreed with the app. The tool now reports `NO REGISTRY TO READ` as its own third state and this row is hand-verified against `sairnvet.html` (`svExportControlled()` at the "Export CSV" button on `panel-controlled`), not against the tool.

---

## The finding: a record you can look at is not a record you can hand over

**Fixed 2026-09-14, after this was written.** The four gaps below were all in an app whose export registry already existed, so each was a missing row rather than a missing feature, and each is now built:

| Gap | What was added |
|---|---|
| `dnt_charges` | a `charges` dataset — one row per charge, the charge id kept, patient and procedure resolved to names **with the raw ids beside them**, plus the estimated insurance portion. Export CSV on the Billing panel. |
| `dnt_payments` | a `payments` dataset — one row per payment with id, patient, method and amount. Export CSV beside it. |
| `dnt_vendor_orders` | a `vendororders` dataset — one row per order, line items flattened into one cell the way `credentials` already flattens its type-specific half. The header states that the local archive is capped at 200 and the server is not. |
| `rf_claim_photos` | a `claim_photos` report with its own per-claim fan-out loader, because the server requires `payload.claim_id` and gates each read on the claim's own assignment rule. A claim that refuses is NAMED in the fan-out note. |

**The image bytes are deliberately not in the roofing CSV, and the file says so rather than leaving it to be discovered.** `photo_base64` is a full data URL, routinely megabytes; a CSV cell holding one is not evidence anybody can open, and a few hundred is a file nothing will load. Each row carries `photo_present` and `photo_chars` instead, so the export is a complete evidence inventory that states what it does not itself contain — the same call the proposals export already makes for a 1.5MB signature, and records.

Held by `tests/sairndental_ledger_export.js` (8 arms, which RUN every column closure over seeded data rather than reading them) and `tests/roofing_claim_photo_export.js` (8 arms driving the fan-out). Three sabotage controls: pointing `charges` at the ageing buckets takes 3 arms red, dropping the fan-out's failure list takes 1, and swapping the inventory columns for a `photo_base64` column takes 1. Each asserted its anchor first and each file was restored byte-identical.

### What the gaps were

An inspector, an auditor or a subpoena asks for a **record**, not a screenshot.
"Can staff look it up" and "can this practice produce what it was asked for" are
different questions and only the second one has a deadline attached.

**Four of these sat in an app whose export registry ALREADY EXISTED and did not
carry them.** That is a gap in a built mechanism, not a missing feature:

  * `dnt_charges` and `dnt_payments` — SAIRNdental's append-only money records.
    Nine datasets have an Export CSV button. These two do not. The `ageing`
    export is a **derived aggregate** — buckets computed from charges and
    payments — and the app's own comment says why it is derived rather than
    stored. **A bucket total is not the append-only row-level record**, and
    substituting one for the other is exactly the kind of near-miss that reads
    as coverage.
  * `dnt_vendor_orders` — the registry exports `supplies`, which is
    `dnt_supplies`, a different resource.
  * `rf_claim_photos` — the registry exports `claims`, which is `rf_claims`.
    The photo evidence attached to a claim is not in it.

The other **two** (`alf_staff_credentials`, `mech_credentials`) sit in apps with
**no export path at all** — no `createObjectURL`, no `text/csv`, anywhere in
either file, verified by grep on 2026-09-16 and by the checker's own `NONE`
state. That is a larger piece of work and a different decision, so the two are
counted separately rather than summed into one number.

`sv_controlled` and `sv_audit_log` were the third and fourth of these and both
are closed; SAIRNvet has export machinery and no registry, which is the case
the checker used to mislabel and now reports as `NO REGISTRY TO READ`.

`tools/export_coverage_check.py` checks this half mechanically. It **failed on
its first day** on those four and **passes now**; the probe's gating direction
is driven against a PLANTED registry rather than against the app, so closing a
real gap can never quietly disarm it. Held by
`tests/run_export_coverage_probe.py`, whose section E pins all eleven verdicts
by name so a later change to any app's registry flips an arm, and whose section C drives the finding text through
`report_only_checks.by_exit` so the four NAMES survive rather than collapsing
to the string `exit 1`.

---

## The method, and the two detectors that were wrong before this one

Both wrong versions are recorded because each failed in a way the scoping doc
predicted, and the second failure is the reason the on-screen half is **not**
shipped as a tool.

**v1 — bind the key string and `return ld(KEY)` accessors, then check
call-graph reachability from a nav root.** Reported `alf_staff_credentials` as
having no reader. It has one: `crRefresh()` calls `alfCredRead()` (which names
the key), stashes the result in the file-scope variable `_crRecords`, and
`rCredentials()` renders a full table from `_crRecords` — which never mentions
the key. **This is the miss the scoping doc predicted for a key-string method,
reproduced exactly.** It also reported `rf_certifications` and `rf_proposals` as
having no renderer, and both have panels.

**v2 — bind transitively.** Promoted any function that *referenced* a bound
name into a carrier, so every caller of every reader cascaded in and most of
SAIRNdental was bound. 41 "renderers" for `dnt_payments`, including `dntLogin`.

**v3 — separate the two ideas.** A *carrier* is an identifier whose **value** is
the data: the key, a function that names the key or calls a carrier function,
and a file-scope variable assigned inside such a function. Merely **reading** a
carrier variable does not make you one — which is what stops the cascade, and is
also what a renderer does. v3 gives exactly `rCredentials` for
`alf_staff_credentials`, matching the hand read.

**v3 still over-binds in SAIRNdental**, because a generic sync layer names every
storage key and everything it touches inherits the binding. So the on-screen
column above is **hand-verified against the source**, with v3 used as the
second, structurally different method rather than as the answer. Two methods
agreeing is the evidence; neither alone is.

---

## What is NOT claimed

* **Role scoping is not read.** `EXPORTABLE` means a code path exists, not that
  the person asking is allowed to use it. Both registries carry per-role gates
  (`'Management and estimators export the whole roster's credentials. Everyone
  else exports only their own.'`) and this work does not evaluate them.
* **No live check.** Nothing was fetched from a provisioned licence; every
  answer is from source. Whether any real practice holds rows in these tables
  was not checked.
* **Retention is still unanswered and is still not a technical question.**
  Fourth's point stands: until somebody states how long each of these must
  survive and under whose rule, "did the record survive its retention period"
  is not a checkable question, and a checker built against an unstated period
  would be inventing the rule it enforces.
* **Nothing was changed in any app.** No export was added, no panel built.
