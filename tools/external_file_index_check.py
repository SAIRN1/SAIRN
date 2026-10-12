#!/usr/bin/env python
# OWNER: cc
"""A tool, script or handoff outside git must be DECLARED, or it is invisible.

    python tools/external_file_index_check.py            # report
    python tools/external_file_index_check.py --count     # one number, for a hook
    python tools/external_file_index_check.py --fixtures  # the criteria lock, alone
    python tools/external_file_index_check.py --index <p> # check a different index

Exit 0 clean, 1 findings (unindexed external files), 2 COULD NOT RUN.
READ-ONLY: it lists directories and reads one JSON file. It writes nothing.

── THE DEFECT, MEASURED 2026-10-08 AND NOT HYPOTHETICAL ────────────────────────
`C:\\Users\\marsh\\` holds 335 loose .py/.js/.sh/.md files. 319 of them are
`chk_*.js`, `temp_check_*.js`, `final_check_*.js` and `script*.js` -- extracted
StoneDesk script blocks from ONE session on 2026-06-22/23, four months before
this check existed. Among them, found by this inventory and by nothing else:

  SAIRN-SESSION66-HANDOFF.md   A REAL HANDOFF, in git under NO name. The one
                               thing CLAUDE.md forbids by name: "Handoffs live
                               only in a real clone -- never write one to
                               C:\\Users\\marsh\\ directly." Committed as
                               docs/SAIRN-2026-07-26-session66-handoff.md.
  OLD-uncommitted-sairnlaw-trust-disbursement-2026-08-18.md
                               Carries its own note explaining it was RENAMED
                               after colliding with a real committed handoff and
                               a fresh session read the wrong one. Deliberately
                               out of git; indexed so the next inventory does
                               not re-litigate it.

A handoff nobody can find is worse than no handoff: the next session reads the
one it CAN find and continues the wrong work. That already happened once here.

── WHAT THIS REFUSES, AND THE THREE STATES IT KEEPS APART ──────────────────────
For every file under a DECLARED external directory whose extension is in
TRACKED_EXT, or whose name looks like a handoff:

  TRACKED    the path is also inside the repo and git-tracked. Fine.
  INDEXED    the index names it, with a purpose. Fine.
  UNINDEXED  neither. A FINDING -- exit 1.

AND THE INDEX'S ABSENCE IS NOT A PASS. If the index file does not exist this
exits 2 and says which path it looked for. A check whose data file is missing
reports a pass it never performed -- PR 1.11, the most expensive shape on this
platform. "Could not run" is a third state and is never folded into "passed".

── WHY THIS DOES NOT WRITE THE INDEX ───────────────────────────────────────────
`docs/external-files-index.json` is in CODY'S live claim at the time this was
written and did not yet exist. So this reads a schema it does not own and fails
CLOSED when it is absent, rather than creating a second competing index -- which
is the "second copy of something" defect this platform already records. The
schema it expects is documented in SCHEMA below and routed to that owner.
"""
import argparse
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join('docs', 'external-files-index.json')
CRITERIA_VERSION = '2026-10-08.2'
EXIT_COULD_NOT_RUN = 2

# A tool, a script or a handoff. NOT every file: a .json cache or a .lock is not
# work somebody could lose, and indexing them would bury the ones that are.
TRACKED_EXT = ('.py', '.js', '.sh', '.ps1')
HANDOFF_HINTS = ('handoff', 'HANDOFF')

SCHEMA = """{
 "_what_this_is": "...",
 "agents": {
   "<session>": {
     "dirs": [{"path": "<absolute or ~ path>",
               "purpose": "why this directory exists outside git",
               "transient": true | false,
               "recursive": true | false}],
     "files": [{"path": "<absolute or ~ path>",
                "purpose": "what it is and why it is not in git",
                "belongs_in_git": true | false}]
   }
 }
}
`transient: true` says every file under it is scratch by construction, so the
directory is declared once instead of its contents being enumerated for ever.
`recursive` DEFAULTS TO FALSE and that default was paid for: declaring the
machine home directory recursively reported 164,549 unindexed files -- every
node_modules, every clone, every cache -- which is a flood that hides the six
files that matter, not a finding. Turn it on per directory, deliberately.
`belongs_in_git: false` is a DECISION with a reason in `purpose`, not a default.
"""


