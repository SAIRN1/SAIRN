// tests/sairncare_transport_refusal.js
//
// REQUIREMENT: a request SAIRNcare's second transport could not complete must
//   arrive at the renderer, and at the credential ledger, as a REFUSAL --
//   never as the compliance engine's own answer and never as an empty ledger
//
// ── THE TWO SHAPES, AND THEY ARE ONE DEFECT SEEN FROM TWO ENDS ─────────────
// `alfPostRaw()` carried `if(!r.ok && !d.error)`, so its HTTP_<status>
// normalisation fired ONLY when the server sent no error body. deea8c55 removed
// that same clause from `alfRoute()` and `alfData()` on 2026-09-21 and left it
// here deliberately, recorded in a comment above the function, because neither
// caller PERSISTS -- different blast radius, its own change. This is that
// change.
//
//   (a) THE CODE. Every api/sd-data.js refusal that DOES carry a body passed
//       through wearing the server's own code, so a transport refusal was
//       rendered where the COMPLIANCE ENGINE's refusal codes belong --
//       NO_SESSION shown in the place NO_RULE_FOR_STATE goes. And
//       `upstream()`'s 502 has `{error:{message}}` with NO CODE AT ALL, so
//       cqRenderResult() printed its `e.code||'Not available'` fallback.
//
//   (b) THE LEDGER, WHICH IS THE HALF WITH A FILE AT THE END OF IT.
//       `crRefresh()` read `(r && Array.isArray(r.data)) ? r.data : []`. An
//       error envelope has no `data` array, so a REFUSED credential read set
//       `_crRecords = []` and `rCredentials()` rendered "No credential or
//       training entries recorded yet."
//
//       AND THE GUARD THAT WOULD HAVE CAUGHT IT ALREADY EXISTED AND WAS NEVER
//       REACHED. `ALF_EXPORTS.credentials.rows()` returns null when
//       `_crRecords === null`, under a comment saying "`_crRecords === null` IS
//       REFUSED RATHER THAN EXPORTED AS EMPTY. Never loaded and genuinely empty
//       are two different facts." Correct, and dead: crRefresh never produced
//       null on a refusal. So a refused read could be exported as a CSV whose
//       own preamble says `ROWS IN THIS FILE: 0` about an append-only
//       credential ledger -- the file somebody hands to an inspector.
//
// ── IT RUNS THE SHIPPED FUNCTIONS, NOT A COPY OF THEM ──────────────────────
// Same extraction discipline as tests/sairncare_route_record.js: every
// function under test is lifted out of sairncare.html by anchor at run time,
// and a missing or ambiguous anchor THROWS rather than skipping. The whole
// chain is driven end to end -- fake fetch -> alfPostRaw -> alfCredRead ->
// crRefresh -> _crRecords -- because an arm that constructs the body it
// expects cannot see a defect about which bodies actually arrive.
//
// DELIBERATELY NOT 'use strict': the lifted functions are brought into this
// scope by a DIRECT eval, and a strict eval gets its own scope.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'sairncare.html');
const LINES = fs.readFileSync(APP, 'utf8').split('\n');

function grab(anchor) {
  const hits = [];
  for (let i = 0; i < LINES.length; i++) if (LINES[i].startsWith(anchor)) hits.push(i);
  if (hits.length !== 1) {
    throw new Error('ANCHOR-' + hits.length + ' for ' + JSON.stringify(anchor) +
      ' in sairncare.html -- this suite is not testing what it says it tests. ' +
      'Fix the anchor, do not delete the arm.');
  }
  for (let j = hits[0]; j < LINES.length; j++) {
    if (LINES[j] === '}') return LINES.slice(hits[0], j + 1).join('\n');
  }
  throw new Error('no closing brace found after ' + JSON.stringify(anchor));
}

// ── The environment the shipped functions expect, and nothing more ─────────
const DATA_API = 'https://example.invalid/api/sd-data';
const APP_ID = 'sairncare';
let alfSession = { token: 'tok' };
function alfLicenseKey() { return 'LIC-TEST'; }

