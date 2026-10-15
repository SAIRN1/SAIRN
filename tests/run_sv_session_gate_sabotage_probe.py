"""api/sd-data-sv-session-gate.test.js must REFUSE, not merely agree.

Run: python tests/run_sv_session_gate_sabotage_probe.py

# REQUIREMENT: the suite guarding SAIRNvet's session gate must go RED when the
#   gate is removed, when it is moved BEHIND the query so a refused request
#   has already read the rows, when it stops being scoped to the app, when it
#   covers one branch and not the other, when it lands AFTER the pre-existing
#   sv_controlled witness lock instead of before it, or when the client half
#   that makes it survivable is reverted -- because a gate that is present and
#   wrong looks exactly like a gate that works

WHAT WAS OPEN. Until 2026-09-21 (hover2) SV_RESOURCES had no session gate at
all in api/sd-data.js, and the comment above it said so was NOT an omission:
"SAIRNvet has no per-employee authentication at all... a session gate here
would gate on a session that does not exist." That was true when written and
false for 8 days by the time this landed -- api/sv-auth.js, ROLES_BY_APP.
sairnvet, AUTH_TABLE_BY_APP.sairnvet and sql/sairnvet_employee_auth_schema.sql
all shipped 2026-09-13 (29b1f1d5). Reproduced against the shipped file with a
valid key and NO X-SD-Auth header: sv_controlled read answered 200 with rows,
sv_patients write answered 200 having upserted. 41 tables, including the
DEA-relevant controlled-substance register and its own patient records.

── WHY THE "MOVED BEHIND THE QUERY" ARM IS THE ONE TO KEEP ────────────────
A gate that answers 401 after the fetch has already run is the shape that
passes every status-code assertion and leaks anyway. The suite counts fetch()
calls on a refused request for exactly that reason.

── AND WHY THERE IS A SEVENTH ARM THE LEG PROBE DOES NOT NEED ─────────────
sv_controlled already carried an independent witness-token requirement
(api/sv-witness.js, 2026-09-13) on its write path before this session gate
existed. The new gate has to run BEFORE that check, not merely alongside it --
an unauthenticated caller should be refused for having no session, not merely
for lacking a witness token, which is a weaker and orthogonal claim. Arm 7
proves the ordering rather than assuming it from the diff.

── AND THE CLIENT HALF IS SABOTAGED TOO ───────────────────────────────────
svData() sent ONLY the licence key on all 14 of its call sites; svAuthCall(),
a DIFFERENT function used only for the auth endpoint itself, already attached
the session header. Reverting the one added line turns the gate into an
outage on every read and write in the app, which is the failure most likely
to get a security fix rolled back rather than fixed forward.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-sv-session-gate.test.js')
SD = os.path.join('api', 'sd-data.js')
APP = 'sairnvet.html'

GATE = ("    if (SV_RESOURCES[resource]) {\n"
        "      const svSess = verifySessionToken(tokenFromRequest(req), licHash, 'sairnvet');\n"
        "      if (!svSess) {")

MUTATIONS = [
    ("1. THE GATE IS REMOVED -- the state of this file until 2026-09-21, in "
     "which a bare licence key reads the DEA-relevant controlled-substance "
     "register",
     SD, GATE,
     "    if (false) {\n"
     "      const svSess = verifySessionToken(tokenFromRequest(req), licHash, 'sairnvet');\n"
     "      if (!svSess) {"),

    ("2. THE GATE STOPS REFUSING -- it runs, it verifies, and it lets a null "
     "session through anyway",
     SD,
     "      if (!svSess) {\n"
     "        res.status(401).json({ error: { code: 'NO_SESSION', message: 'Your sign-in could not be verified, so nothing was read or saved. Sign out and sign in again, then try once more.' } });",
     "      if (false) {\n"
     "        res.status(401).json({ error: { code: 'NO_SESSION', message: 'Your sign-in could not be verified, so nothing was read or saved. Sign out and sign in again, then try once more.' } });"),

    ("3. THE APP SCOPING IS DROPPED -- a valid session for ANY other app now "
     "reads and writes these tables, the Check 28 collision",
     SD,
     "      const svSess = verifySessionToken(tokenFromRequest(req), licHash, 'sairnvet');",
     "      const svSess = verifySessionToken(tokenFromRequest(req), licHash);"),

    ("4. THE GATE COVERS THE WRITE BRANCH ONLY -- the read is open again, "
     "which is the half that leaks rather than the half that changes them",
     SD, "    if (SV_RESOURCES[resource]) {",
     "    if (SV_RESOURCES[resource] && action === 'write') {"),

    # THE FRONT GATE IS REMOVED AND A LATE ONE PUT IN ITS PLACE, in one
    # replacement, because a mutation that only ADDS the late check and
    # leaves the front gate standing tests nothing -- the real guard is still
    # there and the arm goes silent.
    ("5. THE GATE MOVES BEHIND THE QUERY -- it answers 401 having already "
     "read the rows, which passes every status-code assertion and leaks "
     "anyway",
     SD,
     # ── ANCHOR RE-DERIVED 2026-09-25, AND AGAIN 2026-10-15 ──────────────
     # FIRST ROT: this quoted the read's QUERY LINE, which gained a
     # `Prefer: count=exact` header on 2026-09-24 (the truncation-disclosure
     # fix) -- so the anchor matched nothing and the arm sat ANCHOR-0 red on
     # main while looking armed. The 2026-09-25 fix quoted the whole gate
     # block plus the read branch's opening line instead.
     #
     # SECOND ROT, AND THE SAME CAUSE ONE LEVEL UP: on 2026-10-14 the gate
     # block GREW -- fourth b15's role table (`svRoles.decide`) and the
     # append-only check landed INSIDE it, taking it from 6 lines to about 68.
     # The anchor quoted the 6-line version, so it matched nothing again and
     # both this arm and arm 7 went ANCHOR-0, reporting as if the live gate
     # had moved when the mutation had never been applied at all. b15's
     # triage then read that label as a statement about api/ and nearly
     # routed it to hank.
     #
     # THE LESSON TAKEN THIS TIME IS NOT A SHORTER BLOCK, IT IS NO BLOCK.
     # Two short anchors on the two SITES the property is about, as a paired
     # mutation, so neither anchor contains anything that is free to grow
     # between them:
     #   edit 1 -- the front gate stops covering reads
     #   edit 2 -- a 401 appears in the read branch AFTER the fetch has run
     # That is exactly "answers 401 having already read the rows", and the
     # suite's fetch-count-on-a-refused-request assertion is what must catch
     # it.
     ["    if (SV_RESOURCES[resource]) {\n      const svSess = verifySessionToken(tokenFromRequest(req), licHash, 'sairnvet');",
      "      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true, total: total });"],
     ["    if (SV_RESOURCES[resource] && action !== 'read') {\n      const svSess = verifySessionToken(tokenFromRequest(req), licHash, 'sairnvet');",
      "      if (!verifySessionToken(tokenFromRequest(req), licHash, 'sairnvet')) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'no' } }); return; }\n      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true, total: total });"]),

    ("6. [CLIENT] THE TRANSPORT STOPS SENDING THE TOKEN -- the gate becomes "
     "an outage on all 14 call sites, which is how a security fix gets "
     "reverted instead of fixed forward",
     APP,
     "  var svTokNow = svTok();\n  if (svTokNow) headers['X-SD-Auth'] = svTokNow;",
     "  var svTokNow = svTok();"),

    # THE ORDERING ARM SPECIFIC TO SV: the pre-existing witness lock must not
    # become a stand-in for the session gate. Swapping the two so the witness
    # check runs FIRST would still refuse an unauthenticated sv_controlled
    # write (403, not 401) and every OTHER resource in the map would go
    # straight through with no session check at all, because the witness
    # module only knows about sv_controlled.
    ("7. THE SESSION GATE MOVES AFTER THE WITNESS LOCK -- sv_controlled still "
     "refuses an unauthenticated write, for the WRONG reason, and the other "
     "forty resources lose their gate entirely",
     SD,
     # ── RE-DERIVED 2026-10-15, SAME ROT AS ARM 5 ────────────────────────
     # This quoted the same 6-line gate block, which grew to ~68 lines on
     # 2026-10-14, so the arm was ANCHOR-0 and its label -- "THE SESSION GATE
     # MOVES AFTER THE WITNESS LOCK" -- was a mutation that had never been
     # applied. Re-derived as two short anchors on the two sites:
     #   edit 1 -- the front gate stops covering writes
     #   edit 2 -- the session check reappears in the write branch, AFTER
     #             svWitness.requireWitness has already answered
     # Which is the ordering the arm exists to prove: an unauthenticated
     # sv_controlled write is then refused for lacking a WITNESS rather than
     # for lacking a session, and the other forty resources -- which the
     # witness module knows nothing about -- lose their gate entirely.
     ["    if (SV_RESOURCES[resource]) {\n",
      "      if (refusal) { res.status(refusal.status).json(refusal.body); return; }\n"],
     ["    if (SV_RESOURCES[resource] && action === 'read') {\n",
      "      if (refusal) { res.status(refusal.status).json(refusal.body); return; }\n      if (!verifySessionToken(tokenFromRequest(req), licHash, 'sairnvet')) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'no' } }); return; }\n"]),
]

# ── WHY THERE IS A __main__ GUARD HERE AS OF 2026-10-15 ───────────────────
# There was not one, and `sys.exit(run_probe(...))` sat at module level. So
# IMPORTING this file -- which any inventory tool, test collector or triage
# script does -- drove a full seven-arm sabotage run that writes
# api/sd-data.js in place, and then called sys.exit() on the importer. Found
# by doing exactly that during b17's anchor audit: a read-only uniqueness
# check on the mutation list executed the probe instead. The run restored the
# file and said so, which is the only reason this was a scare rather than an
# incident. Every other probe in tests/ carries the guard; this one was the
# exception.
if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNvet: 41 tables including the DEA-relevant controlled-substance '
              'register must require an employee session -- on BOTH verbs, BEFORE '
              'the query, BEFORE the pre-existing witness lock, and scoped to this '
              'app',
        stage=(SD, APP),
    ))
