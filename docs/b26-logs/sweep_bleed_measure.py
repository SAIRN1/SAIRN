# docs/b26-logs/sweep_bleed_measure.py
# OWNER: cody   batch b26   2026-10-19
#
# THE CONCEPT: b24 measured its sweep's FILE-DERIVED class at 1-of-4 real and
#   named the cause -- WINDOW BLEED, an extraction sitting next to an
#   assertion getting classified as one -- so instead of reading 85 candidates
#   at 1-in-4 odds, every FILE-DERIVED hit is RE-CLASSIFIED mechanically by
#   whether the subject occurrence falls INSIDE the assertion call's own
#   balanced argument span, and the bleed fraction is MEASURED over the whole
#   population rather than estimated from one sample of four.
#
#   python docs/b26-logs/sweep_bleed_measure.py            # the measurement
#   python docs/b26-logs/sweep_bleed_measure.py --list      # per-hit detail
#   python docs/b26-logs/sweep_bleed_measure.py --file <p>  # one file
#
# Exit: 0 measured - 2 COULD NOT RUN
#
# ── READ THIS BEFORE TRUSTING ANY FIGURE BELOW ──────────────────────────────
# b24's caveat, quoted rather than paraphrased
# (docs/2026-10-19-cody-b24-sweep-continued.md):
#
#   "The residual cause is named: window bleed. The assertion window is a line
#    plus up to five continuation lines, so an extraction sitting next to an
#    assertion gets classified as one. 1 of 4 is better than b23's 6 of 16 and
#    it is not good."
#
# The four it read were cody's own, and ONE was real:
#   tests/sairncode_pt_gp_modifier.js:333   REAL -- ok(/id="pt-gp"/.test(html))
#   tests/sairnbuild_server_backup.js:112   false positive -- extraction
#   tests/stonedesk_pricing_backtest.js:61  false positive -- extraction
#   tests/sf_operator_payee_review_probe.js:41  false positive -- an anchor
#       UNIQUENESS guard, which is the STRONGER shape
#
# ── WHAT THIS TOOL ADDS, AND WHAT IT STILL CANNOT DO ───────────────────────
# IT ADDS: a mechanical IN-ASSERT / BLED split, so the work-list is the hits
# that are really inside a claim. That is strictly a PRECISION improvement on
# the classifier and it does NOT touch the candidate matcher -- b24's reason
# for leaving that matching stands: "narrowing clears the known instances and
# fails silently on the next phrasing, and in a detector a false negative is
# invisible where a false positive is loud and gets read."
#
# IT STILL CANNOT TELL a real hole from an assertion whose subject genuinely
# IS the file's prose -- a disclosure requirement, a licence header, a
# doc-comment rule. Several of those exist in this repo and are CORRECT. It
# also cannot see b24's fourth case, an anchor UNIQUENESS guard
# (`count(anchor) !== 1`), which is a STRONGER shape than the one being swept
# for and will land in IN-ASSERT. **SO IN-ASSERT IS A WORK-LIST AND NEVER A
# DEFECT COUNT**, and the sample read by hand below is what turns a work-list
# figure into a precision figure.
#
# ── AND THE CONTROL: IT MUST REPRODUCE b24's FOUR VERDICTS ─────────────────
# A reclassifier that cannot reproduce the four hand-read verdicts that
# motivated it is not measuring the thing it was built for. Those four are
# driven as FIXTURES against the real files, before any population figure is
# printed, and the run REFUSES if they do not come out right. This is the
# "lock the criteria against fixtures before running on real data" convention
# applied to a tool whose fixtures happen to be real files.

import io
import os
import re
import sys

SWEEP = 'docs/b23-logs/green_but_worthless_sweep.py'
if not os.path.isfile(SWEEP):
    print('COULD NOT RUN: ' + SWEEP + ' is not here, so this tool cannot '
          'reuse its matcher and would be inventing a second one. Nothing '
          'was measured.')
    sys.exit(2)

