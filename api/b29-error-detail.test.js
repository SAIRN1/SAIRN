// api/b29-error-detail.test.js
//
// Run:  node api/b29-error-detail.test.js
//
// ── THE DEFECT ──────────────────────────────────────────────────────────────
// A raw upstream error body is handed straight back to the HTTP client as
// `error.detail`. Three shapes, eleven sites, measured:
//
//   SHAPE 1  the raw PostgREST **text** -- `detail: bt` after `await r.text()`
//            api/sd-data.js x7  (rf_proposals, rf_invoices, grd programmes,
//            sd_locations, schedule entries, rules, agreements)
//   SHAPE 2  the raw **Stedi JSON** -- `detail: data || null`
//            api/sc-eligibility.js x2  (search_payer, and the 270/271 CHECK)
//   SHAPE 3  the raw PostgREST **rows**, carried on an Error and re-echoed --
//            `detail: err.detail`   api/audit-checkpoint.js x2
//
// ── WHY THIS IS NOT A TIDINESS FIX ──────────────────────────────────────────
// A PostgREST error body names the TABLE, the CONSTRAINT, the COLUMN and often
// the offending VALUE. That is an internal schema map handed to anyone holding
// a licence key, and the value half can be customer data. `api/sd-data.js`'s
// own `upstream()` helper got this right years ago -- it logs the body and
// answers "Data store error — try again" -- and these eleven sites bypass it.
//
// SHAPE 2 IS THE SHARPEST AND IT IS NOT PostgREST. `api/sc-eligibility.js:309`
// is the 270/271 eligibility check, whose REQUEST carries subscriber first
// name, last name, member id and date of birth. A payer's error body routinely
// echoes the subscriber block it could not match -- so that `detail` can hand
// PHI back in an error envelope, and the code comment above the sibling site
// defends the behaviour on the grounds that a generic message would hide an
// auth or quota error. BOTH can be true: log the body, answer generically,
// and the HTTP status plus the code already separate auth from quota.
//
// ── THE BRIEF SAID 9 SITES AND IT IS 11 ────────────────────────────────────
// Reported rather than quoted. A grep for `detail: <body-variable>` finds
// nine; the two in `api/audit-checkpoint.js` assign the body to an Error
// property first (`e.detail = rows`, api/_lib/countersign-endpoint.js:181) and
// echo it a function later, so they are invisible to that pattern. The two
// extra are the same defect by a less visible route, which is the direction
// worth over- rather than under-counting.
//
// ── WHAT EACH ARM ASSERTS, AND WHY IT IS THE WHOLE RESPONSE ────────────────
// Not "there is no `detail` key". A marker string is planted in the upstream
// error body and the arm asserts THE MARKER APPEARS NOWHERE IN THE SERIALISED
// RESPONSE -- so moving the leak to a different key, or into the message, does
// not make the arm green. And the second half: the marker MUST appear in
// `console.error`, because a fix that merely deletes the body makes the next
// 400 undiagnosable and that is a different defect, not a fix.
//
// Exit: 0 all arms passed · 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b29', 'error', 'detail', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
process.env.CRON_SECRET = process.env.CRON_SECRET || 'b29-cron-fixture';

const path = require('path');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'b29-detail-hash';
const KEY = 'KEY-FOR-' + HASH;

// THE MARKER IS SHAPED LIKE THE THING THAT ACTUALLY LEAKS. A PostgREST error
// body carries a constraint name, a column and a value; a payer error carries
// the subscriber block. Each marker is a single improbable token so a substring
// search over the whole response cannot miss it and cannot false-positive.
const PG_MARKER = 'ZZB29LEAKCONSTRAINT';
const STEDI_MARKER = 'ZZB29LEAKSUBSCRIBER';
const ROWS_MARKER = 'ZZB29LEAKAUDITTABLE';

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 700));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  res.end = function () { return res; };
  res.setHeader = function () { return res; };
  return res;
}

// Captures console.error for the duration of one call, so "the body is still
// logged" is asserted rather than hoped for.
async function withCapturedErr(fn) {
  const lines = [];
  const real = console.error;
  console.error = function () {
    lines.push(Array.prototype.map.call(arguments, function (a) {
      if (typeof a === 'string') return a;
      try { return JSON.stringify(a); } catch (e) { return String(a); }
    }).join(' '));
  };
  try {
    const out = await fn();
    return { out: out, log: lines.join('\n') };
  } finally {
    console.error = real;
  }
}

function serialised(res) {
  try { return JSON.stringify(res.body); } catch (e) { return String(res.body); }
}

