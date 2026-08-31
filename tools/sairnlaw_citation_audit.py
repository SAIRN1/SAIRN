#!/usr/bin/env python
"""Are the SAIRNlaw deadline engine's rule CITATIONS still the right numbers?

READ-ONLY. No network, no writes. Exits 1 on a hard finding, 0 otherwise.

    python tools/sairnlaw_citation_audit.py
    python tools/sairnlaw_citation_audit.py --verbose

── WHY THIS EXISTS ────────────────────────────────────────────────────────
Idaho moved computation of time from Rule 6 to RULE 2.2 effective 1 July 2016.
"Idaho Rule 6" has pointed at nothing for a decade. Nothing in this repo would
have noticed, because a stale rule number is not a syntax error, not a failing
test, and not a wrong date -- it is a wrong CITATION on a right answer, which is
invisible until someone follows it.

Nebraska is the same shape twice over: its mail-extension rule was "Rule 6(e)",
then Sec. 6-1106(e) in 2008, and is Sec. 6-1106(c) since 2025; and Neb. Rev.
Stat. Sec. 25-1143, the old new-trial section, was repealed outright in 2000.

── WHAT THIS TOOL CAN AND CANNOT DO ───────────────────────────────────────
It CANNOT tell you a state renumbered. That needs a primary source and a human
or a fetch. What it CAN do is three things that are worth having every session:

  1. DORMANT STANDARDS -- a computation or service-extension standard that no
     seeded rule uses. Its citation has therefore never been exercised by a real
     computation and has usually never been re-read either.

  2. UNCORROBORATED CITATIONS -- a standard whose rule NUMBER appears nowhere in
     this repo except its own declaration line. Every well-sourced standard is
     quoted verbatim in a comment and again in its jurisdiction's gate document;
     one that is not has a number nobody has written down twice.

  3. STALE-NUMBER PROBES -- a maintained list of renumberings we KNOW about.
     Each is a regex plus the reason it is stale. A hit outside a line that is
     itself warning about the staleness is a finding.

  4. THE VERIFICATION LEDGER -- which standards have actually been checked
     against a primary source, and when. This is the part that matters most and
     the part a tool cannot compute: it is a hand-maintained table, and its job
     is to make "never checked" VISIBLE rather than silent. Add a row when you
     verify one; do not add a row for a standard you merely believe is fine.

── HOW TO EXTEND IT ───────────────────────────────────────────────────────
When a jurisdiction is seeded, add its computation standard to LEDGER with the
date it was read and the URL it was read from. When a renumbering is discovered,
add a STALE_PROBES entry so it can never quietly come back.
"""

import argparse
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ENGINE = os.path.join(ROOT, 'api', '_lib', 'deadline-engine.js')


# ── 3. Renumberings we know about ─────────────────────────────────────────
# (label, regex, why it is stale). Keep adding; never remove -- a probe that
# stops finding anything is the point, not a reason to delete it.
STALE_PROBES = [
    ('Idaho "Rule 6" / "I.R.C.P. 6"',
     r'Idaho[^.\n]{0,40}Rule\s*6\b|I\.R\.C\.P\.\s*6\b',
     '2.2',
     'Idaho restyled in 2016; computation moved from Rule 6 to Rule 2.2, '
     'effective 1 July 2016'),
    ('Nebraska "Rule 6(e)"',
     r'Neb[^.\n]{0,30}Rule\s*6\(e\)',
     '6-1106',
     'renumbered to Sec. 6-1106(e) in 2008 and to Sec. 6-1106(c) effective '
     '1 January 2025'),
    ('Nebraska Sec. 25-1143',
     r'\b25-1143\b',
     '25-1144.01',
     'repealed by Laws 2000, LB 921, Sec. 38; the new-trial motion is now '
     'Neb. Rev. Stat. Sec. 25-1144.01'),
    ('Florida "R. Jud. Admin." without "Gen. Prac."',
     r'Fla\.\s*R\.\s*Jud\.\s*Admin',
     'Gen. Prac',
     'renamed the Florida Rules of GENERAL PRACTICE AND Judicial '
     'Administration in 2021; Rule 2.514 kept its number, the set did not '
     'keep its name'),
    ('Florida "Rule 1.090"',
     r'Fla[^.\n]{0,30}\b1\.090\b',
     '2.514',
     'computation moved out of Fla. R. Civ. P. 1.090 to R. 2.514 in 2006'),
    ('California "rule 45" (pre-2007 Rules of Court)',
     r'Cal[^.\n]{0,30}R\.\s*Ct\.\s*45\b',
     '1.10',
     'the California Rules of Court were comprehensively renumbered effective '
     '1 January 2007; time for actions is now rule 1.10'),
]

# A line that is itself warning about a stale number is not a finding. These
# markers suppress a hit on that line.
WARNING_MARKERS = (
    'stale', 'renumber', 'repealed', 'no longer', 'pointed at nothing',
    'has pointed', 'moved from', 'trap', 'superseded', 'do not cite',
    'CITE ', 'was REPEALED', 'formerly', 'prior version',
)


