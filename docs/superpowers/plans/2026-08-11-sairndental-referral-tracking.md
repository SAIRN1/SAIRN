# SAIRNdental Referral Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track incoming/outgoing patient referrals between this practice
and external providers, per
`docs/superpowers/specs/2026-08-11-sairndental-referral-tracking-design.md`.

**Architecture:** A new `dnt_referrals` resource — a new Supabase table
(this is the first genuinely new `dnt_*` table since the original
foundation build, so it needs a real migration, not just a client-side
addition), a new `api/sd-data.js` generic-resource registration, and the
standard SAIRNdental client-side triad (accessor + add/status functions,
panel UI, sync integration) that every existing resource already follows.

**Tech Stack:** No new dependencies — reuses this app's existing
`sdnData()`/`ld()`/`st()`/`toast()`/`newId()`/`dntLocalToday()` helpers
and the `dntSyncFromServer()` mechanism built earlier this session.

## Global Constraints

- **Field whitelist is exhaustive — no fee/commission/value field of any
  kind, anywhere, ever, without a fresh legal review** (spec §0, §3):
  `id`, `direction`, `patient_name`, `patient_id`, `external_party`,
  `internal_provider_id`, `date`, `reason`, `status`, `created_at`. This
  is the entire schema, client-side and server-side, in every task below.
- No remove/delete function for referrals (spec §0, §6) — append-only,
  only `status` is ever updated post-creation.
- `patient_id`/`internal_provider_id` are optional; `direction`,
  `patient_name`, `external_party`, `date`, `reason` are required (spec
  §1, §5).
- `dnt_referrals` must be added to `DNT_SYNC_RESOURCES`
  (`sairndental.html:1199-1209`) and `dntSyncFromServer()`'s re-render
  block in the same pass this feature ships, not deferred (spec §0, §4).
- `python tools/checkblocks.py sairndental.html` / `div_balance_check.py`
  / `duplicate_global_check.py` clean after every `sairndental.html`
  change. `node --check api/sd-data.js` after the server change. Push
  Protocol: full local checks before push, real live-verify after.

---

### Task 1: `dnt_referrals` Supabase table + `api/sd-data.js` registration

**Files:**
- Create: `sql/sairndental_referrals_schema.sql`
- Modify: `api/sd-data.js`

**Interfaces:**
- Produces: a live `public.dnt_referrals` table (once the migration is
  run in Supabase — this repo's standing convention is that SQL files
  are committed but run manually, matching every prior `sql/*.sql` file)
  and a `DNT_RESOURCES.dnt_referrals = 'referral_id'` entry — Task 2's
  `sdnData('write','dnt_referrals',rec)`/`sdnData('read','dnt_referrals')`
  calls depend on both existing.

- [ ] **Step 1: Write the migration**

```sql
-- sql/sairndental_referrals_schema.sql
-- New table for SAIRNdental's referral-tracking feature (2026-08-11).
-- Matches every existing dnt_* table's exact shape (see
-- sql/sairndental_data_schema.sql for the pattern this mirrors) --
-- license_hash-scoped, jsonb data payload, 64KB size cap (this
-- resource has no photos/large payloads, the standard cap is
-- appropriate here unlike dnt_appointments' still-open oversized-data
-- question). See
-- docs/superpowers/specs/2026-08-11-sairndental-referral-tracking-design.md.

create table if not exists public.dnt_referrals (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  referral_id text not null, data jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, referral_id), constraint dntrf_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntrf_license on public.dnt_referrals(license_hash);
```

- [ ] **Step 2: Register the resource in `api/sd-data.js`**

In the `DNT_RESOURCES` object (`api/sd-data.js:1733-1738`):

```js
    const DNT_RESOURCES = {
      dnt_patients: 'patient_id', dnt_providers: 'provider_id', dnt_operatories: 'operatory_id',
      dnt_provider_hours: 'provider_hour_id', dnt_procedure_types: 'procedure_type_id',
      dnt_coverage_rules: 'coverage_rule_id', dnt_charges: 'charge_id',
      dnt_payments: 'payment_id', dnt_denial: 'denial_id', dnt_ar: 'ar_id', dnt_revenue: 'revenue_id',
      dnt_referrals: 'referral_id'
    };
```

Also add `dnt_referrals` to the resource allowlist error message
(`api/sd-data.js:178`, the long comma-separated string ending
`...dnt_ar, dnt_revenue, dnt_settings'`) — append `, dnt_referrals`
immediately before the closing `'`.

