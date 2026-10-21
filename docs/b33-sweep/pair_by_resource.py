#!/usr/bin/env python
"""Pair each inverted-projection candidate with the write path of the SAME resource.

CONCEPT (one line): proximity is not pairing -- a read projection is proved inert
only against the storedBlob() strip lists of the SAME RESOURCE (pooled across the
read and write blocks that name it), found by brace-matching each `if (resource === 'X'` block.

  python pair_by_resource.py <dir containing projection_order_scan.py> <file.js>
Prints one line per site: line, resource(s), keys, verdict.
  PAIRED   every key is in a strip list of a storedBlob() in ANY block naming the same resource
  PARTIAL  some keys are, some are not (named)
  NO-STRIP no storedBlob() anywhere for that resource -- allowlisted or raw: READ BY HAND
  GENERIC  the site is not inside a literal `resource === '...'` block
"""
import re
import sys

sys.path.insert(0, sys.argv[1])
import projection_order_scan as P

src = open(sys.argv[2], encoding='utf-8').read()
m = P.mask(src)


def line_of(i):
    return src.count('\n', 0, i) + 1


# every `if (<cond containing resource === 'x'>) {` block
blocks = []
for mt in re.finditer(r'\bif\s*\(', m):
    o = mt.end() - 1
    c = P.match(m, o, '(', ')')
    if c < 0:
        continue
    cond = src[o:c + 1]
    names = re.findall(r"resource\s*===\s*'(\w+)'", cond)
    if not names:
        continue
    k = c + 1
    while k < len(m) and m[k] in ' \t\r\n':
        k += 1
    if k >= len(m) or m[k] != '{':
        continue
    e = P.match(m, k, '{', '}')
    if e < 0:
        continue
    blocks.append((k, e, names))


def enclosing(pos):
    best = None
    for s, e, names in blocks:
        if s < pos < e and (best is None or (e - s) < (best[1] - best[0])):
            best = (s, e, names)
    return best


strips = []  # (pos, set of keys)
for mt in re.finditer(r'storedBlob\s*\(', m):
    o = mt.end() - 1
    c = P.match(m, o, '(', ')')
    args = P.split_top(m, o + 1, c)
    if len(args) >= 2:
        strips.append((mt.start(), set(re.findall(r"'(\w+)'", src[args[1][0]:args[1][1]]))))

for mt in re.finditer(r'Object\.assign\s*\(', m):
    o = mt.end() - 1
    c = P.match(m, o, '(', ')')
    args = P.split_top(m, o + 1, c)
    if len(args) < 2:
        continue
    t = [m[a:b] for a, b in args]
    if not P.is_keyed_literal(t[0]):
        continue
    later = [src[a:b].strip() for (a, b), x in zip(args[1:], t[1:]) if not P.is_literal(x)]
    if not later or re.search(r'headers|extra|base|patch|result', later[0]):
        continue
    lm = m[args[0][0]:args[0][1]]
    ia, ib = args[0][0] + lm.index('{') + 1, args[0][0] + lm.rindex('}')
    keys = []
    for a, b in P.split_top(m, ia, ib):
        km = re.match(r'\s*[\'"]?([A-Za-z_$][\w$]*)[\'"]?\s*(:|$|,)', src[a:b])
        if km:
            keys.append(km.group(1))
    blk = enclosing(mt.start())
    if not blk:
        print('%d GENERIC keys=%s <- %s' % (line_of(mt.start()), keys, later[0][:30]))
        continue
    s, e, names = blk
    # A resource's read and write are usually SEPARATE `if` blocks, so strip lists
    # are pooled by RESOURCE NAME across every block that names it, not taken from
    # the one block enclosing the read.
    union = set()
    n = 0
    for pos, ks in strips:
        sb = enclosing(pos)
        if sb and set(sb[2]) & set(names):
            union |= ks
            n += 1
    # EVERY storedBlob() call for the resource must individually cover the keys --
    # a pooled union can hide one write branch that strips nothing relevant.
    per_call = []
    for pos, ks in strips:
        sb = enclosing(pos)
        if sb and set(sb[2]) & set(names):
            per_call.append([k for k in keys if k not in ks])
    # ...and no write block for the resource may store the raw payload as the blob.
    raw_n = 0
    for bs, be, bnames in blocks:
        if set(bnames) & set(names):
            raw_n += len(re.findall(r"data:\s*(payload\b(?!\.[a-z_]+\s*[|&?])|payload\.data\b|body\b|aiScan\.redactAiFields\(\s*[\w']+\s*,\s*payload\b)", m[bs:be]))
    if n == 0:
        verdict = 'NO-STRIP'
    else:
        weak = sorted(set(k for miss in per_call for k in miss))
        if weak:
            verdict = 'WEAK-CALL missing-in-some-call=%s' % weak
        else:
            verdict = 'PAIRED'
        if raw_n:
            verdict += '+RAW-WRITE(%d)' % raw_n
    print('%d %s keys=%s <- %s  [%s, %d strip call(s)]' % (line_of(mt.start()), verdict, keys, later[0][:24], ','.join(names)[:40], n))
