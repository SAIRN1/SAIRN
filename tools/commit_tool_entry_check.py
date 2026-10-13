#!/usr/bin/env python
# OWNER: fourth
r"""commit_tool_entry_check.py -- does THIS COMMIT add a tools/ file nothing describes?

    python tools/commit_tool_entry_check.py --pre-commit   # the staged commit
    python tools/commit_tool_entry_check.py --range A..B    # commits already made
    python tools/commit_tool_entry_check.py --fixtures      # the criteria lock alone

Exit 0 every tools/*.py the subject ADDS carries a description; 1 at least one
does not; 2 COULD NOT CHECK -- which is never folded into either of the other
two (PR §1.11).

── WHY THIS EXISTS, AND IT IS NOT HYPOTHETICAL ────────────────────────────────
Michael decided on 2026-09-13 that no tools/ file is mergeable without a
matching inventory entry, and TWO gates enforce it: push-gate checks 12 and 14,
plus the generator itself, which exits 2 rather than emitting a blank cell.
Every one of those three asks the question AT PUSH TIME.

So the rule held and the feedback arrived five batches late. `report_sha_check.py`
landed in b5 (28179dba) and `temp_state_leak_check.py` in b7 (78f0aff6), each
with no entry in either source. Nothing said so at the commit that added them,
nothing said so at the next commit, and by the time a push gate refused over
the pair on 2026-10-13 there were 29 unpushed commits -- five batches of
unrelated, finished work -- stacked behind a refusal whose entire cause was two
missing dict keys. The refusal was correct. Its TIMING is the defect: a check
that fires only at the boundary converts a one-line omission into a blocked
queue, and the session that has to clear it is whichever one pushes next rather
than the one that wrote the tool.

The generator says this itself, in the comment above `doc_sha_reseat.py`: *"any
session adding a tool must write into whatever session happens to hold the
inventory."* That coupling is cheapest to pay in the same minute the tool is
written and most expensive to pay at a push.

── WHAT COUNTS AS DESCRIBED, AND WHY IT IS TWO SOURCES ────────────────────────
`tooling_inventory.missing_purposes` is the authority and it accepts EITHER:

    absent = [t for t in tools if t not in reg and t not in PURPOSES]

`PURPOSES` in tools/tooling_inventory.py, or a `REGISTRY` entry in
tools/report_only_checks.py (which carries its own `catches` text). A handful of
tools carry no PURPOSES entry ON PURPOSE because they are registered instead --
a check that read only PURPOSES would refuse those correctly-described tools, so
both are read here.

── IT READS THE STAGED BLOBS, NOT THE WORKING TREE ────────────────────────────
The question is whether the COMMIT carries the entry, and those differ in the
exact case worth catching: write the tool, stage it, write the entry, forget to
stage the inventory. A working-tree read passes that commit and the entry lands
one commit later or never. So `git show :<path>` is the subject, and the
working-tree copy is read only for a path that is not staged at all.

── THE AST READER IS DUPLICATED DELIBERATELY ──────────────────────────────────
`tooling_inventory.duplicate_purposes_keys()` already parses that literal, and
it is bound to its own `__file__`. It cannot be pointed at a staged blob, which
is the whole subject here. The duplication is named rather than hidden, and
convention 8 applies to it: if the literal's SHAPE moves -- a computed key, a
`PURPOSES` built by update() -- this reports COULD NOT CHECK by name instead of
reporting a clean population it never read.

── WHAT IT IS NOT ─────────────────────────────────────────────────────────────
NOT a replacement for push-gate checks 12 and 14. A pre-commit hook is per-clone
state: it is installed by `python tools/install_git_hooks.py` and a clone that
never ran that has no hook at all. The boundary check stays the backstop; this
moves the FIRST notice to the commit. Both, not either.

NOT a judgement about the entry's CONTENT. A one-word PURPOSES line satisfies
this exactly as a good one does. What catches a useless entry is a reader, and
the generator's own refusal text already says what an entry is for -- naming
what the tool CATCHES, not what it does.
"""
from __future__ import annotations

import ast
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = 'tools/tooling_inventory.py'
ROC = 'tools/report_only_checks.py'


class CouldNotCheck(Exception):
    """Exit 2. Raised with the reason, never swallowed into a pass."""


def _git(*args):
    """stdout, or CouldNotCheck naming the command -- never an empty string."""
    try:
        r = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=120)
    except Exception as e:                                       # noqa: BLE001
        raise CouldNotCheck('git %s did not run (%s: %s)'
                            % (' '.join(args), type(e).__name__, e))
    if r.returncode != 0:
        raise CouldNotCheck('git %s exited %d: %s'
                            % (' '.join(args), r.returncode,
                               (r.stderr or '').strip().splitlines()[-1:] or ['no stderr']))
    return r.stdout


