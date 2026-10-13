#!/usr/bin/env python
# OWNER: fourth
r"""temp_state_leak_check.py -- did a probe leave its scaffolding in .git/config?

    python tools/temp_state_leak_check.py --probe tests/push_gate/check8_probe.py
    python tools/temp_state_leak_check.py --snapshot before.json
    python tools/temp_state_leak_check.py --compare  before.json
    python tools/temp_state_leak_check.py --fixtures        # the control pair
    python tools/temp_state_leak_check.py --status          # print, compare nothing

Exit 0 nothing leaked; 1 something did; 2 COULD NOT RUN -- never folded into
either of the other two.

REPORT ONLY, AND THAT IS A DESIGN DECISION RATHER THAN A STAGE. It is wired to
no hook and no gate. A check that BLOCKS on a probe's leftovers would stop a
session mid-run over a condition it can fix in one command, and the thing worth
having first is the NAME of the probe that leaks. If a leak class turns out to
be chronic, promoting this is one line in settings.json -- but promoting a
checker nobody has read output from is how a gate arrives already distrusted.

── WHY .git/config AND NOT THE WORKING TREE ───────────────────────────────────
The working tree has watchers: `git status` is in every gate, every suite driver
digests it, and b5 and b6 both caught sabotaged files that way. `.git/config`
has NONE of that. `git status` cannot see it, a dirty-tree check passes while it
is wrong, and the platform has already paid twice for exactly that blindness:

  core.bare = true    tests/push_gate/check8_probe.py:209 records it in its own
                      comment -- "first dry-run push was reliably leaving
                      core.bare = true behind". MEASURED LIVE in b5: with it set,
                      `git status` exits 128, every `git checkout --` restore
                      fails SILENTLY, and two live API files were left
                      sabotaged, one of them not parsing. The detector that
                      exists, tools/clone_health_check.py:209-211, reports and
                      nothing refuses on it.
  user.email          a probe that commits needs an identity. If it sets one at
                      the repo level and does not unset it, every later commit
                      in the clone is attributed to `probe@local` -- and the
                      attribution is the only thing tying a defect record to a
                      session.
  worktree entries    a probe that adds a worktree and dies leaves a registration
                      pointing at a directory that is gone. b6 cleared two.

FOUR FACTS, chosen because each one is invisible to `git status` and each has a
recorded instance. This is not a general config differ: a general differ over a
file people legitimately edit produces noise, and noise is how a report-only
check stops being read.

── WHAT IT CANNOT SEE, stated rather than discovered later ────────────────────
  * A probe that leaks and then restores before this runs. It compares two
    points in time, not the interval between them.
  * A leak in the GLOBAL git config. Deliberate: a repo-level check that
    silently started reporting machine-level state would be answering a
    different question from the one its name asks.
  * Anything in .git/ that is not config -- hooks, refs, the index.
  * WHETHER A CHANGE IS WRONG. `core.bare=true` is correct in a bare clone. It
    reports a CHANGE ACROSS A PROBE, which is a different claim from "this value
    is bad", and the two must not be confused.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

CRITERIA_VERSION = '2026-10-14.1'
OK, LEAK, CANT = 0, 1, 2
BAD_EMAIL_MARKERS = ('probe@local', 'probe@', 'test@local', 'fixture@')


def git(args, repo=None):
    cmd = ['git'] + (['-C', repo] if repo else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()


def snapshot(repo=None):
    """The four facts. A value that cannot be read is None, never ''."""
    out = {}
    for key in ('core.bare', 'user.name', 'user.email'):
        rc, so, _ = git(['config', '--local', '--get', key], repo)
        out[key] = so if rc == 0 else None
    rc, so, _ = git(['worktree', 'list', '--porcelain'], repo)
    if rc != 0:
        out['worktrees'] = None
    else:
        out['worktrees'] = sorted(l.split(' ', 1)[1] for l in so.split('\n')
                                  if l.startswith('worktree '))
    return out


def judge(before, after):
    """-> (exit, [finding, ...]). Never raises."""
    find = []
    if before is None or after is None:
        return CANT, ['one of the two snapshots is missing']
    for key in ('core.bare', 'user.name', 'user.email'):
        b, a = before.get(key), after.get(key)
        if b != a:
            find.append('%s CHANGED across the probe: %r -> %r' % (key, b, a))
    email = after.get('user.email') or ''
    if any(m in email.lower() for m in BAD_EMAIL_MARKERS):
        find.append('user.email is a PROBE IDENTITY (%r). Every commit made in '
                    'this clone from now on is attributed to it.' % email)
    bw = before.get('worktrees')
    aw = after.get('worktrees')
    if bw is None or aw is None:
        find.append('worktree list COULD NOT BE READ on one side -- not folded '
                    'into a pass')
        return CANT, find
    added = [w for w in aw if w not in bw]
    gone = [w for w in bw if w not in aw]
    for w in added:
        find.append('worktree ADDED and not removed: %s%s'
                    % (w, '' if os.path.isdir(w) else '   (and the directory '
                       'does not exist -- a registration pointing at nothing)'))
    for w in gone:
        find.append('worktree REMOVED across the probe: %s' % w)
    if any('COULD NOT' in f for f in find):
        return CANT, find
    return (LEAK if find else OK), find


def report(before, after, label):
    code, find = judge(before, after)
    print('temp-state leak check -- criteria %s   %s' % (CRITERIA_VERSION, label))
    for k in ('core.bare', 'user.name', 'user.email'):
        print('  %-12s %r -> %r' % (k, before.get(k), after.get(k)))
    print('  %-12s %d -> %d' % ('worktrees', len(before.get('worktrees') or []),
                                len(after.get('worktrees') or [])))
    print()
    if not find:
        print('  NO LEAK. The four facts are unchanged across the probe.')
    for f in find:
        print('  ! %s' % f)
    print()
    print('EXIT %d   (0 clean, 1 leaked, 2 could not run). REPORT ONLY -- this is '
          'wired to no hook and no gate.' % code)
    return code


# ── THE CONTROL PAIR ───────────────────────────────────────────────────────
def fixtures():
    """Plant a leak -> it must fire. Plant nothing -> it must be silent.

    In a THROWAWAY repo. A control that mutated the live clone to prove a
    checker works would be the defect the checker is about.
    """
    arms = []

    def arm(name, got, want):
        arms.append((name, got == want, got, want))

    d = tempfile.mkdtemp(prefix='tempstate-')
    repo = os.path.join(d, 'r')
    os.makedirs(repo)
    for a in (['init', '-q'], ['config', 'user.name', 'Real Name'],
              ['config', 'user.email', 'real@example.invalid']):
        git(a, repo)
    io.open(os.path.join(repo, 'a.txt'), 'w').write('x\n')
    git(['add', '-A'], repo)
    git(['commit', '-q', '-m', 'base'], repo)

    base = snapshot(repo)
    arm('the fixture repo reads back its own config',
        base['user.email'], 'real@example.invalid')

    # ── NEGATIVE HALF FIRST: nothing planted, must be SILENT ──────────────
    arm('CLEAN: no change -> exit 0', judge(base, snapshot(repo))[0], OK)
    arm('CLEAN: and it reports no findings', judge(base, snapshot(repo))[1], [])

    # ── core.bare ────────────────────────────────────────────────────────
    git(['config', 'core.bare', 'true'], repo)
    code, find = judge(base, snapshot(repo))
    arm('LEAK core.bare=true -> exit 1', code, LEAK)
    arm('...and it NAMES core.bare',
        any('core.bare' in f for f in find), True)
    git(['config', 'core.bare', 'false'], repo)

    # ── probe identity ───────────────────────────────────────────────────
    git(['config', 'user.email', 'probe@local'], repo)
    code, find = judge(base, snapshot(repo))
    arm('LEAK user.email=probe@local -> exit 1', code, LEAK)
    arm('...and it says the identity is a PROBE one, not just changed',
        any('PROBE IDENTITY' in f for f in find), True)
    git(['config', 'user.email', 'real@example.invalid'], repo)
    arm('restoring the email clears it', judge(base, snapshot(repo))[0], OK)

    # ── user.name ────────────────────────────────────────────────────────
    git(['config', 'user.name', 'probe'], repo)
    arm('LEAK user.name changed -> exit 1', judge(base, snapshot(repo))[0], LEAK)
    git(['config', 'user.name', 'Real Name'], repo)

    # ── worktree ─────────────────────────────────────────────────────────
    wt = os.path.join(d, 'wt')
    rc, so, se = git(['worktree', 'add', '-q', '--detach', wt], repo)
    if rc == 0:
        code, find = judge(base, snapshot(repo))
        arm('LEAK a worktree added and left -> exit 1', code, LEAK)
        # NORMALISED, because `git worktree list --porcelain` prints its own
        # spelling of the path -- forward slashes on Windows where the caller
        # passed backslashes. The first version of this arm compared the raw
        # strings and failed against CORRECT output, which would have been a
        # control reporting a defect in the thing it is controlling.
        def norm(s):
            return s.replace('\\', '/').lower()
        arm('...and it NAMES the directory',
            any(norm(wt) in norm(f) for f in find), True)
        git(['worktree', 'remove', '--force', wt], repo)
        arm('removing it clears the finding', judge(base, snapshot(repo))[0], OK)
    else:
        arm('worktree arms COULD NOT RUN (%s) -- reported, not skipped silently'
            % (se or rc)[:40], 'could-not-run', 'could-not-run')

    # ── the third state ──────────────────────────────────────────────────
    arm('a missing snapshot is COULD NOT RUN, not a pass', judge(base, None)[0], CANT)
    arm('an unreadable worktree list is COULD NOT RUN',
        judge(base, dict(base, worktrees=None))[0], CANT)

    print('temp_state_leak_check --fixtures   criteria %s' % CRITERIA_VERSION)
    bad = [a for a in arms if not a[1]]
    for name, good, got, want in arms:
        print('  %-4s %s%s' % ('ok' if good else 'FAIL', name,
                               '' if good else '   got %r want %r' % (got, want)))
    print('\n%d arm(s), %d failed' % (len(arms), len(bad)))
    print('BOTH DIRECTIONS: %d planted-leak arm(s) fired, and the clean arms were '
          'silent. A checker only shown the broken case cannot show it is not '
          'simply always failing.'
          % sum(1 for a in arms if a[0].startswith('LEAK')))
    return 0 if not bad else 1


def main(argv):
    if not argv or '--help' in argv:
        print(__doc__)
        return CANT
    if argv[0] == '--fixtures':
        return fixtures()
    if argv[0] == '--status':
        s = snapshot()
        print(json.dumps(s, indent=1))
        return OK
    if argv[0] == '--snapshot':
        if len(argv) < 2:
            print('COULD NOT RUN: --snapshot needs a path')
            return CANT
        io.open(argv[1], 'w', encoding='utf-8').write(json.dumps(snapshot(), indent=1))
        print('snapshot written: %s' % argv[1])
        return OK
    if argv[0] == '--compare':
        if len(argv) < 2 or not os.path.isfile(argv[1]):
            print('COULD NOT RUN: --compare needs an existing snapshot path')
            return CANT
        before = json.load(io.open(argv[1], encoding='utf-8'))
        return report(before, snapshot(), 'compared against %s' % argv[1])
    if argv[0] == '--probe':
        if len(argv) < 2:
            print('COULD NOT RUN: --probe needs a suite path')
            return CANT
        suite = argv[1]
        if not os.path.isfile(suite):
            print('COULD NOT RUN: %s does not exist' % suite)
            return CANT
        before = snapshot()
        cmd = ['python', suite] if suite.endswith('.py') else ['node', suite]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = None
        after = snapshot()
        print('probe: %s   exit %s' % (suite, rc))
        return report(before, after, 'across %s' % suite)
    print('COULD NOT RUN: unknown option %r' % argv[0])
    return CANT


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
