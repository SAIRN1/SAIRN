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


# ── R4: STILL SERVED IN PRODUCTION? added 2026-09-13 ───────────────────────
# R1-R3 ask "can anyone reach this". R4 asks the next question over: the code is
# reachable, but does it still serve a PURPOSE in the running system, or has the
# world moved past it?
#
# THE PROXY IS CONCRETE AND MEASURED, NOT A JUDGMENT CALL: days since the route
# was last OBSERVED INVOKED in Vercel's production runtime logs, over a declared
# window, compared against a DECLARED EXPECTED CADENCE. Both halves are files
# with dates and owners in them (production_activity_snapshot.json,
# activity_cadence.json), so a reader can check the claim rather than trust it.
#
# ── THE THREE THINGS THAT KEEP THIS HONEST ─────────────────────────────────
#
# 1. IT NEVER SUGGESTS REMOVAL AND NEVER GATES. R4 cannot change this tool's
#    exit code. "Nothing called it" is an observation about a 72-hour window on
#    a platform with almost no customers; treating that as permission to delete
#    is how a working disaster-recovery path gets removed the month before it is
#    needed. The output is a prompt to WRITE A CADENCE ROW, nothing more.
#
# 2. RARE-BUT-REAL IS A DECLARED CLASS, NOT AN INFERENCE. Year-end code,
#    incident-only code and unlaunched code are all correctly silent, and no
#    amount of log reading can tell them from dead code. activity_cadence.json
#    is where a human says which, with an owner and a reason. A route with no
#    row is NO CADENCE DECLARED -- a known-unknown, printed as one.
#
# 3. THE DENOMINATOR GATE, which is the part that stops this being theatre.
#    If the snapshot observed fewer than MIN_ROUTE_COVERAGE of the routed
#    endpoints AT ALL, then "this route saw zero" carries no information --
#    every route saw zero -- and NOTHING is classified. Identical rule and
#    identical number to MIN_PANEL_COVERAGE above, for an identical reason: an
#    under-covered snapshot is a could-not-tell, and could-not-tell must never
#    render as clean.
#
# MEASURED THE DAY IT WAS BUILT, and the result is the finding: over 72 hours,
# 13 of 64 routed endpoints were observed at all -- 20%, far under the bar. Two
# of the thirteen are the declared hourly crons. So the gate fires, nothing is
# classified, and the honest output is "this snapshot cannot discriminate". That
# is a real answer to the question "which of our code is dead": right now,
# production traffic cannot tell us, and any tool claiming otherwise from this
# data would be fabricating confidence.
ACTIVITY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'production_activity_snapshot.json')
CADENCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'activity_cadence.json')
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(REPO_ROOT, 'api', '_resources')


