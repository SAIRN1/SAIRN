#!/usr/bin/env python
"""tools/sairn_strict_args_check.py -- Guardian check 31.

Finds functions that mutate a parameter and then forward `arguments`, inside a
script block that is under 'use strict'. In that situation the arguments object
is NOT linked to the parameters, so the mutation is silently thrown away.

WHY THIS IS ITS OWN CHECK. On 2026-08-30 six window.fetch patches in
stonedesk.html had exactly this shape. Three were on live features -- Session
Memory, Tone & Style, and the personalization / shared-knowledge /
employee-profile injector -- and every one had been doing nothing since it
shipped. No error, no failed request, nothing wrong on screen. The code reads
correctly, renders correctly, and passes node --check, because it IS valid
JavaScript. Only running it settles the question, which is what
tools/strict_args_harness.js is for.

THE TRAP: the functions carry no 'use strict' of their own. They inherit it from
an enclosing IIFE dozens of lines above, so reading the function in isolation
gives no hint. This checker therefore looks for strictness at BLOCK level, not
at function level -- checking the function alone would find nothing.

Usage:
    python tools/sairn_strict_args_check.py [file.html ...]      # default: *.html

Exit 0 when clean, 1 when any site is found.

KNOWN LIMITS, stated because a checker that over-reports gets ignored:
  * Regex-based, not a JS parser. It reads a bounded window after each function
    opening, so an unusually long function body can be truncated.
  * It matches the text `.apply(this, arguments)` anywhere in that window --
    INCLUDING INSIDE A COMMENT. That is a real false positive and it has already
    happened once: the fix commit for the original six added an explanatory
    comment quoting the old line, and the re-scan flagged it. Read the hit
    before believing it.
  * It only recognises `param = Object.assign(...)` as mutation. Other forms
    (`param = {...param}`, `param.body = x` -- the latter is NOT this bug, since
    mutating in place does reach the callee) are not detected.
"""
import re
import sys
import glob
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BLOCK = re.compile(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', re.S)
FN = re.compile(
    r'(?:window\.)?([\w.$]+)\s*=\s*(?:async\s+)?function\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)\s*\{',
    re.M,
)
FORWARD = re.compile(r'\.apply\s*\(\s*this\s*,\s*arguments\s*\)')
STRICT = re.compile(r'''^\s*['"]use strict['"]\s*;''', re.M)
LINE_COMMENT = re.compile(r'//[^\n]*')
BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.S)


def strip_comments(text):
    return LINE_COMMENT.sub('', BLOCK_COMMENT.sub('', text))


def scan(path):
    src = open(path, encoding='utf-8', errors='replace').read()
    findings = []
    for bm in BLOCK.finditer(src):
        js = bm.group(1)
        base = bm.start(1)
        if not STRICT.search(js):
            continue  # sloppy mode: arguments IS linked, mutation carries through
        for m in FN.finditer(js):
            name, p1, p2 = m.group(1), m.group(2), m.group(3)
            body = js[m.end():m.end() + 3000]
            end = re.search(r'\n\s{0,4}\};', body)
            if end:
                body = body[:end.end()]
            body = strip_comments(body)
            mutates = re.search(r'\b%s\s*=\s*Object\.assign' % re.escape(p2), body)
            if mutates and FORWARD.search(body):
                findings.append((src[:base + m.start()].count('\n') + 1, name, p1, p2))
    return findings


def main(argv):
    targets = argv[1:] or sorted(glob.glob('*.html'))
    total = 0
    for path in targets:
        for line, name, p1, p2 in scan(path):
            print('%s:%d  %s = function(%s, %s) mutates `%s` then forwards '
                  '`arguments` under strict mode -- the mutation is DISCARDED. '
                  'Forward explicitly: .call(this, %s, %s)'
                  % (path, line, name, p1, p2, p2, p1, p2))
            total += 1
    print('')
    if total:
        print('%d site(s) found. Confirm with: node tools/strict_args_harness.js' % total)
        return 1
    print('clean -- no mutate-then-forward-arguments sites under strict mode')
    print('in %d file(s)' % len(targets))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
