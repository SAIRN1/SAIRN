"""Reclassification sweep v2 — now BIDIRECTIONAL.

v1 (2026-08-30) searched only for statutes that DEEM workers employees. It would
have missed Delaware, whose 16 Del. C. 122(3)(o)(2)(A) expressly PERMITS
independent contractors. Delaware was found by reading, not by sweeping.

v2 adds the affirmative-permission forms, and reports which polarity each hit is,
so a state that permits is not silently filed as clean.
"""
import glob
import io
import os
import re
import zipfile

DEEM = [
    r'not\s+independent\s+contractors?',
    r'shall\s+be\s+considered\s+(?:an\s+)?employ',
    r'shall\s+be\s+deemed\s+(?:to\s+be\s+)?(?:an\s+)?employ',
    r'deemed\s+(?:to\s+be\s+)?employees',
    r'considered\s+employees',
    r'shall\s+not\s+be\s+considered\s+(?:an\s+)?independent\s+contractor',
]
ROLE = [
    r'employer\s+of\s+record',
    r'co-?employer',
    r'common\s+law\s+employer',
    r'joint\s+employ',
    r'is\s+the\s+employer\s+of',
    r'managing\s+employer',
]
PERMIT = [
    r'including\s+those\s+contracts\s+with\s+individuals\s+considered\s+to\s+be\s+independent\s+contractors',
    r'(?:may|can)\s+be\s+provided\s+by\s+independent\s+contractors',
    r'(?:employees?\s+(?:of\s+the\s+\w+\s+)?or|or)\s+(?:through\s+)?contract(?:ual)?\s+arrangements?',
    r'employ\s+or\s+contract\s+with',
    r'whether\s+employed\s+or\s+contracted',
    r'employees\s+or\s+independent\s+contractors',
    r'independent\s+contractor\s+(?:status|arrangement)',
]
GROUPS = [('DEEM', DEEM), ('ROLE', ROLE), ('PERMIT', PERMIT)]
RX = [(name, re.compile('|'.join(pats), re.I)) for name, pats in GROUPS]


def text_of(path):
    low = path.lower()
    if low.endswith('.txt'):
        return io.open(path, encoding='utf-8', errors='replace').read()
    if low.endswith('.pdf'):
        try:
            from pypdf import PdfReader
            return '\n'.join((p.extract_text() or '') for p in PdfReader(path).pages)
        except Exception:
            return ''
    if low.endswith('.docx'):
        try:
            x = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8', 'replace')
            return re.sub(r'<[^>]+>', ' ', x)
        except Exception:
            return ''
    s = io.open(path, encoding='utf-8', errors='replace').read()
    s = re.sub(r'(?is)<(script|style).*?</\1>', ' ', s)
    return re.sub(r'<[^>]+>', ' ', s)


files = sorted(set(glob.glob('*.txt') + glob.glob('*.html') + glob.glob('*.pdf')
                   + glob.glob('*.docx') + glob.glob('*.out')))
print('files:', len(files))
tally = {'DEEM': 0, 'ROLE': 0, 'PERMIT': 0}
for f in files:
    if os.path.getsize(f) < 400:
        continue
    try:
        t = re.sub(r'\s+', ' ', text_of(f))
    except Exception:
        continue
    if not t:
        continue
    for name, rx in RX:
        seen = set()
        for m in rx.finditer(t):
            seg = t[max(0, m.start() - 200):m.start() + 260]
            if seg[:45] in seen:
                continue
            seen.add(seg[:45])
            tally[name] += 1
            print('\n[%s] %s :: %s' % (name, f, m.group(0)[:44]))
            print('   ' + seg)
            if len(seen) >= 2:
                break
print('\nTALLY:', tally)
