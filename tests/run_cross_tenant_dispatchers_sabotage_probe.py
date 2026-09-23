#!/usr/bin/env python
"""tests/run_cross_tenant_dispatchers_sabotage_probe.py

Run:  python tests/run_cross_tenant_dispatchers_sabotage_probe.py

Exit 0 every mutation was refused, 1 one was not, 2 COULD NOT RUN.

── WHY THIS FILE EXISTS ───────────────────────────────────────────────────────
The sabotage run behind api/sd-data-cross-tenant-dispatchers.test.js has been
PROSE ONLY, twice. `5a878e71` claimed "18 of 18 sabotages caught, api/sd-data.js
byte-identical after every one" with no runner in the commit, and
tests/cross_tenant_dispatchers_review_probe.py wrote that up as FINDING 3.
`3b4563d1` then claimed eleven line-targeted mutations, again with no runner:
that commit changed exactly one file, the suite itself. So an obligation asking
a reviewer to "RE-RUN THE CONTROL rather than trusting the summary" pointed at
something that was not on disk, and the second reviewer hit the same wall as
the first.

A sabotage claim nobody can re-run is the same shape as the coverage claims this
whole suite exists to replace: true when it was made, unfalsifiable afterwards,
and silently dead the day the anchor moves.

── WHY EVERY MUTATION IS LINE-TARGETED ────────────────────────────────────────
Not a preference. The canonical generic read line

    const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });

appears NINE times in api/sd-data.js, byte for byte. A text-replace anchor on
that string mutates whichever copy comes first and reports the resulting red
suite as proof of an arm that never ran. That has happened three times on this
file already (SF against BLD, dnt_settings across three call sites,
rf_company_programs). So each mutation here names the line it opens on, asserts
its anchor is present on THAT line before changing anything, and fails loudly on
a no-op.

── AND THE ASSERTION IS TWO-SIDED, WHICH IS THE PART THE PROSE NEVER HAD ──────
A mutation is only evidence if it lands where its label says. So each one
asserts BOTH:

  (a) every arm named for that branch FAILS, and
  (b) NO arm outside that branch fails.

(b) is what a wrong-site mutation cannot satisfy: mutating BLD while claiming SF
turns BLD's arms red, and this probe reports that as a MISLANDED mutation rather
than as a caught sabotage. A one-sided control cannot tell those apart, which is
exactly how the three near-misses got as far as they did.

── AND A SECOND KIND OF MUTATION, IN THE OPPOSITE DIRECTION ───────────────────
The filter mutations REMOVE a tenant clause. The gate tripwires ADD a session
check to a branch that has none. The GRD unit is configured `app: null` exactly
so no credential is invented for six branches that never ask for one -- and the
entire value of that choice is that the arms cannot survive a gate arriving.
Before this, the unit sent a signed X-SD-Auth header, so it would have stayed
green through precisely that change while still carrying a comment saying the
gate was absent. `app: null` reads like a disclosure either way; the difference
between a disclosure and a TRIPWIRE is whether anything actually goes red, and
that is what this section measures rather than asserts.

── NOTHING IN THE WORKING TREE IS MUTATED ─────────────────────────────────────
api/sd-data.js is never written. The handler, its _lib/_resources dependencies
and the suite are copied into a scratch sandbox once, and every mutation is
applied to the COPY. The working tree is verified byte-identical at the end
anyway, because "I did not intend to write it" is not a check.
"""

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVING = os.path.join(ROOT, 'api', 'sd-data.js')
SUITE = 'sd-data-cross-tenant-dispatchers.test.js'

