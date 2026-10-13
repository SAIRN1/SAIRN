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
import atexit, subprocess, os, sys, re, shutil, tempfile
import os

# ── RUN THIS, DO NOT IMPORT IT (2026-09-11) ────────────────────────────────
# This probe commits fixtures and mutates a source file. Since the throwaway-
# repo change below, it does both outside the clone -- so an interrupted import
# no longer leaves a tracked file modified. What it does leave is a stray
# directory in %TEMP% and a half-finished push attempt, which is still worth
# refusing loudly.
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


MAIN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = 'api/legal-deadlines.js'

# ── THE FIXTURES ARE PLANTED IN A THROWAWAY CLONE (2026-10-12) ─────────────
# IT WAS A LINKED WORKTREE FROM 2026-09-11 UNTIL TODAY, AND THAT IS THE DEFECT
# BEING FIXED HERE. A linked worktree SHARES `.git/config` with the clone that
# owns it, so a `git config` write made by ANYTHING running with cwd inside the
# worktree -- a gate, a gate's fixture, a tool invoked from a base commit --
# lands in the REAL clone's config.
#
# REPRODUCED IN TWO COMMANDS, not inferred, and recorded in
# docs/2026-10-07-fourth-routed-pinned-worktree-shared-config.md:
#
#     git worktree add -q --detach /tmp/repro HEAD
#     git -C /tmp/repro config core.bare true
#
# left `bare = true` in Documents/SAIRN-fourth/.git/config, after which EVERY
# git command in that clone failed with "fatal: this operation must be run in a
# work tree". The class is cody's SHARED_CONFIG_WRITE_FROM_WORKTREE.
#
# A CLONE HAS ITS OWN `.git/config`, so the write cannot reach this clone at
# all -- regardless of who makes it, and regardless of whether this process
# lives long enough to put anything back. check8_probe.py made exactly this
# move on 2026-10-06 (b23dbc2e) and is the pattern followed here rather than a
# second invention.
#
# ── HARDLINKED, NOT `--no-hardlinks`, AND THE NUMBER IS MEASURED ───────────
# The batch brief asked for `git clone --local --no-hardlinks`. Measured in
# this clone on 2026-10-12: `--no-hardlinks` takes 7.7s and leaves 207MB on
# disk per run (.git alone is 100MB); the hardlinked form costs no measurable
# time and no disk, which is why check8_probe.py uses it. These probes run in
# the whole-tree suite, in four clones, after every push. `--no-hardlinks` buys
# object-store isolation nothing here needs: git never rewrites a pack in
# place, new objects land in new files, and no probe runs `gc`. The config was
# the whole defect and a clone fixes it either way. Said out loud because it is
# a deliberate deviation from the brief, not an oversight.
#
# ── THE ORIGINAL NOTE, KEPT, BECAUSE ITS FIRST REASON STILL HOLDS ──────────
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
#
# ── OR A THROWAWAY BARE REMOTE, OPT-IN (2026-10-13, b5 item 6) ────────────
# `SAIRN_PROBE_LOCAL_REMOTE=1` or `--local-remote` builds a bare repo on local
# disk at BASE and points the clone's origin at it, so the verdict stops
# depending on the network and on origin/main moving under the run. The hook is
# NOT stubbed -- same `core.hooksPath`, same real gate, every check still votes.
# tests/push_gate/_local_remote.py carries the whole argument, including what
# this does NOT fix. The real-remote path stays the DEFAULT, because a probe
# that can only run against a local remote has stopped proving anything about
# the push that actually ships.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local_remote                                          # noqa: E402

