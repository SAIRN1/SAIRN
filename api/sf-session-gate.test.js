// api/sf-session-gate.test.js
//
// REQUIREMENT: sf_accounts, sf_ledger and sf_vendor_prices -- SAIRNfreedom's
//   three Tier A resources -- are reachable only by a signed-in employee of
//   THAT post whose credential is still active.
//
// CROSS-TENANT-ISOLATION: none (the tenant boundary on these three is asserted
//   in api/sd-data-cross-tenant-dispatchers.test.js; this suite is about WHO
//   inside a post may act)
//
// Run:  node api/sf-session-gate.test.js
//
// ── WHAT THIS IS ──────────────────────────────────────────────────────────
// The END-TO-END arm of a five-piece change. The other four are asserted where
// they live -- the schema by its own verification queries, ROLES_BY_APP and
// api/sf-auth.js by api/sf-auth.test.js, the client header by inspection of
// sairnfreedom.html's single transport. This one drives the WHOLE CHAIN:
// api/sf-auth.js mints a real session, and api/sd-data.js's gate is asked to
// accept or refuse it.
//
// ── THE ORDER OF THE FIVE PIECES WAS DRIVEN, NOT CHOSEN ──────────────────
// Arming the gate first answers 403 to every real call, because until today
// SAIRNfreedom had no way to produce a session: no sf_employee_auth table, no
// `sairnfreedom` in ROLES_BY_APP (so signSessionToken THREW), no
// api/sf-auth.js, and no X-SD-Auth header anywhere in the client. The first
// arm below reproduces that state and proves the refusal, so the reason for
// the ordering is in the suite rather than only in a commit message.
//
// ── WHAT IT DOES NOT COVER ───────────────────────────────────────────────
// The database. The RLS policy and the grants at the foot of
// sql/sairnfreedom_employee_auth_schema.sql are not exercised here -- a wrong
// grant surfaces as a 42501 that api/sf-auth.js turns into NOT_GRANTED, which
// IS asserted, but the grant itself is a live-verification item.
//
// Some sf_ resources stay UNGATED by design, and the last pair of arms drives
// BOTH directions through the real dispatcher: an ungated resource is not
// refused, a gated one is. That pairing is the arm's whole value -- on its own
// the "stays ungated" half is satisfied by a gate that protects nothing.
//
// ── THE COUNT IS NOT WRITTEN HERE ANY MORE, AND THAT IS THE FIX ───────────
// This header said "the other 32 sf_ resources stay UNGATED by design" and the
// arm below named sf_members as its example. sf_members WAS GATED ON
// 2026-09-22 and this suite went red and stayed red -- discovered 2026-09-24
// while gating sf_signatures, two days later, by running it rather than by
// anyone noticing. A suite pinned to a moving number is a suite that expires
// on a date nobody writes down. The authoritative list is SD_SESSION_GATED in
// api/sd-data.js; api/sd-data-sf-session-gate.test.js asserts it against the
// approved set in both directions. This file's job is the CHAIN, not the list.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sf', 'gate', 'chain', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://fixture.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY
  || ['fixture', 'service', 'key'].join('-');

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const LIC = 'post-A-hash';
const GATED = ['sf_accounts', 'sf_ledger', 'sf_vendor_prices'];

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// One store serving BOTH handlers: the credential table api/sf-auth.js writes
// and api/sd-data.js's active re-check reads, plus the sf_ data rows. Using
// two stores would let the gate pass against a credential the auth endpoint
// never actually created.
function world() {
  const creds = [];
  const data = [
    { license_hash: LIC, account_id: 'A-1', data: { id: 'A-1', name: 'General Fund' } }
  ];
  const calls = [];
  return {
    creds: creds, calls: calls,
    fn: async function (url, opts) {
      const u = String(url);
      const method = (opts && opts.method) || 'GET';
      calls.push({ url: u, method: method });
      const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
      const eqs = [];
      q.split('&').forEach(function (p) {
        const m = p.match(/^([a-z_]+)=eq\.(.*)$/);
        if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
      });
      const match = function (r) {
        return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
      };
      const isCreds = u.indexOf('sairnfreedom_employee_auth') !== -1;
      const table = isCreds ? creds : data;
      if (method === 'POST') {
        const sent = JSON.parse(opts.body);
        const i = table.findIndex(function (r) {
          return r.license_hash === sent.license_hash
            && (isCreds ? r.employee_id === sent.employee_id : true);
        });
        if (i >= 0 && isCreds) table[i] = Object.assign({}, table[i], sent);
        else table.push(Object.assign({}, sent));
        return { ok: true, status: 200, json: async function () { return [sent]; } };
      }
      if (method === 'PATCH') {
        const patch = JSON.parse(opts.body);
        table.forEach(function (r, i) { if (match(r)) table[i] = Object.assign({}, r, patch); });
        return { ok: true, status: 204, json: async function () { throw new SyntaxError('no body'); } };
      }
      return { ok: true, status: 200, json: async function () { return table.filter(match); } };
    }
  };
}

