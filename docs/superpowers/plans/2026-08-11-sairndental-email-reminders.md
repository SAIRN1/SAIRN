# SAIRNdental Automated Email Reminders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Real automated 48h/2h-before email reminders for `Confirmed`
dental appointments, via Resend, on an hourly Vercel Cron, per
`docs/superpowers/specs/2026-08-11-sairndental-email-reminders-design.md`.

**Architecture:** A new, non-public serverless endpoint
(`api/sairndental/send-reminder.js`), invoked only by Vercel Cron, scans
every practice's `Confirmed` appointments directly against Supabase
(service-role key, same pattern as `api/sairndental/public-availability.js`
— no per-practice license key involved, since the cron is cross-tenant),
sends due reminders through Resend, and stamps idempotency timestamps
back onto the appointment record. Two small client-side additions in
`sairndental.html`: a Practice Info settings section (feeds the email's
practice name/phone/address) and a "no email on file" badge on the
Appointments panel.

**Tech Stack:** Existing zero-extra-dependency Node serverless function
style (see `api/sairndental/public-availability.js`), Resend's HTTP API
(`https://api.resend.com/emails`, called via `fetch`, no SDK — this repo
adds npm dependencies only when hand-rolling would be a real security risk,
per `package.json`'s own header; a JSON POST to a REST API doesn't qualify).

## No SQL migration in this plan

`dnt_appointments` and `dnt_settings` are already real Supabase-backed
resources with a generic `data` JSONB column (see `api/sd-data.js`'s
`dnt_appointments`/`dnt_settings` write handlers, ~L1765-1855). The two
new appointment fields (`reminder_48h_sent_at`, `reminder_2h_sent_at`)
and three new settings fields (`practice_name`, `practice_phone`,
`practice_address`) are new keys inside that existing JSONB payload —
same pattern the fee-schedule plan used for `estimated_insurance_portion`.
No `EXCLUDE` constraint, uniqueness, or fast indexed lookup needs any of
these five fields promoted to real columns, so none are.

## Global Constraints

- **Blocking prerequisite, manual, outside what I can do myself:**
  Michael must set two more Vercel project env vars beyond the
  already-confirmed `RESEND_API_KEY`:
  - `CRON_SECRET` — any random secret string. When set, Vercel Cron
    automatically sends `Authorization: Bearer <CRON_SECRET>` on
    cron-triggered requests; the endpoint checks this to refuse any
    caller that isn't the real cron trigger.
  - `RESEND_FROM_ADDRESS` — the exact sender address on the domain
    Michael verified in Resend (e.g. `reminders@yourdomain.com`). Not
    hardcoded in code — the spec's `reminders@sairndental.app` was an
    illustrative example, not a domain confirmed as actually
    registered/verified, so the real value must come from Michael, not
    be guessed.
  Both `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` already exist
  (confirmed — `api/sd-data.js` already depends on them in production).
- Only `Confirmed` appointments are ever considered (spec §3).
- `reminder_48h_sent_at`/`reminder_2h_sent_at` are stamped **only** on a
  confirmed successful Resend response — never speculatively, never on
  a caught error (spec §4).
- A failed Resend call is logged (appointment ID, reminder stage, error
  detail) via `console.error`, never silently swallowed, and does not
  stop the batch — the next appointment in the same run still gets
  processed (spec §4).
- No cancel/reschedule link, no per-practice sender domain, no SMS, no
  configurable offsets, no reminder-effectiveness reporting this pass
  (spec §6).
- `python tools/checkblocks.py sairndental.html` / `div_balance_check.py`
  / `duplicate_global_check.py` clean after every `sairndental.html`
  change. `python tools/vercel_config_check.py` clean after the
  `vercel.json` change. `node --check` on every new/modified `.js` file.
  Push Protocol: full local checks before push, real live-verify after.

---

### Task 1: Practice Info settings fields

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: existing `settings()` (line 809), `rBookingSettings()`
  (line 810), `saveBookingSettings()` (line 822), `$()`, `st()`, `toast()`,
  `dntLicenseKey()`, `DATA_API`, `APP_ID`.
