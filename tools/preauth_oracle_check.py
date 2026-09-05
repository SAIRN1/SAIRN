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
    try:
        with io.open(ACCEPTED_PATH, encoding='utf-8') as fh:
            return {(e['file'], e['line']): e.get('reason', '') for e in json.load(fh)}
    except (IOError, ValueError):
        return {}


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


def main(argv):
    accepted = load_accepted()
    files = [a for a in argv if not a.startswith('--')]
    disclosure = oracle = unbounded = 0
    for path in handlers(files):
        rel, boundary, found = scan(path)
        if boundary is None:
            unbounded += 1
            print('NO AUTH BOUNDARY  %s  -- nothing to be "before"; read it rather '
                  'than assuming it is public' % rel)
            continue
        for line, tier, code, text in found:
            if (rel, line) in accepted:
                continue
            if tier == 'DISCLOSURE':
                disclosure += 1
            else:
                oracle += 1
            print('%-11s %s:%d  [%s]  %s' % (tier, rel, line, code, text))
    print('PREAUTH_DISCLOSURES:%d' % disclosure)
    print('PREAUTH_ORACLES:%d' % oracle)
    print('HANDLERS_WITH_NO_AUTH_BOUNDARY:%d' % unbounded)
    print('NOTE: a clean run means no refusal matched these SHAPES above the '
          'first auth call. It cannot tell you whether a leak matters -- see '
          'the header.')
    return 1 if disclosure else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
