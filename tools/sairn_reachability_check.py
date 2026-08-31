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


def main(argv):
    targets = argv[1:] or sorted(glob.glob('*.html'))
    total = 0
    for path in targets:
        rows = scan(path)
        if not rows:
            continue
        print('=== %s ===' % path)
        for code, name, why in rows:
            print('  %s  %-34s %s' % (code, name, why))
        total += len(rows)
    print('')
    if total:
        print('%d reachability finding(s) across %d file(s).' % (total, len(targets)))
        print('R1/R2 are near-certain. R3 needs a read before you believe it.')
        return 1
    print('clean -- no unreachable features of these three shapes in %d file(s)' % len(targets))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
