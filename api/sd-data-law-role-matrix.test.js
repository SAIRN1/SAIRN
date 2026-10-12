// api/sd-data-law-role-matrix.test.js
//
// REQUIREMENT: every one of SAIRNlaw's 19 role-gated resources has a rule for
//   every one of its 3 roles; the rules are MONOTONIC (paralegal ⊆ attorney ⊆
//   owner); the trust lock cannot be opened by anything; and the table is
//   actually WIRED into both of api/sd-data.js's two law gates.
//
// Run:  node api/sd-data-law-role-matrix.test.js
//
// ── THE DEFECT THIS HOLDS (hover2 seq 757) ────────────────────────────────
// Exactly ONE role check existed across SAIRNlaw's whole data surface before
// 2026-10-12 and it was on the 20th resource. The other 19 were session-gated
// with no role distinction, so any signed-in role could read and write
// law_picases, law_pimedical and law_bankstatements as freely as a managing
// attorney.
//
// ── WHY THIS FILE IS FOUR DIFFERENT KINDS OF CHECK AND NOT ONE ────────────
// A table like this has four ways to be wrong and only one of them is "a rule
// is missing":
//
//   COMPLETENESS   a law resource with no row, or a role with no column. This
//                  is the one the batch asked for by name, and it is the
//                  cheapest to get wrong again later: a twentieth resource
//                  added to LAW_RESOURCES with no row here would be DENIED by
//                  `decide` (fail-closed, correct) and nobody would know.
//   DERIVED FROM   the resource list is read out of api/sd-data.js ITSELF --
//   THE SOURCE     from SD_SESSION_GATED and LAW_RESOURCES -- and not retyped
//                  here. A list typed into a test agrees with whatever the
//                  test's author believed, which is the staleness this platform
//                  keeps paying for. Retyping it would make COMPLETENESS
//                  vacuous on the day a resource is added.
//   MONOTONICITY   a METAMORPHIC RELATION rather than an expected value: for
//                  every resource and every action, allowed(paralegal) implies
//                  allowed(attorney) implies allowed(owner). It needs no table
//                  of right answers, so it keeps working when the policy
//                  changes -- which an expected-value test does not.
//   WIRED          the table is called from both gates in the handler. A
//                  perfect table nothing reads is the defect with extra steps.
//
// ── AND EACH CHECK IS CONTROL-PAIRED, WHICH IS THE POINT OF SECTIONS C ────
// A checker that has only ever returned clean has, by construction, never
// refused anything. Every structural check below is run TWICE against
// deliberately mutated copies of the table: once where it MUST fire, once
// where it MUST stay silent. The silent half matters as much as the loud one --
// a check that fires on everything is as useless as one that fires on nothing,
// and it is the half that is usually left out.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not test the DATABASE and it does not make a live request. The
// handler arms drive the real dispatcher with a mocked PostgREST, so they
// prove the gate answers 403 before any fetch -- not that the deployed
// endpoint does. It also does not assert the POLICY is right: whether a
// paralegal should read law_pimedical is Michael's decision, transcribed in
// api/_lib/law-roles.js, and a test cannot check a decision.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['law', 'role', 'matrix', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { signSessionToken, ROLES_BY_APP } = require('./_lib/auth');
const lawRoles = require('./_lib/law-roles');

const HASH = 'law-firm-hash';
const APP = 'sairnlaw';
const ACTIONS = ['read', 'write'];

let pass = 0, fail = 0;
const FAILED = [];
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; FAILED.push(name); }
}
function section(t) { console.log('\n' + t); }

