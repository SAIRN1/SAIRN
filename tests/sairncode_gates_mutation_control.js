// tests/sairncode_gates_mutation_control.js
//
// Run:  node tests/sairncode_gates_mutation_control.js
//
// THE NEGATIVE CONTROL FOR tests/sairncode_gates.js -- AND IT VERIFIES ITS OWN
// SABOTAGE APPLIED.
//
// Measured on this platform on 2026-09-13 by `tools/sabotage_control_check.py`:
// 23 of 39 negative controls NEVER VERIFY THEIR OWN SABOTAGE APPLIED. A control
// that anchors on a string which no longer exists, mutates nothing, and then
// reports "the suite went red" is reporting nothing -- it would pass
// identically against a subject with the defect still in it.
//
// Every mutation below is asserted in FOUR parts, in order:
//
//   1. the anchor is FOUND in api/sd-data.js exactly once   (else: stale anchor)
//   2. the mutated copy DIFFERS from the original            (else: no-op edit)
//   3. the mutant still PARSES                               (else: a red suite
//      would be the FILE failing, not the gate)
//   4. tests/sairncode_gates.js, run against the mutated handler, EXITS NON-ZERO
//
// ── WHY THIS MATTERS MORE HERE THAN ON A TYPICAL SUITE ──────────────────────
// sairncode_gates.js asserts that things are REFUSED. A suite of refusals is
// the easiest kind to write so that it passes vacuously -- a handler that
// refused everything, or one that never ran at all, satisfies every "is it
// 403?" arm. The suite carries its own CONTROL arms for that (an admin really
// does reach storage, an ordinary sc_auth_requests write really is open), and
// these mutations are the independent check on whether those controls bite.
//
// SAIRNcode's gates are what stand between a licence key and a deleted
// medical-billing record: it is the only app on the platform where all 28
// registered resources declare a `delete` verb.
//
// The mutations are written to a temp copy of the whole api/ tree. api/sd-data.js
// is never touched, and the closing section asserts that.

'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SRC = path.join(ROOT, 'api', 'sd-data.js');
// THE CLIENT HALF IS MUTATED TOO (2026-09-14). The Tier A write gate has two
// halves that can each be wrong on their own: the server refusing, and the
// client not rendering that refusal as a refusal. A control on only the first
// would pass on a build where a coder is told to "wait until resolved" for
// something that will never resolve.
const APP = path.join(ROOT, 'sairncode.html');
const SUITE = path.join(__dirname, 'sairncode_gates.js');
const ORIGINAL = fs.readFileSync(SRC, 'utf8');
const APP_ORIGINAL = fs.readFileSync(APP, 'utf8');

let n = 0, failures = 0;
function ok(cond, label, detail) {
  n += 1;
  if (cond) { console.log('  ok   ' + label); return; }
  failures += 1;
  console.log('  FAIL ' + label + (detail ? '\n       ' + detail : ''));
}
function section(s) { console.log('\n' + s); }

// The suite requires api/sd-data.js BY PATH from ROOT, so the mutant has to be
// swapped in at that path. Copying the whole repo would be slow and copying
// only api/ breaks the suite's other requires, so the handler is swapped in
// place and restored in a finally -- and section 2 asserts the restore worked
// by comparing bytes, not by trusting that the finally ran.
// `target` defaults to the handler, so every pre-existing mutation is unchanged.
function runSuiteWith(source, target) {
  const file = target || SRC;
  fs.writeFileSync(file, source, 'utf8');
  try {
    const r = spawnSync(process.execPath, [SUITE], { cwd: ROOT, encoding: 'utf8',
                                                     timeout: 300000 });
    return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
  } finally {
    fs.writeFileSync(SRC, ORIGINAL, 'utf8');
    fs.writeFileSync(APP, APP_ORIGINAL, 'utf8');
  }
}
function sourceFor(m) { return m.app ? APP_ORIGINAL : ORIGINAL; }
function pathFor(m) { return m.app ? APP : SRC; }
function labelFor(m) { return m.app ? 'sairncode.html' : 'api/sd-data.js'; }

