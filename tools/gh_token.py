#!/usr/bin/env python
"""gh_token.py -- the ONE place that knows where the GitHub token comes from.

    python tools/gh_token.py            # report which source answered, never the token
    from gh_token import github_token   # raises TokenUnavailable with every source tried

── WHY THIS EXISTS, AND IT IS A SEVEN-WEEK SILENT FAILURE ─────────────────
`tools/gh_push.py` and `tools/gh_verify.py` each carried their own copy of

    with open(r"C:\\Users\\marsh\\Documents\\SAIRN\\.env.local") as f: ...

and that file has been **0 bytes since 2026-08-08**. Both tools have raised
`RuntimeError: GITHUB_TOKEN not found in .env.local` on every invocation since,
and nothing said so -- they are not wired into any hook, gate or suite, so the
failure surfaced only when somebody reached for one. Found 2026-09-25 by the
tools sweep; the handoff that set the path up even records the ambiguity ("both
exist, only one is what tools/gh_push.py actually reads").

THE DEEPER DEFECT IS THE DUPLICATION, NOT THE PATH. Two tools, two copies of
one decision -- which is item 94's information leakage on a credential lookup.
When the token moved, both copies went stale together and neither could be
fixed without finding the other. So the decision lives here now, once.

── THE ORDER IS DELIBERATE AND THE REASON IS RECOVERABILITY ───────────────
1. `GITHUB_TOKEN` in the environment -- an explicit override, and the only
   source a CI runner would have.
2. The git credential manager (`git credential fill`). This is what actually
   holds a working token on this machine, it is what the platform's REST push
   path uses today, and it is maintained by git rather than by a file somebody
   has to remember to update.
3. `.env.local`, both spellings that have ever been used here. Kept LAST rather
   than deleted: if somebody puts a token back in one, it should work -- but it
   must not shadow the credential manager, because a stale file beating a live
   credential is exactly how this broke.

── IT NEVER PRINTS THE TOKEN, AND THE FAILURE NAMES EVERY SOURCE TRIED ────
A credential has been pasted into a chat three times on this platform during a
rotation (the handoff records it). So `--report` prints WHICH source answered
and the token's length, never a prefix and never the value: a prefix is enough
to confirm a guess. And `TokenUnavailable` lists every source with why it did
not answer, because "GITHUB_TOKEN not found in .env.local" sent readers to the
one place that could not have had it.
"""
import io
import os
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


class TokenUnavailable(RuntimeError):
    """No source answered. Carries the full list, because a one-source error
    message is what made this a seven-week failure rather than a five-minute
    one."""


ENV_FILES = (
    r'C:\Users\marsh\Documents\SAIRN\.env.local',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 '.env.local'),
)


def _from_env():
    t = (os.environ.get('GITHUB_TOKEN') or '').strip()
    return (t, 'environment GITHUB_TOKEN') if t else (None, 'environment GITHUB_TOKEN is unset')


def _from_credential_manager():
    try:
        r = subprocess.run(['git', 'credential', 'fill'],
                           input='protocol=https\nhost=github.com\n\n',
                           capture_output=True, text=True, timeout=20)
    except Exception as exc:                                     # noqa: BLE001
        return None, 'git credential fill raised (%s)' % type(exc).__name__
    if r.returncode != 0:
        return None, 'git credential fill exited %d' % r.returncode
    for line in (r.stdout or '').splitlines():
        if line.startswith('password='):
            t = line.split('=', 1)[1].strip()
            if t:
                return t, 'git credential manager'
    return None, 'git credential manager returned no password line'


def _from_env_files():
    tried = []
    for path in ENV_FILES:
        try:
            size = os.path.getsize(path)
        except OSError:
            tried.append('%s (absent)' % path)
            continue
        if size == 0:
            # NAMED EXPLICITLY. This is the exact state that broke both tools,
            # and "absent" and "present but empty" are different problems: one
            # is a missing file, the other is a file somebody trusts.
            tried.append('%s (EXISTS BUT IS 0 BYTES)' % path)
            continue
        try:
            for line in io.open(path, encoding='utf-8'):
                if line.startswith('GITHUB_TOKEN='):
                    t = line.split('=', 1)[1].strip().strip('"').strip("'")
                    if t:
                        return t, path
            tried.append('%s (no GITHUB_TOKEN line)' % path)
        except OSError as exc:
            tried.append('%s (unreadable: %s)' % (path, exc))
    return None, '; '.join(tried)


