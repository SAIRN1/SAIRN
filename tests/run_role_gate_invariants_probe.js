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
// AND THE DENOMINATOR ARM IS THE ONE THAT MATTERS MOST. ~~61 of 80 possible
// checks cannot be made today, because most auth modules do not export their
// role sets.~~ **2026-09-14: 24, after the tool learned to read a module's
// internal constants and to derive AUTHENTICATED_ROLES from the app role
// vocabulary.** The old sentence is struck rather than deleted so the scale of
// what changed is visible. If that number is ever folded into "no violations"
// the tool starts reporting a clean bill of health over almost nothing -- so an
// arm asserts the output distinguishes them, in words.
//
// **THE NUMBER ITSELF IS NOT ASSERTED ANYWHERE IN THIS FILE, ON PURPOSE.** An
// arm pinned to "24" fails the day somebody legitimately adds an auth module,
// which trains people to edit the test. The arms assert the DISTINCTIONS hold
// -- run versus not-checkable, and which provenance each check rested on.

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

// ── E. the internal probe reads VALUES, and the comment trap proves why ────
console.log('\n--- E. reading a module\'s internal constants ---');
{
  const A = path.join(REPO, 'api');
  const alf = T.probeInternals(path.join(A, 'alf-auth.js'));
  ok('E1 it reads a constant the module never exports',
    Array.isArray(alf.PROVISIONING_ROLES) && alf.PROVISIONING_ROLES.indexOf('owner') !== -1,
    JSON.stringify(alf));
  ok('E2 and the object form too, not only the array form',
    alf.MANAGEMENT_ROLES && alf.MANAGEMENT_ROLES.owner === true, JSON.stringify(alf));
  ok('E3 it reads APP, which is the whole key into the role vocabulary',
    alf.APP === 'sairncare', String(alf.APP));
  // THE ARM THAT JUSTIFIES EXECUTING INSTEAD OF PARSING. sb-auth.js contains
  // the TEXT "MANAGEMENT_ROLES" inside a comment saying the app has no such
  // concept. A grep-based reader finds that token; this one must not.
  const sbSrc = require('fs').readFileSync(path.join(A, 'sb-auth.js'), 'utf8');
  ok('E4 the comment trap is still in sb-auth.js -- if it is gone this arm proves nothing',
    /no MANAGEMENT_ROLES concept/.test(sbSrc), 'the trap moved; re-point this arm');
  const sb = T.probeInternals(path.join(A, 'sb-auth.js'));
  ok('E5 ...and a token that appears ONLY in a comment reads as ABSENT, not as a set',
    sb.MANAGEMENT_ROLES === undefined, JSON.stringify(sb.MANAGEMENT_ROLES));
  ok('E6 a module with no role constants at all comes back empty, not thrown',
    T.probeInternals(path.join(A, 'sd-sub-auth.js')).PROVISIONING_ROLES === undefined, '');
}

// ── F. I6 is a real control: it fires, and its failure WITHDRAWS ───────────
console.log('\n--- F. the derivation is licensed, and can be un-licensed ---');
{
  const mk = (auth, app) => ({
    app: app, authenticated: auth,
    prov: { authenticated: auth ? 'internal' : 'absent' }
  });
  const VOCAB = { appx: ['owner', 'clerk'], appy: ['owner', 'clerk'] };

  const good = { vocabulary: VOCAB, apps: { a: mk(['owner', 'clerk'], 'appx'), b: mk(null, 'appy') } };
  const g = T.applyDerivation(good);
  ok('F1 I6 is silent when a stated AUTHENTICATED_ROLES equals the vocabulary',
    g.violations.length === 0 && g.licensed, JSON.stringify(g));
  ok('F2 ...and the derivation then fills in the module that states nothing',
    good.apps.b.authenticated.join() === 'owner,clerk' &&
    good.apps.b.prov.authenticated === 'derived', JSON.stringify(good.apps.b));

  const bad = { vocabulary: VOCAB, apps: { a: mk(['owner'], 'appx'), b: mk(null, 'appy') } };
  const f = T.applyDerivation(bad);
  ok('F3 I6 FIRES when a stated set is not the vocabulary',
    f.violations.length === 1 && /violates I6/.test(f.violations[0]), JSON.stringify(f));
  ok('F4 ...and the whole derivation is WITHDRAWN, not just that one app',
    !f.licensed && f.derived.length === 0 && bad.apps.b.authenticated === null,
    JSON.stringify(bad.apps.b));

  // A CONTROL WITH NOTHING TO CONTROL IS NOT A PASSING CONTROL.
  const vac = { vocabulary: VOCAB, apps: { b: mk(null, 'appy') } };
  const v = T.applyDerivation(vac);
  ok('F5 no module stating AUTHENTICATED_ROLES means VACUOUS, not licensed',
    !v.licensed && v.stated === 0 && v.violations.length === 0, JSON.stringify(v));
  ok('F6 ...so nothing is derived off an unchecked assumption',
    vac.apps.b.authenticated === null, JSON.stringify(vac.apps.b));

  // A PROBE THAT FAILED MUST NOT BE BACKFILLED BY A DERIVATION. The whole
  // point of the could-not-probe state is that this tool does not know.
  const unp = {
    vocabulary: VOCAB,
    apps: {
      a: mk(['owner', 'clerk'], 'appx'),
      b: { app: 'appy', authenticated: null, prov: { authenticated: 'could-not-probe' } }
    }
  };
  T.applyDerivation(unp);
  ok('F7 a could-not-probe set is NOT quietly filled in by the derivation',
    unp.apps.b.authenticated === null &&
    unp.apps.b.prov.authenticated === 'could-not-probe', JSON.stringify(unp.apps.b));

  ok('F8 the real tree licenses it today -- if this flips, the derived count is 0',
    T.applyDerivation(T.load()).licensed, 'I6 no longer licenses the derivation');
}

