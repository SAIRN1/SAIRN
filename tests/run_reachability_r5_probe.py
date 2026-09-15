"""tests/run_reachability_r5_probe.py

Run:  python tests/run_reachability_r5_probe.py

The control pair for R5 in tools/sairn_reachability_check.py -- item 32's
function-level purpose proxy.

CONTROLS_FOR = ['sairn_reachability_check.py']

WHY THIS FILE EXISTS AT ALL. R5 reports **zero** against the real tree today:
measured across all 67 routed api/ endpoints, not one has a named function
without a caller. That is a genuine and reassuring result -- and it leaves R5 in
the exact state this platform keeps having to correct, a check nobody has ever
seen produce a finding. `checkblocks.py` always exited 0 for months and nothing
noticed, because a check that always passes looks identical to a codebase that
is always clean.

THE TWO HALVES ARE SEPARATED ON PURPOSE AND THE ARMS PROVE IT.

  * The SERVED half is an inference FROM OBSERVATION -- the route ran, and the
    sweep says nothing calls this function. That needs no denominator: a route
    that was observed is evidence about itself however quiet the others were.
    It reports today, at 20% route coverage.

  * The SILENT half is an inference FROM SILENCE, and one route seeing zero
    means nothing when almost every route saw zero. It is gated behind R4's
    coverage bar, and arm D proves the gate is a GATE rather than a permanent
    off switch by feeding a synthetic high-coverage snapshot and watching the
    section classify.

NOTHING IS MUTATED IN THIS CLONE. Every plant happens in a throwaway worktree,
and every plant asserts it landed before the checker is run -- a rotted anchor
makes str.replace do nothing, the checker then runs against an unmodified file,
and "R5 reported nothing" reads as the clean arm passing.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['sairn_reachability_check.py']

# ── IMPORTED AT THE TOP, AND THE REASON IS A DEFECT THIS PROBE HAD ─────────
# tools/sairn_reachability_check.py REPLACES sys.stdout at import time (it wraps
# the buffer to force utf-8). Importing it half way down this file abandoned the
# old stream's buffer and SILENTLY DISCARDED EVERY LINE PRINTED BEFORE THAT
# POINT -- three of four sections vanished, and the run still ended with "all
# arms pass". A probe that loses most of its own output and reports success is
# the exact shape these controls exist to catch, arriving inside one of them.
#
# Importing before anything is printed means the swap happens once, early, with
# nothing buffered to lose.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import sairn_reachability_check as R                             # noqa: E402

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
FAIL = []

SERVED_ROUTE = '/api/alf-alerts'
SERVED_FILE = 'api/alf-alerts.js'
SILENT_ROUTE = '/api/accounting'
SILENT_FILE = 'api/accounting.js'
# A function nothing can possibly call. Named distinctively so a false PASS
# cannot come from matching something that was already in the file.
PLANT = '\nfunction zzR5ProbeOrphanFunction() { return 1; }\n'


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:600]))
    if not cond:
        FAIL.append(name)


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace')


def worktree(tag):
    d = os.path.join(tempfile.gettempdir(), 'r5-%s-%d' % (tag, os.getpid()))
    if os.path.isdir(d):
        git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'add', '-q', '--detach', d, 'HEAD')
    # The checker itself is copied from THIS clone, not taken from HEAD: a
    # control that only exercises the committed version cannot prove anything
    # about the change being made, which is the one moment it is for.
    for rel in ('tools/sairn_reachability_check.py',):
        src = io.open(os.path.join(REPO, rel), encoding='utf-8').read()
        io.open(os.path.join(d, rel.replace('/', os.sep)), 'w',
                encoding='utf-8', newline='').write(src)
    return d


def drop(d):
    git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'prune')


def plant(wt, rel, text):
    p = os.path.join(wt, rel.replace('/', os.sep))
    before = io.open(p, encoding='utf-8').read()
    if text in before:
        raise AssertionError('the SABOTAGE did not land: %s already contains it' % rel)
    io.open(p, 'w', encoding='utf-8', newline='').write(before + text)
    after = io.open(p, encoding='utf-8').read()
    if text not in after:
        raise AssertionError('the SABOTAGE did not land: not on disk in ' + rel)


def run(wt, activity=None):
    args = [sys.executable, os.path.join(wt, 'tools', 'sairn_reachability_check.py'),
            '--activity']
    if activity:
        args.append(activity)
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=wt, timeout=600)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def r5_block(out):
    i = out.find('=== R5:')
    return out[i:] if i != -1 else ''


print('R5 -- the function-level purpose proxy')

# ── A. the real tree, untouched ────────────────────────────────────────────
print('\n--- A. the real tree ---')
wt = worktree('base')
try:
    rc, out = run(wt)
    blk = r5_block(out)
    ok('A1 the R5 section runs at all', blk != '', out[-500:])
    ok('A2 it reports zero served-with-no-caller today',
       'no caller: 0' in blk, blk[:400])
    ok('A3 the silent half is NOT CLASSIFIED, because coverage is under the bar',
       'NOT CLASSIFIED' in blk, blk[:600])
    ok('A4 and it says WHY the served half does not need that denominator',
       'evidence about itself' in blk, blk[:600])
finally:
    drop(wt)

# ── B. THE CONTROL: an uncallable function in a SERVED route ───────────────
print('\n--- B. a function with no caller, in a route production DID serve ---')
wt = worktree('served')
try:
    plant(wt, SERVED_FILE, PLANT)
    rc, out = run(wt)
    blk = r5_block(out)
    ok('B1 R5 reports it', 'no caller: 1' in blk, blk[:600])
    ok('B2 it names the route', SERVED_ROUTE in blk, blk[:600])
    ok('B3 it names the function', 'zzR5ProbeOrphanFunction' in blk, blk[:600])
    ok('B4 it says to READ THE DISPATCH rather than to delete anything',
       'READ THE DISPATCH' in blk, blk[:800])
    ok('B5 and it says this is a question about the SWEEP too, not only the code',
       'question about the sweep' in blk, blk[:800])
    # NEVER GATES. The whole section is report-only, and an exit code change
    # would make it a gate by accident.
    ok('B6 THE EXIT CODE IS UNCHANGED -- R5 never gates', rc == 0, 'rc=%d' % rc)
finally:
    drop(wt)

# ── C. the same plant in a SILENT route must NOT appear in the served half ─
print('\n--- C. the same function in a route production did NOT serve ---')
wt = worktree('silent')
try:
    plant(wt, SILENT_FILE, PLANT)
    rc, out = run(wt)
    blk = r5_block(out)
    ok('C1 the SERVED half stays at zero -- the two halves are not one list',
       'no caller: 0' in blk, blk[:600])
    ok('C2 and it is not classified at all, because the silent half is gated',
       'NOT CLASSIFIED' in blk, blk[:600])
finally:
    drop(wt)

# ── D. the gate is a GATE, not a permanent off switch ──────────────────────
print('\n--- D. with enough coverage, the silent half classifies ---')
wt = worktree('cover')
try:
    plant(wt, SILENT_FILE, PLANT)
    # A synthetic snapshot claiming every route was observed EXCEPT the silent
    # one. Deliberately synthetic and labelled as such: the point is to prove
    # the coverage bar releases, not to assert anything about real traffic.
    routes = R.routed_api_paths()
    counts = dict((r, 5) for r in routes if r != SILENT_ROUTE)
    snap = {
        '_what_this_is': 'SYNTHETIC fixture written by tests/run_reachability_r5_probe.py '
                         'to prove the coverage gate releases. NOT a real capture.',
        'source': 'synthetic', 'captured_at': '2026-09-14T00:00:00Z',
        'window_hours': 72, 'counts': counts
    }
    fp = os.path.join(wt, 'synthetic_activity.json')
    io.open(fp, 'w', encoding='utf-8', newline='').write(json.dumps(snap))
    rc, out = run(wt, fp)
    blk = r5_block(out)
    ok('D1 the silent half is now classified rather than gated',
       'NOT CLASSIFIED' not in blk, blk[:700])
    ok('D2 and it finds the planted function in the silent route',
       'zzR5ProbeOrphanFunction' in blk and SILENT_ROUTE in blk, blk[:700])
    ok('D3 ...and STILL refuses to vote for removal',
       'does not vote' in blk or 'NOT' in blk and 'permission to delete' in blk, blk[:900])
    ok('D4 the exit code is still unchanged', rc == 0, 'rc=%d' % rc)
finally:
    drop(wt)

print('')
if FAIL:
    print('R5: %d ARM(S) FAILED -- %s' % (len(FAIL), ', '.join(FAIL)))
    sys.exit(1)
print('R5: all arms pass')
