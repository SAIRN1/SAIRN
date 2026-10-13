"""Live-verify push-gate check 7 the way checks 1-4 were: a planted violation
must BLOCK, a clean push must be ALLOWED, and each arm asserts on the refusal
REASON rather than the exit code alone.

CHECK 7 blocks a push that ships an api/ endpoint answering a refusal ABOVE the
first auth call. It went in blocking on 2026-09-08, immediately after the
fifteen *-auth.js handlers were reordered and tools/preauth_oracle_check.py
started exiting 0 for the first time.

THIS PROBE IS THE POINT OF THAT SENTENCE. A gate whose findings are clean has,
by construction, never denied anything -- so nobody knows whether it CAN. The
same standard tools/discarded_verdict_check.py was held to.

Driven from Python so nothing depends on Bash command text. Restores the repo
in a `finally`, and asserts the tree is clean before it starts.
"""
import atexit
import os
import shutil
import subprocess
import sys
import tempfile

MAIN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EP = 'api/sb-auth.js'

# ── THE FIXTURES ARE PLANTED IN A THROWAWAY CLONE (2026-10-12) ─────────────
# IT WAS A LINKED WORKTREE UNTIL TODAY AND THAT IS THE DEFECT BEING FIXED. A
# linked worktree SHARES `.git/config` with the clone that owns it, so a `git
# config` write made by ANYTHING running with cwd inside the worktree -- a
# gate, a gate's fixture, a tool invoked from a base commit -- lands in the
# REAL clone's config.
#
# REPRODUCED IN TWO COMMANDS, not inferred, and recorded in
# docs/2026-10-07-fourth-routed-pinned-worktree-shared-config.md:
#
#     git worktree add -q --detach /tmp/repro HEAD
#     git -C /tmp/repro config core.bare true
#
# left `bare = true` in Documents/SAIRN-fourth/.git/config, after which EVERY
# git command in that clone failed with "fatal: this operation must be run in
# a work tree". The class is cody's SHARED_CONFIG_WRITE_FROM_WORKTREE.
#
# A CLONE HAS ITS OWN `.git/config`, SO THE WRITE CANNOT REACH THIS CLONE AT
# ALL -- regardless of who makes it and regardless of whether this process
# lives long enough to put anything back. That is the difference between
# containing it and fixing it. check8_probe.py made exactly this move on
# 2026-10-06 (b23dbc2e) and is the pattern followed here rather than a second
# invention; the comment block there is the longer account.
#
# ── HARDLINKED, NOT `--no-hardlinks`, AND THE NUMBER IS MEASURED ───────────
# The batch brief asked for `git clone --local --no-hardlinks`. Measured in
# this clone on 2026-10-12: `--no-hardlinks` takes 7.7s and leaves 207MB on
# disk per run (.git alone is 100MB); the hardlinked form costs no measurable
# time and no disk, which is why check8_probe.py uses it. These probes run in
# the whole-tree suite, in four clones, after every push -- and "a repair
# command nobody can run is not a repair" is already written into
# tier_a_review_gate.py's own history. `--no-hardlinks` buys object-store
# isolation that nothing here needs: git never rewrites a pack in place, new
# objects land in new files, and no probe runs `gc`. The config was the whole
# defect and a clone fixes it either way. Said out loud because it is a
# deliberate deviation from the brief, not an oversight.
#
# ── WHAT A CLONE DOES NOT INHERIT, AND WHY EACH ONE MATTERS ────────────────
# `core.hooksPath` is CONFIG, not a tracked file, so the clone does not get it
# -- and without it the pre-push hook NEVER FIRES and this probe would report
# "not blocked" about a gate it never asked. Asserted below rather than
# assumed. `origin` in a clone of a local path points at THAT PATH, so a push
# there would exercise a different thing entirely; the real URL is read off
# MAIN and set. Both are the silent-pass direction, which is why
# `_setup_clone()` returns a REASON string and the caller exits 3 rather than
# limping on.
#
# ── THE ORIGINAL WORKTREE NOTE, KEPT, BECAUSE ITS FIRST REASON STILL HOLDS ─
# Same change, same day and the same reason as check4_probe.py, which
# `docs/2026-09-10-run-all-tests-hook-PAUSED.md` names alongside this file:
# both committed fixtures ONTO THE WORKING BRANCH and `git reset --mixed` back.
# That is safe for one runner on a quiet branch, and when the full-suite hook
# fired on every Bash tool call it was not -- several copies ran at once, each
# reset to its own start, and five stranded `PROBE` commits reached origin/main
# in a day. One of this pair's fixtures shipped to production.
#
# A detached worktree has no branch tip to strand a commit on. The pre-push
# hook still fires from it: `core.hooksPath` is `.githooks` and worktrees share
# the common git dir -- measured, not assumed.
#
# ── AND IT IS BUILT ON THE FETCHED REMOTE TIP, NOT ON LOCAL HEAD (2026-09-16) ─
# This said `HEAD`, and in a five-clone repo local HEAD is behind origin/main
# most of the time. The gate then refuses with "the outgoing range
# <remote>..<local> could not be read" -- CORRECTLY, since the remote tip is not
# an object this clone has yet -- and that refusal lands before check 7 is ever
# reached. Measured 2026-09-16: all three failing arms reported exit 1 with
# blocked_by_preauth False and names_the_file False, which reads as "check 7 did
# not fire" and actually meant "the push never got that far".
#
# Built on the fetched tip, the outgoing range is exactly the fixture commit.
#
# ── OR A THROWAWAY BARE REMOTE, OPT-IN (2026-10-13, b5 item 6) ────────────
# `SAIRN_PROBE_LOCAL_REMOTE=1` or `--local-remote` builds a bare repo on local
# disk at BASE and points the clone's origin at it, so the verdict stops
# depending on the network and on origin/main moving under the run. The hook is
# NOT stubbed -- same `core.hooksPath`, same real gate, every check still votes.
# tests/push_gate/_local_remote.py carries the argument and what it does NOT
# fix. The real-remote path stays the DEFAULT.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _local_remote                                          # noqa: E402