def routed_api_paths():
    """Every api/ handler Vercel serves, derived from the tree -- not a list.

    Excludes `_lib/` and `_resources/` (imported, never routed) and `*.test.js`.
    Derived rather than written down for the same reason the App File Map had to
    be: a list of routes maintained by hand is a claim that drifts.
    """
    import subprocess
    out = subprocess.run(['git', 'ls-files', 'api/*.js', 'api/*/*.js'],
                         cwd=REPO_ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    paths = []
    for f in out.split('\n'):
        f = f.strip()
        if not f or f.endswith('.test.js'):
            continue
        if f.startswith('api/_lib/') or f.startswith('api/_resources/'):
            continue
        paths.append('/' + f[:-3])
    return sorted(paths)


def declared_crons():
    """Cron paths read out of vercel.json itself, never hand-listed here."""
    try:
        with open(os.path.join(REPO_ROOT, 'vercel.json'), encoding='utf-8') as fh:
            return {c.get('path') for c in (json.load(fh).get('crons') or [])
                    if c.get('path')}
    except Exception:
        return None            # unreadable -> caller treats it as could-not-tell


def load_activity(path):
    """(snapshot, error_or_None). Fail CLOSED on anything unreadable."""
    try:
        with open(path, encoding='utf-8') as fh:
            snap = json.load(fh)
    except Exception as e:
        return None, 'activity snapshot unreadable (%s): %s' % (type(e).__name__, e)
    for field in ('counts', 'captured_at', 'window_hours'):
        if field not in snap:
            return None, 'activity snapshot is missing %r' % field
    return snap, None


def report_activity(snap):
    """Print the R4 section. Returns nothing -- it CANNOT affect the exit code."""
    cadence = {}
    min_cov = 0.60
    try:
        with open(CADENCE_FILE, encoding='utf-8') as fh:
            c = json.load(fh)
            cadence = c.get('rows') or {}
            min_cov = c.get('min_route_coverage', 0.60)
    except Exception as e:
        print('  CADENCE FILE UNREADABLE (%s) -- every route reads as '
              'NO CADENCE DECLARED, which is a could-not-tell, not a pass.' % e)

    routes = routed_api_paths()
    counts = snap.get('counts') or {}
    crons = declared_crons()
    observed = [r for r in routes if counts.get(r)]
    # Counts for paths that are NOT routed handlers in this tree. A snapshot
    # naming a route that no longer exists is evidence about the snapshot, and
    # it is printed rather than dropped.
    unknown_paths = sorted(set(counts) - set(routes))

    print('')
    print('=== R4: STILL SERVED IN PRODUCTION? (report only, never gates) ===')
    print('  snapshot      : %s, %sh window, %s'
          % (snap.get('captured_at'), snap.get('window_hours'),
             snap.get('source', 'source not stated')))
    print('  routed api/   : %d endpoints (derived from the tree)' % len(routes))
    print('  observed at all: %d  (%.0f%%)'
          % (len(observed), 100.0 * len(observed) / max(1, len(routes))))
    if crons is None:
        print('  declared crons: COULD NOT READ vercel.json -- cron traffic '
              'cannot be separated, so treat the figure above as inflated')
        cron_n = 0
    else:
        cron_n = len([r for r in observed if r in crons])
        print('  of those, declared crons: %d  (%s)'
              % (cron_n, ', '.join(sorted(crons)) or 'none'))
    print('  the rest are UNATTRIBUTED -- this platform has no request-level')
    print('  attribution, so a hit cannot be split into customer traffic, a')
    print('  session\'s own live-verification fetch, a deploy check or a probe.')
    if unknown_paths:
        print('  in the snapshot but NOT a routed handler here: %s'
              % ', '.join(unknown_paths))

    coverage = len(observed) / float(max(1, len(routes)))
    if coverage < min_cov:
        print('')
        print('  VERDICT: UNKNOWN. Route coverage %.0f%% is under the %.0f%% bar,'
              % (100 * coverage, 100 * min_cov))
        print('  so NOTHING IS CLASSIFIED. When most routes see zero, one route')
        print('  seeing zero is not evidence about that route -- it is evidence')
        print('  about the traffic. Same rule as MIN_PANEL_COVERAGE: an')
        print('  under-covered snapshot is a could-not-tell, not a pass.')
        print('  No route is called dead here and none should be removed on')
        print('  the strength of this run.')
        # RETURNS THE COVERAGE VERDICT so R5 can honour the same bar for its
        # silence-based half and ignore it for its observation-based half.
        return False

    silent_declared, silent_undeclared = [], []
    for r in routes:
        if counts.get(r):
            continue
        row = cadence.get(r)
        (silent_declared if row else silent_undeclared).append((r, row))
    print('')
    print('  SERVED                    : %d' % len(observed))
    print('  SILENT, cadence declared  : %d  (expected silence, read the row)'
          % len(silent_declared))
    print('  SILENT, NO CADENCE ROW    : %d  <- a known-unknown, not a finding'
          % len(silent_undeclared))
    for r, row in silent_declared:
        print('    -- %-44s %s' % (r, row.get('cadence')))
    for r, _ in silent_undeclared:
        print('    ?  %-44s no cadence declared' % r)
    print('')
    print('  WHAT TO DO WITH THE "?" ROWS: write a cadence row in')
    print('  tools/activity_cadence.json saying why silence is expected --')
    print('  annual, incident, unlaunched -- or that it is not. NOT delete the')
    print('  code. A silent route is a question, and this tool asks it; it does')
    print('  not answer it and it never votes for removal.')
    return True


# ── R5: THE PURPOSE PROXY AT FUNCTION GRANULARITY ──────────────────────────
# R4 answers "is this ROUTE still served". Item 32 asks the same question one
# level down -- was the FUNCTION actually invoked -- and there is no telemetry
# for that. No production log records a JS function call. So R5 does not invent
# one: it CROSSES two things that already exist and reports where they disagree.
#
# THE DIRECTION THAT WORKS TODAY IS THE ONE FROM OBSERVATION, NOT FROM SILENCE,
# and that distinction is the whole reason this is worth adding under R4's
# coverage gate rather than behind it. R4 gates because "this route saw zero"
# carries no information when almost every route saw zero -- an inference FROM
# SILENCE needs a denominator. An inference from a route that WAS OBSERVED needs
# no such thing: a served route is positive evidence about itself regardless of
# how many others were quiet. So:
#
#   route SERVED + the sweep says a function in it has NO CALLERS
#       -> a question about THE SWEEP, not about the code. The file ran. Either
#          the function genuinely never executed on those requests, or it is
#          reached by a dispatch the caller analysis cannot see -- a string key,
#          a table of handlers, an exported name called from elsewhere. Worth a
#          human read either way, and it is the only direction this data can
#          support today at 20% route coverage.
#
#   route SILENT + no callers
#       -> the strongest available signal, and still NOT permission to delete.
#          Gated behind R4's coverage bar because it is an inference from
#          silence, and printed only when that bar is met.
#
# IT NEVER GATES AND NEVER SUGGESTS REMOVAL, the same standing rule R4 carries:
# this platform has almost no customers, and treating a quiet 72 hours as a
# mandate to delete is how a disaster-recovery path gets removed the month
# before it is needed.
# ── R6: IS THE RESOURCE ASKED FOR? (report only, never gates) ─────────────
# THE RUNG R4 AND R5 CANNOT REACH, and the reason is arithmetic. R4 asks
# whether a ROUTE is still served; R5 asks whether a FUNCTION inside one was
# invoked. Both take the route as the unit -- and `/api/sd-data` is ONE route
# carrying 384 registered resources. It is among the most-served endpoints on
# the platform, so every resource behind it reads as reachable whether or not
# anything has ever asked for it by name.
#
# R6 changes the unit to the RESOURCE. A registered name that no app HTML and
# no api/ module ever mentions passes the allowlist and then falls through to
# "Unsupported action/resource combination" -- which api/_resources/sairnlaw.js
# already records as a WORSE failure than not registering it, because the name
# looks supported right up to the moment somebody calls it.
#
# ── IT NEVER GATES AND NEVER SUGGESTS REMOVAL ────────────────────────────
# The same standing rule R4 and R5 carry, for the same reason: legitimate code
# can be rare. A year-end calculation, a disaster-recovery path or a resource
# whose panel has not shipped yet is quiet and correct, and treating quiet as a
# mandate to delete is how the recovery path gets removed the month before it
# is needed. This prints a list and a denominator. Nothing else.
#
# ── WHAT IT CANNOT SEE, so nobody reads the list as exhaustive ───────────
#   * a name BUILT at runtime -- `'dnt_' + kind` is invisible to a literal
#     scan, and the answer for such a resource is NOT KNOWN rather than absent;
#   * a caller outside this repo entirely;
#   * whether a resource that IS named is named on a path anyone runs. That is
#     R4 and R5's question, one level up.
R6_ACKNOWLEDGED = {
    ('sairndental', 'dnt_ar'):
        'DELIBERATE, and argued in api/sd-data-dental-ledger-validation.test.js '
        'around line 1821: "deliberately no write to dnt_ar -- a stored ageing row '
        'is stale the next time anything changes". It stays registered and unwritten '
        'so the tier gate covers it the day something does write it.',
    ('sairndental', 'dnt_revenue'):
        'Same decision, same file, same paragraph: registered and covered by the '
        'financial tier gate (api/sd-data-dental-financial-tier.test.js drives both '
        'through the real handler), with no writer by design.',
}


def _registered_resources():
    """{app: {name, ...}} from the registry modules, parsed the same way
    tools/criticality_tier_check.py parses them -- one reader, not two."""
    out = {}
    if not os.path.isdir(RESOURCES_DIR):
        return out
    for f in sorted(os.listdir(RESOURCES_DIR)):
        if not f.endswith('.js') or f.endswith('.test.js'):
            continue
        app = f[:-3]
        if app in ('index', 'shared'):
            continue
        names = set()
        for l in io.open(os.path.join(RESOURCES_DIR, f), encoding='utf-8'):
            s = l.strip()
            if s.startswith("'") and s.endswith("',") and s.count("'") == 2:
                names.add(s.strip("',"))
        if names:
            out[app] = names
    return out


def _mention_corpus():
    """Every place a resource name could legitimately be asked for: the app
    HTML files and every api/ module EXCEPT the registry itself.

    THE REGISTRY IS EXCLUDED ON PURPOSE. It is where the name is DECLARED, and
    counting a declaration as a use is how a check reports a closed loop as
    coverage -- the same shape as a generator's --check comparing a document to
    its own output.
    """
    blob = []
    for f in sorted(os.listdir(REPO_ROOT)):
        if f.endswith('.html'):
            blob.append(io.open(os.path.join(REPO_ROOT, f), encoding='utf-8',
                                errors='replace').read())
    api_dir = os.path.join(REPO_ROOT, 'api')
    for dp, dn, fn in os.walk(api_dir):
        dn[:] = [d for d in dn if d != 'node_modules']
        if os.path.basename(dp) == '_resources':
            continue
        for f in sorted(fn):
            if f.endswith('.js') and not f.endswith('.test.js'):
                blob.append(io.open(os.path.join(dp, f), encoding='utf-8',
                                    errors='replace').read())
    return ''.join(blob)


def report_resource_demand():
    """Print the R6 section. Like R4 and R5 it CANNOT affect the exit code."""
    print('')
    print('=== R6: IS THE RESOURCE ASKED FOR? (report only, never gates) ===')
    registered = _registered_resources()
    if not registered:
        print('  COULD NOT RUN: no registry modules were readable under '
              'api/_resources, so NO resource was checked. That is not an '
              'empty result.')
        return
    corpus = _mention_corpus()
    total = sum(len(v) for v in registered.values())
    unrequested = []
    for app in sorted(registered):
        for name in sorted(registered[app]):
            if ("'" + name + "'") in corpus or ('"' + name + '"') in corpus:
                continue
            unrequested.append((app, name))

    acked = [x for x in unrequested if x in R6_ACKNOWLEDGED]
    open_rows = [x for x in unrequested if x not in R6_ACKNOWLEDGED]
    print('  registered resources : %d across %d app registr(y/ies)'
          % (total, len(registered)))
    print('  named nowhere        : %d  (%d acknowledged, %d open)'
          % (len(unrequested), len(acked), len(open_rows)))
    print('  THE UNIT IS THE RESOURCE, NOT THE ROUTE. /api/sd-data is one route')
    print('  carrying most of that %d, so R4 and R5 read every one of them as' % total)
    print('  reachable. This is the only rung that can tell them apart.')

    if open_rows:
        print('')
        print('  NOT ASKED FOR BY ANY app HTML OR api/ MODULE -- read these, do not')
        print('  act on the list. A resource whose panel has not shipped yet looks')
        print('  exactly like one nobody needs:')
        for app, name in open_rows:
            print('    %-14s %s' % (app, name))
    else:
        print('')
        print('  none open. Every registered resource is named somewhere a caller')
        print('  could reach it -- a measured zero over %d names, not a silence.' % total)

    # ACKNOWLEDGEMENTS ARE PRINTED EVERY RUN. One nobody can see is a
    # suppression, and one that outlives the finding it excused is worse.
    print('')
    print('  ACKNOWLEDGED (%d) -- deliberate, with the reason and where it is argued:'
          % len(acked))
    for app, name in acked:
        print('    %s/%s' % (app, name))
        print('      %s' % R6_ACKNOWLEDGED[(app, name)])
    stale = [k for k in R6_ACKNOWLEDGED if k not in set(unrequested)]
    if stale:
        print('  STALE ACKNOWLEDGEMENT(S) -- the resource IS named now, so the entry')
        print('  has outlived what it excused. Remove them:')
        for app, name in stale:
            print('    %s/%s' % (app, name))
    print('')
    print('  CANNOT SEE: a resource name BUILT at runtime is invisible to a literal')
    print('  scan, and for such a resource the answer is NOT KNOWN rather than')
    print('  absent. Nor can this tell whether a name that IS mentioned sits on a')
    print('  path anyone runs -- that is R4 and R5, one level up.')


# ── R7: IS THE ACTION ASKED FOR? (report only, never gates) ───────────────
# THE SAME UNIT MISMATCH AS R6, ON A SECOND AXIS -- and finding it there is the
# reason R6's insight was worth generalising rather than filing.
#
# R6 asked whether a RESOURCE is asked for, because /api/sd-data is one route
# carrying 385 of them. The sweep that followed found the shape is not unique to
# that route: 182 individually-addressable ACTIONS are dispatched across 27
# routes, and R4 and R5 measure reachability at the ROUTE for every one of them.
# api/law-auth.js alone dispatches on 19 distinct action strings behind a single
# path.
#
# An action nothing asks for is the same failure R6 names one level up: it is
# reachable in principle, answers nothing in practice, and the route around it
# is busy enough that no route-level measurement will ever say so.
#
# ── IT NEVER GATES AND NEVER SUGGESTS REMOVAL ────────────────────────────
# Inherited from R4, R5 and R6 deliberately, and it matters more here than
# anywhere else in this file. An admin action run by hand once a quarter, an
# OAuth callback a provider posts to, a seeding verb used at install: all are
# quiet, all are correct, and all look identical to dead code from inside the
# repo. THIS LIST IS A POINTER. Reading the file is the work.
#
# ── NO ACKNOWLEDGEMENTS ARE PRE-LOADED, AND THAT IS DELIBERATE ───────────
# R6 ships with two, because the files themselves argue the decision in a test
# that names the resource. None of the routes below states why its actions have
# no caller, so acknowledging any of them would mean INVENTING the
# justification -- which is the one thing an acknowledgement must never be. They
# stay open until somebody who owns the file writes the reason.
R7_ACKNOWLEDGED = {}
R7_MIN_ACTIONS = 3


def _action_dispatch():
    """{route: [action, ...]} for every api/ module dispatching on >= N actions."""
    out = {}
    pat = re.compile(r"\baction\s*===\s*'([a-z][a-z0-9_]{1,40})'")
    for dp, dn, fn in os.walk(os.path.join(REPO_ROOT, 'api')):
        dn[:] = [d for d in dn if d != 'node_modules']
        for f in sorted(fn):
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, REPO_ROOT).replace(os.sep, '/')
            src = io.open(full, encoding='utf-8', errors='replace').read()
            acts = sorted(set(pat.findall(src)))
            if len(acts) >= R7_MIN_ACTIONS:
                out[rel] = acts
    return out


