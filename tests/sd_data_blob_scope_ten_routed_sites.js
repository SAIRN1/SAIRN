// tests/sd_data_blob_scope_ten_routed_sites.js
// OWNER: cody
// written 2026-10-15, batch b15, item 3
// REQUIREMENT: the three SCOPE KEYS -- license_hash, app_id, p_license_hash --
//   are derived by the handler from the verified licence and session and must
//   never be stored inside a row's `data` jsonb, on any branch. A copy inside
//   `data` is a field the row's own real column contradicts, it is echoed back
//   on read, and the next reader that trusts it is reading a forged tenant id.
//   api/_lib/blob.js states that as the one universal truth it hides; these
//   ten write sites do not call it.
//
//   node tests/sd_data_blob_scope_ten_routed_sites.js
//
// Exit: 0 every arm passed · 1 an arm FAILED · 3 COULD NOT RUN
//
// ── THIS REPLACES CITATIONS WITH RUNNABLE ARMS ──────────────────────────────
// docs/2026-10-14-cody-b14-blob-conversion-routed-to-hank.md routed ten
// unconverted sites to hank with a branch, a table and a paired read PER SITE.
// Every one of those was a CITATION read out of the source and stamped to a
// sha -- not a test result, and the document said so. b15 item 3 is the other
// half: each of the ten is now DRIVEN through the real handler, and the arm
// asserts on THE BODY ACTUALLY POSTED UPSTREAM rather than on the response.
// The response is not where the defect lives.
//
// ── THE TEN ARMS ARE GREEN SINCE 2026-10-15, AND THE PREMISE WAS STALE ──────
// This header read "ALL TEN ARMS ARE RED UNTIL hank CONVERTS THE SITE" and was
// never true of a tree this suite was run on: hank's conversion landed in
// 8627f4e4 at 08:09 and this file was committed in 9f04ad39 at 08:11, on a
// PARALLEL branch -- `git merge-base --is-ancestor 8627f4e4 9f04ad39` -> NO.
// The b15 measurement and the b15 isolated-clone diagnosis (sha 040cbfd9, also
// not a descendant of the fix) were both real; their BASE was old. At HEAD the
// suite is exit 0, 16 passed, so the greens are MEASUREMENTS of a landed
// conversion and not an unarmed harness -- which is what the CONTROL arm and
// arm Z exist to tell apart. Found by fourth b25 F1.
//
// THE CHEAP CHECK FOR EVERY FAILING-FIRST SUITE, and it costs one command:
//   git merge-base --is-ancestor <the fix> <the sha the red was measured at>
// separates "red because the defect is there" from "red because my base is
// old". Nothing else in the red verdict distinguishes the two.
//
// ── WHAT IS DELIBERATELY NOT ASSERTED, SITE BY SITE ─────────────────────────
// NOT that every site NEEDS converting. tools/blob_conversion_coverage.py says
// in its own header that it "cannot tell a harmless RAW site from a harmful
// one", and this file does not overrule that. What it asserts is the ONE thing
// blob.js makes universal -- the scope keys -- and nothing per-table beyond it.
//
// NOT that `id` should be stripped. THE OPPOSITE, and it is an arm: `sd_slabs`
// and the two dispatchers' reads re-attach or return the blob whole, so a fix
// that stripped `id` would be a correct-looking scope fix that silently
// emptied the id off every record. Arm Z asserts `id` SURVIVES on a site whose
// read returns `x.data` verbatim. Without it, "strip everything" satisfies
// arms A1-A10.
//
// NOT the column-shadowing half on sites 6 and 7. Their reads do
// `Object.assign({ id: x[cfg.idCol] }, x.data)` -- blob spread LAST -- so a
// payload `id` SHADOWS the real column. That is a real finding and it is
// reported by arm S as a MEASUREMENT rather than asserted, because which
// payload fields are real columns is a fact about each table and choosing the
// strip list is the converter's judgement, not this file's.
//
// ── ONE INJECTION POINT, never set on an ordinary run ───────────────────────
// SAIRN_B15_SD_DATA / SAIRN_B15_SD_STORE point the suite at a MUTATED COPY of
// the handler so the pre-fix counterfactual can be driven -- proving each arm
// goes GREEN once its site derives the blob through storedBlob(). An env var
// rather than an edit, because api/ is hank's and this batch touches none of
// it.

