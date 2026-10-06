#!/usr/bin/env python
"""run_scrutiny_flag_probe.py -- the control on push-gate CHECK 15.

CHECK 15 flags a push that changes something which CHECKS the work: a test
file, CI/hook configuration, or push-gate logic. It never denies. This probe
proves the three things a non-blocking control can get wrong without anybody
noticing:

  A. IT FIRES on a planted WEAKENING, through the real gate, on a real git
     repository with a real `origin/main` -- not against the classifier
     functions, which `--scrutiny-selftest` already covers with 23 arms.
  B. IT DOES NOT FIRE on a push that touches nothing self-checking. A flag that
     appears on every push is a flag that gets ignored.
  C. IT NEVER DENIES. The gate must still allow in both arms, because a control
     that could block gate edits could not be installed.
  D. THE LEDGER RECEIVES THE FLAG, so a review obligation can pick it up -- and
     a second identical push does NOT duplicate it.
  E. TEETH: blind the classifier and A's finding must collapse.
  F. THE IMPORT FAILURE IS A THIRD STATE, not a silent pass -- the shape PR
     §1.11 is about.

WHY A TEMPORARY GIT REPOSITORY. The gate reads `outgoing_files(repo, base,
tip)` and diffs between two real commits. Faking that with stubs would test the
stubs. A scratch repo with one `origin` and two commits is the smallest thing
that exercises the wiring rather than the parts.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
ESA = os.path.join(REPO, 'tools', 'exit_status_attributable.py')

_fail = []


def ok(what, cond, detail=''):
    if cond:
        print('  ok   %s' % what)
    else:
        _fail.append(what)
        print('  FAIL %s%s' % (what, ('\n         [%s]' % detail) if detail
                               else ''))


def run(*args, **kw):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', **kw)


def git(wd, *args):
    return run('git', *args, cwd=wd)


def build_repo(weakening, gate_src=None):
    """A scratch repo with origin/main one commit behind HEAD.

    `weakening` is {path: (base_content, tip_content)}. The gate and the
    classifier are copied in under tools/, because CHECK 15 imports the
    classifier from the repo it is checking.
    """
    root = tempfile.mkdtemp(prefix='scrut_probe_')
    wd = os.path.join(root, 'work')
    bare = os.path.join(root, 'origin.git')
    os.makedirs(wd)
    run('git', 'init', '--bare', '-q', bare)
    git(wd, 'init', '-q', wd)
    git(wd, 'config', 'user.email', 'probe@example.invalid')
    git(wd, 'config', 'user.name', 'probe')
    git(wd, 'config', 'core.hooksPath', os.path.join(root, 'nohooks'))
    os.makedirs(os.path.join(wd, 'tools'))
    # ── THE sql/ DIRECTORY IS LOAD-BEARING AND IT IS NOT MINE ──────────────
    # `main()` opens with `if not repo or not os.path.isdir(repo + '/sql'):
    # sys.exit(0)`. WITHOUT THIS DIRECTORY THE ENTIRE GATE TURNS ITSELF OFF
    # AND PRINTS NOTHING -- all 15 checks, silently, exit 0. The first version
    # of this probe omitted it and 10 arms failed with no gate output at all,
    # which read exactly like "check 15 does not work". It works; the gate had
    # not started. Recorded here because the next person to write a gate probe
    # will lose the same hour otherwise, and routed as a finding in its own
    # right: that early exit predates check 15 and is wider than it looks.
    os.makedirs(os.path.join(wd, 'sql'))
    io.open(os.path.join(wd, 'sql', 'placeholder.json'), 'w',
            encoding='utf-8', newline='').write('{}\n')
    shutil.copy(gate_src or GATE, os.path.join(wd, 'tools',
                                               'sairn_push_gate_hook.py'))
    shutil.copy(ESA, os.path.join(wd, 'tools',
                                  'exit_status_attributable.py'))
    for p, (bodyA, _) in weakening.items():
        full = os.path.join(wd, p.replace('/', os.sep))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        io.open(full, 'w', encoding='utf-8', newline='').write(bodyA)
    git(wd, 'add', '-A')
    git(wd, 'commit', '-q', '-m', 'base')
    git(wd, 'remote', 'add', 'origin', bare)
    git(wd, 'push', '-q', 'origin', 'HEAD:refs/heads/main')
    git(wd, 'fetch', '-q', 'origin')
    for p, (_, bodyB) in weakening.items():
        full = os.path.join(wd, p.replace('/', os.sep))
        io.open(full, 'w', encoding='utf-8', newline='').write(bodyB)
    git(wd, 'add', '-A')
    git(wd, 'commit', '-q', '-m', 'tip')
    return root, wd


def drive(wd):
    """The gate in pretooluse mode, exactly as the PreToolUse hook calls it."""
    payload = json.dumps({'tool_name': 'Bash',
                          'tool_input': {'command': 'git push origin main'}})
    return run(sys.executable,
               os.path.join(wd, 'tools', 'sairn_push_gate_hook.py'),
               input=payload, cwd=wd)


WEAK_A = ('def test_x():\n    assert x == 1\n    assert y == 2\n'
          '    assert z == 3\n')
WEAK_B = 'def test_x():\n    pass\n'

print('A. a planted WEAKENING in a test file, through the real gate')
root, wd = build_repo({'tests/run_planted_probe.py': (WEAK_A, WEAK_B)})
try:
    r = drive(wd)
    ok('the gate ALLOWS -- exit 0, because this check must never deny',
       r.returncode == 0, 'exit=%d stderr=%s' % (r.returncode, r.stderr[-240:]))
    ok('EXTRA SCRUTINY appears in the gate output',
       'EXTRA SCRUTINY' in r.stderr, r.stderr[-400:])
    ok('...naming the planted file',
       'tests/run_planted_probe.py' in r.stderr, r.stderr[-400:])
    ok('...at level WEAKENING, not merely CHANGE',
       'WEAKENING' in r.stderr, r.stderr[-400:])
    ok('...and naming the SHAPE rather than a bare count',
       'assertions NET REMOVED' in r.stderr, r.stderr[-400:])
    ok('it says NOT A REFUSAL in its own words, so the reader cannot mistake '
       'it for a block', 'NOT A REFUSAL' in r.stderr, r.stderr[-400:])
    ok('and it states what it cannot see rather than implying coverage',
       'WHAT THIS CANNOT SEE' in r.stderr, r.stderr[-400:])

    print('\nD. the ledger receives it, and a re-push does not duplicate it')
    led = os.path.join(wd, 'docs', 'scrutiny-flags.json')
    ok('docs/scrutiny-flags.json was written', os.path.isfile(led))
    if os.path.isfile(led):
        d = json.load(io.open(led, encoding='utf-8'))
        ok('it carries a union-by-identity merge policy on (sha, path), the '
           'shape sairn_rebase_resolve.py already merges',
           d.get('merge_policy', {}).get('identity') == ['sha', 'path'],
           d.get('merge_policy'))
        ok('exactly one flag for the planted path', len(
            [f for f in d['flags']
             if f['path'] == 'tests/run_planted_probe.py']) == 1, d['flags'])
        ok('the flag records its own blind spots in the file, not only on '
           'screen', bool(d.get('blind_spots')), d.get('blind_spots'))
        drive(wd)
        d2 = json.load(io.open(led, encoding='utf-8'))
        ok('a SECOND identical push adds nothing -- keyed by commit, not by '
           'push attempt', len(d2['flags']) == len(d['flags']),
           '%d then %d' % (len(d['flags']), len(d2['flags'])))
finally:
    shutil.rmtree(root, ignore_errors=True)

print('\nB. CONTROL -- a push that touches nothing self-checking')
root, wd = build_repo({'stonedesk.html': ('<p>a</p>\n', '<p>b</p>\n')})
try:
    r = drive(wd)
    ok('the gate ALLOWS', r.returncode == 0,
       'exit=%d %s' % (r.returncode, r.stderr[-200:]))
    ok('NO scrutiny block is printed -- a flag on every push is a flag nobody '
       'reads', 'EXTRA SCRUTINY' not in r.stderr, r.stderr[-300:])
    ok('and NO ledger is created',
       not os.path.isfile(os.path.join(wd, 'docs', 'scrutiny-flags.json')))
finally:
    shutil.rmtree(root, ignore_errors=True)

print('\nC. a push-gate-logic edit flags itself')
root, wd = build_repo({'tools/sairn_push_gate_hook.py': (None, None)}
                      if False else
                      {'.githooks/pre-push': ('#!/bin/sh\nexit 0\n',
                                              '#!/bin/sh\n# relaxed\nexit 0\n')})
try:
    r = drive(wd)
    ok('a .githooks edit is flagged as CI / hook configuration',
       'CI / hook configuration' in r.stderr, r.stderr[-400:])
    ok('and the gate still ALLOWS', r.returncode == 0, 'exit=%d' % r.returncode)
finally:
    shutil.rmtree(root, ignore_errors=True)

print('\nE. teeth -- blind the classifier and A must collapse')
src = io.open(ESA, encoding='utf-8').read()
# ── BOTH ANCHORS ARE CHECKED FOR UNIQUENESS BEFORE EITHER IS MUTATED ────────
# Scrubber item 17: `str.replace` returns the string UNCHANGED when the anchor
# is absent, so an unguarded sabotage mutates nothing and the arm reports
# green forever. The first version of this arm guarded only the SECOND anchor.
# That would have been the loud direction here rather than the silent one --
# with the suffix path alone disabled, `tests/` still classifies through the
# prefix path and the flag still appears, so the arm would have gone red --
# but "it would have failed loudly" is not the rule. The rule is that a
# control asserts its own sabotage applied.
ANCHORS = ("        for pre in prefixes:", "    if p.endswith(TEST_SUFFIXES):")
for _a in ANCHORS:
    ok('sabotage anchor appears EXACTLY ONCE: %r' % _a.strip(),
       src.count(_a) == 1, src.count(_a))
blind = src.replace(ANCHORS[0], "        for pre in ():").replace(
    ANCHORS[1], "    if False:")
ok('and the blinded source really DIFFERS from the subject -- the mutation '
   'applied rather than silently no-opping', blind != src)
root = tempfile.mkdtemp(prefix='scrut_blind_')
try:
    bsrc = os.path.join(root, 'exit_status_attributable.py')
    io.open(bsrc, 'w', encoding='utf-8', newline='').write(blind)
    root2, wd = build_repo({'tests/run_planted_probe.py': (WEAK_A, WEAK_B)})
    try:
        shutil.copy(bsrc, os.path.join(wd, 'tools',
                                       'exit_status_attributable.py'))
        r = drive(wd)
        ok('the blinded classifier flags NOTHING -- so A really does come from '
           'the path classes and not from anywhere else',
           'EXTRA SCRUTINY' not in r.stderr, r.stderr[-300:])
        ok('and the gate still allows rather than crashing closed',
           r.returncode == 0, 'exit=%d' % r.returncode)
    finally:
        shutil.rmtree(root2, ignore_errors=True)
finally:
    shutil.rmtree(root, ignore_errors=True)

print('\nF. the import failure is a THIRD STATE, never a silent pass')
root, wd = build_repo({'tests/run_planted_probe.py': (WEAK_A, WEAK_B)})
try:
    os.remove(os.path.join(wd, 'tools', 'exit_status_attributable.py'))
    r = drive(wd)
    ok('the gate says COULD NOT RUN and names the import error',
       'EXTRA SCRUTINY: COULD NOT RUN' in r.stderr, r.stderr[-400:])
    ok('...and says in words that this is not a pass',
       'not a pass' in r.stderr, r.stderr[-400:])
    ok('...and still ALLOWS, because a missing classifier must not block '
       "somebody else's push", r.returncode == 0, 'exit=%d' % r.returncode)
finally:
    shutil.rmtree(root, ignore_errors=True)

print('')
if _fail:
    print('%d failure(s)' % len(_fail))
    for f in _fail:
        print('  - %s' % f)
    sys.exit(1)
print('ALL ARMS PASS')
sys.exit(0)
