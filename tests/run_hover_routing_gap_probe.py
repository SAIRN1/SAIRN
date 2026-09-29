r"""tests/run_hover_routing_gap_probe.py -- control pair for
tools/hover_routing_gap_check.py.

    python tests/run_hover_routing_gap_probe.py

CONTROLS_FOR = ['tools/hover_routing_gap_check.py']
LIVE_PROBE_CLASS = 'FIXTURE'

WHY THE TOOL EXISTS, AND IT IS A MEASURED FAILURE RATHER THAN A WORRY.
The hover auditor finds things and writes them to its own tamper-evident log. The
open-work index is what a build session reads. NOTHING CONNECTS THE TWO. Three
findings sat in the log unrouted -- `leg_petcases` and `leg_processions` never
reached the index at all, and `msb_sale_hours` (log #608) stood unactioned for a
day while its tier row asserted something false about an alcohol-sale gate. All
three were landed on 2026-09-29 only because a human read the log by hand.

THE ARMS, and each is here because a plausible implementation gets it wrong:

  TRUE NEGATIVE          a routable finding that IS in the index -> silent
  CORRECTLY WITHHELD     a `no-report` entry, and an entry with no routable
                         field at all -> never flagged. The auditor deliberately
                         records findings it chose NOT to report, and flagging
                         those would make the tool an argument with a judgement.
  TRUE POSITIVE          the exact leg_petcases / leg_processions /
                         msb_sale_hours shape: routable, old, absent -> flagged
  FAIL CLOSED (x2)       log absent, and log present but unreadable -> exit 2

KNOWN-BAD CONTROL, and it is the one that matters. A naive substring matcher
matches `jobs` inside `grd_jobs`, so a finding about `jobs` would be reported as
LANDED because an unrelated resource's name contains it. The arm asserts the real
matcher refuses that AND that the naive one accepts it -- both directions, on one
fixture, so the arm cannot pass while proving nothing.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

TOOL = os.path.join(REPO, 'tools', 'hover_routing_gap_check.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/hover_routing_gap_check.py is not on disk. This '
          'control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

import hover_routing_gap_check as G   # noqa: E402

NL = chr(10)


def strip_py_comments(src):
    """Python source with docstrings and `#` comments removed.

    Small and deliberately conservative: it removes triple-quoted strings and
    trailing `#` runs, and it does NOT try to parse. Over-removal here could only
    make the arm below weaker in the direction of a false PASS, so the helper
    also asserts it left the file non-trivial.
    """
    import re as _re
    q3 = chr(34)*3
    s3 = chr(39)*3
    out = _re.sub('(?s)'+q3+'.*?'+q3, '', src)
    out = _re.sub('(?s)'+s3+'.*?'+s3, '', out)
    out = NL.join(_re.sub(r'#.*$', '', ln) for ln in out.split(NL))
    assert len(out) > len(src) // 4, (
        'strip_py_comments removed most of the file, so the arm using it would '
        'pass by having nothing left to look at')
    return out


passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:500])


def entry(seq, ts, **kw):
    e = {'seq': seq, 'ts': ts, 'type': 'finding', 'summary': '', 'target': 'hank',
         'routable': None, 'ref': ''}
    e.update(kw)
    return e


def write_log(path, rows):
    with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
        for r in rows:
            fh.write(json.dumps(r) + '\n')


NOW = '2026-09-29T12:00:00Z'
OLD = '2026-09-29T02:00:00Z'      # 10h before NOW -- past the 6h threshold
RECENT = '2026-09-29T11:45:00Z'   # 15m before NOW -- inside it

print('CONTROL PAIR -- tools/hover_routing_gap_check.py\n')

# ══ PART 1 -- THE MATCHER, which is where the known-bad lives ═══════════════
print('PART 1 -- word-boundary matching, never substring')

INDEX_WITH_GRD_JOBS = 'some row about `grd_jobs` and nothing else'

ok(G.landed_in('grd_jobs', INDEX_WITH_GRD_JOBS),
   'the real resource name is found')
ok(not G.landed_in('jobs', INDEX_WITH_GRD_JOBS),
   'KNOWN-BAD: `jobs` is NOT matched inside `grd_jobs` -- a substring matcher '
   'would report an unrouted finding as landed because an unrelated resource '
   'contains its name')
ok('jobs' in INDEX_WITH_GRD_JOBS,
   'FIXTURE VALIDITY: the naive substring test really does match here, so the '
   'arm above is proving something rather than asserting an absence that was '
   'never there')

ok(G.landed_in('leg_petcases', 'row naming `leg_petcases` in backticks'),
   'a backtick-span name is found')
ok(G.landed_in('leg_petcases', 'row naming leg_petcases bare'),
   'and so is a bare one -- the index does not always backtick')
ok(not G.landed_in('leg_pet', 'row naming `leg_petcases`'),
   'a PREFIX is not a match either -- the other direction of the same defect')
ok(not G.landed_in('petcases', 'row naming `leg_petcases`'),
   'nor is a SUFFIX after an underscore')

# ══ PART 2 -- WHICH ENTRIES ARE ROUTABLE, structured vs fallback ════════════
print('\nPART 2 -- the structured field, and the disclosed fallback')

names, source = G.routable_names(entry(1, OLD, routable=['leg_petcases']))
ok(names == ['leg_petcases'] and source == 'structured',
   'a structured --routable list is read as structured', (names, source))

names, source = G.routable_names(entry(2, OLD, routable=None,
                                       ref='leg_processions,668,docs/x.md'))
ok('leg_processions' in names and source == 'prose-fallback',
   'an entry logged BEFORE the field existed falls back to its ref, and the '
   'source is DISCLOSED as weaker rather than silently equated', (names, source))

names, source = G.routable_names(entry(3, OLD, type='no-report',
                                       routable=['leg_petcases']))
ok(names == [] and source == 'withheld',
   'a `no-report` entry is NEVER routable -- the auditor records findings it '
   'deliberately chose not to report, and flagging those would make this tool '
   'an argument with a judgement', (names, source))

names, source = G.routable_names(entry(4, OLD, type='check', ref='ran a thing'))
ok(names == [] and source in ('none', 'withheld'),
   'a plain check with no resource-shaped ref yields nothing', (names, source))

# ══ PART 3 -- THE FOUR FIXTURE ARMS, through gaps() ═════════════════════════
print('\nPART 3 -- the four fixture arms')

INDEX_ALL = 'rows naming `leg_petcases`, `leg_processions` and `msb_sale_hours`'
INDEX_NONE = 'an index with none of them in it'

rows_landed = [entry(i, OLD, routable=['leg_petcases']) for i in range(1, 21)]
g = G.gaps(rows_landed, INDEX_ALL, now=NOW)
ok(g == [], 'TRUE NEGATIVE: a routable finding that IS in the index is silent', g)

rows_withheld = ([entry(1, OLD, type='no-report', routable=['leg_petcases'])]
                 + [entry(i, OLD, type='check') for i in range(2, 21)])
g = G.gaps(rows_withheld, INDEX_NONE, now=NOW)
ok(g == [],
   'CORRECTLY WITHHELD: a no-report entry and 19 plain checks produce nothing, '
   'even with an index that names none of them', g)

rows_gap = ([entry(1, OLD, routable=['leg_petcases', 'leg_processions',
                                     'msb_sale_hours'])]
            + [entry(i, OLD, type='check') for i in range(2, 21)])
g = G.gaps(rows_gap, INDEX_NONE, now=NOW)
ok(len(g) == 3,
   'TRUE POSITIVE: the exact leg_petcases / leg_processions / msb_sale_hours '
   'shape is flagged, one finding per resource (got %d)' % len(g), g)
ok(all(x['seq'] == 1 for x in g) and {x['resource'] for x in g}
   == {'leg_petcases', 'leg_processions', 'msb_sale_hours'},
   'and each names its log entry and its resource', g)
ok(all('reasoned' in (x.get('threshold_note') or '').lower() for x in g),
   'and every finding carries the note that the threshold is REASONED, not '
   'calibrated -- a number presented as measured when it was chosen is the '
   'defect this platform names repeatedly', g)

# ── NEITHER THRESHOLD ALONE, which is a real way to get this wrong ─────────
rows_recent = ([entry(1, RECENT, routable=['leg_petcases'])]
               + [entry(i, RECENT, type='check') for i in range(2, 4)])
g = G.gaps(rows_recent, INDEX_NONE, now=NOW)
ok(g == [],
   'a finding 15 minutes old with 2 entries after it is NOT flagged -- the '
   'auditor is given room to route its own work', g)

rows_age_only = ([entry(1, OLD, routable=['leg_petcases'])]
                 + [entry(i, OLD, type='check') for i in range(2, 4)])
g = G.gaps(rows_age_only, INDEX_NONE, now=NOW)
ok(len(g) == 1, 'AGE alone is enough (10h old, only 2 entries after it)', g)

rows_count_only = ([entry(1, RECENT, routable=['leg_petcases'])]
                   + [entry(i, RECENT, type='check') for i in range(2, 30)])
g = G.gaps(rows_count_only, INDEX_NONE, now=NOW)
ok(len(g) == 1, 'and ENTRY COUNT alone is enough (28 entries after it, 15m old) '
   '-- OR, not AND, because a busy hour buries a finding as effectively as a '
   'quiet day does', g)

# ══ PART 4 -- FAIL CLOSED, twice ═══════════════════════════════════════════
print('\nPART 4 -- fail closed on unknown, never silent')


def run(*args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')

rc, out = run('--log', os.path.join('docs', '_zz_no_such_hover_log.jsonl'))
ok(rc == EXIT_COULD_NOT_RUN,
   'FAIL CLOSED 1: an ABSENT log is exit 2, not 0 (got %d). "No findings" and '
   '"could not look" are different answers and this tool runs on a machine '
   'where the log may legitimately not exist' % rc, out[-400:])
ok('COULD NOT RUN' in out and 'hover' in out.lower(),
   'and it says so, naming what it could not read', out[-300:])

tmp = tempfile.mkdtemp(prefix='sairn_hrg_')
try:
    bad = os.path.join(tmp, 'garbage.jsonl')
    io.open(bad, 'w', encoding='utf-8').write('this is not json\nnor is this\n')
    rc, out = run('--log', bad)
    ok(rc == EXIT_COULD_NOT_RUN,
       'FAIL CLOSED 2: a log present but with NO parseable entry is exit 2 (got '
       '%d) -- a file that reads as zero findings is the shape that turns a '
       'broken reader into a clean report' % rc, out[-400:])

    empty = os.path.join(tmp, 'empty.jsonl')
    io.open(empty, 'w', encoding='utf-8').write('')
    rc, out = run('--log', empty)
    ok(rc == EXIT_COULD_NOT_RUN,
       'and an EMPTY log is exit 2 for the same reason (got %d)' % rc,
       out[-300:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ══ PART 5 -- THE REAL LOG, reported not asserted ══════════════════════════
print('\nPART 5 -- the real machine, reported not asserted')
rc, out = run()
print('  --   against the real hover log: exit %d. NOT AN ASSERTION -- whether a '
      'finding is currently unrouted is the state of two documents, not a '
      'property of this tool.' % rc)
ok(rc in (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN),
   'it exits one of the three defined codes (got %d)' % rc, out[-300:])
ok('REASONED, NOT CALIBRATED' in out.upper(),
   'and the real run states the threshold is reasoned rather than calibrated',
   out[-500:])
# ASSERTED ON THE SOURCE, NOT ON THE OUTPUT. The first version of this arm
# tested `'defect_register' not in out` and FAILED -- because the tool's report
# says, correctly, that it deliberately does NOT use the register. An arm that
# forbids a tool from EXPLAINING its own boundary punishes the disclosure, and
# would have been "fixed" by deleting the explanation. What matters is that no
# code path reaches the register, so the SOURCE is what is checked, with comments
# and docstrings stripped so the explanation itself cannot trip it -- the same
# PR 1.2 distinction the X-SD-Auth check needed.
TOOL_SRC = io.open(TOOL, encoding='utf-8').read()
CODE_ONLY = strip_py_comments(TOOL_SRC)
ok(not re.search(r'^\s*(import|from)\s+defect_register', CODE_ONLY, re.M)
   and 'subprocess' not in CODE_ONLY,
   'and NO CODE PATH reaches tools/defect_register.py -- it is not imported, and '
   'the tool spawns NO SUBPROCESS AT ALL, so there is no route to it. Asserted on '
   'the source with comments and docstrings stripped, and on the mechanism rather '
   'than on the token: the report text NAMES the register in a print() in order to '
   'say it is not used, and an arm forbidding that would be "fixed" by deleting '
   'the explanation -- the same PR 1.2 code-versus-text distinction the X-SD-Auth '
   'check needed, one level up',
   [l for l in CODE_ONLY.split(NL)
    if re.search(r'import\s+defect_register|subprocess', l)][:3])
ok('defect_register' in TOOL_SRC,
   'FIXTURE VALIDITY: the register IS named in the tool, in prose, so the arm '
   'above is distinguishing code from text rather than asserting an absence '
   'that was never there')

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
