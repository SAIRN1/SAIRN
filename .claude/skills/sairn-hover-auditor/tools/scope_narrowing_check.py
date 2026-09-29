#!/usr/bin/env python
"""scope_narrowing_check.py -- has what this role actually reviews quietly
narrowed over time, without any explicit decision anywhere logging it.

WAS A NAMED RISK ONLY UNTIL NOW (SKILL.md's independence-of-scope material,
round 3 item d, and the Gender Shades app-coverage-skew finding from an
earlier round -- both real, both previously one-time observations rather
than a standing, running check). Built on direct instruction: this needs to
be a real, running check, not just awareness of the risk.

WHAT IT ACTUALLY MEASURES, stated narrowly. For each of the four real build
agents (hank, cc, fourth, cody), how many real check/finding entries have
been logged since that agent was last the SUBJECT of one -- read from the
structured `target` field, never from prose. An agent whose count is far
past the others is a real, computed signal that this role's own attention
has drifted away from them, for whatever reason, without anyone having
decided that on purpose.

DISCLOSED LIMIT, same as every comparable tool in this directory: this
counts ATTENTION (how often an agent was the subject of a check), not
CORRECTNESS or RISK -- an agent going quiet in this log could mean this
role's coverage genuinely narrowed, or could mean that agent simply had
less real, completed work to check in the period measured. This tool
cannot tell the two apart on its own; it surfaces the number so a human (or
this role, deliberately) can ask which one it is, and a stale agent count
is a candidate for the NEXT undirected or targeted pass, not a confirmed
finding of neglect by itself.

Run:
  python scope_narrowing_check.py --log PATH
  python scope_narrowing_check.py --selftest
"""
import json
import sys

BUILD_AGENTS = ('hank', 'cc', 'fourth', 'cody')
NARROWING_THRESHOLD = 60  # see docstring: reasoned starting number, same honesty
                          # as undirected_sweep_freshness.py's own disclosed cadence


def load_entries(path):
    entries = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def check_scope_narrowing(entries, threshold=NARROWING_THRESHOLD):
    cf = [e for e in entries if e.get('type') in ('check', 'finding')]
    total = len(cf)
    per_agent = {}
    for agent in BUILD_AGENTS:
        last = 0
        for e in cf:
            if e.get('target') == agent:
                last = e['seq']
        since = len([e for e in cf if e['seq'] > last])
        per_agent[agent] = {
            'last_seq': last,
            'ever_reviewed': last > 0,
            'real_entries_since': since,
        }
    narrowed = [a for a in BUILD_AGENTS
                if not per_agent[a]['ever_reviewed']
                or per_agent[a]['real_entries_since'] >= threshold]
    return {
        'threshold': threshold,
        'threshold_basis': 'REASONED starting number, matching '
                            'undirected_sweep_freshness.py\'s own disclosed '
                            'honesty about not yet having real repeat-gap '
                            'history to calibrate from.',
        'total_real_entries': total,
        'per_agent': per_agent,
        'narrowed_agents': narrowed,
        'FAIL_scope_narrowed': len(narrowed) > 0,
    }


def _selftest():
    failures = []

    def check(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    def fake(seq, target, etype='check'):
        return {'seq': seq, 'type': etype, 'target': target}

    even_coverage = []
    seq = 1
    for _ in range(20):
        for a in BUILD_AGENTS:
            even_coverage.append(fake(seq, a)); seq += 1
    r = check_scope_narrowing(even_coverage, threshold=60)
    check('even coverage across all four agents flags nobody',
          r['narrowed_agents'] == [] and not r['FAIL_scope_narrowed'])

    one_never_reviewed = [fake(i, 'hank') for i in range(1, 10)] + \
                          [fake(i, 'cc') for i in range(10, 19)] + \
                          [fake(i, 'fourth') for i in range(19, 28)]
    # 'cody' never appears at all.
    r = check_scope_narrowing(one_never_reviewed, threshold=60)
    check("an agent NEVER reviewed at all is flagged, distinct from one "
          "reviewed once long ago", 'cody' in r['narrowed_agents']
          and r['per_agent']['cody']['ever_reviewed'] is False)

    one_gone_quiet = []
    seq = 1
    for a in BUILD_AGENTS:
        one_gone_quiet.append(fake(seq, a)); seq += 1
    # everyone reviewed once, then 65 more entries all about 'hank' only --
    # cc/fourth/cody each went quiet for 65 real entries.
    for _ in range(65):
        one_gone_quiet.append(fake(seq, 'hank')); seq += 1
    r = check_scope_narrowing(one_gone_quiet, threshold=60)
    check('three agents each quiet for 65 entries (over the 60 threshold) '
          'are all flagged; hank, reviewed continuously, is not',
          set(r['narrowed_agents']) == {'cc', 'fourth', 'cody'})

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
    r = check_scope_narrowing(entries)
    print('SCOPE-NARROWING CHECK -- attention, not correctness or risk')
    print('  threshold: %d real entries since an agent was last reviewed (%s)'
          % (r['threshold'], r['threshold_basis']))
    for a in BUILD_AGENTS:
        p = r['per_agent'][a]
        flag = ' <-- NARROWED' if a in r['narrowed_agents'] else ''
        print('  %-8s last at seq %-5s  %d real entries since%s'
              % (a, p['last_seq'] or 'never', p['real_entries_since'], flag))
    if r['FAIL_scope_narrowed']:
        print('NARROWED: %s -- pick one of these for the next targeted pass, '
              'or confirm the quiet stretch is real (they had less completed '
              'work in the window) rather than a drift nobody decided.'
              % ', '.join(r['narrowed_agents']))
        return 1
    print('OK: no agent has gone quiet past the threshold.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
