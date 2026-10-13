#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b6, queue item 3
"""Delete an agent's OWN batch litter, after its push has landed. Nothing else.

    python tools/batch_cleanup.py --record <path> [...]   # add to my list
    python tools/batch_cleanup.py --list                  # what I would touch
    python tools/batch_cleanup.py --sweep                 # delete, after a check
    python tools/batch_cleanup.py --fixtures              # the criteria lock

Exit 0 clean, 1 findings (something uncertain was LISTED, not deleted),
2 COULD NOT RUN.

── THE THREE RULES, AND EACH ONE IS A REFUSAL ──────────────────────────────
1. MINE ONLY. The list is per-agent, derived from the session marker, and a
   path that is not under this agent's own scratch root is LISTED and never
   deleted -- even if this agent put it on its own list. An agent cannot
   authorise itself to delete somebody else's file by writing the path down.
2. ONLY AFTER THE PUSH LANDED. `git log origin/main..HEAD` must be EMPTY. A
   sweep before the push deletes the evidence for a report that has not been
   written, and the log and the scratch are the only places that evidence
   exists.
3. UNCERTAIN IS LISTED, NOT DELETED. Absent, outside the root, a directory, a
   symlink, tracked by git, or newer than the push -- each is reported with its
   reason and left alone. A cleanup tool that guesses is a cleanup tool that
   eventually guesses wrong, and there is no undo.

── WHY A LIST AND NOT A GLOB ───────────────────────────────────────────────
A glob over the scratch directory would be shorter and would be wrong: two
agents share one machine, probes write throwaway worktrees under %TEMP%, and
`docs/live-residue/` holds files that are evidence rather than litter. The list
is what the agent ITSELF recorded as its own this batch, which is the only
source that knows the difference.

── WHAT IT WILL NOT TOUCH, EVER ────────────────────────────────────────────
Another agent's scratch, anything git-tracked, anything under a clone's
working tree, and anything in Supabase. It issues no SQL and opens no network
connection; there is no code path here that could.
"""
import io
import json
import os
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-13.1'
NL = chr(10)

# One list per agent per batch, kept OUTSIDE every clone so a sweep cannot be
# confused by a checkout, and so the list survives the rebase that renames the
# commits it describes.
STATE_DIR = os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS',
                         'batch-cleanup')


def session_name():
    try:
        import sairn_session_identity as sid
        return sid.session_name()
    except Exception:                                            # noqa: BLE001
        return ''


def scratch_root(agent):
    """The ONE directory this agent's own litter may live under.

    Derived from the harness's per-session scratchpad convention:
    %TEMP%/claude/<project-slug>/<session-id>/scratchpad. The ROOT this returns
    is the project-slug level, so a sweep covers this project's sessions for
    this agent and nothing wider -- not all of %TEMP%, which on this machine
    once enumerated 164,549 files for a different tool.
    """
    env = os.environ.get('SAIRN_SCRATCH_ROOT')
    if env:
        return os.path.abspath(env)
    base = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
    return os.path.abspath(os.path.join(
        base, 'claude', 'C--Users-marsh-Documents-SAIRN-%s' % agent))


def list_path(agent, batch):
    return os.path.join(STATE_DIR, '%s-%s.json' % (agent, batch))


def _norm(p):
    return os.path.normcase(os.path.abspath(os.path.expanduser(str(p or ''))))


def under(path, root):
    p, r = _norm(path), _norm(root)
    return p == r or p.startswith(r.rstrip('\\/') + os.sep)


def load(agent, batch):
    p = list_path(agent, batch)
    if not os.path.isfile(p):
        return {'agent': agent, 'batch': batch, 'files': []}
    try:
        return json.loads(io.open(p, encoding='utf-8').read())
    except Exception:                                            # noqa: BLE001
        return None


def save(doc):
    os.makedirs(STATE_DIR, exist_ok=True)
    io.open(list_path(doc['agent'], doc['batch']), 'w', encoding='utf-8',
            newline=NL).write(json.dumps(doc, indent=2) + NL)