- Produces: `settings()`'s returned object gains `practice_name`,
  `practice_phone`, `practice_address` string fields — Task 4's email
  copy module consumes these three field names exactly (via the values
  Task 4 reads server-side from the synced `dnt_settings` row, not from
  this client code directly, but the field names must match).

- [ ] **Step 1: Add Practice Info fields to the settings default + form**

In `settings()` (line 809), add the three new fields to the default
object:

```js
function settings(){return ld('dnt_settings_obj',{id:'default',booking_slug:'',timezone:'',publicly_bookable_procedure_type_ids:[],practice_name:'',practice_phone:'',practice_address:''});}
```

In the `panel-booking-settings` HTML (line 377-386), add a new card
before the existing one, inside the same panel:

```html
<div class="panel" id="panel-booking-settings">
  <div class="ph"><div><div class="ptitle">Booking Settings</div><div class="psub">Your practice's public self-scheduling link &mdash; the license key never appears on that page, this link is separate and safe to share.</div></div></div>
  <div class="card"><div class="ch"><div class="ct">Practice Info</div></div><div class="cb">
    <div class="fg"><label>Practice Name</label><input type="text" id="bs-practice-name" placeholder="e.g. Pinnacle Dental"></div>
    <div class="fg"><label>Practice Phone</label><input type="text" id="bs-practice-phone" placeholder="e.g. (555) 123-4567"></div>
    <div class="fg"><label>Practice Address</label><input type="text" id="bs-practice-address" placeholder="e.g. 123 Main St, Springfield, IL 62701"></div>
    <div style="font-size:11px;color:var(--muted);margin-bottom:14px">Used on every appointment reminder email &mdash; name and phone in the body, address in the footer.</div>
  </div></div>
  <div class="card"><div class="cb">
    <div class="fg"><label>Public Booking Link Slug</label><input type="text" id="bs-slug" placeholder="e.g. pinnacle-dental"></div>
    <div style="font-size:11px;color:var(--muted);margin-bottom:14px" id="bs-link-preview"></div>
    <div class="fg"><label>Practice Timezone</label><input type="text" id="bs-timezone" placeholder="e.g. America/New_York"></div>
    <div class="fg"><label>Publicly Bookable Procedure Types</label><div id="bs-procedure-checks" style="font-size:13px"></div></div>
    <button class="btn bp" onclick="saveBookingSettings()">Save Settings</button>
  </div></div>
</div>
```

