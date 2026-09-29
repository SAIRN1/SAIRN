#!/usr/bin/env python
"""undirected_sweep_freshness.py (hover2's own build) -- is the deliberately
UNDIRECTED sweep actually happening, or only a principle in SKILL.md?
Implemented from hover_parity_specs.md #3 (H1, 2026-09-24), not H1's source.

An undirected sweep = a pass with no target and no seed chosen in advance
(SKILL.md, the Nightingale/wiki precedent). It only counts when the entry
carries the STRUCTURED `undirected_sweep: true` field hover_log.py's
--undirected-sweep flag stores -- never inferred from summary wording (a
keyword match is the exact self-referential-check shape this platform keeps
finding).

VERDICTS, three, never two:
  PASS (0)          fewer than CADENCE real check/finding entries since the
                    last undirected_sweep entry; the count is printed (the
                    margin, discipline 4).
  FINDING (1)       >= CADENCE real entries since the last sweep, or since
                    genesis if none has EVER been logged -- which is this
                    instance's own honest starting state and must not read
                    as an error.
  COULD-NOT-RUN (2) log unreadable / no parseable entries; also if the log
                    tool cannot store the field at all (checked against
                    hover_log.py's own source), because a freshness check
                    over a field that cannot exist is a check that
                    structurally cannot fire.

CADENCE = 40 real entries -- REASONED, not measured: hover2 has ZERO prior
undirected sweeps to calibrate a repeat-gap from, and the output says so on
every run until a real history exists (discipline 8: cadence from a
MEASURED drift rate; until measurable, the number's provenance is
disclosed, not laundered into fact).

Run:
  python undirected_sweep_freshness.py
  python undirected_sweep_freshness.py --selftest
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'hover-audit-log.jsonl')
LOG_TOOL = os.path.join(HERE, 'hover_log.py')
CADENCE = 40  # REASONED, uncalibrated -- disclosed in every output line
REAL_TYPES = ('check', 'finding')


def read_entries(path):
    try:
        out = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out, None
    except (OSError, ValueError) as e:
        return None, str(e)


def freshness(entries, cadence=CADENCE):
    """Pure core. -> dict(real_since, last_sweep_seq, due)."""
    real_since = 0
    last_sweep_seq = None
    for e in reversed(entries):
        if e.get('undirected_sweep') is True:
            last_sweep_seq = e.get('seq')
            break
        if e.get('type') in REAL_TYPES:
            real_since += 1
    return {'real_since': real_since, 'last_sweep_seq': last_sweep_seq,
            'due': real_since >= cadence}


def log_tool_supports_field(path=LOG_TOOL):
    try:
        with io.open(path, encoding='utf-8', errors='replace') as f:
            return 'undirected_sweep' in f.read()
    except OSError:
        return False


def _selftest():
    fails = []

    def chk(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            fails.append(label)

    mk = lambda seq, typ, sweep=False: dict(
        {'seq': seq, 'type': typ},
        **({'undirected_sweep': True} if sweep else {}))

    # negative control: cadence+1 real entries, no sweep field anywhere
    es = [mk(i, 'check') for i in range(1, CADENCE + 2)]
    r = freshness(es)
    chk('cadence+1 real entries, never swept -> FINDING',
        r['due'] and r['last_sweep_seq'] is None)

    # a recent sweep -> PASS
    es = [mk(i, 'check') for i in range(1, 50)] + [mk(50, 'note', sweep=True)] \
        + [mk(51, 'check')]
    r = freshness(es)
    chk('recent sweep -> PASS, count restarts after it',
        not r['due'] and r['real_since'] == 1 and r['last_sweep_seq'] == 50)

    # non-real entries do not advance the counter
    es = [mk(1, 'note', sweep=True)] + [mk(i, 'note') for i in range(2, 60)]
    r = freshness(es)
    chk('notes do not count toward the denominator',
        not r['due'] and r['real_since'] == 0)

    # boundary: exactly cadence -> FINDING (>=)
    es = [mk(1, 'note', sweep=True)] + \
        [mk(i, 'finding') for i in range(2, 2 + CADENCE)]
    r = freshness(es)
    chk('exactly cadence real entries -> FINDING (>= bound)', r['due'])

    print()
    if fails:
        print('%d SELFTEST FAILURE(S): %s' % (len(fails), fails))
        return 1
    print('ALL SELFTEST CASES PASS')
    return 0


def main(argv):
    if '--selftest' in argv:
        return _selftest()
    if not log_tool_supports_field():
        print('COULD NOT RUN: hover_log.py beside this tool does not carry '
              'the undirected_sweep field at all -- a freshness check over a '
              'field the log cannot record is a check that structurally '
              'cannot fire. Fix the log tool first. (exit 2)')
        return 2
    entries, err = read_entries(LOG)
    if entries is None or not entries:
        print('COULD NOT RUN: log unreadable or empty (%s). (exit 2)' % err)
        return 2
    r = freshness(entries)
    provenance = ('cadence %d is REASONED, not measured -- zero completed '
                  'sweep-to-sweep gaps exist yet to calibrate from'
                  % CADENCE)
    if r['due']:
        anchor = ('since the last undirected sweep at seq %s'
                  % r['last_sweep_seq']) if r['last_sweep_seq'] is not None \
            else ('and NO undirected sweep has EVER been logged by this '
                  'instance -- the honest starting state, not an error')
        print('FINDING: %d real check/finding entries %s (bound %d; %s). '
              'The next pass should be a genuinely undirected one -- no '
              'target, no seed, logged with --undirected-sweep. (exit 1)'
              % (r['real_since'], anchor, CADENCE, provenance))
        return 1
    print('PASS: %d real entries since the undirected sweep at seq %s '
          '(bound %d; %s).'
          % (r['real_since'], r['last_sweep_seq'], CADENCE, provenance))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
