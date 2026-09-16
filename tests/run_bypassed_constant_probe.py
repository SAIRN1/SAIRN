
# REQUIREMENT: a constant declared as the single source is not bypassed by a literal
#   elsewhere, because a second copy is what makes two answers possible
#
#!/usr/bin/env python
"""tests/run_bypassed_constant_probe.py

Run:  python tests/run_bypassed_constant_probe.py

CONTROLS_FOR = ['bypassed_constant_check.py']

THIS CHECKER IS GREEN ON THE REAL TREE, because the finding that produced it was
fixed in the same commit. A checker nobody has watched fire looks exactly like a
codebase where the problem never happens, so every arm here plants its own case
and drives scan() directly -- no file on disk is touched.

THE ARM THAT MATTERS MOST IS B2. sairnbiz declares the EMPLOYER and EMPLOYEE
FICA halves separately and deliberately -- different money, identical
percentage -- so each declaration SEES THE OTHER as a literal of its own value.
The first version of this criterion reported both, forever, against a file with
nothing wrong with it. Two correct constants must not accuse each other.
"""
import io
import os
import subprocess
import sys

CONTROLS_FOR = ['bypassed_constant_check.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import bypassed_constant_check as B            # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '  ' + str(detail)[:300]))
    if not cond:
        fails.append(name)


print('bypassed constant check -- it must FIRE, and it must not cry wolf\n')

print('A. it fires on the real shape')
hits = B.scan("var SB_TAX_FICA_RATE = 0.0765;\nvar x = gross * 0.0765;\n")
check('A1 a declared decimal bypassed by its own literal is a finding',
      len(hits) == 1 and hits[0][0] == 'SB_TAX_FICA_RATE', hits)
check('A2 ...and it counts HOW MANY sites bypass it, not merely that one does',
      hits and hits[0][2] == 1, hits)
hits = B.scan("var RATE_X = 0.0765;\nvar a = g * 0.0765;\nvar b = h * 0.0765;\n")
check('A3 two bypasses are counted as two', hits and hits[0][2] == 2, hits)

# THE FIXTURE NAMES MUST MATCH THE TOOL'S OWN DECLARATION PATTERN, or a
# negative arm passes against an empty result and proves nothing. These arms
# were written as `var R = 0.0765` -- one character, never matched by
# [A-Z][A-Z0-9_]{3,40} -- so A3 went red and B1 and B6 sat GREEN on the same
# mistake, which is the arm-passing-for-the-wrong-reason shape exactly.
check('A4 the fixture name is one the tool actually recognises, or every '
      'negative arm below passes vacuously',
      len(B.scan("var RATE_X = 0.0765;\nvar a = g * 0.0765;\n")) == 1,
      'RATE_X is not matched by DECL -- fix the fixture, not the tool')

print('\nB. it does not cry wolf')
check('B1 a constant nothing bypasses is silent',
      B.scan("var RATE_X = 0.0765;\nvar a = g * RATE_X;\n") == [], 'fired on clean code')
# THE ARM THAT MATTERS. Two correct constants at the same value must not report
# each other -- this is the real sairnbiz shape and the first version failed it.
hits = B.scan("var SB_TAX_FICA_RATE = 0.0765;\n"
              "var SB_EMPLOYEE_FICA_RATE = 0.0765;\n"
              "var a = g * SB_TAX_FICA_RATE;\n")
check('B2 two DECLARATIONS sharing a value do not accuse each other -- the '
      'employer and employee FICA halves are different money at the same rate',
      hits == [], hits)
hits = B.scan("var SB_TAX_FICA_RATE = 0.0765;\n"
              "var SB_EMPLOYEE_FICA_RATE = 0.0765;\n"
              "var a = g * 0.0765;\n")
check('B3 ...and a REAL bypass alongside them is still caught, so B2 is not '
      'just a blanket exemption', len(hits) == 2 and hits[0][2] == 1, hits)
check('B4 an INTEGER constant is out of scope by design -- 30 occurs '
      'everywhere for unrelated reasons',
      B.scan("var TRIAL_DAYS = 30;\nvar a = b * 30;\n") == [], 'integer flagged')
check('B5 a two-digit decimal is out of scope too -- 0.22 is not distinctive',
      B.scan("var RATE = 0.22;\nvar a = b * 0.22;\n") == [], '0.22 flagged')
check('B6 a longer number that merely CONTAINS the value is not a match',
      B.scan("var RATE_X = 0.0765;\nvar a = 10.07651;\n") == [], 'substring matched')

print('\nC. the real tree, end to end')
p = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'bypassed_constant_check.py')],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO)
out = (p.stdout or '') + (p.stderr or '')
flat = ' '.join(out.split())
check('C1 it is GREEN today, because the finding it was built for was fixed',
      p.returncode == 0, out[-400:])
check('C2 ...and it scanned a plausible number of files rather than none',
      'files scanned            : 2' in out or 'files scanned            : 1' in out,
      out[:300])
check('C3 it states its scope on a CLEAN run, so green is not read as more '
      'than it is', 'SCOPE, STATED' in out, out[:600])
check('C4 ...naming the integer blind spot as deliberate, with the measurement',
      'from 2 findings to 60' in flat, out[:900])
check('C5 ...and that api/ belongs to completeness_check.py',
      'completeness_check.py' in out, out[:900])

print('\nD. it fails CLOSED rather than reporting clean')
src = io.open(os.path.join(REPO, 'tools', 'bypassed_constant_check.py'),
              encoding='utf-8').read()
check('D1 a missing jscomments is COULD NOT RUN, not a scan without comment '
      'stripping -- these files discuss their own rates in prose',
      'COULD NOT RUN: tools/jscomments.py' in src, 'the import guard is gone')
check('D2 ...and it says a run without stripping is a DIFFERENT check, not a '
      'weaker one', 'it is a different one' in ' '.join(src.split()),
      'the reasoning is no longer stated')
check('D3 too few .html files is a broken reader, not a platform with no apps',
      'broken reader, not a platform with no app pages' in src,
      'the floor guard is gone')

print('\n%s  run_bypassed_constant_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
