// api/auth-license-app-scope.test.js
//
// Run:  node api/auth-license-app-scope.test.js
//
// REQUIREMENT: an app's auth endpoint must refuse a licence key issued for a
//   DIFFERENT app -- and must still admit one it cannot attribute.
//
// ── WHAT WAS MEASURED, 2026-09-23 ─────────────────────────────────────────
// `SD-AUDIT-2026` is a StoneDesk licence. Against the LIVE SAIRNvet endpoint:
//
//     POST /api/sv-auth {"action":"check_license"}   Bearer SD-AUDIT-2026
//     -> 200 {"ok":true,"active":true,"app_id":"stonedesk"}
//
// All seventeen api/*-auth.js files validated `lic.valid` and `lic.active` and
// NONE of them compared the licence's own `app_id` to the app it was talking
// to. The response even echoes the foreign app back.
//
// ── WHY "sd-data.js ALREADY BOUNDS IT" IS NOT A DEFENCE ───────────────────
// It is true and it is not the point. api/sd-data.js:661 gates on the verified
// `lic.app_id`, so the foreign licence reaches no data. What it does not do is
// stop a credential ROW being written into another app's `*_employee_auth`
// table under a foreign licence's hash -- and it cannot, because that write
// never goes through sd-data.js.
//
// AND THE ENDPOINT'S OWN COMMENT IS THE ARGUMENT. sairnvet.html:2967 says the
// licence is checked with `check_license` BEFORE it is stored precisely so
// that "a bad licence key gets misattributed later" cannot happen -- "that
// misattribution is the reason check_license exists at all". A wrong-app key
// passes that check and is then stored. The gate is not merely redundant; it
// answers the exact question it was built to answer, wrongly.
//
// ── THE DIRECTION OF THE REFUSAL IS THE HARD PART ─────────────────────────
// An UNATTRIBUTABLE licence -- `app_id` null, blank, or a name the registry
// does not know -- is ADMITTED, deliberately. That is not softness; it is the
// posture api/_resources/index.js already took and wrote down: "cannot
// attribute -> cannot judge". Nothing read `lic.app_id` before 2026-09-04, so
// refusing an unrecognised one would lock out a real customer nobody can
// enumerate. Guardian's own rule: fail-closed in the WRONG DIRECTION is still
// wrong.
//
// So there are THREE states and they are kept three: match, mismatch,
// cannot-tell. Only the middle one refuses.
//
// ── CASE, BECAUSE IT HAS ALREADY BITTEN ONCE ──────────────────────────────
// api/_resources/index.js records a licence whose app_id was 'StoneDesk' being
// read as UNATTRIBUTABLE, which silently turned the boundary off for it. The
// comparison here goes through the SAME normApp/isKnownApp the registry uses,
// rather than a second lowercase() written next to it.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = __dirname;
const reg = require('./_resources');

let pass = 0, fail = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// ── PART A: the shared validator's own verdict ─────────────────────────────
// Driven against the REAL api/_lib/license.js with the licence_keys lookup
// stubbed, not against a model of it.

