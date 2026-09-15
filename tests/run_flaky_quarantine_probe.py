"""tests/run_flaky_quarantine_probe.py -- quarantine is a process with a way
back out, and the flip detector can be shown to fire and to stay quiet.

    python tests/run_flaky_quarantine_probe.py

The arms that matter are the two failure modes this discipline has, and they
pull in opposite directions:

  * TOO EAGER -- a detector that counts a changing duration or timestamp as a
    flip quarantines the whole fleet on the first run. Section 2 pins the
    things that legitimately vary, with CONTROLS asserting a real verdict
    change still counts.
  * TOO PERMANENT -- a quarantine list that only grows is a graveyard. Section 4
    pins that a stable checker becomes READY TO REINTRODUCE on its own, and
    that an overdue entry is reported as loudly as a flaky one.

And the rule that keeps it honest either way: NEVER QUARANTINE ON A SINGLE RED.
Section 3 pins that one disagreement is WATCH, and that too few runs is not a
verdict at all.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import flaky_checker_quarantine as Q                            # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


def obs(digests, tree='t'):
    return {'observations': [{'digest': d, 'tree': tree} for d in digests]}


print('1. the blind lock')
check('1a  every fixture classifies as decided', Q.run_fixtures() == [], Q.run_fixtures())
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'flaky_checker_quarantine.py'),
                    '--fixtures'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('1b  the lock runs on its own and passes', p.returncode == 0, 'exit %d' % p.returncode)
check('1c  it is stated as running BEFORE anything was measured',
      'before any checker was measured' in (p.stdout or ''))

print('2. what legitimately varies is NOT a flip')
for name, a, b, want_same in Q.NORMALISE_FIXTURES:
    check('2  ' + name, (Q.normalise(a) == Q.normalise(b)) == want_same)

print('3. NEVER on a single red')
check('3a  one disagreement in forty is WATCH, not QUARANTINE',
      Q.classify(obs(['a'] * 39 + ['b']))[0] == 'WATCH')
check('3b  two runs is TOO-FEW-RUNS -- not STABLE, which would be a claim',
      Q.classify(obs(['a', 'a']))[0] == 'TOO-FEW-RUNS')
check('3c  CONTROL: a genuinely stable checker over many runs IS stable -- or 3a '
      'and 3b would pass on a classifier that never says STABLE',
      Q.classify(obs(['a'] * 20))[0] == 'STABLE')
check('3d  a checker flipping every other run is QUARANTINE',
      Q.classify(obs(['a', 'b'] * 6))[0] == 'QUARANTINE')
check('3e  the WATCH alarm is TIGHTER than the quarantine bar',
      Q.WATCH_AT < Q.QUARANTINE_AT, '%s < %s' % (Q.WATCH_AT, Q.QUARANTINE_AT))

print('4. a way BACK OUT -- the anti-graveyard half')
led = {'checkers': {'x.py': obs(['a'] * Q.REENTRY_RUNS)},
       'quarantine': {'x.py': {'owner': 'Hank', 'deadline': '2099-01-01',
                               'evidence': 'flipped 3/10 on 2026-09-13'}}}
tmp = tempfile.mkdtemp(prefix='flaky-')
led_path = os.path.join(tmp, 'ledger.json')
io.open(led_path, 'w', encoding='utf-8', newline=chr(10)).write(json.dumps(led))
old = Q.LEDGER
try:
    Q.LEDGER = led_path
    l2 = Q.load_ledger()
    v = Q.classify(l2['checkers']['x.py'])
    ready = bool(l2['quarantine'].get('x.py')) and v[0] == 'STABLE' \
        and v[2] >= Q.REENTRY_RUNS
    check('4a  a quarantined checker that is stable again is READY TO REINTRODUCE',
          ready, v)
    check('4b  re-entry needs a real run count, not one clean run',
          Q.REENTRY_RUNS >= 10, Q.REENTRY_RUNS)
finally:
    Q.LEDGER = old

print('5. a quarantine that cannot be recorded without an owner and a deadline')
q = {'owner': 'Hank', 'deadline': '2026-09-20', 'evidence': 'flip rate 0.30 over 10 runs'}
check('5a  the shape carries all three', all(k in q for k in ('owner', 'deadline', 'evidence')))
src = io.open(os.path.join(REPO, 'tools', 'flaky_checker_quarantine.py'),
              encoding='utf-8').read()
code = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('#'))
check('5b  the tool reports OVERDUE entries -- a list that only grows is a graveyard',
      'OVERDUE QUARANTINE' in code)
check('5c  and it reports READY TO REINTRODUCE', 'READY TO REINTRODUCE' in code)

print('6. ACCURACY -- runs from a different tree are discarded, not averaged')
mixed = {'observations': [{'digest': 'a', 'tree': 't1'}, {'digest': 'b', 'tree': 't2'}]}
kept = [o for o in mixed['observations'] if o['tree'] == 't1']
check('6a  a flip across two trees is not a flip -- it is the tool noticing an edit',
      len(kept) == 1)
check('6b  the measure step filters by the CURRENT tree hash',
      "o.get('tree') == th" in code)
check('6c  and an empty ledger reports an honest zero rather than a clean fleet',
      'NO EVIDENCE YET' in code and 'honest' in code)

print('7. STARVATION -- the order decides who never gets measured (item 22)')
# THE DEFECT THESE ARMS HOLD, measured rather than imagined: the pass was
# alphabetical, one registered checker (comment_sensitivity_check.py) takes
# 103 SECONDS PER RUN against a fleet median under a second, and a pass never
# finished inside a real session window. So the same alphabetical tail starved
# EVERY time and eleven checkers had no evidence at all months after the rest
# had six observations each. A fixed order plus a budget that always runs out
# is not partial coverage, it is a permanent blind spot that reports as a
# clean fleet.
th = 'TREE'
led7 = {'checkers': {
    'zebra_never_measured.py': {'observations': []},
    'alpha_well_measured.py': obs(['a'] * 6, tree=th),
    'mid_partly_measured.py': obs(['a', 'a'], tree=th),
}}
order = Q.measure_order(led7, ['alpha_well_measured.py', 'mid_partly_measured.py',
                               'zebra_never_measured.py'], th)
check('7a  the checker with NO evidence is measured FIRST, not last alphabetically',
      order[0] == 'zebra_never_measured.py', order)
check('7b  ...and the best-covered one goes last, so a truncated pass converges',
      order[-1] == 'alpha_well_measured.py', order)
check('7c  CONTROL: the order is not simply reverse-alphabetical -- the MIDDLE '
      'one sorts by its evidence count, between the other two',
      order[1] == 'mid_partly_measured.py', order)
# A tool with observations from ANOTHER tree has no evidence about THIS one, so
# it must sort as unmeasured. Without this the starved checkers would be
# re-starved the moment anybody edited the repo, which is continuously.
led7['checkers']['other_tree.py'] = obs(['a'] * 20, tree='DIFFERENT')
order2 = Q.measure_order(led7, list(led7['checkers'].keys()), th)
check('7d  evidence from a DIFFERENT tree does not count as coverage of this one',
      order2.index('other_tree.py') < order2.index('mid_partly_measured.py'), order2)
check('7e  the order is deterministic -- two passes that measured different '
      'tools in different orders would be indistinguishable from a flip',
      Q.measure_order(led7, list(led7['checkers'].keys()), th) == order2)
# THE ARM THAT CAUGHT THE FIRST VERSION OF THIS FIX DOING NOTHING. The tree
# hash changes on EVERY commit, so right after the ordering landed all 37
# checkers had zero observations at the new tree, every weight tied at zero,
# the tie broke on name, and the pass went ALPHABETICAL AGAIN -- starving
# exactly the same tail it was written to rescue. Watched happening, not
# reasoned about: the ledger sat at 26 entries while the pass ground through
# the same alphabetical head.
led_fresh = {'checkers': {
    'zzz_never_run_anywhere.py': {'observations': []},
    'aaa_measured_yesterday.py': obs(['a'] * 6, tree='YESTERDAY'),
}}
fresh = Q.measure_order(led_fresh, list(led_fresh['checkers'].keys()), 'TODAY')
check('7f  AT A BRAND-NEW TREE, where nobody has evidence, the checker that '
      'has never run AT ANY TREE still sorts first -- otherwise every commit '
      'resets the order to alphabetical and the fix does nothing',
      fresh[0] == 'zzz_never_run_anywhere.py', fresh)
check('7g2 ...and it is the SAME order the tool actually measures in, not a '
      'helper nothing calls', 'measure_order(led, tools, th)' in code)

# THE BUDGET ARM IS BEHAVIOURAL, NOT A GREP. Written that way after the
# source-level version was proven worthless: deleting the `break` outright left
# every word the grep looked for still in the file and the suite stayed GREEN.
# A source arm on a behaviour is the same shape as a checker nobody has seen
# fail -- it looks covered and is not.
tmp7 = tempfile.mkdtemp(prefix='flaky-budget-')
led7_path = os.path.join(tmp7, 'ledger.json')
io.open(led7_path, 'w', encoding='utf-8', newline=chr(10)).write('{"checkers":{}}')
old_led, old_reg = Q.LEDGER, Q.registry_tools
try:
    Q.LEDGER = led7_path
    # Two REAL registered checkers, both measured at well under a second above,
    # so the control below cannot be slow enough to trip its own budget.
    Q.registry_tools = lambda: ['checkblocks.py', 'cleanup_confirm_check.py']
    l7 = Q.load_ledger()
    # measure() returns a THIRD value since 2026-09-14: the registered
    # checkers this runner cannot execute at all. Unpacked rather than
    # starred, so the next signature change breaks here loudly too.
    reached, tools, unrunnable = Q.measure(l7, runs=1, budget=0)
    check('7h  a budget of zero REACHES NOTHING and says so, rather than being '
          'killed mid-pass with no output at all',
          reached == [] and len(tools) == 2, (reached, tools))
    l8 = Q.load_ledger()
    reached2, tools2, unrunnable2 = Q.measure(l8, runs=1, budget=None)
    check('7i  CONTROL: with no budget the same two ARE measured -- 7g would '
          'otherwise pass on a measure() that never runs anything',
          sorted(reached2) == sorted(tools2) and len(reached2) == 2, reached2)
finally:
    Q.LEDGER, Q.registry_tools = old_led, old_reg
check('7j  what a short pass did not reach is NAMED, not counted -- a silent '
      'cap reads as a complete pass', 'STOPPED EARLY' in code and 'for t in skipped' in code)

print('8. A FLIP MUST BE DIAGNOSABLE -- two hashes is not evidence')
# The first real flip this tool ever found (comment_sensitivity_check.py,
# 0.333 over 12 runs) could not be investigated at all: the ledger held two
# digests and nothing else. A detector that can say THAT something flipped and
# never WHAT produces findings nobody can act on.
tmp8 = tempfile.mkdtemp(prefix='flaky-sample-')
p8 = os.path.join(tmp8, 'ledger.json')
io.open(p8, 'w', encoding='utf-8', newline=chr(10)).write('{"checkers":{}}')
old_led, old_reg = Q.LEDGER, Q.registry_tools
try:
    Q.LEDGER = p8
    Q.registry_tools = lambda: ['cleanup_confirm_check.py']
    l8 = Q.load_ledger()
    Q.measure(l8, runs=2, budget=None)
    e8 = Q.load_ledger()['checkers']['cleanup_confirm_check.py']
    check('8a  the ledger records the VERDICT TEXT, not only its hash',
          bool(e8.get('samples')), list((e8.get('samples') or {}).keys()))
    check('8b  ...keyed by the digest, so a sample belongs to a specific verdict',
          all(k in {o['digest'] for o in e8['observations']} for k in e8['samples']))
    check('8c  ...and BOUNDED, so a genuinely random checker cannot grow the '
          'ledger without limit', Q.SAMPLE_CAP <= 8 and all(len(v) <= 400 for v in e8['samples'].values()),
          '%d distinct, cap %d' % (len(e8['samples']), Q.SAMPLE_CAP))
finally:
    Q.LEDGER, Q.registry_tools = old_led, old_reg
check('8d  a tool whose samples predate capture SAYS SO rather than printing '
      'nothing, which would read as "no difference"',
      'NO VERDICT TEXT IS ON FILE' in code)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
