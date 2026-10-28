#!/usr/bin/env python
"""The control for tools/assertion_label_shape_check.py -- BOTH directions.

    python tests/run_assertion_label_shape_probe.py

Exit 0 all arms pass, 1 any arm fails.

A checker that has never been seen to FIRE is a checker whose behaviour nobody
knows, and its clean line is then evidence for the wrong conclusion. So every
arm below is one half of a pair:

    plant the defect  -> it must REPORT   (exit 1, naming the file and line)
    plant clean code  -> it must STAY SILENT (exit 0)
    break the CRITERIA -> it must REFUSE  (exit 2, "nothing real was judged")

THE THIRD PAIR IS THE ONE THAT MATTERS MOST HERE, and it is why this file is
longer than the checker deserves on its own. This tool's entire claim rests on
a criteria lock that runs before any real file is read (discipline 1). A lock
that does not actually gate the run is decoration, so section A breaks a
criterion and asserts the tool refuses to judge -- INCLUDING on the ordinary
run, not only under `--fixtures`, because a lock that only guards its own flag
guards nothing.

── TWO STRUCTURALLY DIFFERENT DRIVING METHODS, ON PURPOSE (discipline 6) ────
Section A drives the module IN PROCESS and monkeypatches the criterion, so no
file on disk is mutated and there is no restore to get wrong -- this repo has
already had one probe restore another probe's mutation and report byte-identical
success. Sections B and C drive the real CLI through subprocess, so the
exit-code contract is exercised as a caller actually meets it. Two passes
through one mechanism would share its blind spot exactly.

── THE SABOTAGE IS VERIFIED TO HAVE APPLIED ────────────────────────────────
`sabotage_control_check.py` measures exactly this: 39 probes sabotage something
and 16 verify the sabotage took. A monkeypatch that silently fails leaves an
arm running the checker against an UNMODIFIED criterion and reporting green for
ever. So A2 asserts the patched pattern no longer matches a string the real one
did, BEFORE it asserts anything about the tool's behaviour.
"""
import io
import os
import subprocess
import sys
import tempfile
import contextlib
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'assertion_label_shape_check.py')
CONTROLS_FOR = ['assertion_label_shape_check.py']

import assertion_label_shape_check as A                            # noqa: E402

_pass, _fail = 0, 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


def section(t):
    print('\n' + t)


def run(*args):
    """(returncode, stdout+stderr) from the real CLI."""
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def tmpfile(body, suffix='.py'):
    fd, p = tempfile.mkstemp(prefix='als-', suffix=suffix)
    os.close(fd)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    return p


print('ASSERTION LABEL vs SHAPE -- the control for the checker')

# ── A. THE CRITERIA LOCK REALLY GATES THE RUN ───────────────────────────────
section('A. break a criterion and the tool must REFUSE, not report clean')
rc, out = run('--fixtures')
check('A1. the lock passes on the shipped criteria, and says how many fixtures',
      rc == 0 and re.search(r'criteria lock: (\d+)/\1 fixtures', out),
      (rc, out[-300:]))
_n_fixtures = len(A.FIXTURES) + len(A.TIER_FIXTURES)
check('A1b. ...and there is more than a token number of them, so A1 is not '
      'vacuous on an empty list',
      _n_fixtures >= 20, _n_fixtures)

_real_exhaustive = A.EXHAUSTIVE
_BROKEN = re.compile(r'(?!x)x')          # matches nothing at all
check('A2a. THE SABOTAGE APPLIES: the real pattern matches "every row" and the '
      'broken one does not -- asserted BEFORE the tool is driven, because a '
      'patch that silently failed would leave every arm below green for ever',
      bool(_real_exhaustive.search('every row')) and not _BROKEN.search('every row'),
      (bool(_real_exhaustive.search('every row')), bool(_BROKEN.search('every row'))))

_buf = io.StringIO()
try:
    A.EXHAUSTIVE = _BROKEN
    with contextlib.redirect_stdout(_buf):
        _rc_fx = A.main(['--fixtures'])
    _out_fx = _buf.getvalue()
    _buf2 = io.StringIO()
    with contextlib.redirect_stdout(_buf2):
        _rc_real = A.main([])
    _out_real = _buf2.getvalue()
finally:
    A.EXHAUSTIVE = _real_exhaustive

