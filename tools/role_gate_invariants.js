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
// every app is checked against every invariant ~~over its whole role set~~ THAT
// THIS TOOL IMPLEMENTS, over its whole role set. That is the property that made
// authorization the right first target -- the rules are small enough to state
// exactly, and the cost of a wrong answer is somebody reading a
// controlled-substance register.
//
// THE QUALIFIER WAS MISSING AND IT MATTERED (CC's review, 2026-09-14, Finding
// 4). "Every invariant" read as all of them; the spec has I1 and I2 as well,
// this file implements neither, and the output said nothing. Both are runtime
// properties proven elsewhere -- see SPEC_NOT_CHECKED_HERE, which the run now
// PRINTS with where each one is actually proven. The existing denominator does
// not cover them: "N not checkable" is about role sets that could not be READ,
// and an invariant never evaluated for any app appears in no count at all.
//
// ── UNSPECIFIED IS A THIRD STATE AND IT IS COUNTED SEPARATELY ──────────────
// Several auth modules export no role sets at all -- their gates are internal.
// That is NOT "no violations": it is "not checkable from outside", and folding
// the two together would let the coverage fall to zero while the output stayed
// green. The denominator is printed on every run.
//
// ── 2026-09-14: THE 61 WERE THE FINDING, SO THE 61 ARE THE WORK ────────────
// The first run made 19 checks and could not make 61, because "exports it" was
// the only way this tool could see a role set. Nine of sixteen modules DECLARE
// `MANAGEMENT_ROLES` / `PROVISIONING_ROLES` and export neither. Three sources
// are read now, and WHICH ONE ANSWERED IS CARRIED ON EVERY CHECK:
//
//   exported  module.exports.X -- the module's own public statement.
//   internal  the module is executed with an appendix that exports its
//             module-scope constants, so the value read is THE VALUE THE GATE
//             USES. Not a text scrape.
//   derived   AUTHENTICATED_ROLES from `ROLES_BY_APP[APP]` in api/_lib/auth.js,
//             licensed by invariant I6 below and withdrawn wholesale if I6 ever
//             fails.
//
// **THE PROVENANCE IS NOT DECORATION AND THE COUNTS ARE NEVER FUSED.** A
// derived answer is weaker evidence than an exported one; printing one total
// would hide a coverage number that grew only because the evidence got thinner.
// Same discipline as the attestation downgrade in tools/claim_provenance.py.
//
// **WHY EXECUTE RATHER THAN PARSE, and it is not a preference.** `sb-auth.js`
// contains the text `MANAGEMENT_ROLES` in a comment reading "This app has no
// MANAGEMENT_ROLES concept". Any grep or regex reader finds that token and has
// to guess; this one runs the module and correctly reports the constant does
// not exist. Executing is also no new risk -- load() already requires every one
// of these modules and has since the first version.
//
// It does mean each module's top level runs TWICE per invocation, once through
// require() and once through the probe, so the property this rests on is that
// these modules do no top-level work: they define constants and export a
// handler. Measured 2026-09-14 -- whole run 0.18s, and no active handle or
// request survives load(), so nothing was opened and left open. If an auth
// module ever opens a connection or starts a timer at import time, this run
// doubles it and that is the line to come back to.
//
// **ABSENT AND COULD-NOT-PROBE ARE DIFFERENT AND STAY DIFFERENT.** A constant
// that genuinely is not there is a fact about the app. A probe that threw is a
// fact about this tool, and it is named, counted apart, and never allowed to
// read as "that app has no management tier".
//
// Exit 0 clean, 1 an invariant is violated, 2 could not run.

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const Module = require('module');

const REPO = path.dirname(__dirname);
const AUTH_DIR = path.join(REPO, 'api');
const EXIT_CLEAN = 0, EXIT_FINDING = 1, EXIT_COULD_NOT_RUN = 2;

// The module-scope names worth asking for. APP is here because it is the key
// into ROLES_BY_APP and therefore the whole derivation.
const PROBE_NAMES = ['PROVISIONING_ROLES', 'MANAGEMENT_ROLES', 'AUTHENTICATED_ROLES',
  'BROAD_READ_ROLES', 'PRESCRIBER_ROLES', 'APP'];

