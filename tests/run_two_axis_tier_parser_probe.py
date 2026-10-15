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
import ast
import io
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    r = subprocess.run([sys.executable, TOOL], capture_output=True, text=True, encoding='utf-8', errors='replace',
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
# ── THE LABELS ARE READ OUT OF THE CHECKER, NOT TYPED HERE (2026-09-23) ──
# They used to be a hand-written tuple of five. A list of another file's
# strings is a second copy of them, and it goes stale the first time somebody
# adds a sixth -- silently, because a label the probe has never heard of is a
# problem class it then asserts nothing about, and a skipped assertion reads
# exactly like a passed one. Same move tests/claims/run_push_verify_probe.py's
# local_deps() makes for imports: resolve it from the SOURCE.
#
# AST, NOT A REGEX. The labels sit inside `problems.append('LABEL  %s ...' %
# ...)`, and the checker's own prose discusses "the BAD TIER check" in comments
# three times. A regex over the source would collect those sentences as labels.
# A parser cannot read a comment as a call. (Same class as the import scan that
# returned `HEAD`, `a` and `the` from docstrings, recorded twice on this
# platform now.)
def checker_problem_labels(path):
    """Every problem label tools/criticality_tier_check.py can emit."""
    try:
        tree = ast.parse(io.open(path, encoding='utf-8').read())
    except (OSError, SyntaxError) as e:
        return None, str(e)[:120]
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr == 'append'
                and isinstance(f.value, ast.Name) and f.value.id == 'problems'):
            continue
        arg = node.args[0] if node.args else None
        while isinstance(arg, ast.BinOp):      # 'LABEL  %s ...' % (...)
            arg = arg.left
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            m = re.match(r'^([A-Z][A-Z ]*[A-Z])', arg.value)
            if m:
                out.add(m.group(1).strip())
    return out, None


# A SYNTHETIC APP CANNOT SATISFY THESE, so they fire on every fixture by
# construction and say nothing about the parser. This is the one judgement that
# stays hand-written, and it is a judgement about what a LABEL means rather
# than a copy of what the checker says -- the header comment below the fixtures
# already explains why asserting PROBLEMS:0 here would be asserting that a
# constructed app is a real one.
SYNTHETIC_APP_LABELS = frozenset({
    'NO ROLLUP',        # the fixture app has a registry and no rollup line
    'GONE',             # ...and every real app has a rollup and no fixture registry
    'NOT A RESOURCE',   # the fixture's rows are registered in no api/_resources
})

# ── DOCUMENT-SCOPE, NOT ROW-SCOPE (added 2026-10-14, cody b14) ───────────
# HEADLINE is not a row-level problem and never was. It is a check on the
# DOCUMENT's own prose -- tools/criticality_tier_check.py:1003-1008 re-reads the
# whole register and looks for the "N resources, A A, B B, C C" summary
# sentence, and says so in its own comment: "this is a check on the DOCUMENT's
# prose, not on the table parse() builds". Every fixture here is a two-row
# table with no summary sentence by construction, so the checker reports a
# could-not-tell on every single run.
#
# THAT IS WHY ARM 2 WAS RED, AND THE PARSER WAS NEVER IMPLICATED. The fixture
# parses: the same run prints RESOURCE_ROWS:2 and ROWS_MIGRATED_TWO_AXIS:2 of
# 2, and arms 3-14 pass on it. row_problems() was over-collecting a
# headline-scope third state into an arm whose own words say "row-level".
# Diagnosed by fourth 2026-10-06, re-driven by cody b9, fixed here.
#
# THE OTHER REPAIR -- giving the fixtures a headline -- WAS REJECTED, and the
# reason is this file's own recorded defect class. HEADER is shared by all 14
# arms over fixtures with different row counts and different tier letters, so a
# typed sentence would be a second copy of NEW_ROWS that goes stale the first
# time a fixture row changes, and a derived one would make the HEADLINE check
# agree with itself on every arm -- a check that can no longer fail. Scoping
# the helper changes one judgement; rewriting the fixtures changes fourteen.
DOCUMENT_LABELS = frozenset({
    'HEADLINE',         # the register's summary SENTENCE; fixtures have none
})

# The five that were hand-typed here until 2026-09-23. Kept ONLY as a criteria
# lock: a derivation that silently returned garbage -- or nothing -- would make
# row_problems() return [] and arm 2 would pass vacuously forever, which is the
# failure this change could introduce. If the derivation stops finding these,
# the probe refuses to run rather than reporting a clean parse.
KNOWN_LABELS = ('BAD TIER', 'BAD CONFIDENTIALITY', 'COMPUTED TIER MISMATCH',
                'NO EVIDENCE', 'NO WORST CASE')