check('A2b. a broken criterion makes --fixtures exit 2 COULD NOT RUN, never 0',
      _rc_fx == A.EXIT_COULD_NOT_RUN, _rc_fx)
check('A2c. ...and it SAYS nothing real was judged, rather than printing a '
      'count a reader would take for a sweep',
      'NOTHING REAL WAS JUDGED' in _out_fx, _out_fx[-300:])
check('A3. THE LOCK GATES THE ORDINARY RUN TOO -- a bare run with a broken '
      'criterion is 2, not 0 and not 1. A lock that only guards its own flag '
      'guards nothing',
      _rc_real == A.EXIT_COULD_NOT_RUN, _rc_real)
check('A3b. ...and that run reported NO findings, so the 2 is a refusal and '
      'not a finding count that happens to be non-zero',
      'FINDINGS' not in _out_real, _out_real[-300:])
check('A4. the criterion was RESTORED -- otherwise every arm below is running '
      'against a sabotaged tool and this whole file means nothing',
      A.EXHAUSTIVE is _real_exhaustive
      and bool(A.EXHAUSTIVE.search('every row')),
      A.EXHAUSTIVE.pattern[:40])

# ── B. BOTH DIRECTIONS ON REAL FILES ────────────────────────────────────────
section('B. plant a defect, plant clean code')
_bad = tmpfile(
    "def check(name, cond, detail=''):\n"
    "    pass\n"
    "\n"
    "check('every promoted checker is scored', len(rows) > 20, 'd')\n")
rc, out = run('--paths', _bad)
check('B1. THE PLANTED DEFECT IS REPORTED -- exit 1',
      rc == 1, (rc, out[-400:]))
check('B1b. ...and the finding names the file AND the line, so it is actionable '
      'rather than a count',
      (os.path.basename(_bad) in out and ':4' in out), out[-400:])

_clean = tmpfile(
    "def check(name, cond, detail=''):\n"
    "    pass\n"
    "\n"
    "check('at least 12 sections yield requirements', len(reqs) >= 12, 'd')\n"
    "check('every row is present', len(rows) == 12, 'd')\n"
    "check('every table is in the queried set', set(a) <= set(b), 'd')\n"
    "check('every entry carries a reason', all(len(w) > 30 for w in ws), 'd')\n"
    "check('the ratio holds on every page', min(r.values()) >= 0.4, r)\n"
    "check('every section list is not empty', len(rows) > 0, 'd')\n")
rc, out = run('--paths', _clean)
check('B2. SIX CORRECT SHAPES ARE SILENT -- exit 0. This is the half a checker '
      'that always reports would fail',
      rc == 0, (rc, out[-500:]))
check('B2b. ...and it says CLEAN in words rather than just exiting 0',
      'CLEAN' in out, out[-300:])

_adv = tmpfile(
    "def check(name, cond, detail=''):\n"
    "    pass\n"
    "\n"
    "check('it does NOT report every one as unguarded', n > 2, 'd')\n")
rc, out = run('--paths', _adv)
check('B3. AN ADVISORY ROW IS NOT A FINDING -- exit 0, not 1',
      rc == 0, (rc, out[-400:]))
check('B3b. ...and the advisory is still PRINTED with its demotion reason, so '
      'the demotion is auditable rather than a silent drop',
      'ADVISORY (1)' in out and 'negated' in out, out[-500:])
check('B3c. ...and the two tier counts are printed separately with the words '
      'that forbid summing them',
      'not added' in out and '0 CONFIRMED, 1 ADVISORY' in out, out[-500:])

_broken_syntax = tmpfile("def check(  :\n    pass\n")
rc, out = run('--paths', _broken_syntax)
check('B4. A FILE THAT DOES NOT PARSE IS EXIT 2, NOT 0 -- a file it could not '
      'read is not a file with nothing in it (PR 1.11)',
      rc == A.EXIT_COULD_NOT_RUN, (rc, out[-400:]))
check('B4b. ...and it says COULD NOT RUN and names the file',
      'COULD NOT RUN' in out and os.path.basename(_broken_syntax) in out,
      out[-400:])

