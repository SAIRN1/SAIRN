"""api/_lib/law-trust-reconcile.test.js must refuse a leg that cannot fail.

Run: python tests/law_trust_reconcile_probe.py

THIS FILE RECONCILES ATTORNEY IOLTA CLIENT TRUST MONEY -- the one balance a bar
association audits -- and it was written to replace a check whose commit is
literally named "the leg the existing check was asked about could not fail".

THE REPLACEMENT HAD THE SAME PROPERTY. `allocation_vs_ledger` was documented as
one that "CAN genuinely fail: a row the attribution pass loses shows up here as
a difference". Driven, it does not: both traversals skip on the same two
predicates -- isVoided(), and cents() returning null -- and differ only in which
bucket they add to, so the two sums are the same arithmetic over the same
survivors. An unreadable amount, a missing client_id, a non-string client_id, a
voided row, and all of them mixed: agrees:true every time.

So the leg is now LABELLED structural and EXCLUDED from legs_compared, and the
falsifiable half it was meant to be is a ROW CONSERVATION identity -- every row
is either voided or in exactly one client bucket -- which counts rows rather
than money and therefore CAN see a row both money passes dropped.

The mutations are the ways that repair comes undone:

  * a skip is added to ONE traversal, which is exactly the change leg 1 was
    supposed to catch and could not, and which conservation does catch;
  * `structural` is dropped, so the leg that cannot disagree is counted among
    the compared ones again and a reconciliation with no external leg reports
    as having compared something;
  * the bank leg's as-of boundary is removed, comparing an all-time ledger
    total against a point-in-time bank balance -- the original defect this
    file was built to fix;
  * the negative-client signal is dropped, which is the per-client gate having
    failed rather than a reconciliation difference.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', '_lib', 'law-trust-reconcile.test.js')
LIB = os.path.join('api', '_lib', 'law-trust-reconcile.js')

MUTATIONS = [
    ("1. A SKIP IS ADDED TO ONE TRAVERSAL ONLY -- the attribution pass drops "
     "disbursements and the ledger pass keeps them. This is the exact change "
     "allocation_vs_ledger was documented as catching; it does catch this one, "
     "because the predicates have genuinely diverged",
     LIB,
     "    b.rows += 1;",
     "    if (String((row && row.type) || '') === 'Disbursement') return;\n    b.rows += 1;"),

    # ── MUTATION 2 WAS WITHDRAWN, AND THE REASON IS WORTH THE SPACE ────────
    # "the conservation identity stops forcing DISAGREES" -- removing
    # `|| !conservation.holds` from the status line -- is an EQUIVALENT MUTANT
    # with respect to this suite, and the reasoning is not obvious.
    #
    # The term only changes an answer when the identity is BROKEN, and no
    # INPUT can break it: it is an invariant over the code, not over the data.
    # The only thing that breaks it is a source mutation -- mutation 1 -- and
    # when that is applied the suite fails on the conservation arm itself,
    # before the status term is ever reached. So the two cannot be separated
    # from outside.
    #
    # IT IS STILL WORTH HAVING. The endpoint returns the whole object, and a
    # caller reading `status` alone -- a UI badge, a future gate -- would see
    # AGREES while rows were vanishing between the passes. That is a real
    # caller-facing guarantee with no driveable arm, which is a different thing
    # from a guarantee nobody needs, and it is recorded here rather than
    # counted as a caught mutation.

    ("3. `structural` is dropped from leg 1, so the leg that CANNOT disagree "
     "is counted among the compared ones again -- and a reconciliation with no "
     "bank statement and no device total reports as having compared something",
     LIB,
     "      structural: true,",
     ""),

    ("4. the BANK LEG loses its as-of boundary and compares an all-time ledger "
     "total against a point-in-time bank balance. That is the original defect "
     "this file was built to fix, and the two quantities are not the same thing",
     # ── RE-ANCHORED 2026-09-22, AND THE ARM WAS RED, NOT SILENT ──────────
     # The old anchor was the two-line form
     #     if (d <= latest.date) asOfCents += signed;
     #     else afterStatementCents += signed;
     # which stopped existing when the outstanding-item clearance tracking
     # landed inside that branch on 2026-09-18. The mutation then planted
     # NOTHING and the harness reported ANCHOR-0 -- red, which is the harness
     # working, and red for a reason with nothing to do with the property the
     # arm guards, which is how a suite teaches people to expect one failure.
     #
     # Anchored on the BOUNDARY ITSELF now rather than on the two statements
     # that happened to sit either side of it. Neutering the condition removes
     # the as-of comparison and leaves every other behaviour in the branch --
     # including the clearance tracking -- untouched, which is a cleaner
     # expression of the defect than deleting the else ever was.
     LIB,
     "      if (d <= latest.date) {",
     "      if (true) {"),

    ("5. the NEGATIVE-CLIENT signal is dropped. A client whose allocation is "
     "negative is one client's money spent on another -- the per-client "
     "disbursement gate having failed, not a reconciliation difference, which "
     "is why it is named separately and cannot be read as rounding",
     LIB,
     "    negative_clients: clients.filter((c) => c.cents < 0).map((c) => c.client_id),",
     "    negative_clients: [],"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='the IOLTA trust reconciliation -- the suite must refuse a leg '
              'that cannot fail and a row that goes missing',
        # The library and the suite are both being edited; a worktree at HEAD
        # would test the committed pair. Third-and-fourth instance of f4397982
        # this session, so it is set up front rather than after a red baseline.
        stage=[LIB, SUITE]))