(The button label changes from "Save Booking Settings" to "Save
Settings" since it now saves both cards' fields in one write.)

- [ ] **Step 2: Load and save the new fields**

In `rBookingSettings()` (line 810), add after the existing
`$('bs-timezone').value=s.timezone||'';` line:

```js
  $('bs-practice-name').value=s.practice_name||'';
  $('bs-practice-phone').value=s.practice_phone||'';
  $('bs-practice-address').value=s.practice_address||'';
```

In `saveBookingSettings()` (line 822), add to the `rec` object
construction:

```js
async function saveBookingSettings(){
  var slug=$('bs-slug').value.trim();
  var timezone=$('bs-timezone').value.trim();
  if(!slug){toast('Booking slug required');return;}
  var checkedIds=Array.from(document.querySelectorAll('#bs-procedure-checks input[type=checkbox]:checked')).map(function(el){return el.getAttribute('data-proc-id');});
  var rec={id:'default',booking_slug:slug,timezone:timezone,publicly_bookable_procedure_type_ids:checkedIds,
    practice_name:$('bs-practice-name').value.trim(),practice_phone:$('bs-practice-phone').value.trim(),
    practice_address:$('bs-practice-address').value.trim()};
  st('dnt_settings_obj',rec);
```

(The rest of the function — the `dntLicenseKey()` check, the
`fetch(DATA_API,...)` call, the `SLUG_TAKEN` handling — is unchanged;
`rec` already flows into that same `body:JSON.stringify({...payload:rec})`
call.)

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

Expected: all clean (no new duplicate IDs — `bs-practice-name`,
`bs-practice-phone`, `bs-practice-address` are new and unique).

- [ ] **Step 4: Manual verification**

Open the Booking Settings panel, fill in all three Practice Info
fields plus the existing slug, click Save Settings, reload the page,
navigate back to Booking Settings — confirm all three fields still
show the saved values (proves the round-trip through `dnt_settings_obj`
localStorage works, independent of server sync being provisioned).

- [ ] **Step 5: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- Practice Info settings fields (name/phone/address for reminder emails)"
```

---

### Task 2: "No email on file" badge on Appointments panel

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: existing `rAppointments()` (line ~885), `appointments()`,
  `patients()`, `providers()`, `procedureTypes()`, `H()`, `$()`.
- Produces: no new functions — a display-only change.

- [ ] **Step 1: Add a Reminders column**

In the `appointments-table` header (in `panel-appointments`'s HTML),
add a column:

```html
<table id="appointments-table"><thead><tr><th>Patient</th><th>Provider</th><th>Time</th><th>Procedure</th><th>Reminders</th><th></th></tr></thead><tbody id="appointments-tbody"></tbody></table>
```

- [ ] **Step 2: Render the badge**

In `rAppointments()`, add a badge cell and update the empty-state
`colspan` from 5 to 6:

```js
function rAppointments(){
  var list=appointments().filter(function(a){return a.status==='Confirmed';});
  var pats=patients(),provs=providers(),procs=procedureTypes();
  var tbody=$('appointments-tbody');
  tbody.innerHTML=list.map(function(a){
    var pt=pats.find(function(x){return x.id===a.patient_id;});
    var pv=provs.find(function(x){return x.id===a.provider_id;});
    var pc=procs.find(function(x){return x.id===a.procedure_type_id;});
    var noEmail=!pt||!pt.email;
    return '<tr><td>'+H(pt?pt.name:'(unknown patient)')+'</td><td>'+H(pv?pv.name:'(unknown provider)')+'</td>'+
      '<td>'+H(a.start_time?new Date(a.start_time).toLocaleString():'--')+'</td><td>'+H(pc?(pc.cdt_code+' -- '+pc.description):'(unknown procedure)')+'</td>'+
      '<td>'+(noEmail?'<span style="color:var(--danger);font-size:12px">No email on file</span>':'<span style="color:var(--muted);font-size:12px">--</span>')+'</td>'+
      '<td><button class="btn bp bs" onclick="openCompleteVisitModal(\''+a.id+'\')">Complete Visit</button></td></tr>';
  }).join('')||'<tr><td colspan="6" style="color:var(--muted);text-align:center">No confirmed appointments</td></tr>';
}
```

- [ ] **Step 3: Syntax-check**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
```

- [ ] **Step 4: Manual verification**

Add a patient with no email, confirm an appointment for them, open the
Appointments panel — confirm the "No email on file" badge shows for
that row and "--" shows for a patient that does have an email on file.

- [ ] **Step 5: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- 'no email on file' badge on Appointments panel"
```

---

### Task 3: Reminder email copy module

**Files:**
- Create: `api/_lib/dental-reminder-copy.js`

**Interfaces:**
- Consumes: nothing (pure function, no I/O).
- Produces: `buildReminderEmail(opts)` — Task 4 imports and calls this
  exact function with this exact shape:
  `{practiceName, practicePhone, practiceAddress, patientName, providerName, procedureLabel, startTimeISO, stage}`
  where `stage` is the literal string `'48h'` or `'2h'`. Returns
  `{subject, text, html}`.

- [ ] **Step 1: Write the module**

```js
// api/_lib/dental-reminder-copy.js
// Pure email-copy builder for SAIRNdental appointment reminders --
// no network/DB access, so it's testable with a plain Node script.
// Informational only, no cancel/reschedule link (design spec §0):
// states the appointment details and the practice's phone number to
// call for any change. practiceAddress appears in the footer as the
// CAN-SPAM-required physical address.

function formatWhen(startTimeISO) {
  var d = new Date(startTimeISO);
  return d.toLocaleString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
    hour: 'numeric', minute: '2-digit'
  });
}

