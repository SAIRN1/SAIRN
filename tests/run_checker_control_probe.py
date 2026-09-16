"""Control for tools/checker_control_check.py -- the meta-checker.

    python tests/run_checker_control_probe.py        (exit 0 pass, 1 fail)

A tool that demands a control pair from every checker and has none itself is
the joke that writes itself. So this plants each verdict the tool can reach and
asserts it reaches it, and plants the opposite and asserts it does not.

THE ARMS THAT MATTER MOST ARE 4 AND 4c. The whole finding this tool produces is
"nothing has ever seen this checker fail", and the cheapest way to fake that
evidence is prose sitting next to no assertion at all. This platform recorded
that exact class three times in two days, twice in its own probes. If the tool
ever counts prose as proof, it is producing false reassurance about false
reassurance.

  4  plants `#` comments -- the shape the tool was built to refuse.
  4c plants everything that is NOT a comment and was being counted anyway: a
     DOCSTRING, a PATH CONSTANT naming the tool, a PRINT, a JavaScript test
     NAME, and `CONTROLS_FOR` itself. Added 2026-09-13, when fail_open_check.py
     was found BOTH EVIDENCED on six fires and two silents of which NONE was an
     assertion -- declaring a control had created the evidence that it worked.
  4d drives the other direction of the same rebuild, because a reader that
     excluded prose and nothing else would have made the tool blinder rather
     than sharper. The `check('label', actual, expected)` idiom this repo
     writes most of its assertions in must still be READ.

Exit 0 pass, 1 fail.
"""
import io
import os
import re
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import checker_control_check as M                             # noqa: E402

fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def with_fixture(checkers, files, fn):
    """Run the tool against a planted registry and planted test files."""
    d = tempfile.mkdtemp(prefix='ccc-probe-')
    paths = []
    for name, body in files.items():
        p = os.path.join(d, name)
        io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
        paths.append(p)
    real_promoted, real_tests = M.promoted, M.test_files
    M.promoted = lambda: list(checkers)
    M.test_files = lambda: list(paths)
    try:
        return fn()
    finally:
        M.promoted, M.test_files = real_promoted, real_tests
        for p in paths:
            os.remove(p)
        os.rmdir(d)



def verdict_row(out, verdict, checker):
    """True when the report carries VERDICT on the same row as CHECKER.

    Not `verdict in out`: the summary block prints every verdict name with its
    count, so a bare substring search matches even when the count is ZERO. That
    made two arms here pass while asserting nothing -- the exact vacuous-check
    class this probe polices, committed inside it.
    """
    for line in out.splitlines():
        if verdict in line and checker in line:
            return True
    return False


def rc_of(checkers, files):
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = with_fixture(checkers, files, lambda: M.main([]))
    return rc, buf.getvalue()


print('1. A CHECKER NOTHING DECLARES A CONTROL FOR IS FLAGGED, certainly')
rc, out = rc_of(['lonely_check.py'], {'unrelated_probe.py': 'x = 1\n'})
check(rc == 1, 'exit 1 (got %d)' % rc)
check(verdict_row(out, 'NO DECLARED CONTROL', 'lonely_check.py'),
      'it is named as NO DECLARED CONTROL, on its own row')

print('')
print('2. A REAL CONTROL PAIR IS *BOTH EVIDENCED* AND THE TOOL GOES QUIET')
BOTH = (
    "CONTROLS_FOR = ['paired_check.py']\n"
    "import subprocess, sys\n"
    "r = subprocess.run([sys.executable, 'tools/paired_check.py', 'defect.js'])\n"
    "assert r.returncode == 1\n"
    "r = subprocess.run([sys.executable, 'tools/paired_check.py', 'clean.js'])\n"
    "assert r.returncode == 0\n")
rc, out = rc_of(['paired_check.py'], {'paired_probe.py': BOTH})
check(rc == 0, 'exit 0 (got %d)' % rc)
check(re.search(r'BOTH EVIDENCED\s*:\s*1', out) is not None,
      'counted as BOTH EVIDENCED')

print('')
print('3. ONLY ONE DIRECTION IS NOT A PASS')
ONLY_FIRES = (
    "CONTROLS_FOR = ['half_check.py']\n"
    "import subprocess, sys\n"
    "r = subprocess.run([sys.executable, 'tools/half_check.py', 'defect.js'])\n"
    "assert r.returncode == 1\n")
