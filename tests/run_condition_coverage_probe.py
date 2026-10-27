"""tests/run_condition_coverage_probe.py -- the mutation harness mutates the
right thing, restores what it touched, and can be shown to find a real gap.

    python tests/run_condition_coverage_probe.py

THIS TOOL WRITES TO REAL SOURCE FILES, so the arms that matter are not about
its findings. They are about whether it can be trusted to put the file back:

  * the parser must not see an operator inside a comment, a string or a
    template literal -- mutating one rewrites a user-facing message while
    reporting it as logic;
  * a CONTROL asserts real operators ARE found, or a parser that saw nothing
    would satisfy every arm above;
  * the restore is verified, retried, and escalated to `git checkout` rather
    than left ambiguous -- the first version reported RESTORED: NO on a file
    that was byte-identical to HEAD, a read that beat the write to disk;
  * and the harness must find a PLANTED gap: an operand added to a copy of an
    engine with no test covering it must come back SURVIVED.
"""

# ── A STABLE LAST LINE (2026-10-20, cody b28) ─────────────────────────────
# AT THE TOP, NOT THE END, FOR TWO REASONS. (1) This probe calls sys.exit()
# at module level; SystemExit propagates out of the module body, so an
# atexit.register() below it is never reached -- b27 appended it and
# measured 0 of 12. (2) atexit runs handlers in REVERSE registration order,
# so being registered FIRST is what makes this line print LAST.
# THE CONCEPT: this probe must print ONE deterministic final line on every
#   exit path, so docs/known-red-suites.json can record a tail the runner
#   really produces -- b26 measured this file's stored tail as one it CANNOT.
#
# atexit fires after the summary AND after sys.exit(1), which is the path an
# arm failure takes here. The line carries NO DIGITS on purpose:
# known_red_check.py normalises digits away, so a count would make a red run
# and a green run compare EQUAL. It is a CONSTANT rather than a verdict for
# two reasons, the second of which was a real bug in the first draft:
#   1. known_red_check.py decides RECOVERED from the run's GREEN list, by
#      exit code, so the tail's only job is to identify the last line.
#   2. atexit handlers receive NO exit code, and sys.last_value is an
#      interactive-mode artefact of an uncaught exception -- it is NOT set
#      by sys.exit(1), which is the path this probe takes. Reading it would
#      have printed one verdict for every run.
import atexit as _b27_atexit


def _b27_stable_last_line():
    try:
        print('SUITE-RESULT tests/run_condition_coverage_probe.py END')
    except Exception:
        pass


_b27_atexit.register(_b27_stable_last_line)
# REQUIREMENT: condition coverage counts each sub-condition of a compound test
#   separately, so a branch that is never exercised on one operand is not
#   reported as covered
#
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Arm 4 appends to a TRACKED engine (and restores it). An import would run
# that, so an import is refused -- the shape CHECK 5e calls UNGUARDED.
if __name__ != '__main__':
    raise ImportError('tests/run_condition_coverage_probe.py modifies a tracked '
                      'engine in arm 4; run it as a script, never import it')
sys.path.insert(0, os.path.join(REPO, 'tools'))
import condition_coverage as C                                  # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


print('1. the parser sees code, never prose')
for name, src, want in C.FIXTURES:
    check('1  ' + name, len(C.operands(src)) == want,
          'expected %d got %d' % (want, len(C.operands(src))))

print('2. the mutation is the minimal one, and reversible in meaning')
for name, src, op, want in C.MUTATE_FIXTURES:
    ops = C.operands(src)
    check('2  ' + name, ops and C.mutate(src, ops[0]['pos'], op) == want)

print('3. offsets survive stripping -- a position must point at the REAL file')
src = "// a && b\nvar m = 'x || y';\nif (p && q) go();\n"
ops = C.operands(src)
check('3a  exactly one operand found in that sample', len(ops) == 1, len(ops))
check('3b  and it is the one on line 3', ops and ops[0]['line'] == 3,
      ops[0]['line'] if ops else None)
check('3c  mutating it changes ONLY that operator',
      C.mutate(src, ops[0]['pos'], '&&') == "// a && b\nvar m = 'x || y';\nif (p || q) go();\n")

