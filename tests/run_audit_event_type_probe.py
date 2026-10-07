# OWNER: hank
"""run_audit_event_type_probe.py -- drive tools/audit_event_type_check.py from
OUTSIDE, in a scratch tree, and prove it fires and refuses for the right reasons.

    python tests/run_audit_event_type_probe.py
    python tests/run_audit_event_type_probe.py --selftest

EXIT 0 every arm holds, 1 an arm failed, 2 COULD NOT RUN.

── WHY A PROBE WHEN THE TOOL HAS A --selftest ───────────────────────────────
The selftest calls `findings()` and `emitted_in()` directly. This runs the
PROGRAM, in a tree it built, and reads the exit code -- so it covers the wiring
between them: argument handling, the scan over real directories, and the
COULD-NOT-RUN path. A unit-level selftest cannot fail on a broken `main()`, and
`main()` is what a push gate or a hook would call.

── THE REGRESSION IT LOCKS ──────────────────────────────────────────────────
This whole tool exists because `tests/provisioning_attribution.js` was green
while six write paths recorded nothing: a stubbed `fetch` cannot refuse a row,
so the CHECK constraint was invisible. Arm B is the one that would have caught
that on the day -- a planted event_type outside the list must FLAG.

**IT FAILS WITHOUT THE TOOL.** Arm A0 asserts the program exists and runs at
all; before `tools/audit_event_type_check.py` existed every arm here errored on
a missing file, which is the loud direction.

── READ-ONLY AGAINST THE LIVE CLONE ─────────────────────────────────────────
Every arm builds its own tiny tree under the system temp dir and runs the tool
with that tree as the repo. The live clone is never written to and never read as
the subject. The scratch tree is removed in a `finally`.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'audit_event_type_check.py')
CRITERIA_VERSION = '2026-10-07.1'

DDL_TMPL = """
create table if not exists public.zz_probe_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  event_type text not null check (event_type in (
%s
  )),
  detail jsonb
);
"""
AUDIT_LIB = """
const AUDIT_TABLES = { zz_probe_audit_log: true };
const DEFAULT_AUDIT_TABLE = 'zz_probe_audit_log';
async function writeAuditLog(u, k, o) { return true; }
module.exports = { writeAuditLog };
"""
HANDLER_TMPL = """
const { writeAuditLog } = require('./_lib/audit');
const AUDIT_TABLE = 'zz_probe_audit_log';
module.exports = async (req, res) => {
  await writeAuditLog(U, K, { event_type: '%s', table: AUDIT_TABLE });
};
"""


def build(root, allowed, emitted):
    """A minimal repo: sql/ with one CHECK list, api/ with one emitter."""
    os.makedirs(os.path.join(root, 'sql'))
    os.makedirs(os.path.join(root, 'api', '_lib'))
    os.makedirs(os.path.join(root, 'tools'))
    io.open(os.path.join(root, 'sql', 'zz.sql'), 'w', encoding='utf-8',
            newline='\n').write(
        DDL_TMPL % ',\n'.join("    '%s'" % v for v in allowed))
    io.open(os.path.join(root, 'api', '_lib', 'audit.js'), 'w',
            encoding='utf-8', newline='\n').write(AUDIT_LIB)
    io.open(os.path.join(root, 'api', 'zz-handler.js'), 'w', encoding='utf-8',
            newline='\n').write(HANDLER_TMPL % emitted)
    shutil.copyfile(TOOL, os.path.join(root, 'tools',
                                       'audit_event_type_check.py'))


def run(root, extra=None):
    cmd = [sys.executable, os.path.join(root, 'tools',
                                        'audit_event_type_check.py')]
    if extra:
        cmd += extra
    p = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=120)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def main(argv):
    print('AUDIT event_type CHECK PROBE -- criteria %s' % CRITERIA_VERSION)
    if not os.path.isfile(TOOL):
        print('COULD NOT RUN: %s does not exist. Nothing was driven -- this is '
              'NOT "the checker is fine".' % TOOL)
        return 2
    npass = nfail = 0

    def ck(label, cond, extra=''):
        nonlocal npass, nfail
        if cond:
            npass += 1
            print('  ok   ' + label)
        else:
            nfail += 1
            print('  FAIL ' + label)
            if extra:
                print('       ' + str(extra)[:400])

    base = tempfile.mkdtemp(prefix='aet-probe-')
    try:
        # A0 -- the program runs at all.
        r0 = os.path.join(base, 'a0')
        os.makedirs(r0)
        build(r0, ['allowed_one'], 'allowed_one')
        rc, out = run(r0)
        ck('A0. the PROGRAM runs and exits 0 on a clean pair. Without this arm '
           'every arm below could be passing on a crash, and before this tool '
           'existed they all errored on a missing file',
           rc == 0, 'exit=%d %s' % (rc, out[-200:]))

        # B -- the regression: a planted value outside the list must FLAG.
        r1 = os.path.join(base, 'b')
        os.makedirs(r1)
        build(r1, ['allowed_one', 'allowed_two'], 'not_in_the_check')
        rc, out = run(r1)
        ck('B1. an event_type OUTSIDE the CHECK list makes the program EXIT 1. '
           'THIS IS THE ARM THAT WOULD HAVE CAUGHT THE REAL DEFECT: six write '
           'paths recorded nothing for a day while their suite was green, '
           'because a stubbed fetch cannot refuse a row',
           rc == 1, 'exit=%d' % rc)
        ck('B2. ...and the output NAMES the rejected value and the table. '
           '"something is rejected somewhere" is not actionable',
           'not_in_the_check' in out and 'zz_probe_audit_log' in out,
           out[-300:])

        # C -- the paired positive, same tree shape.
        r2 = os.path.join(base, 'c')
        os.makedirs(r2)
        build(r2, ['allowed_one', 'allowed_two'], 'allowed_two')
        rc, out = run(r2)
        ck('C1. the SAME tree with an allowed value exits 0. Without this arm a '
           'program that exited 1 unconditionally would satisfy B1',
           rc == 0, 'exit=%d %s' % (rc, out[-200:]))

        # D -- the third state, both halves.
        r3 = os.path.join(base, 'd')
        os.makedirs(r3)
        build(r3, ['allowed_one'], 'allowed_one')
        shutil.rmtree(os.path.join(r3, 'sql'))
        rc, out = run(r3)
        ck('D1. with sql/ ABSENT the program exits 2 COULD NOT RUN, not 0. A '
           'missing population is not a clean verdict, and folding it into one '
           'is PR 1.11',
           rc == 2 and 'COULD NOT RUN' in out, 'exit=%d %s' % (rc, out[-200:]))

        r4 = os.path.join(base, 'e')
        os.makedirs(r4)
        build(r4, ['allowed_one'], 'allowed_one')
        io.open(os.path.join(r4, 'api', '_lib', 'audit.js'), 'w',
                encoding='utf-8', newline='\n').write(
            '// no DEFAULT_AUDIT_TABLE here at all\n')
        rc, out = run(r4)
        ck('D2. with DEFAULT_AUDIT_TABLE missing the program exits 2 rather '
           'than guessing which table an untargeted call lands in. The first '
           'version of this sweep bucketed four real files as "unresolved" and '
           'left them OUT of the comparison -- that hid six of the twelve '
           'rejected values',
           rc == 2 and 'COULD NOT RUN' in out, 'exit=%d %s' % (rc, out[-200:]))

        # F -- a table with no CHECK must not become a permanent false positive.
        r5 = os.path.join(base, 'f')
        os.makedirs(r5)
        build(r5, ['allowed_one'], 'anything_at_all')
        p = os.path.join(r5, 'sql', 'zz.sql')
        s = io.open(p, encoding='utf-8').read()
        s = s.replace("""event_type text not null check (event_type in (
    'allowed_one'
  ))""", 'event_type text not null')
        io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
        rc, out = run(r5)
        ck('F1. a table with NO event_type CHECK yields NO finding and exits 0 '
           '-- it cannot be violated. sv_audit_log is this case live, and '
           'treating absence as a violation would make it a permanent false '
           'positive',
           rc == 0, 'exit=%d %s' % (rc, out[-250:]))

        rc, out = run(r2, ['--selftest'])
        ck('G1. the tool\'s own --selftest exits 0 when driven as a program, '
           'not just when its functions are called',
           rc == 0, 'exit=%d' % rc)
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print('')
    print('%d passed, %d failed' % (npass, nfail))
    return 1 if nfail else 0


if __name__ == '__main__':
    sys.exit(main([a for a in sys.argv[1:] if a != '--selftest']))
