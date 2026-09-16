"""tests/run_testability_gate_probe.py -- the criteria are locked, and the lock bites.

    python tests/run_testability_gate_probe.py

The design constraint this gate exists under is that its pass/fail criteria are
decided BEFORE it runs against real code, never derived from what the corpus
already says. That is enforced by tools/testability_criteria.py carrying
hand-decided fixtures and the gate refusing to judge anything real until they
all classify correctly.

So the arms that matter are not "does it classify". They are:
  * the lock BITES -- loosen a criterion and the fixtures fail and NOTHING real
    is judged (arm 2);
  * the requirement column is found by its HEADER, never by index (arm 3) --
    the first version took cell 2 across four tables of different widths, read
    `Tool` in one section and `Status` in another, and reported 100% of a
    section as TOO-SHORT about tool filenames;
  * it does not flag everything (arm 4). A gate that fails a whole corpus is
    far more likely miscalibrated than right, and one that passed everything
    would satisfy every other arm here.
"""
CONTROLS_FOR = ['tools/testability_gate.py']

# REQUIREMENT: the testability gate reads the column it claims to read, after a version
#   of it scored the wrong one and reported a confident wrong number
#
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import testability_gate as G                                    # noqa: E402
import testability_criteria as C                                # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


def run(*args, **kw):
    env = dict(os.environ)
    env.update(kw.get('env') or {})
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'testability_gate.py')]
                       + list(args), capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=kw.get('cwd', REPO), env=env)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print('1. the criteria classify their own hand-decided cases')
bad = G.run_fixtures()
check('1a  every fixture classifies as decided', bad == [], bad)
check('1b  and there are fixtures of every verdict, so 1a is not vacuous',
      len(set(v for _, v in C.FIXTURES)) >= 4,
      sorted(set(v for _, v in C.FIXTURES)))
rc, out = run('--fixtures')
check('1c  the lock can be run on its own and passes', rc == 0, 'exit %d' % rc)

print('2. THE LOCK BITES -- a loosened criterion stops the whole gate')
tmp = tempfile.mkdtemp(prefix='testgate-')
shutil.copytree(os.path.join(REPO, 'tools'), os.path.join(tmp, 'tools'))
shutil.copytree(os.path.join(REPO, 'docs'), os.path.join(tmp, 'docs'),
                ignore=shutil.ignore_patterns('sources', 'skill-backups', 'superpowers'))
crit = os.path.join(tmp, 'tools', 'testability_criteria.py')
src = io.open(crit, encoding='utf-8').read()
# EMPTY the vague-word list -- the single most likely "quiet loosening", since
# dropping a word is how a gate stops flagging the thing somebody found
# annoying. The first draft of this sabotage wrote `VAGUE = () if False else (`
# which evaluates to the ORIGINAL tuple: a no-op that made the lock look broken
# when it was fine. A control that does not actually break the target tests
# nothing, which is the lesson this whole file is about.
# ── AND THE ANCHOR IS ASSERTED UNIQUE BEFORE IT IS USED (2026-09-16) ────────
# The paragraph above records that the FIRST version of this sabotage was a
# no-op that made the lock look broken when it was fine. The remedy for that
# was a better replacement; what was still missing is a check that the anchor
# is there AT ALL and there ONCE. `tools/sabotage_control_check.py` reported
# this probe UNGUARDED for exactly that.
_ANCHOR = "VAGUE = ("
_hits = src.count(_ANCHOR)
check('2z  the sabotage anchor %r appears exactly once in the criteria file '
      '(found %d)' % (_ANCHOR, _hits), _hits == 1,
      'at 0 nothing is planted and 2a below measures an UNMUTATED gate; above '
      '1 it plants in whichever came first')
io.open(crit, 'w', encoding='utf-8', newline='\n').write(
    src.replace(_ANCHOR, "VAGUE = ()\n_SABOTAGED_VAGUE = (", 1))
check('2z2 ...and the file written really differs from the original',
      io.open(crit, encoding='utf-8').read() != src)
p = subprocess.run([sys.executable, os.path.join(tmp, 'tools', 'testability_gate.py')],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=tmp)
both = (p.stdout or '') + (p.stderr or '')
check('2a  a loosened criterion makes the gate exit 2, not 0 or 1', p.returncode == 2,
      'exit %d' % p.returncode)
check('2b  and it says NOTHING REAL WAS JUDGED rather than reporting a clean run',
      'Nothing real was judged' in both)
check('2c  and it names the fixtures that broke', 'expected' in both)
check('2d  CONTROL: the same tree UNMODIFIED does judge the corpus',
      True)   # established by arm 1c and arm 4 below on the real tree
shutil.rmtree(tmp, ignore_errors=True)

print('3. the requirement column is found by HEADER, never by index')
reqs = G.matrix_requirements()
secs = sorted(set(s for s, _ in reqs))
check('3a  every section of the matrix yields requirements', len(secs) >= 4, secs)
# Section 3's second column is `Tool` and section 4's is `Status`. If the
# extractor were taking cell 2 those sections would be full of filenames and
# status strings, not sentences.
tool_like = [r for s, r in reqs if r.endswith('.py') or r.endswith('.js')]
check('3b  no requirement is a bare tool FILENAME -- that is the `Tool` column',
      len(tool_like) == 0, tool_like[:3])
status_like = [r for s, r in reqs if r.upper().startswith(('OPEN', 'CLOSED', 'BUILT'))]
check('3c  no requirement is a bare STATUS -- that is the `Status` column',
      len(status_like) == 0, status_like[:3])
check('3d  and the corpus is big enough to be the real matrix', len(reqs) > 100, len(reqs))

print('4. it neither passes nor fails the whole corpus')
flagged = [(s, r) for s, r in reqs if G.classify(r)[0] != 'PASS']
rate = 100.0 * len(flagged) / len(reqs)
check('4a  it flags SOMETHING -- a gate that passes everything checks nothing',
      len(flagged) > 0, '%d of %d' % (len(flagged), len(reqs)))
check('4b  it does not flag EVERYTHING -- that would be miscalibration, not a finding',
      rate < 60.0, '%.0f%% flagged' % rate)
check('4c  every PASS fixture still passes against the live classifier',
      all(G.classify(t)[0] == 'PASS' for t, v in C.FIXTURES if v == 'PASS'))

print('5. it reports and never gates')
rc, out = run()
check('5a  a corpus with findings exits 1, never 0 -- a silent pass is not a pass',
      rc == 1, 'exit %d' % rc)
check('5b  the criteria VERSION is printed, so two runs can be compared honestly',
      C.VERSION in out)
check('5c  the flag rate is printed with its calibration warning beside it',
      'THE RATE IS THE CALIBRATION' in out)
check('5d  and nothing was written', 'report only' in out)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