sys.path.insert(0, os.path.dirname(os.path.abspath(SWEEP)))
import importlib.util
spec = importlib.util.spec_from_file_location('gbw', SWEEP)
GBW = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(GBW)
except SystemExit:
    pass
except Exception as e:
    print('COULD NOT RUN: ' + SWEEP + ' would not import (' + str(e)
          + '). Nothing was measured.')
    sys.exit(2)

for need in ('ASSERT_MARK', 'SUBJECT_RE', 'classify_subject', 'STRIPS'):
    if not hasattr(GBW, need):
        print('COULD NOT RUN: ' + SWEEP + ' no longer exposes ' + need
              + ', so this tool would be using a matcher of its own. Nothing '
                'was measured.')
        sys.exit(2)

# ── THE ASSERTION's OWN ARGUMENT SPAN, BY BALANCED PARENTHESIS ─────────────
# This is the whole mechanism. `assert.ok(html.indexOf(x) >= 0);` has the
# subject INSIDE the span. A `const a = html.indexOf(startMark)` on the next
# line is OUTSIDE it -- and the five-line window could not tell, because a
# window is a guess about where the statement ends and a balanced paren is a
# property of the call.
CALL = re.compile(r'(?:assert(?:\.\w+)?|ok|bad|arm|expect|is)\s*\(')


def assert_spans(text):
    """[(start, end)] of every assertion call's balanced argument span."""
    out = []
    for m in CALL.finditer(text):
        # The call keyword must not be part of a longer identifier.
        if m.start() > 0 and re.match(r'[\w.$]', text[m.start() - 1]):
            continue
        i = text.index('(', m.start())
        d = 0
        for k in range(i, len(text)):
            c = text[k]
            if c == '(':
                d += 1
            elif c == ')':
                d -= 1
                if d == 0:
                    out.append((i, k + 1))
                    break
    return out


# ── AND A SECOND DISCRIMINATION, FOUND BY READING THE TOP CANDIDATE ────────
# ── 2026-10-19, cody b26 ───────────────────────────────────────────────────
# THE CONCEPT: an ABSENCE assertion over unstripped source text CANNOT be
#   satisfied by a comment -- a comment carrying the spelling makes it FAIL,
#   loudly -- so only PRESENCE assertions are candidates for this defect at
#   all, and folding the two together halves the signal.
#
# MEASURED, by reading the highest-count file in the work-list
# (tests/sairnvet_formulary_source_honesty.js): of its 8 distinct IN-ASSERT
# subject lines, FOUR are absence assertions --
#   :87   assert.ok(region.indexOf('Verified</span>') === -1, ...)
#   :118  assert.ok(!/verified (database|record)/i.test(prompt), ...)
#   :158  assert.ok(!/Verified calculation/.test(line), ...)
#   :168  assert.ok(src.indexOf(pair[1]) === -1, ...)
# -- and every one of them is in the SAFE DIRECTION. A comment in the app
# source containing "Verified</span>" cannot make :87 pass; it can only make
# it fail. These are not instances of the defect and never were.
#
# THE REMAINING FOUR ARE PRESENCE and ARE the work-list for that file:
#   :96  /d\.reference/.test(region)        :102 /No source recorded/.test(region)
#   :126 /unsourced|.../.test(prompt)       :149 /CITES NO PUBLISHED SOURCE/.test(near)
#
# UNSURE IS A THIRD STATE AND IS NOT FOLDED INTO EITHER. A test whose polarity
# this cannot read is exactly what a human has to resolve, and calling it
# PRESENCE would inflate the work-list while calling it ABSENCE would hide a
# real one.
NEG = (
    re.compile(r'!\s*/'),                      # !/re/.test(x)
    re.compile(r'!\s*[\w.$\[\]]*\b(?:indexOf|includes|match|test)\s*\('),
    re.compile(r'(?:indexOf|search)\s*\([^)]*\)\s*(?:===?\s*-\s*1|<\s*0)'),
    re.compile(r',\s*-\s*1\s*[,)]'),           # assert.strictEqual(..., -1)
    re.compile(r'\bdoesNotMatch\b'),
    re.compile(r'===?\s*false\b'),
)
POS = (
    re.compile(r'(?<![!\w])/.*?/\w*\s*\.\s*test\s*\('),
    re.compile(r'(?:indexOf|search)\s*\([^)]*\)\s*(?:>=?\s*0|!==?\s*-\s*1)'),
    re.compile(r'(?<![!\w])[\w.$\[\]]+\.includes\s*\('),
    re.compile(r'\bassert\.match\s*\('),
)


