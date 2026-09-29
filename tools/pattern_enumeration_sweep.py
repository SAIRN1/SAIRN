r"""A POPULATION DERIVED BY NAME IS STILL A GUESS ABOUT THE NAME.

    python tools/pattern_enumeration_sweep.py
    python tools/pattern_enumeration_sweep.py --json
    python tools/pattern_enumeration_sweep.py --tool <path>   # one file

REPORT ONLY. Exit 0 clean, 1 findings, 2 COULD NOT RUN. Writes nothing.

── WHY, AND IT IS THE THIRD INSTANCE OF ONE DEFECT ─────────────────────────
`docs/NHI-REGISTER.md`'s `clone-push-access` row is the rotation blast radius for
the GitHub push credential. It has been wrong three times:

  2026-09-16  CLAUDE.md said "Four clones" and named four while a FIFTH pushed.
              Fixed by correcting the list.
  2026-09-17  the register's own row said "FOUR working copies" for the same
              reason. Fixed by COUNTING FROM DISK instead of typing the list --
              and the tool's header explains that at length.
  2026-09-29  the count WAS derived from disk and was STILL WRONG. The filter was
              `name.startswith('SAIRN-')`, and `Documents\SAIRN` is a clone of the
              same remote, on main, able to push. SEVEN working copies, six
              counted.

**The lesson is not "derive your populations".** That was already done. It is that
**deriving a population does not make it right if the FILTER encodes a habit.**
The question was "is this directory a git clone of the same origin", and nothing
about a hyphen answers it.

── WHAT THIS SWEEP LOOKS FOR ───────────────────────────────────────────────
Every tool that builds a population from a NAME -- `startswith`, `endswith`, a
filename glob, a regex over a path, `os.listdir` with a name test -- and reports
whether that population is corroborated by a SECOND, INDEPENDENT derivation.

"Independent" means it answers **who is IN the population** from something other
than the name:

  * `git ls-files`            -- tracked-ness, which a name cannot tell you
  * `git worktree list`       -- what git itself considers a working copy
  * `rev-parse --git-dir`     -- whether a directory really is a repository
  * an explicit member list maintained elsewhere

**READING THE FILE IS NOT CORROBORATION, and the first version of this tool got
that wrong.** It counted `open(` as a second derivation, matched almost every tool
in the repo, and reported 3 findings out of ~200 files -- which looked like good
news and was a vacuous pass. Reading a file you ALREADY SELECTED BY NAME tells you
what it is; it cannot tell you whether you should have selected it.

**The clone undercount is the proof.** `nhi_register.sibling_clones()` read
`remote.origin.url` out of every directory it examined -- real content, from a real
second source -- and still missed a working copy, because the NAME decided which
directories it examined. Content corroborates CLASSIFICATION. Only a different
membership test corroborates MEMBERSHIP.

A name test with no second derivation is a **SINGLE-DERIVATION POPULATION**. That
is a finding, not a failure: most are perfectly safe, and the point is that
nothing currently says which.

── IT REPORTS, IT DOES NOT RANK, AND IT DOES NOT AUTO-FIX ──────────────────
There is no severity column, because severity here is a judgement about what the
population is FOR -- a glob over `tests/*.py` that under-counts by one costs a
missed arm; a clone enumeration that under-counts by one costs a credential
rotation that misses a machine. The tool cannot tell those apart and does not
pretend to. Every finding is printed with its line so a human ranks it.

── THE NUMBERS IT PRINTS ARE COUNTS OF CODE SHAPES, NOT OF DEFECTS ─────────
Said plainly because a "23 findings" line in a report reads as 23 bugs. It is 23
places where a population comes from a name and nothing corroborates it. The
2026-09-29 clone undercount was one of these; so is every `glob('tests/*.py')`
that is completely fine.
"""
import argparse
import io
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

CRITERIA_VERSION = '2026-09-29.1'
NL = chr(10)