def _callers_excluding(rel):
    """Every app HTML plus every api/ module EXCEPT the one being asked about.

    A ROUTE IS NOT ITS OWN CALLER. Leaving the file in would make every action
    reachable by definition -- the same closed loop R6 avoids by excluding the
    registry, and the reason both exclusions are asserted by their probes rather
    than left as an implementation detail.
    """
    blob = []
    for f in sorted(os.listdir(REPO_ROOT)):
        if f.endswith('.html'):
            blob.append(io.open(os.path.join(REPO_ROOT, f), encoding='utf-8',
                                errors='replace').read())
    for dp, dn, fn in os.walk(os.path.join(REPO_ROOT, 'api')):
        dn[:] = [d for d in dn if d != 'node_modules']
        for f in sorted(fn):
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            full = os.path.join(dp, f)
            if os.path.relpath(full, REPO_ROOT).replace(os.sep, '/') == rel:
                continue
            blob.append(io.open(full, encoding='utf-8', errors='replace').read())
    return ''.join(blob)


def report_action_demand():
    """Print the R7 section. Like R4, R5 and R6 it CANNOT affect the exit code."""
    print('')
    print('=== R7: IS THE ACTION ASKED FOR? (report only, never gates) ===')
    routes = _action_dispatch()
    if not routes:
        print('  COULD NOT RUN: no api/ module was readable, so NO action was '
              'checked. That is not an empty result.')
        return
    total = sum(len(v) for v in routes.values())
    findings = []
    for rel in sorted(routes):
        callers = _callers_excluding(rel)
        for a in routes[rel]:
            if ("'" + a + "'") in callers or ('"' + a + '"') in callers:
                continue
            findings.append((rel, a))
    acked = [x for x in findings if x in R7_ACKNOWLEDGED]
    open_rows = [x for x in findings if x not in R7_ACKNOWLEDGED]

    print('  routes dispatching on >=%d actions : %d' % (R7_MIN_ACTIONS, len(routes)))
    print('  individually addressable actions   : %d' % total)
    print('  named by NOTHING in this repo      : %d  (%d acknowledged, %d open)'
          % (len(findings), len(acked), len(open_rows)))
    print('  THE UNIT IS THE ACTION, NOT THE ROUTE. api/law-auth.js alone carries')
    print('  19 behind one path, and R4 and R5 measure reachability at the path.')

    if open_rows:
        print('')
        print('  READ THESE, DO NOT ACT ON THE LIST. An admin verb run by hand once a')
        print('  quarter, an OAuth callback a provider posts to, and a seeding action')
        print('  used at install are all quiet, all correct, and all look exactly like')
        print('  this from inside the repo:')
        last = None
        for rel, a in open_rows:
            if rel != last:
                print('    %s' % rel)
                last = rel
            print('        %s' % a)
    else:
        print('')
        print('  none open -- a measured zero over %d actions, not a silence.' % total)

    print('')
    print('  ACKNOWLEDGED (%d).' % len(acked))
    if not acked:
        print('    NONE PRE-LOADED, DELIBERATELY. R6 ships with two because the files')
        print('    themselves argue the decision; none of the routes above states why')
        print('    its actions have no caller, and acknowledging one would mean')
        print('    INVENTING the justification -- the one thing an acknowledgement')
        print('    must never be.')
    for rel, a in acked:
        print('    %s %s' % (rel, a))
        print('      %s' % R7_ACKNOWLEDGED[(rel, a)])
    stale = [k for k in R7_ACKNOWLEDGED if k not in set(findings)]
    if stale:
        print('  STALE ACKNOWLEDGEMENT(S) -- the action HAS a caller now:')
        for rel, a in stale:
            print('    %s %s' % (rel, a))
    print('')
    print('  CANNOT SEE: an action string BUILT at runtime, a caller outside this')
    print('  repo (a browser redirect, a provider webhook, an operator with curl),')
    print('  or whether an action that IS named sits on a path anyone runs. Only')
    print('  the last of those is R4 and R5, one level up.')


