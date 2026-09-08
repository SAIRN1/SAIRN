"""Mutation probe for api/law-auth-custody-matter-attribution.test.js.

WHY IT EXISTS. The open-work row flagging this change for independent review
said the suite carried "11 assertions and five negative controls". The
assertions were on disk; **the negative controls were not** -- no probe file,
no harness, nothing that had ever watched the suite go red. That is the second
review row in a row to claim controls that do not exist, and both times writing
one found something.

Here it found that an assertion was PINNING THE DEFECT. It required
`e.matter_verified===undefined||e.matter_verified===null` -- the flattening of
"the check failed" into "the record predates the check" -- under the failure
message *"a not-checked record is not distinguished from a failed one"*. The
message named the flattening as the defect while the assertion required it, so
separating the two states turned the suite red with a message saying they had
not been separated.

Nine mutations across BOTH files the change touches, restored and sha256-
verified.

Run:  python tests/law_custody_attribution_probe.py
"""
import hashlib
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
SUITE = os.path.join('api', 'law-auth-custody-matter-attribution.test.js')

API = os.path.join('api', 'law-auth.js')
APP = 'sairnlaw.html'

MUTATIONS = [
    ("1. the verdict starts false, so an unfinished check accuses a real matter", API,
     "        matter_verified = 'unavailable';   // until a lookup actually answers",
     "        matter_verified = false;   // until a lookup actually answers"),
    ("2. a non-general id starts null again, colliding with 'general'", API,
     "        matter_verified = 'unavailable';   // until a lookup actually answers",
     "        matter_verified = null;   // until a lookup actually answers"),
    ("3. the lookup drops its licence scope -- another firm's matter would confirm", API,
     "          const mr = await fetch(rest('law_matters?license_hash=eq.' + enc(licHash) +\n"
     "            '&matter_id=eq.' + enc(matter_id) + '&select=matter_id&limit=1'), { headers });",
     "          const mr = await fetch(rest('law_matters?matter_id=eq.' + enc(matter_id) +\n"
     "            '&select=matter_id&limit=1'), { headers });"),
    ("4. 'general' is looked up too, so a non-matter gets a verdict", API,
     "      if (matter_id !== 'general') {\n        matter_verified = 'unavailable';",
     "      if (true) {\n        matter_verified = 'unavailable';"),
    ("5. a thrown lookup is recorded as a failed verification", API,
     "        } catch (e) { /* leaves 'unavailable' -- see above */ }",
     "        } catch (e) { matter_verified = false; }"),
    ("6. ai_list coerces the verdict, killing the distinction at the API boundary", API,
     "          matter_verified: e.detail ? e.detail.matter_verified : undefined,",
     "          matter_verified: (e.detail && e.detail.matter_verified) || false,"),
    ("7. the panel re-flattens a failed check into 'predates the check'", APP,
     "        } else if(e.matter_verified==='unavailable'||e.matter_verified===null){",
     "        } else if(false){"),
    ("8. the panel loses its unconfirmed marker entirely", APP,
     '&#9888; matter UNCONFIRMED</span>',
     '</span>'),
    ("9. the unconfirmed warning starts alleging fabrication", APP,
     "That can mean a matter created on a device that has not synced -- or an id that was never real.",
     "This matter was fabricated by the user."),
]


def main():
    targets = sorted({m[1] for m in MUTATIONS})
    orig, before = {}, {}
    for t in targets:
        orig[t] = open(os.path.join(ROOT, t), 'rb').read()
        before[t] = hashlib.sha256(orig[t]).hexdigest()

    baseline = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
    results = [('0. the suite is green on the unmodified files',
                'GREEN' if baseline.returncode == 0 else 'RED-BEFORE-MUTATION')]

    try:
        for name, target, old, new in MUTATIONS:
            src = orig[target]
            n = src.count(old.encode('utf-8'))
            if n != 1:
                results.append((name, 'ANCHOR-%d' % n))
                continue
            open(os.path.join(ROOT, target), 'wb').write(
                src.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
            r = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
            results.append((name, 'BITES' if r.returncode != 0 else 'SILENT'))
            open(os.path.join(ROOT, target), 'wb').write(src)
    finally:
        for t in targets:
            open(os.path.join(ROOT, t), 'wb').write(orig[t])

    for name, verdict in results:
        print('  %-8s %s' % (verdict, name))
    print()
    ok = True
    for t in targets:
        after = hashlib.sha256(open(os.path.join(ROOT, t), 'rb').read()).hexdigest()
        ok = ok and after == before[t]
        print('%-24s restored byte-identical: %s  %s' % (t, after == before[t], before[t][:16]))
    bad = [n for n, v in results if v not in ('BITES', 'GREEN')]
    print('PROBES THAT DID NOT BITE:', bad if bad else 'none')
    return 1 if (bad or not ok) else 0


if __name__ == '__main__':
    sys.exit(main())
