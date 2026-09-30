"""The control on tools/mech_gate_live_probe.py: a live check that CREATES A ROW
and does not RECORD it must fail.

    python tests/run_mech_gate_live_probe_probe.py

NO NETWORK. Every arm drives the tool's recorder and its cross-check directly, or
runs the tool's own --selftest. A control that needed the live endpoint could only
run when the endpoint was up, and the thing being checked is bookkeeping.

── THE INCIDENT ────────────────────────────────────────────────────────────
2026-09-29. The mech_docs gate was verified live by an ad-hoc script, which left
two rows on MECH-PINNACLE-2026 -- a demo-facing licence -- on tables with no
DELETE grant. They needed a human in the SQL editor. `require_audit_licence`
would have refused the key outright and was not imported, and
`tools/live_probe_residue_audit.py` could not see the run because its universe is
TRACKED files.

── THE ARM THAT MATTERS, AND WHY IT IS NOT SELF-REFERENTIAL ────────────────
`finish()` takes the number of writes the ENDPOINT observed and refuses when the
recorder saw fewer. A recorder that counted only its own calls could never detect
a write that bypassed it -- it would report "1 row created, here is the SQL" and be
confidently incomplete. So the arm below records ONE row, claims TWO were
observed, and requires COULD NOT RUN with no SQL printed.
"""
import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

TOOL = os.path.join(REPO, 'tools', 'mech_gate_live_probe.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: %s is missing, so nothing below was checked. This is '
          'not a pass.' % TOOL)
    sys.exit(EXIT_COULD_NOT_RUN)

import mech_gate_live_probe as P                                # noqa: E402

passed = failed = 0


def ck(name, cond, detail=''):
    global passed, failed
    print(('  ok   ' if cond else '  FAIL ') + name)
    if cond:
        passed += 1
    else:
        failed += 1
        if detail:
            print('         ' + str(detail).replace('\n', '\n         ')[:500])


def capture(fn):
    """Run fn with stdout and stderr captured, returning (rc, out, err)."""
    so, se = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        rc = fn()
        return rc, sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.stdout, sys.stderr = so, se


print('tools/mech_gate_live_probe.py: a created row that is not recorded must '
      'fail, and the SQL must name the real column\n')

# ── 1. THE DECLARATIONS THE PLATFORM AUDITOR READS ──────────────────────────
src = io.open(TOOL, encoding='utf-8').read()
ck('1. it declares LIVE_PROBE_CLASS = VERIFICATION, so '
   'tools/live_probe_residue_audit.py can judge it at all',
   "LIVE_PROBE_CLASS = 'VERIFICATION'" in src)
ck('1b. it declares LIVE_PROBE_RESIDUE naming the tables, the id shape and the '
   'dated record', 'LIVE_PROBE_RESIDUE' in src
   and 'mech_checks' in src and 'live-residue' in src)
ck('1c. it calls require_audit_licence BEFORE any request -- the line whose '
   'absence produced the 2026-09-29 residue',
   'require_audit_licence(' in src
   and src.index('require_audit_licence(') < src.index('def call('))

# ── 2. THE ID COLUMN IS THE REAL ONE ────────────────────────────────────────
# The removal SQL that was pushed on 2026-09-29 named `entry_id`, which does not
# exist on any of these four tables. A removal script that names a column the
# table does not have deletes nothing and, in anything that swallows the error,
# reads as a clean sweep.
ck('2. the id-column map matches the schema: check_id / takeoff_id / doc_id / '
   'quote_id, and entry_id appears nowhere in it',
   P.ID_COL == {'mech_quotes': 'quote_id', 'mech_checks': 'check_id',
                'mech_docs': 'doc_id', 'mech_takeoffs': 'takeoff_id'},
   P.ID_COL)

r = P.Residue('t', 'MECH-AUDIT-2026')
r.created('mech_takeoffs', 'ZZ-T-1')
sql = '\n'.join(r.sql())
ck('2b. the generated SQL names takeoff_id and never entry_id',
   'takeoff_id' in sql and 'entry_id' not in sql, sql[:300])
ck('2c. the licence hash is DERIVED in SQL, not pasted as a hex literal',
   "digest('MECH-AUDIT-2026', 'sha256')" in sql, sql[:200])
ck('2d. and it is select, then delete, then confirm -- in that order',
   sql.index('select') < sql.index('delete from')
   < sql.rindex('count(*) as remaining'), sql[:200])

try:
    r.created('sd_slabs', 'X')
    ck('2e. a table with no known id column is REFUSED, rather than recorded '
       'with a guessed one', False)
except KeyError:
    ck('2e. a table with no known id column is REFUSED, rather than recorded '
       'with a guessed one', True)

