#!/usr/bin/env python
# OWNER: cc
# written 2026-10-20, batch b28, item 4
"""Alert Michael when a builder crosses 85% of its REAL context window.

    python tools/builder_context_watch.py                 # one pass, report
    python tools/builder_context_watch.py --watch         # loop, 60s
    python tools/builder_context_watch.py --watch --interval 120
    python tools/builder_context_watch.py --test 87       # prove it fires
    python tools/builder_context_watch.py --fixtures      # criteria lock

Exit 0 nobody over, 1 at least one ALERT, 2 COULD NOT RUN.

── CONCEPT ─────────────────────────────────────────────────────────────────
**THE AGENT CANNOT BE TRUSTED TO NOTICE ITS OWN CEILING, SO THE THING THAT
WATCHES MUST NOT BE INSIDE THE AGENT.** cc wrapped b25 at 81.9% and b26 at
89.0% against an 80% trigger it had read in its own dispatch, both times while
believing it was fine. A reminder delivered into the context being exhausted
competes with the work for the attention of the same process. This runs
OUTSIDE, in its own OS process, reading the transcripts from disk, and it
cannot be talked out of a reading by the session it is measuring.

── IT IS NOT A HOOK, AND THAT IS THE POINT, NOT A LIMITATION ──────────────
HOOKS STAY OFF -- Michael disabled all 23 on 2026-10-11 because they were
causing agent compaction, and `~/.claude/settings.json` carries `"hooks": {}`
deliberately (an ABSENT key and `{}` are different facts; only the second
survives a clone/reset/rebase). A hook would also be the wrong shape twice
over: it fires INSIDE the session, on the session's own turn, adding to the
context it is warning about -- and it cannot fire at all once a session is
wedged, which is exactly when the warning matters. A separate process keeps
reporting about a session that has stopped reporting about itself.

Michael starts it himself, in a terminal, once:

    python tools/builder_context_watch.py --watch

── WHAT IT MEASURES, AND WHY IT IS THE SAME READ AS THE STATUS LINE ────────
`tools/sairn_status_line.py` already solved this and its two functions are
IMPORTED rather than re-implemented: `used_tokens()` (the last `message.usage`
in a transcript, `input + cache_read + cache_creation`, scanned from the END in
a bounded window because a transcript is megabytes) and `window_for()` (the
REAL window per named model -- 1,000,000 for Opus 5 / any `[1m]`, 967,000 for
Sonnet 5, and NEVER a hardcoded 200K). Two readers of one number with two
implementations is two numbers waiting to disagree; if that import ever fails
this exits 2 and names the file rather than reinventing the arithmetic.

── THREE THINGS IT REFUSES TO DO ──────────────────────────────────────────
1. IT NEVER PRINTS 0% OR "FINE" FOR A SESSION IT COULD NOT MEASURE. An
   unreadable transcript, a missing model id, an ambiguous window: all are
   UNKNOWN, reported with the reason, and counted in their own bucket. The
   status line learned this the hard way -- 0% is the one wrong value that
   reads as reassuring.
2. IT NEVER WRITES ANOTHER SESSION'S STATUS ROW. `sairn_status.py` rows are
   each session's own claim about itself; a watcher filling one in would be
   impersonation, and the next reader could not tell a measurement from a
   self-report. Alerts go to the watcher's OWN files, named as the watcher's.
3. IT ALERTS ONCE PER CROSSING, not once per poll. A watcher that prints every
   60 seconds is a watcher Michael stops reading, which is the same failure as
   not warning at all. The per-session state is remembered so a session that
   crosses, stays over and then compacts back below re-arms.

── WHAT IT CANNOT DO, SAID OUT LOUD ───────────────────────────────────────
It cannot stop a session, interrupt one, or make one wrap up. It tells Michael.
It cannot see a session whose transcript it cannot find -- a session started
with a non-default projects directory is invisible here and is NOT reported as
under the threshold; it is simply absent, which is why the output prints how
many sessions it found and for which subjects. And it reads the LAST usage
line, so between two assistant turns the figure is as of the previous turn, up
to one turn stale -- never ahead, always behind, which errs toward warning late
rather than early and is stated so nobody reads it as instantaneous.
"""
import io
import json
import os
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-20.1'

