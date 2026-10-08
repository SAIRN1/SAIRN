#!/usr/bin/env python
"""hover2_external_file_check.py (batch Q item 4) -- fails when a tool,
script or handoff sits in one of this role's own DECLARED external
directories and is neither git-tracked (for the ones meant to be
duplicated into the clone) nor named in hover2-external-files-index.json.

WHY. Item 3 this same batch found hover2_code_normalize.py sitting ONLY at
the log-repo path for 12+ days, cited as committed when it never was
(seq626). The index built in that item records what is KNOWN to be there
and why; this tool is what makes a FUTURE untracked file visible instead of
silently joining the pile.

RULE: for each declared directory that is not blanket-exempt, every real
file (not a subdirectory) must be either (a) listed in the index's
"indexed" array, (b) match the directory's "handoff_glob_prefix" (handoffs
are open-ended by nature -- gating on an exact filename list would refuse
every new date), or (c) resolve as a git-tracked blob under
.claude/skills/sairn-hover-auditor/tools-hover2/ in the platform repo (for
genuinely new tools that landed there first and have not yet been added to
the index by name -- being committed is itself sufficient evidence of
intent, same standard citation_resolve_check.py already uses for --ref).
Anything matching NONE of the three is UNINDEXED and fails the check.

Exit 0: zero unindexed files. Exit 1: N unindexed files found, each
printed with its full path. Exit 2: COULD NOT RUN (index missing/unreadable,
or a declared directory's path cannot be resolved from the template).

Run:
  python hover2_external_file_check.py [--repo PATH]
  python hover2_external_file_check.py --selftest
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_JSON = os.path.join(HERE, 'hover2-external-files-index.json')
DEFAULT_REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))


def resolve_template(template):
    """~/... templates resolve against the real home dir. A '*' segment
    (used only for the scratchpad template, which is blanket-exempt and
    therefore never actually globbed by this function) is left as-is --
    callers must check blanket_exempt before trying to resolve it."""
    if template.startswith('~/'):
        return os.path.join(os.path.expanduser('~'), *template[2:].split('/'))
    return template


def git_tracked_tools(repo):
    try:
        out = subprocess.run(
            ['git', 'ls-tree', '-r', '--name-only', 'HEAD',
             '.claude/skills/sairn-hover-auditor/tools-hover2/'],
            cwd=repo, capture_output=True, text=True, check=True)
    except Exception:
        return set()
    return {os.path.basename(p) for p in out.stdout.splitlines()}


def check_directory(entry, repo):
    """Returns (unindexed: list[str], could_not_run: str|None)."""
    if entry.get('blanket_exempt'):
        return [], None
    path = resolve_template(entry['path_template'])
    if '*' in path or not os.path.isdir(path):
        return [], 'directory not resolvable: %s' % entry['path_template']

    indexed = set(entry.get('indexed', []))
    handoff_prefix = entry.get('handoff_glob_prefix')
    tracked = git_tracked_tools(repo)

    unindexed = []
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if not os.path.isfile(full):
            continue
        if name in indexed:
            continue
        if handoff_prefix and name.startswith(handoff_prefix):
            continue
        if name in tracked:
            continue
        unindexed.append(full)
    return unindexed, None


def run(index_path, repo):
    if not os.path.isfile(index_path):
        print("COULD NOT RUN: index not found: %s" % index_path)
        return 2
    try:
        index = json.load(open(index_path, encoding='utf-8'))
    except Exception as e:
        print("COULD NOT RUN: index unreadable: %s" % e)
        return 2

    total_unindexed = []
    for entry in index.get('directories', []):
        unindexed, err = check_directory(entry, repo)
        if err:
            print("COULD NOT RUN: %s (%s)" % (err, entry.get('key')))
            return 2
        total_unindexed.extend(unindexed)

    print("UNINDEXED COUNT: %d" % len(total_unindexed))
    for p in total_unindexed:
        print("  UNINDEXED: %s" % p)
    return 1 if total_unindexed else 0


def _selftest():
    import tempfile
    import shutil

    tmp = tempfile.mkdtemp(prefix='extfilecheck_')
    try:
        ext_dir = os.path.join(tmp, 'external')
        os.makedirs(ext_dir)
        with open(os.path.join(ext_dir, 'known.py'), 'w') as f:
            f.write('# known\n')
        with open(os.path.join(ext_dir, 'handoff-x-2026-01-01.md'), 'w') as f:
            f.write('# handoff\n')
        with open(os.path.join(ext_dir, 'surprise.py'), 'w') as f:
            f.write('# never indexed\n')

        repo = os.path.join(tmp, 'repo')
        os.makedirs(repo)
        subprocess.run(['git', 'init', '-q'], cwd=repo, check=True)
        subprocess.run(['git', 'config', 'user.email', 'x@example.invalid'], cwd=repo, check=True)
        subprocess.run(['git', 'config', 'user.name', 'x'], cwd=repo, check=True)
        toolsdir = os.path.join(repo, '.claude', 'skills', 'sairn-hover-auditor', 'tools-hover2')
        os.makedirs(toolsdir)
        with open(os.path.join(toolsdir, 'seed.txt'), 'w') as f:
            f.write('seed\n')
        subprocess.run(['git', 'add', '-A'], cwd=repo, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'seed'], cwd=repo, check=True)

        index_path = os.path.join(tmp, 'index.json')
        index = {"directories": [
            {"key": "ext", "path_template": ext_dir, "indexed": ["known.py"],
             "handoff_glob_prefix": "handoff-x-"}
        ]}
        with open(index_path, 'w') as f:
            json.dump(index, f)

        # ARM 1: surprise.py is neither indexed, nor a handoff, nor
        # git-tracked -> must be flagged UNINDEXED, count 1.
        rc = run(index_path, repo)
        assert rc == 1, "expected exit 1 with one unindexed file, got %r" % rc

        # ARM 2 (the real transition, not a planted fixture): actually
        # COMMIT surprise.py into the clone's tools-hover2/ dir for real,
        # then re-check -- it must now pass via the git-tracked path.
        with open(os.path.join(toolsdir, 'surprise.py'), 'w') as f:
            f.write('# now real\n')
        subprocess.run(['git', 'add', '-A'], cwd=repo, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'land surprise.py'], cwd=repo, check=True)
        rc2 = run(index_path, repo)
        assert rc2 == 0, "expected exit 0 after committing surprise.py, got %r" % rc2

        # ARM 3: a file indexed by NAME (not committed) must also pass --
        # confirms the "indexed" path works independent of git.
        with open(os.path.join(ext_dir, 'also_known.py'), 'w') as f:
            f.write('# also known\n')
        index["directories"][0]["indexed"].append('also_known.py')
        with open(index_path, 'w') as f:
            json.dump(index, f)
        rc3 = run(index_path, repo)
        assert rc3 == 0, "expected exit 0 for a by-name-indexed file, got %r" % rc3

        # ARM 4: blanket_exempt directory is never even listed, regardless
        # of what unindexed garbage is in it.
        exempt_dir = os.path.join(tmp, 'exempt')
        os.makedirs(exempt_dir)
        with open(os.path.join(exempt_dir, 'anything.py'), 'w') as f:
            f.write('# anything\n')
        index["directories"].append(
            {"key": "exempt", "path_template": exempt_dir, "blanket_exempt": True})
        with open(index_path, 'w') as f:
            json.dump(index, f)
        rc4 = run(index_path, repo)
        assert rc4 == 0, "blanket_exempt directory must not be scanned, got %r" % rc4

        print("ALL SELFTEST CASES PASS")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=DEFAULT_REPO)
    ap.add_argument('--index', default=INDEX_JSON)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    return run(args.index, args.repo)


if __name__ == '__main__':
    sys.exit(main())
