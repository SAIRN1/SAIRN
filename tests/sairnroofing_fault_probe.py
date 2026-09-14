"""SAIRNroofing's claim-gate and unprovisioned suites must DENY.

Run: python tests/sairnroofing_fault_probe.py

── GATE 4, ON THE VERTICAL WITH THE MOST SUITES AND NO PROBE ────────────────
`docs/MASTER-PLAN.md` gate 4: the guards are known to DENY, not merely to pass.
SAIRNroofing read 0 suites until 2026-09-14 -- an attribution artefact, since
27 of them exist and none is named `sairnroofing*` -- and it has had zero fault
probes the whole time.

── TWO SUBJECTS, CHOSEN BECAUSE THEY FAIL IN OPPOSITE DIRECTIONS ───────────
  * THE CLAIM ASSIGNMENT GATE. `rfAuth.ownsRow()` replaced a hand-written
    expression at SEVEN branches of api/sd-data.js, and api/rf-auth.js's own
    header names duplicated role logic as SAIRNsenior's root cause. Breaking it
    WIDENS access: a crew member sees somebody else's claim. That is the
    security direction.
  * THE PROVISIONED FLAG. `api/sd-data.js` answers an absent table with
    `200 {ok:true,data:[],provisioned:false}` -- deliberately soft, because the
    FLAG carries the answer. A call site that ignores it prints "No bonding
    letter recorded" over a table that was never created: a statement about the
    contractor's SURETY POSITION that is not true. That is the honesty
    direction, and it is the one nobody thinks to test, because the screen
    looks completely normal.

── EVERY ARM IS A DEFECT THIS APP REALLY HAD ───────────────────────────────
The hand-written gate really was at seven branches; both provisioned call sites
really did ignore the flag, and the suites exist because of it.

── EVERY ARM RUNS IN A THROWAWAY WORKTREE, never this clone ────────────────
Subject files are copied from the WORKING TREE, not taken from HEAD, so a suite
change made to close a hole this probe finds is visible to it. That trap was hit
for real on tests/sairnbiz_fault_probe.py's first run.

── EVERY ANCHOR IS COUNTED, NOT MERELY FOUND ───────────────────────────────
`once()` asserts exactly one match and refuses rather than letting `replace()`
pick which of seven branches to damage -- which on this subject is not a
hypothetical worry.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
AUTH = os.path.join('api', 'rf-auth.js')
HTML = 'sairnroofing.html'
GATE = os.path.join('tests', 'roofing_claim_gate_single_source.js')
PROV = os.path.join('tests', 'roofing_unprovisioned_is_not_empty.js')
SUBJECTS = (AUTH, HTML, GATE, PROV)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(wt, suite):
    r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('sairnroofing -- the claim gate and the provisioned flag must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-rf-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    for _rel in SUBJECTS:
        shutil.copyfile(os.path.join(REPO, _rel), os.path.join(wt, _rel))

    ORIG = {}
    for rel in (AUTH, HTML):
        ORIG[rel] = io.open(os.path.join(wt, rel), encoding='utf-8', newline='').read()

    def write(rel, text):
        io.open(os.path.join(wt, rel), 'w', encoding='utf-8', newline='').write(text)

    def restore():
        for rel, txt in ORIG.items():
            write(rel, txt)

    def once(rel, needle):
        n = ORIG[rel].count(needle)
        assert n == 1, ('fixture invalid: %r matches %d places in %s, not 1 -- '
                        'widen the anchor rather than letting replace() pick'
                        % (needle[:60], n, rel))
        return needle

    def arm(label, suite, edits):
        try:
            for rel, old, new in edits:
                write(rel, ORIG[rel].replace(once(rel, old), new, 1))
            rc, out = run(wt, suite)
            check(label + '  [' + os.path.basename(suite) + ']', rc != 0,
                  'the suite still PASSED against the mutation\n' + out[-300:])
        finally:
            restore()

    # ── ARM 0: THE CONTROLS, FIRST ─────────────────────────────────────────
    for suite in (GATE, PROV):
        rc, out = run(wt, suite)
        check('the shipped tree passes %s' % os.path.basename(suite), rc == 0,
              out[-400:])

    # ── 1. THE ASSIGNMENT GATE WIDENS ──────────────────────────────────────
    # ownsRow() stops being a predicate about assignment and becomes "yes".
    # Every one of the seven branches that imports it opens at once.
    arm('a gate that answers TRUE for everybody is caught', GATE,
        [(AUTH, '  return !!(row && row.assigned_employee_id === session.employee_id);',
          '  return true;')])

    # ── 2. ...AND THE OTHER DIRECTION, WHICH IS NOT THE SAME BUG ───────────
    # Refusing everybody is a broken app rather than a breach, and a suite that
    # only catches the permissive direction would let it ship.
    arm('a gate that answers FALSE for everybody is caught too', GATE,
        [(AUTH, '  if (seesAllRows(session)) return true;', '  if (false) return true;')])

    # ── 3. A MISSING ROW STOPS BEING A REFUSAL ─────────────────────────────
    # `row` is undefined when the record does not exist. Reading a missing row
    # as owned is how a delete-then-read becomes an authorisation bypass.
    arm('a MISSING row treated as owned is caught', GATE,
        [(AUTH, '  return !!(row && row.assigned_employee_id === session.employee_id);',
          '  return !row || row.assigned_employee_id === session.employee_id;')])

    # ── 4. THE BONDING PANEL LIES ABOUT SURETY AGAIN ───────────────────────
    # `provisioned:false` ignored -> "No bonding letter recorded." A contractor
    # reads that as "you have no bond". The truth was "the table was never
    # created", and the two are not close.
    arm('the bonding panel ignoring provisioned:false is caught', PROV,
        [(HTML, '        if(cd.provisioned===false){\n          rfBonding=null;',
          '        if(false){\n          rfBonding=null;')])

    # ── 5. AND THE SAFETY PANEL ABOUT HAZARD ASSESSMENTS ───────────────────
    # "No hazard assessments recorded" on a job-hazard-analysis panel reads as
    # "none were needed", which is the opposite of "we cannot tell you".
    arm('the safety panel ignoring provisioned:false is caught', PROV,
        [(HTML, '        if(jd.provisioned===false){\n          rfJhas=[];',
          '        if(false){\n          rfJhas=[];')])

    # ── 6. THE TWO PANELS TOGETHER ─────────────────────────────────────────
    # Both at once, because a suite that catches either alone might be keying
    # on a total rather than on each site.
    arm('both call sites ignoring the flag at once is caught', PROV,
        [(HTML, '        if(cd.provisioned===false){\n          rfBonding=null;',
          '        if(false){\n          rfBonding=null;'),
         (HTML, '        if(jd.provisioned===false){\n          rfJhas=[];',
          '        if(false){\n          rfJhas=[];')])

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    # Every arm restores in a `finally`. A restore that silently failed would
    # leave every later arm passing against a mutated file, and the probe would
    # report green while testing a corrupted state -- the one failure mode that
    # defeats this whole method.
    ok_all = all(io.open(os.path.join(wt, rel), encoding='utf-8',
                         newline='').read() == ORIG[rel] for rel in ORIG)
    check('both subject files are byte-identical to the working tree after '
          'every arm', ok_all,
          'a restore did not land -- later arms tested a mutated file')
    for suite in (GATE, PROV):
        rc, out = run(wt, suite)
        check('...and %s is green again on it' % os.path.basename(suite),
              rc == 0, out[-300:])
finally:
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)
    print('\n  the throwaway worktree is gone: %s' % (not os.path.isdir(wt)))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
