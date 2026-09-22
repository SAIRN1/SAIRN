r"""Scanned-document text must be redacted BEFORE it is stored, on the server.

Run: python tests/mech_docs_redaction_wiring_probe.py

WHAT WAS WRONG. `sairnmechanical.html`'s `scanDoc()` asks the model, in its own
words, to "EXTRACT: Every field -- names, dates, amounts, codes, reference
numbers" off work orders, maintenance contracts, permits, inspection reports
and INVOICES. `saveDoc()` stored that answer VERBATIM and `mechPushRecord`
synced it to `mech_docs`. Nothing redacted anything, and the toast said "Saved
on this device" while the line above it pushed to a server.

THREE THINGS THIS ASSERTS, and the third is the one a unit suite cannot:

  * the SERVER redacts on the write path -- `api/_lib/mech-redact.js` is pure
    and 17 arms drive it, but a pure function nothing calls protects nothing,
    and this is the fourth time that shape has been paid for on this platform.
  * the client copy is redacted too, and the client and server rules AGREE.
    Two implementations of one rule set is a second answer unless something
    compares them, and a single-file HTML app cannot require() the module.
  * NO LITERAL BACKSPACE SURVIVES IN EITHER REDACTOR. This is not theoretical:
    the first version of the client function was written through a heredoc,
    every `\b` was consumed as a 0x08 BACKSPACE, and five of its six rules
    could never match while LOOKING correct in any editor that renders 0x08 as
    nothing. That is the exact defect CLAUDE.md records -- "a regex that
    shipped with a literal backspace and could never match" -- and it was
    caught by the parity arm below, not by reading.

AND ONE IT DELIBERATELY DOES NOT ASSERT: that the text is anonymous. A name in
ordinary prose survives this pass, by design and by disclosure. An arm that
demanded otherwise would be demanding a guarantee the code does not make.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, 'sairnmechanical.html')
HANDLER = os.path.join(REPO, 'api', 'sd-data.js')
MODULE = os.path.join(REPO, 'api', '_lib', 'mech-redact.js')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:500]))
    if not cond:
        fails.append(name)


def strip_comments(js):
    """Blank // and /* */ spans, string-aware, preserving length."""
    out = list(js)
    i, n = 0, len(js)
    while i < n:
        c = js[i]
        if c in '\'"`':
            q, i = c, i + 1
            while i < n:
                if js[i] == '\\':
                    i += 2
                    continue
                if js[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == '/' and i + 1 < n and js[i + 1] == '/':
            while i < n and js[i] != '\n':
                out[i] = ' '
                i += 1
            continue
        if c == '/' and i + 1 < n and js[i + 1] == '*':
            j = js.find('*/', i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
            continue
        i += 1
    return ''.join(out)


def function_body(src, name):
    """The text of `function <name>(...){...}`, by brace matching.

    ── ANCHORED ON THE CONSTRUCT, NOT ON THE FILE ─────────────────────────
    Arms 3, 6 and 7 first searched the whole file and all three were WRONG
    about correct code. `Saved on this device` is still in the file and always
    should be -- it belongs to `saveTakeoff`, a different function that syncs
    nothing. And the comment this change added to `saveDoc` QUOTES the old
    toast in order to explain why it is gone, so a file-wide absence check
    flagged its own explanation.

    Same lesson as the confidentiality flagger earlier today: a window that can
    reach the declaration next door measures proximity, not ownership. This
    takes the function.
    """
    i = src.find('function ' + name)
    if i == -1:
        return ''
    j = src.find('{', i)
    if j == -1:
        return ''
    depth, k, quote = 0, j, None
    while k < len(src):
        c = src[k]
        if quote:
            if c == '\\':
                k += 2
                continue
            if c == quote:
                quote = None
        elif c in '\'"`':
            quote = c
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
        k += 1
    return src[i:]


CASES = [
    'Contact j.smith@acme-hvac.com for access.',
    'Call (440) 555-0100 on arrival.',
    'SSN 123-45-6789 EIN 12-3456789',
    'Paid with 4111 1111 1111 1111.',
    'Site: 1425 Lakeshore Blvd, Suite 200',
    'Customer: Eleanor Whitfield\nTechnician: D. Okoye\nUnit: Carrier 58MVC',
    'Unit Carrier 58MVC080-F-1-20, filter 16x25x1.',
    'Serial 4405550100 on the data plate.',
    'Compressor serial 1234567890123456789012.',
    'EPA 608 Type II cert 608-II-2026-00417.',
    'Total $12,480.00, deposit $3,000.',
    'Spoke to Dave about the condenser.',
]

SERVER_CALL = re.compile(r'mechRedact\s*\.\s*redactDocumentText\s*\(')
CLIENT_CALL = re.compile(r'\bmechRedactLocal\s*\(')


def parity(app_src, module_path):
    """Run the CLIENT function and the SERVER module on the same inputs."""
    m = re.search(r'function mechRedactLocal\(text\)\{.*?\n\}', app_src, re.S)
    if not m:
        return None, 'mechRedactLocal not found in the app'
    harness = (m.group(0) + '\n'
               + 'const server = require(process.argv[2]);\n'
               + 'const CASES = ' + json.dumps(CASES) + ';\n'
               + 'const bad = [];\n'
               + 'CASES.forEach(function (c) {\n'
               + '  var a = mechRedactLocal(c).text, b = server.redactDocumentText(c).text;\n'
               + '  if (a !== b) bad.push([c, a, b]);\n'
               + '});\n'
               + 'console.log(JSON.stringify(bad));\n')
    d = tempfile.mkdtemp(prefix='sairn-redact-')
    p = os.path.join(d, 'parity.js')
    io.open(p, 'w', encoding='utf-8').write(harness)
    r = subprocess.run(['node', p, module_path], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return None, (r.stdout or '') + (r.stderr or '')
    try:
        return json.loads((r.stdout or '').strip().split('\n')[-1]), ''
    except ValueError as e:
        return None, 'unparseable parity output: %s' % e


print('mech_docs redaction -- redacted before storage, on the server, and the '
      'two copies agree\n')

for p in (APP, HANDLER, MODULE):
    if not os.path.isfile(p):
        print('COULD NOT RUN: no %s. Nothing was verified.' % p)
        sys.exit(3)

RAW_APP = io.open(APP, encoding='utf-8', errors='replace').read()
APP_CODE = strip_comments(RAW_APP)
H_CODE = strip_comments(io.open(HANDLER, encoding='utf-8', errors='replace').read())
MOD_RAW = io.open(MODULE, encoding='utf-8', errors='replace').read()

# ── 1-2: THE SERVER IS THE BOUNDARY ─────────────────────────────────────
check('1. the handler CALLS the redactor on the mech_docs write path',
      bool(SERVER_CALL.search(H_CODE)) and "resource === 'mech_docs'" in H_CODE,
      'a pure function nothing calls protects nothing')
check('2. the redacted payload is what gets stored AND what is returned',
      'data: mPayload' in H_CODE and 'rows[0].data : mPayload' in H_CODE,
      'returning the raw request body on the fallback arm hands the client '
      'back the unredacted text it sent')

# ── 3: THE CLIENT COPY ──────────────────────────────────────────────────
SAVE_DOC = function_body(RAW_APP, 'saveDoc')
check('3. saveDoc redacts the LOCAL row before writing it',
      bool(SAVE_DOC) and bool(CLIENT_CALL.search(SAVE_DOC))
      and 'redaction:' in SAVE_DOC,
      'saveDoc body found: %s' % bool(SAVE_DOC))

# ── 4: THE TWO RULE SETS AGREE ──────────────────────────────────────────
bad, err = parity(RAW_APP, MODULE)
check('4. the client and server redactors agree on every case',
      bad == [], err or ('disagreements: ' + json.dumps(bad)[:400]))

# ── 5: NO LITERAL BACKSPACE, WHICH IS NOT THEORETICAL ───────────────────
# The first version of the client function had a 0x08 in place of every `\b`
# and five of six rules could never match, while looking correct on screen.
check('5. neither redactor contains a literal backspace (0x08)',
      '\x08' not in RAW_APP and '\x08' not in MOD_RAW,
      'a regex that shipped with a literal backspace and could never match -- '
      'this repo records that defect, and this change reproduced it once')

# ── 6: THE HONESTY CONTRACT REACHES THE ROW AND THE SCREEN ──────────────
check('6. the limits travel WITH the record, not only in a comment',
      'complete: red.complete' in H_CODE and 'note: red.note' in H_CODE
      and 'MECH_REDACT_NOTE' in SAVE_DOC,
      'a row that looks redacted with no account of its limits is the false '
      'confidence this change exists to avoid')
# SCOPED TO saveDoc. `saveTakeoff` still says "Saved on this device" and is
# still RIGHT to -- it is a different function. A file-wide check called
# correct code wrong, twice over: once for saveTakeoff and once for this
# change's own comment quoting the old toast to explain its removal.
check('7. saveDoc no longer says "Saved on this device" while syncing',
      bool(SAVE_DOC) and 'Saved on this device' not in strip_comments(SAVE_DOC),
      'the line above the toast calls mechPushRecord')
check('7b. THE PAIRED CONTROL: saveTakeoff still says it, so arm 7 is scoped '
      'and not a file-wide sweep',
      'Saved on this device' in function_body(RAW_APP, 'saveTakeoff'))

# ── 8-10: MUTATIONS ─────────────────────────────────────────────────────
MUTATIONS = [
    ('8. removing the server call is REFUSED',
     lambda s: SERVER_CALL.sub('noRedact(', s, 1),
     lambda code: bool(SERVER_CALL.search(code)) and "resource === 'mech_docs'" in code,
     'handler'),
    ('9. storing the RAW payload instead of the redacted one is REFUSED',
     lambda s: s.replace('data: mPayload', 'data: payload', 1),
     lambda code: 'data: mPayload' in code and 'rows[0].data : mPayload' in code,
     'handler'),
    ('10. dropping the limits note from the row is REFUSED',
     lambda s: s.replace('note: red.note', 'note: null', 1),
     lambda code: 'complete: red.complete' in code and 'note: red.note' in code,
     'handler'),
]
H_RAW = io.open(HANDLER, encoding='utf-8', errors='replace').read()
for label, mutate, predicate, which in MUTATIONS:
    src = H_RAW
    m = mutate(src)
    if m == src:
        check(label, False,
              'THE MUTATION PLANTED NOTHING -- its anchor no longer matches, so '
              'this arm is not testing what it says it tests.')
        continue
    check(label, not predicate(strip_comments(m)),
          'the mutated file still passed the check it was built to break')

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
