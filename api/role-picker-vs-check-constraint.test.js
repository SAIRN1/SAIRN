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

const { ROLES_BY_APP, AUTH_TABLE_BY_APP } = require('./_lib/auth');

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

// ── ROLE LISTS DECLARED IN JAVASCRIPT, NOT IN MARKUP (2026-10-15) ───────────
// The second method. Returns the same {id, values} shape as selects() so the
// comparison below is one loop and cannot drift between the two.
//
// AN ARRAY LITERAL QUALIFIES ONLY WHEN EVERY QUOTED TOKEN IN IT IS A ROLE for
// this app, and there are at least two. `['Pending','Completed']` fails on the
// first member; `['owner','crew_lead','office']` passes. That is deliberately
// the strict direction: a false POSITIVE here would compare a list of
// non-roles against a role CHECK and manufacture a finding, which is the
// failure mode this whole check exists to avoid committing itself.
//
// NESTED BRACKETS ARE SKIPPED rather than guessed at. An array of objects
// (`[{id:'owner',...},{id:'hr',...}]`) still matches, because the scan is over
// QUOTED TOKENS inside the literal and not over its structure -- the keys are
// unquoted identifiers in this codebase's style, so `id:` does not pollute the
// token set. A literal containing another array is not parsed and is reported
// as skipped rather than silently dropped.
function roleArrays(html, vocab) {
  const out = [];
  if (!vocab || !vocab.length) return out;
  // Candidate literals: a `[` ... `]` with no nested bracket, short enough to
  // be a declaration rather than a data blob.
  const re = /\[([^[\]]{4,2000})\]/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const body = m[1];
    const toks = (body.match(/'([^'\n]*)'|"([^"\n]*)"/g) || [])
      .map((s) => s.slice(1, -1))
      .filter((s) => s !== '');
    if (toks.length < 2) continue;
    const uniq = toks.filter((t, i) => toks.indexOf(t) === i);
    const inVocab = uniq.filter((t) => vocab.indexOf(t) !== -1);
    if (inVocab.length < 2) continue;
    if (inVocab.length !== uniq.length) continue;   // ALL, not some
    const line = html.slice(0, m.index).split('\n').length;
    out.push({ id: 'array literal at line ' + line, values: uniq });
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
//
// ── THE TABLE NAME IS READ OFF THE PLATFORM'S OWN MAP (2026-10-15) ────────
// THIS IS WHY FOUR OF b12's ELEVEN UNPROVEN APPS WERE UNPROVEN, and it was a
// defect in this check rather than a fact about those apps. It constructed
// `app + '_employee_auth'`, and api/_lib/auth.js:1094 says in its own words
// that there is no such rule: "`sd`, `sb`, `grd` and `scp` use a prefix, the
// rest use the full app name... A derivation would be wrong for at least five
// of them and wrong SILENTLY". stonedesk's table is `sd_employee_auth`,
// sairnbiz's is `sb_employee_auth`, sairngrounds' is `grd_employee_auth` and
// sairnscape's is `scp_employee_auth` -- so this searched sql/ for four names
// that do not exist, found nothing, and reported four apps as unmeasurable.
//
// AUTH_TABLE_BY_APP is exported and is the same map the live session gate uses
// to decide which table to read, so there is now one source for the name
// rather than a second rule that can disagree with it. An app with NO entry is
// a different answer again and is handled at the call site.
function authTable(app) {
  const t = AUTH_TABLE_BY_APP && AUTH_TABLE_BY_APP[app];
  return (typeof t === 'string' && t) ? t : null;
}
function roleChecks(app) {
  const dir = path.join(ROOT, 'sql');
  let files;
  try { files = fs.readdirSync(dir); } catch (e) { return null; }
  const tbl = authTable(app);
  if (tbl === null) return 'NO_TABLE';
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

  // ── AN APP WITH NO EMPLOYEE-AUTH TABLE IS NOT-APPLICABLE, NOT UNPROVEN ──
  // `stonedesk_sub` is DELIBERATELY absent from AUTH_TABLE_BY_APP and that
  // file says why: subcontractors authenticate against `sd_sub_auth` keyed on
  // `sub_id`, not `employee_id`, and their removal path is a different one. So
  // there is no `<app>_employee_auth` role CHECK to compare a picker against,
  // and reporting "could not measure" implied a measurement was owed. A
  // question with a recorded answer is not an open question.
  if (checks === 'NO_TABLE') {
    ok(app + ': NOT APPLICABLE -- no entry in AUTH_TABLE_BY_APP, so this app '
     + 'has no `<app>_employee_auth` table and no role CHECK of this shape to '
     + 'compare against. api/_lib/auth.js records the reason (stonedesk_sub '
     + 'authenticates against sd_sub_auth keyed on sub_id). If an app that '
     + 'SHOULD have employee credentials appears here, the missing map entry '
     + 'is itself the finding -- the live session gate reads the same map and '
     + 'answers NO_ACTIVE_CHECK without one');
    return;
  }
  if (html === null) {
    cannot(app + ': no ' + app + '.html in the repo, so its pickers could not '
         + 'be read. NOT a pass -- an app with a role vocabulary and no file '
         + 'here is a question, and the file may simply be named differently',
           htmlPath);
    return;
  }
  if (checks === null || checks.length === 0) {
    cannot(app + ': no `check (role in (...))` found in any sql/ file naming '
         + authTable(app) + ', so there is nothing to compare the picker '
         + 'against. NOT a pass: an app whose constraint cannot be found is '
         + 'exactly the app whose picker nobody has checked',
           'searched sql/*.sql for ' + authTable(app));
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
  // ── A SECOND, STRUCTURALLY DIFFERENT METHOD (2026-10-15) ────────────────
  // NINE OF b12's ELEVEN UNPROVEN APPS WERE UNPROVEN BECAUSE OF THIS GAP, and
  // it is this check's limitation rather than a fact about those apps. The
  // scan above reads STATIC <option> markup. sairnfreedom's picker is
  // `<select id="ac-cap"></select>` -- empty in the HTML -- and
  // sfRenderAccess() fills it at runtime from the CAPABILITIES array
  // (sairnfreedom.html:2680). An option whose value is `' + c.id + '` leaves
  // no literal token for an option scanner to find, so the app looked as
  // though it had no picker at all.
  //
  // THE SECOND METHOD IS NOT A WIDER REGEX OVER THE SAME TEXT, which is what
  // cross-domain convention 6 refuses: it reads ARRAY LITERALS instead of
  // markup. Any array literal in the page carrying two or more quoted tokens
  // that are ALL in this app's own role vocabulary is a declared role list.
  //
  // "ALL, NOT SOME", and that is what stops the rule matching anything. An
  // array of status strings, column names or menu labels fails it the moment
  // one member is not a role. The cost runs the other way -- an array MIXING
  // roles with non-roles is missed -- which is stated here rather than
  // discovered later, and is why the static scan is kept rather than replaced.
  //
  // THE LINE NUMBER IS REPORTED so a reader can check what was matched. A
  // detector that says "found a role list" without saying where is one nobody
  // can audit.
  const runtimeLists = roleArrays(html, vocab);
  const allPickers = pickers.concat(runtimeLists);
  if (allPickers.length === 0) {
    // ── A PAGE WITH NO PROVISIONING ACTION IS A MEASURED ANSWER (2026-10-15)
    // Four apps reached here after both detectors, and the reason turned out
    // to be the same for all four and is not a detector gap: THEY DO NOT
    // ASSIGN ROLES FROM THEIR OWN PAGE. sairnmechanical says so in its own UI
    // text -- "PINs are no longer set here ... An Owner provisions them
    // through api/mech-auth.js (setup)" -- and sairncode's access panel reads
    // the roster and toggles `active` with no role control at all. A page that
    // cannot send a role cannot offer one the CHECK refuses, so "could not
    // measure" overstated what was owed.
    //
    // THE TEST IS THE ACTION NAME, because that is the one thing every one of
    // these transports has in common: `setup` is the verb that mints a
    // credential with a role across all fifteen auth endpoints. No quoted
    // 'setup' anywhere in the page means no call site can reach it.
    //
    // AND THE LIMIT IS NAMED RATHER THAN LEFT IMPLIED: this says nothing about
    // what a DIRECT API caller sends. api/*-auth.js validates the role against
    // its own SEN_ROLES-style list and the database CHECK refuses the rest,
    // which is a different control from a picker and is not what this check
    // measures.
    if (!/['"]setup['"]/.test(html)) {
      ok(app + ': NOT APPLICABLE -- this page has no quoted `setup` action '
       + 'anywhere, so it never assigns a role and cannot offer one the CHECK '
       + 'refuses. Credentials for this app are provisioned through its '
       + 'api/*-auth.js endpoint directly. What a DIRECT caller sends is NOT '
       + 'measured here: that is the endpoint\'s own role validation plus the '
       + 'database CHECK. Re-derive with: '
       + 'grep -c "\'setup\'" ' + app + '.html');
      return;
    }
    cannot(app + ': a provisioning `setup` call EXISTS in ' + app + '.html but '
         + 'no role picker was found -- no <select> has two or more static '
         + 'option values from this app\'s own vocabulary, AND no array '
         + 'literal carries two or more of them either. Two structurally '
         + 'different methods found nothing beside a call that does send a '
         + 'role, so one of them has stopped matching. SETTLE IT BY HAND: '
         + 'grep -n "setup" ' + app + '.html, then read what the `role:` on '
         + 'that call is bound to',
           'vocabulary: [' + vocab.join(', ') + ']');
    return;
  }

  const offenders = [];
  allPickers.forEach(function (p) {
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
    // ── WHICH METHOD FOUND IT IS PART OF THE ANSWER (2026-10-15) ──────────
    // A static <option> picker is the strong case: that markup IS a
    // provisioning control. An ARRAY LITERAL is a weaker claim -- it is a
    // declared role list in the page, which may be a runtime-filled picker
    // (sairnfreedom's CAPABILITIES) or may be a vocabulary constant used for
    // display or filtering. Either way every token in it is accepted by the
    // CHECK, which is worth knowing; but reporting the two identically would
    // let "a constant carries no refused role" read as "the picker was
    // checked", and those are not the same sentence.
    ok(app + ': all ' + allPickers.length + ' role list(s) offer only roles the '
     + 'CHECK in ' + checks.map((c) => c.file).join(', ') + ' accepts ('
     + Object.keys(allowed).length + ' allowed) -- '
     + pickers.length + ' static <select> picker(s), '
     + runtimeLists.length + ' array literal(s)'
     + (pickers.length === 0
        ? '. ARRAY-ONLY: no static picker was found, so what is proven is that '
          + 'no DECLARED role list in this page carries a refused role, which '
          + 'is broader and weaker than "the provisioning picker was checked"'
        : ''));
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
// ── AND A SECOND LIMIT, FOUND BY SABOTAGING THIS CHECK (2026-10-15) ────────
// The comparison skips any option value NOT in ROLES_BY_APP, because a picker
// legitimately carries '' and non-role options. So a MISSPELT role --
// 'med_aide_II' planted into SAIRNsenior's picker -- was offered, would be
// refused 23514 by the database, and this check stayed green. Measured, not
// reasoned about: that was the first sabotage run and it was MISSED. The
// second sabotage, narrowing a CHECK while the picker still offered the role,
// is caught by both methods (exit 1, two apps named), which is the shape the
// check is actually for. Printed every run rather than left in a log.
console.log('  NOT CAUGHT a picker value that is in NEITHER the app\'s');
console.log('             ROLES_BY_APP vocabulary NOR the CHECK -- a');
console.log('             MISSPELT role is invisible here. Closing it means');
console.log('             deciding which non-role option values are legitimate');
console.log('             per app, which is a vocabulary nobody has written.');
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
