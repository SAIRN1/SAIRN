"""Probe tools/mutation_anchor_check.py, by attacking it.

The tool reports ZERO bad anchors against the real repo. A checker that finds
nothing is indistinguishable from one that looks at nothing -- so every arm here
plants the defect on a throwaway fixture and asserts the tool sees it.

WHY THE TOOL EXISTS, in one line each:
  * an anchor that matches ZERO times plants nothing, so the control stops
    testing (dnt_vendor arm 4, a refactor collapsed an else-if);
  * an anchor that matches TWICE probes whichever came first, i.e. neither on
    purpose;
  * a probe that mutates a tracked file IN PLACE and has no `__main__` guard
    mutates that file when merely IMPORTED -- and an interrupted import leaves
    it mutated. That is not hypothetical: the first version of the tool imported
    the probes, hung, was killed, and left api/_lib/dental-guardian.js modified.

ARM 4 IS THE ONE THAT MATTERS: the tool must never IMPORT a probe to read it.
It runs the checker against a fixture probe that writes a sentinel file at
import time, and asserts the sentinel was never written.

Run: python tests/run_mutation_anchor_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'mutation_anchor_check.py')

failures = []


def check(name, ok, detail=''):
    print('  %-4s %-64s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        failures.append(name)


def run_against(tmp):
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    shim = os.path.join(tmp, '_runner.py')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        'import sys\n'
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import mutation_anchor_check as M\n'
        'M.REPO = %r\n' % tmp +
        'sys.exit(M.main(["x"]))\n')
    p = subprocess.run([sys.executable, shim], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def fixture(probe_body, target_name='app.js', target_body='function f(){ return 1; }\n'):
    tmp = tempfile.mkdtemp(prefix='anchor_probe_')
    os.makedirs(os.path.join(tmp, 'tests'))
    io.open(os.path.join(tmp, target_name), 'w', encoding='utf-8', newline='\n').write(target_body)
    io.open(os.path.join(tmp, 'tests', 'fx_probe.py'), 'w', encoding='utf-8',
            newline='\n').write(probe_body)
    return tmp


HEAD = "import os\nTARGET = 'app.js'\n"

print('MUTATION ANCHOR CHECK PROBE -- every arm plants a defect and demands it be seen\n')

# ── 1. an anchor that no longer matches
tmp = fixture(HEAD + "MUTATIONS = [\n ('1. gone', 'return 42;', 'return 0;'),\n]\n")
rc, out = run_against(tmp)
check('1a  ANCHOR-0 is reported', 'ANCHOR-0' in out, '')
check('1b  and the exit code is non-zero', rc == 1, 'exit %d' % rc)
shutil.rmtree(tmp, ignore_errors=True)

# ── 2. an anchor that matches twice
tmp = fixture(HEAD + "MUTATIONS = [\n ('2. ambiguous', 'return 1;', 'return 0;'),\n]\n",
              target_body='function a(){ return 1; }\nfunction b(){ return 1; }\n')
rc, out = run_against(tmp)
check('2a  ANCHOR-2 is reported', 'ANCHOR-2' in out, 'an arm that probes whichever came first')
shutil.rmtree(tmp, ignore_errors=True)

# ── 3. NEGATIVE CONTROL: a good anchor is silent
tmp = fixture(HEAD + "MUTATIONS = [\n ('3. fine', 'return 1;', 'return 0;'),\n]\n")
rc, out = run_against(tmp)
check('3a  CONTROL: a unique anchor is not reported',
      'anchors NOT matching exactly once: 0' in out, '')
check('3b  CONTROL: and exits 0', rc == 0, 'exit %d' % rc)
check('3c  CONTROL: and it really did look -- 1 anchor checked',
      'anchors checked              : 1' in out, 'a tool that inspects 0 also exits 0')
shutil.rmtree(tmp, ignore_errors=True)

# ── 4. THE ONE THAT MATTERS: the tool must PARSE, never IMPORT
tmp = fixture(
    HEAD +
    "# A probe that does something at import time. A tool that imports this to\n"
    "# read MUTATIONS runs it -- which is exactly how a real probe left a mutated\n"
    "# source file on disk on 2026-09-11.\n"
    "open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),\n"
    "                  'IMPORTED'), 'w').write('the tool imported me')\n"
    "MUTATIONS = [\n ('4. fine', 'return 1;', 'return 0;'),\n]\n")
rc, out = run_against(tmp)
sentinel = os.path.join(tmp, 'IMPORTED')
check('4a  the fixture probe was NOT executed', not os.path.exists(sentinel),
      'no side effect from reading it')
check('4b  and its MUTATIONS were still read', 'anchors checked              : 1' in out,
      'parsed with ast, not imported')
shutil.rmtree(tmp, ignore_errors=True)

# ── 5. the import-guard half
UNGUARDED = (
    "import io, os\nREPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
    "TARGET = 'app.js'\n"
    "p = os.path.join(REPO, 'app.js')\n"
    "io.open(p, 'wb').write(b'mutated')\n"
    "MUTATIONS = [\n ('5. fine', 'return 1;', 'return 0;'),\n]\n")
tmp = fixture(UNGUARDED)
rc, out = run_against(tmp)
check('5a  a probe that mutates a REPO path with no guard is reported',
      'do NOT refuse an import: 1' in out, '')
check('5b  and it is named', 'fx_probe.py' in out.split('do NOT refuse an import')[-1], '')
shutil.rmtree(tmp, ignore_errors=True)

# ── 6. NEGATIVE CONTROL: the same write into a TEMP worktree is fine
# This is the version that made the first draft of the guard check cry wolf on
# six probes that were doing the right thing.
tmp = fixture(UNGUARDED.replace("p = os.path.join(REPO, 'app.js')",
                                "wt = os.environ.get('TMP', '.')\n"
                                "p = os.path.join(wt, 'app.js')"))
rc, out = run_against(tmp)
check('6a  CONTROL: a write into a temp worktree is NOT reported',
      'do NOT refuse an import: 0' in out,
      'os.path.join(wt, ...) is the safe pattern')
shutil.rmtree(tmp, ignore_errors=True)

# ── 7. the real repo
p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                   encoding='utf-8', errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('7a  the real repo has zero bad anchors and zero unguarded probes',
      p.returncode == 0, 'exit %d' % p.returncode)
check('7b  and it inspected a real number of them',
      'anchors checked              : 0' not in p.stdout and 'anchors checked' in p.stdout,
      [l.strip() for l in p.stdout.split('\n') if 'anchors checked' in l][:1])

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  %s' % f)
sys.exit(1 if failures else 0)
