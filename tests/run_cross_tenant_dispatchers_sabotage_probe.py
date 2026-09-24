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
# opener : a string that appears EXACTLY ONCE in api/sd-data.js and identifies
#          this branch. Uniqueness is asserted, not assumed -- it is what pins
#          a mutation to one dispatcher when nine of them carry byte-identical
#          query text.
# arms   : substrings of the arm names that MUST turn red. Every other arm in
#          the suite must stay green.
#
# ── LINE NUMBERS WERE THE FIRST SPELLING AND THEY LASTED ABOUT AN HOUR ──────
# The table carried `open_line` and `read_line` as 1-indexed literals. Three
# other sessions were editing api/sd-data.js the same afternoon, and after one
# rebase EIGHT of the thirteen reported ANCHOR MOVED. The guard behaved
# correctly -- it refused rather than mutating whatever now sits on line 11036
# -- but a control that goes red on a green tree every time somebody else
# commits is a control people learn to ignore, which is the slower version of
# the failure this file exists to prevent.
#
# SO THE BRANCH IS LOCATED BY SEARCH AND THE READ LINE IS DERIVED FROM IT: the
# first tenant filter at or below the opener, within a bounded window. That
# keeps the property line-targeting was FOR -- one named branch, never the
# byte-identical copy 900 lines away -- and drops the part that rots. The
# located line number is printed on every run so it stays checkable.
MUTATIONS = [
    ('LEG_RESOURCES', "if (LEG_RESOURCES[resource] && action === 'read') {",
     ['leg_', 'LEG_RESOURCES [L-rev]']),
    ('SV_RESOURCES', "if (SV_RESOURCES[resource] && action === 'read') {",
     ['sv_', 'SV_RESOURCES [L-rev]']),
    # The read branch's opener is the WHOLE condition: `SB_RESOURCES[resource]`
    # alone also matches `const idCol = SB_RESOURCES[resource];` in the write
    # branch, and the uniqueness check refused it rather than guessing.
    ('SB_RESOURCES', 'if (SB_RESOURCES[resource]) {',
     ['sb_', 'SB_RESOURCES [L-rev]']),
    ('SDN_RESOURCES', "if (SDN_RESOURCES[resource] && action === 'read') {",
     ['sdn_', 'SDN_RESOURCES [L-rev]']),
    ('LAW_RESOURCES', "if (LAW_RESOURCES[resource] && action === 'read') {",
     ['law_portalesign', 'law_portalmessages', 'law_timeentries', 'law_clecredits',
      'law_optx', 'law_pimedical', 'law_mattertasks', 'law_matterdocs',
      'law_mattermilestones', 'law_bankstatements', 'LAW_RESOURCES [L-rev]']),
    ('SF_RESOURCES', "if (SF_RESOURCES[resource] && action === 'read') {",
     ['sf_', 'SF_RESOURCES [L-rev]']),
    # ── THE FOURTH ELEMENT IS A READ MARKER, AND SC IS WHY IT EXISTS ──────
    # "the first tenant filter below the opener" was right when written and
    # stopped being right silently. A `tombstones` action was added to this
    # branch on 2026-09-23 with its own license_hash-filtered query, so the
    # FIRST filter below `if (isScResource) {` is now tombstones' at +81 and
    # the generic list read is at +103 -- past READ_WINDOW as well as past the
    # tombstones line. The control mutated a query no isolation arm drives,
    # reported 24 expected-red arms stayed green, and READ AS IF THE ARMS WERE
    # BROKEN. They are not: mutating the real read at +103 by hand turns
    # exactly those 24 red. A control that is looking at the wrong line does
    # not fail quietly here -- it fails LOUDLY about the wrong thing, which is
    # the failure mode this file's own header warns about.
    #
    # The marker is `scSoftFilter`, which appears on the generic read and on
    # no other query in the branch. A marker that matches nothing is a
    # COULD-NOT-RUN, never a fall back to proximity: falling back is how this
    # got here.
    ('SC_RESOURCES', 'if (isScResource) {',
     ['sc_', 'SC_RESOURCES [L-rev]'], 'scSoftFilter'),
    ('BLD_RESOURCES', "if (BLD_RESOURCES[resource] && action === 'read') {",
     ['bld_', 'BLD_RESOURCES [L-rev]']),
    # Each rf_ branch below names its ACTION as well as its resource: the bare
    # `resource === 'x'` form matches the read, the write and (for three of
    # them) a third verb, so it cannot say which branch a mutation would hit.
    ('rf_company_programs',
     "if (resource === 'rf_company_programs' && action === 'read') {",
     ['rf_company_programs']),
    ('rf_job_warranties',
     "if (resource === 'rf_job_warranties' && action === 'read') {",
     ['rf_job_warranties']),
    ('rf_prequal_documents',
     "if (resource === 'rf_prequal_documents' && (action === 'read' || action === 'readiness')) {",
     ['rf_prequal_documents']),
    ('rf_safety_equipment',
     "if (resource === 'rf_safety_equipment' && (action === 'read' || action === 'board')) {",
     ['rf_safety_equipment']),
    ('sen_visits', "if (resource === 'sen_visits' && action === 'read') {",
     ['sen_visits']),
    # TWO MORE, 2026-09-23, added with the units they cover rather than after:
    # sd_sms_log and sd_email_threats joined SD_LOCAL_RESOURCES and sd_crm got
    # its own bespoke unit, all three on the same day their register rows read
    # A. A unit added without a mutation is a unit nobody has tried to break.
    ('SD_LOCAL_RESOURCES', "if (SD_LOCAL_RESOURCES[resource] && action === 'read') {",
     ['sd_aiquotes', 'sd_fin_jobs', 'sd_invoices', 'sd_negotiated_prices',
      'sd_order_history', 'sd_pricing_rules', 'sd_exec_msgs', 'sd_sms_log',
      'sd_email_threats', 'SD_LOCAL_RESOURCES [L-rev]']),
    ('sd_crm', "if (resource === 'sd_crm' && action === 'read') {",
     ['sd_crm']),
]

