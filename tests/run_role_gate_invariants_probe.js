// tests/run_role_gate_invariants_probe.js
//
// Run:  node tests/run_role_gate_invariants_probe.js
//
// The control pair for tools/role_gate_invariants.js -- item 78.
//
// CONTROLS_FOR = ['role_gate_invariants.js']
//
// IT REPORTS ZERO VIOLATIONS AGAINST THE REAL TREE, which is the state this
// platform keeps having to correct: a checker nobody has seen fire looks exactly
// like a codebase that is always correct. So every invariant is planted
// separately, and the pair for each proves it stays silent on a correct set.
//
// THE INVARIANTS ARE CHECKED AS FUNCTIONS, not through the whole tool, because
// they are pure -- (role sets) -> violation or null. That is the half worth
// covering exhaustively, and driving it through module loading would test
// `require` rather than the rule. The tool's REPORTING is covered separately by
// running the real thing.
//
// AND THE DENOMINATOR ARM IS THE ONE THAT MATTERS MOST. 61 of 80 possible
// checks cannot be made today, because most auth modules do not export their
// role sets. If that number is ever folded into "no violations" the tool starts
// reporting a clean bill of health over almost nothing -- so an arm asserts the
// output distinguishes them, in words.

'use strict';
const assert = require('assert');
const path = require('path');
const { execFileSync } = require('child_process');

const CONTROLS_FOR = ['role_gate_invariants.js'];
const REPO = path.dirname(__dirname);
const T = require(path.join(REPO, 'tools', 'role_gate_invariants.js'));

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  console.log('  ' + (cond ? 'PASS ' : 'FAIL ') + name +
              (cond ? '' : '\n        ' + String(detail).slice(0, 500)));
  if (cond) pass++; else fail++;
}
const inv = (id) => T.INVARIANTS.filter((i) => i.id === id)[0];

console.log('role_gate_invariants -- the control pair');

// ── A. each invariant fires on its own violation ───────────────────────────
console.log('\n--- A. plant each violation separately ---');
{
  const i3 = inv('I3');
  ok('A1 I3 fires when a provisioner is not management',
    !!i3.check({ provisioning: ['owner', 'clerk'], management: ['owner'] }),
    'silent on a provisioner outside management');
  ok('A2 ...and NAMES the offending role, not just the set',
    /clerk/.test(i3.check({ provisioning: ['owner', 'clerk'], management: ['owner'] })),
    'the message does not say which role');
  ok('A3 THE PAIR: it is silent when provisioning is inside management',
    i3.check({ provisioning: ['owner'], management: ['owner', 'admin'] }) === null);
  // SAIRNcode's real shape: PROVISIONING is `admin`, not `owner`. The invariant
  // must not smuggle in an assumption that the provisioner is called owner --
  // CLAUDE.md records that exact mistake costing a real bug.
  ok('A4 ...including when the provisioner is admin rather than owner',
    i3.check({ provisioning: ['admin'], management: ['admin', 'owner'] }) === null);
}
{
  const i4 = inv('I4');
  ok('A5 I4 fires when a management role cannot sign in',
    !!i4.check({ management: ['owner', 'auditor'], authenticated: ['owner'] }));
  ok('A6 THE PAIR: silent when management can sign in',
    i4.check({ management: ['owner'], authenticated: ['owner', 'clerk'] }) === null);
}
{
  ok('A7 I5a fires on an empty MANAGEMENT set', !!inv('I5a').check({ management: [] }));
  ok('A8 I5b fires on an empty AUTHENTICATED set', !!inv('I5b').check({ authenticated: [] }));
  ok('A9 I5c fires on an empty PROVISIONING set -- no way back into the app',
    !!inv('I5c').check({ provisioning: [] }));
  ok('A10 THE PAIR: a non-empty set is silent',
    inv('I5a').check({ management: ['owner'] }) === null);
}

// ── B. the observation reports BOTH ways, which is its whole purpose ───────
console.log('\n--- B. the observation is not an invariant ---');
{
  const o1 = T.OBSERVATIONS[0];
  ok('B1 it holds when management is inside broad-read',
    o1.holds({ management: ['owner', 'admin'], broadRead: ['owner', 'admin', 'estimator'] }));
  ok('B2 and it STOPS holding when a management role is not a broad reader',
    !o1.holds({ management: ['owner', 'auditor'], broadRead: ['owner', 'estimator'] }));
  ok('B3 the false message tells the reader the 22 sites changed MEANING',
    /answering a different question/.test(o1.whenFalse), o1.whenFalse);
  ok('B4 and the true message says both terms must be KEPT, not simplified',
    /redundant/.test(o1.whenTrue) && /must be kept/.test(o1.whenTrue), o1.whenTrue);
}

// ── C. the real tool, on the real tree ─────────────────────────────────────
console.log('\n--- C. the real run ---');
{
  let out = '', code = 0;
  try {
    out = execFileSync(process.execPath,
      [path.join(REPO, 'tools', 'role_gate_invariants.js')], { encoding: 'utf8' });
  } catch (e) { out = (e.stdout || '') + (e.stderr || ''); code = e.status; }
  ok('C1 it exits 0 against the tree as it stands', code === 0, 'rc=' + code);
  ok('C2 it reports how many checks it actually RAN', /invariant checks RUN\s*:\s*\d+/.test(out), out);
  ok('C3 AND how many it could NOT make -- the denominator', /NOT CHECKABLE\s*:\s*\d+/.test(out), out);
  ok('C4 ...saying in words that unspecified is not "no violations"',
    /this is not "no violations"/.test(out), out);
  ok('C5 and the clean line refuses to generalise past what it checked',
    /not about the \d+ that could not be made/.test(out), out);
  ok('C6 the SAIRNroofing observation is surfaced, not buried',
    /rf-auth\.js O1/.test(out), out);
  ok('C7 it names the spec it is checking against',
    /docs\/spec\/RoleGates\.tla/.test(out), out);
}

// ── D. a module that will not load is could-not-run, not clean ────────────
console.log('\n--- D. could-not-load is a third state ---');
{
  // load() is driven directly: making a real api/*-auth.js unloadable would
  // mean mutating the tree, and the branch under test is what load() does with
  // a require that throws -- which is the same branch either way.
  const loaded = T.load();
  ok('D1 load() reports unreadable modules as their own list',
    Array.isArray(loaded.unreadable), JSON.stringify(Object.keys(loaded)));
  ok('D2 and none are unreadable today -- so C1\'s exit 0 is a real 0',
    loaded.unreadable.length === 0, JSON.stringify(loaded.unreadable));
  const src = require('fs').readFileSync(
    path.join(REPO, 'tools', 'role_gate_invariants.js'), 'utf8');
  ok('D3 an unreadable module forces exit 2, not exit 0',
    /if \(loaded\.unreadable\.length\) return EXIT_COULD_NOT_RUN;/.test(src), 'the guard moved');
  ok('D4 and the source says a module that will not load is not one with no roles',
    /not a module with no roles/i.test(src), 'the reason is no longer stated');
}

console.log('');
if (fail) {
  console.log('role_gate_invariants: ' + fail + ' ARM(S) FAILED');
  process.exit(1);
}
console.log('role_gate_invariants: all ' + pass + ' arms pass');