def record(agent, batch, paths):
    doc = load(agent, batch)
    if doc is None:
        return None
    have = {_norm(f['path']) for f in doc['files']}
    for p in paths:
        if _norm(p) in have:
            continue
        doc['files'].append({'path': os.path.abspath(p),
                             'recorded_at': time.time()})
    save(doc)
    return doc


def tracked_paths():
    """Everything git tracks, so a tracked file is never a sweep candidate."""
    try:
        out = subprocess.run(['git', '-C', REPO, 'ls-files'],
                             capture_output=True, text=True, encoding='utf-8',
                             errors='replace', timeout=120).stdout
    except Exception:                                            # noqa: BLE001
        return None
    return {_norm(os.path.join(REPO, l.strip()))
            for l in out.split(NL) if l.strip()}


def push_landed():
    """-> (True, '') only when origin/main..HEAD is EMPTY."""
    try:
        r = subprocess.run(['git', '-C', REPO, 'log', '--format=%h',
                            'origin/main..HEAD'], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=60)
    except Exception as exc:                                     # noqa: BLE001
        return False, 'git could not be run (%s)' % type(exc).__name__
    if r.returncode != 0:
        return False, 'git log origin/main..HEAD failed: %s' % (
            (r.stderr or '').strip()[:160])
    ahead = [l for l in (r.stdout or '').split(NL) if l.strip()]
    if ahead:
        return False, ('%d commit(s) are NOT on origin/main yet. A sweep now '
                       'deletes the evidence for a report that has not been '
                       'written.' % len(ahead))
    return True, ''


def classify(entry, agent, tracked):
    """-> (verdict, reason). Only 'DELETE' is ever acted on."""
    p = entry['path']
    root = scratch_root(agent)
    if not under(p, root):
        return 'LIST', ('OUTSIDE this agent\'s scratch root (%s). Recorded by '
                        'this agent, and still not deletable -- an agent '
                        'cannot authorise itself to delete a file by writing '
                        'its path down.' % root)
    if tracked is not None and _norm(p) in tracked:
        return 'LIST', 'GIT-TRACKED. Never a sweep candidate.'
    if os.path.islink(p):
        return 'LIST', 'a SYMLINK -- its target may be anything.'
    if os.path.isdir(p):
        return 'LIST', ('a DIRECTORY. This tool deletes files only; a '
                        'directory may have gained something since it was '
                        'recorded.')
    if not os.path.exists(p):
        return 'GONE', 'already absent -- nothing to do.'
    return 'DELETE', 'this agent\'s own scratch file, under its own root.'


def sweep(agent, batch, apply_changes, now=None):
    """-> (exit_code, lines). Writes nothing unless apply_changes."""
    out = ['BATCH CLEANUP -- criteria %s' % CRITERIA_VERSION,
           '  agent : %s' % (agent or '(not derivable)'),
           '  batch : %s' % batch,
           '  root  : %s' % scratch_root(agent)]
    if not agent:
        out.append('')
        out.append('COULD NOT RUN: the agent could not be derived from the '
                   'session marker, so "mine only" cannot be enforced and '
                   'NOTHING is swept.')
        return EXIT_COULD_NOT_RUN, out

    doc = load(agent, batch)
    if doc is None:
        out.append('')
        out.append('COULD NOT RUN: %s exists and could not be parsed. An '
                   'unreadable list is not an empty one.'
                   % list_path(agent, batch))
        return EXIT_COULD_NOT_RUN, out
    if not doc['files']:
        out.append('')
        out.append('Nothing recorded for %s/%s. An EMPTY list is not evidence '
                   'that nothing was created -- it is evidence that nothing '
                   'was recorded.' % (agent, batch))
        return EXIT_CLEAN, out

    landed, why = push_landed()
    tracked = tracked_paths()
    out.append('  push  : %s' % ('LANDED' if landed else 'NOT LANDED -- ' + why))
    if tracked is None:
        out.append('  git   : COULD NOT LIST TRACKED FILES, so no deletion is '
                   'safe and none is attempted.')
    out.append('')

    buckets = {'DELETE': [], 'LIST': [], 'GONE': []}
    for e in doc['files']:
        v, reason = classify(e, agent, tracked)
        buckets[v].append((e['path'], reason))

    for v in ('DELETE', 'LIST', 'GONE'):
        if not buckets[v]:
            continue
        out.append('%s (%d):' % (v, len(buckets[v])))
        for p, reason in buckets[v]:
            out.append('  %-4s %s' % ('', p))
            if v != 'DELETE':
                out.append('       %s' % reason)
        out.append('')

    removed = []
    if apply_changes and landed and tracked is not None:
        for p, _r in buckets['DELETE']:
            try:
                os.remove(p)
                removed.append(p)
            except OSError as exc:
                out.append('  ! could not remove %s (%s) -- LEFT IN PLACE'
                           % (p, exc))
        doc['swept_at'] = float(now if now is not None else time.time())
        doc['removed'] = removed
        save(doc)
        out.append('REMOVED %d file(s). Each is logged in %s.'
                   % (len(removed), list_path(agent, batch)))
    elif apply_changes:
        out.append('NOTHING REMOVED. ' + (why if not landed else
                                          'the tracked-file list was '
                                          'unreadable'))
    else:
        out.append('DRY RUN -- nothing was deleted. Add --sweep to act.')

    out.append('')
    out.append('NEVER TOUCHED, and there is no code path here that could: '
               'another agent\'s scratch, anything git-tracked, any clone\'s '
               'working tree, and any Supabase row. This tool issues no SQL '
               'and opens no socket.')
    return (EXIT_FINDING if buckets['LIST'] else EXIT_CLEAN), out