function buildReminderEmail(opts) {
  var practiceName = opts.practiceName || 'Your dental practice';
  var practicePhone = opts.practicePhone || '';
  var practiceAddress = opts.practiceAddress || '';
  var patientName = opts.patientName || 'there';
  var providerName = opts.providerName || 'your provider';
  var procedureLabel = opts.procedureLabel || 'your appointment';
  var when = formatWhen(opts.startTimeISO);
  var stage = opts.stage;

  var leadIn = stage === '2h'
    ? "This is a reminder that your appointment is coming up soon:"
    : "This is a reminder about your upcoming appointment:";

  var subject = stage === '2h'
    ? practiceName + ': your appointment is in about 2 hours'
    : practiceName + ': appointment reminder for ' + when;

  var callLine = practicePhone
    ? ('If you need to reschedule or cancel, please call us at ' + practicePhone + '.')
    : 'If you need to reschedule or cancel, please call the office.';

  var text = 'Hi ' + patientName + ',\n\n' + leadIn + '\n\n' +
    'When: ' + when + '\n' +
    'Provider: ' + providerName + '\n' +
    'Procedure: ' + procedureLabel + '\n\n' +
    callLine + '\n\n' +
    '-- ' + practiceName + (practiceAddress ? ('\n' + practiceAddress) : '');

  var html = '<p>Hi ' + escHtml(patientName) + ',</p>' +
    '<p>' + escHtml(leadIn) + '</p>' +
    '<p><strong>When:</strong> ' + escHtml(when) + '<br>' +
    '<strong>Provider:</strong> ' + escHtml(providerName) + '<br>' +
    '<strong>Procedure:</strong> ' + escHtml(procedureLabel) + '</p>' +
    '<p>' + escHtml(callLine) + '</p>' +
    '<p style="color:#666;font-size:12px">' + escHtml(practiceName) +
    (practiceAddress ? ('<br>' + escHtml(practiceAddress)) : '') + '</p>';

  return { subject: subject, text: text, html: html };
}

// Same escaping discipline as sairndental.html's H() -- this text
// ultimately renders as HTML in a patient's inbox.
function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

module.exports = { buildReminderEmail: buildReminderEmail };
```

- [ ] **Step 2: `node --check`**

```
node --check api/_lib/dental-reminder-copy.js
```

Expected: no output, exit code 0.

- [ ] **Step 3: Node harness verification**

Create a throwaway script (not committed) to sanity-check the output:

```js
// scratch verification, run then discard
var { buildReminderEmail } = require('./api/_lib/dental-reminder-copy.js');
var r48 = buildReminderEmail({
  practiceName: 'Pinnacle Dental', practicePhone: '(555) 123-4567',
  practiceAddress: '123 Main St, Springfield, IL', patientName: 'Jane Doe',
  providerName: 'Dr. Smith', procedureLabel: 'D0120 -- Periodic Oral Evaluation',
  startTimeISO: '2026-08-13T14:00:00.000Z', stage: '48h'
});
console.log(r48.subject);
console.log(r48.text);
var r2 = buildReminderEmail(Object.assign({}, arguments[0], {stage:'2h'}));
```

Expected: subject contains "Pinnacle Dental", text contains "Jane Doe",
"Dr. Smith", the procedure label, and "(555) 123-4567"; a name/procedure
containing `<` or `&` renders escaped in `html` but literal in `text`.

- [ ] **Step 4: Commit**

```bash
git add api/_lib/dental-reminder-copy.js
git commit -m "feat: SAIRNdental -- reminder email copy module (pure, no I/O)"
```

---

### Task 4: `send-reminder.js` cron endpoint

**Files:**
- Create: `api/sairndental/send-reminder.js`

**Interfaces:**
- Consumes: `buildReminderEmail()` from Task 3
  (`../_lib/dental-reminder-copy.js`). Env vars `CRON_SECRET`,
  `RESEND_API_KEY`, `RESEND_FROM_ADDRESS`, `SUPABASE_URL`,
  `SUPABASE_SERVICE_ROLE_KEY`.
- Produces: `module.exports = async (req, res) => {...}` — a standard
  Vercel serverless handler, matching
  `api/sairndental/public-availability.js`'s shape. Task 5 wires
  `vercel.json`'s `crons` entry to `/api/sairndental/send-reminder`.

- [ ] **Step 1: Write the endpoint**

```js
// api/sairndental/send-reminder.js
// Cron-only endpoint (Vercel Cron -> CRON_SECRET check below), never
// publicly callable. Cross-tenant by design: scans every practice's
// Confirmed appointments directly against Supabase using the
// service-role key, the same posture as public-availability.js --
// there is no per-practice license key available to a scheduled job,
// so this bypasses api/sd-data.js's Bearer-license layer entirely and
// talks to Supabase REST directly. See
// docs/superpowers/specs/2026-08-11-sairndental-email-reminders-design.md.

