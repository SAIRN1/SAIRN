// api/sv-auth.test.js
//
// Run:  node api/sv-auth.test.js
//
// Control for api/sv-auth.js -- SAIRNvet per-employee auth, the sixteenth and
// last app to get one, built because the app holding a DEA-relevant
// controlled-substance register knew which PRACTICE was writing and never which
// PERSON.
//
// WHY THE STRUCTURAL HALF IS ASSERTED FROM CODE ANCHORS, NEVER FROM PROSE.
// This endpoint's header carries long comments naming the very constructs the
// assertions look for. api/preauth-envelope-ordering.test.js records the trap
// exactly: a detector's boundary regex matched `verifySessionToken(` inside a
// HEADER COMMENT in law-auth.js and mech-auth.js, so both files reported zero
// findings while carrying the defect. Every source assertion below therefore
// runs against COMMENT-STRIPPED source, and the stripper's own output is
// checked first -- a stripper that blanked everything would make every
// "must not appear" assertion pass by construction.
//
// AND WHY THE BEHAVIOURAL HALF IS NOT HERE. On a developer machine SUPABASE_URL
// is unset, so almost any call to this endpoint returns a config 500 and a test
// written against that passes whether the logic is right or not -- the recorded
// lesson of api/sd-sub-data-auth-ordering.test.js. The live sequence is written
// down in the skill's §14 checklist (bootstrap -> 409 -> login -> 5 wrong PINs
// -> 429 -> whoami -> setup -> roster -> set_active off -> login fails ->
// set_active on -> last-owner 409) and must be run against the real deployment
// by somebody holding a licence key. THIS FILE DOES NOT CLAIM THAT WAS DONE.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const SRC_RAW = fs.readFileSync(path.join(ROOT, 'api', 'sv-auth.js'), 'utf8');
const SCHEMA = fs.readFileSync(
  path.join(ROOT, 'sql', 'sairnvet_employee_auth_schema.sql'), 'utf8');

// Comment-stripped view. Uses the platform's single stripper rather than a
// fourth local regex -- tools/jscomments.py's own header records three
// implementations destroying up to 89% of a file while reporting CLEAN.
function stripJsComments(src) {
  let out = '';
  let i = 0;
  const n = src.length;
  let prev = '';
  const REGEX_OK = new Set('(,=:[!&|?{};+-*%~^'.split('').concat(['']));
  while (i < n) {
    const c = src[i], nx = src[i + 1] || '';
    if (c === '/' && nx === '*') { const j = src.indexOf('*/', i + 2); i = j === -1 ? n : j + 2; continue; }
    if (c === '/' && nx === '/') { const j = src.indexOf('\n', i); i = j === -1 ? n : j; continue; }
    if (c === '"' || c === "'" || c === '`') {
      const q = c; let j = i + 1;
      while (j < n) {
        if (src[j] === '\\') { j += 2; continue; }
        if (src[j] === q) { j++; break; }
        if (q !== '`' && src[j] === '\n') break;
        j++;
      }
      out += src.slice(i, j); i = j; prev = q; continue;
    }
    if (c === '/' && REGEX_OK.has(prev)) {
      let j = i + 1, ok = false;
      while (j < n && src[j] !== '\n') {
        if (src[j] === '\\') { j += 2; continue; }
        if (src[j] === '/') { ok = true; j++; break; }
        j++;
      }
      if (ok) { out += src.slice(i, j); i = j; prev = '/'; continue; }
    }
    if (!/\s/.test(c)) prev = c;
    out += c; i++;
  }
  return out;
}
const SRC = stripJsComments(SRC_RAW);

// SQL with `--` comments blanked. Length-preserving, so any offset comparison
// stays true. Needed for the same reason SRC is: this schema's comments
// deliberately spell out the verbs it must NOT grant.
const SQL_CODE = SCHEMA.split('\n')
  .map((l) => { const i = l.indexOf('--'); return i === -1 ? l : l.slice(0, i); })
  .join('\n');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

