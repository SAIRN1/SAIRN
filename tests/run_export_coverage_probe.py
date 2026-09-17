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
# Compared against the app's OWN sync-pair count rather than a magic number.
# The first version of this arm was `< 12`, which was one more than the answer
# on the day it was written -- so adding three real exports on 2026-09-14 took
# it red on a correct change. A bound derived from the thing it is bounding
# cannot go stale that way.
_dn_src = io.open(os.path.join(REPO, 'sairndental.html'),
                  encoding='utf-8', errors='replace').read()
_dn_pairs = len(set(a for a, _ in X.PAIR.findall(_dn_src)))
ok('...and resolving it did NOT sweep in every resource the app holds',
   dn is not None and 0 < len(dn) < _dn_pairs,
   '%d resolved of %d sync pairs' % (len(dn or []), _dn_pairs))
# ── THIS ARM WAS "sairnmechanical HAS NO EXPORT MACHINERY" UNTIL 2026-09-16 ──
# It was a correct arm and it stopped describing the app the moment
# sairnmechanical.html gained MECH_EXPORTS. What it was really defending is the
# thing worth keeping: a resource declared by a registry must RESOLVE to itself,
# not to an empty set that the reader then labels. So it now drives the same
# app in the direction it actually goes, and the NONE state -- which no app is
# in any more -- is driven directly in section C instead.
mc, mc_state = X.app_exports('sairnmechanical')
ok('sairnmechanical declares mech_credentials in its registry, and it resolves',
   mc == {'mech_credentials'} and mc_state == X.REGISTRY, (mc, mc_state))
nn, _ = X.app_exports('no_such_app_39c')
ok('an app file that does not exist is unreadable, not empty', nn is None, nn)

print('\nC. --check gates on the gap that is a GAP, and not on the one that is '
      'a missing feature')
# ── THIS ARM FLIPPED ON 2026-09-14 AND THE FLIP IS THE RECORD ──────────────
# It read "the repo FAILS --check today, because four resources sit in apps
# whose export registry already exists and does not carry them". All four were
# then closed -- dnt_charges, dnt_payments and dnt_vendor_orders got registry
# entries and Export CSV buttons, rf_claim_photos got a fanned-out evidence
# report. So the real repo now passes, and asserting only that would leave the
# GATING direction untested forever. Both directions are driven, and the
# failing one is driven against a PLANTED registry rather than against the app,
# so closing a real gap can never quietly disarm this.
rc = X.main(['--check'])
ok('the real repo PASSES --check -- all four gaps found on 2026-09-14 are '
   'closed', rc == 0, rc)

_real = X.app_exports
try:
    X.app_exports = lambda app: ((set(), X.REGISTRY) if app == 'sairnroofing'
                                 else _real(app))
    ok('a registry that EXISTS and drops a Class A resource fails --check',
       X.main(['--check']) == 1)
    X.app_exports = lambda app: (set(), X.NONE)
    ok('...but an app with NO export machinery at all does NOT fail -- that is '
       'a feature nobody built, not a gap in one that exists',
       X.main(['--check']) == 0)
    # ── AND NEITHER DOES THE THIRD STATE, WHICH IS THE POINT OF HAVING IT ──
    # UNLISTED means the tool could not enumerate the app. Gating on it would
    # be a blocking gate firing on a question it never answered -- PR 1.11
    # exactly -- and folding it back into REGISTRY is the single edit that
    # would do that silently, so it is driven here rather than assumed.
    X.app_exports = lambda app: (set(), X.UNLISTED)
    ok('...and an app with export machinery but NO REGISTRY TO READ does NOT '
       'fail either -- a could-not-tell must never be gated as a gap',
       X.main(['--check']) == 0)
finally:
    X.app_exports = _real
ok('app_exports was restored', X.app_exports is _real)

