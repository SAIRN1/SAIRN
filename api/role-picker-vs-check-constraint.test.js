// api/role-picker-vs-check-constraint.test.js
//
// Run:  node api/role-picker-vs-check-constraint.test.js
//
// REQUIREMENT: no app offers a role in a UI picker that its own database CHECK
//   constraint will refuse.
//
// ── THE DEFECT CLASS, AND IT HAS A NAME ON THIS PLATFORM ───────────────────
// b11 added `office_manager` to SAIRNcare: to ROLES_BY_APP, to the server's
// provisioning set, to the role CHECK in sql/, and to three places in
// sairncare.html. The server mints the role the moment Vercel deploys. The
// Postgres CHECK only widens when somebody RUNS the migration -- so between
// the deploy and the run, the owner's provisioning picker offers a role the
// database refuses with 23514, and the save fails at the last step with no
// validation message. b11's own handoff carries that as an open item and the
// HTML carries a comment saying so.
//
// THAT IS THE SHAPE THIS CHECK EXISTS FOR, and it is not specific to one role:
// a picker and a CHECK constraint are two lists in two languages in two files
// that must agree, which is the defect shape this repo records paying for
// repeatedly. Nothing compared them until now.
//
// ── WHAT IT COMPARES, AND THE LIMIT IT CANNOT CLOSE ────────────────────────
// It reads the CHECK out of `sql/`, which is THE REPO'S INTENDED constraint and
// NOT the live database's. A role that is in the repo's CHECK and not yet
// migrated is INVISIBLE here -- which is exactly the office_manager state
// today. So this check catches the DRIFT (a picker ahead of the schema file)
// and cannot catch the LAG (a schema file ahead of production). The lag needs a
// live query and is named in the output every run rather than left to be
// discovered. Arm C is what reports it.
//
// ── FAILS CLOSED IN BOTH DIRECTIONS ────────────────────────────────────────
// An app whose picker cannot be found, or whose CHECK cannot be parsed, is
// UNPROVEN -- never a pass. A comparison with one side missing reports a clean
// sweep over a file it never read, which is the single most common defect shape
// on this platform after a silent failure.
//
// Exit: 0 all apps proved clean · 1 a picker offers a refused role · 3 an app
//       could not be measured
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const { ROLES_BY_APP } = require('./_lib/auth');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split(':')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 500));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split(':')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 500));
}

// ── THE APP LIST IS DERIVED, NOT TYPED ─────────────────────────────────────
// ROLES_BY_APP is the platform's own record of which apps have a role
// vocabulary at all, so an app added there is covered the day it is added
// rather than the day somebody re-reads this file. An app with no HTML or no
// schema is reported, not skipped.
const APPS = Object.keys(ROLES_BY_APP || {}).sort();

// Every `<select>` in the file, with its id and its option values.
function selects(html) {
  const out = [];
  const re = /<select\b([^>]*)>([\s\S]*?)<\/select>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const attrs = m[1] || '';
    const idM = /id\s*=\s*"([^"]+)"/.exec(attrs);
    const vals = [];
    const ore = /<option\b[^>]*value\s*=\s*"([^"]*)"/g;
    let o;
    while ((o = ore.exec(m[2])) !== null) { vals.push(o[1]); }
    out.push({ id: idM ? idM[1] : null, values: vals });
  }
  return out;
}

