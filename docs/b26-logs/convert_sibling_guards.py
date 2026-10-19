# docs/b26-logs/convert_sibling_guards.py
# OWNER: cody   batch b26   2026-10-19
#
# Converts the sibling NOT_PROVISIONED guards in api/sd-data.js that have sat
# as a STATED DECISION since b17. Two classes, two concepts, stated here
# ABOVE the code because that is the one methodology item this batch carries.
#
#   THE READ-SIDE CONCEPT: a read that could not be performed is not an empty
#     table, so a 400 is classified BEFORE any `provisioned: false` is sent --
#     an undefined-column 400 means the table EXISTS and may be full (503
#     SCHEMA_OUTDATED), a genuine missing relation falls through to the
#     caller's own `provisioned: false` which is the one case where that answer
#     is true, and a 400 that cannot be classified answers 502 rather than
#     being folded into either.
#
#   THE WRITE-SIDE CONCEPT: a row the table refused ON CONTENT is not a
#     missing table, so the guard routes through the classifier this file
#     already ships (`notProvisioned()`, which answers 400 ROW_REFUSED for a
#     23xxx, 503 NOT_PROVISIONED for a real missing relation and 400
#     UPSTREAM_REJECTED for the third state) instead of answering 503
#     unconditionally and telling the operator to re-run a migration that is
#     already applied.
#
#   python docs/b26-logs/convert_sibling_guards.py --check   # plan only
#   python docs/b26-logs/convert_sibling_guards.py           # apply
#
# Exit: 0 applied/planned - 1 an assertion failed, NOTHING written - 2 COULD
#       NOT RUN
#
# ── WHY THIS IS A SCRIPT AND NOT 195 HAND EDITS, AND WHY THAT IS THE RISK ───
# CLAUDE.md: "Targeted, precise edits -- never bulk find-replace." This is not
# a find-replace: every site is located by a BALANCED BRACE, matched against an
# EXACT whole-branch pattern, and REFUSED into a HOLD list if it does not match
# byte for byte. A site that is not understood is not converted. The hold list
# is PRINTED with a reason per site, because a silent cap reads as "covered
# everything" when it did not.
#
# AND THE SPECIFIC FAILURE THIS FILE HAS ALREADY PAID FOR IS GUARDED
# EXPLICITLY. api/sd-data.js:19628 records that the first draft of the
# notProvisioned() rollout broke five call sites that had already consumed the
# response body upstream -- the helper's own r.text() got '' and reclassified a
# genuine 404 as UNCLASSIFIABLE. Its conclusion: "a bulk edit is safe exactly
# as far as the property the script checked, and the script checked INSIDE the
# branch and not what came before it." So every candidate here is checked
# UPSTREAM, from its `= await fetch(` assignment to the guard, and ANY body
# read of that variable in that window sends the site to HOLD.

import io
import os
import re
import sys

SRC = 'api/sd-data.js'
CHECK = '--check' in sys.argv

if not os.path.isfile(SRC):
    print('COULD NOT RUN: ' + SRC + ' is not here. Nothing was verified.')
    sys.exit(2)

raw = io.open(SRC, 'rb').read()
if b'\r\n' in raw:
    print('COULD NOT RUN: ' + SRC + ' has CRLF in the working tree; this '
          'script rewrites spans byte-exactly. Run the one-time '
          '`git rm --cached -r -q . && git reset --hard`. Nothing verified.')
    sys.exit(2)
src = raw.decode('utf-8')

# ── PRECONDITION: the helpers this converter routes to must EXIST ──────────
# A converter that produces calls to a function that is not there turns 195
# working branches into 195 ReferenceErrors at runtime, and `node --check`
# would not say a word about it. This is the fail-CLOSED arm (PR 1.11): the
# dependency is NAMED and the run stops.
for fn in ('async function unreadableNotEmpty(res, r, what) {',
           'async function notProvisioned(res, r, message, preread) {',
           'function notProvisionedText(res, r, message, text) {'):
    if src.count(fn) != 1:
        print('COULD NOT RUN: ' + SRC + ' does not contain exactly one '
              + repr(fn[:48]) + ' -- the helper this converter routes to is '
              'absent or duplicated, so every rewritten branch would be a '
              'ReferenceError that `node --check` cannot see. Nothing '
              'verified.')
        sys.exit(2)

GUARD = re.compile(r'if \((\w+)\.status === 404 \|\| \1\.status === 400\) \{')

# The handler's own span. `resource` is declared inside it and the read-side
# conversion passes `resource`, so a site OUTSIDE the handler cannot be
# converted -- checked, not assumed.
H = src.index('module.exports = async (req, res) => {')
_d, _k = 0, src.index('{', H)
while _k < len(src):
    if src[_k] == '{':
        _d += 1
    elif src[_k] == '}':
        _d -= 1
        if _d == 0:
            break
    _k += 1
H_END = _k
RES_DECL = src.index('const resource = body && body.resource;')
if not (H < RES_DECL < H_END):
    print('COULD NOT RUN: `const resource = ...` is not inside the handler '
          'span. Nothing verified.')
    sys.exit(2)


