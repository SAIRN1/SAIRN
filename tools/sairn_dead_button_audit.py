#!/usr/bin/env python3
"""
sairn_dead_button_audit.py -- non-functional-button audit for SAIRN apps.

Usage:  python3 sairn_dead_button_audit.py stonedesk.html [sairnbiz.html ...]

Bakes in the two Session 77 corrections:
  1. Comments are stripped before ANY counting. A `function foo()` written
     inside an explanatory comment is not a definition.
  2. A toast-only function body is NOT a finding until its callers are
     enumerated. Zero callers -> orphan (delete). Callers -> live button
     (wire up or relabel). Opposite fixes, so never guess.
"""
import re
import sys
import collections

TOAST = r'(?:showToast|toast|showMsg|notify|alert)'
HANDLER = re.compile(r'\bon(?:click|change|submit|input|dblclick|keyup)\s*=\s*(["\'])(.*?)\1',
                     re.S | re.I)
DOM_BUILTINS = {
    'getElementById', 'querySelector', 'querySelectorAll', 'click', 'remove',
    'scrollIntoView', 'focus', 'blur', 'preventDefault', 'stopPropagation',
    'parseInt', 'parseFloat', 'String', 'Number', 'Boolean', 'Array', 'Object',
    'JSON', 'Math', 'Date', 'confirm', 'prompt', 'alert', 'setTimeout',
    'setInterval', 'encodeURIComponent', 'decodeURIComponent', 'isNaN',
    'fetch', 'print', 'open', 'close', 'reload', 'toLocaleString', 'toFixed',
    'if', 'for', 'while', 'switch', 'return', 'typeof', 'new', 'function',
    'catch', 'this',
}


def blank(s):
    """Replace with spaces, preserving newlines so line numbers stay true."""
    return re.sub(r'[^\n]', ' ', s)


def strip_comments(src):
    r"""Blank out //, /* */ and <!-- --> comments with a real state machine.

    A naive /\*.*?\*/ regex is UNSAFE here: a /* inside a string, a URL or a
    regex literal blanks thousands of lines of real code and every function
    definition in them then reads as 'never defined'. This is what produced
    58 phantom dead buttons on the first run of this script.
    """
    out = list(src)
    i, n = 0, len(src)
    prev = ''            # last significant char, for regex-vs-divide
    REGEX_OK = set('(,=:[!&|?{};+-*%~^') | {''}

    def kill(a, b):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ' '

    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        # HTML comment
        if src.startswith('<!--', i):
            j = src.find('-->', i)
            j = n if j == -1 else j + 3
            kill(i, j); i = j; continue
        # block comment
        if c == '/' and nxt == '*':
            j = src.find('*/', i + 2)
            j = n if j == -1 else j + 2
            kill(i, j); i = j; continue
        # line comment
        if c == '/' and nxt == '/':
            j = src.find('\n', i)
            j = n if j == -1 else j
            kill(i, j); i = j; continue
        # string / template literal -- skip over, never strip inside
        if c in '"\'`':
            q = c; j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2; continue
                if src[j] == q:
                    j += 1; break
                if q != '`' and src[j] == '\n':
                    break
                j += 1
            i = j; prev = q; continue
        # regex literal -- skip over, so /*/ and // inside it are safe
        if c == '/' and prev in REGEX_OK:
            j = i + 1; ok = False
            while j < n and src[j] != '\n':
                if src[j] == '\\':
                    j += 2; continue
                if src[j] == '[':
                    while j < n and src[j] not in ']\n':
                        j += 2 if src[j] == '\\' else 1
                if src[j] == '/':
                    ok = True; j += 1; break
                j += 1
            if ok:
                i = j; prev = '/'; continue
        if not c.isspace():
            prev = c
        i += 1
    return ''.join(out)


def mask_scripts(src):
    """Blank out <script> bodies so HTML-side scans don't see JS."""
    out = list(src)
    for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', src, re.S | re.I):
        for i in range(m.start(1), m.end(1)):
            if out[i] != '\n':
                out[i] = ' '
    return ''.join(out)


