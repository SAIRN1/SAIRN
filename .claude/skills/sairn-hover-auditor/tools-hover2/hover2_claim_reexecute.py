#!/usr/bin/env python
"""hover2_claim_reexecute.py -- re-run a build agent's CLAIMED check/test
result from its recorded inputs, in this role's own environment, and report
MATCH / MISMATCH / COULD NOT RUN. Never folds the third into either of the
first two (PR 1.11).

GOALS: given a build-agent's claimed command + claimed exit code + claimed
output substring(s), re-run the SAME command for real and compare -- a
mismatch is a finding regardless of what was reported. Also detect SOURCE
DRIFT (a cited file has changed since the claim) so a MISMATCH is told
apart from "the code moved on since the claim" rather than silently read
as "the claim was wrong."

NON-GOALS: does not check out a historical commit and run the command
against that exact tree -- this repo moves fast (multiple sessions pushing
continuously) and checking out a past commit in the live working clone
would be destructive against other sessions' in-progress files. Runs the
cited command AT CURRENT HEAD instead, with drift reported separately.
Does not itself decide whether a MISMATCH is the build agent's fault or
drift -- that judgment is this role's own, informed by the drift notes
this tool prints, same split as every other tool this role has built
(evidence, not auto-verdict).

ALTERNATIVES CONSIDERED:
  1. Check out the historical commit in a throwaway worktree and run
     there -- rejected as unnecessary weight for THIS purpose: the
     question a re-execution answers is "does the claim hold NOW", and a
     worktree checkout adds disk/setup cost without changing that answer
     (drift is reported either way via blob-sha comparison, cheaper).
  2. Trust the harness's own completion status instead of a real
     subprocess exit code -- rejected outright, this is the Rule E shape.

CROSS-CUTTING: this role's OWN exit-code recorder
(hover2_exit_capture.py), not tools/capture_exit.py (cody's) -- CORRECTED
2026-10-06 per the standing-instruction correction this same batch. The
line naming cody's tool was in this docstring's ADVICE only; the code
below never called it (checked, not assumed).

EXIT CODE OF THIS TOOL ITSELF: 0 = MATCH, 1 = MISMATCH, 2 = COULD NOT RUN
(bad arguments, the cited command itself could not be launched, or git
could not answer the drift question).

USAGE:
    python hover2_claim_reexecute.py --check --cmd "python tools/x.py" \\
        --claimed-exit 0 --claimed-contains "ALL ARMS PASS" \\
        --commit <sha> --source tools/x.py:<blob-sha-at-claim-time>

    python hover2_claim_reexecute.py --selftest
"""
import argparse
import subprocess
import sys


