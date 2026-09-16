// api/sd-data-sairnlaw-resources.test.js
// Plain node:assert tests. Run: node api/sd-data-sairnlaw-resources.test.js
//
// PIECE B. sairnlaw.html wrote TWENTY distinct resources across 31 call sites
// and api/_resources/sairnlaw.js registered FOUR. The other fifteen were
// refused by the resource allowlist before any credential mattered -- proven
// live against the deployed endpoint with a control, same bogus licence key
// both times and only the resource name different:
//
//   law_invoices -> 400 "resource must be one of ..."   (refused at the gate)
//   law_matters  -> 401 INVALID_LICENSE                 (past the gate)
//
// 23 call sites, including BILLABLE TIME, invoices, matter documents (six
// sites), operating-account transactions and bank statements. Every failure
// rendered as "server sync not yet enabled for this app".
//
// THE THING MOST WORTH ASSERTING IS NOT THAT THE BRANCH WORKS. It is that all
// four places that must agree DO agree: the client's write calls, the
// registry, the handler map, and the SQL. A resource missing from any one of
// them fails in a different and quieter way --
//
//   in the client but not the registry -> 400 at the allowlist   (this defect)
//   in the registry but no branch      -> "Unsupported action/resource"
//                                         (exactly what law_deadlines did, and
//                                         the note that branch still carries)
//   branch but no table                -> 503 NOT_PROVISIONED
//
// so the cross-check runs in every direction rather than one.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname + path.sep + '..';
const registry = require('./_resources/sairnlaw.js');
const merged = require('./_resources/index.js');
const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8').replace(/\r\n/g, '\n');
const HTML = fs.readFileSync(path.join(ROOT, 'sairnlaw.html'), 'utf8').replace(/\r\n/g, '\n');
const SQL = fs.readFileSync(path.join(ROOT, 'sql', 'sairnlaw_data_extended_schema.sql'), 'utf8').replace(/\r\n/g, '\n');

const LIC_HASH = 'test-hash';
function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
// A REAL SIGNED SESSION, not a stubbed one, and signed against the hash the
// HANDLER derives -- api/_lib/license.js hashes the bearer key, and a token
// signed against anything else verifies fine in isolation and is rejected by
// the handler with an indistinguishable NO_SESSION. sairn-api-tester section 2.
const { signSessionToken } = require('./_lib/auth');
const tok = (role) => signSessionToken({ app: 'sairnlaw', employee_id: 'emp-' + role, role: role, license_hash: LIC_HASH });
// role defaults to a real signed owner session; pass null for NO session.
function mockReq(body, role) {
  const headers = { authorization: 'Bearer GOOD-KEY' };
  const r = role === undefined ? 'owner' : role;
  if (r !== null) headers['x-sd-auth'] = tok(r);
  return { method: 'POST', headers: headers, body: body };
}
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: LIC_HASH, trial_ends_at: null, stripe_subscription_id: null }) }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

