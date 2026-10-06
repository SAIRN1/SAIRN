// tests/sd_data_sdn_blob_scope.js
//
// REQUIREMENT: the ONE generic `SDN_RESOURCES` write branch in api/sd-data.js
//   must not store caller-supplied SCOPE KEYS inside the `data` jsonb column.
//   `license_hash`, `app_id` and `p_license_hash` are derived by the handler
//   from the verified licence; a copy of them inside `data` is a field the
//   row's own real column contradicts.
//
// WHY, AND IT IS HOVER H2 seq 529 / seq 538. Until 2026-10-05 the branch built
// its body as `data: payload` -- the caller's entire object, verbatim. ONE
// branch serves ALL EIGHTEEN SDN resources, so the single omission was
// eighteen omissions, twelve of them on rows carrying client identity or
// money.
//
// LATENT RATHER THAN LIVE, SAID OUT LOUD SO THE ARMS ARE NOT OVERSOLD: every
// read path resolves tenancy from the real `license_hash` COLUMN, which always
// wins, so no cross-tenant read was ever reachable through this. What the
// defect produced was a stored lie -- a forged tenant id sitting in `data`,
// echoed back on read, waiting for the next reader that trusts it.
//
// AND THE ARM THAT MATTERS AS MUCH AS THE REFUSALS: `id` MUST SURVIVE. This
// branch's read (`api/sd-data.js`, the SDN read limb) returns `x.data`
// verbatim with no re-attachment from the id column, unlike the sibling
// branches that pass `['id']` to storedBlob. A fix that stripped `id` here
// would be a correct-looking scope fix that silently emptied the id off every
// record in eighteen resources.
//
// IT DRIVES THE REAL HANDLER with auth, licence and fetch mocked, and it
// asserts on the BODY ACTUALLY POSTED UPSTREAM rather than on the response --
// the response is not where the defect lived.
//
// Run:  node tests/sd_data_sdn_blob_scope.js

'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..');

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'REAL_HASH',
  stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: 'sairndesign'
});

const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token) => {
  if (!token) return null;
  const p = JSON.parse(token);
  return { role: p.role, employee_id: p.employee_id, app: 'sairndesign',
           subject: p.employee_id };
};

