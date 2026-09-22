r"""tools/criticality_tier_check.py must handle BOTH tier-table shapes, and must
refuse the ways the two-axis migration can go wrong.

Run: python tests/run_two_axis_tier_parser_probe.py

WHY A FIXTURE AND NOT THE LIVE FILE. Step 1 of the migration plan
(docs/2026-09-21-criticality-tiers-two-axis-spec.md §3.4) lands the parser
BEFORE any row moves, so on the live file every new branch is dead: 387 rows in
the old shape, 0 migrated. A control that ran only against the live table would
report a confident pass over code that has never executed -- the exact shape
this platform keeps recording. Every arm here drives a constructed table
instead, with the checker pointed at it.

THE ARM THAT MATTERS MOST IS 3. hover2 found, before a single row moved, that
parse() told a rollup row from a resource row by CELL COUNT -- and the new
resource shape has six cells, exactly like a rollup. A migrated row would have
fallen into the rollup branch and had its confidentiality letter read as a
resource COUNT: a mis-parse, not a crash, so nothing would have said so. The
fix disambiguates on cell 1's own shape. This arm is what stops that fix being
quietly undone.
"""
import io
import os
import re
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'criticality_tier_check.py')

HEADER = '''# Criticality tiers -- fixture

## Rollup -- one line per app

| App | Registered resources | A | B | C | Status |
|---|---|---|---|---|---|
| `fixtureapp` | 2 | **1** | 1 | 0 | **RE-TIERED** -- fixture |

## `fixtureapp` -- all 2 registered resources

'''

OLD_HDR = '| Resource | Tier | Worst consequence if it is wrong | Evidence |\n|---|---|---|---|\n'
NEW_HDR = ('| Resource | Tier | Confidentiality | Worst consequence if it is wrong or lost '
           '| Worst consequence if it is read by the wrong person | Evidence |\n'
           '|---|---|---|---|---|---|\n')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(table_body, header):
    """Point the checker at a constructed register and return its output."""
    d = tempfile.mkdtemp(prefix='sairn-2axis-')
    path = os.path.join(d, 'CRITICALITY-TIERS.md')
    io.open(path, 'w', encoding='utf-8', newline='\n').write(HEADER + header + table_body)
    env = dict(os.environ, SAIRN_TIER_REGISTER=path)
    r = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                       cwd=REPO, env=env)
    return (r.stdout or '') + (r.stderr or '')


print('two-axis tier parser -- both shapes, and the ways the migration breaks\n')

# The checker resolves its register path at import time; if it does not honour
# an override this probe cannot drive it at all, and that is COULD NOT RUN
# rather than a pass.
src = io.open(TOOL, encoding='utf-8').read()
if 'SAIRN_TIER_REGISTER' not in src:
    print('COULD NOT RUN: tools/criticality_tier_check.py has no register override, '
          'so this probe cannot point it at a fixture. Nothing was verified.')
    sys.exit(3)

OLD_ROWS = ('| `alpha_one` | **A** | money moves wrongly | Evidence for alpha |\n'
            '| `alpha_two` | **B** | operational data lost | rule |\n')
NEW_ROWS = ('| `alpha_one` | **A** | **A** | money moves wrongly | read by a competitor '
            '| Evidence for alpha |\n'
            '| `alpha_two` | **B** | **B** | operational data lost | nothing elevated | rule |\n')

# ── WHAT THESE ARMS ASSERT, AND WHAT THEY DELIBERATELY DO NOT ─────────
# A constructed table names an app that has no api/_resources/*.js, so the
# app-vs-registry checks (NO ROLLUP / GONE / NOT A RESOURCE) fire on every
# fixture by construction. Asserting PROBLEMS:0 here would be asserting that a
# synthetic app is a real one -- the first spelling of these arms did exactly
# that and failed for a reason that had nothing to do with the parser.
# What is asserted instead is the PARSER's own output: how many resource rows
# it found, how many it read as migrated, and the ABSENCE of the specific
# row-level problem classes this change introduces.
ROW_PROBLEMS = ('BAD TIER', 'BAD CONFIDENTIALITY', 'COMPUTED TIER MISMATCH',
                'NO EVIDENCE', 'NO WORST CASE')


def row_problems(out):
    return [k for k in ROW_PROBLEMS if k in out]


out = run(OLD_ROWS, OLD_HDR)
check('1. the OLD four-cell shape still parses and raises no row-level problem',
      'RESOURCE_ROWS:2' in out and not row_problems(out),
      'row problems: %s\n%s' % (row_problems(out), out[-400:]))
check('   ...and reports 0 of 2 migrated, so a partial migration is visible',
      'ROWS_MIGRATED_TWO_AXIS:0 of 2' in out, out[-300:])