const handlerBlock = (() => {
  const a = SRC.indexOf('const LAW_RESOURCES = {');
  assert.ok(a > 0, 'LAW_RESOURCES map not found in api/sd-data.js');
  const b = SRC.indexOf('const LEG_RESOURCES = {', a);
  return SRC.slice(a, b);
})();
const HANDLED = (() => {
  const map = handlerBlock.slice(0, handlerBlock.indexOf('};'));
  const out = {};
  (map.match(/law_\w+:\s*'\w+'/g) || []).forEach((p) => {
    const [k, v] = p.split(':').map((x) => x.trim().replace(/'/g, ''));
    out[k] = v;
  });
  return out;
})();
const CLIENT_WRITES = [...new Set([...HTML.matchAll(/sdnData\('write','(law_\w+)'/g)].map((m) => m[1]))];
// ── BESPOKE WAS A HARDCODED FOUR AND THERE ARE FIVE (fixed 2026-09-16) ──────
// `law_trust_reconcile` shipped with a real branch at api/sd-data.js and was in
// neither this list nor HANDLED, so the orphan arm below reported it as
// "registered with no handler" -- a FALSE FINDING about a resource that works,
// standing in a suite whose whole subject is resources that do not.
//
// The list is now DERIVED from the branches that exist, not kept by hand. A
// hand-kept list of the things a checker should skip goes stale in exactly one
// direction: silently, toward false findings, on the day somebody adds the
// fifth. That is the pinned-list-drift shape this repo has corrected
// repeatedly, and the fix is never a longer hand-kept list.
//
// DERIVING IT WOULD MAKE ONE ARM VACUOUS AND THAT ARM IS EXCLUDED BY NAME.
// "every bespoke resource still has its branch" cannot be asserted against a
// list built BY looking for branches -- it would assert that what was found was
// found. That arm keeps an explicit expectation (BESPOKE_EXPECTED) and this
// derived set is checked AGAINST it, so a branch that disappears is still a
// failure and a branch that is ADDED is not a false finding.
const BESPOKE = [...new Set(
  [...SRC.matchAll(/resource === '(law_\w+)'/g)].map((m) => m[1])
)].filter((r) => !HANDLED[r]).sort();
// What we expect to be there. A name here with no branch is a REGRESSION; a
// branch here with no name is a new bespoke resource somebody must add.
const BESPOKE_EXPECTED = ['law_clients', 'law_deadlines', 'law_matters',
                          'law_trust_reconcile', 'law_trusttx'];

let passed = 0, total = 0;
async function test(name, fn) {
  total++;
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

async function main() {
  console.log('api/sd-data.js -- SAIRNlaw extended resources');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  process.env.SD_AUTH_SECRET = ['law', 'resources', 'fixture'].join('-');

  // ── the four-way cross-check ────────────────────────────────────────────
  await test('EVERY resource the client writes is registered -- the defect itself', () => {
    const missing = CLIENT_WRITES.filter((r) => registry.resources.indexOf(r) === -1);
    assert.deepStrictEqual(missing, [],
      'written by sairnlaw.html and refused at the allowlist: ' + missing.join(', '));
    assert.ok(CLIENT_WRITES.length >= 19, 'expected 19+ law writes in the client, found ' + CLIENT_WRITES.length);
  });

  await test('every registered resource has a HANDLER -- registering a name is not sufficient', () => {
    // A registered name with no branch passes the allowlist and falls through
    // to "Unsupported action/resource combination", which is exactly what
    // law_deadlines returned until its branch existed.
    const orphans = registry.resources.filter((r) => !HANDLED[r] && BESPOKE.indexOf(r) === -1);
    assert.deepStrictEqual(orphans, [], 'registered with no handler: ' + orphans.join(', '));
  });

  await test('every handled resource has a TABLE, and the id column matches', () => {
    Object.keys(HANDLED).forEach((r) => {
      assert.ok(SQL.indexOf('create table if not exists public.' + r + ' (') !== -1, 'no table for ' + r);
      assert.ok(SQL.indexOf('grant select, insert, update on public.' + r + ' to service_role;') !== -1, 'no grant for ' + r);
      const t = SQL.slice(SQL.indexOf('create table if not exists public.' + r + ' ('));
      const body = t.slice(0, t.indexOf(');'));
      assert.ok(body.indexOf('\n  ' + HANDLED[r] + ' text not null,') !== -1, r + ' has no ' + HANDLED[r] + ' column');
      assert.ok(body.indexOf('unique (license_hash, ' + HANDLED[r] + ')') !== -1, r + ' is not unique on (license_hash, ' + HANDLED[r] + ')');
    });
  });

  await test('no handler is orphaned the other way -- every mapped name is registered', () => {
    const extra = Object.keys(HANDLED).filter((r) => registry.resources.indexOf(r) === -1);
    assert.deepStrictEqual(extra, [], 'handled but unregistered: ' + extra.join(', '));
    assert.strictEqual(Object.keys(HANDLED).length, 15);
  });

  await test('the bespoke resources were NOT folded into the generic map', () => {
    // law_matters and law_trusttx promote real columns (client_id, matter_id,
    // amount, type, status) a generic loop would not populate, and law_trusttx
    // carries a balance guard. Folding them in would drop both.
    BESPOKE.forEach((r) => assert.ok(!HANDLED[r], r + ' was folded into the generic map -- its promoted columns and guard would be lost'));
  });

  await test('every bespoke branch we EXPECT still exists -- asserted against an '
             + 'explicit list, not against the one derived from the branches', () => {
    // THIS IS THE ARM THE DERIVATION WOULD HAVE MADE VACUOUS. Asserting that
    // each name in BESPOKE has a branch, when BESPOKE was built by finding
    // branches, is "what was found was found" -- green against any codebase,
    // including one where every branch was deleted. So it is asserted against
    // BESPOKE_EXPECTED, which a human wrote down.
    const gone = BESPOKE_EXPECTED.filter((r) => BESPOKE.indexOf(r) === -1);
    assert.deepStrictEqual(gone, [], 'bespoke branch lost: ' + gone.join(', '));
    // And the other direction is a PROMPT, not a failure: a new bespoke branch
    // is ordinary work, and the only thing wrong with it is nobody adding it
    // here -- which is what left law_trust_reconcile reported as an orphan.
    const added = BESPOKE.filter((r) => BESPOKE_EXPECTED.indexOf(r) === -1);
    assert.deepStrictEqual(added, [],
      'new bespoke branch(es) not yet listed in BESPOKE_EXPECTED: ' + added.join(', ')
      + ' -- add them, and check whether they also need a session gate');
  });

  await test('no law_ resource collides with another app', () => {
    registry.resources.forEach((r) => assert.strictEqual(merged.OWNER_BY_RESOURCE[r], 'sairnlaw', r + ' is not owned by sairnlaw'));
    assert.strictEqual(new Set(merged.RESOURCE_NAMES).size, merged.RESOURCE_NAMES.length, 'duplicate resource names platform-wide');
  });

  await test('the SQL grants no delete anywhere', () => {
    assert.ok(!/\bdelete\b/i.test(SQL.replace(/^--.*$/gm, '')), 'a delete grant appeared in the schema');
  });

  // ── the branch itself ───────────────────────────────────────────────────
  await test('a write reaches the store with the right id column and a derived license_hash', async () => {
    let sent = null;
    const handler = loadHandler(async (url, init) => {
      sent = { url: String(url), body: JSON.parse(init.body) };
      return { ok: true, status: 200, json: async () => [{ data: { id: 'TT-1' } }] };
    });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'law_timeentries', payload: { id: 'TT-1', matter_id: 'M-1', hours: 2.5 } }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(sent.body.timeentry_id, 'TT-1');
    assert.strictEqual(sent.body.app_id, 'sairnlaw');
    assert.strictEqual(sent.body.license_hash, LIC_HASH);
    assert.ok(sent.url.indexOf('on_conflict=license_hash,timeentry_id') !== -1, sent.url);
  });

  await test('a read returns the rows and provisioned:true', async () => {
    const handler = loadHandler(async () => ({ ok: true, status: 200, json: async () => [{ data: { id: 'IV-1' } }] }));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_invoices' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.provisioned, true);
    assert.strictEqual(res.body.data[0].id, 'IV-1');
  });

  await test('an UNPROVISIONED read is provisioned:false, not an empty success', async () => {
    // "nothing saved yet" and "this was never migrated" must not collapse into
    // each other -- the client counts the second as a failure and says so.
    const handler = loadHandler(async () => ({ ok: false, status: 404, json: async () => ({}) }));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_picases' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.provisioned, false);
    assert.deepStrictEqual(res.body.data, []);
  });

  await test('an UNPROVISIONED write names the SQL file to run', async () => {
    const handler = loadHandler(async () => ({ ok: false, status: 404, json: async () => ({}) }));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'law_pimedical', payload: { id: 'PM-1' } }), res);
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
    assert.match(res.body.error.message, /sairnlaw_data_extended_schema\.sql/);
  });

  await test('a write with no payload.id is refused before any query', async () => {
    const handler = loadHandler(async () => { throw new Error('fetch must not be called'); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'law_barcerts', payload: { staff_name: 'x' } }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.match(res.body.error.message, /payload\.id is required/);
  });

  await test('every one of the fifteen answers on both verbs', async () => {
    for (const r of Object.keys(HANDLED)) {
      const rh = loadHandler(async () => ({ ok: true, status: 200, json: async () => [] }));
      const rr = mockRes();
      await rh(mockReq({ action: 'read', resource: r }), rr);
      assert.strictEqual(rr.statusCode, 200, r + ' read -> ' + rr.statusCode + ' ' + JSON.stringify(rr.body));
      const wh = loadHandler(async () => ({ ok: true, status: 200, json: async () => [{ data: { id: 'X' } }] }));
      const wr = mockRes();
      await wh(mockReq({ action: 'write', resource: r, payload: { id: 'X' } }), wr);
      assert.strictEqual(wr.statusCode, 200, r + ' write -> ' + wr.statusCode + ' ' + JSON.stringify(wr.body));
    }
  });

  await test('an unknown law_ name is still refused -- the allowlist did not become a wildcard', () => {
    assert.ok(!HANDLED['law_notathing']);
    assert.strictEqual(registry.resources.indexOf('law_notathing'), -1);
  });


  // ── PHASE 1 OF THE SESSION GATE ─────────────────────────────────────────
  await test('NO session -> 401 NO_SESSION on every one of the fifteen, and nothing is queried', async () => {
    for (const r of Object.keys(HANDLED)) {
      const handler = loadHandler(async () => { throw new Error('fetch must not be called without a session'); });
      const res = mockRes();
      await handler(mockReq({ action: 'read', resource: r }, null), res);
      assert.strictEqual(res.statusCode, 401, r + ' -> ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'NO_SESSION');
    }
  });

  await test('the refusal tells the user what to DO, not just that it failed', async () => {
    const handler = loadHandler(async () => { throw new Error('no fetch'); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'law_pimedical', payload: { id: 'X' } }, null), res);
    assert.match(res.body.error.message, /Sign out and sign in again/);
    assert.match(res.body.error.message, /nothing was saved/i);
  });

  await test('a session for ANOTHER app is refused -- Check 28, the cross-app collision', async () => {
    const foreign = signSessionToken({ app: 'sairndental', employee_id: 'emp-x', role: 'owner', license_hash: LIC_HASH });
    const handler = loadHandler(async () => { throw new Error('no fetch'); });
    const res = mockRes();
    const req = { method: 'POST', headers: { authorization: 'Bearer GOOD-KEY', 'x-sd-auth': foreign }, body: { action: 'read', resource: 'law_timeentries' } };
    await handler(req, res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
  });

  await test('EVERY law role is accepted -- this is a session gate, not a role gate', async () => {
    // owner / attorney / paralegal all legitimately work matters, time and
    // documents. Inventing a per-role split here would break the app for the
    // people it is for.
    for (const role of ['owner', 'attorney', 'paralegal']) {
      const handler = loadHandler(async () => ({ ok: true, status: 200, json: async () => [] }));
      const res = mockRes();
      await handler(mockReq({ action: 'read', resource: 'law_matterdocs' }, role), res);
      assert.strictEqual(res.statusCode, 200, role + ' -> ' + res.statusCode + ' ' + JSON.stringify(res.body));
    }
  });

  // ── PHASE 1 BOUNDARY, PARTIALLY FLIPPED (updated 2026-09-16) ──────────────
  // The original arm asserted that all FOUR bespoke resources still work
  // without a session, and carried its own instruction: "WHEN THAT HAPPENS THIS
  // TEST MUST BE INVERTED, not deleted." It happened -- `law_trusttx` was moved
  // into SD_SESSION_GATED the same day, because attorney IOLTA trust money had
  // no session check at all -- and the arm was not inverted, so this suite has
  // been running 18/20 with a red arm that is CORRECT ABOUT THE CODE and wrong
  // about the policy. A red arm nobody can act on is read as noise, and the
  // next genuinely red arm beside it is read the same way.
  //
  // THE FLIP IS PER RESOURCE, NOT WHOLESALE. Only law_trusttx moved. The other
  // three are still live against clients that send no token, and Vercel ships
  // the page and the endpoint together, so flipping them mid-day would fail a
  // staff member with the app already open. Two lists, both explicit, because
  // deriving either from SD_SESSION_GATED would assert that the code equals
  // itself -- the same vacuous shape as deriving BESPOKE above.
  const PHASE1_STILL_OPEN = ['law_clients', 'law_matters', 'law_deadlines'];
  const PHASE2_NOW_GATED = ['law_trusttx'];

  await test('PHASE 1 BOUNDARY: the not-yet-flipped bespoke resources still work '
             + 'WITHOUT a session', async () => {
    for (const r of PHASE1_STILL_OPEN) {
      const handler = loadHandler(async () => ({ ok: true, status: 200, json: async () => [] }));
      const res = mockRes();
      await handler(mockReq({ action: 'read', resource: r }, null), res);
      assert.strictEqual(res.statusCode, 200, r + ' -> ' + res.statusCode + ' ' + JSON.stringify(res.body));
    }
  });

  await test('PHASE 2: law_trusttx is REFUSED without a session -- the inversion '
             + 'the original arm asked for', async () => {
    for (const r of PHASE2_NOW_GATED) {
      const handler = loadHandler(async () => ({ ok: true, status: 200, json: async () => [] }));
      const res = mockRes();
      await handler(mockReq({ action: 'read', resource: r }, null), res);
      // THE REFUSAL IS THE ASSERTION; THE CODE IS PINNED BESIDE IT.
      // SD_SESSION_GATED answers 403 FORBIDDEN, while the generic fifteen
      // answer 401 NO_SESSION for the same condition -- two refusal shapes for
      // "no session" in one endpoint. Noted rather than changed: making them
      // agree is a client-visible contract change and not this suite's to make.
      // Both halves are asserted so neither a 200 nor a silent re-coding passes.
      assert.notStrictEqual(res.statusCode, 200, r + ' answered 200 to a caller '
        + 'with NO session -- the trust-money gate is gone');
      assert.strictEqual(res.statusCode, 403, r + ' -> ' + res.statusCode
        + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    }
  });

  await test('...and the two phase lists PARTITION the bespoke writable four, so '
             + 'a resource cannot fall out of both', () => {
    // The failure this prevents is the quiet one: a resource dropped from the
    // open list without being added to the gated list disappears from the
    // boundary entirely, and the suite goes green having stopped asking.
    const covered = [...PHASE1_STILL_OPEN, ...PHASE2_NOW_GATED].sort();
    const writable = BESPOKE_EXPECTED.filter((r) => r !== 'law_trust_reconcile').sort();
    assert.deepStrictEqual(covered, writable,
      'the phase lists no longer cover exactly the bespoke writable resources');
  });

  await test('the client actually SENDS the token it has always held', () => {
    const HTMLSRC = HTML.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
    assert.ok(HTMLSRC.indexOf("h['X-SD-Auth']=tok") > 0, 'sdnData() does not send the session header');
    assert.ok(HTMLSRC.indexOf('function lawSessionToken()') > 0, 'no token accessor');
    // SCOPED TO THE FUNCTION BODY, and this arm SURVIVED a mutation probe
    // until it was: the whole-file match also hit lawRestoreSession(), which
    // reads the same key, so removing the fallback from lawSessionToken() left
    // the assertion green. sairn-code-scrubber item 16 Shape A -- match the
    // function, not a window of the file that mentions it.
    const at = HTMLSRC.indexOf('function lawSessionToken()');
    assert.ok(at > 0, 'lawSessionToken not found');
    let depth = 0, end = at;
    for (let i = HTMLSRC.indexOf('{', at); i < HTMLSRC.length; i++) {
      if (HTMLSRC[i] === '{') depth++;
      else if (HTMLSRC[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
    }
    const tokenFn = HTMLSRC.slice(at, end);
    // The persisted copy is the fallback: sdnData() can run before
    // lawEnterApp() has set the in-memory mirror on a session restore.
    assert.match(tokenFn, /getItem\('law_session'\)/,
      'the persisted-session fallback was removed -- a restored session would send no token');
    assert.match(tokenFn, /lawSession\.token/, 'the in-memory mirror is no longer read');
    // A missing token must NOT be invented into a header the server would
    // then have to reject as malformed rather than absent.
    assert.match(HTMLSRC, /if\(tok\)h\['X-SD-Auth'\]=tok;/);
  });

  console.log('\n' + passed + ' / ' + total + ' passed');
  if (passed !== total) process.exitCode = 1;
}

main();