// The role CHECK, parsed out of whatever schema file declares it. More than one
// file can declare the same table (a schema file and an all-migrations file),
// so EVERY declaration is read and the UNION is what the database could end up
// holding -- taking the first would report a narrower constraint than exists.
// ── THE SCOPE IS THE STATEMENT, NOT THE FILE, AND THE FIRST DRAFT GOT THIS
//    WRONG IN THE PERMISSIVE DIRECTION ──────────────────────────────────────
// That draft took any sql/ file MENTIONING `<app>_employee_auth` and then
// collected EVERY `check (role in (...))` in it. Run over the real repo, it
// reported sairncare as having 18 allowed roles drawn from
// sairnroofing_employee_auth_schema.sql among others, and sairnlaw as 15 drawn
// from four other apps -- because a file that mentions one table in a COMMENT
// declares others in code. A union across apps makes `allowed` a superset and
// the whole check PERMISSIVE: it would report clean on a genuinely refused
// role, which is the one direction a detector must never fail in.
//
// Caught by READING the output rather than the exit code: the run was already
// "0 with a refused role" and the role lists beside it were wrong.
//
// Now each declaration is bounded to the statement that names this app's
// table: `create table ... <app>_employee_auth ( ... )` to the matching
// paren, or `alter table ... <app>_employee_auth ... check (role in (...))`
// up to the statement's semicolon.
function roleChecks(app) {
  const dir = path.join(ROOT, 'sql');
  let files;
  try { files = fs.readdirSync(dir); } catch (e) { return null; }
  const tbl = app + '_employee_auth';
  const hits = [];
  function rolesIn(text) {
    const m = /check\s*\(\s*role\s+in\s*\(([^)]*)\)/i.exec(text);
    if (!m) return null;
    const vals = (m[1].match(/'([^']*)'/g) || []).map((s) => s.slice(1, -1));
    return vals.length ? vals : null;
  }
  files.filter((f) => /\.sql$/.test(f)).forEach(function (f) {
    let src;
    try { src = fs.readFileSync(path.join(dir, f), 'utf8'); } catch (e) { return; }
    // CREATE TABLE: bounded by the paren that opens the column list.
    const cre = new RegExp('create\\s+table[^;]*?\\b' + tbl + '\\s*\\(', 'gi');
    let c;
    while ((c = cre.exec(src)) !== null) {
      const open = src.lastIndexOf('(', cre.lastIndex);
      let d = 0, k = open;
      for (; k < src.length; k++) {
        if (src[k] === '(') d++;
        else if (src[k] === ')') { d--; if (d === 0) break; }
      }
      const roles = rolesIn(src.slice(open, k + 1));
      if (roles) hits.push({ file: f, roles: roles, form: 'create' });
    }
    // ALTER TABLE ... ADD CONSTRAINT: bounded by the statement's semicolon.
    const alt = new RegExp('alter\\s+table[^;]*?\\b' + tbl + '\\b[^;]*;', 'gi');
    let a;
    while ((a = alt.exec(src)) !== null) {
      const roles = rolesIn(a[0]);
      if (roles) hits.push({ file: f, roles: roles, form: 'alter' });
    }
  });
  return hits;
}

console.log('ROLE PICKER vs DATABASE CHECK CONSTRAINT -- criteria 2026-10-14.1');
console.log(APPS.length + ' app(s) from ROLES_BY_APP, derived not typed\n');

const liveLag = [];

