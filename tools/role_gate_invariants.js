// tools/role_gate_invariants.js
//
//   node tools/role_gate_invariants.js
//   node tools/role_gate_invariants.js --json
//
// THE HALF OF ITEM 78 THAT RUNS. docs/spec/RoleGates.tla states the properties
// SAIRN's cross-app role gates are supposed to have; this checks that the REAL
// exported role sets in api/*-auth.js still have them.
//
// ── NEITHER HALF IS ENOUGH ALONE ───────────────────────────────────────────
// A TLA+ spec is a statement about a MODEL. Nothing connects it to the
// JavaScript, and a spec that drifts from the code it describes is worse than
// none: it is a document asserting properties nobody holds. So the invariants
// are written twice on purpose -- once formally, once against the real
// constants -- and this file is the one that fails when the code moves.
//
// ── EXHAUSTIVE IS AFFORDABLE HERE, WHICH IS WHY THIS CLASS WAS CHOSEN ──────
// Sixteen apps, at most six roles each. There is no sampling and no heuristic:
// every app is checked against every invariant over its whole role set. That is
// the property that made authorization the right first target -- the rules are
// small enough to state exactly, and the cost of a wrong answer is somebody
// reading a controlled-substance register.
//
// ── UNSPECIFIED IS A THIRD STATE AND IT IS COUNTED SEPARATELY ──────────────
// Several auth modules export no role sets at all -- their gates are internal.
// That is NOT "no violations": it is "not checkable from outside", and folding
// the two together would let the coverage fall to zero while the output stayed
// green. The denominator is printed on every run.
//
// Exit 0 clean, 1 an invariant is violated, 2 could not run.

'use strict';
const fs = require('fs');
const path = require('path');

const REPO = path.dirname(__dirname);
const AUTH_DIR = path.join(REPO, 'api');
const EXIT_CLEAN = 0, EXIT_FINDING = 1, EXIT_COULD_NOT_RUN = 2;

function asSet(v) {
  if (Array.isArray(v)) return v.slice();
  if (v && typeof v === 'object') return Object.keys(v).filter((k) => v[k]);
  return null;
}

function load() {
  let files;
  try {
    files = fs.readdirSync(AUTH_DIR).filter((f) => /-auth\.js$/.test(f)).sort();
  } catch (e) {
    return { err: 'could not read api/ (' + e.code + '), so NOTHING was checked' };
  }
  if (!files.length) return { err: 'no api/*-auth.js modules found, so nothing was checked' };
  const apps = {};
  const unreadable = [];
  for (const f of files) {
    let m;
    try {
      m = require(path.join(AUTH_DIR, f));
    } catch (e) {
      // A MODULE THAT WILL NOT LOAD IS NOT A MODULE WITH NO ROLES.
      unreadable.push(f + ' -- ' + (e && e.message ? e.message.slice(0, 90) : 'require failed'));
      continue;
    }
    apps[f] = {
      provisioning: asSet(m.PROVISIONING_ROLES),
      management: asSet(m.MANAGEMENT_ROLES),
      authenticated: asSet(m.AUTHENTICATED_ROLES),
      broadRead: asSet(m.BROAD_READ_ROLES),
      prescriber: asSet(m.PRESCRIBER_ROLES)
    };
  }
  return { apps: apps, unreadable: unreadable, fileCount: files.length };
}

const subset = (a, b) => a.every((x) => b.indexOf(x) !== -1);
const missing = (a, b) => a.filter((x) => b.indexOf(x) === -1);

// Each invariant says which SPEC clause it is, so a violation here can be read
// against the formal statement rather than only against this file.
const INVARIANTS = [
  {
    id: 'I3', spec: 'ProvisioningIsManagement',
    needs: ['provisioning', 'management'],
    why: 'whoever may create credentials must already be management',
    check: (r) => subset(r.provisioning, r.management)
      ? null
      : 'PROVISIONING_ROLES has ' + JSON.stringify(missing(r.provisioning, r.management)) +
        ' which is not in MANAGEMENT_ROLES -- a role that can mint credentials '
        + 'and is not management'
  },
  {
    id: 'I4', spec: 'ManagementIsAuthenticated',
    needs: ['management', 'authenticated'],
    why: 'a management role that cannot sign in is a gate nobody can pass',
    check: (r) => subset(r.management, r.authenticated)
      ? null
      : 'MANAGEMENT_ROLES has ' + JSON.stringify(missing(r.management, r.authenticated)) +
        ' which is not in AUTHENTICATED_ROLES -- that gate reads as locked down '
        + 'and is broken'
  },
  {
    id: 'I5a', spec: 'NoEmptyGate',
    needs: ['management'],
    why: 'an empty allowed-set is a door with no key, and whether it reads as '
       + 'refuse-all or allow-all depends on how the predicate was written',
    check: (r) => r.management.length ? null : 'MANAGEMENT_ROLES is EMPTY'
  },
  {
    id: 'I5b', spec: 'NoEmptyGate',
    needs: ['authenticated'],
    why: 'same, for the set that decides who may sign in at all',
    check: (r) => r.authenticated.length ? null : 'AUTHENTICATED_ROLES is EMPTY'
  },
  {
    id: 'I5c', spec: 'NoEmptyGate',
    needs: ['provisioning'],
    why: 'an empty provisioning set means no one can ever add an employee, and '
       + 'the app has no way back',
    check: (r) => r.provisioning.length ? null : 'PROVISIONING_ROLES is EMPTY'
  }
];

