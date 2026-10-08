#!/usr/bin/env python
"""hover2_code_normalize.py -- strip comments and normalise identifiers
before counting or matching an anchor string, so a verdict is about CODE,
never about what a comment merely SAYS.

WRITTEN INDEPENDENTLY, NOT SHARED WITH H1. H1 built its own
hover_code_normalize.py (its seq944) in its own clone's log directory for
the same instruction. This role does not have write access to that file and
would not reuse it even if it did -- two instances agreeing because one is
a copy of the other proves nothing about either being correct, the same
reasoning hover_log.py's own header already gives for not copying H1's
hashing implementation. Built from the recurring defect class this role has
already found and verified several times this session, not from reading
H1's approach: tier_a_review_gate.py's own strip_diff_noise() (seq546/560's
own worked example -- a resource name inside a 3+-word sentence-shaped
quote is blanked; a bare identifier in real code is not), and
sd_data_family_mar_gate.js's own C0 uniqueness guard (an anchor matching a
file more than once means the check is measuring the wrong block, found the
hard way at that file's own commit history).

WHAT IT DOES: splits a source file's text into COMMENT regions and CODE
regions (line comments // and #, block comments /* */, naive -- does not
understand string literals containing comment-like sequences, which is
named as a limit below rather than silently handled), then reports where an
anchor string appears in each region separately. Optionally normalises
identifiers (case-fold, strip common separators) before matching, so
"employee_id" and "EmployeeID" or "employee-id" are not treated as proving
or disproving different things when the question is about the CONCEPT, not
the exact spelling.

LIMITS, NAMED RATHER THAN DISCOVERED LATER: a comment marker inside a
string literal (e.g. a JS string containing "//") is misread as starting a
comment. This is the same class of imprecision strip_diff_noise() itself
accepts for its own narrower job; a parser-correct version would need a
real tokenizer per language, which this tool does not attempt.

USAGE:
    python hover2_code_normalize.py --anchor "resource_name" --file path.js
    python hover2_code_normalize.py --anchor "resource_name" --file path.js --normalize
    python hover2_code_normalize.py --selftest
"""
import argparse
import re
import sys

LINE_COMMENT_JS = re.compile(r'//.*$', re.MULTILINE)
BLOCK_COMMENT_JS = re.compile(r'/\*.*?\*/', re.DOTALL)
LINE_COMMENT_PY = re.compile(r'#.*$', re.MULTILINE)


def split_code_and_comments(text, lang='js'):
    """(code_only, comments_only) -- code_only has every comment region
    replaced with spaces of the SAME LENGTH (so line/column numbers do not
    shift and a later re-match against the original text still lines up);
    comments_only is the inverse, code replaced with spaces."""
    if lang == 'py':
        patterns = [LINE_COMMENT_PY]
    else:
        patterns = [BLOCK_COMMENT_JS, LINE_COMMENT_JS]

    comment_spans = []
    for pat in patterns:
        for m in pat.finditer(text):
            comment_spans.append((m.start(), m.end()))
    comment_spans.sort()

    # Merge overlapping spans (a line comment inside what looks like a block
    # comment span, etc.) so code_only/comments_only partition cleanly.
    merged = []
    for s, e in comment_spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    code_chars = list(text)
    comment_chars = list(' ' * len(text))
    for s, e in merged:
        for i in range(s, e):
            ch = code_chars[i]
            comment_chars[i] = ch if ch != '\n' else '\n'
            code_chars[i] = ' ' if ch != '\n' else '\n'
    return ''.join(code_chars), ''.join(comment_chars)


_SEP_RE = re.compile(r'[_\-]+')


def normalize_identifier(s):
    """Case-folded, separator-collapsed form, for comparing CONCEPTS rather
    than exact spelling. "employee_id" / "EmployeeID" / "employee-id" all
    normalise to "employeeid"."""
    return _SEP_RE.sub('', s).lower()


def count_occurrences(text, anchor, normalize=False):
    if not normalize:
        return text.count(anchor)
    norm_text = normalize_identifier(text)
    norm_anchor = normalize_identifier(anchor)
    if not norm_anchor:
        return 0
    return norm_text.count(norm_anchor)