'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SD_DATA = process.env.SAIRN_B15_SD_DATA
  || path.join(ROOT, 'api/sd-data.js');
const SD_STORE = process.env.SAIRN_B15_SD_STORE
  || path.join(ROOT, 'api/_lib/sd-store.js');

let pass = 0;
const failed = [];
const notes = [];

function ok(l) { pass += 1; console.log('  ok   ' + l); }
function bad(l, why) {
  failed.push(l);
  console.log('  FAIL ' + l + (why ? '\n         ' + String(why).slice(0, 420) : ''));
}
function section(t) { console.log('\n' + t); }
function couldNotRun(why) {
  console.log('COULD NOT RUN: ' + why + ' Nothing was verified.');
  process.exit(3);
}

// ── PRECONDITIONS, each a third state and never folded into a pass ─────────
for (const p of [SD_DATA, SD_STORE]) {
  if (!fs.existsSync(p)) couldNotRun(p + ' does not exist.');
}
// EVERY MOCKED MODULE IS RESOLVED RELATIVE TO THE HANDLER UNDER TEST, not to
// the repo. When the counterfactual points SAIRN_B15_SD_DATA at a mutated COPY
// of the api/ tree, that copy requires ITS OWN `./_lib/license`, so a mock
// keyed on the real repo path does not apply to it -- the first spelling did
// exactly that and every site failed its PRECONDITION arm with
// "invalid licence", which would have read as "the conversion does not fix the
// arm". The handler's own directory is the only correct base.
const API_DIR = path.dirname(SD_DATA);
const BLOB = path.join(API_DIR, '_lib/blob.js');
if (!fs.existsSync(BLOB)) {
  couldNotRun('api/_lib/blob.js is absent, so the scope-key list cannot be read '
            + 'from the one place that owns it.');
}
// THE SCOPE KEYS ARE READ OUT OF blob.js, NEVER TYPED HERE. A second copy of
// another module's list is the defect this whole module exists to remove, and
// it would go stale the first time a fourth scope key is added -- silently,
// because an unasserted key reads exactly like an absent one.
const { NEVER_STORED } = require(BLOB);
if (!Array.isArray(NEVER_STORED) || NEVER_STORED.length < 3) {
  couldNotRun('api/_lib/blob.js NEVER_STORED is not a list of at least three '
            + 'keys (got ' + JSON.stringify(NEVER_STORED) + '), so this suite '
            + 'cannot assert the absence of the right things.');
}

const LIC_HASH = 'hash-of-the-b15-blob-scope-licence';
const LICENCE = require.resolve(path.join(API_DIR, '_lib/license.js'));
let LIC_APP = 'stonedesk';
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
  || ['b15', 'blob', 'scope', String(process.pid)].join('-');
const { signSessionToken } = require(path.join(API_DIR, '_lib/auth.js'));

// Every upstream POST is CAPTURED. The question this file asks is "what did the
// handler SEND", so the sent body is the measurement and the reply is only
// enough to let the branch finish.
let posts = [];
global.fetch = async (url, opts) => {
  const u = String(url);
  const method = (opts && opts.method) || 'GET';
  if (method === 'POST' || method === 'PATCH') {
    let body = null;
    try { body = JSON.parse(opts.body); } catch (e) { body = { UNPARSEABLE: String(opts.body).slice(0, 200) }; }
    posts.push({ url: u, body: body });
    return { ok: true, status: 200,
             json: async () => [Object.assign({}, body)] };
  }
  // The active-credential pre-gate runs before every branch and asks the app's
  // employee-auth table whether this credential is still active. An empty
  // answer is a 403 and would have made every arm below fail for the wrong
  // reason. Answered honestly -- an ACTIVE employee -- so the arms measure the
  // write branch and not the pre-gate.
  if (/_employee_auth\?/.test(u)) {
    return { ok: true, status: 200, json: async () => [{ active: true }] };
  }
  // business_profiles is read by writeMemory to stamp shop_id.
  if (/business_profiles\?/.test(u)) {
    return { ok: true, status: 200, json: async () => [{ shop_id: 'SHOP-REAL' }] };
  }
  return { ok: true, status: 200, json: async () => [] };
};