// Stated as an OBSERVATION, never as a requirement -- see the spec's own note.
// It holds today in SAIRNroofing and makes the management term in
// `~management && ~broad` redundant at 22 sites. The day it stops holding, all
// 22 change meaning at once, silently, and this is the line that says so.
const OBSERVATIONS = [
  {
    id: 'O1', needs: ['management', 'broadRead'],
    holds: (r) => subset(r.management, r.broadRead),
    whenTrue: 'MANAGEMENT_ROLES is a subset of BROAD_READ_ROLES, so any '
            + '`!management && !broad` predicate is today identical to `!broad` '
            + '-- the management term is redundant and both must be kept, '
            + 'because the day a management role is added that is not a broad '
            + 'reader every such site changes meaning at once',
    whenFalse: 'MANAGEMENT_ROLES is NO LONGER a subset of BROAD_READ_ROLES. '
             + 'Every `!management && !broad` predicate has just started '
             + 'answering a different question from the one it answered '
             + 'yesterday. READ THEM.'
  }
];

function main(argv) {
  const loaded = load();
  if (loaded.err) {
    console.error('COULD NOT RUN: ' + loaded.err + '. That is not a clean result.');
    return EXIT_COULD_NOT_RUN;
  }
  const findings = [];
  const notes = [];
  const unspecified = [];
  let checks = 0;

  for (const app of Object.keys(loaded.apps)) {
    const r = loaded.apps[app];
    for (const inv of INVARIANTS) {
      const have = inv.needs.every((k) => Array.isArray(r[k]));
      if (!have) {
        unspecified.push(app + ' ' + inv.id + ' (exports no ' +
          inv.needs.filter((k) => !Array.isArray(r[k])).join('/') + ')');
        continue;
      }
      checks++;
      const bad = inv.check(r);
      if (bad) {
        findings.push(app + ' violates ' + inv.id + ' (' + inv.spec + '): ' + bad +
          ' -- ' + inv.why);
      }
    }
    for (const o of OBSERVATIONS) {
      if (!o.needs.every((k) => Array.isArray(r[k]))) continue;
      notes.push(app + ' ' + o.id + ': ' + (o.holds(r) ? o.whenTrue : o.whenFalse));
    }
  }

  if (argv.indexOf('--json') !== -1) {
    console.log(JSON.stringify({
      findings: findings, notes: notes, unspecified: unspecified,
      checks: checks, unreadable: loaded.unreadable
    }, null, 2));
  } else {
    console.log('ROLE GATE INVARIANTS -- docs/spec/RoleGates.tla');
    console.log('  auth modules on disk : %d', loaded.fileCount);
    console.log('  invariant checks RUN : %d', checks);
    // THE DENOMINATOR. A module exporting nothing is not a module with no
    // violations, and letting coverage fall to zero behind a green line is the
    // failure every convention in the disciplines document defends against.
    console.log('  NOT CHECKABLE        : %d (module exports no such set -- this '
                + 'is not "no violations")', unspecified.length);
    if (loaded.unreadable.length) {
      console.log('\n  COULD NOT LOAD (%d) -- NOT counted as clean:', loaded.unreadable.length);
      for (const u of loaded.unreadable) console.log('    ? ' + u);
    }
    if (notes.length) {
      console.log('\n  OBSERVATIONS (true today, NOT required):');
      for (const n of notes) console.log('    . ' + n);
    }
    if (unspecified.length) {
      console.log('\n  UNSPECIFIED:');
      for (const u of unspecified.slice(0, 40)) console.log('    - ' + u);
      if (unspecified.length > 40) console.log('    ... and %d more', unspecified.length - 40);
    }
    if (findings.length) {
      console.log('\nVIOLATIONS (%d):', findings.length);
      for (const f of findings) console.log('  ! ' + f);
    } else {
      console.log('\nNo invariant is violated by the role sets these modules export.');
      console.log('That is a statement about %d checks, not about the %d that could '
                  + 'not be made.', checks, unspecified.length);
    }
  }
  if (loaded.unreadable.length) return EXIT_COULD_NOT_RUN;
  return findings.length ? EXIT_FINDING : EXIT_CLEAN;
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = { load, INVARIANTS, OBSERVATIONS, main };