// Every upstream POST is captured rather than answered from a fixture list:
// the question this file asks is "what did the handler SEND", so the sent body
// is the measurement and the reply is only enough to let the branch finish.
let lastPost = null;
global.fetch = async (url, opts) => {
  const u = String(url);
  const method = (opts && opts.method) || 'GET';
  if (method === 'POST') {
    lastPost = { url: u, body: JSON.parse(opts.body) };
    // return=representation: echo back what a real PostgREST upsert would.
    return { ok: true, status: 200,
             json: async () => [{ data: lastPost.body.data }] };
  }
  // THE ACTIVE-CREDENTIAL PRE-GATE RUNS BEFORE EVERY BRANCH and asks the app's
  // employee-auth table whether this credential is still active. An empty
  // answer is a 403 CREDENTIAL_INACTIVE, which is correct behaviour and would
  // have made every arm below fail for the wrong reason. Answered honestly
  // here -- an ACTIVE employee -- so what the arms measure is the write
  // branch and not the pre-gate.
  if (/_employee_auth\?/.test(u)) {
    return { ok: true, status: 200, json: async () => [{ active: true }] };
  }
  return { ok: true, status: 200, json: async () => [] };
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function write(resource, payload, withSession) {
  lastPost = null;
  const headers = { authorization: 'Bearer testkey' };
  if (withSession) {
    headers['x-test-token'] = JSON.stringify({ role: 'owner', employee_id: 'E1' });
  }
  const req = { method: 'POST', headers: headers,
                body: { action: 'write', resource: resource, payload: payload } };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

let pass = 0, fail = 0;
function ok(l) { pass++; console.log('  ok   ' + l); }
function bad(l, why) {
  fail++;
  console.log('  FAIL ' + l);
  if (why) console.log('       ' + String(why).slice(0, 400));
}

// A payload shaped like the real attack: a forged tenant id and a forged
// app id riding in beside ordinary fields.
function forged(extra) {
  return Object.assign({
    id: 'PJ-1',
    name: 'Harbour House',
    budget: 120000,
    license_hash: 'ATTACKER_HASH',
    app_id: 'not-sairndesign',
    p_license_hash: 'ATTACKER_HASH_RPC'
  }, extra || {});
}

(async function main() {
  console.log('SDN GENERIC WRITE -- STORED BLOB SCOPE -- criteria 2026-10-05.1\n');

  console.log('A. REFUSED INTO THE BLOB: the three scope keys never land in `data`');

  let r = await write('sdn_projects', forged(), true);
  if (r.statusCode !== 200 || !lastPost) {
    bad('A0. the gated write must reach upstream at all',
        'status=' + r.statusCode + ' body=' + JSON.stringify(r.body));
  } else {
    ok('A0. a session-gated SDN write (sdn_projects) reaches upstream, so the '
       + 'arms below are measuring a real POST and not a refusal');
  }

  const d = (lastPost && lastPost.body && lastPost.body.data) || {};
  if (lastPost && d.license_hash === undefined) {
    ok('A1. a FORGED `license_hash` in the payload is NOT stored in `data`. '
       + 'THIS IS THE DEFECT: it used to be, verbatim, and the row\'s real '
       + 'column then contradicted a field sitting beside it');
  } else {
    bad('A1. payload license_hash must not reach `data`',
        'data.license_hash=' + JSON.stringify(d.license_hash));
  }
  if (lastPost && d.app_id === undefined) {
    ok('A2. ...and neither is a forged `app_id`');
  } else {
    bad('A2. payload app_id must not reach `data`',
        'data.app_id=' + JSON.stringify(d.app_id));
  }
  if (lastPost && d.p_license_hash === undefined) {
    ok('A3. ...nor the RPC spelling `p_license_hash`, which is the same key '
       + 'class wearing a different prefix and is why blob.js lists all three');
  } else {
    bad('A3. payload p_license_hash must not reach `data`',
        'data.p_license_hash=' + JSON.stringify(d.p_license_hash));
  }

  if (lastPost && lastPost.body.license_hash === 'REAL_HASH') {
    ok('A4. the real COLUMN still carries the licence derived from the bearer '
       + 'key, not the forged one -- the fix removes a lie, it does not remove '
       + 'the tenancy');
  } else {
    bad('A4. the license_hash column must come from the verified licence',
        'column=' + JSON.stringify(lastPost && lastPost.body.license_hash));
  }

  console.log('\nB. KEPT: everything that is not a scope key, and `id` above all');

  if (lastPost && d.id === 'PJ-1') {
    ok('B1. `id` SURVIVES INTO `data`. WITHOUT THIS ARM the obvious fix -- '
       + 'storedBlob(payload, [\'id\']), which every sibling branch uses -- '
       + 'would pass A1-A3 and silently empty the id off every record in all '
       + 'eighteen resources, because THIS read returns `x.data` verbatim and '
       + 'never re-attaches it from the column');
  } else {
    bad('B1. id must remain inside the stored blob', 'data.id=' + JSON.stringify(d.id));
  }
  if (lastPost && d.name === 'Harbour House' && d.budget === 120000) {
    ok('B2. ordinary fields are untouched, so the fix is a scope strip and '
       + 'not a sanitiser that quietly drops data');
  } else {
    bad('B2. ordinary payload fields must survive', JSON.stringify(d));
  }

  console.log('\nC. ALL EIGHTEEN, not just the gated ones -- one branch, one fix');

  // sdn_moodboards is NOT in SD_SESSION_GATED. If the fix had been written
  // into a gated path rather than the shared one, this arm would fail.
  r = await write('sdn_moodboards', forged({ id: 'MB-1', title: 'Palette' }), false);
  const d2 = (lastPost && lastPost.body && lastPost.body.data) || {};
  if (r.statusCode === 200 && lastPost && d2.license_hash === undefined
      && d2.app_id === undefined && d2.id === 'MB-1') {
    ok('C1. an UNGATED SDN resource (sdn_moodboards, licence-key only) is '
       + 'stripped identically and keeps its id -- the fix is in the shared '
       + 'branch, which is the only place it could cover all eighteen');
  } else {
    bad('C1. the ungated SDN resources must be stripped too',
        'status=' + r.statusCode + ' data=' + JSON.stringify(d2));
  }

  console.log('\nD. THE GATE IS IN THE HANDLER, pinned at source');

  const fs = require('fs');
  const SRC = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const CODE = SRC.split(/\r?\n/)
    .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');

  // UNIQUENESS GUARD. `data: payload` is a shape that occurs in more than one
  // branch of this file, so a bare substring search would be answering about
  // whichever one it happened to find. The anchor is this branch's own
  // variable, asserted to appear exactly once as a declaration.
  const DECL = 'const sdnData = storedBlob(payload, []);';
  const declCount = CODE.split(DECL).length - 1;
  if (declCount === 1) {
    ok('D1. the SDN branch builds its blob through storedBlob, and the anchor '
       + 'for this check appears EXACTLY ONCE so D2 below cannot be grading a '
       + 'different branch');
  } else {
    bad('D1. the storedBlob declaration must appear exactly once',
        'found ' + declCount + ' time(s)');
  }
  // SCOPED TO THE BRANCH, and the first version of this arm was NOT. It cut
  // the block at the string `SAIRNLEGACY` -- which only exists in a COMMENT,
  // and comments are stripped two lines above -- so the "block" ran to the end
  // of the file and matched `data: payload` in unrelated branches. The cut is
  // now the next top-level `if (` at this indentation, which is code.
  const sdnBlock = CODE.split("if (SDN_RESOURCES[resource] && action === 'write')")[1] || '';
  const upToEnd = sdnBlock.split(/\n {4}if \(/)[0];
  if (upToEnd && upToEnd.length < sdnBlock.length && !/data:\s*payload\b/.test(upToEnd)) {
    ok('D2. and `data: payload` is gone from that branch entirely -- including '
       + 'the fallback limb of the 200 response, which used to answer "here is '
       + 'the stored row" with a shape the database does not hold');
  } else {
    bad('D2. no raw `data: payload` may remain in the SDN write branch', '');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
