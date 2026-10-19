# docs/b26-logs/guard_census.py
# OWNER: cody   batch b26   2026-10-19
#
# THE CONCEPT: a bulk conversion is safe exactly as far as the property the
#   script checked, so before ANY guard is rewritten every one of them is
#   enumerated with the four facts a conversion depends on -- the response
#   variable, whether its body was ALREADY CONSUMED upstream, the exact answer
#   the branch sends today, and the exact byte span that would be replaced --
#   and any site missing one of those four is reported as a THIRD STATE rather
#   than converted on a guess.
#
#   python docs/b26-logs/guard_census.py            # summary
#   python docs/b26-logs/guard_census.py --shapes   # every distinct answer shape
#   python docs/b26-logs/guard_census.py --list <class>
#
# This is the MEASUREMENT step. It writes nothing.
#
# WHY THE PRE-READ FACT IS THE ONE THAT MATTERS: api/sd-data.js:19628 records
# that the FIRST draft of the notProvisioned() rollout broke five call sites
# that had already done `await r.json()` before the status guard -- a helper
# calling r.text() on a consumed stream got '' and classified a genuine 404 as
# UNCLASSIFIABLE, turning one wrong diagnosis into a different wrong one. The
# comment's own conclusion: "a bulk edit is safe exactly as far as the property
# the script checked, and the script checked INSIDE the branch and not what
# came before it." So this census looks UPSTREAM of every guard, inside the
# enclosing function, and that is the whole reason it exists.

import io
import os
import re
import sys
import json

SRC = 'api/sd-data.js'
if not os.path.isfile(SRC):
    print('COULD NOT RUN: ' + SRC + ' is not here. Nothing was measured.')
    sys.exit(2)

src = io.open(SRC, encoding='utf-8').read().replace('\r\n', '\n')
lines = src.split('\n')

GUARD = re.compile(r'if \((\w+)\.status === 404 \|\| \1\.status === 400\) \{')


def line_of(idx):
    return src.count('\n', 0, idx) + 1


def balanced(start):
    """Byte span of the `{ ... }` block whose `{` is at or after `start`.

    A TERMINATOR IS A GUESS ABOUT WHAT COMES NEXT; A BALANCED BRACE IS A
    PROPERTY OF THE BLOCK ITSELF. The misclass suite paid for the other way
    round -- a `\\n    if (resource === ` terminator overran by a factor of
    130 and a precondition arm then reported a shipped defect as fixed.
    """
    j = src.index('{', start)
    depth = 0
    k = j
    while k < len(src):
        c = src[k]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return j, k + 1
        k += 1
    return None


# ── THE ENCLOSING FUNCTION, FOUND BY SCANNING BACKWARDS ────────────────────
# The pre-read question is "did anything consume this response's body between
# where it was assigned and this guard", and the honest window for that is
# FROM THE ASSIGNMENT, not a fixed number of lines. So the assignment is
# located by searching backwards for `const <var> = await fetch(` /
# `<var> = await fetch(` and the window is assignment -> guard.
def preread_state(var, gstart):
    """('none'|'json'|'text'|'UNKNOWN', assignment line or None, snippet)"""
    pats = [
        re.compile(r'\b(?:const|let|var)\s+' + re.escape(var)
                   + r'\s*=\s*await\s+fetch\('),
        re.compile(r'\b' + re.escape(var) + r'\s*=\s*await\s+fetch\('),
    ]
    best = -1
    for p in pats:
        for m in p.finditer(src, 0, gstart):
            if m.start() > best:
                best = m.start()
    if best < 0:
        return 'UNKNOWN', None, ''
    window = src[best:gstart]
    # Only a read OF THIS VARIABLE counts. `await other.json()` in between is
    # somebody else's stream and must not be mistaken for this one's.
    j = re.search(r'await\s+' + re.escape(var) + r'\s*\.\s*json\s*\(', window)
    t = re.search(r'await\s+' + re.escape(var) + r'\s*\.\s*text\s*\(', window)
    if j and t:
        return 'BOTH', line_of(best), window[-200:]
    if j:
        return 'json', line_of(best), window[-200:]
    if t:
        return 'text', line_of(best), window[-200:]
    return 'none', line_of(best), window[-200:]


def classify(body):
    """What the branch ANSWERS today, from its own text."""
    if re.search(r'\bnotProvisioned(Text)?\s*\(\s*res\s*,', body):
        return 'HELPER'
    if 'SCHEMA_OUTDATED' in body:
        return 'HELPER'
    has503 = re.search(r'status\(503\)', body) and 'NOT_PROVISIONED' in body
    has200 = re.search(r'status\(200\)', body) and 'provisioned: false' in body
    if has503 and has200:
        return 'BOTH503AND200'
    if has503:
        return 'RAW503'
    if has200:
        return 'RAW200'
    return 'OTHER'


