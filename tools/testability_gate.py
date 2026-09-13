"""Does a requirement carry a claim somebody could falsify by running something?

    python tools/testability_gate.py                 # the real matrix
    python tools/testability_gate.py --fixtures      # the lock, on its own
    python tools/testability_gate.py --json
    python tools/testability_gate.py --text "some requirement sentence"

── THE LOCK, AND IT IS THE POINT OF THIS TOOL ────────────────────────────
THE CRITERIA ARE LOCKED BEFORE THIS RUNS AGAINST REAL CODE, and that is
enforced rather than promised: `tools/testability_criteria.py` holds the rules
AND a set of hand-decided fixtures, and THIS TOOL REFUSES TO JUDGE A SINGLE
REAL REQUIREMENT UNLESS EVERY FIXTURE CLASSIFIES CORRECTLY FIRST.

Why that is not ceremony. A gate whose criteria were derived from what the
corpus already says is a description wearing a check's clothes: it passes by
construction and tells you nothing. Hours before this was written, an FMEA
scorer on this platform reported 38% accuracy from a rule chosen because it
produced a number -- and every one of those hits was a false positive. Criteria
quietly loosened to flatter the real matrix will break a fixture before they
can flatter anything.

The criteria carry a VERSION. It is printed on every run and belongs in any
comparison of two runs: a pass rate that improved across a version change is
evidence about the criteria, not about the requirements.

── REPORT-ONLY, AND THE PREMORTEM THAT DECIDED THAT ───────────────────────
"This shipped and got switched off -- why?" Because it flagged good prose and
somebody got tired of it. That is not hypothetical: `nav_panel_check` reported
ALL 26 SAIRNfreedom panels unreachable because it scanned `<button>` and that
app navigates with divs. So this never blocks, the burden is on the CHECKER to
show a requirement is untestable rather than on the requirement to prove
itself, and the false-positive rate over the real corpus is printed on every
run so it can be argued with.

── WHAT IT CANNOT SEE, said here rather than discovered later ────────────
  * whether a testable-LOOKING requirement is actually true. This is about
    falsifiability, never about correctness;
  * a requirement that is precise and measures the wrong thing;
  * anything outside docs/traceability-matrix.md. Requirements living in prose
    elsewhere are not reached, and that is a coverage gap, not a clean result.

Exit 0 when every requirement is testable or declared, 1 when at least one is
not, 2 when the fixtures fail -- which means the criteria are not trustworthy
and NOTHING was judged.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import testability_criteria as C                                  # noqa: E402

MATRIX = os.path.join(REPO, 'docs', 'traceability-matrix.md')

# Requirements judged untestable ON PURPOSE, each with a reason beside it. The
# same two-list discipline as the cache-purge guards: an exclusion is a
# decision with a reason, never a silence. Empty today -- it is populated only
# when a real row is argued through, never pre-filled to make a run look clean.
DECLARED = {}


def _norm(s):
    s = re.sub(r'`([^`]*)`', r'\1', s or '')          # code spans are content
    s = re.sub(r'\*\*|~~|\*', '', s)
    s = re.sub(r'&mdash;|&[a-z]+;|&#\d+;', ' ', s)
    s = re.sub(r'<br\s*/?>', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def classify(text):
    """One of PASS / VAGUE / NO-CLAIM / TOO-SHORT / UNFALSIFIABLE, plus why."""
    t = _norm(text)
    low = ' ' + t.lower() + ' '
    words = [w for w in re.findall(r"[A-Za-z_][A-Za-z_'-]*", t)]

    # ORDER MATTERS, and getting it wrong is the first thing the fixtures
    # caught. "errors are reported appropriately" is four words AND vague; if
    # length is tested first it comes back TOO-SHORT and the vague word -- the
    # thing that actually needs fixing -- is never mentioned. So the SPECIFIC
    # verdicts are tested before the structural one.
    for h in C.HEDGE:
        if h in low:
            return 'UNFALSIFIABLE', 'hedged with "%s" -- true whatever happens' % h.strip()

    for v in C.VAGUE:
        if re.search(r'(?<![A-Za-z])' + re.escape(v) + r'(?![A-Za-z])', low):
            return 'VAGUE', '"%s" stands where a measurable condition should be' % v.strip()

    if len(words) < C.MIN_WORDS:
        return 'TOO-SHORT', '%d words; a subject AND a condition needs at least %d' \
            % (len(words), C.MIN_WORDS)

    if not any(re.search(r'(?<![A-Za-z])' + re.escape(b) + r'(?![A-Za-z])', low)
               for b in C.BEHAVIOUR):
        return 'NO-CLAIM', 'names a thing but asserts no behaviour anyone could falsify'

    return 'PASS', ''


def run_fixtures():
    bad = []
    for text, want in C.FIXTURES:
        got, why = classify(text)
        if got != want:
            bad.append((text, want, got, why))
    return bad


def matrix_requirements():
    """(section, requirement text) for every row of the generated matrix.

    The requirement is the SECOND cell of a table row. Rows are found by their
    leading pipe and skipped when they are a header or a separator -- and the
    row is NOT split by index beyond taking cell 2, because a pipe inside a
    code span is content (docs/SAIRN-PROCESS-RULES.md section 2.1). Taking the
    second cell is safe; taking the fifth would not be.
    """
    out, section, col = [], '(none)', None
    if not os.path.exists(MATRIX):
        return out
    for line in io.open(MATRIX, encoding='utf-8'):
        if line.startswith('## '):
            section, col = line[3:].strip(), None
            continue
        if not line.startswith('|'):
            continue
        if set(line.strip()) <= set('|-: '):
            continue
        cells = line.split('|')
        if col is None:
            # THE REQUIREMENT COLUMN IS FOUND BY ITS HEADER, NEVER BY INDEX.
            # The first version took cell 2 everywhere and was reading the
            # WRONG COLUMN in two of the four sections -- `Tool` in section 3
            # and `Status` in section 4 -- because the four tables have
            # different layouts. It then reported 100% of section 3 as
            # TOO-SHORT, which was a true statement about tool FILENAMES.
            # That is docs/SAIRN-PROCESS-RULES.md section 2.1: a cell taken by
            # index across tables of different widths lands somewhere nobody
            # intended.
            for i, c in enumerate(cells):
                if _norm(c).lower().startswith('requirement'):
                    col = i
                    break
            if col is None:
                col = -1          # this table has no requirement column
            continue
        if col < 0 or len(cells) <= col:
            continue
        req = _norm(cells[col])
        if req:
            out.append((section, req))
    return out


def main(argv):
    bad = run_fixtures()
    only_fixtures = '--fixtures' in argv
    print('TESTABILITY GATE -- criteria %s, report only' % C.VERSION)
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. Nothing real was judged.')
        print('     The fixtures are hand-decided cases committed WITH the criteria.')
        print('     A failure here means the criteria were changed and no longer')
        print('     classify a case somebody already ruled on -- which is exactly how')
        print('     a gate gets quietly loosened to flatter the corpus it judges.')
        for text, want, got, why in bad:
            print('     expected %-14s got %-14s  %s' % (want, got, text[:60]))
        return 2
    print('  fixtures: %d/%d correct -- the criteria are locked and were not'
          % (len(C.FIXTURES), len(C.FIXTURES)))
    print('            tuned against the corpus below.')
    if only_fixtures:
        return 0

    reqs = matrix_requirements()
    if not reqs:
        print('  !! docs/traceability-matrix.md has no rows to read. NOT a pass.')
        return 2

    findings = []
    for section, req in reqs:
        verdict, why = classify(req)
        if verdict == 'PASS':
            continue
        if req in DECLARED:
            continue
        findings.append({'section': section, 'requirement': req,
                         'verdict': verdict, 'why': why})

    if '--json' in argv:
        print(json.dumps({'criteria_version': C.VERSION,
                          'requirements': len(reqs),
                          'declared': len(DECLARED),
                          'findings': findings}, indent=1))
        return 1 if findings else 0

    print('  requirements read : %d  (from %d sections of the generated matrix)'
          % (len(reqs), len(set(s for s, _ in reqs))))
    print('  declared untestable on purpose: %d' % len(DECLARED))
    print('  NOT TESTABLE AS WRITTEN: %d  (%.0f%% of the corpus)'
          % (len(findings), 100.0 * len(findings) / len(reqs) if reqs else 0))
    print('')
    print('  THE RATE IS THE CALIBRATION. A gate flagging most of a corpus that')
    print('  people have been working from is far more likely to be miscalibrated')
    print('  than to have found that most requirements are junk -- read the')
    print('  findings before believing the number.')
    for f in findings[:25]:
        print('')
        print('  %-14s %s' % (f['verdict'], f['requirement'][:96]))
        print('                 %s' % f['why'])
        print('                 in: %s' % f['section'][:70])
    if len(findings) > 25:
        print('\n  ... and %d more (use --json for all of them)' % (len(findings) - 25))
    return 1 if findings else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
