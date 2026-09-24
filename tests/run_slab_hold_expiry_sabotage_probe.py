"""tests/run_slab_hold_expiry_sabotage_probe.py -- does the slab-hold suite
actually REFUSE a broken expiry, or is it green over whatever is there?

    python tests/run_slab_hold_expiry_sabotage_probe.py

REQUIREMENT: api/sd-data-slab-reserve.test.js must go RED for each defect
planted below. A suite that stays green with one of these in place is not
protecting the hold; it is describing it.

── WHY THIS PATH GETS A SABOTAGE PROBE AND MOST DO NOT ────────────────────
The compare-and-swap it guards exists because two salespeople sold the same
physical slab and the app could not tell anyone it had happened. Expiry makes
that guard CONDITIONAL for the first time -- before today a reservation always
won, and now it wins only while its deadline holds. Every mutation below is a
way for that condition to be wrong in the direction that gives the slab away.

── THE TWO THAT WOULD SHIP QUIETEST ───────────────────────────────────────
MUTATION 1 makes a MISSING reservedUntil read as expired. Every slab reserved
before this feature existed has no such field, so this single line releases
every standing hold on the platform the moment it deploys -- silently, with no
error anywhere, discovered when two people cut the same slab. It is one
character of difference (`Infinity` to `0`) and it reads as tidier.

MUTATION 4 trusts the caller's own reservedUntil instead of overwriting it.
Nothing refuses, nothing logs, and every reservation still succeeds. What
changes is that a client can now back-date somebody else's hold and take the
slab, which is the original double-sale with one extra field.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                      # noqa: E402

SUITE = os.path.join('api', 'sd-data-slab-reserve.test.js')
SRC = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. THE ONE THAT RELEASES EVERY STANDING HOLD ON DEPLOY: an ABSENT "
     "reservedUntil reads as expired rather than as indefinite. Every slab "
     "reserved before this feature existed has no such field, so this hands "
     "all of them to the next caller at once, silently, with nothing to see "
     "until two people cut the same slab",
     SRC,
     "      if (until === undefined || until === null || until === '') return Infinity;",
     "      if (until === undefined || until === null || until === '') return 0;"),

    ("2. AN UNPARSEABLE DEADLINE FAILS OPEN: garbage in reservedUntil is read "
     "as 'expired' instead of 'cannot tell'. 'I could not read the deadline' "
     "becomes 'the deadline passed', which is the fail-open direction on a "
     "record about who owns a slab",
     SRC,
     "      if (!isFinite(t)) return Infinity;",
     "      if (!isFinite(t)) return 0;"),

    ("3. A LIVE HOLD STOPS BEING CHECKED: the lapsed test is dropped from the "
     "conflict refusal, so every reservation takes the slab whether the other "
     "hold has run out or not. This is the original double-sale, restored",
     SRC,
     "      if (action === 'reserve' && curStatus === 'reserved' && curWho && curWho !== who && !lapsed) {",
     "      if (action === 'reserve' && curStatus === 'reserved' && curWho && curWho !== who && lapsed) {"),

    ("4. THE CALLER'S OWN reservedUntil IS TRUSTED instead of overwritten by "
     "the server's clock. Nothing refuses and nothing logs; what changes is "
     "that a client can back-date somebody else's hold and take the slab",
     SRC,
     "        status: 'reserved', reservedFor: who, reservedUntil: reservedUntil\n      });\n      delete merged.holdMinutes;",
     "        status: 'reserved', reservedFor: who\n      });\n      delete merged.holdMinutes;"),

    ("5. holdMinutes IS COERCED RATHER THAN REFUSED -- the Number('') shape "
     "this platform has already paid for. An empty string becomes 0 and 'abc' "
     "becomes NaN, and either one reaches Date as a hold that expired before "
     "it was made",
     SRC,
     "        if (!isFinite(n) || n <= 0 || n > HOLD_MINUTES_MAX || Math.floor(n) !== n) {",
     "        if (false) {"),

    ("6. RELEASE BECOMES A WAY TO TAKE A SLAB: the not-your-hold refusal is "
     "dropped, so release-then-reserve clears somebody else's live hold and "
     "the compare-and-swap never sees a conflict because there is not one "
     "left to see",
     SRC,
     "        if (curStatus === 'reserved' && curWho && curWho !== who && !lapsed) {\n          const err = {\n            code: 'NOT_YOUR_HOLD',",
     "        if (false) {\n          const err = {\n            code: 'NOT_YOUR_HOLD',"),

    ("7. A TAKEOVER GOES SILENT: the slab is still taken from the lapsed "
     "holder, correctly, but nobody is told. The customer on the other quote "
     "has not necessarily heard that their hold ran out, and the salesperson "
     "standing here is the only person who can do anything about it",
     SRC,
     "      const tookOverFrom = (lapsed && curWho && curWho !== who) ? curWho : null;",
     "      const tookOverFrom = null;"),

    ("8. A RELEASE INSERTS A ROW for a slab the server has never seen -- a "
     "request asking for the ABSENCE of state creates state, and a slab that "
     "was never reserved anywhere acquires a server record saying so",
     SRC,
     "        if (action === 'release') {\n          res.status(200).json({ ok: true, data: null, released: false,",
     "        if (false) {\n          res.status(200).json({ ok: true, data: null, released: false,"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title=('StoneDesk slab holds: a reservation must expire on the '
               'SERVER\'s clock, an absent deadline must never read as '
               'expired, and release must not become a way to take a slab'),
        # api/_resources/shared.js IS STAGED TOO, and the baseline arm is what
        # said so. 'release' is granted there, not in api/sd-data.js: without
        # it the verb is unknown, every release answers 400 rather than
        # reaching the branch under test, and the baseline goes red for a
        # reason that has nothing to do with any mutation below.
        stage=(SUITE, SRC, os.path.join('api', '_resources', 'shared.js'))))
