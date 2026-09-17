"""tests/exec_role_gate.js must REFUSE -- the panel holds SAIRN's own books.

Run: python tests/exec_role_gate_probe.py

THE EXECUTIVE SUITE'S ADVISOR PROMPTS CARRY SAIRN TECH LLC'S OWN CHART OF
ACCOUNTS, StoneDesk's price book and the patent deadline. Before 2026-09-02 a
PAYING CUSTOMER'S SALES REP COULD OPEN IT, through four doors at once:

  1. `#sb-executive` carried no gating class, and `.admin-only` only ever
     covered `.nav-btn`, never the sidebar's `.sb-btn`;
  2. showPanel() had no role check on any panel;
  3. applyExecRole() read the `sd_exec_role` localStorage preference BEFORE
     checking any role -- and localStorage is per-origin and PERMANENT while a
     session role is not, so one owner setting it once granted is-exec to every
     later user of that browser;
  4. setExecRoleAndClose() was a global with no check at all, and it WRITES the
     preference that (3) then trusts.

THE THIRD AND FOURTH ARE THE ONES WORTH A CONTROL. A stale localStorage
preference is not a bug you can see by reading the gate: the gate is present,
the check is right there, and it runs in the wrong ORDER. And the second door
writes the state the first door believes -- a pair where fixing either one alone
leaves the exposure open.

The mutations put each door back:

  * the stored-preference branch runs BEFORE the privilege check again, which is
    defect 3 verbatim;
  * the stale preference is IGNORED rather than CLEARED, so the next owner
    session re-grants it -- the quieter half, and the suite has a separate arm
    for it because "refused once" is not "removed";
  * the writer stops checking, re-opening door 4 while door 3 stays shut;
  * the writer persists the preference BEFORE it refuses, so a refused sales
    rep leaves behind the state the next load believes. The first version of
    this mutation merely REORDERED the three lines after the guard, which is
    an EQUIVALENT MUTANT -- everything after a `return` guard is already
    unreachable to a refused caller, and reordering unreachable-to-them code
    changes nothing. The write had to move ABOVE the guard to express the
    hazard at all;
  * applying an unprivileged role stops STRIPPING an is-exec left from before,
    so a downgrade within one browser session keeps the panel open.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'exec_role_gate.js')
APP = 'stonedesk.html'

MUTATIONS = [
    ("1. DEFECT 3 VERBATIM -- the privilege check stops running first, so a "
     "stored `sd_exec_role` from any previous owner of that BROWSER grants "
     "is-exec to whoever is logged in now. localStorage is per-origin and "
     "permanent; the session role is not",
     APP,
     "  if(!sdExecPrivileged()){\n    document.body.classList.remove('is-exec');\n"
     "    sdExecRole='';\n    try{ localStorage.removeItem('sd_exec_role'); }catch(e){}\n"
     "    return;\n  }",
     "  if(false){\n    return;\n  }"),

    ("2. the stale preference is IGNORED rather than CLEARED. The sales rep is "
     "refused, and the state that granted it survives for the next session to "
     "find -- which is why 'refused once' and 'removed' are separate arms",
     APP,
     "    try{ localStorage.removeItem('sd_exec_role'); }catch(e){}",
     "    try{ /* left in place */ }catch(e){}"),

    ("3. DOOR 4 RE-OPENS while door 3 stays shut. setExecRoleAndClose() is a "
     "global callable from anywhere and it WRITES the preference applyExecRole() "
     "trusts -- so an unchecked writer defeats a correct reader",
     APP,
     "  if(!sdExecPrivileged()){\n    var pk=document.getElementById('exec-role-picker');\n"
     "    if(pk) pk.remove();\n    return;\n  }",
     "  if(false){\n    return;\n  }"),

    ("4. the writer REFUSES but still persists. It returns without granting, and "
     "leaves `sd_exec_role` set for the next load to believe -- a refusal that "
     "writes the state it refused is worse than no refusal, because it looks "
     "like one",
     APP,
     "function setExecRoleAndClose(role){",
     "function setExecRoleAndClose(role){\n  stRaw('sd_exec_role',role);"),

    ("5. applying an UNPRIVILEGED role stops stripping an is-exec left over from "
     "before, so a role change inside one browser session leaves the panel open "
     "-- the class is the thing the UI actually reads",
     APP,
     "    document.body.classList.remove('is-exec');\n    sdExecRole='';",
     "    sdExecRole='';"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title="the Executive Suite gate -- the suite must refuse each of the "
              "four doors a sales rep walked through"))
