#!/usr/bin/env python
"""undirected_sweep_freshness.py -- makes the deliberately-undirected sweep
(SKILL.md, round 3, the Von Arx/wiki-discovery item) a real, running check
rather than a documented principle nobody is mechanically reminded of.

WAS A DESIGN NOTE ONLY UNTIL NOW. Built on direct instruction: this needs to
actually run periodically alongside the risk-weighted targeted rotation, not
exist only as a paragraph in SKILL.md.

WHAT COUNTS AS ONE, MECHANICALLY, NEVER BY PROSE. hover_log.py's --add now
accepts --undirected-sweep, stored as a structured field
(entry['undirected_sweep']), the identical discipline process_pass and
eqa_checkpoint already use and for the identical reason: a future reader
should not have to trust that "undirected" was worded consistently in a
summary, and this role should not have to remember its own wording either.

THE BOUND IS DISCLOSED AS REASONED, NOT CALIBRATED, BECAUSE THERE IS NO
HISTORY TO CALIBRATE FROM YET -- said plainly rather than faked. Unlike
hover_process_pass_freshness.py, which derived its 36h/48h bounds from three
real historical gaps already in the log, this field has zero prior
occurrences before this tool's own first run: there is nothing to measure a
cadence FROM. UNDIRECTED_SWEEP_CADENCE below is a stated, round, defensible
starting number (one genuinely undirected pass roughly every 40 real
check/finding entries -- reasoned from this session's own actual pace
producing on the order of 200+ such entries across one long working
session, not measured from repeat gaps), and this tool's own report says so
on every run so a future reader re-derives the number instead of inheriting
it as though it were measured.

Run:
  python undirected_sweep_freshness.py --log PATH
  python undirected_sweep_freshness.py --selftest
"""
import json
import sys

UNDIRECTED_SWEEP_CADENCE = 40  # see docstring: reasoned, not yet calibrated


def load_entries(path):
    entries = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def check_undirected_sweep_freshness(entries, cadence=UNDIRECTED_SWEEP_CADENCE):
    """Counts real check/finding entries since the last one flagged
    undirected_sweep=True. Mirrors check_eqa_checkpoint_due()'s own shape in
    hover_self_health.py -- STRUCTURAL FIELD ONLY, never prose.
    """
    cf = [e for e in entries if e.get('type') in ('check', 'finding')]
    sweeps = [e for e in cf if e.get('undirected_sweep')]
    last_seq = sweeps[-1]['seq'] if sweeps else 0
    since = [e for e in cf if e['seq'] > last_seq]
    return {
        'cadence': cadence,
        'cadence_basis': 'REASONED starting number, not yet calibrated from '
                          'real repeat gaps -- there is no prior occurrence '
                          'of this field to measure a cadence from yet.',
        'sweeps_ever_performed': len(sweeps),
        'last_sweep_seq': last_seq,
        'real_entries_since_last_sweep': len(since),
        'FAIL_undirected_sweep_due': len(since) >= cadence,
    }


def _selftest():
    failures = []

    def check(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    def fake(seq, etype='check', undirected=False):
        return {'seq': seq, 'type': etype, 'undirected_sweep': undirected}

    zero_ever = [fake(i) for i in range(1, 10)]
    r = check_undirected_sweep_freshness(zero_ever, cadence=40)
    check('zero sweeps ever, under cadence, is NOT yet due',
          r['sweeps_ever_performed'] == 0 and not r['FAIL_undirected_sweep_due'])

    many_since_none = [fake(i) for i in range(1, 45)]
    r = check_undirected_sweep_freshness(many_since_none, cadence=40)
    check('zero sweeps ever, PAST cadence in raw entry count, IS due',
          r['FAIL_undirected_sweep_due'])

    one_recent = [fake(i) for i in range(1, 30)] + [fake(30, undirected=True)] + \
                 [fake(i) for i in range(31, 35)]
    r = check_undirected_sweep_freshness(one_recent, cadence=40)
    check('a recent real sweep resets the count -- not due',
          r['last_sweep_seq'] == 30 and r['real_entries_since_last_sweep'] == 4
          and not r['FAIL_undirected_sweep_due'])

    finding_type_counts_too = [fake(1, etype='finding', undirected=True)] + \
                               [fake(i, etype='finding') for i in range(2, 45)]
    r = check_undirected_sweep_freshness(finding_type_counts_too, cadence=40)
    check('a sweep logged as type finding (not just check) is still recognised',
          r['sweeps_ever_performed'] == 1 and r['last_sweep_seq'] == 1)

    a_note_does_not_count_toward_the_denominator = \
        [fake(1, undirected=True)] + [fake(i, etype='note') for i in range(2, 60)] + \
        [fake(i) for i in range(60, 70)]
    r = check_undirected_sweep_freshness(a_note_does_not_count_toward_the_denominator, cadence=40)
    check('note-type entries do not count toward the since-last-sweep total, '
          'only real check/finding entries do',
          r['real_entries_since_last_sweep'] == 10)

    print()
    if failures:
        print('%d SELFTEST FAILURE(S): %s' % (len(failures), failures))
        return 1
    print('ALL SELFTEST CASES PASS')
    return 0


def main(argv):
    if '--selftest' in argv:
        return _selftest()
    log_path = None
    i = 0
    while i < len(argv):
        if argv[i] == '--log' and i + 1 < len(argv):
            log_path = argv[i + 1]; i += 2
        else:
            i += 1
    if not log_path:
        print('--log PATH is required')
        return 2
    try:
        entries = load_entries(log_path)
    except OSError as e:
        print('COULD NOT RUN: could not read %s: %s' % (log_path, e))
        return 2
    r = check_undirected_sweep_freshness(entries)
    print('UNDIRECTED-SWEEP FRESHNESS')
    print('  cadence: one per %d real check/finding entries (%s)'
          % (r['cadence'], r['cadence_basis']))
    print('  sweeps ever performed: %d' % r['sweeps_ever_performed'])
    print('  last sweep at seq: %s' % (r['last_sweep_seq'] or 'never'))
    print('  real entries since: %d' % r['real_entries_since_last_sweep'])
    if r['FAIL_undirected_sweep_due']:
        print('DUE: run a genuinely undirected pass -- no target, no seed '
              'chosen in advance -- and log it with --undirected-sweep.')
        return 1
    print('OK: not yet due.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
