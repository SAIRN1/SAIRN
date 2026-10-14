// api/lifecycle-audit-event-coverage.test.js
//
// REQUIREMENT: every api/*-auth.js that calls the shared credential-lifecycle
//   engine has an audit-log CHECK constraint that PERMITS the event types that
//   engine emits. A rejected event_type is a silently missing audit row.
//
// Run:  node api/lifecycle-audit-event-coverage.test.js
//
// ── THE DEFECT THIS EXISTS BECAUSE OF ─────────────────────────────────────
// EVERY credential deactivation, reactivation and refusal in SAIRNlaw was
// failing to write its audit row, and had been since the lifecycle engine was
// adopted. api/law-auth.js's set_active calls api/_lib/employee-lifecycle.js,
// which emits `credential_deactivated`, `credential_reactivated` and
// `credential_change_refused`; sairnlaw_audit_log's CHECK permitted none of the
// three. writeAuditLog is NON-FATAL and returns false, so the INSERT was
// rejected 23514, the handler carried on, and the caller got its 200.
//
// THE LOG'S EMPTINESS READ AS "NOTHING HAPPENED". That is the whole cost: an
// audit log is consulted precisely when somebody asks who removed an account,
// and this one would have answered "nobody did".
//
// ── WHY NO EXISTING CHECKER SAW IT ───────────────────────────────────────
// tools/audit_event_type_check.py compares emitted event types against CHECK
// constraints and exits 0 with this gap live. Its own LIMITS section says why:
// "ONE HELPER IS FOLLOWED AND THE REST ARE NOT". It resolves the pin-setup
// helper's call sites through each caller's `const APP`, and the lifecycle
// engine is a SECOND helper it does not follow. The engine also has no
// `const APP` of its own -- it is shared by eleven apps -- so attributing its
// emissions requires walking the callers, which that tool does not do for it.
//
// THIS FILE IS THAT WALK, FOR THAT ONE ENGINE. It is deliberately narrow: it
// does not re-implement the general checker, and extending the general one is
// routed to cc because tools/ is cc's.
//
// ── WHAT IT DOES NOT COVER ───────────────────────────────────────────────
// THE DATABASE. It reads sql/ files. A constraint widened live and never
// written back is invisible here, and the reverse -- a file widened and never
// RUN -- is equally invisible. As at the commit that added this file, the
// sairnlaw ALTER had NOT been run, so this suite is green and the live log is
// still dropping rows. That is not a flaw in the suite; it is the boundary of
// what a clone can know, and it is why the sql/ block carries a query that
// answers it from the database side.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { AUDIT_TABLE_BY_APP } = require('./_lib/audit');

const API_DIR = __dirname;
const SQL_DIR = path.join(__dirname, '..', 'sql');

// The three the engine emits. READ OUT OF THE ENGINE, not transcribed: a
// hand-kept copy here would be a fourth list to drift, which is the exact shape
// this batch spent its methodology item removing.
function emittedByEngine() {
  const src = fs.readFileSync(path.join(API_DIR, '_lib', 'employee-lifecycle.js'), 'utf8');
  const code = src.split('\n').map(function (l) {
    const i = l.indexOf('//');
    return i === -1 ? l : l.slice(0, i);
  }).join('\n');
  const found = new Set();
  const re = /doAudit\(\s*(?:[^)]*?\?\s*)?'([a-z0-9_]+)'(?:\s*:\s*'([a-z0-9_]+)')?/g;
  let m;
  while ((m = re.exec(code)) !== null) {
    if (m[1]) found.add(m[1]);
    if (m[2]) found.add(m[2]);
  }
  return Array.from(found).sort();
}

function stripSqlComments(src) {
  const NL = String.fromCharCode(10);
  return src.split(NL).map(function (l) {
    const i = l.indexOf('--');
    return i === -1 ? l : l.slice(0, i);
  }).join(NL);
}

