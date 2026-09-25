CONTROLS_FOR = ['tools/register_feed_gate.py']
#!/usr/bin/env python
"""tests/run_register_feed_gate_probe.py -- controls for
tools/register_feed_gate.py.

THIS GATE CAN FAIL IN TWO OPPOSITE WAYS AND BOTH ARE TESTED SEPARATELY.

  TOO QUIET  it stops asking, the register starves again, and every tool
             downstream reports a vacuous number -- the exact condition that
             was diagnosed FIVE times on 2026-09-15 before this was built.
  TOO LOUD   it refuses work that predates the rule, becomes a wall, and gets
             overridden -- which this repo already records costing more than a
             gate saves. 422 `fix(` commits touching code exist across history
             with no record; a gate without a requirement date would refuse
             essentially every push.

So the arms come in pairs: the rule bites AND the requirement date holds AND
the escape hatch works AND a bare escape is refused.

Exit 0 all arms passed, 1 otherwise.
"""

import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
SUBJECT = os.path.join(REPO, 'tools', 'register_feed_gate.py')

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('    ok   %s' % label)
    else:
        FAILS.append(label)
        print('    FAIL %s' % label)
        if detail:
            print('         %s' % str(detail)[:400])


import register_feed_gate as G   # noqa: E402

SHA = 'b' * 40


def verdict(subject, date, has_record, body=''):
    real = G.touches_code
    G.touches_code = lambda _s: ['api/x.js']
    try:
        owed, escaped, backlog = G.judge(
            [(SHA, date, subject, body)], {SHA[:8]} if has_record else set())
    finally:
        G.touches_code = real
    return ('owed' if owed else 'escaped' if escaped
            else 'backlog' if backlog else 'ok')


print('\nA. the rule bites')
ok('a fix after the date with NO record is OWED',
   verdict('fix(x): y', '2026-09-20', False) == 'owed')
ok('...and WITH a record it passes',
   verdict('fix(x): y', '2026-09-20', True) == 'ok')
ok('the subject prefix is what selects -- a feat is not a defect closure',
   verdict('feat(x): y', '2026-09-20', False) == 'ok')
ok('...nor is a chore', verdict('chore(x): y', '2026-09-20', False) == 'ok')

print('\nB. the requirement date holds -- it must not become a wall')
ok('a fix BEFORE the date is BACKLOG, never owed',
   verdict('fix(x): y', '2026-09-10', False) == 'backlog')
ok('...and the boundary day itself is INSIDE the rule',
   verdict('fix(x): y', G.REQUIREMENT_DATE, False) == 'owed')
ok('...while the day before is not',
   verdict('fix(x): y', '2026-09-15', False) == 'backlog')
# MOVING THE DATE FORWARD FORGIVES A GAP RATHER THAN CLOSING ONE. Pinned here
# as well as in the subject's own --self-check, because the subject's copy
# could be edited in the same breath as the constant.
ok('the requirement date is still the day this shipped',
   G.REQUIREMENT_DATE == '2026-09-16', G.REQUIREMENT_DATE)

print('\nC. the escape hatch, and the bare refusal it will not accept')
ok('a REAL no-defect-record reason is accepted',
   verdict('fix(x): y', '2026-09-20', False,
           'no-defect-record: a comment typo in a header; nothing shipped '
           'changed at all') == 'escaped')
ok('a BARE one is still OWED -- an escape with no note is a field that means '
   'nothing',
   verdict('fix(x): y', '2026-09-20', False, 'no-defect-record: typo') == 'owed')
_real = G.touches_code
G.touches_code = lambda _s: ['api/x.js']
try:
    _owed = G.judge([(SHA, '2026-09-20', 'fix(x): y',
                      'no-defect-record: typo')], set())[0]
finally:
    G.touches_code = _real
ok('...and the refusal SAYS how short it was',
   'characters of reason' in str(_owed), _owed)

print('\nD. scope, stated rather than silent')
real = G.touches_code
G.touches_code = lambda _s: []
try:
    o, e, b = G.judge([(SHA, '2026-09-20', 'fix(docs): wording', '')], set())
finally:
    G.touches_code = real
ok('a fix touching NO code path is not a defect closure', not (o or e or b))
G.touches_code = lambda _s: None
try:
    o2, _e, _b = G.judge([(SHA, '2026-09-20', 'fix(x): y', '')], set())
finally:
    G.touches_code = real
ok('a file list that CANNOT BE READ is OWED, not skipped -- could-not-tell is '
   'never folded into passed', bool(o2), o2)