# ── THE MUTATION TABLE ─────────────────────────────────────────────────────
# open_line  : the 1-indexed line the branch OPENS on, and `open_anchor` must
#              be on it. This is what pins a mutation to one dispatcher when
#              nine of them carry byte-identical query text.
# read_line  : the 1-indexed line carrying the tenant filter to remove.
# arms       : substrings of the arm names that MUST turn red. Every other arm
#              in the suite must stay green.
MUTATIONS = [
    ('LEG_RESOURCES', 11036, "LEG_RESOURCES[resource] && action === 'read'", 11037,
     ['leg_', 'LEG_RESOURCES [L-rev]']),
    ('SV_RESOURCES', 10355, "SV_RESOURCES[resource] && action === 'read'", 10356,
     ['sv_', 'SV_RESOURCES [L-rev]']),
    ('SB_RESOURCES', 10732, 'SB_RESOURCES[resource]', 10739,
     ['sb_', 'SB_RESOURCES [L-rev]']),
    ('SDN_RESOURCES', 10019, "SDN_RESOURCES[resource] && action === 'read'", 10021,
     ['sdn_', 'SDN_RESOURCES [L-rev]']),
    ('LAW_RESOURCES', 10911, "LAW_RESOURCES[resource] && action === 'read'", 10912,
     ['law_portalesign', 'law_portalmessages', 'law_timeentries', 'law_clecredits',
      'law_optx', 'law_pimedical', 'law_mattertasks', 'law_matterdocs',
      'law_mattermilestones', 'law_bankstatements', 'LAW_RESOURCES [L-rev]']),
    ('SF_RESOURCES', 10511, "SF_RESOURCES[resource] && action === 'read'", 10512,
     ['sf_', 'SF_RESOURCES [L-rev]']),
    ('SC_RESOURCES', 13052, 'if (isScResource) {', 13120,
     ['sc_', 'SC_RESOURCES [L-rev]']),
    ('BLD_RESOURCES', 10106, "BLD_RESOURCES[resource] && action === 'read'", 10107,
     ['bld_', 'BLD_RESOURCES [L-rev]']),
    ('rf_company_programs', 7955, "resource === 'rf_company_programs'", 7962,
     ['rf_company_programs']),
    ('rf_job_warranties', 7361, "resource === 'rf_job_warranties'", 7362,
     ['rf_job_warranties']),
    ('rf_prequal_documents', 6594, "resource === 'rf_prequal_documents'", 6595,
     ['rf_prequal_documents']),
    ('rf_safety_equipment', 6781, "resource === 'rf_safety_equipment'", 6782,
     ['rf_safety_equipment']),
    ('sen_visits', 4845, "resource === 'sen_visits' && action === 'read'", 4848,
     ['sen_visits']),
]

# Two shapes, because the filter is written two ways in this file. Form A is the
# single-line `...+ '&select=...'`; form B covers a continuation line and the SC
# branch's `+ scSoftFilter +`. Both erase the tenant clause and nothing else.
FORM_A = "?license_hash=eq.' + enc(licHash) + '&"
FORM_B = "?license_hash=eq.' + enc(licHash) +"


def die(msg):
    sys.stderr.write('COULD NOT RUN: %s\n' % msg)
    sys.exit(2)


def sha(path):
    return hashlib.sha256(io.open(path, 'rb').read()).hexdigest()


def run_suite(sandbox):
    """Return (ok_names, failed_names, tail). A suite that will not start at all
    is a COULD-NOT-RUN, never a caught sabotage."""
    p = subprocess.run([NODE, os.path.join(sandbox, SUITE)],
                       cwd=sandbox, capture_output=True, text=True)
    out = p.stdout or ''
    if 'passed,' not in out:
        return None, None, (out + (p.stderr or ''))[-1200:]
    ok, bad = [], []
    for line in out.split('\n'):
        s = line.strip()
        if s.startswith('ok   '):
            ok.append(s[5:].strip())
        elif s.startswith('FAIL '):
            bad.append(s[5:].strip())
    return ok, bad, out[-400:]


NODE = shutil.which('node')
if not NODE:
    die('node is not on PATH, so nothing here ran. This probe needs node to '
        'execute the suite; a static read cannot answer whether a mutation is '
        'caught.')
if not os.path.isfile(SERVING):
    die('api/sd-data.js not found at %s' % SERVING)

tree_before = sha(SERVING)
src_lines = io.open(SERVING, encoding='utf-8').read().split('\n')

