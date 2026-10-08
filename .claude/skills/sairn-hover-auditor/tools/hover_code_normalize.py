#!/usr/bin/env python
"""Strip comments/docstrings and normalize identifiers -- so a correctness
verdict on code isn't swayed by a misleading comment or a misleading name.

Own tool, own location (hover's own log directory, never a build-agent
file). Built 2026-10-06 (H1, batch E, item 2). Every sweep this role built
before this one (hover_money_on_row_sweep.py, citation_class_check.py, etc)
only matches a GREP SHAPE -- a field name near a reduce/display call, a
citation's line number. The moment this role reads code to judge whether it
is actually RIGHT, not just pattern-shaped, a function named isSecure() that
returns true unconditionally, or a comment claiming "role-gated" above code
that checks no role at all, can sway a verdict the same way a misleading
variable name can. This tool produces a canonical, comment-free,
identifier-blind token stream so two structurally identical snippets
normalize to the SAME string regardless of what they are named or what a
comment above them claims -- and so two structurally DIFFERENT snippets
still read as different even when superficially dressed up to look alike.

NOT a parser -- a regex tokenizer. Correctly strips // and /* */ comments
and single/double/backtick-quoted strings (handling backslash escapes), and
renames every non-reserved identifier to VAR1, VAR2, ... in first-appearance
order, reset per call so two independently-normalized snippets are directly
comparable.

KNOWN GAP, NAMED RATHER THAN SILENTLY ASSUMED CORRECT: regex literals
(/pattern/flags) are not distinguished from the division operator. A regex
containing characters that look like a comment-opener or a string quote can
be mis-tokenized. Not exercised by any fixture below -- a future false
result from a regex-heavy file is a real possibility, not a surprise.
"""
import re
import sys

RESERVED = set("""
break case catch class const continue debugger default delete do else
export extends finally for function if import in instanceof new return
super switch this throw try typeof var void while with yield let static
get set async await of true false null undefined NaN Infinity
""".split())

TOKEN_RE = re.compile(r"""
    (?P<comment_line>//[^\n]*)
  | (?P<comment_block>/\*.*?\*/)
  | (?P<string_dq>"(?:\\.|[^"\\])*")
  | (?P<string_sq>'(?:\\.|[^'\\])*')
  | (?P<string_bt>`(?:\\.|[^`\\])*`)
  | (?P<ident>[A-Za-z_$][A-Za-z0-9_$]*)
  | (?P<number>\d+\.?\d*)
  | (?P<ws>\s+)
  | (?P<other>.)
""", re.VERBOSE | re.DOTALL)


def tokenize(code):
    return [(m.lastgroup, m.group()) for m in TOKEN_RE.finditer(code)]


def strip_comments(code):
    """Remove // and /* */ comments; everything else passes through verbatim."""
    toks = tokenize(code)
    return ''.join(text for kind, text in toks
                   if kind not in ('comment_line', 'comment_block'))


def normalize(code):
    """Strip comments AND rename every non-reserved identifier to VARn in
    first-appearance order. Strings and numbers are kept VERBATIM -- a
    literal value is part of behavior, not naming, and blinding it would
    hide real differences (e.g. a hardcoded True vs a hardcoded False)."""
    toks = tokenize(code)
    mapping = {}
    next_id = [1]
    out = []
    for kind, text in toks:
        if kind in ('comment_line', 'comment_block'):
            continue
        if kind == 'ident' and text not in RESERVED:
            if text not in mapping:
                mapping[text] = 'VAR%d' % next_id[0]
                next_id[0] += 1
            out.append(mapping[text])
        elif kind == 'ws':
            out.append(' ')
        else:
            out.append(text)
    return re.sub(r'\s+', ' ', ''.join(out)).strip(), mapping


# ---------------------------------------------------------------------------
# Selftest fixtures.
#
# FIXTURES_SAME: pairs where a misleading name or comment is the ONLY
# difference from an honestly-boring equivalent -- normalize() must collapse
# them to the identical string, proving the tool is not swayed by naming or
# comments.
#
# FIXTURES_DIFFERENT: pairs that are genuinely different in behavior despite
# looking superficially similar -- normalize() must NOT collapse them,
# proving the tool isn't just flattening everything to one blob.
# ---------------------------------------------------------------------------

FIXTURES_SAME = [
    (
        "misleading name+comment: claims full validation, always returns true",
        "function isValidLicense(key){ // fully validates the license against the server, checked on every call\n  return true;\n}",
        "honest trivial stub, same shape",
        "function foo(x){\n  return true;\n}",
    ),
    (
        "misleading comment claims a role check that is not actually there",
        "function evaluate(session){ // role-gated: owner/billing/nursing only\n  return doThing(session); }",
        "same shape, no claim, different names throughout",
        "function bar(a){ return doThing(a); }",
    ),
    (
        "same logic, reassuring name 'secureCheck'",
        "function secureCheck(u){ if(u){ return true; } return true; }",
        "same logic, neutral name 'f'",
        "function f(z){ if(z){ return true; } return true; }",
    ),
]

FIXTURES_DIFFERENT = [
    (
        "real role gate present before the call",
        "function evaluate(session){ if(!ALLOWED[session.role]) return null; return doThing(session); }",
        "no role gate at all, otherwise same shape",
        "function evaluate(session){ return doThing(session); }",
    ),
    (
        "returns true unconditionally",
        "function check(x){ return true; }",
        "returns the actual argument (NOT always true)",
        "function check(x){ return x; }",
    ),
]


def _selftest():
    ok = 0
    total = 0
    for desc_a, code_a, desc_b, code_b in FIXTURES_SAME:
        total += 1
        norm_a, _ = normalize(code_a)
        norm_b, _ = normalize(code_b)
        same = norm_a == norm_b
        status = 'ok  ' if same else 'FAIL'
        if same:
            ok += 1
        print('  %s SAME-expected  %s  <->  %s' % (status, desc_a, desc_b))
        if not same:
            print('       A: %s' % norm_a)
            print('       B: %s' % norm_b)
    for desc_a, code_a, desc_b, code_b in FIXTURES_DIFFERENT:
        total += 1
        norm_a, _ = normalize(code_a)
        norm_b, _ = normalize(code_b)
        same = norm_a == norm_b
        status = 'ok  ' if not same else 'FAIL'
        if not same:
            ok += 1
        print('  %s DIFF-expected  %s  <->  %s' % (status, desc_a, desc_b))
        if same:
            print('       A: %s' % norm_a)
            print('       B: %s' % norm_b)
    print('%d/%d fixtures correct' % (ok, total))
    return ok == total


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--strip' in argv:
        path = argv[argv.index('--strip') + 1]
        with open(path, encoding='utf-8') as f:
            sys.stdout.write(strip_comments(f.read()))
        return 0
    if '--normalize' in argv:
        path = argv[argv.index('--normalize') + 1]
        with open(path, encoding='utf-8') as f:
            norm, _mapping = normalize(f.read())
        print(norm)
        return 0
    print('usage: hover_code_normalize.py --selftest | --strip FILE | --normalize FILE')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
