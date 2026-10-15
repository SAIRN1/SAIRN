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

THAT CLAIM WAS MEASURED AND IS NOW UNVERIFIED, AND THAT IS SAID AT THE TOP
RATHER THAN BURIED. old_form_is_blind() pulled the suite AS IT ACTUALLY WAS out
of git -- the parent of the commit that introduced PHASE_2_GATED, derived rather
than pinned -- and required every same-reason mutation to leave it GREEN. It is
RETIRED as of 2026-10-14: a suite carrying a HAND-WRITTEN record of its subject
cannot be replayed against a later subject, and three candidate pre-repair
commits were driven to prove that rather than assuming it -- all three fail on
`sairngrounds: measured SOME, recorded NONE`, a gate that landed 2026-10-07 and
that no historical copy can know about. The full account, the measurement and
the smaller control that would restore the evidence without replay are in the
docstring of counterfactual_retired(). SO THE SAME-REASON SET IS STILL DRIVEN
AND STILL REFUSED; what is no longer shown is that the OLD predicate was blind
to it.

THE FIRST THREE CANDIDATES WERE WRONG AND THE CONTROL SAID SO, while it ran:

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
import re
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
     # ANCHOR REPAIRED 2026-09-23. It matched law_trusttx as the LAST entry in
     # SD_SESSION_GATED, closing brace and all. The map has since grown past it
     # -- law_clients, law_matters and law_deadlines followed it in when phase
     # 2 completed -- so the brace is no longer adjacent and this anchor had
     # matched NOTHING for some time. The entry line, comma included, is the
     # stable spelling, and deleting it is exactly what this mutation means.
     API,
     "      'law_trusttx': ['read', 'write'],\n",
     ""),

    ("2. only the READ is gated. The quiet half: a trust ledger that can be "
     "read by anyone holding the licence key errors nowhere, and the write "
     "refusal makes the feature look protected",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'law_trusttx': ['write']"),

    # ── MUTATION 3 WITHDRAWN 2026-09-24, the SECOND casualty of ce835a7e ──
    # It planted `'law_deadlines': ['read','write']` into SD_SESSION_GATED to
    # express "a still-open resource is gated EARLY, before its phase-2 day".
    # ce835a7e completed phase 2: law_deadlines is now in that map LEGITIMATELY
    # (api/sd-data.js:995), so the mutation inserted a DUPLICATE key with the
    # identical value -- in a JS object literal the last key wins, the planted
    # line changed nothing, and the suite was RIGHT to stay green. An
    # equivalent mutant, but unlike the withdrawn `!== 401` it did not start
    # as one: TIME made it equivalent, which is the eighth discipline's shape
    # (nothing announces the day a check stops testing anything) landing on a
    # probe's own arm. It surfaced as a SILENT verdict the first day the
    # suite's baseline went green -- the arm had been unreachable behind a red
    # baseline since before its subject expired.
    #
    # NOT REPOINTED, and the reason is a fact about the boundary rather than a
    # judgement: STILL_UNGATED is now EMPTY -- every phase-1 resource is gated
    # -- so "gated early" has no remaining subject in this suite's scope. The
    # class returns the day a new app's resources enter a phased rollout, and
    # belongs to that suite when it does.

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
     # ANCHOR REPAIRED 2026-09-23. PHASE_2_GATED held only law_trusttx when
     # this was written; `ce835a7e` completed phase 2 and it now holds all
     # four, so the one-element spelling stopped matching. The intent is
     # unchanged -- law_trusttx falls back into STILL_UNGATED, which demands
     # 200 and gets the gate's 403.
     SUITE,
     "  const PHASE_2_GATED = ['law_trusttx', 'law_clients', 'law_matters', 'law_deadlines'];",
     "  const PHASE_2_GATED = ['law_clients', 'law_matters', 'law_deadlines'];"),

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
     # ── ANCHOR REPAIRED 2026-10-14 (cody b11), REPORTED AS ANCHOR-3 ─────────
     # The anchor was the bare 403/FORBIDDEN block. It was unique when written
     # and api/sd-data.js now contains it THREE times -- the SD_SESSION_GATED
     # gate at :2106, which is the one this mutation names, plus two ROLE gates
     # that landed later and have nothing to do with the session boundary:
     # sairnsenior's MANAGEMENT_ROLES at :6777 and sairnbuild's BLD_DRAW_ROLES
     # at :13983. The harness reported ANCHOR-3 and FAILED the arm, which is
     # the right answer -- `replace(o, n, 1)` would have planted in whichever
     # came first, asserting something about a line nobody chose.
     #
     # NOT A COVERAGE GAP IN THE SUITE, and the distinction is the whole point:
     # this arm was never running. It was reachable only because the fix to
     # tests/app_session_isolation.js took this probe from exit 2 COULD NOT RUN
     # (baseline red) to actually driving its mutations.
     #
     # `if (!gateSession) {` is carried into the anchor because it is the line
     # that IDENTIFIES the session gate. Measured unique at the time of writing,
     # and the harness fails loudly on ANCHOR-0 or ANCHOR-2 if that changes
     # again rather than planting somewhere arbitrary.
     API,
     "      if (!gateSession) {\n        res.status(403).json({\n          error: {\n            code: 'FORBIDDEN',",
     "      if (!gateSession) {\n        res.status(500).json({\n          error: {\n            code: 'FORBIDDEN',"),

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
     # ── ANCHOR REPAIRED 2026-09-23, AND THE NEW GUARD IS WHAT FOUND IT ──────
     # It read `const SD_GATE_APP = { 'law_trusttx': 'sairnlaw' };` -- the map
     # as a one-liner. SD_GATE_APP has since grown to fourteen sf_* entries
     # plus law_matters and law_deadlines across forty lines, so that string
     # has not matched for some time. str.replace did nothing, the pre-fix
     # suite ran against CLEAN source, and the arm was counted.
     #
     # AND THE OLD GUARD REPORTED IT AS THE WRONG THING. A missing anchor went
     # into the same bucket as "the old form caught it too", so the run exited
     # 1 under the sentence "1 same-reason mutation(s) were ALSO caught before
     # the repair" -- a claim about the suite, printed for a stale table in
     # this file. It is now a CANNOT and exit 3.
     #
     # The anchor is the ENTRY rather than the whole map: removing
     # law_trusttx's line is exactly the reversion this mutation is about, it
     # survives the map growing, and it matches exactly once (checked).
     API,
     "      'law_trusttx': 'sairnlaw',\n",
     ""),
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