const { buildReminderEmail } = require('../_lib/dental-reminder-copy.js');

function supabaseHeaders() {
  return {
    apikey: process.env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: 'Bearer ' + process.env.SUPABASE_SERVICE_ROLE_KEY,
    'Content-Type': 'application/json'
  };
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}
function enc(s) { return encodeURIComponent(s); }

// Window definition (spec §3, precise form): an appointment needs the
// 48h reminder when 47 < hoursUntil <= 48, and the 2h reminder when
// 1 < hoursUntil <= 2. Half-open on the near edge, closed on the far
// edge -- an hourly cron can't skip either window, and neither stage
// double-sends within one window.
function hoursUntil(startTimeISO, nowMs) {
  return (new Date(startTimeISO).getTime() - nowMs) / (1000 * 60 * 60);
}
function needsStage(row, stage, nowMs) {
  var h = hoursUntil(row.start_time, nowMs);
  var already = stage === '48h' ? row.data.reminder_48h_sent_at : row.data.reminder_2h_sent_at;
  if (already) return false;
  if (stage === '48h') return h > 47 && h <= 48;
  return h > 1 && h <= 2;
}

async function fetchOne(resource, idCol, licenseHash, id) {
  var r = await fetch(rest(resource + '?license_hash=eq.' + enc(licenseHash) + '&' + idCol + '=eq.' + enc(id) + '&select=data'), { headers: supabaseHeaders() });
  if (!r.ok) return null;
  var rows = await r.json();
  return (Array.isArray(rows) && rows[0]) ? rows[0].data : null;
}

async function sendResendEmail(to, subject, text, html) {
  var r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + process.env.RESEND_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: process.env.RESEND_FROM_ADDRESS, to: [to], subject: subject, text: text, html: html })
  });
  if (!r.ok) {
    var bodyText = await r.text().catch(function () { return ''; });
    throw new Error('Resend ' + r.status + ': ' + bodyText);
  }
  return true;
}

async function stampReminderSent(row, stage, nowISO) {
  var data = row.data;
  if (stage === '48h') data.reminder_48h_sent_at = nowISO; else data.reminder_2h_sent_at = nowISO;
  var r = await fetch(rest('dnt_appointments?on_conflict=license_hash,appointment_id'), {
    method: 'POST',
    headers: Object.assign({}, supabaseHeaders(), { Prefer: 'resolution=merge-duplicates,return=representation' }),
    body: JSON.stringify({
      license_hash: row.license_hash, app_id: 'sairndental', appointment_id: row.appointment_id, data: data,
      provider_id: row.provider_id || null, operatory_id: row.operatory_id || null,
      start_time: row.start_time || null, end_time: row.end_time || null, status: row.status || null,
      updated_at: nowISO
    })
  });
  if (!r.ok) {
    var bodyText = await r.text().catch(function () { return ''; });
    throw new Error('stamp write ' + r.status + ': ' + bodyText);
  }
}