delete require.cache[require.resolve(SD_DATA)];
const handler = require(SD_DATA);
delete require.cache[require.resolve(SD_STORE)];
const store = require(SD_STORE);

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

// THE HEADER NAME IS READ OUT OF auth.js, NOT TYPED. The first spelling of
// this helper sent `x-sd-session` and every gated site failed its PRECONDITION
// arm with a 401/403 -- which is exactly the shape of a suite that reports ten
// defects and has measured none of them. tokenFromRequest() reads `x-sd-auth`.
const AUTH_SRC = fs.readFileSync(path.join(API_DIR, '_lib/auth.js'), 'utf8');
// ── COMMENT-STRIPPED BEFORE THE MATCH. 2026-10-19, cody b24, routed by b23's
//    green-but-worthless sweep as the LOWEST of its six confirmed ──────────
// THE CONCEPT: the session header name is EXTRACTED from the handler's own
// EXECUTABLE code, so this suite cannot type it and a comment cannot supply a
// wrong one.
//
// THE EXTRACTION ITSELF IS THE DISCIPLINE AND IS NOT THE DEFECT -- reading the
// name rather than typing it is precisely what stopped this suite reporting
// ten defects it had measured none of. The only hole was that `auth.js`'s own
// comments are in scope of the match, so a comment carrying this shape with a
// DIFFERENT header name could be picked up ahead of the real one and every
// gated site would then fail its precondition for a reason that is not about
// the blob. Stripping comments first closes that without touching the design.
const AUTH_CODE = AUTH_SRC
  .replace(/\/\*[\s\S]*?\*\//g, ' ')
  .replace(/\/\/[^\n]*/g, ' ');
const HDR_M = AUTH_CODE.match(/function tokenFromRequest\(req\)\s*\{\s*\n?\s*const h = req\.headers\[['"]([a-z0-9-]+)['"]\]/);
if (!HDR_M) {
  couldNotRun('the session header could not be read out of '
            + 'api/_lib/auth.js tokenFromRequest(), so this suite cannot '
            + 'present a session and every gated site would fail its '
            + 'precondition for a reason that is not about the blob.');
}
const SESSION_HEADER = HDR_M[1];

function token(role, app) {
  return signSessionToken({ app: app || 'stonedesk', employee_id: 'E1',
                            role: role, license_hash: LIC_HASH });
}

async function write(resource, payload, opts) {
  posts = [];
  const o = opts || {};
  LIC_APP = o.app || 'stonedesk';
  const headers = { authorization: 'Bearer testkey' };
  // The session must be signed for the SAME app the licence names, or
  // verifySessionToken refuses it and the arm measures a cross-app refusal.
  if (o.role) headers[SESSION_HEADER] = token(o.role, LIC_APP);
  const req = { method: 'POST', headers: headers,
                body: { action: 'write', resource: resource, payload: payload } };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

// THE FORGED PAYLOAD. Shaped like the real thing: a forged tenant id and a
// forged app id riding in beside ordinary fields. Built from NEVER_STORED so a
// fourth scope key is forged the day it is added.
function forged(extra) {
  const p = Object.assign({ id: 'REC-1', name: 'A record' }, extra || {});
  NEVER_STORED.forEach((k) => { p[k] = 'FORGED_' + k.toUpperCase(); });
  return p;
}

function storedData() {
  const p = posts.filter((x) => x.body && x.body.data !== undefined);
  return p.length ? p[p.length - 1].body.data : null;
}

// ── THE TEN SITES, in the order docs/...-routed-to-hank.md lists them ──────
// Each entry carries ONLY what driving it needs. The branch/table/read triples
// live in the routing document and are not duplicated here.
const SITES = [
  { n: 2,  site: 'api/sd-data.js:2326',  resource: 'profile',
    table: 'business_profiles', payload: () => forged(),
    opts: { role: 'owner' } },
  { n: 3,  site: 'api/sd-data.js:3663',  resource: 'slabs',
    table: 'sd_slabs', payload: () => forged(), opts: { role: 'owner' },
    idMustSurvive: true },
  { n: 4,  site: 'api/sd-data.js:3718',  resource: 'locations',
    table: 'sd_locations', payload: () => forged({ name: 'Yard One' }),
    opts: { role: 'owner' } },
  { n: 5,  site: 'api/sd-data.js:3755',  resource: 'remnants',
    table: 'sd_remnants', payload: () => forged(), opts: { role: 'owner' } },
  { n: 6,  site: 'api/sd-data.js:4116',  resource: 'sd_blocks',
    table: 'sd_blocks', payload: () => forged(), opts: { role: 'owner' },
    dispatcher: 'SD_LINEAGE', shadows: 'id' },
  { n: 6,  site: 'api/sd-data.js:4116',  resource: 'sd_bundles',
    table: 'sd_bundles', payload: () => forged(), opts: { role: 'owner' },
    dispatcher: 'SD_LINEAGE', shadows: 'id' },
  { n: 6,  site: 'api/sd-data.js:4116',  resource: 'sd_slab_history',
    table: 'sd_slab_history', payload: () => forged(), opts: { role: 'owner' },
    dispatcher: 'SD_LINEAGE', shadows: 'id' },
  { n: 7,  site: 'api/sd-data.js:4175',  resource: 'sd_hr_employees',
    table: 'sd_hr_employees', payload: () => forged(), opts: { role: 'owner' },
    dispatcher: 'SD_HR', shadows: 'id', person: true },
  { n: 7,  site: 'api/sd-data.js:4175',  resource: 'sd_hr_certs',
    table: 'sd_hr_certs', payload: () => forged(), opts: { role: 'owner' },
    dispatcher: 'SD_HR', shadows: 'id', person: true },
  { n: 8,  site: 'api/sd-data.js:4913',  resource: 'properties',
    table: 'grd_properties', payload: () => forged(),
    opts: { app: 'sairngrounds', role: 'owner' } },
  { n: 9,  site: 'api/sd-data.js:4934',  resource: 'jobs',
    table: 'grd_jobs', payload: () => forged({ property_id: 'PR-1' }),
    opts: { app: 'sairngrounds', role: 'owner' } },
  { n: 10, site: 'api/sd-data.js:4955',  resource: 'quotes',
    table: 'grd_quotes', payload: () => forged({ property_id: 'PR-1' }),
    opts: { app: 'sairngrounds', role: 'owner' } },
];

(async function main() {
  console.log('THE TEN ROUTED BLOB SITES, DRIVEN -- criteria 2026-10-15.1');
  console.log('scope keys read from api/_lib/blob.js: '
            + JSON.stringify(NEVER_STORED));
  console.log('handler: ' + path.relative(ROOT, SD_DATA).replace(/\\/g, '/'));
  console.log('store  : ' + path.relative(ROOT, SD_STORE).replace(/\\/g, '/'));

  // ── SITE 1 IS A LIBRARY FUNCTION, not a resource branch ────────────────
  // api/_lib/sd-store.js writeMemory(lic, memory) is reached through
  // api/sd-agent.js:173, not through a sd-data resource. Called directly, with
  // the same captured-POST measurement.
  section('SITE 1 -- api/_lib/sd-store.js:203  writeMemory() -> ai_memories');
  posts = [];
  let reached1 = true;
  try {
    await store.writeMemory({ license_hash: LIC_HASH, app_id: 'stonedesk' },
                            forged());
  } catch (e) {
    reached1 = false;
    bad('A1 PRECONDITION. writeMemory() must reach an upstream POST at all',
        'threw: ' + (e && e.message));
  }
  if (reached1) {
    const d1 = storedData();
    if (d1 === null) {
      bad('A1 PRECONDITION. writeMemory() must POST a body carrying `data`',
          'posts: ' + JSON.stringify(posts).slice(0, 300));
    } else {
      ok('A1 PRECONDITION. writeMemory() reaches upstream and posts a `data` '
         + 'blob, so the arm below measures a real write');
      const leaked1 = NEVER_STORED.filter((k) => d1[k] !== undefined);
      if (leaked1.length === 0) {
        ok('A1 (site 1, ai_memories): no scope key reaches `data`');
      } else {
        bad('A1 (site 1, api/_lib/sd-store.js:203 -> ai_memories): the scope '
            + 'key(s) ' + JSON.stringify(leaked1) + ' must not reach `data`',
            'data=' + JSON.stringify(d1).slice(0, 300)
            + '\n         CONVERT: data: storedBlob(payload, [...]) -- and note '
            + 'shop_id IS a column on this write, stamped from business_profiles, '
            + 'and readMemories() at :175 does NOT re-merge it, so a payload '
            + 'shop_id is stored and silently contradicts the row\'s own column.');
      }
      if (d1 && d1.shop_id !== undefined) {
        notes.push('site 1: payload `shop_id` reached `data` ('
                   + JSON.stringify(d1.shop_id) + ') while the row\'s own '
                   + 'shop_id column is stamped from business_profiles');
      }
    }
  }

  // ── SITES 2-10 ─────────────────────────────────────────────────────────
  section('SITES 2-10 -- the api/sd-data.js write branches');
  let reached = 0;
  for (const s of SITES) {
    const label = 'site ' + s.n + ' ' + s.resource;
    const r = await write(s.resource, s.payload(), s.opts);
    const d = storedData();
    if (r.statusCode !== 200 || d === null) {
      bad('A' + s.n + ' PRECONDITION (' + label + '): the write must reach '
          + 'upstream with a `data` blob, or the arm measures a refusal',
          'status=' + r.statusCode + ' body=' + JSON.stringify(r.body).slice(0, 220));
      continue;
    }
    reached += 1;
    const leaked = NEVER_STORED.filter((k) => d[k] !== undefined);
    if (leaked.length === 0) {
      ok('A' + s.n + ' (' + label + ' -> ' + s.table + '): no scope key reaches `data`');
    } else {
      bad('A' + s.n + ' (' + label + ', ' + s.site + ' -> ' + s.table + '): the '
          + 'scope key(s) ' + JSON.stringify(leaked) + ' must not reach `data`',
          'data=' + JSON.stringify(d).slice(0, 240)
          + (s.dispatcher
             ? '\n         THIS IS THE ' + s.dispatcher + ' DISPATCHER: one edit '
               + 'covers every resource it serves.'
             : '')
          + (s.person ? '\n         PERSON DATA -- re-qualify the tier before '
                      + 'converting.' : ''));
    }
    // THE MEASUREMENT, not an assertion: which mapped column a payload copy
    // would shadow on read. Reported so the converter has the list without
    // this file choosing it.
    if (s.shadows && d[s.shadows] !== undefined) {
      notes.push(label + ': payload `' + s.shadows + '` reached `data`, and that '
                 + 'read spreads the blob LAST, so it shadows the real column');
    }
    // ── ARM Z, AND THE `else` IT WAS MISSING (2026-10-15, fourth b25 F1) ──
    // This read `if (d.id !== undefined && s.idMustSurvive)` and had NO else,
    // so the one state the arm exists to catch -- `id` absent -- emitted
    // neither `ok` nor `bad`. IT DID NOT GO RED; IT DISAPPEARED. fourth
    // ablated it on a copy and measured BASELINE exit 0 / 16 passed / arm Z
    // present 1 against ABLATED exit 0 / 15 passed / arm Z present 0: a fix
    // that stripped `id` off every blob would have been exit 0 both ways.
    // THE PREDICATE SPLIT IS THE FIX: `s.idMustSurvive` selects the
    // POPULATION, `d.id !== undefined` is the ASSERTION. Folding the two into
    // one condition is what made a failing assertion indistinguishable from a
    // site the arm does not apply to.
    if (s.idMustSurvive) {
      if (d.id !== undefined) {
        ok('Z (' + label + '): `id` SURVIVES into `data`, which this table\'s '
           + 'read requires -- it returns `x.data` whole. Without this arm, '
           + '"strip everything" would satisfy every A arm above');
      } else {
        bad('Z (' + label + '): `id` MUST SURVIVE into `data` and it is ABSENT. '
            + 'This table\'s read returns `x.data` whole, so every record this '
            + 'branch writes now has no id -- a correct-looking scope fix that '
            + 'emptied the id off the row',
            'data=' + JSON.stringify(d).slice(0, 240));
      }
    }
  }

  if (reached === 0) {
    couldNotRun('not one of sites 2-10 reached an upstream POST, so nothing was '
              + 'measured. The harness, not the handler, is what failed.');
  }

  // ── THE CONTROL THAT STOPS THIS SUITE PASSING VACUOUSLY ────────────────
  section('CONTROL -- the arms can tell a converted site from an unconverted one');
  // A site that ALREADY derives its blob through storedBlob must pass. Without
  // this, every A arm failing would be indistinguishable from a harness that
  // cannot read `data` at all. sdn_projects is converted (tests/sd_data_sdn_blob_scope.js
  // drives it) and is used here as the positive end of the pair.
  const rc = await write('sdn_projects', forged(),
                         { app: 'sairndesign', role: 'owner' });
  const dc = storedData();
  // ── READ OFF failed.length, NOT TYPED (2026-10-15, fourth b25) ──────────
  // This message said "so the ten failures above" as a literal, and hank's
  // conversion landed two minutes before this suite was committed -- so it
  // printed "the ten failures above" on a run with ZERO failures above, in
  // the one arm whose whole job is to make the count above readable. A
  // control that describes the result it is qualifying has to measure it.
  const nAbove = failed.length;
  const aboveTxt = nAbove === 0
    ? 'and there are NO failures above, so the A arms\' greens are '
      + 'measurements rather than a harness that cannot see a blob at all'
    : 'so the ' + nAbove + ' failure(s) above are about those sites and not '
      + 'about this harness being unable to see a clean blob';
  if (rc.statusCode === 200 && dc !== null) {
    const leakedC = NEVER_STORED.filter((k) => dc[k] !== undefined);
    if (leakedC.length === 0) {
      ok('CONTROL: an ALREADY-CONVERTED branch (sdn_projects) passes the same '
         + 'arm, ' + aboveTxt);
    } else {
      bad('CONTROL: the already-converted sdn_projects branch leaked '
          + JSON.stringify(leakedC) + ', which means this harness or that '
          + 'branch regressed -- the ten arms above cannot be read until this '
          + 'is explained', 'data=' + JSON.stringify(dc).slice(0, 240));
    }
  } else {
    bad('CONTROL: the already-converted sdn_projects branch must reach upstream, '
        + 'or the positive end of the pair is missing',
        'status=' + rc.statusCode + ' body=' + JSON.stringify(rc.body).slice(0, 220));
  }

  if (notes.length) {
    section('MEASURED, NOT ASSERTED -- the column-shadowing list for the converter');
    notes.forEach((n) => console.log('  * ' + n));
    console.log('  Which payload fields are real columns is a fact about each '
              + 'table.\n  This suite reports them; it does not choose the strip '
              + 'list.');
  }

  console.log('\n' + pass + ' passed, ' + failed.length + ' failed');
  if (failed.length) {
    console.log(failed.length + ' ARM(S) FAILED:');
    failed.forEach((f) => console.log('  - ' + f));
    console.log('\nTHIS SUITE IS GREEN AT HEAD (16 passed, 0 failed, 2026-10-15) '
              + 'and its row is in docs/known-red-suites.json `recovered`. ANY '
              + 'failure above is NEW -- an A arm means a conversion was '
              + 'reverted or a new scope key was added to api/_lib/blob.js '
              + 'NEVER_STORED and a branch does not derive it; arm Z means a '
              + 'scope fix stripped `id`; a PRECONDITION or CONTROL arm means '
              + 'the measurement, not the handler.');
    process.exit(1);
  }
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
