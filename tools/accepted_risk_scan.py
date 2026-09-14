"""accepted_risk_scan.py -- risk ACCEPTANCES that live in a comment and nowhere else.

    python tools/accepted_risk_scan.py
    python tools/accepted_risk_scan.py --json

── WHY ────────────────────────────────────────────────────────────────────
2026-09-14: `api/sairncash/portal.js` carries, in its own header, a deliberate
and well-reasoned acceptance -- *"possession of a subscription id still gets you
a portal ... recorded here rather than left to be discovered."* It was recorded
in the FILE and in nothing else. It reached neither `docs/SAIRN-OPEN-WORK-INDEX.md`
nor `docs/SOUP-REGISTER.md`, so it was invisible to anyone not reading that one
file -- and it was consequently mistaken for an UNRECOGNISED gap twice in one
afternoon, by me, after I had read the paragraph above it.

**An accepted risk that only one file knows about is indistinguishable from an
unnoticed one.** That is the same information-leakage shape as item 94 one level
up: the knowledge existed and no register owned it.

── WHAT THIS IS ───────────────────────────────────────────────────────────
A LOCATOR, not a detector. It finds comment blocks whose language says somebody
weighed a risk and chose to live with it, and reports whether anything
resembling that file appears in a central register. It cannot read intent and it
will over-report: "deliberate" and "on purpose" are also how this codebase
explains correct decisions that carry no residual risk at all.

So the output is a READ-LIST ordered by how strongly the language commits, and
the count is not a score. Driving it to zero would mean deleting comments.

── THE CROSS-CHECK IS DELIBERATELY WEAK, AND SAYS SO ──────────────────────
"Is this in a register" is answered by looking for the FILE PATH or its basename
in the index and the SOUP register. A risk described there in prose without
naming the file reads here as ABSENT. That is a false positive in the
conservative direction -- it asks a human to look -- and the alternative,
matching prose to prose, is the word-overlap scoring that returned 38% with five
false positives out of five.

REPORT ONLY. Exit 0 with findings, 2 when it could not look.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTERS = [os.path.join('docs', 'SAIRN-OPEN-WORK-INDEX.md'),
             os.path.join('docs', 'SOUP-REGISTER.md'),
             os.path.join('docs', 'ACCEPTED-RISKS.md')]

# Ordered strongest first. The phrase that matched is reported, because "this
# file says `recorded here rather than`" is actionable and "score 3" is not.
PHRASES = [
    (3, r'recorded here rather than'),
    (3, r'accepted (?:risk|as[- ]is|and recorded)'),
    (3, r'we accept\b|is accepted\b'),
    (3, r'not a perfect (?:gate|guard|check)'),
    (3, r'live with (?:it|this)'),
    (2, r'known limitation'),
    (2, r'is not fixed (?:here|now)|left unfixed'),
    (2, r'stated rather than (?:implied|hidden|fixed)'),
    (2, r'honest limit'),
    (2, r'nothing bounds (?:it|this)'),
    (2, r'is a real (?:credential|risk|exposure)'),
    (1, r'deliberately not|NOT fixed'),
    (1, r'on purpose\b'),
]

# Files that are ABOUT risk acceptance rather than instances of one.
SKIP_DIRS = ('node_modules', '.git', 'archive', 'docs', 'dist')


def read(rel):
    p = os.path.join(REPO, rel.replace('/', os.sep))
    if not os.path.isfile(p):
        return None
    return io.open(p, encoding='utf-8', errors='replace').read()


def register_text():
    """All register text, or None if none of them can be read."""
    parts = []
    for r in REGISTERS:
        t = read(r)
        if t is not None:
            parts.append(t)
    return '\n'.join(parts) if parts else None


def sources():
    out = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for f in files:
            if not (f.endswith('.js') or f.endswith('.html') or f.endswith('.sql')):
                continue
            if f.endswith('.test.js'):
                continue
            rel = os.path.relpath(os.path.join(root, f), REPO).replace(os.sep, '/')
            out.append(rel)
    return sorted(out)


def main(argv):
    regs = register_text()
    if regs is None:
        print('COULD NOT CHECK: none of %s is readable, so "is it registered" '
              'cannot be answered and every file would look unregistered. Not a '
              'pass.' % ', '.join(REGISTERS))
        return 2
    files = sources()
    if not files:
        print('COULD NOT CHECK: no source files found. ZERO TARGETS IS NOT A '
              'CLEAN SWEEP.')
        return 2

    rows = []
    for rel in files:
        src = read(rel)
        if src is None:
            continue
        hits = []
        for weight, pat in PHRASES:
            m = re.search(pat, src, re.I)
            if m:
                hits.append((weight, m.group(0)))
        if not hits:
            continue
        base = os.path.basename(rel)
        registered = (rel in regs) or (base in regs)
        rows.append({'file': rel, 'weight': max(h[0] for h in hits),
                     'phrases': sorted(set(h[1].lower() for h in hits))[:4],
                     'registered': registered})

    rows.sort(key=lambda r: (-r['weight'], r['registered'], r['file']))
    unreg = [r for r in rows if not r['registered']]

    if '--json' in argv:
        print(json.dumps({'rows': rows, 'unregistered': len(unreg)}, indent=1))
        return 0

    print('ACCEPTED-RISK SCAN -- report only, nothing was written')
    print('  source files read            : %d' % len(files))
    print('  carrying acceptance language : %d' % len(rows))
    print('  of those, the file is NOT named in any register: %d' % len(unreg))
    print('')
    print('  A COUNT IS NOT A SCORE AND ZERO IS NOT THE GOAL. "deliberately"')
    print('  and "on purpose" are also how this codebase explains correct')
    print('  decisions with no residual risk; driving this to zero would mean')
    print('  deleting comments. Read the weight-3 rows.')
    print('')
    for w in (3, 2, 1):
        sel = [r for r in unreg if r['weight'] == w]
        if not sel:
            continue
        print('  WEIGHT %d -- unregistered (%d)' % (w, len(sel)))
        for r in sel[:14]:
            print('    %-44s %s' % (r['file'][:44], '; '.join(r['phrases'])[:60]))
        if len(sel) > 14:
            print('    ... and %d more' % (len(sel) - 14))
        print('')
    print('  THE CROSS-CHECK IS WEAK BY DESIGN: "registered" means the file path')
    print('  or its basename appears in a register. A risk described there in')
    print('  prose without naming the file reads as UNREGISTERED here. That is a')
    print('  false positive in the direction that asks a human to look, and the')
    print('  alternative -- matching prose to prose -- is the word-overlap')
    print('  scoring that returned 38% with five false positives out of five.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
