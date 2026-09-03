"""tools/literal_drift_check.py -- find duplicated literals that have DIVERGED.

Promoted from a scratch script to a real tool on 2026-09-03, after THREE drift
bugs surfaced in stonedesk.html in a single session and Michael called it a
pattern rather than three coincidences. A fourth turned up the moment this pass
ran. Run it against any single-file SAIRN app:

    python tools/literal_drift_check.py stonedesk.html

WHAT DRIFT LOOKS LIKE HERE, from the real cases:
  1. THE PREFIX. Two copies of the base system prompt, 1,793 vs 2,086 chars,
     identical up to the shorter one's end -- one had been corrected and the
     other had not. The live Drawing Tool used the stale copy.
  2. THE NUMBER IN PROSE. The printed cut sheet recomputed the on-screen
     figures and dropped every caveat. No literal comparison can see that; only
     a fact-level check can.
  3. THE SHORT COPY. "Cuyahoga County" in a long governing-law clause AND in a
     one-line summary bullet six lines above it. A 120-char threshold missed it.
  4. THE PRICE LIST. The customer-facing agreement offers Founding/Solo/Pro/Shop
     at 199/299/499/799 while the internal price book quotes
     Starter/Professional/Enterprise at 199/299/599.

So this runs three passes, not one. A HIT IS A TRIAGE SIGNAL, NEVER PROOF --
demo phone numbers and repeated error strings dominate the raw output and are
fine. Read every line before acting on it.
"""

import io, re, sys, difflib
from collections import defaultdict

path = sys.argv[1]
src = io.open(path, encoding='utf-8').read().replace('\r\n', '\n')

blocks = [(m.start(1), m.group(1)) for m in
          re.finditer(r'<script\b[^>]*>(.*?)</script>', src, re.S | re.I)]

LIT = re.compile(r'''(?<![\w$])(?:"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)')''')

# A literal is MARKUP/CSS noise if it is mostly tags, properties or selectors.
NOISE = re.compile(r'(style=|padding:|margin:|border:|display:|font-size:|'
                   r'background:|color:#|width:|height:|flex|grid-template|'
                   r'border-radius:|<div|<td|<th|<tr|<span|<button|<option)', re.I)

def is_prose(t):
    if NOISE.search(t):
        return False
    letters = sum(c.isalpha() or c == ' ' for c in t)
    return letters / max(len(t), 1) > 0.75

lits = []
for base, body in blocks:
    for m in LIT.finditer(body):
        t = m.group(1) if m.group(1) is not None else m.group(2)
        if t is None or len(t) < 30:
            continue
        line = src.count('\n', 0, base + m.start()) + 1
        lits.append((line, t))

prose = [(l, t) for l, t in lits if is_prose(t)]
print('literals >= 30 chars: %d   of which prose: %d' % (len(lits), len(prose)))

by_text = defaultdict(list)
for line, t in prose:
    by_text[t].append(line)

print('\n=== A1. EXACT PROSE DUPLICATES ===')
ex = {t: ls for t, ls in by_text.items() if len(ls) > 1}
if not ex:
    print('  none')
for t, ls in sorted(ex.items(), key=lambda kv: -len(kv[0]))[:25]:
    print('  %4d chars x%d  lines %s' % (len(t), len(ls), ls[:6]))
    print('       %s' % t[:120])

print('\n=== A2. NEAR-DUPLICATE PROSE (similar, NOT identical) ===')
uniq = sorted(set(t for _, t in prose), key=len, reverse=True)
found = 0
for i, a in enumerate(uniq):
    for b in uniq[i + 1:]:
        if len(b) < len(a) * 0.5:
            break
        head = min(30, len(b))
        if a[:head] != b[:head]:
            continue
        r = difflib.SequenceMatcher(None, a, b).ratio()
        if r < 0.75:
            continue
        found += 1
        pre = a.startswith(b) or b.startswith(a)
        print('\n  pair %d: %d vs %d chars, ratio %.3f%s' %
              (found, len(a), len(b), r, '   *** PREFIX -- THE BASE-PROMPT SHAPE ***' if pre else ''))
        print('     A line(s) %s' % by_text[a][:4])
        print('     B line(s) %s' % by_text[b][:4])
        sm = difflib.SequenceMatcher(None, a, b)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                continue
            print('     first diff @%d  A=%r  B=%r' % (i1, a[i1:i1+70], b[j1:j1+70]))
            break
if not found:
    print('  none')

print('\n=== B. FACT DIVERGENCE (a fact with more than one value) ===')
FACTS = {
    'county':        r'\b([A-Z][a-z]+) County\b',
    'ohio city':     r'\b(Westlake|Orrville|Columbus|Cleveland|Akron|Cuyahoga Falls)\b',
    'entity name':   r'\bSAIRN (?:Technologies LLC|Tech LLC|Technologies™|Technologies)\b',
    'business email': r'\b([A-Za-z0-9._%+-]+@sairn\.com)\b',
    'phone':         r'\((\d{3})\)\s?\d{3}-\d{4}',
    'tier price':    r'\$(199|299|599)/mo',
    'thh rate':      r'(\d+(?:\.\d+)?)hr per 50\s?sqft',
    'slab default':  r'(\d+)\s*sqft per slab',
    'waste pct':     r'(\d{2})% waste allowance',
}
for name, pat in FACTS.items():
    vals = defaultdict(list)
    for m in re.finditer(pat, src):
        v = m.group(0)
        vals[v].append(src.count('\n', 0, m.start()) + 1)
    if len(vals) > 1:
        print('  !! %-15s %d distinct values' % (name, len(vals)))
        for v, ls in sorted(vals.items(), key=lambda kv: -len(kv[1])):
            print('       %-32s x%-3d lines %s' % (v[:32], len(ls), ls[:6]))
    elif vals:
        v = list(vals)[0]
        print('  ok %-15s one value: %-30s x%d' % (name, v[:30], len(vals[v])))
    else:
        print('  -- %-15s not present' % name)

print('\n=== C. SAME LABEL, DIFFERENT VALUE ===')
pairs = defaultdict(set)
for m in re.finditer(r'>([A-Z][A-Za-z ()/]{3,28})</span><span class="rv">([^<]{1,60})<', src):
    pairs[m.group(1).strip()].add(m.group(2).strip())
for m in re.finditer(r"l:'([^']{3,28})'[^}]*?s:'([^']{1,70})'", src):
    pairs[m.group(1).strip()].add(m.group(2).strip())
hits = {k: v for k, v in pairs.items() if len(v) > 1}
if not hits:
    print('  none')
for k, v in sorted(hits.items()):
    print('  !! %-24s -> %s' % (k, sorted(v)[:4]))