print('4. it REFUSES to run when a MEASURED engine is modified')
# RE-AIMED cody b53. This arm made the tree dirty with an UNTRACKED marker and
# looked for 'WORKING TREE IS DIRTY'. The tool has since scoped its refusal to
# the engines and suites it measures, ignoring untracked files on purpose (its
# own comment: one stray file made it unrunnable platform-wide), and reworded
# the message. So 4b was red on every run: the marker no longer counts as
# dirt, and the sentence it looked for no longer exists. The arm now dirties
# a MEASURED engine -- one appended comment line -- and restores it from a
# byte snapshot, checked byte-identical.
eng = os.path.join(REPO, C.ENGINES[0][1])
snap = io.open(eng, 'rb').read()
try:
    io.open(eng, 'ab').write(b'\n// run_condition_coverage_probe arm 4: temporary dirt\n')
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'condition_coverage.py')],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
finally:
    io.open(eng, 'wb').write(snap)
check('4a  a modified engine exits 2, not 0 or 1', p.returncode == 2, 'exit %d' % p.returncode)
check('4b  and it says WHY -- the engine on disk is not the one that would be mutated',
      'AN ENGINE OR ITS SUITE IS MODIFIED' in (p.stdout or ''), (p.stdout or '')[-300:])
check('4c  and the engine is byte-identical again after the arm',
      io.open(eng, 'rb').read() == snap)

print('5. THE PLANTED GAP -- it must find an operand no test covers')
tmp = tempfile.mkdtemp(prefix='condcov-')
os.makedirs(os.path.join(tmp, 'api', '_lib'))
os.makedirs(os.path.join(tmp, 'tools'))
shutil.copy(os.path.join(REPO, 'tools', 'condition_coverage.py'),
            os.path.join(tmp, 'tools', 'condition_coverage.py'))
eng = os.path.join(tmp, 'api', '_lib', 'planted.js')
io.open(eng, 'w', encoding='utf-8', newline='\n').write(
    "function f(a, b) { return a && b; }\n"
    "function untested(x, y) { return x && y; }\n"
    "module.exports = { f: f, untested: untested };\n")
suite = os.path.join(tmp, 'api', '_lib', 'planted.test.js')
io.open(suite, 'w', encoding='utf-8', newline='\n').write(
    "const assert = require('assert');\n"
    "const m = require('./planted.js');\n"
    "assert.strictEqual(m.f(true, false), false);\n"   # covers f's &&
    "console.log('1 passed');\n")
sys.path.insert(0, os.path.join(tmp, 'tools'))
C2 = C
old_repo, old_engines = C2.REPO, C2.ENGINES
try:
    C2.REPO = tmp
    C2.ENGINES = [('planted', 'api/_lib/planted.js', 'api/_lib/planted.test.js')]
    # root= IS REQUIRED NOW (cody b53): sweep() refuses to default it to REPO,
    # so this arm crashed with ValueError and never reached 5a-5e. The planted
    # sandbox IS the root.
    r = C2.sweep('planted', 'api/_lib/planted.js', 'api/_lib/planted.test.js', root=tmp)
finally:
    C2.REPO, C2.ENGINES = old_repo, old_engines
check('5a  both operands were found', r['operands'] == 2, r['operands'])
check('5b  the COVERED one is killed', r['killed'] == 1, r['killed'])
check('5c  the UNCOVERED one SURVIVES -- this is the finding the tool exists for',
      r['survived'] == 1, r['survived'])
check('5d  every mutation actually applied -- a SURVIVED from a no-op mutation '
      'would report a TESTED operand as untested',
      r['not_applied'] == 0, r['not_applied'])
check('5e  and the file was restored byte-identical',
      r['restored_byte_identical'], r.get('restored_how'))
shutil.rmtree(tmp, ignore_errors=True)

print('6. the real engines are named, and the suites were READ not guessed')
check('6a  four Tier A engines are registered', len(C.ENGINES) == 4, len(C.ENGINES))
for key, engine, suite in C.ENGINES:
    check('6b  %-16s engine and suite both exist on disk' % key,
          os.path.exists(os.path.join(REPO, engine)) and
          os.path.exists(os.path.join(REPO, suite)))
check('6c  care-charges points at its REAL suite, which does NOT follow the '
      '<engine>.test.js convention',
      dict((k, s) for k, _e, s in C.ENGINES)['care-charges']
      == 'tests/sairncare/test-care-charges.js')

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
