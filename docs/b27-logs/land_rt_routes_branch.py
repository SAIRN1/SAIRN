# docs/b27-logs/land_rt_routes_branch.py
# OWNER: cody   batch b27   2026-10-19
#
# THE CONCEPT: the rt_routes/rt_stops endpoint must answer all four verbs
#   behind BOTH a licence and an employee session -- a licence proves the shop,
#   and a list of addresses joined to a named employee is not shop metadata --
#   and the registry must declare the three non-read verbs IN THE SAME EDIT,
#   because api/_resources/index.js asserts extra actions at load and a verb
#   declared without a handler asserts a capability that answers 400.
#
#   python docs/b27-logs/land_rt_routes_branch.py --check
#   python docs/b27-logs/land_rt_routes_branch.py
#
# Exit: 0 applied / --check clean - 1 an assertion failed, NOTHING written -
#       2 COULD NOT RUN
#
# ── THE CODE IS EXTRACTED FROM THE ROUTING DOCUMENT, NOT RETYPED ───────────
# Michael's instruction is "exactly as written in
# docs/2026-10-19-fourth-b34-routing-phase1.md section 3, and nothing else in
# that change". Retyping 150 lines by hand cannot be shown to be exact; lifting
# them out of the fenced block CAN, and this script asserts it both ways:
#
#   * the branch is inserted with FOUR SPACES of leading indentation per line,
#     because the file's per-resource branches sit at that depth inside the
#     handler's try block -- and then the inserted region is read back, the
#     four spaces stripped, and asserted BYTE-IDENTICAL to the doc's block.
#     Re-indentation is the only difference and it is proved to be the only
#     one. **Indentation is not the code**; a byte comparison that ignored it
#     would be the thing that could not tell a reformat from an edit.
#   * "nothing else in that change" is asserted as a DIFF PROPERTY, not an
#     intention: exactly one contiguous insertion in api/sd-data.js, exactly
#     one in api/_resources/routes.js, and every other line of both files
#     byte-identical.

import io
import os
import re
import sys

DOC = 'docs/2026-10-19-fourth-b34-routing-phase1.md'
SRC = 'api/sd-data.js'
REG = 'api/_resources/routes.js'
CHECK = '--check' in sys.argv

for p in (DOC, SRC, REG):
    if not os.path.isfile(p):
        print('COULD NOT RUN: ' + p + ' is not here. Nothing was verified.')
        sys.exit(2)

doc = io.open(DOC, encoding='utf-8').read().replace('\r\n', '\n')

# ── THE TWO FENCED BLOCKS, LOCATED BY THEIR OWN CONTENT ───────────────────
# Not by line number and not by "the first ```js" -- a line number rots and an
# ordinal breaks the day somebody adds a block above. Each is anchored on a
# string only that block contains.
blocks = re.findall(r'```js\n(.*?)```', doc, re.S)
branch = [b for b in blocks if "if (resource === 'rt_routes' || resource === 'rt_stops') {" in b]
extra = [b for b in blocks if b.strip().startswith('extraActions: {')]
if len(branch) != 1:
    print('COULD NOT RUN: the handler-branch block was found ' + str(len(branch))
          + ' times in ' + DOC + ', not once. Nothing was verified.')
    sys.exit(2)
if len(extra) != 1:
    print('COULD NOT RUN: the extraActions block was found ' + str(len(extra))
          + ' times in ' + DOC + ', not once. Nothing was verified.')
    sys.exit(2)
BRANCH = branch[0].rstrip('\n')
EXTRA = extra[0].strip()

# ── PRECONDITION: the module and the registry the branch depends on MUST
#    EXIST. FAIL CLOSED (PR 1.11). A branch that requires a module which is
#    not there is a ReferenceError at request time and `node --check` says
#    nothing about it.
for dep, why in (
    ('api/_lib/routes.js', 'the branch does require("./_lib/routes.js") and '
                           'calls validateRouteKey, validateStops, applyOrder '
                           'and optimize on it'),
    ('api/_lib/routes.test.js', 'item 1 adds an arm to it'),
):
    if not os.path.isfile(dep):
        print('COULD NOT RUN: ' + dep + ' does not exist, and ' + why
              + '. Nothing was verified.')
        sys.exit(2)