def check(args):
    try:
        with open(args.file, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    except OSError as e:
        print('COULD NOT RUN: could not read %s: %s' % (args.file, e))
        return 2

    lang = 'py' if args.file.endswith('.py') else 'js'
    code_only, comments_only = split_code_and_comments(text, lang)

    code_count = count_occurrences(code_only, args.anchor, args.normalize)
    comment_count = count_occurrences(comments_only, args.anchor, args.normalize)

    print('FILE: %s (lang=%s, normalize=%s)' % (args.file, lang, args.normalize))
    print('ANCHOR: %r' % args.anchor)
    print('IN CODE: %d' % code_count)
    print('IN COMMENTS ONLY: %d' % comment_count)
    if code_count == 0 and comment_count > 0:
        print('VERDICT: COMMENT-ONLY -- this anchor is never referenced in real code, '
             'only described in a comment. A verdict based on a plain grep over the '
             'whole file would have been WRONG here.')
        return 1
    if code_count > 0:
        print('VERDICT: REAL CODE REFERENCE EXISTS (%d time(s))' % code_count)
        return 0
    print('VERDICT: NOT FOUND ANYWHERE')
    return 1


def selftest():
    cases = 0
    failed = 0

    def case(label, ok):
        nonlocal cases, failed
        cases += 1
        print(('  ok   ' if ok else '  FAIL ') + label)
        if not ok:
            failed += 1

    # 1. THE MISLEADING-COMMENT FIXTURE, the exact shape this tool exists
    #    for: a resource name mentioned ONLY in a comment, never in real
    #    code, which a plain grep would wrongly count as "referenced."
    fixture_js = (
        "// sd_fake_resource used to be read here, before the rewrite\n"
        "function realHandler() {\n"
        "  return doSomethingElse('sd_real_resource');\n"
        "}\n"
    )
    code_only, comments_only = split_code_and_comments(fixture_js, 'js')
    case('comment-only mention: 0 occurrences in CODE',
        count_occurrences(code_only, 'sd_fake_resource') == 0)
    case('comment-only mention: 1 occurrence in COMMENTS',
        count_occurrences(comments_only, 'sd_fake_resource') == 1)
    case('real reference: 1 occurrence in CODE, 0 in comments',
        count_occurrences(code_only, 'sd_real_resource') == 1
        and count_occurrences(comments_only, 'sd_real_resource') == 0)

    # 2. BLOCK COMMENTS, multi-line.
    fixture_block = (
        "/* old code:\n"
        "   if (resource === 'sd_old_thing') { ... }\n"
        "*/\n"
        "if (resource === 'sd_new_thing') { realWrite(); }\n"
    )
    code_only2, comments_only2 = split_code_and_comments(fixture_block, 'js')
    case('block comment: the old resource is 0 in code, present in comments',
        count_occurrences(code_only2, 'sd_old_thing') == 0
        and count_occurrences(comments_only2, 'sd_old_thing') == 1)
    case('block comment does not eat the real line after it',
        count_occurrences(code_only2, 'sd_new_thing') == 1)

    # 3. IDENTIFIER NORMALISATION: three spellings of the same concept match
    #    under --normalize, and do NOT match without it.
    text_variants = "const employee_id = 1; const EmployeeID = 2; const employee-id-thing = 3;"
    case('without normalize, a differently-spelled variant does not match',
        count_occurrences(text_variants, 'EmployeeId', normalize=False) == 0)
    case('with normalize, employee_id / EmployeeID / employee-id all fold together',
        count_occurrences(text_variants, 'EmployeeId', normalize=True) >= 2)

    # 4. PYTHON LANG: # comments stripped the same way.
    fixture_py = "# legacy_rule_name was the old check\ndef real_rule_name():\n    pass\n"
    code_only3, comments_only3 = split_code_and_comments(fixture_py, 'py')
    case('python: comment-only name is 0 in code',
        count_occurrences(code_only3, 'legacy_rule_name') == 0)
    case('python: real def is present in code',
        count_occurrences(code_only3, 'real_rule_name') == 1)

    print('')
    print('%d case(s), %d failed' % (cases, failed))
    return 1 if failed else 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--anchor')
    ap.add_argument('--file')
    ap.add_argument('--normalize', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.anchor and args.file:
        return check(args)
    sys.stderr.write('nothing to do -- pass --anchor + --file, or --selftest\n')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