APPS.forEach(function (app) {
  const vocab = ROLES_BY_APP[app] || [];
  const htmlPath = path.join(ROOT, app + '.html');
  let html = null;
  try { html = fs.readFileSync(htmlPath, 'utf8'); } catch (e) { html = null; }
  const checks = roleChecks(app);

  if (html === null) {
    cannot(app + ': no ' + app + '.html in the repo, so its pickers could not '
         + 'be read. NOT a pass -- an app with a role vocabulary and no file '
         + 'here is a question, and the file may simply be named differently',
           htmlPath);
    return;
  }
  if (checks === null || checks.length === 0) {
    cannot(app + ': no `check (role in (...))` found in any sql/ file naming '
         + app + '_employee_auth, so there is nothing to compare the picker '
         + 'against. NOT a pass: an app whose constraint cannot be found is '
         + 'exactly the app whose picker nobody has checked',
           'searched sql/*.sql for ' + app + '_employee_auth');
    return;
  }

  // THE UNION ACROSS DECLARATIONS. Two files declaring the same table is
  // normal here (a schema file plus an all-remaining-migrations file) and
  // taking the narrower one would invent a finding.
  const allowed = {};
  checks.forEach(function (c) { c.roles.forEach(function (r) { allowed[r] = true; }); });

  // ── WHICH SELECTS ARE ROLE PICKERS, DECIDED BY CONTENT ────────────────────
  // NOT by the id. sairncare's two are `st-position` and `sec-new-role`;
  // sairnvet's are different again, and an id-based rule would silently miss
  // one and report the app clean. A select is a role picker when TWO OR MORE of
  // its option values are in this app's own role vocabulary -- two, not one,
  // because a single coincidence ('owner' in a filter dropdown) is not a
  // picker.
  const pickers = selects(html).filter(function (s) {
    const inVocab = s.values.filter(function (v) { return vocab.indexOf(v) !== -1; });
    return inVocab.length >= 2;
  });
  if (pickers.length === 0) {
    cannot(app + ': no role picker found in ' + app + '.html -- no <select> '
         + 'has two or more option values from this app\'s own vocabulary. '
         + 'Either the app provisions roles somewhere this detector cannot see, '
         + 'or the detector has stopped matching. Either way nothing was '
         + 'compared',
           'vocabulary: [' + vocab.join(', ') + ']');
    return;
  }

  const offenders = [];
  pickers.forEach(function (p) {
    p.values.forEach(function (v) {
      // Only values that are REAL ROLES for this app. A picker legitimately
      // carries '' for "none selected" and may carry non-role options.
      if (vocab.indexOf(v) === -1) return;
      if (!allowed[v]) {
        offenders.push((p.id || '<no id>') + ' offers "' + v + '"');
      }
    });
  });

  if (offenders.length) {
    bad(app + ': a picker offers a role the database CHECK refuses -- the save '
      + 'will fail 23514 at the last step with no validation message. '
      + offenders.length + ' case(s)',
        offenders.join('; ') + '  |  CHECK allows [' + Object.keys(allowed).join(', ')
      + '] from ' + checks.map((c) => c.file).join(', '));
  } else {
    ok(app + ': all ' + pickers.length + ' role picker(s) offer only roles the '
     + 'CHECK in ' + checks.map((c) => c.file).join(', ') + ' accepts ('
     + Object.keys(allowed).length + ' allowed)');
  }

  // ── THE LAG THIS CHECK CANNOT SEE, COLLECTED AND REPORTED ────────────────
  // A role in the repo's CHECK that is NOT in a picker is usually fine. A role
  // in the CHECK that arrived by an ALTER in a dated migration file is the
  // interesting one: the repo intends it, and whether production has it is a
  // question only a live query answers.
  checks.forEach(function (c) {
    if (/^\d{4}-\d{2}-\d{2}/.test(c.file)) {
      liveLag.push(app + ': ' + c.file + ' widens the CHECK by ALTER, so the '
        + 'repo allows [' + c.roles.join(', ') + '] and PRODUCTION allows that '
        + 'only if the file has been run');
    }
  });
});

console.log('\n── THE LIMIT, REPORTED EVERY RUN RATHER THAN DISCOVERED ──');
console.log('This compares a picker against the CHECK IN sql/, which is the');
console.log('repo\'s INTENDED constraint and not the live database\'s. A role');
console.log('that is in the schema file and NOT YET MIGRATED is invisible here');
console.log('-- that is the office_manager state as this is written. So:');
console.log('  CAUGHT    a picker ahead of the schema file (drift)');
console.log('  NOT CAUGHT a schema file ahead of production (lag)');
if (liveLag.length) {
  console.log('\n' + liveLag.length + ' CHECK-widening migration(s) found. Each '
            + 'is a lag this check cannot measure:');
  liveLag.forEach(function (l) { console.log('  * ' + l); });
  console.log('  The live question is one query per app:');
  console.log('    select pg_get_constraintdef(oid) from pg_constraint');
  console.log('     where conname = \'<app>_employee_auth_role_check\';');
} else {
  console.log('\nNo dated CHECK-widening migration found in sql/, so there is');
  console.log('no known lag to report. That is measured, not assumed.');
}

console.log('\n' + pass + ' app(s) clean, ' + fail + ' with a refused role, '
          + unproven + ' could not be measured');
if (failed.length) console.log(failed.length + ' APP(S) FAILED: ' + failed.join(', '));
if (notProved.length) console.log(notProved.length + ' APP(S) UNPROVEN: ' + notProved.join(', '));
process.exit(fail ? 1 : (unproven ? 3 : 0));