// Run the module with an appendix that hands back its module-scope constants.
// `typeof x === 'undefined'` rather than a bare reference, because a missing
// const must come back as ABSENT and not as a ReferenceError that would be
// indistinguishable from the module being broken.
function probeInternals(file) {
  const src = fs.readFileSync(file, 'utf8');
  const tail = '\n;module.exports.__probe__ = {' + PROBE_NAMES.map(
    (n) => n + ': (typeof ' + n + " === 'undefined' ? undefined : " + n + ')').join(', ') + '};\n';
  const m = new Module(file, null);
  m.filename = file;
  m.paths = Module._nodeModulePaths(path.dirname(file));
  const fn = vm.runInThisContext(Module.wrap(src + tail), { filename: file });
  fn.call(m.exports, m.exports, m.require.bind(m), m, file, path.dirname(file));
  return m.exports.__probe__ || {};
}

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
  const unprobed = [];
  const KEYS = [
    ['provisioning', 'PROVISIONING_ROLES'], ['management', 'MANAGEMENT_ROLES'],
    ['authenticated', 'AUTHENTICATED_ROLES'], ['broadRead', 'BROAD_READ_ROLES'],
    ['prescriber', 'PRESCRIBER_ROLES']
  ];
  for (const f of files) {
    const full = path.join(AUTH_DIR, f);
    let m;
    try {
      m = require(full);
    } catch (e) {
      // A MODULE THAT WILL NOT LOAD IS NOT A MODULE WITH NO ROLES.
      unreadable.push(f + ' -- ' + (e && e.message ? e.message.slice(0, 90) : 'require failed'));
      continue;
    }
    // A PROBE THAT THREW IS NOT AN APP WITHOUT ROLES. It is recorded as its own
    // state, and every set this module did not export stays NOT CHECKABLE --
    // which is what it was before this feature existed, so a broken probe can
    // only lose the coverage it added and can never invent a clean answer.
    let probed = {}, probeErr = null;
    try {
      probed = probeInternals(full);
    } catch (e) {
      probeErr = (e && e.message ? e.message.slice(0, 90) : 'probe failed');
      unprobed.push(f + ' -- ' + probeErr);
    }
    const r = { app: typeof probed.APP === 'string' ? probed.APP : null, prov: {} };
    for (const [key, name] of KEYS) {
      const fromExport = asSet(m[name]);
      if (fromExport) { r[key] = fromExport; r.prov[key] = 'exported'; continue; }
      const fromInternal = asSet(probed[name]);
      if (fromInternal) { r[key] = fromInternal; r.prov[key] = 'internal'; continue; }
      r[key] = null;
      r.prov[key] = probeErr ? 'could-not-probe' : 'absent';
    }
    apps[f] = r;
  }
  return {
    apps: apps, unreadable: unreadable, unprobed: unprobed, fileCount: files.length,
    vocabulary: vocabulary()
  };
}

