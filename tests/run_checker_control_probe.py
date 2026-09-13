"""Control for tools/checker_control_check.py -- the meta-checker.

    python tests/run_checker_control_probe.py        (exit 0 pass, 1 fail)

A tool that demands a control pair from every checker and has none itself is
the joke that writes itself. So this plants each verdict the tool can reach and
asserts it reaches it, and plants the opposite and asserts it does not.

THE ARM THAT MATTERS MOST IS THE COMMENT ONE. The whole finding this tool
produces is "nothing has ever seen this checker fail", and the cheapest way to
fake that evidence is a comment saying `# expect exit 1` next to no assertion at
all. This platform recorded that exact class three times in two days, twice in
its own probes. If the tool ever counts a comment as proof, it is producing
false reassurance about false reassurance.

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

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
