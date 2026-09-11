"""Negative controls for tests/dnt_vendor_write_confirmation.js.

    python tests/dnt_vendor_write_confirmation_probe.py

A suite that has only ever been green is a suite whose behaviour nobody knows.
Each control below REINTRODUCES one half of the live defect in sairndental.html,
asserts the suite goes RED, restores the file, and verifies it byte-identical.

THE DEFECT, and it was live: sql/sairndental_vendor_schema.sql has been run, so
`st(...); dntPushVendorPricing(rules); toast('discount set to 12%')` -- an
unawaited push whose result nobody read -- showed success on a failed write,
and `dntSyncFromServer()` then put the server's older object straight back over
it. Wholesale-replace is the RIGHT design (it is what makes a removal
expressible); the missing half was confirming the write before trusting it.

REFUSES A DIRTY TARGET, like every other mutation probe here since 2026-09-09:
the bytes it would snapshot as "original" would not be the original, and the
restore would bake somebody else's edit in while reporting byte-identical.
"""
import hashlib
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TARGET = 'sairndental.html'
SUITE = os.path.join('tests', 'dnt_vendor_write_confirmation.js')

# (name, exact text, replacement). Each anchor must appear EXACTLY ONCE -- an
# anchor that stops matching is reported as ANCHOR-n and FAILS, because a
# mutation that silently probes nothing is how a control suite rots.
MUTATIONS = [
    # ANCHORED ON THE UNIQUE THIRD WRITER. The first version used the shared
    # `.then(function(ok){ dntVendorSaveToast(ok,_msg); })` line, which two
    # writers use verbatim -- reported ANCHOR-2 and probed nothing. An anchor
    # that is not unique is a control that silently does not run.
    ("1. the toast goes back to firing before the push result is known",
     "  dntPushVendorPricing(rules).then(function(ok){ dntVendorSaveToast(ok,"
     "'Price override set for '+sku); });",
     "  dntPushVendorPricing(rules);\n  toast('Price override set for '+sku);"),
    ("2. a refused push no longer says NOT SAVED",
     "    toast('NOT SAVED TO THE SERVER",
     "    toast('Saved. ('NOT SAVED TO THE SERVER"),
    # RE-ANCHORED 2026-09-11, and this one is the sharper of the two. The old
    # anchor carried SIX leading spaces, which is the MISSING-FIELDS branch of
    # dntPushOne(), not the refused branch this arm is named for. It still
    # matched EXACTLY ONCE, so the harness raised no ANCHOR-n error -- it just
    # quietly probed a different branch and reported SILENT. AN ANCHOR THAT IS
    # UNIQUE IS NOT THE SAME AS AN ANCHOR THAT IS RIGHT, and uniqueness is the
    # only half this harness can check. The anchor now includes the line that
    # follows it, which is what distinguishes the two branches.
    ("3. a refused push stops marking the key unconfirmed",
     "    if(storeKey) dntMarkUnconfirmed(storeKey,true);\n    return null;",
     "    if(false) dntMarkUnconfirmed(storeKey,true);\n    return null;"),
    # The branch the old anchor had drifted ONTO deserves its own control:
    # nothing covered it once arm 3 was moved back where it belongs, and a
    # response that comes back without the fields that were sent is exactly the
    # case this suite exists for.
    ("3b. a response MISSING fields stops marking the key unconfirmed",
     "      if(storeKey) dntMarkUnconfirmed(storeKey,true);\n      return r;",
     "      if(false) dntMarkUnconfirmed(storeKey,true);\n      return r;"),
    # RE-ANCHORED 2026-09-11. The old anchor expected an else-if that no longer
    # exists: dntPushOne() was refactored and the branch collapsed into a flat
    # if. That one DID report ANCHOR-0 and fail the probe, which is the harness
    # working as designed -- it had simply never been fixed.
    ("4. a successful push stops CLEARING the key, so the guard never lifts",
     "    if(storeKey) dntMarkUnconfirmed(storeKey,false);\n    return r;",
     "    if(false) dntMarkUnconfirmed(storeKey,false);\n    return r;"),
    ("5. contacts hydration overwrites an unconfirmed local write again",
     "    if(dntIsUnconfirmed('dnt_vendor_contacts')){",
     "    if(false&&dntIsUnconfirmed('dnt_vendor_contacts')){"),
    ("6. pricing hydration overwrites an unconfirmed local write again",
     "    if(dntIsUnconfirmed('dnt_vendor_pricing_rules')){",
     "    if(false&&dntIsUnconfirmed('dnt_vendor_pricing_rules')){"),
    ("7. the refresh calls a held-back sync 'Refreshed from server' again",
     "    }else if(result&&result.unconfirmed_held&&result.unconfirmed_held.length){",
     "    }else if(false&&result.unconfirmed_held&&result.unconfirmed_held.length){"),
    ("8. the flag stops being persisted, so a reload forgets it",
     "  try{ localStorage.setItem(DNT_UNCONFIRMED_KEY,JSON.stringify(o)); return true; }",
     "  try{ return true; }"),
]


