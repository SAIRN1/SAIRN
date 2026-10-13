// ─────────────────────────────────────────────────────────────────────────────
// SAIRNfreedom — THE DRIVEN ROLE MATRIX. Routed to cody by hank,
// docs/2026-10-13-hank-b6-routing.md item 3.
//
// WHAT api/sd-data-sf-role-matrix.test.js ALREADY PROVES, and what this is not
// repeating: that the policy in api/_lib/sf-roles.js is complete (36 rows),
// locked, mirrored and wired. It drives no session and says so in its own
// closing lines.
//
// WHAT THIS FILE PROVES: that a REAL SIGNED SESSION for each of the ten
// SAIRNfreedom roles actually gets the answer the table says it should, from
// the handler, over every gated resource and both verbs. That is the WIRING and
// the REACHABILITY of the call site, resource by resource — the thing a locked
// table cannot tell you, because a table is still correct when nobody reads it.
//
// WHAT IT CANNOT PROVE, said here rather than discovered later: the handler
// calls `sfRoles.decide` and so does this file's EXPECTATION, so agreement does
// NOT prove the policy is RIGHT. It proves the policy is REACHED. If the table
// itself is wrong, every arm here passes and the b6 locked matrix test plus
// Michael's reading of the VFW Manual of Procedure are what catch it. The
// division is deliberate: expectation from the TABLE, observation from the
// HANDLER, never both from the table — hank's instruction, and the reason this
// file never asserts a transcribed verdict.
//
// THE DENOMINATOR IS DISCLOSED AND IS NOT 720. Ten roles × 36 resources × 2
// verbs = 720 cells, but only 27 of the 36 resources enter SD_SESSION_GATED, so
// only 540 cells can be driven through a role gate AT ALL. The other 180 are
// LICENCE-KEY-ONLY: there is no session, so there is no role to decide against,
// and an arm asserting a refusal there would be asserting a gate that does not
// exist. Those nine resources are NAMED and their 180 cells are reported as
// NOT-DRIVEN rather than folded into a pass count. 540 + 180 = 720, and the
// arithmetic is printed so neither number can be quoted without the other.
// ─────────────────────────────────────────────────────────────────────────────

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sf', 'driven', 'matrix', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const API = path.join(__dirname, '..', 'api');
const { signSessionToken, ROLES_BY_APP } = require(path.join(API, '_lib', 'auth'));
const sfRoles = require(path.join(API, '_lib', 'sf-roles'));

const HASH = 'sf-post-hash';
const APP = 'sairnfreedom';
const ACTIONS = ['read', 'write'];

let pass = 0, fail = 0;
const FAILED = [];
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; FAILED.push(name); }
}
function section(t) { console.log('\n' + t); }

// ── THE GATED SET, DERIVED FROM api/sd-data.js RATHER THAN RETYPED ──────────
// A literal list in this file would agree with the handler only until somebody
// edits one of them, and the disagreement is the whole defect class. IF THE
// PARSE FINDS NOTHING THIS FILE REFUSES rather than reporting a clean 0 of 0 —
// a regex over source is exactly the anchor that stops matching in silence.
function gatedSfFromSource() {
  const src = fs.readFileSync(path.join(API, 'sd-data.js'), 'utf8');
  const start = src.indexOf('const SD_SESSION_GATED = {');
  assert.ok(start > 0, 'could not find SD_SESSION_GATED in api/sd-data.js -- this '
    + 'parse is this file\'s only source for the gated set and a silent miss here '
    + 'would report every resource as ungated, which reads as "no policy" rather '
    + 'than as a broken test');
  const end = src.indexOf('\n    };', start);
  assert.ok(end > start, 'could not find the end of SD_SESSION_GATED');
  const found = (src.slice(start, end).match(/'(sf_[a-z_]+)'/g) || [])
    .map((m) => m.replace(/'/g, ''))
    .filter((v, i, a) => a.indexOf(v) === i);
  assert.ok(found.length >= 20, 'SD_SESSION_GATED parse found only ' + found.length
    + ' sf_ resources; it held 27 on 2026-10-13. Either the dict moved or the '
    + 'anchor rotted -- both are findings, neither is a pass.');
  return found;
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// A PostgREST stand-in that RECORDS every call. The DENY arms assert no data
// fetch happened, which is a stronger claim than "the status was 403": a 403
// returned after the row was already read is a leak with a tidy status code.
function pgMock(calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, method: (opts && opts.method) || 'GET' });
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: 'emp-1', role: 'post.govern', active: true }] };
    }
    if (opts && opts.method === 'POST') {
      return { ok: true, status: 200, json: async () => [JSON.parse(opts.body)] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

function loadHandler(fetchImpl) {
  const licPath = require.resolve(path.join(API, '_lib', 'license'));
  delete require.cache[licPath];
  require.cache[licPath] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: APP })
    }
  };
  global.fetch = fetchImpl;
  const hPath = require.resolve(path.join(API, 'sd-data.js'));
  delete require.cache[hPath];
  return require(hPath);
}

