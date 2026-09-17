#!/usr/bin/env python
"""tests/run_cron_liveness_probe.py -- controls for the SECOND watchdog.

WHAT IS UNDER TEST, and it is two things that fail the same silent way:

  tools/cron_liveness_check.py          -- the out-of-band reader
  .github/workflows/cron-liveness.yml   -- the independent scheduler around it

THE FAILURE THIS FILE EXISTS AGAINST IS A MONITOR THAT GOES GREEN. Every other
kind of monitoring bug announces itself; this one looks exactly like a healthy
platform, and on 2026-09-15 the production watchdog spent four hours in that
state -- HTTP 200, `checked 4 job(s)`, and structurally unable to tell anybody
anything because SAIRN_OPS_EMAIL was unset.

THE WORKFLOW'S DECISION TABLE IS DRIVEN AS SHELL, not read. A verdict written
in YAML that nobody executes is a verdict nobody has ever seen run, and the
whole point of the hard step is that it fires. Section C extracts the real
script out of the real workflow file -- so an edit to the YAML changes what is
tested here -- and runs it under every combination of exit codes.

Exit 0 = every arm passed. Exit 1 = at least one failed. Exit 2 = could not run.
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

WORKFLOW = os.path.join(REPO, '.github', 'workflows', 'cron-liveness.yml')
FAILS = []
PASSES = [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('    ok   %s' % label)
    else:
        FAILS.append(label)
        print('    FAIL %s' % label)
        if detail:
            print('         %s' % str(detail)[:400])


# ══ A. the reader's verdict on a payload ═══════════════════════════════════
print('\nA. tools/cron_liveness_check.py -- what it calls OK')
import cron_liveness_check as C   # noqa: E402

FRESH = {'job': '/api/alf-alerts', 'status': 'ok', 'last_run_at': 'x',
         'age_seconds': 10, 'seconds_until_late': 3000}


def payload(jobs=None, channel=None, actions=None, **kw):
    p = {'ok': True, 'checked': 1,
         'jobs': jobs if jobs is not None else [dict(FRESH)],
         'actions': actions or []}
    if channel is not None:
        p['notify_channel'] = channel
    p.update(kw)
    return p


def run_against(p):
    """Drive main() with the network and the status document both faked.

    The document path is redirected so a probe run never rewrites the real
    docs/CRON-LIVENESS-STATUS.md -- a test that overwrites the live status file
    would make this repo assert a check that was a fixture.
    """
    tmp = tempfile.mkdtemp(prefix='cronlive_')
    real_doc, real_fetch = C.DOC, None
    C.DOC = os.path.join(tmp, 'STATUS.md')
    os.environ['CRON_SECRET'] = 'probe'
    try:
        import sairn_http
        real_fetch = sairn_http.fetch_json
        sairn_http.fetch_json = lambda *a, **k: p
        code = C.main([])
        doc = io.open(C.DOC, encoding='utf-8').read() if os.path.isfile(C.DOC) else ''
        return code, doc
    finally:
        if real_fetch is not None:
            import sairn_http
            sairn_http.fetch_json = real_fetch
        C.DOC = real_doc
        shutil.rmtree(tmp, ignore_errors=True)


code, doc = run_against(payload(channel={'configured': True, 'missing': [],
                                         'escalation_has_own_address': True}))
ok('a healthy platform with a working channel is OK (exit 0)', code == 0, code)
ok('...and the document says OK', 'OK' in doc, doc[:200])

code, doc = run_against(payload(channel={'configured': False,
                                         'missing': ['SAIRN_OPS_EMAIL'],
                                         'escalation_has_own_address': False}))
ok('EVERY JOB HEALTHY BUT NO CHANNEL IS NOT OK -- the 2026-09-15 production state',
   code == 1, code)
ok('...and the document NAMES the missing variable rather than saying "not ok"',
   'SAIRN_OPS_EMAIL' in doc, doc[-600:])
ok('...and says it is a configuration state that will not clear by itself',
   'CONFIGURATION state' in doc, doc[-600:])

# An older deployment simply does not have the field. Absent must not read as
# fine -- "the channel is healthy" and "this build cannot say" are different
# answers and only one of them is a pass.
code, doc = run_against(payload())
ok('a payload with NO notify_channel is COULD NOT TELL (exit 2), not OK', code == 2, code)
ok('...and the document does NOT say OK', 'COULD NOT TELL' in doc, doc[:300])

# The pre-existing guarantees must still hold -- this change must not have
# bought the channel check by loosening something else.
code, _ = run_against(payload(jobs=[dict(FRESH, status='DEAD')],
                              channel={'configured': True, 'missing': []}))
ok('CONTROL: a DEAD job is still a finding', code == 1, code)
code, _ = run_against(payload(jobs=[], channel={'configured': True, 'missing': []}))
ok('CONTROL: zero jobs checked is still COULD NOT TELL, not a clean sweep',
   code == 2, code)
code, _ = run_against({'error': {'code': 'NOT_PROVISIONED', 'message': 'no table'}})
ok('CONTROL: NOT_PROVISIONED is still COULD NOT TELL', code == 2, code)

# TEETH: if the channel check is removed, the arm that matters must collapse.
src = io.open(os.path.join(REPO, 'tools', 'cron_liveness_check.py'),
              encoding='utf-8').read()
ANCHOR = "    if not channel.get('configured'):"
ok('the teeth anchor is present in the subject', src.count(ANCHOR) == 1,
   'anchor stale or ambiguous -- the teeth arm below tests NOTHING')
broken = src.replace(ANCHOR, "    if False:")
ok('the neutering changed the source', broken != src)
TMP = tempfile.mkdtemp(prefix='cronlive_teeth_')
try:
    shutil.copy(os.path.join(REPO, 'tools', 'sairn_http.py'), TMP)
    bpath = os.path.join(TMP, 'broken_check.py')
    io.open(bpath, 'w', encoding='utf-8').write(broken)
    drv = os.path.join(TMP, 'drive.py')
    io.open(drv, 'w', encoding='utf-8').write(
        'import sys, json, os\n'
        'sys.path.insert(0, %r)\n' % TMP +
        'import sairn_http\n'
        'sairn_http.fetch_json = lambda *a, **k: json.loads(os.environ["PAYLOAD"])\n'
        'import broken_check as B\n'
        'B.DOC = os.path.join(%r, "S.md")\n' % TMP +
        'sys.exit(B.main([]))\n')
    env = dict(os.environ, CRON_SECRET='probe', PAYLOAD=json.dumps(
        payload(channel={'configured': False, 'missing': ['SAIRN_OPS_EMAIL']})))
    r = subprocess.run([sys.executable, drv], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=TMP, env=env)
    ok('the broken copy runs at all', r.returncode in (0, 1, 2), r.stderr[-300:])
    ok('TEETH: with the channel check neutered, the dead channel reports OK',
       r.returncode == 0,
       'the neutered copy still found it -- the arms above are not testing this '
       'check and the section proves nothing')
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the teeth scratch directory is gone', not os.path.isdir(TMP))


# ══ B. the workflow file, read as data ═════════════════════════════════════
print('\nB. .github/workflows/cron-liveness.yml -- structure')
try:
    import yaml
except ImportError:
    print('    (COULD NOT RUN: pyyaml is not installed -- reported, not skipped)')
    FAILS.append('pyyaml missing, section B did not run')
    yaml = None

wf = None
if yaml:
    wf = yaml.safe_load(io.open(WORKFLOW, encoding='utf-8'))
    trig = wf.get(True, wf.get('on'))          # PyYAML reads bare `on:` as True
    ok('it is on a SCHEDULE -- an independent scheduler is the whole point',
       'schedule' in trig, list(trig))
    ok('...and can be run by hand for a real verification', 'workflow_dispatch' in trig)
    crons = [c['cron'] for c in trig['schedule']]
    ok('it does NOT fire on the same minute as the Vercel watchdog (:15)',
       all(not c.startswith('15 ') for c in crons), crons)
    vercel = json.load(io.open(os.path.join(REPO, 'vercel.json'), encoding='utf-8'))
    mins = set()
    for c in vercel.get('crons', []):
        mins.add(c['schedule'].split()[0])
    ok('...nor on any minute a real Vercel cron fires on',
       all(c.split()[0] not in mins for c in crons), (crons, sorted(mins)))
    steps = wf['jobs']['liveness']['steps']
    names = [s.get('name') or s.get('uses') for s in steps]
    ok('there is a step that refuses to run without the secret',
       any('blind' in str(n).lower() for n in names), names)
    ok('there are TWO reads with a soft attempt between them',
       sum(1 for s in steps if 'cron_liveness_check.py' in str(s.get('run', ''))) == 2,
       names)
    verdict = [s for s in steps if s.get('name') == 'Verdict']
    ok('the verdict step exists and runs even when a read failed',
       len(verdict) == 1 and verdict[0].get('if') == 'always()', verdict)
    ok('the soft attempt is gated on exit code 1, not on generic failure',
       any("outputs.code == '1'" in str(s.get('if', '')) for s in steps),
       [s.get('if') for s in steps])


# ══ C. the verdict logic, EXECUTED ═════════════════════════════════════════
print('\nC. the verdict decision table -- driven as real shell')
if not shutil.which('sh'):
    print('    (COULD NOT RUN: no POSIX sh on PATH -- reported, not skipped)')
    FAILS.append('no sh available, section C did not run')
elif wf:
    script = [s for s in wf['jobs']['liveness']['steps']
              if s.get('name') == 'Verdict'][0]['run']
    ok('the verdict script was extracted from the real workflow file',
       'CRON LIVENESS FAILED' in script,
       'extraction anchor stale -- section C is testing a script that is not '
       'the one in the workflow')

    def verdict(c1, c2):
        env = dict(os.environ, C1=c1, C2=c2)
        r = subprocess.run(['sh', '-c', script], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', env=env)
        return r.returncode, r.stdout + r.stderr

    rc, out = verdict('0', '')
    ok('clean first read -> PASS, and no soft attempt was needed', rc == 0, out)

    rc, out = verdict('1', '0')
    ok('finding then clean -> PASS (the soft attempt worked)', rc == 0, out)
    ok('...but it is RECORDED as a warning, not silently green',
       '::warning' in out, out)

    rc, out = verdict('1', '1')
    ok('finding twice -> FAIL, which is the notification', rc == 1, out)
    ok('...and the error names all three causes that look alike',
       'notify_channel' in out and 'unreachable' in out, out[:300])

    rc, out = verdict('2', '')
    ok('COULD NOT TELL with no soft attempt -> FAIL, never a pass', rc == 1, out)

    rc, out = verdict('2', '2')
    ok('COULD NOT TELL twice -> FAIL', rc == 1, out)

    # THE ARM THAT MATTERS MOST. If the read step dies before writing its
    # output, C1 is empty. A naive `[ "$C1" != "0" ]` chain can fall through to
    # a pass, and the monitor goes green because it broke.
    rc, out = verdict('', '')
    ok('NO EXIT CODE RECORDED AT ALL -> FAIL, not pass', rc == 1, out)
    ok('...and it says nothing was checked, rather than reporting a finding',
       'NOTHING was checked' in out, out[:300])

    # And the other direction, so the arms above cannot be passing because the
    # script simply always fails.
    rc, _ = verdict('0', '2')
    ok('CONTROL: a clean first read wins even if a stale second code is present',
       rc == 0)


# ── AN ABSENT SECRET ARRIVES AS AN EMPTY STRING, NOT AS AN ABSENT NAME ─────
# Added 2026-09-17 after the workflow had failed SIX consecutive scheduled runs
# and not one request had reached the endpoint. `env: X: ${{ secrets.X }}` sets
# X to '' when the secret does not exist, and `os.environ.get(X, DEFAULT)`
# returns '' for that -- so the tool asked nothing, exited 2, and the failure
# read as the platform being unhealthy.
#
# BOTH DIRECTIONS AND THE OVERRIDE, because a helper that always returned the
# default would satisfy the first arm while silently ignoring a staging URL --
# which is the only reason the variable exists.
print(chr(10) + '5. an ABSENT secret arrives as EMPTY, and empty is not a URL')
import cron_liveness_check as CLC                                 # noqa: E402

_saved = os.environ.get('SAIRN_WATCHDOG_URL')
try:
    os.environ['SAIRN_WATCHDOG_URL'] = ''
    ok('an EMPTY SAIRN_WATCHDOG_URL falls back to the production endpoint',
       CLC.watchdog_url() == CLC.DEFAULT_URL, CLC.watchdog_url())

    os.environ['SAIRN_WATCHDOG_URL'] = '   '
    ok('whitespace is not a URL either',
       CLC.watchdog_url() == CLC.DEFAULT_URL, CLC.watchdog_url())

    os.environ['SAIRN_WATCHDOG_URL'] = 'https://staging.example/api/cron-watchdog'
    ok('CONTROL: a REAL override is still honoured -- the fallback is not '
       'swallowing the variable',
       CLC.watchdog_url() == 'https://staging.example/api/cron-watchdog',
       CLC.watchdog_url())

    del os.environ['SAIRN_WATCHDOG_URL']
    ok('an ABSENT name still falls back, which is what always worked',
       CLC.watchdog_url() == CLC.DEFAULT_URL, CLC.watchdog_url())
finally:
    if _saved is None:
        os.environ.pop('SAIRN_WATCHDOG_URL', None)
    else:
        os.environ['SAIRN_WATCHDOG_URL'] = _saved

# THE WORKFLOW AND THE TOOL MUST AGREE ABOUT THE SAME VARIABLE. The shell step
# already used `${VAR:-default}`, which treats empty as absent; the Python did
# not. Two languages, one variable, opposite defaults is what made this survive
# review -- so the agreement is asserted rather than left to a reader.
_wf = io.open(WORKFLOW, encoding='utf-8').read()
ok('the workflow shell still uses :- so it agrees with the tool on empty',
   '${SAIRN_WATCHDOG_URL:-' in _wf,
   'the shell default changed shape; re-check it against watchdog_url()')


print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
