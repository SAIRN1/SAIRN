#!/usr/bin/env python
# REQUIREMENT: tools/deploy_verify_notify.py must decide whether a Bash command
#   pushed from what the command DOES, not from whether its text contains the
#   literal "git push" -- it silently skipped every push driven through
#   tools/push_retry.py, which is the path a session is told to use when the
#   branch is contended
#
# Run: python tests/run_deploy_verify_entry_probe.py
#
# ── THE MEASURED GAP ──────────────────────────────────────────────────────
# The old entry condition was one substring:
#
#     if "git push" not in cmd: sys.exit(0)
#
# tools/push_retry.py pushes at line 610 through subprocess, so the Bash
# command string is `python tools/push_retry.py --loop` and that substring is
# absent. The post-push deploy check never ran for it, and said nothing when
# it skipped. The file's own header had recorded the same blind spot for
# sairn_claim.py and had not named push_retry.py -- which is the one that
# matters, because contention is the normal case with five clones.
#
# BOTH DIRECTIONS, and a third verdict. A classifier that answers "push" to
# everything would make the hook fire on every command; one that answers
# "not-a-push" to everything restores the original defect. And an unrecognised
# push-shaped command must be UNSURE, never a silent skip.

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import deploy_verify_notify as D  # noqa: E402

CASES = [
    # --- must be recognised as a push --------------------------------------
    ('git push',                                   'push'),
    ('git push origin main',                       'push'),
    ('git push --force-with-lease',                'push'),
    ('git -c foo=bar push',                        'push'),
    ('cd /repo && git push',                       'push'),
    ('git add -A; git commit -q -m x; git push',   'push'),
    # THE REGRESSION THIS FILE EXISTS FOR
    ('python tools/push_retry.py --loop',          'push'),
    ('PYTHONIOENCODING=utf-8 python tools/push_retry.py --loop --attempts 6', 'push'),
    ('python tools/sairn_claim.py claim app "x"',  'push'),
    ('python tools/register_freshness_propose.py', 'push'),

    # --- must NOT be treated as a push -------------------------------------
    ('git status --short',                         'not-a-push'),
    ('ls tools/',                                  'not-a-push'),
    ('node tests/foo.js',                          'not-a-push'),
    ('',                                           'not-a-push'),
    # A command that only TALKS about pushing. A sibling hook refused the very
    # commit documenting this defect because its message body said "git push".
    ('echo "run git push later"',                  'not-a-push'),
    ('# git push goes here',                       'not-a-push'),

    # --- must be UNSURE, not silently dropped ------------------------------
    ('python tools/some_new_pusher.py',            'unsure'),
    ('./scripts/deploy-and-push.sh',               'unsure'),
]

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name
          + (('\n       ' + detail) if not cond and detail else ''))


print('deploy_verify_notify entry condition -- what counts as a push\n')
for cmd, want in CASES:
    got = D.classify_command(cmd)
    check('%-10s <- %s' % (want, (cmd[:62] or '<empty>')),
          got == want, 'got %r' % got)

print('\ncontrols')
# A classifier that answers the same thing to everything passes no real test.
verdicts = set(D.classify_command(c) for c, _w in CASES)
check('C1. the fixture set reaches all three verdicts',
      verdicts == {'push', 'not-a-push', 'unsure'},
      'only reached: %s' % sorted(verdicts))
check('C2. PUSHING_TOOLS is non-empty and names push_retry.py -- the entry '
      'the old condition missed',
      'push_retry.py' in D.PUSHING_TOOLS,
      'PUSHING_TOOLS = %r' % (D.PUSHING_TOOLS,))
# The list is hand-maintained, so prove each named tool really does push.
missing = []
for tool in D.PUSHING_TOOLS:
    p = os.path.join(REPO, 'tools', tool)
    if not os.path.isfile(p):
        missing.append(tool + ' (no such file)')
        continue
    src = open(p, encoding='utf-8', errors='replace').read()
    if "'push'" not in src and '"push"' not in src:
        missing.append(tool + ' (no git push call found)')
check('C3. every tool in PUSHING_TOOLS actually runs a push -- a stale name '
      'here is a push the hook would claim to cover and does not',
      not missing, '; '.join(missing))

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
