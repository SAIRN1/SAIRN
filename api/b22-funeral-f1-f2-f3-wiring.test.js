// api/b22-funeral-f1-f2-f3-wiring.test.js
//
// Run:  node api/b22-funeral-f1-f2-f3-wiring.test.js
//
// REQUIREMENT (b22, item 4): the three SAIRNlegacy practitioner answers --
// F1 (cremation second signer), F2 (livery billing per home), F3 (apprentice
// clearance owner-configurable) -- are POLICY IN api/_lib/leg-roles.js, and
// two of the three are consulted by NOTHING in production. This suite asserts
// both halves: that the policy is right, and that it is INERT.
//
// ── WHY THE INERTNESS NEEDS AN ARM AND NOT A PARAGRAPH ────────────────────
// `api/sd-data.js` calls `legRoles.decide(resource, role, action)` with THREE
// arguments. `decide()` takes FIVE -- `(resource, role, action, grants, home)`
// -- so every apprentice gets the empty F3 default and every livery driver
// gets the default F2 setting, no matter what a home configured. That has been
// recorded in prose in the b19, b20 and b21 handoffs and in a comment at the
// call site, and a paragraph in a handoff is not a mechanism: it is re-read by
// whoever happens to open that handoff.
//
// THIS SUITE IS THE MECHANISM. Arm C1 asserts the arity of the live call site
// and FAILS THE DAY SOMEBODY WIRES IT -- which is the intended outcome. A
// failing C1 means "the wiring landed; delete this arm and move the F2/F3
// behaviour arms from module-level to handler-level". A failing C1 is GOOD
// NEWS and the arm says so in its own message, because an arm whose failure
// reads as a regression gets silenced instead of actioned.
//
// ── WHAT THIS SUITE DOES NOT TOUCH ────────────────────────────────────────
// `api/sd-data.js` is cody's and is READ ONLY here -- the arms parse it, they
// never edit it. No SQL is run by anything in this file.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const legRoles = require('./_lib/leg-roles.js');
const cs = require('./_lib/countersign.js');
const legCs = require('./leg-countersign.js');

const SD_DATA = path.join(__dirname, 'sd-data.js');

let pass = 0, fail = 0;
const failed = [];
function t(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) {
    console.log('  FAIL ' + name + '\n       ' + e.message);
    fail++; failed.push(name.split('.')[0]);
  }
}
function section(s) { console.log('\n' + s); }

console.log('b22 -- SAIRNlegacy F1/F2/F3: the policy, and what consults it');

// ══ F1 ════════════════════════════════════════════════════════════════════
section('A. F1 -- the cremation second signer. BUILT, and the lock is armed.');

t('A1. leg_cremations is the ONLY resource in LEG_COUNTERSIGN_REQUIRED. A lock '
  + 'that crept onto a second resource would be a separate decision with a '
  + 'separate answer behind it, so the set is asserted and not just read', () => {
  const req = Object.keys(legRoles.LEG_COUNTERSIGN_REQUIRED);
  assert.deepStrictEqual(req, ['leg_cremations'], JSON.stringify(req));
  assert.ok(Object.isFrozen(legRoles.LEG_COUNTERSIGN_REQUIRED),
    'the set is not frozen -- a caller could add one at runtime');
});

t('A2. the endpoint profile locks leg_cremations in MODE_ALWAYS, so the OWNER '
  + 'is bound too. This is the difference from SAIRNlaw C2 lock '
  + '(MODE_PREPARED_ONLY) and it is the whole content of "the paperwork needs a '
  + 'second named person" -- a rule the owner is exempt from is not that rule',
  () => {
    const p = legCs.PROFILE;
    assert.deepStrictEqual(Object.keys(p.lockedResources), ['leg_cremations']);
    assert.strictEqual(p.lockedResources.leg_cremations, cs.MODE_ALWAYS,
      'leg_cremations is not MODE_ALWAYS: ' + p.lockedResources.leg_cremations);
  });