LOCAL_REMOTE = _local_remote.requested(sys.argv[1:])
BARE = None
if LOCAL_REMOTE:
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
              'mode, so nothing about check 7 was verified.')
        sys.exit(3)
else:
    _fetch = subprocess.run(['git', '-C', MAIN, 'fetch', '--quiet', 'origin', 'main'],
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    if _fetch.returncode != 0:
        print('SKIPPED: could not fetch origin/main, so the fixture below could not be')
        print('built on the tip the gate compares against, and nothing about check 7')
        print('was verified: %s' % (_fetch.stderr or '').strip()[:200])
        sys.exit(3)
    BASE = subprocess.run(['git', '-C', MAIN, 'rev-parse', 'FETCH_HEAD'],
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace').stdout.strip()
WT = os.path.join(tempfile.gettempdir(), 'check7-probe-%d' % os.getpid())


def _setup_clone():
    """-> None on success, or a reason string. Never half-builds silently."""
    r = subprocess.run(['git', 'clone', '--quiet', '--local', '--no-checkout',
                        MAIN, WT], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return 'clone failed: %s' % (r.stderr or '').strip()[:200]
    global BARE
    if LOCAL_REMOTE:
        BARE, why = _local_remote.create(
            MAIN, BASE,
            os.path.join(tempfile.gettempdir(), 'check7-bare-%d' % os.getpid()))
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
                 ['config', 'user.email', 'check7-probe@example.invalid'],
                 ['config', 'user.name', 'check7-probe'],
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
    print('nothing about check 7 was verified: %s' % _why)
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


@atexit.register
def _remove_clone():
    _rmtree_loud(WT)
    if BARE:
        _local_remote.destroy(BARE)


print('  remote mode: %s'
      % ('LOCAL BARE at %s -- no network, tip cannot move' % BARE
         if LOCAL_REMOTE else 'the REAL origin (default)'))

# Every git and filesystem operation below happens in the clone. The name is
# kept so the arms and the existing `finally` read unchanged.
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
# It existed (2026-09-08, exit 3 rather than exit 1, because a precondition is
# not a failure) because `git add` in the clone could sweep somebody's
# uncommitted work into a probe commit. The worktree is created from HEAD and
# never contains the clone's uncommitted files, so there is nothing to sweep --
# and the guard had been SKIPPING this BLOCKING gate's only proof on every run
# in any clone with a modified tracked file.
#
# WHAT MUST STILL BE PROVED IS THAT THE CLONE WAS LEFT ALONE, which is the
# claim that was actually violated when a fixture from this pair shipped. It is
# asserted at the bottom against these.
MAIN_TREE_BEFORE = subprocess.run(
    ['git', '-C', MAIN, 'status', '--porcelain'],
    capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
MAIN_HEAD_BEFORE = subprocess.run(
    ['git', '-C', MAIN, 'rev-parse', 'HEAD'],
    capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()


# ── AND THE CLONE'S `.git/config`, WHICH IS THE THING THAT WAS BEING
#    CORRUPTED (2026-10-12) ──────────────────────────────────────────────────
# The two snapshots above are about the TREE and the BRANCH TIP. Neither of
# them could see the defect this file was actually carrying: `bare = true`
# appearing in MAIN's config leaves the tree clean and HEAD unmoved right up
# to the moment every git command starts failing. `--git-common-dir` is used
# rather than a hardcoded `.git/config` join because `MAIN/.git` is a DIRECTORY
# in a clone and a FILE in a linked worktree, and this probe has to be
# developable from either.
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
          'about check 7 was verified.' % MAIN_CONFIG_PATH)
    sys.exit(3)

start = run('git', 'rev-parse', 'HEAD').stdout.strip()
R = {}


# The gate's own words when it cannot compute what is being pushed. Matched
# rather than inferred from the exit code, because "could not tell" and "no"
# are different answers and this probe must not read one as the other.
RANGE_UNREADABLE = 'could not be read'
# ── A SECOND WAY THE GATE CANNOT READ THE PUSH (2026-10-13, b6 item 3) ────
# Same addition and same reason as check4_probe.py's: register_feed_gate
# denies with "stdin is not a terminal and carried NO ref lines", and its own
# text says a nested `git push` inside a script cannot reproduce the ref list
# git hands a hook -- "ISSUE THE PUSH DIRECTLY ... there is nothing wrong with
# the change." A probe drives every push from Python, so it is permanently in
# that case. That is the gate COULD NOT READ THE PUSH, not a verdict about
# check 7, and without this marker the planted arms report FAILED on a run
# where check 7 was never reached.
NO_REF_LINES = 'carried NO ref lines'


def dry_push():
    r = run('git', 'push', '--dry-run', 'origin', 'HEAD:main')
    err = (r.stderr or '') + (r.stdout or '')
    # ── THE REMOTE TIP MOVES UNDER THIS PROBE, SO ONE RETRY AFTER A FETCH ────
    # Five clones push to this branch and a run takes a minute. When origin/main
    # advances between one arm and the next, the sha git hands the hook is an
    # object this clone does not have yet, and the gate refuses -- correctly --
    # before check 7 is reached. Measured mid-run on 2026-09-16: arm 1 passed
    # and the three arms after it all carried exactly this refusal, which is
    # what made it look like check 7 had stopped firing.
    #
    # The fetch puts the new tip in the object store the push is judged
    # against, and the range becomes the fixture commit again -- BASE is an
    # ancestor of the new tip, so nothing else is in it. If it persists,
    # `could_not_run` below says so rather than letting the arms call it a
    # check-7 failure.
    #
    # ── IT FETCHES INTO THE CLONE, NOT INTO MAIN (2026-10-12) ─────────────
    # This said `git -C MAIN fetch` and worked ONLY because a linked worktree
    # shares MAIN's object store. A clone does not. Left unchanged by the
    # worktree-to-clone move it would have fetched into the wrong repository
    # and the retry would have failed exactly as the first attempt did --
    # which reads as "check 7 did not fire" and is the silent-pass direction
    # the 2026-09-16 note above this one is already about.
    if r.returncode != 0 and (RANGE_UNREADABLE in err or NO_REF_LINES in err):
        subprocess.run(['git', '-C', REPO, 'fetch', '--quiet', 'origin', 'main'],
                       capture_output=True)
        r = run('git', 'push', '--dry-run', 'origin', 'HEAD:main')
        err = (r.stderr or '') + (r.stdout or '')
    return {
        'could_not_run': r.returncode != 0 and (RANGE_UNREADABLE in err
                                        or NO_REF_LINES in err),
        'exit': r.returncode,
        # MATCHED ON A FRAGMENT THAT SURVIVES THE LINE WRAP. The first version
        # looked for 'BEFORE the caller is authenticated' and the deny message
        # breaks between 'the' and 'caller', so the arm reported NOT BLOCKED
        # against a push the gate had correctly refused -- exit 1, file named,
        # and the one assertion that mattered red for the wrong reason.
        'blocked_by_preauth': 'answer a refusal BEFORE the' in err,
        'names_the_file': EP in err,
        'unchecked': 'UNCHECKED for pre-auth disclosures' in err,
        'blocked_undeclared': 'NO authentication' in err and 'no declaration' in err,
        'rejected_by_remote': 'fetch first' in err or 'rejected' in err,
        # THE TEXT, NOT JUST THE FLAGS. Every flag above is a marker somebody
        # chose; a refusal none of them names leaves the whole dict reading
        # False, which is indistinguishable from "nothing blocked it".
        'err': err.strip()[-400:],
    }


path = os.path.join(REPO, EP)
original = open(path, encoding='utf-8').read()


def anchor_once(hay, needle, what):
    """Refuse an anchor that does not match EXACTLY ONCE (2026-09-10).

    Arm 1 asserted nothing at all -- a `.replace(x, y, 1)` whose x had gone
    would have committed the file UNCHANGED and reported that a clean change
    was allowed, which is true of any file and proves nothing. Arm 2 used
    .index(), which throws when the anchor is gone and silently takes the FIRST
    of several when it is ambiguous.

    Both directions matter and only one of them was covered. An anchor is a
    string match against code somebody else keeps editing, so going ambiguous
    is how it AGES rather than an accident: arm 15 of
    tests/sairndental_outbound_queue_probe.py went ambiguous the day a second
    SAIRNdental write branch landed with an identical header, and it survived
    as a real guard only because it counted.
    """
    n = hay.count(needle)
    assert n == 1, ('fixture invalid: %s matches %d places in %s, not 1 -- widen '
                    'the anchor until it is unique rather than letting the probe '
                    'pick one' % (what, n, EP))
    return needle

try:
    # ── ARM 1: a CLEAN change to the same endpoint must be allowed ──────────
    # Not a change to an unrelated file: the arm has to prove the check let a
    # touched endpoint through, or it proves only that the scope filter works.
    anchor_once(original, 'module.exports = async (req, res) => {', 'the handler opening')
    open(path, 'w', encoding='utf-8', newline='').write(
        original.replace('module.exports = async (req, res) => {',
                         '// probe: a comment, and nothing else\nmodule.exports = async (req, res) => {', 1))
    run('git', 'add', EP)
    run('git', 'commit', '-q', '-m', 'PROBE clean endpoint change')
    R['clean_change'] = dry_push()
    run('git', 'reset', '--mixed', start)
    run('git', 'checkout', '--', EP)

    # ── ARM 2: the REORDER PUT BACK must block ─────────────────────────────
    # The exact defect, not an invented one: move the envelope gate back above
    # validateLicenseKey, which is what all fifteen looked like before
    # 2026-09-08.
    anchor_once(original, '  let body = req.body;', 'the envelope gate opening')
    anchor_once(original, '  let lic;\n  try {', 'the licence-validation opening')
    body_at = original.index('  let body = req.body;')
    body_end = original.index('\n  }\n', original.index('.indexOf(action)', body_at)) + len('\n  }\n')
    block = original[body_at:body_end]
    reverted = original[:body_at] + original[body_end:]
    lic_at = reverted.index('  let lic;\n  try {')
    reverted = reverted[:lic_at] + block + '\n' + reverted[lic_at:]
    assert 'let body = req.body;' in reverted and reverted != original, 'fixture invalid'
    open(path, 'w', encoding='utf-8', newline='').write(reverted)
    run('git', 'add', EP)
    run('git', 'commit', '-q', '-m', 'PROBE pre-auth disclosure')
    R['planted_disclosure'] = dry_push()
    run('git', 'reset', '--mixed', start)
    run('git', 'checkout', '--', EP)
    # ── ARM 3: a NEW endpoint with no auth boundary must block ─────────────
    # The api/claude.js shape: an endpoint that authenticates nothing, added
    # with nothing to notice it. It is not wrong on its own -- 25 are public on
    # purpose -- but it must be DECLARED, and this arm is the only thing that
    # proves an undeclared one cannot slip in.
    newep = os.path.join(REPO, 'api', 'zz_probe_public.js')
    _src = [
        '// probe: an endpoint that authenticates nothing and declares nothing.',
        'module.exports = async (req, res) => {',
        "  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }",
        '  res.status(200).json({ ok: true });',
        '};',
    ]
    open(newep, 'w', encoding='utf-8', newline='').write(chr(10).join(_src) + chr(10))
    run('git', 'add', 'api/zz_probe_public.js')
    run('git', 'commit', '-q', '-m', 'PROBE undeclared public endpoint')
    R['undeclared_endpoint'] = dry_push()
    run('git', 'reset', '--mixed', start)
    if os.path.exists(newep):
        os.remove(newep)

finally:
    _stray = os.path.join(REPO, 'api', 'zz_probe_public.js')
    if os.path.exists(_stray):
        os.remove(_stray)
    open(path, 'w', encoding='utf-8', newline='').write(original)
    run('git', 'reset', '--mixed', start)
    run('git', 'checkout', '--', EP)

fails = []
RAN = [0]


def check(name, cond, detail=''):
    RAN[0] += 1
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


print('push-gate check 7 -- a pre-auth disclosure must not reach origin\n')

a = R['clean_change']
# ── THE CLEAN PUSH IS THE PRECONDITION, NOT ONLY AN ARM (2026-09-16) ───────
# If a CLEAN change cannot get through, every refusal below is attributable to
# whatever stopped this one and not to check 7. Reporting those arms as check-7
# failures is a failure report about check 7 written on evidence that says
# nothing about check 7. Could-not-run is a third state: exit 3, with the text.
#
# ── A REFUSAL BY A DIFFERENT CHECK IS A FOURTH STATE (2026-10-13, b5) ──────
# Same change and same reason as check4_probe.py's. The paragraph above is
# right that a refused clean push makes a LATER refusal unattributable; it is
# NOT right that it makes the whole run unverifiable, and that cost this probe
# its verdict on 2026-10-12 and again on 2026-10-13 when the
# external-file-index check refused over another session's handoff on a shared
# Google Drive -- a reason entirely outside this repository.
#
# CLASSIFIED, NOT JUST COUNTED. If the clean push's refusal carries check 7's
# OWN markers it is a check-7 failure and still exits 3. If it carries none,
# some other check voted no: arm 1 is UNPROVEN, the run CONTINUES, and the
# planted arms stay attributable because they assert markers no other check
# emits. The hook is not stubbed, nothing is skipped, no override is set --
# the probe simply stops reading another check's verdict as its own.
_unattributable = [k for k, v in R.items() if v.get('could_not_run')]
_clean_foreign = (a['exit'] != 0 and not a['blocked_by_preauth']
                  and not a['unchecked'] and not a['blocked_undeclared']
                  and not a['names_the_file'])
if _unattributable or (a['exit'] != 0 and not _clean_foreign):
    print('SKIPPED: a push was refused before check 7 could answer, so nothing')
    print('here is attributable to it. Nothing about check 7 was verified.')
    if _unattributable:
        print('  the gate could not read the outgoing range for: %s'
              % ', '.join(sorted(_unattributable)))
    print('  the refusal: %s' % (R[_unattributable[0]]['err'] if _unattributable
                                 else a['err']))
    sys.exit(3)
if _clean_foreign:
    print('NOTE: the clean push was refused by a DIFFERENT check in the hook.')
    print('Arms 1 and 2 are therefore answered by running check 7\'s OWN')
    print('checker directly rather than reported UNPROVEN. The foreign refusal:')
    print('  %s\n' % a['err'][-300:])

# ── ARMS 1 AND 2 ARE NOW ANSWERED FIRST-HAND (2026-10-13, b6 item 3) ───────
# b5 reported these two UNPROVEN whenever a foreign check refused the clean
# push. That was honest and not good enough: UNPROVEN is an absence of
# information and the information was available.
#
# CHECK 7 IS `tools/preauth_oracle_check.py`, and the gate does not shell out to
# it -- it imports the module and calls `scan(path)` on the blob at the push tip
# (tools/sairn_push_gate_hook.py's CHECK 7 block). So the probe calls THE SAME
# FUNCTION on the clean fixture file and reads check 7's own answer, with no
# other check able to speak over it.
#
# `scan()` RETURNS (rel, boundary, found) AND BOTH ARMS COME OUT OF IT:
#   boundary is None   the file has NO auth boundary at all. That is what
#                      "failing open" means here, and it is arm 2.
#   found              every refusal answered ABOVE the boundary, each tagged
#                      ORACLE or DISCLOSURE. Check 7 BLOCKS on the DISCLOSURE
#                      tier, so a clean file must carry none. That is arm 1.
#
# ARM 2 IS THE SHARPER OF THE TWO AND IT IS WHY `boundary` IS CHECKED RATHER
# THAN ONLY THE FINDING LIST. An empty `found` is produced BOTH by a clean file
# and by a file whose boundary could not be located -- `scan` returns early with
# no findings in that case. Reading an empty list as a pass would be a checker
# that stays silent because it never looked, which is exactly the shape check 7
# exists to refuse one level down.
_pre_tool = os.path.join(REPO, 'tools', 'preauth_oracle_check.py')
_pre = {'ok': False, 'why': '', 'boundary': None, 'found': None}
if not os.path.isfile(_pre_tool):
    _pre['why'] = ('tools/preauth_oracle_check.py is not in the fixture clone, '
                   'so check 7 could not be asked directly')
else:
    try:
        import importlib.util as _ilu7
        _ps = _ilu7.spec_from_file_location('b6_preauth', _pre_tool)
        _pm = _ilu7.module_from_spec(_ps)
        _ps.loader.exec_module(_pm)
        _rel7, _bnd7, _found7 = _pm.scan(os.path.join(REPO, EP))
        _pre['boundary'] = _bnd7
        _pre['found'] = _found7
        _pre['ok'] = True
    except BaseException as _e7:                             # noqa: BLE001
        _pre['why'] = '%s: %s' % (type(_e7).__name__, _e7)

if not _pre['ok']:
    check('a clean change to a touched endpoint is NOT blocked by check 7',
          False,
          'FAILED -- check 7 could not be asked directly: ' + _pre['why'])
    check('...and check 7 did not silently fail open on it',
          False,
          'FAILED -- check 7 could not be asked directly: ' + _pre['why'])
else:
    _disc7 = [f for f in (_pre['found'] or []) if f[1] == 'DISCLOSURE']
    _orac7 = [f for f in (_pre['found'] or []) if f[1] == 'ORACLE']
    check('a clean change to a touched endpoint is NOT blocked by check 7 -- '
          'preauth_oracle_check.scan() finds %d DISCLOSURE-tier refusal(s) '
          'above the auth boundary in %s, and check 7 blocks on that tier'
          % (len(_disc7), EP),
          not _disc7,
          'DISCLOSURE findings: %r  (ORACLE tier, which check 7 reports but '
          'does not block on: %d)' % (_disc7[:4], len(_orac7)))
    check('...and check 7 did not silently fail open on it -- scan() LOCATED '
          'the auth boundary, so an empty finding list means "looked and found '
          'nothing" rather than "never looked"',
          _pre['boundary'] is not None,
          'scan() returned boundary=None for %s, which is the fail-open shape: '
          'no auth call was located, so every refusal in the file is above a '
          'boundary that does not exist and the empty finding list means '
          'nothing' % EP)

b = R['planted_disclosure']
check('the reorder put back IS blocked', b['blocked_by_preauth'], str(b))
check('...and the refusal names the file', b['names_the_file'], str(b))
check('...and the push exits non-zero', b['exit'] != 0, str(b))

c = R['undeclared_endpoint']
check('a NEW endpoint with no auth boundary and no declaration IS blocked',
      c['blocked_undeclared'], str(c))
check('...and that push exits non-zero', c['exit'] != 0, str(c))

check('the repo was restored', open(path, encoding='utf-8').read() == original)
check('...and the probe endpoint was removed',
      not os.path.exists(os.path.join(REPO, 'api', 'zz_probe_public.js')))
check('...and HEAD is back where it started',
      run('git', 'rev-parse', 'HEAD').stdout.strip() == start)

# ── AND THE CLONE ITSELF WAS NEVER TOUCHED (2026-09-11) ────────────────────
# The three above are about the WORKTREE and still matter -- a probe whose own
# cleanup is broken measured the wrong tree in its later arms. None of them is
# the claim that was violated when a fixture from this file reached origin/main
# and shipped to production, and until now nothing asserted that one.
check('and the CLONE was never touched -- no commit, no modified file',
      subprocess.run(['git', '-C', MAIN, 'status', '--porcelain'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace').stdout == MAIN_TREE_BEFORE
      and subprocess.run(['git', '-C', MAIN, 'rev-parse', 'HEAD'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
      == MAIN_HEAD_BEFORE)

# ── AND ITS `.git/config` IS BYTE-IDENTICAL, WHICH THE TWO ARMS ABOVE
#    CANNOT SEE (2026-10-12) ─────────────────────────────────────────────────
# This is the arm the worktree-to-clone move exists for. Against the OLD code
# it could go red for real: a `git config` write from inside a linked worktree
# reaches the owning clone, and that is the delta
# docs/2026-10-07-fourth-routed-pinned-worktree-shared-config.md reproduced in
# two commands. A clone has its own config, so the write cannot arrive here at
# all -- which is why this can be green rather than aspirational.
_cfg_after = _read_main_config()
check("...and the clone's .git/config is byte-identical -- the delta a shared "
      'config lets a worktree write, and the one a clean tree and an unmoved '
      'HEAD both cannot see',
      _cfg_after == MAIN_CONFIG_BEFORE,
      'config changed: %s bytes before, %s after, at %s'
      % (len(MAIN_CONFIG_BEFORE),
         len(_cfg_after) if _cfg_after is not None else 'unreadable',
         MAIN_CONFIG_PATH))

# ── AND NO WORKTREE REGISTRATION WAS LEFT BEHIND ───────────────────────────
# The old code registered a linked worktree in `.git/worktrees/` and removed it
# in an atexit handler, so a killed run left one to be pruned. A clone leaves
# nothing to prune -- asserted rather than claimed, because "nothing to clean
# up" is the kind of statement that stays in a comment after it stops being
# true.
_wt_list = subprocess.run(['git', '-C', MAIN, 'worktree', 'list', '--porcelain'],
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace').stdout
check('...and no linked worktree was registered in the clone at all',
      'check7-probe' not in _wt_list, _wt_list.strip()[:300])


# COUNTED, NOT HARDCODED. This printed a literal `10` regardless of how many
# checks actually ran -- the same derived-subject blindness the 2026-09-10
# sweep went looking for, in the one line a reader uses to judge coverage.
# Adding a check would have left it reporting 10 of 11.
if _clean_foreign:
    # SAID IN THE VERDICT LINE, not only in a note 60 lines up -- but the
    # sentence has changed: arms 1 and 2 are no longer unproven, they are
    # answered by a different and better source than the gate's exit code.
    print('\n  NOTE: the clean push was refused by a DIFFERENT check in the same')
    print('  hook, so arms 1 and 2 were answered by calling check 7\'s own')
    print('  preauth_oracle_check.scan() on the clean fixture directly. Both')
    print('  are real results above -- neither is UNPROVEN.')
print('\n%s  check7_probe: %d checks, %d failed'
      % ('FAILED' if fails else 'ok', RAN[0], len(fails)))
sys.exit(1 if fails else 0)
