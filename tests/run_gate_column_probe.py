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
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['gate_column_check.py']

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

# ── 8. THE TWO NUMBERS IN THE HEADER, both wrong until 2026-09-12 ───────────
# Neither of these changes a finding. Both change what a reader believes about
# the evidence under one, which is the same thing one level up.
import io as _io                                                    # noqa: E402
import json as _json                                                # noqa: E402
import datetime as _dt                                              # noqa: E402
sys.path.insert(0, os.path.join(REPO, 'tools'))
import gate_column_check as _g                                      # noqa: E402

_raw = _json.load(_io.open(os.path.join(REPO, 'db', 'schema_snapshot.json'),
                           encoding='utf-8'))
_meta = [k for k in _raw if k.startswith('_')]
check('8a  metadata keys are NOT counted as tables',
      len(_g.snapshot()) == len(_raw) - len(_meta),
      'dropped %d non-table keys: %s' % (len(_meta), ', '.join(sorted(_meta))))
check('8b  and the fixture has some, so 8a is not vacuous',
      len(_meta) > 0,
      'a snapshot with no metadata keys would make 8a pass while counting them')
check('8c  no metadata key survives into the table map',
      not any(k.startswith('_') for k in _g.snapshot()),
      'the header count and the lookup must agree on what a table is')

# The age must come from the CAPTURE's own stamp, not the commit date. It read
# the commit date and printed "25 hours ago" about a 43-hour-old capture --
# understating it by 18.7 hours, in the direction that makes stale data look
# current.
_age = _g.snapshot_age()
_stamp = str(_raw.get('_generated_at') or '')[:19]
_gen = _dt.datetime.strptime(_stamp, '%Y-%m-%d %H:%M:%S')
_hours = (_dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
          - _gen).total_seconds() / 3600.0
check('8d  the age is derived from _generated_at, not from the commit date',
      ('%.1f hours ago' % _hours) in _age,
      _age)
check('8e  the commit date is still shown -- a capture only one clone has is '
      'not yet a fact for anyone else',
      'committed' in _age,
      _age)