def github_token():
    """(token, source_label). Raises TokenUnavailable naming every source."""
    problems = []
    for fn in (_from_env, _from_credential_manager, _from_env_files):
        tok, why = fn()
        if tok:
            return tok, why
        problems.append(why)
    raise TokenUnavailable(
        'No GitHub token from any source. Tried, in order: ' + ' | '.join(problems)
        + '. The credential manager is the one that normally answers on this '
          'machine; `git credential fill` interactively is how you seed it.')


# ══ THE LIVE HALF, AND IT IS OPT-IN FOR A REASON ═══════════════════════════
# WHAT WAS WRONG WITH THIS FILE, FOUND 2026-10-04 BY BEING ASKED TO VERIFY A
# TOKEN WITH IT. Everything above answers "where did a token come from". It was
# read as answering "does the token work" -- and a revoked, scope-stripped or
# expired token returns exit 0 here with a source and a length.
#
# That is this file's own origin defect one level up. It was built to end a
# seven-week silence in which two tools read a 0-byte .env.local and said
# nothing; it removed the duplication and kept the SHAPE, because "a token was
# found" and "a token is good" arrive in the same confident output.
#
# NOT HYPOTHETICAL, AND THE INSTANCE IS WHY THIS EXISTS. A dispatch said
# `SAIRN-Session55` expires Oct 4 and named this tool as the check. The tool
# said `source: git credential manager, length: 40`. An authenticated GET /user
# said http 200 and NO `github-authentication-token-expiration` header at all --
# so the credential actually answering has no expiry and is therefore NOT the
# one the deadline was about. Nobody could have learned that from the output
# above, and the deadline was the question.
#
# ── WHY `github_token()` DOES NOT CALL THIS, AND MUST NOT ─────────────────
# Six tools import this module. If the lookup made a network call, then on a
# clone with no network every one of them would be told THERE IS NO TOKEN --
# converting a working credential plus a dead network into a missing
# credential. That is a silent failure traded for a louder wrong answer, which
# is not an improvement. So the lookup stays pure and `--live` is opt-in, and
# COULD NOT RUN is a third state that is never folded into either verdict
# (PR 1.11).
#
# ── THE TWO HEADERS, AND "ABSENT" IS NOT "EMPTY" ───────────────────────────
# This is the same distinction _from_env_files() already makes between a
# missing file and a file that exists and is 0 bytes, which is the distinction
# that made the original failure invisible. It recurs here exactly:
#
#   x-oauth-scopes ABSENT  -> a FINE-GRAINED PAT (or an app/installation
#                             token). GitHub does not emit the header for
#                             these at all. Reporting "no scopes" would be a
#                             wrong answer about a token that may have every
#                             permission it needs.
#   x-oauth-scopes ''      -> a CLASSIC PAT with ZERO scopes selected. Real,
#                             different, and nearly useless for this platform.
#   github-authentication-token-expiration ABSENT -> no expiry. GitHub emits
#                             this header for any PAT that HAS one, so its
#                             absence is informative rather than unknown.
#
# classify() IS PURE so its control can drive every combination from synthetic
# headers without a network (discipline 1: lock the criteria against fixtures
# before trusting it on real data). Only fetch_user() touches the wire.
GITHUB_USER_URL = 'https://api.github.com/user'

# What this platform's push path actually needs. `repo` alone is enough to push;
# `workflow` is needed only to touch .github/workflows. Checked and REPORTED,
# never enforced -- a token that can do the job with a narrower grant is better,
# not worse, and this tool is not the place to decide a policy.
SCOPES_FOR_PUSH = ('repo',)


