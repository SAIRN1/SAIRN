// api/_lib/employee-lifecycle-wiring.test.js
// A SOURCE-LEVEL test over every auth endpoint on the platform.
//
// Run:  node --test api/_lib/employee-lifecycle-wiring.test.js
//
// employee-lifecycle.test.js proves the shared rules are right. This file
// proves each endpoint is actually wired to them, and — the part that matters
// most — that the PROVISIONING_ROLES each endpoint hands the shared helper are
// THE SAME ROLES ITS OWN `setup` GATE ENFORCES.
//
// That check exists because of a specific recorded failure. CLAUDE.md:
//
//   "Read the app's own PROVISIONING_ROLES — SAIRNcode's is `admin`, not
//    `owner`. A guard that hardcodes `owner` passes SAIRNcode clean forever
//    while checking nothing."
//
// The shared helper takes the roles as a parameter precisely so each app can
// pass its own. That design is worth nothing if an app passes the wrong list,
// and the wrong list is invisible in review — it looks like every other app's.
// So the roles are re-derived here FROM THE SETUP GATE'S OWN SOURCE and
// compared. Three of the nine are genuinely not owner-only:
//
//   SAIRNgrounds  owner, superintendent
//   SAIRNbiz      owner, hr
//   SAIRNscape    owner, crew_lead
//
// This is a static read of the files. It cannot prove the handler behaves —
// employee-lifecycle.test.js does that — but it does prove the handler EXISTS
// and is reachable, which is the failure mode a behavioural test cannot see:
// a correct gate that no code path calls reads as safe in review and enforces
// nothing.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const API = path.join(__dirname, '..');
const read = (f) => fs.readFileSync(path.join(API, f), 'utf8');

// Endpoints migrated onto api/_lib/employee-lifecycle.js.
const WIRED = [
  { file: 'sen-auth.js', app: 'sairnsenior', table: 'sairnsenior_employee_auth' },
  { file: 'alf-auth.js', app: 'sairncare', table: 'sairncare_employee_auth' },
  { file: 'bld-auth.js', app: 'sairnbuild', table: 'sairnbuild_employee_auth' },
  { file: 'sdn-auth.js', app: 'sairndesign', table: 'sairndesign_employee_auth' },
  { file: 'grd-auth.js', app: 'sairngrounds', table: 'grd_employee_auth' },
  { file: 'sb-auth.js', app: 'sairnbiz', table: 'sb_employee_auth' },
  { file: 'scp-auth.js', app: 'sairnscape', table: 'scp_employee_auth' },
  { file: 'law-auth.js', app: 'sairnlaw', table: 'sairnlaw_employee_auth' },
  { file: 'leg-auth.js', app: 'sairnlegacy', table: 'sairnlegacy_employee_auth' }
];

// The five that already had their own hand-written set_active before the shared
// helper existed. Deliberately NOT migrated — they are live, on the auth path,
// and a refactor whose only benefit is tidiness is not worth a locked-out
// customer. Listed so "why is this one different" has an answer on file, and so
// the count below fails if somebody migrates one without updating this.
const PRE_EXISTING = ['sd-auth.js', 'sc-auth.js', 'dnt-auth.js', 'mech-auth.js', 'rf-auth.js'];

// Endpoints that still have no way to deactivate a credential at all. This list
// is the remaining work, written down rather than described, so it can only
// shrink deliberately.
// Empty as of 2026-09-03: all nine are wired. Kept rather than deleted so the
// accounting assertion below still has three lists to cover every endpoint, and
// so a NEW app that ships credentials without a deactivation path has an
// obvious place to be recorded instead of being quietly missed.
const STILL_OPEN = [];

