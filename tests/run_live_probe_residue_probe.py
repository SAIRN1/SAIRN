"""Control pair for tools/live_probe_residue_audit.py.

Run:  python tests/run_live_probe_residue_probe.py

CONTROLS_FOR = ['tools/live_probe_residue_audit.py']
LIVE_PROBE_CLASS = 'FIXTURE'

Four directions, because this checker has four ways to be wrong and a control
that only plants one defect is evidence about one of them:

  a writing probe with NO class declared          -> must be REPORTED
  a VERIFICATION probe with no audit-licence guard -> must be REPORTED
  a VERIFICATION probe with no residue declared    -> must be REPORTED
  a VERIFICATION probe naming a residue path that
      DOES NOT EXIST                               -> must be REPORTED
  and a fully compliant one                        -> must be SILENT

THE LAST ONE IS THE ARM THAT MATTERS MOST. A checker that reports every writing
probe passes the first four and is useless -- it would have reported the two
roofing probes that were already doing the right thing since 2026-09-02.

── THE FIXTURES ARE SYNTHETIC, AND THE REAL DEFECT IS NAMED ────────────────
The incident this checker exists for -- a probe rule written to LAW-TEST-2026
that DELETE was revoked on -- cannot be replanted, because the fix was to gate
the probe rather than to change a file that can be restored. So these are
temporary files written into tools/ and removed. That is weaker evidence than a
restored real defect and is said rather than implied.
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'live_probe_residue_audit.py')
PLANT_REL = 'tools/_zz_planted_live_probe.py'
PLANT = os.path.join(REPO, PLANT_REL)

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2
passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:400])


def run():
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.run([sys.executable, TOOL], cwd=REPO, env=env,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def git(*a):
    return subprocess.run(['git'] + list(a), cwd=REPO, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')


# A live probe that WRITES. The host string and the action literal are what the
# checker reads; nothing here makes a request.
def fixture(declaration, action='write'):
    return (
        '"""A planted live probe for tests/run_live_probe_residue_probe.py."""\n'
        'import json\n'
        + declaration +
        'ENDPOINT = "https://sairn.vercel.app/api/sd-data"\n'
        'def go(key):\n'
        '    return json.dumps({"action": "%s", "resource": "zz_probe",\n'
        '                       "payload": {}})\n' % action)


CASES = [
    ('a writing probe with NO class declared', '',
     'declares no LIVE_PROBE_CLASS'),
    ('a VERIFICATION probe with no audit-licence guard',
     "LIVE_PROBE_CLASS = 'VERIFICATION'\n"
     "LIVE_PROBE_RESIDUE = 'none -- nothing is written'\n",
     'never calls require_audit_licence'),
    ('a VERIFICATION probe with no residue declared',
     "LIVE_PROBE_CLASS = 'VERIFICATION'\n"
     "def _g(k):\n"
     "    from audit_licence import require_audit_licence\n"
     "    return require_audit_licence(k)\n",
     'declares no LIVE_PROBE_RESIDUE'),
    ('a VERIFICATION probe naming a residue path that does not exist',
     "LIVE_PROBE_CLASS = 'VERIFICATION'\n"
     "LIVE_PROBE_RESIDUE = 'sql/zz_this_file_does_not_exist.sql -- cleanup'\n"
     "def _g(k):\n"
     "    from audit_licence import require_audit_licence\n"
     "    return require_audit_licence(k)\n",
     'does not exist'),
]

COMPLIANT = (
    "LIVE_PROBE_CLASS = 'VERIFICATION'\n"
    "LIVE_PROBE_RESIDUE = 'none -- the write is an upsert on a fixed id, overwritten by the next run'\n"
    "def _g(k):\n"
    "    from audit_licence import require_audit_licence\n"
    "    return require_audit_licence(k)\n")

# ── OBLIGATION 4: A TEARDOWN MUST BE ASSERTED, NOT INFERRED FROM ITS REPLY ───
# The residue obligations answer "where does what you left go". They do not ask
# whether a probe that CLEANS UP checked that the cleanup happened.
# tools/sc_tier_a_write_gate_live_probe.py read its deleted ROWS back and did not
# read its deactivated CREDENTIALS back -- it asserted `set_active -> 200` and
# stopped, and a 200 is the endpoint's account of itself. On 2026-09-28 a
# different cleanup on a different licence answered 400 and printed OK. A
# credential left live is the worse residue of the two: it is a way in, on a
# licence that outlives the run.
#
# DECLARED, NEVER INFERRED -- the same decision the class field already makes and
# argues for. No source scan can tell a real read-back from a variable named
# `roster`, and the three inference models tried for the equivalent question
# elsewhere were all wrong within an hour.
TEARDOWN_UNDECLARED = (
    "LIVE_PROBE_CLASS = 'VERIFICATION'\n"
    "LIVE_PROBE_RESIDUE = 'none -- the subject is deactivated at the end of the run'\n"
    "def _g(k):\n"
    "    from audit_licence import require_audit_licence\n"
    "    return require_audit_licence(k)\n")

TEARDOWN_DECLARED = (
    TEARDOWN_UNDECLARED +
    "LIVE_PROBE_TEARDOWN = 'the roster is read back after the loop and both "
    "subjects must show active == false; an unreadable roster fails'\n")

if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/live_probe_residue_audit.py is not on disk. This '
          'control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

print('CONTROL PAIR -- tools/live_probe_residue_audit.py\n')

print('BASELINE -- the shipped tree')
base_rc, base_out = run()
ok(base_rc == EXIT_CLEAN,
   'every real writing probe is compliant, so the tool exits 0 (got %d)' % base_rc,
   base_out[-500:])
ok('VERIFICATION' in base_out and 'LOADER' in base_out,
   'and it SEES both classes -- a tool that found nothing would also exit 0, '
   'which is the always-passing checker this repo has measured')
ok('CHECKED / UNIVERSE' in base_out,
   'and it prints checked/universe, so a silently narrowed scan is visible')

if os.path.exists(PLANT):
    os.remove(PLANT)

try:
    for label, decl, expect in CASES:
        print('\nDIRECTION -- %s' % label)
        with io.open(PLANT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(fixture(decl))
        git('add', '-N', PLANT_REL)
        rc, out = run()
        ok(rc == EXIT_FINDING, 'the tool exits 1 (got %d)' % rc, out[-400:])
        ok(PLANT_REL in out, 'and NAMES the file',
           '\n'.join(l for l in out.split('\n') if 'zz_planted' in l)[:300])
        ok(expect in out, 'and says WHY: %r' % expect,
           '\n'.join(l for l in out.split('\n') if 'zz_planted' in l)[:300])

    print('\nDIRECTION -- a VERIFICATION probe that TEARS DOWN and does not say '
          'how it checked')
    with io.open(PLANT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(fixture(TEARDOWN_UNDECLARED, action='set_active'))
    git('add', '-N', PLANT_REL)
    rc, out = run()
    ok(rc == EXIT_FINDING, 'the tool exits 1 (got %d)' % rc, out[-400:])
    ok('LIVE_PROBE_TEARDOWN' in out and PLANT_REL in out,
       'and names the file and the missing declaration',
       '\n'.join(l for l in out.split('\n') if 'zz_planted' in l)[:300])

    print('\nDIRECTION -- the SAME probe with the declaration must be SILENT')
    with io.open(PLANT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(fixture(TEARDOWN_DECLARED, action='set_active'))
    git('add', '-N', PLANT_REL)
    rc, out = run()
    ok(rc == EXIT_CLEAN,
       'declaring how the teardown is checked clears it (exit %d) -- without this '
       'arm the obligation would be a checker that flags every cleanup there is'
       % rc,
       '\n'.join(l for l in out.split('\n') if 'zz_planted' in l)[:400])

    print('\nDIRECTION -- a probe that writes but NEVER tears down is not asked')
    with io.open(PLANT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(fixture(TEARDOWN_UNDECLARED, action='write'))
    git('add', '-N', PLANT_REL)
    rc, out = run()
    ok(rc == EXIT_CLEAN,
       'the obligation fires on the TEARDOWN action, not on writing at all '
       '(exit %d). The same declaration text is missing in both directions, so '
       'this separates the trigger from the text' % rc,
       '\n'.join(l for l in out.split('\n') if 'zz_planted' in l)[:400])

    print('\nDIRECTION -- a FULLY COMPLIANT writing probe must be SILENT')
    with io.open(PLANT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(fixture(COMPLIANT))
    git('add', '-N', PLANT_REL)
    rc, out = run()
    ok(rc == EXIT_CLEAN,
       'THE ARM THAT MATTERS MOST: a compliant probe is NOT reported (exit %d) -- '
       'a checker that flags every writing probe would have flagged the two '
       'roofing ones that have been correct since 2026-09-02' % rc,
       '\n'.join(l for l in out.split('\n') if 'zz_planted' in l or '!' in l)[:400])
    ok(PLANT_REL in out and 'VERIFICATION' in out,
       'and it is still LISTED as VERIFICATION -- silent is not the same as blind')
finally:
    if os.path.exists(PLANT):
        os.remove(PLANT)
    git('rm', '--cached', '-q', '--ignore-unmatch', PLANT_REL)

print('\nAFTER -- the tree is restored')
rc, out = run()
ok(rc == base_rc and PLANT_REL not in out,
   'the verdict is back to the baseline (%d) and the fixture is gone' % base_rc,
   'rc=%d' % rc)
st = git('status', '--porcelain', PLANT_REL)
ok(st.stdout.strip() == '',
   'and nothing is left staged -- a probe that leaves a file behind has changed '
   'the repo it was measuring', st.stdout[:200])

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