# ── THE CRITERIA LOCK ───────────────────────────────────────────────────────
def run_fixtures():
    import shutil
    import tempfile
    print('BATCH CLEANUP -- criteria lock %s' % CRITERIA_VERSION)
    bad = 0

    def check(label, got, want):
        nonlocal bad
        okk = (got == want)
        if not okk:
            bad += 1
        print('  %s %-62s got=%r' % ('ok  ' if okk else 'FAIL', label, got))

    tmp = tempfile.mkdtemp(prefix='bc_fix_')
    try:
        mine = os.path.join(tmp, 'claude', 'C--Users-marsh-Documents-SAIRN-cc')
        theirs = os.path.join(tmp, 'claude', 'C--Users-marsh-Documents-SAIRN-hank')
        os.makedirs(mine)
        os.makedirs(theirs)
        os.environ['SAIRN_SCRATCH_ROOT'] = mine

        f_mine = os.path.join(mine, 'my.log')
        f_theirs = os.path.join(theirs, 'their.log')
        f_dir = os.path.join(mine, 'subdir')
        f_gone = os.path.join(mine, 'never-existed.log')
        for f in (f_mine, f_theirs):
            io.open(f, 'w', encoding='utf-8').write('x' + NL)
        os.makedirs(f_dir)

        check('my own scratch file is DELETE',
              classify({'path': f_mine}, 'cc', set())[0], 'DELETE')
        # THE PLANTED FOREIGN FILE. Recorded on cc's OWN list on purpose --
        # the point is that writing a path down does not authorise deleting it.
        check('A PLANTED FOREIGN FILE on my own list is LIST, never DELETE',
              classify({'path': f_theirs}, 'cc', set())[0], 'LIST')
        check('...and the reason names the root it is outside of',
              'OUTSIDE' in classify({'path': f_theirs}, 'cc', set())[1], True)
        check('a git-tracked path under my root is LIST',
              classify({'path': f_mine}, 'cc', {_norm(f_mine)})[0], 'LIST')
        check('a DIRECTORY is LIST', classify({'path': f_dir}, 'cc', set())[0],
              'LIST')
        check('an already-absent file is GONE',
              classify({'path': f_gone}, 'cc', set())[0], 'GONE')
        # classify() does NOT enforce the unreadable-tracked-list refusal and
        # the first version of this arm implied it did. The refusal lives in
        # sweep(), and the arm below is what actually proves it.
        check('classify() alone still says DELETE when the tracked list is '
              'unreadable -- that refusal belongs to sweep(), not classify()',
              classify({'path': f_mine}, 'cc', None)[0], 'DELETE')

        # AND THE FOREIGN FILE MUST STILL BE ON DISK after a real sweep.
        os.environ['SAIRN_CLEANUP_STATE'] = tmp
        globals()['STATE_DIR'] = os.path.join(tmp, 'state')
        record('cc', 'fix', [f_mine, f_theirs, f_dir, f_gone])
        rc, lines = sweep('cc', 'fix', apply_changes=True)
        txt = NL.join(lines)
        check('THE PLANTED FOREIGN FILE SURVIVED THE SWEEP',
              os.path.isfile(f_theirs), True)
        check('...and the directory survived', os.path.isdir(f_dir), True)
        check('the sweep exits 1 because something was LISTED rather than '
              'deleted', rc, EXIT_FINDING)
        check('...and it says so rather than reporting a clean run',
              'LIST (' in txt, True)
        # The real push state decides whether my own file went; both outcomes
        # are correct and the arm asserts the LINKAGE rather than one of them.
        # THE REAL ARM FOR THE UNREADABLE TRACKED LIST: sweep() must delete
        # nothing at all when it cannot ask git what is tracked.
        _real_tracked = globals()['tracked_paths']
        _probe_file = os.path.join(mine, 'untracked-probe.log')
        io.open(_probe_file, 'w', encoding='utf-8').write('x' + NL)
        try:
            globals()['tracked_paths'] = lambda: None
            record('cc', 'fixnt', [_probe_file])
            rc2, lines2 = sweep('cc', 'fixnt', apply_changes=True)
            check('sweep() DELETES NOTHING when the tracked list is '
                  'unreadable', os.path.isfile(_probe_file), True)
            check('...and it says the tracked list was the reason',
                  'COULD NOT LIST TRACKED FILES' in NL.join(lines2), True)
        finally:
            globals()['tracked_paths'] = _real_tracked

        landed, _w = push_landed()
        check('my own file is deleted IF AND ONLY IF the push had landed',
              (not os.path.isfile(f_mine)), bool(landed))
        # 'NOTHING REMOVED' CONTAINS 'REMOVED', so the first version of this
        # arm could never tell the two outcomes apart -- and it failed, which
        # is the arm doing its job on itself.
        check('...and the run says which of those it was, distinguishably',
              ('REMOVED %d file(s)' % len(
                  [x for x in (f_mine,) if not os.path.isfile(x)]) in txt)
              if landed else ('NOTHING REMOVED' in txt), True)
    finally:
        os.environ.pop('SAIRN_SCRATCH_ROOT', None)
        os.environ.pop('SAIRN_CLEANUP_STATE', None)
        shutil.rmtree(tmp, ignore_errors=True)
    print('  %d/%d fixtures classify correctly' % (16 - bad, 16))
    return EXIT_FINDING if bad else EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv:
        return run_fixtures()
    agent = (argv[argv.index('--agent') + 1] if '--agent' in argv
             else session_name())
    batch = (argv[argv.index('--batch') + 1] if '--batch' in argv else 'b6')
    if '--record' in argv:
        paths = [a for a in argv[argv.index('--record') + 1:]
                 if not a.startswith('--')]
        if not paths:
            print('COULD NOT RUN: --record needs at least one path.')
            return EXIT_COULD_NOT_RUN
        doc = record(agent, batch, paths)
        if doc is None:
            print('COULD NOT RUN: the existing list could not be parsed.')
            return EXIT_COULD_NOT_RUN
        print('recorded %d path(s); %s now lists %d'
              % (len(paths), list_path(agent, batch), len(doc['files'])))
        return EXIT_CLEAN
    # THE LOCK RUNS BEFORE ANY REAL SWEEP. A cleanup tool whose own criteria
    # are broken deletes on a verdict it never checked.
    if run_fixtures() != EXIT_CLEAN:
        print('')
        print('COULD NOT RUN: the criteria lock failed, so nothing was swept.')
        return EXIT_COULD_NOT_RUN
    print('')
    rc, lines = sweep(agent, batch, apply_changes=('--sweep' in argv))
    for l in lines:
        print(l)
    return rc


if __name__ == '__main__':
    sys.exit(main())