rows = []
for m in GUARD.finditer(src):
    var = m.group(1)
    span = balanced(m.start())
    if span is None:
        rows.append({'line': line_of(m.start()), 'var': var,
                     'cls': 'UNSLICEABLE', 'pre': 'UNKNOWN',
                     'assign': None, 'body': '', 'start': m.start(),
                     'end': None})
        continue
    bstart, bend = span
    body = src[bstart:bend]
    pre, aline, _ = preread_state(var, m.start())
    rows.append({'line': line_of(m.start()), 'var': var,
                 'cls': classify(body), 'pre': pre, 'assign': aline,
                 'body': body, 'start': m.start(), 'end': bend})

by_cls = {}
for r in rows:
    by_cls.setdefault(r['cls'], []).append(r)

print('GUARD CENSUS -- ' + SRC + ', ' + str(len(lines)) + ' lines')
print('shape: `if (X.status === 404 || X.status === 400) {`')
print('total guard sites: ' + str(len(rows)))
print('')
print('  CLASS            n     pre-read: none  json  text  BOTH  UNKNOWN')
for cls in sorted(by_cls, key=lambda c: -len(by_cls[c])):
    g = by_cls[cls]
    c = {}
    for r in g:
        c[r['pre']] = c.get(r['pre'], 0) + 1
    print('  %-16s %4d              %4d  %4d  %4d  %4d  %4d'
          % (cls, len(g), c.get('none', 0), c.get('json', 0), c.get('text', 0),
             c.get('BOTH', 0), c.get('UNKNOWN', 0)))

print('')
print('CONVERTIBLE = RAW503 (write side) + RAW200 (read side).')
print('  RAW503 ' + str(len(by_cls.get('RAW503', []))) + '   RAW200 '
      + str(len(by_cls.get('RAW200', []))) + '   -> '
      + str(len(by_cls.get('RAW503', [])) + len(by_cls.get('RAW200', [])))
      + ' sites')
print('NOT CONVERTIBLE WITHOUT A HUMAN, and NOT folded into either:')
for cls in ('OTHER', 'BOTH503AND200', 'UNSLICEABLE'):
    if by_cls.get(cls):
        print('  ' + cls + ': ' + str(len(by_cls[cls])) + ' -- lines '
              + ', '.join(str(r['line']) for r in by_cls[cls][:40]))
unk = [r for r in rows if r['pre'] == 'UNKNOWN']
print('  pre-read UNKNOWN (no `= await fetch(` found upstream): '
      + str(len(unk))
      + (' -- lines ' + ', '.join(str(r['line']) for r in unk[:40])
         if unk else ''))

if '--shapes' in sys.argv:
    # ── EVERY DISTINCT ANSWER SHAPE, because the converter has to reproduce
    #    them and "they are all `{ok:true,data:[],provisioned:false}`" is an
    #    assumption until it is counted.
    print('')
    print('DISTINCT RAW200 ANSWER SHAPES (the literal sent today):')
    shapes = {}
    for r in by_cls.get('RAW200', []):
        s = re.search(r'status\(200\)\.json\((\{[^;]*?\})\)\s*;', r['body'])
        key = re.sub(r'\s+', ' ', s.group(1)) if s else '<<UNMATCHED>>'
        shapes.setdefault(key, []).append(r['line'])
    for k in sorted(shapes, key=lambda k: -len(shapes[k])):
        print('  %4d  %s' % (len(shapes[k]), k[:150]))
        if k == '<<UNMATCHED>>':
            print('        lines: ' + ', '.join(str(x) for x in shapes[k][:60]))
    print('')
    print('DISTINCT RAW503 MESSAGE-ARGUMENT SHAPES:')
    shapes = {}
    for r in by_cls.get('RAW503', []):
        s = re.search(r"status\(503\)\.json\(\{\s*error:\s*\{\s*code:\s*'NOT_PROVISIONED',\s*message:\s*([\s\S]*?)\s*\}\s*\}\)\s*;", r['body'])
        key = 'MATCHED' if s else '<<UNMATCHED>>'
        shapes.setdefault(key, []).append(r['line'])
    for k in sorted(shapes, key=lambda k: -len(shapes[k])):
        print('  %4d  %s' % (len(shapes[k]), k))
        if k == '<<UNMATCHED>>':
            print('        lines: ' + ', '.join(str(x) for x in shapes[k][:60]))

if '--list' in sys.argv:
    want = sys.argv[sys.argv.index('--list') + 1]
    print('')
    for r in by_cls.get(want, []):
        print('%6d  var=%-10s pre=%-7s assign=%s'
              % (r['line'], r['var'], r['pre'], r['assign']))

if '--json' in sys.argv:
    io.open('docs/b26-logs/guard_census.json', 'w', encoding='utf-8').write(
        json.dumps([{k: v for k, v in r.items() if k != 'body'} for r in rows],
                   indent=1))
    print('\nwrote docs/b26-logs/guard_census.json')

sys.exit(0)
