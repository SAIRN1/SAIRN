"""api/alf-append-only-fail-closed.test.js must REFUSE, not merely agree.

Run: python tests/alf_append_only_probe.py

TIER A, AND THE SUITE HAD NEVER BEEN DRIVEN. Measured 2026-09-15: 7 of 154
JavaScript suites on this platform have a negative control at all, and 67 of the
147 without one touch a Tier A resource. This suite guards four of them --
`alf_claim_routes`, `alf_incidents`, `alf_op_audits`, `alf_staff_credentials` --
and had never been shown to catch anything.

WHY THIS ONE FIRST. It is a SOURCE-TEXT suite: it asserts against the text of
`api/sd-data.js` rather than executing it. That is the exact shape that produced
the test-layer half of defect cluster `5b98fd27`, where three assertions matched
text AFTER the guard rather than the guard's own position and stayed green with
`if(false && ...)` planted. A text suite that has never been sabotaged has no
evidence its assertions are anchored on the thing they name.

WHAT THE SUITE PROTECTS. Six append-only writes read the table to see whether an
`entry_id` already exists. All six used to read it as
`existingR.ok ? await existingR.json() : []`, so a 401, 403, 500 or 503 answered
"no existing record" and the write proceeded. For `alf_mar`, `alf_incidents` and
`alf_op_audits` the write is a merge-duplicates upsert, so a failed check
SILENTLY OVERWRITES a past medication administration, an incident report or an
audit observation.

Every mutation below restores one half of that defect.
"""
# REQUIREMENT: an append-only medication record cannot be updated or deleted through
#   any reachable path, because the append-only property IS the audit trail
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'alf-append-only-fail-closed.test.js')
API = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    # ── RE-AIMED 2026-09-21, AND THE REASON IS THE WHOLE POINT ────────────
    # This anchored on alf_mar's appendOnlyExisting call, and alf_mar no longer
    # has one: it moved to the atomic RPC because the read-then-write it used
    # was a TOCTOU window, not merely a fail-open one. The harness reported
    # ANCHOR-0 and refused, which is the right outcome -- a mutation aimed at
    # code that no longer exists proves nothing and must not be scored.
    #
    # RE-AIMED RATHER THAN DELETED: the requirement is "ONE of the sites goes
    # back to fail-open", and five sites still carry it. alf_claim_routes is
    # the one chosen because mutations 2 and 3 already own alf_incidents and
    # alf_op_audits, so this keeps three distinct sites under mutation.
    ("1. ONE of the five remaining sites goes back to fail-open -- the "
     "smallest possible diff, and it silently overwrites a recorded billing "
     "determination",
     API,
     "      const existingRows = await appendOnlyExisting(res, existingR, "
     "'alf_claim_routes'); if (!existingRows) return;",
     "      const existingRows = existingR.ok ? await existingR.json() : [];"),

    # ── AND THE NEW PROPERTY THAT REPLACED IT, WHICH NEEDS ITS OWN ARM ────
    ("1b. alf_mar goes BACK to the read-then-write it was moved off -- the "
     "TOCTOU window reopens, the suite's five-site count becomes six, and a "
     "medication administration can be overwritten by two writers racing",
     API,
     "      const r = await fetch(rest('rpc/alf_check_and_insert_mar_entry'), {",
     "      const existingRows = await appendOnlyExisting(res, existingR, 'alf_mar'); if (!existingRows) return;\n"
     "      const r = await fetch(rest('rpc/alf_check_and_insert_mar_entry'), {"),

    ("2. an incident report's site goes back to fail-open",
     API,
     "      const existingRows = await appendOnlyExisting(res, existingR, "
     "'alf_incidents'); if (!existingRows) return;",
     "      const existingRows = existingR.ok ? await existingR.json() : [];"),

    ("3. the guard is CALLED and its answer ignored -- the shape that looks "
     "right in review because the call is right there",
     API,
     "      const existingRows = await appendOnlyExisting(res, existingR, "
     "'alf_op_audits'); if (!existingRows) return;",
     "      const existingRows = await appendOnlyExisting(res, existingR, "
     "'alf_op_audits') || [];"),

    ("4. a non-OK read stops refusing, so a 503 from the check answers 'no "
     "existing record'",
     API,
     "async function appendOnlyExisting(res, r, what) {\n  if (!r.ok) {",
     "async function appendOnlyExisting(res, r, what) {\n  if (false) {"),

    # ── THE SCENARIO IN THIS NAME WAS WRONG, corrected 2026-09-21 ──────────
    # It said "an HTML error page parses to something that is not a list". An
    # HTML page does not parse as JSON at all -- it throws, the
    # `.catch(() => null)` yields null, and every call site's
    # `if (!existingRows) return;` refuses it even with this guard removed. So
    # the stated trigger could not have driven the arm.
    #
    # The reachable one is a body that parses to a TRUTHY non-array: a JSON
    # OBJECT, which is the shape PostgREST returns for an error
    # ({"message": ...}), or a bare string or number. That value is truthy, so
    # the caller's falsy check passes it through, `existingRows.length > 0` is
    # undefined-guarded away, and the write proceeds. Corrected because a
    # control whose own description names an impossible trigger invites the
    # next reader to decide the arm is theoretical.
    ("5. a non-array body stops refusing -- a JSON OBJECT (PostgREST's error "
     "shape) is truthy, so it survives the caller's falsy check and the write "
     "proceeds",
     API,
     "  if (!Array.isArray(rows)) {\n    console.error('sd-data: append-only "
     "check returned a non-array (' + what + ')');",
     "  if (false) {\n    console.error('sd-data: append-only "
     "check returned a non-array (' + what + ')');"),

    ("6. the refusal loses its code, so a caller cannot tell an integrity "
     "failure from any other 502",
     API,
     "    res.status(502).json({ error: { code: 'INTEGRITY_CHECK_FAILED', "
     "message: 'Could not confirm whether this record already exists, so "
     "nothing was written. Try again.' } });\n    return null;\n  }\n  const "
     "rows = await r.json()",
     "    res.status(502).json({ error: { code: 'UPSTREAM_ERROR', "
     "message: 'Could not confirm whether this record already exists, so "
     "nothing was written. Try again.' } });\n    return null;\n  }\n  const "
     "rows = await r.json()"),

    ("7. the refusal returns a VALUE instead of null, so every call site's "
     "`if (!existingRows) return` stops firing while the guard still looks "
     "present",
     API,
     "    console.error('sd-data: append-only check failed (' + what + '), "
     "HTTP', r.status);",
     "    console.error('sd-data: append-only check failed (' + what + '), "
     "HTTP', r.status);\n    return [];"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNcare append-only -- the suite must refuse a fail-open '
              'integrity check on four Tier A tables',
        # ── api/sd-data.js IS STAGED SINCE 2026-09-21 ───────────────────────
        # The worktree is created at HEAD and the SUITE is always copied in
        # from this clone, so an uncommitted change to the SUBJECT left the
        # two describing different code. It went red the moment alf_mar moved
        # to the atomic RPC: the staged suite expected five appendOnlyExisting
        # call sites and the HEAD copy of api/sd-data.js still had six. The
        # baseline arm said so plainly rather than letting a mutation be
        # scored against a subject nobody had changed, which is the whole
        # reason that arm exists.
        stage=(API,)))
