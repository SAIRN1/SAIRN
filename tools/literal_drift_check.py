"""tools/literal_drift_check.py -- find duplicated literals that have DIVERGED.

This file is a CONSUMER of the comment-quoting lesson, not an instance of it:
it blanks comments before counting (see the note above strip_comments below).
Canonical rule: docs/SAIRN-PROCESS-RULES.md section 1.2, "Grep cannot tell code
from text that describes code", which names all three tools and says it once.

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
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import defaultdict

path = sys.argv[1]
src = io.open(path, encoding='utf-8').read().replace('\r\n', '\n')

# COMMENTS ARE BLANKED BEFORE ANYTHING IS COUNTED (2026-09-11).
# This checker's whole verdict is "this literal appears in N places and
# two of them disagree", and a commented-out copy is NOT a place. It was
# counting comment prose as live literals: measured on sairnbiz.html,
# 370 literals >= 30 chars raw vs 358 with comments blanked -- TWELVE of
# them comment text, including "benefits cost is always $0 in this app"
# and "did we run payroll this period?". The dangerous case is not the
# inflated count: it is a live literal plus an out-of-date commented-out
# copy reading as two places that disagree, which is exactly the drift
# this file exists to report. Found by tools/comment_sensitivity_check.py.
#
# Offsets are PRESERVED -- the span is overwritten with spaces, not removed
# -- so every line number this file reports still points at the real file.
from comment_quote_check import strip_comments
src = strip_comments(src)

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
# ── A TOTAL ORDER, BECAUSE `key=len` ALONE LEFT SET ITERATION SHOWING THROUGH
# (2026-09-12) This was `sorted(set(...), key=len, reverse=True)`. `sorted` is
# stable, so equal-length strings kept the order they came out of the SET in --
# and set iteration order for strings depends on PYTHONHASHSEED, which varies
# between processes. Reproduced by running this file at three seeds: seeds 2 and
# 12345 disagree with seed 1.
#
# IT IS WORSE THAN THE A/B SWAP THE INDEX ROW RECORDS. The row describes "same
# lines, same ratio, opposite A/B labels", which is harmless. Measured here, the
# PAIR NUMBERING moves too: at one seed `pair 5` is 63-vs-52 chars at ratio
# 0.904, at another it is 63-vs-42 at 0.800 -- a different finding under the
# same label. Anything that cites a pair number, or diffs two runs of this
# checker, is reading noise.
#
# Sorting by (-len, text) is a total order over distinct strings, so the result
# no longer depends on anything the interpreter is free to vary.
uniq = sorted(set(t for _, t in prose), key=lambda t: (-len(t), t))
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
# ── WHAT THIS TOOL GATES, AND WHAT IT ONLY REPORTS (decided 2026-09-13) ─────
# It was promoted on 2026-09-10 with `'verdict': by_exit` in
# tools/report_only_checks.py and had NO sys.exit at all, so it could never
# report a finding through the registry that ran it, whatever it printed. Its
# evidence line -- "0 findings" -- is what a deaf checker looks like.
#
# THE FIX WAS NOT A TYPO, WHICH IS WHY IT WAS DECIDED RATHER THAN PATCHED.
# Measured across every app file before choosing: 126 near-duplicate prose
# pairs and 14 fact divergences, of which the fact half is DOMINATED by demo
# phone numbers and demo city names. This file's own header says it: "A HIT IS
# A TRIAGE SIGNAL, NEVER PROOF -- demo phone numbers and repeated error strings
# dominate the raw output and are fine." Gating all of that is how a checker
# earns being routed around.
#
# GATED: the entity name, and section C. Those are invariants, not samples --
# one company has one legal name, and one label has one value. On the real tree
# they fire on exactly two files (stonedesk.html 23x "SAIRN Tech LLC" vs 17x
# "SAIRN Technologies", sairnscape.html 3x vs 1x), which is a real and
# previously-known inconsistency.
#
# REPORT-ONLY: everything else, printed exactly as before. A person reading the
# output loses nothing; the push gate stops crying wolf.
GATED_FACTS = ('entity name',)
gated = []

for name, pat in FACTS.items():
    vals = defaultdict(list)
    for m in re.finditer(pat, src):
        v = m.group(0)
        vals[v].append(src.count('\n', 0, m.start()) + 1)
    if len(vals) > 1:
        if name in GATED_FACTS:
            gated.append('%s: %d distinct values' % (name, len(vals)))
        print('  !! %-15s %d distinct values%s'
              % (name, len(vals), '   [GATED]' if name in GATED_FACTS else ''))
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
# WORD BOUNDARIES ON THE KEY NAMES (2026-09-13). Without them `l:'` matches the
# TAIL of `email:'...'` and `s:'` the tail of `address:'...'` / `status:'...'`,
# so this paired a customer's email with an unrelated key's value from
# somewhere else in the same object literal. Measured across every app file:
# 69 matches before, 4 after -- SIXTY-FIVE of them substring artifacts, and the
# only section C finding on the whole platform was one of them
# (`Install -> ['Sales', 'Sales Visit']`, three unrelated dictionaries).
# Found while gating this section, which could not have been done on top of it.
for m in re.finditer(r"(?<![\w$])l:'([^']{3,28})'[^}]*?(?<![\w$])s:'([^']{1,70})'",
                     src):
    pairs[m.group(1).strip()].add(m.group(2).strip())
hits = {k: v for k, v in pairs.items() if len(v) > 1}
if not hits:
    print('  none')
for k, v in sorted(hits.items()):
    gated.append('label %r has %d values' % (k, len(v)))
    print('  !! %-24s -> %s   [GATED]' % (k, sorted(v)[:4]))

# ── THE EXIT CODE ────────────────────────────────────────────────────────────
# It is read by tools/report_only_checks.py with by_exit, which looks at the
# return code and NOTHING else. Until today there was no sys.exit here at all.
# Held in both directions by tests/run_literal_drift_control_probe.py, and the
# class is guarded by arm E3 of tests/run_report_only_checks_probe.py.
print('')
if gated:
    print('GATED FINDINGS:%d -- %s' % (len(gated), '; '.join(gated)))
    print('An entity name and a label are INVARIANTS: one company has one legal')
    print('name, one label has one value. Everything else above is report-only')
    print('and does not affect this exit code -- read it, do not gate on it.')
else:
    print('GATED FINDINGS:0 -- the gated set is the entity name and section C.')
    print('Anything printed above under another heading is a TRIAGE SIGNAL and')
    print('was deliberately not gated: demo phone numbers and demo city names')
    print('dominate it, and a checker that cries wolf is one nobody reads.')
sys.exit(1 if gated else 0)
