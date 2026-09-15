"""tests/push_gate/check12_probe.py

Run:  python tests/push_gate/check12_probe.py

CHECK 12 REFUSES WHAT *THIS PUSH* BROKE, AND NOTHING ELSE.

── THE ARM THAT MATTERS IS THE PAIR, NOT EITHER HALF ─────────────────────────
Sections B and D plant the IDENTICAL breakage and differ only in WHICH COMMIT it
sits in -- the pushed one, or one already at the base. B must deny and D must
not. Either arm alone is satisfiable by a broken check: one that denies on any
stale document passes B, one that never denies passes D. Only the pair says the
scoping is real, and the scoping IS the decision this check implements
(Michael, 2026-09-14: block what this push introduced, never a pre-existing gap).

── WHY A PROBE AND NOT A READ ────────────────────────────────────────────────
The check's whole mechanism is a second `--check` run against a throwaway
worktree at the base commit. Nothing about that is visible in a diff, and the
failure mode if it is wrong is SILENCE -- a gate that stops denying looks exactly
like a stream of clean pushes. `tools/sabotage_control_check.py` exists because
21 of 37 negative controls on this platform had drifted into exactly that state.

── THE TWO LEVERS ARE MEASURED, NOT ASSUMED ──────────────────────────────────
Both were run against a real worktree before this file was written, because a
fixture that does not actually move the generator proves nothing:

    a new tools/*.py   -> tooling_inventory.py  EXIT 2 (refuses: no PURPOSES
                          entry). master_plan and traceability_matrix unmoved.
    a new tests/*.py   -> master_plan.py        EXIT 1 (stale)
                          traceability_matrix.py EXIT 1 (stale)
                          tooling_inventory unmoved.

Exit 1 and exit 2 are DIFFERENT states and both are exercised, because the
messages and the fixes differ and a check that collapsed them would pass an arm
that only ever tested one.

── WHAT IS NOT COVERED, SAID RATHER THAN IMPLIED ─────────────────────────────
The COULD-NOT-TELL path -- base worktree unresolvable or uncreatable, which
ALLOWS with a notice -- has no arm here. Reaching it needs `git worktree add` to
fail or both base references to be unresolvable, and neither can be arranged from
outside without editing the gate, which would be the probe proving its own edit.
Same boundary tests/push_gate/missing_checker_probe.py records for check 2's
unrunnable-subprocess arm. It is a real gap in this file's coverage.

Section F's arm was drafted as "both absent -> the gate allows" and THE CHECK
PROVED THE FIXTURE WRONG: deleting any tools/*.py trips tooling_inventory.py's
refusal in the other direction, a PURPOSES entry naming a tool that no longer
exists. So the both-absent state is not reachable in this repo by deletion, F
asserts the skip BRANCH instead of a clean allow, and that limit is recorded in
the section rather than papered over by relaxing the assertion.

Negative arms assert EXIT 0, not merely the absence of check 12's wording. A
denial from an earlier check would make "check 12 said nothing" true and vacuous.
F is the one section where exit 0 is not asserted, for the reason above, and it
pins WHY it denies so nobody reads it as "removing a generator is fine".
"""
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
GATE = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:600]))
    if not cond:
        FAIL.append(name)


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args),
                          capture_output=True, text=True, encoding='utf-8', errors='replace')


def run_gate(cwd, tip, base):
    """Drive the REAL hook through its pre-push entry point."""
    line = 'refs/heads/probe %s refs/heads/probe %s\n' % (tip, base)
    r = subprocess.run([sys.executable, GATE, '--pre-push'],
                       input=line, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# ── EVERY SABOTAGE BELOW ASSERTS IT LANDED ──────────────────────────────────
# tools/sabotage_control_check.py flagged this file as UNGUARDED on its first
# run and it was RIGHT. The sabotage here is not `src.replace(anchor, ...)` --
# it is `git rm` and a fixture write -- but the failure shape is identical: if a
# path is renamed, `git rm` fails, the commit carries nothing, and the gate is
# then run against an UNCHANGED tree. Section E's "the push is REFUSED" would
# still pass, satisfied by some other check denying for its own reasons, and the
# arm would report green while testing nothing.
#
# So each helper returns only after proving the tree actually moved, and raises
# rather than returning a sha that means nothing.
def _assert(cond, msg):
    if not cond:
        raise AssertionError('the SABOTAGE did not land: ' + msg)


def commit(wt, rel, body, subject):
    """Stage one file and commit it, and prove the commit contains it.

    The subject must NOT begin with PROBE: check 8 refuses those outright and
    would answer in place of the check under test.
    """
    before = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    full = os.path.join(wt, rel)
    d = os.path.dirname(full)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(full, 'w', encoding='utf-8', newline='').write(body)
    git(wt, 'add', '--', rel)
    git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
        'commit', '-q', '-m', subject)
    sha = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    _assert(sha and sha != before, 'no commit was created for ' + rel)
    named = git(wt, 'show', '--name-only', '--format=', sha).stdout.replace('\\', '/')
    _assert(rel in named, '%s is not in the commit it was written for' % rel)
    _assert(os.path.isfile(full), '%s is not on disk after the commit' % rel)
    return sha


