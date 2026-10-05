#!/usr/bin/env python
"""Control for tools/gh_token.py --live, written before the verdicts were trusted.

# REQUIREMENT: `gh_token.py` must be able to say whether the credential WORKS,
#   not only that one was FOUND -- and it must keep three verdicts apart:
#   GOOD, REJECTED, and COULD NOT RUN. A network failure is never either of the
#   other two, because calling it "rejected" sends somebody to rotate a working
#   token and calling it "good" is the original defect.

WHY THE KNOWN-BAD IS AN ABSENT HEADER. GitHub does not emit `x-oauth-scopes` at
all for a fine-grained PAT. A classifier that reads the header with `or ''` --
the obvious spelling -- reports "scopes: none" for a token that may hold every
permission it needs, and reports the identical string for a CLASSIC PAT with
zero scopes selected, which is a real and nearly useless state. Two opposite
facts, one output. Arms B and C require them told apart.

The same shape is already in this file's own history: `_from_env_files()`
distinguishes a MISSING .env.local from one that EXISTS AND IS 0 BYTES, because
not distinguishing them is what made a seven-week failure invisible. The
expiration header recurs it a third time -- ABSENT means "no expiry", which is
information, and must not be reported as unknown.

WHY classify() IS PURE AND THIS CONTROL NEEDS NO NETWORK. Every arm below drives
synthetic status codes and header dicts. The criteria are locked against
fixtures before the tool is trusted on a real credential (discipline 1), and the
control cannot go green-because-offline. Arm F is the only one that touches the
wire, and it is written so that no-network is a PASS of the could-not-run path
rather than a failure of the suite.

Run:  python tests/run_gh_token_live_probe.py
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'gh_token.py')
sys.path.insert(0, os.path.join(REPO, 'tools'))

CRITERIA_VERSION = '2026-10-05.1'

_pass = _fail = 0


def ok(n):
    global _pass
    _pass += 1
    sys.stdout.write('  ok   %s\n' % n)


def bad(n, why):
    global _fail
    _fail += 1
    sys.stdout.write('  FAIL %s\n       %s\n' % (n, why))


def section(t):
    sys.stdout.write('\n%s\n' % t)


def main():
    if not os.path.isfile(TOOL):
        sys.stderr.write('tools/gh_token.py is missing -- COULD NOT RUN, '
                         'which is not a pass.\n')
        return 2
    try:
        import gh_token
    except Exception as exc:                                      # noqa: BLE001
        sys.stderr.write('tools/gh_token.py does not import (%s) -- COULD NOT '
                         'RUN, which is not a pass.\n' % exc)
        return 2
    sys.stdout.write('GH TOKEN LIVE CONTROL -- criteria %s\n'
                     % CRITERIA_VERSION)

    C = gh_token.classify

    def text(status, hdrs):
        v, lines = C(status, hdrs)
        return v, '\n'.join(lines)

    # ── A. THE VERDICTS ARE THREE, NOT TWO ────────────────────────────────
    section('A. THREE VERDICTS, and the third is never folded into either')

    v, o = text(401, {})
    if v == 'rejected' and 'REJECTED' in o and '401' in o:
        ok('A1. 401 is REJECTED and says the credential is revoked, expired or '
           'invalid, with the re-seed command')
    else:
        bad('A1. 401 must be REJECTED', '%s\n%s' % (v, o))

    v, o = text(403, {})
    if v == 'rejected' and 'UNVERIFIED' in o:
        ok('A2. 403 is REJECTED and says so in PR 3.2\'s words -- a 403 means '
           'UNVERIFIED, never verified-good. The same rule this platform '
           'applies to a deployment, applied to a credential')
    else:
        bad('A2. 403 must be REJECTED and must not read as a pass',
            '%s\n%s' % (v, o))

    v, o = text(500, {})
    if v == 'could-not-run' and 'COULD NOT RUN' in o:
        ok('A3. a 500 is COULD NOT RUN -- GitHub failing is not an answer '
           'about the credential')
    else:
        bad('A3. a non-200 non-4xx must be COULD NOT RUN', '%s\n%s' % (v, o))

    # ── B. THE KNOWN-BAD: ABSENT IS NOT EMPTY ─────────────────────────────
    section('B. THE KNOWN-BAD: an ABSENT scopes header is not an EMPTY one')

    v_fine, o_fine = text(200, {})                       # header ABSENT
    v_zero, o_zero = text(200, {'x-oauth-scopes': ''})   # header PRESENT, empty

    if v_fine == 'good' and v_zero == 'good':
        ok('B0. both authenticate -- so the arms below are about the '
           'DESCRIPTION, not about the verdict')
    else:
        bad('B0. both must be good', '%s / %s' % (v_fine, v_zero))

    if o_fine != o_zero:
        ok('B1. KNOWN-BAD: the two produce DIFFERENT output. A classifier '
           'reading the header with `or \'\'` -- the obvious spelling -- '
           'reports the same "scopes: none" for both, which is two opposite '
           'facts in one string')
    else:
        bad('B1. absent and empty scopes must not produce identical output',
            'both:\n%s' % o_fine)

    if 'FINE-GRAINED' in o_fine and 'NOT ENUMERABLE' in o_fine:
        ok('B2. the ABSENT case names a FINE-GRAINED PAT and says its '
           'permissions are NOT ENUMERABLE by this tool -- stated, rather '
           'than reported as "none"')
    else:
        bad('B2. absent must be reported as not-enumerable', o_fine)

    if 'ZERO scopes' in o_zero and 'cannot push' in o_zero:
        ok('B3. the EMPTY case names a CLASSIC PAT with zero scopes and says '
           'it cannot push -- a real state, and the one that actually is '
           '"none"')
    else:
        bad('B3. empty must be reported as zero-scopes', o_zero)

    if 'NO' in o_zero.split('push ready')[-1][:40]:
        ok('B4. ...and push-ready is NO for it, so B3 is not passing on prose '
           'alone')
    else:
        bad('B4. zero scopes must not be push-ready', o_zero)

    # ── C. A POPULATED CLASSIC TOKEN, AND THE MISSING-SCOPE DIRECTION ─────
    section('C. A populated classic token, both directions')

    v, o = text(200, {'x-oauth-scopes': 'gist, repo, workflow'})
    if v == 'good' and 'CLASSIC PAT' in o and 'yes' in o.split('push ready')[-1][:30]:
        ok('C1. a classic PAT carrying `repo` is push-ready and is named as a '
           'classic PAT')
    else:
        bad('C1. a repo-scoped classic PAT must be push-ready', o)

    v, o = text(200, {'x-oauth-scopes': 'gist, read:org'})
    if v == 'good' and 'missing repo' in o:
        ok('C2. ...and one WITHOUT `repo` is reported NOT push-ready, naming '
           'what is missing. Without this, C1 could be passing because every '
           'token is called ready')
    else:
        bad('C2. a token lacking repo must say so', o)

    # ── D. EXPIRY, WHERE ABSENT IS THE INFORMATIVE CASE ───────────────────
    section('D. EXPIRY -- and the absence of the header is INFORMATION')

    v, o = text(200, {'x-oauth-scopes': 'repo'})
    if 'expires      : NEVER' in o and 'NOT THE ONE IT WAS SET' in o:
        ok('D1. no expiration header means NO EXPIRY, and the output says that '
           'a rotation deadline set for this credential is therefore about a '
           'DIFFERENT one. This is the exact finding the live check was built '
           'for: a dispatch named a token expiring Oct 4 and the credential '
           'answering had no expiry at all')
    else:
        bad('D1. an absent expiry header must be reported as NEVER, with the '
            'deadline consequence named', o)

    v, o = text(200, {'x-oauth-scopes': 'repo',
                      'github-authentication-token-expiration':
                          '2026-10-04 12:00:00 UTC'})
    if '2026-10-04' in o and 'NEVER' not in o:
        ok('D2. a real expiry is printed verbatim and does NOT also say never, '
           'so D1 is not passing because the branch is unreachable')
    else:
        bad('D2. a present expiry must be printed and must suppress NEVER', o)

    v, o = text(200, {'x-oauth-scopes': 'repo',
                      'github-authentication-token-expiration': ''})
    if 'COULD NOT TELL' in o:
        ok('D3. a PRESENT-BUT-EMPTY expiry header is COULD NOT TELL, not '
           '"never" -- the third state of the same absent-vs-empty '
           'distinction, and GitHub is not documented to do it')
    else:
        bad('D3. an empty expiry header must not be read as never', o)

    # ── E. THE LOOKUP STAYED PURE, which is the half that protects 6 tools ─
    section('E. THE DEFAULT PATH IS UNCHANGED AND MAKES NO NETWORK CALL')

    r = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=120)
    o = (r.stdout or '') + (r.stderr or '')
    if 'token source' in o and 'token length' in o:
        ok('E1. the bare invocation still reports source and length -- the '
           'contract six importing tools depend on is not changed')
    else:
        bad('E1. the default output must be unchanged', o[-400:])

    if 'NOT VERIFIED' in o and 'nothing above contacted GitHub' in o:
        ok('E2. ...and it now DECLINES the reading that was the defect, in its '
           'own output: a token was FOUND, whether it WORKS is untested here. '
           'The fix is not only the new flag -- the old output was being '
           'misread and now says so')
    else:
        bad('E2. the default output must say what it did not test', o[-400:])

    if '--live' in o:
        ok('E3. ...and names the flag that does test it, so the reader is not '
           'left with a disclaimer and no route')
    else:
        bad('E3. the default output must name --live', o[-300:])

    import inspect
    src = inspect.getsource(gh_token.github_token)
    if 'fetch_user' not in src and 'urlopen' not in src:
        ok('E4. github_token() does not call the network. THIS IS THE ARM '
           'THAT MATTERS MOST: if the lookup fetched, then on a clone with no '
           'network all six importers would be told there is NO TOKEN -- a '
           'working credential plus a dead network reported as a missing '
           'credential')
    else:
        bad('E4. github_token() must stay pure', src)

    # ── F. THE REAL CREDENTIAL, and no-network is a PASS of the third path ─
    section('F. THE REAL RUN -- and offline is a pass of COULD NOT RUN')

    r = subprocess.run([sys.executable, TOOL, '--live'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace',
                       timeout=180)
    o = (r.stdout or '') + (r.stderr or '')
    if r.returncode == 0 and 'verdict      : GOOD' in o:
        ok('F1. the real credential VERIFIES: exit 0, authenticated, with type, '
           'scopes and expiry reported')
    elif r.returncode == 2 and 'COULD NOT RUN' in o:
        ok('F1. COULD NOT RUN and exit 2 -- no token or no network. THIS IS A '
           'PASS of the third path and the suite says so rather than going '
           'green because it is offline')
    elif r.returncode == 1 and 'REJECTED' in o:
        bad('F1. THE REAL CREDENTIAL IS REJECTED -- the tool works and the '
            'token does not. Rotate it.', o[-500:])
    else:
        bad('F1. --live must return one of the three verdicts',
            'exit=%s\n%s' % (r.returncode, o[-500:]))

    if 'the value is never printed' in o:
        ok('F2. ...and the live path still never prints the token. A '
           'credential has been pasted into a chat on this platform three '
           'times, and a prefix is enough to confirm a guess')
    else:
        bad('F2. the live path must not print the token', o[-300:])

    tok_in_output = False
    try:
        t, _ = gh_token.github_token()
        tok_in_output = t in o
    except Exception:                                             # noqa: BLE001
        pass
    if not tok_in_output:
        ok('F3. KNOWN-BAD, CHECKED DIRECTLY RATHER THAN BY WORDING: the real '
           'token string does not appear anywhere in the live output. F2 '
           'checks that a promise is printed; this checks the promise is kept')
    else:
        bad('F3. THE TOKEN LEAKED INTO THE OUTPUT', 'redact immediately')

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