def audit(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        raw = fh.read()
    src = strip_comments(raw)          # <-- correction 1
    html = mask_scripts(src)

    def ln(pos):
        return src.count('\n', 0, pos) + 1

    # ---- definitions (comment-free) ----
    defined = collections.defaultdict(list)
    for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*)\s*\(', src):
        defined[m.group(1)].append(ln(m.start()))
    for m in re.finditer(
            r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\()', src):
        defined[m.group(1)].append(ln(m.start()))
    for m in re.finditer(r'window\.([A-Za-z_$][\w$]*)\s*=', src):
        defined[m.group(1)].append(ln(m.start()))

    # ---- every call site anywhere (handlers + JS body) ----
    calls = collections.defaultdict(list)
    for m in re.finditer(r'\b([A-Za-z_$][\w$]*)\s*\(', src):
        calls[m.group(1)].append(ln(m.start()))
    handler_calls = collections.defaultdict(list)
    for m in HANDLER.finditer(html):
        for c in re.finditer(r'\b([A-Za-z_$][\w$]*)\s*\(', m.group(2)):
            handler_calls[c.group(1)].append(ln(m.start()))

    findings = collections.OrderedDict()

    # A. handler target with no definition -> hard dead button
    findings['A. DEAD BUTTON -- handler target never defined'] = [
        f'{n}()  x{len(v)}  handler line(s) {v[:8]}'
        for n, v in sorted(handler_calls.items())
        if n not in defined and n not in DOM_BUILTINS
    ]

    # B. inline handler whose only action is a toast
    findings['B. DEAD BUTTON -- inline handler is toast-only'] = [
        f'L{ln(m.start())}: {m.group(2).strip()[:120]}'
        for m in HANDLER.finditer(html)
        if re.fullmatch(TOAST + r'\s*\(.*\)', m.group(2).strip().rstrip(';').strip(), re.S | re.I)
    ]

    # C. toast-only function bodies, SPLIT by caller count  <-- correction 2
    live, orphan = [], []
    for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{(.*?)\}', src, re.S):
        name, body = m.group(1), m.group(2).strip()
        if len(body) > 220 or not body:
            continue
        stmts = [s.strip() for s in body.split(';') if s.strip()]
        if not stmts or not any(re.match(TOAST + r'\s*\(', s, re.I) for s in stmts):
            continue
        if not all(re.match(TOAST + r'\s*\(', s, re.I) or re.match(r'return\b', s) for s in stmts):
            continue
        sites = [p for p in calls.get(name, []) if p not in defined.get(name, [])]
        row = f'L{ln(m.start())}: {name}()  callers={len(sites)} {sites[:6]}'
        (live if sites else orphan).append(row)
    findings['C1. LIVE toast-only function (wire up or relabel)'] = live
    findings['C2. ORPHAN toast-only function, zero callers (delete)'] = orphan

    # D. duplicate definitions, comment-free
    findings['D. DUPLICATE definitions (later silently wins)'] = [
        f'{n}  x{len(v)}  lines {v}'
        for n, v in sorted(defined.items()) if len(v) > 1 and n not in ('load', 'save', 'render', 's', 'sv')
    ]

    # E. placeholder copy, excluding input placeholder= and CSS class names
    place = []
    for pat in (r'coming next build', r'coming soon', r'not yet implemented',
                r'future build', r'future release', r'under construction',
                r'work in progress', r'\bTODO\b', r'\bFIXME\b'):
        for m in re.finditer(pat, src, re.I):
            place.append(f'L{ln(m.start())}: {pat}')
    for m in re.finditer(r'placeholder', src, re.I):
        pre = src[max(0, m.start() - 30):m.start()]
        post = src[m.end():m.end() + 2]
        if not post.startswith('=') and 'class' not in pre and '-' not in pre[-1:]:
            place.append(f'L{ln(m.start())}: bare "placeholder" -- check by hand')
    findings['E. PLACEHOLDER copy (attrs and CSS classes excluded)'] = place

    print('=' * 72)
    print(f'{path}   {len(raw):,} bytes')
    print('=' * 72)
    total = 0
    for head, rows in findings.items():
        print(f'\n{head}  -> {len(rows)}')
        total += len(rows)
        for r in rows[:40]:
            print(f'   {r}')
        if len(rows) > 40:
            print(f'   ... {len(rows) - 40} more')
    print(f'\nTOTAL FLAGGED: {total}')
    print('Reminder: A and B are fixes. C1 vs C2 are OPPOSITE fixes -- read the '
          'caller list, do not guess. D and E need a human read before action.\n')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        audit(p)
