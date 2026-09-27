"""tools/role_gate_negative_coverage.py -- which role gates would survive being
deleted, because no test ever drives them with a role they exclude?

    python tools/role_gate_negative_coverage.py                    # the SCREEN
    python tools/role_gate_negative_coverage.py --list
    python tools/role_gate_negative_coverage.py --ablate alf_facility   # the PROOF
    python tools/role_gate_negative_coverage.py --baseline   # after a real change

── THE DEFECT THIS EXISTS FOR ──────────────────────────────────────────────
api/sd-data.js's `alf_family_contacts` read had NO role gate at all until
2026-09-26: any authenticated SAIRNcare employee of any role could list every
family contact on the licence with phone, email and the full medication-consent
trail. Its suite, api/sd-data-family-contacts.test.js, was EIGHTEEN GREEN ARMS at
the time, and the reason none of them saw it is one line:

    verifySessionToken: function () { return { employee_id: 'owner-1',
                                               role: opts.role || 'owner' }; }

**EVERY ARM RAN AS `owner`.** The role was a parameter the harness defaulted and
no arm ever varied, so a completely ABSENT gate and a correct one produce
identical output. This tool asks the question those eighteen arms could not:
**if the gate were deleted, would anything go red?**

── WHAT IT MEASURES, AND WHY IT IS NOT "DO THE TESTS MENTION A ROLE" ───────
For each resource branch in api/sd-data.js that tests a role set:

  1. the ALLOWED roles, resolved from the `roleSet({...})` declaration itself --
     not from a list here, which would be a second copy of a fact the file owns;
  2. the EXCLUDED roles, being every role any set declares minus those;
  3. every (resource, role) pair the test suites actually DRIVE.

A gate is reported when a suite drives the resource but NEVER with an excluded
role. That is strictly stronger than "the suite mentions a role": a suite can pass
`role: 'owner'` on every arm, mention FORBIDDEN in a comment, and still be unable
to detect the gate's removal.

── WHAT IT CANNOT DO, AND THE FIRST ONE BIT ME ─────────────────────────────
IT CANNOT TELL A SUITE THAT DRIVES A RESOURCE FROM ONE THAT MENTIONS IT. The
first version matched any quoted lowercase string in a test file, so a resource
named in a COMMENT counted as exercised -- that reported 16 gates instead of 11,
and five of those were mentions. Only a `resource:` or `resource ===` position
counts now, which is the opposite error: a suite driving a resource through a
variable is invisible and its gate will be reported as uncovered. An over-report
is the safe direction here (it asks for an arm that already exists), and it is
stated rather than left for a reader to discover.

IT ALSO CANNOT SEE role gates outside api/sd-data.js -- api/*-auth.js files carry
their own, and this tool says nothing about them -- and it cannot judge whether a
gate is CORRECT. A gate excluding the wrong roles passes here as long as somebody
tests the exclusion it does implement.

── THE DEFAULT PASS IS A SCREEN; --ablate IS THE PROOF ─────────────────────
Three static rules were tried for step 3 and ALL THREE WERE WRONG -- see driven().
The screen over-reports on purpose. `--ablate <resource>` deletes that gate, runs
all 400 suites, and reports CAUGHT or SILENT: the property itself rather than a
pattern correlated with it. Settle any individual gate that way before believing
the screen about it, and never lower the pin on the strength of the screen alone.

A RATCHET, pinned to docs/role-gate-negative-coverage.json. The honest state is 12
of 31 by the screen and a check that simply failed would sit permanently red. An absent,
unparseable or `uncovered`-less pin is exit 2 COULD NOT TELL, never 0 -- and so is
finding zero role gates at all, because the gate shape moving must not read as
"everything is covered".
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD = os.path.join(REPO, 'api', 'sd-data.js')
PIN = os.path.join(REPO, 'docs', 'role-gate-negative-coverage.json')

# ── A BRANCH ENDS WHERE THE NEXT ONE BEGINS, NOT AT A CHARACTER COUNT ───────
# THIS WAS `BRANCH_WINDOW = 3000` AND THE PROBE CAUGHT IT. A fixed window from
# `resource === 'x'` reaches into the NEXT branch and swallows ITS role gate, so a
# resource gated on ALF_MANAGEMENT_ROLES was reported as gated on
# `ALF_CARE_ROLES,ALF_MANAGEMENT_ROLES`. Union the two members and the ALLOWED set
# becomes every role, the EXCLUDED set becomes empty, and no test can ever be
# found driving an excluded role -- so the gate is reported uncovered NO MATTER
# WHAT ANY SUITE DOES. An arm that drove it correctly still failed.
#
# It is the same defect as the magic 4200-char window in
# tests/roofing_claim_gate_single_source.js, fixed the same way and for the same
# reason: a fixed length is a guess about a subject whose extent is knowable.
BRANCH_MARK = re.compile(r"resource === '([a-z0-9_]+)'")


class CouldNotTell(Exception):
    pass


def _read(path, what):
    if not os.path.isfile(path):
        raise CouldNotTell('%s does not exist, so %s could not be read'
                           % (os.path.relpath(path, REPO), what))
    return io.open(path, encoding='utf-8', errors='replace').read()


def role_sets(src):
    """{SET_NAME: {member roles}} from the roleSet() declarations themselves."""
    out = {}
    for m in re.finditer(r'const\s+([A-Z][A-Z0-9_]*ROLES)\s*=\s*roleSet\(\{([^}]*)\}\)', src):
        out[m.group(1)] = set(re.findall(r'([a-z_][a-z0-9_]*)\s*:\s*true', m.group(2)))
    if not out:
        raise CouldNotTell('no roleSet({...}) declaration matched in api/sd-data.js '
                           '-- the declaration shape moved and NOTHING was resolved. '
                           'This is not "no role sets".')
    return out


def gated_branches(src):
    """{resource: {role set names its branch tests}}.

    Each branch runs from its own `resource === '...'` to the NEXT one. See
    BRANCH_MARK: a fixed-length window swallowed the following branch's gate and
    made the resource unfalsifiable.
    """
    marks = [(m.start(), m.group(1)) for m in BRANCH_MARK.finditer(src)]
    out = {}
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        for g in re.finditer(r'!\s*([A-Z][A-Z0-9_]*ROLES)\s*\[\s*session\.role\s*\]',
                             src[pos:end]):
            out.setdefault(name, set()).add(g.group(1))
    if not out:
        raise CouldNotTell('no resource branch tested a role set -- the gate shape '
                           'moved and NOTHING was measured. This is not '
                           '"no role gates".')
    return out


def suite_files():
    out = []
    for pat in (('api', '*.test.js'), ('api', '_lib', '*.test.js'), ('tests', '*.js')):
        d = os.path.join(REPO, *pat[:-1])
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if n.endswith('.test.js') or (pat[0] == 'tests' and n.endswith('.js')):
                out.append(os.path.join(d, n))
    if not out:
        raise CouldNotTell('no test files found under api/ or tests/')
    return out


# A suite ASSERTS a role refusal. Required alongside a bare role literal -- see
# driven() for why a literal alone is not enough.
ROLE_REFUSAL = re.compile(r"""FORBIDDEN|NOT_AUTHORIS|NOT_AUTHORIZ|"""
                          r"""status(?:Code)?\s*,\s*403|403\s*,""")


def driven(all_roles):
    """{resource: {roles any suite drives it with}}.

    ── A ROLE PASSED AS A VARIABLE WAS INVISIBLE, AND THE FIX HAD TO NOT BE A
    ── LOOSENING (2026-09-27) ────────────────────────────────────────────────
    The first version matched only `role: 'x'` and `tokenFor('x')`. Real arms are
    written as a loop over a declared list:

        const ALF_NON_MGMT = ['nursing', 'med_aide', 'caregiver', 'activities'];
        for (const role of ALF_NON_MGMT) { ... call(hash, emp, role, ...) ... }

    There is no `role: 'nursing'` anywhere in that, so four arms that DO drive the
    excluded roles -- and that fail when the gate is deleted, proven by ablation --
    left the resource reading `driven-as=owner`. The tool would have kept demanding
    an arm that already existed.

    A BARE QUOTED ROLE ANYWHERE IN THE FILE WOULD FIX IT AND BREAK THE TOOL: it is
    the same over-crediting that made the first resource matcher report 16 for 11,
    and here it is worse, because crediting a comment turns a real gap into a pass.
    So a bare literal counts ONLY IN A FILE THAT ALSO ASSERTS A ROLE REFUSAL --
    FORBIDDEN, NOT_AUTHORIS(Z)ED or a 403. A suite that names a role and never
    asserts a refusal is exactly the family-contact shape and must keep failing.

    ── AND THEN TWO ATTEMPTS TO FIX THAT WERE BOTH WRONG, IN OPPOSITE
    ── DIRECTIONS, WHICH IS WHY THIS IS A SCREEN AND NOT A VERDICT ───────────
    ATTEMPT 1, TOO LOOSE: admit a bare literal in any file that ALSO asserts a
    refusal anywhere. It moved the figure 12 -> 7, and I ablated the five it newly
    credited instead of trusting it. TWO WERE STILL SILENT -- deleting sd_customers'
    and alf_mar's gates failed NOTHING across 400 suites. A file can name
    `caregiver` and assert a 403 about two unrelated resources, which is what those
    suites do. It would have absolved two real gaps.

    ATTEMPT 2, TOO STRICT: require the role and the resource in the same test ARM.
    Uncovered fell to 1 and NOT DRIVEN jumped 15 -> 29, because the resource is
    usually named in a helper, a UNITS table or a loop OUTSIDE the arm. It stopped
    seeing the drives at all.

    SO THE STATIC RULE IS THE ORIGINAL STRICT ONE AND IT IS A SCREEN, NOT A
    VERDICT. `role: 'x'` or `tokenFor('x')` only. It OVER-reports, deliberately:
    a suite driving an excluded role through a variable reads as uncovered, which
    asks for an arm that may already exist. That is the safe direction, and the
    honest resolution is that the ONLY sound measurement here is ABLATION -- delete
    the gate and see whether anything fails -- which `--ablate` now does on demand.
    Every reduction in the pinned figure should be an ablation-CONFIRMED one.
    """
    out = {}
    for p in suite_files():
        s = io.open(p, encoding='utf-8', errors='replace').read()
        if 'role' not in s:
            continue
        roles = set()
        for r in all_roles:
            if re.search(r"""role\s*[:=]\s*['"]%s['"]""" % re.escape(r), s) \
               or re.search(r"""(?:tokenFor|token|session|sessionFor|as)\(\s*['"]%s['"]"""
                            % re.escape(r), s):
                roles.add(r)
        if not roles:
            continue
        # STRICT: a `resource:` / `resource ===` position only. See the docstring --
        # the loose version counted mentions and over-reported by five.
        for res in set(re.findall(r"""resource\s*[:=]\s*['"]([a-z0-9_]+)['"]""", s)):
            out.setdefault(res, set()).update(roles)
    return out


