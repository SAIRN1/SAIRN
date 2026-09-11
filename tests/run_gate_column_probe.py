"""Probe tools/gate_column_check.py, by attacking it.

The tool currently reports exactly ONE finding against the real repo -- the
known, filed `trial_ends_at` one. A tool that reports one thing and would report
the same one thing no matter what the code said is not a check, so every arm
below builds a throwaway api/ tree whose answer is known in advance.

ARM 4 IS THE CONTROL THAT MATTERS. A tool that flagged every property read would
pass arm 1 and be worthless; a file whose reads are all real columns must come
back silent.

ARM 5 is the honesty arm: a file that queries several tables cannot have its
reads attributed without real dataflow, and it must be COUNTED AND NAMED rather
than quietly dropped -- an unattributed file silently treated as clean is the
failure this whole tool exists to catch, one level up.

Run: python tests/run_gate_column_probe.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'gate_column_check.py')

failures = []


def check(name, ok, detail=''):
    print('  %-4s %-60s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        failures.append(name)


SCHEMA = {'license_keys': ['id', 'key', 'status', 'plan'],
          'other_table': ['id', 'name']}


def fixture(js, schema=None):
    tmp = tempfile.mkdtemp(prefix='gatecol_probe_')
    os.makedirs(os.path.join(tmp, 'api', '_lib'))
    os.makedirs(os.path.join(tmp, 'db'))
    io.open(os.path.join(tmp, 'db', 'schema_snapshot.json'), 'w',
            encoding='utf-8', newline='\n').write(json.dumps(schema or SCHEMA))
    io.open(os.path.join(tmp, 'api', '_lib', 'fx.js'), 'w',
            encoding='utf-8', newline='\n').write(js)
    return tmp


def run(tmp):
    shim = os.path.join(tmp, '_runner.py')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        'import sys, os\n'
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import gate_column_check as G\n'
        'G.REPO = %r\n' % tmp +
        "G.SNAPSHOT = os.path.join(%r, 'db', 'schema_snapshot.json')\n" % tmp +
        'sys.exit(G.main(["x"]))\n')
    p = subprocess.run([sys.executable, shim], capture_output=True, text=True,
                       encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


ONE_TABLE = ("const url = SUPABASE_URL + '/rest/v1/license_keys?key=eq.' + k;\n"
             "const rows = await res.json();\n"
             "const row = rows[0];\n")

print('GATE COLUMN PROBE -- every fixture has a known answer\n')

# ── 1. the real shape: a read of a column that is not on the table
tmp = fixture(ONE_TABLE + "out.trial_ends_at = row.trial_ends_at || null;\n")
rc, out = run(tmp)
check('1a  a read of a nonexistent column is reported',
      'reads of a column that DOES NOT EXIST: 1' in out, '')
check('1b  it names the property', 'row.trial_ends_at' in out, '')
check('1c  and lists what the table actually has', 'license_keys has:' in out, '')
check('1d  exit code is non-zero', rc == 1, 'exit %d' % rc)
shutil.rmtree(tmp, ignore_errors=True)

# ── 2. it moves with the SCHEMA, not with a hardcoded name
tmp = fixture(ONE_TABLE + "out.trial_ends_at = row.trial_ends_at || null;\n",
              schema={'license_keys': ['id', 'key', 'status', 'plan', 'trial_ends_at']})
rc, out = run(tmp)
check('2a  the SAME read is silent once the column exists',
      'reads of a column that DOES NOT EXIST: 0' in out,
      'the answer follows the snapshot, not a name list')
check('2b  and exits 0', rc == 0, 'exit %d' % rc)
shutil.rmtree(tmp, ignore_errors=True)

# ── 3. a table name in a COMMENT is not a query
# This repo names tables and columns in prose constantly; matching those would
# attribute a file to a table it never queries.
tmp = fixture("// we used to read /rest/v1/other_table here\n" + ONE_TABLE +
              "out.plan = row.plan;\n")
rc, out = run(tmp)
check('3a  a commented-out table does not break attribution',
      'files attributed  : 1' in out, 'still attributed to license_keys alone')
check('3b  and the real reads are clean',
      'reads of a column that DOES NOT EXIST: 0' in out, '')
shutil.rmtree(tmp, ignore_errors=True)

# ── 4. CONTROL: reads that ARE columns stay silent
tmp = fixture(ONE_TABLE + "out.plan = row.plan; out.status = row.status; out.key = row.key;\n")
rc, out = run(tmp)
check('4a  CONTROL: real columns are not reported',
      'reads of a column that DOES NOT EXIST: 0' in out, '')
check('4b  CONTROL: and the file WAS attributed -- it did look',
      'files attributed  : 1' in out, 'a tool attributing 0 files also reports 0 findings')
shutil.rmtree(tmp, ignore_errors=True)

# ── 5. HONESTY: a multi-table file is named, not silently dropped
tmp = fixture("const a = '/rest/v1/license_keys?x';\nconst b = '/rest/v1/other_table?y';\n"
              "const rows = await res.json();\nconst row = rows[0];\n"
              "out.nope = row.definitely_not_a_column;\n")
rc, out = run(tmp)
check('5a  a multi-table file is counted as NOT checked',
      'NOT checked       : 1' in out, '')
check('5b  it is named, not just counted', 'api/_lib/fx.js' in out, '')
check('5c  and it is NOT reported as a finding',
      'reads of a column that DOES NOT EXIST: 0' in out,
      'refusing to attribute is not the same as clearing')
shutil.rmtree(tmp, ignore_errors=True)

# ── 6. a missing snapshot is exit 2, not a pass
tmp = fixture(ONE_TABLE)
os.remove(os.path.join(tmp, 'db', 'schema_snapshot.json'))
rc, out = run(tmp)
check('6a  a missing snapshot exits 2, not 0', rc == 2, 'exit %d' % rc)
check('6b  and says nothing was checked', 'NOT a pass' in out, '')
shutil.rmtree(tmp, ignore_errors=True)

# ── 6b. TWO DEFECTS THIS TOOL SHIPPED WITH, both found by other checkers on
# 2026-09-11 and both permanent arms now.
#
# (i) a literal 0x08 BACKSPACE where a word boundary was meant. The alternation
#     read `<BS>rest(` instead of `\brest(`, so the second URL form NEVER
#     matched and the widening that was committed as working did nothing --
#     attribution stayed at 3 files and the commit message said it covered both
#     forms. Found by tools/control_char_check.py, not by reading it.
# (ii) `rest('rpc/name')` captured as a table. PostgREST's rpc path is a
#     function call, and treating it as a table made ai-rate-limit.js report
#     "queries a table absent from the snapshot" -- a finding about nothing.
src_tool = io.open(TOOL, encoding='utf-8', errors='replace').read()
check('6c  no raw control bytes in the tool itself',
      chr(8) not in src_tool and chr(0) not in src_tool,
      'a literal backspace silently disabled an alternation here once')
check('6d  the second URL form really is live',
      'rest(?:Url)?' in src_tool and chr(92) + 'b' in src_tool,
      'the word boundary is an escape, not a control character')
tmp = fixture("const rows = await res.json();\n" "const row = rows[0];\n" "const u = rest('rpc/do_a_thing');\n" "out.plan = row.plan;\n")
rc, out = run(tmp)
check('6e  a PostgREST rpc/ call is not treated as a table',
      'absent from the snapshot' not in out,
      'rpc is a function path, not a table')
shutil.rmtree(tmp, ignore_errors=True)

# ── 7. the real repo
p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                   encoding='utf-8', errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('7a  the real repo still reports the known trial_ends_at read',
      'trial_ends_at' in p.stdout,
      'if this ever goes quiet, either the column landed or the gate was removed -- check which')
check('7b  and it attributed files rather than reporting on nothing',
      'files attributed  : 0' not in p.stdout,
      [l.strip() for l in p.stdout.split('\n') if 'files attributed' in l][:1])

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  %s' % f)
sys.exit(1 if failures else 0)
