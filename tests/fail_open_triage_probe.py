"""api/fail-open-triage-2026-09-04.test.js must go RED when a refusal is removed.

Run: python tests/fail_open_triage_probe.py

WHY THIS SUITE IS THE ONE TO CONTROL. It is the only thing standing between
twelve fixed fail-open reads and their quiet return, and its own header explains
why the checker beside it cannot do the job: tools/fail_open_check.py matches
the SHAPE `x.ok ? await x.json() : []`, and DELETING a guard leaves no shape to
match. That was measured, not assumed -- three fixes were reverted one at a time
and the count never moved. So the checker guards the shape coming back and this
suite guards the refusals being taken out, and if the suite does not bite there
is nothing on that side at all.

EVERY ONE OF THE TWELVE REPLACED A FALSE STATEMENT rather than a missing error:
a patient's valid complaint link reported as "not valid", a family member told
there are no visits, a customer reported as having no consent on record. That is
what a mutation here restores.

ONE PROPERTY PER MUTATION, and the last two are the structural arms rather than
the case list -- the arms that would still pass if every individual guard were
present and the file had quietly grown a new fail-open beside them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'fail-open-triage-2026-09-04.test.js')
THREAD = os.path.join('api', 'sairndental', 'public-complaint-thread.js')
ALERTS = os.path.join('api', 'alf-alerts.js')
ACCT = os.path.join('api', 'accounting.js')
DATA = os.path.join('api', 'sd-data.js')
ACCEPTED = os.path.join('tools', 'fail_open_accepted.json')

MUTATIONS = [
    # THE PATIENT-FACING ONE. `return null` here becomes a 404 telling somebody
    # holding a perfectly good link that it is not valid.
    ("1. the complaint-link read goes back to collapsing an upstream failure "
     "into 'this link is not valid'",
     THREAD,
     "    const e = new Error('dnt_complaints token lookup read failed: HTTP ' + r.status);",
     "    const e = new Error('lookup failed');"),
    ("2. the facility policy read stops distinguishing UNREADABLE from absent, "
     "so a facility is told to set a window it already set",
     ALERTS, "  if (!r.ok) return 'UNREADABLE';", "  if (!r.ok) return null;"),
    # THE ORDERING ARM. A provisioned check running first answers "the tables
    # are not set up" for a read that merely failed -- swapping one false
    # reason for another, which is what the code's own comment says.
    ("3. the accounting provisioned check runs BEFORE the unreadable check, so "
     "an unread state is reported as an unconfigured one",
     ACCT,
     "      if (st.unreadable) {\n"
     "        console.error('accounting: consent/connection state unreadable --', st.detail);\n"
     "        res.status(502).json({ error: { code: 'STATE_UNREADABLE', message: 'Could not read the consent and connection records, so no connection status is being reported. This is not a statement that consent is absent.' } });\n"
     "        return;\n"
     "      }\n"
     "      if (!st.provisioned) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The accounting connector tables are not set up.' } }); return; }",
     "      if (!st.provisioned) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The accounting connector tables are not set up.' } }); return; }\n"
     "      if (st.unreadable) {\n"
     "        console.error('accounting: consent/connection state unreadable --', st.detail);\n"
     "        res.status(502).json({ error: { code: 'STATE_UNREADABLE', message: 'Could not read the consent and connection records, so no connection status is being reported. This is not a statement that consent is absent.' } });\n"
     "        return;\n"
     "      }"),
    # WIDENED TO THE COMMENT ABOVE IT. The message appears FOUR times in
    # sd-data.js -- two call sites, each guarding `!jr.ok` and `!Array.isArray`
    # -- and the narrow anchor reported ANCHOR-2. An ambiguous anchor plants in
    # whichever came first and then asserts something about a line nobody chose.
    ("4. the WIP read stops saying nothing was computed, so a partial job read "
     "publishes a figure",
     DATA,
     "// as api/ledger.js's balanced-and-empty trial balance.\n"
     "          if (!jr.ok) { res.status(502).json({ error: { code: 'READ_FAILED', message: 'Could not read jobs, so no WIP figures were computed.' } }); return; }",
     "// as api/ledger.js's balanced-and-empty trial balance.\n"
     "          if (!jr.ok) { res.status(502).json({ error: { code: 'READ_FAILED', message: 'Could not read jobs.' } }); return; }"),
    # ── RE-AIMED, AND THE REASON IS A REAL LIMIT OF THE SUITE ──────────────
    # This arm was first pointed at alf-alerts' SWEEP_READ_FAILED and reported
    # ANCHOR-4. Widening it would not have helped: the suite's arm asserts the
    # regex EXISTS SOMEWHERE IN THE FILE, so removing one of four occurrences
    # leaves it green and removing all four is not a single-anchor mutation.
    # That is worth naming rather than working around -- an existence arm over
    # a repeated marker cannot tell four call sites from one, so the suite
    # genuinely does not hold each of those four individually. Re-aimed at a
    # guard whose message is unique, where the arm means what it looks like.
    ("5. the family-visit read stops saying an unread schedule is not an empty "
     "one, so a relative is told there are no visits",
     os.path.join('api', 'sen-portal.js'),
     "        console.error('sen-portal: sen_visits read failed, HTTP', visitsR.status);\n"
     "        res.status(502).json({ error: { code: 'READ_FAILED', message: 'Could not load the visit schedule just now. This does not mean there are no visits -- please try again shortly.' } });",
     "        console.error('sen-portal: sen_visits read failed, HTTP', visitsR.status);\n"
     "        res.status(502).json({ error: { code: 'READ_FAILED', message: 'Could not load the visit schedule just now.' } });"),
    # ── THE STRUCTURAL ARMS ────────────────────────────────────────────────
    # Every mutation above removes ONE named guard. These two would still pass
    # with all twelve present: a NEW fail-open beside them, and an acceptance
    # nobody justified.
    ("6. a fixed site grows a NEW fail-open ternary beside its intact guards",
     THREAD, "  const rows = await r.json();",
     "  const zzRows = r.ok ? await r.json() : [];\n  const rows = await r.json();"),
    # ANCHORED ON ONE ENTRY'S OWN FIELD, not on the field NAME -- `"reason":`
    # occurs eleven times and reported ANCHOR-11. Removing the `file` key drops
    # the entry out of the arm's population entirely, which is the shape the
    # old `>= 6` floor could absorb five times over.
    ("7. an accepted fail-open drops out of the acceptance list, so a decision "
     "to keep a fail-open stops being visible",
     ACCEPTED, '"file": "api/sd-webauthn.js"', '"zz_file": "api/sd-webauthn.js"'),
]

if __name__ == '__main__':
    sys.exit(run_probe(SUITE, MUTATIONS,
                       title='negative control -- api/fail-open-triage-2026-09-04.test.js '
                             'must refuse each way a fixed fail-open can come back'))