t('A3. the SIGNER set is IMPORTED from leg-roles, not re-listed in the '
  + 'endpoint. Two copies of a role set is an access-control surface and an '
  + 'irreversible-write surface disagreeing about who may sign', () => {
  assert.strictEqual(legCs.PROFILE.signerRoles, legRoles.LEG_REGULATED_WRITE_ROLES,
    'signerRoles is not the same object as LEG_REGULATED_WRITE_ROLES -- it has '
    + 'been copied, and a copy can drift');
});

t('A4. and the regulated write set is { owner, director } -- the licensed roles. '
  + 'A task role appearing here is what the lock exists to prevent', () => {
  const signers = Object.keys(legRoles.LEG_REGULATED_WRITE_ROLES).sort();
  assert.deepStrictEqual(signers, ['director', 'owner'], JSON.stringify(signers));
});

// ══ F2 ════════════════════════════════════════════════════════════════════
section('B. F2 -- livery billing per home. POLICY BUILT. Driven, not read.');

t('B1. the setting has exactly TWO values and an unrecognised one falls to the '
  + 'NARROW default. A typo must not open a resource -- `direct-to-family` with '
  + 'a hyphen is the realistic mistake and it resolves to through_the_home',
  () => {
    assert.deepStrictEqual(legRoles.LEG_LIVERY_BILLING_VALUES.slice(),
      ['through_the_home', 'direct_to_family']);
    assert.strictEqual(legRoles.liveryBilling(undefined), 'through_the_home');
    assert.strictEqual(legRoles.liveryBilling('direct-to-family'), 'through_the_home');
    assert.strictEqual(legRoles.liveryBilling('direct_to_family'), 'direct_to_family');
    assert.strictEqual(legRoles.liveryBilling({}), 'through_the_home');
  });

t('B2. THE DISPATCH\'S OWN WORDING -- "default no money read" -- holds, and it '
  + 'is stronger than stated: leg_liveryvendors carries the pricing an invoice '
  + 'is built from and is DENY to livery under EVERY setting, even with an '
  + 'explicit per-employee grant. There is no arrangement that needs it', () => {
  for (const setting of [undefined, 'through_the_home', 'direct_to_family']) {
    const d = legRoles.decide('leg_liveryvendors', 'livery', 'read',
      { leg_liveryvendors: true }, { livery_billing: setting });
    assert.strictEqual(d, legRoles.DENY,
      'leg_liveryvendors readable under ' + String(setting) + ': ' + d);
  }
});

t('B3. the setting\'s ONE effect, in both directions -- under direct_to_family a '
  + 'GRANTED driver may read their own booking, and under the default the SAME '
  + 'grant yields nothing. A setting with no measurable effect would be dormant '
  + 'code dressed as a policy', () => {
  const granted = { leg_liverybookings: true };
  assert.strictEqual(
    legRoles.decide('leg_liverybookings', 'livery', 'read', granted,
      { livery_billing: 'direct_to_family' }), legRoles.ALLOW);
  assert.strictEqual(
    legRoles.decide('leg_liverybookings', 'livery', 'read', granted), legRoles.DENY);
});

t('B4. NOTHING WIDENS WITHOUT A GRANT. Setting direct_to_family alone grants no '
  + 'driver anything -- personnel above them still have to perform the grant, '
  + 'which is F2\'s companion answer', () => {
  assert.strictEqual(
    legRoles.decide('leg_liverybookings', 'livery', 'read', null,
      { livery_billing: 'direct_to_family' }), legRoles.DENY);
});

// ══ F3 ════════════════════════════════════════════════════════════════════
section('C. F3 -- apprentice clearance owner-configurable. POLICY BUILT.');

t('C1. the default grants NOTHING NEW and turns the disclosure ON. A home that '
  + 'has not answered F3 keeps exactly the shipped policy and is TOLD the app '
  + 'cannot enforce supervision', () => {
  const pol = legRoles.apprenticePolicy(undefined);
  assert.deepStrictEqual(pol.countersign, []);
  assert.deepStrictEqual(pol.forbidden, []);
  assert.strictEqual(pol.presence_disclosure, true);
  assert.ok(/cannot verify/i.test(pol.disclosure_text), pol.disclosure_text);
});

