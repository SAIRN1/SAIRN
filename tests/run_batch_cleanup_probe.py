"""Control for tools/batch_cleanup.py.

    python tests/run_batch_cleanup_probe.py

A deletion tool's only interesting failure is the one where it deletes
something. So every arm below is about something that must SURVIVE -- a
planted foreign file above all -- and the arms that assert a deletion exist to
stop the tool passing by never deleting anything at all.

DRIVEN AS A SUBPROCESS where the verdict is the exit code and the printed
reason, because that is what a session reads. Writes nothing outside a
temporary tree: SAIRN_SCRATCH_ROOT and the module's STATE_DIR are both
redirected, and an arm asserts the redirection took before anything is
deleted.
"""
CONTROLS_FOR = ['batch_cleanup.py']

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'batch_cleanup.py')
NL = chr(10)

if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- %s is absent.' % TOOL)
    sys.exit(2)

_spec = importlib.util.spec_from_file_location('bc_probe', TOOL)
BC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BC)

passed, fails = 0, []


def ok(cond, label, detail=''):
    global passed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        fails.append(label)
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:400])


print('1. the shipped criteria lock is clean and really ran')
r = subprocess.run([sys.executable, TOOL, '--fixtures'], capture_output=True,
                   text=True, encoding='utf-8', errors='replace')
ok(r.returncode == 0, 'the lock passes', (r.returncode, (r.stdout or '')[-300:]))
ok('16/16' in (r.stdout or ''), '...and all of its fixtures ran',
   (r.stdout or '')[-200:])
ok('PLANTED FOREIGN FILE' in (r.stdout or ''),
   '...including the planted foreign file, which is the arm this tool exists '
   'to pass')

