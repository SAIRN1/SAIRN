r"""tests/run_hedge_carry_probe.py -- control pair for tools/hedge_carry_check.py.

    python tests/run_hedge_carry_probe.py

CONTROLS_FOR = ['tools/hedge_carry_check.py']
LIVE_PROBE_CLASS = 'FIXTURE'

The tool carries its own `--selftest` with seven fixture arms; this probe drives it
END TO END -- through argv, a real `--range` against this repository's own log, and
every fail-closed path -- because a selftest calling the module's functions cannot
see a broken CLI, a bad range, or an exit code that says the wrong thing.

THE ONE THAT MATTERS MOST IS THE REAL RANGE. The check's whole claim is that it can
be pointed at a dispatch and a commit range and give a verdict. The arm below points
it at the ACTUAL dispatch sentence from queue22 item 6 and the ACTUAL commit that
did the work, and requires a PASS -- because a check that fires on the one commit
that got it right would be worse than nothing.
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

TOOL = os.path.join(REPO, 'tools', 'hedge_carry_check.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/hedge_carry_check.py is not on disk. This '
          'control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

NL = chr(10)
passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:500])


def run(*args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=200,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print('CONTROL PAIR -- tools/hedge_carry_check.py' + NL)

# ══ THE TOOL'S OWN FIXTURES MUST PASS, driven through argv ══════════════════
print('PART 1 -- the selftest runs through the CLI')
rc, out = run('--selftest')
ok(rc == EXIT_CLEAN, '--selftest exits 0 (got %d)' % rc, out[-500:])
ok('ALL ARMS PASS' in out, 'and every fixture arm passes', out[-500:])
ok('KNOWN-BAD THE OTHER WAY' in out,
   'including the arm in the OTHER direction -- emphasis is not a hedge, so a '
   'wide word list cannot make this fire on every dispatch. A check that fires '
   'on everything is switched off in a day', out[-500:])

# ══ THE REAL DISPATCH AND THE REAL COMMIT ══════════════════════════════════
print(NL + 'PART 2 -- the real queue22 sentence against the real commit')
ITEM = ('sv_financials, dnt_vendor_orders, leg_insurance and msb_food_waste are '
        'likely Tier A on the money limb.')

# Find the commit that did that work, by its own subject. Derived, not typed:
# a hardcoded sha would go dangling on the next rebase, which is the defect
# --reseat-shas exists for.
p = subprocess.run(['git', '-C', REPO, 'log', '--format=%H',
                    '--grep=detection-method table summed to 358', '-n', '1'],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace')
sha = (p.stdout or '').strip().split(NL)[0]
if sha:
    rc, out = run('--item', ITEM, '--range', sha + '~1..' + sha)
    ok(rc == EXIT_CLEAN,
       'THE ARM THAT MATTERS: the commit that ACTUALLY did this work PASSES '
       '(exit %d). It says "the routed finding said LIKELY TIER A. IT IS NOT, and '
       'the re-read is recorded rather than the finding quietly dropped." A check '
       'that fired on the one commit that got it right would be worse than '
       'nothing' % rc, out[-700:])
    ok('CARRIED' in out or 'RESOLVED' in out,
       'and the verdict names which -- carried forward or resolved', out[-500:])
else:
    ok(False, 'could not find the real commit by subject, so the arm that '
              'matters most did not run -- that is a third state, not a pass')

# ══ THE KNOWN-BAD, against a REAL commit that says nothing about the hedge ══
print(NL + 'PART 3 -- KNOWN-BAD against a real commit in this repository')
p = subprocess.run(['git', '-C', REPO, 'log', '--format=%H', '-n', '1',
                    '--grep=^chore(docs): regenerate'],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace')
plain = (p.stdout or '').strip().split(NL)[0]
if plain:
    rc, out = run('--item', ITEM, '--range', plain + '~1..' + plain)
    ok(rc == EXIT_FINDING,
       'a hedged dispatch against a commit whose message says nothing about the '
       'uncertainty is a FINDING (exit %d) -- and this is a REAL commit from this '
       'repository rather than a string I wrote' % rc, out[-600:])
    ok('DROPPED' in out,
       'and the verdict is DROPPED, naming the hedge and the sentence it came '
       'from so a reader sees WHAT was hedged', out[-600:])
else:
    ok(False, 'no plain commit found to drive the known-bad against')

# ══ PART 3b -- THE FALSE DROPPED, DRIVEN THROUGH THE CLI ═══════════════════
# The tool's own selftest locks these too, and that is not enough on its own: a
# tool asserting that its own fix works is the shape item 11 is about. This runs
# the fix through the REAL command line against a REAL plain commit -- the exact
# configuration that produced the false finding.
print(NL + 'PART 3b -- the false DROPPED, through the CLI, against a real plain commit')
if plain:
    NOT_HEDGES = [
        ("The resource name appears in citation_drift_hook.py's DOCSTRING and in "
         "invocation_path_scan.py's docstring, as the worked example.",
         '`appears` meaning OCCURS'),
        ('Strip comments and block comments, then confirm the only possible '
         'values are A and B.',
         '`possible` ENUMERATING a closed set'),
        ('The named suspect is the matcher, not the tool.',
         '`suspect` as a NOUN'),
    ]
    for text, label in NOT_HEDGES:
        rc, out = run('--item', text, '--range', plain + '~1..' + plain)
        ok(rc == EXIT_CLEAN and 'DROPPED' not in out,
           'FALSE DROPPED, FIXED: %s is not a hedge, so a real plain commit no '
           'longer answers for it (exit %d)' % (label, rc), out[-500:])
        ok('NOTHING TO CHECK' in out.upper(),
           '   ...and it says it checked nothing rather than printing a clean '
           'line -- the same distinction as an unhedged dispatch', out[-400:])

    REAL_HEDGES = [
        ('This appears to be a Tier A resource on the money limb.', '`appears to`'),
        ('It is possible that the register is right about this row.', '`possible that`'),
        ('I suspect the matcher is reading the wrong column.', '`I suspect`'),
    ]
    for text, label in REAL_HEDGES:
        rc, out = run('--item', text, '--range', plain + '~1..' + plain)
        ok(rc == EXIT_FINDING and 'DROPPED' in out,
           'and %s STILL fires (exit %d) -- the fix DISAMBIGUATES the three '
           'polysemous entries, it does not delete them, and a fix that deleted '
           'them would pass every arm above' % (label, rc), out[-500:])

    # THE SHADOWING, end to end. One dispatch, a non-hedging use first and a real
    # hedge second. The bare-word version reported the first and stopped.
    rc, out = run('--item', 'The name appears in the docstring. Separately, the '
                  'row appears to be Tier A on the money limb.',
                  '--range', plain + '~1..' + plain)
    ok(rc == EXIT_FINDING and 'appears to' in out,
       'and the real hedge is no longer SHADOWED by a non-hedging use of the '
       'same word earlier in the dispatch -- reported under its own label '
       '`appears to` (exit %d)' % rc, out[-600:])
    ok('appears to be Tier A' in out,
       '   ...with the sentence that actually carried the hedge as its context, '
       'not the first sentence in the dispatch', out[-600:])
else:
    ok(False, 'no plain commit found, so the false-DROPPED arms did not run -- '
              'that is a could-not-run and is reported as a failure, not skipped')

# ══ FAIL CLOSED ════════════════════════════════════════════════════════════
print(NL + 'PART 4 -- fail closed, three ways')
rc, out = run('--item', ITEM)
ok(rc == EXIT_COULD_NOT_RUN,
   'no --range is exit 2 (got %d) -- with nothing to compare against, a clean '
   'line would mean "no hedge was dropped"' % rc, out[-300:])

rc, out = run('--range', 'HEAD~1..HEAD')
ok(rc == EXIT_COULD_NOT_RUN,
   'no --item is exit 2 (got %d) -- an empty item yields no hedges, which reads '
   'as nothing dropped' % rc, out[-300:])

rc, out = run('--item', ITEM, '--range', 'no-such-ref-xyz..HEAD')
ok(rc == EXIT_COULD_NOT_RUN,
   'an unreadable range is exit 2 (got %d) and not a quiet pass' % rc,
   out[-300:])

rc, out = run('--item-file', os.path.join('docs', '_zz_no_such_item.txt'),
              '--range', 'HEAD~1..HEAD')
ok(rc == EXIT_COULD_NOT_RUN,
   'and an absent --item-file is exit 2 (got %d)' % rc, out[-300:])

# ══ THE UNHEDGED CASE SAYS IT CHECKED NOTHING ══════════════════════════════
print(NL + 'PART 5 -- an unhedged dispatch does not pretend to have checked')
rc, out = run('--item', 'promote msb_food_waste to Tier A on the money limb',
              '--range', 'HEAD~1..HEAD')
ok(rc == EXIT_CLEAN, 'an unhedged item exits 0 (got %d)' % rc, out[-300:])
ok('NOTHING TO CHECK' in out.upper(),
   'and SAYS it made no assertion, rather than printing a clean line that reads '
   'as coverage -- a flat false premise is invisible to this check by '
   'construction and the report says so', out[-600:])

print(NL + '%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