function load(mod, licHash, fetchImpl) {
  const lic = path.join(__dirname, '_lib', 'license');
  delete require.cache[require.resolve(lic)];
  require.cache[require.resolve(lic)] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: licHash, trial_ends_at: null,
                 stripe_subscription_id: null, app_id: 'sairnfreedom' };
      }
    }
  };
  global.fetch = fetchImpl;
  const p = path.join(__dirname, mod);
  delete require.cache[require.resolve(p)];
  return require(p);
}

async function call(h, body, token) {
  const headers = { authorization: 'Bearer KEY' };
  if (token) headers['x-sd-auth'] = token;
  const res = mockRes();
  await h({ method: 'POST', headers: headers, body: body }, res);
  return res;
}

// Mints a REAL session through api/sf-auth.js -- never a hand-signed token.
// A hand-signed one would prove the gate accepts a signature; this proves the
// chain a real user walks actually produces something the gate accepts.
async function provision(w, employee_id, role) {
  let h = load('sf-auth.js', LIC, w.fn);
  if (!w.creds.length) {
    const r = await call(h, { action: 'bootstrap', employee_id: 'gov', pin: '123456' });
    assert.strictEqual(r.statusCode, 200, 'bootstrap failed: ' + JSON.stringify(r.body));
    if (employee_id === 'gov') return r.body.token;
  }
  const govLogin = await call(load('sf-auth.js', LIC, w.fn),
    { action: 'login', employee_id: 'gov', pin: '123456' });
  assert.strictEqual(govLogin.statusCode, 200, JSON.stringify(govLogin.body));
  if (employee_id === 'gov') return govLogin.body.token;
  h = load('sf-auth.js', LIC, w.fn);
  const s = await call(h, { action: 'setup', employee_id: employee_id, pin: '654321',
                            role: role }, govLogin.body.token);
  assert.strictEqual(s.statusCode, 200, 'setup failed: ' + JSON.stringify(s.body));
  const login = await call(load('sf-auth.js', LIC, w.fn),
    { action: 'login', employee_id: employee_id, pin: '654321' });
  assert.strictEqual(login.statusCode, 200, JSON.stringify(login.body));
  return login.body.token;
}