def report_function_purpose(snap, coverage_ok):
    print('')
    print('=== R5: FUNCTIONS INSIDE api/ ROUTES (report only, never gates) ===')
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sairn_dead_function_sweep as sweeper
    except Exception as e:
        # FAIL LOUD, NOT SILENT. A missing sibling tool means this section did
        # not run; folding that into "nothing to report" is the fail-open this
        # repo keeps correcting.
        print('  COULD NOT RUN: tools/sairn_dead_function_sweep.py could not be '
              'imported (%s: %s), so NO function was crossed against production '
              'activity. That is not an empty result.' % (type(e).__name__, e))
        return

    counts = snap.get('counts') or {}
    routes = routed_api_paths()
    served_no_callers, silent_no_callers, unreadable = [], [], []
    for route in routes:
        rel = 'api' + route[len('/api'):] + '.js' if route.startswith('/api') else None
        path = os.path.join(REPO_ROOT, (rel or '').replace('/', os.sep))
        if not rel or not os.path.isfile(path):
            continue
        try:
            _defs, dead, _export_only = sweeper.sweep(path)
        except Exception as e:
            unreadable.append((route, '%s: %s' % (type(e).__name__, e)))
            continue
        if not dead:
            continue
        names = [n for n, _ in dead]
        (served_no_callers if counts.get(route) else silent_no_callers).append((route, names))

    if unreadable:
        print('  COULD NOT READ (%d) -- not counted as clean:' % len(unreadable))
        for route, why in unreadable:
            print('    ? %-40s %s' % (route, why))

    print('  routes SERVED in the window whose file has a function with no '
          'caller: %d' % len(served_no_callers))
    for route, names in served_no_callers:
        print('    ! %-40s %s' % (route, ', '.join(names[:6]) +
                                  ('' if len(names) <= 6 else ' (+%d)' % (len(names) - 6))))
    if served_no_callers:
        print('  ^ THE FILE RAN. So either these never executed on those')
        print('    requests, or the caller analysis cannot see how they are')
        print('    reached -- a string dispatch, a handler table, an exported')
        print('    name called from another file. READ THE DISPATCH. This is a')
        print('    question about the sweep at least as much as about the code.')

    if not coverage_ok:
        print('')
        print('  SILENT-ROUTE side: NOT CLASSIFIED. R4\'s coverage bar was not')
        print('  met, and "no caller AND the route was quiet" is an inference')
        print('  FROM SILENCE -- it needs the denominator R4 says is missing.')
        print('  The served side above does not: a route that WAS observed is')
        print('  evidence about itself however quiet the others were.')
        return
    print('  routes SILENT in the window whose file has a function with no '
          'caller: %d' % len(silent_no_callers))
    for route, names in silent_no_callers:
        print('    ? %-40s %s' % (route, ', '.join(names[:6])))
    print('  ^ The strongest signal this data can produce, and STILL NOT')
    print('    permission to delete anything. Write a cadence row or read the')
    print('    code; this tool does not vote.')