def remove(wt, rel, subject):
    """Delete a tracked file and prove it is gone from the tree AND the commit."""
    before = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    _assert(os.path.isfile(os.path.join(wt, rel)),
            '%s was not there to delete -- renamed or moved?' % rel)
    git(wt, 'rm', '-q', '--', rel)
    git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
        'commit', '-q', '-m', subject)
    sha = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    _assert(sha and sha != before, 'no commit was created deleting ' + rel)
    _assert(not os.path.isfile(os.path.join(wt, rel)),
            '%s is still on disk after git rm' % rel)
    return sha


_N = [0]


def worktree():
    _N[0] += 1
    d = os.path.join(tempfile.gettempdir(), 'gate12-%d-%d' % (os.getpid(), _N[0]))
    if os.path.isdir(d):
        git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'add', '-q', '--detach', d, 'HEAD')
    return d


def drop(d):
    git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'prune')


# A file that is derived from by NOTHING: not tools/, not tests/, not an app
# html, not api/_resources. If this one moved a generator the negative arms
# below would be testing the wrong thing.
INERT = ('// fixture: an api lib with nothing derived from it.\n'
         'module.exports = { zzProbeInert: function () { return 1; } };\n')
NEW_TOOL = '"""fixture tool: exists to have no PURPOSES entry."""\n'
NEW_SUITE = 'print("fixture suite -- counted on disk, traced to nothing")\n'

TOOL_REL = 'tools/zz_check12_fixture.py'
SUITE_REL = 'tests/zz_check12_fixture.py'
INERT_REL = 'api/_lib/zz_check12_inert.js'

MARK = 'check 12'
DENY_TEXT = 'makes a GENERATED document stop matching'

print('check 12 -- a generated document THIS push broke')

# ── A. the control: a push that derives nothing must not be touched by it ────
print('\n--- A. a push that moves no generator ---')
wt = worktree()
try:
    base = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    tip = commit(wt, INERT_REL, INERT, 'add an inert lib')
    rc, out = run_gate(wt, tip, base)
    ok('A1 the gate allows', rc == 0, 'rc=%d\n%s' % (rc, out))
    ok('A2 check 12 says nothing at all', DENY_TEXT not in out and MARK not in out, out)
finally:
    drop(wt)

# ── B. this push breaks it -> DENY ──────────────────────────────────────────
print('\n--- B. the pushed commit is what broke it ---')
wt = worktree()
try:
    base = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    tip = commit(wt, SUITE_REL, NEW_SUITE, 'add a suite')
    rc, out = run_gate(wt, tip, base)
    ok('B1 the push is REFUSED', rc != 0, 'rc=%d\n%s' % (rc, out))
    ok('B2 and it is check 12 that refused', DENY_TEXT in out, out[-800:])
    ok('B3 it names MASTER-PLAN', 'docs/MASTER-PLAN.md' in out.replace('\\', '/'), out[-800:])
    ok('B4 it names the traceability matrix',
       'docs/traceability-matrix.md' in out.replace('\\', '/'), out[-800:])
    ok('B5 it says the document no longer matches its sources',
       'no longer matches its sources' in out, out[-800:])
    # NAMING THE FIX IS PART OF THE CHECK, not decoration: a deny that does not
    # say `python tools/master_plan.py` sends the reader to find it.
    ok('B6 it names the command that fixes it',
       'python tools/master_plan.py' in out.replace('\\', '/'), out[-800:])
    # The document it did NOT break must not be dragged in.
    ok('B7 it does NOT name TOOLING-INVENTORY, which this push did not move',
       'docs/TOOLING-INVENTORY.md' not in out.replace('\\', '/'), out[-800:])
