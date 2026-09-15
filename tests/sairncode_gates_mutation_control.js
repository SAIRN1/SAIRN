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
// ── THE MUTATIONS ARE PLANTED IN A THROWAWAY GIT WORKTREE ───────────────────
// Corrected 2026-09-15, and the correction is the point of this paragraph
// rather than a footnote to it. THIS HEADER USED TO SAY *"the mutations are
// written to a temp copy of the whole api/ tree. api/sd-data.js is never
// touched, and the closing section asserts that"* -- and the code forty lines
// below said the opposite in its own comment: *"the handler is swapped in place
// and restored in a finally."* It was swapped in place, every mutation, every
// run, in this clone, on THREE tracked files. The temp directory existed and
// held nothing the suite ever ran against.
//
// A control whose header describes a mechanism it does not implement is the
// worst version of this defect class, not a documentation nit: the header is
// exactly what somebody reads to decide whether a risk is already covered, and
// this one answered the isolation question with the reassuring answer while
// doing the unsafe thing. It went unnoticed because every assertion still
// passed -- the restore really did work, on every run anybody watched.
//
// WHAT THE IN-PLACE VERSION RISKED, all three reachable rather than theoretical:
//   * A KILLED PROCESS leaves a sabotaged handler on disk in a tracked file. The
//     `finally` does not run for a SIGKILL or a closed terminal, and
//     tools/run_all_tests.py deliberately does NOT clean residue -- it reports
//     it, because `git checkout --` on somebody's working tree is the worse
//     trade. A stranded PROBE commit reached origin twice in two days on
//     2026-09-10; tests/sairnlegacy_fault_probe.py cites that incident as the
//     reason it uses a worktree, and it shipped in the SAME COMMIT as the Tier A
//     mutations this file added.
//   * A CONCURRENT DIRECT RUN restores the wrong bytes. The snapshot is taken at
//     module load, so a second run starting mid-mutation captures the MUTATED
//     file as its "original", restores to that, and passes its byte-identical
//     arm. run_all_tests.py's lock does not help: it guards the runner, and
//     nothing stops `node tests/sairncode_gates_mutation_control.js` directly.
//   * A TREE THAT WAS ALREADY DIRTY is "restored" to its dirty state and section
//     2 reports success, because the baseline it compares against is whatever it
//     happened to find.
// Now: the worktree is created at HEAD, the working-tree copies of the files
// under test are copied in so the semantics stay "test what is on disk now", and
// every write lands inside it. If the worktree cannot be created this file FAILS
// CLOSED and says so -- a control that cannot isolate must not report a full
// sheet of caught mutations (PR 1.11).
//
// THE REGISTRY HALF (item 97) CAME IN ON THE SAME DAY, FROM ANOTHER CLONE, and
// is why UNDER_TEST is a list rather than three constants: a fourth mutable half
// is one string, not another parallel snapshot/restore/assert triple to keep in
// step. The two changes met in a rebase; the isolation was re-applied on top of
// the registry work rather than either being taken whole.

'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
// THE CLIENT HALF IS MUTATED TOO (2026-09-14). The Tier A write gate has two
// halves that can each be wrong on their own: the server refusing, and the
// client not rendering that refusal as a refusal. A control on only the first
// would pass on a build where a coder is told to "wait until resolved" for
// something that will never resolve.
//
// THE REGISTRY IS THE THIRD MUTABLE HALF (2026-09-15, item 97). The list that
// decides which resources may be destroyed lives in api/_resources/sairncode.js,
// not in the handler, so a control that could only sabotage the handler could
// not reach the one edit that reopens the whole finding -- emptying the list.
const UNDER_TEST = ['api/sd-data.js', 'sairncode.html', 'api/_resources/sairncode.js',
                    'tests/sairncode_gates.js'];

// ── THE CLONE'S OWN BYTES, RECORDED BEFORE ANYTHING HAPPENS ─────────────────
// Hashed rather than kept in memory as text: the closing control's job is to
// prove this process never wrote these paths, and a hash is the cheap way to say
// so about a 2MB document.
function sha(p) {
  return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
}
// ── MTIME IS RECORDED TOO, AND THAT IS NOT BELT-AND-BRACES ─────────────────
// The hash alone cannot tell NEVER WRITTEN from WRITTEN AND RESTORED, which is
// the same conflation this whole change exists to remove -- and it was caught by
// running the finished control with its own isolation deliberately broken
// (SRC repointed at the clone, 2026-09-15). Arms went red and the structural arm
// fired, but every hash arm PASSED, because `runSuiteWith`'s `finally` had
// already put the original bytes back. A control that only compares end-state
// bytes reports a clean clone about a run that mutated it many times over.
// LIMIT, stated rather than implied: this detects a write-and-restore only
// because the pre-run mtime is minutes or hours old. Two writes inside one
// filesystem timestamp granularity would be invisible, so the STRUCTURAL arm
// below -- not this one -- is what carries the guarantee.
function stamp(p) { return sha(p) + ':' + fs.statSync(p).mtimeMs; }
const CLONE_BEFORE = {};
UNDER_TEST.forEach((rel) => { CLONE_BEFORE[rel] = stamp(path.join(ROOT, rel)); });