async function validate(rowAppId, expectedApp, opts) {
  delete require.cache[require.resolve('./_lib/license')];
  const { validateLicenseKey } = require('./_lib/license');
  const envURL = process.env.SUPABASE_URL, envKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const realFetch = global.fetch;
  process.env.SUPABASE_URL = 'https://stub.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub-key';
  global.fetch = async () => ({
    ok: true, status: 200,
    json: async () => ((opts && opts.noRow) ? [] : [{ status: 'active', app_id: rowAppId }])
  });
  try {
    return await validateLicenseKey('K', expectedApp);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = envURL;
    if (envKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = envKey;
  }
}

section('the validator answers in three states, not two');

t('a licence for THIS app -> match', async () => {
  const lic = await validate('stonedesk', 'stonedesk');
  assert.strictEqual(lic.app_scope, 'match');
});

t('a licence for ANOTHER app -> mismatch (the measured defect)', async () => {
  const lic = await validate('stonedesk', 'sairnvet');
  assert.strictEqual(lic.app_scope, 'mismatch',
    'a stonedesk licence was not flagged against sairnvet -- this is the live finding');
});

t('case is normalised the way the registry normalises it', async () => {
  // 'StoneDesk' read as UNATTRIBUTABLE once already, and silently disabled a
  // boundary. It must be a MATCH here, not a cannot-tell.
  assert.strictEqual((await validate('StoneDesk', 'stonedesk')).app_scope, 'match');
  assert.strictEqual((await validate('  STONEDESK  ', 'stonedesk')).app_scope, 'match');
  assert.strictEqual((await validate('StoneDesk', 'sairnvet')).app_scope, 'mismatch');
});

t('an UNATTRIBUTABLE licence is cannot-tell, never mismatch', async () => {
  for (const v of [null, '', '   ', 'not-an-app', 'shared']) {
    const lic = await validate(v, 'sairnvet');
    assert.strictEqual(lic.app_scope, 'unattributable',
      JSON.stringify(v) + ' was judged ' + lic.app_scope + ' -- it must not be refusable');
  }
});

t('an unknown EXPECTED app is cannot-tell too -- the judge is not exempt', async () => {
  // sd-sub-auth.js mints tokens for 'stonedesk_sub', which is not a registered
  // app. If a caller ever passes a name the registry does not know, this must
  // decline to judge rather than refuse every licence on earth.
  const lic = await validate('stonedesk', 'stonedesk_sub');
  assert.strictEqual(lic.app_scope, 'unattributable');
});

t('OMITTING the argument leaves every existing caller untouched', async () => {
  // api/sd-data.js, api/sd-render.js and _lib/sd-store.js all call this with
  // one argument. Their behaviour must be byte-identical to yesterday.
  const lic = await validate('stonedesk');
  assert.strictEqual(lic.app_scope, 'not-asked');
  assert.strictEqual(lic.valid, true);
  assert.strictEqual(lic.active, true);
  assert.strictEqual(lic.app_id, 'stonedesk');
});

t('an unknown KEY stays invalid and is not given a scope verdict to hide behind', async () => {
  const lic = await validate('stonedesk', 'sairnvet', { noRow: true });
  assert.strictEqual(lic.valid, false);
  assert.strictEqual(lic.app_scope, 'unattributable');
});

// ── PART B: through the REAL handlers ──────────────────────────────────────

const ENDPOINTS = [
  ['sv-auth.js', 'sairnvet'],
  ['sd-auth.js', 'stonedesk'],
  ['law-auth.js', 'sairnlaw'],
  ['sc-auth.js', 'sairncode'],
  ['alf-auth.js', 'sairncare'],
];

async function callHandler(file, licenceAppId, action) {
  const p = path.join(ROOT, file);
  delete require.cache[require.resolve(p)];
  delete require.cache[require.resolve('./_lib/license')];
  const handler = require(p);
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; }, setHeader() {} };
  const envURL = process.env.SUPABASE_URL, envKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const envSec = process.env.SD_AUTH_SECRET;
  const realFetch = global.fetch;
  process.env.SUPABASE_URL = 'https://stub.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub-key';
  process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-secret-for-tests';
  // Every lookup answers with the same row. The licence query reads app_id off
  // it; any employee query that follows simply finds nothing useful, which is
  // fine -- the property under test is decided before that point.
  global.fetch = async () => ({
    ok: true, status: 200, json: async () => [{ status: 'active', app_id: licenceAppId }]
  });
  try {
    await handler({ method: 'POST', headers: { authorization: 'Bearer K' },
                    body: { action: action, employee_id: 'nobody', pin: '000000' } }, res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = envURL;
    if (envKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = envKey;
    if (envSec === undefined) delete process.env.SD_AUTH_SECRET; else process.env.SD_AUTH_SECRET = envSec;
  }
  return out;
}

section('through the REAL handlers -- the foreign licence is refused');

t('a stonedesk licence is refused by every OTHER app it was measured against', async () => {
  for (const [file, app] of ENDPOINTS) {
    if (app === 'stonedesk') continue;
    const out = await callHandler(file, 'stonedesk', 'login');
    assert.strictEqual(out.code, 403,
      file + ' answered ' + out.code + ' to a stonedesk licence -- expected 403');
    assert.strictEqual(out.body && out.body.error && out.body.error.code, 'LICENSE_WRONG_APP',
      file + ' refused with ' + JSON.stringify(out.body) + ' -- expected LICENSE_WRONG_APP');
  }
});

t('THE CONTROL: each app still admits its OWN licence', async () => {
  // Without this a fix that refuses everything scores full marks above.
  for (const [file, app] of ENDPOINTS) {
    const out = await callHandler(file, app, 'login');
    const code = out.body && out.body.error && out.body.error.code;
    assert.notStrictEqual(code, 'LICENSE_WRONG_APP',
      file + ' refused its OWN licence -- the fix is inverted');
  }
});

t('an unattributable licence is still admitted by all of them', async () => {
  for (const [file] of ENDPOINTS) {
    const out = await callHandler(file, null, 'login');
    const code = out.body && out.body.error && out.body.error.code;
    assert.notStrictEqual(code, 'LICENSE_WRONG_APP',
      file + ' refused a licence with no app_id -- that locks out customers nobody can enumerate');
  }
});

t('the refusal happens BEFORE any credential is touched', async () => {
  // A wrong-app licence must not be able to probe employee_ids. If the refusal
  // for a foreign licence were to differ by employee_id, the gate would be an
  // oracle instead of a gate.
  const a = await callHandler('sv-auth.js', 'stonedesk', 'login');
  const b = await callHandler('sv-auth.js', 'stonedesk', 'setup');
  assert.deepStrictEqual(a.body, b.body,
    'two different actions gave different refusals for the same foreign licence');
  assert.strictEqual(a.code, b.code);
});

// ── PART C: the tripwire -- a NEW endpoint cannot skip this ────────────────

section('every auth endpoint asks the question');

t('all api/*-auth.js pass a second argument to validateLicenseKey', () => {
  const files = fs.readdirSync(ROOT).filter(f => /-auth\.js$/.test(f) && !/\.test\.js$/.test(f));
  assert.ok(files.length >= 17, 'expected at least 17 auth endpoints, found ' + files.length);
  const bare = [];
  files.forEach(f => {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    // The call with exactly one argument. Comments are not matched because the
    // anchor requires the `await` and the assignment.
    if (/=\s*await\s+validateLicenseKey\(\s*licenseKey\s*\)/.test(src)) bare.push(f);
  });
  assert.deepStrictEqual(bare, [],
    'these endpoints still validate a licence without asking which app it is for: ' + bare.join(', '));
});

t('sd-sub-auth passes the LICENCE app, not its token namespace', () => {
  // Its APP is 'stonedesk_sub' on purpose -- the file says "DELIBERATELY NOT
  // 'stonedesk'" because that literal separates the token it MINTS from the
  // employee token it CHECKS. The licence it receives is StoneDesk's. Passing
  // APP here would have been silently wrong: 'stonedesk_sub' is not a
  // registered app, so every judgement would have collapsed to cannot-tell and
  // the endpoint would look guarded while checking nothing.
  const src = fs.readFileSync(path.join(ROOT, 'sd-sub-auth.js'), 'utf8');
  assert.ok(/=\s*await\s+validateLicenseKey\(\s*licenseKey\s*,\s*LICENCE_APP\s*\)/.test(src),
    'sd-sub-auth.js does not pass LICENCE_APP');
  assert.ok(/const\s+LICENCE_APP\s*=\s*'stonedesk'/.test(src),
    "sd-sub-auth.js's LICENCE_APP is not 'stonedesk'");
  assert.ok(reg.isKnownApp('stonedesk') && !reg.isKnownApp('stonedesk_sub'),
    'the premise of this test changed: stonedesk_sub is now a registered app');
});

t('and the app each endpoint names is one the registry actually knows', () => {
  // A typo here is the quietest possible failure: an unknown expected app
  // collapses every judgement to cannot-tell, so the endpoint reports as
  // guarded and refuses nobody.
  const files = fs.readdirSync(ROOT).filter(f => /-auth\.js$/.test(f) && !/\.test\.js$/.test(f));
  const bad = [];
  files.forEach(f => {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    const m = src.match(/=\s*await\s+validateLicenseKey\(\s*licenseKey\s*,\s*([A-Za-z_$][\w$]*)\s*\)/);
    if (!m) return;
    const constName = m[1];
    const cm = src.match(new RegExp('const\\s+' + constName + "\\s*=\\s*'([a-z_]+)'"));
    if (!cm) { bad.push(f + ' (cannot read ' + constName + ')'); return; }
    if (!reg.isKnownApp(cm[1])) bad.push(f + ' -> ' + cm[1]);
  });
  assert.deepStrictEqual(bad, [], 'auth endpoints naming an app the registry does not know: ' + bad.join(', '));
});

// ── PART D: the negative control ───────────────────────────────────────────

section('the control: this suite can fail');

t('dropping the comparison lets the foreign licence straight back in', async () => {
  // Proves the Part B arms are testing the comparison and not some other
  // refusal that happens to return 403. The real validator is loaded and its
  // verdict is overwritten to what it said BEFORE the fix.
  delete require.cache[require.resolve('./_lib/license')];
  const mod = require('./_lib/license');
  const real = mod.validateLicenseKey;
  mod.validateLicenseKey = async (k, expected) => {
    const lic = await real(k, expected);
    delete lic.app_scope;            // the pre-fix return shape
    return lic;
  };
  try {
    const p = path.join(ROOT, 'sv-auth.js');
    delete require.cache[require.resolve(p)];
    const handler = require(p);
    const out = { code: null, body: null };
    const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; }, setHeader() {} };
    const realFetch = global.fetch;
    const envURL = process.env.SUPABASE_URL, envKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
    const envSec = process.env.SD_AUTH_SECRET;
    process.env.SUPABASE_URL = 'https://stub.invalid';
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub-key';
    // SD_AUTH_SECRET TOO, AND ITS ABSENCE IS WHY THIS LINE EXISTS. Without it
    // sv-auth answered a config 500 and this arm passed while proving nothing
    // -- the exact trap api/sd-sub-data-auth-ordering.test.js already records:
    // on a developer machine almost any call returns a config error, and a
    // control written against that is green whether the fix works or not.
    process.env.SD_AUTH_SECRET = envSec || 'stub-secret-for-tests';
    global.fetch = async () => ({ ok: true, status: 200, json: async () => [{ status: 'active', app_id: 'stonedesk' }] });
    try {
      await handler({ method: 'POST', headers: { authorization: 'Bearer K' },
                      body: { action: 'login', employee_id: 'nobody', pin: '000000' } }, res);
    } finally {
      global.fetch = realFetch;
      if (envURL === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = envURL;
      if (envKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = envKey;
      if (envSec === undefined) delete process.env.SD_AUTH_SECRET; else process.env.SD_AUTH_SECRET = envSec;
    }
    const code = out.body && out.body.error && out.body.error.code;
    // It must have got PAST the licence layer, not died before it.
    assert.notStrictEqual(out.code, 500,
      'the control died on configuration (' + JSON.stringify(out.body) + ') -- it proved nothing');
    assert.notStrictEqual(code, 'LICENSE_WRONG_APP',
      'the pre-fix shape still refused -- Part B may be passing for the wrong reason');
  } finally {
    mod.validateLicenseKey = real;
    delete require.cache[require.resolve('./_lib/license')];
  }
});

// ───────────────────────────────────────────────────────────────────────────
(async () => {
  for (const [name, fn] of run) {
    if (fn === null) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
