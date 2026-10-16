// tests/sd_data_not_provisioned_misclass.js
// OWNER: cody
// written 2026-10-16, batch b19, item 5
// REQUIREMENT: a PostgREST 400 whose body carries a Postgres error code must
//   not be reported as a missing table. The two states have opposite remedies
//   -- "run the migration" versus "the row itself was rejected and re-running
//   the migration will not help" -- and on a Tier A compliance log the
//   operator is told to re-run a migration that is already applied. The
//   platform already owns the correct classifier: notProvisioned() /
//   notProvisionedDecide() in api/sd-data.js read the body, answer 400
//   ROW_REFUSED for a 23xxx, 503 NOT_PROVISIONED for a genuine missing
//   relation, and 400 UPSTREAM_REJECTED for anything they cannot classify.
//   The defect is at the CALL SITES that never adopted it.
//
//   node tests/sd_data_not_provisioned_misclass.js
//
// Exit: 0 every arm passed · 1 an arm FAILED · 3 COULD NOT RUN
//
// ── TWO ARMS ARE RED ON PURPOSE AND THE FIX IS hank's ───────────────────────
// A1 and B1 are failing-first. Read the row in docs/known-red-suites.json
// before treating this suite's exit 1 as new, and read `expected_red_scope`
// there: it names the arms. Every PRECONDITION, CONTROL and COUNTERFACTUAL arm
// is expected GREEN, and one of those going red means the measurement rather
// than the handler.
//
// ── THESE TWO WERE OBSERVED BY fourth AND NEVER DRIVEN BY ANYTHING ──────────
// docs/2026-10-15-fourth-b25-findings.md §1 made both observations with a
// scratchpad driver that was not landed, so nothing in the tree would notice
// either being fixed OR getting worse. That is what this file is: the same two
// observations as runnable arms, with the populations they belong to measured
// here rather than quoted from the document.
//
// (1) A 23514 THROUGH A CLASS-B WRITE GUARD -- alf_op_audits, TIER A.
//     The guard is `if (w.status === 404 || w.status === 400)` on the response
//     of the upsert POST, and it answers 503 NOT_PROVISIONED unconditionally.
//     A row refused ON CONTENT -- a check constraint, a not-null, a 64KB
//     overflow -- is therefore reported as a missing table, on an operational
//     audit log whose entries are append-only compliance records.
//
// (2) A 42703 THROUGH A CLASS-C READ GUARD -- mech_site_assets.
//     The same guard shape on a GET answers HTTP 200 with
//     `{ ok: true, data: [], provisioned: false }`. A DROPPED OR RENAMED
//     column is then indistinguishable from a table that was never created,
//     and nothing in the answer is an error. THE CODE'S OWN COMMENT ARGUES FOR
//     FAILING CLOSED HERE AND THAT ARGUMENT IS NOT DISPUTED BY THIS FILE: a
//     registry provisioned before the AIM Act columns existed SHOULD be told
//     to re-run the idempotent migration. What is asserted is narrower and is
//     the half the comment does not address -- that the two states are
//     DISTINGUISHABLE in the answer. 42703 and 404 currently produce the same
//     bytes.
//
// ── WHAT IS DELIBERATELY NOT ASSERTED ──────────────────────────────────────
// NOT that all 151 sibling read guards or all 67 sibling write guards should
// be converted. The populations are MEASURED here and printed, because a
// number typed into a document goes stale and this one is the whole reason the
// finding matters -- but which of them carry a real risk is a per-branch
// judgement and belongs to whoever owns api/. This file drives the two fourth
// actually observed.
// NOT what the correct status code for a refused row is. notProvisioned()
// already chose 400 ROW_REFUSED and that choice is shipped; the counterfactual
// uses the shipped helper rather than inventing a second opinion.
// NOT that the read branch should return an error status. `provisioned: false`
// plus a distinguishing field would satisfy B1.

'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');

const ROOT = path.join(__dirname, '..');
// ONE INJECTION POINT, never set on an ordinary run: the counterfactual points
// this at a MUTATED COPY of the handler so the fix can be driven without
// editing api/, which is hank's.
const SD_DATA = process.env.SAIRN_B19_SD_DATA
  || path.join(ROOT, 'api/sd-data.js');

