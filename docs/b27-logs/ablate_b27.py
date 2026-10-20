# docs/b27-logs/ablate_b27.py
# OWNER: cody   batch b27   2026-10-19
#
# THE CONCEPT: an arm that cannot be made to fail is not evidence, so every
#   gate this batch changed is MUTATED in a disposable copy of api/ and the arm
#   that is supposed to notice must go RED -- and a named CONTROL arm, outside
#   the mutation's blast radius, must stay GREEN, because an arm that goes red
#   because the whole copy is broken is attributable to nothing.
#
#   python docs/b27-logs/ablate_b27.py            # every leg
#   python docs/b27-logs/ablate_b27.py --only A1
#
# Exit: 0 every leg behaved as expected - 1 a leg did not - 2 COULD NOT RUN
#
# NOTHING IS WRITTEN IN THE LIVE CLONE. Every leg copies api/ into a
# tempfile.mkdtemp() and mutates the copy; `git status --porcelain` is captured
# before and after the whole run and compared, so "the live tree was never
# written" is an ASSERTION rather than an intention.
#
# ── THREE HARNESS DEFECTS THIS IS WRITTEN AGAINST, ALL PAID FOR ───────────
# b24: the harness wrote the subject first and copied api/_lib OVER it, so for
#      a subject inside api/ the leg silently drove the DISK copy. -> the
#      library goes down FIRST and the written file is READ BACK.
# b26: a file-wide `replace(INSERT,'')` removed the FIRST of 150 byte-identical
#      insertions, thousands of lines from the subject, and would have reported
#      green arms over an untouched subject. -> every mutation asserts its
#      anchor occurs EXACTLY ONCE before replacing it.
# b26: an ablation's control arm was inside the blast radius, so it went red
#      with the subject and proved nothing. -> each leg names its own control.

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.getcwd()
ONLY = None
if '--only' in sys.argv:
    ONLY = sys.argv[sys.argv.index('--only') + 1]

if not os.path.isdir(os.path.join(REPO, 'api')):
    print('COULD NOT RUN: no api/ directory here. Nothing was verified.')
    sys.exit(2)


def git_status():
    return subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                          capture_output=True, text=True).stdout


BEFORE = git_status()

# Each leg: (id, suite, file to mutate (relative to api/), anchor, replacement,
#            arm that MUST go red, control arm that MUST stay green, why)
LEGS = (
    ('A1',
     'api/sd-data-alf-isolation.test.js',
     'sd-data.js',
     "const ALF_MANAGEMENT_ROLES = roleSet({ owner: true, billing: true });",
     "const ALF_MANAGEMENT_ROLES = roleSet({ owner: true, billing: true, office_manager: true });",
     r'^  FAIL alf_facility \[ROLE\] office_manager ',
     r'^  ok   alf_facility \[ROLE\] caregiver ',
     'office_manager is admitted to the alf_facility management set. The NEW '
     'arm must go red and the FOUR pre-existing non-management arms must stay '
     'green -- which is what makes the red attributable to the token rather '
     'than to a broken copy.'),
    ('A2',
     'api/sd-data-alf-isolation.test.js',
     '_lib/auth.js',
     "  sairncare: ['owner', 'nursing', 'med_aide', 'caregiver', 'billing', 'activities', 'office_manager'],",
     "  sairncare: ['owner', 'nursing', 'med_aide', 'caregiver', 'billing', 'activities', 'office_manager', 'volunteer'],",
     r'^  FAIL alf_facility \[ROLE-all\] ',
     r'^  ok   alf_facility \[ROLE\] office_manager ',
     'an EIGHTH sairncare role is declared and no arm drives it. The '
     'completeness arm must go red -- this is the leg that proves it closes '
     'the class rather than only recording today.'),
    ('R1',
     'api/_lib/routes.test.js',
     '_resources/routes.js',
     "  visibleToAllApps: true,\n",
     "",
     r'^  FAIL D1\. ',
     r'^  ok   D2b\. ',
     'the cross-app visibility flag is removed, which is the state the feature '
     'shipped in. D1 must go red and the shared-resource control D2b, outside '
     'the blast radius, must stay green.'),
    # ── L1's SUBJECT ARM IS P1, AND THE FIRST SPELLING GOT THAT WRONG ──────
    # It expected S1 or S2 to go red. They do not, and the reason is a finding
    # rather than a harness bug: S1 and S2 are POLICY arms driven on decide()
    # directly, and dropping the argument at the CALL SITE cannot move them.
    #
    # AND NO DISPATCHER-OBSERVABLE ARM CAN MOVE EITHER, which is the honest
    # state of this wiring: `prepare` is not a declared extraAction for any
    # leg_ resource, so checkEnvelope() answers 400 before the role gate runs
    # (arms V1/V2 measure exactly that). So the fifth argument is wired and its
    # effect is NOT yet observable end to end -- the only things that move are
    # the call shape (P1, on comment-stripped source) and the settings read
    # (S1b). THIS ABLATION THEREFORE PROVES P1 HAS TEETH AND SAYS OUT LOUD
    # THAT BEHAVIOUR-LEVEL ATTRIBUTION IS BLOCKED ON THE VERB DECLARATION,
    # which is routed rather than claimed.
    ('L1',
     'api/b27-leg-settings.test.js',
     'sd-data.js',
     "legRoles.decide(resource, legSess.role, action, null, legHome)",
     "legRoles.decide(resource, legSess.role, action)",
     r'^  FAIL P1\. ',
     r'^  ok   S0\. ',
     'the fifth argument is dropped at the call site, which is the deliberate '
     'omission b18 recorded and b27 closes. P1 -- which reads the call shape '
     'off comment-stripped source -- must go red, and S0 must stay green '
     'because an absent settings row and a missing fifth argument produce the '
     'SAME narrow default. S0 green in both legs IS the compatibility '
     'guarantee this change had to keep.'),
)