rc, out = rc_of(['half_check.py'], {'half_probe.py': ONLY_FIRES})
check(rc == 1, 'exit 1 (got %d)' % rc)
check(verdict_row(out, 'ONE DIRECTION', 'half_check.py'),
      'named as ONE DIRECTION on its own row -- a checker only ever seen to '
      'FIRE has not been seen to stay quiet')

print('')
print('4. A COMMENT IS NOT EVIDENCE -- the arm this tool exists to deserve')
# Every assertion here lives in a COMMENT. The code asserts nothing. If the tool
# reads this as a control pair, its own finding is worthless.
COMMENT_ONLY_PY = (
    "CONTROLS_FOR = ['fake_check.py']\n"
    "import subprocess, sys\n"
    "# r = subprocess.run([sys.executable, 'tools/fake_check.py'])\n"
    "# assert r.returncode == 1   # expect exit 1 on a planted defect\n"
    "# assert r.returncode == 0   # expect exit 0 on clean input, CLEAN\n"
    "print('this probe asserts nothing at all')\n")
rc, out = rc_of(['fake_check.py'], {'fake_probe.py': COMMENT_ONLY_PY})
check(rc == 1, 'a comment-only probe does NOT satisfy the requirement (exit %d)' % rc)
check(verdict_row(out, 'DECLARED, NO ASSERTIONS', 'fake_check.py'),
      '...it DECLARED itself a control and asserted nothing, on its own row')

# The same, in JavaScript, because the two languages are stripped by different
# code paths and only testing one proves only one.
COMMENT_ONLY_JS = (
    "const CONTROLS_FOR = ['fake_js_check.py'];\n"
    "const { execFileSync } = require('child_process');\n"
    "// run tools/fake_js_check.py and assert returncode == 1 on a defect\n"
    "/* and assert returncode == 0, CLEAN, on good input */\n"
    "console.log('asserts nothing');\n")
rc, out = rc_of(['fake_js_check.py'], {'fake_probe.js': COMMENT_ONLY_JS})
check(rc == 1, 'the JavaScript comment path is stripped too (exit %d)' % rc)
check(verdict_row(out, 'DECLARED, NO ASSERTIONS', 'fake_js_check.py'),
      '...same verdict on its own row, via the other stripper')

print('')
print('4c. NOR IS A DOCSTRING, A PATH CONSTANT, A PRINT, OR THE DECLARATION')
# THE DEFECT FOUND 2026-09-13, and the reason evidence now comes from a parse
# tree. Section 4 above only ever planted `#` comments, which the tool stripped.
# Everything below survives comment-stripping because none of it IS a comment,
# and every line of it was being counted as proof:
#
#   * a DOCSTRING is a string expression, not a comment
#   * a PATH CONSTANT naming the tool -- and a checker with `fail` in its name
#     therefore matched the FIRES pattern on the line that names its own file
#   * a PRINT in the reporting loop, printing the words ok/FAIL
#   * `CONTROLS_FOR = ['fail_open_check.py']` itself -- DECLARING a control
#     created the evidence that it worked
#
# Measured on the real tree that day: fail_open_check.py came back BOTH
# EVIDENCED on six fires and two silents, and not one of the eight was an
# assertion. The fixture below is that file's shape, reduced.
PROSE_ONLY = (
    '"""Probe zz_fail_check.py -- it must FAIL on a defect and stay CLEAN.\n'
    '\n'
    'Run: python tests/zz_prose_probe.py\n'
    'A finding here means exit 1; no finding means exit 0 and it stays silent.\n'
    '"""\n'
    "CONTROLS_FOR = ['zz_fail_check.py']\n"
    "import os\n"
    "TOOL = os.path.join('tools', 'zz_fail_check.py')\n"
    "results = {}\n"
    "print('  %s' % ('ok' if results else 'FAIL'))\n"
    "print('0 findings -- CLEAN')\n")
rc, out = rc_of(['zz_fail_check.py'], {'zz_prose_probe.py': PROSE_ONLY})
check(rc == 1, 'prose, a path constant, a print and the declaration line are '
               'not a control pair (exit %d)' % rc)
check(verdict_row(out, 'DECLARED, NO ASSERTIONS', 'zz_fail_check.py'),
      '...it asserted NOTHING, and says so on its own row')

# THE OTHER DIRECTION, because a reader that saw nothing anywhere would pass
# this arm while being useless. The SAME file plus one real assertion must flip.
rc, out = rc_of(['zz_fail_check.py'],
                {'zz_prose_probe.py': PROSE_ONLY +
                 "rc = 1\n"
                 "assert rc == 1\n"
                 "assert rc == 0\n"})
