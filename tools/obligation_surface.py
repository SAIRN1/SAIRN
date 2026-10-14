#!/usr/bin/env python
# OWNER: cc
# written 2026-10-14, batch b11, queue item 2
"""Every review obligation open longer than 48h, printed where a session will see it.

    python tools/obligation_surface.py                 # the surface
    python tools/obligation_surface.py --mine          # only what THIS clone owns
    python tools/obligation_surface.py --json
    python tools/obligation_surface.py --selftest      # the criteria lock

Exit 0 nothing is overdue, 1 something is, 2 COULD NOT RUN -- and the third
one is never folded into either of the others.

── WHY THIS EXISTS, AND IT IS A MEASUREMENT RATHER THAN A WORRY ─────────────
fourth asked for it in b18 item 5 after triaging the queue by hand. Measured
on the day this was written, 2026-10-14, over `docs/tier-a-reviews.json`:
**20 obligations open, and the oldest was 401 HOURS -- sixteen days.** Four of
them were owned by `cloud`, a session whose newest claim is 2026-09-27, so
they were assigned to somebody who was never coming back. Nothing printed any
of that at session start, so each batch began by reading a handoff that did
not mention them and discovering them, or not, by accident.

THE REGISTER ALREADY KNEW. `tier_a_review_gate.py --list` prints the queue,
and nothing runs it. That is the whole gap: an obligation is not forgotten
because the data is missing, it is forgotten because the data is somewhere
nobody looks on the way in.

── WHY 48 HOURS AND NOT A NUMBER OF MY OWN ──────────────────────────────────
It is `OWNER_STALE_HOURS`, imported from `tier_a_review_gate` rather than
re-typed. That is the point at which the gate itself says anybody may
`--takeover`, so an obligation past it is one the platform has ALREADY decided
is late. A second threshold here would be a second opinion about the same
fact, and the two would drift -- this file's own staleness class.

── A3 FAIL-CLOSED ───────────────────────────────────────────────────────────
If the register cannot be read, parsed, or has no `records` list, this exits 2
and says which. **It does NOT print "nothing overdue".** A surface whose empty
state and whose broken state look identical is worse than no surface: it
actively reassures. That is PR 1.11 in the one place a reader glances at
rather than reads.

── A6 THE THIRD STATE ───────────────────────────────────────────────────────
An obligation whose `opened_at` cannot be parsed has an UNKNOWN age. It is
neither fresh nor overdue, it is counted and printed in its own section, and
it makes the exit code non-zero -- because the one record nobody can age is
exactly the one that has been sitting there longest. Folding it into "fresh"
is the silent-failure direction; folding it into "overdue" would be a number
that cannot be defended.

NOT A HOOK. This is a command, printed by whatever runs it. Nothing here
wires itself into a session lifecycle, and the 23 hooks cleared on 2026-10-11
stay cleared.
"""
import datetime
import io
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

REVIEWS = os.path.join(REPO, 'docs', 'tier-a-reviews.json')

# IMPORTED, NEVER RE-TYPED. See the header: a second threshold would be a
# second opinion about the same fact and the two would drift.
try:
    from tier_a_review_gate import OWNER_STALE_HOURS as OVERDUE_HOURS
    _THRESHOLD_SOURCE = 'tier_a_review_gate.OWNER_STALE_HOURS'
except Exception:                                                # noqa: BLE001
    OVERDUE_HOURS = None
    _THRESHOLD_SOURCE = None


def load(path=REVIEWS):
    """-> (records, None) or (None, why). A3: never an empty list on failure."""
    if not os.path.isfile(path):
        return None, ('the Tier A register is not at %s, so NOTHING was '
                      'checked. This is not "no obligations".'
                      % os.path.relpath(path, REPO))
    try:
        doc = json.loads(io.open(path, encoding='utf-8').read())
    except ValueError as e:
        return None, ('the Tier A register is not valid JSON (%s), so NOTHING '
                      'was checked.' % e)
    except OSError as e:
        return None, ('the Tier A register could not be read (%s), so NOTHING '
                      'was checked.' % e.__class__.__name__)
    recs = doc.get('records')
    if not isinstance(recs, list):
        return None, ('the Tier A register has no `records` list, so NOTHING '
                      'was checked -- the format moved and this tool would '
                      'otherwise report a clean queue from a file it did not '
                      'understand.')
    return recs, None