# ── C. THE REAL CORPUS, and the coverage statement ──────────────────────────
section('C. the real run says what it read and what it did not')
rc, out = run()
_m = re.search(r'read (\d+) Python and (\d+) JavaScript suite file', out)
check('C1. the bare run reads a NON-EMPTY file list IN BOTH LANGUAGES -- a zero '
      'in either would make that half of the verdict vacuous',
      bool(_m) and int(_m.group(1)) > 50 and int(_m.group(2)) > 50,
      _m.group(0) if _m else out[:300])
# ── C2 REWRITTEN 2026-09-29, AND THE OLD VERSION WAS RIGHT TO FAIL ──────────
# It asserted the JavaScript suites are declared NOT COVERED. They ARE covered
# now, so that arm was asserting a gap that had been closed -- the exact
# staleness this repo treats as a defect class of its own (discipline 8). What
# must still be true is the thing the old arm was protecting: a reader cannot
# mistake partial coverage for whole, so the output must still name WHAT IS NOT
# READ even when the file denominator reaches 100%.
check('C2. the output names what is STILL not read even at full file coverage, '
      'so a 100% denominator cannot be read as "everything is judged"',
      'STILL NOT READ' in out.upper() and 'COULD NOT RUN' in out
      and re.search(r'CHECKED / UNIVERSE: (\d+) of (\d+)', out) is not None,
      out[:900])
check('C2c. ...and BOTH languages are named in the coverage statement, so '
      'neither half can silently drop out of the denominator',
      'Python' in out and 'JAVASCRIPT' in out.upper(), out[:900])
# ── THE DENOMINATOR IS ASSERTED, NOT JUST ITS PRESENCE ─────────────────────
# "It prints a coverage line" is satisfied by a line that prints 0 of 0. The two
# numbers are read back and compared, so a denominator that collapses -- a git
# call that failed and returned nothing, the commonest way a coverage figure goes
# vacuous -- is a RED arm rather than a clean 100%.
_cu = re.search(r'CHECKED / UNIVERSE: (\d+) of (\d+)', out)
# EXPECTATION CHANGED 2026-09-29, from `universe > checked` to `checked <=
# universe`. The old arm encoded the capability gap as a REQUIREMENT -- it would
# have gone red the day the gap closed, which it did. The property worth holding
# is that the two figures are REAL and CONSISTENT: a collapsed denominator
# (0 of 0) and a checked count exceeding its own universe are both still caught.
check('C2b. ...and the two figures are REAL and consistent: checked > 0 and '
      'checked <= universe, so neither a collapsed denominator nor a count '
      'exceeding its own universe can pass',
      _cu is not None and int(_cu.group(1)) > 0
      and int(_cu.group(1)) <= int(_cu.group(2)),
      _cu.group(0) if _cu else 'no CHECKED / UNIVERSE line at all')
check('C3. both tier counts appear on the real run too',
      re.search(r'TIERS: \d+ CONFIRMED, \d+ ADVISORY', out) is not None,
      out[:800])
check('C4. exit is 0, 1 or 2 and nothing else',
      rc in (0, 1, 2), rc)

# ── C5. THE KNOWN-BAD JAVASCRIPT CONTROL, BOTH DIRECTIONS ──────────────────
# Added 2026-09-29 with the JavaScript extension. Section B's known-bad/known-good
# pair only ever exercised the `ast` path, so every arm above could have passed
# with the JS extractor returning nothing at all. Numbered C5 because C4 (exit
# code) already exists above; renumbering it would break nothing here and would
# silently break anyone quoting an arm name.
#
# THE SILENT HALF IS NOT OPTIONAL. "The planted bug is reported" is satisfied by
# a checker that reports every JS arm it sees; C5b is what makes C5 mean
# something, and C5c is the commented-out case that checker_control_check had to
# rebuild itself around in Python -- checked here in JavaScript.
_bad_js = tmpfile("assert.ok(rows.length >= 3, 'every row is present');\n",
                  suffix='.js')
rc_kb, out_kb = run('--paths', _bad_js)
check('C5. KNOWN-BAD: a JS arm labelling a universal behind a one-sided floor '
      'IS REPORTED, and the finding names the planted file',
      rc_kb == 1 and os.path.basename(_bad_js) in out_kb,
      (rc_kb, out_kb[-400:]))
_good_js = tmpfile("assert.ok(rows.length === 3, 'every row is present');\n",
                   suffix='.js')
