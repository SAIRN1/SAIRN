"""Negative controls for the fault-injection suites.

    python tests/faults/run_fault_suite_probe.py

A fault-injection suite that has only ever been green is exactly as unproven as
any other suite. Worse, in fact: its whole claim is that it catches what the
logic-level tests could not, and that claim is worth nothing until somebody has
watched it go red on the real defect.

EVERY CONTROL BELOW REINTRODUCES A DEFECT THAT ACTUALLY SHIPPED on 2026-09-10,
and asserts the fault suite fails. Controls 1 and 2 are the missing `finally`
that left SAIRNvet's backup silenced for a whole session -- the one the
logic-level suites were green through.

REFUSES A DIRTY TARGET, like every mutation probe here since 2026-09-09: the
bytes it would snapshot as "original" would not be the original, and the
restore would bake somebody else's edit in while reporting byte-identical.
"""
import hashlib
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()

# (name, target file, suite that must go red, exact text, replacement)
CONTROLS = [
    ("1. the hydration site loses its finally -- the defect that shipped",
     'sairnvet.html', 'tests/faults/sv_suppression_faults.js',
     "        svSyncSuppressed=true;\n        try{ st(key,local); }\n"
     "        finally{ svSyncSuppressed=false; }",
     "        svSyncSuppressed=true;\n        st(key,local);\n"
     "        svSyncSuppressed=false;"),
    ("2. svSeedStore loses its finally",
     'sairnvet.html', 'tests/faults/sv_suppression_faults.js',
     "  svSyncSuppressed = true;\n  try { return saver(rows); }\n"
     "  finally { svSyncSuppressed = false; }",
     "  svSyncSuppressed = true;\n  var _r = saver(rows);\n"
     "  svSyncSuppressed = false;\n  return _r;"),
    ("3. svSeedStore stops raising the flag at all, so a seed reaches the server",
     'sairnvet.html', 'tests/faults/sv_suppression_faults.js',
     "  svSyncSuppressed = true;\n  try { return saver(rows); }",
     "  svSyncSuppressed = false;\n  try { return saver(rows); }"),
    ("4. a refused vendor write stops reporting the refusal",
     'sairndental.html', 'tests/faults/dnt_vendor_write_faults.js',
     "    toast('NOT SAVED TO THE SERVER",
     "    toast('Saved. ('NOT SAVED TO THE SERVER"),
    ("5. a failed flag write reports success, so the guard records nothing",
     'sairndental.html', 'tests/faults/dnt_vendor_write_faults.js',
     "  catch(e){ try{ console.warn('SAIRNdental: could not record the unconfirmed-write '+",
     "  catch(e){ return true; } if(false){ try{ console.warn('X'+"),
]


def dirty(paths):
    r = subprocess.run(['git', 'status', '--porcelain', '--'] + list(paths),
                       cwd=ROOT, capture_output=True, text=True)
    return [l for l in (r.stdout or '').splitlines() if l.strip()]


def run(suite):
    return subprocess.run(['node', suite], cwd=ROOT, capture_output=True).returncode


def main():
    targets = sorted({c[1] for c in CONTROLS})
    already = dirty(targets)
    if already:
        print('SKIPPED: a target of this probe is already modified, so the bytes')
        print('it would snapshot as "original" are not the original and the')
        print('restore would bake them in. Nothing was verified. Tree:')
        for l in already:
            print('    %s' % l)
        return 3

    orig = {t: open(os.path.join(ROOT, t), 'rb').read() for t in targets}
    before = {t: hashlib.sha256(v).hexdigest() for t, v in orig.items()}
    results = []
    for suite in sorted({c[2] for c in CONTROLS}):
        results.append((suite, '0. green on the unmodified files',
                        'GREEN' if run(suite) == 0 else 'RED-BEFORE-MUTATION'))
    try:
        for name, target, suite, old, new in CONTROLS:
            src = orig[target]
            n = src.count(old.encode('utf-8'))
            if n != 1:
                results.append((suite, name, 'ANCHOR-%d' % n))
                continue
            open(os.path.join(ROOT, target), 'wb').write(
                src.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
            results.append((suite, name, 'BITES' if run(suite) != 0 else 'SILENT'))
            open(os.path.join(ROOT, target), 'wb').write(src)
    finally:
        # Restored even if the run dies mid-way. These are LIVE apps and one of
        # them has its schema provisioned.
        for t in targets:
            open(os.path.join(ROOT, t), 'wb').write(orig[t])

    last = None
    for suite, name, verdict in results:
        if suite != last:
            print('\n-- %s --' % suite)
            last = suite
        print('  %-8s %s' % (verdict, name))
    print('')
    ok = True
    for t in targets:
        after = hashlib.sha256(open(os.path.join(ROOT, t), 'rb').read()).hexdigest()
        ok = ok and after == before[t]
        print('%-22s restored byte-identical: %s  %s'
              % (t, after == before[t], before[t][:16]))
    bad = [n for _, n, v in results if v not in ('BITES', 'GREEN')]
    print('CONTROLS THAT DID NOT BITE:', bad if bad else 'none')
    return 1 if (bad or not ok) else 0


if __name__ == '__main__':
    sys.exit(main())
