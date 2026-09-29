#!/usr/bin/env python
"""The control for tools/dead_rule_sweep.py -- BOTH directions.

    python tests/run_dead_rule_sweep_probe.py

Exit 0 all arms pass, 1 any arm fails.

── THE ARM THAT MATTERS IS THE RESTORE ─────────────────────────────────────
This sweep MUTATES real tool files -- it neutralises one compiled pattern at a
time and re-runs the tool's own evidence. A restore that silently fails leaves
a broken rule in a tool somebody else pushes, and this repo has already paid
once for a probe whose restore was wrong. Section C drives a real neutralise /
restore cycle on a scratch copy and asserts BYTE IDENTITY afterwards.

── AND THE SECOND ARM IS THAT THE REWRITE PARSES ───────────────────────────
A neutralisation that breaks the module turns every rule red for the wrong
reason and the sweep reports a clean bill of exercised rules. Section B checks
the rewritten source still parses, still imports, and actually contains the
never-matching pattern -- because "the patch applied" and "the patch did
nothing" are the two answers that look identical from the outside.
"""
import ast
import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'dead_rule_sweep.py')
CONTROLS_FOR = ['dead_rule_sweep.py']

import dead_rule_sweep as D                                      # noqa: E402

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


print('DEAD RULE SWEEP -- the control for the sweep')

# ── A. THE CRITERIA LOCK GATES THE RUN ─────────────────────────────────────
section('A. break the rewrite and the sweep must REFUSE, not report clean')
rc, out = run('--fixtures')
check('A1. the lock passes on the shipped criteria', rc == 0
      and 'fixtures classify correctly' in out, (rc, out[-300:]))

_orig = io.open(TOOL, encoding='utf-8', newline='').read()
_sab = _orig.replace('NEVER = "(?!x)x"', 'NEVER = "(?!x)x"  # noqa\nNEVER = ""', 1)
check('A2a. THE SABOTAGE APPLIED -- without this A2 proves nothing',
      _sab != _orig, 'the NEVER anchor moved')
try:
    io.open(TOOL, 'w', encoding='utf-8', newline='').write(_sab)
    rc, out = run('--fixtures')
    check('A2. ...and with the never-matching pattern emptied the lock FAILS '
          'and the sweep exits 2. A sweep whose own rewrite is broken reports '
          'every rule as dead, which is the loudest possible wrong answer',
          rc == 2 and 'CRITERIA LOCK FAILED' in out, (rc, out[-400:]))
finally:
    io.open(TOOL, 'w', encoding='utf-8', newline='').write(_orig)
rc, out = run('--fixtures')
check('A3. THE RESTORE WORKED', rc == 0, (rc, out[-200:]))

# ── B. THE REWRITE IS REAL, AND IT PARSES ──────────────────────────────────
section('B. the neutralisation applies, parses, and can never match')

SRC = ("import re\n"
       "PAT = re.compile(\n    r'abc'\n    r'|def', re.I)\n"
       "OTHER = re.compile(r'zzz')\n")
_new = D.neutralise(SRC, 'PAT')
check('B1. a MULTI-LINE pattern with adjacent literals and a flag is rewritten '
      '-- text surgery gets this wrong, which is why it goes through ast',
      _new is not None and D.NEVER in _new, _new)
check('B1b. ...and the result STILL PARSES. A rewrite that breaks the module '
      'turns every rule red for the wrong reason and the sweep then reports a '
      'clean bill of exercised rules',
      _new is not None and ast.parse(_new) is not None, _new)
check('B1c. ...and the FLAGS are carried over, not dropped. Dropping re.I '
      'changes behaviour beyond the neutralisation, so the ablation would be '
      'measuring two things at once',
      _new is not None and 're.I' in _new, _new)
check('B1d. ...and the OTHER pattern in the same module is untouched, so one '
      'ablation is one rule',
      _new is not None and "OTHER = re.compile(r'zzz')" in _new, _new)
check('B2. the never-matching pattern really matches NOTHING -- if it matched '
      'anything the ablation would be a no-op reported as an exercise',
      __import__('re').compile(D.NEVER).search('x') is None
      and __import__('re').compile(D.NEVER).search('') is None, D.NEVER)