let pass = 0;
const failed = [];
const notes = [];

function ok(l) { pass += 1; console.log('  ok   ' + l); }
function bad(l, why) {
  failed.push(l);
  console.log('  FAIL ' + l + (why ? '\n         ' + String(why).slice(0, 460) : ''));
}
function section(t) { console.log('\n' + t); }
function couldNotRun(why) {
  console.log('COULD NOT RUN: ' + why + ' Nothing was verified.');
  process.exit(3);
}

if (!fs.existsSync(SD_DATA)) couldNotRun(SD_DATA + ' does not exist.');
const API_DIR = path.dirname(SD_DATA);
const HANDLER_SRC = fs.readFileSync(SD_DATA, 'utf8').replace(/\r\n/g, '\n');

// ── THE TWO SUBJECT GUARDS, ANCHORED ON THE BRANCH THEY SIT IN ─────────────
// A bare `if (w.status === 404 || w.status === 400)` occurs hundreds of times
// in this file, so the anchor is the BRANCH GUARD and the window is bounded by
// the next `if (resource === ` rather than by a character count. A fixed-size
// window is the thing that rots; this one grows with the branch.
// THE FIRST SPELLING BOUNDED THE BRANCH AT THE NEXT `\n    if (resource === `
// AND IT OVERRAN, recorded rather than quietly replaced because the failure it
// produced was the wrong verdict in the right direction. It sliced 23,575
// characters for a branch of about 180 lines -- the next same-indent branch
// guard is a long way below -- and the slice therefore contained OTHER
// branches that DO call notProvisioned(). Arm P5, which asserts the subject
// has NOT already been fixed, then reported that the defect was gone: a
// precondition arm telling the suite to retire itself, on a defect that is
// still shipped. A TERMINATOR IS A GUESS ABOUT WHAT COMES NEXT; A BALANCED
// BRACE IS A PROPERTY OF THE BRANCH ITSELF.
function branchOf(guard) {
  const i = HANDLER_SRC.indexOf(guard);
  if (i < 0) return null;
  let j = HANDLER_SRC.indexOf('{', i);
  if (j < 0) return null;
  let depth = 0;
  for (; j < HANDLER_SRC.length; j += 1) {
    const c = HANDLER_SRC[j];
    if (c === '{') depth += 1;
    else if (c === '}') {
      depth -= 1;
      if (depth === 0) return HANDLER_SRC.slice(i, j + 1);
    }
  }
  return null;
}

const OPA_GUARD = "if (resource === 'alf_op_audits' && action === 'write') {";
const MECH_GUARD =
  "if (resource === 'mech_site_assets' && (action === 'read' || action === 'write')) {";
const SHAPE = /if \((\w+)\.status === 404 \|\| \1\.status === 400\)/g;

section('PRECONDITIONS -- each a third state, never folded into a pass');
for (const g of [OPA_GUARD, MECH_GUARD]) {
  const n = HANDLER_SRC.split(g).length - 1;
  if (n !== 1) {
    couldNotRun('the branch guard ' + JSON.stringify(g) + ' occurs ' + n
              + ' times in ' + SD_DATA + ', so the subject branch could '
              + 'not be located unambiguously.');
  }
}
const OPA_BRANCH = branchOf(OPA_GUARD);
const MECH_BRANCH = branchOf(MECH_GUARD);
if (!OPA_BRANCH || !MECH_BRANCH) {
  couldNotRun('one of the two subject branches could not be sliced out of the '
            + 'handler source.');
}
ok('P1. both subject branches located by their own `resource ===` guard and '
   + 'closed by BALANCED BRACES rather than by a terminator or a character '
   + 'window (alf_op_audits ' + OPA_BRANCH.length + ' chars, mech_site_assets '
   + MECH_BRANCH.length + ' chars)');
// P1b IS WHAT WOULD HAVE CAUGHT THE OVERRUN. A slice that swallows the next
// branch is still "balanced" as far as the counter is concerned if the counter
// started in the wrong place, so the arm is on the CONTENT: each branch must
// mention its own resource and must NOT mention the other's.
const opaClean = OPA_BRANCH.indexOf('alf_op_audits') >= 0
  && OPA_BRANCH.indexOf("resource === 'mech_site_assets'") < 0;