// ── 0. THE STRIPPER ITSELF ──────────────────────────────────────────────────
// Without this every "must not appear" assertion below would pass on an empty
// string. Same class as the vacuous-check arms this repo keeps finding.
section('0. the comment stripper did not eat the file');
t('the stripped source still holds most of the code', () => {
  assert.ok(SRC.length > SRC_RAW.length * 0.25,
    'stripper kept only ' + Math.round(100 * SRC.length / SRC_RAW.length) + '%');
});
t('...and the comments really are gone', () => {
  assert.ok(SRC.indexOf('THE SIXTEENTH AND LAST APP') === -1);
  assert.ok(SRC_RAW.indexOf('THE SIXTEENTH AND LAST APP') !== -1);
});

// ── 1. THE ENVELOPE GATE ORDERING ───────────────────────────────────────────
section('1. the envelope gate answers BELOW licence validation');
t('validateLicenseKey is called before the body is parsed', () => {
  const lic = SRC.indexOf('await validateLicenseKey(');
  const parse = SRC.indexOf('JSON.parse(body)');
  assert.ok(lic > 0 && parse > 0, 'both anchors present');
  assert.ok(lic < parse,
    'a caller with no credential could otherwise tell malformed JSON from a bad licence');
});
t('...and before the action allowlist answers', () => {
  const lic = SRC.indexOf('await validateLicenseKey(');
  const act = SRC.indexOf('ACTIONS.indexOf(action)');
  assert.ok(act > 0 && lic < act,
    'the action refusal names this app\'s whole verb vocabulary');
});
t('a non-POST is refused before anything else', () => {
  // Anchored on the CALL, not the bare name: `validateLicenseKey` also appears
  // in the require() line at the top of the file, which is above everything and
  // made the first version of this assertion compare against the wrong offset.
  const m = SRC.indexOf("req.method !== 'POST'");
  const lic = SRC.indexOf('await validateLicenseKey(');
  assert.ok(m > 0 && lic > 0, 'both anchors present');
  assert.ok(m < lic, 'a 405 must cost no licence lookup');
});
t('a missing bearer costs no licence lookup', () => {
  assert.ok(SRC.indexOf('NO_LICENSE') < SRC.indexOf('await validateLicenseKey('));
});

// ── 2. THE ROLE MODEL AND ITS TIERS ─────────────────────────────────────────
section('2. the role model, and the tier the witnessing lock keys on');
const sv = require('./sv-auth.js');
const { ROLES_BY_APP } = require('./_lib/auth.js');
t('sairnvet is registered in ROLES_BY_APP', () => {
  assert.ok(Array.isArray(ROLES_BY_APP.sairnvet), 'signSessionToken throws on an unknown app');
});
t('the vocabulary is the app\'s own six, and NOT seven', () => {
  assert.deepStrictEqual(ROLES_BY_APP.sairnvet,
    ['owner', 'dvm', 'tech', 'assistant', 'manager', 'frontdesk']);
});
t("...so the roster's 'Other' option is not an identity", () => {
  assert.ok(ROLES_BY_APP.sairnvet.indexOf('other') === -1);
  assert.ok(ROLES_BY_APP.sairnvet.indexOf('Other') === -1);
});
t('only owner provisions', () => {
  assert.deepStrictEqual(sv.PROVISIONING_ROLES, ['owner']);
});
t('the credential roster is management-only, and a DVM is not management', () => {
  assert.strictEqual(sv.MANAGEMENT_ROLES.owner, true);
  assert.strictEqual(sv.MANAGEMENT_ROLES.manager, true);
  assert.ok(!sv.MANAGEMENT_ROLES.dvm, 'the roster is the access-control surface, not app data');
});

