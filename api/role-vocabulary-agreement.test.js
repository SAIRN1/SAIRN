// api/role-vocabulary-agreement.test.js
//
// REQUIREMENT: for EVERY app with an employee_auth table, the role list the
//   server accepts (ROLES_BY_APP in api/_lib/auth.js) and the role list the
//   DATABASE accepts (the `role ... check (role in (...))` constraint in that
//   app's sql/ schema file) are the SAME SET.
//
// Run:  node api/role-vocabulary-agreement.test.js
//
// ── THE DEFECT THIS EXISTS BECAUSE OF, AND IT IS NOT HYPOTHETICAL ─────────
// `trustee.audit` was added to sairnfreedom.html's CAPABILITIES on 2026-09-27
// and reached NEITHER of the other two copies. For sixteen days a VFW post
// could assign the Trustee office in its Access panel and then could not give
// that trustee a sign-in, because api/sf-auth.js refuses to provision a role it
// does not know.
//
// Three separate files already WARNED about that drift in prose --
// api/_lib/auth.js ("THE LIST NOW LIVES IN THREE PLACES and that is a real
// drift risk, named here rather than left to be discovered"),
// sql/sairnfreedom_employee_auth_schema.sql ("three copies of one list, which
// is a real drift risk and is named here"), and the schema's own header. All
// three warnings were accurate, all three were read by people, and the drift
// happened anyway. THIS FILE IS THE DIFFERENCE BETWEEN NAMING A RISK AND
// CHECKING IT.
//
// ── WHY IT COVERS EVERY APP AND NOT THE ONE THAT BROKE ───────────────────
// Sixteen apps carry an employee_auth table and every one of them has the same
// two-copy structure. A check scoped to SAIRNfreedom would pass forever on the
// other fifteen while they drifted, which is the shape this platform keeps
// paying for: a control written at the site of one incident, looking like
// coverage.
//
// ── THE TWO FAILURE DIRECTIONS ARE DIFFERENT BUGS AND BOTH ARE CHECKED ───
//   A ROLE IN ROLES_BY_APP THAT THE CHECK REJECTS -- the server provisions
//     happily and the INSERT fails. That is a 400 carrying a Postgres check
//     violation, raised at the one moment somebody is trying to give a
//     colleague a sign-in. Nobody can read it and nobody can work around it.
//   A ROLE IN THE CHECK THAT ROLES_BY_APP DOES NOT HAVE -- the database would
//     accept it and the server refuses to mint it. Less sharp, and still a
//     capability the app appears to offer and cannot deliver, which is exactly
//     what the trustee gap was.
//
// ── WHAT THIS DOES NOT COVER, SAID PLAINLY ───────────────────────────────
// THE THIRD COPY. Each app's HTML also carries its own capability or role list,
// and comparing those is a per-app parse with a different shape in each file --
// `CAPABILITIES` with `id:` keys in sairnfreedom.html, plain arrays elsewhere.
// api/sf-auth.test.js does it for SAIRNfreedom. Generalising it is real work
// and is NOT done here, so this file closes two of the three edges and says so
// rather than implying three.
//
// AND IT READS THE sql/ FILE, NOT THE DATABASE. A constraint widened live and
// never written back into sql/ is invisible here -- that exact state existed on
// three audit-log tables until 2026-10-13. `tools/audit_event_type_check.py`
// carries the same limit for the same reason: a clone has no database handle.
// What this catches is the two IN-REPO copies disagreeing.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { ROLES_BY_APP, AUTH_TABLE_BY_APP } = require('./_lib/auth');

const SQL_DIR = path.join(__dirname, '..', 'sql');

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); passed++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); failed++; }
}

// ── COMMENT-STRIPPED, LENGTH-PRESERVING ────────────────────────────────────
// A prose mention of a role name inside a comment is not a permitted value, and
// this platform has three recorded instances of a checker whose universe
// included the text DESCRIBING its subject -- most recently
// tools/audit_event_type_check.py exiting 2 COULD NOT RUN because a comment
// mentioned a helper by name. Line-based so any offset stays true.
function stripSqlComments(src) {
  const NL = String.fromCharCode(10);
  return src.split(NL).map(function (l) {
    const i = l.indexOf('--');
    return i === -1 ? l : l.slice(0, i);
  }).join(NL);
}

