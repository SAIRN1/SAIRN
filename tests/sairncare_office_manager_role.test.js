// tests/sairncare_office_manager_role.test.js
//
// FAILING-FIRST. RED ON PURPOSE AND MUST STAY RED UNTIL THE api/ OWNER LANDS
// THE ROLE. Registered in docs/known-red-suites.json so a genuinely new
// regression can be told from this deliberate one, and wired into NO gate.
//
// ── THE DECISION THIS ENCODES (Michael, 2026-10-14) ────────────────────────
// "An office manager may grant billing access to a MAR." And the open question
// that b8 routed -- add the role, or declare `owner` to BE the office manager
// -- IS NOW ANSWERED: **ADD THE ROLE.** `owner`-as-office-manager is off the
// table, so this suite asserts the role itself exists.
//
// b8's tests/mar_billing_grant.test.js arm B2 is the arm this file discharges.
// That arm said the grantor role "is not in this app's role vocabulary, so no
// session can ever satisfy the grant gate", and left both resolutions open.
// This file picks the one Michael picked and pins it in all four places.
//
// ── WHY FOUR PLACES AND NOT ONE ────────────────────────────────────────────
// A role is not one declaration. It is a server vocabulary, an endpoint that
// decides what the role may DO, and TWO database CHECK constraints -- because
// `sairncare_employee_auth` is declared twice in sql/. Add the role to the
// server only and credential creation fails at the DATABASE with a 400 while
// the app believes the role exists; add it to one of the two SQL files only and
// whichever declaration a given deployment ran decides whether it works.
//
//   place 1  ROLES_BY_APP.sairncare          api/_lib/auth.js
//   place 2  the SAIRNcare auth endpoint     api/alf-auth.js
//   place 3  the role CHECK                  sql/sairncare_employee_auth_schema.sql
//   place 4  the role CHECK, again           sql/sairncare_all_remaining_migrations.sql
//
// ── WHAT THIS SUITE DELIBERATELY DOES NOT DO ───────────────────────────────
// It does NOT re-assert set-equality between ROLES_BY_APP and the SQL CHECKs.
// api/role-vocabulary-agreement.test.js (hank) already pins that in BOTH
// directions, for every app, across both of SAIRNcare's two declarations. So:
//
//   ** IF hank ADDS office_manager TO ROLES_BY_APP AND NOT TO BOTH CHECKS,
//      hank's OWN SUITE GOES RED BEFORE MINE DOES. **
//
// That is the safety net, it already exists, and duplicating it here would be
// a second copy of a property with one owner. Arm D1 asserts that net is still
// in place instead -- if that suite is ever deleted, D1 is what says the
// agreement is no longer pinned anywhere.
//
// ── EVERY SOURCE READ CARRIES A UNIQUENESS GUARD ───────────────────────────
// An anchor that matches twice cannot say which site it measured, and an anchor
// that matches zero times makes a "not found" arm pass for the wrong reason.
// Both are counted as UNPROVEN here, never as a pass and never as a failure --
// b8 paid for this twice in one file.
//
// Run:  node tests/sairncare_office_manager_role.test.js
// Exit: 0 all arms proved and passing · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const ROLE = 'office_manager';

// The six roles SAIRNcare has today, read once and asserted as a CONTROL so
// that "add office_manager" cannot be satisfied by replacing the vocabulary.
const EXISTING = ['owner', 'nursing', 'med_aide', 'caregiver', 'billing', 'activities'];

const AUTH_JS = path.join(ROOT, 'api/_lib/auth.js');
const ALF_JS = path.join(ROOT, 'api/alf-auth.js');
const SQL_A = path.join(ROOT, 'sql/sairncare_employee_auth_schema.sql');
const SQL_B = path.join(ROOT, 'sql/sairncare_all_remaining_migrations.sql');
const AGREEMENT = path.join(ROOT, 'api/role-vocabulary-agreement.test.js');