out = run(NEW_ROWS, NEW_HDR)
check('2. the NEW six-cell shape parses, raises no row-level problem, and counts '
      'as migrated',
      'ROWS_MIGRATED_TWO_AXIS:2 of 2' in out and not row_problems(out),
      'row problems: %s\n%s' % (row_problems(out), out[-400:]))

# ── 3. the mis-parse hover2 found before a row moved ──────────────────────
# If a six-cell RESOURCE row fell into the rollup branch it would not be
# counted as a resource row at all -- RESOURCE_ROWS would drop and the migrated
# count would be 0. Both numbers together are the assertion; either alone could
# be satisfied by the wrong parse.
out = run(NEW_ROWS, NEW_HDR)
check('3. a migrated six-cell resource row is NOT swallowed by the rollup branch',
      'RESOURCE_ROWS:2' in out and 'ROWS_MIGRATED_TWO_AXIS:2 of 2' in out,
      'a six-cell resource row was read as a rollup line: ' + out[-400:])

# ── 4. the derived tier is cross-checked, not trusted ─────────────────────
MISMATCH = ('| `alpha_one` | **B** | **A** | money moves wrongly | read by a competitor '
            '| Evidence for alpha |\n'
            '| `alpha_two` | **B** | **B** | operational data lost | nothing elevated | rule |\n')
out = run(MISMATCH, NEW_HDR)
check('4. Tier B beside Confidentiality A is REFUSED -- the tier is derived',
      'COMPUTED TIER MISMATCH' in out and 'PROBLEMS:0' not in out, out[-400:])

# ── 5. evidence is required per axis ──────────────────────────────────────
NOEV = ('| `alpha_one` | **A** | **A** | money moves wrongly | read by a competitor |  |\n'
        '| `alpha_two` | **B** | **B** | operational data lost | nothing elevated | rule |\n')
out = run(NOEV, NEW_HDR)
check('5. Confidentiality-A with an empty evidence cell is REFUSED',
      'NO EVIDENCE' in out, out[-400:])

# ── 6. an unanswered read-axis is not a low one ───────────────────────────
NOREAD = ('| `alpha_one` | **A** | **A** | money moves wrongly |  | Evidence for alpha |\n'
          '| `alpha_two` | **B** | **B** | operational data lost | nothing elevated | rule |\n')
out = run(NOREAD, NEW_HDR)
check('6. a migrated row with an EMPTY read-consequence is REFUSED, because an '
      'unanswered axis is not a low one',
      'NO WORST CASE (read)' in out, out[-400:])

# ── 7. a nonsense confidentiality letter is refused rather than coerced ───
BADC = ('| `alpha_one` | **A** | **X** | money moves wrongly | read by a competitor '
        '| Evidence for alpha |\n'
        '| `alpha_two` | **B** | **B** | operational data lost | nothing elevated | rule |\n')
out = run(BADC, NEW_HDR)
check('7. a confidentiality letter outside A/B/C is REFUSED',
      'BAD CONFIDENTIALITY' in out or 'RESOURCE_ROWS:1' in out, out[-400:])

# ── 8. MIXED shapes coexist, which is the whole point of step 1 ───────────
MIXED = ('| `alpha_one` | **A** | **A** | money moves wrongly | read by a competitor '
         '| Evidence for alpha |\n'
         '| `alpha_two` | **B** | operational data lost | rule |\n')
out = run(MIXED, NEW_HDR)
check('8. one migrated row and one not-yet-migrated row coexist and BOTH parse',
      'RESOURCE_ROWS:2' in out and 'ROWS_MIGRATED_TWO_AXIS:1 of 2' in out, out[-400:])

# ── 9-11. §2.3: THE MIGRATED ROW MAY NOT CARRY THE FALSE CLAIM FORWARD ────
# The old default B sentence asserted "Employee-auth-gated" -- an ACCESS-CONTROL
# fact, not a content judgement -- and it was false for all 41 SV_RESOURCES
# rows, which have no session gate at all. The check binds to MIGRATED rows
# only, so these arms are the only thing that can execute it: the live file is
# 0-of-387 migrated and would report a confident pass over a dead branch.
GATE_CLAIM = ('| `alpha_one` | **A** | **A** | money moves wrongly | read by a competitor '
              '| Evidence for alpha |\n'
              '| `alpha_two` | **B** | **B** | operational data lost | nothing elevated '
              '| Employee-auth-gated operational data: neither money nor a regulated '
              'record |\n')
out = run(GATE_CLAIM, NEW_HDR)
check('9. a MIGRATED row still asserting "Employee-auth-gated" is REFUSED',
      'ASSERTS A GATE' in out and 'PROBLEMS:0' not in out, out[-400:])

