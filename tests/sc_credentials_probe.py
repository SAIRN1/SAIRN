"""api/sc-credentials.test.js must REFUSE a lost-update, not merely observe one.

Run: python tests/sc_credentials_probe.py

`sc_credential_scope` is one of SAIRNcode's seven TIER A records. Every service
credential for a medical-billing practice lives in ONE jsonb blob keyed
(license_hash, credential_id='default'), and the handler read that blob, changed
one service inside it, and upserted THE WHOLE THING back with
resolution=merge-duplicates -- which replaces `data` wholesale.

TWO COMPLIANCE ADMINS CONFIGURING DIFFERENT SERVICES IN THE SAME WINDOW both
read the same blob and each wrote their own service on top of what they read.
The second write silently dropped the first's credential: no error, nothing in
the UI, and the missing key surfacing later as an eligibility check reporting
NOT_CONFIGURED for a service somebody knows they set up. A clinical-billing
integration that stops working with no event anywhere naming the moment it
stopped.

THE SUITE'S OWN HEADER MAKES THE ARGUMENT THIS PROBE MEASURES: asserting only
the final blob would PASS AGAINST A LUCKY ORDERING, so it asserts the write is
CONDITIONAL -- an updated_at precondition on a PATCH -- because the SHAPE is the
fix. That is exactly the right instinct and it is an argument, not evidence.
This is the evidence.

AND IT FOUND ONE. `clear` is implemented TWICE -- once on the main path and
once in applyChange(), which exists so a retry re-applies THIS request's change
to a freshly-read blob rather than re-sending a stale merge. That is the right
design, and it means the deletion is written twice while the suite's clear arm
never conflicts, so only one of the two copies was ever reached. Mutation 3b
wipes the blob in the retry copy and the suite stayed GREEN. An arm now drives
`clear` THROUGH a forced conflict and asserts it actually retried, because an
arm that silently takes the non-retry path proves nothing the existing one does
not already prove.

THE 2026-09-18 THREE-STATE WRITE RESULT SHIPPED WITH NO MUTATION AT ALL, and
mutations 6-8 are it, added 2026-09-21 from the independent review of that
change. Everything numbered 1-5 guards the 2026-09-04 concurrency fix and the
auth checks; the only 09-18 edit to this file was RE-AIMING a stale anchor,
which is a repair and not coverage. The author's own obligation reports
mutations run BY HAND -- the measurement existed and the tree could not
reproduce it, which is the state a control exists to end.

AND ONE OF THE THREE HAD TO BE A PAIR, WHICH IS WHY THE SHARED HARNESS GREW A
MULTI-EDIT MUTATION. The first-path UNKNOWN check and the final gate are
MUTUALLY REDUNDANT: driven individually, removing either alone is SILENT,
because the survivor answers with the identical 502. That is not an unpinned
guard, it is a property that only exists as a conjunction -- and a harness that
can plant one edit at a time cannot state it. `old` and `new` may now be lists.

THE NINE mutations, which are exactly the nine driven below -- no more, because
a list of properties longer than the list of mutations is a coverage claim
nobody made:

  1. the updated_at precondition is dropped, so the PATCH is unconditional
     again and a concurrent write is overwritten -- the original defect;
  2. a failed precondition stops being detected, so the caller is told their
     credential was saved and it was not -- the same data loss with a
     confirmation message on top;
  3. `clear` wipes the whole blob on the MAIN path;
  3b. and on the RETRY path, which is the one that had no arm;
  4. the admin role check goes;
  5. the session check goes, and the suite asserts the refusal happens BEFORE
     the table is touched rather than merely that a refusal happens;
  6. BOTH the first-path UNKNOWN check and the final gate go together, so an
     unreadable body is reported as a saved credential again;
  7. the RETRY path's own UNKNOWN check goes -- it bites alone, because that
     path returns before the final gate;
  8. representationSays() calls an unreadable body WROTE, so all three guards
     stay and every one of them asks a function that answers wrongly.

AND ONE THING MEASURED WHILE WRITING MUTATION 6, RECORDED BECAUSE IT CHANGES
WHAT THE FINAL GATE IS. Its comment calls it "the last gate, and it covers the
INSERT path too". It does not, and it cannot refuse anything: the insert path
enters the SAME `if (writeR.ok || writeR.status === 409)` block, so the
first-path check has already classified it. Instrumented in a throwaway
worktree -- the gate is evaluated THREE times across the whole suite and says
WROTE every one of them, and the control flow says why: an UNKNOWN returns at
the check above, a MISSED returns from the retry path, and a non-ok response
returns at `upstream()` one line earlier. It is belt-and-braces, which is a
fine thing to keep; it is not a second gate on a path the first one misses,
and mutation 6 is a pair rather than two singles for exactly that reason.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sc-credentials.test.js')
SRC = os.path.join('api', 'sc-credentials.js')

MUTATIONS = [
    ("1. THE ORIGINAL DEFECT, RESTORED. The updated_at precondition is dropped "
     "from the PATCH, so the write is unconditional again and the second admin "
     "silently overwrites the first -- no error, nothing in the UI",
     SRC,
     "          '&updated_at=eq.' + enc(expectedUpdatedAt)), {",
     "          ''), {"),

    ("2. a failed precondition becomes a SILENT NO-OP instead of a conflict. "
     "PostgREST answers a PATCH that matched no row with success and zero rows, "
     "so the caller is told the credential was saved and it was not -- the same "
     "data loss, now with a confirmation message on top",
     SRC,
     # ANCHOR RE-AIMED 2026-09-18. The two lines this used to name were
     # replaced when api/sc-credentials.js grew a three-way write result
     # (WROTE / MISSED / UNKNOWN), and the harness reported ANCHOR-0 --
     # correctly a FAILURE rather than a skip, because a stale anchor is how
     # this class of probe quietly stops testing anything. The mutation is
     # unchanged in intent: the zero-rows detection stops detecting, so a
     # failed precondition becomes a silent no-op.
     "      const noRowsMatched = firstSays === MISSED;",
     "      const noRowsMatched = false;"),

    ("3. `clear` removes the whole blob rather than the named service on the "
     "MAIN path, so clearing one integration deletes every other practice "
     "credential with it",
     SRC,
     "    } else {\n      delete next[service];\n    }",
     "    } else {\n      for (const k of Object.keys(next)) delete next[k];\n    }"),

    ("3b. and the same thing on the RETRY path. applyChange() is a SEPARATE "
     "copy of the change, written so a retry re-applies the change rather than "
     "re-sending a stale merge -- so `clear` is implemented twice and only one "
     "of the two is reached by a test that never conflicts",
     SRC,
     "      if (action === 'set') { out[service] = nextEntry; } else { delete out[service]; }",
     "      if (action === 'set') { out[service] = nextEntry; } else { return {}; }"),

    ("4. the ROLE check goes. A concurrency fix on a Tier A credential store "
     "that lets any signed-in user write it is protecting the wrong thing",
     SRC,
     "    if (caller.role !== 'admin') {",
     "    if (false) {"),

    ("5. the SESSION check goes, so the table is reachable without signing in "
     "at all -- and the suite asserts the refusal happens BEFORE the table is "
     "touched, not merely that a refusal happens",
     SRC,
     "  if (!caller) {",
     "  if (false) {"),

    # ── THE 2026-09-18 THREE-STATE WRITE RESULT, WHICH SHIPPED WITH NONE ────
    # Added 2026-09-21 by cody, from the independent review of that change.
    # Everything above guards the 2026-09-04 concurrency fix and the auth
    # checks; the only 09-18 edit to this file was RE-AIMING a stale anchor,
    # which is a repair and not coverage. The author's own record reports
    # mutations run BY HAND -- so the measurement existed and the tree could
    # not reproduce it, which is the state a control exists to end.

    ("6. THE PAIR, AND IT HAS TO BE A PAIR. The first-path UNKNOWN check and "
     "the final gate BOTH go, so an unreadable body on the first PATCH is "
     "reported as a saved credential -- the original defect, restored through "
     "the two guards that replaced it",
     SRC,
     # NEITHER ONE ALONE IS OBSERVABLE AND THAT IS NOT A GAP IN THE SUITE.
     # Driven, each alone, before this was written: removing the first-path
     # check alone leaves `writeRows` null, the `if (writeRows === null)`
     # re-read of an already-consumed body yields null again, and the final
     # gate refuses with the same 502 -- externally identical. Removing the
     # final gate alone changes nothing at all, for the reason in mutation 7.
     # So the property a control can pin is the CONJUNCTION, and a harness
     # that could only plant one edit could not state it.
     ["      if (firstSays === UNKNOWN) { refuseUnconfirmed(res); return; }",
      "    if (representationSays(writeRows) !== WROTE) { refuseUnconfirmed(res); return; }"],
     ["      if (false) { refuseUnconfirmed(res); return; }",
      "    if (false) { refuseUnconfirmed(res); return; }"]),

    ("7. THE RETRY PATH'S OWN UNKNOWN CHECK, which bites ALONE because that "
     "path RETURNS before the final gate and nothing downstream can cover for "
     "it -- the half the author recorded as untested",
     SRC,
     "        if (secondSays === UNKNOWN) { refuseUnconfirmed(res); return; }",
     "        if (false) { refuseUnconfirmed(res); return; }"),

    ("8. THE CLASSIFIER ITSELF: an unreadable body is WROTE again, so all "
     "three guards stay in place and every one of them asks a function that "
     "now answers wrongly -- the defect one level below the guards",
     SRC,
     "      if (rows === null || rows === undefined) return UNKNOWN;  // body unreadable",
     "      if (rows === null || rows === undefined) return WROTE;  // body unreadable"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNcode service credentials -- the suite must refuse a write '
              'that can lose another administrator\'s credential'))