- [ ] **Step 3: Syntax-check**

```
node --check api/sd-data.js
python -c "print('sql file has no syntax checker in this repo -- read it back once to confirm it matches the pattern exactly')"
```

- [ ] **Step 4: Commit**

```bash
git add sql/sairndental_referrals_schema.sql api/sd-data.js
git commit -m "feat: SAIRNdental -- dnt_referrals table + api/sd-data.js registration"
```

---

### Task 2: Data layer (`referrals()`, `addReferral()`, `setReferralStatus()`)

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: existing `newId()`, `dntLocalToday()`, `ld()`, `st()`,
  `sdnData()`, `toast()`.
- Produces: `referrals()` — Task 3's `rReferrals()` reads this.
  `addReferral()` — Task 3's Add form calls this. `setReferralStatus(id,
  status)` — Task 3's status control calls this exact function with
  exactly these two arguments.

- [ ] **Step 1: Add the accessor**

Immediately after `function payments(){return ld('dnt_payments_list',[]);}`
in `sairndental.html` (locate by content search, not line number):

```js
function referrals(){return ld('dnt_referrals_list',[]);}
```

- [ ] **Step 2: Add `addReferral()` and `setReferralStatus()`**

Immediately after the accessor from Step 1:

```js
// ── REFERRAL TRACKING (2026-08-11) ───────────────────────────────────
// Append-only, matching dnt_charges/dnt_payments' precedent -- no
// remove function. patient_id/internal_provider_id are optional links;
// patient_name/external_party are always independently stored so a
// referral row never breaks if the linked record is later removed
// locally. NO fee/commission/value field exists anywhere in this
// resource -- illegal under the Anti-Kickback Statute + state dental
// board ethics rules (design spec §0/§3). Do not add one.
async function addReferral(){
  var direction=$('rf-add-direction').value;
  var patientName=$('rf-add-patient-name').value.trim();
  var externalParty=$('rf-add-external').value.trim();
  var date=$('rf-add-date').value;
  var reason=$('rf-add-reason').value.trim();
  if(!patientName){toast('Patient name required');return;}
  if(!externalParty){toast('External party required');return;}
  if(!date){toast('Date required');return;}
  if(!reason){toast('Reason required');return;}
  var rec={id:newId('RF'),direction:direction,patient_name:patientName,
    patient_id:$('rf-add-patient').value,external_party:externalParty,
    internal_provider_id:$('rf-add-provider').value,date:date,reason:reason,
    status:'Pending',created_at:dntLocalToday()};
  var list=referrals();list.push(rec);st('dnt_referrals_list',list);
  rReferrals();
  ['rf-add-patient-name','rf-add-external','rf-add-date','rf-add-reason'].forEach(function(id){$(id).value='';});
  $('rf-add-patient').value='';$('rf-add-provider').value='';
  var syncResult=await sdnData('write','dnt_referrals',rec);
  toast(syncResult?'Referral added':'Saved on this device only -- server sync not yet enabled for this app',syncResult?3000:5000);
}
async function setReferralStatus(id,status){
  var list=referrals();
  var r=list.find(function(x){return x.id===id;});
  if(!r){toast('Referral not found');return;}
  r.status=status;
  st('dnt_referrals_list',list);rReferrals();
  var syncResult=await sdnData('write','dnt_referrals',r);
  toast(syncResult?('Referral marked '+status):'Saved on this device only -- server sync not yet enabled for this app',syncResult?3000:5000);
}
```

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

- [ ] **Step 4: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- referral data layer (referrals()/addReferral()/setReferralStatus())"
```

---

### Task 3: Referrals panel UI

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: `referrals()`, `addReferral()`, `setReferralStatus()` from
  Task 2; existing `patients()`, `providers()`, `H()`, `$()`, `nav()`,
  `fillDentalSelects()`.
- Produces: `rReferrals()` — Task 4's `dntSyncFromServer()` calls this
  exact function name.

- [ ] **Step 1: Add the nav button**

In the sidebar (`sairndental.html:220-221`, inside the "Patients"
section, immediately after the Insurance Capture button):

```html
      <button class="sb" id="sb-patients" onclick="nav('patients')"><span class="sico">&#129502;</span>Patients</button>
      <button class="sb" id="sb-icap" onclick="nav('icap')"><span class="sico">&#128248;</span>Insurance Capture</button>
      <button class="sb" id="sb-referrals" onclick="nav('referrals')"><span class="sico">&#128257;</span>Referrals</button>
```