# ── WHAT IS NOT MUTATED, SAID HERE RATHER THAN LEFT TO LOOK COVERED ─────────
# Fifteen branches are driven above. The suite's other units are NOT: DNT, SD_HR,
# GRD, rf_entities, the six RF bespoke branches, the four SEN units and
# law_clients. Each of those still has [L]/[W] arms in the suite -- they are
# tested -- but nothing here proves those arms would go red if their tenant
# filter were removed. That is the same "sampled, not exhaustive" disclosure
# hank made for SF, applied to this file's own coverage, and it is the honest
# reading of the RESULT line at the bottom.


# Two shapes, because the filter is written two ways in this file. Form A is the
# single-line `...+ '&select=...'`; form B covers a continuation line and the SC
# branch's `+ scSoftFilter +`. Both erase the tenant clause and nothing else.
FORM_A = "?license_hash=eq.' + enc(licHash) + '&"
FORM_B = "?license_hash=eq.' + enc(licHash) +"


# How far below a branch's opener its tenant filter may sit. SC_RESOURCES is
# the widest real gap and IT HAS MOVED: the comment here said 68 lines, which
# was true when it was written. Measured 2026-09-24 it is 103 -- the KX
# accumulator AND a `tombstones` action now sit between the opener and the
# generic list read -- so 90 could no longer reach it at all. 160 covers the
# current worst case with room and is still far short of the next dispatcher.
#
# THE NUMBER IS MEASURED AND PRINTED, not asserted: a window is a guess about
# somebody else's file and the only honest version of it says when it was last
# checked against that file. Raising it is not the real fix either -- see the
# read marker on SC_RESOURCES for that.
READ_WINDOW = 160


def locate_opener(lines, anchor):
    """The 1-indexed line carrying `anchor`, or None unless it matches once."""
    hits = [i + 1 for i, l in enumerate(lines) if anchor in l]
    return hits[0] if len(hits) == 1 else None


def locate_read(lines, open_line, marker=None):
    """The tenant filter this branch's READ uses, within READ_WINDOW.

    WITH A MARKER the line must carry it as well as a filter form, so a branch
    with several license_hash-filtered queries says WHICH one is the read
    rather than taking whichever comes first. Without one the behaviour is
    unchanged: the first filter below the opener.

    A MARKER THAT MATCHES NOTHING RETURNS None and the caller reports a MISS.
    It does NOT fall back to proximity -- falling back is exactly how the SC
    row came to be mutating a `tombstones` query for a day without anybody
    being able to tell from the output.
    """
    for i in range(open_line - 1, min(open_line - 1 + READ_WINDOW, len(lines))):
        if FORM_A in lines[i] or FORM_B in lines[i]:
            if marker and marker not in lines[i]:
                continue
            return i + 1
    return None


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
    for row in MUTATIONS:
        label, open_anchor, arms = row[0], row[1], row[2]
        read_marker = row[3] if len(row) > 3 else None
        # 1. the opener must identify EXACTLY ONE place in the file
        open_line = locate_opener(src_lines, open_anchor)
        if open_line is None:
            hits = sum(1 for l in src_lines if open_anchor in l)
            failures.append('%s: the opener %r matches %d lines in api/sd-data.js, '
                            'not 1. Zero means it was reworded; more than one '
                            'means this mutation cannot say WHICH branch it '
                            'would hit. Either way nothing was mutated -- a '
                            'stale table, not a caught sabotage.'
                            % (label, open_anchor, hits))
            print('  MISS  %-22s opener matches %d lines, not 1' % (label, hits))
            continue
        # 2. the read line is DERIVED from the opener, not typed
        read_line = locate_read(src_lines, open_line, read_marker)
        if read_line is None:
            failures.append('%s: no tenant filter%s within %d lines below the '
                            'opener at %d. The branch was restructured, its '
                            'filter is written in a third shape this probe does '
                            'not know, or the read marker no longer appears on '
                            'the read. Nothing was mutated.'
                            % (label, (' carrying %r' % read_marker) if read_marker else '',
                               READ_WINDOW, open_line))
            print('  MISS  %-22s no%s filter under opener at %d'
                  % (label, (' %r' % read_marker) if read_marker else '', open_line))
            continue
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
        ('grd_boq_rates',
         "if (resource === 'grd_boq_rates' && action === 'read') {",
         ['grd_boq_rates [L]', 'NO session gate) [L-rev]']),
        ('grd_rounds', "if (resource === 'grd_rounds' && action === 'read') {",
         ['grd_rounds [L]']),
    ]
    for label, open_anchor, arms in TRIPWIRES:
        open_line = locate_opener(src_lines, open_anchor)
        if open_line is None:
            hits = sum(1 for l in src_lines if open_anchor in l)
            failures.append('%s tripwire: the opener %r matches %d lines, not 1, '
                            'so no gate was inserted and nothing was proven.'
                            % (label, open_anchor, hits))
            print('  MISS  %-22s opener matches %d lines, not 1' % (label, hits))
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
