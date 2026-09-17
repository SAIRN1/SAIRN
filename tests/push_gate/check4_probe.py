"""Live-verify push-gate check 4 the same way checks 1-3 were verified:
a planted violation must BLOCK, a clean push must be ALLOWED.

Driven from Python so nothing depends on Bash command text, and every arm
asserts on the refusal REASON, not just the exit code -- three of tonight's
probe arms returned the right code for the wrong reason.
"""
# REQUIREMENT: push-gate check 4 blocks a planted violation and allows a clean
#   push, and every arm asserts on the refusal REASON rather than on the exit
#   code alone, because three probe arms once returned the right code for the
#   wrong reason
#
import atexit, subprocess, os, sys, re, tempfile

# ── RUN THIS, DO NOT IMPORT IT (2026-09-11) ────────────────────────────────
# This probe commits fixtures and mutates a source file. Since the worktree
# change below, it does both in a THROWAWAY WORKTREE rather than in the clone
# -- so an interrupted import no longer leaves a tracked file modified. What it
# does leave is a stray worktree and a half-finished push attempt, which is
# still worth refusing loudly.
#
# THE HISTORY IS KEPT BECAUSE IT IS WHY THE GUARD EXISTS. On 2026-09-11 a
# read-only checker walked tests/**/*_probe.py and imported each one to read its
# MUTATIONS list. It hung, was killed mid-probe, and left
# api/_lib/dental-guardian.js modified with an injected
# `if (r.zz_probe_field) return "probe";`. Found by `git status`, restored by
# hand, and the checker rewritten to PARSE rather than import.
if __name__ != '__main__':
    raise RuntimeError(
        __file__ + ' commits fixtures and pushes. Run it as a script; do not '
        'import it. To read its structure, parse it with ast -- see '
        'tools/mutation_anchor_check.py.')


MAIN = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
EP = 'api/legal-deadlines.js'

# ── THE FIXTURES ARE PLANTED IN A THROWAWAY WORKTREE (2026-09-11) ──────────
# This probe used to `git commit` its fixtures ONTO THE WORKING BRANCH and
# `git reset --mixed` back. That is safe for one runner on a quiet branch and
# was not safe here: when `run_all_tests.py --hook` fired on every Bash tool
# call, several copies ran at once, copy A reset to ITS OWN start while copy B's
# commit sat on the branch, and whoever pushed next published it.
#
# FIVE STRANDED `PROBE` COMMITS REACHED origin/main IN ONE DAY. One of them
# deleted `service_methods: body.service_methods,` from api/legal-deadlines.js
# -- the exact line whose absence made SAIRNlaw compute Florida answer deadlines
# five days late for five days. The fixture this probe plants deliberately, to
# prove the gate catches it, shipped to production because the RESET lost a
# race. `docs/2026-09-10-run-all-tests-hook-PAUSED.md` records the whole thing
# and names this file and check7_probe.py as needing exactly this treatment.
#
# A detached worktree has no branch tip to strand a commit on, and it is deleted
# at the end. Two consequences beyond the obvious one:
#
#   * THE CLEAN-TREE PRECONDITION IS GONE, deliberately. The old exit-3 guard
#     existed because `git add` here could sweep somebody's uncommitted work
#     into a probe commit. It cannot: the worktree is created from HEAD and
#     never contains the clone's uncommitted files. That guard had been
#     SKIPPING this probe on every run in any clone with a modified tracked
#     file -- verifying nothing about a BLOCKING gate -- so removing it is a
#     coverage gain, not a relaxation.
#   * The pre-push hook still fires. `core.hooksPath` is `.githooks` and
#     worktrees share the common git dir, so `git push --dry-run` from the
#     worktree runs the real gate. Measured before this was written, not
#     assumed: a planted seam violation blocked with the real refusal text.
#
# ── AND IT IS BUILT ON THE FETCHED REMOTE TIP, NOT ON LOCAL HEAD (2026-09-16) ─
# This said `HEAD`, and in a five-clone repo local HEAD is behind origin/main
# most of the time. The gate then refuses with "the outgoing range
# <remote>..<local> could not be read" -- CORRECTLY, because the remote tip is
# not an object this clone has yet -- and that refusal lands before check 4 is
# ever reached. Measured 2026-09-16: both arms exited 1 with every reason flag
# False, so the probe was failing while verifying nothing.
#
# Built on the fetched tip, the outgoing range is exactly the fixture commit,
# which is the range these arms are actually about.
_fetch = subprocess.run(['git', '-C', MAIN, 'fetch', '--quiet', 'origin', 'main'],
                        capture_output=True, text=True, encoding='utf-8', errors='replace')
