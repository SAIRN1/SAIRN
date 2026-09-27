"""A BRANCH GATED ON A FIELD NAME NOTHING EVER SETS.

Run:  python tools/ghost_field_read_scan.py
      python tools/ghost_field_read_scan.py --json
      python tools/ghost_field_read_scan.py --list-builtins

── WHAT THIS DECIDES, AND WHY IT IS A SEPARATE TOOL ────────────────────────
`docs/2026-09-26-ghost-failure-path-sweep.md` names three members of one family
-- a verdict whose two outcomes are computed from something that cannot differ
-- and says only the FIRST was mechanically decidable
(`tools/unreachable_failure_path_scan.py`: a function whose every `return` is
bare, so a caller comparing its result against a literal has a dead branch).

THIS IS A SECOND DECIDABLE MEMBER, and it was paid for the day after that sweep
was written, by the author of that sweep, for the third time in one afternoon:

    api/_lib/compliance-rules.js gated its "we could not read who this
    requirement applies to" message on `out.unmapped_requirements_pending`
    -- a property name that is never assigned ANYWHERE, in any file. The
    branch could not fire, so every empty applicable set reported "no
    obligation" instead of "could not tell". A staff member with a real
    training obligation was reported as having none.

THE DEFECT IS NOT A TYPO, it is that a typo in a GATE is silent: the condition
is simply always falsy, the code reads as a working safeguard on every future
review of it, and the only symptom is the safer answer never appearing.

── THE RULE, STATED SO A READER CAN DISAGREE WITH IT ───────────────────────
A finding is a property READ, `x.FIELD`, that

  1. appears inside a CONDITION -- an `if (...)`, a `while (...)`, a ternary
     test, a `&&`/`||` operand, or under a `!` -- so it GATES something. A
     ghost read in a plain expression yields `undefined` into a value, which is
     usually visible; a ghost read in a gate yields a branch that never runs,
     which is not.
  2. is NOT a JavaScript or DOM property (`BUILTIN_PROPS` below, printed by
     `--list-builtins` so the exclusion list is readable rather than trusted).
  3. NEVER APPEARS AS A WRITE OR A KEY ANYWHERE IN THE REPO -- not as
     `x.FIELD =`, not as `FIELD:` in an object literal, not as a destructured
     binding, not as `'FIELD'` / `"FIELD"` in any string, not as a key in any
     tracked `.json`, `.sql` or `.md`. The universe is the WHOLE repo and not
     the file, deliberately: a server field arrives in a PostgREST row and is
     spelled in a schema file, and a per-file universe would report every one
     of those as a ghost.

CONDITION (3) IS WHY THIS CAN BE ZERO AND MEAN SOMETHING. A name that is read
and never written, never quoted, and is not a builtin, cannot have a value.

── WHAT IT CANNOT SEE, so the gap is a decision and not an omission ─────────
* A field written under a COMPUTED key (`row[k] = v`, `Object.assign(out, m)`).
  Then the name exists nowhere as a literal and a real field looks like a
  ghost. This is the false-POSITIVE direction and it is why every finding is
  printed with its line for a human to read, and why the tool reports findings
  rather than gating a push.
* A field that is written SOMEWHERE and read on the WRONG OBJECT -- the
  `payload.check` vs `payload.requirement_type` case, member (2) of the sweep.
  `check` is a real key elsewhere, so condition (3) clears it. Deciding that
  needs each endpoint's required-field list joined to every caller's payload,
  across two languages, and it is still not built.
* A MISSPELLED name that happens to be spelled that way somewhere else for an
  unrelated reason. Condition (3) clears it and this tool will not find it.

So: a finding here is strong evidence, and a clean run means only that no
LITERALLY-UNSPELLED gate field remains. It does not mean no gate reads the
wrong field.

── THE CONTROL ─────────────────────────────────────────────────────────────
`tests/run_ghost_field_read_probe.py` restores the real pre-fix condition into
the real `api/_lib/compliance-rules.js` and demands this scan name it, then
restores the file and demands silence. Both directions, on the real defect
rather than a synthetic fixture.
"""
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker_kit import (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN,  # noqa: E402
                         REPO, tracked, strip_comments, finish, read)