- [ ] **Step 2: Add the panel HTML**

Insert a new panel immediately after `panel-patients` closes (locate the
`</div>` that closes `<div class="panel" id="panel-patients">` by
content search, not line number — it's a large panel, look for the next
`<div class="panel" id="panel-icap">` and insert immediately before it):

```html
      <div class="panel" id="panel-referrals">
        <div class="ph"><div><div class="ptitle">Referrals</div><div class="psub">Incoming and outgoing patient referrals to/from external providers &mdash; record-keeping only, never a mechanism for referral payment (illegal under federal and state law).</div></div>
          <div class="pa"><button class="btn bo bs" onclick="exportPanelCSV('panel-referrals','referrals')">Export CSV</button></div>
        </div>
        <div class="card"><div class="ch"><div class="ct">Add Referral</div></div><div class="cb">
          <div class="fr">
            <div class="fg"><label>Direction</label><select id="rf-add-direction"><option value="incoming">Incoming</option><option value="outgoing">Outgoing</option></select></div>
            <div class="fg"><label>Patient Name</label><input type="text" id="rf-add-patient-name" placeholder="Full name"></div>
          </div>
          <div class="fr">
            <div class="fg"><label>Link to Existing Patient (optional)</label><select id="rf-add-patient"><option value="">(none yet)</option></select></div>
            <div class="fg"><label>External Practice/Provider</label><input type="text" id="rf-add-external" placeholder="e.g. Dr. Jones Oral Surgery"></div>
          </div>
          <div class="fr">
            <div class="fg"><label>This Practice's Provider (optional)</label><select id="rf-add-provider"><option value="">(none)</option></select></div>
            <div class="fg"><label>Date</label><input type="date" id="rf-add-date"></div>
          </div>
          <div class="fg"><label>Reason</label><input type="text" id="rf-add-reason" placeholder="e.g. Root canal consult"></div>
          <button class="btn bp" onclick="addReferral()">Add Referral</button>
        </div></div>
        <div class="card"><div class="ch"><div class="ct">On File</div></div><div class="cb" style="padding:0">
          <table id="referrals-table"><thead><tr><th>Direction</th><th>Patient</th><th>External Party</th><th>Provider</th><th>Date</th><th>Reason</th><th>Status</th></tr></thead><tbody id="referrals-tbody"></tbody></table>
        </div></div>
      </div>
```

- [ ] **Step 3: Add `rReferrals()` and wire it into `nav()`/`fillDentalSelects()`**

`rReferrals()`, immediately after Task 2's `setReferralStatus()`:

```js
function rReferrals(){
  var list=referrals(),pats=patients(),provs=providers();
  var tbody=$('referrals-tbody');
  tbody.innerHTML=list.map(function(r){
    var prov=provs.find(function(p){return p.id===r.internal_provider_id;});
    var statusOpts=['Pending','Scheduled','Completed','Declined'].map(function(s){
      return '<option value="'+s+'"'+(s===r.status?' selected':'')+'>'+s+'</option>';
    }).join('');
    return '<tr><td>'+H(r.direction==='incoming'?'Incoming':'Outgoing')+'</td><td>'+H(r.patient_name)+'</td>'+
      '<td>'+H(r.external_party)+'</td><td>'+H(prov?prov.name:'--')+'</td><td>'+H(r.date)+'</td><td>'+H(r.reason)+'</td>'+
      '<td><select onchange="setReferralStatus(\''+r.id+'\',this.value)">'+statusOpts+'</select></td></tr>';
  }).join('')||'<tr><td colspan="7" style="color:var(--muted);text-align:center">No referrals on file yet</td></tr>';
}
```

In `nav(id)` (`sairndental.html:569-587`), add alongside the other
`if(id===...)` lines:

```js
  if(id==='referrals')rReferrals();
```

In `fillDentalSelects()` (`sairndental.html:616-625`), add two new
dropdown fills alongside the existing ones:

```js
  if($('rf-add-patient'))$('rf-add-patient').innerHTML='<option value="">(none yet)</option>'+ptOpts;
  if($('rf-add-provider'))$('rf-add-provider').innerHTML='<option value="">(none)</option>'+provOpts;
```

- [ ] **Step 4: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

Expected: clean, no duplicate IDs (`sb-referrals`, `panel-referrals`,
`rf-add-direction`, `rf-add-patient-name`, `rf-add-patient`,
`rf-add-external`, `rf-add-provider`, `rf-add-date`, `rf-add-reason`,
`referrals-table`, `referrals-tbody` are all new and unique).