# The registry that runs this keeps only lines starting `  - ` or `FAIL`. A
# check wired by something it does not emit reports nothing while looking
# healthy -- literal_drift_check.py sat that way for weeks. Driven through the
# real reader, on a planted gap, rather than asserted about the format.
GAPDIR = tempfile.mkdtemp(prefix='exp_probe_')
try:
    PLANT = ('found = set(ROOFING_ENTRY.findall(code))\n'
             "    if app == 'sairnroofing':\n"
             "        found.discard('rf_claim_photos')")
    base = io.open(SUBJECT, encoding='utf-8').read()
    ok('the plant anchor is present in the subject',
       'found = set(ROOFING_ENTRY.findall(code))' in base,
       'anchor gone stale -- this arm plants nothing')
    io.open(os.path.join(GAPDIR, 'planted_check.py'), 'w',
            encoding='utf-8').write(
        base.replace('found = set(ROOFING_ENTRY.findall(code))', PLANT, 1))
    # REPO and SOURCE are overridden, because a copy in a temp directory
    # resolves REPO to that directory and then reports COULD-NOT-CHECK -- which
    # is correct behaviour and would have made this arm pass for the wrong
    # reason. It did, on the first run.
    drv = os.path.join(GAPDIR, 'drive_gap.py')
    io.open(drv, 'w', encoding='utf-8').write(
        'import sys\n'
        'sys.path.insert(0, %r)\n' % GAPDIR +
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import planted_check as B\n'
        'B.REPO = %r\n' % REPO +
        'B.SOURCE = %r\n' % X.SOURCE +
        "sys.exit(B.main(['--check']))\n")
    out = subprocess.run([sys.executable, drv], capture_output=True, text=True, encoding='utf-8', errors='replace',
                         cwd=REPO)
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import report_only_checks as R                               # noqa: E402
    findings, _ = R.by_exit(out.returncode, out.stdout)
    ok('the planted gap really did make the copy fail', out.returncode == 1,
       'exit=%d %s' % (out.returncode, (out.stdout + out.stderr)[-250:]))
    ok('...and the resource NAME survives report_only_checks.by_exit rather '
       'than collapsing to the string "exit 1"',
       len(findings) == 1 and 'rf_claim_photos' in findings[0], findings)
finally:
    shutil.rmtree(GAPDIR, ignore_errors=True)

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
    out = subprocess.run([sys.executable, drv], capture_output=True, text=True, encoding='utf-8', errors='replace',
                         cwd=TMP)
    ok('the broken copy runs at all', out.returncode == 0, out.stderr[-300:])
    ok('a blinded registry reader reports rf_certifications as NOT exportable',
       out.returncode == 0 and 'rf_certifications' not in out.stdout,
       'still found it -- section B was not testing the reader: '
       + out.stdout.strip()[:200])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the throwaway copy is gone', not os.path.isdir(TMP))

