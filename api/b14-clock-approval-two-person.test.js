// api/b14-clock-approval-two-person.test.js
//
// Run:  node api/b14-clock-approval-two-person.test.js
//
// MICHAEL'S b14 DECISION: no self-approval on clock corrections -- the
// approver must DIFFER from the submitter. That overturns the flag-not-refusal
// trade b13 made (`self_approved: true` on the entry, allowed because in a
// one-person agency there is nobody else), and it is a maker-checker rule:
// whoever submits a correction can never be the one who makes it effective.
//
// THE CONSEQUENCE IS REAL AND IS NOT HIDDEN BY THESE ARMS. It applies to BOTH
// routes, because on `propose_clock_correction` the submitter and the approver
// were the same person by construction -- the scheduler filed and the filing
// itself approved. So that route no longer auto-approves either, and a
// one-person agency cannot make ANY correction effective. Named in the handoff
// as a follow-up decision, not smuggled in here.
//
// WHAT IS PROVEN WHERE, stated rather than implied:
//   S arms  the real api/sd-data.js handler and the real
//           api/_lib/sen-evv-clock.js, with the transport stubbed.
//   U arms  the real sairnsenior.html render functions, EXTRACTED and run in a
//           vm with a stubbed DOM. A vm is not a browser: it proves the
//           function's logic and NOT that the markup renders. Playwright,
//           jsdom and html5lib are all absent from this clone, so the
//           beyond-a-vm leg is done through the Chrome tooling against the
//           DEPLOYED page and recorded separately.
//
// Exit: 0 all arms passed - 1 an arm FAILED - 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '..');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['b14', 'fixture', String(process.pid)].join('-');
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

const eCode = (r) => (r && r.body && r.body.error && r.body.error.code) || '';
function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
require.cache[require.resolve('./_lib/license')] = {
  id: require.resolve('./_lib/license'),
  filename: require.resolve('./_lib/license'),
  loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH,
      trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnsenior' })
  }
};
const { signSessionToken } = require('./_lib/auth');
delete require.cache[require.resolve('./sd-data.js')];
const handler = require('./sd-data.js');
const clock = require('./_lib/sen-evv-clock');

let VISIT = null;
const writes = [];
function senFetch() {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => [{ license_hash: HASH, employee_id: 'E1',
                                    role: 'caregiver', active: true }] };
    }
    if (method !== 'GET') {
      writes.push({ url: u, body: init && init.body });
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => [JSON.parse(init.body)] };
    }
    if (/sen_visits\?/.test(u)) {
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => (VISIT ? [VISIT] : []) };
    }
    return { ok: true, status: 200, headers: { get: () => '' },
             text: async () => '[]', json: async () => [] };
  };
}
async function call(action, payload, role, employeeId) {
  writes.length = 0;
  global.fetch = senFetch();
  const res = mockRes();
  await handler({ method: 'POST',
    headers: { authorization: 'Bearer ' + KEY,
               'x-sd-auth': signSessionToken({ app: 'sairnsenior',
                 employee_id: employeeId, role: role, license_hash: HASH }) },
    body: { action: action, resource: 'sen_visits', payload: payload } }, res);
  return { res: res, writes: writes.slice() };
}
function stored(w) {
  if (!w.length) return null;
  try { return JSON.parse(w[w.length - 1].body).data || null; } catch (e) { return null; }
}
const H = 60 * 60 * 1000;
const NOW = Date.now();
const RECORDED = new Date(NOW - 4 * H).toISOString();
const SUBMITTED = new Date(NOW - 5 * H).toISOString();

// A visit whose caregiver E1 has submitted a pending correction.
function visitWithPendingFrom(who) {
  return { visit_id: 'V1', assigned_employee_id: 'E1',
    data: { clock_in_at: RECORDED,
            clock_corrections: [{ field: 'clock_in_at', original_at: RECORDED,
              proposed_at: SUBMITTED, reason_code: 'transcription_error',
              reason_label: 'The time was entered incorrectly',
              proposed_by: who, proposed_at_server: RECORDED,
              status: 'pending', approved_by: null,
              approved_at_server: null }] } };
}

console.log('b14. no self-approval: the approver must differ from the submitter\n');

