// tests/sd_data_alf_mar_derive_charges_gate.js
//
// REQUIREMENT: `alf_billing` / `derive_charges` must not hand a MEDICATION NAME
//   to a role that `alf_mar` / `read` would 403. The charge line still appears,
//   priced, with its date and amount; the drug name does not.
//
// WHY, AND IT IS A ROLE-SET DIFFERENCE OF EXACTLY ONE. The gate on
// derive_charges is ALF_MANAGEMENT_ROLES = { owner, billing }. The gate on
// alf_mar/read, which OWNS that table, is ALF_MAR_ROLES = { owner, nursing,
// med_aide }. `billing` is in the first and not the second. Until 2026-10-06
// the MAR loop set `description: d.medication_name || d.name`, and description
// is returned on every derived line -- so a billing clerk, refused the MAR
// directly, learned which medications a NAMED resident is on by asking for
// their invoice. A medication regimen is diagnostic-revealing, which is what
// makes it PHI rather than an administrative detail.
//
// ROUTED BY hover2 seq -- reproducing artifact
// `.claude/skills/sairn-hover-auditor/tools-hover2/alf_cross_resource_repro.py
// --table alf_mar`, which exits 1 while the finding stands. That file is the
// auditor's and is READ ONLY to this session; this suite is the build-side
// acceptance test, and the FINDING STAYS OPEN for its finder to close.
//
// NOTHING IS LOST FROM THE BILLING ANSWER, and arm C is what proves it rather
// than asserting it: `api/_lib/care-charges.js` prices on `e.type` through
// `CHARGEABLE[type].rate_key`, never on description.
//
// REAL: the handler and the auth module. MOCKED: fetch, validateLicenseKey.
// NOT RUN: the live round trip.
//
// MUTATION PROOF: against the parent commit, arms B and D go red.
//
// Run:  node tests/sd_data_alf_mar_derive_charges_gate.js

'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..');

const LICENCE = require.resolve(path.join(ROOT, 'api/_lib/license.js'));
const LIC_HASH = 'hash-of-the-alf-mar-charges-licence';
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: LIC_HASH,
      stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: 'sairncare'
    }),
    hashLicense: () => LIC_HASH,
  },
};

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || 'alf-mar-derive-charges-test-secret';
const { signSessionToken } = require(path.join(ROOT, 'api/_lib/auth.js'));

// THE DRUG NAME IS DISTINCTIVE so the leak test can look for it ANYWHERE in the
// response rather than only on the line it was supposed to be on.
const DRUG = 'QUETIAPINE-FUMARATE-25MG';
const MAR = [
  { entry_id: 'MAR-1', entry_type: 'administration',
    data: { status: 'given', administered_at: '2026-09-03T09:00:00Z',
            medication_name: DRUG } },
  { entry_id: 'MAR-2', entry_type: 'administration',
    data: { status: 'given', administered_at: '2026-09-04T09:00:00Z',
            medication_name: DRUG } },
];
// THE RATE KEY IS `med_admin_rate` AND THE CARD IS THE BLOB ITSELF, and I had
// both wrong on the first run: the fixture said `{ rates: { medication_
// administration: 4.5 } }`, so every dose landed in `unpriced` instead of
// `lines` and FOUR arms failed -- including arm D, the allowed side. Read off
// the code rather than guessed: `api/_lib/care-charges.js:33` declares
// `medication_administration: { rate_key: 'med_admin_rate' }` and
// `api/sd-data.js:10691` passes `facRows[0].data` straight in as `rate_card`.
// Recorded here because it is the same defect shape as last batch's
// `staff` vs `staff_findings`: a fixture key nobody read out of the code.
const FACILITY = [{ data: { med_admin_rate: 4.5 } }];

