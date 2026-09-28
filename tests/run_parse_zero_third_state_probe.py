#!/usr/bin/env python
"""The control for tools/parse_zero_third_state_check.py -- BOTH directions.

    python tests/run_parse_zero_third_state_probe.py

Exit 0 all arms pass, 1 any arm fails.

── WHY BOTH DIRECTIONS, EVERY TIME ─────────────────────────────────────────
This tool's whole subject is a checker that reports CLEAN because it read
nothing. A control that only proves it FIRES would be satisfied by a tool that
reports every variable in the repo; a control that only proves it is SILENT
would be satisfied by a tool that reports nothing at all -- which is exactly the
failure mode under audit, one level up. So every shape below is checked in both
directions, and the criteria sabotage in section A asserts the sabotage APPLIED
before asserting anything about behaviour, because a patch that silently failed
leaves every arm green for ever.

── AND THE FALSE POSITIVES THE FIRST REAL RUN PAID FOR ─────────────────────
The first run reported 28 findings and most were not this defect: `bad =
run_fixtures()`, `res = scan()`, `found = classify()`. Those functions all read a
corpus somewhere inside, but what they RETURN is a findings list, and an empty
findings list is a clean sweep -- the correct answer. Section C pins that
distinction, because a checker whose findings are mostly wrong is one nobody runs
twice, and the fix for it is the kind that quietly turns into "report nothing".
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'parse_zero_third_state_check.py')
CONTROLS_FOR = ['parse_zero_third_state_check.py']

import parse_zero_third_state_check as Z                          # noqa: E402

_pass, _fail = 0, 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


def section(t):
    print('\n' + t)


def run(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def verdict(src):
    rows = Z.classify(src)
    return rows[0][2] if rows else None


print('ZERO-ITEM CORPUS -- the control for the checker')

# ── A. THE CRITERIA LOCK REALLY GATES THE RUN ───────────────────────────────
section('A. break a criterion and the tool must REFUSE, not report clean')
rc, out = run('--fixtures')
check('A1. the lock passes on the shipped criteria and says how many fixtures',
      rc == 0 and 'fixtures classify correctly' in out, (rc, out[-300:]))

_src_path = TOOL
_orig = io.open(_src_path, encoding='utf-8', newline='').read()
_sab = _orig.replace("CORPUS_MARKER = 'ls-files'", "CORPUS_MARKER = 'zz-no-such'", 1)
check('A2a. THE SABOTAGE APPLIED. If this goes red, A2 below proves nothing and '
      'every later arm is running against the unmodified tool',
      _sab != _orig, 'the CORPUS_MARKER anchor moved -- the patch did nothing')
try:
    io.open(_src_path, 'w', encoding='utf-8', newline='').write(_sab)
    rc, out = run('--fixtures')
    check('A2. ...and with the corpus marker broken the tool exits COULD NOT RUN '
          'and says NOTHING REAL WAS JUDGED -- it does not report a clean sweep '
          'from criteria that cannot classify a hand-built case',
          rc == 2 and 'CRITERIA LOCK FAILED' in out, (rc, out[-400:]))
finally:
    io.open(_src_path, 'w', encoding='utf-8', newline='').write(_orig)
rc, out = run('--fixtures')
check('A3. THE RESTORE WORKED -- otherwise every arm below is running against a '
      'sabotaged tool and this whole file means nothing',
      rc == 0 and 'fixtures classify correctly' in out, (rc, out[-300:]))

# ── B. THE DEFECT, AND ITS SILENT HALF ──────────────────────────────────────
section('B. plant the defect, plant the fix')

DEFECT = '''
def sources():
    return subprocess.run(['git', 'ls-files', '*.py']).stdout.split()
def main(argv):
    files = sources()
    print('read %d file(s)' % len(files))
    for f in files:
        scan(f)
'''
check('B1. THE DEFECT IS REPORTED: a printed corpus count with nothing testing '
      'zero, which is how "read 0 file(s) / CLEAN" gets published',
      verdict(DEFECT) == Z.NO_GUARD, verdict(DEFECT))

FIXED = DEFECT.replace("    print('read %d file(s)' % len(files))",
                       "    if not files:\n        return EXIT_COULD_NOT_RUN\n"
                       "    print('read %d file(s)' % len(files))")
check('B1b. ...AND THE SILENT HALF: the same source with the guard is NOT '
      'reported. Without this, B1 is satisfied by a tool that flags every '
      'corpus variable in the repo',
      verdict(FIXED) == Z.GUARDED, verdict(FIXED))

WRONG = DEFECT.replace("    print('read %d file(s)' % len(files))",
                       "    if not files:\n        print('nothing to do')\n"
                       "        return 0\n"
                       "    print('read %d file(s)' % len(files))")
check('B2. THE GUARD WEARING A CHECK is its own verdict, not folded into either '
      'of the other two: it TESTS the empty case and then reports it as a pass',
      verdict(WRONG) == Z.WRONG_EXIT, verdict(WRONG))

check('B3. the `len(X) == 0` spelling is the same guard as `if not X`, so a tool '
      'is not reported for choosing the other one',
      verdict(DEFECT.replace(
          "    print('read %d file(s)' % len(files))",
          "    if len(files) == 0:\n        return EXIT_COULD_NOT_RUN\n"
          "    print('read %d file(s)' % len(files))")) == Z.GUARDED,
      'the len() spelling is not recognised')

# ── C. THE FALSE POSITIVES THE FIRST REAL RUN PAID FOR ──────────────────────
section('C. what is NOT this defect (the 28-findings run)')

FINDINGS_LIST = '''
def scan():
    out = []
    for f in subprocess.run(['git', 'ls-files', '*.py']).stdout.split():
        if bad(f):
            out.append({'file': f, 'why': 'it is bad'})
    return out
def main(argv):
    rows = scan()
    print('%d finding(s)' % len(rows))
    for r in rows:
        print(r)
'''
check('C1. A FINDINGS LIST IS NOT A CORPUS. scan() reads a corpus but RETURNS '
      'rows it built; an empty findings list is a clean sweep and reporting it '
      'was most of the first run\'s 28 rows',
      verdict(FINDINGS_LIST) is None, Z.classify(FINDINGS_LIST))

CORPUS_BUILDER = '''
def test_files():
    out = []
    for root, dirs, files in os.walk(TESTS):
        for f in files:
            if f.endswith('.py'):
                out.append(os.path.join(root, f))
    return sorted(out)
def main(argv):
    tests = test_files()
    print('read %d test file(s)' % len(tests))
    for t in tests:
        scan(t)
'''
check('C1b. ...BUT A CORPUS BUILT THE SAME WAY STILL COUNTS. Both are `out = []` '
      'plus append-in-a-loop; what separates them is that this one appends a '
      'PATH. Without this arm the C1 fix silently becomes "report nothing"',
      verdict(CORPUS_BUILDER) == Z.NO_GUARD, Z.classify(CORPUS_BUILDER))

ONE_FILE = '''
def helper():
    return io.open(PATH).read()
def main(argv):
    src = helper()
    print('read %d byte(s)' % len(src))
'''
check('C2. ONE FILE IS NOT A CORPUS -- `open` is deliberately outside the '
      'enumeration vocabulary, or every tool that reads a config joins the '
      'population',
      verdict(ONE_FILE) is None, Z.classify(ONE_FILE))

UNPRINTED = '''
def sources():
    return subprocess.run(['git', 'ls-files', '*.py']).stdout.split()
def main(argv):
    files = sources()
    for f in files:
        scan(f)
    return finish(findings)
'''
check('C3. A COUNT THAT IS NEVER PRINTED cannot be misread as coverage. The '
      'corpus is real, but nothing tells a reader it was 811 or 0, so it is a '
      'different defect and this tool does not claim it',
      verdict(UNPRINTED) is None, Z.classify(UNPRINTED))

# ── D. THE REAL RUN, AND THE FIGURE THAT MUST NOT BE SWALLOWED ──────────────
section('D. the real run publishes what it could not tell')
rc, out = run()
import re                                                         # noqa: E402
check('D1. the run reads a NON-EMPTY tool list -- a zero would make the verdict '
      'vacuous, which is this tool\'s own subject applied to itself',
      re.search(r'read (\d+) tool', out) is not None
      and int(re.search(r'read (\d+) tool', out).group(1)) > 50,
      out[:300])
_cu = re.search(r'CHECKED / UNIVERSE: (\d+) of (\d+)', out)
check('D2. CHECKED / UNIVERSE is published and both figures are real: checked > '
      '0 and checked <= universe',
      _cu is not None and int(_cu.group(1)) > 0
      and int(_cu.group(1)) <= int(_cu.group(2)),
      _cu.group(0) if _cu else 'no CHECKED / UNIVERSE line')
check('D3. ...and THE COULD-NOT-TELL COUNT IS NOT SWALLOWED INTO CLEARED. This '
      'tool judges a small minority of tools/ and the output has to say so in '
      'words, or a 3%% denominator reads as a platform verdict',
      'NOT CLEARED' in out and 'COULD NOT' in out, out[:900])
check('D4. the three verdict counts are all printed, so a reader can see the '
      'split rather than one total',
      re.search(r'\d+ GUARDED, \d+ WRONG EXIT, \d+ NO GUARD', out) is not None,
      out[:900])
check('D5. exit is 0, 1 or 2 and nothing else', rc in (0, 1, 2), rc)

rc_p, out_p = run('--propose')
check('D6. --propose PRINTS a guard and the output says out loud that it does '
      'not apply one (discipline 11: a detector that blesses its own fix is the '
      'fail-open one step later)',
      'DOES NOT APPLY' in out_p and 'EXIT_COULD_NOT_RUN' in out_p,
      out_p[-500:])

# ── E. ANCHOR ARMS -- what tells us the day this control stops testing ──────
section('E. the anchors this control depends on (discipline 8)')
_s = io.open(TOOL, encoding='utf-8').read()
check('E1. classify() is still the name this control calls; if it is renamed '
      'every arm above silently stops testing the tool',
      'def classify(' in _s, 'a function was renamed')
check('E2. CRITERIA_VERSION is present and appears in the real output',
      bool(str(getattr(Z, 'CRITERIA_VERSION', '')).strip())
      and Z.CRITERIA_VERSION in out, getattr(Z, 'CRITERIA_VERSION', None))
check('E3. the tool declares this file as its control, so checker_control_check '
      'can find the pair from either end',
      'run_parse_zero_third_state_probe.py' in _s, 'CONTROLLED_BY is stale')
check('E4. the three verdict constants are still distinct strings -- if two '
      'collapse, B1/B1b/B2 start agreeing with each other and go green',
      len({Z.GUARDED, Z.WRONG_EXIT, Z.NO_GUARD}) == 3,
      (Z.GUARDED, Z.WRONG_EXIT, Z.NO_GUARD))

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
