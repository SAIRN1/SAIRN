# docs/b26-logs/known_red_tail_census.py
# OWNER: cody   batch b26   2026-10-19
#
# THE CONCEPT: a known-red entry only makes a failure ATTRIBUTABLE if the tail
#   it records is a line the runner can really produce, so every registered
#   suite is driven ALONE, its own `out[-1]` is captured the way
#   tools/run_all_tests.py captures it, and the stored tail is compared with
#   tools/known_red_check.py's OWN `_same_reason` -- not a comparison invented
#   here, because a census using a different rule from the tool would measure
#   a different thing and agree with nothing.
#
#   python docs/b26-logs/known_red_tail_census.py --list     # names only, no run
#   python docs/b26-logs/known_red_tail_census.py --run      # drive them
#   python docs/b26-logs/known_red_tail_census.py --run --only tests/x.py,...
#
# Exit: 0 census complete - 1 the census itself could not be trusted - 2 COULD
#       NOT RUN
#
# ── THIS IS THE EXPENSIVE HALF OF b22 ITEM 4, ROUTED AT SAIRN-handoff-cody-
#    b22.md 6.6 AND UNMEASURED THROUGH b23, b24 AND b25 ─────────────────────
# b22 found ONE row whose `tail` had been an ARM LIST since b19 while the
# suite's last printed line was its closing expected-red paragraph -- so the
# two NEVER matched and the row reported CHANGED, which reads as "a second
# defect is hiding inside an entry that says this file is expected to fail"
# when the ENTRY is the thing that is wrong. b22's own words: "A ROW REGISTERED
# WITH A TAIL THE RUNNER CANNOT PRODUCE IS WORSE THAN AN ABSENT ROW. Absent
# reads NEW and gets looked at."
#
# What it did NOT do is ask how many of the other rows are like that, because
# "it is not cheap. Establishing it needs each registered suite driven ALONE
# and its out[-1] compared to its row -- a long run, and several of those
# suites WRITE WHEN RUN."
#
# ── SO IT REFUSES TO RUN IN A CLONE WITH A GIT DIRECTORY ───────────────────
# SEVERAL OF THESE SUITES WRITE WHEN RUN. b25's own ablation found a probe had
# dirtied docs/report-only-reachability.json mid-run and made a 99-failure
# list possibly CASCADED. This script therefore refuses unless it is told, by
# an explicit flag, that it is somewhere disposable -- it does not try to
# detect "am I in a worktree", because that is a guess and the cost of being
# wrong is a mutated live clone.
#
# ── AND IT IS SEGMENTED (convention 10: no long run whose first check is at
#    the end) ───────────────────────────────────────────────────────────────
# A verdict is printed per suite as it completes and the running census is
# re-printed every 10, so a run killed at minute 20 still yields the rows it
# got through rather than nothing.

import io
import json
import os
import re
import subprocess
import sys
import tempfile

REG = 'docs/known-red-suites.json'
CHK = 'tools/known_red_check.py'

if not os.path.isfile(REG) or not os.path.isfile(CHK):
    print('COULD NOT RUN: need both ' + REG + ' and ' + CHK
          + '. Nothing was measured.')
    sys.exit(2)

# ── THE COMPARISON IS IMPORTED, NOT RE-IMPLEMENTED ─────────────────────────
# A census that normalises differently from the tool whose verdicts it is
# auditing measures a different thing and can neither confirm nor contradict
# it. This is the "structurally different method for independence" convention
# read the other way: for AGREEMENT with a tool, use the tool's own rule.
sys.path.insert(0, os.path.dirname(os.path.abspath(CHK)))
try:
    import known_red_check as KRC
except Exception as e:                                  # pragma: no cover
    print('COULD NOT RUN: ' + CHK + ' would not import (' + str(e)
          + '), so the census cannot use its comparison and would have to '
            'invent one. Nothing was measured.')
    sys.exit(2)
if not hasattr(KRC, '_same_reason'):
    print('COULD NOT RUN: ' + CHK + ' no longer exposes _same_reason, so the '
          'census would be comparing by a rule of its own. Nothing measured.')
    sys.exit(2)

reg = json.load(io.open(REG, encoding='utf-8'))
entries = reg.get('entries') or []
if not entries:
    print('COULD NOT RUN: ' + REG + ' has no `entries`. Nothing measured.')
    sys.exit(2)

only = None
if '--only' in sys.argv:
    only = set(sys.argv[sys.argv.index('--only') + 1].split(','))

rows = [e for e in entries if only is None or e.get('file') in only]

print('KNOWN-RED TAIL CENSUS -- b26')
print('  registry           ' + REG)
print('  registered entries ' + str(len(entries)))
print('  in this run        ' + str(len(rows)))
print('  comparison         tools/known_red_check.py::_same_reason, IMPORTED')
print('  tail definition    (stdout or stderr).strip().splitlines()[-1], the '
      'way tools/run_all_tests.py:942 builds it')
print('')

missing = [e['file'] for e in rows if not os.path.isfile(e['file'])]
blank = [e['file'] for e in rows if not (e.get('tail') or '').strip()]
print('  REGISTERED FILE NOT ON DISK: ' + str(len(missing))
      + ('  ' + ', '.join(missing) if missing else ''))
print('  REGISTERED WITH AN EMPTY `tail`: ' + str(len(blank))
      + ('  ' + ', '.join(blank) if blank else ''))
print('    -- an empty tail is a THIRD STATE. It cannot match and it cannot '
      'mismatch; it is NOT counted as either.')
print('')

