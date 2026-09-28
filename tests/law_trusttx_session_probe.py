"""api/sd-data-law-trusttx-session.test.js must REFUSE, not merely agree.

Run: python tests/law_trusttx_session_probe.py

THE HIGHEST-STAKES GATE ON THE PLATFORM AND IT DID NOT EXIST. `law_trusttx` is
an attorney IOLTA client trust ledger -- the one figure a bar association
audits -- and both its read and write branches dispatched on the licence hash
alone. The licence key is shipped to the browser.

A SUITE WRITTEN THE SAME HOUR AS THE FIX IS A SUITE THAT HAS NEVER REFUSED
ANYTHING. Every mutation below removes one property of the gate, and each is a
change somebody could plausibly make while tidying:

  * the resource leaves the registry entirely, or leaves it for ONE action --
    a read-only hole is the quiet half, because nothing downstream errors;
  * the expected app reverts to the hardcoded 'stonedesk', which refuses every
    correctly signed-in attorney and would be "fixed" by removing the gate;
  * the session check becomes advisory -- verified and its answer discarded,
    which reads as correct at a glance because the call is right there;
  * the deactivated-credential refusal is downgraded to the NO_ACTIVE_CHECK
    warning path, so a deactivated attorney keeps trust access for the life of
    a 12h token;
  * the adjacent reconcile branch loses ITS session check, because moving the
    hole next door is the failure this whole finding is about.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-law-trusttx-session.test.js')
API = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    # ── ANCHOR RE-DERIVED 2026-09-25, same staleness as arm 4 below: the
    # entry stopped being the map's LAST row when later gates were added, so
    # the `...]\n    };` anchor matched nothing and this arm was ANCHOR-0 red
    # on main. The mutation now removes the entry alone, wherever it sits.
    ("1. law_trusttx leaves the session registry entirely -- the pre-fix state, "
     "restored in one line",
     API,
     "      'law_trusttx': ['read', 'write'],",
     "      /* 'law_trusttx' entry removed -- ungated again */"),

    ("2. only the WRITE is gated -- the quiet half, because a readable trust "
     "ledger errors nowhere and looks like a working app",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'law_trusttx': ['write']"),

    ("3. only the READ is gated, so anyone with the licence key can POST a "
     "disbursement",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'law_trusttx': ['read']"),

    # ── ANCHOR RE-DERIVED 2026-09-25: SD_GATE_APP grew into a MULTI-LINE map
    # (law_clients/matters/deadlines, then the sdn five) and the single-line
    # literal this arm quoted matched NOTHING -- the arm was failing ANCHOR-0
    # on main, the stale-anchor class the harness exists to refuse. The
    # mutation now removes only the law_trusttx ENTRY, which is the same
    # defect (this resource's expected app falls back to 'stonedesk') without
    # asserting anything about the map's other rows.
    ("4. the expected app reverts to the hardcoded 'stonedesk' -- every "
     "correctly signed-in attorney is refused, and the obvious fix for THAT is "
     "to remove the gate",
     API,
     "      'law_trusttx': 'sairnlaw',",
     "      /* 'law_trusttx' entry removed -- falls back to 'stonedesk' */"),

    ("5. the session is verified and its answer DISCARDED -- the call is right "
     "there, so review reads it as present",
     API,
     "      if (!gateSession) {\n        res.status(403).json({",
     "      if (false) {\n        res.status(403).json({"),

    # ── MUTATION REPOINTED 2026-09-28: IT WAS PLANTING NOTHING ─────────────
    # This arm aimed at `if (!preActive.ok && preActive.code ===
    # 'CREDENTIAL_INACTIVE') {` -- but that is the NO-ROW-ON-AN-UNSCOPED-
    # RESOURCE log branch, and it sits AFTER `if (preHardRefusal) { ...
    # return; }`. A genuinely deactivated credential (reason === 'inactive')
    # never reaches it: it is refused 403 one branch earlier. So `if (false)`
    # there changed which MESSAGE a cross-app token gets logged with and
    # nothing else, the trust ledger stayed shut, and the suite was green
    # BECAUSE THE LABELLED DEFECT WAS NEVER PLANTED. Reported as SILENT for
    # days; the diagnosis blamed a stale anchor in
    # api/sd-data-active-credential.test.js, which is a different suite and was
    # a different (real) defect. A mutation that cannot produce the outcome its
    # label names is worse than a missing arm: the arm reads as coverage.
    #
    # The docstring above already says what the defect IS -- the refusal
    # DOWNGRADED to the warning path -- so the anchor is now the refusal's own
    # guard. Disabling it drops a deactivated attorney through to the no-row
    # log and on into the branch gate, which their token and role both satisfy,
    # and the ledger answers 200. Arm 4 of the suite expects 403
    # CREDENTIAL_INACTIVE and is driven with active:false, so it goes red.
    ("6. a DEACTIVATED credential falls through to the warning path, so "
     "somebody who has just left the firm keeps trust access for the life of a "
     "12h token",
     API,
     "        if (preHardRefusal) {",
     "        if (false) {"),

    ("7. the ADJACENT reconcile branch loses its own session check -- moving "
     "the hole next door is the exact failure this finding is about",
     API,
     "      if (!recSess) { res.status(401).json({ error: { code: 'NO_SESSION', "
     "message: 'Sign in first' } }); return; }",
     "      if (false) { res.status(401).json({ error: { code: 'NO_SESSION', "
     "message: 'Sign in first' } }); return; }"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='law_trusttx session gate -- the suite must refuse a trust '
              'ledger that is reachable on a licence key alone',
        # THE FIX ITSELF IS STAGED IN. The worktree is at HEAD and the gate is
        # not committed yet; without this the baseline is red because the fix
        # is absent, not because the suite is wrong -- and the control would
        # only be runnable after the push, which is the wrong order.
        stage=[API]))