def main(argv):
    args = [a for a in argv[1:]]
    live_paths, require_live, check_exemptions = [], False, False
    activity_path, rest = None, []
    i = 0
    while i < len(args):
        if args[i] == '--live' and i + 1 < len(args):
            live_paths.append(args[i + 1]); i += 2; continue
        if args[i] == '--require-live':
            require_live = True; i += 1; continue
        if args[i] == '--check-exemptions':
            check_exemptions = True; i += 1; continue
        # `--activity` alone uses the committed snapshot; `--activity x.json`
        # overrides it. The next token is only consumed when it is a .json path
        # -- an earlier version consumed whatever followed and swallowed the
        # html target, then failed closed on it as an unreadable snapshot. Fail
        # closed did its job; the argument parsing was still wrong.
        if args[i] == '--activity':
            if i + 1 < len(args) and args[i + 1].lower().endswith('.json'):
                activity_path = args[i + 1]; i += 2
            else:
                activity_path = ACTIVITY_FILE; i += 1
            continue
        rest.append(args[i]); i += 1

    exempt, exempt_err = load_exemptions()
    if exempt_err:
        # Fail CLOSED on a broken exemption file. The alternative -- carrying on
        # with an empty set -- silently converts a typo into a wall of blocked
        # findings and invites someone to delete the file to make it stop.
        print('BLOCKING: %s' % exempt_err)
        print('Fix tools/reachability_exemptions.json; it is not optional once entries exist.')
        return 2

    # R4 runs FIRST and prints FIRST because its subject is api/ routes while
    # R1-R3's is html files -- two different questions about two different
    # trees. It is opt-in (--activity), it cannot change the exit code, and a
    # BROKEN snapshot file fails closed at 2 the same way a broken exemption
    # file does: a corrupt input read as "no data" is how a checker reports a
    # pass it never performed.
    if activity_path:
        snap, act_err = load_activity(activity_path)
        if act_err:
            print('BLOCKING: %s' % act_err)
            print('An unreadable activity snapshot is a could-not-tell, not an '
                  'empty one. Re-capture it or drop --activity.')
            return 2
        coverage_ok = report_activity(snap)
        report_function_purpose(snap, bool(coverage_ok))

    # R6 NEEDS NO ACTIVITY SNAPSHOT -- it is a static question -- so it runs on
    # every FULL sweep rather than only with --activity. It is skipped on a
    # targeted run for the same reason the stale-exemption report is: a subset
    # cannot say what the whole tree does not mention.
    if not rest:
        report_resource_demand()
        report_action_demand()

    targets = rest or sorted(glob.glob('*.html'))
    # A STALE REPORT IS ONLY MEANINGFUL ON A FULL RUN, and this tool was missing
    # the fix its sibling already had. fail_open_check.py carried exactly this
    # bug -- it compared every acceptance against whatever subset had just been
    # scanned, so a targeted run declared a live, correct entry dead and told
    # the reader to delete it. That was fixed there and never here.
    #
    # It cost something on 2026-09-08. A run of ONE unrelated file printed both
    # of stonedesk.html's exemptions under "STALE EXEMPTIONS -- these no longer
    # match any finding and should be deleted", because a file that was never
    # scanned cannot match anything. Acting on that advice removed two live,
    # justified exemptions and un-suppressed two real R1 findings; it was caught
    # only by re-running and watching the count move from 0 to 2. The advice was
    # confident, specific, and wrong.
    full_run = not rest
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
    stale = sorted(exempt - matched) if full_run else []
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