def age_hours(rec, now=None):
    """-> hours open, or None for the THIRD STATE (A6). Never 0 for unknown."""
    stamp = rec.get('opened_at')
    if not isinstance(stamp, str) or not stamp.strip():
        return None
    try:
        when = datetime.datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return (now - when).total_seconds() / 3600.0


def is_open(rec):
    """Open means not discharged. A record with a verdict is done whatever its
    status string says, and a record with neither is open -- the two are
    checked together so a half-written record cannot read as closed."""
    if rec.get('verdict'):
        return False
    return rec.get('status') != 'discharged'


def survey(recs, now=None):
    """-> (overdue, unknown_age, fresh). Sorted oldest-first within each."""
    overdue, unknown, fresh = [], [], []
    for rec in recs:
        if not is_open(rec):
            continue
        h = age_hours(rec, now)
        if h is None:
            unknown.append((rec, None))
        elif OVERDUE_HOURS is not None and h > OVERDUE_HOURS:
            overdue.append((rec, h))
        else:
            fresh.append((rec, h))
    overdue.sort(key=lambda p: -(p[1] or 0))
    fresh.sort(key=lambda p: -(p[1] or 0))
    return overdue, unknown, fresh


def _line(rec, hours):
    age = '   UNKNOWN' if hours is None else '%7.0fh' % hours
    return ('  %s  owner=%-9s author=%-9s %s'
            % (age, rec.get('reviewer_owner') or '(UNOWNED)',
               rec.get('author_session') or '?',
               ','.join(rec.get('resources') or [])[:40]))


def report(recs, mine=None, as_json=False, now=None):
    overdue, unknown, fresh = survey(recs, now)
    if mine:
        overdue = [p for p in overdue if p[0].get('reviewer_owner') == mine]
        unknown = [p for p in unknown if p[0].get('reviewer_owner') == mine]
        fresh = [p for p in fresh if p[0].get('reviewer_owner') == mine]

    if as_json:
        print(json.dumps({
            'threshold_hours': OVERDUE_HOURS,
            'threshold_source': _THRESHOLD_SOURCE,
            'overdue': [{'opened_at': r.get('opened_at'), 'hours': round(h, 1),
                         'owner': r.get('reviewer_owner'),
                         'author': r.get('author_session')}
                        for r, h in overdue],
            'unknown_age': [{'opened_at': r.get('opened_at'),
                             'owner': r.get('reviewer_owner')}
                            for r, _h in unknown],
            'open_total': len(overdue) + len(unknown) + len(fresh),
        }, indent=2, sort_keys=True))
        return EXIT_FINDING if (overdue or unknown) else EXIT_CLEAN

    print('REVIEW OBLIGATIONS OPEN OVER %dh%s'
          % (OVERDUE_HOURS, '  (%s only)' % mine if mine else ''))
    print('  threshold from %s -- the point the gate itself says anybody may '
          '--takeover' % _THRESHOLD_SOURCE)
    print('  open total: %d   overdue: %d   unknown age: %d'
          % (len(overdue) + len(unknown) + len(fresh), len(overdue),
             len(unknown)))
    if overdue:
        print('')
        print('  OVERDUE, oldest first:')
        for r, h in overdue:
            print(_line(r, h))
    if unknown:
        print('')
        print('  UNKNOWN AGE -- A THIRD STATE, not fresh and not overdue. The '
              'one record')
        print('  nobody can age is the one most likely to have been sitting '
              'longest:')
        for r, _h in unknown:
            print(_line(r, None))
    if not overdue and not unknown:
        print('')
        print('  Nothing open past the threshold. %d fresh obligation(s) '
              'remain.' % len(fresh))
        return EXIT_CLEAN
    print('')
    print('  Discharge one:  python tools/tier_a_review_gate.py --list')
    print('  An obligation nobody is reminded of is the one that reaches 401h, '
          'which is')
    print('  what the oldest of these was when this tool was written.')
    return EXIT_FINDING


