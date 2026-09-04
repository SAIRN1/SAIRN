"""
tests/sairn_http_response_shape.py -- `in` against a fetch result must not be
silently False, and everything else about that result must not change.

WHAT THIS PROTECTS. On 2026-09-04 a live-verify of a just-pushed fix wrote

    if 'marker-from-the-fix' in sairn_http.fetch(url):

and reported the fix ABSENT for seven minutes across 20 polls. `in` against a
2-tuple is a MEMBERSHIP test -- it asked "is this string one of these two
elements", correctly answered False, and never looked at the body. The deploy
had been READY the whole time.

That is the exact failure class `sairn_http` was written to stop -- a check
that stops checking and says nothing -- arriving inside the module that stops
it. So the guard belongs here rather than in a rule someone has to remember.

TWO HALVES, AND THE SECOND IS THE REASON THIS FILE IS LONGER THAN THE FIX.
A guard that also changed the return shape would break two working callers to
fix a mistake neither of them made, so most of these assertions are the
BACKWARD-COMPATIBILITY half: it is still a tuple, it still unpacks, it still
compares equal to the plain tuple it used to be.

Offline: nothing here touches the network.
"""
import os
import sys
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sairn_http  # noqa: E402

passed = failed = 0


def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
        print('  ok   ' + name)
    else:
        failed += 1
        print('  FAIL ' + name + '\n         expected %r\n         actual   %r'
              % (expected, actual))


def section(t):
    print('--- ' + t + ' ---')


print('sairn_http -- the response shape, and the one misuse that was silent')

R = sairn_http.Response
resp = R(200, b'<html>marker-from-the-fix</html>')

# ── the defect itself ──────────────────────────────────────────────────
section('the silent membership test is now loud')

try:
    'marker-from-the-fix' in resp
    check('a str `in` the response RAISES instead of answering False',
          'no raise', 'TypeError')
except TypeError as e:
    check('a str `in` the response RAISES instead of answering False', True, True)
    # The message has to carry the fix, not just the complaint -- the reader
    # is mid-verification and needs the working spelling, now.
    check('and the message says it is always False', 'ALWAYS False' in str(e), True)
    check('and names response.body as the thing to search',
          'response.body' in str(e), True)
    check('and shows the unpack that also works',
          'status, body = sairn_http.fetch(url)' in str(e), True)

# bytes is the same mistake -- a caller comparing against a bytes literal is
# doing exactly what the body actually is, so this one is EASIER to write.
for operand, label in [(b'marker-from-the-fix', 'bytes'),
                       (bytearray(b'marker'), 'bytearray')]:
    try:
        operand in resp
        check('a %s `in` the response raises too' % label, 'no raise', 'TypeError')
    except TypeError:
        check('a %s `in` the response raises too' % label, True, True)

# ...and the working spelling is not broken by the guard.
check('`in response.body` still works and finds it',
      b'marker-from-the-fix' in resp.body, True)
check('`in response.body` still reports a genuine absence',
      b'not-in-here' in resp.body, False)

# ── the guard is NARROW ────────────────────────────────────────────────
section('and it does not break ordinary tuple membership')
# Only str/bytes are guarded, because only those spellings are the mistake.
# Refusing every `in` would be a bigger behaviour change than the bug.
check('a non-string member still answers normally (present)', 200 in resp, True)
check('a non-string member still answers normally (absent)', 404 in resp, False)

# ── the backwards-compatibility half ───────────────────────────────────
section('everything else about the result is unchanged')

check('it is still a tuple', isinstance(resp, tuple), True)
check('it still unpacks', list(resp) == [200, resp.body], True)
check('it still indexes', (resp[0], resp[1]) == (200, resp.body), True)
check('it still has length 2', len(resp), 2)
check('it still compares EQUAL to the plain tuple it used to be',
      resp == (200, b'<html>marker-from-the-fix</html>'), True)
check('and a plain tuple compares equal to it, in that direction too',
      (200, b'<html>marker-from-the-fix</html>') == resp, True)
check('.status reads the status', resp.status, 200)
check('.body reads the body', resp.body, b'<html>marker-from-the-fix</html>')

status, body = sairn_http.Response(204, b'')
check('the two-name unpack every real caller uses still works',
      (status, body), (204, b''))

# ── both entry points return it ────────────────────────────────────────
section('fetch() and fetch_json() both hand back the guarded type')


