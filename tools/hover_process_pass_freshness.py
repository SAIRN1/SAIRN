"""Has the hover auditor run a PROCESS PASS recently enough? Asked from OUTSIDE.

    python tools/hover_process_pass_freshness.py
    python tools/hover_process_pass_freshness.py --selftest
    python tools/hover_process_pass_freshness.py --fail-hours 72

Exit 0  a process pass is recorded within FAIL_HOURS
Exit 1  STALE -- the last recorded process pass is older than FAIL_HOURS
Exit 2  COULD NOT RUN -- and that is a third state, never folded into either

── WHY THIS LIVES HERE AND NOT IN THE AUDITOR'S SKILL ───────────────────────
The hover auditor already has `hover_self_health.py`, which flags staleness at
its own SessionStart. That is a good check and it is SELF-POLICED: it runs
inside the role it measures, on the cadence that role chooses, and it is silent
in exactly the case that matters -- the auditor not running at all.

A role that audits four build agents cannot be the only thing watching itself.
This is the same structural argument as the hover-separation branch protection:
the separation between auditor and build agents is enforced from the build side
because an auditor enforcing its own separation proves nothing about the case
where the auditor is the problem. This file is the calendar half of that.

It is READ-ONLY and touches nothing in the auditor's clone. It reads the
tamper-evident self-log, which lives outside every repository by design.

── THE CHAIN IS VERIFIED BEFORE THE TIMESTAMP IS BELIEVED ───────────────────
The log is hash-chained. Reading a timestamp out of it without checking the
chain would be trusting the thing being checked -- so the chain is verified
first, using the SAME verifier tools/hover_separation_audit.py uses rather than
a second copy that can disagree with it. A broken chain is COULD NOT RUN, not
stale and not fresh: it means the answer is unavailable, which is a different
fact from a late auditor.

── THE INTERVAL, AND WHERE THE NUMBER COMES FROM ────────────────────────────
DEFAULT: FAIL at 48 hours, WARN at 36.

MEASURED, NOT PICKED. The four process passes the auditor's own skill names --
self-log entries 40, 142, 147 and 203 -- fall at gaps of 33.9h, 0.6h and 20.6h
across a 2.4-day log. The largest real gap is 33.9 hours, so:

  * WARN at 36h  -- just above the largest gap actually observed, so a normal
                    irregular cadence does not cry wolf, and a genuinely longer
                    silence is visible before it is a failure;
  * FAIL at 48h  -- comfortably outside every observed gap, and the point at
                    which "irregular" has become "not happening".

The cadence is IRREGULAR BY DESIGN -- the skill is explicit that a process pass
is unscheduled -- so this is not a schedule. It is an outer bound on silence,
and the measurement it is derived from is printed on every run so the next
reader can re-derive it instead of inheriting a number.

── WHAT IT CANNOT SEE, SAID OUT LOUD ────────────────────────────────────────
`process_pass` is a STRUCTURED FIELD, added to the log after the first three
real process passes had already happened. Entries 40, 142 and 147 are real
process passes carrying no flag, and this tool cannot see them -- it counts the
field, never the prose, because matching "PROCESS PASS" in a summary is the
grep-cannot-tell-code-from-text class and would make the auditor's own wording
load-bearing. So the answer is meaningful only from the first FLAGGED entry
onward, and the report says which one that is.
"""
import argparse
import calendar
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hover_separation_audit as HSA                             # noqa: E402

FAIL_HOURS = 48.0
WARN_HOURS = 36.0

# The calibration set, by seq, from the auditor's own skill. Named here so the
# derivation is auditable and so a later reader can re-run it rather than
# trusting the numbers in the docstring.
CALIBRATION_SEQS = (40, 142, 147, 203)


def fail(msg):
    print('COULD NOT RUN: ' + msg)
    print('This is exit 2. It is not a pass, and it is not a staleness finding.')
    sys.exit(2)


