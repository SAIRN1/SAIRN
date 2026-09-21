"""tests/stonedesk_exec_msgs_gate.js must REFUSE, not merely agree.

Run: python tests/run_exec_msgs_gate_sabotage_probe.py

WHY. The suite it drives is a same-hour regression suite for a SECURITY gate --
StoneDesk's private CEO/CFO/CTO channel was readable and writable by anyone
holding the shared fabrication-shop licence key. A suite written beside its own
fix has never been observed red, and "11 passed" is a statement about the suite
agreeing with the code, not about the suite being able to disagree with it. The
platform measured what that is worth on 2026-09-15: 7 of 154 JavaScript suites
had a negative control, and 67 of the 147 without one guarded a Tier A resource.

Same six directions cc's tests/run_leg_session_gate_sabotage_probe.py uses,
because they are the six ways a session gate stops being one, plus the role
half this gate has and that one does not.

EVERY MUTATION RUNS IN A THROWAWAY WORKTREE built at HEAD, with the SUBJECT
staged in from this clone -- the gate is not committed when this first runs, and
a baseline that went red for that reason would be measuring the wrong thing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'stonedesk_exec_msgs_gate.js')
API = os.path.join('api', 'sd-data.js')

GATE_READ = "      if (resource === 'sd_exec_msgs' && !sdExecGate(res)) return;\n"

MUTATIONS = [
    ("1. THE GATE IS GONE from the read path -- the smallest possible diff, and "
     "the private executive channel is a licence key away again",
     API,
     GATE_READ + "      // SOFT-DELETED ROWS ARE NOT RETURNED.",
     "      // SOFT-DELETED ROWS ARE NOT RETURNED."),

    ("2. the gate runs and does not REFUSE -- it returns a session-shaped object "
     "for a caller with no session, so every call site's `!sdExecGate(res)` "
     "stops firing while the gate still looks present",
     API,
     "      if (!s) {\n"
     "        response.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } });\n"
     "        return null;\n"
     "      }",
     "      if (!s) { return { role: 'owner', employee_id: 'nobody' }; }"),

    ("3. the APP SCOPING is dropped, so a valid session for any other SAIRN app "
     "satisfies StoneDesk's executive gate (Guardian Check 28)",
     API,
     "      const s = verifySessionToken(tokenFromRequest(req), licHash, 'stonedesk');",
     "      const s = verifySessionToken(tokenFromRequest(req), licHash);"),

    ("4. the ROLE half is dropped -- any signed-in employee, including a "
     "fabricator or an installer, reads the executive channel",
     API,
     "      if (s.role !== 'owner' && s.role !== 'admin') {",
     "      if (false) {"),

    # ANCHORED ON THE BRANCH LINE, NOT ON `const idCol`. The first spelling used
    # the gate line plus `const idCol = SD_LOCAL_RESOURCES[resource];`, which is
    # byte-identical in the write branch AND the soft_delete branch -- the
    # harness reported ANCHOR-2 and refused rather than letting replace() pick
    # which of the two paths to damage. That refusal is the harness working: a
    # mutation that lands somewhere the label does not name proves nothing.
    ("5. the WRITE path alone loses the gate, so the channel is still private to "
     "read and open to write -- the half-applied fix a hurried edit produces",
     API,
     "    if (SD_LOCAL_RESOURCES[resource] && action === 'write') {\n" + GATE_READ,
     "    if (SD_LOCAL_RESOURCES[resource] && action === 'write') {\n"),

    ("6. the gate is moved BEHIND the query -- it still answers 401, but only "
     "after the private messages have been read out of the database",
     API,
     GATE_READ + "      // SOFT-DELETED ROWS ARE NOT RETURNED. The marker lives inside `data`, so",
     "      // SOFT-DELETED ROWS ARE NOT RETURNED. The marker lives inside `data`, so"),
]

# Mutation 6 needs its refusal to still happen, just too late -- otherwise it is
# mutation 1 wearing a different label. The second edit puts the gate back after
# the fetch, so the arm asserting 401 stays satisfied and ONLY an arm that looks
# at WHERE the refusal happened can catch it.
MUTATIONS[5] = (
    MUTATIONS[5][0], API,
    GATE_READ
    + "      // SOFT-DELETED ROWS ARE NOT RETURNED. The marker lives inside `data`, so\n"
      "      // the filter is on the jsonb field rather than a column. A row that has\n"
      "      // never been soft-deleted has no `_deleted_at` key at all and `->>`\n"
      "      // yields NULL for it, so `is.null` matches every pre-existing row --\n"
      "      // this filter changes nothing for data written before it existed.\n"
      "      const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) +\n"
      "        '&data->>_deleted_at=is.null&select=data'), { headers });",
    "      // SOFT-DELETED ROWS ARE NOT RETURNED. The marker lives inside `data`, so\n"
    "      // the filter is on the jsonb field rather than a column. A row that has\n"
    "      // never been soft-deleted has no `_deleted_at` key at all and `->>`\n"
    "      // yields NULL for it, so `is.null` matches every pre-existing row --\n"
    "      // this filter changes nothing for data written before it existed.\n"
    "      const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) +\n"
    "        '&data->>_deleted_at=is.null&select=data'), { headers });\n"
    "      if (resource === 'sd_exec_msgs' && !sdExecGate(res)) return;")

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='StoneDesk sd_exec_msgs gate -- the suite must refuse six ways of '
              'un-gating a private executive channel',
        # The gate is not committed when this first runs; the worktree is built
        # at HEAD, so without this the baseline measures the UNFIXED file.
        stage=(API,)))