# Bumped whenever the rule above changes, so a stored verdict cannot be read as
# current under different criteria. Same reason sabotage_control_check.py
# carries CRITERIA_VERSION.
CRITERIA_VERSION = '2026-09-27.1'

# ── JS AND DOM PROPERTIES, which are read and never assigned BY DESIGN ──────
# PRINTED BY `--list-builtins` ON PURPOSE. An exclusion list nobody can read is
# a place to hide a real field, and this one is the only judgement in the tool.
# Kept to properties that actually appear in CONDITIONS in this repo -- a
# thousand-name dump of the DOM would hide an addition.
BUILTIN_PROPS = frozenset("""
length size name message stack code cause constructor prototype __proto__
toString valueOf hasOwnProperty call apply bind
push pop shift unshift slice splice concat join indexOf lastIndexOf includes
find findIndex filter map forEach reduce reduceRight some every sort reverse
flat flatMap fill keys values entries at
trim trimStart trimEnd toLowerCase toUpperCase split replace replaceAll match
matchAll search startsWith endsWith padStart padEnd repeat charAt charCodeAt
codePointAt normalize localeCompare substring substr
test exec source flags global ignoreCase multiline lastIndex
toFixed toPrecision toExponential
getTime getFullYear getMonth getDate getDay getHours getMinutes getSeconds
getMilliseconds getTimezoneOffset toISOString toJSON toLocaleDateString
toLocaleTimeString toLocaleString getUTCFullYear getUTCMonth getUTCDate
now parse stringify random floor ceil round abs max min pow sqrt sign trunc
isArray isInteger isFinite isNaN from of assign freeze isFrozen create
getOwnPropertyNames getPrototypeOf defineProperty
then catch finally all allSettled race resolve reject
has get set add delete clear
document window location navigator history localStorage sessionStorage console
body head documentElement innerHTML outerHTML textContent innerText value
checked disabled selected readOnly hidden files dataset style classList
className id tagName nodeType nodeName children childNodes firstChild
lastChild firstElementChild lastElementChild parentNode parentElement
nextSibling previousSibling nextElementSibling previousElementSibling
offsetWidth offsetHeight offsetTop offsetLeft clientWidth clientHeight
clientTop clientLeft scrollTop scrollLeft scrollWidth scrollHeight
getBoundingClientRect querySelector querySelectorAll getElementById
getElementsByClassName getElementsByTagName closest matches contains
addEventListener removeEventListener dispatchEvent preventDefault
stopPropagation target currentTarget relatedTarget key keyCode which altKey
ctrlKey shiftKey metaKey button buttons clientX clientY pageX pageY
touches changedTouches
href protocol host hostname pathname port hash origin search searchParams
appendChild removeChild insertBefore replaceChild cloneNode remove append
prepend insertAdjacentHTML setAttribute getAttribute removeAttribute
hasAttribute attributes selectedIndex options rows cells
localName namespaceURI
ok statusText headers url redirected type bodyUsed json text blob arrayBuffer
formData clone
env argv platform exit stdout stderr stdin cwd
readyState responseText response status
FileReader result
""".split())

# The names above that are ALSO real SAIRN field names are a real hazard: an
# entry here silences a genuine ghost. Two are known and NOT excluded for that
# reason -- `ok` and `status` appear in both worlds, so they are listed above
# (they are read off `fetch` responses constantly) AND they are spelled as keys
# in hundreds of places, so condition (3) clears them anyway. The exclusion is
# therefore not load-bearing for either. Stated so the next reader does not
# have to work it out.

