// api/_lib/auth-roleset-seam.test.js
// REQUIREMENT: roleSet() and hasRole() hold their contract for EVERY caller,
//   because tools/sairn_seam_check.py cannot read this seam and 18 files depend
//   on it.
//
// Run: SD_AUTH_SECRET=test-secret node api/_lib/auth-roleset-seam.test.js
//
// Plain node:assert, no framework, matching api/'s zero-npm-dependency
// convention.
//
// ── WHY THIS FILE EXISTS, AND IT IS NOT "MORE COVERAGE" ────────────────────
// `python tools/sairn_seam_check.py` reports, for EIGHTEEN files:
//
//   CANNOT TELL api/<x>.js -> api/_lib/auth.js
//     roleSet() makes no direct `literal.field` reads -- it probably copies or
//     destructures its input first, so this tool cannot see what it depends on
//
// It is right. roleSet() does `for (const k of Object.keys(src)) m[k] = src[k]`,
// so there is no `literal.field` read for a static tool to follow. COULD NOT
// TELL IS NOT A PASS, and that tool's own output says so: "a seam this tool
// cannot read still needs a hand-written test". This is that test.
//
// It is written BEFORE changing roleSet()'s membership (the caregiver work),
// on the principle that you do not modify the one function every gate on the
// platform depends on while its seam is unverified.
//
// ── WHAT IS ACTUALLY AT STAKE HERE ────────────────────────────────────────
// A role map built as a PLAIN OBJECT LITERAL is an authorisation bypass for any
// caller whose role is named after an Object.prototype member. `{}.constructor`
// is a function -- truthy -- so `if (!ROLES[role])` PASSES for role
// 'constructor', 'toString', 'valueOf', 'hasOwnProperty' and '__proto__'.
//
// api/_lib/auth.js's own header records this for ROLES_BY_APP and calls it "not
// an authorisation bypass (the app name is signed into the token), but a 500
// where a null session was intended". THAT REASONING IS SPECIFIC TO
// ROLES_BY_APP. For the role maps that gate resources, the role also comes from
// a signed token -- so the same mitigation applies and the same caveat holds:
// the protection is the SIGNATURE, not the map. roleSet() is what makes the map
// safe on its own, so the two controls are independent. Section 5 drives that
// distinction rather than asserting it.
//
// EVERY POSITIVE ARM HERE HAS A NEGATIVE CONTROL that shows a plain literal
// FAILING the same assertion. Without it, a test that passed because the
// property is true of plain objects too would be indistinguishable from one
// that passed because roleSet() works.

'use strict';

const assert = require('assert');
const path = require('path');
const fs = require('fs');

const { roleSet, hasRole, ROLES_BY_APP } = require('./auth');

let passed = 0;
const failures = [];

function test(name, fn) {
  try {
    fn();
    passed += 1;
    console.log('  ok   ' + name);
  } catch (e) {
    failures.push(name + '\n       ' + e.message);
    console.log('  FAIL ' + name);
  }
}

function section(title) {
  console.log('');
  console.log(title);
}

// The names that exist on Object.prototype and therefore read as TRUTHY on a
// plain literal. Derived, not typed out, so a future V8 addition is included
// rather than missed.
const PROTO_NAMES = Object.getOwnPropertyNames(Object.prototype)
  .filter((k) => k !== '__proto__');

section('1. THE BYPASS THIS FUNCTION EXISTS TO CLOSE');

test('a PLAIN LITERAL role map is truthy for every Object.prototype name '
  + '-- the negative control, and it must FAIL', () => {
    const plain = { owner: true, billing: true };
    const leaked = PROTO_NAMES.filter((k) => plain[k]);
    assert.ok(leaked.length > 0,
      'a plain literal no longer leaks prototype members, so the control below '
      + 'proves nothing and this whole file needs rewriting');
    assert.ok(leaked.indexOf('constructor') !== -1,
      'constructor is not truthy on a plain literal -- the premise moved');
  });

test('roleSet() is truthy for NONE of them', () => {
  const set = roleSet({ owner: true, billing: true });
  const leaked = PROTO_NAMES.filter((k) => set[k]);
  assert.deepStrictEqual(leaked, [],
    'roleSet leaked ' + JSON.stringify(leaked) + ' -- a caller whose role is '
    + 'named that would pass `if (!SET[role])`');
});

test('the bracket form -- which is how EVERY gate is written -- refuses a '
  + 'prototype-named role', () => {
    const set = roleSet({ owner: true });
    PROTO_NAMES.forEach((role) => {
      assert.strictEqual(!set[role], true,
        'role ' + JSON.stringify(role) + ' passed `if (!SET[role])`');
    });
  });

