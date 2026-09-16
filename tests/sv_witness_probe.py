"""api/sv-witness.test.js must REFUSE, not merely agree.

Run: python tests/sv_witness_probe.py

TIER A, AND THE HIGHEST-STAKES ONE WITHOUT A CONTROL. The witnessing lock is
this platform's first hard lock on an irreversible write: SAIRNvet's
controlled-substance register (`sv_controlled`, `sv_audit_log`, `sv_patients`).
Its own header says what a control for a lock has to prove -- "a lock that
cannot be made to REFUSE is decorative" -- and until now nothing had ever made
its SUITE refuse.

Measured 2026-09-15: 7 of 154 JavaScript suites on this platform have a
negative control at all, and 67 of the 147 without one touch a Tier A resource.

WHAT IS PLANTED. The mechanism is content binding: a witness token is issued
against a hash of (resource + canonical payload) and may be spent once. Every
mutation below removes one property of that binding, and each is a change that
makes the code SIMPLER and reads as a tidy-up:

  * the resource leaves the hash, so a token issued for one table spends on
    another -- the content-binding hole wearing a different hat, named in the
    source's own comment;
  * key ordering leaves the canonical form, so two payloads that differ only in
    key order stop agreeing and the binding becomes accidental;
  * the token is stored in the clear rather than hashed;
  * the expiry becomes long enough that a signature detaches from the act it
    witnessed;
  * the locked-resource set empties, so the lock exists and locks nothing.
"""
# REQUIREMENT: api/sv-witness.test.js can be MADE TO REFUSE, because a lock
#   that cannot be made to refuse is decorative -- and this is the platform's
#   first hard lock on an irreversible write, SAIRNvet's controlled-substance
#   register
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sv-witness.test.js')
SRC = os.path.join('api', 'sv-witness.js')

MUTATIONS = [
    ("1. THE RESOURCE LEAVES THE HASH -- a token issued for one table can be "
     "spent on another, which the source's own comment names as the "
     "content-binding hole",
     SRC,
     "    .update(String(resource) + '\\n' + canonical(payload))",
     "    .update(canonical(payload))"),

    ("2. the canonical form stops SORTING keys, so two payloads that differ "
     "only in key order no longer hash alike and the binding becomes an "
     "accident of serialisation order",
     SRC,
     "  const keys = Object.keys(value).sort();",
     "  const keys = Object.keys(value);"),

    ("3. arrays lose their canonical form, so [1,2] and [2,1] collapse",
     SRC,
     "  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') "
     "+ ']';",
     "  if (Array.isArray(value)) return JSON.stringify(value.slice().sort());"),

    ("4. the token is stored IN THE CLEAR instead of hashed -- a database read "
     "then yields a spendable witness",
     SRC,
     "function hashToken(tok) {\n  return crypto.createHash('sha256')"
     ".update(String(tok)).digest('hex');\n}",
     "function hashToken(tok) {\n  return String(tok);\n}"),

    ("5. the lock's resource set EMPTIES -- the lock is still there, still "
     "imported, and locks nothing",
     SRC,
     "const LOCKED_RESOURCES = { sv_controlled: true };",
     "const LOCKED_RESOURCES = {};"),

    ("6. the ten-minute expiry becomes a week, so a signature detaches from "
     "the act it witnessed",
     SRC,
     "const TOKEN_TTL_MS = 10 * 60 * 1000;",
     "const TOKEN_TTL_MS = 7 * 24 * 60 * 60 * 1000;"),

    ("7. a null payload stops being distinguishable from the string 'null' in "
     "the canonical form",
     SRC,
     "  if (value === null || typeof value !== 'object') return "
     "JSON.stringify(value);",
     "  if (value === null || typeof value !== 'object') return String(value);"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNvet witnessing lock -- the suite must refuse a lock whose '
              'content binding has been loosened'))
