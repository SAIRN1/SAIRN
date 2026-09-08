"""Mutation probe for tests/sd_timesheet_pay_est.js.

WHY IT EXISTS. The open-work row flagging `11fc0f30` for independent review
said that suite carried "18 assertions and three negative controls". The
assertions were on disk; **the negative controls were not** -- no probe file,
no mutation harness, nothing that had ever watched the suite go red. That is
the same gap this session closed in its own SAIRNdental suites earlier the same
day, and it is worth more here: four of this suite's strongest claims are
SOURCE assertions, and its own header records one already caught passing a
mutation that had removed the behaviour.

So this breaks stonedesk.html in nine specific ways -- one per defect the suite
claims to hold, including the one the review itself found -- asserts the suite
goes RED for every one, then restores the file and verifies it byte-identical
by sha256.

Run:  python tests/sd_timesheet_pay_est_probe.py
"""
import hashlib
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TARGET = 'stonedesk.html'
SUITE = os.path.join('tests', 'sd_timesheet_pay_est.js')

# (name, exact text to replace, replacement). A dead anchor is reported as
# ANCHOR-n and FAILS the run rather than skipping quietly.
MUTATIONS = [
    ("1. tsRate reads truthiness again, so a deliberate 0 stops being a rate",
     "    return (typeof r==='number'&&isFinite(r)&&r>=0)?r:null;",
     "    return r||null;"),
    ("2. tsRate accepts anything, so a string or NaN becomes a rate",
     "    return (typeof r==='number'&&isFinite(r)&&r>=0)?r:null;",
     "    return r===undefined?null:r;"),
    ("3. tsPay prices an unpriceable row at zero instead of refusing",
     "    return r===null?null:(x.hrs||0)*r;",
     "    return (x.hrs||0)*(r||0);"),
    ("4. the CSV writes a price for a row with no rate",
     "    return p===null?'':'$'+Math.round(p).toLocaleString();",
     "    return '$'+Math.round(p||0).toLocaleString();"),
    ("5. tsTotal stops distinguishing nothing-priced from priced-at-zero",
     "    return {sum:sum,priced:priced,unpriced:unpriced,total:priced?sum:null};",
     "    return {sum:sum,priced:priced,unpriced:unpriced,total:sum};"),
    ("6. the payroll KPI reads .sum again -- the defect the review found",
     'payEl.textContent=tsMoney(payTot.total)+(payTot.unpriced?" *":"");',
     'payEl.textContent=tsMoney(payTot.sum)+(payTot.unpriced?" *":"");'),
    ("7. the printed TOTALS row reads .sum again",
     '<td class=\\"amt\\">"+tsMoney(payT.total)+(payT.unpriced?" *":"")+"</td>',
     '<td class=\\"amt\\">"+tsMoney(payT.sum)+(payT.unpriced?" *":"")+"</td>'),
    ("8. sdTSLog defaults a blank rate to 28 again",
     '    var rate=rateRaw===""?NaN:parseFloat(rateRaw);\n    if(!isFinite(rate)||rate<0){',
     '    var rate=parseFloat(rateRaw)||28;\n    if(false){'),
    ("9. the printed page drops its partial-total disclosure",
     'if(payT.unpriced)w.document.write("<p style=\\"color:#92400e;font-size:11px\\">* Partial total"',
     'if(false)w.document.write("<p style=\\"color:#92400e;font-size:11px\\">* Partial total"'),
]


def main():
    path = os.path.join(ROOT, TARGET)
    orig = open(path, 'rb').read()
    before = hashlib.sha256(orig).hexdigest()

    baseline = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
    results = [('0. the suite is green on the unmodified file',
                'GREEN' if baseline.returncode == 0 else 'RED-BEFORE-MUTATION')]

    try:
        for name, old, new in MUTATIONS:
            n = orig.count(old.encode('utf-8'))
            if n != 1:
                results.append((name, 'ANCHOR-%d' % n))
                continue
            open(path, 'wb').write(orig.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
            r = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True)
            results.append((name, 'BITES' if r.returncode != 0 else 'SILENT'))
            open(path, 'wb').write(orig)
    finally:
        # Restored even if the run dies mid-way. A probe that leaves a mutated
        # 2 MB app on disk is worse than no probe.
        open(path, 'wb').write(orig)

    for name, verdict in results:
        print('  %-8s %s' % (verdict, name))
    print()
    after = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    print('%s restored byte-identical: %s  %s' % (TARGET, after == before, before[:16]))
    bad = [n for n, v in results if v not in ('BITES', 'GREEN')]
    print('PROBES THAT DID NOT BITE:', bad if bad else 'none')
    return 1 if (bad or after != before) else 0


if __name__ == '__main__':
    sys.exit(main())