# ── THIRD-PARTY CONTRACTS, DECLARED WITH THE OWNER NAMED ────────────────────
# A field that arrives from somebody else's API can never be spelled in this
# repo, so condition (3) can never clear it and it would be reported for ever.
# The alternative to declaring them is a report nobody reads, which is the same
# end state as no report.
#
# EACH ENTRY NAMES THE CONTRACT THAT OWNS THE SHAPE, so a reader can check it
# against that vendor's documentation rather than against this file's opinion.
#
# AN ENTRY THAT MATCHES NOTHING IS REPORTED, not silently kept. That is the
# whole staleness defence: a hand-kept exclusion list that cannot be seen to be
# doing anything is a place to hide a real field, and this repo has paid for
# that shape more than once (a string anchor that no longer matched; a suite's
# hand-listed dependency going stale five times).
EXTERNAL_CONTRACTS = {
    'JWT header / OIDC discovery document (RFC 7517, RFC 8414)':
        ('alg', 'iss', 'aud', 'jwks_uri', 'kid'),
    'WebAuthn / @simplewebauthn/server':
        ('credentialBackedUp', 'credentialDeviceType', 'registrationInfo',
         'getClientExtensionResults'),
    'Stripe Node SDK':
        ('billingPortal',),
    'Open-Meteo current-weather response':
        ('current_weather', 'weathercode', 'windspeed'),
    'CourtListener API':
        ('dateFiled', 'opinions'),
    'Stedi 271 eligibility response':
        ('benefitAmount', 'benefitPercent', 'coverageLevel',
         'inPlanNetworkIndicator', 'serviceTypes', 'primaryPayerId',
         'stediId', 'planDetails'),
    'WebGL / WebXR (gl.*, XRWebGLLayer, XRSession)':
        ('FRAMEBUFFER', 'makeXRCompatible', 'framebuffer', 'renderState'),
    'DOM and media APIs not in BUILTIN_PROPS':
        ('mediaDevices', 'selectedOptions', 'videoWidth', 'videoHeight',
         'mimeType', 'coords'),
}
EXTERNAL_FIELDS = {}
for _owner, _fields in EXTERNAL_CONTRACTS.items():
    for _f in _fields:
        EXTERNAL_FIELDS[_f] = _owner

# ── THE REQUEST BODY IS A DIFFERENT FINDING AND GETS ITS OWN BUCKET ──────────
# `payload.X` / `body.X` inside an `api/` handler is the CALLER's half of a
# documented request contract. If nothing else in the repo spells X, the honest
# reading is usually "no client sends it yet" -- DORMANCY -- and not "this gate
# reads the wrong field". Both matter and they are not the same thing, so they
# are not reported in the same list.
#
# MEASURED, NOT ASSUMED. On the first real run this bucket held
# `payload.ordered_at` on sd_supplier_lead_times: the endpoint's own comment
# documents `observe -- a REAL receipt (ordered_at, received_at)`, the name is
# self-consistent inside that handler, and the finding is that NO CLIENT CALLS
# `mode: 'observe'` at all. Filing that beside a wrong-field gate would have
# made both harder to read.
REQUEST_OBJECTS = ('payload', 'body', 'reqBody', 'requestBody')

CODE_PATTERNS = ('*.js', '*.html', '*.py', '*.cjs', '*.mjs')
# ── PROSE IS NOT A SPELLING, AND THIS TOOL PAID FOR THAT ON ITS FIRST DAY ────
# `*.md` was in this list, and the spelled universe was built from RAW text
# including comments. So the moment a test arm was written asserting
# "rfDeliveredHoursFor must not read `actual_start`", the words
# `actual_start` existed in a comment -- and the scan went silent about
# `actual_start` for ever. Its own control probe caught it: MUTATION 1
# re-planted the real shipped defect and the scan did not name it.
#
# THAT IS PR 1.1 EXACTLY -- a check that stopped checking -- committed by a tool
# whose whole subject is a condition that cannot fire. The fix is that the
# spelled universe comes from CODE AND DATA and never from prose:
#   * .js/.html/.cjs/.mjs -- comments stripped, STRINGS KEPT (a string key is a
#     real spelling).
#   * .py -- `#` comments stripped, strings kept, same reason.
#   * .json/.sql/.csv -- data. Keys and columns are real spellings.
#   * .md -- EXCLUDED. A field named in a document is a field being DISCUSSED,
#     and this tool's findings and this repo's incident write-ups both discuss
#     dead field names by name. The cost is that a field defined ONLY in a
#     markdown spec reads as a ghost; that is the safe direction (a false
#     finding a human dismisses) and is stated here rather than discovered.
KEY_PATTERNS = ('*.js', '*.html', '*.json', '*.sql', '*.py', '*.csv',
                '*.cjs', '*.mjs')