test('__proto__ as a ROLE NAME is an own key, not a prototype mutation', () => {
  // On a plain literal `{'__proto__': true}` sets the PROTOTYPE, silently
  // discarding the entry -- so the role would be absent rather than granted.
  // Wrong in the safe direction, and still wrong: the map does not say what
  // its author wrote.
  const set = roleSet({ __proto__: true, owner: true });
  assert.strictEqual(Object.getPrototypeOf(set), null,
    'the prototype was replaced');
  assert.strictEqual(set.owner, true, 'a normal key was lost');
});

section('2. FAITHFUL FORWARDING -- the part the seam check cannot see');

test('every own enumerable key and value is copied exactly', () => {
  const src = { owner: true, billing: true, nursing: false, coordinator: true };
  const set = roleSet(src);
  Object.keys(src).forEach((k) => {
    assert.strictEqual(set[k], src[k], 'key ' + k + ' did not survive');
  });
  assert.deepStrictEqual(Object.keys(set).sort(), Object.keys(src).sort(),
    'the key set changed');
});

test('ARRAY values survive too -- ROLES_BY_APP is app -> roles[], not '
  + 'role -> true', () => {
    const set = roleSet({ sairncare: ['owner', 'nursing'] });
    assert.deepStrictEqual(set.sairncare, ['owner', 'nursing']);
    assert.strictEqual(typeof set.sairncare.indexOf, 'function',
      'the array lost its methods, which is what verifySessionToken calls');
  });

test('INHERITED properties are NOT copied', () => {
  const parent = { inherited_role: true };
  const child = Object.create(parent);
  child.owner = true;
  const set = roleSet(child);
  assert.strictEqual(set.owner, true);
  assert.strictEqual(set.inherited_role, undefined,
    'an inherited key was copied into the role map');
});

test('roleSet(undefined) and roleSet(null) give an EMPTY map, not a throw', () => {
  [undefined, null].forEach((bad) => {
    const set = roleSet(bad);
    assert.strictEqual(Object.keys(set).length, 0);
    assert.strictEqual(set.owner, undefined);
    assert.strictEqual(Object.getPrototypeOf(set), null);
  });
});

test('the returned map is a COPY -- mutating the source afterwards does not '
  + 'change the gate', () => {
    const src = { owner: true };
    const set = roleSet(src);
    src.attacker = true;
    assert.strictEqual(set.attacker, undefined,
      'the role map is live-linked to its source literal');
  });

section('3. hasRole() IS STRICTER THAN THE BRACKET FORM, AND THE GAP IS REAL');

test('hasRole requires === true, so a TRUTHY-BUT-NOT-TRUE value does not grant',
  () => {
    const set = roleSet({ owner: 1, billing: 'yes', nursing: {} });
    ['owner', 'billing', 'nursing'].forEach((r) => {
      assert.strictEqual(hasRole(set, r), false,
        r + ' was granted on a truthy non-true value');
    });
  });

test('BUT THE BRACKET FORM GRANTS ALL THREE -- the divergence, driven rather '
  + 'than assumed', () => {
    // This is not a defect today: every role map in the repo is written with
    // `: true`. It is recorded because the two forms are used interchangeably
    // across 18 files, and a map written with `: 1` would be granted by one and
    // refused by the other -- a difference no reader would expect from two
    // spellings of the same check.
    const set = roleSet({ owner: 1 });
    assert.strictEqual(!!set.owner, true, 'premise moved');
    assert.strictEqual(hasRole(set, 'owner'), false, 'premise moved');
  });

test('hasRole refuses a NON-STRING role instead of coercing it', () => {
  const set = roleSet({ owner: true, 1: true });
  [1, null, undefined, {}, [], true].forEach((role) => {
    assert.strictEqual(hasRole(set, role), false,
      JSON.stringify(role) + ' was accepted as a role name');
  });
  assert.strictEqual(hasRole(set, '1'), true,
    'the string form of a numeric key stopped working');
});

test('hasRole on a null/undefined SET is false, not a throw', () => {
  assert.strictEqual(hasRole(null, 'owner'), false);
  assert.strictEqual(hasRole(undefined, 'owner'), false);
});

test('hasRole refuses prototype names on a PLAIN literal too -- it holds even '
  + 'where roleSet was not used', () => {
    const plain = { owner: true };
    PROTO_NAMES.forEach((role) => {
      assert.strictEqual(hasRole(plain, role), false,
        'hasRole granted ' + role + ' on a plain literal');
    });
  });

section('4. THE REAL MAP, NOT A FIXTURE');