# ── the sandbox: a copy, so the working tree is never the thing being broken ──
_root = tempfile.mkdtemp(prefix='xtenant-sabotage-')
sandbox = _root
try:
    # THE WHOLE api/ TREE, not a hand-picked subset. The first version copied
    # _lib and _resources and got 369 red arms on an UNMUTATED copy, because
    # sd-data.js also requires siblings directly (`./mech-auth`). A sandbox
    # missing one dependency reddens every arm, which is indistinguishable
    # from a mutation catching everything -- so the baseline gate above is the
    # thing that caught it, and it stays.
    sandbox = os.path.join(sandbox, 'api')
    shutil.copytree(os.path.join(ROOT, 'api'), sandbox,
                    ignore=shutil.ignore_patterns('*.test.js', '__pycache__'))
    shutil.copy(os.path.join(ROOT, 'api', SUITE), os.path.join(sandbox, SUITE))
    SAND_SERVING = os.path.join(sandbox, 'sd-data.js')

    print('=== BASELINE (unmutated copy) ===')
    base_ok, base_bad, tail = run_suite(sandbox)
    if base_ok is None:
        die('the suite did not run against an UNMUTATED copy, so no mutation '
            'result below would mean anything:\n' + tail)
    print('  %d passed, %d failed' % (len(base_ok), len(base_bad)))
    if base_bad:
        die('the baseline is not green (%d failing). A sabotage control on a '
            'red baseline cannot distinguish its own mutation from the '
            'pre-existing failure. Failing: %s'
            % (len(base_bad), ', '.join(base_bad[:5])))
    baseline = set(base_ok)

    failures = []
    print('\n=== %d LINE-TARGETED MUTATIONS ===' % len(MUTATIONS))
    for label, open_line, open_anchor, read_line, arms in MUTATIONS:
        # 1. the branch really opens where the table says
        if open_line - 1 >= len(src_lines) or open_anchor not in src_lines[open_line - 1]:
            failures.append('%s: ANCHOR MOVED -- line %d does not carry %r. The '
                            'mutation was NOT applied; this is a stale table, '
                            'not a caught sabotage.'
                            % (label, open_line, open_anchor))
            print('  MISS  %-22s anchor not on line %d' % (label, open_line))
            continue
        # 2. the read line really carries a tenant filter
        target = src_lines[read_line - 1]
        if FORM_A in target:
            mutated_line = target.replace(FORM_A, '?', 1)
        elif FORM_B in target:
            mutated_line = target.replace(FORM_B, "?' +", 1)
        else:
            failures.append('%s: no tenant filter on line %d -- %r. NO-OP '
                            'MUTATION, which is a loud error and not a pass.'
                            % (label, read_line, target.strip()[:90]))
            print('  MISS  %-22s no filter on line %d' % (label, read_line))
            continue
        if mutated_line == target:
            failures.append('%s: the replacement changed nothing on line %d'
                            % (label, read_line))
            continue

        new = list(src_lines)
        new[read_line - 1] = mutated_line
        changed = [i for i in range(len(new)) if new[i] != src_lines[i]]
        if changed != [read_line - 1]:
            failures.append('%s: the mutation touched %d lines, not 1'
                            % (label, len(changed)))
            continue
        io.open(SAND_SERVING, 'w', encoding='utf-8', newline='').write('\n'.join(new))

        ok, bad, tail = run_suite(sandbox)
        if ok is None:
            failures.append('%s: the suite did not run under this mutation, so '
                            'nothing was proven:\n%s' % (label, tail))
            print('  MISS  %-22s suite did not run' % label)
            io.open(SAND_SERVING, 'w', encoding='utf-8', newline='').write('\n'.join(src_lines))
            continue

        red = set(bad)
        expected_red = set(a for a in baseline
                           if any(k in a for k in arms) and '[L' in a)
        missed = sorted(a for a in expected_red if a not in red)
        # (b) -- a red arm that belongs to NO other branch's label is a mislanding
        strayed = sorted(a for a in red if a not in expected_red)

        if not expected_red:
            failures.append('%s: the arm filter matched NOTHING in the green '
                            'baseline, so this mutation asserts nothing.' % label)
            print('  MISS  %-22s arm filter matched no baseline arm' % label)
        elif missed:
            failures.append('%s: %d arm(s) the mutation should have turned red '
                            'stayed green: %s' % (label, len(missed), ', '.join(missed[:4])))
            print('  MISS  %-22s %d expected-red arm(s) stayed green'
                  % (label, len(missed)))
        elif strayed:
            failures.append('%s: MISLANDED -- %d arm(s) OUTSIDE this branch went '
                            'red: %s. A mutation that reddens another branch is '
                            'evidence about that branch, not this one.'
                            % (label, len(strayed), ', '.join(strayed[:4])))
            print('  MISS  %-22s MISLANDED, %d foreign arm(s) red'
                  % (label, len(strayed)))
        else:
            print('  ok    %-22s line %-6d %2d arm(s) red, 0 elsewhere'
                  % (label, read_line, len(red)))

        io.open(SAND_SERVING, 'w', encoding='utf-8', newline='').write('\n'.join(src_lines))
        if sha(SAND_SERVING) != sha(SERVING):
            failures.append('%s: the sandbox copy did not restore byte-identically'
                            % label)

    # ── THE SECOND KIND, AND IT MUTATES IN THE OPPOSITE DIRECTION ───────────
    # Everything above REMOVES a tenant filter and expects red. This ADDS a
    # session gate to a branch that has none, and expects red for a different
    # reason: the unit is configured `app: null` precisely so that no credential
    # is invented for a branch that never asks for one, and the whole value of
    # that choice is that the arms cannot survive a gate arriving.
    #
    # WHY IT NEEDS PROVING RATHER THAN STATING. `app: null` reads like a
    # disclosure either way. The difference between a disclosure and a TRIPWIRE
    # is whether anything actually goes red on the day the handler changes, and
    # the version of this unit that sent a token would have stayed green through
    # exactly that change while still carrying a comment saying the gate was
    # absent. So the claim is worth only as much as this section.
    print('\n=== GATE TRIPWIRES -- `app: null` units must NOT survive a gate ===')
    GATE = ("      { const _g = verifySessionToken(tokenFromRequest(req), licHash, "
            "'sairngrounds'); if (!_g) { res.status(403).json({ error: { code: "
            "'FORBIDDEN', message: 'gate arrived' } }); return; } }")
    TRIPWIRES = [
        # grd_boq_rates is the unit's FIRST member, so the once-per-unit
        # [L-rev] arm drives it too and must go red as well. Naming only the
        # [L] arm reported a correct result as a MISLANDING on the first run --
        # the two-sided assertion catching the expectation table rather than
        # the code, which is the direction it is supposed to fail in.
        ('grd_boq_rates', 3432, "resource === 'grd_boq_rates' && action === 'read'",
         ['grd_boq_rates [L]', 'NO session gate) [L-rev]']),
        ('grd_rounds', 3243, "resource === 'grd_rounds' && action === 'read'",
         ['grd_rounds [L]']),
    ]
    for label, open_line, open_anchor, arms in TRIPWIRES:
        if open_line - 1 >= len(src_lines) or open_anchor not in src_lines[open_line - 1]:
            failures.append('%s tripwire: ANCHOR MOVED -- line %d does not carry '
                            '%r, so no gate was inserted and nothing was proven.'
                            % (label, open_line, open_anchor))
            print('  MISS  %-22s anchor not on line %d' % (label, open_line))
            continue
        new = src_lines[:open_line] + [GATE] + src_lines[open_line:]
        io.open(SAND_SERVING, 'w', encoding='utf-8', newline='').write('\n'.join(new))
        ok, bad, tail = run_suite(sandbox)
        if ok is None:
            failures.append('%s tripwire: the suite did not run with the gate '
                            'inserted:\n%s' % (label, tail))
            print('  MISS  %-22s suite did not run' % label)
        else:
            red = set(bad)
            want = sorted(a for a in baseline if any(k in a for k in arms))
            missed = [a for a in want if a not in red]
            strayed = sorted(a for a in red if a not in want)
            if not want:
                failures.append('%s tripwire: matched no baseline arm' % label)
                print('  MISS  %-22s matched no baseline arm' % label)
            elif missed:
                failures.append('%s tripwire: a session gate arrived on this '
                                'branch and the arm STAYED GREEN: %s. The unit is '
                                'sending a credential the handler now demands, so '
                                'the gate landed unrecorded -- which is the exact '
                                'failure `app: null` exists to make impossible.'
                                % (label, ', '.join(missed)))
                print('  MISS  %-22s arm stayed green under a new gate' % label)
            elif strayed:
                failures.append('%s tripwire: %d arm(s) outside this branch also '
                                'went red: %s' % (label, len(strayed), ', '.join(strayed[:4])))
                print('  MISS  %-22s %d foreign arm(s) red' % (label, len(strayed)))
            else:
                print('  ok    %-22s line %-6d gate arrives -> %d arm(s) red, 0 '
                      'elsewhere' % (label, open_line, len(red)))
        io.open(SAND_SERVING, 'w', encoding='utf-8', newline='').write('\n'.join(src_lines))
finally:
    shutil.rmtree(_root, ignore_errors=True)

print('\n=== THE WORKING TREE ===')
same = sha(SERVING) == tree_before
print('  api/sd-data.js unchanged: %s' % same)
if not same:
    failures.append('api/sd-data.js in the WORKING TREE changed. Nothing here '
                    'should have written it.')

print('\n=== RESULT ===')
if failures:
    for f in failures:
        print('  FAIL  %s' % f)
    print('\n%d check(s) did not hold across %d filter mutations and %d gate '
          'tripwires.' % (len(failures), len(MUTATIONS), len(TRIPWIRES)))
    sys.exit(1)
print('  all %d filter mutations refused, each in the branch its label names and '
      'no other branch disturbed; both `app: null` gate tripwires fired.'
      % len(MUTATIONS))
sys.exit(0)