print('\nE. which way it fails')
r = subprocess.run([sys.executable, SUBJECT, '--pre-push'], input='',
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO)
ok('no ref lines on stdin -> non-zero, never a silent pass', r.returncode != 0,
   r.returncode)
ok('...and it says it could not tell what is being pushed',
   'could not tell what is being pushed' in r.stdout, r.stdout[:300])

env = dict(os.environ, SAIRN_TEST_BAD_REGISTER='1')
import tempfile
TMP = tempfile.mkdtemp(prefix='rfg_')
try:
    broken = os.path.join(TMP, 'broken.py')
    src = io.open(SUBJECT, encoding='utf-8').read()
    ANCHOR = "REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')"
    ok('the register-path anchor is present', src.count(ANCHOR) == 1,
       'anchor stale -- the unreadable-register arm tests NOTHING')
    io.open(broken, 'w', encoding='utf-8').write(
        src.replace(ANCHOR, "REGISTER = os.path.join(REPO, 'docs', 'NO-SUCH-FILE.json')"))
    rb = subprocess.run([sys.executable, broken, '--pre-push'],
                        input='refs/heads/main aaa refs/heads/main bbb\n',
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', cwd=REPO,
                        env=dict(os.environ, PYTHONPATH=os.path.join(REPO, 'tools')))
    ok('AN UNREADABLE REGISTER DENIES THE PUSH -- a gate whose input is missing '
       'has checked nothing', rb.returncode != 0, rb.returncode)
    ok('...and says so rather than reporting a clean push',
       'checked NOTHING' in rb.stdout, rb.stdout[:300])
finally:
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the scratch directory is gone', not os.path.isdir(TMP))

print('\nF. it is actually wired, and the chain cannot eat stdin')
hook = io.open(os.path.join(REPO, '.githooks', 'pre-push'),
               encoding='utf-8').read()
ok('the hook invokes the gate', 'register_feed_gate.py' in hook)
ok('...and blocks on it rather than ignoring its status',
   'register_feed_gate.py" --pre-push || exit 1' in hook, hook[-500:])
# THE ARM THAT MATTERS MOST HERE. git feeds the ref lines on stdin and a stream
# is consumed by its first reader; a chain that read it twice would leave the
# EXISTING six-check gate with nothing, silently disabling it to add one.
ok('stdin is captured ONCE and replayed', hook.count('REFS=$(cat)') == 1, hook[-800:])
ok('...and every gate is fed from the capture, not from the stream',
   hook.count("printf '%s\\n' \"$REFS\" |") >= 3, hook[-800:])
# COMMENT LINES ARE EXCLUDED, because this file's own comment EXPLAINS the
# `| exec` trap and would otherwise fail the arm that checks for it -- a check
# defeated by its own documentation, which is the shape worth avoiding here of
# all places.
_hook_code = chr(10).join(l for l in hook.split(chr(10))
                          if not l.lstrip().startswith('#'))
ok('the last gate is NOT run under `| exec`, which would replace the subshell '
   'and lose the hook status', '| exec ' not in _hook_code, _hook_code[-400:])
ok('CONTROL: the pre-existing push gate is still invoked',
   'sairn_push_gate_hook.py" --pre-push' in hook, hook[-400:])

print('\nG. the subject passes its own rule table')
rg = subprocess.run([sys.executable, SUBJECT, '--self-check'],
                    capture_output=True, text=True, encoding='utf-8',
                    errors='replace', cwd=REPO)
ok('--self-check exits 0', rg.returncode == 0, rg.stdout[-300:])
# ── BOTH TABLES, AND THIS ARM WENT RED WHEN THE SECOND ONE ARRIVED ─────────
# It read `== len(G.CASES)` and the gate gained REUSE_CASES on 2026-09-16, so
# the arrow count became 14 against an expected 7. The arm was RIGHT to fail --
# that is what an "every case is driven" assertion is for -- and the fix is to
# name both tables rather than to loosen it to a floor. A THIRD table added
# without touching this line will fail here the same way, which is the property
# worth keeping.
ok('...over every case in BOTH rule tables',
   rg.stdout.count('-> ') == len(G.CASES) + len(G.REUSE_CASES),
   'arrows=%d cases=%d reuse=%d\n%s'
   % (rg.stdout.count('-> '), len(G.CASES), len(G.REUSE_CASES), rg.stdout[-300:]))