// ── G. the three coverage numbers are never fused ──────────────────────────
console.log('\n--- G. coverage that grew because evidence got thinner ---');
{
  let out = '';
  try {
    out = execFileSync(process.execPath,
      [path.join(REPO, 'tools', 'role_gate_invariants.js'), '--json'],
      { encoding: 'utf8' });
  } catch (e) { out = (e.stdout || '') + (e.stderr || ''); }
  const j = JSON.parse(out);
  const b = j.byProvenance;
  ok('G1 --json reports the three provenances separately',
    b && typeof b.exported === 'number' && typeof b.internal === 'number' &&
    typeof b.derived === 'number', out.slice(0, 300));
  ok('G2 they sum to the headline count -- no check is uncounted or double-counted',
    b.exported + b.internal + b.derived === j.checks,
    JSON.stringify(b) + ' vs ' + j.checks);
  ok('G3 the internal probe actually bought coverage the exports could not',
    b.internal > 0, JSON.stringify(b));
  ok('G4 and so did the derivation', b.derived > 0, JSON.stringify(b));

  const txt = execFileSync(process.execPath,
    [path.join(REPO, 'tools', 'role_gate_invariants.js')], { encoding: 'utf8' });
  ok('G5 the human output prints the breakdown, not just a total',
    /WEAKEST evidence/.test(txt) && /derived\s+\d+/.test(txt), txt.slice(0, 400));
  ok('G6 ...and says what licenses the derived ones',
    /I6 CONTROL/.test(txt), txt.slice(0, 400));
  ok('G7 could-not-probe is stated as different from having no such roles',
    /which is NOT the same as those apps having no such roles/.test(
      require('fs').readFileSync(
        path.join(REPO, 'tools', 'role_gate_invariants.js'), 'utf8')),
    'the distinction is no longer stated in the output');
}