// ── THE RESOURCE LIST, DERIVED FROM api/sd-data.js RATHER THAN RETYPED ─────
// Parsed out of the source text, because the alternative is a literal array in
// this file that agrees with the handler only until somebody edits one of them.
// Two shapes to read: the four named individually inside SD_SESSION_GATED, and
// the fifteen keys of the LAW_RESOURCES dict.
//
// IF EITHER PARSE FINDS NOTHING THIS FILE REFUSES rather than reporting a
// clean 0-of-0. A regex over source is exactly the kind of anchor that stops
// matching silently, so the count is asserted before it is used.
function lawResourcesFromSource() {
  const src = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
  const gatedStart = src.indexOf('const SD_SESSION_GATED = {');
  assert.ok(gatedStart > 0, 'could not find SD_SESSION_GATED in api/sd-data.js -- '
    + 'this parse is the test\'s only source for four of the nineteen and a '
    + 'missing anchor must refuse, not report an empty list');
  const gatedEnd = src.indexOf('\n    };', gatedStart);
  assert.ok(gatedEnd > gatedStart, 'could not find the end of SD_SESSION_GATED');
  const gatedBlock = src.slice(gatedStart, gatedEnd);
  const inGated = (gatedBlock.match(/'(law_[a-z_]+)'\s*:/g) || [])
    .map((m) => m.replace(/'/g, '').replace(/\s*:$/, ''));

  const resStart = src.indexOf('const LAW_RESOURCES = {');
  assert.ok(resStart > 0, 'could not find LAW_RESOURCES in api/sd-data.js');
  const resEnd = src.indexOf('\n    };', resStart);
  assert.ok(resEnd > resStart, 'could not find the end of LAW_RESOURCES');
  const inDict = (src.slice(resStart, resEnd).match(/(law_[a-z_]+)\s*:/g) || [])
    .map((m) => m.replace(/\s*:$/, ''));

  const all = inGated.concat(inDict).filter((v, i, a) => a.indexOf(v) === i);
  return { inGated, inDict, all };
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// A PostgREST stand-in that RECORDS every call. The gate arms assert no data
// fetch happened, which is a stronger claim than "the status was 403": a 403
// returned after the row was already read is a leak with a tidy status code.
function pgMock(calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, method: (opts && opts.method) || 'GET' });
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: true }] };
    }
    if (opts && opts.method === 'POST') {
      return { ok: true, status: 200, json: async () => [JSON.parse(opts.body)] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: APP })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function call(resource, action, role, payload) {
  const calls = [];
  const h = loadHandler(pgMock(calls));
  const res = mockRes();
  const body = { action, resource };
  if (action === 'write') body.payload = payload || { id: 'X1' };
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: 'emp-1', role, license_hash: HASH })
    },
    body
  }, res);
  return { res, calls };
}

// ── THE MONOTONICITY RELATION, AS A FUNCTION OVER ANY TABLE ───────────────
// Takes a table rather than reading the module's, so the control pair below can
// hand it a deliberately broken one. Returns the list of violations; an empty
// list is the clean answer.
const ORDER = ['paralegal', 'attorney', 'owner'];
function monotonicityViolations(table, trustLocked) {
  const out = [];
  const allows = (row, role, action) => {
    const g = String((row && row[role]) || '');
    return (action === 'read') ? (g === 'rw' || g === 'r') : (g === 'rw');
  };
  Object.keys(table).forEach((resource) => {
    const row = table[resource];
    ACTIONS.forEach((action) => {
      for (let i = 0; i < ORDER.length - 1; i++) {
        const lower = ORDER[i], higher = ORDER[i + 1];
        if (allows(row, lower, action) && !allows(row, higher, action)) {
          out.push(resource + '/' + action + ': ' + lower + ' allowed but '
                   + higher + ' is not');
        }
      }
    });
    // The lock is part of the relation, not a separate idea: a locked resource
    // allowed to anyone below attorney breaks the ordering AND the lock.
    if (trustLocked && trustLocked[resource]) {
      ACTIONS.forEach((action) => {
        if (allows(row, 'paralegal', action)) {
          out.push(resource + '/' + action + ': TRUST-LOCKED but paralegal is allowed');
        }
      });
    }
  });
  return out;
}