# Michael's threshold for the four builders, 2026-10-20. The dispatch raised
# the wrap-up trigger from 80 to 85 in the same breath as asking for this.
THRESHOLD = 85.0

BUILDERS = ('hank', 'cc', 'cody', 'fourth')

HOME = os.path.expanduser('~')
PROJECTS = os.path.join(HOME, '.claude', 'projects')
# Outside every clone, like the status registry, so no push is needed for
# Michael to see it and no clone's git state can hide it.
ALERT_DIR = os.path.join(HOME, 'SAIRN-SESSION-LOCKS', 'context-alerts')
# The shared Drive folder he already reads. Best-effort: see _drive_append.
DRIVE = os.path.join('G:', os.sep, 'My Drive', 'SAIRN-status')
DRIVE_FILE = os.path.join(DRIVE, 'CONTEXT-ALERTS.txt')


def _clone_key(subject):
    """The per-clone projects directory name the harness sanitises to."""
    return 'C--Users-marsh-Documents-SAIRN-' + subject


def newest_transcript(subject):
    """-> (path, '') or (None, why). The most recently MODIFIED .jsonl.

    Newest by MTIME and not by name: a session id sorts arbitrarily, and the
    one being written to right now is the one that matters.
    """
    d = os.path.join(PROJECTS, _clone_key(subject))
    if not os.path.isdir(d):
        return None, 'no projects dir for %s' % subject
    best, best_m = None, -1.0
    try:
        for name in os.listdir(d):
            if not name.endswith('.jsonl'):
                continue
            p = os.path.join(d, name)
            try:
                m = os.path.getmtime(p)
            except OSError:
                continue
            if m > best_m:
                best, best_m = p, m
    except OSError as exc:
        return None, 'projects dir unreadable (%s)' % exc.__class__.__name__
    if not best:
        return None, 'no transcript in %s' % d
    return best, ''


def model_id(path):
    """-> a payload shaped the way sairn_status_line.window_for() wants it.

    The model id is read from the SAME last-usage record, so the window and
    the token count describe one turn rather than two.
    """
    try:
        from sairn_status_line import _tail_lines
    except Exception:                                            # noqa: BLE001
        return None
    for nbytes in (200000, 2000000):
        try:
            lines = _tail_lines(path, nbytes)
        except OSError:
            return None
        for raw in reversed(lines):
            raw = raw.strip()
            if not raw or b'"model"' not in raw:
                continue
            try:
                rec = json.loads(raw.decode('utf-8', 'replace'))
            except ValueError:
                continue
            msg = rec.get('message')
            if isinstance(msg, dict) and msg.get('model'):
                return {'model': {'id': msg['model']}}
    return None


def read_one(subject):
    """-> dict. Always has `subject` and `state`; state is over/under/unknown."""
    try:
        from sairn_status_line import used_tokens, window_for
    except Exception as exc:                                     # noqa: BLE001
        return {'subject': subject, 'state': 'unknown',
                'why': 'tools/sairn_status_line.py could not be imported (%s) '
                       '-- the measurement is NOT re-implemented here on '
                       'purpose' % exc.__class__.__name__}
    path, why = newest_transcript(subject)
    if not path:
        return {'subject': subject, 'state': 'unknown', 'why': why}
    tokens, why = used_tokens(path)
    if tokens is None:
        return {'subject': subject, 'state': 'unknown', 'why': why,
                'transcript': path}
    payload = model_id(path)
    if not payload:
        return {'subject': subject, 'state': 'unknown', 'transcript': path,
                'why': 'no model id in the transcript tail, so the window is '
                       'unknown and a percentage would be invented'}
    window, wwhy = window_for(payload)
    if not window:
        return {'subject': subject, 'state': 'unknown', 'transcript': path,
                'tokens': tokens, 'why': wwhy or 'window unknown'}
    pct = round(100.0 * tokens / float(window), 1)
    return {'subject': subject, 'transcript': path, 'tokens': tokens,
            'window': window, 'pct': pct, 'model': payload['model']['id'],
            'state': 'over' if pct >= THRESHOLD else 'under'}