// ── THREE OUTCOMES, AND UNPROVEN IS COUNTED RATHER THAN PRINTED ────────────
// process.exit reads the unproven counter, so this suite cannot exit 0 while an
// arm was never evaluated. docs/2026-10-13-cody-b6-methodology-unproven.md §3.
let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 300));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 300));
}

function read(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch (e) { return null; }
}

// COMMENTS ARE STRIPPED BEFORE ANY SOURCE ASSERTION. Both api/ files DOCUMENT
// the role vocabulary in prose above the code -- and this very file's name will
// be in anyone's grep output -- so a naive match reports a change that is only
// a sentence. Matching the construct, not the word.
function codeOnly(js) {
  return js.split(/\r?\n/).filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
}
function sqlCodeOnly(sql) {
  return sql.split(/\r?\n/).filter((l) => !/^\s*--/.test(l)).join('\n');
}

// Returns {n, roles} for a `role text not null check (role in ('a','b'))`
// declaration: n is the MATCH COUNT so the caller can refuse a non-unique read.
const CHECK_RE = /role\s+text\s+not\s+null\s+check\s*\(\s*role\s+in\s*\(([^)]*)\)\s*\)/g;
function roleCheck(sql) {
  const body = sqlCodeOnly(sql);
  const hits = [];
  let m;
  CHECK_RE.lastIndex = 0;
  while ((m = CHECK_RE.exec(body)) !== null) hits.push(m[1]);
  if (hits.length !== 1) return { n: hits.length, roles: null };
  const roles = hits[0].split(',')
    .map((s) => s.trim().replace(/^'|'$/g, ''))
    .filter((s) => s.length);
  return { n: 1, roles: roles };
}

