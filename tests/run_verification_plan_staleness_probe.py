"""tools/verification_plan_staleness_check.py must FIND drift, not just agree.

The plan it is built for DOES NOT EXIST YET on this machine -- searched the
repo, git history, all six clones and the filesystem -- so the tool's own
subject is absent and it exits 2 COULD NOT TELL when run bare. That is the
right behaviour and it is arm 1 below.

IT ALSO MEANS THE DERIVATION HALF WOULD SHIP UNEXERCISED, which is the state
this platform keeps recording (the consent doc's section 9 discloses two such
things already). So every other arm drives the tool against a SYNTHETIC plan
written here, in a throwaway directory, with known drift planted in it.

Run: python tests/run_verification_plan_staleness_probe.py
"""
CONTROLS_FOR = ['verification_plan_staleness_check.py']

import io
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True,
                      encoding='utf-8', errors='replace').stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'verification_plan_staleness_check.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run(args):
    r = subprocess.run([sys.executable, TOOL] + args, cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('verification-plan staleness -- the checker must find drift\n')

# ── ARM 1: the absent subject ─────────────────────────────────────────────
rc, out = run([])
check('with NO plan on disk it exits 2 COULD NOT TELL, not 0',
      rc == 2 and 'COULD NOT TELL' in out, 'rc=%s' % rc)
check('...and it NAMES every path it looked for',
      'verification-methodology-implementation-plan.md' in out)
check('...and it says nothing was checked',
      'NOTHING WAS CHECKED' in out)

rc, out = run(['--plan', 'docs/no-such-plan.md'])
check('an explicit --plan that does not exist is also exit 2',
      rc == 2 and 'does not exist' in out, 'rc=%s' % rc)

# A REAL commit subject from THIS repo, so the match arm below is not testing
# a string the tool was handed twice.
_, log = subprocess.run(['git', 'log', '-40', '--format=%s'], cwd=REPO,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace').stdout, None
real_subjects = [s.strip() for s in _.split('\n') if s.strip()]
assert real_subjects, 'fixture invalid: no commit subjects to anchor on'
REAL = real_subjects[0][:40]

tmp = tempfile.mkdtemp(prefix='sairn-planprobe-')
PLAN = os.path.join(tmp, 'plan.md')


def write(body):
    io.open(PLAN, 'w', encoding='utf-8', newline='').write(body)


try:
    # ── ARM 2: an empty plan is COULD NOT TELL, never clean ───────────────
    write('# A plan\n\nNothing here.\n')
    rc, out = run(['--plan', PLAN])
    check('a plan with ZERO item lines is exit 2, not a clean pass',
          rc == 2 and 'ZERO item lines' in out, 'rc=%s' % rc)

    # ── ARM 3: STALE-UNCLAIMED ────────────────────────────────────────────
    write('## Tier 0\n\n- unclaimed: rebuild the widget '
          '<!-- verify: commit=%s -->\n' % REAL)
    rc, out = run(['--plan', PLAN])
    check('an item marked UNCLAIMED whose commit has landed is reported',
          rc == 1 and 'STALE-UNCLAIMED' in out, 'rc=%s out=%s' % (rc, out[-200:]))
    check('...and the finding names the commit that contradicts it',
          REAL[:20].lower() in out.lower())

    # ── ARM 4: STALE-DONE, the direction that flatters ────────────────────
    write('## Tier 1\n\n- done: a thing that never happened '
          '<!-- verify: commit=zzz-no-such-commit-subject-zzz -->\n')
    rc, out = run(['--plan', PLAN])
    check('an item marked DONE with no matching commit is reported',
          rc == 1 and 'STALE-DONE' in out, 'rc=%s' % rc)

    # ── ARM 5: STALE-INFLIGHT ─────────────────────────────────────────────
    write('## Tier 2\n\n- in flight: something '
          '<!-- verify: claim=a-claim-nobody-holds -->\n')
    rc, out = run(['--plan', PLAN])
    check('an item marked IN FLIGHT with no active claim of that name is reported',
          rc == 1 and 'STALE-INFLIGHT' in out, 'rc=%s' % rc)

    # ── ARM 6: THE PAIRED POSITIVE ────────────────────────────────────────
    # Every arm above is satisfied by a tool that reports drift on everything.
    write('## Tier 0\n\n- done: a real thing <!-- verify: commit=%s -->\n' % REAL)
    rc, out = run(['--plan', PLAN])
    # 'STALE' alone matches the report's own TITLE (...STALENESS), so the
    # first version of this arm failed on the header rather than on a
    # finding. Asserting on the hyphenated finding prefix instead.
    check('an item marked DONE whose commit DID land is NOT reported',
          rc == 0 and 'STALE-' not in out, 'rc=%s out=%s' % (rc, out[-200:]))

    # ── ARM 7: the third state is counted, not filtered ───────────────────
    write('## Tier 0\n\n- unclaimed: described in prose with no marker at all\n'
          '- done: another one, also unmarked\n')
    rc, out = run(['--plan', PLAN])
    check('items with NO verify marker are counted as UNVERIFIABLE',
          'UNVERIFIABLE' in out and rc == 0, 'rc=%s' % rc)
    check('...and the count is 2, not 0 -- they are measured, not filtered out',
          'UNVERIFIABLE -- no marker at all    2' in out
          or 'UNVERIFIABLE -- no marker at all  ' in out and ' 2' in out)

    # ── ARM 8: the state word is read from the line, not assumed ──────────
    write('## Tier 0\n\n- open: a thing <!-- verify: commit=%s -->\n' % REAL)
    rc, out = run(['--plan', PLAN])
    check('"open" is read as unclaimed, so a landed commit still drifts',
          rc == 1 and 'STALE-UNCLAIMED' in out, 'rc=%s' % rc)

    # ── ARM 9: a plan with no state word at all is not invented ───────────
    write('## Tier 0\n\n- a thing with no state word <!-- verify: commit=%s -->\n'
          % REAL)
    rc, out = run(['--plan', PLAN])
    check('an item with a marker but NO state word is not given one',
          rc == 0 and 'STALE-' not in out, 'rc=%s' % rc)

finally:
    try:
        os.unlink(PLAN)
        os.rmdir(tmp)
    except OSError:
        pass

print('')
if fails:
    print('FAILED  run_verification_plan_staleness_probe: %d failed' % len(fails))
    sys.exit(1)
print('ok  run_verification_plan_staleness_probe: 0 failed')
print('')
print('NOTE: the plan this tool is FOR does not exist on this machine yet.')
print('Every arm above drives a synthetic one. So the derivation half is')
print('exercised and the REAL plan has still never been read -- which is')
print('exactly what arm 1 reports when the tool is run bare, and is the')
print('honest state rather than a green tick.')
sys.exit(0)
