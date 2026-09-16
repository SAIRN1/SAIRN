"""api/sd-data-session-gate.test.js must REFUSE, and it was RED on main.

Run: python tests/session_gate_table_probe.py

SD_SESSION_GATED IS THE MECHANISM EVERY GATED RESOURCE ON sd-data DEPENDS ON.
The licence key is a bearer credential StoneDesk prints into a link the shop is
told to send customers; before this table it read the whole slab inventory, the
business profile (company, EIN, revenue range, owner) and the shop's AI
memories, and it could WRITE slabs. `locations` joined it on 2026-09-03 and
`law_trusttx` -- attorney IOLTA client trust money -- on 2026-09-16.

THE SUITE WAS FAILING ON origin/main FOR THE RIGHT REASON AND NOBODY FINISHED
IT. Its count arm said 9 pairs, the table held 11, and the arm's own message is
"add the new resource to this test and say why it is gated". It did its job;
the answer was never written down, so the suite sat red. A suite left red by its
own correct finding is a suite whose NEXT finding is read as noise -- and this
one sits beside the gate that protects trust money.

Fixed, and then measured. The mutations are the properties:

  * a resource leaves the table entirely -- the pre-gate state, restored in one
    line, for each of the three most valuable entries;
  * only ONE VERB is gated. This is the quiet half every time: a readable slab
    inventory or a readable trust ledger errors nowhere and looks like a
    working app, so the write-only and read-only holes are driven separately;
  * the refusal happens AFTER the database is already queried, so the refused
    request has still read the rows it refuses to return;
  * a resource is added to the table and driven by NOTHING. It is counted, it
    is gated, and no arm anywhere exercises it -- which from inside the suite
    is indistinguishable from coverage.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-session-gate.test.js')
API = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. law_trusttx leaves the table -- attorney IOLTA trust money back on the "
     "licence key alone, which is the state it shipped in until 2026-09-16",
     API,
     "      'law_trusttx': ['read', 'write']\n    };",
     "    };"),

    ("2. slabs leaves the table -- the whole inventory readable and WRITABLE by "
     "anyone holding the link the shop was told to send customers",
     API,
     "      'slabs':   ['read', 'write', 'reserve'],",
     ""),

    ("3. locations leaves the table. The GAP 7 branch describes itself as "
     "carrying \"the same licence-scoped gate as 'slabs'\" -- and slabs is in "
     "THIS table, so removing it here is how locations came to have no session "
     "requirement at all the first time",
     API,
     "      'locations': ['read', 'write'],",
     ""),

    ("4. only the WRITE of law_trusttx is gated. The quiet half: a readable "
     "trust ledger errors nowhere, returns 200, and looks like a working app",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'law_trusttx': ['write']"),

    ("5. only the READ of slabs is gated, so the licence key alone can still "
     "write and reserve",
     API,
     "      'slabs':   ['read', 'write', 'reserve'],",
     "      'slabs':   ['read'],"),

    ("6. the refusal stops being a refusal -- the gate computes its answer and "
     "does not return, so the request continues to the handler. The check is "
     "still right there in the file, which is exactly why it reads as present",
     API,
     "            message: 'A valid employee session is required — sign in first'\n"
     "          }\n        });\n        return;\n      }",
     "            message: 'A valid employee session is required — sign in first'\n"
     "          }\n        });\n      }"),

    # ── AND THE ARM ADDED 2026-09-16, WHICH THE OTHERS CANNOT REACH ─────────
    ("7. a resource is ADDED to the table and driven by nothing. It is counted, "
     "it is gated, and no arm anywhere exercises it -- which from inside the "
     "suite looks exactly like coverage. Only the driven-somewhere arm sees it",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'sd_payroll': ['read', 'write'],\n      'law_trusttx': ['read', 'write']"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SD_SESSION_GATED -- the suite must refuse a resource leaving the '
              'table, half of one leaving it, and a new one nothing drives',
        stage=[SUITE]))
