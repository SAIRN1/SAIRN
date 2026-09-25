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
  { file: 'leg-auth.js', app: 'sairnlegacy', table: 'sairnlegacy_employee_auth' },
  // SAIRNvet, 2026-09-13 -- the SIXTEENTH and last app to get per-employee
  // auth, and WIRED from its first commit rather than hand-written. Its
  // first draft was modelled on api/rf-auth.js, which is the cleanest
  // complete example of the ACTION SET and is also one of the five that
  // predate this helper -- so the draft arrived hand-written and THIS TEST
  // caught it at the push gate. PRE_EXISTING would have been the wrong
  // list: its entry reason is 'already live before the helper existed', and
  // adding a same-day endpoint there is raising a count to clear a gate.
  { file: 'sv-auth.js', app: 'sairnvet', table: 'sairnvet_employee_auth' },
  // SAIRNfreedom, 2026-09-21. WIRED FROM ITS FIRST COMMIT, not migrated later
  // and not added to PRE_EXISTING -- the sv-auth.js sequence recorded below
  // settled that a SAME-DAY endpoint does not qualify for that list.
  //
  // It is also the FIRST caller to pass `soleRole`. Every app before it had
  // one provisioning role, so "who may provision" and "who must not reach
  // zero" were one set; SAIRNfreedom has post.govern AND post.govern.deputy
  // provisioning, and only post.govern carries `sole:true` in the app's own
  // CAPABILITIES. Counting the last-admin guard over the provisioning list
  // would let a DEPUTY deactivate the sole governor and brick the licence.
  { file: 'sf-auth.js', app: 'sairnfreedom', table: 'sairnfreedom_employee_auth' }
];

// The five that already had their own hand-written set_active before the shared
// helper existed. Deliberately NOT migrated — they are live, on the auth path,
// and a refactor whose only benefit is tidiness is not worth a locked-out
// customer. Listed so "why is this one different" has an answer on file, and so
// the count below fails if somebody migrates one without updating this.
// ── sv-auth.js WAS BRIEFLY LISTED HERE, AND THE SEQUENCE IS WORTH KEEPING ──
// Hank added it on 2026-09-13 after it arrived by rebase from 29b1f1d5 and this
// suite's accounting assertion went red for EVERY session in every clone. That
// is the seam check working exactly as designed: it reads the whole tree
// precisely so somebody else's change cannot land unrecorded. Their reading of
// the file was correct AT THAT MOMENT -- it did have its own set_active and
// `grep -c employee-lifecycle api/sv-auth.js` returned 0 -- and they read the
// right list off the failures rather than guessing.
//
// IT IS NOW WIRED, and that is not a reversal of their call. Fourth hit the
// same red from the authoring side and migrated the endpoint onto the shared
// helper instead, because PRE_EXISTING's entry reason is "already live before
// the helper existed" and a SAME-DAY endpoint does not qualify. Two sessions
// reached opposite entries from the same failure because they were looking at
// the file in two different states, hours apart. Recorded rather than silently
// resolved: the list a file belongs in is a fact about its CURRENT shape, and a
// rebase can change that between one session reading it and another.
const PRE_EXISTING = ['sd-auth.js', 'sc-auth.js', 'dnt-auth.js', 'mech-auth.js',
                      'rf-auth.js'];

// Endpoints that still have no way to deactivate a credential at all. This list
// is the remaining work, written down rather than described, so it can only
// shrink deliberately.
// Empty as of 2026-09-03: all nine are wired. Kept rather than deleted so the
// accounting assertion below still has three lists to cover every endpoint, and
// so a NEW app that ships credentials without a deactivation path has an
// obvious place to be recorded instead of being quietly missed.
const STILL_OPEN = [];

