"""api/sd-data-sb-void-role.test.js must go RED when the void gate is undone.

Run: python tests/sd_data_sb_void_role_probe.py

WHY THIS SUITE. It is Tier A -- sb_po and sb_recv are the two documents a bill
settles against, so a void is a money decision -- and the gate it pins is the
one that replaced a CLIENT CONSTANT. `SB_VOID_ROLES` lived in sairnbiz.html and
nowhere else, which stopped a staff account CLICKING the button and did nothing
to stop it POSTing the row. A suite covering the half that makes the decision
true is worth exactly as much as its ability to notice that half leaving, and
until now it had never been asked to notice anything.

Unlike a source-text suite, every arm here DRIVES the real handler against a
fake REST layer, so these mutations are behavioural: each one changes what the
endpoint does, not what it says about itself.

ONE PROPERTY PER MUTATION, and each is a shape the block's own comments argue
against in prose -- which is the point: prose is not a control.

  1. only SETTING a void stays privileged, so a staff account un-voids by
     posting the same id with the status removed. The comment calls this "a
     void anybody can undo is not a void"; nothing tested it;
  2. an unreadable stored row is treated as not-void, which is the gate quietly
     not running -- could-not-tell folded into a pass (PR 1.11);
  3. `staff` joins the privileged list, which is the decision itself reversed;
  4. the gate covers sb_po and forgets sb_recv, which is the fix-applied-where-
     the-finder-pointed shape: receipts are the other half of the same match;
  5. the NOT-PROVISIONED read becomes an error, so an app whose tables are not
     set up yet reports a fault instead of the honest answer the write gives;
  6. the gate stops being about the TRANSITION and fires on every voidable
     write, which locks staff out of raising a purchase order at all. This is
     the direction a one-way reading of "voids are privileged" produces, and
     the suite says in its header that it must fail here rather than silently.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-sb-void-role.test.js')
SRC = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. only SETTING a void stays privileged, so staff can UN-VOID by posting "
     "the row without its status",
     SRC,
     "          if (incomingVoid !== storedVoid\n"
     "              && SB_VOID_ROLES.indexOf(sbBizSession.role) === -1) {",
     "          if (incomingVoid\n"
     "              && SB_VOID_ROLES.indexOf(sbBizSession.role) === -1) {"),
    ("2. an UNREADABLE stored row is read as not-void, so the gate passes on a "
     "state it could not determine",
     SRC,
     "              res.status(503).json({ error: { code: 'VOID_STATE_UNREADABLE', message: "
     "'Could not read the stored ' + resource + ' row, so whether this write clears a void "
     "is unknown. The write was refused rather than allowed.' } });\n"
     "              return;",
     "              storedVoid = false;"),
    ("3. `staff` joins the privileged list, which is the decision reversed",
     SRC, "          const SB_VOID_ROLES = ['owner', 'manager'].filter(",
     "          const SB_VOID_ROLES = ['owner', 'manager', 'staff'].filter("),
    ("4. the gate covers sb_po and forgets sb_recv -- the other half of the "
     "same three-way match",
     SRC, "        const SB_VOIDABLE = { sb_po: 1, sb_recv: 1 };",
     "        const SB_VOIDABLE = { sb_po: 1 };"),
    ("5. the NOT-PROVISIONED stored read becomes an error, so an unprovisioned "
     "app reports a fault instead of the honest answer",
     SRC,
     "            if (cur.status === 404 || cur.status === 400) {\n"
     "              storedVoid = false;",
     "            if (cur.status === 404 || cur.status === 400) {\n"
     "              res.status(503).json({ error: { code: 'VOID_STATE_UNREADABLE', message: 'no row' } });\n"
     "              return;",
     ),
    # THE OTHER DIRECTION, and the one a suite about a refusal usually forgets.
    # A gate that refuses everything passes every arm that asserts a refusal.
    ("6. the gate fires on EVERY voidable write rather than on the transition, "
     "which locks staff out of raising a purchase order at all",
     SRC, "          if (incomingVoid !== storedVoid\n",
     "          if (true\n"),
]

if __name__ == '__main__':
    sys.exit(run_probe(SUITE, MUTATIONS,
                       title='negative control -- api/sd-data-sb-void-role.test.js '
                             'must refuse each way the void gate can be undone'))