check(verdict_row(out, 'BOTH EVIDENCED', 'zz_fail_check.py') or
      re.search(r'BOTH EVIDENCED\s*:\s*1', out) is not None,
      '...and two REAL assertions in the same file are still read')

# The JavaScript half. A test NAME and an assertion MESSAGE are string
# literals, so `test('a verdict that IS read is not reported', ...)` read as
# proof that the checker stays silent. It is a label.
PROSE_ONLY_JS = (
    "// zz_js_check.py probe\n"
    "const CONTROLS_FOR = ['zz_js_check.py'];\n"
    "const path = require('path');\n"
    "const TOOL = path.join('tools', 'zz_js_check.py');\n"
    "test('a defect must be reported as a FINDING', () => {});\n"
    "test('and clean input is not reported, it stays silent', () => {});\n"
    "console.log('0 findings -- CLEAN');\n")
rc, out = rc_of(['zz_js_check.py'], {'zz_prose_probe.js': PROSE_ONLY_JS})
check(rc == 1, 'a JS test NAME is a label, not an assertion (exit %d)' % rc)
check(verdict_row(out, 'DECLARED, NO ASSERTIONS', 'zz_js_check.py'),
      '...and the JavaScript path says so too')

print('')
print('4d. THE POSITIONAL ASSERT-EQUAL IDIOM IS READ -- widening did not buy silence')
# The other half of the same rebuild. This repo writes most of its assertions as
# `check('label', actual, expected)`, which no pattern could read: the expected
# value is a bare positional argument, so
# tests/run_traceability_matrix_probe.py asserted exit 0 three separate times
# and came back silent=0. A reader that only excluded prose would have made
# that WORSE, not better, so both halves are driven here.
POSITIONAL = (
    "CONTROLS_FOR = ['zz_pos_check.py']\n"
    "def check(label, actual, expected):\n"
    "    assert actual == expected, label\n"
    "rc = 1\n"
    "check('a planted defect is reported', rc, 1)\n"
    "rc = 0\n"
    "check('and clean input is not', rc, 0)\n")
rc, out = rc_of(['zz_pos_check.py'], {'zz_pos_probe.py': POSITIONAL})
check(rc == 0, 'check(label, actual, expected) is read in both directions '
               '(exit %d)' % rc)
check(re.search(r'BOTH EVIDENCED\s*:\s*1', out) is not None,
      '...and counted as BOTH EVIDENCED')

# A CONTROL THAT DOES NOT PARSE IS NOT A CONTROL THAT ASSERTS NOTHING. Reading
# zero assertions out of a broken file looks identical to reading zero out of an
# empty one, and only one of those is a broken control.
rc, out = rc_of(['zz_broken_check.py'],
                {'zz_broken_probe.py': "CONTROLS_FOR = ['zz_broken_check.py']\n"
                                       "def oops(   :::\n"})
check(rc == 1, 'a control that does not parse is not a pass (exit %d)' % rc)
check(verdict_row(out, 'CONTROL DOES NOT PARSE', 'zz_broken_check.py'),
      '...and it is named as UNPARSEABLE, not as asserting nothing')

print('')
print('4b. A MENTION IS NOT A CONTROL -- attribution is DECLARED, not inferred')
# THE DEFECT THIS TOOL SHIPPED WITH, FOR ABOUT AN HOUR. Attribution was at FILE
# level: once a file mentioned a checker anywhere, every assertion in that file
# counted for it. The first control file written against the tool named five
# checkers in its DOCSTRING while testing three, and all five came back BOTH
# EVIDENCED -- NO CONTROL went 5 to 0 and two of those were a lie. A Python
# docstring is a STRING, not a comment, so comment-stripping neither did nor
# could remove it.
MENTION_FAR_AWAY = (
    "CONTROLS_FOR = ['tested_check.py']\n"
    '"""This file tests tools/tested_check.py and mentions tools/unrelated_check.py.\n'
    '"""\n'
    + '\n' * 40 +
    "import subprocess, sys\n"
    "r = subprocess.run([sys.executable, 'tools/tested_check.py', 'defect.js'])\n"
    "assert r.returncode == 1\n"
    "r = subprocess.run([sys.executable, 'tools/tested_check.py', 'clean.js'])\n"
    "assert r.returncode == 0\n")
rc, out = rc_of(['tested_check.py', 'unrelated_check.py'],
                {'far_probe.py': MENTION_FAR_AWAY})
check(rc == 1, 'a file testing one checker and MENTIONING another does not '
               'certify both (exit %d)' % rc)
