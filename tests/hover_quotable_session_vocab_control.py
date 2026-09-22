"""Control on tests/hover_quotable_session_vocab_check.py.

    python tests/hover_quotable_session_vocab_control.py

THE CHECKER'S WHOLE VALUE IS THAT IT FINDS A SESSION QUOTABLE HAS NEVER HEARD
OF, and exit 0 on the real tree proves nothing about that -- the tree is clean,
so exit 0 is also what a checker that read the wrong file, matched the wrong
anchor, or parsed to an empty set would print. Every arm here runs it against a
SYNTHETIC tree where the answer is known, in both directions.

CONTROLS_FOR is DECLARED rather than inferred, because three inference models
were each wrong within an hour of being written elsewhere in this repo.

THE ARMS RUN THE CHECKER IN A THROWAWAY DIRECTORY, never against this clone.
This repo established that a probe which edits tracked files is
indistinguishable from residue when it dies, and `tools/hover_separation_audit.py`
is a file a reader would trust on sight.

THIS CONTROL FOUND A DEFECT IN THE CHECK BEFORE THE CHECK SHIPPED, and the
sentence that used to sit here is the record of it. It read: *"ONE THING THIS
CONTROL CANNOT DO -- the checker reads two machine-local sources that a
synthetic tree cannot move."* True when written, and it meant arms 1, 3 and 7
went red on the first run because the synthetic tree inherited this
workstation's real `hover2`. Three arms failing for a reason unrelated to the
property they guard is the state this repo's own probes have a comment about:
it teaches a reader to expect red and stop reading.

The fix was in the CHECK, not here -- `SAIRN_STATUS_DIR` and
`SAIRN_CLONES_GLOB`, the same mechanism `SAIRN_TIER_REGISTER` provides on
`tools/criticality_tier_check.py` and for the same stated reason. A checker
that cannot be pointed at a known answer cannot be driven, and one that cannot
be driven has never been shown to refuse anything.

So every arm now switches both machine-local sources off and drives the
in-repo one, `.claude/claims/*.json` -- the weakest of the three and the only
portable one, which is the right one to hold a control to.
"""
CONTROLS_FOR = ['hover_quotable_session_vocab_check.py']

import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
REL_CHECK = os.path.join('tests', 'hover_quotable_session_vocab_check.py')
REL_AUDIT = os.path.join('tools', 'hover_separation_audit.py')

FAILURES = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        FAILURES.append(name)


def build_tree(quotable_names, claim_names):
    """A minimal tree the checker can read: the audit literal and a claims dir."""
    d = tempfile.mkdtemp(prefix='sairn-quotable-')
    os.makedirs(os.path.join(d, 'tools'))
    os.makedirs(os.path.join(d, 'tests'))
    os.makedirs(os.path.join(d, '.claude', 'claims'))
    shutil.copy(os.path.join(REPO, REL_CHECK), os.path.join(d, REL_CHECK))
    body = 'QUOTABLE = (%s)\n' % ', '.join("'%s'" % n for n in quotable_names)
    io.open(os.path.join(d, REL_AUDIT), 'w', encoding='utf-8').write(body)
    for n in claim_names:
        io.open(os.path.join(d, '.claude', 'claims', n + '.json'), 'w',
                encoding='utf-8').write('{}')
    return d


def run(tree):
    # THE TWO MACHINE-LOCAL SOURCES ARE SWITCHED OFF FOR EVERY ARM. Without
    # this the synthetic tree inherits the REAL workstation's sessions and
    # three arms go red for a reason unrelated to the property they guard --
    # which is exactly what happened on the first run, and is why the check
    # gained the overrides at all.
    env = dict(os.environ, SAIRN_STATUS_DIR='', SAIRN_CLONES_GLOB='')
    r = subprocess.run([sys.executable, os.path.join(tree, REL_CHECK)],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=tree, env=env)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('control on the QUOTABLE session-vocabulary check\n')