# ── 3. THE KNOWN-BAD CONTROL: A CREATED ROW THAT WAS NOT RECORDED ───────────
tmp = tempfile.mkdtemp(prefix='residue-probe-')
real_dir = P.RESIDUE_DIR
P.RESIDUE_DIR = tmp
try:
    good = P.Residue('t', 'MECH-AUDIT-2026')
    good.created('mech_checks', 'ZZ-T-2')
    rc, out, err = capture(lambda: good.finish('2026-01-01', 1))
    ck('3. CONTROL: recorded 1, endpoint observed 1 -- CLEAN, the record is '
       'written and the SQL printed',
       rc == EXIT_CLEAN and 'delete from public.mech_checks' in out
       and os.path.isfile(good.record_path('2026-01-01')),
       'rc=%s err=%s' % (rc, err[:200]))

    bad = P.Residue('t', 'MECH-AUDIT-2026')
    bad.created('mech_checks', 'ZZ-T-3')
    rc2, out2, err2 = capture(lambda: bad.finish('2026-01-02', 2))
    ck('3b. KNOWN-BAD: recorded 1 but the endpoint observed 2 -- COULD NOT RUN '
       '(%d), not clean and not a finding' % EXIT_COULD_NOT_RUN,
       rc2 == EXIT_COULD_NOT_RUN, 'rc=%s' % rc2)
    ck('3c. ...and it prints NO removal SQL, because SQL that covers one of two '
       'rows is worse than none -- it reads as complete',
       'delete from' not in out2, out2[-300:])
    ck('3d. ...and it writes NO residue record, so nothing on disk claims the '
       'run was accounted for',
       not os.path.isfile(bad.record_path('2026-01-02')))
    ck('3e. ...and it says WHY on stderr, naming both counts',
       '1 were RECORDED' in err2 and '2 write(s)' in err2, err2[:300])

    # The zero case is NOT the same as the unrecorded case and must not be
    # confused with it: a run that wrote nothing is clean and says so.
    none = P.Residue('t', 'MECH-AUDIT-2026')
    rc3, out3, _ = capture(lambda: none.finish('2026-01-03', 0))
    ck('3f. a run that created NOTHING is CLEAN and says there is nothing to '
       'remove, which is a different answer from an unrecorded write',
       rc3 == EXIT_CLEAN and 'nothing to' in out3, out3[-200:])
finally:
    P.RESIDUE_DIR = real_dir
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

# ── 4. THE TOOL'S OWN SELFTEST RUNS AND PASSES ──────────────────────────────
p = subprocess.run([sys.executable, TOOL, '--selftest'], cwd=REPO,
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
ck('4. the tool\'s --selftest runs with no network and exits 0 (exit %d)'
   % p.returncode, p.returncode == EXIT_CLEAN,
   (p.stdout or '') + (p.stderr or ''))

# ── 5. A NON-AUDIT LICENCE IS REFUSED BEFORE ANY REQUEST ────────────────────
# Driven through the real entry point, because the guard being IMPORTED is not the
# same fact as the guard being CALLED on the path that writes.
p = subprocess.run([sys.executable, TOOL, '--key', 'MECH-PINNACLE-2026'],
                   cwd=REPO, capture_output=True, text=True, encoding='utf-8',
                   errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
ck('5. THE 2026-09-29 KEY ITSELF: --key MECH-PINNACLE-2026 is REFUSED with '
   'COULD NOT RUN (exit %d) before a single request' % p.returncode,
   p.returncode == EXIT_COULD_NOT_RUN
   and 'not an audit licence' in (p.stderr or ''),
   (p.stdout or '') + (p.stderr or ''))

# ── 6. THE PLATFORM AUDITOR CAN ACTUALLY SEE THIS TOOL ──────────────────────
# THREE SEPARATE WAYS THIS TOOL DECLARED ITSELF CORRECTLY AND WAS STILL NOT
# JUDGED, each found by RUNNING the auditor rather than by reading it:
#   * the write action was passed positionally into a helper, so
#     action_literals() saw no `action = 'write'` and the tool was absent from
#     the writing-probe list entirely -- the audit said 9 writers, not 10;
#   * LIVE_PROBE_RESIDUE was a parenthesised multi-line concatenation, and
#     RESIDUE_RE matches ONE quoted literal, so the declaration existed and
#     counted as absent;
#   * the residue declaration did not START with a real path, and the audit takes
#     residue.split()[0] and requires that file to exist.
#
# A TOOL THAT DECLARES ITSELF TO A CHECKER THAT CANNOT FIND IT DECLARES ITSELF TO
# NOBODY, which is the same failure as the 2026-09-29 script being untracked, one
# level in. So this arm asserts the AUDITOR'S VERDICT, not the presence of the
# declarations -- the declarations were present all three times.
p = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'live_probe_residue_audit.py')],
                   cwd=REPO, capture_output=True, text=True, encoding='utf-8',
                   errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
audit_out = (p.stdout or '') + (p.stderr or '')
ck('6. the residue auditor LISTS this tool as a VERIFICATION writer, rather than '
   'not seeing it at all',
   'mech_gate_live_probe.py' in audit_out
   and 'VERIFICATION tools/mech_gate_live_probe.py' in audit_out,
   audit_out[-700:])
ck('6b. ...with guard=yes and a residue declaration it ACCEPTS',
   'guard=yes  residue=docs/live-residue/README.md' in audit_out,
   audit_out[-700:])
_mine = [l for l in audit_out.split('\n')
         if l.strip().startswith('!') and 'mech_gate_live_probe' in l]
ck('6c. ...and the auditor raises NO finding about this tool', not _mine,
   '\n'.join(_mine))
ck('6d. and the standing residue path the declaration names FIRST is a real '
   'file, because that is the token the auditor checks',
   os.path.isfile(os.path.join(REPO, 'docs', 'live-residue', 'README.md')))

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