// THE ARM THIS FILE EXISTS FOR. A controlled-substance entry is a legal act by
// a licensed veterinarian, and the witnessing lock must key on a tier it
// IMPORTS rather than a role list it re-types -- the drift that cost
// SAIRNsenior a real bug when one function used senIsManagement() where the
// rest used senIsBroadRead().
section('3. PRESCRIBER_ROLES -- the licensed-practitioner tier');
t('owner and dvm are prescribers', () => {
  assert.strictEqual(sv.isPrescriber({ role: 'owner' }), true);
  assert.strictEqual(sv.isPrescriber({ role: 'dvm' }), true);
});
t('a technician is NOT', () => {
  assert.strictEqual(sv.isPrescriber({ role: 'tech' }), false);
});
t('an assistant is NOT', () => {
  assert.strictEqual(sv.isPrescriber({ role: 'assistant' }), false);
});
t('A PRACTICE MANAGER IS NOT -- they run the office and are not a clinician', () => {
  assert.strictEqual(sv.isPrescriber({ role: 'manager' }), false,
    'conflating the two is how a non-veterinarian is recorded as the author of a DEA-relevant row');
});
t('front desk is NOT', () => {
  assert.strictEqual(sv.isPrescriber({ role: 'frontdesk' }), false);
});
t('no session at all is NOT', () => {
  assert.strictEqual(sv.isPrescriber(null), false);
  assert.strictEqual(sv.isPrescriber(undefined), false);
  assert.strictEqual(sv.isPrescriber({}), false);
});
t('the tier is EXPORTED so a gate imports it instead of re-listing roles', () => {
  assert.ok(sv.PRESCRIBER_ROLES && sv.PRESCRIBER_ROLES.dvm === true);
});
t('every prescriber role is a real role in the app vocabulary', () => {
  Object.keys(sv.PRESCRIBER_ROLES).forEach((r) => {
    assert.ok(ROLES_BY_APP.sairnvet.indexOf(r) !== -1, r + ' is not a sairnvet role');
  });
});

// ── 4. THE INVARIANTS THAT ARE NOT OPTIONAL ─────────────────────────────────
section('4. the lifted invariants');
t('the timing-equalised PIN comparison is byte-identical to the family', () => {
  assert.ok(SRC.indexOf(
    'const pinOk = row ? verifyPin(pin, row.pin_hash, row.pin_salt) : verifyPin(pin, null, null);') !== -1,
    'a short-circuit here enumerates valid employee IDs -- real 2026-08-03 finding');
});
t('one generic credential failure, never which half was wrong', () => {
  assert.ok(SRC.indexOf('Incorrect employee ID or PIN') !== -1);
  assert.ok(SRC.indexOf('No such employee ID') === -1);
  assert.ok(SRC.indexOf('Wrong PIN') === -1);
});
t('lockout is the platform-wide 5 / 15', () => {
  assert.ok(/LOCKOUT_THRESHOLD\s*=\s*5/.test(SRC));
  assert.ok(/LOCKOUT_MINUTES\s*=\s*15/.test(SRC));
});
t('the lock check precedes verifyPin', () => {
  assert.ok(SRC.indexOf('isLocked(row)') < SRC.indexOf('const pinOk ='));
});
t('a post-lockout success clears BOTH fields, not just the counter', () => {
  assert.ok(SRC.indexOf('!row.failed_attempts && !row.locked_until') !== -1,
    'sc and sd test only the counter and leave a stale locked_until forever');
});
t('every REST query is licence-filtered -- there is no unfiltered read', () => {
  const reads = SRC.split('rest(TABLE').slice(1);
  assert.ok(reads.length >= 4, 'found ' + reads.length + ' table queries');
  reads.forEach((r, i) => {
    const head = r.slice(0, 200);
    assert.ok(head.indexOf('license_hash=eq.') !== -1 || head.indexOf('method:') !== -1
      || /^\s*\)/.test(head),
      'query ' + i + ' is not licence-filtered: ' + head.slice(0, 80));
  });
});
t('expectedApp is passed on every session verification', () => {
  // `[^)]*` stops at the FIRST close paren, and every call here nests one --
  // verifySessionToken(tokenFromRequest(req), licHash, APP) -- so the naive
  // form never saw the third argument and failed on correct code. Read to the
  // BALANCED close instead. A regex that cannot see the thing it is checking
  // is the same shape as one that matches prose about the code.
  let i = 0, n = 0;
  while ((i = SRC.indexOf('verifySessionToken(', i)) !== -1) {
    let j = i + 'verifySessionToken('.length, depth = 1;
    while (j < SRC.length && depth > 0) {
      if (SRC[j] === '(') depth++;
      else if (SRC[j] === ')') depth--;
      j++;
    }
    const call = SRC.slice(i, j);
    assert.ok(/,\s*APP\s*\)/.test(call),
      'without expectedApp a valid owner token from another app would pass: ' + call);
    n++; i = j;
  }
  assert.ok(n >= 4, 'found only ' + n + ' session verifications');
});

