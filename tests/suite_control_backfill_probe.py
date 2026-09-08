"""Negative controls for five suites that had none committed.

WHY THESE FIVE. On 2026-09-08 a sweep of the open-work index found 29 rows
crediting a suite with a specific number of negative controls. Most of those
claims are backed by something real -- either a separate probe harness, or
control arms living INSIDE the suite (`api/sd-data-dental-ledger-validation.
test.js` runs fourteen of them). **The first version of that sweep missed the
in-suite shape entirely and was retracted within the hour**; these five are what
survived the correction: suites whose controls were run by hand by a session
that has since ended, and which nothing on disk has ever watched go red.

A number in a row is a fact about a past run. This makes it a fact about the
repo.

ONE FILE RATHER THAN FIVE, deliberately. The five share no subject -- a vet
storage wrapper, two hydrate functions, a coverage-rule editor and a settings
PATCH endpoint -- but they share a reason for existing, and five near-identical
harnesses would be five places to keep in step. The table is the harness; adding
a sixth suite is three lines.

WHAT A CONTROL HERE IS: revert one specific fix in the real source, assert the
suite goes RED, restore the file, and verify it byte-identical by sha256. An
anchor that stops matching is reported as ANCHOR-n and FAILS the run -- a
mutation that silently probes nothing is how a control suite rots.

Run:  python tests/suite_control_backfill_probe.py
"""
import hashlib
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()

# suite -> (target source, [(control name, exact text, replacement), ...])
SUITES = [
    ('tests/sv_storage_guard.js', 'sairnvet.html', [
        ("a full disk goes back to being silent",
         "    try{ console.error('SAIRNvet: localStorage write FAILED",
         "    try{ (function(){}) ('SAIRNvet: localStorage write FAILED"),
        ("every failure is blamed on the quota",
         "  return e.name==='QuotaExceededError'",
         "  return true; return e.name==='QuotaExceededError'"),
        # The early `if(_svUnreadable[key])` return is NOT the anchor, and
        # trying it first is why this control came back SILENT: on the first
        # call the latch is still false, so what actually refuses a corrupt
        # value is the parse-verification block below it. The arm tests the
        # first call. A control has to break what the arm exercises.
        ("the corrupt-value verification is removed, so a bad store is overwritten",
         "        catch(err){_svUnreadable[key]=true;_svWriteFailed=key;svBlockForCorruptStore([key]);return false;}",
         "        catch(err){}"),
    ]),
    ('tests/sairnlaw_hydrate.js', 'sairnlaw.html', [
        ("hydrate runs with no licence key",
         "  if(!lawLicenseKey())return{merged:0,failed:0};",
         "  if(false)return{merged:0,failed:0};"),
        ("a failed read is treated as an empty one",
         "    if(!Array.isArray(rows)){failed++;continue;}",
         "    if(!Array.isArray(rows)){rows=[];}"),
        ("the server copy clobbers local records instead of merging",
         "    rows.forEach(function(r){if(r&&r.id!=null&&!have[String(r.id)]){local.push(r);have[String(r.id)]=true;added++;}});",
         "    local=rows.slice();added=rows.length;"),
        ("a no-op boot writes anyway",
         "    if(added){st(key,local);merged+=added;}",
         "    st(key,local);merged+=added;"),
    ]),
    ('tests/sairndental_coverage_edit.js', 'sairndental.html', [
        ("editing a rule that is gone half-loads instead of refusing",
         "  if(!rule){toast('That coverage rule is no longer on file -- refresh and try again',4000);return;}",
         "  if(!rule){rule={};}"),
        ("an edit mints a NEW id, so the server inserts instead of updating",
         "  var rec={id:cvEditId||newId('CV'),payer:payer,procedure_type_id:procedureTypeId,coverage_percent:pct,",
         "  var rec={id:newId('CV'),payer:payer,procedure_type_id:procedureTypeId,coverage_percent:pct,"),
        ("created_at is stamped with today, losing when the rule was really written",
         "    created_at:(existing&&existing.created_at)||dntLocalToday()};",
         "    created_at:dntLocalToday()};"),
    ]),
    ('api/sd-data-dental-settings-patch.test.js', 'api/sd-data.js', [
        ("the PATCH goes back to being a PUT, so one panel erases another's keys",
         "    const dntMerged = Object.assign({}, dntBase, payload);",
         "    const dntMerged = payload;"),
        ("an unreadable current row no longer fails closed",
         "      res.status(503).json({ error: { code: 'SETTINGS_READ_UNAVAILABLE'",
         "      if(false) res.status(503).json({ error: { code: 'SETTINGS_READ_UNAVAILABLE'"),
    ]),
    ('tests/sairnsenior_org_hydrate.js', 'sairnsenior.html', [
        # This suite is one of my own from earlier the same session, and its row
        # claimed three mutation probes that were run by hand and never
        # committed. Fixing my own row first would have been the comfortable
        # order; it is last here because it is the least consequential.
        # ANCHORED ON THE WHOLE OPENING OF senHydrateOrg, because it
        # deliberately mirrors senHydrateReferrals line for line -- the short
        # forms of these four appear three to six times in the file and the
        # first attempt reported ANCHOR-6. A shape shared on purpose is not an
        # anchor.
        ("hydrate runs with no licence key",
         "  if(!senLicenseKey())return Promise.resolve(false);\n"
         "  return Promise.all([\n"
         "    senData('read','sen_branches',null,true),",
         "  if(false)return Promise.resolve(false);\n"
         "  return Promise.all([\n"
         "    senData('read','sen_branches',null,true),"),
        # THE REMAINING THREE ALL INJECT AFTER THE ONE UNIQUE LINE IN THIS
        # FUNCTION -- the pair list naming both resources. Everything below it
        # is shared verbatim with senHydrateReferrals and appears three times.
        #
        # And the first attempt at the failed-read control was SILENT for a
        # real reason worth keeping: turning a failed read into `rows=[]` does
        # not change what the suite can see. An empty list adds nothing, so
        # nothing is written, so "leaves that resource alone" still holds. The
        # defect that arm actually guards is a failed read WIPING local data,
        # so that is what gets injected.
        ("a failed read WIPES the local list instead of leaving it alone",
         "    [['sen_branches',res[0]],['sen_applicants',res[1]]].forEach(function(pair){",
         "    [['sen_branches',res[0]],['sen_applicants',res[1]]].forEach(function(pair){\n"
         "      if(!pair[1]||!Array.isArray(pair[1])){st(pair[0],[]);return;}"),
        ("the server copy clobbers local records instead of merging",
         "    [['sen_branches',res[0]],['sen_applicants',res[1]]].forEach(function(pair){",
         "    [['sen_branches',res[0]],['sen_applicants',res[1]]].forEach(function(pair){\n"
         "      if(pair[1]&&Array.isArray(pair[1])&&pair[1].length){st(pair[0],pair[1]);merged=true;return;}"),
        ("a no-op boot writes anyway",
         "    [['sen_branches',res[0]],['sen_applicants',res[1]]].forEach(function(pair){",
         "    [['sen_branches',res[0]],['sen_applicants',res[1]]].forEach(function(pair){\n"
         "      st(pair[0],ld(pair[0],[]));"),
        ("hydrate is never called at boot",
         "  senHydrateOrg().then(function(merged){",
         "  Promise.resolve(false).then(function(merged){"),
    ]),
]