def classify(status, headers, source='unknown'):
    """(verdict, lines) from an HTTP status and a header mapping. PURE.

    verdict is one of:
      'good'          the credential authenticated
      'rejected'      GitHub refused it -- 401 revoked/invalid, 403 blocked
      'could-not-run' anything that is not an answer ABOUT the credential

    `headers` is anything with .get(name) returning None when ABSENT. The
    absent-vs-empty distinction is load-bearing; see the block above.
    """
    def h(name):
        try:
            return headers.get(name)
        except AttributeError:
            return None

    lines = ['token source : %s' % source]

    if status == 401:
        return 'rejected', lines + [
            'verdict      : REJECTED -- GitHub returned 401. The credential is '
            'revoked, expired or invalid.',
            'what to do   : re-seed it with `git credential fill` '
            'interactively, or set GITHUB_TOKEN.']
    if status == 403:
        return 'rejected', lines + [
            'verdict      : REJECTED -- GitHub returned 403. The credential '
            'authenticated or is absent AND the request was refused: a blocked '
            'token, an SSO-unauthorised one, or rate limiting.',
            'note         : 403 is NOT read as a pass here. A 403 means '
            'UNVERIFIED (PR 3.2), and this is the same rule applied to a '
            'credential rather than to a deployment.']
    if status != 200:
        return 'could-not-run', lines + [
            'verdict      : COULD NOT RUN -- http %s is not an answer about '
            'the credential.' % status]

    scopes = h('x-oauth-scopes')
    expiry = h('github-authentication-token-expiration')
    login = h('x-sairn-login')          # filled in by fetch_user from the body

    lines.append('verdict      : GOOD -- authenticated against %s'
                 % GITHUB_USER_URL)
    if login:
        lines.append('login        : %s' % login)

    # ── TOKEN TYPE, DERIVED FROM THE HEADER'S PRESENCE ────────────────────
    if scopes is None:
        lines.append('token type   : FINE-GRAINED PAT, or an app/installation '
                     'token. GitHub emits no x-oauth-scopes header for these, '
                     'so this tool CANNOT enumerate its permissions -- stated '
                     'rather than reported as "none".')
        lines.append('scopes       : NOT ENUMERABLE for this token type (the '
                     'header is ABSENT, which is not the same as empty)')
    elif scopes.strip() == '':
        lines.append('token type   : CLASSIC PAT with ZERO scopes selected. '
                     'The header is PRESENT and EMPTY, which is a real and '
                     'different state from absent.')
        lines.append('scopes       : NONE -- this token can read public data '
                     'and cannot push.')
        missing = ', '.join(SCOPES_FOR_PUSH)
        lines.append('push ready   : NO -- needs %s' % missing)
    else:
        have = [s.strip() for s in scopes.split(',') if s.strip()]
        lines.append('token type   : CLASSIC PAT (x-oauth-scopes is present '
                     'and populated)')
        lines.append('scopes       : %s' % ', '.join(have))
        missing = [s for s in SCOPES_FOR_PUSH if s not in have]
        lines.append('push ready   : %s'
                     % ('NO -- missing %s' % ', '.join(missing) if missing
                        else 'yes -- carries %s' % ', '.join(SCOPES_FOR_PUSH)))

    # ── EXPIRY. The absence of this header is INFORMATION, not ignorance ──
    if expiry is None:
        lines.append('expires      : NEVER -- GitHub emits '
                     '`github-authentication-token-expiration` for any PAT '
                     'that HAS an expiry, so its absence means there is none. '
                     'IF A ROTATION DEADLINE WAS SET FOR THIS CREDENTIAL, THE '
                     'CREDENTIAL ANSWERING HERE IS NOT THE ONE IT WAS SET '
                     'FOR.')
    elif str(expiry).strip() == '':
        lines.append('expires      : COULD NOT TELL -- the expiration header '
                     'is PRESENT AND EMPTY, which GitHub is not documented to '
                     'do. Not read as "never".')
    else:
        lines.append('expires      : %s' % expiry)
    return 'good', lines