# THE CONTROL, and it must not go red for the wrong reason. 8d only proves
# anything while the capture stamp and the commit date actually differ. When a
# capture is committed promptly they converge, and then 8d would pass whichever
# field the tool read -- so the control SAYS SO rather than failing or, worse,
# passing quietly. The first draft hardcoded "~25 hours" and would have gone red
# the moment a fresh snapshot landed, which is a probe failing for a reason that
# has nothing to do with the thing it guards.
_cp = subprocess.run(['git', 'log', '-1', '--format=%cI', '--', 'db/schema_snapshot.json'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
_cs = (_cp.stdout or '').strip()
_chours = None
if len(_cs) >= 19:
    _cd = _dt.datetime.strptime(_cs[:19], '%Y-%m-%dT%H:%M:%S')
    _off = _cs[19:]
    if _off and _off[0] in '+-':
        _cd -= _dt.timedelta(hours=(-1 if _off[0] == '-' else 1) * int(_off[1:3]))
    _chours = (_dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
               - _cd).total_seconds() / 3600.0
if _chours is not None and abs(_hours - _chours) > 2:
    check('8f  CONTROL: the two fields really do differ, so 8d discriminates',
          ('%.1f hours ago' % _chours) not in _age,
          'capture %.1fh old vs commit %.1fh old -- the commit age must NOT appear'
          % (_hours, _chours))
else:
    check('8f  CONTROL INAPPLICABLE, declared rather than passed quietly',
          True,
          'capture and commit are within 2h (%.1f vs %s) -- 8d cannot discriminate '
          'right now and is not evidence until they diverge again'
          % (_hours, '%.1f' % _chours if _chours is not None else 'unknown'))

# ── 9. THE ACCEPTANCE MECHANISM, ADDED 2026-09-16 ──────────────────────────
#
# This tool asks "does the column exist" and cannot ask whether the read is a
# DEFECT or deliberate forward-compatibility -- both look like `row.X` against
# an absent column. An acceptance file answers that second question ONCE, with
# evidence, so the tool can stay readable.
#
# EVERY ARM HERE IS ABOUT THE DANGEROUS DIRECTION. An acceptance is a way to
# make a finding disappear, so the arms that matter are the ones proving it
# CANNOT disappear quietly: the count is printed, the entry is named, a
# reasonless entry is refused, a malformed file disables every acceptance
# loudly, and an acceptance that outlives its read is itself a finding.
def fixture_with_accept(js, accepted_json, schema=None):
    tmp = fixture(js, schema)
    os.makedirs(os.path.join(tmp, 'tools'), exist_ok=True)
    io.open(os.path.join(tmp, 'tools', 'gate_column_accepted.json'), 'w',
            encoding='utf-8', newline='\n').write(accepted_json)
    return tmp


ACC_OK = json.dumps([{'file': 'api/_lib/fx.js', 'property': 'trial_ends_at',
                      'reason': 'a real reason a reader can check'}])

tmp = fixture_with_accept(
    ONE_TABLE + "out.trial_ends_at = row.trial_ends_at || null;\n", ACC_OK)
rc, out = run(tmp)
check('9a  an ACCEPTED read is not a finding',
      'reads of a column that DOES NOT EXIST: 0' in out, out[:400])
check('9b  ...and the exit code is clean', rc == 0, 'exit %d' % rc)
check('9c  but it is COUNTED, never silently subtracted',
      '1 TRIAGED AND ACCEPTED' in out, out[:400])
check('9d  ...and NAMED, with its reason on screen',
      'row.trial_ends_at' in out and 'a real reason a reader can check' in out,
      out[:600])
shutil.rmtree(tmp, ignore_errors=True)

# THE CONTROL FOR 9a. Without this, every arm above is satisfied by a tool that
# reports nothing at all.
tmp = fixture_with_accept(
    ONE_TABLE + "out.some_other = row.some_other || null;\n", ACC_OK)
rc, out = run(tmp)
check('9e  CONTROL: an acceptance for a DIFFERENT property does not excuse '
      'this one', 'reads of a column that DOES NOT EXIST: 1' in out and rc == 1,
      out[:400])
shutil.rmtree(tmp, ignore_errors=True)

# A STALE ACCEPTANCE IS A FINDING IN ITS OWN RIGHT. The read it excused is gone,
# so the entry now excuses nothing and nothing else would ever say so.
tmp = fixture_with_accept(ONE_TABLE + "out.key = row.key;\n", ACC_OK)
rc, out = run(tmp)
check('9f  an acceptance matching NO read in the source is reported STALE',
      'STALE ACCEPTANCE' in out, out[:500])
check('9g  ...and a stale acceptance FAILS, rather than sitting in a file',
      rc == 1, 'exit %d' % rc)
shutil.rmtree(tmp, ignore_errors=True)

# AN ACCEPTANCE WITH NO REASON IS NOT ONE.
tmp = fixture_with_accept(
    ONE_TABLE + "out.trial_ends_at = row.trial_ends_at || null;\n",
    json.dumps([{'file': 'api/_lib/fx.js', 'property': 'trial_ends_at'}]))
rc, out = run(tmp)
check('9h  a reasonless acceptance is REFUSED and the read stays a finding',
      'reads of a column that DOES NOT EXIST: 1' in out and rc == 1, out[:400])
check('9i  ...and it says why rather than dropping the entry silently',
      'an acceptance nobody justified is not one' in out, out[:600])
shutil.rmtree(tmp, ignore_errors=True)

# A MALFORMED FILE DISABLES EVERY ACCEPTANCE, LOUDLY. The opposite -- a bad
# file quietly excusing everything, or quietly excusing nothing while claiming
# "accepted 0" -- is the swallow-and-carry-on this platform has already been
# bitten by in fail_open_check.load_accepted().
tmp = fixture_with_accept(
    ONE_TABLE + "out.trial_ends_at = row.trial_ends_at || null;\n",
    '{ this is not json')
rc, out = run(tmp)
check('9j  a malformed acceptance file leaves the read UNTRIAGED, not excused',
      'reads of a column that DOES NOT EXIST: 1' in out and rc == 1, out[:400])
check('9k  ...and says so out loud',
      'NO acceptances are in effect' in out, out[:600])
shutil.rmtree(tmp, ignore_errors=True)

# AND THE PATH IS LATE-BOUND. Every arm above depends on it: a module-level
# ACCEPTED_PATH computed from the real REPO would have made them all read the
# REAL acceptance file while believing they were reading a fixture.
tmp = fixture(ONE_TABLE + "out.trial_ends_at = row.trial_ends_at || null;\n")
rc, out = run(tmp)
check('9l  with NO acceptance file in the fixture the read is a finding -- so '
      'the arms above were reading the fixture, not the real repo file',
      'reads of a column that DOES NOT EXIST: 1' in out and rc == 1, out[:400])
shutil.rmtree(tmp, ignore_errors=True)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  %s' % f)
sys.exit(1 if failures else 0)