_labels, _why = checker_problem_labels(TOOL)
if _labels is None:
    print('COULD NOT RUN: tools/criticality_tier_check.py would not parse (%s). '
          'Nothing was verified.' % _why)
    sys.exit(3)
_missing = [k for k in KNOWN_LABELS if k not in _labels]
if _missing:
    print('COULD NOT RUN: the label derivation lost %s. It reads '
          "problems.append('LABEL ...') out of the checker; if that shape "
          'changed, this probe must be updated rather than left asserting the '
          'absence of nothing. Nothing was verified.' % _missing)
    sys.exit(3)

# AN EXCLUSION THAT EXCLUDES NOTHING IS THE DANGEROUS SHAPE, so the two
# hand-written sets are checked against the derivation rather than trusted. If
# the checker renames or retires one of these labels, the exclusion stops
# naming anything real and quietly narrows what arm 2 asserts -- and nothing
# would say so, because the arm would simply pass. COULD NOT RUN, not a pass.
# (A label renamed the other way is already safe: the new name lands in
# ROW_PROBLEMS and turns arm 2 red naming it.)
_stale = [k for k in sorted(SYNTHETIC_APP_LABELS | DOCUMENT_LABELS)
          if k not in _labels]
if _stale:
    print('COULD NOT RUN: %s is excluded from row_problems() but the checker no '
          'longer emits it, so the exclusion is stale and arm 2 is asserting '
          'the absence of a label that cannot occur. Re-read the checker and '
          'fix the set. Nothing was verified.' % _stale)
    sys.exit(3)

# Derived, so a NEW problem class is asserted absent the day it is added. A new
# APP-level label would land here wrongly and turn arm 2 red -- that is the
# safe direction and it names the label, where the old tuple would have said
# nothing at all.
ROW_PROBLEMS = tuple(sorted(_labels - SYNTHETIC_APP_LABELS - DOCUMENT_LABELS))


def row_problems(out):
    return [k for k in ROW_PROBLEMS if k in out]


# ── ARM 1 CHANGED 2026-09-22 WHEN THE MIGRATION COMPLETED ────────────────
# It used to assert the old four-cell shape raises NO row-level problem, which
# was right while 387 rows were still in it. §3.4 step 4 arms the opposite once
# every row carries both axes: an old-shape row is now a NEW row that skipped
# the axis checks, and a skipped check reads exactly like a passed one.
# IT MUST STILL PARSE. The compatibility branch is kept rather than deleted --
# an unparseable row would vanish from the table instead of being refused,
# which is the same silence one layer down. Both halves are asserted together.
out = run(OLD_ROWS, OLD_HDR)
check('1. the OLD four-cell shape still PARSES (both rows are seen)',
      'RESOURCE_ROWS:2' in out, out[-400:])
check('   ...and is now REFUSED by name rather than skipped',
      'NOT MIGRATED' in out and 'PROBLEMS:0' not in out, out[-400:])
check('   ...and still reports 0 of 2 migrated, so the count stays honest',
      'ROWS_MIGRATED_TWO_AXIS:0 of 2' in out, out[-300:])

out = run(NEW_ROWS, NEW_HDR)
check('2. the NEW six-cell shape parses, raises no row-level problem, and counts '
      'as migrated',
      'ROWS_MIGRATED_TWO_AXIS:2 of 2' in out and not row_problems(out),
      'row problems: %s\n%s' % (row_problems(out), out[-400:]))

# ── THE CONTROL ON ARM 2'S EXCLUSION (2026-10-14, cody b14) ──────────────
# Arm 2 passes partly because HEADLINE is excluded from row_problems(). That
# exclusion is only honest while the checker still RAISES a headline problem on
# this fixture. If somebody deletes the headline check from
# tools/criticality_tier_check.py, arm 2 would go on passing and would be
# passing for a reason that no longer exists -- the exact "delete the check and
# the control is satisfied" shape. So the signal arm 2 sets aside is asserted
# PRESENT, on the same run, on the same output.
# This is NOT a second copy of the checker's behaviour: it asserts only that
# the label appears, not what it says, and the label itself is read out of the
# checker by checker_problem_labels() above.
check('   ...and the HEADLINE problem arm 2 sets aside is STILL RAISED on that '
      'same run, so the exclusion re-scopes a live signal rather than hiding '
      'an absent one',
      'HEADLINE' in out, out[-400:])

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
check('8. one migrated row and one not-yet-migrated row coexist and BOTH parse '
      '(the un-migrated one is refused, not lost)',
      'RESOURCE_ROWS:2' in out and 'ROWS_MIGRATED_TWO_AXIS:1 of 2' in out
      and 'NOT MIGRATED' in out, out[-400:])

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