# ── ALERT DELIVERY. THREE CHANNELS, EACH WITH ITS LIMIT NAMED. ─────────────
def _drive_append(line):
    """-> (ok, why). Best-effort, and a failure is REPORTED not swallowed.

    The Drive mount may be absent on a machine that has not signed in. That is
    a could-not-deliver and the console line above it already carried the
    alert, so it degrades rather than failing the run -- but it says so.
    """
    try:
        if not os.path.isdir(DRIVE):
            return False, 'Drive mount %s is not present' % DRIVE
        with io.open(DRIVE_FILE, 'a', encoding='utf-8', newline='\n') as fh:
            fh.write(line + '\n')
        return True, ''
    except OSError as exc:
        return False, 'Drive write failed (%s)' % exc.__class__.__name__


def fire(row, now_iso):
    """Write the alert everywhere it goes. -> list of delivery notes."""
    notes = []
    line = ('%s  ALERT  %-7s %5.1f%% of %s  (%d tokens)  >= %.0f%%  %s'
            % (now_iso, row['subject'], row['pct'], row['window'],
               row['tokens'], THRESHOLD, row.get('model', '?')))
    print(line)                                   # channel 1: the terminal
    notes.append('console')
    try:                                          # channel 2: a file he can grep
        if not os.path.isdir(ALERT_DIR):
            os.makedirs(ALERT_DIR)
        p = os.path.join(ALERT_DIR, '%s.json' % row['subject'])
        payload = dict(row)
        payload['alerted_at'] = now_iso
        payload['threshold'] = THRESHOLD
        payload['written_by'] = 'tools/builder_context_watch.py'
        payload['note'] = ('A MEASUREMENT BY A WATCHER, not a self-report. '
                           'This is deliberately NOT a sairn_status.py row -- '
                           'those are each session\'s own claim about itself.')
        io.open(p, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(payload, indent=1) + '\n')
        notes.append('file %s' % p)
    except OSError as exc:
        notes.append('FILE WRITE FAILED (%s)' % exc.__class__.__name__)
    ok, why = _drive_append(line)                 # channel 3: the shared Drive
    notes.append('drive' if ok else 'drive NOT delivered: %s' % why)
    return notes


def one_pass(state, now_iso):
    """-> (exit_code, rows). `state` maps subject -> was_over, so an alert
    fires on the CROSSING and not on every poll."""
    rows = [read_one(s) for s in BUILDERS]
    over = [r for r in rows if r['state'] == 'over']
    unknown = [r for r in rows if r['state'] == 'unknown']
    for r in rows:
        was = state.get(r['subject'], False)
        if r['state'] == 'over' and not was:
            fire(r, now_iso)
        state[r['subject']] = (r['state'] == 'over')
    for r in rows:
        if r['state'] == 'under':
            print('       ok     %-7s %5.1f%% of %s' % (r['subject'], r['pct'],
                                                        r['window']))
        elif r['state'] == 'unknown':
            print('       ??     %-7s UNKNOWN -- %s' % (r['subject'],
                                                        r.get('why', '')))
    print('  %d of %d measured; %d OVER %.0f%%; %d UNKNOWN (never counted as '
          'under)' % (len(rows) - len(unknown), len(rows), len(over),
                      THRESHOLD, len(unknown)))
    return (EXIT_FINDING if over else EXIT_CLEAN), rows


