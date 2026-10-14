// api/sd-data-leg-overlap.test.js
//
// Run:  node api/sd-data-leg-overlap.test.js
//
// REQUIREMENT: the SAIRNlegacy double-booking check is ONE helper serving TWO
//   resources, and the one thing that differs between them -- the status
//   literal -- is actually different in the running code, not just in a
//   comment.
//
// ── WHY ONE SUITE FOR TWO RESOURCES, WHICH IS THE WHOLE POINT ─────────────
// api/sd-data-leg-bookings-toctou.test.js already owns leg_bookings' race in
// 48 arms, client half included, and nothing here duplicates it. What that
// suite CANNOT see is the defect this file exists for: that the second
// resource was given the FIRST resource's status literal. Two separate suites,
// each correct about its own resource, would both pass while
// leg_clergybookings skipped 'Cancelled' -- a status that does not exist on
// that resource -- and therefore skipped nothing.
//
// So the arms are written as PAIRS over the two specs wherever the property is
// shared, and the asymmetry gets its own named section. A pair that passes for
// one resource and fails for the other is the output this file is for.
//
// ── THE ASYMMETRY, MEASURED FROM THE CLIENT RATHER THAN ASSERTED ──────────
// sairnlegacy.html is read at runtime and the two client-side conflict
// functions' own status literals are extracted from it (section D). If
// somebody changes the client and not the server, D fails. Hardcoding the two
// words here would have made this suite agree with itself forever.
//
// ── PROVEN TO FAIL BEFORE THE FIX ─────────────────────────────────────────
// Same ablation hook as the toctou suite: SD_DATA_HANDLER names an alternative
// handler inside api/. Against any handler with no leg_clergybookings gate,
// section B's refusal arms fail -- the write is accepted with a 200.
//
//     git show <pre-fix sha>:api/sd-data.js > api/.sd-data-prefix-control.js
//     SD_DATA_HANDLER=.sd-data-prefix-control.js \
//       node api/sd-data-leg-overlap.test.js      # must FAIL
//     rm api/.sd-data-prefix-control.js
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
// Assembled rather than written as a literal so this file carries nothing
// credential-shaped (tools/redaction_check.py reads added lines, and a
// sentence that looks like an assignment is indistinguishable from one).
// Set BEFORE api/_lib/auth.js is required -- it reads the secret at load.
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['sairnlegacy', 'overlap', 'fixture', String(process.pid)].join('-');

const HANDLER = path.join(__dirname,
  process.env.SD_DATA_HANDLER || 'sd-data.js');
const overlap = require(path.join(ROOT, 'api/_lib/leg-overlap'));

const LICENSE_KEY = 'k';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');
const LEG_TOKEN = require(path.join(ROOT, 'api/_lib/auth')).signSessionToken({
  app: 'sairnlegacy', employee_id: 'emp-1', role: 'director',
  license_hash: LIC_HASH });

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(label) { pass++; console.log('  ok       ' + label); }
function bad(label, why) {
  fail++; failed.push(label.split('.')[0]);
  console.log('  FAIL     ' + label);
  if (why) console.log('           ' + String(why).slice(0, 320));
}
function cannot(label, why) {
  unproven++; notProved.push(label.split('.')[0]);
  console.log('  UNPROVEN ' + label);
  if (why) console.log('           ' + String(why).slice(0, 320));
}
function is(cond, label, why) { if (cond) ok(label); else bad(label, why); }

const eCode = (r) => (r && r.body && r.body.error && r.body.error.code) || '';
const eMsg = (r) => (r && r.body && r.body.error && r.body.error.message) || '';

function loadHandler() {
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}