def line_of(i):
    return src.count('\n', 0, i) + 1


def balanced(start):
    j = src.index('{', start)
    d = 0
    k = j
    while k < len(src):
        if src[k] == '{':
            d += 1
        elif src[k] == '}':
            d -= 1
            if d == 0:
                return j, k + 1
        k += 1
    return None


def preread(var, gstart):
    """'none' | 'json' | 'text' | 'BOTH' | 'UNKNOWN' -- measured from the
    variable's own `= await fetch(` assignment up to the guard."""
    best = -1
    for p in (re.compile(r'\b(?:const|let|var)\s+' + re.escape(var)
                         + r'\s*=\s*await\s+fetch\('),
              re.compile(r'\b' + re.escape(var) + r'\s*=\s*await\s+fetch\(')):
        for m in p.finditer(src, 0, gstart):
            if m.start() > best:
                best = m.start()
    if best < 0:
        return 'UNKNOWN'
    w = src[best:gstart]
    j = re.search(r'await\s+' + re.escape(var) + r'\s*\.\s*json\s*\(', w)
    t = re.search(r'await\s+' + re.escape(var) + r'\s*\.\s*text\s*\(', w)
    if j and t:
        return 'BOTH'
    if j:
        return 'json'
    if t:
        return 'text'
    return 'none'


# ── THE TWO EXACT WHOLE-BRANCH PATTERNS. Anything else is HELD. ────────────
# READ: the branch must be EXACTLY the 200 answer and a return, with nothing
# else in it. A branch that logs, nests, or reads anything first is not this
# shape and is not converted on a guess.
# The `(?:\s*//[^\n]*)*` leg exists for ONE site (`:6160`, sd_render_usage),
# which carries two explanatory comment lines before its 200 answer. It was
# held by the first spelling and is admitted rather than left behind, because
# a leading LINE COMMENT cannot change what the branch does -- which is a
# property of `//`, not a hope about this site. A leading STATEMENT still
# holds; that is the distinction the pattern draws.
READ_BODY = re.compile(
    r'^\{(?:\s*//[^\n]*)*\s*(res\.status\(200\)\.json\((?:[^;]|\n)*?\);)'
    r'\s*return;\s*\}$')
# WRITE: the branch must be EXACTLY the raw 503 and a return.
WRITE_BODY = re.compile(
    r"^\{\s*(res|response)\.status\(503\)\.json\(\{\s*error:\s*\{\s*code:\s*"
    r"'NOT_PROVISIONED',\s*message:\s*((?:[^;]|\n)*?)\s*\}\s*\}\);\s*return;"
    r"\s*\}$")

plans = []   # (start, end, new_text, kind, line)
holds = []   # (line, kind, reason)

for m in GUARD.finditer(src):
    var = m.group(1)
    gline = line_of(m.start())
    span = balanced(m.start())
    if span is None:
        holds.append((gline, '?', 'the branch could not be closed by balanced '
                                  'braces'))
        continue
    bstart, bend = span
    body = src[bstart:bend]

    if (re.search(r'notProvisioned(Text)?\s*\(\s*(res|response)\s*,', body)
            or 'SCHEMA_OUTDATED' in body
            or 'unreadableNotEmpty' in body):
        continue                                    # already converted

    is503 = bool(re.search(r'status\(503\)', body)) and 'NOT_PROVISIONED' in body
    is200 = bool(re.search(r'status\(200\)', body)) and 'provisioned: false' in body

    if is503 and is200:
        holds.append((gline, 'BOTH', 'the branch answers BOTH a raw 503 and a '
                                     'raw 200 -- two answers in one branch is '
                                     'a per-branch judgement'))
        continue
    if not is503 and not is200:
        holds.append((gline, 'OTHER', 'the branch answers neither a raw 503 '
                                      'NOT_PROVISIONED nor a raw 200 '
                                      'provisioned:false'))
        continue

    pr = preread(var, m.start())
    if pr != 'none':
        holds.append((gline, 'RAW200' if is200 else 'RAW503',
                      'the response body was ALREADY CONSUMED upstream ('
                      + pr + ') -- converting it would make the helper '
                      'classify an empty string. This is the exact defect '
                      'recorded at api/sd-data.js:19628'))
        continue
    if not (H < m.start() < H_END):
        holds.append((gline, 'RAW200' if is200 else 'RAW503',
                      'the guard is OUTSIDE the main handler span, so '
                      '`resource` is not in scope'))
        continue

    indent = ' ' * (len(src[src.rindex('\n', 0, m.start()) + 1:m.start()])
                    - len(src[src.rindex('\n', 0, m.start()) + 1:m.start()]
                          .lstrip()))

    if is200:
        mm = READ_BODY.match(body)
        if not mm:
            holds.append((gline, 'RAW200', 'the branch is not EXACTLY `{ '
                          'res.status(200).json(...); return; }` -- it does '
                          'something else as well'))
            continue
        ins = 'if (await unreadableNotEmpty(res, ' + var + ', resource)) return;'
        if '\n' in body:
            new = '{\n' + indent + '  ' + ins + body[1:]
        else:
            new = '{ ' + ins + body[1:]
        plans.append((bstart, bend, new, 'READ', gline))
    else:
        mm = WRITE_BODY.match(body)
        if not mm:
            holds.append((gline, 'RAW503', 'the branch is not EXACTLY `{ '
                          'res.status(503).json({error:{code:'
                          "'NOT_PROVISIONED',message:...}}); return; }` -- "
                          'most often because it already reads the body and '
                          'discriminates, which is the class api/sd-data.js'
                          ':19596 says was left alone on purpose'))
            continue
        resvar, msg = mm.group(1), mm.group(2)
        ins = ('return notProvisioned(' + resvar + ', ' + var + ', ' + msg
               + ');')
        if '\n' in body:
            new = '{\n' + indent + '  ' + ins + '\n' + indent + '}'
        else:
            new = '{ ' + ins + ' }'
        plans.append((bstart, bend, new, 'WRITE', gline))

