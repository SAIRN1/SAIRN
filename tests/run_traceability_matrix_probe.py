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
import io
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = 'tools/traceability_matrix.py'
OUT = 'docs/traceability-matrix.md'
R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True, text=True)


def run(wt, *args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=wt,
                       capture_output=True, text=True, timeout=600)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


TREE_BEFORE = git(REPO, 'status', '--porcelain').stdout
wt = os.path.join(tempfile.gettempdir(), 'trace-probe-%d' % os.getpid())
add = git(REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD')
check('A0 the throwaway worktree was created', add.returncode, 0)
try:
    # The worktree is at HEAD, which may not carry the tool being tested.
    for rel in (TOOL, OUT):
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
    check('C1 it reports how many tests are UNTRACED',
          'test files are traced to a stated requirement' in doc, True)
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
                       capture_output=True, text=True, timeout=300)
    check('E1 every generated table is well formed', p.returncode, 0)
    check('E2 and the checker actually looked at it',
          OUT.replace('/', os.sep) in p.stdout or OUT in p.stdout, True)
finally:
    git(REPO, 'worktree', 'remove', '--force', wt)
    git(REPO, 'worktree', 'prune')

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
