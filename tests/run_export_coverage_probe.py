"""tests/run_export_coverage_probe.py

Run:  python tests/run_export_coverage_probe.py

CONTROLS_FOR = tools/export_coverage_check.py

── WHAT IS LOCKED, AND WHAT DELIBERATELY IS NOT ──────────────────────────────
The subject answers ONE half of item 39's question -- can a Class A record be
produced as a FILE -- and says in its own header that the other half, whether a
person can see it on screen, is not mechanical. This controls the half it
claims.

The verdict table is PINNED by name in section E. That is the point: these
eleven answers were hand-verified against the source on 2026-09-14, so any
later change to an app's export registry flips an arm and has to be looked at
rather than absorbed. When one genuinely changes, change the expectation IN THE
SAME COMMIT as the app -- that edit is the record that somebody decided.

Section D is the teeth. Section A fails CLOSED: the set comes from a document,
and a document that stops parsing must not become a clean sweep over nothing.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['export_coverage_check.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import export_coverage_check as X                                # noqa: E402

SUBJECT = os.path.join(REPO, 'tools', 'export_coverage_check.py')
FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


print('A. the Class A set is PARSED from the scoping document, and fails closed')
pairs, why = X.class_a()
ok('the real document parses', pairs is not None, why)
ok('...to more than the four apps that carry one resource each',
   pairs and len(pairs) >= 8, pairs and len(pairs))
ok('sv_controlled is included -- it is named in the PROSE under the table, '
   'not in it', ('sairnvet', 'sv_controlled') in (pairs or []), pairs)
_src = X.SOURCE
try:
    X.SOURCE = os.path.join(REPO, 'docs', 'no-such-document-39c.md')
    p2, why2 = X.class_a()
    ok('a MISSING source document is refused, not treated as zero findings',
       p2 is None and 'missing' in (why2 or ''), why2)
    empty = tempfile.mkdtemp(prefix='exp_probe_')
    X.SOURCE = os.path.join(empty, 'table-gone.md')
    io.open(X.SOURCE, 'w', encoding='utf-8').write('# no table here\n')
    p3, why3 = X.class_a()
    ok('a source document whose TABLE stopped parsing is refused too',
       p3 is None and 'fewer' in (why3 or ''), why3)
    shutil.rmtree(empty, ignore_errors=True)
finally:
    X.SOURCE = _src
ok('SOURCE was restored', X.SOURCE == _src)

print('\nB. the two registry shapes are read, and "no machinery" is a THIRD '
      'state rather than an empty registry')
rf, rf_has = X.app_exports('sairnroofing')
ok('sairnroofing: the `resource:..., action:read` shape is read',
   rf_has and 'rf_certifications' in rf, sorted(rf or []))
dn, dn_has = X.app_exports('sairndental')
ok('sairndental: a registry keyed by SHORT LABEL is resolved through its '
   'accessor to a resource name', dn_has and 'dnt_credentials' in dn,
   sorted(dn or []))
ok('...and resolving it did NOT sweep in every resource the app holds',
   dn is not None and len(dn) < 12, sorted(dn or []))
mc, mc_has = X.app_exports('sairnmechanical')
ok('sairnmechanical has NO export machinery, and that is not the same as an '
   'empty registry', mc == set() and mc_has is False, (mc, mc_has))
nn, _ = X.app_exports('no_such_app_39c')
ok('an app file that does not exist is unreadable, not empty', nn is None, nn)

print('\nC. --check gates on the gap that is a GAP, and not on the one that is '
      'a missing feature')
rc = X.main(['--check'])
ok('the repo FAILS --check today, because four resources sit in apps whose '
   'export registry already exists and does not carry them', rc == 1, rc)
# The registry that runs this keeps only lines starting `  - ` or `FAIL`. A
# check wired by something it does not emit reports nothing while looking
# healthy -- literal_drift_check.py sat that way for weeks. Driven through the
# real reader rather than asserted about the format.
out = subprocess.run([sys.executable, SUBJECT, '--check'],
                     capture_output=True, text=True, cwd=REPO)
sys.path.insert(0, os.path.join(REPO, 'tools'))
import report_only_checks as R                                   # noqa: E402
findings, _ = R.by_exit(out.returncode, out.stdout)
ok('...and the four NAMES survive report_only_checks.by_exit, rather than '
   'collapsing to the string "exit 1"',
   len(findings) == 4 and all('sairn' in f for f in findings), findings)

print('\nD. teeth -- blind the registry reader and the EXPORTABLE answers must '
      'collapse')
TMP = tempfile.mkdtemp(prefix='exp_probe_')
try:
    src = io.open(SUBJECT, encoding='utf-8').read()
    ANCHOR = 'ROOFING_ENTRY = re.compile('
    ok('the sabotage anchor is still present in the subject', ANCHOR in src,
       'anchor has gone stale -- this section tests NOTHING until it is updated')
    i = src.index(ANCHOR)
    j = src.index('\n', i)
    broken = src[:i] + "ROOFING_ENTRY = re.compile(r'ZZ_NEVER_MATCHES_ZZ')" + src[j:]
    ok('the sabotage actually changed the file', broken != src)
    p = os.path.join(TMP, 'broken_export_check.py')
    io.open(p, 'w', encoding='utf-8').write(broken)
    drv = os.path.join(TMP, 'drive.py')
    io.open(drv, 'w', encoding='utf-8').write(
        'import sys, json\n'
        'sys.path.insert(0, %r)\n' % TMP +
        'import broken_export_check as B\n'
        'B.REPO = %r\n' % REPO +
        "B.SOURCE = %r\n" % X.SOURCE +
        "found, has = B.app_exports('sairnroofing')\n"
        'print(json.dumps({"found": sorted(found or []), "has": has}))\n')
    out = subprocess.run([sys.executable, drv], capture_output=True, text=True,
                         cwd=TMP)
    ok('the broken copy runs at all', out.returncode == 0, out.stderr[-300:])
    ok('a blinded registry reader reports rf_certifications as NOT exportable',
       out.returncode == 0 and 'rf_certifications' not in out.stdout,
       'still found it -- section B was not testing the reader: '
       + out.stdout.strip()[:200])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the throwaway copy is gone', not os.path.isdir(TMP))

print('\nE. the eleven answers, pinned by name as of 2026-09-14')
# EXPORTABLE / NOT IN REGISTRY (the app has one and this is not in it) /
# NO MACHINERY (the app has no export path at all).
EXPECTED = {
    ('sairncare', 'alf_staff_credentials'): 'NO MACHINERY',
    ('sairndental', 'dnt_charges'): 'NOT IN REGISTRY',
    ('sairndental', 'dnt_credentials'): 'EXPORTABLE',
    ('sairndental', 'dnt_payments'): 'NOT IN REGISTRY',
    ('sairndental', 'dnt_vendor_orders'): 'NOT IN REGISTRY',
    ('sairnmechanical', 'mech_credentials'): 'NO MACHINERY',
    ('sairnroofing', 'rf_certifications'): 'EXPORTABLE',
    ('sairnroofing', 'rf_claim_photos'): 'NOT IN REGISTRY',
    ('sairnroofing', 'rf_proposals'): 'EXPORTABLE',
    ('sairnvet', 'sv_audit_log'): 'NO MACHINERY',
    ('sairnvet', 'sv_controlled'): 'NO MACHINERY',
}
pairs, _ = X.class_a()
cache, actual = {}, {}
for app, res in pairs:
    if app not in cache:
        cache[app] = X.app_exports(app)
    exported, has = cache[app]
    actual[(app, res)] = ('EXPORTABLE' if res in exported
                          else 'NOT IN REGISTRY' if has else 'NO MACHINERY')
ok('the Class A set is exactly the eleven that were verified',
   set(actual) == set(EXPECTED),
   'added %s / gone %s' % (sorted(set(actual) - set(EXPECTED)),
                           sorted(set(EXPECTED) - set(actual))))
wrong = {k: (EXPECTED.get(k), v) for k, v in actual.items()
         if k in EXPECTED and EXPECTED[k] != v}
ok('every verdict still matches the hand-verified answer', not wrong, wrong)
ok('and the answers are not all the same, so the table distinguishes anything',
   len(set(actual.values())) == 3, sorted(set(actual.values())))

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
