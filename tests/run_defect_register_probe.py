"""Control for tools/defect_register.py.

    python tests/run_defect_register_probe.py

The register's only value is that its records are true. A register that accepts
a commit that does not exist, a made-up detection method, or the same defect
twice is worse than none: its LENGTH reads as evidence of thoroughness.

So the arms below attack it rather than exercise it -- and the report's own
caveats are asserted too, because a density figure quoted without them is the
failure this platform keeps recording. A number nobody qualifies gets quoted.

RUNS IN A THROWAWAY WORKTREE. It never writes this clone's register.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = 'tools/defect_register.py'
REG = 'docs/defect-density-register.json'
R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True, text=True)


def run(wt, *args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=wt,
                       capture_output=True, text=True, timeout=300)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


TREE_BEFORE = git(REPO, 'status', '--porcelain').stdout
wt = os.path.join(tempfile.gettempdir(), 'defreg-probe-%d' % os.getpid())
add = git(REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD')
check('A0 the throwaway worktree was created', add.returncode, 0)
try:
    # The worktree is at HEAD, which may not carry the tool or the register.
    for rel in (TOOL, REG):
        src = os.path.join(REPO, rel.replace('/', os.sep))
        if os.path.isfile(src):
            dst = os.path.join(wt, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            io.open(dst, 'wb').write(io.open(src, 'rb').read())

    real = git(wt, 'rev-parse', 'HEAD').stdout.strip()[:12]

    # ── A. it reports and it validates ─────────────────────────────────────
    rc, out = run(wt, '--report')
    check('A1 --report runs', rc, 0)
    rc, out = run(wt, '--check')
    check('A2 --check passes on the committed register', rc, 0)

    # ── B. IT REFUSES WHAT IT CANNOT VERIFY ────────────────────────────────
    rc, out = run(wt, '--add', '--commit', 'deadbeefdead', '--app', 'x',
                  '--layer', 'product', '--severity', 'high',
                  '--method', 'code-review', '--summary', 'nope')
    check('B1 a commit that does not exist is REFUSED', rc, 2)
    check('B2 and it says so', 'no such commit' in out, True)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'x',
                  '--layer', 'product', '--severity', 'high',
                  '--method', 'vibes', '--summary', 'nope')
    check('B3 an invented detection method is REFUSED', rc, 2)
    check('B4 because the matrix is meaningless with free text',
          '--method must be one of' in out, True)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'x',
                  '--layer', 'guesswork', '--severity', 'high',
                  '--method', 'code-review', '--summary', 'nope')
    check('B5 an invented layer is REFUSED', rc, 2)

    # ── C. it derives rather than trusting what it was told ────────────────
    rc, out = run(wt, '--add', '--commit', real, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--summary', 'a probe fixture')
    check('C1 a real commit is accepted', rc, 0)
    doc = json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                            encoding='utf-8'))
    rec = [r for r in doc['records'] if r['summary'] == 'a probe fixture'][0]
    check('C2 the date is DERIVED, not supplied', len(rec['date']), 10)
    check('C3 the files are DERIVED', isinstance(rec['files'], list), True)
    check('C4 and so are the line counts',
          isinstance(rec['lines_added'], int) and isinstance(rec['lines_removed'], int),
          True)

    # ── D. the same defect cannot be counted twice ─────────────────────────
    before = len(json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                                   encoding='utf-8'))['records'])
    rc, out = run(wt, '--add', '--commit', real, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--summary', 'a probe fixture')
    after = len(json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                                  encoding='utf-8'))['records'])
    check('D1 a duplicate is not appended', after, before)
    check('D2 and it says so', 'already registered' in out, True)

    # ...but the SAME COMMIT with a DIFFERENT defect is a different record.
    # 5b98fd27 fixed three distinct faults in one commit, and collapsing them
    # would undercount by two.
    rc, out = run(wt, '--add', '--commit', real, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--summary', 'a SECOND fixture')
    after2 = len(json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                                   encoding='utf-8'))['records'])
    check('D3 one commit CAN carry several distinct defects', after2, before + 1)

    # ── E. --check catches a register that has stopped being true ──────────
    p = os.path.join(wt, REG.replace('/', os.sep))
    doc = json.load(io.open(p, encoding='utf-8'))
    doc['records'].append(dict(doc['records'][0], commit='000000000000'))
    io.open(p, 'w', encoding='utf-8', newline='').write(json.dumps(doc, indent=2))
    rc, out = run(wt, '--check')
    check('E1 a record pointing at no commit FAILS --check', rc, 1)
    check('E2 and names it', '000000000000' in out, True)

    # ── F. THE REPORT REFUSES TO BE QUOTED BARE ────────────────────────────
    rc, out = run(wt, '--report')
    check('F1 the density is printed against a MEASURED denominator',
          'MEASURED denominator' in out, True)
    check('F2 an app with no records is called unswept, not clean',
          'not a clean one' in out, True)
    check('F3 and the honest signal is stated as consecutive zero-finding '
          'sweeps by DIFFERENT methods',
          'DIFFERENT METHODS' in out, True)
    check('F4 the denominator states what it does NOT count',
          'It does not count' in out, True)
    check('F5 and the coverage matrix is printed beside the number',
          'COVERAGE -- which methods' in out, True)
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
print('defect-register: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
