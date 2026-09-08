"""Mutation probe for tests/sairndental_write_failure_voice.js.

A test suite that has only ever been green is a suite whose behaviour nobody
knows. This breaks sairndental.html in sixteen specific ways -- one per defect
the suite claims to hold -- and asserts the suite goes RED for every one, then
restores the file and verifies it byte-identical by sha256.

WHY IT EXISTS AT ALL. The suite it probes was written on 2026-09-04 and its
mutation arms were run BY HAND, which is why Fourth's independent review the
next day could find three live defects in the code it covered and two holes in
the suite itself. Two more holes were found by running THIS, not by reading:

  * probe 10 was SILENT on the first run. Changing submitCharge to ask for
    'dnt_payments' -- exactly the defect the pairing walk exists to catch, in
    the function that reports the CHARGE ledger -- left the suite green,
    because the walk only ever saw functions containing sdnData('write') and
    submitCharge calls addChargeEntry() instead. The three functions carrying
    the ledger's failure sentences were outside the walk entirely. The walk now
    follows one level of helper call.

  * probes 4b/5b and 13/14 cover a defect this fix INTRODUCED. Keeping a row
    locally when the server could not be reached makes "recorded on this
    device" a claim, and st() can fail on a full localStorage. Ignoring its
    return was safe while a kept row implied the server already had it.

Run:  python tests/sairndental_write_failure_probe.py
"""
import hashlib
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TARGET = os.path.join(ROOT, 'sairndental.html')
SUITE = os.path.join('tests', 'sairndental_write_failure_voice.js')

# (name, exact source to replace, what to replace it with). Each anchor must
# appear EXACTLY ONCE -- an anchor that stops matching is reported as
# ANCHOR-n and fails the run rather than silently probing nothing, which is
# the way a mutation suite rots.
MUTATIONS = [
    ("1. dntLastErrText shows the raw browser exception again",
     "  return (e&&e.status)?e.message:'';",
     "  return e?e.message:'';"),
    ("2. sdnData stops recording which failures a server answered",
     "message:(d&&d.error&&d.error.message)||'',status:r.status};",
     "message:(d&&d.error&&d.error.message)||''};"),
    ("3. every failure is treated as a refusal",
     "  return !!(e&&e.status&&e.status<500);",
     "  return true;"),
    ("4. addChargeEntry drops the row on any null again",
     "  if(syncResult||!refused){var list=charges();list.push(rec);kept=st('dnt_charges_list',list);}",
     "  if(syncResult){var list=charges();list.push(rec);kept=st('dnt_charges_list',list);}"),
    ("5. addPaymentEntry drops the row on any null again",
     "  if(syncResult||!refused){var list=payments();list.push(rec);kept=st('dnt_payments_list',list);}",
     "  if(syncResult){var list=payments();list.push(rec);kept=st('dnt_payments_list',list);}"),
    ("4b. addChargeEntry ignores st()'s return and calls a lost row kept",
     "  if(syncResult||!refused){var list=charges();list.push(rec);kept=st('dnt_charges_list',list);}",
     "  if(syncResult||!refused){var list=charges();list.push(rec);st('dnt_charges_list',list);kept=true;}"),
    ("5b. addPaymentEntry ignores st()'s return and calls a lost row kept",
     "  if(syncResult||!refused){var list=payments();list.push(rec);kept=st('dnt_payments_list',list);}",
     "  if(syncResult||!refused){var list=payments();list.push(rec);st('dnt_payments_list',list);kept=true;}"),
    ("6. the no-licence branch leaves the previous error in place",
     "  if(!lic){dntLastErr[resource]={code:'NO_LICENCE',message:''};return Promise.resolve(null);}",
     "  if(!lic)return Promise.resolve(null);"),
    ("7. setAppointmentStatus returns the appointment alone",
     "  return {appt:a, syncResult:syncResult};",
     "  return a;"),
    ("8. submitCompleteVisit announces success regardless of the appointment write",
     "  if(!appt||!appt.syncResult){",
     "  if(false){"),
    ("9. submitPayment clears the box on a refusal too",
     "      toast(dntWriteFailText('dnt_payments','The payment was not saved -- nothing was recorded on this device or the server.'),9000);\n      return;",
     "      toast(dntWriteFailText('dnt_payments','The payment was not saved -- nothing was recorded on this device or the server.'),9000);\n      $('pm-add-amount').value='';return;"),
    ("10. submitCharge asks for another resource's error (the pairing walk)",
     "      ? dntWriteFailText('dnt_charges','The charge was not saved -- nothing was recorded on this device or the server.')",
     "      ? dntWriteFailText('dnt_payments','The charge was not saved -- nothing was recorded on this device or the server.')"),
    ("11. a dntLastErrText path asks for the WRONG resource",
     "if(!syncResult){toast(dntLastErrText('dnt_coverage_rules')||'Could not save the coverage rule -- nothing was changed',7000);return;}",
     "if(!syncResult){toast(dntLastErrText('dnt_patients')||'Could not save the coverage rule -- nothing was changed',7000);return;}"),
    ("12. submitCharge stops distinguishing unreachable from refused",
     "    toast(result.refused\n      ? dntWriteFailText('dnt_charges','The charge was not saved -- nothing was recorded on this device or the server.')\n      : (result.kept\n        ? 'Recorded on THIS DEVICE ONLY -- the server could not be reached. It is not on any other workstation and will not upload by itself.'\n        : 'The charge was NOT saved anywhere -- the server could not be reached and this device could not store it either.'),\n      9000);",
     "    toast(dntWriteFailText('dnt_charges','The charge was not saved -- nothing was recorded on this device or the server.'),9000);"),
    ("13. submitCharge stops distinguishing a kept row from a lost one",
     "      : (result.kept\n        ? 'Recorded on THIS DEVICE ONLY -- the server could not be reached. It is not on any other workstation and will not upload by itself.'\n        : 'The charge was NOT saved anywhere -- the server could not be reached and this device could not store it either.'),",
     "      : 'Recorded on THIS DEVICE ONLY -- the server could not be reached. It is not on any other workstation and will not upload by itself.',"),
    ("14. submitPayment promises the device has a row it could not store",
     "    if(!result.kept){",
     "    if(false){"),
]


