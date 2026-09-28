#!/usr/bin/env python3
"""tools/auth_header_name_sweep.py -- every caller that sends a session must
spell the header the way the SERVER reads it, and the expected name is DERIVED
from the server rather than typed here.

    python tools/auth_header_name_sweep.py
    python tools/auth_header_name_sweep.py --list
    python tools/auth_header_name_sweep.py --baseline

Exit 0 no worse than pinned, 1 a regression, 2 COULD NOT TELL.

── THE DEFECT ─────────────────────────────────────────────────────────────
tools/alf_facility_role_gate_live_probe.py sent the session as
`X-Session-Token`. api/_lib/auth.js's tokenFromRequest() reads
`req.headers['x-sd-auth']` AND NOTHING ELSE. So every request that probe ever
made carried a licence and no session, every role received the identical
no-session answer, and the role differentiation the file exists to demonstrate
was never exercised once.

A WRONG HEADER NAME IS THE QUIETEST POSSIBLE FAILURE. Nothing 400s. The request
is well-formed, the server simply sees no session and answers the
no-session branch, so the caller gets a real HTTP answer to a question it did not
ask. Found by tools/gate_caller_impact.py and fixed in 8435809a.

WHAT KEPT IT FROM PUBLISHING A LIE was the probe's own CONTROL arm: with no
session, management gets 401 rather than "allowed", so the
`management must still be ALLOWED` arm could not pass and the probe reported
UNVERIFIED -- the third state -- instead of a false clean. That is the argument
for control arms in one sentence.

── WHY A SWEEP AND NOT A GREP ─────────────────────────────────────────────
A grep for `X-Session-Token` answers today and nothing else. This derives the
correct name FROM api/_lib/auth.js, so the day somebody renames the header the
sweep re-derives it and every caller still using the old spelling fails -- rather
than the check continuing to pass against a name typed into a tool.

DERIVATION IS FAIL-CLOSED. If tokenFromRequest cannot be found, or reads more
than one header, or reads none, this exits 2 COULD NOT TELL and names why. It
never falls back to a hardcoded default, because a default is exactly the
second copy of a fact that lets the two drift apart.

── WHAT IT CANNOT DO ──────────────────────────────────────────────────────
It matches header ASSIGNMENTS in source text. A header name built from a
variable, read from an env var, or set by a library is invisible to it, so
callers-with-a-session is a FLOOR and is reported as such. It also cannot tell
whether a caller SHOULD send a session -- an unauthenticated endpoint correctly
sends none, and tools/gate_caller_impact.py is the tool for that question.
"""
import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN = os.path.join(REPO, 'docs', 'auth-header-name-coverage.json')
AUTH = os.path.join(REPO, 'api', '_lib', 'auth.js')

# Anything that looks like it is meant to carry a session or auth token.
SESSION_ISH = re.compile(
    r"""['"]((?:x-|X-)[A-Za-z0-9-]*(?:auth|session|token|Auth|Session|Token)"""
    r"""[A-Za-z0-9-]*)['"]""")

# A file that REPLACES tokenFromRequest is exempt BY CONSTRUCTION, not by name:
# it never reaches the server's reader, so the server's header name does not
# apply to it. The exemption expires by itself the moment the stub is removed.
OVERRIDES_READER = re.compile(
    r"""tokenFromRequest\s*[:=]\s*(?:function|\(|async)"""
    r"""|['"]tokenFromRequest['"]\s*:""")

SCAN_DIRS = ('tools', 'tests', 'api', 'scripts')
SKIP_NAMES = {'x-vercel-challenge-token'}   # Vercel's own, not ours


class CouldNotTell(Exception):
    pass


