#!/usr/bin/env python
"""The control for tools/checker_selftest_check.py -- BOTH directions.

    python tests/run_checker_selftest_probe.py

Exit 0 all arms pass, 1 any arm fails.

── THE RECURSION IS THE POINT, AND IT IS NOT A JOKE ────────────────────────
The tool under test asks every checker in the report-only registry: on the run
that just said CLEAN, did you demonstrate you can still report a
known-positive? A tool asking that question has to answer it about itself, and
it does -- its criteria lock runs on every real run and prints `criteria lock:
8/8` beside the finding count. D2 below asserts exactly that against the real
output, so the tool cannot start exempting itself.

── AND THE HARSH-DIRECTION ERROR THE FIRST REAL RUN MADE ───────────────────
The first version matched the isolated-flag branch as `attr='fixtures'` and
`'fixtures'` and missed `if '--selftest' in argv:`, because the AST dump carries
`value='--selftest'` and the leading quote never lines up with the dashes. It
reported tools/ai_action_approval_audit.py as SILENT -- runs and says nothing --
when its self-test is FLAG-ONLY and, read properly, is one of the better ones in
the repo: it drives the real `app_files()` with an emptied list and asserts the
tool refuses. A wrong verdict, in the harsher direction, on the tool that had
already found this exact class of blindness in itself. Section C pins it.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'checker_selftest_check.py')
CONTROLS_FOR = ['checker_selftest_check.py']

import checker_selftest_check as S                              # noqa: E402

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


print('KNOWN-POSITIVE SELF-TEST -- the control for the checker')

# ── A. THE CRITERIA LOCK REALLY GATES THE RUN ───────────────────────────────
section('A. break a criterion and the tool must REFUSE, not report clean')
rc, out = run('--fixtures')
check('A1. the lock passes on the shipped criteria and says how many fixtures',
      rc == 0 and 'fixtures classify correctly' in out, (rc, out[-300:]))

_orig = io.open(TOOL, encoding='utf-8', newline='').read()
_sab = _orig.replace("SELFTEST_NAMES = ('run_fixtures',",
                     "SELFTEST_NAMES = ('zz_no_such_runner',", 1)
check('A2a. THE SABOTAGE APPLIED. If this goes red, A2 proves nothing and every '
      'arm below is running against the unmodified tool',
      _sab != _orig, 'the SELFTEST_NAMES anchor moved -- the patch did nothing')
try:
    io.open(TOOL, 'w', encoding='utf-8', newline='').write(_sab)
    rc, out = run('--fixtures')
    check('A2. ...and with the runner vocabulary broken it exits COULD NOT RUN '
          'rather than reporting every tool in the registry as having no '
          'fixture set, which would be a 67-row clean-looking sweep',
          rc == 2 and 'CRITERIA LOCK FAILED' in out, (rc, out[-400:]))
finally:
    io.open(TOOL, 'w', encoding='utf-8', newline='').write(_orig)
rc, out = run('--fixtures')
check('A3. THE RESTORE WORKED -- otherwise every arm below is running against a '
      'sabotaged tool and this whole file means nothing',
      rc == 0 and 'fixtures classify correctly' in out, (rc, out[-300:]))

# ── B. THE FOUR VERDICTS, EACH IN BOTH DIRECTIONS ──────────────────────────
section('B. the four verdicts on hand-built sources')

GOOD = '''
def run_fixtures():
    return []
def main(argv):
    bad = run_fixtures()
    if bad:
        return 2
    print('criteria lock: %d/%d fixtures classify correctly' % (N, N))
    rows = scan()
    print('%d finding(s)' % len(rows))
'''
check('B1. THE SHAPE THAT PASSES: a known-positive set, run on the DEFAULT '
      'path, with its result PRINTED beside the real one',
      S.classify(GOOD) == S.PUBLISHED, S.classify(GOOD))

check('B2. FLAG-ONLY is its own verdict, not folded into "has a self-test". A '
      'self-test that runs when somebody asks is a control with a shorter '
      'name, and the person reading a clean line at 2am is not asking',
      S.classify(GOOD.replace(
          "    bad = run_fixtures()",
          "    if args.fixtures:\n        bad = run_fixtures()")) == S.FLAG_ONLY,
      S.classify(GOOD.replace("    bad = run_fixtures()",
                              "    if args.fixtures:\n        bad = run_fixtures()")))

SILENT_SRC = '''
def run_fixtures():
    return []
def main(argv):
    bad = run_fixtures()
    if bad:
        return 2
    rows = scan()
    print('%d finding(s)' % len(rows))
'''
check('B3. SILENT is its own verdict too: it RUNS, and a passing run says '
      'nothing, so the reader of the CLEAN line still cannot tell the tool '
      'demonstrated anything. The refusal path is real and is not the point',
      S.classify(SILENT_SRC) == S.SILENT, S.classify(SILENT_SRC))

check('B4. NO FIXTURE SET AT ALL is distinguished from all three -- it is the '
      'commonest state in the registry and the honest name for it is not '
      '"clean"',
      S.classify('def main(argv):\n    rows = scan()\n'
                 "    print('%d' % len(rows))\n") == S.NONE,
      S.classify('def main(argv):\n    rows = scan()\n'))

check('B5. the four verdict constants are DISTINCT strings. If two collapse, '
      'B1-B4 start agreeing with each other and all four go green',
      len({S.PUBLISHED, S.SILENT, S.FLAG_ONLY, S.NONE}) == 4,
      (S.PUBLISHED, S.SILENT, S.FLAG_ONLY, S.NONE))

# ── C. THE HARSH-DIRECTION ERROR THE FIRST REAL RUN MADE ───────────────────
section('C. the isolated-flag spelling that produced a wrong verdict')

IN_ARGV = '''
def selftest():
    print('  ok   a planted case is reported')
    return 0
def main(argv):
    if '--selftest' in argv:
        return selftest()
    rows = scan()
    print('%d finding(s)' % len(rows))
'''
check('C1. `if \'--selftest\' in argv:` IS the isolated path. Matching only '
      '`attr=\'fixtures\'` missed it and called ai_action_approval_audit.py '
      'SILENT when it is FLAG-ONLY -- a wrong verdict in the harsher direction',
      S.classify(IN_ARGV) == S.FLAG_ONLY, S.classify(IN_ARGV))

check('C1b. ...and the `--fixtures in argv` spelling of the same thing',
      S.classify(IN_ARGV.replace('--selftest', '--fixtures')) == S.FLAG_ONLY,
      S.classify(IN_ARGV.replace('--selftest', '--fixtures')))

check('C2. THE SILENT HALF OF THAT FIX: normalising dashes must not swallow the '
      'PASSING shape. A runner called OUTSIDE the flag branch with the early '
      'return INSIDE it is how several tools here are written and it must '
      'still clear',
      S.classify('''
def run_fixtures():
    return []
def main(argv):
    bad = run_fixtures()
    print('criteria lock: %d fixtures' % len(bad))
    if '--fixtures' in argv:
        return 0
    rows = scan()
''') == S.PUBLISHED, 'the dash normalisation over-matched and ate a passing shape')

check('C3. a fixture RUNNER THAT MAIN NEVER CALLS is FLAG-ONLY, not NONE -- the '
      'fixtures are real and the wiring is what is missing, and calling it '
      'NONE would send the reader to write a fixture set that already exists',
      S.classify('''
def run_fixtures():
    return []
def helper():
    return run_fixtures()
def main(argv):
    rows = scan()
    print('%d' % len(rows))
''') == S.FLAG_ONLY, 'a never-called runner is misclassified')

# ── D. THE REAL RUN, INCLUDING ON ITSELF ───────────────────────────────────
section('D. the real run, and the tool answering its own question')
rc, out = run()
import re                                                         # noqa: E402
check('D1. the population is NON-EMPTY and is the registry, named as such -- a '
      'zero would make every verdict vacuous',
      re.search(r'read (\d+) tool', out) is not None
      and int(re.search(r'read (\d+) tool', out).group(1)) > 20
      and 'report-only registry' in out, out[:400])
check('D2. THE TOOL ANSWERS ITS OWN QUESTION. Its criteria lock runs on the '
      'REAL run -- not only under --fixtures -- and prints beside the finding '
      'count. A tool that asks this of 67 others and exempts itself is the '
      'defect it reports',
      re.search(r'criteria lock: (\d+)/(\d+) fixtures classify correctly', out)
      is not None, out[:400])
_m = re.search(r'criteria lock: (\d+)/(\d+)', out)
check('D2b. ...and that lock is NON-EMPTY and fully passing on the real run: a '
      '0/0 lock prints the same sentence and proves nothing',
      _m is not None and int(_m.group(1)) > 0
      and _m.group(1) == _m.group(2),
      _m.group(0) if _m else 'no criteria lock line on the real run')
check('D3. the four verdict counts are printed SEPARATELY, so a reader sees the '
      'split rather than one total -- "has a self-test" over flag-only and '
      'silent would be a score nobody agreed',
      'printed on every real run' in out and 'flag-only' in out
      and 'no fixture set' in out and 'runs, prints nothing' in out, out[:900])
_cu = re.search(r'CHECKED / UNIVERSE: (\d+) of (\d+)', out)
check('D4. CHECKED / UNIVERSE is published and both figures are real',
      _cu is not None and int(_cu.group(1)) > 0
      and int(_cu.group(1)) <= int(_cu.group(2)),
      _cu.group(0) if _cu else 'no coverage line')
check('D5. exit is 0, 1 or 2 and nothing else', rc in (0, 1, 2), rc)

# ── E. ANCHOR ARMS (discipline 8) ──────────────────────────────────────────
section('E. the anchors this control depends on')
_s = io.open(TOOL, encoding='utf-8').read()
check('E1. classify() is still the name this control calls',
      'def classify(' in _s, 'a function was renamed')
check('E2. CRITERIA_VERSION is present and appears in the real output',
      bool(str(getattr(S, 'CRITERIA_VERSION', '')).strip())
      and S.CRITERIA_VERSION in out, getattr(S, 'CRITERIA_VERSION', None))
check('E3. the tool declares this file as its control',
      'run_checker_selftest_probe.py' in _s, 'CONTROLLED_BY is stale')
check('E4. the population still comes from report_only_checks.REGISTRY rather '
      'than from a list inside the tool. A hand-kept copy would drift from the '
      'registry and this tool would stop being about the thing that runs',
      'report_only_checks' in _s and 'REGISTRY' in _s,
      'the population is no longer read from the registry')

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
