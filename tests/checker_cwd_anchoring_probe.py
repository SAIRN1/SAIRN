"""Four checkers defaulted to a glob relative to the CURRENT DIRECTORY, so
running any of them from anywhere but the repo root scanned nothing and said so
in a way that reads like good news.

    python tests/checker_cwd_anchoring_probe.py

WHY THIS EXISTS. The tools/ half of the self-referential-guard sweep
(docs/2026-09-10-self-referential-guard-sweep.md) asked one question of every
checker: if its subject list went empty, would anyone find out? For this group
the list went empty for a reason NOBODY CHOSE -- not a deleted file, just a
different working directory -- and the answer was no:

    tools/write_without_readback_check.py   empty table, `none`, `none`, exit 0
    tools/sairn_seam_check.py               `0 clean, 0 not-forwarded, 0 could-not-tell`
    tools/sairn_stale_snapshot_scan.py      `0 UTC | 0 stale-snapshot | 0 re-read`
    tools/sairn_strict_args_check.py        `clean -- no ... sites` / `in 0 file(s)`

THE TRIGGER IS NOT HYPOTHETICAL. On 2026-09-10 a single `cd tools` left this
session's shell in a subdirectory for the rest of the turn -- and because the
PreToolUse hooks are relative paths resolved against that same working
directory, even `cd ..` was blocked. Any checker run by hand in that state
would have answered about nothing. (`report_only_checks.py` was never exposed:
it passes `cwd=REPO` to every subprocess. That is exactly the fix, applied one
layer up.)

THE ASSERTION IS DIFFERENTIAL, and that is what makes it hard to fake: the same
checker, run from the repo root and from a subdirectory, must produce BYTE-
IDENTICAL output. A tool that anchors its paths passes trivially; a tool that
does not cannot, because the two runs see different files. It also asserts the
output is NON-TRIVIAL -- identical-but-empty would satisfy equality while
meaning the opposite.

THE DIFFERENTIAL AND COVERAGE ARMS WERE RUN AGAINST THE UNFIXED TOOLS AND
WATCHED TO FAIL -- that is where the four output lines quoted above came from.
`seam_check` failed twice: anchoring its glob alone was not enough, because a
second `os.path.isfile()` on a repo-relative name was also CWD-relative and
every delegate silently resolved to False. The two explicit-path arms at the
bottom are NOT in that category and are stated as what they are: they guard the
fix from over-reaching, by proving a path somebody typed is still resolved from
where they typed it.

Exit 0 pass, 1 fail.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# A real directory inside the repo that is NOT the root. `docs/` is tracked and
# always present; a temp directory would not reproduce the case, since these
# tools are run from inside the checkout.
ELSEWHERE = os.path.join(REPO, 'docs')

# (tool, extra args, a regex capturing THE COUNT this tool discloses).
#
# A COUNT, NEVER A VERDICT. Every one of these four printed a clean-looking
# verdict while scanning nothing; the count is the only part of the output that
# changes when the subject list goes empty. Four exact patterns rather than one
# loose heuristic, because the loose version passed three tools and failed the
# fourth for the wrong reason -- sairn_seam_check.py discloses its coverage as
# `75 clean, ...` and names no files at all, so a regex hunting the word "file"
# reported a real, anchored tool as trivial.
TOOLS = [
    ('write_without_readback_check.py', [], r'FILES SCANNED: (\d+)'),
    ('sairn_seam_check.py', [], r'(\d+) clean, \d+ not-forwarded'),
    ('sairn_stale_snapshot_scan.py', ['--quiet-clean'], r'(\d+) file\(s\) scanned'),
    ('sairn_strict_args_check.py', [], r'in (\d+) file\(s\)'),
]

fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def run(tool, args, cwd):
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', tool)] + args,
                       cwd=cwd, capture_output=True, text=True, timeout=600)
    return p.returncode, (p.stdout or '')


def disclosed_count(out, pattern):
    """The count this tool discloses, or None if it discloses none."""
    m = re.search(pattern, out)
    return int(m.group(1)) if m else None


for tool, args, pattern in TOOLS:
    print('')
    print('%s' % tool)
    rc_root, out_root = run(tool, args, REPO)
    rc_else, out_else = run(tool, args, ELSEWHERE)
    n = disclosed_count(out_root, pattern)
    check(n is not None,
          '%s: the root run DISCLOSES a count (%s)' % (tool, pattern))
    check(bool(n),
          '%s: and that count is above zero (%s)' % (tool, n))
    check(rc_root == rc_else,
          '%s: same exit code from the repo root and from docs/ (%d vs %d)'
          % (tool, rc_root, rc_else))
    check(out_root == out_else,
          '%s: BYTE-IDENTICAL output from the repo root and from docs/' % tool)
    if out_root != out_else:
        r, e = out_root.splitlines(), out_else.splitlines()
        for i in range(max(len(r), len(e))):
            a = r[i] if i < len(r) else '(no line)'
            b = e[i] if i < len(e) else '(no line)'
            if a != b:
                print('        first difference at line %d' % (i + 1))
                print('        root : %s' % a[:100])
                print('        docs : %s' % b[:100])
                break

print('')
print('AN EXPLICIT PATH ARGUMENT STAYS CWD-RELATIVE, ON PURPOSE')
# Anchoring the DEFAULT must not silently re-root a path somebody typed. Run
# from the repo root with a relative path that only resolves from there.
rc, out = run('sairn_strict_args_check.py', ['stonedesk.html'], REPO)
check(rc == 0 and 'in 1 file(s)' in out,
      'a named target resolves from the repo root and scans exactly it')
rc2, _ = run('sairn_strict_args_check.py', ['stonedesk.html'], ELSEWHERE)
check(rc2 != 0,
      'the SAME relative name from docs/ does NOT silently resolve to the repo '
      'copy -- a typed path means what was typed, and a missing one is an '
      'error rather than a quiet zero')

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
