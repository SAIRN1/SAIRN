"""Negative control for api/_lib/sairnsenior-hydrate-delegation.test.js.

    python tests/run_sairnsenior_hydrate_delegation_probe.py

Exit 0  every planted defect was REFUSED, and sairnsenior.html is
        byte-identical again afterwards
Exit 1  a planted defect SURVIVED, or the app file was left modified
Exit 2  COULD NOT RUN -- never folded into either of the other two

── WHY THIS ONE IN PARTICULAR ──────────────────────────────────────────────
The gap this suite closes existed because eight hydrates were pinned by
NOTHING: rewriting any of them back to additive-only would have broken no test
anywhere. A suite written to close that is worth exactly as much as its
ability to fail, so every hydrate gets both mutations, individually.

  A. DELEGATION REMOVED -- the merge call is taken out of that hydrate.
  B. THE CALL IS STILL IN THE FILE BUT NOT IN THAT HYDRATE -- moved to a
     comment at end of file. This is the one that separates an
     extracted-body assertion from a file-wide regex, and it is the shape
     the old stale arms actually had.

A third mutation is run for the variable-key hydrates only: dropping ONE
resource from the pair list while leaving the call intact. A call-only arm
passes that and the resource silently stops being merged.
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = 'sairnsenior.html'
SUITE = os.path.join('api', '_lib', 'sairnsenior-hydrate-delegation.test.js')
NODE = 'node'

LITERAL = [
    ('senHydrateClients', 'sen_clients'),
    ('senHydrateCaregivers', 'sen_caregivers'),
    ('senHydrateVisits', 'sen_visits'),
    ('senHydrateClaims', 'sen_claims'),
    ('senHydrateFranchise', 'sen_franchise_agreements'),
]
VARIABLE = [
    ('senHydrateReferrals', ['sen_referrals', 'sen_referral_sources']),
    ('senHydrateOrg', ['sen_branches', 'sen_applicants']),
    ('senHydrateTraining', ['sen_training_records', 'sen_training_rules']),
]


def die(msg):
    print('\nCOULD NOT RUN -- %s' % msg)
    sys.exit(2)


def read():
    with open(os.path.join(ROOT, APP), 'r', encoding='utf-8', newline='') as fh:
        return fh.read()


def write(text):
    with open(os.path.join(ROOT, APP), 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)


def suite_passes():
    """Anything but exit 0 is a refusal. A suite that cannot run has not
    cleared the code either."""
    p = subprocess.run([NODE, SUITE], cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0


def body_span(src, name):
    """Brace-balanced span of `function name(...)`, same extraction the suite
    uses -- so a mutation lands where the assertion looks."""
    start = src.find('function ' + name + '(')
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(src)):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return start, i + 1
    return None


def mutate_a(src, name, call_re):
    """A. delegation removed from THIS hydrate."""
    span = body_span(src, name)
    if not span:
        return None
    a, b = span
    body = src[a:b]
    new = re.sub(call_re, 'null', body, count=1)
    if new == body:
        return None
    return src[:a] + new + src[b:]


def mutate_b(src, name, call_re):
    """B. the call still exists IN THE FILE, just not in this hydrate.

    This is what a file-wide regex cannot tell from correct code, and it is
    the shape the pre-2026-09-21 arms actually had.
    """
    span = body_span(src, name)
    if not span:
        return None
    a, b = span
    body = src[a:b]
    m = re.search(call_re, body)
    if not m:
        return None
    moved = m.group(0)
    new = body[:m.start()] + 'null' + body[m.end():]
    return (src[:a] + new + src[b:]
            + '\n<!-- PROBE: the call still exists in this file: '
            + moved + ' -->\n')


def mutate_c(src, name, res):
    """C. one resource quietly leaves the PAIR LIST, fetch and call intact.

    ── THIS MUTATION DID NOT DO WHAT ITS LABEL SAID, AND THE FIRST RUN SHOWED
    ── IT ─────────────────────────────────────────────────────────────────
    It replaced the first occurrence of `'<res>'` in the body. Every one of
    these hydrates names each resource TWICE -- once in its
    `senData('read','<res>',...)` fetch and once in the pair list -- and the
    FETCH COMES FIRST. So the mutation broke the fetch, left the pair list
    alone, and all six ran as SURV against an arm that had just been correctly
    re-anchored on the pair list. The arm was right and the mutation was
    lying about what it planted.

    A probe whose mutation does not land where its label claims reports a
    coverage gap that does not exist -- which is the same defect shape as an
    assertion that passes for the wrong reason, one layer up. Anchored on
    `['<res>',` now, which is the pair-list position itself.
    """
    span = body_span(src, name)
    if not span:
        return None
    a, b = span
    body = src[a:b]
    needle = "['" + res + "',"
    if needle not in body:
        return None
    new = body.replace(needle, "['sen_probe_removed',", 1)
    return src[:a] + new + src[b:]


def main():
    for rel in (APP, SUITE):
        if not os.path.isfile(os.path.join(ROOT, rel)):
            die('%s is not in this clone.' % rel)

    pre = subprocess.run(['git', 'status', '--porcelain', APP, SUITE],
                         cwd=ROOT, capture_output=True, text=True)
    if pre.returncode != 0:
        die('could not read git status: %s' % (pre.stderr or '').strip())
    already_dirty = sorted(l[3:] for l in pre.stdout.splitlines() if l.strip())

    if not suite_passes():
        die('the suite is ALREADY RED before any mutation. A probe against a '
            'red suite proves nothing.')
    print('baseline: %s is GREEN\n' % SUITE)

    original = read()
    planned = []
    for name, res in LITERAL:
        call = r"senServerWinsMerge\('" + res + r"',\s*serverRows\)"
        planned.append(('A  %-24s delegation removed' % name,
                        lambda s, n=name, c=call: mutate_a(s, n, c)))
        planned.append(('B  %-24s call moved OUT of the hydrate, still in file'
                        % name, lambda s, n=name, c=call: mutate_b(s, n, c)))
    for name, resources in VARIABLE:
        call = r'senServerWinsMerge\(key,\s*rows\)'
        planned.append(('A  %-24s delegation removed' % name,
                        lambda s, n=name, c=call: mutate_a(s, n, c)))
        planned.append(('B  %-24s call moved OUT of the hydrate, still in file'
                        % name, lambda s, n=name, c=call: mutate_b(s, n, c)))
        for res in resources:
            planned.append(('C  %-24s %s dropped from the pair list'
                            % (name, res),
                            lambda s, n=name, r=res: mutate_c(s, n, r)))

    survived = []
    try:
        for label, build in planned:
            mutated = build(original)
            if mutated is None:
                die('mutation %r could not be applied -- its anchor is gone. '
                    'That is NOT a pass; the probe has stopped testing what it '
                    'claims to test.' % label.strip())
            if mutated == original:
                die('mutation %r changed nothing.' % label.strip())
            write(mutated)
            passed = suite_passes()
            write(original)
            if passed:
                survived.append(label)
            print('  %-4s %s' % ('SURV' if passed else 'ok', label))
    finally:
        write(original)

    print()
    if read() != original:
        print('NOT RESTORED: %s' % APP)
        return 1
    print('  ok   %s is byte-identical again' % APP)

    if not suite_passes():
        print('  FAIL the suite is not green again with everything restored')
        return 1
    print('  ok   the suite is GREEN again with everything restored')

    post = subprocess.run(['git', 'status', '--porcelain', APP, SUITE],
                          cwd=ROOT, capture_output=True, text=True)
    now_dirty = sorted(l[3:] for l in post.stdout.splitlines() if l.strip())
    if now_dirty != already_dirty:
        print('NEWLY DIRTY: %s' % ', '.join(set(now_dirty) - set(already_dirty)))
        return 1
    print('  ok   nothing newly dirty (%d file(s) were already modified before '
          'this run and are not its doing)' % len(already_dirty))

    if survived:
        print('\n%d MUTATION(S) SURVIVED -- the suite passed while the hydrate '
              'was broken:' % len(survived))
        for s in survived:
            print('   %s' % s)
        return 1

    print('\nALL %d MUTATIONS REFUSED across %d hydrates.'
          % (len(planned), len(LITERAL) + len(VARIABLE)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
