"""tests/run_fmea_probe.py -- the risk drafter cites or says nothing, and the
scorer refuses to invent a number.

    python tests/run_fmea_probe.py

A risk generator that emits plausible-sounding text is a FABRICATION ENGINE.
These arms exist because the first version of the scorer WAS one: it matched on
three shared content words, reported 38% accuracy, and every one of those five
hits came from a draft of a WORKLOG file, on overlaps like (never, nothing,
push). A worklog accumulates the prose of every defect ever recorded.

So the arms that matter are not "does it produce output". They are:
  * every emitted risk carries a citation, or it is not emitted;
  * a target that RECORDS defects rather than having them is refused;
  * no detector fires on more than a third of the tree (a rule that fires on
    half the repo is a horoscope);
  * the scorer reports NO-DRAFT first and never quotes the drafted-only rate
    on its own.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import fmea_draft as D                                      # noqa: E402
import fmea_prediction_check as P                           # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


def run(tool, *args):
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', tool)] + list(args),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=REPO)
    return p.returncode, (p.stdout or '') + (p.stderr or '')

records = D.load_register()
titles = D.rule_titles()

print('1. every emitted risk carries a citation -- no citation, no risk')
seen = 0
for target in ('tools/md_table_check.py', 'tools/sairn_claim.py',
               'api/_lib/wip-accounting.js', 'sairnvet.html'):
    a = D.analyse(target, records, titles)
    for r in a['risks']:
        seen += 1
        if not r.get('cite'):
            check('1a  a risk with no citation was emitted for ' + target, False, r)
check('1a  every risk across four real targets carries a citation', True,
      '%d risks checked' % seen)
check('1b  and there were some, so 1a is not vacuous', seen > 0, seen)

print('2. a target that RECORDS defects is refused, not drafted')
for bad in ('SAIRN-ACTIVE-WORK-cody.md', 'docs/SAIRN-OPEN-WORK-INDEX.md',
            'docs/traceability-matrix.md'):
    a = D.analyse(bad, records, titles)
    check('2a  refused: ' + bad, bool(a.get('refused')) and not a['risks'])
a = D.analyse('tools/md_table_check.py', records, titles)
check('2b  CONTROL: a real code file is NOT refused -- or 2a passes on a '
      'drafter that refuses everything', not a.get('refused'))

print('3. no detector is a horoscope')
n, hits = D.fire_rates()
check('3a  the tree was actually scanned', n > 50, '%d files' % n)
for rid, _, _, _ in D.DETECTORS:
    pct = 100.0 * hits[rid] / n
    if hits[rid] == 0:
        continue          # a .sql-only detector correctly never fires on .py
    check('3b  %-5s fires on %.0f%% of the tree (must be under 35%%)' % (rid, pct),
          pct < 35.0)
check('3c  at least half the detectors fire SOMEWHERE -- a table of dead '
      'detectors would pass 3b trivially',
      sum(1 for r in hits if hits[r] > 0) >= len(D.DETECTORS) // 2,
      '%d of %d fire' % (sum(1 for r in hits if hits[r] > 0), len(D.DETECTORS)))

print('4. the drafter never claims a clean bill of health')
tmp = tempfile.mkdtemp(prefix='fmea-')
rc, out = run('fmea_draft.py', 'tools/fmea_draft.py')
check('4a  it runs', rc == 0, 'exit %d' % rc)
rc, out = run('fmea_draft.py', 'no/such/file/anywhere.py')
check('4b  an unknown file says NOTHING MATCHED is not a clean bill of health',
      'NOTHING MATCHED' in out and 'not a clean bill of health' in out)
check('4c  and every run names the rules with no detector yet',
      'NO DETECTOR YET' in out)

print('5. the scorer refuses to invent a number')
check('5a  matching is by RULE CITATION only -- word overlap is gone',
      P.matched({'risks': [{'cite': 'docs/SAIRN-PROCESS-RULES.md section 1.1',
                            'risk': 'a check that cannot fail'}]},
                {'summary': 'a check that cannot fail was shipped'})[0] is None,
      'identical words must NOT score as a prediction without a rule id')
check('5b  a real rule match on BOTH sides does score',
      P.matched({'risks': [{'cite': 'docs/SAIRN-PROCESS-RULES.md section 1.1',
                            'risk': 'x'}]},
                {'summary': 'y', 'rules': ['1.1']})[0] == 'rule 1.1')
check('5c  a DIFFERENT rule does not score',
      P.matched({'risks': [{'cite': 'docs/SAIRN-PROCESS-RULES.md section 1.1',
                            'risk': 'x'}]},
                {'summary': 'y', 'rules': ['2.3']})[0] is None)

rc, out = run('fmea_prediction_check.py')
check('5d  it runs', rc == 0, 'exit %d' % rc)
check('5e  NO DRAFT is reported FIRST, above the hit rate',
      out.index('NO DRAFT AT ALL') < out.index('predicted'))
if 'over drafted files only' in out:
    check('5f  the drafted-only rate is never offered without its warning',
          'DO NOT QUOTE THIS ALONE' in out)
else:
    # DECLARED INAPPLICABLE, and the reason moved. It used to be "no drafts
    # exist"; twelve drafts exist now and the line is still absent, because
    # nothing is SCOREABLE -- every draft postdates every defect, so predicted
    # and missed are both zero and there is no drafted-only rate to warn about.
    check('5f  DECLARED INAPPLICABLE: nothing is scoreable yet, so no '
          'drafted-only rate was printed to warn about',
          'predicted             : 0' in out)

print('\n6. a draft cannot predict what already happened')
# THE BACKDATING ARM. The first run that ever had drafts on disk scored one
# PREDICTION from a draft saved the same afternoon as the defect it "predicted"
# -- the comparison was `>` on day-resolution dates, so same-day counted as
# before. A risk tool scoring itself right on a defect that had already
# happened is the fabrication shape the whole pipeline is built against,
# arriving through the TIMESTAMP instead of through the generator.
FIX = 'tools/probe_fixture_target.py'
REC = {'summary': 'x', 'rules': ['1.1'], 'date': '2026-09-10',
       'files': [FIX]}
RISK = {'cite': 'docs/SAIRN-PROCESS-RULES.md section 1.1', 'risk': 'x'}


def score(draft_date):
    """Run the real bucketing with one draft and one defect."""
    saved_records = P.load_register
    saved_drafts = P.load_drafts
    P.load_register = lambda: [dict(REC)]
    P.load_drafts = lambda: [{'target': FIX, 'risks': [dict(RISK)],
                              '_file': 'docs/fmea/fixture.json',
                              'drafted_on': draft_date,
                              '_asof': draft_date}]
    try:
        import io as _io
        buf, real = _io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            P.main(['--json'])
        finally:
            sys.stdout = real
        return json.loads(buf.getvalue())
    finally:
        P.load_register = saved_records
        P.load_drafts = saved_drafts


before = score('2026-09-09')
same = score('2026-09-10')
after = score('2026-09-11')
check('6a  a draft written BEFORE the defect scores it',
      before['predicted'] == 1, before)
check('6b  a SAME-DAY draft does NOT score it -- day-resolution dates cannot '
      'show it preceded the defect', same['predicted'] == 0, same)
check('6c  and that same-day draft lands in its own bucket, not NO DRAFT',
      same['draft_newer_than_defect'] == 1 and same['no_draft'] == 0, same)
check('6d  a draft written AFTER is likewise unscoreable, not a miss',
      after['predicted'] == 0 and after['missed'] == 0 and
      after['draft_newer_than_defect'] == 1, after)
check('6e  CONTROL: the before-case really is a MISS when the rule differs, '
      'so 6a is not scoring on the date alone',
      P.matched({'risks': [dict(RISK)]},
                {'summary': 'x', 'rules': ['2.3']})[0] is None)

print('7. a same-file register risk can be scored; a same-app one cannot')
# WHY THIS SECTION EXISTS, measured before it was written: matched() scored
# only on risks citing the rules document, and no defect-register risk does --
# it cites a commit SHA. Over the 12 drafts then on disk, 19 of 274 risks
# (6.9%) could EVER produce a PREDICTED, so drafting the 60 undrafted code
# files would have raised coverage while leaving the scoreable surface flat.
SAME_FILE = {'source': 'defect-register', 'cite': 'abc123def456',
             'risk': 'a hung write never settled', 'rules': ['1.5']}
SAME_APP = {'source': 'defect-register', 'cite': 'abc123def456',
            'risk': 'a hung write never settled elsewhere'}

check('7a  a same-file register risk whose rule the defect cites DOES score',
      P.matched({'risks': [dict(SAME_FILE)]},
                {'summary': 'y', 'rules': ['1.5']})[0] is not None)
check('7b  and it says WHICH rule and that it came from a register risk',
      '1.5' in (P.matched({'risks': [dict(SAME_FILE)]},
                          {'summary': 'y', 'rules': ['1.5']})[0] or '')
      and 'same-file' in (P.matched({'risks': [dict(SAME_FILE)]},
                                    {'summary': 'y', 'rules': ['1.5']})[0] or ''))
check('7c  a DIFFERENT rule still does not score -- this is exact-id '
      'equality, not the word overlap that scored 38%',
      P.matched({'risks': [dict(SAME_FILE)]},
                {'summary': 'y', 'rules': ['2.3']})[0] is None)
check('7d  a NOT-CITABLE record matches nothing, so the escape hatch that '
      'stops manufactured agreement still works',
      P.matched({'risks': [dict(SAME_FILE)]}, {'summary': 'y', 'rules': []})[0] is None)
check('7e  A SAME-APP RISK CARRIES NO RULES AND MUST NOT SCORE -- otherwise '
      'every PLATFORM draft predicts every PLATFORM defect',
      P.matched({'risks': [dict(SAME_APP)]},
                {'summary': 'y', 'rules': ['1.5']})[0] is None)
check('7f  CONTROL: 7e is not passing because the whole mechanism is dead -- '
      'the identical risk WITH rules does score',
      P.matched({'risks': [dict(SAME_APP, rules=['1.5'])]},
                {'summary': 'y', 'rules': ['1.5']})[0] is not None)

# THE GENERATOR HALF. The matcher can only read what fmea_draft.py writes, so
# the two arms above are worth nothing unless the drafter actually attaches
# `rules` to same-file risks and withholds them from same-app ones.
import json as _json                                                # noqa: E402
# --json emits a LIST of per-target drafts, not a single object. The first
# version of this arm read it as an object, got no risks, and 7h/7i passed
# VACUOUSLY over an empty list -- which is exactly what 7g is here to catch,
# and it caught it. The target is one with real same-file register history;
# a file whose only risks are process-rules ones cannot exercise this at all.
_rc, _out = run('fmea_draft.py', 'tests/faults/transport_timeout_sweep.js', '--json')
try:
    _d = _json.loads(_out)
    _risks = [r for t in (_d if isinstance(_d, list) else [_d])
              for r in (t.get('risks') or [])]
except Exception:                                                   # noqa: BLE001
    _risks = []
_sf = [r for r in _risks if 'THIS FILE' in (r.get('basis') or '')]
_sa = [r for r in _risks if 'same app' in (r.get('basis') or '')]
check('7g  the drafter emitted same-file risks to judge at all', len(_sf) > 0,
      'no same-file risk in the draft, so 7h is vacuous')
check('7h  every same-file risk carries a `rules` key',
      all('rules' in r for r in _sf), [r.get('basis') for r in _sf][:3])
check('7i  and no same-app risk does', all('rules' not in r for r in _sa),
      '%d same-app risk(s) carry rules' % len([r for r in _sa if 'rules' in r]))

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
