#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""unproven_arm_check.py -- a suite must not exit 0 while an arm is UNPROVEN.

SPEC: docs/2026-10-13-cody-b6-routed-to-cc.md section 2, written in b6 which
deliberately built nothing. THE DEFECT IT EXISTS FOR, measured not imagined:
in b5 two of my own probes exited 0 while an arm had not been evaluated at all.
The disclosure was a print(). The exit code -- the only thing a runner, a hook
or a session summary actually reads -- did not carry it. The gap between those
two readings was one print() wide.

THREE SIGNALS, and the discriminator is the SUMMARY/EXIT CONSTRUCT rather than
the word, because the false-positive shape was named in advance: a file that
merely MENTIONS unproven in prose must not trip this, and the spec document's
own filename appears in any grep for the word.

  A1  the word without the count -- an unproven verdict is emitted but the
      summary print does not carry an unproven number. The exact b5 defect.
  A2  an exit reachable with an unproven arm recorded -- the exit expression
      names the failure counter and no unproven counter, so unproven arms
      cannot change the exit code.
  A3  the inverse, and the one that keeps A1 honest -- the summary prints an
      unproven count the file never sets. A state it cannot reach.

WHAT IS NOT CHECKED, said here rather than discovered later. The third
sub-rule -- "an arm may be unproven at most once; twice is a FAILURE" -- is a
property of two consecutive RUNS and is invisible to a static reader of source.
It is NOT implemented and NOT reported as clean. A4 is listed as NOT-CHECKED in
every run's output so the three signals cannot be quoted as the whole rule.

REPORT-ONLY, and that is a decision held in writing rather than an accident:
exit 1 on a finding, and NOT wired into the push gate. A checker promoted to
blocking while real findings exist refuses every push to the affected file, and
that is how a gate gets switched off -- the same decision dup_dom_ids_check.py
and sairn_reachability_check.py both carry. Promote it when the tree is clean.
A checker may be deliberately non-blocking; it may not be deliberately
inaccurate, so the exit code here is accurate about its own run.

FAILS CLOSED: exit 2 COULD NOT RUN when the scan finds no files at all, because
"0 findings over 0 files" is indistinguishable from a clean tree and this repo
refuses that fold everywhere else.

  exit 0  scanned, no finding
  exit 1  at least one finding (REPORT-ONLY -- not a gate)
  exit 2  COULD NOT RUN -- nothing was compared