print('\nE. the eleven answers, pinned by name as of 2026-09-16')
# EXPORTABLE / NOT IN REGISTRY (the app has one and this is not in it) /
# NO REGISTRY TO READ (the app HAS export machinery and no registry this tool
# can enumerate -- a could-not-tell, hand-verified elsewhere) /
# NO MACHINERY (the app has no export path at all).
#
# ── SAIRNVET'S TWO MOVED OFF `NO MACHINERY` ON 2026-09-16 ──────────────────
# Not because the app changed under this pin -- because the pin was recording
# the tool's mislabel. sairnvet.html has carried `svExportControlled()` since
# before this table was written and gained `svExportDoseAudit()` on 2026-09-16,
# two real CSV writers on two real buttons; it has no registry, and the tool
# reported the absence of a registry as the absence of export machinery. This
# table pinned that verdict faithfully, which is what a pin does -- it makes an
# answer stable, not true. The tool now has a third state and these two carry it.
EXPECTED = {
    # ── THE LAST TWO MOVED OFF `NO MACHINERY` ON 2026-09-16 ────────────────
    # These two were the real thing the verdict described: no `createObjectURL`
    # and no `text/csv` anywhere in either app. Both now carry an export
    # registry in SAIRNdental's DNT_EXPORTS shape, each declaring its resource
    # the way RF_REPORTS does. Eleven of eleven Class A records can now be
    # produced as a file -- which is NOT a statement about who may produce one,
    # and `alf_staff_credentials` is scope-filtered per session.
    ('sairncare', 'alf_staff_credentials'): 'EXPORTABLE',
    # The four NOT IN REGISTRY verdicts became EXPORTABLE on 2026-09-14, in the
    # same commit as the app change, which is what this table is for: the edit
    # is the record that somebody decided, rather than a count quietly moving.
    ('sairndental', 'dnt_charges'): 'EXPORTABLE',
    ('sairndental', 'dnt_credentials'): 'EXPORTABLE',
    ('sairndental', 'dnt_payments'): 'EXPORTABLE',
    ('sairndental', 'dnt_vendor_orders'): 'EXPORTABLE',
    ('sairnmechanical', 'mech_credentials'): 'EXPORTABLE',
    ('sairnroofing', 'rf_certifications'): 'EXPORTABLE',
    ('sairnroofing', 'rf_claim_photos'): 'EXPORTABLE',
    ('sairnroofing', 'rf_proposals'): 'EXPORTABLE',
    ('sairnvet', 'sv_audit_log'): 'NO REGISTRY TO READ',
    ('sairnvet', 'sv_controlled'): 'NO REGISTRY TO READ',
}
LABEL = {X.REGISTRY: 'NOT IN REGISTRY', X.UNLISTED: 'NO REGISTRY TO READ',
         X.NONE: 'NO MACHINERY'}
pairs, _ = X.class_a()
cache, actual = {}, {}
for app, res in pairs:
    if app not in cache:
        cache[app] = X.app_exports(app)
    exported, state = cache[app]
    actual[(app, res)] = 'EXPORTABLE' if res in exported else LABEL[state]
ok('the Class A set is exactly the eleven that were verified',
   set(actual) == set(EXPECTED),
   'added %s / gone %s' % (sorted(set(actual) - set(EXPECTED)),
                           sorted(set(EXPECTED) - set(actual))))
wrong = {k: (EXPECTED.get(k), v) for k, v in actual.items()
         if k in EXPECTED and EXPECTED[k] != v}
ok('every verdict still matches the hand-verified answer', not wrong, wrong)
# Was 3 while four gaps were open, then 2, then 3 when NO REGISTRY TO READ was
# separated out, and is 2 again now that the last two NO MACHINERY verdicts have
# become EXPORTABLE. Stated rather than loosened to `>= 1`, which would pass on
# a table that had stopped distinguishing anything at all.
#
# NO MACHINERY IS NOW UNREACHABLE FROM THE REAL REPO and that is not the same
# as untested: section C drives `X.NONE` directly through --check, so the state
# that no longer occurs in any app is still pinned as NOT GATED.
ok('and the answers are not all the same, so the table distinguishes anything',
   len(set(actual.values())) == 2, sorted(set(actual.values())))

# ── THE ARM THAT KEEPS THE THIRD STATE FROM COLLAPSING BACK ────────────────
# The whole repair is that "I cannot enumerate this app" stopped being reported
# as "this app cannot export". An arm on the LABELS alone would still pass if
# somebody re-folded UNLISTED into NONE and re-pinned the table, so this one
# asserts the underlying fact the label rests on: sairnvet HAS export machinery.
sv_src = io.open(os.path.join(REPO, 'sairnvet.html'), encoding='utf-8',
                 errors='replace').read()
ok('SAIRNvet really does have export machinery, which is why NO MACHINERY was '
   'the wrong word',
   'svExportControlled(' in sv_src and 'svExportDoseAudit(' in sv_src
   and 'text/csv' in sv_src,
   'the premise of the third state has gone -- re-check before re-pinning')
ok('...and still no registry in either shape the tool reads, so the answer is '
   'a could-not-tell and not a gap',
   X.app_exports('sairnvet')[1] == X.UNLISTED, X.app_exports('sairnvet'))

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
