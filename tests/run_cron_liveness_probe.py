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


def run_against(p, status=200):
    """Drive main() with the network and the status document both faked.

    The document path is redirected so a probe run never rewrites the real
    docs/CRON-LIVENESS-STATUS.md -- a test that overwrites the live status file
    would make this repo assert a check that was a fixture.

    ── THE FAKE RETURNS WHAT THE REAL FUNCTION RETURNS (fixed 2026-09-17) ───
    THIS IS THE DEFECT THAT HID THE OTHER ONE, and it is the more important of
    the two. `sairn_http.fetch_json` returns `Response(status, body)`, a
    namedtuple. This fake returned the BODY -- a bare dict -- so every arm below
    proved the tool worked against a function that does not exist, while the
    real tool assigned the namedtuple to `payload`, failed its own
    `isinstance(payload, dict)` guard, and exited 2 COULD NOT TELL on every
    input it would ever see.

    A fake whose return SHAPE disagrees with the function it replaces does not
    weaken a test, it inverts it: the suite went green precisely because the
    tool was broken in a way the fake could not express. The `status` parameter
    exists so an HTTP error can be driven too -- fetch_json does NOT raise on
    one, it returns the parsed error body with its code, and nothing here had
    ever exercised that.
    """
    tmp = tempfile.mkdtemp(prefix='cronlive_')
    real_doc, real_fetch = C.DOC, None
    C.DOC = os.path.join(tmp, 'STATUS.md')
    os.environ['CRON_SECRET'] = 'probe'
    try:
        import sairn_http
        real_fetch = sairn_http.fetch_json
        sairn_http.fetch_json = lambda *a, **k: sairn_http.Response(status, p)
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
        # Response(status, body), NOT the bare body. The teeth driver carried
        # the identical fake-shape defect as run_against(): it returned the
        # body, so the arm it holds was proving the neutering worked against a
        # function that does not exist.
        'sairn_http.fetch_json = lambda *a, **k: sairn_http.Response(\n'
        '    200, json.loads(os.environ[\"PAYLOAD\"]))\n'
        'import broken_check as B\n'
        'B.DOC = os.path.join(%r, \"S.md\")\n' % TMP +
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
    # COUNTS INVOCATIONS, NOT MENTIONS (tightened 2026-09-17). This matched any
    # step whose `run` contained the tool's NAME, and the commit step added the
    # same day names the tool in its commit message -- so a correct change made
    # a structural arm go red for a reason that had nothing to do with the
    # structure. `python tools/...` is the thing being counted.
    ok('there are TWO reads with a soft attempt between them',
       sum(1 for s in steps
           if 'python tools/cron_liveness_check.py' in str(s.get('run', ''))) == 2,
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


# ── 6. THE TOOL CAN REACH A VERDICT AT ALL (2026-09-17) ────────────────────
# `sairn_http.fetch_json` returns `Response(status, body)`. The tool assigned
# that namedtuple straight to `payload` and then guarded with
# `isinstance(payload, dict)` -- ALWAYS true -- so EVERY run took the
# unreadable-answer branch and exited 2, including the two production runs
# where the watchdog answered 200 with all four jobs ok. The independent second
# opinion was structurally incapable of holding one.
#
# IT WAS THE FAKE THAT HID IT. run_against() returned the BODY, so the arms
# above proved the tool worked against a function that does not exist. Both
# fakes now return a real Response; these arms drive all three verdicts so a
# tool that has collapsed onto one can never satisfy them.
print(chr(10) + '6. the tool can actually reach a verdict, not only COULD NOT TELL')

_HEALTHY2 = payload(jobs=[{'job': '/api/a', 'status': 'ok'}],
                    channel={'configured': True, 'missing': []})
_DEAD2 = payload(jobs=[{'job': '/api/a', 'status': 'DEAD'}],
                 channel={'configured': True, 'missing': []})

_c0, _d0 = run_against(_HEALTHY2)
ok('a HEALTHY 200 exits 0 -- the verdict this tool could never once reach',
   _c0 == 0, 'exit %s' % _c0)
ok('...and the document says OK, not COULD NOT TELL',
   '| **State** | **OK** |' in _d0, _d0[:400])

_c1, _d1 = run_against(_DEAD2)
ok('a DEAD job is a FINDING (exit 1), which is not could-not-tell',
   _c1 == 1, 'exit %s' % _c1)

# fetch_json does NOT raise on an HTTP error -- it returns the parsed error
# body with its code -- so without reading `status` a 401 from a stale secret
# would be parsed as an answer. Nothing had ever driven that.
_c2, _d2 = run_against({'error': {'message': 'Unauthorized'}}, status=401)
ok('a 401 is COULD NOT TELL (exit 2), not an answer', _c2 == 2, 'exit %s' % _c2)
ok('...and it names the stale-secret cause instead of blaming the jobs',
   'CRON_SECRET' in _d2 and '401' in _d2, _d2[:400])

# TEETH. Three different inputs must give three different codes; if they ever
# collapse, the arms above are satisfied by a tool that distinguishes nothing --
# which is precisely the state that shipped.
ok('clean, finding and could-not-tell are three DIFFERENT exit codes',
   len({_c0, _c1, _c2}) == 3,
   'the tool has collapsed onto %s' % sorted({_c0, _c1, _c2}))



# == D. THE COMMIT-BACK STEP, EXECUTED AGAINST A REAL GIT REPO ==============
# Added 2026-09-17 with the step itself. The status document used to be
# uploaded as an artifact and never committed, so the copy a human reads
# asserted a verdict from three days earlier -- and THAT is why nobody looked
# at the run history while nine real runs failed.
#
# THE SCRIPT IS EXTRACTED AND RUN, not read. A commit step that has stopped
# committing looks exactly like one that had nothing to commit, so the only
# honest arm is one that checks whether a commit object actually appeared.
print(chr(10) + 'D. the commit-back step -- driven against a throwaway repo')
if not shutil.which('git') or not shutil.which('sh'):
    print('    (COULD NOT RUN: git or sh missing -- reported, not skipped)')
    FAILS.append('git/sh unavailable, section D did not run')
elif wf:
    _job = wf['jobs']['liveness']
    # JOB-SCOPED, NOT WORKFLOW-SCOPED, and both halves are asserted: a write at
    # the top would hand push rights to every job added to this file later.
    ok('the WORKFLOW default is still contents: read',
       (wf.get('permissions') or {}).get('contents') == 'read',
       wf.get('permissions'))
    ok('the JOB asks for contents: write, which is what lets it commit',
       (_job.get('permissions') or {}).get('contents') == 'write',
       _job.get('permissions'))

    _commit = [s for s in _job['steps']
               if s.get('name') == 'Commit the status document']
    ok('the commit step exists', len(_commit) == 1,
       [s.get('name') for s in _job['steps']])
    ok('...and runs even when the verdict failed -- COULD NOT TELL and NOT OK '
       'are exactly the states worth landing',
       len(_commit) == 1 and _commit[0].get('if') == 'always()', _commit)

    if _commit:
        _script = _commit[0]['run']
        ok('the commit script was extracted from the real workflow file',
           'CRON-LIVENESS-STATUS.md' in _script,
           'extraction anchor stale -- section D is driving a script that is '
           'not the one in the workflow')

        def _repo_pair():
            """A bare origin plus a clone, so `git push origin HEAD:main` is real."""
            d = tempfile.mkdtemp(prefix='cronlive_commit_')
            bare = os.path.join(d, 'origin.git')
            work = os.path.join(d, 'work')
            subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', bare],
                           check=True)
            subprocess.run(['git', 'clone', '-q', bare, work], check=True)
            for k, v in (('user.name', 'probe'),
                         ('user.email', 'probe@example.invalid')):
                subprocess.run(['git', '-C', work, 'config', k, v], check=True)
            os.makedirs(os.path.join(work, 'docs'), exist_ok=True)
            io.open(os.path.join(work, 'docs', 'CRON-LIVENESS-STATUS.md'), 'w',
                    encoding='utf-8', newline='').write('# base' + chr(10))
            subprocess.run(['git', '-C', work, 'add', '.'], check=True)
            subprocess.run(['git', '-C', work, 'commit', '-qm', 'base'], check=True)
            subprocess.run(['git', '-C', work, 'push', '-q', 'origin', 'main'],
                           check=True)
            return d, bare, work

        def _count(work):
            r = subprocess.run(['git', '-C', work, 'rev-list', '--count', 'HEAD'],
                               capture_output=True, text=True)
            return int((r.stdout or '0').strip() or 0)

        def _head(path):
            return subprocess.run(['git', '-C', path, 'rev-parse', 'HEAD'],
                                  capture_output=True, text=True).stdout.strip()

        def _drive(work, script):
            env = dict(os.environ, GITHUB_RUN_NUMBER='77',
                       GITHUB_WORKFLOW='cron-liveness')
            return subprocess.run(['sh', '-c', script], cwd=work, env=env,
                                  capture_output=True, text=True,
                                  encoding='utf-8', errors='replace')

        # 1. THE DOCUMENT CHANGED -> A COMMIT MUST APPEAR.
        _d, _bare, _work = _repo_pair()
        try:
            io.open(os.path.join(_work, 'docs', 'CRON-LIVENESS-STATUS.md'), 'w',
                    encoding='utf-8', newline='').write('# changed' + chr(10))
            _before = _count(_work)
            _r = _drive(_work, _script)
            _after = _count(_work)
            ok('a CHANGED status document lands a real commit',
               _after == _before + 1,
               'commits %d -> %d %s' % (_before, _after, _r.stdout + _r.stderr))
            _origin_head = subprocess.run(
                ['git', '-C', _bare, 'rev-parse', 'main'],
                capture_output=True, text=True).stdout.strip()
            ok('...and it reaches ORIGIN, not just the local branch',
               _origin_head == _head(_work), _r.stdout + _r.stderr)
            _author = subprocess.run(
                ['git', '-C', _work, 'log', '-1', '--format=%an <%ae>'],
                capture_output=True, text=True).stdout.strip()
            ok('...under the bot identity, not a person',
               'github-actions[bot]' in _author, _author)
        finally:
            shutil.rmtree(_d, ignore_errors=True)

        # 2. THE OTHER DIRECTION. Without it, arm 1 passes against a step that
        #    commits unconditionally -- an empty commit on main every run.
        _d, _bare, _work = _repo_pair()
        try:
            _before = _count(_work)
            _r = _drive(_work, _script)
            ok('an UNCHANGED document commits nothing',
               _count(_work) == _before, _r.stdout + _r.stderr)
            ok('...and says so rather than exiting silently',
               'Nothing to commit' in (_r.stdout + _r.stderr), _r.stdout)
        finally:
            shutil.rmtree(_d, ignore_errors=True)

        # 3. A MISSING DOCUMENT IS A WARNING, NOT A CRASH AND NOT A PASS.
        _d, _bare, _work = _repo_pair()
        try:
            os.remove(os.path.join(_work, 'docs', 'CRON-LIVENESS-STATUS.md'))
            _r = _drive(_work, _script)
            ok('a MISSING document warns rather than failing the job',
               _r.returncode == 0
               and 'no status document' in (_r.stdout + _r.stderr),
               'rc=%s %s' % (_r.returncode, _r.stdout + _r.stderr))
        finally:
            shutil.rmtree(_d, ignore_errors=True)

    # 4. THE RETROACTIVE ARM: the version BEFORE this step must not commit. A
    #    step added today is trivially present; what needs proving is that its
    #    absence was the defect.
    _prev = subprocess.run(
        ['git', '-C', REPO, 'log', '--format=%H', '-2', '--',
         '.github/workflows/cron-liveness.yml'],
        capture_output=True, text=True).stdout.split()
    if _prev:
        _old = subprocess.run(
            ['git', '-C', REPO, 'show',
             '%s:.github/workflows/cron-liveness.yml' % _prev[-1]],
            capture_output=True, text=True, encoding='utf-8',
            errors='replace').stdout
        ok('the pre-change workflow had NO commit step -- only the artifact '
           'upload, which is the gap this closes',
           'Commit the status document' not in _old and 'upload-artifact' in _old,
           'the historical anchor moved; this arm proves nothing as written')


print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
