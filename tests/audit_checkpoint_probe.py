"""api/audit-checkpoint.test.js must REFUSE, and this suite has a PROVEN escape.

Run: python tests/audit_checkpoint_probe.py

THIS IS THE ONE SUITE ON THE PLATFORM WITH DOCUMENTED EVIDENCE THAT IT LET A
REAL DEFECT THROUGH. The paging guard read

    total !== null && total !== rows.length

so the ABSENCE of a Content-Range total disabled the completeness check rather
than failing it. Driven against the real handler with a fake returning one row
of three: `0-0/3` correctly refused, while `0-0/*` and no header at all returned
HTTP 200 and wrote a checkpoint with row_count 1. Found on 2026-09-14 by an
INDEPENDENT REVIEW that drove the handler, not by this suite, whose every arm
presented a well-formed Content-Range -- the shape the API returns in normal
operation, and therefore the one shape that could never expose the guard.

A SUITE WITH A KNOWN ESCAPE IS THE HIGHEST-VALUE PLACE TO PUT A CONTROL, because
the question is no longer hypothetical: mutation 1 re-introduces that exact
defect, byte for byte, and the arms added by the fix must now catch what they
did not catch before. Every earlier green run of this suite is evidence about a
handler that no longer exists.

WHAT THIS FILE PROTECTS. All three audit tables carry `grant select, insert` and
nothing else, so a row cannot be edited or removed through the API. The mode the
grant leaves open is INSERTION -- api/_lib/audit.js lets created_at default, so
anyone with the service key can insert a row with any timestamp under any
license_hash. The checkpoint chain is what makes that visible, and on the backup
side it is also the fingerprint carried INSIDE the data that lets a restored
dump be checked against its own past without a baseline captured at dump time.
A vacuous checkpoint therefore breaks two things, one of them silently.

THE MUTATIONS ARE THE PROPERTIES, ONE EACH:

  * the paging guard vanishes with its input again -- the 2026-09-14 defect;
  * a short read stops refusing, which is the same harm arriving through a
    WRONG count rather than an absent one;
  * the open window is checkpointed, so today is hashed mid-flight and every
    later row in it reads as an insertion;
  * the chain stops folding in the previous digest, so a rewritten checkpoint
    is undetectable and CHAIN_BROKEN can never fire;
  * the genesis link becomes an empty string, so a lost prev_digest is
    indistinguishable from a genuine first link;
  * an empty table gets a checkpoint, which is a digest over nothing and a
    permanent lie that verifies cleanly forever;
  * the row sort is dropped, so the digest depends on the order the server
    happened to return -- every verification fails on a correct log, and with
    no UPDATE grant nothing can repair it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'audit-checkpoint.test.js')
SRC = os.path.join('api', 'audit-checkpoint.js')

MUTATIONS = [
    ("1. THE 2026-09-14 DEFECT, RESTORED. The completeness check is conditioned "
     "on the total being present, so a response with no Content-Range -- or "
     "`0-0/*` -- skips it entirely and a checkpoint is written over one row of "
     "three. This suite did not catch it the first time",
     SRC,
     "  if (total === null) {",
     "  if (false) {"),

    ("2. the same harm through a WRONG count rather than an absent one: a short "
     "read stops refusing, so a digest over the first page of a busy day is "
     "stable, reproducible, and covers a fraction of the window",
     SRC,
     "  if (total !== rows.length) {",
     "  if (false && total !== rows.length) {"),

    ("3. TODAY IS CHECKPOINTED. The open window is hashed mid-flight, so every "
     "row written into the rest of the day reads afterwards as an INSERTION -- "
     "a tamper finding manufactured daily against a correct log",
     SRC,
     "  const closedThrough = dayStart(nowMs);          // today's window is still OPEN",
     "  const closedThrough = dayStart(nowMs) + DAY_MS;"),

    ("4. the chain stops being a chain -- the digest no longer folds in the "
     "previous one, so a rewritten checkpoint row is undetectable and "
     "CHAIN_BROKEN can never fire on anything",
     SRC,
     "  let prev = last ? last.digest : GENESIS;",
     "  let prev = GENESIS;"),

    ("5. the genesis link becomes an empty string. A prev_digest that was LOST "
     "or never set then reads as a genuine first link, which is the one "
     "distinction the named constant exists to preserve",
     SRC,
     "const GENESIS = 'genesis:sairn-audit-checkpoint:v1';",
     "const GENESIS = '';"),

    ("6. an EMPTY table gets a checkpoint anyway -- a digest over nothing, which "
     "verifies cleanly forever and is a permanent lie about a window nobody "
     "wrote to",
     SRC,
     "    if (!first) return { table: table, written: 0, note: 'no audit rows yet' };",
     "    if (!first) { cursor = dayStart(nowMs) - DAY_MS; return checkpointEmpty(table, cursor); }"),

    ("7. the rows are hashed in the order the server happened to return them "
     "instead of sorted. The digest becomes non-deterministic, every "
     "verification reports a broken chain on a CORRECT log, and with no UPDATE "
     "grant on the checkpoint table nothing can repair it",
     SRC,
     "  const ordered = rows.slice().sort((a, b) => {",
     "  const ordered = rows.slice(); const _unusedSort = ((a, b) => {"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='the audit checkpoint chain -- the suite that once let a vacuous '
              'checkpoint through must now refuse the same defect'))
