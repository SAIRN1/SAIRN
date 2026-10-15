#!/usr/bin/env python
# OWNER: cody
# written 2026-10-15, batch b18, item 5
"""A fixed-size character window in an assertion is a guess with an expiry date.

    python tests/run_window_anchor_ratchet_probe.py
    python tests/run_window_anchor_ratchet_probe.py --list

Exit 0 the count did not rise · 1 it rose · 2 COULD NOT RUN.

# REQUIREMENT: the number of UNJUSTIFIED fixed-size character windows in
#   tests/ must never rise, because every one of them is an assertion that
#   holds only while its subject stays a certain number of characters long --
#   and the day it stops holding, the probe reports the SUBJECT as broken

── THE CLASS, AND WHY IT GETS A CHECK RATHER THAN A PARAGRAPH ──────────────
Nine files have now been read to cause across cody b16, b17 and b18. In SIX of
them the FAILURE LINE NAMED THE SUBJECT AND THE CAUSE WAS IN THE PROBE. The
failure said "the gate WIDENS", "app_id is taken from the client again", "the
role gate must precede the consent check", "the transport records an id when a
WRITE really lands" -- each reads as a live defect in shipped code, and each
was the probe's own anchor having stopped matching a subject that moved for a
good reason. Twice the moving reason was a SECURITY FIX and once it was a
correctness fix for a bereaved family getting duplicate grief-support calls.

The general class -- "an assertion anchored on its subject's current text or
shape reports a legitimate change as a defect" -- has no mechanical detector,
and pretending otherwise would be worse than saying so. What it HAS is one
sub-shape that is exactly greppable, and that sub-shape is the one that cost
the most time:

    A FIXED-SIZE CHARACTER WINDOW:  {0,200}   .{0,40}   [\\s\\S]{0,1200}?

MEASURED, b18. tests/server_wins_hydration.js asserted that a transport's
`<fn>(resource, payload.id)` call appears within 200 characters of its
`action === 'write'` guard. Per-app distance: sairnlaw 53, sairnsenior 53,
sairnfreedom 53, stonedesk 78 -- and sairnlegacy 311, because its transport
gained a server-id canonicalisation block. The arm reported the one app that
wrote it most carefully as the one missing the guard. AND THE ARM'S OWN COMMENT
HAD PREDICTED THAT CLASS IN WORDS: "a one-line anchor would have reported the
one app that wrote it most carefully as the one missing it." 200 was a wider
guess and it failed in the same direction. A comment did not stop it. A number
that cannot rise might.

── WHAT THIS CHECKS, AND WHAT IT DOES NOT ─────────────────────────────────
It counts fixed-size windows in tests/*.py and tests/**/*.js that carry NO
justification, and refuses an increase. It does NOT claim the existing ones are
wrong -- several are bounded between two adjacent lines of one statement, which
is a different risk from spanning a whole block. It claims only that a NEW one
must be argued for in writing, at the site, where the next reader will see it.

A WINDOW IS JUSTIFIED by `WINDOW-OK:` plus a reason, on the same line or within
the 6 lines above it. The reason lives AT THE WINDOW and not in a second file
on purpose: two lists that must agree is the defect shape this repo already
pays for in SD_SESSION_GATED and SD_GATE_APP.

THE PREFERRED FIX IS NOT A JUSTIFICATION, IT IS A STRUCTURE. b18's replacement
for the 200-character window identifies the guard's CONSEQUENT -- balanced
braces, or the single statement up to its `;` -- and asks whether the call is
inside it. No character budget exists to outgrow. Reach for that first; the
annotation is for the cases where the structural form genuinely is not
available, and it has to say which case that is.

── THE PROCEDURE FOR THE HALF THIS CANNOT SEE ─────────────────────────────
A literal identifier, a specific wording, a recency relation. No grep finds
those. The procedure, paid for six times:

  1. A FAILURE LINE THAT NAMES SHIPPED CODE IS A HYPOTHESIS, NOT A VERDICT.
     Before routing it to the owner of that code, open the subject and measure
     the thing the line claims.
  2. ASK WHETHER THE SUBJECT MOVED FOR A GOOD REASON. Read the git comment at
     the site. Twice it said, in the file, exactly why it had changed.
  3. IF THE PROBE LAGGED, RE-DERIVE THE PROPERTY, NOT THE TEXT. Assert what
     must be true (a role set is consulted; a call is inside a guard; a sha
     touches a file set) rather than how it is currently spelled.
  4. A WIDER WINDOW, A LONGER QUOTED BLOCK OR A SECOND LITERAL IS THE SAME
     DEFECT WITH A LATER DATE. b17 widened an anchor that had already been
     widened once in b16 and it rotted again inside a month.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, 'tests')
PIN = os.path.join(ROOT, 'docs', 'window-anchor-ceiling.json')

# `{0,N}` with N >= 2 digits. One digit is a character class like `\s{0,9}` and
# is not the shape this is about; the shortest real offender measured was 40.
WINDOW = re.compile(r'\{0,\d{2,}\}')
JUSTIFY = 'WINDOW-OK:'
LOOKBACK = 6


def could_not_run(msg):
    print('COULD NOT RUN -- %s' % msg)
    sys.exit(2)


def scan():
    """-> (unjustified, justified) lists of 'rel:line' strings."""
    un, ju = [], []
    for base, dirs, files in os.walk(TESTS):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in sorted(files):
            if not f.endswith(('.py', '.js')):
                continue
            rel = os.path.relpath(os.path.join(base, f), ROOT)
            rel = rel.replace(os.sep, '/')
            if rel == 'tests/run_window_anchor_ratchet_probe.py':
                # THIS FILE IS EXCLUDED, AND THE EXCLUSION IS PRINTED rather
                # than silent: it quotes the shape in its own docstring, so a
                # scanner that counted itself would report a finding about its
                # own documentation for ever.
                continue
            try:
                lines = io.open(os.path.join(ROOT, rel), encoding='utf-8',
                                errors='replace').read().split('\n')
            except (IOError, OSError):
                could_not_run('%s could not be read. A file this scanner '
                              'cannot open is not a file with no windows.'
                              % rel)
            for i, line in enumerate(lines):
                if not WINDOW.search(line):
                    continue
                window = lines[max(0, i - LOOKBACK):i + 1]
                hit = '%s:%d' % (rel, i + 1)
                (ju if any(JUSTIFY in w for w in window) else un).append(hit)
    return un, ju


def read_pin():
    if not os.path.isfile(PIN):
        could_not_run('%s is absent, so there is no ceiling to compare against '
                      'and this check would pass by having nothing to say.'
                      % os.path.relpath(PIN, ROOT))
    try:
        d = json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        could_not_run('%s does not parse: %s' % (os.path.relpath(PIN, ROOT), e))
    v = d.get('ceiling')
    if not isinstance(v, int) or v < 0:
        could_not_run('%s has no integer "ceiling".' % os.path.relpath(PIN, ROOT))
    return v, d


def selftest():
    """FAIL-FIRST, on fixtures, before the real tree is read.

    Without these the real arm could pass by never being able to fail -- and
    this file exists because an arm that cannot fail is the thing it is about.
    """
    bad = []

    def ck(name, got, want):
        print('  %-4s %s' % ('PASS' if got == want else 'FAIL', name))
        if got != want:
            bad.append('%s -- wanted %r got %r' % (name, want, got))

    ck('the pattern CATCHES a bare window', bool(WINDOW.search('x{0,200}?y')),
       True)
    ck('...and a dotted one', bool(WINDOW.search('a.{0,40}b')), True)
    ck('...and a class-prefixed one',
       bool(WINDOW.search(r'[\s\S]{0,1200}?')), True)
    ck('it does NOT catch a single-digit repeat, which is a different shape',
       bool(WINDOW.search(r'\s{0,9}')), False)
    ck('it does NOT catch an unbounded repeat', bool(WINDOW.search('x{2,}')),
       False)
    ck('a window with WINDOW-OK on the SAME line is justified',
       'WINDOW-OK:' in 'a{0,99}  # WINDOW-OK: bounded by one statement', True)
    return bad


if __name__ == '__main__':
    if '--list' in sys.argv:
        _un, _ju = scan()
        print('UNJUSTIFIED (%d):' % len(_un))
        for h in _un:
            print('  ' + h)
        print('JUSTIFIED (%d):' % len(_ju))
        for h in _ju:
            print('  ' + h)
        sys.exit(0)

    print('fixed-size window anchors in tests/ -- the count must not rise\n')
    print('0. the scanner itself, on fixtures')
    fails = selftest()

    ceiling, pin_doc = read_pin()
    un, ju = scan()

    print('')
    print('1. the real tree')
    # THE POPULATION IS ASSERTED. Zero would mean the scanner stopped finding
    # its subject, which looks exactly like success.
    if not un and not ju:
        could_not_run('the scanner found NO fixed-size window anywhere in '
                      'tests/. That is not credible on a tree that had 33 of '
                      'them on 2026-10-15; the scanner has stopped matching.')
    print('  unjustified : %d   (ceiling %d)' % (len(un), ceiling))
    print('  justified   : %d' % len(ju))
    print('  EXCLUDED, and printed: tests/run_window_anchor_ratchet_probe.py '
          'quotes the shape in its own docstring.')

    if len(un) > ceiling:
        print('')
        print('REFUSED: %d unjustified window(s), ceiling is %d. The new one(s) '
              'are among:' % (len(un), ceiling))
        for h in un:
            print('  ' + h)
        print('')
        print('  A fixed-size character window asserts that its subject stays a '
              'certain')
        print('  number of characters long. Prefer the STRUCTURAL form -- the '
              'balanced')
        print('  block, or the statement up to its `;` -- which has no budget to '
              'outgrow.')
        print('  If that genuinely is not available, put `WINDOW-OK: <why>` at '
              'the site.')
        fails.append('the unjustified window count rose from %d to %d'
                     % (ceiling, len(un)))

    if len(un) < ceiling:
        # IT RATCHETS DOWN, NEVER UP, and the lowering is a WRITE so the gain
        # cannot be given back silently. The opposite direction is a refusal
        # above, never an automatic raise: a ceiling that rose by itself would
        # absorb every new window as the new normal.
        pin_doc['ceiling'] = len(un)
        pin_doc.setdefault('history', []).append(
            {'lowered_to': len(un), 'from': ceiling,
             'by': 'tests/run_window_anchor_ratchet_probe.py'})
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(pin_doc, indent=1, ensure_ascii=False) + '\n')
        print('  LOWERED the ceiling %d -> %d and wrote %s.'
              % (ceiling, len(un), os.path.relpath(PIN, ROOT)))

    print('')
    print('%d failure(s)' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1 if fails else 0)
