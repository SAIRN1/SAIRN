#!/usr/bin/env python
r"""hover_external_unindexed_check.py -- does any tool, script or handoff
this role could plausibly own sit in an external directory, neither
git-tracked nor named in EXTERNAL-TOOLS-INDEX.md.

H1 batch X item 2. EXTERNAL-TOOLS-INDEX.md (batch T) is a human-read
inventory, built once, by hand, from a snapshot. This is its mechanical
counterpart: run fresh every session, over every directory this role
actually writes to, and refuse to let a NEW external file go unindexed
the way the original hover_cross_resource_gate_check.py did for two whole
batches before anyone checked.

FOUR DIRECTORIES, PER THIS BATCH'S OWN INSTRUCTION:
  1. The external working directory
     (.claude/projects/.../hover-audit-log/) -- scanned FULLY, every file,
     because this is the one directory where "anything here is plausibly
     mine" is actually true.
  2. This session's own scratchpad -- scanned for hover-NAMED files only
     (see below); everything else there is legitimately transient scratch
     by design and flagging it would be noise, not a finding.
  3. The home directory root (non-recursive) -- scanned for hover-named
     files only. FOUND DURING THIS TOOL'S OWN FIRST REAL RUN: the home
     root carries ~100 unrelated chk_N.js / apibridge.js files, almost
     certainly another process's node --check extraction litter, not this
     role's. A name filter is not a convenience here, it is the
     difference between a real check and a report dominated by someone
     else's scratch files.
  4. The system temp directory (top level + the claude/ subtree) --
     same name-filtered scope as above.

NAME FILTER, used for directories 2-4: a file counts as plausibly this
role's own if its basename starts with `hover`, `chain-tip-`, or
`TIP-BEACON`, OR if its basename already appears somewhere in
EXTERNAL-TOOLS-INDEX.md (so a file renamed away from the `hover` prefix
but still indexed is not falsely flagged as new). Directory 1 gets no
filter -- every file there is checked.

A file is UNINDEXED if its basename is neither (a) a basename present
anywhere in `git ls-tree -r origin/main` nor (b) a basename appearing in
EXTERNAL-TOOLS-INDEX.md (which also names, with a reason, the files this
role deliberately keeps external forever -- the chain log itself,
mirror credentials, RFC 3161 point-in-time artifacts). Those reasoned
exclusions are read from the index, not hardcoded a second time here,
so the two lists cannot drift apart silently.

Read-only. Never writes, never deletes.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
EXT_DIR = r'C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hover\hover-audit-log'
HOME_DIR = r'C:\Users\marsh'
TEMP_DIR = r'C:\Users\marsh\AppData\Local\Temp'
INDEX_FILE = os.path.join(REPO, '.claude', 'skills', 'sairn-hover-auditor',
                           'EXTERNAL-TOOLS-INDEX.md')

NAME_FILTER_RE = re.compile(r'^(hover|chain-tip-|TIP-BEACON)', re.I)
SKIP_DIR_NAMES = {'.git', '__pycache__', 'node_modules'}


def discover_repo():
    for cand in (os.environ.get('HOVER_PROBE_REPO'), REPO,
                 r'C:\Users\marsh\Documents\SAIRN-hover'):
        if cand and os.path.isdir(os.path.join(cand, '.git')):
            return cand
    return None


def git_tracked_basenames(repo):
    try:
        r = subprocess.run(['git', 'ls-tree', '-r', 'origin/main', '--name-only'],
                            cwd=repo, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, 'could not run git ls-tree: %s' % e
    if r.returncode != 0:
        return None, 'git ls-tree failed (rc=%d)' % r.returncode
    return set(os.path.basename(p) for p in r.stdout.splitlines() if p.strip()), None


# FOUND on this tool's own second real run: `.mirror-token` is a bare
# dotfile with no recognized extension (the name IS "token" after one
# leading dot, no further "."), so the extension-based pattern alone
# missed it even though it is correctly backtick-named in the index.
# A dotfile with no further extension is accepted as a second shape.
_FILENAME_RE = re.compile(
    r'^([A-Za-z0-9_.\-]+\.(?:py|js|md|json|jsonl|pem|crt|txt|bat|out)|\.[A-Za-z0-9_\-]+)$')


def index_basenames(index_path):
    if not os.path.isfile(index_path):
        return None, 'EXTERNAL-TOOLS-INDEX.md not found at %s' % index_path
    with open(index_path, encoding='utf-8') as f:
        src = f.read()
    names = set()
    # FOUND ON THIS TOOL'S OWN FIRST REAL RUN: the index's "deliberately
    # not committed" table lists several filenames in ONE backtick span,
    # comma- or slash-separated (e.g. "`class_detail.json, none27_fresh
    # .json, ...`" and "`freetsa-cacert.pem / freetsa-tsa.crt`") rather
    # than one backtick pair per name. A regex requiring the WHOLE
    # backtick span to be a single filename matched none of them --
    # 12 real, already-reasoned exclusions read as unindexed. Split each
    # span on both separators before testing each piece.
    for span in re.findall(r'`([^`]+)`', src):
        for piece in re.split(r'[,/]', span):
            piece = piece.strip()
            if _FILENAME_RE.match(piece):
                names.add(piece)
    # chain-tip-seq*.msg/.tsr/.tsq are named with a glob in the index text
    # (`chain-tip-seq*.msg / .tsr / .tsq`) rather than one literal name per
    # file -- expand that convention here rather than re-list every seq.
    if 'chain-tip-seq' in src:
        names.add('__GLOB__chain-tip-seq')
    return names, None


def is_indexed(basename, git_names, idx_names):
    if basename in git_names or basename in idx_names:
        return True
    if '__GLOB__chain-tip-seq' in idx_names and re.match(r'^chain-tip-seq\d+\.(msg|tsr|tsq)$', basename):
        return True
    return False


def scan_full(dir_path):
    out = []
    if not os.path.isdir(dir_path):
        return out
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
        for fn in files:
            out.append(os.path.join(root, fn))
    return out


def scan_filtered_top_level(dir_path):
    out = []
    if not os.path.isdir(dir_path):
        return out
    try:
        entries = os.listdir(dir_path)
    except OSError:
        return out
    for fn in entries:
        full = os.path.join(dir_path, fn)
        if os.path.isfile(full) and NAME_FILTER_RE.match(fn):
            out.append(full)
    return out


def scan_filtered_recursive(dir_path, max_depth=2):
    out = []
    if not os.path.isdir(dir_path):
        return out
    base_depth = dir_path.rstrip('\\/').count(os.sep)
    for root, dirs, files in os.walk(dir_path):
        depth = root.rstrip('\\/').count(os.sep) - base_depth
        if depth >= max_depth:
            dirs[:] = []
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
        for fn in files:
            if NAME_FILTER_RE.match(fn):
                out.append(os.path.join(root, fn))
    return out


def run(scratchpad_dir=None):
    repo = discover_repo()
    if not repo:
        return {'error': 'no known hover-visible clone found'}
    git_names, err1 = git_tracked_basenames(repo)
    if err1:
        return {'error': err1}
    idx_names, err2 = index_basenames(INDEX_FILE)
    if err2:
        return {'error': err2}

    candidates = []
    candidates += [('working-dir', p) for p in scan_full(EXT_DIR)]
    if scratchpad_dir:
        candidates += [('scratchpad', p) for p in scan_filtered_top_level(scratchpad_dir)]
    candidates += [('home', p) for p in scan_filtered_top_level(HOME_DIR)]
    candidates += [('temp', p) for p in scan_filtered_recursive(TEMP_DIR, max_depth=3)]

    unindexed = []
    for location, path in candidates:
        base = os.path.basename(path)
        if not is_indexed(base, git_names, idx_names):
            unindexed.append((location, path))
    return {'checked': len(candidates), 'unindexed': unindexed}


def main(argv):
    scratchpad = None
    if '--scratchpad' in argv:
        scratchpad = argv[argv.index('--scratchpad') + 1]
    report = run(scratchpad)
    if report.get('error'):
        print('COULD NOT RUN: %s' % report['error'])
        return 2
    print('Checked %d candidate files across working-dir/scratchpad/home/temp.'
          % report['checked'])
    print('UNINDEXED COUNT: %d' % len(report['unindexed']))
    for location, path in report['unindexed']:
        print('  [%s] %s' % (location, path))
    if '--json' in argv:
        print(json.dumps(report, indent=1))
    return 1 if report['unindexed'] else 0


def _selftest():
    import tempfile
    failures = []

    def chk(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, 'repo', '.git'))
        os.makedirs(os.path.join(td, 'ext'))
        os.makedirs(os.path.join(td, 'home'))
        os.makedirs(os.path.join(td, 'scratch'))
        skill_dir = os.path.join(td, 'repo', '.claude', 'skills', 'sairn-hover-auditor')
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, 'EXTERNAL-TOOLS-INDEX.md'), 'w') as f:
            f.write('| `hover_tracked.py` | path | purpose |\n'
                    '| `chain-tip-seq*.msg / .tsr / .tsq` | path | RFC3161 |\n'
                    '| `class_detail.json, none27_fresh.json, hover_multi_name.py` | path | comma-separated cell |\n'
                    '| `.mirror-hover-token` | path | bare dotfile, no extension |\n')
        with open(os.path.join(td, 'ext', 'hover_multi_name.py'), 'w') as f:
            f.write('print(4)\n')
        with open(os.path.join(td, 'ext', '.mirror-hover-token'), 'w') as f:
            f.write('secret\n')
        with open(os.path.join(td, 'ext', 'hover_tracked.py'), 'w') as f:
            f.write('print(1)\n')
        with open(os.path.join(td, 'ext', 'chain-tip-seq42.msg'), 'w') as f:
            f.write('x\n')
        with open(os.path.join(td, 'ext', 'hover_NEW_untracked.py'), 'w') as f:
            f.write('print(2)\n')
        with open(os.path.join(td, 'home', 'chk_999.js'), 'w') as f:
            f.write('// unrelated litter\n')
        with open(os.path.join(td, 'home', 'hover_stray.py'), 'w') as f:
            f.write('print(3)\n')

        global EXT_DIR, HOME_DIR, TEMP_DIR, INDEX_FILE, REPO
        real = (EXT_DIR, HOME_DIR, TEMP_DIR, INDEX_FILE, REPO)
        EXT_DIR = os.path.join(td, 'ext')
        HOME_DIR = os.path.join(td, 'home')
        TEMP_DIR = os.path.join(td, 'nonexistent-temp')
        INDEX_FILE = os.path.join(skill_dir, 'EXTERNAL-TOOLS-INDEX.md')
        REPO = os.path.join(td, 'repo')
        try:
            # Case 1: planted directly.
            report = run(os.path.join(td, 'scratch'))
            unindexed_names = set(os.path.basename(p) for _, p in report['unindexed'])
            chk('hover_tracked.py (indexed) is NOT flagged',
                'hover_tracked.py' not in unindexed_names)
            chk('chain-tip-seq42.msg (glob-indexed) is NOT flagged',
                'chain-tip-seq42.msg' not in unindexed_names)
            chk('hover_NEW_untracked.py (genuinely new) IS flagged',
                'hover_NEW_untracked.py' in unindexed_names)
            chk("chk_999.js (unrelated litter, no hover-prefix) is NOT flagged",
                'chk_999.js' not in unindexed_names)
            chk('hover_stray.py in home (hover-prefixed, unindexed) IS flagged',
                'hover_stray.py' in unindexed_names)
            chk('hover_multi_name.py (named in a COMMA-SEPARATED index cell) is NOT flagged',
                'hover_multi_name.py' not in unindexed_names)
            chk('.mirror-hover-token (bare dotfile, indexed) is NOT flagged',
                '.mirror-hover-token' not in unindexed_names)

            # Case 2: the real transition -- the new file is committed
            # (simulated by adding it to the index text), same tool, same
            # directory, nothing else changes, and the SAME file that was
            # flagged now clears.
            with open(INDEX_FILE, 'a') as f:
                f.write('| `hover_NEW_untracked.py` | path | purpose |\n')
            report2 = run(os.path.join(td, 'scratch'))
            unindexed_names2 = set(os.path.basename(p) for _, p in report2['unindexed'])
            chk('after indexing it (real transition), hover_NEW_untracked.py clears',
                'hover_NEW_untracked.py' not in unindexed_names2)
            chk('hover_stray.py is STILL flagged -- the transition only touched one file',
                'hover_stray.py' in unindexed_names2)
        finally:
            EXT_DIR, HOME_DIR, TEMP_DIR, INDEX_FILE, REPO = real

    print()
    print('SELFTEST %s (%d/%d)' % ('PASS' if not failures else 'FAIL', 9 - len(failures), 9))
    return 0 if not failures else 1


if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--selftest' in argv:
        sys.exit(_selftest())
    sys.exit(main(argv))
