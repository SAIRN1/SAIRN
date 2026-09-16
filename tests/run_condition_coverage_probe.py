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

print('4. it REFUSES to run on a dirty tree')
dirty = subprocess.run(['git', 'status', '--porcelain'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', cwd=REPO).stdout.strip()
tmpf = None
if not dirty:
    tmpf = os.path.join(REPO, 'tools', '_probe_dirty_marker.tmp')
    io.open(tmpf, 'w', encoding='utf-8').write('x')
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'condition_coverage.py')],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
if tmpf and os.path.exists(tmpf):
    os.remove(tmpf)
check('4a  a dirty tree exits 2, not 0 or 1', p.returncode == 2, 'exit %d' % p.returncode)
check('4b  and it says WHY -- a restore cannot be verified against a modified baseline',
      'WORKING TREE IS DIRTY' in (p.stdout or ''))

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
    r = C2.sweep('planted', 'api/_lib/planted.js', 'api/_lib/planted.test.js')
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
