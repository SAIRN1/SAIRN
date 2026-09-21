"""tests/sairnlaw_billable_rate.js must REFUSE, not merely agree.

Run: python tests/run_sairnlaw_billable_rate_sabotage_probe.py

# REQUIREMENT: the suite guarding the billable-rate gate must go RED when the
#   zero-rate hour is allowed back through either layer, when the refusal
#   widens onto no-charge entries it has no business judging, or when the rate
#   that is CHECKED stops being the rate that is STORED -- because a green
#   suite over a restored defect is the only outcome that is worse than no
#   suite at all, and this defect's whole signature is that nothing complains

A GREEN SUITE IS NOT A GUARD. `tools/sabotage_control_check.py` measures how
many suites on this platform have ever been seen to refuse anything, and the
answer has been embarrassing twice. tests/sairnlaw_billable_rate.js was
written in the same hour as the fix it covers, which is exactly the case where
"it passes" proves the least -- the fix and the test were authored by one
session, from one reading, and share its blind spot.

── WHAT IS PLANTED, AND WHY EACH ONE IS A DEFECT SOMEBODY WOULD PLAUSIBLY WRITE
  1. THE ORIGINAL DEFECT, RESTORED EXACTLY. The server-side rate check is
     removed outright -- which is the state of the file up to 2026-09-21 and
     the state anybody "simplifying" the validator would produce.
  2. `|| 0` COMES BACK IN THE BROWSER. `Number($('ttrate').value)||0` is the
     line that produced the defect in the first place: it is the natural way
     to write it, it reads as defensive, and it silently converts a blank box
     into a zero-fee billable hour.
  3. THE REFUSAL WIDENS ONTO NO-CHARGE WORK. Dropping the `r.billable` guard
     looks like a stricter gate and is a different defect: a firm can no
     longer record a no-charge hour at all, and a refusal that over-reaches is
     the failure mode the review of this module's billing-code check spent
     most of its length warning about.
  4. THE TYPE CHECK GOES COERCIVE. `Number(r.rate) > 0` accepts the STRING
     '350' and stores a string in a column an invoice MULTIPLIES -- the
     validate-one-thing/store-another seam that FINDING 1 of the same review
     recorded against billing_code.trim().
  5. ZERO SLIPS THROUGH THE COMPARISON. `< 0` instead of `<= 0` is a one
     character edit that refuses the negative rate nobody enters and admits
     the zero rate everybody does.

The suite is STAGED into the worktree rather than taken from HEAD, along with
the two files it exercises, because the fix and the suite are not committed
when this first runs -- and a baseline that is red for that reason is a
baseline that proves nothing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairnlaw_billable_rate.js')
MODULE = os.path.join('api', '_lib', 'law-timeentry.js')
APP = 'sairnlaw.html'

MUTATIONS = [
    ("1. THE ORIGINAL DEFECT, RESTORED -- the server stops checking the rate "
     "at all, which is the state of this file up to 2026-09-21",
     MODULE,
     "  if (r.billable) {\n"
     "    if (typeof r.rate !== 'number' || !isFinite(r.rate)) {",
     "  if (false) {\n"
     "    if (typeof r.rate !== 'number' || !isFinite(r.rate)) {"),

    ("2. `|| 0` COMES BACK IN THE BROWSER -- the exact line that produced the "
     "defect, and the natural way somebody would rewrite it",
     APP,
     "var billable=$('ttbillable').checked,rate=Number($('ttrate').value)||0;\n"
     "  if(billable&&!(rate>0)){",
     "var billable=$('ttbillable').checked,rate=Number($('ttrate').value)||0;\n"
     "  if(false){"),

    ("3. THE REFUSAL WIDENS ONTO NO-CHARGE WORK -- looks stricter, and stops a "
     "firm recording a no-charge hour at all",
     MODULE,
     "  if (r.billable) {\n"
     "    if (typeof r.rate !== 'number' || !isFinite(r.rate)) {",
     "  if (true) {\n"
     "    if (typeof r.rate !== 'number' || !isFinite(r.rate)) {"),

    ("4. THE TYPE CHECK GOES COERCIVE -- the string '350' is accepted and a "
     "string is stored in a column an invoice multiplies",
     MODULE,
     "    if (typeof r.rate !== 'number' || !isFinite(r.rate)) {",
     "    if (!isFinite(Number(r.rate))) {"),

    ("5. ZERO SLIPS THROUGH THE COMPARISON -- `< 0` refuses the negative rate "
     "nobody enters and admits the zero rate everybody does",
     MODULE,
     "    if (r.rate <= 0) {",
     "    if (r.rate < 0) {"),

    # ── THE OTHER FACTOR OF THE SAME $0.00 LINE, added 2026-09-21 ──────────
    # hours 0 and rate 0 produce the IDENTICAL invoice line. The arms that
    # cover it were an INVERSION of an arm that used to pin the gap as open,
    # so these three matter more than usual: a pin that is flipped and then
    # left uncontrolled is how a closed gap quietly reopens.
    ("6. THE HOURS CHECK IS REMOVED -- the state of this file between the rate "
     "fix and today, and the state any 'simplify the validator' edit produces",
     MODULE,
     "    if (typeof r.hours !== 'number' || !isFinite(r.hours)) {",
     "    if (false) {"),

    ("7. ZERO HOURS SLIPS THROUGH -- `< 0` for `<= 0`, the same one-character "
     "edit as arm 5, on the other factor",
     MODULE,
     "    if (r.hours <= 0) {",
     "    if (r.hours < 0) {"),

    ("8. THE HOURS REFUSAL WIDENS ONTO NO-CHARGE WORK -- a zero-hour "
     "no-charge row cannot reach an invoice, so refusing it refuses work the "
     "app has no reason to stop",
     MODULE,
     "  if (r.billable) {\n"
     "    if (typeof r.rate !== 'number' || !isFinite(r.rate)) {",
     "  if (r.billable||r.hours===0) {\n"
     "    if (typeof r.rate !== 'number' || !isFinite(r.rate)) {"),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='a BILLABLE hour with no rate must be refused at both ends -- and a '
          'NO-CHARGE hour must not be',
    stage=(MODULE, APP),
))