print('')
print('2. A FOREIGN FILE SURVIVES, even when this agent recorded it itself')
tmp = tempfile.mkdtemp(prefix='bcp_')
_state = BC.STATE_DIR
_root = os.environ.get('SAIRN_SCRATCH_ROOT')
try:
    mine = os.path.join(tmp, 'claude', 'C--Users-marsh-Documents-SAIRN-cc')
    hank = os.path.join(tmp, 'claude', 'C--Users-marsh-Documents-SAIRN-hank')
    hover = os.path.join(tmp, 'claude', 'C--Users-marsh-Documents-SAIRN-hover')
    live = os.path.join(tmp, 'live-residue')
    for d in (mine, hank, hover, live):
        os.makedirs(d)
    os.environ['SAIRN_SCRATCH_ROOT'] = mine
    BC.STATE_DIR = os.path.join(tmp, 'state')
    ok(BC.scratch_root('cc') == os.path.abspath(mine),
       'the probe really redirected the scratch root', BC.scratch_root('cc'))
    ok(BC.STATE_DIR.startswith(tmp),
       'and the state directory, so the real lists are untouched')

    f_mine = os.path.join(mine, 'mine.log')
    f_hank = os.path.join(hank, 'hanks.log')
    f_hover = os.path.join(hover, 'hovers-audit-log.jsonl')
    f_live = os.path.join(live, '2026-10-13-probe.json')
    for f in (f_mine, f_hank, f_hover, f_live):
        io.open(f, 'w', encoding='utf-8').write('payload' + NL)

    # Every foreign path is put on CC'S OWN LIST. That is the whole test: the
    # list is not an authorisation.
    BC.record('cc', 'probe', [f_mine, f_hank, f_hover, f_live])
    rc, lines = BC.sweep('cc', 'probe', apply_changes=True)
    txt = NL.join(lines)

    ok(os.path.isfile(f_hank),
       "ANOTHER AGENT'S FILE SURVIVED a sweep that was told to take it",
       txt[-500:])
    ok(os.path.isfile(f_hover),
       "the AUDITOR's log survived -- the one file no build agent may touch")
    ok(os.path.isfile(f_live),
       'a live-residue evidence file survived')
    ok('OUTSIDE' in txt,
       '...and each is reported with the reason, not silently skipped')
    ok(rc == 1, 'the sweep exits 1 because something was LISTED rather than '
       'deleted -- a clean exit here would read as "nothing to do"', rc)

    print('')
    print('3. the push gate on deletion')
    _real = BC.push_landed
    try:
        BC.push_landed = lambda: (False, '3 commit(s) are NOT on origin/main yet')
        BC.record('cc', 'probe2', [f_mine])
        rc2, lines2 = BC.sweep('cc', 'probe2', apply_changes=True)
        ok(os.path.isfile(f_mine),
           'MY OWN file survives while the push has NOT landed -- the scratch '
           'is the only copy of the evidence for a report not yet written',
           NL.join(lines2)[-300:])
        ok('NOT LANDED' in NL.join(lines2),
           '...and the run says the push was the reason')

        BC.push_landed = lambda: (True, '')
        rc3, lines3 = BC.sweep('cc', 'probe2', apply_changes=True)
        ok(not os.path.isfile(f_mine),
           'and it IS deleted once the push has landed -- so the tool is not '
           'passing by never deleting anything', NL.join(lines3)[-300:])
        ok('REMOVED 1 file(s)' in NL.join(lines3),
           '...and the removal is logged in the run output')
        doc = json.loads(io.open(BC.list_path('cc', 'probe2'),
                                 encoding='utf-8').read())
        ok(doc.get('removed') == [os.path.abspath(f_mine)],
           '...and written into the list file, so the removal is auditable '
           'after the session ends', doc.get('removed'))
    finally:
        BC.push_landed = _real

    print('')
    print('4. the states that must refuse rather than guess')
    d = os.path.join(mine, 'adir')
    os.makedirs(d)
    ok(BC.classify({'path': d}, 'cc', set())[0] == 'LIST',
       'a DIRECTORY is listed, never removed')
    ok(BC.classify({'path': os.path.join(mine, 'nope.log')}, 'cc', set())[0]
       == 'GONE', 'an already-absent file is GONE, not an error')
    tracked = {BC._norm(os.path.join(mine, 'tracked.py'))}
    io.open(os.path.join(mine, 'tracked.py'), 'w', encoding='utf-8').write('x')
    ok(BC.classify({'path': os.path.join(mine, 'tracked.py')}, 'cc',
                   tracked)[0] == 'LIST',
       'a GIT-TRACKED path under my own root is listed, never removed')

    # An unreadable list is not an empty one.
    io.open(BC.list_path('cc', 'broken'), 'w', encoding='utf-8').write('{oops')
    rc4, lines4 = BC.sweep('cc', 'broken', apply_changes=True)
    ok(rc4 == 2 and 'could not be parsed' in NL.join(lines4),
       'an UNREADABLE list is COULD NOT RUN, not an empty sweep', rc4)

    rc5, lines5 = BC.sweep('', 'probe', apply_changes=True)
    ok(rc5 == 2, 'an undetectable agent is COULD NOT RUN -- "mine only" '
       'cannot be enforced without knowing who I am', rc5)

    print('')
    print('5. it cannot reach a database even by accident')
    # ASSERTED ON THE IMPORT GRAPH, NOT ON WORDS IN THE FILE. Two earlier
    # versions of this arm scanned for substrings and both failed on the
    # tool's OWN SENTENCE "opens no socket" -- first in a docstring, then in a
    # printed string, which stripping comments cannot reach. A scan that
    # cannot tell code from text describing code is PR 1.2, and it was this
    # probe committing it twice.
    #
    # The real property is what the module IMPORTS, which is a fact about the
    # parse tree rather than about prose.
    import ast as _ast
    _tree = _ast.parse(io.open(TOOL, encoding='utf-8').read())
    _imported = set()
    for _n in _ast.walk(_tree):
        if isinstance(_n, _ast.Import):
            for _a in _n.names:
                _imported.add(_a.name.split('.')[0])
        elif isinstance(_n, _ast.ImportFrom) and _n.module:
            _imported.add(_n.module.split('.')[0])
    ok(_imported <= {'io', 'json', 'os', 'subprocess', 'sys', 'time',
                     'checker_kit', 'sairn_session_identity', 'shutil',
                     'tempfile', 'ast'},
       'the module imports NOTHING that could reach a network or a database',
       sorted(_imported))
    for _bad in ('supabase', 'psycopg', 'psycopg2', 'requests', 'urllib',
                 'socket', 'http', 'httplib', 'ssl'):
        ok(_bad not in _imported,
           'it does not import %r' % _bad, sorted(_imported))
    # And no SQL text anywhere, which IS a substring question and is fair as
    # one: there is no legitimate reason for this file to contain a statement.
    _src = io.open(TOOL, encoding='utf-8').read()
    for _sql in ('DELETE FROM', 'UPDATE ', 'INSERT INTO', 'TRUNCATE'):
        ok(_sql not in _src, 'the file contains no %r' % _sql)
    ok('shutil.rmtree' not in _src.split('def run_fixtures')[0],
       'no recursive tree removal outside its own fixtures')
finally:
    BC.STATE_DIR = _state
    if _root is None:
        os.environ.pop('SAIRN_SCRATCH_ROOT', None)
    else:
        os.environ['SAIRN_SCRATCH_ROOT'] = _root
    shutil.rmtree(tmp, ignore_errors=True)

print('')
print('%d passed, %d failed' % (passed, len(fails)))
for f in fails:
    print('  FAILED: %s' % f)
sys.exit(1 if fails else 0)