# THE PAIRED NEGATIVE, because arm 9 alone is satisfied by a check that refuses
# every migrated row. §2.3's own replacement sentence must PASS.
CONF_B_DEFAULT = ('Internal, role-restricted data with no elevated confidentiality '
                  'class -- no PII, PHI, privileged communication, or '
                  'financial-account detail on this row. Classified by the stated B '
                  'rule rather than individually read')
CLEAN = ('| `alpha_one` | **A** | **A** | money moves wrongly | read by a competitor '
         '| Evidence for alpha |\n'
         '| `alpha_two` | **B** | **B** | Operational data lost or wrong: neither money '
         'nor a regulated record | nothing elevated | ' + CONF_B_DEFAULT + ' |\n')
out = run(CLEAN, NEW_HDR)
check('10. THE PAIRED NEGATIVE: the §2.3 replacement sentence is ACCEPTED, so arm 9 '
      'is not a check that refuses every migrated row',
      'ASSERTS A GATE' not in out and 'ROWS_MIGRATED_TWO_AXIS:2 of 2' in out,
      out[-400:])

# AND AN UN-MIGRATED ROW IS COUNTED, NOT REFUSED. 264 live rows carry that
# sentence today; firing on all of them is the atomic unreviewable diff §3.4
# step 1 exists to avoid. But a check that will not fire until a row moves must
# not read like one that passed, so the outstanding number is printed.
STALE = ('| `alpha_one` | **A** | money moves wrongly | Evidence for alpha |\n'
         '| `alpha_two` | **B** | operational data lost | Employee-auth-gated '
         'operational data: neither money nor a regulated record |\n')
out = run(STALE, OLD_HDR)
check('11. an UN-migrated row asserting a gate is COUNTED and printed, not refused',
      'ROWS_STILL_ASSERTING_A_GATE:1' in out and 'ASSERTS A GATE' not in out,
      out[-400:])

# ── 12-14. THE TWO REFINEMENTS THE MIGRATION ITSELF FORCED ───────────────
# Both were found by running the §2.3 check over real rows, one app apart, and
# both are cases where the first spelling refused the writing the register
# wants MORE of. They are locked here because the next person to tighten
# ACCESS_CONTROL_CLAIM will otherwise re-break them.
#
# 12. A QUOTED claim is not an asserted one. `grd_boq_rates` explains its own
# re-tier by quoting the sentence it was rescued from -- the check's own
# success story, refused by the check.
QUOTED = ('| `alpha_one` | **A** | **B** | money moves wrongly | commercial only '
          '| RE-TIERED on the money limb. It was B on the generic sentence '
          '&ldquo;employee-auth-gated operational data: neither money nor a '
          'regulated record&rdquo;, which is false about a pricing rule |\n'
          '| `alpha_two` | **B** | **B** | operational data lost | nothing elevated | rule |\n')
out = run(QUOTED, NEW_HDR)
check('12. a row QUOTING the old sentence to say it was wrong is ACCEPTED',
      'ASSERTS A GATE' not in out, out[-500:])

# 13. A CITED claim is not an uncited one. `law_portalmessages` says the
# resource is session-gated and names the dispatcher, the handler and a test
# that drives it to 401. §2.3's words are "stop asserting things NOTHING
# VERIFIED"; refusing this would delete the best-evidenced sentence in the file
# to protect a rule aimed at the worst-evidenced one.
CITED = ('| `alpha_one` | **A** | **A** | privileged material lost | privilege waived '
         '| The resource is genuinely session-gated (`LAW_RESOURCES` in '
         '`api/sd-data.js`, driven to 401 with no session in '
         '`api/sd-data-sairnlaw-resources.test.js`) |\n'
         '| `alpha_two` | **B** | **B** | operational data lost | nothing elevated | rule |\n')
out = run(CITED, NEW_HDR)
check('13. an access-control claim that CITES a file and a test is ACCEPTED',
      'ASSERTS A GATE' not in out, out[-500:])

# 14. AND THE PAIRED POSITIVE FOR BOTH. Arms 12 and 13 are each satisfied by a
# check that has stopped working; this is the one that says it has not. Bare
# assertion, no quotation marks, no citation anywhere in the sentence.
BARE = ('| `alpha_one` | **A** | **B** | money moves wrongly | commercial only '
        '| Employee-auth-gated operational data: neither money nor a regulated '
        'record |\n'
        '| `alpha_two` | **B** | **B** | operational data lost | nothing elevated | rule |\n')
out = run(BARE, NEW_HDR)
check('14. THE PAIRED POSITIVE: a BARE uncited, unquoted gate claim is still '
      'REFUSED, so arms 12-13 are not a check that accepts everything',
      'ASSERTS A GATE' in out, out[-500:])

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