// Pull the roles a `setup` gate actually enforces, out of its own source.
// Handles both shapes in the repo: `caller.role !== 'owner'` and
// `(caller.role !== 'owner' && caller.role !== 'superintendent')`.
function rolesFromSetupGate(src) {
  const at = src.indexOf("action === 'setup'");
  assert.ok(at > 0, 'no setup gate found');
  const window = src.slice(at, at + 600);
  const m = /if \(!caller \|\|([\s\S]*?)\) \{/.exec(window);
  assert.ok(m, 'could not read the setup gate condition');
  const roles = [];
  const re = /caller\.role !== '([a-z_]+)'/g;
  let g;
  while ((g = re.exec(m[1])) !== null) roles.push(g[1]);
  assert.ok(roles.length > 0, 'the setup gate names no roles');
  return roles.sort();
}

function declaredProvisioningRoles(src) {
  const m = /const PROVISIONING_ROLES = \[([^\]]*)\]/.exec(src);
  assert.ok(m, 'no PROVISIONING_ROLES constant');
  return m[1].split(',').map((x) => x.trim().replace(/^'|'$/g, '')).filter(Boolean).sort();
}

// ── EVERY WIRED ENDPOINT IS ACTUALLY WIRED ─────────────────────────────────

WIRED.forEach((e) => {
  test(e.file + ' requires the shared lifecycle helper', () => {
    assert.match(read(e.file), /require\('\.\/_lib\/employee-lifecycle'\)/);
  });

  test(e.file + ' declares set_active AND roster as accepted actions', () => {
    // Two shapes exist in this repo and both are real: a `const ACTIONS = [...]`
    // list (the later endpoints) and an inline
    // `['bootstrap','login','setup'].indexOf(action) === -1` guard (the earlier
    // ones). Either is fine; what is NOT fine is a handler the validator
    // refuses before it is ever reached, which is a gate that exists and
    // enforces nothing — the exact failure this whole file is here to catch.
    const src = read(e.file);
    const m = /const ACTIONS = \[([\s\S]*?)\]/.exec(src) ||
              /if \(\[([^\]]*)\]\.indexOf\(action\) === -1\)/.exec(src);
    assert.ok(m, 'no action allow-list of either known shape');
    ["'set_active'", "'roster'"].forEach((a) => {
      assert.ok(m[1].indexOf(a) !== -1,
        a + ' is handled but not accepted — the action validator refuses it first');
    });
  });

  test(e.file + ' does not hand-write a 400 message that omits an accepted action', () => {
    // Some endpoints GENERATE the message from the list ("one of: " +
    // ACTIONS.join) and can never drift. The older ones hand-write it, and a
    // hand-written list beside a real one is exactly how `employee_profile`
    // ended up a valid resource missing from api/sd-data.js's own error string.
    // Only the hand-written shape is checked; the generated one has nothing to
    // check.
    const src = read(e.file);
    const m = /message: "action must be ([^"]*)"/.exec(src);
    if (!m) return;
    const list = /const ACTIONS = \[([\s\S]*?)\]/.exec(src) ||
                 /if \(\[([^\]]*)\]\.indexOf\(action\) === -1\)/.exec(src);
    const names = (list[1].match(/'([a-z_]+)'/g) || []).map((x) => x.replace(/'/g, ''));
    names.forEach((n) => {
      assert.ok(m[1].indexOf(n) !== -1,
        'the 400 message does not mention "' + n + '", which the validator accepts — ' +
        'a caller reading it would not know the action exists');
    });
  });

  test(e.file + ' has a set_active handler that CALLS the shared helper', () => {
    // The failure this catches: a gate that exists and is never reached.
    const src = read(e.file);
    const at = src.indexOf("action === 'set_active'");
    assert.ok(at > 0, 'no set_active handler');
    const body = src.slice(at, at + 900);
    assert.match(body, /lifecycle\.setActive\(/, 'the handler does not call the shared helper');
  });

  test(e.file + ' routes its roster through the shared helper too', () => {
    const src = read(e.file);
    const at = src.indexOf("action === 'roster'");
    assert.ok(at > 0, 'no roster handler');
    assert.match(src.slice(at, at + 900), /lifecycle\.roster\(/);
  });

  test(e.file + ' passes ITS OWN table and licence to the helper', () => {
    const src = read(e.file);
    assert.match(src, new RegExp("const TABLE = '" + e.table + "'"),
      'the table constant is not this app\'s');
    const at = src.indexOf("action === 'set_active'");
    const body = src.slice(at, at + 900);
    assert.match(body, /table: TABLE/);
    assert.match(body, /licHash: licHash/);
  });

  test(e.file + ' scopes the session token to ITS OWN app id', () => {
    // Without expectedApp, an `owner` token from a different app passes --
    // 'owner' exists in nearly every app's role list. Both handlers must scope.
    const src = read(e.file);
    assert.match(src, new RegExp("const APP = '" + e.app + "'"));
    ["action === 'set_active'", "action === 'roster'"].forEach((k) => {
      const at = src.indexOf(k);
      const body = src.slice(at, at + 400);
      assert.match(body, /verifySessionToken\(tokenFromRequest\(req\), licHash, APP\)/,
        k + ' does not scope the token to this app');
    });
  });

  // ── THE ONE THAT EARNS ITS KEEP ──────────────────────────────────────────
  test(e.file + ': PROVISIONING_ROLES equals what its own setup gate enforces', () => {
    const src = read(e.file);
    assert.deepStrictEqual(
      declaredProvisioningRoles(src), rolesFromSetupGate(src),
      'the roles handed to the shared helper disagree with the roles this app ' +
      'actually lets provision. One of the two is wrong, and if it is the ' +
      'helper\'s list then deactivation is gated on a role that does not exist ' +
      'here — or worse, open to one that should not have it.'
    );
  });

  test(e.file + ' passes a human label naming those same roles', () => {
    const src = read(e.file);
    const m = /const PROVISIONING_LABEL = '([^']*)'/.exec(src);
    assert.ok(m, 'no PROVISIONING_LABEL');
    const label = m[1].toLowerCase();
    declaredProvisioningRoles(src).forEach((r) => {
      // crew_lead -> "crew lead"; the label is prose, the role is a token.
      const word = r.replace(/_/g, ' ');
      assert.ok(label.indexOf(word) !== -1,
        'the refusal message says "' + m[1] + '" but the role list includes ' + r +
        ' — a customer would be told to ask a role that cannot help them');
    });
  });
});