def server_header():
    """The ONE header tokenFromRequest reads, derived from api/_lib/auth.js."""
    if not os.path.isfile(AUTH):
        raise CouldNotTell('api/_lib/auth.js does not exist, so the expected '
                           'header could not be derived. NOT a pass.')
    src = io.open(AUTH, encoding='utf-8', errors='replace').read()
    m = re.search(r'function\s+tokenFromRequest\s*\([^)]*\)\s*\{(.*?)\n\}',
                  src, re.S)
    if not m:
        raise CouldNotTell(
            'tokenFromRequest() was not found in api/_lib/auth.js -- the shape '
            'moved and NOTHING was derived. This is not "no header".')
    names = re.findall(r"""req\.headers\[\s*['"]([^'"]+)['"]\s*\]""", m.group(1))
    if not names:
        raise CouldNotTell(
            'tokenFromRequest() reads no req.headers[...] entry. Either it now '
            'takes the token some other way, or the derivation is broken; '
            'either way nothing was checked.')
    uniq = sorted(set(n.lower() for n in names))
    if len(uniq) != 1:
        raise CouldNotTell(
            'tokenFromRequest() reads %d different headers (%s). This sweep '
            'assumes exactly one and will not guess which callers should use '
            'which.' % (len(uniq), ', '.join(uniq)))
    return uniq[0]


