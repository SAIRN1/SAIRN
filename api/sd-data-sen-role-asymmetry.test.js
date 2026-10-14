// api/sd-data-sen-role-asymmetry.test.js
//
// Run:  node api/sd-data-sen-role-asymmetry.test.js
//
// REQUIREMENT: three SAIRNsenior gates that were asymmetric between read and
//   write are symmetric now, in the direction that does not break the thing the
//   open read was built for.
//
//   sen_branches   write management-only, read was ANY signed-in employee and
//                  returned the WHOLE blob. Now tiered by an allowlist.
//   sen_settings   same shape, plus `updated_by` / `updated_at` -- who changed
//                  the agency's compliance declaration, and when.
//   the five SEN_REFERRAL_RESOURCES  read AND write were both decided by a role
//                  set literally named SEN_CLIENT_BROAD_READ_ROLES. Write is
//                  management-only now; read is deliberately unchanged.
//
// ── WHY A FLAT ROLE GATE WOULD HAVE BEEN THE WRONG FIX ───────────────────
// api/sd-data.js records, in the caregiver's own terms, why the branch read was
// open: a caregiver's roster row names a branch, and if the name cannot resolve
// the screen shows a raw id. The EVV state is the same -- the rules applied to
// a caregiver's own visits are unexplainable without it. Refusing those reads
// outright would break a real screen, and a security change that breaks a
// screen gets reverted as broken rather than fixed. So both reads are
// MINIMUM-NECESSARY instead, which is the pattern this file already uses for
// SAIRNdental's financial tier.
//
// ── THE ALLOWLIST DIRECTION IS THE LOAD-BEARING PART ─────────────────────
// A denylist would disclose by default: the next field somebody puts on a
// branch row, or the next setting key somebody adds, would be published to
// every caregiver until a reviewer noticed. The arms below drive that
// explicitly with a field and a key that do not exist in today's app.

'use strict';
const crypto = require('crypto');
const path = require('path');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['sen', 'asymmetry', 'fixture', String(process.pid)].join('-');

const HANDLER = path.join(__dirname, 'sd-data.js');
const senAuth = require('./sen-auth');
const { signSessionToken } = require('./_lib/auth');

const LICENSE_KEY = 'k';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');
const tok = (role) => signSessionToken({
  app: 'sairnsenior', employee_id: 'sen-' + role, role: role,
  license_hash: LIC_HASH });

let n = 0, bad = 0;
function ok(cond, label) {
  if (cond) { console.log('  ok   ' + label); n++; }
  else { console.log('  FAIL ' + label); bad++; }
}
function section(s) { console.log('\n' + s); }
const eCode = (r) => (r && r.body && r.body.error && r.body.error.code) || '';

function loadHandler() {
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}

