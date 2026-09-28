// tests/role_maps_have_no_prototype.js
// REQUIREMENT: a role membership set must not inherit Object.prototype, so an
//   inherited name can never be read as a role
//
// Run:  node tests/role_maps_have_no_prototype.js
//
// WHY THIS EXISTS. Every app on this platform expresses "which roles may do X"
// as an object literal indexed by the session's role:
//
//     if (!MANAGEMENT_ROLES[session.role]) { ...refuse... }
//
// A plain object literal inherits every key on Object.prototype, so
// `MANAGEMENT_ROLES['constructor']` is TRUTHY. Found in api/rf-auth.js and
// reproduced live 2026-09-24; the shape was then counted at 48 literals across
// 19 files, which is the whole platform rather than one app.
//
// THE REASON THE COUNT MATTERS MORE THAN THE BUG. All 48 were inert, and all 48
// for the SAME distant reason: api/_lib/auth.js's verifySessionToken()
// re-validates `payload.role` against ROLES_BY_APP on every verification, so no
// session carrying an inherited name reaches any of them. One function that 48
// authorisation gates silently depend on, with nothing at either end saying so.
// Narrowing that vocabulary, or adding one caller that builds a session some
// other way, would open all 48 at once.
//
// TWO STRUCTURALLY DIFFERENT METHODS, ON PURPOSE. The cross-domain disciplines
// require independence to mean a different METHOD, not a second reading:
//
//   1. a SOURCE scan over every non-test file in api/, which is the only way to
//      see the 25 maps declared INSIDE functions in api/sd-data.js -- they are
//      never exported and a runtime check cannot reach them;
//   2. a RUNTIME check on every map that IS exported, which is the only way to
//      catch a map that is built correctly in source and mutated afterwards.
//
// Neither subsumes the other and the counts are reported separately.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// git ls-files, not a directory walk: an untracked scratch file in api/ is not
// shipped and must not fail anybody's push, and a tracked file that is not on
// disk is a state worth erroring on rather than silently skipping.
const FILES = execFileSync('git', ['ls-files', 'api/*.js', 'api/_lib/*.js'],
                           { cwd: ROOT, encoding: 'utf8' })
  .split('\n').map((s) => s.trim())
  .filter((s) => s && !s.endsWith('.test.js'));

// The shape being refused: `const SOMETHING_ROLES = { ... };` or `_KEYS`, with
// a bare literal on the right. Anchored to the whole line so a call already
// wrapped in roleSet(...) does not match -- that is the fixed form.
const BARE = /^\s*const ([A-Z][A-Z0-9_]*(?:ROLES|KEYS))\s*=\s*\{[^{}]*\}\s*;\s*$/;
const WRAPPED = /^\s*const ([A-Z][A-Z0-9_]*(?:ROLES|KEYS))\s*=\s*roleSet\((\{[^{}]*\})\)\s*;\s*$/;

section('1. SOURCE -- no bare literal role map anywhere in api/');

const bare = [];
const wrapped = [];
const wrappedBodies = [];   // [site, name, literalSourceText] -- for section 4
for (const rel of FILES) {
  const src = fs.readFileSync(path.join(ROOT, rel), 'utf8');
  src.split('\n').forEach((line, i) => {
    const w = WRAPPED.exec(line);
    if (w) {
      wrapped.push(rel + ':' + (i + 1));
      wrappedBodies.push([rel + ':' + (i + 1), w[1], w[2]]);
    } else if (BARE.test(line)) {
      bare.push(rel + ':' + (i + 1) + '  ' + line.trim().slice(0, 90));
    }
  });
}

test('every role/key membership map in api/ goes through roleSet()', () => {
  assert.deepStrictEqual(bare, [],
    'these are plain object literals and inherit Object.prototype, so an '
    + 'inherited name indexes truthy:\n       ' + bare.join('\n       '));
});

