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
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(rows) == 1 and cited == ['a_cited'] and no_cite == [],
   'a row citing `app.html:1234` is NOT a finding',
   (rows, cited, no_cite))

# 2. cites NOTHING -> a finding
doc = NL.join([row('b_bare', 'B', 'B', 'Operational data lost or wrong')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
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
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(disc) == 1 and contra == [],
   'a row that ADMITS it was not read individually is a DISCLOSED gap, not a '
   'contradiction -- being honest about a default must not score worse than '
   'saying nothing', (contra, disc))

# 4. cites nothing and CLAIMS a read -> the contradiction
doc = NL.join([row('d_claims', 'A', 'A',
                   '**2026-09-23 re-audit, read individually.** CONFIRMED A')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(contra) == 1 and contra[0]['resource'] == 'd_claims',
   'THE ARM THAT MATTERS: a row claiming an individual read while pointing at NO '
   'line is the CONTRADICTION bucket. The other two groups are disclosed gaps; '
   'this one asserts evidence it does not show', (contra, disc))

# 5. BOTH phrases -> disclosed wins, because the admission is the specific one
doc = NL.join([row('e_both', 'B', 'B',
                   'read individually. Classified by the stated B rule rather '
                   'than individually read')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
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
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
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
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(contra) == 1,
   'and it fires on the register\'s OWN wording, taken verbatim from a real row '
   'shape rather than invented for the fixture', contra)

# ══ THE FOURTH EVIDENCE SHAPE, AND THE SECOND TIME THIS BUCKET OVER-ACCUSED ══
# The group-stamp correction above took CONTRADICTORY from 138 to 32 and stopped.
# Reading all 32 by hand found 31 carrying real, disclosed evidence in a form the
# tool did not recognise, and 1 that was a regex false positive. The honest count
# is ZERO. These arms lock each shape, in BOTH directions, against fixtures.
print(NL + 'THE FOURTH EVIDENCE SHAPE -- a dated read, or a field list, with no line')

# 7. AXIS + read + DATE AFTER it -> evidence, not a contradiction
doc = NL.join([row('h_dated', 'A', 'A',
                   'A named patient is disclosed. **Confidentiality '
                   'individually read 2026-09-22**')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(rdis) == 1 and contra == [],
   'a row stamped "Confidentiality individually read 2026-09-22" is a DATED '
   'READ, not a contradiction -- 27 real rows carry exactly this and were all '
   'being accused of showing no evidence', (contra, rdis))
ok(len(no_cite) == 1,
   'and it still counts as citing no LINE, because it does not -- the date is '
   'weaker evidence, not a citation', no_cite)

# 7b. THE DATE MUST FOLLOW THE READ. A date sitting NEAR a bare claim is still a
#     bare claim, and this is the arm that keeps the fix from swallowing the
#     bucket whole.
doc = NL.join([row('i_datefirst', 'A', 'A',
                   '**FULLY RE-AUDITED 2026-09-23.** Read individually and '
                   'confirmed A.')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(contra) == 1 and rdis == [],
   'KNOWN-BAD CONTROL: a date BEFORE the claim, with no axis word, is still a '
   'contradiction. If this lands in the dated bucket the fix has emptied the '
   'bucket by widening rather than by measuring', (contra, rdis))

# 7c. an axis word with a read and NO date -> still a contradiction
doc = NL.join([row('j_nodate', 'A', 'B',
                   'Confidentiality individually read and left at B.')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(contra) == 1 and rdis == [],
   'KNOWN-BAD CONTROL: an axis and a read with NO date is a contradiction -- '
   'the date is what makes it a stamp somebody can check', (contra, rdis))

# 8. CONFIRMED B/B BY INDIVIDUAL READ -> evidence
doc = NL.join([row('k_confirmed', 'B', 'B',
                   '**CONFIRMED B/B BY INDIVIDUAL READ, 2026-09-24 (hover H1 '
                   'log #531).**')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(rdis) == 1 and contra == [],
   'an explicit "CONFIRMED B/B BY INDIVIDUAL READ" is evidence -- 3 real rows '
   'carry it with an auditor log reference', (contra, rdis))

# 9. READ OUT OF THE <X>: {field list} -> evidence, with no line number
doc = NL.join([row('l_fields', 'A', 'A',
                   'READ OUT OF THE APP: `{asked_at, date, patient, answer, '
                   'statement_version}`')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(rdis) == 1 and contra == [],
   'a FIELD LIST lifted out of the source is evidence without a line number',
   (contra, rdis))
doc = NL.join([row('m_handler', 'A', 'B',
                   'READ OUT OF THE HANDLER: `{warranty_id, job_id, '
                   'manufacturer, registered_at}`')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(rdis) == 1 and contra == [],
   'and HANDLER counts as well as APP -- two real rows say HANDLER, and a rule '
   'keyed on the single word APP would have missed both', (contra, rdis))

# 9b. KNOWN-BAD: "READ OUT OF THE APP" with NO field list and no line
doc = NL.join([row('n_bareread', 'A', 'A',
                   'READ OUT OF THE APP and confirmed A. No details given.')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(contra) == 1 and rdis == [],
   'KNOWN-BAD CONTROL: the words "READ OUT OF THE APP" with NO field list '
   'behind them are a claim, not evidence', (contra, rdis))

# 10. A GROUP STAMP STILL WINS over a dated read when a cell carries both,
#     because a named group is the stronger disclosure -- a reader can disagree
#     with a group and cannot disagree with a date.
doc = NL.join([row('o_both', 'A', 'A',
                   '**Confidentiality individually read in the 3.2 pass, '
                   '2026-09-22 (MONEY_INTERNAL)**')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(grp) == 1 and rdis == [] and contra == [],
   'a cell carrying BOTH a group stamp and a dated read is reported under the '
   'GROUP -- 14 real sv_ rows carry both, and reporting them as merely dated '
   'would lose the group a reader can argue with', (grp, rdis))

# 11. `re-derived` USED ABOUT THE DATA IS NOT A CLAIM OF A READ
doc = NL.join([row('p_rederived', 'A', 'A',
                   'Losing a milestone is an operational nuisance: the matter '
                   'survives it and the stage can be re-derived. READING one '
                   'is not.')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(contra == [] and rdis == [],
   'KNOWN-BAD, FIXED: "the stage can be re-derived" is a sentence about whether '
   'lost DATA can be reconstructed, not a claim that anybody read the row. It '
   'was the sole basis for accusing law_mattermilestones', (contra, rdis))
doc = NL.join([row('q_rederived_head', 'A', 'A',
                   'Tier and confidentiality re-derived at HEAD, 2026-09-29.')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(len(contra) == 1 or len(rdis) == 1,
   'and the narrowing did not kill the real form: "re-derived AT HEAD" is still '
   'a claim of a read and is still counted', (contra, rdis))

# 12. A CITATION UNDER LINE 100, attached to a path
doc = NL.join([row('r_shortline', 'B', 'B',
                   '`api/_resources/stonedesk.js:27` records that this resource '
                   'is keyed (license_hash, employee_id)')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(cited == ['r_shortline'] and no_cite == [],
   'KNOWN-BAD, FIXED: `api/_resources/stonedesk.js:27` IS a citation. The '
   'shipped rule needed three digits, so it excluded the first 99 lines of '
   'every file -- and api/_resources declarations live at the top', (cited, no_cite))
doc = NL.join([row('s_barenumber', 'B', 'B',
                   'The signing window is 8:30 and the review runs :45 past.')])
rows, cited, no_cite, contra, disc, grp, rdis = C.scan(doc)
ok(no_cite and cited == [],
   'CONTROL: a bare two-digit `:45` with no path is NOT promoted to a citation '
   '-- the widening is attached to a path on purpose', (cited, no_cite))

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
ok('CONTRADICTORY (0)' in out or 'CONTRADICTORY (' in out,
   'and it prints the contradiction bucket either way -- a bucket that '
   'disappears when it is empty is indistinguishable from a bucket nobody '
   'computed', out[-600:])
ok('NOT THE RULE THAT WAS SCOPED' in out,
   'and it says which rule it is NOT, so a reader does not take it for the '
   'write-site rule that was measured and declined')

print(NL + '%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