// Every `*employee_auth` table declared in sql/, with the role list each
// declaration's CHECK permits.
//
// RETURNS A LIST PER TABLE, NOT ONE DECLARATION, and that is not defensive
// generality -- it is a measured fact about this repo. `sairncare_employee_auth`
// is declared TWICE: in sql/sairncare_employee_auth_schema.sql and again in
// sql/sairncare_all_remaining_migrations.sql, a bundle that re-declares it. A
// first draft of this suite kept one declaration per table and flagged the
// duplicate as an error; that was the wrong instrument. Banning a duplicate
// DDL is a repo-layout opinion nobody asked for, whereas two declarations of
// one table whose CHECKs DISAGREE is a real defect -- and picking one silently
// is how you fail to notice either.
//
// NEVER A SILENT MISS: a declaration whose CHECK cannot be parsed is recorded
// with roles === null, so the arms below refuse it rather than skip it.
function sqlRoleChecks() {
  const out = Object.create(null);
  fs.readdirSync(SQL_DIR).filter(function (f) { return /\.sql$/.test(f); })
    .sort().forEach(function (f) {
      const code = stripSqlComments(fs.readFileSync(path.join(SQL_DIR, f), 'utf8'));
      const ddl = /create table if not exists\s+(?:public\.)?(\w*employee_auth)\b/gi;
      let m;
      while ((m = ddl.exec(code)) !== null) {
        const table = m[1];
        const tail = code.slice(m.index, m.index + 8000);
        const chk = /role\s+text[^,]*check\s*\(\s*role\s+in\s*\(([^)]*)\)/i.exec(tail);
        const roles = chk
          ? Array.from(new Set((chk[1].match(/'([a-z0-9_.]+)'/g) || [])
              .map(function (s) { return s.replace(/'/g, ''); }))).sort()
          : null;
        (out[table] = out[table] || []).push({ file: f, roles: roles });
      }
    });
  return out;
}

// -- ONE COMPARISON, TWO CALLERS ---------------------------------------------
// The load-bearing arm and its negative control MUST drive the same code. A
// control over a second copy of the logic only proves the copy fires, which is
// what cross-domain convention 6 is about: independence has to come from the
// INPUT being different, not from a reimplementation being different.
//
// EVERY DECLARATION IS COMPARED, not the first one found. A table declared in
// two files gets both of its CHECKs checked against ROLES_BY_APP, so a stale
// copy in a migration bundle cannot hide behind a current one.
function divergences(apps, rolesByApp, checks) {
  const diverged = [];
  apps.forEach(function (app) {
    (checks[AUTH_TABLE_BY_APP[app]] || []).forEach(function (d) {
      if (!d.roles) return;          // refused by the parseability arm, not here
      const code = Array.from(new Set(rolesByApp[app])).sort();
      const sql = d.roles;
      const serverOnly = code.filter(function (r) { return sql.indexOf(r) === -1; });
      const dbOnly = sql.filter(function (r) { return code.indexOf(r) === -1; });
      if (serverOnly.length || dbOnly.length) {
        diverged.push(app + ' (' + d.file + '): the server accepts '
          + (serverOnly.length ? JSON.stringify(serverOnly) + ' which the CHECK '
             + 'REJECTS -- provisioning one is a 400 carrying a Postgres check '
             + 'violation' : 'nothing the CHECK rejects')
          + '; the CHECK permits '
          + (dbOnly.length ? JSON.stringify(dbOnly) + ' which the server will '
             + 'not mint' : 'nothing the server cannot mint'));
      }
    });
  });
  return diverged;
}

function main() {
  console.log('ROLE VOCABULARY AGREEMENT -- ROLES_BY_APP vs every sql/ role CHECK\n');

  const checks = sqlRoleChecks();
  const apps = Object.keys(ROLES_BY_APP).sort();
  const withTable = apps.filter(function (a) { return AUTH_TABLE_BY_APP[a]; });

  // ── VACUITY FIRST. Every arm below iterates one of these. ───────────────
  test('the populations are real -- a short scan here would make every arm '
    + 'below pass over almost nothing', function () {
    assert.ok(apps.length >= 17,
      'ROLES_BY_APP yielded only ' + apps.length + ' apps');
    assert.ok(withTable.length >= 16,
      'only ' + withTable.length + ' apps resolved an auth table through '
      + 'AUTH_TABLE_BY_APP');
    const declCount = Object.keys(checks).reduce(function (n, t) {
      return n + checks[t].length;
    }, 0);
    assert.ok(declCount >= 16,
      'only ' + declCount + ' employee_auth role CHECK(s) were '
      + 'parsed out of sql/, so this suite compared almost nothing. The DDL or '
      + 'the CHECK was reformatted past the regex.');
    // AND THE STRIPPER MUST ACTUALLY STRIP, proven on a fixture rather than
    // trusted: without this, a regex that accidentally matched comment text
    // would still satisfy every arm below.
    const NL = String.fromCharCode(10);
    assert.strictEqual(
      stripSqlComments("role text check (role in ('a')), -- 'ghost'" + NL + "x").indexOf('ghost'),
      -1, 'stripSqlComments left a quoted name that was inside a comment');
  });

  test('where a table is declared MORE THAN ONCE in sql/, every declaration '
    + 'permits the SAME roles -- two CHECKs for one table is how both get '
    + 'believed', function () {
    // MEASURED, NOT ANTICIPATED: sairncare_employee_auth is declared twice
    // today, in its own schema file and again in a migration bundle, and the
    // two agree. The failure this arm exists for is the day they stop agreeing,
    // because then "what the database accepts" depends on which file was run
    // last and no reader of either file can tell.
    const inconsistent = [];
    Object.keys(checks).forEach(function (t) {
      const decls = checks[t];
      if (decls.length < 2) return;
      const first = JSON.stringify(decls[0].roles);
      decls.slice(1).forEach(function (d) {
        if (JSON.stringify(d.roles) !== first) {
          inconsistent.push(t + ': ' + decls[0].file + ' permits ' + first
            + ' but ' + d.file + ' permits ' + JSON.stringify(d.roles));
        }
      });
    });
    assert.deepStrictEqual(inconsistent, [], inconsistent.join('; '));
  });

  test('every app with an auth table has a PARSEABLE role CHECK in sql/ -- a '
    + 'table with no CHECK is not an app with no rules, it is an app whose '
    + 'rules this suite could not read', function () {
    const problems = [];
    withTable.forEach(function (app) {
      const t = AUTH_TABLE_BY_APP[app];
      const decls = checks[t];
      if (!decls || !decls.length) {
        problems.push(app + '/' + t + ': no `create table if not exists ' + t + '` found in sql/');
        return;
      }
      decls.forEach(function (d) {
        if (d.roles === null) problems.push(app + '/' + t + ': declared in ' + d.file + ' but its role CHECK did not parse');
        else if (!d.roles.length) problems.push(app + '/' + t + ': its role CHECK in ' + d.file + ' parsed to an EMPTY list');
      });
    });
    assert.deepStrictEqual(problems, [], problems.join('; '));
  });

  // ── THE LOAD-BEARING ARM ────────────────────────────────────────────────
  test('THE LOAD-BEARING ONE: for every app, ROLES_BY_APP and the sql/ role '
    + 'CHECK are the SAME SET, in both directions', function () {
    const diverged = divergences(withTable, ROLES_BY_APP, checks);
    assert.deepStrictEqual(diverged, [],
      diverged.length + ' app(s) disagree:\n       ' + diverged.join('\n       '));
  });

  // -- THE NEGATIVE CONTROL, AND IT IS NOT OPTIONAL --------------------------
  // ADDED 2026-10-13 (b8). The arm above was GREEN on the day it was written
  // and had never once been seen to fail. A comparison that has only ever
  // agreed is indistinguishable from a comparison that CANNOT disagree -- and
  // this file exists because three other files WARNED about this exact drift in
  // prose while it happened anyway. A warning that has become an assertion
  // which has never fired is the same artefact one layer down.
  //
  // THE CONTROL IS PER APP, NOT ONE WITNESS, because item 5 asks for a test
  // that fails when ROLES_BY_APP and any sql/ CHECK diverge FOR EVERY APP. A
  // single planted divergence proves the detector fires once; it says nothing
  // about the other fifteen, and an app whose CHECK this suite silently cannot
  // parse would pass a one-witness control forever. That case is reported as a
  // MISSED CONTROL rather than skipped.
  //
  // BOTH DIRECTIONS, because they are different defects with different
  // symptoms: a role the server will mint and the CHECK rejects is a 400
  // carrying a Postgres check violation at provisioning time -- what
  // trustee.audit did for sixteen days -- while a role the CHECK permits and
  // the server will not mint is dead vocabulary that reads as a working feature.
  //
  // PLANTED IN A COPY. Nothing in sql/ and nothing in api/_lib/auth.js is
  // touched; the fixtures are copies, which is what makes this safe to run in
  // the live clone rather than in a worktree.
  test('NEGATIVE CONTROL: the comparison CATCHES a planted divergence, in '
    + 'BOTH directions, for EVERY app', function () {
    const PLANT = ['fx', 'planted', 'role'].join('.');
    const missed = [];
    withTable.forEach(function (app) {
      const table = AUTH_TABLE_BY_APP[app];
      // (a) the server accepts a role the CHECK rejects.
      const codePlus = Object.assign({}, ROLES_BY_APP);
      codePlus[app] = ROLES_BY_APP[app].concat([PLANT]);
      const a = divergences([app], codePlus, checks);
      if (!a.length || a.join(' ').indexOf(PLANT) === -1) {
        missed.push(app + ': a role in ROLES_BY_APP and NOT in the CHECK was '
          + 'not reported');
      }
      // (b) the CHECK permits a role the server will not mint.
      const sqlPlus = {};
      Object.keys(checks).forEach(function (t) {
        sqlPlus[t] = checks[t].map(function (d) {
          return { file: d.file, roles: d.roles ? d.roles.slice() : d.roles };
        });
      });
      let planted = false;
      (sqlPlus[table] || []).forEach(function (d) {
        if (d.roles) { d.roles = d.roles.concat([PLANT]).sort(); planted = true; }
      });
      if (!planted) {
        missed.push(app + ': no parseable CHECK declaration to plant into, so '
          + 'this app is NOT actually being compared by the arm above');
        return;
      }
      const b = divergences([app], ROLES_BY_APP, sqlPlus);
      if (!b.length || b.join(' ').indexOf(PLANT) === -1) {
        missed.push(app + ': a role in the CHECK and NOT in ROLES_BY_APP was '
          + 'not reported');
      }
    });
    assert.deepStrictEqual(missed, [],
      missed.length + ' control(s) did not fire:\n       '
      + missed.join('\n       '));
  });

  test('...and the comparison is not vacuous: at least one app has a NON-TRIVIAL '
    + 'list and SAIRNfreedom carries the trustee that caused this file', function () {
    // The arm above is satisfied by two empty sets. This is the anchor that
    // proves it compared something real, and it names the specific role whose
    // sixteen-day absence is why this suite exists.
    const biggest = withTable.reduce(function (n, a) {
      return Math.max(n, ROLES_BY_APP[a].length);
    }, 0);
    assert.ok(biggest >= 10, 'the largest role list has ' + biggest + ' entries');
    assert.ok(ROLES_BY_APP.sairnfreedom.indexOf('trustee.audit') !== -1,
      'trustee.audit is not in ROLES_BY_APP.sairnfreedom');
    const sfDecls = checks[AUTH_TABLE_BY_APP.sairnfreedom] || [];
    assert.ok(sfDecls.length && sfDecls.every(function (d) {
      return d.roles && d.roles.indexOf('trustee.audit') !== -1;
    }),
      'trustee.audit is not in the sairnfreedom_employee_auth role CHECK, so '
      + 'the login Michael approved would fail at the database');
  });

  // ── THE APP WITH NO TABLE IS NAMED, NOT SKIPPED ─────────────────────────
  test('every app WITHOUT an auth table is accounted for by name -- a silent '
    + 'skip is how a real app stops being checked', function () {
    const noTable = apps.filter(function (a) { return !AUTH_TABLE_BY_APP[a]; });
    // stonedesk_sub shares sd_employee_auth with stonedesk BY DESIGN: it is the
    // subcontractor view of one StoneDesk tenant, not a separate tenant, and
    // its single role is granted on the parent app's table. If a NEW name turns
    // up here, it is an app whose credentials nothing in this suite checks --
    // which is the state this arm refuses to let pass quietly.
    assert.deepStrictEqual(noTable, ['stonedesk_sub'],
      'unexpected app(s) with no auth table: ' + JSON.stringify(noTable)
      + '. Either AUTH_TABLE_BY_APP is missing an entry -- in which case '
      + 'credentialStillActive answers NO_ACTIVE_CHECK and the request proceeds '
      + 'on the token alone, which FAILS OPEN -- or a new app needs a row here.');
  });

  const declTotal = Object.keys(checks).reduce(function (n, t) { return n + checks[t].length; }, 0);
  console.log('\n' + passed + ' passed, ' + failed + ' failed  (' + withTable.length
    + ' app(s) compared, ' + declTotal + ' declaration(s) of '
    + Object.keys(checks).length + ' table(s) parsed)');
  console.log('\nWHAT A GREEN RUN DOES NOT SAY: that the LIVE database agrees. '
    + 'This reads\nsql/ files. A constraint widened live and never written back '
    + 'is invisible here --\nthat state existed on three audit-log tables until '
    + '2026-10-13. Nor does it\ncheck each app\'s HTML, the third copy; only '
    + 'SAIRNfreedom\'s is checked, in\napi/sf-auth.test.js.');
  if (failed) process.exit(1);
}

main();