def counterfactual_retired():
    """RETIRED 2026-10-14 (cody b12), with the finding recorded.

    WHAT IT DID. `old_form_is_blind()` below replayed the suite AS IT ACTUALLY
    WAS, taken out of git history, against each same-reason mutation -- so that
    "the repair mattered" was evidence rather than a claim. It worked once and
    then stopped, reporting exit 3 COULD NOT RUN: "the pre-fix suite is not
    green against current source, so BLIND would mean nothing."

    THE DECISION WAS RE-BASE OR RETIRE, AND IT IS RETIRE, BECAUSE RE-BASING
    CANNOT WORK -- MEASURED, NOT ASSUMED. Three candidate pre-repair commits
    were driven against current source on 2026-10-14, each copy taken straight
    out of history:

        79854387^   33 ok, exit 1    the commit the control already used
        4f757c3f^   33 ok, exit 1    the `!== 401` repair's own parent
        2efe796f^   33 ok, exit 1    the LATEST pre-repair boundary, the day
                                     the posture column stopped counting 401
                                     only -- nine days closer to today

    ALL THREE FAIL AT THE SAME ARM AND IT IS NOT THE PREDICATE:
    `sairngrounds: measured SOME, recorded NONE`. The sairngrounds session gate
    landed on 2026-10-07 in 6a2690be and NO historical copy of this suite can
    know that, because the posture map is a HAND-WRITTEN record of the world at
    the moment it was written. A later pre-repair commit is still before
    2026-10-07, so moving the anchor forward buys nothing; and the failure is
    not in the thing under test, so it cannot be excluded without excluding the
    arm that makes the suite a drift detector at all.

    THE PREMISE WAS WRONG, WHICH IS THE FINDING. A suite that carries a
    hand-written record of its subject cannot be replayed against a later
    subject. It is not that this counterfactual broke; it is that it was always
    going to, on the first gate that landed after it was written. The cost is
    real and is named rather than written off: the same-reason mutations can no
    longer be SHOWN to have been invisible to the old `!== 401` predicate. That
    is a loss of evidence, not a pass.

    WHAT WOULD REPLACE IT, for whoever picks this up: do not replay the suite.
    Apply the OLD PREDICATE to the mutant's own refusal -- assert that
    `!== 401` accepts a 500 and that `=== 403 && FORBIDDEN` refuses it -- which
    needs no historical copy and no world-state. That is a smaller, durable
    control over the one line that actually changed.

    SO THIS FUNCTION IS NOT A STUB. It asserts that the retirement reason STILL
    HOLDS: the suite still carries a hand-written posture table. The day that
    table becomes DERIVED, replay becomes possible and the retirement must be
    revisited -- so that is exit 3 COULD NOT TELL with the reason named, never
    a silent pass.
    """
    repo = _git('rev-parse', '--show-toplevel').stdout.strip()
    gsuite = SUITE.replace(os.sep, '/')
    src = io.open(os.path.join(repo, SUITE), encoding='utf-8').read()
    print('')
    print('PRE-FIX COUNTERFACTUAL -- RETIRED 2026-10-14, reason recorded in the')
    print('docstring of counterfactual_retired(). Three candidate pre-repair')
    print('commits were driven and all three fail on the hand-written posture')
    print('row, not on the predicate under test.')
    # The retirement rests on ONE property: the posture map is hand-written.
    # Asserted against the suite's own source, in both directions -- the table
    # must be there AND must still be literal rows rather than a derivation.
    has_table = 'const POSTURE' in src
    literal_rows = len(re.findall(r"\n  [a-z]+:\s*\{ gate: '", src))
    derived_marker = re.search(r'POSTURE\s*=\s*[^{\n]*\b(map|reduce|'
                               r'fromEntries|forEach)\b', src)
    if not has_table or literal_rows < 2 or derived_marker:
        print('  COULD NOT TELL: the retirement premise no longer holds.')
        print('    const POSTURE present: %s; literal hand-written rows: %d; '
              'derivation detected: %s'
              % (has_table, literal_rows, bool(derived_marker)))
        print('    If the posture map is now DERIVED, a historical copy CAN be')
        print('    replayed and the counterfactual should be re-opened rather')
        print('    than left retired. Exit 3, not a pass.')
        return 3
    print('  ok     the posture map is still %d hand-written rows, so a '
          'historical copy' % literal_rows)
    print('         still cannot be replayed against current source. The '
          'retirement stands.')
    print('  NOTE   LOSS OF EVIDENCE, STATED: the same-reason mutations above '
          'are no longer')
    print('         shown to have been INVISIBLE to the old `!== 401` '
          'predicate. See the')
    print('         docstring for the smaller control that would restore it '
          'without replay.')
    return 0


