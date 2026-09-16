"""The landing check must fail on the things it exists to catch.

    python tests/run_landing_verification_probe.py

A tool that has only ever printed CLEAN is not evidence. Every arm here drives
the real functions in `tools/landing_verification.py` against fixtures built in
a temp directory, and the arms that matter are the ones asserting a NON-clean
answer -- an arm written as "expect no findings" keeps passing against a
checker that has stopped working, which is the asymmetry
`sabotage_control_check.py` exists to measure.

THE THREE ARMS THAT CARRY THE TOOL, each pinned to a real incident:

  arm 3  A CRLF-vs-LF pair must compare EQUAL. The user skill store is CRLF and
         the repo is LF; a bare byte diff reports every content-identical file
         as changed and produced three false alarms in one session on
         2026-09-03. If this arm goes red the mirror check reports the whole
         platform diverged.

  arm 6  An ABSENT EXECUTABLE must produce COULD NOT TELL, never CURRENT. This
         is the fail-closed rule (PR 1.11) and it is not hypothetical here: the
         first version of npm_row() crashed on Windows because `npm` is
         `npm.cmd`, which is the good failure -- the bad one is the same
         function returning "nothing outdated" because it could not ask.

  arm 8  A Vercel bot-mitigation CHALLENGE must produce UNVERIFIED and must
         never be counted as MATCHES. A 403 means the check did not run
         (PR 3.2); folding it into the pass column is how a deploy watcher goes
         silently blind.
"""
# REQUIREMENT: landing_verification.py compares a CRLF and an LF copy as EQUAL,
#   and answers COULD NOT TELL rather than CURRENT when an executable it
#   depends on is absent -- the fail-closed rule, and a bare byte diff once
#   reported the whole skill mirror as diverged
#
CONTROLS_FOR = ['landing_verification.py']

import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'landing_verification.py')

spec = importlib.util.spec_from_file_location('lv', TOOL)
lv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lv)

fails = 0


def check(label, actual, expected):
    global fails
    if actual == expected:
        print('  ok    %s' % label)
        return True
    fails += 1
    print('FAIL  %s\n        expected %r\n        actual   %r'
          % (label, expected, actual))
    return False


tmp = tempfile.mkdtemp(prefix='landingverify-')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, 'w', encoding='utf-8', newline='').write(text)


# ── 1. the clone list is DISCOVERED, and a non-repo directory is not a clone ──
parent = os.path.join(tmp, 'clonedir')
for name, is_repo in (('SAIRN-a', True), ('SAIRN-b', True),
                      ('SAIRN-notarepo', False), ('Unrelated', True)):
    os.makedirs(os.path.join(parent, name), exist_ok=True)
    if is_repo:
        os.makedirs(os.path.join(parent, name, '.git'), exist_ok=True)
_saved = lv.CLONE_PARENT
lv.CLONE_PARENT = parent
found = [os.path.basename(p) for p in lv.clones()]
lv.CLONE_PARENT = _saved
check('1 every SAIRN-* directory that is a repo is discovered',
      found, ['SAIRN-a', 'SAIRN-b'])
check('1 a directory without .git is NOT counted as a clone',
      'SAIRN-notarepo' in found, False)

# ── 2. the URL map REFUSES rather than returning an empty clean answer ────────
_saved_repo = lv.REPO
d = os.path.join(tmp, 'norouting')
os.makedirs(d)
lv.REPO = d
r, err = lv.routes()
check('2 a missing vercel.json is an error, not zero routes', (r, bool(err)),
      (None, True))
write(os.path.join(d, 'vercel.json'), '{"routes": []}')
r, err = lv.routes()
check('2 a vercel.json yielding ZERO routes REFUSES rather than passing',
      (r, 'zero routes' in (err or '').lower()), (None, True))
write(os.path.join(d, 'vercel.json'),
      '{"routes": [{"src": "/alpha$", "dest": "/alpha.html"},'
      ' {"src": "/(.*)", "dest": "/$1"}]}')
r, err = lv.routes()
check('2 a real route is read and a catch-all is not mistaken for an app',
      (r, err), ([('alpha', 'alpha.html')], None))