// The app role vocabulary, read from the one module every auth handler already
// keys into. Returned as {} rather than thrown on, because a missing vocabulary
// must withdraw the derivation, not stop the 19 checks that never needed it.
function vocabulary() {
  try {
    const v = require(path.join(AUTH_DIR, '_lib', 'auth.js')).ROLES_BY_APP;
    return v && typeof v === 'object' ? v : {};
  } catch (e) {
    return {};
  }
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

// ── WHAT THE SPEC REQUIRES THAT THIS TOOL CANNOT CHECK, DECLARED ──────────
// The spec's Safety conjunction is larger than the list above, and the gap has
// to be written down HERE rather than inferred by whoever reads one half. Each
// of these is a property of RUNNING BEHAVIOUR -- a token being presented to an
// endpoint -- and nothing about a role set can decide it. Naming them is what
// keeps "this tool passes" from being read as "the spec holds".
//
// The probe asserts every Safety conjunct is either checked above or listed
// here, so a NEW spec invariant cannot be added and quietly go unchecked.
// I6 is checked, but not by INVARIANTS -- it is a control over the whole run
// rather than a rule applied per app, so it lives in applyDerivation(). Listed
// so the coverage arithmetic stays complete without pretending it is a normal
// invariant or, worse, listing it as unchecked.
const SPEC_CHECKED_ELSEWHERE = {
  AuthenticatedMatchesVocabulary:
    'applyDerivation() -- a control over the run, not a per-app rule: its '
    + 'failure withdraws every derived set instead of reporting one app'
};

// ── AND IT IS PRINTED, NOT ONLY DECLARED (2026-09-14) ──────────────────────
// CC's independent review, Finding 4: this file's header said "every app is
// checked against every invariant" while implementing I3, I4, I5a/b/c only.
// I1 (AppIsolation) and I2 (DeactivationBinds) are in the spec and have NO
// checker here, and the output never said so.
//
// THE DENOMINATOR THAT WAS ALREADY PRINTED DOES NOT COVER THIS, and that is
// the sharp part of the finding. "56 checks run, 22 not checkable" is about
// role SETS that could not be READ. An invariant never evaluated for any app
// does not appear in either number. Two different kinds of gap, one of them
// invisible.
//
// So each entry now carries WHERE the property is actually proven. Neither is
// unproven -- both are runtime behaviour covered elsewhere -- which is why the
// fix is a disclosure rather than new code here.
const SPEC_NOT_CHECKED_HERE = {
  TypeOK: {
    why: 'a well-formedness statement about the model\'s own variables; there '
       + 'is no runtime counterpart to read',
    proven_by: '(nothing to prove -- it constrains the model, not the code)'
  },
  AppIsolation: {
    why: 'requires presenting a token minted for one app to another and '
       + 'observing the refusal -- behaviour, not a role set, and no reading of '
       + 'MANAGEMENT_ROLES can decide it',
    proven_by: 'tests/app_session_isolation.js, plus the Semgrep rule '
             + '.semgrep/verify-session-token-app-scope.yml which blocks a '
             + 'verifySessionToken() call missing its expectedApp argument'
  },
  DeactivationBinds: {
    why: 'requires a deactivated credential to be refused AT THE GATE. The set '
       + 'of roles is unchanged by deactivation, so this file is structurally '
       + 'blind to it',
    proven_by: 'the deactivated-caller re-check each api/*-auth.js performs '
             + '(activeCaller() and its equivalents), and for the witnessing '
             + 'lock specifically, api/sv-witness.test.js section 5b'
  }
};

const sameSet = (a, b) => a.length === b.length && subset(a, b) && subset(b, a);

// ── I6 IS THE CONTROL THAT LICENSES THE DERIVATION, AND IT RUNS FIRST ──────
// Deriving AUTHENTICATED_ROLES from `ROLES_BY_APP[APP]` is an assumption: that
// the set of roles who may sign in IS the app's role vocabulary. Two modules
// state AUTHENTICATED_ROLES outright -- dnt-auth.js and mech-auth.js -- and on
// 2026-09-14 both equalled their vocabulary exactly. That is what makes the
// derivation checkable rather than merely plausible, and it is the reason the
// assumption is written as an invariant instead of as a comment.
//
// **IF I6 FAILS ANYWHERE, EVERY DERIVED SET IS WITHDRAWN PLATFORM-WIDE** and
// the checks that rested on it go back to NOT CHECKABLE. A derivation whose
// control has failed must not keep answering: that is the fail-open shape --
// coverage staying high while the thing underneath it stopped being true.
function applyDerivation(loaded) {
  const vocab = loaded.vocabulary;
  const violations = [];
  let stated = 0;
  for (const f of Object.keys(loaded.apps)) {
    const r = loaded.apps[f];
    if (!r.app || !Array.isArray(vocab[r.app])) continue;
    if (!Array.isArray(r.authenticated)) continue;
    stated++;
    if (!sameSet(r.authenticated, vocab[r.app])) {
      violations.push(f + ' violates I6 (AuthenticatedMatchesVocabulary): its ' +
        'AUTHENTICATED_ROLES ' + JSON.stringify(r.authenticated.slice().sort()) +
        ' is not the same set as ROLES_BY_APP[' + JSON.stringify(r.app) + '] ' +
        JSON.stringify(vocab[r.app].slice().sort()) + ' -- so who may sign in is ' +
        'NOT the app role vocabulary, and every AUTHENTICATED_ROLES derived from ' +
        'that vocabulary elsewhere is unsound');
    }
  }
  // A control with nothing to control is not a passing control. If no module
  // states AUTHENTICATED_ROLES, I6 is vacuous and cannot license anything.
  const licensed = violations.length === 0 && stated > 0;
  const derived = [];
  if (licensed) {
    for (const f of Object.keys(loaded.apps)) {
      const r = loaded.apps[f];
      if (Array.isArray(r.authenticated)) continue;
      if (r.prov.authenticated === 'could-not-probe') continue;
      if (!r.app || !Array.isArray(vocab[r.app])) {
        // "THIS APP HAS NO SIGN-IN ROLE SET" AND "THIS TOOL COULD NOT FIND THE
        // APP KEY" ARE DIFFERENT FACTS and printed differently. sd-auth.js and
        // sd-sub-auth.js pass their app name as a string literal at each call
        // site instead of declaring `const APP`, so there is nothing to look the
        // vocabulary up by. Closing it is a one-line declaration in each -- a
        // deliberate edit to production auth code, NOT something a checker
        // should infer by scraping `signSessionToken({app: '...'})`.
        r.prov.authenticated = 'no-app-key';
        continue;
      }
      r.authenticated = vocab[r.app].slice();
      r.prov.authenticated = 'derived';
      derived.push(f);
    }
  }
  return { violations: violations, stated: stated, licensed: licensed, derived: derived };
}

function main(argv) {
  const loaded = load();
  if (loaded.err) {
    console.error('COULD NOT RUN: ' + loaded.err + '. That is not a clean result.');
    return EXIT_COULD_NOT_RUN;
  }
  const control = applyDerivation(loaded);
  const findings = control.violations.slice();
  const notes = [];
  const unspecified = [];
  // THE WEAKEST LINK NAMES THE CHECK. An invariant reading one exported set and
  // one derived set is a derived check, because that is the strength of the
  // evidence it rests on -- never the strength of its best input.
  const RANK = { exported: 0, internal: 1, derived: 2 };
  const byProv = { exported: 0, internal: 0, derived: 0 };
  let checks = 0;

  for (const app of Object.keys(loaded.apps)) {
    const r = loaded.apps[app];
    for (const inv of INVARIANTS) {
      const have = inv.needs.every((k) => Array.isArray(r[k]));
      if (!have) {
        const short = inv.needs.filter((k) => !Array.isArray(r[k]));
        unspecified.push(app + ' ' + inv.id + ' (' +
          short.map((k) => k + ': ' + r.prov[k]).join(', ') + ')');
        continue;
      }
      checks++;
      const weakest = inv.needs.reduce(
        (w, k) => (RANK[r.prov[k]] > RANK[w] ? r.prov[k] : w), 'exported');
      byProv[weakest]++;
      const bad = inv.check(r);
      if (bad) {
        findings.push(app + ' violates ' + inv.id + ' (' + inv.spec + '): ' + bad +
          ' -- ' + inv.why + ' [evidence: ' + weakest + ']');
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
      checks: checks, byProvenance: byProv, control: control,
      unreadable: loaded.unreadable, unprobed: loaded.unprobed
    }, null, 2));
  } else {
    console.log('ROLE GATE INVARIANTS -- docs/spec/RoleGates.tla');
    console.log('  auth modules on disk : %d', loaded.fileCount);
    console.log('  invariant checks RUN : %d', checks);
    // THREE NUMBERS, NEVER ONE. Coverage that grew because the evidence got
    // thinner is not the same as coverage that grew, and a single total would
    // report the two identically.
    console.log('    of those, by the WEAKEST evidence each rests on:');
    // String(n).padStart, NOT '%3d' -- Node's console.log has no width syntax and
    // silently appends the argument instead, which is how the first run of this
    // block printed the literal text "%3d" beside a number.
    const w = (n) => String(n).padStart(3);
    console.log('      exported  ' + w(byProv.exported) + '  the module says so itself');
    console.log('      internal  ' + w(byProv.internal) +
      '  read from the module\'s own executed constants');
    console.log('      derived   ' + w(byProv.derived) +
      '  AUTHENTICATED_ROLES from ROLES_BY_APP[APP], licensed by I6');
    // THE DENOMINATOR. A module exporting nothing is not a module with no
    // violations, and letting coverage fall to zero behind a green line is the
    // failure every convention in the disciplines document defends against.
    console.log('  NOT CHECKABLE        : %d (no such set could be read -- this '
                + 'is not "no violations")', unspecified.length);
    // WHAT REMAINS, AND WHETHER ANYONE CAN CLOSE IT. Before this breakdown the
    // whole remainder read as "the tool cannot see", which was true when the
    // only source was module.exports and is not true now. `absent` is a fact
    // about the app -- six of these deliberately have no management tier and
    // say so in their own comments. Only the last two states are work.
    const reasons = {};
    for (const u of unspecified) {
      for (const part of (u.match(/\(([^)]*)\)/) || [null, ''])[1].split(', ')) {
        const why = part.split(': ')[1];
        if (why) reasons[why] = (reasons[why] || 0) + 1;
      }
    }
    console.log('    why, counted by SET not by check:');
    for (const k of Object.keys(reasons).sort()) {
      const gloss = {
        'absent': 'the constant is not there -- a fact about the app, not a gap here',
        'no-app-key': 'the module declares no `const APP`, so its role vocabulary '
                    + 'cannot be looked up. CLOSABLE: one declaration per module',
        'could-not-probe': 'THIS TOOL failed, and that is not the app\'s answer'
      }[k] || '';
      console.log('      ' + k.padEnd(16) + ' ' + String(reasons[k]).padStart(3) +
        '  ' + gloss);
    }
    // ── WHAT THIS TOOL DOES NOT EVALUATE AT ALL ──────────────────────────
    // Distinct from NOT CHECKABLE above, and the distinction is the finding:
    // that one is a role set nobody could READ; this one is a spec invariant
    // never EVALUATED for any app, which appears in no count anywhere.
    const notHere = Object.keys(SPEC_NOT_CHECKED_HERE)
      .filter((k) => k !== 'TypeOK');
    console.log('\n  SPEC INVARIANTS THIS TOOL DOES NOT EVALUATE (%d) -- NOT part',
      notHere.length);
    console.log('  of the counts above, which are about role sets that could not');
    console.log('  be read. These are never asked here for ANY app:');
    for (const k of notHere) {
      const e = SPEC_NOT_CHECKED_HERE[k];
      console.log('    %s -- %s', k, e.why);
      console.log('      proven by: %s', e.proven_by);
    }

    console.log('\n  I6 CONTROL -- what licenses the derived checks:');
    if (control.licensed) {
      console.log('    %d module(s) state AUTHENTICATED_ROLES outright and every one '
                  + 'equals', control.stated);
      console.log('    ROLES_BY_APP[APP], so the derivation is used for %d more.',
        control.derived.length);
    } else if (control.violations.length) {
      console.log('    FAILED. Every derived set is WITHDRAWN and those checks are');
      console.log('    back in NOT CHECKABLE -- a derivation whose control failed');
      console.log('    must stop answering, not keep answering.');
    } else {
      console.log('    VACUOUS -- no module states AUTHENTICATED_ROLES, so there is');
      console.log('    nothing the derivation could be checked against and it is NOT');
      console.log('    used. A control with nothing to control does not pass.');
    }
    if (loaded.unreadable.length) {
      console.log('\n  COULD NOT LOAD (%d) -- NOT counted as clean:', loaded.unreadable.length);
      for (const u of loaded.unreadable) console.log('    ? ' + u);
    }
    if (loaded.unprobed.length) {
      console.log('\n  COULD NOT PROBE (%d) -- their internal sets stay NOT CHECKABLE,',
        loaded.unprobed.length);
      console.log('  which is NOT the same as those apps having no such roles:');
      for (const u of loaded.unprobed) console.log('    ? ' + u);
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
      console.log('\nNo invariant is violated by the role sets these modules export,');
      console.log('declare internally, or inherit from the app role vocabulary.');
      console.log('That is a statement about %d checks, not about the %d that could '
                  + 'not be made.', checks, unspecified.length);
    }
  }
  if (loaded.unreadable.length) return EXIT_COULD_NOT_RUN;
  return findings.length ? EXIT_FINDING : EXIT_CLEAN;
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = {
  load, INVARIANTS, OBSERVATIONS, main, probeInternals, applyDerivation, vocabulary,
  SPEC_NOT_CHECKED_HERE, SPEC_CHECKED_ELSEWHERE
};