def old_predicate_is_blind(force=None, quiet=False):
    """THE REPLACEMENT for the retired replay. Written 2026-10-14 (cody b13).

    WHAT THE RETIRED CONTROL WAS FOR, because the replacement has to keep it.
    run_probe() proves the CURRENT suite refuses mutations 6, 7 and 9. On its
    own that says nothing about whether the 2026-09-16 repair addressed the
    CAUSE -- a suite can catch a mutation for a reason unrelated to the thing
    that was fixed. The evidence is the other direction: the OLD predicate must
    have been BLIND to the same mutation. `counterfactual_retired()` records why
    replaying the historical suite can no longer produce that evidence, and it
    is worth reading before this function.

    THIS DOES NOT REPLAY ANYTHING, WHICH IS THE WHOLE DESIGN. The retired
    control ran a historical COPY OF THE SUITE against current source, so it
    dragged in every unrelated thing that copy asserted -- and it died on a
    hand-written posture row that cannot know about a gate landing in 2026-10.
    The property actually under test is much smaller than a suite: it is ONE
    EXPRESSION. `out.code !== 401` versus `out.code === 403 && ... FORBIDDEN`.
    So the two predicates are applied DIRECTLY to the refusal shape each
    mutation produces. No worktree, no historical suite, no world-state, and
    nothing that a later gate landing somewhere else can invalidate.

    EVERY INPUT IS DERIVED, AND THAT IS NOT A FLOURISH -- a retyped predicate
    or a retyped status code is the second-copy defect this file has already
    paid for twice:
      * the NEW predicates come out of tests/app_session_isolation.js, from the
        two `ok(` expressions the arms actually use;
      * the OLD predicate comes out of HISTORY, from the same DERIVED commit
        the retired control located -- the one that introduced PHASE_2_GATED --
        and only ONE EXPRESSION is read from it, never the file to run;
      * each mutant status code comes out of the MUTATION TABLE above, from the
        replacement text of the mutation itself.
    Anything that cannot be derived is exit 3 UNPROVEN with the reason named,
    never a pass. A control that cannot find its own inputs has not run.

    TWO CONTROLS, BOTH DIRECTIONS, because each arm below is satisfiable by a
    broken predicate on its own:
      * "the new predicate refuses everything" would satisfy every REFUSED arm,
        so the new predicate must ACCEPT the HEALTHY shape.
      * "the old predicate accepts everything" would satisfy every BLIND arm,
        so the old predicate must REFUSE a 401 shape -- the one code it could
        see, which is why 401 was never a legitimate mutation here.

    MUTATION 6 IS NOT APPLICABLE AND IS SAID SO RATHER THAN COUNTED. It changes
    an app NAME, not a status code, and the arm it trips -- the expectedApp arm
    -- DID NOT EXIST before the repair. That is the exact trap the first version
    of the retired control fell into: hand-reverting a predicate does not remove
    an arm. There is no pre-repair predicate to apply, so this control reports it
    as out of scope instead of pretending to measure it.
    """
    print('')
    print('OLD-PREDICATE CONTROL -- the replacement for the retired replay.')
    print('Each same-reason mutation\'s own refusal shape, put through BOTH')
    print('predicates. No historical suite is run.')

    repo = _git('rev-parse', '--show-toplevel').stdout.strip()
    bad, unrun, ran = [], [], 0

    def cannot(which, why):
        print('  CANNOT %s' % which[:92])
        print('         %s' % why)
        unrun.append(which)

    # ── 1. THE NEW PREDICATES, OUT OF THE SUITE ─────────────────────────────
    # The gate arm and the oracle arm assert different codes, so both are read
    # rather than one being assumed to stand for the other.
    try:
        suite_src = io.open(os.path.join(repo, SUITE), encoding='utf-8').read()
    except OSError as exc:                                       # noqa: BLE001
        print('  COULD NOT RUN: %s is unreadable (%s), so no predicate can be '
              'derived. Exit 3.' % (SUITE, exc))
        return 3
    m_gate = re.search(r'ok\(out\.code === (\d{3}) && out\.body && out\.body\.error'
                       r"\s*&& out\.body\.error\.code === '([A-Z_]+)'", suite_src)
    m_oracle = re.search(r'ok\(out\.code === (\d{3}),\s*\n\s*\'\.\.\.and it is the '
                         r'LICENCE boundary', suite_src)
    if not m_gate or not m_oracle:
        cannot('the NEW predicates', 'one of the two positive `ok(out.code === '
               'NNN ...)` expressions is no longer in %s, so this control cannot '
               'say what the repair produced. gate=%s oracle=%s'
               % (SUITE, bool(m_gate), bool(m_oracle)))
        print('')
        print('UNPROVEN: the new predicate could not be derived. Exit 3.')
        return 3
    GATE_OK_CODE, GATE_OK_ERR = int(m_gate.group(1)), m_gate.group(2)
    ORACLE_OK_CODE = int(m_oracle.group(1))
    # ── THE ONE INJECTION POINT THE ABLATION USES ───────────────────────────
    # `force` overrides a DERIVED constant and nothing else. It exists so the
    # ablation below can break exactly one input at a time without editing this
    # file, copying it, or touching the suite -- and because an arm whose
    # failure path has never been driven is an assertion, not a check. It is
    # never set on an ordinary run.
    _f = force or {}
    # THE SHAPE'S error code and the PREDICATE'S expected error code are two
    # names, and the ablation is what forced that apart. With one name,
    # overriding it moved the predicate AND the healthy shape together, they
    # still agreed, and CONTROL A could not fail -- a control that cannot fail
    # is the thing this file exists to refuse. Found by driving A3, not by
    # reading.
    GATE_SHAPE_ERR = GATE_OK_ERR
    GATE_OK_CODE = _f.get('GATE_OK_CODE', GATE_OK_CODE)
    GATE_OK_ERR = _f.get('GATE_OK_ERR', GATE_OK_ERR)
    ORACLE_OK_CODE = _f.get('ORACLE_OK_CODE', ORACLE_OK_CODE)
    if not quiet:
        print('  derived from %s: gate arm demands %d %s, oracle arm demands %d'
              % (SUITE, GATE_OK_CODE, GATE_OK_ERR, ORACLE_OK_CODE))

    # ── 2. THE OLD PREDICATE, OUT OF HISTORY -- ONE EXPRESSION, NOT A FILE ──
    # The commit is DERIVED the same way the retired control derived it: the
    # OLDEST commit introducing PHASE_2_GATED, whose parent is the pre-repair
    # file. A pinned sha would rot on the next rebase, and this repo rebases.
    gsuite = SUITE.replace(os.sep, '/')
    log = [l for l in _git('-C', repo, 'log', '--format=%H', '-S',
                           'PHASE_2_GATED', '--', gsuite).stdout.split('\n')
           if l.strip()]
    intro = log[-1] if log else ''
    old_src = ''
    if intro:
        before = _git('-C', repo, 'show', '%s^:%s' % (intro, gsuite))
        if before.returncode == 0:
            old_src = before.stdout
    m_old = re.search(r'ok\((?:own|out)\.code !== (\d{3})', old_src)
    if not m_old:
        cannot('the OLD predicate', 'no `ok(<x>.code !== NNN` expression could be '
               'read out of %s^:%s, so the counterfactual predicate is not '
               'available. This control refuses to retype it -- a hand-written '
               'pre-fix predicate is a guess about history, which is the defect '
               'the retired replay was built to avoid.'
               % ((intro or 'NO-COMMIT')[:12], gsuite))
        print('')
        print('UNPROVEN: the old predicate could not be derived. Exit 3.')
        return 3
    # DERIVED_OLD is kept apart from OLD_BLIND_TO for the same reason, and the
    # ablation found this one too: CONTROL B asked whether the predicate refuses
    # OLD_BLIND_TO, which is whatever OLD_BLIND_TO happens to be -- true by
    # construction for every value, so A4 could not fail it. The property is
    # that the predicate refuses the code HISTORY recorded.
    DERIVED_OLD = int(m_old.group(1))
    OLD_BLIND_TO = _f.get('OLD_BLIND_TO', DERIVED_OLD)
    if not quiet:
        print('  derived from %s^: the pre-repair predicate is `code !== %d`'
              % (intro[:12], OLD_BLIND_TO))

    # ── 3. THE PREDICATES AS FUNCTIONS, each applied to a refusal shape ─────
    def old_accepts(shape):
        """The pre-repair form: a negation of ONE refusal code."""
        return shape['code'] != OLD_BLIND_TO

    def new_accepts(shape, kind):
        if kind == 'oracle':
            return shape['code'] == ORACLE_OK_CODE
        return (shape['code'] == GATE_OK_CODE
                and (shape.get('error') == GATE_OK_ERR))

    # ── 4. THE MUTANT SHAPES, OUT OF THE MUTATION TABLE ─────────────────────
    # The status code each mutation installs is read from its own replacement
    # text, so editing the table moves this control with it.
    SHAPES = {
        '7. SAME-REASON TEST': ('gate', r'res\.status\((\d{3})\)',
                                r'res\.status\((\d{3})\)'),
        '9. SAME-REASON TEST': ('oracle', r'status: (\d{3}),',
                                r'status: (\d{3}),'),
    }
    for name, rel, old, new in MUTATIONS:
        key = next((k for k in SAME_REASON if name.startswith(k)), None)
        if key is None:
            continue
        if key not in SHAPES:
            cannot(name, 'this same-reason mutation changes no STATUS CODE -- it '
                         'changes an app name -- and the arm it trips did not '
                         'exist before the repair, so there is no pre-repair '
                         'predicate to apply. OUT OF SCOPE for this control, '
                         'reported rather than counted. (The retired replay fell '
                         'into exactly this: hand-reverting a predicate does not '
                         'remove an arm.)')
            continue
        kind, old_rx, new_rx = SHAPES[key]
        m_h = re.search(old_rx, old if isinstance(old, str) else '')
        m_m = re.search(new_rx, new if isinstance(new, str) else '')
        if not m_h or not m_m:
            cannot(name, 'the status code could not be read out of this '
                         'mutation\'s own text, so the shape it produces is '
                         'unknown. healthy=%s mutant=%s' % (bool(m_h), bool(m_m)))
            continue
        healthy_code, mutant_code = int(m_h.group(1)), int(m_m.group(1))
        if healthy_code == mutant_code:
            cannot(name, 'the mutation installs the SAME status code it replaces '
                         '(%d), so it changes nothing this control can see and '
                         'BLIND would be meaningless.' % healthy_code)
            continue
        healthy = {'code': healthy_code, 'error': GATE_SHAPE_ERR}
        mutant = {'code': mutant_code, 'error': GATE_SHAPE_ERR}
        ran += 1

        blind = old_accepts(mutant)
        caught = not new_accepts(mutant, kind)
        label = '%s (%d -> %d)' % (key, healthy_code, mutant_code)
        if blind and caught:
            print('  BLIND  %s  -- old `!== %d` ACCEPTS it, new predicate '
                  'REFUSES it' % (label, OLD_BLIND_TO))
        elif not blind:
            bad.append('%s: the OLD predicate ALSO refuses %d, so this mutation '
                       'is not evidence that the repair mattered'
                       % (label, mutant_code))
            print('  SEEN   %s  -- the old form caught it too' % label)
        else:
            bad.append('%s: the NEW predicate ACCEPTS %d, so the repair does not '
                       'catch this mutation at all' % (label, mutant_code))
            print('  MISS   %s  -- the new predicate accepts it' % label)

        # CONTROL A: the new predicate must ACCEPT the healthy shape, or
        # "refuses everything" satisfies the arm above.
        if not new_accepts(healthy, kind):
            bad.append('%s CONTROL: the NEW predicate refuses the HEALTHY shape '
                       '%d too, so "it refuses the mutant" is not evidence'
                       % (label, healthy_code))
            print('  FAIL   %s  CONTROL: new predicate refuses the healthy shape'
                  % label)

    # CONTROL B: the old predicate must REFUSE the one code it could see.
    # Without this, "accepts everything" satisfies every BLIND line above -- and
    # it is also why 401 was never a legitimate mutation in this table.
    if old_accepts({'code': DERIVED_OLD, 'error': GATE_SHAPE_ERR}):
        bad.append('CONTROL: the OLD predicate in use accepts %d, the one code '
                   'history records it could see, so it is not the negation this '
                   'control thinks it is and every BLIND line above is vacuous.'
                   % DERIVED_OLD)
        print('  FAIL   CONTROL: the old predicate accepts %d' % DERIVED_OLD)
    else:
        print('  ok     CONTROL: the old predicate really does refuse %d, the '
              'code history records, so BLIND is not "accepts anything"'
              % DERIVED_OLD)

    print('')
    if unrun:
        print('%d same-reason mutation(s) COULD NOT be put through this control, '
              'named above.' % len(unrun))
    if bad:
        for b in bad:
            print('  ! %s' % b)
        print('EXIT 1 -- the repair is NOT shown to have addressed the cause.')
        return 1
    if ran == 0:
        print('UNPROVEN: no same-reason mutation reached this control, so '
              'nothing was measured. Exit 3, not a pass.')
        return 3
    print('  -- %d same-reason mutation(s) are INVISIBLE to the pre-repair '
          'predicate and REFUSED by the current one.' % ran)
    print('  THAT is the repair, measured, with no historical suite replayed.')
    return 0


