"""Does a probe's assertion match the target's COMMENTS instead of its code?

WHY. Twice on 2026-09-10, hours apart, a probe searched a source file for a
literal and matched the fix's own comment rather than the code:

  * tests/sd_security_status_is_measured.js looked for 'Prompt injection: Active'
    to prove the hardcoded assurance was gone. The new Layer 30 header QUOTES all
    four dead literals to record what they were, so the probe failed a CORRECT
    file.
  * tests/sairnlaw_csp.js counted `eval(` to prove the file has none. The new CSP
    comment says "this file contains zero eval() and zero new Function()", so it
    counted its own documentation and failed a CORRECT file.

Both were caught because they went red. THE OTHER DIRECTION IS THE DANGEROUS ONE
AND NOTHING WOULD CATCH IT: an assertion of PRESENCE -- `indexOf(x) !== -1`,
"the guard is still there" -- passes when the only remaining mention of `x` is a
comment describing the feature that was deleted. A probe that goes green off a
comment is a check that stopped checking, which is the class this whole platform
keeps finding.

WHAT IT DOES. For each test that reads exactly one source file, it pulls the
string literals that test searches that source for, then asks where each literal
actually occurs in the target:

  COMMENT-ONLY   the literal exists ONLY inside comments. An assertion of
                 presence is passing on documentation; an assertion of absence
                 is failing on documentation. Either way it is not testing code.
  BOTH           it occurs in code AND in comments. A count-based assertion is
                 inflated; a boolean one is probably fine. Reported separately,
                 not lumped in.

REPORT ONLY. It never edits, and it is not a pass/fail gate on a single number:
a COMMENT-ONLY hit can legitimately be a probe asserting that a comment SURVIVES
-- tests/sairnlaw_csp.js arm 3c does exactly that on purpose. Those are declared
in EXPECTED_COMMENT_ASSERTIONS below with a reason, the same two-list discipline
as the cache-purge guards: an exclusion is a decision with a reason beside it,
never a silence.

WHAT IT CANNOT SEE, said here rather than discovered later:
  * literals built by concatenation or interpolation -- only simple quoted
    strings are extracted;
  * regex-literal assertions (`/foo/.test(src)`) are skipped. The pattern is not
    a plain string and matching it against comment spans would need a real JS
    regex engine;
  * the comment stripper is a scanner, not a parser. It understands HTML
    comments, `//` to end of line and block comments, and it does NOT strip a
    `//` that sits inside a string literal -- so it can over-strip. That biases
    it toward reporting MORE code as comment, i.e. toward false alarms rather
    than misses, which is the safe direction for a report-only checker;
  * a test that reads several sources is skipped rather than guessed at.

Usage:
    python tools/comment_quote_check.py
    python tools/comment_quote_check.py --json

Exit 0 clean, 1 when an undeclared comment-only assertion exists.
"""
import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Declared, with a reason each. See the module docstring for why this list
# exists rather than the checker simply not looking.
EXPECTED_COMMENT_ASSERTIONS = {
    # ON PURPOSE: the probe's subject IS the comment.
    ('tests/sairnlaw_csp.js', 'zero eval() and zero'):
        'arm 3c asserts the comment recording "this file has no eval" survives.',
    ('tests/sd_security_status_is_measured.js', "'Prompt injection: Active'"):
        'arm 1e asserts the Layer 30 header still QUOTES the dead literal it '
        'replaced, so the history is not silently dropped.',
    ('tests/sairndental_write_failure_voice.js', 'sync not yet enabled'):
        'line 63 searches a comment-STRIPPED copy for the absence; line 70 then '
        'asserts on the raw file that the comment record of the old wording was '
        'NOT removed. Both halves deliberate, and prior art for this whole rule '
        '-- it was doing the right thing before the rule existed.',
    # LOCATORS: the comment is used to FIND a block, not to prove anything. Safe
    # only because a miss is asserted, which is what makes these declarable
    # rather than defects -- `assert.ok(start > 0, ...)` fails loudly if the
    # heading is ever reworded, instead of silently testing an empty slice.
    ('tests/nesting_dxf.js', '  // ── SAW AND PICK TICKETS (2026-09-02'):
        'block locator; the miss is asserted at start > 0.',
    ('tests/nesting_saw_ticket.js', '  // ── SAW AND PICK TICKETS (2026-09-02'):
        'block locator; the miss is asserted at start > 0.',
}

