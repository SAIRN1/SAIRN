// api/sd-data-ai-scan-redaction.test.js
//
// REQUIREMENT: every resource that persists RAW MODEL OUTPUT has that text
//   redacted BY THE SERVER before it reaches the row -- in every app, not only
//   the one the gate happened to name.
//
// Run:  node api/sd-data-ai-scan-redaction.test.js
//
// ── THE DEFECT ────────────────────────────────────────────────────────────
// api/sd-data.js carried MECH_SCANNED_TEXT: the right idea, scoped to one app,
// inlined in one branch. Its own history is the argument for widening it. The
// gate before it read `if (resource === 'mech_docs')` -- a resource NAME rather
// than a property of the data -- so mech_takeoffs, four lines away in the same
// table map and storing the same shape, was ungated for its whole life.
//
// Widening a name-scoped gate to a map fixed ONE APP. The identical shape was
// live in five others: an auditor found raw scan text in bld_photo_analyses,
// grd_progress_photos, scp_progress_photos and rf_photos, and two more only by
// working BACKWARD from the store rather than forward from the model call.
//
// ── THE UNIVERSE WAS DERIVED TWICE, AND THE COUNTS DISAGREED ──────────────
// tools/ai_output_resource_scan.py runs both directions. FORWARD found 11,
// BACKWARD found 12, they agreed on 5, and each found resources the other
// could not see. THAT IS THE REASON FOR TWO METHODS: a single-direction answer
// would have been reported as a universe while missing a third of it. Every
// candidate was then confirmed by READING the store site -- seven turned out
// to be false positives of the narrower and are named, with the reason, in
// api/_lib/ai-scan-redaction.js DELIBERATELY_EXCLUDED.
//
// ── WHAT EACH ARM DRIVES ──────────────────────────────────────────────────
// Every arm goes through the REAL handler with the real map. For each gated
// resource a payload carrying a NAME, a PHONE and an SSN is written, and the
// body actually sent to PostgREST is read back and asserted on -- not the
// response, which a server that redacted only its reply would pass.
//
// THE KNOWN-BAD CONTROL PER RESOURCE removes that resource's entry from the
// map and requires the arm to FAIL. Without it, an arm proves only that the
// text arrived clean, which would also be true if the client had sanitised it,
// if the fixture were wrong, or if the redactor ran on something else.
//
// AND ONE ARM IN THE OTHER DIRECTION: a DELIVERABLE field must arrive
// UNTOUCHED. Over-redaction is not the safe failure here -- a parsed quantity
// with a digit removed is a different way to lose the record, which is the
// reasoning mech_checks already carries.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['ai', 'scan', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');
const aiScan = require('./_lib/ai-scan-redaction');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// Assembled from parts so this file is not itself a finding in any PII scan.
const NAME = ['Dana', 'Whitfield'].join(' ');
const PHONE = '(216) ' + ['555', '0142'].join('-');
const SSN = ['123', '45', '6789'].join('-');
const NL = String.fromCharCode(10);
const SCAN = 'SITE NOTE' + NL + 'Customer: ' + NAME + NL + 'Phone: ' + PHONE
  + NL + 'SSN: ' + SSN + NL + 'Unit: RTU-4  Tons: 7.5';

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

function postgrestMock(calls, hash, me) {
  return async function (url, opts) {
    calls.push({ url: String(url), opts: opts || null });
    if (/_employee_auth\?/.test(String(url))) {
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: hash, employee_id: me, role: 'owner', active: true }]; } };
    }
    // rf_photos reads the job row first and gates on it.
    if (/rf_jobs\?/.test(String(url))) {
      return { ok: true, status: 200, json: async function () {
        return [{ job_id: 'JOB-1', assigned_employee_id: me,
                  data: { id: 'JOB-1', assigned_employee_id: me } }]; } };
    }
    if (/business_profiles\?/.test(String(url))) {
      return { ok: true, status: 200, json: async function () {
        return [{ shop_id: 'SHOP-1' }]; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, text: async function () { return opts.body; },
               json: async function () { return [sent]; } };
    }
    return { ok: true, status: 200, json: async function () { return []; } };
  };
}