t('C2. the config is OWNER-CONFIGURABLE and not fixed -- a countersign entry '
  + 'makes `prepare` reachable for an apprentice where the default refuses it. '
  + 'That is the "not fixed" half of the dispatch\'s wording', () => {
  assert.strictEqual(
    legRoles.decide('leg_cremations', 'apprentice', 'prepare'), legRoles.DENY);
  assert.strictEqual(
    legRoles.decide('leg_cremations', 'apprentice', 'prepare', null,
      { apprentice: { countersign: ['leg_cremations'] } }), legRoles.ALLOW);
});

t('C3. `forbidden` NARROWS and runs FIRST, so it cannot be outvoted by the band '
  + 'or by a countersign route. Narrowing-before-widening is the ordering that '
  + 'made the trust lock reachable in the sibling module', () => {
  const both = { apprentice: { forbidden: ['leg_cremations'],
                               countersign: ['leg_cremations'] } };
  assert.strictEqual(
    legRoles.decide('leg_cremations', 'apprentice', 'prepare', null, both),
    legRoles.DENY, 'forbidden lost to countersign -- the order is wrong');
  assert.strictEqual(
    legRoles.decide('leg_cremations', 'apprentice', 'read', null, both),
    legRoles.DENY);
});

t('C4. a STORED CONFIG IS UNTRUSTED INPUT: a resource name that is not in the '
  + 'table is DROPPED, and a string where a list belongs cannot widen anything. '
  + 'A typo must grant nothing rather than match nothing silently later', () => {
  const pol = legRoles.apprenticePolicy({ countersign: ['leg_not_a_resource'],
                                          forbidden: 'leg_cremations' });
  assert.deepStrictEqual(pol.countersign, [], JSON.stringify(pol.countersign));
  assert.deepStrictEqual(pol.forbidden, [], JSON.stringify(pol.forbidden));
  assert.strictEqual(
    legRoles.decide('leg_cremations', 'apprentice', 'prepare', null,
      { apprentice: { countersign: ['leg_not_a_resource'] } }), legRoles.DENY);
});

t('C5. anything other than an explicit `false` leaves the disclosure ON. A '
  + 'missing, null or malformed value must not silently remove a disclosure',
  () => {
    for (const v of [undefined, null, 0, '', 'false', {}]) {
      assert.strictEqual(
        legRoles.apprenticePolicy({ presence_disclosure: v }).presence_disclosure,
        true, 'the disclosure was removed by ' + JSON.stringify(v));
    }
    assert.strictEqual(
      legRoles.apprenticePolicy({ presence_disclosure: false }).presence_disclosure,
      false, 'an explicit false must be honoured');
  });

// ══ THE INERTNESS, AS A MECHANISM ═════════════════════════════════════════
section('D. F2 AND F3 ARE CONSULTED BY NOTHING. This is the arm, not a paragraph.');