READ_RE = re.compile(r"readFileSync\(path\.join\(__dirname, *'\.\.',([^)]*)\)")
# Simple, quoted-literal searches only -- see the docstring on what is skipped.
# THE VARIABLE MATTERS, NOT JUST THE CALL. An early version matched any
# `x.indexOf('lit')` and produced two false alarms immediately: one on a probe
# searching `codeOnly`, a comment-stripped copy it had made itself, and one on
# a sibling searching `policy`, a substring of the file. Both were doing exactly
# the right thing. Only a search against the variable BOUND TO THE RAW FILE can
# be testing comments, so that is the only variable considered.
BIND_RE = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*fs\.readFileSync\(")
# Simple, quoted-literal searches only -- see the docstring on what is skipped.
SEARCH_TMPL = "\\b%s\\.(?:indexOf|includes)\\(\\s*%s(.+?)%s"


def strip_comments(text, sql=False):
    """Blank out comment spans, preserving offsets so positions stay comparable.

    STRING-AWARE, AND THE FIRST VERSION WAS NOT -- which made this tool commit
    the exact error it exists to find. It blanked from any `//` to end of line,
    so every `https://` in the target blanked the rest of ITS line, and on a
    file as URL-dense as stonedesk.html that reported real rendering code as
    comment. The count before and after the fix is in the commit message.

    It now skips quoted strings (single, double, backtick) before looking for a
    comment opener, and treats `://` as a URL rather than a comment. It still
    does not parse regex literals, so a `//` inside one can over-strip --
    disclosed rather than hidden, and it biases toward reporting MORE code as
    comment, which for a report-only checker is the safe direction.
    """
    out = list(text)

    def blank(a, b, keep_newlines=True):
        for k in range(a, b):
            if not (keep_newlines and out[k] == '\n'):
                out[k] = ' '

    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ('"', "'", "`"):
            # Skip the string whole. Nothing inside it opens a comment.
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == c:
                    j += 1
                    break
                if c != "`" and text[j] == '\n':
                    break          # unterminated on this line; do not run away
                j += 1
            i = j
            continue
        if text.startswith('<!--', i):
            j = text.find('-->', i)
            j = n if j < 0 else j + 3
            blank(i, j)
            i = j
        elif text.startswith('/*', i):
            j = text.find('*/', i)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
        elif text.startswith('//', i) and text[i - 1:i] != ':':
            # `text[i-1] == ":"` is a URL scheme, not a comment. That one
            # character is the difference between this tool working and this
            # tool reporting a third of stonedesk.html as documentation.
            j = text.find('\n', i)
            j = n if j < 0 else j
            blank(i, j, keep_newlines=False)
            i = j
        elif sql and text.startswith('--', i) and text[max(0, i - 1):i] in ('', chr(10), ' '):
            # SQL LINE COMMENT, AND ONLY IN A SQL FILE. This branch used to run
            # on every file type and it silently destroyed real markup: this
            # repo writes ' -- ' in ordinary prose constantly, so
            # "<title>SAIRNmechanical -- HVAC & Mechanical</title>" had
            # everything from the dashes onward blanked, INCLUDING the closing
            # tag. Found 2026-09-11 by tools/comment_sensitivity_check.py, which
            # noticed panel_nesting_check.py giving a different answer on a
            # stripped copy -- the tool built today catching a defect in the
            # tool built yesterday, which is the system working rather than a
            # coincidence worth glossing over.
            # SQL line comment, only at a line start or after whitespace.
            j = text.find('\n', i)
            j = n if j < 0 else j
            blank(i, j, keep_newlines=False)
            i = j
        else:
            i += 1
    return ''.join(out)

def target_of(test_path, src):
    """The single source file this test reads, or None if it is not exactly one."""
    names = []
    for m in READ_RE.finditer(src):
        parts = re.findall(r"'([^']+)'", m.group(1))
        if parts:
            names.append('/'.join(parts))
    names = sorted(set(names))
    if len(names) != 1:
        return None
    p = os.path.join(REPO, *names[0].split('/'))
    return p if os.path.exists(p) else None


def main(argv):
    rows = []
    for test in sorted(glob.glob(os.path.join(REPO, 'tests', '**', '*.js'), recursive=True)):
        rel = os.path.relpath(test, REPO).replace('\\', '/')
        tsrc = open(test, encoding='utf-8', errors='replace').read()
        target = target_of(test, tsrc)
        if not target:
            continue
        tgt_rel = os.path.relpath(target, REPO).replace('\\', '/')
        raw = open(target, encoding='utf-8', errors='replace').read()
        code = strip_comments(raw)
        raw_vars = set(BIND_RE.findall(tsrc))
        if not raw_vars:
            continue
        pats = [SEARCH_TMPL % (re.escape(v), q, q) for v in raw_vars for q in ('"', '\'')]
        search_re = re.compile('|'.join(pats))
        for m in search_re.finditer(tsrc):
            lit = next(g for g in m.groups() if g is not None)
            if len(lit) < 6:
                continue          # too short to be a meaningful anchor
            lit = lit.replace('\\\\', '\\').replace("\\'", "'").replace('\\"', '"')
            in_raw = raw.count(lit)
            if not in_raw:
                continue          # not about this target at all
            in_code = code.count(lit)
            if in_code == 0:
                state = 'COMMENT-ONLY'
            elif in_code < in_raw:
                state = 'BOTH'
            else:
                continue
            declared = (rel, lit) in EXPECTED_COMMENT_ASSERTIONS
            rows.append({'test': rel, 'target': tgt_rel, 'literal': lit,
                         'in_source': in_raw, 'in_code': in_code,
                         'state': state, 'declared': declared})

    undeclared = [r for r in rows if r['state'] == 'COMMENT-ONLY' and not r['declared']]
    both = [r for r in rows if r['state'] == 'BOTH']

    if '--json' in argv:
        print(json.dumps(rows, indent=1))
    else:
        print('COMMENT-QUOTE CHECK -- report only, nothing was written')
        print('  assertions inspected      : %d' % len(rows))
        print('  COMMENT-ONLY, undeclared  : %d  (the assertion is testing a comment)' % len(undeclared))
        print('  COMMENT-ONLY, declared    : %d  (deliberate -- see the tool)'
              % sum(1 for r in rows if r['state'] == 'COMMENT-ONLY' and r['declared']))
        print('  BOTH code and comment     : %d  (a COUNT here is inflated)' % len(both))
        for r in undeclared:
            print('\n  %s' % r['test'])
            print('      searches %s for %r' % (r['target'], r['literal']))
            print('      occurs %d time(s), ALL of them inside comments -- this asserts'
                  % r['in_source'])
            print('      something about the documentation, not about the code.')
        for r in both:
            print('\n  %-52s BOTH' % r['test'])
            print('      %r in %s: %d total, %d in code'
                  % (r['literal'], r['target'], r['in_source'], r['in_code']))
    return 1 if undeclared else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
