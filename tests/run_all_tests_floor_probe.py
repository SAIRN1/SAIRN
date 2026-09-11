"""Does the shrinking-suite floor in tools/run_all_tests.py actually fire --
in BOTH copies, and does the pin still match reality?

WHY THIS EXISTS. The runner discovers its own subject by walking `tests/` and
`api/`, so it is the largest derived-subject guard on the platform: delete
twenty test files and it prints a true sentence -- "ALL 160 TEST FILES PASS" --
about a suite that just lost twenty guards. MIN_TEST_FILES is the pin that
makes the deletion visible. This probe is what keeps the pin honest.

IT WAS WRITTEN BECAUSE THE FIRST VERSION OF THAT PIN WAS WRONG IN TWO WAYS,
both found by reading rather than by any test, and both invisible from the
diff that added it:

  1. the floor was 163 while discover() returned 180, so seventeen test files
     could be deleted in silence -- a dead zone 85% the size of the twenty-file
     example the comment itself uses;
  2. the floor was added to `_main_body()` only. `_hook_body()` -- the copy
     that runs UNATTENDED after every push, in every clone -- never checked it.
     That is the half that mattered: a deletion you made yourself is in your
     own diff, and a deletion that arrives by REBASE from another clone is
     visible to nothing else.

Both are the same standing lesson CLAUDE.md records for sairn_claim_hook.py:
a fix verified on the copy a human invokes is not verified if a second copy
runs on its own.

A FLOOR AT BOTH ENDS -- MICHAEL'S DECISION, 2026-09-11. Arm 1 first shipped as
an EQUALITY, on the reasoning that a pin below the real count is an unmeasured
dead zone. It fired on the very first rebase after it was written -- 181 became
184 because other clones had added tests -- failing the suite for a session that
had added nothing. The call: **count >= pin, never an equality.** It keeps all
of the real protection, since any silent DELETION still fails immediately, and
drops the only false-positive shape, which was a legitimate ADDITION from
another clone. A stale floor after growth is cosmetic and gets bumped as
housekeeping; friction on every rebase is what gets a gate switched off out of
annoyance. Growth is still PRINTED with the number to write -- reported, not
enforced.

EVERY ARM IS MUTATION-PROVED. An arm that asserts a guard fires is worth
nothing unless the matching arm shows it stays quiet when it should -- a
`return 1` on every path would pass half of this file.

Exit 0 pass, 1 fail.
"""
import io
import json
import os
import sys
import contextlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import run_all_tests as R  # noqa: E402

fails = []


def check(cond, label):
    if cond:
        print('  ok   %s' % label)
    else:
        print('  FAIL %s' % label)
        fails.append(label)


def fake_run(js, py, quiet=True):
    """Every discovered file passes and none skips -- the green case.

    The floor has to be the ONLY thing that can speak in these arms, otherwise
    a fired guard cannot be told apart from an ordinary failure.
    """
    return [], []


@contextlib.contextmanager
def patched(count):
    """Make discover() return `count` files; restore whatever happens."""
    real_discover, real_run = R.discover, R._run
    js = ['tests/fake_%d.js' % i for i in range(count)]
    R.discover = lambda: (js, [], [])
    R._run = fake_run
    try:
        yield
    finally:
        R.discover, R._run = real_discover, real_run


