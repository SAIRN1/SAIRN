#!/usr/bin/env python
"""Probe: a pure-base push retry never skips the gate over a changed gate.

    python tests/run_pure_base_skip_probe.py

REQUIREMENT (C3, docs/recurring-bug-classes-2.md, cody b57; enforced b58): a
retry may skip the pre-push gate only when our patches are the ones the gate
passed, the incoming commits touch none of our files, NONE of what the gate
itself reads (the tier register, .githooks/, the hook, any tool the hook runs
or imports), and the whole-tree re-check is green. Every other case -- and
every case this cannot decide -- takes the full gate.

The arms drive tools/pure_base_skip.decide() with the REAL derived gate read
set. Section C ablates the regate rule and the floor and requires the arms
that depend on them to go red, so an arm that cannot fail is caught.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tools'))
import pure_base_skip as P  # noqa: E402

GREEN = lambda: [('defect_register', 0), ('master_plan', 0), ('traceability_matrix', 0)]
OURS = ['tests/sd_data_mech_write_unconfirmed.js', 'api/sd-data.js']
PATCH = 'aaa bbb'
results = []


def arm(name, ok):
    results.append((name, bool(ok)))
    print('  %s  %s' % ('ok  ' if ok else 'FAIL', name))


def code(incoming, tools, recheck=GREEN, patches=PATCH, gated=PATCH, ours=OURS):
    return P.decide(ours, incoming, patches, gated, tools, recheck)[0]


def main():
    tools = P.gate_tools()
    print('A. the gate read set is derived from the real hook')
    arm('derived (%s tools), at or above the floor %d'
        % (None if tools is None else len(tools), P.MIN_GATE_TOOLS),
        tools is not None and len(tools) >= P.MIN_GATE_TOOLS)
    if tools is None:
        print('COULD NOT RUN: the hook could not be read')
        return 2
    for t in ('tools/gate_skip.py', 'tools/tier_a_review_gate.py', 'tools/bypass_log.py'):
        arm('%s is in the read set' % t, t in tools)
    one_tool = sorted(tools)[0]

    print('\nB. what is FORCED into the full gate')
    unrelated = ['docs/some-unrelated-note.md']
    arm('control: an unrelated incoming file with a green re-check -> SKIP',
        code(unrelated, tools) == P.SKIP)
    for path in (P.TIER_REGISTER, '.githooks/pre-push', '.githooks/post-rewrite', P.HOOK,
                 one_tool):
        arm('incoming %s -> GATE' % path, code(unrelated + [path], tools) == P.GATE)
    arm('incoming change to one of OUR files -> GATE', code(['api/sd-data.js'], tools) == P.GATE)
    arm('our patch-ids differ from the gated ones -> GATE',
        code(unrelated, tools, gated='aaa ccc') == P.GATE)
    arm('no gate pass recorded -> GATE', code(unrelated, tools, gated='') == P.GATE)
    for rc in (1, 2, None):
        red = lambda rc=rc: [('defect_register', 0), ('master_plan', rc), ('traceability_matrix', 0)]
        arm('re-check master_plan rc=%s -> GATE' % rc, code(unrelated, tools, recheck=red) == P.GATE)
    called = []
    arm('a regate path decides GATE without running the 18 s re-check',
        code([P.TIER_REGISTER], tools, recheck=lambda: called.append(1) or GREEN()) == P.GATE
        and not called)
    arm('read set underivable (None) -> COULD NOT DECIDE, never SKIP',
        code(unrelated, None) == P.CANNOT)
    arm('read set below the floor -> COULD NOT DECIDE, never SKIP',
        code(unrelated, {P.HOOK}) == P.CANNOT)
    missing = P.gate_tools(repo=os.path.join(HERE, 'no-such-repo-b58'))
    arm('gate_tools() on an unreadable hook returns None (fail closed)', missing is None)

    print('\nC. ABLATION: each rule removed must turn its arm red')
    real_reason, real_floor = P.regate_reason, P.MIN_GATE_TOOLS
    try:
        P.regate_reason = lambda incoming, tools: None
        arm('without the regate rule, a tier-register change would SKIP (arm B can fail)',
            code([P.TIER_REGISTER], tools) == P.SKIP)
        P.regate_reason = real_reason
        P.MIN_GATE_TOOLS = 0
        arm('without the floor, a one-tool read set would SKIP (floor arm can fail)',
            code(['docs/x.md'], {P.HOOK}) == P.SKIP)
    finally:
        P.regate_reason, P.MIN_GATE_TOOLS = real_reason, real_floor

    failed = [n for n, ok in results if not ok]
    print('\n%s -- %d passed, %d failed' % ('FAILED' if failed else 'PASSED',
                                           len(results) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
