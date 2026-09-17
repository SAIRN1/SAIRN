"""The negative control for tests/sairnfreedom_server_backup.js.

    python tests/sairnfreedom_server_backup_probe.py

WHY THIS SUITE. `tools/suite_control_triage.py` ranks the suites nobody has
tried to break by the criticality tier of the resources they name. This one
names `sf_ledger`, `sf_disbursements`, `sf_accounts`, `sf_gaming_expenses` and
`sf_members` -- and the registry's own header says why the app got a server at
all: *"membership, the ledger, gaming sessions, gaming expenses and CHARITABLE
DISBURSEMENTS -- the ORC 2915 reportable side of a fraternal post's gaming --
lived in one browser."* A statutory reporting obligation on a gaming post.

── WHAT KIND OF SUITE THIS IS, BECAUSE IT DECIDES THE MUTATIONS ────────────
It is a SOURCE-AGREEMENT suite, not a behavioural one. It says so itself: "no
live write is made from here." Three sides must agree -- the registry in
`api/_resources/sairnfreedom.js` names a resource, the client in
`sairnfreedom.html` decides to push it, and `sql/sairnfreedom_data_schema.sql`
has to have a table for it -- and the suite's stated hazard is that "TWO OF
THREE AGREEING IS EXACTLY HOW DRIFT HIDES."

So a mutation that breaks one side and leaves the other two is the right
sabotage, and a behavioural mutation would be testing a suite that does not
exist. Every mutation below breaks exactly one side.

── THE FIRST ONE IS THE CASE THE SUITE'S HEADER NAMES IN WORDS ─────────────
*"A registry that silently lost sf_disbursements would still pass a pairwise
count. It would not pass this."* Mutation 1 is that sentence made real. If it
survives, the suite's own headline claim is false.

── WHAT THIS CONTROL CANNOT SHOW ───────────────────────────────────────────
That the three sides are RIGHT -- only that the suite notices when they stop
agreeing. A resource registered, pushed and tabled under a wrong name agrees
with itself perfectly and is invisible to both the suite and this control.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairnfreedom_server_backup.js')
APP = 'sairnfreedom.html'
REG = os.path.join('api', '_resources', 'sairnfreedom.js')
SCHEMA = os.path.join('sql', 'sairnfreedom_data_schema.sql')

MUTATIONS = [
    ("1. THE REGISTRY SILENTLY LOSES sf_disbursements -- the ORC 2915 "
     "reportable side of the post's gaming, and the exact case this suite's "
     "header says a pairwise count would miss",
     REG,
     "    'sf_disbursements',\n",
     ""),

    ("2. THE CLIENT STOPS PUSHING sf_ledger -- the ledger is registered and "
     "tabled and never leaves the browser, which is a backup everyone believes "
     "exists",
     APP,
     "'sf_district_imports','sf_documents','sf_donations','sf_donor_awards',",
     "'sf_documents','sf_donations','sf_donor_awards',"),

    ("3. THE CLIENT PUSHES SOMETHING UNREGISTERED -- a name no registry or "
     "schema knows, which is the drift running the other way",
     APP,
     "  'sf_waivers','sf_youth_participants'\n",
     "  'sf_waivers','sf_youth_participants','sf_not_registered_anywhere'\n"),

    ("4. SF_SYNCED_ON IS HAND-LISTED INSTEAD OF DERIVED -- a second list is a "
     "fourth thing to drift, which is the suite's own wording",
     APP,
     "SF_SYNCED.forEach(function(k){ SF_SYNCED_ON[k]=true; });",
     "SF_SYNCED_ON['sf_ledger']=true;"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='negative control for tests/sairnfreedom_server_backup.js -- '
              'sf_ledger and sf_disbursements are ORC 2915 reportable'))
