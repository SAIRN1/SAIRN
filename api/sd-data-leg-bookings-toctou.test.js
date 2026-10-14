// api/sd-data-leg-bookings-toctou.test.js
//
// Run:  node api/sd-data-leg-bookings-toctou.test.js
//
// REQUIREMENT: a facility booking cannot be double-booked by a second device
//   holding a stale copy of the calendar, and the device that loses is not left
//   showing a booking the server refused.
//
// ── THE DEFECT, AND WHO FOUND IT ───────────────────────────────────────────
// The hover auditor, H1 batch b25, log seq1370, scanning the `leg_bookings`
// panel. Its override sweep came back CLEAN -- `bookingConflict()` HARD BLOCKS
// and there is no override checkbox anywhere -- and the standard scan then
// found a different, real thing:
//
//     bookingConflict() reads only the LOCAL client-side store -- the exact
//     TOCTOU race leg_merch_units' reservation-lock was explicitly built to
//     close, never applied here.
//
// sairnlegacy.html:2999 is a correct interval-overlap test over `bookings()`,
// which is THIS DEVICE'S localStorage. Two staff on two devices, each holding a
// copy taken before the other's booking synced, both pass their own check and
// both write; the second write is accepted because a new booking carries a new
// booking_id and nothing collides. The thing double-booked is a chapel, a
// removal van, or -- because leg_facilities seeds row FC-3 as
// `{type:'Staff', name:'Maria Chen', notes:'Funeral Director'}` -- a named
// member of staff, against a specific death case and a time window.
//
// ── WHY THIS SUITE EXISTS SEPARATELY FROM tests/sairnlegacy_reservation_lock.js
// That suite owns the MERCHANDISE lock and asserts, correctly, that reserving
// takes exactly ONE upstream call, "because a read-then-write that happens to
// answer 409" is a weaker thing than an atomic conditional PATCH. This gate IS
// a read-then-write, for reasons api/sd-data.js's own branch comment sets out
// (a new booking has no row to PATCH; PostgREST has no INSERT ... WHERE NOT
// EXISTS; an EXCLUDE constraint over tstzrange cannot be indexed against a
// window living in `data` jsonb, because text::timestamptz is STABLE and not
// IMMUTABLE). Folding it into that suite would have meant weakening that
// suite's central assertion to accommodate a different mechanism.
//
// SO THIS SUITE ASSERTS THE WINDOW IT ACTUALLY CLOSES AND THE ONE IT DOES NOT.
// Arm 2 asserts the SELECT-then-refuse shape by COUNTING the upstream calls --
// which is the same measurement the merch suite makes, read the other way, so
// that nobody reading either file can come away thinking these are the same
// control.
//
// ── PROVEN TO FAIL BEFORE THE FIX, AND HOW TO REPRODUCE THAT ───────────────
// A test written after the code it tests is worth nothing until it has been run
// against the code WITHOUT the fix. Set SD_DATA_HANDLER to the basename of an
// alternative handler inside api/ and this suite drives that file instead:
//
//     git show <pre-fix sha>:api/sd-data.js > api/.sd-data-prefix-control.js
//     SD_DATA_HANDLER=.sd-data-prefix-control.js \
//       node api/sd-data-leg-bookings-toctou.test.js     # must FAIL
//     rm api/.sd-data-prefix-control.js
//
// It must sit inside api/ because the handler's own requires are relative. The
// measured result is recorded in the commit message and in
// docs/SAIRN-handoff-hank-b8.md rather than here, because a result written into
// the file that produced it is the one place it cannot be checked from.

'use strict';
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
// Assembled rather than written as a literal, so this file carries nothing
// credential-shaped. Set BEFORE api/_lib/auth.js is required -- it reads the
// secret at module load, and a token signed against a different one fails with
// an indistinguishable 401.
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['sairnlegacy', 'bookings', 'fixture', String(process.pid)].join('-');

const HANDLER = path.join(__dirname,
  process.env.SD_DATA_HANDLER || 'sd-data.js');
const LEG = require(path.join(ROOT, 'api/_resources/sairnlegacy.js'));
// LEG_HTML is the client-half half of the same ablation, and the name is taken
// from tests/sairnlegacy_reservation_lock.js rather than invented, so one
// convention covers both suites that drive this app's client code.
const HTML = fs.readFileSync(process.env.LEG_HTML
  || path.join(ROOT, 'sairnlegacy.html'), 'utf8').replace(/\r\n/g, '\n');

