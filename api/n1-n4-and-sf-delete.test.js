// api/n1-n4-and-sf-delete.test.js
//
// Run:  node api/n1-n4-and-sf-delete.test.js
//
// The four findings fourth's b18 Tier A discharge left open at HEAD (N1-N4),
// plus the two SAIRNfreedom delete defects (F6) that document reported and
// nobody had driven.
//
//   N1  a recorded clock_in_at could be OVERWRITTEN with no trail, on a path
//       any caregiver reaches on their own visit
//   N2  sen-auth `setup` could demote the LAST owner, after which nothing can
//       provision -- `set_active` has been guarded against the same end state
//       since the lifecycle module was written
//   N3  a requirement that EXCLUDED this person's position vanished from the
//       response with no disclosure anywhere
//   N4  three comments claimed a driven arm that does not exist, and the
//       hire-date check is shape-only so an impossible date became an
//       impossible window start on a regulated finding
//   F6  sfDeleteEvent announced "Event and its bingo session removed" having
//       removed nothing, and sfDeleteSession created the stale pointer that
//       made it do so
//
// EVERY BEHAVIOURAL ARM DRIVES THE REAL CODE -- the handler for N1/N2/N3/N4,
// and the two SAIRNfreedom functions EXTRACTED FROM THE HTML AND RUN. A
// reimplementation would pass against the unfixed code, which is the failure
// mode this platform keeps paying for.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '..');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['n1n4', 'fixture', String(process.pid)].join('-');
// api/sen-auth.js refuses 500 without these, which is correct and is NOT what
// N2 is about -- an arm that fails on a missing env var is measuring the
// fixture. Named here rather than discovered twice.
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');
let LIC_APP = 'sairnsenior';

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
      trial_ends_at: null, stripe_subscription_id: null, app_id: LIC_APP })
  }
};
const { signSessionToken } = require('./_lib/auth');
delete require.cache[require.resolve('./sd-data.js')];
const handler = require('./sd-data.js');
delete require.cache[require.resolve('./sen-auth.js')];
const senAuth = require('./sen-auth.js');

const rules = require('./_lib/compliance-rules');

// ── THE VISIT ROW IS THE FIXTURE, because N1 is entirely about what is
//    ALREADY in it. `writes` records every POST so an arm can assert that a
//    refusal wrote NOTHING -- a 409 that still upserted is not a refusal.
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

async function visitWrite(payload) {
  writes.length = 0;
  global.fetch = senFetch();
  const res = mockRes();
  await handler({ method: 'POST',
    headers: { authorization: 'Bearer ' + KEY,
               'x-sd-auth': signSessionToken({ app: 'sairnsenior',
                 employee_id: 'E1', role: 'caregiver', license_hash: HASH }) },
    body: { action: 'write', resource: 'sen_visits', payload: payload } }, res);
  return { res: res, writes: writes.slice() };
}

console.log('N1-N4 and the SAIRNfreedom deletes -- criteria 2026-10-14.1\n');