# ── THE NAME-TEST SHAPES. Each is a way of deciding membership from a string.
NAME_TESTS = (
    ('startswith', re.compile(r'\.startswith\s*\(')),
    ('endswith', re.compile(r'\.endswith\s*\(')),
    ('glob', re.compile(r'\bglob\.glob\s*\(|\biglob\s*\(')),
    ('fnmatch', re.compile(r'\bfnmatch\b')),
    ('listdir', re.compile(r'\bos\.listdir\s*\(')),
)

# ── OPTION PARSING IS NOT A POPULATION FILTER, and excluding it is a criteria
# decision rather than a convenience. `tokens[i].startswith('-')` decides whether
# a command-line argument is a flag. There is no population and nothing to
# corroborate, and counting it made the first run of this sweep report
# git_push_master_guard.py -- a file with no population in it at all. A sweep
# whose findings are mostly argv parsing is a sweep nobody reads.
OPTION_PARSING = re.compile(r"""\.startswith\s*\(\s*r?['"]-{1,2}['"]""")

# ── WHAT COUNTS AS CORROBORATION, AND THE FIRST VERSION OF THIS LIST WAS WRONG
# IN THE WAY THAT MATTERS MOST. It included "reads the file content" (`open(`),
# which matched almost every tool in the repo and made the sweep report 3 findings
# out of ~200 files. That looked like good news and was a vacuous pass.
#
# THE DISTINCTION IS BETWEEN MEMBERSHIP AND CLASSIFICATION. Reading a file you
# ALREADY SELECTED BY NAME tells you what it is; it cannot tell you whether you
# should have selected it. The clone undercount is the proof: nhi_register read
# `remote.origin.url` out of every directory it looked at -- real content, from a
# real second source -- and still missed a clone, because the NAME decided which
# directories it looked at in the first place.
#
# So corroboration has to answer "who is IN this population" from something other
# than the name. Tracked-ness, git's own idea of a working copy, or an explicit
# list of members maintained elsewhere.
CORROBORATIONS = (
    ('git ls-files', re.compile(r'ls-files')),
    ('git worktree list', re.compile(r'worktree\s+list|[\'"]worktree[\'"]')),
    ('git rev-parse --git-dir', re.compile(r'rev-parse[^\n]*git-dir')),
    ('an explicit member list maintained elsewhere',
     re.compile(r'\bREGISTRY\b|\bNOT_PROMOTED\b|\bPURPOSES\b|\bCONTROLS_FOR\b')),
)

# Files this sweep does not read, with the reason. NAMED, never silently skipped.
SKIP = (
    ('__pycache__', 'compiled bytecode, not source'),
    ('pattern_enumeration_sweep.py',
     'this file. Its own NAME_TESTS table is a list of regexes ABOUT name tests, '
     'so it matches itself on every row and the finding would be pure noise. '
     'Covered instead by tests/run_pattern_enumeration_probe.py, which drives it '
     'against fixtures.'),
)


def source_files():
    out = []
    for root, dirs, files in os.walk(os.path.join(REPO, 'tools')):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in sorted(files):
            if not f.endswith('.py'):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO).replace('\\', '/')
            if any(s in rel for s, _why in SKIP):
                continue
            out.append(rel)
    return out


def strip_comments(src):
    """Docstrings and `#` runs removed.

    Necessary, not cosmetic: this sweep's own subject is discussed in prose all
    over this repo, and a tool whose HEADER explains that it avoids a glob would
    otherwise be reported for having one. PR 1.2, and the trap the X-SD-Auth
    check and the credential-duplication sweep both fell into first.
    """
    q3, s3 = chr(34) * 3, chr(39) * 3
    out = re.sub('(?s)' + q3 + '.*?' + q3, '', src)
    out = re.sub('(?s)' + s3 + '.*?' + s3, '', out)
    return NL.join(re.sub(r'#.*$', '', ln) for ln in out.split(NL))


