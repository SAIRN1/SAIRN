"""tests/sairnbuild_server_wins.js must REFUSE, not merely agree.

Run: python tests/run_sairnbuild_server_wins_sabotage_probe.py

# REQUIREMENT: the suite guarding SAIRNbuild's server-wins conversion must go
#   RED when the merge reverts to additive, when the pending-set carve-out is
#   removed, when any of the three not-overwrite conditions stops failing
#   closed, when the trust gate that stands in for a bootstrap is bypassed or
#   attested without being earned, or when either of the two blocker repairs
#   is undone -- because every one of those failures is SILENT at runtime

EACH BLOCKER IS SABOTAGED ON ITS OWN, because each was a separate decision and
a probe that only proved "the suite is red for something" would not say which.
The three the plan named are arms 1-2 (the missing try/finally and the missing
catch), arms 3-4 (__overflow and an unreadable file, both of which have to
fail CLOSED), and arms 5-6 (bld_bids, which is not sync-hooked and would
otherwise get a carve-out that is always empty). Arms 7-10 are the carve-out
and the trust gate themselves.

── WHY THE TRUST GATE IS SABOTAGED IN BOTH DIRECTIONS ─────────────────────
Bypassing it overwrites records on a device whose pending list predates the
schema ever existing. Attesting it unconditionally is subtler and worse: the
flag is never cleared, so one wrong attestation makes the carve-out permanently
unearned on that device while everything keeps looking correct.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairnbuild_server_wins.js')
APP = 'sairnbuild.html'

MUTATIONS = [
    ("1. [BLOCKER A] THE finally IS REMOVED -- a throw inside st() leaves the "
     "whole app's backup suppressed for the rest of the session, invisibly",
     APP,
     "  try { return fn(); } finally { bldSeeding = was; }",
     "  var out = fn(); bldSeeding = was; return out;"),

    ("2. [BLOCKER A] THE BOOT CHAIN'S catch IS REMOVED -- a throw above it "
     "strands the pending-retry queue and says nothing",
     APP,
     # `}).catch(function(e){` alone appears FOUR times in this file, so the
     # anchor carries the line above it. ANCHOR-4 is a failure, not a skip.
     "    bldBackupNotice(pushed);\n  }).catch(function(e){",
     "    bldBackupNotice(pushed);\n  }).then(function(e){"),

    ("3. [BLOCKER B] __overflow IS IGNORED -- past the cap the list stops "
     "recording, so every id beyond it looks un-pending during exactly the "
     "long outage that filled the list",
     APP,
     "  var mayOverwrite = pend.state==='ok' && !pend.map.__overflow && bldPendingTrusted();",
     "  var mayOverwrite = pend.state==='ok' && bldPendingTrusted();"),

    ("4. [BLOCKER B] AN UNREADABLE PENDING FILE STOPS FAILING CLOSED -- "
     "'nothing is pending' is permission, and a failed read must never be "
     "read as permission",
     APP,
     "  var mayOverwrite = pend.state==='ok' && !pend.map.__overflow && bldPendingTrusted();",
     "  var mayOverwrite = !pend.map.__overflow && bldPendingTrusted();"),

    ("5. [BLOCKER C] bld_bids LOSES ITS PENDING TRACKING -- its hydrate is "
     "converted with a carve-out that is always empty, which is the silent "
     "inheritance the plan refused",
     APP,
     "BLD_PENDING_TRACKED['bld_bids'] = true;",
     "BLD_PENDING_TRACKED['bld_bids'] = false;"),

    ("6. [BLOCKER C] THE RETRY SENDS bld_bids WITHOUT ITS SESSION -- its "
     "branch in api/sd-data.js refuses that, so a pending bid is retried "
     "forever and never clears",
     APP,
     "jobs.push(bldData('write',key,rec,key==='bld_bids').then(function(saved){",
     "jobs.push(bldData('write',key,rec).then(function(saved){"),

    ("7. [CARVE-OUT] THE PENDING CHECK IS REMOVED -- every id the server has "
     "is overwritten, including one holding a change that never reached it",
     APP,
     "    if(mayOverwrite&&!pendingHere[id]){",
     "    if(mayOverwrite){"),

    ("8. [CARVE-OUT] THE MERGE REVERTS TO ADDITIVE -- a locally held id is "
     "never overwritten, which is the behaviour this whole conversion "
     "replaces",
     APP,
     "    if(mayOverwrite&&!pendingHere[id]){",
     "    if(false){"),

    ("9. [TRUST GATE] IT IS BYPASSED -- a device whose pending list predates "
     "the schema ever being run starts overwriting immediately",
     APP,
     "function bldPendingTrusted(){\n"
     "  try{ return localStorage.getItem(BLD_TRUST_KEY) !== null; }catch(e){ return false; }\n"
     "}",
     "function bldPendingTrusted(){\n"
     "  return true;\n"
     "}"),

    ("10. [TRUST GATE] IT IS ATTESTED WITHOUT BEING EARNED -- the flag is "
     "never cleared, so one wrong attestation makes the carve-out "
     "permanently unearned while everything looks correct",
     APP,
     "    if(_bldBackup.provisioned!==false&&bldPendingRead().state==='ok'&&bldPendingCount()===0)bldMarkPendingTrusted();",
     "    bldMarkPendingTrusted();"),

    # ── THE HALF THAT WAS MISSING, ADDED 2026-09-21 ────────────────────────
    # Mutation 10 above removes the whole condition, which every source-text
    # arm catches. These two leave it LOOKING right: the line still has
    # `bldPendingCount()===0` and still has the provisioned test, and the
    # arms that read it as text still pass. Only the arms that RUN it can
    # see that a never-written list now earns trust with zero pushes.

    ("11. THE ORIGINAL DEFECT, RESTORED: the attestation stops requiring the "
     "pending list to EXIST, so a device whose key was never written -- the "
     "pre-2026-09-04 install this design is reasoned about -- earns trust on "
     "its first load having pushed nothing",
     APP,
     "    if(_bldBackup.provisioned!==false&&bldPendingRead().state==='ok'&&bldPendingCount()===0)bldMarkPendingTrusted();",
     "    if(_bldBackup.provisioned!==false&&bldPendingCount()===0)bldMarkPendingTrusted();"),

    ("12. THE ONE THAT READS AS CORRECT: `state==='ok'` becomes "
     "`state!=='unreadable'`, which looks like the same fail-closed intent and "
     "still admits ABSENT -- the only state that matters here",
     APP,
     "bldPendingRead().state==='ok'&&bldPendingCount()===0",
     "bldPendingRead().state!=='unreadable'&&bldPendingCount()===0"),

    ("13. the boot chain loses its catch, so a throw anywhere above strands "
     "the pending retry in silence. Included because the arm guarding it was "
     "reading a FIXED 2200-character window and had just failed against a "
     "chain that still had one -- this proves the re-bounded arm bites",
     APP,
     # ANCHOR WIDENED before this arm was ever green: the bare `}).catch(` line
     # matches FOUR times in sairnbuild.html, and the harness reported ANCHOR-4
     # and refused rather than planting in whichever came first. Carried down to
     # the comment that names this one.
     "  }).catch(function(e){\n"
     "    // ── AND A CATCH, WHICH THIS CHAIN NEVER HAD",
     "  }).then(function(e){\n"
     "    // ── AND A CATCH, WHICH THIS CHAIN NEVER HAD"),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='SAIRNbuild server-wins: the carve-out from bld_sync_pending, the '
          'three conditions that must fail CLOSED, the trust gate, and both '
          'blocker repairs must all be REFUSABLE',
    stage=(APP,),
))
