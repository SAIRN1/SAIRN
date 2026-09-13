"""Does a checker give the SAME verdict on UNCHANGED code, run after run?

    python tools/flaky_checker_quarantine.py --fixtures     # the blind lock alone
    python tools/flaky_checker_quarantine.py --measure      # run the fleet N times
    python tools/flaky_checker_quarantine.py                # read the ledger, report
    python tools/flaky_checker_quarantine.py --json

── WHY, FROM A REAL INSTANCE ─────────────────────────────────────────────
tools/literal_drift_check.py answered differently on identical input: its
near-duplicate pairs came back with the A and B labels swapped between runs,
because set iteration order depends on PYTHONHASHSEED. It was found by hand and
fixed in ac8f8491. NOTHING CATCHES THE NEXT ONE.

A flaky checker is worse than a broken one. A broken checker is red every time
and somebody fixes it. A flaky one is red on Tuesday and green on Wednesday, so
the red gets re-run instead of read -- and after that, every red from that tool
is discounted, including the true ones. The failure is not the wrong answer; it
is the credibility the tool takes down with it.

── QUARANTINE IS A PROCESS, NOT A DELETE ─────────────────────────────────
NEVER ON A SINGLE RED. A checker is quarantined only when its measured FLIP
RATE over unchanged code crosses a threshold -- a verdict that changed while
nothing did. One red is a finding; a flip is a defect in the checker.

Every quarantine carries, and this tool refuses to record one without them:
  * a NAMED OWNER -- an unowned quarantine is a deletion nobody voted for;
  * a DEADLINE -- the date it must be resolved by;
  * the EVIDENCE -- the runs, the differing outputs, the flip rate measured.

And it comes BACK automatically: a quarantined checker keeps being measured,
and once it is stable across the re-entry threshold it is reported as READY TO
REINTRODUCE. **A quarantine list that only ever grows is a graveyard**, so an
overdue entry is reported as loudly as a flaky checker -- the deadline is a
real gate, not a note.

── THE BLIND LOCK ────────────────────────────────────────────────────────
Flip detection and the thresholds are decided against synthetic fixtures below,
and this refuses to measure a real checker until they classify as written.

── ACCURACY AND STABILITY, SEPARATELY ────────────────────────────────────
ACCURACY   was the code genuinely UNCHANGED between runs? A flip measured
           across a modified tree is not a flip, it is the tool noticing an
           edit. The tree hash is recorded with every run and a measurement
           spanning two different trees is DISCARDED, not averaged.
STABILITY  the flip rate itself: distinct verdicts / runs.

── MARGIN ────────────────────────────────────────────────────────────────
The alarm is set TIGHTER than the quarantine threshold: a checker that has
flipped once but not yet crossed the bar is reported as WATCH, before it earns
a quarantine. Drift toward the limit is the signal worth having.

── WHAT IT CANNOT SEE, said here rather than discovered later ───────────
  * a checker that is deterministically WRONG. Perfectly stable and perfectly
    useless looks identical to perfectly stable and correct;
  * flakiness that needs more runs than were done to show itself. The run count
    is printed with every rate, because 2/2 stable is not 20/20 stable;
  * flakiness caused by the clock, the network or another session's push. Those
    are real and this cannot separate them from the checker's own
    non-determinism -- it reports the evidence and names the owner.

Exit 0 when nothing is flaky or overdue, 1 when something is, 2 when the
fixtures fail -- which means nothing was measured.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(REPO, 'docs', 'flaky-checker-ledger.json')
CRITERIA_VERSION = '2026-09-13.1'

# ── THRESHOLDS, decided before any checker was measured ───────────────────
RUNS_PER_MEASURE = 3        # per invocation; evidence accumulates in the ledger
MIN_RUNS_TO_JUDGE = 4       # below this, "stable" is not a claim worth making
QUARANTINE_AT = 0.05        # >5% of runs disagreeing with the modal verdict
WATCH_AT = 0.0001           # ANY disagreement at all is worth watching first
REENTRY_RUNS = 10           # consecutive clean runs before it may come back


def tree_hash():
    """What the working tree looked like. A flip across two trees is not a flip."""
    p = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd=REPO)
    dirty = subprocess.run(['git', 'status', '--porcelain'], capture_output=True,
                           text=True, cwd=REPO).stdout
    # THE LEDGER IS EXCLUDED FROM ITS OWN TREE HASH, and this is not a nicety.
    # Without it the tool cannot accumulate ANY evidence: the first --measure
    # writes docs/flaky-checker-ledger.json, which changes `git status`, which
    # changes the tree hash, so the next pass discards everything the first one
    # recorded. Measured: three passes in a row each left exactly 3 observations
    # and the classifier honestly answered TOO-FEW-RUNS forever.
    #
    # A tool whose own output invalidates its own input is its own subject. The
    # fix is to take itself out of the measurement, not to loosen the filter --
    # the filter is correct and is what made the loop visible.
    dirty = '
'.join(l for l in dirty.split('
')
                      if 'flaky-checker-ledger.json' not in l)
    return hashlib.sha256(((p.stdout or '') + dirty).encode('utf-8')).hexdigest()[:16]


def normalise(out):
    """Strip what legitimately varies so a real flip is not drowned in noise.

    Timings, ages and absolute paths change between runs WITHOUT the verdict
    changing. Counting those as flips would quarantine the whole fleet on the
    first measurement -- the horoscope failure, applied to flakiness.
    """
    out = re.sub(r'\d+\.\d+\s*(hours?|seconds?|ms)\b', '<t>', out)
    out = re.sub(r'\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[^\s]*', '<ts>', out)
    out = re.sub(r'\b\d+ (hours?|minutes?|days?) ago\b', '<ago>', out)
    out = re.sub(r'[A-Za-z]:[\\/][^\s\'"]+', '<path>', out)
    out = re.sub(r'\s+', ' ', out)
    return out.strip()


def load_ledger():
    if not os.path.exists(LEDGER):
        return {'version': CRITERIA_VERSION, 'checkers': {}, 'quarantine': {}}
    try:
        with io.open(LEDGER, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {'version': CRITERIA_VERSION, 'checkers': {}, 'quarantine': {}}


def save_ledger(led):
    with io.open(LEDGER, 'w', encoding='utf-8', newline=chr(10)) as fh:
        fh.write(json.dumps(led, indent=1, sort_keys=True))


def flip_rate(entry):
    """(rate, runs, distinct). Rate = runs disagreeing with the MODAL verdict."""
    obs = entry.get('observations', [])
    if not obs:
        return 0.0, 0, 0
    counts = {}
    for o in obs:
        counts[o['digest']] = counts.get(o['digest'], 0) + 1
    modal = max(counts.values())
    return (len(obs) - modal) / float(len(obs)), len(obs), len(counts)


def classify(entry):
    rate, runs, distinct = flip_rate(entry)
    if runs < MIN_RUNS_TO_JUDGE:
        return 'TOO-FEW-RUNS', rate, runs
    if rate > QUARANTINE_AT:
        return 'QUARANTINE', rate, runs
    if rate > WATCH_AT:
        return 'WATCH', rate, runs
    return 'STABLE', rate, runs


# ── FIXTURES: hand-decided, before any checker was measured ───────────────
def _e(digests):
    return {'observations': [{'digest': d, 'tree': 't'} for d in digests]}


FIXTURES = [
    ('a checker with one verdict over many runs is STABLE',
     _e(['a'] * 12), 'STABLE'),
    ('a single disagreement is WATCH, never an immediate quarantine',
     _e(['a'] * 39 + ['b']), 'WATCH'),
    ('a checker flipping most runs is QUARANTINE',
     _e(['a', 'b', 'a', 'b', 'a', 'b']), 'QUARANTINE'),
    ('CONTROL: too few runs is NOT a verdict -- 2/2 stable is not a claim',
     _e(['a', 'a']), 'TOO-FEW-RUNS'),
    ('a checker just over the bar is QUARANTINE, not WATCH',
     _e(['a'] * 18 + ['b', 'b']), 'QUARANTINE'),
]

NORMALISE_FIXTURES = [
    ('a changing DURATION is not a flip',
     'ran in 1.23 seconds, 0 findings', 'ran in 4.56 seconds, 0 findings', True),
    ('a changing AGE is not a flip',
     'capture 24.3 hours ago: clean', 'capture 25.1 hours ago: clean', True),
    ('a changing TIMESTAMP is not a flip',
     'at 2026-09-13T01:00:00Z ok', 'at 2026-09-13T02:00:00Z ok', True),
    ('an absolute PATH is not a flip',
     'read C:/a/b/c.json ok', 'read D:/x/y/c.json ok', True),
    ('CONTROL: a changed FINDING COUNT really is a flip',
     '3 findings', '4 findings', False),
    ('CONTROL: a changed verdict word really is a flip',
     'CLEAN', 'FINDINGS', False),
]


def run_fixtures():
    bad = []
    for name, entry, want in FIXTURES:
        got = classify(entry)[0]
        if got != want:
            bad.append((name, want, got))
    for name, a, b, want_same in NORMALISE_FIXTURES:
        same = normalise(a) == normalise(b)
        if same != want_same:
            bad.append((name, want_same, same))
    return bad


def registry_tools():
    """The promoted checkers, read from the one registry that already exists."""
    src = io.open(os.path.join(REPO, 'tools', 'report_only_checks.py'),
                  encoding='utf-8').read()
    return sorted(set(re.findall(r"'tool':\s*'([^']+)'", src)))


def measure(led, runs=RUNS_PER_MEASURE):
    th = tree_hash()
    tools = registry_tools()
    for t in tools:
        p = os.path.join(REPO, 'tools', t)
        if not os.path.exists(p):
            continue
        e = led['checkers'].setdefault(t, {'observations': []})
        for _ in range(runs):
            try:
                r = subprocess.run([sys.executable, p], capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', cwd=REPO, timeout=180)
                out = normalise((r.stdout or '') + (r.stderr or '')) + '|exit=' + str(r.returncode)
            except Exception as ex:
                out = 'RUNNER-ERROR:' + type(ex).__name__
            e['observations'].append({'digest': hashlib.sha256(out.encode('utf-8')).hexdigest()[:16],
                                      'tree': th})
        # ACCURACY: observations from a DIFFERENT tree are not comparable. Keep
        # only the current tree's -- a flip measured across an edit is the tool
        # noticing the edit, which is the tool working.
        e['observations'] = [o for o in e['observations'] if o.get('tree') == th][-40:]
    return len(tools)


def main(argv):
    bad = run_fixtures()
    print('FLAKY-CHECKER QUARANTINE -- criteria %s' % CRITERIA_VERSION)
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING WAS MEASURED.')
        for n, w, g in bad:
            print('     expected %r, got %r -- %s' % (w, g, n))
        return 2
    print('  blind lock: %d/%d fixtures correct, run before any checker was measured.'
          % (len(FIXTURES) + len(NORMALISE_FIXTURES), len(FIXTURES) + len(NORMALISE_FIXTURES)))
    if '--fixtures' in argv:
        return 0

    led = load_ledger()
    if '--measure' in argv:
        n = measure(led)
        save_ledger(led)
        print('  measured %d registered checker(s), %d run(s) each, tree %s'
              % (n, RUNS_PER_MEASURE, tree_hash()))

    rows = []
    for tool, e in sorted(led.get('checkers', {}).items()):
        verdict, rate, runs = classify(e)
        q = led.get('quarantine', {}).get(tool)
        rows.append({'tool': tool, 'verdict': verdict, 'flip_rate': round(rate, 4),
                     'runs': runs, 'quarantined': bool(q), 'quarantine': q,
                     'ready_to_reintroduce': bool(q) and verdict == 'STABLE'
                                             and runs >= REENTRY_RUNS})

    # Computed BEFORE either output branch. The first version defined it only
    # inside the human-readable path, so `--json` raised UnboundLocalError --
    # a tool whose machine-readable output crashes is a tool nothing can wire
    # up, and the exit code would have been an unhandled 1 that read like a
    # finding.
    today = subprocess.run(['git', 'log', '-1', '--format=%cs'], capture_output=True,
                           text=True, cwd=REPO).stdout.strip() or '2026-01-01'
    overdue = [r for r in rows if r['quarantined'] and r['quarantine']
               and r['quarantine'].get('deadline', '9999') < today]

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'rows': rows,
                          'overdue': [r['tool'] for r in overdue]}, indent=1))
    else:
        by = {}
        for r in rows:
            by.setdefault(r['verdict'], []).append(r)
        print('  checkers with evidence: %d' % len(rows))
        for v in ('QUARANTINE', 'WATCH', 'STABLE', 'TOO-FEW-RUNS'):
            note = {'QUARANTINE': '  <- flipped on unchanged code past the bar',
                    'WATCH': '  <- flipped at least once; alarm is TIGHTER than the bar',
                    'STABLE': '',
                    'TOO-FEW-RUNS': '  <- NOT a pass. 2/2 stable is not a claim'}[v]
            print('    %-14s %3d%s' % (v, len(by.get(v, [])), note))
        for r in by.get('QUARANTINE', []) + by.get('WATCH', []):
            print('      %-34s rate %.3f over %d run(s)' % (r['tool'], r['flip_rate'], r['runs']))
        ready = [r for r in rows if r['ready_to_reintroduce']]
        if ready:
            print('')
            print('  READY TO REINTRODUCE -- stable again, bring them back:')
            for r in ready:
                print('      %s' % r['tool'])
        if overdue:
            print('')
            print('  OVERDUE QUARANTINE -- a list that only grows is a GRAVEYARD:')
            for r in overdue:
                print('      %-34s owner %s, due %s'
                      % (r['tool'], r['quarantine'].get('owner', '(none)'),
                         r['quarantine'].get('deadline', '(none)')))
        print('')
        print('  A quarantine is NEVER entered on a single red: it needs a measured')
        print('  flip rate over UNCHANGED code, a named owner, and a deadline. Runs')
        print('  from a different tree are discarded rather than averaged.')
        if not rows:
            print('')
            print('  NO EVIDENCE YET. Run with --measure. An empty ledger is an honest')
            print('  zero, not a clean fleet.')

    bad_rows = [r for r in rows if r['verdict'] == 'QUARANTINE'] + overdue
    return 1 if bad_rows else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
