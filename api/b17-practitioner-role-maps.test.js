// api/b17-practitioner-role-maps.test.js
//
// Run:  node api/b17-practitioner-role-maps.test.js
//
// REQUIREMENT: Michael's b17 practitioner answers are recorded in ONE PLACE
//   EACH, as role maps and constants, and are driven rather than described.
//
//   SEN  a home-care coordinator taking a phone referral may write intake
//        without a manager -- retire Option B for that role
//   LEG  funeral prep gets a licensed-embalmer tier; livery is blocked from
//        leg_dispatches and leg_custodylog unless access is granted by
//        personnel above them
//   VET  the practice manager gets access to clinical records; a vet tech may
//        record controlled substances like a med-pass log; no HIPAA claim for
//        animals, confidentiality is good practice
//
// ── WHY A SUITE AND NOT A COMMENT ────────────────────────────────────────
// Two of these answers CHANGE NO CODE -- the manager's clinical read was
// already `r`, and livery was already `NO` on both funeral resources. An
// answer that changes nothing is the one most likely to be silently reversed
// later by somebody who reads the row and not the decision, so each is pinned
// by an arm. The other two change real access and are driven at the handler.
//
// ── AND ONE ANSWER IS RECORDED WITH NOTHING TO APPLY IT TO ───────────────
// The licensed-embalmer tier has NO RESOURCE in this app: SAIRNlegacy's 36
// rows contain no preparation-room record. Building a tier that granted
// something today would be dormant code -- Guardian Check 0d exactly. So the
// decision is recorded and arm L-E2 is a LIVE check that fails if a
// preparation-room resource is ever added without a tier decision on it.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['b17', 'prac', String(process.pid)].join('-');
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');

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
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// ── DRIVE THE REAL SAIRNSENIOR REFERRAL BRANCH ───────────────────────────
async function driveSen(opts) {
  const o = opts || {};
  const writes = [];
  const licResolved = require.resolve('./_lib/license');
  require.cache[licResolved] = {
    id: licResolved, filename: licResolved, loaded: true,
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH, trial_ends_at: null,
        stripe_subscription_id: null, app_id: 'sairnsenior' })
    }
  };
  const res200 = (rows) => ({ ok: true, status: 200, headers: { get: () => '' },
    text: async () => JSON.stringify(rows), json: async () => rows });
  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth\?/.test(u)) {
      return res200([{ license_hash: HASH, employee_id: 'E1',
                       role: o.role, active: true }]);
    }
    if (method !== 'GET') {
      let p = null;
      try { p = JSON.parse(init.body); } catch (e) { p = null; }
      writes.push({ url: u, body: p });
      return res200([p]);
    }
    return res200([]);
  };
  ['./sen-auth.js', './sd-data.js'].forEach((m) => {
    try { delete require.cache[require.resolve(m)]; } catch (e) { /* absent */ }
  });
  const handler = require('./sd-data.js');
  const { signSessionToken } = require('./_lib/auth');
  const out = { statusCode: null, body: null };
  out.status = (c) => { out.statusCode = c; return out; };
  out.json = (b) => { out.body = b; return out; };
  await handler({ method: 'POST',
    headers: { authorization: 'Bearer ' + KEY,
               'x-sd-auth': signSessionToken({ app: 'sairnsenior',
                 employee_id: 'E1', role: o.role, license_hash: HASH }) },
    body: { action: 'write', resource: o.resource,
            payload: { id: 'X1', note: 'phone referral' } } }, out);
  return { status: out.statusCode, body: out.body,
           writes: writes.filter((w) => new RegExp(o.resource).test(w.url)) };
}
function code(r) { return r.body && r.body.error && r.body.error.code; }