(async () => {
  // ── N1. A RECORDED CLOCK TIME IS NOT OVERWRITABLE ───────────────────────
  console.log('N1. a recorded EVV clock time cannot be replaced silently');

  VISIT = { visit_id: 'V1', assigned_employee_id: 'E1',
            data: { status: 'scheduled' } };
  {
    const { res } = await visitWrite({ id: 'V1', clock_in_at: '2026-10-14T09:00:00.000Z' });
    is(res.statusCode === 200,
       'N1a. CONTROL -- a FIRST clock-in on a visit with none recorded is '
     + 'accepted. Without this arm the fix could be "refuse every clock write" '
     + 'and every arm below would still pass',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }

  VISIT = { visit_id: 'V1', assigned_employee_id: 'E1',
            data: { status: 'in_progress', clock_in_at: '2026-10-14T09:00:00.000Z' } };
  {
    const { res, writes: w } = await visitWrite(
      { id: 'V1', clock_in_at: '2026-10-14T08:15:00.000Z' });
    // ── SUPERSEDED BY MICHAEL'S T16 DECISION, 2026-10-15 ─────────────────
    // This arm asserted 409 CLOCK_ALREADY_RECORDED with nothing written. The
    // refusal closed the overwrite and left a hole beside it: the only other
    // route is scheduler-only, so a caregiver who clocked in at the wrong time
    // on their own visit had NO route at all. The decision is keep the
    // original and APPEND a correction record, pending a scheduler's approval.
    // What the arm now asserts is the part that must still hold -- the
    // recorded value does not move -- and the full contract is driven in
    // api/t16-clock-correction-record.test.js. Rewritten rather than deleted,
    // so the boundary stays covered here too.
    const n1Stored = w.length ? (JSON.parse(w[w.length - 1].body).data || {}) : {};
    is(res.statusCode === 200
       && n1Stored.clock_in_at === '2026-10-14T09:00:00.000Z'
       && (n1Stored.clock_corrections || []).length === 1,
       'N1b. THE ARM THE WHOLE SECTION IS FOR -- a DIFFERENT clock_in_at over a '
     + 'recorded one does NOT replace it: the original is still on the row and '
     + 'the submission is appended to the correction trail. This module\'s own '
     + 'words: "a state audit that finds an edited time with no trail cannot '
     + 'tell a typo correction from a fabrication"',
       'status=' + res.statusCode + ' code=' + eCode(res)
     + ' stored=' + JSON.stringify(n1Stored).slice(0, 200));
  }
  {
    const { res } = await visitWrite(
      { id: 'V1', clock_in_at: '2026-10-14T09:00:00.000Z' });
    is(res.statusCode === 200,
       'N1c. CONTROL -- an IDENTICAL re-send is still accepted. sairnsenior '
     + 'queues clock events offline and replays them UNCHANGED, so the same '
     + 'visit legitimately arrives twice; refusing that would break the replay '
     + 'path this module is written around',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }
  {
    const { res } = await visitWrite(
      { id: 'V1', clock_out_at: '2026-10-14T13:00:00.000Z' });
    is(res.statusCode === 200,
       'N1d. CONTROL -- the OTHER half of the visit still writes. The guard is '
     + 'per field, so a clock-out after a recorded clock-in is the normal case '
     + 'and is not collateral damage',
       'status=' + res.statusCode + ' code=' + eCode(res));
  }
  {
    VISIT = { visit_id: 'V1', assigned_employee_id: 'E1',
              data: { clock_in_at: '2026-10-14T09:00:00.000Z',
                      clock_out_at: '2026-10-14T13:00:00.000Z' } };
    const { res, writes: w } = await visitWrite(
      { id: 'V1', clock_out_at: '2026-10-14T17:00:00.000Z' });
    // Superseded the same way as N1b -- the rule is now append-not-replace.
    const n1e = w.length ? (JSON.parse(w[w.length - 1].body).data || {}) : {};
    is(res.statusCode === 200
       && n1e.clock_out_at === '2026-10-14T13:00:00.000Z'
       && (n1e.clock_corrections || []).length === 1
       && (n1e.clock_corrections || [])[0].field === 'clock_out_at',
       'N1e. ...and clock_out_at is covered too, not just clock_in_at. A rule '
     + 'proven on one of two fields is a rule that covers one of two fields',
       'status=' + res.statusCode + ' stored=' + JSON.stringify(n1e).slice(0, 200));
  }

  // ── N2. setup CANNOT DEMOTE THE LAST OWNER ──────────────────────────────
  console.log('\nN2. sen-auth setup cannot leave the licence with no Owner');

  let ROSTER = [];
  function authFetch() {
    return async function (url, init) {
      const method = (init && init.method) || 'GET';
      if (method === 'GET') {
        return { ok: true, status: 200, headers: { get: () => '' },
                 text: async () => '[]', json: async () => ROSTER };
      }
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => [JSON.parse(init.body)] };
    };
  }
  async function setup(employee_id, role) {
    LIC_APP = 'sairnsenior';
    global.fetch = authFetch();
    const res = mockRes();
    await senAuth({ method: 'POST',
      headers: { authorization: 'Bearer ' + KEY,
                 'x-sd-auth': signSessionToken({ app: 'sairnsenior',
                   employee_id: 'OWN1', role: 'owner', license_hash: HASH }) },
      body: { action: 'setup', employee_id: employee_id, pin: '123456',
              role: role } }, res);
    return res;
  }

  ROSTER = [{ employee_id: 'OWN1', role: 'owner', active: true,
              display_name: 'Owner One' }];
  {
    const res = await setup('OWN1', 'caregiver');
    is(res.statusCode !== 200,
       'N2a. the SOLE active Owner cannot be re-roled to caregiver by setup ('
     + res.statusCode + ' ' + eCode(res) + '). set_active has been guarded '
     + 'against the same end state since the lifecycle module was written; '
     + 'setup reached it through the ROLE instead of the active flag',
       'status=' + res.statusCode + ' body=' + JSON.stringify(res.body).slice(0, 200));
  }
  ROSTER = [{ employee_id: 'OWN1', role: 'owner', active: true },
            { employee_id: 'OWN2', role: 'owner', active: true }];
  {
    const res = await setup('OWN1', 'caregiver');
    is(res.statusCode === 200,
       'N2b. CONTROL -- with a SECOND active Owner the same call succeeds. '
     + 'Without this arm the fix could be "never change an owner\'s role" and '
     + 'N2a would still pass',
       'status=' + res.statusCode + ' body=' + JSON.stringify(res.body).slice(0, 160));
  }
  ROSTER = [{ employee_id: 'OWN1', role: 'owner', active: true }];
  {
    const res = await setup('NEW1', 'caregiver');
    is(res.statusCode === 200,
       'N2c. CONTROL -- provisioning a NEW caregiver while one Owner exists is '
     + 'untouched. The guard is about the target being the last Owner, not '
     + 'about the roster size',
       'status=' + res.statusCode);
  }
  {
    const res = await setup('OWN1', 'owner');
    is(res.statusCode === 200,
       'N2d. CONTROL -- re-running setup on the sole Owner AS an owner (a PIN '
     + 'reset) still works. A guard that blocked that would lock the one '
     + 'person who can fix anything out of their own password',
       'status=' + res.statusCode);
  }

  // ── N3. AN EXCLUDED POSITION IS VISIBLE ON THE RESPONSE ─────────────────
  console.log('\nN3. a requirement that excluded this position is disclosed');

  {
    // THE FIXTURE SHAPE IS THE ONE evaluateTraining REALLY TAKES -- a LIST of
    // rule rows, each with `data`, plus opts -- read off the real call site in
    // api/_lib/compliance-rules-staff-join.test.js:99 rather than guessed. A
    // guessed shape threw `(rules || []).filter is not a function`, which is
    // the arm failing about itself.
    const RULE = [{ rule_id: 'TEST-1', state: 'XX', requirement_type: 'training',
                    facility_class: 'alf', effective_from: '2020-01-01',
                    data: { requirements: [
                      { who: 'nursing', annual_hours: 8,
                        applies_to_positions: ['nursing'] },
                      { who: 'all', annual_hours: 4, audience: 'all_staff' }
                    ] } }];
    const out = rules.evaluateTraining(RULE, {
      state: 'XX', facility_class: 'alf', on_date: '2026-06-01',
      staff: [{ staff_id: 'S1', name: 'A Caregiver', position: 'caregiver',
                annual_hours_recorded: 4 }] });
    const f = (out && out.staff_findings && out.staff_findings[0]) || null;
    if (!f) {
      cannot('N3a. evaluateTraining returned no staff finding, so the '
           + 'disclosure could not be measured',
             JSON.stringify(out).slice(0, 200));
      cannot('N3b. depends on N3a', 'no finding');
    } else {
      const ex = f.excluded_by_position;
      // THE ASSERTION IS ON THE KEY AND THE HOURS, not on the word "nursing"
      // appearing in the reason. The first draft grepped the serialised entry
      // for 'nursing' and FAILED against correct code: matchAudience's reason
      // names the STAFF position being tested ("position caregiver against the
      // requirement's declared position list"), not the list's contents. An
      // arm that greps prose is an arm that measures prose.
      is(Array.isArray(ex) && ex.length === 1
         && ex[0].key === 'TEST-1#0' && ex[0].annual_hours === 8,
         'N3a. a requirement that returned a clean `false` for this position is '
       + 'listed in `excluded_by_position` with the reason matchAudience gave. '
       + 'It used to vanish: `unmapped_requirements` is built only from '
       + 'STRUCTURALLY unmappable rows, so a row WITH a position list never '
       + 'appeared there no matter who it excluded',
         JSON.stringify(ex));
      is(typeof f.excluded_by_position_caveat === 'string'
         && /not in `required_annual_hours`/.test(f.excluded_by_position_caveat),
         'N3b. ...and the caveat says the excluded hours are NOT in '
       + '`required_annual_hours`, because under-inclusion that nobody can see '
       + 'is indistinguishable from the requirement not existing -- which was '
       + 'the author\'s own self-flag on this point',
         String(f.excluded_by_position_caveat).slice(0, 120));
    }
  }
  {
    // ABSENT WHEN NOTHING WAS EXCLUDED. A key present on every finding with an
    // empty list is a key a reader stops reading.
    const RULE = [{ rule_id: 'TEST-2', state: 'XX', requirement_type: 'training',
                    facility_class: 'alf', effective_from: '2020-01-01',
                    data: { requirements: [
                      { who: 'all', annual_hours: 4, audience: 'all_staff' }] } }];
    const out = rules.evaluateTraining(RULE, {
      state: 'XX', facility_class: 'alf', on_date: '2026-06-01',
      staff: [{ staff_id: 'S1', position: 'caregiver', annual_hours_recorded: 4 }] });
    const f = (out && out.staff_findings && out.staff_findings[0]) || {};
    is(f.excluded_by_position === undefined,
       'N3c. CONTROL -- the key is ABSENT when nothing was excluded, not an '
     + 'empty array on every finding',
       JSON.stringify(f.excluded_by_position));
  }

  // ── N4. THE COMMENTS, AND THE SHAPE-ONLY HIRE DATE ──────────────────────
  console.log('\nN4. no comment claims an arm that does not exist');

  {
    const src = fs.readFileSync(path.join(__dirname, '_lib/compliance-rules.js'), 'utf8');
    // The three claims fourth measured. Each must now either be gone or say
    // out loud that it was a hand-drive.
    const claims = [
      ['and an arm drives that', 'the leap-day normalisation'],
      ['Driven: hire 2024-11-03', 'the anniversary boundary']
    ];
    const left = claims.filter((c) => src.indexOf(c[0]) !== -1);
    is(left.length === 0,
       'N4a. neither bare "driven" claim survives in '
     + 'api/_lib/compliance-rules.js. They most likely meant DRIVEN BY HAND, '
     + 'which is a real activity -- the defect is that a hand-drive leaves no '
     + 'artefact, so six weeks later the comment is the only evidence and it '
     + 'reads like a reference to a committed arm',
       left.map((c) => c[1]).join(', '));
    is(/NO COMMITTED ARM/.test(src) && /routed to cody/i.test(src),
       'N4b. ...and the replacement says what IS true -- driven by hand, no '
     + 'committed arm, the arms routed to cody. True, cheap, and it tells the '
     + 'next reader exactly what to distrust',
       'the corrected wording was not found');
  }
  {
    // THE SHAPE-ONLY HIRE DATE, DRIVEN. fourth reported '2024-02-30' -> a
    // window start of '2026-02-30'. Driving it found that case AND a worse one
    // the report did not reach: an impossible MONTH, which the day-decrement
    // normalisation cannot touch at all.
    const bad = [];
    // '2024-04-31' IS IN THIS LIST AND IT MOVED HERE FROM THE CONTROL BELOW.
    // The first draft of N4d expected it to normalise to 2026-04-30, because
    // the day-decrement normalisation does exactly that to a computed window
    // START. It does NOT apply to the hire date itself: April 31 is not a day
    // anybody was hired on, so the hire is refused one step earlier -- which is
    // the behaviour this batch introduced and the right one. The arm was
    // encoding the old path, and it failed loudly rather than quietly agreeing.
    for (const hire of ['2024-02-30', '2024-13-01', '2024-99-99', '2024-04-31']) {
      const r = rules.hoursInWindow([], 'rolling_12_months_from_hire',
                                    '2026-06-01', null, hire);
      if (r.window_from !== null || !r.window_error) {
        bad.push(hire + ' -> window_from=' + JSON.stringify(r.window_from)
               + ' err=' + JSON.stringify(r.window_error));
      }
    }
    is(bad.length === 0,
       'N4c. an impossible hire date yields NO window and a named '
     + 'window_error, instead of an impossible window start printed on a '
     + 'regulated finding. REFUSED, NOT REPAIRED: normalising 2024-02-30 would '
     + 'be this code choosing which date somebody was hired on',
       bad.join('; '));
    const good = [];
    for (const hire of ['2024-02-29', '2024-11-03', '2024-12-31']) {
      const r = rules.hoursInWindow([], 'rolling_12_months_from_hire',
                                    '2026-06-01', null, hire);
      if (!r.window_from || r.window_error) {
        good.push(hire + ' -> ' + JSON.stringify(r.window_from) + ' '
                + JSON.stringify(r.window_error));
      }
    }
    is(good.length === 0,
       'N4d. CONTROL -- a REAL leap-day hire and a real end-of-year hire still '
     + 'compute a window (2024-02-29 -> 2026-02-28 by the day-decrement '
     + 'normalisation, 2024-12-31 -> 2025-12-31). The refusal is for dates that '
     + 'are not dates; a date that merely has no counterpart in the target year '
     + 'is still normalised, and that distinction is the whole of it',
       good.join('; '));
  }

  // ── F6. THE TWO SAIRNfreedom DELETES, EXTRACTED AND RUN ─────────────────
  console.log('\nF6. sfDeleteEvent reported a removal that did not happen');

  {
    const html = fs.readFileSync(path.join(ROOT, 'sairnfreedom.html'), 'utf8');
    function grab(name) {
      const m = new RegExp('function\\s+' + name + '\\s*\\(').exec(html);
      if (!m) return null;
      const o = html.indexOf('{', m.index);
      let d = 0, k = o;
      for (; k < html.length; k++) {
        if (html[k] === '{') d++;
        else if (html[k] === '}') { d--; if (d === 0) break; }
      }
      return html.slice(m.index, k + 1);
    }
    const delEv = grab('sfDeleteEvent');
    const delSe = grab('sfDeleteSession');
    if (!delEv || !delSe) {
      cannot('F6a. one of the two delete functions could not be extracted from '
           + 'sairnfreedom.html', 'delEv=' + !!delEv + ' delSe=' + !!delSe);
      cannot('F6b. depends on F6a', 'extraction');
      cannot('F6c. depends on F6a', 'extraction');
    } else {
      function world(events, sessions) {
        const store = { K_EVENTS: events, K_SESSIONS: sessions };
        const ctx = {
          Object, JSON, String, Number, Array,
          K_EVENTS: 'K_EVENTS', K_SESSIONS: 'K_SESSIONS',
          toasts: [],
          st: function (k, v) { store[k] = v; },
          getEvents: function () { return store.K_EVENTS; },
          getSessions: function () { return store.K_SESSIONS; },
          sfRenderAll: function () {},
          store: store
        };
        ctx.toast = function (t) { ctx.toasts.push(String(t)); };
        vm.createContext(ctx);
        vm.runInContext(delEv + '\n' + delSe, ctx);
        return ctx;
      }

      // THE DEFECT, END TO END: delete the session, then delete the event.
      const w = world([{ id: 'EV1', sessionId: 'SS1' }], [{ id: 'SS1' }]);
      w.sfDeleteSession('SS1');
      const pointerCleared = !(w.store.K_EVENTS[0] || {}).sessionId;
      is(pointerCleared,
         'F6a. sfDeleteSession CLEARS the event\'s sessionId. It used to remove '
       + 'the session and leave the pointer, and the UI offers Remove on every '
       + 'session row -- so the stale pointer was one click away',
         'event after delete: ' + JSON.stringify(w.store.K_EVENTS[0]));
      w.toasts.length = 0;
      w.sfDeleteEvent('EV1');
      const t = w.toasts[0] || '';
      is(!/Event and its bingo session removed/.test(t),
         'F6b. ...and deleting that event does NOT announce "Event and its '
       + 'bingo session removed", because no session was removed. The toast '
       + 'used to be chosen on the POINTER being truthy and never on whether '
       + 'the filter matched -- affirmative false success, which is worse than '
       + 'silence because it tells the operator a thing happened. Said: '
       + JSON.stringify(t.slice(0, 80)),
         'toast=' + JSON.stringify(t));

      // AND THE HONEST POSITIVE. With the session still present, the original
      // message is correct and must survive.
      const w2 = world([{ id: 'EV1', sessionId: 'SS1' }], [{ id: 'SS1' }]);
      w2.sfDeleteEvent('EV1');
      is(/Event and its bingo session removed/.test(w2.toasts[0] || '')
         && w2.store.K_SESSIONS.length === 0,
         'F6c. CONTROL -- when the session IS there, it is removed and the '
       + 'original message is still the one shown. The fix is to report the '
       + 'OUTCOME, not to stop reporting',
         'toast=' + JSON.stringify(w2.toasts[0])
       + ' sessions=' + w2.store.K_SESSIONS.length);

      // ── F6e ISOLATES sfDeleteEvent'S HALF, AND AN ABLATION IS WHY ───────
      // Reverting sfDeleteEvent's toast to the pointer-based choice left every
      // arm green: F6b runs after F6a has already cleared the pointer, so
      // `ev.sessionId` is undefined and even the OLD code says "Event removed".
      // The two fixes are each sufficient on their own -- good, and it means
      // neither was individually NECESSARY for any arm. This arm builds the
      // stale-pointer state DIRECTLY, which is the state a database that was
      // written before today is already in: events whose sessionId points at a
      // session sfDeleteSession removed without clearing it.
      const w4 = world([{ id: 'EV1', sessionId: 'GONE' }], [{ id: 'SS1' }]);
      w4.sfDeleteEvent('EV1');
      is(!/Event and its bingo session removed/.test(w4.toasts[0] || '')
         && w4.store.K_SESSIONS.length === 1,
         'F6e. an event whose sessionId points at a session that DOES NOT '
       + 'EXIST does not announce a session removal, and the unrelated session '
       + 'survives. This is the state every row written before today is in, so '
       + 'it is the arm that matters after a deploy. Said: '
       + JSON.stringify((w4.toasts[0] || '').slice(0, 70)),
         'toast=' + JSON.stringify(w4.toasts[0])
       + ' sessions=' + w4.store.K_SESSIONS.length);

      const w3 = world([{ id: 'EV2' }], [{ id: 'SS1' }]);
      w3.sfDeleteEvent('EV2');
      is((w3.toasts[0] || '') === 'Event removed'
         && w3.store.K_SESSIONS.length === 1,
         'F6d. CONTROL -- an event with NO session says "Event removed" and '
       + 'leaves the unrelated session alone. Three outcomes, three messages',
         'toast=' + JSON.stringify(w3.toasts[0])
       + ' sessions=' + w3.store.K_SESSIONS.length);
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
