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

print('\n' + ('%d ARM(S) FAILED: %s' % (len(fails), ', '.join(fails))
              if fails else 'ALL ARMS PASS'))
sys.exit(1 if fails else 0)