class _FakeResp:
    status = 201

    def __init__(self, payload):
        self._p = payload

    def read(self):
        return self._p

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_real_urlopen = sairn_http.urllib.request.urlopen
try:
    sairn_http.urllib.request.urlopen = lambda req, timeout=None: _FakeResp(b'{"ok":true}')
    r = sairn_http.fetch('https://example.invalid/x')
    check('fetch() returns a Response', isinstance(r, sairn_http.Response), True)
    check('fetch() still returns the real status and body', (r.status, r.body),
          (201, b'{"ok":true}'))

    j = sairn_http.fetch_json('https://example.invalid/x', payload={})
    check('fetch_json() returns a Response', isinstance(j, sairn_http.Response), True)
    check('fetch_json() still parses the reply', (j.status, j.body),
          (201, {'ok': True}))
    try:
        'ok' in j
        check('and fetch_json()\'s result refuses the same silent test',
              'no raise', 'TypeError')
    except TypeError:
        check('and fetch_json()\'s result refuses the same silent test', True, True)
    check('while `in .body` reads the parsed JSON normally', 'ok' in j.body, True)
finally:
    sairn_http.urllib.request.urlopen = _real_urlopen


# fetch_json's ERROR path builds its own tuples, and an error reply is exactly
# when someone greps the result for a message.
class _FakeHTTPError(urllib.error.HTTPError):
    def __init__(self, body):
        self._b = body
        urllib.error.HTTPError.__init__(
            self, 'https://example.invalid/x', 400, 'Bad Request', {}, None)

    def read(self):
        return self._b


for payload, label, expect in [(b'{"error":"nope"}', 'a JSON error body', {'error': 'nope'}),
                               (b'not json', 'a NON-JSON error body', None)]:
    try:
        sairn_http.urllib.request.urlopen = \
            (lambda p: (lambda req, timeout=None: (_ for _ in ()).throw(_FakeHTTPError(p))))(payload)
        j = sairn_http.fetch_json('https://example.invalid/x', payload={})
        check('the error path returns a Response too (%s)' % label,
              isinstance(j, sairn_http.Response), True)
        check('  ...with the real status (%s)' % label, j.status, 400)
        if expect is not None:
            check('  ...and the parsed body (%s)' % label, j.body, expect)
        else:
            check('  ...and the raw text wrapped, not lost (%s)' % label,
                  'not json' in j.body['error']['message'], True)
    finally:
        sairn_http.urllib.request.urlopen = _real_urlopen

# ── the real callers ───────────────────────────────────────────────────
section('the two real fetch() callers unpack, so nothing downstream moved')
# Asserted on the source rather than run, because both of them talk to the
# live site. If a third caller appears that does NOT unpack, this list is
# where someone has to look at it.
dvn = open(os.path.join(ROOT, 'tools', 'deploy_verify_notify.py'), encoding='utf-8').read()
check('deploy_verify_notify unpacks its fetch',
      '_, remote_bytes = sairn_http.fetch(' in dvn, True)

# ── NEGATIVE CONTROL ───────────────────────────────────────────────────
section('NEGATIVE CONTROL -- the assertion above is measuring the guard')
# Without this, deleting __contains__ entirely would leave every assertion in
# this file green except one, and "a str in a tuple is False" would read as a
# passing test rather than as the bug. Two arms: a plain tuple must exhibit
# the ORIGINAL silent behaviour, and a copy of the module with the guard
# stripped must stop raising.
plain = (200, b'<html>marker-from-the-fix</html>')
check('a PLAIN tuple still answers False silently -- the bug, reproduced',
      'marker-from-the-fix' in plain, False)

import re  # noqa: E402
import types  # noqa: E402

src = open(os.path.join(ROOT, 'tools', 'sairn_http.py'), encoding='utf-8').read()
stripped, n = re.subn(
    r'\n    def __contains__\(self, item\):.*?return tuple\.__contains__\(self, item\)\n',
    '\n', src, flags=re.S)
check('the guard was found in the source and removed for the control', n, 1)
mutant = types.ModuleType('sairn_http_mutant')
mutant.__dict__['__file__'] = os.path.join(ROOT, 'tools', 'sairn_http.py')
exec(compile(stripped, 'sairn_http_mutant', 'exec'), mutant.__dict__)
check('WITHOUT the guard the same expression is silently False again -- so the '
      'assertion at the top is testing the guard, not the language',
      'marker-from-the-fix' in mutant.Response(200, b'<html>marker-from-the-fix</html>'),
      False)
# And the compatibility half must still hold in the mutant, which proves those
# assertions are NOT what catches the regression -- they are the safety net,
# and they would have stayed green through the entire seven-minute failure.
check('...while the mutant still unpacks, i.e. the compat assertions cannot '
      'catch this on their own',
      tuple(mutant.Response(200, b'x')), (200, b'x'))

print(('FAILED %d/%d' % (failed, passed + failed)) if failed
      else ('ALL %d RESPONSE-SHAPE ASSERTIONS PASS' % passed))
sys.exit(1 if failed else 0)