const LICENSE_KEY = 'k';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');
const LEG_TOKEN = require(path.join(ROOT, 'api/_lib/auth')).signSessionToken({
  app: 'sairnlegacy', employee_id: 'emp-1', role: 'director',
  license_hash: LIC_HASH });

// ── EVERY ARM MUST BE ABLE TO FAIL WITHOUT KILLING THE RUN ────────────────
// Found by the ablation this suite was written to pass: with the pre-fix
// handler, `r.body.error.message` threw on an arm whose whole point is that
// there IS no error, the process died, and the six arms after it were never
// measured at all. A suite that stops at its first unexpected shape reports a
// SMALLER failure count than the truth, which is the direction that reads as
// reassuring.
const eCode = (r) => (r && r.body && r.body.error && r.body.error.code) || '';
const eMsg = (r) => (r && r.body && r.body.error && r.body.error.message) || '';

let n = 0, bad = 0;
function ok(cond, label) {
  if (cond) { console.log('  ok   ' + label); n++; }
  else { console.log('  FAIL ' + label); bad++; }
}
function section(s) { console.log('\n' + s); }

function loadHandler() {
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}

// Drives the REAL handler and RECORDS EVERY UPSTREAM CALL, same shape as
// tests/sairnlegacy_reservation_lock.js. The URLs and the call COUNT are part
// of the assertion, not scaffolding: "the server decides" is a claim about what
// goes to Postgres.
//
// TWO UPSTREAM CALLS ARE ANSWERED BY THE HARNESS AND DELIBERATELY NOT COUNTED,
// and both are named rather than swallowed:
//
//   * the licence row, which every request in this handler reads first.
//   * the ACTIVE-CREDENTIAL pre-check. api/_lib/auth.js's credentialStillActive
//     costs one indexed lookup per gated request -- its own comment says so --
//     and it runs before any resource branch. Folding it into out.calls would
//     make every count arm below read 2 instead of 1 and would bury the number
//     this suite is actually measuring.
//
// out.credentialChecks COUNTS IT ANYWAY, and arm 0 asserts it is exactly 1.
// A harness that answers a call without counting it is one commit away from
// answering a call nobody knows is being made.
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
      // The licence row. app_id null = the documented unattributable fallback.
      return { ok: true, status: 200,
               json: async () => [{ status: 'active', app_id: null }] };
    }
    if (/_employee_auth\?.*&select=active&limit=1/.test(String(url))) {
      out.credentialChecks++;
      return { ok: true, status: 200,
               json: async () => (opts.deactivated ? [{ active: false }]
                                                   : [{ active: true }]) };
    }
    out.calls.push({ url: String(url), method: (init && init.method) || 'GET',
                     body: (init && init.body) || null,
                     prefer: (init && init.headers && init.headers.Prefer) || null });
    const r = replies.length ? replies.shift() : { status: 200, rows: [] };
    return { ok: r.status >= 200 && r.status < 300, status: r.status,
             json: async () => (r.rows === undefined ? [] : r.rows) };
  };
  try {
    await handler({ method: 'POST',
                    headers: { authorization: 'Bearer ' + LICENSE_KEY,
                               'x-sd-auth': opts.noSession ? '' : LEG_TOKEN },
                    body: { action: opts.action || 'write',
                            resource: opts.resource,
                            app_id: 'sairnlegacy',
                            payload: opts.payload === undefined ? {} : opts.payload } },
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

// A server row as PostgREST hands it back: the id column plus the jsonb.
const row = (id, over) => ({ booking_id: id,
  data: Object.assign({ id: id, facility_id: 'FC-1', case_id: 'CS-1',
                        start_time: '2026-11-02T14:00:00.000Z',
                        end_time: '2026-11-02T16:00:00.000Z',
                        purpose: 'Service', status: 'Scheduled' }, over || {}) });
// The booking THIS device is trying to save -- a different case, the same room,
// an overlapping hour, and an id the server has never seen. Exactly what a
// second device with a stale calendar produces.
const BK = (over) => Object.assign({ id: 'BK-NEW', facility_id: 'FC-1',
  case_id: 'CS-2', start_time: '2026-11-02T15:00:00.000Z',
  end_time: '2026-11-02T17:00:00.000Z', purpose: 'Second service',
  status: 'Scheduled' }, over || {});

console.log('leg_bookings -- the double-booking race the client half could not '
            + 'see\n(handler under test: api/' + path.basename(HANDLER) + ')\n');

(async () => {
  const h = loadHandler();

  // ── 0. THE FIXTURE IS REAL ────────────────────────────────────────────────
  section('0. the fixture');
  ok(LEG.resources.indexOf('leg_bookings') !== -1,
     'leg_bookings is a registered SAIRNlegacy resource');
  ok(LEG.resources.indexOf('leg_facilities') !== -1,
     'and so is leg_facilities -- the thing being double-booked');
  {
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              noSession: true });
    ok(r.code === 401 && eCode(r) === 'NO_SESSION',
       'the resource is session-gated, so every arm below is driving a '
       + 'SIGNED-IN write and not an anonymous one -- ' + r.code);
    ok(r.calls.length === 0,
       '...and an unsigned-in write reaches the database ZERO times');
  }
  {
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              replies: [{ status: 200, rows: [] },
                                        { status: 201, rows: [{ data: BK() }] }] });
    ok(r.credentialChecks === 1,
       'the active-credential pre-check runs exactly once per write, and the '
       + 'harness answers it WITHOUT counting it, so every call count below is '
       + 'the booking gate alone -- ' + r.credentialChecks);
    ok(r.code === 200, '...and that signed-in write with a free room succeeds, '
       + 'which is the baseline every arm below is measured against -- ' + r.code);
  }
  {
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              deactivated: true,
                              replies: [{ status: 200, rows: [] }] });
    ok(r.code === 403 && eCode(r) === 'CREDENTIAL_INACTIVE'
       && r.calls.length === 0,
       'and a DEACTIVATED credential is refused before the booking gate runs, '
       + 'so the arm above is not passing because the harness always says '
       + 'active -- ' + r.code + ', ' + r.calls.length + ' call(s)');
  }

  // ── 1. THE RACE ITSELF ────────────────────────────────────────────────────
  // THE ARM THE WHOLE FILE EXISTS FOR. The client's bookingConflict() passed --
  // it had to, because this device's localStorage does not contain BK-1. The
  // server's rows do.
  section('1. a booking the LOCAL check could not see is refused by the server');
  {
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              replies: [{ status: 200, rows: [row('BK-1')] }] });
    ok(r.code === 409, 'the losing device gets 409 -- ' + r.code + ' '
       + JSON.stringify(r.body).slice(0, 160));
    ok(eCode(r) === 'BOOKING_CONFLICT',
       '...with a code the client can branch on, not a bare message');
    ok(/BK-1/.test(eMsg(r)),
       '...and the message names the booking that already holds the room, so '
       + 'the staff member can go and look at it');
    ok(r.calls.length === 1,
       'AND THE WRITE NEVER HAPPENS: exactly one upstream call, the check. A '
       + 'second call here would mean the row was written and then reported as '
       + 'refused. Took ' + r.calls.length);
    ok(r.calls[0].method === 'GET',
       '...and that one call is a read -- ' + r.calls[0].method);
  }

  // ── 2. THE CHECK IS SCOPED, OR IT IS A DIFFERENT BUG ─────────────────────
  // An unscoped check refuses one funeral home's booking because ANOTHER
  // funeral home has the same facility id -- a cross-tenant lockout, which is
  // how a security fix becomes an outage.
  section('2. the check is scoped to this licence and this facility');
  {
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              replies: [{ status: 200, rows: [] },
                                        { status: 201, rows: [{ data: BK() }] }] });
    const q = r.calls[0].url;
    ok(q.indexOf('license_hash=eq.' + LIC_HASH) !== -1,
       'the check filters on license_hash, so one funeral home\'s calendar '
       + 'cannot block another\'s');
    ok(/data->>facility_id=eq\.FC-1/.test(q),
       '...and on the facility, so booking the chapel is not blocked by the '
       + 'removal van -- ' + (q.split('?')[1] || '').slice(0, 110));
    ok(/select=/.test(q), '...and it asks for a projection rather than *');
  }

  // ── 3. IT IS A GATE, NOT A LOCKOUT ───────────────────────────────────────
  section('3. a booking that really is free still saves');
  {
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              replies: [{ status: 200, rows: [row('BK-1', {
                                            start_time: '2026-11-02T08:00:00.000Z',
                                            end_time: '2026-11-02T09:00:00.000Z' }) ] },
                                        { status: 201, rows: [{ data: BK() }] }] });
    ok(r.code === 200, 'a non-overlapping booking on the same facility is saved '
       + '-- ' + r.code + ' ' + JSON.stringify(r.body).slice(0, 120));
    ok(r.calls.length === 2 && r.calls[1].method === 'POST',
       '...and it takes the check plus the upsert, in that order -- '
       + r.calls.map((c) => c.method).join(','));
  }
  {
    // THE BOUNDARY, IN THE DIRECTION THAT COSTS SOMETHING IF IT IS WRONG. Back
    // to back bookings are the normal case for a funeral home: a 10-11 service
    // followed by an 11-12 service in the same chapel. A `<=` instead of a `<`
    // refuses every one of them, and the app looks broken rather than careful.
    const r = await call(h, { resource: 'leg_bookings',
                              payload: BK({ start_time: '2026-11-02T16:00:00.000Z',
                                            end_time: '2026-11-02T18:00:00.000Z' }),
                              replies: [{ status: 200, rows: [row('BK-1')] },
                                        { status: 201, rows: [{ data: BK() }] }] });
    ok(r.code === 200,
       'a booking that STARTS exactly when another ENDS is not a conflict -- '
       + r.code);
  }
  {
    // And the other side of the same boundary.
    const r = await call(h, { resource: 'leg_bookings',
                              payload: BK({ start_time: '2026-11-02T12:00:00.000Z',
                                            end_time: '2026-11-02T14:00:00.000Z' }),
                              replies: [{ status: 200, rows: [row('BK-1')] },
                                        { status: 201, rows: [{ data: BK() }] }] });
    ok(r.code === 200,
       'a booking that ENDS exactly when another STARTS is not a conflict -- '
       + r.code);
  }
  {
    // ONE MINUTE OF OVERLAP IS AN OVERLAP. Without this, the two arms above are
    // satisfied by a check that never fires at all.
    const r = await call(h, { resource: 'leg_bookings',
                              payload: BK({ start_time: '2026-11-02T15:59:00.000Z',
                                            end_time: '2026-11-02T18:00:00.000Z' }),
                              replies: [{ status: 200, rows: [row('BK-1')] }] });
    ok(r.code === 409,
       'one minute of overlap IS a conflict -- without this arm the two above '
       + 'pass on a check that does nothing. ' + r.code);
  }

  // ── 4. A ROW DOES NOT CONFLICT WITH ITSELF ───────────────────────────────
  section('4. a row does not conflict with itself, and a cancelled row holds '
          + 'nothing');
  {
    const r = await call(h, { resource: 'leg_bookings', payload: BK({ id: 'BK-1' }),
                              replies: [{ status: 200, rows: [row('BK-1')] },
                                        { status: 201, rows: [{ data: BK() }] }] });
    ok(r.code === 200,
       're-saving a booking over its own server row is not a conflict with '
       + 'itself -- ' + r.code);
  }
  {
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              replies: [{ status: 200,
                                          rows: [row('BK-1', { status: 'Cancelled' })] },
                                        { status: 201, rows: [{ data: BK() }] }] });
    ok(r.code === 200,
       'a CANCELLED booking does not hold the room -- that is what cancelling '
       + 'it means. ' + r.code);
  }

  // ── 5. CANCELLING IS EXEMPT, AND THAT IS A DECISION ──────────────────────
  // cancelBooking() writes the same record back with status 'Cancelled'. A gate
  // that checked it would refuse a cancellation BECAUSE the booking being
  // cancelled overlaps something -- the fix causing the harm. Asserted by the
  // CALL COUNT, because a 200 alone cannot tell an exemption from a check that
  // happened to pass.
  section('5. cancelling a booking is exempt -- no check at all');
  {
    const r = await call(h, { resource: 'leg_bookings',
                              payload: BK({ status: 'Cancelled' }),
                              replies: [{ status: 201, rows: [{ data: BK() }] }] });
    ok(r.code === 200, 'a cancellation is saved -- ' + r.code);
    ok(r.calls.length === 1 && r.calls[0].method === 'POST',
       '...with ONE upstream call and no check, so it can never be refused for '
       + 'overlapping the thing it is cancelling -- '
       + r.calls.map((c) => c.method).join(','));
  }

  // ── 6. THE GATE IS NARROW ────────────────────────────────────────────────
  // The merch lock's own comment calls itself "a narrow, resource+transition-
  // specific gate". A gate that quietly widened to the other 35 resources would
  // turn ordinary saves into 409s, and every arm above would still pass.
  section('6. the other LEG resources keep blind-upsert semantics');
  for (const other of ['leg_cases', 'leg_facilities', 'leg_obituaries']) {
    const r = await call(h, { resource: other, payload: { id: 'X-1' },
                              replies: [{ status: 201, rows: [{ data: { id: 'X-1' } }] }] });
    ok(r.code === 200 && r.calls.length === 1 && r.calls[0].method === 'POST',
       other + ' is still a single blind upsert -- ' + r.code + ', '
       + r.calls.map((c) => c.method).join(','));
  }

  // ── 7. A WINDOW THAT IS NOT THERE, AND ONE THAT CANNOT BE READ ───────────
  section('7. a missing window is refused, and an unreadable one is a THIRD '
          + 'state');
  for (const [label, over] of [
    ['no facility', { facility_id: '' }],
    ['no start', { start_time: '' }],
    ['no end', { end_time: '' }],
    ['an unparseable start', { start_time: 'next Tuesday' }],
    ['end before start', { start_time: '2026-11-02T17:00:00.000Z',
                           end_time: '2026-11-02T15:00:00.000Z' }],
    ['a zero-length window', { start_time: '2026-11-02T15:00:00.000Z',
                               end_time: '2026-11-02T15:00:00.000Z' }]]) {
    const r = await call(h, { resource: 'leg_bookings', payload: BK(over) });
    ok(r.code === 400 && eCode(r) === 'BOOKING_WINDOW_REQUIRED'
       && r.calls.length === 0,
       'a booking with ' + label + ' is refused before any database call -- '
       + r.code + ', ' + r.calls.length + ' call(s)');
  }
  {
    // PR 1.11 APPLIED TO DATA RATHER THAN TO A TOOL: "could not tell" is a
    // third state and is never folded into "no conflict". An existing row whose
    // window does not parse cannot be compared, so this refuses and names it.
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              replies: [{ status: 200,
                                          rows: [row('BK-BAD', { start_time: 'whenever' })] },
                                        { status: 201, rows: [{ data: BK() }] }] });
    ok(r.code === 409 && eCode(r) === 'BOOKING_CHECK_INDETERMINATE',
       'an existing row with an unreadable window is NOT silently treated as '
       + 'non-overlapping -- ' + r.code + ' '
       + eCode(r));
    ok(/BK-BAD/.test(eMsg(r)),
       '...and the refusal names the row, so it is actionable rather than '
       + 'mysterious');
    ok(r.calls.length === 1,
       '...and nothing was written -- ' + r.calls.length + ' call(s)');
  }
  {
    // AND A REAL CLASH STILL OUTRANKS AN UNREADABLE ONE. Reporting "could not
    // tell" when the answer is actually "yes, it clashes" is a worse message
    // for the same refusal.
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              replies: [{ status: 200,
                                          rows: [row('BK-BAD', { end_time: 'soon' }),
                                                 row('BK-1')] }] });
    ok(r.code === 409 && eCode(r) === 'BOOKING_CONFLICT',
       'a real clash is reported as a clash even when another row is '
       + 'unreadable -- ' + eCode(r));
  }

  // ── 8. NOT PROVISIONED IS NOT A CONFLICT ─────────────────────────────────
  section('8. an unprovisioned table says so, rather than reading as a clash');
  {
    const r = await call(h, { resource: 'leg_bookings', payload: BK(),
                              replies: [{ status: 404, rows: [] }] });
    ok(r.code === 503 && eCode(r) === 'NOT_PROVISIONED',
       'a 404 from the check is NOT_PROVISIONED, not BOOKING_CONFLICT -- '
       + r.code + ' ' + eCode(r));
  }

  // ── 9. THE CLIENT HALF ───────────────────────────────────────────────────
  // THE SHARPER HALF, and the reason the server fix alone would make things
  // worse in one specific way: saveBooking() writes to localStorage BEFORE the
  // await, so a refused booking stays on this device's calendar showing a room
  // the server knows is not ours. A silent divergence, where before the fix
  // there was at least a visible toast.
  //
  // The two properties are the ones confirmReserve()'s rollback was fixed twice
  // to get right, and they are asserted here rather than assumed to have been
  // copied: RE-READ instead of writing back the pre-await snapshot, and only
  // touch the record if it is still OURS.
  section('9. saveBooking() rolls the optimistic local write back on 409');
  {
    function grab(sig) {
      const start = HTML.indexOf(sig);
      assert.ok(start > 0, 'not found in sairnlegacy.html: ' + sig);
      let i = HTML.indexOf('{', start + sig.length - 1), depth = 0, q = null;
      for (; i < HTML.length; i++) {
        const c = HTML[i], p = HTML[i - 1];
        if (q) { if (c === q && p !== '\\') q = null; continue; }
        if (c === '"' || c === "'" || c === '`') { q = c; continue; }
        if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
        if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
        if (c === '{') depth++;
        else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
      }
      throw new Error('unterminated: ' + sig);
    }

    // `duringAwait` runs WHILE the request is in flight, which is the only way
    // to reproduce a concurrent local change. A fixture that mutates before or
    // after cannot see the snapshot bug at all.
    function ctxFor(existing, opts) {
      opts = opts || {};
      const store = { leg_bookings: JSON.stringify(existing || []),
                      leg_facilities: JSON.stringify([{ id: 'FC-1', type: 'Chapel',
                                                        name: 'Chapel', notes: '' }]),
                      leg_license_key: 'LIC-1' };
      const ctx = {
        console: console, toasts: [], store: store, legLastErr: {},
        APP_ID: 'sairnlegacy', DATA_API: 'https://stub.invalid/api/sd-data',
        legSession: { token: 'TOK-1' }, sent: [], JSON: JSON, Date: Date,
        legLocalToday: () => '2026-10-13',
        localStorage: { getItem: (k) => (k in store ? store[k] : null),
                        setItem: (k, v) => { store[k] = String(v); } },
        rScheduling: () => { ctx.rendered = (ctx.rendered || 0) + 1; },
        closeBookingModal: () => {},
        legMarkSynced: () => {},
        legFetchTimeoutSignal: () => undefined,
        toast: function (m) { ctx.toasts.push(String(m)); },
        fetch: async (url, init) => {
          ctx.sent.push({ url: String(url), body: (init && init.body) || '' });
          if (opts.duringAwait) opts.duringAwait(ctx);
          return { ok: opts.status >= 200 && opts.status < 300,
                   status: opts.status,
                   json: async () => opts.payload };
        },
      };
      ctx._els = {};
      ctx.$ = (id) => {
        if (!ctx._els[id]) {
          const v = { bkfacility: 'FC-1', bkstart: '2026-11-02T15:00',
                      bkend: '2026-11-02T17:00', bkpurpose: 'Second service',
                      bkcase: 'CS-2' }[id];
          ctx._els[id] = { value: v === undefined ? '' : v, textContent: '' };
        }
        return ctx._els[id];
      };
      vm.createContext(ctx);
      for (const sig of ['function lgyIsQuotaError(e){', 'function st(k,v){',
                         'function ld(k,d){', 'function bookings(){',
                         'function facilities(){',
                         'function facilityLabel(id){',
                         'function fdatetime(iso){',
                         'function newId(prefix){',
                         'function legLicenseKey(){',
                         'function bookingConflict(facilityId,startIso,endIso,excludeId){',
                         'function legLastErrText(resource){',
                         'function legLastErrCode(resource){',
                         'function legWriteFailText(resource,fallback){',
                         'function sdnData(action,resource,payload,withSession){',
                         'async function saveBooking(){']) {
        vm.runInContext(grab(sig), ctx);
      }
      return ctx;
    }
    const bk = (ctx) => JSON.parse(ctx.store.leg_bookings);

    // (a) THE REFUSAL IS UNDONE LOCALLY.
    {
      const ctx = ctxFor([], { status: 409,
        payload: { error: { code: 'BOOKING_CONFLICT',
                            message: 'That facility is already booked' } } });
      await ctx.saveBooking();
      ok(bk(ctx).length === 0,
         'a booking the server refused is REMOVED from this device, so the '
         + 'calendar does not show a room the server says is not ours');
      ok(ctx.toasts.some((t) => /already booked/.test(t)),
         '...and the toast carries the SERVER\'s words, not a generic '
         + '"saved on this device only"');
      ok((ctx.rendered || 0) >= 2,
         '...and the panel is re-rendered after the rollback, or the removed '
         + 'booking stays on screen until something else redraws');
    }

    // (b) THE SNAPSHOT BUG. A cancellation lands on this device while the
    // request is in flight. Writing back the pre-await `list` would silently
    // revert it -- the exact defect fixed in confirmReserve() on 2026-09-02,
    // reproduced here against the second copy of that rollback.
    {
      const ctx = ctxFor([{ id: 'BK-OLD', facility_id: 'FC-2', case_id: 'CS-9',
                            start_time: '2026-11-05T10:00:00.000Z',
                            end_time: '2026-11-05T11:00:00.000Z',
                            purpose: 'x', status: 'Scheduled' }], {
        status: 409,
        payload: { error: { code: 'BOOKING_CONFLICT', message: 'taken' } },
        duringAwait: (c) => {
          const l = JSON.parse(c.store.leg_bookings);
          l.find((b) => b.id === 'BK-OLD').status = 'Cancelled';
          c.store.leg_bookings = JSON.stringify(l);
        } });
      await ctx.saveBooking();
      const old = bk(ctx).find((b) => b.id === 'BK-OLD');
      ok(old && old.status === 'Cancelled',
         'a cancellation made WHILE the request was in flight survives the '
         + 'rollback -- the rollback re-reads instead of writing back its '
         + 'pre-await snapshot');
      ok(!bk(ctx).some((b) => b.facility_id === 'FC-1'),
         '...and the refused booking is still the only thing removed');
    }

    // (c) A NETWORK FAILURE IS NOT A REFUSAL. The server never said no, so the
    // local record must SURVIVE -- deleting it would destroy a booking that is
    // merely unsynced, which is the opposite failure and a worse one.
    {
      const ctx = ctxFor([], { status: 500, payload: {} });
      await ctx.saveBooking();
      ok(bk(ctx).length === 1,
         'a 500 leaves the booking on this device -- an unsynced booking is '
         + 'not a refused one');
      ok(ctx.toasts.some((t) => /this device|server/i.test(t)),
         '...and the toast says it did not reach the server');
    }

    // (d) THE HAPPY PATH STILL TOASTS SUCCESS, so (a) is not satisfied by a
    // function that reports a conflict on everything.
    {
      const ctx = ctxFor([], { status: 200, payload: { ok: true, data: {} } });
      await ctx.saveBooking();
      ok(bk(ctx).length === 1 && ctx.toasts.some((t) => /Booking created/.test(t)),
         'a booking the server accepts is kept and reported as created');
    }

    // (e) AND THE LOCAL CHECK IS STILL THERE. The server gate does not make it
    // redundant: it is what gives immediate feedback in the modal, and
    // deleting it would send every same-device double-booking on a round trip.
    {
      // THE WINDOW IS DERIVED, NOT WRITTEN. saveBooking() reads the modal's
      // datetime-local value and calls new Date(...).toISOString(), which is
      // LOCAL time -- so a hand-written `...T14:00:00.000Z` fixture overlaps
      // the modal's 15:00-17:00 only in UTC and this arm would quietly pass in
      // one timezone and fail in another. Converted the same way the function
      // under test converts, so it holds anywhere.
      const localIso = (s) => new Date(s).toISOString();
      const ctx = ctxFor([{ id: 'BK-OLD', facility_id: 'FC-1', case_id: 'CS-9',
                            start_time: localIso('2026-11-02T14:00'),
                            end_time: localIso('2026-11-02T16:00'),
                            purpose: 'x', status: 'Scheduled' }],
                         { status: 200, payload: { ok: true, data: {} } });
      await ctx.saveBooking();
      ok(ctx.sent.length === 0 && bk(ctx).length === 1,
         'a clash this device CAN see is refused in the modal with no request '
         + 'and nothing added');
      ok(/already booked/.test(ctx._els['booking-err'].textContent),
         '...and the modal names the conflicting window');
    }
  }

  console.log('\n' + n + ' passed, ' + bad + ' failed');
  process.exit(bad ? 1 : 0);
})();