def git_tracked():
    r = subprocess.run(['git', '-C', REPO, 'ls-files'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return None
    return {os.path.normcase(os.path.abspath(os.path.join(REPO, p.strip())))
            for p in (r.stdout or '').split('\n') if p.strip()}


def norm(p):
    return os.path.normcase(os.path.abspath(os.path.expanduser(str(p or ''))))


def is_work_file(path):
    """Is this a tool, a script or a handoff -- the three things the item names?"""
    base = os.path.basename(path)
    if base.lower().endswith(TRACKED_EXT):
        return True
    return any(h in base for h in HANDOFF_HINTS) and base.lower().endswith('.md')


def load_index(path):
    if not os.path.isfile(path):
        return None, ('%s does not exist, so NOTHING was checked. That is a '
                      'third state, not a pass: a check whose data file is '
                      'absent reports a pass it never performed.\n  The schema '
                      'this expects:\n%s' % (path, SCHEMA))
    try:
        doc = json.loads(io.open(path, encoding='utf-8').read())
    except (OSError, ValueError) as e:
        return None, '%s could not be read as JSON: %s' % (path, e)
    if not isinstance(doc, dict) or not isinstance(doc.get('agents'), dict):
        return None, ('%s has no `agents` object, so it is not this index and '
                      'nothing was checked.\n  Expected:\n%s' % (path, SCHEMA))
    return doc, ''


def declared(doc):
    """(dirs, transient_dirs, recursive_dirs, files) as normalised abs paths."""
    dirs, transient, recursive, files = {}, set(), set(), {}
    for sess, blk in (doc.get('agents') or {}).items():
        if not isinstance(blk, dict):
            continue
        for d in blk.get('dirs') or []:
            if not isinstance(d, dict) or not d.get('path'):
                continue
            n = norm(d['path'])
            dirs[n] = (sess, d.get('purpose') or '')
            if d.get('transient'):
                transient.add(n)
            if d.get('recursive'):
                recursive.add(n)
        for f in blk.get('files') or []:
            if not isinstance(f, dict) or not f.get('path'):
                continue
            files[norm(f['path'])] = (sess, f.get('purpose') or '')
    return dirs, transient, recursive, files


def under(path, directory):
    p, d = norm(path), norm(directory)
    return p == d or p.startswith(d.rstrip('\\/') + os.sep)


def classify(path, tracked, dirs, transient, files):
    """('TRACKED'|'INDEXED'|'TRANSIENT'|'UNINDEXED', detail)."""
    n = norm(path)
    if tracked is not None and n in tracked:
        return 'TRACKED', 'git-tracked inside the repo'
    if n in files:
        return 'INDEXED', '%s: %s' % files[n]
    for d in transient:
        if under(n, d):
            return 'TRANSIENT', 'under declared transient dir %s' % d
    return 'UNINDEXED', 'neither git-tracked nor named in the index'


def scan(dirs, transient, recursive, files, tracked):
    """Every work file under every declared dir, with its state.

    ── NON-RECURSIVE BY DEFAULT, AND MY OWN DRY RUN IS WHY (2026-10-08) ───────
    The first version walked every declared directory to its leaves. Pointed at
    the machine home directory it reported 164,549 UNINDEXED files -- every
    node_modules, every clone, every AppData cache -- which is not a finding,
    it is a flood that hides the six files that matter. The interesting ones sit
    at depth 1; recursion is now opt-in per directory via `recursive: true`.

    AND THE TRANSIENT SKIP WAS A NO-OP ON SUBTREES. `continue` on a matching
    root does not stop os.walk descending into its children, so a declared
    transient tree was still enumerated file by file. The same dry run showed
    it: TRANSIENT 0 with three transient directories declared. `_sub` is now
    pruned IN PLACE, which is the only thing os.walk honours.
    """
    out = []
    for d in sorted(dirs):
        if not os.path.isdir(d):
            out.append((d, 'DIR_MISSING',
                        'declared by %s and does not exist here' % dirs[d][0]))
            continue
        if any(under(d, t) for t in transient):
            continue                      # the whole tree is answered already
        if d not in recursive:
            try:
                names = [n for n in os.listdir(d)
                         if os.path.isfile(os.path.join(d, n))]
            except OSError as e:
                out.append((d, 'DIR_MISSING', 'could not be listed: %s' % e))
                continue
            for nm in names:
                full = os.path.join(d, nm)
                if is_work_file(full):
                    out.append((full,) + classify(full, tracked, dirs,
                                                  transient, files))
            continue
        for root, sub, names in os.walk(d):
            # PRUNED IN PLACE. Anything else leaves os.walk descending.
            sub[:] = [s for s in sub
                      if not any(under(os.path.join(root, s), t)
                                 for t in transient)]
            if any(under(root, t) for t in transient):
                sub[:] = []
                continue
            for nm in names:
                full = os.path.join(root, nm)
                if not is_work_file(full):
                    continue
                out.append((full,) + classify(full, tracked, dirs,
                                              transient, files))
    return out


# ── THE CRITERIA LOCK (discipline 1), on hand-built paths only ──────────────
# Every arm is paired: a shape that must reach one state AND one that must not.
def run_fixtures(verbose=False):
    bad, arms = [], 0
    T = {norm('/repo/tools/a.py')}
    D = {norm('/ext'): ('cc', 'why'), norm('/scratch'): ('cc', 'scratch')}
    TR = {norm('/scratch')}
    F = {norm('/ext/keepme.py'): ('cc', 'a real tool kept outside git')}
    cases = [
        ('/repo/tools/a.py', 'TRACKED', 'a git-tracked file is never a finding'),
        ('/ext/keepme.py', 'INDEXED', 'a file the index names, with a purpose'),
        ('/scratch/anything.py', 'TRANSIENT',
         'under a declared TRANSIENT dir -- answered at the directory level, '
         'because enumerating scratch for ever buries the real findings'),
        ('/scratch/deep/deeper/x.py', 'TRANSIENT',
         '...and transience is INHERITED, not just the top level'),
        ('/ext/stray.py', 'UNINDEXED',
         'a script under a declared dir that nothing names -- THE FINDING'),
        ('/ext/SESSION66-HANDOFF.md', 'UNINDEXED',
         'a HANDOFF outside git is the case this check exists for'),
    ]
    for p, want, why in cases:
        arms += 1
        got, _d = classify(p, T, D, TR, F)
        if got != want:
            bad.append('%s -- wanted %s got %s' % (why, want, got))
        elif verbose:
            print('  ok   %-9s %s' % (want, why))
    # is_work_file, both directions: the three things the item names, and not
    # the things it does not.
    for nm, want, why in (
            ('x.py', True, 'a python script'),
            ('x.js', True, 'a javascript file'),
            ('x.sh', True, 'a shell script'),
            ('x.ps1', True, 'a powershell script'),
            ('APP-2026-01-01-thing-handoff.md', True, 'a handoff by name'),
            ('notes.md', False,
             'an ordinary .md is NOT a handoff -- indexing every markdown file '
             'would bury the handoffs among them'),
            ('cc.lock', False, 'a lock file is not work somebody could lose'),
            ('cache.json', False, 'a cache is not a tool, script or handoff')):
        arms += 1
        got = is_work_file('/ext/' + nm)
        if got != want:
            bad.append('%s -- wanted %r got %r' % (why, want, got))
        elif verbose:
            print('  ok   %-9s %s' % (str(want), why))
    # AND THE MISSING INDEX MUST BE EXIT 2, NOT CLEAN.
    arms += 1
    _doc, err = load_index(os.path.join(REPO, '__no_such_index__.json'))
    if _doc is not None or 'third state' not in err:
        bad.append('an ABSENT index must be a could-not-run, not a pass')
    elif verbose:
        print('  ok   COULD_NOT  an ABSENT index is exit 2, never a clean pass')
    return bad, arms


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--count', action='store_true',
                    help='print only the unindexed count, for a session hook')
    ap.add_argument('--fixtures', action='store_true')
    ap.add_argument('--index', default=None)
    a = ap.parse_args(argv)

    bad, arms = run_fixtures(verbose=a.fixtures)
    if bad:
        if not a.count:
            print('EXTERNAL FILE INDEX -- criteria %s' % CRITERIA_VERSION)
            print('\nCRITERIA LOCK FAILED -- %d of %d:' % (len(bad), arms))
            for b in bad:
                print('  ! %s' % b)
            print('\nNOTHING REAL WAS SCANNED.')
        else:
            print('criteria lock failed -- could not run')
        return EXIT_COULD_NOT_RUN
    if a.fixtures:
        print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
              'paths only' % (arms, arms))
        return 0

    idx = a.index or os.path.join(REPO, INDEX)
    doc, err = load_index(idx)
    if doc is None:
        if a.count:
            # A HOOK GETS A WORD, NEVER A ZERO. Printing 0 here would be the
            # silent-pass shape: a session would read "0 unindexed" off a check
            # that never ran.
            print('UNKNOWN -- %s is absent, so nothing was checked'
                  % os.path.relpath(idx, REPO))
            return EXIT_COULD_NOT_RUN
        print('EXTERNAL FILE INDEX -- criteria %s' % CRITERIA_VERSION)
        print('\nCOULD NOT RUN: %s' % err)
        return EXIT_COULD_NOT_RUN

    tracked = git_tracked()
    dirs, transient, recursive, files = declared(doc)
    rows = scan(dirs, transient, recursive, files, tracked)
    unindexed = [r for r in rows if r[1] == 'UNINDEXED']
    missing = [r for r in rows if r[1] == 'DIR_MISSING']

    if a.count:
        print('%d' % len(unindexed))
        return 1 if unindexed else 0

    print('EXTERNAL FILE INDEX -- criteria %s' % CRITERIA_VERSION)
    print('criteria lock: %d/%d fixtures classify correctly' % (arms, arms))
    print('\n  index                 %s' % os.path.relpath(idx, REPO))
    print('  agents declared     %3d' % len(doc.get('agents') or {}))
    print('  dirs declared       %3d  (%d transient, %d recursive)'
          % (len(dirs), len(transient), len(recursive)))
    print('  files declared      %3d' % len(files))
    print('  git-tracked paths   %s'
          % ('COULD NOT READ -- git ls-files failed' if tracked is None
             else '%3d' % len(tracked)))
    for st in ('TRACKED', 'INDEXED', 'TRANSIENT', 'UNINDEXED'):
        print('  %-18s %3d' % (st, len([r for r in rows if r[1] == st])))

    if missing:
        print('\n%d declared director(ies) do not exist in this clone -- '
              'reported, not a finding:' % len(missing))
        for p, _st, why in missing:
            print('  ? %s -- %s' % (p, why))

    if unindexed:
        print('\n%d UNINDEXED work file(s) under a declared external directory. '
              'Each is a tool,\nscript or handoff that no other session can '
              'find:' % len(unindexed))
        for p, _st, _why in unindexed[:40]:
            print('  ! %s' % p)
        if len(unindexed) > 40:
            print('  ... and %d more' % (len(unindexed) - 40))
        print('\nEither commit it, or add it to %s with a purpose.'
              % os.path.relpath(idx, REPO))
        return 1

    print('\nCLEAN -- every work file under a declared external directory is '
          'either git-tracked\nor named in the index.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