- [ ] **Step 5: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- Referrals panel (add form, status control, CSV export)"
```

---

### Task 4: Sync integration

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: `rReferrals()` from Task 3.
- Produces: no new functions — wires an existing resource into the
  existing sweep.

- [ ] **Step 1: Add to `DNT_SYNC_RESOURCES`**

At `sairndental.html:1199-1209`:

```js
var DNT_SYNC_RESOURCES=[
  ['dnt_patients','dnt_patients_list'],
  ['dnt_providers','dnt_providers_list'],
  ['dnt_operatories','dnt_operatories_list'],
  ['dnt_provider_hours','dnt_hours_list'],
  ['dnt_procedure_types','dnt_procedures_list'],
  ['dnt_coverage_rules','dnt_coverage_list'],
  ['dnt_appointments','dnt_appointments_list'],
  ['dnt_charges','dnt_charges_list'],
  ['dnt_payments','dnt_payments_list'],
  ['dnt_referrals','dnt_referrals_list']
];
```

- [ ] **Step 2: Add `rReferrals()` to the re-render block**

In `dntSyncFromServer()`'s `if(changed){...}` block, add `rReferrals();`
alongside the other render calls.

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

- [ ] **Step 4: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- wire dnt_referrals into the real-sync sweep"
```

---

### Task 5: End-to-end verification, push, live-verify

- [ ] **Step 1:** Confirm the migration has actually been run in
  Supabase before live-testing (this repo's standing convention — SQL
  files are committed but run manually; `dnt_referrals` writes will
  return `NOT_PROVISIONED` until it has). If not yet run, surface this
  plainly rather than assuming — same honest-status discipline as every
  other not-yet-provisioned resource in this app.
- [ ] **Step 2:** Full local re-check: `checkblocks.py` /
  `div_balance_check.py` / `duplicate_global_check.py` on
  `sairndental.html`; `node --check` on `api/sd-data.js`.
- [ ] **Step 3:** Push to `main`.
- [ ] **Step 4:** Live regression test using the real `DNT-PINNACLE-2026`
  demo practice. First, the validation path (spec §7's explicit
  requirement): attempt to submit the Add Referral form with each of
  `rf-add-patient-name`/`rf-add-external`/`rf-add-date`/`rf-add-reason`
  empty in turn, confirm the corresponding toast blocks submission each
  time and no referral is created; confirm leaving both `rf-add-patient`
  and `rf-add-provider` blank does NOT block submission (they're
  optional). Then the happy path: add one incoming and one outgoing
  referral (leaving the optional link fields blank on at least one, and
  set on the other, to cover both), confirm both appear correctly in the
  table with the right direction label, confirm changing status via the
  dropdown persists through a page reload.
- [ ] **Step 5: Stale-link regression test (the actual test for spec
  §5's claim).** Link a referral to an existing test patient via
  `rf-add-patient`, then remove that patient locally via the Patients
  panel's Remove button. Confirm the referral row still shows the
  correct `patient_name` text, not "(unknown patient)" or a blank cell.
- [ ] **Step 6: Sync regression test (the actual test for spec §4/
  Task 4).** In a fresh browser session (cleared localStorage), log into
  the same demo practice, confirm the referrals added in Step 4 appear
  without any extra action — proving `dnt_referrals` genuinely
  participates in the sweep, not just present in code.
- [ ] **Step 7: Field-whitelist regression (the actual test for spec §0/
  §3's legal constraint).** Read back one real synced referral record
  (via a direct `api/sd-data.js` read, the same method used throughout
  this session) and confirm its keys are exactly the §1 whitelist —
  `id`, `direction`, `patient_name`, `patient_id`, `external_party`,
  `internal_provider_id`, `date`, `reason`, `status`, `created_at` —
  nothing else, no amount/fee/value field present.
- [ ] **Step 8:** Delete any test referral/patient records created in
  Steps 4-6 — **note up front, per the already-logged backlog item,
  there is no delete API anywhere on this platform**, so this means
  reporting the exact record IDs for manual Supabase-dashboard deletion,
  the same honest limitation already hit twice this session.
- [ ] **Step 9:** Update
  `docs/superpowers/specs/2026-08-11-sairndental-referral-tracking-design.md`'s
  status line with the real commit SHAs and confirmed-live date.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks 1-5
is written**, per your instruction.