// ── 5. THE BOOTSTRAP TRAPDOOR ───────────────────────────────────────────────
section('5. the bootstrap trapdoor stays absolute');
t('the existence probe does NOT filter on active', () => {
  const i = SRC.indexOf("action === 'bootstrap'");
  const j = SRC.indexOf("action === 'login'");
  const branch = SRC.slice(i, j);
  const probe = branch.slice(branch.indexOf('select=id'));
  assert.ok(branch.indexOf('select=id&limit=1') !== -1, 'the probe is present');
  assert.ok(probe.indexOf('active=eq.true') === -1,
    'a softer probe lets anyone with the licence key deactivate their way to a fresh owner');
});
t('a second bootstrap is refused with ALREADY_PROVISIONED', () => {
  assert.ok(SRC.indexOf('ALREADY_PROVISIONED') !== -1);
});

// ── 6. THE DEACTIVATION LIFECYCLE ───────────────────────────────────────────
section('6. set_active -- guard ordering, and deactivate-never-delete');
const SA = SRC.slice(SRC.indexOf("action === 'set_active'"));
t('self-deactivation is refused BEFORE the roster read', () => {
  const self = SA.indexOf('SELF_DEACTIVATE');
  const roster = SA.indexOf('select=employee_id,role,active');
  assert.ok(self > 0 && roster > 0 && self < roster,
    'an already-deactivated caller must get SELF_DEACTIVATE, not CREDENTIAL_INACTIVE');
});
t('a reason is required to deactivate and not to reactivate', () => {
  assert.ok(SA.indexOf('!nextActive && !reason') !== -1);
});
t('the caller-still-active re-check is computed off the same one read', () => {
  assert.ok(SA.indexOf('CREDENTIAL_INACTIVE') !== -1);
  assert.ok(SA.indexOf('callerRow.active !== true') !== -1);
});
t('the last-owner guard is present and quarantined, not deleted', () => {
  assert.ok(SA.indexOf('LAST_OWNER') !== -1);
  assert.ok(SRC_RAW.indexOf('QUARANTINED, NOT DEAD') !== -1,
    'the comment explaining why it looks unused must survive, or somebody removes it');
});
t('the wire format is LAST_OWNER / remaining_owners, stated in the header', () => {
  assert.ok(SA.indexOf('remaining_owners') !== -1);
  assert.ok(SA.indexOf('remaining_admins') === -1, 'the platform has two spellings; pick one');
  assert.ok(SRC_RAW.indexOf('WIRE FORMAT') !== -1);
});
t('NOTHING in this endpoint deletes a credential row', () => {
  assert.ok(SRC.indexOf("method: 'DELETE'") === -1);
  assert.ok(!/\bdelete\b/i.test(SRC.replace(/merge-duplicates/g, '')),
    'deactivation is active=false; a delete orphans the author of a DEA-relevant record');
});
t('the PATCH result is only parsed when it failed', () => {
  assert.ok(SA.indexOf('if (!patchR.ok)') !== -1,
    'PostgREST answers 204 No Content, and parsing it unconditionally 502s a landed write');
});

// ── 7. DIAGNOSTICS AND HONESTY ──────────────────────────────────────────────
section('7. diagnostics, and the audit gap stated rather than implied');
t('NOT_PROVISIONED and NOT_GRANTED are distinguished', () => {
  assert.ok(SRC.indexOf('NOT_PROVISIONED') !== -1);
  assert.ok(SRC.indexOf('NOT_GRANTED') !== -1);
});
t('...and each names the file that fixes it', () => {
  assert.ok(SRC.indexOf('sql/sairnvet_employee_auth_schema.sql') !== -1);
});
t('set_active reports audited:false rather than implying coverage', () => {
  assert.ok(SA.indexOf('audited: false') !== -1,
    'api/_lib/audit.js allowlists three tables and sairnvet is not one');
});
t('all seven actions ship', () => {
  ['check_license', 'whoami', 'bootstrap', 'login', 'setup', 'roster', 'set_active']
    .forEach((a) => assert.ok(SRC.indexOf("'" + a + "'") !== -1, 'missing ' + a));
});
t('roster includes inactive rows so a deactivation can be undone', () => {
  const R = SRC.slice(SRC.indexOf("action === 'roster'"), SRC.indexOf("action === 'set_active'"));
  assert.ok(R.indexOf('active=eq.true') === -1,
    'filtering here makes a deactivated person invisible to the only person who can restore them');
});
t('roster never returns the PIN material', () => {
  const R = SRC.slice(SRC.indexOf("action === 'roster'"), SRC.indexOf("action === 'set_active'"));
  assert.ok(R.indexOf('pin_hash') === -1 && R.indexOf('pin_salt') === -1);
});

