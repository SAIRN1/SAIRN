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

The SIX mutations, which are exactly the six driven below -- no more, because a
list of properties longer than the list of mutations is a coverage claim nobody
made:

  1. the updated_at precondition is dropped, so the PATCH is unconditional
     again and a concurrent write is overwritten -- the original defect;
  2. a failed precondition stops being detected, so the caller is told their
     credential was saved and it was not -- the same data loss with a
     confirmation message on top;
  3. `clear` wipes the whole blob on the MAIN path;
  3b. and on the RETRY path, which is the one that had no arm;
  4. the admin role check goes;
  5. the session check goes, and the suite asserts the refusal happens BEFORE
     the table is touched rather than merely that a refusal happens.
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
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNcode service credentials -- the suite must refuse a write '
              'that can lose another administrator\'s credential'))