"""

import os
import re
import sys

CRITERIA_VERSION = '2026-10-13.1'

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# NORMALISATION. This is the part that decides every false positive, so it is
# one named function and the probe locks it against fixtures in both
# directions.
#
# Comments go, and so do TRIPLE-QUOTED strings (python) and TEMPLATE LITERALS
# (js). A fixture body embedded in a triple-quoted string is not code in the
# file that holds it -- it is data describing some other file -- and a checker
# whose universe includes the text that DESCRIBES its subject is a shape this
# repo has paid for three times. Removing them is what lets this tool's own
# probe carry fixture source without tripping the tool.
# ---------------------------------------------------------------------------

_PY_TRIPLE = re.compile(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'')
_JS_TEMPLATE = re.compile(r'`[^`]*`')
_JS_BLOCK = re.compile(r'/\*[\s\S]*?\*/')


def _hash_outside_literal(line):
    """Index of the first '#' that is NOT inside a string literal, or -1."""
    i = 0
    quote = None
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == '\\':
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in '\'"':
            quote = ch
        elif ch == '#':
            return i
        i += 1
    return -1


def normalise(src, lang):
    """Return (normalised_source, line_count_preserved_text).

    Newlines inside a removed region are preserved so reported line numbers
    stay true to the real file. A checker that reports a line number it has
    shifted is worse than one that reports none.
    """
    def blank(m):
        return re.sub(r'[^\n]', ' ', m.group(0))

    if lang == 'py':
        src = _PY_TRIPLE.sub(blank, src)
        out = []
        for line in src.split('\n'):
            # LITERAL-AWARE, and the crude version was not adequate -- measured,
            # not assumed. It cut at the first '#' wherever it fell, so a line
            # holding a fixture string that CONTAINS a comment --
            #     "# an arm that cannot run is reported UNPROVEN\n"
            # -- was truncated mid-literal, leaving an unterminated quote that
            # shifted every literal boundary after it on the joined statement
            # and exposed an exit expression that was really fixture data. One
            # phantom A2 finding, in the probe for this tool, from the one
            # shortcut this function admitted to taking.
            i = _hash_outside_literal(line)
            out.append(line if i < 0 else line[:i])
        return '\n'.join(out)

    src = _JS_TEMPLATE.sub(blank, src)
    src = _JS_BLOCK.sub(blank, src)
    out = []
    for line in src.split('\n'):
        i = line.find('//')
        if i >= 0 and '://' not in line[max(0, i - 1):i + 3]:
            line = line[:i]
        out.append(line)
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# THE CONSTRUCTS
# ---------------------------------------------------------------------------

# An identifier whose NAME says unproven. Case-insensitive because this repo
# writes the verdict in capitals and the counter in lower case.
#
# THE PREFIX IS OPTIONAL AND THAT IS NOT COSMETIC. The first version required
# at least one character before the token -- `[A-Za-z_][A-Za-z_0-9]*unproven`
# -- so it matched `n_unproven` and `self.unproven` and MISSED the bare name
# `unproven`, which is what anybody actually writes. The A2 control fixture
# caught it: A2 stayed silent on a file that plainly sets a counter, and A3
# fired instead, so the tool reported the OPPOSITE signal. A passing-looking
# scan over the real tree would never have shown it.
_UNPROVEN_ID = re.compile(
    r'(?<![A-Za-z_0-9])[A-Za-z_0-9]*unproven[A-Za-z_0-9]*', re.I)

# A counted unproven state: assigned, incremented, appended or pushed.
_UNPROVEN_SET = re.compile(
    r'(?<![A-Za-z_0-9])([A-Za-z_0-9]*unproven[A-Za-z_0-9]*)\s*'
    r'(?:=[^=]|\+=|-=|\.append\(|\.push\(|\.add\()', re.I)

# A print/log call at all. Matching is done LINE BY LINE and every pattern
# below is anchorless and backtrack-free on purpose: the first version of this
# tool used one regex per construct with nested lazy quantifiers and HUNG --
# not failed, hung -- on the long lines real test files carry. A checker that
# does not terminate reports nothing, which is the same outcome as a checker
# that reports a false clean, and it is the line-based idiom this repo already
# uses elsewhere for exactly this reason.
_EMITTER = re.compile(r'\b(?:print|console\.(?:log|warn|error))\s*\(')
_PASSWORD = re.compile(r'pass(?:ed)?\b', re.I)
_FAILWORD = re.compile(r'fail(?:ed|ure|s)?\b', re.I)

# String literals on a single line, either quote style, escapes honoured.
_LITERAL = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")
# A lowercase prose word. Three letters, because "an" and "of" are not enough
# to tell prose from a label and the repo writes verdict labels in capitals.
_PROSE_WORD = re.compile(r'[a-z]{3,}')


def verdict_emission(line):
    """True when this print/log emits UNPROVEN as an ARM VERDICT, not prose.

    THIS IS THE WHOLE FALSE-POSITIVE DEFENCE and it was written against a REAL
    miss, not an imagined one. tests/push_gate/check4_probe.py:526 contains

        print('directly rather than reported UNPROVEN. The foreign refusal:')

    which is a sentence ABOUT the b5 defect inside the probe that FIXED it. The
    first version of this tool counted it as a mechanism, which is this repo's
    own recurring shape -- a checker whose universe includes the text that
    DESCRIBES its subject -- and it is also the specific false positive the
    spec named in advance.

    The discriminator: inside the string literal, look at what precedes the
    token. A verdict label has nothing before it but padding, punctuation,
    digits or capitals ('UNPROVEN  arm 1', '(2 ARMS UNPROVEN -- see above)').
    Prose has a lowercase word before it ('reported UNPROVEN.'). Locked against
    fixtures in both directions by tests/run_unproven_arm_probe.py.
    """
    for lit in _LITERAL.finditer(line):
        text = lit.group(0)[1:-1]
        at = text.find('UNPROVEN')
        while at >= 0:
            if not _PROSE_WORD.search(text[:at]):
                return True
            at = text.find('UNPROVEN', at + 1)
    return False

# An exit construct and its expression.
_EXIT = re.compile(r'(?:sys\.exit|process\.exit|os\._exit)\s*\(([^\n]*)\)')

# A failure counter named in an exit expression. OPTIONAL PREFIX, for the
# identical reason _UNPROVEN_ID carries one: the first version required a
# character before the token and so matched `n_fail` while MISSING the bare
# `failed`, which is what every suite in this repo actually writes. Same
# one-character defect, found by the same A2 control fixture, in two regexes.
_FAIL_ID = re.compile(
    r'(?<![A-Za-z_0-9])[A-Za-z_0-9]*fail[A-Za-z_0-9]*', re.I)

# AN OUTCOME FLAG, which is the other way this repo spells the same thing and
# the reason A2 caught only ONE of the two real instances at first. The b5
# tests/push_gate/check4_probe.py ends
#
#     sys.exit(0 if ok else 1)
#
# -- no failure COUNTER anywhere, a boolean `ok` instead -- so the fail-counter
# form of A2 could not see it. MEASURED: 1 of 2 before this list existed, 2 of
# 2 after (tools/unproven_arm_check.py --root over check4_probe.py and
# check7_probe.py as they stood at c465743b~1).
#
# THE LIST IS A CLOSED SET OF WHOLE IDENTIFIERS, not a substring match, and
# that is the whole reason it is safe to widen here. The tempting version --
# "any identifier at all" -- fires on `sys.exit(main())`, which is a CORRECT
# shape that delegates the whole verdict including the unproven count to a
# function. A false positive on the correct shape is how a checker gets
# switched off, so the widening stops at names that mean "did it go well".
_OUTCOME_ID = re.compile(
    r'(?<![A-Za-z_0-9])'
    r'(?:[A-Za-z_0-9]*fail[A-Za-z_0-9]*|[A-Za-z_0-9]*error[A-Za-z_0-9]*'
    r'|ok|all_ok|allOk|is_ok|isOk|any_bad|bad|clean|is_clean|green)'
    r'(?![A-Za-z_0-9])', re.I)


def _lines(norm):
    """LOGICAL lines, not physical ones, with the first physical line number.

    WHY, and it was measured by a control fixture rather than foreseen: a
    summary print is very often written across two physical lines --

        console.log(pass + ' passed, ' + fail + ' failed, '
                    + unproven + ' unproven');

    -- and a physical-line reader sees the pass/fail words on line 1 and the
    unproven count on line 2, concludes the summary does not carry the count,
    and reports A1 against a file that does everything right. That is a FALSE
    POSITIVE on the CORRECT shape, which is the precise way a checker gets
    switched off. The same applies to a multi-line exit expression.

    Joining is by PAREN BALANCE, counted outside single-line string literals so
    a '(' inside a message does not hold the join open forever.
    """
    phys = norm.split('\n')
    out = []
    i = 0
    while i < len(phys):
        start = i
        text = phys[i]
        depth = _balance(text)
        while depth > 0 and i + 1 < len(phys):
            i += 1
            text += ' ' + phys[i]
            depth += _balance(phys[i])
        out.append((start + 1, text))
        i += 1
    return out


def _balance(line):
    bare = _LITERAL.sub("''", line)
    return bare.count('(') - bare.count(')')


def code_only(text):
    """Blank the INSIDE of every single-line string literal, keeping length.

    A CONSTRUCT INSIDE A STRING LITERAL IS DATA ABOUT CODE, NOT CODE, and this
    tool needed the distinction the moment its own probe existed. The probe
    holds fixture source in ordinary double-quoted literals --

        "passed = 1\\nfailed = 0\\nimport sys\\nsys.exit(1 if failed else 0)\\n"

    -- and the first version read those as seven real exit constructs and
    reported seven A2 findings against the file that proves A2 works. That is
    this repo's own named shape (a checker whose universe includes the text
    describing its subject) and my own recorded one (my comments trip my own
    scanners), arriving together.

    So the two families of construct are read off different texts, which is
    the actual distinction rather than a patch:
      CODE-LEVEL   -- setters and exits -- read from code_only()
      MESSAGE-LEVEL -- the summary print and the UNPROVEN verdict -- read from
                      the normalised source, because they live in literals BY
                      DEFINITION and blanking them would delete the signal.
    """
    def blank(m):
        body = m.group(0)
        return body[0] + (' ' * (len(body) - 2)) + body[-1]
    return _LITERAL.sub(blank, text)


def analyse(path, src):
    """Return a list of (signal, line, detail). Pure function of the source."""
    lang = 'py' if path.endswith('.py') else 'js'
    norm = normalise(src, lang)
    lines = _lines(norm)

    summaries = []   # (lineno, text) -- a print carrying a pass AND a fail word
    emits = []       # (lineno, text) -- a print carrying the UNPROVEN verdict
    for n, text in lines:
        if not _EMITTER.search(text):
            continue
        if _PASSWORD.search(text) and _FAILWORD.search(text):
            summaries.append((n, text))
        if 'UNPROVEN' in text and verdict_emission(text):
            emits.append((n, text))

    bare = code_only(norm)
    setters = [(bare.count('\n', 0, m.start()) + 1, m.group(1))
               for m in _UNPROVEN_SET.finditer(bare)]
    # Exits read off the LOGICAL lines too, for the same reason: an exit
    # expression split across lines would otherwise be truncated at the
    # newline and judged on half of itself.
    exits = []
    for n, text in lines:
        for m in _EXIT.finditer(code_only(text)):
            exits.append((n, m.group(1)))

    # The mechanism test. A file is IN SCOPE only if it both reports a
    # pass/fail summary AND has an unproven mechanism -- a counter it sets, or
    # a verdict it prints. Prose alone is not a mechanism, which is the whole
    # point of normalise().
    in_scope = bool(summaries) and bool(emits or setters)

    summary_carries = any(re.search(r'unproven', text, re.I)
                          for _, text in summaries)

    findings = []

    if in_scope and not summary_carries:
        where = (emits[0] if emits else setters[0])[0]
        findings.append((
            'A1', where,
            'an unproven verdict is emitted or counted, but no summary print '
            'carries an unproven number. A reader of "N passed, 0 failed" '
            'cannot tell an unproven arm from a passing one, and the exit code '
            'certainly cannot.'))

    # ── A2 DOES NOT REQUIRE A SUMMARY, AND THAT WAS FORCED BY ABLATION RATHER
    # THAN BY REASONING. The only two real instances this defect has ever had
    # are the pre-fix b5 versions of tests/push_gate/check4_probe.py and
    # check7_probe.py; both are recoverable at c465743b~1, so the ablation is a
    # real measurement over real code and not a fixture.
    #
    # NEITHER of those two probes has a "N passed, M failed" summary line. So
    # while A2 was gated on `in_scope` -- which requires one -- A2 could not
    # fire on either, and the run reported both as NOT ASSESSED. Quarantining
    # is the correct failure direction and is why the clean verdict was never
    # wrong, but quarantine is not detection. A2's premise never needed a
    # summary: an unproven mechanism plus an exit expression that cannot see it
    # is the whole defect. Gated on the mechanism alone it fires.
    #
    # THE MEASURED NUMBERS, each re-derived here rather than carried over:
    #
    #   gated on in_scope          0 of 2   (quarantined, not caught)
    #   gated on the mechanism,    1 of 2   check7_probe.py only -- check4's
    #     fail-counter form only            exit is `sys.exit(0 if ok else 1)`
    #                                       and names no failure COUNTER
    #   plus the outcome-flag set  2 of 2   see _OUTCOME_ID above
    #
    # The middle row is the one worth keeping: a widening that catches half the
    # instances reads exactly like one that catches all of them unless somebody
    # runs the ablation per ARM instead of per exit code.
    if emits or setters:
        for lineno, expr in exits:
            if not expr.strip():
                continue
            if re.search(r'unproven', expr, re.I):
                continue
            if _OUTCOME_ID.search(expr):
                findings.append((
                    'A2', lineno,
                    'the exit expression `%s` names a failure counter or an '
                    'outcome flag and no unproven counter, so this suite exits '
                    '0 with unproven arms recorded.' % expr.strip()[:80]))

    if summary_carries and not setters:
        lineno = next((n for n, text in summaries
                       if re.search(r'unproven', text, re.I)), summaries[0][0])
        findings.append((
            'A3', lineno,
            'the summary prints an unproven count but nothing in this file '
            'ever sets one -- it reports a state it cannot reach, which is '
            'the inverse defect and the one that keeps A1 honest.'))

    return findings, {
        'summary_construct': bool(summaries),
        'unproven_mechanism': bool(emits or setters),
        'in_scope': in_scope,
    }


# ---------------------------------------------------------------------------
# SCAN
# ---------------------------------------------------------------------------

def targets(root):
    """tests/**/*probe*.py and tests/**/*.test.js, plus tests/**/*.test.py."""
    base = os.path.join(root, 'tests')
    found = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames
                       if d not in ('.git', 'node_modules', '__pycache__')]
        for fn in filenames:
            if fn.endswith('.py') and 'probe' in fn:
                found.append(os.path.join(dirpath, fn))
            elif fn.endswith('.test.js') or fn.endswith('.test.py'):
                found.append(os.path.join(dirpath, fn))
    return sorted(found)


def main(argv):
    root = REPO
    only = None
    for i, a in enumerate(argv):
        if a == '--root' and i + 1 < len(argv):
            root = os.path.abspath(argv[i + 1])
        elif a == '--file' and i + 1 < len(argv):
            only = os.path.abspath(argv[i + 1])

    print('UNPROVEN ARM CHECK -- criteria %s' % CRITERIA_VERSION)
    print('  REPORT-ONLY. Not wired into the push gate; see this file\'s header.')
    print('  A4 ("unproven at most once") is NOT CHECKED -- it is a property of')
    print('  two consecutive RUNS and is invisible to a static read of source.')
    print('')

    files = [only] if only else targets(root)
    files = [f for f in files if os.path.isfile(f)]

    if not files:
        print('COULD NOT RUN: no file matched tests/**/*probe*.py or')
        print('tests/**/*.test.js under %s.' % root)
        print('Nothing was compared. "0 findings over 0 files" is')
        print('indistinguishable from a clean tree, so this is exit 2.')
        return 2

    all_findings = []
    unreadable = []
    n_summary = n_mech = n_scope = 0
    scoped_names = []
    not_assessed = []
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                src = fh.read()
        except OSError as exc:
            unreadable.append((path, str(exc)))
            continue
        rel = os.path.relpath(path, root).replace('\\', '/')
        findings, facts = analyse(path, src)
        n_summary += 1 if facts['summary_construct'] else 0
        n_mech += 1 if facts['unproven_mechanism'] else 0
        if facts['in_scope']:
            n_scope += 1
            scoped_names.append(rel)
        elif facts['unproven_mechanism']:
            # An unproven mechanism with NO detectable pass/fail summary. A1
            # and A2 both hang off the summary construct, so this file is NOT
            # ASSESSED -- named, counted separately, and never folded into the
            # clean verdict. "Could not assess" is a third state here for the
            # same reason it is everywhere else in this repo.
            not_assessed.append(rel)
        for sig, line, detail in findings:
            all_findings.append((rel, sig, line, detail))

    by_sig = {}
    for rel, sig, line, detail in all_findings:
        by_sig.setdefault(sig, []).append((rel, line, detail))

    # THE DENOMINATOR, PRINTED BEFORE THE FINDING COUNTS. "0 findings over 398
    # files" and "0 findings over 398 files, 0 of which could trip anything"
    # are different claims, and only the second one is honest. A1 and A2 can
    # only fire on an IN-SCOPE file -- one that both reports a pass/fail
    # summary and has an unproven mechanism -- so that number is the real
    # denominator and it is printed where nobody can quote the zero alone.
    print('  files scanned        %d' % len(files))
    print('  with a pass/fail summary construct   %d' % n_summary)
    print('  with an unproven mechanism           %d' % n_mech)
    print('  IN SCOPE for A1 (summary + mechanism) %d%s'
          % (n_scope, '   <- the denominator for the A1 zero below'
             if n_scope == 0 else ''))
    if scoped_names:
        for rel in scoped_names:
            print('      %s' % rel)
    print('  A1 NOT ASSESSED (mechanism, no summary)  %d' % len(not_assessed))
    for rel in not_assessed:
        print('      %s  -- A1 hangs off the summary construct, so A1 was not'
              % rel)
        print('      assessed here and this file is NOT part of a clean A1')
        print('      verdict. A2 DID run on it: A2 needs only the mechanism and')
        print('      the exit expression, which is the correction ablation forced.')
    for sig in ('A1', 'A2', 'A3'):
        print('  %s findings          %d' % (sig, len(by_sig.get(sig, []))))
    if unreadable:
        print('  UNREADABLE           %d  -- counted, never folded into clean'
              % len(unreadable))

    if all_findings:
        print('')
        for sig in ('A1', 'A2', 'A3'):
            for rel, line, detail in by_sig.get(sig, []):
                print('%s  %s:%d' % (sig, rel, line))
                print('    %s' % detail)

    if unreadable:
        print('')
        for path, err in unreadable:
            print('UNREADABLE  %s -- %s' % (path, err))

    print('')
    if all_findings or unreadable:
        print('%d FINDING(S) over %d file(s). REPORT-ONLY -- this does not block '
              'a push.' % (len(all_findings) + len(unreadable), len(files)))
        return 1
    print('NO FINDING over %d file(s) -- %d of them IN SCOPE for A1/A2, %d NOT '
          'ASSESSED.' % (len(files), n_scope, len(not_assessed)))
    print('A4 remains NOT CHECKED. Neither number above may be quoted alone.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
