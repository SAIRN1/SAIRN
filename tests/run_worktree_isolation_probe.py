#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""run_worktree_isolation_probe.py -- the control for tools/git_config_isolation.py.

Subject: tools/git_config_isolation.py. This probe exists because the subject
carries its own --selftest, and a selftest's verdict is worthless if it never
reaches the exit code -- which is the exact defect family this batch is about
(docs/2026-10-13-cody-b6-methodology-unproven.md). So every arm here drives the
REAL CLI in a SUBPROCESS and reads the real exit code, one per line.

IT NEVER MUTATES THE LIVE CLONE, and arm 2 proves that rather than promising it:
the live .git/config sha and .git/worktrees listing are measured before and
after a guarded run and must be identical. Every arm that needs a WRITE does it
in a throwaway clone under tempfile.mkdtemp.

EXIT 0 all arms held / 1 an arm failed / 2 the subject is absent or unreadable
/ 3 an arm could not be evaluated.
"""

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

CRITERIA_VERSION = '2026-10-13.1'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'git_config_isolation.py')

passed = failed = 0
FAILED = []
UNPROVEN = []


def arm(name, fn):
    global passed, failed
    try:
        fn()
        print('  ok    %s' % name)
        passed += 1
    except AssertionError as exc:
        print('  FAIL  %s\n        %s' % (name, exc))
        failed += 1
        FAILED.append(name)
    except Exception as exc:                      # noqa: BLE001 -- see below
        # NOT folded into a pass and NOT folded into a failure. An arm that
        # could not be evaluated is a third state, counted in the summary and
        # carried into the exit code, which is the rule
        # tools/unproven_arm_check.py enforces on everything else in tests/.
        print('  UNPROVEN  %s\n        could not be evaluated: %s'
              % (name, exc))
        UNPROVEN.append(name)


def live_snapshot():
    g = os.path.join(REPO, '.git')
    with open(os.path.join(g, 'config'), 'rb') as fh:
        cfg = fh.read()
    wtd = os.path.join(g, 'worktrees')
    wt = sorted(os.listdir(wtd)) if os.path.isdir(wtd) else []
    return hashlib.sha256(cfg).hexdigest(), len(cfg), wt


def run(args, cwd=REPO):
    p = subprocess.run([sys.executable, TOOL] + args, cwd=cwd,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def mk_clone():
    """A throwaway git repo. Nothing here is ever the live clone."""
    tmp = tempfile.mkdtemp(prefix='wt_iso_probe_')
    r = os.path.join(tmp, 'r')
    os.makedirs(r)

    def g(*a):
        return subprocess.run(['git'] + list(a), cwd=r,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    g('init', '-q', '.')
    g('config', 'user.email', 'probe@example.invalid')
    g('config', 'user.name', 'probe')
    with io.open(os.path.join(r, 'a.txt'), 'w', encoding='utf-8') as fh:
        fh.write('hi\n')
    g('add', 'a.txt')
    g('commit', '-q', '-m', 'init')
    return tmp, r


def main():
    print('WORKTREE / GIT-CONFIG ISOLATION PROBE -- criteria %s'
          % CRITERIA_VERSION)
    print('  subject: tools/git_config_isolation.py')
    print('  the live clone is MEASURED, never written. Every write arm runs')
    print('  in tempfile.mkdtemp.')
    print('')

    if not os.path.isfile(TOOL):
        print('COULD NOT RUN: %s is absent. A probe with no subject reports 2,'
              % TOOL)
        print('not a pass -- folding a missing subject into a clean result is')
        print('the defect this batch exists to stop.')
        return 2

    def selftest_verdict_reaches_the_exit_code():
        rc, out = run(['--selftest'])
        m = re.search(r'(\d+) passed, (\d+) failed', out)
        assert m, ('the selftest printed no summary line this probe can read:\n'
                   '%s' % out[-800:])
        p, f = int(m.group(1)), int(m.group(2))
        assert p >= 8, 'only %d arm(s) ran in the subject selftest' % p
        assert f == 0, '%d selftest arm(s) failed:\n%s' % (f, out[-1500:])
        assert rc == 0, ('the selftest printed "%d passed, %d failed" and then '
                         'exited %d. A verdict that does not reach the exit '
                         'code is the b5 defect exactly.' % (p, f, rc))
    arm('1. the subject --selftest verdict REACHES its exit code (>=8 arms, 0 '
        'failed, rc 0)', selftest_verdict_reaches_the_exit_code)

    def live_clone_untouched_by_a_guarded_run():
        before = live_snapshot()
        rc, out = run(['--', 'git', 'status', '--porcelain'])
        after = live_snapshot()
        assert rc == 0, ('a read-only guarded run over the LIVE clone returned '
                         '%d:\n%s' % (rc, out[-900:]))
        assert before == after, (
            'THE LIVE CLONE CHANGED during a read-only guarded run.\n'
            '  config sha %s -> %s\n  config bytes %d -> %d\n'
            '  worktrees %r -> %r'
            % (before[0][:12], after[0][:12], before[1], after[1],
               before[2], after[2]))
        print('        live .git/config %s (%d bytes), worktrees %s -- '
              'identical after'
              % (before[0][:12], before[1], before[2] or '(none)'))
    arm('2. the LIVE clone is byte-identical after a guarded read-only run',
        live_clone_untouched_by_a_guarded_run)

    def the_measurement_can_detect_a_change():
        # WITHOUT THIS ARM, ARM 2 IS VACUOUS. If live_snapshot() could not see
        # a difference, "identical after" would pass whatever happened. Proved
        # on a throwaway clone with the same comparison arm 2 uses.
        tmp, r = mk_clone()
        try:
            g = os.path.join(r, '.git')
            def snap():
                with open(os.path.join(g, 'config'), 'rb') as fh:
                    cfg = fh.read()
                wtd = os.path.join(g, 'worktrees')
                return (hashlib.sha256(cfg).hexdigest(), len(cfg),
                        sorted(os.listdir(wtd)) if os.path.isdir(wtd) else [])
            b = snap()
            subprocess.run(['git', '-C', r, 'config', 'sairn.planted', 'yes'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            a = snap()
            assert b != a, ('the same comparison arm 2 relies on did NOT see '
                            'an unguarded `git config` write, so arm 2 proves '
                            'nothing')
            assert b[0] != a[0], 'the config sha did not move: %r vs %r' % (b, a)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    arm('3. CONTROL -- that same measurement DOES detect an unguarded write '
        '(so arm 2 is not vacuous)', the_measurement_can_detect_a_change)

    def a_write_through_the_guard_is_a_finding():
        tmp, r = mk_clone()
        try:
            rc, out = run(['--repo', r, '--', 'git', 'config',
                           'sairn.planted', 'yes'], cwd=r)
            assert rc == 1, ('a guarded command that wrote .git/config '
                             'returned %d; 1 is the finding code.\n%s'
                             % (rc, out[-900:]))
            assert 'RESTORED' in out, ('the guard reported the change but the '
                                       'output never says it put the bytes '
                                       'back:\n%s' % out[-900:])
            with open(os.path.join(r, '.git', 'config'), 'rb') as fh:
                assert b'sairn.planted' not in fh.read() and \
                       b'planted' not in fh.read(), \
                    'the planted key survived restoration'
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    arm('4. a .git/config write THROUGH the guard is exit 1 and is restored',
        a_write_through_the_guard_is_a_finding)

    def a_worktree_add_through_the_guard_is_cleaned():
        tmp, r = mk_clone()
        try:
            wt = os.path.join(tmp, 'wt')
            rc, out = run(['--repo', r, '--', 'git', 'worktree', 'add', '-q',
                           '--detach', wt, 'HEAD'], cwd=r)
            assert rc == 1, ('a guarded `worktree add` returned %d:\n%s'
                             % (rc, out[-900:]))
            wtd = os.path.join(r, '.git', 'worktrees')
            left = sorted(os.listdir(wtd)) if os.path.isdir(wtd) else []
            assert left == [], ('a worktree administrative entry was left '
                               'behind: %r. A stale entry is what makes the '
                               'NEXT `worktree add` refuse, which is how one '
                               'dead probe blocks an unrelated run.' % left)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    arm('5. a `worktree add` THROUGH the guard is exit 1 and .git/worktrees is '
        'cleaned', a_worktree_add_through_the_guard_is_cleaned)

    def no_command_is_could_not_run():
        rc, out = run([])
        assert rc == 2, ('the wrapper with nothing to wrap returned %d. A '
                         'wrapper that reports 0 when it guarded nothing is '
                         'the fold this repo refuses everywhere.\n%s'
                         % (rc, out[-500:]))
    arm('6. the wrapper with NO command is exit 2 COULD NOT RUN',
        no_command_is_could_not_run)

    def the_premise_is_stated_as_measured():
        # The brief for this item said the worktree probes corrupt
        # .git/config. MEASURED, THEY DO NOT -- `worktree add` leaves
        # .git/config byte-identical and creates .git/worktrees/<name>. This
        # arm pins that measurement so the correction cannot quietly rot back
        # into the original wording.
        tmp, r = mk_clone()
        try:
            g = os.path.join(r, '.git')
            with open(os.path.join(g, 'config'), 'rb') as fh:
                before = hashlib.sha256(fh.read()).hexdigest()
            wt = os.path.join(tmp, 'wt_premise')
            subprocess.run(['git', '-C', r, 'worktree', 'add', '-q',
                            '--detach', wt, 'HEAD'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with open(os.path.join(g, 'config'), 'rb') as fh:
                after = hashlib.sha256(fh.read()).hexdigest()
            wtd = os.path.join(g, 'worktrees')
            entries = sorted(os.listdir(wtd)) if os.path.isdir(wtd) else []
            assert before == after, (
                'ON THIS GIT VERSION `worktree add` DID change .git/config. '
                'That contradicts the measurement this tool was designed '
                'around and the design note must be corrected, not this arm.')
            assert entries, ('`worktree add` created no .git/worktrees entry '
                             'either, so neither half of the premise holds and '
                             'the mechanism is something this guard does not '
                             'snapshot')
            print('        confirmed: .git/config unchanged, .git/worktrees '
                  'gained %s' % ' '.join(entries))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    arm('7. THE PREMISE, pinned -- `worktree add` does NOT touch .git/config; '
        'it writes .git/worktrees', the_premise_is_stated_as_measured)

    def the_adoption_queue_is_still_the_same_files():
        # The routing note names the tools that run `worktree add` against the
        # LIVE repo. DERIVED by reading tools/, not transcribed, so the note
        # cannot go stale without this arm saying so.
        hits = []
        tdir = os.path.join(REPO, 'tools')
        for fn in sorted(os.listdir(tdir)):
            if not fn.endswith('.py'):
                continue
            p = os.path.join(tdir, fn)
            try:
                with io.open(p, encoding='utf-8', errors='replace') as fh:
                    src = fh.read()
            except OSError:
                continue
            for m in re.finditer(r"'worktree',\s*'add'", src):
                seg = src[max(0, m.start() - 160):m.start()]
                if 'REPO' in seg or "'-C', repo" in seg:
                    hits.append(fn)
                    break
        hits = sorted(set(hits))
        assert hits, ('no tool was found running `worktree add` against the '
                      'live repo. If that is now true the adoption queue is '
                      'empty and this arm should be retired deliberately, not '
                      'left passing on an anchor that stopped matching.')
        print('        adoption queue, derived: %s' % ' '.join(hits))
        expected = {'condition_coverage.py', 'dead_rule_sweep.py',
                    'guard_ablation.py'}
        extra = set(hits) - expected
        missing = expected - set(hits)
        assert not missing, ('a tool that used to drive the live repo no '
                             'longer does, or the anchor rotted: %s'
                             % ' '.join(sorted(missing)))
        if extra:
            print('        NEW since the routing note was written: %s'
                  % ' '.join(sorted(extra)))
    arm('8. the adoption queue is DERIVED from tools/ and still contains the '
        'three named', the_adoption_queue_is_still_the_same_files)

    def the_three_tools_refuse_a_bare_live_run():
        # THE ADOPTION, DRIVEN. Each of the three now calls
        # require_isolation() before its `worktree add`, so a bare run against
        # the live clone must exit 2 and must create nothing. MEASURED BEFORE
        # THE GUARD EXISTED: `python tools/guard_ablation.py --help` created
        # .git/worktrees/sairn-abl-8c6o2uub in this clone and LEFT IT THERE
        # when the run was killed -- git status never showed it, and prune
        # would not take it while its temp directory survived.
        before = live_snapshot()
        bad = []
        for tool in ('condition_coverage.py', 'guard_ablation.py'):
            proc = subprocess.run(
                [sys.executable, os.path.join(REPO, 'tools', tool)],
                cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=180)
            out = proc.stdout.decode('utf-8', 'replace')
            if proc.returncode != 2:
                bad.append('%s exited %d, not 2' % (tool, proc.returncode))
            elif 'COULD NOT RUN -- ' not in out:
                bad.append('%s exited 2 without naming the guard' % tool)
        after = live_snapshot()
        assert not bad, '; '.join(bad)
        assert before == after, (
            'a REFUSED bare run still changed the live clone: %r -> %r'
            % (before, after))
        print('        both refused with exit 2; live .git unchanged')
    arm('9. ADOPTION -- a bare live run of the guarded tools is exit 2 and creates nothing',
        the_three_tools_refuse_a_bare_live_run)

    def dead_rule_sweep_help_still_works():
        # THE GUARD MUST NOT BREAK WHAT ALREADY WORKED. dead_rule_sweep.py
        # handles --help in argparse before it reaches the worktree, so it
        # must still print usage and exit 0. If this ever flips to 2 the guard
        # has been moved above the argument parser and is refusing a read-only
        # invocation, which is how a guard gets removed instead of fixed.
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, 'tools', 'dead_rule_sweep.py'),
             '--help'], cwd=REPO, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=180)
        out = proc.stdout.decode('utf-8', 'replace')
        assert proc.returncode == 0, ('dead_rule_sweep.py --help exited %d: %s'
                                      % (proc.returncode, out[-400:]))
        assert 'usage:' in out, 'no usage line in --help output'
    arm('10. the guard does NOT refuse dead_rule_sweep.py --help (exit 0, usage printed)',
        dead_rule_sweep_help_still_works)

    print('')
    if FAILED:
        print('%d ARM(S) FAILED:' % len(FAILED))
        for n in FAILED:
            print('  - %s' % n)
    if UNPROVEN:
        print('%d ARM(S) COULD NOT BE EVALUATED:' % len(UNPROVEN))
        for n in UNPROVEN:
            print('  - %s' % n)
    print('%d passed, %d failed, %d unproven'
          % (passed, failed, len(UNPROVEN)))
    if UNPROVEN:
        print('EXIT 3: an arm was not evaluated, so this run is not a pass.')
        return 3
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
