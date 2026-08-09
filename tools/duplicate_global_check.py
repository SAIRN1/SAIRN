r"""
duplicate_global_check.py -- flags any top-level function name (or
window.X=function assignment) declared more than once anywhere in
stonedesk.html.

<script> blocks in a classic (non-module) HTML page all share ONE global
scope -- a `function foo(){}` declared at the top level of ANY block is a
true global, visible to every other block. If the same name is declared
at the top level twice, the LATER one silently wins for the rest of the
page's lifetime, and whichever declaration "loses" becomes dead code that
still looks correct on its own -- this exact bug hit four times in one
session (escHtml, renderCustomers, safetyRenderIncidents, invDelete),
each time only found by a live Playwright test showing the wrong
behavior, not by reading the code.

Method: extract every <script> block (reusing extract_scripts.py's real
HTML-parser-based extraction), then scan each block tracking brace depth
(skipping strings/comments) and recording every `function NAME(` or
`window.NAME = function(` seen at depth 0 -- i.e. NOT nested inside any
other function/IIFE, which is what makes it a true top-level global
rather than a private helper scoped to one closure. Flags any name seen
at depth 0 more than once, anywhere in the file.

Known limitation: only catches the two declaration styles actually used
throughout this file (`function NAME(...)` and `window.NAME = function`).
Arrow-function-assigned globals (`const NAME = () => {}`) or object-
method-shorthand globals are not tracked.

FIXED 2026-07-30 (was CONFIRMED REAL GAP, now closed): the brace-depth
scanner previously had zero regex-literal awareness, which caused two
related failure modes, both confirmed concretely on real files, not
theoretical:
  1. A regex containing literal `{`/`}` (e.g. `/\{2,4\}/`) miscounted
     as real braces.
  2. WORSE, and the one that actually broke sairnbiz.html's scan: a
     regex containing a literal quote character, e.g. `.replace(/'/g,
     '&#39;')` -- the scanner's naive `c in ("'",'"','\`')` check fired
     on the `'` INSIDE the regex delimiters, treated it as the start of
     a real string, and searched for the next `'` to close it -- which
     it found almost immediately (the very next `'` is the one opening
     `'&#39;'`), silently swallowing everything between as a fake
     "string" and desyncing the running depth for the rest of the
     block. Root-caused by tracing sairnbiz.html's depth to a first
     negative dip at line 828, then walking backward to find only ONE
     depth-0 function (`H`) detected before that point despite several
     more (`st`, `ld`, `$`, `fmt`, `fdate`, `toast`, ...) sitting in
     plain sight right after it -- the desync happened inside `H`'s own
     body, at exactly this `.replace(/'/g,...)` pattern.

Fix: track the previous significant token before each `/` and use the
standard JS-lexer heuristic to decide regex-literal vs division --a `/`
starts a regex if the previous non-whitespace character is anything
that can't end a value expression (an operator, `(`, `,`, `;`, `:`,
`{`, `}`, `[`, `!`, `&`, `|`, `?`, `=`, `<`, `>`, `+`, `-`, `*`, `%`, or
the very start of the block). Once inside a regex, scan to the closing
unescaped `/` (respecting a `[...]` character class, where an unescaped
`/` does NOT close the regex) treating everything inside as opaque,
then skip trailing flags. Not a full JS tokenizer -- still a heuristic,
same class of limitation as the rest of this toolkit -- but closes the
two confirmed failure modes above.
"""
import sys, os, re
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_scripts import ScriptExtractor

FUNC_DECL_RE = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')
WINDOW_ASSIGN_RE = re.compile(r'window\.([A-Za-z_$][\w$]*)\s*=\s*function\s*\(')

# Characters after which a '/' is a regex-literal start, not division.
# (Standard JS-lexer disambiguation heuristic.)
REGEX_PRECEDING_CHARS = set('([{,;:!&|?=<>+-*%~^\n')
REGEX_PRECEDING_KEYWORDS = ('return', 'typeof', 'instanceof', 'in', 'of',
                             'new', 'delete', 'void', 'throw', 'case', 'do',
                             'else', 'yield', 'await')