(function main() {
  console.log('SAIRNCARE office_manager ROLE -- criteria 2026-10-14.1 '
            + '(FAILING-FIRST)\n');

  // ── A. ROLES_BY_APP, THE SERVER VOCABULARY ──────────────────────────────
  console.log('A. place 1 -- ROLES_BY_APP.sairncare (api/_lib/auth.js)');

  // THE REAL OBJECT, NOT A REGEX OVER ITS SOURCE. Requiring the module is
  // strictly stronger: it survives reformatting, and it is what the handler
  // actually reads at runtime.
  let roles = null;
  try {
    roles = require(AUTH_JS).ROLES_BY_APP.sairncare;
  } catch (e) {
    cannot('A1. api/_lib/auth.js could not be required, so the server '
         + 'vocabulary was not read at all', e && e.message);
  }

  if (roles === null || roles === undefined) {
    if (roles === undefined) {
      cannot('A1. ROLES_BY_APP.sairncare is undefined -- the app key is gone, '
           + 'which is a different defect from a missing role', 'undefined');
    }
  } else if (!Array.isArray(roles)) {
    cannot('A1. ROLES_BY_APP.sairncare is not an array, so membership cannot '
         + 'be judged', typeof roles);
  } else if (roles.indexOf(ROLE) !== -1) {
    ok('A1. ROLES_BY_APP.sairncare includes ' + ROLE + ', so a session can '
     + 'actually hold the role the grant gate will require '
     + '(api/_lib/auth.js, the `sairncare: [` entry)');
  } else {
    bad('A1. ROLES_BY_APP.sairncare must include ' + ROLE,
        'it is ' + JSON.stringify(roles) + ' -- six roles, none of them an '
      + 'office manager. THIS IS THE OPEN ITEM, not a regression');
  }

  if (Array.isArray(roles)) {
    const lost = EXISTING.filter((r) => roles.indexOf(r) === -1);
    if (lost.length === 0) {
      ok('A2. CONTROL -- all six existing roles are still present. WITHOUT '
       + 'THIS ARM, "add ' + ROLE + '" could be satisfied by replacing the '
       + 'vocabulary and A1 would pass on a broken app');
    } else {
      bad('A2. CONTROL -- adding a role must not remove one',
          'missing: ' + JSON.stringify(lost));
    }
  } else {
    cannot('A2. the control cannot run while A1 could not read the vocabulary',
           'depends on A1');
  }

  // ── B. THE SAIRNcare AUTH ENDPOINT ──────────────────────────────────────
  console.log('\nB. place 2 -- the SAIRNcare auth endpoint (api/alf-auth.js)');

  const alf = read(ALF_JS);
  if (alf === null) {
    cannot('B1. api/alf-auth.js is not readable at ' + ALF_JS, 'ENOENT');
    cannot('B2. and neither arm below can be judged', 'depends on B1');
  } else {
    const alfCode = codeOnly(alf);

    // PLACE 2 IS SATISFIED BY PLACE 1 **ONLY WHILE THE DERIVATION HOLDS.**
    // ALF_ROLES is not a second literal list; it reads ROLES_BY_APP. So the
    // honest assertion for this file is that the derivation is intact -- if
    // somebody replaces it with a hardcoded array, place 1 stops reaching
    // place 2 and nothing else in this repo would say so.
    const DERIVE = 'const ALF_ROLES = ROLES_BY_APP[APP];';
    const derives = alfCode.split(DERIVE).length - 1;
    if (derives !== 1) {
      cannot('B1. the derivation anchor ' + JSON.stringify(DERIVE) + ' matched '
           + derives + ' time(s), not once, so this arm cannot say whether '
           + 'api/alf-auth.js still derives its roles from ROLES_BY_APP',
             'uniqueness guard');
    } else if (Array.isArray(roles) && roles.indexOf(ROLE) !== -1) {
      ok('B1. api/alf-auth.js still DERIVES ALF_ROLES from ROLES_BY_APP[APP], '
       + 'and ROLES_BY_APP now carries ' + ROLE + ' -- so place 2\'s '
       + 'vocabulary follows place 1 rather than being a second list that can '
       + 'drift');
    } else {
      bad('B1. the derivation is intact but ROLES_BY_APP does not carry '
        + ROLE + ' yet, so api/alf-auth.js does not know the role either',
          'blocked by A1 -- the derivation itself is FINE');
    }

    // ** THE DECISION ARM. ** A role in the vocabulary that appears in no
    // capability set can sign in and do nothing: it is a vocabulary entry with
    // no authority. An office manager who "may grant billing access to a MAR"
    // must therefore be named somewhere in this endpoint's own decisions.
    // TWO LEGITIMATE RESOLUTIONS AND THIS ARM ACCEPTS EITHER -- asserting one
    // would dictate the implementation:
    //   (a) add it to PROVISIONING_ROLES, so an office manager may create
    //       credentials (today that list is ['owner'], and the file says it is
    //       owner-only as a CHECKED fact rather than an assumption);
    //   (b) declare a new named constant for the grantor capability.
    // What is NOT acceptable is silence: a role nobody wrote a rule for.
    if (new RegExp('[\'"]' + ROLE + '[\'"]').test(alfCode)) {
      ok('B2. api/alf-auth.js names ' + ROLE + ' in CODE (comments stripped), '
       + 'so the endpoint makes an explicit decision about what an office '
       + 'manager may do rather than leaving the role capability-less');
    } else {
      bad('B2. api/alf-auth.js must name ' + ROLE + ' in a code line -- in '
        + 'PROVISIONING_ROLES or in a new grantor constant, EITHER IS '
        + 'ACCEPTED HERE',
          'absent from api/alf-auth.js. PROVISIONING_ROLES is [\'owner\'] and '
        + 'MANAGEMENT_ROLES is { owner, billing } -- an office manager is in '
        + 'neither, so the role would exist with no authority at all');
    }
  }

  // ── C. THE TWO DATABASE CHECK CONSTRAINTS ───────────────────────────────
  console.log('\nC. places 3 and 4 -- the role CHECK, declared TWICE in sql/');

  const sqls = [
    ['C1', SQL_A, 'sql/sairncare_employee_auth_schema.sql'],
    ['C2', SQL_B, 'sql/sairncare_all_remaining_migrations.sql'],
  ];
  const parsed = [];
  sqls.forEach(function (row) {
    const id = row[0], p = row[1], label = row[2];
    const sql = read(p);
    if (sql === null) {
      cannot(id + '. ' + label + ' is not readable', 'ENOENT');
      parsed.push(null);
      return;
    }
    const rc = roleCheck(sql);
    if (rc.n !== 1) {
      cannot(id + '. the role CHECK in ' + label + ' matched ' + rc.n
           + ' time(s), not once, so this arm cannot say which constraint it '
           + 'measured', 'uniqueness guard');
      parsed.push(null);
      return;
    }
    parsed.push(rc.roles);
    if (rc.roles.indexOf(ROLE) !== -1) {
      ok(id + '. ' + label + ' permits ' + ROLE + ', so credential creation '
       + 'for the role is accepted by the database');
    } else {
      bad(id + '. ' + label + ' must permit ' + ROLE,
          'CHECK permits ' + JSON.stringify(rc.roles) + '. A role the server '
        + 'mints and the CHECK rejects is a 400 at insert time with the app '
        + 'believing the role exists');
    }
  });

  // CONTROL, AND IT IS WHAT MAKES C1 AND C2 EVIDENCE. If the regex had missed
  // the construct, C1 and C2 would both report "absent" for a role that is
  // right there. Proving both CHECKs parsed to a real, non-empty list is what
  // distinguishes "not permitted" from "not measured".
  if (parsed.length === 2 && parsed[0] && parsed[1]) {
    if (parsed[0].length >= 2 && parsed[1].length >= 2) {
      ok('C3. CONTROL -- both CHECKs parsed to real non-empty role lists ('
       + parsed[0].length + ' and ' + parsed[1].length + ' values), so C1 and '
       + 'C2 above are measuring a constraint rather than a failed match');
    } else {
      bad('C3. CONTROL -- a CHECK that parsed to fewer than two roles is a '
        + 'parse failure wearing the costume of a narrow constraint',
          JSON.stringify(parsed));
    }
  } else {
    cannot('C3. the control cannot run while a CHECK could not be parsed',
           'depends on C1 and C2');
  }

  // ── D. THE SAFETY NET THAT ALREADY EXISTS ───────────────────────────────
  console.log('\nD. the agreement property, owned elsewhere');

  const agree = read(AGREEMENT);
  if (agree === null) {
    bad('D1. api/role-vocabulary-agreement.test.js is GONE. The both-direction '
      + 'set-equality between ROLES_BY_APP and every sql/ role CHECK is now '
      + 'pinned NOWHERE, and this suite deliberately does not duplicate it',
        'ENOENT at ' + AGREEMENT);
  } else if (/ROLES_BY_APP/.test(agree) && /check\s*\(\s*role\s+in/i.test(agree)) {
    ok('D1. api/role-vocabulary-agreement.test.js is present and still reads '
     + 'BOTH ROLES_BY_APP and the sql/ role CHECKs -- so adding ' + ROLE
     + ' to the server and not to both CHECKs turns THAT suite red before '
     + 'this one, which is the correct owner for that property');
  } else {
    bad('D1. api/role-vocabulary-agreement.test.js exists but no longer reads '
      + 'both sides, so the agreement is not actually pinned there any more',
        'ROLES_BY_APP present: ' + /ROLES_BY_APP/.test(agree));
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  console.log('\nEXPECTED RED until the api/ owner lands the role in all four '
            + 'places. Registered in docs/known-red-suites.json; no gate '
            + 'reads this. CODE CHANGE ROUTED TO hank.');
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})();