test('and the count is not zero -- this scan is actually finding them', () => {
  // WITHOUT THIS THE ARM ABOVE PASSES ON AN EMPTY LIST. A regex that stopped
  // matching -- a renamed convention, a reformatted declaration, a changed
  // file glob -- produces exactly the same clean output as a clean repo.
  assert.ok(wrapped.length >= 40,
    'only ' + wrapped.length + ' wrapped map(s) found across ' + FILES.length
    + ' file(s). The sweep landed 48. Either the convention changed or this '
    + 'scan has stopped seeing them, and a silent zero reads as a pass.');
});

test('NEGATIVE CONTROL: the pattern really does match a bare literal', () => {
  // Proves the arms above can fail. Without it, a regex with a typo reports a
  // clean repo forever.
  assert.ok(BARE.test('const MANAGEMENT_ROLES = { owner: true, admin: true };'),
    'the bare-literal pattern no longer matches a bare literal');
  assert.ok(!BARE.test('const MANAGEMENT_ROLES = roleSet({ owner: true });'),
    'the bare-literal pattern is ALSO matching the fixed form, so the first '
    + 'arm would fail on correct code');
  assert.ok(WRAPPED.test('const MANAGEMENT_ROLES = roleSet({ owner: true });'),
    'the wrapped pattern no longer matches the fixed form');
});

section('2. RUNTIME -- every EXPORTED map really has a null prototype');

// Deliberately not derived from the source scan above: this is the second
// method, and a map that is built correctly and then mutated is invisible to a
// source read.
const MODULES = ['accounting', 'alf-alerts', 'alf-auth', 'bld-auth', 'dnt-auth',
                 'dnt-bi', 'law-auth', 'ledger', 'leg-auth', 'mech-auth',
                 'rf-auth', 'sd-data', 'sd-sub-data', 'sdn-auth', 'sen-auth',
                 'sen-portal', 'sf-auth', 'sv-auth'];

const INHERITED = ['constructor', 'toString', 'valueOf', 'hasOwnProperty',
                   'isPrototypeOf', 'propertyIsEnumerable', 'toLocaleString',
                   '__defineGetter__', '__lookupGetter__'];

function exportedMaps() {
  const found = [];
  const mods = MODULES.map((m) => ['api/' + m + '.js', require(path.join(ROOT, 'api', m + '.js'))])
    .concat([['api/_lib/auth.js', require(path.join(ROOT, 'api', '_lib', 'auth.js'))],
             ['api/_lib/dental-bi.js', require(path.join(ROOT, 'api', '_lib', 'dental-bi.js'))]]);
  for (const [rel, mod] of mods) {
    for (const k of Object.keys(mod)) {
      const v = mod[k];
      if (!/(ROLES|KEYS|BY_APP)$/.test(k) || !v || typeof v !== 'object') continue;
      // An ARRAY is a different shape: it is read with .indexOf(role), which
      // never consults the prototype chain for a role name. Counted, not
      // checked, so the skip is visible rather than implied.
      if (Array.isArray(v)) { found.push([rel, k, v, true]); continue; }
      found.push([rel, k, v, false]);
    }
  }
  return found;
}

const maps = exportedMaps();
const objectMaps = maps.filter((m) => !m[3]);
const arrayMaps = maps.filter((m) => m[3]);

test('every exported object map has a NULL prototype', () => {
  const bad = objectMaps.filter(([, , v]) => Object.getPrototypeOf(v) !== null)
    .map(([rel, k]) => rel + ':' + k);
  assert.deepStrictEqual(bad, [], 'not null-prototype: ' + bad.join(', '));
});

test('...and not one of them resolves an inherited name', () => {
  const leaks = [];
  for (const [rel, k, v] of objectMaps) {
    for (const n of INHERITED) {
      if (v[n] !== undefined) leaks.push(rel + ':' + k + '[' + n + ']');
    }
  }
  assert.deepStrictEqual(leaks, [], 'inherited names resolve on: ' + leaks.join(', '));
});