lv.REPO = _saved_repo

# ── 3. CRLF IS NOT DRIFT, and this arm is why the mirror check is usable ─────
check('3 a CRLF file and its LF twin compare EQUAL',
      lv.sha(b'line one\r\nline two\r\n'), lv.sha(b'line one\nline two\n'))
check('3 but a REAL content difference still differs',
      lv.sha(b'line one\n') == lv.sha(b'line ONE\n'), False)

# ── 4. the mirror: a diverged file is a FINDING, a store-only skill is not ───
def mirror_case(name, build):
    d = os.path.join(tmp, name)
    repo_s = os.path.join(d, 'repo', '.claude', 'skills')
    store = os.path.join(d, 'store')
    build(repo_s, store)
    _r, _u = lv.REPO, lv.USER_SKILL_STORE
    lv.REPO, lv.USER_SKILL_STORE = os.path.join(d, 'repo'), store
    try:
        return lv.mirror_row()
    finally:
        lv.REPO, lv.USER_SKILL_STORE = _r, _u


def same(repo_s, store):
    write(os.path.join(repo_s, 'sairn-x', 'SKILL.md'), 'hello\nworld\n')
    write(os.path.join(store, 'sairn-x', 'SKILL.md'), 'hello\r\nworld\r\n')
    write(os.path.join(store, 'third-party', 'SKILL.md'), 'not mirrored\n')


row = mirror_case('mirror-same', same)
check('4 a CRLF store copy of an identical skill is NOT a finding',
      row['verdict'], 'MATCHES')
check('4 and a store-only third-party skill is counted and named, not a '
      'finding', '1 in the store only' in row['detail'], True)


def diverged(repo_s, store):
    write(os.path.join(repo_s, 'sairn-x', 'SKILL.md'), 'hello\nworld\n')
    write(os.path.join(store, 'sairn-x', 'SKILL.md'), 'hello\nWORLD\n')


row = mirror_case('mirror-diverged', diverged)
check('4 a genuinely diverged mirrored skill IS a finding',
      (row['verdict'], any('sairn-x' in f for f in row.get('files', []))),
      ('FINDING', True))


def absent(repo_s, store):
    write(os.path.join(repo_s, 'sairn-x', 'SKILL.md'), 'hello\n')
    os.makedirs(store, exist_ok=True)


row = mirror_case('mirror-absent', absent)
check('4 a mirrored skill MISSING from the store is a finding, not silence',
      (row['verdict'], any('MISSING FROM STORE' in f
                           for f in row.get('files', []))), ('FINDING', True))

# ── 5. a missing reference is COULD NOT TELL, never a clean mirror ───────────
_u = lv.USER_SKILL_STORE
lv.USER_SKILL_STORE = os.path.join(tmp, 'does-not-exist')
row = lv.mirror_row()
lv.USER_SKILL_STORE = _u
check('5 an ABSENT user store means the check DID NOT RUN, not that it passed',
      (row['verdict'], 'did NOT run' in row['detail']),
      ('COULD NOT TELL', True))

# ── 6. FAIL CLOSED ON AN ABSENT TOOL. The whole point of PR 1.11. ────────────
rc, out, err = lv.run(['a-command-that-does-not-exist-anywhere'])
check('6 an executable that is not on PATH returns MISSING, not an exception',
      (rc, 'not on PATH' in err), (lv.MISSING, True))

_real_run = lv.run
lv.run = lambda args, cwd=None: (lv.MISSING, '', '%s is not on PATH' % args[0])
try:
    nrow = lv.npm_row()
    prow = lv.pip_row()
finally:
    lv.run = _real_run
check('6 npm absent reports COULD NOT TELL, NEVER "nothing outdated"',
      (nrow['verdict'], 'DID NOT RUN' in nrow['detail']),
      ('COULD NOT TELL', True))
check('6 pip absent reports COULD NOT TELL too',
      prow['verdict'], 'COULD NOT TELL')

# ── 7. the verdict: a FINDING outranks an UNKNOWN, an UNKNOWN never reads clean
def v(rows):
    return lv.verdict({'sections': {'skills': {'rows': rows}}})