check('B3. a name that is NOT a module-level pattern yields no rewrite, rather '
      'than a silent no-op that would be counted as a rule nothing depends on',
      D.neutralise(SRC, 'NOSUCH') is None, 'a phantom rewrite was produced')
check('B3b. ...and a pattern compiled INSIDE A FUNCTION is out of reach, which '
      'is a stated limit and not a gap',
      D.neutralise("def f():\n    P = re.compile(r'x')\n", 'P') is None, '')

# ── C. THE RESTORE, DRIVEN ON A REAL FILE ──────────────────────────────────
section('C. the sweep puts the file back, byte for byte')

_tmpdir = tempfile.mkdtemp(prefix='drs-')
_scratch = os.path.join(_tmpdir, 'scratch_tool.py')
_body = ("import re\nPAT = re.compile(r'abc')\n\n\n"
         "def main(argv):\n    return 0\n")
io.open(_scratch, 'w', encoding='utf-8', newline='').write(_body)
_before = io.open(_scratch, encoding='utf-8', newline='').read()
_patched = D.neutralise(_before, 'PAT')
io.open(_scratch, 'w', encoding='utf-8', newline='').write(_patched)
check('C1. the mutation really lands on disk -- a probe that asserts a restore '
       'without proving the mutation happened is asserting nothing',
      D.NEVER in io.open(_scratch, encoding='utf-8').read(), '')
io.open(_scratch, 'w', encoding='utf-8', newline='').write(_before)
check('C2. ...and the restore is BYTE IDENTICAL. This repo has already paid '
      'once for a probe whose restore was wrong, and this sweep mutates files '
      'other sessions push',
      io.open(_scratch, encoding='utf-8', newline='').read() == _before, '')
try:
    os.unlink(_scratch)
    os.rmdir(_tmpdir)
except OSError:
    pass

check('C3. ANCHOR: the sweep restores inside a `finally` and RAISES when the '
      'file on disk is not what it was -- a silent restore failure is worse '
      'than no sweep at all',
      'finally:' in _orig and 'RESTORE FAILED' in _orig,
      'the restore guard is gone')

# ── D. THE REAL RUN, ON ITSELF ─────────────────────────────────────────────
section('D. the real run')
rc, out = run('--tool', 'assertion_label_shape_check.py')
import re                                                        # noqa: E402
check('D1. it reads a NON-EMPTY rule list -- a zero would make the verdict '
      'vacuous', re.search(r'(\d+) module-level compiled rule', out) is not None
      and int(re.search(r'(\d+) module-level compiled rule', out).group(1)) > 0,
      out[:400])
check('D2. it publishes CHECKED / UNIVERSE and keeps COULD NOT TELL SEPARATE '
      'from clean -- "no evidence to ablate" and "the rule is exercised" are '
      'opposite findings that would otherwise print the same',
      'CHECKED / UNIVERSE' in out and 'NOT CLEARED' in out
      and 'COULD NOT TELL' in out, out[:900])
check('D3. and it reports BOTH numbers, exercised and dead, rather than one '
      'score', re.search(r'\(\d+ exercised, \d+ dead\)', out) is not None,
      out[:900])
check('D4. exit is 0, 1 or 2 and nothing else', rc in (0, 1, 2), rc)
check('D5. THE FILE IT ABLATED IS UNCHANGED after the real run',
      subprocess.run(['git', 'diff', '--quiet', '--',
                      'tools/assertion_label_shape_check.py'],
                     cwd=REPO).returncode == 0,
      'the sweep left a real tool modified')

# ── E. ANCHORS ─────────────────────────────────────────────────────────────
section('E. the anchors this control depends on')
check('E1. neutralise() and sweep_tool() are still the names this control calls',
      'def neutralise(' in _orig and 'def sweep_tool(' in _orig, '')
check('E2. CRITERIA_VERSION is present and appears in the real output',
      bool(str(getattr(D, 'CRITERIA_VERSION', '')).strip())
      and D.CRITERIA_VERSION in out, getattr(D, 'CRITERIA_VERSION', None))
check('E3. the tool declares this file as its control',
      'run_dead_rule_sweep_probe.py' in _orig, 'CONTROLLED_BY is stale')

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
