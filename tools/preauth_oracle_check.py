"""tools/preauth_oracle_check.py -- refusals an endpoint gives before it knows
who is asking.

    python tools/preauth_oracle_check.py            # every api/*.js handler
    python tools/preauth_oracle_check.py api/x.js   # named files

WHY THIS EXISTS (2026-09-05). Two endpoints were found with the same shape one
after the other, which is a pattern rather than two coincidences:

  * api/sd-data.js  -- a junk bearer token got a 400 naming all 268 registered
    resources, because the envelope gate ran above licence validation.
  * api/sd-sub-data.js -- the same ordering. Only three hardcoded names, so the
    enumeration was trivial, but the ORACLE was real: a caller holding no
    credential got a different refusal for a real resource than an invented
    one, a different one again for a refused verb, a 413 for an oversized
    payload and a 400 for malformed JSON.

Both were found by reading. Nothing looked for the class, so nothing could say
whether it was over. This does.

── WHAT IT MEASURES ──────────────────────────────────────────────────────
For each handler it finds the AUTHENTICATION BOUNDARY -- the first
`await validateLicenseKey(` or `verifySessionToken(` -- and reports every
refusal that answers ABOVE it, split into two tiers because they are not
equally serious:

  DISCLOSURE  the refusal message enumerates two or more names. This is the
              sd-data shape: the response hands an unauthenticated caller a
              list of what exists.
  ORACLE      any other body-dependent refusal above the boundary. It leaks no
              list, but a caller can still tell one input from another by
              which refusal comes back.

Two refusals are deliberately NOT counted, because neither depends on what
exists: the 405 method check, and the missing-bearer 401. Both answer the same
way for every request body there is.

── WHAT IT CANNOT DECIDE ─────────────────────────────────────────────────
Whether the leak MATTERS. `sd-auth.js` discloses six verb names that anyone
holding the app already knows; `sd-data.js` disclosed 268 table names across
every app on the platform. Same shape, different severity, and no parser can
tell them apart. So the output is a list to read, and triaged endpoints go in
tools/preauth_oracle_accepted.json with a reason -- the same convention as
tools/fail_open_accepted.json.

It also cannot see an endpoint with NO authentication boundary at all: a
public endpoint has nothing to be "before". Those are listed separately rather
than silently passing, because "no boundary found" and "nothing above the
boundary" are different answers and only one of them is good news.

And it only knows TWO boundaries by name. An endpoint authenticated by a
bespoke credential -- api/dnt-bi.js's BI feed token, api/sen-portal.js's and
api/stonedesk-track.js's link tokens -- has a real boundary this cannot see, so
its whole body reports as pre-auth. Those are triaged into the accepted file
with the reason, rather than teaching AUTH_RE every bespoke check and quietly
widening what counts as authenticated.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCEPTED_PATH = os.path.join(ROOT, 'tools', 'preauth_oracle_accepted.json')
DECLARED_PATH = os.path.join(ROOT, 'tools', 'public_endpoint_declarations.json')

# The first call that establishes WHO is asking. Anything answering above one
# of these answers to an unauthenticated caller.
AUTH_RE = re.compile(r'(await\s+validateLicenseKey\s*\(|verifySessionToken\s*\()')

# A refusal: res.status(NNN) with a 4xx or 5xx, captured with its message.
REFUSAL_RE = re.compile(r'res\.status\(\s*(\d{3})\s*\)\s*\.json\(\s*(\{.{0,400}?\})\s*\)', re.S)

# Refusals that cannot be an oracle: they answer identically for every body.
IGNORE_MESSAGES = (
    'Method not allowed',
    'Missing bearer license key',
    'Server configuration error',
)

# Two or more quoted names in one message is a list being handed out.
QUOTED_RE = re.compile(r"'([A-Za-z_][\w.\-]{2,})'")

# ...and so is a list JOINED IN at runtime. A first version matched quoted
# literals only, which under-reported by more than half: sd-auth.js writes its
# six verbs out by hand and was caught, while alf-, bld-, dnt-, law-, leg-,
# mech-, rf-, sdn- and sen-auth build the identical message with
# `ACTIONS.join(', ')` and were filed as harmless. Same disclosure, different
# spelling -- exactly the trap the storage-wrapper checks kept hitting.
#
# It is ONLY `.join(`. The first attempt at this fix also matched any 4+ letter
# uppercase token, on the theory that a bare `ACTIONS` reference would read the
# same way. That over-corrected past the bug it was fixing: it matched the word
# JSON in 'Invalid JSON body' and every structural error code -- NOT_FOUND,
# UPSTREAM, READ_FAILED -- and reported 74 disclosures, of which the great
# majority were neither. Verified by running it, not reasoned about.
JOINED_RE = re.compile(r'\.join\s*\(')

# `code: 'NOT_FOUND'` is the response's own machine-readable error code, not the
# name of something that exists. Strip it before counting names, or every
# two-field error envelope counts itself as a disclosure of one.
CODE_FIELD_RE = re.compile(r'\bcode\s*:\s*[\'"][^\'"]*[\'"]')


def strip_comments(src):
    """Blank out JS comments, preserving every byte offset and line number.

    NOT cosmetic. The first version matched the raw source, so AUTH_RE found
    its boundary in a HEADER COMMENT: api/law-auth.js line 26 and
    api/mech-auth.js line 44 both spell `verifySessionToken(` inside prose
    explaining the auth model. The boundary landed above `module.exports`, the
    whole handler counted as "after" it, and both files reported ZERO findings
    while carrying the same envelope-above-licence ordering as their eleven
    siblings. A checker that matches commentary about the code instead of the
    code certifies the defect it exists to find.

    String-aware, because a bare `//` strip would cut every REST URL in half
    and could blank a real refusal along with it.
    """
    out = list(src)
    i, n = 0, len(src)
    quote = None          # ' " or ` when inside a string literal
    while i < n:
        c = src[i]
        if quote:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in '\'"`':
            quote = c
            i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':
                out[i] = ' '
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            end = src.find('*/', i + 2)
            end = n if end == -1 else end + 2
            for j in range(i, end):
                if out[j] != '\n':
                    out[j] = ' '
            i = end
            continue
        i += 1
    return ''.join(out)


def load_accepted():
    """Accepted pre-auth refusals, matched by WHAT THEY ARE, not by where they sit.

    ── WHY THIS IS NOT KEYED ON A LINE NUMBER ANY MORE (2026-09-09) ──────────
    It was: {(file, line): reason}. That breaks in both directions, and both
    were reproduced in this repo rather than argued.

    THE NOISY DIRECTION, which is how it was found. Adding ONE import line near
    the top of api/sd-data.js shifted its 429 rate limiter from line 388 to 389,
    the exemption keyed at 388 stopped matching, and the tool reported a fresh
    ORACLE against code nobody had touched. An exemption that expires whenever
    anything above it moves generates a false finding on ordinary edits, and a
    gate that cries wolf on ordinary edits is one somebody switches off.

    THE SILENT DIRECTION, which is the dangerous one. The same drift runs the
    other way: a DIFFERENT refusal shifting INTO an exempted line inherits an
    exemption written for something else. This tool gates a push on the
    DISCLOSURE tier, so that is a blocking gate quietly ceasing to block, with
    nothing on screen to say so -- the exact shape this repo keeps recording.

    THE KEY IS NOW (file, status, match), where `match` is a substring the
    refusal's own text must contain -- normally its error-code identifier. A
    refusal cannot drift into somebody else's exemption because it would have to
    BE that refusal to match.

    WHAT THAT DELIBERATELY ALLOWS, said plainly rather than discovered later: a
    second refusal with the SAME status and the SAME code in the SAME file is
    covered by one entry. That is intended. Three of these already exist --
    api/stonedesk-track.js answers UPSTREAM identically at three lines -- and
    they are textually indistinguishable, so a line key was the only thing ever
    separating them. If an identical refusal is acceptable at one line it is
    acceptable at another; what is NOT acceptable is a different one inheriting
    the pass.

    `lines_when_written` is kept as a HUMAN HINT and is never matched on. main()
    reports it when it has drifted, so the file can be tidied without the drift
    ever having been able to change a verdict.
    """
    try:
        with io.open(ACCEPTED_PATH, encoding='utf-8') as fh:
            raw = json.load(fh)
    except (IOError, ValueError):
        return []
    out = []
    for e in raw:
        if not isinstance(e, dict) or 'file' not in e or 'match' not in e:
            # A malformed entry must not silently become a blanket pass, and it
            # must not silently vanish either -- it is surfaced by main() as an
            # exemption that matched nothing.
            continue
        out.append({
            'file': e['file'],
            'status': str(e.get('status', '')),
            'match': e['match'],
            'lines_when_written': e.get('lines_when_written') or (
                [e['line_when_written']] if e.get('line_when_written') is not None
                else ([e['line']] if e.get('line') is not None else [])),
            'reason': e.get('reason', ''),
            'hits': 0,
            'lines': [],
        })
    return out


def accepted_entry(accepted, rel, code, text):
    """The entry covering this refusal, or None. First match wins."""
    for e in accepted:
        if e['file'] == rel and e['status'] == code and e['match'] in text:
            return e
    return None


def handlers(paths):
    if paths:
        return [p if os.path.isabs(p) else os.path.join(ROOT, p) for p in paths]
    api = os.path.join(ROOT, 'api')
    out = []
    for base, dirs, files in os.walk(api):
        dirs[:] = [d for d in dirs if d != 'node_modules']
        for f in sorted(files):
            # _lib and _resources are helpers, not endpoints; *.test.js are tests.
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            rel = os.path.relpath(os.path.join(base, f), api).replace('\\', '/')
            if rel.startswith('_lib/') or rel.startswith('_resources/'):
                continue
            out.append(os.path.join(base, f))
    return out


def scan(path):
    src = strip_comments(io.open(path, encoding='utf-8', errors='replace').read())
    rel = os.path.relpath(path, ROOT).replace('\\', '/')
    m = AUTH_RE.search(src)
    if not m:
        return rel, None, []
    boundary = m.start()
    found = []
    for r in REFUSAL_RE.finditer(src):
        if r.start() >= boundary:
            break
        code, blob = r.group(1), r.group(2)
        if not code.startswith(('4', '5')):
            continue
        if code == '405':
            continue          # a method check answers the same for every body
        if any(ig in blob for ig in IGNORE_MESSAGES):
            continue
        line = src[:r.start()].count('\n') + 1
        names = QUOTED_RE.findall(CODE_FIELD_RE.sub('', blob))
        # Drop the response's own structural keys, which are not disclosures.
        names = [n for n in names if n not in ('error', 'message', 'code')]
        tier = ('DISCLOSURE' if (len(set(names)) >= 2 or JOINED_RE.search(blob))
                else 'ORACLE')
        text = re.sub(r'\s+', ' ', blob)[:130]
        found.append((line, tier, code, text))
    return rel, boundary, found


def load_declared():
    """Endpoints declared to have no auth boundary ON PURPOSE, with a reason.

    ── WHY A DECLARATION AND NOT JUST A LIST (2026-09-08) ────────────────────
    This checker has always PRINTED the no-boundary handlers, and the header
    above has always said they must be READ rather than assumed public. Nothing
    recorded the outcome of reading them, so the list was re-triaged from
    scratch every time and, worse, a NEW one could be added with nothing to
    notice it.

    That is not hypothetical. api/claude.js was an open Anthropic proxy whose
    own comment said "this endpoint has no other auth beyond a client-supplied
    app_id" -- the design was known and written down IN THE FILE, and the
    consequence still went unnoticed until 2026-09-05.

    An UNDECLARED no-boundary handler now fails this checker, so the answer has
    to be written down once rather than re-derived by whoever looks next.
    """
    try:
        with io.open(DECLARED_PATH, encoding='utf-8') as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return None                      # unreadable: reported, never silently empty
    return {k: v for k, v in doc.items() if not k.startswith('_')}


def main(argv):
    accepted = load_accepted()
    declared = load_declared()
    files = [a for a in argv if not a.startswith('--')]
    disclosure = oracle = unbounded = undeclared = 0
    undeclared_names = []
    for path in handlers(files):
        rel, boundary, found = scan(path)
        if boundary is None:
            unbounded += 1
            if declared is None:
                print('NO AUTH BOUNDARY  %s  -- declarations file unreadable, so this '
                      'is UNTRIAGED rather than accepted' % rel)
            elif rel in declared:
                print('NO AUTH BOUNDARY  %s  -- declared %s: %s'
                      % (rel, declared[rel].get('class', '?'),
                         (declared[rel].get('reason', '') or '')[:90]))
            else:
                undeclared += 1
                undeclared_names.append(rel)
                print('UNDECLARED PUBLIC %s  -- no auth boundary and no entry in '
                      'tools/public_endpoint_declarations.json' % rel)
            continue
        for line, tier, code, text in found:
            hit = accepted_entry(accepted, rel, code, text)
            if hit is not None:
                hit['hits'] += 1
                hit['lines'].append(line)
                continue
            if tier == 'DISCLOSURE':
                disclosure += 1
            else:
                oracle += 1
            print('%-11s %s:%d  [%s]  %s' % (tier, rel, line, code, text))
    # ── BOOKKEEPING ON THE EXEMPTION FILE ITSELF ─────────────────────────────
    # An accepted-list that nobody audits is how a suppression outlives the
    # thing it suppressed. Neither of these changes the verdict -- they are
    # facts about the FILE, not about the code -- but both are printed, because
    # the alternative is a list that quietly rots.
    #
    # This block is skipped when specific files were named on the command line:
    # every entry for a file that was not scanned would report as stale, which
    # would be an artefact of the invocation rather than a fact about the file.
    if not files:
        stale = [e for e in accepted if e['hits'] == 0]
        drift = [e for e in accepted
                 if e['hits'] and e['lines_when_written']
                 and sorted(e['lines']) != sorted(e['lines_when_written'])]
        if stale:
            print('')
            for e in stale:
                print('STALE EXEMPTION  %s [%s] %s -- matched nothing. Either the '
                      'refusal was removed (delete this entry) or its text changed '
                      '(re-read it, then update `match`).'
                      % (e['file'], e['status'], e['match']))
        if drift:
            for e in drift:
                print('NOTE  %s [%s] %s -- now at %s, recorded as %s. The hint is '
                      'stale; the exemption still matched, because it is keyed on '
                      'the refusal and not on the line.'
                      % (e['file'], e['status'], e['match'],
                         ','.join(str(x) for x in sorted(e['lines'])),
                         ','.join(str(x) for x in sorted(e['lines_when_written']))))
        print('STALE_EXEMPTIONS:%d' % len(stale))
    print('PREAUTH_DISCLOSURES:%d' % disclosure)
    print('PREAUTH_ORACLES:%d' % oracle)
    print('HANDLERS_WITH_NO_AUTH_BOUNDARY:%d' % unbounded)
    print('UNDECLARED_PUBLIC_HANDLERS:%d' % undeclared)
    if undeclared:
        print('')
        print('An endpoint with no auth boundary is not a finding on its own -- some '
              'are public on purpose. What it must not be is UNANSWERED. Read each '
              'one and add an entry to tools/public_endpoint_declarations.json '
              'saying what actually protects it, or that nothing does and why that '
              'is acceptable:')
        for n in undeclared_names:
            print('    %s' % n)
    print('NOTE: a clean run means no refusal matched these SHAPES above the '
          'first auth call. It cannot tell you whether a leak matters -- see '
          'the header.')
    return 1 if (disclosure or undeclared) else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
