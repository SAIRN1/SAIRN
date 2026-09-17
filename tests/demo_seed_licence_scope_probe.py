"""tests/demo_seed_licence_scope.js must refuse a paying customer being shown
invented figures as its own business.

Run: python tests/demo_seed_licence_scope_probe.py

THIRTY-TWO SEED SITES RENDERED FABRICATED NUMBERS TO ANYBODY WHOSE ACCOUNT
HAPPENED TO LOOK UNTOUCHED. Not a data-loss defect -- thirty-one of the
thirty-two mask nothing -- but a REAL PAYING CUSTOMER saw:

  sd_ap         open payables, due-this-week, OVERDUE and MTD-paid, plus a full
                aging table, off six invented bills DATED 2024
  sd_equipment  ~$471,000 of equipment value
  sd_bids       ~$293,000 of bid value

presented as its own business. The decision was deliberately NOT a blanket
delete -- the demo account has to keep looking like a populated shop for sales
use -- so the seeds render for SD-PINNACLE-2026 and every other licence gets the
honest empty state.

ONE GATE REACHES ALL THIRTY-TWO, which is the right call in a 2MB file where
rewriting 59 call sites is the bulk find-replace the syntax rule forbids. THE
COST IS THAT ONE FUNCTION NOW CARRIES TWO MEANINGS: sdDemoCleared() is the gate,
sdDemoClearedByUser() is the original "did the user press Clear Demo Data", and
the second exists for exactly one caller. A single edit to the wrong one of
those two changes what thirty-two sites do.

EVERY MUTATION BELOW IS INVISIBLE TO A DEMO ACCOUNT, which is the only account
anybody demonstrates with:

  * the comparison stops normalising case, so a licence key entered in the
    customer's own capitalisation stops matching and a demo shop goes empty --
    the failure that looks like broken software rather than a leak;
  * it stops trimming, so one trailing space does the same;
  * the gate loses its `!sdIsDemoLicense()` half, which restores the defect
    verbatim: thirty-two sites showing $471,000 of somebody else's equipment;
  * an unlicensed install is treated as the demo licence, which is the state
    every fresh browser is in;
  * the Admin checkbox path starts reporting the GATE rather than the user's own
    action, so the box reads "cleared" for every non-demo customer who never
    pressed it -- the one caller sdDemoClearedByUser() exists for.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'demo_seed_licence_scope.js')
APP = 'stonedesk.html'

MUTATIONS = [
    ("1. the comparison stops NORMALISING CASE. A demo licence entered as "
     "sd-pinnacle-2026 stops matching, the demo shop goes empty, and it reads "
     "as broken software rather than as a gate -- so the repair somebody "
     "reaches for is widening the gate",
     APP,
     "    return String(k||'').trim().toUpperCase()===SD_DEMO_LICENSE;",
     "    return String(k||'').trim()===SD_DEMO_LICENSE;"),

    ("2. it stops TRIMMING, so one trailing space from a paste does the same "
     "thing -- and a key with invisible whitespace is the hardest kind of "
     "not-matching to diagnose from a screenshot",
     APP,
     "    return String(k||'').trim().toUpperCase()===SD_DEMO_LICENSE;",
     "    return String(k||'').toUpperCase()===SD_DEMO_LICENSE;"),

    ("3. THE DEFECT VERBATIM. The gate loses its `!sdIsDemoLicense()` half and "
     "becomes the old user-action-only check, so all thirty-two seed sites "
     "render invented payables, $471,000 of equipment and $293,000 of bids to "
     "every paying customer whose account looks untouched",
     APP,
     "function sdDemoCleared(){ return sdDemoClearedByUser()||!sdIsDemoLicense(); }",
     "function sdDemoCleared(){ return sdDemoClearedByUser(); }"),

    ("4. AN UNLICENSED INSTALL IS TREATED AS THE DEMO LICENCE -- which is the "
     "state every fresh browser is in, before anybody has typed anything. The "
     "catch returning true reads as a safe default and is the widest one",
     APP,
     "  }catch(e){ return false; }\n}\nwindow.sdIsDemoLicense=sdIsDemoLicense;",
     "  }catch(e){ return true; }\n}\nwindow.sdIsDemoLicense=sdIsDemoLicense;"),

    ("5. the ADMIN CHECKBOX starts reporting the GATE rather than the user's own "
     "action, so it reads 'cleared' for every non-demo customer who never "
     "pressed it. sdDemoClearedByUser() exists for exactly one caller, and this "
     "is the edit that silently removes the distinction",
     APP,
     "function sdDemoClearedByUser(){try{return localStorage.getItem('sd_demo_cleared')==='1';}catch(e){return false;}}",
     "function sdDemoClearedByUser(){try{return localStorage.getItem('sd_demo_cleared')==='1'||!sdIsDemoLicense();}catch(e){return false;}}"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='the demo-seed licence gate -- the suite must refuse a paying '
              'customer being shown invented figures as its own business'))