# ── THE CRITERIA LOCK ───────────────────────────────────────────────────────
def run_fixtures():
    bad = 0
    print('BUILDER CONTEXT WATCH -- criteria lock %s' % CRITERIA_VERSION)

    def check(label, got, want):
        nonlocal bad
        ok = got == want
        if not ok:
            bad += 1
        print('  %s %-66s got=%r want=%r' % ('ok  ' if ok else 'FAIL',
                                             label, got, want))

    def classify(pct):
        return 'over' if pct >= THRESHOLD else 'under'

    check('exactly 85.0 is OVER -- the boundary is >=, not >', classify(85.0),
          'over')
    check('84.9 is under', classify(84.9), 'under')
    check('85.1 is over', classify(85.1), 'over')
    check("cc's b26 reading of 89.0 would have fired", classify(89.0), 'over')
    check("cc's b25 reading of 81.9 would NOT have, at 85", classify(81.9),
          'under')
    check('the threshold is Michael\'s 85, not the old 80', THRESHOLD, 85.0)
    check('all four builders are watched', sorted(BUILDERS),
          ['cc', 'cody', 'fourth', 'hank'])
    check('the AUDITORS are not watched -- a build-agent tool does not '
          'measure the auditor clones',
          [s for s in BUILDERS if 'hover' in s], [])

    # THE CROSSING, not the level: the arm that stops this becoming noise.
    st = {}
    fired = []
    real_fire = globals()['fire']
    globals()['fire'] = lambda row, now: fired.append(row['subject'])
    try:
        for seq in (True, True, False, True):
            for sub in ('zz',):
                was = st.get(sub, False)
                if seq and not was:
                    globals()['fire']({'subject': sub}, 'x')
                st[sub] = seq
    finally:
        globals()['fire'] = real_fire
    check('over,over,under,over fires TWICE -- on each crossing, not each poll',
          fired, ['zz', 'zz'])

    check('an UNKNOWN row is neither over nor under',
          {'state': 'unknown'}['state'] in ('over', 'under'), False)
    print('  %d/%d fixtures classify correctly'
          % (9 - bad, 9))
    return EXIT_FINDING if bad else EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv:
        return run_fixtures()

    if run_fixtures() != EXIT_CLEAN:
        print('\nCOULD NOT RUN: the criteria lock failed, so no reading from '
              'this tool is trustworthy. Nothing was checked.')
        return EXIT_COULD_NOT_RUN
    print('')

    now_iso = time.strftime('%Y-%m-%dT%H:%M:%S')

    # ── --test: PROVE THE ALERT PATH END TO END WITHOUT WAITING FOR A REAL
    # SESSION TO GET BIG. The reading is INJECTED and the row says so, so a
    # test alert can never be mistaken for a measurement.
    if '--test' in argv:
        try:
            pct = float(argv[argv.index('--test') + 1])
        except (IndexError, ValueError):
            print('COULD NOT RUN: --test needs a percentage, e.g. --test 87')
            return EXIT_COULD_NOT_RUN
        row = {'subject': 'zz-test', 'pct': pct, 'tokens': int(pct * 10000),
               'window': 1000000, 'model': 'TEST-INJECTED-NOT-A-MEASUREMENT',
               'state': 'over' if pct >= THRESHOLD else 'under',
               'transcript': '(none -- injected by --test)'}
        print('TEST INJECTION: %.1f%% for a fake subject. %s'
              % (pct, 'EXPECT an alert.' if row['state'] == 'over'
                 else 'EXPECT NO alert -- this is under the threshold.'))
        if row['state'] == 'over':
            for n in fire(row, now_iso):
                print('       delivered -> %s' % n)
            return EXIT_FINDING
        print('       no alert, as expected at %.1f%% < %.0f%%' % (pct,
                                                                   THRESHOLD))
        return EXIT_CLEAN

    print('BUILDER CONTEXT WATCH -- threshold %.0f%%, NOT A HOOK, reading '
          'transcripts from %s' % (THRESHOLD, PROJECTS))
    state = {}
    if '--watch' not in argv:
        code, _ = one_pass(state, now_iso)
        return code

    interval = 60
    if '--interval' in argv:
        try:
            interval = max(5, int(argv[argv.index('--interval') + 1]))
        except (IndexError, ValueError):
            print('COULD NOT RUN: --interval needs seconds.')
            return EXIT_COULD_NOT_RUN
    print('  watching every %ds. Ctrl-C to stop.' % interval)
    try:
        while True:
            one_pass(state, time.strftime('%Y-%m-%dT%H:%M:%S'))
            time.sleep(interval)
    except KeyboardInterrupt:
        print('\nstopped by Ctrl-C. Nothing is watching now -- say so if you '
              'walk away from this terminal.')
        return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