print('\nH. a STALE record is told apart from a MISSING one')
# Added 2026-09-16. The refusal used to say "no register record cites it" about
# a commit whose record exists and whose sha a rebase had moved, which sent four
# separate hand-repairs at a capability the register has always had.
#
# BOTH DIRECTIONS, because a pointer that appears on every refusal is noise and
# a pointer that never appears is the bug coming back. Driven through the real
# deny(), with no repository involved.
import contextlib                                                # noqa: E402
import io as _io                                                 # noqa: E402

_subs = G.cited_subjects()
ok('the register yields subjects to match against at all', bool(_subs), len(_subs))
if _subs:
    _known = next(iter(_subs))
    _buf = _io.StringIO()
    with contextlib.redirect_stdout(_buf):
        G.deny([('deadbeef', '2026-09-20', _known, 'no register record cites it')], [])
    _stale = _buf.getvalue()
    ok('a commit whose SUBJECT is already recorded names --reseat',
       '--reseat' in _stale, _stale[-300:])
    ok('...and says the record EXISTS rather than that it is missing',
       'ALREADY EXISTS' in _stale, _stale[-300:])
    ok('...and names the stale sha it is pointing at',
       _subs[_known] in _stale, _stale[-300:])

_buf = _io.StringIO()
with contextlib.redirect_stdout(_buf):
    G.deny([('deadbeef', '2026-09-20', 'fix(zz): a subject no record carries',
             'no register record cites it')], [])
_fresh = _buf.getvalue()
ok('CONTROL: a genuinely unrecorded commit does NOT name --reseat',
   '--reseat' not in _fresh, _fresh[-300:])
ok('...and is still told how to record it',
   '--add --commit' in _fresh, _fresh[-300:])


# ── A NEW BRANCH IS MEASURED FROM WHERE IT DIVERGED, NOT FROM THE ROOT ──────
# 2026-09-25. git sends an all-zero REMOTE sha for a branch that does not
# exist on the remote yet. outgoing_range() returned the bare LOCAL sha,
# which to `git log` means EVERYTHING REACHABLE -- so every unrecorded
# closure ever made on origin/main was reported as something the new branch
# was adding, and NO NEW BRANCH COULD BE PUSHED FROM ANY CLONE AT ALL. Found
# the day the register-freshness proposer needed to publish ten regfresh/*
# branches, because a propose-then-human-merge workflow is nothing but new
# branches.
ZERO = '0' * 40
_head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO,
                       capture_output=True, text=True).stdout.strip()
_base = subprocess.run(['git', 'merge-base', 'origin/main', 'HEAD'], cwd=REPO,
                       capture_output=True, text=True).stdout.strip()

_rng, _prob = G.outgoing_range('refs/heads/x %s refs/heads/x %s\n' % (_head, ZERO))
ok('a NEW branch resolves to a RANGE, never a bare tip -- a bare tip means '
   'all of history to git log',
   _prob == '' and (_rng is None or '..' in str(_rng)), (_rng, _prob))
if _rng is not None:
    ok('...and its base is the merge-base with origin/main, so the range is '
       'what this push ADDS',
       _rng == '%s..%s' % (_base, _head), (_rng, _base, _head))

_rng2, _prob2 = G.outgoing_range('refs/heads/x %s refs/heads/x %s\n'
                                 % (_head, 'a' * 40))
ok('CONTROL: an EXISTING remote branch is still rsha..lsha, unchanged',
   _rng2 == '%s..%s' % ('a' * 40, _head), _rng2)

_rng3, _prob3 = G.outgoing_range('refs/heads/x %s refs/heads/x %s\n'
                                 % (ZERO, 'b' * 40))
ok('CONTROL: a DELETE (all-zero LOCAL sha) is still nothing to check',
   _rng3 is None and _prob3 == '', (_rng3, _prob3))

_rng4, _prob4 = G.outgoing_range('refs/heads/x %s refs/heads/x %s\n'
                                 % (_base, ZERO))
ok('a new branch pointing AT the merge-base adds nothing and is not measured '
   'as if it did', _rng4 is None and _prob4 == '', (_rng4, _prob4))

# THE PAIRED REFUSAL: an unresolvable base is could-not-tell, never a range
# from the root -- the direction the original defect fell in.
_saved_mb = G._merge_base
try:
    G._merge_base = lambda a, b: None
    _rng5, _prob5 = G.outgoing_range('refs/heads/x %s refs/heads/x %s\n'
                                     % (_head, ZERO))
    ok('an UNRESOLVABLE base is could-not-tell WITH a reason, not a range '
       'from the root', _rng5 is None and 'could not be resolved' in _prob5,
       (_rng5, _prob5))
finally:
    G._merge_base = _saved_mb
ok('the probe restored the real merge-base resolver', G._merge_base is _saved_mb)

print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