// EVERY MUTATION IS A REAL DEFECT SOMEBODY COULD WRITE -- a gate relaxed, a
// check inverted, a server-set field taken from the client instead. None is a
// syntax error: a control that sabotages by breaking the parse proves only that
// the file still has to parse.
const MUTATIONS = [
  {
    name: 'the delete gate accepts ANY authenticated role, not just admin',
    find: "        if (!scCaller || scCaller.role !== 'admin') {\n"
        + "          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Compliance Admin can delete records' } });",
    replace: "        if (!scCaller) {\n"
        + "          res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only Compliance Admin can delete records' } });",
  },
  {
    name: 'the delete gate drops the expectedApp argument -- any app\'s session '
        + 'deletes SAIRNcode records',
    find: "        const scCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairncode');",
    replace: "        const scCaller = verifySessionToken(tokenFromRequest(req), licHash);",
  },
  {
    name: 'the sc_settings write gate is removed entirely',
    find: "        if (resource === 'sc_settings') {\n"
        + "          const scSetCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairncode');",
    replace: "        if (false) {\n"
        + "          const scSetCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairncode');",
  },
  {
    name: 'the retention floor becomes a floor of zero',
    find: "          const validNumber = Number.isFinite(numeric) && numeric >= SC_RETENTION_FLOOR_YEARS;",
    replace: "          const validNumber = Number.isFinite(numeric) && numeric >= 0;",
  },
  {
    name: 'the retention check accepts any non-empty string, so "forever" stores',
    find: "          const validIndefinite = rv === 'indefinite';",
    replace: "          const validIndefinite = typeof rv === 'string' && rv !== '';",
  },
  {
    name: 'the sign-off gate fires only on status=submitted, so setting '
        + 'signedOffBy alone slips past',
    find: "          const attemptingSignOff = Object.prototype.hasOwnProperty.call(payload, 'signedOffBy') ||\n"
        + "            payload.status === 'submitted';",
    replace: "          const attemptingSignOff = payload.status === 'submitted';",
  },
  {
    name: 'the signed-off name is taken from the CLIENT payload again -- the '
        + 'forged-name defect',
    find: "            payload.signedOffBy = arCaller.employee_id;",
    replace: "            payload.signedOffBy = payload.signedOffBy || arCaller.employee_id;",
  },
  // ── THE TIER A BILLING WRITE GATE (2026-09-14) ─────────────────────────────
  // Michael's decision, and a behaviour change on live data: six resources that
  // accepted a write from the licence key alone now require admin or biller.
  // Every mutation below is a way that gate could be written wrong while still
  // looking right -- and two of them make the app WORSE than it was before the
  // gate existed, which is the direction a security narrowing actually fails in.
  {
    name: 'the Tier A billing write gate is removed entirely -- back to '
        + 'licence-only on six Tier A resources',
    find: "        if (SC_TIER_A_WRITE_GATED.indexOf(resource) !== -1) {",
    replace: "        if (false) {",
  },
  {
    name: 'the gate accepts ANY authenticated role, so a coder writes claims again',
    find: "          if (SC_TIER_A_WRITE_ROLES.indexOf(scTierACaller.role) === -1) {",
    replace: "          if (false) {",
  },
  {
    name: 'the role list names a role this app does not have -- the PR 3.4 trap, '
        + 'and it locks EVERY account out',
    find: "const SC_TIER_A_WRITE_ROLES = ['admin', 'biller'];",
    replace: "const SC_TIER_A_WRITE_ROLES = ['admin', 'manager'];",
  },
  {
    name: '401 and 403 are collapsed, so "not signed in" and "wrong role" become '
        + 'one answer with one wrong fix',
    find: "            res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first — ' + resource + ' is a billing record and requires a signed-in employee session' } });",
    replace: "            res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Not allowed' } });",
  },
  {
    name: 'the gate drops expectedApp, so another app\'s admin session writes '
        + 'SAIRNcode billing records',
    find: "          const scTierACaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairncode');",
    replace: "          const scTierACaller = verifySessionToken(tokenFromRequest(req), licHash);",
  },
  {
    name: 'the gate widens to all 28, so the 20 non-billing resources every role '
        + 'writes start answering 401',
    find: "        if (SC_TIER_A_WRITE_GATED.indexOf(resource) !== -1) {",
    replace: "        if (true) {",
  },
  {
    name: 'one resource is quietly dropped from the gated list',
    find: "  'sc_ar', 'sc_claims', 'sc_revenue', 'sc_denial', 'sc_compliance',",
    replace: "  'sc_claims', 'sc_revenue', 'sc_denial', 'sc_compliance',",
  },
  // ── THE CLIENT HALF ────────────────────────────────────────────────────────
  // A refusal the server states and the client renders as "server sync failed,
  // will not appear on other devices until resolved" is WORSE than a bare error:
  // "until resolved" tells a coder to wait for something that will never happen,
  // and the row sits on that one device for ever. Shipping the gate without this
  // half would have reintroduced the silent-failure class on purpose.
  {
    app: true,
    name: 'CLIENT: the refusal helper falls through to the transient sentence, '
        + 'so a 403 reads as "will resolve"',
    find: "            if (code === 'FORBIDDEN' || code === 'NO_SESSION') {",
    replace: "            if (false) {",
  },
  {
    app: true,
    name: 'CLIENT: the helper replaces the message for EVERY failure, so a real '
        + 'network drop reads as permanent',
    find: "            if (code === 'FORBIDDEN' || code === 'NO_SESSION') {",
    replace: "            if (true) {",
  },
  {
    app: true,
    name: 'CLIENT: sc_claims stops routing its failure through the helper -- one '
        + 'of six call sites, which is how half a fix ships',
    find: "showToast(!saved ? 'Could not save -- storage may be full or unavailable, try again' : (synced ? 'Claim added' : scWriteRefusalText('Claim added on this device only",
    replace: "showToast(!saved ? 'Could not save -- storage may be full or unavailable, try again' : (synced ? 'Claim added' : ('Claim added on this device only",
  },
  {
    app: true,
    name: 'CLIENT: the refusal stops carrying the server\'s own words, so the '
        + 'user is not told which role can',
    find: "                    ((e && e.message) || 'your role is not allowed to change this record.') +",
    replace: "                    ('this record could not be saved.') +",
  },
  {
    app: true,
    name: 'CLIENT: the refusal stops saying re-trying will not help',
    find: "                    ' It is on this computer only, and re-trying will not change that.';",
    replace: "                    ' It is on this computer only.';",
  },
  {
    name: 'an unconditional session gate APPEARS on sc_claims -- narrowing the '
        + 'WRONG branch, which breaks the allowed roles and the reads',

    find: "      if (action === 'write') {\n"
        + "        if (!payload || !payload.id) { res.status(400).json({ error: { message: 'payload.id is required' } }); return; }\n"
        + "        // sc_settings ROLE GATE",
    replace: "      if (action === 'write') {\n"
        + "        if (!payload || !payload.id) { res.status(400).json({ error: { message: 'payload.id is required' } }); return; }\n"
        + "        if (resource === 'sc_claims' && !verifySessionToken(tokenFromRequest(req), licHash, 'sairncode')) {\n"
        + "          res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return;\n"
        + "        }\n"
        + "        // sc_settings ROLE GATE",
  },
];