// ── D1 FIRED, AND IT WAS GOOD NEWS. RE-AIMED 2026-10-20 (hank b24). ───────
// This arm asserted that NO call site passed `grants`/`home`, and said in its
// own text: "A FAILURE HERE IS GOOD NEWS -- it means the wiring landed."
// IT FAILED. cody's b27 wired it, and the arm named the site:
//
//   api/sd-data.js:16702  resource, legSess.role, action, null, legHome
//
// RE-AIMED RATHER THAN DELETED, and that is the whole discipline: the arm's own
// instruction was "delete this arm and promote the F2/F3 arms to handler
// level". Deleting it HERE would leave nothing asserting that the wiring is
// still there -- the gap stopped being the risk and a REGRESSION became one.
// Promoting the module-level F2/F3 arms to handler level is cody's lane (their
// wiring, their batch) and is ROUTED in SAIRN-handoff-hank-b24.md, not done
// here. What this arm does now is hold the new truth.
t('D1. api/sd-data.js NOW calls legRoles.decide with FIVE arguments, so `home` '
  + 'reaches the policy and F2/F3 are consulted. This arm asserted the OPPOSITE '
  + 'until cody\'s b27 wired it; it is re-aimed, not deleted, so a revert '
  + 'cannot pass unnoticed', () => {
  const src = fs.readFileSync(SD_DATA, 'utf8');
  const calls = [];
  const re = /legRoles\.decide\(([^;]*?)\)\s*===/g;
  let m;
  while ((m = re.exec(src)) !== null) {
    const argc = m[1].split(',').length;
    const line = src.slice(0, m.index).split('\n').length;
    calls.push({ line: line, argc: argc, text: m[1].trim().slice(0, 90) });
  }
  assert.ok(calls.length >= 1,
    'no legRoles.decide call site found in api/sd-data.js at all -- either the '
    + 'handler stopped using the module (a much bigger finding) or this arm is '
    + 'looking for the wrong shape');
  const wired = calls.filter((c) => c.argc >= 5);
  assert.ok(wired.length >= 1,
    'NO call site passes grants/home any more -- the wiring has been REVERTED, '
    + 'and F2/F3 are policy nothing consults again. Call sites found:\n       '
    + calls.map((c) => 'sd-data.js:' + c.line + ' (' + c.argc + ' args)')
        .join('\n       '));
  console.log('       wired call site(s): '
    + wired.map((c) => 'sd-data.js:' + c.line + '  ' + c.text).join(', '));
});

t('D2. ...and `leg_settings` is registered as a resource NOWHERE in '
  + 'api/sd-data.js, so there is no row to pass even if the call took it. The '
  + 'only occurrence is the handler\'s own comment saying exactly that', () => {
  const src = fs.readFileSync(SD_DATA, 'utf8');
  const lines = src.split('\n');
  const hits = [];
  lines.forEach((l, i) => {
    if (l.indexOf('leg_settings') !== -1) {
      hits.push({ line: i + 1, comment: l.trim().indexOf('//') === 0 });
    }
  });
  const code = hits.filter((h) => !h.comment);
  assert.strictEqual(code.length, 0,
    'leg_settings now appears in CODE at sd-data.js:'
    + code.map((h) => h.line).join(', ') + ' -- the registration may have '
    + 'landed. Check it, then update D1 and D2 together.');
  assert.ok(hits.length >= 1,
    'the handler no longer even mentions leg_settings -- the comment that '
    + 'records this gap has been deleted, which is worse than the gap');
});

t('D3. NEGATIVE CONTROL ON D1 AND D2: decide() really does take five '
  + 'parameters, so the three-argument call site is genuinely dropping two. '
  + 'Without this, D1 could be asserting an arity that does not exist and would '
  + 'pass on a module that never accepted grants or home at all', () => {
  assert.strictEqual(legRoles.decide.length, 5,
    'decide() takes ' + legRoles.decide.length + ' parameters, not 5 -- D1 is '
    + 'measuring against the wrong contract');
  // And the two dropped arguments demonstrably CHANGE the answer, so they are
  // not vestigial parameters nobody reads.
  const g = { leg_liverybookings: true };
  const h = { livery_billing: 'direct_to_family' };
  assert.notStrictEqual(
    legRoles.decide('leg_liverybookings', 'livery', 'read'),
    legRoles.decide('leg_liverybookings', 'livery', 'read', g, h),
    'passing grants and home changes nothing, so the wiring gap would be '
    + 'harmless and D1 would not be worth asserting');
});

// ══ F1'S OWN GAP ══════════════════════════════════════════════════════════
section('E. F1 is wired but its table is not provisioned -- the third state.');

t('E1. the endpoint names the SQL file a reader has to run, so a 503 from it is '
  + 'actionable rather than mysterious. The lock is ARMED IN CODE and INERT IN '
  + 'THE DATABASE, and those are different facts', () => {
  assert.strictEqual(legCs.PROFILE.sqlFile,
    'sql/sairnlegacy_countersign_schema.sql', legCs.PROFILE.sqlFile);
  assert.ok(fs.existsSync(path.join(__dirname, '..', legCs.PROFILE.sqlFile)),
    'the profile names a SQL file that does not exist in the repo');
});