def _strip_hash_comments(text):
    """Blank `#` comments in Python, preserving offsets. Quote-aware, because
    `'#'` and `"# not a comment"` are ordinary strings and a naive split on `#`
    is the house defect (PR 1.2)."""
    out, i, n, quote = [], 0, len(text), None
    while i < n:
        c = text[i]
        if quote:
            if c == '\\' and i + 1 < n:
                out.append(text[i:i + 2])
                i += 2
                continue
            if c == quote:
                quote = None
            out.append(c)
            i += 1
            continue
        if c in '\'"':
            quote = c
            out.append(c)
            i += 1
            continue
        if c == '#':
            j = text.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i))
            i = j
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def code_only(rel, raw):
    """The text a SPELLING may be read out of: code and data, never prose."""
    if rel.endswith('.py'):
        return _strip_hash_comments(raw)
    if rel.endswith(('.js', '.cjs', '.mjs', '.html')):
        return strip_comments(raw)          # comments blanked, strings kept
    return raw                               # .json / .sql / .csv are data

IDENT = r'[A-Za-z_$][A-Za-z0-9_$]*'

# A property read: `word.field` not followed by `(` (a call), `=` (a write) or
# another `.`-chained write target we handle separately.
READ_RE = re.compile(r'\b(' + IDENT + r')\s*\.\s*(' + IDENT + r')\b(?!\s*\()')

# Every way a name can be SPELLED as a field in this repo. Deliberately
# generous: the cost of a missing spelling here is a false finding, and the cost
# of an extra one is only a ghost this tool declines to report -- so it errs
# toward silence, and the header says so.
def spelled_names(text):
    out = set()
    # obj.field = ...  /  obj.field++  /  delete obj.field
    for m in re.finditer(r'\.\s*(' + IDENT + r')\s*(?:=[^=]|\+\+|--|\+=|-=)', text):
        out.add(m.group(1))
    for m in re.finditer(r'\bdelete\s+' + IDENT + r'\s*\.\s*(' + IDENT + r')', text):
        out.add(m.group(1))
    # { field: ... } -- an object-literal or JSON key. THE ADJACENCY MUST NOT BE
    # REQUIRED: the first version demanded a `{` or `,` immediately before, and
    # in a file where every key carries a comment above it (which is this
    # repo's whole house style) the comment sits between the comma and the key,
    # so `no_applicable_requirement:` in api/_lib/compliance-rules.js was NOT
    # recognised as a spelling and its own test file was reported as a ghost.
    # Line-anchored and delimiter-anchored, both.
    for m in re.finditer(r'(?:^|[{,(])[ \t]*(' + IDENT + r')\s*:', text, re.M):
        out.add(m.group(1))
    # { field, } and { field } -- shorthand property and destructuring binding.
    for m in re.finditer(r'(?:^|[{,])[ \t]*(' + IDENT + r')\s*(?:[,}=]|$)', text, re.M):
        out.add(m.group(1))
    # ── A DECLARED TOP-LEVEL NAME IS A SPELLING (added on the first real run) ─
    # This repo's suites extract an app's script into a `vm` context and then
    # read the app's own constants BACK OFF that context object -- `ctx
    # .SC_PT_SOURCES`, `T.INVARIANTS`, `c.DC_MIN_INSIDE_RADIUS_IN`. The name
    # exists as `const SC_PT_SOURCES = ...` in the app and as no key anywhere,
    # so without this the whole sandbox-harness class reads as ghosts. Eleven
    # did on the first run.
    for m in re.finditer(r'\b(?:const|let|var|function|class)\s+(' + IDENT + r')', text):
        out.add(m.group(1))
    # any quoted token that looks like an identifier: a string key, a JSON key,
    # a SQL column, a name in prose. This is the widest net and is why a clean
    # run is credible.
    for m in re.finditer(r'''['"`](''' + IDENT + r''')['"`]''', text):
        out.add(m.group(1))
    # bare SQL/markdown/CSV column tokens
    for m in re.finditer(r'\b(' + IDENT + r')\b', text):
        pass  # deliberately NOT added -- see below
    return out


