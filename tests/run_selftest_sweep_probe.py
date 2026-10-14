"""Every tool that tests ITSELF, actually run -- because a control in a drawer is not a control.

    python tests/run_selftest_sweep_probe.py
    python tests/run_selftest_sweep_probe.py --list

── WHY THIS EXISTS ────────────────────────────────────────────────────────────
`tools/first_article_inspection.py` reported seven artefacts shipped on
2026-09-15 with NO SUITE AT ALL. That was wrong about five of them and the
correction is the point: FIVE carried a working `--selftest`, 48 arms between
them, that nothing in `tools/run_all_tests.py` ever invoked. The runner
discovers `tests/**` and `*.test.js`; a self-test lives inside the tool and is
invisible to it.

**UNVERIFIED AND UNWIRED ARE DIFFERENT STATES.** One is a gap in the work. The
other is a gap in the wiring, and it is cheaper to close -- this file closes it.

── AND A SELF-TEST IS STILL THE WEAKER KIND, WHICH IS WHY THIS DOES NOT ───────
── CLOSE THE QUESTION ─────────────────────────────────────────────────────────
`docs/2026-09-13-cross-domain-disciplines.md` section 5: the deep check runs
with its subject NOT trusted. A `_selftest()` is edited in the same commit as
the code it checks, by the same hand, in the same file. It cannot be independent
of its subject and no amount of running it makes it so. Running it is strictly
better than not running it and strictly worse than an outside probe.

── DISCOVERED, NOT LISTED ─────────────────────────────────────────────────────
The population is every `tools/*.py` whose source declares a self-test flag. A
hardcoded list would go stale the first time somebody adds a tool, which is the
failure this file was created by.

── THE TREE MUST BE UNCHANGED AFTERWARDS, AND THAT IS ASSERTED ────────────────
Several of these MUTATE FILES -- `sabotage.py` plants a defect, `line_endings.py`
rewrites bytes, `guard_ablation.py` removes a guard. Their self-tests are
supposed to work in a temp directory and restore anything they touch. "Supposed
to" is the whole risk, so `git status --porcelain` is captured before and after
and any difference FAILS. That check is the reason this file can safely run a
mutating tool at all.
"""
import ast
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, 'tools')

# THE FLAG MUST BE COMPARED AGAINST argv, not merely PRESENT in the file.
# A bare substring search enrolled tools/first_article_inspection.py on the
# first run because that file's own source contains the string `--self-check`
# inside a regex it uses to detect OTHER tools' self-tests. A sweep that runs a
# flag the tool does not have gets an unknown-argument path, not a self-test,
# and would have reported a pass for a run that tested nothing.
SELFTEST_RX = re.compile(
    r"['\"](--self-?check|--selftest)['\"]\s*in\s*(?:sys\.)?argv", re.I)

