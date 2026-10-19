// api/b21-bridge-unknown-action.test.js
//
// Run:  node api/b21-bridge-unknown-action.test.js
//
// REQUIREMENT (b21): api/bridge.js refuses an UNKNOWN `?action=` outright and
// never lets it fall through to `handlePush`.
//
// ── WHY THIS EXISTS, AND IT IS NOT HYPOTHETICAL ───────────────────────────
// The dispatch block used to end `return handlePush(body, res, req)` with
// nothing between it and the proxy_get branch, so every `?action=` value this
// endpoint does not know became a push attempt. MEASURED by grepping every app
// file for the URL rather than reasoned about -- three live call sites land
// there today:
//
//   stonedesk.html:12814  ?action=maps-static    -- no such action
//   stonedesk.html:12927  ?action=maps-optimize  -- no such action
//   stonedesk.html:7795   NO ?action= at all, a sairn-mobile-sync envelope
//
// All three reached `handlePush` and were answered 401 NO_LICENCE / 403. So a
// caller asking for an action that has never existed was told its CREDENTIALS
// were wrong -- the wrong diagnosis pointed at the wrong layer, which is the
// same shape that sent a previous session hunting a RESEND_API_KEY that was
// present and correct the whole time (Guardian check 30's general rule).
//
// ── THE ARM THE DISPATCH ASKED FOR IS A NEGATIVE CONTROL ──────────────────
// A LICENCE-HEADED POST to an unknown action must be REFUSED and must write NO
// bridge_data row. The licence header matters: without it a 401 would be
// returned whether the refusal exists or not, and the arm would pass for the
// wrong reason. With a VALID licence and a VALID session the push path would
// otherwise succeed and upsert -- so the "nothing was written" half is only
// meaningful on this shape, and ARM E ablates the guard to prove it.
//
// Same stubbing decision as api/bridge-push-auth.test.js: the licence module is
// stubbed because SUPABASE_URL is unset on a developer machine, so a suite
// written against the real one would pass whether the logic is right or wrong.
// `api/_lib/auth.js` is NOT stubbed -- these arms sign real tokens and run the
// real verifier.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const LICENCE = require.resolve('./_lib/license');
let licenceAnswer = { valid: true, active: true, license_hash: 'hash-of-shop-a' };
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: { validateLicenseKey: async () => licenceAnswer },
};

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || 'bridge-unknown-action-test-secret';
const { signSessionToken } = require('./_lib/auth');

// Captured, not sent. The sd_employee_auth read is answered separately and is
// NOT counted as an upsert -- otherwise every "nothing was written" assertion
// would pass or fail on the wrong traffic, which is the trap the sibling suite
// already names.
let upserts = [];
let proxyFetches = [];
global.fetch = async (url, opts) => {
  const u = String(url);
  if (u.includes('sd_employee_auth')) {
    return { ok: true, status: 200, json: async () => ([{ active: true }]),
             text: async () => '[{"active":true}]' };
  }
  if (u.includes('bridge_data')) {
    upserts.push({ url: u, body: opts && opts.body });
    return { ok: true, status: 200, json: async () => ([{ license_hash: 'x' }]),
             text: async () => '[]' };
  }
  // Anything else is the proxy_get relay reaching an external host.
  proxyFetches.push(u);
  return { ok: true, status: 200, headers: { get: () => 'application/json' },
           json: async () => ({ relayed: true }), text: async () => '{}',
           body: null };
};

function mockRes() {
  const r = { _s: 0, _j: null };
  r.status = (s) => { r._s = s; return r; };
  r.json = (j) => { r._j = j; return r; };
  return r;
}

// `h` is the handler under test, so ARM E can drive an ABLATED copy through the
// identical call shape rather than a second hand-written one.
async function call(h, url, body, opts) {
  opts = opts || {};
  upserts = [];
  proxyFetches = [];
  const headers = {};
  if (opts.licence !== false) headers.authorization = 'Bearer SD-A-REAL-LICENCE';
  if (opts.session !== false) {
    headers['x-sd-auth'] = signSessionToken({ app: 'stonedesk',
      employee_id: 'emp-1', role: 'owner',
      license_hash: licenceAnswer.license_hash });
  }
  const res = mockRes();
  await h({ method: 'POST', url: url, headers: headers, body: body || {} }, res);
  return { status: res._s, body: res._j, upserts: upserts.slice(),
           proxyFetches: proxyFetches.slice() };
}

