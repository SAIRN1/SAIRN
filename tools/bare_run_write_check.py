#!/usr/bin/env python
"""Which tools in tools/ WRITE when you run them with no arguments.

WHY THIS EXISTS. Running a tool bare, to see what it does, executed it -- and
three generated documents were rewritten by that one act. `python tools/foo.py`
with no arguments is the most natural way to ask a tool what it is, and on this
platform it has been the same keystroke as telling it to go. A tool whose bare
run mutates the repo makes reading it indistinguishable from running it.

THE RULE THIS MEASURES: a bare run must be REPORT-ONLY. Writing is a thing you
ask for with a flag.

── WHY IT REFUSES TO RUN IN A REAL CLONE, AND WHY THAT IS THE WHOLE POINT ────
This tool executes every tool it finds. In a real clone that is exactly the
damage it exists to detect, done 274 times. It therefore refuses on any target
that looks like one of the working clones, refuses on a dirty tree (a write it
did not cause is indistinguishable from one it did), and refuses when it finds
no tools at all -- an empty sweep reporting "nothing writes" is the shape this
repo has paid for more than once.

EXIT CODES, and the third one is not a pass:
  0  every tool's bare run was report-only
  1  at least one tool WROTE on a bare run (or on --help)
  2  COULD NOT RUN -- no usable scratch repo, no tools found, or the tree was
     dirty before the sweep started. NOT a clean bill.

── SEGMENTED ON PURPOSE (cross-domain discipline 10) ────────────────────────
274 tools at a few seconds each is a long run. Every tool's verdict is printed
and flushed as it is decided, and the reset between tools is VERIFIED rather
than assumed -- if `git status --porcelain` is not empty after the reset, the
sweep stops there rather than attributing the residue to the next tool.

Usage:
  python tools/bare_run_write_check.py --repo <path to a scratch clone>
  python tools/bare_run_write_check.py --repo <path> --only foo.py,bar.py
  python tools/bare_run_write_check.py --repo <path> --timeout 20
"""
import hashlib
import io
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import bare_run_writers as _allow           # noqa: E402
except Exception:                               # noqa: BLE001
    _allow = None

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A path that looks like one of the working clones. Refused outright: this tool
# runs what it finds, so pointing it at a clone somebody is working in is the
# defect it detects, performed deliberately.
REAL_CLONE_RX = re.compile(r'[\\/]Documents[\\/]SAIRN-[\w]+[\\/]?$', re.I)


def out(line):
    sys.stdout.write(line + '\n')
    sys.stdout.flush()


