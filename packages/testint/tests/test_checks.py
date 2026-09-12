r"""Control for every check in the suite: can it SEE the defect it hunts?

    python tests/test_checks.py        (exit 0 pass, 1 fail)

A check that has never been seen to fail is a check whose behaviour nobody
knows. Each section below builds a **complete throwaway project** in a temp
directory -- a config, a source file and a test file -- plants the defect, and
asserts the check reports it. Then it plants the CLEAN version and asserts the
check stays quiet.

**Both halves are required.** A check that always reports passes the first half
alone; a check that never reports passes the second alone. Only the pair says
anything.

The fixtures are also the clearest documentation of what each check catches, so
they are written to be read: each one is the smallest project in which the
defect is real.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, PKG)

fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(text)
    return p


def project(files, config):
    """A throwaway project. Returns its root; caller removes it."""
    root = tempfile.mkdtemp(prefix='testint-fixture-')
    for rel, text in files.items():
        write(root, rel, text)
    cfg = dict(config)
    cfg['root'] = '.'
    write(root, 'testint.config.json', json.dumps(cfg, indent=2))
    return root


def run_check(module, root):
    """(exit code, stdout) for a check run against a fixture project."""
    p = subprocess.run(
        [sys.executable, '-m', module, '--config',
         os.path.join(root, 'testint.config.json')],
        cwd=PKG, capture_output=True, text=True, timeout=300,
        env=dict(os.environ, PYTHONPATH=PKG, PYTHONIOENCODING='utf-8'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


# ── 1. COMMENT QUOTE ─────────────────────────────────────────────────────────
print('1. COMMENT-QUOTE -- an assertion that matches only a comment')

# THE DEFECT, in the smallest project where it is real. The test asserts the
# guard is still present; the guard was DELETED and only the comment describing
# it remains. The assertion passes, and it is checking nothing.
GUARD_GONE = (
    '// The rate limiter used to call assertRateLimit() here.\n'
    'function handler(req, res) {\n'
    '  res.send("ok");\n'
    '}\n')
GUARD_PRESENT = (
    '// The rate limiter is called below.\n'
    'function handler(req, res) {\n'
    '  assertRateLimit(req);\n'
    '  res.send("ok");\n'
    '}\n')
TEST_JS = (
    "const fs = require('fs');\n"
    "const path = require('path');\n"
    "const src = fs.readFileSync(path.join(__dirname, '..', 'src/handler.js'), 'utf8');\n"
    "if (src.indexOf('assertRateLimit(') === -1) { throw new Error('guard gone'); }\n")
CFG = {'tests': ['tests/**/*.js'], 'sources': ['src/**/*.js']}

root = project({'src/handler.js': GUARD_GONE, 'tests/guard.test.js': TEST_JS}, CFG)
try:
    rc, out = run_check('testint.check_comment_quote', root)
    check(rc == 1, 'the defect is REPORTED (exit 1, got %d)' % rc)
    check('COMMENT-ONLY' in out, '...and named as comment-only')
    check('assertRateLimit(' in out, '...and the literal is quoted back')
finally:
    shutil.rmtree(root, ignore_errors=True)

root = project({'src/handler.js': GUARD_PRESENT, 'tests/guard.test.js': TEST_JS}, CFG)
try:
    rc, out = run_check('testint.check_comment_quote', root)
    check(rc == 0, 'the CLEAN project is quiet (exit 0, got %d)' % rc)
    check('COMMENT-ONLY, undeclared: 0' in out, '...with nothing undeclared')
finally:
    shutil.rmtree(root, ignore_errors=True)

# An allow entry silences it -- and the loader REFUSES an entry with no reason.
root = project({'src/handler.js': GUARD_GONE, 'tests/guard.test.js': TEST_JS},
               dict(CFG, allow='allow.json'))
try:
    write(root, 'allow.json', json.dumps({'expected': [
        {'file': 'tests/guard.test.js', 'literal': 'assertRateLimit(',
         'reason': 'deliberate: this arm asserts the historical note survives.'}]}))
    rc, out = run_check('testint.check_comment_quote', root)
    check(rc == 0, 'a DECLARED exception silences it (exit 0, got %d)' % rc)
    check('declared  : 1' in out or 'declared' in out, '...and is counted as declared')
    write(root, 'allow.json', json.dumps({'expected': [
        {'file': 'tests/guard.test.js', 'literal': 'assertRateLimit(', 'reason': '  '}]}))
    rc, out = run_check('testint.check_comment_quote', root)
    check(rc == 3, 'an allow entry with NO REASON is a config error, not a pass '
                   '(exit 3, got %d)' % rc)
finally:
    shutil.rmtree(root, ignore_errors=True)

# ── 2. MUTATION ANCHOR ───────────────────────────────────────────────────────
print('')
print('2. MUTATION ANCHOR -- a control whose anchor no longer matches')

SRC_PY = 'def pay(amount):\n    if amount > 0:\n        return amount\n    return 0\n'
CONTROL_OK = (
    "TARGET = 'src/pay.py'\n"
    "MUTATIONS = [\n"
    "    ('positive-guard', 'if amount > 0:', 'if True:'),\n"
    "]\n")
CONTROL_STALE = (
    "TARGET = 'src/pay.py'\n"
    "MUTATIONS = [\n"
    "    ('positive-guard', 'if amount >= 0:', 'if True:'),\n"   # refactored away
    "]\n")
CONTROL_AMBIGUOUS = (
    "TARGET = 'src/pay.py'\n"
    "MUTATIONS = [\n"
    "    ('return-guard', 'return', 'pass'),\n"                  # matches twice
    "]\n")
MCFG = {'probes': ['controls/**/*_probe.py'], 'sources': ['src/**/*.py'],
        'tests': ['controls/**/*_probe.py']}

for label, control, want_rc, want_word in (
        ('an anchor that matches NOTHING', CONTROL_STALE, 1, 'ANCHOR-0'),
        ('an anchor that matches TWICE', CONTROL_AMBIGUOUS, 1, 'AMBIGUOUS'),
        ('a correct control', CONTROL_OK, 0, 'exactly once')):
    root = project({'src/pay.py': SRC_PY, 'controls/pay_probe.py': control}, MCFG)
    try:
        rc, out = run_check('testint.check_mutation_anchor', root)
        check(rc == want_rc, '%s -> exit %d (got %d)' % (label, want_rc, rc))
        check(want_word in out, '...and the report says %r' % want_word)
    finally:
        shutil.rmtree(root, ignore_errors=True)

# IT MUST NOT IMPORT THE CONTROL. A control that writes a file on import would
# leave that file behind; this asserts the file is never created.
root = project({
    'src/pay.py': SRC_PY,
    'controls/danger_probe.py': (
        "import io, os\n"
        "io.open(os.path.join(os.path.dirname(__file__), 'RAN'), 'w').write('x')\n"
        "TARGET = 'src/pay.py'\n"
        "MUTATIONS = [('g', 'if amount > 0:', 'if True:')]\n")}, MCFG)
try:
    rc, out = run_check('testint.check_mutation_anchor', root)
    check(not os.path.exists(os.path.join(root, 'controls', 'RAN')),
          'the control was PARSED, not imported -- its side effect never happened')
finally:
    shutil.rmtree(root, ignore_errors=True)

# ── 3. DETERMINISM ───────────────────────────────────────────────────────────
print('')
print('3. DETERMINISM -- a checker that answers differently on the same input')

UNSTABLE = ('items = {"aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh"}\n'
            'for x in sorted(items, key=len):\n'
            '    print(x)\n')
STABLE = ('items = {"aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh"}\n'
          'for x in sorted(items, key=lambda t: (len(t), t)):\n'
          '    print(x)\n')
SILENT = 'import sys\nsys.exit(0)\n'
DCFG = {'checkers': ['checkers/*.py'], 'tests': ['checkers/*.py'],
        'determinism': {'seeds': ['1', '7', '12345', '99999']}}

for label, body, want_rc, want_word in (
        ('a seed-dependent checker', UNSTABLE, 1, 'VARIES'),
        ('a checker with a total order', STABLE, 0, 'byte-identical'),
        ('a checker that prints NOTHING', SILENT, 1, 'COULD NOT RUN')):
    root = project({'checkers/c.py': body}, DCFG)
    try:
        rc, out = run_check('testint.check_determinism', root)
        check(rc == want_rc, '%s -> exit %d (got %d)' % (label, want_rc, rc))
        check(want_word in out, '...and the report says %r' % want_word)
    finally:
        shutil.rmtree(root, ignore_errors=True)

# ── 4. THE RUNNER ────────────────────────────────────────────────────────────
print('')
print('4. THE RUNNER -- could-not-run is never folded into clean')
root = project({'src/handler.js': GUARD_PRESENT, 'tests/guard.test.js': TEST_JS}, CFG)
try:
    p = subprocess.run(
        [sys.executable, '-m', 'testint.run', '--config',
         os.path.join(root, 'testint.config.json')],
        cwd=PKG, capture_output=True, text=True, timeout=600,
        env=dict(os.environ, PYTHONPATH=PKG, PYTHONIOENCODING='utf-8'))
    out = (p.stdout or '') + (p.stderr or '')
    # `checkers` is absent from this config, so determinism COULD NOT RUN.
    check(p.returncode == 3,
          'a config with no checkers makes the runner exit 3, not 0 (got %d)'
          % p.returncode)
    check('COULD NOT RUN' in out, '...and the summary says COULD NOT RUN')
    check('SUMMARY' in out, '...and every check is listed by name')
finally:
    shutil.rmtree(root, ignore_errors=True)

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
