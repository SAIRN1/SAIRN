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
import io
import os
import re
import subprocess
import sys

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


def run_tool(repo, rel, args, timeout):
    """(exit_code_or_None, wrote) -- None means it did not finish."""
    try:
        r = subprocess.run([sys.executable, rel] + list(args), cwd=repo,
                           capture_output=True, timeout=timeout)
        code = r.returncode
    except subprocess.TimeoutExpired:
        code = None
    except OSError as e:
        out('    COULD NOT LAUNCH %s: %s' % (rel, e))
        code = None
    wrote = porcelain(repo)
    return code, wrote


def opt(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def main(argv):
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

    writes_bare, writes_help, could_not = [], [], []
    for n in names:
        rel = os.path.join('tools', n)
        code, wrote = run_tool(repo, rel, [], timeout)
        if wrote:
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

        code, wrote = run_tool(repo, rel, ['--help'], timeout)
        if wrote:
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
    out('  WROTE on a bare run       : %d' % len(writes_bare))
    out('  WROTE on --help           : %d' % len(writes_help))
    out('  COULD NOT RUN (no verdict): %d -- these are NOT reported as clean'
        % len(could_not))
    for n, why in could_not:
        out('      %-46s %s' % (n, why))
    out('')
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