def polarity(span_text):
    """PRESENCE / ABSENCE / UNSURE for one assertion's own argument text."""
    neg = any(p.search(span_text) for p in NEG)
    pos = any(p.search(span_text) for p in POS)
    if neg and not pos:
        return 'ABSENCE'
    if pos and not neg:
        return 'PRESENCE'
    if neg and pos:
        return 'UNSURE'
    return 'UNSURE'


def hits_for(path):
    """[{line, subject, cls, in_assert, polarity, text}] for one test file."""
    try:
        src = io.open(path, encoding='utf-8', errors='replace').read()
    except Exception:
        return []
    src = src.replace('\r\n', '\n')
    spans = assert_spans(src)

    def enclosing(p):
        best = None
        for a, b in spans:
            if a <= p < b and (best is None or (b - a) < (best[1] - best[0])):
                best = (a, b)
        return best

    out = []
    for m in GBW.SUBJECT_RE.finditer(src):
        name = m.group(1) or m.group(2)
        if not name:
            continue
        cls = GBW.classify_subject(src, name)
        if cls != 'FILE-DERIVED':
            continue
        ln = src.count('\n', 0, m.start()) + 1
        line = src.split('\n')[ln - 1].strip()
        sp = enclosing(m.start())
        out.append({'line': ln, 'subject': name, 'cls': cls,
                    'in_assert': sp is not None,
                    'polarity': polarity(src[sp[0]:sp[1]]) if sp else '',
                    'text': line[:150]})
    return out


# ── THE CONTROL. b24's four hand-read verdicts, as fixtures. ───────────────
# expected: IN-ASSERT at the named line for the REAL one, and the three false
# positives must have NO in-assert hit on their named line.
# ── THE FIRST SPELLING OF THIS CONTROL WAS WRONG IN BOTH DIRECTIONS AND IT
#    REFUSED THE RUN, WHICH IS THE CONTROL WORKING. RECORDED, NOT ERASED. ───
# It encoded all four of b24's verdicts as bleed expectations, and only TWO of
# the four are about bleed at all:
#
#   * `sairncode_pt_gp_modifier.js:333` was expected IN-ASSERT because b24 read
#     it as REAL -- and b24 ALSO REPAIRED IT, in the same batch, in section
#     4.1. The file strips comments there now and line 333 is a comment. **A
#     FIXTURE ENCODING A DEFECT THAT WAS FIXED BY THE DOCUMENT IT WAS READ
#     FROM** -- discipline 8 (nothing announces the day a check stops testing
#     anything) landing on the control written to honour it, one batch later.
#
#   * `sf_operator_payee_review_probe.js:41` was expected NOT-in-assert because
#     b24 called it a false positive. It is
#     `assert.strictEqual(HTML.indexOf(startAnchor, i + 1), -1, ...)` -- an
#     anchor UNIQUENESS guard, INSIDE an assertion, and b24 called it a false
#     positive of the SWEEP on SEMANTIC grounds: the shape is STRONGER than the
#     one being swept for. **"False positive of the sweep" and "bled" are two
#     different things and the first spelling conflated them**, which is the
#     exact collapse the tool's own header warns about two paragraphs above.
#
# SO THE CONTROL NOW ENCODES ONLY WHAT THIS DISCRIMINATOR DECIDES -- bleed --
# and names the other two as non-subjects with their reasons, ANCHORED ON LINE
# CONTENT rather than on a line number, because a line number is the thing
# that rots and these four moved once already.
CONTROL = (
    ('tests/sairnbuild_server_backup.js', 112, False, 'indexOf',
     'b24: FALSE POSITIVE -- `const a = html.indexOf(startMark)`, an '
     'extraction pulled into the window next to an assertion. THIS IS BLEED '
     'and it is what the discriminator is for.'),
    ('tests/stonedesk_pricing_backtest.js', 61, False, 'indexOf',
     'b24: FALSE POSITIVE -- the same extraction shape. BLEED.'),
    ('tests/sf_operator_payee_review_probe.js', 41, True, 'indexOf',
     'b24: FALSE POSITIVE, but NOT by bleed -- an anchor UNIQUENESS guard '
     'genuinely inside an assertion. IN-ASSERT is the CORRECT answer here, '
     'and it is why IN-ASSERT is a work-list and not a defect count.'),
)
# NAMED AND NOT DRIVEN, so the next reader does not re-derive it:
#   tests/sairncode_pt_gp_modifier.js:333 -- b24's one REAL finding, REPAIRED
#   in b24 section 4.1. The file strips comments there now, so there is no
#   longer a FILE-DERIVED raw-source assertion at that line to classify. It is
#   excluded rather than expected, because an expectation on a repaired defect
#   fails for the right reason and reads as a broken tool.