// ══ SHAPE 1 ═══════════════════════════════════════════════════════════════
// api/sd-data.js, seven sites. Driven through rf_proposals, whose branch is
// the first of the seven and whose fall-through is reached by a 400 that
// matches NEITHER of its two classified cases.
function sdPgMock(status, bodyText) {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: m ? decodeURIComponent(m[1]) : 'emp-1',
          role: 'owner', active: true }] };
    }
    if (method === 'POST' && /rf_proposals/.test(u)) {
      return {
        ok: false, status: status,
        text: async () => bodyText,
        json: async () => { try { return JSON.parse(bodyText); } catch (e) { return null; } }
      };
    }
    if (method === 'POST' || method === 'PATCH') {
      return { ok: true, status: 200, json: async () => [{ id: 'x' }] };
    }
    return { ok: true, status: 200, json: async () => [
      { id: 'row-1', claim_id: 'CLM-1', proposal_id: 'PR-1', data: {} }] };
  };
}

function loadSdData(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnroofing' })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// ══ SHAPE 2 ═══════════════════════════════════════════════════════════════
// api/sc-eligibility.js. Two outbound calls matter: the credential read
// (Supabase) must succeed, and the Stedi call must fail with a body.
function scMock(stediStatus, stediBody) {
  return async function (url) {
    const u = String(url);
    if (/supabase/.test(u)) {
      return { ok: true, status: 200,
               json: async () => [{ data: { stedi: { enc: 'v2.FIXTURE' } } }] };
    }
    return { ok: false, status: stediStatus, json: async () => stediBody };
  };
}

function loadScEligibility(fetchImpl) {
  const authPath = require.resolve('./_lib/auth');
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairncode' })
    }
  };
  // decryptSecret is stubbed and NOTHING ELSE IS. A real ciphertext would make
  // this arm depend on which encryption key the environment happens to carry,
  // which is a precondition it is not about; the session verification stays
  // REAL so the arm cannot pass against a broken auth gate.
  delete require.cache[authPath];
  require.cache[authPath] = {
    exports: Object.assign({}, realAuth, {
      decryptSecret: () => 'stedi-key-fixture'
    })
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sc-eligibility.js')];
  const h = require('./sc-eligibility.js');
  delete require.cache[authPath];          // put the real module back
  return h;
}

// ══ SHAPE 3 ═══════════════════════════════════════════════════════════════
// api/audit-checkpoint.js. The CHECK_NOT_WIDENED path: the checkpoint insert
// is refused by the table's own audit_table CHECK, and the raw rows ride out
// on an Error property.
// THE THREE READS HAVE TO ANSWER DIFFERENTLY OR THE INSERT IS NEVER REACHED,
// and the first spelling of this mock answered them all the same way. It
// returned an audit-log row for the CHECKPOINT read too, so `last.window_end`
// was undefined, `Date.parse(undefined)` was NaN, the cursor never advanced and
// the job reported "0 written" for all sixteen tables -- S3a passed while
// nothing was driven. Measured, then fixed:
//   the CHECKPOINT table read  -> [] (no prior checkpoint, so the cursor comes
//                                 from the earliest audit row)
//   the EARLIEST-ROW read      -> a created_at well in the past, so there is at
//                                 least one CLOSED window to checkpoint
//   the window read            -> one row, so the digest covers something
//   the CHECKPOINT insert      -> refused 400 with a CHECK violation
// AND A `headers` WITH A `get`, because the heartbeat reads one off the
// response. Without it the handler threw "Cannot read properties of undefined
// (reading 'get')", landed in the generic catch, and S3a passed on a 500 that
// had nothing to do with the leak -- a harness fault reported as a pass, which
// is the failure this file's own catch block refuses to call one.
// AND AN EXACT `content-range`, because readWindow REFUSES a read it cannot
// confirm complete and throws `incomplete` -- correctly, and it lands in the
// WINDOW_INCOMPLETE branch instead of the one under test. That branch echoes an
// err.detail too, and its err.detail is a COMPOSED object ({table, read, why}),
// not a raw body, so it is NOT one of the eleven sites. Worth writing down: two
// `detail: err.detail` lines, one a leak and one not, is exactly why this file
// drives the sites instead of counting them.
const NO_HEADERS = { get: function (k) {
  return String(k).toLowerCase() === 'content-range' ? '0-0/1' : null;
} };
function acMock(bodyObj) {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/audit_checkpoint/.test(u)) {
      if (method === 'POST') {
        return { ok: false, status: 400, headers: NO_HEADERS,
                 json: async () => bodyObj,
                 text: async () => JSON.stringify(bodyObj) };
      }
      return { ok: true, status: 200, headers: NO_HEADERS,
               json: async () => [], text: async () => '[]' };
    }
    return { ok: true, status: 200, headers: NO_HEADERS,
             json: async () => [{ id: 1, created_at: '2020-01-02T00:00:00Z',
                                  event_type: 'login_success' }],
             text: async () => '[]' };
  };
}