global.fetch = async (url) => {
  const u = String(url);
  const ok = (rows) => ({ ok: true, status: 200, json: async () => rows });
  if (/alf_mar\?/.test(u)) return ok(MAR);
  if (/alf_clients\?/.test(u)) return ok([{ data: {} }]);
  if (/alf_activities\?/.test(u)) return ok([]);
  if (/alf_facility\?/.test(u)) return ok(FACILITY);
  if (/alf_billing\?/.test(u)) return ok([]);
  if (/_employee_auth\?/.test(u)) return ok([{ active: true }]);
  throw new Error('Unmocked fetch: ' + u);
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

async function derive(role) {
  const headers = { authorization: 'Bearer ALF-MAR-TEST-KEY' };
  if (role !== null) {
    headers['x-sd-auth'] = signSessionToken({
      app: 'sairncare', employee_id: 'EMP-' + String(role).toUpperCase(),
      role: role, license_hash: LIC_HASH });
  }
  const req = { method: 'POST', headers: headers, body: {
    action: 'derive_charges', resource: 'alf_billing',
    payload: { resident_id: 'R1', month: '2026-09' } } };
  const res = fakeRes();
  await handler(req, res);
  return res;
}

const mentions = (res, needle) =>
  JSON.stringify(res.body || {}).indexOf(needle) !== -1;
// `lines`, READ OFF api/_lib/care-charges.js:141-148 -- the return object is
// { ok, resident_id, month, lines, total, unpriced, unbillable_event_types }.
// Guessing `charge_lines` first is what produced the vacuous run described at
// the fixture above.
const medLines = (res) =>
  (((res.body || {}).lines) || [])
    .filter((l) => l.type === 'medication_administration');
// A dose that failed to PRICE lands in `unpriced`, which carries no
// description -- so a mis-keyed rate card redacts the drug name for EVERY role
// and makes the narrow arms pass for the wrong reason. Asserted, not assumed.
const unpriced = (res) => ((res.body || {}).unpriced) || [];

let pass = 0, fail = 0;
function ok(l) { pass++; console.log('  ok   ' + l); }
function bad(l, why) {
  fail++;
  console.log('  FAIL ' + l);
  if (why) console.log('       ' + String(why).slice(0, 400));
}

(async function main() {
  console.log('ALF_MAR VIA derive_charges -- PHI SCOPE -- criteria 2026-10-06.1\n');

  console.log('A. THE FIXTURE REACHES THE CODE AT ALL');
  let r = await derive('owner');
  const own = medLines(r);
  if (r.statusCode === 200 && own.length === 2 && unpriced(r).length === 0) {
    ok('A1. owner gets TWO PRICED medication_administration lines and NOTHING '
       + 'in `unpriced`. Without this arm every arm below could be passing on '
       + 'an empty list -- which is exactly what happened on the first run of '
       + 'this file, because the fixture rate key was wrong and all four doses '
       + 'went to `unpriced`, where there is no description to leak');
  } else {
    bad('A1. the fixture must produce two PRICED medication lines for owner',
        'status=' + r.statusCode + ' lines=' + JSON.stringify(own).slice(0, 200)
        + ' unpriced=' + JSON.stringify(unpriced(r)).slice(0, 200)
        + ' keys=' + Object.keys(r.body || {}).join(','));
  }

  console.log('\nB. billing IS REFUSED THE DRUG NAME -- the one role in the difference');
  r = await derive('billing');
  const bl = medLines(r);
  if (r.statusCode === 200 && !mentions(r, DRUG)) {
    ok('B1. the drug name appears NOWHERE in billing\'s response. This is the '
       + 'leak test rather than the field test -- a blanked line field with the '
       + 'same value echoed on a summary key would pass the narrow assertion '
       + 'and still be the defect');
  } else {
    bad('B1. billing must not receive the medication name',
        'status=' + r.statusCode + ' leaked=' + mentions(r, DRUG));
  }
  if (bl.length === 2 && bl.every((l) => l.amount > 0)) {
    ok('B2. ...and billing STILL GETS BOTH LINES, priced. The redaction is the '
       + 'drug name, not the charge -- a biller who cannot see the invoice is a '
       + 'worse outcome than the defect');
  } else {
    bad('B2. billing must still get both priced lines',
        JSON.stringify(bl).slice(0, 300));
  }
  if (r.body && r.body.mar_description_withheld === true) {
    ok('B3. ...and billing is TOLD -- mar_description_withheld:true. A blank '
       + 'description and a withheld one are indistinguishable to a biller, so '
       + 'the response says which it is');
  } else {
    bad('B3. the redaction must be declared on the response',
        'mar_description_withheld='
        + JSON.stringify(r.body && r.body.mar_description_withheld));
  }

  console.log('\nC. THE PRICE DID NOT MOVE -- description is display-only, proven not assumed');
  {
    const o = medLines(await derive('owner'));
    const b = medLines(await derive('billing'));
    const sum = (xs) => xs.reduce((a, x) => a + Number(x.amount || 0), 0);
    if (o.length === b.length && sum(o) === sum(b) && sum(o) > 0) {
      ok('C1. owner and billing get the SAME number of lines and the SAME '
         + 'total (' + sum(o) + '). care-charges.js prices on e.type through '
         + 'CHARGEABLE[type].rate_key and never on description, and this is the '
         + 'arm that proves the redaction cost the billing answer nothing');
    } else {
      bad('C1. the redaction must not change the priced total',
          'owner=' + sum(o) + ' billing=' + sum(b));
    }
  }

  console.log('\nD. ALF_MAR_ROLES STILL SEE THE NAME -- without this, redact-for-all would pass B');
  for (const role of ['owner']) {
    r = await derive(role);
    if (mentions(r, DRUG) && r.body.mar_description_withheld === false) {
      ok('D. ' + role + ' is in ALF_MAR_ROLES and still receives the drug name, '
         + 'with mar_description_withheld:false. WITHOUT THIS ARM the fix could '
         + 'redact for every role and every arm in B would still pass');
    } else {
      bad('D. ' + role + ' must still see the medication name',
          'sees=' + mentions(r, DRUG) + ' withheld='
          + JSON.stringify(r.body && r.body.mar_description_withheld));
    }
  }

  console.log('\nE. THE OTHER SIDE OF THE DIFFERENCE IS STILL REFUSED THE ACTION');
  for (const role of ['nursing', 'med_aide', 'caregiver', 'activities']) {
    r = await derive(role);
    if (r.statusCode === 403) {
      ok('E. ' + role + ' is still 403 on derive_charges itself -- the fix '
         + 'narrowed what `billing` SEES and widened nothing');
    } else {
      bad('E. ' + role + ' must stay 403 on derive_charges',
          'status=' + r.statusCode);
    }
  }

  console.log('\nF. NO SESSION');
  r = await derive(null);
  if (r.statusCode === 401 && r.body && r.body.error
      && r.body.error.code === 'NO_SESSION') {
    ok('F1. no session is 401 NO_SESSION');
  } else {
    bad('F1. no session must be 401 NO_SESSION', 'status=' + r.statusCode);
  }

  console.log('\nG. PINNED AT SOURCE -- the OWNING table\'s set, not a new one');
  const fs = require('fs');
  const SRC = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  const CODE = SRC.split(/\r?\n/)
    .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  const ANCHOR = "if (resource === 'alf_billing' && action === 'derive_charges')";
  const n = CODE.split(ANCHOR).length - 1;
  if (n !== 1) {
    bad('G0. the source anchor must match EXACTLY ONCE -- it matched ' + n
        + ' time(s), so G1 cannot say which block it measured and is NOT run', '');
  } else {
    ok('G0. the derive_charges anchor matches exactly once');
    const block = CODE.split(ANCHOR)[1].split(/\n {4}if \(/)[0];
    if (/ALF_MAR_ROLES\[session\.role\]/.test(block)) {
      ok('G1. the branch consults ALF_MAR_ROLES -- the set alf_mar/read uses '
         + 'for the same table -- rather than inventing a third list. A gate '
         + 'that disagrees with the table\'s own reader is the defect, not the '
         + 'fix');
    } else {
      bad('G1. the branch must consult ALF_MAR_ROLES', '');
    }
    if (!/description_withheld:/.test(block)) {
      ok('G2. the withheld flag is NOT set on the event object. Setting it '
         + 'there was the first version of this fix and it was a SILENT NO-OP '
         + '-- care-charges.js copies a fixed field list to each line and drops '
         + 'the rest, so the flag never reached the caller while the redaction '
         + 'did');
    } else {
      bad('G2. the flag must not be set on the event, where it is dropped', '');
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
