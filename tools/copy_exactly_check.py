"""copy_exactly_check.py -- does the must-copy-exactly block still match the app?

    python tools/copy_exactly_check.py
    python tools/copy_exactly_check.py --json

── WHAT THIS IS FOR ───────────────────────────────────────────────────────
`docs/2026-09-13-cross-domain-disciplines.md` section 7 says propagating a
proven pattern needs the TARGET re-qualified -- scale, input range, criticality
tier -- and not merely a diff proving the bytes match. Auditing that on
2026-09-14 turned up a prior question nobody was asking:

    IS THE SOURCE STILL RIGHT?

`SAIRNVET-FINAL-SPEC.md` carries the one literal "SAIRN CLAUDE ENGINE -- Copy
Exactly" block on this platform. Measured that day: of its five functions,
ZERO were byte-identical to what `sairnvet.html` actually runs, one differed
only in line wrapping, and FOUR differed in substance -- every one of them
because the APP had been fixed and the spec had not. The sharpest:

    spec : function svStore(k,v){try{localStorage.setItem('sv_'+k,
                                 JSON.stringify(v));}catch(e){}}
    app  : function svStore(k,v){return st('sv_'+k,v);}

The spec still ships a storage wrapper that swallows its own failure. The app
routed it through the honest one months ago. **Anyone who copied that block into
a new app today would reintroduce a silent-failure write**, which is the defect
class this platform has spent the most time removing.

So a Copy-Exactly block is not only a propagation aid, it is a propagation
VECTOR, and nothing was watching it.

── FOUR STATES, NEVER COLLAPSED ───────────────────────────────────────────
  identical   the bytes match
  reflowed    the same code, wrapped differently. NOT DRIFT. Three false
              alarms on this platform came from calling a whitespace
              difference a change (CRLF, 2026-09-03), and a checker that
              reports a re-wrapped line trains people to ignore it.
  differs     the stripped bodies are not the same code
  absent      the function is not in the app at all

── WHAT IT DELIBERATELY DOES NOT DO ───────────────────────────────────────
It does NOT answer section 7's actual question. Scale, input range and tier
cannot be read off a diff -- the disciplines doc says so itself and calls for
"a refusal to propagate without a recorded answer to each", not an automatic
verdict. This tool answers the narrower, mechanical half: whether the thing
being copied still matches the thing it was copied from. The re-qualification
half is UNBUILT, and saying that here is the point: a green run from this tool
means the bytes agree, and agreeing bytes are exactly what section 7 warns is
not safety.

REPORT ONLY. Exit 0 on drift, 2 on could-not-check.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = 'SAIRNVET-FINAL-SPEC.md'
APP = 'sairnvet.html'
HEADING = 'Copy Exactly'


def read(rel):
    p = os.path.join(REPO, rel.replace('/', os.sep))
    if not os.path.isfile(p):
        return None
    return io.open(p, encoding='utf-8', errors='replace').read()


def spec_block(src):
    i = src.find(HEADING)
    if i < 0:
        return None
    j = src.find('```javascript', i)
    if j < 0:
        return None
    k = src.find('```', j + 3)
    if k < 0:
        return None
    return src[j + len('```javascript'):k]


def functions(text):
    """name -> body, brace-matched. Not a JS parse; see the limit below."""
    out = {}
    for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*)\s*\(', text):
        b = text.find('{', m.end() - 1)
        if b < 0:
            continue
        depth, k = 0, b
        for k in range(b, len(text)):
            if text[k] == '{':
                depth += 1
            elif text[k] == '}':
                depth -= 1
                if not depth:
                    break
        else:
            continue
        out[m.group(1)] = text[b:k + 1]
    return out


def tight(x):
    return re.sub(r'\s+', '', x)


def classify(spec_fns, app_fns):
    rows = []
    for name in sorted(spec_fns):
        if name not in app_fns:
            rows.append((name, 'absent'))
        elif app_fns[name] == spec_fns[name]:
            rows.append((name, 'identical'))
        elif tight(app_fns[name]) == tight(spec_fns[name]):
            rows.append((name, 'reflowed'))
        else:
            rows.append((name, 'differs'))
    return rows


def main(argv):
    spec_src = read(SPEC)
    app_src = read(APP)
    # FAIL CLOSED. A missing file is a third state and is never a pass: PR 1.11.
    if spec_src is None:
        print('COULD NOT CHECK: %s is not in this clone. Not a pass.' % SPEC)
        return 2
    if app_src is None:
        print('COULD NOT CHECK: %s is not in this clone. Not a pass.' % APP)
        return 2
    block = spec_block(spec_src)
    if block is None:
        print('COULD NOT CHECK: no fenced javascript block under a %r heading '
              'in %s. The block may have been renamed or removed -- either way '
              'this tool is no longer looking at anything.' % (HEADING, SPEC))
        return 2

    spec_fns = functions(block)
    if not spec_fns:
        print('COULD NOT CHECK: the Copy-Exactly block defines no functions. '
              'ZERO TARGETS IS NOT A CLEAN SWEEP.')
        return 2
    app_fns = functions(app_src)
    rows = classify(spec_fns, app_fns)
    counts = {}
    for _, v in rows:
        counts[v] = counts.get(v, 0) + 1

    if '--json' in argv:
        print(json.dumps({'spec': SPEC, 'app': APP,
                          'functions': dict(rows), 'counts': counts}, indent=1))
        return 0

    print('COPY-EXACTLY DRIFT CHECK -- report only, nothing was written')
    print('  source: %s  ->  target: %s' % (SPEC, APP))
    print('  functions in the block: %d' % len(spec_fns))
    print('')
    for name, verdict in rows:
        note = {'identical': '',
                'reflowed': 'same code, wrapped differently -- NOT drift',
                'differs': '<- the block would reintroduce this if copied today',
                'absent': '<- not in the app at all'}[verdict]
        print('  %-12s %-10s %s' % (name, verdict, note))
    print('')
    print('  identical %d | reflowed %d | DIFFERS %d | absent %d'
          % (counts.get('identical', 0), counts.get('reflowed', 0),
             counts.get('differs', 0), counts.get('absent', 0)))
    if counts.get('differs') or counts.get('absent'):
        print('')
        print('  A BLOCK LABELLED "COPY EXACTLY" THAT NO LONGER MATCHES ITS OWN')
        print('  APP IS A PROPAGATION VECTOR. Whoever copies it next inherits')
        print('  whatever the app has since fixed and the document has not.')
    print('')
    print('  THIS DOES NOT ANSWER DISCIPLINES 7. Scale, input range and')
    print('  criticality tier cannot be read off a diff; this checks only that')
    print('  the bytes still agree, and agreeing bytes are precisely what')
    print('  section 7 warns is not safety.')
    print('')
    print('  LIMIT: functions are found by regex and brace matching, not by a')
    print('  JS parse. A function expression assigned to a var, or one whose')
    print('  body contains a brace inside a string or regex literal, is a shape')
    print('  this cannot see -- the same blind-spot class that let tesseract.js')
    print('  sit unregistered in the SOUP register.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
