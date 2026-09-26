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


def main():
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
    return 0


if __name__ == '__main__':
    sys.exit(main())