def _git(repo, *args):
    r = subprocess.run(('git', '-C', repo) + args, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()


def blob_sha(repo, path, ref='HEAD'):
    """The git blob sha for `path` at `ref`, or None if it cannot be read --
    COULD NOT RUN is this function's third state too, not a guess of ''."""
    rc, out, _err = _git(repo, 'rev-parse', '%s:%s' % (ref, path))
    if rc != 0:
        return None
    return out.strip()


def run_claimed_command(cmd, timeout=600):
    """Runs `cmd` as a real subprocess (shell=True, same as a human pasting
    it), returns (rc_or_None, stdout, stderr). rc is None only on a timeout
    or a launch failure -- never silently coerced to 0 or 1."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
        # shell=True means "command not found" is the SHELL's own exit code,
        # not a Python OSError -- found by this tool's own selftest, which
        # claimed exit 0 for a nonexistent binary and got a real MISMATCH (1)
        # instead of the COULD-NOT-LAUNCH case this branch exists to catch.
        # THE EXIT CODE FOR "NOT FOUND" IS NOT ONE NUMBER: bash reports 127,
        # cmd.exe (what Python's shell=True actually invokes on THIS Windows
        # host, confirmed by driving it directly rather than assumed from
        # the platform name) reports 1 with a DIFFERENT phrase. So the
        # phrase is the real signal, checked on both known wordings, not the
        # exit code -- and a real tool's own exit 1 is never mistaken for
        # this unless it HAPPENS to print one of these two exact phrases.
        _stderr_l = (r.stderr or '').lower()
        if ('not recognized as an internal or external command' in _stderr_l
                or ('command not found' in _stderr_l and r.returncode == 127)):
            return None, r.stdout or '', 'LAUNCH FAILED (shell could not find the command): %s' % (r.stderr or '').strip()
        return r.returncode, r.stdout or '', r.stderr or ''
    except subprocess.TimeoutExpired:
        return None, '', 'TIMEOUT after %ds' % timeout
    except OSError as e:
        return None, '', 'LAUNCH FAILED: %s' % e


def check(args):
    drift_notes = []
    for s in (args.source or []):
        if ':' not in s:
            print('COULD NOT RUN: --source %r must be path:blobsha' % s)
            return 2
        path, claimed_sha = s.split(':', 1)
        now_sha = blob_sha(args.repo, path)
        if now_sha is None:
            drift_notes.append('%s: COULD NOT READ at current HEAD (deleted, '
                               'or not tracked, or git failed)' % path)
        elif now_sha != claimed_sha:
            drift_notes.append('%s: DRIFTED -- claimed %s, now %s'
                               % (path, claimed_sha[:12], now_sha[:12]))
        else:
            drift_notes.append('%s: unchanged since the claim' % path)

    rc, out, err = run_claimed_command(args.cmd, timeout=args.timeout)
    if rc is None:
        print('COULD NOT RUN: %s' % err)
        for d in drift_notes:
            print('  drift: %s' % d)
        return 2

    exit_ok = (args.claimed_exit is None) or (rc == args.claimed_exit)
    missing = [c for c in (args.claimed_contains or []) if c not in out]
    content_ok = not missing

    print('COMMAND : %s' % args.cmd)
    if args.commit:
        print('CLAIMED COMMIT : %s' % args.commit)
    print('CLAIMED EXIT : %r   REAL EXIT : %d   %s'
         % (args.claimed_exit, rc, 'MATCH' if exit_ok else 'MISMATCH'))
    if args.claimed_contains:
        print('CLAIMED OUTPUT SUBSTRING(S) : %s'
             % (' | MATCH, all present' if content_ok
                else ' | MISMATCH, missing: %s' % missing))
    for d in drift_notes:
        print('  source : %s' % d)

    if exit_ok and content_ok:
        print('VERDICT: MATCH')
        return 0
    print('VERDICT: MISMATCH')
    return 1


def selftest():
    cases = 0
    failed = 0

    def case(label, ok):
        nonlocal cases, failed
        cases += 1
        print(('  ok   ' if ok else '  FAIL ') + label)
        if not ok:
            failed += 1

    # 1. A command whose real exit matches a true claim -> MATCH.
    class A:
        cmd = 'python -c "import sys; sys.exit(0)"'
        claimed_exit = 0
        claimed_contains = None
        commit = None
        source = None
        repo = '.'
        timeout = 10
    rc = check(A())
    case('a correctly-claimed exit 0 reports MATCH (tool exit 0)', rc == 0)

    # 2. A command whose real exit CONTRADICTS the claim -> MISMATCH.
    class B:
        cmd = 'python -c "import sys; sys.exit(1)"'
        claimed_exit = 0
        claimed_contains = None
        commit = None
        source = None
        repo = '.'
        timeout = 10
    rc = check(B())
    case('a falsely-claimed exit 0 (real exit 1) reports MISMATCH (tool exit 1)', rc == 1)

    # 3. A claimed output substring that is genuinely present -> MATCH.
    class C:
        cmd = 'python -c "print(\'HELLO WORLD\')"'
        claimed_exit = 0
        claimed_contains = ['HELLO']
        commit = None
        source = None
        repo = '.'
        timeout = 10
    rc = check(C())
    case('a real, present output substring reports MATCH', rc == 0)

    # 4. A claimed output substring that is NOT present -> MISMATCH, not silently passed.
    class D:
        cmd = 'python -c "print(\'HELLO WORLD\')"'
        claimed_exit = 0
        claimed_contains = ['GOODBYE']
        commit = None
        source = None
        repo = '.'
        timeout = 10
    rc = check(D())
    case('a claimed substring that never appears reports MISMATCH, not MATCH', rc == 1)

    # 5. A command that cannot launch -> COULD NOT RUN (2), never folded into MATCH or MISMATCH.
    class E:
        cmd = 'this-binary-does-not-exist-anywhere --flag'
        claimed_exit = 0
        claimed_contains = None
        commit = None
        source = None
        repo = '.'
        timeout = 10
    rc = check(E())
    case('an unlaunchable command reports COULD NOT RUN (tool exit 2), not 0 or 1', rc == 2)

    # 6. blob_sha on a real, tracked file in THIS repo returns a real sha,
    #    and a wrong claimed sha is reported as DRIFTED, not silently accepted.
    real_sha = blob_sha('.', 'tools/sairn_claim.py')
    case('blob_sha resolves a real tracked file to a real sha', bool(real_sha))
    if real_sha:
        class F:
            cmd = 'python -c "import sys; sys.exit(0)"'
            claimed_exit = 0
            claimed_contains = None
            commit = 'selftest'
            source = ['tools/sairn_claim.py:0000000000000000000000000000000000000000']
            repo = '.'
            timeout = 10
        import io
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            check(F())
        finally:
            sys.stdout = old
        case('a deliberately-wrong claimed blob sha is reported as DRIFTED',
            'DRIFTED' in buf.getvalue())

    print('')
    print('%d case(s), %d failed' % (cases, failed))
    return 1 if failed else 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--cmd')
    ap.add_argument('--claimed-exit', type=int)
    ap.add_argument('--claimed-contains', action='append')
    ap.add_argument('--commit')
    ap.add_argument('--source', action='append',
                    help='path:blobsha, repeatable -- the file(s) the claim '
                         'was read against, to detect drift since the claim')
    ap.add_argument('--repo', default='.')
    ap.add_argument('--timeout', type=int, default=600)
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.check:
        if not args.cmd:
            sys.stderr.write('--cmd is required with --check\n')
            return 2
        return check(args)
    sys.stderr.write('nothing to do -- pass --check or --selftest\n')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
