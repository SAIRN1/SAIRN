// api/b23-iolta-attestation.test.js
//
// Run:  node api/b23-iolta-attestation.test.js
//
// THE IOLTA RECONCILIATION ATTESTATION, driven end to end, plus the ablations
// that prove the single-signer gate is load-bearing.
//
// CONCEPT UNDER TEST (docs/2026-10-19-hank-b23-notes.md item 3):
//   A completed three-way reconciliation becomes an ATTESTED record only when
//   a bar-admitted person signs a hash of the exact comparison that was run; a
//   firm with EXACTLY ONE active owner/attorney may switch on a per-firm
//   single-signer setting and attest alone, and every attestation taken that
//   way is stored as signer_mode 'single'.
//
// ── THE TWO PROPERTIES THIS SUITE EXISTS FOR ─────────────────────────────
//   1. A STALE SETTING AUTHORISES NOTHING. The roster is re-counted on every
//      single-signer attestation, so a firm that switched the setting on as a
//      solo and later hired a second attorney loses the route without anyone
//      touching the setting. Arms E3/E4 and ablation I2.
//   2. THE RECORD NEVER CLAIMS TWO PEOPLE LOOKED WHEN ONE DID. `signer_mode`
//      is stored, the database CHECK ties it to whether the two names differ,
//      and on the dual path the ATTESTER IS THE COUNTERSIGNER AND NOT THE
//      CALLER. Arms F1/F2 and ablation I3.
//
// ── WHAT THIS DOES NOT DO ────────────────────────────────────────────────
// It touches no database and makes no live request. The handler arms drive the
// real route with a recorded PostgREST stand-in, so they prove the route
// answers before any insert -- not that the deployed endpoint does.
// sql/sairnlaw_trust_attestations.sql HAS NOT BEEN RUN, so in production every
// write answers 503 NOT_PROVISIONED today. Arm G5 asserts exactly that,
// because "it refuses until the SQL is run" and "it writes unattested until
// the SQL is run" are opposite facts and only one of them is safe.
//
// The SQL file's own CHECK constraints are verified by the four negative
// inserts and one positive control written into that file, NOT here -- a
// JavaScript suite cannot drive a Postgres constraint, and pretending
// otherwise would be the shape of a check that tests nothing.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b23', 'attest', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { signSessionToken } = require('./_lib/auth');
const cs = require('./_lib/countersign');
const lawRoles = require('./_lib/law-roles');
const attest = require('./_lib/law-attest');

const ATTEST_LIB_SRC = path.join(__dirname, '_lib', 'law-attest.js');
const ROUTE_SRC = path.join(__dirname, 'law-attest.js');
const SQL_SRC = path.join(__dirname, '..', 'sql', 'sairnlaw_trust_attestations.sql');
const SELF = __filename;
const ARMS_ONLY = process.env.B23_ATTEST_ARMS_ONLY === '1';
const HASH = 'b23-attest-hash';
const KEY = 'KEY-FOR-' + HASH;

// Declares itself a placeholder so tools/redaction_check.py's
// generic_credential_assignment pattern reads it as one -- the same reason
// api/b18-countersign-lock.test.js spells its fixture this way.
const FIXTURE_TOKEN = 'attest-token-placeholder';

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 700));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 700));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

// ── THE COMPARISON FIXTURES ─────────────────────────────────────────────────
// AGREES with three equal legs, which is the only AGREES the validator and the
// database both accept.
const CMP = Object.freeze({
  bank_balance_cents: 1250000,
  ledger_balance_cents: 1250000,
  client_subledger_total_cents: 1250000,
  bank_as_of: '2026-10-01',
  ledger_as_of: '2026-10-01',
  subledger_as_of: '2026-10-01',
  verdict: 'AGREES'
});
// ONE CENT APART, on purpose. The interesting content-binding failure is never
// a big one: a token signed for CMP must not be spendable on this.
const CMP_ONE_CENT = Object.assign({}, CMP, {
  bank_balance_cents: 1250001, verdict: 'DISAGREES'
});
// What the server actually hashes is the NORMALISED object, which carries
// `negative_balances: []`. A token built over the raw fixture would not match
// and every dual arm would pass for the wrong reason.
function normalised(c) {
  const n = attest.normaliseComparison(c);
  if (n.refused) throw new Error('fixture does not normalise: ' + n.refused.code);
  return n.comparison;
}

// ── THE HANDLER HARNESS ─────────────────────────────────────────────────────
function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function eCode(res) { return (res.body && res.body.error && res.body.error.code) || ''; }
function eMsg(res) { return (res.body && res.body.error && res.body.error.message) || ''; }

/**
 * opts.settingOn        the stored setting's value (default: absent row = off)
 * opts.settingMissing   the settings table does not exist (PostgREST shape)
 * opts.barAdmitted      how many active owner/attorney rows the count finds
 * opts.rosterUnreadable the count query fails -- the could-not-tell case
 * opts.callerRole       the role the EMPLOYEE ROW carries (not the token)
 * opts.callerInactive   the caller's employee row is absent/inactive
 * opts.tokenRow         the countersignature row the lookup finds
 * opts.recordMissing    the attestation table does not exist
 * opts.recordDuplicate  the insert hits the unique constraint
 */