# ── THE CRITERIA LOCK ───────────────────────────────────────────────────────
def run_selftest():
    print('OBLIGATION SURFACE -- criteria lock')
    bad = total = 0

    def ck(label, got, want=True):
        nonlocal bad, total
        total += 1
        if got != want:
            bad += 1
            print('  FAIL ' + label)
            print('       wanted %r, got %r' % (want, got))
        else:
            print('  ok   ' + label)

    now = datetime.datetime(2026, 10, 14, 12, 0, 0,
                            tzinfo=datetime.timezone.utc)

    def rec(hours_ago, owner='hank', status='open', verdict=None, stamp=None):
        r = {'reviewer_owner': owner, 'author_session': 'cody',
             'status': status, 'resources': ['x']}
        if stamp is not None:
            r['opened_at'] = stamp
        elif hours_ago is not None:
            r['opened_at'] = (now - datetime.timedelta(hours=hours_ago)
                              ).strftime('%Y-%m-%dT%H:%M:%SZ')
        if verdict:
            r['verdict'] = verdict
        return r

    ck('the threshold is IMPORTED from the gate, not re-typed here -- a second '
       'number about the same fact would drift from it',
       (OVERDUE_HOURS, _THRESHOLD_SOURCE),
       (48, 'tier_a_review_gate.OWNER_STALE_HOURS'))

    o, u, f = survey([rec(401), rec(47), rec(49)], now)
    ck('an obligation past the threshold is OVERDUE', len(o), 2)
    ck('...and one inside it is FRESH, so the arm above is about the threshold '
       'and not about counting everything', len(f), 1)
    ck('OVERDUE is sorted oldest-first -- the 401h one is what a reader must '
       'see at the top', round(o[0][1]), 401)
    ck('exactly AT the threshold is NOT overdue -- the boundary is >, matching '
       'the gate\'s own `age <= OWNER_STALE_HOURS` refusal',
       len(survey([rec(48)], now)[0]), 0)

    ck('a DISCHARGED record is not open', len(survey([rec(401, status='discharged')], now)[0]), 0)
    ck('a record carrying a VERDICT is not open either, whatever its status '
       'says -- a half-written record must not read as closed',
       len(survey([rec(401, verdict='sound')], now)[0]), 0)

    # ── A6 THE THIRD STATE ──────────────────────────────────────────────────
    o, u, f = survey([rec(None, stamp='not-a-date'), rec(None, stamp=''),
                      rec(None)], now)
    ck('A6: an unparseable opened_at is UNKNOWN AGE, not fresh', len(u), 3)
    ck('A6: ...and an unknown age is NOT silently counted as fresh, which is '
       'the direction that would hide the oldest record', len(f), 0)
    ck('A6: ...and never as overdue either, which would be a number that '
       'cannot be defended', len(o), 0)
    ck('A6: an unknown age alone makes the run NON-ZERO -- the record nobody '
       'can age is the one most likely to be oldest',
       report([rec(None, stamp='nope')], as_json=True, now=now), EXIT_FINDING)
    ck('A6 CONTROL: a surveyable fresh-only queue really does exit 0, so the '
       'arm above is about the unknown age and not about always failing',
       report([rec(2)], as_json=True, now=now), EXIT_CLEAN)

    # ── A3 FAIL-CLOSED ──────────────────────────────────────────────────────
    import tempfile
    d = tempfile.mkdtemp(prefix='oblig-surface-')
    try:
        missing = os.path.join(d, 'nope.json')
        recs, why = load(missing)
        ck('A3: an ABSENT register is a reason, never an empty list',
           (recs, bool(why)), (None, True))
        ck('A3: ...and the reason says NOTHING was checked rather than '
           'implying a clean queue', 'NOTHING was checked' in why)
        p = os.path.join(d, 'bad.json')
        io.open(p, 'w', encoding='utf-8').write('{not json')
        recs, why = load(p)
        ck('A3: an UNPARSEABLE register is a reason, not an empty list',
           (recs, 'valid JSON' in (why or '')), (None, True))
        p2 = os.path.join(d, 'noshape.json')
        io.open(p2, 'w', encoding='utf-8').write('{"somethingelse": []}')
        recs, why = load(p2)
        ck('A3: a register with NO `records` list is a reason -- the format '
           'moving must not read as a clean queue',
           (recs, 'no `records` list' in (why or '')), (None, True))
        p3 = os.path.join(d, 'good.json')
        io.open(p3, 'w', encoding='utf-8').write('{"records": []}')
        recs, why = load(p3)
        ck('A3 CONTROL: a readable register with an EMPTY records list loads '
           'fine and is genuinely empty -- so the arms above are about '
           'failure and not about rejecting everything', (recs, why), ([], None))
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    # ── THE ABLATION ────────────────────────────────────────────────────────
    # The pre-tool state is "nothing runs at session start", which cannot be
    # ablated directly. What CAN be: the two decisions this file makes that a
    # careless version would get wrong in the reassuring direction.
    def fold_unknown_into_fresh(records):
        """The pre-A6 shape: an unreadable date counted as age 0, i.e. fresh."""
        return [r for r in records if (age_hours(r, now) or 0) > OVERDUE_HOURS]
    planted = [rec(None, stamp='not-a-date'), rec(500)]
    ck('ABLATION: folding UNKNOWN into fresh (age-or-zero) hides the '
       'unreadable record entirely -- it reports 1 where the real answer is '
       '1 overdue PLUS 1 unaccounted', len(fold_unknown_into_fresh(planted)), 1)
    o2, u2, _f2 = survey(planted, now)
    ck('ABLATION: ...while this tool reports both, and the unknown one by name',
       (len(o2), len(u2)), (1, 1))

    def empty_on_failure(path):
        """The pre-A3 shape: return [] when the file will not load."""
        try:
            return json.loads(io.open(path, encoding='utf-8').read())['records']
        except Exception:                                        # noqa: BLE001
            return []
    ck('ABLATION: returning [] on a failed load makes a BROKEN register '
       'indistinguishable from an empty one -- the surface would print '
       '"nothing overdue" over a file it could not read',
       empty_on_failure(os.path.join(REPO, 'does-not-exist.json')), [])

    print('  %d/%d arm(s) pass' % (total - bad, total))
    if bad:
        print('  THE CRITERIA ARE BROKEN. This surface cannot be trusted to '
              'say the queue is clear.')
        return EXIT_FINDING
    return EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--selftest' in argv:
        return run_selftest()
    if OVERDUE_HOURS is None:
        sys.stderr.write(
            'COULD NOT RUN: tier_a_review_gate.OWNER_STALE_HOURS could not be '
            'imported, so there is no threshold to measure against. This tool '
            'does not substitute a number of its own -- a second opinion about '
            'the same fact is how the two drift.\n')
        return EXIT_COULD_NOT_RUN
    recs, why = load()
    if recs is None:
        sys.stderr.write('COULD NOT RUN: %s\n' % why)
        return EXIT_COULD_NOT_RUN
    mine = None
    if '--mine' in argv:
        try:
            import sairn_session_identity as sid
            mine = sid.session_name()
        except Exception as e:                                   # noqa: BLE001
            sys.stderr.write('COULD NOT RUN: --mine needs this clone\'s '
                             'session identity and it could not be read '
                             '(%s).\n' % e.__class__.__name__)
            return EXIT_COULD_NOT_RUN
    return report(recs, mine=mine, as_json='--json' in argv)


if __name__ == '__main__':
    sys.exit(main())