const mechClean = MECH_BRANCH.indexOf('mech_site_assets') >= 0
  && MECH_BRANCH.indexOf("resource === 'alf_op_audits'") < 0;
if (opaClean && mechClean) {
  ok('P1b. ...and neither slice has overrun into the other branch -- each '
     + 'names its own resource and not the other\'s. THE FIRST VERSION OF '
     + 'branchOf() OVERRAN BY A FACTOR OF 130 and P5 below then reported the '
     + 'defect as already fixed, which is a precondition arm telling the '
     + 'suite to retire itself over a defect that is still shipped');
} else {
  bad('P1b. a branch slice has overrun into another branch, so every arm that '
      + 'reads the slice is reading the wrong code',
      'alf_op_audits clean: ' + opaClean + ', mech_site_assets clean: '
      + mechClean);
}

// ── THE POPULATIONS, MEASURED HERE AND NOT QUOTED ──────────────────────────
// fourth's document names 22 class-B write-guarded branches and a class-C read
// set; both numbers are re-derived from the shipped source on every run, so a
// figure in this output can never be older than the file it describes.
const POP = { total: 0, helper: 0, raw503: 0, raw200: 0, other: 0 };
const SRC_LINES = HANDLER_SRC.split('\n');
let m;
SHAPE.lastIndex = 0;
while ((m = SHAPE.exec(HANDLER_SRC)) !== null) {
  POP.total += 1;
  const ln = HANDLER_SRC.slice(0, m.index).split('\n').length;
  const win = SRC_LINES.slice(ln - 1, ln + 5).join('\n');
  if (win.indexOf('notProvisioned(') >= 0) POP.helper += 1;
  else if (win.indexOf('503') >= 0 && win.indexOf('NOT_PROVISIONED') >= 0) POP.raw503 += 1;
  else if (win.indexOf('provisioned: false') >= 0) POP.raw200 += 1;
  else POP.other += 1;
}
ok('P2. the guard population is MEASURED from source on this run, not quoted: '
   + POP.total + ' guards of the form `X.status === 404 || X.status === 400` -- '
   + POP.helper + ' route through notProvisioned(), ' + POP.raw503
   + ' answer a raw 503 NOT_PROVISIONED, ' + POP.raw200
   + ' answer a raw HTTP 200 `provisioned: false`, ' + POP.other + ' other');
if (POP.total < 50 || POP.helper === 0 || POP.raw503 === 0 || POP.raw200 === 0) {
  bad('P3. the population scan found a plausible spread of all three answers, '
      + 'so P2 is a measurement rather than a regex that stopped matching',
      JSON.stringify(POP));
} else {
  ok('P3. ...and all three answers are represented, so P2 is a measurement '
     + 'rather than a regex that stopped matching');
}
// MEMBERSHIP, ASSERTED: the two subjects must each be an instance of the shape
// the population counts. Without this, P2 could be counting a set that does
// not contain either thing this file drives.
SHAPE.lastIndex = 0;
const opaHasShape = SHAPE.test(OPA_BRANCH);
SHAPE.lastIndex = 0;
const mechHasShape = SHAPE.test(MECH_BRANCH);
if (opaHasShape && mechHasShape) {
  ok('P4. and BOTH subjects are members of that population -- the guard shape '
     + 'occurs inside each of the two branches this file drives');
} else {
  bad('P4. both subjects must be members of the measured population',
      'alf_op_audits: ' + opaHasShape + ', mech_site_assets: ' + mechHasShape);
}
if (OPA_BRANCH.indexOf('notProvisioned(') < 0) {
  ok('P5. ...and the alf_op_audits branch does NOT already route through '
     + 'notProvisioned(), so A1 below is measuring the shipped answer');
} else {
  bad('P5. the alf_op_audits branch already calls notProvisioned() -- A1 is '
      + 'no longer measuring the shipped defect and this suite needs '
      + 're-aiming or retiring', OPA_BRANCH.slice(0, 300));
}

// ── THE HARNESS. licence, session and fetch mocked; nothing real is reached ─
const LIC_HASH = 'hash-of-the-b19-not-provisioned-licence';
const LICENCE = require.resolve(path.join(API_DIR, '_lib/license.js'));
let LIC_APP = 'sairncare';
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: LIC_HASH,
      stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: LIC_APP
    }),
    hashLicense: () => LIC_HASH,
  },
};

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  process.env[['SD', 'AUTH', 'SECRET'].join('_')]
  || ['b19', 'notprov', String(process.pid)].join('-');