test('ROLES_BY_APP as shipped is null-prototype and leaks nothing', () => {
  assert.strictEqual(Object.getPrototypeOf(ROLES_BY_APP), null);
  const leaked = PROTO_NAMES.filter((k) => ROLES_BY_APP[k]);
  assert.deepStrictEqual(leaked, [],
    'ROLES_BY_APP leaked ' + JSON.stringify(leaked) + ' -- this is the exact '
    + 'case its own header documents, live');
});

test('every ROLES_BY_APP value is an array with a working indexOf -- what '
  + 'verifySessionToken calls on it', () => {
    Object.keys(ROLES_BY_APP).forEach((app) => {
      assert.ok(Array.isArray(ROLES_BY_APP[app]),
        app + ' does not map to an array');
    });
    assert.strictEqual(ROLES_BY_APP['constructor'], undefined,
      'the guard `!ROLES_BY_APP[payload.app]` would pass for app=constructor '
      + 'and then .indexOf would throw a 500');
  });

section('5. THE SEAM ACROSS ALL 18 CALLERS, READ FROM SOURCE');

// The seam check cannot follow roleSet(). These arms check the property it
// would have checked: that a role map indexed by request-derived data is built
// through roleSet() rather than as a bare literal.

const API = path.join(__dirname, '..');

function apiFiles() {
  const out = [];
  [API, path.join(API, '_lib')].forEach((dir) => {
    fs.readdirSync(dir).forEach((n) => {
      if (n.endsWith('.js') && !n.endsWith('.test.js')) {
        out.push(path.join(dir, n));
      }
    });
  });
  return out;
}

test('every ROLES map in api/ is built through roleSet(), with the exceptions '
  + 'NAMED rather than tolerated', () => {
    // KNOWN AND GUARDED, verified by reading the call site rather than assumed:
    //   api/sd-data.js SC_TIER_A_WRITE_ROLES_BY_RESOURCE is a bare literal and
    //   IS indexed by the request's `resource` -- but only inside
    //   `if (SC_TIER_A_WRITE_GATED.indexOf(resource) !== -1)`, so the index is
    //   a member of a real array before the lookup runs and 'constructor'
    //   cannot reach it. LATENT, NOT LIVE. It is one edit away from live: move
    //   or widen that guard and `scTierAWriteRoles('constructor')` returns the
    //   Function constructor, whose .indexOf is undefined -> 500.
    const KNOWN = { 'sd-data.js': ['SC_TIER_A_WRITE_ROLES_BY_RESOURCE'] };
    const bare = [];
    apiFiles().forEach((f) => {
      const src = fs.readFileSync(f, 'utf8');
      const rx = /const\s+([A-Z][A-Z0-9_]*(?:ROLES|ROLES_BY_[A-Z]+))\s*=\s*\{/g;
      let m;
      while ((m = rx.exec(src)) !== null) {
        const base = path.basename(f);
        if ((KNOWN[base] || []).indexOf(m[1]) === -1) {
          bare.push(base + ':' + m[1]);
        }
      }
    });
    assert.deepStrictEqual(bare, [],
      'role map(s) built as a bare object literal: ' + bare.join(', ')
      + ' -- each is truthy for constructor/toString/valueOf. Either wrap in '
      + 'roleSet() or add it to KNOWN here WITH the guard that makes it '
      + 'unreachable, read and stated.');
  });

test('the KNOWN exception still has the guard that makes it unreachable -- so '
  + 'this exemption cannot outlive its reason', () => {
    const src = fs.readFileSync(path.join(API, 'sd-data.js'), 'utf8');
    assert.ok(/SC_TIER_A_WRITE_ROLES_BY_RESOURCE\[resource\]/.test(src),
      'the lookup shape moved; re-read the call site before trusting the '
      + 'exemption above');
    assert.ok(/SC_TIER_A_WRITE_GATED\.indexOf\(resource\)\s*!==\s*-1/.test(src),
      'THE GUARD IS GONE. SC_TIER_A_WRITE_ROLES_BY_RESOURCE is a bare literal '
      + 'indexed by the request resource, and the array-membership check that '
      + 'made that safe is no longer in the file. This exemption is now LIVE, '
      + 'not latent.');
  });

console.log('');
if (failures.length) {
  console.log(failures.length + ' FAILED of ' + (passed + failures.length) + ':');
  failures.forEach((f) => console.log('  - ' + f));
  process.exit(1);
}
console.log(passed + '/' + passed + ' passed.');
console.log('');
console.log('WHAT THIS DOES NOT PROVE: that any individual gate names the RIGHT');
console.log('roles. It proves the seam -- that a role map built through roleSet()');
console.log('behaves as all 18 callers assume, and that no map indexed by');
console.log('request data is a bare literal without a stated guard. Whether');
console.log('ALF_MANAGEMENT_ROLES should contain `caregiver` is a product');
console.log('question and is not decidable here.');