def git(repo, *args):
    r = subprocess.run(('git',) + args, cwd=repo, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, r.stdout, r.stderr


def porcelain(repo):
    code, so, se = git(repo, 'status', '--porcelain')
    if code != 0:
        return None
    return [l for l in so.split('\n') if l.strip()]


def reset(repo):
    git(repo, 'checkout', '--', '.')
    git(repo, 'clean', '-fdq')
    return porcelain(repo)


# ── SHARED STATE: THE HALF `git status` CANNOT SEE (widened 2026-10-08) ─────
# THE DEFECT THAT FORCED THIS, measured in batch 18: a bare run of
# `tools/session_lock_check.py` ACQUIRED A SESSION LOCK -- it created
# `~/SAIRN-SESSION-LOCKS/<clone>.lock`, printed nothing and exited 0. This tool,
# built to catch exactly a mutating bare run, reported it CLEAN.
#
# It was not a bug in the comparison. It was the SCOPE. `git status` sees the
# working tree, and the lock registry lives OUTSIDE EVERY CLONE on purpose --
# that is why it is current without a fetch. So the write was real, it mattered
# to every other session that reads the registry, and it was invisible to the
# one tool whose job it was.
#
# THE EVIDENCE WAS SITTING THERE: ~/SAIRN-SESSION-LOCKS/ held locks named after
# throwaway clones that no longer exist -- bare_scratch (2026-09-30), b11wt2
# (2026-10-06), b12wt2 (2026-10-07) -- each one a bare run of that file inside a
# scratch copy, recorded in a registry other sessions consult to decide whether
# somebody is working.
#
# THREE THINGS ARE WATCHED, and each is a place a tool has really written:
#   1. ~/SAIRN-SESSION-LOCKS/   the cross-clone registry
#   2. <repo>/.git/config       a LINKED WORKTREE shares this with its clone, so
#                               a `git config` write from inside one lands here
#                               -- this is how core.bare=true reached a live
#                               clone in batch 18. `git status` never sees it.
#   3. git worktree list        registering or pruning a worktree is a change to
#                               shared state with no file in the tree.
#
# A SHARED-STATE WRITE IS NEVER EXEMPTED BY THE ALLOWLIST.
# tools/bare_run_writers.py declares REPO paths; nothing in it says a tool may
# write outside the clone. Treating silence there as permission is how this gap
# stayed open, so these are reported unconditionally.
# OVERRIDABLE FOR THE SELFTEST ONLY, and that is the whole reason it exists: a
# detector of writes outside the repo cannot be tested without a safe place to
# watch, and watching the REAL registry while planting fixtures in it would make
# the test the defect. Production never sets this.
LOCKS_DIR = os.environ.get(
    'SAIRN_LOCKS_DIR',
    os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS'))


def shared_snapshot(repo):
    """A fingerprint of everything outside the working tree a tool could write.

    Returns a dict; a value of the string 'UNREADABLE' is kept rather than
    dropped, because a path that cannot be read is a third state and comparing
    two absences would report CLEAN.
    """
    snap = {}
    if os.path.isdir(LOCKS_DIR):
        for dirpath, _dirs, files in os.walk(LOCKS_DIR):
            for fn in sorted(files):
                p = os.path.join(dirpath, fn)
                k = 'LOCKS:' + os.path.relpath(p, LOCKS_DIR).replace('\\', '/')
                try:
                    snap[k] = hashlib.sha256(
                        io.open(p, 'rb').read()).hexdigest()[:16]
                except OSError:
                    snap[k] = 'UNREADABLE'
    else:
        snap['LOCKS:<dir>'] = 'ABSENT'
    cfg = os.path.join(repo, '.git', 'config')
    try:
        snap['GITCONFIG'] = hashlib.sha256(
            io.open(cfg, 'rb').read()).hexdigest()[:16]
    except OSError:
        snap['GITCONFIG'] = 'UNREADABLE'
    code, so, _se = git(repo, 'worktree', 'list', '--porcelain')
    snap['WORKTREES'] = (hashlib.sha256(so.encode('utf-8')).hexdigest()[:16]
                         if code == 0 else 'UNREADABLE')
    return snap


def shared_diff(before, after):
    """Human-readable changes between two snapshots, newest key order stable."""
    keys = sorted(set(before) | set(after))
    diffs = []
    for k in keys:
        b, a = before.get(k), after.get(k)
        if b == a:
            continue
        if b is None:
            diffs.append('%s CREATED' % k)
        elif a is None:
            diffs.append('%s DELETED' % k)
        else:
            diffs.append('%s CHANGED' % k)
    return diffs


def run_tool(repo, rel, args, timeout):
    """(exit_code_or_None, wrote, shared) -- None means it did not finish.

    `shared` is the list of out-of-tree changes, which is why this returns three
    values now instead of two.
    """
    s_before = shared_snapshot(repo)
    # ── THE DETECTOR MUST NOT CAUSE WHAT IT DETECTS (RULE G, 2026-10-08) ────
    # This sweep RUNS every tool. Several of them write to the lock registry,
    # and `tools/session_lock_check.py` honours `SAIRN_SESSION_LOCK_DIR`. If
    # LOCKS_DIR has been redirected to a sandbox, the children are pointed at
    # THE SAME sandbox -- so a lock-writing tool is still caught, and the real
    # cross-clone registry other sessions read is never written to.
    #
    # ALIGNED HERE RATHER THAN LEFT TO THE CALLER, because a detector whose
    # correctness depends on remembering two environment variables is one
    # somebody will eventually run with only the first.
    env = dict(os.environ)
    if os.environ.get('SAIRN_LOCKS_DIR'):
        env['SAIRN_SESSION_LOCK_DIR'] = os.environ['SAIRN_LOCKS_DIR']
    try:
        r = subprocess.run([sys.executable, rel] + list(args), cwd=repo,
                           capture_output=True, timeout=timeout, env=env)
        code = r.returncode
    except subprocess.TimeoutExpired:
        code = None
    except OSError as e:
        out('    COULD NOT LAUNCH %s: %s' % (rel, e))
        code = None
    wrote = porcelain(repo)
    shared = shared_diff(s_before, shared_snapshot(repo))
    return code, wrote, shared


def opt(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def selftest():
    """Can the SHARED-STATE half be made to fail? If not, it is decoration.

    Every arm plants a real change in a real place and asserts the detector
    reports it. The fixtures live in a temp directory with SAIRN_LOCKS_DIR
    pointed at it, so the real registry is never written to -- watching the live
    registry while planting fixtures in it would make the test the defect.
    """
    import shutil
    import tempfile
    global LOCKS_DIR
    npass = nfail = 0

    def ck(label, cond, extra=''):
        nonlocal npass, nfail
        if cond:
            npass += 1
            out('  ok   ' + label)
        else:
            nfail += 1
            out('  FAIL ' + label)
            if extra:
                out('       ' + str(extra)[:300])

    out('BARE-RUN WRITE SWEEP -- SELFTEST of the shared-state half')
    out('  SAIRN_LOCKS_DIR is redirected to a temp dir; the real registry is '
        'never touched.')
    out('')
    base = tempfile.mkdtemp(prefix='brwc_self_')
    real_locks = LOCKS_DIR
    try:
        LOCKS_DIR = os.path.join(base, 'locks')
        os.makedirs(LOCKS_DIR)
        repo = os.path.join(base, 'repo')
        os.makedirs(repo)
        for a in (['init', '-q'], ['config', 'user.email', 'f@x.invalid'],
                  ['config', 'user.name', 'f']):
            git(repo, *a)
        io.open(os.path.join(repo, 'a.txt'), 'w', encoding='utf-8').write('x\n')
        git(repo, 'add', '-A')
        git(repo, 'commit', '-q', '-m', 'f')

        s0 = shared_snapshot(repo)
        ck('A1. two snapshots of an untouched world are IDENTICAL -- without '
           'this every arm below would pass on noise',
           shared_diff(s0, shared_snapshot(repo)) == [],
           shared_diff(s0, shared_snapshot(repo)))

        io.open(os.path.join(LOCKS_DIR, 'planted.lock'), 'w',
                encoding='utf-8').write('{"pid": 1}\n')
        d = shared_diff(s0, shared_snapshot(repo))
        ck('A2. a NEW lock file is reported CREATED. This is the exact shape '
           'session_lock_check.py produced on a bare run, which this tool used '
           'to report CLEAN',
           d == ['LOCKS:planted.lock CREATED'], d)

        s1 = shared_snapshot(repo)
        io.open(os.path.join(LOCKS_DIR, 'planted.lock'), 'w',
                encoding='utf-8').write('{"pid": 2}\n')
        d = shared_diff(s1, shared_snapshot(repo))
        ck('A3. an EDITED lock is reported CHANGED, not missed -- a refreshed '
           'lock is still a write to a registry other sessions read',
           d == ['LOCKS:planted.lock CHANGED'], d)

        s2 = shared_snapshot(repo)
        os.remove(os.path.join(LOCKS_DIR, 'planted.lock'))
        d = shared_diff(s2, shared_snapshot(repo))
        ck('A4. a DELETED lock is reported DELETED. Removing somebody else\'s '
           'lock is as much a change as taking one',
           d == ['LOCKS:planted.lock DELETED'], d)

        s3 = shared_snapshot(repo)
        git(repo, 'config', 'core.bare', 'false')
        git(repo, 'config', 'sairn.selftest', 'planted')
        d = shared_diff(s3, shared_snapshot(repo))
        ck('A5. a `git config` write is reported GITCONFIG CHANGED. THIS IS THE '
           'ONE git status CANNOT SEE, and it is how core.bare=true reached a '
           'live clone from inside a linked worktree',
           d == ['GITCONFIG CHANGED'], d)

        s4 = shared_snapshot(repo)
        wt = os.path.join(base, 'wt')
        git(repo, 'worktree', 'add', '--detach', wt, 'HEAD')
        d = shared_diff(s4, shared_snapshot(repo))
        ck('A6. registering a WORKTREE is reported WORKTREES CHANGED -- a '
           'change to shared state with no file in the tree, and every '
           'registration is another door to the shared config',
           'WORKTREES CHANGED' in d, d)

        s5 = shared_snapshot(repo)
        ck('A7. THE PAIRED NEGATIVE: with nothing planted, the detector reports '
           'NOTHING. An alarm that always fires is not a detector',
           shared_diff(s5, shared_snapshot(repo)) == [],
           shared_diff(s5, shared_snapshot(repo)))

        # ── END TO END: a planted tool that takes a lock must make the sweep
        # fail, through run_tool, not through shared_diff called by hand.
        os.makedirs(os.path.join(repo, 'tools'), exist_ok=True)
        io.open(os.path.join(repo, 'tools', 'zz_planted_locker.py'), 'w',
                encoding='utf-8').write(
            'import io, os, sys\n'
            'p = os.path.join(os.environ["SAIRN_LOCKS_DIR"], "e2e.lock")\n'
            'io.open(p, "w", encoding="utf-8").write("{}\\n")\n'
            'sys.exit(0)\n')
        git(repo, 'add', '-A')
        git(repo, 'commit', '-q', '-m', 'planted')
        os.environ['SAIRN_LOCKS_DIR'] = LOCKS_DIR
        code, wrote, shared = run_tool(repo, os.path.join(
            'tools', 'zz_planted_locker.py'), [], 25)
        ck('B1. END TO END -- a planted tool that writes a lock on a bare run is '
           'caught by run_tool, exit 0 and a clean `git status` '
           'notwithstanding. THAT COMBINATION IS EXACTLY WHAT WAS BEING MISSED',
           shared == ['LOCKS:e2e.lock CREATED'] and not wrote and code == 0,
           'code=%s wrote=%s shared=%s' % (code, wrote, shared))
    finally:
        LOCKS_DIR = real_locks
        os.environ.pop('SAIRN_LOCKS_DIR', None)
        shutil.rmtree(base, ignore_errors=True)

    out('')
    out('%d passed, %d failed' % (npass, nfail))
    return 1 if nfail else 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    repo = opt(argv, '--repo')
    if not repo:
        sys.stderr.write(
            '--repo is required and must be a SCRATCH clone.\n'
            'This tool runs every tool it finds; there is no safe default.\n'
            '  git clone --local --no-hardlinks . <scratch path>\n')
        return 2
    repo = os.path.abspath(repo)
    if not os.path.isdir(os.path.join(repo, '.git')):
        sys.stderr.write('Not a git repository: %s\n'
                         'COULD NOT RUN -- without git there is no way to tell '
                         'what a tool wrote.\n' % repo)
        return 2
    if REAL_CLONE_RX.search(repo.rstrip('\\/')) or os.path.normcase(repo) == os.path.normcase(REPO):
        sys.stderr.write(
            'REFUSED: %s looks like a working clone.\n'
            'This tool EXECUTES every tool in tools/. Running it here is the\n'
            'defect it exists to detect, performed 274 times on a tree\n'
            'somebody is using. Clone to scratch first.\n' % repo)
        return 2

    dirty = porcelain(repo)
    if dirty is None:
        sys.stderr.write('COULD NOT RUN -- git status failed in %s\n' % repo)
        return 2
    if dirty:
        sys.stderr.write(
            'REFUSED: the scratch tree is already dirty (%d path(s)).\n'
            'A change this sweep did not cause is indistinguishable from one it\n'
            'did, so the result would be unattributable rather than wrong.\n'
            'First: git checkout -- . && git clean -fd\n' % len(dirty))
        return 2

    timeout = int(opt(argv, '--timeout', '25'))
    only = opt(argv, '--only')
    only = set(x.strip() for x in only.split(',')) if only else None

    tools_dir = os.path.join(repo, 'tools')
    if not os.path.isdir(tools_dir):
        sys.stderr.write('COULD NOT RUN -- no tools/ directory in %s\n' % repo)
        return 2
    names = sorted(n for n in os.listdir(tools_dir) if n.endswith('.py'))
    if only is not None:
        names = [n for n in names if n in only]
    if not names:
        sys.stderr.write(
            'COULD NOT RUN -- no tools matched. An empty sweep reporting '
            '"nothing writes" is not a finding, it is a measurement that did '
            'not happen.\n')
        return 2

    out('BARE-RUN WRITE SWEEP -- does running a tool with no arguments mutate '
        'the repo')
    out('  scratch repo : %s' % repo)
    out('  tools swept  : %d' % len(names))
    out('  per-tool timeout: %ds (a tool that does not finish is COULD NOT RUN, '
        'never "did not write")' % timeout)
    out('')

    # THE ALLOWLIST, AND IT FAILS CLOSED (2026-09-30). tools/bare_run_writers.py
    # names the tools whose bare run is SUPPOSED to write, with the path and the
    # reason for each. If that module cannot be imported, nothing is exempted --
    # the sweep reports every writer as before and says the list was unreadable,
    # because an allowlist that silently becomes empty is safe and one that
    # silently becomes universal is not.
    if _allow is None:
        out('  ALLOWLIST         : UNREADABLE -- tools/bare_run_writers.py could '
            'not be')
        out('                      imported, so NOTHING is exempted and every '
            'writer below is')
        out('                      reported. This is the safe direction and it is '
            'said out loud.')
    else:
        out('  ALLOWLIST         : %d tool(s) declared as intended writers in '
            'tools/bare_run_writers.py' % len(_allow.WRITERS))
        out('                      Each names the path it writes and why. They are '
            'listed as')
        out('                      INTENDED below rather than omitted -- an '
            'exemption nobody can')
        out('                      see is indistinguishable from a check that '
            'stopped running.')
    out('')

    out('  SHARED STATE      : WATCHED TOO, and never exempted by the '
        'allowlist.')
    out('                      %s' % LOCKS_DIR)
    out('                      <repo>/.git/config  (a LINKED WORKTREE shares '
        'this, which is')
    out('                      how core.bare=true reached a live clone -- '
        '`git status`')
    out('                      never sees it)')
    out('                      `git worktree list`  (registering one is a '
        'change with no')
    out('                      file in the tree)')
    out('                      bare_run_writers.py declares REPO paths only. '
        'Nothing in it')
    out('                      says a tool may write OUTSIDE the clone, and '
        'reading that')
    out('                      silence as permission is how this gap stayed '
        'open.')
    out('')

    writes_bare, writes_help, could_not, intended = [], [], [], []
    writes_shared = []
    for n in names:
        rel = os.path.join('tools', n)
        code, wrote, shared = run_tool(repo, rel, [], timeout)
        if shared:
            writes_shared.append((n, shared))
            out('  WRITES(SHARED) %-45s exit=%s  %s' % (
                n, code, '; '.join(shared[:4])
                + (' ...+%d' % (len(shared) - 4) if len(shared) > 4 else '')))
        if wrote and _allow is not None and _allow.is_intended(n):
            # DECLARED. Reported, and the paths are CHECKED against what it said
            # it would write: a declared writer that starts writing something
            # ELSE is exactly the case an allowlist must not cover.
            said = set(_allow.writes(n))
            got = set(w[3:].strip().strip('"') for w in wrote)
            extra = sorted(got - said)
            intended.append((n, sorted(got), extra))
            out('  INTENDED      %-46s exit=%s  %s%s' % (
                n, code, ', '.join(sorted(got)[:3]),
                '   ** ALSO WROTE UNDECLARED: %s **' % ', '.join(extra)
                if extra else ''))
        elif wrote:
            writes_bare.append((n, wrote))
            out('  WRITES(bare)  %-46s exit=%s  %s' % (
                n, code, ', '.join(w[3:] for w in wrote[:4])
                + (' ...+%d' % (len(wrote) - 4) if len(wrote) > 4 else '')))
        elif code is None:
            could_not.append((n, 'bare run did not finish in %ds' % timeout))
            out('  COULD NOT RUN %-46s bare run did not finish in %ds' % (n, timeout))
        left = reset(repo)
        if left:
            out('')
            out('  STOPPING HERE. The reset after %s left %d path(s) dirty, so '
                'every verdict after this one would be unattributable:' % (n, len(left)))
            for l in left[:10]:
                out('      %s' % l)
            out('')
            return 2

        code, wrote, shared = run_tool(repo, rel, ['--help'], timeout)
        if shared:
            writes_shared.append((n + ' --help', shared))
            out('  WRITES(SHARED) %-45s exit=%s  %s'
                % (n + ' --help', code, '; '.join(shared[:4])))
        if wrote and _allow is not None and _allow.is_intended(n):
            pass                      # a declared writer writing on --help too
        elif wrote:
            writes_help.append((n, wrote))
            out('  WRITES(--help) %-45s exit=%s  %s' % (
                n, code, ', '.join(w[3:] for w in wrote[:4])))
        left = reset(repo)
        if left:
            out('')
            out('  STOPPING HERE. The reset after %s --help left %d path(s) '
                'dirty.' % (n, len(left)))
            return 2

    out('')
    out('  swept                     : %d tool(s)' % len(names))
    out('  INTENDED writers          : %d -- declared, with a reason, and their '
        'written paths' % len(intended))
    out('                              checked against what they declared')
    _undeclared = [(n, x) for n, _g, x in intended if x]
    if _undeclared:
        out('  !! DECLARED WRITERS THAT WROTE SOMETHING ELSE: %d'
            % len(_undeclared))
        for n, x in _undeclared:
            out('      %-46s undeclared: %s' % (n, ', '.join(x)))
    out('  WROTE on a bare run       : %d' % len(writes_bare))
    out('  WROTE on --help           : %d' % len(writes_help))
    out('  CHANGED SHARED STATE      : %d -- outside the working tree, so '
        '`git status`' % len(writes_shared))
    out('                              could not have seen any of them')
    for n, sh in writes_shared:
        out('      %-46s %s' % (n, '; '.join(sh[:5])))
    out('  COULD NOT RUN (no verdict): %d -- these are NOT reported as clean'
        % len(could_not))
    for n, why in could_not:
        out('      %-46s %s' % (n, why))
    out('')
    if _undeclared:
        out('A DECLARED WRITER THAT WRITES AN UNDECLARED PATH IS NOT COVERED BY')
        out('THE ALLOWLIST. Update tools/bare_run_writers.py, or find out why the')
        out('path changed.')
        return 1
    if writes_shared:
        out('A BARE RUN MUST NOT TOUCH SHARED STATE, AND NO ALLOWLIST COVERS '
            'THIS.')
        out('tools/bare_run_writers.py declares paths INSIDE the repo. A write')
        out('to the lock registry, to .git/config or to the worktree list')
        out('reaches every other clone on this box, and the session that reads')
        out('it next has no way to tell it came from a sweep.')
        out('')
        out('THIS IS THE CASE THIS TOOL USED TO MISS ENTIRELY. Before '
            '2026-10-08 it')
        out('compared only `git status`, so tools/session_lock_check.py taking a')
        out('lock on a bare run was reported CLEAN.')
        return 1
    if writes_bare or writes_help:
        out('A BARE RUN MUST BE REPORT-ONLY. Each tool above needs an explicit')
        out('write flag, with its bare path printing what it WOULD do.')
        return 1
    if could_not:
        out('No tool wrote, AND %d tool(s) have no verdict at all. That is not '
            'a clean bill.' % len(could_not))
        return 2
    out('Every bare run was report-only.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