rc_kg, out_kg = run('--paths', _good_js)
check('C5b. ...and THE SILENT HALF: the same label with an EXACT comparison is '
      'NOT reported, so C5 is not satisfied by a checker that flags every JS arm',
      rc_kg == 0, (rc_kg, out_kg[-400:]))
_cmt_js = tmpfile("// assert.ok(rows.length >= 3, 'every row is present');\n",
                  suffix='.js')
rc_kc, out_kc = run('--paths', _cmt_js)
check('C5c. ...and a COMMENTED-OUT arm is not reported -- the comment-stripping '
      'half of the JS scan is load-bearing and is checked, not assumed',
      rc_kc == 0, (rc_kc, out_kc[-400:]))
for _p in (_bad_js, _good_js, _cmt_js):
    try:
        os.unlink(_p)
    except OSError:
        pass

# ── F. THE COUNTS THAT COULD ONLY EVER SAY ZERO OR 100% (b55 M4-M6) ─────────
section('F. the limit count, the coverage figure and NOT JUDGED are measured')
# M4: strip_comments(src, rel) put `rel` in `strings=`, blanking the label the
# exhaustive test reads, so "OF WHICH N carry an exhaustive label" was always 0.
# SOURCE CHANGED 2026-10-28 from `assert.ok(` to the local `ok(` helper:
# assert.ok on a plain value is JUDGED now and correctly leaves the limit, so
# the still-unjudged shape carries this arm. F1b holds the judged half.
_bare_js = tmpfile("ok(rows, 'every row is present');\n", suffix='.js')
_rcF, _outF = run('--paths', _bare_js)
check('F1. a JS bare truthiness under an EXHAUSTIVE label is counted in the '
      'registered-limit figure -- "OF WHICH 1", not a structural 0',
      re.search(r'bare-truthiness\s+call\(s\).*?OF WHICH 1\b', _outF, re.S)
      is not None, _outF[:1400])
_bare_ok_js = tmpfile("assert.ok(rows, 'every row is present');\n",
                      suffix='.js')
_rcF1b, _outF1b = run('--paths', _bare_ok_js)
# EXPECTATION CHANGED 2026-10-28 (same day): exit 1 -> exit 0 with an ADVISORY
# row. The rule measured 0 true of 4 CONFIRMED on the real tree and is capped
# at ADVISORY until a true positive is measured (JS_BARE_CAP_WHY in the tool).
check('F1b. ...and assert.ok(value, LABEL) IS JUDGED end to end: the real CLI '
      'prints it as a capped ADVISORY BARE TRUTHINESS row naming the file, '
      'exits 0 because the cap keeps it out of CONFIRMED, and its limit figure '
      'is 0, so it sits in exactly one bucket',
      _rcF1b == 0 and os.path.basename(_bare_ok_js) in _outF1b
      and 'ADVISORY (1)' in _outF1b and 'BARE TRUTHINESS' in _outF1b
      and re.search(r'OF WHICH 0\b', _outF1b) is not None,
      (_rcF1b, _outF1b[-600:]))
_real_bu = A.js_bare_unjudged
def _boom(_s):
    raise RuntimeError('planted')
try:
    A.js_bare_unjudged = _boom
    _res = A.scan([], js_paths=[_bare_js])
finally:
    A.js_bare_unjudged = _real_bu
check('F2. a CRASH in the limit count is COULD NOT RUN (unparsed), never a '
      '(0, 0) that reads as "the limit costs nothing"',
      any('planted' in u for u in _res[4]), _res[4])
# M5: printed `_checked of _checked` -- 100% whatever was unparsed.
_ok_py = tmpfile("check('at least one row', len(rows) >= 1, 'd')\n")
_bad_py = tmpfile("def check(  :\n    pass\n")
_rcF, _outF = run('--paths', _ok_py, _bad_py)
check('F3. one file read and one that does not parse -> CHECKED / UNIVERSE is '
      '1 of 2, not 2 of 2 (100%)',
      re.search(r'CHECKED / UNIVERSE: 1 of 2\b', _outF) is not None
      and _rcF == A.EXIT_COULD_NOT_RUN,
      (_rcF, re.findall(r'CHECKED / UNIVERSE: [^\n]*', _outF)))
# M6: CLEAN_NO_COMPARE is unreachable, so NOT JUDGED always printed 0 while the
# arms that really go unjudged were `continue`d and counted nowhere.
_nj = tmpfile("check('every row is present', got, want)\n"
              "print('every row', n)\n")
