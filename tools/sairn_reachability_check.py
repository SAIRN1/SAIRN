#!/usr/bin/env python
"""tools/sairn_reachability_check.py -- is a shipped feature actually reachable?

THE CLASS. On 2026-08-30/31 three complete, working, AI-backed StoneDesk
features -- Document Upload + Analysis, Feature 9 Compare, and the multi-modal
camera path -- were found to be unreachable by a customer. Nothing was broken.
Each injected its ONLY trigger button into `#sairn-intake-actions`, an element
that exists solely as an empty `display:none` placeholder. The code was correct,
the API worked, the panels rendered. There was simply no way in.

Guardian 0b asks whether a number has a function behind it. This asks the
opposite question: the function is real -- can anyone REACH it?

Three detectors, deliberately narrow, because a reachability checker that
over-reports is one nobody runs:

  R1  STUB COLLISION -- an id exists BOTH as an empty display:none placeholder
      in markup AND as something the JS creates. getElementById returns the
      first in document order, which is always the stub, so install-once guards
      refuse to install and later lookups address the wrong element.

  R2  INJECTED INTO A HIDDEN CONTAINER -- JS appends a control into an element
      whose markup carries display:none. The control exists and works; nobody
      can see it.

  R3  ORPHAN ENTRY POINT -- a window.<name> = function that no markup handler,
      no other JS, and no event wiring ever calls. This is the shape that hid
      openCompare / openDocModal / openCamera.

Usage:
    python tools/sairn_reachability_check.py [file.html ...]     # default *.html

Exit 0 clean, 1 if anything is found.

KNOWN LIMITS, stated because they bound the claim:
  * Static. It cannot see a handler attached at runtime from a computed name,
    nor a container un-hidden by JS. R2 in particular has false positives when
    something later clears the inline style -- verify before believing.
  * R3 ignores functions referenced in comments, which is deliberate; a mention
    in prose is not a caller.
  * Clean output means "no unreachable feature of THESE THREE SHAPES", not
    "every feature is reachable". Only a browser settles that.
"""
import re
import os
import json
import sys
import glob
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STUB = re.compile(r'<div id="([a-zA-Z0-9_-]+)"[^>]*style="display:none"[^>]*>\s*</div>')
JS_CREATES = re.compile(r"\.id\s*=\s*['\"]([a-zA-Z0-9_-]+)['\"]")
WINDOW_FN = re.compile(r'window\.([a-zA-Z_$][\w$]*)\s*=\s*(?:async\s+)?function')
APPEND = re.compile(r"getElementById\(['\"]([a-zA-Z0-9_-]+)['\"]\)[^;\n]{0,120}?\.(?:appendChild|insertBefore)\(")
# NO COMMENT STRIPPING, and that is the corrected decision rather than a
# shortcut. Two stripper attempts both destroyed real code on stonedesk.html:
#   1. `//[^\n]*` truncated every line containing an https:// URL, which deleted
#      real onclick handlers and made reachable functions look orphaned.
#   2. `/\*.*?\*/` matched across `/*` and `*/` sequences living inside JS
#      strings and regexes, removing 1.2 MB of a 2.2 MB file -- more than half.
#      sdAIQExport was reported as an orphan while `onclick="sdAIQExport()"` sat
#      inside the deleted region.
# So this searches RAW SOURCE. The cost is that a function named only in a
# comment counts as "used", so R3 under-reports. That is the safe direction for
# a checker: a missed orphan is a gap, a fabricated one trains people to ignore
# the tool.
# Referenced without being called: setTimeout(fn), addEventListener('x', fn),
# btn.onclick = fn, [fn, fn2]. Any of these makes it reachable.
REFERENCED = r'(?:[=,(]\s*(?:window\.)?%s\b(?!\s*[=(]))'


def scan(path):
    src = open(path, encoding='utf-8', errors='replace').read()
    bare = src   # see the NO COMMENT STRIPPING note above
    stubs = set(STUB.findall(src))
    created = set(JS_CREATES.findall(src))
    out = []

    for i in sorted(stubs & created):
        out.append(('R1', i, 'stub placeholder squats an id the JS also creates'))

    for i in sorted(set(APPEND.findall(src)) & stubs):
        out.append(('R2', i, 'JS injects into a container that is display:none in markup'))

    # Overwriting a browser built-in is a monkey-patch, not a feature entry
    # point -- window.fetch/onload/XMLHttpRequest are reached by the platform,
    # not by a caller in this file.
    BUILTINS = {'fetch', 'onload', 'onerror', 'onbeforeunload', 'onclick',
                'XMLHttpRequest', 'alert', 'confirm', 'prompt', 'open', 'print',
                'addMsg'}
    for fn in sorted(set(WINDOW_FN.findall(bare))):
        if fn in BUILTINS:
            continue
        # A deliberate empty no-op shim is a RETIRED feature, not an unreachable
        # one. sairnmechanical ships `window.savePins=function(){}` beside a
        # comment saying roles now come from the server on login. Flagging those
        # is the checker misreading intent, so an empty body is skipped.
        if re.search(r'window\.%s\s*=\s*(?:async\s+)?function\s*\([^)]*\)\s*\{\s*\}'
                     % re.escape(fn), bare):
            continue
        called = len(re.findall(r'\b%s\s*\(' % re.escape(fn), bare))
        referenced = len(re.findall(REFERENCED % re.escape(fn), bare))
        if called == 0 and referenced == 0:
            out.append(('R3', fn, 'window.%s is defined but never called or wired' % fn))
    return out


