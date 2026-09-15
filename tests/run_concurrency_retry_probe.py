"""tests/run_concurrency_retry_probe.py

Run:  python tests/run_concurrency_retry_probe.py

CONTROLS_FOR = tools/run_all_tests.py

── WHY A RETRY NEEDS A CONTROL MORE THAN MOST THINGS DO ──────────────────────
A retry is the most dangerous kind of leniency a test runner can grow. It turns
a red file green with no code change, and if it is quiet about doing so it is
indistinguishable from the runner simply not testing that file any more -- the
exact silent-exclusion shape `run_all_tests.py`'s own header was written
against.

So the arms here are not "does the retry work". They are:

  * a file NOT in the set gets NO second chance -- one failure is a failure;
  * a file IN the set that fails TWICE is a plain failure, and the message says
    it failed on its own;
  * a file in the set that passes on retry is reported BY NAME, loudly, and is
    NOT folded into the pass count;
  * the hook's silence-on-clean rule does NOT swallow a retry;
  * every name in CONCURRENCY_SENSITIVE is a real file, so a rename cannot
    leave a dead exemption behind that silently covers nothing.

The subject is driven with synthetic test files, so nothing here depends on the
three real probes staying flaky -- if they are fixed, these arms still hold.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['run_all_tests.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import run_all_tests as T                                        # noqa: E402

FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


print('A. every exemption names a file that exists')
for rel in sorted(T.CONCURRENCY_SENSITIVE):
    ok('%s is a real file' % rel,
       os.path.isfile(os.path.join(REPO, rel.replace('/', os.sep))),
       'a renamed or deleted file leaves a dead exemption that covers nothing '
       'and reads as coverage')
ok('the set is not empty -- an empty set would make every arm below vacuous',
   len(T.CONCURRENCY_SENSITIVE) > 0)

print('\nB. the retry is driven with synthetic files, not the real three')
TMP = tempfile.mkdtemp(prefix='retry_probe_')
_repo = T.REPO
_sens = T.CONCURRENCY_SENSITIVE
try:
    T.REPO = TMP
    # Fails the first time and passes the second, by leaving a marker behind.
    io.open(os.path.join(TMP, 'flaky.py'), 'w', encoding='utf-8').write(
        'import os, sys\n'
        'm = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ran.marker")\n'
        'if os.path.exists(m):\n'
        '    print("passed on the second attempt"); sys.exit(0)\n'
        'open(m, "w").write("1")\n'
        'print("first attempt fails"); sys.exit(1)\n')
    io.open(os.path.join(TMP, 'always.py'), 'w', encoding='utf-8').write(
        'import sys\nprint("always fails"); sys.exit(1)\n')

    T.CONCURRENCY_SENSITIVE = {'flaky.py'}
    failures, skipped, retried = T._run([], ['flaky.py'], quiet=True)
    ok('a listed file that passes on the second attempt is NOT a failure',
       not failures, failures)
    ok('...and it IS reported, by name, rather than silently absorbed',
       [r[1] for r in retried] == ['flaky.py'], retried)

    os.remove(os.path.join(TMP, 'ran.marker'))
    T.CONCURRENCY_SENSITIVE = set()
    failures, skipped, retried = T._run([], ['flaky.py'], quiet=True)
    ok('the SAME file, not listed, gets no second chance', len(failures) == 1,
       failures)
    ok('...and nothing is reported as retried', not retried, retried)

    T.CONCURRENCY_SENSITIVE = {'always.py'}
    failures, skipped, retried = T._run([], ['always.py'], quiet=True)
    ok('a listed file that fails TWICE is still a failure', len(failures) == 1,
       failures)
    ok('...and the message says the second attempt was on its own, so nobody '
       'reads it as load',
       failures and 'FAILED TWICE' in failures[0][2] and 'on its own' in failures[0][2],
       failures)
finally:
    T.REPO = _repo
    T.CONCURRENCY_SENSITIVE = _sens
    shutil.rmtree(TMP, ignore_errors=True)
ok('REPO and the exemption set were restored',
   T.REPO == _repo and T.CONCURRENCY_SENSITIVE is _sens)

print('\nC. a retry cannot hide behind the hook\'s silence-on-clean rule')
src = io.open(os.path.join(REPO, 'tools', 'run_all_tests.py'),
              encoding='utf-8').read()
ok('the hook early-return counts `retried` alongside failures and skips',
   'not failures and not skipped and not retried and not shrunk' in src,
   'the hook returns 0 before mentioning a retry -- a file needing a second '
   'attempt would be invisible on every push')
# Matched on a SINGLE-LINE fragment. The first version of these two arms
# searched for the whole sentence and failed, because both strings are wrapped
# across source lines -- an assertion about source text has to match the source,
# not the sentence a reader assembles.
ok('...and the hook message has a line for it',
   'CONCURRENCY_SENSITIVE file(s) failed once and passed ' in src)
ok('the human report says out loud that a retried file is not clean either',
   'and they are NOT clean either:' in src
   and 'RETRIED, PASSED ALONE' in src)

print('\nD. teeth -- remove the retry and the arms above must collapse')
TMP2 = tempfile.mkdtemp(prefix='retry_probe_')
try:
    ANCHOR = 'if r.returncode != 0 and rel in CONCURRENCY_SENSITIVE:'
    ok('the sabotage anchor is present in the subject', ANCHOR in src,
       'anchor gone stale -- this section tests NOTHING until it is updated')
    broken = src.replace(ANCHOR, 'if False:', 1)
    ok('the sabotage actually changed the file', broken != src)
    p = os.path.join(TMP2, 'broken_runner.py')
    io.open(p, 'w', encoding='utf-8').write(broken)
    io.open(os.path.join(TMP2, 'flaky.py'), 'w', encoding='utf-8').write(
        'import os, sys\n'
        'm = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ran.marker")\n'
        'if os.path.exists(m):\n'
        '    sys.exit(0)\n'
        'open(m, "w").write("1")\n'
        'sys.exit(1)\n')
    drv = os.path.join(TMP2, 'drive.py')
    io.open(drv, 'w', encoding='utf-8').write(
        'import sys, json\n'
        'sys.path.insert(0, %r)\n' % TMP2 +
        'import broken_runner as B\n'
        'B.REPO = %r\n' % TMP2 +
        "B.CONCURRENCY_SENSITIVE = {'flaky.py'}\n"
        "f, s, r = B._run([], ['flaky.py'], quiet=True)\n"
        'print(json.dumps({"failures": len(f), "retried": len(r)}))\n')
    out = subprocess.run([sys.executable, drv], capture_output=True, text=True, encoding='utf-8', errors='replace',
                         cwd=TMP2)
    ok('the broken copy runs at all', out.returncode == 0, out.stderr[-300:])
    ok('with the retry removed, the listed file is a FAILURE again',
       out.returncode == 0 and '"failures": 1' in out.stdout
       and '"retried": 0' in out.stdout,
       'section B was not testing the retry: ' + out.stdout.strip()[:200])
finally:
    shutil.rmtree(TMP2, ignore_errors=True)
    ok('the throwaway copy is gone', not os.path.isdir(TMP2))

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