if _fetch.returncode != 0:
    print('SKIPPED: could not fetch origin/main, so the fixture below could not be')
    print('built on the tip the gate compares against, and nothing about check 4')
    print('was verified: %s' % (_fetch.stderr or '').strip()[:200])
    sys.exit(3)
BASE = subprocess.run(['git', '-C', MAIN, 'rev-parse', 'FETCH_HEAD'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip()
WT = os.path.join(tempfile.gettempdir(), 'check4-probe-%d' % os.getpid())
_add = subprocess.run(['git', '-C', MAIN, 'worktree', 'add', '-q', '--detach',
                       WT, BASE], capture_output=True, text=True, encoding='utf-8', errors='replace')
if _add.returncode != 0:
    print('SKIPPED: could not create the throwaway worktree this probe needs, so')
    print('nothing about check 4 was verified: %s' % (_add.stderr or '').strip()[:200])
    sys.exit(3)


# ATEXIT RATHER THAN try/finally, because wrapping 120 lines of heavily
# commented arms in a try block would reindent all of it and make the diff
# unreadable. atexit runs on a normal exit, on sys.exit(), and after an
# unhandled exception; a hard kill skips it, exactly as the old reset did.
@atexit.register
def _remove_worktree():
    subprocess.run(['git', '-C', MAIN, 'worktree', 'remove', '--force', WT],
                   capture_output=True)
    subprocess.run(['git', '-C', MAIN, 'worktree', 'prune'], capture_output=True)


# Every git and filesystem operation below now happens in the worktree. The
# name is kept so the arms read unchanged.
REPO = WT


# ── THIS PROBE DECLARES ITSELF TO PUSH-GATE CHECK 8 (2026-09-10) ──────────
# Check 8 refuses a push carrying a commit whose subject starts with PROBE,
# because one of this file's own fixtures reached origin/main and shipped to
# production on 2026-09-09. This probe's pushes are `--dry-run` and publish
# nothing, so they are exempt -- but git hands a pre-push hook NO signal that a
# push is a dry run, so the exemption has to be declared rather than detected.
#
# It suppresses CHECK 8 ONLY. It is set here, in the probe that plants the
# fixture, and nowhere else. A real push that sets it is defeating a gate it had
# to go out of its way to defeat.
PROBE_ENV = dict(os.environ, SAIRN_PROBE_PUSH='1')


def run(*a, **k):
    return subprocess.run(list(a), cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
                          env=PROBE_ENV, **k)


def clean_tree():
    return run('git', 'status', '--porcelain').stdout.strip()


# ── THE CLEAN-TREE PRECONDITION IS GONE -- SEE THE WORKTREE BLOCK ABOVE ────
# Two earlier corrections lived here and both are now moot, but they are the
# reason the guard could be removed safely rather than hopefully, so the
# reasoning is kept: it existed because `git add` in the clone could sweep
# somebody's uncommitted work into a probe commit (2026-09-08, exit 3 rather
# than exit 1, because a precondition is not a failure), and it compared the
# WHOLE porcelain output so a single untracked file skipped the probe entirely
# (2026-09-09 -- one had been sitting in a clone since 2026-08-28, so this
# BLOCKING gate went unverified there on every run).
#
# The worktree removes the danger itself: it is created from HEAD and never
# contains the clone's uncommitted files, so there is nothing to sweep.
#
# WHAT THIS PROBE MUST STILL PROVE IS THAT IT LEFT THE CLONE ALONE, which is a
# stronger claim than the old one and is asserted at the bottom against these:
MAIN_TREE_BEFORE = subprocess.run(
    ['git', '-C', MAIN, 'status', '--porcelain'],
    capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
MAIN_HEAD_BEFORE = subprocess.run(
    ['git', '-C', MAIN, 'rev-parse', 'HEAD'],
    capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()

start = run('git', 'rev-parse', 'HEAD').stdout.strip()
# The untracked files that were here BEFORE this probe ran. The restore check at
# the bottom compares against this rather than against an empty tree.
START_UNTRACKED = {l for l in clean_tree().split('\n') if l.startswith('??')}
R = {}


# The gate's own words when it cannot compute what is being pushed. Matched
# rather than inferred from the exit code, because "could not tell" and "no" are
# different answers and this probe must not read one as the other.
RANGE_UNREADABLE = 'could not be read'


def dry_push():
    r = run('git', 'push', '--dry-run', 'origin', 'HEAD:main')
    err = r.stderr or ''
    # ── THE REMOTE TIP MOVES UNDER THIS PROBE, SO ONE RETRY AFTER A FETCH ────
    # Five clones push to this branch and a run takes a minute. When origin/main
    # advances between one arm and the next, the sha git hands the hook is an
    # object this clone does not have yet, and the gate refuses -- correctly --
    # before check 4 is reached. The fetch puts the new tip in the object store
    # the worktree shares and the range becomes the fixture commit again, since
    # BASE is an ancestor of the new tip. If it persists, `could_not_run` says
    # so rather than letting the arms report it as a check-4 failure.
    if r.returncode != 0 and RANGE_UNREADABLE in err:
        subprocess.run(['git', '-C', MAIN, 'fetch', '--quiet', 'origin', 'main'],
                       capture_output=True)
        r = run('git', 'push', '--dry-run', 'origin', 'HEAD:main')
        err = r.stderr or ''
    return {
        'exit': r.returncode,
        'could_not_run': r.returncode != 0 and RANGE_UNREADABLE in err,
        'blocked_by_seam': 'does not forward every input its engine reads' in err,
        'blocked_by_sql': 'no live schema snapshot' in err,
        'rejected_by_remote': 'fetch first' in err or 'rejected' in err,
        'names_field': 'service_methods' in err,
        # THE TEXT, NOT JUST THE FLAGS. Every flag above is a marker somebody
        # chose; when a refusal arrives that none of them names, the flags all
        # read False and the dict looks exactly like "nothing blocked it". That
        # is how this probe spent a day reporting a bare False for a push the
        # gate had stopped for a reason nobody could see from the output.
        'err': err.strip()[-400:],
    }


# ---- ARM 1: CLEAN api change must be allowed by check 4 ----
p = os.path.join(REPO, 'api', '_lib', 'zz_probe_clean.js')
open(p, 'w').write('// probe: a new lib nothing calls\nmodule.exports = {};\n')
run('git', 'add', 'api/_lib/zz_probe_clean.js')
run('git', 'commit', '-q', '-m', 'PROBE clean api change')
R['clean_api_change'] = dry_push()
run('git', 'reset', '--mixed', start)
os.remove(p)

# ── AND IT IS THE PRECONDITION, NOT ONLY AN ARM (2026-09-16) ───────────────
# If a CLEAN push cannot get through, then every later arm's refusal is
# attributable to whatever stopped this one and not to check 4. Asserting
# `blocked_by_seam` in that state produces a FAILURE REPORT ABOUT CHECK 4 on
# evidence that says nothing about check 4 -- the exact shape CLAUDE.md names:
# could-not-run is a third state and is never folded into either of the others.
# Exit 3, with the refusal text, so the runner records a SKIP rather than a red.
if R['clean_api_change']['exit'] != 0:
    print('SKIPPED: a CLEAN push is already being refused, so nothing below could')
    print('be attributed to check 4. Nothing about check 4 was verified.')
    print('  the refusal: %s' % R['clean_api_change']['err'])
    sys.exit(3)

# ---- ARM 2: PLANTED seam violation must block ----
path = os.path.join(REPO, EP)
src = open(path, encoding='utf-8').read()
# ── EXACTLY ONCE, NOT MERELY PRESENT (2026-09-10) ─────────────────────────
# `assert patched != src` catches an anchor that has DISAPPEARED and says
# nothing about one that now matches SEVERAL places -- re.sub(count=1) would
# quietly mutate whichever came first, and the arm would then be asserting
# something about a line nobody chose. That is not hypothetical: arm 15 of
# tests/sairndental_outbound_queue_probe.py went ambiguous the day a second
# SAIRNdental write branch landed with an identical header, and it only
# survived as a real guard because it counted.
#
# An anchor is a string match against code somebody else keeps editing, so
# going ambiguous is how it AGES rather than an accident.
#
# COUNTED WITHOUT THE SURROUNDING NEWLINES, and the first version of this line
# was vacuous for the one case that matters most. `\n...\n` cannot match two
# ADJACENT copies: the trailing newline of the first is the leading newline of
# the second, and re.findall does not return overlapping matches, so two
# identical lines in a row counted as ONE. A control that duplicated the line
# caught it -- the assertion was already the shape it exists to forbid.
_hits = len(re.findall(r'^\s*service_methods\s*:[^\n]*$', src, re.M))
assert _hits == 1, ('fixture invalid: the anchor matches %d places in %s, not 1 -- '
                    'widen it until it is unique rather than letting re.sub pick'
                    % (_hits, EP))
patched = re.sub(r'\n\s*service_methods\s*:[^\n]*\n', '\n', src, count=1)
assert patched != src, 'fixture invalid'
open(path, 'w', encoding='utf-8').write(patched)
run('git', 'add', EP)
run('git', 'commit', '-q', '-m', 'PROBE seam violation')
R['planted_violation'] = dry_push()
run('git', 'reset', '--mixed', start)
run('git', 'checkout', '--', EP)

# ── RESTORED MEANS "THIS PROBE LEFT NOTHING", NOT "THE TREE IS EMPTY" ──────
# Same defect as the guard at the top and found in the same run: this was
# `clean_tree() == ''`, so a pre-existing untracked file made the probe report
# NOT RESTORED and exit 1 -- a false failure about the probe's own cleanup,
# which is the loudest possible way to be wrong about residue in a repo that
# has spent a session learning to read residue correctly.
#
# What actually matters is that nothing THIS PROBE created or modified is still
# there. So: no modified tracked files, and the untracked set is exactly what it
# was before the probe started. That still catches a stranded fixture -- the
# thing the check exists for -- and stops blaming this probe for a file it never
# touched.
_after_untracked = {l for l in clean_tree().split('\n') if l.startswith('??')}
_after_tracked = [l for l in clean_tree().split('\n')
                  if l.strip() and not l.startswith('??')]
R['restored'] = (not _after_tracked and _after_untracked == START_UNTRACKED)
R['head_restored'] = (run('git', 'rev-parse', 'HEAD').stdout.strip() == start)

# ── AND THE CLONE ITSELF WAS NEVER TOUCHED (2026-09-11) ────────────────────
# The two checks above are about the WORKTREE, and they still matter: the arms
# depend on each reset landing, so a probe whose own cleanup is broken is a
# probe whose later arms measured the wrong tree. But neither of them is the
# claim that was actually violated when five PROBE commits reached origin/main.
# That claim is this one, and until now nothing asserted it.
R['clone_untouched'] = (
    subprocess.run(['git', '-C', MAIN, 'status', '--porcelain'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace').stdout == MAIN_TREE_BEFORE
    and subprocess.run(['git', '-C', MAIN, 'rev-parse', 'HEAD'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
    == MAIN_HEAD_BEFORE)

for k, v in R.items():
    print('%-20s %s' % (k, v))
print()

# COULD-NOT-RUN IS THE THIRD STATE AND IS NOT FOLDED INTO EITHER OTHER. If the
# gate never reached check 4 -- because the outgoing range was unreadable even
# after the retry -- then `blocked_by_seam: False` means "not asked", not "not
# blocked", and calling that a check-4 failure is a verdict on evidence that
# carries none.
_unattributable = [k for k, v in R.items()
                   if isinstance(v, dict) and v.get('could_not_run')]
if _unattributable:
    print('SKIPPED: the gate could not read the outgoing range for %s, so it never'
          % ', '.join(sorted(_unattributable)))
    print('reached check 4. Nothing about check 4 was verified.')
    print('  the refusal: %s' % R[_unattributable[0]]['err'])
    sys.exit(3)
ok = (R['planted_violation']['blocked_by_seam'] and R['planted_violation']['names_field']
      and not R['clean_api_change']['blocked_by_seam']
      and R['restored'] and R['head_restored'] and R['clone_untouched'])
print('CHECK 4 VERIFIED (planted blocks by seam + names the field, clean not blocked by seam):', ok)
sys.exit(0 if ok else 1)
