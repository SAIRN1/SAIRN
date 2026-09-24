"""api/_lib/law-timeentry.test.js must REFUSE, not merely agree.

Run: python tests/run_law_timeentry_trim_sabotage_probe.py

# REQUIREMENT: the suite guarding SAIRNlaw's time-entry gate must go RED when
#   the billing code that is VALIDATED stops being the billing code that is
#   STORED -- when the normaliser is not called, when it is called and does
#   nothing, when only the echo is normalised and not the row, when it reaches
#   past the one field a gate stands behind, or when it quietly coerces a value
#   the gate exists to refuse

WHAT WAS OPEN. timeEntryProblem() has judged `billing_code.trim()` since it was
written; api/sd-data.js then wrote `data: payload`, the UNTRIMMED string. Every
arm in the suite asked whether a request was REFUSED, and all of them passed
against the seam: '  L100  ' was accepted, correctly, and then stored with the
padding the validator had already removed. FINDING 1 of the independent review
of that module named this shape, and the module's own header repeated the name
in its rate section while leaving it open on the field it was found on.

── WHY THE LENGTH ARM IS THE ONE TO KEEP ──────────────────────────────────
A trailing space in an invoice column is cosmetic. The bound is not: 30 spaces
followed by 'L100' is 34 characters, trims to 4, and MAX_BILLING_CODE_CHARS is
checked against the 4. So a value the gate would refuse if asked about the
thing being written was accepted and written. Arm 2 is what proves the suite
reads the STORED row rather than the response, because the response is built
from the database's representation and is right either way.

── AND THE ECHO IS SABOTAGED SEPARATELY FROM THE ROW ──────────────────────
The handler answers `rows[0].data` when PostgREST returns a representation and
the request row otherwise. Arm 4 normalises only one of the two, which is
invisible to any arm that exercises the representation path alone -- the reason
the suite gained an arm driving the fallback branch.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', '_lib', 'law-timeentry.test.js')
LIB = os.path.join('api', '_lib', 'law-timeentry.js')
SD = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. THE NORMALISER IS NOT CALLED -- the state of this write path until "
     "2026-09-21, in which the value judged and the value stored are different "
     "values",
     SD,
     "        lawRow = lawTimeEntry.normalizedTimeEntry(payload);",
     "        lawRow = payload;"),

    ("2. THE NORMALISER RUNS AND DOES NOTHING -- it is called, it returns, and "
     "the untrimmed code is what lands, which is the shape a present-and-wrong "
     "control has",
     LIB,
     "  const code = r.billing_code.trim();\n"
     "  // Returned unchanged when there is nothing to change",
     "  const code = r.billing_code;\n"
     "  // Returned unchanged when there is nothing to change"),

    ("3. THE LENGTH BOUND IS CHECKED ON THE TRIMMED VALUE AND THE RAW ONE IS "
     "STORED -- the half of this defect that changes whether the row PASSES, "
     "not merely how it prints",
     LIB,
     "  if (code === r.billing_code) { return record; }\n"
     "  return Object.assign({}, r, { billing_code: code });",
     "  if (code === r.billing_code) { return record; }\n"
     "  return Object.assign({}, r, { billing_code: r.billing_code.slice(0) });"),

    ("4. ONLY THE ECHO IS NORMALISED, NOT THE ROW -- the caller is shown "
     "'L100' while the database holds '  L100  ', which no arm reading the "
     "representation path can see",
     SD,
     "        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', [lawIdCol]: String(payload.id), data: lawRow, updated_at: nowISO() })",
     "        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', [lawIdCol]: String(payload.id), data: payload, updated_at: nowISO() })"),

    ("5. THE NORMALISER REACHES PAST ITS FIELD -- it trims every string in the "
     "entry, so `description` is reshaped by a module with no gate standing "
     "behind that decision",
     LIB,
     "  return Object.assign({}, r, { billing_code: code });",
     "  const out = Object.assign({}, r, { billing_code: code });\n"
     "  Object.keys(out).forEach(function (k) {\n"
     "    if (typeof out[k] === 'string') { out[k] = out[k].trim(); }\n"
     "  });\n"
     "  return out;"),

    # THE ANCHOR CARRIES THE COMMENT AND THE trim() LINE, not the `typeof`
    # test alone. That test appears TWICE in this file -- timeEntryProblem()
    # opens with the identical line -- and the harness refused the mutation as
    # ANCHOR-2 rather than silently planting it in whichever came first. A
    # mutation that lands in the wrong function tests the wrong thing, and the
    # probe said so.
    ("6. THE NORMALISER COERCES A NON-STRING CODE -- String(100).trim() is "
     "'100', so the day timeEntryProblem() stops refusing a number this hides "
     "it instead of showing it",
     LIB,
     "  if (typeof r.billing_code !== 'string') {\n"
     "    // NOT a second refusal. timeEntryProblem() has already rejected a\n"
     "    // non-string code by the time this runs; coercing one here would hide the\n"
     "    // day that stops being true.\n"
     "    return record;\n"
     "  }\n"
     "  const code = r.billing_code.trim();",
     "  if (r.billing_code === undefined || r.billing_code === null) {\n"
     "    return record;\n"
     "  }\n"
     "  const code = String(r.billing_code).trim();"),

    ("7. THE NORMALISER MUTATES THE CALLER'S OBJECT -- the stored row is right "
     "and the payload every later line reads has been rewritten underneath it",
     LIB,
     "  if (code === r.billing_code) { return record; }\n"
     "  return Object.assign({}, r, { billing_code: code });",
     "  if (code === r.billing_code) { return record; }\n"
     "  r.billing_code = code;\n"
     "  return r;"),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='SAIRNlaw: the billing code a time entry is JUDGED on must be the '
          'billing code it is STORED with -- including at the length bound, '
          'where the two differ in whether they pass',
    # api/_lib/auth.js is staged 2026-09-24 because the file(s) above now
    # call roleSet() from it -- the platform-wide null-prototype role-map
    # sweep. The worktree is at HEAD, so an UNSTAGED DEPENDENCY of a staged
    # file dies at require() and the BASELINE goes red before any mutation
    # is planted. Same gap as an unstaged file. Full account: api/_lib/auth.js.
    stage=(LIB, SD, os.path.join('api', '_lib', 'auth.js')),
))
