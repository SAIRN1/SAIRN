#!/usr/bin/env python3
"""tools/git_discovery_anchoring_check.py -- which tools shell out to `git`
WITHOUT saying which repository they mean, and so can answer confidently about
the wrong one?

    python tools/git_discovery_anchoring_check.py
    python tools/git_discovery_anchoring_check.py --list
    python tools/git_discovery_anchoring_check.py --baseline

Exit 0 no worse than pinned, 1 a regression, 2 COULD NOT TELL.

── THE HAZARD, MEASURED ON THIS MACHINE ────────────────────────────────────
**C:/Users/marsh/.git EXISTS.** The home directory is itself a git repository.
Git resolves a repository by walking UP from the working directory, so from any
scratch, temp or sub-directory beneath the home directory:

    $ cd "$TEMP/not-a-repo-at-all" && git rev-parse --git-dir
    C:/Users/marsh/.git          <-- exit 0

It does not fail. `git ls-files` answers with THAT repository's files, `git log`
walks THAT history, and a checker that trusted it prints a confident, specific,
wrong answer about a repository it was never pointed at. Found 2026-09-27 by
tools/conflict_marker_preflight.py's OWN probe: the arm asserting "outside a git
repo this must exit 2" got 0, and the reason was not a bug in the tool's logic --
it was that there is no "outside a git repo" under this home directory.

THIS IS THE SAME SHAPE AS clone_name()'s cwd BUG in tools/session_lock_check.py,
which read os.path.basename(os.getcwd()) and returned 'tools' or 'docs' depending
on where the session's shell happened to be -- making four separate clones claim
one lock. A tool that believes where it is standing instead of ESTABLISHING it.
Every clone has a tools/ and a docs/; every directory on this machine has a
git repository above it.

── WHAT COUNTS AS ANCHORED ─────────────────────────────────────────────────
Any ONE of these is enough, and they are all explicit:

  1. `cwd=` a path derived from `__file__` on the subprocess call -- the repo root
     is a fact about where the tool lives, the cwd is not;
  2. `git -C <path>` in the argument list;
  3. `--git-dir=` / `GIT_DIR` in the environment passed to the call;
  4. an assertion that `rev-parse --show-toplevel` IS the intended root, which is
     the only one that also catches a WRONG cwd rather than an absent one.

(4) is the strongest and is what conflict_marker_preflight.assert_this_repo()
does. (1) is what most tools here already do and is sufficient in practice.

── WHAT THIS CANNOT DO, SAID BEFORE THE NUMBER ─────────────────────────────
IT IS A STATIC SCREEN AND IT READS TEXT. A tool that computes its cwd through two
indirections reads as unanchored here; a tool that passes `cwd=os.getcwd()` reads
as ANCHORED and is not. So:

  * the UNANCHORED list is a list to READ, not a list of defects;
  * `cwd=` anything is credited, but a cwd that is not derived from `__file__` is
    reported separately as WEAK rather than folded into either answer.

A RATCHET, pinned to docs/git-discovery-anchoring.json: `unanchored` must never
rise. An absent or unparseable pin is exit 2, never 0 -- and so is finding zero
git callers at all, because the call shape moving must not read as "everything is
anchored".
"""
import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN = os.path.join(REPO, 'docs', 'git-discovery-anchoring.json')

SCAN_DIRS = ('tools', 'tests', 'api', 'scripts')

# A subprocess call whose argv begins with git, in any of the shapes used here.
GIT_CALL = re.compile(
    r"""subprocess\.(?:run|call|check_output|check_call|Popen)\s*\(\s*"""
    r"""(?P<args>\(|\[)?\s*(?:['"]git['"]|\(\s*['"]git['"])""")

# os.popen / os.system with a bare git, which carry no cwd parameter at all.
BARE_SHELL = re.compile(r"""os\.(?:popen|system)\s*\(\s*['"]\s*git\s""")


class CouldNotTell(Exception):
    pass