def _source_at(path, rev):
    """The blob `path` holds at `rev` -- used by --range, never by --pre-commit.

    A historical range must be judged against the inventory AS IT WAS, not
    against today's. Reading today's copy would report a 2026-10-02 commit as
    clean the moment somebody adds the entry in 2026-10-13, which is precisely
    the back-dating that makes a check stop testing anything (convention 8).
    """
    try:
        r = subprocess.run(['git', 'show', '%s:%s' % (rev, path)], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=120)
    except Exception as e:                                       # noqa: BLE001
        raise CouldNotCheck('git show %s:%s did not run (%s: %s)'
                            % (rev, path, type(e).__name__, e))
    if r.returncode != 0:
        raise CouldNotCheck('%s does not exist at %s, so nothing could say '
                            'whether a tool is described there' % (path, rev))
    return r.stdout, '%s' % rev


def _staged_source(path):
    """The blob THIS COMMIT would carry for `path`, or the working tree copy.

    A path absent from the index is not an error: the inventory is often
    untouched by the commit under test, and then the committed/working copy IS
    what the commit leaves behind. A path that is staged but unreadable IS an
    error.
    """
    try:
        r = subprocess.run(['git', 'show', ':' + path], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=120)
    except Exception as e:                                       # noqa: BLE001
        raise CouldNotCheck('git show :%s did not run (%s: %s)'
                            % (path, type(e).__name__, e))
    if r.returncode == 0:
        return r.stdout, 'staged'
    disk = os.path.join(REPO, path.replace('/', os.sep))
    if not os.path.isfile(disk):
        raise CouldNotCheck('%s is neither staged nor on disk, so nothing could '
                            'say whether a tool is described' % path)
    try:
        return io.open(disk, encoding='utf-8').read(), 'working tree'
    except Exception as e:                                       # noqa: BLE001
        raise CouldNotCheck('could not read %s (%s: %s)' % (path, type(e).__name__, e))


def purposes_keys(src, where=INV):
    """Every key of the module-level `PURPOSES = {...}` literal in `src`.

    Module level and by `tree.body` rather than `ast.walk`, for the same reason
    the generator gives: the literal that matters is the one an import would
    evaluate, and a `PURPOSES` nested in a function is not it.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        raise CouldNotCheck('could not parse %s as Python (%s)' % (where, e))
    for st in tree.body:
        if (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)
                and st.targets[0].id == 'PURPOSES'
                and isinstance(st.value, ast.Dict)):
            keys = []
            for k in st.value.keys:
                if not isinstance(k, ast.Constant) or not isinstance(k.value, str):
                    raise CouldNotCheck(
                        'the PURPOSES key at %s line %d is not a plain string '
                        'literal, so the keys cannot be compared by value'
                        % (where, getattr(k, 'lineno', 0)))
                keys.append(k.value)
            return set(keys)
    raise CouldNotCheck('no module-level `PURPOSES = {...}` literal in %s, so '
                        'nothing was compared' % where)


def registry_tools(src, where=ROC):
    """Every `tool` named by the module-level `REGISTRY = [...]` literal.

    A REGISTRY entry whose `tool` is not a plain string is a COULD NOT CHECK and
    not a skip: a silently dropped entry reads downstream as an undescribed
    tool, which is a refusal this check would then be causing itself.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        raise CouldNotCheck('could not parse %s as Python (%s)' % (where, e))
    for st in tree.body:
        if (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)
                and st.targets[0].id == 'REGISTRY'
                and isinstance(st.value, (ast.List, ast.Tuple))):
            names = []
            for item in st.value.elts:
                if not isinstance(item, ast.Dict):
                    raise CouldNotCheck(
                        'a REGISTRY element at %s line %d is not a dict literal'
                        % (where, getattr(item, 'lineno', 0)))
                got = None
                for k, v in zip(item.keys, item.values):
                    if isinstance(k, ast.Constant) and k.value == 'tool':
                        if not isinstance(v, ast.Constant) or not isinstance(v.value, str):
                            raise CouldNotCheck(
                                'the REGISTRY `tool` at %s line %d is not a '
                                'plain string literal'
                                % (where, getattr(v, 'lineno', 0)))
                        got = v.value
                if got is None:
                    raise CouldNotCheck(
                        'a REGISTRY element at %s line %d carries no `tool` key'
                        % (where, getattr(item, 'lineno', 0)))
                names.append(got)
            return set(names)
    raise CouldNotCheck('no module-level `REGISTRY = [...]` literal in %s, so '
                        'nothing was compared' % where)


def added_tool_files(subject):
    """Basenames of the tools/*.py files `subject` ADDS.

    ADDS, not touches: the rule is about a tool arriving undescribed. An edit to
    an existing tool is somebody else's question and this stays silent on it.
    """
    if subject == '--pre-commit':
        out = _git('diff', '--cached', '--name-only', '--diff-filter=A')
    else:
        out = _git('diff', '--name-only', '--diff-filter=A', subject)
    names = []
    for line in out.splitlines():
        p = line.strip().replace('\\', '/')
        if p.startswith('tools/') and p.endswith('.py') and p.count('/') == 1:
            names.append(p[len('tools/'):])
    return names