function pgMock(calls, opts) {
  opts = opts || {};
  const missing = () => ({ ok: false, status: 404,
    json: async () => ({ code: 'PGRST205',
      message: 'Could not find the table in the schema cache' }) });
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });

    if (/sairnlaw_firm_settings/.test(u)) {
      if (opts.settingMissing) return missing();
      if (method === 'POST') {
        return { ok: true, status: 200, json: async () => [JSON.parse(init.body)] };
      }
      if (opts.settingOn === undefined) {
        return { ok: true, status: 200, json: async () => [] };   // absent = off
      }
      return { ok: true, status: 200, json: async () => [{
        value: opts.settingOn, updated_by: 'alice', updated_role: 'owner',
        updated_at: '2026-10-19T00:00:00Z', bar_admitted_count_at_set: 1 }] };
    }

    if (/sairnlaw_trust_attestations/.test(u)) {
      if (opts.recordMissing) return missing();
      if (method === 'POST') {
        if (opts.recordDuplicate) {
          return { ok: false, status: 409, json: async () => ({ code: '23505',
            message: 'duplicate key value violates unique constraint' }) };
        }
        return { ok: true, status: 200, json: async () => [JSON.parse(init.body)] };
      }
      return { ok: true, status: 200, json: async () => (opts.records || []) };
    }

    if (/sairnlaw_countersign_tokens/.test(u)) {
      if (method === 'PATCH') {
        return { ok: true, status: 200,
                 json: async () => (opts.tokenRow ? [{ id: 'tok-1' }] : []) };
      }
      return { ok: true, status: 200,
               json: async () => (opts.tokenRow ? [opts.tokenRow] : []) };
    }

    if (/sairnlaw_employee_auth/.test(u)) {
      // THE COUNT QUERY AND THE CALLER QUERY ARE TOLD APART BY `role=in.(`.
      // Matching only on the table name would make one opts flag drive both,
      // and `rosterUnreadable` would then also break the caller lookup -- so
      // a 503 arm would be measuring a failed session read instead.
      if (/role=in\./.test(u)) {
        if (opts.rosterUnreadable) {
          return { ok: false, status: 500, json: async () => ({ message: 'boom' }) };
        }
        const n = opts.barAdmitted === undefined ? 1 : opts.barAdmitted;
        return { ok: true, status: 200,
                 json: async () => Array.from({ length: n },
                   (_, i) => ({ employee_id: 'bar-' + i })) };
      }
      const m = u.match(/employee_id=eq\.([^&]+)/);
      const who = m ? decodeURIComponent(m[1]) : 'alice';
      if (opts.callerInactive) return { ok: true, status: 200, json: async () => [] };
      if (opts.inactive && opts.inactive.indexOf(who) !== -1) {
        return { ok: true, status: 200, json: async () => [] };
      }
      return { ok: true, status: 200, json: async () => [
        { employee_id: who, role: opts.callerRole || 'attorney' }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

function loadRoute(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnlaw' })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./law-attest.js')];
  delete require.cache[require.resolve('./_lib/law-attest.js')];
  delete require.cache[require.resolve('./_lib/countersign-endpoint')];
  return require('./law-attest.js');
}

async function call(body, opts) {
  opts = opts || {};
  const calls = [];
  const h = loadRoute(pgMock(calls, opts));
  const res = mockRes();
  const headers = { authorization: 'Bearer ' + KEY };
  if (!opts.noSession) {
    headers['x-sd-auth'] = signSessionToken({
      app: 'sairnlaw', employee_id: opts.callerId || 'alice',
      role: opts.tokenRole || opts.callerRole || 'attorney', license_hash: HASH });
  }
  if (opts.tokenRow || opts.sendToken) headers['x-law-countersign'] = FIXTURE_TOKEN;
  await h({ method: 'POST', headers: headers, body: body }, res);
  return { res: res, calls: calls };
}

function tokenRowFor(comparison, over) {
  return Object.assign({
    id: 'tok-1',
    resource: attest.ATTEST_RESOURCE,
    content_hash: cs.contentHash(attest.ATTEST_RESOURCE, normalised(comparison)),
    prepared_by: 'bob', prepared_role: 'paralegal',
    countersign_employee_id: 'alice', countersign_role: 'attorney',
    countersigned_at: new Date().toISOString(),
    spent_at: null,
    expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString()
  }, over || {});
}

// The row the mock echoed back from the insert, so arms assert WHAT WAS
// WRITTEN rather than what the response summarised. A response can be right
// about a row that was wrong.
function writtenRow(calls) {
  const w = calls.filter((c) => c.method === 'POST'
    && /sairnlaw_trust_attestations/.test(c.url));
  return w.length ? w : null;
}
function insertedBody(calls) {
  const h = loadRouteInsert(calls);
  return h;
}
function loadRouteInsert(calls) {
  // The mock records url+method only; the body is read back from the response
  // the route returns, plus the POST presence here. Arms that need the exact
  // row use `captured` below instead.
  return calls;
}

// A pgMock wrapper that keeps the exact insert body, because the row is the
// deliverable and asserting the response alone would let a correct-looking
// answer sit on top of a wrong row.
function capturingMock(calls, opts, box) {
  const inner = pgMock(calls, opts);
  return async function (url, init) {
    if (String(url).indexOf('sairnlaw_trust_attestations') !== -1
        && init && init.method === 'POST') {
      box.row = JSON.parse(init.body);
    }
    return inner(url, init);
  };
}
async function callCapturing(body, opts) {
  opts = opts || {};
  const calls = [];
  const box = {};
  const h = loadRoute(capturingMock(calls, opts, box));
  const res = mockRes();
  const headers = { authorization: 'Bearer ' + KEY };
  if (!opts.noSession) {
    headers['x-sd-auth'] = signSessionToken({
      app: 'sairnlaw', employee_id: opts.callerId || 'alice',
      role: opts.tokenRole || opts.callerRole || 'attorney', license_hash: HASH });
  }
  if (opts.tokenRow || opts.sendToken) headers['x-law-countersign'] = FIXTURE_TOKEN;
  await h({ method: 'POST', headers: headers, body: body }, res);
  return { res: res, calls: calls, row: box.row };
}

const ATTEST = (over) => Object.assign(
  { action: 'attest', attestation_id: 'AT-1', comparison: CMP }, over || {});

// ── THE ABLATION HARNESS (api/b18-countersign-lock.test.js's shape) ────────
function runSuite(file, armsOnly) {
  const env = armsOnly
    ? Object.assign({}, process.env, { B23_ATTEST_ARMS_ONLY: '1' })
    : process.env;
  try {
    const out = execFileSync(process.execPath, [file], {
      env: env, encoding: 'utf8', stdio: 'pipe' });
    return { exit: 0, out: String(out || '') };
  } catch (e) {
    return { exit: typeof e.status === 'number' ? e.status : -1,
             out: String((e && e.stdout) || '') + String((e && e.stderr) || '') };
  }
}
function failedArms(out) {
  const m = String(out || '').match(/FAILED:\s*(.+)/);
  return m ? m[1].trim().split(/\s*,\s*/).filter(Boolean) : [];
}
function ablate(file, find, replace) {
  const original = fs.readFileSync(file, 'utf8');
  const hits = original.split(find).length - 1;
  if (hits !== 1) {
    return { ok: false, why: 'the ablation anchor matched ' + hits + ' time(s) in '
      + path.basename(file) + ', not exactly 1 -- REFUSING to mutate. FIX THE '
      + 'ANCHOR, do not delete the arm. Anchor: ' + find.slice(0, 110) };
  }
  try {
    fs.writeFileSync(file, original.replace(find, replace), 'utf8');
    const mine = runSuite(SELF, true);
    return { ok: true, exit: mine.exit, arms: failedArms(mine.out), out: mine.out };
  } finally {
    fs.writeFileSync(file, original, 'utf8');
  }
}

(async () => {
  console.log('b23 IOLTA reconciliation attestation'
            + (ARMS_ONLY ? '  [ARMS ONLY]' : '') + '\n');

  // ══ A. THE MODULE SAYS WHAT WAS BUILT, AND WHAT WAS DELIBERATELY NOT ════
  section('A. the policy module');
  {
    const att = lawRoles.LAW_RECONCILE_ATTESTATION;
    is(att.required_by_rule === true && att.implemented === true,
       'A1. LAW_RECONCILE_ATTESTATION now says the review is required AND is '
     + 'implemented. This is the flip that makes arm A1 of '
     + 'api/b19-iolta-reconcile-carveout.test.js RED -- deliberately; that arm '
     + 'asserted `implemented === false` and is to be RE-AIMED, not deleted',
       JSON.stringify({ required: att.required_by_rule, implemented: att.implemented }));
    is(typeof att.inert_until === 'string' && /NOT_PROVISIONED/.test(att.inert_until)
       && /18804/.test(att.inert_until),
       'A2. ...and `implemented` does NOT mean usable: inert_until names the '
     + 'unrun SQL and the owner-only gate, because armed-in-code and '
     + 'inert-in-the-database are different facts',
       att.inert_until);
    is(!lawRoles.LAW_RECONCILE_ROLES.paralegal
       && typeof att.delegation_reopens_when === 'string',
       'A3. `paralegal` is STILL OFF LAW_RECONCILE_ROLES and the condition for '
     + 'restoring it is written down. Granting it now would be inert today and '
     + 'go live the day the gate is wired -- possibly before the SQL is run, '
     + 'which is the state b20 withdrew it to avoid',
       Object.keys(lawRoles.LAW_RECONCILE_ROLES).join(',') + ' | '
       + String(att.delegation_reopens_when).slice(0, 80));
    is(Object.isFrozen(att), 'A4. and it is still frozen',
       'frozen=' + Object.isFrozen(att));
  }

  // ══ B. THE PROFILE ══════════════════════════════════════════════════════
  section('B. the countersignature profile');
  {
    const route = require('./law-attest.js');
    const P = route.PROFILE;
    is(P.lockedResources[attest.ATTEST_RESOURCE] === cs.MODE_ALWAYS,
       'B1. law_trust_attestation is MODE_ALWAYS. MODE_PREPARED_ONLY would let '
     + 'an attorney who ran the reconciliation attest their own work with no '
     + 'second party and no token -- the shape b20 withdrew a grant to avoid',
       String(P.lockedResources[attest.ATTEST_RESOURCE]));
    is(P.signerRoles === lawRoles.LAW_BAR_ADMITTED_ROLES,
       'B2. signerRoles is the SAME OBJECT as LAW_BAR_ADMITTED_ROLES, not a '
     + 'copy -- so the licensure tier cannot drift between the access-control '
     + 'surface and the IOLTA record',
       'same object=' + (P.signerRoles === lawRoles.LAW_BAR_ADMITTED_ROLES));
    is(P.preparerRoles.paralegal === true && P.preparerRoles.attorney === true
       && P.preparerRoles.owner === true,
       'B3. all three of owner/attorney/paralegal may PREPARE. A profile with '
     + 'only { paralegal } -- which is what reusing api/law-countersign.js '
     + 'would have given -- would stop an attorney staging an attestation of '
     + 'their own comparison, which is the solo case',
       Object.keys(P.preparerRoles).join(','));
    is(P.tokenTable === 'sairnlaw_countersign_tokens',
       'B4. the token table is REUSED. Measured: that table\'s `resource` '
     + 'column has no CHECK on its value and Michael has already run that '
     + 'schema, so the two-signer path needs no new SQL',
       P.tokenTable);
    const lawCs = require('./law-countersign.js');
    is(Object.keys(lawCs.PROFILE.lockedResources).join(',') === 'law_trusttx'
       && Object.keys(lawRoles.LAW_TRUST_TWO_STAGE).join(',') === 'law_trusttx',
       'B5. api/law-countersign.js\'s locked list is UNCHANGED and still equals '
     + 'LAW_TRUST_TWO_STAGE -- so arm E3 of api/b18-countersign-lock.test.js '
     + 'stays GREEN. The design note expected that arm to need re-aiming; '
     + 'building a second profile instead means it does not',
       Object.keys(lawCs.PROFILE.lockedResources).join(','));
  }

  // ══ C. THE COMPARISON VALIDATOR ═════════════════════════════════════════
  section('C. normaliseComparison -- what a signature is allowed to cover');
  {
    const good = attest.normaliseComparison(CMP);
    is(!good.refused && good.comparison.negative_balances.length === 0,
       'C1. a valid comparison normalises, and an ABSENT negative_balances '
     + 'becomes [] -- an absent key and a cannot-tell read the same to a '
     + 'consumer and only one is honest',
       JSON.stringify(good.refused || good.comparison.negative_balances));
    const flt = attest.normaliseComparison(
      Object.assign({}, CMP, { bank_balance_cents: 12500.5 }));
    is(flt.refused && flt.refused.code === 'CENTS_NOT_INTEGER',
       'C2. a FLOAT leg is refused, not rounded. A rounding difference here '
     + 'could manufacture the discrepancy the reconciliation exists to settle',
       JSON.stringify(flt.refused || flt.comparison));
    const str = attest.normaliseComparison(
      Object.assign({}, CMP, { ledger_balance_cents: '1250000' }));
    is(str.refused && str.refused.code === 'CENTS_NOT_INTEGER',
       'C3. a STRING leg is refused rather than coerced',
       JSON.stringify(str.refused || str.comparison));
    const unk = attest.normaliseComparison(
      Object.assign({}, CMP, { note: 'everything is fine' }));
    is(unk.refused && unk.refused.code === 'COMPARISON_UNKNOWN_FIELD',
       'C4. an UNKNOWN field is REFUSED, not dropped. A value the signer saw '
     + 'and the record does not carry is a signature over something other '
     + 'than what was shown',
       JSON.stringify(unk.refused || unk.comparison));
    const nod = attest.normaliseComparison(
      Object.assign({}, CMP, { bank_as_of: 'October 2026' }));
    is(nod.refused && nod.refused.code === 'AS_OF_DATE_REQUIRED',
       'C5. a leg with no usable as-of date is refused -- a balance without one '
     + 'is a number, not a leg of a reconciliation',
       JSON.stringify(nod.refused || nod.comparison));
    const bv = attest.normaliseComparison(
      Object.assign({}, CMP, { verdict: 'FINE' }));
    is(bv.refused && bv.refused.code === 'VERDICT_UNKNOWN',
       'C6. an unknown verdict is refused', JSON.stringify(bv.refused || bv.comparison));
    const inc = attest.normaliseComparison(
      Object.assign({}, CMP, { bank_balance_cents: CMP.bank_balance_cents + 1 }));
    is(inc.refused && inc.refused.code === 'VERDICT_INCONSISTENT',
       'C7. AGREES with legs ONE CENT apart is refused. This checks the record '
     + 'against ITSELF -- a verdict that contradicts the figures printed beside '
     + 'it is the shape a fabricated verdict takes. It says nothing about '
     + 'whether the figures are right, and nothing here could',
       JSON.stringify(inc.refused || inc.comparison));
    const disagrees = attest.normaliseComparison(
      Object.assign({}, CMP, { bank_balance_cents: CMP.bank_balance_cents + 1,
                               verdict: 'DISAGREES' }));
    is(!disagrees.refused,
       'C8. THE NEGATIVE CONTROL for C7: the same unequal legs with verdict '
     + 'DISAGREES are ACCEPTED. Without this, C7 is equally consistent with '
     + '"the consistency check works" and "unequal legs are refused outright", '
     + 'which would make a real discrepancy unrecordable',
       JSON.stringify(disagrees.refused || 'accepted'));
    const posneg = attest.normaliseComparison(
      Object.assign({}, CMP, { negative_balances: [{ client_id: 'C1', cents: 5 }] }));
    is(posneg.refused && posneg.refused.code === 'NEGATIVE_BALANCES_SHAPE',
       'C9. a NON-negative entry in negative_balances is refused -- a '
     + 'contradiction, not a rounding question',
       JSON.stringify(posneg.refused || posneg.comparison));
  }

  // ══ C10. THE CROSS-FILE CHECK ═══════════════════════════════════════════
  // The SQL carries a SECOND COPY of LAW_BAR_ADMITTED_ROLES and of
  // SETTING_KEY. Two copies drift, and the day they drift the constraint
  // refuses a role the app allows -- in Supabase, at a firm, during a bar
  // examination. This fails here instead.
  section('C10. the SQL\'s literals still match the modules');
  {
    let sql = null;
    try { sql = fs.readFileSync(SQL_SRC, 'utf8'); } catch (e) { sql = null; }
    if (!sql) {
      cannot('C10. sql/sairnlaw_trust_attestations.sql could not be read, so '
           + 'the cross-file check DID NOT RUN', String(SQL_SRC));
    } else {
      // AS A SET, NOT AS A SORTED STRING. The first draft compared
      // `Object.keys(...).sort()` against the SQL's literal order and failed on
      // a file that was correct -- the constraint reads ('owner','attorney')
      // because that is the order the policy is written in. An arm that fails
      // on spelling rather than on meaning is a false positive somebody
      // eventually silences.
      const m = sql.match(/attested_role in \(([^)]*)\)/);
      const inSql = m ? m[1].split(',').map((s) => s.trim().replace(/^'|'$/g, '')).sort()
                      : null;
      const roles = Object.keys(lawRoles.LAW_BAR_ADMITTED_ROLES).sort();
      is(inSql && inSql.join(',') === roles.join(','),
         'C10a. the attester CHECK lists exactly LAW_BAR_ADMITTED_ROLES, '
       + 'compared as a SET. If this fails THE SQL IS THE STALE COPY and the '
       + 'constraint disagrees with the app about who may attest',
         'sql=' + (inSql ? inSql.join(',') : 'NOT FOUND') + ' module=' + roles.join(','));
      is(sql.indexOf("setting_key in ('" + attest.SETTING_KEY + "')") !== -1,
         'C10b. the settings CHECK lists exactly SETTING_KEY',
         attest.SETTING_KEY);
      is(/no update/i.test(sql)
         && /grant select, insert on public\.sairnlaw_trust_attestations/.test(sql)
         && !/grant[^;]*update[^;]*sairnlaw_trust_attestations/i.test(sql),
         'C10c. the record table is granted SELECT and INSERT and NOT UPDATE '
       + 'or DELETE -- an attestation is never amended; a correction is a new '
       + 'row',
         'grants line present=' + /grant select, insert on public\.sairnlaw_trust_attestations/.test(sql));
      is(/revoke all on public\.sairnlaw_trust_attestations from service_role/.test(sql),
         'C10d. and the REVOKE ALL comes first, so the table does not inherit '
       + 'TRUNCATE from the platform default ACL -- which here would erase '
       + 'every attestation a firm has ever recorded, in one statement',
         'present');
    }
  }

  // ══ D. SINGLE-SIGNER ELIGIBILITY, THE PURE DECISION ═════════════════════
  section('D. singleSignerEligible -- exactly one, and three ways of not being one');
  {
    is(attest.singleSignerEligible(1).eligible === true,
       'D1. exactly one active bar-admitted employee is eligible', '1');
    const two = attest.singleSignerEligible(2);
    is(two.refused && two.refused.code === 'SINGLE_SIGNER_NOT_SOLO',
       'D2. TWO is refused -- a firm that can staff a second signer uses one',
       JSON.stringify(two.refused || two));
    const zero = attest.singleSignerEligible(0);
    is(zero.refused && zero.refused.code === 'SINGLE_SIGNER_NO_ATTORNEY',
       'D3. ZERO gets its OWN refusal, not NOT_SOLO. "no attorney at all" and '
     + '"more than one" are different problems with different fixes',
       JSON.stringify(zero.refused || zero));
    const nul = attest.singleSignerEligible(null);
    is(nul.refused && nul.refused.code === 'ELIGIBILITY_UNKNOWN',
       'D4. NULL -- the roster could not be read -- is ELIGIBILITY_UNKNOWN and '
     + 'not 0 and not eligible. Could-not-tell is a third state and is never '
     + 'folded into "one, so go ahead"',
       JSON.stringify(nul.refused || nul));
    const dec = attest.decideAttestation(
      { callerRole: 'paralegal', settingOn: true, activeBarAdmitted: 1 });
    is(dec.refused && dec.refused.code === 'NOT_BAR_ADMITTED',
       'D5. a paralegal is refused even at an eligible solo firm -- the '
     + 'eligibility is about the FIRM, the licensure is about the PERSON, and '
     + 'neither substitutes for the other',
       JSON.stringify(dec.refused || dec));
    const dual = attest.decideAttestation(
      { callerRole: 'attorney', hasToken: true, settingOn: true, activeBarAdmitted: 1 });
    is(dual.mode === attest.SIGNER_MODE_DUAL,
       'D6. a token means DUAL even at an eligible solo firm -- doing the '
     + 'stronger thing is never blocked by a setting, and the record then says '
     + '`dual`, which is the truth',
       JSON.stringify(dual));
  }

  // ══ E. THE SINGLE-SIGNER PATH THROUGH THE REAL ROUTE ════════════════════
  section('E. the route -- single-signer');
  {
    const e1 = await callCapturing(ATTEST(), { settingOn: true, barAdmitted: 1 });
    is(e1.res.statusCode === 200 && e1.res.body
       && e1.res.body.signer_mode === attest.SIGNER_MODE_SINGLE,
       'E1. setting ON + exactly one bar-admitted + an attorney = attested, '
     + 'signer_mode `single`',
       e1.res.statusCode + ' ' + JSON.stringify(e1.res.body && e1.res.body.signer_mode));
    is(e1.row && e1.row.signer_mode === 'single'
       && e1.row.prepared_by === e1.row.attested_by
       && e1.row.attested_role === 'attorney',
       'E2. AND THE ROW SAYS SO -- signer_mode single with one name in both '
     + 'places. Asserted on the INSERT BODY, not on the response: a response '
     + 'can be right about a row that is wrong',
       JSON.stringify(e1.row && { m: e1.row.signer_mode, p: e1.row.prepared_by,
                                  a: e1.row.attested_by }));
    const e3 = await call(ATTEST(), { barAdmitted: 1 });               // setting absent
    is(e3.res.statusCode === 403 && eCode(e3.res) === 'COUNTERSIGN_REQUIRED',
       'E3. AN ABSENT SETTING IS OFF. A solo firm that never switched it on '
     + 'needs the second signature -- absent-means-on would hand the weaker '
     + 'control to every firm on the platform',
       e3.res.statusCode + ' ' + eCode(e3.res));
    const e4 = await call(ATTEST(), { settingOn: true, barAdmitted: 2 });
    is(e4.res.statusCode === 403 && eCode(e4.res) === 'SINGLE_SIGNER_NOT_SOLO',
       'E4. THE STALE-SETTING ARM, AND IT IS THE ONE THAT MATTERS. The setting '
     + 'is ON and the firm now has TWO attorneys -- the attestation is REFUSED, '
     + 'because the roster is re-counted at attest time and not trusted from '
     + 'when the setting was accepted',
       e4.res.statusCode + ' ' + eCode(e4.res));
    const e5 = await call(ATTEST(), { settingOn: true, rosterUnreadable: true });
    is(e5.res.statusCode === 503 && eCode(e5.res) === 'ELIGIBILITY_UNKNOWN',
       'E5. an unreadable roster is 503 could-not-tell, NOT a single-signer '
     + 'attestation and NOT a flat 403. PR §1.11 on a record a bar auditor '
     + 'reads',
       e5.res.statusCode + ' ' + eCode(e5.res));
    const e6 = await call(ATTEST(), { settingOn: true, barAdmitted: 1,
                                      callerRole: 'paralegal' });
    is(e6.res.statusCode === 403 && eCode(e6.res) === 'NOT_BAR_ADMITTED',
       'E6. a paralegal cannot attest, at any firm', e6.res.statusCode + ' ' + eCode(e6.res));
    // THE ROLE COMES FROM THE EMPLOYEE ROW, NOT THE TOKEN. A session outlives
    // a demotion by up to its TTL, so a token still saying `attorney` must not
    // be what decides.
    const e7 = await call(ATTEST(), { settingOn: true, barAdmitted: 1,
                                      callerRole: 'paralegal', tokenRole: 'attorney' });
    is(e7.res.statusCode === 403 && eCode(e7.res) === 'NOT_BAR_ADMITTED',
       'E7. a token that still says `attorney` over an employee row that says '
     + '`paralegal` is REFUSED -- the role is read from the row, so a demotion '
     + 'takes effect at once rather than waiting out the session',
       e7.res.statusCode + ' ' + eCode(e7.res));
    const e8 = await call(ATTEST(), { noSession: true });
    is(e8.res.statusCode === 401 && eCode(e8.res) === 'NO_SESSION',
       'E8. no session is 401 and never a write', e8.res.statusCode + ' ' + eCode(e8.res));
    const e9 = await call(ATTEST(), { settingOn: true, barAdmitted: 1,
                                      callerInactive: true });
    is(e9.res.statusCode === 401,
       'E9. a session whose employee row is gone or inactive is refused -- a '
     + 'signature carrying a name that no longer means anything is worse than '
     + 'no signature',
       e9.res.statusCode + ' ' + eCode(e9.res));
    const e10 = await call(ATTEST({ comparison: Object.assign({}, CMP,
      { bank_balance_cents: 1.5 }) }), { settingOn: true, barAdmitted: 1 });
    is(e10.res.statusCode === 400 && eCode(e10.res) === 'CENTS_NOT_INTEGER',
       'E10. the comparison is validated BEFORE anything about signatures, so '
     + 'an unattestable record is refused for the right reason',
       e10.res.statusCode + ' ' + eCode(e10.res));
  }

  // ══ F. THE TWO-SIGNER PATH ══════════════════════════════════════════════
  section('F. the route -- two-signer, through the shared lock');
  {
    // THE SAVER IS `carol`, THE PREPARER IS `bob` AND THE SIGNER IS `alice` --
    // THREE DIFFERENT PEOPLE, AND THAT IS NOT DECORATION. The first draft let
    // the caller default to `alice`, who is also the countersigner, so
    // attributing the record to the SAVER and attributing it to the SIGNER
    // produced the same row and F2 passed either way. ABLATION I3 CAUGHT THAT:
    // it mutated the read-back, nothing went red, and the arm was the thing at
    // fault. A property that cannot distinguish the defect from the fix is not
    // being tested.
    const f1 = await callCapturing(ATTEST(),
      { tokenRow: tokenRowFor(CMP), callerId: 'carol' });
    is(f1.res.statusCode === 200 && f1.res.body.signer_mode === attest.SIGNER_MODE_DUAL,
       'F1. a good token attests, signer_mode `dual`',
       f1.res.statusCode + ' ' + JSON.stringify(f1.res.body));
    is(f1.row && f1.row.prepared_by === 'bob' && f1.row.prepared_role === 'paralegal'
       && f1.row.attested_by === 'alice' && f1.row.attested_role === 'attorney',
       'F2. THE ROW NAMES THE TOKEN\'S TWO PEOPLE, read back from the spent '
     + 'token -- the preparer is the paralegal who ran it and the attester is '
     + 'the COUNTERSIGNER. Not the caller: on this path the caller is whoever '
     + 'is saving, and attributing the attestation to them is the defect the '
     + 'stored-role rule exists to prevent',
       JSON.stringify(f1.row && { p: f1.row.prepared_by, a: f1.row.attested_by }));
    const f3 = await call(ATTEST(), { tokenRow: tokenRowFor(CMP,
      { prepared_by: 'alice', countersign_employee_id: 'alice' }) });
    is(f3.res.statusCode === 409 && eCode(f3.res) === 'COUNTERSIGN_SAME_PERSON',
       'F3. A SELF-COUNTERSIGNATURE IS STILL REFUSED. The single-signer mode '
     + 'did NOT weaken this -- it is a separate path with its own name on the '
     + 'row, and api/_lib/countersign.js\'s no-self-signature rule is untouched',
       f3.res.statusCode + ' ' + eCode(f3.res));
    const f4 = await call(ATTEST(), { tokenRow: tokenRowFor(CMP_ONE_CENT) });
    is(f4.res.statusCode === 409 && eCode(f4.res) === 'COUNTERSIGN_CONTENT_MISMATCH',
       'F4. a token signed over a comparison ONE CENT different cannot be '
     + 'spent on this one. This is the arm the whole mechanism exists for',
       f4.res.statusCode + ' ' + eCode(f4.res));
    const f5 = await call(ATTEST(), { tokenRow: tokenRowFor(CMP,
      { expires_at: new Date(Date.now() - 1000).toISOString() }) });
    is(f5.res.statusCode === 409 && eCode(f5.res) === 'COUNTERSIGN_EXPIRED',
       'F5. an expired token is refused', f5.res.statusCode + ' ' + eCode(f5.res));
    const f6 = await call(ATTEST(), { tokenRow: tokenRowFor(CMP,
      { spent_at: new Date().toISOString() }) });
    is(f6.res.statusCode === 409 && eCode(f6.res) === 'COUNTERSIGN_ALREADY_SPENT',
       'F6. a spent token is refused -- each signature covers exactly one write',
       f6.res.statusCode + ' ' + eCode(f6.res));
    const f7 = await call(ATTEST(), { tokenRow: tokenRowFor(CMP,
      { countersign_role: 'paralegal' }) });
    is(f7.res.statusCode === 403 && eCode(f7.res) === 'COUNTERSIGN_NOT_QUALIFIED',
       'F7. a signature from a non-bar-admitted role is refused, judged on the '
     + 'role STORED ON THE ROW',
       f7.res.statusCode + ' ' + eCode(f7.res));
    // THE CALLER IS `carol` AND THE DEACTIVATED PERSON IS THE SIGNER `alice`.
    // The first draft deactivated alice while alice was also the caller, so
    // the arm measured the 401 session refusal and never reached the settling
    // step -- a green-looking red for the wrong reason, which is why the
    // caller and the signer are different people here.
    const f8 = await call(ATTEST(), { tokenRow: tokenRowFor(CMP),
                                      callerId: 'carol', inactive: ['alice'] });
    is(f8.res.statusCode === 403 && eCode(f8.res) === 'COUNTERSIGN_NO_LONGER_ACTIVE',
       'F8. the SETTLING STEP: a signer deactivated between signing and saving '
     + 'stops the write, even though the SAVER is active',
       f8.res.statusCode + ' ' + eCode(f8.res));
    const f9 = await call(ATTEST(), { sendToken: true });   // token, no row
    is(f9.res.statusCode === 403 && eCode(f9.res) === 'COUNTERSIGN_REQUIRED',
       'F9. an unrecognised token is refused and nothing is written',
       f9.res.statusCode + ' ' + eCode(f9.res));
  }

  // ══ G. POLICY, LIST, AND THE UNPROVISIONED STATE ════════════════════════
  section('G. set_policy / policy / list / not provisioned');
  {
    const g1 = await call({ action: 'set_policy', enabled: true },
      { callerRole: 'owner', barAdmitted: 1 });
    is(g1.res.statusCode === 200 && g1.res.body.single_signer_enabled === true
       && /re-counted on every/.test(g1.res.body.note || ''),
       'G1. the owner of a solo firm may switch it on, and the answer SAYS the '
     + 'roster is re-counted on every attestation',
       g1.res.statusCode + ' ' + JSON.stringify(g1.res.body));
    const g2 = await call({ action: 'set_policy', enabled: true },
      { callerRole: 'attorney', barAdmitted: 1 });
    is(g2.res.statusCode === 403,
       'G2. an ATTORNEY may not change it. Turning this on changes what a '
     + 'record of a regulated review may claim, which is provisioning-class '
     + 'and not a working preference',
       g2.res.statusCode + ' ' + eCode(g2.res));
    const g3 = await call({ action: 'set_policy', enabled: true },
      { callerRole: 'owner', barAdmitted: 3 });
    is(g3.res.statusCode === 409 && eCode(g3.res) === 'SINGLE_SIGNER_NOT_SOLO',
       'G3. THE FIRST ENFORCEMENT POINT: a firm with three bar-admitted '
     + 'employees cannot switch it on at all',
       g3.res.statusCode + ' ' + eCode(g3.res));
    const g4 = await call({ action: 'set_policy', enabled: false },
      { callerRole: 'owner', barAdmitted: 3 });
    is(g4.res.statusCode === 200 && g4.res.body.single_signer_enabled === false,
       'G4. switching it OFF is always allowed and does not read the roster -- '
     + 'a firm must never be unable to tighten its own control',
       g4.res.statusCode + ' ' + JSON.stringify(g4.res.body));
    const g5 = await call(ATTEST(), { settingOn: true, barAdmitted: 1,
                                      recordMissing: true });
    is(g5.res.statusCode === 503 && eCode(g5.res) === 'NOT_PROVISIONED'
       && /sairnlaw_trust_attestations\.sql/.test(eMsg(g5.res)),
       'G5. WITH THE SQL UNRUN -- which is production today -- it answers 503 '
     + 'NOT_PROVISIONED and names the file. "It refuses until the SQL is run" '
     + 'and "it writes unattested until the SQL is run" are opposite facts',
       g5.res.statusCode + ' ' + eCode(g5.res));
    const g6 = await call(ATTEST(), { settingOn: true, barAdmitted: 1,
                                      recordDuplicate: true });
    is(g6.res.statusCode === 409 && eCode(g6.res) === 'ATTESTATION_ID_TAKEN',
       'G6. a reused attestation_id is its own 409 and not a generic data-store '
     + 'error, which would send somebody to look at Supabase',
       g6.res.statusCode + ' ' + eCode(g6.res));
    const g7 = await call({ action: 'policy' }, { settingOn: true, barAdmitted: 2 });
    is(g7.res.statusCode === 200 && g7.res.body.single_signer_enabled === true
       && g7.res.body.single_signer_available === false
       && g7.res.body.active_bar_admitted === 2,
       'G7. `policy` shows the SETTING AND THE LIVE COUNT SIDE BY SIDE, and '
     + 'reports available=false when they disagree. A panel that showed only '
     + 'the setting would present it as working',
       JSON.stringify(g7.res.body));
    const g8 = await call({ action: 'list' }, { callerRole: 'paralegal' });
    is(g8.res.statusCode === 403,
       'G8. a paralegal may not LIST attestations -- they carry the three trust '
     + 'leg balances, which are inside LAW_TRUST_LOCKED',
       g8.res.statusCode + ' ' + eCode(g8.res));
    const g9 = await call({ action: 'list' }, { callerRole: 'attorney',
      records: [{ attestation_id: 'AT-1', signer_mode: 'single' }] });
    const g9s = JSON.stringify(g9.res.body || {});
    is(g9.res.statusCode === 200 && !/token/i.test(g9s),
       'G9. an attorney may list, and NO token or token hash appears anywhere '
     + 'in the answer -- a readable table of live tokens is a table of '
     + 'signatures waiting to be borrowed',
       g9.res.statusCode + ' ' + g9s.slice(0, 160));
    is(/does not certify/.test(g9s),
       'G10. and every answer carries the sentence that an attestation is NOT '
     + 'a correctness guarantee, from the server rather than from seventeen '
     + 'front-ends each writing their own version',
       g9s.indexOf('does not certify') !== -1 ? 'present' : 'absent');
    const g11 = await call({ action: 'nonsense' }, {});
    is(g11.res.statusCode === 400 && /attest/.test(eMsg(g11.res)),
       'G11. an unknown action is a 400 that NAMES the actions, and the four '
     + 'shared ones are in the list',
       g11.res.statusCode + ' ' + eMsg(g11.res));
    const g12 = await call({ action: 'prepare', resource: attest.ATTEST_RESOURCE,
      payload: normalised(CMP) }, { callerRole: 'paralegal' });
    is(g12.res.statusCode === 200 || g12.res.statusCode === 503,
       'G12. `prepare` reaches the SHARED endpoint rather than this file\'s own '
     + 'dispatch -- a paralegal staging an attestation is not refused as an '
     + 'unknown action',
       g12.res.statusCode + ' ' + eCode(g12.res));
  }

  if (ARMS_ONLY) {
    console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
    if (failed.length) console.log('  FAILED: ' + failed.join(', '));
    if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
    process.exit(fail ? 1 : (unproven ? 3 : 0));
  }

  // ══ I. THE ABLATIONS ════════════════════════════════════════════════════
  // Remove ONE named layer from already-clean code and measure what IT ALONE
  // catches, per ARM rather than per exit code (item 12 of
  // docs/2026-09-13-cross-domain-disciplines.md).
  section('I. ABLATIONS');

  // I0. THE CLEAN CONTROL, FIRST. An ablation that reddens proves nothing if
  // the file is red to begin with -- and the child runs with ARMS_ONLY, which
  // is a different code path from this one.
  const i0 = runSuite(SELF, true);
  is(i0.exit === 0,
     'I0. THE CONTROL: with nothing ablated, the arms-only child run is GREEN '
   + '(exit 0). Every ablation below is measured against this',
     'child exit ' + i0.exit + '\n' + String(i0.out).slice(-400));

  // I1. The SETTING itself. Remove the `settingOn !== true` refusal and E3 --
  // "an absent setting is off" -- must go red, while the others stay green.
  const i1 = ablate(ATTEST_LIB_SRC,
    "  if (c.settingOn !== true) {",
    "  if (false) {");
  if (!i1.ok) {
    cannot('I1. the per-firm setting is load-bearing', i1.why);
  } else {
    is(i1.exit === 1 && i1.arms.indexOf('E3') !== -1,
       'I1. removing ONLY the setting check makes arm E3 FAIL -- so the setting '
     + 'is what stands between a firm that never opted in and a single-signer '
     + 'attestation. Measured per ARM: E3 by name, not merely exit 1',
       'exit ' + i1.exit + ' arms=' + i1.arms.join(','));
    is(i1.arms.indexOf('E1') === -1 && i1.arms.indexOf('F1') === -1,
       'I1b. ...and E1/F1 stay GREEN, so one layer was removed and not the '
     + 'floor. An ablation that breaks the whole file measures nothing',
       'arms=' + i1.arms.join(','));
  }

  // I2. THE RE-COUNT. Widen `=== 1` to `>= 1` and E4 -- the stale-setting arm
  // -- must go red while E1 stays green. This is the ablation for property 1.
  const i2 = ablate(ATTEST_LIB_SRC,
    "  if (activeBarAdmitted === 1) return { eligible: true, count: 1 };",
    "  if (activeBarAdmitted >= 1) return { eligible: true, count: activeBarAdmitted };");
  if (!i2.ok) {
    cannot('I2. the exactly-one count is load-bearing', i2.why);
  } else {
    is(i2.exit === 1 && i2.arms.indexOf('E4') !== -1 && i2.arms.indexOf('D2') !== -1,
       'I2. widening exactly-one to at-least-one makes E4 and D2 FAIL -- so '
     + '"exactly one" is doing the work and a two-attorney firm with a stale '
     + 'setting would otherwise attest with one signature',
       'exit ' + i2.exit + ' arms=' + i2.arms.join(','));
    is(i2.arms.indexOf('E1') === -1,
       'I2b. ...and E1 stays GREEN -- the legitimate solo attestation still '
     + 'works, so the ablation removed one condition and not the feature',
       'arms=' + i2.arms.join(','));
  }

  // I3. THE SIGNER READ-BACK. Attribute the attestation to the CALLER instead
  // of the countersigner and F2 must go red. This is the ablation for
  // property 2 -- the one that would let a record name the wrong person while
  // every status code stayed correct.
  const i3 = ablate(ROUTE_SRC,
    "        attestedBy = trow.countersign_employee_id;\n        attestedRole = trow.countersign_role;",
    "        attestedBy = caller.employee_id;\n        attestedRole = caller.role;");
  if (!i3.ok) {
    cannot('I3. the attester is read from the token row, not the caller', i3.why);
  } else {
    is(i3.exit === 1 && i3.arms.indexOf('F2') !== -1,
       'I3. attributing the attestation to the SAVER instead of the SIGNER '
     + 'makes arm F2 FAIL -- a defect that changes no status code and no '
     + 'response field a panel reads, only the name on a record a bar auditor '
     + 'will read years later',
       'exit ' + i3.exit + ' arms=' + i3.arms.join(','));
    is(i3.arms.indexOf('F1') === -1 && i3.arms.indexOf('F3') === -1,
       'I3b. ...and F1/F3 stay GREEN, so the lock itself was untouched',
       'arms=' + i3.arms.join(','));
  }

  console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => {
  console.error('\n  HARNESS ERROR -- the suite did not finish, which is NOT a '
    + 'pass:\n', e);
  process.exit(1);
});
