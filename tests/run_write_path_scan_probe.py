"""tests/run_write_path_scan_probe.py -- attacks tools/write_path_fault_scan.py.

Run:  python tests/run_write_path_scan_probe.py

WHY THIS EXISTS. The scan shipped 2026-09-10 with no probe, and the first fix
written against one of its findings LANDED ON ITS OWN REPORT: svPushOne() in
sairnvet.html maps a rejection onto null using `.then(onOk, onErr)`, the
two-argument form, and the scan only looked for the literal `.catch(`. So the
repair was reported as the hazard. sairndental.html's dntPushOne() had been
reported the same way since the evening before.

A checker that flags its own fixes is one a session switches off, so the
correction is held here rather than remembered. Every arm below is a string the
real classifier is run against -- nothing re-implements it.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'tools'))
import write_path_fault_scan as W            # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check(label, cond, detail=''):
    print('  %s %s%s' % ('ok  ' if cond else 'FAIL', label,
                         '' if cond else '\n       ' + detail))
    if not cond:
        fails.append(label)


def classify(src):
    m = W.WRITE.search(src)
    assert m, 'the probe string does not contain a write call: ' + src[:60]
    return W.classify(src, m)


print('--- the two-argument .then IS a rejection handler ---')

check('.then(ok, err) counts as handled',
      classify("svData('write','k',r).then(function(r){return r;},"
               "function(e){return null;});") == 'handled',
      'the two-argument form was still reported as then-no-catch')

check('...across a line break, as the real code is written',
      classify("svData('write','k',r)\n  .then(function(r){ return r; },\n"
               "        function(e){ return REJECTED; });") == 'handled')

check('.then(ok).catch(err) still counts as handled',
      classify("svData('write','k',r).then(function(r){}).catch(function(e){});")
      == 'handled')

print('--- and a ONE-argument .then is still a finding ---')

check('a bare .then is then-no-catch',
      classify("svData('write','k',r).then(function(saved){ if(saved===null){} });")
      == 'then-no-catch',
      'THE REAL DEFECT STOPPED BEING REPORTED -- the fix went too far')

check('a comma INSIDE the handler body does not count',
      classify("svData('write','k',r).then(function(s){ warn(a,b); });")
      == 'then-no-catch',
      'a nested comma was read as a second argument, so any handler that calls '
      'a two-argument function now reports as handled')

check('a comma inside a STRING does not count',
      classify("svData('write','k',r).then(function(s){ warn('a, b'); });")
      == 'then-no-catch')

check('a comma inside a nested object literal does not count',
      classify("svData('write','k',r).then(function(s){ go({a:1,b:2}); });")
      == 'then-no-catch')

check('an escaped quote inside a string does not break the scan',
      classify("svData('write','k',r).then(function(s){ warn('it\\'s, fine'); });")
      == 'then-no-catch')

print('--- the other classes are unchanged ---')

check('a bare statement is fire-and-forget',
      classify("svData('write','shared_knowledge',{words:w});")
      == 'fire-and-forget')

check('a returned promise is awaited-or-returned',
      classify("return svData('write','k',r);") == 'awaited-or-returned')

print('--- an element of an awaited Promise.all is NOT fire-and-forget ---')
# FIVE of SAIRNgrounds' eight flagged sites were this, and all five were safe --
# `await Promise.all([...])` whose results drive a toast naming exactly which
# records failed to sync. The most careful write-reporting on the platform was
# being reported as the least. Over-reporting is the direction that gets a
# checker switched off, which is why this is fixed rather than footnoted.

check('a write inside await Promise.all([...]) is awaited-or-returned',
      classify("var results=await Promise.all([\n"
               "  gData('write','a',x),\n  gData('write','b',y)\n]);")
      == 'awaited-or-returned')

check('...and so is the SECOND element, not just the first',
      (lambda s: W.classify(s, list(W.WRITE.finditer(s))[1]))(
          "var results=await Promise.all([\n"
          "  gData('write','a',x),\n  gData('write','b',y)\n]);")
      == 'awaited-or-returned')

check('...through a .concat() on the array literal, as sairngrounds writes it',
      classify("var r=await Promise.all([gData('write','msb_sales',rec)]"
               ".concat(invLogPromises));") == 'awaited-or-returned')

check('return Promise.all([...]) counts too',
      classify("return Promise.all([gData('write','a',x)]);")
      == 'awaited-or-returned')

check('a BARE Promise.all -- nobody awaits or returns it -- is still blind',
      classify("Promise.all([gData('write','a',x)]);") == 'fire-and-forget',
      'an unawaited collection reports nothing and is exactly the hazard; the '
      'fix must not swallow it')

check('a plain array literal that nobody awaits is still blind',
      classify("var jobs=[gData('write','a',x)];") == 'fire-and-forget')

print('--- the TIMEOUT column, which was wrong in the OPTIMISTIC direction ---')
# Found 2026-09-10 the moment the SAIRNgrounds work started: the column ran the
# timeout regex over RAW SOURCE, file-wide. Two separate errors, both of which
# made an unprotected app read as protected.


def tstate(src):
    return W.timeout_state(src)


check('a user-facing STRING mentioning signal: is not a timeout',
      tstate("function f(){ el.textContent='Weather Command Engine signal: '+x;"
             " gData('write','k',r); }") == 'none',
      'the sairngrounds false positive is back -- that file has eight '
      'fire-and-forget writes and was reading as bounded')

check('...and a COMMENT mentioning AbortController is not one either',
      tstate("function f(){ /* an AbortController would fix this */"
             " gData('write','k',r); }") == 'none')

check('a real race in the same function as the write is a WRITE-path timeout',
      tstate("function push(){ return Promise.race([gData('write','k',r),t]); }")
      == 'write')

check('a race in a function that does NOT write is read-only, not yes',
      tstate("function hydrate(){ return Promise.race([readAll(),t]); }\n"
             "function save(){ gData('write','k',r); }") == 'read-only',
      'a read-path timeout is being counted as protecting a write; sairnbiz and '
      'stonedesk both bound only a READ')

check('AbortSignal.timeout counts as a timeout construct',
      tstate("function push(){ return gData('write','k',r,"
             "{signal:AbortSignal.timeout(8000)}); }") == 'write')

check('no timeout token anywhere is none',
      tstate("function save(){ gData('write','k',r); }") == 'none')

check('a timeout in the SHARED TRANSPORT the write calls is a write-path timeout',
      tstate("async function gData(a,r,p){ return fetch(u,"
             "{signal:AbortSignal.timeout(15000)}); }\n"
             "async function save(){ var x=await gData('write','k',r); }")
      == 'write',
      'SAIRNgrounds bounds all 43 of its writes inside grdData(); reporting that '
      'as read-only calls the broadest possible fix the weakest')

print('--- comments are not code, here either ---')
# Bit the same day: the SAIRNgrounds fix carried a comment QUOTING the house
# pattern, and the scan reported a fire-and-forget write at a line holding only
# prose. Two other apps carried the same phantom -- sairndental:4839 and
# sairndesign:2292 both say "Was sdnData('write',...)" about code that is gone.

check('a write call inside a // comment is not a write site',
      len([m for m in W.WRITE.finditer(W.jscomments.strip_comments(
          "// var x = await gData('write','k',r);\nfoo();"))]) == 0)

check('...nor inside a block comment',
      len([m for m in W.WRITE.finditer(W.jscomments.strip_comments(
          "/* gData('write','k',r) */ foo();"))]) == 0)

check('a REAL write beside a comment still counts',
      len([m for m in W.WRITE.finditer(W.jscomments.strip_comments(
          "// see gData('write',...) below\ngData('write','k',r);"))]) == 1)

check('stripping preserves line numbers, or every reported line is wrong',
      (lambda s: W.jscomments.strip_comments(s).count(chr(10)) == s.count(chr(10))
       and len(W.jscomments.strip_comments(s)) == len(s))(
          "a();\n// gone\n/* also\ngone */\nb();"))

print('--- and the real files, measured rather than asserted ---')

EXPECTED_TSTATE = {
    # The only two apps with a genuine write-path timeout, both added 2026-09-10.
    'sairnvet.html': 'write',
    'sairndental.html': 'write',
    # WERE 'read-only' UNTIL 2026-09-11 and the change is deliberate: both had a
    # timer on a READ only -- sairnbiz raced sbFirstDeviceHydrate(), stonedesk put
    # AbortSignal.timeout(8000) on /api/knowledge -- and the portfolio sweep put a
    # real one in each transport. This arm is what forced that to be written down
    # rather than noticed later, which is the only reason the map is here.
    'sairnbiz.html': 'write',
    'stonedesk.html': 'write',
    # Bounded inside grdData() 2026-09-10, which protects all 43 of its writes.
    'sairngrounds.html': 'write',
}
for app, want in sorted(EXPECTED_TSTATE.items()):
    path = os.path.join(REPO, app)
    if not os.path.exists(path):
        check(app + ' present', False, 'app file missing; this arm tests nothing')
        continue
    with open(path, encoding='utf-8', errors='replace') as f:
        got = W.timeout_state(f.read())
    check('%-22s timeout state is %s' % (app, want), got == want,
          'got %r, expected %r -- if a timeout was deliberately added or removed, '
          'update this map in the same commit and say which' % (got, want))

print('--- against the REAL files, which is what produced the false positive ---')

for app, fn in (('sairnvet.html', 'svPushOne'), ('sairndental.html', 'dntPushOne')):
    path = os.path.join(REPO, app)
    if not os.path.exists(path):
        check(app + ' present', False, 'the app file is gone; this arm tests nothing')
        continue
    with open(path, encoding='utf-8') as f:
        src = f.read()
    if ('function ' + fn + '(') not in src:
        check(fn + '() present in ' + app, False,
              'the push helper was renamed or removed -- if the helper is gone '
              'the hazard is back, and this probe must not pass quietly')
        continue
    # The helper's own write call must classify as handled, not as the hazard.
    start = src.index('function ' + fn + '(')
    m = W.WRITE.search(src, start)
    check(fn + "()'s own write is classified handled",
          m is not None and W.classify(src, m) == 'handled',
          'the push helper is still being reported as the hazard it fixes')

# ── THE RATCHET, BOTH DIRECTIONS (2026-09-15) ──────────────────────────────
# The scan has been a pointer since 2026-09-10 and the portfolio total has not
# moved. A pointer cannot stop the 26th site being written, and that is the half
# that closes the root cause behind cluster 5b98fd27: a write path with one
# success shape and no representation for failure. A ratchet that never fires is
# indistinguishable from a clean portfolio, so both directions are here.
print('\n--- the ratchet ---')

import io                                                        # noqa: E402
import json                                                      # noqa: E402
import tempfile                                                  # noqa: E402


def run_ratchet(baseline_doc=None):
    """Exit code with the shipped baseline, or with one written for this arm."""
    real = W.BASELINE
    tmp = None
    try:
        if baseline_doc is not None:
            fd, tmp = tempfile.mkstemp(suffix='.json')
            os.close(fd)
            with io.open(tmp, 'w', encoding='utf-8') as fh:
                json.dump(baseline_doc, fh)
            W.BASELINE = tmp
        return W.ratchet([])
    finally:
        W.BASELINE = real
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


check('the shipped baseline PASSES today -- a ratchet that fails on a clean '
      'tree is one somebody turns off', run_ratchet() == 0, 'expected exit 0')

with io.open(W.BASELINE, encoding='utf-8') as _fh:
    _shipped = json.load(_fh)
_worst = max(_shipped['counts'], key=lambda k: _shipped['counts'][k])

# A baseline one lower for a single app is exactly what "somebody added a new
# blind write site" looks like to this tool.
_tightened = dict(_shipped['counts'])
_tightened[_worst] -= 1
check('a NEW blind write site FAILS the ratchet -- it can fire',
      run_ratchet({'recorded': 'fixture', 'counts': _tightened}) == 1,
      'expected exit 1 with %s tightened to %d' % (_worst, _tightened[_worst]))

# The other direction: a count that FELL must not be reported as a regression.
_loosened = dict(_shipped['counts'])
_loosened[_worst] += 5
check('a count that FELL is not a regression',
      run_ratchet({'recorded': 'fixture', 'counts': _loosened}) == 0,
      'expected exit 0')

# A MISSING baseline must REFUSE rather than record today as the standard.
# "Could not run" is a third state and is never folded into "passed" (PR 1.11).
_real = W.BASELINE
try:
    W.BASELINE = os.path.join(REPO, 'tools', 'no_such_baseline_file.json')
    check('a MISSING baseline is COULD-NOT-RUN (exit 2), never a silent first run',
          W.ratchet([]) == 2, 'expected exit 2')
finally:
    W.BASELINE = _real

# An app ABSENT from the baseline counts as zero, so a new app arriving with a
# blind write fails rather than being grandfathered in.
_partial = dict((k, v) for k, v in _shipped['counts'].items() if k != _worst)
check('an app ABSENT from the baseline counts as zero, so a new app with a '
      'blind write fails',
      run_ratchet({'recorded': 'fixture', 'counts': _partial}) == 1,
      'expected exit 1 with %s removed from the baseline' % _worst)

# Without this, an app could drop out of the scan entirely and its hazards would
# leave the total silently -- a shrinking number that reads as an improvement.
check('the baseline records every app the scan measures, so none is invisible',
      set(_shipped['counts']) == set(W.apps([])),
      'baseline %d apps, scan %d' % (len(_shipped['counts']), len(W.apps([]))))

check('the baseline is declared OPEN AND UNREAD, not accepted',
      'OPEN AND UNREAD' in _shipped.get('note', ''), _shipped.get('note', '')[:120])


print('\n' + ('%d ARM(S) FAILED: %s' % (len(fails), ', '.join(fails))
              if fails else 'ALL ARMS PASS'))
sys.exit(1 if fails else 0)