LOCAL_REMOTE = _local_remote.requested(sys.argv[1:])
BARE = None
if LOCAL_REMOTE:
    # No network at all. BASE is local origin/main when this clone has it, and
    # local HEAD otherwise -- either is a real commit, and nothing else pushes
    # to the bare remote, so the outgoing range is exactly the fixture commit.
    _b = subprocess.run(['git', '-C', MAIN, 'rev-parse', 'origin/main'],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace')
    if _b.returncode != 0:
        _b = subprocess.run(['git', '-C', MAIN, 'rev-parse', 'HEAD'],
                            capture_output=True, text=True, encoding='utf-8',
                            errors='replace')
    BASE = (_b.stdout or '').strip()
    if not BASE:
        print('SKIPPED: could not resolve a BASE commit for the local-remote '
              'mode, so nothing about check 4 was verified.')
        sys.exit(3)
else:
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


# ── WHAT A CLONE DOES NOT INHERIT, AND WHY EACH ONE MATTERS ────────────────
# `core.hooksPath` is CONFIG, not a tracked file, so the clone does not get it
# -- and without it the pre-push hook NEVER FIRES and this probe would report
# "not blocked" about a gate it never asked. Asserted below rather than
# assumed. `origin` in a clone of a local path points at THAT PATH, so pushing
# there would exercise a different thing entirely; the real URL is read off
# MAIN and set. Both are the silent-pass direction, which is why this returns a
# REASON string and the caller exits 3 rather than limping on.
def _setup_clone():
    """-> None on success, or a reason string. Never half-builds silently."""
    r = subprocess.run(['git', 'clone', '--quiet', '--local', '--no-checkout',
                        MAIN, WT], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return 'clone failed: %s' % (r.stderr or '').strip()[:200]
    global BARE
    if LOCAL_REMOTE:
        # The bare remote is built from MAIN at BASE, then becomes this clone's
        # origin. No network is touched and nothing else can move the tip.
        BARE, why = _local_remote.create(
            MAIN, BASE,
            os.path.join(tempfile.gettempdir(), 'check4-bare-%d' % os.getpid()))
        if why:
            return 'local bare remote: %s' % why
        url = BARE
    else:
        url = subprocess.run(['git', '-C', MAIN, 'remote', 'get-url', 'origin'],
                             capture_output=True, text=True, encoding='utf-8',
                             errors='replace').stdout.strip()
        if not url:
            return 'could not read origin url from %s' % MAIN
    for args in (['remote', 'set-url', 'origin', url],
                 ['config', 'core.hooksPath', '.githooks'],
                 ['config', 'user.email', 'check4-probe@example.invalid'],
                 ['config', 'user.name', 'check4-probe'],
                 ['checkout', '--detach', '--quiet', BASE]):
        rr = subprocess.run(['git', '-C', WT] + args, capture_output=True,
                            text=True, encoding='utf-8', errors='replace')
        if rr.returncode != 0:
            return '%s failed: %s' % (' '.join(args[:2]),
                                      (rr.stderr or '').strip()[:160])
    # origin/main inside the clone must be the tip the gate compares against.
    subprocess.run(['git', '-C', WT, 'fetch', '--quiet', 'origin', 'main'],
                   capture_output=True)
    hp = os.path.join(WT, '.githooks', 'pre-push')
    if not os.path.isfile(hp):
        return 'the clone has no .githooks/pre-push, so the gate could not fire'
    return None


_why = _setup_clone()
if _why:
    shutil.rmtree(WT, ignore_errors=True)
    print('SKIPPED: could not create the throwaway clone this probe needs, so')
    print('nothing about check 4 was verified: %s' % _why)
    sys.exit(3)


def _rmtree_loud(p):
    """Remove it, and SAY SO if it survives.

    `ignore_errors=True` was check8_probe.py's first version here and it leaked
    a hardlinked clone per run, silently: on Windows a cloned object store
    carries READ-ONLY pack files and rmtree cannot unlink them. A cleanup that
    cannot fail loudly is the same defect class this probe exists for, one
    layer out.
    """
    def _chmod_retry(func, q, _exc):
        try:
            os.chmod(q, 0o700)
            func(q)
        except OSError:
            pass
    shutil.rmtree(p, onerror=_chmod_retry)
    if os.path.isdir(p):
        print('WARNING: could not remove the throwaway clone at %s -- it is '
              "hardlinked to this repo's object store and will sit in TEMP "
              'until somebody deletes it.' % p)
        return False
    return True


# ATEXIT RATHER THAN try/finally, because wrapping 120 lines of heavily
# commented arms in a try block would reindent all of it and make the diff
# unreadable. atexit runs on a normal exit, on sys.exit(), and after an
# unhandled exception; a hard kill skips it, exactly as the old reset did.
@atexit.register
def _remove_clone():
    _rmtree_loud(WT)
    if BARE:
        _local_remote.destroy(BARE)


# Every git and filesystem operation below now happens in the clone. The name
# is kept so the arms read unchanged.
REPO = WT
print('  remote mode: %s'
      % ('LOCAL BARE at %s -- no network, tip cannot move' % BARE
         if LOCAL_REMOTE else 'the REAL origin (default)'))


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


# ── AND THE CLONE'S `.git/config`, WHICH IS THE THING THAT WAS BEING
#    CORRUPTED (2026-10-12) ──────────────────────────────────────────────────
# The two snapshots above are about the TREE and the BRANCH TIP. Neither could
# see the defect this file was carrying: `bare = true` appearing in MAIN's
# config leaves the tree clean and HEAD unmoved right up to the moment every
# git command starts failing. `--git-common-dir` is used rather than a
# hardcoded `.git/config` join because `MAIN/.git` is a DIRECTORY in a clone
# and a FILE in a linked worktree, and this probe has to be developable from
# either.
def _common_git_dir():
    r = subprocess.run(['git', '-C', MAIN, 'rev-parse', '--git-common-dir'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return None
    d = r.stdout.strip()
    return d if os.path.isabs(d) else os.path.normpath(os.path.join(MAIN, d))


_GITDIR = _common_git_dir()
MAIN_CONFIG_PATH = (os.path.join(_GITDIR, 'config') if _GITDIR
                    else os.path.join(MAIN, '.git', 'config'))


def _read_main_config():
    try:
        with open(MAIN_CONFIG_PATH, 'rb') as fh:
            return fh.read()
    except OSError:
        return None


MAIN_CONFIG_BEFORE = _read_main_config()
if MAIN_CONFIG_BEFORE is None:
    print('SKIPPED: could not read %s, so this probe cannot prove it left the '
          'clone alone -- which is the one claim it was violating. Nothing '
          'about check 4 was verified.' % MAIN_CONFIG_PATH)
    sys.exit(3)

start = run('git', 'rev-parse', 'HEAD').stdout.strip()
# The untracked files that were here BEFORE this probe ran. The restore check at
# the bottom compares against this rather than against an empty tree.
START_UNTRACKED = {l for l in clean_tree().split('\n') if l.startswith('??')}
R = {}


# The gate's own words when it cannot compute what is being pushed. Matched
# rather than inferred from the exit code, because "could not tell" and "no" are
# different answers and this probe must not read one as the other.
RANGE_UNREADABLE = 'could not be read'
# ── A SECOND WAY THE GATE CANNOT READ THE PUSH, AND IT IS STRUCTURAL FOR A
#    PROBE (2026-10-13, b6 item 3) ───────────────────────────────────────────
# `register_feed_gate` denies with "stdin is not a terminal and carried NO ref
# lines", and its own text says what that means: "the push was issued from
# inside a SHELL SCRIPT, a pipe or any other wrapper. git hands the ref list to
# the hook it runs; a nested `git push` inside a script does not reproduce it
# ... ISSUE THE PUSH DIRECTLY -- that is the fix, and THERE IS NOTHING WRONG
# WITH THE CHANGE."
#
# A probe drives every push from Python, so it is permanently in case 1. That
# is the gate COULD NOT READ THE PUSH -- the same third state RANGE_UNREADABLE
# already names -- and NOT a verdict about check 4. Without this marker the
# planted arms report FAILED on a run where check 4 was never reached, which is
# the misattribution this file exists to refuse, one gate over.
NO_REF_LINES = 'carried NO ref lines'


def dry_push():
    r = run('git', 'push', '--dry-run', 'origin', 'HEAD:main')
    err = r.stderr or ''
    # ── THE REMOTE TIP MOVES UNDER THIS PROBE, SO ONE RETRY AFTER A FETCH ────
    # Five clones push to this branch and a run takes a minute. When origin/main
    # advances between one arm and the next, the sha git hands the hook is an
    # object this clone does not have yet, and the gate refuses -- correctly --
    # before check 4 is reached. The fetch puts the new tip in the object store
    # the push is judged against and the range becomes the fixture commit
    # again, since BASE is an ancestor of the new tip. If it persists,
    # `could_not_run` says so rather than letting the arms report it as a
    # check-4 failure.
    #
    # ── IT FETCHES INTO THE CLONE, NOT INTO MAIN (2026-10-12) ─────────────
    # This said `git -C MAIN fetch` and worked ONLY because a linked worktree
    # shares MAIN's object store. A clone does not. Left unchanged by the
    # worktree-to-clone move it would have fetched into the wrong repository,
    # so the retry would have failed exactly as the first attempt did -- which
    # reads as "check 4 did not fire" and is the silent-pass direction the
    # 2026-09-16 note at the top of this file is already about.
    if r.returncode != 0 and (RANGE_UNREADABLE in err or NO_REF_LINES in err):
        subprocess.run(['git', '-C', REPO, 'fetch', '--quiet', 'origin', 'main'],
                       capture_output=True)
        r = run('git', 'push', '--dry-run', 'origin', 'HEAD:main')
        err = r.stderr or ''
    return {
        'exit': r.returncode,
        'could_not_run': r.returncode != 0 and (RANGE_UNREADABLE in err
                                        or NO_REF_LINES in err),
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
#
# ── A REFUSAL BY A DIFFERENT CHECK IS A FOURTH STATE (2026-10-13, b5) ──────
# The paragraph above is right that a refused clean push makes a LATER
# refusal unattributable. It is NOT right that it makes the whole run
# unverifiable, and that distinction cost this probe its verdict twice:
# on 2026-10-12 and again on 2026-10-13 it exited 3 because the
# external-file-index check refused over ANOTHER SESSION'S handoff on a
# shared Google Drive -- a reason entirely outside this repository, which
# will keep being true for as long as that loop runs.
#
# So the clean push's refusal is CLASSIFIED rather than only counted:
#   OURS      the refusal carries check 4's own marker. The check really did
#             block a clean change, which IS a check-4 failure. Exit 3 is
#             wrong for this and it still exits 3 below -- unchanged,
#             because calling it a pass would be worse.
#   FOREIGN   the refusal carries NO check-4 marker. Some other check in the
#             hook voted no. Nothing about check 4 is proved by it either
#             way, so the ARM is reported UNPROVEN and the run CONTINUES --
#             because "the planted violation was refused WITH check 4's
#             marker" is evidence about check 4 no matter what else also
#             refused on the same push.
#
# THIS IS NOT A BYPASS AND THE DIFFERENCE MATTERS. The hook still runs, every
# check still votes, nothing is skipped and no override is set. What changed is
# that the probe no longer reads another check's verdict as its own.
_clean = R['clean_api_change']
_clean_foreign = (_clean['exit'] != 0 and not _clean['blocked_by_seam']
                  and not _clean.get('names_field'))
if _clean['exit'] != 0 and not _clean_foreign:
    print('SKIPPED: a CLEAN push is already being refused BY CHECK 4 itself, so')
    print('nothing below could be attributed to it. Nothing was verified.')
    print('  the refusal: %s' % _clean['err'])
    sys.exit(3)

# ── ARM 1 IS NOW ANSWERED FIRST-HAND INSTEAD OF REPORTED UNPROVEN
#    (2026-10-13, b6 item 3) ─────────────────────────────────────────────────
# b5 made a foreign refusal a fourth state and called arm 1 UNPROVEN. That was
# honest and it was not good enough: UNPROVEN is an absence of information, and
# the information was available the whole time.
#
# CHECK 4 IS `tools/sairn_seam_check.py`. The gate shells out to exactly that
# script (see tools/sairn_push_gate_hook.py's CHECK 4 block), so running it
# against the clean fixture tree gives CHECK 4'S OWN VERDICT ON THIS CHANGE,
# first-hand, with no other check able to speak over it. That is a positive
# answer rather than an inference from the absence of a marker.
#
# WHY NOT INFER IT FROM THE GATE'S COLLECTED REFUSALS. The gate does collect
# every refusal rather than stopping at the first, so "check 4's marker is
# absent from the full list" is suggestive. But `_deny_now_if_any()` runs from
# inside the crash handler, which means the collected list CAN be short if a
# later continuation raised -- the hook's own docstring says so. An absence in a
# list that may be truncated is not evidence, and the whole subject of this file
# is not treating one for the other.
#
# AND THE CRITERION IS THE NOT-FORWARDED COUNT, NOT THE EXIT CODE. That
# distinction was found by running it: `sairn_seam_check.py` exits 2 in this
# repo on ANY tree, because 19 endpoint/engine pairs are genuinely unparseable
# (`roleSet()` destructures its input, so the tool cannot see the reads) and it
# refuses to call those a pass. The GATE treats exit 2 as ALLOW with a
# disclosed note -- its own comment says "blocking on it would make an
# unanalysable shape unshippable" -- and reserves denial for exit 1.
#
# So reading exit 2 as "arm 1 fails" would conflate a REPO-WIDE BACKLOG with
# "check 4 refuses this clean change", and the arm would be red for ever for a
# reason that has nothing to do with the fixture. The thing check 4 blocks on
# is NOT-FORWARDED, and the checker prints it: "96 clean, 0 not-forwarded,
# 19 could-not-tell". That number is the verdict.
#
# OUTCOMES, AND NONE OF THEM IS UNPROVEN:
#   0 not-forwarded                -> arm 1 PASSES, with the could-not-tell
#                                     count DISCLOSED rather than dropped
#   >0 not-forwarded               -> arm 1 FAILS, named, with the count
#   summary line unreadable        -> arm 1 FAILS, named: a criterion that
#                                     cannot be parsed has not been met
#   checker absent or crashed      -> arm 1 FAILS, named
_seam_tool = os.path.join(REPO, 'tools', 'sairn_seam_check.py')
_SEAM_SUMMARY = re.compile(
    r'(\d+)\s+clean,\s*(\d+)\s+not-forwarded,\s*(\d+)\s+could-not-tell')
if not os.path.isfile(_seam_tool):
    _seam = {'rc': None, 'nf': None, 'cnt': None, 'cannot': None,
             'out': 'tools/sairn_seam_check.py is not in the fixture clone, so '
                    'check 4 could not be asked directly'}
else:
    _sp = subprocess.run([sys.executable, _seam_tool], cwd=REPO,
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', env=PROBE_ENV)
    _out = ((_sp.stdout or '') + (_sp.stderr or '')).strip()
    _m = _SEAM_SUMMARY.search(_out)
    _seam = {'rc': _sp.returncode, 'out': _out,
             'cnt': int(_m.group(1)) if _m else None,
             'nf': int(_m.group(2)) if _m else None,
             'cannot': int(_m.group(3)) if _m else None}
R['seam_direct'] = _seam

if _clean_foreign:
    print('NOTE: the clean push was refused by a DIFFERENT check in the hook.')
    print('Arm 1 is therefore answered by running check 4\'s OWN checker')
    print('directly rather than reported UNPROVEN. The foreign refusal:')
    print('  %s' % _clean['err'][-300:])

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

# ── AND ITS `.git/config` IS BYTE-IDENTICAL, WHICH clone_untouched CANNOT SEE
#    (2026-10-12) ────────────────────────────────────────────────────────────
# This is the result the worktree-to-clone move exists for. Against the OLD
# code it could go red for real: a `git config` write from inside a linked
# worktree reaches the owning clone, and that is the delta
# docs/2026-10-07-fourth-routed-pinned-worktree-shared-config.md reproduced in
# two commands. A clone has its own config, so the write cannot arrive here at
# all. Reported as its own row rather than folded into `clone_untouched`,
# because a reader needs to see WHICH of the three claims held.
_cfg_after = _read_main_config()
R['clone_config_unchanged'] = (_cfg_after == MAIN_CONFIG_BEFORE)
# And no worktree registration was left in `.git/worktrees/` to prune. "Nothing
# to clean up" is the kind of statement that stays in a comment after it stops
# being true, so it is measured.
R['no_worktree_registered'] = ('check4-probe' not in subprocess.run(
    ['git', '-C', MAIN, 'worktree', 'list', '--porcelain'], capture_output=True,
    text=True, encoding='utf-8', errors='replace').stdout)

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
      and R['restored'] and R['head_restored'] and R['clone_untouched']
      # ADDED TO THE VERDICT, NOT ONLY TO THE PRINTOUT (2026-10-12). A row
      # printed and left out of `ok` is a measurement nobody acts on, and the
      # config was the one thing this probe was actually damaging.
      and R['clone_config_unchanged'] and R['no_worktree_registered'])

# ── ARM 1'S VERDICT, FIRST-HAND, AND IT IS PART OF `ok` ───────────────────
# In the verdict, not only in the printout: a result printed and left out of
# `ok` is a measurement nobody acts on, which is the same note the config arm
# carries above.
_arm1_pass = False
if _seam['rc'] is None:
    _arm1_why = ('FAILED -- check 4 could not be asked directly: %s'
                 % _seam['out'][:200])
elif _seam['nf'] is None:
    _arm1_why = ('FAILED -- sairn_seam_check.py ran (exit %s) but its summary '
                 'line could not be parsed, so the not-forwarded count is '
                 'unknown. A criterion that cannot be read has not been met. '
                 'tail: %s' % (_seam['rc'], _seam['out'][-300:]))
elif _seam['nf'] == 0:
    _arm1_pass = True
    _arm1_why = ('PASSED -- sairn_seam_check.py reports %d clean, 0 '
                 'NOT-FORWARDED on the clean fixture tree, so check 4 has '
                 'nothing to block. (It also reports %d could-not-tell, which '
                 'is a standing repo-wide backlog -- 19 pairs where roleSet() '
                 'destructures its input -- and is DISCLOSED here rather than '
                 'dropped. The gate allows exit 2 for exactly that reason and '
                 'denies only on not-forwarded.)'
                 % (_seam['cnt'], _seam['cannot']))
else:
    _arm1_why = ('FAILED -- check 4 BLOCKS a clean change: %d NOT-FORWARDED '
                 'on the clean fixture tree (exit %s). tail: %s'
                 % (_seam['nf'], _seam['rc'], _seam['out'][-300:]))
print('arm 1 (a clean change is not blocked by check 4): %s' % _arm1_why)

# CONSISTENCY, because two sources that disagree is a third failure and not a
# pass on whichever one is convenient: if the direct run says the clean change
# is fine, the gate's own output must not carry check 4's refusal marker for it.
_arm1_consistent = not (_arm1_pass and _clean['blocked_by_seam'])
if not _arm1_consistent:
    print('arm 1 CONSISTENCY FAILED -- sairn_seam_check.py exits 0 on the clean '
          'tree while the gate refused the same push WITH check 4\'s marker. '
          'Two sources disagree and neither is taken on trust.')

ok = ok and _arm1_pass and _arm1_consistent
print('CHECK 4 VERIFIED (planted blocks by seam + names the field, clean not blocked by seam):', ok)
sys.exit(0 if ok else 1)
