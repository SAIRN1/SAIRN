"""tests/run_temporary_state_probe.py

Run:  python tests/run_temporary_state_probe.py

CONTROLS_FOR = tools/temporary_state_check.py

── WHAT THIS CONTROLS, AND WHAT IT CANNOT ────────────────────────────────────
The subject reports state that LOOKS temporary and DECLARES NOTHING. Its output
is a read-list, not a defect count, so "it printed 171 rows" is not evidence it
works. What CAN be locked is the criteria: which shapes it must report, which
declarations must silence it, which declarations must NOT, and the one false
positive that was already found and fixed.

Every arm below is a fixture with a KNOWN answer. Section E is the teeth: the
subject is copied out and deliberately broken, and if the positive arms still
pass with the detector neutered then this file was never testing anything. The
sabotage asserts its own anchor is present before it patches -- a `.replace()`
whose anchor has gone stale changes nothing and reports a pass.

Section F is the live instance. `sdSyncSuppressed=true` is in stonedesk.html
right now with no `finally`. It may be FIXED later, at which point this arm
stops testing anything -- so it reads the file and says out loud which branch it
took rather than quietly passing either way.

Section G proves a DOCUMENTED BLIND SPOT is real. The subject only matches
lowercase `= true;`, so a Python `flag = True` is invisible. That limitation is
written in the subject's docstring; this asserts the docstring is not lying in
the optimistic direction.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['temporary_state_check.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import temporary_state_check as T                              # noqa: E402

SUBJECT = os.path.join(REPO, 'tools', 'temporary_state_check.py')
FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


def shapes(rel, raw):
    rows, bad = T.findings_for(rel, raw)
    return set((r['shape'], r['line']) for r in rows), rows, bad


# ── fixtures ─────────────────────────────────────────────────────────────────
# The hydration leak, reduced. Set on the way in, cleared on the way out, and
# nothing guarantees the way out runs.
LEAK_JS = """var sdSyncSuppressed=false;
function hydrate(key, blob){
  sdSyncSuppressed=true;
  st(key, blob);
  sdSyncSuppressed=false;
}
"""

DECLARED_JS = """var sdSyncSuppressed=false;
function hydrate(key, blob){
  // TEMPORARY-STATE: scope=call released-by=finally below
  sdSyncSuppressed=true;
  try { st(key, blob); } finally { sdSyncSuppressed=false; }
}
"""

# The declaration is FOUR lines above the assignment. The window is three, so
# this must NOT silence it -- otherwise one declaration anywhere in a function
# covers everything under it.
FAR_DECL_JS = """var sdSyncSuppressed=false;
// TEMPORARY-STATE: scope=call released-by=finally below
function hydrate(key, blob){
  var x = 1;
  var y = 2;
  sdSyncSuppressed=true;
  st(key, blob);
  sdSyncSuppressed=false;
}
"""

BAD_SCOPE_JS = """var sdSyncSuppressed=false;
function hydrate(key, blob){
  // TEMPORARY-STATE: scope=forever released-by=nothing
  sdSyncSuppressed=true;
  st(key, blob);
  sdSyncSuppressed=false;
}
"""

# The 131-commit substrate: the identity written into the clone's config.
GIT_LEAK_PY = """import subprocess
def setup(wt):
    subprocess.run(['git', '-C', wt, 'config', 'user.email', 'probe@local'])
"""

GIT_OK_PY = """import subprocess
def setup(wt):
    subprocess.run(['git', '-C', wt, '-c', 'user.email=probe@local', 'commit'])
"""

# The false positive that shipped: `storeError('CONFIG', ...)` has nothing to do
# with git, and a case-insensitive /config/ matched it in api/_lib/sd-store.js.
NOT_GIT_JS = """function restUrl(path) {
  if (!process.env.SUPABASE_URL) {
    throw storeError('CONFIG', 'SUPABASE_URL not set');
  }
}
"""

PY_FLAG = """suppressed = False
def hydrate():
    global suppressed
    suppressed = True
    store()
    suppressed = False