def main():
    orig = open(TARGET, encoding='utf-8', newline='').read()
    before = hashlib.sha256(orig.encode('utf-8')).hexdigest()

    # The suite must be GREEN before any of this means anything.
    baseline = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True, text=True)
    # Labelled GREEN rather than BITES: nothing was broken here, and a baseline
    # row reading like a passing probe is exactly the kind of small dishonesty
    # that makes a report harder to read than it needs to be.
    results = [("0. the suite is green on the unmodified file",
                "GREEN" if baseline.returncode == 0 else "RED-BEFORE-MUTATION")]

    try:
        for name, old, new in MUTATIONS:
            n = orig.count(old)
            if n != 1:
                results.append((name, 'ANCHOR-%d' % n))
                continue
            open(TARGET, 'w', encoding='utf-8', newline='').write(orig.replace(old, new, 1))
            r = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True, text=True)
            results.append((name, 'BITES' if r.returncode != 0 else 'SILENT'))
    finally:
        # Restored even if the run dies mid-way. A probe that leaves a mutated
        # app on disk is worse than no probe.
        open(TARGET, 'w', encoding='utf-8', newline='').write(orig)

    after = hashlib.sha256(open(TARGET, encoding='utf-8', newline='').read().encode('utf-8')).hexdigest()
    for name, verdict in results:
        print('  %-8s %s' % (verdict, name))
    print()
    print('sairndental.html restored byte-identical:', before == after, before[:16])
    bad = [n for n, v in results if v not in ('BITES', 'GREEN')]
    print('PROBES THAT DID NOT BITE:', bad if bad else 'none')
    return 1 if (bad or before != after) else 0


if __name__ == '__main__':
    sys.exit(main())