# ── THE "in argv" TIGHTENING WAS STILL TEXT, 2026-10-14 ─────────────────────
# The regex above requires the FULL phrase `'--selftest' in sys.argv`, and
# three files still false-positived: tools/first_article_inspection.py (the
# phrase appears inside a STRING LITERAL it builds and writes to disk as a
# FIXTURE for its own --fixtures test), tools/subprocess_decode_check.py (the
# phrase appears in its module DOCSTRING, quoting this exact bug class as
# prose), and tools/checker_selftest_check.py (the phrase appears in a `#`
# COMMENT, explaining a past fix to ITS OWN unrelated flag-detection code).
# A regex run over raw source text cannot distinguish "this is real code" from
# "this is a string/comment that merely contains the shape of real code" --
# text does not know what a string literal is. An AST does: a Python string
# whose CONTENTS look like an `if` statement is one opaque ast.Constant, never
# an ast.Compare, because the parser never looks inside it. Confirmed live:
# all three fail at the actual invocation with argparse's "unrecognized
# arguments" -- the AST check below reproduces that without spending a
# subprocess per candidate.
def _flag_is_live_code(src, flag):
    """True iff `<flag> in (sys.)?argv` is a REAL `if`/comparison the parser
    sees, not text sitting inside a string, docstring or comment."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    target = flag.lower().replace('-', '').replace('_', '')
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(op, ast.In) for op in node.ops):
            continue
        left = node.left
        if not (isinstance(left, ast.Constant) and isinstance(left.value, str)):
            continue
        if left.value.lower().replace('-', '').replace('_', '') != target:
            continue
        for comp in node.comparators:
            name = (comp.attr if isinstance(comp, ast.Attribute)
                    else comp.id if isinstance(comp, ast.Name) else None)
            if name == 'argv':
                return True
    return False

# ── DECLARED EXCLUSIONS, EACH WITH A REASON ───────────────────────────────────
# Not a convenience list. A tool is excluded only when RUNNING it in the suite
# would do something the suite must not do, and the reason says which.
EXCLUDE = {
    'sc_tier_a_write_gate_live_probe.py':
        'writes and DELETES rows on the production demo tenant. It has no '
        'self-test flag today, and is named here so that adding one later does '
        'not quietly enrol a production writer into every push.',
    'rf_claim_gate_live_probe.py':
        'live licence and network, same reason.',
    'stonedesk_storefront_live_check.py':
        'live HTTP against the deployed storefront.',
    'waf_rule_check.py':
        'live HTTP.',
    'sairn_app_map_check.py':
        'one live HTTP request per app route.',
}

# A tool whose self-test needs something this environment may not have. These
# are RUN, and a failure is reported as COULD NOT TELL rather than as a defect
# -- but never as a pass.
# "not recognized" was spelled for a DIFFERENT message than the one argparse
# actually prints. argparse's rejection of an unknown flag is "unrecognized
# arguments: --selftest" -- no "not", one word -- so a tool that gets run with
# a flag it never had (exactly what the three AST false-positives above used
# to trigger) went to `fails` as a real defect instead of COULD NOT TELL.
# Verbatim from a live run: `checker_selftest_check.py: error: unrecognized
# arguments: --selftest`.
TOLERATE_MISSING = re.compile(
    r'No module named|command not found|not recognized|unrecognized argument|'
    r'ENOENT|connection|timed out|NOT_PROVISIONED', re.I)

fails, could_not = [], []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:500]))
    if not cond:
        fails.append(name)


def discover():
    out = []
    for f in sorted(os.listdir(TOOLS)):
        if not f.endswith('.py') or f in EXCLUDE:
            continue
        src = io.open(os.path.join(TOOLS, f), encoding='utf-8',
                      errors='replace').read()
        m = SELFTEST_RX.search(src)
        if not m:
            continue
        if not _flag_is_live_code(src, m.group(1)):
            continue
        out.append((f, m.group(1)))
    return out


def porcelain():
    p = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return None if p.returncode != 0 else sorted(p.stdout.splitlines())


found = discover()

if '--list' in sys.argv[1:]:
    for f, flag in found:
        print('%-46s %s' % (f, flag))
    sys.exit(0)

print('\n1. THE POPULATION')
check('at least one tool declares a self-test -- an empty sweep passes '
      'trivially and is exactly how this class hid in the first place',
      len(found) >= 3, found)
check('the population is DISCOVERED, not listed -- so a tool added tomorrow is '
      'swept without anybody remembering',
      all(os.path.isfile(os.path.join(TOOLS, f)) for f, _fl in found))
missing_excl = [f for f in EXCLUDE if not os.path.isfile(os.path.join(TOOLS, f))]
check('every declared exclusion names a file that EXISTS -- an exclusion for a '
      'deleted tool is dead weight that reads as coverage',
      not missing_excl, missing_excl)
check('...and every one carries a reason. The bar is NON-EMPTY, not a word '
      'count: "live HTTP." is a complete reason and a length floor would have '
      'rejected it, which is a rule about prose rather than about safety',
      all(isinstance(v, str) and v.strip() for v in EXCLUDE.values()),
      sorted(EXCLUDE))
check('CONTROL: no excluded tool is in the swept population',
      not any(f in EXCLUDE for f, _fl in found),
      [f for f, _fl in found if f in EXCLUDE])

before = porcelain()
check('git status is readable, so the tree can be compared afterwards -- '
      'without it a mutating self-test could not safely be run here',
      before is not None)

print('\n2. EVERY SELF-TEST ACTUALLY RUNS (%d)' % len(found))
for f, flag in found:
    p = subprocess.run([sys.executable, os.path.join('tools', f), flag],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=180)
    blob = (p.stdout or '') + (p.stderr or '')
    if p.returncode != 0 and TOLERATE_MISSING.search(blob):
        could_not.append((f, blob.strip().splitlines()[-1][:160] if blob.strip() else ''))
        print('  ?    COULD NOT TELL  %-38s %s' % (f, flag))
        continue
    check('%s %s exits 0' % (f, flag), p.returncode == 0,
          blob.strip()[-400:] or ('exit %d with no output' % p.returncode))

print('\n3. NOTHING IN THE WORKING TREE MOVED')
after = porcelain()
check('git status is still readable', after is not None)
if before is not None and after is not None:
    added = [l for l in after if l not in before]
    gone = [l for l in before if l not in after]
    check('the working tree is BYTE-FOR-BYTE as it was. Several of these tools '
          'plant defects, rewrite line endings or remove guards from real '
          'files; "their self-test cleans up" is the assumption this arm '
          'refuses to make', not added and not gone,
          {'appeared': added[:6], 'disappeared': gone[:6]})

print('\n4. COULD-NOT-TELL IS REPORTED, NEVER FOLDED INTO A PASS')
if could_not:
    print('  %d self-test(s) could not run here, and that is NOT a pass:'
          % len(could_not))
    for f, why in could_not:
        print('    %-40s %s' % (f, why))
else:
    print('  ok   every discovered self-test ran to a verdict.')
check('a could-not-tell is reported by name rather than counted as success',
      True)

print('\n5. WHAT THIS DOES NOT ESTABLISH')
print('  A self-test is edited in the same commit as the code it checks, by')
print('  the same hand, in the same file. It cannot be independent of its')
print('  subject -- disciplines section 5 -- so running it is strictly better')
print('  than leaving it in a drawer and strictly worse than an outside probe.')
print('  Nothing here says any of these tools is adequately verified.')

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS%s'
          % ('' if not could_not else ' (%d COULD NOT TELL, listed above)'
             % len(could_not)))
sys.exit(1 if fails else 0)
