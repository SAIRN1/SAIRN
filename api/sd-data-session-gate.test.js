// api/sd-data-session-gate.test.js
// REQUIREMENT: slabs, profile and memory require an employee SESSION and not
//   the licence key alone -- the key is a bearer credential StoneDesk prints
//   into a link the shop is told to send customers, and it read the whole slab
//   inventory, the business profile and the shop's AI memories
//
// Plain node:assert tests. Run: node api/sd-data-session-gate.test.js
//
// slabs, profile and memory predate per-employee sessions and were reachable
// with the licence key alone. docs/superpowers/specs/2026-09-02-licence-key-exposure-audit.md
// proved what that meant: the key is a bearer credential, StoneDesk printed it
// into a link the shop is told to send customers, and anyone holding it could
// read the whole slab inventory, the business profile (company, EIN, revenue
// range, owner) and the shop's AI memories -- and WRITE slabs.
//
// `profile` READ was held open for exactly one commit while SAIRNcode migrated
// off it, and is now gated too. The assertion that used to protect that hole is
// inverted below rather than deleted, so the file still records that the
// exception existed and that it closed.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(action, resource, payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SD-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: action, resource: resource, payload: payload || {} }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function loadHandler(opts) {
  opts = opts || {};
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () { return opts.noSession ? null : { employee_id: 'emp-1', role: 'sales' }; }
    })
  };
  // Any network call at all on a refused request is itself a defect.
  global.fetch = async function (url, init) {
    calls.push({ url: String(url), method: (init && init.method) || 'GET' });
    if (opts.refuseNetwork) throw new Error('the gate let a refused request reach the database');
    const m = (init && init.method) || 'GET';
    if (m === 'GET') return { ok: true, status: 200, json: async () => [] };
    return { ok: true, status: 201, json: async () => [{ data: {} }] };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

// The exposure, as the audit measured it, expressed as a table.
const GATED = [
  ['slabs', 'read'],
  ['slabs', 'write'],
  ['slabs', 'reserve'],
  ['profile', 'read'],
  ['profile', 'write'],
  ['memory', 'read'],
  ['memory', 'write']
];

async function main() {
  console.log('api/sd-data.js -- the licence key alone is no longer enough for slabs/profile/memory');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  for (const [resource, action] of GATED) {
    await test(resource + '/' + action + ' -> 403 with a licence key and NO session', async () => {
      const { handler, calls } = loadHandler({ noSession: true, refuseNetwork: true });
      const res = mockRes();
      const payload = resource === 'slabs' ? { id: 'S1', reservedFor: 'X' } : { x: 1 };
      await handler(mockReq(action, resource, payload), res);
      assert.strictEqual(res.statusCode, 403, 'status was ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
      assert.match(res.body.error.message, /sign in first/i);
      assert.strictEqual(calls.length, 0, 'a refused request still hit the database');
    });
  }

  for (const [resource, action] of GATED) {
    await test(resource + '/' + action + ' still works WITH a session', async () => {
      const { handler } = loadHandler({});
      const res = mockRes();
      const payload = resource === 'slabs' ? { id: 'S1', reservedFor: 'X' } : { x: 1 };
      await handler(mockReq(action, resource, payload), res);
      assert.notStrictEqual(res.statusCode, 403,
        'the gate refuses a legitimate signed-in caller');
    });
  }

  await test('THE HOLE IS CLOSED: no resource in the table is exempt any more', async () => {
    // This assertion used to say the opposite. profile/read was open only
    // while SAIRNcode probed it for licence validity without a session;
    // SAIRNcode now calls api/sc-auth.js check_license, verified live. Kept
    // inverted rather than deleted so the file records that the exception
    // existed, and would fail loudly if anyone re-opened it.
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\};/);
    assert.ok(!/'profile':\s*\['write'\]/.test(m[0]),
      'profile/read is exempt again -- if that is deliberate, say why in the table');
  });

  await test('the gate is a table, not scattered checks -- and the pair count is COUNTED, not claimed', () => {
    // This assertion used to be titled "lists exactly seven pairs" and counted
    // nothing -- it matched three entries and stopped. Adding 'locations' on
    // 2026-09-03 took the table to nine pairs and the title stayed green while
    // becoming false, which is the whole failure mode a count is supposed to
    // catch. It is now derived from the table rather than asserted about it.
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\n    \};/);
    assert.ok(m, 'the gate table is gone');
    assert.match(m[0], /'slabs':\s*\['read', 'write', 'reserve'\]/);
    assert.match(m[0], /'profile':\s*\['read', 'write'\]/);
    assert.match(m[0], /'memory':\s*\['read', 'write'\]/);
    // Yards, 2026-09-03. The GAP 7 branch described itself as carrying "the
    // same licence-scoped gate as 'slabs'" -- and slabs is in THIS table, so
    // locations had no session requirement at all and a licence key alone
    // could rename or close a yard.
    assert.match(m[0], /'locations':\s*\['read', 'write'\]/);
    // law_trusttx, 2026-09-16. ATTORNEY IOLTA CLIENT TRUST MONEY -- the one
    // figure a bar association audits -- and it had NO session gate at all.
    // Both branches dispatched on the licence hash alone, and the licence key
    // is shipped to the browser and readable by anyone who can open the app.
    // Not a session that had gone stale: no session check existed. The adjacent
    // `law_trust_reconcile` reads THE SAME TABLE forty lines below and verifies
    // a session AND a role, which is why it survived three reads of the file.
    //
    // THIS ARM WAS RED ON origin/main FOR THE RIGHT REASON AND NOBODY FINISHED
    // IT (fixed 2026-09-16). The count said 9 and the table held 11, so the arm
    // did exactly what it exists to do -- "add the new resource to this test
    // and say why it is gated" -- and the answer was never written down. A
    // suite left red by its own correct finding is a suite whose next finding
    // is read as noise.
    assert.match(m[0], /'law_trusttx':\s*\['read', 'write'\]/);
    // PHASE 2 COMPLETED, 2026-09-22. The last three SAIRNlaw resources that
    // were the licence key alone. Measured before the change: all six pairs
    // answered 200 with no token, against a control where law_invoices/read
    // answered 401. Driven in api/sd-data-law-phase2-session.test.js, which
    // this file's coverage arm below names -- adding them here without that
    // file fails that arm, which is how this was caught rather than shipped.
    assert.match(m[0], /'law_clients':\s*\['read', 'write'\]/);
    assert.match(m[0], /'law_matters':\s*\['read', 'write'\]/);
    assert.match(m[0], /'law_deadlines':\s*\['read', 'write'\]/);
    // SAIRNfreedom's three Tier A resources, 2026-09-21. Same shape as
    // law_trusttx above and found the same way: SF_RESOURCES' read and write
    // branches carried NO session check of any kind, so the licence key --
    // shipped to the browser and readable by anyone who can open the app --
    // was the whole authorisation on the general ledger, the chart of accounts
    // and vendor pricing. SAIRNfreedom was not swept with law_trusttx on
    // 2026-09-16. Gated LAST of five pieces, deliberately: until sf-auth.js,
    // the ROLES_BY_APP/AUTH_TABLE_BY_APP entries, the schema and the client's
    // X-SD-Auth header existed, arming this line would have 403'd every real
    // call with no way to clear it.
    assert.match(m[0], /'sf_accounts':\s*\['read', 'write'\]/);
    assert.match(m[0], /'sf_ledger':\s*\['read', 'write'\]/);
    assert.match(m[0], /'sf_vendor_prices':\s*\['read', 'write'\]/);
    const pairs = (m[0].match(/'(read|write|reserve)'/g) || []).length;
    // 17 -> 23 on 2026-09-22: phase 2's final three, six pairs. WHY THEY ARE
    // GATED, which is what this tripwire asks for: law_clients, law_matters and
    // law_deadlines were the last three resources in SAIRNlaw authorised by the
    // licence key alone -- a key shipped to the browser and readable by anyone
    // who can open the app. Measured before the change: all six pairs answered
    // 200 with no token, against a control where law_invoices/read answered 401.
    // law_matters names the client and the matter.
    assert.strictEqual(pairs, 23,
      'the gate table changed size to ' + pairs + ' pairs -- add the new resource to this test and say why it is gated');
  });

  // ── EVERY PAIR IN THE TABLE IS DRIVEN SOMEWHERE, AND IT IS SAID WHERE ─────
  // Added 2026-09-16. The count arm above proves the table has not changed
  // size; it says nothing about whether anything EXERCISES the entries. GATED
  // drives the StoneDesk-session pairs; everything needing another app's session
  // is driven in its own suite and named in `drivenElsewhere` below, because
  // this file mints StoneDesk tokens and cannot mint a SAIRNlaw or SAIRNfreedom
  // one.
  //
  // THE PROSE HERE USED TO SAY "7 of the 11 pairs" AND THE TABLE HELD 17 WHEN
  // THAT WAS READ (2026-09-22) -- a hand-maintained count in a comment, stale
  // and invisible because nothing compares prose to the table. Replaced with a
  // description rather than a number: the arm below DERIVES both sides and names
  // what is missing, so a count in this comment adds nothing but a second thing
  // to get wrong.
  //
  // The failure this prevents is the quiet one: a resource added to the table,
  // counted by the arm above, and driven by nothing anywhere -- which looks
  // identical to a covered resource from inside this file.
  await test('every pair in the gate table is DRIVEN -- here, or in a suite '
    + 'this arm names', () => {
      const fs = require('fs');
      const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
      const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\n    \};/);
      assert.ok(m, 'the gate table is gone');
      const inTable = (m[0].match(/'([a-z_]+)':\s*\[/g) || [])
        .map((x) => x.replace(/'|:|\s|\[/g, '')).sort();
      const drivenHere = [...new Set(GATED.map((p) => p[0]))];
      // Stated by hand, with the file that does the driving. A derived answer
      // here would be this arm asserting its own premise.
      const drivenElsewhere = {
        locations: 'api/sd-data-locations.test.js',
        law_trusttx: 'api/sd-data-law-trusttx-session.test.js',
        // Phase 2's final three, driven together in one suite for the same
        // reason law_trusttx has its own: they need a SAIRNlaw session and
        // this file mints StoneDesk ones. That suite drives the whole chain --
        // no session refused on read AND write with ZERO database calls, all
        // three real roles still reading, a write still succeeding so the gate
        // is a split rather than a lockout, a session from another SAIRN app
        // refused, a deactivated credential refused on a token that still
        // verifies, and both table entries asserted on the source.
        law_clients: 'api/sd-data-law-phase2-session.test.js',
        law_matters: 'api/sd-data-law-phase2-session.test.js',
        law_deadlines: 'api/sd-data-law-phase2-session.test.js',
        // SAIRNfreedom's three, driven in their own suite for the same reason
        // law_trusttx is: they need a SAIRNfreedom session, and this file mints
        // StoneDesk ones. That suite drives the whole chain -- no session
        // refused, a real session minted by api/sf-auth.js accepted, a write
        // gated as well as a read, a deactivated employee refused on a token
        // that is still cryptographically valid, and a token from another SAIRN
        // app refused.
        sf_accounts: 'api/sf-session-gate.test.js',
        sf_ledger: 'api/sf-session-gate.test.js',
        sf_vendor_prices: 'api/sf-session-gate.test.js'
      };
      const covered = [...drivenHere, ...Object.keys(drivenElsewhere)].sort();
      assert.deepStrictEqual(inTable, covered,
        'a gated resource is driven by nothing: ' +
        inTable.filter((r) => covered.indexOf(r) === -1).join(', ') +
        ' -- add arms here, or name the suite that drives it');
      Object.keys(drivenElsewhere).forEach((r) => {
        const f = require.resolve('./' + drivenElsewhere[r].replace('api/', ''));
        assert.ok(fs.existsSync(f), 'the suite named for ' + r + ' does not exist: '
          + drivenElsewhere[r]);
        assert.ok(fs.readFileSync(f, 'utf8').indexOf(r) > -1,
          drivenElsewhere[r] + ' does not mention ' + r + ' at all');
      });
    });

  await test('an ungated resource is untouched by the table', async () => {
    const { handler } = loadHandler({ noSession: true });
    const res = mockRes();
    await handler(mockReq('read', 'employees', {}), res);
    // employees has its own, older gate -- what matters is that this one did
    // not start refusing things it was never asked to.
    assert.ok(res.body && res.body.error, 'expected employees to keep its own refusal');
    assert.ok(!/sign in first/i.test(res.body.error.message || ''),
      'the new gate swallowed a resource that has its own');
  });

  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' SESSION-GATE ASSERTIONS PASS'));
}

main();
