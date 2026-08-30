#!/usr/bin/env python
"""Tokenizer-based comment/string stripper for JS.

Replaces every comment with a space and every string/template literal with an
empty literal of the same quote kind.  Self-test: the OUTPUT must still pass
`node --check`.  If the tokenizer mis-identifies a regex literal or a string
boundary, the output is overwhelmingly likely to be a syntax error, so a clean
`node --check` on the stripped file is real evidence the tokenizer worked --
not merely an assumption that it did.
"""
import sys

# A '/' starts a regex (not a division) when the previous significant token is
# not a value-producing token.  Standard heuristic.
VALUE_ENDERS = set(') ] }'.split())
KEYWORDS_BEFORE_REGEX = {
    'return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void',
    'throw', 'case', 'do', 'else', 'yield', 'await',
}


def strip(src):
    out = []
    i = 0
    n = len(src)
    prev_tok = ''          # last significant token (word or punctuation char)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''

        # line comment
        if c == '/' and nxt == '/':
            j = src.find('\n', i)
            if j == -1:
                j = n
            out.append(' ')
            i = j
            continue

        # block comment -- keep newlines so line numbers survive
        if c == '/' and nxt == '*':
            j = src.find('*/', i + 2)
            if j == -1:
                j = n
            else:
                j += 2
            out.append('\n' * src.count('\n', i, j))
            out.append(' ')
            i = j
            continue

        # string literals
        if c in ('"', "'"):
            q = c
            j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == q:
                    j += 1
                    break
                j += 1
            out.append(q + q)
            prev_tok = 'STR'
            i = j
            continue

        # template literal -- handle ${ } nesting recursively
        if c == '`':
            j = i + 1
            depth = 0
            while j < n:
                ch = src[j]
                if ch == '\\':
                    j += 2
                    continue
                if depth == 0 and ch == '`':
                    j += 1
                    break
                if depth == 0 and ch == '$' and j + 1 < n and src[j + 1] == '{':
                    depth += 1
                    j += 2
                    continue
                if depth > 0:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                j += 1
            seg = src[i:j]
            out.append('``')
            out.append('\n' * seg.count('\n'))
            prev_tok = 'STR'
            i = j
            continue

        # regex literal
        if c == '/':
            is_regex = True
            if prev_tok == 'STR' or prev_tok == 'NUM' or prev_tok == 'WORD_VAL':
                is_regex = False
            if prev_tok in VALUE_ENDERS:
                is_regex = False
            if is_regex:
                j = i + 1
                in_class = False
                ok = False
                while j < n:
                    ch = src[j]
                    if ch == '\\':
                        j += 2
                        continue
                    if ch == '\n':
                        break
                    if ch == '[':
                        in_class = True
                    elif ch == ']':
                        in_class = False
                    elif ch == '/' and not in_class:
                        j += 1
                        ok = True
                        break
                    j += 1
                if ok:
                    while j < n and src[j].isalpha():
                        j += 1
                    out.append(src[i:j])   # regexes are CODE -- keep verbatim
                    prev_tok = 'STR'
                    i = j
                    continue
            out.append(c)
            prev_tok = '/'
            i += 1
            continue

        # identifiers / numbers
        if c.isalnum() or c in '_$':
            j = i
            while j < n and (src[j].isalnum() or src[j] in '_$'):
                j += 1
            word = src[i:j]
            out.append(word)
            if word in KEYWORDS_BEFORE_REGEX:
                prev_tok = 'KW'
            elif word[0].isdigit():
                prev_tok = 'NUM'
            else:
                prev_tok = 'WORD_VAL'
            i = j
            continue

        out.append(c)
        if not c.isspace():
            prev_tok = c
        i += 1

    return ''.join(out)


if __name__ == '__main__':
    data = open(sys.argv[1], encoding='utf-8').read()
    open(sys.argv[2], 'w', encoding='utf-8').write(strip(data))