// ── THE ROSTER CHANGE HAS A MATCHING CLIENT FIX ────────────────────────────
// The roster action now returns INACTIVE rows so an owner can reactivate
// somebody. Every client that builds a picker from it must filter them back
// out, or a deactivated employee silently becomes assignable again on a
// dropdown that looks completely normal. This is the cross-file agreement the
// endpoint change depends on, so it is asserted rather than trusted.
// `rawMapSites` is the number of places each file may still map the RAW cache,
// with the reason. Anything above that count is a picker somebody forgot.
//
// This assertion has already earned its keep: the first version of this change
// converted one picker per app and shipped. This test found FIVE more — two in
// SAIRNsenior, three in SAIRNcare — including the CONTROLLED-SUBSTANCE WITNESS
// selector, where a "second signature" from somebody who no longer works there
// is not a witness at all.
const CLIENTS = [
  { file: 'sairnsenior.html', cache: '_senRoster', helper: 'senAssignable', rawMapSites: 0, why: null },
  { file: 'sairncare.html', cache: '_alfRoster', helper: 'alfAssignable', rawMapSites: 1,
    why: 'the Security panel\'s accounts table, which MUST show deactivated rows — that is the point of it' },
  { file: 'sairnbuild.html', cache: '_bldRoster', helper: 'bldAssignable', rawMapSites: 0, why: null },
  { file: 'sairndesign.html', cache: '_sdnRoster', helper: 'sdnAssignable', rawMapSites: 0, why: null }
];