def ablate_old_predicate_control():
    """Drive old_predicate_is_blind()'s own failure paths. Nothing is written.

    FAILING-FIRST, AND THE RED IS THE STATE THIS REPLACED. Before b13 the
    property was UNVERIFIED and this file said so at the top: "what is no longer
    shown is that the OLD predicate was blind to it." The retired replay could
    not produce it, run_probe cannot produce it, and the suite exited 0 with the
    gap written down. That is the red.

    So the new arms are not merely green -- each one is driven to its FAILURE,
    by breaking exactly ONE derived input through `force` and requiring the
    verdict to change. An arm whose failure path has never been driven is an
    assertion rather than a check, and this control exists to catch a predicate
    that cannot discriminate.
    """
    print('')
    print('ABLATION of the old-predicate control -- one derived input broken per')
    print('case, and the verdict must change. The clone is never written.')
    CASES = [
        ('A1 the NEW predicate accepts the mutant code -> MISS, not BLIND',
         {'GATE_OK_CODE': 500}, 1),
        ('A2 the OLD predicate also refuses the mutant -> SEEN, so the mutation '
         'is not evidence', {'OLD_BLIND_TO': 500}, 1),
        ('A3 CONTROL A -- the new predicate refuses the HEALTHY shape too',
         {'GATE_OK_ERR': 'NOT_THE_CODE'}, 1),
        ('A4 CONTROL B -- the old predicate accepts the one code it could see',
         {'OLD_BLIND_TO': 599}, 1),
    ]
    bad = 0
    base = old_predicate_is_blind(quiet=True)
    if base != 0:
        print('  COULD NOT RUN: the control is not green unmutated (exit %d), so '
              'a changed verdict below would mean nothing. Exit 3.' % base)
        return 3
    print('  ok     BASELINE: the control is green unmutated, so every changed '
          'verdict below is the mutation')
    for label, force, want in CASES:
        got = old_predicate_is_blind(force=force, quiet=True)
        okd = got == want
        if not okd:
            bad += 1
        print('  %s %s  -- exit %d, wanted %d'
              % ('ok    ' if okd else 'FAIL  ', label, got, want))
    print('')
    print('  %d of %d ablation case(s) changed the verdict'
          % (len(CASES) - bad, len(CASES)))
    return 1 if bad else 0