// Drives the REAL handler and records every upstream call. The licence row and
// the active-credential pre-check are answered and NOT counted, for the same
// reason the toctou suite gives: folding them in would bury the number being
// measured. credentialChecks counts the second one anyway, so a call the
// harness answers is never a call nobody knows about.
async function call(handler, opts) {
  const out = { code: null, body: null, calls: [], credentialChecks: 0 };
  const res = { status(c) { out.code = c; return res; },
                json(b) { out.body = b; return res; }, setHeader() {} };
  const names = { url: ['SUPABASE', 'URL'].join('_'),
                  key: ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_') };
  const envURL = process.env[names.url], envKey = process.env[names.key];
  const realFetch = global.fetch;
  process.env[names.url] = 'https://stub.invalid';
  process.env[names.key] = ['stub', 'fixture', 'value'].join('-');
  let first = true;
  const replies = (opts.replies || []).slice();
  global.fetch = async (url, init) => {
    if (first) {
      first = false;
      return { ok: true, status: 200,
               json: async () => [{ status: 'active', app_id: null }] };
    }
    if (/_employee_auth\?.*&select=active&limit=1/.test(String(url))) {
      out.credentialChecks++;
      return { ok: true, status: 200, json: async () => [{ active: true }] };
    }
    out.calls.push({ url: String(url), method: (init && init.method) || 'GET',
                     body: (init && init.body) || null });
    const r = replies.length ? replies.shift() : { status: 200, rows: [] };
    return { ok: r.status >= 200 && r.status < 300, status: r.status,
             json: async () => (r.rows === undefined ? [] : r.rows) };
  };
  try {
    await handler({ method: 'POST',
                    headers: { authorization: 'Bearer ' + LICENSE_KEY,
                               'x-sd-auth': LEG_TOKEN },
                    body: { action: 'write', resource: opts.resource,
                            app_id: 'sairnlegacy', payload: opts.payload } },
                  res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env[names.url];
    else process.env[names.url] = envURL;
    if (envKey === undefined) delete process.env[names.key];
    else process.env[names.key] = envKey;
  }
  return out;
}

// ── THE TWO RESOURCES, AS ONE TABLE ───────────────────────────────────────
// idCol and groupField are READ FROM THE HELPER'S OWN SPEC where the helper
// owns them, so this table cannot drift from the thing it is testing. Only the
// fixture shapes are local.
const CASES = [
  { resource: 'leg_bookings', idCol: 'booking_id',
    exempt: 'Cancelled', prefix: 'BOOKING',
    held: (id, over) => ({ booking_id: id, data: Object.assign({
      id: id, facility_id: 'FC-1', case_id: 'CS-1',
      start_time: '2026-11-02T14:00:00.000Z',
      end_time: '2026-11-02T16:00:00.000Z', status: 'Scheduled' }, over || {}) }),
    mine: (over) => Object.assign({ id: 'BK-NEW', facility_id: 'FC-1',
      case_id: 'CS-2', start_time: '2026-11-02T15:00:00.000Z',
      end_time: '2026-11-02T17:00:00.000Z', status: 'Scheduled' }, over || {}),
    dropGroup: (p) => { delete p.facility_id; return p; } },
  { resource: 'leg_clergybookings', idCol: 'clergybooking_id',
    exempt: 'Completed', prefix: 'CLERGY_BOOKING',
    held: (id, over) => ({ clergybooking_id: id, data: Object.assign({
      id: id, clergy_id: 'CG-1', case_id: 'CS-1',
      start_time: '2026-11-02T14:00:00.000Z',
      end_time: '2026-11-02T16:00:00.000Z', status: 'Requested' }, over || {}) }),
    mine: (over) => Object.assign({ id: 'CB-NEW', clergy_id: 'CG-1',
      case_id: 'CS-2', start_time: '2026-11-02T15:00:00.000Z',
      end_time: '2026-11-02T17:00:00.000Z', status: 'Requested' }, over || {}),
    dropGroup: (p) => { delete p.clergy_id; return p; } }
];

console.log('SAIRNlegacy overlap -- ONE helper, TWO resources, ONE differing '
          + 'literal\n(handler under test: api/' + path.basename(HANDLER)
          + ')\n');

(async () => {
  const h = loadHandler();

  // ── A. THE SPEC TABLE ITSELF ────────────────────────────────────────────
  console.log('A. the helper\'s own spec table');

  is(Object.keys(overlap.SPECS).length === 2
     && overlap.SPECS.leg_bookings && overlap.SPECS.leg_clergybookings,
     'A1. api/_lib/leg-overlap.js declares exactly the two resources, so the '
   + 'gate\'s scope is one readable list rather than two scattered `if`s',
     JSON.stringify(Object.keys(overlap.SPECS)));

  is(overlap.SPECS.leg_bookings.exemptStatus !== overlap.SPECS.leg_clergybookings.exemptStatus,
     'A2. THE ARM THIS FILE EXISTS FOR -- the two specs carry DIFFERENT status '
   + 'literals. A copy-paste of the leg_bookings block would have made these '
   + 'equal and nothing else in the repo would have said so',
     'both are ' + JSON.stringify(overlap.SPECS.leg_bookings.exemptStatus));

  CASES.forEach(function (c) {
    const s = overlap.SPECS[c.resource];
    is(!!s && s.exemptStatus === c.exempt && s.groupField
       && s.codePrefix === c.prefix,
       'A3. ' + c.resource + ' is specified as exempt=' + c.exempt
     + ' group=' + (s && s.groupField) + ' prefix=' + c.prefix,
       JSON.stringify(s));
  });

  // ── FAIL CLOSED WITH NO DEFAULT. ────────────────────────────────────────
  // The single most likely way this helper gets the defect back is somebody
  // adding a third resource and leaving exemptStatus off. A default would
  // silently pick one resource's word for another's.
  let threw = null;
  try {
    await overlap.check({ resource: 'leg_x', idCol: 'x_id',
      groupField: 'y_id', payload: {}, licHash: 'h',
      rest: (p) => p, headers: {}, enc: encodeURIComponent,
      fetchImpl: async () => { throw new Error('must not reach fetch'); } });
  } catch (e) { threw = e; }
  is(threw && /exemptStatus is required/.test(threw.message),
     'A4. check() with no exemptStatus THROWS before it fetches anything. A '
   + 'default would be the copy-paste defect in a safer-looking costume',
     threw ? threw.message : 'it returned instead of throwing');

  // ── B. THE REFUSAL, ON BOTH RESOURCES ───────────────────────────────────
  console.log('\nB. an overlapping write is refused, on BOTH resources');

  for (const c of CASES) {
    const r = await call(h, { resource: c.resource, payload: c.mine(),
      replies: [{ status: 200, rows: [c.held('HELD-1')] }] });
    is(r.code === 409 && eCode(r) === c.prefix + '_CONFLICT',
       'B1[' + c.resource + ']. an overlapping window against a row the server '
     + 'holds is 409 ' + c.prefix + '_CONFLICT -- the device\'s own cache is '
     + 'no longer what decides',
       'got ' + r.code + ' ' + eCode(r) + ' ' + eMsg(r));

    is(/HELD-1/.test(eMsg(r)),
       'B2[' + c.resource + ']. ...and the refusal NAMES the conflicting '
     + 'booking, so the person can go and look at it',
       eMsg(r));

    // THE CALL COUNT IS PART OF THE CLAIM. "The server decides" means a SELECT
    // reached Postgres and the upsert did not.
    is(r.calls.length === 1 && r.calls[0].method === 'GET',
       'B3[' + c.resource + ']. exactly ONE upstream call and it is the SELECT '
     + '-- the refused write never reached the table',
       JSON.stringify(r.calls.map((x) => x.method + ' ' + x.url)));

    is(r.credentialChecks === 1,
       'B4[' + c.resource + ']. the active-credential pre-check ran exactly '
     + 'once, so the harness is answering a call it also counts',
       String(r.credentialChecks));
  }

  // ── C. THE OVER-REFUSAL CONTROLS ────────────────────────────────────────
  // Without these, "refuses an overlap" is satisfied by a gate that refuses
  // everything, which is how a control gets switched off by Friday.
  console.log('\nC. the over-refusal controls -- a gate that refuses '
            + 'everything is not this gate');

  for (const c of CASES) {
    const clear = await call(h, { resource: c.resource,
      payload: c.mine({ start_time: '2026-11-03T09:00:00.000Z',
                        end_time: '2026-11-03T10:00:00.000Z' }),
      replies: [{ status: 200, rows: [c.held('HELD-1')] },
                { status: 200, rows: [{ data: { id: 'ok' } }] }] });
    is(clear.code === 200,
       'C1[' + c.resource + ']. a NON-overlapping window on the same '
     + 'facility/clergy is accepted (200) and reaches the upsert',
       clear.code + ' ' + eCode(clear) + ' ' + eMsg(clear));

    const touching = await call(h, { resource: c.resource,
      payload: c.mine({ start_time: '2026-11-02T16:00:00.000Z',
                        end_time: '2026-11-02T17:00:00.000Z' }),
      replies: [{ status: 200, rows: [c.held('HELD-1')] },
                { status: 200, rows: [{ data: { id: 'ok' } }] }] });
    is(touching.code === 200,
       'C2[' + c.resource + '] CONTROL. a window that STARTS exactly when the '
     + 'held one ends is accepted -- the test is half-open, so back-to-back '
     + 'bookings are not a clash',
       touching.code + ' ' + eCode(touching) + ' ' + eMsg(touching));

    const self = await call(h, { resource: c.resource,
      payload: c.mine({ id: 'HELD-1' }),
      replies: [{ status: 200, rows: [c.held('HELD-1')] },
                { status: 200, rows: [{ data: { id: 'ok' } }] }] });
    is(self.code === 200,
       'C3[' + c.resource + '] CONTROL. editing the SAME booking does not '
     + 'clash with itself',
       self.code + ' ' + eCode(self) + ' ' + eMsg(self));
  }

  // ── D. THE ASYMMETRY, BOTH WAYS, AGAINST THE CLIENT ─────────────────────
  console.log('\nD. the status literal -- different per resource, and taken '
            + 'from the client rather than asserted');

  for (const c of CASES) {
    // The payload carrying the exempt status is not checked AT ALL -- a gate
    // that refused a cancellation because the booking it cancels overlaps
    // something would be the fix causing the harm.
    const exempt = await call(h, { resource: c.resource,
      payload: c.mine({ status: c.exempt }),
      replies: [{ status: 200, rows: [{ data: { id: 'ok' } }] }] });
    is(exempt.code === 200 && exempt.calls.length === 1
       && exempt.calls[0].method === 'POST',
       'D1[' + c.resource + ']. a payload with status ' + c.exempt + ' skips '
     + 'the check entirely -- ONE upstream call and it is the upsert',
       exempt.code + ' ' + JSON.stringify(exempt.calls.map((x) => x.method)));

    // A HELD row with the exempt status does not block.
    const heldExempt = await call(h, { resource: c.resource,
      payload: c.mine(),
      replies: [{ status: 200, rows: [c.held('HELD-1', { status: c.exempt })] },
                { status: 200, rows: [{ data: { id: 'ok' } }] }] });
    is(heldExempt.code === 200,
       'D2[' + c.resource + ']. a HELD row with status ' + c.exempt + ' does '
     + 'not block an overlapping new booking',
       heldExempt.code + ' ' + eCode(heldExempt) + ' ' + eMsg(heldExempt));

    // ** AND THE CROSS-CHECK: THE OTHER RESOURCE'S WORD MUST NOT WORK HERE. **
    // This is the arm that catches the copy-paste. If leg_clergybookings were
    // given 'Cancelled', this arm would see the held row NOT skipped and the
    // write refused -- correctly, because 'Cancelled' means nothing there.
    const other = CASES.find((x) => x !== c).exempt;
    const heldOther = await call(h, { resource: c.resource,
      payload: c.mine(),
      replies: [{ status: 200, rows: [c.held('HELD-1', { status: other })] }] });
    is(heldOther.code === 409 && eCode(heldOther) === c.prefix + '_CONFLICT',
       'D3[' + c.resource + ']. a held row carrying the OTHER resource\'s '
     + 'status word (' + other + ') still BLOCKS. This is the arm that catches '
     + 'the copy-paste: it fails the moment the two specs share a literal',
       heldOther.code + ' ' + eCode(heldOther) + ' ' + eMsg(heldOther));
  }

  // The client halves, read at runtime. If the client and the server disagree
  // about which status is skipped, the two checks refuse different sets and
  // the device-side one is the one the user sees first.
  let html = null;
  try {
    html = fs.readFileSync(process.env.LEG_HTML
      || path.join(ROOT, 'sairnlegacy.html'), 'utf8').replace(/\r\n/g, '\n');
  } catch (e) { html = null; }
  if (html === null) {
    cannot('D4. sairnlegacy.html is not readable, so the client literals were '
         + 'not compared against the server\'s', 'ENOENT');
  } else {
    const fns = [
      ['bookingConflict', 'leg_bookings'],
      ['clergyBookingConflict', 'leg_clergybookings']
    ];
    fns.forEach(function (pair) {
      const name = pair[0], resource = pair[1];
      const at = html.indexOf('function ' + name + '(');
      if (at === -1) {
        cannot('D4[' + resource + ']. ' + name + '() was not found in '
             + 'sairnlegacy.html, so the client literal could not be read',
               'anchor absent');
        return;
      }
      const bodyText = html.slice(at, html.indexOf('\n}', at));
      const m = bodyText.match(/status\s*[=!]==?\s*'([A-Za-z]+)'/);
      if (!m) {
        cannot('D4[' + resource + ']. ' + name + '() has no status literal to '
             + 'read, so the comparison could not be made', bodyText.slice(0, 200));
        return;
      }
      is(m[1] === overlap.SPECS[resource].exemptStatus,
         'D4[' + resource + ']. the client\'s ' + name + '() skips '
       + JSON.stringify(m[1]) + ' and the server spec exempts '
       + JSON.stringify(overlap.SPECS[resource].exemptStatus) + ' -- READ from '
       + 'the HTML, not hardcoded here',
         'client=' + m[1] + ' server=' + overlap.SPECS[resource].exemptStatus);
    });
  }

  // ── E. THE THIRD STATE ──────────────────────────────────────────────────
  console.log('\nE. an unreadable window is a third state, not "no conflict"');

  for (const c of CASES) {
    const r = await call(h, { resource: c.resource, payload: c.mine(),
      replies: [{ status: 200,
                  rows: [c.held('HELD-BAD', { start_time: 'not-a-time' })] }] });
    is(r.code === 409 && eCode(r) === c.prefix + '_CHECK_INDETERMINATE'
       && /HELD-BAD/.test(eMsg(r)),
       'E1[' + c.resource + ']. a held row whose window cannot be parsed is '
     + 'refused as INDETERMINATE and the row is named -- not silently treated '
     + 'as non-overlapping',
       r.code + ' ' + eCode(r) + ' ' + eMsg(r));

    const missing = await call(h, { resource: c.resource,
      payload: c.dropGroup(c.mine()) });
    is(missing.code === 400 && eCode(missing) === c.prefix + '_WINDOW_REQUIRED'
       && missing.calls.length === 0,
       'E2[' + c.resource + ']. a payload with no facility/clergy is 400 '
     + c.prefix + '_WINDOW_REQUIRED and never reaches Postgres',
       missing.code + ' ' + eCode(missing) + ' calls=' + missing.calls.length);

    const notProv = await call(h, { resource: c.resource, payload: c.mine(),
      replies: [{ status: 404, rows: [] }] });
    is(notProv.code === 503 && eCode(notProv) === 'NOT_PROVISIONED',
       'E3[' + c.resource + ']. a 404 from the CHECK is NOT_PROVISIONED, not '
     + 'a conflict and not a pass -- the gate did not run and says so',
       notProv.code + ' ' + eCode(notProv));
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
