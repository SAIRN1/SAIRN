"""api/_lib/last-admin-sole-role.test.js must REFUSE a soleRole that names nothing.

Run: python tests/run_solerole_validation_sabotage_probe.py

# REQUIREMENT: the suite guarding the shared last-admin engine must go RED when
#   a soleRole naming no real role stops being refused, when the refusal is
#   moved BEHIND the roster read so an unreachable store can mask it, when the
#   check is inverted so a VALID soleRole is refused instead, when a falsy
#   soleRole starts being treated as a typo, and when the refusal stops naming
#   the value that caused it

WHAT WAS OPEN. `setActive()` narrows the last-admin count to `[soleRole]` when
an app names one, and nothing checked that the name was real. THE FAILURE WAS
PERMISSIVE, which is the opposite of what the one comment describing this
scenario said: guardRoles matches no row, activeProvisioners counts ZERO, and
the refusal condition also tests `guardRoles.indexOf(target.role) !== -1` --
false for every real row -- so the branch is UNREACHABLE.

REPRODUCED before the fix, driving the real engine: roster of one `post.govern`
and one `post.govern.deputy`, soleRole `'post.governor'` (one letter), caller
the deputy, target the governor -> **200 and the PATCH IS SENT**. The licence
reaches zero governors and bootstrap still 409s, which is the SD-AUDIT-2026
trapdoor arriving through a typo rather than through a missing guard.

FIVE ENDPOINTS pass this value as a hand-written literal.

── WHY ARM 2 IS THE ONE TO KEEP ───────────────────────────────────────────
A validation that runs AFTER the roster read is refused by no status assertion
at all -- the status is still 500 and the code is still GUARD_MISCONFIGURED.
What changes is that an unreachable store now answers first, so a
misconfiguration is reported as an upstream error and the real cause never
surfaces. The suite counts reads on the refused path for exactly that reason.

── AND ARM 4 IS WHY ARM 1 IS NOT ENOUGH ───────────────────────────────────
Refusing every soleRole would satisfy "a typo is refused" and break the nine
callers that pass null. The suite drives the falsy case and the valid case in
both directions so a blanket refusal cannot pass.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', '_lib', 'last-admin-sole-role.test.js')
LIB = os.path.join('api', '_lib', 'employee-lifecycle.js')

GUARD = """  if (ctx.soleRole && roles.indexOf(ctx.soleRole) === -1) {
    return refusal(500, 'GUARD_MISCONFIGURED',"""

MUTATIONS = [
    ("1. THE VALIDATION IS REMOVED -- the state of this engine until "
     "2026-09-21, in which one mistyped letter in any of five endpoints turns "
     "the last-admin guard off and nothing says so",
     LIB, GUARD,
     "  if (false) {\n"
     "    return refusal(500, 'GUARD_MISCONFIGURED',"),

    ("2. THE VALIDATION MOVES BEHIND THE ROSTER READ -- the status and the "
     "code are unchanged, so every code assertion still passes; what changes "
     "is that an unreachable store answers first and the misconfiguration is "
     "reported as an upstream error",
     LIB,
     "  if (ctx.soleRole && roles.indexOf(ctx.soleRole) === -1) {",
     "  if (ctx.soleRole && roles.indexOf(ctx.soleRole) === -1 && ctx._rosterRead) {"),

    ("3. THE CHECK IS INVERTED -- a VALID soleRole is refused and a typo is "
     "let through, which is the same hole wearing the opposite sign",
     LIB,
     "  if (ctx.soleRole && roles.indexOf(ctx.soleRole) === -1) {",
     "  if (ctx.soleRole && roles.indexOf(ctx.soleRole) !== -1) {"),

    ("4. A FALSY soleRole IS TREATED AS A TYPO -- every one of the nine "
     "callers passing null is refused 500, which is a lockout wearing a "
     "safety check",
     LIB,
     "  if (ctx.soleRole && roles.indexOf(ctx.soleRole) === -1) {",
     "  if (roles.indexOf(ctx.soleRole) === -1) {"),

    ("5. THE REFUSAL STOPS NAMING THE VALUE THAT CAUSED IT -- the request is "
     "still refused and the operator is told a guard failed without being "
     "told which literal to fix, in a file five endpoints share",
     LIB,
     "      'The last-admin guard cannot run: this app names ' + JSON.stringify(ctx.soleRole)\n"
     "      + ' as the role a license must never lose, and that is not one of its '\n"
     "      + 'provisioning roles ' + JSON.stringify(roles) + '. Refusing rather than '",
     "      'The last-admin guard cannot run because it is misconfigured'\n"
     "      + '. Refusing rather than '"),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='SAIRN: a soleRole that names no real role must fail CLOSED and say '
          'which value is wrong -- before the roster is read, and without '
          'refusing the nine callers that name no sole role at all',
    stage=(LIB,),
))