# ── LIVE MODE, added 2026-09-01 ────────────────────────────────────────────
# The docstring above admits the limit that matters: "Static. It cannot see a
# handler attached at runtime from a computed name." Every SAIRN app builds its
# tables by assigning innerHTML from JS template strings, so a button a
# customer clicks every day exists nowhere a grep can read it. R3 therefore
# reports orphans that are not orphans, and its own summary line has to tell
# people not to believe it -- which is the state a standing check cannot be in.
#
# --live takes a snapshot of the RENDERED DOM (produced by
# tools/sairn_dom_snapshot.js, run in the browser after clicking through the
# app) and clears any R3 whose name is actually wired in the live tree.
#
# THE SNAPSHOT CAN LIE BY OMISSION, so it is not trusted blindly. A handler on
# a panel nobody opened is absent from it and would look unreachable. The
# snapshot records panels_seen/panels_total and this refuses to clear anything
# from a snapshot that saw less than MIN_PANEL_COVERAGE of the app -- an
# under-clicked snapshot is a could-not-tell, not a pass. Same rule as the SQL
# preflight's --require-live: "could not tell" must never render as clean.
MIN_PANEL_COVERAGE = 0.60


def load_snapshots(paths):
    import json
    snaps = []
    for p in paths:
        try:
            with open(p, encoding='utf-8') as fh:
                snaps.append((p, json.load(fh)))
        except Exception as e:
            print('SNAPSHOT UNREADABLE: %s (%s)' % (p, e))
            return None
    return snaps


def apply_live(rows, snaps):
    """Returns (kept, cleared, coverage_problem)."""
    wired, ids, seen, total, gated = set(), set(), 0, 0, False
    for _, s in snaps:
        wired |= set(s.get('handler_names') or [])
        ids |= set(s.get('element_ids') or [])
        # panels_with_handlers, not panels_seen -- see the note in
        # tools/sairn_dom_snapshot.js. Visibility is the wrong metric: every
        # panel but the active one is display:none by design, so a
        # visibility-based floor never clears anything.
        seen += int(s.get('panels_with_handlers') or s.get('panels_seen') or 0)
        total += int(s.get('panels_total') or 0)
        gated = gated or bool(s.get('gated'))
    if gated:
        return rows, [], ('snapshot was taken on the LICENCE GATE, so it describes the gate '
                          'and nothing else -- get into the app and retake it')
    coverage = (seen / total) if total else 0.0
    if total == 0 or coverage < MIN_PANEL_COVERAGE:
        return rows, [], (
            'snapshot has handlers in %d of %d panels (%.0f%%); below the %.0f%% floor, so '
            'it clears nothing -- open the app properly and retake it'
            % (seen, total, coverage * 100, MIN_PANEL_COVERAGE * 100))
    kept, cleared = [], []
    for code, name, why in rows:
        if code == 'R3' and name in wired:
            cleared.append((code, name, 'wired at RUNTIME (present in a live on*= handler) -- static scan could not see it'))
        else:
            kept.append((code, name, why))
    return kept, cleared, None


# ── ACKNOWLEDGED EXEMPTIONS (2026-09-02) ────────────────────────────────────
# Added when this check was promoted to BLOCKING. A blocking gate with no way to
# record a justified exception refuses correct code forever, and a gate that
# refuses correct code gets switched off -- the same reasoning that gave the SQL
# preflight its UNDECLARED_TABLE carve-out and the push gate its
# SAIRN_SEED_GATE=off, made specific and reviewable instead of a blanket
# override.
#
# An exemption is a claim that the CHECKER IS WRONG about a finding. A finding
# that is real and unfixed belongs in SAIRN-BACKLOG.md. --check-exemptions
# reports any entry that no longer matches a live finding as STALE, so this file
# cannot quietly accumulate justifications for code that has moved on.
EXEMPTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'reachability_exemptions.json')


