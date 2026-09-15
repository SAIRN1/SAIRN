"""Does a checker give the SAME verdict on UNCHANGED code, run after run?

    python tools/flaky_checker_quarantine.py --fixtures     # the blind lock alone
    python tools/flaky_checker_quarantine.py --measure --runs 6   # one tree, N runs
    python tools/flaky_checker_quarantine.py --measure --runs 6 --budget-seconds 400
    python tools/flaky_checker_quarantine.py                # read the ledger, report
    python tools/flaky_checker_quarantine.py --json

── THE PASS IS WEAKEST-EVIDENCE-FIRST, AND A BUDGET STOPS IT CLEANLY ─────
Measured 2026-09-14: one registered checker (comment_sensitivity_check.py)
takes 103 SECONDS PER RUN against a fleet median under a second, so a full pass
does not fit the window a session here actually gets. It used to run
alphabetically, so the SAME TAIL STARVED EVERY TIME and eleven checkers had no
evidence at all months after the rest had six observations each. The order is
now by evidence-at-this-tree, so a truncated pass advances the checkers that
know least and coverage converges. `--budget-seconds` stops before the kill
instead of after it, and NAMES what it did not reach -- a pass that is killed
prints nothing, and a third of the fleet then looks exactly like all of it.

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
import math
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(REPO, 'docs', 'flaky-checker-ledger.json')
CRITERIA_VERSION = '2026-09-13.1'

# ── THRESHOLDS, decided before any checker was measured ───────────────────
RUNS_PER_MEASURE = 3        # per invocation; evidence accumulates in the ledger
MIN_RUNS_TO_JUDGE = 4       # below this, "stable" is not a claim worth making
QUARANTINE_AT = 0.05        # >5% of runs disagreeing with the modal verdict
WATCH_AT = 0.0001           # ANY disagreement at all is worth watching first
REENTRY_RUNS = 10           # consecutive clean runs before it may come back
SAMPLE_CAP = 4              # distinct verdict excerpts kept per checker


def tree_hash():
    """What the working tree looked like. A flip across two trees is not a flip."""
    p = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
    dirty = subprocess.run(['git', 'status', '--porcelain'], capture_output=True,
                           text=True, encoding='utf-8', errors='replace', cwd=REPO).stdout
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
    keep = [l for l in dirty.split(chr(10))
            if 'flaky-checker-ledger.json' not in l]
    dirty = chr(10).join(keep)
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


# ── THE RUN COUNT AT WHICH THE WATCH BAND EXISTS AT ALL ───────────────────
# DERIVED FROM THE THRESHOLD, NOT PICKED -- so it moves on its own if
# QUARANTINE_AT is ever changed, which is convention 4 applied to the
# estimator rather than to the alarm.
#
# ITEM 89 (the look-elsewhere effect) IS WHAT SENT ME LOOKING, AND THE
# ARITHMETIC UNDERNEATH IT IS WORSE THAN THE MULTIPLICITY. With n runs the
# smallest NON-ZERO flip rate this estimator can produce is 1/n. The WATCH band
# is (WATCH_AT, QUARANTINE_AT] = (0.0001, 0.05], so a single disagreement lands
# in WATCH only when 1/n <= 0.05, i.e. n >= 20.
#
# MEASURED ON THE REAL LEDGER, 2026-09-14: all 37 registered checkers sit at
# n=6 or n=12. At n=6 one disagreement is 0.167 -- more than THREE TIMES
# QUARANTINE_AT. So the WATCH tier was unreachable for the entire fleet, and
# every first chance flip went straight to QUARANTINE.
#
# That directly contradicts this file's own stated rule. The MARGIN section
# says the alarm is deliberately set tighter than the quarantine bar because
# "drift toward the limit is the signal worth having", and FIXTURES asserts
# "a single disagreement is WATCH, never an immediate quarantine" -- using
# n=40, where the arithmetic happens to work. No fixture covered the n=4..19
# regime, which is the only regime any real checker has ever been in, so the
# lock passed 5/5 while the rule it encodes could not fire.
#
# THE FIX IS THE STATED RULE, IMPLEMENTED -- NOT A NEW THRESHOLD. Nothing
# pre-registered moves: QUARANTINE_AT, WATCH_AT and MIN_RUNS_TO_JUDGE are
# untouched. A post-hoc threshold change after seeing the data is exactly what
# convention 1 forbids. What changes is that ONE disagreement is WATCH at any
# run count, because that is what the file already said and what the estimator
# was too coarse to express.
#
# And it is the right answer for item 89 as well: a single spurious flip is by
# far the likeliest chance event across a fleet this size, so it is precisely
# the one that must not spend a quarantine.
WATCH_EXPRESSIBLE_AT = int(math.ceil(1.0 / QUARANTINE_AT))


def classify(entry):
    rate, runs, distinct = flip_rate(entry)
    obs = entry.get('observations', [])
    # ── AN UNRUNNABLE CHECKER IS NOT A STABLE ONE ─────────────────────────
    # A tool that cannot be EXECUTED raises the same exception every run, so
    # every digest matched, so the flip rate was 0.0 and this returned STABLE.
    # The least-verified thing in the fleet read as the most reliable. That is
    # the fail-open shape PR 1.11 names, inside the tool whose job is judging
    # other tools -- so "could not run" gets its own verdict rather than being
    # folded into a pass. Checked FIRST, before the run-count gate, because a
    # handful of failed launches is not evidence of anything at all.
    if obs and all(o.get('err') for o in obs):
        return 'UNRUNNABLE', rate, runs
    if runs < MIN_RUNS_TO_JUDGE:
        return 'TOO-FEW-RUNS', rate, runs
    # ONE disagreement is WATCH, at every run count. See WATCH_EXPRESSIBLE_AT.
    disagreements = int(round(rate * runs))
    if disagreements == 1:
        return 'WATCH', rate, runs
    if rate > QUARANTINE_AT:
        return 'QUARANTINE', rate, runs
    if rate > WATCH_AT:
        return 'WATCH', rate, runs
    return 'STABLE', rate, runs


def chance_expectation(n_checkers, runs_each, per_run_flip=0.01):
    """Expected number of checkers showing >=1 disagreement BY CHANCE.

    Item 89's substance, published as a number rather than applied as a silent
    correction. A fleet-wide WATCH count is not N independent findings: with
    N checkers each run n times, even a small per-run non-determinism produces
    an expected crop of WATCH verdicts owing nothing to any real defect.

    `per_run_flip` is an ASSUMPTION, not a measurement, and is labelled as one
    wherever it is printed. It is not calibrated from this ledger on purpose --
    deriving the chance rate from the same observations it is used to judge
    would be the validation-eats-its-own-subject shape (disciplines item 5).
    """
    if not n_checkers or not runs_each:
        return 0.0
    return n_checkers * (1.0 - (1.0 - per_run_flip) ** runs_each)


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

    # ── THE UNRUNNABLE STATE, WHICH USED TO READ AS THE BEST IN THE FLEET ──
    # Every observation an execution failure. Identical digests, flip rate
    # 0.0, and the old classifier called that STABLE. These two fixtures are
    # the difference between a tool that always agrees with itself because it
    # is reliable and one that always agrees because it never ran.
    ('a checker that NEVER RAN is UNRUNNABLE, not STABLE',
     {'observations': [{'digest': 'x', 'tree': 't', 'err': True}] * 6},
     'UNRUNNABLE'),
    ('CONTROL: one failed launch among real runs is NOT unrunnable -- that is '
     'a flip, and it must still reach the flake logic',
     {'observations': [{'digest': 'a', 'tree': 't', 'err': False}] * 5
      + [{'digest': 'x', 'tree': 't', 'err': True}]},
     'WATCH'),
    ('a checker just over the bar is QUARANTINE, not WATCH',
     _e(['a'] * 18 + ['b', 'b']), 'QUARANTINE'),

    # ── THE REGIME EVERY REAL CHECKER IS ACTUALLY IN, AND NOTHING COVERED IT ──
    # The five fixtures above use n = 12, 40, 6, 2 and 20. The single-
    # disagreement case -- the one the rule above is named after -- was only
    # ever tested at n=40, where 1/40 = 0.025 happens to land inside the WATCH
    # band. MEASURED ON THE REAL LEDGER 2026-09-14: all 37 registered checkers
    # sit at n=6 or n=12, where one disagreement is 0.167 and 0.083, BOTH ABOVE
    # QUARANTINE_AT. So the stated rule could not fire anywhere in the fleet
    # while the lock read 5/5.
    #
    # These three are ADDITIONS covering a gap, not fixtures bent to match
    # output -- and their expected verdicts come from this file's own prose
    # ("a single disagreement is WATCH, never an immediate quarantine"), which
    # was written before any of this was measured.
    ('one disagreement at the fleet"s ACTUAL run count is WATCH, not QUARANTINE',
     _e(['a'] * 5 + ['b']), 'WATCH'),
    ('...and at the other real run count too',
     _e(['a'] * 11 + ['b']), 'WATCH'),
    ('CONTROL: TWO disagreements at that same run count is still QUARANTINE, '
     'so this is not a blanket amnesty for small samples',
     _e(['a'] * 4 + ['b', 'b']), 'QUARANTINE'),
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


# ── HOW A CHECKER IS RUN, BY EXTENSION (2026-09-14) ───────────────────────
# THE BLOCKER THIS REMOVES was named in tools/report_only_checks.py's
# NOT_PROMOTED entry for restore_coherence_check.js: the ledger shelled out
# with `sys.executable` unconditionally, so a promoted .js checker would have
# been "measured" by handing a JavaScript file to Python. That does not fail
# loudly -- Python exits non-zero with a SyntaxError, IDENTICALLY every run, so
# the flip rate is 0.0 and the checker is reported STABLE. The first .js
# promotion would have created a registry entry nothing could measure, and the
# ledger would have said it was the most reliable tool on the platform.
#
# `node` is not assumed present. An interpreter that is missing is a
# COULD-NOT-MEASURE and is named; it is never folded into a verdict, which is
# the same rule the push gate's check-9 lock and this file's own third state
# already follow.
INTERPRETERS = {'.py': [sys.executable], '.js': ['node']}


def interpreter_for(tool):
    """argv prefix to run `tool`, or None if this runner cannot run it.

    None is a REFUSAL, not a skip: the caller records the tool as unrunnable
    and main() prints it. Returning a best-guess interpreter would reproduce
    exactly the defect this function exists to remove.
    """
    ext = os.path.splitext(tool)[1].lower()
    argv = INTERPRETERS.get(ext)
    if not argv:
        return None
    if ext != '.py':
        # Probe the interpreter once rather than discovering its absence as a
        # per-run exception that then looks like a stable verdict.
        try:
            r = subprocess.run(argv + ['--version'], capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=30)
            if r.returncode != 0:
                return None
        except Exception:                                       # noqa: BLE001
            return None
    return list(argv)


def decided_tools():
    """Every tool a decision HAS been recorded about -- promoted or not.

    Both registries, because the question this answers is "did anybody choose",
    not "was it promoted". Read with the same source regex `registry_tools()`
    uses so the two cannot disagree about what a registry entry looks like.

    COMMA-SPLIT ON PURPOSE. Two NOT_PROMOTED entries name several tools in one
    string, so those names are unreachable by an exact-name lookup. Without the
    split this undercounts recorded decisions and OVER-reports the gap.

    ── IT IMPORTS RATHER THAN PARSES, AND THE DIFFERENCE WAS MEASURED ──────
    The first version regexed the source, in the style of `registry_tools()`
    above. It found 59 decided names where importing the module finds 61 --
    missing `licence_recoverability_check.py` and `rf_claim_gate_live_probe.py`,
    both buried in the same comma-packed NOT_PROMOTED string. So the gap read
    24 when it is 23.

    An over-report is the safer direction and it is still wrong, and a reader
    cannot tell a parser's blind spot from a real gap. The import is the
    structure; the regex is a guess at it. The regex stays only as a FALLBACK,
    and when it is used the caller SAYS SO instead of quoting the figure as if
    both methods agreed.
    """
    try:
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        import report_only_checks as _roc

        def _names(e):
            v = (e.get('tool') if isinstance(e, dict)
                 else (e[0] if isinstance(e, (list, tuple)) else e))
            return [os.path.basename(x.strip())
                    for x in str(v).split(',') if x.strip()]
        out = set()
        for e in list(_roc.REGISTRY) + list(_roc.NOT_PROMOTED):
            out.update(_names(e))
        return sorted(out), 'imported'
    except Exception as e:
        src = io.open(os.path.join(REPO, 'tools', 'report_only_checks.py'),
                      encoding='utf-8').read()
        out = set()
        for raw in re.findall(r"'tool':\s*'([^']+)'", src):
            out.update(os.path.basename(x.strip())
                       for x in raw.split(',') if x.strip())
        return sorted(out), 'REGEX FALLBACK (%s) -- known to undercount' % type(e).__name__


def measure_order(led, tools, th):
    """WEAKEST EVIDENCE FIRST, and this ordering is the whole of item 22.

    It used to be alphabetical. A full pass is ~37 checkers times N runs of a
    subprocess each, and one of them -- comment_sensitivity_check.py -- takes
    103 SECONDS PER RUN, measured, against a fleet median under a second. So a
    pass never finished inside the window this repo's sessions actually get,
    and because the order was fixed, THE SAME TAIL STARVED EVERY TIME. Eleven
    checkers had never been measured at all, months after the others had six
    observations each: committer_identity, invisible_in_pattern, master_plan,
    metamorphic, schema_snapshot_freshness, soup_register, tooling_inventory,
    traceability_matrix, truthy_sum, vercel_config, write_without_readback.

    Sorting by evidence-at-this-tree means a truncated pass always advances the
    checkers that know least, so coverage CONVERGES instead of a fixed
    suffix being permanently unmeasured. It does not make the pass faster and
    is not meant to -- it makes the part that does run the part worth running.

    THE SECOND KEY IS EVIDENCE AT *ANY* TREE, AND WITHOUT IT THIS FIX DOES
    NOTHING. Found by watching the first version run: the tree hash changes on
    every commit, so the moment this landed, all 37 checkers had zero
    observations at the new tree, every weight tied at zero, the tie broke on
    name -- and the pass was ALPHABETICAL AGAIN, starving exactly the same
    tail. On a repo with four active sessions a commit lands every few minutes,
    so "evidence at this tree" alone is almost always zero for everybody and
    carries no ordering information at all.

    A checker with six observations from YESTERDAY'S tree still knows more
    about itself than one that has never been run at any tree. That is not
    evidence about the current tree -- `classify` still refuses to mix trees --
    it is evidence about which checker is most starved, which is a different
    question and the one this ordering answers.

    Ties break on name so the order is deterministic, which matters: two runs
    that disagree because they measured different tools in different orders
    would be indistinguishable from a flip.
    """
    def weight(t):
        e = led.get('checkers', {}).get(t) or {}
        all_obs = e.get('observations', [])
        here = [o for o in all_obs if o.get('tree') == th]
        return (len(here), len(all_obs), t)
    return sorted(tools, key=weight)


def measure(led, runs=RUNS_PER_MEASURE, budget=None):
    th = tree_hash()
    tools = [t for t in registry_tools() if os.path.exists(os.path.join(REPO, 'tools', t))]
    tools = measure_order(led, tools, th)
    started = time.time()
    reached = []
    unrunnable = []
    for t in tools:
        # A BUDGET THAT STOPS CLEANLY, because the alternative is being KILLED,
        # and a killed pass prints nothing at all -- so the run that covered a
        # third of the fleet and the run that covered all of it look the same
        # from outside. Checked BEFORE each checker rather than after, so the
        # stated budget is the one honoured. Nothing is capped silently: what
        # was not reached is printed and named by main().
        if budget is not None and time.time() - started >= budget:
            break
        p = os.path.join(REPO, 'tools', t)
        argv = interpreter_for(t)
        if argv is None:
            # AN UNRUNNABLE CHECKER IS NOT A STABLE ONE. Skipped WITHOUT an
            # observation and named by main(), rather than measured into a
            # digest -- see interpreter_for().
            unrunnable.append(t)
            continue
        reached.append(t)
        e = led['checkers'].setdefault(t, {'observations': []})
        for _ in range(runs):
            err = False
            try:
                r = subprocess.run(argv + [p], capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', cwd=REPO, timeout=180)
                out = normalise((r.stdout or '') + (r.stderr or '')) + '|exit=' + str(r.returncode)
            except Exception as ex:
                out = 'RUNNER-ERROR:' + type(ex).__name__
                err = True
            dg = hashlib.sha256(out.encode('utf-8')).hexdigest()[:16]
            # `err` IS RECORDED, AND WITHOUT IT THE WORST CASE READS BEST.
            # A checker that cannot be EXECUTED raises the same exception every
            # run, so it produced the same digest every run, so flip_rate was
            # 0.0 and classify() called it STABLE. A tool that never ran once
            # was the most stable thing in the fleet -- the fail-open shape
            # this platform names as its most repeated defect, inside the tool
            # whose whole job is judging other tools.
            e['observations'].append({'digest': dg, 'tree': th, 'err': err})
            # ONE SAMPLE PER DISTINCT VERDICT, and this exists because the
            # first real flip this tool ever found was UNDIAGNOSABLE
            # (comment_sensitivity_check.py, 2026-09-14, rate 0.333 over 12
            # runs). The ledger held two digests and nothing else, so there was
            # no way to see WHAT had differed -- the evidence a quarantine is
            # required to carry was a pair of hashes. A detector that can say
            # THAT something flipped and never WHAT is a detector whose findings
            # cannot be acted on.
            #
            # BOUNDED HARD: first occurrence only, first 400 characters, and
            # only while fewer than SAMPLE_CAP distinct verdicts are held. A
            # genuinely random checker would otherwise grow the ledger without
            # limit, which is how a diagnostic aid becomes its own problem.
            samples = e.setdefault('samples', {})
            if dg not in samples and len(samples) < SAMPLE_CAP:
                samples[dg] = out[:400]
        # ACCURACY: observations from a DIFFERENT tree are not comparable. Keep
        # only the current tree's -- a flip measured across an edit is the tool
        # noticing the edit, which is the tool working.
        e['observations'] = [o for o in e['observations'] if o.get('tree') == th][-40:]
        # Samples for digests no longer held are dropped with them -- an
        # excerpt of a verdict from a tree nobody can reproduce is worse than
        # nothing, because it reads as evidence about the current one.
        live_digests = {o['digest'] for o in e['observations']}
        if e.get('samples'):
            e['samples'] = {k: v for k, v in e['samples'].items() if k in live_digests}
        # SAVED AFTER EVERY CHECKER, not once at the end. A full pass is ~200
        # subprocess runs and outran a 560-second window twice; the whole
        # measurement was then lost, because the single save at the end never
        # ran. Evidence that only lands if the process is allowed to finish is
        # evidence this repo will never actually gather -- the sessions here get
        # interrupted constantly. A partial pass now contributes what it managed.
        save_ledger(led)
    return reached, tools, unrunnable


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
        # --runs N lets ONE invocation gather enough observations in ONE tree
        # state. Without it, accumulating across invocations needs a tree that
        # nobody touches in between -- and on a repo with four active sessions
        # that never happens, so the classifier answered TOO-FEW-RUNS forever.
        # This is NOT loosening the threshold to get a number: MIN_RUNS_TO_JUDGE
        # is unchanged. It is letting a single measurement be big enough to
        # reach it honestly.
        runs = RUNS_PER_MEASURE
        if '--runs' in argv:
            i = argv.index('--runs')
            runs = max(1, int(argv[i + 1])) if i + 1 < len(argv) else runs
        budget = None
        if '--budget-seconds' in argv:
            i = argv.index('--budget-seconds')
            budget = max(1, int(argv[i + 1])) if i + 1 < len(argv) else None
        reached, tools, unrunnable = measure(led, runs, budget)
        save_ledger(led)
        print('  measured %d of %d registered checker(s), %d run(s) each, tree %s'
              % (len(reached), len(tools), runs, tree_hash()))
        # PRINTED, because a list that is computed and never shown is a
        # measurement nobody can act on -- and I did exactly that to the R3
        # counter in ai_prompt_refusal_check.py earlier today. A registered
        # checker this runner cannot execute is the most important line in the
        # output: it has no evidence and no prospect of any.
        if unrunnable:
            print('  CANNOT BE RUN BY THIS RUNNER: %d registered checker(s). Not '
                  'measured, NOT a pass,' % len(unrunnable))
            print('     and no amount of re-running changes it. Either add the '
                  'interpreter to INTERPRETERS')
            print('     or record a NOT_PROMOTED reason -- an unmeasurable '
                  'registry entry is the shape')
            print('     the 2026-09-14 coverage pass was widened to expose:')
            for t in unrunnable:
                print('     - ' + t)
        # NO SILENT CAP. A pass that stopped early and says nothing is a pass
        # that reads as complete; the skipped names are printed, not a count.
        if len(reached) + len(unrunnable) < len(tools):
            skipped = [t for t in tools
                       if t not in set(reached) and t not in set(unrunnable)]
            print('  STOPPED EARLY on a %ss budget -- %d checker(s) NOT measured '
                  'this pass, and that is not evidence about them:' % (budget, len(skipped)))
            for t in skipped:
                print('     - ' + t)
            print('  They sort FIRST next pass, because the order is '
                  'weakest-evidence-first. Run again to advance them.')

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
                           text=True, encoding='utf-8', errors='replace', cwd=REPO).stdout.strip() or '2026-01-01'
    overdue = [r for r in rows if r['quarantined'] and r['quarantine']
               and r['quarantine'].get('deadline', '9999') < today]

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'rows': rows,
                          'overdue': [r['tool'] for r in overdue]}, indent=1))
    else:
        by = {}
        for r in rows:
            by.setdefault(r['verdict'], []).append(r)
        # COVERAGE DISCLOSURE. A partial pass that reports only what it reached
        # reads as a clean fleet -- the shape docs/SAIRN-PROCESS-RULES.md 1.7
        # names. The registered-but-unmeasured checkers are counted and listed.
        try:
            registered = set(registry_tools())
        except Exception:
            registered = set()
        measured = set(r['tool'] for r in rows)
        unmeasured = sorted(registered - measured)
        print('  checkers with evidence: %d of %d registered'
              % (len(rows), len(registered) or len(rows)))
        if unmeasured:
            print('  NOT MEASURED AT ALL   : %d  <- READ THIS BEFORE THE ROWS BELOW.'
                  % len(unmeasured))
            print('     A partial pass that reports only what it reached reads as a')
            print('     clean fleet. These have no evidence either way:')
            for t in unmeasured:
                print('       %s' % t)

        # ── THE CATEGORY THIS DISCLOSURE COULD NOT SEE ─────────────────────
        # "of N registered" is an honest denominator for a registry, and it is
        # the WRONG denominator for the question anyone actually asks: is every
        # checker on this platform measured. A tool that was never registered
        # is not "measured 0 times" here -- it is absent from the arithmetic
        # entirely, so the fleet reads as fully covered while a third of it is
        # outside the frame.
        #
        # MEASURED 2026-09-14: 64 check-shaped tools on disk, 29 in REGISTRY,
        # 12 recorded in NOT_PROMOTED, and 23 IN NEITHER -- no decision either
        # way, and therefore never measured for flakiness. Several were built
        # in the preceding two days. The 11 unwired checkers this platform
        # already found once had exactly this shape, so the disclosure is
        # widened rather than the finding re-discovered a third time.
        #
        # NOT_PROMOTED IS SPLIT ON COMMAS ON PURPOSE. Two of its entries pack
        # several tool names into one string, so five names are invisible to
        # an exact-name lookup -- which is how this count read 25 before the
        # split and 23 after. The packing is a data-shape problem in
        # report_only_checks.py with an owner; what must not happen is this
        # disclosure inheriting the undercount.
        try:
            _dec_list, _dec_how = decided_tools()
            _decided = set(_dec_list)
            # ── WIRING IS A DECISION TOO, AND THIS MISSED IT AT FIRST ───────
            # The first version of this disclosure counted 23 tools as having
            # no recorded decision. EIGHT of those are wired MORE strongly than
            # report-only -- six reachable from the push gate (BLOCKING), one
            # report-only through a PostToolUse hook, one advisory through
            # SessionStart. For those, "nothing measures them and no one chose
            # that" is simply false, and asking for a NOT_PROMOTED line saying
            # "we decided not to promote this to report-only" about something
            # that already blocks a push is a sentence with no meaning.
            #
            # So the classification counts. not_promoted() in
            # tooling_inventory.py records this exact mistake being made twice
            # before -- a count that overstated the gap because a source of
            # truth existed and was not read. This is the third time, in a
            # disclosure written to expose the opposite error, which is why the
            # wiring is now consulted rather than assumed absent.
            try:
                sys.path.insert(0, os.path.join(REPO, 'tools'))
                import tooling_inventory as _ti
                _out = _ti.classify()
                _cls = next((x for x in (_out if isinstance(_out, tuple) else (_out,))
                             if isinstance(x, dict)), {})
                _wired = set(t for t, k in _cls.items()
                             if k in ('BLOCKING', 'REPORT-ONLY', 'ADVISORY'))
                _decided |= _wired
                _dec_how += ' + wiring'
            except Exception as _we:
                _dec_how += (' -- WIRING NOT CONSULTED (%s), so the count below '
                             'OVER-reports by however many tools are hook- or '
                             'gate-wired' % type(_we).__name__)
            _ondisk = [os.path.basename(f) for f in subprocess.run(
                ['git', 'ls-files', 'tools/'], capture_output=True, text=True, encoding='utf-8', errors='replace',
                cwd=REPO).stdout.split(chr(10))
                if f.endswith(('_check.py', '_check.js', '_scan.py', '_sweep.py'))]
            _nodecision = sorted(set(_ondisk) - _decided)
        except Exception as _e:
            _nodecision = None
            print('  COULD NOT TELL how many tools have no recorded decision '
                  '(%s) -- so do NOT' % type(_e).__name__)
            print('     read the registered-vs-measured figures above as fleet '
                  'coverage.')
        if _nodecision:
            print('  NO RECORDED DECISION  : %d of %d check-shaped tools on '
                  'disk  [registries %s]'
                  % (len(_nodecision), len(set(_ondisk)), _dec_how))
            print('     Not promoted (REGISTRY), not recorded as deliberately '
                  'unpromoted')
            print('     (NOT_PROMOTED), AND not wired into a hook or the push '
                  'gate -- so nothing')
            print('     measures them and nobody chose that. This is the '
                  '11-unwired-checkers')
            print('     shape; the fix is one NOT_PROMOTED line each, with a '
                  'reason -- not a')
            print('     promotion. A hook- or gate-wired tool is NOT listed '
                  'here: its wiring is')
            print('     the decision, and asking it for a not-promoted-to-'
                  'report-only line would')
            print('     be a sentence with no meaning.')
            for t in _nodecision:
                print('       %s' % t)
        for v in ('QUARANTINE', 'UNRUNNABLE', 'WATCH', 'STABLE', 'TOO-FEW-RUNS'):
            note = {'QUARANTINE': '  <- flipped on unchanged code past the bar',
                    'UNRUNNABLE': '  <- NEVER EXECUTED. Not a pass, and it used '
                                  'to read as STABLE',
                    'WATCH': '  <- flipped at least once; alarm is TIGHTER than the bar',
                    'STABLE': '',
                    'TOO-FEW-RUNS': '  <- NOT a pass. 2/2 stable is not a claim'}[v]
            print('    %-14s %3d%s' % (v, len(by.get(v, [])), note))

        # ── ITEM 89: THE TRIALS FACTOR, PUBLISHED RATHER THAN CORRECTED ────
        # The verdicts above are PER-CHECKER, and every threshold in this file
        # is a per-checker threshold. Read down a column of 37 of them and the
        # look-elsewhere effect applies: with that many measurements, some
        # elevated flip rates are expected from chance alone, and a WATCH count
        # of 3 is NOT three independent findings.
        #
        # It is REPORTED, not silently corrected, and that is the deliberate
        # part. Tightening the bar by a multiplicity factor would be a post-hoc
        # threshold change of exactly the kind convention 1 forbids, and it
        # would also hide real flakiness in a fleet that has already recorded
        # one genuine case (literal_drift_check.py, PYTHONHASHSEED). The number
        # below lets a reader discount the column themselves.
        #
        # The per-run assumption is LABELLED AS AN ASSUMPTION every time it is
        # printed, because it is not measured -- and deliberately is not
        # calibrated from this same ledger, which would be the validation
        # feeding on its own subject.
        runs_each = [r.get('runs') or 0 for r in rows]
        typical = max(set(runs_each), key=runs_each.count) if runs_each else 0
        # WHAT THE TRIALS FACTOR DOES AND DOES NOT EXPLAIN. Multiplicity
        # explains a crop of checkers showing ONE disagreement. It does NOT
        # explain a checker disagreeing repeatedly: at 4 flips in 12 runs the
        # chance of that arising from a small per-run probability is negligible,
        # so quoting an expected-by-chance figure next to it would DISCOUNT A
        # REAL DEFECT -- the opposite error, and the more expensive one, because
        # this fleet has already recorded one genuine flaky checker
        # (literal_drift_check.py, PYTHONHASHSEED). The two populations are
        # therefore reported separately rather than summed.
        # THE KEY IS `flip_rate`, NOT `rate`, AND THE FIRST VERSION GOT IT
        # WRONG -- reading a key that does not exist gave None, coerced to 0,
        # and printed "exactly one: 0 / more than one: 0" beside a live
        # QUARANTINE. A quiet zero from a bad lookup is indistinguishable from
        # a real zero, which is why the disagreement counts are cross-checked
        # against the verdict column below rather than trusted.
        def _disagreements(r):
            return int(round((r.get('flip_rate') or 0) * (r.get('runs') or 0)))

        single = [r for r in rows if _disagreements(r) == 1]
        repeat = [r for r in rows if _disagreements(r) > 1]
        print('')
        print('  THE TRIALS FACTOR (item 89 -- look-elsewhere). These are %d '
              'per-checker verdicts,' % len(rows))
        print('  each against a per-checker threshold, so the column below is '
              'not %d independent' % len(rows))
        print('  findings. Multiplicity explains SINGLE disagreements; it does '
              'NOT explain repeats.')
        for p in (0.005, 0.01, 0.02):
            print('    if each run flips with probability %.3f (ASSUMED, not '
                  'measured), expect %.1f of %d to show >=1'
                  % (p, chance_expectation(len(rows), typical, p), len(rows)))
        print('    OBSERVED, split because the two mean different things:')
        print('      exactly one disagreement : %d  <- this is the population '
              'the figures above apply to' % len(single))
        print('      more than one            : %d  <- NOT explained by '
              'multiplicity; read the evidence' % len(repeat))
        print('      typical run count        : %d' % typical)
        # CROSS-CHECK, because the split is computed from a DIFFERENT field
        # than the verdict column and a mismatch means one of them is lying.
        # This is the arm that would have caught the `rate`-vs-`flip_rate`
        # lookup immediately instead of printing a plausible pair of zeros.
        _flagged = len(by.get('WATCH', [])) + len(by.get('QUARANTINE', []))
        if len(single) + len(repeat) != _flagged:
            print('      !! THESE TWO LINES DISAGREE WITH THE VERDICT COLUMN '
                  '(%d vs %d flagged).' % (len(single) + len(repeat), _flagged))
            print('         The split is computed from flip_rate x runs and the '
                  'column from classify();')
            print('         when they differ, NEITHER figure can be quoted. '
                  'Do not discount anything')
            print('         on the strength of the trials factor until this '
                  'agrees.')
        print('  Nothing is thresholded on any of this -- it is yours to '
              'discount with, and every')
        print('  per-checker row below still names its own evidence.')
        if typical and typical < WATCH_EXPRESSIBLE_AT:
            print('')
            print('  AND THE ESTIMATOR IS COARSER THAN THE BANDS IT FEEDS: at '
                  '%d runs the smallest' % typical)
            print('  non-zero flip rate expressible is 1/%d = %.3f, while the '
                  'WATCH band is (%g, %g].'
                  % (typical, 1.0 / typical, WATCH_AT, QUARANTINE_AT))
            print('  WATCH is reachable by RATE only at %d+ runs, so a single '
                  'disagreement is classified' % WATCH_EXPRESSIBLE_AT)
            print('  as WATCH explicitly rather than by rate. See '
                  'WATCH_EXPRESSIBLE_AT -- this was measured, not')
            print('  assumed, and it had disabled the WATCH tier for the whole '
                  'fleet.')
        for r in by.get('QUARANTINE', []) + by.get('WATCH', []):
            print('      %-34s rate %.3f over %d run(s)' % (r['tool'], r['flip_rate'], r['runs']))
            # THE VERDICTS THEMSELVES, not just the rate. A flip reported as two
            # hashes is a finding nobody can act on -- which is what the first
            # real flip here turned out to be.
            samples = (led.get('checkers', {}).get(r['tool']) or {}).get('samples') or {}
            if len(samples) > 1:
                print('        the %d verdicts it gave, first occurrence of each:' % len(samples))
                for dg, ex in sorted(samples.items()):
                    print('          [%s] %s' % (dg, ex[:220]))
            else:
                print('        NO VERDICT TEXT IS ON FILE for this tool -- its observations')
                print('        predate sample capture, so WHAT differed is not recoverable')
                print('        from this ledger. Re-measure to record it. That is a gap in')
                print('        the evidence, not a reason to discount the rate.')
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