# WHY THE LAST LOOP IS EMPTY AND KEPT. Adding every bare identifier in every
# .md and .sql file would make the spelled set effectively "every word", and the
# scan could then never report anything -- which is the always-passes checker
# this repo has measured. The narrower nets above are the decision; this stub
# records that the wider one was considered and rejected, so a later reader does
# not "fix" it into uselessness.


def condition_spans(text):
    """Char ranges that GATE something: if/while/ternary tests, &&/|| operands,
    and `!x`. Returns a list of (start, end).

    Parenthesis-matched rather than regex-terminated, because an `if` condition
    routinely contains its own parentheses and a `.*?\\)` would stop at the
    first inner one -- which would silently shrink the scanned region and make
    the scan quieter than it looks.
    """
    spans = []
    for m in re.finditer(r'\b(?:if|while)\s*\(', text):
        i = m.end() - 1
        depth = 0
        for j in range(i, len(text)):
            if text[j] == '(':
                depth += 1
            elif text[j] == ')':
                depth -= 1
                if depth == 0:
                    spans.append((m.end(), j))
                    break
    # A ternary TEST: from the start of the line (or the last `(`/`,`/`=`) to
    # the `?`. Approximate on purpose -- over-reaching here only widens what is
    # scanned, and every finding is printed with its line.
    for m in re.finditer(r'\?', text):
        start = max(text.rfind('\n', 0, m.start()),
                    text.rfind('(', 0, m.start()),
                    text.rfind(',', 0, m.start()),
                    text.rfind('=', 0, m.start()))
        if start >= 0 and m.start() - start < 300:
            spans.append((start + 1, m.start()))
    # `&&` / `||` operands and `!x` -- take a window either side.
    for m in re.finditer(r'&&|\|\||!(?!=)', text):
        spans.append((max(0, m.start() - 160), min(len(text), m.end() + 160)))
    return spans


