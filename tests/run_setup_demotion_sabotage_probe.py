"""api/_lib/setup-demotion-guard.test.js must REFUSE, not merely agree.

Run: python tests/run_setup_demotion_sabotage_probe.py

# REQUIREMENT: the suite guarding the setup demotion route must go RED when the
#   guard stops refusing, when it is moved BEHIND the write it exists to
#   prevent, when an INACTIVE holder starts counting as cover, when it starts
#   refusing a promotion or a PIN reset, when an unreadable roster becomes a
#   silent allow, and when any ONE of the four endpoints stops calling it

WHAT WAS OPEN. setActive() refuses DEACTIVATING the last holder of a sole role
and says nothing about CHANGING that holder's role. Every `setup` on this
platform upserts on (license_hash, employee_id) writing the role column, so the
same end state -- zero active owners, bootstrap still answering 409 because it
does not filter on active -- was one call away through a door nothing watched.

MEASURED BEFORE THE FIX: 17 setup paths across api/*-auth.js, ONE guarded
(api/sf-auth.js), 16 not, and FOUR reachable -- grd, sb, scp and sd each name a
SOLE_ROLE and each upsert a role. Those four are the same apps hardened against
DEACTIVATION hours earlier, which is the point: hardening one route is not
hardening the state.

── WHY THE PER-ENDPOINT ARMS ARE THE ONES TO KEEP ─────────────────────────
A shared guard can be perfect and unwired. Arms 6 to 9 remove the call from ONE
endpoint at a time, leaving the guard itself and the other three intact, which
is exactly how this gap would return: somebody restructures one setup path.

── AND ARM 4 IS WHY ARM 1 IS NOT ENOUGH ───────────────────────────────────
A guard that refused every setup would satisfy every "the demotion is refused"
arm and break provisioning entirely. The suite drives the promotion, the PIN
reset, the two-owner case and the non-owner case so a blanket refusal fails.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', '_lib', 'setup-demotion-guard.test.js')
LIB = os.path.join('api', '_lib', 'employee-lifecycle.js')
# sf-auth.js joined this list on 2026-09-22, when its INLINE copy of the guard
# was folded onto the shared function. It wrote the check first and was the one
# app the per-endpoint arms could not speak for; now it is a caller like the
# other four and a mutation that drops its call must go red like theirs.
APPS = [os.path.join('api', a) for a in
        ('grd-auth.js', 'sb-auth.js', 'scp-auth.js', 'sd-auth.js', 'sf-auth.js')]

REFUSE = """  if (target && target.active === true && target.role === sole
      && activeSole.length <= 1) {"""

CALL_HEAD = "      const demote = await lifecycle.soleRoleDemotionRefusal({"

MUTATIONS = [
    ("1. THE GUARD STOPS REFUSING -- it runs, it reads the roster, and it lets "
     "the demotion through anyway, which is the state all four apps were in "
     "until 2026-09-21",
     LIB, REFUSE,
     "  if (false && target && target.active === true && target.role === sole\n"
     "      && activeSole.length <= 1) {"),

    ("2. AN INACTIVE HOLDER COUNTS AS COVER -- one deactivated owner on the "
     "roster is enough to let the only ACTIVE one be demoted, which is the "
     "same off-by-one set_active was written to avoid",
     LIB,
     "  const activeSole = all.filter((x) => x.active === true && x.role === sole);",
     "  const activeSole = all.filter((x) => x.role === sole);"),

    ("3. THE GUARD REFUSES A PROMOTION TOO -- provisioning a new owner is "
     "blocked by the check that exists to keep one, and the roster is read on "
     "every setup for an answer that cannot be no",
     LIB,
     "  if (ctx.newRole === sole) { return null; }",
     "  if (false) { return null; }"),

    ("4. AN UNREADABLE ROSTER BECOMES A SILENT ALLOW -- could-not-tell folded "
     "into permitted, on the one call that can empty a licence",
     LIB,
     "  if (!r.ok) { return { upstream: r.detail }; }",
     "  if (!r.ok) { return null; }"),

    ("5. A soleRole NAMING NO REAL ROLE IS COUNTED AS ZERO HOLDERS instead of "
     "refused -- the misconfiguration hole reappearing on the demotion route",
     LIB,
     "  if (roles.indexOf(sole) === -1) {\n"
     "    return refusal(500, 'GUARD_MISCONFIGURED',",
     "  if (false) {\n"
     "    return refusal(500, 'GUARD_MISCONFIGURED',"),
]

# ONE ENDPOINT AT A TIME. The guard stays correct and the other three stay
# wired, which is the shape a restructured setup path would actually have.
for app in APPS:
    MUTATIONS.append((
        "%d. %s STOPS CALLING THE GUARD -- the shared function is intact and "
        "the other three still use it, so nothing about the helper looks wrong"
        % (len(MUTATIONS) + 1, os.path.basename(app)),
        app, CALL_HEAD,
        "      const demote = null && await lifecycle.soleRoleDemotionRefusal({"))

MUTATIONS.append((
    "%d. ONE APP'S REFUSAL SENTENCE IS REPLACED BY ANOTHER'S -- the guard "
    "still refuses, the status and the code are unchanged, and a SAIRNfreedom "
    "governing officer is told to add an Owner to a shop"
    % (len(MUTATIONS) + 1),
    os.path.join('api', 'sf-auth.js'),
    "        soleMessage: 'This is the only active governing officer on this license. '",
    "        soleMessage: 'This is the only active Owner on this license. '"))

# ── AND OMITTING IT ALTOGETHER IS A REFUSAL, NOT A GENERIC SENTENCE ───────
# The first design defaulted the message. tools/sairn_seam_check.py refused the
# push for exactly that -- a field that falls back to a default is SILENT, and
# silent is how a refusal reaches a customer in words their app does not use.
# The engine now refuses 500 GUARD_MISCONFIGURED instead, so this mutation
# checks the suite notices a caller that stops passing one at all.
MUTATIONS.append((
    "%d. A CALLER STOPS PASSING ITS REFUSAL SENTENCE -- under the first design "
    "that was a generic message nobody would notice; it is now a refusal that "
    "names itself, and the suite has to see the difference"
    % (len(MUTATIONS) + 1),
    os.path.join('api', 'grd-auth.js'),
    "        soleMessage: 'This is the only active Owner on this license. Changing their role '",
    "        _dropped: 'This is the only active Owner on this license. Changing their role '"))

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='SAIRN: demoting the last holder of a sole role must be refused on '
          'the SETUP route too -- on all four apps, before the write, and '
          'without refusing a promotion or a PIN reset',
    # api/_lib/auth.js is staged 2026-09-24 because the file(s) above now
    # call roleSet() from it -- the platform-wide null-prototype role-map
    # sweep. The worktree is at HEAD, so an UNSTAGED DEPENDENCY of a staged
    # file dies at require() and the BASELINE goes red before any mutation
    # is planted. Same gap as an unstaged file. Full account: api/_lib/auth.js.
    stage=tuple([LIB] + APPS + [os.path.join('api', '_lib', 'auth.js')]),
))
