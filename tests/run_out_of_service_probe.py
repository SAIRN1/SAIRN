"""Control pair for tools/out_of_service_register.py.

Run:  python tests/run_out_of_service_probe.py

CONTROLS_FOR = ['tools/out_of_service_register.py']
LIVE_PROBE_CLASS = 'FIXTURE'

Six directions. The register has six ways to be wrong and a control that plants
one is evidence about one of them:

  an entry missing a required field          -> REPORTED
  an entry older than max_age_days           -> REPORTED
  the count risen above the ceiling          -> REPORTED
  THE KNOWN-BAD: an out-of-service probe with
      NO register entry                      -> REPORTED
  an absent register                         -> COULD NOT RUN (exit 2, not 1)
  the real, fully declared register          -> SILENT

THE LAST TWO ARE THE ARMS THAT MATTER. A checker that reports every register is
useless; and one that treats a MISSING register as clean is the failure this
whole tool exists to prevent, one level up -- an absent register is not an empty
one.

THE REGISTER IS RESTORED BYTE-IDENTICAL and that is asserted, not assumed: this
probe rewrites a real tracked file, and a control that leaves the thing it was
measuring altered has changed the answer.
"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'out_of_service_register.py')
REG_REL = 'docs/out-of-service-controls.json'
REG = os.path.join(REPO, REG_REL)
PLANT_REL = 'tools/_zz_planted_oos_probe.py'
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


def run(*extra):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.run([sys.executable, TOOL] + list(extra), cwd=REPO, env=env,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def git(*a):
    return subprocess.run(['git'] + list(a), cwd=REPO, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')


def write_reg(obj):
    with io.open(REG, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


if not os.path.isfile(TOOL) or not os.path.isfile(REG):
    print('COULD NOT RUN: the tool or its register is not on disk. This control '
          'tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

ORIGINAL = io.open(REG, encoding='utf-8', newline='').read()

print('CONTROL PAIR -- tools/out_of_service_register.py\n')

print('BASELINE -- the real register')
rc, out = run()
ok(rc == EXIT_CLEAN, 'the shipped register is clean (exit %d)' % rc, out[-400:])
ok('OUT OF SERVICE  : 4' in out,
   'and the COUNT IS PUBLISHED on a clean run -- a number only visible on '
   'failure is one nobody watches')
ok('NOT A COMPLETE LIST' in out,
   'and it says what it cannot see, rather than implying completeness')

try:
    base = json.loads(ORIGINAL)

    print('\nDIRECTION -- an entry missing a required field')
    bad = json.loads(ORIGINAL)
    bad['entries'][0].pop('unblocked_by')
    write_reg(bad)
    rc, out = run()
    ok(rc == EXIT_FINDING, 'exits 1 (got %d)' % rc, out[-300:])
    ok('unblocked_by' in out and 'silence wearing a status' in out,
       'and names the missing field with the reason it matters')

    print('\nDIRECTION -- an entry aged past max_age_days')
    old = json.loads(ORIGINAL)
    old['entries'][0]['out_since'] = '2026-01-01'
    write_reg(old)
    rc, out = run('--today', '2026-09-28')
    ok(rc == EXIT_FINDING, 'exits 1 (got %d)' % rc, out[-300:])
    ok('past the stated limit' in out and 'blocked on' in out,
       'and names the age, the limit and who it is blocked on')

    print('\nDIRECTION -- the count risen above the ceiling')
    many = json.loads(ORIGINAL)
    extra = json.loads(json.dumps(many['entries'][0]))
    while len(many['entries']) <= many['ceiling']:
        extra = json.loads(json.dumps(extra))
        extra['id'] = extra['id'] + '-x%d' % len(many['entries'])
        many['entries'].append(extra)
    write_reg(many)
    rc, out = run('--today', '2026-09-28')
    ok(rc == EXIT_FINDING, 'exits 1 (got %d)' % rc, out[-300:])
    ok('THE COUNT HAS RISEN' in out,
       'and says raising the ceiling is a decision made out loud, not a side '
       'effect of adding an entry')

    print('\nDIRECTION -- THE KNOWN-BAD: an out-of-service probe with NO entry')
    write_reg(base)
    with io.open(PLANT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(
            '"""A planted out-of-service probe for the control pair."""\n'
            'import os\n'
            "LIVE_PROBE_CLASS = 'VERIFICATION'\n"
            "LIVE_PROBE_RESIDUE = 'none'\n"
            "LICENSE = os.environ.get('ZZQ_LICENSE', '')\n"
            'def go():\n'
            '    from audit_licence import require_audit_licence\n'
            '    return require_audit_licence(LICENSE)\n')
    git('add', '-N', PLANT_REL)
    rc, out = run('--today', '2026-09-28')
    ok(rc == EXIT_FINDING,
       'THE ARM THAT CANNOT BE GAMED BY EDITING THE REGISTER: a guarded '
       'VERIFICATION probe whose audit licence does not exist, with no entry, '
       'exits 1 (got %d)' % rc, out[-400:])
    ok(PLANT_REL in out and 'NO entry in the register' in out,
       'and NAMES the file and the reason',
       '\n'.join(l for l in out.split('\n') if 'zz_planted' in l)[:300])
finally:
    io.open(REG, 'w', encoding='utf-8', newline='').write(ORIGINAL)
    if os.path.exists(PLANT):
        os.remove(PLANT)
    git('rm', '--cached', '-q', '--ignore-unmatch', PLANT_REL)

print('\nDIRECTION -- an ABSENT register is COULD NOT RUN, never clean')
tmp = REG + '.probe-moved'
os.rename(REG, tmp)
try:
    rc, out = run()
    ok(rc == EXIT_COULD_NOT_RUN,
       'exits 2, not 0 and not 1 (got %d) -- an absent register is not an empty '
       'one, it is a question nobody can answer' % rc, out[-300:])
finally:
    os.rename(tmp, REG)

print('\nAFTER -- the tree is restored')
ok(io.open(REG, encoding='utf-8', newline='').read() == ORIGINAL,
   'the register is byte-identical to how it started')
rc, out = run()
ok(rc == EXIT_CLEAN and 'OUT OF SERVICE  : 4' in out,
   'and the verdict is back to the baseline', 'rc=%d' % rc)
st = git('status', '--porcelain', PLANT_REL)
ok(st.stdout.strip() == '', 'and nothing is left staged', st.stdout[:200])

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