test('the runtime population is non-empty and the array skips are COUNTED', () => {
  assert.ok(objectMaps.length >= 10,
    'only ' + objectMaps.length + ' exported object map(s) -- this arm has '
    + 'stopped seeing them, which looks exactly like a clean result');
  console.log('       ' + objectMaps.length + ' object map(s) checked, '
    + arrayMaps.length + ' array(s) skipped (read with .indexOf, not indexed '
    + 'by role name)');
});

test('NEGATIVE CONTROL: a plain literal of the same roles DOES leak', () => {
  const literal = { owner: true, admin: true };
  assert.ok(literal['constructor'],
    'a plain object literal no longer inherits constructor in this runtime -- '
    + 'every arm above is testing nothing, re-derive them');
});

section('3. the shared helper is the ONE place this is decided');

test('roleSet and hasRole are exported from api/_lib/auth.js', () => {
  const a = require(path.join(ROOT, 'api', '_lib', 'auth.js'));
  assert.strictEqual(typeof a.roleSet, 'function');
  assert.strictEqual(typeof a.hasRole, 'function');
});

test('roleSet copies the literal verbatim -- no key added, none dropped', () => {
  // The sweep wrapped 48 literals. The failure mode of a mechanical sweep is a
  // transcription error, so the helper must be a COPY and not a re-listing.
  const a = require(path.join(ROOT, 'api', '_lib', 'auth.js'));
  const lit = { owner: true, admin: false, estimator: true };
  const s = a.roleSet(lit);
  assert.deepStrictEqual(Object.keys(s).sort(), Object.keys(lit).sort());
  for (const k of Object.keys(lit)) assert.strictEqual(s[k], lit[k]);
  assert.strictEqual(Object.getPrototypeOf(s), null);
});

test('hasRole refuses an inherited name, a non-string, and a falsy value', () => {
  const a = require(path.join(ROOT, 'api', '_lib', 'auth.js'));
  const plain = { owner: true, admin: false };   // deliberately a PLAIN literal
  assert.strictEqual(a.hasRole(plain, 'constructor'), false,
    'hasRole must hold even when the map it is given is a plain literal');
  assert.strictEqual(a.hasRole(plain, 'owner'), true);
  assert.strictEqual(a.hasRole(plain, 'admin'), false,
    'a key present but not true is not a role');
  for (const r of [null, undefined, 0, 1, {}, [], true]) {
    assert.strictEqual(a.hasRole(plain, r), false, 'non-string role accepted: ' + String(r));
  }
});

section('4. VALUE SHAPE -- MAP[role] and hasRole(MAP, role) cannot disagree');

// THE DECISION, recorded at the place that enforces it. Two spellings of the
// same check are in use across the platform:
//
//     if (!MANAGEMENT_ROLES[session.role]) { ...refuse... }   // the 48 gates
//     if (!hasRole(MANAGEMENT_ROLES, session.role)) { ...refuse... }
//
// THEY ARE NOT EQUIVALENT. hasRole() requires `=== true`; the bracket form
// grants on any truthy value. A map written `{ owner: 1 }` is granted by one
// spelling and refused by the other -- a difference no reader would expect from
// two spellings of one check. api/_lib/auth-roleset-seam.test.js drives that
// divergence directly and records it as latent, which it is: every map in the
// repo is written `: true` today. Nothing stopped the next one from not being.
//
// hasRole() IS THE CORRECT SEMANTICS -- it refuses an inherited name, refuses a
// non-string role instead of coercing it, and treats `key present but not true`
// as not-a-role. The gates are made consistent with it WITHOUT rewriting the 48
// bracket sites, because roleSet()'s own comment argues against exactly that
// rewrite: the wrapper exists so every `MAP[role]` site is fixed without being
// edited, a 48-site sweep's real failure mode being transcription.
//
// So this arm pins the PRECONDITION that makes the two forms provably identical
// instead: every role map carries `true` and nothing else. Under that invariant
// `!!MAP[role]` and `hasRole(MAP, role)` agree on every input, mixing the two
// spellings is safe, and the day someone writes `owner: 1` this goes red rather
// than opening a silent gap between two lines that read the same.
//
// SCOPE, stated rather than implied: this reads the same single-line
// `const NAME_ROLES = roleSet({...});` declarations section 1 already
// enumerates. The two multi-line maps in api/_lib/auth.js -- ROLES_BY_APP
// (arrays, read with .indexOf) and AUTH_TABLE_BY_APP (table-name strings) --
// are not role membership sets, are never indexed by a session role, and do not
// match that shape, so they are outside this arm by the shape of the
// declaration rather than by a name list that could go stale.

