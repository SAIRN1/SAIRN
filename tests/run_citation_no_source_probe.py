r"""tests/run_citation_no_source_probe.py -- control pair for
tools/citation_no_source_report.py.

    python tests/run_citation_no_source_probe.py

CONTROLS_FOR = ['tools/citation_no_source_report.py']
LIVE_PROBE_CLASS = 'FIXTURE'

EVERY CRITERION IS DRIVEN AGAINST A KNOWN-BAD FIXTURE BEFORE THE CORPUS, which is
the standing rule this session adopted after two criteria came out wrong: a sweep
that counted `open(` as corroboration reported 3 findings out of 263 and looked like
good news, and a citation repoint was not idempotent and double-shifted ten cites.
A vacuous pass has to be impossible by construction, not unlikely.

THE FOUR CRITERIA, each with a fixture in BOTH directions:

  a row that CITES a line                    -> not a finding
  a row that cites NOTHING                   -> a finding
  ... and ADMITS it was not read             -> a DISCLOSED gap
  ... and CLAIMS an individual read          -> the CONTRADICTION bucket

and two fail-closed arms: an absent document, and a document whose rows do not
parse -- because a count of zero uncited rows reads as perfect coverage and is
exactly what a broken parser produces.
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

TOOL = os.path.join(REPO, 'tools', 'citation_no_source_report.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/citation_no_source_report.py is not on disk. '
          'This control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

import citation_no_source_report as C   # noqa: E402

NL = chr(10)
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


def row(res, tier, conf, cell):
    return '| `%s` | **%s** | **%s** | consequence | confidentiality | %s |' % (
        res, tier, conf, cell)


print('CONTROL PAIR -- tools/citation_no_source_report.py' + NL)
print('CRITERIA, each against a known-bad fixture BEFORE the corpus')

# 1. CITES a line -> not a finding
doc = NL.join([row('a_cited', 'A', 'B',
                   'READ OUT OF THE APP: `app.html:1234` writes `{id}`')])
rows, cited, no_cite, contra, disc, grp = C.scan(doc)
ok(len(rows) == 1 and cited == ['a_cited'] and no_cite == [],
   'a row citing `app.html:1234` is NOT a finding',
   (rows, cited, no_cite))

# 2. cites NOTHING -> a finding
doc = NL.join([row('b_bare', 'B', 'B', 'Operational data lost or wrong')])
rows, cited, no_cite, contra, disc, grp = C.scan(doc)
ok(len(no_cite) == 1 and no_cite[0]['resource'] == 'b_bare',
   'a row citing no line IS a finding', no_cite)
ok(contra == [] and disc == [],
   'and with neither phrase it lands in neither sub-bucket -- the tool counts '
   'that third group separately rather than folding it into one of the two',
   (contra, disc))

# 3. cites nothing and ADMITS it -> disclosed
doc = NL.join([row('c_admits', 'B', 'B',
                   'Classified by the stated B rule rather than individually '
                   'read')])
rows, cited, no_cite, contra, disc, grp = C.scan(doc)
ok(len(disc) == 1 and contra == [],
   'a row that ADMITS it was not read individually is a DISCLOSED gap, not a '
   'contradiction -- being honest about a default must not score worse than '
   'saying nothing', (contra, disc))

# 4. cites nothing and CLAIMS a read -> the contradiction
doc = NL.join([row('d_claims', 'A', 'A',
                   '**2026-09-23 re-audit, read individually.** CONFIRMED A')])
rows, cited, no_cite, contra, disc, grp = C.scan(doc)
ok(len(contra) == 1 and contra[0]['resource'] == 'd_claims',
   'THE ARM THAT MATTERS: a row claiming an individual read while pointing at NO '
   'line is the CONTRADICTION bucket. The other two groups are disclosed gaps; '
   'this one asserts evidence it does not show', (contra, disc))

# 5. BOTH phrases -> disclosed wins, because the admission is the specific one
doc = NL.join([row('e_both', 'B', 'B',
                   'read individually. Classified by the stated B rule rather '
                   'than individually read')])
rows, cited, no_cite, contra, disc, grp = C.scan(doc)
ok(len(disc) == 1 and contra == [],
   'and a cell containing BOTH phrases counts as DISCLOSED, not contradictory -- '
   'over-accusing is the direction that gets a report ignored', (contra, disc))

# 6. A GROUP STAMP IS EVIDENCE, NOT A CONTRADICTION -- the criterion I got wrong
#    and caught before reporting the number. The first version called 138 rows
#    contradictory; 106 of them carry a 3.2 pass group stamp, which the register's
#    own header describes as a deliberate form of evidence ("so a reader can
#    disagree with a GROUP rather than with 99 separate judgements").
doc = NL.join([row('g_stamped', 'A', 'B',
                   'Money. **Confidentiality individually read in the 3.2 pass, '
                   '2026-09-22 (MONEY_INTERNAL)**')])
rows, cited, no_cite, contra, disc, grp = C.scan(doc)
ok(len(grp) == 1 and contra == [],
   'THE CRITERION I GOT WRONG: a row carrying a 3.2 GROUP STAMP is its own '
   'category, not a contradiction. Flattening the two over-accused 106 rows, and '
   'over-accusing is the direction that gets a report ignored -- which this '
   'report says in its own closing text about something else', (contra, grp))
ok(len(no_cite) == 1,
   'and it is still counted as citing no line, because it does not -- the group '
   'stamp is weaker evidence, not a citation', no_cite)

# 6b. FIXTURE VALIDITY, in the other direction: the contradiction arm must be
#    capable of firing on the real corpus vocabulary, not only on my fixture.
doc = NL.join([row('f_real', 'A', 'A',
                   '**FULLY RE-AUDITED 2026-09-23, read individually.** '
                   'CONFIRMED A, individually read rather than defaulted.')])
rows, cited, no_cite, contra, disc, grp = C.scan(doc)
ok(len(contra) == 1,
   'and it fires on the register\'s OWN wording, taken verbatim from a real row '
   'shape rather than invented for the fixture', contra)

# ══ FAIL CLOSED ════════════════════════════════════════════════════════════
print(NL + 'FAIL CLOSED -- a count of zero must never read as full coverage')


def run(*args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


rc, out = run('--doc', os.path.join('docs', '_zz_no_such_register.md'))
ok(rc == EXIT_COULD_NOT_RUN,
   'an ABSENT document is exit 2, not 0 (got %d) -- an absent document is not a '
   'document with full coverage' % rc, out[-300:])

tmp = tempfile.mkdtemp(prefix='sairn_cns_')
try:
    p = os.path.join(tmp, 'noparse.md')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(
        '# a document with no resource rows at all' + NL)
    rc, out = run('--doc', p)
    ok(rc == EXIT_COULD_NOT_RUN,
       'a document whose ROWS DO NOT PARSE is exit 2 (got %d). Zero uncited rows '
       'out of zero rows is what a broken parser produces and it reads as '
       'perfect coverage' % rc, out[-400:])
    ok('would read as perfect coverage' in out or 'read as perfect coverage' in out,
       'and it says why, rather than printing a bare refusal', out[-400:])
finally:
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

# ══ THE REAL CORPUS, reported not asserted ═════════════════════════════════
print(NL + 'THE REAL REGISTER -- reported, not asserted')
rc, out = run()
print('  --   exit %d' % rc)
ok(rc in (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN),
   'it exits one of the three defined codes', out[-300:])
ok('COVERAGE FIGURE, NOT A DEFECT COUNT' in out,
   'and it says the number is coverage rather than bugs, because "209 findings" '
   'reads as 209 defects')
ok('NOT THE RULE THAT WAS SCOPED' in out,
   'and it says which rule it is NOT, so a reader does not take it for the '
   'write-site rule that was measured and declined')

print(NL + '%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
