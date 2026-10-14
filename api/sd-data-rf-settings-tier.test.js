// api/sd-data-rf-settings-tier.test.js
//
// Run:  node api/sd-data-rf-settings-tier.test.js
//
// REQUIREMENT: a non-management SAIRNroofing employee can still read the
//   company damage threshold -- which is the whole reason that read is open --
//   and can no longer read WHO set it or WHEN, or any setting key nobody
//   decided to publish.
//
// ── WHY THIS SUITE EXISTS, AND WHY IT EXISTS LATE ─────────────────────────
// The tier landed in the same commit as the SAIRNlegacy overlap helper and
// shipped with ZERO arms. It changes the RESPONSE SHAPE of a live app, and a
// response-shape change with no test is the thing a later refactor quietly
// reverts. Written after an adversarial review of that commit named the gap;
// recorded here rather than in a commit message, because a gap that is only
// mentioned once is a gap nobody can find again.
//
// ── THE TIER IS NARROWER THAN sen_settings' AND THAT IS THE POINT ─────────
// There the public fields were a SUBSET of one key's blob. Here the whole
// damage_threshold value stays public INCLUDING `source`, because the branch
// comment justifies the open read precisely on the number being
// unexplainable without it -- a threshold with no cited origin is
// indistinguishable from a guess once whoever configured it has moved on, and
// it decides whether a slope is called total. So arm B2 asserts `source`
// SURVIVES. A tier that stripped it would be defensible-looking and wrong.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['sairnroofing', 'settings', 'fixture', String(process.pid)].join('-');

const APP = 'sairnroofing';
const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');
const { signSessionToken } = require('./_lib/auth');
const rfAuth = require('./rf-auth');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// THE STORED ROWS. `updated_by` and `updated_at` are COLUMNS, not blob fields,
// which is why a tier can drop them without touching the value.
const ROWS = [
  { setting_key: 'damage_threshold',
    data: { hail: { hits_per_test_square: 8, source: 'Carrier bulletin HB-12' },
            wind: { hits_per_test_square: 3, source: 'State guidance 2024-7' } },
    updated_by: 'emp-boss', updated_at: '2026-10-01T00:00:00.000Z' },
  // AN UNDECIDED KEY. The write path stores unknown keys as-is -- it is a
  // settings store, not a schema registry -- so a store that accepts anything
  // must not also DISCLOSE anything. This row is what arm B3 is for.
  { setting_key: 'payroll_rates',
    data: { foreman_hourly: 42 },
    updated_by: 'emp-boss', updated_at: '2026-10-01T00:00:00.000Z' }
];

function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

function loadHandler() {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: APP })
    }
  };
  global.fetch = async function (url, init) {
    const u = String(url);
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200,
               json: async () => [{ active: true }] };
    }
    if (/rf_settings\?/.test(u) && (!init || !init.method || init.method === 'GET')) {
      return { ok: true, status: 200, json: async () => ROWS };
    }
    // NOT a silent empty list for anything else -- an unmocked read that
    // answers [] makes an arm pass for a reason nobody chose.
    throw new Error('Unmocked fetch: ' + ((init && init.method) || 'GET') + ' ' + u);
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function read(role) {
  const h = loadHandler();
  const res = mockRes();
  await h({ method: 'POST',
            headers: { authorization: 'Bearer ' + KEY,
                       'x-sd-auth': signSessionToken({
                         app: APP, employee_id: 'emp-1', role: role,
                         license_hash: HASH }) },
            body: { action: 'read', resource: 'rf_settings' } }, res);
  return res;
}
const rowFor = (res, key) =>
  ((res.body && res.body.data) || []).filter((x) => x.setting_key === key)[0];

console.log('rf_settings -- the tiered read -- criteria 2026-10-14.1\n');