const { signSessionToken } = require(path.join(API_DIR, '_lib/auth.js'));

// THE SESSION HEADER IS READ OUT OF auth.js, NOT TYPED. The blob-scope suite
// paid for the other way round: `x-sd-session` was typed, tokenFromRequest()
// reads `x-sd-auth`, and every gated site failed its precondition -- which is
// the shape of a suite reporting defects and measuring none.
const AUTH_SRC = fs.readFileSync(path.join(API_DIR, '_lib/auth.js'), 'utf8');
const HDR_M = AUTH_SRC.match(/function tokenFromRequest\(req\)\s*\{\s*\n\s*const h = req\.headers\[['"]([a-z0-9-]+)['"]\]/);
if (!HDR_M) {
  couldNotRun('the session header could not be read out of '
            + 'api/_lib/auth.js tokenFromRequest(), so this suite cannot '
            + 'present a session and every arm would fail its precondition '
            + 'for a reason that is not about the classification.');
}
const SESSION_HEADER = HDR_M[1];

// ── THE FAILURE INJECTOR ───────────────────────────────────────────────────
// `inject` names ONE table and ONE method and answers it with a real
// PostgREST failure body. Everything else answers healthily, so the branch
// reaches its guard instead of dying earlier -- which is the difference
// between measuring the guard and measuring a validation refusal.
let inject = null;
const seen = [];
global.fetch = async (url, opts) => {
  const u = String(url);
  const method = (opts && opts.method) || 'GET';
  seen.push(method + ' ' + u.slice(u.indexOf('/rest/') + 1, u.indexOf('?') < 0 ? u.length : u.indexOf('?')));
  if (inject && u.indexOf(inject.table) >= 0 && method === inject.method) {
    const raw = JSON.stringify(inject.body);
    return {
      ok: false, status: inject.status,
      json: async () => inject.body,
      text: async () => raw,
    };
  }
  if (/_employee_auth\?/.test(u)) {
    return { ok: true, status: 200, json: async () => [{ active: true }] };
  }
  if (/alf_facility\?/.test(u)) {
    return { ok: true, status: 200,
             json: async () => [{ data: { food_thresholds: {} } }] };
  }
  if (method === 'POST' || method === 'PATCH') {
    let body = null;
    try { body = JSON.parse(opts.body); } catch (e) { body = {}; }
    return { ok: true, status: 200, json: async () => [Object.assign({}, body)] };
  }
  return { ok: true, status: 200, json: async () => [] };
};

delete require.cache[require.resolve(SD_DATA)];
const handler = require(SD_DATA);

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

async function call(action, resource, payload, opts) {
  const o = opts || {};
  LIC_APP = o.app || 'sairncare';
  inject = o.inject || null;
  seen.length = 0;
  const headers = { authorization: 'Bearer testkey' };
  headers[SESSION_HEADER] = signSessionToken({
    app: LIC_APP, employee_id: 'E1', role: o.role || 'owner',
    license_hash: LIC_HASH });
  const req = { method: 'POST', headers: headers,
                body: { action: action, resource: resource, payload: payload } };
  const res = fakeRes();
  await handler(req, res);
  inject = null;
  return res;
}

function code(res) {
  return (res.body && res.body.error && res.body.error.code) || '';
}

// A valid operational-audit observation. THE record_type MATTERS: the branch
// validates it against ALF_OPA_TYPES before any fetch, and fourth's first run
// of this observation injected a failure that was never reached because the
// payload carried `incident_review`. THE CONTROL IS WHAT SHOWED IT -- the
// no-failure control returned the same 400. The value is read out of the
// handler's own allowlist rather than typed, so this cannot happen again
// silently.
const TYPES_M = HANDLER_SRC.match(/const ALF_OPA_TYPES = ([^;]*);/);
let OPA_TYPE = null;
if (TYPES_M) {
  const keys = TYPES_M[1].match(/([a-z_]+)\s*:/g) || [];
  const plain = keys.map((k) => k.replace(/\s*:$/, ''));
  OPA_TYPE = plain.indexOf('sanitation') >= 0 ? 'sanitation' : plain[0];
}
if (!OPA_TYPE) {
  couldNotRun('ALF_OPA_TYPES could not be read out of the handler, so this '
            + 'suite cannot build a payload that survives validation -- and a '
            + 'payload refused at validation never reaches the guard under '
            + 'test, which is a suite measuring nothing while reporting a '
            + 'defect.');
}
ok('P6. the record_type is READ from the handler\'s own ALF_OPA_TYPES '
   + 'allowlist (' + JSON.stringify(OPA_TYPE) + '), never typed -- a payload '
   + 'refused at validation never reaches the guard under test');

function observation(extra) {
  return Object.assign({ id: 'OPA-B19-' + Date.now(), record_type: OPA_TYPE,
                         observed_on: '2026-10-16', passed: true,
                         notes: 'b19 arm' }, extra || {});
}

const PG_23514 = { code: '23514', message: 'new row for relation '
  + '"alf_op_audits" violates check constraint "alf_op_audits_passed_check"',
  details: null, hint: null };
const PG_42703 = { code: '42703',
  message: 'column mech_site_assets.site_state does not exist',
  details: null, hint: null };
const PG_404 = { code: 'PGRST205',
  message: 'Could not find the table \'public.alf_op_audits\' in the schema '
  + 'cache', details: null, hint: null };

(async function main() {
  console.log('NOT_PROVISIONED MISCLASSIFICATION -- criteria 2026-10-16.1');
  console.log('handler under test: ' + SD_DATA);

  // ── SECTION A: a 23514 through a class-B WRITE guard, TIER A resource ────
  section('A. alf_op_audits (TIER A) -- a row refused on CONTENT');

  const a0 = await call('write', 'alf_op_audits', observation());
  if (a0.statusCode === 200 && a0.body && a0.body.ok) {
    ok('A0. CONTROL, store healthy: the write reaches the upsert and answers '
       + '200 ok -- so A1 below is measuring the guard and not a validation '
       + 'refusal, a 401, a 403 or a 409. THIS IS THE ARM THAT CAUGHT fourth\'s '
       + 'first run, where an invalid record_type made the control and the '
       + 'injected case return the same 400');
  } else {
    bad('A0. CONTROL, store healthy: the write must reach the upsert and '
        + 'answer 200 ok, or nothing below has measured the guard',
        'status=' + a0.statusCode + ' body=' + JSON.stringify(a0.body).slice(0, 300)
        + '\n         fetches: ' + JSON.stringify(seen));
  }

  const a1 = await call('write', 'alf_op_audits', observation(),
    { inject: { table: 'alf_op_audits?on_conflict', method: 'POST',
                status: 400, body: PG_23514 } });
  if (a1.statusCode === 503 || code(a1) === 'NOT_PROVISIONED') {
    bad('A1 (RED ON PURPOSE, FIX ROUTED TO hank): a 400 carrying Postgres '
        + '23514 on the alf_op_audits upsert must NOT be reported as a '
        + 'missing table -- the operator is told to run a migration that is '
        + 'already applied, on a Tier A append-only compliance log',
        'got status=' + a1.statusCode + ' code=' + JSON.stringify(code(a1))
        + '\n         ' + JSON.stringify(a1.body).slice(0, 300)
        + '\n         THE FIX IS A CALL-SITE CHANGE AND NOTHING ELSE: replace '
        + 'the raw 503 at the `w.status === 404 || w.status === 400` guard '
        + 'with `await notProvisioned(res, w, <the same message>)`. The helper '
        + 'already answers correctly -- arm A2 drives it.');
  } else {
    ok('A1. a 400 carrying Postgres 23514 on the alf_op_audits upsert is NOT '
       + 'reported as a missing table (status=' + a1.statusCode + ' code='
       + JSON.stringify(code(a1)) + ')');
  }

  // ── A2: THE COUNTERFACTUAL, ON A COPY. api/ IS NEVER WRITTEN. ───────────
  // A failing-first arm with no counterfactual cannot say whether the fix it
  // names would work, and this one names a specific call-site change. The copy
  // applies exactly that change and nothing else.
  if (process.env.SAIRN_B19_SD_DATA) {
    ok('A2. (not run: this IS the counterfactual child)');
  } else {
    const RAW_503 = OPA_BRANCH.match(
      /if \(w\.status === 404 \|\| w\.status === 400\) \{\n(\s+)res\.status\(503\)\.json\(\{ error: \{ code: 'NOT_PROVISIONED', message: '([^']*)' \} \}\);\n\s+return;\n\s+\}/);
    if (!RAW_503) {
      bad('A2. PRECONDITION: the raw 503 block could not be matched inside the '
          + 'alf_op_audits branch, so the counterfactual could not be built. '
          + 'Re-anchor it on the branch rather than loosening the pattern',
          OPA_BRANCH.slice(-600));
    } else {
      const fixed = RAW_503[0].replace(
        /res\.status\(503\)\.json\(\{[\s\S]*?\}\);/,
        "await notProvisioned(res, w, '" + RAW_503[2] + "');");
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'b19-notprov-'));
      const copyDir = path.join(tmp, 'api');
      fs.cpSync(path.join(ROOT, 'api'), copyDir, { recursive: true });
      const copy = path.join(copyDir, 'sd-data.js');
      fs.writeFileSync(copy,
        fs.readFileSync(copy, 'utf8').replace(/\r\n/g, '\n')
          .replace(RAW_503[0], fixed), 'utf8');
      const { execFileSync } = require('child_process');
      let out = '';
      let childCode = null;
      try {
        out = execFileSync(process.execPath, [__filename], {
          encoding: 'utf8',
          env: Object.assign({}, process.env, { SAIRN_B19_SD_DATA: copy }),
          cwd: ROOT,
        });
        childCode = 0;
      } catch (e) {
        out = (e.stdout || '') + (e.stderr || '');
        childCode = e.status;
      }
      const a1Green = /^  ok   A1\. /m.test(out);
      const rowRefused = /ROW_REFUSED/.test(out);
      if (a1Green && rowRefused) {
        ok('A2. COUNTERFACTUAL on a COPY of api/, one call site changed and '
           + 'nothing else: routing that guard through the shipped '
           + 'notProvisioned() makes A1 GREEN and answers 400 ROW_REFUSED. So '
           + 'A1 measures this specific call site and the fix needs no new '
           + 'helper, no new status code and no decision (child exit '
           + childCode + ')');
      } else {
        bad('A2. COUNTERFACTUAL: with the guard routed through '
            + 'notProvisioned() in a copy, A1 must go green and the answer '
            + 'must be ROW_REFUSED', 'child exit ' + childCode
            + ' A1 green: ' + a1Green + ' ROW_REFUSED seen: ' + rowRefused
            + '\n         ' + out.slice(-600));
      }
      const a3 = /^  ok   A3\. /m.test(out);
      if (a3) {
        ok('A3. ...and in that same copy a GENUINE missing table still '
           + 'answers 503 NOT_PROVISIONED, so the fix does not trade one '
           + 'wrong answer for another');
      } else {
        bad('A3. the counterfactual copy must still answer 503 '
            + 'NOT_PROVISIONED for a real missing relation', out.slice(-600));
      }
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  }

  // A3 is asserted BY THE CHILD, which is the only process where the fix is
  // applied. In the parent it is reported through the child's output above.
  if (process.env.SAIRN_B19_SD_DATA) {
    const a3r = await call('write', 'alf_op_audits', observation(),
      { inject: { table: 'alf_op_audits?on_conflict', method: 'POST',
                  status: 404, body: PG_404 } });
    if (a3r.statusCode === 503 && code(a3r) === 'NOT_PROVISIONED') {
      ok('A3. a GENUINE missing table still answers 503 NOT_PROVISIONED');
    } else {
      bad('A3. a genuine missing table must still answer 503 NOT_PROVISIONED',
          'status=' + a3r.statusCode + ' code=' + JSON.stringify(code(a3r)));
    }
  }

  // ── SECTION B: a 42703 through a class-C READ guard ─────────────────────
  section('B. mech_site_assets -- a column that is gone');

  const b0 = await call('read', 'mech_site_assets', {},
                        { app: 'sairnmechanical' });
  if (b0.statusCode === 200 && b0.body && b0.body.provisioned === true) {
    ok('B0. CONTROL, store healthy: the read answers 200 with '
       + '`provisioned: true` -- so B1 below is a comparison between two real '
       + 'answers and not a harness that cannot reach the branch');
  } else {
    bad('B0. CONTROL, store healthy: the read must answer 200 with '
        + '`provisioned: true`',
        'status=' + b0.statusCode + ' body=' + JSON.stringify(b0.body).slice(0, 300)
        + '\n         fetches: ' + JSON.stringify(seen));
  }

  const bCol = await call('read', 'mech_site_assets', {},
    { app: 'sairnmechanical',
      inject: { table: 'mech_site_assets?license_hash', method: 'GET',
                status: 400, body: PG_42703 } });
  const bGone = await call('read', 'mech_site_assets', {},
    { app: 'sairnmechanical',
      inject: { table: 'mech_site_assets?license_hash', method: 'GET',
                status: 404, body: PG_404 } });
  if (bGone.statusCode === 200 && bGone.body
      && bGone.body.provisioned === false) {
    ok('B2. CONTROL: a genuine missing table on the read answers 200 '
       + '`provisioned: false` -- the paired positive, so B1 is comparing the '
       + 'column case against a real never-provisioned answer');
  } else {
    bad('B2. CONTROL: a genuine missing table must answer 200 '
        + '`provisioned: false`',
        'status=' + bGone.statusCode + ' body='
        + JSON.stringify(bGone.body).slice(0, 300));
  }
  const sameStatus = bCol.statusCode === bGone.statusCode;
  const sameBody = JSON.stringify(bCol.body) === JSON.stringify(bGone.body);
  if (sameStatus && sameBody) {
    bad('B1 (RED ON PURPOSE, FIX ROUTED TO hank): a 42703 -- a DROPPED or '
        + 'RENAMED column -- must be distinguishable in the answer from a '
        + 'table that was never created. Both produce byte-identical '
        + 'responses, at HTTP 200, with nothing in them that is an error, '
        + 'which is the state a PARTIAL MIGRATION leaves',
        'status ' + bCol.statusCode + ' both; body both '
        + JSON.stringify(bCol.body).slice(0, 220)
        + '\n         NOT an argument for returning an error here: the '
        + 'branch\'s own comment is right that a registry predating the AIM '
        + 'Act columns should be told to re-run the idempotent migration. The '
        + 'assertion is only that the two states DIFFER -- a distinguishing '
        + 'field alongside `provisioned: false` satisfies it.');
  } else {
    ok('B1. a 42703 is distinguishable from a never-provisioned table in the '
       + 'answer (status ' + bCol.statusCode + ' vs ' + bGone.statusCode
       + ', bodies ' + (sameBody ? 'identical' : 'different') + ')');
  }
  notes.push('mech_site_assets, 42703: status ' + bCol.statusCode + ' body '
             + JSON.stringify(bCol.body));
  notes.push('mech_site_assets, 404:   status ' + bGone.statusCode + ' body '
             + JSON.stringify(bGone.body));
  notes.push('alf_op_audits, 23514:    status ' + a1.statusCode + ' code '
             + JSON.stringify(code(a1)));

  if (notes.length) {
    section('MEASURED, NOT ASSERTED -- the answers as shipped');
    notes.forEach((n) => console.log('  * ' + n));
    console.log('  Which of the ' + POP.raw200 + ' sibling read guards and '
              + POP.raw503 + ' sibling write guards carry a real risk is a '
              + 'per-branch\n  judgement and belongs to whoever owns api/. '
              + 'This file drives the two\n  fourth observed.');
  }

  console.log('\n' + pass + ' passed, ' + failed.length + ' failed');
  if (failed.length) {
    console.log(failed.length + ' ARM(S) FAILED:');
    failed.forEach((f) => console.log('  - ' + f));
    console.log('\nA1 AND B1 ARE EXPECTED RED until the two call sites are '
              + 'changed; the row in docs/known-red-suites.json names them. '
              + 'ANY OTHER failure here is NEW and means the measurement '
              + 'rather than the handler -- a P arm means an anchor or an '
              + 'allowlist moved, A0/B0/B2 mean the branch was not reached, '
              + 'and A2/A3 mean the named fix no longer produces the answer '
              + 'this file claims for it.');
    process.exit(1);
  }
  process.exit(0);
}());