def examine(rel):
    """(name_tests, corroborations) for one file, by line."""
    path = os.path.join(REPO, rel)
    try:
        raw = io.open(path, encoding='utf-8', errors='replace').read()
    except OSError as exc:
        return None, str(exc)
    code = strip_comments(raw)
    lines = code.split(NL)

    tests = []
    for i, ln in enumerate(lines, 1):
        if OPTION_PARSING.search(ln):
            continue
        for label, rx in NAME_TESTS:
            if rx.search(ln):
                tests.append((label, i, ln.strip()[:90]))
    corrob = sorted({label for label, rx in CORROBORATIONS if rx.search(code)})
    return (tests, corrob), None



# ── THE SECOND DERIVATION, RUN RATHER THAN RECOMMENDED ──────────────────────
# Reporting "this population has one derivation" is half a tool. The other half
# is running a second one and saying where the two disagree -- which is what
# item 15 asked for, and what the clone undercount needed.
#
# THE ONE COMPARISON THAT IS AVAILABLE PLATFORM-WIDE is filesystem membership
# against git membership. A tool that walks a directory counts UNTRACKED files; a
# tool that asks `git ls-files` does not. Neither is wrong -- they answer
# different questions -- but a tool that does not say which it meant is one whose
# count changes when somebody leaves a scratch file in the tree.
#
# THIS IS NOT HYPOTHETICAL ON THIS MACHINE. tools/tooling_inventory.py REFUSES to
# generate when a tool is on disk and untracked, and its refusal message exists
# because that exact difference produced a document that named a tool as deleted.
# The two populations disagree; the question is whether each tool knows it.
FS_SCOPES = (
    ('tools/', ('.py', '.js', '.cjs', '.sh')),
    ('tests/', ('.py', '.js')),
    ('docs/', ('.md', '.json')),
    ('sql/', ('.sql',)),
)


def _git_lines(*args):
    import subprocess
    try:
        r = subprocess.run(['git', '-C', REPO] + list(args), capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=60)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return [x.strip().replace(chr(92), '/') for x in (r.stdout or '').splitlines()
            if x.strip()]