def dirty():
    r = subprocess.run(['git', 'status', '--porcelain', '--', TARGET], cwd=ROOT,
                       capture_output=True, text=True)
    return r.stdout.strip()


def run_suite():
    return subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True).returncode


def main():
    already = dirty()
    if already:
        print('SKIPPED: %s is already modified, so the bytes this probe would' % TARGET)
        print('snapshot as "original" are not the original and the restore would')
        print('bake them in. Nothing was verified. Working tree:')
        print('    %s' % already)
        return 3

    path = os.path.join(ROOT, TARGET)
    orig = open(path, 'rb').read()
    before = hashlib.sha256(orig).hexdigest()

    results = [('0. the suite is green on the unmodified file',
                'GREEN' if run_suite() == 0 else 'RED-BEFORE-MUTATION')]
    try:
        for name, old, new in MUTATIONS:
            n = orig.count(old.encode('utf-8'))
            if n != 1:
                results.append((name, 'ANCHOR-%d' % n))
                continue
            open(path, 'wb').write(
                orig.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
            results.append((name, 'BITES' if run_suite() != 0 else 'SILENT'))
            open(path, 'wb').write(orig)
    finally:
        # Restored even if the run dies mid-way. A probe that leaves a mutated
        # app on disk is worse than no probe -- and this one mutates a LIVE app
        # whose schema has been run.
        open(path, 'wb').write(orig)

    for name, verdict in results:
        print('  %-8s %s' % (verdict, name))
    after = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    print('')
    print('%-22s restored byte-identical: %s  %s'
          % (TARGET, after == before, before[:16]))
    bad = [n for n, v in results if v not in ('BITES', 'GREEN')]
    print('CONTROLS THAT DID NOT BITE:', bad if bad else 'none')
    # SILENT HAS TWO CAUSES AND THEY NEED OPPOSITE FIXES. Said here because
    # getting this wrong cost a real arm: on 2026-09-11 arm 3's anchor had
    # drifted onto a DIFFERENT branch of dntPushOne(), still matched exactly
    # once so the harness raised nothing, and reported SILENT -- which reads as
    # "the suite is weak here" when it actually meant "this anchor is no longer
    # pointing at what its name says". Check the anchor BEFORE adding an
    # assertion; an anchor that is unique is not the same as an anchor that is
    # right, and uniqueness is the only half this harness can check.
    if any(v == 'SILENT' for _, v in results):
        print('')
        print('A SILENT control means ONE OF TWO THINGS, and they need opposite fixes:')
        print('  (a) the suite genuinely does not assert this behaviour  -> add the assertion;')
        print('  (b) the ANCHOR has drifted onto different code that the suite')
        print('      does not cover -> re-anchor it. It can still match exactly')
        print('      once while pointing at the wrong branch, which is what')
        print('      happened to arm 3 on 2026-09-11. Read the anchor first.')
    return 1 if (bad or after != before) else 0


if __name__ == '__main__':
    sys.exit(main())