def analyse():
    src = _read(SD, 'the role gates')
    sets = role_sets(src)
    gated = gated_branches(src)
    all_roles = set()
    for v in sets.values():
        all_roles |= v
    drv = driven(all_roles)

    uncovered, covered, undriven = [], [], []
    for res in sorted(gated):
        allowed = set()
        for name in gated[res]:
            allowed |= sets.get(name, set())
        excluded = all_roles - allowed
        got = drv.get(res)
        if not got:
            # NOT the same finding. Nothing drives this resource at all, so there is
            # no suite to add an arm to -- that is a coverage gap of a different
            # kind and is counted apart rather than folded in.
            undriven.append((res, sorted(gated[res])))
            continue
        if got & excluded:
            covered.append((res, sorted(got & excluded)))
        else:
            uncovered.append((res, sorted(gated[res]), sorted(got)))
    return sets, gated, uncovered, covered, undriven


def ablate(resource):
    """Delete `resource`'s role gate(s), run every suite, report CAUGHT or SILENT.

    ── THE ONLY SOUND MEASUREMENT IN THIS FILE ─────────────────────────────────
    The static pass above is a SCREEN: it asks whether a suite names an excluded
    role, which is a proxy for the real question. This asks the real question --
    delete the gate and see whether anything goes red. Three static rules were
    tried and all three were wrong (see driven()); this one cannot be, because it
    is the property itself rather than a pattern that correlates with it.

    IT COSTS A FULL SUITE RUN PER GATE, which is why it is on demand and not the
    default. It restores the file and asserts byte-identity before returning --
    a mutation tool that can leave a repo mutated is worse than no tool, and this
    one edits the platform's largest dispatcher.
    """
    src = io.open(SD, encoding='utf-8', errors='replace').read()
    marks = [(m.start(), m.group(1)) for m in BRANCH_MARK.finditer(src)]
    blocks = []
    for i, (pos, name) in enumerate(marks):
        if name != resource:
            continue
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        for g in re.finditer(r' *if \(!([A-Z][A-Z0-9_]*ROLES)\[session\.role\]\) \{\n'
                             r'(?:[^\n]*\n)*?[ ]*\}\n', src[pos:end]):
            blocks.append((pos + g.start(), pos + g.end(), g.group(1)))
    if not blocks:
        sys.stderr.write('COULD NOT TELL -- no role gate found for %r. Either the '
                         'name is wrong or the gate shape moved; this is not '
                         '"the gate is untested".\n' % resource)
        return 2

    suites = []
    for pat in (('api',), ('api', '_lib'), ('tests',)):
        d = os.path.join(REPO, *pat)
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if n.endswith('.test.js') or (pat[0] == 'tests' and n.endswith('.js')):
                suites.append(os.path.join(d, n))

    def run_all():
        bad = set()
        for f in suites:
            try:
                r = subprocess.run(['node', f], capture_output=True, timeout=300)
                if r.returncode != 0:
                    bad.add(os.path.relpath(f, REPO).replace(os.sep, '/'))
            except Exception:
                bad.add(os.path.relpath(f, REPO).replace(os.sep, '/') + ' (error)')
        return bad

    print('ABLATING %s -- %d gate block(s): %s'
          % (resource, len(blocks), ', '.join(b[2] for b in blocks)))
    print('baseline over %d suites (this takes a while) ...' % len(suites))
    base = run_all()
    print('baseline failures: %d' % len(base))

    rc = 0
    try:
        for start, end, rs in blocks:
            mutated = src[:start] + src[end:]
            io.open(SD, 'w', encoding='utf-8', newline='\n').write(mutated)
            chk = subprocess.run(['node', '--check', SD], capture_output=True)
            if chk.returncode != 0:
                # NOT a pass. A mutation that will not parse has tested nothing,
                # and reporting it as CAUGHT would be the worst possible answer.
                print('  %-24s COULD NOT TELL -- the mutation does not parse' % rs)
                rc = max(rc, 2)
                io.open(SD, 'w', encoding='utf-8', newline='\n').write(src)
                continue
            newly = sorted(run_all() - base)
            if newly:
                print('  %-24s CAUGHT by %d suite(s): %s'
                      % (rs, len(newly), ', '.join(newly[:3])))
            else:
                print('  %-24s *** SILENT *** deleting this gate failed NOTHING'
                      % rs)
                rc = max(rc, 1)
            io.open(SD, 'w', encoding='utf-8', newline='\n').write(src)
    finally:
        io.open(SD, 'w', encoding='utf-8', newline='\n').write(src)
    # Byte-identity, asserted rather than assumed.
    if io.open(SD, encoding='utf-8', errors='replace').read() != src:
        sys.stderr.write('RESTORE FAILED -- %s is not byte-identical. FIX THIS '
                         'BEFORE ANYTHING ELSE.\n' % SD)
        return 2
    print('restored byte-identical')
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ablate', metavar='RESOURCE',
                    help='delete that resource\'s role gate(s), run every suite and '
                         'report CAUGHT or SILENT. The only sound measurement here; '
                         'exit 1 if any gate is SILENT, 2 if it could not be told')
    ap.add_argument('--list', action='store_true', help='print every uncovered gate')
    ap.add_argument('--baseline', action='store_true',
                    help='rewrite the pin to the CURRENT numbers. Only correct after '
                         'a real arm is added, never to make a run pass')
    args = ap.parse_args(argv)

    if args.ablate:
        return ablate(args.ablate)

    try:
        sets, gated, uncovered, covered, undriven = analyse()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2

    print('ROLE-GATE NEGATIVE COVERAGE (api/sd-data.js)')
    print('%d role set(s) declared, %d resource branch(es) gated on one.'
          % (len(sets), len(gated)))
    print('')
    print('UNCOVERED -- a suite drives it, never with a role the gate excludes: %d'
          % len(uncovered))
    print('COVERED   -- some suite drives it with an excluded role:             %d'
          % len(covered))
    print('NOT DRIVEN by any suite at all (a different gap, counted apart):     %d'
          % len(undriven))
    print('')
    if args.list or uncovered:
        for res, gs, got in uncovered:
            print('   %-26s gate=%-34s driven-as=%s'
                  % (res, ','.join(gs)[:34], ','.join(got)))
    if args.list and undriven:
        print('')
        print('   NOT DRIVEN:')
        for res, gs in undriven:
            print('   %-26s gate=%s' % (res, ','.join(gs)))
    print('')
    print('AN UNCOVERED GATE WOULD SURVIVE BEING DELETED. That is the whole claim --')
    print('not that the gate is wrong, but that nothing would notice its absence.')
    print('api/sd-data-family-contacts.test.js was 18 green arms over a resource with')
    print('NO GATE AT ALL, because every arm ran as owner.')
    print('')

    if args.baseline:
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            '_what': 'Pinned role-gate negative coverage. Written by '
                     'tools/role_gate_negative_coverage.py --baseline. A ratchet: '
                     '`uncovered` must never rise. Lower it by adding an arm that '
                     'drives the resource with a role its gate excludes.',
            'uncovered': len(uncovered),
            'covered': len(covered),
            'not_driven': len(undriven),
            'gated_total': len(gated),
            'uncovered_resources': [u[0] for u in uncovered],
        }, indent=2, sort_keys=True) + '\n')
        print('wrote %s' % os.path.relpath(PIN, REPO))
        return 0

    if not os.path.isfile(PIN):
        sys.stderr.write('COULD NOT TELL -- %s does not exist, so nothing was '
                         'compared. Run --baseline once to pin the measured state.\n'
                         % os.path.relpath(PIN, REPO))
        return 2
    try:
        pin = json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        sys.stderr.write('COULD NOT TELL -- %s will not parse (%s). NOTHING WAS '
                         'COMPARED.\n' % (os.path.relpath(PIN, REPO), e))
        return 2
    was = pin.get('uncovered')
    if not isinstance(was, int):
        sys.stderr.write('COULD NOT TELL -- the pin carries no integer `uncovered`.\n')
        return 2

    if len(uncovered) > was:
        print('REGRESSION -- uncovered role gates rose from %d to %d.' % (was, len(uncovered)))
        print('Either add an arm driving the new gate with a role it excludes, or say')
        print('why it does not need one and re-pin with --baseline in the same commit.')
        return 1
    if len(uncovered) < was:
        print('IMPROVED -- uncovered fell from %d to %d. Re-pin:' % (was, len(uncovered)))
        print('   python tools/role_gate_negative_coverage.py --baseline')
        return 0
    print('OK -- no worse than pinned (%d uncovered).' % was)
    print('A RATCHET IS NOT A PASS. %d gate(s) would still survive deletion.'
          % len(uncovered))
    return 0


if __name__ == '__main__':
    sys.exit(main())
