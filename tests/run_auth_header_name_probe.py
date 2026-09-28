#!/usr/bin/env python3
"""tests/run_auth_header_name_probe.py -- the KNOWN-BAD control for
tools/auth_header_name_sweep.py: it must go red when a caller sends a session
header the server never reads.

Run:  python tests/run_auth_header_name_probe.py

── WHY A CONTROL AND NOT JUST THE SWEEP ──────────────────────────────────
The sweep currently reports ZERO mismatches. A checker reporting zero is
indistinguishable from a checker that cannot find anything, and this one in
particular could report zero for three different wrong reasons: its header regex
stops matching, its derivation of the server's name silently changes, or its
stubbed-exemption swallows the whole population. Each arm below plants one and
asserts the sweep notices.

── THE DEFECT IT IS CONTROLLING FOR ──────────────────────────────────────
tools/alf_facility_role_gate_live_probe.py sent `X-Session-Token`;
api/_lib/auth.js's tokenFromRequest() reads `x-sd-auth` and nothing else. Every
request it ever made carried no session, so every role got the identical
no-session answer and the role differentiation the probe exists to demonstrate
was never exercised. Nothing 400s on a wrong header name -- the request is well
formed and the server answers the no-session branch -- which is why this needs a
checker rather than a test run.

── AND THE EXEMPTION IS THE PART MOST LIKELY TO ROT ──────────────────────
37 files are exempt because they REPLACE tokenFromRequest and therefore choose
their own header. That exemption is a property of the file, not a name on a
list, so it expires by itself when the stub is removed -- arm 3 drives exactly
that transition, because an exemption that outlives its reason is the hole this
platform keeps closing.
"""
import io
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import auth_header_name_sweep as S  # noqa: E402

FAILURES = []
N = [0]


def expect(name, got, want):
    N[0] += 1
    if got != want:
        FAILURES.append('%s\n     wanted %r, got %r' % (name, want, got))
        print('  FAIL %s' % name)
    else:
        print('  ok   %s' % name)


def sandbox():
    """A throwaway tree with a real auth.js and a tools/ dir the sweep scans."""
    d = tempfile.mkdtemp(prefix='authhdr-')
    os.makedirs(os.path.join(d, 'api', '_lib'))
    os.makedirs(os.path.join(d, 'tools'))
    io.open(os.path.join(d, 'api', '_lib', 'auth.js'), 'w',
            encoding='utf-8', newline='\n').write(
        "function tokenFromRequest(req) {\n"
        "  const h = req.headers['x-sd-auth'];\n"
        "  return typeof h === 'string' && h.trim() ? h.trim() : null;\n"
        "}\n")
    return d


def write(d, rel, text):
    p = os.path.join(d, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(text)


def run(d):
    """(expected_header, wrong_list, stubbed_set) against the sandbox."""
    S.REPO = d
    S.AUTH = os.path.join(d, 'api', '_lib', 'auth.js')
    exp = S.server_header()
    senders, wrong, stubbed = S.scan(exp)
    return exp, wrong, stubbed, senders


def main():
    print('AUTH HEADER NAME PROBE -- the sweep must go RED on a planted defect')
    saved = (S.REPO, S.AUTH)
    d = sandbox()
    try:
        # ── 1. THE REAL DEFECT, PLANTED ──────────────────────────────────
        print('')
        print('1. a caller sending the wrong header, with no stub')
        write(d, 'tools/live_probe.py',
              "hdrs['X-Session-Token'] = token\n")
        exp, wrong, stubbed, senders = run(d)
        expect('the expected header is DERIVED as x-sd-auth', exp, 'x-sd-auth')
        expect('the wrong-header caller is CAUGHT',
               sorted(r for r, _ in wrong), ['tools/live_probe.py'])
        expect('and it is not silently exempted', 'tools/live_probe.py' in stubbed,
               False)

        # ── 2. THE CORRECT SPELLING IS NOT FLAGGED ───────────────────────
        print('')
        print('2. THE CONTROL -- a correct caller must NOT be reported')
        write(d, 'tools/live_probe.py', "hdrs['X-SD-Auth'] = token\n")
        exp, wrong, stubbed, senders = run(d)
        expect('case-insensitive: X-SD-Auth matches x-sd-auth',
               [r for r, _ in wrong], [])
        expect('but the file is still COUNTED as a sender, not dropped',
               'tools/live_probe.py' in senders, True)

        # ── 3. THE EXEMPTION EXPIRES WITH ITS REASON ─────────────────────
        print('')
        print('3. the stub exemption is a property of the file, not a name')
        stubbed_src = (
            "authMod.tokenFromRequest = (req) => req.headers['x-test-token'];\n"
            "headers = {'x-test-token': 'abc'}\n")
        write(d, 'tools/harness_suite.py', stubbed_src)
        exp, wrong, stubbed, senders = run(d)
        expect('a file that REPLACES the reader is exempt',
               'tools/harness_suite.py' in stubbed, True)
        expect('and is therefore NOT reported as wrong',
               [r for r, _ in wrong], [])
        # Remove the stub, keep the header: the exemption must expire.
        write(d, 'tools/harness_suite.py', "headers = {'x-test-token': 'abc'}\n")
        exp, wrong, stubbed, senders = run(d)
        expect('REMOVE THE STUB and the same file is now CAUGHT',
               sorted(r for r, _ in wrong), ['tools/harness_suite.py'])

        # ── 4. FAIL CLOSED ON THE DERIVATION ─────────────────────────────
        print('')
        print('4. the derivation fails CLOSED, never to a hardcoded default')
        for label, body in (
                ('tokenFromRequest is gone',
                 "function somethingElse(req) { return null; }\n"),
                ('it reads NO header',
                 "function tokenFromRequest(req) {\n  return req.token || null;\n}\n"),
                ('it reads TWO headers',
                 "function tokenFromRequest(req) {\n"
                 "  return req.headers['x-sd-auth'] || req.headers['x-other'];\n}\n")):
            io.open(os.path.join(d, 'api', '_lib', 'auth.js'), 'w',
                    encoding='utf-8', newline='\n').write(body)
            S.AUTH = os.path.join(d, 'api', '_lib', 'auth.js')
            raised = False
            try:
                S.server_header()
            except S.CouldNotTell:
                raised = True
            expect('COULD NOT TELL when ' + label, raised, True)
    finally:
        S.REPO, S.AUTH = saved
        shutil.rmtree(d, ignore_errors=True)

    print('')
    if FAILURES:
        print('%d of %d FAILED:' % (len(FAILURES), N[0]))
        for f in FAILURES:
            print('  - %s' % f)
        return 1
    print('%d/%d passed.' % (N[0], N[0]))
    print('')
    print('WHAT THIS DOES NOT PROVE: that any caller sends a VALID session, or')
    print('that a caller which sends none SHOULD send one. The first needs a live')
    print('run with real credentials; the second is tools/gate_caller_impact.py.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