async function call(handler, opts) {
  const out = { code: null, body: null, calls: [], credentialChecks: 0 };
  const res = { status(c) { out.code = c; return res; },
                json(b) { out.body = b; return res; }, setHeader() {} };
  const names = { url: ['SUPABASE', 'URL'].join('_'),
                  key: ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_') };
  const envURL = process.env[names.url], envKey = process.env[names.key];
  const realFetch = global.fetch;
  process.env[names.url] = 'https://stub.invalid';
  process.env[names.key] = ['stub', 'fixture', 'value'].join('-');
  let first = true;
  const replies = (opts.replies || []).slice();
  global.fetch = async (url, init) => {
    if (first) {
      first = false;
      return { ok: true, status: 200,
               json: async () => [{ status: 'active', app_id: null }] };
    }
    if (/_employee_auth\?.*&select=active&limit=1/.test(String(url))) {
      out.credentialChecks++;
      return { ok: true, status: 200, json: async () => [{ active: true }] };
    }
    out.calls.push({ url: String(url), method: (init && init.method) || 'GET',
                     body: (init && init.body) || null });
    const r = replies.length ? replies.shift() : { status: 200, rows: [] };
    return { ok: r.status >= 200 && r.status < 300, status: r.status,
             json: async () => (r.rows === undefined ? [] : r.rows) };
  };
  try {
    await handler({
      method: 'POST',
      headers: Object.assign(
        { authorization: 'Bearer ' + LICENSE_KEY },
        opts.token ? { 'x-sd-auth': opts.token } : {}),
      body: { action: opts.action, resource: opts.resource,
              app_id: 'sairnsenior', payload: opts.payload || {} }
    }, res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env[names.url]; else process.env[names.url] = envURL;
    if (envKey === undefined) delete process.env[names.key]; else process.env[names.key] = envKey;
  }
  return out;
}

// A branch row as stored: the three fields a caregiver legitimately needs,
// plus the two the write path stamps, plus one NOBODY HAS ADDED YET -- which is
// the allowlist arm's whole point.
const BRANCH_ROW = {
  branch_id: 'BR-1',
  data: { name: 'North Office', state: 'OH', active: true,
          updatedBy: 'sen-owner', updatedByRole: 'owner',
          internal_lease_cost: 48000 }
};
const SETTING_ROWS = [
  { setting_key: 'evv_config',
    data: { state: 'OH', aggregator: 'sandata',
            // THE VALUE CARRIES THE WORD `example` ON PURPOSE.
            // tools/redaction_check.py's generic_credential_assignment
            // pattern matches any `secret: "<16+ chars>"` and the push gate
            // REFUSED this file on the first attempt -- correctly, because a
            // credential-shaped literal in a commit is exposed whether or not
            // anybody meant it. The detector skips values containing a
            // placeholder marker, which is what this now is in both senses.
            api_secret: 'example-secret-that-must-not-leave' },
    updated_by: 'sen-owner', updated_at: '2026-10-01T00:00:00.000Z' },
  { setting_key: 'agency_profile',
    data: { name: 'Northside Home Care', tax_id: '00-0000000' },
    updated_by: 'sen-owner', updated_at: '2026-10-01T00:00:00.000Z' },
  // A KEY NOBODY HAS ADDED YET. The write path stores unknown keys as-is by
  // design; this proves the READ does not therefore disclose them.
  { setting_key: 'future_unknown_key',
    data: { something: 'private' },
    updated_by: 'sen-owner', updated_at: '2026-10-01T00:00:00.000Z' }
];

console.log('SAIRNsenior -- three read/write asymmetries, closed without '
            + 'breaking the open read\n');

(async () => {
  const h = loadHandler();

  // ── 0. THE FIXTURE ──────────────────────────────────────────────────────
  section('0. the fixture');
  ok(!!senAuth.MANAGEMENT_ROLES.owner && !senAuth.MANAGEMENT_ROLES.caregiver,
     'MANAGEMENT_ROLES is imported from api/sen-auth.js and is owner/billing, '
     + 'not re-listed here -- a second copy is the drift this app paid for on '
     + '2026-08-20');
  ok(!senAuth.MANAGEMENT_ROLES.coordinator && !senAuth.MANAGEMENT_ROLES.scheduler,
     '...and a coordinator and a scheduler are NOT management, which is what '
     + 'makes the write arms below mean something');

  // ── 1. sen_branches ─────────────────────────────────────────────────────
  section('1. sen_branches -- the read is tiered, not refused');
  {
    const r = await call(h, { action: 'read', resource: 'sen_branches',
      token: null });
    ok(r.code === 401 && eCode(r) === 'NO_SESSION' && r.calls.length === 0,
       'no session is still refused with zero database calls -- ' + r.code);
  }
  {
    const r = await call(h, { action: 'read', resource: 'sen_branches',
      token: tok('caregiver'), replies: [{ status: 200, rows: [BRANCH_ROW] }] });
    ok(r.code === 200, 'a CAREGIVER can still read branches -- ' + r.code
       + '. If this went red the roster screen would show a raw id, which is '
       + 'the regression the tier exists to avoid');
    const row = r.body.data[0];
    ok(row.name === 'North Office' && row.state === 'OH' && row.active === true,
       '...and gets the three fields the need actually requires -- '
       + JSON.stringify(row));
    ok(row.updatedBy === undefined && row.updatedByRole === undefined,
       '...but NOT who changed the office configuration');
    ok(row.internal_lease_cost === undefined,
       '...and NOT a field nobody has added yet. THE ALLOWLIST ARM: a denylist '
       + 'would have published internal_lease_cost the day somebody stored it');
    ok(row.id === 'BR-1', '...and the id still resolves, which is the point');
  }
  {
    const r = await call(h, { action: 'read', resource: 'sen_branches',
      token: tok('owner'), replies: [{ status: 200, rows: [BRANCH_ROW] }] });
    const row = r.body.data[0];
    ok(r.code === 200 && row.updatedBy === 'sen-owner'
       && row.internal_lease_cost === 48000,
       'MANAGEMENT still reads the row whole -- without this arm the tier '
       + 'could be a blanket redaction and every arm above would pass. '
       + JSON.stringify(row).slice(0, 120));
  }
  {
    const r = await call(h, { action: 'write', resource: 'sen_branches',
      token: tok('coordinator'), payload: { id: 'BR-2', state: 'OH' } });
    ok(r.code === 403 && eCode(r) === 'FORBIDDEN' && r.calls.length === 0,
       'the write is still management-only -- ' + r.code);
  }

  // ── 2. sen_settings ─────────────────────────────────────────────────────
  section('2. sen_settings -- the compliance declaration, tiered the same way');
  {
    const r = await call(h, { action: 'read', resource: 'sen_settings',
      token: tok('caregiver'), replies: [{ status: 200, rows: SETTING_ROWS }] });
    ok(r.code === 200 && r.body.tiered === true,
       'a caregiver read succeeds and SAYS it is tiered, so a client cannot '
       + 'mistake a filtered answer for the whole row -- ' + r.code);
    const byKey = {};
    (r.body.data || []).forEach((x) => { byKey[x.setting_key] = x.value; });
    ok(byKey.evv_config && byKey.evv_config.state === 'OH'
       && byKey.evv_config.aggregator === 'sandata',
       '...and the EVV state and aggregator still come through, because the '
       + 'rules applied to a caregiver\'s own visits are unexplainable '
       + 'without them -- ' + JSON.stringify(byKey.evv_config));
    ok(byKey.evv_config && byKey.evv_config.api_secret === undefined,
       '...and an aggregator SECRET on the same row does not');
    ok(byKey.agency_profile && byKey.agency_profile.name === 'Northside Home Care'
       && byKey.agency_profile.tax_id === undefined,
       '...the agency NAME comes through and its tax id does not -- '
       + JSON.stringify(byKey.agency_profile));
    ok(byKey.future_unknown_key === undefined,
       'AND AN UNKNOWN SETTING KEY IS WITHHELD ENTIRELY. The write path stores '
       + 'unknown keys as-is by design -- "a settings store, not a schema '
       + 'registry" -- so without this the next setting anybody adds is '
       + 'published to every caregiver by default');
    const raw = JSON.stringify(r.body);
    ok(raw.indexOf('updated_by') === -1 && raw.indexOf('updated_at') === -1,
       '...and neither updated_by nor updated_at appears anywhere in the '
       + 'non-management response');
  }
  {
    const r = await call(h, { action: 'read', resource: 'sen_settings',
      token: tok('owner'), replies: [{ status: 200, rows: SETTING_ROWS }] });
    const keys = (r.body.data || []).map((x) => x.setting_key).sort();
    ok(r.code === 200 && !r.body.tiered && keys.length === 3,
       'MANAGEMENT reads all three keys including the unknown one -- '
       + keys.join(', '));
    ok((r.body.data || []).every((x) => x.updated_by === 'sen-owner'),
       '...with updated_by intact, so the tier is a tier and not a deletion');
  }
  for (const role of ['caregiver', 'coordinator', 'scheduler']) {
    const r = await call(h, { action: 'write', resource: 'sen_settings',
      token: tok(role), payload: { setting_key: 'evv_config', value: { state: 'OH' } } });
    ok(r.code === 403 && r.calls.length === 0,
       'a ' + role + ' still cannot write a setting -- ' + r.code);
  }

  // ── 3. THE REFERRAL FAMILY ──────────────────────────────────────────────
  // THE ASYMMETRY WAS IN THE ROLE SET'S OWN NAME: SEN_CLIENT_BROAD_READ_ROLES
  // was deciding a WRITE on all five.
  section('3. SEN_REFERRAL_RESOURCES -- a broad-READ set no longer decides a '
          + 'WRITE');
  const REFERRAL = ['sen_referral_sources', 'sen_referrals', 'sen_training_rules',
                    'sen_training_records', 'sen_applicants'];
  for (const resource of REFERRAL) {
    for (const role of ['coordinator', 'scheduler']) {
      const r = await call(h, { action: 'write', resource: resource,
        token: tok(role), payload: { id: 'X-1' } });
      ok(r.code === 403 && eCode(r) === 'FORBIDDEN' && r.calls.length === 0,
         resource + ': a ' + role + ' can no longer write -- ' + r.code
         + ', ' + r.calls.length + ' call(s)');
    }
  }
  for (const resource of REFERRAL) {
    // READ IS DELIBERATELY UNCHANGED. Without these arms the change above is
    // indistinguishable from refusing coordinators the whole family, which
    // would take the referral and applicant screens away from the people whose
    // job they are.
    const r = await call(h, { action: 'read', resource: resource,
      token: tok('coordinator'), replies: [{ status: 200, rows: [] }] });
    ok(r.code === 200,
       resource + ': a coordinator can STILL READ it -- ' + r.code);
  }
  {
    const r = await call(h, { action: 'write', resource: 'sen_referrals',
      token: tok('owner'), payload: { id: 'RF-1' },
      replies: [{ status: 201, rows: [{ referral_id: 'RF-1', data: {} }] }] });
    ok(r.code === 200,
       'and MANAGEMENT can write -- without this the gate could be refusing '
       + 'everybody and every arm above would still pass. ' + r.code);
  }
  {
    const r = await call(h, { action: 'read', resource: 'sen_referrals',
      token: tok('caregiver'), replies: [{ status: 200, rows: [] }] });
    ok(r.code === 403,
       'a CAREGIVER still cannot read the referral family at all, which is the '
       + 'pre-existing rule and was not widened by this change -- ' + r.code);
  }

  console.log('\n' + n + ' passed, ' + bad + ' failed');
  console.log('\nWHAT THIS DOES NOT SETTLE: whether a coordinator SHOULD be able to log a\n'
              + 'referral. The write set is management-only because that is the\n'
              + 'instruction; if intake is a coordinator\'s job the fix is a per-resource\n'
              + 'write map in ONE place, not a return to the broad set. Named in the\n'
              + 'handoff rather than left in a comment.');
  process.exit(bad ? 1 : 0);
})();