let pass = 0, fail = 0;
const failed = [];
function t(name, fn) {
  return Promise.resolve().then(fn)
    .then(() => { console.log('  ok   ' + name); pass++; })
    .catch((e) => {
      console.log('  FAIL ' + name + '\n       ' + e.message);
      fail++; failed.push(name.split('.')[0]);
    });
}
function section(s) { console.log('\n' + s); }

// ── THE ABLATION ANCHORS, NAMED ONCE (b22) ───────────────────────
// Every ablation arm below cuts the SAME guard out of a lifted copy of
// api/bridge.js, and each one used to carry its own copy of the source text
// to find it. b22 changed that guard's condition and TWO arms went red with
// "the anchor has drifted" -- which is the arms working, and also four
// places to re-seat instead of one. Named here so the next change to the
// guard is a one-line fix, and so a drifted anchor fails LOUDLY rather than
// silently ablating nothing.
const GUARD_ANCHOR = '  if (!action || KNOWN_ACTIONS.indexOf(action) === -1) {';
const FALLTHROUGH_ANCHOR = '\n  return handlePush(body, res, req);';

const handler = require('./bridge.js');
const PUSH_BODY = { invoices: [{ id: 'i1', amount: 10 }] };

(async () => {
  console.log('api/bridge.js -- an unknown ?action= is refused, not pushed');

  // ── A. THE NEGATIVE CONTROL THE DISPATCH ASKED FOR ──────────────────────
  section('A. a LICENCE-HEADED POST to an unknown action is refused and writes nothing');

  await t('A1. ?action=maps-optimize -- a REAL live call site -- is refused 400 '
        + 'UNKNOWN_ACTION and writes NO bridge_data row', async () => {
    const r = await call(handler, '/api/bridge?action=maps-optimize', PUSH_BODY);
    assert.strictEqual(r.status, 400, 'status was ' + r.status + ': '
      + JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'UNKNOWN_ACTION',
      'code was ' + JSON.stringify(r.body));
    // THE HALF THAT MATTERS. The licence and session are both VALID here, so
    // without the refusal this request upserts.
    assert.strictEqual(r.upserts.length, 0,
      'an unknown action still wrote a bridge_data row: '
      + JSON.stringify(r.upserts));
  });

  await t('A2. ?action=maps-static -- the other real live call site -- same '
        + 'answer, so the refusal is on the CLASS and not on one string',
    async () => {
      const r = await call(handler, '/api/bridge?action=maps-static', PUSH_BODY);
      assert.strictEqual(r.status, 400, JSON.stringify(r.body));
      assert.strictEqual(r.body.error.code, 'UNKNOWN_ACTION');
      assert.strictEqual(r.upserts.length, 0);
    });

  await t('A3. and an action nobody has ever sent is refused identically -- a '
        + 'guard that only knows the two strings already in the tree is a '
        + 'blocklist wearing an allowlist\'s name', async () => {
    const r = await call(handler, '/api/bridge?action=' + encodeURIComponent('../../etc/passwd'),
                         PUSH_BODY);
    assert.strictEqual(r.status, 400, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'UNKNOWN_ACTION');
    assert.strictEqual(r.upserts.length, 0);
  });

  await t('A4. NO LICENCE on an unknown action is still UNKNOWN_ACTION, not '
        + 'NO_LICENCE -- the refusal names what is actually wrong rather than '
        + 'the first gate it happens to reach', async () => {
    const r = await call(handler, '/api/bridge?action=maps-optimize', PUSH_BODY,
                         { licence: false, session: false });
    assert.strictEqual(r.status, 400, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'UNKNOWN_ACTION',
      'an unauthenticated unknown action was diagnosed as a credential '
      + 'problem: ' + JSON.stringify(r.body));
  });

  // ── B. THE MESSAGE IS DERIVED, NOT WRITTEN OUT ──────────────────────────
  section('B. the refusal names the accepted actions, derived from KNOWN_ACTIONS');

  await t('B1. the message names BOTH accepted actions', async () => {
    const r = await call(handler, '/api/bridge?action=nope', PUSH_BODY);
    const m = r.body.error.message;
    assert.ok(/\?action=push/.test(m), 'push not named: ' + m);
    assert.ok(/\?action=proxy_get/.test(m), 'proxy_get not named: ' + m);
  });

  await t('B2. ...and does NOT name `pull`, which was removed 2026-09-17 for '
        + 'serving one tenant\'s data to an unauthenticated GET keyed on a RAW '
        + 'licence key. A refusal that advertises a withdrawn read side is '
        + 'worse than no refusal', async () => {
    const r = await call(handler, '/api/bridge?action=nope', PUSH_BODY);
    assert.ok(!/pull/.test(r.body.error.message),
      'the refusal advertises pull: ' + r.body.error.message);
  });

  await t('B3. ...and it states that nothing was written, because a 400 on a '
        + 'write endpoint is otherwise ambiguous about whether the row landed',
    async () => {
      const r = await call(handler, '/api/bridge?action=nope', PUSH_BODY);
      assert.ok(/nothing was written/i.test(r.body.error.message),
        r.body.error.message);
    });

  // ── C. THE TWO REAL ACTIONS STILL WORK ──────────────────────────────────
  section('C. CONTROL -- the live callers are unaffected');

  await t('C1. ?action=push with a valid licence and session STILL upserts. '
        + 'Without this arm the refusal could be a wall and every arm above '
        + 'would still pass', async () => {
    const r = await call(handler, '/api/bridge?action=push', PUSH_BODY);
    assert.strictEqual(r.status, 200, JSON.stringify(r.body));
    assert.strictEqual(r.upserts.length, 1,
      'the one live push caller stopped writing');
  });

  await t('C2. data_type:proxy_get with NO ?action= still relays -- this is how '
        + 'sairnbuild.html:7754 and StoneDesk signal it, and requiring them to '
        + 'change was never on the table', async () => {
    const r = await call(handler, '/api/bridge',
      { source_app: 'sairnbuild', data_type: 'proxy_get',
        payload: { url: 'https://api.stlouisfed.org/fred/series/observations?x=1' } });
    assert.notStrictEqual(r.status, 400,
      'the proxy_get body signal was swallowed by the unknown-action refusal: '
      + JSON.stringify(r.body));
    assert.strictEqual(r.upserts.length, 0, 'a proxy_get wrote a row');
  });

  await t('C3. ?action=proxy_get in the QUERY is also still accepted -- both '
        + 'spellings were documented and only one is used, so the unused one is '
        + 'exactly the kind of thing a narrowing change breaks silently',
    async () => {
      const r = await call(handler, '/api/bridge?action=proxy_get',
        { payload: { url: 'https://api.stlouisfed.org/fred/series/observations?x=1' } });
      assert.notStrictEqual(r.status, 400, JSON.stringify(r.body));
    });

  // ── D. THE RESIDUAL b21 DECLARED, NOW CLOSED (b22) ────────────────
  // THESE ARMS ARE RE-AIMED, NOT DELETED, and the difference is the point.
  // b21 asserted that an ABSENT ?action= reaches handlePush and said IN THE ARM
  // TEXT that if that ever changed, THIS is the arm to update. It changed; this
  // is that update. Deleting D1 to go green would have destroyed the only
  // record that the old behaviour was a DECISION rather than an oversight, so
  // the old expectation is quoted in each arm and the reason it reversed is
  // named at the line.
  section('D. an ABSENT ?action= is REFUSED too (b22) -- the residual b21 declared, closed after censusing every caller');

  await t('D1. no ?action= and no data_type is REFUSED 400 UNKNOWN_ACTION and '
        + 'writes NOTHING. RE-AIMED in b22: in b21 this arm asserted '
        + 'notStrictEqual(400) and strictEqual(200), because the absent case was '
        + 'a declared residual then. Closed after a census of EIGHT /api/bridge '
        + 'call sites found that every LEGITIMATE action-less caller signals '
        + 'data_type:proxy_get and is matched BEFORE this branch', async () => {
    const r = await call(handler, '/api/bridge', PUSH_BODY);
    assert.strictEqual(r.status, 400,
      'an absent action is no longer refused -- b22 closed this residual, so a '
      + '200 here is a REGRESSION of that decision rather than the old '
      + 'behaviour legitimately returning: status was ' + r.status);
    assert.strictEqual(r.body.error.code, 'UNKNOWN_ACTION',
      JSON.stringify(r.body));
    assert.strictEqual(r.upserts.length, 0,
      'an action-less request still wrote a bridge_data row');
  });

  await t('D1b. ...and the message says NO ACTION WAS GIVEN rather than naming a '
        + 'bogus one. An absent selector and a misspelled selector are different '
        + 'mistakes that a caller fixes differently, so ONE branch answers both '
        + 'and the WORDING still tells them apart', async () => {
    const absent = await call(handler, '/api/bridge', PUSH_BODY);
    const bogus = await call(handler, '/api/bridge?action=nope', PUSH_BODY);
    assert.ok(/no action was given/i.test(absent.body.error.message),
      absent.body.error.message);
    assert.ok(/no such action/i.test(bogus.body.error.message),
      bogus.body.error.message);
    // BOTH still name the accepted set, so the refusal is derived from
    // KNOWN_ACTIONS on both paths and not written out on one of them.
    for (const m of [absent.body.error.message, bogus.body.error.message]) {
      assert.ok(/\?action=push/.test(m) && /\?action=proxy_get/.test(m), m);
    }
  });

  await t('D1c. an EMPTY ?action= is refused too, and this is the arm that proves '
        + 'the guard tests for a MISSING NAME and not a MISSING PARAMETER -- '
        + 'getQueryParam returns null for one and the empty string for the '
        + 'other, and a guard written against only null would let this through '
        + 'to handlePush', async () => {
    const r = await call(handler, '/api/bridge?action=', PUSH_BODY);
    assert.strictEqual(r.status, 400, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'UNKNOWN_ACTION');
    assert.strictEqual(r.upserts.length, 0);
  });

  await t('D2. THE THREE-NULL WRITE IS GONE. RE-AIMED in b22: in b21 this arm '
        + 'asserted that stonedesk.html:7795 sairn-mobile-sync envelope reached '
        + 'handlePush and UPSERTED {jobs:null, invoices:null, employees:null}. '
        + 'That was the real finding b21 routed, and the absent-action refusal '
        + 'closes it AT THE ENDPOINT -- the envelope is refused and writes no '
        + 'row at all', async () => {
    const r = await call(handler, '/api/bridge',
      { app_id: 'stonedesk', event_type: 'pos_sale', source_device: 'mobile',
        timestamp: '2026-10-19T00:00:00.000Z', payload: { num: 'INV-1' } });
    assert.strictEqual(r.status, 400, JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'UNKNOWN_ACTION');
    assert.strictEqual(r.upserts.length, 0,
      'the three-null row is STILL being written: ' + JSON.stringify(r.upserts));
  });

  await t('D2b. ...and so are the OTHER TWO action-less callers the b22 census '
        + 'found -- stonedesk.html:2954 sendToNetwork {type:learn} and :19939 '
        + 'sairnSyncAll {type:full-sync}. NEITHER was known to b21, which '
        + 'grepped the literal URL and missed every caller that goes through a '
        + 'BRIDGE / SAIRN_BRIDGE constant', async () => {
    const learn = await call(handler, '/api/bridge',
      { from: 'stonedesk', to: 'network', type: 'learn', payload: { x: 1 } });
    const sync = await call(handler, '/api/bridge',
      { from: 'stonedesk', to: 'all', type: 'full-sync',
        timestamp: '2026-10-19T00:00:00.000Z' });
    for (const pair of [['sendToNetwork', learn], ['sairnSyncAll', sync]]) {
      const name = pair[0], r = pair[1];
      assert.strictEqual(r.status, 400, name + ': ' + JSON.stringify(r.body));
      assert.strictEqual(r.body.error.code, 'UNKNOWN_ACTION', name);
      assert.strictEqual(r.upserts.length, 0, name + ' wrote a row');
    }
  });

  await t('D2c. AND THE CALLER-SIDE DEFECT THIS DOES *NOT* FIX, asserted so the '
        + 'refusal is not credited with closing it: the endpoint answers 400 '
        + 'with a machine-readable code, and stonedesk.html:19939 will STILL '
        + 'toast "All apps synced" -- fetch RESOLVES on a 4xx, so its catch '
        + 'never runs. The refusal turns 401 into 400 and changes nothing the '
        + 'user sees. stonedesk.html is claimed; this is routed', async () => {
    const r = await call(handler, '/api/bridge',
      { from: 'stonedesk', to: 'all', type: 'full-sync' });
    assert.strictEqual(r.status, 400, JSON.stringify(r.body));
    assert.ok(r.body && r.body.error && r.body.error.code === 'UNKNOWN_ACTION',
      'the refusal must carry a machine-readable code, because branching on '
      + 'res.ok or on this code is the only way a caller can stop claiming '
      + 'success it did not have');
  });

  // ── E. ABLATION -- remove the guard and D1 AND A1 must go RED ───────
  // b22 ADDS AN ABSENT-ACTION ABLATION (E3) beside the unknown-action one,
  // because an ablation that reddens A1 alone does NOT show the ABSENT case
  // is held by anything -- ONE condition now covers both, so an ablation of
  // it has to be shown to redden BOTH, or D1 could be passing because the
  // handler happens to refuse somewhere else entirely.
  section('E. ABLATION -- the OLD fall-through, and A1 fails on it');

  await t('E1. with the unknown-action refusal REMOVED, ?action=maps-optimize '
        + 'reaches handlePush and UPSERTS a bridge_data row -- so A1 is testing '
        + 'this guard and not something else. This is the pre-b21 behaviour, '
        + 'reproduced on purpose', async () => {
    const src = fs.readFileSync(path.join(__dirname, 'bridge.js'), 'utf8');
    // Cut exactly the refusal, by its own code constant, and leave the rest of
    // the file byte-identical. Anchored on the `if (action !== null` condition
    // through its closing `}` so the ablation cannot silently remove more.
    const start = src.indexOf(GUARD_ANCHOR);
    assert.notStrictEqual(start, -1, 'the guard was not found -- this ablation '
      + 'is anchored on SOURCE TEXT and the anchor has drifted, which means it '
      + 'is no longer ablating anything. FIX THE ANCHOR, DO NOT DELETE THE ARM. '
      + 'Last re-seated in b22 when the condition became `!action || ...`; the '
      + 'arm caught its own staleness that time, which is the whole reason it '
      + 'asserts the anchor exists before trusting the ablation');
    const end = src.indexOf(FALLTHROUGH_ANCHOR, start);
    assert.notStrictEqual(end, -1, 'the fall-through after the guard was not found');
    const ablated = src.slice(0, start) + src.slice(end + 1);
    // ASSERT ON THE CODE LITERAL, NOT THE BARE NAME. The first draft of this
    // arm asserted `!ablated.includes('UNKNOWN_ACTION')` and FAILED on a
    // correct ablation, because KNOWN_ACTIONS' own header comment says "the
    // UNKNOWN_ACTION refusal below". An ablation check that matches prose
    // about the code cannot tell a removed guard from a described one.
    assert.ok(!/code: 'UNKNOWN_ACTION'/.test(ablated),
      'the ablation left the refusal in place, so this arm proves nothing');

    // INSIDE api/, not os.tmpdir(). The ablated copy still does
    // `require('./_lib/license')`, and a relative require resolves from the
    // FILE's directory -- a temp-dir copy dies with MODULE_NOT_FOUND, which is
    // a harness failure wearing an arm failure's clothes.
    const tmp = path.join(__dirname,
      '.bridge-ablated-' + process.pid + '.js');
    fs.writeFileSync(tmp, ablated, 'utf8');
    let ablatedHandler;
    try {
      ablatedHandler = require(tmp);
      const r = await call(ablatedHandler, '/api/bridge?action=maps-optimize',
                           PUSH_BODY);
      assert.strictEqual(r.status, 200,
        'the ablated handler did not reach handlePush -- the ablation removed '
        + 'the wrong thing: ' + r.status + ' ' + JSON.stringify(r.body));
      assert.strictEqual(r.upserts.length, 1,
        'the ablated handler refused anyway, so A1 may be passing for another '
        + 'reason');
    } finally {
      try { fs.unlinkSync(tmp); } catch (e) { /* best effort */ }
    }
  });

  await t('E2. CLEAN -- the ablation is a REMOVAL, not a break: the ablated '
        + 'handler still serves ?action=push normally. Without this, E1 would '
        + 'also pass if the ablation had simply corrupted the file', async () => {
    const src = fs.readFileSync(path.join(__dirname, 'bridge.js'), 'utf8');
    const start = src.indexOf(GUARD_ANCHOR);
    const end = src.indexOf(FALLTHROUGH_ANCHOR, start);
    const ablated = src.slice(0, start) + src.slice(end + 1);
    const tmp = path.join(__dirname,
      '.bridge-ablated-clean-' + process.pid + '.js');
    fs.writeFileSync(tmp, ablated, 'utf8');
    try {
      const h = require(tmp);
      const r = await call(h, '/api/bridge?action=push', PUSH_BODY);
      assert.strictEqual(r.status, 200, JSON.stringify(r.body));
      assert.strictEqual(r.upserts.length, 1);
    } finally {
      try { fs.unlinkSync(tmp); } catch (e) { /* best effort */ }
    }
  });

  await t('E3. ABLATION, THE ABSENT HALF: with the same guard cut, an '
        + 'action-less request reaches handlePush and UPSERTS. So D1 is held by '
        + 'THIS condition and not by an unrelated refusal further down -- one '
        + 'condition covers both cases now, and an ablation of it must redden '
        + 'both or neither arm is attributable', async () => {
    const s0 = fs.readFileSync(path.join(__dirname, 'bridge.js'), 'utf8');
    const start = s0.indexOf(GUARD_ANCHOR);
    assert.notStrictEqual(start, -1, 'the guard was not found -- re-seat the '
      + 'anchor, do not delete the arm');
    const end = s0.indexOf(FALLTHROUGH_ANCHOR, start);
    assert.notStrictEqual(end, -1, 'the fall-through after the guard was not found');
    const ablated = s0.slice(0, start) + s0.slice(end + 1);
    assert.ok(!/code: 'UNKNOWN_ACTION'/.test(ablated),
      'the ablation left the refusal in place, so this arm proves nothing');
    const tmp = path.join(__dirname, '.bridge-abl-absent-' + process.pid + '.js');
    fs.writeFileSync(tmp, ablated, 'utf8');
    try {
      const h = require(tmp);
      const r = await call(h, '/api/bridge', PUSH_BODY);
      assert.strictEqual(r.status, 200,
        'the ablated handler did not reach handlePush on an ABSENT action: '
        + r.status + ' ' + JSON.stringify(r.body));
      assert.strictEqual(r.upserts.length, 1,
        'the ablated handler refused an action-less request anyway, so D1 may '
        + 'be passing for a reason other than this guard');
    } finally {
      try { fs.unlinkSync(tmp); } catch (e) { /* best effort */ }
    }
  });

  await t('E4. NEGATIVE CONTROL ON THE ABLATION ITSELF: the ablated handler still '
        + 'relays a data_type:proxy_get body. Without this, E1 and E3 could both '
        + 'be measuring a file that no longer routes anything rather than one '
        + 'with a single guard removed', async () => {
    const s0 = fs.readFileSync(path.join(__dirname, 'bridge.js'), 'utf8');
    const start = s0.indexOf(GUARD_ANCHOR);
    const end = s0.indexOf(FALLTHROUGH_ANCHOR, start);
    const ablated = s0.slice(0, start) + s0.slice(end + 1);
    const tmp = path.join(__dirname, '.bridge-abl-ctl-' + process.pid + '.js');
    fs.writeFileSync(tmp, ablated, 'utf8');
    try {
      const h = require(tmp);
      const r = await call(h, '/api/bridge',
        { data_type: 'proxy_get',
          payload: { url: 'https://api.stlouisfed.org/fred/series/observations?x=1' } });
      assert.notStrictEqual(r.status, 400, JSON.stringify(r.body));
      assert.strictEqual(r.upserts.length, 0, 'a proxy_get wrote a row');
    } finally {
      try { fs.unlinkSync(tmp); } catch (e) { /* best effort */ }
    }
  });

  console.log('\nbridge unknown action: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) console.log('FAILED: ' + failed.join(', '));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no arm result should be read as a pass:', e);
  process.exit(1);
});
