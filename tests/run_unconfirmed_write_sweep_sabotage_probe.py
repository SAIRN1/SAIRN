"""api/sd-data-unconfirmed-write-sweep.test.js must REFUSE, not merely agree.

Run: python tests/run_unconfirmed_write_sweep_sabotage_probe.py

# REQUIREMENT: the guard on unconfirmed representation-PATCHes must go RED when
#   any of the EIGHT repaired sites goes back to reporting ok:true for a write
#   the store did not confirm, when the three-answer vocabulary collapses to
#   two, or when the predicate that keeps the shape from coming back stops
#   recognising it -- because every one of those failures is SILENT at runtime
#   and the suite is the only thing that would notice

WHY THIS FILE EXISTS AT ALL. The 2026-09-21 sweep reported "9 of 9 sabotages
caught" and the commit contains no probe -- the nine were run ad hoc and
discarded, which is the finding the review of that work recorded. The same
review then found FOUR MORE live sites the guard could not see. So this is the
committed control for both halves: hank's four and the four found reviewing
them.

── THE TWO GENERATIONS, AND WHY BOTH ARE SABOTAGED ────────────────────────
The first four were written with `.json().catch(() => null)` and answer 404 on
a MISS. The second four read the body with a bare `await r.json()` and answer
409 with a named race code, because each of them READ the row moments before
the PATCH -- so a zero-row match is the row moving, not the row having never
been there. Both generations must be refusable.

── WHAT IS PLANTED ────────────────────────────────────────────────────────
  1-4. EACH OF THE FOUR NEW SITES GOES BACK TO ITS OLD LINE, exactly as it
       was before the repair. These are not invented defects: they are the
       code that shipped.
  5.   THE RACE BECOMES A SUCCESS: the MISSED branch of one site is removed,
       so a zero-row PATCH falls through to the 200.
  6.   wroteRow's MISSED BECOMES WROTE -- the vocabulary collapses at the
       source, for all eight sites at once.
  7.   wroteRow's NON-ARRAY branch becomes WROTE. This is the sabotage that
       SURVIVED the original run, because the only UNKNOWN arm drove a body
       that would not parse and the catch turned that into null, handled by
       the function's first line. It is covered now and must stay covered.
  8.   refuseUnconfirmedWrite answers 200 ok:true, so UNKNOWN reads as success.
  9.   THE PREDICATE STOPS WALKING THE PATCH and goes back to keying on the
       read's spelling -- the exact narrowing that hid four live sites while
       reporting the file clean.
 10.   THE PREDICATE'S GUARD TEST WIDENS to accept any mention of rows, so a
       site that merely names a variable counts as guarded.

The suite is staged into the worktree along with api/sd-data.js, because
neither is committed when this first runs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-unconfirmed-write-sweep.test.js')
SD = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. [:2634 sd_quote_requests] THE ORIGINAL LINE RESTORED -- the body is "
     "read and never consulted, and the 200 carries an object assembled "
     "locally from a read taken moments earlier",
     SD,
     "      const qrSays = wroteRow(wrows);",
     "      const qrSays = 'WROTE';"),

    ("2. [:7500 rf_invoices issue] THE ORIGINAL LINE RESTORED -- an invoice "
     "reported ISSUED on a PATCH that matched nothing, after the sequential "
     "allocator has already spent the number",
     SD,
     "        const issSays = wroteRow(rows);",
     "        const issSays = 'WROTE';"),

    ("3. [:7536 rf_invoices add_payment] THE ORIGINAL LINE RESTORED -- a "
     "payment recorded against an invoice that did not take it",
     SD,
     "        const paySays = wroteRow(rows);",
     "        const paySays = 'WROTE';"),

    ("4. [:8064 rf_schedule] THE ORIGINAL LINE RESTORED -- the worst spelling "
     "in the file: it answers 200 with the status the REQUEST carried",
     SD,
     "      const schedSays = wroteRow(rows);",
     "      const schedSays = 'WROTE';"),

    ("5. [:8064] THE RACE BRANCH IS REMOVED -- a zero-row PATCH falls through "
     "to the success response instead of 409",
     SD,
     "      if (schedSays === 'MISSED') {",
     "      if (false) {"),

    ("6. wroteRow: MISSED BECOMES WROTE -- the three-answer vocabulary "
     "collapses to two at the source, for all eight sites at once",
     SD,
     "  if (rows.length === 0) return 'MISSED';                      // matched nothing",
     "  if (rows.length === 0) return 'WROTE';                       // matched nothing"),

    ("7. wroteRow: THE NON-ARRAY BRANCH BECOMES WROTE -- the sabotage that "
     "SURVIVED the original run, because the only UNKNOWN arm drove a body "
     "that would not parse and the catch turned that into null",
     SD,
     "  if (!Array.isArray(rows)) return 'UNKNOWN';                  // not the shape asked for",
     "  if (!Array.isArray(rows)) return 'WROTE';                    // not the shape asked for"),

    ("8. refuseUnconfirmedWrite ANSWERS SUCCESS -- UNKNOWN is reported as a "
     "write that landed",
     SD,
     "  res.status(502).json({ error: { code: 'WRITE_UNCONFIRMED',",
     "  res.status(200).json({ ok: true, code: 'WRITE_UNCONFIRMED',"),

    ("9. THE PREDICATE STOPS WALKING THE PATCH and keys on the read's spelling "
     "again -- the exact narrowing that hid four live sites while reporting "
     "the file clean",
     SUITE,
     "    if (!/method:\\s*'PATCH'/.test(l)) return;",
     "    if (!/\\.json\\(\\)\\.catch\\(/.test(l)) return;"),

    ("10. THE PREDICATE'S GUARD TEST WIDENS -- any mention of a rows variable "
     "counts as guarded, so a site that merely names one is cleared",
     SUITE,
     "    if (/wroteRow\\(/.test(after)) return;                                  // guarded, the platform way",
     "    if (/rows/.test(after)) return;                                         // guarded, the platform way"),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='no representation-PATCH may report a write the store did not '
          'confirm -- and the predicate that keeps it true must stay able to '
          'see the shape',
    # api/_lib/auth.js is staged 2026-09-24 because the file(s) above now
    # call roleSet() from it -- the platform-wide null-prototype role-map
    # sweep. The worktree is at HEAD, so an UNSTAGED DEPENDENCY of a staged
    # file dies at require() and the BASELINE goes red before any mutation
    # is planted. Same gap as an unstaged file. Full account: api/_lib/auth.js.
    stage=(SD, os.path.join('api', '_lib', 'auth.js')),
))
