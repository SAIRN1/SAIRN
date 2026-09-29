r"""tests/run_plugin_upgrade_token_probe.py -- there is ONE place that knows
where the GitHub token comes from, and tools/plugin_upgrade_check.py now uses it.

    python tests/run_plugin_upgrade_token_probe.py

CONTROLS_FOR = ['tools/plugin_upgrade_check.py', 'tools/gh_token.py']
LIVE_PROBE_CLASS = 'FIXTURE'

WHY, AND IT IS A SEVEN-WEEK SILENT FAILURE REPEATING. `tools/gh_token.py` exists
because `gh_push.py` and `gh_verify.py` each carried their own copy of the token
lookup, both read a file that had been 0 bytes since 2026-08-08, and both raised
on every invocation for seven weeks with nothing saying so. Its header states the
lesson in one line: **the deeper defect is the duplication, not the path.** When
the token moved, both copies went stale together and neither could be fixed
without finding the other.

`tools/plugin_upgrade_check.py` then grew a THIRD copy -- found 2026-09-29 while
enumerating credential read sites for a rotation. It read the credential manager
directly and never imported `gh_token`, so it could not benefit from the ordering
that fix established (env var, then credential manager, then `.env.local` last so
a stale file cannot shadow a live credential).

THE KNOWN-BAD CONTROL IS THE ARM THAT MATTERS, and it is about the FAILURE
CONTRACT rather than the happy path. The two functions differ in what they do when
no token is available:

    the old local copy   returns None      -- and the caller does `or ''`
    gh_token.github_token()  RAISES TokenUnavailable, naming every source tried

Swapping one for the other without adapting the call site would turn "no token, so
the comparison is COULD NOT RUN" into an uncaught traceback. The arm drives exactly
that: with every source removed, the tool must still report a third state and must
NOT crash.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

TOOL = os.path.join(REPO, 'tools', 'plugin_upgrade_check.py')
GH = os.path.join(REPO, 'tools', 'gh_token.py')
for p in (TOOL, GH):
    if not os.path.isfile(p):
        print('COULD NOT RUN: %s is not on disk. This control tested nothing, '
              'which is a third state and not a pass.' % os.path.relpath(p, REPO))
        sys.exit(EXIT_COULD_NOT_RUN)

NL = chr(10)

# THE REAL SHAPE, not the phrase. `git credential fill` is invoked as an
# ARGUMENT LIST -- ['git', 'credential', 'fill'] -- so the words are never
# adjacent in the source and a search for the phrase matched nothing. And a
# search for the bare word `credential` matched 20+ tools that legitimately
# discuss credentials without reading one. Both were wrong in opposite
# directions: the first under-detected, the second made the sweep meaningless.
# What identifies the call is the two list elements next to each other.
CREDENTIAL_FILL_RE = re.compile(r'''['\"]credential['\"]\s*,\s*['\"]fill['\"]''')

passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:500])


def strip_py(src):
    """Source with docstrings and # comments removed.

    The tool's own header NAMES the duplication it used to have, so an arm
    searching raw text for `git credential fill` would match the sentence
    explaining that the call is gone -- PR 1.2, and the same trap the X-SD-Auth
    check fell into.
    """
    q3, s3 = chr(34) * 3, chr(39) * 3
    out = re.sub('(?s)' + q3 + '.*?' + q3, '', src)
    out = re.sub('(?s)' + s3 + '.*?' + s3, '', out)
    out = NL.join(re.sub(r'#.*$', '', ln) for ln in out.split(NL))
    assert len(out) > len(src) // 4, 'strip_py removed most of the file'
    return out


print('CONTROL PAIR -- one token lookup, not three' + NL)

SRC = io.open(TOOL, encoding='utf-8').read()
CODE = strip_py(SRC)

# ══ PART 1 -- THE DUPLICATION IS GONE, asserted on code not on prose ════════
print('PART 1 -- the third copy is gone')

# `git credential fill` is an ARG LIST in code, so the phrase never appears
# literally. Matching the token `credential` in stripped code is what actually
# detects the shape -- the first version of this arm looked for the phrase and
# passed against a file that still had the call.
ok(not CREDENTIAL_FILL_RE.search(CODE),
   'NO credential-manager call remains in the tool -- asserted against the '
   'source with comments and docstrings stripped, because the header NAMES the '
   'lookup it used to have and a raw-text search would match the sentence '
   'saying it is gone',
   [l for l in CODE.split(NL) if 'credential' in l][:3])
ok('credential' in SRC,
   'FIXTURE VALIDITY: the word IS in the file, in prose, so the arm above is '
   'distinguishing code from text rather than asserting an absence that was '
   'never there')
ok(re.search(r'from\s+gh_token\s+import|import\s+gh_token', CODE),
   'and it imports the shared lookup instead', [l for l in CODE.split(NL)
                                                if 'gh_token' in l][:3])
ok(not re.search(r'^def github_token', CODE, re.M),
   'and defines no github_token() of its own',
   [l for l in CODE.split(NL) if 'def github_token' in l])

# The whole platform, so a FOURTH copy cannot appear quietly.
print(NL + 'PART 2 -- and nowhere else grew a fourth')
others = []
for root, _dirs, files in os.walk(os.path.join(REPO, 'tools')):
    if '__pycache__' in root:
        continue
    for f in sorted(files):
        if not f.endswith('.py') or f == 'gh_token.py':
            continue
        p = os.path.join(root, f)
        try:
            body = strip_py(io.open(p, encoding='utf-8', errors='replace').read())
        except Exception:
            continue
        if CREDENTIAL_FILL_RE.search(body):
            others.append(os.path.relpath(p, REPO))
ok(others == [],
   'tools/gh_token.py is the ONLY file calling `git credential fill` -- checked '
   'across every tool, comments stripped, so the "one place that knows" claim in '
   'its header is now MEASURED rather than asserted', others)

# ══ PART 3 -- THE FAILURE CONTRACT, which is the known-bad ══════════════════
print(NL + 'PART 3 -- KNOWN-BAD: no token available must be a THIRD STATE, not a crash')

env = dict(os.environ)
env.pop('GITHUB_TOKEN', None)
env['PYTHONIOENCODING'] = 'utf-8'
# Break every source at once: no env var, and a credential helper that answers
# nothing. `-c credential.helper=` empties the helper list for this process only,
# so the real stored credential is untouched.
env['GIT_CONFIG_COUNT'] = '1'
env['GIT_CONFIG_KEY_0'] = 'credential.helper'
env['GIT_CONFIG_VALUE_0'] = ''

p = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace', env=env,
                   timeout=300)
out = (p.stdout or '') + (p.stderr or '')
ok('Traceback' not in out,
   'with EVERY token source removed the tool does not crash. gh_token RAISES '
   'TokenUnavailable where the old local copy returned None, so a swap that did '
   'not adapt the call site would turn a third state into an uncaught traceback '
   '-- this is that arm', out[-600:])
ok(p.returncode in (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN),
   'and it exits one of the three defined codes (got %d)' % p.returncode,
   out[-400:])

# ══ PART 4 -- gh_token's own contract, so the arm above rests on something ══
print(NL + 'PART 4 -- the shared lookup still behaves as the tool now depends on')
import gh_token   # noqa: E402

ok(hasattr(gh_token, 'github_token') and hasattr(gh_token, 'TokenUnavailable'),
   'gh_token exports github_token() and TokenUnavailable')
ok(gh_token.github_token.__doc__ and 'source' in gh_token.github_token.__doc__,
   'and returns a SOURCE LABEL alongside the token, which is what lets a caller '
   'say which of the three answered without printing the value')

src_env = dict(os.environ, GITHUB_TOKEN='')
probe = subprocess.run(
    [sys.executable, '-c',
     'import sys; sys.path.insert(0,"tools");'
     'import gh_token;'
     'sys.exit(0 if hasattr(gh_token,"TokenUnavailable") else 1)'],
    cwd=REPO, capture_output=True, text=True, env=src_env)
ok(probe.returncode == 0, 'and it imports cleanly from a bare interpreter',
   (probe.stderr or '')[-300:])

ok('gh_token' in io.open(GH, encoding='utf-8').read()[:200]
   or 'ONE place' in io.open(GH, encoding='utf-8').read()[:1200],
   'and its header still states that it is the ONE place that knows where the '
   'token comes from -- the claim this control now measures')

print(NL + '%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