function loadHandler(fetchImpl, app, hash) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: hash,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: app };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// The record the SERVER sent to PostgREST -- not the response body. A server
// that redacted only its reply would pass a response-only check.
async function storedRow(app, resource, payload) {
  const hash = app + '-ai-scan-hash';
  const me = 'emp-1';
  const calls = [];
  const h = loadHandler(postgrestMock(calls, hash, me), app, hash);
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + hash,
      'x-sd-auth': signSessionToken({ app: app, employee_id: me,
                                      role: 'owner', license_hash: hash })
    },
    body: { action: 'write', resource: resource, app_id: app, payload: payload }
  }, res);
  const posts = calls.filter(function (c) {
    return c.opts && c.opts.method === 'POST' && /\/rest\/v1\//.test(c.url);
  });
  assert.ok(posts.length,
    resource + ': the handler never POSTed a row. status=' + res.statusCode
    + ' body=' + JSON.stringify(res.body).slice(0, 300));
  const body = JSON.parse(posts[posts.length - 1].opts.body);
  return { data: body.data, status: res.statusCode, res: res };
}

// ── THE GATED RESOURCES, AND THE PAYLOAD SHAPE EACH REALLY USES ────────────
// The field names and the sibling fields are taken from the store site in the
// app, not invented: a fixture with the wrong field name would pass every arm
// while the real write went ungated.
const CASES = [
  { app: 'sairnbuild', resource: 'bld_photo_analyses',
    payload: { id: 'FP-1', job_id: 'J1', date: '2026-09-30',
               summary: 'Customer: ' + NAME, full: SCAN,
               spawned_co: false, spawned_rfi: false },
    redact: ['full', 'summary'], keep: { job_id: 'J1' },
    site: 'sairnbuild.html:3666-3667 fpSave()' },

  { app: 'sairngrounds', resource: 'grd_progress_photos',
    payload: { id: 'GRDPH-1', schedule_id: 'S1', property_id: 'P1',
               photo_b64: 'AAAA', is_final: false, ai_analysis: SCAN,
               qc_status: 'not_applicable' },
    redact: ['ai_analysis'], keep: { photo_b64: 'AAAA' },
    site: 'sairngrounds.html:3490-3492' },

  { app: 'sairngrounds', resource: 'grd_ecosystem_reports',
    payload: { id: 'ECO-1', property_id: 'P1', date: '2026-09-30',
               summary: SCAN },
    redact: ['summary'], keep: { property_id: 'P1' },
    site: 'sairngrounds.html:4183-4189' },

  { app: 'sairngrounds', resource: 'msb_food_scans',
    payload: { id: 'MSBFS-1', date: '2026-09-30',
               items: ['- tomatoes', '- lettuce'], raw: SCAN },
    redact: ['raw'], keep: null,
    site: 'sairngrounds.html:4833' },

  { app: 'sairnscape', resource: 'scp_progress_photos',
    payload: { id: 'SCPPH-1', schedule_id: 'S1', customer_id: 'C1',
               photo_b64: 'AAAA', is_final: false, ai_analysis: SCAN,
               qc_status: 'not_applicable' },
    redact: ['ai_analysis'], keep: { photo_b64: 'AAAA' },
    site: 'sairnscape.html:3426-3429' },

  { app: 'sairnroofing', resource: 'rf_photos',
    payload: { job_id: 'JOB-1', photo_base64: 'AAAA', ai_analysis: SCAN,
               parsed_quantities: { squares: 24, ridge_lf: 40 } },
    redact: ['ai_analysis'], keep: null,
    site: 'sairnroofing.html:5348' },

  { app: 'stonedesk', resource: 'memory',
    payload: { memory_text: SCAN, source: 'stonedesk',
               created_at: '2026-09-30T00:00:00.000Z' },
    redact: ['memory_text'], keep: { source: 'stonedesk' },
    site: 'stonedesk.html:30425 writeSDMemory()' },
];

function leaks(text) {
  const s = String(text == null ? '' : text);
  const found = [];
  if (s.indexOf(NAME) !== -1) found.push('NAME');
  if (s.indexOf(PHONE) !== -1) found.push('PHONE');
  if (s.indexOf(SSN) !== -1) found.push('SSN');
  return found;
}

