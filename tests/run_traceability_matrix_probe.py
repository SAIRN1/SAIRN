"""Control for tools/traceability_matrix.py.

    python tests/run_traceability_matrix_probe.py

The matrix is the document an outside auditor would read, so the thing that
matters most about it is not that it is complete -- it is that it CANNOT
quietly stop matching the repo. `--check` is that mechanism, and a mechanism
nobody has watched fail is not a mechanism.

CLAUDE.md is explicit about the trap this design walks past: a GENERATED gate
that must be regenerated after every edit reproduces the silent-failure shape it
exists to catch (see the superseded header on tools/sairn_build_load_gates.py).
So arm B is the important one -- change a SOURCE, and `--check` must go red.

RUNS IN A THROWAWAY WORKTREE. It never writes this clone.
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['traceability_matrix.py']

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
TOOL = 'tools/traceability_matrix.py'
OUT = 'docs/traceability-matrix.md'
# Files the throwaway worktree needs that HEAD may not carry. The worktree is
# created at HEAD, so anything this tool has newly started importing has to be
# copied in beside it -- otherwise the probe fails with ModuleNotFoundError and
# says nothing at all about the tool. Added 2026-09-13 when the generator began
# importing the closing-error guard.
CARRY = [TOOL, OUT, 'tools/closing_error.py']
R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')


def run(wt, *args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=wt,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


TREE_BEFORE = git(REPO, 'status', '--porcelain').stdout
wt = os.path.join(tempfile.gettempdir(), 'trace-probe-%d' % os.getpid())
add = git(REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD')
check('A0 the throwaway worktree was created', add.returncode, 0)
try:
    # The worktree is at HEAD, which may not carry the tool being tested.
    for rel in CARRY:
        src = os.path.join(REPO, rel.replace('/', os.sep))
        if os.path.isfile(src):
            dst = os.path.join(wt, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            io.open(dst, 'wb').write(io.open(src, 'rb').read())

    # ── A. it generates, and --check agrees with what it just wrote ─────────
    rc, out = run(wt)
    check('A1 it generates without error', rc, 0)
    doc = io.open(os.path.join(wt, OUT.replace('/', os.sep)), encoding='utf-8').read()
    check('A2 and the document is not empty', len(doc) > 2000, True)
    rc, out = run(wt, '--check')
    check('A3 --check passes on what it just generated', rc, 0)

    # ── B. THE ONE THAT MATTERS: a changed SOURCE makes --check go red ──────
    # A generated document that cannot notice its own sources moving is the
    # exact failure CLAUDE.md records against a generated gate.
    gate = os.path.join(wt, 'tools', 'sairn_push_gate_hook.py')
    original = io.open(gate, 'rb').read()
    io.open(gate, 'wb').write(original.replace(
        b'GUARD_TESTS = [',
        b"GUARD_TESTS = [\n    ('tests/zz_probe_guard.js', 'a probe requirement',"
        b" 'a probe defect'),", 1))
    rc, out = run(wt, '--check')
    check('B1 a NEW guard test makes --check fail', rc, 1)
    check('B2 and it says the document no longer matches its sources',
          'no longer matches its sources' in out, True)
    check('B3 and it names the command that fixes it',
          'python tools/traceability_matrix.py' in out, True)
    rc, _ = run(wt)
    rc, out = run(wt, '--check')
    check('B4 regenerating makes it agree again', rc, 0)
    doc = io.open(os.path.join(wt, OUT.replace('/', os.sep)), encoding='utf-8').read()
    check('B5 and the new requirement is IN the document',
          'a probe requirement' in doc, True)
    io.open(gate, 'wb').write(original)
    run(wt)

    # ── C. the gaps are reported, not hidden ───────────────────────────────
    doc = io.open(os.path.join(wt, OUT.replace('/', os.sep)), encoding='utf-8').read()
    # THE ANCHOR MOVED ON 2026-09-15 AND THIS ARM CAUGHT IT, which is the arm
    # working. Section 5 used to lead with the RATIO; it now leads with the
    # ABSOLUTE COUNT, because the ratio improved for five days while the count
    # rose. The arm follows the headline rather than pinning the old sentence.
    check('C1 it reports how many tests are UNTRACED, as the HEADLINE',
          re.search(r'###\s+\d+ test files are traced to no stated requirement',
                    doc) is not None, True)
    check('C1b and the ratio appears BELOW it, marked as context rather than '
          'the figure -- leading with a ratio is what let the page improve '
          'while the backlog grew',
          doc.find('are traced to no stated requirement')
          < doc.find('For context and not as the headline'), True)
    check('C2 and lists them', doc.count('\n- `tests/') > 20, True)
    check('C3 and reports citations pointing at a file that does not exist',
          'Citations pointing at a file that does not exist' in doc, True)
    check('C4 and states what it cannot tell you',
          'What this matrix cannot tell you' in doc, True)
    check('C5 including that a traced test may not PROVE its requirement',
          'Whether the assertion is strong enough' in doc, True)

    # ── D. app attribution refuses to guess ────────────────────────────────
    sys.path.insert(0, os.path.join(wt, 'tools'))
    for m in ('traceability_matrix',):
        sys.modules.pop(m, None)
    import traceability_matrix as tm            # noqa: E402
    names = tm.apps()
    check('D1 a single named app is attributed',
          tm.app_of('a row about sairnvet only', names), 'sairnvet')
    check('D2 TWO named apps is PLATFORM, not the first one',
          tm.app_of('sairnvet and sairnlaw both', names), 'PLATFORM')
    check('D3 no named app is PLATFORM', tm.app_of('a generic row', names), 'PLATFORM')

    # ── E. the document is valid markdown tables ───────────────────────────
    p = subprocess.run([sys.executable, 'tools/md_table_check.py', OUT], cwd=wt,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    check('E1 every generated table is well formed', p.returncode, 0)
    check('E2 and the checker actually looked at it',
          OUT.replace('/', os.sep) in p.stdout or OUT in p.stdout, True)
finally:
    git(REPO, 'worktree', 'remove', '--force', wt)
    git(REPO, 'worktree', 'prune')

# ── THE THIRD CITING SOURCE (2026-09-15) ────────────────────────────────────
# A declared REQUIREMENT in a test file's own header. It is the WEAKEST of the
# three -- nothing outside the file corroborates it -- so the arms that matter
# are the ones proving it cannot be satisfied by writing nothing.
# Loaded from THIS CLONE by path, under its own module name. The worktree copy
# is already in sys.modules by now and its directory has been removed, so a
# plain import would hand back a module whose REPO points at a path that no
# longer exists -- and the failure would look like a defect in the rule rather
# than in the loading.
import importlib.util                                            # noqa: E402
_spec = importlib.util.spec_from_file_location(
    'tm_live', os.path.join(REPO, 'tools', 'traceability_matrix.py'))
tm_live = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tm_live)

_REAL_ALL = tm_live.all_tests
_REAL_REPO = tm_live.REPO
_TMP = tempfile.mkdtemp(prefix='trace-req-probe-')
try:
    GOOD = ('a money value can never be built from a non-number, so nothing '
            'reaches a ledger coerced from a string')
    cases = {
        'good.test.js': '// good.test.js\n// REQUIREMENT: ' + GOOD + '\n',
        'short.test.js': '// short.test.js\n// REQUIREMENT: tests money\n',
        'echo.test.js': '// echo.test.js\n// REQUIREMENT: echo\n',
        'none.test.js': '// none.test.js\n// just a test file\n',
        'buried.test.js': ('// buried.test.js\n' + ('// filler\n' * 500)
                           + '// REQUIREMENT: ' + GOOD + '\n'),
    }
    for _n, _body in cases.items():
        io.open(os.path.join(_TMP, _n), 'w', encoding='utf-8',
                newline='\n').write(_body)
    tm_live.REPO = _TMP
    tm_live.all_tests = lambda: sorted(cases)
    got = dict(tm_live.declared_requirements())
finally:
    tm_live.REPO = _REAL_REPO
    tm_live.all_tests = _REAL_ALL
    shutil.rmtree(_TMP, ignore_errors=True)

check('R1 a substantive declaration is a citation', 'good.test.js' in got, True)
check('R2 CONTROL a declaration too short to state anything is NOT',
      'short.test.js' in got, False)
check('R3 CONTROL a declaration that is only the filename back again is NOT -- '
      'that is an echo and not a requirement', 'echo.test.js' in got, False)
check('R4 CONTROL a file with no declaration is NOT', 'none.test.js' in got, False)
check('R5 CONTROL a declaration buried past the header is NOT -- a file\'s '
      'requirement belongs where a reader meets the file',
      'buried.test.js' in got, False)
check('R6 exactly one of the five qualifies, so the rule discriminates',
      len(got), 1)
check('R7 the three sources carry DISTINCT labels, so a reader can see which '
      'files rest on the weakest one',
      sorted(set(x for v in tm_live.traced().values() for x in v)),
      ['GUARD_TESTS', 'declared', 'index'])
check('R8 the declared source is not carrying the whole figure -- if it were, '
      'the metric would have been moved rather than closed',
      len([1 for v in tm_live.traced().values() if v == ['declared']])
      < len(tm_live.traced()) // 2, True)

check('Z1 the worktree was cleaned up', os.path.exists(wt), False)
check('Z2 and this clone is exactly as it was',
      git(REPO, 'status', '--porcelain').stdout, TREE_BEFORE)

for k in sorted(R):
    ok, actual, expected = R[k]
    print('  %-6s %s' % ('ok' if ok else 'FAIL', k))
    if not ok:
        print('         expected %r, got %r' % (expected, actual))
bad = [k for k in R if not R[k][0]]
print()
print('traceability-matrix: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