if '--list' in sys.argv or '--run' not in sys.argv:
    print('  kind  file                                               '
          'stored tail')
    for e in rows:
        kind = 'py' if e['file'].endswith('.py') else 'node'
        print('  %-5s %-50s %s'
              % (kind, e['file'], (e.get('tail') or '(EMPTY)')[:70]))
    print('\n--list: NOTHING WAS DRIVEN. Pass --run --disposable-clone to '
          'drive them.')
    sys.exit(0)

# ── THE REFUSAL. Explicit, not inferred. ───────────────────────────────────
if '--disposable-clone' not in sys.argv:
    print('REFUSED: several registered suites WRITE WHEN RUN. Driving them '
          'needs a disposable checkout, and this script will not guess '
          'whether it is in one.')
    print('  git worktree add <tmp> HEAD   &&   cd <tmp>   &&   python '
          'docs/b26-logs/known_red_tail_census.py --run --disposable-clone')
    print('Nothing was driven.')
    sys.exit(2)

env = dict(os.environ)
env['SAIRN_BYPASS_LOG'] = os.path.join(tempfile.gettempdir(),
                                       'sairn-census-bypass-%d.jsonl'
                                       % os.getpid())

TIMEOUT = int(os.environ.get('SAIRN_CENSUS_TIMEOUT', '300'))

verdicts = []


def summarise():
    c = {}
    for v in verdicts:
        c[v['verdict']] = c.get(v['verdict'], 0) + 1
    return c


for i, e in enumerate(rows):
    f = e['file']
    stored = e.get('tail') or ''
    if not os.path.isfile(f):
        verdicts.append({'file': f, 'verdict': 'FILE_GONE', 'exit': None,
                         'observed': '', 'stored': stored})
        print('  %-50s FILE_GONE' % f[:50])
        continue
    cmd = [sys.executable if f.endswith('.py') else 'node', f]
    try:
        r = subprocess.run(cmd, cwd=os.getcwd(), capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           env=env, timeout=TIMEOUT)
        out = (r.stdout or r.stderr or '').strip().splitlines()
        observed = out[-1] if out else '(no output)'
        code = r.returncode
    except subprocess.TimeoutExpired:
        verdicts.append({'file': f, 'verdict': 'TIMEOUT', 'exit': None,
                         'observed': '', 'stored': stored})
        print('  %-50s TIMEOUT after %ds' % (f[:50], TIMEOUT))
        if (i + 1) % 10 == 0:
            print('    ... running census: ' + json.dumps(summarise()))
        continue

    # ── FOUR VERDICTS, AND "COULD NOT RUN" IS NOT FOLDED INTO EITHER ──────
    #   GREEN_RECOVERED  exit 0 -- the registry's own rule says delete it
    #   SKIPPED          exit 3 -- a precondition, never a pass
    #   TAIL_MATCHES     red, and the stored tail is reproducible
    #   TAIL_UNPRODUCIBLE red, and the stored tail is NOT what the runner sees
    #   EMPTY_TAIL       registered with nothing to compare
    if code == 0:
        v = 'GREEN_RECOVERED'
    elif code == 3:
        v = 'SKIPPED'
    elif not stored.strip():
        v = 'EMPTY_TAIL'
    elif KRC._same_reason(stored, observed):
        v = 'TAIL_MATCHES'
    else:
        v = 'TAIL_UNPRODUCIBLE'
    verdicts.append({'file': f, 'verdict': v, 'exit': code,
                     'observed': observed, 'stored': stored})
    print('  %-50s %-18s exit %s' % (f[:50], v, code))
    if v == 'TAIL_UNPRODUCIBLE':
        print('      stored   : ' + stored[:110])
        print('      observed : ' + observed[:110])
    if (i + 1) % 10 == 0:
        print('    ... running census: ' + json.dumps(summarise()))

print('')
print('CENSUS -- ' + str(len(verdicts)) + ' registered suites driven ALONE')
for k, n in sorted(summarise().items(), key=lambda x: -x[1]):
    print('  %-18s %3d' % (k, n))

unp = [v for v in verdicts if v['verdict'] == 'TAIL_UNPRODUCIBLE']
rec = [v for v in verdicts if v['verdict'] == 'GREEN_RECOVERED']
print('')
print('THE ANSWER b22 6.6 ASKED FOR: ' + str(len(unp)) + ' of '
      + str(len([v for v in verdicts
                 if v['verdict'] in ('TAIL_MATCHES', 'TAIL_UNPRODUCIBLE')]))
      + ' comparable rows carry a tail the runner CANNOT produce.')
for v in unp:
    print('  * ' + v['file'])
print('')
print('AND ' + str(len(rec)) + ' registered row(s) are GREEN, which the '
      'registry\'s own `_what_this_is_NOT` says must be DELETED -- while one '
      'stands it swallows the next real failure of that file:')
for v in rec:
    print('  * ' + v['file'])

# newline='' because Python on Windows otherwise writes CRLF while
# .gitattributes normalises the stored blob to LF -- `git status` stays clean
# and every later byte comparison reports a phantom difference. This file was
# written CRLF on its first run and had to be normalised by hand.
io.open('docs/b26-logs/known_red_tail_census.json', 'w',
        encoding='utf-8', newline='').write(json.dumps(
            {'measured': '2026-10-19', 'by': 'cody b26',
             'tool': 'docs/b26-logs/known_red_tail_census.py',
             'comparison': 'tools/known_red_check.py::_same_reason, imported',
             'registered_entries': len(entries),
             'driven': len(verdicts),
             'summary': summarise(),
             'verdicts': verdicts}, indent=1))
print('\nwrote docs/b26-logs/known_red_tail_census.json')
sys.exit(0)