// Pull the roles a `setup` gate actually enforces, out of its own source.
// THREE shapes exist in this repo and all three are real:
//
//   caller.role !== 'owner'                                    (literal)
//   caller.role !== 'owner' && caller.role !== 'superintendent' (literals)
//   PROVISIONING_ROLES.indexOf(caller.role) === -1              (the constant)
//
// THE THIRD WAS ADDED 2026-09-13, AND WIDENING RATHER THAN NARROWING WAS THE
// RIGHT DIRECTION HERE. api/sv-auth.js writes its gate against the constant,
// which is what `sairn-employee-auth-scaffold` asks for in terms -- it records
// that sc-auth.js and sd-auth.js both DECLARE the constant "so if this list
// ever grows, that guard grows with it automatically" and then use literals in
// their own setup gates anyway. A gate written against the constant cannot
// diverge from it, so the failure THIS TEST EXISTS FOR is structurally
// impossible there; reading it as "names no roles" would have forced the newer
// endpoint to adopt the weaker shape to satisfy the checker.
//
// The widening is narrow on purpose: it matches the constant BY NAME, so a
// gate testing some other list still reads as unparseable rather than being
// waved through. Driven in both directions by the two fixture arms below.
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
  if (!roles.length && /PROVISIONING_ROLES\.indexOf\(caller\.role\) === -1/.test(m[1])) {
    // The gate IS the constant. Return what the constant declares -- the two
    // cannot disagree, which is the whole point of writing it this way.
    return declaredProvisioningRoles(src);
  }
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
      //
      // DOTS TOO, ADDED 2026-09-21. SAIRNfreedom is the first app whose roles
      // are DOTTED CAPABILITY IDS -- post.govern, post.govern.deputy -- taken
      // from its own CAPABILITIES array because a VFW finance officer is the
      // Quartermaster and an Elks one the Treasurer, so one hardcoded
      // vocabulary would be wrong for three of its five target orders.
      // Without this the arm demanded a customer-facing refusal message
      // containing the literal string "post.govern.deputy", which is worse
      // for the customer, not better. The ARM'S INTENT is unchanged: a label
      // must name every role it tells somebody to go and ask.
      const word = r.replace(/[_.]/g, ' ');
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
  { file: 'sairnscape.html', fn: 'scpSetActive', render: 'scpRenderAccess' },
  // SAIRNvet, 2026-09-13. Its endpoint and its screen landed together
  // rather than a release apart, because this test refused the endpoint
  // on its own -- correctly. sairnvet.html had NO auth client at all
  // before today: zero references to sv-auth, to X-SD-Auth, or to any
  // session, and a gate comparing the licence to a literal and the PIN to
  // '1234' in the browser with the ROLE PICKED FROM A DROPDOWN.
  { file: 'sairnvet.html', fn: 'svSetActive', render: 'svRenderAccess' },
  // SAIRNfreedom, 2026-09-21. Endpoint and screen landed together, and the
  // screen is not optional here: arming the session gate on sf_accounts /
  // sf_ledger / sf_vendor_prices while the app had no way to OBTAIN a session
  // would have made three Tier A resources unreachable from the real client.
  // A gate nothing can satisfy is a break, not a control.
  { file: 'sairnfreedom.html', fn: 'sfSetActive', render: 'sfRenderAccess' }
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

test('the pre-existing implementations still have their own set_active', () => {
  // Was "the five" in its own name until 2026-09-13, when sv-auth.js briefly
  // made it six and then stopped -- it was migrated onto the shared helper the
  // same day and moved to WIRED. A count in a test NAME is a claim like any
  // other and this one was wrong TWICE in one day, in both directions; the
  // list is the count, which is why the name no longer carries a number.
  PRE_EXISTING.forEach((f) => {
    assert.match(read(f), /action === 'set_active'/, f + ' lost its handler');
  });
});