_rcF, _outF = run('--paths', _nj)
check('F4. a Python callee-compares arm `check(LABEL, got, want)` counts as 1 '
      'NOT JUDGED -- and a non-assertion `print(...)` is not counted',
      re.search(r'0 arm\(s\) judged, 1 NOT JUDGED', _outF) is not None,
      re.findall(r'read [^\n]*', _outF))
_nj_js = tmpfile("assert.strictEqual(a, b, 'every row is present');\n",
                 suffix='.js')
_rcF, _outF = run('--paths', _nj_js)
check('F5. the JS callee-compares form `assert.strictEqual(a, b, LABEL)` counts '
      'as 1 NOT JUDGED', re.search(r'0 arm\(s\) judged, 1 NOT JUDGED', _outF)
      is not None, re.findall(r'read [^\n]*', _outF))
for _p in (_bare_js, _bare_ok_js, _ok_py, _bad_py, _nj, _nj_js):
    try:
        os.unlink(_p)
    except OSError:
        pass

# ── E. THE 2026-09-29 RULES, AND THE REGEX THAT COULD NEVER MATCH ──────────
# The fourteen NOT-JUDGED arms were read one at a time. Every one was decidable,
# so the bucket is gone rather than explained -- but the rule that removed it
# shipped, in its first version, with a LITERAL BACKSPACE in its pattern:
#
#     'fixture invalid\x08|could not\x08|...'
#
# written through a shell heredoc that turned every `\b` into chr(8). It matched
# nothing, ever, and it READ AS A WORKING RULE: the tool ran, the NOT-JUDGED
# count went to zero by the other branch, and the demotion the rule existed for
# silently did not happen. This repo's own skill notes name that exact failure
# and it has now happened here. E1 is the arm that would have caught it in one
# second, because a regex cannot report that it is unreachable.
section('E. the 2026-09-29 rules')

check('E1. NO CONTROL CHARACTER IN ANY CRITERIA PATTERN. The first '
      'FAILURE_DESCRIPTION shipped with chr(8) where every `\\b` should have '
      'been -- it matched nothing, for ever, and the tool looked fine doing it',
      all(not any(ord(c) < 32 for c in getattr(A, n).pattern)
          for n in ('FAILURE_DESCRIPTION', 'EXHAUSTIVE', 'ONE_SIDED_DECLARED',
                    'JS_BARE_CALL')),
      [(n, [hex(ord(c)) for c in getattr(A, n).pattern if ord(c) < 32])
       for n in ('FAILURE_DESCRIPTION', 'EXHAUSTIVE', 'ONE_SIDED_DECLARED',
                 'JS_BARE_CALL')])

check('E2. A BARE TRUTHINESS UNDER A UNIVERSAL LABEL IS A FINDING. It is a '
      'WORSE instance than the floor this tool was built for -- ONE row '
      'satisfies "every row is present" -- and v1 counted it NOT JUDGED',
      A.classify('every row is present', []) == A.FINDING_BARE,
      A.classify('every row is present', []))

check('E2b. ...AND THE SILENT HALF: the same bare truthiness under an HONEST '
      'label is clean, or the rule is just "has no operator"',
      A.classify('at least one row is present', []) == A.CLEAN_NO_EXHAUSTIVE,
      A.classify('at least one row is present', []))

check('E3. A FAILURE DESCRIPTION IS NOT A CLAIM -- it names the state that '
      'would be WRONG. Two of the fourteen carried `every` inside one and '
      'tier() called them CONFIRMED',
      A.classify('fixture invalid: every listed name appears more than once',
                 []) == A.CLEAN_FAILURE_DESC,
      A.classify('fixture invalid: every listed name appears more than once', []))

check('E3b. ...AND THAT RULE IS SCOPED TO THE NO-OPERATOR BRANCH. Applied to '
      'every arm it demoted SEVENTY-FOUR, several of them real claims, which '
      'makes this checker WEAKER -- the one direction a criteria change must '
      'never go. With an operator present the same label is still a FINDING',
      A.classify('fixture invalid: every row must be present',
                 [__import__('ast').GtE()]) == A.FINDING,
      A.classify('fixture invalid: every row must be present',
                 [__import__('ast').GtE()]))