test('the literal body was captured for EVERY wrapped map -- a broken capture '
  + 'group would empty this arm while section 1 stayed green', () => {
    assert.strictEqual(wrappedBodies.length, wrapped.length,
      'section 1 found ' + wrapped.length + ' wrapped map(s) but only '
      + wrappedBodies.length + ' literal(s) were captured');
    assert.ok(wrappedBodies.length >= 40,
      'only ' + wrappedBodies.length + ' literal(s) captured -- a silent zero '
      + 'here reads exactly like a clean repo');
  });

test('every role map carries `true` and nothing else, so the bracket form and '
  + 'hasRole() agree on every input', () => {
    const offenders = [];
    for (const [site, name, text] of wrappedBodies) {
      let obj;
      try {
        // Evaluated, not pattern-matched: the values are read by node's own
        // parser, so this arm cannot be fooled by a spelling a regex for
        // `true` would miss. A body that will not parse is an error, never a
        // pass -- "could not tell" is not "clean".
        obj = (new Function('return (' + text + ');'))();
      } catch (e) {
        offenders.push(site + ' ' + name + ' COULD NOT PARSE: ' + e.message);
        continue;
      }
      for (const k of Object.keys(obj)) {
        if (obj[k] !== true) {
          offenders.push(site + ' ' + name + '.' + k + ' = '
            + JSON.stringify(obj[k]) + ' (' + typeof obj[k] + ')');
        }
      }
    }
    assert.deepStrictEqual(offenders, [],
      'these values are not `true`, so `MAP[role]` and `hasRole(MAP, role)` '
      + 'give different answers for them:\n       ' + offenders.join('\n       '));
    console.log('       ' + wrappedBodies.length + ' of ' + wrapped.length
      + ' role map(s) checked, all values === true');
  });

test('NEGATIVE CONTROL: the divergence is real in this runtime AND the arm '
  + 'above catches it', () => {
    const a = require(path.join(ROOT, 'api', '_lib', 'auth.js'));
    // (i) the premise -- if these ever agree, the arm above is guarding nothing
    const diverging = a.roleSet({ owner: 1 });
    assert.strictEqual(!!diverging.owner, true, 'premise moved: bracket form');
    assert.strictEqual(a.hasRole(diverging, 'owner'), false, 'premise moved: hasRole');
    // (ii) the detection -- the same read the arm above performs, on a planted
    //      value, must flag it; and must NOT flag the correct form
    const bad = (new Function('return ({ owner: 1, billing: true });'))();
    assert.deepStrictEqual(Object.keys(bad).filter((k) => bad[k] !== true), ['owner'],
      'the value read no longer distinguishes a truthy non-true value');
    const good = (new Function('return ({ owner: true, billing: true });'))();
    assert.deepStrictEqual(Object.keys(good).filter((k) => good[k] !== true), [],
      'the value read now flags a correct map, so the arm above would fail on '
      + 'clean code');
    // (iii) the capture -- the line pattern must actually yield the literal
    const m = WRAPPED.exec('  const ALF_MAR_ROLES = roleSet({ owner: 1 });');
    assert.ok(m, 'the wrapped pattern no longer matches a real declaration');
    assert.strictEqual(m[2], '{ owner: 1 }',
      'the literal capture group returned ' + JSON.stringify(m[2]));
  });

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' ROLE-MAP PROTOTYPE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