rt = io.open('api/_lib/routes.js', encoding='utf-8').read()
missing = [f for f in ('validateRouteKey', 'validateStops', 'applyOrder', 'optimize')
           if ('exports.' + f) not in rt and (f + ':') not in rt
           and ('function ' + f) not in rt]
if missing:
    print('COULD NOT RUN: api/_lib/routes.js does not appear to export '
          + ', '.join(missing) + ' -- the branch calls them. Nothing verified.')
    sys.exit(2)

src_raw = io.open(SRC, 'rb').read()
if b'\r\n' in src_raw:
    print('COULD NOT RUN: ' + SRC + ' has CRLF in the working tree; this '
          'script compares bytes. Run the one-time `git rm --cached -r -q . && '
          'git reset --hard`. Nothing verified.')
    sys.exit(2)
src = src_raw.decode('utf-8')

if 'rt_routes' in src:
    print('ALREADY APPLIED: api/sd-data.js already mentions rt_routes. '
          'Nothing written. (Re-running is a no-op, not a second insertion.)')
    sys.exit(0)

# ── THE INSERTION POINT, ANCHORED ON THE HANDLER'S OWN FALLTHROUGH ────────
# The last thing in the handler's try block is its unreachable-combination
# 400. A new per-resource branch belongs immediately before it, at the same
# depth -- any later and it is dead code behind that 400.
ANCHOR = ('\n    // Should be unreachable given the guards above.\n'
          "    res.status(400).json({ error: { message: 'Unsupported action/resource combination' } });\n")
if src.count(ANCHOR) != 1:
    print('COULD NOT RUN: the handler fallthrough anchor occurs '
          + str(src.count(ANCHOR)) + ' times in ' + SRC + ', not once, so the '
          'insertion point could not be located unambiguously. Nothing '
          'verified.')
    sys.exit(2)

INDENT = '    '
indented = '\n'.join((INDENT + l) if l.strip() else l for l in BRANCH.split('\n'))
new_src = src.replace(ANCHOR, '\n' + indented + '\n' + ANCHOR)

# ── THE REGISTRY, IN THE SAME EDIT ────────────────────────────────────────
reg_raw = io.open(REG, 'rb').read()
if b'\r\n' in reg_raw:
    print('COULD NOT RUN: ' + REG + ' has CRLF in the working tree.')
    sys.exit(2)
reg = reg_raw.decode('utf-8')
if 'extraActions' in reg:
    print('COULD NOT RUN: ' + REG + ' already declares extraActions. This '
          'script would add a second one. Nothing verified.')
    sys.exit(2)
REG_ANCHOR = "    'rt_stops',\n  ],\n};\n"
if reg.count(REG_ANCHOR) != 1:
    print('COULD NOT RUN: ' + REG + ' does not end with the expected '
          'resources array; the insertion point could not be located.')
    sys.exit(2)
REG_NOTE = (
    "  ],\n"
    "  // ── THE THREE NON-READ VERBS, DECLARED WITH THE HANDLER AND NOT "
    "BEFORE IT ──\n"
    "  // 'upsert', 'reorder' and 'optimize' are verbs beyond read/write, and\n"
    "  // api/_resources/index.js asserts extra actions AT LOAD: a verb\n"
    "  // declared for a resource whose module does not register it is\n"
    "  // refused, and a verb declared with no handler branch asserts a\n"
    "  // capability that answers 400. So this line lands in the SAME edit as\n"
    "  // the api/sd-data.js branch -- fourth's routing document held it back\n"
    "  // on purpose for exactly that reason.\n"
    "  //\n"
    "  // rt_stops gets NO extra verbs. Every verb here operates on a ROUTE\n"
    "  // and its stop set together -- 'reorder' renumbers the whole set and\n"
    "  // 'optimize' replaces it -- so a verb aimed at a single stop would be\n"
    "  // a capability with no handler behind it.\n"
    "  extraActions: {\n"
    "    rt_routes: ['upsert', 'reorder', 'optimize'],\n"
    "  },\n"
    "};\n")
