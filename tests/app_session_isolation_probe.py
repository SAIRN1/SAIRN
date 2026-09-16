"""tests/app_session_isolation.js must REFUSE -- and it PASSED while printing
its own refutation.

Run: python tests/app_session_isolation_probe.py

THE ARM SAID THIS, IN GREEN, ON origin/main:

    ok  PHASE 1 (2026-09-05, still open): law_trusttx is reachable with the
        LICENCE ALONE -- no session -- and answers 403

It asserted `out.code !== 401`. law_trusttx was gated on 2026-09-16 and
SD_SESSION_GATED refuses with 403 FORBIDDEN, not 401, so the arm stayed green
and interpolated into its own message the status code that disproves the
sentence it was asserting. REACHABILITY WAS ENCODED AS THE NEGATION OF ONE
REFUSAL CODE, and the refusal that arrived was the other one.

The file's own comment, six lines above that loop, says: "a silent canary and a
healthy canary look identical." This canary sang the wrong note and was counted
as singing.

THIS IS THE THIRD UN-INVERTED PHASE ARM FOUND IN ONE SESSION and the only one
that did not go red. The other two -- in api/sd-data-sairnlaw-resources.test.js
and api/sd-data-session-gate.test.js -- failed loudly and sat failing. This one
is worse: nothing to notice, nothing to ignore, and the suite reporting ALL 54
ASSERTIONS PASS the whole time.

WHAT THIS SUITE IS FOR, which is why the arm mattered. For a licence with no
`app_id` -- the entire pre-2026-09-04 population, which nobody can enumerate --
THE ONLY THING BETWEEN ONE APP'S SESSION AND ANOTHER APP'S DATA IS THE
`expectedApp` ARGUMENT INSIDE EACH BRANCH. The licence boundary is deliberately
open for an unattributable licence; this file is what checks the other half.

NINE MUTATIONS, and six of them prove less than they look like they prove.
1-5 and 8 take the gate apart -- the resource leaves the registry, half of it
leaves, a still-open resource is gated early, the resource falls out of both
phase lists, it moves back into the ungated loop, a fixture resource is gated
against the wrong app. Every one is worth driving AND EVERY ONE WOULD HAVE BEEN
CAUGHT BY THE BROKEN SUITE TOO, so on their own they say nothing about whether
the repair addressed the cause.

── THE SAME-REASON SET, AND THE CONTROL THAT DECIDES WHICH ONES QUALIFY ──────
6, 7 and 9 change what the endpoint SAYS while leaving what it DOES alone: the
expected app reverts to 'stonedesk'; the gate refuses with 500 instead of 403;
the enumeration oracle answers 404 instead of 400. Each is invisible to a
`!== <one code>` predicate and visible to a positive one.

THAT CLAIM IS MEASURED, NOT ASSERTED. old_form_is_blind() pulls the suite AS IT
ACTUALLY WAS out of git -- the parent of the commit that introduced
PHASE_2_GATED, derived rather than pinned -- and requires every same-reason
mutation to leave it GREEN. A mutation the old suite also caught is reported as
SEEN and the control FAILS, because it is not evidence.

THE FIRST THREE CANDIDATES WERE WRONG AND THE CONTROL SAID SO:

  * 403 -> 401 was SEEN. 401 is the one code the broken predicate could see;
    testing the repair with the only input the defect never had is no test.
    Changed to 500.
  * gating sb_payruns was SEEN, through the cross-app refusal arms, which
    expect 401 and get 403. Demoted to an ordinary mutation.
  * and the control's own FIRST version was wrong in the same family: it
    hand-reverted three predicates instead of reading history, which cannot
    remove an ARM that did not exist yet, so it reported two false SEENs.
    A counterfactual assembled by hand is a guess about history.

── ONE MUTATION WAS WITHDRAWN, AND THE REASON IS THE POINT ───────────────────
The obvious seventh is "put `!== 401` back". It is an EQUIVALENT MUTANT as the
file now stands: the only resource that answers 403 is in PHASE_2_GATED, which
is asserted positively, so the remaining loop sees nothing but 200s and `!== 401`
and `=== 200` agree on every input it will ever get. Counting it would have
inflated this probe by one arm that proves nothing.

THE ORIGINAL DEFECT NEEDED BOTH HALVES -- a resource in the wrong list AND a
predicate too weak to notice -- and mutation 5 drives the half that is
observable. That is the distinction this platform paid for once already, when a
mutant swapping `if (!session) return false;` for `session = session || {};` was
nearly reported as a coverage gap in the roofing claim gate: MANAGEMENT_ROLES
[undefined] is already falsy, so the two are identical for every input, and
calling it a gap would have been a fabricated finding against a suite that was
right.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'app_session_isolation.js')
API = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. THE DEFECT THE BROKEN ARM COULD NOT SEE. law_trusttx leaves the session "
     "registry, so attorney IOLTA trust money is reachable on the licence key "
     "alone again -- the exact state this suite reported as healthy for as long "
     "as it was asserting `!== 401`",
     API,
     "      'law_trusttx': ['read', 'write']\n    };",
     "    };"),

    ("2. only the READ is gated. The quiet half: a trust ledger that can be "
     "read by anyone holding the licence key errors nowhere, and the write "
     "refusal makes the feature look protected",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'law_trusttx': ['write']"),

    ("3. a still-open resource is gated EARLY -- law_deadlines joins the "
     "registry before its phase-2 day, which fails a staff member with the app "
     "already open on a cached page that sends no token",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'law_deadlines': ['read', 'write'],\n      'law_trusttx': ['read', 'write']"),

    ("4. law_trusttx is dropped from BOTH phase lists -- it leaves the boundary "
     "entirely and the suite goes green having stopped asking about it. Only the "
     "partition arm sees this, and only because the two lists are required to "
     "reconstruct the original four",
     SUITE,
     "const PHASE_1_UNGATED = ['law_clients', 'law_matters', 'law_trusttx', 'law_deadlines'];",
     "const PHASE_1_UNGATED = ['law_clients', 'law_matters', 'law_deadlines'];"),

    ("5. law_trusttx MOVES BACK into the still-ungated loop -- the pre-fix "
     "classification. It answers 403, the loop demands 200, and the arm fails. "
     "The ORIGINAL defect needed BOTH halves: this list error AND reachability "
     "expressed as `!== 401`, which is why mutating the assertion alone is "
     "WITHDRAWN below rather than counted",
     SUITE,
     "  const PHASE_2_GATED = ['law_trusttx'];",
     "  const PHASE_2_GATED = [];"),

    # ── 7, 8, 9: THE "SAME REASON" TEST ────────────────────────────────────
    # The original arm did not fail because it was pointed at the wrong thing;
    # it failed because its PREDICATE was a negation, satisfied by a refusal
    # shape it was not written for. Mutations 1-6 would all have been caught by
    # the broken predicate too, so on their own they say nothing about whether
    # the repair addressed the actual cause.
    #
    # These three change the STATUS CODE rather than the behaviour: each one
    # leaves the gate doing the right thing and makes it SAY something else.
    # Every one of them passes under the old `!== <one code>` form and fails
    # under the positive one. That is the difference the repair was for, and it
    # is the only evidence that can distinguish the two.
    ("7. SAME-REASON TEST -- the gate refuses with 500 instead of 403. The gate "
     "is intact and the trust ledger is still protected; only the code changed, "
     "and a caller now cannot tell a refusal from a fault. `!== 401` is "
     "satisfied by a 500 and the pre-fix suite is BLIND to it; "
     "`=== 403 && FORBIDDEN` is not. (401 was tried here first and is NOT "
     "evidence: it is the one code the old predicate could see.)",
     API,
     "        res.status(403).json({\n          error: {\n            code: 'FORBIDDEN',",
     "        res.status(500).json({\n          error: {\n            code: 'FORBIDDEN',"),

    ("8. a GATED fixture resource joins SD_SESSION_GATED "
     "with no SD_GATE_APP entry, so its expected app defaults to 'stonedesk' "
     "and each app's OWN session is refused its OWN resource with 403. The "
     "control that licenses every refusal below it is then false. NOT a "
     "same-reason arm: the pre-fix suite catches this too, through its "
     "cross-app refusal arms, which expect 401 and get 403 -- measured, not "
     "assumed, by the control below",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'sb_payruns': ['read', 'write'],\n      'law_trusttx': ['read', 'write']"),

    ("9. SAME-REASON TEST -- the enumeration oracle answers 404 instead of 400. "
     "A foreign resource and an invented one still agree, so the oracle arm "
     "stays green; only the second arm, which claims the LICENCE boundary "
     "answered rather than the session gate, can see it -- and only now that it "
     "names 400 rather than ruling out 401",
     API,
     "      status: 400,\n      code: registered ? 'FOREIGN_RESOURCE' : 'UNKNOWN_RESOURCE',",
     "      status: 404,\n      code: registered ? 'FOREIGN_RESOURCE' : 'UNKNOWN_RESOURCE',"),

    ("6. SAME-REASON TEST -- the EXPECTED APP reverts to the hardcoded 'stonedesk'. Every correctly "
     "signed-in attorney is refused, and the obvious repair for THAT symptom is "
     "to take the gate off. This is the mutation that was SILENT until the "
     "expectedApp arms were added -- every other arm drives with NO session, "
     "and a no-session refusal is the same 403 whichever app the gate expected",
     API,
     "    const SD_GATE_APP = { 'law_trusttx': 'sairnlaw' };",
     "    const SD_GATE_APP = {};"),
]

# ── AND THE OTHER DIRECTION, WHICH IS THE ONLY EVIDENCE THAT MATTERS ────────
# run_probe proves the CURRENT suite refuses mutations 7-9. On its own that does
# not say the repair addressed the cause: a suite can catch a mutation for a
# reason unrelated to the thing that was fixed.
#
# So each same-reason mutation is ALSO run against a copy of the suite with the
# OLD predicates put back, and is required to go GREEN. A mutation that the old
# form misses and the new form catches is the difference the repair made,
# measured rather than argued. If one of these ever starts failing -- i.e. the
# old form catches it too -- then that mutation proves nothing about the repair
# and this control says so instead of quietly counting it.
# THE COUNTERFACTUAL IS THE REAL PRE-FIX FILE, TAKEN OUT OF HISTORY, not a
# hand-reverted copy. The first version of this control reverted three
# predicates by hand and got the wrong answer: it reported mutations 7 and 8 as
# SEEN, because the arms they trip -- the phase-2 arm and the expectedApp arms
# -- DID NOT EXIST before the repair, and hand-reverting a predicate does not
# remove an arm. A counterfactual assembled by hand is a guess about history;
# `git show` is history.
#
# The commit is DERIVED, not pinned: the one that introduced PHASE_2_GATED, and
# its parent is the file as it stood. A pinned sha would rot on the next rebase.
SAME_REASON = ['6. SAME-REASON TEST', '7. SAME-REASON TEST', '9. SAME-REASON TEST']


def _git(*a):
    return subprocess.run(['git'] + list(a), capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def old_form_is_blind():
    """Each same-reason mutation, against the suite AS IT ACTUALLY WAS."""
    repo = _git('rev-parse', '--show-toplevel').stdout.strip()
    # THE OLDEST commit touching PHASE_2_GATED, not the newest. `-1` gives the
    # most recent, which after any later edit is that edit -- and its parent
    # still contains the repair, so the control would compare the fix against
    # itself and report everything SEEN. Found by the control failing rather
    # than by reading it.
    # FORWARD SLASHES. git wants them in a pathspec and in a <rev>:<path> spec
    # even on Windows; os.path.join gives backslashes, `git show` answers "does
    # not exist", and this control would have reported "no pre-fix copy" -- a
    # COULD NOT RUN caused by a path separator and indistinguishable, from the
    # outside, from a genuine absence of history.
    gsuite = SUITE.replace(os.sep, '/')
    log = [l for l in _git('-C', repo, 'log', '--format=%H', '-S',
                           'PHASE_2_GATED', '--', gsuite).stdout.split('\n')
           if l.strip()]
    intro = log[-1] if log else ''
    if not intro:
        print('COULD NOT RUN the pre-fix control: no commit introduces '
              'PHASE_2_GATED in %s, so the counterfactual cannot be located. '
              'This is exit 3, not a pass.' % SUITE)
        return 3
    before = _git('-C', repo, 'show', '%s^:%s' % (intro, gsuite))
    if before.returncode != 0 or 'PHASE_2_GATED' in before.stdout:
        print('COULD NOT RUN the pre-fix control: %s^ does not yield a pre-fix '
              'copy of the suite. Exit 3.' % intro[:12])
        return 3

    wt = tempfile.mkdtemp(prefix='asi-old-')
    shutil.rmtree(wt, ignore_errors=True)
    add = _git('-C', repo, 'worktree', 'add', '-q', '--detach', wt, 'HEAD')
    if add.returncode != 0:
        print('COULD NOT RUN the pre-fix control: ' + (add.stderr or ''))
        return 3
    bad, ran = [], 0
    try:
        api_clean = io.open(os.path.join(repo, API), encoding='utf-8').read()
        io.open(os.path.join(wt, SUITE), 'w', encoding='utf-8',
                newline='').write(before.stdout)

        print('')
        print('PRE-FIX CONTROL -- the suite as it stood at %s^, from history. '
              'Each same-reason' % intro[:12])
        print('mutation must be BLIND to it, or it is not evidence that the '
              'repair mattered.')
        # The pre-fix suite must be GREEN on clean source, or every BLIND below
        # would be meaningless -- a suite that cannot pass cannot be blind.
        base = subprocess.run(['node', os.path.join(wt, SUITE)], cwd=wt,
                              capture_output=True, text=True, encoding='utf-8',
                              errors='replace')
        if base.returncode != 0:
            print('  COULD NOT RUN: the pre-fix suite is not green against '
                  'current source, so BLIND would mean nothing. Exit 3.')
            return 3
        print('  ok     the pre-fix suite is GREEN against current source -- '
              'which is the defect, restated')
        for name, rel, o, n in MUTATIONS:
            if not any(name.startswith(p) for p in SAME_REASON):
                continue
            if rel != API or o not in api_clean:
                print('  COULD NOT RUN  %s -- anchor missing' % name[:40])
                bad.append(name)
                continue
            io.open(os.path.join(wt, API), 'w', encoding='utf-8',
                    newline='').write(api_clean.replace(o, n, 1))
            r = subprocess.run(['node', os.path.join(wt, SUITE)], cwd=wt,
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace')
            blind = r.returncode == 0
            ran += 1
            print('  %-6s %s' % ('BLIND' if blind else 'SEEN', name[:92]))
            if not blind:
                bad.append(name)
            io.open(os.path.join(wt, API), 'w', encoding='utf-8',
                    newline='').write(api_clean)
    finally:
        _git('-C', repo, 'worktree', 'remove', '--force', wt)
    if not ran:
        print('  COULD NOT RUN: no same-reason mutation was executed. Exit 3.')
        return 3
    if bad:
        print('')
        print('%d same-reason mutation(s) were ALSO caught before the repair, '
              'so they are not evidence that it mattered:' % len(bad))
        for b in bad:
            print('    ' + b[:110])
        return 1
    print('  -- all %d are invisible to the suite as it was, and refused by the '
          'suite as it is. THAT is the repair, measured.' % ran)
    return 0


if __name__ == '__main__':
    rc = run_probe(
        SUITE, MUTATIONS,
        title='app session isolation -- the suite must refuse a gate that moves, '
              'and must no longer report a 403 as "reachable"',
        stage=[SUITE])
    rc2 = old_form_is_blind()
    sys.exit(rc or rc2)