// audit table -> [{file, allowed}] for every `create table ... *_audit_log`
// declaration in sql/. Every declaration, not the first: a stale copy in a
// migration bundle must not hide behind a current one.
function auditChecks() {
  const out = Object.create(null);
  fs.readdirSync(SQL_DIR).filter(function (f) { return /\.sql$/.test(f); })
    .sort().forEach(function (f) {
      const code = stripSqlComments(fs.readFileSync(path.join(SQL_DIR, f), 'utf8'));
      const ddl = /create table if not exists\s+(?:public\.)?(\w*audit_log)\b/gi;
      let m;
      while ((m = ddl.exec(code)) !== null) {
        const tail = code.slice(m.index, m.index + 8000);
        const chk = /event_type\s+text[^,]*check\s*\(\s*event_type\s+in\s*\(([^)]*)\)/i.exec(tail);
        (out[m[1]] = out[m[1]] || []).push({
          file: f,
          allowed: chk
            ? Array.from(new Set((chk[1].match(/'([a-z0-9_]+)'/g) || [])
                .map(function (s) { return s.replace(/'/g, ''); }))).sort()
            : null
        });
      }
    });
  return out;
}

// Every auth endpoint that calls the engine's setActive, with the `const APP`
// its audit rows are attributed to.
function lifecycleCallers() {
  return fs.readdirSync(API_DIR)
    .filter(function (f) { return /-auth\.js$/.test(f); })
    .sort()
    .map(function (f) {
      const src = fs.readFileSync(path.join(API_DIR, f), 'utf8');
      if (src.indexOf('lifecycle.setActive') === -1) return null;
      const m = /const APP\s*=\s*'([a-z_]+)'/.exec(src);
      return { file: f, app: m ? m[1] : null };
    })
    .filter(Boolean);
}

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); passed++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); failed++; }
}

function main() {
  console.log('CREDENTIAL-LIFECYCLE AUDIT EVENT COVERAGE\n');

  const events = emittedByEngine();
  const callers = lifecycleCallers();
  const checks = auditChecks();

  test('the populations are real -- a short scan here would make the arm below '
    + 'pass over nothing', function () {
    assert.ok(events.length >= 3,
      'only ' + events.length + ' event type(s) parsed out of '
      + 'api/_lib/employee-lifecycle.js: ' + JSON.stringify(events)
      + '. The doAudit() call shape changed and this suite is now blind.');
    for (const required of ['credential_deactivated', 'credential_reactivated',
                            'credential_change_refused']) {
      assert.ok(events.indexOf(required) !== -1,
        required + ' was not found in the engine. Either it stopped being '
        + 'emitted -- which is a bigger finding than this suite was written for '
        + '-- or the parse broke.');
    }
    assert.ok(callers.length >= 11,
      'only ' + callers.length + ' auth endpoint(s) were found calling '
      + 'lifecycle.setActive');
    assert.ok(Object.keys(checks).length >= 16,
      'only ' + Object.keys(checks).length + ' audit_log CHECK(s) parsed from sql/');
  });

  test('every lifecycle caller resolves an APP and an audit table -- an '
    + 'unresolved caller is a caller this suite cannot check, not one that '
    + 'passes', function () {
    const problems = [];
    callers.forEach(function (c) {
      if (!c.app) {
        problems.push(c.file + ": no `const APP = '...'` found, so its audit "
          + 'rows cannot be attributed to a table');
        return;
      }
      if (!AUDIT_TABLE_BY_APP[c.app]) {
        problems.push(c.file + ': APP ' + c.app + ' has no entry in '
          + 'AUDIT_TABLE_BY_APP, so writeAuditLog has nowhere to write');
      }
    });
    assert.deepStrictEqual(problems, [], problems.join('; '));
  });

  // ── THE LOAD-BEARING ARM ────────────────────────────────────────────────
  test('THE LOAD-BEARING ONE: every lifecycle caller\'s audit log PERMITS every '
    + 'event the engine emits', function () {
    const gaps = [];
    callers.forEach(function (c) {
      const table = c.app && AUDIT_TABLE_BY_APP[c.app];
      if (!table) return;                  // refused by the arm above, not here
      (checks[table] || []).forEach(function (d) {
        if (!d.allowed) {
          gaps.push(c.file + ' -> ' + table + ' (' + d.file
            + '): its event_type CHECK did not parse, so nothing was compared');
          return;
        }
        const missing = events.filter(function (e) { return d.allowed.indexOf(e) === -1; });
        if (missing.length) {
          gaps.push(c.file + ' -> ' + table + ' (' + d.file + ') REJECTS '
            + JSON.stringify(missing)
            + ' -- every one of those is a credential change that writes NO '
            + 'audit row, because writeAuditLog is non-fatal and the handler '
            + 'still answers 200');
        }
      });
      if (!checks[table]) {
        gaps.push(c.file + ' -> ' + table + ': no `create table` for it in sql/');
      }
    });
    assert.deepStrictEqual(gaps, [],
      gaps.length + ' gap(s):\n       ' + gaps.join('\n       '));
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed  ('
    + callers.length + ' caller(s) x ' + events.length + ' event(s), against '
    + Object.keys(checks).length + ' audit table(s))');
  console.log('\nWHAT A GREEN RUN DOES NOT SAY: that the LIVE constraint permits '
    + 'them. This reads\nsql/ files, so a file widened and never RUN is green '
    + 'here and still dropping rows\nin production -- which is exactly the state '
    + 'of sairnlaw_audit_log at the commit\nthat added this suite. The sql/ '
    + 'block carries a query that answers it from the\ndatabase side.');
  if (failed) process.exit(1);
}

main();
