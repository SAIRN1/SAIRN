#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b7, queue item 5
"""`hover_auditor_scope_gate.changed_outgoing()` against a remote tip this clone has NEVER FETCHED.

    python tests/run_scope_gate_unfetched_base_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

THE DEFECT, routed twice by fourth (b10 in full, b11 as a register row because
b10 was still unacknowledged -- `docs/2026-10-13-fourth-b11-routed-to-cc.md`).
`changed_outgoing()` built its range from `rsha` -- the REMOTE's sha, read off
git's own pre-push stdin line, by field position -- with no existence test, and
then reported the failure as a property of the RANGE:

    could not read the outgoing range A..B: <git's stderr>

With five sessions pushing one branch, that sha is routinely an object this
clone has never fetched. **The ordinary case, reported as an anomaly about the
change being pushed.** THE FOURTH INSTANCE OF A SHAPE FIXED THREE TIMES:
`register_feed_gate.py` (ac9d47d8), `copy_exactly_gate.py` (55777a74) and
`sairn_push_gate_hook.py` (9c36aa7c) -- the last of which printed a FALSE
FINDING, `NO OWNER: 4`, over four pre-existing shared tools.

AND IT IS NOT A STORY: this batch hit the same CLASS of defect in the same
hook, from the other direction. `git push` was denied twice with
`register_feed_gate: stdin is not a terminal and carried NO ref lines` while
this clone was 9 commits behind; rebasing cleared it with no change to the
push. A diagnosis that names a mechanism instead of the cause costs a session
every time.

── THE ARMS ────────────────────────────────────────────────────────────────
1. A remote tip that RESOLVES behaves exactly as before -- the range is read,
   no note is added. Without this arm the fix could be "always take the
   merge-base", which would be a gate that silently changed its subject.
2. A remote tip that IS NOT AN OBJECT here: the paths are still found, via
   merge-base(origin/main, local), and the substitution is SAID OUT LOUD in
   the notes rather than performed quietly.
3. Neither resolvable: a COULD-NOT-READ naming the remote and prescribing
   `git fetch origin` -- NOT a finding about the change, and not a pass.
4. The all-zero remote sha (a new branch) still takes the `log` path.
5. ABLATION: with `_have_commit` stubbed to always answer True -- which is the
   pre-fix behaviour exactly -- arm 2's input goes back to the opaque
   `could not read the outgoing range` refusal. Without this, arm 2 could be
   passing for some reason other than the guard.

── WHAT THIS PROBE DOES NOT TOUCH ──────────────────────────────────────────
  * the auditor's clone. `Documents\\SAIRN-hover` is never read or written; a
    build agent must not reach into it (CLAUDE.md), and nothing here does.
    Every arm runs in a throwaway repository this file builds.
  * the rest of the gate. `changed_outgoing()` is the subject; the ALLOWED
    list, the refusal text and the marker-file leg are covered elsewhere
    (`tests/run_hover_scope_own_claim_probe.py`, `run_hover_separation_probe.py`).
  * whether a superset range can make this gate PASS something it should
    refuse. It cannot -- more paths examined means more that can be refused --
    but that is an argument, and the arm that would measure it would need a
    real out-of-scope path in the extra range. Named, not claimed.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GATE = os.path.join(REPO, 'tools', 'hover_auditor_scope_gate.py')

if not os.path.isfile(GATE):
    print('COULD NOT RUN: %s is absent, so NOTHING WAS TESTED.' % GATE)
    sys.exit(2)

spec = importlib.util.spec_from_file_location('scope_gate_subject', GATE)
sg = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.join(REPO, 'tools'))
try:
    spec.loader.exec_module(sg)
except Exception as exc:                                         # noqa: BLE001
    print('COULD NOT RUN: the gate would not import (%s).' % exc)
    sys.exit(2)
if not hasattr(sg, '_have_commit'):
    print('COULD NOT RUN: the gate has no _have_commit, so the fix this probe '
          'exists for is NOT PRESENT. That is a finding about the tool and it '
          'is not something this probe can test around.')
    sys.exit(2)

ZERO = '0' * 40
ABSENT = 'dead' * 10            # 40 hex chars, and not an object anywhere


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')


def build(tmp):
    """A throwaway repo: base commit, tip commit, origin/main at base."""
    d = tempfile.mkdtemp(prefix='sgufb-', dir=tmp)
    git(d, 'init', '-q', '-b', 'main')
    git(d, 'config', 'user.email', 'probe@example.invalid')
    git(d, 'config', 'user.name', 'probe')
    open(os.path.join(d, 'base.txt'), 'w').write('base\n')
    git(d, 'add', '-A')
    git(d, 'commit', '-q', '-m', 'base')
    base = git(d, 'rev-parse', 'HEAD').stdout.strip()
    os.makedirs(os.path.join(d, 'tools'), exist_ok=True)
    open(os.path.join(d, 'tools', 'thing.py'), 'w').write('# tip\n')
    git(d, 'add', '-A')
    git(d, 'commit', '-q', '-m', 'tip')
    tip = git(d, 'rev-parse', 'HEAD').stdout.strip()
    git(d, 'update-ref', 'refs/remotes/origin/main', base)
    return d, base, tip


def refline(lsha, rsha):
    return 'refs/heads/main %s refs/heads/main %s\n' % (lsha, rsha)


arms = []
tmp = tempfile.mkdtemp(prefix='sgufb-probe-')
cwd0 = os.getcwd()
print('scope gate unfetched-base probe')
print('  subject : tools/hover_auditor_scope_gate.py changed_outgoing()')
print('  repos   : %s  (the auditor clone is never touched)' % tmp)
print('')

try:
    d, base, tip = build(tmp)
    os.chdir(d)

    # ── ARM 1: a remote tip that RESOLVES ───────────────────────────────────
    paths, notes = sg.changed_outgoing(refline(tip, base))
    arms.append(('ARM 1: a remote tip this clone HAS reads the range it was '
                 'handed', paths, ['tools/thing.py']))
    arms.append(('ARM 1b: ...and adds NO note, so the gate did not quietly '
                 'change its own subject on the ordinary path', notes, ''))

    # ── ARM 2: a remote tip that is NOT an object here ──────────────────────
    paths, notes = sg.changed_outgoing(refline(tip, ABSENT))
    arms.append(('ARM 2 (the routed defect): an UNFETCHED remote tip still '
                 'yields the changed paths, via merge-base', paths,
                 ['tools/thing.py']))
    arms.append(('ARM 2b: ...and the substitution is stated out loud',
                 ('not an object in this clone' in notes,
                  'SUPERSET' in notes), (True, True)))
    arms.append(('ARM 2c: ...naming the merge-base it used, so a reader can '
                 're-run it', base[:12] in notes, True))

    # ── ARM 3: neither resolvable -> COULD NOT READ, about the REMOTE ───────
    git(d, 'update-ref', '-d', 'refs/remotes/origin/main')
    paths, why = sg.changed_outgoing(refline(tip, ABSENT))
    arms.append(('ARM 3: with no origin/main either, it returns a '
                 'COULD-NOT-READ rather than a range error',
                 (paths, 'NOT an object in this clone' in why), (None, True)))
    arms.append(('ARM 3b: ...which says it is NOT a finding about the change',
                 'not a finding about the change' in why, True))
    arms.append(('ARM 3c: ...and prescribes the fix by command',
                 'git fetch origin' in why, True))
    git(d, 'update-ref', 'refs/remotes/origin/main', base)

    # ── ARM 4: the all-zero remote sha is still the new-branch path ─────────
    paths, notes = sg.changed_outgoing(refline(tip, ZERO))
    arms.append(('ARM 4: an all-zero remote sha still checks every reachable '
                 'commit -- untouched by this fix',
                 (sorted(paths), 'new branch' in notes),
                 (['base.txt', 'tools/thing.py'], True)))

    # ── ARM 5: ABLATION -- stub the guard and the old refusal returns ───────
    keep = sg._have_commit
    try:
        sg._have_commit = lambda sha: True        # the pre-fix behaviour
        paths, why = sg.changed_outgoing(refline(tip, ABSENT))
    finally:
        sg._have_commit = keep
    arms.append(('ARM 5 ABLATION: with _have_commit stubbed to always say yes '
                 '-- which IS the pre-fix code -- the same input goes back to '
                 'the opaque range refusal, so arm 2 is the guard and nothing '
                 'else',
                 (paths, 'could not read the outgoing range' in (why or '')),
                 (None, True)))

    # ── ARM 6: THE POPULATION, which is what stops a FIFTH instance ─────────
    # This arm is the cc b7 ruling on the other half of fourth's routed item.
    # The standalone 6-arm taint checker is NOT PROMOTED -- the reason, with
    # the measurement, is in tools/report_only_checks.py NOT_PROMOTED -- and
    # this is the substitute: the population re-measured on every run of a
    # probe that already exists, so a FOURTH author of this shape fails a
    # test rather than being caught by somebody remembering a grep.
    #
    # ITS LIMIT, AND IT IS WEAKER THAN FOURTH'S SPEC: the guard is detected
    # PER FILE, not along the flow. It catches `no guard anywhere in the
    # file`, which is the shape all four real instances had, and it would NOT
    # catch a file that guards one path and leaves another unguarded. Stated
    # here rather than discovered later; a flow-level answer is the thing that
    # was declined, and this arm is not a stand-in for it.
    import glob
    import io
    import re
    pop, unguarded = [], []
    for p in sorted(glob.glob(os.path.join(REPO, 'tools', '*.py'))):
        src = io.open(p, encoding='utf-8', errors='replace').read()
        if 'pre-push' not in src and 'pre_push' not in src:
            continue
        if not re.search(r'parts\[:4\]|parts\[3\]|split\(\)\[3\]', src):
            continue
        pop.append(os.path.basename(p))
        if not re.search(r"cat-file['\"],\s*['\"]-e|rev-parse['\"],\s*"
                         r"['\"]--verify|_have_commit", src):
            unguarded.append(os.path.basename(p))
    print('  POPULATION: %d tool(s) bind a remote sha from a pre-push ref '
          'line by field position: %s' % (len(pop), ', '.join(pop)))
    arms.append(('ARM 6: every tool that binds a remote sha from a pre-push '
                 'ref line by field position carries an existence guard '
                 'SOMEWHERE in the file (population %d, named above)'
                 % len(pop), unguarded, []))
    arms.append(('ARM 6b: the population is not EMPTY -- an arm over zero '
                 'files passes for ever and tests nothing', len(pop) >= 3,
                 True))
finally:
    os.chdir(cwd0)
    shutil.rmtree(tmp, ignore_errors=True)

passed = 0
for name, got, want in arms:
    ok = got == want
    passed += ok
    print('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
    if not ok:
        print('       wanted %r' % (want,))
        print('       got    %r' % (got,))
print('scope gate unfetched-base probe: %d/%d arm(s) pass' % (passed, len(arms)))
sys.exit(0 if passed == len(arms) else 1)