# E4 REWRITTEN b55 (M6). It asserted the real run's NOT JUDGED figure is 0, and
# it was green only because that figure was STRUCTURALLY 0: CLEAN_NO_COMPARE is
# unreachable and the arms that really go unjudged (the callee-compares form
# `check(LABEL, got, want)` / `assert.strictEqual(a, b, LABEL)`) were dropped
# uncounted. The 14 bare-truthiness arms the old arm protected are JUDGED now
# (FINDING_BARE), which E3/the fixture lock hold. What must be true is that the
# figure is a MEASUREMENT: the corpus carries the callee-compares form, so a 0
# here is the dead counter coming back.
check('E4. THE REAL RUN COUNTS ITS NOT JUDGED ARMS -- a non-zero measured '
      'figure, because a 0 here is the counter that could never move',
      re.search(r'(\d+) NOT JUDGED', out) is not None
      and int(re.search(r'(\d+) NOT JUDGED', out).group(1)) > 0,
      re.search(r'(\d+) NOT JUDGED', out).group(0)
      if re.search(r'(\d+) NOT JUDGED', out) else out[:300])

check('E5. THE ONE REGISTERED LIMIT IS PRINTED WITH BOTH ITS FIGURES, and the '
      'second one is what decides whether it is a limit or a gap. A limit '
      'stated only in a comment goes stale the day it stops being true',
      'ONE REGISTERED LIMIT' in out
      and re.search(r'(\d+) JavaScript bare-truthiness', out) is not None
      and re.search(r'OF WHICH (\d+)', out) is not None,
      out[:1400])
_ex = re.search(r'OF WHICH (\d+)', out)
# E5b SAID "== 0" AND WAS GREEN ONLY BECAUSE OF M4 (cody b58). The count was
# structurally 0 -- `strip_comments(src, rel)` blanked every string body -- so
# the limit looked free. Fixed, it measured 35, pinned here as the ceiling.
#
# 2026-10-28: the JS extractor now JUDGES assert.ok(<plain value>, LABEL), the
# mirror of Python's `assert x, 'label'`, and that shape left the count: 35 ->
# 27. NOT 0 -- what remains is unjudged ON PURPOSE, measured by callee:
#   15  assert.strictEqual / notStrictEqual(x, 'none') -- the literal is the
#       EXPECTED VALUE, not a label; JS_BARE_CALL's `assert.<name>` alternative
#       over-counts them. Callee-compares form, which Python does not judge.
#    6  local ok(...) helpers -- per-file signatures, so the call site cannot
#       say the callee tests truthiness; Python's check(label, x) is likewise
#       NOT JUDGED.
#    6  assert.ok PREDICATES (`!r.rejected`, `a && a.opts`) -- a predicate is
#       not a population being present; judging that shape gave 28 of 28 false
#       positives on the first real run, so it is left out by design.
E5B_CEILING = 27
check('E5b. ...and the measured cost of the limit has not grown past %d '
      '(2026-10-28; 35 in b58). If this goes red, more exhaustive labels sit on '
      'a shape the JS extractor does not judge -- read them rather than raise '
      'this number' % E5B_CEILING,
      _ex is not None and int(_ex.group(1)) <= E5B_CEILING,
      _ex.group(0) if _ex else 'no registered-limit line at all')

# ── D. ANCHOR ARMS -- what tells us the day this control stops testing ──────
section('D. the anchors this control depends on (discipline 8)')
_src = io.open(TOOL, encoding='utf-8').read()
check('D1. the tool still accepts --paths, which every arm in section B uses. '
      'If this goes red, sections B and C are running against a default file '
      'list and are no longer controls',
      "'--paths'" in _src, 'the flag is gone')
check('D2. CRITERIA_VERSION is present and non-empty, so a criteria change is '
      'visible in the output rather than silent',
      bool(str(getattr(A, 'CRITERIA_VERSION', '')).strip())
      and A.CRITERIA_VERSION in out, getattr(A, 'CRITERIA_VERSION', None))
check('D3. the tool declares this file as its control, so checker_control_check '
      'can find the pair from either end',
      'run_assertion_label_shape_probe.py' in _src, 'CONTROLLED_BY is stale')

for _p in (_bad, _clean, _adv, _broken_syntax):
    try:
        os.unlink(_p)
    except OSError:
        pass

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