def load_exemptions():
    """Returns (set_of_(file,code,name), error_or_None).

    A MISSING file is fine -- no exemptions. An UNREADABLE or malformed one is
    NOT: silently treating a corrupt exemption file as "no exemptions" would
    turn a typo into a wall of blocked findings, and silently treating it as
    "everything exempt" would be worse. Either way the caller is told.
    """
    if not os.path.isfile(EXEMPTIONS_FILE):
        return set(), None
    try:
        with open(EXEMPTIONS_FILE, encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception as e:
        return set(), 'exemption file is unreadable (%s): %s' % (type(e).__name__, e)
    out = set()
    for row in (data.get('exemptions') or []):
        f, c, n = row.get('file'), row.get('code'), row.get('name')
        if not (f and c and n):
            return set(), 'an exemption entry is missing file/code/name'
        if not str(row.get('reason') or '').strip():
            return set(), 'exemption %s/%s carries no reason -- a bare id is not a justification' % (f, n)
        out.add((f, c, n))
    return out, None


def main(argv):
    args = [a for a in argv[1:]]
    live_paths, require_live, check_exemptions = [], False, False
    rest = []
    i = 0
    while i < len(args):
        if args[i] == '--live' and i + 1 < len(args):
            live_paths.append(args[i + 1]); i += 2; continue
        if args[i] == '--require-live':
            require_live = True; i += 1; continue
        if args[i] == '--check-exemptions':
            check_exemptions = True; i += 1; continue
        rest.append(args[i]); i += 1

    exempt, exempt_err = load_exemptions()
    if exempt_err:
        # Fail CLOSED on a broken exemption file. The alternative -- carrying on
        # with an empty set -- silently converts a typo into a wall of blocked
        # findings and invites someone to delete the file to make it stop.
        print('BLOCKING: %s' % exempt_err)
        print('Fix tools/reachability_exemptions.json; it is not optional once entries exist.')
        return 2

    targets = rest or sorted(glob.glob('*.html'))
    snaps = load_snapshots(live_paths) if live_paths else None
    if live_paths and snaps is None:
        return 2
    if require_live and not snaps:
        print('BLOCKING: --require-live was asked for and no readable DOM snapshot was given.')
        print('Produce one with tools/sairn_dom_snapshot.js, then pass --live <file>.')
        print('"Could not tell" is not a pass.')
        return 2

    total, cleared_total, coverage_note = 0, 0, None
    matched = set()          # exemptions that matched a real finding this run
    exempted_count = 0
    for path in targets:
        rows = scan(path)
        # Exempt AFTER scanning, never by skipping the scan, so an entry that
        # stops matching a real finding is still visible as stale.
        exempted_here = [r for r in rows if (path, r[0], r[1]) in exempt]
        rows = [r for r in rows if (path, r[0], r[1]) not in exempt]
        matched.update((path, c, n) for c, n, _ in exempted_here)
        if snaps:
            rows, cleared, problem = apply_live(rows, snaps)
            coverage_note = coverage_note or problem
            cleared_total += len(cleared)
        else:
            cleared = []
        if not rows and not cleared:
            continue
        print('=== %s ===' % path)
        for code, name, why in rows:
            print('  %s  %-34s %s' % (code, name, why))
        for code, name, why in cleared:
            print('  ok  %-34s %s' % (name, why))
        for code, name, why in exempted_here:
            print('  --  %-34s %s [EXEMPT]' % (name, why))
        exempted_count += len(exempted_here)
        total += len(rows)
    print('')
    if coverage_note:
        print('COVERAGE: %s' % coverage_note)
    if cleared_total:
        print('%d static finding(s) cleared by the live DOM.' % cleared_total)
    stale = sorted(exempt - matched)
    if exempted_count:
        print('%d finding(s) suppressed by tools/reachability_exemptions.json.' % exempted_count)
    if stale:
        # A stale exemption is not a blocker -- it suppresses nothing -- but it
        # is a justification for code that has moved on, and left unsaid it
        # becomes the reason a future real finding gets waved through.
        print('')
        print('STALE EXEMPTIONS -- these no longer match any finding and should be deleted:')
        for f, c, n in stale:
            print('    %s  %s  %s' % (f, c, n))
    if total:
        print('%d reachability finding(s) across %d file(s).' % (total, len(targets)))
        if snaps and not coverage_note:
            print('Checked against the RENDERED DOM, so R3 here is no longer a maybe.')
        else:
            print('R1/R2 are near-certain. R3 needs a read before you believe it --')
            print('pass --live <snapshot.json> to settle it against the real page.')
        return 1
    if coverage_note:
        return 2
    print('clean -- no unreachable features of these three shapes in %d file(s)' % len(targets))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