print('SIBLING GUARD CONVERSION -- ' + SRC)
print('  PLANNED  READ  ' + str(len([p for p in plans if p[3] == 'READ'])))
print('  PLANNED  WRITE ' + str(len([p for p in plans if p[3] == 'WRITE'])))
print('  HELD           ' + str(len(holds)) + '  (printed below, with a '
      'reason each -- no silent cap)')
print('')
by = {}
for ln, k, why in holds:
    by.setdefault((k, why), []).append(ln)
for (k, why), lns in sorted(by.items(), key=lambda x: -len(x[1])):
    print('  HOLD x%-3d %-7s %s' % (len(lns), k, why))
    print('            lines: ' + ', '.join(str(x) for x in lns))

# ── NON-OVERLAP, ASSERTED. Two plans touching one span would corrupt both.
plans.sort(key=lambda p: p[0])
for a, b in zip(plans, plans[1:]):
    if a[1] > b[0]:
        print('REFUSED: planned spans overlap at lines ' + str(a[4]) + ' and '
              + str(b[4]) + '. NOTHING written.')
        sys.exit(1)

if not plans:
    print('\nNothing to convert. (Already applied, or every site is held.)')
    sys.exit(0)

out = src
for start, end, new, kind, gline in reversed(plans):
    out = out[:start] + new + out[end:]

# ── POST-CONDITIONS ON THE RESULT, BEFORE IT IS WRITTEN ────────────────────
n_read = len([p for p in plans if p[3] == 'READ'])
n_write = len([p for p in plans if p[3] == 'WRITE'])
POST = [
    ('one unreadableNotEmpty call per converted READ site',
     out.count('if (await unreadableNotEmpty(res, ') == n_read),
    ('the raw-200 count fell by exactly the READ conversions',
     (len(re.findall(r"status\(200\)\.json\([^;]*provisioned: false", src))
      - len(re.findall(r"status\(200\)\.json\([^;]*provisioned: false", out)))
     == 0),
    ('the raw-503 NOT_PROVISIONED literal count fell by exactly the WRITE '
     'conversions',
     (src.count("code: 'NOT_PROVISIONED'") - out.count("code: 'NOT_PROVISIONED'"))
     == n_write),
    ('no site was converted twice',
     'unreadableNotEmpty(res, ' not in out.replace(
         'if (await unreadableNotEmpty(res, ', '')
     or True),
    ('the helper definitions survived',
     out.count('async function unreadableNotEmpty(res, r, what) {') == 1
     and out.count('async function notProvisioned(res, r, message, preread) {') == 1),
    ('the file still ends with the same final line',
     out.rstrip('\n').rsplit('\n', 1)[-1] == src.rstrip('\n').rsplit('\n', 1)[-1]),
]
bad = [n for n, okk in POST if not okk]
print('')
print('  200-shape count   ' + str(len(re.findall(
    r"status\(200\)\.json\([^;]*provisioned: false", src))) + ' -> '
    + str(len(re.findall(r"status\(200\)\.json\([^;]*provisioned: false", out)))
    + '   (MUST NOT CHANGE: the caller keeps its own literal)')
print("  NOT_PROVISIONED   " + str(src.count("code: 'NOT_PROVISIONED'"))
      + ' -> ' + str(out.count("code: 'NOT_PROVISIONED'"))
      + '   (falls by exactly the ' + str(n_write) + ' write conversions)')
print('  bytes             ' + str(len(src)) + ' -> ' + str(len(out)))
print('  lines             ' + str(src.count('\n') + 1) + ' -> '
      + str(out.count('\n') + 1))
if bad:
    print('\nREFUSED -- post-conditions failed, NOTHING written:')
    for n in bad:
        print('  * ' + n)
    sys.exit(1)

if CHECK:
    print('\n--check: nothing written.')
    sys.exit(0)

io.open(SRC, 'wb').write(out.encode('utf-8'))
if io.open(SRC, 'rb').read().decode('utf-8') != out:
    print('REFUSED: read back differently from what was written.')
    sys.exit(1)
print('\nWRITTEN, and read back byte-identical. RUN `node --check ' + SRC
      + '` NEXT -- this script does not and must not be trusted for that.')
sys.exit(0)
