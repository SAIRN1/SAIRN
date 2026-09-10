"""tools/criticality_tier_check.py must DENY, not just agree.

The register is clean today, and a gate whose findings are clean has by
construction never refused anything -- so nobody knows whether it can. Same
standard tests/push_gate/check7_probe.py and tools/discarded_verdict_check.py
were held to.

EVERY ARM MUTATES A COPY IN A THROWAWAY WORKTREE, never this clone. That is
deliberate rather than tidy: this repo spent a session establishing that a probe
which edits tracked files is indistinguishable from residue when it dies, and
the register is a file a reader would trust on sight.

Run: python tests/run_criticality_tier_probe.py
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
REL_DOC = os.path.join('docs', 'CRITICALITY-TIERS.md')
REL_TOOL = os.path.join('tools', 'criticality_tier_check.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run(wt):
    r = subprocess.run([sys.executable, os.path.join(wt, REL_TOOL)],
                       cwd=wt, capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('criticality tier register -- the checker must refuse a register that has '
      'stopped describing the platform\n')

wt = tempfile.mkdtemp(prefix='sairn-crit-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

DOC = os.path.join(wt, REL_DOC)
try:
    ORIGINAL = io.open(DOC, encoding='utf-8', newline='').read()

    # ── ARM 1: THE CONTROL, FIRST ──────────────────────────────────────────
    # So a refusal in any later arm cannot be confused with a checker that
    # refuses everything.
    rc, out = run(wt)
    check('the shipped register PASSES', rc == 0, out[-400:])
    check('...and it says how many verticals it saw', 'VERTICALS_ON_DISK:' in out)
    check('...and it does NOT claim the tiers are correct',
          'It does not say the tier is right' in out,
          'a checker that implies more reach than it has is worse than none')

    def mutate(new_text, label, expect_marker):
        io.open(DOC, 'w', encoding='utf-8', newline='').write(new_text)
        rc2, out2 = run(wt)
        check(label, rc2 == 1 and expect_marker in out2,
              'exit=%s marker=%s' % (rc2, expect_marker in out2))
        io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)

    # ── ARM 2: A VERTICAL WITH NO ROW ──────────────────────────────────────
    # The one that matters most in practice: a new app is added and nobody
    # states its worst case. It must not pass by simply not being mentioned.
    dropped = re.sub(r'^\| `sairnvet\.html`.*\n', '', ORIGINAL, count=1, flags=re.M)
    assert dropped != ORIGINAL, 'fixture invalid: the sairnvet row did not match'
    mutate(dropped, 'a vertical on disk with NO ROW is refused', 'NO TIER')

    # ── ARM 3: A ROW FOR SOMETHING THAT IS GONE ────────────────────────────
    ghost = ORIGINAL.replace(
        '| `sairnvet.html` |',
        '| `zz-no-such-app.html` | **A** | nothing | nothing |\n| `sairnvet.html` |', 1)
    mutate(ghost, 'a row naming a file that is NOT on disk is refused', 'GONE')

    # ── ARM 4: A TIER OUTSIDE THE VOCABULARY ───────────────────────────────
    # The scheme is A/B/C, taken from the SOUP register so the platform has one
    # scheme. A row inventing 'HIGH' or 'P1' is how a second scheme starts.
    badtier = ORIGINAL.replace('| `sairnvet.html` | **A** |',
                               '| `sairnvet.html` | **CRITICAL** |', 1)
    mutate(badtier, 'a tier outside A/B/C/UNTIERED is refused', 'BAD TIER')

    # ── ARM 5: A TIER WITH NOTHING TO CHECK IT AGAINST ─────────────────────
    # A tier with no evidence is a label. This is the arm that keeps the
    # register auditable rather than merely present.
    #
    # ANCHOR MOVED 2026-09-10, the second time in one day, and both moves are
    # the probe working rather than rotting. It pointed at `sairnscape.html`
    # while that row was **B**; measuring the eight B rows moved every one of
    # them to A and the fixture assertion failed loudly on the next run.
    #
    # It now points at `sairnlaw.html`, chosen because its A is backed by a
    # recorded incident rather than by a classification that could be revised --
    # the tier most likely to still be there next time. COUNTED, not merely
    # found, per the platform anchor sweep.
    EVIDENCE_ROW = r'^\| `sairnlaw\.html` \| \*\*A\*\* \| [^|]*\|[^|]*\|'
    _ne = len(re.findall(EVIDENCE_ROW, ORIGINAL, flags=re.M))
    assert _ne == 1, ('fixture invalid: the sairnlaw row matches %d places, not 1'
                      % _ne)
    noev = re.sub(r'(^\| `sairnlaw\.html` \| \*\*A\*\* \| [^|]*\|)[^|]*\|',
                  r'\1  |', ORIGINAL, count=1, flags=re.M)
    assert noev != ORIGINAL, 'fixture invalid: the sairnlaw row did not match'
    mutate(noev, 'a tier with an EMPTY evidence cell is refused', 'NO EVIDENCE')

    # ── ARM 6: AN OPEN QUESTION WITH NO WAY TO CLOSE IT ────────────────────
    # UNTIERED is allowed on purpose -- guessing is worse than an open question
    # -- but only if it says what would settle it. Otherwise it is a permanent
    # shrug that looks like a decision. This arm was written after the checker
    # caught exactly that in two rows of the register's own first draft.
    #
    # ANCHOR MOVED 2026-09-10 and the move is stated rather than quietly edited.
    # It pointed at `stonedesk-catalog.html`, which was UNTIERED until Michael's
    # tier-inheritance decision made it A. The fixture assertion caught that
    # LOUDLY on the next run -- which is the probe working, and is why the
    # assertion is there. It now points at `sairncash.html`, the one row that is
    # UNTIERED by design rather than by accident: it becomes A the day a Stripe
    # key is set. If that ever lands, move this again and add a line.
    #
    # COUNTED, NOT MERELY PRESENT, per the platform anchor sweep: `!= ORIGINAL`
    # catches an anchor that has GONE and says nothing about one matching
    # several places, where re.sub(count=1) would rewrite whichever came first.
    UNTIERED_ROW = r'^\| `sairncash\.html` \| \*\*UNTIERED\*\* \| [^|]*\|[^|]*\|'
    _n = len(re.findall(UNTIERED_ROW, ORIGINAL, flags=re.M))
    assert _n == 1, ('fixture invalid: the sairncash UNTIERED row matches %d places, '
                     'not 1 -- widen the anchor rather than letting re.sub pick' % _n)
    shrug = re.sub(r'(^\| `sairncash\.html` \| \*\*UNTIERED\*\* \| [^|]*\|)[^|]*\|',
                   r'\1 nothing moves today |', ORIGINAL, count=1, flags=re.M)
    assert shrug != ORIGINAL, 'fixture invalid: the sairncash row did not match'
    mutate(shrug, 'an UNTIERED row that does not say what would SETTLE it is refused',
           'OPEN WITH NO EXIT')

    # ── ARM 7: THE DECLARED NON-VERTICAL IS NAMED, NOT FILTERED ────────────
    # A checker that silently skipped piac.html would hide that something
    # non-app is sitting in the app directory.
    #
    # THE FILE IS CREATED HERE RATHER THAN ASSUMED, and the first version of
    # this arm failed because of it: piac.html is UNTRACKED, so a fresh
    # worktree does not have it and the arm was measuring the environment
    # instead of the logic. A clean checkout genuinely has 22 verticals and no
    # exclusion to report -- which is correct, and is why the exclusion has to
    # be provoked to be tested.
    io.open(os.path.join(wt, 'piac.html'), 'w', encoding='utf-8').write('<!-- probe -->')
    try:
        rc7, out7 = run(wt)
        check('the declared non-vertical is REPORTED rather than silently skipped',
              'EXCLUDED' in out7 and 'piac.html' in out7, out7[:300])
        check('...and it does not count as a missing tier',
              'NO TIER    piac.html' not in out7 and rc7 == 0, out7[:300])
    finally:
        os.remove(os.path.join(wt, 'piac.html'))

    check('the register was restored byte for byte after every arm',
          io.open(DOC, encoding='utf-8', newline='').read() == ORIGINAL)
finally:
    subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                   capture_output=True, text=True)
    shutil.rmtree(wt, ignore_errors=True)

# NOTHING IN THIS CLONE MAY HAVE MOVED. The worktree is the point; this asserts
# it rather than trusting it.
here = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', REL_DOC],
                      capture_output=True, text=True).stdout.strip()
check('this clone\'s own register is untouched', here == '', here)

print('\n%s  run_criticality_tier_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
