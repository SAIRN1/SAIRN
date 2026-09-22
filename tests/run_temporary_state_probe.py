r"""tests/run_temporary_state_probe.py

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

Section F runs against the REAL app files, both directions, and computes the
truth here rather than trusting a proxy. Its first version asked "is the
literal `sdSyncSuppressed=true` still in stonedesk.html, and if so does the
checker report it" -- and went RED the moment the leak was FIXED, because the
literal was still there, now behind a declaration, and the checker was right to
stay silent. An arm anchored on a proxy for the property fails on a correct
change. So the property is computed independently: a site is declared if the
token appears within the two lines above it, and the checker must report every
undeclared one and stay silent on every declared one. Two further arms assert
that BOTH directions were actually exercised on real files, because "all
undeclared sites were reported" is vacuously true when there are none.

That re-aiming immediately found a real defect in the subject: `^\s*` under
re.M starts a match at the first line of a whitespace run, and comments are
blanked to SPACES before matching, so a 20-line comment block above an
assignment made the reported line the top of the comment. sairnvet.html:2396
was being reported as :2376.

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

# The declaration token in every fixture below is ASSEMBLED AT RUNTIME. The
# subject walks the whole repo including tests/, which is correct -- the
# 131-commit leak lived in a probe -- so a literal declaration written here
# would be read as a real one in a real file: the valid ones would inflate the
# subject's declaration count with fixtures, and `scope=forever` would be
# reported as a genuinely malformed declaration. Assembling it keeps the
# fixtures honest for findings_for() without lying to the repo walk. An
# exclusion rule for tests/ was the alternative, and it would have blinded the
# tool to the exact directory the original leak came from.
TOKEN = 'TEMPORARY' + '-STATE:'

DECLARED_JS = """var sdSyncSuppressed=false;
function hydrate(key, blob){
  // %s scope=call released-by=finally below
  sdSyncSuppressed=true;
  try { st(key, blob); } finally { sdSyncSuppressed=false; }
}
""" % TOKEN

# The declaration is FOUR lines above the assignment. The window is three, so
# this must NOT silence it -- otherwise one declaration anywhere in a function
# covers everything under it.
FAR_DECL_JS = """var sdSyncSuppressed=false;
// %s scope=call released-by=finally below
function hydrate(key, blob){
  var x = 1;
  var y = 2;
  sdSyncSuppressed=true;
  st(key, blob);
  sdSyncSuppressed=false;
}
""" % TOKEN

BAD_SCOPE_JS = """var sdSyncSuppressed=false;
function hydrate(key, blob){
  // %s scope=forever released-by=nothing
  sdSyncSuppressed=true;
  st(key, blob);
  sdSyncSuppressed=false;
}
""" % TOKEN

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
   TOKEN + ' scope=call' in DECLARED_JS)
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
    # The two characters backslash-t, NOT a tab. A literal tab here would
    # silently fail to match and the sabotage would patch nothing -- which
    # is why the arm below asserts the anchor is PRESENT before using it.
    ANCHOR = r"FLAG_ON = re.compile(r'^[ \t]*([A-Za-z_$][\w$.]*)\s*=\s*true\s*;', re.M)"
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
                         text=True, encoding='utf-8', errors='replace', cwd=TMP)
    ok('the broken copy runs at all', out.returncode == 0, out.stderr[-300:])
    ok('the neutered detector reports NOTHING for the leak fixture',
       out.stdout.strip() == '[]',
       'still reported %r -- section A was not testing the detector'
       % out.stdout.strip()[:200])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the throwaway copy is gone', not os.path.isdir(TMP))

print('\nF. real app files, both directions, with the truth computed HERE')
# ── RE-AIMED 2026-09-14, AND THE REASON IS THE POINT ────────────────────────
# This section used to ask "is the literal `sdSyncSuppressed=true` still in
# stonedesk.html?" and, if so, demand the checker report it. Then the leak was
# FIXED -- the flag moved into sdWhileSuppressed() with a `finally` and a
# declaration above it -- and the arm went RED on a correct change, because the
# literal was still there and the checker was right not to report it.
#
# That is the failure this platform keeps paying for: an arm anchored on a
# PROXY for the property instead of the property. So the property is computed
# here, independently of the subject: a site is DECLARED if the declaration
# token appears within the two lines above it, and UNDECLARED otherwise. The
# checker must report every undeclared site and stay silent on every declared
# one -- a real two-direction test on real files that keeps working whichever
# way the apps go.
SITE = re.compile(r'^[ \t]*([A-Za-z_$][\w$.]*Suppress\w*)\s*=\s*true\s*;', re.M)
REAL = ['stonedesk.html', 'sairnfreedom.html', 'sairnvet.html']
seen_declared = seen_undeclared = 0
for rel in REAL:
    p = os.path.join(REPO, rel)
    if not os.path.isfile(p):
        ok(rel + ' is readable', False, 'not found at ' + p)
        continue
    raw = io.open(p, encoding='utf-8', errors='replace').read()
    lines = raw.split('\n')
    rows, _ = T.findings_for(rel, raw)
    reported = set(r['line'] for r in rows if 'Suppress' in r['what'])
    declared, undeclared = [], []
    for m in SITE.finditer(raw):
        n = raw[:m.start()].count('\n') + 1
        above = '\n'.join(lines[max(0, n - 3):n - 1])
        (declared if TOKEN in above else undeclared).append(n)
    print('    %-20s %d declared, %d undeclared'
          % (rel, len(declared), len(undeclared)))
    seen_declared += len(declared)
    seen_undeclared += len(undeclared)
    ok(rel + ': every UNDECLARED suppression site is reported',
       all(n in reported for n in undeclared),
       'missed %s' % [n for n in undeclared if n not in reported])
    ok(rel + ': every DECLARED site is silent',
       not [n for n in declared if n in reported],
       'reported anyway: %s' % [n for n in declared if n in reported])
# Both directions must actually be exercised. If the apps ever reach a state
# where every site is declared, the silent half is still tested but the
# reporting half is not -- and that is stated, not assumed.
ok('the reporting direction was exercised on real files at all',
   seen_undeclared > 0,
   'ZERO undeclared sites remain across %s -- the arms above only tested the '
   'SILENT direction. That is good news about the apps and a real loss of '
   'coverage here; sections A and C still cover reporting on fixtures.'
   % ', '.join(REAL))
ok('the silent direction was exercised on real files at all',
   seen_declared > 0, 'no declared site exists in any real app yet')

print('\nG. the documented blind spot is real, not a hedge')
s, rows, _ = shapes('fx/flags.py', PY_FLAG)
ok('a Python `= True` flag is invisible to the subject',
   not any(r['shape'] == 'flag-on' for r in rows), rows)
subject_doc = io.open(SUBJECT, encoding='utf-8').read()
ok('...and the subject says so in its own limits section',
   'lowercase' in subject_doc.lower() and 'True' in subject_doc,
   'the limit is real but undisclosed -- a silent blind spot')

print('\nH. --check has a verdict, and it is the one thing that needs no '
      'threshold')
H = tempfile.mkdtemp(prefix='tsc_check_')
_real_repo = T.REPO
try:
    ok('the real repo passes --check today', T.main(['--check']) == 0)
    T.REPO = H
    io.open(os.path.join(H, 'bad.js'), 'w', encoding='utf-8').write(BAD_SCOPE_JS)
    ok('a declaration naming a scope that does not exist FAILS --check',
       T.main(['--check']) == 1)
    io.open(os.path.join(H, 'bad.js'), 'w', encoding='utf-8').write(LEAK_JS)
    ok('...but 1 undeclared candidate and 0 declarations does NOT fail, '
       'because the count is not a score', T.main(['--check']) == 0)
    T.REPO = os.path.join(H, 'empty')
    os.mkdir(T.REPO)
    ok('ZERO TARGETS IS NOT A CLEAN SWEEP -- an empty tree exits 2',
       T.main([]) == 2)
finally:
    T.REPO = _real_repo
    shutil.rmtree(H, ignore_errors=True)
    ok('REPO was restored', T.REPO == _real_repo)

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