print('SWEEP BLEED MEASUREMENT -- b26')
print('  matcher reused from ' + SWEEP + ' (SUBJECT_RE, classify_subject)')
print('  new discriminator   the subject occurrence must fall inside an '
      'assertion call\'s BALANCED PARENTHESIS span')
print('')
print('CONTROL -- b24\'s four hand-read verdicts, driven as fixtures against '
      'the real files')
wrong = []
for path, line, want_in, anchor, why in CONTROL:
    if not os.path.isfile(path):
        wrong.append(path + ' is not on disk, so the control could not run')
        print('  %-44s FILE GONE' % path[:44])
        continue
    hs = hits_for(path)
    # ANCHORED ON CONTENT AS WELL AS ON THE LINE. A fixture that finds nothing
    # at its line number is a THIRD STATE -- the subject moved -- and must not
    # read as agreement with want_in=False.
    on_line = [h for h in hs if h['line'] == line and anchor in h['text']]
    if not on_line:
        print('  %-44s:%-5d SUBJECT NOT FOUND AT THIS LINE -- the fixture has '
              'gone stale, which is NOT a pass' % (path[:44], line))
        wrong.append(path + ':' + str(line) + ' (subject moved)')
        continue
    got_in = any(h['in_assert'] for h in on_line)
    okk = (got_in == want_in)
    print('  %-44s:%-5d want in-assert=%-5s got=%-5s  %s'
          % (path[:44], line, want_in, got_in, 'ok' if okk else 'WRONG'))
    print('        ' + why)
    if not okk:
        for h in on_line:
            print('        line text: ' + h['text'])
        wrong.append(path + ':' + str(line))
if wrong:
    print('')
    print('REFUSED: the reclassifier does not reproduce b24\'s hand-read '
          'verdicts, so no population figure below would be trustworthy.')
    for w in wrong:
        print('  * ' + w)
    sys.exit(1)
print('  3/3 -- the reclassifier agrees with every hand-read verdict it is '
      'ENTITLED to decide, in BOTH directions: two BLED, one correctly '
      'IN-ASSERT.')

# ── THE POPULATION ─────────────────────────────────────────────────────────
if '--file' in sys.argv:
    files = [sys.argv[sys.argv.index('--file') + 1]]