test('and none of them has quietly been migrated onto the shared helper', () => {
  // THE DIRECTION THAT WAS MISSING. The assertion above only asks whether the
  // handler is still there, so an endpoint moved onto _lib/employee-lifecycle
  // would keep passing while sitting in the list that says it has not been --
  // and WIRED's own assertions would never see it, because WIRED is where it
  // would then belong. Without this, PRE_EXISTING is a place a migration can
  // hide. Found while reconciling two sessions' independent fixes for
  // sv-auth.js on 2026-09-13.
  // ── NARROWED FROM `require` TO THE CALL, 2026-09-21, AND THE INTENT IS
  // ── UNCHANGED ──────────────────────────────────────────────────────────
  // This asserted that a PRE_EXISTING endpoint does not `require` the helper
  // at all, which was a correct proxy for "has not been migrated" only while
  // the helper exported nothing a non-migrated endpoint would want. It now
  // exports soleRoleDemotionRefusal(), a single guard for the OTHER route to
  // zero provisioners -- the setup role change -- and api/sd-auth.js imports
  // exactly that while keeping its own hand-written set_active.
  //
  // THE PROPERTY WORTH ASSERTING WAS NEVER THE IMPORT. It is whether the
  // endpoint's set_active has been handed to the shared engine, because that
  // is what decides whether WIRED's assertions speak for it. So the check is
  // now `lifecycle.setActive(` and nothing else, which is the same question
  // asked of the thing it was always about.
  //
  // RELAXING A CHECK TO FIT A CHANGE IS THE SHAPE THIS PLATFORM WARNS ABOUT,
  // so: the migration this arm exists to catch still fails it. An endpoint
  // that moves onto the engine calls setActive() -- there is no way to be
  // migrated without it -- and the arm below drives that rather than leaving
  // it as a claim.
  PRE_EXISTING.forEach((f) => {
    assert.strictEqual(/lifecycle\.setActive\(/.test(read(f)), false,
      f + ' now calls the shared setActive() -- move it to WIRED, where its ' +
      'wiring is actually checked, rather than leaving it listed as pre-existing');
  });
});

test('...and that narrowed check still catches a real migration', () => {
  // The arm above was relaxed from "does not import the module" to "does not
  // call setActive". A relaxation is only safe if the thing it was written to
  // catch still fails, so that is driven here against the real source of a
  // PRE_EXISTING endpoint rather than asserted in prose.
  const f = PRE_EXISTING[0];
  const migrated = read(f).replace(
    /action === 'set_active'/,
    "action === 'set_active' && await lifecycle.setActive(ctx)");
  assert.notStrictEqual(migrated, read(f),
    'the injection found no set_active in ' + f + ' -- this arm is not testing '
    + 'what it says it tests');
  assert.strictEqual(/lifecycle\.setActive\(/.test(migrated), true,
    'a migrated ' + f + ' would slip past the narrowed check');
});

// ── THE OTHER ROUTE TO ZERO PROVISIONERS HAD NO WIRING ARM (2026-09-25) ────
// employee-lifecycle.js exports soleRoleDemotionRefusal() and documents the
// route it closes at :340: "setActive() refuses DEACTIVATING the last holder
// of a sole role. It says nothing about CHANGING that holder's role, and every
// `setup` on this platform upserts on (license_hash, employee_id) writing the
// role column -- so demoting the last owner is one call the deactivation guard
// never sees."
//
// EVERY ARM ABOVE IS ABOUT set_active. Nothing asserted that an endpoint whose
// setup WRITES A ROLE calls the demotion guard, and api/sv-auth.js shipped
// without it -- found 2026-09-25 while investigating why SV-PINNACLE-2026 could
// not be signed into while bootstrap answered 409 ALREADY_PROVISIONED, which is
// precisely the dead-licence end state that route produces.
//
// AND THE DETECTOR SHIPPED WITH A DEAD ALTERNATIVE (repaired 2026-09-25).
// The regex below was written through a heredoc and its `\\b` arrived as a RAW
// 0x08 BACKSPACE, so `role:\\s*role\\b` could never match. It was invisible
// because the FIRST alternative matched everywhere it needed to -- the classic
// vacuous-green-with-a-dead-pattern shape, and the fourth instance of
// code-scrubber item 18 on this platform. tools/control_char_check.py caught it
// at the push gate. Repaired by building the escape with chr(92), which is the
// rule that entry states, and the corrected pattern was RE-MEASURED rather than
// assumed: still 16 endpoints, so nothing was hiding behind the dead half.
//
// DERIVED, NOT LISTED: the subject set is read off the files -- every
// *-auth.js whose setup upserts on (license_hash, employee_id) with `role` in
// the body -- so a NEW endpoint is covered the day it lands rather than the day
// somebody remembers to add it. That is the expired-fixture class this arm
// would otherwise join.
//
// GRANDFATHERED, BECAUSE TEN ARE UNGUARDED TODAY AND A RED ARM ON A GREEN TREE
// TEACHES PEOPLE TO IGNORE THE FILE. Measured 2026-09-25: 16 endpoints write a
// role in setup, 6 call the guard (grd, sb, scp, sd, sf, sv) and 10 do not.
// Fixing ten endpoints is real work with ten customer-facing refusal sentences
// to write, and it is not this change. The arm fails on a NEW unguarded
// endpoint and on any of the six LOSING its guard -- both directions, so it
// cannot be satisfied by an empty set.
const DEMOTION_GUARDED = ['grd-auth.js', 'sb-auth.js', 'scp-auth.js',
                          'sd-auth.js', 'sf-auth.js', 'sv-auth.js'];
const DEMOTION_UNGUARDED_BASELINE = ['alf-auth.js', 'bld-auth.js', 'dnt-auth.js',
  'law-auth.js', 'leg-auth.js', 'mech-auth.js', 'rf-auth.js', 'sc-auth.js',
  'sdn-auth.js', 'sen-auth.js'];

function setupRoleWriters() {
  const fs2 = require('fs');
  const out = { guarded: [], unguarded: [] };
  fs2.readdirSync(API).filter((f) => /-auth\.js$/.test(f)).forEach((f) => {
    const src = read(f);
    const i = src.indexOf("action === 'setup'");
    if (i === -1) return;
    // To the NEXT action, not a fixed window: sv-auth's guard comment pushed
    // its upsert past a 4000-char window on the first version of this arm and
    // the endpoint read as "does not write a role" -- a detector measuring the
    // wrong span and reporting clean.
    const j = src.indexOf("action === '", i + 20);
    const region = src.slice(i, j > 0 ? j : src.length);
    if (!/on_conflict=license_hash,employee_id/.test(region)) return;
    if (!/role,\s*pin_hash|role:\s*role\b/.test(region)) return;
    (/soleRoleDemotionRefusal\s*\(/.test(region) ? out.guarded : out.unguarded).push(f);
  });
  return out;
}

test('the setup-writes-a-role set was actually found -- an empty scan passes '
   + 'every assertion below vacuously', () => {
  const r = setupRoleWriters();
  assert.ok(r.guarded.length + r.unguarded.length >= 14,
    'found only ' + (r.guarded.length + r.unguarded.length) + ' setup paths '
    + 'that write a role; the detector is not finding them');
});

test('no endpoint LOSES its sole-role demotion guard', () => {
  const r = setupRoleWriters();
  const lost = DEMOTION_GUARDED.filter((f) => r.guarded.indexOf(f) === -1);
  assert.deepStrictEqual(lost, [],
    'these called soleRoleDemotionRefusal() in setup and no longer do, so the '
    + 'sole active provisioner can demote themselves and leave the licence '
    + 'unrecoverable (bootstrap refuses 409 once any credential exists): '
    + lost.join(', '));
});

test('...and no NEW endpoint joins the unguarded set', () => {
  const r = setupRoleWriters();
  const isNew = r.unguarded.filter((f) => DEMOTION_UNGUARDED_BASELINE.indexOf(f) === -1);
  assert.deepStrictEqual(isNew, [],
    'these write a role in setup with no demotion guard and are not in the '
    + 'grandfathered baseline: ' + isNew.join(', ') + '. Grandfathered means '
    + '"predates the check", never "fine" -- the ten in the baseline are a real '
    + 'open gap, listed in the comment above.');
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