CLIENTS.forEach((c) => {
  test(c.file + ' maps the raw roster only where it deliberately should', () => {
    const src = fs.readFileSync(path.join(API, '..', c.file), 'utf8');
    const raw = new RegExp('\\(?' + c.cache + '(\\s*\\|\\|\\s*\\[\\])?\\)?\\.map\\(', 'g');
    const hits = (src.match(raw) || []).length;
    assert.strictEqual(hits, c.rawMapSites,
      hits > c.rawMapSites
        ? c.cache + ' is mapped directly ' + hits + ' times but only ' + c.rawMapSites +
          ' site(s) may be — a picker will now list deactivated employees' +
          (c.why ? ' (the allowed one is ' + c.why + ')' : '')
        : 'fewer raw sites than expected — if a deliberate one was converted, ' +
          'lower rawMapSites here and say why');
  });

  test(c.file + ' routes its pickers through ' + c.helper + '()', () => {
    const src = fs.readFileSync(path.join(API, '..', c.file), 'utf8');
    assert.match(src, new RegExp('function ' + c.helper + '\\('),
      'no ' + c.helper + '() helper — the roster change has no client half');
    assert.match(src, new RegExp(c.helper + '\\(\\)\\.map\\('),
      c.helper + '() is defined but nothing uses it');
    // One helper, not a filter copied to each call site: a filter that must be
    // repeated is a filter that will be half-applied.
    assert.match(src, /active\s*!==\s*false/);
  });

  test(c.file + ' still resolves a DEACTIVATED person\'s name on old records', () => {
    // The other half, and the one an over-eager filter breaks: a departed
    // caregiver must stop being assignable but must NOT turn into a bare id on
    // every visit note they are already attached to.
    const src = fs.readFileSync(path.join(API, '..', c.file), 'utf8');
    const at = src.indexOf(c.cache + '){var m=' + c.cache);
    const alt = src.indexOf('if(' + c.cache + '){var m=');
    assert.ok(at > 0 || alt > 0,
      'the name-resolution lookup was not found — if it was changed to filter ' +
      'on active, historical records now show raw employee ids');
  });
});

// ── THE REMAINING WORK IS WRITTEN DOWN, NOT DESCRIBED ──────────────────────

// ── EVERY WIRED ENDPOINT HAS A CLIENT THAT CALLS IT ────────────────────────
// A set_active endpoint nobody can reach from the app is dormant code: the
// customer still cannot deactivate anyone, and the gap looks closed in a
// tracking table. Each entry names the function that must exist.
const UI = [
  { file: 'sairnsenior.html', fn: 'senSetActive', render: 'senRenderAccess' },
  // SAIRNcare is the one that does NOT get its own render function: its
  // Security panel already had an accounts table listing `active`, built
  // before set_active existed. Only the button was missing, so rSecurity()
  // stayed the renderer rather than growing a near-duplicate beside it.
  { file: 'sairncare.html', fn: 'alfSetActive', render: 'rSecurity' },
  { file: 'sairnbuild.html', fn: 'bldSetActive', render: 'bldRenderAccess' },
  { file: 'sairndesign.html', fn: 'sdnSetActive', render: 'sdnRenderAccess' },
  { file: 'sairnlaw.html', fn: 'lawSetActive', render: 'lawRenderAccess' },
  { file: 'sairnlegacy.html', fn: 'legSetActive', render: 'legRenderAccess' },
  { file: 'sairnbiz.html', fn: 'sbSetActive', render: 'sbRenderAccess' },
  { file: 'sairngrounds.html', fn: 'grdSetActive', render: 'grdRenderAccess' },
  { file: 'sairnscape.html', fn: 'scpSetActive', render: 'scpRenderAccess' }
];

// Empty as of 2026-09-03: all nine wired endpoints have a screen.
//
// CORRECTION KEPT ON PURPOSE. This list previously held sairnscape.html with
// the reason "a marketing-page-plus-app single file driven by showPage(), with
// no panel/nav convention to slot a credential screen into". THAT WAS WRONG.
// SAIRNscape has a complete panel/nav convention -- `scp-panel`, `scp-sb-*`,
// `scpNav()` -- and the screen took the same shape as the other eight.
//
// The mistake is worth recording because of HOW it was made: the conclusion
// came from grepping `class="panel"` and `function nav(` and treating two
// misses as proof of absence. Every id in that file is prefixed `scp-`. A
// negative search result is only as strong as the search, and "I could not
// find it" was written down as "it does not exist" -- the same shape as the
// `sairn-code-guardian` claim CLAUDE.md corrects twice.
//
// Kept rather than deleted so a future app that ships credentials without a
// screen has an obvious place to be recorded instead of being quietly missed.
const UI_NOT_BUILT = [];