// ── THE WORKTREE. FAIL CLOSED IF IT CANNOT BE MADE ─────────────────────────
// "Could not isolate" is a third answer and it is never folded into "every
// mutation caught". Exit 2, loudly, naming what was missing.
const WT = fs.mkdtempSync(path.join(os.tmpdir(), 'sairncode-gates-wt-'));
fs.rmSync(WT, { recursive: true, force: true });   // git insists on creating it
{
  const add = spawnSync('git', ['-C', ROOT, 'worktree', 'add', '-q', '--detach', WT, 'HEAD'],
                        { encoding: 'utf8', timeout: 300000 });
  if (add.status !== 0) {
    console.log('COULD NOT CHECK: no git worktree, so NOTHING WAS MEASURED.');
    console.log('Zero failures here is not a sheet of caught mutations -- it is');
    console.log('a control that never ran. '
                + String(add.stderr || add.error || '').trim().slice(0, 300));
    process.exit(2);
  }
}
// The worktree is at HEAD; the mutations must apply to what is ON DISK NOW, or
// this control would silently stop covering uncommitted work -- which is exactly
// when a gate is most likely to be wrong.
UNDER_TEST.forEach((rel) => {
  fs.copyFileSync(path.join(ROOT, rel), path.join(WT, rel));
});

const SRC = path.join(WT, 'api', 'sd-data.js');
const APP = path.join(WT, 'sairncode.html');
const REGISTRY = path.join(WT, 'api/_resources/sairncode.js');
const SUITE = path.join(WT, 'tests', 'sairncode_gates.js');
const ORIGINAL = fs.readFileSync(SRC, 'utf8');
const APP_ORIGINAL = fs.readFileSync(APP, 'utf8');
const REGISTRY_ORIGINAL = fs.readFileSync(REGISTRY, 'utf8');

let n = 0, failures = 0;
function ok(cond, label, detail) {
  n += 1;
  if (cond) { console.log('  ok   ' + label); return; }
  failures += 1;
  console.log('  FAIL ' + label + (detail ? '\n       ' + detail : ''));
}
function section(s) { console.log('\n' + s); }

