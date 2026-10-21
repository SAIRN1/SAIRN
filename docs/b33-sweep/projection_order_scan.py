#!/usr/bin/env python
"""Find object merges where an UNTRUSTED/STORED source can override KEYED columns.

CONCEPT (one line): in `Object.assign(a, b, c)` and in `{ ...a, k: v }` the LATER
source wins, so a merge is a candidate when a keyed object literal (the
authoritative columns) comes BEFORE a non-literal source (a stored or supplied
blob); flag it, then classify by hand -- the scan reports shape, never intent.

  python projection_order_scan.py --fixtures       # criteria lock, alone
  python projection_order_scan.py <file-or-dir>... # scan
Exit 0 = ran; 1 = fixtures failed; 2 = could not run.
"""
import os
import re
import sys


def mask(src):
    """Return src with comment bodies and string/template contents replaced by
    spaces (same length, newlines kept), so bracket matching sees only code."""
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        nx = src[i + 1] if i + 1 < n else ''
        if c == '/' and nx == '/':
            j = src.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
        elif c == '/' and nx == '*':
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if src[k] != '\n':
                    out[k] = ' '
            i = j
        elif c in '\'"`':
            q = c
            j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == q:
                    break
                if q != '`' and src[j] == '\n':
                    break
                j += 1
            for k in range(i + 1, min(j, n)):
                if src[k] != '\n':
                    out[k] = ' '
            i = j + 1
        else:
            i += 1
    return ''.join(out)


def match(m, i, open_c, close_c):
    depth = 0
    for j in range(i, len(m)):
        if m[j] == open_c:
            depth += 1
        elif m[j] == close_c:
            depth -= 1
            if depth == 0:
                return j
    return -1


def split_top(m, a, b):
    """Split m[a:b] on top-level commas -> list of (start, end)."""
    parts, depth, s = [], 0, a
    for j in range(a, b):
        c = m[j]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ',' and depth == 0:
            parts.append((s, j))
            s = j + 1
    parts.append((s, b))
    return [(x, y) for x, y in parts if m[x:y].strip()]


def is_keyed_literal(text):
    t = text.strip()
    if not t.startswith('{') or not t.endswith('}'):
        return False
    inner = t[1:-1].strip()
    return bool(inner) and not inner.startswith('...') or (
        bool(inner) and bool(re.search(r'[A-Za-z_$][\w$]*\s*:', inner)))


def is_literal(text):
    t = text.strip()
    return t.startswith('{') and t.endswith('}')


def scan_text(src):
    m = mask(src)
    hits = []
    for mt in re.finditer(r'Object\.assign\s*\(', m):
        o = mt.end() - 1
        c = match(m, o, '(', ')')
        if c < 0:
            continue
        args = split_top(m, o + 1, c)
        if len(args) < 2:
            continue
        texts = [m[a:b] for a, b in args]
        lit = [is_literal(t) for t in texts]
        keyed = [is_keyed_literal(t) for t in texts]
        # candidate: a keyed literal precedes a NON-literal source
        first_keyed = next((i for i, k in enumerate(keyed) if k), None)
        if first_keyed is None:
            continue
        later_nonlit = [i for i in range(first_keyed + 1, len(texts)) if not lit[i]]
        if not later_nonlit:
            continue
        line = src.count('\n', 0, mt.start()) + 1
        hits.append(('assign', line, src[args[first_keyed][0]:args[first_keyed][1]].strip()[:90],
                     [src[args[i][0]:args[i][1]].strip()[:40] for i in later_nonlit]))
    # object-spread: `{ key: v, ...x }` -- a spread AFTER a keyed property
    for mt in re.finditer(r'\{', m):
        o = mt.start()
        c = match(m, o, '{', '}')
        if c < 0 or c - o > 4000:
            continue
        body_parts = split_top(m, o + 1, c)
        seen_key = False
        for a, b in body_parts:
            t = m[a:b].strip()
            if t.startswith('...'):
                if seen_key:
                    line = src.count('\n', 0, o) + 1
                    hits.append(('spread', line, src[o:min(c + 1, o + 90)].replace('\n', ' '),
                                 [t[:40]]))
                    break
            elif re.match(r'[A-Za-z_$][\w$]*\s*(:|,|$)', t) or re.match(r'[\'"]', t):
                seen_key = True
    return hits


FIXTURES = [
    # (name, source, expect_hit)
    ('inverted assign: columns first, blob last',
     "x = Object.assign({ id: r.job_id, status: r.s }, r.data);", True),
    ('safe assign: blob first, columns last',
     "x = Object.assign({}, r.data, { id: r.job_id });", False),
    ('safe assign: all literals', "x = Object.assign({ a: 1 }, { b: 2 });", False),
    ('inverted spread: key then spread', "x = { id: 1, ...blob };", True),
    ('safe spread: spread then key', "x = { ...blob, id: 1 };", False),
    ('keyed literal then identifier, 3 args',
     "x = Object.assign({ a: 1 }, { b: 2 }, extra);", True),
    ('string containing Object.assign is not code',
     "x = 'Object.assign({ a: 1 }, blob)';", False),
    ('comment containing it is not code',
     "// Object.assign({ a: 1 }, blob)\nx = 1;", False),
    ('nested call arg is balanced',
     "x = Object.assign({ a: f(1, 2) }, g(h(3)));", True),
    ('empty literal first is NOT a keyed literal',
     "x = Object.assign({}, blob);", False),
]


def run_fixtures():
    bad = 0
    for name, src, expect in FIXTURES:
        got = bool(scan_text(src))
        ok = got == expect
        print('  %s %s' % ('ok  ' if ok else 'FAIL', name))
        if not ok:
            bad += 1
            print('       expected %s got %s' % (expect, got))
    print('  %d/%d fixtures classify correctly' % (len(FIXTURES) - bad, len(FIXTURES)))
    return bad


def main(argv):
    if '--fixtures' in argv:
        return 1 if run_fixtures() else 0
    if run_fixtures():
        print('REFUSING TO SCAN: criteria fixtures failed', file=sys.stderr)
        return 1
    files = []
    for a in [x for x in argv if not x.startswith('--')]:
        if os.path.isdir(a):
            for dp, _dn, fn in os.walk(a):
                for f in fn:
                    if f.endswith('.js') and not f.endswith('.test.js'):
                        files.append(os.path.join(dp, f))
        elif os.path.isfile(a):
            files.append(a)
    if not files:
        print('COULD NOT RUN: no files', file=sys.stderr)
        return 2
    total = 0
    for f in sorted(files):
        src = open(f, encoding='utf-8', errors='replace').read()
        for kind, line, head, later in scan_text(src):
            total += 1
            print('%s:%d [%s] %s  <-  %s' % (f, line, kind, head, ', '.join(later)))
    print('%d candidate(s) in %d file(s)' % (total, len(files)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