def capture(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn()
    return rc, buf.getvalue()


print('1. THE REAL COUNT IS AT OR ABOVE THE PIN')
# ONE DIRECTION FAILS. Shrinkage is the defect and fails here; growth is
# reported with the number to write and passes. See the header for why this is
# not an equality -- it was one, for a few hours, and the cost landed on the
# first rebase.
#
# THE MUTATION PROOF FOR THIS ARM IS ARMS 2-6, not a line here. This comparison
# cannot be driven short without deleting real files; arms 2-6 patch discover()
# and prove the SAME constant makes both bodies fire and exit non-zero. What
# this arm adds on top of them is the case they cannot see: a pin written
# ABOVE the real count, which would false-alarm every run forever.
js, py, _ = R.discover()
real = len(js) + len(py)
if real > R.MIN_TEST_FILES:
    print('     NOTE the suite GREW: %d files discovered, MIN_TEST_FILES says '
          '%d.' % (real, R.MIN_TEST_FILES))
    print('     HOUSEKEEPING, NOT A FAILURE -- raise MIN_TEST_FILES to %d when '
          'you are next' % real)
    print('     editing this area. Until then %d test file(s) could be deleted '
          'with the' % (real - R.MIN_TEST_FILES))
    print('     guard silent, which is the accepted cost of not failing a '
          'session that added nothing.')
elif real < R.MIN_TEST_FILES:
    print('     the suite SHRANK: %d discovered, %d expected. Test files were '
          'deleted.' % (real, R.MIN_TEST_FILES))
check(real >= R.MIN_TEST_FILES,
      'discovered (%d) >= MIN_TEST_FILES (%d)' % (real, R.MIN_TEST_FILES))

print('')
print('2. _main_body() -- THE COPY A HUMAN RUNS')
with patched(R.MIN_TEST_FILES - 1):
    rc, out = capture(lambda: R._main_body(quiet=True))
check('THE SUITE HAS SHRUNK' in out, 'one file short: it says the suite shrank')
check(rc == 1, 'one file short: exit code is 1, not 0')
check('ALL %d TEST FILES PASS' % (R.MIN_TEST_FILES - 1) not in out,
      'one file short: it does NOT print ALL N TEST FILES PASS')
check('NOT ALL WELL' in out, 'one file short: the verdict line contradicts the green run')

print('')
print('3. _main_body() MUTATION PROOF -- quiet at the floor')
with patched(R.MIN_TEST_FILES):
    rc, out = capture(lambda: R._main_body(quiet=True))
check('THE SUITE HAS SHRUNK' not in out, 'exactly at the floor: no false alarm')
check(rc == 0, 'exactly at the floor: exit 0')
check('ALL %d TEST FILES PASS' % R.MIN_TEST_FILES in out,
      'exactly at the floor: the ordinary pass line is printed')

print('')
print('4. _main_body() MUTATION PROOF -- quiet ABOVE the floor')
# The runtime half is a FLOOR on purpose. If this arm ever fails, somebody
# turned it into an equality and every clone mid-addition now false-alarms.
with patched(R.MIN_TEST_FILES + 5):
    rc, out = capture(lambda: R._main_body(quiet=True))
check(rc == 0 and 'THE SUITE HAS SHRUNK' not in out,
      'five files above the floor: silent and exit 0')

print('')
print('5. _hook_body() -- THE COPY THAT RUNS UNATTENDED AFTER EVERY PUSH')
with patched(R.MIN_TEST_FILES - 1):
    rc, out = capture(R._hook_body)
check(out.strip() != '', 'one file short: the hook does not stay silent')
payload = {}
try:
    payload = json.loads(out)
except Exception as e:
    check(False, 'one file short: the hook emits parseable JSON (%s)' % e)
ctx = (payload.get('hookSpecificOutput') or {}).get('additionalContext', '')
head = payload.get('systemMessage', '')
check('SUITE HAS SHRUNK' in ctx, 'one file short: additionalContext names it')
# The headline is the only line guaranteed to be read. A reassuring
# "0 failing, 0 skipped" over a body that says guards vanished is the
# badge-beside-an-honest-field shape this repo keeps finding.
check('SHRUNK' in head, 'one file short: the HEADLINE carries it, not just the body')
check(rc == 0, 'one file short: the hook still exits 0 -- it reports, never blocks')

print('')
print('6. _hook_body() MUTATION PROOF -- silent on a clean green run')
with patched(R.MIN_TEST_FILES):
    rc, out = capture(R._hook_body)
check(out.strip() == '', 'exactly at the floor: the hook prints nothing at all')
check(rc == 0, 'exactly at the floor: exit 0')

print('')
print('7. THE TWO COPIES SHARE ONE CONSTANT')
# Not decoration. The defect this probe was written for was two copies of one
# idea with the check in only one of them; a second hardcoded number would
# recreate it in a form arms 2-6 would still pass.
#
# DECLARED, per CLAUDE.md's comment-quote rule: this arm reads the RAW source,
# comments included, on purpose. It is counting how many places DEFINE and
# COMPARE the constant, and a comment that reads like a second definition is a
# thing a human should be made to look at rather than something to strip away.
# The failure direction is loud and self-correcting -- an extra match fails a
# correct file, it never passes a broken one.
src = open(os.path.join(REPO, 'tools', 'run_all_tests.py'), encoding='utf-8').read()
check(src.count('MIN_TEST_FILES = ') == 1,
      'MIN_TEST_FILES is defined exactly once')
check(src.count('< MIN_TEST_FILES') == 2,
      'both bodies compare against it (found %d comparison(s))'
      % src.count('< MIN_TEST_FILES'))

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