t('E2. and the schema carries BOTH constraints the lock depends on -- the '
  + 'self-signature refusal and the complete-signature refusal. A table applied '
  + 'without them looks identical to a reader and accepts every row the lock '
  + 'exists to refuse', () => {
  const sql = fs.readFileSync(
    path.join(__dirname, '..', legCs.PROFILE.sqlFile), 'utf8');
  for (const c of ['sairnlegacy_countersign_not_self',
                   'sairnlegacy_countersign_complete']) {
    assert.ok(sql.indexOf('constraint ' + c) !== -1,
      'the schema does not declare ' + c);
  }
});

// ══ F. THE ABLATIONS, ADDED 2026-10-20 (hank b24) ═════════════════════════
// THIS SUITE HAD NO ABLATION. Found by a census of the nine b18-b23 suites --
// six carried one, three did not -- not by review, which is the point: every
// arm above could have been passing because the thing in FRONT of the guard
// was working. fourth's b26 finding H1 was exactly that, one file over.
//
// D1/D2 are deliberately INVERTED arms (they assert a gap still exists) and
// D3 is already their control, so the ablations below target the arms that
// assert something BUILT.
//
// Per ARM, not per exit code, and each names what must STAY GREEN.
if (process.env.B22_FUNERAL_ARMS_ONLY !== '1') {
  const { execFileSync } = require('child_process');
  const SELF = __filename;
  const LEG_ROLES_SRC = path.join(__dirname, '_lib', 'leg-roles.js');
  const LEG_CS_SRC = path.join(__dirname, 'leg-countersign.js');

  const runArms = () => {
    try {
      const out = execFileSync(process.execPath, [SELF], {
        env: Object.assign({}, process.env, { B22_FUNERAL_ARMS_ONLY: '1' }),
        encoding: 'utf8', stdio: 'pipe' });
      return { exit: 0, out: String(out || '') };
    } catch (e) {
      return { exit: typeof e.status === 'number' ? e.status : -1,
               out: String((e && e.stdout) || '') + String((e && e.stderr) || '') };
    }
  };
  const armsOf = (out) => {
    const m = String(out || '').match(/FAILED:\s*(.+)/);
    return m ? m[1].trim().split(/\s*,\s*/).filter(Boolean) : [];
  };
  // BYTES IN, BYTES OUT -- this repo has mixed line endings file by file, so a
  // text round trip would rewrite every line and the restore would not be one.
  const ablate = (file, find, replace) => {
    const buf = fs.readFileSync(file);
    const src = buf.toString('utf8');
    let needle = find, repl = replace, hits = src.split(find).length - 1;
    if (hits !== 1) {
      const crlf = find.replace(/\n/g, '\r\n');
      if (src.split(crlf).length - 1 === 1) {
        needle = crlf; repl = replace.replace(/\n/g, '\r\n'); hits = 1;
      }
    }
    if (hits !== 1) {
      return { ok: false, why: 'the ablation anchor matched ' + hits
        + ' time(s) in ' + path.basename(file) + ', not exactly 1 -- REFUSING '
        + 'to mutate. FIX THE ANCHOR, do not delete the arm.' };
    }
    try {
      fs.writeFileSync(file, Buffer.from(src.replace(needle, repl), 'utf8'));
      const r = runArms();
      return { ok: true, exit: r.exit, arms: armsOf(r.out) };
    } finally {
      fs.writeFileSync(file, buf);
    }
  };

  section('F. ABLATIONS -- remove ONE layer and measure what it alone catches');

  t('F0. THE CONTROL: with nothing ablated the arms-only child run is GREEN '
    + '(exit 0). Every ablation below is measured against this', () => {
    const c = runArms();
    assert.strictEqual(c.exit, 0, 'child exit ' + c.exit + '\n' + c.out.slice(-400));
  });

  t('F1. MODE_ALWAYS -> MODE_PREPARED_ONLY makes arm A2 FAIL -- so the mode is '
    + 'what binds the OWNER, and F1\'s whole answer ("a rule the owner is '
    + 'exempt from is not a second named person") rests on that one value',
    () => {
      const r = ablate(LEG_CS_SRC, 'leg_cremations: cs.MODE_ALWAYS',
                       'leg_cremations: cs.MODE_PREPARED_ONLY');
      assert.ok(r.ok, r.why);
      assert.ok(r.exit === 1 && r.arms.indexOf('A2') !== -1,
        'exit ' + r.exit + ' arms=' + r.arms.join(','));
      assert.ok(r.arms.indexOf('A1') === -1 && r.arms.indexOf('A3') === -1,
        'A1/A3 should stay GREEN -- the membership and the imported signer set '
        + 'are untouched. arms=' + r.arms.join(','));
    });

  t('F2. removing the EARLY `forbidden` DENY in decide() makes arm C3 FAIL -- '
    + 'so the ORDER is the policy and "may not touch these records at all" '
    + 'really does win. This ablation was RE-AIMED: see F2b', () => {
      const r = ablate(LEG_ROLES_SRC,
        "    if (pol.forbidden.indexOf(resource) !== -1) return DENY;",
        "    if (false && pol.forbidden.indexOf(resource) !== -1) return DENY;");
      assert.ok(r.ok, r.why);
      assert.ok(r.exit === 1 && r.arms.indexOf('C3') !== -1,
        'exit ' + r.exit + ' arms=' + r.arms.join(','));
      assert.ok(r.arms.indexOf('C1') === -1,
        'C1 should stay GREEN -- the default still grants nothing new. arms='
        + r.arms.join(','));
    });

  // ── F2b IS A FINDING, NOT A PASS, AND IT IS WHY THIS PASS WAS WORTH DOING ─
  // F2's FIRST draft ablated a DIFFERENT layer: the
  // `.filter((r) => forbidden.indexOf(r) === -1)` inside apprenticePolicy(),
  // which strips a resource out of `countersign` when it is also `forbidden`.
  // NOTHING WENT RED. That layer is REDUNDANT given the early DENY above, so
  // no arm in this suite can see it -- which means it is not a control and
  // must not be read as one. It is recorded here rather than deleted: a second
  // narrowing is cheap and the `apprentice` config is untrusted stored input,
  // so belt-and-braces is defensible. What is NOT defensible is leaving a
  // reader to assume an arm is watching it.
  t('F2b. and the SECOND narrowing inside apprenticePolicy() is REDUNDANT: '
    + 'ablating it reddens NOTHING, because the early DENY has already '
    + 'answered. Asserted so the layer is not mistaken for a control', () => {
      const r = ablate(LEG_ROLES_SRC,
        "  const countersign = known(src.countersign)\n"
        + "    .filter((r) => forbidden.indexOf(r) === -1);",
        "  const countersign = known(src.countersign);");
      assert.ok(r.ok, r.why);
      assert.strictEqual(r.exit, 0,
        'removing the second narrowing DID redden something (exit ' + r.exit
        + ', arms=' + r.arms.join(',') + ') -- so it IS load-bearing after all '
        + 'and this arm has the wrong expectation. Re-aim it, do not delete it.');
    });

  t('F3. making the disclosure default OFF makes arm C5 FAIL -- a missing, '
    + 'null or malformed value must not silently remove a disclosure, and '
    + '`!== false` is the one character that holds that', () => {
      const r = ablate(LEG_ROLES_SRC,
        'presence_disclosure: src.presence_disclosure !== false,',
        'presence_disclosure: src.presence_disclosure === true,');
      assert.ok(r.ok, r.why);
      assert.ok(r.exit === 1 && r.arms.indexOf('C5') !== -1,
        'exit ' + r.exit + ' arms=' + r.arms.join(','));
    });
}

console.log('\nb22 funeral f1/f2/f3: ' + pass + ' passed, ' + fail + ' failed');
if (fail) console.log('FAILED: ' + failed.join(', '));
process.exit(fail ? 1 : 0);