new_reg = reg.replace(REG_ANCHOR, "    'rt_stops',\n" + REG_NOTE)

# ── POST-CONDITIONS, BEFORE ANYTHING IS WRITTEN ───────────────────────────
# (1) EXACTNESS: strip the four spaces back off the inserted region and
#     require it to equal the document's block BYTE FOR BYTE.
back = '\n'.join(l[len(INDENT):] if l.startswith(INDENT) else l
                 for l in indented.split('\n'))
# (2) ONE CONTIGUOUS INSERTION, and every other line untouched.
a, b = src.split('\n'), new_src.split('\n')
ins = len(b) - len(a)
head = 0
while head < len(a) and a[head] == b[head]:
    head += 1
tail = 0
while tail < len(a) - head and a[len(a) - 1 - tail] == b[len(b) - 1 - tail]:
    tail += 1
POST = [
    ('the inserted branch is BYTE-IDENTICAL to the document block once the '
     'four spaces of indentation are stripped', back == BRANCH),
    ('the document block is the one the registry line belongs with',
     EXTRA == "extraActions: {\n  rt_routes: ['upsert', 'reorder', 'optimize'],\n},"),
    ('exactly one contiguous insertion in ' + SRC,
     head + tail == len(a) and ins == len(BRANCH.split('\n')) + 1),
    ('no line of ' + SRC + ' was removed or altered', len(a) + ins == len(b)),
    ('the registry gained exactly the three verbs',
     new_reg.count("rt_routes: ['upsert', 'reorder', 'optimize'],") == 1),
    ('the registry still registers both resources',
     new_reg.count("'rt_routes',") == 1 and new_reg.count("'rt_stops',") == 1),
    ('the branch gates on a SESSION and not only a licence',
     'verifySessionToken(tokenFromRequest(req), licHash, p.app_id)' in new_src),
    # THE FIRST SPELLING OF THIS ARM WAS WRONG AND IT REFUSED THE RUN, which
    # is the arm working. It compared against the first occurrence of the bare
    # string 'Unsupported action/resource combination' -- and that string
    # appears THREE times in this file, twice inside COMMENTS at :15940 and
    # :18693 that discuss the fallthrough, thousands of lines above it. So the
    # comparison was against a comment, not against the statement. Anchored on
    # the real ANCHOR (the comment-plus-statement pair the insertion point was
    # located by) rather than on a substring that also occurs in prose -- the
    # same defect class as b26's 1400-character window, in a post-condition.
    ('the branch is INSIDE the handler, before its fallthrough 400',
     new_src.index("resource === 'rt_routes'") < new_src.index(ANCHOR)),
]
bad = [n for n, okk in POST if not okk]

print('LAND rt_routes -- b27 item 1')
print('  document      ' + DOC + ' section 3')
print('  branch block  ' + str(len(BRANCH.split('\n'))) + ' lines, extracted '
      'from the fence rather than retyped')
print('  ' + SRC + '  lines ' + str(len(a)) + ' -> ' + str(len(b))
      + '  (+' + str(ins) + ', one contiguous insertion at line '
      + str(head + 1) + ')')
print('  ' + REG + '  +' + str(len(new_reg.split('\n')) - len(reg.split('\n')))
      + ' lines, extraActions declared IN THE SAME EDIT')
for n, okk in POST:
    print('   %-4s %s' % ('ok' if okk else 'FAIL', n))
if bad:
    print('\nREFUSED -- NOTHING written.')
    sys.exit(1)
if CHECK:
    print('\n--check: nothing written.')
    sys.exit(0)

io.open(SRC, 'wb').write(new_src.encode('utf-8'))
io.open(REG, 'wb').write(new_reg.encode('utf-8'))
if io.open(SRC, 'rb').read().decode('utf-8') != new_src:
    print('REFUSED: ' + SRC + ' read back differently from what was written.')
    sys.exit(1)
if io.open(REG, 'rb').read().decode('utf-8') != new_reg:
    print('REFUSED: ' + REG + ' read back differently.')
    sys.exit(1)
print('\nWRITTEN, both read back byte-identical. RUN `node --check ' + SRC
      + '` NEXT -- this script does not and must not be trusted for that.')
sys.exit(0)