def main(argv):
    if '--list-builtins' in argv:
        for p in sorted(BUILTIN_PROPS):
            print(p)
        print('\n%d names. CRITERIA_VERSION %s' % (len(BUILTIN_PROPS), CRITERIA_VERSION))
        return EXIT_CLEAN

    code_files, notes = tracked(*CODE_PATTERNS)
    key_files, _ = tracked(*KEY_PATTERNS)
    if not code_files:
        print('COULD NOT RUN: `git ls-files` returned no code files. That is a '
              'broken invocation, not a clean repo.')
        return EXIT_COULD_NOT_RUN

    # ── THE SPELLED UNIVERSE, over the WHOLE repo ───────────────────────────
    # The stripped text is CACHED because the biggest files appear in both lists
    # and stripping stonedesk.html twice is the difference between a run
    # somebody makes and one they skip.
    spelled = set()
    unreadable = []
    stripped_cache = {}
    for f in key_files:
        p = os.path.join(REPO, f)
        try:
            text = code_only(f, read(p))
            if f.endswith(('.js', '.cjs', '.mjs', '.html')):
                stripped_cache[f] = text
            spelled |= spelled_names(text)
        except (IOError, OSError) as e:
            unreadable.append('%s could not be read (%s), so its field names '
                              'are MISSING from the spelled universe -- every '
                              'name only it spells would read as a ghost' % (f, e))

    findings, dormant, external, judged = [], [], [], 0
    contracts_hit = set()
    for f in code_files:
        p = os.path.join(REPO, f)
        try:
            raw = read(p)
        except (IOError, OSError) as e:
            unreadable.append('%s could not be read (%s) -- NOT scanned' % (f, e))
            continue
        if f.endswith('.py'):
            # Python files are in the KEY universe (they spell field names in
            # strings) but are not scanned for JS-shaped reads.
            continue
        # Comments AND string interiors blanked here -- the subject is CODE, so
        # a `.field` inside a refusal message must not read as a property read.
        # Different from the spelled pass, which keeps strings because a string
        # key IS a spelling. Two passes, two questions, stated so a later reader
        # does not collapse them onto the cache.
        src = strip_comments(raw, strings=True)
        judged += 1
        gates = condition_spans(src)
        if not gates:
            continue
        seen = set()
        for m in READ_RE.finditer(src):
            obj, field = m.group(1), m.group(2)
            if field in BUILTIN_PROPS or field in spelled:
                continue
            if obj in ('Math', 'JSON', 'Object', 'Array', 'String', 'Number',
                       'Date', 'Promise', 'console', 'process', 'window',
                       'document', 'localStorage', 'sessionStorage'):
                continue
            if not any(a <= m.start() < b for a, b in gates):
                continue
            line = src.count('\n', 0, m.start()) + 1
            key = (f, field, line)
            if key in seen:
                continue
            seen.add(key)
            if field in EXTERNAL_FIELDS:
                contracts_hit.add(EXTERNAL_FIELDS[field])
                external.append('%s:%d  `%s.%s` -- declared: %s'
                                % (f, line, obj, field, EXTERNAL_FIELDS[field]))
                continue
            if obj in REQUEST_OBJECTS and f.startswith('api/'):
                dormant.append('%s:%d  `%s.%s` -- a REQUEST field no caller in '
                               'this repo sends. Usually dormancy (the feature '
                               'has no client yet), not a wrong-field gate. '
                               'Read the handler before treating it as either.'
                               % (f, line, obj, field))
                continue
            findings.append('%s:%d  `%s.%s` GATES a branch and `%s` is never '
                            'written, never a key and never quoted anywhere in '
                            'the repo -- the condition cannot be true'
                            % (f, line, obj, field, field))

    print('GHOST FIELD READ SCAN -- a branch gated on a name nothing sets')
    print('  criteria                 : %s' % CRITERIA_VERSION)
    print('  files scanned for gates  : %d' % judged)
    print('  files read for spellings : %d' % len(key_files))
    print('  distinct field spellings : %d' % len(spelled))
    print('  builtin props excluded   : %d   (--list-builtins to read them)'
          % len(BUILTIN_PROPS))
    for n in notes:
        print('  excluded: %s' % n)

    # ── THE TWO OTHER BUCKETS, PRINTED RATHER THAN DROPPED ──────────────────
    if external:
        print('\nDECLARED THIRD-PARTY CONTRACTS (%d reads) -- not findings, and '
              'the owner is named so\na reader can check the shape against that '
              'vendor rather than against this file:' % len(external))
        for e in sorted(external):
            print('  . %s' % e)
    if dormant:
        print('\nREQUEST FIELDS NO CALLER SENDS (%d) -- a DIFFERENT finding, '
              'reported separately\nbecause "no client yet" and "this gate reads '
              'the wrong field" are not the same thing:' % len(dormant))
        for d in sorted(dormant):
            print('  ~ %s' % d)

    # AN EXCLUSION THAT MATCHED NOTHING IS REPORTED. See EXTERNAL_CONTRACTS.
    unused = [c for c in EXTERNAL_CONTRACTS if c not in contracts_hit]
    if unused:
        print('\nDECLARED CONTRACTS THAT MATCHED NOTHING (%d) -- an exclusion '
              'doing no work is a place\nto hide a real field. Delete it or say '
              'why it is still here:' % len(unused))
        for c in sorted(unused):
            print('  ? %s' % c)

    if '--json' in argv:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'findings': findings,
                          'request_fields_no_caller': dormant,
                          'declared_external': external,
                          'unused_declarations': unused,
                          'could_not_run': unreadable}, indent=2))

    return finish(findings, could_not_run=unreadable, clean_line=(
        '\nCLEAN -- no gate in any scanned file reads a field name that is '
        'unspelled everywhere.\nTHAT IS NARROWER THAN "no gate reads the wrong '
        'field": a name spelled\nsomewhere else for an unrelated reason clears '
        'condition 3 by construction.\nSee the header for the two members of '
        'this family that are still undecided.'))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