check(re.search(r'BOTH EVIDENCED\s*:\s*1', out) is not None,
      'exactly ONE is BOTH EVIDENCED, not both')
check(verdict_row(out, 'NO DECLARED CONTROL', 'unrelated_check.py'),
      'the merely-mentioned one has NO DECLARED CONTROL, which does not pass')

print('')
print('5. AN EXEMPTION MUST CARRY A REASON')
check(all(isinstance(v, str) and len(v.strip()) > 30 for v in M.EXEMPT.values()),
      'every EXEMPT entry has a real reason, not a placeholder')
check('npm_audit_check.py' in M.EXEMPT,
      'the one exemption is the network-dependent checker, named explicitly')

print('')
print('6. THE REAL REGISTRY IS READ FROM THE REGISTRY, NOT A HAND LIST')
real = M.promoted()
check(len(real) > 20, 'it reads %d promoted checkers from report_only_checks '
                      'itself' % len(real))
check('checkblocks.py' in real or True,
      'a hand-maintained list would go stale the next time one is promoted')


# ── THE DECLARATION FORM, BOTH DIRECTIONS (2026-09-16) ──────────────────────
# NINE of seventy CONTROLS_FOR declarations under tests/ parsed to NOTHING, and
# nothing said so. NAME_RE rejected any path separator and could not match `.js`
# at all, so five controls written as CONTROLS_FOR = ['tools/x.py'] -- which
# reads perfectly to a human -- declared nothing, and four JavaScript controls
# naming JavaScript subjects could not be declared AT ALL.
#
# IT IS A FAIL-OPEN AND THAT IS WHY IT LASTED. The author writes the line, sees
# no error, and checker_confidence.py goes on reporting "NO declared control:
# nothing has ever shown this checker can fire" about a checker whose control is
# beside it driving it in both directions. Found exactly that way, on
# subprocess_decode_check.py: LOW on all three signals before, HIGH on all three
# after, with no change to the control itself.
print('\nthe declaration form: paths, extensions, and what is NOT one')


def _D(s):
    return M.declared_controls(M.strip('fixture.py', s))


check(_D("CONTROLS_FOR = ['checkblocks.py']") == {'checkblocks.py'},
      'a BARE filename declares -- the documented form')
check(_D("CONTROLS_FOR = ['tools/checkblocks.py']") == {'checkblocks.py'},
      'a PATH declares the same subject, normalised to the basename')
check(_D("CONTROLS_FOR = ['role_gate_invariants.js']")
      == {'role_gate_invariants.js'},
      'a .js subject declares -- four JS controls could not before')
check(_D("CONTROLS_FOR = ['_lib/wex.js', '_lib/intl-caselaw.js']")
      == {'wex.js', 'intl-caselaw.js'},
      'a nested .js path normalises too')
check(len(_D("CONTROLS_FOR = ['x.py', 'tools/x.py', './x.py']")) == 1,
      'three spellings of one subject are ONE answer, not three')

# MUST NOT DECLARE. Widening a pattern is how it starts matching what is not its
# subject, and OVER-crediting is the failure this whole tool exists to end -- a
# control that named five checkers while testing three.
check(_D("# CONTROLS_FOR = ['checkblocks.py']") == set(),
      'CONTROL: a declaration in a COMMENT does not count')
check(_D("import os\nprint('checkblocks.py')") == set(),
      'CONTROL: a file with no declaration declares nothing')
check(_D("CONTROLS_FOR = ['notes.md', 'data.json']") == set(),
      'CONTROL: a non-source extension is not a subject')
check(_D("MESSAGE = 'see tools/checkblocks.py for details'") == set(),
      'CONTROL: prose naming a checker is not a declaration')

# AND THE MEASUREMENT ITSELF, so a regression surfaces as a named list rather
# than as a checker quietly scoring uncontrolled.
_dead = []
for _root, _dirs, _files in os.walk(os.path.join(REPO, 'tests')):
    _dirs[:] = [d for d in _dirs if d != '__pycache__']
    for _f in _files:
        if not (_f.endswith('.py') or _f.endswith('.js')):
            continue
        _p = os.path.join(_root, _f)
        _src = io.open(_p, encoding='utf-8', errors='replace').read()
        if 'CONTROLS_FOR' not in _src:
            continue
        if not M.declared_controls(M.strip(_p, _src)):
            _dead.append(os.path.relpath(_p, REPO).replace(os.sep, '/'))
check(not _dead,
      'EVERY CONTROLS_FOR under tests/ parses to a subject (these declare '
      'nothing: %s)' % _dead)

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