def filesystem_vs_git():
    """Per scope: (on disk, tracked, disk-only, git-only).

    `disk-only` is the set a filesystem walk counts and `git ls-files` does not.
    `git-only` is the opposite -- a tracked file no longer on disk, which is a
    different and rarer failure.
    """
    tracked = _git_lines('ls-files')
    if tracked is None:
        return None
    tracked = set(tracked)
    out = []
    for scope, exts in FS_SCOPES:
        base = os.path.join(REPO, scope.rstrip('/'))
        disk = set()
        if os.path.isdir(base):
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for f in files:
                    if not f.endswith(exts):
                        continue
                    rel = os.path.relpath(os.path.join(root, f), REPO)
                    disk.add(rel.replace(chr(92), '/'))
        tr = {t for t in tracked
              if t.startswith(scope) and t.endswith(exts)}
        out.append((scope, disk, tr, sorted(disk - tr), sorted(tr - disk)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tool', default=None)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    files = ([os.path.relpath(os.path.abspath(args.tool), REPO).replace('\\', '/')]
             if args.tool else source_files())
    if not files:
        print('COULD NOT RUN: no source files were found under tools/. A sweep '
              'over nothing reports clean, which is the vacuous-pass shape this '
              'platform records most often.')
        return EXIT_COULD_NOT_RUN

    single, corroborated, unreadable = [], [], []
    for rel in files:
        result, err = examine(rel)
        if err:
            unreadable.append((rel, err))
            continue
        tests, corrob = result
        if not tests:
            continue
        (corroborated if corrob else single).append((rel, tests, corrob))

    print('PATTERN ENUMERATION SWEEP -- a population derived by NAME is still a '
          'guess about the name')
    print('  criteria : %s' % CRITERIA_VERSION)
    print('  swept    : %d file(s) under tools/' % len(files))
    print()
    print('  WHY: the clone count in docs/NHI-REGISTER.md was wrong THREE TIMES.')
    print('  The third time it was already DERIVED FROM DISK and still wrong,')
    print('  because the filter was startswith(\'SAIRN-\') and one clone of the')
    print('  same remote has no hyphen. Deriving a population does not make it')
    print('  right if the FILTER encodes a habit.')
    print()
    for name, why in SKIP:
        print('  NOT SWEPT: %s -- %s' % (name, why))
    print()
    print('  CORROBORATED (%d) -- a name test AND at least one derivation that is '
          'not a name:' % len(corroborated))
    for rel, tests, corrob in corroborated:
        print('    ok  %-44s %d name test(s); also %s'
              % (rel, len(tests), ', '.join(corrob)))
    print()
    if single:
        print('SINGLE-DERIVATION POPULATIONS (%d) -- membership decided by a NAME '
              'and nothing else:' % len(single))
        for rel, tests, _c in single:
            print('  ! %s' % rel)
            for label, line, text in tests[:4]:
                print('      %-18s :%-5d %s' % (label, line, text))
            if len(tests) > 4:
                print('      ... and %d more in this file' % (len(tests) - 4))
    else:
        print('Every file with a name test also derives membership some other way.')

    if unreadable:
        print()
        print('COULD NOT READ (%d) -- NOT a pass:' % len(unreadable))
        for rel, err in unreadable:
            print('  ? %s (%s)' % (rel, err))

    print()
    print('  THESE ARE COUNTS OF CODE SHAPES, NOT OF DEFECTS. Most name tests are')
    print('  perfectly safe. The finding is that nothing currently says WHICH --')
    print('  and severity here depends on what the population is FOR, which this')
    print('  tool cannot know: a glob over tests/ that under-counts by one costs a')
    print('  missed arm, and a clone enumeration that under-counts by one costs a')
    print('  credential rotation that misses a machine.')
    print()
    print('  NO RANKING AND NO AUTO-FIX, deliberately. A tool that rewrote a')
    print('  filter would be deciding what a population means.')

    # ── THE SECOND DERIVATION, RUN. See FS_SCOPES.
    print()
    print('SECOND DERIVATION -- filesystem membership vs git membership')
    fs = filesystem_vs_git()
    disagreements = []
    if fs is None:
        print('  COULD NOT RUN: git did not answer `ls-files`, so the second')
        print('  derivation was NOT performed. That is a third state: the')
        print('  single-derivation list above stands, and nothing was compared.')
        unreadable.append(('git ls-files', 'did not answer'))
    else:
        for scope, disk, tr, disk_only, git_only in fs:
            agree = not disk_only and not git_only
            print('  %-4s %-8s disk=%-5d tracked=%-5d  %s'
                  % ('ok' if agree else '!!', scope, len(disk), len(tr),
                     'the two derivations agree' if agree
                     else 'DISAGREE: %d on disk only, %d tracked only'
                          % (len(disk_only), len(git_only))))
            for f in disk_only[:6]:
                print('         disk only  %s' % f)
            for f in git_only[:6]:
                print('         git only   %s' % f)
            if not agree:
                disagreements.append(scope)
        if disagreements:
            print()
            print('  A DISAGREEMENT IS NOT AUTOMATICALLY A DEFECT -- the two')
            print('  populations answer different questions, and an untracked')
            print('  scratch file legitimately appears in one. IT IS A DEFECT IN')
            print('  ANY TOOL THAT DID NOT CHOOSE. tools/tooling_inventory.py')
            print('  chose: it REFUSES to generate while a tool is untracked, and')
            print('  its refusal message exists because that exact difference')
            print('  once produced a document naming a live tool as deleted.')

    if args.json:
        print(json.dumps({
            'criteria': CRITERIA_VERSION,
            'swept': len(files),
            'second_derivation_disagreements': disagreements,
            'skipped': [{'name': n, 'why': w} for n, w in SKIP],
            'single_derivation': [{'file': r, 'tests': t} for r, t, _ in single],
            'corroborated': [{'file': r, 'by': c} for r, _t, c in corroborated],
            'unreadable': [{'file': r, 'error': e} for r, e in unreadable],
        }, indent=2))

    if unreadable:
        return EXIT_COULD_NOT_RUN
    return EXIT_FINDING if single else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