# ── 4. The verification ledger ────────────────────────────────────────────
# standard key -> (date the rule NUMBER was read on a primary source, source).
# ONLY add a row you actually verified. An absent row means "never checked",
# which is exactly what this table exists to show.
LEDGER = {
    'id_ircp_2_2':   ('2026-08-30', 'isc.idaho.gov/rules-procedure/ircp'),
    'ne_25_2221':    ('2026-08-30', 'nebraskalegislature.gov statute 25-2221'),
    'ms_r_civ_p_6':  ('2026-08-30', 'courts.ms.gov 2026-07-01 MRCP PDF'),
    'nm_1_006':      ('2026-08-30', 'nmonesource.com NMRA Rule Set 1 PDF'),
    'ks_60_206':     ('2026-08-30', 'ksrevisor.gov ch60 060_002_0006'),
    'pa_rja_107':    ('2026-08-30', '201 Pa. Code Ch. 1 Rule 107, pacodeandbulletin.gov'),
    'ca_crc_1_10':   ('2026-08-30', 'courts.ca.gov rule1_10 -- "Rule 1.10. Time for actions"'),
    'nv_nrcp_6':     ('2026-08-30', 'leg.state.nv.us/courtrules/NRCP.html -- '
                                    'Rule 6, "Computing and Extending Time"'),
    'fl_rgpja_2514': ('2026-08-31', 'read VERBATIM from the 1 July 2026 edition, '
                                    'floridabar.org, 259pp -- 2.514 retained, set name current'),
    'hi_hrcp_6':     ('2026-08-31', 'courts.state.hi.us hrcp_ada.htm -- Rule 6, and 6(a) names '
                                    'HRS Sec. 8-1 as the holiday referent by number'),
    'va_code_1_210': ('2026-08-31', 'law.lis.virginia.gov -- "Sec. 1-210. Computation of time"'),
    'ny_gcl_20':     ('2026-08-31', 'nysenate.gov GCN ch. 22 art. 2 Sec. 20, "Day, computation" '
                                    '-- note the law code is GCN, not CNS'),
    'illinois_5ilcs70_111':
                     ('2026-08-31', 'ilga.gov fulltext DocName=000500700K1.11 -- "Sec. 1.11", '
                                    'text matches what the standard models'),
    'ca_ccp_12_12a': ('2026-08-31', 'leginfo.legislature.ca.gov CCP section 12 resolves; SECTION '
                                    'NUMBER confirmed from the page title, body not extracted'),
    'ga_ocga_1_3_1_d3':
                     ('2026-08-31', 'law.justia.com MIRROR -- subsection (d)(3) "Computation of '
                                    'time" confirmed. NOT the official publisher: the OCGA is '
                                    'published by LexisNexis, so this row is weaker than the rest'),
}

# Standards someone TRIED to verify and could not reach. Recorded so the next
# session does not walk the same dead ends. Not a finding -- an absence of one.
ATTEMPTED_AND_UNREACHED = {
    'or_orcp_10': ('2026-08-31',
                   'courts.oregon.gov/programs/utcr/Documents/2026_ORCP.pdf and '
                   '/rules/orcp/Documents/ORCP_2026.pdf both 404; '
                   'oregonlegislature.gov/bills_laws/Pages/ORCP.aspx loads but carries no rule '
                   'text. Oregon puts computation at ORCP 10 rather than 6, which is exactly the '
                   'shape most likely to be mis-cited, so this one is worth finishing.'),
    'ct_pb_63_2': ('2026-08-31',
                   'jud.ct.gov/pb.htm is an index page and does not carry Sec. 63-2 inline. '
                   'LOWEST PRIORITY of the unchecked set: Connecticut is held out of the seed by '
                   'its own _hold_reason and never computes, so a stale citation there cannot '
                   'reach an answer.'),
}


def read(path):
    with io.open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def standard_keys(src, varname):
    i = src.index('var %s = {' % varname)
    depth, j = 0, i + len('var %s = ' % varname)
    while True:
        if src[j] == '{':
            depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0:
                break
        j += 1
    body = src[i:j]
    out = {}
    for m in re.finditer(r'^  ([a-z0-9_]+):\s*\{(.{0,400}?)label:\s*\'([^\']+)\'',
                         body, re.M | re.S):
        out[m.group(1)] = m.group(3)
    return out


