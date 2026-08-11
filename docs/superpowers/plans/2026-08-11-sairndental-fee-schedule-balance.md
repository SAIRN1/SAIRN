# SAIRNdental Fee-Schedule + Checkout Balance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Real per-CDT-code fee-schedule/coverage engine + patient-level
checkout balance, per
`docs/superpowers/specs/2026-08-11-sairndental-fee-schedule-balance-design.md`.

**No SQL migration in this plan.** `dnt_charges`/`dnt_payments` are
already real, generic-jsonb foundation resources — `estimated_insurance_portion`
is a new field inside the existing `data` payload, not a promoted
column (no `EXCLUDE` constraint or fast server-side lookup needs it —
unlike the availability engine's `dnt_appointments`). `dnt_appointments.status`
is already a plain `text` column; `'Completed'` is just a new value,
not a schema change.

## Global Constraints

- `estimated_insurance_portion` is computed once, at charge-creation
  time, and never recomputed on a later coverage-rule change (spec
  §0) — the lookup function runs inside `addCharge()`/`completeVisit()`,
  not inside the balance-display render function.
- Coverage-rule lookup is case-insensitive exact match; no rule found
  → `$0` estimate + a visible, honest message, never a guessed
  percentage (spec §2).
- No delete/void for charges or payments this pass (spec §3).
- No patient-facing balance view — Billing/Appointments panels are
  internal, license-gated only (spec §3).
- `python tools/checkblocks.py sairndental.html` /
  `div_balance_check.py` / `duplicate_global_check.py` clean after
  every change.
- Push Protocol: full local checks before push, real live-verify
  after.

---

### Task 1: Charge/payment data layer + fee-schedule math

**Files:** Modify `sairndental.html`

- [ ] **Step 1: Data accessors**

```js
function charges(){return ld('dnt_charges_list',[]);}
function payments(){return ld('dnt_payments_list',[]);}
```

- [ ] **Step 2: Coverage lookup — pure, deterministic, honest on a miss**

```js
// Case-insensitive exact match only -- no fuzzy matching (spec §2).
// Returns {found:false, coveragePercent:0} on a miss -- caller must
// show the honest no-rule-found message, never silently guess.
function lookupCoverage(payer, procedureTypeId){
  var rules=coverageRules();
  var payerNorm=(payer||'').trim().toLowerCase();
  var match=rules.find(function(r){
    return (r.payer||'').trim().toLowerCase()===payerNorm && r.procedure_type_id===procedureTypeId;
  });
  return match ? {found:true, coveragePercent:Number(match.coverage_percent)||0} : {found:false, coveragePercent:0};
}
// Locked-in at call time -- caller stores the result on the charge
// record permanently (spec §0). Never called again for an existing
// charge.
function computeEstimatedInsurance(amount, payer, procedureTypeId){
  var cov=lookupCoverage(payer, procedureTypeId);
  return { amount: Math.round(amount * (cov.coveragePercent/100) * 100)/100, found: cov.found };
}
```

- [ ] **Step 3: Balance computation**

```js
function patientBalance(patientId){
  var myCharges=charges().filter(function(c){return c.patient_id===patientId;});
  var myPayments=payments().filter(function(p){return p.patient_id===patientId;});
  var totalCharges=myCharges.reduce(function(s,c){return s+(Number(c.amount)||0);},0);
  var totalEstInsurance=myCharges.reduce(function(s,c){return s+(Number(c.estimated_insurance_portion)||0);},0);
  var totalPayments=myPayments.reduce(function(s,p){return s+(Number(p.amount)||0);},0);
  var balanceDue=(totalCharges-totalEstInsurance)-totalPayments;
  return {totalCharges:totalCharges, totalEstInsurance:totalEstInsurance, totalPayments:totalPayments, balanceDue:balanceDue};
}
```

- [ ] **Step 4: Charge/payment add functions**

```js
async function addChargeEntry(patientId, appointmentId, procedureTypeId, amount){
  var pt=patients().find(function(p){return p.id===patientId;});
  var est=computeEstimatedInsurance(amount, pt?pt.insurance_payer:'', procedureTypeId);
  var rec={id:newId('CH'), patient_id:patientId, appointment_id:appointmentId||'', procedure_type_id:procedureTypeId,
    amount:amount, estimated_insurance_portion:est.amount, date:dntLocalToday()};
  var list=charges();list.push(rec);st('dnt_charges_list',list);
  var syncResult=await sdnData('write','dnt_charges',rec);
  return {rec:rec, coverageFound:est.found, syncResult:syncResult};
}
async function addPaymentEntry(patientId, amount, method){
  var rec={id:newId('PM'), patient_id:patientId, amount:amount, method:method, date:dntLocalToday()};
  var list=payments();list.push(rec);st('dnt_payments_list',list);
  var syncResult=await sdnData('write','dnt_payments',rec);
  return {rec:rec, syncResult:syncResult};
}
```

- [ ] **Step 5: Node harness verification**

Real test cases: coverage found vs. not found, locked-estimate value
matches a hand computation, balance math across multiple
charges/payments including a partial payment.

- [ ] **Step 6: Syntax-check + commit**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
```

```
git add sairndental.html
git commit -m "feat: SAIRNdental -- fee-schedule/coverage lookup + charge/payment data layer

..."
```

---

### Task 2: Billing panel

**Files:** Modify `sairndental.html`

- [ ] **Step 1: Panel UI**

Patient selector → real computed balance breakdown (`patientBalance()`),
itemized charge list (amount / locked estimated portion / resulting
patient responsibility / date), itemized payment list, Add Charge form
(procedure-type select auto-fills `default_fee` into an editable
amount field via an `onchange` handler; on submit, calls
`addChargeEntry()` and — if `coverageFound` is false — shows the
honest "No coverage rule on file... showing full amount due" message,
spec §2), Add Payment form (amount, method select).

- [ ] **Step 2: Syntax-check + commit**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
```

```
git add sairndental.html
git commit -m "feat: SAIRNdental -- Billing panel (real patient balance, charge/payment entry)

..."
```

---

### Task 3: Appointments panel + Complete Visit

**Files:** Modify `sairndental.html`

- [ ] **Step 1: Appointments panel**

Lists `status:'Confirmed'` appointments (distinct from the existing
Pending Requests panel, which stays focused on triage), with a
"Complete Visit" button per row.

- [ ] **Step 2: Complete Visit flow**

Opens a pre-filled charge form (procedure type + `default_fee` from
the appointment's own `procedure_type_id`, patient locked to the
appointment's `patient_id`) — **does not create the charge or change
the appointment's status until the form is explicitly submitted**
(spec §0's "never silently auto-committed" requirement). On submit:
calls `addChargeEntry()` with the appointment's real `id` as
`appointment_id`, then sets the appointment's `status` to
`'Completed'` via the same `setAppointmentStatus()`-style write
already used by Confirm/Reject.

- [ ] **Step 3: Syntax-check + commit**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
```

```
git add sairndental.html
git commit -m "feat: SAIRNdental -- Appointments panel + Complete Visit (auto-fills, never auto-commits, the linked charge)

..."
```

---

### Task 4: End-to-end verification, push, live-verify

- [ ] **Step 1:** Full local re-check of every changed file.
- [ ] **Step 2:** Push.
- [ ] **Step 3:** Real interaction test: add a coverage rule, add a
  charge for a matching payer/procedure, confirm the displayed
  estimated portion matches a hand computation.
- [ ] **Step 4:** Locked-estimate regression test (the actual test for
  spec §0): change the coverage rule's percentage after the charge
  above exists, confirm that charge's stored
  `estimated_insurance_portion` did NOT change, confirm a *new* charge
  created afterward uses the new percentage.
- [ ] **Step 5:** No-rule-found test: add a charge for a payer/procedure
  combination with no coverage rule, confirm the honest message
  appears and the estimate is `$0` (full amount shown due).
- [ ] **Step 6:** Complete Visit regression test (the actual test for
  spec §0's second decision): confirm the pre-filled form appears,
  confirm no charge exists and the appointment is still `Confirmed`
  until the form is submitted, confirm both the charge and the
  `Completed` status land together after submission.
- [ ] **Step 7:** Real balance test: multiple charges + a partial
  payment for one patient, confirm the displayed balance due matches
  a hand computation.
- [ ] **Step 8:** Update
  `docs/superpowers/specs/2026-08-11-sairndental-fee-schedule-balance-design.md`'s
  status, with commit SHAs.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks 1-4
is written**, per your instruction.

## After this plan

Two feature areas remain per the original design spec: automated
email reminders (spec §5 of the top-level design — needs a real email
provider account Michael provisions before it can be built against
anything real) and the denial/A/R/revenue bridge from SAIRNcode
(spec §6 — largely direct reuse, no dependency on this plan).
