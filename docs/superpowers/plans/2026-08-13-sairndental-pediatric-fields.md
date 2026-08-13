# SAIRNdental Pediatric Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add guardian/parent contact fields to SAIRNdental's patient record, auto-shown and required when the patient's DOB implies a minor, so reminders/billing/consent for pediatric patients have a real contact to reach.

**Architecture:** Four new optional string fields on the existing `dnt_patients` client-side record object (no SQL migration — `dnt_patients` is a JSONB blob table). One shared `isMinorPatient(dob)` helper computes minor status from DOB and is called from both the Add Patient form's live show/hide toggle plus its save-time validation, and from the Patients table's row renderer — a single source of truth for the age math. All changes are confined to `sairndental.html`.

**Tech Stack:** Vanilla JS, single-file client app (no build step, no test runner — verified via `python tools/checkblocks.py sairndental.html` and manual browser/console checks, matching this file's existing convention).

## Global Constraints

- Guardian fields **supplement**, never replace, the patient's own `phone`/`email` fields — both remain visible and usable for every patient regardless of minor status.
- Minor status is **auto-computed from `dob`** (age < 18 as of today) via one shared helper, `isMinorPatient(dob)` — no separate manual minor flag anywhere.
- An empty/unset `dob` is treated as **not** a minor (`isMinorPatient('')` returns `false`) — matches the form's existing behavior where DOB is optional; a patient with no DOB is never blocked from saving and never has guardian fields forced on them.
- When `isMinorPatient(dob)` is true at save time, `addPatient()` **blocks save** (toast, no throw) unless `guardian_name` is non-empty AND at least one of `guardian_phone`/`guardian_email` is non-empty. Adult patients get no new validation.
- `guardian_relationship` is a `<select>` with options Mother / Father / Legal Guardian / Other — matches this file's existing `<select>` pattern (e.g. `pm-add-method` at `sairndental.html:463`).
- No edit-patient flow is introduced. No changes to reminders, billing, or consent-document generation. No SQL/server-side validation of the minor-requires-guardian rule.
- Never bulk find-replace — every edit below is a targeted, unique-context change.
- `python tools/checkblocks.py sairndental.html` must report `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0` after every step that touches the file.

---

## File Structure

| File | Responsibility for this feature |
|---|---|
| `sairndental.html` | `isMinorPatient()` helper (new); Add Patient form gets a new hidden-by-default guardian field group wired to `pt-add-dob`'s change event; `addPatient()` reads/validates/persists the four new fields; `rPatients()` renders the new Guardian table column. |

Line numbers below are as of this plan's base commit and will drift as edits land — every edit is anchored to unique surrounding code, not the raw number.

---

### Task 1: Guardian fields — helper, form, validation, and display

**Files:**
- Modify: `sairndental.html` (Add Patient form ~L257-274, `addPatient()` ~L677-689, `rPatients()` ~L668-676)

**Interfaces:**
- Produces: `function isMinorPatient(dob)` — returns `boolean`. Takes a date string (or empty string) in the same format `pt-add-dob`'s `<input type="date">` produces (`YYYY-MM-DD`) or a patient record's stored `p.dob` (same format, since it's saved directly from that input's `.value`).
- Consumed by: this task's own `addPatient()` validation and `rPatients()` row rendering — no other task/file depends on it.

- [ ] **Step 1: Add the `isMinorPatient()` helper**

Find (the exact current start of `addPatient()`, so the helper lands immediately above the function that will use it):

```js
async function addPatient(){
  var name=$('pt-add-name').value.trim();
  if(!name){toast('Patient name required');return;}
```

Replace with:

```js
// Pediatric fields (2026-08-13): single source of truth for minor status,
// used by both the Add Patient form's live guardian-field toggle and
// addPatient()'s save-time validation, plus rPatients()'s table column --
// avoids duplicating the age math in three places where it could drift.
// Empty/unset dob is NOT a minor, matching this form's existing behavior
// where DOB is optional and never blocks saving an adult patient.
function isMinorPatient(dob){
  if(!dob)return false;
  var b=new Date(dob),today=new Date();
  var age=today.getFullYear()-b.getFullYear();
  var m=today.getMonth()-b.getMonth();
  if(m<0||(m===0&&today.getDate()<b.getDate()))age--;
  return age<18;
}
async function addPatient(){
  var name=$('pt-add-name').value.trim();
  if(!name){toast('Patient name required');return;}
```

- [ ] **Step 2: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 3: Add the guardian field group to the Add Patient form, hidden by default, toggled by DOB change**

Find (the exact current form block):

```html
        <div class="card"><div class="ch"><div class="ct">Add Patient</div></div><div class="cb">
          <div class="fr">
            <div class="fg"><label>Name</label><input type="text" id="pt-add-name" placeholder="Full name"></div>
            <div class="fg"><label>Date of Birth</label><input type="date" id="pt-add-dob"></div>
          </div>
          <div class="fr">
            <div class="fg"><label>Phone</label><input type="text" id="pt-add-phone" placeholder="(555) 555-5555"></div>
            <div class="fg"><label>Email</label><input type="email" id="pt-add-email" placeholder="patient@example.com"></div>
          </div>
          <div class="fr">
            <div class="fg"><label>Insurance Payer</label><input type="text" id="pt-add-payer" placeholder="e.g. Delta Dental"></div>
            <div class="fg"><label>Member ID</label><input type="text" id="pt-add-memberid" placeholder="Member ID"></div>
          </div>
          <button class="btn bp" onclick="addPatient()">Add Patient</button>
        </div></div>
```

Replace with:

```html
        <div class="card"><div class="ch"><div class="ct">Add Patient</div></div><div class="cb">
          <div class="fr">
            <div class="fg"><label>Name</label><input type="text" id="pt-add-name" placeholder="Full name"></div>
            <div class="fg"><label>Date of Birth</label><input type="date" id="pt-add-dob" onchange="onPtDobChange()"></div>
          </div>
          <div class="fr">
            <div class="fg"><label>Phone</label><input type="text" id="pt-add-phone" placeholder="(555) 555-5555"></div>
            <div class="fg"><label>Email</label><input type="email" id="pt-add-email" placeholder="patient@example.com"></div>
          </div>
          <div class="fr">
            <div class="fg"><label>Insurance Payer</label><input type="text" id="pt-add-payer" placeholder="e.g. Delta Dental"></div>
            <div class="fg"><label>Member ID</label><input type="text" id="pt-add-memberid" placeholder="Member ID"></div>
          </div>
          <!-- Pediatric fields (2026-08-13): hidden unless pt-add-dob implies
               a minor (see onPtDobChange()/isMinorPatient()) -- supplements,
               never replaces, the patient's own phone/email fields above. -->
          <div class="fr" id="pt-add-guardian-group" style="display:none">
            <div class="fg"><label>Guardian Name</label><input type="text" id="pt-add-guardian-name" placeholder="Full name"></div>
            <div class="fg"><label>Relationship</label><select id="pt-add-guardian-relationship"><option>Mother</option><option>Father</option><option>Legal Guardian</option><option>Other</option></select></div>
          </div>
          <div class="fr" id="pt-add-guardian-group2" style="display:none">
            <div class="fg"><label>Guardian Phone</label><input type="text" id="pt-add-guardian-phone" placeholder="(555) 555-5555"></div>
            <div class="fg"><label>Guardian Email</label><input type="email" id="pt-add-guardian-email" placeholder="guardian@example.com"></div>
          </div>
          <button class="btn bp" onclick="addPatient()">Add Patient</button>
        </div></div>
```

- [ ] **Step 4: Add the `onPtDobChange()` toggle function**

Find (the `isMinorPatient()` helper just added in Step 1, to anchor the new function immediately after it):

```js
function isMinorPatient(dob){
  if(!dob)return false;
  var b=new Date(dob),today=new Date();
  var age=today.getFullYear()-b.getFullYear();
  var m=today.getMonth()-b.getMonth();
  if(m<0||(m===0&&today.getDate()<b.getDate()))age--;
  return age<18;
}
async function addPatient(){
```

Replace with:

```js
function isMinorPatient(dob){
  if(!dob)return false;
  var b=new Date(dob),today=new Date();
  var age=today.getFullYear()-b.getFullYear();
  var m=today.getMonth()-b.getMonth();
  if(m<0||(m===0&&today.getDate()<b.getDate()))age--;
  return age<18;
}
function onPtDobChange(){
  var show=isMinorPatient($('pt-add-dob').value)?'grid':'none';
  $('pt-add-guardian-group').style.display=show;
  $('pt-add-guardian-group2').style.display=show;
}
async function addPatient(){
```

Note: `'grid'` matches this file's real `.fr` CSS rule (`sairndental.html:101`: `.fr{display:grid;grid-template-columns:1fr 1fr;gap:12px;}`) — confirmed directly, not assumed.

- [ ] **Step 5: Wire validation and persistence into `addPatient()`**

Find (the exact current function, immediately after Step 1's helper insertion):

```js
async function addPatient(){
  var name=$('pt-add-name').value.trim();
  if(!name){toast('Patient name required');return;}
  var rec={id:newId('PT'),name:name,dob:$('pt-add-dob').value,phone:$('pt-add-phone').value.trim(),
    email:$('pt-add-email').value.trim(),insurance_payer:$('pt-add-payer').value.trim(),
    insurance_member_id:$('pt-add-memberid').value.trim(),insurance_group_number:'',insurance_plan_type:'',
    created_at:dntLocalToday()};
  var list=patients();list.push(rec);st('dnt_patients_list',list);
  rPatients();
  ['pt-add-name','pt-add-dob','pt-add-phone','pt-add-email','pt-add-payer','pt-add-memberid'].forEach(function(id){$(id).value='';});
  var syncResult=await sdnData('write','dnt_patients',rec);
  toast(syncResult?'Patient added':'Saved on this device only -- server sync not yet enabled for this app',syncResult?3000:5000);
}
```

Replace with:

```js
async function addPatient(){
  var name=$('pt-add-name').value.trim();
  if(!name){toast('Patient name required');return;}
  var dob=$('pt-add-dob').value;
  var gName=$('pt-add-guardian-name').value.trim();
  var gRel=$('pt-add-guardian-relationship').value;
  var gPhone=$('pt-add-guardian-phone').value.trim();
  var gEmail=$('pt-add-guardian-email').value.trim();
  if(isMinorPatient(dob)&&(!gName||(!gPhone&&!gEmail))){
    toast('Guardian name and at least one contact method (phone or email) are required for a minor patient');
    return;
  }
  var rec={id:newId('PT'),name:name,dob:dob,phone:$('pt-add-phone').value.trim(),
    email:$('pt-add-email').value.trim(),insurance_payer:$('pt-add-payer').value.trim(),
    insurance_member_id:$('pt-add-memberid').value.trim(),insurance_group_number:'',insurance_plan_type:'',
    guardian_name:gName,guardian_relationship:gRel,guardian_phone:gPhone,guardian_email:gEmail,
    created_at:dntLocalToday()};
  var list=patients();list.push(rec);st('dnt_patients_list',list);
  rPatients();
  ['pt-add-name','pt-add-dob','pt-add-phone','pt-add-email','pt-add-payer','pt-add-memberid',
   'pt-add-guardian-name','pt-add-guardian-phone','pt-add-guardian-email'].forEach(function(id){$(id).value='';});
  $('pt-add-guardian-relationship').selectedIndex=0;
  onPtDobChange();
  var syncResult=await sdnData('write','dnt_patients',rec);
  toast(syncResult?'Patient added':'Saved on this device only -- server sync not yet enabled for this app',syncResult?3000:5000);
}
```

Note: `onPtDobChange()` is called again after the field reset so the now-empty DOB field correctly re-hides the guardian group for the next entry, rather than leaving it visibly shown from the just-submitted patient.

- [ ] **Step 6: Add the Guardian column to the Patients table**

Find (the exact current table header and row template):

```html
          <table id="patients-table"><thead><tr><th>Name</th><th>DOB</th><th>Phone</th><th>Payer</th><th>Member ID</th><th></th></tr></thead><tbody id="patients-tbody"></tbody></table>
```

Replace with:

```html
          <table id="patients-table"><thead><tr><th>Name</th><th>DOB</th><th>Phone</th><th>Payer</th><th>Member ID</th><th>Guardian</th><th></th></tr></thead><tbody id="patients-tbody"></tbody></table>
```

Then find (the exact current row template in `rPatients()`):

```js
    return '<tr><td>'+H(p.name)+'</td><td>'+H(p.dob||'--')+'</td><td>'+H(p.phone||'--')+'</td><td>'+H(p.insurance_payer||'--')+'</td><td>'+H(p.insurance_member_id||'--')+'</td>'+
```

Replace with:

```js
    return '<tr><td>'+H(p.name)+'</td><td>'+H(p.dob||'--')+'</td><td>'+H(p.phone||'--')+'</td><td>'+H(p.insurance_payer||'--')+'</td><td>'+H(p.insurance_member_id||'--')+'</td>'+
      '<td>'+H(isMinorPatient(p.dob)&&p.guardian_name?p.guardian_name+(p.guardian_relationship?' ('+p.guardian_relationship+')':''):'--')+'</td>'+
```

- [ ] **Step 7: Run syntax check**

Run: `python tools/checkblocks.py sairndental.html`
Expected: `TOTAL_BLOCKS:1`, `FAILED_BLOCKS:0`.

- [ ] **Step 8: Manual verification (browser console, matching this app's existing no-automated-test convention)**

With the app open in a browser to the Patients panel:

```js
// Scenario 1: adult patient, no DOB -- no guardian fields, saves clean
$('pt-add-name').value='Adult NoDOB';
addPatient();
// Expected: toast "Patient added" (or the local-save fallback), guardian group stays display:none throughout, table row shows '--' in Guardian column.

// Scenario 2: adult patient, real adult DOB -- guardian group stays hidden
$('pt-add-name').value='Adult WithDOB';
$('pt-add-dob').value='1990-01-01'; onPtDobChange();
// Expected: pt-add-guardian-group and pt-add-guardian-group2 remain style.display 'none'.
addPatient();
// Expected: saves clean, table row shows '--' in Guardian column.

// Scenario 3: minor patient, DOB implies age < 18, no guardian info -- blocked
$('pt-add-name').value='Minor NoGuardian';
var d=new Date(); d.setFullYear(d.getFullYear()-10);
$('pt-add-dob').value=d.toISOString().slice(0,10); onPtDobChange();
// Expected: pt-add-guardian-group/group2 now visible (style.display 'grid').
addPatient();
// Expected: toast "Guardian name and at least one contact method (phone or email) are required for a minor patient", no new row added to the table.

// Scenario 4: minor patient, guardian name + phone only (no email) -- allowed
$('pt-add-guardian-name').value='Jane Doe';
$('pt-add-guardian-phone').value='555-111-2222';
addPatient();
// Expected: saves clean, table row shows "Jane Doe (Mother)" (or whichever relationship option was selected) in Guardian column.

// Scenario 5: confirm isMinorPatient() directly for a sanity check on the boundary
isMinorPatient(new Date(new Date().setFullYear(new Date().getFullYear()-18)).toISOString().slice(0,10)); // exactly 18 today -> false
isMinorPatient(new Date(new Date().setFullYear(new Date().getFullYear()-17)).toISOString().slice(0,10)); // 17 -> true
```

Expected: all five scenarios match their stated expectations. Clean up test rows afterward via each row's existing Remove button (`removePatient()`).

- [ ] **Step 9: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- pediatric guardian/parent contact fields, auto-shown and required for minor patients"
```

---

## Self-Review Notes

- **Spec coverage:** every "In scope" bullet from the design spec has a corresponding step above — data model fields (Step 5), minor auto-detection (Step 1), live form toggle (Steps 3-4), save-time validation (Step 5), and table display (Step 6). Every "Explicitly out of scope" item (no edit flow, no reminders/billing wiring, no SQL validation) has no corresponding step, confirming nothing crept in.
- **Placeholder scan:** no TBD/TODO — every step shows real code matching the actual current file content (re-read from the real repo file immediately before writing this plan) or a real runnable check with a stated expected result. Step 4's toggle display value was verified directly against `.fr`'s real CSS rule rather than assumed.
- **Type/name consistency:** `isMinorPatient(dob)` (Step 1) is called with identical name/signature in Step 4 (`onPtDobChange()`), Step 5 (`addPatient()`), and Step 6 (`rPatients()`'s row template). Field IDs (`pt-add-guardian-name`/`-relationship`/`-phone`/`-email`) introduced in Step 3 are consumed with identical IDs in Steps 4-5. Record field names (`guardian_name`/`guardian_relationship`/`guardian_phone`/`guardian_email`) match exactly between Step 5's write and Step 6's read.
