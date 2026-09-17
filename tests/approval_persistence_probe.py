"""tests/approval_persistence.js must refuse a $0 signature and a promise the app
cannot keep.

Run: python tests/approval_persistence_probe.py

THE DOCUMENT PROVING A CUSTOMER AGREED TO A PRICE. Three defects in one flow:

  1. sd_approvals was written to localStorage and READ BACK FROM NOWHERE in the
     file. One cache clear destroyed the only record that a customer had agreed
     to anything.
  2. The total was parsed out of `#est-total.textContent`. With no quote loaded
     that element reads an EM-DASH, which parses to NaN and then to ZERO -- so a
     customer could sign a $0 agreement and it saved silently.
  3. The confirmation said "Your project is reserved" while NOTHING was
     reserved: no slab, no schedule slot, no install date.

The second is the one worth the most care, because every step of it is
plausible: reading a total off the screen is what a person would do, an em-dash
is what an empty total looks like, and `Number('\\u2014')` is NaN rather than a
throw. There is no error anywhere -- a signed agreement for nothing.

THE SUITE IS STRUCTURAL: it reads stonedesk.html rather than driving the flow,
which is the right call for a 2MB single file and is also the shape with the most
ways to pass while testing nothing. Every mutation below leaves the feature
working and removes one guarantee:

  * the total goes back to the rendered element, which is defect 2 verbatim;
  * the positive-total refusal goes, so NaN or zero saves silently;
  * the refusal stops saying nothing was signed, which leaves the customer to
    guess what happened to an agreement they just signed;
  * "Your project is reserved" comes back -- a promise of a slab, a slot and a
    date, none of which exist;
  * the approvals list stops loading on login, so the record is invisible until
    somebody signs another one;
  * a LOCAL-ONLY row is dropped by the server merge, which is precisely the row
    nothing else in the world has.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'approval_persistence.js')
APP = 'stonedesk.html'

MUTATIONS = [
    ("1. DEFECT 2 VERBATIM -- the total goes back to being read off the rendered "
     "element. With no quote loaded that reads an em-dash, Number() gives NaN, "
     "and a customer signs a $0 agreement with no error anywhere",
     APP,
     "typeof lastCalc !== 'undefined' && lastCalc && Number(lastCalc.total) > 0",
     "true"),

    ("2. the POSITIVE-TOTAL REFUSAL goes, so a zero or NaN total saves silently. "
     "The signature, the name and the date are all captured correctly -- only "
     "the amount is nothing",
     APP,
     "  if (!(totalAmt > 0)) {",
     "  if (false) {"),

    ("3. the refusal stops SAYING NOTHING WAS SIGNED. It still refuses, so no "
     "bad record is written, and the customer is left to guess what happened to "
     "an agreement they just put their name to",
     APP,
     "Nothing was recorded, and nothing was signed",
     "Please try again"),

    ("4. \"Your project is reserved\" COMES BACK -- a promise of a slab, a "
     "schedule slot and an install date, none of which exist. The app telling a "
     "customer something it has not done is the defect this file is named for",
     APP,
     "Your approval is recorded",
     "Your project is reserved."),

    ("5. the approvals list stops LOADING ON LOGIN, so a signed approval is "
     "invisible until somebody happens to sign another one. The record exists "
     "and nothing shows it, which is indistinguishable from it not existing",
     APP,
     "'loadWeather','sdApprovalsLoad'",
     "'loadWeather'"),

    ("6. a LOCAL-ONLY row is dropped by the server merge. It is precisely the "
     "row nothing else in the world has -- the one that never reached the "
     "server -- so the merge deletes the only copy of the document proving a "
     "customer agreed",
     APP,
     "_sdApprovals.forEach(function(a){ if(a&&a.id) byId[a.id]=a; })",
     "_sdApprovals.forEach(function(a){ if(a&&a.id&&byId[a.id]) byId[a.id]=a; })"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='the signed approval -- the suite must refuse a $0 agreement and a '
              'reservation the app never made'))