finally:
    drop(wt)

# ── C. exit 2 is a different state and carries a different message ──────────
print('\n--- C. the push adds a tool with no inventory entry (exit 2) ---')
wt = worktree()
try:
    base = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    tip = commit(wt, TOOL_REL, NEW_TOOL, 'add a tool')
    rc, out = run_gate(wt, tip, base)
    ok('C1 the push is REFUSED', rc != 0, 'rc=%d\n%s' % (rc, out))
    # ── C2/C3 WERE REWRITTEN 2026-09-14 AND THE REASON IS THE POINT ─────────
    # They used to assert check 12's generic message. Check 12b now answers
    # FIRST and more narrowly: it names THE TOOL THIS PUSH ADDS rather than the
    # document, because the document is a symptom and the file is the cause. The
    # push is refused either way -- C1 is unchanged -- and the arm asserting the
    # WORSE message was the one that had to move.
    ok('C2 it names the TOOL this push adds, not just the document it broke',
       'tools/zz_check12_fixture.py' in out.replace('\\', '/'), out[-900:])
    ok("C3 it cites the decision rather than only the mechanism",
       '2026-09-13: no tool file is mergeable' in out, out[-900:])
    ok('C4 it does not call an exit 2 a stale document',
       'docs/TOOLING-INVENTORY.md -- no longer matches' not in out.replace('\\', '/'),
       out[-800:])
    ok('C5 and it says what to do -- an entry, then regenerate',
       'PURPOSES entry' in out and 'python tools/tooling_inventory.py' in out, out[-900:])
finally:
    drop(wt)

# ── D. THE PAIR WITH B. Same breakage, already at the base -> ALLOW ──────────
print('\n--- D. the breakage was already at the base commit ---')
wt = worktree()
try:
    # The SAME fixture as B, committed FIRST so it is part of the base.
    base = commit(wt, SUITE_REL, NEW_SUITE, 'add a suite')
    tip = commit(wt, INERT_REL, INERT, 'add an inert lib')
    rc, out = run_gate(wt, tip, base)
    ok('D1 the push is ALLOWED -- not this push, not this push to fix',
       rc == 0, 'rc=%d\n%s' % (rc, out))
    ok('D2 it did NOT deny', DENY_TEXT not in out, out[-800:])
    # SILENCE WOULD BE WRONG TOO. A gate that allows and says nothing is
    # indistinguishable from one that never looked.
    ok('D3 but it SAYS the document is stale', 'NOTICE (check 12)' in out, out[-1200:])
    ok('D4 and says it was ALREADY stale at the base commit',
       'ALREADY' in out, out[-1200:])
    ok('D5 and names who has to clear it, with the command',
       'python tools/master_plan.py' in out.replace('\\', '/')
       or 'python tools/traceability_matrix.py' in out.replace('\\', '/'),
       out[-1200:])
finally:
    drop(wt)

# ── E. a document with no generator is a COULD-NOT-TELL, and it denies ──────
print('\n--- E. the generator is missing and its document is not ---')
wt = worktree()
try:
    base = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    tip = remove(wt, 'tools/master_plan.py', 'drop a generator')
    rc, out = run_gate(wt, tip, base)
    ok('E1 the push is REFUSED', rc != 0, 'rc=%d\n%s' % (rc, out))
    ok('E2 it names the path it looked for',
       'tools/master_plan.py' in out.replace('\\', '/'), out[-800:])
    ok('E3 and calls it a could-not-tell rather than a finding',
       'COULD-NOT-TELL' in out, out[-800:])
finally:
    drop(wt)