def _call_end(src, open_idx):
    """Index just past the ) closing the call whose ( is at open_idx.

    Brace/paren matching on a string-and-comment MASK, not a fixed window. A
    fixed slice after the match is how a call's own arguments get confused with
    the next call's -- the magic-window defect this platform has now paid for
    three times (BRANCH_WINDOW=3000, the 4200-char roofing window, and a 3000-char
    branch window that swallowed the next branch's role set).
    """
    depth = 0
    i, n = open_idx, len(src)
    while i < n:
        c = src[i]
        if c in '\'"':
            q = c
            trip = src[i:i + 3] in (q * 3,)
            i += 3 if trip else 1
            while i < n:
                if src[i] == '\\':
                    i += 2
                    continue
                if trip and src[i:i + 3] == q * 3:
                    i += 3
                    break
                if not trip and src[i] == q:
                    i += 1
                    break
                if not trip and src[i] == '\n':
                    break
                i += 1
            continue
        if c == '#':
            j = src.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def classify(src):
    """[(kind, line, snippet)] for every git subprocess call in one file."""
    out = []
    for m in list(GIT_CALL.finditer(src)) :
        paren = src.find('(', m.start())
        end = _call_end(src, paren)
        if end is None:
            # The call's extent could not be established. NOT credited as
            # anchored -- an unreadable call is the third state, and calling it
            # clean is the fail-open this whole tool is about.
            out.append(('UNREADABLE', src.count('\n', 0, m.start()) + 1,
                        src[m.start():m.start() + 70].replace('\n', ' ')))
            continue
        call = src[m.start():end]
        line = src.count('\n', 0, m.start()) + 1
        snippet = ' '.join(call.split())[:90]
        if '--show-toplevel' in src and 'normcase' in src:
            kind = 'ASSERTED'
        elif re.search(r"""['"]-C['"]|--git-dir""", call):
            kind = 'ANCHORED'
        elif 'cwd=' in call:
            kind = 'ANCHORED' if re.search(
                r'cwd\s*=\s*(REPO|ROOT|REPO_ROOT|_REPO|self\.repo|repo_root)', call
            ) else 'WEAK'
        else:
            kind = 'UNANCHORED'
        out.append((kind, line, snippet))
    for m in BARE_SHELL.finditer(src):
        out.append(('UNANCHORED', src.count('\n', 0, m.start()) + 1,
                    ' '.join(src[m.start():m.start() + 70].split())))
    return out


def scan():
    results = {}
    for d in SCAN_DIRS:
        base = os.path.join(REPO, d)
        if not os.path.isdir(base):
            continue
        for root, _, names in os.walk(base):
            for n in sorted(names):
                if not n.endswith('.py'):
                    continue
                full = os.path.join(root, n)
                rel = os.path.relpath(full, REPO).replace(os.sep, '/')
                try:
                    src = io.open(full, encoding='utf-8', errors='replace').read()
                except OSError as exc:
                    raise CouldNotTell('%s could not be read (%s)' % (rel, exc))
                hits = classify(src)
                if hits:
                    results[rel] = hits
    if not results:
        raise CouldNotTell(
            'no subprocess git call matched anywhere under %s -- the call shape '
            'moved and NOTHING was measured. This is NOT "everything is anchored".'
            % ', '.join(SCAN_DIRS))
    return results