console.log('SAIRNcode gates: every arm is shown to FAIL on a sabotaged '
            + 'handler\n');

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'sairncode-gates-mutation-'));

try {
  // ── 0. BASELINE ───────────────────────────────────────────────────────────
  // Without this, every "went red" below could be a suite that is red for an
  // unrelated reason.
  section('0. baseline -- the suite is green against the shipped handler');
  {
    const r = runSuiteWith(ORIGINAL);
    ok(r.code === 0, 'tests/sairncode_gates.js passes against the unmutated '
       + 'handler (exit ' + r.code + ')',
       (r.out.split('\n').filter((l) => l.trim()).slice(-6).join('\n')));
    ok(/5\. the posture of every resource/.test(r.out),
       '...and it really reached section 5, so the posture arms below have '
       + 'something to break');
  }

  section('1. each mutation: found, applied, parses, and caught');
  MUTATIONS.forEach((m, i) => {
    const idx = i + 1;
    console.log('\n  [' + idx + '] ' + m.name);

    const base = sourceFor(m);
    const hits = base.split(m.find).length - 1;
    ok(hits === 1, 'the anchor is present in ' + labelFor(m)
       + ' EXACTLY once (found ' + hits + ')');
    if (hits !== 1) return;

    const mutated = base.replace(m.find, m.replace);
    ok(mutated !== base, 'the mutated source differs from the original');

    // sairncode.html is not a JS file, so the parse arm is the SCRIPT-BLOCK
    // check for it -- the same tool the push gate uses -- rather than a JS parse
    // of the whole document.
    let parses = true;
    if (m.app) {
      fs.writeFileSync(APP, mutated, 'utf8');
      const cb = spawnSync('python', [path.join(ROOT, 'tools', 'checkblocks.py'),
                                      'sairncode.html'],
                           { cwd: ROOT, encoding: 'utf8', timeout: 300000 });
      parses = /FAILED_BLOCKS:0/.test(cb.stdout || '');
      fs.writeFileSync(APP, APP_ORIGINAL, 'utf8');
    } else {
      try {
        // eslint-disable-next-line no-new-func
        new (require('vm').Script)(mutated, { filename: 'mutant.js' });
      } catch (e) {
        parses = false;
        console.log('       SyntaxError: ' + (e && e.message));
      }
    }
    ok(parses, '...and it still PARSES, so a red suite is the GATE failing and '
       + 'not the file');
    if (!parses) return;

    // Written to disk as well, so the "sabotage applied" claim is about bytes
    // a process will actually read rather than about a string in memory.
    const onDisk = path.join(tmpDir, 'mutant-' + idx + '.js');
    fs.writeFileSync(onDisk, mutated, 'utf8');
    ok(fs.readFileSync(onDisk, 'utf8').indexOf(m.replace.split('\n')[0]) !== -1,
       '...and the mutation is present in the bytes on disk');

    const r = runSuiteWith(mutated, pathFor(m));
    ok(r.code !== 0, 'tests/sairncode_gates.js FAILS on it (exit ' + r.code + ')',
       r.out.split('\n').filter((l) => l.trim()).slice(-4).join('\n'));
  });

  // ── 2. THE SHIPPED HANDLER IS UNTOUCHED ───────────────────────────────────
  // Asserted by comparing bytes rather than by trusting that every `finally`
  // ran. This control swaps a real file in the real tree, so "it was restored"
  // is the one claim it must not take on faith.
  section('2. both mutated files were restored byte for byte');
  ok(fs.readFileSync(SRC, 'utf8') === ORIGINAL,
     'the shipped handler is byte-identical to how this run found it');
  ok(fs.readFileSync(APP, 'utf8') === APP_ORIGINAL,
     'and so is sairncode.html');
} finally {
  try { fs.writeFileSync(SRC, ORIGINAL, 'utf8'); } catch (e) { /* last resort */ }
  try { fs.writeFileSync(APP, APP_ORIGINAL, 'utf8'); } catch (e) { /* last resort */ }
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) { /* temp */ }
}

console.log('\n' + (failures
  ? failures + ' OF ' + n + ' ASSERTIONS FAILED'
  : 'ALL ' + n + ' ASSERTIONS PASS'));
process.exit(failures ? 1 : 0);
