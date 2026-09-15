"""tests/run_dependency_graph_probe.py -- the graph analysis can be shown to
FIRE on a real chokepoint and to STAY QUIET on a genuinely redundant one.

    python tests/run_dependency_graph_probe.py

THE TWO WAYS THIS ANALYSIS GOES WRONG, and they pull opposite ways:

  * TOO EAGER -- an articulation-point list that names half the tree is a
    single-point-of-failure report nobody reads. Section 3 pins that a helper
    with one requirer is NOT reported as a wide risk, and that a cycle has no
    cut vertex at all.
  * TOO NARROW -- a pair search that has quietly degenerated into a second copy
    of the articulation search finds nothing on a four-cycle, which is exactly
    the graph item 53 exists for. Section 4 pins that case specifically.

AND THE ONE THAT IS NEITHER: a number that is TRUE OF THE WRONG POPULATION.
More than half the `.js` files under `api/` are `*.test.js`, so a blast radius
that counts them answers "how much of CI stops" while being read as "how much
of production stops". Section 5 pins the two populations apart and asserts they
actually differ, which is the only way to know the exclusion is doing anything.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import dependency_graph as G                                     # noqa: E402

# THIS FILE IS THE CONTROL FOR dependency_graph.py, declared rather than
# inferred -- tools/checker_control_check.py records three inference models
# that were each wrong within an hour, in three different directions.
#
# BOTH DIRECTIONS ARE HERE, which is what the declaration is claiming:
#   FIRES   3b/3d/4b -- a real cut vertex, a real 2-cut pair, a real blast
#           radius are REPORTED.
#   SILENT  3a/4a/4c/4d/5a -- a cycle has no cut vertex, adjacent corners are
#           not a pair, a leaf is not a chokepoint, and a graph cut by ONE node
#           yields no pair at all.
CONTROLS_FOR = ['dependency_graph.py']

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


print('1. the blind lock')
check('1a  every synthetic graph classifies as written', G.run_fixtures() == [],
      G.run_fixtures())
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'dependency_graph.py'),
                    '--fixtures'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('1b  the lock runs on its own and passes', p.returncode == 0, 'exit %d' % p.returncode)
check('1c  it is stated as running BEFORE the repo was read',
      'BEFORE the repo was read' in (p.stdout or ''))

print('2. a require() inside a comment or a string is not an edge')
# The real defect: the first scan reported `./_lib/heartbeat` unresolvable,
# which reads as a crash waiting to happen. It was a usage example in a comment
# INSIDE api/_lib/heartbeat.js. A graph that counts documentation as structure
# reports the platform it is describing rather than the one that runs.
src = ("// const a = require('./commented-out');\n"
       "/* const b = require('./block-commented'); */\n"
       "const c = require('./real');\n")
st = G.strip_js(src)
check('2a  a line-commented require is gone', "commented-out" not in st)
check('2b  a block-commented require is gone', "block-commented" not in st)
check('2c  CONTROL: the real one survives -- 2a and 2b would pass on a stripper '
      'that deleted everything', "require('./real')" in st, st.strip())

print('3. TOO EAGER -- the analysis must not call everything a chokepoint')
tri = {'A': {'B', 'C'}, 'B': {'A', 'C'}, 'C': {'A', 'B'}}
check('3a  a cycle has NO cut vertex -- every pair still has a way round',
      G.articulation(tri, set(tri)) == set())
# A leaf: one endpoint requires it and nothing else does. Removing it costs that
# one endpoint, and calling it an articulation point would drown the real ones.
leaf = {'hub': {'x', 'y'}, 'x': {'hub'}, 'y': {'hub'}}
ap = G.articulation(leaf, set(leaf))
check('3b  a leaf is not a cut vertex; the hub joining two of them is',
      ap == {'hub'}, sorted(ap))

print('4. TOO NARROW -- the pair search is not the single-point search again')
# THE LOAD-BEARING FIXTURE. A four-cycle has no articulation point whatsoever,
# so every single-point analysis is completely silent on it -- and it has
# exactly two fatal pairs, the opposite corners. A pair search that had
# collapsed into a copy of the articulation search returns nothing here and
# would look like a clean result.
cyc = {'A': {'B', 'D'}, 'B': {'A', 'C'}, 'C': {'B', 'D'}, 'D': {'C', 'A'}}
pairs, base_ap, iso = G.cut_pairs(cyc, set(cyc))
check('4a  the four-cycle has no single cut vertex at all', base_ap == [], base_ap)
check('4b  ...and exactly the two OPPOSITE pairs are fatal together',
      pairs == [('A', 'C'), ('B', 'D')], pairs)
check('4c  CONTROL: adjacent corners are NOT a pair -- removing A and B leaves '
      'C-D connected, so a pair search returning every pair would fail here',
      ('A', 'B') not in pairs and len(pairs) == 2, pairs)
# And a graph whose only weakness IS a single point must yield no pairs, or the
# two analyses would be reporting the same thing twice under different names.
path = {'A': {'B'}, 'B': {'A', 'C'}, 'C': {'B'}}
pp, pap, _ = G.cut_pairs(path, set(path))
check('4d  a graph cut by ONE node reports that node and no pair -- the two '
      'analyses do not double-count', pap == ['B'] and pp == [], (pap, pp))

print('5. THE POPULATION -- production is not CI')
prod = G.js_files(with_tests=False)
allf = G.js_files(with_tests=True)
tests = [f for f in allf if f.endswith('.test.js')]
check('5a  test files are excluded by default', not any(f.endswith('.test.js') for f in prod))
check('5b  ...and there are enough of them for it to matter -- more than half '
      'the files under api/ are tests',
      len(tests) > len(allf) / 2, '%d of %d' % (len(tests), len(allf)))
n_prod, e_prod, _ = G.build(include_env=False, with_tests=False)
n_all, e_all, _ = G.build(include_env=False, with_tests=True)
b_prod = G.blast(e_prod, n_prod)
b_all = G.blast(e_all, n_all)
key = 'api/_lib/license.js'
check('5c  the SAME node has a materially different blast radius in the two '
      'populations, so the exclusion is doing real work rather than being '
      'cosmetic', key in b_prod and b_all[key] > b_prod[key],
      'production %d vs with-tests %d' % (b_prod.get(key, -1), b_all.get(key, -1)))
check('5d  CONTROL: --with-tests really does put them back',
      any(f.endswith('.test.js') for f in allf))

print('6. what it reports about the real repo is reproducible')
r1 = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'dependency_graph.py'),
                     '--json'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
r2 = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'dependency_graph.py'),
                     '--json'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('6a  two runs on the same tree give the same answer -- set iteration '
      'order has flipped a checker on this platform before',
      r1.stdout == r2.stdout and r1.returncode == 0)
code = io.open(os.path.join(REPO, 'tools', 'dependency_graph.py'), encoding='utf-8').read()
code = '\n'.join(l for l in code.split('\n') if not l.strip().startswith('#'))
check('6b  it states what it CANNOT see rather than leaving the reader to '
      'assume the graph is complete',
      'cannot see' in code.lower() and 'SHARED BACKEND' in code.upper().replace('_', ' ')
      or 'RUNTIME call that is not a require' in code)
check('6c  the printed pair list says so when it stops printing, so a truncated '
      'display is not read as a complete analysis',
      'only the printing stops here' in code)

print('7. ITEM 91 -- the register shrinks by MEASUREMENT, not by decision')
# A single-point-of-failure list generated once and filed is a document. The
# arms below are about the failure that turns a live register back into one:
# a row somebody marked RETIRED while the thing was still a chokepoint.
rp = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'dependency_graph.py'),
                     '--register'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('7a  the real register passes against the live graph',
      rp.returncode == 0, (rp.stdout or '')[-300:])

REG = io.open(os.path.join(REPO, 'docs', 'SPOF-REGISTER.md'), encoding='utf-8').read()
rows = G.register_rows(REG)
check('7b  the parser reads real rows out of the real file, so 7a is not '
      'passing on an empty list', len(rows) >= 5, len(rows))
check('7c  every row carries an owner and a status in the vocabulary',
      all(r['owner'] and r['status'] in ('OPEN', 'ACCEPTED', 'RETIRED') for r in rows),
      [(r['component'], r['owner'], r['status']) for r in rows if
       r['status'] not in ('OPEN', 'ACCEPTED', 'RETIRED')])

# THE ARMS THAT MATTER, driven against the checker with a doctored register
# rather than asserted from its source.
import tempfile                                                  # noqa: E402
real_reg = G.REGISTER
tmpdir = tempfile.mkdtemp(prefix='spof-')


def with_register(text):
    path = os.path.join(tmpdir, 'reg.md')
    io.open(path, 'w', encoding='utf-8', newline=chr(10)).write(text)
    G.REGISTER = path
    try:
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = G.check_register()
        return rc, buf.getvalue()
    finally:
        G.REGISTER = real_reg


HEAD = '| Component | Owner | Status | Blast |\n|---|---|---|---|\n'
rc, out = with_register(HEAD)
check('7d  a register with NO rows is REFUSED -- every live chokepoint is '
      'reported unregistered, rather than an empty table reading as clean',
      rc == 1 and 'UNREGISTERED' in out, rc)

full = HEAD + ''.join('| `%s` | CC | OPEN | x |\n' % r['component'] for r in rows)
rc, out = with_register(full)
check('7e  CONTROL: the same rows marked OPEN pass -- 7d is not a checker that '
      'refuses everything', rc == 0, out[-200:])

retired = HEAD + ''.join('| `%s` | CC | %s | x |\n'
                         % (r['component'], 'RETIRED' if i == 0 else 'OPEN')
                         for i, r in enumerate(rows))
rc, out = with_register(retired)
check('7f  A ROW MARKED RETIRED WHILE THE COMPONENT IS STILL A CHOKEPOINT IS '
      'REFUSED -- retirement is a measurement, not a decision somebody makes',
      rc == 1 and 'NOT RETIRED' in out, out[-260:])

ghost = full + '| `api/does-not-exist.js` | CC | OPEN | x |\n'
rc, out = with_register(ghost)
check('7g  a row naming a component that is in no graph at all is reported -- '
      'renamed, deleted or mistyped',
      rc == 1 and ('NOT A NODE' in out or 'STALE' in out), out[-260:])

unowned = HEAD + ''.join('| `%s` | &mdash; | OPEN | x |\n' % r['component'] for r in rows)
rc, out = with_register(unowned)
check('7h  an unowned row is refused -- an entry nobody owns is a note',
      rc == 1 and 'NO OWNER' in out, out[-200:])

G.REGISTER = os.path.join(tmpdir, 'absent.md')
try:
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = G.check_register()
finally:
    G.REGISTER = real_reg
check('7i  a MISSING register is COULD-NOT-RUN (exit 2), never a clean pass -- '
      'could-not-tell is a third state', rc == 2 and 'COULD NOT RUN' in buf.getvalue(), rc)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