// The suite requires api/sd-data.js BY PATH from its own ROOT, which inside the
// worktree resolves to the worktree -- so the mutant is swapped in at that path
// there and the suite needs no knowledge that any of this is happening. The
// restore between mutations still matters (each mutation must run ALONE, or a
// verdict is a claim about two defects at once), but it is no longer the only
// thing standing between a killed process and a sabotaged tracked file.
// `target` defaults to the handler, so every pre-existing mutation is unchanged.
function runSuiteWith(source, target) {
  const file = target || SRC;
  fs.writeFileSync(file, source, 'utf8');
  try {
    const r = spawnSync(process.execPath, [SUITE], { cwd: WT, encoding: 'utf8',
                                                     timeout: 300000 });
    return { code: r.status, out: (r.stdout || '') + (r.stderr || '') };
  } finally {
    fs.writeFileSync(SRC, ORIGINAL, 'utf8');
    fs.writeFileSync(APP, APP_ORIGINAL, 'utf8');
    fs.writeFileSync(REGISTRY, REGISTRY_ORIGINAL, 'utf8');
  }
}
function sourceFor(m) {
  if (m.app) return APP_ORIGINAL;
  if (m.registry) return REGISTRY_ORIGINAL;
  return ORIGINAL;
}
function pathFor(m) {
  if (m.app) return APP;
  if (m.registry) return REGISTRY;
  return SRC;
}
function labelFor(m) {
  if (m.app) return 'sairncode.html';
  if (m.registry) return 'api/_resources/sairncode.js';
  return 'api/sd-data.js';
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
    // ANCHOR UPDATED 2026-09-14, and it went ANCHOR-0 first. The line used to
    // read `SC_TIER_A_WRITE_ROLES.indexOf(...)`; adding the per-resource
    // override changed it to `scAllowed.indexOf(...)`. That is the stale-anchor
    // failure this control's part-one arm exists for, caught on the run right
    // after the edit rather than months later on a probe reporting clean.
    name: 'the gate accepts ANY authenticated role, so a coder writes claims again',
    find: "          if (scAllowed.indexOf(scTierACaller.role) === -1) {",
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
  // ── THE TWO ROLE DECISIONS OF 2026-09-14 ─────────────────────────────────
  // Both were open questions when the gate shipped. A decision nothing can
  // fail on is a preference, so each is planted in both directions: reversed,
  // and implemented the OTHER way (by widening the shared constant), which is
  // the version that grants five resources nobody decided about.
  {
    name: 'the auditor override is deleted, so the role whose job is '
        + 'compliance cannot record a finding',
    find: "const SC_TIER_A_WRITE_ROLES_BY_RESOURCE = {\n  sc_compliance: ['admin', 'biller', 'auditor'],\n};",
    replace: "const SC_TIER_A_WRITE_ROLES_BY_RESOURCE = {};",
  },
  {
    name: 'the override is applied by WIDENING the shared list instead, '
        + 'granting an auditor five resources nobody decided about',
    find: "const SC_TIER_A_WRITE_ROLES = ['admin', 'biller'];",
    replace: "const SC_TIER_A_WRITE_ROLES = ['admin', 'biller', 'auditor'];",
  },
  {
    name: 'the 403 MESSAGE reverts to the shared constant, so a refusal on '
        + 'sc_compliance names the wrong set of roles',
    find: "                message: 'Only ' + scAllowed.join(' or ') + ' can change '",
    replace: "                message: 'Only ' + SC_TIER_A_WRITE_ROLES.join(' or ') + ' can change '",
  },
  {
    name: 'coder is admitted to sc_claims -- the other decision reversed',
    find: "const SC_TIER_A_WRITE_ROLES_BY_RESOURCE = {\n  sc_compliance: ['admin', 'biller', 'auditor'],\n};",
    replace: "const SC_TIER_A_WRITE_ROLES_BY_RESOURCE = {\n  sc_compliance: ['admin', 'biller', 'auditor'],\n  sc_claims: ['admin', 'biller', 'coder'],\n};",
  },
  {
    // ── RE-ANCHORED 2026-09-15, AND THE HARNESS IS WHAT REPORTED IT ───────
    // Both of these anchored on the SC_TIER_A_WRITE_GATED array literal in
    // api/sd-data.js. That literal is gone: the write gate is DERIVED from
    // SC_TIER_A_SOFT_DELETE_ONLY now, because the hand-written list was SIX
    // while the register said SEVEN, and sc_denial_events accepted a write
    // with no session at all until a live probe found it. Both arms reported
    // ANCHOR-0 on the next run -- the stale-anchor failure this harness exists
    // to make loud, caught minutes after the edit rather than months later on
    // a probe reporting clean.
    //
    // Re-anchored onto the registry, which is where the list lives now, with
    // SINGLE-LINE anchors because api/_resources/sairncode.js is CRLF in this
    // working tree while api/sd-data.js is LF.
    registry: true,
    name: 'sc_coded_items is gated too, so the coder exclusion becomes a '
        + 'lockout rather than a split',
    find: "  'sc_denial', 'sc_denial_events', 'sc_revenue'",
    replace: "  'sc_denial', 'sc_denial_events', 'sc_revenue', 'sc_coded_items'",
  },
  {
    registry: true,
    name: 'one resource is quietly dropped from the gated list',
    find: "  'sc_ar', 'sc_claims', 'sc_compliance', 'sc_credential_scope',",
    replace: "  'sc_claims', 'sc_compliance', 'sc_credential_scope',",
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
  // ── ITEM 97: THE THREE WAYS THE SOFT-DELETE FIX CAN BE UNDONE (2026-09-15) ─
  // Each of these leaves a handler that still passes every arm written before
  // today, which is why they are here rather than trusted to the existing 25.
  {
    registry: true,
    // A SINGLE-LINE ANCHOR ON PURPOSE. The first version of this spanned four
    // lines and reported ANCHOR-0 immediately: api/_resources/sairncode.js is
    // CRLF in this working tree while api/sd-data.js is LF, so a multi-line
    // anchor written with \n cannot match one of them. The harness reads bytes
    // from disk, which is the honest thing for it to do, so the anchor is the
    // part that has to not care -- and CLAUDE.md's own line-endings note is
    // about exactly this trap.
    name: 'REGISTRY: the per-resource test is defeated, so all 28 grant a '
        + 'destroying delete again -- the exact state item 97 found',
    find: "    map[name] = SC_TIER_A_SOFT_DELETE_ONLY.indexOf(name) === -1",
    replace: "    map[name] = [].indexOf(name) === -1",
  },
  {
    name: 'the READ stops excluding soft-deleted rows, so hiding a record is '
        + 'cosmetic and it returns on the next read',
    find: "        const scSoftFilter = scIsSoftDeleteOnly(resource) ? '&data->>_deleted_at=is.null' : '';",
    replace: "        const scSoftFilter = '';",
  },
  {
    name: "the handler's own SOFT_DELETE_ONLY refusal is removed, so a "
        + "'delete' that gets past the envelope destroys a Tier A record",
    find: "        if (scIsSoftDeleteOnly(resource)) {\n"
        + "          res.status(403).json({\n"
        + "            error: {\n"
        + "              code: 'SOFT_DELETE_ONLY',",
    replace: "        if (false) {\n"
        + "          res.status(403).json({\n"
        + "            error: {\n"
        + "              code: 'SOFT_DELETE_ONLY',",
  },
  {
    name: 'soft_delete loses its admin gate -- the verb is narrowed but anyone '
        + 'signed in can hide a claims record',
    find: "        const scSoftCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairncode');\n"
        + "        if (!scSoftCaller || scSoftCaller.role !== 'admin') {",
    replace: "        const scSoftCaller = verifySessionToken(tokenFromRequest(req), licHash, 'sairncode') || { role: 'admin', employee_id: 'x' };\n"
        + "        if (!scSoftCaller || scSoftCaller.role !== 'admin' && false) {",
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
      // The TOOL comes from the clone (it is not what is under test); the
      // DOCUMENT it reads comes from the worktree, which is why cwd is WT.
      const cb = spawnSync('python', [path.join(ROOT, 'tools', 'checkblocks.py'),
                                      'sairncode.html'],
                           { cwd: WT, encoding: 'utf8', timeout: 300000 });
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

  // ── 2. THE WORKTREE COPIES WERE RESTORED BETWEEN MUTATIONS ────────────────
  // Still asserted, because each mutation has to run ALONE: residue from one
  // would make the next one's verdict a claim about two defects at once.
  section('2. all three mutated files were restored byte for byte in the worktree');
  ok(fs.readFileSync(SRC, 'utf8') === ORIGINAL,
     'the worktree handler is byte-identical to how this run found it');
  ok(fs.readFileSync(APP, 'utf8') === APP_ORIGINAL,
     'and so is the worktree sairncode.html');
  ok(fs.readFileSync(REGISTRY, 'utf8') === REGISTRY_ORIGINAL,
     'and so is the worktree api/_resources/sairncode.js -- the file whose ONE '
     + 'list decides which records can be destroyed');

  // ── 3. THE CLONE WAS NEVER WRITTEN AT ALL ─────────────────────────────────
  // The control that the isolation is real, and the one the in-place version
  // could not have. "Restored" and "never touched" are different claims, and
  // only the second survives a killed process: the old design's guarantee lived
  // entirely inside a `finally` that a SIGKILL skips.
  section('3. THE CLONE\'S OWN FILES WERE NEVER WRITTEN -- not merely restored');
  UNDER_TEST.forEach((rel) => {
    ok(stamp(path.join(ROOT, rel)) === CLONE_BEFORE[rel],
       rel + ' in this clone is unchanged AND unwritten -- same bytes and the '
       + 'same mtime, so a write-then-restore would fail this too');
  });
  ok([SRC, APP, REGISTRY, SUITE].every((p) => p.indexOf(WT) === 0),
     'STRUCTURAL: every mutation target resolves inside the worktree, so the '
     + 'arms above cannot pass by luck -- there is no code path that writes the '
     + 'clone');
} finally {
  // The worktree goes whether or not anything above succeeded. `--force`
  // because it is deliberately dirty: the last mutation's restore may not have
  // run, and refusing to clean up a throwaway would leave the residue this
  // change exists to prevent.
  try {
    spawnSync('git', ['-C', ROOT, 'worktree', 'remove', '--force', WT],
              { encoding: 'utf8', timeout: 300000 });
    spawnSync('git', ['-C', ROOT, 'worktree', 'prune'], { encoding: 'utf8', timeout: 300000 });
  } catch (e) { /* prune is best-effort; the next run's mkdtemp is unique */ }
  try { fs.rmSync(WT, { recursive: true, force: true }); } catch (e) { /* gone already */ }
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) { /* temp */ }
}

console.log('\n' + (failures
  ? failures + ' OF ' + n + ' ASSERTIONS FAILED'
  : 'ALL ' + n + ' ASSERTIONS PASS'));
process.exit(failures ? 1 : 0);