function completenessGaps(table, expectedResources, roles) {
  const out = [];
  expectedResources.forEach((r) => {
    if (!Object.prototype.hasOwnProperty.call(table, r)) {
      out.push(r + ': no row in the table at all');
      return;
    }
    roles.forEach((role) => {
      if (!Object.prototype.hasOwnProperty.call(table[r], role)) {
        out.push(r + ': no rule for role ' + role);
      }
    });
  });
  return out;
}

(async function () {
  console.log('SAIRNlaw role matrix -- 19 resources x 3 roles (hover2 seq 757)');

  const SRC = lawResourcesFromSource();
  const ROLES = (ROLES_BY_APP[APP] || []).slice();

  section('A. THE POPULATION, DERIVED FROM THE HANDLER AND NOT FROM THIS FILE');

  await test('api/sd-data.js yields 4 law resources from SD_SESSION_GATED and '
    + '15 from LAW_RESOURCES -- 19 distinct', () => {
      assert.strictEqual(SRC.inGated.length, 4,
        'SD_SESSION_GATED parse found ' + SRC.inGated.length + ': '
        + JSON.stringify(SRC.inGated));
      assert.strictEqual(SRC.inDict.length, 15,
        'LAW_RESOURCES parse found ' + SRC.inDict.length + ': '
        + JSON.stringify(SRC.inDict));
      assert.strictEqual(SRC.all.length, 19,
        'distinct total is ' + SRC.all.length);
    });

  await test('...and ROLES_BY_APP.sairnlaw is exactly owner / attorney / '
    + 'paralegal, so the 3 in "19 x 3" is derived too', () => {
      assert.deepStrictEqual(ROLES.slice().sort(),
        ['attorney', 'owner', 'paralegal'],
        'ROLES_BY_APP.' + APP + ' is ' + JSON.stringify(ROLES));
    });

  section('B. COMPLETENESS -- the check the batch asked for by name');

  await test('every one of the 19 has a row, and every row has a rule for all '
    + '3 roles. FAILS IF ANY LAW RESOURCE HAS NO RULE', () => {
      const gaps = completenessGaps(lawRoles.LAW_ROLE_MATRIX, SRC.all, ROLES);
      assert.deepStrictEqual(gaps, [],
        gaps.length + ' gap(s):\n       ' + gaps.join('\n       '));
    });

  await test('...and the table carries NO resource the handler does not gate, '
    + 'so it cannot drift into fiction', () => {
      const extra = lawRoles.resources().filter((r) => SRC.all.indexOf(r) === -1);
      assert.deepStrictEqual(extra, [],
        'the table names ' + JSON.stringify(extra) + ', which api/sd-data.js '
        + 'does not gate. A rule for a resource that does not exist reads as '
        + 'coverage and is not.');
    });

  await test('...and law_trust_reconcile is NOT in the table -- it has its own '
    + 'owner-only gate and is excluded on purpose', () => {
      assert.ok(lawRoles.LAW_EXCLUDED.indexOf('law_trust_reconcile') !== -1,
        'law_trust_reconcile is not declared as excluded, so a reader cannot '
        + 'tell a deliberate exclusion from an omission');
      assert.strictEqual(lawRoles.decide('law_trust_reconcile', 'owner', 'read'),
        lawRoles.NOT_LAW,
        'the excluded resource must return NOT_LAW so this table does not '
        + 'second-guess the gate that already exists on it');
    });

  section('C1. CONTROL PAIR FOR COMPLETENESS -- plant a gap, then plant clean');

  await test('PLANTED: a resource with no row is REPORTED', () => {
    const gaps = completenessGaps(lawRoles.LAW_ROLE_MATRIX,
      SRC.all.concat(['law_zz_planted']), ROLES);
    assert.ok(gaps.some((g) => /law_zz_planted: no row/.test(g)),
      'the completeness check did not report a resource with no row: '
      + JSON.stringify(gaps));
  });

  await test('PLANTED: a row with a MISSING ROLE is REPORTED -- the half a '
    + '"does the key exist" check misses', () => {
      const broken = JSON.parse(JSON.stringify(lawRoles.LAW_ROLE_MATRIX));
      delete broken.law_matters.paralegal;
      const gaps = completenessGaps(broken, SRC.all, ROLES);
      assert.ok(gaps.some((g) => /law_matters: no rule for role paralegal/.test(g)),
        'a row missing one role was not reported: ' + JSON.stringify(gaps));
    });

  await test('CLEAN: the real table reports nothing -- so the two arms above '
    + 'are not firing on everything', () => {
      assert.deepStrictEqual(
        completenessGaps(lawRoles.LAW_ROLE_MATRIX, SRC.all, ROLES), []);
    });

  section('D. MONOTONICITY -- the metamorphic relation (batch item 3)');

  await test('paralegal implies attorney implies owner, for every resource and '
    + 'every action', () => {
      const v = monotonicityViolations(lawRoles.LAW_ROLE_MATRIX,
                                      lawRoles.LAW_TRUST_LOCKED);
      assert.deepStrictEqual(v, [],
        v.length + ' violation(s):\n       ' + v.join('\n       '));
    });

  await test('...and the relation is checked through `decide` as well as the '
    + 'raw table, so the FUNCTION cannot disagree with the data', () => {
      const bad = [];
      lawRoles.resources().forEach((r) => ACTIONS.forEach((a) => {
        const p = lawRoles.decide(r, 'paralegal', a) === lawRoles.ALLOW;
        const t = lawRoles.decide(r, 'attorney', a) === lawRoles.ALLOW;
        const o = lawRoles.decide(r, 'owner', a) === lawRoles.ALLOW;
        if (p && !t) bad.push(r + '/' + a + ': paralegal but not attorney');
        if (t && !o) bad.push(r + '/' + a + ': attorney but not owner');
      }));
      assert.deepStrictEqual(bad, [], bad.join('; '));
    });

  section('D1. CONTROL PAIR FOR MONOTONICITY -- plant a violation, then clean');

  await test('PLANTED: paralegal granted where attorney is not -- FIRES', () => {
    const broken = JSON.parse(JSON.stringify(lawRoles.LAW_ROLE_MATRIX));
    broken.law_invoices.attorney = '';
    const v = monotonicityViolations(broken, lawRoles.LAW_TRUST_LOCKED);
    assert.ok(v.some((x) => /law_invoices\/read: paralegal allowed but attorney is not/.test(x)),
      'the relation did not fire on a planted inversion: ' + JSON.stringify(v));
  });

  await test('PLANTED: attorney granted where owner is not -- FIRES', () => {
    const broken = JSON.parse(JSON.stringify(lawRoles.LAW_ROLE_MATRIX));
    broken.law_matters.owner = 'r';
    const v = monotonicityViolations(broken, lawRoles.LAW_TRUST_LOCKED);
    assert.ok(v.some((x) => /law_matters\/write: attorney allowed but owner is not/.test(x)),
      'the relation did not fire on a write-level inversion: ' + JSON.stringify(v));
  });

  await test('PLANTED: a TRUST-LOCKED resource opened to paralegal -- FIRES, '
    + 'and this is the one a pure ordering check would have MISSED', () => {
      const broken = JSON.parse(JSON.stringify(lawRoles.LAW_ROLE_MATRIX));
      broken.law_trusttx.paralegal = 'r';
      const v = monotonicityViolations(broken, lawRoles.LAW_TRUST_LOCKED);
      assert.ok(v.some((x) => /law_trusttx\/read: TRUST-LOCKED but paralegal is allowed/.test(x)),
        'the lock arm did not fire: ' + JSON.stringify(v));
      // The point of this arm: owner and attorney still have rw, so the
      // ORDERING is intact and a monotonicity-only check reports clean.
      const orderingOnly = monotonicityViolations(broken, null);
      assert.deepStrictEqual(orderingOnly, [],
        'ordering alone should NOT have caught this -- if it did, this arm is '
        + 'not demonstrating what it claims: ' + JSON.stringify(orderingOnly));
    });

  await test('CLEAN: the real table reports no violation -- the silent half of '
    + 'the pair', () => {
      assert.deepStrictEqual(
        monotonicityViolations(lawRoles.LAW_ROLE_MATRIX, lawRoles.LAW_TRUST_LOCKED), []);
    });

  section('E. THE TRUST LOCK HOLDS AGAINST A TABLE EDIT, not just against the '
    + 'table');

  await test('`decide` still DENIES a trust resource to paralegal even when the '
    + 'TABLE is edited to allow it -- the lock is a second structure for '
    + 'exactly this reason', () => {
      const real = lawRoles.LAW_ROLE_MATRIX.law_trusttx.paralegal;
      assert.strictEqual(real, '', 'fixture assumption changed: the real table '
        + 'grants paralegal ' + JSON.stringify(real) + ' on law_trusttx');
      // Mutating the frozen module table is refused, which is itself the
      // guarantee: an override layer cannot reach in and change it.
      let mutated = false;
      try {
        lawRoles.LAW_ROLE_MATRIX.law_trusttx.paralegal = 'rw';
        mutated = (lawRoles.LAW_ROLE_MATRIX.law_trusttx.paralegal === 'rw');
      } catch (e) { mutated = false; }
      assert.strictEqual(lawRoles.decide('law_trusttx', 'paralegal', 'read'),
        lawRoles.DENY,
        'law_trusttx/read was ALLOWED to paralegal after a table mutation '
        + '(mutation took effect: ' + mutated + '). The lock must survive this.');
      assert.strictEqual(lawRoles.decide('law_bankstatements', 'paralegal', 'write'),
        lawRoles.DENY, 'law_bankstatements/write was allowed to paralegal');
    });

  await test('...and a FOURTH role nobody added a column for gets NOTHING, '
    + 'rather than inheriting', () => {
      lawRoles.resources().forEach((r) => ACTIONS.forEach((a) => {
        assert.strictEqual(lawRoles.decide(r, 'frontdesk', a), lawRoles.DENY,
          r + '/' + a + ' allowed an undeclared role');
      }));
    });

  await test('...and a NEW law_ resource nobody put in the table is DENIED, '
    + 'not NOT_LAW -- fail closed on the thing most likely to happen next', () => {
      assert.strictEqual(lawRoles.decide('law_newthing', 'owner', 'read'),
        lawRoles.DENY);
    });

  await test('...and a NON-law resource is NOT_LAW, so this table cannot '
    + 'approve or refuse another app\'s resource', () => {
      ['sen_caregivers', 'sf_ledger', 'quotes', 'memory'].forEach((r) => {
        assert.strictEqual(lawRoles.decide(r, 'owner', 'read'), lawRoles.NOT_LAW, r);
      });
    });

  await test('...and a write-class verb that is not "write" is treated as a '
    + 'WRITE, so a future verb cannot ride in on a read grant', () => {
      // law_pimedical is paralegal READ-only. soft_delete must not be allowed.
      assert.strictEqual(lawRoles.decide('law_pimedical', 'paralegal', 'read'),
        lawRoles.ALLOW);
      assert.strictEqual(lawRoles.decide('law_pimedical', 'paralegal', 'soft_delete'),
        lawRoles.DENY);
      assert.strictEqual(lawRoles.decide('law_pimedical', 'paralegal', 'export'),
        lawRoles.DENY);
    });

  section('F. WIRED -- both of the handler\'s two law gates call the table');

  await test('[SD_SESSION_GATED path] a paralegal reading law_trusttx gets 403 '
    + 'AND no row is fetched', async () => {
      const { res, calls } = await call('law_trusttx', 'read', 'paralegal');
      assert.strictEqual(res.statusCode, 403,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.ok(/trust/i.test(res.body.error.message),
        'the refusal does not mention trust: ' + res.body.error.message);
      assert.ok(!calls.some((c) => /law_trusttx\?/.test(c.url)),
        'the row was fetched before the refusal -- a 403 after the read is a '
        + 'leak with a tidy status code. Calls: '
        + JSON.stringify(calls.map((c) => c.url)));
    });

  await test('[LAW_RESOURCES path] a paralegal WRITING law_pimedical gets 403 '
    + 'AND nothing is POSTed', async () => {
      const { res, calls } = await call('law_pimedical', 'write', 'paralegal');
      assert.strictEqual(res.statusCode, 403,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.ok(!calls.some((c) => c.method === 'POST' && /law_pimedical/.test(c.url)),
        'a refused write still POSTed: ' + JSON.stringify(calls));
    });

  await test('[LAW_RESOURCES path] ...and the SAME paralegal READING '
    + 'law_pimedical is NOT refused -- so the arm above is a role gate and not '
    + 'a dead branch', async () => {
      const { res } = await call('law_pimedical', 'read', 'paralegal');
      assert.notStrictEqual(res.statusCode, 403,
        'a read-only grant was refused on read: ' + JSON.stringify(res.body));
    });

  await test('[LAW_RESOURCES path] a paralegal writing law_matterdocs is NOT '
    + 'refused -- the read+write category really is writable', async () => {
      const { res } = await call('law_matterdocs', 'write', 'paralegal');
      assert.notStrictEqual(res.statusCode, 403,
        'a read+write grant was refused on write: ' + JSON.stringify(res.body));
    });

  await test('NEGATIVE HALF: an ATTORNEY is refused NONE of the 19 on either '
    + 'action -- so the gate is not simply denying everything', async () => {
      const refused = [];
      for (const r of lawRoles.resources()) {
        for (const a of ACTIONS) {
          const { res } = await call(r, a, 'attorney');
          if (res.statusCode === 403) refused.push(r + '/' + a + ' -> '
            + JSON.stringify(res.body && res.body.error && res.body.error.message));
        }
      }
      assert.deepStrictEqual(refused, [],
        refused.length + ' attorney call(s) refused:\n       ' + refused.join('\n       '));
    });

  await test('...and a NON-law resource is never refused BY THE LAW TABLE, so '
    + 'adding the check did not gate the platform', async () => {
      // ASSERTS ON THE REFUSAL REASON, NOT ON THE STATUS, AND THE FIRST
      // VERSION OF THIS ARM DID NOT -- which is why it failed for the wrong
      // reason. `memory` resolves its expected app from the CALLER
      // (gateApp = memApp), so a token signed for 'sairnlaw' fails
      // verifySessionToken and the PRE-EXISTING session gate answers 403 "A
      // valid employee session is required". That is a correct refusal by a
      // gate this batch did not touch, and reading it as "the law table
      // refused a non-law resource" is the could-not-tell-two-refusals-apart
      // mistake this repo already records. Two 403s, two causes; the arm must
      // name which one it is about.
      for (const r of ['memory', 'profile', 'slabs']) {
        const { res } = await call(r, 'read', 'owner');
        const msg = (res.body && res.body.error && res.body.error.message) || '';
        assert.ok(!/does not have access to this record|Client trust records/.test(msg),
          r + ' was refused by the LAW table: ' + JSON.stringify(res.body)
          + '. `decide` must return NOT_LAW for every non-law resource, and a '
          + 'NOT_LAW must never reach the 403.');
      }
      // And the positive half, proved at the function rather than through a
      // handler whose own session gate can mask it: NOT_LAW, explicitly.
      ['memory', 'profile', 'slabs', 'sf_ledger', 'quotes'].forEach((r) => {
        assert.strictEqual(lawRoles.decide(r, 'owner', 'read'), lawRoles.NOT_LAW, r);
      });
    });

  if (FAILED.length) {
    console.log('\n' + FAILED.length + ' ARM(S) FAILED:');
    FAILED.forEach((f) => console.log('  - ' + f));
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
