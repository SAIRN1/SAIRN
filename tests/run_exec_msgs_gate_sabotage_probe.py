"""tests/stonedesk_exec_msgs_gate.js must REFUSE, not merely agree.

Run: python tests/run_exec_msgs_gate_sabotage_probe.py

WHY. The suite it drives is a same-hour regression suite for a SECURITY gate --
StoneDesk's private CEO/CFO/CTO channel was readable and writable by anyone
holding the shared fabrication-shop licence key. A suite written beside its own
fix has never been observed red, and "11 passed" is a statement about the suite
agreeing with the code, not about the suite being able to disagree with it. The
platform measured what that is worth on 2026-09-15: 7 of 154 JavaScript suites
had a negative control, and 67 of the 147 without one guarded a Tier A resource.

Six of the eight are the directions cc's
tests/run_leg_session_gate_sabotage_probe.py uses, because they are the ways a
session gate stops being one, adapted for the role half this gate has and that
one does not.

THE LAST TWO ARE NOT ABOUT THE CODE AT ALL, and they are the reason this probe
is longer than its sibling. This resource's protection has two halves: the gate
in api/sd-data.js, and its Tier A row in docs/CRITICALITY-TIERS.md, which is
where tools/tier_a_review_gate.py takes its Tier A set from and nowhere else.
Reverting that one cell to B costs a character, changes no code, and silently
stops every future edit to the private executive channel from requiring an
independent review. It sat at B for eleven days on "an internal message lost"
and that sentence is a large part of why nobody asked who could read it.

EVERY MUTATION RUNS IN A THROWAWAY WORKTREE built at HEAD, with the SUBJECT
staged in from this clone -- the gate is not committed when this first runs, and
a baseline that went red for that reason would be measuring the wrong thing.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'stonedesk_exec_msgs_gate.js')
API = os.path.join('api', 'sd-data.js')
TIERS = os.path.join('docs', 'CRITICALITY-TIERS.md')

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROWS = [ln for ln in io.open(os.path.join(_REPO, TIERS), encoding='utf-8')
         if ln.startswith('| `sd_exec_msgs` |')]
if len(_ROWS) != 1:
    print('CANNOT RUN: %s holds %d sd_exec_msgs rows, not 1 -- the register half '
          'of this probe cannot be aimed and a probe that cannot be aimed is not '
          'a pass.' % (TIERS, len(_ROWS)))
    sys.exit(3)
_EXEC_ROW = _ROWS[0].rstrip('\n')

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

# ── THE REGISTER HALF (2026-09-21) ─────────────────────────────────────────
# The gate in the code is only half of what keeps this resource protected. The
# OTHER half is its Tier A row: tools/tier_a_review_gate.py reads its Tier A set
# from docs/CRITICALITY-TIERS.md and nowhere else, so that one cell is what
# makes the next change to sd_exec_msgs require an independent review. Reverting
# it costs one character, changes no code, and would have been invisible --
# criticality_tier_check.py verifies that a row HAS a tier and that A rows carry
# evidence, never that a resource is rated right. These two arms exist because
# the B rating is what made the missing gate look acceptable for eleven days.
MUTATIONS += [
    ("7. the TIER IS QUIETLY REVERTED to B -- no code changes, and every future "
     "edit to the private executive channel stops requiring a review",
     TIERS,
     '| `sd_exec_msgs` | **A** |',
     '| `sd_exec_msgs` | **B** |'),

    ("8. the A row keeps its tier and LOSES ITS EVIDENCE -- a tier asserted with "
     "nothing to check it against is a label, and the register's own rule says "
     "so",
     TIERS,
     _EXEC_ROW,
     '| `sd_exec_msgs` | **A** | A private executive message read, altered or '
     'deleted by somebody it was never for | |'),
]

# ── MUTATION 8 IS BUILT FROM THE FILE, NOT TYPED ───────────────────────────
# The first spelling replaced the opening words of the evidence cell with a
# placeholder and left the rest of it in place, so the cell was still long and
# the arm's `length > 40` check was still satisfied. The probe reported SILENT
# and it was RIGHT: the mutation did not do what its label said. Reading the
# real row and rebuilding it with an EMPTY evidence cell is the only spelling
# that plants the defect the label describes -- and it stays correct when the
# evidence prose is later edited, which a typed copy would not.

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='StoneDesk sd_exec_msgs gate -- the suite must refuse eight ways of '
              'un-gating a private executive channel, in the code AND in the '
              'register that gates its reviews',
        # The gate is not committed when this first runs; the worktree is built
        # at HEAD, so without this the baseline measures the UNFIXED file. The
        # register is staged for the same reason -- the re-tier and the arm
        # asserting it land together, so at HEAD the row still reads B and the
        # baseline would go red against a document nobody had changed yet.
        # api/_lib/auth.js joined 2026-09-24: api/sd-data.js now calls
        # roleSet() from it (the platform-wide null-prototype role-map
        # sweep), so a staged sd-data.js run against a HEAD copy of auth.js
        # that does not export it dies at require() and the baseline goes red
        # for a reason that has nothing to do with the exec channel. An
        # unstaged DEPENDENCY of a staged file is the same gap as an unstaged
        # file.
        stage=(API, TIERS, os.path.join('api', '_lib', 'auth.js'))))