UI.forEach((u) => {
  test(u.file + ' has a ' + u.fn + '() that calls set_active', () => {
    const src = fs.readFileSync(path.join(API, '..', u.file), 'utf8');
    assert.ok(src.indexOf('function ' + u.fn + '(') !== -1, 'no ' + u.fn + '()');
    assert.match(src, /'set_active'/, 'nothing in this file posts set_active');
    assert.match(src, /'roster'/, 'nothing in this file reads the roster');
  });

  test(u.file + ' actually CALLS its render function -- a defined panel is not a shown one', () => {
    // Nearly shipped for real: sairnbiz.html got its access card and its
    // sbRenderAccess() and nothing invoked it, so the card would have rendered
    // empty forever. Defined-but-never-called is the same dormant-code failure
    // as an endpoint with no client, one layer down, and neither the DOM-target
    // check nor a syntax check can see it.
    const src = fs.readFileSync(path.join(API, '..', u.file), 'utf8');
    const render = u.render;
    const defs = src.split('function ' + render + '(').length - 1;
    const uses = src.split(render + '(').length - 1;
    assert.ok(defs >= 1, 'no ' + render + '() at all');
    assert.ok(uses > defs,
      render + '() is defined ' + defs + ' time(s) and called ' + (uses - defs) +
      ' — nothing renders the panel, so it stays empty');
  });

  test(u.file + ' asks for a reason before deactivating', () => {
    // The server refuses 400 without one. A client that does not ask produces a
    // button that always fails, which reads as a broken feature.
    const src = fs.readFileSync(path.join(API, '..', u.file), 'utf8');
    const at = src.indexOf('function ' + u.fn + '(');
    const body = src.slice(at, at + 1400);
    assert.match(body, /window\.prompt\(/, 'never asks for a reason');
    assert.match(body, /reason/, 'never sends a reason');
  });

  test(u.file + ' does not second-guess the server about who may be deactivated', () => {
    // A client-side copy of "last owner" or "not yourself" is a second copy of
    // a security rule, free to drift from the one that enforces it.
    const src = fs.readFileSync(path.join(API, '..', u.file), 'utf8');
    const at = src.indexOf('function ' + u.fn + '(');
    const body = src.slice(at, at + 1400);
    assert.strictEqual(/LAST_ADMIN|last owner|lastOwner|activeOwners/.test(body), false,
      'the client re-implements a lockout guard');
  });
});

test('the not-built UI list is accurate', () => {
  UI_NOT_BUILT.forEach((u) => {
    const src = fs.readFileSync(path.join(API, '..', u.file), 'utf8');
    assert.strictEqual(/function \w+SetActive\(/.test(src), false,
      u.file + ' now HAS a deactivation UI but is still listed as not built — ' +
      'move it to UI and delete the excuse');
  });
});

test('every wired endpoint has either a UI or a written-down reason it does not', () => {
  const uiApps = UI.map((u) => u.file.replace('.html', ''));
  const noUiApps = UI_NOT_BUILT.map((u) => u.file.replace('.html', ''));
  WIRED.forEach((e) => {
    const covered = uiApps.indexOf(e.app) !== -1 || noUiApps.indexOf(e.app) !== -1;
    assert.ok(covered,
      e.app + ' has a set_active endpoint and appears in neither the UI list nor ' +
      'the not-built list — it is dormant code nobody has accounted for');
  });
});

test('the five pre-existing implementations still have their own set_active', () => {
  PRE_EXISTING.forEach((f) => {
    assert.match(read(f), /action === 'set_active'/, f + ' lost its handler');
  });
});

test('the still-open list is accurate: those endpoints really have no set_active', () => {
  // If this fails because somebody wired one, move it to WIRED. A stale
  // "still open" list is how a closed gap gets worked twice -- which cost this
  // project four hours on 2026-08-30.
  STILL_OPEN.forEach((f) => {
    assert.strictEqual(read(f).indexOf("action === 'set_active'"), -1,
      f + ' now has a set_active handler but is still listed as open');
  });
});

test('every app auth endpoint is accounted for in exactly one list', () => {
  const all = fs.readdirSync(API)
    .filter((f) => /-auth\.js$/.test(f) && !/\.test\.js$/.test(f))
    .filter((f) => f !== 'sd-sub-auth.js');   // subcontractor portal, not employees
  const known = WIRED.map((e) => e.file).concat(PRE_EXISTING, STILL_OPEN).sort();
  assert.deepStrictEqual(all.sort(), known,
    'an auth endpoint exists that no list mentions — it is neither wired, ' +
    'pre-existing, nor recorded as open, so nobody will ever look at it');
});