def run(suite):
    exe = ['node', suite] if suite.endswith('.js') else [sys.executable, suite]
    return subprocess.run(exe, cwd=ROOT, capture_output=True).returncode


def main():
    targets = sorted({t for _, t, _ in SUITES})
    orig = {t: open(os.path.join(ROOT, t), 'rb').read() for t in targets}
    before = {t: hashlib.sha256(v).hexdigest() for t, v in orig.items()}

    results = []
    try:
        for suite, target, controls in SUITES:
            rc = run(suite)
            results.append((suite, '0. green on the unmodified file',
                            'GREEN' if rc == 0 else 'RED-BEFORE-MUTATION'))
            src = orig[target]
            for n, (name, old, new) in enumerate(controls, 1):
                count = src.count(old.encode('utf-8'))
                if count != 1:
                    results.append((suite, '%d. %s' % (n, name), 'ANCHOR-%d' % count))
                    continue
                open(os.path.join(ROOT, target), 'wb').write(
                    src.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
                rc = run(suite)
                results.append((suite, '%d. %s' % (n, name),
                                'BITES' if rc != 0 else 'SILENT'))
                open(os.path.join(ROOT, target), 'wb').write(src)
    finally:
        # Restored even if the run dies mid-way. A probe that leaves a mutated
        # app on disk is worse than no probe.
        for t in targets:
            open(os.path.join(ROOT, t), 'wb').write(orig[t])

    last = None
    for suite, name, verdict in results:
        if suite != last:
            print('\n-- %s --' % suite)
            last = suite
        print('  %-8s %s' % (verdict, name))

    print()
    ok = True
    for t in targets:
        after = hashlib.sha256(open(os.path.join(ROOT, t), 'rb').read()).hexdigest()
        ok = ok and after == before[t]
        print('%-24s restored byte-identical: %s  %s' % (t, after == before[t], before[t][:16]))
    bad = [n for _, n, v in results if v not in ('BITES', 'GREEN')]
    print('CONTROLS THAT DID NOT BITE:', bad if bad else 'none')
    return 1 if (bad or not ok) else 0


if __name__ == '__main__':
    sys.exit(main())