def run(suite, api_dir, cwd):
    env = dict(os.environ)
    env['SAIRN_BYPASS_LOG'] = os.path.join(tempfile.gettempdir(),
                                           'b27-ablate-bypass.jsonl')
    r = subprocess.run(['node', suite], cwd=cwd, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', env=env,
                       timeout=300)
    return (r.stdout or '') + (r.stderr or ''), r.returncode


results = []
for leg, suite, target, anchor, repl, red_re, green_re, why in LEGS:
    if ONLY and leg != ONLY:
        continue
    if not os.path.isfile(os.path.join(REPO, suite)):
        results.append((leg, 'COULD NOT RUN', suite + ' does not exist'))
        print('  %-3s COULD NOT RUN -- %s does not exist' % (leg, suite))
        continue
    tmp = tempfile.mkdtemp(prefix='b27-ablate-')
    try:
        # LIBRARY DOWN FIRST. b24's defect, asserted away rather than avoided.
        shutil.copytree(os.path.join(REPO, 'api'), os.path.join(tmp, 'api'))
        # The suite under test may live outside api/ -- copy what it needs.
        for d in ('tests', 'tools', 'docs', 'sql'):
            src = os.path.join(REPO, d)
            if os.path.isdir(src) and suite.startswith(d + '/'):
                shutil.copytree(src, os.path.join(tmp, d))
        tgt = os.path.join(tmp, 'api', target)
        if not os.path.isfile(tgt):
            results.append((leg, 'COULD NOT RUN', 'api/' + target + ' absent'))
            print('  %-3s COULD NOT RUN -- api/%s absent in the copy' % (leg, target))
            continue
        src_txt = io.open(tgt, encoding='utf-8').read().replace('\r\n', '\n')
        n = src_txt.count(anchor)
        if n != 1:
            # b26's defect: a mutation applied to one of N identical instances
            # is a control that proves nothing and reads as one that proves
            # everything. THIRD STATE, never folded into a pass or a fail.
            results.append((leg, 'COULD NOT RUN',
                            'the anchor occurs %d times in api/%s, not once'
                            % (n, target)))
            print('  %-3s COULD NOT RUN -- anchor occurs %d times in api/%s, '
                  'not once, so the mutation would be ambiguous'
                  % (leg, n, target))
            continue
        want = src_txt.replace(anchor, repl)
        io.open(tgt, 'w', encoding='utf-8', newline='').write(want)
        back = io.open(tgt, encoding='utf-8', newline='').read()
        if back != want or (repl == '' and anchor in back):
            results.append((leg, 'COULD NOT RUN', 'the copy did not read back'))
            print('  %-3s COULD NOT RUN -- the mutated copy did not read back '
                  'as written' % leg)
            continue
        # Drive the suite IN THE COPY, so every require() resolves there.
        out, rc = run(suite, os.path.join(tmp, 'api'), tmp)
        red = re.search(red_re, out, re.M) is not None
        green = re.search(green_re, out, re.M) is not None
        verdict = 'AS EXPECTED' if (red and green) else 'NOT AS EXPECTED'
        results.append((leg, verdict,
                        'subject red: %s  control green: %s  (exit %s)'
                        % (red, green, rc)))
        print('  %-3s %-15s subject red: %-5s control green: %-5s  exit %s'
              % (leg, verdict, red, green, rc))
        if verdict != 'AS EXPECTED':
            print('       MUTATION : api/%s' % target)
            print('       WHY      : %s' % why)
            print('       ' + out.strip().replace('\n', '\n       ')[-1400:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

AFTER = git_status()
print('')
print('ABLATION -- b27, %d leg(s)' % len(results))
for leg, v, d in results:
    print('  %-3s %-15s %s' % (leg, v, d))
print('')
if BEFORE != AFTER:
    print('REFUSED: THE LIVE TREE CHANGED DURING THIS RUN, so no leg above is '
          'trustworthy -- a mutation reached the clone.')
    print('  before: ' + repr(BEFORE))
    print('  after : ' + repr(AFTER))
    sys.exit(1)
print('THE LIVE TREE WAS NEVER WRITTEN -- `git status --porcelain` is '
      'byte-identical before and after, asserted rather than intended.')
bad = [r for r in results if r[1] != 'AS EXPECTED']
if bad:
    print('')
    print('%d leg(s) did NOT behave as expected:' % len(bad))
    for leg, v, d in bad:
        print('  %-3s %-15s %s' % (leg, v, d))
    sys.exit(1)
print('Every leg: the subject arm went RED and its named control stayed GREEN.')
sys.exit(0)