function loadAuditCheckpoint(fetchImpl) {
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./audit-checkpoint.js')];
  return require('./audit-checkpoint.js');
}

(async function main() {
  // ═══════════════════════════════════════════════════════════════════════
  section('S1. api/sd-data.js -- the raw PostgREST TEXT as error.detail (7 sites)');
  // ═══════════════════════════════════════════════════════════════════════

  // A real-shaped PostgREST 400: a CHECK violation naming the constraint, the
  // column and the offending value. Neither of the branch's two classified
  // cases matches it, so it reaches the fall-through.
  const PG_BODY = JSON.stringify({
    code: '23514',
    details: null,
    hint: null,
    message: 'new row for relation "rf_proposals" violates check constraint "'
           + PG_MARKER + '"'
  });

  {
    const { out, log } = await withCapturedErr(async function () {
      const h = loadSdData(sdPgMock(400, PG_BODY));
      const res = mockRes();
      await h({
        method: 'POST',
        headers: {
          authorization: 'Bearer ' + KEY,
          'x-sd-auth': signSessionToken({
            app: 'sairnroofing', employee_id: 'emp-1', role: 'owner',
            license_hash: HASH })
        },
        // THE FULL PAYLOAD THE BRANCH'S OWN VALIDATOR ACCEPTS. A thin one
        // ({id} alone) is refused 400 by validateProposal before any insert,
        // and the arm would then be measuring a field validator while claiming
        // to measure an error-body leak -- "some refusal happened" is not
        // "this leak is closed". Measured: the first spelling got
        // "job_id is required; event_type must be one of: ..." and S1a passed
        // vacuously.
        body: {
          action: 'write', resource: 'rf_proposals',
          payload: { id: 'PR-1', job_id: 'JOB-1', event_type: 'issued',
                     issued_on: '2026-10-19',
                     line_items: [{ description: 'tear-off', amount: 1000 }] }
        }
      }, res);
      return res;
    });
    const resp = serialised(out);
    is(out.statusCode !== null && resp.indexOf(PG_MARKER) === -1,
       'S1a. THE REPRODUCTION: the constraint name does not appear ANYWHERE in '
       + 'the response body',
       'status ' + out.statusCode + ' body ' + resp.slice(0, 300));
    is(log.indexOf(PG_MARKER) !== -1,
       'S1b. ...and it IS logged server-side, so the 400 stays diagnosable',
       'console.error captured: ' + (log.slice(0, 300) || '(nothing)'));
    is(!/detail/.test(resp),
       'S1c. ...and no `detail` key survives in the response at all',
       resp.slice(0, 300));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('S2. api/sc-eligibility.js -- the raw Stedi JSON as error.detail (2 sites)');
  // ═══════════════════════════════════════════════════════════════════════

  // Shaped like a real payer rejection, which echoes the subscriber block it
  // could not match. THAT IS PHI IN AN ERROR ENVELOPE.
  const STEDI_BODY = {
    error: 'subscriber not found',
    subscriber: { firstName: STEDI_MARKER, lastName: 'Testpatient',
                  memberId: 'MBR-0001', dateOfBirth: '1954-02-11' }
  };

  for (const [name, body] of [
    ['search_payer', { action: 'search_payer', query: 'aetna' }],
    ['check (the 270/271, which carries the subscriber block)',
     { action: 'check', payerId: 'P1',
       provider: { organizationName: 'X', npi: '1234567893' },
       subscriber: { firstName: 'A', lastName: 'B', memberId: 'M1',
                     dateOfBirth: '1954-02-11' },
       encounter: { serviceTypeCodes: ['30'] } }]
  ]) {
    const { out, log } = await withCapturedErr(async function () {
      const h = loadScEligibility(scMock(403, STEDI_BODY));
      const res = mockRes();
      await h({
        method: 'POST',
        headers: {
          authorization: 'Bearer ' + KEY,
          'x-sd-auth': signSessionToken({
            app: 'sairncode', employee_id: 'emp-1', role: 'admin',
            license_hash: HASH })
        },
        body: body
      }, res);
      return res;
    });
    const resp = serialised(out);
    is(out.statusCode !== null && resp.indexOf(STEDI_MARKER) === -1,
       'S2a[' + name + ']. the subscriber name does not appear anywhere in the '
       + 'response',
       'status ' + out.statusCode + ' body ' + resp.slice(0, 300));
    is(log.indexOf(STEDI_MARKER) !== -1,
       'S2b[' + name + ']. ...and the payer body IS logged server-side',
       'console.error captured: ' + (log.slice(0, 300) || '(nothing)'));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('S3. api/audit-checkpoint.js -- the raw rows via err.detail (2 sites)');
  // ═══════════════════════════════════════════════════════════════════════

  const AC_BODY = {
    code: '23514',
    message: 'new row for relation "audit_checkpoints" violates check '
           + 'constraint "' + ROWS_MARKER + '"'
  };

  {
    const { out, log } = await withCapturedErr(async function () {
      const h = loadAuditCheckpoint(acMock(AC_BODY));
      const res = mockRes();
      await h({
        method: 'POST',
        headers: { authorization: 'Bearer ' + process.env.CRON_SECRET },
        body: { action: 'checkpoint' }
      }, res);
      return res;
    });
    const resp = serialised(out);
    is(out.statusCode !== null && resp.indexOf(ROWS_MARKER) === -1,
       'S3a. the constraint name does not appear anywhere in the response',
       'status ' + out.statusCode + ' body ' + resp.slice(0, 400));
    is(log.indexOf(ROWS_MARKER) !== -1,
       'S3b. ...and the rows ARE logged server-side',
       'console.error captured: ' + (log.slice(0, 300) || '(nothing)'));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('C. THE SOURCE SWEEP -- no site of any of the three shapes is left');
  // ═══════════════════════════════════════════════════════════════════════

  // THE ARMS ABOVE DRIVE ONE SITE PER SHAPE, which proves the shape is fixed
  // where it was driven and says nothing about the other eight. A static sweep
  // is a different METHOD, not a second reading, and it is the only thing that
  // can see a site no arm reaches -- the independence requirement in
  // docs/2026-09-13-cross-domain-disciplines.md.
  //
  // It scans COMMENT-STRIPPED source, because this very file's header names
  // the patterns and the fixed sites carry comments quoting what they used to
  // do -- a scan over raw text would re-flag its own documentation, which is a
  // defect this clone's auto-memory already records paying for.
  // `stripJs` AND NOT the library's `stripComments`: these are slices of API
  // JavaScript, and `stripComments` is the HTML-aware entry point, which would
  // be the wrong one. api/auth-setup-attribution.test.js records the same
  // choice at the same library for the same reason.
  // `stripJs` AND NOT the library's `stripComments`: these are slices of API
  // JavaScript, and `stripComments` is the HTML-aware entry point, which would
  // be the wrong one. api/auth-setup-attribution.test.js records the same
  // choice at the same library for the same reason.
  const fs = require('fs');
  const { stripJs } = require('../tests/lib/strip_comments.js');
  const FILES = ['sd-data.js', 'sc-eligibility.js', 'audit-checkpoint.js'];

  // -- THE DEFECT IS `detail` IN A CLIENT RESPONSE, NOT `detail` ANYWHERE ---
  // The first spelling of this sweep matched `detail: <identifier>` on any
  // line and flagged sd-data.js:14170 --
  //
  //     event_type: event_type, detail: detail, table: alfAuditTable
  //
  // -- an argument to an INTERNAL audit-log writer, a `detail` whose whole job
  // is to carry the particulars into a table. A sweep that cannot tell a
  // response from a function call would have had me "fix" a correct line. The
  // first spelling is recorded here rather than quietly replaced, because
  // narrowing a check after it fires looks identical to moving the goalposts
  // and the difference is whether the reason is written down.
  //
  // The span is anchored on `res.status(` and runs twelve lines, which covers
  // the longest real response literal in these three files. That is a BOUND
  // and a bound can be wrong, so C2 runs the SAME function over a fixture
  // carrying one real leak and three things that look like one.
  // -- AND ONE DECLARED EXCEPTION, WHICH IS WHY THIS IS AN ALLOWLIST -------
  // A static sweep cannot tell a RAW UPSTREAM BODY from an object this
  // codebase COMPOSED -- both are `detail: <identifier>` in a response. b29
  // learned that by removing both in api/audit-checkpoint.js and watching
  // api/audit-checkpoint.test.js go red on an arm that reads `detail.why`:
  // WINDOW_INCOMPLETE's detail is `{ table, read, why }`, built by readWindow,
  // and discloses nothing.
  //
  // SO THE EXCEPTION IS DECLARED HERE, WITH ITS REASON, AND THE SWEEP FAILS
  // CLOSED ON EVERY OTHER NAME. An allowlist of one is a statement a reader
  // can check; narrowing the PATTERN until the hit disappeared would have been
  // the same change with nothing to read. Adding an entry here costs somebody
  // a sentence, which is the point.
  const DECLARED_SAFE = [{
    expr: 'err.detail',
    file: 'audit-checkpoint.js',
    why: 'WINDOW_INCOMPLETE only: readWindow composes { table, read, why }. '
       + 'The CHECK_NOT_WIDENED sibling carried a raw PostgREST body and is '
       + 'FIXED.'
  }];

  function responseDetailHits(src, label) {
    const srcLines = src.split('\n');
    const out = [];
    for (let i = 0; i < srcLines.length; i++) {
      if (!/res\.status\(/.test(srcLines[i])) continue;
      // THE SPAN ENDS AT THE STATEMENT, NOT AFTER N LINES. A fixed twelve-line
      // window was the second spelling and C2 caught it: from a ONE-LINE
      // response the window ran on into the next statement and flagged the
      // internal `auditAlf({ ... detail: detail ... })` two lines later. So
      // the span stops at the first line that closes the call, with 14 as a
      // backstop against an unterminated one. C2 going red on a FIXTURE is
      // exactly what that arm is for -- it found this before C1's zero could
      // be believed.
      const span = [];
      for (let j = i; j < srcLines.length && j < i + 14; j++) {
        span.push(srcLines[j]);
        if (/\);\s*$/.test(srcLines[j])) break;
      }
      const m = span.join('\n').match(/\bdetail: *[A-Za-z_$][A-Za-z0-9_$.]*/);
      if (m && !/detail: *(null|true|false|undefined)/.test(m[0])
          && !DECLARED_SAFE.some(function (d) {
               return m[0].replace(/\s+/g, ' ') === 'detail: ' + d.expr;
             })) {
        out.push(label + ':' + (i + 1) + '  ' + m[0]
                 + '   response opened at: ' + srcLines[i].trim().slice(0, 70));
      }
    }
    return out;
  }

  {
    const hits = [];
    for (const f of FILES) {
      hits.push.apply(hits, responseDetailHits(
        stripJs(fs.readFileSync(path.join(__dirname, f), 'utf8')), f));
    }
    is(hits.length === 0,
       'C1. ZERO `detail: <identifier>` sites remain in a CLIENT RESPONSE '
       + 'across the three files',
       hits.join('\n        '));
  }

  // C2 RUNS BOTH DIRECTIONS THROUGH THE SAME FUNCTION C1 USES. A scan that
  // matches nothing because its pattern is broken reports the same zero as a
  // scan over clean code -- item 8 of the cross-domain disciplines. One leak
  // must be FOUND; a null, a literal and an internal audit call must not be.
  //
  // AND IT EARNED ITS KEEP IMMEDIATELY, on the exact defect this platform has
  // already written down once: "a regex that shipped with A LITERAL BACKSPACE
  // and could never match". The exclusion was authored as
  // `/detail: *(null|true|false|undefined)backslash-b/` through a script, and `backslash-b`
  // reached the file as byte 0x08 rather than a word boundary -- so the null
  // exclusion silently never fired. C1 was GREEN at the time, because the real
  // source happens to contain no `detail: null` in a response. A pattern that
  // cannot exclude is indistinguishable from clean code, and only running it
  // over something that SHOULD match could tell. The `backslash-b` is simply gone now;
  // it was never needed, and a boundary that can arrive as a control character
  // is not worth re-adding.
  {
    const fixture = [
      "res.status(400).json({ error: { message: 'x', detail: bt } });",
      '',
      "res.status(400).json({ error: { message: 'x', detail: null } });",
      '',
      "res.status(400).json({ error: { message: 'x', detail: 'a literal' } });",
      '',
      'auditAlf({ event_type: event_type, detail: detail, table: t });'
    ].join('\n');
    const hits = responseDetailHits(fixture, 'fixture');
    is(hits.length === 1 && /detail: bt/.test(hits[0]),
       'C2. the C1 FUNCTION finds exactly the one real leak in a fixture that '
       + 'also carries a null, a literal and an internal audit call -- so '
       + "C1's zero means clean, not blind",
       'found ' + hits.length + ': ' + JSON.stringify(hits));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed'
    + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