let _crRecords = null, _crScopedToSelf = false;
let rendered = 0;
function rCredentials() { rendered += 1; }

let NEXT = null;                       // what the fake server answers
global.fetch = function () {
  return Promise.resolve({
    ok: NEXT.status >= 200 && NEXT.status < 300,
    status: NEXT.status,
    json: function () { return Promise.resolve(NEXT.body); }
  });
};

const SRC_POST = grab('function alfPostRaw(body){');
const SRC_READ = grab('function alfCredRead(){');
const SRC_REFRESH = grab('function crRefresh(){');
eval(SRC_POST);                                              // eslint-disable-line
eval(SRC_READ);                                              // eslint-disable-line
eval(SRC_REFRESH);                                           // eslint-disable-line

let pass = 0, fail = 0;
function t(name, fn) {
  return Promise.resolve().then(fn).then(
    function () { pass += 1; console.log('  ok   ' + name); },
    function (e) { fail += 1; console.log('  FAIL ' + name + '\n       ' + e.message); });
}
function section(s) { console.log('\n' + s); }

console.log('SAIRNcare -- a request that could not complete must arrive as a REFUSAL');

// ── The four refusal shapes api/sd-data.js actually emits ─────────────────
const REFUSALS = [
  [401, { error: { code: 'NO_SESSION', message: 'Your sign-in could not be verified.' } },
   'a session refusal'],
  [403, { error: { code: 'FORBIDDEN', message: 'A valid employee session is required.' } },
   'a role refusal'],
  [503, { error: { code: 'NOT_PROVISIONED', message: 'Run sql/sairncare_compliance_rules_schema.sql first.' } },
   'an unprovisioned table'],
  // upstream() forwards PostgREST with NO code at all. This is the shape that
  // reached cqRenderResult()'s `e.code || 'Not available'` fallback.
  [502, { error: { message: 'The data service is not answering.' } },
   'an upstream 502 carrying NO code'],
];