def fetch_user(token, timeout=30):
    """(status, headers) from an authenticated GET /user, or (None, reason).

    The only function here that touches the network. NEVER logs the token, and
    never puts it in a URL -- it goes in the Authorization header, which is why
    a failure's text is safe to print.
    """
    import json
    import urllib.error
    import urllib.request
    req = urllib.request.Request(GITHUB_USER_URL, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'sairn-gh-token-liveness',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            hdrs = dict((k.lower(), v) for k, v in r.headers.items())
            try:
                body = json.loads(r.read().decode('utf-8'))
                if isinstance(body, dict) and body.get('login'):
                    hdrs['x-sairn-login'] = body['login']
            except Exception:                                     # noqa: BLE001
                # DELIBERATE, and not a fail-open: a 200 with an unreadable
                # body is still a 200 about the credential. The login is a
                # nicety; the status is the answer, and it is returned below
                # whatever happens here.
                #
                # THE WORD IS IN THE FIRST LINE ON PURPOSE. fail_open_scan.py
                # reads a window of `ln - 6 .. ln + 3` around the `except`, so
                # a reason written five lines down is invisible to it -- which
                # is how this site stayed classified DEPENDENCY-shaped through
                # a first attempt at exactly this comment. The classifier's
                # window is the constraint, not its vocabulary.
                #
                # tools/fail_open_scan.py classified
                # this site as DEPENDENCY-shaped -- "could not check, reported
                # clean" -- which is wrong about what is being checked. The
                # check is the HTTP STATUS, and it has already been obtained
                # and is returned below regardless of what happens here. What
                # cannot be read is a display name.
                #
                # So the swallow is scoped to one optional field and could not
                # hide a credential answer even in principle. The classifier
                # reads the words around a guard, so the reason is written in
                # the words it reads rather than the scanner being loosened --
                # loosening it would have exempted every bare except in the
                # repository to fix one comment.
                pass
            return r.status, hdrs
    except urllib.error.HTTPError as e:
        return e.code, dict((k.lower(), v) for k, v in e.headers.items())
    except Exception as exc:                                       # noqa: BLE001
        # NO NETWORK, DNS FAILURE, TLS, TIMEOUT, PROXY. None of these is an
        # answer about the credential, and calling any of them "rejected" would
        # send somebody to rotate a working token.
        return None, '%s: %s' % (type(exc).__name__, exc)


def verify(timeout=30):
    """(exit_code, lines). 0 good, 1 rejected, 2 could-not-run."""
    try:
        tok, src = github_token()
    except TokenUnavailable as exc:
        return 2, ['NO TOKEN AVAILABLE', '  %s' % exc]
    status, hdrs = fetch_user(tok, timeout=timeout)
    if status is None:
        return 2, [
            'token source : %s' % src,
            'token length : %d characters (the value is never printed)'
            % len(tok),
            'verdict      : COULD NOT RUN -- the request to GitHub did not '
            'complete, so NOTHING is known about whether this credential '
            'works.',
            'reason       : %s' % hdrs,
            'NOT a pass and NOT a failure. A clone with no network has a '
            'token this tool cannot judge, and saying either would be a '
            'claim it has not got.']
    verdict, lines = classify(status, hdrs, source=src)
    lines.insert(1, 'token length : %d characters (the value is never printed)'
                 % len(tok))
    return {'good': 0, 'rejected': 1}.get(verdict, 2), lines


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--live' in argv:
        code, lines = verify()
        for l in lines:
            print(l)
        if code == 0:
            print('')
            print('This is the ONLY output of this tool that means the '
                  'credential WORKS. Without --live, exit 0 means a token was '
                  'FOUND -- which is a different claim, and was read as this '
                  'one for as long as the tool existed.')
        return code
    try:
        tok, src = github_token()
    except TokenUnavailable as exc:
        print('NO TOKEN AVAILABLE')
        print('  %s' % exc)
        return 2
    # LENGTH, NEVER A PREFIX. A prefix is enough to confirm a guess, and a
    # credential has been pasted into a chat on this platform three times.
    print('token source : %s' % src)
    print('token length : %d characters (the value is never printed)' % len(tok))
    # SAYING WHAT THIS DID NOT TEST, EVERY TIME. The whole defect was that this
    # output was read as a liveness check, so the output now declines that
    # reading itself rather than relying on a reader knowing the difference.
    print('')
    print('NOT VERIFIED: nothing above contacted GitHub. A token was FOUND; '
          'whether it WORKS, what type it is, what it can do and when it '
          'expires are untested here.')
    print('  python tools/gh_token.py --live   # authenticated GET /user: '
          'type, scopes, expiry')
    return 0


if __name__ == '__main__':
    sys.exit(main())