(async () => {
  // ── S. SERVER SIDE ──────────────────────────────────────────────────────
  console.log('S. api/sd-data.js approve_clock_correction');
  {
    // THE SUBMITTER IS S1 AND S1 IS A SCHEDULER, so the role gate passes and
    // the ONLY thing that can refuse is the identity rule. Without this
    // framing the arm would pass on the 403 it already had.
    VISIT = visitWithPendingFrom('S1');
    const r = await call('approve_clock_correction',
                         { id: 'V1', correction_index: 0 }, 'owner', 'S1');
    is(r.res.statusCode === 403 && r.writes.length === 0,
       'S1. THE ARM THE DECISION IS -- a scheduler cannot approve a correction '
     + 'THEY submitted: 403 and NOTHING written. b13 marked this '
     + '`self_approved: true` and allowed it; the decision is that an approval '
     + 'by the submitter is not an approval at all',
       'status=' + r.res.statusCode + ' code=' + eCode(r.res)
     + ' writes=' + r.writes.length);
    is(eCode(r.res) === 'SELF_APPROVAL_REFUSED',
       'S2. ...with its own code, not the generic FORBIDDEN the role gate '
     + 'returns. A caller cannot act on a refusal they cannot tell apart from '
     + '"you are the wrong role"',
       'code=' + eCode(r.res));
    const msg = String((r.res.body && r.res.body.error && r.res.body.error.message) || '');
    is(/another|second|different|someone else/i.test(msg) && msg.length > 60,
       'S3. ...and the message says what to do next. A refusal that does not '
     + 'name the route gets worked around',
       JSON.stringify(msg.slice(0, 160)));
  }
  {
    VISIT = visitWithPendingFrom('E1');
    const r = await call('approve_clock_correction',
                         { id: 'V1', correction_index: 0 }, 'owner', 'S1');
    const e = ((stored(r.writes) || {}).clock_corrections || [])[0] || {};
    is(r.res.statusCode === 200 && e.status === 'approved' && e.approved_by === 'S1',
       'S4. CONTROL -- a DIFFERENT person approving still works. Without this '
     + 'arm the fix could be "refuse every approval" and S1 would still pass',
       'status=' + r.res.statusCode + ' entry=' + JSON.stringify(e).slice(0, 180));
    is(e.self_approved === undefined && r.res.body.self_approved === undefined,
       'S5. ...and `self_approved` is GONE from the entry and the response. A '
     + 'field that can no longer be true is a field a reader will still look '
     + 'for and a consumer will still branch on',
       'entry=' + JSON.stringify(e).slice(0, 200)
     + ' body.self_approved=' + JSON.stringify(r.res.body.self_approved));
  }
  {
    // THE OTHER ROUTE. On propose_clock_correction the filer and the approver
    // were the same person BY CONSTRUCTION, so b13's approve-at-filing is
    // exactly what this decision forbids.
    VISIT = { visit_id: 'V1', assigned_employee_id: 'E1',
              data: { clock_in_at: RECORDED } };
    const r = await call('propose_clock_correction',
      { id: 'V1', correction: { field: 'clock_in_at', proposed_at: SUBMITTED,
                                reason_code: 'transcription_error' } },
      'owner', 'S1');
    const d = stored(r.writes) || {};
    const e = (d.clock_corrections || [])[0] || {};
    const eff = clock.effectiveClock(d, 'clock_in_at');
    is(r.res.statusCode === 200 && e.status === 'pending',
       'S6. a SCHEDULER filing through propose_clock_correction no longer '
     + 'approves it at the same moment. The filer and the approver were the '
     + 'same person by construction on that route, which is the thing the '
     + 'decision forbids -- so b13\'s approve-at-filing had to go with it',
       'status=' + r.res.statusCode + ' entry=' + JSON.stringify(e).slice(0, 180));
    is(eff.value === RECORDED && eff.corrected === false && eff.pending === true,
       'S7. ...and the effective clock does NOT move on filing. This is the '
     + 'half that makes the rule real rather than a field on a row',
       JSON.stringify(eff).slice(0, 200));
    is(r.res.body && /pending|approv/i.test(JSON.stringify(r.res.body)),
       'S8. ...and the filer is TOLD it is pending. A 200 that reads like a '
     + 'completed correction is affirmative false success',
       JSON.stringify(r.res.body).slice(0, 200));
  }
  {
    VISIT = visitWithPendingFrom('E1');
    const r = await call('approve_clock_correction',
                         { id: 'V1', correction_index: 0 }, 'caregiver', 'E9');
    is(r.res.statusCode === 403 && eCode(r.res) === 'FORBIDDEN'
       && r.writes.length === 0,
       'S9. CONTROL -- a caregiver still cannot approve at all, and still gets '
     + 'the ROLE refusal rather than the new identity one. Two different '
     + 'reasons, two different codes',
       'status=' + r.res.statusCode + ' code=' + eCode(r.res));
  }
  {
    VISIT = { visit_id: 'V1', assigned_employee_id: 'E1',
      data: { clock_in_at: RECORDED,
              clock_corrections: [{ field: 'clock_in_at', original_at: RECORDED,
                proposed_at: SUBMITTED, reason_code: 'transcription_error',
                proposed_by: 'E1', proposed_at_server: RECORDED,
                status: 'approved', approved_by: 'S2',
                approved_at_server: RECORDED }] } };
    const r = await call('approve_clock_correction',
                         { id: 'V1', correction_index: 0 }, 'owner', 'S1');
    is(r.res.statusCode === 409 && eCode(r.res) === 'ALREADY_APPROVED'
       && r.writes.length === 0,
       'S10. CONTROL -- an already-approved entry still 409s, and the identity '
     + 'check did not displace that. Order matters: a second approval record '
     + 'for one decision double-counts at audit',
       'status=' + r.res.statusCode + ' code=' + eCode(r.res));
  }
  {
    // THE MODULE REFUSES ON ITS OWN, not only through the handler. The rule
    // belongs where proposeCorrection's rules are, so a second caller cannot
    // reach approval without it.
    const entry = { field: 'clock_in_at', proposed_by: 'E1', status: 'pending' };
    const v = clock.approveCorrection(entry, 'E1', new Date(NOW).toISOString());
    is(v.ok === false && v.error && v.error.code === 'SELF_APPROVAL_REFUSED',
       'S11. api/_lib/sen-evv-clock.js approveCorrection() refuses it ITSELF. '
     + 'A rule enforced only in one branch of one handler is a rule the next '
     + 'caller does not get',
       JSON.stringify(v).slice(0, 200));
    const v2 = clock.approveCorrection(entry, 'S1', new Date(NOW).toISOString());
    is(v2.ok === true && v2.entry.approved_by === 'S1',
       'S12. CONTROL -- the module still approves for anybody else',
       JSON.stringify(v2).slice(0, 160));
  }

  // ── U. THE QUEUE IN sairnsenior.html ────────────────────────────────────
  console.log('\nU. the pending-corrections queue and its Approve control');

  const HTML = (function () {
    try { return fs.readFileSync(path.join(ROOT, 'sairnsenior.html'), 'utf8'); }
    catch (e) { return null; }
  })();
  function lift(name) {
    if (HTML === null) return null;
    const re = new RegExp('\\nfunction ' + name + '\\([^)]*\\)\\{[\\s\\S]*?\\n\\}');
    const m = HTML.match(re);
    return m ? m[0] : null;
  }
  const NEEDED = ['senPendingCorrections', 'renderCorrectionsView',
                  'vsCorrectionsBadgeText'];
  const missing = NEEDED.filter((n) => lift(n) === null);
  if (HTML === null) {
    cannot('U1. sairnsenior.html is not readable', 'ENOENT');
    cannot('U2. depends on U1', '-'); cannot('U3. depends on U1', '-');
    cannot('U4. depends on U1', '-'); cannot('U5. depends on U1', '-');
  } else if (missing.length) {
    // A MISSING FUNCTION IS A FAIL, NOT AN UNPROVEN. "The queue is not there"
    // and "I could not measure it" are different answers.
    ['U1', 'U2', 'U3', 'U4', 'U5'].forEach(function (n) {
      bad(n + '. the queue functions are not all present in sairnsenior.html '
        + '-- the panel has not been built', 'missing: ' + missing.join(', '));
    });
  } else {
    const els = {};
    function el(id) {
      if (!els[id]) els[id] = { id: id, innerHTML: '', textContent: '',
                                style: {}, className: '' };
      return els[id];
    }
    const sandbox = {
      console: console,
      $: el,
      H: function (s) { return String(s == null ? '' : s); },
      senSession: { employee_id: 'S1', role: 'owner', token: 't' },
      senIsScheduler: function () { return true; },
      VISITS: [],
      visits: function () { return sandbox.VISITS; },
      senData: function () { return Promise.resolve(null); },
      fdatetime: function (v) { return String(v); },
      toast: function () {},
      senLocalToday: function () { return '2026-10-15'; }
    };
    vm.createContext(sandbox);
    let booted = true;
    try { vm.runInContext(NEEDED.map(lift).join('\n'), sandbox); }
    catch (e) { booted = false; cannot('U1. the extracted functions would not run', String(e)); }
    if (booted) {
      // One pending correction submitted by SOMEBODY ELSE -> approvable.
      sandbox.VISITS = [{ id: 'V1', assigned_employee_id: 'E1',
        clock_in_at: RECORDED,
        clock_corrections: [{ field: 'clock_in_at', original_at: RECORDED,
          proposed_at: SUBMITTED, reason_code: 'transcription_error',
          proposed_by: 'E1', status: 'pending' }] }];
      sandbox.renderCorrectionsView();
      let html = el('vs-view-corrections').innerHTML;
      is(/vsApproveCorrection\(/.test(html) && !/disabled/.test(html),
         'U1. a pending correction submitted by somebody ELSE renders an '
       + 'ENABLED Approve control',
         JSON.stringify(html.slice(0, 220)));
      is(html.indexOf(String(RECORDED)) !== -1 && html.indexOf(String(SUBMITTED)) !== -1,
         'U2. ...showing BOTH times. A queue that shows only the proposed value '
       + 'has become the overwrite this whole mechanism exists to avoid',
         JSON.stringify(html.slice(0, 260)));

      // The same correction, submitted by the CURRENT user -> not approvable.
      sandbox.VISITS = [{ id: 'V1', assigned_employee_id: 'S1',
        clock_in_at: RECORDED,
        clock_corrections: [{ field: 'clock_in_at', original_at: RECORDED,
          proposed_at: SUBMITTED, reason_code: 'transcription_error',
          proposed_by: 'S1', status: 'pending' }] }];
      sandbox.renderCorrectionsView();
      html = el('vs-view-corrections').innerHTML;
      is(/disabled/.test(html) && /you submitted|your own|submitted it/i.test(html),
         'U3. a pending correction THIS user submitted renders a DISABLED '
       + 'control with the reason on screen. The server refuses it either way; '
       + 'offering a button that always 403s teaches people the app is broken',
         JSON.stringify(html.slice(0, 260)));

      // Nothing pending -> an empty state, not a blank panel.
      sandbox.VISITS = [{ id: 'V2', clock_in_at: RECORDED }];
      sandbox.renderCorrectionsView();
      html = el('vs-view-corrections').innerHTML;
      is(html.replace(/<[^>]*>/g, '').trim().length > 15,
         'U4. CONTROL -- no pending corrections renders a sentence, not an '
       + 'empty panel. A blank panel is indistinguishable from one that failed '
       + 'to load',
         JSON.stringify(html.slice(0, 200)));

      // The badge counts them, and an APPROVED entry is not counted.
      sandbox.VISITS = [
        { id: 'V1', clock_corrections: [{ field: 'clock_in_at', proposed_by: 'E1', status: 'pending' },
                                        { field: 'clock_out_at', proposed_by: 'E1', status: 'approved' }] },
        { id: 'V2', clock_corrections: [{ field: 'clock_in_at', proposed_by: 'E2', status: 'pending' }] }];
      is(sandbox.senPendingCorrections().length === 2,
         'U5. the queue counts PENDING entries only, across visits -- an '
       + 'approved one is not waiting for anybody',
         'count=' + sandbox.senPendingCorrections().length);
    }
  }
  {
    // THE REFUSAL MUST REACH THE SCREEN. senData() returns null on every
    // failure and logs to the console, so without a recorded reason the
    // queue's own refusal would be a silent no-op -- the exact shape this
    // platform keeps paying for.
    const src = HTML || '';
    is(/senLastErr/.test(src),
       'U6. sairnsenior.html records WHY a senData call failed, so the '
     + 'corrections panel can show the server\'s refusal instead of doing '
     + 'nothing visible. senData() returned a bare null on every failure',
       'no senLastErr in sairnsenior.html');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