trees = []
try:
    # ── ARM 1: THE CONTROL, FIRST, so a refusal later cannot be confused with
    #    a checker that refuses everything.
    t = build_tree(['hank', 'cc', 'cody', 'fourth', 'hover'],
                   ['hank', 'cc', 'cody', 'fourth', 'hover'])
    trees.append(t)
    rc, out = run(t)
    check('1. a complete QUOTABLE PASSES', rc == 0, 'exit=%s\n%s' % (rc, out[-400:]))

    # ── ARM 2: THE ONE THIS EXISTS FOR ──────────────────────────────────
    # A sixth clone appears and QUOTABLE has never heard of it. On the real
    # tree this is invisible: quote_attribution() returns `none`, the citation
    # is reported as DISPUTED, and nothing fails.
    t = build_tree(['hank', 'cc', 'cody', 'fourth', 'hover'],
                   ['hank', 'cc', 'cody', 'fourth', 'hover', 'hover3'])
    trees.append(t)
    rc, out = run(t)
    check('2. a session MISSING from QUOTABLE is REFUSED, and named',
          rc == 1 and 'hover3' in out, 'exit=%s\n%s' % (rc, out[-500:]))

    # ── ARM 3: THE REVERSE DIRECTION IS DELIBERATELY NOT CHECKED ────────
    # `ted`, `hover1` and `michael` are legitimately in QUOTABLE and are not
    # clones. If this arm ever goes red somebody has added a reverse check and
    # it will report all three as phantoms on the real tree.
    t = build_tree(['hank', 'cc', 'cody', 'fourth', 'hover', 'ted', 'michael'],
                   ['hank', 'cc', 'cody', 'fourth', 'hover'])
    trees.append(t)
    rc, out = run(t)
    check('3. an EXTRA name in QUOTABLE is NOT a finding -- the check is '
          'one-directional on purpose', rc == 0,
          'a reverse check would report ted/hover1/michael as phantoms on the '
          'real tree:\nexit=%s\n%s' % (rc, out[-400:]))

    # ── ARM 4: A BROKEN ANCHOR IS COULD-NOT-TELL, NEVER A PASS ──────────
    # The failure this check was written against, arriving from the other
    # direction: the literal is renamed and the checker silently examines
    # nothing. Exit 2, not 0.
    t = build_tree(['hank'], ['hank'])
    trees.append(t)
    io.open(os.path.join(t, REL_AUDIT), 'w', encoding='utf-8').write(
        'SPEAKERS = (\'hank\',)\n')
    rc, out = run(t)
    check('4. a RENAMED literal is COULD NOT TELL (exit 2), not a pass',
          rc == 2 and 'COULD NOT TELL' in out, 'exit=%s\n%s' % (rc, out[-400:]))

    # ── ARM 5: AN EMPTY LITERAL IS COULD-NOT-TELL, NOT "EVERYTHING MISSING"
    # An empty QUOTABLE would make every session look missing -- a finding the
    # checker would have INVENTED rather than found, and a loud wrong answer
    # trains people to distrust the quiet right ones.
    t = build_tree([], ['hank', 'cc'])
    trees.append(t)
    rc, out = run(t)
    check('5. an EMPTY QUOTABLE is COULD NOT TELL, not five findings',
          rc == 2 and 'EMPTY' in out.upper(), 'exit=%s\n%s' % (rc, out[-400:]))

    # ── ARM 6: THE SOURCE COUNT IS REPORTED, so "OK" cannot overclaim ───
    # In a synthetic tree the two machine-local sources may or may not exist on
    # the running machine. What must always be true is that the run SAYS how
    # many it read, because a clean result from one source is a narrower claim
    # than a clean result from three.
    t = build_tree(['hank'], ['hank'])
    trees.append(t)
    rc, out = run(t)
    check('6. the run states how many of the 3 sources it could read',
          'of 3 sources' in out, out[-400:])

    # ── ARM 7: THE PAIRED POSITIVE ON ARM 2 ─────────────────────────────
    # Arm 2 alone is satisfied by a checker that refuses every tree. Adding the
    # missing name must make the SAME tree pass.
    t = build_tree(['hank', 'cc', 'cody', 'fourth', 'hover', 'hover3'],
                   ['hank', 'cc', 'cody', 'fourth', 'hover', 'hover3'])
    trees.append(t)
    rc, out = run(t)
    check('7. THE PAIRED POSITIVE: naming the new session makes arm 2\'s tree '
          'pass, so arm 2 is not a checker that refuses everything', rc == 0,
          'exit=%s\n%s' % (rc, out[-400:]))
finally:
    for t in trees:
        shutil.rmtree(t, ignore_errors=True)

here = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', REL_AUDIT],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip()
check('this clone\'s own audit tool is untouched', here == '', here)

print('\n%d failure(s)' % len(FAILURES))
for f in FAILURES:
    print('  - ' + f)
sys.exit(1 if FAILURES else 0)