module.exports = async (req, res) => {
  if (!process.env.CRON_SECRET) {
    console.error('CRON_SECRET not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }
  if (req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) {
    res.status(401).json({ error: { message: 'Unauthorized' } });
    return;
  }
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY || !process.env.RESEND_API_KEY || !process.env.RESEND_FROM_ADDRESS) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / RESEND_API_KEY / RESEND_FROM_ADDRESS not fully set');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }

  var nowMs = Date.now();
  var nowISO = new Date(nowMs).toISOString();
  var rangeStartISO = nowISO;
  var rangeEndISO = new Date(nowMs + 48 * 60 * 60 * 1000).toISOString();

  var summary = { sent: 0, skippedNoEmail: 0, skippedNotDue: 0, failed: 0 };

  try {
    var listRes = await fetch(rest('dnt_appointments?status=eq.Confirmed&start_time=gt.' + enc(rangeStartISO) + '&start_time=lte.' + enc(rangeEndISO) + '&select=license_hash,appointment_id,data,provider_id,operatory_id,start_time,end_time,status'), { headers: supabaseHeaders() });
    if (!listRes.ok) {
      var errBody = await listRes.text().catch(function () { return ''; });
      console.error('send-reminder: dnt_appointments list failed', listRes.status, errBody);
      res.status(502).json({ error: { message: 'Could not list appointments' } });
      return;
    }
    var rows = await listRes.json();

    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var stage = null;
      if (needsStage(row, '48h', nowMs)) stage = '48h';
      else if (needsStage(row, '2h', nowMs)) stage = '2h';
      if (!stage) { summary.skippedNotDue++; continue; }

      try {
        var patientId = row.data.patient_id;
        var patient = await fetchOne('dnt_patients', 'patient_id', row.license_hash, patientId);
        if (!patient || !patient.email) { summary.skippedNoEmail++; continue; }

        var settings = await fetchOne('dnt_settings', 'settings_id', row.license_hash, 'default');
        var provider = row.provider_id ? await fetchOne('dnt_providers', 'provider_id', row.license_hash, row.provider_id) : null;
        var procedureTypeId = row.data.procedure_type_id;
        var procedure = procedureTypeId ? await fetchOne('dnt_procedure_types', 'procedure_type_id', row.license_hash, procedureTypeId) : null;

        var copy = buildReminderEmail({
          practiceName: (settings && settings.practice_name) || '',
          practicePhone: (settings && settings.practice_phone) || '',
          practiceAddress: (settings && settings.practice_address) || '',
          patientName: patient.name || '',
          providerName: (provider && provider.name) || '',
          procedureLabel: procedure ? (procedure.cdt_code + ' -- ' + procedure.description) : '',
          startTimeISO: row.start_time,
          stage: stage
        });

        await sendResendEmail(patient.email, copy.subject, copy.text, copy.html);
        await stampReminderSent(row, stage, nowISO);
        summary.sent++;
      } catch (perAppointmentErr) {
        console.error('send-reminder: failed for appointment', row.appointment_id, 'stage', stage, '-', perAppointmentErr.message);
        summary.failed++;
      }
    }

    res.status(200).json({ ok: true, summary: summary });
  } catch (err) {
    console.error('send-reminder: fatal error', err);
    res.status(500).json({ error: { message: 'Internal error' } });
  }
};
```

- [ ] **Step 2: `node --check`**

```
node --check api/sairndental/send-reminder.js
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add api/sairndental/send-reminder.js
git commit -m "feat: SAIRNdental -- send-reminder.js cron endpoint (48h/2h Resend reminders)"
```

---

### Task 5: Vercel Cron wiring

**Files:** Modify `vercel.json`

- [ ] **Step 1: Add the crons entry**

```json
{
  "buildCommand": "mkdir -p dist && cp *.html dist/ && cp stonedesk.html dist/index.html && cp sw.js dist/sw.js",
  "outputDirectory": "dist",
  "routes": [
    ...(unchanged, all 13 existing entries stay exactly as they are)...
  ],
  "crons": [
    {
      "path": "/api/sairndental/send-reminder",
      "schedule": "0 * * * *"
    }
  ]
}
```

(Only the top-level `crons` array is new; every existing `routes` entry
stays byte-for-byte unchanged.)

- [ ] **Step 2: Validate**

```
python tools/vercel_config_check.py
```

Expected: clean — this only adds a new top-level key, `buildCommand`
length is unaffected.

```
python -c "import json; json.load(open('vercel.json'))"
```

Expected: no output, exit code 0 (confirms valid JSON).

- [ ] **Step 3: Commit**

```bash
git add vercel.json
git commit -m "feat: SAIRNdental -- hourly Vercel Cron for send-reminder.js"
```

---

### Task 6: End-to-end verification, push, live-verify

- [ ] **Step 1:** Confirm Michael has set all three required env vars
  (`RESEND_API_KEY` — already confirmed; `CRON_SECRET`;
  `RESEND_FROM_ADDRESS`) in Vercel before proceeding — the real send
  test in Step 3 cannot succeed without all three.
- [ ] **Step 2:** Full local re-check of every changed/new file
  (`checkblocks.py`, `div_balance_check.py`, `duplicate_global_check.py`
  on `sairndental.html`; `node --check` on both new `.js` files;
  `vercel_config_check.py` on `vercel.json`).
- [ ] **Step 3:** Push to `main`.
- [ ] **Step 4: Real test send through Resend — the actual credential
  verification, not assumed from the deploy completing.** Create one
  real test patient (with a real, deliverable email address Michael
  provides) and one `Confirmed` test appointment with `start_time` set
  to exactly 47.5 hours from now (inside the 48h window). Manually
  invoke the deployed endpoint once, directly, with the real
  `CRON_SECRET`:
  ```
  curl -X GET https://sairn.vercel.app/api/sairndental/send-reminder \
    -H "Authorization: Bearer <the real CRON_SECRET>"
  ```
  Expected: `{"ok":true,"summary":{"sent":1,...}}` and a real email
  genuinely arrives at the test address (confirmed by Michael checking
  the inbox, or via Resend's dashboard delivery log) — not just a
  200 response.
- [ ] **Step 5: Window-boundary test.** Using the same mechanism as
  Step 4, create test appointments at hoursUntil = 46.9 (just outside
  the 48h window, below), 47.5 (inside), 48.1 (just outside, above),
  0.9 (just outside the 2h window, below), 1.5 (inside), 2.1 (just
  outside, above). Invoke the endpoint once. Expected: only the 47.5h
  and 1.5h appointments appear in `summary.sent`; the other four
  contribute to `summary.skippedNotDue`.
- [ ] **Step 6: Idempotency test.** Invoke the endpoint a second time
  immediately after Step 4/5 without changing any test data. Expected:
  `summary.sent` is `0` for the appointments already sent in the prior
  run (their `reminder_*_sent_at` is now set), confirming no duplicate
  email.
- [ ] **Step 7: Missing-email test.** Create a test appointment for a
  patient with no `email` value, inside a reminder window. Invoke the
  endpoint. Expected: `summary.skippedNoEmail` increments by 1, no
  Resend call attempted for that appointment, and the Appointments
  panel (Task 2) shows its "No email on file" badge for that
  appointment.
- [ ] **Step 8: Failed-send logging test.** Temporarily set
  `RESEND_API_KEY` to an intentionally invalid value in a preview
  deployment (never production), invoke the endpoint against a due
  test appointment. Expected: `summary.failed` increments by 1, Vercel
  function logs show the `console.error` line with the appointment ID
  and stage, and `reminder_*_sent_at` was NOT stamped (confirm via a
  direct read of that appointment afterward) — proving a real failure
  is retried on the next legitimate run, not silently marked sent.
  Restore the real `RESEND_API_KEY` afterward.
- [ ] **Step 9:** Delete all test patients/appointments created for
  Steps 4-8 so they don't pollute real practice data or the live
  Appointments panel.
- [ ] **Step 10:** Update
  `docs/superpowers/specs/2026-08-11-sairndental-email-reminders-design.md`'s
  status line with the real commit SHAs and confirmed-live date.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks 1-6
is written**, per your instruction.