def scan(expected):
    """(senders, wrong) -- files that set a session-ish header, and the bad ones."""
    senders, wrong, stubbed = {}, [], set()
    for d in SCAN_DIRS:
        base = os.path.join(REPO, d)
        if not os.path.isdir(base):
            continue
        for root, _, names in os.walk(base):
            for n in sorted(names):
                if not n.endswith(('.py', '.js')):
                    continue
                path = os.path.join(root, n)
                rel = os.path.relpath(path, REPO).replace(os.sep, '/')
                try:
                    src = io.open(path, encoding='utf-8', errors='replace').read()
                except OSError as exc:
                    raise CouldNotTell('%s could not be read (%s) -- NOT a pass'
                                       % (rel, exc))
                got = set()
                for m in SESSION_ISH.finditer(src):
                    name = m.group(1).lower()
                    if name in SKIP_NAMES:
                        continue
                    got.add(name)
                if not got:
                    continue
                senders[rel] = sorted(got)
                # ── A FILE THAT REPLACES tokenFromRequest OWNS ITS HEADER ────
                # The first cut reported 20 mismatches on `x-test-token` and
                # every one was WRONG. Those suites stub the reader itself:
                #     authMod.tokenFromRequest = (req) => req.headers['x-test-token']
                # so the real server's name is irrelevant to them -- they never
                # reach it, and the header is theirs to choose.
                #
                # NAMING THEM IN A SKIP-LIST WOULD HAVE BEEN THE WRONG FIX and
                # is the hole this platform keeps closing. The DISCRIMINATOR is
                # a property of the file: does it override the reader? If yes
                # it is exempt by construction, and the exemption expires the
                # moment the stub is removed. If no, it is talking to the real
                # server and must spell the header the way the server reads it.
                if OVERRIDES_READER.search(src):
                    stubbed.add(rel)
                    continue
                for name in sorted(got):
                    if name != expected:
                        wrong.append((rel, name))
    if not senders:
        raise CouldNotTell(
            'no file anywhere sets a session-ish header -- the spelling moved '
            'and NOTHING was measured. This is not "no callers".')
    return senders, wrong, stubbed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--baseline', action='store_true')
    args = ap.parse_args(argv)

    try:
        expected = server_header()
        senders, wrong, stubbed = scan(expected)
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2

    # A name used by only one or two files, where another spelling dominates, is
    # the shape the defect took. Reported separately from a flat mismatch count.
    counts = {}
    for names in senders.values():
        for n in names:
            counts[n] = counts.get(n, 0) + 1

    print('AUTH HEADER NAME SWEEP')
    print('expected header, DERIVED from api/_lib/auth.js tokenFromRequest(): %r'
          % expected)
    print('')
    print('%d file(s) set a session-ish header, of which %d REPLACE'
          % (len(senders), len(stubbed)))
    print('tokenFromRequest and are exempt by construction -- they never reach')
    print('the reader, so the server header name does not apply to them.')
    for n in sorted(counts, key=lambda k: -counts[k]):
        mark = '  <-- expected' if n == expected else '  <-- NOT what the server reads'
        print('  %-28s %4d file(s)%s' % (n, counts[n], mark))
    print('')

    if wrong:
        print('  MISMATCHED -- these callers send a header the server never reads.')
        print('  Nothing 400s: the request is well formed, the server simply sees')
        print('  no session and answers the no-session branch.')
        for rel, name in wrong:
            print('   %-58s %s' % (rel, name))
        print('')
    if args.list:
        for rel in sorted(senders):
            print('   %-58s %s' % (rel, ','.join(senders[rel])))
        print('')

    # CHECKED is the NON-EXEMPT population. Counting the 37 stubbed files as
    # "carrying the derived name" would inflate the figure with files the
    # question does not apply to -- the coverage-arithmetic defect this platform
    # records, where the denominator quietly absorbs what was never checked.
    checked = len(senders) - len(stubbed)
    print('CHECKED / UNIVERSE: %d of %d NON-EXEMPT session-sending files carry '
          'the derived' % (checked - len({r for r, _ in wrong}), checked))
    print('name. THE UNIVERSE IS A FLOOR: a header built from a variable, read')
    print('from an env var, or set by a library is invisible to a source scan,')
    print('so "senders" undercounts and cannot be treated as complete.')
    print('')

    if args.baseline:
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            '_what': 'Pinned auth-header-name coverage. Written by '
                     'tools/auth_header_name_sweep.py --baseline. A ratchet: '
                     '`mismatched` must never rise.',
            '_why': 'A wrong header name is the quietest failure available: the '
                    'request is well formed and the server answers the '
                    'no-session branch, so the caller gets a real HTTP answer to '
                    'a question it did not ask.',
            'expected_header': expected,
            'session_sending_files': len(senders),
            'stubbed_exempt': len(stubbed),
            'mismatched': len(wrong),
            'mismatched_files': sorted({r for r, _ in wrong}),
            'names_seen': counts,
        }, indent=2, sort_keys=True) + '\n')
        print('wrote %s' % os.path.relpath(PIN, REPO))
        return 0

    if not os.path.isfile(PIN):
        sys.stderr.write('COULD NOT TELL -- %s does not exist, so NOTHING was '
                         'compared. Run --baseline once.\n'
                         % os.path.relpath(PIN, REPO))
        return 2
    try:
        pin = json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        sys.stderr.write('COULD NOT TELL -- %s will not parse (%s). NOTHING WAS '
                         'COMPARED.\n' % (os.path.relpath(PIN, REPO), e))
        return 2
    was = pin.get('mismatched')
    if not isinstance(was, int):
        sys.stderr.write('COULD NOT TELL -- the pin carries no integer '
                         '`mismatched`.\n')
        return 2
    # A RENAMED HEADER IS A FINDING, NOT A SILENT RE-PIN. If the server's header
    # changed, every pinned figure was computed against a different question.
    if pin.get('expected_header') not in (None, expected):
        print('THE SERVER HEADER CHANGED: pinned %r, derived %r.'
              % (pin.get('expected_header'), expected))
        print('Every caller must be re-checked against the new name, and the pin')
        print('re-taken deliberately. This is not a regression and not a pass.')
        return 1
    if len(wrong) > was:
        print('REGRESSION -- callers sending the wrong header rose from %d to %d.'
              % (was, len(wrong)))
        return 1
    if len(wrong) < was:
        print('IMPROVED -- fell from %d to %d. Re-pin:' % (was, len(wrong)))
        print('   python tools/auth_header_name_sweep.py --baseline')
        return 0
    print('OK -- no worse than pinned (%d mismatched).' % was)
    if was == 0:
        print('A RATCHET IS NOT A PASS. Zero mismatches means no caller spells it')
        print('wrong IN SOURCE; it does not mean every caller sends a session, or')
        print('that any of them sends a VALID one.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