def check(subject):
    """(exit, lines). Pure apart from git and two file reads."""
    added = added_tool_files(subject)
    if not added:
        return 0, ['commit_tool_entry_check: this commit adds no tools/*.py file.']
    if subject == '--pre-commit':
        inv_src, inv_from = _staged_source(INV)
        roc_src, roc_from = _staged_source(ROC)
    else:
        tip = subject.split('..')[-1] or 'HEAD'
        inv_src, inv_from = _source_at(INV, tip)
        roc_src, roc_from = _source_at(ROC, tip)
    described = purposes_keys(inv_src) | registry_tools(roc_src)
    missing = [t for t in added if t not in described]
    head = ['commit_tool_entry_check: %d tools/*.py added; PURPOSES read from the '
            '%s copy of %s, REGISTRY from the %s copy of %s.'
            % (len(added), inv_from, INV, roc_from, ROC)]
    if not missing:
        return 0, head + ['    all described: ' + ', '.join(sorted(added))]
    return 1, head + [
        '',
        'REFUSED: %d tools/*.py in this commit with no description:' % len(missing),
    ] + ['    ' + t for t in missing] + [
        '',
        "Michael's decision, 2026-09-13: no tools/ file is mergeable without a",
        'matching inventory entry. A blank cell is how the last inventory went',
        'stale, and a tool nobody described is one nobody can decide to run.',
        '',
        'Write a PURPOSES entry naming what it CATCHES -- not what it does --',
        'in %s, STAGE that file, and commit again:' % INV,
        '    git add ' + INV,
        '',
        'Or register it in %s if it is report-only; either satisfies this.' % ROC,
        '',
        'This is the SAME rule push-gate checks 12 and 14 enforce. It is asked',
        'here so the answer costs one line now instead of a blocked push queue',
        'later: the two tools that caused this check to exist went undescribed',
        'for five batches and 29 commits.',
    ]


# ── THE CRITERIA LOCK, BEFORE ANY REAL DATA (convention 1) ──────────────────
# Both directions, and the third arm is the one that would have made this tool
# WRONG: a tool described only in REGISTRY must PASS. Reading PURPOSES alone
# looks correct, passes the obvious fixtures, and refuses every report-only
# tool on the platform.
_FIX_INV = ('PURPOSES = {\n'
            "    'alpha.py': ('CHECKER', 'a thing'),\n"
            "    'beta.py': ('LIBRARY', 'another thing'),\n"
            '}\n')
_FIX_ROC = ('REGISTRY = [\n'
            "    {'tool': 'gamma.py', 'catches': 'a third thing'},\n"
            ']\n')


def fixtures():
    arms, bad = [], 0

    def arm(name, got, want):
        nonlocal bad
        ok = got == want
        if not ok:
            bad += 1
        arms.append('  %s %s -- got %r, want %r' % ('ok  ' if ok else 'FAIL', name, got, want))

    try:
        p = purposes_keys(_FIX_INV, 'fixture')
        r = registry_tools(_FIX_ROC, 'fixture')
        arm('PURPOSES keys read', sorted(p), ['alpha.py', 'beta.py'])
        arm('REGISTRY tools read', sorted(r), ['gamma.py'])
        arm('a PURPOSES tool is described', 'alpha.py' in (p | r), True)
        arm('a REGISTRY-ONLY tool is described', 'gamma.py' in (p | r), True)
        arm('an unentered tool is NOT described', 'delta.py' in (p | r), False)
    except CouldNotCheck as e:
        arm('the clean fixtures parse', 'CouldNotCheck: %s' % e, 'no exception')

    for name, src, reader in (
        ('a computed PURPOSES key refuses',
         'PURPOSES = {\n    "a" + "b": ("CHECKER", "x"),\n}\n', purposes_keys),
        ('a PURPOSES nested in a function is not the literal',
         'def f():\n    PURPOSES = {"alpha.py": 1}\n', purposes_keys),
        ('a REGISTRY element with no tool key refuses',
         'REGISTRY = [\n    {"catches": "x"},\n]\n', registry_tools),
        ('a non-literal REGISTRY tool refuses',
         'REGISTRY = [\n    {"tool": NAME},\n]\n', registry_tools),
        ('unparseable source refuses', 'def (\n', purposes_keys),
    ):
        try:
            reader(src, 'fixture')
            arm(name, 'returned a population', 'CouldNotCheck')
        except CouldNotCheck:
            arm(name, 'CouldNotCheck', 'CouldNotCheck')

    print('commit_tool_entry_check --fixtures: %d arm(s), %d failing' % (len(arms), bad))
    print('\n'.join(arms))
    return 1 if bad else 0


def main(argv):
    if '--fixtures' in argv:
        return fixtures()
    subject = '--pre-commit'
    if '--range' in argv:
        i = argv.index('--range')
        if i + 1 >= len(argv):
            print('COULD NOT CHECK: --range needs a revision range', file=sys.stderr)
            return 2
        subject = argv[i + 1]
    try:
        rc, lines = check(subject)
    except CouldNotCheck as e:
        print('COULD NOT CHECK -- %s' % e, file=sys.stderr)
        print('Exit 2 is not a pass and not a finding. Nothing was compared.',
              file=sys.stderr)
        return 2
    print('\n'.join(lines))
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
