"""tests/sairncare_route_record.js must REFUSE, not merely agree.

Run: python tests/run_sairncare_route_record_sabotage_probe.py

# REQUIREMENT: the suite guarding alf_claim_routes must go RED when the
#   coverage of "the engine never judged" narrows back, when WROTE/MISSED/
#   UNKNOWN collapses into two answers, when an UNKNOWN write re-offers the
#   retry button, or when `provisioned:false` is thrown away again -- because
#   every one of those was TRUE IN THE SHIPPED FILE until 2026-09-21 and a
#   green suite said nothing about any of them

THE THREE DEFECTS THIS SUITE WAS BUILT FOR WERE ALL FOUND BY READING, NOT BY A
TEST, and the file had no test at all. That is the situation a negative control
exists for: a suite written in the same hour as the fix has never refused
anything, and "it passes" is not evidence that it would notice the fix being
undone.

SEVEN MUTATIONS, AND MUTATION 1 IS THE ORIGINAL DEFECT RESTORED EXACTLY -- the
`&& !d.error` that let four api/sd-data.js refusal shapes reach a biller
wearing a "Record this determination" button, one of which (502 `upstream()`,
whose body carries no code at all) would write a permanent "not routed" row
into an append-only table with no delete grant.

MUTATIONS 2 AND 7 ARE THE ONES THAT READ AS CORRECT. 2 removes the consumer's
own no-code guard while leaving the producer's stamping in place, so the
end-to-end arms all still pass and only the "defends itself if the producer
regresses" arm can see it -- which is the arm that exists because the producer
WAS the thing that regressed. 7 flips an absent verdict from UNKNOWN to WROTE,
a one-word change that reads as a harmless default and is a success claimed
from no evidence.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                      # noqa: E402

SUITE = os.path.join('tests', 'sairncare_route_record.js')
APP = 'sairncare.html'

MUTATIONS = [
    ("1. THE ORIGINAL DEFECT RESTORED: alfRoute() stops stamping HTTP_<status> "
     "on a non-200 that carries an error body, so NO_SESSION, FORBIDDEN, "
     "NOT_PROVISIONED and upstream()'s codeless 502 reach the biller wearing "
     "the engine's own clothes",
     APP,
     "      if(!r.ok)return {ok:false,error:{code:'HTTP_'+r.status,",
     "      if(!r.ok&&!d.error)return {ok:false,error:{code:'HTTP_'+r.status,"),

    ("2. THE ONE THAT READS AS CORRECT: the consumer's own no-code guard is "
     "removed while the producer still stamps, so every end-to-end arm keeps "
     "passing and only the regression guard can see it",
     APP,
     "    if(!code)return false;\n    if(code==='NETWORK'",
     "    if(code==='NETWORK'"),

    ("3. the recordable test stops looking at whether there is an error at "
     "all and goes back to reading a bare code off any body",
     APP,
     "  if(res.ok===false||res.error){\n    var code=(res.error&&res.error.code)||'';",
     "  if(true){\n    var code=(res.error&&res.error.code)||'';"),

    ("4. WROTE/MISSED/UNKNOWN collapses to two answers: a 5xx is reported as "
     "MISSED, so a store error on a write the server may have taken is "
     "reported as nothing saved",
     APP,
     "        alfNote(resource,r.status>=500?'UNKNOWN':'MISSED',",
     "        alfNote(resource,'MISSED',"),

    ("5. THE TIMEOUT GOES BACK TO LYING: the transport catch reports MISSED, "
     "so a 15s abort on a write that landed tells the biller nothing was "
     "saved and invites the retry that duplicates the row",
     APP,
     "    alfNote(resource,'UNKNOWN',{code:timedOut?'TIMEOUT':'NETWORK',",
     "    alfNote(resource,'MISSED',{code:timedOut?'TIMEOUT':'NETWORK',"),

    ("6. an UNKNOWN write re-offers the retry button -- the wording still says "
     "UNKNOWN, so the message is right and the only control that can do harm "
     "is handed back anyway",
     APP,
     "      if(btn){btn.disabled=true;btn.textContent='NOT CONFIRMED — check the trail';}",
     "      if(btn){btn.disabled=false;btn.textContent='NOT CONFIRMED — check the trail';}"),

    ("7. THE SECOND ONE THAT READS AS CORRECT: a resource nobody has asked "
     "anything defaults to WROTE instead of UNKNOWN -- one word, and it is a "
     "success claimed from no evidence",
     APP,
     "  return (e&&e.verdict)||'UNKNOWN';",
     "  return (e&&e.verdict)||'WROTE';"),

    ("8. provisioned is read by truthiness rather than ===false, so every "
     "branch that does not report the flag is announced as an unprovisioned "
     "table and the banner stops meaning anything",
     APP,
     "  return !!e&&e.provisioned===false;",
     "  return !!e&&!e.provisioned;"),

    ("9. the success path stops recording the flag at all, so an absent table "
     "reads as a genuinely empty trail again -- the defect this half was "
     "built for",
     APP,
     "      alfNote(resource,'WROTE',{status:r.status,provisioned:d.provisioned});",
     "      alfNote(resource,'WROTE',{status:r.status});"),

    ("10. the helper stays correct and THE TRAIL STOPS ASKING IT -- an "
     "unprovisioned table falls through to 'No routing determination has been "
     "recorded yet', which is the original defect with a working helper "
     "sitting beside it unused",
     APP,
     "    if(alfNotProvisioned('alf_claim_routes')){",
     "    if(false&&alfNotProvisioned('alf_claim_routes')){"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='alf_claim_routes -- the suite must refuse a file that records a '
              'determination the engine never made, or claims a write it never '
              'confirmed',
        # BOTH are staged. The worktree is at HEAD and neither the fix nor the
        # suite is committed when this first runs, so without staging the
        # baseline would be red for a reason that has nothing to do with any
        # mutation below.
        stage=(SUITE, APP)))