def tally(results):
    counts = {'ASSERTED': 0, 'ANCHORED': 0, 'WEAK': 0, 'UNANCHORED': 0,
              'UNREADABLE': 0}
    files = {k: set() for k in counts}
    for rel, hits in results.items():
        for kind, _, _ in hits:
            counts[kind] += 1
            files[kind].add(rel)
    return counts, files


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true',
                    help='print every call site, not only the summary')
    ap.add_argument('--baseline', action='store_true',
                    help='rewrite the pin to the CURRENT numbers. Only correct '
                         'after a real anchoring fix, never to make a run pass')
    args = ap.parse_args(argv)

    try:
        results = scan()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2
    counts, files = tally(results)

    print('GIT-DISCOVERY ANCHORING')
    print('C:/Users/marsh/.git exists, so an unanchored git call does not FAIL --')
    print('it answers about the home repository. That is the hazard being counted.')
    print('')
    print('%d file(s) shell out to git, %d call site(s).'
          % (len(results), sum(counts.values())))
    print('  ASSERTED   toplevel checked against the intended root : %d' % counts['ASSERTED'])
    print('  ANCHORED   cwd=REPO-derived, git -C, or --git-dir     : %d' % counts['ANCHORED'])
    print('  WEAK       a cwd is passed but not derived from __file__: %d' % counts['WEAK'])
    print('  UNANCHORED no cwd, no -C, no --git-dir                : %d' % counts['UNANCHORED'])
    print('  UNREADABLE the call extent could not be established   : %d' % counts['UNREADABLE'])
    print('')

    for kind in ('UNANCHORED', 'UNREADABLE', 'WEAK'):
        if not files[kind]:
            continue
        print('  %s:' % kind)
        for rel in sorted(files[kind]):
            for k, line, snip in results[rel]:
                if k == kind:
                    print('   %s:%d' % (rel, line))
                    if args.list:
                        print('      %s' % snip)
        print('')

    print('A LIST TO READ, NOT A LIST OF DEFECTS. This is a static screen: a tool')
    print('that reaches its cwd through two indirections reads as unanchored, and')
    print('one passing cwd=os.getcwd() reads as WEAK and is not safe. The')
    print('strongest form is asserting rev-parse --show-toplevel IS the intended')
    print('root -- see conflict_marker_preflight.assert_this_repo() -- because it')
    print('catches a WRONG cwd and not merely an absent one.')
    print('')

    if args.baseline:
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            '_what': 'Pinned git-discovery anchoring. Written by '
                     'tools/git_discovery_anchoring_check.py --baseline. A '
                     'ratchet: `unanchored` and `unreadable` must never rise.',
            '_why': 'C:/Users/marsh/.git exists, so git discovery walks UP and '
                    'succeeds from any directory on this machine. An unanchored '
                    'call answers about the wrong repository instead of failing.',
            'unanchored': counts['UNANCHORED'],
            'unreadable': counts['UNREADABLE'],
            'weak': counts['WEAK'],
            'anchored': counts['ANCHORED'],
            'asserted': counts['ASSERTED'],
            'unanchored_files': sorted(files['UNANCHORED']),
            'weak_files': sorted(files['WEAK']),
        }, indent=2, sort_keys=True) + '\n')
        print('wrote %s' % os.path.relpath(PIN, REPO))
        return 0

    if not os.path.isfile(PIN):
        sys.stderr.write('COULD NOT TELL -- %s does not exist, so NOTHING was '
                         'compared. Run --baseline once to pin the measured '
                         'state.\n' % os.path.relpath(PIN, REPO))
        return 2
    try:
        pin = json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        sys.stderr.write('COULD NOT TELL -- %s will not parse (%s). NOTHING WAS '
                         'COMPARED.\n' % (os.path.relpath(PIN, REPO), e))
        return 2
    was = pin.get('unanchored')
    if not isinstance(was, int):
        sys.stderr.write('COULD NOT TELL -- the pin carries no integer '
                         '`unanchored`.\n')
        return 2

    now = counts['UNANCHORED']
    if now > was:
        print('REGRESSION -- unanchored git calls rose from %d to %d.' % (was, now))
        print('Anchor the new call (cwd= a __file__-derived root, or git -C), or')
        print('say why it is correct and re-pin with --baseline in the same commit.')
        return 1
    if now < was:
        print('IMPROVED -- unanchored fell from %d to %d. Re-pin:' % (was, now))
        print('   python tools/git_discovery_anchoring_check.py --baseline')
        return 0
    print('OK -- no worse than pinned (%d unanchored).' % was)
    print('A RATCHET IS NOT A PASS. %d call site(s) can still answer about the')
    print('wrong repository, and %d more pass a cwd nobody derived from __file__.'
          % (now, counts['WEAK']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