(async function () {
  section('1. the CODE -- every non-200 is stamped HTTP_<status>, because the engine judges on 200 and only on 200');

  for (const [status, body, label] of REFUSALS) {
    await t(label + ' (' + status + ') is stamped HTTP_' + status, async function () {
      NEXT = { status: status, body: body };
      const r = await alfPostRaw({ action: 'read', resource: 'x' });
      assert.ok(r && r.error, 'no error envelope came back: ' + JSON.stringify(r));
      assert.strictEqual(r.error.code, 'HTTP_' + status,
        'code was ' + JSON.stringify(r.error.code) +
        ' -- the server\'s own code reached a renderer that reserves that field ' +
        'for the compliance engine');
      assert.strictEqual(r.ok, false);
    });
  }

  await t('the SERVER\'S MESSAGE is kept -- it is the actionable half', async function () {
    NEXT = { status: 503, body: { error: { code: 'NOT_PROVISIONED', message: 'Run sql/sairncare_compliance_rules_schema.sql first.' } } };
    const r = await alfPostRaw({ action: 'read', resource: 'x' });
    assert.match(r.error.message, /sairncare_compliance_rules_schema\.sql/,
      'the operator lost the sentence they can act on: ' + r.error.message);
  });

  await t('a refusal with NO message still says something a person can read', async function () {
    NEXT = { status: 500, body: { error: { code: 'BOOM' } } };
    const r = await alfPostRaw({ action: 'read', resource: 'x' });
    assert.strictEqual(r.error.code, 'HTTP_500');
    assert.ok(r.error.message && r.error.message.length > 0, 'blank message');
  });

  section('2. and it does NOT refuse everything -- the arms above are satisfied by a transport that fails always');

  await t('a 200 success passes through untouched', async function () {
    NEXT = { status: 200, body: { ok: true, data: [{ id: 'C-1' }], scoped_to_self: false } };
    const r = await alfPostRaw({ action: 'read', resource: 'x' });
    assert.strictEqual(r.ok, true);
    assert.strictEqual(r.data.length, 1);
    assert.ok(!r.error);
  });

  await t('a 200 carrying the ENGINE\'S OWN refusal keeps the engine\'s code', async function () {
    // The whole reason the stamp is keyed on the status and not on the body:
    // every routing and compliance answer, refusal included, is status 200.
    // Anything else is somebody other than the engine saying no.
    NEXT = { status: 200, body: { ok: false, error: { code: 'NO_RULE_FOR_STATE', message: 'Ohio is not covered.' } } };
    const r = await alfPostRaw({ action: 'evaluate', resource: 'x' });
    assert.strictEqual(r.error.code, 'NO_RULE_FOR_STATE',
      'an engine refusal was overwritten with a transport code');
  });

  await t('an unreadable body is BAD_RESPONSE, not a silent null', async function () {
    NEXT = { status: 200, body: null };
    global.fetch = function () {
      return Promise.resolve({ ok: true, status: 200,
        json: function () { return Promise.reject(new Error('not json')); } });
    };
    const r = await alfPostRaw({ action: 'read', resource: 'x' });
    assert.strictEqual(r.error.code, 'BAD_RESPONSE');
    global.fetch = function () {
      return Promise.resolve({ ok: NEXT.status >= 200 && NEXT.status < 300, status: NEXT.status,
        json: function () { return Promise.resolve(NEXT.body); } });
    };
  });

  section('3. the LEDGER -- a refused read is NOT an empty ledger, and the export already knew that');

  for (const [status, body, label] of REFUSALS) {
    await t(label + ' leaves _crRecords NULL, not []', async function () {
      _crRecords = 'unset'; rendered = 0;
      NEXT = { status: status, body: body };
      await crRefresh();
      assert.strictEqual(_crRecords, null,
        '_crRecords is ' + JSON.stringify(_crRecords) +
        ' -- rCredentials() renders that as "No credential or training entries ' +
        'recorded yet", and ALF_EXPORTS.credentials.rows() exports it as a file ' +
        'whose preamble says ROWS IN THIS FILE: 0');
      assert.strictEqual(rendered, 1, 'the panel was not re-rendered');
    });
  }

  await t('a GENUINELY EMPTY ledger is [] -- so null means refused, not "no rows"', async function () {
    _crRecords = 'unset';
    NEXT = { status: 200, body: { ok: true, data: [], scoped_to_self: false } };
    await crRefresh();
    assert.ok(Array.isArray(_crRecords) && _crRecords.length === 0,
      'an empty ledger came back as ' + JSON.stringify(_crRecords) +
      ' -- if empty and refused are the same value the distinction above is decorative');
  });

  await t('rows still load on success, and the scope flag with them', async function () {
    _crRecords = null; _crScopedToSelf = false;
    NEXT = { status: 200, body: { ok: true, data: [{ id: 'C-1' }, { id: 'C-2' }], scoped_to_self: true } };
    const out = await crRefresh();
    assert.strictEqual(out.length, 2);
    assert.strictEqual(_crScopedToSelf, true);
  });

  await t('a null response -- no licence key -- is refused, not read as empty', async function () {
    // alfPostRaw returns a bare null when there is no licence at all.
    _crRecords = 'unset';
    const saved = alfLicenseKey;
    alfLicenseKey = function () { return ''; };                // eslint-disable-line
    try {
      await crRefresh();
      assert.strictEqual(_crRecords, null);
    } finally { alfLicenseKey = saved; }                       // eslint-disable-line
  });

  section('4. the export guard this depends on is still there -- it is the half that produces a FILE');

  await t('ALF_EXPORTS.credentials.rows() still refuses on _crRecords === null', function () {
    // Asserted against the source rather than driven: extracting ALF_EXPORTS
    // would pull in the whole CSV layer. What matters is that the guard the
    // arms above feed has not been removed -- it was correct and unreachable
    // for as long as crRefresh could not produce null, and removing it now
    // would re-open the defect from the other side.
    const src = LINES.join('\n');
    const hits = src.split('if(_crRecords===null)return null;').length - 1;
    assert.strictEqual(hits, 1,
      'the export\'s null guard is gone or duplicated (' + hits + ' occurrences)');
  });

  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairncare transport refusal: ' +
    pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
