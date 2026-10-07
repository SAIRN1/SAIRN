#!/usr/bin/env python
"""hover2_claim_verify.py -- this role's OWN claim re-derivation tool,
built from scratch for the standing NO BUILDER EXECUTION rule. Re-derives
a build-agent's claimed FACT from a real git object read, never by
running the build agent's own command.

GOAL: given a claim of the shape "at commit C, file F contains/asserts
X" (a line's exact text, a substring's presence, or a regex match
count), re-derive X by reading the file AT THAT COMMIT via `git show
<sha>:<path>` -- a read of a git object, not an execution of any script
-- and report MATCH / MISMATCH / COULD NOT VERIFY. A mismatch is a
finding regardless of what was reported, per the standing instruction.

WHY NOT hover2_claim_reexecute.py (this role's own prior tool, batch I):
that tool's whole mechanism is re-running the CLAIMED COMMAND
(`--cmd "python tools/x.py"`) in this clone, which is exactly a build-
agent tool/test/script invocation -- permitted under the rule standing
when it was built, but NOT under the CURRENT standing instruction's "run
no build-agent tool, test, script, skill or command, for any reason."
That tool is left in place (it is now-correctly-scoped history, not
deleted) but is NOT used this batch, and this new tool exists because the
gap it leaves (verifying a claim with no execution at all) was not
previously built.

NON-GOALS: does not evaluate prose judgment calls ("the fix is
correct-by-design") -- only MECHANICALLY CHECKABLE factual assertions
about a git object's content at a specific commit. Does not check out a
commit into the working tree (git show reads a blob directly, no
checkout, no risk to other sessions' in-progress files). Does not decide
whether a MISMATCH is the build agent's fault or this role's own
mis-transcription of the claim -- that judgment stays with the caller,
same evidence-not-auto-verdict split as every other tool here.

ALTERNATIVES CONSIDERED:
  1. Re-run the build agent's own test/check command -- rejected
     outright, this is the exact NO BUILDER EXECUTION violation this
     tool exists to avoid.
  2. Diff the whole file against the previous commit and eyeball it --
     rejected as the default mode: too coarse for "is this ONE claimed
     fact true", and not scriptable for a selftest or a batch of claims.
     (A raw diff IS available as a secondary read when the one-fact
     check is insufficient -- see --show-diff.)

CROSS-CUTTING: read-only via `git show`/`git cat-file` only -- no
`git checkout`, no executing any file's contents, no subprocess call
to anything other than `git` itself (which is infrastructure, not a
build-agent tool).

Usage:
  python hover2_claim_verify.py --commit SHA --file PATH --line N --expect TEXT [--repo PATH]
  python hover2_claim_verify.py --commit SHA --file PATH --contains TEXT [--repo PATH]
  python hover2_claim_verify.py --commit SHA --file PATH --count-regex PATTERN --expect-count N [--repo PATH]
  python hover2_claim_verify.py --show-diff --commit SHA --file PATH [--repo PATH]
  python hover2_claim_verify.py --selftest
"""
import argparse
import os
import re
import subprocess
import sys


def git_show_blob(repo, commit, path):
    """Reads a file's content AT A SPECIFIC COMMIT via `git show`. This is
    a git-object READ, not an execution of the file's own contents --
    the same distinction this role's other tools already rely on (e.g.
    hover2_exit_capture.py reading a status file it wrote itself)."""
    try:
        out = subprocess.run(
            ['git', '-C', repo, 'show', '%s:%s' % (commit, path)],
            capture_output=True, text=True, encoding='utf-8', errors='replace')
    except FileNotFoundError:
        return None, 'COULD NOT VERIFY: git not found'
    if out.returncode != 0:
        return None, ('COULD NOT VERIFY: git show %s:%s failed -- %s'
                      % (commit, path, (out.stderr or '').strip()[:200]))
    return out.stdout, None