async function main() {
  console.log('api/b17-practitioner-role-maps.test.js');
  console.log('  Michael\'s b17 practitioner answers, one place each, driven');

  // ══ SAIRNSENIOR: INTAKE ════════════════════════════════════════════════
  const senAuth = require('./sen-auth.js');

  // S-I1: the decision, at the handler.
  try {
    const r = await driveSen({ role: 'coordinator', resource: 'sen_referrals' });
    is(r.status === 200 && r.writes.length === 1,
       'S-I1. a COORDINATOR writes sen_referrals: 200 and the row lands. '
     + 'Michael: a home-care coordinator taking a phone referral may write '
     + 'intake without a manager',
       'status=' + r.status + ' code=' + code(r) + ' writes=' + r.writes.length);
  } catch (e) {
    bad('S-I1. a coordinator writes sen_referrals', e && e.stack);
  }

  // S-I2: ...and the source too, because a referral from a hospital not yet
  // on file is the case that would otherwise send them back to a manager.
  try {
    const r = await driveSen({ role: 'coordinator', resource: 'sen_referral_sources' });
    is(r.status === 200,
       'S-I2. a COORDINATOR writes sen_referral_sources too -- a referral from '
     + 'a hospital not yet on file would otherwise be defeated by its own '
     + 'prerequisite and send the coordinator back to a manager\'s desk',
       'status=' + r.status + ' code=' + code(r));
  } catch (e) {
    bad('S-I2. a coordinator writes sen_referral_sources', e && e.stack);
  }

  // S-I3: CONTROL -- the three that are NOT intake did not move.
  for (const res of ['sen_applicants', 'sen_training_records', 'sen_training_rules']) {
    try {
      const r = await driveSen({ role: 'coordinator', resource: res });
      is(r.status === 403 && code(r) === 'FORBIDDEN' && r.writes.length === 0,
         'S-I3. CONTROL -- a coordinator is STILL refused on ' + res
       + '. The decision was about intake; an applicant record is employment '
       + 'data about somebody not yet staff and a training rule decides '
       + 'whether a caregiver may work at all',
         'status=' + r.status + ' code=' + code(r));
    } catch (e) {
      bad('S-I3. CONTROL -- a coordinator is still refused on ' + res, e && e.stack);
    }
  }

  // S-I4: CONTROL -- SCHEDULER WAS NOT GRANTED. fourth's Option A was
  // "+ coordinator, scheduler"; Michael named the coordinator.
  try {
    const r = await driveSen({ role: 'scheduler', resource: 'sen_referrals' });
    is(r.status === 403 && code(r) === 'FORBIDDEN',
       'S-I4. CONTROL -- a SCHEDULER is still refused on sen_referrals. '
     + 'fourth\'s Option A was "+ coordinator, scheduler" and Michael named '
     + 'the COORDINATOR, so an access decision is read at its narrowest',
       'status=' + r.status + ' code=' + code(r));
  } catch (e) {
    bad('S-I4. CONTROL -- a scheduler is still refused', e && e.stack);
  }

  // S-I5: a caregiver never had this and still does not.
  try {
    const r = await driveSen({ role: 'caregiver', resource: 'sen_referrals' });
    is(r.status === 403,
       'S-I5. CONTROL -- a CAREGIVER is refused: a referral names a '
     + 'PROSPECTIVE client and the reason they were referred',
       'status=' + r.status + ' code=' + code(r));
  } catch (e) {
    bad('S-I5. CONTROL -- a caregiver is refused', e && e.stack);
  }

  // S-I6: the map is complete, and a missing row is a REFUSAL not a default.
  {
    const map = senAuth.SEN_REFERRAL_WRITE_ROLES || {};
    const sd = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const resList = /const SEN_REFERRAL_RESOURCES = \{([\s\S]*?)\};/.exec(sd);
    const names = resList
      ? (resList[1].match(/([a-z_]+):/g) || []).map((x) => x.replace(':', ''))
      : [];
    const uncovered = names.filter((n) => !map[n]);
    is(names.length === 5 && uncovered.length === 0
       && /WRITE_MAP_MISSING/.test(sd),
       'S-I6. all ' + names.length + ' SEN_REFERRAL_RESOURCES have a row in '
     + 'SEN_REFERRAL_WRITE_ROLES, and a resource with NO row gets a 500 '
     + 'WRITE_MAP_MISSING rather than inheriting whichever set is nearest in '
     + 'the file -- which is how a broad-READ set came to decide a WRITE',
       'resources=' + JSON.stringify(names)
     + ' uncovered=' + JSON.stringify(uncovered)
     + ' refusesUnmapped=' + /WRITE_MAP_MISSING/.test(sd));
  }

  // S-I7: and the policy is in ONE place -- the branch reads the map.
  {
    const sd = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
    const branch = /SEN_REFERRAL_WRITE_ROLES\[resource\]/.test(sd);
    const noLocalTest = !/senAuth\.MANAGEMENT_ROLES\[session\.role\]\)\s*\{\s*\n\s*res\.status\(403\)[\s\S]{0,200}referral, applicant or/.test(sd);
    is(branch && noLocalTest,
       'S-I7. the referral branch READS the map and no longer tests a role '
     + 'itself. A role test in the branch is a second copy of the answer the '
     + 'day a sixth resource joins',
       'readsMap=' + branch + ' oldLocalTestGone=' + noLocalTest);
  }

  // ══ SAIRNLEGACY: THE EMBALMER TIER AND THE LIVERY GRANT ════════════════
  const legRoles = require('./_lib/leg-roles');

  // L-E1: the tier is recorded, in the file that owns leg role policy.
  {
    const t = legRoles.LEG_EMBALMER_TIER || {};
    is(t.tier === 'licensed_embalmer' && t.role === 'embalmer'
       && /2026-10-15/.test(String(t.recorded))
       && typeof t.grants === 'string' && t.grants.length > 10,
       'L-E1. the licensed-embalmer tier is RECORDED in api/_lib/leg-roles.js '
     + 'with the role name it would use and what it would grant, so a future '
     + 'implementer reads the decision instead of re-deriving it',
       JSON.stringify(t));
  }

  // L-E2: THE LIVE CHECK. The tier applies to nothing today because there is
  // no preparation-room resource. If one appears, it must carry a decision.
  {
    const names = legRoles.resources();
    const prepish = names.filter((n) =>
      /prep|embalm|mortuary|preparation/i.test(n));
    const undecided = prepish.filter((n) => !legRoles.LEG_PREP_ROOM_RESOURCES[n]);
    is(undecided.length === 0,
       'L-E2. no preparation-room resource exists in SAIRNlegacy\'s '
     + names.length + ' rows (measured, not assumed), so the embalmer tier '
     + 'grants nothing today and no dormant policy was written. If one is '
     + 'added it must carry a tier decision in LEG_PREP_ROOM_RESOURCES or '
     + 'this arm fails',
       'resources matching prep/embalm/mortuary with NO tier decision: '
     + JSON.stringify(undecided));
  }

  // L-L1: livery is blocked on both, which it already was -- pinned so it
  // cannot be reversed by somebody reading the band and not the decision.
  {
    const bad2 = [];
    ['leg_dispatches', 'leg_custodylog'].forEach((r) => {
      ['read', 'write'].forEach((a) => {
        if (legRoles.decide(r, 'livery', a) !== legRoles.DENY) bad2.push(r + '/' + a);
      });
    });
    is(bad2.length === 0,
       'L-L1. livery is DENIED read and write on leg_dispatches and '
     + 'leg_custodylog with no grant present. The REGULATED band already gave '
     + 'livery NO, so no row changed -- which is exactly why it is pinned',
       'allowed where it must not be: ' + JSON.stringify(bad2));
  }

  // L-L2: ...unless access is granted by personnel above them.
  {
    const g = { leg_dispatches: true };
    is(legRoles.decide('leg_dispatches', 'livery', 'read', g) === legRoles.ALLOW
       && legRoles.decide('leg_dispatches', 'livery', 'write', g) === legRoles.DENY,
       'L-L2. WITH a grant, livery may READ leg_dispatches and still may NOT '
     + 'write it. A grant yields read only: leg_custodylog is append-only for '
     + 'every role including the owner, so a write grant would be a route '
     + 'around that lock',
       'read=' + legRoles.decide('leg_dispatches', 'livery', 'read', g)
     + ' write=' + legRoles.decide('leg_dispatches', 'livery', 'write', g));
  }

  // L-L3: CONTROL -- a grant cannot open a resource that is not grantable,
  // and cannot open anything for a role that is not livery.
  {
    const wide = { leg_deathrecords: true, leg_cremations: true, leg_dispatches: true };
    const leaks = [];
    if (legRoles.decide('leg_deathrecords', 'livery', 'read', wide) !== legRoles.DENY) {
      leaks.push('leg_deathrecords opened by a grant');
    }
    if (legRoles.decide('leg_cremations', 'livery', 'read', wide) !== legRoles.DENY) {
      leaks.push('leg_cremations opened by a grant');
    }
    if (legRoles.decide('leg_dispatches', 'apprentice', 'write', wide) !== legRoles.DENY) {
      leaks.push('a non-livery role got write from a livery grant');
    }
    is(leaks.length === 0,
       'L-L3. CONTROL -- a grant opens ONLY the two grantable resources and '
     + 'ONLY for livery. Without this arm the grant could be "any resource '
     + 'named in an object the caller controls", which is worse than the block '
     + 'it replaces',
       JSON.stringify(leaks));
  }

  // L-L4: and who may grant is named, narrowly.
  {
    const gr = legRoles.LEG_LIVERY_GRANTOR_ROLES || {};
    const grantable = legRoles.LEG_LIVERY_GRANTABLE || {};
    is(!!gr.owner && !!gr.director && !gr.arranger && !gr.office && !gr.livery
       && Object.keys(grantable).sort().join(',') === 'leg_custodylog,leg_dispatches',
       'L-L4. "personnel above them" is owner and director -- the two roles '
     + 'with RW on REGULATED -- and the grantable set is exactly the two '
     + 'resources Michael named. Livery cannot grant itself',
       'grantors=' + JSON.stringify(gr)
     + ' grantable=' + JSON.stringify(Object.keys(grantable)));
  }

  // ══ SAIRNVET ═══════════════════════════════════════════════════════════
  const svRoles = require('./_lib/sv-roles');

  // V-M: the manager's clinical read, CONFIRMED AS BUILT. No row changed.
  {
    const clinical = ['sv_soapnotes', 'sv_labresults', 'sv_imaging'];
    const present = clinical.filter((r) => svRoles.resources().indexOf(r) !== -1);
    const reads = present.filter((r) =>
      svRoles.decide(r, 'manager', 'read') === svRoles.ALLOW);
    const writes = present.filter((r) =>
      svRoles.decide(r, 'manager', 'write') === svRoles.ALLOW);
    is(present.length >= 2 && reads.length === present.length && writes.length === 0,
       'V-M. the practice MANAGER reads clinical records and writes none, on '
     + 'all ' + present.length + ' driven. Michael CONFIRMED the spec\'s own '
     + 'proposed answer, which it had called "the one most likely to be '
     + 'wrong" -- so nothing changed and the [CONFIRM] is now closed',
       'present=' + JSON.stringify(present) + ' reads=' + reads.length
     + ' writes=' + JSON.stringify(writes));
  }

  // V-T: the tech may record a controlled substance.
  {
    is(svRoles.decide('sv_controlled', 'tech', 'write') === svRoles.ALLOW
       && svRoles.decide('sv_controlled', 'assistant', 'write') === svRoles.DENY
       && svRoles.decide('sv_controlled', 'frontdesk', 'write') === svRoles.DENY,
       'V-T. a vet TECH may write sv_controlled, and assistant and frontdesk '
     + 'still may not. "Like a med-pass log" widened the RECORDER by one role',
       'tech=' + svRoles.decide('sv_controlled', 'tech', 'write')
     + ' assistant=' + svRoles.decide('sv_controlled', 'assistant', 'write')
     + ' frontdesk=' + svRoles.decide('sv_controlled', 'frontdesk', 'write'));
  }

  // V-W: THE CO-SIGNATURE HALF. The witness set did NOT widen, which is the
  // thing that makes V-T safe rather than a hole in a DEA register.
  {
    const witness = require('./sv-witness');
    const prescribers = require('./sv-auth').PRESCRIBER_ROLES || {};
    is(!!witness.LOCKED_RESOURCES.sv_controlled
       && !prescribers.tech && !!prescribers.owner && !!prescribers.dvm,
       'V-W. the WITNESSING LOCK still covers sv_controlled and PRESCRIBER_ROLES '
     + 'still excludes tech -- so a tech-recorded entry cannot be FILED '
     + 'without a licensed veterinarian countersigning. Widening the recorder '
     + 'and widening the witness are two decisions and Michael made one',
       'locked=' + !!witness.LOCKED_RESOURCES.sv_controlled
     + ' prescribers=' + JSON.stringify(prescribers));
  }

  // V-H: NO HIPAA CLAIM FOR ANIMALS. A false compliance claim is the class
  // sairn-decision-gate exists for, so this is mechanical rather than a note.
  {
    const files = ['sairnvet.html', 'api/sv-auth.js', 'api/sv-witness.js',
                   'api/_lib/sv-roles.js'];
    const hits = [];
    files.forEach((f) => {
      let src = null;
      try { src = fs.readFileSync(path.join(ROOT, f), 'utf8'); }
      catch (e) { return; }
      const re = /HIPAA/gi;
      let m;
      while ((m = re.exec(src)) !== null) {
        const win = src.slice(Math.max(0, m.index - 160), m.index + 160);
        // A sentence SAYING HIPAA does not apply is the correct content and is
        // not a claim. Only an assertion of compliance/coverage is.
        if (/not\s+(?:apply|PHI|HIPAA)|no HIPAA|does not apply|is not PHI|not a HIPAA|human/i.test(win)) continue;
        hits.push(f + ' :: ' + win.replace(/\s+/g, ' ').slice(0, 120));
      }
    });
    is(hits.length === 0,
       'V-H. no file in SAIRNvet CLAIMS HIPAA coverage. HIPAA protects a '
     + 'HUMAN\'s identifiable health information; a veterinary record is not '
     + 'PHI, and claiming otherwise is a false compliance claim. '
     + 'Confidentiality here is GOOD PRACTICE and is stated as such',
       JSON.stringify(hits));
  }

  console.log('');
  console.log('  passed ' + pass + '  failed ' + fail + '  unproven ' + unproven);
  if (fail) console.log('  FAILING ARMS: ' + failed.join(' '));
  if (unproven) console.log('  UNPROVEN ARMS: ' + notProved.join(' '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main().catch((e) => { console.log('  HARD ERROR ' + (e && e.stack)); process.exit(1); });
