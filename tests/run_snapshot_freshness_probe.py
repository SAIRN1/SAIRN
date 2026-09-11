"""Probe tools/schema_snapshot_freshness.py, by attacking it.

The tool reports 210 absent tables against the real repo, 39 of them queried by
api/. A number that large is easy to produce by accident -- a broken regex that
matches nothing in the snapshot would report ALL of them -- so every arm below
builds a throwaway repo whose answer is known in advance.

ARM 3 IS THE CONTROL THAT MATTERS. A tool that reported every table as absent
would pass arms 1 and 2 and be worthless; a table that IS in the snapshot must
come back silent.

ARM 4 is the honesty arm. The two readings -- "the SQL was never run" and "the
snapshot is behind" -- are both real and were both measured live on 2026-09-11
(mech_checks provisioned:true, grd_rounds provisioned:false, same list). The
tool must present the question and must NOT pick one, so the arm asserts the
wording says so.

Run: python tests/run_snapshot_freshness_probe.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'schema_snapshot_freshness.py')

failures = []


def check(name, ok, detail=''):
    print('  %-4s %-60s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        failures.append(name)


def fixture(sql, snapshot, api=''):
    tmp = tempfile.mkdtemp(prefix='snapfresh_probe_')
    for d in ('sql', 'db', 'api'):
        os.makedirs(os.path.join(tmp, d))
    io.open(os.path.join(tmp, 'sql', 'fx.sql'), 'w', encoding='utf-8',
            newline='\n').write(sql)
    io.open(os.path.join(tmp, 'db', 'schema_snapshot.json'), 'w', encoding='utf-8',
            newline='\n').write(json.dumps(snapshot))
    io.open(os.path.join(tmp, 'api', 'fx.js'), 'w', encoding='utf-8',
            newline='\n').write(api)
    return tmp


def run(tmp):
    shim = os.path.join(tmp, '_runner.py')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        'import sys, os\n'
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import schema_snapshot_freshness as S\n'
        'S.REPO = %r\n' % tmp +
        "S.SNAPSHOT = os.path.join(%r, 'db', 'schema_snapshot.json')\n" % tmp +
        'sys.exit(S.main(["x"]))\n')
    p = subprocess.run([sys.executable, shim], capture_output=True, text=True,
                       encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print('SNAPSHOT FRESHNESS PROBE -- every fixture has a known answer\n')

# -- 1. a table sql/ creates and the snapshot does not know
tmp = fixture('create table if not exists public.widget_log (id uuid);\n',
              {'other': ['id']})
rc, out = run(tmp)
check('1a  an absent table is reported',
      'ABSENT from the snapshot: 1' in out, '')
check('1b  and it is named', 'widget_log' in out, '')
check('1c  exit code is non-zero', rc == 1, 'exit %d' % rc)
shutil.rmtree(tmp, ignore_errors=True)

# -- 2. the HIGH-SIGNAL split: absent AND queried by api/
tmp = fixture('create table if not exists public.widget_log (id uuid);\n',
              {'other': ['id']},
              api="const u = '/rest/v1/widget_log?select=*';\n")
rc, out = run(tmp)
check('2a  a table live code queries is counted separately',
      'also QUERIED by api/ : 1' in out, 'live code expects it -- the sharper set')
shutil.rmtree(tmp, ignore_errors=True)

tmp = fixture('create table if not exists public.widget_log (id uuid);\n',
              {'other': ['id']})
rc, out = run(tmp)
check('2b  CONTROL: and one nothing queries is NOT in that set',
      'also QUERIED by api/ : 0' in out, 'listed as undecidable instead')
check('2c  CONTROL: but it is still listed, not hidden',
      'undecidable here, listed not hidden' in out and 'widget_log' in out, '')
shutil.rmtree(tmp, ignore_errors=True)

# -- 3. CONTROL: a table the snapshot DOES know is silent
tmp = fixture('create table if not exists public.widget_log (id uuid);\n',
              {'widget_log': ['id']})
rc, out = run(tmp)
check('3a  CONTROL: a known table is not reported',
      'ABSENT from the snapshot: 0' in out, '')
check('3b  CONTROL: and it exits 0', rc == 0, 'exit %d' % rc)
check('3c  CONTROL: and it did read the sql -- 1 table created',
      'tables created in sql/: 1' in out, 'a tool finding 0 tables also reports 0 absent')
shutil.rmtree(tmp, ignore_errors=True)

# -- 4. HONESTY: it must not pick one of the two readings
tmp = fixture('create table if not exists public.widget_log (id uuid);\n',
              {'other': ['id']},
              api="const u = '/rest/v1/widget_log?select=*';\n")
rc, out = run(tmp)
check('4a  both readings are offered, neither chosen',
      'never been run' in out and 'snapshot is behind' in out
      and 'will not guess which' in out,
      'measured live the same day: one of each in the real list')
check('4b  and the re-capture step names the half that goes missing',
      'SAVE IT as db/schema_snapshot.json' in out and 'COMMIT it' in out, '')
shutil.rmtree(tmp, ignore_errors=True)

# -- 5. a table named only in a SQL COMMENT is not a created table
tmp = fixture('-- create table if not exists public.only_in_a_comment (id uuid);\n'
              'create table if not exists public.widget_log (id uuid);\n',
              {'widget_log': ['id']})
rc, out = run(tmp)
check('5a  a commented-out create is not counted',
      'tables created in sql/: 1' in out and 'only_in_a_comment' not in out,
      'the comment-quoting class, guarded here too')
shutil.rmtree(tmp, ignore_errors=True)

# -- 6. a missing snapshot is exit 2, not a pass
tmp = fixture('create table public.widget_log (id uuid);\n', {'widget_log': ['id']})
os.remove(os.path.join(tmp, 'db', 'schema_snapshot.json'))
rc, out = run(tmp)
check('6a  a missing snapshot exits 2, not 0', rc == 2, 'exit %d' % rc)
check('6b  and says nothing was checked', 'NOT a pass' in out, '')
shutil.rmtree(tmp, ignore_errors=True)

# -- 7. the real repo
p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                   encoding='utf-8', errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('7a  the real repo reports the stale snapshot', p.returncode == 1,
      'exit %d -- goes to 0 when the capture is re-run and committed' % p.returncode)
check('7b  and it read a real number of sql files',
      'tables created in sql/: 0' not in p.stdout,
      [l.strip() for l in p.stdout.split('\n') if 'created in sql/:' in l][:1])
check('7c  no raw control bytes in the tool itself',
      chr(8) not in io.open(TOOL, encoding='utf-8', errors='replace').read(),
      'a literal backspace disabled half of a sibling tool on 2026-09-11')

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  %s' % f)
sys.exit(1 if failures else 0)