def verify_line(repo, commit, path, line_no, expect):
    content, err = git_show_blob(repo, commit, path)
    if err:
        return 'COULD_NOT_VERIFY', err
    lines = content.splitlines()
    if line_no < 1 or line_no > len(lines):
        return 'COULD_NOT_VERIFY', ('line %d out of range (file has %d lines at this commit)'
                                    % (line_no, len(lines)))
    actual = lines[line_no - 1]
    if expect.strip() == actual.strip():
        return 'MATCH', actual
    return 'MISMATCH', 'claimed %r, actual line %d is %r' % (expect, line_no, actual)


def verify_contains(repo, commit, path, substring):
    content, err = git_show_blob(repo, commit, path)
    if err:
        return 'COULD_NOT_VERIFY', err
    if substring in content:
        return 'MATCH', 'found'
    return 'MISMATCH', 'substring not found in file at this commit'


def verify_count(repo, commit, path, pattern, expect_count):
    content, err = git_show_blob(repo, commit, path)
    if err:
        return 'COULD_NOT_VERIFY', err
    try:
        actual_count = len(re.findall(pattern, content))
    except re.error as e:
        return 'COULD_NOT_VERIFY', 'bad regex: %s' % e
    if actual_count == expect_count:
        return 'MATCH', 'count=%d' % actual_count
    return 'MISMATCH', 'claimed count=%d, actual count=%d' % (expect_count, actual_count)


def selftest():
    repo = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    # KNOWN-TRUE: HEAD's own CLAUDE.md names python, not python3.
    head = subprocess.run(['git', '-C', repo, 'rev-parse', 'HEAD'],
                          capture_output=True, text=True).stdout.strip()
    verdict_true, detail_true = verify_contains(repo, head, 'CLAUDE.md',
                                                "Use `python`")
    # KNOWN-FALSE: a claim about CLAUDE.md that is NOT true at HEAD.
    verdict_false, detail_false = verify_contains(
        repo, head, 'CLAUDE.md', 'THIS STRING DOES NOT EXIST IN CLAUDE MD XQZ')
    ok = (verdict_true == 'MATCH') and (verdict_false == 'MISMATCH')
    print('SELFTEST %s: known-true=%s (%s), known-false=%s (%s)' %
          ('PASS' if ok else 'FAIL', verdict_true, detail_true, verdict_false, detail_false))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit')
    ap.add_argument('--file')
    ap.add_argument('--line', type=int)
    ap.add_argument('--expect')
    ap.add_argument('--contains')
    ap.add_argument('--count-regex')
    ap.add_argument('--expect-count', type=int)
    ap.add_argument('--show-diff', action='store_true')
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.commit or not args.file:
        print('usage: --commit SHA --file PATH [--line N --expect TEXT | '
              '--contains TEXT | --count-regex PATTERN --expect-count N] | --selftest')
        sys.exit(2)

    if args.show_diff:
        out = subprocess.run(
            ['git', '-C', args.repo, 'show', args.commit, '--', args.file],
            capture_output=True, text=True, encoding='utf-8', errors='replace')
        print(out.stdout if out.returncode == 0 else 'COULD NOT RUN: %s' % out.stderr)
        sys.exit(0 if out.returncode == 0 else 2)

    if args.line is not None and args.expect is not None:
        verdict, detail = verify_line(args.repo, args.commit, args.file, args.line, args.expect)
    elif args.contains is not None:
        verdict, detail = verify_contains(args.repo, args.commit, args.file, args.contains)
    elif args.count_regex is not None and args.expect_count is not None:
        verdict, detail = verify_count(args.repo, args.commit, args.file,
                                       args.count_regex, args.expect_count)
    else:
        print('usage: one of --line+--expect, --contains, or --count-regex+--expect-count')
        sys.exit(2)

    print('%s: %s' % (verdict, detail))
    sys.exit({'MATCH': 0, 'MISMATCH': 1, 'COULD_NOT_VERIFY': 2}[verdict])


if __name__ == '__main__':
    main()