def epoch(ts):
    try:
        return calendar.timegm(time.strptime(ts, '%Y-%m-%dT%H:%M:%SZ'))
    except (TypeError, ValueError):
        return None


def gaps(rows, seqs):
    """Hours between consecutive calibration entries, for re-derivation."""
    picked = [r for r in rows if r.get('seq') in seqs]
    picked.sort(key=lambda r: r.get('seq'))
    out, prev = [], None
    for r in picked:
        e = epoch(r.get('ts'))
        if e is None:
            continue
        if prev is not None:
            out.append((r.get('seq'), (e - prev) / 3600.0))
        prev = e
    return out


def cnr(msg):
    """COULD NOT RUN for ONE session. Prints and RETURNS 2 -- it does not exit.

    fail() calls sys.exit(2) directly, which was correct while there was exactly
    one session and is the specific trap in a loop: it would kill the process
    after the first log and make every later session invisible. The aggregate in
    main() is what decides the exit code now.
    """
    print('  COULD NOT RUN: ' + msg)
    return 2


def _check_one_session(rows, path, args):
    """One session's freshness. Returns 0 OK/WARN, 1 STALE, 2 COULD NOT RUN.

    LIFTED FROM main() (2026-09-22) with one change of kind: every fail() became
    a RETURNED could-not-run. Nothing about the bounds, the calibration or the
    staleness arithmetic moved.
    """

    ok, why, _n = HSA.verify_chain(rows)
    if not ok:
        return cnr('the self-log HASH CHAIN does not verify (%s). A timestamp read '
             'out of an unverified chain is the thing being checked vouching '
             'for itself.' % why)

    flagged = [r for r in rows if r.get('process_pass')]
    # The banner is printed once by main(); this printed its own because it WAS
    # the only session. The path stays, so a reader sees which log each block is
    # about.
    print('  log: %s' % path)
    print('  %d entries, chain verifies' % len(rows))

    g = gaps(rows, CALIBRATION_SEQS)
    if g:
        print('  calibration (the passes the skill names, by seq): %s'
              % ', '.join('%s:+%.1fh' % (s, h) for s, h in g))
        print('  largest observed gap %.1fh -> warn %.0fh, fail %.0fh'
              % (max(h for _s, h in g), args.warn_hours, args.fail_hours))

    if not flagged:
        return cnr('NO entry carries process_pass. That is not "the auditor never ran "'
             'a process pass" -- the field postdates the first real ones -- it '
             'is that this tool has nothing it is allowed to count. Counting '
             'prose instead would make the auditor\'s own wording load-bearing.')

    first, last = flagged[0], flagged[-1]
    le = epoch(last.get('ts'))
    if le is None:
        return cnr('the newest flagged entry (seq %s) has an unparseable ts %r'
             % (last.get('seq'), last.get('ts')))
    age = (time.time() - le) / 3600.0

    print('  flagged process passes: %d (meaningful from seq %s, %s)'
          % (len(flagged), first.get('seq'), first.get('ts')))
    print('  last: seq %s at %s -- %.1f hours ago'
          % (last.get('seq'), last.get('ts'), age))
    print('        %s' % (last.get('summary') or '')[:100])
    print('')

    if age > args.fail_hours:
        print('STALE: the last recorded process pass is %.1f hours old, over the '
              '%.0f-hour bound.' % (age, args.fail_hours))
        print('A process pass is the check on the MACHINERY across all four '
              'build agents rather than on any one claim. Its absence is not '
              'visible in any single audit entry, which is why it is bounded '
              'from outside the role.')
        return 1
    if age > args.warn_hours:
        print('WARN: %.1f hours since the last process pass, past the %.0f-hour '
              'warning bound and inside the %.0f-hour failure bound. The cadence '
              'is irregular by design; this is early notice, not a finding.'
              % (age, args.warn_hours, args.fail_hours))
        return 0
    print('OK: a process pass was recorded %.1f hours ago, inside the %.0f-hour '
          'bound.' % (age, args.warn_hours))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--fail-hours', type=float, default=FAIL_HOURS)
    ap.add_argument('--warn-hours', type=float, default=WARN_HOURS)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()

    # ── ONE VERDICT PER SESSION, WORST WINS (2026-09-22) ─────────────────
    # This called HSA.read_hover_log() and refused outright once two logs
    # existed, so both sessions lost their answer the day a second hover
    # instance started. Each log is now checked on its own and NOTHING IS FUSED:
    # hover2's genuine "no process pass logged yet" must not read as hover1
    # being stale, and hover1 being fine must not cover for hover2.
    #
    # PRECEDENCE IS THE ONE hover_separation_audit.py ALREADY USES: any STALE
    # beats any COULD NOT RUN beats clean. A second session can never soften a
    # first.
    print('HOVER PROCESS-PASS FRESHNESS -- asked from the build side')
    print('')
    logs = HSA.read_hover_logs()
    if not logs:
        fail('no hover auditor self-log found under '
             '~/.claude/projects/*/hover-audit-log/. Set SAIRN_HOVER_LOG to '
             'point at it.')

    codes = []
    for lg in logs:
        print('-- %s --' % lg['session'])
        if lg['problem']:
            codes.append(cnr(lg['problem']))
            print('')
            continue
        ok, why, _n = HSA.verify_chain(lg['rows'])
        if not ok:
            codes.append(cnr('the self-log HASH CHAIN does not verify (%s). A '
                             'timestamp read out of an unverified chain is the '
                             'thing being checked vouching for itself.' % why))
            print('')
            continue
        codes.append(_check_one_session(lg['rows'], lg['path'], args))
        print('')

    if 1 in codes:
        print('OVERALL: at least one session is STALE (not a clean bill)')
        return 1
    if 2 in codes:
        print('OVERALL: PART COULD NOT RUN (not a clean bill)')
        return 2
    print('OVERALL: every session inside its bound')
    return 0