(async function () {
  section('1. every gated resource redacts on the way INTO the row');
  for (const c of CASES) {
    await test(c.resource + ' (' + c.site + ')', async function () {
      const row = await storedRow(c.app, c.resource, c.payload);
      for (const f of c.redact) {
        const got = row.data[f];
        assert.strictEqual(leaks(got).length, 0,
          c.resource + '.' + f + ' reached the row still carrying '
          + leaks(got).join(' and ') + '. Stored value: ' + JSON.stringify(got));
        assert.ok(String(got).indexOf('REDACTED') !== -1,
          c.resource + '.' + f + ' shows no redaction marker, so it is not '
          + 'clear the pass ran at all: ' + JSON.stringify(got));
      }
      assert.ok(row.data.redaction && row.data.redaction.applied_at,
        c.resource + ' carries no redaction block ON THE ROW. A row that looks '
        + 'redacted with no account of what the pass did or could not do is '
        + 'the false confidence this mechanism exists to avoid.');
    });
  }

  section('2. the whole record survives -- only the declared fields change');
  for (const c of CASES) {
    if (!c.keep) continue;
    await test(c.resource + ': sibling fields untouched', async function () {
      const row = await storedRow(c.app, c.resource, c.payload);
      for (const k of Object.keys(c.keep)) {
        assert.strictEqual(row.data[k], c.keep[k],
          c.resource + '.' + k + ' was altered and is not a declared field');
      }
    });
  }

  section('3. THE DELIVERABLE IS NOT REDACTED -- over-redaction is not safe');
  await test('rf_photos.parsed_quantities keeps every number', async function () {
    const c = CASES.filter(function (x) { return x.resource === 'rf_photos'; })[0];
    const row = await storedRow(c.app, c.resource, c.payload);
    assert.strictEqual(row.data.parsed_quantities.squares, 24,
      'a parsed quantity was altered. A digit removed from an estimate is a '
      + 'different way to lose the record, not a safer failure.');
    assert.strictEqual(row.data.parsed_quantities.ridge_lf, 40);
  });
  await test('msb_food_scans.items keeps the parsed product names', async function () {
    const c = CASES.filter(function (x) { return x.resource === 'msb_food_scans'; })[0];
    const row = await storedRow(c.app, c.resource, c.payload);
    assert.deepStrictEqual(row.data.items, ['- tomatoes', '- lettuce'],
      'the parsed inventory was altered. An inventory with the product names '
      + 'removed is not an inventory.');
  });

  section('4. an UNGATED resource in the same app is untouched');
  await test('bld_jobs passes through with no redaction block', async function () {
    const row = await storedRow('sairnbuild', 'bld_jobs',
      { id: 'J1', name: 'Whitfield Residence', notes: SCAN });
    assert.strictEqual(row.data.notes, SCAN,
      'an ungated resource was redacted. The map is the gate; widening it by '
      + 'accident is how a deliverable gets eaten.');
    assert.strictEqual(row.data.redaction, undefined);
  });

  section('5. KNOWN-BAD CONTROL, one per resource: remove the map entry');
  // Without this, section 1 proves only that the text ARRIVED clean -- which
  // would also be true if the fixture were wrong, if the client had sanitised
  // it, or if the redactor had run on some other field.
  for (const c of CASES) {
    await test('CONTROL ' + c.resource + ': no map entry => the arm fails',
      async function () {
        const saved = aiScan.AI_SCANNED_TEXT[c.resource];
        assert.ok(saved, c.resource + ' is not in the map at all, so this '
          + 'control is not exercising anything');
        delete aiScan.AI_SCANNED_TEXT[c.resource];
        try {
          const row = await storedRow(c.app, c.resource, c.payload);
          const f = c.redact[0];
          assert.ok(leaks(row.data[f]).length > 0,
            'with ' + c.resource + ' REMOVED from the map the text still '
            + 'arrived clean. Something other than this gate is redacting it, '
            + 'so the arm above proves nothing about the gate.');
          assert.strictEqual(row.data.redaction, undefined,
            'a redaction block was written for a resource with no map entry');
        } finally {
          aiScan.AI_SCANNED_TEXT[c.resource] = saved;
        }
      });
  }

  section('6. the map and the exclusions are both declared, and disjoint');
  await test('no resource is both gated and excluded', function () {
    const both = Object.keys(aiScan.AI_SCANNED_TEXT)
      .filter(function (r) { return aiScan.DELIBERATELY_EXCLUDED[r]; });
    assert.deepStrictEqual(both, [],
      'these are in BOTH lists, so the record says two things: ' + both);
  });
  await test('every exclusion states a reason of real length', function () {
    const thin = Object.keys(aiScan.DELIBERATELY_EXCLUDED)
      .filter(function (r) { return (aiScan.DELIBERATELY_EXCLUDED[r] || '').length < 60; });
    assert.deepStrictEqual(thin, [],
      'an exclusion with no real reason is a resource nobody decided about: '
      + thin);
  });

  console.log('');
  console.log(pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