async function call(resource, action, role) {
  const calls = [];
  const h = loadHandler(pgMock(calls));
  const res = mockRes();
  const body = { action, resource };
  if (action === 'write') body.payload = { id: 'X1' };
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

// THE ONE OBSERVATION PREDICATE, used by every arm and by the controls.
// "Was this caller refused BY THE ROLE GATE" -- not "was there a 403", because
// a 403 from the session gate or a trapdoor guard is a different refusal and
// counting it would make an unwired resource look policed.
function refusedByRoleGate(res, resource, role) {
  return res.statusCode === 403
    && !!res.body && !!res.body.error
    && res.body.error.code === 'FORBIDDEN'
    && res.body.error.message === sfRoles.denyMessage(resource, role);
}

(async function main() {
  const ROLES = ROLES_BY_APP[APP];
  assert.ok(Array.isArray(ROLES) && ROLES.length >= 10,
    'ROLES_BY_APP.sairnfreedom must be the role source; got ' + JSON.stringify(ROLES));
  const TABLE = sfRoles.resources();
  const GATED = gatedSfFromSource().filter((r) => TABLE.indexOf(r) !== -1);
  const UNGATED = TABLE.filter((r) => GATED.indexOf(r) === -1);

  section('0. THE DENOMINATOR, PRINTED BEFORE ANY ARM RUNS');
  console.log('  roles                    ' + ROLES.length + '  ' + ROLES.join(' '));
  console.log('  resources in the table   ' + TABLE.length);
  console.log('  of those SESSION-GATED   ' + GATED.length + '   -> ' + (ROLES.length * GATED.length * 2) + ' DRIVEN cells');
  console.log('  LICENCE-KEY-ONLY         ' + UNGATED.length + '   -> ' + (ROLES.length * UNGATED.length * 2) + ' cells that CANNOT be driven');
  console.log('  the nine, named          ' + UNGATED.join(' '));
  console.log('  total                    ' + (ROLES.length * TABLE.length * 2) + ' cells');

  // ── THE CONTROL PAIR FIRST. A harness that cannot fail proves nothing, and
  // running it LAST means a broken harness has already printed 540 passes.
  section('1. CONTROL PAIR -- the comparison must be able to FAIL (run FIRST)');
  await test('1a. a cell the table DENIES is observed as refused, and asserting the OPPOSITE fails', async () => {
    let cell = null;
    for (const r of GATED) for (const role of ROLES) for (const a of ACTIONS) {
      if (sfRoles.decide(r, role, a) === sfRoles.DENY) { cell = { r, role, a }; break; }
      if (cell) break;
    }
    assert.ok(cell, 'no DENY cell exists in the gated set -- a role matrix that '
      + 'denies nobody is the finding, not a passing control');
    const { res } = await call(cell.r, cell.a, cell.role);
    const observed = refusedByRoleGate(res, cell.r, cell.role);
    assert.strictEqual(observed, true, 'the chosen DENY cell ' + cell.r + '/'
      + cell.a + '/' + cell.role + ' was NOT refused: ' + JSON.stringify(res.body));
    assert.throws(() => assert.strictEqual(observed, false),
      'the inverted assertion did NOT throw, so this harness cannot fail and '
      + 'every arm below is decoration');
  });
  await test('1b. a cell the table ALLOWS is observed as NOT refused, and asserting the OPPOSITE fails', async () => {
    let cell = null;
    for (const r of GATED) for (const role of ROLES) for (const a of ACTIONS) {
      if (sfRoles.decide(r, role, a) === sfRoles.ALLOW) { cell = { r, role, a }; break; }
      if (cell) break;
    }
    assert.ok(cell, 'no ALLOW cell exists in the gated set -- a gate that refuses '
      + 'everybody passes every denied arm, which is why this control exists');
    const { res } = await call(cell.r, cell.a, cell.role);
    const observed = refusedByRoleGate(res, cell.r, cell.role);
    assert.strictEqual(observed, false, 'the chosen ALLOW cell ' + cell.r + '/'
      + cell.a + '/' + cell.role + ' WAS refused by the role gate: '
      + JSON.stringify(res.body));
    assert.throws(() => assert.strictEqual(observed, true),
      'the inverted assertion did NOT throw');
  });

  // ── THE DRIVEN SWEEP. One arm per role × verb so the output stays readable;
  // every cell inside is checked and every failing cell is NAMED, so the arm
  // count is 20 and the CELL count is 540 and both are printed.
  section('2. THE DRIVEN SWEEP -- ' + (ROLES.length * GATED.length * 2)
          + ' cells, expectation from the TABLE, observation from the HANDLER');
  let cells = 0, denyCells = 0, allowCells = 0, leakChecks = 0;
  for (const role of ROLES) {
    for (const action of ACTIONS) {
      await test('2. ' + role + ' / ' + action + ' over ' + GATED.length + ' gated resources', async () => {
        const bad = [];
        for (const resource of GATED) {
          const expectDeny = sfRoles.decide(resource, role, action) === sfRoles.DENY;
          const { res, calls } = await call(resource, action, role);
          const observed = refusedByRoleGate(res, resource, role);
          cells++;
          if (expectDeny) {
            denyCells++;
            if (!observed) {
              bad.push(resource + ': table says DENY, handler answered '
                + res.statusCode + ' ' + JSON.stringify(res.body && res.body.error));
            } else {
              // THE STRONGER CLAIM: refused BEFORE the row was fetched.
              leakChecks++;
              const touched = calls.filter((c) => c.url.indexOf(resource) !== -1);
              if (touched.length) {
                bad.push(resource + ': refused 403 but the row was ALREADY '
                  + 'FETCHED (' + touched.length + ' call(s)) -- a leak with a '
                  + 'tidy status code');
              }
            }
          } else {
            allowCells++;
            if (observed) {
              bad.push(resource + ': table says ALLOW, role gate refused it');
            }
          }
        }
        assert.strictEqual(bad.length, 0, bad.length + ' cell(s):\n       - '
          + bad.join('\n       - '));
      });
    }
  }

  // ── THE TWO ARMS HANK NAMED AS HIGHEST VALUE, WRITTEN OUT EXPLICITLY.
  // They are inside the sweep above; they are repeated by name because a
  // governance roster and four ORC Chapter 2915 payee records are what somebody
  // will want to read off this file without reconstructing a 540-cell loop.
  section('3. THE TWO HIGHEST-VALUE ARMS, NAMED');
  await test('3a. sf_officers WRITE by each non-provisioning role -> refused', async () => {
    const nonProv = ROLES.filter((r) => sfRoles.PROVISIONING.indexOf(r) === -1);
    assert.ok(nonProv.length >= 8, 'expected at least 8 non-provisioning roles, got '
      + nonProv.length + ' -- PROVISIONING is ' + JSON.stringify(sfRoles.PROVISIONING));
    const bad = [];
    for (const role of nonProv) {
      const { res } = await call('sf_officers', 'write', role);
      if (!refusedByRoleGate(res, 'sf_officers', role)) {
        bad.push(role + ' -> ' + res.statusCode + ' ' + JSON.stringify(res.body));
      }
    }
    assert.strictEqual(bad.length, 0, 'the officer roster accepted a write from: '
      + bad.join('; '));
  });
  await test('3b. the three money resources WRITE by records.write -> refused', async () => {
    const bad = [];
    for (const resource of ['sf_ledger', 'sf_disbursements', 'sf_gaming_expenses']) {
      const { res } = await call(resource, 'write', 'records.write');
      if (!refusedByRoleGate(res, resource, 'records.write')) {
        bad.push(resource + ' -> ' + res.statusCode + ' ' + JSON.stringify(res.body));
      }
    }
    assert.strictEqual(bad.length, 0, 'records.write reached an ORC 2915 payee '
      + 'record: ' + bad.join('; '));
  });

  // ── THE NINE. NOT a pass, and not silence either.
  section('4. THE NINE LICENCE-KEY-ONLY RESOURCES -- DISCLOSED, NOT DRIVEN');
  await test('4. each of the nine is confirmed ABSENT from the gated set, and the '
             + 'role gate is confirmed NOT to fire for one of them', async () => {
    assert.ok(UNGATED.length > 0, 'if this is 0 the nine have been gated and this '
      + 'arm plus the denominator above both need rewriting -- which is the '
      + 'correct outcome, not a failure of the app');
    for (const r of UNGATED) {
      assert.strictEqual(GATED.indexOf(r), -1, r + ' is in both lists');
    }
    // The honest half: pick the role the table denies hardest and show the
    // handler does NOT refuse, because there is no gate here to refuse.
    const r = UNGATED[0];
    const role = ROLES[ROLES.length - 1];
    const { res } = await call(r, 'write', role);
    assert.strictEqual(refusedByRoleGate(res, r, role), false,
      r + ' IS now role-gated. That is an improvement and this arm is the thing '
      + 'that noticed -- move it into GATED and re-run.');
    console.log('       ' + UNGATED.length + ' resource(s) × ' + ROLES.length
      + ' roles × 2 verbs = ' + (UNGATED.length * ROLES.length * 2)
      + ' cells NOT DRIVEN, and not counted as passes');
  });

  section('CELL ARITHMETIC, so no number here can be quoted alone');
  console.log('  driven cells        ' + cells);
  console.log('    expected DENY     ' + denyCells + '  (each also checked for a pre-refusal row fetch: ' + leakChecks + ')');
  console.log('    expected ALLOW    ' + allowCells);
  console.log('  NOT-DRIVEN cells    ' + (UNGATED.length * ROLES.length * 2) + '  (the nine, named above)');
  console.log('  arms                ' + (pass + fail));

  if (FAILED.length) {
    console.log('\n' + FAILED.length + ' ARM(S) FAILED:');
    FAILED.forEach((f) => console.log('  - ' + f));
  }
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