def repo_files():
    out = []
    for pat in ('**/*.js', '**/*.json', '**/*.md', '**/*.py', '**/*.sql'):
        for p in glob.glob(os.path.join(ROOT, pat), recursive=True):
            rel = os.path.relpath(p, ROOT).replace('\\', '/')
            if rel.startswith(('node_modules/', '.git/', 'archive/')):
                continue
            # This file is the warning; scanning it finds its own probes.
            if rel == 'tools/sairnlaw_citation_audit.py':
                continue
            out.append((rel, p))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    src = read(ENGINE)
    comp = standard_keys(src, 'COMPUTATION_STANDARDS')
    ext = standard_keys(src, 'SERVICE_EXTENSION_STANDARDS')

    comp_used, ext_used = set(), set()
    for f in glob.glob(os.path.join(ROOT, 'sql', 'sairnlaw_deadline_seed_*.json')):
        with io.open(f, encoding='utf-8') as fh:
            d = json.load(fh)
        for r in d.get('rules', []):
            if r.get('computation'):
                comp_used.add(r['computation'])
            se = r.get('service_extension') or {}
            if se.get('standard'):
                ext_used.add(se['standard'])

    findings = 0
    print('SAIRNlaw citation audit -- %d computation standards, %d service-extension '
          'standards' % (len(comp), len(ext)))

    # ── 1. Dormant ────────────────────────────────────────────────────────
    print('\n== 1. DORMANT STANDARDS (declared, used by no seeded rule)')
    dormant = sorted((comp.keys() - comp_used) | (ext.keys() - ext_used))
    if not dormant:
        print('   none')
    for k in dormant:
        print('   %-22s %s' % (k, comp.get(k) or ext.get(k)))
    if dormant:
        print('   NOT AN ERROR. A dormant standard cannot compute a wrong date, because')
        print('   nothing calls it. It is listed because its citation has never been')
        print('   exercised, and whoever seeds that domain will inherit it untested.')

    # ── 2. Uncorroborated ─────────────────────────────────────────────────
    files = repo_files()
    blob = {}
    for rel, p in files:
        blob[rel] = read(p)
    print('\n== 2. UNCORROBORATED CITATIONS (rule number appears only in its own declaration)')
    uncorr = []
    for k, label in sorted(list(comp.items()) + list(ext.items())):
        nums = re.findall(r'\d+[\w.\-]*', label)
        if not nums:
            continue
        needle = nums[-1]
        hits = sum(t.count(needle) for t in blob.values())
        if hits <= 1:
            uncorr.append((k, label, needle, hits))
    if not uncorr:
        print('   none')
    for k, label, needle, hits in uncorr:
        print('   %-22s %-34s (number %r appears %d time)' % (k, label, needle, hits))

    # ── 3. Stale-number probes ────────────────────────────────────────────
    print('\n== 3. STALE-NUMBER PROBES (%d maintained)' % len(STALE_PROBES))
    for label, rx, replacement, why in STALE_PROBES:
        cre = re.compile(rx, re.I)
        real = []
        for rel, t in blob.items():
            lines = t.split('\n')
            for m in cre.finditer(t):
                line_no = t[:m.start()].count('\n') + 1
                # A WINDOW, not a line: prose that explains a renumbering
                # routinely spans a sentence break.
                lo = max(0, line_no - 3)
                window = '\n'.join(lines[lo:line_no + 2]).lower()
                # Primary suppressor: the REPLACEMENT citation is named nearby,
                # so this mention is explaining the change, not relying on it.
                if replacement.lower() in window:
                    continue
                if any(w.lower() in window for w in WARNING_MARKERS):
                    continue
                real.append((rel, line_no, lines[line_no - 1].strip()[:100]))
        if real:
            findings += len(real)
            print('   ⚠ %s -- %d unexplained hit(s)' % (label, len(real)))
            print('     why stale: %s' % why)
            for rel, n, line in real[:5]:
                print('     %s:%d  %s' % (rel, n, line))
        elif args.verbose:
            print('   ok %s -- no unexplained hits' % label)
    if not args.verbose:
        print('   (clean probes hidden; --verbose to list them)')

    # ── 4. Ledger ─────────────────────────────────────────────────────────
    print('\n== 4. VERIFICATION LEDGER -- rule NUMBER read on a primary source')
    checked = sorted(k for k in comp if k in LEDGER)
    unchecked = sorted(k for k in comp if k not in LEDGER)
    print('   verified: %d of %d computation standards' % (len(checked), len(comp)))
    for k in checked:
        when, where = LEDGER[k]
        print('     %-16s %s  %s' % (k, when, where))
    if ATTEMPTED_AND_UNREACHED:
        print('   TRIED AND COULD NOT REACH (%d) -- dead ends already walked, so nobody '
              'walks them twice:' % len(ATTEMPTED_AND_UNREACHED))
        for k in sorted(ATTEMPTED_AND_UNREACHED):
            when, why = ATTEMPTED_AND_UNREACHED[k]
            print('     %-16s %s  %s' % (k, when, why))
    print('   NEVER CHECKED (%d) -- this is a statement about our records, not a '
          'claim that any of them is wrong:' % len(unchecked))
    for i in range(0, len(unchecked), 4):
        print('     ' + '  '.join('%-20s' % k for k in unchecked[i:i + 4]))

    print('\n%s' % ('FINDINGS: %d' % findings if findings else 'NO HARD FINDINGS'))
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
