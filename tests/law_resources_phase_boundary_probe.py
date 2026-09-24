"""api/sd-data-sairnlaw-resources.test.js must REFUSE the drift it was just fixed for.

Run: python tests/law_resources_phase_boundary_probe.py

THIS SUITE RAN 18/20 ON origin/main AND BOTH RED ARMS WERE THE SUITE'S FAULT,
not the code's.

  * `BESPOKE` was a hardcoded four and a fifth bespoke branch shipped, so the
    orphan arm reported `law_trust_reconcile` as "registered with no handler" --
    a FALSE FINDING about a resource that works, inside a suite whose whole
    subject is resources that do not.
  * The PHASE 1 arm asserted all four bespoke resources still work WITHOUT a
    session, and carried its own instruction: "WHEN THAT HAPPENS THIS TEST MUST
    BE INVERTED, not deleted." It happened -- law_trusttx was gated the same day
    because attorney IOLTA trust money had no session check at all -- and the
    arm was not inverted.

A RED ARM NOBODY CAN ACT ON IS READ AS NOISE, AND THE NEXT GENUINELY RED ARM
BESIDE IT IS READ THE SAME WAY. That is the real cost of leaving these two, and
it is why the repair is not "make them green" but "make them able to fail again"
-- which is what this probe measures.

THE TWO ARMS THE REPAIR ADDED ARE THE ONES MOST AT RISK OF BEING VACUOUS.
BESPOKE is now DERIVED from the branches that exist, so "every bespoke resource
has a branch" asserted against it would be green against a codebase with every
branch deleted. Mutations 2 and 3 exist to prove the explicit expectation, not
the derived set, is what bites.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-sairnlaw-resources.test.js')
API = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    # ── THE PHASE BOUNDARY, IN BOTH DIRECTIONS ─────────────────────────────
    ("1. law_trusttx leaves the session registry -- the pre-2026-09-16 state, "
     "an attorney trust ledger reachable on the licence key alone, and the "
     "suite's PHASE 2 arm is the only thing here that would notice",
     API,
     # ANCHOR RE-DERIVED 2026-09-25: the entry stopped being the registry's
     # last row when phase 2 added four more gates, so the trailing-brace
     # anchor matched nothing and this arm sat ANCHOR-0 red on main.
     "      'law_trusttx': ['read', 'write'],",
     "      /* 'law_trusttx' entry removed -- licence-key-only again */"),

    # PREMISE RE-DERIVED 2026-09-25: the phased rollout COMPLETED --
    # law_deadlines is legitimately gated now (sd-data.js SD_SESSION_GATED),
    # so planting it "early" planted current reality and the arm reported
    # SILENT forever. The other-direction property survives in the suite as
    # `PHASE1_STILL_OPEN = []` asserted empty, so the mutation now reopens a
    # resource in that list -- the modern spelling of the same defect.
    ("2. the boundary stops biting in the OTHER direction -- a resource is "
     "declared still-open after the rollout completed, and the suite must "
     "refuse the claim rather than absorb it",
     SUITE,
     "  const PHASE1_STILL_OPEN = [];",
     "  const PHASE1_STILL_OPEN = ['law_deadlines'];"),

    # ── THE DERIVED LIST, WHICH IS THE PART THAT COULD GO VACUOUS ───────────
    ("3. the law_trust_reconcile branch is renamed away. BESPOKE is DERIVED "
     "from the branches present, so the derived set simply shrinks and notices "
     "nothing -- only BESPOKE_EXPECTED, which a human wrote down, can see a "
     "branch disappear",
     API,
     "    if (resource === 'law_trust_reconcile' && action === 'read') {",
     "    if (resource === 'law_trust_reconcile_DISABLED' && action === 'read') {"),

    ("4. a SIXTH bespoke branch appears and nobody lists it -- exactly how "
     "law_trust_reconcile came to be reported as an orphan. The suite must ask "
     "for it to be listed rather than silently absorbing it",
     API,
     "    if (resource === 'law_clients' && action === 'read') {",
     "    if (resource === 'law_escrow_TEST' && action === 'read') { res.status(200).json({ ok: true }); return; }\n"
     "    if (resource === 'law_clients' && action === 'read') {"),

    # ── AND THE ARM THAT KEEPS THE TWO PHASE LISTS HONEST ──────────────────
    # PREMISE RE-DERIVED 2026-09-25: the pre-completion open list this arm
    # quoted is gone (ANCHOR-0 on main). Same quiet failure, current shape:
    # a resource falls out of the GATED list without landing anywhere, and
    # the suite must notice it left the boundary rather than going green
    # having stopped asking about it.
    ("5. law_deadlines is dropped from the gated list without landing "
     "anywhere. It falls out of the boundary entirely and the suite must not "
     "go GREEN having stopped asking about it",
     SUITE,
     "  const PHASE2_NOW_GATED = ['law_trusttx', 'law_clients', 'law_matters', 'law_deadlines'];",
     "  const PHASE2_NOW_GATED = ['law_trusttx', 'law_clients', 'law_matters'];"),

    # ── REWRITTEN 2026-09-25: THE ORIGINAL MUTANT DID NOT PARSE ────────────
    # `[].concat([...new Set(` opened a paren nothing closed, so the suite
    # died on Unexpected end of input -- red about syntax, not about the
    # folded resource. Scored CAUGHT until the harness's parse check. The
    # rewrite makes the derived BESPOKE list silently LOSE law_trusttx --
    # what folding it into the generic map would actually look like from the
    # suite's own computation -- and parses.
    ("6. a bespoke resource is folded into the generic map, dropping its "
     "promoted columns and, for law_trusttx, its balance guard",
     SUITE,
     ")].filter((r) => !HANDLED[r]).sort();",
     ")].filter((r) => !HANDLED[r] && r !== 'law_trusttx').sort();"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNlaw resource phase boundary -- the suite must refuse a gate '
              'that moves, a branch that vanishes, and a resource that falls '
              'out of both phase lists',
        # The corrected suite is not committed yet; without staging it the
        # baseline is red because the FIX is absent, which says nothing about
        # whether the suite bites.
        stage=[SUITE, API]))
