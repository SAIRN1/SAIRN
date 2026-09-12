"""Control for testint.comments -- the piece everything else rests on.

A comment stripper that eats code is not a weak tool, it is a false one: every
check built on it then reports clean while reading a fraction of the input.
Three separate tools in the codebase this package came from carried a naive
regex and preserved **11%** of real files while reporting nothing wrong.

So the arms below are of two kinds and BOTH matter:

  * a comment really is removed  -- the tool does its job
  * code really is NOT removed   -- the tool does not eat the file

The second kind is the one that catches the expensive failure, and it is the
kind a hand-written smoke test usually skips.

Run: python tests/test_comments.py    (exit 0 pass, 1 fail)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from testint import comments  # noqa: E402

fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def gone(src, needle, **kw):
    return needle not in comments.strip(src, **kw)


def kept(src, needle, **kw):
    return needle in comments.strip(src, **kw)


print('1. LENGTH AND LINE NUMBERS SURVIVE')
src = 'a = 1  // note\nb = 2\n'
out = comments.strip(src, language='javascript')
check(len(out) == len(src), 'length is unchanged, so offsets still resolve')
check(out.count('\n') == src.count('\n'), 'newline count is unchanged')
check(out.splitlines()[1] == 'b = 2', 'the line after a comment is untouched')

print('')
print('2. JAVASCRIPT -- the cases that ate 80% of a real file')
js = 'x = 1; // gone\n/* gone */ y = 2;\n'
check(gone(js, 'gone', language='javascript'), 'both comment forms are removed')
check(kept(js, 'y = 2', language='javascript'), '...and the code between them is not')
# THE CASE THAT CAUSED THE INCIDENT. The /* in a MIME wildcard is not a comment.
mime = '<input accept="image/*" capture="environment">\nreal_code_here();\n'
check(kept(mime, 'real_code_here', language='javascript'),
      'a `/*` inside a STRING does not open a comment (the accept="image/*" case)')
check(kept('u = "http://x/y"; keep_me();', 'keep_me', language='javascript'),
      'a `//` inside a URL string is not a comment')
check(kept('re = /a\\/\\/b/; keep_me();', 'keep_me', language='javascript'),
      'a `//` inside a REGEX literal is not a comment')
check(kept('re = /[/]/; keep_me();', 'keep_me', language='javascript'),
      'a `/` inside a regex CHARACTER CLASS does not end the literal')
check(kept('s = `a ${b} // c`; keep_me();', 'keep_me', language='javascript'),
      'a template literal spanning a `//` is not a comment')
# Division must NOT be read as a regex, or everything after it is eaten.
check(kept('q = a / b; keep_me();', 'keep_me', language='javascript'),
      'a division `/` is not read as the start of a regex')
# ── THE ONE THIS PACKAGE GOT WRONG FIRST, CAUGHT BY MEASURING AGAINST A REAL
# FILE RATHER THAN BY READING. `<` was in the regex-context set on the reasoning
# that `a < /re/.source` is legal JavaScript. In HTML-embedded script `</div>`
# puts a `/` straight after a `<`, the scan runs forward for a closing `/` and
# finds it inside the NEXT HTML comment -- so the `<!--` never opens, and 267
# characters of comment survived as code in a real 2 MB file.
closing_tag = '</div><!-- /panel-wrap (label now correct) -->\nkeep_me();\n'
check(gone(closing_tag, 'panel-wrap', language='javascript'),
      'an HTML comment after a closing tag IS stripped (the `</div><!-- /x -->` case)')
check(kept(closing_tag, 'keep_me', language='javascript'),
      '...and the code after it survives')

print('')
print('3. PYTHON -- a docstring is a string, not a comment')
py = '# gone\nx = 1  # gone\ns = "# kept"\nd = """also kept"""\n'
check(gone(py, 'gone', language='python'), 'hash comments are removed')
check(kept(py, '# kept', language='python'), 'a hash inside a STRING is not a comment')
check(kept(py, 'also kept', language='python'),
      'a triple-quoted string is preserved -- it is a docstring, not a comment')
check(kept('s = r"\\"  \nkeep_me()', 'keep_me', language='python'),
      'a raw string ending in a backslash does not swallow the next line')

print('')
print('4. SQL -- doubled quotes, and block comments that NEST')
sql = "-- gone\nselect 'it''s fine' as keep_me;\n"
check(gone(sql, 'gone', language='sql'), 'a `--` comment is removed')
check(kept(sql, 'keep_me', language='sql'),
      "a doubled '' inside a string does not end it (it''s)")
# Standard SQL nests /* */. Treating it as non-nesting ends the comment at the
# first close and lets the tail of the comment back in as code.
nested = '/* outer /* inner */ still comment */ keep_me();'
check(gone(nested, 'still comment', language='sql'), 'nested block comments nest')
check(kept(nested, 'keep_me', language='sql'), '...and the code after them survives')

print('')
print('5. THE SAME NESTING IS WRONG FOR C, AND THAT IS DELIBERATE')
# C does NOT nest. The first */ ends it. Asserting the opposite would eat code.
c = '/* outer /* inner */ keep_me();'
check(kept(c, 'keep_me', language='c_family'),
      'C ends a block comment at the FIRST close, so the tail is code')

print('')
print('6. AN UNSUPPORTED LANGUAGE RAISES RATHER THAN GUESSING')
try:
    comments.strip('x', path='thing.cobol')
    check(False, 'an unknown extension raises UnsupportedLanguage')
except comments.UnsupportedLanguage:
    check(True, 'an unknown extension raises UnsupportedLanguage')
try:
    comments.strip('x', language='klingon')
    check(False, 'an unknown language name raises')
except comments.UnsupportedLanguage:
    check(True, 'an unknown language name raises')

print('')
print('7. SURVIVAL -- the number that catches a stripper eating the file')
code_heavy = 'function a(){return 1;}\nfunction b(){return 2;}\n'
check(comments.survival(code_heavy, language='javascript') == 1.0,
      'a file with no comments survives 100%')
mostly_comment = '/* ' + ('x ' * 200) + '*/\nf();\n'
s = comments.survival(mostly_comment, language='javascript')
check(s < 0.1, 'a file that is mostly comment survives under 10 percent (%.3f)' % s)
check(comments.caveats_for(language='python'),
      'caveats are reported rather than implied -- python has at least one')

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