// ── 8. THE SCHEMA ───────────────────────────────────────────────────────────
section('8. the schema grants, and what it deliberately does not contain');
t('no DELETE grant', () => {
  // ASSERTED AGAINST COMMENT-STRIPPED SQL, and the first version was not.
  // `grant[^;]*delete` matched the FILE'S OWN COMMENT -- "NO DELETE GRANT ...
  // deactivation is active=false, never a row delete" -- because a `--` comment
  // carries no semicolon to stop the span. A checker that reads prose about
  // code as code is the single most-recorded defect class in this repo, and it
  // showed up inside the test written to police it.
  assert.ok(!/grant[^;]*delete/i.test(SQL_CODE),
    'nothing on this platform deletes a credential row');
  assert.ok(/NO DELETE GRANT/.test(SCHEMA),
    '...and the raw file still explains why, for whoever edits it next');
});
t('REVOKE ALL from service_role comes BEFORE the grant', () => {
  const rev = SCHEMA.indexOf('revoke all on public.sairnvet_employee_auth from service_role');
  const grant = SCHEMA.indexOf('grant select, insert, update');
  assert.ok(rev > 0 && grant > 0 && rev < grant,
    'without it the table inherits TRUNCATE, which wipes every credential at once');
});
t('anon and authenticated are revoked', () => {
  assert.ok(/revoke all on public\.sairnvet_employee_auth from anon, authenticated/.test(SCHEMA));
});
t('the column is `active`, never `is_active`', () => {
  assert.ok(/\bactive boolean not null default true/.test(SCHEMA));
  assert.ok(SCHEMA.indexOf('is_active') === -1);
});
t('the CHECK constraint matches ROLES_BY_APP exactly', () => {
  const m = SCHEMA.match(/role in \(([^)]*)\)/);
  assert.ok(m, 'the check constraint is present');
  const inSql = m[1].split(',').map((s) => s.trim().replace(/'/g, ''));
  assert.deepStrictEqual(inSql.sort(), ROLES_BY_APP.sairnvet.slice().sort(),
    'an unsynchronised pair lets signSessionToken mint a role the table refuses');
});
t('THE SCHEMA SEEDS NO CREDENTIAL ROW', () => {
  assert.ok(!/insert\s+into\s+public\.sairnvet_employee_auth/i.test(SCHEMA),
    'a PIN committed to the repo is a PIN in every clone history forever');
});
t('...and it says so, so nobody adds one', () => {
  assert.ok(SCHEMA.indexOf('WRITES NO CREDENTIAL ROWS') !== -1);
});
t('the verify block is one query per statement with its expected answer', () => {
  assert.ok((SCHEMA.match(/--\s+expect/g) || []).length >= 4,
    'a single count at the end cannot tell a full apply from a partial one');
});

// ── 9. THE TRAPDOOR DETECTOR KNOWS ABOUT THIS APP ───────────────────────────
section('9. provisioner-health registers the new app');
t('sairnvet is in the APPS map, reading the exported list not a literal', () => {
  const PH = fs.readFileSync(path.join(ROOT, 'api', 'provisioner-health.js'), 'utf8');
  assert.ok(/sairnvet:\s*\{\s*table:\s*sv\.EMPLOYEE_TABLE,\s*roles:\s*sv\.PROVISIONING_ROLES\s*\}/.test(PH),
    'a new auth endpoint absent from this map is one whose trapdoor nothing watches');
});

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsv-auth: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