else:
    files = []
    for root, dirs, names in os.walk('tests'):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git')]
        for n in sorted(names):
            if n.endswith('.js') or n.endswith('.py'):
                files.append(os.path.join(root, n).replace('\\', '/'))
    for d in ('api', 'api/_lib', 'api/_resources'):
        if os.path.isdir(d):
            for n in sorted(os.listdir(d)):
                if n.endswith('.test.js'):
                    files.append(d + '/' + n)

tot_in = tot_bled = 0
pol = {'PRESENCE': 0, 'ABSENCE': 0, 'UNSURE': 0}
rows = []
for f in files:
    hs = hits_for(f)
    if not hs:
        continue
    ia = [h for h in hs if h['in_assert']]
    bl = [h for h in hs if not h['in_assert']]
    # A file that strips comments somewhere is not a candidate of this sweep.
    try:
        src = io.open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    if GBW.STRIPS.search(src):
        continue
    tot_in += len(ia)
    tot_bled += len(bl)
    for h in ia:
        pol[h['polarity']] = pol.get(h['polarity'], 0) + 1
    if ia or bl:
        rows.append((f, len(ia), len(bl), ia,
                     len([h for h in ia if h['polarity'] == 'PRESENCE'])))

print('')
print('POPULATION -- FILE-DERIVED subject occurrences in files with NO '
      'comment stripping anywhere')
print('  files with at least one      ' + str(len(rows)))
print('  IN-ASSERT  (the work-list)   ' + str(tot_in))
print('  BLED       (extraction next to an assertion, NOT a claim)  '
      + str(tot_bled))
if tot_in + tot_bled:
    print('  bleed fraction               %.0f%% of FILE-DERIVED occurrences '
          'were never inside a claim' % (100.0 * tot_bled / (tot_in + tot_bled)))
print('')
print('  IN-ASSERT IS A WORK-LIST AND NEVER A DEFECT COUNT. An assertion '
      'whose\n  subject genuinely IS the file\'s prose -- a disclosure '
      'requirement, a\n  licence header, a doc-comment rule -- is CORRECT as '
      'written, and b24\'s\n  anchor-UNIQUENESS case is a STRONGER shape that '
      'lands here too.')
print('')
print('POLARITY of the ' + str(tot_in) + ' IN-ASSERT occurrences -- an '
      'ABSENCE assertion over')
print('unstripped source CANNOT be satisfied by a comment; a comment can only '
      'make it FAIL:')
for k in ('PRESENCE', 'ABSENCE', 'UNSURE'):
    print('  %-9s %4d%s' % (k, pol.get(k, 0),
                            '   <- the real work-list' if k == 'PRESENCE'
                            else ('   <- SAFE DIRECTION, not this defect'
                                  if k == 'ABSENCE'
                                  else '   <- THIS TOOL COULD NOT TELL, a '
                                       'human must read these')))
if tot_in + tot_bled:
    print('')
    print('  SO THE WORK-LIST IS %d of %d FILE-DERIVED occurrences -- %.0f%% '
          'of what the'
          % (pol.get('PRESENCE', 0), tot_in + tot_bled,
             100.0 * pol.get('PRESENCE', 0) / (tot_in + tot_bled)))
    print('  unsplit sweep reports. b24 measured its FILE-DERIVED class at '
          '1-of-4 real on a\n  sample of four and named window bleed as the '
          'cause; that is consistent with\n  this, measured over the whole '
          'population.')

print('')
print('  files with the most PRESENCE occurrences -- the routable work-list:')
for f, ni, nb, ia, npres in sorted(rows, key=lambda r: -r[4])[:25]:
    if npres == 0:
        continue
    print('    %-52s %3d presence  %3d absence/unsure  %3d bled'
          % (f[:52], npres, ni - npres, nb))
    if '--list' in sys.argv:
        for h in ia[:10]:
            print('          :%-6d %-9s %-8s %s'
                  % (h['line'], h['subject'], h['polarity'][:8],
                     h['text'][:84]))
sys.exit(0)