check('7 all MATCHES is clean', v([{'verdict': 'MATCHES'}]), 0)
check('7 one FINDING among matches is exit 1',
      v([{'verdict': 'MATCHES'}, {'verdict': 'FINDING'}]), 1)
check('7 one COULD NOT TELL among matches is exit 2, NOT 0',
      v([{'verdict': 'MATCHES'}, {'verdict': 'COULD NOT TELL'}]), 2)
check('7 a FINDING outranks a COULD NOT TELL',
      v([{'verdict': 'COULD NOT TELL'}, {'verdict': 'FINDING'}]), 1)
check('7 an UNVERIFIED live route is exit 2, never clean',
      lv.verdict({'sections': {'landing': {'live': [{'verdict': 'MATCHES'},
                                                    {'verdict': 'UNVERIFIED'}]}}}),
      2)
check('7 a DRIFTing live route is a FINDING',
      lv.verdict({'sections': {'landing': {'live': [{'verdict': 'DRIFT'}]}}}), 1)

# ── 8. A CHALLENGE IS UNVERIFIED AND IS NEVER COUNTED AS A MATCH ─────────────
# Driven through the real live_checks() with a stand-in transport, because the
# thing being proved is the BRANCH, and against the real host every route
# answered 200 -- so the challenge path has never executed on a real run and
# would be untested exactly when it matters.
class FakeHTTP(object):
    class Challenged(Exception):
        def __init__(self, status):
            self.status = status
            super().__init__('challenge')

    def __init__(self, mode):
        self.mode = mode

    def fetch(self, url, timeout=None, no_cache=False):
        if self.mode == 'challenge':
            raise self.Challenged(403)
        if self.mode == 'match':
            return 200, self.body
        return 200, b'something else entirely'


def drive(mode, body=b''):
    d = os.path.join(tmp, 'live-' + mode)
    os.makedirs(d, exist_ok=True)
    fake = FakeHTTP(mode)
    fake.body = body
    sys.modules['sairn_http'] = fake
    _run = lv.run
    lv.run = lambda args, cwd=None: (
        (0, 'alpha content\n', '') if args[:2] == ['git', 'show']
        else _run(args, cwd or lv.REPO))
    try:
        return lv.live_checks([('alpha', 'alpha.html')], 'deadbeef', False)
    finally:
        lv.run = _run
        sys.modules.pop('sairn_http', None)


rows = drive('challenge')
check('8 a Vercel challenge is UNVERIFIED, not MATCHES and not a FINDING',
      rows[0]['verdict'], 'UNVERIFIED')
check('8 and it says the check did not run rather than implying a bad deploy',
      'NOT verified-good' in rows[0]['detail'], True)
check('8 a live body equal to origin/main is MATCHES',
      drive('match', b'alpha content\n')[0]['verdict'], 'MATCHES')
check('8 a live body that differs is DRIFT',
      drive('drift')[0]['verdict'], 'DRIFT')
check('8 and DRIFT does not claim to know WHY',
      'never deployed' in drive('drift')[0]['detail'], True)

# ── 9. --offline reports NOT RUN, which is exit 2 and is not a pass ──────────
rows = lv.live_checks([('alpha', 'alpha.html')], 'deadbeef', True)
check('9 --offline reports NOT RUN rather than a silent clean',
      rows[0]['verdict'], 'NOT RUN')
check('9 and NOT RUN is exit 2',
      lv.verdict({'sections': {'landing': {'live': rows}}}), 2)

# ── 10. and the real tool runs end to end without the network ────────────────
r = subprocess.run([sys.executable, TOOL, '--offline', '--skills'], cwd=REPO,
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
check('10 the real tool runs offline and does not crash', r.returncode in (0, 1, 2),
      True)
check('10 and it names the baseline it measured against',
      'baseline origin/main' in r.stdout, True)

shutil.rmtree(tmp, ignore_errors=True)
print()
if fails:
    print('%d FAILED' % fails)
    sys.exit(1)
print('ALL PASS -- a challenge, an absent tool and a CRLF difference each '
      'produce the right one of three answers.')