def old_form_is_blind():
    """DEAD CODE, KEPT ON PURPOSE -- see counterfactual_retired().

    Not called. It is left in place rather than deleted because it is the only
    written-down account of how the replay was done correctly -- the derived
    commit rather than a pinned sha, the oldest introducing commit rather than
    the newest, the forward-slash pathspec, the anchor guard as a third state --
    and whoever builds the replacement control will want every one of those
    lessons. Deleting it would retire the reasoning along with the mechanism.
    """
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
    bad, ran, unrun = [], 0, []

    # ── THE ANCHOR GUARD, AND WHY IT IS A THIRD STATE RATHER THAN A FINDING ──
    # This loop mutates api/sd-data.js by `api_clean.replace(o, n, 1)`. When a
    # refactor moves the anchor, str.replace does NOTHING and returns the
    # string unchanged -- so the pre-fix suite runs against CLEAN source, exits
    # 0, and the arm prints BLIND. A mutation that never applied would be
    # counted as evidence that the repair mattered, which is the exact shape of
    # the defect this whole probe was written about: green for a reason nobody
    # asked for.
    #
    # IT WAS ALREADY GUARDED AND THE GUARD ANSWERED THE WRONG QUESTION. The old
    # form appended a missing anchor to `bad`, which made the run exit 1 under
    # the message "N same-reason mutation(s) were ALSO caught before the
    # repair" -- a sentence about the suite, printed for a condition that is
    # about this file's own table. Everywhere else in this function a
    # could-not-run exits 3. Folding one into a finding is how a stale table
    # gets read as a result.
    def cannot(which, why):
        print('  CANNOT %s' % which[:92])
        print('         %s' % why)
        unrun.append(which)

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
            if rel != API:
                cannot(name, 'this same-reason mutation does not target %s, so '
                             'the pre-fix counterfactual cannot be driven for '
                             'it at all.' % API)
                continue
            if o not in api_clean:
                cannot(name, 'ANCHOR MISSING in %s. The replace below would be '
                             'a no-op, the pre-fix suite would run against '
                             'CLEAN source, and this arm would print BLIND '
                             'having tested nothing. Could-not-run, not a pass '
                             'and not a finding.' % API)
                continue
            mutated = api_clean.replace(o, n, 1)
            # BELT AND BRACES, AND NOT REDUNDANT: the anchor check above proves
            # the needle is present, this proves the write actually differs. An
            # anchor equal to its replacement would satisfy the first and still
            # be a no-op.
            if mutated == api_clean:
                cannot(name, 'the mutation changed nothing -- anchor present '
                             'but the replacement is identical to it. BLIND '
                             'would be meaningless.')
                continue
            io.open(os.path.join(wt, API), 'w', encoding='utf-8',
                    newline='').write(mutated)
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
    if unrun:
        print('')
        print('%d same-reason mutation(s) COULD NOT BE DRIVEN -- see CANNOT '
              'above. That is exit 3, not a pass and not a finding.' % len(unrun))
        return 3
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
    rc2 = counterfactual_retired()
    # THE REPLACEMENT RUNS AFTER THE RETIREMENT NOTE, deliberately: the note
    # explains why a replay is gone, and this measures the same property
    # without one. `max` rather than `or` -- a 1 must outrank a 3, because a
    # failure is a finding and a could-not-run is not.
    rc3 = old_predicate_is_blind()
    # ABLATION IS OPT-IN because it runs the control five times. `--ablate`
    # drives each new arm to its own failure; the ordinary run does not need to.
    rc4 = ablate_old_predicate_control() if '--ablate' in sys.argv else 0
    codes = [c for c in (rc, rc2, rc3, rc4) if c]
    sys.exit(1 if 1 in codes else (max(codes) if codes else 0))