// ── H. what remains is broken down by WHOSE gap it is ─────────────────────
console.log('\n--- H. the remainder is not one undifferentiated pile ---');
{
  const VOCAB = { appx: ['owner'] };
  const noKey = {
    vocabulary: VOCAB,
    apps: {
      a: { app: 'appx', authenticated: ['owner'], prov: { authenticated: 'internal' } },
      b: { app: null, authenticated: null, prov: { authenticated: 'absent' } }
    }
  };
  T.applyDerivation(noKey);
  ok('H1 a module with no `const APP` is marked no-app-key, not plain absent',
    noKey.apps.b.prov.authenticated === 'no-app-key', JSON.stringify(noKey.apps.b));

  const txt = execFileSync(process.execPath,
    [path.join(REPO, 'tools', 'role_gate_invariants.js')], { encoding: 'utf8' });
  ok('H2 the output separates "the constant is not there" from work anyone can do',
    /absent\s+\d+\s+the constant is not there/.test(txt), txt.slice(0, 900));
  // H3/H4 USED TO PIN sd-auth.js AND sd-sub-auth.js AS THE no-app-key CASES.
  // They gained `const APP` on 2026-09-14 and the state emptied, so those two
  // arms were DROPPED rather than weakened -- which is what the note on the old
  // H4 said to do. The code path is still live and still needs a control: H1
  // above drives it directly, which is a better test than a fact about the tree
  // that anyone can close. What is asserted here instead is that the remainder
  // is still EXPLAINED rather than presented as one undifferentiated pile.
  ok('H3 the output says what `absent` means -- a fact about the app, not a gap here',
    /absent\s+\d+\s+the constant is not there -- a fact about the app/.test(txt),
    txt.slice(0, 900));
  ok('H4 no no-app-key remains in the tree today -- if this fails, a module lost '
    + 'its `const APP`',
    !/no-app-key/.test(txt),
    'a module stopped declaring const APP; find it in the UNSPECIFIED list');
  // NO WIDTH SPECIFIERS. console.log is not printf; '%-16s' prints literally and
  // appends the argument, which shipped twice in this file's own output.
  ok('H5 no printf width specifier survives in the tool\'s output strings',
    !/%-\d|%\d+d/.test(require('fs').readFileSync(
      path.join(REPO, 'tools', 'role_gate_invariants.js'), 'utf8')
      .split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n')),
    'a %-Nd or %Ns is back in a non-comment line');
}

// ── I. the two halves cannot drift apart unnoticed ────────────────────────
// The tool's own header says a spec that drifts from the code it describes is
// worse than none. Nothing enforced that until now: I6 was added to both halves
// by hand, and the next one could as easily go into one.
console.log('\n--- I. the spec and the checker are held together ---');
{
  const tla = require('fs').readFileSync(
    path.join(REPO, 'docs', 'spec', 'RoleGates.tla'), 'utf8');

  const cited = Array.from(new Set(
    T.INVARIANTS.map((i) => i.spec).concat(Object.keys(T.SPEC_CHECKED_ELSEWHERE))));
  const undefinedInSpec = cited.filter(
    (n) => !new RegExp('^' + n + '\\s*==', 'm').test(tla));
  ok('I1 every spec name the checker cites is actually DEFINED in the .tla',
    undefinedInSpec.length === 0, JSON.stringify(undefinedInSpec));

  // The Safety conjunction is the spec's own statement of what must hold.
  // Taken line by line and STOPPED at the first line that is not a conjunct --
  // splitting on a blank line ran straight into the transitions section and
  // collected `UNCHANGED` and every variable name as though they were
  // invariants, which would have made I3 unpassable for the wrong reason.
  const conjuncts = [];
  const after = (tla.split(/^Safety\s*==/m)[1] || '').split('\n');
  for (const line of after) {
    const m = line.match(/^\s+\/\\\s*(\w+)\s*$/);
    if (m) { conjuncts.push(m[1]); continue; }
    if (line.trim() === '') continue;
    break;
  }
  ok('I2 the Safety conjunction was actually parsed -- an empty list proves nothing',
    conjuncts.length >= 4, JSON.stringify(conjuncts));

  const unaccounted = conjuncts.filter(
    (c) => cited.indexOf(c) === -1 && !(c in T.SPEC_NOT_CHECKED_HERE));
  ok('I3 every Safety conjunct is either checked here or DECLARED as not checked',
    unaccounted.length === 0,
    'unaccounted: ' + JSON.stringify(unaccounted) +
    ' -- add an invariant, or a reason to SPEC_NOT_CHECKED_HERE');

  ok('I4 ...and nothing is declared un-checkable that is in fact being checked',
    Object.keys(T.SPEC_NOT_CHECKED_HERE).every((k) => cited.indexOf(k) === -1),
    JSON.stringify(Object.keys(T.SPEC_NOT_CHECKED_HERE).filter(
      (k) => cited.indexOf(k) !== -1)));

  // ── CC's FINDING 4: an invariant never EVALUATED appears in no count ─────
  // "N not checkable" is about role sets that could not be READ. I1 and I2 are
  // not evaluated for ANY app, which no number here ever reflected.
  const notHere = Object.keys(T.SPEC_NOT_CHECKED_HERE).filter((k) => k !== 'TypeOK');
  ok('I6 every not-evaluated invariant names WHERE it is actually proven',
    notHere.length > 0 && notHere.every(
      (k) => T.SPEC_NOT_CHECKED_HERE[k].why && T.SPEC_NOT_CHECKED_HERE[k].proven_by),
    JSON.stringify(T.SPEC_NOT_CHECKED_HERE));
  // Captured here rather than reusing section H's `txt`, which is block-scoped
  // to H -- the first version of these arms referenced it and died with a
  // ReferenceError, which is a probe that tested nothing rather than a pass.
  const runOut = execFileSync(process.execPath,
    [path.join(REPO, 'tools', 'role_gate_invariants.js')], { encoding: 'utf8' });
  ok('I7 ...and the RUN prints them, so the gap is not only in the source',
    /DOES NOT EVALUATE/.test(runOut) && /proven by:/.test(runOut), runOut.slice(-900));
  ok('I8 ...naming AppIsolation and DeactivationBinds specifically',
    /AppIsolation/.test(runOut) && /DeactivationBinds/.test(runOut), runOut.slice(-900));
  ok('I9 ...and it says outright they are NOT part of the counts above',
    /NOT part[\s\S]{0,120}counts above/.test(runOut), runOut.slice(-900));
  ok('I10 the header no longer claims every invariant unqualified',
    /every invariant ~~over its whole role set~~ THAT/.test(
      require('fs').readFileSync(
        path.join(REPO, 'tools', 'role_gate_invariants.js'), 'utf8')),
    'the unqualified "every invariant" claim is back');

  ok('I5 I6 in particular reached BOTH halves',
    /AuthenticatedMatchesVocabulary\s*==/m.test(tla) &&
    conjuncts.indexOf('AuthenticatedMatchesVocabulary') !== -1,
    'I6 is in the checker but not in the spec Safety conjunction: ' +
    JSON.stringify(conjuncts));
}

console.log('');
if (fail) {
  console.log('role_gate_invariants: ' + fail + ' ARM(S) FAILED');
  process.exit(1);
}
console.log('role_gate_invariants: all ' + pass + ' arms pass');