(async function () {
  console.log('SAIRNfreedom session gate -- the whole chain, end to end');

  // ════════════════════════════════════════════════════════════════════════
  section('THE STATE BEFORE ALL FIVE PIECES -- why the order was what it was');

  await test('no session at all is REFUSED on every gated resource', async () => {
    for (const resource of GATED) {
      const w = world();
      const h = load('sd-data.js', LIC, w.fn);
      const r = await call(h, { action: 'read', resource: resource, app_id: 'sairnfreedom' });
      assert.strictEqual(r.statusCode, 403,
        resource + ' served a caller with no session: ' + JSON.stringify(r.body));
      assert.strictEqual(r.body.error.code, 'FORBIDDEN');
    }
  });

  await test('...and that is exactly what a pre-2026-09-21 client would have got', async () => {
    // The client sent `Authorization: Bearer <licence>` and NOTHING else --
    // reproduced literally here. This is the arm that justifies arming the
    // gate FIFTH rather than first.
    const w = world();
    const h = load('sd-data.js', LIC, w.fn);
    const res = mockRes();
    await h({ method: 'POST', headers: { authorization: 'Bearer KEY' },
              body: { action: 'read', resource: 'sf_ledger', app_id: 'sairnfreedom' } }, res);
    assert.strictEqual(res.statusCode, 403, JSON.stringify(res.body));
  });

  // ════════════════════════════════════════════════════════════════════════
  section('THE CHAIN -- a real session minted by api/sf-auth.js is accepted');

  await test('a governor reads all three gated resources', async () => {
    for (const resource of GATED) {
      const w = world();
      const token = await provision(w, 'gov');
      const h = load('sd-data.js', LIC, w.fn);
      const r = await call(h, { action: 'read', resource: resource, app_id: 'sairnfreedom' }, token);
      assert.strictEqual(r.statusCode, 200,
        resource + ' refused a valid governor session: ' + JSON.stringify(r.body));
    }
  });

  await test('a finance officer reads the ledger -- the gate is about IDENTITY, not rank', async () => {
    // Deliberate: the gate asks "is this a signed-in, still-active employee of
    // this post", not "which capability". Narrowing it to a capability tier is
    // a product decision about who may see a ledger and nobody has made it.
    const w = world();
    const token = await provision(w, 'qm', 'finance.write');
    const h = load('sd-data.js', LIC, w.fn);
    const r = await call(h, { action: 'read', resource: 'sf_ledger', app_id: 'sairnfreedom' }, token);
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
  });

  await test('a WRITE is gated too, not only a read', async () => {
    const w = world();
    const token = await provision(w, 'gov');
    let h = load('sd-data.js', LIC, w.fn);
    const noTok = await call(h, { action: 'write', resource: 'sf_ledger',
                                  app_id: 'sairnfreedom', payload: { id: 'L-1' } });
    assert.strictEqual(noTok.statusCode, 403, JSON.stringify(noTok.body));
    h = load('sd-data.js', LIC, w.fn);
    const withTok = await call(h, { action: 'write', resource: 'sf_ledger',
                                    app_id: 'sairnfreedom', payload: { id: 'L-1' } }, token);
    assert.strictEqual(withTok.statusCode, 200, JSON.stringify(withTok.body));
  });

  // ════════════════════════════════════════════════════════════════════════
  section('THE PART THE TOKEN CANNOT PROVE -- still-active NOW');

  await test('a DEACTIVATED employee is refused on a still-valid token', async () => {
    // verifySessionToken proves the token was minted by us and has not
    // expired. It proves nothing about now, and a session outlives its own
    // credential's deactivation by up to 12h. This is what
    // credentialStillActive exists for, and it needs sairnfreedom in
    // AUTH_TABLE_BY_APP -- without that entry it answers NO_ACTIVE_CHECK and
    // the request is allowed on the token alone.
    const w = world();
    const token = await provision(w, 'qm', 'finance.write');
    w.creds.forEach(function (r) { if (r.employee_id === 'qm') r.active = false; });
    const h = load('sd-data.js', LIC, w.fn);
    const r = await call(h, { action: 'read', resource: 'sf_ledger', app_id: 'sairnfreedom' }, token);
    assert.strictEqual(r.statusCode, 403,
      'a deactivated employee kept ledger access on an old token: ' + JSON.stringify(r.body));
    assert.strictEqual(r.body.error.code, 'CREDENTIAL_INACTIVE', JSON.stringify(r.body));
  });

  await test('sairnfreedom IS in AUTH_TABLE_BY_APP, so the check can run at all', async () => {
    const auth = fs.readFileSync(path.join(__dirname, '_lib', 'auth.js'), 'utf8');
    const seg = auth.slice(auth.indexOf('const AUTH_TABLE_BY_APP'));
    const map = seg.slice(0, seg.indexOf('};'));
    assert.match(map, /sairnfreedom:\s*'sairnfreedom_employee_auth'/,
      'without this entry credentialStillActive answers NO_ACTIVE_CHECK, which '
      + 'is NOT a refusal -- the request proceeds on the token alone and only a '
      + 'console warning records it. That fails OPEN.');
  });

  // ════════════════════════════════════════════════════════════════════════
  section('SCOPE -- the gate covers these three and says which app');

  await test('a token from ANOTHER SAIRN app is refused', async () => {
    const { signSessionToken } = require('./_lib/auth');
    const foreign = signSessionToken({ app: 'stonedesk', employee_id: 'gov',
                                       role: 'owner', license_hash: LIC });
    const w = world();
    await provision(w, 'gov');
    const h = load('sd-data.js', LIC, w.fn);
    const r = await call(h, { action: 'read', resource: 'sf_ledger', app_id: 'sairnfreedom' }, foreign);
    assert.strictEqual(r.statusCode, 403,
      'a StoneDesk session opened a veterans post ledger: ' + JSON.stringify(r.body));
  });

  await test('SD_GATE_APP names sairnfreedom for all three', async () => {
    // Without the entry the gate defaults to expectedApp 'stonedesk', a
    // correctly signed-in caller fails verification, and every call answers
    // FORBIDDEN "sign in first" no matter what they do. That is the exact
    // defect `memory` produced on 2026-09-03.
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const seg = src.slice(src.indexOf('const SD_GATE_APP'));
    const map = seg.slice(0, seg.indexOf('};'));
    for (const resource of GATED) {
      assert.ok(map.indexOf("'" + resource + "': 'sairnfreedom'") !== -1,
        resource + ' is gated but has no SD_GATE_APP entry, so it would demand '
        + 'a stonedesk session');
    }
  });

  await test('THE GATE IS TABLE-DRIVEN, NOT BLANKET: a resource outside '
            + 'SD_SESSION_GATED is not refused by THIS gate', async () => {
    // ── MOVED 2026-10-13 (b7), WHICH IS WHAT THE OLD VERSION ASKED FOR ──────
    // This arm drove sf_bottle_fills and required "not 403", as the negative
    // half of the gate's control pair. Its own comment said: "if it is ever
    // approved, this arm is the thing to move, not to delete." It was approved
    // in b7 -- all 36 sf_ resources are now gated -- so the arm is moved.
    //
    // IT COULD NOT STAY POINTED AT ANY sf_ RESOURCE, and that is a statement
    // about the app rather than about this arm: THERE IS NO LONGER AN UNGATED
    // ONE. A negative control needs a subject that should legitimately pass,
    // and SAIRNfreedom no longer has one. Pretending otherwise by picking a
    // gated resource and inverting the expectation would assert the opposite of
    // the approved state -- which this arm already did once, for two days in
    // September, when it named sf_members after sf_members was gated.
    //
    // SO THE CONTROL IS RE-AIMED AT THE PROPERTY THAT ACTUALLY MATTERS and that
    // is still falsifiable: the gate must refuse by TABLE LOOKUP, not by app or
    // by prefix. A resource absent from SD_SESSION_GATED must not come back
    // with the gate's own refusal. If someone ever replaces the table lookup
    // with a prefix test -- gate anything starting sf_, or anything on a
    // SAIRNfreedom licence -- every positive arm in this file still passes and
    // this is the arm that fails.
    //
    // THE SUBJECT IS `render_usage`: in the dispatch's resource allow-list, and
    // NOT in SD_SESSION_GATED. The first draft of this arm used an invented
    // name (`sf_not_a_real_resource`) and WAS VACUOUS -- an unknown resource is
    // refused 400 by the allow-list BEFORE the gate is ever consulted, so the
    // request never reached the thing under test. Found by ablation rather than
    // by review: the gate's table lookup was replaced with a prefix test, this
    // arm still passed, and that is what a vacuous control looks like from
    // outside.
    //
    // WHAT THIS ARM CATCHES, stated as narrowly as it is true: a gate that
    // refuses EVERYTHING on a SAIRNfreedom licence, and a gate that grows to
    // cover a resource absent from its table.
    //
    // WHAT CATCHES THE PREFIX CASE IS A DIFFERENT ARM, and it was measured, not
    // assumed: `if ((SD_SESSION_GATED[...] ...) || resource starts with sf_)`
    // makes the single-dispatch-check arm in
    // api/sd-data-sf-session-gate.test.js fail, because its regex requires the
    // condition to BEGIN with the table lookup. Two arms in two files, each
    // catching what the other cannot -- recorded here so the next reader does
    // not have to re-derive which one is load-bearing for which failure.
    const w = world();
    const h = load('sd-data.js', LIC, w.fn);
    const r = await call(h, { action: 'read', resource: 'render_usage', app_id: 'sairnfreedom' });
    const msg = String((r.body && r.body.error && r.body.error.message) || '');
    assert.ok(!/sign in first/i.test(msg),
      'render_usage is NOT in SD_SESSION_GATED and was refused by the session '
      + 'gate anyway, so the gate is matching on something other than its '
      + 'table. Answer was ' + r.statusCode + ' ' + JSON.stringify(r.body));
    // AND IT MUST HAVE REACHED THE GATE AT ALL. The vacuity this arm was
    // rewritten to remove: a 400 from the resource allow-list means the
    // subject never got as far as the gate, and the assertion above would pass
    // for that reason instead of the intended one.
    assert.ok(!/resource must be one of/i.test(msg),
      'the subject was rejected by the resource allow-list before reaching the '
      + 'gate, so this control proves nothing: ' + r.statusCode + ' ' + msg);
  });

  // ── THE PAIRED POSITIVE, AND IT IS READ OFF THE TABLE ────────────────────
  // WITHOUT THIS, THE ARM ABOVE IS SATISFIED BY A GATE THAT PROTECTS NOTHING.
  // "Not 403" is true of every resource when SD_SESSION_GATED is empty, so the
  // negative on its own is a green run over an open door.
  //
  // WHY THE LIST IS DERIVED FROM api/sd-data.js RATHER THAN TYPED HERE
  // (2026-09-24): api/sd-data-session-gate.test.js carries a coverage arm that
  // asks whether every gated resource is DRIVEN somewhere, with a hand-written
  // map naming the suite for each. That map named three sf_ resources and the
  // gate held fifteen, so eleven of them -- minors' names, a felony flag, an
  // ORC 2915 payee record -- were gated in source and exercised by nothing,
  // and the arm had been red on origin/main since 2026-09-22 saying so. A
  // derived loop cannot fall behind the table that way: gate a sixteenth
  // resource and it is driven here in the same commit, with no list to update.
  //
  // It drives BOTH verbs and asserts ZERO database calls, because a refusal
  // that still reaches the store is a refusal that leaked on the way.
  const gatedSfResources = (function () {
    const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\n    \};/);
    assert.ok(m, 'SD_SESSION_GATED is gone -- this loop would silently drive nothing');
    const code = m[0].split('\n')
      .map((l) => (/^\s*(\/\/|\*|\/\*)/.test(l) ? '' : l)).join('\n');
    const out = [];
    (code.match(/'(sf_\w+)':\s*\[([^\]]*)\]/g) || []).forEach((entry) => {
      const name = entry.match(/'(sf_\w+)'/)[1];
      (entry.match(/'(read|write|reserve)'/g) || [])
        .forEach((a) => out.push([name, a.replace(/'/g, '')]));
    });
    return out;
  }());

  await test('the gated-resource list was actually parsed -- an empty loop '
            + 'passes every arm it does not run', () => {
    assert.ok(gatedSfResources.length >= 2,
      'parsed ' + gatedSfResources.length + ' gated sf_ pairs out of '
      + 'SD_SESSION_GATED. A regex that matched nothing produces a loop that '
      + 'asserts nothing and reports green.');
  });

  // ── THE LOOP COUNTS WHAT IT DROVE, AND A SHORTFALL IS ITS OWN FAILURE
  //    (2026-09-25). Found by attacking the shared coverage arm the way its
  //    own obligation asked: that arm credits EVERY sf_ table entry to this
  //    loop, and verifies only that this file mentions SD_SESSION_GATED and
  //    gatedSfResources -- two strings a `.slice(0, 4)` on this line leaves
  //    intact. Driven before fixing: with that slice planted, eleven gated
  //    resources lost their only coverage and BOTH suites stayed green. So
  //    the loop now tallies its own iterations and a final arm compares the
  //    tally to the parsed count -- narrowing the iterable, skipping inside
  //    the body, or filtering the list all show up as a number that does not
  //    match, in THIS file, where the narrowing happened.
  let sfPairsDriven = 0;
  for (const [resource, action] of gatedSfResources) {
    sfPairsDriven += 1;
    await test('DRIVEN: ' + resource + '/' + action + ' -> 403 with a licence '
              + 'key and NO session', async () => {
      const w = world();
      const h = load('sd-data.js', LIC, w.fn);
      const r = await call(h, { action: action, resource: resource,
                                app_id: 'sairnfreedom', payload: { id: 'X1' } });
      assert.strictEqual(r.statusCode, 403,
        resource + '/' + action + ' answered ' + r.statusCode + ' with no '
        + 'session token, so it is reachable on the licence key alone -- a key '
        + 'shipped to the browser. Body: ' + JSON.stringify(r.body));
      assert.strictEqual(w.calls.length, 0,
        resource + '/' + action + ' was refused but still made '
        + w.calls.length + ' database call(s) on the way.');
    });
  }

  await test('every parsed pair was actually iterated -- the loop cannot be '
            + 'quietly narrowed', () => {
    assert.strictEqual(sfPairsDriven, gatedSfResources.length,
      'the DRIVEN loop iterated ' + sfPairsDriven + ' of '
      + gatedSfResources.length + ' parsed pairs. Something narrowed the '
      + 'iterable or skipped members; the shared coverage arm credits ALL of '
      + 'them to this loop, so a shortfall here is uncovered Tier A surface '
      + 'that still reads as covered over there.');
  });

  await test('the client actually sends the header the gate reads', async () => {
    // The fourth piece, asserted where the other three cannot see it. A gate
    // nothing feeds is a gate that refuses everybody.
    const html = fs.readFileSync(path.join(__dirname, '..', 'sairnfreedom.html'), 'utf8');
    const i = html.indexOf('function sfData(');
    assert.ok(i > 0, 'sfData is gone -- the transport was renamed or removed');
    const body = html.slice(i, i + 1200);
    assert.ok(body.indexOf("X-SD-Auth") !== -1,
      'sairnfreedom.html\'s only sd-data transport does not send X-SD-Auth, so '
      + 'every gated call from the real app answers 403');
    assert.ok(body.indexOf('Authorization') !== -1,
      'the licence header is gone -- two secrets, two headers');
  });

  section('THE CLIENT CAN ACTUALLY OBTAIN A SESSION -- a gate nothing satisfies is a break');

  // -- ADDED AFTER TWO SABOTAGES SURVIVED ----------------------------------
  // api/_lib/employee-lifecycle-wiring.test.js checks the DEACTIVATION screen,
  // which is its subject, and nothing checked the ARRIVAL path. Mutating the
  // boot handler and sfUnlock to walk straight into the app -- which is what
  // they BOTH did before today -- left every arm on the platform green while
  // making sf_accounts, sf_ledger and sf_vendor_prices unreachable from the
  // real client. A 403 nobody can clear is a break, not a control, and it is
  // the exact failure that made the five pieces land in the order they did.
  const clientSrc = fs.readFileSync(path.join(__dirname, '..', 'sairnfreedom.html'), 'utf8');

  await test('the licence gate hands off to SIGN-IN, not straight to the app', async () => {
    const at = clientSrc.indexOf('function sfUnlock(');
    assert.ok(at > 0, 'sfUnlock is gone -- the licence gate was renamed or removed');
    const body = clientSrc.slice(at, at + 1600);
    assert.ok(body.indexOf("$('pin').classList.add('on')") !== -1,
      'sfUnlock no longer opens the sign-in pane, so a licence walks straight '
      + 'into an app whose ledger answers 403 with nothing on screen to say why');
    // THE CALL, NOT THE WORD. Asserting on `check_license` alone SURVIVED a
    // sabotage that replaced the call with a resolved promise -- because the
    // comment three lines above it in the source still contains the word, and
    // a comment is not a call. Caught by mutation, not by review.
    assert.ok(body.indexOf("sfAuth('check_license'") !== -1,
      'sfUnlock no longer validates the licence before moving on');
  });

  await test('a stored licence does not boot past sign-in either', async () => {
    // ANCHORED ON THE LISTENER, NOT THE WORD. The first occurrence of
    // "DOMContentLoaded" in this file is inside a COMMENT 5,000 lines earlier,
    // so a bare indexOf window read prose and proved nothing.
    const at = clientSrc.indexOf("document.addEventListener('DOMContentLoaded'");
    assert.ok(at > 0, 'no boot handler found');
    const body = clientSrc.slice(at, at + 2600);
    assert.ok(body.indexOf('sfRestoreSession()') !== -1,
      'the boot handler does not try to restore a session, so a stored licence '
      + 'opens the app with no token and every gated call answers 403');
    assert.ok(body.indexOf("$('pin').classList.add('on')") !== -1,
      'the boot handler has no path to the sign-in pane');
  });

  await test('the sign-in pane and the bootstrap link both exist in the markup', async () => {
    // A handler with no pane to show is the dormant-code failure one layer up.
    assert.ok(clientSrc.indexOf('id="pin"') !== -1, 'no sign-in pane');
    assert.ok(clientSrc.indexOf('id="l-eid"') !== -1 && clientSrc.indexOf('id="l-pin"') !== -1,
      'the sign-in pane has no employee ID / PIN fields');
    assert.ok(clientSrc.indexOf('sfShowBootstrap()') !== -1,
      'no route to bootstrap -- the FIRST officer of a post could never sign in, '
      + 'and there is deliberately no client-side first-run probe to fall back on');
  });


  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