(async () => {
  // ── A. THE ROLES, READ OFF THE APP RATHER THAN ASSUMED ──────────────────
  console.log('A. the two tiers exist and are the app\'s own');

  const mgmt = Object.keys(rfAuth.MANAGEMENT_ROLES);
  is(mgmt.length >= 1 && mgmt.indexOf('owner') !== -1,
     'A1. rfAuth.MANAGEMENT_ROLES is read from api/rf-auth.js and includes '
   + 'owner. The gate uses THIS set, not a second list -- the write gate one '
   + 'line below it uses the same one',
     JSON.stringify(mgmt));

  // A NON-MANAGEMENT ROLE MUST ACTUALLY EXIST, or every arm below is vacuous:
  // it would be testing the management path twice.
  const { ROLES_BY_APP } = require('./_lib/auth');
  const nonMgmt = (ROLES_BY_APP[APP] || [])
    .filter((r) => !rfAuth.MANAGEMENT_ROLES[r]);
  if (!nonMgmt.length) {
    cannot('A2. this app has NO non-management role, so the tiered branch is '
         + 'unreachable and nothing below measures it',
           JSON.stringify(ROLES_BY_APP[APP]));
  } else {
    ok('A2. ' + nonMgmt.length + ' non-management role(s) exist ('
     + nonMgmt.slice(0, 4).join(', ') + '), so the tiered branch is reachable. '
     + 'Without this arm every B arm below could be testing the management '
     + 'path twice');
  }
  const FOREMAN = nonMgmt[0];

  // ── B. THE NON-MANAGEMENT TIER ──────────────────────────────────────────
  console.log('\nB. a non-management reader');

  if (!FOREMAN) {
    cannot('B1-B5. no non-management role to drive', 'see A2');
  } else {
    const r = await read(FOREMAN);
    is(r.statusCode === 200 && r.body && r.body.tiered === true,
       'B1. the response is 200 and FLAGS ITSELF as tiered, so a client can '
     + 'tell a withheld field from an absent one',
       r.statusCode + ' tiered=' + JSON.stringify(r.body && r.body.tiered));

    const dt = rowFor(r, 'damage_threshold');
    is(dt && dt.value && dt.value.hail
       && dt.value.hail.hits_per_test_square === 8
       && dt.value.hail.source === 'Carrier bulletin HB-12'
       && dt.value.wind && dt.value.wind.source === 'State guidance 2024-7',
       'B2. THE ARM THAT KEEPS THIS HONEST -- the whole damage_threshold value '
     + 'survives, INCLUDING `source`. The open read exists because the number '
     + 'on a foreman\'s screen is unexplainable without it, and a threshold '
     + 'with no cited origin is indistinguishable from a guess',
       JSON.stringify(dt));

    is(!rowFor(r, 'payroll_rates'),
       'B3. an UNDECIDED setting key is WITHHELD. The write path stores '
     + 'unknown keys as-is, so a store that accepts anything must not also '
     + 'disclose anything -- otherwise the next setting somebody adds is '
     + 'published to every foreman by default',
       JSON.stringify((r.body && r.body.data) || []));

    is(dt && !('updated_by' in dt) && !('updated_at' in dt),
       'B4. NO updated_by AND NO updated_at on this tier. Which member of '
     + 'management last changed the number that decides whether a slope is '
     + 'called total is management information about management',
       JSON.stringify(dt && Object.keys(dt)));

    const blob = JSON.stringify(r.body);
    is(blob.indexOf('emp-boss') === -1,
       'B5. the acting employee\'s id appears NOWHERE in the response -- not '
     + 'as a column and not smuggled inside a value',
       blob.slice(0, 200));
  }

  // ── C. THE OVER-REFUSAL CONTROL ─────────────────────────────────────────
  // Without this, "the tier withholds things" is satisfied by a branch that
  // withholds everything from everybody.
  console.log('\nC. management is UNCHANGED -- the control');

  const m = await read('owner');
  const mdt = rowFor(m, 'damage_threshold');
  is(m.statusCode === 200 && m.body && m.body.tiered === false,
     'C1. an owner gets 200 and tiered=false',
     m.statusCode + ' tiered=' + JSON.stringify(m.body && m.body.tiered));
  is(mdt && mdt.updated_by === 'emp-boss'
     && mdt.updated_at === '2026-10-01T00:00:00.000Z',
     'C2. CONTROL -- management STILL sees updated_by and updated_at. A tier '
   + 'that hid them from everyone would pass every B arm above',
     JSON.stringify(mdt));
  is(!!rowFor(m, 'payroll_rates'),
     'C3. CONTROL -- management still sees the undecided key, so B3 is a tier '
   + 'and not a filter that dropped the row for everybody',
     JSON.stringify(((m.body && m.body.data) || []).map((x) => x.setting_key)));

  // ── D. THE CLIENT, READ RATHER THAN ASSUMED ─────────────────────────────
  // The tier is only safe because no screen used the dropped fields. That was
  // checked by hand once; this re-checks it every run, which is the difference
  // between a fact and a memory of one.
  console.log('\nD. the client half, re-read every run');

  let html = null;
  try {
    html = fs.readFileSync(path.join(__dirname, '..', 'sairnroofing.html'), 'utf8');
  } catch (e) { html = null; }
  if (html === null) {
    cannot('D1. sairnroofing.html is not readable, so "no screen used the '
         + 'dropped fields" was not measured', 'ENOENT');
  } else {
    const uses = (html.match(/updated_by|updated_at/g) || []).length;
    is(uses === 0,
       'D1. sairnroofing.html references updated_by/updated_at ZERO times, so '
     + 'no screen lost a field it was using. MEASURED, not remembered',
       uses + ' occurrence(s)');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
