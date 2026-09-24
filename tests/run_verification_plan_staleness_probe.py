"""tools/verification_plan_staleness_check.py must FIND drift, not just agree.

THE PLAN NOW EXISTS, since 2026-09-24. It was committed to
docs/verification-methodology-implementation-plan.md as a point-in-time
snapshot; before that it lived only in chat and the tool's subject was absent
from the repo, git history and all six clones. Arm 1 used to drive absence by
running the tool bare, and that stopped being true the moment the plan
landed -- two of its three assertions kept passing while testing something
else. Absence is now driven against a COPY of the tool in a throwaway tree,
which reaches the real search-miss branch; arm 1b reads the real plan.

THE REAL PLAN EXERCISES EXACTLY ONE BRANCH. It describes its state in prose
and carries no `verify:` markers, so it is "items present, none checkable" --
exit 2. Every other branch is driven against a SYNTHETIC plan written here,
in a throwaway directory, with known drift planted in it, because otherwise
the derivation half would ship unexercised -- the state this platform keeps
recording (the consent doc's section 9 discloses two such things already).

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

# ── ARM 1: the absent subject, DRIVEN WHERE IT IS REALLY ABSENT ───────────
# THIS ARM WAS REWRITTEN 2026-09-24 AND THE REWRITE IS THE POINT. Until that
# day the plan existed nowhere, so a BARE run WAS the absent-plan case and
# this arm drove it that way. The plan is now committed at
# docs/verification-methodology-implementation-plan.md, so a bare run no
# longer tests absence at all -- it opens the real plan. Two of the three
# assertions still passed after the subject moved (exit 2 for an unrelated
# reason, and the path named because it is the path it OPENED), which is the
# shape where a control keeps reporting ok while testing something else.
#
# The tool resolves REPO from its own __file__, so absence cannot be reached
# by argument while the plan is in place. It is reached by putting a COPY of
# the tool in a throwaway tree that has no docs/ plan, which exercises the
# real search-miss branch rather than a stand-in for it.
_abs_root = tempfile.mkdtemp(prefix='sairn-plan-absent-')
os.makedirs(os.path.join(_abs_root, 'tools'))
_abs_tool = os.path.join(_abs_root, 'tools', os.path.basename(TOOL))
io.open(_abs_tool, 'w', encoding='utf-8', newline='').write(
    io.open(TOOL, encoding='utf-8', newline='').read())
_r = subprocess.run([sys.executable, _abs_tool], cwd=_abs_root,
                    capture_output=True, text=True, encoding='utf-8',
                    errors='replace')
rc, out = _r.returncode, (_r.stdout or '') + (_r.stderr or '')
check('with NO plan on disk it exits 2 COULD NOT TELL, not 0',
      rc == 2 and 'COULD NOT TELL' in out, 'rc=%s' % rc)
check('...and it NAMES every path it looked for',
      'verification-methodology-implementation-plan.md' in out)
check('...and it says nothing was checked',
      'NOTHING WAS CHECKED' in out)

rc, out = run(['--plan', 'docs/no-such-plan.md'])
check('an explicit --plan that does not exist is also exit 2',
      rc == 2 and 'does not exist' in out, 'rc=%s' % rc)

# ── ARM 1b: THE REAL PLAN, as it actually sits in this repo ───────────────
# Not a fixture. The committed plan describes its state entirely in prose, so
# it has item lines and no verify markers -- which is the defect found by
# running the tool on it the day it landed: zero checkable items returned
# exit 0, indistinguishable to any caller from "checked them all and they
# agree". If somebody later adds markers to the plan this arm changes answer,
# and it asserts on the TOOL's vocabulary rather than on a fixed count so it
# reports that honestly instead of going red.
rc, out = run([])
_real_checkable = 'COULD NOT TELL' not in out
check('the REAL committed plan is measured, and a plan with items but NO '
      'checkable one is exit 2, never exit 0',
      (rc == 0 or rc == 1) if _real_checkable else (rc == 2),
      'rc=%s checkable=%s' % (rc, _real_checkable))

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
    # EXPECTATION CHANGED 2026-09-24, from rc == 0 to rc == 2. This fixture
    # has two items and NOT ONE marker, so nothing is measured -- and until
    # that day the tool returned 0, which reads to any caller as a pass. The
    # arm was asserting the printed column while accepting the exit code that
    # contradicted it.
    write('## Tier 0\n\n- unclaimed: described in prose with no marker at all\n'
          '- done: another one, also unmarked\n')
    rc, out = run(['--plan', PLAN])
    check('items with NO verify marker are counted as UNVERIFIABLE',
          'UNVERIFIABLE' in out and rc == 2, 'rc=%s' % rc)
    check('...and the count is 2, not 0 -- they are measured, not filtered out',
          'UNVERIFIABLE -- no marker at all    2' in out
          or 'UNVERIFIABLE -- no marker at all  ' in out and ' 2' in out)
    check('...and NOT ONE checkable item is COULD NOT TELL, not a clean pass',
          rc == 2 and 'COULD NOT TELL' in out and 'NOT a pass' in out,
          'rc=%s' % rc)

    # ── ARM 7b: THE PAIRED CONTROL -- a PARTIAL measurement is NOT 2 ──────
    # Without this, arm 7 is satisfied by a tool that returns 2 whenever any
    # unverifiable item exists, which would make every real plan permanently
    # could-not-tell and is the opposite failure. One marked item that agrees
    # with the repo plus one unmarked item is exit 0, with the unmarked one
    # still counted and the denominator stated.
    write('## Tier 0\n\n- done: a real thing <!-- verify: commit=%s -->\n'
          '- unclaimed: described in prose with no marker at all\n' % REAL)
    rc, out = run(['--plan', PLAN])
    check('a PARTIAL measurement -- one checkable, one not -- is exit 0, not 2',
          rc == 0 and 'COULD NOT TELL' not in out, 'rc=%s' % rc)
    check('...and it still says how many were NOT measured, so the 0 is not '
          'read as out of 2',
          'were NOT measured at all' in out)

    # ── ARM 7c: a PARTIAL measurement that finds drift is still exit 1 ────
    write('## Tier 0\n\n- unclaimed: a real thing <!-- verify: commit=%s -->\n'
          '- done: described in prose with no marker at all\n' % REAL)
    rc, out = run(['--plan', PLAN])
    check('a PARTIAL measurement that DOES find drift is exit 1, not 2',
          rc == 1 and 'STALE-UNCLAIMED' in out, 'rc=%s' % rc)

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
print('NOTE: the plan this tool is FOR now EXISTS -- committed 2026-09-24 at')
print('docs/verification-methodology-implementation-plan.md, which is what')
print('arm 1b reads. Most arms above still drive a SYNTHETIC plan, because')
print('the real one is a point-in-time snapshot that describes its state in')
print('prose and carries no verify markers, so it exercises exactly one')
print('branch: items present, none checkable, exit 2. Until somebody marks')
print('items in it, the derivation half is exercised by fixtures only, and')
print('that is a limit of this control rather than a property of the tool.')
sys.exit(0)