# ── F. neither present -- the branch is proven, the clean-allow is NOT ───────
# THIS ARM WAS WRITTEN AS "the gate allows" AND THE CHECK PROVED THE FIXTURE
# WRONG, which is worth more than the arm as drafted. Deleting ANY tools/*.py
# trips tooling_inventory.py's refusal in the OTHER direction -- "a PURPOSES
# entry naming a tool that no longer exists" -- so the both-absent state is not
# reachable in this repo by deletion, and a push that removes a generator is
# genuinely a push that breaks a generated document.
#
# So the arm now asserts the branch that IS under test: with BOTH gone, check 12
# must not emit section E's could-not-tell about the missing generator. The
# unrelated exit-2 deny is expected and is asserted as the ONLY thing it says.
print('\n--- F. generator AND document both absent ---')
wt = worktree()
try:
    base = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    for _p in ('tools/master_plan.py', 'docs/MASTER-PLAN.md'):
        _assert(os.path.isfile(os.path.join(wt, _p)),
                '%s was not there to delete -- renamed or moved?' % _p)
    git(wt, 'rm', '-q', '--', 'tools/master_plan.py', 'docs/MASTER-PLAN.md')
    git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
        'commit', '-q', '-m', 'drop a generator and its document')
    tip = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    _assert(tip != base, 'no commit was created')
    for _p in ('tools/master_plan.py', 'docs/MASTER-PLAN.md'):
        _assert(not os.path.isfile(os.path.join(wt, _p)),
                '%s is still on disk after git rm' % _p)
    rc, out = run_gate(wt, tip, base)
    flat = out.replace('\\', '/')
    ok('F1 no could-not-tell about the absent generator -- the skip branch ran',
       'expected: tools/master_plan.py' not in flat, out[-800:])
    ok('F2 and MASTER-PLAN is not named at all, having no generator and no document',
       'docs/MASTER-PLAN.md' not in flat, out[-800:])
    # AND THE REASON IT STILL DENIES, pinned so a future reader does not read
    # F1/F2 as "removing a generator is fine".
    ok('F3 it denies for the OTHER direction instead: a PURPOSES entry naming a '
       'tool that no longer exists',
       rc != 0 and 'docs/TOOLING-INVENTORY.md' in flat, 'rc=%d\n%s' % (rc, out[-800:]))
finally:
    drop(wt)

# ── G. 12b: THE HOLE THE LIVE CONFIRMATION FOUND ───────────────────────────
# Michael's 2026-09-13 decision is that no tools/ file is mergeable without a
# matching inventory entry. Driven against the real hook on 2026-09-14, it held
# on a CLEAN base (section C) and DID NOT HOLD once the inventory was already
# refusing: the second unentered tool was waved through with a notice, and so
# would every one after it, until somebody cleared the first.
#
# The pair below is what makes the fix narrow rather than a widening of check
# 12: a push that SHIPS an unentered tool is refused even on a dirty base, and a
# push that ships NO tools/ file is still allowed on that same dirty base. If
# the second arm ever fails, this has become the thing check 12 exists not to
# be -- a gate that blocks you for somebody else's mess.
print('\n--- G. 12b: an unentered tool, on a base that was ALREADY refusing ---')
wt = worktree()
try:
    base = commit(wt, 'tools/zz_g_first.py', '"""first, unentered."""\n',
                  'base already carries an unentered tool')
    tip = commit(wt, 'tools/zz_g_second.py', '"""second, unentered."""\n',
                 'add a SECOND unentered tool')
    rc, out = run_gate(wt, tip, base)
    flat = out.replace('\\', '/')
    ok('G1 the push is REFUSED even though the inventory was already refusing',
       rc != 0, 'rc=%d\n%s' % (rc, out[-900:]))
    ok('G2 it names the tool THIS push adds', 'tools/zz_g_second.py' in flat, out[-900:])
    ok('G3 and NOT the one that was already there -- never somebody else\'s to clear',
       'tools/zz_g_first.py' not in flat, out[-900:])
finally:
    drop(wt)

print('\n--- G(ii). the pair: no tools/ file in the push, same dirty base ---')
wt = worktree()
try:
    base = commit(wt, 'tools/zz_g_first.py', '"""first, unentered."""\n',
                  'base already carries an unentered tool')
    tip = commit(wt, INERT_REL, INERT, 'an unrelated lib, no tools touched')
    rc, out = run_gate(wt, tip, base)
    ok('G4 the push is ALLOWED -- 12b did not widen into check 12',
       rc == 0, 'rc=%d\n%s' % (rc, out[-900:]))
    ok('G5 and the pre-existing refusal is still SAID, not silently tolerated',
       'NOTICE (check 12)' in out and 'ALREADY' in out, out[-900:])
finally:
    drop(wt)

print('')
if FAIL:
    print('check 12: %d ARM(S) FAILED -- %s' % (len(FAIL), ', '.join(FAIL)))
    sys.exit(1)
print('check 12: all arms pass')