"""

print('A. the two real leak shapes are reported when nothing is declared')
s, rows, bad = shapes('fx/leak.js', LEAK_JS)
ok('an undeclared flag set true is reported', ('flag-on', 3) in s, sorted(s))
ok('and only where it is set TRUE, not where it is cleared',
   len([r for r in rows if r['shape'] == 'flag-on']) == 1, rows)
s2, rows2, _ = shapes('fx/probe.py', GIT_LEAK_PY)
ok('a persistent git config write is reported',
   any(r['shape'] == 'git-config-write' for r in rows2), rows2)

print('\nB. a declaration on the line above silences it -- that is the point')
s, rows, bad = shapes('fx/declared.js', DECLARED_JS)
ok('scope=call on the preceding line covers the assignment',
   not any(r['shape'] == 'flag-on' for r in rows), rows)
ok('...and the fixture really does carry the declaration',
   'TEMPORARY-STATE: scope=call' in DECLARED_JS)
s, rows, _ = shapes('fx/ok.py', GIT_OK_PY)
ok('a per-invocation `-c` is not a persistent write',
   not any(r['shape'] == 'git-config-write' for r in rows), rows)

print('\nC. a declaration that is too far away, or names a scope that does '
      'not exist, is not a declaration')
s, rows, bad = shapes('fx/far.js', FAR_DECL_JS)
ok('four lines above does NOT cover -- the window is three',
   any(r['shape'] == 'flag-on' for r in rows), rows)
s, rows, bad = shapes('fx/badscope.js', BAD_SCOPE_JS)
ok('scope=forever is rejected as a scope', bad and bad[0][1] == 'forever', bad)
ok('...and the line it claimed to cover is still reported',
   any(r['shape'] == 'flag-on' for r in rows), rows)

print('\nD. the false positive that was already found stays fixed')
s, rows, _ = shapes('fx/store.js', NOT_GIT_JS)
ok("storeError('CONFIG', ...) is not a git config write",
   not any(r['shape'] == 'git-config-write' for r in rows), rows)
ok('...and the fixture really does contain the string that used to match',
   "'CONFIG'," in NOT_GIT_JS)

print('\nE. teeth -- neuter the detector and the positive arms must collapse')
TMP = tempfile.mkdtemp(prefix='tsc_probe_')
try:
    src = io.open(SUBJECT, encoding='utf-8').read()
    ANCHOR = r"FLAG_ON = re.compile(r'^\s*([A-Za-z_$][\w$.]*)\s*=\s*true\s*;', re.M)"
    ok('the sabotage anchor is still present in the subject', ANCHOR in src,
       'anchor has gone stale -- this section tests NOTHING until it is updated')
    broken = src.replace(ANCHOR, "FLAG_ON = re.compile(r'ZZ_NEVER_MATCHES_ZZ')")
    ok('the sabotage actually changed the file', broken != src)
    shutil.copy(os.path.join(REPO, 'tools', 'jscomments.py'), TMP)
    p = os.path.join(TMP, 'broken_check.py')
    io.open(p, 'w', encoding='utf-8').write(broken)
    drv = os.path.join(TMP, 'drive.py')
    io.open(drv, 'w', encoding='utf-8').write(
        'import sys, json\n'
        'sys.path.insert(0, %r)\n' % TMP +
        'import broken_check as B\n'
        'rows, bad = B.findings_for("fx/leak.js", open(sys.argv[1]).read())\n'
        'print(json.dumps(rows))\n')
    fx = os.path.join(TMP, 'leak.js')
    io.open(fx, 'w', encoding='utf-8').write(LEAK_JS)
    out = subprocess.run([sys.executable, drv, fx], capture_output=True,
                         text=True, cwd=TMP)
    ok('the broken copy runs at all', out.returncode == 0, out.stderr[-300:])
    ok('the neutered detector reports NOTHING for the leak fixture',
       out.stdout.strip() == '[]',
       'still reported %r -- section A was not testing the detector'
       % out.stdout.strip()[:200])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the throwaway copy is gone', not os.path.isdir(TMP))

print('\nF. the live instance in stonedesk.html -- says which branch it took')
sd = os.path.join(REPO, 'stonedesk.html')
if not os.path.isfile(sd):
    ok('stonedesk.html is readable', False, 'not found at ' + sd)
else:
    raw = io.open(sd, encoding='utf-8', errors='replace').read()
    live = bool(re.search(r'^\s*sdSyncSuppressed\s*=\s*true\s*;', raw, re.M))
    rows, _ = T.findings_for('stonedesk.html', raw)
    hits = [r for r in rows if r['what'] == 'sdSyncSuppressed']
    if live:
        print('    (the undeclared hydration flag is STILL IN THE FILE)')
        ok('the checker reports the real, still-present leak shape',
           len(hits) >= 1, 'found none -- the checker regressed')
    else:
        print('    (the flag is gone or now declared -- THIS ARM NO LONGER '
              'TESTS THE CHECKER)')
        ok('...and the checker agrees it is gone, rather than reporting a '
           'phantom', not hits, hits)

print('\nG. the documented blind spot is real, not a hedge')
s, rows, _ = shapes('fx/flags.py', PY_FLAG)
ok('a Python `= True` flag is invisible to the subject',
   not any(r['shape'] == 'flag-on' for r in rows), rows)
subject_doc = io.open(SUBJECT, encoding='utf-8').read()
ok('...and the subject says so in its own limits section',
   'lowercase' in subject_doc.lower() and 'True' in subject_doc,
   'the limit is real but undisclosed -- a silent blind spot')

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
