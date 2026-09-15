"""tests/run_completeness_probe.py -- item 38's shapes can be shown to FIRE on a
rule that is not applied everywhere, and to STAY QUIET on one that is.

    python tests/run_completeness_probe.py

THE FAILURE MODE THIS SUITE IS MOSTLY ABOUT IS OVER-REPORTING, because that is
the one this repo has a record of: a first draft that reports the whole tree
gets switched off within a day, and then the real finding inside it goes with
it. S3 produced FIVE candidates on the real tree before it was narrowed and
every single one was a false positive; four are excluded by rule and one by a
named acknowledgement. Section 3 pins each narrowing against the real file that
paid for it, so undoing one fails here rather than quietly returning the noise.

AND THE OTHER DIRECTION, which is the reason the narrowings are fixtures rather
than comments: a shape narrowed until it reports nothing is indistinguishable
from a shape that works. Every narrowing arm has a CONTROL beside it asserting
the real positive still fires.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import completeness_check as C                                   # noqa: E402
import dependency_graph as G                                     # noqa: E402

# THIS FILE IS THE CONTROL FOR completeness_check.py, declared rather than
# inferred. BOTH DIRECTIONS, and the silent half is the larger one here because
# over-reporting is this shape's recorded failure mode:
#   FIRES   2a/2c/3b/3d -- a rule consulted nowhere, a rule named only in a
#           comment, and a genuine fall-through dispatch are REPORTED.
#   SILENT  2b/3a/3c/3c2/3e -- a rule that IS consulted, a terminal else
#           covering one leftover, a predicate wearing a dispatch's clothes, a
#           single-arm test, and a two-value domain all stay quiet.
CONTROLS_FOR = ['completeness_check.py']

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


def fires(shape, src):
    fn = {'S1': C.s1_declared_never_consulted, 'S2': C.s2_one_direction_only,
          'S3': C.s3_fall_through}[shape]
    return bool(fn(G.strip_js(src), '<probe>'))


print('1. the blind lock')
check('1a  every synthetic source classifies as written', C.run_fixtures() == [],
      C.run_fixtures())
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'completeness_check.py'),
                    '--fixtures'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('1b  the lock runs on its own and passes', p.returncode == 0, 'exit %d' % p.returncode)
check('1c  the narrowings are stated as paid for by real false positives, not as taste',
      'paid for by a real false positive' in (p.stdout or ''))

print('2. S1 -- a rule that gates nothing')
check('2a  declared and never consulted FIRES',
      fires('S1', "const MANAGEMENT_ROLES = { owner: true };\nconst B = { a: 1 };\nuse(B);"))
check('2b  CONTROL: a rule that IS consulted stays quiet -- otherwise S1 reports '
      'every rule in the tree',
      not fires('S1', "const MANAGEMENT_ROLES = { owner: true };\nif (MANAGEMENT_ROLES[r]) ok();"))
check('2c  a rule named in a COMMENT is not a use -- the comment stripper runs first',
      fires('S1', "const MANAGEMENT_ROLES = { owner: true };\n// MANAGEMENT_ROLES is used below\nok();"))
check('2d  it found the real one: api/sen-portal.js MANAGEMENT_ROLES',
      any(f['shape'] == 'S1' and f['file'].endswith('sen-portal.js')
          and f['rule'] == 'MANAGEMENT_ROLES' for f in C.analyse()),
      [f['file'] + ':' + f['rule'] for f in C.analyse() if f['shape'] == 'S1'])

print('3. S3 -- the four narrowings, each against the file that paid for it')
# NARROWING 1: a terminal else covers ONE remaining member.
# api/_lib/roofing-agreements.js RESCISSION_UNITS.
check('3a  a terminal else covering ONE member stays quiet (RESCISSION_UNITS)',
      not fires('S3', "const RESCISSION_UNITS = ['business_days', 'calendar_days', 'hours'];\n"
                      "if (u === 'hours') { a(); } else if (u === 'calendar_days') { b(); } else { c(); }"))
check('3b  CONTROL: a terminal else does NOT excuse TWO unhandled members -- an '
      'else is for the leftover, not for half the domain',
      fires('S3', "const JOB_STATUSES = ['draft', 'open', 'closed', 'void'];\n"
                  "if (s === 'open') { a(); } else if (s === 'closed') { b(); } else { c(); }"))
# NARROWING 2: a single if with || is a predicate.
# api/_lib/wip-accounting.js DRAW_STATUSES.
check('3c  a single if with || is a PREDICATE, not a dispatch (DRAW_STATUSES) -- '
      'excluded by IF_HEAD, which only starts a chain on a BARE equality',
      not fires('S3', "const DRAW_STATUSES = ['draft', 'requested', 'approved', 'received', 'rejected'];\n"
                      "if (status === 'requested' || status === 'approved') { outstanding(); }"))
check('3c2 a SINGLE arm is a test, not a dispatch -- this is the arm the '
      'len(arms) < 2 rule actually does the work for. The first version of this '
      'suite credited the || exclusion to that rule, and a fixture that passes '
      'for a reason other than the stated one is one nobody can maintain',
      not fires('S3', "const JOB_STATUSES = ['draft', 'open', 'closed', 'void'];" + chr(10)
                      + "if (s === 'open') { a(); }"))
check('3d  CONTROL: the same domain with a real two-arm chain and no else FIRES',
      fires('S3', "const DRAW_STATUSES = ['draft', 'requested', 'approved', 'received', 'rejected'];\n"
                  "if (status === 'requested') { a(); } else if (status === 'approved') { b(); }"))
check('3e  a domain of two values is not a domain worth dispatching on',
      not fires('S3', "const PAIR_TYPES = ['a', 'b'];\n"
                      "if (t === 'a') { x(); } else if (t === 'b') { y(); }"))

print('4. ACKNOWLEDGEMENTS are visible, named, and cannot rot')
src = io.open(os.path.join(REPO, 'tools', 'completeness_check.py'), encoding='utf-8').read()
code = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('#'))
check('4a  every acknowledgement carries a written reason, not just a key',
      all(isinstance(v, str) and len(v) > 60 for v in C.ACKNOWLEDGED.values()),
      list(C.ACKNOWLEDGED))
check('4b  the acknowledged COUNT is printed on every run -- an acknowledgement '
      'nobody can see is a suppression',
      'ACKNOWLEDGED FALSE POSITIVES' in code)
check('4c  an acknowledgement whose finding no longer occurs is reported STALE, '
      'so the list cannot outlive what it excused', 'STALE ACKNOWLEDGEMENT' in code)
# The acknowledgement must still be ABOUT something. If the finding stops
# occurring the entry is stale; if the entry names a file that no longer exists
# it was never checked.
for shape, f, rule in C.ACKNOWLEDGED:
    check('4d  ' + f + ' still exists, so the acknowledgement is about a real file',
          os.path.exists(os.path.join(REPO, f.replace('/', os.sep))))

print('5. what the report claims about itself is true')
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'completeness_check.py')],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
out = r.stdout or ''
check('5a  a shape with no findings says it is a MEASURED zero, not a silence',
      'a measured zero, not a check that did not run' in out)
check('5b  ...and names how many files it ran over, so the zero has a denominator',
      'RAN over' in out and str(len(C.js_files())) in out)
check('5c  it says it is report-only, because a shape that cannot read intent '
      'has no business refusing a push', 'REPORT ONLY' in out)

# -- FIRES, ASSERTED ON THE TOOL'S OWN EXIT CODE --------------------------
# The internal-function arms above prove a SHAPE matches. This proves the
# CHECKER REPORTS: a real run with a real finding must exit 1, not print
# something and exit 0. tools/checker_control_check.py reads direction from
# parsed assertions and counts an exit-code comparison as evidence of firing,
# and it is right to -- a tool that finds something and exits 0 is one nothing
# downstream can chain.
print('6. FIRES and SILENT on the same entry point')
_r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'completeness_check.py')],
                    capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('6a  FIRES: with a real finding on the real tree the tool exits 1, so a '
      'caller can chain it -- printing a finding and exiting 0 is how a checker '
      'becomes decorative', _r.returncode == 1, 'exit %d' % _r.returncode)
check('6b  ...and the finding it exits 1 for is the real one, not any line that '
      'happens to be printed',
      'sen-portal.js' in (_r.stdout or '') and 'MANAGEMENT_ROLES' in (_r.stdout or ''))
_f = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'completeness_check.py'),
                     '--fixtures'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('6c  SILENT: with nothing to report the same tool exits 0 -- the pair is '
      'what makes 6a evidence rather than an observation',
      _f.returncode == 0, 'exit %d' % _f.returncode)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
