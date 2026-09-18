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
    # ── THE SABOTAGE IS ASSERTED TO HAVE APPLIED (2026-09-16) ──────────────
    # tools/sabotage_control_check.py reported this probe UNGUARDED: it
    # replaced an anchor and never checked the anchor was there. UNIQUENESS
    # rather than presence, because `GUARD_TESTS = [` matching twice would
    # inject into whichever came first and B1 below would be asserting about a
    # list nobody chose.
    _anchor = b'GUARD_TESTS = ['
    _hits = original.count(_anchor)
    check('B0 the sabotage anchor appears exactly once in the push gate '
          '(found %d) -- at 0 nothing is planted and B1 measures an unmutated '
          'file' % _hits, _hits, 1)
    _mutated = original.replace(
        _anchor,
        b"GUARD_TESTS = [\n    ('tests/zz_probe_guard.js', 'a probe requirement',"
        b" 'a probe defect'),", 1)
    check('B0b ...and the mutated bytes really differ from the original',
          _mutated != original, True)
    io.open(gate, 'wb').write(_mutated)
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
        # WRAPPED ACROSS LINES, which is how every real one is written at this
        # repo's 72-column comment width. The first version matched only the
        # line carrying the keyword and rejected a 160-character requirement
        # for being under a 60-character floor.
        'wrapped.test.js': ('// wrapped.test.js\n'
                            '// REQUIREMENT: a money value can never be built\n'
                            '//   from a non-number, so nothing reaches a\n'
                            '//   ledger coerced from a string\n'
                            '//\n'),
        # ...and the continuation must STOP at a line that is not one, or the
        # rest of the header joins the requirement and any short declaration
        # passes by absorbing the prose under it.
        'stops.test.js': ('// stops.test.js\n'
                          '// REQUIREMENT: too short\n'
                          '// a separate comment line that is not indented\n'),
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
check('R6a a WRAPPED declaration is joined and counted -- the floor must '
      'measure the whole requirement, not the first line of it',
      'wrapped.test.js' in got, True)
check('R6b CONTROL the continuation STOPS at a line that is not one, so a '
      'short declaration cannot pass by absorbing the prose beneath it',
      'stops.test.js' in got, False)
check('R6 exactly two of the seven qualify, so the rule discriminates',
      len(got), 2)
check('R7 the three sources carry DISTINCT labels, so a reader can see which '
      'files rest on the weakest one',
      sorted(set(x for v in tm_live.traced().values() for x in v)),
      ['GUARD_TESTS', 'declared', 'index'])
check('R8 the declared source is not carrying the whole figure -- if it were, '
      'the metric would have been moved rather than closed',
      len([1 for v in tm_live.traced().values() if v == ['declared']])
      < len(tm_live.traced()) // 2, True)

# ══ E. THE ENUMERATOR AND THE DEAD-CITATION DROP (2026-09-18) ═══════════════
# all_tests() walked `tests/**` recursively and then listed exactly two `api`
# directories, so SIXTEEN real *.test.js files under api/sairndental/,
# api/sairncash/, api/_resources/ and api/agent/ were invisible -- and that
# number is the denominator under every coverage figure on this platform.
#
# THE ASSERTION IS AGAINST A DIFFERENT MECHANISM, NOT AGAINST THE FUNCTION
# ITSELF. `git ls-files` reads the index; all_tests() walks the filesystem.
# Comparing the function to a re-implementation of the same walk would be the
# generator-checking-its-own-output shape this repo already has a rule about
# (PR 1.8). Two mechanisms disagreeing is the finding; two mechanisms agreeing
# is the only version of this check worth running.
_gl = subprocess.run(['git', '-C', REPO, 'ls-files'], capture_output=True,
                     text=True, encoding='utf-8', errors='replace').stdout
_indexed = sorted(x.strip() for x in _gl.split('\n') if x.strip()
                  and ((x.strip().startswith('tests/')
                        and x.strip().endswith(('.js', '.py')))
                       or (x.strip().startswith('api/')
                           and x.strip().endswith('.test.js'))))
_walked = tm_live.all_tests()
check('N1 all_tests() agrees with the GIT INDEX exactly -- a different '
      'mechanism, not a second copy of the same walk',
      sorted(_walked), _indexed)
check('N2 ...and every api/ SUBDIRECTORY is reached, not just api/ and '
      'api/_lib/ -- the two that used to be hardcoded',
      sorted(set(os.path.dirname(x) for x in _walked
                 if x.startswith('api/'))) != ['api', 'api/_lib'], True)
check('N3 CONTROL the api/ subdirectories really are non-empty, so N2 is not '
      'passing on an absence',
      len([x for x in _walked if x.startswith('api/')
           and os.path.dirname(x) not in ('api', 'api/_lib')]) > 0, True)

# traced() must DROP a citation naming a file that is not on disk, and
# dead_citations() must REPORT it. Both directions, because dropping quietly is
# how a row promising coverage it does not have becomes a better number.
_cited = tm_live.traced()
_dead = tm_live.dead_citations()
check('N4 no cited file is missing from disk -- traced() counts only what is '
      'there', [t for t in _cited if not os.path.isfile(os.path.join(REPO, t))],
      [])
check('N5 the prose figure and the closing-error leg are ONE population -- '
      'they read 512 and 518 in the same run before this',
      len(_cited), len([t for t in _walked if t in _cited]))
check('N6 dead_citations() is REPORTED rather than folded into traced()',
      isinstance(_dead, list), True)
# THE CONTROL THAT MAKES E4/E6 MEAN ANYTHING. Both currently pass on an empty
# set -- there are no dead citations today, which is the point of having fixed
# them, and a check that only ever sees the clean case has never run. So one
# real cited file is made to LOOK absent by narrowing all_tests() for the
# duration, and the two questions are asked again: traced() must lose it, and
# dead_citations() must name it.
_real_all = tm_live.all_tests
# THE VICTIM MUST BE CITED BY A SOURCE THAT DOES NOT ITSELF READ all_tests().
# `declared` is scraped FROM the files all_tests() returns, so hiding such a
# file removes it from the raw citations too and it is simply gone rather than
# dead -- the first version of this control picked one and N8 failed for a
# reason that was about the control, not about the tool. An `index` or
# `GUARD_TESTS` citation lives in a document and survives the file vanishing,
# which is exactly the real-world shape: a row citing a deleted test.
_victim = sorted(t for t, srcs in _cited.items()
                 if 'index' in srcs or 'GUARD_TESTS' in srcs)[0]
try:
    tm_live.all_tests = lambda: [t for t in _real_all() if t != _victim]
    _c2 = tm_live.traced()
    _d2 = dict(tm_live.dead_citations())
finally:
    tm_live.all_tests = _real_all
check('N7 CONTROL with one cited file made to look absent, traced() DROPS it',
      _victim in _c2, False)
check('N8 CONTROL ...and dead_citations() NAMES it, so the drop is reported '
      'rather than silent', _victim in _d2, True)
check('N9 CONTROL ...and it drops exactly that one, not the population',
      len(_c2), len(_cited) - 1)
check('N10 the real tool is restored after the control', tm_live.all_tests,
      _real_all)

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
