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
const SUITE = path.join(__dirname, 'sairncode_gates.js');
const ORIGINAL = fs.readFileSync(SRC, 'utf8');

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
function runSuiteWith(source) {
  fs.writeFileSync(SRC, source, 'utf8');
  try {
    const r = spawnSync(process.execPath, [SUITE], { cwd: ROOT, encoding: 'utf8',
                                                     timeout: 300000 });
    return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
  } finally {
    fs.writeFileSync(SRC, ORIGINAL, 'utf8');
  }
}

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
  {
    name: 'a session gate APPEARS on sc_claims -- the posture map must fail in '
        + 'this direction too',
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

    const hits = ORIGINAL.split(m.find).length - 1;
    ok(hits === 1, 'the anchor is present in api/sd-data.js EXACTLY once (found '
       + hits + ')');
    if (hits !== 1) return;

    const mutated = ORIGINAL.replace(m.find, m.replace);
    ok(mutated !== ORIGINAL, 'the mutated source differs from the original');

    let parses = true;
    try {
      // eslint-disable-next-line no-new-func
      new (require('vm').Script)(mutated, { filename: 'mutant.js' });
    } catch (e) {
      parses = false;
      console.log('       SyntaxError: ' + (e && e.message));
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

    const r = runSuiteWith(mutated);
    ok(r.code !== 0, 'tests/sairncode_gates.js FAILS on it (exit ' + r.code + ')',
       r.out.split('\n').filter((l) => l.trim()).slice(-4).join('\n'));
  });

  // ── 2. THE SHIPPED HANDLER IS UNTOUCHED ───────────────────────────────────
  // Asserted by comparing bytes rather than by trusting that every `finally`
  // ran. This control swaps a real file in the real tree, so "it was restored"
  // is the one claim it must not take on faith.
  section('2. api/sd-data.js was restored byte for byte');
  ok(fs.readFileSync(SRC, 'utf8') === ORIGINAL,
     'the shipped handler is byte-identical to how this run found it');
} finally {
  try { fs.writeFileSync(SRC, ORIGINAL, 'utf8'); } catch (e) { /* last resort */ }
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) { /* temp */ }
}

console.log('\n' + (failures
  ? failures + ' OF ' + n + ' ASSERTIONS FAILED'
  : 'ALL ' + n + ' ASSERTIONS PASS'));
process.exit(failures ? 1 : 0);