def _is_regex_start(content, i, last_sig_char, last_sig_word):
    if i == 0:
        return True
    if last_sig_char in REGEX_PRECEDING_CHARS:
        return True
    if last_sig_char == '/':
        return False
    if last_sig_word in REGEX_PRECEDING_KEYWORDS:
        return True
    return False


def find_depth0_globals(content, base_line):
    results = []
    depth = 0
    i = 0
    n = len(content)
    line = base_line
    last_sig_char = ''
    last_sig_word = ''
    word_buf = ''
    while i < n:
        c = content[i]
        if c == '\n':
            line += 1
            i += 1
            last_sig_char = '\n'
            continue
        if c.isspace():
            i += 1
            continue
        if c == '/' and i + 1 < n and content[i+1] == '/':
            j = content.find('\n', i)
            if j == -1:
                break
            i = j
            continue
        if c == '/' and i + 1 < n and content[i+1] == '*':
            j = content.find('*/', i+2)
            if j == -1:
                break
            line += content.count('\n', i, j)
            i = j + 2
            continue
        if c == '/' and _is_regex_start(content, i, last_sig_char, last_sig_word):
            j = i + 1
            in_class = False
            while j < n:
                if content[j] == '\\':
                    j += 2
                    continue
                if content[j] == '\n':
                    break  # unterminated regex -- bail, don't eat the rest of the block
                if content[j] == '[':
                    in_class = True
                elif content[j] == ']':
                    in_class = False
                elif content[j] == '/' and not in_class:
                    break
                j += 1
            j += 1  # past closing '/'
            while j < n and content[j] in 'gimsuy':
                j += 1
            i = j
            last_sig_char = '/'
            last_sig_word = ''
            continue
        if c in ("'", '"', '`'):
            quote = c
            j = i + 1
            while j < n:
                if content[j] == '\\':
                    j += 2
                    continue
                if content[j] == quote:
                    break
                j += 1
            line += content.count('\n', i, j)
            i = j + 1
            last_sig_char = quote
            last_sig_word = ''
            continue
        if c == '{':
            depth += 1
            i += 1
            last_sig_char = c
            last_sig_word = ''
            continue
        if c == '}':
            depth -= 1
            i += 1
            last_sig_char = c
            last_sig_word = ''
            continue
        if depth == 0:
            m = FUNC_DECL_RE.match(content, i)
            if m:
                results.append((m.group(1), 'function', line))
                i = m.end()
                last_sig_char = ')'
                last_sig_word = ''
                continue
            m2 = WINDOW_ASSIGN_RE.match(content, i)
            if m2:
                results.append((m2.group(1), 'window.assign', line))
                i = m2.end()
                last_sig_char = ')'
                last_sig_word = ''
                continue
        if c.isalnum() or c == '_' or c == '$':
            word_buf = (word_buf + c) if last_sig_char.isalnum() or last_sig_char in ('_', '$') else c
        else:
            word_buf = ''
        if word_buf:
            last_sig_word = word_buf
        last_sig_char = c
        i += 1
    return results


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'stonedesk.html'
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    parser = ScriptExtractor()
    parser.feed(html)

    all_globals = []
    for start_line, end_line, content in parser.blocks:
        all_globals.extend(find_depth0_globals(content, start_line))

    by_name = defaultdict(list)
    for name, kind, line in all_globals:
        by_name[name].append((kind, line))

    dupes = {name: entries for name, entries in by_name.items() if len(entries) > 1}

    print("TOTAL_DEPTH0_GLOBALS:%d" % len(all_globals))
    print("DISTINCT_NAMES:%d" % len(by_name))
    print("DUPLICATE_NAMES:%d" % len(dupes))
    for name in sorted(dupes):
        entries = dupes[name]
        print("DUPLICATE: %s -> %s" % (name, ', '.join('%s@%d' % (k, l) for k, l in entries)))

    sys.exit(1 if dupes else 0)


if __name__ == '__main__':
    main()