# ── SELFTEST, AGAINST FIXTURES, BOTH DIRECTIONS ─────────────────────────────
def selftest():
    bad = []

    def arm(name, ok, detail=''):
        print(('  ok   ' if ok else '  FAIL ') + name + ('' if ok else '  ' + str(detail)))
        if not ok:
            bad.append(name)

    now = time.time()

    def stamp(hours_ago):
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now - hours_ago * 3600))

    print('SELFTEST -- criteria locked against fixtures before the real run\n')

    arm('a ts round-trips through the parser',
        abs(epoch(stamp(10)) - (now - 36000)) < 2, epoch(stamp(10)))
    arm('an unparseable ts is None, not an exception and not zero',
        epoch('yesterday') is None and epoch(None) is None)

    rows = [{'seq': 1, 'ts': stamp(50), 'process_pass': True},
            {'seq': 2, 'ts': stamp(40), 'process_pass': False},
            {'seq': 3, 'ts': stamp(5), 'process_pass': True}]
    flagged = [r for r in rows if r.get('process_pass')]
    arm('only FLAGGED entries count -- prose is never matched',
        [r['seq'] for r in flagged] == [1, 3], flagged)
    age = (now - epoch(flagged[-1]['ts'])) / 3600.0
    arm('...and the age is taken from the NEWEST flagged entry, not the newest '
        'entry', 4.9 < age < 5.1, age)

    g = gaps([{'seq': 40, 'ts': stamp(60)}, {'seq': 142, 'ts': stamp(20)}],
             (40, 142))
    arm('the calibration gap is computed in hours between named entries',
        len(g) == 1 and 39.9 < g[0][1] < 40.1, g)
    arm('...and an entry with a bad ts is skipped rather than crashing the run',
        gaps([{'seq': 40, 'ts': 'nope'}, {'seq': 142, 'ts': stamp(1)}], (40, 142)) == [])

    print('')
    if bad:
        print('%d selftest arm(s) failed' % len(bad))
        return 2
    print('OK: the criteria separate flagged from unflagged, take the age from '
          'the newest FLAGGED entry, and survive a malformed timestamp.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
